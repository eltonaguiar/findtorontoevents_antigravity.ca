#!/usr/bin/env python3
"""
Non-crypto agent entrypoint.

Fetches forex/equity/commodity data, runs the dedicated non-crypto strategy
set, scores candidates with the elite scorer, then curates a paper-trade-only
list of higher-quality picks.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf


ROOT = Path(__file__).resolve().parent
ALPHA_ENGINE = ROOT.parent / "alpha_engine"
sys.path.insert(0, str(ALPHA_ENGINE))

from commodities_strategies import (  # noqa: E402
    agricultural_spread,
    gold_safe_haven,
    metals_mean_reversion,
    oil_inventory_momentum,
    seasonal_momentum,
)
from bond_strategies import (  # noqa: E402
    bond_connors_rsi2,
    bond_credit_spread_mean_reversion,
    bond_duration_rotation,
    bond_mean_reversion,
    bond_yield_curve_slope,
    bond_yield_momentum,
)
from config import BOND_SYMBOLS, COMMODITY_SYMBOLS, EQUITY_SYMBOLS, ETF_SYMBOLS, FOREX_SYMBOLS, FUTURES_SYMBOLS  # noqa: E402
from elite_scorer import compute_elite_score  # noqa: E402
from non_crypto_quality_gate import mtf_rsi_confluence_gate, vix_hard_block_gate  # noqa: E402
from equity_strategies import (  # noqa: E402
    equity_two_bar_rsi_reversal,
    intermarket_risk_on,
    meme_social_velocity,
    momentum_factor_12m,
    penny_volume_breakout,
    quality_value_composite,
    support_resistance_bounce,
)
from etf_strategies import (  # noqa: E402
    etf_dual_momentum,
    etf_risk_parity_rotation,
    etf_sector_momentum,
    etf_trend_following,
)
from forex_strategies import (  # noqa: E402
    asian_range_breakout,
    carry_trade,
    # KILLED 2026-04-12: connors_rsi2_forex — 61.75% WR but PF 0.68, -20.6% return
    # on 995 forex trades. Classic high-WR-negative-economics trap. See
    # multi_asset/FOCUSED_NONCRYPTO_BACKTEST_REPORT_2026-04-07.md §"Weak Or
    # Misleading Edges". Losses pay too much relative to wins.
    # connors_rsi2_forex,
    cot_positioning_forex,
    cross_sectional_momentum_forex,
    london_session_breakout,
    mean_reversion_200d,
    orb_breakout,
)
from futures_strategies import (  # noqa: E402
    futures_connors_rsi2,
    futures_cross_asset_momentum,
    futures_tsmom,
    futures_vol_regime_breakout,
)


NON_CRYPTO_SYMBOLS = {**EQUITY_SYMBOLS, **FOREX_SYMBOLS, **COMMODITY_SYMBOLS, **ETF_SYMBOLS, **FUTURES_SYMBOLS, **BOND_SYMBOLS}


def _pick_direction(pick: dict) -> str:
    raw = str(pick.get("signal_type") or pick.get("direction") or "BUY").upper()
    return "SHORT" if raw in {"SELL", "SHORT"} else "LONG"


def _quality_rank(pick: dict) -> tuple[float, float, float]:
    return (
        float(pick.get("elite_score", 0) or 0),
        float(pick.get("confidence", 0) or 0),
        float(pick.get("risk_reward", 0) or 0),
    )


def _min_rr_for_pick(pick: dict) -> float:
    category = str(pick.get("category", "")).lower()
    if category == "forex":
        return 1.0
    if category in {"commodity", "futures", "bond"}:
        return 1.15
    return 1.20


DXY_TICKER = "DX-Y.NYB"  # yfinance proxy for US Dollar Index

# Per-symbol profit factor from multi_asset/FOCUSED_NONCRYPTO_BACKTEST_REPORT_2026-04-07.md.
# Symbols are tagged and given elite_score boosts proportional to their proven
# historical PF. Unknown symbols pass through with no boost (neither penalized
# nor promoted). This concentrates the curation toward backtest-validated winners
# without starving the book via a hard allowlist.
_SYMBOL_PF: dict[str, float] = {
    # ETFs
    "GLD": 3.96, "XLK": 2.99, "QQQ": 2.23, "XLF": 2.15, "XLV": 1.95,
    # Forex (DXY-filtered performance; only applies when DXY gate is also aligned)
    "USDCHF=X": 2.26, "EURUSD=X": 1.85, "AUDUSD=X": 1.64, "USDJPY=X": 1.55,
    "GBPUSD=X": 1.57,
    # Commodities / safe haven
    "GC=F": 2.42, "SI=F": 1.71, "CORN": 2.51, "CL=F": 1.63,
    # Equity blue-chip mean reversion
    "META": 1.59, "V": 1.49, "MSFT": 1.43, "JPM": 1.34, "GOOGL": 1.21,
}


def symbol_pf_boost(symbol: str) -> tuple[float, str]:
    """Return (elite_score_delta, tier_tag) for a symbol based on backtest PF.

    Tier 1 (PF >= 2.0): +8 elite, SYMBOL_PF_TIER1 — concentrated winners
    Tier 2 (PF >= 1.5): +4 elite, SYMBOL_PF_TIER2 — solid winners
    Tier 3 (PF >= 1.2): +0 elite, SYMBOL_PF_TIER3 — marginal positive
    Unknown:            +0 elite, SYMBOL_PF_UNKNOWN — neither boost nor penalty

    Soft boost by design — does not hard-block unmapped symbols, so new
    strategies / new symbols are not starved. Tighten to hard allowlist after
    validation if starvation is not observed.
    """
    pf = _SYMBOL_PF.get(symbol)
    if pf is None:
        return 0.0, "SYMBOL_PF_UNKNOWN"
    if pf >= 2.0:
        return 8.0, "SYMBOL_PF_TIER1"
    if pf >= 1.5:
        return 4.0, "SYMBOL_PF_TIER2"
    if pf >= 1.2:
        return 0.0, "SYMBOL_PF_TIER3"
    return 0.0, "SYMBOL_PF_UNKNOWN"


# Per-pair DXY correlation. Sourced from multi_asset/forex_strategies.py
# FOREX_PAIRS.dxy_correlation. Duplicated here to avoid cross-package import
# complexity (non_crypto_agent is a standalone entry point).
_DXY_CORRELATION: dict[str, float] = {
    "EURUSD=X": -0.95,
    "USDJPY=X":  0.60,
    "GBPUSD=X": -0.85,
    "AUDUSD=X": -0.70,
    "NZDUSD=X": -0.65,
    "USDCAD=X":  0.75,
    "USDCHF=X":  0.90,
    "EURJPY=X": -0.20,
}


# Per-asset-class SL-distance floors (relative %, as fractions of entry price).
# Backed by DEEPSEEK_APR122026.MD §6B which reported 75.5% of trades hit
# stop-loss on universal_resolved_picks.json (main-thread re-measurement on
# ghost-cleaned closed_picks.json showed 59.1% — still well above the 30-40%
# systematic target). PR #137 ships the exit-side complement (partial TP +
# breakeven activation in forward_test_portfolios.py); this is the entry-side
# gate that rejects picks whose stop is so tight it is effectively noise-bait.
_SL_DISTANCE_FLOOR_BY_CATEGORY: dict[str, float] = {
    "crypto": 0.020,      # crypto moves 5%+ intraday, sub-2% stops get noise-killed
    "forex": 0.005,       # forex is tight, but <0.5% is unrealistic
    "equity": 0.015,      # equities have overnight gaps
    "stock": 0.015,
    "commodity": 0.015,
    "futures": 0.015,
    "etf": 0.012,
}
_SL_DISTANCE_FLOOR_DEFAULT: float = 0.010


def sl_distance_floor_gate(pick: dict) -> tuple[bool, str]:
    """Reject picks whose stop-loss distance is below the per-asset-class floor.

    Computes SL distance as ``abs(entry_price - stop_loss) / entry_price`` and
    compares against the floor for ``pick["category"]`` (falling back to
    ``_SL_DISTANCE_FLOOR_DEFAULT`` when the category is unknown). Tight stops
    get noise-killed before any real move develops — this is the entry-side
    complement to the partial-TP + breakeven-activation exit-side fix landed
    in PR #137 (forward_test_portfolios.py).

    Safe default: passes when ``entry_price`` or ``stop_loss`` is missing or
    non-finite so that picks are never silently rejected due to missing data.
    Returns ``(allowed, reason)``.
    """
    try:
        entry_raw = pick.get("entry_price")
        sl_raw = pick.get("stop_loss")
        if entry_raw is None or sl_raw is None:
            return True, "missing entry_price/stop_loss, passing"
        entry = float(entry_raw)
        sl = float(sl_raw)
    except (TypeError, ValueError):
        return True, "non-numeric entry_price/stop_loss, passing"

    import math
    if not math.isfinite(entry) or not math.isfinite(sl) or entry == 0:
        return True, "invalid entry_price/stop_loss, passing"

    distance = abs(entry - sl) / abs(entry)
    category = str(pick.get("category", "")).lower()
    floor = _SL_DISTANCE_FLOOR_BY_CATEGORY.get(category, _SL_DISTANCE_FLOOR_DEFAULT)

    if distance < floor:
        return False, (
            f"SL distance {distance*100:.2f}% < floor "
            f"{floor*100:.2f}% for category={category or 'default'}"
        )
    return True, f"SL distance {distance*100:.2f}% >= floor {floor*100:.2f}%"


def dxy_macro_check(dxy_df: pd.DataFrame | None, symbol: str,
                    direction: str) -> tuple[bool, str]:
    """Mandatory DXY alignment check for forex picks.

    Conservative: only blocks when DXY has a clear trend AND the pair has a
    strong (|rho|>=0.5) DXY correlation AND the pick direction conflicts with
    what DXY implies. Passes on insufficient data, weak correlation, or no
    clear trend — mirroring multi_asset/forex_strategies.dxy_macro_check so
    behavior is identical across the two pipelines.
    """
    if dxy_df is None or len(dxy_df) < 60:
        return True, "DXY data unavailable, passing"
    try:
        close = dxy_df["Close"].astype(float)
        price = float(close.iloc[-1])
        ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
        ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
    except Exception:
        return True, "DXY data invalid, passing"
    import math
    if not all(map(math.isfinite, (price, ema20, ema50))):
        return True, "DXY data invalid, passing"

    dxy_bull = price > ema20 > ema50
    dxy_bear = price < ema20 < ema50
    if not dxy_bull and not dxy_bear:
        return True, "DXY no clear trend, passing"

    correlation = _DXY_CORRELATION.get(symbol, 0.0)
    if abs(correlation) < 0.50:
        return True, f"Weak DXY correlation ({correlation:.2f}), passing"

    if dxy_bull:
        expected = "SHORT" if correlation < 0 else "LONG"
    else:
        expected = "LONG" if correlation < 0 else "SHORT"

    if direction == expected:
        return True, f"DXY {'BULL' if dxy_bull else 'BEAR'} aligns with {direction}"
    return False, (f"DXY {'BULL' if dxy_bull else 'BEAR'} conflicts: "
                   f"expected {expected}, got {direction}")


def _pct_change_60d(df: "pd.DataFrame | None") -> float | None:
    """Return 60-bar percent change from Close, or None if insufficient data."""
    if df is None or len(df) < 60:
        return None
    try:
        close = df["Close"].astype(float)
        last = float(close.iloc[-1])
        prior = float(close.iloc[-60])
    except Exception:
        return None
    import math
    if not math.isfinite(last) or not math.isfinite(prior) or prior == 0:
        return None
    return (last / prior) - 1.0


def compute_etf_relative_strength_ranking(
    data: dict[str, "pd.DataFrame"] | None,
) -> dict[str, int] | None:
    """Compute the top-half ETF universe by 3-month relative strength vs SPY.

    Returns a dict mapping ETF symbol -> rank (1 = strongest), restricted to
    the TOP HALF of the universe. Returns None if SPY data is missing or has
    fewer than 60 bars (safe-default: pass-through in caller).

    Universe = symbols in `data` whose canonical ETF_SYMBOLS entry is present.
    Per the FOCUSED_NONCRYPTO_BACKTEST_REPORT_2026-04-07 ETF Relative Strength
    section (PF 1.55, Sharpe 2.57, 178 trades), trend leadership concentrated
    in GLD/XLK/QQQ/XLF/XLV is the cleanest ETF edge in the repo.
    """
    if not data:
        return None
    spy_df = data.get("SPY")
    spy_pct = _pct_change_60d(spy_df)
    if spy_pct is None:
        return None  # safe default → caller passes all picks

    rs_by_symbol: dict[str, float] = {}
    for sym in data.keys():
        if sym not in ETF_SYMBOLS:
            continue
        etf_pct = _pct_change_60d(data.get(sym))
        if etf_pct is None:
            continue
        rs_by_symbol[sym] = etf_pct - spy_pct

    if not rs_by_symbol:
        return None

    ranked = sorted(rs_by_symbol.items(), key=lambda kv: kv[1], reverse=True)
    half = max(1, (len(ranked) + 1) // 2)  # ceiling: top half (round up)
    return {sym: i + 1 for i, (sym, _rs) in enumerate(ranked[:half])}


def etf_relative_strength_gate(
    data: dict[str, "pd.DataFrame"] | None,
    symbol: str,
    top_half_ranking: dict[str, int] | None,
) -> tuple[bool, str]:
    """Block ETF picks whose 3-month relative strength vs SPY is below the
    universe median.

    Safe default: if `top_half_ranking` is None (SPY missing, insufficient
    bars, or empty universe), the gate passes the pick. The conservative
    posture matches the DXY/VIX gates — never hard-block on data shortage.
    """
    if top_half_ranking is None:
        return True, "ETF relative-strength data unavailable, passing"
    if symbol in top_half_ranking:
        rank = top_half_ranking[symbol]
        return True, f"ETF top-half leader (rank {rank}/{len(top_half_ranking)})"
    return False, f"ETF {symbol} below median 3m relative strength vs SPY"


def fetch_data(symbols: dict[str, dict], period: str = "1y") -> dict[str, pd.DataFrame]:
    """Fetch OHLCV data for non-crypto symbols.

    Also fetches ^VIX, SPY, and the DXY proxy if not already in symbols — all
    three are required by downstream gates (equity_macro_gate, vix_confidence_adj,
    dxy_macro_check). Without them gates fall through to safe defaults.
    """
    data: dict[str, pd.DataFrame] = {}
    all_syms = list(symbols.keys())
    # Ensure gate dependencies are always fetched
    for extra in ("^VIX", "SPY", DXY_TICKER):
        if extra not in all_syms:
            all_syms.append(extra)
    for sym in all_syms:
        try:
            ticker = yf.Ticker(sym)
            df = ticker.history(period=period)
            if not df.empty:
                data[sym] = df
        except Exception:
            continue
    return data


def generate_picks(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Run all non-crypto strategies."""
    picks: list[dict] = []

    picks += momentum_factor_12m(data)
    picks += penny_volume_breakout(data)
    picks += meme_social_velocity(data)
    picks += quality_value_composite(data)
    picks += intermarket_risk_on(data)
    picks += support_resistance_bounce(data)
    picks += equity_two_bar_rsi_reversal(data)  # opt-in EQUITY_RSI2_TWOBAR_ENABLED=1

    # PEAD equity strategy (opt-in via PEAD_EQUITY_ENABLED=1)
    # Default OFF: needs real earnings dates to be useful; backtest gate not yet cleared.
    try:
        import os as _os_pead
        if _os_pead.environ.get("PEAD_EQUITY_ENABLED", "0") not in ("0", "false"):
            from alpha_engine.strategies.pead_equity import generate_pead_signals
            _earnings = data.get("earnings_events", [])
            if not _earnings:
                import logging as _log_pead
                _log_pead.getLogger("non_crypto_agent").warning(
                    "PEAD_EQUITY_ENABLED=1 but no earnings_events in data — PEAD will emit 0 picks. "
                    "Wire an earnings data source (e.g. FRED, Yahoo Finance) to enable PEAD signals."
                )
            picks += generate_pead_signals(_earnings)
    except Exception as _pead_exc:
        pass  # fail-open: earnings data may not be available

    picks += carry_trade(data)
    picks += asian_range_breakout(data)
    picks += orb_breakout(data)
    # KILLED 2026-04-12: connors_rsi2_forex (see import block)
    # picks += connors_rsi2_forex(data)
    picks += cross_sectional_momentum_forex(data)
    picks += cot_positioning_forex(data)
    picks += london_session_breakout(data)
    picks += mean_reversion_200d(data)

    picks += seasonal_momentum(data)
    picks += gold_safe_haven(data)
    picks += oil_inventory_momentum(data)
    picks += metals_mean_reversion(data)
    picks += agricultural_spread(data)

    # Commodity carry+momentum double-sort sidecar (Fuertes/Miffre/Rallis 2010, opt-in
    # via COMMODITY_CARRY_MOMO_ENABLED=1). Long top-quintile both mom+carry, short bottom.
    # All picks tagged paper_trade=True — COMMODITY_FORCE_MONITOR=1 blocks real capital.
    try:
        import os as _os_ccm
        if _os_ccm.environ.get("COMMODITY_CARRY_MOMO_ENABLED", "0") not in ("0", "false", "FALSE", "False"):
            import sys as _sys_ccm
            from pathlib import Path as _Path_ccm
            _ccm_path = str(_Path_ccm(__file__).resolve().parent.parent / "tools" / "research")
            if _ccm_path not in _sys_ccm.path:
                _sys_ccm.path.insert(0, _ccm_path)
            from commodity_carry_momo import fetch_momentum_carry, double_sort_basket, DEFAULT_SYMBOLS as _CCM_SYMS
            _ccm_rows = fetch_momentum_carry(_CCM_SYMS)
            _ccm_basket = double_sort_basket(_ccm_rows, quintile=3)
            for _sym in _ccm_basket.get("longs", []):
                picks.append({"symbol": _sym, "direction": "LONG", "asset_class": "COMMODITY",
                              "strategy": "commodity_carry_momo_double_sort", "source_system": "carry_momo_sidecar",
                              "confidence": 0.55, "paper_trade": True})
            for _sym in _ccm_basket.get("shorts", []):
                picks.append({"symbol": _sym, "direction": "SHORT", "asset_class": "COMMODITY",
                              "strategy": "commodity_carry_momo_double_sort", "source_system": "carry_momo_sidecar",
                              "confidence": 0.55, "paper_trade": True})
    except Exception as _ccm_exc:
        import logging as _log_ccm
        _log_ccm.getLogger(__name__).debug("commodity_carry_momo sidecar skipped: %s", _ccm_exc)

    # ETF strategies (new — previously had no dedicated scanner, only 12 trades)
    picks += etf_dual_momentum(data)
    picks += etf_sector_momentum(data)
    picks += etf_risk_parity_rotation(data)
    picks += etf_trend_following(data)

    # Futures strategies (new — previously had only 3 trades, no dedicated strategies)
    picks += futures_tsmom(data)
    picks += futures_connors_rsi2(data)
    picks += futures_cross_asset_momentum(data)
    picks += futures_vol_regime_breakout(data)

    # Bond strategies — wired 2026-05-15 to grow BOND n from 11 toward T2 charter (100).
    # conf_floor=0.40 (matching futures low floor) in curate_quality_picks to unstarve tile.
    # bond_credit_spread_mean_reversion is opt-in (env BOND_ENABLE_CREDIT_SPREAD=1).
    picks += bond_yield_momentum(data)
    picks += bond_duration_rotation(data)
    picks += bond_mean_reversion(data)
    picks += bond_connors_rsi2(data)
    picks += bond_credit_spread_mean_reversion(data)
    picks += bond_yield_curve_slope(data)

    # Sector dual-momentum sidecar (Antonacci GEM 12-1, opt-in via ETF_SECTOR_DUALMO_ENABLED=1).
    # Emits paper_trade=True picks for top-3 SPDR sectors on positive SPY 12-1 momentum.
    # Wire-Up Rule: explicit opt-in sidecar per CLAUDE.md — no production capital gated.
    try:
        import os as _os_sdm
        if _os_sdm.environ.get("ETF_SECTOR_DUALMO_ENABLED", "0") not in ("0", "false", "FALSE", "False"):
            import sys as _sys_sdm
            from pathlib import Path as _Path_sdm
            _sdm_path = str(_Path_sdm(__file__).resolve().parent.parent / "tools" / "research")
            if _sdm_path not in _sys_sdm.path:
                _sys_sdm.path.insert(0, _sdm_path)
            from sector_dual_momentum import fetch_momentum_12_1, build_decision
            _DEFAULT_UNIVERSE = ["XLE", "XLF", "XLK", "XLV", "XLI", "XLP", "XLY", "XLU", "XLB", "SPY", "AGG"]
            _SECTORS = ["XLE", "XLF", "XLK", "XLV", "XLI", "XLP", "XLY", "XLU", "XLB"]
            _sdm_rows = fetch_momentum_12_1(_DEFAULT_UNIVERSE)
            _sdm_dec = build_decision(_sdm_rows, _SECTORS)
            if _sdm_dec.get("regime") == "risk_on":
                for _sdm_ticker in _sdm_dec.get("basket", []):
                    picks.append({
                        "symbol": _sdm_ticker,
                        "direction": "LONG",
                        "asset_class": "ETF",
                        "strategy": "sector_dual_momentum_12_1",
                        "source_system": "sector_dual_momentum_sidecar",
                        "confidence": 0.55,
                        "paper_trade": True,
                        "note": _sdm_dec.get("note", ""),
                    })
    except Exception as _sdm_exc:
        import logging as _log_sdm
        _log_sdm.getLogger(__name__).debug("sector_dual_momentum sidecar skipped: %s", _sdm_exc)

    return picks


