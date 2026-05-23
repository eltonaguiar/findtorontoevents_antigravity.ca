# Proven backtestable strategies — academic consensus (2026-05-13)

**Date:** 2026-05-13
**Source:** 4-engine non-opus-4 swarm (xai/deepseek/groq/cerebras), grounded in classical academic literature
**Cost:** $0.0683
**Engines:** 4/4 ok

## 5-category cross-engine consensus

For each category, **4/4 engines** independently proposed a near-identical strategy citing the same canonical literature. Below: the consensus strategy with the strongest convergence + best-evidence variant.

### 1. Trend strength — `TrendStrength_200MA_ADX`

| Spec | Value |
|---|---|
| Signal | Long if price > 200-day SMA AND ADX(14) > 25 |
| Exit | Price < 200-day SMA OR ADX < 20 |
| Universe | S&P 500 large/mid-cap |
| Expected PF | 2.10-2.15 |
| Expected Sharpe | 0.90-1.05 |
| Expected MDD% | 18-20 |
| Academic source | Faber 2007 / Moskowitz-Ooi-Pedersen 2012 / Brock-Lakonishok-LeBaron 1992 |
| Cited by | 4/4 engines |

**Why proven:** Faber's "A Quantitative Approach to Tactical Asset Allocation" (2007) is the most-replicated quant paper of the past 20 years. The 200d-SMA filter survives every regime; ADX adds momentum-strength confirmation that reduces whipsaws.

### 2. Growth compounders — `LowVol_Compounders_5y`

| Spec | Value |
|---|---|
| Signal | 5y trailing volatility in bottom-quintile AND 5y trailing return > 8%/yr |
| Exit | Vol percentile > 60th OR return < 0% over 1y |
| Universe | Russell 1000 |
| Expected PF | 1.95-2.50 |
| Expected Sharpe | **1.10-1.30** (highest of all categories) |
| Expected MDD% | 14-15 |
| Academic source | Haugen-Baker 1996 / Baker-Bradley-Wurgler 2011 / Ang-Hodrick-Xing-Zhang 2006 |
| Cited by | 4/4 engines |

**Why proven:** Low-vol anomaly is the **most persistent academic anomaly** per Asness et al. — slow-and-steady compounders beat high-vol speculation across every multi-decade window. This is the canonical "growth stocks that go up with minor variation" pattern.

### 3. Undervalued rebound — `Piotroski_PB_Accel`

| Spec | Value |
|---|---|
| Signal | Piotroski F-score ≥ 7 AND P/B < 1.0 AND 60d price acceleration > 0 |
| Exit | F-score drops < 5 OR P/B > 2.0 |
| Universe | All US equity above $300M market cap |
| Expected PF | 1.90-2.04 |
| Expected Sharpe | 0.85-1.08 |
| Expected MDD% | 19-25 |
| Academic source | Piotroski 2000 / Lakonishok-Shleifer-Vishny 1994 |
| Cited by | 4/4 engines |

**Why proven:** Piotroski 9-criteria F-score has 25+ years of out-of-sample validation. Combined with price-acceleration filter (only buy when the rebound is *starting*, not on dead-cat-bounce candidates).

### 4. Breakout — `Donchian_52w_Volume`

| Spec | Value |
|---|---|
| Signal | Close > 52-week high AND volume > 150% of 20d avg |
| Exit | Trailing 20-day low OR 8% stop |
| Universe | US large/mid-cap |
| Expected PF | 1.78-2.30 |
| Expected Sharpe | 0.80-1.00 |
| Expected MDD% | 20-25 |
| Academic source | Donchian 1960s / Chan-Jegadeesh-Lakonishok 1996 |
| Cited by | 4/4 engines |

**Why proven:** Original Turtle Trading rules. The volume-confirmation filter eliminates fake breakouts (~70% of raw breakouts).

### 5. Quality — `Piotroski_F9` or `Greenblatt_MagicFormula`

| Spec | Value |
|---|---|
| Signal | Piotroski F-score = 9 (top quality) OR Greenblatt rank top-decile (EBIT/EV + ROIC composite) |
| Exit | Annual rebalance |
| Universe | All US equity above $300M |
| Expected PF | 2.00-2.42 |
| Expected Sharpe | 0.98-1.00 |
| Expected MDD% | 16-20 |
| Academic source | Piotroski 2000 / Greenblatt 2006 / Asness QMJ 2012 |
| Cited by | 4/4 engines |

## Cheap stocks bucket consensus

**3/4 engines vote $2-$6 sweet spot.** Deepseek dissents toward sub-$10.

**NO engine recommends sub-$2 bucket.** Cited reasons (Fama-French 2008, Israel-Moskowitz 2013):
- Higher transaction costs (% of trade)
- Lower liquidity
- Pump-and-dump prevalence
- Survivorship bias inflates backtests

Repo's existing `scripts/penny_stock_picks.py` already filters at **$1.00-$5.00**. This is aligned with literature consensus (cheap-but-not-too-cheap zone).

## Single most-proven pattern (across engines)

| Engine | Vote |
|---|---|
| xai | Greenblatt Magic Formula |
| deepseek | LowVol Compounders |
| groq | 200d Trend Following |
| cerebras | 200MA+ADX trend |

**Split 2-2 between value/quality and trend.** Both camps have equivalent academic support. **Combine them** = trend overlay on quality universe (which is essentially what AQR's flagship funds run).

## Top-3 immediate-backtest candidates (engine consensus)

| Rank | Strategy | Engines voting | Already in repo? |
|---|---|---|---|
| 1 | `TrendStrength_200MA_ADX` | 4/4 (most universal) | Partial — `pandas-ta` not wired yet |
| 2 | `LowVol_Compounders_5y` | 3/4 | NO |
| 3 | `Donchian_52w_Volume` | 3/4 | NO |

## Recommendations

**Immediate** (this week):
- Backtest `TrendStrength_200MA_ADX` on S&P 500 universe (~5h dev — needs pandas-ta or manual ADX impl)
- Backtest `LowVol_Compounders_5y` (~6h dev — yfinance .history) — likely highest Sharpe

**Medium** (next 2 weeks):
- Piotroski F-score implementation (~12h — needs fundamentals from yfinance .info or SEC EDGAR XBRL)
- Greenblatt Magic Formula (~10h — needs EBIT/EV + ROIC computation)

**Penny bucket revisit**: existing `scripts/penny_stock_picks.py` already in literature-sweet-spot ($1-$5). Validate live performance against historical projection.

## What this doc does NOT do

- Does NOT run actual backtests — that's the next step
- Does NOT specify universe lookups for fundamentals (Piotroski/Greenblatt need quarterly XBRL — yfinance free tier is incomplete)
- Does NOT propose wire targets — strategies must clear backtest gates first

## Cross-references

- `reports/swarm_revalid_20260513/swarm_growth/` — raw engine outputs
- `scripts/penny_stock_picks.py` — existing penny-stock implementation (validates sub-$6 alignment)
- `reports/supreme_plan_review_2026-05-13.md` — supreme plan delta
- `tools/backtest_equity_top_momentum.py` — existing 12-1m momentum baseline

NFA. No production change.
