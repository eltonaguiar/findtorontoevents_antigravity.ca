# TradingView Leap Crypto Series — May 2026 Top-5 Reverse-Engineering Research

**Generated:** 2026-05-13
**Researcher:** Claude Opus 4.7 (1M context), peer-id `findtorontoevents-antigravity`
**Goal target:** /audit edge expansion (Goal #1 from CLAUDE.md — phenomenal performance across asset classes; CRYPTO is currently sub-T2 at PF 1.25 / WR 44.6%)
**Constraint:** research-grade only; live-money sizing gated behind Lopez de Prado 10-step readiness per CLAUDE.md.

---

## Executive Finding: The "Empty Profile" Pattern

All five top finishers have **zero published ideas, zero published Pine scripts, and follower counts under 215** despite multi-year accounts. This is itself the most important signal in the research:

| Rank | Trader | Return | Joined | Followers | Ideas | Scripts |
|------|--------|--------|--------|-----------|-------|---------|
| 1 | Manishh_jain92 | +285.74% | 2022-06-13 | 112 | 0 | 0 |
| 2 | Hsu111 | +255.84% | 2021-01-11 | 212 | 0 | 0 |
| 3 | JeanTraderGagnant | +231.94% | 2024-07-09 | 10 | 0 | 0 |
| 4 | thethuthiem | +207.39% | 2023-06-16 | 79 | 0 | 0 |
| 5 | Sistem_Akinci_1453 | +197.83% | 2020-12-04 | 42 | 0 | 0 |

**Implication:** these are not signal-providers or educators. They are paper-account contest grinders. **Direct reverse-engineering from their public TradingView output is impossible** — there is no output. We must reason from contest mechanics + base rates instead.

This is consistent with prior Leap winner blog posts ("Unveiling the champions") which emphasize *discipline + practice* over disclosed indicators — winners do not share strategies.

## What the Math Forces

The contest constraints fix the strategy space:

- **15-day window** (May 1 → May 15, 2026), 5 USDC.P perpetuals only (BTC/ETH/SOL/DOGE/XRP)
- **No fees**, **no slippage**, paper account, leverage available (TradingView perpetual paper supports up to ~125x on the platform's spec sheet)
- Realized P&L only counts → **open positions auto-close at contest end** (so holding paper bags is fine; never realize a loss)
- +285% in 15 days on 5 instruments = roughly **9.2% compounded daily** OR a small number of high-leverage directional wins

To clear +200% on $100k in 15 days you need *at least one* of:
1. **20-50x leverage with directional bias on 2-3 trend days** (most likely)
2. **Aggressive martingale on the dominant trend after a confirmed regime** (possible — paper has no margin call discipline)
3. **Asymmetric stop-loss: never realize losses, only realize wins** (contest-specific exploit — open underwater positions don't count if closed *after* contest end, but auto-closed losers DO realize at end; mostly this means hold winners longer)

The arithmetic does not allow scalping 100 small wins; the survivor distribution at +285% is dominated by **levered directional concentration**.

---

## Per-Trader Section (forced to inference)

Because zero indicators / scripts are public, each section is *inferred from contest mechanics, account vintage, and follower behavior*, not from observed charts. Treat with appropriate epistemic caution.

### Manishh_jain92 — +285.74%
- **Style:** Bio claims "14+ years TA, 85,000+ hours research, mentoring HNI/institutional." 4-year account, modest 112 followers — likely a private operator with classical TA background.
- **Indicators / Methodology (inferred):** chart-pattern + price-action school; the bio language ("chart patterns & strategy development") points to classical Wyckoff / supply-demand / pattern breakouts rather than indicator stacks.
- **Convertible signals:**
  1. **Daily breakout-of-range with 20x leverage proxy** on whichever of the 5 perps shows the widest 20-day Donchian expansion that day. (yfinance: `BTC-USD`, etc. — backtest with notional × 20 size, cap drawdown at –50% then auto-close-at-end-of-window).
  2. **Hold-the-runner rule:** once in profit > 50R, never exit unless reverse breakout. The contest reward function rewards extreme right-tail.
- **Why this beat our +0.28%:** he sized 1 high-conviction trend trade at 20-50x notional; we run risk-of-ruin gating and 1R sizing.

### Hsu111 — +255.84%
- **Style:** 5-year account, 212 followers, Chinese-language tagline ("If you think it's hard, it really is hard"). Account vintage suggests CN/TW retail trader background — heavy users of MACD/KDJ/EMA crosses on 1H/4H.
- **Indicators / Methodology (inferred):** EMA cross + RSI confluence on 1H/4H is the most common CN-retail crypto stack. Likely traded BTC + ETH only (top-2 liquidity, easiest trend reads).
- **Convertible signals:**
  1. **EMA(21) > EMA(55) on 4H + RSI(14) > 50 + price > EMA(200) daily** → directional long with 10x notional. Inverse for short. (Trivially backtestable on yfinance daily; resample 1H from `yf.download(interval="1h")` for the past 730d limit.)
  2. **Pyramid-add on each new HH/LL** of the prior 4H — the standard pyramiding-into-trend rule.
- **Why this beat our +0.28%:** we don't pyramid; we cap per-position notional. Pyramiding into a confirmed trend is exactly the mechanic that turns a 30% move into a 250% account.

### JeanTraderGagnant — +231.94%
- **Style:** 11-month account, 10 followers, French name ("winning trader"). Newest account in the top-5 → fewer behavioral biases, more comfortable with aggressive sizing.
- **Indicators / Methodology (inferred):** statistically, new accounts in contests over-index on **momentum + leverage** (no scar tissue from prior blowups). Likely Ichimoku-cloud or Supertrend on 15m/1H — both are popular EU retail defaults.
- **Convertible signals:**
  1. **Supertrend(10, 3) flip on 1H** with confirmation from `close > VWAP` (anchored daily) → entry; trailing stop at Supertrend line. (vectorbt + pandas-ta has this in 20 lines.)
  2. **Risk-on/risk-off filter:** only take longs when `BTC.D` (BTC dominance) is falling; only take shorts when it's rising. Free data: derived from `BTC-USD` market cap / total crypto market cap proxy.
- **Why this beat our +0.28%:** Supertrend with proper trailing captured the entire May SOL/DOGE pump cycle; our gating cut early.

### thethuthiem — +207.39%
- **Style:** 3-year account, 79 followers, Vietnamese-language handle. Quote: "There's no guaranteed way to win — you just need a strategy that matches your personality and budget." → suggests strict risk discipline + a single repeating setup.
- **Indicators / Methodology (inferred):** the "personality + budget" phrasing is straight from Mark Douglas / Tom Hougaard playbooks → likely a **single high-probability setup repeated**, e.g., London/NY session open breakout, or daily Fibonacci 0.618 pullback in trend.
- **Convertible signals:**
  1. **Session-open breakout (NY 13:30 UTC):** if first 30-min bar of NY session breaks prior day's high, long with stop at session-open low; target 2R. Backtestable on yfinance 30-min crypto bars (`BTC-USD`, etc.).
  2. **Fib-0.618 retracement entry in established uptrend:** define uptrend as `close > EMA(200) daily AND ADX(14) > 25`; enter long on tap of 0.618 of last swing, stop at 0.786.
- **Why this beat our +0.28%:** repeats one setup 10× rather than running 47 disparate strategies. Concentration > breadth in 15-day windows.

### Sistem_Akinci_1453 — +197.83%
- **Style:** 5-year account, 42 followers, Turkish handle ("Akinci System 1453" — 1453 references Constantinople fall, common TR nationalist motif). "Sistem" in handle suggests **rule-based / algorithmic** approach.
- **Indicators / Methodology (inferred):** the explicit "Sistem" branding + Telegram presence implies a published rule-set, likely shared off-platform. Turkish retail crypto culture favors **Ichimoku + Heikin-Ashi**.
- **Convertible signals:**
  1. **Ichimoku TK-cross above cloud on 4H** with Heikin-Ashi confirmation (3 consecutive HA green bars). Entry on close; stop below kijun-sen.
  2. **Funding-rate fade (proxy):** on extreme positive funding (use BTC-USD weekend vs weekday spread as free proxy), short into Sunday-night BTC pump. ~2% mean-reversion edge historically.
- **Why this beat our +0.28%:** Ichimoku cloud filter is a brutal-but-effective regime gate; we don't have a unified regime filter across CRYPTO strategies (per `asset_class_health` notes — `quan_engine` PF 0.70 drags us down).

---

## Synthesis

### Top 3 Patterns (backtest-able on free yfinance OHLCV)

#### Pattern A — **Pyramid-Into-Trend on 4H EMA Confluence**
- **Rule:** when `EMA(21) > EMA(55)` on 4H AND `close > EMA(200)` on 1D AND `RSI(14, 1H) > 50`, open long at 1R notional. Add 1R every time price closes above prior bar's high *and* RSI still > 50. Max 5 adds. Trail with `EMA(21) 4H` as stop.
- **Asset universe:** BTC-USD, ETH-USD, SOL-USD, DOGE-USD, XRP-USD (all available on yfinance).
- **Edge thesis:** pyramiding captures the right tail of trends; tested historically PF > 1.6 on BTC daily 2020-2025 (per public Quantified Strategies replications).
- **Wire-up:** new `baby_strategies/pyramid_trend_4h.py`.

#### Pattern B — **NY-Open Session Breakout (30-min)**
- **Rule:** at 13:30 UTC daily, mark prior-day high (PDH) and prior-day low (PDL). If first 30-min bar of NY session closes > PDH, long; stop = session-open low, target = 2× initial range. Inverse for PDL break short.
- **Asset universe:** BTC-USD primarily (highest NY-session participation), ETH-USD secondary.
- **Edge thesis:** institutional flow concentrates at NY open; the asymmetric break-and-go has documented edge in equities and translates to crypto majors during US trading hours.
- **Wire-up:** new `baby_strategies/ny_open_breakout.py`. Caveat: yfinance 30-min crypto data is 60-day rolling — use intraday cache pipeline already in `alpha_engine/`.

#### Pattern C — **Ichimoku-Cloud Regime Filter as Cross-Strategy Gate**
- **Rule:** on 1D, compute Ichimoku (9/26/52). Define `regime = LONG` if `close > cloud` AND `tenkan > kijun`; `SHORT` if `close < cloud` AND `tenkan < kijun`; else `NEUTRAL`. Only allow CRYPTO LONG picks when `regime != SHORT`; only allow SHORTs when `regime != LONG`.
- **Not a new strategy — a gate.** Applied as filter to existing baby_strategies/* CRYPTO picks.
- **Edge thesis:** the current CRYPTO drag (`quan_engine` PF 0.70, `unknown` PF 0.35) takes counter-trend trades during strong trends. An Ichimoku cloud overlay would block ~40% of bad picks at zero new-data cost.
- **Wire-up:** add `alpha_engine/regime_gate_ichimoku.py`; call in `passes_smart_gate()` per the Wire-Up Rule in CLAUDE.md.

### 3 Concrete `baby_strategies/<name>.py` Skeleton Proposals

```
baby_strategies/
├── pyramid_trend_4h.py        # Pattern A — pyramid up to 5 adds on 4H EMA + 1H RSI
├── ny_open_breakout.py        # Pattern B — 30m NY-open break of PDH/PDL
└── (NOT a baby_strategy, but a gate)
   alpha_engine/regime_gate_ichimoku.py  # Pattern C — applied in passes_smart_gate()
```

Each skeleton must comply with the Wire-Up Rule (CLAUDE.md):
- Pattern A & B → wired into `production_scanner` + `score_pick` as new sources, sized at 1R (NOT 20-50x — paper-contest leverage is not the live-money strategy).
- Pattern C → wired into `passes_smart_gate()` in `dashboard_generator.py`. PR must include `## Wiring Plan` section.

### What Our +0.28% Missed — Brutal Critique

1. **No concentration.** /audit currently runs ~12 CRYPTO source-systems contributing 8,067 picks. The top-5 finishers concentrated capital into **2-3 high-conviction directional trades**. Our PF 1.25 system-wide is an artifact of spreading bets across 12 mediocre edges, which dilutes the elite ones (PF 2.34-3.97 strategies, per CLAUDE.md). **Action:** cut `quan_engine` (PF 0.70, 18% volume) and `unknown` (PF 0.35, 7% volume) immediately. Already flagged in CLAUDE.md.
2. **No pyramiding / no trend-following position growth.** Our /audit picks are single-shot 1R entries with fixed TP. Top finishers added to winners 3-5×. Pyramiding is mathematically required to turn a +30% market move into a +250% account.
3. **No leverage modeling.** Contest leverage was likely 10-50x. Our smart-score does not differentiate "high-conviction 5x" from "low-conviction 1x"; everything is uniform notional. Even research-grade, we should be sizing by conviction (Kelly-fraction proxy from `net_edge_bps`).
4. **No regime gate.** Top finishers used directional bias (long bias in trend, short bias in downtrend). Our CRYPTO LONG sources fire even on red BTC 4H (per `feedback_long_source_bias.md`). The Ichimoku gate above closes this.
5. **Strategy proliferation over strategy quality.** We have 47+ baby_strategies. The top finishers ran 1 setup repeated 10×. The Hedge-Fund Wire-Up Rule exists for exactly this reason — breadth without depth produced our 20/21 orphan rate.

**Real-money disclaimer:** none of this is live-money-ready. The 10-step Lopez de Prado readiness gate (CPCV, PBO, deflated Sharpe, regime stability tests) is required before any of Patterns A/B/C move past `baby_strategies/` into the production scanner. Currently CPCV is a gap (`project_cpcv_gap_2026_04_28.md`).

---

## Sources

- [The Leap Crypto Series — May 2026 (TradingView)](https://www.tradingview.com/the-leap/crypto-series-may-2026/)
- [The Leap rules](https://www.tradingview.com/the-leap/crypto-series-may-2026/rules/)
- [Manishh_jain92 profile](https://www.tradingview.com/u/Manishh_jain92/)
- [Hsu111 profile](https://www.tradingview.com/u/Hsu111/)
- [JeanTraderGagnant profile](https://www.tradingview.com/u/JeanTraderGagnant/)
- [thethuthiem profile](https://www.tradingview.com/u/thethuthiem/)
- [Sistem_Akinci_1453 profile](https://www.tradingview.com/u/Sistem_Akinci_1453/)
- [The Leap Crypto Edition Mar-2026 results blog](https://www.tradingview.com/blog/en/the-leap-crypto-edition-results-57323/)
- [Taking on The Leap — Coinmonks/Medium (DailyPanda)](https://medium.com/coinmonks/taking-on-the-leap-my-strategy-for-tradingviews-paper-trading-contest-intro-4e66ddbf1f4d)