def curate_quality_picks(picks: list[dict],
                         data: dict[str, pd.DataFrame] | None = None,
                         dxy_df: pd.DataFrame | None = None) -> tuple[list[dict], dict]:
    """Keep only paper-trade-worthy non-crypto picks and remove conflicts.

    Confidence floor by category:
      - forex / etf / commodity: 0.50  (unvalidated strategies capped at
        0.58 by quality gate — keeping them below the anti-predictive 0.6-0.7 band)
      - futures: 0.40  (2026-05-15: the FUTURES tile is starved at n=0 — the
        4 academic futures strategies are coded + wired but their raw signals
        could not clear the 0.50 floor, a self-fulfilling kill loop. Lowered to
        0.40 so signals reach shadow emission and n can accrue. All picks here
        are paper_trade=True — no capital is at risk.)
      - equity / stock: 0.55  (equity gate already hard-blocks bear market picks)
      - default: 0.55

    Forex picks additionally pass through dxy_macro_check — a hard gate
    requiring macro-DXY alignment when DXY has a clear trend and the pair has
    strong DXY correlation. Backed by FOCUSED_NONCRYPTO_BACKTEST_REPORT_2026-04-07
    which showed DXY-filtered forex (dxy_trend_filter) at PF 1.63 on 995 trades
    while generic reversal without macro alignment was the primary forex drag.

    All non-contrarian LONG picks additionally pass through vix_hard_block_gate —
    picks are hard-blocked when VIX > 30 unless their strategy is VIX-exempt
    (contrarian strategies designed for high-VIX conditions) or the pick is a
    SHORT. Complements the existing vix_confidence_adj soft-penalty with a
    visible hard-rejection counter.

    Every pick additionally passes through sl_distance_floor_gate — picks whose
    stop-loss distance (|entry - sl| / entry) falls below the per-asset-class
    floor are rejected. Backed by DEEPSEEK_APR122026.MD §6B (75.5% of trades
    hit SL) as the entry-side complement to PR #137's exit-side fix (partial
    TP + breakeven activation in forward_test_portfolios.py).

    This is intentionally LOWER than the live-trade threshold (0.70+).
    All picks produced here are paper_trade=True only.
    """
    _LOW_CONF_FLOOR = {
        "forex": 0.50,
        "etf": 0.50,
        "futures": 0.40,  # 2026-05-15: lowered 0.50->0.40 to unstarve the n=0 tile
        "bond": 0.40,     # 2026-05-15: low floor to grow BOND n from 11 toward T2 charter (100)
        "commodity": 0.50,
        "equity": 0.55,
        "stock": 0.55,
    }
    _DEFAULT_CONF_FLOOR = 0.55

    filtered: list[dict] = []
    rejected = {
        "low_confidence": 0,
        "low_rr": 0,
        "low_elite": 0,
        "dxy_macro": 0,
        "vix_panic": 0,
        "mtf_rsi": 0,
        "etf_weak_sector": 0,
        "sl_too_tight": 0,
        "direction_conflicts": 0,
        "duplicates": 0,
    }

    # Compute ETF top-half ranking ONCE for the whole batch (efficiency).
    # Returns None on insufficient data → safe-default pass for ETF picks.
    etf_top_half_ranking = compute_etf_relative_strength_ranking(data)

    for pick in picks:
        category = str(pick.get("category", "")).lower()
        conf_floor = _LOW_CONF_FLOOR.get(category, _DEFAULT_CONF_FLOOR)

        # Symbol-level PF boost: concentrate curation on backtest-validated
        # winners without hard-blocking unmapped symbols. Applied BEFORE the
        # elite_score floor check so tier-1/2 symbols get a head start toward
        # the threshold.
        symbol = str(pick.get("symbol", ""))
        pf_delta, pf_tier = symbol_pf_boost(symbol)
        pick["symbol_pf_tier"] = pf_tier
        if pf_delta:
            pick["elite_score"] = float(pick.get("elite_score", 0) or 0) + pf_delta

        confidence = float(pick.get("confidence", 0) or 0)
        rr = float(pick.get("risk_reward", 0) or 0)
        elite = float(pick.get("elite_score", 0) or 0)
        if confidence < conf_floor:
            rejected["low_confidence"] += 1
            continue
        if rr < _min_rr_for_pick(pick):
            rejected["low_rr"] += 1
            continue
        if elite < 55:
            rejected["low_elite"] += 1
            continue

        direction = _pick_direction(pick)

        # Mandatory DXY macro gate for forex picks
        if category == "forex":
            symbol = str(pick.get("symbol", ""))
            aligned, reason = dxy_macro_check(dxy_df, symbol, direction)
            if not aligned:
                rejected["dxy_macro"] += 1
                continue
            pick["dxy_filter"] = reason

        # Mandatory VIX hard-block gate for non-contrarian LONG picks
        if data is not None:
            strategy_name = str(pick.get("strategy") or pick.get("source") or "")
            allowed, vix_reason = vix_hard_block_gate(data, strategy_name, direction)
            if not allowed:
                rejected["vix_panic"] += 1
                continue
            pick["vix_gate"] = vix_reason

        # Multi-timeframe RSI confluence gate (conservative — blocks only on
        # clear higher-TF conflicts). Wired per GitHub agent code review
        # 2026-04-12 noting MTF-RSI features existed in signal_quality_ml.py
        # but were never enforced as a curation gate.
        if data is not None:
            symbol = str(pick.get("symbol", ""))
            signal_tf = str(pick.get("timeframe") or pick.get("interval") or "1d")
            mtf_ok, mtf_reason = mtf_rsi_confluence_gate(
                data, symbol, signal_tf, direction
            )
            if not mtf_ok:
                rejected["mtf_rsi"] += 1
                continue
            pick["mtf_rsi_gate"] = mtf_reason

        # Mandatory ETF relative-strength gate: only ETFs in the top half of
        # 3m RS-vs-SPY are kept. Backed by FOCUSED_NONCRYPTO_BACKTEST_REPORT_
        # 2026-04-07 ETF Relative Strength edge (PF 1.55, Sharpe 2.57, n=178)
        # where leadership concentrated in GLD/XLK/QQQ/XLF/XLV.
        if category == "etf":
            symbol = str(pick.get("symbol", ""))
            allowed, rs_reason = etf_relative_strength_gate(
                data, symbol, etf_top_half_ranking
            )
            if not allowed:
                rejected["etf_weak_sector"] += 1
                continue
            pick["etf_rs_gate"] = rs_reason

        # Mandatory SL-distance floor gate — reject tight stops that will be
        # noise-killed before any real move develops. Entry-side complement to
        # PR #137's exit-side partial-TP + breakeven activation fix.
        sl_ok, sl_reason = sl_distance_floor_gate(pick)
        if not sl_ok:
            rejected["sl_too_tight"] += 1
            continue
        pick["sl_distance_gate"] = sl_reason

        pick["paper_trade"] = True
        filtered.append(pick)

    grouped: dict[str, list[dict]] = {}
    for pick in filtered:
        grouped.setdefault(str(pick.get("symbol", "")), []).append(pick)

    curated: list[dict] = []
    for sym, group in grouped.items():
        directions = {_pick_direction(pick) for pick in group}
        if len(directions) > 1:
            # Direction conflict: keep the highest-scoring pick from the
            # majority direction instead of discarding all picks for that symbol.
            long_picks = [p for p in group if _pick_direction(p) == "LONG"]
            short_picks = [p for p in group if _pick_direction(p) == "SHORT"]
            majority = long_picks if len(long_picks) >= len(short_picks) else short_picks
            minority_count = len(group) - len(majority)
            rejected["direction_conflicts"] += minority_count
            majority.sort(key=_quality_rank, reverse=True)
            curated.append(majority[0])
            rejected["duplicates"] += max(0, len(majority) - 1)
        else:
            group.sort(key=_quality_rank, reverse=True)
            curated.append(group[0])
            rejected["duplicates"] += max(0, len(group) - 1)

    curated.sort(key=_quality_rank, reverse=True)
    return curated, rejected


