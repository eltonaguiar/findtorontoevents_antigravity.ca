"""
Sentiment / News Data Loader

Provides sentiment signals from multiple sources:
1. News headlines via RSS feeds (free)
2. VADER sentiment scoring
3. Sentiment velocity (rate of change)
4. Social attention proxies via volume/price anomalies

This is the "Sentiment Velocity" module from the God-Mode spec.
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SentimentLoader:
    """
    Load and compute sentiment signals.
    
    Uses freely available data + NLP to create sentiment velocity signals.
    When premium APIs are available, plug them in via the `add_source` method.
    """

    # Financial news RSS feeds (free)
    RSS_FEEDS = {
        "yahoo_finance": "https://finance.yahoo.com/news/rssindex",
        "reuters_business": "http://feeds.reuters.com/reuters/businessNews",
        "cnbc": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
        "seeking_alpha": "https://seekingalpha.com/feed.xml",
        "marketwatch": "http://feeds.marketwatch.com/marketwatch/topstories/",
    }

    # Bullish/bearish keyword dictionaries for simple scoring
    BULLISH_KEYWORDS = [
        "upgrade", "beat", "outperform", "bullish", "surge", "rally", "breakout",
        "record high", "strong earnings", "raises guidance", "buy rating",
        "positive surprise", "accelerat", "exceeds expectations", "growth",
        "innovation", "expansion", "new contract", "dividend increase",
        "share buyback", "acquisition", "partnership", "breakthrough",
    ]

    BEARISH_KEYWORDS = [
        "downgrade", "miss", "underperform", "bearish", "crash", "plunge",
        "breakdown", "record low", "weak earnings", "lowers guidance", "sell rating",
        "negative surprise", "decelerat", "disappoints", "recession", "layoffs",
        "default", "fraud", "investigation", "lawsuit", "bankruptcy", "warning",
        "writedown", "impairment", "debt concern",
    ]

    def __init__(self):
        self._headline_cache: Dict[str, List[Dict]] = {}
        self._sentiment_history: Dict[str, pd.DataFrame] = {}

    def fetch_headlines(self, max_per_feed: int = 50) -> List[Dict]:
        """
        Fetch recent headlines from RSS feeds.
        
        Returns list of {'title': str, 'published': datetime, 'source': str, 'link': str}
        """
        try:
            import feedparser
        except ImportError:
            logger.warning("feedparser not installed; using empty headlines")
            return []

        all_headlines = []
        for source, url in self.RSS_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:max_per_feed]:
                    pub_date = datetime.now()
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    all_headlines.append({
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", ""),
                        "published": pub_date,
                        "source": source,
                        "link": entry.get("link", ""),
                    })
            except Exception as e:
                logger.warning(f"Failed to fetch RSS from {source}: {e}")

        logger.info(f"Fetched {len(all_headlines)} headlines from {len(self.RSS_FEEDS)} feeds")
        return all_headlines

    def score_headline(self, text: str) -> Dict[str, float]:
        """
        Score a headline for sentiment using multiple methods.
        
        Returns {'vader': float, 'keyword': float, 'composite': float}
        All scores in [-1, 1] range.
        """
        text_lower = text.lower()

        # Method 1: VADER sentiment
        vader_score = 0.0
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            analyzer = SentimentIntensityAnalyzer()
            scores = analyzer.polarity_scores(text)
            vader_score = scores["compound"]
        except ImportError:
            pass

        # Method 2: Keyword matching
        bull_count = sum(1 for kw in self.BULLISH_KEYWORDS if kw in text_lower)
        bear_count = sum(1 for kw in self.BEARISH_KEYWORDS if kw in text_lower)
        total = bull_count + bear_count
        keyword_score = (bull_count - bear_count) / max(total, 1)

        # Composite: weighted average
        composite = 0.6 * vader_score + 0.4 * keyword_score

        return {"vader": vader_score, "keyword": keyword_score, "composite": composite}

    def score_ticker_sentiment(self, ticker: str, headlines: Optional[List[Dict]] = None) -> Dict[str, float]:
        """
        Score sentiment for a specific ticker by filtering relevant headlines.
        
        Returns {'sentiment_score': float, 'sentiment_count': int, 'sentiment_velocity': float}
        """
        if headlines is None:
            headlines = self.fetch_headlines()

        # Filter headlines mentioning this ticker or company
        relevant = [h for h in headlines if self._is_relevant(ticker, h)]

        if not relevant:
            return {"sentiment_score": 0.0, "sentiment_count": 0, "sentiment_velocity": 0.0}

        scores = [self.score_headline(h["title"] + " " + h.get("summary", ""))["composite"] for h in relevant]
        avg_score = np.mean(scores)

        # Sentiment velocity: compare recent (24h) vs older sentiment
        now = datetime.now()
        recent = [s for s, h in zip(scores, relevant) if (now - h["published"]).total_seconds() < 86400]
        older = [s for s, h in zip(scores, relevant) if (now - h["published"]).total_seconds() >= 86400]

        velocity = 0.0
        if recent and older:
            velocity = np.mean(recent) - np.mean(older)
        elif recent:
            velocity = np.mean(recent)

        return {
            "sentiment_score": avg_score,
            "sentiment_count": len(relevant),
            "sentiment_velocity": velocity,
        }

    def compute_universe_sentiment(self, tickers: List[str]) -> pd.DataFrame:
        """
        Compute sentiment scores for entire universe.
        
        Returns DataFrame indexed by ticker with sentiment columns.
        """
        headlines = self.fetch_headlines()
        rows = []
        for ticker in tickers:
            scores = self.score_ticker_sentiment(ticker, headlines)
            scores["ticker"] = ticker
            rows.append(scores)
        return pd.DataFrame(rows).set_index("ticker")

    def compute_sentiment_from_price_volume(
        self,
        close: pd.DataFrame,
        volume: pd.DataFrame,
        window: int = 20,
    ) -> pd.DataFrame:
        """
        Proxy sentiment from price/volume behavior when news APIs are unavailable.
        
        Signals:
        - Unusual volume + positive returns = bullish accumulation
        - Unusual volume + negative returns = bearish distribution
        - Low volume + drift up = quiet confidence
        - Low volume + drift down = apathy/exhaustion
        
        Returns DataFrame of sentiment proxy scores [-1, 1].
        """
        returns = close.pct_change()
        vol_ratio = volume / volume.rolling(window).mean()

        # Accumulation/Distribution proxy
        ad_signal = returns.multiply(vol_ratio)
        ad_smooth = ad_signal.rolling(5).mean()

        # Normalize to [-1, 1]
        sentiment = ad_smooth.clip(-0.1, 0.1) * 10
        sentiment = sentiment.clip(-1, 1)

        return sentiment

    def _is_relevant(self, ticker: str, headline: Dict) -> bool:
        """Check if a headline is relevant to a specific ticker."""
        text = (headline.get("title", "") + " " + headline.get("summary", "")).upper()

        # Direct ticker mention
        if f" {ticker} " in f" {text} " or f"${ticker}" in text:
            return True

        # Company name matching (basic)
        company_names = {
            "AAPL": ["APPLE"], "MSFT": ["MICROSOFT"], "GOOG": ["GOOGLE", "ALPHABET"],
            "AMZN": ["AMAZON"], "NVDA": ["NVIDIA"], "META": ["META PLATFORMS", "FACEBOOK"],
            "TSLA": ["TESLA"], "JPM": ["JPMORGAN", "JP MORGAN"], "JNJ": ["JOHNSON"],
            "WMT": ["WALMART"], "PG": ["PROCTER"], "KO": ["COCA-COLA", "COCA COLA"],
            "DIS": ["DISNEY"], "NFLX": ["NETFLIX"], "BA": ["BOEING"],
            "V": ["VISA INC"], "MA": ["MASTERCARD"],
        }
        for name in company_names.get(ticker, []):
            if name in text:
                return True

        return False

    def get_market_fear_greed(self, macro_df: pd.DataFrame) -> pd.Series:
        """
        Simple Fear & Greed proxy from macro data.
        
        Components:
        - VIX level (fear)
        - Market momentum (greed)
        - Rate of change of VIX (fear acceleration)
        
        Returns Series [-100, 100] where -100 = extreme fear, 100 = extreme greed.
        """
        score = pd.Series(0.0, index=macro_df.index)

        if "VIX" in macro_df.columns:
            vix = macro_df["VIX"]
            vix_norm = (vix - 20) / 10  # Normalize: 20 = neutral
            score -= vix_norm * 30  # VIX contribution

        if "SPY" in macro_df.columns:
            spy = macro_df["SPY"]
            spy_ret_20d = spy.pct_change(20)
            score += spy_ret_20d * 500  # Momentum contribution

        return score.clip(-100, 100)
