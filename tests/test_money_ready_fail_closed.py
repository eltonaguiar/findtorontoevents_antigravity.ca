from pathlib import Path

JS = Path(__file__).resolve().parents[1] / "audit_dashboard" / "money_ready_filter.js"


def test_missing_verdict_does_not_pass():
    text = JS.read_text(encoding="utf-8")
    assert "if (!mv || !mv.classes) return false;" in text
    assert "if (!c) return false;" in text
    assert "c.verdict !== 'MONEY_READY'" in text


def test_five_gates_are_required_before_the_historical_list():
    text = JS.read_text(encoding="utf-8")
    assert "function fiveGatesPass(edge)" in text
    assert "Number(edge.n) >= 100" in text
    assert "Number(edge.dsr) > 0.95" in text
    assert "Number(edge.pbo) < 0.05" in text
    assert "Number(edge.wfe) > 0.60" in text
    assert "Number(edge.sharpe) > 0.5" in text
    assert "if (!edge || !fiveGatesPass(edge)) return null;" in text
