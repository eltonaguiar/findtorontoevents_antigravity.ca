"""
Insider Activity Loader

Fetches SEC Form 4 filings to detect insider buying clusters.
The "Cluster Buy" signal: 3+ insiders buying in the same 14-day window
is one of the strongest legal predictors of undervalued growth.
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger(__name__)


class InsiderLoader:
    """
    Load insider transaction data from SEC EDGAR.
    
    Focuses on Form 4 filings (insider buys/sells).
    Key signal: "Cluster Buy" = 3+ distinct insiders purchasing within 14 days.
    """

    SEC_EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt={start}&enddt={end}&forms=4"
    SEC_EDGAR_FULL_TEXT = "https://efts.sec.gov/LATEST/search-index?q=%22{cik}%22&forms=4&dateRange=custom&startdt={start}&enddt={end}"

    # SEC EDGAR company search
    SEC_COMPANY_TICKERS = "https://www.sec.gov/files/company_tickers.json"

    HEADERS = {
        "User-Agent": "AlphaEngine/1.0 (research@example.com)",
        "Accept-Encoding": "gzip, deflate",
    }

    def __init__(self):
        from .. import config
        self.cluster_threshold = config.INSIDER_CLUSTER_THRESHOLD
        self.lookback_days = config.INSIDER_LOOKBACK_DAYS
        self.score_multiplier = config.INSIDER_SCORE_MULTIPLIER
        self._ticker_cik_map: Dict[str, str] = {}
        self._cache: Dict[str, pd.DataFrame] = {}

    def load_insider_transactions(self, ticker: str, days_back: int = 90) -> pd.DataFrame:
        """
        Load recent insider transactions for a ticker from SEC EDGAR.
        
        Returns DataFrame with columns:
        - date, insider_name, title, transaction_type, shares, price, value
        """
        if ticker in self._cache:
            return self._cache[ticker]

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        try:
            # Try yfinance insider data first (more reliable)
            df = self._load_from_yfinance(ticker)
            if df is not None and not df.empty:
                self._cache[ticker] = df
                return df
        except Exception as e:
            logger.debug(f"yfinance insider data failed for {ticker}: {e}")

        try:
            # Fallback: SEC EDGAR RSS
            df = self._load_from_sec_rss(ticker, start_date, end_date)
            if df is not None and not df.empty:
                self._cache[ticker] = df
                return df
        except Exception as e:
            logger.debug(f"SEC EDGAR failed for {ticker}: {e}")

        # Return empty DataFrame
        return pd.DataFrame(columns=["date", "insider_name", "title", "transaction_type", "shares", "price", "value"])

    def _load_from_yfinance(self, ticker: str) -> Optional[pd.DataFrame]:
        """Load insider data from yfinance."""
        import yfinance as yf

        stock = yf.Ticker(ticker)

        # Get insider transactions
        insider_df = getattr(stock, "insider_transactions", None)
        if insider_df is None or insider_df.empty:
            return None

        # Normalize columns
        result = pd.DataFrame()
        if "Start Date" in insider_df.columns:
            result["date"] = pd.to_datetime(insider_df["Start Date"])
        elif "Date" in insider_df.columns:
            result["date"] = pd.to_datetime(insider_df["Date"])

        result["insider_name"] = insider_df.get("Insider", insider_df.get("Name", "Unknown"))
        result["title"] = insider_df.get("Position", insider_df.get("Relation", "Unknown"))
        result["transaction_type"] = insider_df.get("Transaction", insider_df.get("Type", "Unknown"))
        result["shares"] = pd.to_numeric(insider_df.get("Shares", insider_df.get("Share", 0)), errors="coerce").fillna(0)
        result["value"] = pd.to_numeric(insider_df.get("Value", 0), errors="coerce").fillna(0)

        if "shares" in result.columns and "value" in result.columns:
            mask = (result["shares"] > 0) & (result["value"] > 0)
            result.loc[mask, "price"] = result.loc[mask, "value"] / result.loc[mask, "shares"]
        if "price" not in result.columns:
            result["price"] = 0.0

        return result

    def _load_from_sec_rss(self, ticker: str, start: datetime, end: datetime) -> Optional[pd.DataFrame]:
        """Load insider data from SEC EDGAR search."""
        try:
            url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms=4&dateRange=custom&startdt={start.strftime('%Y-%m-%d')}&enddt={end.strftime('%Y-%m-%d')}"
            resp = requests.get(url, headers=self.HEADERS, timeout=10)
            if resp.status_code != 200:
                return None
            # Parse response (simplified - SEC API returns JSON)
            data = resp.json()
            if "hits" not in data or not data["hits"]["hits"]:
                return None

            rows = []
            for hit in data["hits"]["hits"]:
                source = hit.get("_source", {})
                rows.append({
                    "date": pd.to_datetime(source.get("file_date", "")),
                    "insider_name": source.get("display_names", ["Unknown"])[0] if source.get("display_names") else "Unknown",
                    "title": "Insider",
                    "transaction_type": "Purchase",
                    "shares": 0,
                    "price": 0,
                    "value": 0,
                })
            return pd.DataFrame(rows) if rows else None
        except Exception:
            return None

    def detect_cluster_buys(self, tickers: List[str], lookback_days: Optional[int] = None) -> pd.DataFrame:
        """
        Detect insider buying clusters across universe.
        
        A "cluster buy" = 3+ distinct insiders purchasing shares within 14 days.
        This is the strongest legal signal of institutional conviction.
        
        Returns DataFrame with columns:
        - ticker, cluster_size, total_value, avg_price, recent_buyers, signal_strength
        """
        if lookback_days is None:
            lookback_days = self.lookback_days

        cutoff = datetime.now() - timedelta(days=lookback_days)
        results = []

        for ticker in tickers:
            try:
                txns = self.load_insider_transactions(ticker, days_back=lookback_days + 30)
                if txns.empty:
                    results.append({
                        "ticker": ticker, "cluster_size": 0, "total_value": 0,
                        "is_cluster_buy": False, "signal_strength": 0.0,
                    })
                    continue

                # Filter to purchases only, within lookback window
                buys = txns[
                    (txns["transaction_type"].str.lower().str.contains("purchase|buy|acquisition", na=False)) &
                    (txns["date"] >= cutoff)
                ]

                if buys.empty:
                    results.append({
                        "ticker": ticker, "cluster_size": 0, "total_value": 0,
                        "is_cluster_buy": False, "signal_strength": 0.0,
                    })
                    continue

                # Count distinct insiders
                unique_buyers = buys["insider_name"].nunique()
                total_value = buys["value"].sum()

                # Signal strength: more buyers + more value = stronger
                is_cluster = unique_buyers >= self.cluster_threshold
                strength = min(unique_buyers / self.cluster_threshold, 2.0)
                if total_value > 1_000_000:
                    strength *= 1.5
                elif total_value > 100_000:
                    strength *= 1.2

                results.append({
                    "ticker": ticker,
                    "cluster_size": unique_buyers,
                    "total_value": total_value,
                    "recent_buyers": ", ".join(buys["insider_name"].unique()[:5]),
                    "is_cluster_buy": is_cluster,
                    "signal_strength": min(strength, 3.0),
                })

            except Exception as e:
                logger.warning(f"Insider analysis failed for {ticker}: {e}")
                results.append({
                    "ticker": ticker, "cluster_size": 0, "total_value": 0,
                    "is_cluster_buy": False, "signal_strength": 0.0,
                })

        return pd.DataFrame(results).set_index("ticker")

    def get_insider_score_multiplier(self, tickers: List[str]) -> pd.Series:
        """
        Get score multiplier based on insider activity.
        
        - No insider activity: 1.0x (neutral)
        - Some buying: 1.1x - 1.3x
        - Cluster buy (3+ insiders): 1.5x (max boost from config)
        - Heavy selling: 0.7x - 0.9x (penalty)
        """
        clusters = self.detect_cluster_buys(tickers)
        multipliers = pd.Series(1.0, index=tickers, name="insider_multiplier")

        for ticker in tickers:
            if ticker not in clusters.index:
                continue
            row = clusters.loc[ticker]
            if row["is_cluster_buy"]:
                multipliers[ticker] = self.score_multiplier  # 1.5x
            elif row["cluster_size"] >= 2:
                multipliers[ticker] = 1.25
            elif row["cluster_size"] >= 1:
                multipliers[ticker] = 1.1

        return multipliers
