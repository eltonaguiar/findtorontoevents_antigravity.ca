# Hourly Audit — 2026-05-21 13Z

**Audit time:** 2026-05-21T13:13Z  
**Dashboard snapshot:** `2026-05-21T12:18:29Z` (n=3500 recent_closed; cron refreshed as expected ~12:20Z)  
**Session:** Claude Sonnet 4.6 hourly audit  
**Predecessor:** reports/HOURLY_AUDIT_2026-05-21_12Z.md

---

## Dashboard Refresh Status

Snapshot updated to 12:18:29Z — cron ran on schedule (~12:20Z). This is the first 13Z computation against fresh data (+2h newer than 12Z audit which used 10:19Z snapshot).

---

## Per-Asset Windows (computed at 13Z from 12:18:29Z snapshot)

| Class | 24h n | 24h PF | 7d n | 7d PF | 7d WR | 30d n | 30d PF | 30d WR |
|-------|-------|--------|------|-------|-------|-------|--------|--------|
| CRYPTO | 90 | 2.959 | 917 | 1.414 | 48.1% | 2,696 | 1.320 | 45.8% |
| EQUITY | 8 | 2.321 | 46 | 0.803 | 37.0% | 151 | 1.431 | 45.0% |
| FOREX | 8 | 1.460 | 17 | 1.083 | 35.3% | 94 | 2.576 | 48.9% |
| COMMODITY | 2 | 4.016 | 42 | 0.227 | 9.5% | 77 | 1.005 | 41.6% |
| ETF | 0 | — | 11 | 1.322 | 27.3% | 47 | 2.121 | 59.6% |
| BOND | 1 | 0.000 | 4 | 0.000 | 0.0% | 4 | 0.000 | 0.0% |

### Long-run asset_class_health (post-resolver-v2, from dashboard payload)

| Class | PF | WR | Status |
|-------|-----|-----|--------|
| FOREX | 2.900 | 54.9% | T1-candidate; post-#687 sustained |
| COMMODITY | 1.422 | 52.5% | 7d crisis (pre-kill tail picks) |
| CRYPTO | 1.356 | 48.1% | T2 candidate |
| ETF | 11.995 | 50.0% | n too small for sizing |
| EQUITY | 0.703 | 35.7% | sub-T2; 7d monitor continues |
| FUTURES | 0.956 | 16.7% | sub-floor |
| BOND | 0.000 | 0.0% | sub-floor |

---

## Deltas vs 12Z Baseline

Baseline: previous hour (12Z, snapshot 10:19Z).

| Class | Window | 12Z | 13Z | Delta | Signal |
|-------|--------|-----|-----|-------|--------|
| CRYPTO | 24h | 3.191 | 2.959 | -0.23 | Normal variance; >2.5 still strong |
| CRYPTO | 7d | 1.482 | 1.414 | -0.07 | Slight drift; above baseline 1.33 |
| CRYPTO | 30d | 1.373 | 1.320 | -0.05 | Stable |
| EQUITY | 7d | 0.803 | 0.803 | 0.00 | Unchanged; sub-T2 persists |
| EQUITY | 30d | 1.431 | 1.431 | 0.00 | T2-floor stable |
| FOREX | 7d | 1.097 | 1.083 | -0.01 | **12th consecutive hr >=1.0 post-#687** ✅ |
| FOREX | 30d | 2.591 | 2.576 | -0.02 | T1-candidate territory |
| COMMODITY | 7d | 0.088 | 0.227 | +0.14 | Marginal improvement; still crisis |
| COMMODITY | 30d | 0.879 | 1.005 | +0.13 | Near breakeven (tail picks aging) |
| ETF | 7d | 1.322 | 1.322 | 0.00 | Stable |

---

## PR Triage

### Merged this turn
- **#1288** (12Z audit): CI 3/3 green (scan, Gitleaks, DB-grep); Greptile COMMENTED only (no REQUEST_CHANGES); squash-merged ✅

### Open PRs — current state

| PR | Title | CI | Reviews | Action |
|----|-------|----|---------|--------|
| #1289 | feat(B10): UEPS KPI sidecar panel | `test (3.11)` FAILED | Greptile COMMENTED | **HOLD** |
| #1287 | feat(b10): UEPS KPI panel (large files missing) | `test (3.11)` FAILED | Greptile COMMENTED | **HOLD** |
| #1279 | docs: AGENTS.md local tests note | — | — | **HOLD** (DRAFT) |

