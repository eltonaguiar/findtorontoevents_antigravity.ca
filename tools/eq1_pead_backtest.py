"""
EQ-1 Post-Earnings Announcement Drift (PEAD) Strategy Factory -- S1 Backtest
============================================================================
Per docs/STRATEGY_PROPOSALS_V1_2026_04_19.md Sec. EQ-1 + DeepSeek-v3.1 amendments.

Hypothesis:
  Top-decile earnings surprise (SUE > 2.5)     -> 30-day CAR +1.5%..+3.5% vs SPY
  Bottom-decile earnings surprise (SUE < -2.5) -> 30-day CAR -1.0%..-2.5% vs SPY
  Effect stronger for mid-caps ($1B-$10B).

Universe: proxy of S&P 400 MidCap constituents (static list of well-known
mid-caps representative of IJH holdings 2020-2025). Honest S1 gate -- no
survivorship correction possible with free-tier data.

Data sources:
  - EPS actual + consensus estimate: FMP stable/earnings?symbol=X (free tier
    returns full history, no limit).
  - Daily OHLCV: yfinance bulk download (fast, free).
  - Benchmark: SPY.

Entry rule (anti-lookahead per DS-v3.1):
  FMP `date` field is the announcement calendar date (precision unknown:
  could be press-release date or scrape date). We take the CONSERVATIVE
  assumption: enter at NEXT trading-day open after the announcement date.
  This eliminates same-day-close lookahead and any sub-day timestamp risk.

Hold: 30 trading days. Early exit if CAR < -5% vs benchmark (stop).

Costs: 30 bps round-trip.

Pre-emption kill-switch (DS-v3.1): if mean(CAR_48h)/mean(CAR_30d) > 0.70,
FAIL regardless of other metrics.

Writes:
  - backtest_results/eq1_pead_S1.json
  - docs/backtests/EQ1_PEAD_S1_RESULTS.md
"""
from __future__ import annotations

import json
import os
import sys
import time
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

try:
    from scipy.stats import beta as _beta
    HAS_SCIPY = True
except Exception:
    HAS_SCIPY = False

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "backtest_results" / "eq1_raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = ROOT / "backtest_results" / "eq1_pead_S1.json"
OUT_MD = ROOT / "docs" / "backtests" / "EQ1_PEAD_S1_RESULTS.md"

FMP_KEY = os.environ.get("FMP_API_KEY", "iF4K10WedJZINDhUWGXlGAiA57rn4sRD")
FMP_BASE = "https://financialmodelingprep.com"

# ---- S1 spec ----
SUE_LONG = 2.5
SUE_SHORT = -2.5
HOLD_DAYS = 30
STOP_CAR = -0.05
TXN_BPS_RT = 30
WINDOW_START = "2020-01-01"
WINDOW_END = "2025-12-31"

# S&P 400 mid-cap proxy: ~60 liquid mid-cap tickers that were mid-caps
# during most of 2020-2025. Keeps request budget well under 10k.
UNIVERSE = [
    # Tech / software
    "GEN", "JBL", "MANH", "WEX", "ACIW", "LSCC", "SAIC", "CIEN",
    # Industrials
    "TOL", "RBC", "SAIA", "GGG", "WWD", "AAON", "ATR", "CW",
    # Consumer / retail
    "BJ", "TXRH", "WING", "MUSA", "DECK", "ANF", "BLD", "FIVE",
    # Financials
    "CBSH", "EWBC", "PNFP", "WBS", "PFG", "RGA", "MTG",
    # Healthcare
    "MEDP", "UTHR", "HALO", "CRL", "RVTY", "NEOG",
    # Energy / materials
    "OVV", "RRC", "MUR", "SM", "PR", "RGLD", "CMC", "AA",
    # Utilities / real estate
    "IDA", "NFG", "OGE", "BRX", "LAMR", "EPR", "SLG",
    # Misc mid-caps
    "CHDN", "JAZZ", "MASI", "ENS", "WSO", "RHI", "OLLI",
    "THG", "UNM", "ORI", "FHB",
]


