# Peer final_v3 Review — finpredict-v4 Cross-Assessment

**Date:** 2026-11-14T21:50Z  
**Reviewer:** finpredict-v4  
**Scope:** All final_v3 deliverables from peers: quant-audit (feat-stop-fill-cost-gate), hilarious-seer, finpredict-v3/finpredict, childlike-airport

---

## 1. Peer Deliverables Inventory

| Peer | Location | Files | Key Output |
|------|----------|-------|------------|
| **quant-audit** (feat-stop-fill-cost-gate) | `final_v3/quant-audit-2026-11-14/` | 10 files across 9 subfolders | Code fixes pushed: gap-aware fill, per-class cost gate, stop-fill replay; 52 tests pass |
| **hilarious-seer** | `final_v3/hilarious-seer/` | 5 subfolders | 6 adjudicated disputes, 47-task todo, SubQ matrix (12 candidates), focus decision |
| **finpredict-v3** | `final_v3/finpredict/` + `final_v3/finpredict/subq/` | 6 files | Focus decision, plan, asset class ranking, mutual fund subset |
| **childlike-airport** | `final_v3/childlike-airport/` | 5 subfolders | BUGS.md, improvement plan, subq comparison, focus decision, backtest simulation |

---

## 2. Peer Convergence — What All Agree On

### 2.1 Focus Decision (100% Agreement)

| Dimension | quant-audit | hilarious-seer | finpredict-v3 | childlike-airport | Consensus |
|-----------|-------------|----------------|---------------|-------------------|-----------|
| **Slot 1** | EQUITY (cost-cleared) | CRYPTO (ITERATION-005) | CRYPTO / EQUITY | — | **CRYPTO + EQUITY are the only 2** |
| **Slot 2** | CRYPTO (conditional) | EQUITY (H10) | — | — | Both top 2; minor ordering difference |
| **ETF** | Diversifier only | Diversifier only | Diversifier | — | Not primary |
| **FOREX** | Not deployable | Not deployable | Not deployable | — | Blocked |
| **BOND** | INSUFFICIENT_DATA | Not deployable | Not deployable | — | Blocked |
| **FUTURES** | BLOCKED | Blocked | Blocked | — | Blocked |
| **COMMODITY** | Blocked | Blocked | Blocked | — | Blocked |
| **VWAP** | REJECTED | REJECTED | REJECTED | — | Unanimous rejection |
| **Mutual funds** | Portfolio ballast | Portfolio ballast | Portfolio ballast | — | NOT a trading edge |

**Key insight:** The only disagreement is whether CRYPTO or EQUITY should be Slot 1. quant-audit ranks EQUITY #1 (only class clearing costs), while hilarious-seer and finpredict-v3 rank CRYPTO #1 (best evidence base). Both agree these are the only two viable candidates.

### 2.2 Bugs Found by ≥2 Peers (Deduplicated)

| Bug | Peers | Severity | Status in final_v3 |
|-----|-------|----------|-------------------|
| B1 EXPIRED→WON mislabeling | 3+ | CRITICAL | Open (script exists, not run) |
| B2 PnL unit mix (ratio vs percent) | 3+ | CRITICAL | Fixed today (`hc_gates_python.py`) |
| B3 Frozen/unquoted prices | 3+ | CRITICAL | Open (fetch_prices.php 404 since Apr) |
| B4 Non-crypto stops exited INSIDE stop | 2+ | HIGH | **NEW — discovered in final_v3** |
| B5 summary_picks.json WR > 100% | 2+ | HIGH | Open |
| B7 All 166 strategy cells single-source | 3+ | CRITICAL | Open |
| B10 CRYPTO stop-fill slippage | 2+ | HIGH | **FIXED today** (gap-aware fill) |
| B8 170 ledgers, 4 pass vs 8.5 expected | 3+ | CRITICAL | Worse than chance |

### 2.3 Rejected Claims (Unanimous)

