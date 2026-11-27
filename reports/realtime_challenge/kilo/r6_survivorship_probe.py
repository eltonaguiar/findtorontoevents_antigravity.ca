#!/usr/bin/env python3
"""R6 SURVIVORSHIP / GATE-1 FEASIBILITY PROBE (REALTIMECHALLENGE kilo, Phase 0).

Question (pre-registered): Gate 1 (survivorship-free, point-in-time universe) is
the binding constraint. Is it even ACHIEVABLE on free data? Probe whether yfinance
returns history for known DELISTED/ACQUIRED tickers. If yes -> survivorship-free
is feasible free; if no -> we need a delisted source (CRSP paid / stooq free).

Reproducible: `python3 reports/realtime_challenge/kilo/r6_survivorship_probe.py`
Read-only. Known corporate actions are public facts; tickers chosen because their
delisting is documented.
"""
import datetime, hashlib, json

# ticker -> (event, delisted_year)  -- all public, well-documented
DELISTED = {
    "ATVI": ("acquired by MSFT", 2023),
    "TWTR": ("acquired (private)", 2022),
    "CELG": ("acquired by BMY", 2019),
    "ALXN": ("acquired by AZN", 2021),
    "XLNX": ("acquired by AMD", 2022),
    "SIVB": ("bank failure", 2023),
}
CONTROL = {"SPY": "current", "AAPL": "current"}

def probe(yf, t):
    try:
        df = yf.download(t, period="max", interval="1d", progress=False, auto_adjust=False)
        if df is None or df.empty:
            return {"status": "EMPTY (no history -> survivorship gap)"}
        last = str(df.index[-1])[:10]; first = str(df.index[0])[:10]
        return {"status": "HAS_HISTORY", "first": first, "last": last, "n": int(len(df))}
    except Exception as e:
        return {"status": f"err:{type(e).__name__}"}

def main():
    import yfinance as yf
    out = {"round": "R6", "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "delisted": {}, "control": {}}
    for t,(ev,yr) in DELISTED.items():
        r = probe(yf,t); r["event"]=ev; r["delisted_year"]=yr; out["delisted"][t]=r
    for t,note in CONTROL.items():
        out["control"][t]=probe(yf,t)
    have = sum(1 for r in out["delisted"].values() if r["status"]=="HAS_HISTORY")
    out["delisted_available_free"] = f"{have}/{len(DELISTED)}"
    out["gate1_feasible_free"] = have >= 3
    with open(__file__,"rb") as fh: out["artifact_sha"]=hashlib.sha256(fh.read()).hexdigest()[:16]
    print(json.dumps(out,indent=2))
    with open(__file__.replace(".py",".json"),"w") as fh: json.dump(out,fh,indent=2)
    print("\nLEAST-SURVIVABLE NUMBER:", out["delisted_available_free"],
          "delisted tickers have free history -> Gate1",
          "FEASIBLE-FREE" if out["gate1_feasible_free"] else "NOT-FEASIBLE-FREE (need paid/alt source)")

if __name__=="__main__":
    main()