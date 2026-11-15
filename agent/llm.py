#!/usr/bin/env python3
"""OpenRouter clients: one for chat (the writer) and one for decision models (the judges).

Rules:
- The key comes from the environment or from .env. It is never printed, logged or returned.
- Every call is logged to a JSONL file (model, role, seconds, cost, probabilities). The log never holds the key.
- Standard library only.

Roles and model ids live in agent/models.json under "roles". Environment variables
MODEL_WRITER, MODEL_JUDGE1 and MODEL_JUDGE2 override them.
"""
import json
import os
import threading
import time

import envload  # noqa: F401  (loads .env before the settings below are read)
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
BASE = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api").rstrip("/")


def _load_key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if k:
        return k.strip()
    path = os.path.join(PROJECT, ".env")
    if os.path.isfile(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def roles():
    """Return {role: model_id}. Environment variables win over models.json."""
    cfg = json.load(open(os.path.join(HERE, "models.json"), encoding="utf-8")).get("roles", {})
    env = {"reasoning": "MODEL_REASONING", "writer": "MODEL_WRITER", "judge1": "MODEL_JUDGE1", "judge2": "MODEL_JUDGE2"}
    return {r: os.environ.get(env[r]) or cfg.get(r) for r in env}


class LLMError(Exception):
    pass


LOG_PATH = None  # set by the caller: llm.LOG_PATH = ".../run-log.jsonl"
MAX_RUN_USD = float(os.environ.get("MAX_RUN_USD", "1.00"))  # spend cap per process
SPENT = {"usd": 0.0, "calls": 0}
_LOCK = threading.Lock()   # Gate 2 scores variants in parallel threads


def _charge(cost):
    with _LOCK:
        SPENT["usd"] += float(cost or 0)
        SPENT["calls"] += 1


def _log(rec):
    if LOG_PATH:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with _LOCK, open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _post(path, body, timeout=120):
    if SPENT["usd"] >= MAX_RUN_USD:
        raise LLMError("spend cap reached: $%.4f of $%.2f (set MAX_RUN_USD to raise it)" % (SPENT["usd"], MAX_RUN_USD))
    key = _load_key()
    if not key:
        raise LLMError("OPENROUTER_API_KEY is not set (environment or .env)")
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "X-Title": "sarvam-website-agent"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
            return data, round(time.time() - t0, 2), r.status
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", "replace")[:600]
        raise LLMError("HTTP %s from %s: %s" % (e.code, path, txt))
    except urllib.error.URLError as e:
        raise LLMError("network error on %s: %s" % (path, e.reason))


def chat(messages, role="writer", max_tokens=1500, temperature=0.4, purpose=""):
    """Writer call. Returns {'text', 'model', 'cost', 'seconds'}."""
    model = roles()[role]
    data, secs, _ = _post("/v1/chat/completions", {
        "model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature})
    try:
        text = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError):
        raise LLMError("unexpected chat reply shape: %s" % json.dumps(data)[:400])
    first_cost = (data.get("usage") or {}).get("cost") or 0
    cut = data["choices"][0].get("finish_reason") == "length"
    if not text.strip() or cut:  # thinking models can spend most of the budget before they answer: retry with room
        _charge(first_cost)
        _log({"kind": "chat", "role": role, "asked_model": model, "answered_model": data.get("model", model),
              "purpose": purpose + (" (cut off, retried)" if cut else " (empty, retried)"), "seconds": secs, "cost": first_cost, "chars": len(text)})
        data, secs, _ = _post("/v1/chat/completions", {
            "model": model, "messages": messages, "max_tokens": max_tokens * 4, "temperature": temperature})
        text = data["choices"][0]["message"]["content"] or ""
        if not text.strip() or data["choices"][0].get("finish_reason") == "length":
            raise LLMError("the %s model ran out of room twice (finish_reason=%s)" % (role, data["choices"][0].get("finish_reason")))
    out = {"text": text, "model": data.get("model", model), "cost": (data.get("usage") or {}).get("cost"), "seconds": secs}
    _charge(out["cost"])
    _log({"kind": "chat", "role": role, "asked_model": model, "answered_model": out["model"],
          "purpose": purpose, "seconds": secs, "cost": out["cost"], "chars": len(text)})
    return out


def decide(role, state, questions, purpose=""):
    """Judge call. role is 'judge1' (Jev) or 'judge2'.
    state: a string, or a list of strings and parts. questions: {name: instructions_text}.
    Every question is a noul question (probability of yes).
    Returns {'answers': {name: {'p': float|None, 'type': str, 'raw': dict}}, 'model', 'cost', 'seconds'}."""
    model = roles()[role]
    body = {"model": model, "state": state,
            "questions": {n: {"type": "noul", "instructions": t} for n, t in questions.items()}}
    data, secs, _ = _post("/alpha/decisions", body)
    answers = {}
    for n in questions:
        a = data.get(n)
        if a is None and isinstance(data.get("answers"), dict):
            a = data["answers"].get(n)
        if not isinstance(a, dict):
            answers[n] = {"p": None, "type": "missing", "raw": a}
            continue
        p = a.get("noul", a.get("probability"))
        answers[n] = {"p": float(p) if isinstance(p, (int, float)) else None, "type": a.get("type", "?"), "raw": a}
    usage = data.get("usage") or {}
    out = {"answers": answers, "model": data.get("model", model), "cost": usage.get("cost"), "seconds": secs}
    _charge(out["cost"])
    _log({"kind": "decide", "role": role, "asked_model": model, "answered_model": out["model"], "purpose": purpose,
          "seconds": secs, "cost": out["cost"], "n_questions": len(questions),
          "p": {n: answers[n]["p"] for n in answers}})
    return out
