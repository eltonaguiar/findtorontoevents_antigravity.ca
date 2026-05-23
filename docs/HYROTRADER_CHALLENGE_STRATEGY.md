# HyroTrader prop challenge — pass strategy

**Optimized for:** prop-style **survival math** (daily + max drawdown, often **trailing**), not “best directional call.”  
**Platform:** HyroTrader (Bybit/Binance via CLEO)  
**Date:** April 8, 2026  

### Locked profile (Hyro FREE TRIAL UI, Apr 2026)

| Field | Value |
|--------|--------|
| **Challenge** | **FREE TRIAL** (Specs: **Two step** product, **futures**, **trailing** DD) |
| **Capital** | **5,000 USDT** |
| **Profit target (meter)** | **+250 USDT** (**+5%**) — single target on trial dashboard |
| **Drawdown limit (meter)** | **−250 USDT** (**5%** trail) — same *size* as profit goal → symmetric risk |
| **Max loss (meter)** | **−500 USDT** (**10%** trail from peak) |
| **Trading days** | **≥ 5** (T-Days 0 → 5) |
| **Risk / trade** | **0.75%** → **37.50 USDT** (adjust if Hyro forces lower) |
| **Daily soft stop** | **−125 USDT** (−2.5%) → no new trades |

A **later funded / step-2** phase may show different profit steps—re-read Hyro when you graduate; do not assume +500 USDT phase 1 on the **trial** screen.

**Position sizing tables + formula:** [`HYROTRADER_POSITION_SIZES.md`](./HYROTRADER_POSITION_SIZES.md)

**Focus of this playbook:** **Crypto only** (BTC, ETH, SOL, etc.) — execution rules and setups.

**Related in this repo**

