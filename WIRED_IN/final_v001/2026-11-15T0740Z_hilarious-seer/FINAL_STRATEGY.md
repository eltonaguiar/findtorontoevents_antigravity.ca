# FINAL STRATEGY — Finding and Proving Profitable Strategies Per Asset Class
## For findtorontoevents.ca/audit

**Date:** 2026-11-15  
**Worktree:** hilarious-seer  
**Author:** Kilo (senior quant analyst)  
**Based on:** 24-48h digest of ALL_STRATEGIES.md (700+ strategies), BABY_STRATEGIES_AUDIT_INTEGRATION.md (4 new strategies), peer audits (finpredict-summary, flaxen-hair), subagent deep dives (ETF/MF, CRYPTO, PENNY), and recent infrastructure fixes.

---

## Executive Summary

After auditing **700+ strategies** across **7 asset classes** with **~871 total configurations**, the conclusion is unanimous across all peer agents:

> **Zero (0) strategies pass all 10 proof-protocol gates. No asset class has a proven profitable edge.**

However, **three candidates have emerged** as the highest-probability paths to profitability. This document specifies exactly how to prove them, what order to run them in, and how to feed results into `findtorontoevents.ca/audit`.

---

## 1. The Three Highest-Probability Candidates (Ranked)

### Candidate 1: BTC SMA200 + RSI2 Mean Reversion (CRYPTO) — PROMISING
**Why it ranks #1:**
- **BTC sma200** is the ONLY signal in the entire repo that beats buy-and-hold on **terminal wealth** (1.94 vs 1.67 B&H) per the hypothesis-test harness
- Appears in 5 separate engine files as a macro regime filter
- **RSI(2) < 10** mean-reversion overlay is well-documented in equity literature (Connors & Alvarez)
- The combination (RSI2 < 10 + close > SMA200) filters out bear-market false signals

**What must be proven:**
1. Run full 10-gate proof protocol on BTC-USD daily data (Binance/yfinance)
2. Entry: RSI(2) < 10 AND close > SMA200
3. Exit: RSI(2) > 60 OR 5% trailing stop OR 24h time exit
4. Cost model: 0.10% taker fee + 0.05% spread + slippage
5. Target: n >= 100 clean trades, PF >= 1.3, Sharpe >= 0.7 (deflated)

**Reference:** `WIRED_IN/2026-11-15T065338Z_hilarious-seer/CRYPTO_AUDIT.md` (Section 5)

---

### Candidate 2: Asset-Class Momentum Rotation (ETF/MF) — PROMISING
**Why it ranks #2:**
- **In-sample robust 2007-2026**: Sharpe 0.88 vs SPY 0.74, MaxDD -19% vs SPY -51%, Calmar 0.48 vs 0.21
- Positive in ALL three time-thirds (including 2008 GFC)
- Corroborated by two independent constructions (VAA-G4 and PAA1)
- 50/50 Rotation+VAA blend: Sharpe 0.89, MaxDD -16%, Calmar 0.50

**What must be proven:**
1. Pre-register 12-month forward test starting NOW
2. Monthly rebalance: top-5 of 14 asset-class ETFs by 6-month momentum
3. Absolute-momentum filter: if momentum < 0, hold AGG (aggregate bonds)
4. Cost model: 5 bps per trade + ER drag
5. Benchmark: SPY total return
6. Decision threshold after 12 months: Sharpe/Calmar > SPY AND PF >= 1.2

**Reference:** `WIRED_IN/2026-11-15T065338Z_hilarious-seer/ETF_MF_AUDIT.md` (Section 5)

---

### Candidate 3: CEF/BDC NAV Discount Mean Reversion (PENNY/ALT) — PROMISING
**Why it ranks #3:**
- Replaces speculative penny-stock risk with a **measurable, audited accounting variable** (NAV discount)
- Avoids pump-and-dump, delisting, and adverse-selection risks entirely
- 4 new experiments proposed with full 10-gate compliance

