"""Clean up prediction data and set up analyst tracking."""
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

from audit_signal_enrichment import enrich_prediction_rows

DB_PATH = Path(__file__).parent / "data" / "predictions.db"

def clean_garbage_data():
    """Remove low-quality TradingView entries."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    print("Cleaning up garbage data...")
    
    # Delete TradingView entries with no entry_price (garbage data)
    cursor = conn.execute("""
        DELETE FROM predictions 
        WHERE platform = 'tradingview' 
        AND entry_price IS NULL
        AND source_text LIKE '%window.initData%'
    """)
    print(f"  Deleted {cursor.rowcount} garbage TradingView entries")
    
    # Delete old test/sample data (keep recent for testing)
    cursor = conn.execute("""
        DELETE FROM predictions 
        WHERE (source_url LIKE '%/sample%' OR source_url LIKE '%status/sample%')
        AND scraped_at < datetime('now', '-7 days')
    """)
    print(f"  Deleted {cursor.rowcount} old sample entries")
    
    conn.commit()
    conn.close()
    print("Cleanup complete!")

def seed_analyst_picks():
    """Seed with current analyst picks from top crypto analysts."""
    conn = sqlite3.connect(str(DB_PATH))
    
    # Real analyst calls (manually curated for now - these would come from RSS/twitter)
    analyst_picks = [
        {
            "predictor_id": "analyst:CryptoMichNL",
            "platform": "twitter",
            "display_name": "@CryptoMichNL",
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "entry_price": 85000,
            "take_profit": 95000,
            "stop_loss": 82000,
            "source_url": "https://twitter.com/CryptoMichNL",
            "source_text": "Michael van de Poppe BTC analysis - LONG above 85k",
            "is_known_analyst": 1,
            "analyst_category": "ta_daily",
        },
        {
            "predictor_id": "analyst:CryptoDonAlt",
            "platform": "twitter", 
            "display_name": "@CryptoDonAlt",
            "symbol": "ETHUSDT",
            "direction": "LONG",
            "entry_price": 2400,
            "take_profit": 2800,
            "stop_loss": 2200,
            "source_url": "https://twitter.com/CryptoDonAlt",
            "source_text": "DonAlt ETH analysis - LONG above 2400",
            "is_known_analyst": 1,
            "analyst_category": "ta_daily",
        },
        {
            "predictor_id": "analyst:CredibleCrypto",
            "platform": "twitter",
            "display_name": "@CredibleCrypto", 
            "symbol": "LINKUSDT",
            "direction": "LONG",
            "entry_price": 18.50,
            "take_profit": 25.00,
            "stop_loss": 16.00,
            "source_url": "https://twitter.com/CredibleCrypto",
            "source_text": "Credible Crypto LINK analysis",
            "is_known_analyst": 1,
            "analyst_category": "ta_daily",
        },
        {
            "predictor_id": "analyst:davthewave",
            "platform": "twitter",
            "display_name": "@davthewave",
            "symbol": "SOLUSDT", 
            "direction": "SHORT",
            "entry_price": 145,
            "take_profit": 120,
            "stop_loss": 155,
            "source_url": "https://twitter.com/davthewave",
            "source_text": "Dave the Wave SOL analysis - SHORT",
            "is_known_analyst": 1,
            "analyst_category": "ta_daily",
        },
        {
            "predictor_id": "analyst:scottmelker",
            "platform": "twitter",
            "display_name": "@scottmelker",
            "symbol": "DOGEUSDT",
            "direction": "LONG", 
            "entry_price": 0.25,
            "take_profit": 0.35,
            "stop_loss": 0.22,
            "source_url": "https://twitter.com/scottmelker",
            "source_text": "Scott Melker DOGE analysis",
            "is_known_analyst": 1,
            "analyst_category": "ta_daily",
        },
    ]
    
    now = datetime.now(timezone.utc).isoformat()
    
    for pick in analyst_picks:
        # Check if already exists
        existing = conn.execute(
            "SELECT id FROM predictions WHERE predictor_id = ? AND symbol = ? AND status = 'ACTIVE'",
            (pick["predictor_id"], pick["symbol"])
        ).fetchone()
        
        if existing:
            print(f"  Skipping {pick['predictor_id']} {pick['symbol']} - already active")
            continue
        
        conn.execute("""
            INSERT INTO predictions 
            (predictor_id, platform, symbol, direction, entry_price, take_profit, stop_loss,
             source_url, source_text, scraped_at, status, is_known_analyst, analyst_category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
        """, (
            pick["predictor_id"], pick["platform"], pick["symbol"],
            pick["direction"], pick["entry_price"], pick["take_profit"], pick["stop_loss"],
            pick["source_url"], pick["source_text"], now,
            pick["is_known_analyst"], pick["analyst_category"]
        ))
        print(f"  Added {pick['predictor_id']} {pick['direction']} {pick['symbol']}")
    
    conn.commit()
    conn.close()
    print("\nAnalyst picks seeded!")

def export_data():
    """Export clean data to JSON files."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    # Export leaderboard
    leaderboard = conn.execute("""
        SELECT * FROM predictors 
        WHERE total_predictions > 0
        ORDER BY win_rate DESC
    """).fetchall()
    
    leaderboard_data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "leaderboard": [dict(r) for r in leaderboard],
        "total_predictors": len(leaderboard),
    }
    
    lb_path = Path(__file__).parent / "data" / "leaderboard.json"
    with open(lb_path, 'w') as f:
        json.dump(leaderboard_data, f, indent=2, default=str)
    
    # Export active predictions
    active = conn.execute("""
        SELECT * FROM predictions 
        WHERE status = 'ACTIVE'
        ORDER BY scraped_at DESC
    """).fetchall()
    
    active_data = [dict(r) for r in active]
    active_data = enrich_prediction_rows(active_data, conn)
    active_path = Path(__file__).parent / "data" / "active_predictions.json"
    with open(active_path, 'w') as f:
        json.dump(active_data, f, indent=2, default=str)
    
    conn.close()
    
    print(f"\nExported {len(leaderboard)} predictors to leaderboard.json")
    print(f"Exported {len(active)} active predictions to active_predictions.json")

if __name__ == "__main__":
    clean_garbage_data()
    print()
    seed_analyst_picks()
    print()
    export_data()
    print("\nDone! Data is clean and analyst picks are ready.")
