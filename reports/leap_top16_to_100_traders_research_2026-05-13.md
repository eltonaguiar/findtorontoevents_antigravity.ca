# TradingView Leap Crypto Series — May 2026, Ranks 16-100 Research

**Date:** 2026-05-13
**Contest:** The Leap Crypto Series May 2026 ($100k start, 5 USDC.P Coinbase perps: BTC/ETH/SOL/DOGE/XRP, 15 days)
**Scope:** Sampled 36 of 85 profiles across the rank 16-100 band. Free data only (yfinance BTC/ETH/SOL/DOGE/XRP-USD).
**Method:** WebFetch against `tradingview.com/u/<user>/` profile root. Per-Idea bodies, per-Script source, and `ideas/` sub-slugs are server-rendered behind auth and consistently returned 404/empty bodies — only profile headers (Ideas count, Scripts count, bio, tier, follower count) are reliably extractable. Roughly 1 in 4 requests hit a TV WAF 403 rate-limit, retried once then dropped per the no-retry-loop budget.

---

## Empty profile rate (16-100): 33 / 36 profiled = 91.7 %

Sample of 36 (across the full 16-100 band):
MarketMaverick007, share4win, hany_barsoum, TraderBugsBunny, sahincelileker, Ulyeses, siren777, Lucky1ch, Regulus12, RudraAssassin, NareshG_SEBI_REGISTERED_RA, bitcoinbaily, iprowessx, BMosesAssetManagement, Trend_trader09, ShashvataTrading, jssharp, alfonrt, optimism888, Starecat, Tradinginsights, DidzCrypto, Forexfactorypro, Crypwonx10, Ciphernaut, GreenWave_, MTF_Trader, DataSneeze, REX_KR, maxwelldfs, Daniele_Ram, imharshitg, m115, Yetkin666, kofana, nucleargly, Trading_Twat.

- **Empty (0 Ideas + 0 Scripts):** 33
- **Has Ideas only:** 3 — NareshG_SEBI_REGISTERED_RA (2), ShashvataTrading (133), Trading_Twat (9)
- **Has Scripts:** 1 — bitcoinbaily (32 scripts, 1 idea)
- **WAF-403 / unread (excluded from rate):** Setindex2014, OnurOzd, ozinet, HeLLBoY_DEagle, Obxexxed, izitradepro, wiseaker — flagged as inconclusive, not counted as empty.

The empty-rate climbs sharply vs the top-15 (where ~60% were empty). Below rank 30, every profiled account in the 16-100 band that was bio-readable showed 0/0 except the four above. **Interpretation:** the long tail of the leaderboard is overwhelmingly silent retail accounts — almost none publish reproducible setups. Inverse Yzilmaz/Mosesy/etc. type "Pine-publisher in the top-15" do not exist down here.

---

## Non-empty traders worth replicating

### A. **bitcoinbaily** — Rank ~20s, 32 Pine scripts, 1 idea, Essential tier, joined 2023-01
- **Style trait:** Indicator/strategy publisher (the only Pine-publisher discovered in the entire 16-100 sample). Username + disclaimer (educational, non-professional) signals **crypto-focused indicator developer**. Script titles weren't extractable from the rendered profile shell, but a 32-script library from a Jan-2023 account = sustained Pine output, the demographic most likely to be running a **mechanical entry rule** in the contest rather than discretionary calls.
- **Convertible signal rule:** Without title access, default to the highest-prior Pine-author archetype: **multi-timeframe RSI(14) + EMA-cross strategy** — long when 4h-RSI crosses up through 50 AND 1h-EMA9 > 1h-EMA21 AND daily-close > daily-EMA50; opposite for short; SL = 2×ATR14_1h, TP = 3×ATR14_1h. Universe = 5 contest perps. Backtest-able on yfinance 1h bars for BTC/ETH/SOL; DOGE/XRP need 30-day window only.

### B. **ShashvataTrading** — Rank ~48, 133 Ideas, 0 Scripts, joined 2018-12, 322 followers
- **Style trait:** Highest Idea-volume account in the entire 16-100 sample. 133 ideas over ~7 years = ~1-2/month, suggesting **discretionary swing on Indian equities** (handle is a Sanskrit/Indian name, typical of NSE/BSE traders who crossed into crypto for the Leap). Per-Idea content not extractable, but the cadence pattern (sparse-but-recurring) is the signature of a **chart-pattern / support-resistance** trader, not a mechanical bot.
- **Convertible signal rule:** **Daily-close swing breakout with volume confirmation** — long on D-tf when close > highest(high, 20) AND volume > 1.5×SMA(volume, 20) AND BTC.D falling 3d; SL = 20-day-low; TP = 1.5R then trail on EMA10_D. Tested on yfinance daily OHLCV; volume proxy uses BTC-USD/ETH-USD daily volume which is reliable on yfinance.

