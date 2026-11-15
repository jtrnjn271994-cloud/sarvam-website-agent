#!/usr/bin/env python3
"""One door for every model call: call_model(step, system, user, cfg).

Self test:  python3 -I agent/model_adapter.py --selftest

The model for each step comes from agent/models.json. No model name is written in code.
Modes (cfg["mode"]):
  mock    Deterministic canned output. Makes no call. Spends nothing. Every reply says MOCK.
  manual  Writes the prompt to runs/<run-id>/prompts/<step>-<hash>.md and stops (text is None).
          A person pastes it into a chat tool, then saves the reply as
          runs/<run-id>/replies/<step>-<hash>.txt. The next run reads that file.
  live    OpenAI-compatible chat completions through urllib. The base URL and the key come from
          the env variables named in models.json. The code never prints a key.
  auto    (default) live when both env variables are set, else mock.
Every prompt starts with: "Answer only from these files. Say what is missing."
The reply cache is keyed by a hash of the exact messages, the model, the mode, the temperature and the endpoint. It sits in runs/<run-id>/cache/ and follows budget.json.
Standard library only.
"""
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import budget as budget_mod  # noqa: E402
import common  # noqa: E402

PREFIX = "Answer only from these files. Say what is missing."
STRONG = ("CHECKED", "CALC", "SEMRUSH", "VENDOR")
UNSET_MODELS = ("", "SET-ME")  # a placeholder in models.json that a person must replace


class AdapterError(Exception):
    pass


def load_models(path=None, profile=None):
    """Read models.json. A profile name (for example "online") merges that profile's models and steps over the default."""
    cfg = common.load_json(path or os.path.join(common.AGENT_DIR, "models.json"))
    prof = (cfg.get("profiles") or {}).get(profile) if profile else None
    if prof:
        cfg = dict(cfg, models=dict(cfg["models"], **(prof.get("models") or {})),
                   steps=dict(cfg["steps"], **{k: dict(cfg["steps"].get(k, {}), **v) for k, v in (prof.get("steps") or {}).items()}))
    return cfg


def load_env(path):
    """Put KEY=VALUE lines of a .env file into os.environ. It never overrides a variable that is already set.
    It prints, logs and returns no value. It returns the names it set."""
    names = []
    if not path or not os.path.isfile(path):
        return names
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            if key.startswith("export "):
                key = key[7:].strip()
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            if key and val and key not in os.environ:
                os.environ[key] = val
                names.append(key)
    return names


def pack(name, obj):
    """Format one named json block for a prompt."""
    return "### %s\n%s\n" % (name, json.dumps(obj, ensure_ascii=False, sort_keys=True))


def unpack(user):
    """Read the named json blocks back out of a prompt."""
    out = {}
    for m in re.finditer(r"^### (\w+)\n(.*?)(?=^### |\Z)", user, re.S | re.M):
        try:
            out[m.group(1)] = json.loads(m.group(2).strip())
        except ValueError:
            out[m.group(1)] = m.group(2).strip()
    return out


MOCK_SELF_CHECK = {"mock": True, "promise_used": "MOCK", "alternative_beaten": "MOCK", "evidence_ids_used": [],
                   "swap_test": [], "audiences_served": [], "rules_checked": [], "gaps": ["MOCK run: no model judged this."]}


TEMPERATURE = 0  # the one decoding setting the request sends. It is part of the cache key.


def contract_text(models=None, root=None):
    """The run contract every model step must follow. Its path comes from contract_file in models.json.
    `models` is the loaded models config of the call. When it names no contract_file, the project default agent/models.json decides.
    Return "" only when no contract_file is set anywhere. When one is set and the file is missing or unreadable, raise AdapterError."""
    try:
        rel_path = (models or {}).get("contract_file") or load_models().get("contract_file")
    except (OSError, ValueError) as e:
        raise AdapterError("models.json cannot be read, so the run contract cannot be found (%s)." % type(e).__name__)
    if not rel_path:
        return ""
    path = os.path.join(root or common.PROJECT, rel_path)  # a run passes its frozen folder, so the contract is the one frozen at run start
    if not os.path.isfile(path):
        raise AdapterError("The run contract file %s is set in models.json but is missing. No model call is made without it." % rel_path)
    return "### CONTRACT\n" + common.read_text(path).strip() + "\n\n"


def build_messages(system, user, models=None, root=None):
    """The one place that builds the chat messages. The live request, the manual prompt file, the size estimate and the cache hash all use it.
    System = research-only sentence + run contract + the step's system text. User = the step's user text."""
    return [{"role": "system", "content": PREFIX + "\n" + contract_text(models, root) + (system or "").strip()},
            {"role": "user", "content": user}]


