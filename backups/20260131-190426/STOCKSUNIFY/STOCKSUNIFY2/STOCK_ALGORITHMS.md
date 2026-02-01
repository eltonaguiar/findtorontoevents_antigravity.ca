# Stock Algorithms — Full Reference

This document defines **every algorithm** used on the Find Stocks page. Algorithm names here match the **All Algorithms** dropdown and filters exactly.

> **Where this file lives:** Keep a copy in the **stocksunify** repo (`STOCK_ALGORITHMS.md` in the repo root) so the links from the Find Stocks page resolve. It also lives in **TORONTOEVENTS_ANTIGRAVITY** in the repo root.

---

## 1. CAN SLIM Growth

**Display name in UI:** CAN SLIM Growth  
**Used for:** Long-term growth (3–12 months)

### What it is

CAN SLIM Growth is a rules-based growth screener based on William O’Neil’s methodology. It finds stocks with strong relative strength, clear uptrends, and solid price action vs. 52-week highs.

### How it works

- **Relative Strength (RS) Rating (up to 40 pts)** — 12‑month price momentum vs. market; we prefer RS ≥ 90, with lower scores down to 60 still contributing.
- **Stage-2 Uptrend (30 pts)** — Minervini-style “Stage 2”: base formation, then break toward new highs. We use price/volume structure and moving-average alignment to flag Stage‑2 candidates.
- **Price vs. 52‑week high (20 pts)** — Current price as a fraction of the 52‑week high; closer to highs scores higher.
- **RSI momentum (10 pts)** — 14‑day RSI; we favor “healthy momentum” (e.g. 50–70) and give partial credit for overbought/oversold when it fits the setup.
- **Volume (bonus)** — Extra points when current volume is meaningfully above average (e.g. >1.5×).

Stocks are scored 0–100. Rating bands: **STRONG BUY** (≥80), **BUY** (≥60), **HOLD** (40–59), **SELL** (<40). Timeframe is treated as 3–6–12 months depending on RS and stage.

### Best for

- Growth stocks, typically $10+
- Hold periods of several months to a year

### Risk and validation

- **Risk:** Medium; favors liquid names with longer history.
- **Validation:** Methodology is grounded in O’Neil’s research (e.g. 60–70% accuracy in his studies). Our implementation uses the same ideas; exact thresholds may differ from his original rules.

### Where it’s implemented

- **This repo:** `scripts/lib/stock-scorers.ts` → `scoreCANSLIM()`  
- **Daily picks:** `scripts/generate-daily-stocks.ts` runs CAN SLIM and writes `algorithm: "CAN SLIM"` (displayed as CAN SLIM Growth in the UI).

---

## 2. Technical Momentum

**Display name in UI:** Technical Momentum  
**Used for:** Short-term momentum (24h, 3d, 7d)

### What it is

Technical Momentum scores stocks on volume, RSI, breakouts, and volatility/regime. Logic and weights **change by timeframe** (24h, 3d, 7d) so the same name can have different ratings per horizon.

### How it works

**24‑hour**

- Volume surge (40 pts) — current vs. 10‑day average; e.g. >2× gets full weight.
- RSI extremes (30 pts) — oversold (<30) or overbought (>70) or “healthy” (50–60).
- Breakout (30 pts) — price at or near 20‑day high.

**3‑day**

- Volume (30 pts), Breakout (30 pts), RSI momentum (25 pts), volatility/ATR‑style (15 pts).

**7‑day**

- Bollinger Squeeze (30 pts) — low volatility before a potential move.
- RSI extremes (25 pts), Volume (25 pts), institutional-style proxy (20 pts) — e.g. size + volume.

Score 0–100. **STRONG BUY** (≥75), **BUY** (≥50), **HOLD** (30–49), **SELL** (<30). Risk is skewed higher for low-price and low-cap names.

### Best for

- Short-term momentum (24h–1 week)
- Liquid names; penny stocks get a higher risk label

### Risk and validation

- **Risk:** Medium to very high for penny/speculative names.
- **Validation:** No formal backtest in this repo; logic follows common technical/volume ideas.

### Where it’s implemented

- **This repo:** `scripts/lib/stock-scorers.ts` → `scoreTechnicalMomentum(data, timeframe)`  
- **Daily picks:** Run for `24h`, `3d`, `7d`; stored as `algorithm: "Technical Momentum"` and `timeframe: "24h"|"3d"|"7d"`.  
- **UI:** Shown as e.g. “Technical Momentum (24h)” when timeframe is included.

---

## 3. ML Ensemble

**Display name in UI:** ML Ensemble  
**Used for:** Next-day or short-horizon returns; technical-heavy features

### What it is

ML Ensemble is a **machine-learning** approach that combines multiple models (e.g. Random Forest, Gradient Boosting, XGBoost) to predict returns. In the referenced repos it typically targets **next-day return** and uses many technical/microstructure features.

### How it works

- **Target:** Usually 1‑day ahead return (or similar short horizon).
- **Features:** Returns, gaps, moving averages (e.g. 5/10/20/50/200), volatility, RSI, MACD, Bollinger, volume ratios, etc.
- **Models:** Tree-based (Random Forest, Gradient Boosting, XGBoost) and sometimes linear models.
- **Evaluation:** MSE, R², MAE on out-of-sample or backtests.
- **Guardrails:** Min history, min volume, anomaly checks to avoid garbage inputs.

It’s a **predictor**, not a simple score; output is a forecasted return or direction, which can be turned into a rating (e.g. STRONG BUY/BUY/HOLD/SELL) with thresholds.

### Best for

- Liquid large/mid caps
- Short-horizon (e.g. 1‑day) predictions where technicals are stable