**What must be proven:**
1. Universe: CEFs/BDCs trading at >10% discount to NAV with audited NAV data
2. Entry: discount > 10% AND 20d discount widening has reversed
3. Exit: discount < 5% OR 90d time exit
4. Cost model: 40-50 bps spread (typical for CEFs) + commission
5. Liquidity cap: 1% of ADV max position

**Reference:** `WIRED_IN/2026-11-15T065338Z_hilarious-seer/PENNY_STOCK_AUDIT.md` (Section 5)

---

## 2. Asset Classes: Current Verdicts

| Asset Class | Status | Best Candidate | Why |
|-------------|--------|---------------|-----|
| **CRYPTO** | PROMISING | BTC SMA200 + RSI2 | Only wealth-beating signal in entire repo |
| **ETF/MF** | PROMISING | TAA Rotation (top-5, 6m momentum) | Only in-sample robust finding; needs forward test |
| **EQUITY** | CLOSED | None | Post-#773; one pre-registered trial only |
| **FOREX** | FROZEN | None | Bounded 2-mutation protocol; kill is a deliverable |
| **BOND** | BLOCKED | None | PF 0.078 catastrophic; trend filters make it worse |
| **COMMODITY** | DEBUNKED | None | 93.8% WR claim was pre-dedup over-emission artifact |
| **FUTURES** | BLOCKED | None | WR 2.5% on 157 picks empirically dead |
| **PENNY** | PROMISING (ALT) | CEF/BDC NAV discount | Avoids penny-specific risks; uses audited NAV |
| **PREDICTION MARKETS** | SHADOW ONLY | None | PBO=0.603 blocks deployment despite 79% forward WR |

---

## 3. The Proof Protocol (Non-Negotiable)

No candidate may be called "profitable" or deployed to `findtorontoevents.ca/audit` as "money-ready" unless it passes ALL 10 gates:

1. **Temporal discipline:** strict chronological train/test split; features from past data only
2. **Walk-forward optimization:** embedded OOS windows; report walk-forward efficiency >= 50-60%
3. **Multiple-testing correction:** state total configurations tried; apply Bonferroni/Holm; deflated Sharpe p < 0.05
4. **Monte Carlo resampling:** block-bootstrap trade sequences; >= 70% of paths positive after costs; 5th-percentile not catastrophic
5. **Full friction model:** spread + commission + slippage + funding + tax; state breakeven cost and margin of safety
6. **Statistical significance:** bootstrap CI for mean excess return excludes zero at 95%; t-stat >= 2.0
7. **Regime robustness:** positive expectancy in >= 3 of 4 regimes (bull/bear/sideways/high-vol)
8. **Shuffle control:** permuted prices must NOT reproduce performance
9. **Pre-registered forward test:** defined protocol (duration, rules, thresholds) BEFORE any paper/live results
10. **Reproducibility:** fixed seeds, versioned data, documented formulas, runnable code

**Reference:** `WIRED_IN/2026-11-15T065338Z_hilarious-seer/PROOF_STANDARD_METRICS.md`

---

## 4. Implementation Roadmap (Next 90 Days)

### Phase 1: Immediate (Days 1-7)
- [ ] **Fix data quality P0:** Backfill missing `strategy_id`, `excess_vs_benchmark`, `cost_cleared` fields so PE-03 gates don't fail-closed on 100% of picks
- [ ] **Deploy BTC Experiment E1:** Run `CRYPTO_AUDIT.md` backtest code with full 10-gate protocol
- [ ] **Pre-register ETF TAA forward test:** Document exact rules, universe, rebalance dates, decision thresholds in `PROOF_PROTOCOL.md`
- [ ] **Audit dashboard update:** Render `CANDIDATE_NOT_READY` tier and new `badges` list (UNQUOTED, STALE, NULL_FIELD, FABRICATED_FLAT)

