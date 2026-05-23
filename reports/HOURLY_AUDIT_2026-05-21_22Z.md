# Hourly Audit — 2026-05-21 22Z

**Generated:** 2026-05-21T22:12Z  
**Dashboard snapshot:** `2026-05-21T21:38:30Z` ✅ (auto-refresh active)  
**Refs:** issues #685 #686 #693 | prior cycle: PR #1301 (21Z)

---

## 1. Dashboard Refresh Status

Auto-refresh confirmed via `[skip ci]` cron. Snapshot lag from now: ~34 min (within 1-hour window). Source: `audit_dashboard/data/dashboard_data.json`.

---

## 2. Per-Asset PF/WR — Current vs Baseline

### asset_class_health (rolling resolved window)

| Class | n | WR% | PF | Total PnL% | Status | sizing_allowed |
|-------|---|-----|----|------------|--------|----------------|
| CRYPTO | 1084 | 48.2% | 1.355 | +23.43% | stable | ✅ |
| FOREX | 154 | 54.5% | 2.942 | +0.44% | stable | ✅ |
| COMMODITY | 61 | 50.8% | 1.296 | +0.37% | candidate | ❌ |
| EQUITY | 55 | 36.4% | 0.921 | -0.08% | candidate | ❌ |
| FUTURES | 12 | 16.7% | 0.956 | -0.01% | thin_sample | ❌ |
| ETF | 2 | 50.0% | 11.99 | +0.22% | insufficient (n=2) | ❌ |
| BOND | 7 | 0.0% | 0.000 | -0.51% | insufficient | ❌ |
| PENNY_STOCK | 1 | 0.0% | 0.000 | -0.01% | insufficient | ❌ |

### Windowed per-asset (from recent_closed n=3500)

| Class | 24h n | 24h PF | 7d n | 7d WR | 7d PF | 30d n | 30d PF |
|-------|-------|--------|------|-------|-------|-------|--------|
| CRYPTO | 185 | 1.796 | 1021 | 48.8% | 1.433 | 2810 | 1.334 |
| EQUITY | 9 | 1.678 | 45 | 35.6% | 0.755 | 142 | 1.379 |
| FOREX | 8 | 1.531 | 11 | 36.4% | 1.451 | 94 | 2.598 |
| COMMODITY | 3 | 1.933 | 35 | 11.4% | 0.246 | 79 | 0.943 |
| ETF | 2 | 0.000 | 12 | 8.3% | 0.884 | 56 | 2.248 |
| BOND | 1 | 0.000 | 5 | 0.0% | 0.000 | 5 | 0.000 |
| FUTURES | — | — | — | — | — | 2 | inf |

### Deltas vs Documented Baselines

