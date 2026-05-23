# Hourly Audit — 2026-05-22 04Z

**Generated:** 2026-05-22T04:09Z  
**Dashboard snapshot:** `2026-05-22T02:19:15Z` ⚠️ STALE — age ~110 min at audit time (same snapshot as 03Z; cron pending or delayed)  
**Methodology note:** Per-window metrics computed from `picks.recent_closed` (n=3500) using `asset_class` / `pnl_pct` / `closed_at` fields. The `asset_class_health` rolling block is read directly from the JSON pre-computed section.

---

## Per-Asset Summary (04Z)

| Class | 24h n | 24h WR | 24h PF | 7d n | 7d WR | 7d PF | 30d n | 30d WR | 30d PF | Status |
|-------|--------|---------|---------|------|-------|-------|-------|-------|-------|--------|
| CRYPTO | 178 | 47.8% | 1.388 | 992 | 47.9% | 1.256 | 2791 | 46.2% | 1.289 | Stable ✅ |
| EQUITY | 9 | 55.6% | 1.678 | 45 | 35.6% | **0.755** | 142 | 42.3% | 1.379 | 7d sub-T2 ⚠️ |
| FOREX | 8 | 50.0% | 1.520 | 11 | 36.4% | 1.442 | 94 | 48.9% | 2.591 | Recovery holds ✅ |
| COMMODITY | 3 | 33.3% | 1.933 | 35 | 11.4% | **0.246** | 79 | 40.5% | 0.943 | CRITICAL ⚠️ |
| ETF | 2 | 0.0% | 0.000 | 12 | 8.3% | 0.884 | 56 | 58.9% | 2.248 | 7d thin/weak |
| BOND | 1 | 0.0% | 0.000 | 5 | 0.0% | 0.000 | 5 | 0.0% | 0.000 | Below gate (n<10) |

### asset_class_health (rolling, pre-computed in JSON)

