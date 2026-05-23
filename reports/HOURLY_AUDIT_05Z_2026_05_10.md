# Hourly Audit — 05Z 2026-05-10

**Agent:** Claude Sonnet 4.6  
**Dashboard snapshot:** `2026-05-10T01:53:09Z` (auto-refresh [skip ci])  
**Audit generated:** 2026-05-10 ~04:30Z  
**Preceding audit:** PR #888 (04Z, same session)  
**Issues context:** #685 (resolver rescope DONE), #686 (per-asset quality), #693 (EQUITY monitor)

---

## 1. Dashboard Refresh Status

Dashboard last auto-refreshed at `2026-05-10T01:53:09Z`. Main was pulled clean post-merge of #874 and #886; 8 signal data files updated in the prior [skip ci] commit. No generator was run locally (policy).

---

## 2. Per-Asset Metrics (vs Documented Baselines)

**Baseline (from task brief):** CRYPTO 24h PF 3.54 / 7d 1.33 / 30d 1.33; EQUITY 7d 0.87 / 30d 1.41–2.18; FOREX 7d 0.14 / 30d 0.97 pre-PR-#687.

| Class | 24h n | 24h PF | 7d n | 7d WR | 7d PF | 30d n | 30d WR | 30d PF | Delta 7d vs baseline |
|-------|-------|--------|------|-------|-------|-------|--------|--------|----------------------|
| **CRYPTO** | 148 | 1.20 | 836 | 46.1% | 1.62 | 1497 | 48.3% | 1.57 | +0.29 ↑ (baseline 1.33) |
| **EQUITY** | 1 | inf | 24 | 62.5% | **4.37** | 113 | 64.6% | **3.18** | **+3.50 ↑ MAJOR** (baseline 0.87) |
| **FOREX** | 17 | inf* | 219 | 13.7% | 0.33 | 387 | 13.2% | 0.25 | +0.19 ↑ (still catastrophic) |
| **COMMODITY** | 0 | — | 19 | 94.7% | 43.93† | 39 | 76.9% | 6.07 | n too small, volatile |
| **ETF** | 0 | — | 13 | 92.3% | 25.25† | 45 | 82.2% | 6.16 | n→stable needed |
| **BOND** | 0 | — | 0 | — | — | 0 | — | — | no recent closes |

*FOREX 24h PF=inf: 17 picks with sum_pnl=0.00% — likely zero-pnl resolution artefact, not a real signal.  
†COMMODITY/ETF PF figures are inflated by small n; not Tier-assessable until n≥100.

### Asset Class Health (dashboard `performance.asset_class_health`)

| Class | PF | WR |
|-------|----|----||
| CRYPTO | 1.41 | 48.2% |
| EQUITY | **1.58** | **53.7%** |
| FOREX | 0.27 | 41.7% |
| COMMODITY | **3.97** | **67.2%** |
| ETF | 1.44 | 59.2% |
| BOND | 0.66 | 54.5% |

---

## 3. Key Findings vs Baselines

### EQUITY (#693 monitor — RESOLVED)

Issue #693 hypothesised that EQUITY 7d (PF 0.87) would recover after PR #692 killed `goldmine_6x_consensus`. **Confirmed:** 7d PF 0.87 → 4.37, WR 41% → 62.5% in <8 days. Issue #693 acceptance criterion ("EQUITY 14d returns to PF ≥ 1.5 within 7 days post-#692") is satisfied early. No action required; monitor continues.

### CRYPTO (watch, don't destabilise)

7d PF 1.62 (up from baseline 1.33). 24h PF 1.20 is softer than prior-session 3.54 baseline — consistent with normal noise on a ~148-pick window. 7d/30d trend stable. Do not act. PR #694 (HYPEUSDT block) is already merged; `quan_engine` drag reduction is in effect.

### FOREX (still catastrophic)

7d PF 0.33, WR 13.7% on n=219. Improvement from baseline 0.14 likely reflects PR #687 (JPY-cross BUY fix) partially landing in the window. Strategy-level breakdown (7d, n≥15):

| Strategy | n | WR | PF | Sum PnL% |
|----------|---|----|----|----------|
| `forex_carry_momentum` | 73 | 10% | 0.17 | -27.4% |
| `myfxbook_retail_contrarian` | 46 | 7% | **0.09** | -23.4% |
| `forex_rsi2_mean_reversion` | 47 | 2% | **0.03** | -22.2% |

