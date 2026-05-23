"""Add sample analyst predictions for demo purposes."""
import db
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

conn = db.get_db()

# Add sample predictions from real analysts
sample_preds = [
    {
        'predictor_id': 'analyst:CryptoMichNL',
        'platform': 'twitter',
        'display_name': 'Michael van de Poppe',
        'symbol': 'BTCUSDT',
        'direction': 'LONG',
        'entry_price': 85000,
        'take_profit': 95000,
        'stop_loss': 82000,
        'source_url': 'https://twitter.com/CryptoMichNL/status/sample1',
        'is_known_analyst': 1,
        'analyst_category': 'ta_daily'
    },
    {
        'predictor_id': 'analyst:CryptoDonAlt',
        'platform': 'twitter', 
        'display_name': 'DonAlt',
        'symbol': 'ETHUSDT',
        'direction': 'LONG',
        'entry_price': 2400,
        'take_profit': 2800,
        'stop_loss': 2200,
        'source_url': 'https://twitter.com/CryptoDonAlt/status/sample2',
        'is_known_analyst': 1,
        'analyst_category': 'ta_daily'
    },
    {
        'predictor_id': 'analyst:davthewave',
        'platform': 'twitter',
        'display_name': 'Dave the Wave',
        'symbol': 'SOLUSDT',
        'direction': 'SHORT',
        'entry_price': 145,
        'take_profit': 120,
        'stop_loss': 155,
        'source_url': 'https://twitter.com/davthewave/status/sample3',
        'is_known_analyst': 1,
        'analyst_category': 'ta_daily'
    },
    {
        'predictor_id': 'analyst:CredibleCrypto',
        'platform': 'twitter',
        'display_name': 'Credible Crypto',
        'symbol': 'LINKUSDT',
        'direction': 'LONG',
        'entry_price': 18.5,
        'take_profit': 25.0,
        'stop_loss': 16.0,
        'source_url': 'https://twitter.com/CredibleCrypto/status/sample4',
        'is_known_analyst': 1,
        'analyst_category': 'ta_daily'
    },
    {
        'predictor_id': 'analyst:scottmelker',
        'platform': 'twitter',
        'display_name': 'Scott Melker',
        'symbol': 'DOGEUSDT',
        'direction': 'LONG',
        'entry_price': 0.25,
        'take_profit': 0.35,
        'stop_loss': 0.22,
        'source_url': 'https://twitter.com/scottmelker/status/sample5',
        'is_known_analyst': 1,
        'analyst_category': 'ta_daily'
    }
]

for pred in sample_preds:
    pred['scraped_at'] = datetime.now(timezone.utc).isoformat()
    pred['sentiment_score'] = 0.75
    pred['source_text'] = f"{pred['display_name']} predicts {pred['direction']} on {pred['symbol']} with entry at {pred['entry_price']}, TP {pred['take_profit']}, SL {pred['stop_loss']}"
    try:
        # Check if exists
        existing = conn.execute('SELECT id FROM predictions WHERE source_url = ?', (pred['source_url'],)).fetchone()
        if not existing:
            conn.execute('''
                INSERT INTO predictions 
                (predictor_id, platform, symbol, direction, entry_price, take_profit, stop_loss,
                 sentiment_score, source_url, source_text, scraped_at, status, is_known_analyst, analyst_category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
            ''', (pred['predictor_id'], pred['platform'], pred['symbol'], pred['direction'],
                  pred['entry_price'], pred['take_profit'], pred['stop_loss'],
                  pred['sentiment_score'], pred['source_url'], pred['source_text'],
                  pred['scraped_at'], pred['is_known_analyst'], pred['analyst_category']))
            print(f"Added {pred['display_name']} - {pred['symbol']}")
    except Exception as e:
        print(f"Error: {e}")

conn.commit()

# Update predictor stats
for pred in sample_preds:
    conn.execute('''
        INSERT INTO predictors (predictor_id, platform, display_name, total_predictions, wins, losses, win_rate, avg_pnl_pct, tier, is_known_analyst, analyst_category, first_seen, last_active)
        VALUES (?, ?, ?, 5, 3, 2, 0.6, 12.5, 'PROVEN', 1, ?, ?, ?)
        ON CONFLICT(predictor_id) DO UPDATE SET
            total_predictions = 5, wins = 3, losses = 2, win_rate = 0.6, avg_pnl_pct = 12.5, tier = 'PROVEN',
            is_known_analyst = 1, analyst_category = ?, last_active = ?
    ''', (pred['predictor_id'], pred['platform'], pred['display_name'], pred['analyst_category'],
          pred['scraped_at'], pred['scraped_at'], pred['analyst_category'], pred['scraped_at']))

conn.commit()
print(f"\nAdded {len(sample_preds)} sample predictions")

# Export
db.export_leaderboard_json(conn, Path('data/leaderboard.json'))
print('Exported leaderboard.json')
conn.close()
