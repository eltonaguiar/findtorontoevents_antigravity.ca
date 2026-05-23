#!/usr/bin/env python3
"""Extract recent picks from backtest for tracking."""

import json
from pathlib import Path
from datetime import datetime, timezone

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "genome" / "data"

# Load backtest results
with open(DATA_DIR / 'kimi_mutations_backtest.json', 'r') as f:
    data = json.load(f)

print('='*70)
print('RECENT SUPPLEMENTAL MUTATION SIGNALS (Last 60 Days)')
print('='*70)
print(f'Backtest run: {data["timestamp"]}')
print(f'Period: {data["backtest_config"]["days"]} days, {data["backtest_config"]["interval"]} interval')
print()

# Extract recent signals from each mutation
all_signals = []
for mutation_name, result in data['mutation_results'].items():
    for sig in result.get('signals', []):
        sig['mutation_name'] = mutation_name
        all_signals.append(sig)

print(f'Total signals in backtest: {len(all_signals)}')
print()

# Get signals from last 7 days
recent = [s for s in all_signals if s.get('days_ago', 999) <= 7]

if recent:
    print(f'Signals in last 7 days: {len(recent)}')
    print()
    # Sort by confidence
    recent.sort(key=lambda x: x.get('confidence', 0), reverse=True)
    signals_to_show = recent
else:
    print('No signals in last 7 days. Showing top 10 highest confidence:')
    print()
    all_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
    signals_to_show = all_signals[:10]

# Display
for i, sig in enumerate(signals_to_show[:10], 1):
    print(f'{i}. {sig["symbol"]} {sig["signal_type"]}')
    print(f'   Strategy: {sig["mutation_name"]}')
    print(f'   Entry: ${sig["entry_price"]:,.2f}')
    print(f'   TP: ${sig["take_profit"]:,.2f} | SL: ${sig["stop_loss"]:,.2f}')
    print(f'   Confidence: {sig["confidence"]:.2f} | R:R: {sig["risk_reward"]:.2f}')
    print(f'   Days ago: {sig.get("days_ago", "?")}')
    print(f'   Reason: {sig.get("reason", "N/A")[:80]}...')
    print()

# Save top picks for tracking
top_picks = []
for sig in signals_to_show[:5]:
    top_picks.append({
        "symbol": sig["symbol"],
        "direction": sig["signal_type"],
        "strategy": sig["mutation_name"],
        "entry_price": sig["entry_price"],
        "take_profit": sig["take_profit"],
        "stop_loss": sig["stop_loss"],
        "confidence": sig["confidence"],
        "risk_reward": sig["risk_reward"],
        "timestamp": sig.get("timestamp", ""),
        "days_ago": sig.get("days_ago", 0),
        "reason": sig.get("reason", ""),
    })

output = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "source": "kimi_supplemental_backtest",
    "note": "These are historical signals from backtest for tracking purposes",
    "top_picks": top_picks,
}

output_file = DATA_DIR / 'kimi_top_picks_for_tracking.json'
with open(output_file, 'w') as f:
    json.dump(output, f, indent=2, default=str)

print(f'Saved top {len(top_picks)} picks to: {output_file}')
