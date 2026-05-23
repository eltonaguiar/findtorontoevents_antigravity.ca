# EQUITY + BOND swarm re-validation — combined synthesis

**Date:** 2026-05-13
**Preset:** non-opus-4 (xai / deepseek / groq / cerebras) — parallel runs
**Cost:** $0.0682 EQUITY + $0.0682 BOND = $0.14 total
**Engines responding:** 8/8 ok

## EQUITY — synthesis

**Mean TIER-1 attainability: 69%** (xai 75 / deepseek 72 / groq 80 / cerebras 48). Cerebras is the dissenter; 3/4 high-conviction.

**Cross-engine consensus on MDD reduction:**

| Technique | Engines proposing | Notes |
|---|---|---|
| VIX-based regime filter | 4/4 | Skip months when VIX > threshold or VIX term-structure inverted |
| Volatility targeting | 4/4 | Scale exposure to target 15% annualized vol |
| Yield-curve inversion filter | 3/4 (xai/deepseek/groq) | Skip when 10y-2y < 0 (recession predictor) |
| Stock-specific position caps | 2/4 (xai/cerebras) | 15% max single-stock concentration |

**Best-of-engine strategies (all expected to lift TIER-1):**

| Strategy | Engine | Expected PF | Sharpe | MDD% |
|---|---|---:|---:|---:|
| VIX_TERM_FILTER | deepseek | 3.1 | 1.5 | 8.5 |
| MOM_YC (yield curve) | groq | 2.8 | 1.6 | 6.0 |
| EQ_MOM_VIX | xai | 2.6 | 1.5 | 9.5 |
| MOM_VOL_FILTER | cerebras | 2.6 | 1.45 | 8.9 |

**Live-to-offline gap diagnoses (engines):**
- **deepseek** (key insight): "Survivorship bias — backtest uses current S&P 500 constituents; live trading includes stocks that later delisted or underperformed" + "Look-ahead bias in universe selection"
- **xai**: "Live emitters lack regime filters; live execution suffers higher transaction costs"
- **groq**: "Overfitting to historical data; lack of regime-filtering in live strategy"

**Most important EQUITY finding:** Adding VIX term-structure regime filter + volatility-targeted position sizing can reduce MDD 24.18% → <10% while maintaining PF > 2.5. **TIER-1 plausibly attainable in 60 days** with regime overlays — but watch for survivorship/look-ahead bias inflating the backtest baseline.

## BOND — synthesis

**Mean TIER-1 attainability: 50%** (xai 40 / deepseek 35 / groq 80 / cerebras 45). Groq outlier-high; rest cluster 35-45%. **Lower confidence than EQUITY** but still meaningful.

**Cross-engine consensus on credit-spread signals:**

| Signal | Engines proposing |
|---|---|
| HYG-LQD spread (high-yield vs investment-grade) | 4/4 |
| BAMLH0A0HYM2 (HY Option-Adjusted Spread, FRED) | 3/4 (xai/deepseek/groq) |
| AAA-BAA corporate spread | 2/4 (xai/deepseek) |
| TED spread (TEDRATE) | 2/4 (deepseek/groq) |

**Cross-engine consensus on duration rotation:**

All 4 engines propose rotating between long-duration (TLT) and short-duration (SHY/BIL) based on **10y-2y yield-curve slope (DGS10-DGS2)**.
- Inverted curve (10y-2y < 0): short-duration (SHY/BIL) — recession predictor
- Steep curve (10y-2y > 0): long-duration (TLT) — growth signal

**Best-of-engine strategies:**

| Strategy | Engine | Expected PF | Sharpe | MDD% |
|---|---|---:|---:|---:|
| CREDIT_SPREAD_DURATION_HYBRID | groq | 1.9 | 0.95 | 10 |
| HYG_LQD_TED_SPREAD_FILTER | deepseek | 1.65 | 1.10 | 12 |
| DualMomentumCrossAsset | cerebras | 1.6 | 1.12 | 18 |
| HYG_LQD_CreditSpread_6m | xai | 1.75 | 0.85 | 18 |

**Most important BOND finding (deepseek):** "0.57 Sharpe is driven by high win rate but low reward-per-win; adding credit-spread regime filter can double Sharpe by avoiding catastrophic drawdowns."

## Action items

### EQUITY
| # | Item | Effort | Reversibility |
|---|---|---|---|
| EQ1 | Backtest VIX term-structure filter on existing top-5 momentum (skip months when VIX1>VIX2 by 5%) | 4h | Full |
| EQ2 | Add volatility-targeted position sizing (target 15% annualized vol) | 6h | Full |
| EQ3 | Validate survivorship bias hypothesis — does backtest use point-in-time S&P 500 constituents? | 2h | N/A (audit) |
| EQ4 | Add 10y-2y yield-curve gate (skip momentum when inverted) | 3h | Full |

### BOND
| # | Item | Effort | Reversibility |
|---|---|---|---|
| BD1 | Backtest HYG-LQD spread regime filter (FRED `BAMLH0A0HYM2`) on existing 6m momentum | 5h | Full |
| BD2 | Add 10y-2y duration-rotation overlay (DGS10-DGS2 from FRED) | 4h | Full |
| BD3 | TED spread filter (TEDRATE) as crisis-skip — Sharpe lift expected 0.57 → 1.10 | 3h | Full |
| BD4 | Wire FRED data adapter (existing `fred_data_fetcher.py` + `FRED_API_KEY`) for all above | 2h | Full |

## Engine-quality (EQUITY+BOND round)

- **Deepseek** highest quality this round — surfaced survivorship bias (which is the most important finding) + named exact FRED series codes
- **Groq** most optimistic on tier-1 (80% both classes) — slightly higher fabrication risk; weight 0.7×
- **Xai** most conservative tier estimates + grounded MDD numbers
- **Cerebras** lowest tier1 confidence on EQUITY (48%) but creative carry-adjusted variant

For future rounds: deepseek as primary for QUANTITATIVE-DEPTH; xai as anchor; groq for speed; cerebras as creative-but-discount.

## Cumulative session totals

After 3 swarm rounds (FUTURES + FOREX + EQUITY+BOND):
- Total cost: $0.07 + $0.07 + $0.14 = **$0.28**
- Strategies proposed: ~50
- Cross-class consensus killers: 5
- Block proposals: 5 unanimous (FOREX JPY-cross triples)
- Tier-1 attainability: FUTURES 53% / FOREX 80% / EQUITY 69% / BOND 50%

NFA. No production change made.
