#!/usr/bin/env python3
"""Spend caps for one run, from agent/budget.json (see rules/spend-rules.md).

Dry run (prints a plan, makes zero calls):  python3 -I agent/budget.py --dry-run
Self test:                                  python3 -I agent/budget.py --selftest

The Budget class counts input and output tokens (an estimate of characters / 4 when no count
comes from the model), calls for each step and fix-loop rounds. It raises BudgetExceeded when a
cap is hit. It never raises a cap. Only a person edits budget.json.
Cache hits cost nothing and do not count toward a call cap.
Standard library only.
"""
import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

# Step name in models.json -> key in budget.json call_caps. A step with no entry has no call cap
# but still counts toward the tokens cap.
STEP_CAP = {"generate_bets": "bets", "generate_copy": "copy", "generate_design": "design",
            "visual_review": "visual_review", "validate": "jev"}
LOG_COLUMNS = ["step", "model", "mode", "tokens_in", "tokens_out", "cost_estimate", "result"]


class BudgetExceeded(Exception):
    pass


def estimate_tokens(text):
    return max(1, len(str(text or "")) // 4)


def load_caps(path=None):
    return common.load_json(path or os.path.join(common.AGENT_DIR, "budget.json"))


class Budget(object):
    def __init__(self, caps=None):
        self.caps = caps if caps is not None else load_caps()
        self.tokens_in = 0
        self.tokens_out = 0
        self.calls = {}
        self.rounds = {}
        self.log = []

    @property
    def cache_on(self):
        return bool(self.caps.get("cache", True))

    @property
    def tokens_used(self):
        return self.tokens_in + self.tokens_out

    def cap_key(self, step):
        return STEP_CAP.get(step)

    def check_before(self, step, est_in, est_out=0):
        """Raise BudgetExceeded if one more call to this step would break a cap."""
        key = self.cap_key(step)
        if key is not None:
            cap = self.caps.get("call_caps", {}).get(key)
            if cap is not None and self.calls.get(step, 0) + 1 > cap:
                raise BudgetExceeded("Call cap reached for step %s: %d calls (cap %d, budget.json call_caps.%s)."
                                     % (step, self.calls.get(step, 0), cap, key))
        cap = self.caps.get("max_tokens_per_run")
        if cap is not None and self.tokens_used + est_in + est_out > cap:
            raise BudgetExceeded("Tokens cap would be passed: %d used, %d more needed, cap %d (budget.json max_tokens_per_run)."
                                 % (self.tokens_used, est_in + est_out, cap))

    def record(self, step, model, mode, tokens_in, tokens_out, cached=False, result="ok"):
        if cached:
            self.log.append([step, model, "cache", 0, 0, "0 (cache hit)", result])
            return
        self.calls[step] = self.calls.get(step, 0) + 1
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        self.log.append([step, model, mode, tokens_in, tokens_out, "not priced (no rate table)", result])

    def loop_round(self, name):
        """Count one fix round. Raise BudgetExceeded after loop_limit rounds."""
        limit = self.caps.get("loop_limit", 2)
        self.rounds[name] = self.rounds.get(name, 0) + 1
        if self.rounds[name] > limit:
            raise BudgetExceeded("Loop limit reached for %s: %d rounds (limit %d). List the faults in the report." % (name, limit, limit))

    def summary(self):
        caps = self.caps.get("call_caps", {})
        return {"tokens_used": self.tokens_used, "tokens_in": self.tokens_in, "tokens_out": self.tokens_out,
                "cap_tokens": self.caps.get("max_tokens_per_run"),
                "calls": dict(self.calls), "call_caps": dict(caps),
                "loop_rounds": dict(self.rounds), "loop_limit": self.caps.get("loop_limit")}

    def log_csv(self):
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(LOG_COLUMNS)
        w.writerows(self.log)
        return buf.getvalue()

    def write_log(self, run_dir):
        common.write_file(os.path.join(run_dir, "run-log.csv"), self.log_csv())


def dry_run_lines(budget, plan, models=None):
    """plan: list of dicts {step, calls, est_in, est_out}. Return printable lines. Makes no call."""
    steps = (models or {}).get("steps", {})
    lines = ["DRY RUN. No model is called. Nothing is spent.", "",
             "%-16s %-8s %-7s %-10s %-10s %s" % ("step", "model", "calls", "est in", "est out", "call cap"),
             "%-16s %-8s %-7s %-10s %-10s %s" % ("-" * 4, "-" * 5, "-" * 5, "-" * 6, "-" * 7, "-" * 8)]
    total = 0
    over = []
    for p in plan:
        spec = steps.get(p["step"], {})
        key = budget.cap_key(p["step"])
        cap = budget.caps.get("call_caps", {}).get(key) if key else None
        total += p["calls"] * (p["est_in"] + p["est_out"])
        if cap is not None and p["calls"] > cap:
            over.append("step %s plans %d calls, cap is %d" % (p["step"], p["calls"], cap))
        lines.append("%-16s %-8s %-7d %-10d %-10d %s" % (p["step"], spec.get("model", "?"), p["calls"], p["est_in"], p["est_out"],
                                                         "none" if cap is None else cap))
    cap = budget.caps.get("max_tokens_per_run")
    lines += ["", "Estimated tokens for the run: %d (cap %s). Estimate is characters / 4." % (total, cap),
              "Cost estimate: not priced. budget.json holds no price list.",
              "Loop limit: %s rounds." % budget.caps.get("loop_limit"), "Cache: %s." % ("on" if budget.cache_on else "off")]
    if cap is not None and total > cap:
        over.append("estimated tokens %d pass the cap %d" % (total, cap))
    for o in over:
        lines.append("WOULD STOP: " + o)
    return lines, bool(over)


def selftest():
    st = common.SelfTest("budget")
    caps = {"max_tokens_per_run": 1000, "call_caps": {"bets": 2, "copy": 1}, "loop_limit": 2, "cache": True}
    b = Budget(caps)
    st.expect(estimate_tokens("a" * 40) == 10 and estimate_tokens("") == 1, "tokens estimate is characters / 4, at least 1")
    b.check_before("generate_bets", 100)
    b.record("generate_bets", "m", "mock", 100, 50)
    b.record("generate_bets", "m", "mock", 100, 50)
    try:
        b.check_before("generate_bets", 10)
        st.expect(False, "a call over the call cap raises BudgetExceeded")
    except BudgetExceeded as e:
        st.expect("Call cap" in str(e) and "bets" in str(e), "a call over the call cap raises BudgetExceeded and names the cap")
    b.check_before("read_summary", 10)
    st.expect(True, "a step with no call cap is allowed under the tokens cap")
    try:
        b.check_before("read_summary", 900)
        st.expect(False, "a call that would pass the tokens cap raises BudgetExceeded")
    except BudgetExceeded as e:
        st.expect("Tokens cap" in str(e), "a call that would pass the tokens cap raises BudgetExceeded")
    b.record("generate_copy", "m", "mock", 5, 5, cached=True)
    st.expect(b.calls.get("generate_copy", 0) == 0 and b.tokens_used == 300, "a cache hit costs nothing and is not counted as a call")
    b.loop_round("fix")
    b.loop_round("fix")
    try:
        b.loop_round("fix")
        st.expect(False, "a third fix round raises BudgetExceeded")
    except BudgetExceeded:
        st.expect(True, "a third fix round raises BudgetExceeded")
    st.expect(b.log_csv().splitlines()[0] == ",".join(LOG_COLUMNS) and len(b.log_csv().splitlines()) == 4, "the run log has a header and one row per call")
    lines, over = dry_run_lines(Budget(caps), [{"step": "generate_bets", "calls": 3, "est_in": 400, "est_out": 100}])
    st.expect(over and any("WOULD STOP" in l for l in lines), "a dry run flags a plan that breaks a cap")
    lines, over = dry_run_lines(Budget(caps), [{"step": "generate_copy", "calls": 1, "est_in": 100, "est_out": 100}])
    st.expect(not over and lines[0].startswith("DRY RUN"), "a dry run of a small plan shows no stop")
    return st.done()


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--dry-run" in argv:
        b = Budget()
        plan = [{"step": s, "calls": c, "est_in": 2000, "est_out": 800} for s, c in
                (("generate_bets", 1), ("generate_copy", 2), ("generate_design", 1))]
        lines, over = dry_run_lines(b, plan, common.load_json(os.path.join(common.AGENT_DIR, "models.json")))
        print("\n".join(lines))
        return 1 if over else 0
    print("Use --dry-run or --selftest. The run script (run.py) uses this file.")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