### Risk and validation

- **Risk:** Medium when used on liquid names with proper position sizing.
- **Validation:** Accuracy is model- and data-dependent; no single “proven” number in this doc.

### Where it’s implemented

- **This repo:** Not implemented in `stock-scorers.ts` or the daily generator. The Find Stocks page **displays** picks that may come from other data sources (e.g. STOCKSUNIFY) that use or aggregate ML Ensemble.
- **Other repos:** Described in `STOCK_CHATGPT_ANALYSIS.md` (e.g. MLBacktesting, XGBoost/GradientBoosting). Algorithm name **ML Ensemble** is kept in the UI and docs so the dropdown and filters stay aligned with all sources.

---

## 4. Composite Rating

**Display name in UI:** Composite Rating  
**Used for:** Medium-term “overall attractiveness” (about 1–3 months)

### What it is

Composite Rating is a **multi-factor score** that mixes technicals, volume, fundamentals, and market regime. It doesn’t target a single horizon but fits best for swing/medium-term screening and watchlist ranking.

### How it works

- **Technical (40 pts)** — Price vs. 50/200 SMAs, RSI in a “healthy” range (e.g. 50–70).
- **Volume (20 pts)** — Current vs. average volume; surge gets more points.
- **Fundamental (20 pts)** — Simplified use of PE and market cap (e.g. reasonable PE, sizable cap).
- **Regime (20 pts)** — Recent volatility buckets (normal / low‑vol / high‑vol); normal regime gets full weight.

Score 0–100. **STRONG BUY** (≥70), **BUY** (≥50), **HOLD** (30–49), **SELL** (<30). Timeframe is treated as about 1–3 months.

### Best for

- Watchlists and “rate these stocks” workflows
- Medium-term swing context

### Risk and validation

- **Risk:** Medium; broad appeal across caps when thresholds are sensible.
- **Validation:** Logic matches the “Composite Rating Engine” described in `STOCKS_IMPLEMENTATION_SUMMARY.md` and ChatGPT analysis; exact weights can be tuned.

### Where it’s implemented

- **This repo:** `scripts/lib/stock-scorers.ts` → `scoreComposite()`  
- **Daily picks:** `scripts/generate-daily-stocks.ts` runs it and stores `algorithm: "Composite Rating"`.

---

## 5. Statistical Arbitrage

**Display name in UI:** Statistical Arbitrage  
**Used for:** Pairs / mean reversion; market-neutral style

### What it is

Statistical Arbitrage focuses on **pairs of correlated stocks** and trades **mean reversion** of the spread (e.g. z‑score). It is relative-value / market-neutral, not a directional rating on a single ticker.

### How it works

- **Pairs:** Find historically correlated names (e.g. same sector, high correlation).
- **Spread:** Track spread (or ratio) between the two; normalize to z‑score.
- **Entry/exit:** Enter when z‑score exceeds a threshold (e.g. ±2); exit when it reverts.
- **Evaluation:** Sharpe ratio, total return, drawdown on the strategy.

Output is **strategy performance** (Sharpe, return), not a STRONG BUY/BUY/HOLD/SELL on one symbol. The Find Stocks page may show it as an algorithm **source** or filter when picks/backtests are imported from repos that run this strategy.

### Best for

- Correlated large-cap/sector pairs
- Mean-reversion, market-neutral allocation

### Risk and validation

- **Risk:** Depends on leverage and pair selection; can be medium if capital and pairs are chosen carefully.
- **Validation:** Typically assessed via backtest Sharpe and returns; see analysis docs for details.

### Where it’s implemented

- **This repo:** Not implemented in `stock-scorers.ts` or the daily generator. The name **Statistical Arbitrage** is included so the UI and docs match all algorithm names used in the ecosystem (e.g. from `STOCK_CHATGPT_ANALYSIS.md` and other repos).
- **Other repos:** Referenced in ChatGPT analysis (e.g. StatisticalArbitrage, z‑score, Sharpe/return).

---

## Name ↔ Dropdown Mapping

| Dropdown / filter name | Document section   | In this repo’s daily generator? |
|------------------------|--------------------|----------------------------------|
| **All Algorithms**    | (no filter)        | —                                |
| **CAN SLIM Growth**    | §1 CAN SLIM Growth | Yes (`CAN SLIM`)                 |
| **Technical Momentum** | §2 Technical Momentum | Yes (`Technical Momentum` + 24h/3d/7d) |
| **ML Ensemble**       | §3 ML Ensemble    | No (other data sources)          |
| **Composite Rating**  | §4 Composite Rating | Yes (`Composite Rating`)        |
| **Statistical Arbitrage** | §5 Statistical Arbitrage | No (other sources)        |

---

## Links

- **This file (GitHub):** Use the same path in your repo, e.g.  
  `https://github.com/<org>/<repo>/blob/main/STOCK_ALGORITHMS.md`
- **Pros/cons & improvements:** `STOCK_ALGORITHM_PROSCONS_AND_IMPROVEMENTS.md` — effectiveness research, pros/cons per algorithm, and improvement suggestions
- **Implementation:** `scripts/lib/stock-scorers.ts`, `scripts/generate-daily-stocks.ts`
- **Summaries:** `STOCK_ALGORITHM_SUMMARY.md`, `STOCKS_IMPLEMENTATION_SUMMARY.md`
- **AI/design analysis:** `STOCK_CHATGPT_ANALYSIS.md`, `STOCK_GOOGLEGEMINI_ANALYSIS.md`, `STOCK_COMETBROWSERAI_ANALYSIS.md`

*Last updated: January 2026*
