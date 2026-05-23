# TradingView Leap Crypto Series — May 2026, Ranks 6-15 Research

**Date:** 2026-05-13
**Contest:** The Leap Crypto Series May 2026 ($100k start, 5 USDC.P Coinbase perps: BTC/ETH/SOL/DOGE/XRP)
**Scope:** Public profile/Ideas/Scripts research, ranks 6-15. Free data only (yfinance).
**Method:** WebFetch against `tradingview.com/u/<user>/` profile root + per-user idea slug. Per-user `/ideas/` slug returns 404 on TV; only the profile header is reliably extractable from static HTML. The global `markets/cryptocurrencies/ideas/?authors=...` filter ignored the author param and returned the generic firehose for all three test users — flagged as non-attributable and discarded.

---

## 6. SinerjiPortfoy — +192.58%
- **Profile:** Public, 1.9K followers, joined 2018-04-01, "Plus" tier, **60 Ideas / 0 Scripts**. Bio (TR): *"Hisse Senetleri Teknik Analiz. Portföy Yönetimi"* = "Stock technical analysis, portfolio management." Active on X/YouTube/FB/IG. Per-user Idea bodies are server-rendered behind auth; titles not retrievable. The bio + 60-Idea volume points to **discretionary technical / portfolio rotation**, likely on BIST equities historically but applied to crypto perps for The Leap.
- **Convertible signal rule (inferred from "portfolio rotation" + crypto-perp success):** **Top-N momentum rotation** — rebalance daily to the 2 of {BTC,ETH,SOL,DOGE,XRP} with the highest 7d return AND price > 50d SMA; equal-weight long, leverage 5x.
- **Alt rule:** **Pullback-to-EMA20 on D-tf** — long when (close > EMA50_D) and (low <= EMA20_D <= close); SL = swing low - 1×ATR14; TP = 2.5R.

## 7. ethemm_sahinn_ — +190.02%
- **Profile:** **EMPTY** — 0 Ideas, 0 Scripts, 199 followers, joined 2020. Bio (TR): *"Trende göre hareket"* = "Move according to the trend." Premium tier but no public content. No code-ready signal can be derived; only the self-declared **trend-following** stance.
- **Convertible signal rule (bio-derived only):** **Donchian-20 breakout + trend filter** — long on close > highest(high,20) when close > EMA100; flip short on inverse; trailing-stop = Chandelier (22, 3×ATR).

## 8. mathieu_dugeny — +181.53%
- **Profile:** **EMPTY** — 0 Ideas, 0 Scripts, 27 followers, joined 2024-01. Premium, no bio. Recently-onboarded account that ranked top-10 in a $100k contest with zero public footprint → likely a private/secondary handle for an experienced trader.
- **Convertible signal rule:** None extractable. Default placeholder if backtesting top-10 archetype: see aggregate strategy below.

## 9. tradingwala — +180.15%
- **Profile:** Public, 258 followers, joined 2014-09, Premium, **7 Ideas / 0 Scripts**. Bio: *"Discretionary MultiTF Trader, Auction Market Theory, OrderFlow, F&O + Macros, Factorbased Investing."* Also placed **3rd in The Leap Christmas Edition 2025** → repeat-podium = persistent edge, not luck. Style cluster: **volume-profile / order-flow / multi-TF context**.
- **Convertible signal rule:** **Value-Area-Low (VAL) rejection long** — on D-tf, mark prior-day VAL from session-Volume-Profile; intraday on 15m, long when price tags VAL ± 0.1×ATR and prints a bullish engulfing or delta-positive bar (proxy: close > open and volume > 1.5×SMA(vol,20)). SL = day's low; TP = POC then VAH.
- **Alt rule:** **Composite-POC breakout** — long on H1 close > 5-day composite POC AND BTC.D falling AND aggregate stable-supply rising 3d.

## 10. Snipercoopz — +177.88%
- **Profile:** **EMPTY** — 0 Ideas, 0 Scripts, 63 followers, joined 2019-06, Essential tier. Bio: *"God 1st, Trading 2nd."* Handle "sniper" + "coopz" → likely **scalp/precision-entry** stance, but no published evidence.
- **Convertible signal rule (handle-derived):** **1m liquidity-sweep reversal** — on 1m, long when low pierces prior-day-low by ≥0.05% then closes back above within 3 bars and RSI(2) crosses up through 10; SL below sweep wick; TP = mid-range or 1R/2R/3R scale.

## 11. bossout10 — +169.55%
- **Profile:** Public, 279 followers, joined 2024-11, Essential, **58 Ideas / 0 Scripts**. Bio: *"Jesus Christ is God and Timing is Everything."* 58 ideas in ~6 months = ~2-3/week, suggesting **high-cadence intraday or swing calls**. Per-Idea bodies not retrievable; cadence + "timing" emphasis points to **session-/event-driven entries**.
- **Convertible signal rule:** **NY-open momentum continuation** — at 09:30 ET, take the 15m breakout direction of the first 15m candle when its body > 0.6×ATR14_15m AND aligned with D-tf EMA20 slope; SL = opening-range opposite extreme; TP = 1.5R hard, runner trails on EMA9_5m.
- **Alt rule:** **Daily-close trend bot** — long when daily closes > EMA10_D AND EMA10_D > EMA20_D AND BTC > EMA50_D; exit on first daily close < EMA10_D.

## 12. jengthanaphon — +165.83%
- **Profile:** **EMPTY** — 0 Ideas, 0 Scripts, 8 followers, joined 2021-08, Essential. No bio. Thai handle. Zero public footprint.
- **Convertible signal rule:** None extractable.

