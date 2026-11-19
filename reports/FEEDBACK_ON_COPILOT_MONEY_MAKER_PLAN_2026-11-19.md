# Feedback on Copilot Money-Maker Plan (2026-11-19)

**Reviewer:** opencode (Beam Free), worktree `findtorontoevents_antigravity-ca`
**Plan reviewed:** `/home/eaguiar2015/.copilot/session-state/d9b004db-79cc-4f99-b5f6-5418f84ef36f/plan.md`
**Date:** 2026-11-19

---

## 1. Overall assessment

The Copilot plan is **excellent and complementary** to our own review. It is more operationally concrete (specific files, workflows, guardrails) and independently arrived at many of the same conclusions. I endorse it with the modifications below.

## 2. Points of strong agreement

1. **ETF TAA as the only real-money edge** — confirmed by our §17.1–17.3 cross-check. Faber GTAA OOS Sharpe 0.68, CAGR 6.05%, MDD 11.7% (2006–Mar 2025). The deepest external replication in the literature. This is the right real-money allocation.
2. **Crypto as the sandbox, not real money** — agrees with our §18.2 (do not put $2k into short-term crypto trading) and §15.4 (phase identification, not prediction).
3. **Selection alpha is NEGATIVE (−0.276%/trade)** — this is a critical number I did not have (I reported it as "not computed"). This changes the urgency: the system has *negative* selection skill. Everything is a candidate for improvement, not sizing.
4. **Forward test verifies execution honesty, not alpha** — exactly right. The audit3 forward gate (n≥100, PF CI-LB>1.0) is the correct promotion mechanism. Our 60-day ORB backtest (PF 1.53) is promising but unproven.
5. **Prop-firm guardrails** (trailing max-DD 10%, daily loss 3%, consistency rule) — excellent borrow from the prop-firm literature. Should be adopted.
6. **Cost model: assume maker fills or low-fee venue** — agrees with our §9.2 (cost constants inconsistent across 3 modules). The plan's explicit maker-fee assumption is the right approach.
7. **Prediction markets: maker-only** — agrees with the WSJ finding (67-70% of Polymarket users lose; maker cuts P(loss) by 9.3pp). Relevant to our Kalshi modules.

## 3. Critical finding the Copilot plan caught that I missed

### 3.1 Sleeve-claim gap (§2 of the plan)

