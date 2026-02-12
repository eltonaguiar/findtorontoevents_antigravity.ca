# kelly_sizer.py - Compute Kelly fractions from live trade data
# Run periodically after trade closes
# Requirements: pip install mysql-connector-python
#
# NOTE: This script queries the ACTUAL lm_trades table schema managed by
# live_trade.php. Column names: algorithm_name, asset_class, realized_pnl_usd,
# realized_pct, status='closed'.
#
# The live_trade.php already auto-computes Kelly on every trade close
# (via _lt_update_kelly). This script serves as a BULK recalculation
# fallback, e.g. after importing historical data.

import mysql.connector
import os
import datetime

# DB config — use env vars (matches GitHub Actions secrets)
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

def compute_kelly():
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME)
    cursor = conn.cursor(dictionary=True)

    # Query per algorithm + asset_class (matches live_trade.php schema)
    query = """
    SELECT
        algorithm_name,
        asset_class,
        COUNT(*) AS sample_size,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) AS wins,
        AVG(CASE WHEN realized_pnl_usd > 0 THEN realized_pct ELSE NULL END) AS avg_win_pct,
        AVG(CASE WHEN realized_pnl_usd <= 0 THEN ABS(realized_pct) ELSE NULL END) AS avg_loss_pct
    FROM lm_trades
    WHERE status = 'closed'
    AND algorithm_name != ''
    GROUP BY algorithm_name, asset_class
    HAVING sample_size >= 5
    """
    cursor.execute(query)
    results = cursor.fetchall()

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    updated = 0

    for row in results:
        sample = int(row['sample_size'])
        wins = int(row['wins'])
        win_rate = wins / sample
        avg_win = float(row['avg_win_pct'] or 0)
        avg_loss = float(row['avg_loss_pct'] or 0.01)

        if avg_loss <= 0:
            avg_loss = 0.01  # Prevent division by zero

        odds = avg_win / avg_loss  # b = avg_win / avg_loss

        # Kelly criterion: f* = p - q/b = win_rate - (1-win_rate) / odds
        full_kelly = win_rate - ((1 - win_rate) / odds)
        half_kelly = full_kelly / 2

        # Clamp: negative Kelly = don't trade, cap at 25%
        if half_kelly < 0:
            half_kelly = 0
        if half_kelly > 0.25:
            half_kelly = 0.25

        algo = row['algorithm_name']
        asset = row['asset_class']

        # Upsert: delete old + insert new (matches live_trade.php pattern)
        cursor.execute("DELETE FROM lm_kelly_fractions WHERE algorithm_name = %s AND asset_class = %s",
                       (algo, asset))
        cursor.execute("""INSERT INTO lm_kelly_fractions
            (algorithm_name, asset_class, win_rate, avg_win_pct, avg_loss_pct,
             full_kelly, half_kelly, sample_size, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (algo, asset, round(win_rate, 4), round(avg_win, 4), round(avg_loss, 4),
             round(full_kelly, 4), round(half_kelly, 4), sample, now))
        updated += 1

    conn.commit()
    cursor.close()
    conn.close()
    return updated

if __name__ == '__main__':
    updated = compute_kelly()
    print(f'Updated Kelly for {updated} algorithm/asset combos')