def render_messages(messages):
    """The messages as one text block, for the manual prompt file and size estimates."""
    return "\n\n".join(m["content"] for m in messages)


def full_prompt(system, user, models=None):
    return render_messages(build_messages(system, user, models))


def resolve_endpoint(spec):
    """The base URL a live call for this step goes to: the env variable of the step, else base_url in models.json. No trailing slash. Never the key."""
    base = os.environ.get(spec.get("base_url_env") or "") or spec.get("base_url") or ""
    return str(base).strip().rstrip("/")


def prompt_hash(step, model, mode, messages, endpoint="", temperature=TEMPERATURE):
    """sha256 over canonical json of everything that can change the answer: step, mode, model, decoding setting, endpoint and the exact messages.
    The API key is never part of it."""
    obj = {"step": step, "mode": mode, "model": model, "temperature": temperature, "endpoint": endpoint, "messages": messages}
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


# ---- mock replies -------------------------------------------------------------------------

def _strong_claims(claims):
    rank = common.STRENGTH
    use = [c for c in claims if c.get("label") in STRONG and c.get("status") != "rejected"]
    return sorted(use, key=lambda c: (rank.get(c.get("label"), 9), c.get("id", "")))


def _evidence_of(claims):
    seen = []
    for c in claims:
        for e in c.get("evidence_ids") or []:
            if e not in seen:
                seen.append(e)
    return seen


def mock_reply(step, user):
    data = unpack(user)
    profile = data.get("PROFILE") or {}
    claims = data.get("CLAIMS") if isinstance(data.get("CLAIMS"), list) else []
    if step == "generate_bets":
        strong = _strong_claims(claims)
        by_id = sorted(strong, key=lambda c: c.get("id", ""))
        hero = [c for c in by_id if str(c.get("section")) == "hero"][:2]

        def with_hero(picks):
            return hero + [c for c in picks if c not in hero][:3]
        brief = data.get("BRIEF") or {}
        main = brief.get("main_cta") or profile.get("main_cta")  # one main button in every arm
        sets = [("Lead with the main action", main, with_hero(strong)),
                ("Lead with the strongest fact", main, with_hero(strong[:1] + [c for c in by_id if c not in strong[:1]])),
                ("Lead with all the claims", main, with_hero(by_id))]
        bets = []
        base_names = [x.get("name") for x in (data.get("BASELINE") or {}).get("sections") or [] if x.get("name") and x.get("name") != "hero"]
        for i, (title, cta, cs) in enumerate(sets, start=1):
            bets.append({"id": "BET-%d" % i, "title": title, "lead_cta": cta, "claim_ids": [c["id"] for c in cs],
                         "lead_section": base_names[(i - 1) % len(base_names)] if base_names else None,
                         "evidence_ids": _evidence_of(cs), "label": "PROPOSED",
                         "idea": "%s. Put '%s' in the first screen and back it with %d claims that carry evidence ids."
                                 % (title, cta, len(cs))})
        ev0 = (strong[0].get("evidence_ids") or [])[:1] if strong else []

        def pblk(text):
            return {"text": text, "evidence_ids": ev0, "label": "PROPOSED", "reason": "MOCK: a canned program wrote this line. No model judged it."}
        position = None
        if ev0:
            role = ((brief.get("first_buyer") or {}).get("role")) or "the first buyer"
            position = {"first_buyer": pblk(role), "category": pblk("MOCK category"), "alternatives": [pblk("MOCK alternative")],
                        "main_claim": pblk(str(strong[0].get("text") or "MOCK claim")), "proof": [pblk(str(strong[0].get("text") or "MOCK proof"))],
                        "swap_test": [{"rival_id": "MOCK-RIVAL", "rival_could_print": None, "reason": "UNKNOWN: a MOCK run reads no rival text."}],
                        "weak_points": ["MOCK weak point one.", "MOCK weak point two.", "MOCK weak point three."],
                        "self_check": dict(MOCK_SELF_CHECK)}
        reply = {"mock": True, "label": "MOCK", "bets": bets, "self_check": MOCK_SELF_CHECK}
        if position:
            reply["position"] = position
        return json.dumps(reply, ensure_ascii=False)
    if step == "generate_copy":
        bet = data.get("BET") or {}
        by_id = dict((c["id"], c) for c in claims)
        order = [by_id[i] for i in bet.get("claim_ids", []) if i in by_id]
        sections = []
        for c in order:
            name = str(c.get("section") or "proof")
            sec = next((x for x in sections if x["section"] == name), None)
            if sec is None:
                sec = {"section": name, "lines": []}
                sections.append(sec)
            sec["lines"].append({"kind": "claim", "text": str(c.get("text") or ""), "claim_ids": [c["id"]],
                                 "evidence_ids": list(c.get("evidence_ids") or []), "label": c.get("label")})
        brief = data.get("BRIEF") or {}
        ctas = [brief.get("main_cta") or profile.get("main_cta"), brief.get("second_cta") or profile.get("second_cta")]
        if bet.get("lead_cta") == ctas[1]:
            ctas.reverse()
        if isinstance((data.get("BASELINE") or {}).get("sections"), list):
            # a baseline exists: return only the hero and the lead section. The code copies every other section from the live page.
            hero_lines = [ln for sec in sections if sec["section"] == "hero" for ln in sec["lines"]] or [ln for sec in sections for ln in sec["lines"]][:2]
            hero_lines = hero_lines[:2] + [{"kind": "cta", "text": str(t).split(" (")[0], "claim_ids": [], "evidence_ids": [], "label": "PROPOSED"} for t in ctas[:1] if t]
            out = [{"section": "hero", "lines": hero_lines}]
            lead = bet.get("lead_section")
            rest = [ln for sec in sections if sec["section"] != "hero" for ln in sec["lines"]][:2]
            if lead and rest:
                out.append({"section": lead, "lines": rest})
            return json.dumps({"mock": True, "label": "MOCK", "bet_id": bet.get("id"), "sections": out, "self_check": MOCK_SELF_CHECK}, ensure_ascii=False)
        sections.append({"section": "cta", "lines": [{"kind": "cta", "text": str(t).split(" (")[0], "claim_ids": [], "evidence_ids": [],
                                                      "label": "PROPOSED"} for t in ctas if t]})
        return json.dumps({"mock": True, "label": "MOCK", "bet_id": bet.get("id"), "sections": sections, "self_check": MOCK_SELF_CHECK}, ensure_ascii=False)
    if step == "generate_design":
        names = [s.get("section") for s in (data.get("COPY") or {}).get("sections", [])]
        cta = (data.get("BRIEF") or {}).get("main_cta") or profile.get("main_cta")
        changes = [
            {"what": "Put the main action '%s' in the first screen." % cta, "why": "The goal is a click on it.", "label": "PROPOSED"},
            {"what": "Place the proof lines next to the main action.", "why": "A buyer sees the facts when they decide.", "label": "PROPOSED"},
            {"what": "Use one column at 390 px.", "why": "The page must work on a phone.", "label": "PROPOSED"}]
        return json.dumps({"mock": True, "label": "MOCK", "section_order": names, "lead_section": names[0] if names else None,
                           "changes": changes, "self_check": MOCK_SELF_CHECK}, ensure_ascii=False)
    if step in ("position_page", "position_assemble", "gap_hypothesis", "variant_fill", "buyer_checklist", "positioning_source"):
        return json.dumps(mock_v2(step, data), ensure_ascii=False)
    return "MOCK reply for step %s. No model was called." % step


