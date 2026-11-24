from pathlib import Path

GEN = Path(__file__).resolve().parents[1] / "audit_trail" / "dashboard_generator.py"


def test_cse_new_picks_must_be_a_list_before_slice():
    """Regression: crypto_signal_engine audit.json can store new_picks as a count.

    An int is truthy, so the old `if cse.get("new_picks"): for pick in
    cse["new_picks"][-20:]` crashed the whole dashboard generate step with
    TypeError: 'int' object is not subscriptable and left /audit stale.
    """
    text = GEN.read_text(encoding="utf-8")
    assert "isinstance(new_picks, list)" in text
    assert 'for pick in cse["new_picks"][-20:]' not in text
