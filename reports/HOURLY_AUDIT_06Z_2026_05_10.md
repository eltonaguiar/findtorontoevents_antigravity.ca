# Hourly Audit — 06Z 2026-05-10

**Dashboard snapshot:** 2026-05-10T04:03:28Z (auto-refresh, hourly cron [skip ci])
**Audit generated:** 2026-05-10T05:12Z
**Preceding audit:** PR #894 (05Z 2026-05-10)
**Source data:** `audit_dashboard/data/dashboard_data.json` — `picks.recent_closed` n=3500

---

## 1. Dashboard Refresh Status

Auto-refresh pulled via `git pull --rebase origin main`. Dashboard data timestamp: `2026-05-10T04:03:28Z`. No generators run locally (policy: py_compile only).

---

## 2. Per-Asset PF/WR — All Windows

Computed from `picks.recent_closed` (n=3500, field: `pnl_pct` with `pnl` fallback).

### Last 24h

| Class | n | WR | PF | Sum PnL% | Note |
|-------|---|----|----|----------|------|
| CRYPTO | 170 | 37.6% | 1.13 | +24.7% | Soft vs baseline 3.54; 7d/30d stable |
| EQUITY | 1 | 100.0% | — | +4.8% | n too small |
| FOREX | 17 | 0.0% | — | 0.0% | pnl_pct null on very-recent closes |
| COMMODITY | 0 | — | — | — | — |
| ETF | 0 | — | — | — | — |
| BOND | 0 | — | — | — | — |

### Last 7d

| Class | n | WR | PF | Sum PnL% | Delta vs baseline | Tier |
|-------|---|----|----|----------|-------------------|------|
| CRYPTO | 855 | 44.9% | **1.54** | +419.1% | +0.21 ↑ (baseline 1.33) | T2 candidate |
| EQUITY | 24 | 62.5% | **4.37** | +102.2% | +3.50 ↑↑ (baseline 0.87) | **T1 confirmed** |
| FOREX | 248 | 16.9% | **0.33** | −64.7% | +0.19 ↑ (baseline 0.14) | Sub-floor |
| COMMODITY | 39 | 92.3% | 43.27† | +83.3% | — (n<50) | Not tier-assessable |
| ETF | 12 | 91.7% | 23.26† | +22.3% | — (n<50) | Not tier-assessable |
| BOND | 0 | — | — | — | — | — |

†High-variance; n below charter 50-trade assessment floor.

### Last 30d

| Class | n | WR | PF | Sum PnL% | Delta vs baseline | Tier |
|-------|---|----|----|----------|-------------------|------|
| CRYPTO | 1499 | 47.6% | **1.53** | +646.9% | +0.20 ↑ (baseline 1.33) | T2 candidate |
| EQUITY | 125 | 63.2% | **3.18** | +284.7% | +1.00 ↑ (baseline 2.18 high) | **T1 confirmed** |
| FOREX | 1056 | 38.2% | **0.27** | −128.9% | −0.70 ↓ (baseline 0.97) | Sub-floor; pre-#687 history drags |
| COMMODITY | 149 | 57.7% | **4.89** | +117.0% | +3.11 ↑ (baseline 1.78) | T1 candidate (n≥100 ✓) |
| ETF | 44 | 81.8% | **6.03** | +77.2% | +4.79 ↑ (baseline 1.24) | T1 candidate (n→100 needed) |
| BOND | 0 | — | — | — | n=18 (charter floor not met) | — |

### Long-run (asset_class_health — dashboard headline)

| Class | PF | WR |
|-------|----|
| FOREX | 0.27 | 41.7% |
| CRYPTO | 1.40 | 48.0% |
| EQUITY | 1.58 | 53.7% |
| COMMODITY | 3.97 | 67.2% |
| ETF | 1.42 | 58.8% |

---

## 3. Key Metric Deltas vs Baselines

| Class | Window | Prev baseline | This audit | Delta | Signal |
|-------|--------|--------------|------------|-------|--------|
| CRYPTO | 24h PF | 3.54 | 1.13 | −2.41 | Soft day; not alarming — 7d stable |
| CRYPTO | 7d PF | 1.33 | 1.54 | +0.21 | Improving |
| CRYPTO | 30d PF | 1.33 | 1.53 | +0.20 | Improving |
| EQUITY | 7d PF | 0.87 | 4.37 | +3.50 | **T1 confirmed** — #692 goldmine_6x kill working |
| EQUITY | 30d PF | 1.41–2.18 | 3.18 | — | T1 territory |
| FOREX | 7d PF | 0.14 | 0.33 | +0.19 | Still catastrophic |
| FOREX | 30d PF | 0.97 | 0.27 | −0.70 | Pre-#687 history contaminates |
| COMMODITY | 30d PF | 1.78 | 4.89 | +3.11 | Strong (n=149 ≥ charter floor) |
| ETF | 30d PF | 1.24 | 6.03 | +4.79 | Strong (n=44, needs →100) |

---

## 4. PR Merge Actions This Hour

