#!/usr/bin/env python3
"""
Real-data backtest harness for MIMO strategies (Workstream A.1).

Plan: docs/ASSET_CLASS_REHAB_PLAN_2026-04-14.md §A.1
Recon: docs/ASSET_CLASS_REHAB_RECON_2026-04-14.md

Runs all 7 MIMO strategies against REAL historical OHLCV bars from
yfinance. No synthetic data (plan §A.3 hard rule). Computes per-strategy
metrics with 1,000 bootstrap resamples for PF / WR CI-lower. Fails loudly
on n < 30 (plan §A.1.7).

Output: mimo_strategies/backtest_results.json (co-located with the
strategies per plan §A.1.6; NOT the live dashboard data directory).

Usage:
    python scripts/backtest_mimo_on_real_bars.py --period 2y
    python scripts/backtest_mimo_on_real_bars.py --strategy mimo_strategies.bond_seasonal_regime
    python scripts/backtest_mimo_on_real_bars.py --quiet

This replaces an earlier broken harness at the same path that called
STRATEGY_REGISTRY[name]['backtest'] — a method that only 1 of 7 MIMO
strategies actually exposes. The other 6 silently failed and looked
like "didn't fire" losers, which is the exact failure mode the plan's
intro calls out. This rewrite drives each strategy through its own
generate_signals() function directly, then replays entries on the same
real bars using a lean inline TP/SL forward walk. No module-level
imports from alpha_engine/battle_test.py because that file pulls in
heavy project state (config, crypto_strategies, forex_strategies,
equity_strategies) that a MIMO-only run does not need — the bar-fetch
pattern is ported directly from alpha_engine/battle_test.py:50-80.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))


# The 7 MIMO strategies discovered in Workstream A.2 recon.
# Each module exposes generate_signals(df, config) -> df with columns:
#   signal (1/-1/0), stop_long, stop_short, atr [+ optional tp_long/tp_short]
MIMO_STRATEGIES: list[tuple[str, str, str]] = [
    ("mimo_strategies.bond_seasonal_regime", "BondSeasonalRegimeConfig", "BOND"),
    ("mimo_strategies.commodity_keltner_cci_reversion", "CommodityKeltnerCCIConfig", "COMMODITY"),
    ("mimo_strategies.equity_volume_momentum_breakout", "EquityVolumeMomentumConfig", "EQUITY"),
    ("mimo_strategies.etf_vwap_mean_reversion", "ETFVWAPMeanReversionConfig", "ETF"),
    ("mimo_strategies.forex_session_carry_momentum", "ForexSessionCarryConfig", "FOREX"),
    ("mimo_strategies.futures_mean_reversion_rsi_bb", "FuturesMeanReversionConfig", "FUTURES"),
    ("mimo_strategies.futures_trend_dual_ema", "FuturesTrendDualEMAConfig", "FUTURES"),
]

DEFAULT_PERIOD = "2y"
DEFAULT_RR_FALLBACK = 2.0   # 2:1 R:R when a strategy emits SL but no TP column
MAX_HOLD_BARS = 60          # 60 days on daily bars
BOOTSTRAP_N = 1000          # plan §A.1.4: 1k, not 10k
MIN_TRADES = 30             # plan §A.1.7: fail-loud threshold
PF_CI_LOWER_GATE = 1.20     # plan §A.4: promotion gate
PERM_P_GATE = 0.05          # plan §A.4: permutation p-value cap


def fetch_historical_data(
    symbols: list[str], period: str = "1y"
) -> dict[str, pd.DataFrame]:
    """Multi-symbol yfinance 1d OHLCV loader.

    Direct port of alpha_engine/battle_test.py:50-80. Returns
    {symbol: DataFrame} with Title-case columns (Open/High/Low/Close/Volume).
    Symbols with <50 bars or empty data are silently dropped.
    """
    data: dict[str, pd.DataFrame] = {}
    if not symbols:
        return data
    tickers = " ".join(symbols)
    try:
        raw = yf.download(
            tickers,
            period=period,
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )
    except Exception as e:
        print(f"  yfinance download failed: {e}", file=sys.stderr)
        return data
    for symbol in symbols:
        try:
            if len(symbols) == 1:
                df = raw
            else:
                df = raw[symbol] if symbol in raw.columns.get_level_values(0) else None
            if df is None or df.empty:
                continue
            df = df.dropna(subset=["Close"])
            if len(df) < 50:
                continue
            data[symbol] = df
        except Exception:
            continue
    return data


def _to_lower_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]
    return df


def _replay_trade(
    entry_idx: int,
    entry: float,
    tp: float,
    sl: float,
    direction: str,
    df: pd.DataFrame,
    max_hold: int,
) -> tuple[float, str, int, float]:
    """Walk future bars checking for TP/SL first-touch.

    Returns (exit_px, exit_reason, bars_held, pnl_pct).
    Intrabar order: gap-open → SL → TP (SL checked first == conservative).
    """
    n = len(df)
    end = min(entry_idx + 1 + max_hold, n)
    for j in range(entry_idx + 1, end):
        o = float(df.iloc[j]["open"])
        h = float(df.iloc[j]["high"])
        low = float(df.iloc[j]["low"])
        if direction == "LONG":
            if o <= sl:
                return o, "sl_gap", j - entry_idx, (o - entry) / entry * 100.0
            if low <= sl:
                return sl, "sl_hit", j - entry_idx, (sl - entry) / entry * 100.0
            if h >= tp:
                return tp, "tp_hit", j - entry_idx, (tp - entry) / entry * 100.0
        else:  # SHORT
            if o >= sl:
                return o, "sl_gap", j - entry_idx, (entry - o) / entry * 100.0
            if h >= sl:
                return sl, "sl_hit", j - entry_idx, (entry - sl) / entry * 100.0
            if low <= tp:
                return tp, "tp_hit", j - entry_idx, (entry - tp) / entry * 100.0
    # Time out or end of data
    last_idx = min(entry_idx + max_hold, n - 1)
    last = float(df.iloc[last_idx]["close"])
    reason = "max_hold" if end < n else "end_of_data"
    if direction == "LONG":
        pnl = (last - entry) / entry * 100.0
    else:
        pnl = (entry - last) / entry * 100.0
    return last, reason, last_idx - entry_idx, pnl


def _bootstrap_ci_lower(pnls: np.ndarray, ci: float = 0.95) -> dict:
    """Bootstrap lower bound of the 95% CI for PF and WR."""
    n = len(pnls)
    if n == 0:
        return {"pf_ci_lower": 0.0, "wr_ci_lower": 0.0}
    rng = np.random.default_rng(seed=42)  # deterministic
    pfs = np.empty(BOOTSTRAP_N, dtype=float)
    wrs = np.empty(BOOTSTRAP_N, dtype=float)
    for i in range(BOOTSTRAP_N):
        sample = rng.choice(pnls, size=n, replace=True)
        wins_mask = sample > 0
        wins_sum = float(sample[wins_mask].sum()) if wins_mask.any() else 0.0
        losses_sum = float(abs(sample[~wins_mask].sum())) if (~wins_mask).any() else 0.0
        if losses_sum > 0:
            pfs[i] = wins_sum / losses_sum
        elif wins_sum > 0:
            pfs[i] = np.inf
        else:
            pfs[i] = 0.0
        wrs[i] = wins_mask.mean()
    finite_pfs = pfs[np.isfinite(pfs)]
    alpha = (1.0 - ci) / 2.0
    return {
        "pf_ci_lower": float(np.quantile(finite_pfs, alpha)) if len(finite_pfs) else 0.0,
        "wr_ci_lower": float(np.quantile(wrs, alpha)),
    }


def _permutation_pvalue(pnls: np.ndarray, n_permutations: int = 500) -> float:
    """Permutation test on per-trade sign.

    H0: mean per-trade PnL is zero (signs are random).
    H1: strategy has positive edge.

    Shuffles the sign of each trade magnitude and counts how often the
    shuffled mean meets or beats the observed mean. One-sided p-value.
    For a negative observed mean, returns 1.0 (no edge claim possible).
    """
    if len(pnls) < 5:
        return 1.0
    observed_mean = float(pnls.mean())
    if observed_mean <= 0:
        return 1.0
    rng = np.random.default_rng(seed=17)
    abs_pnls = np.abs(pnls)
    better_or_equal = 0
    for _ in range(n_permutations):
        signs = rng.choice([-1.0, 1.0], size=len(pnls))
        if float((abs_pnls * signs).mean()) >= observed_mean:
            better_or_equal += 1
    return (better_or_equal + 1) / (n_permutations + 1)


def _failure_mode(n: int, pf_ci_lower: float, pvalue: float) -> str | None:
    reasons = []
    if n < MIN_TRADES:
        reasons.append(f"n={n}<{MIN_TRADES}")
    if pf_ci_lower < PF_CI_LOWER_GATE:
        reasons.append(f"pf_ci_lower={pf_ci_lower:.2f}<{PF_CI_LOWER_GATE}")
    if pvalue >= PERM_P_GATE:
        reasons.append(f"perm_p={pvalue:.3f}>={PERM_P_GATE}")
    return "; ".join(reasons) if reasons else None


def _compute_metrics(trades: list, strategy_name: str, asset_class: str) -> dict:
    n = len(trades)
    base: dict = {
        "strategy": strategy_name,
        "asset_class": asset_class,
        "n_trades": n,
    }
    if n == 0:
        base.update({
            "promotion_eligible": False,
            "failure_mode": "no_trades_generated",
        })
        return base

    pnls = np.array([t["pnl_pct"] for t in trades], dtype=float)
    wins_mask = pnls > 0
    wr = float(wins_mask.mean()) * 100.0
    sum_win = float(pnls[wins_mask].sum()) if wins_mask.any() else 0.0
    sum_loss = float(abs(pnls[~wins_mask].sum())) if (~wins_mask).any() else 0.0
    pf: float | None = sum_win / sum_loss if sum_loss > 0 else None
    avg_win = float(pnls[wins_mask].mean()) if wins_mask.any() else 0.0
    avg_loss = float(pnls[~wins_mask].mean()) if (~wins_mask).any() else 0.0
    std = float(pnls.std(ddof=1)) if n > 1 else 0.0
    sharpe = float(pnls.mean() / std) if std > 0 else 0.0
    downside = pnls[pnls < 0]
    dstd = float(downside.std(ddof=1)) if len(downside) > 1 else 0.0
    sortino = float(pnls.mean() / dstd) if dstd > 0 else 0.0
    cum = np.cumsum(pnls)
    peak = np.maximum.accumulate(cum)
    dd = peak - cum
    max_dd = float(dd.max()) if n else 0.0
    calmar = float(cum[-1] / max_dd) if max_dd > 0 else 0.0
    bars = np.array([t["bars_held"] for t in trades])
    avg_hold = float(bars.mean())
    long_trades = [t for t in trades if t["direction"] == "LONG"]
    short_trades = [t for t in trades if t["direction"] == "SHORT"]
    long_wr = (
        sum(1 for t in long_trades if t["pnl_pct"] > 0) / len(long_trades) * 100.0
        if long_trades
        else None
    )
    short_wr = (
        sum(1 for t in short_trades if t["pnl_pct"] > 0) / len(short_trades) * 100.0
        if short_trades
        else None
    )
    exit_reasons: dict[str, int] = {}
    for t in trades:
        exit_reasons[t["exit_reason"]] = exit_reasons.get(t["exit_reason"], 0) + 1

    bootstrap = _bootstrap_ci_lower(pnls)
    pvalue = _permutation_pvalue(pnls)
    pf_ci_lower = bootstrap["pf_ci_lower"]
    promotion_eligible = (
        n >= MIN_TRADES
        and pf_ci_lower >= PF_CI_LOWER_GATE
        and pvalue < PERM_P_GATE
    )

    base.update({
        "wr_pct": round(wr, 2),
        "pf": round(pf, 3) if pf is not None else None,
        "avg_win_pct": round(avg_win, 3),
        "avg_loss_pct": round(avg_loss, 3),
        "max_dd_pct": round(max_dd, 2),
        "calmar_per_trade": round(calmar, 3),
        "sharpe_per_trade": round(sharpe, 3),
        "sortino_per_trade": round(sortino, 3),
        "avg_hold_bars": round(avg_hold, 1),
        "long_n": len(long_trades),
        "long_wr_pct": round(long_wr, 2) if long_wr is not None else None,
        "short_n": len(short_trades),
        "short_wr_pct": round(short_wr, 2) if short_wr is not None else None,
        "exit_reasons": exit_reasons,
        "bootstrap_pf_ci_lower": round(pf_ci_lower, 3),
        "bootstrap_wr_ci_lower_pct": round(bootstrap["wr_ci_lower"] * 100.0, 2),
        "permutation_pvalue": round(pvalue, 4),
        "promotion_eligible": promotion_eligible,
        "failure_mode": _failure_mode(n, pf_ci_lower, pvalue),
    })
    return base


def _run_one_strategy(
    module_path: str,
    config_name: str,
    asset_class: str,
    period: str,
    quiet: bool,
) -> tuple[dict, list]:
    mod = importlib.import_module(module_path)
    config_cls = getattr(mod, config_name)
    config = config_cls()
    strategy_name = module_path.rsplit(".", 1)[-1]

    symbols = list(config.symbols)
    if not quiet:
        print(f"\n[{strategy_name}] fetching {len(symbols)} symbols ({period})")

    raw = fetch_historical_data(symbols, period=period)
    if not raw:
        return (
            {
                "strategy": strategy_name,
                "asset_class": asset_class,
                "n_trades": 0,
                "promotion_eligible": False,
                "failure_mode": "no_bars_fetched",
            },
            [],
        )
    if not quiet:
        print(f"  fetched {len(raw)}/{len(symbols)} symbols with usable data")

    trades: list[dict] = []
    for symbol, df_title in raw.items():
        if df_title is None or df_title.empty:
            continue
        df = _to_lower_columns(df_title)
        required = {"open", "high", "low", "close"}
        if not required.issubset(set(df.columns)):
            continue
        try:
            sig_df = mod.generate_signals(df, config)
        except Exception as e:
            if not quiet:
                print(f"  {symbol}: generate_signals raised {type(e).__name__}: {e}")
            continue
        if "signal" not in sig_df.columns:
            continue

        entries_df = sig_df[sig_df["signal"] != 0]
        if entries_df.empty:
            continue

        last_exit_idx = -1
        for ts in entries_df.index:
            try:
                entry_idx = sig_df.index.get_loc(ts)
            except KeyError:
                continue
            if not isinstance(entry_idx, (int, np.integer)):
                continue
            entry_idx = int(entry_idx)
            if entry_idx <= last_exit_idx:
                continue
            if entry_idx >= len(sig_df) - 1:
                continue

            row = sig_df.iloc[entry_idx]
            signal_val = float(row["signal"])
            direction = "LONG" if signal_val > 0 else "SHORT"
            entry = float(row["close"])
            if entry <= 0:
                continue

            sl_col = "stop_long" if direction == "LONG" else "stop_short"
            if sl_col not in sig_df.columns:
                continue
            sl_val = row[sl_col]
            if pd.isna(sl_val):
                continue
            sl = float(sl_val)
            if sl <= 0:
                continue

            tp_col = "tp_long" if direction == "LONG" else "tp_short"
            if tp_col in sig_df.columns and pd.notna(row[tp_col]):
                tp = float(row[tp_col])
            else:
                # Derive TP from 2:1 R:R off the stop distance
                if direction == "LONG":
                    tp = entry + DEFAULT_RR_FALLBACK * (entry - sl)
                else:
                    tp = entry - DEFAULT_RR_FALLBACK * (sl - entry)

            # Sanity: reject signals with SL/TP on the wrong side of entry
            if direction == "LONG":
                if sl >= entry or tp <= entry:
                    continue
            else:
                if sl <= entry or tp >= entry:
                    continue
            if tp <= 0:
                continue

            exit_px, reason, bars_held, pnl_pct = _replay_trade(
                entry_idx, entry, tp, sl, direction, sig_df, MAX_HOLD_BARS
            )
            trades.append({
                "symbol": symbol,
                "entry_time": str(ts),
                "direction": direction,
                "entry": round(entry, 6),
                "sl": round(sl, 6),
                "tp": round(tp, 6),
                "exit": round(float(exit_px), 6),
                "exit_reason": reason,
                "bars_held": int(bars_held),
                "pnl_pct": round(float(pnl_pct), 4),
            })
            last_exit_idx = entry_idx + bars_held

    metrics = _compute_metrics(trades, strategy_name, asset_class)
    return metrics, trades


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Real-data MIMO backtest harness (plan A.1, no synthetic OHLCV)"
    )
    parser.add_argument("--period", default=DEFAULT_PERIOD, help="yfinance period (default 2y)")
    parser.add_argument(
        "--output",
        default="mimo_strategies/backtest_results.json",
        help="Output JSON path (relative to repo root)",
    )
    parser.add_argument(
        "--strategy",
        help="Run only one strategy by module path (e.g. mimo_strategies.bond_seasonal_regime)",
    )
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--trades-output",
        help="Optional path to dump every trade as a JSON array (debug/audit)",
    )
    args = parser.parse_args()

    strategies = MIMO_STRATEGIES
    if args.strategy:
        strategies = [s for s in MIMO_STRATEGIES if s[0] == args.strategy]
        if not strategies:
            print(f"Unknown strategy: {args.strategy}", file=sys.stderr)
            return 2

    all_metrics: list[dict] = []
    all_trades: list[dict] = []
    for module_path, config_name, asset_class in strategies:
        try:
            metrics, trades = _run_one_strategy(
                module_path, config_name, asset_class, args.period, args.quiet
            )
        except Exception as e:
            metrics = {
                "strategy": module_path.rsplit(".", 1)[-1],
                "asset_class": asset_class,
                "n_trades": 0,
                "promotion_eligible": False,
                "failure_mode": f"exception: {type(e).__name__}: {e}",
            }
            trades = []
        all_metrics.append(metrics)
        for t in trades:
            t["_strategy"] = metrics["strategy"]
            all_trades.append(t)
        if not args.quiet:
            n = metrics.get("n_trades", 0)
            print(
                f"  -> n={n} "
                f"pf={metrics.get('pf')} "
                f"wr={metrics.get('wr_pct')}% "
                f"pf_ci_lower={metrics.get('bootstrap_pf_ci_lower')} "
                f"perm_p={metrics.get('permutation_pvalue')} "
                f"eligible={metrics.get('promotion_eligible')}"
            )

    print()
    print("=" * 72)
    print("  MIMO REAL-DATA BACKTEST SUMMARY")
    print("=" * 72)
    insufficient = [m for m in all_metrics if m.get("n_trades", 0) < MIN_TRADES]
    if insufficient:
        print(f"\n  {len(insufficient)} strategies under n={MIN_TRADES} — DO NOT PROMOTE:")
        for m in insufficient:
            fm = m.get("failure_mode", "")
            print(
                f"    - {m['strategy']:<42} ({m['asset_class']:<10}) "
                f"n={m.get('n_trades', 0):<4}  {fm}"
            )
    eligible = [m for m in all_metrics if m.get("promotion_eligible")]
    print(f"\n  Promotion-eligible: {len(eligible)}/{len(all_metrics)}")
    for m in eligible:
        print(
            f"    + {m['strategy']} ({m['asset_class']}) "
            f"pf={m['pf']} ci_lower={m['bootstrap_pf_ci_lower']} "
            f"wr={m['wr_pct']}% n={m['n_trades']} perm_p={m['permutation_pvalue']}"
        )
    print("=" * 72)

    out_path = _REPO / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "harness_version": "A.1-2026-04-14",
        "plan_ref": "docs/ASSET_CLASS_REHAB_PLAN_2026-04-14.md",
        "period": args.period,
        "max_hold_bars": MAX_HOLD_BARS,
        "bootstrap_resamples": BOOTSTRAP_N,
        "min_trades_threshold": MIN_TRADES,
        "pf_ci_lower_gate": PF_CI_LOWER_GATE,
        "perm_p_gate": PERM_P_GATE,
        "default_rr_fallback": DEFAULT_RR_FALLBACK,
        "data_source": "yfinance 1d OHLCV (real data; no synthetic)",
        "strategies": all_metrics,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"\n  Saved -> {out_path}")

    if args.trades_output:
        trades_path = _REPO / args.trades_output
        trades_path.parent.mkdir(parents=True, exist_ok=True)
        with open(trades_path, "w", encoding="utf-8") as f:
            json.dump(all_trades, f, indent=2)
        print(f"  Saved trades -> {trades_path}")

    # Exit 0 if anything is eligible; 1 if nothing is eligible.
    # The artifact is always saved so insufficient-n runs are still auditable.
    return 0 if eligible else 1


if __name__ == "__main__":
    sys.exit(main())
