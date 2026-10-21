#!/usr/bin/env python3
"""Paper tracker for crypto_r1: logs daily signals with timestamp."""
import json, os, sys
from datetime import datetime, timezone
import yfinance as yf
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "strategies", "crypto_r1", "paper_log.jsonl")

UNIVERSE = ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD",
            "ADA-USD","AVAX-USD","LINK-USD","DOGE-USD","DOT-USD"]

def main():
    now = datetime.now(timezone.utc).isoformat()
    for sym in UNIVERSE:
        df = yf.download(sym, period="30d", progress=False, auto_adjust=True)
        if df is None or df.empty: continue
        df.columns = [c[0] if isinstance(c,tuple) else c for c in df.columns]
        vol = df["Volume"]; close = df["Close"]; opn = df["Open"]
        volma = vol.rolling(20).mean()
        i = len(df)-1
        if vol.iloc[i] > 2*volma.iloc[i] and close.iloc[i] > opn.iloc[i]:
            rec = {"ts": now, "symbol": sym.replace("-USD","USDT"), "signal": "crypto_r1",
                   "entry": float(close.iloc[i]), "hold_days": 5}
            with open(LOG, "a") as f:
                f.write(json.dumps(rec) + "\n")
            print("SIGNAL", rec)
    print("done")

if __name__ == "__main__":
    main()
EOF
chmod +x /home/eaguiar2015/wt-opencode-moneyready/strategies/crypto_r1/paper_tracker.py
echo done