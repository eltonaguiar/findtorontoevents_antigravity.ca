"""
Pump Forensics: Scan Kraken for historical extreme gainers.
For each pair, fetch daily OHLCV and find episodes where price pumped 50%+ in <=7 days.
Then capture the "pre-pump fingerprint" (what the chart looked like 1-3 days before).
"""
import urllib.request, json, ssl, time, sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "PumpForensics/1.0"})
    resp = urllib.request.urlopen(req, context=ctx, timeout=15)
    return json.loads(resp.read().decode())

# Get all USD pairs
pairs_data = fetch("https://api.kraken.com/0/public/AssetPairs")
all_pairs = []
skip = ["USDC","USDT","DAI","PAX","BUSD","TUSD","PYUSD","FDUSD","USDE","ZGBP","ZEUR","ZCAD","ZJPY","ZAUD"]
for name, info in pairs_data.get("result", {}).items():
    if info.get("status") != "online": continue
    q = info.get("quote", "")
    if q not in ("ZUSD", "USD"): continue
    skip_it = False
    for s in skip:
        if name.startswith(s): skip_it = True; break
    if skip_it: continue
    all_pairs.append(name)

print(f"Scanning {len(all_pairs)} USD pairs for historical pumps...")
print("=" * 90)

pump_episodes = []
scanned = 0

