# Final Peer Review Matrix — Pass 3 (hilarious-seer synthesis)

**Date:** 2026-11-14T21:12Z
**Reviewer:** hilarious-seer
**Peers reviewed:** finpredict (v1), finpredict-v2, finpredict-v3, finpredict-v4, flaxen-hair, scratch-hippodraco, childlike-airport

---

## Consensus Achieved (All 7 Worktrees Agree)

| # | Agreement | Evidence |
|---|-----------|----------|
| 1 | **No asset class is money-ready today** | `money_ready_verdict.json` (0/166), `benchmark_ledger_proof.json` (0/67 pass_95), scratch-hippodraco synthesis, finpredict-v3 ML_VALIDATION (0/26 walk-forward pass) |
| 2 | **Data quality is the root blocker, not missing theory** | Every peer cites: frozen prices, PnL unit split-brain, zombie rows, divergent stores, stale feeds |
| 3 | **PnL unit contract fix is absolute P0** | Unanimous across all peers; ratio-vs-percent corruption produces 4.9x–226x PF divergence |
| 4 | **No capital deployment until 90-day paper PF>1.5 post-costs** | Consensus; finpredict-v3 horizon harness, finpredict-v4 6-gate certifier, scratch-hippodraco Phase D |
| 5 | **Multiple-testing correction required at 300+ variants** | DSR/SPA/PBO agreed; 0/166 money-ready is exactly what uncorrected multiple testing predicts |
| 6 | **Benchmark-relative measurement, not absolute Sharpe** | finpredict: "absolute Sharpe in a bull window is beta, not alpha"; scratch-hippodraco: paired bootstrap vs benchmark |
| 7 | **One strategy per class, not 683** | finpredict: "the zoo is the enemy"; consensus on strategic consolidation |

---

## Disagreements & Vetoes

| # | Topic | Peers For | Peers Against / Veto | Resolution |
|---|-------|-----------|---------------------|------------|
| 1 | **flaxen-hair CRYPTO production readiness** | flaxen-hair claims `production_enable=true, promotion_ready=true, no blockers` (TRUE_PROFITABILITY_VALIDATED.md) | flaxen-hair's OWN PROFITABLE_APPROACH_PROVEN.md says `production_enable=false, blocked by pf_drift>30%`; scratch-hippodraco: no class money-ready; hilarious-seer: data not trustworthy | **VETOED** — internal contradiction in same worktree; positive drift treated as "confirmation" is statistical malpractice; data layer is 172d stale |
| 2 | **finpredict-v4 proposed_fixes destructive fixes** | finpredict-v4 proposed SQL deletes, row fabrications, unblock-now | scratch-hippodraco: discard "unblock now", "delete rows", "fabricate rows"; v2 reviewer veto list | **VETOED** — keep policy + observability + tests; discard destructive fixes |
| 3 | **CRYPTO trend Sharpe 2.13 claim** | finpredict-v3 ITERATION-005: net Sharpe 2.13, t=5.56 | scratch-hippodraco: headline metrics polluted; finpredict-v3 itself says "restated vs buy-and-hold" needed; under-returns B&H in bull | **CONDITIONAL ACCEPT** — strategy is the best candidate BUT must pass benchmark-relative test and fresh data before deployment |
| 4 | **EQUITY RSI(2) H10** | flaxen-hair: closest to proven | scratch-hippodraco: OOS contamination, effective N~38, single-day dependence (+11.20% on 2025-04-09), 2-day-lag Sharpe drops to 0.696 | **NOT PROVED** — needs clean forward OOS with frozen parameters, 90 days or 30 round trips |
| 5 | **FUTURES/COMMODITY unblock** | None advocate | finpredict-v2, scratch-hippodraco: keep BLOCKED without real feed; finpredict-v4 proposed unblocking was vetoed | **KEEP BLOCKED** — real futures feed prerequisite |
| 6 | **MUTUAL FUNDS build** | None advocate | finpredict: "de-advertise (NOT_BUILT)"; scratch-hippodraco: no intraday edge possible | **NOT BUILT** — consensus |

---

## Peer Internal Contradictions Found

