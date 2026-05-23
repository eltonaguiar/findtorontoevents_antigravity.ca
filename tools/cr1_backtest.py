"""
CR-1 Funding Rate Reversion Strategy Factory -- S1 Backtest
===========================================================
Per docs/STRATEGY_PROPOSALS_V1_1_AMENDMENTS_2026_04_19.md Sec. 11.

Hypothesis: BTC/ETH perp funding |>0.08%| on 8h window (+optional OI filter)
=> >=0.8% reversion within 12h. Contrarian entry, exit at 12h or SL 1.5x.

S1 pass criteria (hard):
- IS Sharpe > 1.0 post 30bps round-trip
- Win rate > 55% with n>=200
- avg_winner / |avg_loser| > 1.0
- 70/15/15 IS/OOS split; OOS Sharpe >= 0.7 x IS Sharpe
- Sharpe > 0.5 in >=2 of {2023, 2024, 2025}

Writes:
- backtest_results/cr1_funding_reversion_S1.json
- docs/backtests/CR1_FUNDING_REVERSION_S1_RESULTS.md
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

try:
    from scipy.stats import beta as _beta  # noqa: F401
    HAS_SCIPY = True
except Exception:
    HAS_SCIPY = False

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "backtest_results" / "cr1_raw_data"
OUT_JSON = ROOT / "backtest_results" / "cr1_funding_reversion_S1.json"
OUT_MD = ROOT / "docs" / "backtests" / "CR1_FUNDING_REVERSION_S1_RESULTS.md"

RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_MD.parent.mkdir(parents=True, exist_ok=True)

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
FAPI_BASES = ["https://fapi.binance.com", "https://fapi1.binance.com", "https://fapi2.binance.com"]

FUNDING_THRESHOLD = 0.0008  # 0.08%
HOLD_HOURS = 12
SL_MULT = 1.5  # SL at 1.5x the "entry move against"; interpret as 1.5 * |funding|
TXN_COST_BPS = 30  # round-trip
POS_FRAC = 0.005   # 0.5% of 10k = $50
CAPITAL = 10_000.0

# Window: 2023-01-01 -> today
START_MS = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
END_MS = int(datetime.now(timezone.utc).timestamp() * 1000)


def _get(path: str, params: dict, tag: str) -> Any:
    last_err = None
    for base in FAPI_BASES:
        try:
            r = requests.get(base + path, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            last_err = f"{base} -> {r.status_code} {r.text[:120]}"
        except Exception as e:
            last_err = f"{base} -> {e!r}"
        time.sleep(0.2)
    raise RuntimeError(f"[{tag}] all bases failed: {last_err}")


def fetch_funding(symbol: str) -> pd.DataFrame:
    cache = RAW_DIR / f"funding_{symbol}.pkl"
    if cache.exists():
        return pd.read_pickle(cache)
    rows: list[dict] = []
    start = START_MS
    while True:
        data = _get(
            "/fapi/v1/fundingRate",
            {"symbol": symbol, "startTime": start, "limit": 1000},
            f"funding {symbol}",
        )
        if not data:
            break
        rows.extend(data)
        last_t = int(data[-1]["fundingTime"])
        if len(data) < 1000 or last_t >= END_MS:
            break
        start = last_t + 1
        time.sleep(0.15)
    df = pd.DataFrame(rows)
    df["fundingTime"] = pd.to_datetime(df["fundingTime"].astype("int64"), unit="ms", utc=True)
    df["fundingRate"] = df["fundingRate"].astype(float)
    df = df[["fundingTime", "symbol", "fundingRate"]].drop_duplicates("fundingTime").sort_values("fundingTime").reset_index(drop=True)
    df.to_pickle(cache)
    return df


def fetch_klines(symbol: str, interval: str = "1h") -> pd.DataFrame:
    cache = RAW_DIR / f"klines_{symbol}_{interval}.pkl"
    if cache.exists():
        return pd.read_pickle(cache)
    rows: list[list] = []
    start = START_MS
    while True:
        data = _get(
            "/fapi/v1/klines",
            {"symbol": symbol, "interval": interval, "startTime": start, "limit": 1500},
            f"klines {symbol}",
        )
        if not data:
            break
        rows.extend(data)
        last_t = int(data[-1][0])
        if len(data) < 1500 or last_t >= END_MS:
            break
        start = last_t + 1
        time.sleep(0.15)
    cols = ["openTime", "open", "high", "low", "close", "volume",
            "closeTime", "qv", "trades", "tbav", "tbqv", "ignore"]
    df = pd.DataFrame(rows, columns=cols)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    df["openTime"] = pd.to_datetime(df["openTime"].astype("int64"), unit="ms", utc=True)
    df = df[["openTime", "open", "high", "low", "close", "volume"]].drop_duplicates("openTime").sort_values("openTime").reset_index(drop=True)
    df.to_pickle(cache)
    return df


def simulate(symbol: str, funding: pd.DataFrame, klines: pd.DataFrame) -> pd.DataFrame:
    """For each funding event with |rate|>threshold, enter contrarian at next hour close,
    exit at +12h or SL hit. Long if funding<0, short if funding>0."""
    kl = klines.set_index("openTime").sort_index()
    trades: list[dict] = []

    sig = funding[funding["fundingRate"].abs() > FUNDING_THRESHOLD].copy()
    for _, row in sig.iterrows():
        ft = row["fundingTime"]
        rate = float(row["fundingRate"])
        direction = -1 if rate > 0 else 1  # contrarian

        # Entry: next 1h candle open after funding time
        entry_time = ft.ceil("h")
        exit_time = entry_time + pd.Timedelta(hours=HOLD_HOURS)
        if entry_time not in kl.index:
            continue
        entry_px = float(kl.loc[entry_time, "open"])

        window = kl.loc[(kl.index >= entry_time) & (kl.index < exit_time)]
        if window.empty:
            continue

        # SL: 1.5 * |funding rate| against entry
        sl_move = SL_MULT * abs(rate)
        if direction == 1:  # long
            sl_px = entry_px * (1 - sl_move)
            # check each bar chronologically for SL hit
            sl_hit_idx = window.index[window["low"] <= sl_px]
        else:  # short
            sl_px = entry_px * (1 + sl_move)
            sl_hit_idx = window.index[window["high"] >= sl_px]

        if len(sl_hit_idx) > 0:
            exit_px = sl_px
            exit_t = sl_hit_idx[0]
            sl_hit = True
        else:
            last = window.iloc[-1]
            exit_px = float(last["close"])
            exit_t = last.name
            sl_hit = False

        if direction == 1:
            gross_bps = (exit_px / entry_px - 1.0) * 10_000
        else:
            gross_bps = (entry_px / exit_px - 1.0) * 10_000
        net_bps = gross_bps - TXN_COST_BPS

        hold_h = (exit_t - entry_time).total_seconds() / 3600.0
        trades.append(dict(
            symbol=symbol,
            funding_time=ft,
            entry_time=entry_time,
            exit_time=exit_t,
            funding_rate=rate,
            direction=direction,
            entry_px=entry_px,
            exit_px=exit_px,
            gross_bps=gross_bps,
            net_bps=net_bps,
            sl_hit=sl_hit,
            hold_hours=hold_h,
        ))
    return pd.DataFrame(trades)


def _sharpe(returns_bps: np.ndarray) -> float:
    if len(returns_bps) < 2:
        return 0.0
    r = returns_bps / 10_000.0
    std = r.std(ddof=1)
    if std == 0:
        return 0.0
    # Signals occur at funding events (~3/day). Roughly ~1000/yr per symbol if every event triggered.
    # Annualize conservatively by sqrt(signals_per_year). We'll compute an per-trade Sharpe scaled by sqrt(N_year_avg).
    # Simpler robust choice: sqrt(annualization factor based on ~3 funding events/day * 365 = 1095 opportunities/yr, but
    # only a fraction trigger. Use sqrt(252) treating each trade as a daily-equivalent return -- matches typical Sharpe reporting.)
    return (r.mean() / std) * np.sqrt(252)


def _wilson_lb(wins: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    adj = z * np.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return (centre - adj) / denom


def stats_block(trades: pd.DataFrame, label: str) -> dict:
    if trades.empty:
        return {"label": label, "n": 0}
    r = trades["net_bps"].to_numpy()
    wins = int((r > 0).sum())
    n = len(r)
    winners = r[r > 0]
    losers = r[r <= 0]
    avg_w = float(winners.mean()) if len(winners) else 0.0
    avg_l = float(losers.mean()) if len(losers) else 0.0
    wl_ratio = (avg_w / abs(avg_l)) if avg_l != 0 else float("inf") if avg_w > 0 else 0.0
    equity = np.cumsum(r)
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    return {
        "label": label,
        "n": n,
        "win_rate": wins / n,
        "wilson_lb_95": _wilson_lb(wins, n),
        "avg_winner_bps": avg_w,
        "avg_loser_bps": avg_l,
        "wl_magnitude_ratio": wl_ratio,
        "mean_bps": float(r.mean()),
        "median_bps": float(np.median(r)),
        "std_bps": float(r.std(ddof=1)) if n > 1 else 0.0,
        "sharpe": _sharpe(r),
        "max_dd_bps": float(dd.min()) if n else 0.0,
        "sum_bps": float(r.sum()),
        "sl_hit_rate": float(trades["sl_hit"].mean()),
        "avg_hold_h": float(trades["hold_hours"].mean()),
        "longs": int((trades["direction"] == 1).sum()),
        "shorts": int((trades["direction"] == -1).sum()),
    }


def main() -> int:
    print("[cr1] fetching data...")
    all_trades = []
    for sym in SYMBOLS:
        print(f"  funding {sym}")
        f = fetch_funding(sym)
        print(f"    rows={len(f)} range={f['fundingTime'].min()} -> {f['fundingTime'].max()}")
        print(f"  klines {sym}")
        k = fetch_klines(sym, "1h")
        print(f"    rows={len(k)} range={k['openTime'].min()} -> {k['openTime'].max()}")
        t = simulate(sym, f, k)
        print(f"    signals: {len(t)}")
        all_trades.append(t)

    trades = pd.concat(all_trades, ignore_index=True).sort_values("entry_time").reset_index(drop=True)
    print(f"[cr1] total trades: {len(trades)}")

    results: dict[str, Any] = {
        "spec": {
            "funding_threshold": FUNDING_THRESHOLD,
            "hold_hours": HOLD_HOURS,
            "sl_mult": SL_MULT,
            "txn_cost_bps_roundtrip": TXN_COST_BPS,
            "symbols": SYMBOLS,
            "window_start": "2023-01-01",
            "window_end_ms": END_MS,
            "oi_filter_applied": False,
            "oi_filter_note": "Binance openInterestHist endpoint only returns ~30d of history on free tier; documented and omitted per spec fallback.",
        },
        "combined": stats_block(trades, "combined_all"),
        "per_symbol": {s: stats_block(trades[trades.symbol == s], s) for s in SYMBOLS},
        "per_direction": {
            "long": stats_block(trades[trades.direction == 1], "long"),
            "short": stats_block(trades[trades.direction == -1], "short"),
        },
    }

    # 70/15/15 IS/OOS split (chronological)
    n = len(trades)
    if n > 0:
        i1 = int(n * 0.70)
        i2 = int(n * 0.85)
        IS = trades.iloc[:i1]
        OOS1 = trades.iloc[i1:i2]
        OOS2 = trades.iloc[i2:]
        results["splits"] = {
            "IS": stats_block(IS, "IS_70"),
            "OOS1": stats_block(OOS1, "OOS1_15"),
            "OOS2": stats_block(OOS2, "OOS2_15"),
        }
    else:
        results["splits"] = {}

    # Per-year
    trades["year"] = trades["entry_time"].dt.year
    results["per_year"] = {
        int(y): stats_block(trades[trades.year == y], f"year_{y}")
        for y in sorted(trades["year"].dropna().unique())
    }

    # Hold time distribution
    if n:
        results["hold_time_distribution"] = {
            "min_h": float(trades["hold_hours"].min()),
            "p25_h": float(trades["hold_hours"].quantile(0.25)),
            "median_h": float(trades["hold_hours"].median()),
            "p75_h": float(trades["hold_hours"].quantile(0.75)),
            "max_h": float(trades["hold_hours"].max()),
            "sl_hit_rate": float(trades["sl_hit"].mean()),
        }

    # S1 pass/fail evaluation
    failures: list[str] = []
    comb = results["combined"]
    if comb.get("n", 0) < 200:
        failures.append(f"n={comb.get('n',0)} < 200")
    if comb.get("sharpe", 0) <= 1.0:
        failures.append(f"IS-combined Sharpe {comb.get('sharpe',0):.2f} <= 1.0")
    if comb.get("win_rate", 0) <= 0.55:
        failures.append(f"Win rate {comb.get('win_rate',0):.3f} <= 0.55")
    if comb.get("wl_magnitude_ratio", 0) <= 1.0:
        failures.append(f"W/L magnitude ratio {comb.get('wl_magnitude_ratio',0):.2f} <= 1.0")

    sp = results.get("splits", {})
    is_sh = sp.get("IS", {}).get("sharpe", 0.0)
    oos1_sh = sp.get("OOS1", {}).get("sharpe", 0.0)
    oos2_sh = sp.get("OOS2", {}).get("sharpe", 0.0)
    if is_sh and abs(oos1_sh) < 0.7 * abs(is_sh):
        failures.append(f"OOS1 Sharpe {oos1_sh:.2f} < 0.7 x IS {is_sh:.2f}")
    if is_sh and abs(oos2_sh) < 0.7 * abs(is_sh):
        failures.append(f"OOS2 Sharpe {oos2_sh:.2f} < 0.7 x IS {is_sh:.2f}")

    years_ok = sum(1 for y, s in results["per_year"].items() if s.get("sharpe", 0) > 0.5 and y in (2023, 2024, 2025))
    if years_ok < 2:
        failures.append(f"Only {years_ok}/3 yearly sub-windows (2023/2024/2025) with Sharpe>0.5")

    verdict = "PASS" if not failures else "FAIL"
    results["verdict"] = verdict
    results["failed_criteria"] = failures
    results["has_scipy"] = HAS_SCIPY
    results["generated_utc"] = datetime.now(timezone.utc).isoformat()

    # Save trades
    trades_out = RAW_DIR / "trades.csv"
    trades.to_csv(trades_out, index=False)
    results["trades_csv"] = str(trades_out.relative_to(ROOT)).replace("\\", "/")

    OUT_JSON.write_text(json.dumps(results, default=str, indent=2))
    print(f"[cr1] wrote {OUT_JSON}")

    # Markdown report
    md = []
    md.append(f"# CR-1 Funding Rate Reversion -- S1 Backtest Results\n")
    md.append(f"Generated: {results['generated_utc']}\n")
    md.append(f"\n## Verdict: **{verdict}**\n")
    if failures:
        md.append("\nFailed S1 criteria:\n")
        for f in failures:
            md.append(f"- {f}\n")
    md.append("\n## Spec\n")
    for k, v in results["spec"].items():
        md.append(f"- `{k}`: {v}\n")
    md.append("\n## Combined (all trades, all symbols)\n")
    md.append("| metric | value |\n|---|---|\n")
    for k, v in comb.items():
        md.append(f"| {k} | {v} |\n")
    md.append("\n## Per symbol\n")
    for s, blk in results["per_symbol"].items():
        md.append(f"### {s}\n")
        for k, v in blk.items():
            md.append(f"- {k}: {v}\n")
    md.append("\n## IS/OOS splits (70/15/15)\n")
    for lbl, blk in results["splits"].items():
        md.append(f"### {lbl}\n")
        for k, v in blk.items():
            md.append(f"- {k}: {v}\n")
    md.append("\n## Per year\n")
    for y, blk in results["per_year"].items():
        md.append(f"### {y}\n")
        for k, v in blk.items():
            md.append(f"- {k}: {v}\n")
    md.append("\n## Per direction\n")
    for d, blk in results["per_direction"].items():
        md.append(f"### {d}\n")
        for k, v in blk.items():
            md.append(f"- {k}: {v}\n")
    if "hold_time_distribution" in results:
        md.append("\n## Hold time distribution\n")
        for k, v in results["hold_time_distribution"].items():
            md.append(f"- {k}: {v}\n")
    md.append(f"\n## Notes\n- scipy available: {HAS_SCIPY}\n")
    md.append("- OI filter omitted: Binance `/futures/data/openInterestHist` returns only ~30 days of history on the public endpoint; per spec we documented and proceeded without the OI filter for this first pass.\n")
    md.append(f"- Raw trades: `{results['trades_csv']}`\n")
    md.append("- Per v1.1 spec: **if FAIL, archive; do NOT iterate parameters to force a pass.**\n")

    OUT_MD.write_text("".join(md), encoding="utf-8")
    print(f"[cr1] wrote {OUT_MD}")
    print(f"[cr1] VERDICT: {verdict}")
    if failures:
        for f in failures:
            print(f"  - FAIL: {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
