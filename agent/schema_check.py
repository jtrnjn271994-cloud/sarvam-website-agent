#!/usr/bin/env python3
"""A small JSON schema check. It reads the parts of draft-07 that the schemas in schemas/ use.

Use:  import schema_check; schema_check.check(obj, schema) -> list of plain sentences (empty = fits)
Self test: python3 -I agent/schema_check.py --selftest
Supported: type (one name or a list), required, properties, items, enum, pattern, minLength, maxLength,
minItems, maxItems, and additionalProperties set to false (an unknown key is named). Anything else in a schema is ignored. Standard library only.
"""
import re
import sys

TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is(value, name):
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name in TYPES:
        return isinstance(value, TYPES[name])
    return True


def check(value, schema, path="$"):
    out = []
    t = schema.get("type")
    if t is not None:
        names = t if isinstance(t, list) else [t]
        if not any(_is(value, n) for n in names):
            return ["%s must be %s." % (path, " or ".join(names))]
    if "enum" in schema and value not in schema["enum"]:
        out.append("%s must be one of: %s." % (path, ", ".join(str(x) for x in schema["enum"])))
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            out.append("%s is too short (minimum %d characters)." % (path, schema["minLength"]))
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            out.append("%s is too long (maximum %d characters)." % (path, schema["maxLength"]))
        if "pattern" in schema and not re.search(schema["pattern"], value):
            out.append("%s does not match the pattern %s." % (path, schema["pattern"]))
    if isinstance(value, dict):
        for k in schema.get("required") or []:
            if k not in value:
                out.append("%s lacks the key '%s'." % (path, k))
        for k, sub in (schema.get("properties") or {}).items():
            if k in value:
                out += check(value[k], sub, "%s.%s" % (path, k))
        if schema.get("additionalProperties") is False:
            for k in value:
                if k not in (schema.get("properties") or {}):
                    out.append("%s has the key '%s', which this schema does not allow." % (path, k))
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            out.append("%s needs at least %d item(s)." % (path, schema["minItems"]))
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            out.append("%s holds %d items. The most is %d." % (path, len(value), schema["maxItems"]))
        if isinstance(schema.get("items"), dict):
            for i, v in enumerate(value):
                out += check(v, schema["items"], "%s[%d]" % (path, i))
    return out


def selftest():
    ok = []

    def expect(c, msg):
        ok.append(bool(c))
        print("%s  %s" % ("PASS" if c else "FAIL", msg))
    sch = {"type": "object", "required": ["a", "b"], "properties": {
        "a": {"type": "string", "minLength": 2, "pattern": "^x"},
        "b": {"type": "array", "minItems": 1, "maxItems": 2, "items": {"type": ["boolean", "null"]}},
        "c": {"enum": ["u", "v"]}}}
    expect(check({"a": "xy", "b": [True, None]}, sch) == [], "a fitting object passes, and null is allowed where the type list says so")
    expect(any("lacks the key 'b'" in x for x in check({"a": "xy"}, sch)), "a missing key is named")
    expect(any("$.a is too short" in x for x in check({"a": "x", "b": [True]}, sch)), "a short string is named")
    expect(any("$.b[0] must be boolean or null" in x for x in check({"a": "xy", "b": ["no"]}, sch)), "a wrong item type is named with its index")
    expect(any("The most is 2" in x for x in check({"a": "xy", "b": [True, True, True]}, sch)), "too many items is named")
    expect(any("one of" in x for x in check({"a": "xy", "b": [True], "c": "z"}, sch)), "a value outside the enum is named")
    expect(any("must be object" in x for x in check([], sch)), "a wrong top-level type is named")
    strict = {"type": "object", "properties": {"a": {"type": "string"}}, "additionalProperties": False}
    expect(check({"a": "x"}, strict) == [] and any("key 'b'" in x for x in check({"a": "x", "b": 1}, strict)), "additionalProperties false names an unknown key")
    print("---")
    print("%d checks, %d failed" % (len(ok), ok.count(False)))
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv[1:] else 2)