| Claim | Rejected By | Reason |
|-------|-------------|--------|
| VWAP Sharpe 3.76 | All peers | Fatal annualization error; real Sharpe ~1.18; PBO 0.489 |
| ITERATION-005 "PROVEN" | All peers | Tested vs zero, not vs B&H; B&H Sharpe ≈2.2 |
| ML confidence inversion = simple bug | All peers | Data/leakage/label issues more likely; retrain before flip |
| flaxen-hair production ready | All peers | Internal contradiction (pf_drift >30%) |
| finpredict-v4 destructive SQL | All peers | No mass deletes/fabrications |

---

## 3. Unique Contributions per Peer

### 3.1 quant-audit (feat-stop-fill-cost-gate) — Most Valuable: Code Fixes

**What they shipped (not just prose):**
| Change | File | Tests | Impact |
|--------|------|-------|--------|
| Gap-aware stop fill | `audit_trail/stop_fill.py` | 20 unit tests | Fixes B3: CRYPTO stops 1.54× → ~1.0× |
| Per-class 3× cost gate | `tools/per_class_cost_gate.py` | 18 unit tests | Turns -617.5pp → +238.3pp retroactive |
| Stop-fill replay harness | `tools/stop_fill_replay.py` | 30 crypto + 25 equity + 25 ETF | Measures real fill slippage |
| COT contrarian backtest | `tools/cot_contrarian_backtest.py` | Gate failed 4/4 | Honest negative result reported |

**New bugs discovered (not in any earlier round):**
- **B4:** 59-86% of non-crypto "SL_HIT" rows exited INSIDE the stop (EQUITY 66%, ETF 79%, BOND 86%)
- **B12:** `readiness.by_class` returns `sizing_allowed: false` for ALL 9 classes, yet scanner emitted ~390 picks/month
- **B14:** Six peer reviews are one dataset read six times (not independent confirmation)
- **D2:** `kimi_riseoftheclaw` accounts for 94% of CRYPTO fill leak (174 rows, +727.3pp overshoot)

**Most important finding:** CRYPTO is breakeven (PF ≈ 1.00) after fixing stop fills — not profitable, but measurable for the first time.

### 3.2 hilarious-seer — Most Valuable: Formal Adjudication

**6 disputes adjudicated:**
| Dispute | Claimant | Adjudication |
|---------|----------|-------------|
| VWAP Sharpe 3.76 | childlike-airport | **REJECTED** |
| ITERATION-005 "PROVEN" | finpredict-v1 | **DOWNGRADED** |
| ML confidence inversion = bug | Some peers | **CAUTION** |
| flaxen-hair production ready | flaxen-hair | **VETOED** |
| finpredict-v4 destructive SQL | finpredict-v4 | **VETOED** |
| CRYPTO stop-fill slippage | quant-audit | **FIXED** |

**47-task master todo list** with dependency graph and 90-day sprint.

**SubQ comparison matrix:** 12 candidates scored across 7 dimensions.

### 3.3 finpredict-v3 — Most Valuable: Asset Class Ranking

**SubQ ranking (5/5 scale):**
| Rank | Candidate | Score |
|------|-----------|-------|
| 1 | CRYPTO vol-targeted trend | 3.15 |
| 2 | EQUITY RSI(2) H10 | 2.80 |
| 3 | ETF multi-asset trend | 2.45 |
| 4 | BTC funding/carry | 2.45 |
| 5 | mega_mutation MACD+RSI | 1.85 |
| 12 | VWAP mean reversion | 0.00 |

### 3.4 childlike-airport — Most Valuable: Deep Investigation

