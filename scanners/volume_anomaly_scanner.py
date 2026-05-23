import os
import glob
import pandas as pd
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    filename='../data_lake/logs/volume_scanner.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

DATA_LAKE_DIR = '../data_lake/raw/market_data'
ASSET_CLASSES = ['penny_stocks', 'meme_coins', 'stocks', 'crypto']

def detect_volume_anomalies(file_path):
    sym = os.path.basename(file_path).replace('.parquet', '')
    try:
        df = pd.read_parquet(file_path)
        
        # Ensure we have enough data (e.g. at least 30 days)
        if len(df) < 30:
            return None
            
        # Sort by index (Date) just in case
        df = df.sort_index()
        
        # Calculate 30-day rolling average volume
        df['Vol_30d_MA'] = df['Volume'].rolling(window=30).mean()
        
        # Calculate daily return
        df['Return'] = df['Close'].pct_change()
        
        # Get the latest row
        latest = df.iloc[-1]
        
        # Check conditions: 5x volume spike AND 20% price move
        vol_spike = latest['Vol_30d_MA'] > 0 and latest['Volume'] > (5 * latest['Vol_30d_MA'])
        price_move = abs(latest['Return']) > 0.20
        
        if vol_spike and price_move:
            direction = "BULLISH" if latest['Return'] > 0 else "BEARISH"
            
            # Simulated sentiment check based on short term vs long term volume
            sentiment_score = 0.5
            if latest['Volume'] > 0:
                short_vol = df['Volume'].rolling(window=3).mean().iloc[-1]
                if short_vol > latest['Vol_30d_MA']:
                    sentiment_score = 0.8 if direction == "BULLISH" else 0.2
                else:
                    sentiment_score = 0.6 if direction == "BULLISH" else 0.4
                    
            signal = {
                'Symbol': sym,
                'Date': df.index[-1].strftime('%Y-%m-%d'),
                'Close': latest['Close'],
                'Return_Pct': round(latest['Return'] * 100, 2),
                'Volume': latest['Volume'],
                'Vol_MA': latest['Vol_30d_MA'],
                'Vol_Multiple': round(latest['Volume'] / latest['Vol_30d_MA'], 2),
                'Direction': direction,
                'Sentiment_Score': sentiment_score
            }
            return signal
            
        return None
        
    except Exception as e:
        logging.error(f"Error processing {sym}: {e}")
        return None

def main():
    logging.info("Starting Volume Anomaly Scanner for Penny & Meme assets...")
    signals = []
    
    for category in ASSET_CLASSES:
        cat_dir = os.path.join(DATA_LAKE_DIR, category)
        if not os.path.exists(cat_dir):
            continue
            
        files = glob.glob(os.path.join(cat_dir, '*.parquet'))
        for f in files:
            res = detect_volume_anomalies(f)
            if res:
                res['Category'] = category
                signals.append(res)
                
    if signals:
        logging.info(f"Generated {len(signals)} Volume Anomaly Signals.")
        df_signals = pd.DataFrame(signals)
        print("====== VOLUME ANOMALY DETECTIONS ======")
        print(df_signals.to_string(index=False))
        
        # Save to feature store dropping
        out_dir = '../data_lake/feature_store/signals'
        os.makedirs(out_dir, exist_ok=True)
        today_str = datetime.now().strftime('%Y%m%d')
        df_signals.to_json(os.path.join(out_dir, f'volume_anomalies_{today_str}.json'), orient='records', indent=2)
        
        # Inject into Alpha Engine Consensus Hub
        import subprocess
        try:
            inj_path = os.path.join(os.path.dirname(__file__), 'sentiment_picks_injector.py')
            subprocess.run(["python", inj_path], check=True)
        except Exception as e:
            logging.error(f"Failed to run sentiment injector: {e}")
            
    else:
        logging.info("No volume anomalies detected today.")
        print("No volume anomalies detected today.")

if __name__ == "__main__":
    main()
