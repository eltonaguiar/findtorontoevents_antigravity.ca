#!/usr/bin/env python3
"""
Pre-Skyrocket LONG/SHORT bundle from hourly + daily gainer reverse engineering.

This script:
1) Studies top hourly/daily gainers from local crypto_data.db.
2) Learns continuation and exhaustion weights from historical outcomes.
3) Backtests a long/short bundle walk-forward on a hold horizon.
4) Emits latest LONG and SHORT picks for pre-skyrocket deployment.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DB_PATH = PROJECT_ROOT / "crypto_data.db"
RESULTS_DIR = PROJECT_ROOT / "incubator" / "backtest_results"


def _ridge_fit(x: np.ndarray, y: np.ndarray, l2: float = 0.25) -> np.ndarray:
    eye = np.eye(x.shape[1], dtype=float)
    return np.linalg.solve(x.T @ x + l2 * eye, x.T @ y)


def _drawdown(equity: np.ndarray) -> float:
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / (peak + 1e-12)
    return float(dd.min())


def _load_universe(db_path: Path, min_bars: int = 800) -> Dict[str, pd.DataFrame]:
    query = """
    SELECT pair, timestamp, open, high, low, close, volume
    FROM klines
    ORDER BY pair, timestamp
    """
    with sqlite3.connect(str(db_path)) as conn:
        raw = pd.read_sql_query(query, conn)

    if raw.empty:
        raise RuntimeError("No rows found in klines table")

    raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True, errors="coerce")
    for col in ("open", "high", "low", "close", "volume"):
        raw[col] = pd.to_numeric(raw[col], errors="coerce")
    raw = raw.dropna(subset=["pair", "timestamp", "open", "high", "low", "close", "volume"])

    by_pair: Dict[str, pd.DataFrame] = {}
    for pair, g in raw.groupby("pair"):
        g = g.sort_values("timestamp").reset_index(drop=True)
        if len(g) >= min_bars:
            by_pair[pair] = g

    if not by_pair:
        raise RuntimeError("No pair has enough history for bundle backtest")

    common_ts = None
    for df in by_pair.values():
        ts_set = set(df["timestamp"])
        common_ts = ts_set if common_ts is None else (common_ts & ts_set)
    if not common_ts:
        raise RuntimeError("No overlapping timestamps across selected pairs")

    common_idx = pd.DatetimeIndex(sorted(common_ts))
    aligned: Dict[str, pd.DataFrame] = {}
    for pair, df in by_pair.items():
        x = df.set_index("timestamp").reindex(common_idx).dropna().reset_index()
        x = x.rename(columns={"index": "timestamp"})
        aligned[pair] = x
    return aligned


def _build_feature_frame(data_by_pair: Dict[str, pd.DataFrame], hold_bars: int) -> pd.DataFrame:
    rows: List[pd.DataFrame] = []
    eps = 1e-12

    for pair, df in data_by_pair.items():
        x = df.copy()
        close = x["close"]
        volume = x["volume"]
        high = x["high"]
        low = x["low"]
        open_ = x["open"]

        vol_ma = volume.rolling(24, min_periods=1).mean()
        ema = close.ewm(span=24, adjust=False).mean()
        rolling_high = high.rolling(24, min_periods=1).max()

        f = pd.DataFrame({"timestamp": x["timestamp"]})
        f["pair"] = pair
        f["ret_1h"] = close.pct_change(1)
        f["ret_6h"] = close.pct_change(6)
        f["ret_24h"] = close.pct_change(24)
        f["vol_ratio"] = volume / (vol_ma + eps)
        f["dist_ema"] = (close - ema) / (ema + eps)
        f["dist_high"] = (rolling_high - close) / (close + eps)
        f["range_norm"] = (high - low) / (close + eps)
        f["upper_wick"] = (high - np.maximum(open_, close)) / (high - low + eps)
        f["future_ret"] = close.shift(-hold_bars) / (close + eps) - 1.0
        rows.append(f)

    cs = pd.concat(rows, ignore_index=True)
    cs = cs.replace([np.inf, -np.inf], np.nan).dropna()

    cs["rank_daily"] = cs.groupby("timestamp")["ret_24h"].rank(ascending=False, method="first")
    cs["rank_hourly"] = cs.groupby("timestamp")["ret_1h"].rank(ascending=False, method="first")
    return cs.sort_values(["timestamp", "pair"]).reset_index(drop=True)


def _score(df: pd.DataFrame, cols: List[str], mu: pd.Series, sigma: pd.Series, w: np.ndarray) -> np.ndarray:
    z = (df[cols] - mu) / sigma
    return z.to_numpy(dtype=float) @ w


def run() -> Dict:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts_label = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    hold_bars = 6
    top_rank = 3
    top_k = 3
    # Maker-biased execution assumption for liquid USDT pairs.
    commission = 0.0003

    data_by_pair = _load_universe(DB_PATH)
    cs = _build_feature_frame(data_by_pair, hold_bars=hold_bars)

    unique_ts = cs["timestamp"].sort_values().unique()
    split_idx = int(len(unique_ts) * 0.7)
    split_ts = unique_ts[split_idx]

    study_mask = (cs["rank_daily"] <= top_rank) | (cs["rank_hourly"] <= top_rank)
    train = cs[(cs["timestamp"] <= split_ts) & study_mask].copy()
    test = cs[(cs["timestamp"] > split_ts)].copy()

    long_cols = ["ret_24h", "ret_1h", "ret_6h", "vol_ratio", "dist_ema", "dist_high", "range_norm"]
    short_cols = ["ret_24h", "ret_1h", "vol_ratio", "upper_wick", "dist_ema", "dist_high", "range_norm"]

    mu_long = train[long_cols].mean()
    sigma_long = train[long_cols].std().replace(0, 1.0)
    x_long = ((train[long_cols] - mu_long) / sigma_long).to_numpy(dtype=float)
    y_long = train["future_ret"].to_numpy(dtype=float)
    w_long = _ridge_fit(x_long, y_long, l2=0.35)

    short_train = train[train["rank_daily"] <= top_rank].copy()
    mu_short = short_train[short_cols].mean()
    sigma_short = short_train[short_cols].std().replace(0, 1.0)
    x_short = ((short_train[short_cols] - mu_short) / sigma_short).to_numpy(dtype=float)
    y_short = (-short_train["future_ret"]).to_numpy(dtype=float)
    w_short = _ridge_fit(x_short, y_short, l2=0.45)

    test["long_score"] = _score(test, long_cols, mu_long, sigma_long, w_long)
    test["short_score"] = _score(test, short_cols, mu_short, sigma_short, w_short)

    bar_returns: List[float] = []
    long_trade_pnls: List[float] = []
    short_trade_pnls: List[float] = []
    bar_rows: List[Dict] = []

    for t, g in test.groupby("timestamp", sort=True):
        longs = g.sort_values("long_score", ascending=False).head(top_k)
        short_candidates = g[g["rank_daily"] <= max(top_rank, top_k + 1)]
        if short_candidates.empty:
            short_candidates = g
        shorts = short_candidates.sort_values("short_score", ascending=False).head(top_k)

        long_rets = (longs["future_ret"] - 2.0 * commission).tolist()
        short_rets = (-shorts["future_ret"] - 2.0 * commission).tolist()
        long_trade_pnls.extend(long_rets)
        short_trade_pnls.extend(short_rets)

        long_avg = float(np.mean(long_rets)) if long_rets else 0.0
        short_avg = float(np.mean(short_rets)) if short_rets else 0.0
        bundle_ret = 0.5 * long_avg + 0.5 * short_avg
        bar_returns.append(bundle_ret)

        bar_rows.append(
            {
                "timestamp": pd.Timestamp(t).isoformat(),
                "bundle_return": round(bundle_ret, 6),
                "long_avg_return": round(long_avg, 6),
                "short_avg_return": round(short_avg, 6),
                "long_symbols": ",".join(longs["pair"].tolist()),
                "short_symbols": ",".join(shorts["pair"].tolist()),
            }
        )

    ret_arr = np.array(bar_returns, dtype=float)
    equity = np.cumprod(1.0 + ret_arr) if len(ret_arr) else np.array([1.0])

    sharpe = 0.0
    if len(ret_arr) > 1 and np.std(ret_arr) > 0:
        sharpe = float(np.mean(ret_arr) / np.std(ret_arr) * np.sqrt(24 * 365))

    long_arr = np.array(long_trade_pnls, dtype=float) if long_trade_pnls else np.array([0.0])
    short_arr = np.array(short_trade_pnls, dtype=float) if short_trade_pnls else np.array([0.0])

    latest_ts = cs["timestamp"].max()
    live = cs[cs["timestamp"] == latest_ts].copy()
    live["long_score"] = _score(live, long_cols, mu_long, sigma_long, w_long)
    live["short_score"] = _score(live, short_cols, mu_short, sigma_short, w_short)

    live_longs = live.sort_values("long_score", ascending=False).head(top_k)
    live_shorts = live[live["rank_daily"] <= max(top_rank, top_k + 1)].sort_values("short_score", ascending=False).head(top_k)

    def _row_to_pick(row: pd.Series, side: str) -> Dict:
        return {
            "pair": row["pair"],
            "side": side,
            "score": round(float(row["long_score"] if side == "LONG" else row["short_score"]), 4),
            "ret_1h": round(float(row["ret_1h"]), 5),
            "ret_24h": round(float(row["ret_24h"]), 5),
            "vol_ratio": round(float(row["vol_ratio"]), 4),
            "upper_wick": round(float(row["upper_wick"]), 4),
            "dist_ema": round(float(row["dist_ema"]), 5),
        }

    daily_focus = train[train["rank_daily"] <= top_rank]
    hourly_focus = train[train["rank_hourly"] <= top_rank]

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {
            "hold_bars": hold_bars,
            "top_rank_for_study": top_rank,
            "top_k_picks_each_side": top_k,
            "commission_per_side": commission,
            "pairs": sorted(data_by_pair.keys()),
            "train_split_timestamp": pd.Timestamp(split_ts).isoformat(),
        },
        "reverse_engineering": {
            "study_rows": int(len(train)),
            "top_daily_rows": int(len(daily_focus)),
            "top_hourly_rows": int(len(hourly_focus)),
            "top_daily_avg_future_ret_6h": round(float(daily_focus["future_ret"].mean()), 6),
            "top_hourly_avg_future_ret_6h": round(float(hourly_focus["future_ret"].mean()), 6),
            "long_feature_weights": {k: round(float(v), 6) for k, v in zip(long_cols, w_long)},
            "short_feature_weights": {k: round(float(v), 6) for k, v in zip(short_cols, w_short)},
        },
        "backtest": {
            "bars_tested": int(len(bar_returns)),
            "bundle_sharpe": round(sharpe, 4),
            "bundle_win_rate": round(float((ret_arr > 0).mean()) if len(ret_arr) else 0.0, 4),
            "bundle_total_return": round(float(equity[-1] - 1.0) if len(equity) else 0.0, 6),
            "bundle_max_drawdown": round(_drawdown(equity) if len(equity) else 0.0, 6),
            "long_trade_count": int(len(long_trade_pnls)),
            "long_hit_rate": round(float((long_arr > 0).mean()) if len(long_arr) else 0.0, 4),
            "short_trade_count": int(len(short_trade_pnls)),
            "short_hit_rate": round(float((short_arr > 0).mean()) if len(short_arr) else 0.0, 4),
        },
        "latest_picks": {
            "timestamp": pd.Timestamp(latest_ts).isoformat(),
            "long": [_row_to_pick(r, "LONG") for _, r in live_longs.iterrows()],
            "short": [_row_to_pick(r, "SHORT") for _, r in live_shorts.iterrows()],
        },
    }

    out_json = RESULTS_DIR / f"pre_skyrocket_long_short_bundle_{ts_label}.json"
    out_csv = RESULTS_DIR / f"pre_skyrocket_long_short_bundle_{ts_label}.csv"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pd.DataFrame(bar_rows).to_csv(out_csv, index=False)

    print(f"Saved: {out_json}")
    print(f"Saved: {out_csv}")
    print(
        "Backtest | Sharpe={:.4f} WinRate={:.2%} Return={:.2%} MaxDD={:.2%} LongHit={:.2%} ShortHit={:.2%}".format(
            summary["backtest"]["bundle_sharpe"],
            summary["backtest"]["bundle_win_rate"],
            summary["backtest"]["bundle_total_return"],
            summary["backtest"]["bundle_max_drawdown"],
            summary["backtest"]["long_hit_rate"],
            summary["backtest"]["short_hit_rate"],
        )
    )
    print("Latest LONG picks:", ", ".join([p["pair"] for p in summary["latest_picks"]["long"]]))
    print("Latest SHORT picks:", ", ".join([p["pair"] for p in summary["latest_picks"]["short"]]))
    return summary


if __name__ == "__main__":
    run()
