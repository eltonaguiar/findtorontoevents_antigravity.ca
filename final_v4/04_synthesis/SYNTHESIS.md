# Final Synthesis — All Rounds Combined (final_v4)

**Date:** 2026-11-14T21:50Z  
**Synthesizer:** finpredict-v4  
**Inputs:** final_2026_11_14, final_v2, final_v3 (all peers), local uncommitted files, remote GitHub

---

## 1. The Story Arc: From "Broken" to "Testable"

| Round | Status | Key Finding | Honest Assessment |
|-------|--------|-------------|-------------------|
| **final_2026_11_14** | System is broken | 6 P0 root causes identified; 0/9 asset classes money-ready; SHORT bias validated but blocked | "Not profitable" |
| **final_v2** | System is broken, fixable | Per-asset-class pathways; 8 statistical gates defined; risk controls drafted | "Not profitable, but path exists" |
| **final_v3** | System is breakeven, testable | Gap-aware fill fixes CRYPTO to PF~1.0; per-class cost gate implemented; 52 tests pass; EQUITY clears costs | "Breakeven and now measurable" |
| **final_v4** | Ready to test | All peers converged; 2 deployable candidates; 14 bugs catalogued; 8 open questions ranked | "Test or stop" |

**The arc:** We moved from "the system is unprofitable and we don't know why" (final_2026_11_14) → "the system is unprofitable and here's the path" (final_v2) → "the system is breakeven after fixes and here's what to test" (final_v3) → "everyone agrees on the two candidates, the fixes are shipped, now run the experiment" (final_v4).

---

## 2. Peer Convergence Matrix (All Rounds)

| Question | final_2026_11_14 | final_v2 | final_v3 | final_v4 Consensus |
|----------|------------------|----------|----------|-------------------|
| Is the system profitable? | No | No | No (breakeven after fixes) | **No — but testable** |
| How many asset classes viable? | 1 (CRYPTO SHORT) | 1-2 | 2 | **2 (CRYPTO + EQUITY)** |
| Which is Slot 1? | CRYPTO SHORT bias | CRYPTO SHORT bias | Split (EQUITY or CRYPTO) | **CRYPTO (best evidence) / EQUITY (clears costs)** |
| Which is Slot 2? | — | EQUITY MeanRev | The other of Slot 1 | **The other** |
| Is VWAP deployable? | No | No | **REJECTED** | **REJECTED** |
| Is ETF deployable? | No | Pivot or retire | Diversifier only | **Diversifier only** |
| Is FOREX deployable? | No | Paper lane → decide | Not deployable | **Blocked** |
| Is BOND deployable? | No | Retire | INSUFFICIENT_DATA | **Blocked** |
| Is FUTURES deployable? | Blocked by config | Unblock + test | Blocked | **Blocked** |
| Is COMMODITY deployable? | No | Rebuild fundamentals | Blocked | **Blocked** |
| Mutual funds? | — | — | Portfolio ballast | **Portfolio ballast, not trading edge** |
| Number of bugs catalogued | 5 P0 | 5 P0 + data issues | **14 bugs (B1-B14)** | **14 bugs** |
| Code fixes shipped | 6 | 6 | **+4 (gap fill, cost gate, replay, COT test)** | **10 fixes total** |
| Tests passing | Not quantified | Not quantified | **52** | **52** |

---

## 3. The Two Deployable Candidates (Unanimous Agreement)

### Candidate 1: CRYPTO Vol-Targeted Trend (ITERATION-005)

| Attribute | Value | Source |
|-----------|-------|--------|
| Evidence base | Best among all candidates | SubQ matrix: 3.15/5 |
| Peer consensus | Highest | All peers rank top 2 |
| Fixable blocker | Gap-aware stop fill (DEPLOYED today) | quant-audit final_v3 |
| Honest PF after fix | ~1.00 (breakeven, not profit) | quant-audit B3 |
| Positive sub-bucket | POSITION horizon: n=33, WR 69.7%, PF 3.180 | quant-audit focus decision |
| What to kill | CRYPTO SWING (n=243, PF 0.457, -328.6pp) | quant-audit focus decision |
| What to route | `kimi_riseoftheclaw` through intrabar resolver | quant-audit D2 |
| Forward test | Frozen rules, n≥100, PF≥1.3, WR≥55% | All peers agree |
| Timeline | 6-10 weeks for 100 trades | quant-audit |

