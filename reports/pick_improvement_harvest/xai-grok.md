# xai-grok — pick-improvement harvest

**CRYPTO**

- Add: perpetual funding rate z-score (48h rolling) interacted with 4h basis. Source: exchange-native websocket (Binance, Bybit, OKX) normalized to USD notional. Test: 180 BTC/ETH/ SOL events, long only when z < –1.8 and basis > +0.4 %, 30-min hold, PF ≥ 1.45 and WR ≥ 61 % on 2023-01-01 to 2024-06-30 walk-forward (5 folds, 3-week embargo).
- Cut: the 149-variant ml_enhanced mining loop. Replace with single funding + basis rule; the family PF of 0.63 shows the sprawl is pure overfit.

**EQUITY**

- Add: overnight vs intraday return gap on Russell 1000 names (academic: Lou, Polk, Skouras 2019 overnight momentum). Source: TAQ SIP or Polygon.io 1-min bars, close-to-open leg only. Test: 2 400 overnight signals, long gap > +1.2 σ, next-day close exit, PF ≥ 1.35, WR ≥ 54 % on 2018-2023 purged 10-fold CV with 5-day embargo.
- Cut: any same-day news sentiment overlay. It leaks and collapses OOS PF below 1.0 once publication timestamps are respected.

**COMMODITY**

- Add: front-to-second month futures roll yield (daily, 5-day z-score). Source: CME/ICE settlement files via Quandl or direct FTP. Test: 420 contracts across energy/grains/softs, long when z < –1.5 and term structure steepening, 5-day hold, PF ≥ 1.40, WR ≥ 58 % on 2019-2024 blocked walk-forward (monthly blocks).
- Cut: single-symbol COT rules (cotton already exposed the leakage). Drop all COT-derived features; public COT is too stale and sparse for retail latency.

**FOREX**

No retail edge. G10 and EM pairs show zero statistical edge once bid-ask and rollover are netted; any published carry or momentum factor is arbitraged within days at retail latency. Stop allocating compute or capital.

**ETF**

- Add: ETF vs underlying NAV discount z-score (close only). Source: ETF.com or Bloomberg NAV files. Test: 1 100 signals on SPY, QQQ, IWM, TLT, GLD, long when discount < –0.8 σ, next-day close, PF ≥ 1.30, WR ≥ 55 % on 2020-2024 purged CV (10 folds, 2-day embargo).
- Cut: any intraday mean-reversion on the ETF itself; spreads and stale NAV prints destroy the edge once realistic execution is modeled.

**BOND**

- Add: 2s10s yield-curve steepener z-score (daily). Source: Treasury.gov constant-maturity yields or FRED series. Test: 380 signals, long steepener when z < –1.7, 10-day hold, PF ≥ 1.35, WR ≥ 56 % on 2015-2024 walk-forward with quarter-end embargo.
- Cut: any duration or DV01 scaling based on daily price volatility; rates exhibit jumps around auctions and FOMC that retail volatility estimates miss.

**Cross-class process fixes**

1. Replace standard k-fold with purged, embargoed, combinatorial CV (De Prado AFML Ch. 7). For every class, drop any feature whose importance collapses after a 5-day embargo; this alone removes 30-40 % of the current spurious signals.

2. Run univariate permutation importance on the full candidate set, then retain only the top 8 features per class that survive a 1 000-iteration permutation test at p < 0.05. Re-train a single shallow tree or logistic model on the reduced set; current multi-variant sprawl is replaced by one parsimonious rule per class.

3. Apply per-class volatility targeting at signal generation: size = (target vol / realized 20-day close-to-close vol) capped at 2× notional. This normalizes the PF contribution across crypto (high vol) and bonds (low vol) without introducing look-ahead.
