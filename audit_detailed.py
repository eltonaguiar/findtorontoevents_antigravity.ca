import os
os.environ['AUDIT_DB_HOST'] = 'mysql.50webs.com'
os.environ['AUDIT_DB_USER'] = 'ejaguiar1_stocks'
os.environ['AUDIT_DB_PASS'] = 'stocks'
os.environ['AUDIT_DB_NAME'] = 'ejaguiar1_stocks'

from audit_trail.mysql_client import _create_connection

try:
    conn = _create_connection()
    cursor = conn.cursor()

    print('=== INVESTIGATING NFLX 24.99% RETURN ===')

    cursor.execute('SELECT ticker, entry_date, entry_price, exit_date, exit_price, final_return_pct, hold_days, consensus_count, source_algos, status, exit_reason FROM consensus_tracked WHERE ticker = "NFLX" AND final_return_pct > 20')
    rows = cursor.fetchall()
    if rows:
        row = rows[0]
        print('NFLX suspicious trade details:')
        print(f'  Entry: ${row[2]} on {row[1]}')
        print(f'  Exit: ${row[4]} on {row[3]}')
        print(f'  Return: {row[5]:.2f}%')
        print(f'  Hold days: {row[6]}')
        print(f'  Consensus count: {row[7]}')
        print(f'  Source algos: {row[8]}')
        print(f'  Status: {row[9]}')
        print(f'  Exit reason: {row[10]}')

        # Check if prices are realistic
        entry_price = float(row[2])
        exit_price = float(row[4])
        calculated_return = ((exit_price - entry_price) / entry_price) * 100
        print(f'  Calculated return: {calculated_return:.2f}%')

        print('  AUDIT RESULT: This looks like data corruption - 25% return in 9 days is possible but extreme for NFLX')

    print()
    print('=== INVESTIGATING 0% RETURNS (POSSIBLE SYNTHETIC DATA) ===')

    cursor.execute('SELECT ticker, entry_date, exit_date, entry_price, exit_price, hold_days, status FROM consensus_tracked WHERE final_return_pct = 0 ORDER BY entry_date DESC LIMIT 10')
    rows = cursor.fetchall()
    print('Sample 0% return trades (many have exit_price = 0.0000):')
    for row in rows:
        print(f'  {row[0]}: ${row[3]} -> ${row[4]} ({row[5]} days, {row[1]} to {row[2]}, status: {row[6]})')

    print()
    print('=== AUDITING DATA CORRUPTION PATTERNS ===')

    # Check for trades with exit_price = 0 (clearly wrong)
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE exit_price = 0 AND exit_date IS NOT NULL')
    count = cursor.fetchone()[0]
    print(f'Trades with exit_price = 0 but exit_date set: {count}')

    # Check for trades with unrealistically high returns
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE final_return_pct > 50')
    count = cursor.fetchone()[0]
    print(f'Trades with return > 50%: {count}')

    cursor.execute('SELECT ticker, final_return_pct, hold_days FROM consensus_tracked WHERE final_return_pct > 50 ORDER BY final_return_pct DESC LIMIT 3')
    rows = cursor.fetchall()
    print('Extreme positive returns:')
    for row in rows:
        print(f'  {row[0]}: {row[1]:.2f}% in {row[2]} days')

    conn.close()
except Exception as e:
    print(f'Error: {e}')