for pair in all_pairs:
    scanned += 1
    if scanned % 20 == 0:
        print(f"  ...scanned {scanned}/{len(all_pairs)}")
    
    try:
        data = fetch(f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=1440")
        time.sleep(0.35)  # Rate limit
    except Exception as e:
        continue
    
    candles = []
    for k, v in data.get("result", {}).items():
        if k == "last": continue
        for c in v:
            candles.append({
                "t": int(c[0]), "o": float(c[1]), "h": float(c[2]),
                "l": float(c[3]), "c": float(c[4]), "vw": float(c[5]),
                "v": float(c[6]), "n": int(c[7])
            })
    
    if len(candles) < 30:
        continue
    
    # Find pump episodes: look for 50%+ gains within any 7-day window
    for i in range(7, len(candles)):
        window_low = min(c["l"] for c in candles[i-7:i])
        window_high = candles[i]["h"]
        if window_low <= 0: continue
        gain = ((window_high - window_low) / window_low) * 100
        
        if gain >= 50:
            # Find the exact pump start (the lowest point in the window)
            low_idx = i - 7
            for j in range(i-7, i):
                if candles[j]["l"] <= window_low * 1.01:
                    low_idx = j
                    break
            
            # Verify it's not a rug (price didn't crash >80% in next 7 days)
            post_pump_ok = True
            if i + 7 < len(candles):
                post_high = candles[i]["h"]
                post_low = min(c["l"] for c in candles[i:min(i+7, len(candles))])
                if post_high > 0:
                    drop = ((post_high - post_low) / post_high) * 100
                    if drop > 80:
                        post_pump_ok = False  # Likely a rug pull
            
            # Check volume legitimacy (need some volume)
            pump_vol = sum(c["v"] for c in candles[low_idx:i+1])
            if pump_vol < 100:  # Skip extremely low volume
                continue
            
            # Capture PRE-PUMP fingerprint (3 days before the pump started)
            pre_start = max(0, low_idx - 14)  # 14 days before pump for context
            pre_candles = candles[pre_start:low_idx+1]
            
            if len(pre_candles) < 5:
                continue
            
            # Pre-pump metrics
            pre_closes = [c["c"] for c in pre_candles]
            pre_volumes = [c["v"] for c in pre_candles]
            pre_ranges = [(c["h"] - c["l"]) / max(c["l"], 0.0001) * 100 for c in pre_candles]
            
            # Volume trend (was volume increasing before pump?)
            vol_early = sum(pre_volumes[:len(pre_volumes)//2]) / max(len(pre_volumes)//2, 1)
            vol_late = sum(pre_volumes[len(pre_volumes)//2:]) / max(len(pre_volumes) - len(pre_volumes)//2, 1)
            vol_trend = vol_late / max(vol_early, 0.01)
            
            # Price consolidation (was range tightening?)
            range_early = sum(pre_ranges[:len(pre_ranges)//2]) / max(len(pre_ranges)//2, 1)
            range_late = sum(pre_ranges[len(pre_ranges)//2:]) / max(len(pre_ranges) - len(pre_ranges)//2, 1)
            range_compression = range_late / max(range_early, 0.01)
            
            # Price trend before pump
            if len(pre_closes) >= 2:
                pre_trend = ((pre_closes[-1] - pre_closes[0]) / max(pre_closes[0], 0.0001)) * 100
            else:
                pre_trend = 0
            
            # Average pre-pump volume
            avg_pre_vol = sum(pre_volumes) / max(len(pre_volumes), 1)
            
            # Day-of-pump volume spike
            pump_day_vol = candles[low_idx]["v"] if low_idx < len(candles) else 0
            vol_spike_ratio = pump_day_vol / max(avg_pre_vol, 0.01)
            
            pump_date = time.strftime("%Y-%m-%d", time.gmtime(candles[i]["t"]))
            pump_start_date = time.strftime("%Y-%m-%d", time.gmtime(candles[low_idx]["t"]))
            
            pump_episodes.append({
                "pair": pair,
                "gain_pct": round(gain, 1),
                "pump_date": pump_date,
                "pump_start": pump_start_date,
                "duration_days": i - low_idx,
                "legit": post_pump_ok,
                "pre_vol_trend": round(vol_trend, 2),
                "range_compression": round(range_compression, 2),
                "pre_trend_pct": round(pre_trend, 2),
                "vol_spike_ratio": round(vol_spike_ratio, 2),
                "avg_pre_vol": round(avg_pre_vol, 2),
                "pump_low": window_low,
                "pump_high": window_high,
            })

# Deduplicate (same pair within 14 days = same episode)
unique_pumps = []
seen = set()
for p in sorted(pump_episodes, key=lambda x: x["gain_pct"], reverse=True):
    key = p["pair"] + "_" + p["pump_start"][:7]  # Same pair+month
    if key in seen: continue
    seen.add(key)
    unique_pumps.append(p)

# Separate legit vs rug
legit = [p for p in unique_pumps if p["legit"]]
rugs = [p for p in unique_pumps if not p["legit"]]

print(f"\nFOUND {len(unique_pumps)} PUMP EPISODES (>50% in 7 days)")
print(f"  Legit: {len(legit)}  |  Rug/Dump: {len(rugs)}")
print()

print("TOP 40 LEGIT PUMPS (verified not rug-pulled):")
print("-" * 90)
for i, p in enumerate(legit[:40]):
    print(f"  {i+1:>3}. {p['pair']:<16} +{p['gain_pct']:>7.1f}%  {p['pump_start']} ({p['duration_days']}d)  "
          f"PreVol:{p['pre_vol_trend']:>5.1f}x  RngComp:{p['range_compression']:>5.2f}  "
          f"PreTrend:{p['pre_trend_pct']:>+6.1f}%  VolSpike:{p['vol_spike_ratio']:>5.1f}x")

# Analyze common pre-pump patterns across legit pumps
print("\n" + "=" * 90)
print("PRE-PUMP FINGERPRINT ANALYSIS (what legit pumps looked like BEFORE they moved)")
print("=" * 90)

if legit:
    vol_trends = [p["pre_vol_trend"] for p in legit]
    range_comps = [p["range_compression"] for p in legit]
    pre_trends = [p["pre_trend_pct"] for p in legit]
    vol_spikes = [p["vol_spike_ratio"] for p in legit]
    
    print(f"\n  Volume Trend Before Pump:")
    print(f"    Average: {sum(vol_trends)/len(vol_trends):.2f}x")
    print(f"    Median:  {sorted(vol_trends)[len(vol_trends)//2]:.2f}x")
    print(f"    >1.5x volume increase before pump: {sum(1 for v in vol_trends if v > 1.5)}/{len(vol_trends)} ({sum(1 for v in vol_trends if v > 1.5)/len(vol_trends)*100:.0f}%)")
    
    print(f"\n  Range Compression (volatility tightening):")
    print(f"    Average: {sum(range_comps)/len(range_comps):.2f}")
    print(f"    Median:  {sorted(range_comps)[len(range_comps)//2]:.2f}")
    print(f"    <0.7 (compressed before pump): {sum(1 for r in range_comps if r < 0.7)}/{len(range_comps)} ({sum(1 for r in range_comps if r < 0.7)/len(range_comps)*100:.0f}%)")
    
    print(f"\n  Pre-Pump Price Trend:")
    print(f"    Average: {sum(pre_trends)/len(pre_trends):+.1f}%")
    print(f"    Positive (already rising): {sum(1 for t in pre_trends if t > 0)}/{len(pre_trends)} ({sum(1 for t in pre_trends if t > 0)/len(pre_trends)*100:.0f}%)")
    print(f"    Negative (dip before pump): {sum(1 for t in pre_trends if t < 0)}/{len(pre_trends)} ({sum(1 for t in pre_trends if t < 0)/len(pre_trends)*100:.0f}%)")
    
    print(f"\n  Volume Spike on Pump Day:")
    print(f"    Average: {sum(vol_spikes)/len(vol_spikes):.1f}x normal")
    print(f"    >2x spike: {sum(1 for v in vol_spikes if v > 2)}/{len(vol_spikes)} ({sum(1 for v in vol_spikes if v > 2)/len(vol_spikes)*100:.0f}%)")

# Save for the PHP engine
with open("findcryptopairs/pump_forensics.json", "w") as f:
    json.dump({"legit_pumps": legit[:60], "fingerprint": {
        "avg_vol_trend": round(sum(vol_trends)/len(vol_trends), 2) if legit else 0,
        "avg_range_comp": round(sum(range_comps)/len(range_comps), 2) if legit else 0,
        "avg_pre_trend": round(sum(pre_trends)/len(pre_trends), 2) if legit else 0,
        "avg_vol_spike": round(sum(vol_spikes)/len(vol_spikes), 2) if legit else 0,
        "total_legit": len(legit),
        "total_rugs": len(rugs)
    }}, f, indent=2)
    print(f"\nSaved to findcryptopairs/pump_forensics.json")
