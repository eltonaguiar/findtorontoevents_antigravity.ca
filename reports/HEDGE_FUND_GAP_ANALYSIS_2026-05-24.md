# Hedge Fund Grade Picks — Action Plan & Gap Analysis

**Date:** 2026-05-24 | **Focus:** Closing the gap to "hedge fund quality" picks per asset class

---

## 1. Current State Audit

### 1.1 US Equity Picks (UEPS) — ❌ NO LIVE PICKS
- Status: **"Building track record — n=0/100"**
- Scoring: Composite = 0.55 × ValueComposite + 0.45 × QualityComposite × SafetyGate
- SafetyGate: Altman Z'' ≥ 1.10 AND Beneish M ≤ -1.78 (binary filter)
- **CRITICAL WARNING:** ML calibration is SYSTEM-WIDE INVERTED. Confidence 0.85-0.90 is WORST bucket at 20% WR
- Tier classification deferred until n≥100

### 1.2 AI Tournament — ✅ OPERATIONAL
- 3,149 picks, 9 asset classes, 34 models, 53.4% overall WR
- 4 proven persona pairs via kill gate
- 0 Tier-1 edge pairs (strict statistical framework)
- FOREX auto-blocked, BOND warned

### 1.3 HYROTRADER — ✅ OPERATIONAL (Crypto Only)
- 18-strategy QuanEngine consensus voting
- Live playbook with per-strategy LONG/SHORT signals
- ML edge optimizer for strategy×symbol scoring
- Crypto futures/perps only — no equity, bond, forex coverage

---

## 2. Gap Analysis: What's Missing for Hedge Fund Grade

### 2.1 Per-Asset Class Prediction Features

| Asset Class | Current State | Missing Features | Hedge Fund Standard |
|---|---|---|---|
| **EQUITY** | UEPS building (n=0), tournament 650 picks | Fundamental scoring (F-Score, ROIC, Altman Z), sector rotation, VIX gating | Multi-factor model (value + quality + momentum + low vol), GICS sector-neutral, earnings surprise alpha |
| **CRYPTO** | HYROTRADER 18 strategies, tournament 628 picks | Funding rate arbitrage, on-chain metrics, whale tracking integration | Multi-timeframe consensus, perpetual funding rate edge, cross-exchange arb |
| **FOREX** | Tournament 454 picks (BLOCKED) | Carry trade signal, PPP valuation, COT positioning | G10 carry + momentum blend, real rate differential model, COT extreme positioning |
| **COMMODITY** | Tournament 470 picks, COT scraper | Term structure (backwardation/contango), inventory data, weather gating | Roll yield harvesting, EIA inventory delta, seasonal patterns with weather overlay |
| **ETF** | Tournament 453 picks | Sector momentum, VIX correlation, flow data | Sector rotation with regime detection, flow-of-funds signal, VIX futures term structure |
| **BOND** | Tournament 439 picks (WARNED) | Yield curve dynamics, duration targeting, credit spread analysis | Curve steepener/flattener pairs, real yield vs inflation expectation, HY-IG spread signal |
| **PENNY** | Tournament 43 picks (0 resolved) | Float analysis, social sentiment, SEC filing patterns | Low-float momentum with insider buying confirmation, social volume spike filter |
| **FUTURES** | Tournament 11 picks (0 resolved) | Roll yield calendar, COT extreme positioning, seasonal patterns | Multi-contract calendar spread analysis, CFTC supplemental report decomposition |

### 2.2 Systemic Gaps

| Gap | Severity | Impact |
|---|---|---|
| **ML calibration inverted** — confidence is anti-signal | 🔴 CRITICAL | All "high-confidence" picks underperform coin-flips |
| **No fundamental equity scoring** live in UEPS | 🔴 CRITICAL | Equity picks have no value/quality filtering |
| **UEPS n=0** — no track record at all | 🔴 CRITICAL | Cannot validate equity long-term-value strategy |
| **HYROTRADER crypto-only** — no equity/forex coverage | 🟡 HIGH | Multi-asset coverage missing |
| **No persona registry for "super secure" conservative picks** | 🟡 HIGH | No low-risk pick filter |
| **FRED macro data wired but not integrated into pick generation** | 🟡 MEDIUM | Regime context exists but unused in scoring |
| **Polymarket/Kalshi signals separate from persona system** | 🟡 MEDIUM | Prediction markets not influencing pick direction |
| **Copy trader data available but not scored/evaluated** | 🟡 MEDIUM | 20+ picks/2h not contributing to tournament rankings |

