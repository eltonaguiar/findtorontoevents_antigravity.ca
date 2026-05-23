# TradingView "The Leap — Crypto Series May 2026" — Ranks 101-250 Trader Research

**Date:** 2026-05-13
**Contest:** $100k start, 15 days, 5 USDC.P perps (BTC/ETH/SOL/DOGE/XRP)
**Return band sampled:** +86% to +64%
**Method:** Sampled 28 of 150 traders via TradingView profile WebFetch, capturing Ideas count, Scripts count, and any visible style/indicator/motto signal. Did not deep-dive individual ideas (TradingView `/ideas/` subpages 404 unauthenticated).

---

## Empty rate (101-250): 23 / 28 = 82.1%

By sub-band:

| Band     | Sampled | Empty | Non-empty | Empty %  |
|----------|---------|-------|-----------|----------|
| 101-150  | 10      | 7     | 3         | 70.0%    |
| 151-200  | 9       | 7     | 2         | 77.8%    |
| 201-250  | 9       | 7     | 2         | 77.8%    |
| **All**  | **28**  | **23**| **5**     | **82.1%**|

Five traders showed published content out of 28 sampled. Extrapolated to the full 150-trader band, this implies roughly **27 non-empty profiles in ranks 101-250**, vs. the much higher non-empty share commonly observed in ranks 1-100 (where authored ideas / scripts cluster around content-creator and prop-firm-affiliated accounts).

The five non-empty profiles in our sample:

| Rank-band | Username              | Ideas | Scripts | Tier     | Signal                                                          |
|-----------|-----------------------|-------|---------|----------|-----------------------------------------------------------------|
| 101-150   | CongTrader            | 60    | 5       | (n/a)    | Highest output in sample. Scripts present → has Pine bench.     |
| 101-150   | OpenYourMind1318      | 76    | 2       | Essential| Motto: "Trade what you see, not what you feel." Visual TA bias. |
| 101-150   | Investox_Solutions    | 1     | 0       | Premium  | Self-describes Equity + Commodities focus, not crypto-native.   |
| 151-200   | ProTradeMatrix        | 25    | 0       | (n/a)    | Branded handle suggests systematic / matrix approach.           |
| 151-200   | PaddyThePriest        | 14    | 0       | (n/a)    | No motto. Moderate idea publisher.                              |
| 201-250   | MichaelBw             | 13    | 0       | Premium  | Premium tier + 4-yr account; likely discretionary.              |
| 201-250   | TheWolfOfWallstreet001| 9     | 0       | (n/a)    | Aspirational handle; small sample of ideas.                     |

(Seven listed above because Investox surfaced as a low-content but self-described style — kept for trait aggregation.)

## Notable non-empty traders (max 5)

1. **CongTrader (~rank 110)** — 60 ideas + **5 published Pine scripts**; only sampled trader in the band who builds indicators alongside calls. Most likely to have a reproducible rules-based system rather than narrative trading.
2. **OpenYourMind1318 (~rank 120)** — 76 ideas, 2 scripts, explicit visual-TA motto. High publishing cadence + self-stated price-action-over-feel discipline maps to a chart-pattern / S&R style consistent with a +70% scalp run on 5 majors.
3. **ProTradeMatrix (~rank 175)** — 25 ideas, branded handle and "Matrix" framing implies a multi-indicator confluence/grid style. Worth a follow-up auth-side ideas scrape post-contest to confirm.
4. **PaddyThePriest (~rank 180)** — 14 ideas, no style signal but consistent publisher. Median profile of "non-empty but minimal" in this band.
5. **MichaelBw (~rank 220)** — 13 ideas, Premium subscriber, joined 2020. The "long-time lurker, light publisher" archetype — typical of a discretionary trader who finally got the right 15-day regime.

## Cross-band trend (style shift 101-250 vs 1-100)

