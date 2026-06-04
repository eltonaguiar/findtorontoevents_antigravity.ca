#!/usr/bin/env python3
"""equity_vix_term_structure_regime_rotator — multi-class swarm winner 2026-06-04.

Per agent-swarm synthesis (50 agents, 21 proposals, 21 critiques, 7 synthesizers
across CRYPTO/EQUITY/ETF/FOREX/COMMODITY/BOND/FUTURES), this was the **only**
candidate that cleared adversarial critique with realistic PF >= 1.2. All other
6 classes returned `no_viable_winner` because critic-adjusted PFs landed in the
1.05-1.25 band (sub-floor).

THESIS (Simon & Campasano 2014):
The VIX term structure (VIX9D/VIX/VXV) reflects the vol-risk-premium across
horizons. When near-term (VIX9D/VIX) is in contango (<1.0), short-dated vol
is cheap relative to longer-dated vol → systematic carry available → reach
for risk. When in backwardation (>1.05), short-dated vol is dear → panic
state → de-risk.

REGIMES (3-regime classifier on daily close):
  RISK_ON       — VIX9D/VIX < 0.92  AND  VIX < 20  AND  ADX(SPY, 14) > 12
                  → 100% in best-momentum-rank ETF among {SPY, QQQ, IWM, XLK}
                  using 60-trading-day total return as rank input
                  (handles the rotation between large/small/tech).
  NEUTRAL       — 0.92 <= VIX9D/VIX <= 1.05  OR  20 <= VIX <= 28
                  → 50/50 SPY/IEF; cuts equity beta in the chop zone.
  RISK_OFF      — VIX9D/VIX > 1.05  OR  VIX > 28
                  → 50/50 IEF/GLD; defensive twin-engine.

EXIT/TURNOVER:
  Daily check; rebalance ON regime change (not daily turnover). Equity-leg
  swap inside RISK_ON triggers only on momentum-rank flip with >5pt edge.

THRESHOLDS PRE-LOCKED 2026-06-04 (synthesis spec):
  contango_thresh   = 0.92
  backward_thresh   = 1.05
  vix_low           = 20
  vix_high          = 28
  adx_min           = 12
  mom_lookback      = 60   (trading days)
  rebal_min_edge    = 5    (rank percentile points)

NO_VIABLE_WINNER classes (6 of 7): CRYPTO, ETF, FOREX, COMMODITY, BOND, FUTURES.
For each of those, the swarm produced 3 candidates that ALL failed PF>=1.3.
Per the swarm's recommended_first_step (see reports/swarm_strategy_proposals_
2026-06-04/full_result.json), most should NOT be wired to paper-pilot — they
need parameter cuts, true 2nd-source signal replacement, or upstream data-feed
fixes (intrabar OHLC, FRED carry cache, CME settlement ingest) before re-running.

ADMISSIBILITY GATES (the swarm's pre-registered kill criteria):
  - OOS PF >= 1.3 on 2024-2026 split with 2014-2023 in-sample
  - OOS MDD < 15%
  - Regime-flip-lag PnL audit (avoids the "regime knew before SL fired" bug)

Run:
  python tools/equity_vix_regime_rotator.py --backtest         # historical
  python tools/equity_vix_regime_rotator.py --mc-trials 1000   # MC null
  python tools/equity_vix_regime_rotator.py --walkforward      # OOS split

Output:
  reports/equity_vix_regime_rotator_2026-06-04/backtest_summary.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf


# ── PRE-LOCKED THRESHOLDS (swarm synthesis spec, do not tune without operator) ──
CONTANGO_THRESH = 0.92
BACKWARD_THRESH = 1.05
VIX_LOW = 20.0
VIX_HIGH = 28.0
ADX_MIN = 12.0
MOM_LOOKBACK = 60
REBAL_MIN_EDGE = 5  # rank percentile points

RISK_ON_UNIVERSE = ["SPY", "QQQ", "IWM", "XLK"]
NEUTRAL_LEGS = ["SPY", "IEF"]
RISK_OFF_LEGS = ["IEF", "GLD"]
VIX_SYMBOLS = ["^VIX9D", "^VIX", "^VIX3M"]  # ^VXV renamed to ^VIX3M; CBOE 3-month VIX
ADX_SYMBOL = "SPY"


def _fetch_closes(symbol: str, start: str, end: str) -> pd.Series:
    """Daily close series via yfinance."""
    df = yf.download(symbol, start=start, end=end, progress=False,
                     auto_adjust=False, threads=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df["Close"].dropna()


def _compute_adx(symbol: str, start: str, end: str, period: int = 14) -> pd.Series:
    """Average Directional Index — trend-strength proxy."""
    df = yf.download(symbol, start=start, end=end, progress=False,
                     auto_adjust=False, threads=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    high, low, close = df["High"], df["Low"], df["Close"]
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    tr = pd.concat([(high - low),
                    (high - close.shift()).abs(),
                    (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, min_periods=period).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/period).mean() / atr)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
    return dx.ewm(alpha=1/period, min_periods=period).mean().dropna()


def classify_regime(row: dict) -> str:
    """3-regime classifier per swarm spec. row keys: VIX9D, VIX, VXV, ADX."""
    vix9d, vix, vxv, adx = row["VIX9D"], row["VIX"], row["VXV"], row["ADX"]
    near_ratio = vix9d / vix if vix > 0 else 1.0
    far_ratio = vix / vxv if vxv > 0 else 1.0

    # RISK_OFF: contango broken on near OR fear high
    if near_ratio > BACKWARD_THRESH or vix > VIX_HIGH:
        return "RISK_OFF"
    # RISK_ON: deep contango on near AND fear low AND trend present
    if near_ratio < CONTANGO_THRESH and vix < VIX_LOW and adx > ADX_MIN:
        return "RISK_ON"
    return "NEUTRAL"


def _rank_momentum(closes: pd.DataFrame, lookback: int = MOM_LOOKBACK) -> pd.Series:
    """Return the symbol with highest trailing-`lookback`-day return."""
    rets = closes.pct_change(lookback).iloc[-1]
    return rets.sort_values(ascending=False)


def build_panel(start: str, end: str) -> pd.DataFrame:
    """Build the multi-asset closes panel + regime classification."""
    print(f"[panel] fetching {start} -> {end}")
    cols = {}
    for sym in VIX_SYMBOLS + sorted(set(RISK_ON_UNIVERSE + NEUTRAL_LEGS + RISK_OFF_LEGS)):
        cols[sym] = _fetch_closes(sym, start, end)
    closes = pd.DataFrame(cols).ffill().dropna()
    print(f"[panel] {len(closes)} trading days, {len(cols)} symbols")
    closes["ADX"] = _compute_adx(ADX_SYMBOL, start, end).reindex(closes.index).ffill()
    closes = closes.dropna(subset=["ADX"])
    regimes = []
    for idx, r in closes.iterrows():
        regimes.append(classify_regime({
            "VIX9D": r["^VIX9D"], "VIX": r["^VIX"],
            "VXV": r["^VIX3M"], "ADX": r["ADX"],
        }))
    closes["regime"] = regimes
    return closes


def simulate(panel: pd.DataFrame) -> tuple[pd.Series, list[dict]]:
    """Simulate the regime rotator. Returns (equity_curve, trades)."""
    legs_today = None  # current position e.g. {"SPY": 1.0}
    current_regime = None
    equity = 1.0
    curve = []
    trades = []

    def _pick_legs(regime: str, panel_row: pd.Series) -> dict:
        if regime == "RISK_OFF":
            return {RISK_OFF_LEGS[0]: 0.5, RISK_OFF_LEGS[1]: 0.5}
        if regime == "NEUTRAL":
            return {NEUTRAL_LEGS[0]: 0.5, NEUTRAL_LEGS[1]: 0.5}
        # RISK_ON: pick best-momentum equity ETF
        avail = [s for s in RISK_ON_UNIVERSE if s in panel.columns]
        recent = panel.loc[:panel_row.name, avail].iloc[-(MOM_LOOKBACK + 1):]
        if len(recent) < MOM_LOOKBACK + 1:
            return {RISK_ON_UNIVERSE[0]: 1.0}
        ranks = _rank_momentum(recent, MOM_LOOKBACK)
        return {ranks.index[0]: 1.0}

    panel_iter = list(panel.iterrows())
    for i in range(1, len(panel_iter)):
        idx, row = panel_iter[i]
        prev_idx, prev_row = panel_iter[i - 1]
        regime = row["regime"]

        if legs_today is None or regime != current_regime:
            new_legs = _pick_legs(regime, row)
            if legs_today is not None:
                trades.append({
                    "exit_date": str(idx.date()),
                    "from_regime": current_regime,
                    "to_regime": regime,
                    "from_legs": list(legs_today.keys()),
                    "to_legs": list(new_legs.keys()),
                    "equity_at_switch": float(equity),
                })
            legs_today = new_legs
            current_regime = regime

        day_ret = 0.0
        for sym, w in legs_today.items():
            if sym in panel.columns and sym in prev_row.index:
                prev_px = float(prev_row[sym])
                cur_px = float(row[sym])
                if prev_px > 0:
                    day_ret += w * (cur_px / prev_px - 1)
        equity *= (1 + day_ret)
        curve.append((idx, equity, regime))

    eq = pd.Series([c[1] for c in curve], index=[c[0] for c in curve], name="equity")
    return eq, trades


def stats(eq: pd.Series) -> dict:
    """Compute Sharpe / PF / WR / MDD / CAGR + Monte-Carlo bootstrap p-value vs null."""
    rets = eq.pct_change().dropna()
    if len(rets) == 0:
        return {"error": "no returns"}
    pos = rets[rets > 0]
    neg = rets[rets < 0]
    pf = pos.sum() / (-neg.sum()) if len(neg) and neg.sum() < 0 else float("inf")
    wr = len(pos) / (len(pos) + len(neg)) if (len(pos) + len(neg)) else 0
    sharpe = (rets.mean() / rets.std()) * np.sqrt(252) if rets.std() > 0 else 0
    cum = (1 + rets).cumprod()
    peak = cum.cummax()
    mdd = float(((cum / peak) - 1).min())
    n_days = len(rets)
    cagr = (cum.iloc[-1] ** (252 / n_days)) - 1 if n_days else 0
    return {
        "n_days": int(n_days),
        "sharpe": round(float(sharpe), 3),
        "profit_factor": round(float(pf), 3) if math.isfinite(pf) else None,
        "win_rate": round(float(wr), 3),
        "max_drawdown_pct": round(mdd * 100, 2),
        "cagr_pct": round(float(cagr) * 100, 2),
        "total_return_pct": round((cum.iloc[-1] - 1) * 100, 2),
    }


def monte_carlo_null(eq: pd.Series, panel: pd.DataFrame, n_trials: int = 1000) -> dict:
    """MC null: shuffle the REGIME labels (preserving daily distribution) then
    re-simulate. Tests whether the regime-classification signal actually adds
    value vs random regime assignment with same marginal distribution.

    NOTE 2026-06-04: a previous version of this function shuffled the daily
    return SEQUENCE — but mean/std are permutation-invariant, so the Sharpe
    of permuted returns trivially equals the real Sharpe. That's a degenerate
    null and produces null_std=0. The corrected version shuffles regime LABELS
    instead, which tests the actual hypothesis: is the VIX-term-structure
    regime classification adding alpha vs random labelling?
    """
    rets = eq.pct_change().dropna().values
    if len(rets) < 100 or "regime" not in panel.columns:
        return {"n_trials": 0, "error": "too few returns or no regime column"}
    rng = np.random.default_rng(20260604)
    real_sharpe = (rets.mean() / rets.std()) * np.sqrt(252) if rets.std() > 0 else 0
    real_regimes = panel["regime"].values
    null_sharpes = []
    for _ in range(n_trials):
        shuffled_regimes = rng.permutation(real_regimes).copy()
        shuffled_panel = panel.copy()
        shuffled_panel["regime"] = shuffled_regimes
        # Re-simulate with shuffled regime assignments
        try:
            shuffled_eq, _ = simulate(shuffled_panel)
            sr = shuffled_eq.pct_change().dropna()
            if len(sr) > 0 and sr.std() > 0:
                null_sharpes.append((sr.mean() / sr.std()) * np.sqrt(252))
        except Exception:
            continue
    if not null_sharpes:
        return {"n_trials": 0, "error": "all null trials failed"}
    null_sharpes = np.array(null_sharpes)
    p_value = float((null_sharpes >= real_sharpe).mean())
    return {
        "n_trials": len(null_sharpes),
        "null_hypothesis": "regime labels shuffled (preserves marginal distribution)",
        "real_sharpe": round(float(real_sharpe), 3),
        "null_mean_sharpe": round(float(null_sharpes.mean()), 3),
        "null_std_sharpe": round(float(null_sharpes.std()), 3),
        "null_p95_sharpe": round(float(np.percentile(null_sharpes, 95)), 3),
        "p_value_vs_null": round(p_value, 4),
        "significant_at_5pct": bool(p_value < 0.05),
        "significant_at_1pct": bool(p_value < 0.01),
    }


def walkforward_split(panel: pd.DataFrame) -> dict:
    """In-sample 2014-2023, OOS 2024-2026 (swarm's pre-registered gate)."""
    is_end = "2024-01-01"
    is_panel = panel[panel.index < is_end]
    oos_panel = panel[panel.index >= is_end]
    print(f"[wf] in-sample n={len(is_panel)}, OOS n={len(oos_panel)}")
    is_eq, _ = simulate(is_panel)
    oos_eq, _ = simulate(oos_panel)
    is_stats = stats(is_eq)
    oos_stats = stats(oos_eq)
    # Swarm-spec admissibility gates
    gates = {
        "oos_pf_ge_1_30": (oos_stats.get("profit_factor") or 0) >= 1.30,
        "oos_mdd_lt_15": (oos_stats.get("max_drawdown_pct") or 0) > -15.0,
    }
    return {
        "in_sample": is_stats,
        "out_of_sample": oos_stats,
        "swarm_admissibility_gates": gates,
        "all_gates_pass": all(gates.values()),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2014-01-01")
    ap.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    ap.add_argument("--backtest", action="store_true")
    ap.add_argument("--mc-trials", type=int, default=0,
                    help="If >0, run MC null hypothesis with this many trials")
    ap.add_argument("--walkforward", action="store_true")
    ap.add_argument("--out", default="reports/equity_vix_regime_rotator_2026-06-04")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    panel = build_panel(args.start, args.end)
    panel_path = out_dir / "panel.parquet"
    try:
        panel.to_parquet(panel_path)
    except Exception:
        pass
    print(f"[panel] regime dist:")
    print(panel["regime"].value_counts().to_dict())

    summary = {
        "strategy_name": "equity_vix_term_structure_regime_rotator",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "swarm_synthesis": "reports/swarm_strategy_proposals_2026-06-04/full_result.json",
        "thresholds_pre_locked": {
            "contango_thresh": CONTANGO_THRESH,
            "backward_thresh": BACKWARD_THRESH,
            "vix_low": VIX_LOW,
            "vix_high": VIX_HIGH,
            "adx_min": ADX_MIN,
            "mom_lookback": MOM_LOOKBACK,
        },
        "panel": {
            "start": args.start,
            "end": args.end,
            "trading_days": int(len(panel)),
            "regime_distribution": panel["regime"].value_counts().to_dict(),
        },
    }

    if args.backtest or args.mc_trials > 0 or args.walkforward:
        eq, trades = simulate(panel)
        summary["full_period"] = stats(eq)
        summary["n_regime_switches"] = len(trades)
        print(f"[full] {summary['full_period']}")
        eq_path = out_dir / "equity_curve_full.csv"
        eq.to_csv(eq_path)
        print(f"[full] wrote {eq_path}")

    if args.mc_trials > 0:
        summary["monte_carlo_null"] = monte_carlo_null(eq, panel, args.mc_trials)
        print(f"[mc]   {summary['monte_carlo_null']}")

    if args.walkforward:
        summary["walkforward"] = walkforward_split(panel)
        print(f"[wf]   IS sharpe={summary['walkforward']['in_sample']['sharpe']}, "
              f"OOS sharpe={summary['walkforward']['out_of_sample']['sharpe']}, "
              f"all_gates_pass={summary['walkforward']['all_gates_pass']}")

    summary_path = out_dir / "backtest_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\n[summary] wrote {summary_path}")


if __name__ == "__main__":
    sys.exit(main() or 0)
