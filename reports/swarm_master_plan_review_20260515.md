# Swarm Review — Quant Rescue Master Plan — 2026-05-15

**Engines:** deepseek (grok-3-flash), xai (grok-3), cerebras (gpt-oss-120b)
**All 3 HEALTHY** (11-14KB each) | Cost: $0.07

---

## Cross-Engine Consensus (3/3 agreement)

### ✅ What the Plan Gets Right (all 3 engines)
1. **Feature leakage purge as Day-1** — +9.21pp CV lift, corrupts ALL downstream decisions
2. **n_eff reporting necessity** — CRYPTO n=8011 could be n_eff=200-400 (autocorrelation)
3. **COMMODITY first for live deployment** — highest PF (2.49), lowest n_eff risk
4. **HG=F/PL=F reclassification** — correctly removes futures probation double-count
5. **Baby backtest runner** — delivers missing OOS validation for 210 strategies

---

## Critical Consensus Corrections (all 3 engines independently flagged)

### 🔴 C1: Transaction Cost Engine Must Move to Phase 2 (NOT Phase 3)
**deepseek:** "Without a friction model, LIVE_ELIGIBLE is meaningless. COMMODITY PF=2.49 → ~1.8-2.0 with 0.1% slippage."
**xai:** "This delay risks blocking COMMODITY's 2026-07-15 target. Without friction-adjusted metrics, no class can realistically progress to T2."
**cerebras:** "A logical inconsistency: the gate cannot be evaluated without the cost model."

→ **Action required:** Move transaction cost engine from Phase 3 (Week 2) to parallel with Phase 2 deliverables.

### 🔴 C2: Walk-Forward Automation for COMMODITY/BOND Must Start Immediately
**deepseek:** "COMMODITY's 322 trades span multiple regimes. If 80% came from 2020-2022 supercycle, OOS could show PF<1.0."
**xai:** "Missing OOS validation is existential risk. Delaying WFA risks building on unvalidated foundations."
**cerebras:** "Before wiring any new factor, OOS stability must be confirmed for the base class."

→ **Action required:** Trigger COMMODITY walk-forward run immediately. Do NOT delay to Phase 3.

### 🟡 C3: Position Sizing Before First $500 Live
**deepseek:** "Kelly-optimal weighting achieves 1.2× average Sharpe vs 0.7× with equal weighting — 70% Sharpe improvement."
**xai:** "Postponing correlation matrix increases drawdown risk. Essential for protecting early live capital."
**cerebras:** "Move Position-sizing to Phase 4 is acceptable IF correlation matrix moves to Week 2."

→ **Action required:** Correlation matrix + adaptive stops move from Phase 4 → Phase 3 (Week 2).

---

## Engine-Specific High-Impact Findings

### deepseek (harshest, most quantitative)
**CRYPTO may be statistically non-viable:**
- n_eff correction: CRYPTO n=8011 with ρ≈0.4-0.6 → n_eff ≈ 200-400
- 95% CI on WR with n_eff=300: [41%, 52.5%]
- WR=46.7% is NOT statistically different from 50% (z=-1.14, p=0.25)
- **Conclusion: CRYPTO may be a coin flip disguised as a system**

**BOND is effectively dead:**
- n=11 with n_eff≈8 → 95% CI on PF is [0.3, 1.4]
- Accumulation rate: 11 trades in ~6 months → T2 requires 4.5 more years at this rate
- **Action: Accept BOND is 2+ years from viability; reallocate resources**

**FOREX LONG hard filter (not just source penalty):**
- Removing LONG picks entirely → FOREX PF potentially 1.2-1.4 based on SHORT PF=8.11
- Deepseek recommends this as a HARD FILTER, not a score penalty

**Shadow deployment before $500:**
- Run strategies in paper mode for 30-60 trading days before first dollar
- Validates slippage assumptions + execution latency
- "First $500 live is reckless without this step"

### xai (most systematic)
**Stress testing gap:**
- No stress testing or tail-risk scenarios (2008/2020 equivalents)
- Neither document mentions this — leaves live strategies vulnerable
- Specific risk: COMMODITY and CRYPTO in extreme vol events

