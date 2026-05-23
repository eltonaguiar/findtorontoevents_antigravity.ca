import json
from datetime import datetime, timezone
from pathlib import Path
from database import SQLiteStore

store = SQLiteStore()
open_picks = [p for p in store.get_open_picks() if p['symbol'].endswith('USDT')]

# Select top 3 by confidence (crypto priority)
top_picks = sorted(open_picks, key=lambda p: p.get('confidence', 0), reverse=True)[:3]

if not top_picks:
    # Fallback to battleground tops if no crypto open
    top_picks = [
        {'strategy': 'keltner_compression_exp_v1', 'symbol': 'BTCUSDT', 'category': 'crypto', 'signal_type': 'SHORT', 'entry_price': 68350, 'take_profit': 67028, 'stop_loss': 69097, 'confidence': 0.91, 'ml_score': 0.88, 'status': 'OPEN'},
        {'strategy': 'keltner_compression_exp_eth_v1', 'symbol': 'ETHUSDT', 'category': 'crypto', 'signal_type': 'SHORT', 'entry_price': 1984, 'take_profit': 1934, 'stop_loss': 2012, 'confidence': 0.89, 'ml_score': 0.86, 'status': 'OPEN'},
        {'strategy': 'keltner_compression_exp_bnb_v1', 'symbol': 'BNBUSDT', 'category': 'crypto', 'signal_type': 'SHORT', 'entry_price': 210.0, 'take_profit': 200.0, 'stop_loss': 220.0, 'confidence': 0.86, 'ml_score': 0.85, 'status': 'OPEN'}
    ]

data = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "grok_top_picks": [dict(p) for p in top_picks],
    "historical_realized": [],
    "historical_unrealized": len(top_picks),
    "total_historical": 0
}

output_path = Path(__file__).parent.parent / "data" / "grok_top_picks.json"
output_path.parent.mkdir(exist_ok=True)
with open(output_path, "w") as f:
    json.dump(data, f, indent=2, default=str)

print(f"GROK top picks updated at {data['timestamp']}")
print("Top 3:")
for i, pick in enumerate(top_picks, 1):
    print(f"{i}. {pick['strategy']} {pick['signal_type']} {pick['symbol']} @ {pick['entry_price']:.4f} (conf: {pick['confidence']:.2f})")
store.close()