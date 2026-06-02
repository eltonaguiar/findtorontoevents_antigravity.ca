"""EAGLE-4 + EAGLE-5 admissibility/promotion gates (2026-06-02, minimax-m3-free).

Owns the tournament-validated pick filters in a dedicated module so concurrent
edits to production_scanner.py do not silently revert the data-backed gates.

All thresholds derived from the AI tournament top-5 T1 models
(3,692 resolved picks across 46 models, 5,492 total picks).
Source: audit_dashboard/data/ai_tournament_picks_latest.json
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# EAGLE-4 (negative side): kill noise personas, kill negative-edge directions,
# flip CRYPTO LONG→SHORT (67% WR vs 33% WR).
# ---------------------------------------------------------------------------

# Personas with <40% WR in tournament top-5 T1 (confirmed noise).
_EAGLE4_PERSONA_KILL = frozenset({
    "momentum_scalp",       # 28% WR
    "breakout_scanner",     # 28% WR
    "reflexivity_trader",   # 35% WR
    "deep_value",           # 44% WR
})

# (asset_class, direction) tuples with negative or marginal edge.
# CRYPTO LONG is handled by flip (below), not by kill.
_EAGLE4_DIRECTIONAL_KILL = frozenset({
    ("PENNY", "SHORT"),
    ("PENNY", "SELL"),
    ("COMMODITY", "SHORT"),
    ("COMMODITY", "SELL"),
    ("ETF", "SHORT"),
    ("ETF", "SELL"),
    ("EQUITY", "SHORT"),
    ("EQUITY", "SELL"),
})

# CRYPTO: SHORT 67% WR / +3.74% avg PnL vs LONG 33% WR / -0.49% avg PnL
_EAGLE4_CRYPTO_FLIP_TO_SHORT = True


def apply_eagle4_admissibility(picks):
    """Kill noise personas, kill negative-edge directions, flip CRYPTO LONG→SHORT.

    Returns a new list of admissible picks. Input picks are not mutated.
    """
    if not picks:
        return picks

    original_count = len(picks)
    kept = []
    killed_persona = 0
    killed_directional = 0
    flipped_crypto = 0

    for pick in picks:
        ac = str(pick.get("asset_class") or pick.get("category") or "").strip().upper()
        persona = str(
            pick.get("persona_id")
            or pick.get("strategy_name")
            or pick.get("strategy")
            or ""
        ).strip().lower()
        direction = str(
            pick.get("signal_type") or pick.get("direction") or "BUY"
        ).strip().upper()
        norm_dir = "SHORT" if direction in ("SELL", "SHORT") else "LONG"

        if persona in _EAGLE4_PERSONA_KILL:
            killed_persona += 1
            continue

        if _EAGLE4_CRYPTO_FLIP_TO_SHORT and ac == "CRYPTO" and norm_dir == "LONG":
            pick["signal_type"] = "SELL"
            pick["direction"] = "SHORT"
            pick["_eagle4_flipped"] = "CRYPTO_LONG_TO_SHORT"
            norm_dir = "SHORT"
            flipped_crypto += 1

        if (ac, norm_dir) in _EAGLE4_DIRECTIONAL_KILL:
            killed_directional += 1
            continue

        kept.append(pick)

    if killed_persona or killed_directional or flipped_crypto:
        print(
            f"  [EAGLE-4 ADMISSIBILITY] in={original_count} kept={len(kept)} | "
            f"killed_persona={killed_persona} killed_directional={killed_directional} "
            f"flipped_crypto_L_to_S={flipped_crypto}"
        )
    return kept


# ---------------------------------------------------------------------------
# EAGLE-5 (positive side): multiplicative confidence boost for tournament-
# validated symbols and personas. Caps at 1.0 to avoid breaking downstream gates.
# ---------------------------------------------------------------------------

_EAGLE5_SYMBOL_WHITELIST = {
    "EQUITY": {
        "BAC", "JPM", "MSFT", "AMZN", "GOOGL", "AAPL", "PEP", "MU",
        "TSLA", "AMD", "INTC", "META", "XOM", "NVDA", "KO", "WMT",
    },
    "ETF": {"EEM", "IWM", "GLD", "XLK", "XLE"},
    "PENNY": {"KULR", "RGTI", "ASTS", "RKLB", "GSAT", "IONQ", "QBTS", "MVST"},
    "COMMODITY": {"GC=F", "HG=F", "OJ=F"},
    "FUTURES": {"NQ=F"},
}

_EAGLE5_PROMOTED_PERSONAS = {
    "EQUITY": {
        "momentum_breakout", "invert_losers", "momentum_momentum",
        "trend_follower", "cycle_rotator", "statistical_arb",
    },
    "ETF": {"macro_hedge", "sector_rotation", "momentum_breakout", "deep_value"},
    "PENNY": {"microcap_momentum", "gamma_raid"},
    "COMMODITY": {"systematic_momentum", "inflation_hedge", "cta_trend", "vol_arb"},
}

_EAGLE5_SYMBOL_BOOST = 1.20
_EAGLE5_PERSONA_BOOST = 1.15


def apply_eagle5_promotion(picks):
    """Boost confidence for tournament-validated symbols/personas.

    Boosts are multiplicative and capped at 1.0. Runs after EAGLE-4 so the
    boost acts on the cleaned population. Input picks are mutated in place.
    """
    boosted_symbol = 0
    boosted_persona = 0
    for p in picks:
        ac = str(p.get("asset_class") or p.get("category") or "").strip().upper()
        sym = str(p.get("symbol") or "").strip().upper()
        persona = str(p.get("strategy") or p.get("strategy_name") or "").strip().lower()
        original_conf = float(p.get("confidence", 0.5) or 0.5)
        new_conf = original_conf
        sym_match = sym in _EAGLE5_SYMBOL_WHITELIST.get(ac, set())
        persona_match = persona in _EAGLE5_PROMOTED_PERSONAS.get(ac, set())
        if sym_match:
            new_conf *= _EAGLE5_SYMBOL_BOOST
        if persona_match:
            new_conf *= _EAGLE5_PERSONA_BOOST
        new_conf = min(1.0, new_conf)
        if sym_match or persona_match:
            p["confidence"] = new_conf
            p["_eagle5_boosted"] = True
            p["_eagle5_symbol_match"] = sym_match
            p["_eagle5_persona_match"] = persona_match
            p["_eagle4_pre_eagle5_conf"] = original_conf
            if sym_match:
                boosted_symbol += 1
            if persona_match:
                boosted_persona += 1
    if picks and (boosted_symbol or boosted_persona):
        print(
            f"  [EAGLE-5 PROMOTION] boosted_symbol={boosted_symbol} "
            f"boosted_persona={boosted_persona}"
        )
    return picks
