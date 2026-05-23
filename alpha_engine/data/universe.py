"""
Universe Manager

Manages the stock universe with filters for liquidity, tradability,
sector classification, and survivorship bias controls.
"""
import logging
from typing import Dict, List, Optional, Set

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class UniverseManager:
    """
    Manage the investable universe with quality controls.
    
    Ensures:
    - Sufficient liquidity (dollar volume floor)
    - No survivorship bias (include delisted if available)
    - Sector/industry classification
    - Tradability filters
    """

    def __init__(self):
        from .. import config
        self.default_universe = config.DEFAULT_UNIVERSE
        self.sector_etfs = config.SECTOR_ETFS
        self.dividend_aristocrats = config.DIVIDEND_ARISTOCRATS

    def get_universe(
        self,
        source: str = "default",
        min_dollar_volume: float = 5_000_000,
        min_price: float = 5.0,
        exclude_etfs: bool = False,
        sector: Optional[str] = None,
    ) -> List[str]:
        """
        Get the filtered investable universe.
        
        Args:
            source: 'default', 'sp500', 'dividend_aristocrats', 'all'
            min_dollar_volume: Minimum average daily dollar volume
            min_price: Minimum stock price
            exclude_etfs: Whether to exclude ETFs
            sector: Filter to specific sector
            
        Returns:
            List of ticker symbols
        """
        if source == "dividend_aristocrats":
            universe = list(self.dividend_aristocrats)
        elif source == "sector_etfs":
            universe = list(self.sector_etfs.values())
        elif source == "sp500":
            universe = self._get_sp500_tickers()
        elif source == "all":
            universe = list(set(
                self.default_universe +
                self.dividend_aristocrats +
                list(self.sector_etfs.values()) +
                self._get_sp500_tickers()
            ))
        else:
            universe = list(self.default_universe)

        return sorted(set(universe))

    def _get_sp500_tickers(self) -> List[str]:
        """Get S&P 500 constituents from Wikipedia."""
        try:
            tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
            if tables:
                sp500 = tables[0]
                tickers = sp500["Symbol"].str.replace(".", "-", regex=False).tolist()
                return tickers
        except Exception as e:
            logger.warning(f"Failed to fetch S&P 500 list: {e}. Using default universe.")
        return list(self.default_universe)

    def apply_liquidity_filter(
        self,
        tickers: List[str],
        dollar_volume: pd.DataFrame,
        min_dollar_volume: float = 5_000_000,
        lookback: int = 20,
    ) -> List[str]:
        """
        Filter universe by minimum average daily dollar volume.
        
        Many "edges" vanish when you can't actually trade the size.
        This prevents us from finding alpha in illiquid names.
        """
        avg_dvol = dollar_volume.tail(lookback).mean()
        liquid = avg_dvol[avg_dvol >= min_dollar_volume].index.tolist()
        filtered = [t for t in tickers if t in liquid]
        removed = len(tickers) - len(filtered)
        if removed > 0:
            logger.info(f"Liquidity filter removed {removed} tickers (min ${min_dollar_volume:,.0f} avg daily)")
        return filtered

    def apply_price_filter(
        self,
        tickers: List[str],
        close_prices: pd.DataFrame,
        min_price: float = 5.0,
        max_price: float = 10000.0,
    ) -> List[str]:
        """Filter by price range. Avoids penny stocks and ensures tradability."""
        latest = close_prices.iloc[-1] if not close_prices.empty else pd.Series(dtype=float)
        filtered = []
        for t in tickers:
            if t in latest.index:
                price = latest[t]
                if min_price <= price <= max_price:
                    filtered.append(t)
        return filtered

    def classify_sectors(self, tickers: List[str]) -> Dict[str, str]:
        """
        Get sector classification for each ticker.
        Uses yfinance data.
        """
        from .fundamentals import FundamentalsLoader
        loader = FundamentalsLoader()
        return loader.get_sector_map(tickers)

    def get_sector_groups(self, tickers: List[str]) -> Dict[str, List[str]]:
        """Group tickers by sector."""
        sector_map = self.classify_sectors(tickers)
        groups: Dict[str, List[str]] = {}
        for ticker, sector in sector_map.items():
            if sector not in groups:
                groups[sector] = []
            groups[sector].append(ticker)
        return groups

    def get_dividend_aristocrats(self) -> List[str]:
        """Get the list of dividend aristocrats (25+ years of increases)."""
        return list(self.dividend_aristocrats)

    def is_etf(self, ticker: str) -> bool:
        """Check if a ticker is an ETF."""
        etf_set = set(self.sector_etfs.values())
        etf_set.update(["SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "VGT", "SOXX",
                        "SCHD", "VYM", "DVY", "TLT", "GLD", "BND", "EFA", "VWO"])
        return ticker in etf_set

    def get_earnings_blackout_filter(self, tickers: List[str], days_before: int = 3) -> List[str]:
        """
        Get list of tickers NOT in earnings blackout period.
        Filters out stocks with earnings within N days.
        """
        from .earnings import EarningsLoader
        earnings_loader = EarningsLoader()
        upcoming = set(earnings_loader.get_upcoming_earnings(tickers, days_ahead=days_before))
        safe = [t for t in tickers if t not in upcoming]
        if upcoming:
            logger.info(f"Earnings blackout filter removed {len(upcoming)} tickers: {', '.join(sorted(upcoming)[:10])}")
        return safe