Note: #1289 and #1287 cover the same B10 feature (UEPS KPI panel) from different sessions. Both have `test (3.11)` failing. Do not merge either until CI is green.

### HOLD set verified absent
#660 #658 #681 #661 — not present in open PR list ✅

### Author-rebase watch
#669 #676 #608 #665 #644 #597 #615 #655 — all previously merged or closed; not in current open PR list ✅

### Plan v2.1 guardrails
No open PRs citing PF 5.81 / ml_score 0.90 / WINNER_FILTER ✅  
No resolver-rescope PRs (issue #685: DONE) ✅

---

## COMMODITY Crisis Detail (13th consecutive hour)

### Strategy breakdown — 7d window

| Strategy | n (7d) | WR | PF | n (all-time) | WR (all-time) | PF (all-time) | Kill gate |
|----------|--------|----|----|--------------|---------------|----------------|-----------|
| `cftc_cot_commercial_signal` | 23 | 8.7% | 0.351 | 56 | 53.6% | 1.653 | dedup-only (PR #683); NOT hard-killed |
| `futures_momentum` | 17 | 11.8% | 0.087 | 18 | 11.1% | 0.086 | BLOCKED for FUTURES only; **COMMODITY gap** |
| `futures_bb_mean_reversion` | 2 | 0.0% | 0.000 | 3 | 0.0% | 0.000 | n<20 floor |

### Critical finding: two kill gaps

**Gap A — `futures_momentum` x COMMODITY:**  
`BLOCKED_ASSET_STRATEGY_PAIRS` contains `("FUTURES", "futures_momentum")` (re-blocked 2026-05-19, H-005). COMMODITY class is **not covered**. This strategy is emitting active COMMODITY picks. All-time PF=0.086 on n=18 — catastrophically bad. At current pace, will hit n=20 kill threshold within ~24-48h.  
Action needed: add `("COMMODITY", "futures_momentum")` to `BLOCKED_ASSET_STRATEGY_PAIRS` once n>=20 and 3-AI consensus met. Currently 1/3 AI votes (this audit). **n=18 < 20 threshold — hold.**

**Gap B — `cftc_cot_commercial_signal` x COMMODITY:**  
PR #683 added `cftc_cot_commercial_signal` to `COT_DEDUP_SYSTEMS` (72h dedup window), not to `BLOCKED_SOURCE_SYSTEMS` or `BLOCKED_ASSET_STRATEGY_PAIRS`. Long-run n=56 PF=1.653 is inflated by pre-dedup spam (one pick per symbol per cron run, ~24x per day before dedup). Post-dedup 7d WR=8.7% is likely the true signal. FINDING-48 remains active: this strategy needs hard-kill or a per-class block, pending 2nd + 3rd AI vote.

### Symbol attribution — 7d COMMODITY crisis

| Symbol | n | WR | Sum PnL% | Class |
|--------|---|----|----------|-------|
| SI=F (Silver) | 9 | 0.0% | -39.82% | precious metal |
| CT=F (Cotton) | 14 | 21.4% | -21.54% | soft commodity |
| PL=F (Platinum) | 6 | 0.0% | -18.00% | precious metal |
| ZS=F (Soybeans) | 7 | 0.0% | -15.18% | grain |
| ZW=F (Wheat) | 3 | 0.0% | -13.37% | grain |
| KC=F (Coffee) | 2 | 0.0% | -10.46% | soft commodity |
| HG=F (Copper) | 1 | 100.0% | +0.01% | base metal |

Precious metals and grains are 0% WR across the board. Broad commodity weakness is a regime signal, not a single-symbol fluke.

---

## EQUITY 7d Sub-T2 Analysis

7d EQUITY strategy breakdown (post-#692 goldmine_6x kill):

| Strategy | n | WR | PF | Sum PnL% | Note |
|----------|---|----|----|----------|------|
| `stocks_rsi2_pullback` | 29 | 44.8% | 1.287 | +13.47% | **Recovering** from 35.7% (issue #686) |
| `vol-contraction-scout` | 3 | 33.3% | 1.109 | +0.97% | n<20 |
| `rs-breakout-scout` | 3 | 0.0% | 0.000 | -5.69% | n<20 |
| `stocks_ema_golden_cross` | 2 | 0.0% | 0.000 | -6.83% | n<20 |
| `gap-and-go-stocks` | 1 | 0.0% | 0.000 | -6.83% | n<20 |
| `adx-trend-scout` | 2 | 50.0% | 0.343 | -5.23% | n<20 |
| `macd-hidden-div-scout` | 1 | 0.0% | 0.000 | -6.68% | n<20 |

Issue #693 hypothesis confirmed: post-#692 kill, `stocks_rsi2_pullback` (n=29, dominant) is recovering. 7d composite PF=0.803 is depressed by small-n scouts with single large losses. No new kill candidates (all scouts n<20). Continue monitoring per issue #693 action plan: if EQUITY 14d returns to PF>=1.5 by ~2026-05-28, goldmine_6x kill was sufficient.

---

## FOREX Recovery Confirmation

- 7d PF=1.083, WR=35.3% (n=17) — **12th consecutive hr >=1.0 post-#687** ✅
- 30d PF=2.576 (strong T1-candidate baseline)
- No new JPY-cross BUY rule failures in 7d window
- asset_class_health PF=2.900, WR=54.9% — long-run confirmed T1-territory

Post-#687 recovery is durable. No destabilization warranted.

---

## Mutation Analysis (13Z run)

Results unchanged from 12Z. No new PF<0.5 + n>=20 candidates. Confirmed kill queue:

| # | Finding | Strategy | n | WR | Axis | Votes |
|---|---------|----------|---|----|------|-------|
| FINDING-48 | `cftc_cot_commercial_signal` x COMMODITY | 23 (7d) / 56 all | 8.7% (7d) | Dedup-only; needs hard-kill | 1/3 |
| FINDING-46 | `ig_contrarian_sentiment` LONG | 200 | 16.5% | Axis 1 | 1/3 |
| FINDING-39 | `myfxbook_retail_contrarian` LONG | 124 | 13.7% | Axis 1 | 1/3 |
| FINDING-44 | `quan_engine_swing` LONG | 104 | 26.0% | Axis 1 | 1/3 |
| FINDING-47 | `crypto_mtf_ema_slope_alignment_v1` SHORT | 38 | 31.6% | Axis 1 | 1/3 |
| FINDING-36 | `rapid_fire` x UUSDT | 34 | 0.0% | Axis 3 | 1/3 |
| FINDING-34 | `cta_replicator` x NG=F | 24 | 0.0% | Axis 3 | 1/3 |
| FINDING-45 | `cta_cross_asset_tsmom` LONG | 85 | 29.4% | Axis 1 | P3 watch |

**NEW WATCH (not yet finding): `futures_momentum` x COMMODITY** — n=18, WR=11.1%, PF=0.086.  
Will become FINDING-49 if n reaches 20 with WR<35% sustained. Currently pre-threshold.

---

## Action Items for Next Hour

1. **Monitor `futures_momentum` x COMMODITY n-count** — at n=18, 2 trades from kill threshold. If n>=20 in 14Z snapshot, escalate to FINDING-49 and post to issue #686 for 2nd + 3rd AI consensus.

2. **FINDING-48 escalation** — `cftc_cot_commercial_signal` dedup is not sufficient; 7d post-dedup WR=8.7%. Post to issue #686 requesting Kimi/Copilot/Cursor 2nd + 3rd vote for hard-kill `("COMMODITY", "cftc_cot_commercial_signal")` in `BLOCKED_ASSET_STRATEGY_PAIRS`.

3. **PR #1289 / #1287 CI** — both HOLD on `test (3.11)` failure. If CI goes green next run, re-check reviews and merge.

4. **EQUITY 14d monitor** — check if 14d PF has returned to >=1.0 (issue #693 step 3 gate: >=1.5 by ~May 28).

---

## Refs

- Issues: #685 (resolver: DONE), #686 (live quality, 78 comments), #693 (EQUITY monitor, closed)
- Today's merged PRs: #684 #674 #673 #664 #683 #687 #692 #694 (session-start) + #1288 (this hour)
- Predecessor: reports/HOURLY_AUDIT_2026-05-21_12Z.md
- audit_dashboard/data/dashboard_data.json (snapshot 2026-05-21T12:18:29Z)
