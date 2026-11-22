#!/usr/bin/env python3
"""Forward observation harness for the two pre-registered trend hypotheses.

  H-2026-11-22-EQUITY-TREND10M      SPY vs 10-month SMA
  H-2026-11-22-COMMODITY-TREND10M   roll-managed commodity ETF basket vs 10-month SMA

Pre-registered 2026-11-22 in reports/hypothesis_registry.json (rule M-107).
Promotion requires 100 forward MONTHLY observations. Nothing is sanctioned
before that. This script only OBSERVES and APPENDS; it never trades.

What it does each run
  1. loads the cached/series prices (yfinance, auto_adjust=True = dividends in)
  2. computes the signal from data through month t-2 (the conservative convention
     used in every backtest in this project, so forward and backtest are identical)
  3. appends one JSONL row per hypothesis to reports/forward_observations.jsonl
     (idempotent per month: re-running the same month overwrites that month's row)
  4. prints realised forward stats so far + distance to the 100-observation gate

Usage
    python3 tools/forward_trend_harness.py            # observe + append
    python3 tools/forward_trend_harness.py --refresh  # re-download prices first
    python3 tools/forward_trend_harness.py --status   # print stats, append nothing
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "reports" / "forward_observations.jsonl"
CACHE = ROOT / "reports" / "forward_price_cache.json"

HYPOTHESES = {
    "H-2026-11-22-EQUITY-TREND10M": ["SPY"],
    "H-2026-11-22-COMMODITY-TREND10M": ["DBC", "GSG", "GLD", "SLV", "USO", "UNG",
                                        "CORN", "WEAT", "SOYB", "DBA", "CPER"],
}
SMA_LEN = 10
CASH_TICKER = "SHY"          # 1-3y Treasury total return as the cash leg
MIN_TICKS = 500


def _fetch(tickers: list[str]) -> dict[str, pd.Series]:
    import yfinance as yf
    out: dict[str, pd.Series] = {}
    for t in tickers:
        try:
            d = yf.download(t, period="max", interval="1d", auto_adjust=True,
                            progress=False, threads=False)
            if isinstance(d.columns, pd.MultiIndex):
                d.columns = d.columns.get_level_values(0)
            s = d["Close"].dropna()
            if len(s) > 250:
                s.index = pd.to_datetime(s.index).tz_localize(None)
                out[t] = s.resample("ME").last()
        except Exception:
            continue
    return out


def _load(refresh: bool) -> dict[str, pd.Series]:
    if not refresh and CACHE.exists():
        try:
            raw = json.loads(CACHE.read_text())
            return {k: pd.Series(v).set_axis(pd.to_datetime(list(v.keys()))).sort_index()
                    for k, v in raw.items()}
        except Exception:
            pass
    tickers = sorted({t for v in HYPOTHESES.values() for t in v} | {CASH_TICKER})
    ser = _fetch(tickers)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({k: {d.strftime("%Y-%m"): float(x) for d, x in v.items()}
                                 for k, v in ser.items()}))
    return ser


def observe(ser: dict[str, pd.Series]) -> list[dict]:
    cash = ser[CASH_TICKER].pct_change().fillna(0.0)
    rows = []
    for hid, members in HYPOTHESES.items():
        have = [m for m in members if m in ser]
        # a 1-member universe (EQUITY = SPY only) must not be rejected: the old
        # `max(2, len//2)` floor demanded 2 members from a 1-member list.
        need = len(members) if len(members) <= 2 else max(2, len(members) // 2)
        if len(have) < need:
            rows.append(dict(hypothesis_id=hid, error="insufficient_series",
                             have=have, need=need))
            continue
        px = pd.DataFrame({m: ser[m] for m in have}).dropna()
        R = px.pct_change()
        ew = R.mean(axis=1)
        lvl = (1 + ew.fillna(0)).cumprod()
        t = len(lvl) - 1
        i = t - 1                              # data through t−2, as pre-registered
        if i < SMA_LEN + 1:
            rows.append(dict(hypothesis_id=hid, error="warmup"))
            continue
        sma = float(lvl.iloc[i - SMA_LEN:i].mean())
        invested = int(lvl.iloc[i] > sma)
        realised = float(ew.iloc[t]) if invested else float(cash.reindex(ew.index).fillna(0).iloc[t])
        obs_m = ew.index[-1]
        now_m = datetime.now(timezone.utc).strftime("%Y-%m")
        # A month is only COMPLETE once it is in the past. Counting a
        # month-to-date return toward the 100-observation gate is the same
        # sampling error as month-end MaxDD (see PART11 retraction b).
        complete = obs_m.strftime("%Y-%m") < now_m
        rows.append(dict(
            hypothesis_id=hid,
            observation_month=obs_m.strftime("%Y-%m"),
            data_through_month=lvl.index[i].strftime("%Y-%m"),
            signal=invested,                         # position held during observation_month
            complete_month=complete,
            level=round(float(lvl.iloc[i]), 6),
            sma10=round(sma, 6),
            realised_return_pct=round(realised * 100, 4),
            members=len(have),
            observed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ))
    return rows


MINE = set(HYPOTHESES)


def append(rows: list[dict]) -> int:
    """Append this harness's own rows, PRESERVING every foreign row verbatim.

    The ledger is shared with other pipelines (e.g. 430 H-119 rows written
    elsewhere, which carry no observation_month). An earlier version of this
    function keyed ALL rows on (hypothesis_id, observation_month) and collapsed
    those 430 rows into 1 — destroying committed data. Foreign lines are now
    kept as raw strings and never re-serialised or de-duplicated.
    """
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    foreign: list[str] = []
    mine: dict[tuple[str, str], dict] = {}
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except Exception:
                foreign.append(line)          # unparseable -> keep byte-for-byte
                continue
            if r.get("hypothesis_id") in MINE and r.get("observation_month"):
                mine[(r["hypothesis_id"], r["observation_month"])] = r
            else:
                foreign.append(line)          # not ours -> keep byte-for-byte
    for r in rows:
        if r.get("hypothesis_id") in MINE and r.get("observation_month"):
            mine[(r["hypothesis_id"], r["observation_month"])] = r
        else:
            foreign.append(json.dumps(r))     # error row: append, never keyed
    ordered = [mine[k] for k in sorted(mine)]
    out = foreign + [json.dumps(r) for r in ordered]
    LEDGER.write_text("\n".join(out) + "\n")
    return len(out)


def status() -> None:
    if not LEDGER.exists():
        print("no ledger yet"); return
    rows = [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]
    rows = [r for r in rows if r.get("hypothesis_id") in MINE and r.get("observation_month")]
    if not rows:
        print("\nno forward observations yet for the registered hypotheses"); return
    df = pd.DataFrame(rows)
    for hid, g in df.groupby("hypothesis_id"):
        g = g.sort_values("observation_month")
        # only completed months count toward the pre-registered gate
        done = g[g.get("complete_month", pd.Series(False, index=g.index)).fillna(False).astype(bool)]
        mtd = g[~g.index.isin(done.index)]
        n = len(done)
        r = pd.to_numeric(done["realised_return_pct"], errors="coerce").fillna(0.0) / 100
        sharpe = (r.mean() / r.std(ddof=1) * math.sqrt(12)) if n > 2 and r.std(ddof=1) else float("nan")
        cum = float((1 + r).prod() - 1)
        print(f"\n{hid}")
        print(f"  observations      : {n} / 100 required   ({n/100*100:.0f}% of gate)")
        print(f"  cumulative return : {cum*100:+.2f}%")
        print(f"  annualised Sharpe : {sharpe:.3f}" if not math.isnan(sharpe) else "  Sharpe: n<3")
        sig = pd.to_numeric(g["signal"], errors="coerce").fillna(0)
        print(f"  months invested   : {int(pd.to_numeric(done['signal'], errors='coerce').fillna(0).sum())}/{n}"
              f" (complete months only)")
        if len(mtd):
            mm = mtd.iloc[-1]
            print(f"  month-to-date     : {mm['observation_month']} "
                  f"signal={'INVESTED' if int(float(mm['signal'])) else 'CASH'} "
                  f"return={float(mm['realised_return_pct']):+.2f}% "
                  f"-- NOT COUNTED toward the gate (incomplete month)")
        last = g.iloc[-1]
        print(f"  last observation  : {last['observation_month']} "
              f"({'complete' if bool(last.get('complete_month')) else 'month-to-date'})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.status:
        status(); return 0
    ser = _load(a.refresh)
    if not ser:
        print("no price data available"); return 2
    rows = observe(ser)
    n = append(rows)
    for r in rows:
        if "error" in r:
            print(f"{r['hypothesis_id']}: {r['error']}")
        else:
            print(f"{r['hypothesis_id']}: {r['observation_month']} signal={'INVESTED' if r['signal'] else 'CASH'} "
                  f"level={r['level']} sma10={r['sma10']} realised={r['realised_return_pct']:+.3f}%")
    print(f"\nledger rows: {n} -> {LEDGER}")
    status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
