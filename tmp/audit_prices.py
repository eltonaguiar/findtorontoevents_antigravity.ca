"""ALPHA ENGINE - Price Verification Audit
Cross-references claimed entry prices against real market data for Feb 17, 2026.
"""
import yfinance as yf

symbols_to_check = {
    "AUDJPY=X": {"claimed_entry": 108.554, "signal": "BUY"},
    "GBPUSD=X": {"claimed_entry": 1.35612, "signal": "SELL"},
    "ATOM-USD": {"claimed_entry": 2.239, "signal": "BUY"},
    "AMC": {"claimed_entry": 1.25, "signal": "BUY"},
    "ETH-USD": {"claimed_entry": 1999.54, "signal": "BUY"},
}

print("=" * 60)
print("  ALPHA ENGINE - PRICE VERIFICATION AUDIT")
print("  Date checked: Feb 17, 2026")
print("=" * 60)
print()

verdicts = []

for sym, info in symbols_to_check.items():
    try:
        ticker = yf.Ticker(sym)
        hist = ticker.history(start="2026-02-16", end="2026-02-18")
        if len(hist) > 0:
            row = hist.iloc[-1]
            actual_open = row["Open"]
            actual_close = row["Close"]
            actual_high = row["High"]
            actual_low = row["Low"]
            claimed = info["claimed_entry"]
            in_range = actual_low <= claimed <= actual_high
            verdict = "PASS" if in_range else "FAIL - OUTSIDE DAY RANGE"
            verdicts.append((sym, verdict))
            pct_diff = abs(claimed - actual_close) / actual_close * 100

            print(f"{sym}:")
            print(f"  Signal:        {info['signal']}")
            print(f"  Claimed entry: {claimed}")
            print(f"  Actual OHLC:   O={actual_open:.6f}  H={actual_high:.6f}  L={actual_low:.6f}  C={actual_close:.6f}")
            if in_range:
                print(f"  Verdict:       PASS - entry price falls within the day's High/Low range")
            else:
                print(f"  Verdict:       FAIL - entry {claimed} is outside [{actual_low:.6f}, {actual_high:.6f}]")
            print(f"  Diff from close: {pct_diff:.3f}%")
            print()
        else:
            verdicts.append((sym, "NO DATA"))
            print(f"{sym}: No market data available for Feb 17, 2026")
            print()
    except Exception as e:
        verdicts.append((sym, f"ERROR: {e}"))
        print(f"{sym}: ERROR - {e}")
        print()

print("=" * 60)
print("  SUMMARY")
print("=" * 60)
for sym, v in verdicts:
    print(f"  {sym:16s} -> {v}")

passes = sum(1 for _, v in verdicts if v == "PASS")
total = len(verdicts)
print(f"\n  Result: {passes}/{total} prices verified against real market data")
if passes < total:
    print("  WARNING: Some prices could not be verified or fall outside range")