def mock_checklist(data):
    """A MOCK buyer checklist draft. It cites only ids that appear in the pack it was given, with the label each source carries."""
    persona = data.get("PERSONA") or {}
    role = persona.get("role") or "the buyer"
    ev = [e for e in data.get("EVIDENCE") or [] if isinstance(e, dict) and e.get("id")]
    lib = [x for x in data.get("LIBRARY") or [] if isinstance(x, dict) and x.get("id")]
    needs = [{"text": "MOCK: %s." % persona.get("must_see", "what the buyer must see"), "source_id": None, "label": "PROPOSED"}]
    if ev:
        needs.insert(0, {"text": "MOCK: a fact from note %s that this buyer weighs." % ev[0]["id"], "source_id": ev[0]["id"], "label": ev[0].get("label") or "PROPOSED"})
    if lib:
        needs.append({"text": "MOCK: a point from library file %s." % lib[0]["id"], "source_id": lib[0]["id"], "label": "UNCHECKED" if lib[0].get("label") else "PROPOSED"})
    return {"title": "MOCK: %s" % role, "role_why": "MOCK: a canned program wrote this line. %s decides: %s." % (role, persona.get("decides", "the purchase")),
            "needs": needs, "objections": [{"text": "MOCK: the buyer doubts the page.", "source_id": None, "label": "PROPOSED"}],
            "questions": ["Does the page show what %s must see?" % role, "Does the page say who runs the test?"], "evidence_ids": [ev[0]["id"]] if ev else []}


