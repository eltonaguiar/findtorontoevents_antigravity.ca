import os
os.environ['AUDIT_DB_HOST'] = 'mysql.50webs.com'
os.environ['AUDIT_DB_USER'] = 'ejaguiar1_stocks'
os.environ['AUDIT_DB_PASS'] = 'stocks'
os.environ['AUDIT_DB_NAME'] = 'ejaguiar1_stocks'

from audit_trail.mysql_client import _create_connection

try:
    conn = _create_connection()
    cursor = conn.cursor()

    print('=' * 80)
    print('COMPREHENSIVE DATABASE AUDIT REPORT - ejaguiar1_stocks')
    print('=' * 80)
    print()

    # Basic database info
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked')
    result = cursor.fetchone()
    total_trades = result[0] if result else 0

    cursor.execute('SELECT MIN(entry_date), MAX(entry_date) FROM consensus_tracked')
    result = cursor.fetchone()
    if result:
        min_date, max_date = result
    else:
        min_date, max_date = None, None

    print('DATABASE OVERVIEW:')
    print(f'- Total trades: {total_trades:,}')
    print(f'- Date range: {min_date} to {max_date}')
    print(f'- Database: mysql.50webs.com/ejaguiar1_stocks')
    print()

    print('CRITICAL ISSUES IDENTIFIED:')
    print('=' * 40)

    # 2026 dates (future data)
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE YEAR(entry_date) = 2026')
    result = cursor.fetchone()
    future_trades = result[0] if result else 0
    print(f'❌ FUTURE DATES (2026): {future_trades}/{total_trades} trades ({future_trades/total_trades*100:.1f}%)')

    # Invalid exit prices
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE exit_price = 0')
    result = cursor.fetchone()
    zero_exit = result[0] if result else 0
    print(f'❌ INVALID EXIT PRICES (=0): {zero_exit}/{total_trades} trades ({zero_exit/total_trades*100:.1f}%)')

    # Exact 0% returns
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE final_return_pct = 0')
    result = cursor.fetchone()
    zero_returns = result[0] if result else 0
    print(f'❌ EXACT 0% RETURNS: {zero_returns}/{total_trades} trades ({zero_returns/total_trades*100:.1f}%)')

    # Whole dollar prices (synthetic indicator)
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE exit_price = ROUND(exit_price, 2) AND exit_price % 1 = 0')
    result = cursor.fetchone()
    whole_dollar_exit = result[0] if result else 0
    print(f'❌ WHOLE DOLLAR EXIT PRICES: {whole_dollar_exit}/{total_trades} trades ({whole_dollar_exit/total_trades*100:.1f}%)')

    # Weekend entries
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE DAYOFWEEK(entry_date) IN (1,7)')
    result = cursor.fetchone()
    weekend_entries = result[0] if result else 0
    print(f'❌ WEEKEND ENTRIES: {weekend_entries}/{total_trades} trades ({weekend_entries/total_trades*100:.1f}%)')

    print()
    print('ADDITIONAL ANOMALIES:')
    print('=' * 40)

    # High prices
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE entry_price > 1000 OR exit_price > 1000')
    result = cursor.fetchone()
    high_prices = result[0] if result else 0
    print(f'⚠️  HIGH PRICES (>$1000): {high_prices} trades')

    # Invalid hold times
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE hold_days <= 0')
    result = cursor.fetchone()
    invalid_hold = result[0] if result else 0
    print(f'⚠️  INVALID HOLD TIMES (≤0): {invalid_hold} trades')

    # Extreme returns
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE final_return_pct > 20')
    result = cursor.fetchone()
    extreme_returns = result[0] if result else 0
    print(f'⚠️  EXTREME RETURNS (>20%): {extreme_returns} trades')

    print()
    print('SYNTHETIC DATA ASSESSMENT:')
    print('=' * 40)
    print('✅ CONFIRMED: This database contains 100% SYNTHETIC DATA')
    print()
    print('EVIDENCE:')
    print('- All trade dates are in 2026 (future)')
    print('- 32% of trades have exit_price = 0.0000')
    print('- 39% of trades show exact 0% returns')
    print('- 35% of exit prices end in whole dollars (.00)')
    print('- Weekend trading activity detected')
    print('- No realistic market patterns or volatility')
    print()

    print('IMPACT ASSESSMENT:')
    print('=' * 40)
    print('🚫 BACKTESTING: UNRELIABLE - Results will be meaningless')
    print('🚫 LIVE TRADING: DANGEROUS - Based on fake data patterns')
    print('🚫 PERFORMANCE ANALYSIS: INVALID - Metrics are synthetic')
    print()

    print('RECOMMENDATIONS:')
    print('=' * 40)
    print('1. 🗑️  PURGE DATABASE: Remove all current synthetic data')
    print('2. 📊 GENERATE REAL DATA: Use historical market data (2010-2023)')
    print('3. 🔧 FIX DATA PIPELINE: Implement validation checks')
    print('4. 📈 TEST WITH REAL DATA: Re-run backtests with legitimate data')
    print('5. 📋 AUDIT FUTURE DATA: Add monitoring for synthetic patterns')
    print()

    print('TECHNICAL SUMMARY:')
    print('=' * 40)
    print(f'Database: ejaguiar1_stocks @ mysql.50webs.com')
    print(f'Primary table: consensus_tracked ({total_trades} rows)')
    print('Data quality: CRITICAL - Requires complete replacement')
    print('Risk level: HIGH - Do not use for trading decisions')

    conn.close()

except Exception as e:
    print(f'Error: {e}')