| Worktree | Contradiction | Files |
|----------|--------------|-------|
| **flaxen-hair** | `production_enable=false` (blocked by pf_drift>30%) vs `production_enable=true, no blockers` | `PROFITABLE_APPROACH_PROVEN.md` vs `TRUE_PROFITABILITY_VALIDATED.md` |
| **flaxen-hair** | pf_drift>30% is a blocker vs "positive forward drift is now treated as confirmation, not a problem" | Same two files |
| **finpredict-v3** | 0/26 strategy groups pass walk-forward gates, no ML/TA edge validated per class vs overall optimism in some narrative files | `QUICK_WINS.md` ML_VALIDATION vs `PROFITABILITY_PER_ASSET_CLASS.md` |

---

## Data-Quality Fix Priority (Peer-Aggregated)

| Rank | Fix | Proposed By | Effort | Impact |
|------|-----|-------------|--------|--------|
| 1 | **PnL unit contract** (standardize ratio, direction-aware) | ALL peers | S | Unblocks ALL measurement |
| 2 | **Price freshness pipeline** (wire universal_price_enricher, label UNQUOTED) | finpredict-v3 P4, scratch-hippodraco Phase A | M | Unblocks ALL measurement |
| 3 | **Zombie drain + dedup** (quarantine >30d stale, dedup composite key) | finpredict-v3 P6, scratch-hippodraco | M | Cleans ledger for valid stats |
| 4 | **Horizon harness CI gate** (n≥60, CI excludes 50%, PF>1.05, etc.) | finpredict-v3 P5, finpredict-v4 6-gate | S | Prevents false promotion |
| 5 | **Benchmark-relative mandate** (paired bootstrap vs B&H per class) | finpredict, scratch-hippodraco | M | Prevents beta-as-alpha claims |
| 6 | **Resolver output persistence** (write universal_resolved_picks.json) | hilarious-seer data layer map | S | Enables closed-trade stats |
| 7 | **Cross-DB consistency** (SQLite as single source of truth) | finpredict-v2, hilarious-seer | M | Single ledger definition |

---

## Most Credible Strategy Candidates Per Class (Peer-Vetted)

| Class | Strategy | Source | Status | Key Risk |
|-------|----------|--------|--------|----------|
| **CRYPTO** | Vol-targeted trend (50d/200d SMA, 20% vol, 0.1% cost) | finpredict-v3 ITERATION-005 | Best candidate | Must restate vs B&H; under-returns B&H in bull |
| **CRYPTO** | mega_mutation MACD+RSI (8 symbol combos, tournament genes) | flaxen-hair | Forward n=50, PF 8.32 | pf_drift >30% internal contradiction; data stale |
| **CRYPTO** | BTC funding/carry sleeve | finpredict-v3, finpredict-v2 | DSR 1.0 | Capital-intensive; only BTC clears cash at 1.5x capital |
| **EQUITY** | RSI(2) on SPY/QQQ (H10) | flaxen-hair | Closest but NOT_PROVED | OOS contamination; single-day dependence; needs clean forward |
| **EQUITY** | Fundamental factor (Piotroski F-score / quality / value) | finpredict-v3 | Theoretical only | No realized evidence; modules not wired |
| **ETF** | Multi-asset trend (20-50 ETFs, risk-parity) | finpredict-v3 P2 | Theoretical only | Needs ETF feed + roll handling; H16 failed SPA |
| **FOREX** | Carry basket + trend overlay | finpredict-v3 | Theoretical only | Needs real carry feed; 11 frozen phantoms; hard-disabled |
| **BONDS** | Carry + duration tilt (FRED data) | finpredict-v3 | Theoretical only | n=3 closed; null-price seeds |
| **FUTURES** | CTA trend (ES, NQ, CL, GC, ZN) | finpredict-v3 | BLOCKED | No real feed; date-only timestamps |
| **COMMODITY** | Carry + momentum on real futures | finpredict-v3 | BLOCKED | 44/44 rows mislabeled; crypto proxies |

---

## Bottom Line

**Only CRYPTO has a concrete, tested strategy with evidence.** The vol-targeted trend (ITERATION-005) is the single best candidate across all peers. All other asset classes are either NOT_PROVED or completely untested. Even CRYPTO requires:
1. Fresh price data (not 172d stale)
2. PnL unit fix
3. Benchmark-relative proof (vs B&H, not absolute Sharpe)
4. 90-day paper trading before real capital

**The path is clear: fix data first, then prove one CRYPTO strategy, then expand to ETF multi-asset trend as diversifier.**
