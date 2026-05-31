# Edge Validity Audit Per Asset Class — 2026-05-31

**Auditor:** Quant sub-agent (specialized edge discovery role)  
**Scope:** Current portfolio (closed picks only), vs. industry-standard real-edge criteria  
**Data source:** `audit_dashboard/data/dashboard_data.json`, `top_edges_per_class.json`, `reports/cot_paper_pilot_overemission_falsified_20260513.md`  

---

## Executive Summary

**NO asset class currently passes real-money readiness gates.**

- **ALIVE (0/8 classes):** Zero strategies pass ≥3 of [DSR>0.95, PBO<0.05, WFE>60%, Live Sharpe>0.5, n≥100]
- **WEAK (0/8 classes):** Zero classes meet 1-2 criteria
- **DEAD (8/8 classes):** All show fundamental deficiencies (small n, over-emission, source concentration, or statistical invalidity)

**Root-cause pattern across all classes:**
1. **n < 100** (insufficient sample for statistical power) — affects all except CRYPTO
2. **Source concentration ≥50%** — caps portfolio concentration, signals lack of signal diversity
3. **DSR collapse** — after multiple-testing deflation, DSR<0.5 across the board (real edge requires >0.95)
4. **Over-emission artifacts** — COMMODITY's COT strategy inflated 101→5 when deduplicated
5. **No proven walk-forward edge** — WFE metric unavailable; no OOS data validates IS performance

---

## Per-Asset-Class Verdict

### 🔴 **CRYPTO** — DEAD (actively failing gates)

| Metric | Value | Criterion | Status |
|--------|-------|-----------|--------|
| n | 302 | ≥100 | ✅ PASS |
| WR | 35.1% | >55% | ❌ FAIL |
| PF | 0.872 | ≥1.5 | ❌ FAIL |
| DSR | 0.0 | >0.95 | ❌ FAIL |
| PBO | 0.533 | <0.05 | ❌ FAIL |
| CVaR gate | FAIL | MDD≤0.25 | ❌ FAIL |

**Root causes:**
1. **DSR collapse:** 0.0 = no statistical edge after multiple-testing correction (Bonferroni α=7.289e-5 over 686 tag combos)
2. **PBO ≥ 0.5:** Probability of backtest overfitting 53.3% — strategy is overfitted, not generalizable
3. **Source concentration:** 58.6% from "UNKNOWN" source — concentration risk, not diversified signal
4. **CVaR breech:** Worst-case 95th-percentile loss = -89.3% of equity (total drawdown risk)
5. **Negative expectancy:** -1.3 bps per trade after slippage (structural loss)

**Why it appears "good" in raw stats:** 302 closed picks aggregates multiple overlapping signals and timing windows. Deduplication would likely drop to ~50-80 true signal periods, worsening WR and PF further.

**Recommendation:** 
- HALT all new CRYPTO picks until DSR>0.5 and source concentration <30%
- Quarantine to paper-only mode (no real-money sizing)
- Require fresh 4-week pilot with source diversity constraint

---

### 🔴 **COMMODITY** — DEAD (over-emission artifact confirmed)

| Metric | Value | Criterion | Status |
|--------|-------|-----------|--------|
| n | 7 | ≥100 | ❌ FAIL |
| WR | 42.9% | >55% | ❌ FAIL |
| PF | 1.959 | ≥1.5 | ⚠️ WEAK |
| DSR | N/A | >0.95 | ❌ N/A (n<100) |
| Concentration | 71% (GC=F) | <30% | ❌ FAIL |

**Root causes:**
1. **n=7 catastrophic:** See `reports/cot_paper_pilot_overemission_falsified_20260513.md` — the "TIER_1_RENAISSANCE" COT strategy that showed PF 2.73, WR 90.1%, n=101 was traced to **5 unique CFTC weekly releases over-firing 20× per release** (101→5 consolidated). Real n=5 weekly signals; consolidated PF=0.17, WR=40%, negative PnL -$52.
2. **Apparent PF=1.959:** Likely contains same over-emission artifact as closed picks; true deduplicated PF unknown but expected <1.0
3. **Symbol concentration:** GC=F (gold futures) 71% of picks — single-commodity concentration
4. **No strategies with n≥20:** Cannot compute PBO or SPA (Statistical Pattern Analysis requires ≥20 trials per group)

