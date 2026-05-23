import os
os.environ['AUDIT_DB_HOST'] = 'mysql.50webs.com'
os.environ['AUDIT_DB_USER'] = 'ejaguiar1_stocks'
os.environ['AUDIT_DB_PASS'] = 'stocks'
os.environ['AUDIT_DB_NAME'] = 'ejaguiar1_stocks'

from audit_trail.mysql_client import _create_connection

try:
    conn = _create_connection()
    cursor = conn.cursor()

    print('=== CHECKING FOR SUSPICIOUS RETURNS ===')

    # Check consensus_tracked for high returns
    cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE ABS(final_return_pct) > 10')
    count = cursor.fetchone()[0]
    print(f'consensus_tracked: {count} trades with |return| > 10%')

    if count > 0:
        cursor.execute('SELECT ticker, final_return_pct, status, exit_reason FROM consensus_tracked WHERE ABS(final_return_pct) > 10 ORDER BY final_return_pct DESC LIMIT 10')
        rows = cursor.fetchall()
        print('Top suspicious returns:')
        for row in rows:
            print(f'  {row[0]}: {row[1]}% ({row[2]}, {row[3]})')

    # Check simulation_grid for unrealistic returns
    cursor.execute('SELECT COUNT(*) FROM simulation_grid WHERE ABS(total_return_pct) > 50')
    count = cursor.fetchone()[0]
    print(f'simulation_grid: {count} simulations with |return| > 50%')

    if count > 0:
        cursor.execute('SELECT algorithm, total_return_pct, win_rate FROM simulation_grid WHERE ABS(total_return_pct) > 50 ORDER BY total_return_pct DESC LIMIT 5')
        rows = cursor.fetchall()
        print('Top simulation returns:')
        for row in rows:
            print(f'  {row[0]}: {row[1]}% (WR: {row[2]}%)')

    # Check strategy_health for suspicious metrics
    cursor.execute('SELECT COUNT(*) FROM strategy_health WHERE expectancy > 5 OR expectancy < -5')
    count = cursor.fetchone()[0]
    print(f'strategy_health: {count} strategies with expectancy > 5 or < -5')

    if count > 0:
        cursor.execute('SELECT source_system, strategy, expectancy, win_rate FROM strategy_health WHERE expectancy > 5 OR expectancy < -5 ORDER BY expectancy DESC LIMIT 5')
        rows = cursor.fetchall()
        print('Suspicious expectancies:')
        for row in rows:
            print(f'  {row[0]}/{row[1]}: expectancy {row[2]}, WR {row[3]}%')

    # Check for dummy data patterns
    print()
    print('=== CHECKING FOR DUMMY DATA PATTERNS ===')

    # Repeated identical values
    cursor.execute('SELECT entry_price, COUNT(*) as cnt FROM consensus_tracked GROUP BY entry_price HAVING cnt > 3 ORDER BY cnt DESC LIMIT 5')
    rows = cursor.fetchall()
    if rows:
        print('Repeated entry prices (possible dummy data):')
        for row in rows:
            print(f'  Price {row[0]}: {row[1]} times')

    # Check for obvious test tickers
    cursor.execute("SELECT ticker, COUNT(*) as cnt FROM consensus_tracked WHERE ticker LIKE 'TEST%' OR ticker LIKE 'DUMMY%' GROUP BY ticker")
    rows = cursor.fetchall()
    if rows:
        print('Test/dummy tickers found:')
        for row in rows:
            print(f'  {row[0]}: {row[1]} occurrences')

    # Check for unrealistic win rates
    cursor.execute('SELECT COUNT(*) FROM strategy_health WHERE win_rate > 90 OR win_rate < 10')
    count = cursor.fetchone()[0]
    print(f'strategy_health: {count} strategies with win_rate > 90% or < 10%')

    if count > 0:
        cursor.execute('SELECT source_system, strategy, expectancy, win_rate FROM strategy_health WHERE win_rate > 90 OR win_rate < 10 ORDER BY win_rate DESC LIMIT 5')
        rows = cursor.fetchall()
        print('Extreme win rates:')
        for row in rows:
            print(f'  {row[0]}/{row[1]}: expectancy {row[2]}, WR {row[3]}%')

    conn.close()
except Exception as e:
    print(f'Error: {e}')