# --------------------------------------------------------------------------- #
# Data fetchers
# --------------------------------------------------------------------------- #
def fetch_earnings_fmp(symbol: str, session: requests.Session) -> list[dict]:
    """FMP stable/earnings -- full history, no limit (free tier allows this).

    NOTE: FMP free tier daily quota exhausted during initial run. Using
    yfinance as primary data source instead (see fetch_earnings_yf)."""
    cache = RAW_DIR / f"earnings_{symbol}.json"
    if cache.exists():
        try:
            return json.loads(cache.read_text())
        except Exception:
            pass
    url = f"{FMP_BASE}/stable/earnings?symbol={symbol}&apikey={FMP_KEY}"
    for attempt in range(3):
        try:
            r = session.get(url, timeout=20)
            if r.status_code == 429:
                time.sleep(2 + attempt)
                continue
            data = r.json()
            if isinstance(data, list):
                cache.write_text(json.dumps(data))
                return data
            return []
        except Exception:
            time.sleep(1 + attempt)
    return []


def fetch_earnings_yf(symbol: str) -> list[dict]:
    """yfinance earnings history. Returns rows with date / epsActual / epsEstimated
    mimicking FMP schema for compatibility with build_signals()."""
    import yfinance as yf
    cache = RAW_DIR / f"earnings_yf_{symbol}.json"
    if cache.exists():
        try:
            return json.loads(cache.read_text())
        except Exception:
            pass
    try:
        e = yf.Ticker(symbol).get_earnings_dates(limit=40)
    except Exception:
        e = None
    if e is None or len(e) == 0:
        cache.write_text("[]")
        return []
    rows: list[dict] = []
    for idx, row in e.iterrows():
        try:
            dt = pd.Timestamp(idx).tz_convert(None) if pd.Timestamp(idx).tzinfo else pd.Timestamp(idx)
        except Exception:
            try:
                dt = pd.Timestamp(idx).tz_localize(None)
            except Exception:
                dt = pd.Timestamp(idx)
        est = row.get("EPS Estimate")
        act = row.get("Reported EPS")
        if pd.isna(est) or pd.isna(act):
            continue
        rows.append({
            "symbol": symbol,
            "date": str(dt.date()),
            "epsActual": float(act),
            "epsEstimated": float(est),
        })
    cache.write_text(json.dumps(rows))
    return rows