---

## 3. UEPS Standard Picks Critique

The screenshot shows picks with strong fundamentals:

### ADBE (Adobe) — Score 0.839
| Metric | Value | Assessment |
|---|---|---|
| F-Score | 7/9 | 🟢 Strong financial health |
| Magic Rank | #1 of 49 | 🟢 Top value |
| ROIC | 45.1% | 🟢 Exceptional capital efficiency |
| Altman Z'' | 3.94 | 🟢 Very low bankruptcy risk (>2.6 safe) |
| Beneish M | -2.90 | 🟢 No earnings manipulation |
| FCF Yield | 8.8% | 🟢 Strong cash generation |
| Entry: $244.76 | IV: $367.14 | 🟢 49.9% upside to intrinsic value |

### PYPL (PayPal) — Score 0.785
| Metric | Value | Assessment |
|---|---|---|
| F-Score | 8/9 | 🟢 Excellent financial health |
| ROIC | 18.0% | 🟡 Good, not great |
| Altman Z'' | 2.78 | 🟢 Above safety threshold |
| Entry: $44.23 | IV: $66.34 | 🟢 50.0% upside |

### Key Concerns
1. **UEPS shows n=0/100 on live page** — these picks may be SAMPLE/DEMO data, not actual picks
2. **No stop-loss specified** — long-term value holds may have massive drawdown risk
3. **ML calibration inversion** — if confidence is anti-predictive, scoring may be backwards
4. **Single-factor approach** — pure value/quality without momentum timing can mean years of underperformance
5. **No position sizing** — no Kelly, no risk budget, no max drawdown constraint

---

## 4. Proposed "Super Secure Picks" Persona Category

A new persona category for conservative, capital-preservation-focused picks:

### Super Secure Criteria (per asset class)
| Criterion | Threshold | Rationale |
|---|---|---|
| F-Score (equity only) | ≥ 7/9 | Piotroski financial health |
| Altman Z'' (equity only) | ≥ 2.6 | Safe zone, no bankruptcy risk |
| Beneish M (equity only) | ≤ -1.78 | No earnings manipulation |
| Max Drawdown (all) | ≤ 10% trailing 6m | Capital preservation |
| Sharpe Ratio (all) | ≥ 0.5 trailing 3m | Positive risk-adjusted return |
| Beta (all) | ≤ 1.2 | Low market sensitivity |
| WR (persona level) | ≥ 55% over n≥30 | Proven win rate |
| Kelly allocation | ≤ 1% | Ultra-conservative sizing |

### Persona Names
- `super_secure_value` — for EQUITY with deep value + quality filters
- `super_secure_macro` — for FOREX/BOND with regime confirmation
- `super_secure_trend` — for CRYPTO/COMMODITY/ETF with low-vol trend following

---

## 5. Questions for Agent Swarm

1. The live UEPS page says n=0/100 but the screenshot shows scored picks (ADBE, PYPL, QCOM). Are these sample/demo data or actual picks from a different section?
2. ML calibration is "SYSTEM-WIDE INVERTED" — confidence 0.85-0.90 has 20% WR. How do we fix this without rebuilding the entire ML pipeline?
3. HYROTRADER has 18 crypto strategies but no equity coverage. Should we expand HYROTRADER to equities or build a separate UEPS-equivalent for crypto?
4. Should "super secure picks" be a separate persona category or a post-filter applied across all picks?
5. FRED macro data is now live (7 series). How should regime context influence pick direction and confidence?
6. What's the minimal viable path to get hedge fund grade picks in EQUITY specifically? (considering UEPS has n=0)
7. Should we use the 28 legacy models' historical WR data (from the old pipeline's 16k picks) as seed confidence for our new tournament pipeline?
