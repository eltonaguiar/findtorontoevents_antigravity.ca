import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TOOLS = _ROOT / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from tier_lifecycle import evaluate_tier_row  # noqa: E402


def test_hold_default():
    r = evaluate_tier_row({"tier": "B", "n": 5, "win_rate": 0.5})
    assert r["action"] == "HOLD"


def test_demote_low_wr():
    r = evaluate_tier_row({"tier": "B", "n": 20, "win_rate": 0.40})
    # The action string is "CONSIDER_DEMOTION_OR_RETIRE" which contains "DEMOTE"
    # as a substring (DEMOT-ION). Assert on the full string for clarity.
    assert r["action"] == "CONSIDER_DEMOTION_OR_RETIRE"
