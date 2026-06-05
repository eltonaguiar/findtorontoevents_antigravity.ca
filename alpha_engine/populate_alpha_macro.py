#!/usr/bin/env python3
"""populate_alpha_macro.py — Daily macro snapshot populator for `alpha_macro` table.

Populates the 5 macro indicators + regime label that all 5-axis scrutiny,
walk-forward, and FOREX regime analysis tools join against:
  - VIX (^VIX close) — implied volatility regime
  - SPY close + SPY SMA50 + SPY SMA200 — equity trend regime
  - 10Y yield (^TNX) — long-rate level
  - 5Y yield (^FVX) — mid-curve proxy for 2Y yield (yfinance lacks ^FVX is 5Y)
  - DXY (DX-Y.NYB) close + SMA50 — dollar trend regime
  - regime / regime_score / regime_detail — combined macro label

Why this script exists
----------------------
`alpha_macro` is read by `tools/walk_forward_per_strategy.py --require-macro-join`
and the FOREX regime deep-dive. As of 2026-06-05 it ends at 2026-04-27
(38 days stale), which means 88% of cta_cross_asset_tsmom forex trades can't
join macro data and the walk-forward cannot test regime stability for them
(reports/deep_dive_forex_regime_2026-06-05.md). This script:
  1. Fetches the last `lookback_days` of macro data from yfinance
  2. Computes SMAs and regime label
  3. UPSERTs into `alpha_macro` (idempotent — safe to re-run daily)

Operational notes
-----------------
- Source: yfinance (free, no API key needed)
- Schedule: daily cron at 21:00 UTC (after US market close at 20:00 UTC,
  data is settled by 21:00)
- Idempotent: re-running for the same date updates the existing row
- Failure-tolerant: if a single ticker fails, log and continue
- Lookback default: 60 days (covers SMA200 partial calculation)

Output: writes to `ejaguiar1_stocks.alpha_macro` via tools.db_env.get_stocks_creds().
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import pymysql
import pymysql.cursors
import yfinance as yf
from tools.db_env import get_stocks_creds

# Mapping: yfinance ticker → (alpha_macro column, transform)
# transform: 'close' = use as-is, 'identity' = no transform
TICKERS = {
    "^VIX":     ("vix_close",   "close"),
    "SPY":      ("spy_close",   "close"),
    "^TNX":     ("tnx_close",   "close"),    # 10Y yield in %
    "^FVX":     ("two_yr_yield","close"),    # 5Y used as 2Y proxy (yfinance limitation)
    "DX-Y.NYB": ("dxy_close",   "close"),    # dollar index
}

SMA_WINDOWS = {"spy_sma50": 50, "spy_sma200": 200, "dxy_sma50": 50}
DEFAULT_LOOKBACK_DAYS = 270  # need 200 days for SPY SMA200
BATCH_INSERT_CHUNK = 30


def _f(x):
    return float(x) if isinstance(x, Decimal) else x


def fetch_history(ticker: str, lookback_days: int) -> "pd.DataFrame | None":
    """Fetch ticker history; return DataFrame indexed by date with 'Close' column."""
    try:
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=lookback_days)
        t = yf.Ticker(ticker)
        df = t.history(start=start.isoformat(), end=end.isoformat(), auto_adjust=False)
        if df is None or df.empty:
            print(f"  [WARN] {ticker}: empty history", file=sys.stderr)
            return None
        # Use 'Close' (or 'Adj Close' if Close missing). yfinance >=0.2 returns
        # both; prefer 'Close' for raw index values.
        if "Close" not in df.columns and "Adj Close" in df.columns:
            df = df.rename(columns={"Adj Close": "Close"})
        df = df[["Close"]].copy()
        # Drop timezone + convert to date so the index matches MySQL DATE values
        # (avoids tz-naive vs tz-aware comparison in .loc[:date] slicing)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.index = df.index.date
        return df
    except Exception as e:
        print(f"  [ERR ] {ticker}: {e}", file=sys.stderr)
        return None


def compute_regime(vix, spy, spy_sma50, spy_sma200, tnx, dxy, dxy_sma50) -> tuple[str, int, str]:
    """Compute (regime_label, regime_score, regime_detail_json).

    Returns 'unknown'/0/'{}' if any required input is None.

    Regime labels (single-word for the `regime` column):
      - calm_bull: VIX<20 + SPY>SMA200
      - calm_bear: VIX<20 + SPY<SMA200
      - vol_bull:  20<=VIX<30 + SPY>SMA200
      - vol_bear:  20<=VIX<30 + SPY<SMA200
      - crisis:    VIX>=30
    regime_score is 0-100 (higher = more bullish).
    """
    if any(x is None for x in (vix, spy, spy_sma50, spy_sma200, tnx, dxy, dxy_sma50)):
        return "unknown", 0, "{}"
    bull_eq = spy > spy_sma200
    above_sma50 = spy > spy_sma50
    dxy_strong = dxy > dxy_sma50

    if vix >= 30:
        label = "crisis"
        score = 10
    elif vix >= 20:
        label = "vol_bull" if bull_eq else "vol_bear"
        score = 40 if bull_eq else 25
    else:
        label = "calm_bull" if bull_eq else "calm_bear"
        score = 70 if bull_eq else 50

    # Yield-curve adjustment
    if tnx < 2.0:
        score -= 10  # very low yields = recession risk
    if not dxy_strong:
        score += 5  # weak dollar = risk-on tailwind for non-USD assets

    score = max(0, min(100, score))
    detail = {
        "vix": round(vix, 2),
        "spy": round(spy, 2),
        "tnx": round(tnx, 3),
        "dxy": round(dxy, 2),
        "spy_above_sma50": int(above_sma50),
        "dxy_above_sma50": int(dxy_strong),
    }
    return label, score, str(detail).replace("'", '"')  # JSON-compatible


def upsert_rows(cur, rows: list[dict]) -> int:
    """UPSERT rows into alpha_macro. Returns count upserted."""
    if not rows:
        return 0
    upserted = 0
    for chunk_start in range(0, len(rows), BATCH_INSERT_CHUNK):
        chunk = rows[chunk_start:chunk_start + BATCH_INSERT_CHUNK]
        for r in chunk:
            cur.execute("""
                INSERT INTO alpha_macro
                    (trade_date, vix_close, spy_close, spy_sma50, spy_sma200,
                     tnx_close, two_yr_yield, yield_spread, dxy_close, dxy_sma50,
                     regime, regime_score, regime_detail)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    vix_close = VALUES(vix_close),
                    spy_close = VALUES(spy_close),
                    spy_sma50 = VALUES(spy_sma50),
                    spy_sma200 = VALUES(spy_sma200),
                    tnx_close = VALUES(tnx_close),
                    two_yr_yield = VALUES(two_yr_yield),
                    yield_spread = VALUES(yield_spread),
                    dxy_close = VALUES(dxy_close),
                    dxy_sma50 = VALUES(dxy_sma50),
                    regime = VALUES(regime),
                    regime_score = VALUES(regime_score),
                    regime_detail = VALUES(regime_detail)
            """, (
                r["trade_date"],
                r["vix_close"],
                r["spy_close"],
                r["spy_sma50"],
                r["spy_sma200"],
                r["tnx_close"],
                r["two_yr_yield"],
                r["yield_spread"],
                r["dxy_close"],
                r["dxy_sma50"],
                r["regime"],
                r["regime_score"],
                r["regime_detail"],
            ))
            upserted += 1
    return upserted


def main() -> int:
    ap = argparse.ArgumentParser(description="Populate alpha_macro from yfinance")
    ap.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS,
                    help=f"Lookback window in days (default {DEFAULT_LOOKBACK_DAYS})")
    ap.add_argument("--dry-run", action="store_true",
                    help="Compute the rows but don't write to DB")
    args = ap.parse_args()

    print(f"[populate_alpha_macro] start UTC={datetime.now(timezone.utc).isoformat()[:19]}")
    print(f"[populate_alpha_macro] lookback={args.lookback_days}d dry_run={args.dry_run}")

    # Fetch all tickers
    print("[populate_alpha_macro] fetching yfinance data...")
    histories: dict[str, "pd.DataFrame"] = {}
    for ticker in TICKERS:
        df = fetch_history(ticker, args.lookback_days)
        if df is not None:
            histories[ticker] = df
            print(f"  {ticker}: {len(df)} rows ({df.index.min()} → {df.index.max()})")

    if not histories:
        print("[populate_alpha_macro] ERR: no histories fetched", file=sys.stderr)
        return 1

    # Find common trading dates (intersection of all ticker dates)
    date_sets = [set(df.index) for df in histories.values()]
    common_dates = sorted(set.intersection(*date_sets))
    if not common_dates:
        # Fallback: use SPY dates as the spine (most liquid)
        spy_dates = sorted(set(histories.get("SPY", next(iter(histories.values()))).index))
        common_dates = spy_dates
        print(f"[populate_alpha_macro] WARN: no common dates; using SPY spine ({len(common_dates)} dates)")
    else:
        print(f"[populate_alpha_macro] {len(common_dates)} common trading dates")

    # Compute rows
    rows = []
    spy = histories.get("SPY")
    dxy = histories.get("DX-Y.NYB")
    for d in common_dates:
        try:
            vix_v = float(histories["^VIX"].loc[d, "Close"])
            spy_v = float(histories["SPY"].loc[d, "Close"])
            tnx_v = float(histories["^TNX"].loc[d, "Close"])
            fvx_v = float(histories["^FVX"].loc[d, "Close"])
            dxy_v = float(histories["DX-Y.NYB"].loc[d, "Close"])
        except (KeyError, ValueError, TypeError) as e:
            print(f"  [WARN] {d}: missing data ({e})", file=sys.stderr)
            continue

        # SMAs: average of last N closes up to and including `d`
        def sma(series, window):
            sub = series.loc[:d].tail(window)
            return float(sub["Close"].mean()) if len(sub) >= window else None

        spy_sma50 = sma(spy, 50) if spy is not None else None
        spy_sma200 = sma(spy, 200) if spy is not None else None
        dxy_sma50 = sma(dxy, 50) if dxy is not None else None
        yield_spread = round(tnx_v - fvx_v, 4)  # 10Y-5Y as yield curve proxy

        regime, regime_score, regime_detail = compute_regime(
            vix_v, spy_v, spy_sma50, spy_sma200, tnx_v, dxy_v, dxy_sma50
        )

        rows.append({
            "trade_date": d,
            "vix_close": round(vix_v, 4),
            "spy_close": round(spy_v, 4),
            "spy_sma50": round(spy_sma50, 4) if spy_sma50 else 0,
            "spy_sma200": round(spy_sma200, 4) if spy_sma200 else 0,
            "tnx_close": round(tnx_v, 4),
            "two_yr_yield": round(fvx_v, 4),
            "yield_spread": yield_spread,
            "dxy_close": round(dxy_v, 4),
            "dxy_sma50": round(dxy_sma50, 4) if dxy_sma50 else 0,
            "regime": regime,
            "regime_score": regime_score,
            "regime_detail": regime_detail,
        })

    print(f"[populate_alpha_macro] computed {len(rows)} rows")

    if args.dry_run:
        print("[populate_alpha_macro] DRY RUN — first 3 rows:")
        for r in rows[:3]:
            print(f"  {r}")
        return 0

    # Upsert to DB
    conn = pymysql.connect(**get_stocks_creds(), cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            n = upsert_rows(cur, rows)
        conn.commit()
    finally:
        conn.close()

    print(f"[populate_alpha_macro] upserted {n} rows into alpha_macro")
    print(f"[populate_alpha_macro] done UTC={datetime.now(timezone.utc).isoformat()[:19]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