**Historical context:** COMMODITY was targeted as "Tier-1 promotion" path pending COT timing-leakage fix (PR #941). That fix addressed **look-ahead bias**; this audit reveals **over-emission bias** is independently fatal.

**Recommendation:**
- BLOCK all real-money sizing on COMMODITY class
- Do NOT defer to "awaiting fresh backtest" — the over-emission pattern will repeat unless:
  - De-duplication logic added to `alpha_engine/cot_positioning.py` (one signal per [symbol, report_date, direction] tuple)
  - 4-week post-dedup pilot runs to generate ≥4 unique CFTC cycles with PF≥1.5 on 1-pick-per-cycle basis
  - Re-aggregated verdicts reviewed by external quant before any real-money sizing

---

### 🔴 **EQUITY** — DEAD (insufficient n, catastrophic PF)

| Metric | Value | Criterion | Status |
|--------|-------|-----------|--------|
| n | 22 | ≥100 | ❌ FAIL |
| WR | 27.3% | >55% | ❌ FAIL |
| PF | 0.047 | ≥1.5 | ❌ FAIL |
| DSR | 0.0 | >0.95 | ❌ FAIL |
| CVaR gate | FAIL | MDD≤0.25 | ❌ FAIL |

**Root causes:**
1. **n=22 << 100:** Statistical power insufficient for any verdict
2. **PF=0.047 catastrophic:** For every $100 of wins, $2,128 of losses — structural loss engine
3. **Negative expectancy:** -8.557 bps per trade after slippage — adverse selection at signal generation
4. **WR=27.3%:** Below random (50%) even before edge accounting
5. **Source concentration:** 54.5% UNKNOWN; top symbol WMT only 18%

**Why it looks "developed":** Early-stage portfolio had some wins (6/22), but skewed to large losses (avg_loss $122k vs avg_win $14k).

**Recommendation:**
- SUSPEND EQUITY class entirely — n=22 provides zero statistical power
- Do not attempt to salvage with more picks — the signal source is systemically biased toward losses
- Redirect capital to classes with n≥100

---

### 🔴 **FOREX** — DEAD (near-zero DSR, small n)

| Metric | Value | Criterion | Status |
|--------|-------|-----------|--------|
| n | 18 | ≥100 | ❌ FAIL |
| WR | 27.8% | >55% | ❌ FAIL |
| PF | 0.887 | ≥1.5 | ❌ FAIL |
| DSR | 0.021 | >0.95 | ❌ FAIL |
| Sharpe | N/A | >0.5 | ❌ FAIL |

**Root causes:**
1. **n=18 << 100:** Insufficient trials for statistical power
2. **DSR=0.021:** Essentially zero after multiple-testing adjustment; no statistical edge
3. **WR=27.8%:** Below random; adverse selection
4. **Source concentration:** 61% multi_asset_scanner; top symbol USDJPY=X only 33% (diversified within picks, but small n invalidates)
5. **Negative expectancy:** -0.741 bps per trade

**Why MDD gate passes:** CVaR=-0.629% is tight; but this is statistical luck on small n, not real diversification.

**Recommendation:**
- SUSPEND FOREX; n too small for any statistical claim
- DSR=0.021 confirms no real edge after multiple-testing correction
- Avoid accumulating more forex picks until n≥100 with DSR>0.5

---

### 🔴 **FUTURES** — DEAD (loss engine, sub-random WR)

| Metric | Value | Criterion | Status |
|--------|-------|-----------|--------|
| n | 11 | ≥100 | ❌ FAIL |
| WR | 9.1% | >55% | ❌ FAIL (catastrophic) |
| PF | 0.475 | ≥1.5 | ❌ FAIL |
| DSR | 0.0059 | >0.95 | ❌ FAIL |

**Root causes:**
1. **WR=9.1% catastrophic:** Only 1 win in 11 trades — worse than random (should be ~50%); systematic adverse selection
2. **n=11 << 100:** Too small for verdict, but pattern is consistent loss
3. **DSR=0.0059:** Essentially zero; no edge
4. **100% source concentration:** All picks from multi_asset_scanner (single source)
5. **Top symbol CL=F:** Crude oil 36% of picks; commodity futures inherently volatile

**Why it exists:** Multi_asset_scanner may have specific FUTURES edge claim that hasn't passed validation yet.

**Recommendation:**
- HALT FUTURES immediately — WR=9% indicates systematic loss
- Source 100% concentration violates diversification rule
- Do not add more FUTURES picks until source diversified and n≥20 with WR≥35%

---

### 🔴 **ETF** — DEAD (n=3 catastrophic)

| Metric | Value | Criterion | Status |
|--------|-------|-----------|--------|
| n | 3 | ≥100 | ❌ FAIL |
| WR | 33.3% | >55% | ❌ FAIL |
| PF | 0.193 | ≥1.5 | ❌ FAIL |
| DSR | N/A | >0.95 | ❌ N/A |

**Root causes:**
1. **n=3 catastrophic:** Single trades don't constitute statistics
2. **67% source concentration:** etf_scanner only; no signal diversity
3. **Top symbol XLE:** Sector (energy) 33% of portfolio
4. **PF=0.193:** For every $100 wins, $518 losses

**Recommendation:**
- ABANDON ETF class — n=3 provides zero statistical power
- No edge is detectable on this sample size

---

### 🔴 **BOND** — DEAD (n=2, zero wins)

| Metric | Value | Criterion | Status |
|--------|-------|-----------|--------|
| n | 2 | ≥100 | ❌ FAIL |
| WR | 0% | >55% | ❌ FAIL |
| PF | 0.0 | ≥1.5 | ❌ FAIL |

**Root causes:**
1. **n=2 catastrophic:** No statistical power
2. **WR=0%:** Zero wins observed (both trades lost)
3. **100% source concentration:** All from UNKNOWN source

**Recommendation:**
- ABANDON BOND class — n=2 provides zero statistical power

---

### 🔴 **PENNY_STOCK** — DEAD (n=1 catastrophic)

| Metric | Value | Criterion | Status |
|--------|-------|-----------|--------|
| n | 1 | ≥100 | ❌ FAIL |
| WR | 0% | >55% | ❌ FAIL |
| PF | 0.0 | ≥1.5 | ❌ FAIL |

**Root causes:**
1. **n=1 catastrophic:** Single trade has zero statistical meaning
2. **100% source + symbol concentration:** SOFI only

**Recommendation:**
- ABANDON PENNY_STOCK class — n=1 provides zero statistical power

---

## Cross-Asset Patterns

### 1. Small n is the Universal Constraint
Only CRYPTO (n=302) exceeds 100 trials. All other classes fail n≥100 criterion immediately:
- EQUITY: 22 (82% gap)
- FOREX: 18 (82% gap)
- COMMODITY: 7 (93% gap)
- FUTURES: 11 (89% gap)
- ETF, BOND, PENNY: all <5

**Implication:** Either the portfolio is too young (~2-4 weeks live), or the signal sources are too scarce to generate frequent picks.

### 2. DSR Collapse Across Board
Top-edges analysis (`top_edges_per_class.json`) found:
- **CRYPTO only:** 1 proven edge (n=327, PF=3.885, but tags=None indicates no specific strategy identifier)
- **All others:** 0 proven edges; best attempts show DSR<0.1

**Implication:** Even with permutation search over 686 tag-dimensional combinations, Bonferroni-corrected alpha=7.289e-5 only yields CRYPTO's 1 cell. The others fail multiple-testing correction entirely.

### 3. Source Concentration Capped
`money_ready_verdicts` flags `source_concentration_capped=True` for 7/8 classes:
- CRYPTO: 58.6% UNKNOWN
- EQUITY: 54.5% UNKNOWN
- FOREX: 61% multi_asset_scanner
- FUTURES: 100% multi_asset_scanner
- Others: single sources

**Implication:** Signal diversity is severely limited. Portfolio relies on 1-2 sources per class. Real-money readiness requires ≥3 independent sources with <25% concentration each.

### 4. Over-Emission Artifact in COMMODITY
COT positioning strategy shows empirical pattern:
- Raw headline: n=101, PF=2.73, WR=90.1% → "TIER_1_RENAISSANCE"
- Deduplicated (1-pick-per-CFTC-cycle): n=5, PF=0.17, WR=40% → "NO_EDGE"

This pattern likely repeats in COMMODITY's closed picks. Apparent PF=1.959, n=7 may decompose to fewer true signals with lower PF.

---

## Recommended Actions (Priority Order)

### Immediate (Week 1)
1. **HALT all real-money sizing** on COMMODITY, EQUITY, FOREX, FUTURES, ETF, BOND, PENNY_STOCK classes
2. **Quarantine CRYPTO to paper-only** until DSR>0.5 and source concentration <30%
3. Implement de-duplication patch to `alpha_engine/cot_positioning.py` (one signal per [symbol, report_date, direction])
4. Re-aggregate all closed picks using 1-pick-per-signal dedup logic; recompute verdicts

### Week 2-3
5. **Source diversification sprint:** Identify ≥3 independent signal sources per asset class (external APIs, ML models, human analysts)
6. **Walk-forward validation:** Run 60/40 chronological split on each strategy family to compute WFE and OOS Sharpe
7. **Sample size path:** Plan capital deployment to reach n≥100 per asset class within 8 weeks

### Week 4+
8. **Re-audit post-dedup:** Rerun this edge validity audit against deduplicated picks
9. **Tier-2 proof:** Demonstrate ≥3 strategies per class with DSR>0.5, PBO<0.05, WFE>60% before any tier-2 promotion

---

## Definitions & Criteria

**Real-money readiness gates (ALL must pass):**
- **DSR > 0.95:** Deflated Sharpe ratio accounts for multiple testing; <0.95 = no robust edge
- **PBO < 0.05:** Probability of backtest overfitting <5%; >0.5 = strategy is curve-fit noise
- **WFE > 60%:** Walk-forward efficiency (OOS Sharpe / IS Sharpe) >60%; out-of-sample generalizes to in-sample
- **Live Sharpe > 0.5:** Forward-looking risk-adjusted return
- **n ≥ 100:** Minimum sample size for statistical power on edge detection

**Asset class verdict:**
- **ALIVE:** ≥3/5 criteria pass
- **WEAK:** 1-2 criteria pass
- **DEAD:** 0 criteria pass

Current portfolio: **8/8 DEAD**

---

## Data Lineage

| Source | Date | Key finding |
|--------|------|------------|
| `audit_dashboard/data/dashboard_data.json` | 2026-05-31 21:16 | `money_ready_verdicts` per-class summary; asset_class_health |
| `audit_dashboard/data/top_edges_per_class.json` | 2026-05-29 06:38:48 | Permutation search over 686 tag combos; CRYPTO 1 proven, all others 0 |
| `reports/cot_paper_pilot_overemission_falsified_20260513.md` | 2026-05-13 | COT strategy over-emission: 101→5 trades, PF 2.73→0.17 |

---

## NFA / Disclaimer

No financial advice. Findings are analytical only. Real-money decisions require:
- Independent validation by external quant
- Compliance review (concentration, leverage, counterparty risk)
- Risk committee approval
- Board sign-off on tier-2 promotion

**Current verdict:** Portfolio is not production-ready for any asset class. All capital should remain in cash or low-risk instruments until ≥1 asset class reaches DSR>0.5 + n≥100.
