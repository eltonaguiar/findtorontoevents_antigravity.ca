"""
Example Usage: Unified Data Access Layer
=========================================

This script demonstrates how to use the DataManager to fetch various types
of data for research purposes. All researchers can use this unified interface.

Usage:
    python -m researchers.example_data_usage

Or import in your researcher:
    from researchers.base import Researcher
    # DataManager is automatically available as self.data_manager
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from researchers.data_access import DataManager, Exchange, OnChainMetric, SentimentSource, DataFrequency

def main():
    """Demonstrate all data access capabilities."""
    
    # Initialize DataManager
    # Cache will be stored in ml_crypto_predictor/data/
    dm = DataManager(
        cache_ttl_hours=24,  # Cache data for 24 hours
        rate_limit_delay=0.2,  # Be gentle on APIs
        log_level="INFO"
    )

    # Define time range: last 30 days
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=30)

    print("=" * 70)
    print("UNIFIED DATA ACCESS LAYER EXAMPLES")
    print("=" * 70)

    # ============================================================================
    # 1. PRICE DATA (Multiple Exchanges)
    # ============================================================================
    print("\n1. PRICE DATA")
    print("-" * 70)
    
    # Fetch BTC/USDT 1-hour candles from Binance
    btc_price = dm.get_price_data(
        symbol="BTCUSDT",
        exchange=Exchange.BINANCE,
        timeframe=DataFrequency.HOUR_1,
        start=start_date,
        end=end_date,
        include_indicators=True  # Add SMA, EMA, RSI, MACD, Bollinger Bands
    )
    print(f"[OK] Fetched {len(btc_price)} rows of BTC 1h price data from Binance")
    print(f"  Columns: {list(btc_price.columns)}")
    print(f"  Date range: {btc_price.index[0]} to {btc_price.index[-1]}")
    print(f"\nSample data:")
    print(btc_price.head())

    # Fetch ETH from Coinbase (different exchange)
    eth_price = dm.get_price_data(
        symbol="ETHUSDT",
        exchange=Exchange.COINBASE,
        timeframe=DataFrequency.HOUR_1,
        start=start_date,
        end=end_date
    )
    print(f"\n[OK] Fetched {len(eth_price)} rows of ETH 1h price data from Coinbase")

    # Fetch 4-hour data
    btc_4h = dm.get_price_data(
        symbol="BTCUSDT",
        exchange=Exchange.BINANCE,
        timeframe=DataFrequency.HOUR_4,
        start=start_date,
        end=end_date
    )
    print(f"[OK] Fetched {len(btc_4h)} rows of BTC 4h data")

    # ============================================================================
    # 2. ON-CHAIN METRICS (Bitcoin/Ethereum)
    # ============================================================================
    print("\n\n2. ON-CHAIN METRICS")
    print("-" * 70)
    
    # SOPR (Spent Output Profit Ratio)
    sopr = dm.get_onchain_metrics(
        coin="BTC",
        metric=OnChainMetric.SOPR,
        start=start_date,
        end=end_date,
        frequency=DataFrequency.DAY_1
    )
    print(f"[OK] Fetched {len(sopr)} rows of BTC SOPR")
    print(f"  Columns: {list(sopr.columns)}")
    print(f"\nSample:")
    print(sopr.head())

    # MVRV (Market Value to Realized Value)
    mvrv = dm.get_onchain_metrics(
        coin="BTC",
        metric=OnChainMetric.MVRV,
        start=start_date,
        end=end_date,
        frequency=DataFrequency.DAY_1
    )
    print(f"\n[OK] Fetched {len(mvrv)} rows of BTC MVRV")

    # NUPL (Net Unrealized Profit/Loss)
    nupl = dm.get_onchain_metrics(
        coin="BTC",
        metric=OnChainMetric.NUPL,
        start=start_date,
        end=end_date
    )
    print(f"\n[OK] Fetched {len(nupl)} rows of BTC NUPL")

    # Exchange flows
    inflow = dm.get_onchain_metrics(
        coin="BTC",
        metric=OnChainMetric.EXCHANGE_INFLOW,
        start=start_date,
        end=end_date
    )
    print(f"\n[OK] Fetched {len(inflow)} rows of BTC Exchange Inflow")

    # ETH on-chain data
    eth_sopr = dm.get_onchain_metrics(
        coin="ETH",
        metric=OnChainMetric.SOPR,
        start=start_date,
        end=end_date
    )
    print(f"\n[OK] Fetched {len(eth_sopr)} rows of ETH SOPR")

    # ============================================================================
    # 3. SENTIMENT DATA
    # ============================================================================
    print("\n\n3. SENTIMENT DATA")
    print("-" * 70)
    
    # News sentiment (requires NEWSAPI_KEY environment variable)
    # If not set, will use simulated data
    news_sentiment = dm.get_sentiment_data(
        coin="BTC",
        source=SentimentSource.NEWS,
        start=start_date,
        end=end_date,
        frequency=DataFrequency.HOUR_1
    )
    print(f"[OK] Fetched {len(news_sentiment)} rows of BTC news sentiment")
    print(f"  Columns: {list(news_sentiment.columns)}")
    print(f"\nSample:")
    print(news_sentiment.head())

    # Twitter sentiment (simulated - requires paid API)
    twitter_sentiment = dm.get_sentiment_data(
        coin="BTC",
        source=SentimentSource.TWITTER,
        start=start_date,
        end=end_date
    )
    print(f"\n[OK] Fetched {len(twitter_sentiment)} rows of BTC Twitter sentiment")

    # Reddit sentiment
    reddit_sentiment = dm.get_sentiment_data(
        coin="BTC",
        source=SentimentSource.REDDIT,
        start=start_date,
        end=end_date
    )
    print(f"\n[OK] Fetched {len(reddit_sentiment)} rows of BTC Reddit sentiment")

    # Options flow (simulated - requires paid API)
    options_flow = dm.get_sentiment_data(
        coin="BTC",
        source=SentimentSource.OPTIONS_FLOW,
        start=start_date,
        end=end_date
    )
    print(f"\n[OK] Fetched {len(options_flow)} rows of BTC options flow")

    # ============================================================================
    # 4. ALTERNATIVE DATA
    # ============================================================================
    print("\n\n4. ALTERNATIVE DATA")
    print("-" * 70)
    
    # Google Trends (requires pytrends, otherwise simulated)
    trends = dm.get_google_trends(
        keyword="Bitcoin",
        start=start_date,
        end=end_date,
        frequency=DataFrequency.DAY_1
    )
    print(f"✓ Fetched {len(trends)} rows of Google Trends for 'Bitcoin'")
    print(f"\nSample:")
    print(trends.head())

    # GitHub activity (for Bitcoin repo)
    github = dm.get_github_activity(
        repo="bitcoin/bitcoin",
        start=start_date,
        end=end_date,
        frequency=DataFrequency.DAY_1
    )
    print(f"\n✓ Fetched {len(github)} rows of GitHub activity for bitcoin/bitcoin")
    print(f"\nSample:")
    print(github.head())

    # ============================================================================
    # 5. COMBINING MULTIPLE DATA SOURCES
    # ============================================================================
    print("\n\n5. COMBINING MULTIPLE DATA SOURCES")
    print("-" * 70)
    
    # Build a comprehensive dataset for BTC
    print("Merging price + on-chain + sentiment data...")
    
    # Start with price data
    combined = btc_price.copy()
    
    # Add on-chain metrics (they have different frequencies, will be resampled)
    combined["sopr"] = sopr["value"].reindex(combined.index, method="ffill")
    combined["mvrv"] = mvrv["value"].reindex(combined.index, method="ffill")
    combined["nupl"] = nupl["value"].reindex(combined.index, method="ffill")
    combined["exchange_inflow"] = inflow["value"].reindex(combined.index, method="ffill")
    
    # Add sentiment
    combined["news_sentiment"] = news_sentiment["sentiment_score"].reindex(combined.index, method="ffill")
    combined["twitter_sentiment"] = twitter_sentiment["sentiment_score"].reindex(combined.index, method="ffill")
    combined["reddit_sentiment"] = reddit_sentiment["sentiment_score"].reindex(combined.index, method="ffill")
    
    # Add alternative data
    combined["google_trends"] = trends["trend_score"].reindex(combined.index, method="ffill")
    combined["github_commits"] = github["commits"].reindex(combined.index, method="ffill")
    
    print(f"✓ Combined dataset shape: {combined.shape}")
    print(f"  Features: {list(combined.columns)}")
    print(f"\nSample combined data:")
    print(combined.head())
    
    # Check for missing values
    missing_pct = combined.isna().sum() / len(combined) * 100
    print(f"\nMissing values (%):")
    for col, pct in missing_pct.items():
        if pct > 0:
            print(f"  {col}: {pct:.1f}%")

    # ============================================================================
    # 6. CACHE MANAGEMENT
    # ============================================================================
    print("\n\n6. CACHE MANAGEMENT")
    print("-" * 70)
    
    # Get cache info
    cache_info = dm.get_data_info()
    print("Cache contents:")
    for cache_type, info in cache_info.items():
        print(f"  {cache_type}: {info['files']} files, {info['size_mb']:.2f} MB")
    
    # Clear specific cache
    # dm.clear_data_cache("sentiment")  # Uncomment to clear sentiment cache
    
    # Clear all cache
    # dm.clear_data_cache()  # Uncomment to clear everything

    # ============================================================================
    # 7. DATA QUALITY CHECKS
    # ============================================================================
    print("\n\n7. DATA QUALITY CHECKS")
    print("-" * 70)
    
    # The DataManager automatically validates data during fetch:
    # - Checks for NaN values and forward-fills
    # - Detects duplicate timestamps
    # - Identifies gaps in time series
    # - Flags outliers using IQR method
    # - Validates OHLC relationships
    # - Prevents data leakage (forward-fill limited to 3 periods)
    
    print("✓ All fetched data has been automatically validated")
    print("✓ Gaps filled with forward-fill (max 3 periods)")
    print("✓ Outliers capped using IQR method")
    print("✓ OHLC relationships validated")
    
    # ============================================================================
    # 8. SURVIVORSHIP BIAS WARNING
    # ============================================================================
    print("\n\n8. IMPORTANT NOTES")
    print("-" * 70)
    print("• Survivorship bias: This data layer does NOT include delisted coins.")
    print("  For historical research, you need a complete universe dataset.")
    print("• Corporate actions: Price data is NOT adjusted for splits/forks.")
    print("  You may need to manually adjust for major events.")
    print("• Data sources:")
    print("  - Price: Binance, Coinbase Pro, Kraken (free public APIs)")
    print("  - On-chain: CoinMetrics community API (free, rate-limited)")
    print("  - Sentiment: NewsAPI (free tier: 100 req/day), simulated for others")
    print("  - Alternative: pytrends (free), GitHub API (free with token)")
    print("• Rate limiting: Built-in delays to avoid API bans")
    print("• Caching: All data cached locally to reduce API calls")

    print("\n" + "=" * 70)
    print("EXAMPLE COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Set environment variables for real API access:")
    print("     - NEWSAPI_KEY (NewsAPI)")
    print("     - TWITTER_BEARER_TOKEN (Twitter X)")
    print("     - REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET (Reddit)")
    print("     - GITHUB_TOKEN (GitHub higher rate limits)")
    print("  2. Explore the data in your researcher implementations")
    print("  3. Use self.get_price_data() in your Researcher subclass")
    print("  4. See README.md for full documentation")

if __name__ == "__main__":
    main()