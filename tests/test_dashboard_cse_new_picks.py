from pathlib import Path

GEN = Path(__file__).resolve().parents[1] / "audit_trail" / "dashboard_generator.py"


def test_cse_new_picks_must_be_a_list_before_slice():
    text = GEN.read_text(encoding="utf-8")
    assert 'isinstance(new_picks, list)' in text
    assert 'for pick in cse["new_picks"][-20:]' not in text
