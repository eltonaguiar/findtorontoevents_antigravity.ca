"""
Macro Factors Data Collection
=============================
Collects macro-economic and crypto-specific indicators:
- BTC dominance & total market cap
- DeFi TVL
- Google Trends (crypto interest)
- On-chain metrics (hash rate, active addresses)
- Fear & Greed Index
"""

import pandas as pd
import numpy as np
import requests
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging
import json

from alpha_engine.config import (
    COINGECKO_BASE, CRYPTOCOMPARE_BASE, FEAR_GREED_URL,
    PARQUET_COMPRESSION
)
from alpha_engine.utils.storage import write_parquet, append_to_parquet

logger = logging.getLogger(__name__)


class MacroFactorCollector:
    """
    Collector for macro-level crypto indicators.
    """
    
    def __init__(self, data_dir: Path = Path("data/macro_factors")):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache for rate limiting
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 300  # 5 minutes
    
    def _get_cached(self, key: str) -> Optional[Dict]:
        """Get cached data if not expired."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.utcnow().timestamp() - timestamp < self._cache_ttl:
                return data
        return None
    
    def _set_cached(self, key: str, data: Dict):
        """Cache data with timestamp."""
        self._cache[key] = (data, datetime.utcnow().timestamp())
    
    def fetch_btc_dominance(self) -> Dict[str, float]:
        """
        Fetch BTC dominance and total market cap from CoinGecko.
        """
        cached = self._get_cached('btc_dominance')
        if cached:
            return cached
        
        try:
            url = f"{COINGECKO_BASE}/global"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            result = {
                'btc_dominance': data['data']['market_cap_percentage'].get('btc', 0),
                'eth_dominance': data['data']['market_cap_percentage'].get('eth', 0),
                'total_market_cap_usd': data['data']['total_market_cap'].get('usd', 0),
                'total_volume_24h_usd': data['data']['total_volume'].get('usd', 0),
                'market_cap_change_24h': data['data'].get('market_cap_change_percentage_24h_usd', 0),
            }
            
            self._set_cached('btc_dominance', result)
            return result
            
        except Exception as e:
            logger.error(f"Error fetching BTC dominance: {e}")
            return {}
    
    def fetch_defi_tvl(self) -> Dict[str, float]:
        """
        Fetch DeFi TVL data from CoinGecko.
        """
        cached = self._get_cached('defi_tvl')
        if cached:
            return cached
        
        try:
            url = f"{COINGECKO_BASE}/global/decentralized_finance_defi"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            result = {
                'defi_market_cap': data['data'].get('defi_market_cap', 0),
                'defi_to_eth_ratio': data['data'].get('defi_to_eth_ratio', 0),
                'trading_volume_24h': data['data'].get('trading_volume_24h', 0),
                'defi_dominance': data['data'].get('defi_dominance', 0),
                'top_coin_name': data['data'].get('top_coin_name', ''),
                'top_coin_defi_dominance': data['data'].get('top_coin_defi_dominance', 0),
            }
            
            self._set_cached('defi_tvl', result)
            return result
            
        except Exception as e:
            logger.error(f"Error fetching DeFi TVL: {e}")
            return {}
    
    def fetch_fear_greed(self) -> Dict[str, float]:
        """
        Fetch Fear & Greed Index.
        """
        cached = self._get_cached('fear_greed')
        if cached:
            return cached
        
        import time as _time
        for _attempt in range(3):
            try:
                response = requests.get(FEAR_GREED_URL, timeout=10)
                response.raise_for_status()
                data = response.json()

                result = {
                    'fear_greed_index': float(data['data'][0]['value']),
                    'fear_greed_classification': data['data'][0]['value_classification'],
                    'fear_greed_timestamp': data['data'][0]['timestamp'],
                }

                self._set_cached('fear_greed', result)
                return result

            except Exception as e:
                if _attempt < 2:
                    _time.sleep(2 * (_attempt + 1))
                    continue
                logger.error(f"Error fetching Fear & Greed after 3 attempts: {e}")
                return {}
    
    def fetch_onchain_metrics(self, symbol: str = "BTC") -> Dict[str, float]:
        """
        Fetch on-chain metrics from CryptoCompare.
        Note: Limited free tier, may need API key for full access.
        """
        cache_key = f'onchain_{symbol}'
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            # Active addresses (approximate via CryptoCompare)
            url = f"{CRYPTOCOMPARE_BASE}/blockchain/latest"
            params = {
                'fsym': symbol,
                'api_key': ''  # Add API key if available
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'Data' in data:
                    result = {
                        f'{symbol.lower()}_active_addresses': data['Data'].get('active_addresses', 0),
                        f'{symbol.lower()}_transaction_count': data['Data'].get('transaction_count', 0),
                        f'{symbol.lower()}_average_transaction_fee': data['Data'].get('average_transaction_fee', 0),
                    }
                    self._set_cached(cache_key, result)
                    return result
            
            # Fallback: return empty if API not available
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching on-chain metrics: {e}")
            return {}
    
    def fetch_google_trends(
        self,
        keywords: List[str] = None,
        timeframe: str = "now 1-H"
    ) -> Dict[str, float]:
        """
        Fetch Google Trends data for crypto keywords.
        Note: Requires pytrends library.
        """
        if keywords is None:
            keywords = ['bitcoin', 'ethereum', 'crypto', 'blockchain']
        
        cache_key = f'trends_{"_".join(keywords)}'
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            from pytrends.request import TrendReq
            
            pytrends = TrendReq(hl='en-US', tz=0)
            pytrends.build_payload(keywords, timeframe=timeframe, geo='')
            
            interest = pytrends.interest_over_time()
            
            if not interest.empty:
                latest = interest.iloc[-1]
                result = {
                    f'trends_{kw.replace(" ", "_")}': float(latest[kw])
                    for kw in keywords if kw in latest
                }
                result['trends_is_partial'] = bool(interest.iloc[-1].get('isPartial', False))
                
                self._set_cached(cache_key, result)
                return result
            
            return {}
            
        except ImportError:
            logger.warning("pytrends not installed, skipping Google Trends")
            return {}
        except Exception as e:
            logger.error(f"Error fetching Google Trends: {e}")
            return {}
    
    def fetch_implied_volatility(self) -> Dict[str, float]:
        """
        Fetch implied volatility data from Deribit or other sources.
        Placeholder - requires API integration.
        """
        # This would integrate with Deribit API for BTC/ETH IV
        # For now, return empty - implement when needed
        return {}
    
    def collect_all(self) -> pd.DataFrame:
        """
        Collect all macro factors and return as DataFrame row.
        """
        timestamp = datetime.utcnow()
        
        # Collect all metrics
        data = {'timestamp': timestamp}
        
        data.update(self.fetch_btc_dominance())
        data.update(self.fetch_defi_tvl())
        data.update(self.fetch_fear_greed())
        data.update(self.fetch_onchain_metrics('BTC'))
        data.update(self.fetch_google_trends())
        
        # Convert to DataFrame
        df = pd.DataFrame([data])
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def save_snapshot(self, df: Optional[pd.DataFrame] = None):
        """
        Save current macro factors snapshot to Parquet.
        """
        if df is None:
            df = self.collect_all()
        
        if df.empty:
            logger.warning("No macro data to save")
            return
        
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
        filepath = self.data_dir / f"{date_str}.parquet"
        
        append_to_parquet(df, filepath)
        logger.info(f"Saved macro factors snapshot: {filepath}")
    
    def load_history(
        self,
        lookback_days: int = 30
    ) -> pd.DataFrame:
        """
        Load historical macro factors.
        """
        from alpha_engine.utils.storage import read_parquet
        
        pattern = f"{self.data_dir}/*.parquet"
        df = read_parquet(pattern)
        
        if not df.empty and lookback_days:
            cutoff = datetime.utcnow() - timedelta(days=lookback_days)
            df = df[df.index >= cutoff]
        
        return df


def fetch_fred_data(
    series_id: str,
    api_key: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetch economic data from FRED (Federal Reserve Economic Data).
    Useful for risk-free rate, inflation, etc.
    """
    try:
        from fredapi import Fred
        
        if api_key is None:
            import os
            api_key = os.getenv('FRED_API_KEY')
        
        if not api_key:
            logger.warning("FRED API key not available")
            return pd.DataFrame()
        
        fred = Fred(api_key=api_key)
        series = fred.get_series(series_id)
        
        return pd.DataFrame({series_id: series})
        
    except ImportError:
        logger.warning("fredapi not installed, skipping FRED data")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error fetching FRED data: {e}")
        return pd.DataFrame()


def collect_macro_snapshot(
    output_dir: Path = Path("data/macro_factors")
) -> pd.DataFrame:
    """
    Convenience function to collect and save a macro snapshot.
    """
    collector = MacroFactorCollector(output_dir)
    df = collector.collect_all()
    collector.save_snapshot(df)
    return df
