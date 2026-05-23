"""Track price outcomes for signals at multiple time horizons."""
import sys
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from signal_recorder.db import get_db, record_outcome

# API failover: never rely on a single Binance endpoint
try:
    from alpha_engine import api_failover
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from alpha_engine import api_failover

CHECK_HORIZONS = [15, 60, 240, 1440, 10080]  # minutes: 15m, 1h, 4h, 24h, 7d


def fetch_binance_prices():
    """Fetch all ticker prices with Binance mirror rotation + fallback."""
    for base in api_failover.BINANCE_SPOT_BASES:
        try:
            resp = requests.get(f"{base}/api/v3/ticker/price", timeout=10)
            if resp.status_code == 451:
                continue  # geo-blocked, try next mirror
            resp.raise_for_status()
            return {t["symbol"]: float(t["price"]) for t in resp.json()}
        except Exception:
            continue
    print("  WARNING: All Binance mirrors failed for bulk price fetch")
    return {}


def track_outcomes():
    """For signals old enough, record price outcome at each time horizon."""
    conn = get_db()
    prices = fetch_binance_prices()
    now = datetime.now(timezone.utc)
    stats = {"checked": 0, "outcomes_recorded": 0}

    for horizon in CHECK_HORIZONS:
        cutoff = (now - timedelta(minutes=horizon)).isoformat()
        rows = conn.execute("""
            SELECT sl.id, sl.symbol, sl.signal, sl.price_at_signal, sl.timestamp
            FROM signal_log sl
            WHERE sl.timestamp <= ?
              AND sl.price_at_signal IS NOT NULL
              AND sl.signal IN ('BUY', 'SELL')
              AND NOT EXISTS (
                  SELECT 1 FROM signal_outcomes so
                  WHERE so.signal_log_id = sl.id AND so.check_minutes = ?
              )
            LIMIT 500
        """, (cutoff, horizon)).fetchall()

        for row in rows:
            sym = row["symbol"]
            if sym not in prices:
                continue
            current_price = prices[sym]
            entry_price = row["price_at_signal"]
            if not entry_price or entry_price == 0:
                continue

            if row["signal"] == "BUY":
                pnl = round((current_price - entry_price) / entry_price * 100, 4)
            else:
                pnl = round((entry_price - current_price) / entry_price * 100, 4)

            record_outcome(conn, row["id"], horizon, current_price, pnl)
            stats["outcomes_recorded"] += 1
            stats["checked"] += 1

    conn.close()
    return stats


if __name__ == "__main__":
    stats = track_outcomes()
    print(f"Checked: {stats['checked']}")
    print(f"Outcomes recorded: {stats['outcomes_recorded']}")
