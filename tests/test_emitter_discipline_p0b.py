"""P0-B emitter discipline — is_emission_allowed kill list."""
from alpha_engine.emitter_discipline import is_emission_allowed


def test_hard_kill_futures_momentum():
    ok, reason = is_emission_allowed("futures_momentum", "")
    assert ok is False
    assert "HARD_KILL" in reason


def test_hard_kill_fear_greed():
    ok, _ = is_emission_allowed("st_fear_greed_contrarian", "")
    assert ok is False


def test_allowed_luxalgo_short():
    ok, reason = is_emission_allowed("luxalgo_confluence", "june2026_research")
    assert ok is True
    assert reason == "allowed"
