"""
ALPHA_ENGINE -- crypto_pairs_arb (Statistical Arbitrage on Cointegrated Crypto Majors)
======================================================================================

Classic Engle-Granger statistical arbitrage on log-spread of cointegrated CRYPTO
majors. Fills the production gap flagged in
`docs/strategy-audit-rounds/COVERAGE_VALIDATION_2026-05-09.md` where the
`statistical_arbitrage_pairs` slot was cycled in audit-round boilerplate but
had no real production implementation. This module IS the production
implementation -- pure numpy + pandas, no statsmodels, no scipy.

Pairs (must be present in `data` dict to fire):
    BTCUSDT / ETHUSDT
    ETHUSDT / SOLUSDT
    BTCUSDT / BNBUSDT

Method
------
1. Compute log-prices ln(A), ln(B). Align lengths.
2. Hedge ratio beta = OLS slope from rolling 60-bar window via numpy.linalg.lstsq.
   Spread_t = ln(A_t) - beta * ln(B_t).
3. Half-life filter (cointegration proxy without scipy):
       Fit AR(1): spread_t - mu = phi * (spread_{t-1} - mu) + eps
       half_life = -ln(2) / ln(phi)   when 0 < phi < 1
   Skip pairs whose half-life > 30 bars (no usable mean reversion) OR
   phi >= 1 (non-stationary / divergent).
4. z-score = (spread_now - spread_mu) / spread_sigma  on the same 60-bar window.
5. Entry:  z >  2.0  -> SHORT leg-A (overpriced) + LONG leg-B  (1 pair_id, 2 picks)
           z < -2.0  -> LONG  leg-A (underpriced) + SHORT leg-B (1 pair_id, 2 picks)
6. Exit (TP): price level on each leg implied by spread reverting to z=0.
   Stop: 3% adverse move per leg.
7. Confidence = clamp(|z| / 4.0, 0, 0.95).

Why crypto majors are good candidates: BTC, ETH, SOL, BNB share common
risk factors (overall crypto beta, BTC dominance regime, USD liquidity,
funding rates, exchange-listing tier). Their spreads have historically
exhibited regime-conditional cointegration (Engle-Granger 1987 framework
applied to crypto e.g. Vidyamurthy-style log-spread; see references in
docs/strategy-audit-rounds/statistical_arbitrage_pairs/strategy.md).

Rollback
--------
Set env `CRYPTO_PAIRS_ARB_DISABLED=1` to no-op the whole module
(returns empty list immediately). Use this for fast revert without a
full deploy.

Wiring Plan
-----------
STATUS: WIRED (T2.3, 2026-05-09). Registered into
`alpha_engine/proven_research_strategies.py::PROVEN_RESEARCH_STRATEGIES`
via best-effort import + idempotent dict assignment guarded by module's
own `CRYPTO_PAIRS_ARB_DISABLED=1` rollback. The registry is iterated by
`alpha_engine/scanner.py` (CRYPTO_STRATEGIES.update(PROVEN_RESEARCH_STRATEGIES)
at crypto_strategies.py:4307) and consumed by
`alpha_engine/smart_picks_engine.py` + `alpha_engine/production_scanner.py`.
Scanner's invocation pattern falls through to `func(data)` since this
function exposes only `**kwargs` (no `context` named param) -- compatible.

Follow-ups (not yet wired):
    1. Audit: after 7 days of shadow runs, gate flip default-on requires
       n>=20 closed trades and PF >= 1.2 (per audit_dashboard).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


STRATEGY_NAME = "crypto_pairs_arb"
ASSET_CLASS = "CRYPTO"

# Candidate pairs (leg_a, leg_b). Only fires when BOTH legs are in `data`.
CANDIDATE_PAIRS: List[Tuple[str, str]] = [
    ("BTCUSDT", "ETHUSDT"),
    ("ETHUSDT", "SOLUSDT"),
    ("BTCUSDT", "BNBUSDT"),
]

WINDOW = 60                 # OLS + z-score lookback
ENTRY_Z = 2.0               # |z| entry threshold
EXIT_Z = 0.0                # mean-reversion target
MAX_HALF_LIFE = 30          # bars; reject pairs with weak/no mean-reversion
STOP_PCT = 0.03             # 3% adverse stop per leg
CONF_DIVISOR = 4.0          # confidence = |z|/4 capped at 0.95
CONF_CAP = 0.95
MIN_BARS = WINDOW           # graceful no-op if either leg has < 60 bars


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    if value == 0 or not np.isfinite(value):
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    if abs_val >= 1:
        return round(value, 4)
    if abs_val >= 0.01:
        return round(value, 6)
    return round(value, 10)


def _ols_hedge_ratio(log_a: np.ndarray, log_b: np.ndarray) -> float:
    """Beta from log_a = alpha + beta*log_b via numpy.linalg.lstsq.
    Returns 0.0 if singular / non-finite."""
    if log_a.size < 2 or log_b.size < 2:
        return 0.0
    X = np.column_stack([np.ones_like(log_b), log_b])
    try:
        coef, *_ = np.linalg.lstsq(X, log_a, rcond=None)
    except np.linalg.LinAlgError:
        return 0.0
    beta = float(coef[1])
    if not np.isfinite(beta):
        return 0.0
    return beta


def _half_life(spread: np.ndarray) -> float:
    """AR(1) half-life proxy. Returns +inf if non-stationary / non-finite."""
    if spread.size < 5:
        return float("inf")
    s = spread - np.mean(spread)
    s_lag = s[:-1]
    s_now = s[1:]
    denom = float(np.dot(s_lag, s_lag))
    if denom <= 0:
        return float("inf")
    phi = float(np.dot(s_lag, s_now) / denom)
    if not np.isfinite(phi) or phi <= 0 or phi >= 1:
        return float("inf")
    return float(-np.log(2.0) / np.log(phi))


def _spread_stats(log_a: np.ndarray, log_b: np.ndarray, beta: float) -> Tuple[np.ndarray, float, float]:
    spread = log_a - beta * log_b
    mu = float(np.mean(spread))
    sigma = float(np.std(spread, ddof=1)) if spread.size > 1 else 0.0
    return spread, mu, sigma


def _make_pick(
    pair_id: str,
    leg_role: str,            # "A" or "B"
    symbol: str,
    direction: str,           # "LONG" or "SHORT"
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    confidence: float,
    z_score: float,
    beta: float,
    half_life_bars: float,
    other_symbol: str,
) -> Dict:
    return {
        "strategy": STRATEGY_NAME,
        "asset_class": ASSET_CLASS,
        "category": "crypto",
        "symbol": symbol,
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": _smart_round(entry_price),
        "stop_loss": _smart_round(stop_loss),
        "take_profit": _smart_round(take_profit),
        "confidence": round(float(confidence), 3),
        "pair_id": pair_id,
        "pair_leg": leg_role,
        "pair_partner": other_symbol,
        "hedge_ratio": round(float(beta), 6),
        "z_score": round(float(z_score), 4),
        "half_life_bars": round(float(half_life_bars), 2),
        "timeframe": "1h",
        "reason": (
            f"pairs_arb {pair_id} z={z_score:+.2f} beta={beta:.3f} "
            f"hl={half_life_bars:.1f} -> {direction} {symbol}"
        ),
        "timestamp": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def crypto_pairs_arb(data: Dict[str, pd.DataFrame], **kwargs) -> List[Dict]:
    """Statistical arbitrage entry on cointegrated crypto-majors log-spread.

    Args:
        data: mapping symbol -> OHLCV DataFrame with at least `close` column.
        **kwargs: ignored (context, etc.) for forward-compat with the
            (data, context) signature used by proven_research_strategies.py.

    Returns:
        list of pick dicts. Each fired pair contributes exactly 2 picks
        sharing a `pair_id`. Empty list if no pair fires or env disabled.
    """
    if os.environ.get("CRYPTO_PAIRS_ARB_DISABLED") == "1":
        return []

    if not isinstance(data, dict) or not data:
        return []

    out: List[Dict] = []

    for sym_a, sym_b in CANDIDATE_PAIRS:
        df_a = data.get(sym_a)
        df_b = data.get(sym_b)
        if df_a is None or df_b is None:
            continue
        if not isinstance(df_a, pd.DataFrame) or not isinstance(df_b, pd.DataFrame):
            continue
        if "close" not in df_a.columns or "close" not in df_b.columns:
            continue
        if len(df_a) < MIN_BARS or len(df_b) < MIN_BARS:
            continue

        # Align tail windows.
        n = min(len(df_a), len(df_b), WINDOW)
        if n < MIN_BARS:
            continue
        ca = df_a["close"].iloc[-n:].astype(float).to_numpy()
        cb = df_b["close"].iloc[-n:].astype(float).to_numpy()
        if np.any(ca <= 0) or np.any(cb <= 0):
            continue
        if not (np.all(np.isfinite(ca)) and np.all(np.isfinite(cb))):
            continue

        log_a = np.log(ca)
        log_b = np.log(cb)

        beta = _ols_hedge_ratio(log_a, log_b)
        if beta == 0.0 or not np.isfinite(beta):
            continue

        spread, mu, sigma = _spread_stats(log_a, log_b, beta)
        if sigma <= 0 or not np.isfinite(sigma):
            continue

        hl = _half_life(spread)
        if not np.isfinite(hl) or hl > MAX_HALF_LIFE:
            continue

        z_now = float((spread[-1] - mu) / sigma)
        if not np.isfinite(z_now) or abs(z_now) < ENTRY_Z:
            continue

        # Direction: z>0 -> A overpriced vs B -> SHORT A, LONG B.
        if z_now > 0:
            dir_a, dir_b = "SHORT", "LONG"
        else:
            dir_a, dir_b = "LONG", "SHORT"

        price_a = float(ca[-1])
        price_b = float(cb[-1])

        # TP: implied price when spread mean-reverts to z=0 (mu).
        # log_a' = mu + beta * log_b -> tp_a = exp(mu + beta * ln(price_b)).
        # log_b' = (log_a - mu) / beta -> tp_b = exp((ln(price_a) - mu) / beta).
        try:
            tp_a = float(np.exp(mu + beta * np.log(price_b)))
        except (OverflowError, ValueError):
            tp_a = price_a
        if beta != 0:
            try:
                tp_b = float(np.exp((np.log(price_a) - mu) / beta))
            except (OverflowError, ValueError):
                tp_b = price_b
        else:
            tp_b = price_b

        # Stop: 3% adverse per leg.
        if dir_a == "LONG":
            sl_a = price_a * (1 - STOP_PCT)
        else:
            sl_a = price_a * (1 + STOP_PCT)
        if dir_b == "LONG":
            sl_b = price_b * (1 - STOP_PCT)
        else:
            sl_b = price_b * (1 + STOP_PCT)

        # Sanity: TP must be on the favourable side of entry; if numerics
        # flip it (e.g. negative beta edge cases) fall back to a 3% target.
        def _coerce_tp(entry: float, tp: float, direction: str) -> float:
            if not np.isfinite(tp) or tp <= 0:
                return entry * (1 + STOP_PCT) if direction == "LONG" else entry * (1 - STOP_PCT)
            if direction == "LONG" and tp <= entry:
                return entry * (1 + STOP_PCT)
            if direction == "SHORT" and tp >= entry:
                return entry * (1 - STOP_PCT)
            return tp

        tp_a = _coerce_tp(price_a, tp_a, dir_a)
        tp_b = _coerce_tp(price_b, tp_b, dir_b)

        confidence = float(min(CONF_CAP, abs(z_now) / CONF_DIVISOR))

        # Stable pair_id: deterministic per pair + bar timestamp if available.
        ts_tag = ""
        try:
            last_idx = df_a.index[-1]
            ts_tag = pd.Timestamp(last_idx).strftime("%Y%m%dT%H%M%S")
        except Exception:
            ts_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        pair_id = f"{sym_a}_{sym_b}_{ts_tag}"

        out.append(_make_pick(
            pair_id, "A", sym_a, dir_a,
            price_a, sl_a, tp_a,
            confidence, z_now, beta, hl, sym_b,
        ))
        out.append(_make_pick(
            pair_id, "B", sym_b, dir_b,
            price_b, sl_b, tp_b,
            confidence, z_now, beta, hl, sym_a,
        ))

    return out


# ---------------------------------------------------------------------------
# Synthetic backtest (run via `python -m alpha_engine.crypto_pairs_arb`)
# ---------------------------------------------------------------------------

def _generate_cointegrated_series(n: int = 365, seed: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Two cointegrated synthetic price series (BTC-like, ETH-like).
    Construction:
        common  = random walk (shared market beta)
        spread  = mean-reverting OU (phi=0.85, sigma=0.02)
        log_a   = common + 0.5*spread + noise
        log_b   = beta_true * common - 0.5*spread + noise   (beta_true=0.95)
    """
    rng = np.random.default_rng(seed)
    common = np.cumsum(rng.normal(0.0005, 0.02, n))
    spread = np.zeros(n)
    phi = 0.85
    for i in range(1, n):
        spread[i] = phi * spread[i - 1] + rng.normal(0, 0.02)
    log_a = common + 0.5 * spread + rng.normal(0, 0.005, n) + np.log(50000)
    log_b = 0.95 * common - 0.5 * spread + rng.normal(0, 0.005, n) + np.log(3000)
    a = np.exp(log_a)
    b = np.exp(log_b)
    idx = pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC")
    df_a = pd.DataFrame({"close": a, "high": a * 1.005, "low": a * 0.995, "open": a, "volume": 1.0}, index=idx)
    df_b = pd.DataFrame({"close": b, "high": b * 1.005, "low": b * 0.995, "open": b, "volume": 1.0}, index=idx)
    return df_a, df_b


