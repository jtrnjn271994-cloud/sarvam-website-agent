#!/usr/bin/env python3
"""S1 smoke test: one live call per role. Prints model, seconds, cost and the reply shape. Never prints the key.
Run: python3 -I agent/smoke.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llm
llm.LOG_PATH = os.path.join(os.path.dirname(llm.HERE), "logs", "smoke-log.jsonl")
print("roles:", json.dumps(llm.roles()))
state = ["Hero headline: 'Frontier open models. Served with speed, scale and privacy.'",
         "Evidence quote: 'Run leading open models on Sarvam GPUs in India, with shared or dedicated capacity.'"]
qs = {"supports": "Does the evidence say that the models run in India?",
      "overreach": "Does the headline claim a speed number that the evidence does not give?"}
ok = True
for role in ("judge1", "judge2"):
    try:
        r = llm.decide(role, state, qs, purpose="smoke")
        print(role, "->", r["model"], "| %ss | cost %s" % (r["seconds"], r["cost"]))
        for n, a in r["answers"].items():
            print("   ", n, "p=", a["p"], "type=", a["type"], "raw keys=", sorted(a["raw"]) if isinstance(a["raw"], dict) else a["raw"])
    except llm.LLMError as e:
        ok = False; print(role, "FAILED:", e)
try:
    for role in ("reasoning", "writer"):
        r = llm.chat([{"role": "user", "content": "Write one plain sentence that says a cloud service runs in India. No marketing words."}], role=role, max_tokens=800, purpose="smoke")
        print(role, "->", r["model"], "| %ss | cost %s" % (r["seconds"], r["cost"])); print("   text:", r["text"].strip()[:200])
except llm.LLMError as e:
    ok = False; print("chat FAILED:", e)
sys.exit(0 if ok else 1)