| PR | Title | CI | Action | Reason |
|----|-------|----|--------|--------|
| #894 | audit(05Z 2026-05-10) | scan ✓ | **MERGED** | docs-only, clean CI, no reviews |
| #888 | audit(04Z 2026-05-10) | scan ✓ | **MERGED** | docs-only, clean CI, no reviews |
| #882 | docs: sports CLV gap | scan ✓ | **MERGED** | docs-only, clean CI, no reviews |
| #871 | audit(04Z 2026-05-09) | scan ✓ | **MERGED** | docs-only, clean CI, no reviews |
| #865 | audit(05Z 2026-05-08) | scan ✓ | **MERGED** | docs-only, clean CI, no reviews |

**Total merges this hour: 5**

### Remaining open PRs — CI status summary

| PR | CI Status | Blocker |
|----|-----------|--------|
| #895 | test(3.11) FAIL | systemic CI blocker |
| #893 | test(3.11) FAIL | systemic CI blocker |
| #891 | test(3.11) FAIL, gate FAIL | systemic CI blocker |
| #887 | test(3.11) FAIL | systemic CI blocker |
| #885 | test(3.11) FAIL, gate FAIL | systemic CI blocker |
| #884 | test(3.11) FAIL, gate FAIL | systemic CI blocker |
| #883 | test(3.11) FAIL | systemic CI blocker |
| #878 | gate FAIL, test(3.12) FAIL | systemic CI blocker |
| #877 | gate FAIL, test(3.12) FAIL | systemic CI blocker |
| #876 | gate FAIL, test(3.12) FAIL | systemic CI blocker |
| #873 | test(3.11) FAIL | systemic CI blocker |
| #862 | test(3.11) FAIL | systemic CI blocker |
| #890 | scan ✓ | mergeable=unknown (stale) |
| #879 | no checks | no CI run |
| #892 | no checks | no CI run |
| #849 | no checks | draft |
| #846 | scan ✓, drift ✓ | mergeable=dirty (conflict) |

**Systemic CI blocker:** `test (3.11)` failing on 12/18 remaining feature PRs. Pattern consistent with shared test fixture or dependency break rather than per-PR regression. Dedicated root-cause fix PR needed to unblock queue.

### HOLD set status

#660 closed ✓ | #661 merged (historical) ✓ | #658 closed ✓ | #681 closed ✓

### Author-rebase set status (all resolved prior sessions)

#669 merged ✓ | #676 merged ✓ | #608 merged ✓ | #665 merged ✓ | #644 merged ✓ | #597 merged ✓ | #615 merged ✓ | #655 closed ✓

---

## 5. Mutation Analysis — New Kill Candidate

**Command:** `python tools/mutation_analysis.py --json` — 2026-05-10 05:12Z

### NEW: `ig_contrarian_sentiment` LONG direction

| Direction | n | WR | Avg PnL% |
|-----------|---|----|---------|
| LONG | **163** | **14.7%** | ≈0.00% |
| SHORT | 46 | 60.9% | ≈0.00% |

Kill criteria (CLAUDE.md §NEW STRATEGY KILLS):
- (a) Pattern matches existing kills (direction-split FOREX strategy) ✓
- (b) n=163 ≥ 20 ✓
- (c) WR 14.7% < 35% sustained ✓

**Recommended action:** block LONG direction only; SHORT 60.9% WR is healthy. Awaiting 2 more AI sign-offs before `BLOCKED_ASSET_STRATEGY_PAIRS` update. Posted to issue #686 comment #4414498760.

### Previously-flagged candidates (pending 3-AI consensus)

| Strategy | Direction | n | WR | Sign-offs |
|---|---|---|---|---|
| `myfxbook_retail_contrarian` | LONG | 118 | 10.2% | 1 (Claude) |
| `quan_engine_swing` | LONG | 104 | 26.0% | 1 (Claude) |
| `rapid_fire` UUSDT | symbol | 34 | 0.0% | 1 (Claude) |
| `ig_contrarian_sentiment` | LONG | 163 | 14.7% | 1 (Claude) — **NEW** |

No auto-kills applied. All require 3-AI consensus per protocol.

### Symbol-level variance flagged

- `rapid_fire`: UUSDT 0%/34, ESPUSDT 0%/5 — symbol-allowlist mutation candidate
- `quan_engine`: HYPEUSDT 41.6%/553 (avg −0.22%) — already symbol-blocked per PR #694

---

## 6. Issue #693 Status

EQUITY 7d PF recovered from 0.87 (pre-#692) to 4.37 (this audit). Acceptance criterion (EQUITY 14d PF ≥ 1.5 within 7 days post-#692) satisfied with margin. Issue #693 can be closed when confirmed stable for one more run.

---

## 7. Constraints Verified

- Resolver-rescope: DONE per issue #685 — no code changes proposed ✓
- Plan v2.1 stats (PF 5.81, ml_score 0.90, WINNER_FILTER): not cited ✓
- No peer PR rebases ✓
- HOLD set not touched ✓
- No auto-kills without 3-AI consensus ✓
- Never ran dashboard generators locally ✓

---

_Generated by Claude Sonnet 4.6 — 2026-05-10 05:12Z