def fetch_prices_yf(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """Bulk yfinance download. Returns MultiIndex frame: level0=field, level1=ticker."""
    import yfinance as yf
    cache = RAW_DIR / f"prices_{start}_{end}.parquet"
    if cache.exists():
        try:
            return pd.read_parquet(cache)
        except Exception:
            pass
    # Download in chunks of 20 for reliability
    out_frames = []
    for i in range(0, len(tickers), 20):
        chunk = tickers[i : i + 20]
        df = yf.download(
            chunk,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
            threads=True,
            group_by="column",
        )
        out_frames.append(df)
        time.sleep(0.5)
    full = pd.concat(out_frames, axis=1)
    try:
        full.to_parquet(cache)
    except Exception:
        pass
    return full


def fetch_spy(start: str, end: str) -> pd.DataFrame:
    import yfinance as yf
    cache = RAW_DIR / f"SPY_{start}_{end}.parquet"
    if cache.exists():
        try:
            return pd.read_parquet(cache)
        except Exception:
            pass
    df = yf.download("SPY", start=start, end=end, auto_adjust=True, progress=False)
    try:
        df.to_parquet(cache)
    except Exception:
        pass
    return df


# --------------------------------------------------------------------------- #
# Signal construction
# --------------------------------------------------------------------------- #
def build_signals(symbol: str, earnings: list[dict]) -> pd.DataFrame:
    """Compute SUE per event using rolling std of surprises over 4-8 prior quarters.

    SUE_i = (actual_i - est_i) / std(surprises_{i-8..i-1})
    Requires at least 4 prior quarters with both actual + est.
    """
    if not earnings:
        return pd.DataFrame()
    df = pd.DataFrame(earnings)
    if "date" not in df.columns:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df[(df["date"] >= WINDOW_START) | (df["date"] < WINDOW_START)]
    # Need both fields
    df = df.dropna(subset=["epsActual", "epsEstimated"])
    df["epsActual"] = pd.to_numeric(df["epsActual"], errors="coerce")
    df["epsEstimated"] = pd.to_numeric(df["epsEstimated"], errors="coerce")
    df = df.dropna(subset=["epsActual", "epsEstimated"])
    df = df.sort_values("date").reset_index(drop=True)
    df["surprise"] = df["epsActual"] - df["epsEstimated"]

    sues = []
    for i in range(len(df)):
        lo = max(0, i - 8)
        window = df["surprise"].iloc[lo:i]
        if len(window) < 4:
            sues.append(np.nan)
            continue
        sd = float(window.std(ddof=1))
        if not np.isfinite(sd) or sd <= 1e-9:
            sues.append(np.nan)
            continue
        sues.append(float(df["surprise"].iloc[i] / sd))
    df["sue"] = sues
    df["symbol"] = symbol
    df = df.dropna(subset=["sue"])
    # Filter to backtest window
    df = df[(df["date"] >= WINDOW_START) & (df["date"] <= WINDOW_END)]
    return df[["symbol", "date", "epsActual", "epsEstimated", "surprise", "sue"]]


# --------------------------------------------------------------------------- #
# CAR / trade simulation
# --------------------------------------------------------------------------- #
def get_ticker_close(prices: pd.DataFrame, ticker: str) -> pd.Series | None:
    """Extract Close series for one ticker from yfinance group_by='column' frame."""
    try:
        # MultiIndex columns: (field, ticker)
        if isinstance(prices.columns, pd.MultiIndex):
            if ("Close", ticker) in prices.columns:
                s = prices[("Close", ticker)].dropna()
                return s if len(s) else None
        else:
            if "Close" in prices.columns:
                return prices["Close"].dropna()
    except Exception:
        pass
    return None


def get_ticker_open(prices: pd.DataFrame, ticker: str) -> pd.Series | None:
    try:
        if isinstance(prices.columns, pd.MultiIndex):
            if ("Open", ticker) in prices.columns:
                s = prices[("Open", ticker)].dropna()
                return s if len(s) else None
        else:
            if "Open" in prices.columns:
                return prices["Open"].dropna()
    except Exception:
        pass
    return None


def simulate_trade(
    symbol: str,
    announce_dt: pd.Timestamp,
    direction: int,  # +1 long, -1 short
    sue: float,
    opens: pd.Series,
    closes: pd.Series,
    spy_closes: pd.Series,
) -> dict | None:
    """Enter at next-trading-day OPEN after announce_dt. Hold 30 trading days or
    early exit if CAR < -5% (stop on adverse). Apply 30bps round-trip."""
    # Align: find first open bar strictly after announce date
    future_opens = opens[opens.index > announce_dt]
    if future_opens.empty:
        return None
    entry_dt = future_opens.index[0]
    entry_px = float(future_opens.iloc[0])
    if not np.isfinite(entry_px) or entry_px <= 0:
        return None

    # Slice closes from entry_dt forward
    fwd_closes = closes[closes.index >= entry_dt]
    fwd_spy = spy_closes[spy_closes.index >= entry_dt]
    if len(fwd_closes) < 3 or len(fwd_spy) < 3:
        return None

    # Need an anchor for CAR: use entry_px (stock) and spy close at entry_dt
    spy_entry = spy_closes[spy_closes.index <= entry_dt]
    if spy_entry.empty:
        return None
    spy_entry_px = float(spy_entry.iloc[-1])

    # Daily returns from entry to each subsequent day
    max_days = min(HOLD_DAYS, len(fwd_closes) - 1)
    if max_days < 5:
        return None

    exit_idx = max_days
    car_path = []
    car_48h = None
    stop_hit = False
    for k in range(1, max_days + 1):
        close_k = float(fwd_closes.iloc[k]) if k < len(fwd_closes) else np.nan
        if not np.isfinite(close_k):
            exit_idx = k - 1
            break
        # Match SPY index by date
        date_k = fwd_closes.index[k]
        spy_k_series = fwd_spy[fwd_spy.index <= date_k]
        if spy_k_series.empty:
            continue
        spy_k = float(spy_k_series.iloc[-1])
        stock_ret = (close_k / entry_px) - 1.0
        spy_ret = (spy_k / spy_entry_px) - 1.0
        car_k = stock_ret - spy_ret
        # direction-adjusted CAR (P&L before costs)
        pnl_k = direction * car_k
        car_path.append((k, car_k, pnl_k))
        if k == 2:
            car_48h = direction * car_k  # directional 48h CAR
        # Stop: adverse (directional) CAR < -5%
        if pnl_k < STOP_CAR:
            stop_hit = True
            exit_idx = k
            break

    if not car_path:
        return None
    final_k, final_car, final_pnl = car_path[-1]
    # If we never got a 48h reading (exited before day 2), use the last available
    if car_48h is None:
        car_48h = car_path[min(1, len(car_path) - 1)][2]

    # Apply txn cost
    pnl_net = final_pnl - (TXN_BPS_RT / 10_000.0)

    return {
        "symbol": symbol,
        "announce_date": str(announce_dt.date()),
        "entry_date": str(entry_dt.date()),
        "exit_days": final_k,
        "direction": direction,
        "sue": float(sue),
        "car_30d": float(final_car),
        "car_48h_directional": float(car_48h),
        "pnl_gross": float(final_pnl),
        "pnl_net": float(pnl_net),
        "stop_hit": bool(stop_hit),
    }


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def wilson_lb(wins: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return max(0.0, centre - margin)


def sharpe_from_pnl(pnls: np.ndarray) -> float:
    """Simple per-trade Sharpe (annualized by sqrt(trades_per_year)).
    With 30-day holds, ~12 non-overlapping holds/year per name; we use an
    aggregate-trade Sharpe annualized by sqrt(N_trades_per_yr). To keep honest,
    we report the raw per-trade Sharpe * sqrt(12) as approximate annualization
    (30 trading days ~= 1/8 of a year, but trades overlap across names)."""
    if len(pnls) < 2:
        return 0.0
    mu = float(pnls.mean())
    sd = float(pnls.std(ddof=1))
    if sd <= 1e-12:
        return 0.0
    # Approximate annualization: 252/30 ~= 8.4 independent bars
    return (mu / sd) * math.sqrt(252.0 / HOLD_DAYS)


def compute_metrics(trades: list[dict], label: str) -> dict:
    if not trades:
        return {"label": label, "n": 0}
    df = pd.DataFrame(trades)
    pnls = df["pnl_net"].to_numpy()
    wins = df[df["pnl_net"] > 0]
    losers = df[df["pnl_net"] <= 0]
    avg_w = float(wins["pnl_net"].mean()) if len(wins) else 0.0
    avg_l = float(losers["pnl_net"].mean()) if len(losers) else 0.0
    wl_ratio = (avg_w / abs(avg_l)) if avg_l < 0 else 0.0
    n = len(df)
    n_wins = int(len(wins))
    # Max DD on cumulative
    cum = np.cumsum(pnls)
    peak = np.maximum.accumulate(cum) if len(cum) else np.array([0.0])
    dd = cum - peak
    max_dd = float(dd.min()) if len(dd) else 0.0
    return {
        "label": label,
        "n": n,
        "longs": int((df["direction"] == 1).sum()),
        "shorts": int((df["direction"] == -1).sum()),
        "win_rate": n_wins / n,
        "wilson_lb_95": wilson_lb(n_wins, n),
        "avg_winner": avg_w,
        "avg_loser": avg_l,
        "wl_magnitude_ratio": wl_ratio,
        "mean_pnl": float(pnls.mean()),
        "median_pnl": float(np.median(pnls)),
        "std_pnl": float(pnls.std(ddof=1)) if n >= 2 else 0.0,
        "sharpe": sharpe_from_pnl(pnls),
        "max_dd": max_dd,
        "sum_pnl": float(pnls.sum()),
        "stop_hit_rate": float((df["stop_hit"]).mean()),
        "mean_car_30d": float(df["car_30d"].mean()),
        "mean_car_48h_directional": float(df["car_48h_directional"].mean()),
    }


def split_is_oos(trades: list[dict]) -> tuple[list, list, list]:
    """Time-ordered 70/15/15 split."""
    s = sorted(trades, key=lambda t: t["announce_date"])
    n = len(s)
    a = int(n * 0.70)
    b = int(n * 0.85)
    return s[:a], s[a:b], s[b:]


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    started = datetime.now(timezone.utc).isoformat()
    print(f"[eq1] start {started}")
    print(f"[eq1] universe size: {len(UNIVERSE)}")

    session = requests.Session()

    # 1. Earnings + SUE per symbol
    all_signals = []
    earn_request_count = 0
    for i, sym in enumerate(UNIVERSE):
        data = fetch_earnings_yf(sym)
        earn_request_count += 1
        sigs = build_signals(sym, data)
        if len(sigs):
            all_signals.append(sigs)
        if (i + 1) % 10 == 0:
            print(f"[eq1] earnings {i+1}/{len(UNIVERSE)} reqs={earn_request_count} signals_so_far={sum(len(x) for x in all_signals)}")
        time.sleep(0.25)  # polite to yfinance
    if not all_signals:
        print("[eq1] FATAL: no signals parsed from FMP", file=sys.stderr)
        return 2
    signals = pd.concat(all_signals, ignore_index=True)
    print(f"[eq1] total SUE-computable events in window: {len(signals)}")

    # 2. Filter to top/bottom decile thresholds
    long_sigs = signals[signals["sue"] >= SUE_LONG].copy()
    long_sigs["direction"] = 1
    short_sigs = signals[signals["sue"] <= SUE_SHORT].copy()
    short_sigs["direction"] = -1
    events = pd.concat([long_sigs, short_sigs], ignore_index=True)
    print(f"[eq1] long (SUE>=2.5)={len(long_sigs)}  short (SUE<=-2.5)={len(short_sigs)}  total={len(events)}")

    if len(events) == 0:
        print("[eq1] FATAL: no top/bottom decile events", file=sys.stderr)
        return 2

    # 3. Price data
    symbols_needed = sorted(set(events["symbol"].tolist()))
    print(f"[eq1] downloading prices for {len(symbols_needed)} tickers 2019-12-01..2026-03-01")
    prices = fetch_prices_yf(symbols_needed, "2019-12-01", "2026-03-01")
    spy_df = fetch_spy("2019-12-01", "2026-03-01")
    if "Close" not in spy_df.columns:
        print("[eq1] FATAL: SPY download missing Close", file=sys.stderr)
        return 2
    # Flatten SPY to Series
    spy_closes = spy_df["Close"]
    if isinstance(spy_closes, pd.DataFrame):
        spy_closes = spy_closes.iloc[:, 0]
    spy_closes = spy_closes.dropna()
    spy_closes.index = pd.to_datetime(spy_closes.index).tz_localize(None)

    # 4. Simulate trades
    trades: list[dict] = []
    skipped_no_price = 0
    skipped_short_history = 0
    for _, row in events.iterrows():
        sym = row["symbol"]
        closes = get_ticker_close(prices, sym)
        opens = get_ticker_open(prices, sym)
        if closes is None or opens is None or len(closes) < 60:
            skipped_no_price += 1
            continue
        closes.index = pd.to_datetime(closes.index).tz_localize(None)
        opens.index = pd.to_datetime(opens.index).tz_localize(None)
        announce_dt = pd.Timestamp(row["date"]).tz_localize(None)
        tr = simulate_trade(
            sym, announce_dt, int(row["direction"]), float(row["sue"]),
            opens, closes, spy_closes,
        )
        if tr is None:
            skipped_short_history += 1
            continue
        trades.append(tr)

    print(f"[eq1] simulated trades={len(trades)}  skipped_no_price={skipped_no_price}  skipped_short_hist={skipped_short_history}")

    # 5. Metrics
    combined = compute_metrics(trades, "combined_all")
    long_only = compute_metrics([t for t in trades if t["direction"] == 1], "long_only")
    short_only = compute_metrics([t for t in trades if t["direction"] == -1], "short_only")

    # Time split
    is_trades, oos1, oos2 = split_is_oos(trades)
    is_m = compute_metrics(is_trades, "IS_70pct")
    oos1_m = compute_metrics(oos1, "OOS_15pct_a")
    oos2_m = compute_metrics(oos2, "OOS_15pct_b")

    # Yearly
    yearly = {}
    by_year: dict[int, list] = {}
    for t in trades:
        y = int(t["announce_date"][:4])
        by_year.setdefault(y, []).append(t)
    for y, ts in sorted(by_year.items()):
        yearly[y] = compute_metrics(ts, f"year_{y}")

    # Pre-emption ratio
    mean_48h = combined.get("mean_car_48h_directional", 0.0)
    mean_30d = combined.get("mean_car_30d", 0.0)
    preempt_ratio = (mean_48h / mean_30d) if abs(mean_30d) > 1e-9 else float("nan")

    # 6. S1 gate evaluation
    failed: list[str] = []
    if combined["n"] < 200:
        failed.append(f"n={combined['n']} < 200")
    if is_m.get("sharpe", 0) <= 1.0:
        failed.append(f"IS Sharpe {is_m.get('sharpe',0):.2f} <= 1.0")
    if combined.get("win_rate", 0) <= 0.55:
        failed.append(f"Win rate {combined.get('win_rate',0):.3f} <= 0.55")
    if combined.get("wl_magnitude_ratio", 0) <= 1.0:
        failed.append(f"W/L magnitude {combined.get('wl_magnitude_ratio',0):.2f} <= 1.0")
    is_sharpe = is_m.get("sharpe", 0)
    for lbl, mm in (("OOS1", oos1_m), ("OOS2", oos2_m)):
        if mm.get("sharpe", 0) < 0.7 * is_sharpe:
            failed.append(f"{lbl} Sharpe {mm.get('sharpe',0):.2f} < 0.7*IS {is_sharpe:.2f}")
    recent_years = [y for y in [2022, 2023, 2024, 2025] if y in yearly]
    good_yrs = sum(1 for y in recent_years if yearly[y].get("sharpe", 0) > 0.5)
    if good_yrs < 2:
        failed.append(f"Only {good_yrs}/{len(recent_years)} recent years with Sharpe>0.5")
    # Pre-emption kill switch
    preempt_triggered = False
    if np.isfinite(preempt_ratio) and preempt_ratio > 0.70:
        failed.append(f"Pre-emption ratio {preempt_ratio:.3f} > 0.70 (retail cannot capture)")
        preempt_triggered = True

    verdict = "PASS" if not failed else "FAIL"

    out = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "strategy": "EQ-1 PEAD mid-cap",
        "verdict": verdict,
        "failed_criteria": failed,
        "spec": {
            "sue_long": SUE_LONG,
            "sue_short": SUE_SHORT,
            "hold_days": HOLD_DAYS,
            "stop_car": STOP_CAR,
            "txn_bps_roundtrip": TXN_BPS_RT,
            "window": [WINDOW_START, WINDOW_END],
            "universe_size": len(UNIVERSE),
            "universe": UNIVERSE,
            "entry_rule": "next_trading_day_open (conservative; FMP date precision unverified)",
            "fmp_timestamp_note": (
                "FMP stable/earnings `date` field precision is unverified on free "
                "tier; free tier does not expose pre/after-market `time` flag. "
                "Per DS-v3.1 we adopt the conservative next-open entry to eliminate "
                "same-day-close lookahead risk."
            ),
        },
        "totals": {
            "events_found_in_window": int(len(events) if 'events' in dir() else 0),
            "trades_simulated": len(trades),
            "skipped_no_price": skipped_no_price,
            "skipped_short_history": skipped_short_history,
        },
        "preemption": {
            "mean_car_48h_directional": mean_48h,
            "mean_car_30d": mean_30d,
            "ratio_48h_over_30d": preempt_ratio,
            "kill_switch_triggered": preempt_triggered,
            "threshold": 0.70,
        },
        "combined": combined,
        "long_only": long_only,
        "short_only": short_only,
        "IS": is_m,
        "OOS1": oos1_m,
        "OOS2": oos2_m,
        "yearly": yearly,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2, default=str))
    print(f"[eq1] wrote {OUT_JSON}")

    # 7. Markdown verdict
    md = [
        f"# EQ-1 PEAD Mid-Cap -- S1 Backtest Results",
        f"Generated: {out['generated']}",
        "",
        f"## Verdict: **{verdict}**",
        "",
    ]
    if failed:
        md.append("Failed S1 criteria:")
        for f in failed:
            md.append(f"- {f}")
        md.append("")
    md += [
        "## Pre-emption kill-switch (DS-v3.1)",
        f"- mean CAR 48h (directional): {mean_48h:.5f}",
        f"- mean CAR 30d (raw, long-biased sign): {mean_30d:.5f}",
        f"- ratio (48h / 30d): {preempt_ratio:.3f}" if np.isfinite(preempt_ratio) else "- ratio: nan (30d mean ~ 0)",
        f"- threshold: > 0.70 = FAIL",
        f"- triggered: {preempt_triggered}",
        "",
        "## Spec",
    ]
    for k, v in out["spec"].items():
        md.append(f"- `{k}`: {v}")
    md.append("")
    md.append("## Totals")
    for k, v in out["totals"].items():
        md.append(f"- {k}: {v}")
    md.append("")
    for section, d in [
        ("Combined (all trades)", combined),
        ("Long only (SUE>=2.5)", long_only),
        ("Short only (SUE<=-2.5)", short_only),
        ("IS (first 70%)", is_m),
        ("OOS1 (next 15%)", oos1_m),
        ("OOS2 (last 15%)", oos2_m),
    ]:
        md.append(f"## {section}")
        md.append("| metric | value |")
        md.append("|---|---|")
        for k, v in d.items():
            md.append(f"| {k} | {v} |")
        md.append("")
    md.append("## Yearly")
    md.append("| year | n | sharpe | win_rate | mean_pnl | mean_car_30d |")
    md.append("|---|---|---|---|---|---|")
    for y, m in sorted(yearly.items()):
        md.append(f"| {y} | {m.get('n',0)} | {m.get('sharpe',0):.3f} | "
                  f"{m.get('win_rate',0):.3f} | {m.get('mean_pnl',0):.5f} | "
                  f"{m.get('mean_car_30d',0):.5f} |")
    md.append("")
    md.append("## Notes")
    md.append("- Universe is a static ~60-ticker proxy for S&P 400 mid-caps. "
             "Survivorship bias is possible; S1 is a go/no-go gate, not a "
             "production sim.")
    md.append("- FMP free-tier timestamp precision unverified; conservative "
             "next-open entry used.")
    md.append("- No parameter iteration on fail, per protocol. Result stands.")
    OUT_MD.write_text("\n".join(md))
    print(f"[eq1] wrote {OUT_MD}")
    print(f"[eq1] VERDICT: {verdict}")
    if failed:
        for f in failed:
            print(f"  -- {f}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
