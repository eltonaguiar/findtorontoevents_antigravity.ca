"""Abstract base class for all paper trading strategies."""
from abc import ABC, abstractmethod
from typing import List
from paper_trading.models import NormalizedPick
import logging

logger = logging.getLogger("paper_trading")


class BaseStrategy(ABC):
    name: str = "unnamed"
    display_name: str = "Unnamed Strategy"
    source: str = "Multi-Source"
    category: str = "crypto"
    portfolio_type: str = "technical"
    symbols: List[str] = []

    def fetch_klines(self, symbol: str, interval: str = "1h", limit: int = 250) -> list:
        """Fetch klines via multi-source (Binance → CryptoCompare → CoinGecko).

        Returns Binance-format klines: [ts_ms, O, H, L, C, V, ...]
        Cached in-memory so multiple strategies sharing symbols don't re-fetch.
        """
        from paper_trading.multi_source import fetch_klines
        return fetch_klines(symbol, interval=interval, limit=limit)

    @abstractmethod
    def fetch_data(self) -> dict:
        """Fetch raw data from API. Returns raw payload for audit trail."""
        ...

    @abstractmethod
    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        """Analyze data and return list of normalized picks."""
        ...

    def run(self) -> List[NormalizedPick]:
        """Execute strategy: fetch + generate."""
        try:
            logger.info(f"Running strategy: {self.display_name}")
            data = self.fetch_data()
            picks = self.generate_picks(data)
            logger.info(f"  -> {len(picks)} picks from {self.display_name}")
            return picks
        except Exception as e:
            logger.error(f"Strategy {self.name} failed: {e}")
            return []
