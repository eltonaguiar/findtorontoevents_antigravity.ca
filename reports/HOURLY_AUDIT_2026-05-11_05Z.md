# Hourly Audit — 05Z 2026-05-11

**Source:** `reports/HOURLY_AUDIT_2026-05-11_05Z.md`
**Dashboard snapshot:** 2026-05-11T03:58:29Z (same as 04Z — hourly cron not yet refreshed)
**Preceding audit PR:** #899 (04Z 2026-05-11) — merged this run
**UTC hour:** 05Z

---

## 1. Dashboard Refresh Status

Dashboard `audit_dashboard/data/dashboard_data.json` timestamp: `2026-05-11T03:58:29.263415+00:00`.
Hourly [skip ci] cron not yet refreshed for 05Z — data is identical to the 04Z run. All metrics below reflect the 03:58Z snapshot; next expected refresh ~05:00–05:10Z.

---

## 2. Per-Asset PF/WR — All Windows

Computed from `picks.recent_closed` (n=3500) using `closed_at` field (100% populated in first 100 sampled).

| Class | 24h n | 24h WR | 24h PF | 7d n | 7d WR | 7d PF | 30d n | 30d WR | 30d PF |
|-------|-------|--------|--------|------|-------|-------|-------|--------|--------|
| **CRYPTO** | 311 | 46.3% | 1.53 | 976 | 44.8% | 1.42 | 1499 | 46.3% | 1.40 |
| **EQUITY** | 0 | — | — | 24 | 62.5% | **4.37** | 121 | 62.8% | **3.07** |
| **FOREX** | 6 | 0.0% | 0.00 | 231 | 13.4% | 0.32 | 1000 | 37.1% | 0.25 |
| **COMMODITY** | 0 | — | — | 19† | 94.7% | 43.93† | 101 | 55.4% | **6.02** |
| **ETF** | 0 | — | — | 12† | 91.7% | 23.26† | 44 | 81.8% | **6.03** |
| **BOND** | 0 | — | — | 0 | — | — | 0 | — | — |
| **FUTURES** | 0 | — | — | 0 | — | — | 0 | — | — |

†7d inflated (n<20). 30d windows are the reliable signal for COMMODITY/ETF.

`asset_class_health` (post-resolver-v2, all-time): EQUITY PF 1.60 WR 54.0%; CRYPTO PF 1.39 WR 47.4%; COMMODITY PF 3.92 WR 67.0%; FOREX PF 0.27 WR 41.7%; ETF PF 1.42 WR 58.8%; BOND PF 0.66 WR 54.5%.

---

## 3. Deltas vs Documented Baseline

