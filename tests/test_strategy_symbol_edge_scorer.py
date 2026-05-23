"""Elite scorer: symbol_edge component distinguishes proven vs unproven symbols.

The symbol_edge component (from _PROVEN_PROFITABLE_SYMBOLS in elite_scorer)
assigns points based on historical profitability. FETUSDT is a proven
profitable symbol (+5 pts) while UNIUSDT is not in the registry and gets
0 pts from symbol_edge.
"""

from alpha_engine.elite_scorer import compute_elite_score


def test_fear_greed_fet_beats_uni_elite_with_registry():
    base = {
        "strategy": "st_fear_greed_contrarian",
        "source_system": "claude_gainer_st",
        "direction": "LONG",
        "confidence": 0.76,
        "forward_wr": 0.556,
        "forward_trades": 100,
        "asset_class": "crypto",
    }
    f = compute_elite_score({**base, "symbol": "FETUSDT"})
    u = compute_elite_score({**base, "symbol": "UNIUSDT"})
    # FETUSDT is in _PROVEN_PROFITABLE_SYMBOLS (+5 pts)
    # UNIUSDT is NOT in the profitable list (0 pts from symbol_edge)
    assert f["elite_breakdown"].get("symbol_edge", 0) > u["elite_breakdown"].get("symbol_edge", 0), \
        f"FET symbol_edge={f['elite_breakdown'].get('symbol_edge', 0)} should exceed UNI symbol_edge={u['elite_breakdown'].get('symbol_edge', 0)}"
    assert f["elite_breakdown"].get("symbol_edge", 0) > 0, \
        f"FETUSDT should have positive symbol_edge, got {f['elite_breakdown'].get('symbol_edge', 0)}"
