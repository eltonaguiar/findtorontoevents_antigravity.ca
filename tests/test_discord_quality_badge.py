from cross_aggregation.discord_notify import _quality_badge

def test_elite_badge():
    badge = _quality_badge("ELITE", 8)
    assert "ELITE" in badge
    assert "8/8" in badge

def test_collecting_badge():
    badge = _quality_badge("COLLECTING", 1)
    assert "COLLECTING" in badge
    assert "1/8" in badge

def test_no_gate_badge():
    badge = _quality_badge(None, 0)
    assert "UNRATED" in badge

def test_proven_badge():
    badge = _quality_badge("PROVEN", 7)
    assert "PROVEN" in badge
    assert "7/8" in badge
