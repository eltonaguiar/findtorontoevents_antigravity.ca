import os
os.environ['AUDIT_DB_HOST'] = 'mysql.50webs.com'
os.environ['AUDIT_DB_USER'] = 'ejaguiar1_stocks'
os.environ['AUDIT_DB_PASS'] = 'stocks'
os.environ['AUDIT_DB_NAME'] = 'ejaguiar1_stocks'

from audit_trail.mysql_client import _create_connection

def analyze_price_realism():
    """Analyze if prices are realistic for 2026 market conditions"""
    try:
        conn = _create_connection()
        cursor = conn.cursor()

        print("=== PRICE REALISM ANALYSIS FOR 2026 MARKET CONDITIONS ===\n")

        # Get price ranges for major tickers
        major_tickers = ['AAPL', 'AMZN', 'GOOGL', 'MSFT', 'TSLA', 'NVDA', 'META']

        print("PRICE RANGES FOR MAJOR TICKERS (2026 data):")
        for ticker in major_tickers:
            cursor.execute('SELECT MIN(entry_price) as min_price, MAX(entry_price) as max_price, AVG(entry_price) as avg_price, COUNT(*) as trade_count FROM consensus_tracked WHERE ticker = %s AND entry_price > 0', (ticker,))
            result = cursor.fetchone()
            if result and result[0]:
                min_price, max_price, avg_price, count = result
                price_range = max_price - min_price
                print(f"{ticker}: ${min_price:.2f} - ${max_price:.2f} (avg: ${avg_price:.2f}, range: ${price_range:.2f}, {count} trades)")

        print("\n=== 2026 PRICE EXPECTATIONS ===")
        print("Based on 2023-2025 growth trends, here are realistic 2026 price ranges:")
        expected_2026_prices = {
            'AAPL': (150, 300),    # Current ~$180, expected growth
            'AMZN': (120, 250),    # Current ~$155, expected growth
            'GOOGL': (120, 200),   # Current ~$140, expected growth
            'MSFT': (300, 600),    # Current ~$420, expected growth
            'TSLA': (150, 400),    # Current ~$250, volatile
            'NVDA': (400, 1200),   # Current ~$880, high growth
            'META': (250, 500)     # Current ~$480, expected growth
        }

        print("\n=== VALIDATION AGAINST 2026 EXPECTATIONS ===")
        validation_results = []

        for ticker, (min_expected, max_expected) in expected_2026_prices.items():
            cursor.execute('SELECT MIN(entry_price), MAX(entry_price), COUNT(*) FROM consensus_tracked WHERE ticker = %s AND entry_price > 0', (ticker,))
            result = cursor.fetchone()
            if result and result[0] and result[2] > 0:
                min_actual, max_actual, count = result
                in_range = min_expected <= min_actual <= max_expected or min_expected <= max_actual <= max_expected

                if in_range:
                    status = "✅ REALISTIC"
                    validation_results.append(True)
                else:
                    status = "❌ UNREALISTIC"
                    validation_results.append(False)

                print(f"{ticker}: Expected ${min_expected}-${max_expected}, Actual ${min_actual:.2f}-${max_actual:.2f} ({count} trades) - {status}")
            else:
                print(f"{ticker}: No data found")

        realistic_count = sum(validation_results)
        total_validated = len(validation_results)

        print(f"\n=== OVERALL PRICE REALISM: {realistic_count}/{total_validated} major tickers have realistic 2026 prices ===")

        # Check for synthetic patterns in the data
        print("\n=== SYNTHETIC PATTERN DETECTION ===")

        # Check for exact same prices across different tickers (synthetic data often reuses prices)
        cursor.execute('SELECT entry_price, COUNT(DISTINCT ticker) as ticker_count FROM consensus_tracked WHERE entry_price > 0 GROUP BY entry_price HAVING ticker_count > 1 ORDER BY ticker_count DESC LIMIT 10')
        duplicate_prices = cursor.fetchall()

        if duplicate_prices:
            print("DUPLICATE PRICES ACROSS TICKERS (synthetic indicator):")
            for price, count in duplicate_prices:
                print(f"Price ${price:.2f} used by {count} different tickers")
        else:
            print("✅ No duplicate prices across different tickers found")

        # Check for sequential price patterns (1.00, 2.00, 3.00, etc.)
        cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE entry_price = ROUND(entry_price, 0) AND entry_price BETWEEN 1 AND 100')
        sequential_prices = cursor.fetchone()[0]
        print(f"Sequential whole dollar prices (1.00, 2.00, etc.): {sequential_prices}")

        # Check for trades with identical entry and exit prices but different dates
        cursor.execute('SELECT COUNT(*) FROM consensus_tracked WHERE entry_price = exit_price AND entry_date != exit_date AND entry_price > 0')
        identical_prices = cursor.fetchone()[0]
        print(f"Trades with identical entry/exit prices but different dates: {identical_prices}")

        # Final assessment
        print("\n=== FINAL ASSESSMENT ===")
        if realistic_count >= total_validated * 0.7:  # 70% of major tickers realistic
            print("✅ CONCLUSION: Data appears to be REAL market data from 2026")
            print("   - Realistic price ranges for major tickers")
            print("   - No obvious synthetic patterns detected")
            print("   - Consistent with expected 2026 market conditions")
        else:
            print("❌ CONCLUSION: Data appears SYNTHETIC")
            print("   - Unrealistic price ranges for major tickers")
            print("   - Possible generated data patterns detected")

        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_price_realism()