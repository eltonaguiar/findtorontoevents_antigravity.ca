#!/usr/bin/env python3
"""
Kelly Criterion position sizer — based on Kelly (1956) "A New Interpretation of Information Rate".

Bell Labs Technical Journal, Vol. 35, No. 4, pp. 917-926.
Core formula: f* = (p * b - q) / b  where p=win prob, q=1-p, b=net odds (payout ratio)
Continuous variant: f* = μ / σ²  (expected return over variance of returns)

In practice: fractional Kelly (Quarter-Kelly, fraction=0.25) is standard to account for
model uncertainty, estimation error, and non-stationarity of market edge.
Renaissance, Citadel, Jane Street all use Kelly-adjacent sizing internally.

## Wiring Plan
Target caller: alpha_engine/smart_picks_engine.py (score_pick → size_pick)
Wire-up: call kelly_fraction(pick) after scoring; pass result as pick["kelly_f"]
         and pick["kelly_size_pct"]. Import: from alpha_engine.kelly_position_sizer import size_pick
Expected PR/date: after ≥2-week shadow validation showing improved risk-adjusted returns
                  (target 2026-06-15). Shadow output written to tools/data/kelly_sizing_shadow.json.
"""
from __future__ import annotations

import json
import logging
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Asset-class defaults (conservative, post-resolver-v2, sourced from
# audit_dashboard/data/dashboard_data.json::performance.asset_class_health
# snapshot 2026-05-03T00:06Z + dedup-conservative adjustments)
# ---------------------------------------------------------------------------
_ASSET_CLASS_DEFAULTS: dict[str, dict] = {
    "CRYPTO": {
        "p_win": 0.446,      # WR 44.6% post-noise-filter
        "avg_win_pct": 3.2,
        "avg_loss_pct": 2.8,
    },
    "EQUITY": {
        "p_win": 0.527,      # WR 52.7%
        "avg_win_pct": 4.1,
        "avg_loss_pct": 3.2,
    },
    "ETF": {
        "p_win": 0.552,      # WR 55.2%
        "avg_win_pct": 3.8,
        "avg_loss_pct": 2.9,
    },
    "COMMODITY": {
        "p_win": 0.45,       # WR 46.9% post-dedup (conservative)
        "avg_win_pct": 5.2,
        "avg_loss_pct": 4.8,
    },
    "FOREX": {
        # Sub-floor (PF 0.27 / WR 46.4%) — mutation-before-kill protocol active.
        # Zero out: do not size FOREX picks until rescue plan validated.
        "p_win": 0.0,
        "avg_win_pct": 0.0,
        "avg_loss_pct": 0.0,
    },
    "BOND": {
        "p_win": 0.556,      # WR 55.6% (n=18 — below charter floor; treat as provisional)
        "avg_win_pct": 2.8,
        "avg_loss_pct": 3.1,
    },
}

_MAX_PORTFOLIO_PCT = 50.0   # Hard cap: total Kelly allocation ≤ 50% of bankroll


# ---------------------------------------------------------------------------
# Core Kelly functions
# ---------------------------------------------------------------------------

def kelly_fraction(
    p_win: float,
    avg_win_pct: float,
    avg_loss_pct: float,
    fraction: float = 0.25,
) -> float:
    """Compute fractional Kelly bet size for a discrete-outcome bet.

    Standard Kelly formula:
        f* = (p * b - q) / b

    where b = avg_win_pct / avg_loss_pct (the net odds ratio — how much you
    win relative to how much you risk), q = 1 - p_win.

    Args:
        p_win:        Probability of a winning trade (0-1).
        avg_win_pct:  Average win as a percentage (e.g. 4.1 means +4.1%).
        avg_loss_pct: Average loss as a percentage (e.g. 3.2 means -3.2%).
        fraction:     Kelly multiplier. 0.25 = Quarter-Kelly (default).

    Returns:
        Kelly fraction in [0, fraction]. Returns 0 for negative-edge setups.
    """
    if avg_win_pct <= 0 or avg_loss_pct <= 0:
        return 0.0
    if not (0.0 <= p_win <= 1.0):
        raise ValueError(f"p_win must be in [0, 1], got {p_win}")

    p_lose = 1.0 - p_win
    # b = net odds (win-to-loss ratio)
    b = avg_win_pct / avg_loss_pct

    # f* = (p * b - q) / b  ⟺  p - q/b
    raw_kelly = (p_win * b - p_lose) / b

    if raw_kelly <= 0:
        return 0.0  # No edge — skip this position

    return min(raw_kelly * fraction, fraction)


def continuous_kelly(
    mu: float,
    sigma: float,
    fraction: float = 0.25,
) -> float:
    """Compute fractional Kelly for continuous (log-normal) return streams.

    Continuous Kelly: f* = μ / σ²

    Used when you have empirical return series statistics rather than discrete
    win/loss pairs (e.g. equity curves, daily P&L distributions).

    Args:
        mu:       Expected return (e.g. 0.05 = 5% expected return).
        sigma:    Standard deviation of returns (same units as mu).
        fraction: Kelly multiplier. 0.25 = Quarter-Kelly (default).

    Returns:
        Kelly fraction in [0, fraction]. Returns 0 for zero/negative edge.
    """
    if sigma <= 0:
        raise ValueError(f"sigma must be > 0, got {sigma}")

    raw_kelly = mu / (sigma ** 2)

    if raw_kelly <= 0:
        return 0.0

    return min(raw_kelly * fraction, fraction)


# ---------------------------------------------------------------------------
# Pick-level sizing
# ---------------------------------------------------------------------------

def size_pick(
    pick: dict,
    bankroll: float = 10_000.0,
    fraction: float = 0.25,
) -> dict:
    """Enrich a pick dict with Kelly-based position sizing.

    Reads pick["win_rate"] (0-1), pick["avg_win_pct"], pick["avg_loss_pct"].
    Falls back to asset-class defaults from _ASSET_CLASS_DEFAULTS if any field
    is missing or None.

    Args:
        pick:      A pick dict as produced by smart_picks_engine.py.
        bankroll:  Total account equity in USD (default 10,000).
        fraction:  Kelly multiplier applied to all classes (default 0.25).

    Returns:
        The same pick dict (mutated in-place, also returned) with added keys:
            kelly_f         — raw fractional Kelly fraction (e.g. 0.0624)
            kelly_size_pct  — percent of bankroll to risk (kelly_f * 100)
            kelly_size_usdc — dollar amount at given bankroll
            kelly_edge      — expected edge per unit risked (p*b - q)
            kelly_method    — "discrete" (always for this function)
    """
    asset_class = str(pick.get("asset_class") or pick.get("class") or "").upper()
    defaults = _ASSET_CLASS_DEFAULTS.get(asset_class, _ASSET_CLASS_DEFAULTS["EQUITY"])

    p_win = pick.get("win_rate")
    avg_win = pick.get("avg_win_pct")
    avg_loss = pick.get("avg_loss_pct")
    defaults_used = False

    # Fall back to class defaults for any missing field
    if p_win is None or avg_win is None or avg_loss is None:
        p_win = defaults["p_win"]
        avg_win = defaults["avg_win_pct"]
        avg_loss = defaults["avg_loss_pct"]
        defaults_used = True

    # Compute raw Kelly edge  (p * b - q)  before fractioning
    if avg_win > 0 and avg_loss > 0:
        b = avg_win / avg_loss
        p_lose = 1.0 - p_win
        edge = p_win * b - p_lose
    else:
        edge = 0.0

    kf = kelly_fraction(p_win, avg_win, avg_loss, fraction=fraction)

    pick["kelly_f"] = round(kf, 6)
    pick["kelly_size_pct"] = round(kf * 100, 4)
    pick["kelly_size_usdc"] = round(kf * bankroll, 2)
    pick["kelly_edge"] = round(edge, 6)
    pick["kelly_method"] = "discrete"
    pick["_kelly_defaults_used"] = defaults_used

    if defaults_used:
        log.debug(
            "kelly size_pick: used %s class defaults for %s",
            asset_class or "EQUITY",
            pick.get("symbol", "?"),
        )

    return pick


# ---------------------------------------------------------------------------
# Portfolio-level batch sizing
# ---------------------------------------------------------------------------

def batch_size_picks(
    picks: list[dict],
    bankroll: float = 10_000.0,
    fraction: float = 0.25,
) -> list[dict]:
    """Apply size_pick to every pick, then enforce ≤50% total portfolio exposure.

    Kelly portfolio theory: when multiple simultaneous bets exist, the joint
    optimal fraction is bounded — exceeding 50% total exposure violates the
    Kelly portfolio convexity constraint for uncorrelated bets.

    Args:
        picks:    List of pick dicts (as from smart_picks_engine.py).
        bankroll: Total account equity in USD.
        fraction: Kelly multiplier (0.25 = Quarter-Kelly).

    Returns:
        List of sized pick dicts. If total kelly_size_pct > 50%, all positions
        are scaled proportionally so the total equals exactly 50%.
    """
    sized: list[dict] = []
    for p in picks:
        sized.append(size_pick(p, bankroll=bankroll, fraction=fraction))

    total_pct = sum(p.get("kelly_size_pct", 0.0) for p in sized)

    if total_pct > _MAX_PORTFOLIO_PCT:
        scale = _MAX_PORTFOLIO_PCT / total_pct
        log.info(
            "kelly batch: total %.2f%% > 50%% cap — scaling all by %.4f",
            total_pct,
            scale,
        )
        for p in sized:
            p["kelly_size_pct"] = round(p["kelly_size_pct"] * scale, 4)
            p["kelly_size_usdc"] = round(p["kelly_size_pct"] / 100 * bankroll, 2)
            p["kelly_f"] = round(p["kelly_size_pct"] / 100, 6)
            p["_kelly_portfolio_scaled"] = True

    return sized


# ---------------------------------------------------------------------------
# Vol-adjusted sizing  (Rob Carver / HyroTrader target-vol approach)
# ---------------------------------------------------------------------------

def vol_adjusted_size(
    base: float,
    atr_pct: float,
    target_vol: float = 0.15,
    min_scale: Optional[float] = None,
) -> float:
    """Scale a base position to hit a target annualized volatility.

    realized_vol = atr_pct * sqrt(365)
    vol_scale    = target_vol / realized_vol
    A floor (min_scale) prevents near-zero sizing on extreme-vol assets.
    min_scale defaults to KELLY_VOL_MIN_SCALE env (default 0.05, pre-fix was 0.25).
    min_scale itself is safety-clamped to [0.01, 1.0].
    """
    if atr_pct <= 0:
        return base

    realized_vol = atr_pct * math.sqrt(365)
    if realized_vol <= 0:
        return base

    vol_scale = target_vol / realized_vol

    if min_scale is None:
        env_val = os.environ.get("KELLY_VOL_MIN_SCALE", "0.05").strip()
        try:
            min_scale = float(env_val) if env_val else 0.05
        except (ValueError, TypeError):
            min_scale = 0.05

    min_scale = max(0.01, min(1.0, min_scale))  # safety clamp
    return base * max(min_scale, vol_scale)


# ---------------------------------------------------------------------------
# Drawdown-halt + Hyro overlay composite sizer
# ---------------------------------------------------------------------------

def _apply_hyro_risk_sizer(
    pick: dict,
    portfolio_value: float,
    target_risk_pct: float,
    today_pnl: float,
) -> Optional[float]:
    """Try the Hyro overlay. Returns sized USD, 0.0 on soft-stop, None on error."""
    try:
        from tools.hyrotrader_risk_sizer import size_pick as hyro_size  # noqa: PLC0415
    except ImportError as exc:
        log.warning(
            "Hyro overlay import failed — falling back to legacy Kelly sizing. "
            "ImportError: %s",
            exc,
        )
        return None

    try:
        result = hyro_size(
            pick,
            account_balance=portfolio_value,
            target_risk_pct=target_risk_pct,
            todays_realized_pnl_pct=today_pnl,
        )
    except Exception as exc:
        log.warning(
            "Hyro size_pick raised %s — falling back to legacy Kelly sizing. "
            "RuntimeError: %s",
            type(exc).__name__,
            exc,
        )
        return None

    if not result.get("passed", True):
        pick["hyro_reject_reasons"] = result.get("reject_reasons", [])
        return 0.0

    hyro_usd = float(result.get("size_usd", 0.0))
    pick["hyro_size_usd"] = hyro_usd
    return hyro_usd


def compute_position_size(
    pick: dict,
    stats: dict,
    active_picks: Optional[list] = None,
    portfolio_value: float = 10_000.0,
) -> float:
    """Compute a USD position size with drawdown halt and optional Hyro overlay.

    Pipeline:
      1. DD halt: KELLY_DD_HALT_ENABLED=1 + rolling_dd_30d > KELLY_DD_HALT_MAX → 0.
      2. Base Kelly from stats {win_rate, avg_win_pct, avg_loss_pct}.
      3. Hyro overlay: HYRO_RISK_SIZER_ENABLED=1 → prop-safe vol-scaled cap.
    """
    if active_picks is None:
        active_picks = []

    # 1. Drawdown halt
    if os.environ.get("KELLY_DD_HALT_ENABLED", "0").strip() == "1":
        dd_max_raw = os.environ.get("KELLY_DD_HALT_MAX", "0.30").strip()
        try:
            dd_halt_max = float(dd_max_raw) if dd_max_raw else 0.30
        except (ValueError, TypeError):
            dd_halt_max = 0.30
        dd_halt_max = max(0.01, min(0.95, dd_halt_max))

        rolling_dd = float((pick.get("extra") or {}).get("rolling_dd_30d", 0.0) or 0.0)
        if rolling_dd > dd_halt_max:
            pick["dd_halt_triggered"] = True
            return 0.0

    # 2. Base Kelly sizing
    p_win = float(stats.get("win_rate", 0.5))
    avg_win = float(stats.get("avg_win_pct", 3.0))
    avg_loss = float(stats.get("avg_loss_pct", 3.0))
    kf = kelly_fraction(p_win, avg_win, avg_loss, fraction=0.25)
    base_size_usd = kf * portfolio_value

    # 3. Hyro overlay (optional)
    if os.environ.get("HYRO_RISK_SIZER_ENABLED", "0").strip() == "1":
        try:
            trp = float(os.environ.get("HYRO_TARGET_RISK_PCT", "0.75"))
        except (ValueError, TypeError):
            trp = 0.75
        try:
            pnl = float(os.environ.get("HYRO_TODAY_PNL_PCT", "0.0"))
        except (ValueError, TypeError):
            pnl = 0.0
        hyro_result = _apply_hyro_risk_sizer(pick, portfolio_value, trp, pnl)
        if hyro_result is not None:
            return hyro_result

    return base_size_usd


# ---------------------------------------------------------------------------
# Convenience: update shadow log
# ---------------------------------------------------------------------------

_SHADOW_PATH = (
    Path(__file__).resolve().parent.parent / "tools" / "data" / "kelly_sizing_shadow.json"
)


def update_shadow_log(
    sized_picks: list[dict],
    bankroll: float = 10_000.0,
    fraction: float = 0.25,
) -> None:
    """Append a shadow run record to tools/data/kelly_sizing_shadow.json.

    Does NOT raise on failure — shadow logging is best-effort.
    """
    try:
        shadow: dict = {}
        if _SHADOW_PATH.exists():
            with open(_SHADOW_PATH, "r", encoding="utf-8") as fh:
                shadow = json.load(fh)

        total_pct = sum(p.get("kelly_size_pct", 0.0) for p in sized_picks)
        scaled = any(p.get("_kelly_portfolio_scaled") for p in sized_picks)
        defaults_count = sum(1 for p in sized_picks if p.get("_kelly_defaults_used"))
        skipped = sum(1 for p in sized_picks if p.get("kelly_f", 0) == 0)

        shadow["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        shadow["bankroll_default"] = bankroll
        shadow["fraction"] = fraction
        shadow["picks_sized"] = len(sized_picks)
        shadow["picks_skipped_negative_edge"] = skipped
        shadow["asset_class_defaults_used"] = defaults_count
        shadow["portfolio_scaled"] = scaled
        shadow["total_portfolio_pct"] = round(total_pct, 4)
        shadow["picks"] = [
            {
                k: v
                for k, v in p.items()
                if k.startswith("kelly_") or k in ("symbol", "asset_class")
            }
            for p in sized_picks
        ]

        with open(_SHADOW_PATH, "w", encoding="utf-8") as fh:
            json.dump(shadow, fh, indent=2)
    except Exception as exc:  # pragma: no cover
        log.warning("kelly shadow log update failed: %s", exc)


# ---------------------------------------------------------------------------
# Drawdown-halt wrapper (test-facing public API)
# ---------------------------------------------------------------------------

def _parse_dd_halt_max() -> float:
    """Parse KELLY_DD_HALT_MAX env; fallback 0.30, clamped to [0.01, 0.95]."""
    raw = os.environ.get("KELLY_DD_HALT_MAX", "0.30").strip()
    try:
        val = float(raw)
    except (ValueError, TypeError):
        val = 0.30
    return max(0.01, min(0.95, val))


def _apply_hyro_risk_sizer(
    pick: dict,
    legacy_size_usd: float,
    portfolio_value: float,
    target_risk_pct: float = 0.75,
    today_pnl: float = 0.0,
) -> float:
    """Apply the Hyro risk-sizer overlay. Returns final USD size.

    Logs WARNING on import or runtime failure and falls back to legacy_size_usd.
    Sets pick["hyro_size_usd"] on success, pick["hyro_reject_reasons"] on reject.
    """
    try:
        from tools.hyrotrader_risk_sizer import size_pick as _hyro_size  # type: ignore
    except (ImportError, AttributeError) as exc:
        log.warning(
            "Hyro overlay import failed — falling back to legacy Kelly sizing. "
            "ImportError: %s",
            exc,
        )
        return legacy_size_usd

    try:
        result = _hyro_size(
            pick,
            account_balance=portfolio_value,
            target_risk_pct=target_risk_pct,
            todays_realized_pnl_pct=today_pnl,
        )
        # Hyro rejects: passed=False, reject_reasons populated
        if not result.get("passed", True):
            pick["hyro_reject_reasons"] = result.get("reject_reasons", [])
            return 0.0
        hyro_usd = float(result.get("size_usd", legacy_size_usd))
        pick["hyro_size_usd"] = hyro_usd
        return min(legacy_size_usd, hyro_usd)
    except Exception as exc:
        log.warning(
            "Hyro size_pick raised %s — falling back to legacy Kelly sizing. "
            "RuntimeError: %s",
            type(exc).__name__,
            exc,
        )
        return legacy_size_usd


def compute_position_size(
    pick: dict,
    stats: dict,
    active_picks: list | None = None,
    portfolio_value: float = 10_000.0,
    fraction: float = 0.25,
) -> float:
    """Compute Kelly position size (USD) with drawdown-halt guard and Hyro overlay.

    Args:
        pick:            Pick dict; reads pick["extra"]["rolling_dd_30d"].
        stats:           {"win_rate": float, "avg_win_pct": float, "avg_loss_pct": float}.
        active_picks:    Reserved for concentration-cap callers (not used here).
        portfolio_value: Total account equity in USD (default 10,000).
        fraction:        Kelly multiplier (default 0.25).

    Returns:
        Position size in USD (0.0 = no trade).
        Sets pick["dd_halt_triggered"] = True when DD halt fires.

    Env vars:
        KELLY_DD_HALT_ENABLED:  "1" to enable drawdown halt (default "0").
        KELLY_DD_HALT_MAX:      max 30d rolling drawdown before halt (default "0.30").
                                Invalid values fall back to 0.30; clamped to [0.01, 0.95].
        HYRO_RISK_SIZER_ENABLED:"1" to enable the Hyro overlay (default "0").
    """
    # ── Drawdown-halt guard ──
    if os.environ.get("KELLY_DD_HALT_ENABLED", "0") == "1":
        dd_max = _parse_dd_halt_max()
        rolling_dd = float((pick.get("extra") or {}).get("rolling_dd_30d", 0.0))
        if rolling_dd >= dd_max:
            pick["dd_halt_triggered"] = True
            return 0.0

    # ── Compute legacy Kelly size ──
    _merged = dict(pick)
    _merged["win_rate"] = stats.get("win_rate")
    _merged["avg_win_pct"] = stats.get("avg_win_pct")
    _merged["avg_loss_pct"] = stats.get("avg_loss_pct")
    sized = size_pick(_merged, bankroll=portfolio_value, fraction=fraction)
    for k in ("kelly_f", "kelly_size_pct", "kelly_size_usdc", "kelly_edge", "kelly_method"):
        if k in sized:
            pick[k] = sized[k]
    legacy_usd = sized.get("kelly_size_usdc", 0.0)

    # ── Optional Hyro overlay ──
    if os.environ.get("HYRO_RISK_SIZER_ENABLED", "0") == "1":
        try:
            trp = float(os.environ.get("HYRO_TARGET_RISK_PCT", "0.75"))
        except (ValueError, TypeError):
            trp = 0.75
        try:
            pnl = float(os.environ.get("HYRO_TODAY_PNL_PCT", "0.0"))
        except (ValueError, TypeError):
            pnl = 0.0
        return _apply_hyro_risk_sizer(pick, legacy_usd, portfolio_value, trp, pnl)

    return legacy_usd


# ---------------------------------------------------------------------------
# Tiered conviction sizing (2026-05-17, swarm recommendation)
# ---------------------------------------------------------------------------

def equity_conviction_multiplier(score: float) -> float:
    """Return a sizing multiplier for EQUITY picks based on conviction score.

    Concentrates capital in high-conviction picks to push PF toward T1 (>2).
    Applied on top of the base Kelly fraction. Env-gated: EQUITY_CONVICTION_TIERS=1.

    Tiers (configurable via EQUITY_CONVICTION_TIER_* env vars):
      HIGH  (score > 80): 1.5x — strong forward-validated signal
      MED   (score 60-80): 1.0x — standard sizing
      LOW   (score < 60):  0.5x — half-size for lower-conviction picks

    Returns 1.0 (no change) when EQUITY_CONVICTION_TIERS != "1" or on any error.
    """
    try:
        import os
        if os.environ.get("EQUITY_CONVICTION_TIERS", "0") != "1":
            return 1.0
        from alpha_engine.config import (
            EQUITY_CONVICTION_TIER_HIGH_SCORE,
            EQUITY_CONVICTION_TIER_HIGH_MULT,
            EQUITY_CONVICTION_TIER_MED_SCORE,
            EQUITY_CONVICTION_TIER_MED_MULT,
            EQUITY_CONVICTION_TIER_LOW_MULT,
        )
        if score >= EQUITY_CONVICTION_TIER_HIGH_SCORE:
            return float(EQUITY_CONVICTION_TIER_HIGH_MULT)
        if score >= EQUITY_CONVICTION_TIER_MED_SCORE:
            return float(EQUITY_CONVICTION_TIER_MED_MULT)
        return float(EQUITY_CONVICTION_TIER_LOW_MULT)
    except Exception:
        return 1.0  # fail-open: no tiering if config unavailable


# ---------------------------------------------------------------------------
# Self-test / __main__
# ---------------------------------------------------------------------------

def _self_test() -> None:
    """Run quick sanity checks with known analytical results."""
    failures: list[str] = []

    # --- Test 1: Classic Kelly p=0.6, even odds (b=1.0) ---
    # Full Kelly: f* = (0.6*1 - 0.4) / 1 = 0.20
    # Quarter-Kelly: 0.20 * 0.25 = 0.05
    result = kelly_fraction(p_win=0.6, avg_win_pct=1.0, avg_loss_pct=1.0, fraction=0.25)
    expected = 0.05
    if abs(result - expected) > 1e-9:
        failures.append(
            f"Test 1 FAIL: kelly_fraction(0.6,1,1,0.25)={result}, want {expected}"
        )
    else:
        print(
            f"  [PASS] kelly_fraction(p=0.6, b=1.0, frac=0.25) = {result:.4f}"
            f"  (expected {expected})"
        )

    # --- Test 2: Full Kelly baseline (fraction=1.0) ---
    full = kelly_fraction(p_win=0.6, avg_win_pct=1.0, avg_loss_pct=1.0, fraction=1.0)
    if abs(full - 0.20) > 1e-9:
        failures.append(f"Test 2 FAIL: full kelly={full}, want 0.20")
    else:
        print(
            f"  [PASS] kelly_fraction(p=0.6, b=1.0, frac=1.0)  = {full:.4f}"
            f"  (expected 0.2000)"
        )

    # --- Test 3: Negative edge → 0 ---
    neg = kelly_fraction(p_win=0.3, avg_win_pct=1.0, avg_loss_pct=1.0, fraction=0.25)
    if neg != 0.0:
        failures.append(f"Test 3 FAIL: negative-edge kelly={neg}, want 0.0")
    else:
        print(
            f"  [PASS] kelly_fraction(p=0.3, b=1.0, frac=0.25) = {neg:.4f}"
            f"  (expected 0.0, no edge)"
        )

    # --- Test 4: FOREX defaults → kelly_f = 0 (class is sub-floor) ---
    forex_pick = {"symbol": "EURUSD", "asset_class": "FOREX"}
    size_pick(forex_pick)
    if forex_pick["kelly_f"] != 0.0:
        failures.append(
            f"Test 4 FAIL: FOREX kelly_f={forex_pick['kelly_f']}, want 0.0"
        )
    else:
        print(
            f"  [PASS] FOREX pick kelly_f=0 (sub-floor class correctly zeroed out)"
        )

    # --- Test 5: EQUITY defaults produce positive sizing ---
    eq_pick = {"symbol": "AAPL", "asset_class": "EQUITY"}
    size_pick(eq_pick)
    if eq_pick["kelly_f"] <= 0:
        failures.append(
            f"Test 5 FAIL: EQUITY kelly_f={eq_pick['kelly_f']}, want > 0"
        )
    else:
        print(
            f"  [PASS] EQUITY pick kelly_f={eq_pick['kelly_f']:.4f}"
            f"  size={eq_pick['kelly_size_pct']:.2f}%"
            f"  ${eq_pick['kelly_size_usdc']:.2f}"
        )

    # --- Test 6: continuous_kelly ---
    # f* = 0.10 / (0.20^2) = 0.10 / 0.04 = 2.5 → clamped to fraction=0.25
    ck = continuous_kelly(mu=0.10, sigma=0.20, fraction=0.25)
    if abs(ck - 0.25) > 1e-9:
        failures.append(f"Test 6 FAIL: continuous_kelly clamped={ck}, want 0.25")
    else:
        print(
            f"  [PASS] continuous_kelly(mu=0.10, σ=0.20, frac=0.25) = {ck:.4f}"
            f"  (clamped to fraction)"
        )

    # f* = 0.02 / (0.20^2) = 0.02 / 0.04 = 0.50 * 0.25 = 0.125
    ck2 = continuous_kelly(mu=0.02, sigma=0.20, fraction=0.25)
    if abs(ck2 - 0.125) > 1e-9:
        failures.append(f"Test 6b FAIL: continuous_kelly={ck2}, want 0.125")
    else:
        print(
            f"  [PASS] continuous_kelly(mu=0.02, σ=0.20, frac=0.25) = {ck2:.4f}"
            f"  (expected 0.1250)"
        )

    # --- Test 7: batch_size_picks portfolio cap ---
    # 20 EQUITY picks with explicit high-edge params — total must be ≤ 50%
    many_picks = [
        {
            "symbol": f"EQ{i}",
            "asset_class": "EQUITY",
            "win_rate": 0.6,
            "avg_win_pct": 5.0,
            "avg_loss_pct": 3.0,
        }
        for i in range(20)
    ]
    sized = batch_size_picks(many_picks, bankroll=10_000.0, fraction=0.25)
    total = sum(p["kelly_size_pct"] for p in sized)
    if total > 50.0 + 1e-6:
        failures.append(
            f"Test 7 FAIL: batch total={total:.2f}%, must be ≤50%"
        )
    else:
        print(
            f"  [PASS] batch_size_picks (n=20): total={total:.2f}%  ≤ 50% cap enforced"
        )

    # --- Summary ---
    print()
    if failures:
        print(f"SELF-TEST FAILED ({len(failures)} failure(s)):")
        for f in failures:
            print(f"  {f}")
        raise SystemExit(1)
    else:
        print("All self-tests passed.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print("Kelly Criterion Position Sizer — Self-Test")
    print("=" * 50)
    _self_test()
