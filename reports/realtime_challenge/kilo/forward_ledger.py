#!/usr/bin/env python3
"""Forward ledger ticker — accrues honest, net-of-cost forward observations for
pre-registered EDGE rules, appending to a JSONL ledger. This is the audit's #1
missing piece: a forward clock so a rule can actually graduate or be killed.

Rules tracked (all pre-registered, see EDGE_PROGRAM charter):
  EDGE-5  SPY overnight (buy prior close -> sell open), net of 4bp RT
  EDGE-1  crypto funding-carry level, WEEKLY rebalance, net of 4.5bp/side
          (tracked as a *price+carry* factor per its decomposition, NOT as pure carry)

Idempotent: one row per (rule, as_of_date); re-running the same day rewrites that
row, never duplicates. Read-only public data (yfinance, ccxt). No keys.

Usage:
  python3 forward_ledger.py            # tick all rules, append today's rows
  python3 forward_ledger.py --show     # print ledger summary
  cat reports/realtime_challenge/kilo/forward_ledger.jsonl
"""
import csv, datetime, json, os, sys

LEDGER = os.path.join(os.path.dirname(__file__), "forward_ledger.jsonl")
COST_ETF_BP = 4.0
COST_PERP_BP = 4.5
SYMS = ["BTC","ETH","SOL","BNB","XRP","ADA","DOGE","AVAX","LINK","LTC"]


def _read():
    rows = []
    if os.path.exists(LEDGER):
        with open(LEDGER) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return rows


def _upsert(rows, new):
    key = (new["rule"], new["as_of"])
    out = [r for r in rows if (r["rule"], r["as_of"]) != key]
    out.append(new)
    out.sort(key=lambda r: (r["rule"], r["as_of"]))
    with open(LEDGER, "w") as fh:
        for r in out:
            fh.write(json.dumps(r) + "\n")
    return out


def tick_spy_overnight(today):
    """Record the most recent CLOSED overnight window (prior close -> open)."""
    import yfinance as yf
    df = yf.download("SPY", period="5d", interval="1d", progress=False, auto_adjust=False)
    if df is None or len(df) < 2:
        return None
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df.columns = [c[0] for c in df.columns]
    df = df.dropna(subset=["Open", "Close"])
    o = df["Open"].to_numpy(float); c = df["Close"].to_numpy(float)
    idx = df.index
    prev_close, today_open = c[-2], o[-1]
    gross = today_open/prev_close - 1
    net = gross - COST_ETF_BP/1e4
    return {"rule": "EDGE-5_SPY_OVERNIGHT", "as_of": str(idx[-1].date()),
            "ticker": "SPY", "side": "LONG_overnight",
            "gross_bp": round(gross*1e4, 3), "cost_bp": COST_ETF_BP,
            "net_bp": round(net*1e4, 3), "hit": bool(net > 0),
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat()}


def tick_funding_weekly(today):
    """Record last completed calendar-week's funding-carry+price net for the
    prior week's long-cheap/short-dear ranking (dollar-neutral, k=3, L7)."""
    import ccxt
    import numpy as np
    ex = ccxt.binanceusdm({"enableRateLimit": True})
    now = datetime.datetime.now(datetime.timezone.utc)
    since = int((now - datetime.timedelta(days=21)).timestamp()*1000)
    fund, px = {}, {}
    for s in SYMS:
        sym = f"{s}/USDT:USDT"
        try:
            fr = ex.fetchFundingRateHistory(sym, since=since, limit=1000)
            fund[s] = sorted((int(r["timestamp"]), float(r["fundingRate"])) for r in fr)
            oc = ex.fetch_ohlcv(sym, "1d", since=since, limit=21)
            px[s] = sorted((int(c[0]), float(c[4])) for c in oc)
        except Exception:
            pass
    if len(fund) < 6:
        return None
    all_ts = sorted({t for s in fund for t, _ in fund[s]})
    t_end = all_ts[-1]
    t0 = t_end - 7*24*3600*1000
    def avg(s):
        v = [r for t, r in fund[s] if t0 < t <= t_end]
        return float(np.mean(v)) if v else None
    avgd = {s: avg(s) for s in fund}
    avgd = {s: v for s, v in avgd.items() if v is not None}
    if len(avgd) < 6:
        return None
    ranked = sorted(avgd, key=lambda s: avgd[s])
    longs, shorts = ranked[:3], ranked[-3:]
    # realised over the week ending t_end (carry + price), unit-weight for the ticker
    carry = price = 0.0
    for s in longs+shorts:
        sign = 1.0 if s in longs else -1.0
        payout = [r for t, r in fund[s] if t0 < t <= t_end]
        fsum = float(np.sum(payout)) if payout else 0.0
        p0 = ([p for t, p in px[s] if t <= t0] or [None])[-1]
        p1 = ([p for t, p in px[s] if t <= t_end] or [None])[-1]
        pret = (p1/p0 - 1) if (p0 and p1) else 0.0
        carry += sign*(-fsum)/len(longs)
        price += sign*pret/len(longs)
    gross = carry + price
    cost = 2.0*(COST_PERP_BP/1e4)
    net = gross - cost
    as_of = datetime.datetime.fromtimestamp(t_end/1000, datetime.timezone.utc).date().isoformat()
    return {"rule": "EDGE-1_FUNDING_WEEKLY_FACTOR", "as_of": as_of,
            "longs": longs, "shorts": shorts,
            "carry_bp": round(carry*1e4, 3), "price_bp": round(price*1e4, 3),
            "gross_bp": round(gross*1e4, 3), "cost_bp": COST_PERP_BP*2,
            "net_bp": round(net*1e4, 3), "hit": bool(net > 0),
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat()}


def show():
    rows = _read()
    if not rows:
        print("ledger empty"); return
    from collections import defaultdict
    agg = defaultdict(list)
    for r in rows:
        agg[r["rule"]].append(r["net_bp"])
    for rule, nets in agg.items():
        n = len(nets); m = sum(nets)/n; w = sum(1 for x in nets if x > 0)/n
        print(f"{rule:32s} n={n:4d} mean_net={m:+8.3f}bp win={w:.0%}")
    print(f"\nledger rows: {len(rows)}  -> {LEDGER}")


def main():
    if "--show" in sys.argv:
        show(); return
    today = datetime.date.today().isoformat()
    rows = _read()
    added = []
    for fn in (tick_spy_overnight, tick_funding_weekly):
        try:
            r = fn(today)
            if r:
                rows = _upsert(rows, r)
                added.append(r)
        except Exception as e:
            print(f"WARN {fn.__name__}: {type(e).__name__}: {e}", file=sys.stderr)
    print(json.dumps(added, indent=2))
    print(f"\nledger now has {len(rows)} rows -> {LEDGER}")


if __name__ == "__main__":
    main()