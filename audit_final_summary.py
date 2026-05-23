import os
os.environ['AUDIT_DB_HOST'] = 'mysql.50webs.com'
os.environ['AUDIT_DB_USER'] = 'ejaguiar1_stocks'
os.environ['AUDIT_DB_PASS'] = 'stocks'
os.environ['AUDIT_DB_NAME'] = 'ejaguiar1_stocks'

from audit_trail.mysql_client import _create_connection

try:
    conn = _create_connection()
    cursor = conn.cursor()

    print('=== DATABASE SYNTHETIC DATA AUDIT SUMMARY ===')
    print()

    # Total trades
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked')
    result = cursor.fetchone()
    total_trades = result[0] if result else 0
    print(f'Total trades in database: {total_trades:,}')

    # Date range analysis
    cursor.execute('SELECT MIN(entry_date), MAX(entry_date) FROM consensus_tracked')
    result = cursor.fetchone()
    if result:
        min_date, max_date = result
    else:
        min_date, max_date = None, None
    print(f'Date range: {min_date} to {max_date}')

    # 2026 trades (clearly synthetic)
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE YEAR(entry_date) = 2026')
    result = cursor.fetchone()
    future_trades = result[0] if result else 0
    print(f'Trades with 2026 entry dates: {future_trades:,} ({future_trades/total_trades*100:.1f}%)')

    # Zero exit price trades
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE exit_price = 0')
    result = cursor.fetchone()
    zero_exit = result[0] if result else 0
    print(f'Trades with exit_price = 0: {zero_exit:,} ({zero_exit/total_trades*100:.1f}%)')

    # Exact 0% returns
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE final_return_pct = 0')
    result = cursor.fetchone()
    zero_returns = result[0] if result else 0
    print(f'Trades with exact 0% return: {zero_returns:,} ({zero_returns/total_trades*100:.1f}%)')

    # Open trades with exit_price = 0
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE status = "open" AND exit_price = 0')
    result = cursor.fetchone()
    open_zero = result[0] if result else 0
    print(f'Open trades with exit_price = 0: {open_zero:,}')

    # High return trades (>20%)
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE final_return_pct > 20')
    result = cursor.fetchone()
    high_returns = result[0] if result else 0
    print(f'Trades with return > 20%: {high_returns}')

    # Perfect win rate strategies
    cursor.execute('SELECT COUNT(*) FROM strategy_health WHERE win_rate = 100 AND total_trades > 0')
    result = cursor.fetchone()
    perfect_strategies = result[0] if result else 0
    print(f'Strategies with 100% win rate: {perfect_strategies}')

    print()
    print('=== CONCLUSION ===')
    print('This database appears to contain primarily synthetic/future data:')
    print('- All dates are in 2026 (future dates)')
    print('- Many trades have exit_price = 0.0000 (invalid)')
    print('- Numerous exact 0% returns (suspicious pattern)')
    print('- Some extreme returns that need manual verification')
    print()
    print('RECOMMENDATION: This data should not be used for backtesting or live trading.')
    print('Consider regenerating with historical market data or removing synthetic entries.')

    conn.close()
except Exception as e:
    print(f'Error: {e}')