**Why it's the best candidate:** Large n (1,966 closed), diagnosed fixable defect (stop fills), positive sub-bucket visible, and the gap-aware fix is already deployed.

### Candidate 2: EQUITY RSI(2) H10

| Attribute | Value | Source |
|-----------|-------|--------|
| Cost structure | **Only class clearing 3× round-trip cost** | quant-audit focus decision |
| Mean per trade | +0.323% | quant-audit |
| Losses inside plan | 0.91× (stops respected) | quant-audit |
| Best exit bucket | TIME_EXIT n=220, WR 61.4%, PF 1.988 | quant-audit |
| Statistical significance | t=1.52, p=0.12 (not significant) | quant-audit |
| Second-half decay | PF fell 1.342 → 0.977 | quant-audit |
| Benchmark test | vs SPY total return, not zero | All peers agree |
| Forward test | Frozen params, 90 days / 30 round trips | All peers agree |
| Timeline | ~1 week to set up, then 90 days | quant-audit |

**Why it's the second candidate:** Only class with positive margin. But it may be beta (rising market), not alpha. The SPY benchmark test is critical.

---

## 4. The 14 Bugs (B1-B14) — Consolidated Status

| Bug | Description | Severity | Status | Owner |
|-----|-------------|----------|--------|-------|
| B1 | EXPIRED→WON mislabeling | CRITICAL | Open | All peers |
| B2 | PnL unit mix (ratio vs percent) | CRITICAL | **Fixed** | quant-audit |
| B3 | CRYPTO stop fills 1.54× planned risk | CRITICAL | **Fixed** | quant-audit |
| B4 | 59-86% non-crypto "SL_HIT" exit inside stop | HIGH | Open — deepest bug | quant-audit (new) |
| B5 | `resolution_method` NULL on all 3,500 rows | HIGH | Open | quant-audit (new) |
| B6 | 100× unit bug in MySQL store | FAIL | Open | final_v2 |
| B7 | All 166 strategy cells single-source | CRITICAL | Open | final_v3 |
| B8 | 170 ledgers, 4 pass vs 8.5 expected | CRITICAL | Worse than chance | final_v3 |
| B9 | Three freshness failures (prices 404 since Apr) | CRITICAL | Open | final_v3 |
| B10 | 53 undecisive rows silently 1.5% of ledger | HIGH | Open | final_v3 |
| B11 | FDR gates exist but unverified in main tree | OPEN | Re-check | final_v3 |
| B12 | `readiness.by_class` decorative (all false, yet emits) | FAIL | **Fixed** | quant-audit |
| B13 | 360 workflows, no owner map, schedule collisions | FAIL | Open | final_v3 |
| B14 | Six peer reviews = one dataset read six times | EPISTEMIC | Acknowledged | quant-audit |

**Fixed in final_v3:** B2 (PnL unit), B3 (stop fills), B12 (cost gate)
**Deepest remaining:** B4 (SL_HIT semantics), B8 (worse than chance), B9 (stale prices)

---

## 5. The 8 Open Questions (D1-D8 + I1-I7)

| # | Question | Blocks? | What Would Settle It | Priority |
|---|----------|---------|---------------------|----------|
| D1 | Why do 59-86% of non-crypto SL_HIT exit inside stop? | **YES** | Trail history for ~20 rows/class | P0 |
| D4 | Does any strategy have edge once fills are honest? | **YES** | 100+ post-fix forward trades | P0 |
| D5 | Is EQUITY's +2.9pp margin alpha or beta? | **YES** | 24-month SPY benchmark test | P0 |
| I-1 | Cross-ledger reconciliation (n varies 6×) | **YES** | Published reconciliation job | P0 |
| D3 | Is 4-of-170 an artifact of one benchmark? | Medium | Re-run with different benchmark | P1 |
| I-6 | Bear-market sub-period analysis | Medium | Bear-market window test | P1 |
| D2 | Why does `kimi_riseoftheclaw` overshoot so much? | Medium | Tracker's poll interval/exit branch | P1 |
| D8 | Is `transaction_costs.json` right? | Medium | Measured slippage from fills | P2 |