- **Macro / multi-asset thesis** (gold, oil, indices, FX + crypto) — context only; **Hyro lists crypto perps/futures only:** [`PROP_BET_CHALLENGE_PICKS_APRIL2026.md`](./PROP_BET_CHALLENGE_PICKS_APRIL2026.md)
- **Live tracker + JSON:** [findtorontoevents.ca/audit/hyrotrader/](https://findtorontoevents.ca/audit/hyrotrader/) · `audit_dashboard/data/hyrotrader_picks.json`

---

## The math that matters

Before picking a single trade, understand the constraint math:

| Rule | Value | What it means |
|------|-------|----------------|
| Profit (trial meter) | **+5%** | **+250 USDT** on 5K |
| Drawdown (trial meter) | **−5%** | **−250 USDT** trailing allowance (Hyro UI) |
| Max loss (trial meter) | **−10%** | **−500 USDT** trailing from peak |
| Min trading days | **5** | Hyro T-Days counter |
| Stop loss | Required | Every trade must have SL |
| Drawdown type | **Trailing** | Peaks ratchet floor — book gains |

### Critical: tick-by-tick trailing DD

With trailing intraday/high-water-mark style rules:

- New equity highs can **ratchet** the loss allowance; floating profit that gives back **consumes** room.
- Implication: **book profits**; avoid letting winners float without a plan.

**Confirm** exact DD math on Hyro’s rule page — prop firms vary.

---

## Position sizing

### Rule: risk ~**0.75%** of account per trade (not 1–2%)

| Account | Risk/trade (0.75%) | Example (2% stop distance) |
|---------|---------------------|----------------------------|
| $5,000 | $37.50 | ~$1,875 notional (illustrative) |
| $10,000 | $75.00 | ~$3,750 |
| $25,000 | $187.50 | ~$9,375 |
| $50,000 | $375.00 | ~$18,750 |
| $100,000 | $750.00 | ~$37,500 |

**Position size (concept):**

`Position (units) = (Account × 0.0075) / (stop distance in $ per unit)`  
or equivalently risk dollars ÷ stop distance in dollars.

---

## Day-by-day pace (5-day minimum)

**Trial target +250 USDT:** e.g. **~+50 USDT/day** average over 5 days, or **~+1%/day** — avoid one hero day that then gives back under **trailing** rules.

- Big green day → **reduce** risk the next day (trail eats give-back).
- Red day → no revenge; you only need **+250 USDT** total, not recovery in one session.

**Later phase (if Hyro adds another step):** often tighter psychology—consider **0.50%** risk (**25 USDT**/trade) until you read the new meters.

---

## Five trade setups (challenge-suitable)

Each chosen for: defined risk, relatively quick resolution, clear entries.

### 1) BTC/ETH Bollinger band reversion (primary)

- **Timeframe:** 15m / 1h · **Symbols:** BTCUSDT, ETHUSDT  
- **Idea:** Close below lower BB (20, 2) → wait for close back inside → long; SL ~1.5× ATR below; TP middle band (conservative).  
- **Repo tie-in:** Documented mean-reversion / band studies in audit research stack.

### 2) RSI extreme reversion (scalp)

- **Timeframe:** 5m / 15m · **Symbols:** BTC, ETH, SOL  
- **Idea:** RSI(2) &lt; 10, price above 200 SMA → long on RSI cross back above 10; SL swing low; TP RSI 70 or +1.5% (whichever first). **Skip** if price &lt; 200 SMA.  
- **Repo tie-in:** Connors-style short-RSI mean reversion themes.

### 3) Funding rate contrarian (swing)

- **Timeframe:** 4h / daily · **Symbols:** BTC, ETH  
- **Idea:** Very negative funding → long bias with price/RSI/BB confirmation; SL ~2%; TP when funding normalizes or +3%.  
- **Trailing-DD note:** Consider flattening before sleep if large floating profit is at risk of giving back.

### 4) Volume breakout (momentum)

- **Timeframe:** 15m / 1h · **Symbols:** Top liquidity coins  
- **Idea:** Volume &gt; ~2.5× 20-period avg + break of 20-period high (long); SL breakout candle low; TP ≥ 1.5× risk.

### 5) Support / resistance bounce

- **Timeframe:** 1h / 4h · **Symbols:** BTC, ETH  
- **Idea:** 2nd/3rd touch + rejection candle; SL beyond wick; TP next S/R or 2:1 R.

---

## Rules that save the challenge

1. Set **SL before** entry.  
2. Keep **~0.75%** risk per trade unless your math says otherwise.  
3. Take profit at plan; trailing DD punishes greed.  
4. **Cap trades/day** (e.g. max 3); after 2 losses, **stop** for the day.  
5. After **+1.5%** day, consider standing down.  
6. Avoid high-impact news (CPI, FOMC) if spreads/slippage hurt you.  
7. Prefer **flat overnight** if overnight volatility + trailing DD is a risk.  
8. **No averaging down.**  
9. If daily P&amp;L hits **-2.5%**, stop — half the daily budget gone.  
10. **Log** every trade; if a setup is &lt;50% WR after N trades, pause it.

---

## Trade log template

| Day | Time | Asset | Setup | Entry | Stop | Target | Exit | R | Daily cum |
|-----|------|-------|-------|-------|------|--------|------|---|-----------|
| 1 | | | | | | | | | |

---

## Watchlist example (week of April 8–12, 2026)

**Priority:** BTCUSDT, ETHUSDT, SOLUSDT — verify prices and indicators at execution time (do not treat stale numbers as live).

**Caution:** Low-liquidity alts, headline spikes, events — widen risk or skip.

---

## Scenario planning

See original working notes: best / expected / worst case day paths — goal is stay inside **-5%** daily and **-10%** max while grinding **+5%**.

---

## Pre-challenge checklist

- [ ] Platform tested (CLEO / exchange connection)  
- [ ] Position size calculator  
- [ ] BB + RSI(2) + ATR(14) on charts  
- [ ] Funding checks (e.g. 00:00 / 08:00 / 16:00 UTC if using that setup)  
- [ ] Trade log  
- [ ] News calendar  
- [ ] Notifications for SL/TP  

---

## Final note

Prop challenges reward **survival** and **consistency** more than hero trades.  
This document is **not financial advice**; challenge capital is at risk. Align every rule with Hyro’s **current** terms.

---

*Draws on internal research themes (mean reversion, funding, risk framing). Integrated from workspace playbook `HYROTRADER_CHALLENGE_STRATEGY.md` (April 2026).*

---

## Review feedback — Cursor agent (2026-04-19)

1. **Evidence separation:** Prop survival math is **orthogonal** to `/audit` marketing WR — never cite Hyro challenge metrics as validation for dashboard strategies (or vice versa) without a labeled bridge study.
2. **Factory:** Passing a challenge is **not** S7/S8 in Strategy Factory terms — add one line referencing [STRATEGY_FACTORY_V1_1_AMENDMENTS.md](STRATEGY_FACTORY_V1_1_AMENDMENTS.md) if this doc is used to justify emitter promotion.
3. **Risk:** Trailing DD rules dominate — any “edge” section should cite **max consecutive losers** acceptable under the trial meters, not only per-trade risk %.
4. **Cross-link:** Live JSON + dashboard: `audit_dashboard/data/hyrotrader_picks.json` — note snapshot time when citing performance.
5. **Diversification:** If combining setups, use correlation discipline from [STRATEGY_DISCOVERY_PROTOCOL.md](STRATEGY_DISCOVERY_PROTOCOL.md) / [correlation_prune_strategies.py](../baby_strategies/correlation_prune_strategies.py) when multiple algos run concurrently.