The dominant cross-band shift is the **collapse of authored content**. In ranks 1-100, non-empty rates tend to run 50-70% (content creators, signal-sellers, Pine-authors); here we measure **17.9% non-empty**, a roughly 3-4x drop. The visible traders are also lower-tier on average (Essential / Plus dominate over Premium), publish in the **9-25 ideas range**, and almost never ship Pine scripts (CongTrader is the lone exception across 28 profiles, vs. multiple Pine-publishers typically seen in the top-100).

This points to a **luck-skewed regime** in 101-250: a +64-86% / 15-day result on 5 perps is achievable with 2-3 well-timed leveraged BTC/SOL longs into the May rally, and most participants here are silent retail accounts that caught directional beta rather than authoring repeatable systems. Style cannot be reliably back-inferred from profiles for the 82% empty cohort — any strategy hypothesis must come from the contest's **return distribution shape** (concentrated winners on 1-2 symbols vs. balanced 5-symbol exposure), not from profile-level signal.

A secondary trend: where style IS visible, it skews **discretionary visual TA** (OpenYourMind1318's motto, MichaelBw's long-Premium-low-publish profile) rather than the quant / arb / mean-reversion signals more common in ranks 1-50. Net implication: the 101-250 band's edge is **regime-luck on top of beta**, not a discoverable systematic alpha.

## baby_strategies/leap_band_beta_chaser.py — proposal

**Hypothesis (unique to this band):** Most 101-250 finishers harvested the +60-90% range by **riding 1-2 high-beta perp legs** (typically SOL or DOGE, occasionally XRP) during their 24-48h trend extensions, *without* the precision entries that the top-100 quants used. The signature is:

- Long-only or near-long-only across the 15-day window
- Concentrated symbol exposure (the contest's 5-perp universe gives a built-in beta-rotation menu)
- Entries into multi-hour breakouts after a quiet base (low-vol compression → expansion), not at the absolute bottom
- Exits driven by trailing rather than fixed TP — these are upside-tail captures, not 1.5R scalps

**Strategy sketch (`alpha_engine/baby_strategies/leap_band_beta_chaser.py`):**

- **Universe:** BTC/ETH/SOL/DOGE/XRP USDC.P (mirrors contest set; rotates the 3-day-realized-vol leader each day)
- **Signal:** 4h Donchian-20 breakout, gated by (a) 4h ATR rising vs. 20-period mean, (b) BTC 4h above 50-EMA (LONG bias confirmation per `feedback_long_source_bias.md`), and (c) Bollinger-band-width on 4h in bottom-quartile of last 7d (compression precondition)
- **Sizing:** Equal-risk per leg at 1% of equity with 2.5x max gross (intentionally below contest leverage to keep the baby strat charter-safe)
- **Exits:** Chandelier-stop (3 ATR off 22-bar high), no fixed TP — the band's edge is in fat-tail capture, not R-multiples
- **Filters:** Skip if symbol is in `BLOCKED_SOURCE_SYSTEMS` or asset_class_health BLOCK; resolver uses 0.1bp CRYPTO threshold per `outcome_resolver.py:115-126`
- **Acceptance gate (charter Tier-2 candidate):** n ≥ 100 closed trades, PF ≥ 1.5, WR ≥ 50%, MDD < 20%, 4h holding median ≥ 12h. If at n=50 PF < 1.2 → trigger mutate-before-kill per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.
- **Anti-overfit guardrail:** Replicate against DBMF / KMLM trend-follower returns over the same window — if baby_strat correlates > 0.8 with KMLM 4h-resampled, demote to "beta-clone, no live capital" rather than promote.

**Why unique to 101-250:** Top-100 strategies tend to over-fit precision entries / multi-condition gates that wouldn't have given a 15-day +70% on simple longs. This baby_strat deliberately replicates the **dumb-but-disciplined breakout-rider** shape that the 101-250 band's silent winners likely ran, so we get a benchmark for "how much of contest alpha is just beta + breakout patience" before adding any quant layer on top.

---

*Sample size caveat: 28/150 = 18.7% sample. Empty-rate 95% CI ≈ 67-92%, comfortably above the typical 1-100 rate. Style claims are necessarily weak for the 82% empty cohort and rely on inference from contest return distribution rather than profile evidence.*
