# PENNY STOCKS & MEME COINS — Strategy Audit
**Date:** 2026-05-16 19:55 EST  
**Author:** Buffy (Codebuff)  
**Scope:** Gap analysis — these asset classes are NOT tracked

---

## 1. Current Status: COMPLETELY UNTRACKED

| Metric | Penny Stocks | Meme Coins |
|--------|-------------|------------|
| Closed picks | 0 | 0 |
| Active picks | 0 | 0 |
| Backtests | 0 | 0 |
| Strategy code | None | None |
| Asset class in config | Not defined | Not defined |
| Scanner support | No | No |

**Verdict:** ❌ These asset classes don't exist in the system. No data, no strategies, no tracking.

---

## 2. Why These Matter

### Penny Stocks
- Higher vol = potentially higher PnL per winning trade
- Less institutional competition (most hedge funds can't trade sub-$5 stocks)
- Retail-driven inefficiencies are larger
- Success stories: Traders like Tim Sykes built careers on penny stock patterns

### Meme Coins
- The highest-vol crypto subcategory
- Social sentiment drives 90% of price action (predictable if monitored)
- PEPE, WIF, BONK, DOGE, SHIB have produced 100x+ returns
- Already in our price data (many are on Binance) but not in strategy targeting

---

## 3. What We Need to Build

### Penny Stocks Infrastructure:
- ❌ Symbol universe (OTC markets, NASDAQ sub-$5)
- ❌ Price data feed (Yahoo Finance covers OTC but with delays)
- ❌ Volume filter (must trade >100K shares/day to avoid liquidity traps)
- ❌ News catalyst scraper (pump-and-dump patterns often preceded by promotional emails)
- ❌ Float data (low-float stocks <10M shares are the most explosive)

### Meme Coins Infrastructure:
- ❌ Asset class definition in `config.py`
- ❌ Strategy targeting (can reuse `ml_enhanced_*` but need meme-specific features)
- ❌ Social sentiment scraper (LunarCrush free tier, Twitter/X API v2 free tier)
- ❌ Holder concentration analysis (top 10 wallets >50% supply = dump risk)
- ❌ DexScreener / Birdeye API (free tier available, tracks new pairs)

---

## 4. Free APIs & Data Sources

| Data Need | Free Source | Quality |
|-----------|------------|--------|
| Penny stock prices | Yahoo Finance | ⚠️ Delayed for OTC |
| Penny stock screeners | Finviz (free) | ✅ Good for float, volume, sector |
| SEC filings (penny stocks) | SEC EDGAR | ✅ Free, real-time |
| Meme coin prices | Binance API | ✅ Real-time, we already use it |
| Meme coin social sentiment | **LunarCrush** free tier | ✅ 100 API calls/day |
| New meme coin pairs | **DexScreener** API | ✅ Free, real-time |
| Holder concentration | **Solscan** / **Etherscan** APIs | ✅ Free with rate limits |
| Twitter/X sentiment | **X API v2** free tier | ⚠️ 1,500 tweets/month |
| Reddit sentiment | **Reddit API** | ✅ Free, 60 req/min |

---

## 5. Estimated Impact

| Metric | Conservative Estimate | Optimistic Estimate |
|--------|----------------------|---------------------|
| Additional picks/day | 10-20 | 50+ |
| Expected WR (based on vol) | 35-40% | 45-50% |
| Expected AvgPnL per win | +2-5% | +5-15% |
| Risk | High (liquidity, rug pulls) | High |

**Note:** These are high-risk/high-reward asset classes. Position sizing must be capped (Kelly ≤ 0.25 for meme coins, ≤ 0.10 for penny stocks).

---

## 6. Recommendations

1. **START with meme coins** — we already have Binance price data. Just needs asset class definition + strategy targeting
2. **Add `memecoin` asset class** to `config.py` with appropriate risk limits (max 2% equity per position)
3. **Integrate LunarCrush API** — free tier gives social engagement metrics for 100 coins
4. **Use DexScreener for new pair discovery** — fresh meme coins have highest vol/returns
5. **Penny stocks are lower priority** — OTC data quality issues, liquidity concerns. Start with meme coins first
6. **Add rug-pull detection** — holder concentration >50% top 10 wallets = auto-reject
7. **Create `MEMECOIN_TOXIC_STRATEGIES`** — default-deny until proven strategies emerge
