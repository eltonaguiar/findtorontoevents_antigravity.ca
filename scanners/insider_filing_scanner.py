import os
import requests
import pandas as pd
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    filename='../data_lake/logs/insider_scanner.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

def fetch_recent_insider_buys():
    logging.info("Fetching recent insider cluster buys via OpenInsider...")
    try:
        url = "http://openinsider.com/latest-cluster-buys"
        
        # Add a User-Agent to avoid being blocked
        import urllib.request
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req).read()
        
        dfs = pd.read_html(html)
        if len(dfs) < 12:
            logging.error("OpenInsider page format changed, could not find data table.")
            return None
            
        df = dfs[11] # The main data table is usually at index 11
        
        if df.empty or 'Ticker' not in df.columns:
            logging.warning("No insider data returned or table empty.")
            return None
            
        # Clean up column names which might contain non-breaking spaces
        df.columns = [c.replace('\xa0', ' ') for c in df.columns]
        
        # Filter for recent buys (last 72 hours)
        cutoff_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        df['Trade Date'] = pd.to_datetime(df['Trade Date'], errors='coerce').dt.strftime('%Y-%m-%d')
        df = df[df['Trade Date'] >= cutoff_date]
        
        if df.empty:
            logging.info("No significant recent insider buys found in the last 3 days.")
            return None
            
        # Group by Ticker to find aggregate buys
        df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce')
        agg_buys = df.groupby('Ticker')['Qty'].sum().reset_index()
        
        # Filter for significant buys (e.g., > 10,000 shares)
        sig_buys = agg_buys[agg_buys['Qty'] > 10000]
        
        if sig_buys.empty:
            logging.info("No insider buys met the volume threshold.")
            return None
            
        # Format the output
        signals = []
        for _, row in sig_buys.iterrows():
            sym = row['Ticker']
            vol = row['Qty']
            signals.append({
                'Symbol': sym,
                'Signal': 'INSIDER_BUY',
                'Volume': vol,
                'Source': 'OpenInsider',
                'Date': datetime.now().strftime('%Y-%m-%d')
            })
            
        return signals

    except Exception as e:
        logging.error(f"Error fetching insider data: {e}")
        return None

def main():
    signals = fetch_recent_insider_buys()
    if signals:
        logging.info(f"Generated {len(signals)} Insider Buy Signals.")
        df_signals = pd.DataFrame(signals)
        print("====== INSIDER BUY DETECTIONS ======")
        print(df_signals.to_string(index=False))
        
        # Save to feature store
        out_dir = '../data_lake/feature_store/signals'
        os.makedirs(out_dir, exist_ok=True)
        today_str = datetime.now().strftime('%Y%m%d')
        df_signals.to_json(os.path.join(out_dir, f'insider_buys_{today_str}.json'), orient='records', indent=2)
        
        # Inject into Alpha Engine Consensus Hub
        import subprocess
        try:
            inj_path = os.path.join(os.path.dirname(__file__), 'sentiment_picks_injector.py')
            subprocess.run(["python", inj_path], check=True)
        except Exception as e:
            logging.error(f"Failed to run sentiment injector: {e}")
            
    else:
        print("No significant insider buys detected today.")

if __name__ == "__main__":
    main()