def _walk_forward_backtest() -> Dict:
    df_a, df_b = _generate_cointegrated_series(365)
    train_n = 180
    # Walk-forward: fire on every test bar using only data up to that bar.
    signals: List[Dict] = []
    pnls: List[float] = []
    for t in range(train_n, len(df_a)):
        window_a = df_a.iloc[: t + 1]
        window_b = df_b.iloc[: t + 1]
        picks = crypto_pairs_arb({"BTCUSDT": window_a, "ETHUSDT": window_b})
        if not picks:
            continue
        # Group by pair_id; simulate each leg P&L 5 bars forward (or until exit).
        by_pair: Dict[str, List[Dict]] = {}
        for p in picks:
            by_pair.setdefault(p["pair_id"], []).append(p)
        for pid, legs in by_pair.items():
            if t + 5 >= len(df_a):
                continue
            pair_pnl = 0.0
            for leg in legs:
                sym = leg["symbol"]
                fwd_df = df_a if sym == "BTCUSDT" else df_b
                entry = leg["entry_price"]
                # Simple 5-bar holding period or TP/SL touch.
                future = fwd_df["close"].iloc[t + 1 : t + 6].to_numpy()
                exit_px = float(future[-1])
                tp = leg["take_profit"]
                sl = leg["stop_loss"]
                for fp in future:
                    if leg["direction"] == "LONG":
                        if fp >= tp or fp <= sl:
                            exit_px = float(fp); break
                    else:
                        if fp <= tp or fp >= sl:
                            exit_px = float(fp); break
                if leg["direction"] == "LONG":
                    leg_pnl = (exit_px - entry) / entry
                else:
                    leg_pnl = (entry - exit_px) / entry
                pair_pnl += leg_pnl
            pair_pnl /= max(1, len(legs))
            signals.append({"pair_id": pid, "pnl": pair_pnl})
            pnls.append(pair_pnl)
    n_signals = len(pnls)
    if n_signals == 0:
        return {
            "n_signals": 0, "win_rate": 0.0, "avg_pnl_pct": 0.0,
            "sharpe": 0.0, "train_bars": train_n, "test_bars": len(df_a) - train_n,
        }
    arr = np.array(pnls)
    wins = int((arr > 0).sum())
    win_rate = float(wins / n_signals)
    avg = float(arr.mean())
    std = float(arr.std(ddof=1)) if n_signals > 1 else 0.0
    sharpe = float((avg / std) * np.sqrt(252)) if std > 0 else 0.0
    return {
        "n_signals": n_signals,
        "win_rate": round(win_rate, 4),
        "avg_pnl_pct": round(avg * 100, 4),
        "sharpe": round(sharpe, 3),
        "train_bars": train_n,
        "test_bars": len(df_a) - train_n,
    }


if __name__ == "__main__":
    import json
    res = _walk_forward_backtest()
    print(json.dumps(res, indent=2))
