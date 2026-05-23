#!/usr/bin/env python3
"""
Pre-Skyrocket Multi-Timeframe Profit Bundle v2

Goal:
- Beat the prior single-horizon bundle on Sharpe/return.
- Stay consistent across multiple holding horizons.
- Preserve high trade count (large sample, not sparse lucky hits).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from incubator.backtest_team.pre_skyrocket_long_short_bundle import (  # noqa: E402
    DB_PATH,
    RESULTS_DIR,
    _build_feature_frame,
    _drawdown,
    _load_universe,
    _ridge_fit,
)


LONG_COLS = ["ret_24h", "ret_1h", "ret_6h", "vol_ratio", "dist_ema", "dist_high", "range_norm"]
SHORT_COLS = ["ret_24h", "ret_1h", "vol_ratio", "upper_wick", "dist_ema", "dist_high", "range_norm"]


def _score(df: pd.DataFrame, cols: List[str], mu: pd.Series, sigma: pd.Series, w: np.ndarray) -> np.ndarray:
    z = (df[cols] - mu) / sigma
    return z.to_numpy(dtype=float) @ w


def _zscore(s: pd.Series) -> pd.Series:
    sd = float(s.std())
    if sd <= 1e-12:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - float(s.mean())) / sd


def run() -> Dict:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts_label = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    hold_horizons = [6, 12, 18, 24]
    top_rank = 5
    top_k = 3
    long_weight = 0.25
    short_weight = 0.75
    short_rank_cap = 5
    commission = 0.0003

    data_by_pair = _load_universe(DB_PATH)

    per_hold_summary: Dict[str, Dict] = {}
    per_hold_returns: Dict[int, Dict[pd.Timestamp, float]] = {}
    live_by_hold: Dict[int, pd.DataFrame] = {}
    bar_rows: List[Dict] = []

    for hold in hold_horizons:
        cs = _build_feature_frame(data_by_pair, hold_bars=hold)
        uniq = cs["timestamp"].sort_values().unique()
        split_ts = uniq[int(len(uniq) * 0.7)]

        study = (cs["rank_daily"] <= top_rank) | (cs["rank_hourly"] <= top_rank)
        train = cs[(cs["timestamp"] <= split_ts) & study].copy()
        test = cs[cs["timestamp"] > split_ts].copy()

        mu_long = train[LONG_COLS].mean()
        sigma_long = train[LONG_COLS].std().replace(0, 1.0)
        x_long = ((train[LONG_COLS] - mu_long) / sigma_long).to_numpy(dtype=float)
        y_long = train["future_ret"].to_numpy(dtype=float)
        w_long = _ridge_fit(x_long, y_long, l2=0.35)

        short_train = train[train["rank_daily"] <= top_rank].copy()
        mu_short = short_train[SHORT_COLS].mean()
        sigma_short = short_train[SHORT_COLS].std().replace(0, 1.0)
        x_short = ((short_train[SHORT_COLS] - mu_short) / sigma_short).to_numpy(dtype=float)
        y_short = (-short_train["future_ret"]).to_numpy(dtype=float)
        w_short = _ridge_fit(x_short, y_short, l2=0.45)

        test = test.copy()
        test["long_score"] = _score(test, LONG_COLS, mu_long, sigma_long, w_long)
        test["short_score"] = _score(test, SHORT_COLS, mu_short, sigma_short, w_short)

        per_ts_ret: Dict[pd.Timestamp, float] = {}
        bar_ret: List[float] = []
        long_hits: List[int] = []
        short_hits: List[int] = []
        trade_count = 0

        for t, g in test.groupby("timestamp", sort=True):
            longs = g.sort_values("long_score", ascending=False).head(top_k)
            short_pool = g[g["rank_daily"] <= short_rank_cap]
            if short_pool.empty:
                short_pool = g
            shorts = short_pool.sort_values("short_score", ascending=False).head(top_k)

            long_rets = (longs["future_ret"] - 2.0 * commission).tolist()
            short_rets = (-shorts["future_ret"] - 2.0 * commission).tolist()
            long_avg = float(np.mean(long_rets)) if long_rets else 0.0
            short_avg = float(np.mean(short_rets)) if short_rets else 0.0
            ret = long_weight * long_avg + short_weight * short_avg

            per_ts_ret[pd.Timestamp(t)] = ret
            bar_ret.append(ret)
            long_hits.extend([1 if x > 0 else 0 for x in long_rets])
            short_hits.extend([1 if x > 0 else 0 for x in short_rets])
            trade_count += len(long_rets) + len(short_rets)

        arr = np.array(bar_ret, dtype=float)
        eq = np.cumprod(1.0 + arr) if len(arr) else np.array([1.0])
        sharpe = 0.0
        if len(arr) > 1 and np.std(arr) > 0:
            sharpe = float(np.mean(arr) / np.std(arr) * np.sqrt(24 * 365))

        per_hold_summary[str(hold)] = {
            "bars_tested": int(len(arr)),
            "sharpe": round(sharpe, 4),
            "win_rate": round(float((arr > 0).mean()) if len(arr) else 0.0, 4),
            "total_return": round(float(eq[-1] - 1.0) if len(eq) else 0.0, 6),
            "max_drawdown": round(_drawdown(eq) if len(eq) else 0.0, 6),
            "trade_count": int(trade_count),
            "long_hit_rate": round(float(np.mean(long_hits)) if long_hits else 0.0, 4),
            "short_hit_rate": round(float(np.mean(short_hits)) if short_hits else 0.0, 4),
        }
        per_hold_returns[hold] = per_ts_ret

        latest_ts = cs["timestamp"].max()
        live = cs[cs["timestamp"] == latest_ts].copy()
        live["long_score"] = _score(live, LONG_COLS, mu_long, sigma_long, w_long)
        live["short_score"] = _score(live, SHORT_COLS, mu_short, sigma_short, w_short)
        live_by_hold[hold] = live

    common_ts = sorted(set.intersection(*[set(v.keys()) for v in per_hold_returns.values()]))
    sleeve_returns = []
    for t in common_ts:
        per_hold = {f"ret_h{h}": per_hold_returns[h][t] for h in hold_horizons}
        sleeve = float(np.mean(list(per_hold.values())))
        sleeve_returns.append(sleeve)
        bar_rows.append({"timestamp": t.isoformat(), "sleeve_return": round(sleeve, 6), **{k: round(v, 6) for k, v in per_hold.items()}})

    sleeve_arr = np.array(sleeve_returns, dtype=float)
    sleeve_eq = np.cumprod(1.0 + sleeve_arr) if len(sleeve_arr) else np.array([1.0])
    sleeve_sharpe = 0.0
    if len(sleeve_arr) > 1 and np.std(sleeve_arr) > 0:
        sleeve_sharpe = float(np.mean(sleeve_arr) / np.std(sleeve_arr) * np.sqrt(24 * 365))

    sharpe_list = [per_hold_summary[str(h)]["sharpe"] for h in hold_horizons]
    ret_list = [per_hold_summary[str(h)]["total_return"] for h in hold_horizons]
    dd_list = [per_hold_summary[str(h)]["max_drawdown"] for h in hold_horizons]
    trade_list = [per_hold_summary[str(h)]["trade_count"] for h in hold_horizons]

    # Build multi-timeframe consensus picks from latest timestamp scores.
    latest_ts = max([df["timestamp"].iloc[-1] for df in live_by_hold.values()])
    base_live = live_by_hold[hold_horizons[0]][["pair", "ret_1h", "ret_24h", "vol_ratio", "upper_wick", "dist_ema"]].copy()
    base_live = base_live.set_index("pair")

    long_blend = pd.Series(0.0, index=base_live.index)
    short_blend = pd.Series(0.0, index=base_live.index)
    long_parts: Dict[str, Dict[str, float]] = {}
    short_parts: Dict[str, Dict[str, float]] = {}
    for h, live in live_by_hold.items():
        x = live.set_index("pair")
        lz = _zscore(x["long_score"])
        sz = _zscore(x["short_score"])
        long_blend = long_blend.add(lz, fill_value=0.0)
        short_blend = short_blend.add(sz, fill_value=0.0)
        for p in x.index:
            long_parts.setdefault(p, {})[f"h{h}"] = round(float(lz.loc[p]), 4)
            short_parts.setdefault(p, {})[f"h{h}"] = round(float(sz.loc[p]), 4)

    long_blend /= len(hold_horizons)
    short_blend /= len(hold_horizons)

    long_top = long_blend.sort_values(ascending=False).head(top_k)
    short_top = short_blend.sort_values(ascending=False)
    short_top = short_top[~short_top.index.isin(long_top.index)].head(top_k)

    def _pick_row(pair: str, side: str, score: float) -> Dict:
        row = base_live.loc[pair]
        parts = long_parts[pair] if side == "LONG" else short_parts[pair]
        return {
            "pair": pair,
            "side": side,
            "blended_score": round(float(score), 4),
            "per_horizon_score_z": parts,
            "ret_1h": round(float(row["ret_1h"]), 5),
            "ret_24h": round(float(row["ret_24h"]), 5),
            "vol_ratio": round(float(row["vol_ratio"]), 4),
            "upper_wick": round(float(row["upper_wick"]), 4),
            "dist_ema": round(float(row["dist_ema"]), 5),
        }

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {
            "hold_horizons": hold_horizons,
            "top_rank_for_study": top_rank,
            "top_k_picks_each_side": top_k,
            "long_weight": long_weight,
            "short_weight": short_weight,
            "short_rank_cap": short_rank_cap,
            "commission_per_side": commission,
            "pairs": sorted(data_by_pair.keys()),
        },
        "per_horizon_backtest": per_hold_summary,
        "mtf_sleeve_backtest": {
            "bars_tested": int(len(sleeve_arr)),
            "sharpe": round(sleeve_sharpe, 4),
            "win_rate": round(float((sleeve_arr > 0).mean()) if len(sleeve_arr) else 0.0, 4),
            "total_return": round(float(sleeve_eq[-1] - 1.0) if len(sleeve_eq) else 0.0, 6),
            "max_drawdown": round(_drawdown(sleeve_eq) if len(sleeve_eq) else 0.0, 6),
        },
        "consistency": {
            "min_horizon_sharpe": round(float(min(sharpe_list)), 4),
            "avg_horizon_sharpe": round(float(np.mean(sharpe_list)), 4),
            "avg_horizon_return": round(float(np.mean(ret_list)), 6),
            "worst_horizon_drawdown": round(float(min(dd_list)), 6),
            "avg_horizon_drawdown": round(float(np.mean(dd_list)), 6),
            "avg_horizon_trade_count": int(np.mean(trade_list)),
            "total_trades_all_horizons": int(np.sum(trade_list)),
        },
        "latest_mtf_picks": {
            "timestamp": pd.Timestamp(latest_ts).isoformat(),
            "long": [_pick_row(p, "LONG", s) for p, s in long_top.items()],
            "short": [_pick_row(p, "SHORT", s) for p, s in short_top.items()],
        },
    }

    out_json = RESULTS_DIR / f"pre_skyrocket_multi_tf_profit_bundle_v2_{ts_label}.json"
    out_csv = RESULTS_DIR / f"pre_skyrocket_multi_tf_profit_bundle_v2_{ts_label}.csv"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pd.DataFrame(bar_rows).to_csv(out_csv, index=False)

    print(f"Saved: {out_json}")
    print(f"Saved: {out_csv}")
    print(
        "MTF Sleeve | Sharpe={:.4f} WinRate={:.2%} Return={:.2%} MaxDD={:.2%} Trades(all_horizons)={}".format(
            summary["mtf_sleeve_backtest"]["sharpe"],
            summary["mtf_sleeve_backtest"]["win_rate"],
            summary["mtf_sleeve_backtest"]["total_return"],
            summary["mtf_sleeve_backtest"]["max_drawdown"],
            summary["consistency"]["total_trades_all_horizons"],
        )
    )
    print(
        "Consistency | MinSharpe={} AvgSharpe={} AvgReturn={} AvgTrades/h={}".format(
            summary["consistency"]["min_horizon_sharpe"],
            summary["consistency"]["avg_horizon_sharpe"],
            summary["consistency"]["avg_horizon_return"],
            summary["consistency"]["avg_horizon_trade_count"],
        )
    )
    print("Latest LONG picks:", ", ".join([p["pair"] for p in summary["latest_mtf_picks"]["long"]]))
    print("Latest SHORT picks:", ", ".join([p["pair"] for p in summary["latest_mtf_picks"]["short"]]))
    return summary


if __name__ == "__main__":
    run()
