"""Per-engine override loader for swarm YAML configs.

Reads the YAML config used by `swarm_run.py` and returns the per-engine
`sampling` dict + `retries` int for a given engine name. This decouples
worker_runner.py's per-engine override handling from `swarm_run.py`'s
YAML parser (which is owned by a different subagent and not yet wired
through the per-engine sampling/retries path).

Schema fragment recognised:

    engines:
      - name: deepseek
        model: deepseek-chat
        sampling:               # optional dict passed to api_consult
          temperature: 0.1
          max_tokens: 8000
          top_p: 0.95
        retries: 2              # optional int; overrides --retries

Usage:

    import _engine_overrides
    overrides = _engine_overrides.load("path/to/config.yaml", "deepseek")
    # -> {"sampling": {...} | None, "retries": int | None}

`load()` is forgiving: missing file / missing key / unparseable yaml
returns the empty `{"sampling": None, "retries": None}` shape so callers
never need to special-case error handling.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def _empty() -> dict[str, Any]:
    return {"sampling": None, "retries": None}


def load(yaml_path: str | Path | None, engine_name: str) -> dict[str, Any]:
    """Return {sampling, retries} for the given engine; empty dict on miss."""
    if not yaml_path:
        return _empty()
    p = Path(yaml_path)
    if not p.exists():
        return _empty()
    try:
        import yaml  # type: ignore
    except ImportError:
        return _empty()
    try:
        text = p.read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
    except Exception:
        return _empty()
    engines = data.get("engines") or []
    if not isinstance(engines, list):
        return _empty()
    for ent in engines:
        if not isinstance(ent, dict):
            continue
        if ent.get("name") != engine_name:
            continue
        out = _empty()
        s = ent.get("sampling")
        if isinstance(s, dict):
            # Filter to known keys; pass-through values.
            allowed = {"temperature", "max_tokens", "max_completion_tokens",
                       "num_predict", "top_p", "presence_penalty",
                       "frequency_penalty"}
            out["sampling"] = {k: v for k, v in s.items() if k in allowed}
            if not out["sampling"]:
                out["sampling"] = None
        r = ent.get("retries")
        if isinstance(r, int) and r >= 0:
            out["retries"] = r
        return out
    return _empty()