def main() -> int:
    output_path = ROOT / "picks.json"

    print("Fetching non-crypto data...")
    data = fetch_data(NON_CRYPTO_SYMBOLS)
    print(f"Data for {len(data)} symbols.")

    print("Generating picks...")
    picks = generate_picks(data)

    print("Scoring with elite_scorer...")
    for pick in picks:
        pick.update(compute_elite_score(pick))

    quality_picks, rejected = curate_quality_picks(
        picks, data=data, dxy_df=data.get(DXY_TICKER)
    )

    # Per-asset-class breakdown for audit visibility
    by_category: dict[str, dict] = {}
    for pick in quality_picks:
        cat = str(pick.get("category", "unknown")).lower()
        entry = by_category.setdefault(cat, {"count": 0, "symbols": []})
        entry["count"] += 1
        sym = pick.get("symbol", "")
        if sym not in entry["symbols"]:
            entry["symbols"].append(sym)

    output = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "total_raw_picks": len(picks),
        "quality_picks": len(quality_picks),
        "rejected_counts": rejected,
        "by_category": by_category,
        "picks": quality_picks,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"Generated {len(quality_picks)} quality non-crypto picks -> {output_path.name}")
    print("By category:", {k: v["count"] for k, v in by_category.items()})
    print("Top 5 by elite_score:")
    for pick in quality_picks[:5]:
        print(
            f"  {pick['symbol']} [{pick.get('category','?')}] {pick['signal_type']} "
            f"({pick['confidence']:.2f} conf, {pick['elite_score']:.0f} elite)"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
