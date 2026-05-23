import os
import glob
import pandas as pd
import numpy as np
import logging
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    filename='../data_lake/logs/feature_builder.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

DATA_LAKE_DIR = '../data_lake/raw/market_data'
FEATURE_STORE_DIR = '../data_lake/feature_store'

def compute_garch_proxy(returns, window=30):
    """
    Compute a simple proxy for GARCH(1,1) volatility using EMA of squared returns.
    Real GARCH requires arch package, but EMA(Returns^2) is a standard fast approximation.
    """
    sq_returns = returns ** 2
    var_proxy = sq_returns.ewm(span=window, min_periods=window//2).mean()
    vol_proxy = np.sqrt(var_proxy) * np.sqrt(252)  # Annualized
    return vol_proxy

def compute_multi_horizon_momentum(df):
    """
    Computes 1d, 3d, 7d, 30d momentum with exponential decay.
    """
    df['Ret_1d'] = df['Close'].pct_change(1)
    df['Ret_3d'] = df['Close'].pct_change(3)
    df['Ret_7d'] = df['Close'].pct_change(7)
    df['Ret_30d'] = df['Close'].pct_change(30)
    
    # Exponential decay weights for momentum
    # weights: w1, w3, w7, w30
    w = np.array([1.0, 0.85, 0.85**2, 0.85**3])
    w = w / w.sum()
    
    # Composite Momentum using weighted returns
    df['Composite_Momentum'] = (
        df['Ret_1d'] * w[0] + 
        df['Ret_3d'] * w[1] + 
        df['Ret_7d'] * w[2] + 
        df['Ret_30d'] * w[3]
    )
    
    return df

def process_asset(file_path):
    sym = os.path.basename(file_path).replace('.parquet', '')
    try:
        df = pd.read_parquet(file_path)
        if len(df) < 30:
            return None
        
        df = df.sort_index()
        
        # Momentum Features
        df = compute_multi_horizon_momentum(df)
        
        # Volatility Feature
        df['Vol_GARCH_Proxy'] = compute_garch_proxy(df['Ret_1d'], window=30)
        
        # Target sizing: 0.5% risk per trade.
        # Position Size = Risk Target / Volatility 
        # (Clip to avoid div by zero or infinite scaling)
        df['Target_Weight'] = 0.005 / df['Vol_GARCH_Proxy'].replace(0, np.nan)
        df['Target_Weight'] = df['Target_Weight'].clip(upper=0.2) # Max 20% weight
        
        # Clean up
        df = df.dropna(subset=['Composite_Momentum', 'Vol_GARCH_Proxy'])
        
        return sym, df

    except Exception as e:
        logging.error(f"Error processing {sym}: {e}")
        return None

def main():
    os.makedirs(FEATURE_STORE_DIR, exist_ok=True)
    os.makedirs(os.path.join(FEATURE_STORE_DIR, 'core_features'), exist_ok=True)
    
    logging.info("Starting Feature Store Materialization...")
    processed = 0
    
    for root, dirs, files in os.walk(DATA_LAKE_DIR):
        for f in files:
            if f.endswith('.parquet'):
                file_path = os.path.join(root, f)
                result = process_asset(file_path)
                if result:
                    sym, df = result
                    out_path = os.path.join(FEATURE_STORE_DIR, 'core_features', f"{sym}_features.parquet")
                    df.to_parquet(out_path)
                    processed += 1
                    
    logging.info(f"Successfully materialized features for {processed} assets.")
    print(f"Feature Store materialized with {processed} assets.")

if __name__ == "__main__":
    main()