def mock_positioning(data):
    """A MOCK positioning source: seven pages, each line cites an id that is in the pack it was given."""
    ids = [g["stamp"]["id"] for g in data.get("GROUPS") or [] if isinstance(g, dict) and isinstance(g.get("stamp"), dict) and g["stamp"].get("id")] or ["BASELINE"]
    pages = [{"number": n, "heading": "MOCK page %d" % n, "lines": [{"text": "MOCK: a canned program wrote line %d. No model judged it." % n, "source_ids": [ids[(n - 1) % len(ids)]], "label": "PROPOSED"}]}
             for n in range(1, 8)]
    return {"pages": pages, "gaps": ["MOCK: no model read the files."]}


def mock_v2(step, data):
    """MOCK replies for the flow v2.1 model steps. Every reply fits its schema in schemas/v2/ and copies real claims with their real labels.
    No model judged anything. The handlers label the saved output MOCK."""
    if step == "buyer_checklist":
        return mock_checklist(data)
    if step == "positioning_source":
        return mock_positioning(data)
    claims = data.get("CLAIMS") if isinstance(data.get("CLAIMS"), list) else []
    strong = _strong_claims(claims)
    brief = data.get("BRIEF") or {}
    role = (brief.get("first_buyer") or {}).get("role") or "the first buyer"
    by_id = dict((c["id"], c) for c in claims)
    if step == "position_page":
        page = data.get("PAGE") or {}
        n = page.get("number") if isinstance(page, dict) else 1
        pick = [strong[(int(n or 1) - 1) % len(strong)]] if strong else []
        return {"page": int(n or 1), "label": "MOCK", "points": [{"text": str(c.get("text") or ""), "claim_ids": [c["id"]], "kind": "product"} for c in pick],
                "gaps": ["MOCK: a canned program wrote this note. No model read the page."]}
    if step == "position_assemble":
        ids = []
        for pg in data.get("PAGES") or []:
            for pt in pg.get("points") or []:
                for cid in pt.get("claim_ids") or []:
                    if cid in by_id and cid not in ids:
                        ids.append(cid)
        ids = ids[:3]
        ev0 = (by_id[ids[0]].get("evidence_ids") or ["EV-000"])[:1] if ids else ["EV-000"]

        def blk(text, label="PROPOSED"):
            return {"text": text, "evidence_ids": ev0, "label": label, "reason": "MOCK: a canned program wrote this line. No model judged it."}
        proof = []
        for cid in ids:
            c = by_id[cid]
            proof.append({"text": str(c.get("text") or ""), "claim_ids": [cid], "evidence_ids": list(c.get("evidence_ids") or ev0), "label": c.get("label"),
                          "kind": "product", "reason": "MOCK: copied from claim %s with its own label. No model judged it." % cid})
        return {"first_buyer": blk(role), "category": blk("MOCK category"), "alternatives": [blk("MOCK alternative")],
                "main_claim": blk(str(by_id[ids[0]].get("text")) if ids else "MOCK claim"), "proof": proof,
                "swap_test": [{"rival_id": "MOCK-RIVAL", "rival_could_print": None, "reason": "UNKNOWN: a MOCK run reads no rival text."}],
                "weak_points": ["MOCK weak point one.", "MOCK weak point two.", "MOCK weak point three."]}
    if step == "gap_hypothesis":
        allowed = data.get("ALLOWED") if isinstance(data.get("ALLOWED"), list) else []
        sec = allowed[0] if allowed else "hero"
        cid = strong[0]["id"] if strong else "CL-000"
        return {"observation": "MOCK: the section '%s' does not lead with the proof that the buyer asks for." % sec, "evidence_ids": [cid],
                "hypothesis": "If we change the %s section for %s, clicks on the main button rise, because %s backs the new line." % (sec, role, cid),
                "change": {"section": sec, "what": "MOCK: lead the section with the strongest claim."}, "metric": "main button click rate",
                "limitation": "MOCK: the real conversion loss on this page is unknown. We have no analytics, so this is a hypothesis and not a finding."}
    arm = data.get("ARM") or "A"
    allowed = data.get("ALLOWED") if isinstance(data.get("ALLOWED"), list) else []
    sec = allowed[0] if allowed else "hero"
    if not strong:
        text, c = "MOCK line", {}
    else:
        c = strong[0] if (arm == "A" or len(strong) < 2) else strong[1]
        text = str(c.get("text") or "")
        if arm == "B" and len(strong) < 2:
            text += " (second angle)"
    lines = [{"kind": "claim", "text": text, "claim_ids": [c["id"]] if c else [], "evidence_ids": list(c.get("evidence_ids") or []), "label": c.get("label") or "PROPOSED",
              "proof_kind": "product"}]
    if sec == "hero" and brief.get("main_cta"):
        lines.append({"kind": "cta", "text": brief["main_cta"], "claim_ids": []})
    return {"arm": arm, "sections": [{"section": sec, "lines": lines}],
            "changes": [{"what": "MOCK: lead '%s' with claim %s." % (sec, c.get("id", "none")), "why": "MOCK: a canned program chose this. No model judged it.",
                         "evidence_ids": list(c.get("evidence_ids") or [])}]}


