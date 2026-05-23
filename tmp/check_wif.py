"""Check all WIF picks and their price ranges."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
d = json.load(open(ROOT / "audit_trail/data/dashboard_payload.json", "r", encoding="utf-8"))

# Check active picks
wif_active = [p for p in d["picks"]["active"] if "WIF" in (p.get("symbol", "") or "").upper()]
print(f"=== ACTIVE WIF PICKS: {len(wif_active)} ===")
for p in sorted(wif_active, key=lambda x: float(x.get("entry_price", 0) or 0), reverse=True):
    print(f"  {p.get('symbol')} {p.get('direction')} entry={p.get('entry_price')} tp={p.get('take_profit')} sl={p.get('stop_loss')}")
    print(f"    sys={p.get('source_system')} strat={p.get('strategy')}")
    print(f"    conf={p.get('confidence')} pnl%={p.get('pnl_pct')} ts={p.get('timestamp')}")
    print()

# Check closed picks
wif_closed = [p for p in d["picks"].get("closed", []) if "WIF" in (p.get("symbol", "") or "").upper()]
print(f"=== CLOSED WIF PICKS: {len(wif_closed)} ===")
for p in wif_closed[:10]:
    print(f"  {p.get('symbol')} {p.get('direction')} entry={p.get('entry_price')} exit={p.get('exit_price')} pnl={p.get('pnl_pct')}%")
    print(f"    sys={p.get('source_system')} strat={p.get('strategy')} exit_reason={p.get('exit_reason')}")
    print()

# Check for anomalous prices
print("=== PRICE ANOMALY CHECK ===")
all_wif_prices = []
for p in wif_active:
    entry = float(p.get("entry_price", 0) or 0)
    if entry > 0:
        all_wif_prices.append((entry, p.get("symbol"), p.get("source_system"), p.get("strategy")))

all_wif_prices.sort(reverse=True)
if all_wif_prices:
    max_p = all_wif_prices[0][0]
    min_p = all_wif_prices[-1][0]
    print(f"  Max entry: ${max_p:.6f} ({all_wif_prices[0][1]} from {all_wif_prices[0][2]})")
    print(f"  Min entry: ${min_p:.6f} ({all_wif_prices[-1][1]} from {all_wif_prices[-1][2]})")
    if max_p > 0 and min_p > 0:
        ratio = max_p / min_p
        print(f"  Ratio: {ratio:.1f}x")
        if ratio > 10:
            print(f"  *** WARNING: {ratio:.0f}x price difference! Different tokens or wrong exchange data! ***")

# Also check what LuxAlgo recommended for WIF
print()
print("=== LUXALGO WIF PICKS SPECIFICALLY ===")
luxalgo_wif = [p for p in wif_active if "luxalgo" in (p.get("source_system", "") or "").lower()]
for p in luxalgo_wif:
    print(f"  {p.get('symbol')} {p.get('direction')} entry={p.get('entry_price')} tp={p.get('take_profit')} sl={p.get('stop_loss')}")
    print(f"    strat={p.get('strategy')} conf={p.get('confidence')} ts={p.get('timestamp')}")
    print()

# Check CHATWITHIT picks for WIF
print("=== MEGA MUTATION WIF PICKS ===")
mega_wif = [p for p in wif_active if "mega" in (p.get("strategy", "") or "").lower() or "mutation" in (p.get("strategy", "") or "").lower()]
for p in mega_wif:
    print(f"  {p.get('symbol')} {p.get('direction')} entry={p.get('entry_price')} tp={p.get('take_profit')} sl={p.get('stop_loss')}")
    print(f"    strat={p.get('strategy')} conf={p.get('confidence')} ts={p.get('timestamp')}")
    print()