## 13. crocbeginners30 — +164.61%
- **Profile:** **EMPTY** — 0 Ideas, 0 Scripts, 3 followers, joined **2025-05-08** (one year before contest), Premium. Brand-new account ranked top-15 in $100k contest = either a sharp on a fresh handle or pure-luck variance on a 5-symbol concentrated book.
- **Convertible signal rule:** None extractable; flag for **variance suspicion** (n=1 contest, 5 symbols, leverage allowed → fat-tail single-trade outcomes plausible).

## 14. MiracleCho — +164.42%
- **Profile:** **EMPTY** — 0 Ideas, 0 Scripts, 14 followers, joined 2024-06, Essential. Bio (KO): *"방구석 트레이더. 조프링"* = "room-corner trader" (i.e., retail home trader, casual self-deprecating tone).
- **Convertible signal rule:** None extractable.

## 15. hannesv99 — +163.03%
- **Profile:** **EMPTY** — 0 Ideas, 0 Scripts, 12 followers, joined 2025-02, Premium. No bio. <4-month-old account in top-15.
- **Convertible signal rule:** None extractable.

---

## Patterns unique to ranks 6-15 vs ranks 1-5

- **Empty-profile prevalence is much higher** in 6-15: **7 of 10 (70%)** have zero public Ideas or Scripts. The implication is that mid-pack Leap finishers skew toward **lurkers / private-execution traders / fresh handles** rather than published-thesis content creators. (Cross-check vs top-5 agent's findings expected to show more publishing density up top.)
- **Two non-English bios** (Turkish ×2, Korean ×1) at ranks 6-15 vs presumed English-dominant top-5 — regional retail surge.
- **Bio "trend-following" / "timing"** declarations dominate the ones with text (ethemm, bossout10, SinerjiPortfoy) — no mean-reversion or stat-arb language visible in the 6-15 cohort.
- **Repeat-podium signal (tradingwala 3rd Leap Christmas 2025 → 9th Leap May 2026)** — only one repeat I can confirm in this cohort; this is the single highest-trust source for strategy reverse-engineering.

## Aggregate insight — median style in top-15

With 7 of 10 profiles empty, **the dominant inferable style is trend / momentum continuation on daily-to-intraday timeframes**, mostly discretionary, with **volume-profile / order-flow as the only edge-flavor that shows real bio commitment** (tradingwala). Mean-reversion, stat-arb, and news-driven styles are **absent from the public footprint** of ranks 6-15. Pine Scripts published: **0 across all 10 traders** — no rule-based systematic strategies were shared. Best characterization: **discretionary multi-timeframe momentum with order-flow / volume-profile context, leverage-amplified on a 5-symbol concentrated book**. The concentrated book + the single-month contest window means **variance is meaningful** — multiple empty/fresh-account finishers (crocbeginners30, hannesv99, mathieu_dugeny) likely caught one or two clean leveraged trends rather than running a reproducible system.

## Two complementary `baby_strategies/<name>.py` skeleton proposals

These complement whatever the top-5 agent proposed (presumably more breakout/trend variants). Both use yfinance only.

### 1. `baby_strategies/value_area_low_bounce.py`
Inspired by **tradingwala** (Auction Market Theory / OrderFlow). yfinance has no real volume-profile feed, so we **approximate VAL = 30-bar low-quartile price weighted by volume** on daily bars.

```
Entry (long):
  approx_VAL = quantile(price[-30:], 0.25, weights=vol[-30:])
  if (low_today <= approx_VAL * 1.005) and (close_today > open_today) \
     and (vol_today > 1.5 * vol_sma20):
    enter long
Stop:  today's low - 0.5 * ATR14
TP1:   approx_POC (volume-weighted median price last 30 bars), 50% size
TP2:   approx_VAH (75th-pctile vw price), runner
Universe: BTC, ETH, SOL on daily.
Hypothesis: replicates discretionary "tag-the-VAL, fade-the-flush" entries.
```

### 2. `baby_strategies/regional_momentum_rotation.py`
Inspired by **SinerjiPortfoy** ("Portföy Yönetimi" = portfolio rotation) + the bio-stated **trend-following** stance of ethemm_sahinn and bossout10. Rotates a small concentrated book like the Leap contest's 5-symbol cap.

```
Universe: BTC, ETH, SOL, DOGE, XRP (exact Leap basket).
Daily rebalance (1 bar/day on yfinance):
  rank symbols by 7d_return * (price > SMA50)
  hold top-2 equal-weight long
  hold cash if BTC < SMA200 (regime gate)
Sizing: 50/50 split, no leverage (yfinance can't verify perps fills).
Hypothesis: rotation captures the concentrated-book leverage edge
  the top-15 traders exploit, minus the blow-up risk of 5x perps.
```

---

## Caveats & data-quality notes

- TradingView per-user `/ideas/` slug returns **404** on logged-out fetch; only `/u/<user>/` profile header is reliably extractable. Granular per-idea timeframe/indicator labels were **not retrievable** for any of the 3 active profiles.
- The `markets/cryptocurrencies/ideas/?authors=<x>` URL returned the generic crypto firehose (identical results for SinerjiPortfoy, tradingwala, bossout10) — TV is silently ignoring the `authors` param for non-authenticated requests. Those titles are **discarded** as non-attributable.
- 7 of 10 traders have **zero public content** — verdict for those is "no inference possible beyond bio."
- Backtests must use **yfinance daily/hourly OHLCV** only per constraint. Volume-profile, order-flow, and footprint indicators (tradingwala's stated edge) cannot be exactly replicated — use volume-weighted price-quantile approximations.