---

## 6. Synthesis: What We Know vs What We Don't

### KNOWN (High Confidence)

1. **The system was unprofitable** — 0/9 asset classes money-ready, 0/40 edge trials pass, 4/170 ledgers pass vs 8.5 expected by chance.
2. **Stop fills were the main CRYPTO leak** — 1.54× planned risk, 98.8% of class loss, 94% from one system. **Fixed today.**
3. **EQUITY is the only cost-clearing class** — 3.23× round-trip cost, mean +0.323% per trade.
4. **VWAP is refuted** — Sharpe ~1.18, not 3.76; PBO 0.489.
5. **All peers converge on 2 candidates** — CRYPTO + EQUITY.
6. **52 tests pass** on shipped code fixes.
7. **Mutual funds are not a trading edge** — they are the equity risk premium.

### UNKNOWN (Blocking)

1. **Does any strategy have edge after fixes?** — No forward data exists.
2. **Is EQUITY alpha or beta?** — SPY benchmark test not yet run.
3. **What is B4?** — 59-86% of non-crypto SL_HIT may be mislabelled exits.
4. **Are costs right?** — `transaction_costs.json` is hand-maintained; measured slippage may differ.
5. **Does the system work in bear markets?** — All results bull-flattered.

---

## 7. The Unified 90-Day Plan (All Peers Merged)

| Week | Work | Decision Point | Peers Contributing |
|------|------|---------------|-------------------|
| 1 | Fix data pipeline (B1 relabel, zombie drain, stale prices); route `kimi_riseoftheclaw` to resolver; kill CRYPTO SWING | Can we trust the numbers? | quant-audit, hilarious-seer |
| 1-2 | EQUITY 24-month SPY benchmark test; frozen params | EQUITY alpha or beta? | quant-audit, finpredict-v3 |
| 2-3 | Exit semantics fix (B4); per-class cost gate in CI; freshness gates | Can we trust exits? | quant-audit, childlike-airport |
| 4-8 | CRYPTO POSITION forward test begins; frozen rules | Does crypto have signal after fix? | all peers |
| 9-13 | Review forward data against gates; publish trial count | Scale, or wind down | all peers |

**Kill condition (unanimous):** If any candidate fails any Stage-3 gate in paper trading → halt, return to research. No exceptions.

---

## 8. What final_v4 Adds Beyond final_v3

1. **Cross-peer assessment** — formal review of all final_v3 deliverables, identifying unique contributions and gaps.
2. **Uncommitted files audit** — identified `statistical_scoring_framework.py` as potentially redundant with quant-audit's `tools/per_class_cost_gate.py`.
3. **Remote GitHub tracking** — confirmed `feat/stop-fill-cost-gate-final-v3` is pushed but not PR'd; all GHA workflows green.
4. **Story arc documentation** — the progression from "broken" → "fixable" → "breakeven" → "testable" is now explicit.
5. **Merged 90-day plan** — combines quant-audit's week-by-week sequence with hilarious-seer's 47-task todo and finpredict-v3's SubQ ranking.

---

## 9. Final Verdict

**The system is not profitable today. It may never be. But for the first time, it is testable.**

The gap-aware fill fix turned CRYPTO from "unmeasurable" to "breakeven." The per-class cost gate turned the dashboard from "everything emits" to "only cost-clearing classes emit." The 52 tests provide confidence that the fixes work as intended.

**What remains is the experiment:** run CRYPTO POSITION horizon and EQUITY H10 with frozen rules, honest costs, and benchmark-relative gates. If they pass, the system has its first profitable sleeve. If they fail, the honest answer is "stop" — and that answer, too, is valuable.

**The next round (final_v5, if any) should contain only one thing: forward test results.**

---

*Synthesized by: finpredict-v4*  
*Date: 2026-11-14T21:50Z*  
*Inputs: final_2026_11_14, final_v2, final_v3 (all peers), local uncommitted files, remote GitHub*