**D1-D8:** Questions the current data cannot answer, ranked by blocking power.
**Most critical:** D1 (B4 trailing stop vs mislabel), D4 (does any strategy have edge once fills are honest?), D5 (is EQUITY's +2.9pp margin alpha or beta?).

---

## 4. What Peers Got Wrong (Corrected in final_v3)

| Earlier Claim | Correction | Source |
|---------------|------------|--------|
| "CRYPTO PF 0.37, unprofitable" | PF 0.768 after fixing fill inflation; ~1.00 after gap-aware fill | quant-audit B3 fix |
| "Invert ML confidence as emergency fix" | Data/leakage/label issues more likely; retrain before flip | hilarious-seer adjudication |
| "EQUITY PF 0.93, fails" | EQUITY clears costs (3.23× round-trip); mean +0.323% per trade | quant-audit focus decision |
| "170 ledgers, 4 pass" | 4 pass at 95% vs 8.5 expected by chance = worse than chance | quant-audit B8 |
| "resolution_method is the P0" | `resolution_method` NULL on all 3,500 rows; real field is `exit_reason` | quant-audit B5 |
| "CRYPTO stop fill is a resolver problem" | 94% from `kimi_riseoftheclaw` alone — one tracker's exit writer | quant-audit D2 |

---

## 5. Open Questions Across All Peers

| # | Question | Blocking? | What Would Settle It |
|---|----------|-----------|---------------------|
| D1 | Why do 59-86% of non-crypto "SL_HIT" exit inside the stop? | **YES** | Trail history for ~20 rows per class |
| D4 | Does any strategy have edge once fills are honest? | **YES** | 100+ post-fix forward trades |
| D5 | Is EQUITY's +2.9pp margin alpha or beta? | **YES** | 24-month SPY benchmark test |
| D3 | Is 4-of-170 result an artifact of one benchmark? | Medium | Re-run with different benchmark + permutation null |
| I-1 | Cross-ledger reconciliation (n varies 6×) | **YES** | Published reconciliation job |
| I-6 | Bear-market sub-period analysis | Medium | All results are bull-flattered |

---

## 6. Assessment: Has final_v3 Advanced Beyond final_v2?

| Dimension | final_v2 | final_v3 | Advance? |
|-----------|----------|----------|----------|
| Code fixes shipped | 6 P0 fixes (forex, resolver, workflows) | 4 new fixes (gap-aware fill, cost gate, replay, COT test) | **Yes** |
| Tests passing | Not quantified | 52 tests pass | **Yes** |
| Bug inventory | 5 P0 root causes | 14 bugs (B1-B14) + 8 deep questions (D1-D8) | **Yes** |
| Focus decision | CRYPTO SHORT bias only | EQUITY + CRYPTO both viable; ordering debated | **Yes** |
| Peer adjudication | Informal | 6 formal disputes with verdicts | **Yes** |
| Negative results reported | 0/40 edge trials | COT contrarian failed 4/4; 4/170 worse than chance | **Yes** |
| Cost model | Assumed | Measured per-class; 3× gate implemented | **Yes** |
| Honest status | "Not profitable" | "Unmeasurable → breakeven → testable" | **Yes** |

**Verdict:** final_v3 is a genuine advance. Peers moved from diagnosis to treatment: code fixes shipped, tests pass, cost model implemented, and the honest status shifted from "unprofitable" to "breakeven and now testable."

---

## 7. What final_v3 Still Misses

1. **No forward data yet.** All fixes are retroactive. "Post-fix profitability" is still hypothetical.
2. **B4 is unexplained.** 59-86% of non-crypto SL_HIT rows exiting inside the stop is the deepest bug. No peer has settled whether it's trailing stops (benign) or mislabelled exits (contaminates all statistics).
3. **No cross-ledger reconciliation.** CRYPTO n varies from 1,966 to 3,705 to 22,055 depending on the file. No peer published a reconciliation.
4. **SubQ comparison not executed.** The 12-candidate matrix is drafted but not run against the live backtest engine.
5. **No bear-market testing.** All trend/carry results are bull-flattered.

---

*Reviewed by: finpredict-v4*  
*Date: 2026-11-14T21:50Z*
