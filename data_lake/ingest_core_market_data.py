import os
import datetime
import yfinance as yf
import pandas as pd
import logging

# Configure logging
logging.basicConfig(
    filename='logs/data_ingestion.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

DATA_LAKE_DIR = 'data_lake/raw/market_data'

# Universe definitions based on Hedge-Fund Masterplan requirements
UNIVERSE = {
    'stocks': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JPM', 'JNJ', 'V'],
    'penny_stocks': ['PLTR', 'SOFI', 'RIVN', 'LCID', 'RIOT', 'MARA', 'MSTR', 'OPEN', 'DKNG', 'CVNA'], # Approximations for high retail interest / lower caps
    'etfs': ['SPY', 'QQQ', 'IWM', 'EFA', 'EEM', 'AGG', 'GLD', 'USO', 'VNQ', 'XLF'],
    'forex': ['EURUSD=X', 'JPY=X', 'GBPUSD=X', 'AUDUSD=X', 'USDCAD=X', 'CHF=X'],
    'crypto': ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD', 'ADA-USD', 'DOT-USD', 'MATIC-USD', 'AVAX-USD', 'LINK-USD'],
    'meme_coins': ['DOGE-USD', 'SHIB-USD', 'PEPE-USD'] # yfinance might have limited coverage, but we'll try top ones
}

def ingest_data(symbol, category, start_date='2020-01-01'):
    logging.info(f"Ingesting {symbol} for {category}...")
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, auto_adjust=True)
        
        if df.empty:
            logging.warning(f"No data returned for {symbol}.")
            return False
            
        # Basic data quality checks
        # 1. Schema Validation
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_cols):
            logging.error(f"Schema validation failed for {symbol}. Missing columns.")
            return False
            
        # 2. Check for stale data (e.g. no trades in the last 7 days)
        last_date = df.index[-1]
        # timezone aware vs naive handling
        last_date = pd.to_datetime(last_date).tz_localize(None)
        now = datetime.datetime.now()
        
        # some pairs might not trade on weekends (stocks/forex), give 5 day grace period
        if (now - last_date).days > 5:
            logging.warning(f"Stale data alert for {symbol}. Last update: {last_date}")
            # we will still save it but log the warning
            
        # Add metadata
        df['Symbol'] = symbol
        df['Category'] = category
        df['IngestionTimestamp'] = pd.Timestamp.now()
        
        # Save to data lake as parquet
        category_dir = os.path.join(DATA_LAKE_DIR, category)
        os.makedirs(category_dir, exist_ok=True)
        
        file_path = os.path.join(category_dir, f"{symbol.replace('=', '_')}.parquet")
        # index=True is default for to_parquet with pandas 1.1+ preserving DateTimeIndex usually
        df.to_parquet(file_path)
        logging.info(f"Successfully saved {len(df)} rows to {file_path}")
        return True

    except Exception as e:
        logging.error(f"Error ingesting {symbol}: {e}")
        return False

def main():
    logging.info("Starting Core Market Data Ingestion Pipeline...")
    success_count = 0
    total_count = 0
    
    for category, symbols in UNIVERSE.items():
        for sym in symbols:
            total_count += 1
            if ingest_data(sym, category):
                success_count += 1
                
    logging.info(f"Ingestion completed. {success_count}/{total_count} symbols successfully downloaded.")

if __name__ == "__main__":
    main()
