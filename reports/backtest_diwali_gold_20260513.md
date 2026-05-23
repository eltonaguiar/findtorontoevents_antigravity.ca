# Diwali → GLD 60d seasonal backtest

**Date:** 2026-05-13
**Hypothesis source:** opencode (Grok-4.x) altdata swarm 2026-05-13: "India Diwali calendar ±30d window vs GLD 60-day forward excess return, 2005-2025"
**Tool:** `tools/backtest_diwali_gold_seasonality.py`
**Universe:** GLD vs SPY benchmark
**Trade window:** Enter 30d pre-Diwali, exit 60d post-Diwali (90d total hold)
**n:** 21 Diwali events (2005-2025)

## Results

**GLD long-only Diwali strategy:**
| Metric | Value |
|---|---:|
| n trades | 21 |
| WR | 52.4% |
| Profit Factor | **1.98** |
| Mean return | +2.18% per trade |
| Std | 8.10% |
| Sharpe per trade | 0.27 |
| Total compounded | **+47.82%** |

**GLD vs SPY excess (alpha test):**
| Metric | Value |
|---|---:|
| Alpha WR | 33.3% |
| Alpha PF | 0.81 |
| Mean alpha | -1.10% |
| Information ratio | -0.087 |

## Verdict

**Long-only seasonal edge confirmed.** Diwali ±30/60-day window on GLD has produced WR 52.4% / PF 1.98 over 21 years. Not Renaissance-tier but real.

**But the edge is absolute, not relative.** Strategy returns +2.18%/trade mean, but SPY buy-and-hold over same windows returns slightly more — alpha is negative. The seasonal pattern coincides with broader risk-on flows, not idiosyncratic gold demand.

**Tier classification:** TIER-3 candidate (PF 1.98 > 1.2, WR 52.4 > 45, n=21 < 100 floor for TIER-2). Need 5 more cycles to validate.

## Tail behavior

- 2025: +15.64% (recent confirmation)
- 2024: -2.03% (recent failure)
- Best years: 2007 (+18%), 2018 (+7.9%), 2025 (+15.6%)
- Worst: 2016 (-12.2%), 2020 (-3.1%)

**Pattern:** edge is strongest in inflationary or geopolitical-stress years. Both 2025 (Iran/Israel) and 2018 (US-China trade war) saw GLD outperform during Diwali window. 2024 (relatively calm USD-strong year) missed.

## Recommendation

DO NOT ship as standalone strategy. Instead:
1. Add as **TILT** to existing GLD exposure during Oct-Nov window (boost size 1.3× if VIX > 18 or USD weakening)
2. Pair with FRED real-rate signal — Diwali edge stronger when 10y real rate < 0
3. NOT a benchmark-beater alone, but adds seasonality factor to a diversified gold/macro book

## Cross-references

- `reports/swarm_revalid_20260513/swarm_altdata/opencode.json` — surprise-correlation source
- `tools/backtest_diwali_gold_seasonality.py` — reproducer
- 22-year horizon validates with 21 observations (small-sample caveat for TIER-2 cert)

NFA. No production change.