| Class | Metric | Baseline | Current | Δ | Signal |
|-------|--------|----------|---------|---|--------|
| CRYPTO | 24h PF | 3.54 | 1.796 | -1.744 | Normal regression from spike; 7d trend stable |
| CRYPTO | 7d PF | 1.33 | 1.433 | **+0.103** | ✅ Improving |
| CRYPTO | 30d PF | 1.33 | 1.334 | +0.004 | Flat/stable |
| EQUITY | 7d PF | 0.87 | 0.755 | **-0.115** | 🔴 Further deterioration (pre-kill trades still rolling off) |
| EQUITY | 30d PF | 1.41 | 1.379 | -0.031 | Slight decline; goldmine_6x effect |
| EQUITY | 24h PF | — | 1.678 | — | ✅ 24h recovering post-PR #692 |
| FOREX | 7d PF | 0.14 (pre-#687) | 1.451 | **+1.311** | ✅ Post-#687 recovery confirmed and holding |
| FOREX | 30d PF | 0.97 (pre-#687) | 2.598 | **+1.628** | ✅ Structural improvement |
| COMMODITY | 7d PF | 0.246 (FINDING-59) | 0.246 | 0.000 | 🔴 Unchanged; kill candidates below n=20 floor |

---

## 3. Strategy Kill Candidates

### 7d kill candidates (n≥10, WR<35%) — from recent_closed

| Class | Strategy | n | WR | PF | ΔPnL% | Eligible? |
|-------|----------|---|----|----|--------|-----------|
| COMMODITY | futures_momentum | 17 | 11.8% | 0.087 | -52.81% | ❌ n<20; FINDING-59, monitoring |
| COMMODITY | cftc_cot_commercial_signal | 16 | 12.5% | 0.409 | -42.92% | ❌ n<20; NEW sub-finding |
| CRYPTO | keltner_compression_expansion_eth_v1 | 17 | 29.4% | 0.858 | -0.54% | ❌ n<20; PnL borderline |

### Symbol-level kill candidates (n≥20, WR<35%) — confirmed from mutation_analysis.py

| Strategy×Symbol | n | WR | PF | Status |
|-----------------|---|----|----|--------|
| cta_replicator×NG=F | 24 | 0.0% | 0.0 | **FINDING-60** — awaiting 3-AI consensus (posted #686) |
| rapid_fire×UUSDT | 34 | 0.0% | 0.0 | **FINDING-61** — awaiting 3-AI consensus (posted #686) |

### NEW FINDING-62 — `cftc_cot_commercial_signal` [COMMODITY] approaching kill threshold

- n=16 (floor is 20), WR=12.5%, PF=0.409, sum=-42.92%
- Note: PR #683 killed `cftc_cot` (the parent strategy); `cftc_cot_commercial_signal` is a distinct variant still active
- **Action: monitor at next cycle. If n reaches 20 with sustained WR<35%, open mutation analysis.**
- Does NOT meet current kill criteria (n<20). Posting to issue #686 for tracking.

### Axis-4 candidates from mutation_analysis.py (large-n, vol-normalization candidates)

| Strategy | n | WR | Note |
|----------|---|-----|------|
| multi_asset_copytrader | 1148 | 22.0% | Large n; Axis-4 vol-norm candidate |
| alpha_engine | 55 | 27.3% | Axis-4 candidate |
| rapid_fire | 207 | 29.0% | Already has FINDING-61 symbol block pending |
| quan_engine | 5896 | 30.4% | HYPEUSDT block (PR #694) active; monitor trend |

These require `docs/MUTATION_THREE_AXIS_PROTOCOL.md` investigation before any kill. Do NOT auto-kill.

---

## 4. PR Triage

### Open PRs at 22Z

| PR | Title | CI | Reviews | mergeable_state | Decision |
|----|-------|-----|---------|-----------------|----------|
| #1301 | audit(hourly): 21Z | ✅ 3/3 green | COMMENTED only (greptile bot) | unknown | **HOLD** — GitHub computing mergeability |
| #1299 | chore(loop): LOOP_COMPLETE | ✅ 3/3 green | COMMENTED only (greptile bot) | unknown | **HOLD** — GitHub computing mergeability |
| #1287 | feat(b10): UEPS KPI panel | ❌ test(3.11) FAILED | — | — | **HOLD** — CI failure |
| #1279 | docs: correct AGENTS.md | — | — | — | **HOLD** — DRAFT |

**HOLD set (#660 #658 #681 #661):** All confirmed closed ✅  
**Author-rebase PRs (#669 #676 #608 #665 #644 #597 #615 #655):** All merged/closed ✅  
**Plan v2.1 guardrails:** No PRs citing PF 5.81 / ml_score 0.90 / WINNER_FILTER — clean ✅

### Merged this cycle
**None.** No PR achieved all three criteria simultaneously (mergeable_state=unknown on eligible PRs).

Note: #1299 and #1301 are CI-green with no REQUEST_CHANGES from any human/AI reviewer. They are blocked only by `mergeable_state=unknown` (GitHub lazy computation). Eligible for merge at 23Z if state resolves to MERGEABLE.

---

## 5. Assessment vs Goals

### Goal #1 — Audit performance across all asset classes

| Class | Tier status | Path to Tier-2 | Urgency |
|-------|-------------|----------------|----------|
| CRYPTO | Near-T2 (PF 1.355 / WR 48%) | Vol-targeting MDD reduction | Medium |
| FOREX | **T2 candidate** (PF 2.942 / WR 54.5% / n=154) | Monitor recovery; post-#687 structural | Low — hold |
| EQUITY | Sub-T2 (PF 0.921 / WR 36%) | Post-#692 recovery in progress; wait 24h-72h | Medium |
| COMMODITY | Sub-T2 (PF 1.296 rolling / 0.246 7d) | cta_replicator×NG=F kill (FINDING-60) pending consensus | High |
| ETF | Insufficient data (n=2 rolling) | Accrue more closed trades | Low |
| BOND | Insufficient (n=7) | Accrue more closed trades | Low |

**FOREX is the biggest positive development this hour:** asset_class_health now shows `stable` status, PF=2.942 on n=154. This is T2-grade (PF>1.5/WR>50%). The pre-#687 state was PF=0.27/WR=46.4% — a complete reversal.

**EQUITY 7d continues to lag** but 24h PF=1.678 shows the goldmine_6x kills are starting to filter through. Expected full 7d recovery window: 3-5 days from PR #692 merge date.

**COMMODITY 7d PF=0.246 unchanged.** Structural: cta_replicator×NG=F block needs consensus (FINDING-60) and cftc_cot_commercial_signal approaching kill threshold (FINDING-62, n=16).

---

## 6. Actions Taken This Cycle

1. Pulled latest `dashboard_data.json` from origin/main ✅
2. Computed windowed per-asset PF/WR (24h/7d/30d) ✅
3. Ran `python tools/mutation_analysis.py --json` ✅
4. Verified FINDING-60/61 persisting from 21Z cycle (awaiting 3-AI consensus) ✅
5. Identified **FINDING-62** (`cftc_cot_commercial_signal` [COMMODITY], n=16, approaching kill floor)
6. PR triage: no merges; all eligible PRs blocked by `mergeable_state=unknown`
7. Confirmed HOLD set (#660 #658 #681 #661) all closed ✅
8. Confirmed author-rebase PRs all resolved ✅

---

## 7. Next Cycle (23Z) Priority Actions

1. **Re-check #1299 and #1301 mergeability** — if MERGEABLE, merge both (CI green, no REQUEST_CHANGES)
2. **Issue #686 comment** with FINDING-62 (`cftc_cot_commercial_signal` [COMMODITY]) for tracking
3. **Monitor EQUITY 7d** — expected to recover toward PF>1.0 as goldmine_6x trades roll off window
4. **Monitor cftc_cot_commercial_signal n** — trigger mutation analysis at n=20
5. **3-AI consensus gate** for FINDING-60 (cta_replicator×NG=F) and FINDING-61 (rapid_fire×UUSDT)