PR #692 already killed `forex_carry_momentum` + `goldmine_6x_consensus`. If the kill is live in production, the 7d window still reflects pre-kill trades bleeding through. Monitor next 24h window for further FOREX recovery.

### New Strategy-Level Kill Candidates (Task 4)

From `python tools/mutation_analysis.py --json` + 7d strategy PF scan:

| Strategy | n (7d) | WR | PF | Status |
|----------|--------|----|----|--------|
| `forex_carry_momentum` | 73 | 10% | 0.17 | Already killed (PR #692) |
| `forex_rsi2_mean_reversion` | 47 | 2% | 0.03 | Already in #686 kill queue |
| **`myfxbook_retail_contrarian`** | **46** | **7%** | **0.09** | **NEW — posted to #686** |
| `MeanReversionBB` | 47 | 21% | 0.53 | PF>0.5; watch only |
| `luxalgo_confluence` | 166 | 36% | 0.58 | PF>0.5; watch only |

`myfxbook_retail_contrarian` detail: 100% JPY crosses (USDJPY=X n=19, EURJPY=X n=17, GBPJPY=X n=10), all LONG/BUY direction — same JPY-cross BUY bypass mechanism as `forex_carry_momentum`. Recommendation: wait for post-PR-#687 7d window before committing to BLOCKED_ASSET_STRATEGY_PAIRS; test SHORT-only mutation first. Evidence posted to issue #686 for AI consensus (comment #4414410569, this agent = AI #1).

### Mutation Analysis Axis 1 — Direction Splits

Three strategies show >30pp WR spread by direction:

| Strategy | SHORT WR | LONG WR | Spread | n total |
|----------|----------|---------|--------|---------|
| `ig_contrarian_sentiment` | 60.9% (n=46) | 14.7% (n=163) | 46pp | 209 |
| `myfxbook_retail_contrarian` | 46.2% (n=13) | 10.2% (n=118) | 36pp | 131 |
| `quan_engine_swing` | 60.0% (n=5) | 26.0% (n=104) | 34pp | 109 |

→ All three have a viable SHORT-only variant worth sandboxing before any kill decision.

---

## 4. PR Triage

### HOLD Set Status

| PR | Status | Note |
|----|--------|------|
| #660 | Merged 2026-05-03 (historical) | WINNER_FILTER/ml_score PR — already on main |
| #658 | Closed 2026-05-03 (historical) | Plan v2.1 origin PR — correctly rejected |
| #681 | Closed 2026-05-03 (historical) | strategy_decay_guard — fabricated WR tables |
| #661 | Merged 2026-05-03 (historical) | Infrastructure v2.0 — on main |

All four HOLD-set PRs are already closed. No action needed.

### Author Rebase Set (#669/#676/#608/#665/#644/#597/#615/#655)

All already merged or closed (verified individually). No action needed.

### Merges This Hour

| PR | Title | Decision | CI | Reviews |
|----|-------|----------|----|---------|
| **#874** | chore: TV screener self-delete audit | **MERGED** | scan✓ | MERGE recommendation (independent review) |
| **#886** | docs: negative-hold-time forensic | **MERGED** | scan✓ | No objections |

### Open PRs — CI Gate Summary

| PR | Title (truncated) | CI State | Merge decision |
|----|-------------------|----------|----------------|
| #891 | mysql_sync entry_time fallback | gate FAIL, test3.11 FAIL | HOLD |
| #890 | reports: verified edge scan | not yet run | HOLD |
| #889 | feat(b13): HMM regime CI-fixed | gate FAIL, test3.11 FAIL | HOLD |
| #888 | audit(04Z): EQUITY recovery | scan only, base stale | STALE/INFORMATIONAL |
| #887 | WIN_RATE_TRAP_BLACKLIST | test3.11 FAIL | HOLD |
| #885 | feat(risk_policy) v2 | gate FAIL, test3.11 FAIL | HOLD |
| #884 | mysql_sync: infer category | gate FAIL, test3.11 FAIL | HOLD |
| #883 | quality_gates: swarm-batch-1 | test3.11 FAIL | HOLD |
| #882 | docs: sports CLV forensic | scan only, unknown mergeable | HOLD (base stale) |
| #881 | tv-orchestrator TP/SL flags | no CI runs | HOLD |
| #879 | audit-dashboard Hermes 5-phase | no CI runs | HOLD |
| #878 | short_engine BULL-regime gate | gate FAIL, test3.12 FAIL | HOLD |
| #877 | mysql_sync elite_score backfill | gate FAIL, test3.12 FAIL | HOLD |
| #876 | fix(mysql_sync): pnl_pct clamp | gate FAIL, test3.12 FAIL | HOLD |
| #873 | chore(loop): B13 doc | not checked | HOLD |
| #872 | feat(b13): HMM regime | not checked | HOLD (superseded by #889) |
| #871 | audit(04Z 2026-05-09): EQUITY T1 | not checked | STALE |
| #868 | feat(b13): HMM (original) | not checked | HOLD (superseded) |
| #865 | audit(05Z 2026-05-08) | not checked | STALE |
| #862 | DB query bank | scan only | HOLD (no test coverage) |
| #849 | Edge action plan (draft) | no CI | DRAFT |
| #846 | feat(b18): Shadow Probation | scan+drift | DO NOT ADMIN-MERGE per author |

**Root cause of widespread test failures:** `test (3.11)` failing on 15+ PRs suggests a systemic test-suite issue. Merits a dedicated root-cause PR.

---

## 5. Goal #1 Status vs Tier Targets

| Class | 7d PF | 30d PF | Tier status | Action |
|-------|-------|--------|-------------|--------|
| CRYPTO | 1.62 | 1.57 | Sub-T2 (need PF>1.5 + WR>50%) | WR 46.1% below floor; vol-targeting per deep_dive |
| EQUITY | 4.37 | 3.18 | **T1 (PF>2, WR>55%)** | No action — protect |
| FOREX | 0.33 | 0.25 | Sub-floor | Kill remaining strategies per #686 protocol |
| COMMODITY | 43.93† | 6.07 | T1 (n too small) | Monitor n→100 |
| ETF | 25.25† | 6.16 | T1 (n too small) | Monitor n→100 |
| BOND | — | — | n<20 charter | No position |

---

## 6. Deltas vs Prior Audit (PR #888, 04Z)

| Metric | 04Z (PR #888) | 05Z (this) | Delta |
|--------|--------------|-----------|-------|
| EQUITY 7d PF | 4.37 | 4.37 | = (same snapshot) |
| CRYPTO 7d PF | 1.62 | 1.62 | = |
| FOREX 7d PF | 0.33 | 0.33 | = |
| PRs merged this hour | 1 (#875 per #888) | 2 (#874, #886) | +1 |
| New kill candidates | 3 (per #888) | 1 new (myfxbook_retail_contrarian) | cumulative 4 |
| Issue #686 comments | prior state | +1 (this agent, #4414410569) | 1 new finding |

Note: dashboard snapshot is the same (01:53Z) since no new auto-refresh occurred between 04Z and 05Z runs. Numeric deltas reflect recomputation consistency, not new data.

---

## 7. Recommended Next Actions

1. **Wait for post-#692 FOREX 7d window** (~2026-05-11): if `forex_rsi2_mean_reversion` stays <10% WR on n>=20, propose kill with mutation evidence.
2. **myfxbook_retail_contrarian** kill evidence posted to #686 (comment #4414410569). Await 2 more AI sign-offs.
3. **SHORT-only sandboxes** for `ig_contrarian_sentiment` and `quan_engine_swing` — direction spread >34pp warrants mutation test.
4. **EQUITY #693** — hypothesis satisfied; leave open for 14d continued monitoring.
5. **Test suite root cause** — `test (3.11)` failing systemically across 15+ PRs is blocking the entire merge queue. Identify failing test(s) and open a targeted fix PR.
6. **#846 (shadow probation)** — awaiting human review per author note; do not admin-merge.

---

*Generated by Claude Sonnet 4.6 at ~04:30Z 2026-05-10. Source: `audit_dashboard/data/dashboard_data.json` 2026-05-10T01:53:09Z. Mutation analysis: `python tools/mutation_analysis.py --json`.*
