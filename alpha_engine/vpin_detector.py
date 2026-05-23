import numpy as np
import pandas as pd
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class VPINDetector:
    """
    Volume-Synchronized Probability of Informed Trading (VPIN).
    Detects toxic order flow and impending liquidity crises.
    
    Ref: Easley, Lopez de Prado, and O'Hara (2012)
    "Flow Toxicity and Volatility in a High Frequency World"
    """
    
    def __init__(self, volume_bucket_size: int = 1000):
        # volume_bucket_size depends on the asset's average 24h volume.
        # Typically 1/50th of avg daily volume.
        self.volume_bucket_size = volume_bucket_size

    def compute_vpin(self, ohlcv_df: pd.DataFrame, n_buckets: int = 50) -> Optional[float]:
        """
        Compute the latest VPIN value.
        
        Args:
            ohlcv_df: DataFrame with ['Close', 'Volume']
            n_buckets: Number of volume buckets for the rolling average.
        
        Returns:
            VPIN value (0-1, where > 0.8 is considered toxic).
        """
        if ohlcv_df.empty or len(ohlcv_df) < 50:
            return None
            
        # 1. Approximate buy/sell volume using the "Bulk Volume Classification" (BVC)
        # BVC(t) = Volume(t) * Z((Close(t) - Close(t-1)) / sigma)
        # Simplified BVC: Buy = Vol * (Close - Low) / (High - Low)
        # Using a mid-price proxy if High/Low are missing, but crypto OHLCV usually has them.
        
        df = ohlcv_df.copy()
        if 'High' in df.columns and 'Low' in df.columns:
            # BVC using High/Low/Close
            # BuyVol = V * NormDist((C - L) / (H - L)) - no, standard BVC:
            # Fraction = (C - L) / (H - L); BuyValue = Fraction * Volume
            denominator = (df['High'] - df['Low'])
            denominator = denominator.replace(0, 1e-10) # Avoid div by zero
            buy_fraction = (df['Close'] - df['Low']) / denominator
            df['BuyVol'] = df['Volume'] * buy_fraction
            df['SellVol'] = df['Volume'] * (1.0 - buy_fraction)
        else:
            # Fallback to price change proxy
            df['PriceDelta'] = df['Close'].diff()
            df['BuyVol'] = np.where(df['PriceDelta'] > 0, df['Volume'], 0)
            df['SellVol'] = np.where(df['PriceDelta'] < 0, df['Volume'], 0)
            df['BuyVol'] = np.where(df['PriceDelta'] == 0, df['Volume'] * 0.5, df['BuyVol'])
            df['SellVol'] = np.where(df['PriceDelta'] == 0, df['Volume'] * 0.5, df['SellVol'])
            
        # 2. Time-order to Volume-time aggregation
        cumulative_vol = df['Volume'].cumsum()
        total_volume = cumulative_vol.iloc[-1]
        
        num_buckets = int(total_volume // self.volume_bucket_size)
        if num_buckets < n_buckets:
            logger.warning(f"Insufficient volume ({total_volume}) for {n_buckets} buckets (size {self.volume_bucket_size})")
            return 0.5 # Neutral
            
        # Group into buckets
        imbalances = []
        current_buy = 0
        current_sell = 0
        current_cum_vol = 0
        
        for _, row in df.iterrows():
            current_buy += row['BuyVol']
            current_sell += row['SellVol']
            current_cum_vol += row['Volume']
            
            if current_cum_vol >= self.volume_bucket_size:
                # Close this bucket
                # Imbalance = |Buy - Sell|
                imbalances.append(abs(current_buy - current_sell))
                current_buy = 0
                current_sell = 0
                current_cum_vol = 0
        
        if len(imbalances) < n_buckets:
            return 0.5
            
        # 3. Calculate VPIN
        # VPIN = Σ |Buy_i - Sell_i| / (n * Volume_Bucket_Size)
        latest_imbalances = imbalances[-n_buckets:]
        vpin = sum(latest_imbalances) / (n_buckets * self.volume_bucket_size)
        
        return float(vpin)

if __name__ == "__main__":
    # Test with dummy data
    np.random.seed(42)
    # Create 1000 bars of data
    prices = 100 + np.cumsum(np.random.normal(0, 0.5, 1000))
    vol = np.random.randint(100, 500, 1000)
    highs = prices + np.random.uniform(0, 0.2, 1000)
    lows = prices - np.random.uniform(0, 0.2, 1000)
    
    df = pd.DataFrame({
        'Close': prices,
        'High': highs,
        'Low': lows,
        'Volume': vol
    })
    
    detector = VPINDetector(volume_bucket_size=5000)
    vpin = detector.compute_vpin(df, n_buckets=20)
    
    print(f"\n📊 Order Flow Toxicity Analysis (VPIN):")
    print(f"  Current VPIN: {vpin:.4f}")
    if vpin > 0.8:
        print("  ⚠️ ALERT: High Toxicity detected. Liquidity hunt in progress.")
    elif vpin > 0.6:
        print("  ⚠️ WARNING: Informed trading rising.")
    else:
        print("  ✅ Market normal.")