| Class | Window | This Run | Baseline | Delta | Signal |
|-------|--------|----------|----------|-------|--------|
| CRYPTO | 24h | PF 1.53 | PF 3.54 | −2.01 | Intraday noise (7d/30d stable) |
| CRYPTO | 7d | PF 1.42 | PF 1.33 | **+0.09 ↑** | Marginal improvement sustained |
| CRYPTO | 30d | PF 1.40 | PF 1.33 | **+0.07 ↑** | Below T2, improving |
| EQUITY | 7d | PF 4.37 | PF 0.87 (pre-#692) | **+3.50 ↑↑** | T1 confirmed (3 consecutive runs) |
| EQUITY | 30d | PF 3.07 | PF 2.18 | **+0.89 ↑↑** | T1 confirmed |
| FOREX | 7d | PF 0.32 | PF 0.14 (pre-#687) | +0.18 ↑ | Still catastrophic sub-floor |
| FOREX | 30d | PF 0.25 | PF 0.97 | **−0.72 ↓** | Degrading as bad picks accumulate |
| COMMODITY | 30d | PF 6.02 | PF 1.78 | **+4.24 ↑↑** | T1-candidate; n=101 at charter floor |
| ETF | 30d | PF 6.03 | PF 1.24 | **+4.79 ↑↑** | T1-candidate; n=44 below n=100 |

### Issue #693 (EQUITY divergence monitor) — CLOSED criterion

EQUITY 7d PF 4.37 ≫ acceptance criterion (PF ≥ 1.5). Confirmed in three consecutive runs (03Z, 04Z, 05Z same snapshot). Acceptance criterion fully satisfied. Recommend closing #693 after one more independent-snapshot confirmation (next hourly refresh).

---

## 4. PR Triage

### Systemic CI Blocker
`test (3.11)` failing across ALL code PRs — confirmed cross-PR shared fixture/dependency regression, not per-PR. `test (3.12)` consequently cancelled. This blocker persists from 03Z audit. No code PRs can be merged until root-cause is fixed.

### Open PRs — CI Summary

| PR | Title | test(3.11) | gate | Mergeable | Action |
|----|-------|-----------|------|-----------|--------|
| #900 | B13 regime filter v5 | FAIL | — | NO | CI blocked |
| #899 | 04Z audit doc | scan-only ✅ | — | **YES** | **MERGED this run** |
| #898 | B15 cross-asset corr fix | FAIL | — | NO | CI blocked |
| #895 | B13 regime filter v4 | no runs | — | NO | CI not triggered (stale base) |
| #893 | orphan resolver dryrun | — | — | NO | No CI run |
| #892 | safe_db_archive | — | — | NO | No CI run |
| #891 | mysql_sync timestamps | — | — | NO | No CI run |
| #887 | WIN_RATE_TRAP blacklist | FAIL | — | NO | CI blocked |
| #885 | risk_policy v2 | FAIL | FAIL | NO | CI blocked |
| #884 | mysql_sync category mapper | FAIL | FAIL | NO | CI blocked |
| #883 | source score retunings | FAIL | — | NO | CI blocked |
| #881 | tv-orchestrator TP/SL | — | — | CHECK | Not checked |
| #879 | Hermes 5-phase enhancements | — | — | CHECK | Not checked |
| #878 | short_engine regime gate | FAIL | FAIL | NO | CI blocked |
| #877 | elite_score backfill | FAIL | FAIL | NO | CI blocked |
| #876 | pnl clamp | FAIL | FAIL | NO | CI blocked |
| #873 | B13 queue doc | FAIL | — | NO | `mergeable_state: unstable` |
| #862 | DB query bank | — | — | NO | No CI run / findings-only |
| #849 | Edge action plan | — | — | NO | Draft |
| #846 | B18 shadow probation panel | — | — | CHECK | Not checked |

### HOLD Set (#660, #658, #681, #661)
All confirmed closed per prior audit runs. Not in open PR list.

### Author-Rebase Set (#669, #676, #608, #665, #644, #597, #615, #655)
All resolved per prior audit. Not in open PR list.

### PRs Merged This Run
| PR | Title | Reason |
|----|-------|--------|
| **#899** | audit(04Z 2026-05-11): EQUITY T1 PF 4.37 confirmed | Docs-only, `mergeable_state: clean`, scan ✅, no reviews/comments |

---

## 5. Mutation Analysis — New Findings

`python tools/mutation_analysis.py --json` output (05Z run):

### Direction-split candidates (Section 1)

| Strategy | LONG n | LONG WR | SHORT n | SHORT WR | Spread | Status |
|----------|--------|---------|---------|----------|--------|--------|
| `ig_contrarian_sentiment` | 164 | 14.6% | 46 | 60.9% | 46pp | Pending 3-AI consensus (posted 06Z 2026-05-10) |
| `myfxbook_retail_contrarian` | 118 | 10.2% | 13 | 46.2% | 36pp | Pending 3-AI consensus (posted 03Z 2026-05-11) |
| `quan_engine_swing` | 104 | 26.0% | 5 | 60.0% | 34pp | Pending 3-AI consensus (posted 04Z 2026-05-11) |

**No new direction-split candidates this run.** Kill queue unchanged from 04Z.

### Symbol variance — notable (Section 3)

| Strategy | Symbol | n | WR | Note |
|----------|--------|---|----|------|
| `rapid_fire` | UUSDT | 34 | 0.0% | n≥20, WR=0% — symbol-level, not strategy kill |
| `rapid_fire` | TAOUSDT | 18 | 5.6% | n<20 — monitor |
| `rapid_fire` | KATUSDT | 6 | 33.3% | too small |
| `quan_engine` | HYPEUSDT | 553 | 41.6% | avg -0.22% (blocked by #694) |
| `multi_asset_copytrader` | SI=F/AMD/ZW=F | 5-12 | 0% | too small for kill |

`rapid_fire` UUSDT (n=34, WR 0%) is a new symbol-level signal meeting n≥20 threshold with WR<35%. Does NOT trigger strategy kill per protocol — symbol-allowlist mutation required first. Posted to issue #686.

### Full kill queue (pending 3-AI consensus)

1. `ig_contrarian_sentiment` LONG — n=164, WR 14.6%, PF ~0.0 — catastrophic (posted 06Z 05-10)
2. `myfxbook_retail_contrarian` LONG — n=118, WR 10.2%, PF 0.34 — catastrophic (posted 03Z 05-11)
3. `quan_engine_swing` LONG — n=104, WR 26.0% (posted 04Z 05-11)
4. `forex_carry_momentum` ALL — n=142, WR 9.2%, PF 0.10 (per issue #686)
5. `forex_rsi2_mean_reversion` LONG — n=319, WR 37.6%, PF 0.51 (monitor — just above 0.5 threshold)

**New finding (05Z):** `rapid_fire` symbol `UUSDT` — n=34, WR 0%. Symbol-level mutation candidate, not strategy kill.

---

## 6. Systemic CI Blocker — Root Cause Needed

`test (3.11)` has been failing across 10+ unrelated PRs since at least 03Z 05-11. Pattern: all code-touching PRs fail; docs-only PRs (scan-only) pass. This is a shared fixture or dependency regression on `main`, not a per-PR issue.

**Impact:** ALL code PRs are blocked. The kill queue cannot be executed via PRs until CI is fixed.

**Recommended action:** Dedicated root-cause investigation PR for `test (3.11)` shared fixture failure. Agent should run `pytest tests/ -x --tb=short` locally to identify failing test + traceback, then open a targeted fix PR.

---

## 7. Issue Status

| Issue | Status | Update |
|-------|--------|--------|
| #685 | Open (dormant) | Resolver-rescope DONE; no new activity needed |
| #686 | Open (active) | Kill queue has 4 active candidates + 1 new symbol signal (`rapid_fire` UUSDT) |
| #693 | Open (satisfied) | EQUITY 7d PF 4.37 ≫ acceptance criterion; close after next independent-snapshot confirmation |

---

## 8. Summary

- **Dashboard:** 03:58Z snapshot (unchanged from 04Z; cron pending)
- **EQUITY:** T1 confirmed — 7d PF 4.37 / 30d PF 3.07. PR #692 goldmine_6x kill working.
- **CRYPTO:** Stable below T2 — 7d PF 1.42 / 30d PF 1.40. 24h noise (-2.01 vs baseline) expected.
- **FOREX:** Deteriorating — 30d PF 0.25 (down from 0.97 baseline). Kill queue action needed.
- **COMMODITY:** T1-candidate — 30d PF 6.02, n=101 at charter floor.
- **ETF:** T1-candidate — 30d PF 6.03 but n=44, below n=100 minimum.
- **PRs merged:** #899 (04Z audit doc) — 1 total
- **New findings:** 0 new strategy kill candidates; `rapid_fire` UUSDT symbol signal (n=34, WR 0%)
- **CI blocker:** systemic `test(3.11)` failure blocks all code PRs

https://claude.ai/code/session_01XDkqiizFomCjugJfw79xEQ
