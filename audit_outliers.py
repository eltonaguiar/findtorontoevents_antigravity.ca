import os
os.environ['AUDIT_DB_HOST'] = 'mysql.50webs.com'
os.environ['AUDIT_DB_USER'] = 'ejaguiar1_stocks'
os.environ['AUDIT_DB_PASS'] = 'stocks'
os.environ['AUDIT_DB_NAME'] = 'ejaguiar1_stocks'

from audit_trail.mysql_client import _create_connection

try:
    conn = _create_connection()
    cursor = conn.cursor()

    print('=== OUTLIER DATA DETECTION ===')
    print()

    # Check for extreme negative returns
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE final_return_pct < -50')
    result = cursor.fetchone()
    extreme_losses = result[0] if result else 0
    print(f'Trades with return < -50%: {extreme_losses}')

    if extreme_losses > 0:
        cursor.execute('SELECT ticker, final_return_pct, hold_days FROM consensus_tracked WHERE final_return_pct < -50 ORDER BY final_return_pct ASC LIMIT 5')
        rows = cursor.fetchall()
        print('Extreme losses:')
        for row in rows:
            print(f'  {row[0]}: {row[1]:.2f}% in {row[2]} days')

    # Check for unrealistically short hold times with high returns
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE hold_days <= 1 AND final_return_pct > 10')
    result = cursor.fetchone()
    quick_gains = result[0] if result else 0
    print(f'Trades with >10% return in <=1 day: {quick_gains}')

    if quick_gains > 0:
        cursor.execute('SELECT ticker, final_return_pct, hold_days FROM consensus_tracked WHERE hold_days <= 1 AND final_return_pct > 10 ORDER BY final_return_pct DESC LIMIT 5')
        rows = cursor.fetchall()
        print('Quick gains:')
        for row in rows:
            print(f'  {row[0]}: {row[1]:.2f}% in {row[2]} days')

    # Check for trades with identical entry and exit prices but non-zero returns
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE entry_price = exit_price AND final_return_pct != 0')
    result = cursor.fetchone()
    price_mismatches = result[0] if result else 0
    print(f'Trades with same entry/exit price but non-zero return: {price_mismatches}')

    if price_mismatches > 0:
        cursor.execute('SELECT ticker, entry_price, exit_price, final_return_pct FROM consensus_tracked WHERE entry_price = exit_price AND final_return_pct != 0 LIMIT 5')
        rows = cursor.fetchall()
        print('Price mismatches:')
        for row in rows:
            print(f'  {row[0]}: ${row[1]} -> ${row[2]}, return: {row[3]:.2f}%')

    # Check for trades with negative exit prices
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE exit_price < 0')
    result = cursor.fetchone()
    negative_prices = result[0] if result else 0
    print(f'Trades with negative exit prices: {negative_prices}')

    if negative_prices > 0:
        cursor.execute('SELECT ticker, entry_price, exit_price, final_return_pct FROM consensus_tracked WHERE exit_price < 0 LIMIT 5')
        rows = cursor.fetchall()
        print('Negative exit prices:')
        for row in rows:
            print(f'  {row[0]}: ${row[1]} -> ${row[2]}, return: {row[3]:.2f}%')

    # Check for trades with unrealistically high prices (>$1000)
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE entry_price > 1000 OR exit_price > 1000')
    result = cursor.fetchone()
    high_prices = result[0] if result else 0
    print(f'Trades with prices >$1000: {high_prices}')

    if high_prices > 0:
        cursor.execute('SELECT ticker, entry_price, exit_price FROM consensus_tracked WHERE entry_price > 1000 OR exit_price > 1000 LIMIT 5')
        rows = cursor.fetchall()
        print('High prices:')
        for row in rows:
            print(f'  {row[0]}: ${row[1]} -> ${row[2]}')

    # Check for trades with zero or negative hold days
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE hold_days <= 0')
    result = cursor.fetchone()
    invalid_hold_times = result[0] if result else 0
    print(f'Trades with hold_days <= 0: {invalid_hold_times}')

    if invalid_hold_times > 0:
        cursor.execute('SELECT ticker, entry_date, exit_date, hold_days FROM consensus_tracked WHERE hold_days <= 0 LIMIT 5')
        rows = cursor.fetchall()
        print('Invalid hold times:')
        for row in rows:
            print(f'  {row[0]}: {row[1]} to {row[2]}, hold_days: {row[3]}')

    # Check for duplicate trades (same ticker, entry_date, exit_date)
    cursor.execute('SELECT ticker, entry_date, exit_date, COUNT(*) as count FROM consensus_tracked GROUP BY ticker, entry_date, exit_date HAVING COUNT(*) > 1 ORDER BY count DESC LIMIT 5')
    duplicate_trades = cursor.fetchall()
    if duplicate_trades:
        print(f'Duplicate trades found: {len(duplicate_trades)} patterns')
        for row in duplicate_trades:
            print(f'  {row[0]}: {row[1]} to {row[2]}, {row[3]} duplicates')

    # Check for trades with consensus_count = 0 (no algorithmic consensus)
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE consensus_count = 0')
    result = cursor.fetchone()
    no_consensus = result[0] if result else 0
    print(f'Trades with consensus_count = 0: {no_consensus}')

    # Check for trades with empty or null source_algos
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE source_algos IS NULL OR source_algos = ""')
    result = cursor.fetchone()
    no_algos = result[0] if result else 0
    print(f'Trades with no source algorithms: {no_algos}')

    print()
    print('=== SUMMARY OF OUTLIERS DETECTED ===')
    outliers = {
        'Extreme losses (<-50%)': extreme_losses,
        'Quick gains (>10% in <=1 day)': quick_gains,
        'Price mismatches': price_mismatches,
        'Negative exit prices': negative_prices,
        'High prices (>$1000)': high_prices,
        'Invalid hold times (<=0)': invalid_hold_times,
        'No consensus trades': no_consensus,
        'No source algorithms': no_algos
    }

    total_outliers = sum(outliers.values())
    print(f'Total outlier patterns detected: {len([k for k, v in outliers.items() if v > 0])} categories')
    print(f'Total anomalous trades: {total_outliers}')

    for category, count in outliers.items():
        if count > 0:
            print(f'- {category}: {count}')

    conn.close()
except Exception as e:
    print(f'Error: {e}')