# ---- live call -----------------------------------------------------------------------------

def live_call(spec, model, system, user, urlopen=None, timeout=120, messages=None):
    """One chat completion. `messages` (from build_messages) is what is sent. Without it the messages are built from system and user."""
    base = resolve_endpoint(spec)
    key = os.environ.get(spec.get("api_key_env") or "")
    if not base:
        raise AdapterError("Env variable %s is not set. Live mode needs it." % spec.get("base_url_env"))
    if not key:
        raise AdapterError("Env variable %s is not set. Live mode needs it." % spec.get("api_key_env"))
    body = json.dumps({"model": model, "temperature": TEMPERATURE,
                       "messages": messages if messages is not None else build_messages(system, user)}).encode("utf-8")
    req = urllib.request.Request(base + "/chat/completions", data=body, method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with (urlopen or urllib.request.urlopen)(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise AdapterError("Model API answered with HTTP %s." % e.code)
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise AdapterError("Model API call failed (%s)." % type(e).__name__)
    try:
        text = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise AdapterError("Model API reply has no choices[0].message.content.")
    usage = payload.get("usage") or {}
    return text, usage.get("prompt_tokens"), usage.get("completion_tokens"), str(payload.get("model") or "unknown")


# ---- the one function ------------------------------------------------------------------------

def resolve_mode(cfg, spec):
    if spec.get("provider") == "subagent":
        return "manual"  # a Claude subagent writes the reply. No API key, no live call.
    mode = (cfg.get("mode") or "auto").lower()
    if mode == "auto":
        both = (os.environ.get(spec.get("base_url_env") or "") or spec.get("base_url")) and os.environ.get(spec.get("api_key_env") or "")
        return "live" if both else "mock"
    if mode not in ("mock", "manual", "live"):
        raise AdapterError("Unknown mode '%s'. Use mock, manual or live." % mode)
    return mode


def live_problems(step, cfg=None):
    """Why a live call to this step cannot start now. An empty list means ready. Makes no call.
    It reads .env only when cfg holds env_path."""
    cfg = cfg or {}
    load_env(cfg.get("env_path"))
    models = load_models(cfg.get("models_path"), cfg.get("profile"))
    spec = (models.get("steps") or {}).get(step) or {}
    out = []
    if str(models.get("models", {}).get(spec.get("model"), "")).strip() in UNSET_MODELS:
        out.append("The model name for step %s is not set in agent/models.json." % step)
    if not (os.environ.get(spec.get("base_url_env") or "") or spec.get("base_url")):
        out.append("No base URL: set base_url in models.json or the env variable %s." % spec.get("base_url_env"))
    if not os.environ.get(spec.get("api_key_env") or ""):
        out.append("The env variable %s is not set in this shell%s." % (spec.get("api_key_env"), "" if cfg.get("env_path") else " (a real run also reads the project .env file)"))
    return out


def call_model(step, system, user, cfg):
    """Return a dict: text, mode, model, tokens_in, tokens_out, cached, stopped, prompt_file.

    cfg keys: mode, budget (a Budget), run_dir, models_path (optional), urlopen (tests only).
    """
    load_env(cfg.get("env_path"))  # first, so the mode and the endpoint are read with the same variables the call will use. The loader never overrides a variable and never prints a value.
    models = load_models(cfg.get("models_path"), cfg.get("profile"))
    spec = (models.get("steps") or {}).get(step)
    if spec is None:
        raise AdapterError("Step '%s' is not in models.json." % step)
    if spec.get("provider") == "code":
        raise AdapterError("Step '%s' is a code step. It makes no model call." % step)
    model = models["models"][spec["model"]]
    mode = resolve_mode(cfg, spec)
    if mode == "live" and str(model).strip() in UNSET_MODELS:
        raise AdapterError("The model name for step '%s' is not set. Put the real name in agent/models.json, models.%s. "
                           "Live mode stops until a person sets it." % (step, spec["model"]))
    messages = build_messages(system, user, models, cfg.get("frozen_root"))
    prompt = render_messages(messages)
    endpoint = resolve_endpoint(spec) if mode == "live" else ""  # only a live call goes to an endpoint. Mock and manual keep one identity.
    h = prompt_hash(step, model, mode, messages, endpoint)
    bud = cfg.get("budget") or budget_mod.Budget()
    run_dir = cfg.get("run_dir")
    result = {"text": None, "mode": mode, "model": model, "routed_model": None, "tokens_in": 0, "tokens_out": 0, "cached": False,
              "stopped": False, "prompt_file": None, "hash": h[:8]}
    cache_file = os.path.join(run_dir, "cache", h + ".json") if run_dir else None
    if mode != "manual" and bud.cache_on and cache_file and os.path.isfile(cache_file):
        hit = common.load_json(cache_file)
        result.update(text=hit["text"], cached=True, routed_model=hit.get("routed_model"))
        bud.record(step, model, mode, 0, 0, cached=True)
        return result
    if mode == "manual":
        if not run_dir:
            raise AdapterError("Manual mode needs a run folder.")
        reply = os.path.join(run_dir, "replies", "%s-%s.txt" % (step, h[:8]))
        if os.path.isfile(reply):
            result["text"] = common.read_text(reply)
            bud.record(step, model, mode, 0, 0, result="manual reply read")
            return result
        pfile = os.path.join(run_dir, "prompts", "%s-%s.md" % (step, h[:8]))
        common.write_file(pfile, "# Prompt for step %s (model set in models.json: %s)\n\nPaste everything below the line "
                                 "into your chat tool. Save the reply as:\n%s\n\n---\n\n%s\n" % (step, model, common.rel(common.PROJECT, reply), prompt))
        result.update(stopped=True, prompt_file=pfile)
        bud.record(step, model, mode, 0, 0, result="manual stop: prompt written")
        return result
    tin = budget_mod.estimate_tokens(prompt)
    bud.check_before(step, tin, 0)
    if mode == "mock":
        text = mock_reply(step, user)
        tout = budget_mod.estimate_tokens(text)
    else:
        text, t_in, t_out, routed = live_call(spec, model, system, user, urlopen=cfg.get("urlopen"), timeout=cfg.get("timeout", 120), messages=messages)
        result["routed_model"] = routed
        tin = t_in if isinstance(t_in, int) else tin
        tout = t_out if isinstance(t_out, int) else budget_mod.estimate_tokens(text)
    bud.record(step, model, mode, tin, tout)
    result.update(text=text, tokens_in=tin, tokens_out=tout)
    if bud.cache_on and cache_file:
        common.write_file(cache_file, json.dumps({"text": text, "model": model, "mode": mode, "endpoint": endpoint, "routed_model": result["routed_model"]}))
    return result


def selftest():
    import io
    import shutil
    import tempfile
    st = common.SelfTest("model_adapter")
    tmp = tempfile.mkdtemp(prefix="adapter-selftest-")
    saved = dict((k, os.environ.get(k)) for k in ("MODEL_BASE_URL", "MODEL_API_KEY"))
    try:
        for k in saved:
            os.environ.pop(k, None)
        caps = {"max_tokens_per_run": 100000, "call_caps": {"bets": 1}, "loop_limit": 2, "cache": True}
        claims = [{"id": "CL-001", "label": "VENDOR", "text": "A fact.", "evidence_ids": ["EV-001"], "section": "hero", "status": "draft"},
                  {"id": "CL-002", "label": "UNCHECKED", "text": "Weak.", "evidence_ids": ["EV-002"], "section": "hero", "status": "draft"}]
        user = pack("PROFILE", {"main_cta": "Go now", "second_cta": "Talk"}) + pack("CLAIMS", claims)
        cfg = {"mode": None, "budget": budget_mod.Budget(caps), "run_dir": tmp}
        r = call_model("generate_bets", "sys", user, cfg)
        st.expect(r["mode"] == "mock" and not r["cached"], "with no key env variable the mode is mock")
        bets = json.loads(r["text"])
        st.expect(bets["label"] == "MOCK" and len(bets["bets"]) == 3, "mock bets: three bets, labelled MOCK")
        st.expect(all("CL-002" not in b["claim_ids"] for b in bets["bets"]), "mock bets skip an UNCHECKED claim")
        r2 = call_model("generate_bets", "sys", user, cfg)
        st.expect(r2["cached"] and r2["text"] == r["text"] and cfg["budget"].calls["generate_bets"] == 1,
                  "the second call with the same prompt reads the cache and costs nothing")
        r3 = call_model("generate_bets", "sys", user + "x", {"mode": "mock", "budget": budget_mod.Budget(caps), "run_dir": tmp})
        st.expect(r3["text"] is not None and not r3["cached"], "a different prompt does not hit the cache")
        try:
            call_model("generate_bets", "sys", user + "y", {"mode": "mock", "budget": cfg["budget"], "run_dir": tmp})
            st.expect(False, "a call over the call cap raises BudgetExceeded")
        except budget_mod.BudgetExceeded:
            st.expect(True, "a call over the call cap raises BudgetExceeded")
        st.expect(call_model("generate_bets", "sys", user, {"mode": "mock", "run_dir": tmp, "budget": budget_mod.Budget(caps)})["text"] == r["text"],
                  "mock output is deterministic")
        copy = json.loads(call_model("generate_copy", "s", pack("PROFILE", {"main_cta": "Go now", "second_cta": "Talk"}) +
                                     pack("CLAIMS", claims) + pack("BET", bets["bets"][0]),
                                     {"mode": "mock", "run_dir": tmp, "budget": budget_mod.Budget(caps)})["text"])
        lines = [l for s in copy["sections"] for l in s["lines"]]
        st.expect(any(l["evidence_ids"] == ["EV-001"] for l in lines) and copy["sections"][-1]["section"] == "cta",
                  "mock copy names evidence ids and ends with a cta section")
        try:
            call_model("checks", "s", "u", {"mode": "mock", "run_dir": tmp})
            st.expect(False, "a code step is refused")
        except AdapterError:
            st.expect(True, "a code step is refused")
        # manual mode
        m = call_model("generate_copy", "sys", "user text", {"mode": "manual", "run_dir": tmp, "budget": budget_mod.Budget(caps)})
        ptext = common.read_text(m["prompt_file"]) if m["prompt_file"] else ""
        st.expect(m["stopped"] and m["text"] is None and PREFIX in ptext and "user text" in ptext, "manual mode writes the prompt and stops")
        common.write_file(os.path.join(tmp, "replies", "generate_copy-%s.txt" % m["hash"]), "pasted reply")
        m2 = call_model("generate_copy", "sys", "user text", {"mode": "manual", "run_dir": tmp, "budget": budget_mod.Budget(caps)})
        st.expect(m2["text"] == "pasted reply" and not m2["stopped"], "manual mode reads a saved reply on the next run")
        st.expect(ptext.splitlines()[0].startswith("# Prompt") and "Answer only from these files. Say what is missing." in ptext,
                  "the prompt carries the research-only sentence")
        # live mode with a fake transport, no network
        secret = "sk-test-SECRET-value-123456789012345"
        os.environ["MODEL_BASE_URL"] = "https://example.invalid/v1"
        os.environ["MODEL_API_KEY"] = secret
        seen = {}

        class FakeResp(object):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps({"choices": [{"message": {"content": "live text"}}], "usage": {"prompt_tokens": 7, "completion_tokens": 3}}).encode()

        def fake_open(req, timeout=0):
            seen["url"] = req.full_url
            seen["auth"] = req.get_header("Authorization")
            seen["body"] = json.loads(req.data.decode())
            return FakeResp()
        lv = call_model("generate_copy", "sys", "hello", {"mode": "auto", "run_dir": tmp, "budget": budget_mod.Budget(caps), "urlopen": fake_open})
        st.expect(lv["mode"] == "live" and lv["text"] == "live text" and lv["tokens_in"] == 7, "auto mode is live when both env variables are set")
        st.expect(seen["url"].endswith("/v1/chat/completions") and seen["body"]["model"] == lv["model"]
                  and seen["body"]["messages"][0]["content"].startswith(PREFIX), "live call goes to /chat/completions with the model from models.json")

        st.expect("### CONTRACT" in seen["body"]["messages"][0]["content"], "the live system message carries the run contract, the same as the manual prompt")
        os.environ["MODEL_BASE_URL"] = "https://other-server.invalid/v1"
        lv2 = call_model("generate_copy", "sys", "hello", {"mode": "auto", "run_dir": tmp, "budget": budget_mod.Budget(caps), "urlopen": fake_open})
        os.environ["MODEL_BASE_URL"] = "https://example.invalid/v1"
        st.expect(not lv2["cached"] and seen["url"].startswith("https://other-server.invalid/"), "the same prompt at another endpoint is not served from the cache")

        def bad_open(req, timeout=0):
            raise urllib.error.HTTPError(req.full_url, 401, "denied " + secret, None, io.BytesIO(b"x"))
        try:
            call_model("generate_copy", "sys", "hello2", {"mode": "live", "run_dir": tmp, "budget": budget_mod.Budget(caps), "urlopen": bad_open})
            st.expect(False, "a live HTTP error raises AdapterError")
        except AdapterError as e:
            st.expect(secret not in str(e) and "401" in str(e), "a live error message never holds the key")
        st.expect(lv["routed_model"] == "unknown", "a live reply with no model field gives routed_model unknown")
        os.environ.pop("MODEL_API_KEY")
        try:
            call_model("generate_copy", "sys", "hello3", {"mode": "live", "run_dir": tmp, "budget": budget_mod.Budget(caps)})
            st.expect(False, "live mode without a key raises AdapterError")
        except AdapterError as e:
            st.expect("MODEL_API_KEY" in str(e), "live mode without a key names the env variable and stops")
        os.environ["MODEL_API_KEY"] = secret
        unset = os.path.join(tmp, "models-unset.json")
        cfg_u = common.load_json(os.path.join(common.AGENT_DIR, "models.json"))
        cfg_u["models"]["sonnet"] = "SET-ME"
        common.write_file(unset, json.dumps(cfg_u))
        try:
            call_model("generate_copy", "sys", "hello4", {"mode": "live", "run_dir": tmp, "budget": budget_mod.Budget(caps), "models_path": unset,
                                                          "urlopen": lambda *a, **k: (_ for _ in ()).throw(AssertionError("network used"))})
            st.expect(False, "live mode with an unset model name stops")
        except AdapterError as e:
            st.expect("not set" in str(e) and "SET-ME" not in str(e).split("Put")[0], "live mode with an unset model name stops with a clear message and makes no call")
        # .env loader: a fake value, never printed, never overrides, routed_model saved
        envf = os.path.join(tmp, "fake.env")
        fake = "fake-env-value-ZZ-98765"
        common.write_file(envf, "# comment\nFAKE_LOADER_A=%s\nexport FAKE_LOADER_B=\"quoted-value-QQ\"\nFAKE_LOADER_C=from-file\n" % fake)
        os.environ["FAKE_LOADER_C"] = "already-set"
        buf = io.StringIO()
        import contextlib
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            names = load_env(envf)
        st.expect(os.environ.get("FAKE_LOADER_A") == fake and os.environ.get("FAKE_LOADER_B") == "quoted-value-QQ", ".env loader sets variables from a temp file")
        st.expect(os.environ.get("FAKE_LOADER_C") == "already-set" and "FAKE_LOADER_C" not in names, ".env loader does not override a variable that is set")
        st.expect(fake not in buf.getvalue() and fake not in repr(names) and "quoted-value-QQ" not in repr(names), ".env loader prints and returns no value")
        for k in ("FAKE_LOADER_A", "FAKE_LOADER_B", "FAKE_LOADER_C"):
            os.environ.pop(k, None)
        os.environ["MODEL_BASE_URL"], os.environ["MODEL_API_KEY"] = "https://example.invalid/v1", secret

        class RoutedResp(FakeResp):
            def read(self):
                return json.dumps({"model": "vendor/routed-one", "choices": [{"message": {"content": "YES fine"}}]}).encode()
        rv = call_model("generate_copy", "sys", "routed ask", {"mode": "live", "run_dir": tmp, "budget": budget_mod.Budget(caps), "urlopen": lambda r, timeout=0: RoutedResp()})
        rv2 = call_model("generate_copy", "sys", "routed ask", {"mode": "live", "run_dir": tmp, "budget": budget_mod.Budget(caps)})
        st.expect(rv["routed_model"] == "vendor/routed-one" and rv2["cached"] and rv2["routed_model"] == "vendor/routed-one", "routed_model is read from the reply and kept in the cache")
        base_cfg, online_cfg = load_models(), load_models(profile="online")
        st.expect(base_cfg["steps"]["generate_bets"]["model"] == "sonnet" and online_cfg["models"][online_cfg["steps"]["generate_bets"]["model"]].startswith("deepseek/")
                  and online_cfg["steps"]["validate"]["model"] == base_cfg["steps"]["validate"]["model"], "the online profile moves the generate steps and keeps Jev")
        st.expect(resolve_mode({"mode": "live"}, {"provider": "subagent"}) == "manual", "a subagent step always runs in manual mode, even when live is asked")
        src = common.read_text(os.path.abspath(__file__))
        st.expect(not re.search(r"claude-|gpt-|haiku-|sonnet-|opus-", src.split("def selftest")[0]), "no model name is written in the code")
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(tmp, ignore_errors=True)
    return st.done()


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else 2)
