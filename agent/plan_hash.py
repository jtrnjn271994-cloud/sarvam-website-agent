"""The test plan hash. The plan is fixed before any variant. Standard library only."""
import hashlib
import json


def plan_sha(plan):
    body = dict((k, v) for k, v in plan.items() if k != "plan_hash")
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
