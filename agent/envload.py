"""Load KEY=VALUE lines from .env into os.environ (never overrides a variable that is already set; never prints values)."""
import os

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.isfile(_PATH):
    for _line in open(_PATH, encoding="utf-8"):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            _v = _v.strip().strip('"').strip("'")
            if _k.strip() and _v:
                os.environ.setdefault(_k.strip(), _v)
