import os
os.environ['AUDIT_DB_HOST'] = 'mysql.50webs.com'
os.environ['AUDIT_DB_USER'] = 'ejaguiar1_stocks'
os.environ['AUDIT_DB_PASS'] = 'stocks'
os.environ['AUDIT_DB_NAME'] = 'ejaguiar1_stocks'

from audit_trail.mysql_client import _create_connection

def final_synthetic_proof():
    """Final comprehensive check to prove if data is synthetic"""
    try:
        conn = _create_connection()
        cursor = conn.cursor()

        print("=== FINAL SYNTHETIC DATA PROOF ===\n")

        # Check 1: Price consistency with known 2023 prices vs stored 2026 prices
        print("CHECK 1: PRICE CONSISTENCY WITH MARKET REALITY")
        print("Comparing stored '2026' prices with what we know about 2023-2025 market trends:\n")

        # Real market data knowledge (approximate 2023 prices and expected 2026 growth)
        market_reality = {
            'AAPL': {'2023_price': 180, 'expected_2026_range': (200, 350), 'stored_range': None},
            'AMZN': {'2023_price': 155, 'expected_2026_range': (180, 300), 'stored_range': None},
            'GOOGL': {'2023_price': 140, 'expected_2026_range': (160, 250), 'stored_range': None},
            'MSFT': {'2023_price': 380, 'expected_2026_range': (450, 700), 'stored_range': None},
            'NVDA': {'2023_price': 500, 'expected_2026_range': (600, 1500), 'stored_range': None},
            'META': {'2023_price': 330, 'expected_2026_range': (400, 650), 'stored_range': None},
            'TSLA': {'2023_price': 250, 'expected_2026_range': (200, 500), 'stored_range': None}
        }

        # Get actual stored price ranges
        for ticker in market_reality.keys():
            cursor.execute('SELECT MIN(entry_price), MAX(entry_price) FROM consensus_tracked WHERE ticker = %s AND entry_price > 0', (ticker,))
            result = cursor.fetchone()
            if result and result[0]:
                market_reality[ticker]['stored_range'] = (float(result[0]), float(result[1]))

        # Compare expectations vs reality
        synthetic_indicators = 0
        for ticker, data in market_reality.items():
            if data['stored_range']:
                expected_min, expected_max = data['expected_2026_range']
                stored_min, stored_max = data['stored_range']

                # Check if stored prices are completely outside expected range
                if stored_max < expected_min or stored_min > expected_max:
                    synthetic_indicators += 1
                    print(f"❌ {ticker}: Expected 2026 range ${expected_min}-${expected_max}, but stored ${stored_min:.2f}-${stored_max:.2f} (IMPOSSIBLE)")
                else:
                    overlap = min(stored_max, expected_max) - max(stored_min, expected_min)
                    if overlap > 0:
                        print(f"✅ {ticker}: Expected 2026 range ${expected_min}-${expected_max}, stored ${stored_min:.2f}-${stored_max:.2f} (REALISTIC)")
                    else:
                        synthetic_indicators += 1
                        print(f"❌ {ticker}: No overlap between expected and stored ranges")

        print(f"\nSYNTHETIC INDICATORS FROM PRICE ANALYSIS: {synthetic_indicators}/{len(market_reality)} tickers have impossible prices")

        # Check 2: Statistical patterns that indicate synthetic data
        print("\nCHECK 2: STATISTICAL PATTERNS")

        # Check for exact return percentages (synthetic data often uses clean numbers)
        cursor.execute('SELECT final_return_pct, COUNT(*) as frequency FROM consensus_tracked GROUP BY final_return_pct HAVING frequency > 1 ORDER BY frequency DESC LIMIT 10')
        return_patterns = cursor.fetchall()

        exact_returns = sum(count for _, count in return_patterns if count > 1)
        print(f"Trades with exact same return percentages: {exact_returns}")

        if exact_returns > 10:
            print("❌ SYNTHETIC PATTERN: Too many trades with identical returns")
        else:
            print("✅ NATURAL PATTERN: Reasonable variation in returns")

        # Check 3: Data entry patterns
        print("\nCHECK 3: DATA ENTRY PATTERNS")

        # Check if all trades entered on same day (batch import)
        cursor.execute('SELECT COUNT(DISTINCT DATE(entry_date)) as unique_days FROM consensus_tracked')
        unique_days = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM consensus_tracked')
        total_trades = cursor.fetchone()[0]

        print(f"Trades spread across {unique_days} different days")
        if unique_days < 10 and total_trades > 50:
            print("❌ SYNTHETIC PATTERN: Too many trades concentrated on few days")
        else:
            print("✅ NATURAL PATTERN: Trades spread across multiple days")

        # Check 4: Algorithm consensus patterns
        print("\nCHECK 4: ALGORITHM CONSENSUS PATTERNS")

        cursor.execute('SELECT consensus_count, COUNT(*) as frequency FROM consensus_tracked GROUP BY consensus_count ORDER BY consensus_count')
        consensus_dist = cursor.fetchall()

        print("Consensus count distribution:")
        for count, freq in consensus_dist:
            print(f"  {count} algorithms: {freq} trades")

        # Check for unrealistic consensus counts
        high_consensus = sum(freq for count, freq in consensus_dist if count > 10)
        if high_consensus > 0:
            print(f"❌ SYNTHETIC PATTERN: {high_consensus} trades with unrealistically high consensus (>10 algorithms)")
        else:
            print("✅ NATURAL PATTERN: Realistic consensus counts")

        # FINAL VERDICT
        print("\n" + "="*60)
        print("FINAL VERDICT: IS THIS SYNTHETIC DATA?")
        print("="*60)

        evidence_points = [
            synthetic_indicators >= 3,  # 3+ tickers with impossible prices
            exact_returns > 20,         # Too many identical returns
            unique_days < 5,           # Trades too concentrated
            high_consensus > 10        # Unrealistic consensus
        ]

        synthetic_score = sum(evidence_points)

        if synthetic_score >= 2:
            print("🚨 VERDICT: SYNTHETIC DATA CONFIRMED")
            print(f"   Evidence score: {synthetic_score}/4 indicators positive")
            print("   - Impossible price ranges for major tickers")
            print("   - Statistical patterns inconsistent with real markets")
            print("   - Data entry patterns suggest batch generation")
        else:
            print("✅ VERDICT: POTENTIALLY REAL DATA")
            print(f"   Evidence score: {synthetic_score}/4 indicators positive")
            print("   - Price ranges mostly consistent with market expectations")
            print("   - Natural statistical distribution")

        print("\nRECOMMENDATION:")
        if synthetic_score >= 2:
            print("   🗑️  DELETE this data and regenerate from real market sources")
            print("   📊 Use historical data from 2020-2025 for backtesting")
            print("   🔧 Implement data validation before accepting new trades")
        else:
            print("   ✅ This data can be used for analysis and backtesting")
            print("   📈 Proceed with confidence in the dataset")

        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    final_synthetic_proof()