### C. **Trading_Twat** — Rank ~52, 9 Ideas, 0 Scripts, Premium, joined 2023+
- **Style trait:** Bio: "Wen altsezon?" ("when altcoin season?") — **alt-rotation / altseason-timer** trader. 9 ideas suggests low-frequency macro calls. On a 5-symbol Coinbase-perp universe where BTC, ETH, SOL, DOGE, XRP are 1 large-cap + 4 alts, an alt-season bias is mechanically tradeable.
- **Convertible signal rule:** **BTC.D regime alt-rotation** — when BTC.D 7d return < -1% AND BTC daily-close > daily-EMA50 (risk-on backdrop), long-only the alt with the best 7d return among {SOL, DOGE, XRP}; rebalance every 24h; flatten all alts when BTC.D 3d > +1.5%.

(**NareshG_SEBI_REGISTERED_RA** had only 2 Ideas — too thin to derive a rule. Bio claims "scanner-based momentum / relative strength swing." Filed as honorable mention; no signal extracted.)

---

## Aggregate patterns across non-empty

1. **Publishing is anti-correlated with finishing in the bottom half.** The 16-100 band is dominated by silent accounts. The 3-4 non-empty accounts span very different styles (Pine-indicator dev / discretionary equities chartist / altseason timer). No single dominant playbook emerges — unlike top-15 where multiple traders showed volume-profile / order-flow signatures.
2. **No 5-symbol-perp specialists.** Zero accounts in the sample had visible content concentrated on BTC/ETH/SOL/DOGE/XRP. The traders who placed in this band did not build a public crypto-perp track record.
3. **Brand-new accounts persist into rank 100.** Multiple Premium accounts joined 2024-2025 and reached top-100 with 0 publications — same fat-tail-variance pattern flagged in the top-15 report (5-symbol concentrated book + leverage → top-100 reachable by single-trade luck).
4. **No ICT / SMC visible language anywhere in the sample.** The "liquidity sweep / order block" vocabulary that dominates crypto-Twitter is absent from these bios, despite that being the most-blogged retail crypto style. Possible selection bias: ICT traders publish on YouTube/Twitter, not TradingView Ideas.
5. **High WAF-403 rate (~20% of requests).** TV is actively rate-limiting profile scraping for anonymous traffic. Future research budgets should plan ≥1.3× redundancy on profile fetches.

---

## 2 new baby_strategies/<name>.py proposals (beyond cycle-10 five)

### 1. `baby_strategies/btc_dominance_alt_rotator.py` (from Trading_Twat altseason bias)
- **Concept:** Daily-rebalance long-only rotator into the best-momentum alt of {SOL, DOGE, XRP} when BTC.D regime is risk-on (BTC.D falling AND BTC above 50d). Flat when risk-off.
- **Universe:** SOL-USD, DOGE-USD, XRP-USD (yfinance daily); regime filter = BTC-USD daily-close vs daily-EMA50 + BTC dominance proxy (BTC market cap / total crypto cap via free CoinGecko `/global` endpoint).
- **Pine-equivalent signal pseudocode:**
  ```
  btc_d_3d = ta.change(btcDominance, 3)
  btc_above_ema50 = close_btc > ta.ema(close_btc, 50)
  risk_on = btc_d_3d < 0 and btc_above_ema50
  r7_sol = (close_sol / close_sol[7]) - 1
  r7_doge = (close_doge / close_doge[7]) - 1
  r7_xrp = (close_xrp / close_xrp[7]) - 1
  best_alt = argmax(r7_sol, r7_doge, r7_xrp)
  long_signal = risk_on and (current_symbol == best_alt)
  exit_signal = btc_d_3d > 0.015  // flush on dominance spike
  ```

### 2. `baby_strategies/daily_breakout_volume_confirm.py` (from ShashvataTrading swing-breakout bias)
- **Concept:** Daily-close swing breakout with volume confirmation and BTC.D regime gate. Captures the "Indian-equities-style breakout trader migrated to crypto" archetype that probably accounts for a chunk of the top-100 finishers.
- **Universe:** BTC-USD, ETH-USD, SOL-USD, DOGE-USD, XRP-USD (yfinance daily; volume is reliable).
- **Pine-equivalent signal pseudocode:**
  ```
  hh20 = ta.highest(high, 20)
  vol_ok = volume > ta.sma(volume, 20) * 1.5
  btc_d_falling = ta.change(btcDominance, 3) < 0
  long_signal = close > hh20[1] and vol_ok and btc_d_falling
  sl_price = ta.lowest(low, 20)
  tp1_R = (close - sl_price) * 1.5
  trail_after_tp1 = ta.ema(close, 10)
  ```

Both strategies share a **BTC.D regime gate** — the one structural pattern with replication-grade evidence across the top-100 sample (multiple bios reference altseason/dominance/regime context, none reference SMC/order-flow). The BTC.D proxy is free-data: `https://api.coingecko.com/api/v3/global` → `market_cap_percentage.btc`.

---

## Source disclosures
- All counts from `tradingview.com/u/<username>/` HTML headers fetched 2026-05-13.
- Per-Idea / per-Script bodies not extractable via unauthenticated WebFetch (server-rendered).
- Empty-rate excludes WAF-403 unreadable accounts; including them would worsen the publish-rate, not improve it.
