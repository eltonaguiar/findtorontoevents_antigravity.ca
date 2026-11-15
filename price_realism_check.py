import os
os.environ['AUDIT_DB_HOST'] = 'mysql.50webs.com'
os.environ['AUDIT_DB_USER'] = 'ejaguiar1_stocks'
os.environ['AUDIT_DB_PASS'] = 'stocks'
os.environ['AUDIT_DB_NAME'] = 'ejaguiar1_stocks'

from audit_trail.mysql_client import _create_connection


def fetch_5d_bounds(ticker: str):
    """Fetch recent 5-day OHLC low/high via yfinance.

    Returns (low, high, source) or None if yfinance is unavailable
    or the request fails.
    """
    try:
        import yfinance as yf  # noqa: PLC0415 — lazy by design
    except ImportError:
        return None
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if hist is None or hist.empty:
            return None
        low = float(hist["Low"].min())
        high = float(hist["High"].max())
        return (low, high, "yfinance_5d")
    except Exception:
        return None


def analyze_price_realism():
    """Analyze if prices are realistic using live 5-day bounds."""
    try:
        conn = _create_connection()
        cursor = conn.cursor()

        print("=== PRICE REALISM ANALYSIS (live 5-day bounds) ===\n")

        major_tickers = ['AAPL', 'AMZN', 'GOOGL', 'MSFT', 'TSLA', 'NVDA', 'META']

        print("PRICE RANGES FOR MAJOR TICKERS (DB data):")
        for ticker in major_tickers:
            cursor.execute(
                'SELECT MIN(entry_price) as min_price, MAX(entry_price) as max_price, '
                'AVG(entry_price) as avg_price, COUNT(*) as trade_count '
                'FROM consensus_tracked WHERE ticker = %s AND entry_price > 0',
                (ticker,)
            )
            result = cursor.fetchone()
            if result and result[0]:
                min_price, max_price, avg_price, count = result
                price_range = max_price - min_price
                print(
                    f"{ticker}: ${min_price:.2f} - ${max_price:.2f} "
                    f"(avg: ${avg_price:.2f}, range: ${price_range:.2f}, {count} trades)"
                )

        print("\n=== VALIDATION AGAINST LIVE 5-DAY BOUNDS ===")
        validation_results = []
        suspect_marks = []

        for ticker in major_tickers:
            cursor.execute(
                'SELECT MIN(entry_price), MAX(entry_price), COUNT(*) '
                'FROM consensus_tracked WHERE ticker = %s AND entry_price > 0',
                (ticker,)
            )
            result = cursor.fetchone()
            if not (result and result[0] and result[2] > 0):
                print(f"{ticker}: No data found")
                continue

            min_actual, max_actual, count = result

            bounds = fetch_5d_bounds(ticker)
            if bounds is None:
                status = "SUSPECT_MARK [NO_BOUNDS]"
                validation_results.append(False)
                suspect_marks.append((ticker, "NO_BOUNDS"))
                print(
                    f"{ticker}: Could not fetch 5d bounds — {status} "
                    f"(DB ${min_actual:.2f}-${max_actual:.2f}, {count} trades)"
                )
                continue

            five_low, five_high, source = bounds
            in_range = (
                five_low <= min_actual <= five_high
                and five_low <= max_actual <= five_high
            )

            if in_range:
                status = "REALISTIC"
                validation_results.append(True)
            else:
                status = "SUSPECT_MARK [PRICE_OUTSIDE_5D_RANGE]"
                validation_results.append(False)
                suspect_marks.append((ticker, "PRICE_OUTSIDE_5D_RANGE"))

            print(
                f"{ticker}: 5d bounds [${five_low:.2f}, ${five_high:.2f}] ({source}), "
                f"DB ${min_actual:.2f}-${max_actual:.2f} ({count} trades) — {status}"
            )

        realistic_count = sum(validation_results)
        total_validated = len(validation_results)

        print(
            f"\n=== OVERALL PRICE REALISM: {realistic_count}/{total_validated} "
            f"major tickers passed ==="
        )
        if suspect_marks:
            print("SUSPECT_MARKS:")
            for t, reason in suspect_marks:
                print(f"  {t}: {reason}")

        # Check for synthetic patterns in the data
        print("\n=== SYNTHETIC PATTERN DETECTION ===")

        # Check for exact same prices across different tickers
        cursor.execute(
            'SELECT entry_price, COUNT(DISTINCT ticker) as ticker_count '
            'FROM consensus_tracked WHERE entry_price > 0 '
            'GROUP BY entry_price HAVING ticker_count > 1 '
            'ORDER BY ticker_count DESC LIMIT 10'
        )
        duplicate_prices = cursor.fetchall()

        if duplicate_prices:
            print("DUPLICATE PRICES ACROSS TICKERS (synthetic indicator):")
            for price, count in duplicate_prices:
                print(f"Price ${price:.2f} used by {count} different tickers")
        else:
            print("No duplicate prices across different tickers found")

        # Check for sequential price patterns
        cursor.execute(
            'SELECT COUNT(*) FROM consensus_tracked '
            'WHERE entry_price = ROUND(entry_price, 0) '
            'AND entry_price BETWEEN 1 AND 100'
        )
        sequential_prices = cursor.fetchone()[0]
        print(f"Sequential whole dollar prices (1.00, 2.00, etc.): {sequential_prices}")

        # Check for trades with identical entry and exit prices but different dates
        cursor.execute(
            'SELECT COUNT(*) FROM consensus_tracked '
            'WHERE entry_price = exit_price AND entry_date != exit_date AND entry_price > 0'
        )
        identical_prices = cursor.fetchone()[0]
        print(f"Trades with identical entry/exit prices but different dates: {identical_prices}")

        # Final assessment
        print("\n=== FINAL ASSESSMENT ===")
        if not suspect_marks and realistic_count >= total_validated * 0.7:
            print("CONCLUSION: Data appears to be REAL market data")
            print("   - Prices fall within live 5-day bounds for major tickers")
            print("   - No obvious synthetic patterns detected")
        elif suspect_marks:
            print(f"CONCLUSION: {len(suspect_marks)} ticker(s) flagged with SUSPECT_MARK")
            print("   - Review flagged tickers for stale or synthetic data")
        else:
            print("CONCLUSION: Data appears SYNTHETIC")
            print("   - Unrealistic price ranges for major tickers")
            print("   - Possible generated data patterns detected")

        conn.close()

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    analyze_price_realism()
