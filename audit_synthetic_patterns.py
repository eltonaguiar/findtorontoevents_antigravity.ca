import os
os.environ['AUDIT_DB_HOST'] = 'mysql.50webs.com'
os.environ['AUDIT_DB_USER'] = 'ejaguiar1_stocks'
os.environ['AUDIT_DB_PASS'] = 'stocks'
os.environ['AUDIT_DB_NAME'] = 'ejaguiar1_stocks'

from audit_trail.mysql_client import _create_connection

try:
    conn = _create_connection()
    cursor = conn.cursor()

    print('=== DATA CONSISTENCY AND SYNTHETIC PATTERN ANALYSIS ===')
    print()

    # Check for rounded prices (synthetic data often uses clean numbers)
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE entry_price = ROUND(entry_price, 0)')
    result = cursor.fetchone()
    rounded_entry = result[0] if result else 0

    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE exit_price = ROUND(exit_price, 0)')
    result = cursor.fetchone()
    rounded_exit = result[0] if result else 0

    print(f'Entry prices that are whole dollars: {rounded_entry}')
    print(f'Exit prices that are whole dollars: {rounded_exit}')

    # Check for prices ending in .00 (very common in synthetic data)
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE entry_price = ROUND(entry_price, 2) AND entry_price % 1 = 0')
    result = cursor.fetchone()
    whole_dollar_entry = result[0] if result else 0

    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE exit_price = ROUND(exit_price, 2) AND exit_price % 1 = 0')
    result = cursor.fetchone()
    whole_dollar_exit = result[0] if result else 0

    print(f'Entry prices ending in .00: {whole_dollar_entry}')
    print(f'Exit prices ending in .00: {whole_dollar_exit}')

    # Check for trades with identical timestamps (batch inserted)
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE entry_date = exit_date AND hold_days = 0')
    result = cursor.fetchone()
    same_day_trades = result[0] if result else 0
    print(f'Same-day trades (entry=exit date): {same_day_trades}')

    # Check for trades entered on weekends (unusual for real trading)
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE DAYOFWEEK(entry_date) IN (1,7)')  # Sunday=1, Saturday=7
    result = cursor.fetchone()
    weekend_entries = result[0] if result else 0
    print(f'Trades entered on weekends: {weekend_entries}')

    # Check for sequential ticker patterns (A, B, C, etc. - synthetic)
    cursor.execute('SELECT ticker FROM consensus_tracked ORDER BY ticker LIMIT 20')
    tickers = [row[0] for row in cursor.fetchall()]
    sequential_count = 0
    for i in range(len(tickers)-1):
        if ord(tickers[i+1][0]) - ord(tickers[i][0]) == 1:
            sequential_count += 1
    print(f'Potential sequential ticker patterns: {sequential_count} pairs')

    # Check for trades with unrealistic precision (more than 4 decimal places)
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE entry_price - ROUND(entry_price, 4) != 0')
    result = cursor.fetchone()
    high_precision_entry = result[0] if result else 0

    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE exit_price - ROUND(exit_price, 4) != 0')
    result = cursor.fetchone()
    high_precision_exit = result[0] if result else 0

    print(f'Entry prices with >4 decimal precision: {high_precision_entry}')
    print(f'Exit prices with >4 decimal precision: {high_precision_exit}')

    # Check for trades with returns that don't match calculation
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE ABS(final_return_pct - ((exit_price - entry_price) / entry_price * 100)) > 0.01 AND exit_price > 0 AND entry_price > 0')
    result = cursor.fetchone()
    return_mismatches = result[0] if result else 0
    print(f'Trades with return calculation mismatches: {return_mismatches}')

    if return_mismatches > 0:
        cursor.execute('SELECT ticker, final_return_pct, ((exit_price - entry_price) / entry_price * 100) as calc_return FROM consensus_tracked WHERE ABS(final_return_pct - ((exit_price - entry_price) / entry_price * 100)) > 0.01 AND exit_price > 0 AND entry_price > 0 LIMIT 5')
        rows = cursor.fetchall()
        print('Return mismatches:')
        for row in rows:
            print(f'  {row[0]}: stored {row[1]:.6f}%, calculated {row[2]:.6f}%')

    # Check for trades with consensus_count > 10 (unrealistic)
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE consensus_count > 10')
    result = cursor.fetchone()
    high_consensus = result[0] if result else 0
    print(f'Trades with consensus_count > 10: {high_consensus}')

    # Check for trades with very long hold times (>365 days)
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE hold_days > 365')
    result = cursor.fetchone()
    long_hold = result[0] if result else 0
    print(f'Trades with hold_days > 365: {long_hold}')

    # Check for status inconsistencies
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE status = "closed_win" AND exit_price = 0')
    result = cursor.fetchone()
    closed_zero_price = result[0] if result else 0
    print(f'Closed winning trades with exit_price = 0: {closed_zero_price}')

    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE status = "open" AND exit_date IS NOT NULL')
    result = cursor.fetchone()
    open_with_exit_date = result[0] if result else 0
    print(f'Open trades with exit_date set: {open_with_exit_date}')

    print()
    print('=== SYNTHETIC DATA INDICATORS ===')
    synthetic_indicators = {
        'Whole dollar entry prices': whole_dollar_entry,
        'Whole dollar exit prices': whole_dollar_exit,
        'Same-day trades': same_day_trades,
        'Weekend entries': weekend_entries,
        'Return calculation mismatches': return_mismatches,
        'High consensus counts (>10)': high_consensus,
        'Status inconsistencies': closed_zero_price + open_with_exit_date
    }

    print('Strong synthetic data indicators:')
    for indicator, count in synthetic_indicators.items():
        if count > 0:
            print(f'- {indicator}: {count}')

    total_synthetic_flags = sum(synthetic_indicators.values())
    print(f'\nTotal synthetic data flags: {total_synthetic_flags}')

    # Overall assessment
    if total_synthetic_flags > 50:
        print('\nASSESSMENT: HIGHLY SYNTHETIC - This database shows strong patterns of generated data')
    elif total_synthetic_flags > 20:
        print('\nASSESSMENT: MODERATELY SYNTHETIC - Some generated data patterns detected')
    else:
        print('\nASSESSMENT: POSSIBLY LEGITIMATE - Few synthetic indicators found')

    conn.close()
except Exception as e:
    print(f'Error: {e}')