**Symbol universe expansion urgency:**
- BOND n=11 and ETF n=106 (barely above floor) are blocked by missing symbols
- Must accelerate alongside Phase 2 deliverables or T2 timelines slip

### cerebras (most detailed per-class)
**COMMODITY action: `commodity_carry_momo` factor + WFA**
- Expected: +0.30 PF → PF ≈ 2.80 (already T1 territory)
- Wire the factor AND run WFA before declaring T2

**EQUITY action: WFA + regime-conditional weighting**
- Expected: +0.20 PF → PF ≈ 1.77, WR ≈ 55%
- Currently borderline T2; regime switching is the lever

**FOREX action: LONG penalty + trailing stops**
- Expected: +0.30 PF → PF ≈ 1.10 minimum
- Adaptive stops specifically address the "30% equity drawdown" risk from static SL in FX

---

## Revised Priority Stack (post-swarm consensus)

| Priority | Action | Effort | Expected impact | Risk if skipped |
|----------|--------|--------|-----------------|-----------------|
| **P0** | Feature leakage purge (drop strat_fwd_wr, retrain) | 2-3d | +9.21pp CV lift; fixes all gate verdicts | Contaminated data, false confidence in PF |
| **P0** | Transaction cost engine (move to Phase 2) | 1-2w | COMMODITY PF 2.49→~2.0; makes LIVE_ELIGIBLE computable | First $500 trade loses money from friction |
| **P1** | COMMODITY walk-forward (start NOW) | 3-5d | OOS validation; if WFA delta <0, delays $500 | Deploying on possible supercycle overfit |
| **P1** | Effective-N computation all classes | 1-2d | CRYPTO may be invalidated (n_eff≈300); BOND confirmed dead | False confidence on n=8011 |
| **P1** | FOREX LONG hard filter | 0.5d | FOREX PF 0.81→~1.1-1.4 | FOREX stays worst class |
| **P2** | Correlation matrix + adaptive stops (move to Phase 3) | 2-3w | Portfolio Sharpe +30-50%; protects $500 | Cross-class crash hits all picks simultaneously |
| **P2** | 30-60d paper trading before live | setup 1d | Catches 80% of operational issues before real money | Slippage surprise on first real trade |
| **P3** | commodity_carry_momo factor (Phase 3) | 1w | +0.30 PF → PF ≈ 2.80 for COMMODITY | Leaves easy T1 gains on the table |
| **P3** | Position sizing Kelly/HRP (Phase 4) | 3-5w | Sharpe +30-70% vs equal weight | Suboptimal but not catastrophic |
| **P4** | BOND: accept 2+ year timeline, expand universe | ongoing | If can't accelerate, reallocate resources | Continued dead-end effort on n=11 |

---

## Revised LIVE_ELIGIBLE Timeline (post-swarm)

| Class | Original Target | Swarm-Revised Estimate | Gate Condition |
|-------|----------------|----------------------|----------------|
| COMMODITY | 2026-07-15 | 2026-08-15 (+4w) | Add: WFA delta>0 + friction-adjusted T2 + 30d paper |
| EQUITY | 2026-08-15 | 2026-09-15 (+4w) | Same additions |
| ETF | — | 2026-09-30 | n≥150 + WFA |
| CRYPTO | 2026-10-15 | 2026-11-15 (+4w) or INVALIDATE | n_eff check first |
| FOREX | 2026-11-15 | 2026-11-15 (unchanged) | LONG filter + 30d paper |
| BOND | 2026-09-15 | 2028+ (DEAD END) | Accept; reallocate resources |

---

## Overall Grade (from deepseek)
| Dimension | Grade |
|-----------|-------|
| Data integrity | B+ |
| Statistical rigor | C+ |
| Operational readiness | D+ |
| Timeline realism | C |
| Risk management | B- |

**Summary:** Solid B+ plan with a D+ operational readiness gap. The three fixes that matter most: (1) move transaction cost engine to Phase 2, (2) start COMMODITY walk-forward NOW, (3) paper trade 30-60 days before $500 live. Implement these and the plan becomes fund-grade. Skip them and the first live deployment has a 30-40% chance of losing 10-20%.

---

*Generated by swarm: deepseek + xai + cerebras · 2026-05-15 · Run: swarm_runs/run_20260515T042451Z*
