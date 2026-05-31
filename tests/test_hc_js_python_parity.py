"""Cross-language HC parity: Python dashboard_hc_rules vs audit_dashboard/hc_filter.js.

INC OVERALL #25 — HC JS/Python parity drift. This corpus pins identical pick
fixtures and fails CI when the two implementations disagree.

Run: pytest tests/test_hc_js_python_parity.py -q
Also: node tests/test_hc_filter.js
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_TOOLS = _ROOT / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import dashboard_hc_rules  # noqa: E402
from dashboard_hc_rules import passes_high_conviction_pick  # noqa: E402

_CORPUS = _ROOT / "tests" / "fixtures" / "hc_parity_corpus.json"
_RUNNER = _ROOT / "tests" / "hc_parity_runner.js"


def _js_passes(pick: dict) -> bool:
    proc = subprocess.run(
        ["node", str(_RUNNER), json.dumps(pick)],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(_ROOT),
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"node hc_parity_runner failed: {proc.stderr[:500]}")
    data = json.loads(proc.stdout.strip())
    return bool(data.get("pass"))


def _load_corpus() -> list[dict]:
    raw = json.loads(_CORPUS.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else []


@pytest.mark.parametrize("case", _load_corpus(), ids=lambda c: c["name"])
def test_hc_js_python_parity(case: dict):
    pick = case["pick"]
    py = passes_high_conviction_pick(pick)
    js = _js_passes(pick)
    assert py == js, f"{case['name']}: python={py} js={js} pick={pick}"
