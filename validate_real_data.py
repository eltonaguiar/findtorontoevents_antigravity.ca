import os
os.environ['AUDIT_DB_HOST'] = 'mysql.50webs.com'
os.environ['AUDIT_DB_USER'] = 'ejaguiar1_stocks'
os.environ['AUDIT_DB_PASS'] = 'stocks'
os.environ['AUDIT_DB_NAME'] = 'ejaguiar1_stocks'

from audit_trail.mysql_client import _create_connection
import requests
from datetime import datetime, timedelta

def get_current_prices(tickers):
    """Get current prices for validation"""
    prices = {}
    for ticker in tickers[:5]:  # Limit to first 5 to avoid rate limits
        try:
            # Using Yahoo Finance API (you might need to adjust this)
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'chart' in data and 'result' in data['chart']['result']:
                    price_data = data['chart']['result'][0]
                    if 'meta' in price_data:
                        current_price = price_data['meta'].get('regularMarketPrice')
                        if current_price:
                            prices[ticker] = current_price
        except Exception as e:
            print(f"Could not fetch price for {ticker}: {e}")
    return prices

def validate_ticker_realism():
    """Check if tickers are real market tickers"""
    try:
        conn = _create_connection()
        cursor = conn.cursor()

        # Get unique tickers
        cursor.execute('SELECT DISTINCT ticker FROM consensus_tracked ORDER BY ticker')
        tickers = [row[0] for row in cursor.fetchall()]

        print(f"Found {len(tickers)} unique tickers")
        print("Sample tickers:", tickers[:10])

        # Check for obviously fake tickers
        fake_indicators = ['TEST', 'DUMMY', 'FAKE', 'SAMPLE']
        fake_tickers = [t for t in tickers if any(indicator in t.upper() for indicator in fake_indicators)]
        if fake_tickers:
            print(f"❌ Found fake tickers: {fake_tickers}")
        else:
            print("✅ No obviously fake tickers found")

        # Get current market prices for validation
        print("\nFetching current market prices for validation...")
        current_prices = get_current_prices(tickers)

        # Compare stored prices with current market prices
        print("\nPRICE VALIDATION (comparing with current market data):")
        cursor.execute('SELECT ticker, entry_price, exit_price, entry_date, exit_date FROM consensus_tracked WHERE entry_price > 0 AND exit_price > 0 LIMIT 20')
        trades = cursor.fetchall()

        realistic_trades = 0
        unrealistic_trades = 0

        for trade in trades:
            ticker, entry_price, exit_price, entry_date, exit_date = trade
            current_price = current_prices.get(ticker)

            if current_price:
                # Check if stored prices are within reasonable range of current price
                entry_ratio = abs(entry_price - current_price) / current_price
                exit_ratio = abs(exit_price - current_price) / current_price

                if entry_ratio < 0.5 and exit_ratio < 0.5:  # Within 50% of current price
                    realistic_trades += 1
                    print(f"✅ {ticker}: Entry ${entry_price:.2f}, Exit ${exit_price:.2f}, Current ${current_price:.2f}")
                else:
                    unrealistic_trades += 1
                    print(f"❌ {ticker}: Entry ${entry_price:.2f}, Exit ${exit_price:.2f}, Current ${current_price:.2f} (unrealistic)")

        if realistic_trades > 0:
            print(f"\nREALISTIC PRICE ANALYSIS: {realistic_trades} trades have prices within 50% of current market prices")
        if unrealistic_trades > 0:
            print(f"SYNTHETIC INDICATOR: {unrealistic_trades} trades have unrealistic prices vs current market")

        # Check date consistency
        print("\nDATE CONSISTENCY CHECK:")
        cursor.execute('SELECT ticker, entry_date, exit_date, hold_days FROM consensus_tracked WHERE entry_date IS NOT NULL AND exit_date IS NOT NULL LIMIT 10')
        date_checks = cursor.fetchall()

        for trade in date_checks:
            ticker, entry_date, exit_date, hold_days = trade
            if entry_date and exit_date:
                actual_days = (exit_date - entry_date).days
                if abs(actual_days - hold_days) <= 1:  # Allow 1 day tolerance
                    print(f"✅ {ticker}: Dates consistent ({actual_days} days calculated, {hold_days} stored)")
                else:
                    print(f"❌ {ticker}: Date inconsistency ({actual_days} days calculated, {hold_days} stored)")

        # Check for market-like volatility patterns
        print("\nVOLATILITY PATTERN ANALYSIS:")
        cursor.execute('SELECT ticker, COUNT(*) as trade_count, AVG(final_return_pct) as avg_return, STDDEV(final_return_pct) as return_std FROM consensus_tracked GROUP BY ticker HAVING trade_count > 1 ORDER BY trade_count DESC LIMIT 10')
        volatility_data = cursor.fetchall()

        for row in volatility_data:
            ticker, count, avg_return, std_dev = row
            if std_dev and std_dev > 0.01:  # Some volatility
                print(f"✅ {ticker}: {count} trades, avg return {avg_return:.2f}%, volatility {std_dev:.4f} (realistic)")
            else:
                print(f"❌ {ticker}: {count} trades, avg return {avg_return:.2f}%, volatility {std_dev:.4f} (too consistent)")

        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    validate_ticker_realism()