### Phase 2: Validation (Days 8-30)
- [ ] **BTC:** Collect n >= 30 trades; compute interim Sharpe/PF; if positive, continue to n >= 100
- [ ] **ETF TAA:** Execute first monthly rebalance; log holdings to `tracker/predictions_tracker.csv`
- [ ] **CEF/BDC:** Build NAV discount scraper; backtest on 5 years of CEF data
- [ ] **Hypothesis harness CI:** Wire `tools/hypothesis_test_harness.py` into `.github/workflows/` as pre-promotion gate

### Phase 3: Decision (Days 31-90)
- [ ] **BTC:** If n >= 100, PF >= 1.3, Sharpe >= 0.7 (deflated), all 10 gates pass → promote to **PROVEN**; start 90-day paper trade
- [ ] **ETF TAA:** After 3 monthly rebalances, compute interim Sharpe/Calmar vs SPY; if trending positive, continue to 12 months
- [ ] **CEF/BDC:** If backtest passes 10 gates, start 90-day paper trade
- [ ] **Dashboard integration:** Wire `best_picks_per_class.json` (29 picks) and `pilot_active_picks.json` (202 picks) into live dashboard HTML/JS

### Phase 4: Live Deployment (Day 91+, conditional)
- [ ] Only if at least ONE candidate passes all 10 gates AND 90-day paper PF > 1.5 post-costs with DSR >= 0.95
- [ ] Capital deployment capped at 5% NAV per strategy
- [ ] Continuous monitoring: if forward Sharpe drops below 0.5 for 30 days, auto-kill per pre-registered rules

---

## 5. What Has Been Tried and Killed (Do Not Repeat)

From `ALL_STRATEGIES.md` (700+ strategies) and peer audits:

| Strategy Family | Count | Result | Failure Mode |
|-----------------|-------|--------|--------------|
| Baby Strategies | 77 | Most unvalidated | No forward evidence |
| Alpha Engine — Core Crypto | 33+ | 9 retired/killed | Catastrophic live data (-810% cum PnL) |
| Alpha Engine — Proven Research | 10 | Unverified claims | External citations only (no repo backtest) |
| ML Battleground — 5 Systems | 5 | All near-zero | ML overfit on small samples |
| Mercury2 / Cerebrus AI | 11 | Unvalidated | No OOS proof |
| Faber Dual-Momentum | 1 | FAIL | AnnRet 9.1% vs SPY 14.7% |
| Connors RSI-2 (SPY) | 1 | ELIMINATED | Total return -12.6% vs SPY +345.7% |
| Copy-Trader (COMMODITY) | 1 | DEBUNKED | Pre-dedup over-emission artifact |
| Prediction Markets | 1 | BLOCKED | PBO=0.603 (6× above 0.10 gate) |
| Rapid Fire × Volume Spike | 1 | KILLED | WR 16.7%, PF 0.014 |

**Key lesson:** The repo's primary failure mode is **testing thousands of configurations without multiple-testing correction**, then reporting the best one as "proven." The 10-gate proof protocol exists specifically to prevent this.

---

## 6. Infrastructure Fixes Required Before Any Deployment

### P0 (Blocks Everything)
1. **PnL unit contract fix** (`sync_all_picks_to_mysql.py`): Remove `%*100` heuristic; add row validation
2. **Blank TP/SL in EQUITY:** 691 of 4,390 picks have blank TP/SL; QA ledger flags these as CRITICAL
3. **Stop-fill bug:** `exit_price = entry_price` produces fabricated flat PnL=0%; fixed in commit `49c945b06cf`
4. **Duplicate picks:** 4,390 raw rows → 185 after dedupe; live tracker now dedupes by `(symbol, direction)`

### P1 (Blocks Confidence)
1. **PE-03 gates fail-closed:** `strategy_id`, `excess_vs_benchmark`, `cost_cleared` missing from most picks → 100% downgraded to `CANDIDATE_NOT_READY`
2. **Dashboard template:** Does not render `CANDIDATE_NOT_READY` tier or `badges` list
3. **Price realism:** `price_realism_check.py` now validates vs live yfinance bounds (not hardcoded prices)

### P2 (Nice to Have)
1. **Polymarket v2 migration:** Complete; 6 crypto markets now active (was 0)
2. **Model picks merge:** `merge_model_picks.py` ensures VTI/BND passive beta picks persist