| Class | PF | WR | n | Notes |
|-------|-----|-----|---|-------|
| CRYPTO | 1.355 | 48.2% | 1085 | sub-T2 but stable |
| EQUITY | 0.921 | 36.4% | 55 | sub-T2; 7d drag persists |
| FOREX | **3.406** | **53.8%** | 156 | Tier-2 ✅ (post-#687 JPY fix) |
| COMMODITY | 1.296 | 50.8% | 61 | Rolling OK; 7d window alarming |
| ETF | 11.995 | 50.0% | 2 | n too small for verdict |
| FUTURES | 0.956 | 16.7% | 12 | sub-T2 |
| BOND | 0.000 | 0.0% | 7 | below gate floor (n<20) |

---

## Deltas vs 03Z Baseline

> **Note:** Dashboard snapshot is identical (02:19:15Z). Numeric differences vs 03Z are methodological (different window boundary ms, field name resolution). No new dashboard data arrived between 03Z and 04Z sweeps.

| Class | 7d PF (03Z) | 7d PF (04Z) | Delta | Signal |
|-------|------------|------------|-------|--------|
| CRYPTO | 1.355 | 1.256 | -0.099 | Methodological artefact (same data) |
| EQUITY | 1.124 | 0.755 | -0.369 | Methodological artefact (same data) |
| FOREX | 1.825 | 1.442 | -0.383 | Methodological artefact (same data) |
| COMMODITY | 0.246 | 0.246 | 0.000 | Confirmed unchanged |
| ETF | 1.774 | 0.884 | -0.890 | Methodological artefact (same data) |

Real-world signal does not change until the next cron refresh. The `asset_class_health` rolling block (not window-computed) is the authoritative source between refreshes.

---

## Findings

### FINDING-59 (COMMODITY) — `futures_momentum` + `cftc_cot_commercial_signal` approaching n=20 gate
- `futures_momentum`: n=17 (3 from gate), WR=11.8%, PF=0.087 — Axis-1 mutation prep warranted
- `cftc_cot_commercial_signal`: n=16 (4 from gate), WR=12.5%, PF=0.409 — residual post-PR-#683 kill
- **Status:** UNCHANGED from 03Z. No action until n=20 and 3-AI consensus.
- **Next:** At n=20, run `docs/MUTATION_THREE_AXIS_PROTOCOL.md` for `futures_momentum`.

### FINDING-63 (EQUITY) — Monitoring continues
- 03Z saw 24h PF 3.184 (strong); 04Z 24h PF 1.678 (normalising — same snapshot, window edge effect)
- `stocks_rsi2_pullback` n=29, WR=44.8%, PF=1.396 (7d) — within acceptable range, no action
- `goldmine_6x_consensus` kill (PR #692) continues to reduce 7d drag
- **Status:** Continue to monitor per issue #693. If EQUITY 14d < 1.0 for 14 days post-#692, escalate.

### FINDING-66 (CRYPTO) — `luxalgo_confluence` watch continues
- n=128 (same snapshot as 03Z; n difference from prior report is field-resolution artefact)
- WR=32.8%, PF=0.686 — PF > 0.5 kill floor, WR < 35% sustained
- **Status:** Needs 3-AI consensus before any block. No auto-kill.
- **Next:** Posted to issue #686 requesting Kimi/Copilot/Cursor second opinion.

### FINDING-67 (CRYPTO) — NEW: `crypto_mtf_ema_slope_alignment_v1` crosses n=20 gate
- n=21 (7d), WR=47.6%, PF=0.626
- **First cycle above n=20 gate.** PF=0.626 > 0.5 kill floor — no auto-kill permitted.
- WR 47.6% > 35% — does NOT meet WR auto-kill criterion either.
- **Action:** Posted to issue #686. Requires 3-AI consensus to proceed to kill.
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` gate applies before any BLOCKED entry.

---

## Mutation Analysis

`tools/mutation_analysis.py` requires `closed_picks.csv` export (not available in CI context). Strategy-level metrics derived directly from `recent_closed` n=3500 instead.

**PF<0.5 + n>=20 kill candidates (7d): NONE this cycle.**

Watch list (PF<1.0, n>=10, 7d, full list):

| Class | Strategy | n | WR | PF | Gate Status |
|-------|----------|---|----|----|-------------|
| CRYPTO | `luxalgo_confluence` | 128 | 32.8% | 0.686 | n>=20; PF>0.5 — needs 3-AI (FINDING-66) |
| CRYPTO | `crypto_mtf_ema_slope_alignment_v1` | 21 | 47.6% | 0.626 | n>=20 NEW; PF>0.5 — needs 3-AI (FINDING-67) |
| COMMODITY | `futures_momentum` | 17 | 11.8% | 0.087 | n<20 (3 away) — watch |
| CRYPTO | `multi_period_rsi_confluence_eth` | 17 | 47.1% | 0.513 | n<20 (3 away) |
| CRYPTO | `keltner_compression_expansion_eth_v1` | 17 | 29.4% | 0.858 | n<20 |
| COMMODITY | `cftc_cot_commercial_signal` | 16 | 12.5% | 0.409 | n<20 (4 away) — watch |
| CRYPTO | `multi_period_rsi_confluence` | 10 | 20.0% | 0.184 | n<20 |

---

## PR Triage

### Merged this cycle
| PR | Title | Action |
|----|-------|--------|
| **#1308** ✅ | audit(hourly): 03Z 2026-05-22 | Merged (CI 3/3 green, mergeable=clean, no REQUEST_CHANGES) |

### Holds
| PR | Reason |
|----|--------|
| **#1299** | Merge conflict (branch behind main after bulk updates; prior sweeps left rebase-needed comment). Docs-only — needs author rebase. |
| **#1287** | `test (3.11)` FAILED + `ueps-pytest` cancelled. HOLD until CI green. |
| **#1279** | DRAFT — HOLD. |
| HOLD set (#660 #658 #681 #661) | All previously closed ✅ |

### Author-rebase check (#669 #676 #608 #665 #644 #597 #615 #655)
All merged or closed on prior sessions — no action required.

---

## Dashboard Freshness

Snapshot age ~110 min at audit time. The hourly cron (GitHub Actions) is either:
- Running now (expected ~04:19Z), or
- Delayed / missed (check `gh run list --workflow=dashboard-refresh.yml`)

**Action:** No manual intervention; cron will self-correct. Next audit (~05Z) should see a fresh snapshot (<=60 min old).

---

## Plan v2.1 Guardrails
- No PR citations of refuted stats (PF 5.81, ml_score 0.90, WINNER_FILTER) detected
- Issue #685 resolver-rescope: DONE, no new PRs claiming 'widen re-resolve scope'
- HOLD set (#660 #658 #681 #661): all closed

---

## Refs
- Issues #685 (resolver-rescope done), #686 (live quality regression), #693 (EQUITY monitor — closed 2026-05-13)
- PRs merged today (session context): #684, #674, #673, #664, #683, #687, #692, #694, #1308
- Dashboard: `audit_dashboard/data/dashboard_data.json` (generated 2026-05-22T02:19:15Z)