The Copilot plan identified that `/audit` top_sleeves (`Multi-Timeframe Trend Alignment` 87% WR / PF 11.8, `AuditEnsemble_LONG` PF 10.1, `Price Acceleration Detector` PF 5.9) **do not exist in audit3's 277 strategy cells**. This is a major gap I completely missed. Either:
- A naming/ingestion gap (the sleeves are computed from a different data source than audit3's closed-pick ledger), or
- Sleeve-level survivorship (the sleeves aggregate picks in a way that inflates metrics).

**My recommendation:** This should be the **#1 priority** before anyone sizes on any sleeve. The Copilot plan's "sleeve-reconcile" todo is correct. I suggest adding a specific check: compare the sleeve's underlying pick IDs against the closed-pick ledger. If the picks exist in the ledger but under different strategy names, it's a naming gap (fixable). If the picks don't exist in the ledger, it's survivorship (not fixable, must be flagged UNVERIFIED).

### 3.2 FOREX sleeve `non_crypto_consensus` PF 9.68 vs class PF 0.26

Same pattern — 37× divergence. Classic grade-source divergence. The Copilot plan correctly flags this as SUSPECT.

## 4. Points of disagreement / modification

### 4.1 $2,000 allocation: MES micro-futures vs ETF

The Copilot plan recommends **ETF for real money, CRYPTO for paper sim**. My review (§18.2) recommended **micro futures (MES) on a swing timeframe** for $2,000.

**My reasoning for MES:** No PDT rule, $50 day margin, $1.25/tick, commission ~$1.50/round turn, liquid CME-regulated market, and the project already has futures infrastructure. The ORB backtest (48 trades, PF 1.53, net +$683 over 60 days) provides a concrete, testable edge.

**The Copilot plan's reasoning for ETF:** ETF TAA is the only edge with 20-year robust evidence. At $2k it's implementable with 4-5 commission-free ETFs, monthly rebalance, ~2-5bp cost.

**Resolution:** Both are valid. The choice depends on the user's time commitment:
- **If the user can monitor intraday (2-3 hours/day):** MES ORB (higher potential, higher risk, requires active management).
- **If the user has a day job:** ETF TAA (lower return, near-zero effort, proven edge).

I recommend presenting both as options and letting the user choose based on their time availability. The Copilot plan should add the MES ORB as an alternative for users who can monitor intraday.

### 4.2 PDT rule correction

The Copilot plan correctly notes that the PDT $25k rule was **repealed** (FINRA Notice 26-10, effective 2026-06-04, broker phase-in until 2027-10-20). This contradicts my review (§18.1) which still cited the $25k rule. I need to update my review to reflect this. **My review is now outdated on this point.**

### 4.3 Brazil/Taiwan day-trading base rates

The Copilot plan cites the Brazil futures study (97% of 300-day persisters lose) and Taiwan study (<3% predictably profitable). These are important priors that I did not include. They strengthen the case for **not** day-trading with $2k and instead using the money for ETF TAA or paper trading.

### 4.4 Publication decay (McLean & Pontiff: 26-58% haircut)

The Copilot plan includes this critical caveat that I missed. Any backtested edge should be hair-cut 26-58% post-publication. This means our ORB backtest (PF 1.53) might be PF 0.64-1.13 after publication decay. **This significantly weakens the case for the ORB strategy.**

### 4.5 Crypto funding carry has compressed to 2.7-6%/yr

The Copilot plan notes that crypto funding carry is now ~2.7-6%/yr pre-fee, which is ~$0-80/yr on $2k. This is not worth building for at this size. I did not include this in my review.

### 4.6 Forward-test epistemology

The Copilot plan correctly notes that "a few months of live data cannot confirm a modest edge (SR 1.0 needs ~9 years for t=3)". This is a critical point: our 60-day ORB backtest with 48 trades cannot confirm anything. It can only falsify (if the edge is negative). This aligns with the audit3 philosophy.

## 5. Suggestions for the Copilot plan

### 5.1 Add the sleeve-reconcile as P0, not just a todo

The sleeve gap is the most important finding. If the top_sleeves are survivorship artifacts, then the `/audit` page's headline numbers are misleading and no one should size on them. This should be elevated to P0 (blocks money-readiness), not just a todo item.

### 5.2 Add the ORB backtest results

Our ORB backtest (48 trades, WR 45.8%, PF 1.53, net +$683) should be included in the research doc. The Copilot plan's $2,000 recommendation should mention that MES ORB is a viable alternative for users who can monitor intraday, with the caveat that publication decay may reduce the edge.

### 5.3 Add the volume filter confirmation

Our §8 volume filter test (volume >1.5× 20-bar avg improves PF from 1.40 to 1.53, net +$134) should be included. This is the first empirical confirmation that volume as a filter improves edge — a gap identified in both our review and the Copilot plan.

### 5.4 Add the cost harmonization result

We harmonized OTHER_BP in `forward_observations_ingest.py` to source from `cost_model.py` (single source of truth). The values changed: EQUITY 8→7, ETF 8→3, FOREX 4→2, COMMODITY 12→7, FUTURES 12→5.5, BOND 2→4.5 bps. This should be noted in the research doc.

### 5.5 Add the POD-EQUITY-BREAKOUT fix

We registered 13 actual EQUITY/ETF strategy names in CONDITIONS (was using non-existent names like "donchian-stock-breakout"). Ingest now finds 177 EQUITY rows (was 0). Total ledger 607 rows. This unblocks EQUITY forward testing.

## 6. Recommendation: merge the two plans

The two plans (mine and Copilot's) are complementary. I recommend:

1. **Use the Copilot plan as the primary execution plan** — it is more operationally concrete and has a better $2,000 recommendation (ETF for real money).
2. **Incorporate my findings** — ORB backtest results, volume filter confirmation, cost harmonization, POD-EQUITY-BREAKOUT fix, and the $2,000 MES alternative.
3. **Elevate sleeve-reconcile to P0** — it's the most important finding.
4. **Add publication decay caveat** to all backtested edges (26-58% haircut).
5. **Commit both the Copilot plan and this feedback to GitHub** so Windows agents can review.

## 7. Action items for the Copilot plan

| # | Action | Priority | Owner |
|---|---|---|---|
| 1 | Copy Copilot plan to `plans/` in the repo | P0 | opencode |
| 2 | Commit + push to GitHub for Windows review | P0 | opencode |
| 3 | Elevate sleeve-reconcile to P0 | P0 | copilot |
| 4 | Add publication decay caveat (26-58%) to all backtested edges | P1 | copilot |
| 5 | Add ORB backtest results + volume filter confirmation to research doc | P1 | opencode |
| 6 | Add MES ORB as $2,000 alternative for intraday-capable users | P2 | copilot |
| 7 | Update my review's PDT rule section (repealed) | P1 | opencode |
| 8 | Add crypto funding carry compression (2.7-6%/yr) to research doc | P2 | copilot |

---

*Feedback generated 2026-11-19 by opencode (Beam Free). Companion to: `reports/AUDIT123_COMPREHENSIVE_REVIEW_2026-11-19.md` and `reports/AUDIT_REVIEW_MASTER_TODO.md`.*
