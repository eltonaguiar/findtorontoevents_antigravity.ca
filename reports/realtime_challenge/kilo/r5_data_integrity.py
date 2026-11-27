#!/usr/bin/env python3
"""R5 DATA-INTEGRITY SWEEP (REALTIMECHALLENGE kilo, Phase 0).

Question (pre-registered): Are the series we will measure free of the anomalies
(zero/neg prices, dup/non-monotonic timestamps, gaps, stale last bar, OHLC
inconsistency) that silently corrupt every downstream number?

Reproducible: `python3 reports/realtime_challenge/kilo/r5_data_integrity.py`
Read-only public ccxt OHLCV. PASS only if all checks clean.
"""
import datetime, hashlib, json

PAIRS = ["BTC/USDT","ETH/USDT","SOL/USDT","BNB/USDT","XRP/USDT","ADA/USDT","DOGE/USDT","AVAX/USDT"]
TF="5m"; LIMIT=1000; CADENCE_MS=5*60*1000

def check(o):
    ts=[c[0] for c in o]
    bad_price=sum(1 for c in o if c[1]<=0 or c[2]<=0 or c[3]<=0 or c[4]<=0)
    dup=len(ts)-len(set(ts))
    nonmono=sum(1 for i in range(1,len(ts)) if ts[i]<=ts[i-1])
    gaps=sum(1 for i in range(1,len(ts)) if ts[i]-ts[i-1]!=CADENCE_MS)
    ohlc_bad=sum(1 for c in o if not(c[2]>=max(c[1],c[4]) and c[3]<=min(c[1],c[4]) and c[2]>=c[3]))
    return {"n":len(o),"bad_price":bad_price,"dup_ts":dup,"nonmono_ts":nonmono,
            "gaps":gaps,"ohlc_inconsistent":ohlc_bad}

def main():
    import ccxt, time
    ex=ccxt.binance({"enableRateLimit":True})
    out={"round":"R5","generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "tf":TF,"limit":LIMIT,"series":{}}
    now_ms=int(time.time()*1000)
    allpass=True
    for p in PAIRS:
        try:
            o=ex.fetch_ohlcv(p,TF,limit=LIMIT)
            c=check(o); c["stale_min"]=round((now_ms-o[-1][0])/60000,1)
            c["PASS"]= (c["bad_price"]==0 and c["dup_ts"]==0 and c["nonmono_ts"]==0
                        and c["gaps"]==0 and c["ohlc_inconsistent"]==0 and c["stale_min"]<60)
            out["series"][p]=c
            allpass = allpass and c["PASS"]
        except Exception as e:
            out["series"][p]={"status":f"err:{type(e).__name__}"}; allpass=False
    out["overall"]= "PASS" if allpass else "FAIL"
    with open(__file__,"rb") as fh: out["artifact_sha"]=hashlib.sha256(fh.read()).hexdigest()[:16]
    print(json.dumps(out["series"],indent=2)); print("OVERALL:",out["overall"])
    with open(__file__.replace(".py",".json"),"w") as fh: json.dump(out,fh,indent=2)
    # least-survivable
    worst=max(out["series"].items(), key=lambda kv: kv[1].get("gaps",0)+kv[1].get("ohlc_inconsistent",0) if isinstance(kv[1],dict) else 0)
    print("LEAST-SURVIVABLE:", worst[0], worst[1])

if __name__=="__main__":
    main()