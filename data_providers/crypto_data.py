# data_providers/crypto_data.py
#
# Placeholder data provider for crypto strategies.
# In a production system these functions would fetch data from APIs,
# databases, or on‑chain sources. For now they return mock data
# sufficient for unit‑testing and demonstration purposes.
#
import random
from typing import Dict, List


def get_spot_prices() -> Dict[str, float]:
    """Return a dictionary of current spot prices for a set of symbols."""
    # Mock data – in reality you would query an exchange API.
    return {
        "BTC": 30000.0,
        "ETH": 2000.0,
        "SOL": 25.0,
        "DOGE": 0.07,
    }


def get_iv_surface() -> Dict[str, float]:
    """Return implied‑volatility percentages for each symbol."""
    # Mock IV values – typically >80% indicates high option premium.
    return {
        "BTC": 85.0,
        "ETH": 78.0,
        "SOL": 92.0,
        "DOGE": 55.0,
    }


def get_defi_pools() -> Dict[str, Dict[str, float]]:
    """Return DeFi pool information: APY, price, and short‑term momentum."""
    return {
        "AAVE": {"apy": 18.5, "price": 70.0, "momentum": 1.2},
        "UNI": {"apy": 12.0, "price": 5.5, "momentum": 0.8},
        "SUSHI": {"apy": 22.0, "price": 0.9, "momentum": 1.5},
    }


def get_nft_data() -> Dict[str, Dict[str, float]]:
    """Return NFT collection floor price, volume, and momentum indicator."""
    return {
        "CryptoPunks": {"floor": 120000.0, "volume": 1500, "momentum": 1.8},
        "BoredApe": {"floor": 150000.0, "volume": 800, "momentum": 0.9},
    }


def get_sentiment_scores() -> Dict[str, float]:
    """Return a sentiment score for each symbol (positive = bullish)."""
    return {
        "BTC": 0.35,
        "ETH": -0.12,
        "SOL": 0.05,
        "DOGE": -0.30,
    }


def get_dex_price_spreads() -> Dict[str, Dict[str, float]]:
    """Return price quotes from multiple DEXs for each symbol."""
    return {
        "BTC": {"uniswap": 30010.0, "sushiswap": 29980.0, "pancake": 30050.0},
        "ETH": {"uniswap": 2005.0, "sushiswap": 1998.0, "pancake": 2010.0},
    }


def get_vol_series() -> Dict[str, float]:
    """Return annualized volatility for each asset (used by risk‑parity optimizer)."""
    return {
        "BTC": 0.70,
        "ETH": 0.85,
        "SOL": 1.10,
        "DOGE": 1.30,
    }

# Helper to assemble a full context dictionary for strategies.

def build_context() -> Dict:
    """Collect all data sources into a single context dict expected by strategies."""
    spot = get_spot_prices()
    return {
        "spot_price": spot,
        "iv_surface": get_iv_surface(),
        "defi_pools": get_defi_pools(),
        "nft_data": get_nft_data(),
        "sentiment_scores": get_sentiment_scores(),
        "dex_prices": get_dex_price_spreads(),
        "vol_series": get_vol_series(),
    }