---

## 7. Operational Setup for Daily Picks → Audit Dashboard

### Recommended Flow

```
1. Daily pick generation (GitHub Actions)
   ↓
   Output: timestamped JSON → picks/2026-11-15/picks.json
   Columns: timestamp, asset, asset_class, strategy_id, direction,
            expected_return, tp, sl, horizon, confidence, regime,
            position_size, data_version, code_version
   
2. Weekly ingestion job
   ↓
   Reads new JSON → validates schema → inserts into trading_picks
   
3. Outcome resolver (when trades close)
   ↓
   Writes to at_pick_outcomes / at_signal_outcomes
   
4. Scoring job
   ↓
   Computes Phase 5 metrics → strategy_performance table
   
5. Audit dashboard
   ↓
   Surfaces ONLY strategies that passed (or are in pre-registered forward test)
```

### Why This Works for Investors
- Pre-registration enforced by Git commit timestamp
- No retroactive pick changes
- Outcomes independently joinable and scorable
- Matches the near-miss rule: parameters frozen; only clock extends

---

## 8. The Honest Negative Result

If after 90 days **no candidate passes all 10 gates**, the honest conclusion is:

> "We tested 871+ configurations across 7 asset classes with rigorous statistical controls. Zero directional strategies survived. The profitable alternative is a disciplined passive allocation (e.g., 60/40 VTI/BND with quarterly rebalancing), which has a measurable, provable expected outcome."

This is **not a failure** — it is a **legitimate, publishable finding** that protects capital and redirects effort efficiently. The audit dashboard can pivot to:
- Current allocation display (instead of active picks)
- Expected risk/return based on historical asset-class data
- Rebalancing alerts when allocation drifts > 5%
- Tax-loss harvesting opportunities

---

## 9. File References

All evidence cited in this document is stored in:

| File | Path |
|------|------|
| This document | `WIRED_IN/final_v001/2026-11-15T0740Z_hilarious-seer/FINAL_STRATEGY.md` |
| ETF/MF Audit | `WIRED_IN/2026-11-15T065338Z_hilarious-seer/ETF_MF_AUDIT.md` |
| CRYPTO Audit | `WIRED_IN/2026-11-15T065338Z_hilarious-seer/CRYPTO_AUDIT.md` |
| PENNY Audit | `WIRED_IN/2026-11-15T065338Z_hilarious-seer/PENNY_STOCK_AUDIT.md` |
| Proof Standard | `WIRED_IN/2026-11-15T065338Z_hilarious-seer/PROOF_STANDARD_METRICS.md` |
| Peer Audit (finpredict) | `WIRED_IN/2026-11-15T0700Z_finpredict-summary/Summary.MD` |
| Peer Shortlist | `WIRED_IN/2026-11-15T0700Z_finpredict-summary/STRATEGY_SHORTLIST.md` |
| Strategy Registry | `docs/ALL_STRATEGIES.md` |
| Baby Strategies | `BABY_STRATEGIES_AUDIT_INTEGRATION.md` |
| Master Plan | `2026-11-15_AM_plan/hilarious-seer/COMPREHENSIVE_PROFITABILITY_RECOVERY_PLAN.md` |

---

## 10. Sign-Off

| Role | Verdict |
|------|---------|
| Lead Quant (hilarious-seer) | Three promising candidates; 90-day proof protocol required; no live capital until gates pass |
| Peer Quant (finpredict-summary) | BTC sma200 only wealth-beating signal; all others rejected; live emission NO-GO |
| Peer Quant (flaxen-hair) | Confirms negative result; PRE_PROMPT.MD deployed |
| Data Quality | P0 blockers identified; PE-01/03/04 fixes implemented; backfill required |
| Governance | No capital deployment until 90-day paper PF>1.5 post-costs with DSR>=0.95 |

---

*Generated by hilarious-seer worktree, 2026-11-15T07:40Z*
*Next review: 30m cron checks + 90-day decision gate*
