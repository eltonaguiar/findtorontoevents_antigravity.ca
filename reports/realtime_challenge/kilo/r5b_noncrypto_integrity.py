#!/usr/bin/env python3
"""R5b NON-CRYPTO DATA-INTEGRITY SWEEP (REALTIMECHALLENGE kilo, Phase 0).

Question (pre-registered): Do the non-crypto series (equity/bond/commodity/FX/
futures daily) carry the anomalies (zero/neg, dup/non-monotonic ts, OHLC
inconsistency, stale) that the project's ghost-row / CL=F bugs warn about?

Reproducible: `python3 reports/realtime_challenge/kilo/r5b_noncrypto_integrity.py`
Read-only yfinance daily. Daily cadence => weekends/holidays expected, so gaps
are NOT flagged; dup/nonmono/bad_price/ohlc/stale are.
"""
import datetime, hashlib, json

# ticker -> asset class
TICKERS = {"SPY":"equity_etf","AAPL":"equity","GLD":"commodity_etf","TLT":"bond_etf",
           "EURUSD=X":"forex","CL=F":"futures_crude","GC=F":"futures_gold","BTC-USD":"crypto_daily"}

def check(df):
    df=df.dropna()
    ts=list(df.index)
    bad_price=int(((df[["Open","High","Low","Close"]]<=0).any(axis=1)).sum())
    dup=len(ts)-len(set(ts))
    nonmono=sum(1 for i in range(1,len(ts)) if ts[i]<=ts[i-1])
    ohlc_bad=int((~((df["High"]>=df[["Open","Close"]].max(axis=1)) &
                    (df["Low"]<=df[["Open","Close"]].min(axis=1)) &
                    (df["High"]>=df["Low"]))).sum())
    return {"n":len(df),"bad_price":bad_price,"dup_ts":dup,"nonmono_ts":nonmono,"ohlc_inconsistent":ohlc_bad}

def main():
    import yfinance as yf, time
    out={"round":"R5b","generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "tf":"1d","series":{}}
    now=time.time(); allpass=True
    for t,cls in TICKERS.items():
        try:
            df=yf.download(t,period="2y",interval="1d",progress=False,auto_adjust=False)
            if df.empty: out["series"][t]={"class":cls,"status":"empty"}; allpass=False; continue
            if isinstance(df.columns, __import__("pandas").MultiIndex):
                df.columns=[c[0] for c in df.columns]
            df=df[["Open","High","Low","Close"]]
            c=check(df)
            last_ts=df.index[-1]
            stale_days=(now-last_ts.timestamp())/86400 if hasattr(last_ts,"timestamp") else None
            c["stale_days"]=round(stale_days,1) if stale_days is not None else None
            c["class"]=cls
            c["PASS"]=(c["bad_price"]==0 and c["dup_ts"]==0 and c["nonmono_ts"]==0
                       and c["ohlc_inconsistent"]==0 and (c["stale_days"] is not None and c["stale_days"]<10))
            out["series"][t]=c; allpass=allpass and c["PASS"]
        except Exception as e:
            out["series"][t]={"class":cls,"status":f"err:{type(e).__name__}"}; allpass=False
    out["overall"]="PASS" if allpass else "FAIL"
    with open(__file__,"rb") as fh: out["artifact_sha"]=hashlib.sha256(fh.read()).hexdigest()[:16]
    print(json.dumps(out["series"],indent=2)); print("OVERALL:",out["overall"])
    with open(__file__.replace(".py",".json"),"w") as fh: json.dump(out,fh,indent=2,default=str)

if __name__=="__main__":
    main()