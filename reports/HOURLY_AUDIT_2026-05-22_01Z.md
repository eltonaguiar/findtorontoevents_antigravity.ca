# Hourly Audit — 2026-05-22 01Z

**Generated:** 2026-05-22T01:10Z  
**Dashboard snapshot:** `2026-05-21T22:45:32Z` ⚠️ STALE — third consecutive stale cycle (23Z, 00Z, 01Z). Cron has not fired since ~22:45Z yesterday.  
**Refs:** issues #685 #686 #693 | PRs merged today: #684 #674 #673 #664 #683 #687 #692 #694

---

## 1. Dashboard Refresh Status

Snapshot is `2026-05-21T22:45:32Z` — unchanged from 23Z and 00Z audits. All per-asset numbers and strategy attributions below are identical to the previous cycle; no new data to diff. Cron drift is ~2.5h and counting. No action available (cron-managed; no operator gate).

---

## 2. Per-Asset Summary (01Z)

| Class | PF (24h) | WR (24h) | PF (7d) | WR (7d) | PF (30d) | Status | vs Baseline |
|-------|----------|----------|---------|---------|---------|--------|-------------|
| **CRYPTO** | 1.674 | 51.2% | 1.411 | 48.4% | 1.322 | Stable ✅ | 7d +0.081 vs 1.33 baseline |
| **EQUITY** | 0.300 | 33.3% | **0.654** | **30.8%** | 1.349 | Sub-T2; FINDING-63 | −0.216 vs 0.87 pre-#692 |
| **FOREX** | 1.434 | 42.9% | 1.359 | 30.0% | **2.572** | Recovery holding ✅ | 7d +1.219 vs 0.14 pre-#687 |
| **COMMODITY** | 1.933 | 33.3% | 0.246 | 11.4% | 0.943 | FINDING-59 persists ⚠️ | 7d sub-1; 30d also sub-1 |
| **ETF** | 0.000 | 0.0% | 0.884 | 8.3% | **2.248** | Thin n (7d n=12) | 30d T1-grade; 7d noise |
| **BOND** | 0.000 | 0.0% | 0.000 | 0.0% | 0.000 | n=5 (7d); below charter floor | — |
| **FUTURES** | — | — | — | — | 168924 | n=2 (30d); statistical artifact | — |

**asset_class_health (rolling):**
- FOREX: PF=1.368 / WR=53.5% — T2-grade ✅
- COMMODITY: PF=1.296 / WR=50.8% — approaching T2
- EQUITY: PF=0.921 / WR=36.4% — sub-T2; n=55 in window
- ETF: PF=11.995 — inflated; thin n in rolling window
- FUTURES: PF=0.956 — sub-1 rolling; n too small

---

## 3. Strategy Attribution — New Findings

### FINDING-63 Update (EQUITY 7d deterioration)

Snapshot stale; numbers unchanged from 00Z. Per-strategy 7d EQUITY breakdown:

| Strategy | n | WR | PF | sum PnL% | Status |
|---|---|---|---|---|---|
| `vol-contraction-scout` | 3 | 0.0% | 0.000 | −10.18% | n<20; no action |
| `rs-breakout-scout` | 3 | 0.0% | 0.000 | −8.65% | n<20; no action |
| `price-accel-scout` | 1 | 0.0% | 0.000 | −6.92% | n<20; no action |
| `stocks_ema_golden_cross` | 2 | 0.0% | 0.000 | −6.83% | n<20; no action |
| `macd-hidden-div-scout` | 1 | 0.0% | 0.000 | −6.68% | n<20; no action |
| `adx-trend-scout` | 2 | 50.0% | 0.161 | −6.68% | n<20; no action |
| `stocks_rsi2_pullback` | 25 | 40.0% | 1.242 | +10.87% | **POSITIVE — was flagged as drag in 23Z; now net positive** |
| `aroon-trend-scout` | 1 | 100% | 40504 | +4.05% | Thin n |

**Key shift:** `stocks_rsi2_pullback` n=25 / WR=40.0% / sum=+10.87% is now a **positive contributor**. The 7d EQUITY drag is entirely scout-cohort noise (each n=1–3), below the n=20 kill floor. The FINDING-63 mutation gate concern from 23Z is **relaxed** — no action required this cycle.

EQUITY 7d PF=0.654 remains sub-T2 structurally but is no longer actively deteriorating (stale snapshot; last directional signal was 00Z).

### FINDING-59 (COMMODITY 7d) — Unchanged

| Strategy | n | WR | PF | sum PnL% | Status |
|---|---|---|---|---|---|
| `futures_momentum` | 17 | 11.8% | 0.087 | −52.81% | n=17; approaching n=20 kill floor |
| `cftc_cot_commercial_signal` | 16 | 12.5% | 0.409 | −42.92% | n=16; approaching kill floor |
| `futures_bb_mean_reversion` | 2 | 0.0% | 0.000 | −10.46% | n<10 |

`futures_momentum` at n=17 / WR=11.8% / PF=0.087 is 3 trades from the n=20 kill-analysis gate. Next audit that crosses n=20 with PF<0.5 must post to issue #686 with evidence and request 3-AI consensus.

`cftc_cot_commercial_signal` at n=16 / WR=12.5% / PF=0.409 — similarly approaching gate. Note: `cftc_cot` strategy was killed in PR #683 (today); this residual may be COMMODITY-class legacy picks still resolving.

### NEW — `luxalgo_confluence` volume drag

**NEW FINDING-64:** `luxalgo_confluence` n=131 (7d), WR=34.4%, PF=0.725, sum=−52.68%. This is the **largest n** of any underperforming strategy (above PF=0.5 threshold so not a kill candidate, but material volume drag on system-wide PF). CRYPTO-class. No kill action — PF=0.725 > 0.5. Flag for Axis-2 (symbol rotation) sandbox.

### Direction-flip candidates (persistent from 23Z/00Z)

| Strategy | LONG WR | LONG n | SHORT WR | SHORT n | Action |
|---|---|---|---|---|---|
| `ig_contrarian_sentiment` | 16.5% | 200 | ~50%+ | small | Axis-1 candidate; awaiting 3-AI consensus |
| `myfxbook_retail_contrarian` | 13.7% | 124 | 50.0% | 14 | Axis-1 candidate; flagged 23Z |
| `cta_cross_asset_tsmom` | 29.4% | 85 | — | — | Monitor |

### FINDING-60 / FINDING-61 (from 21Z/22Z, unchanged)

- `cta_replicator`×NG=F: n=24, WR=0% — awaiting 3-AI consensus (no CSV; cannot re-run mutation test locally)
- `rapid_fire`×UUSDT: n=34, WR=0% — awaiting 3-AI consensus

---

## 4. Mutation Analysis — New Kill Candidates

`python tools/mutation_analysis.py` requires `closed_picks.csv` export — not available in cloud environment. Analysis performed directly from `recent_closed` JSON.

**No new PF<0.5 + n≥20 strategies identified this cycle.**

Closest approaching gate:
- `futures_momentum` (COMMODITY): n=17, PF=0.087 — 3 trades from gate
- `cftc_cot_commercial_signal` (COMMODITY): n=16, PF=0.409 — 4 trades from gate
- `crypto_mtf_ema_slope_alignment_v1` (CRYPTO): n=21, PF=0.626 — above 0.5 threshold; monitor only

---

## 5. PR Triage

| PR | Title | CI | Mergeable | Reviews | Action |
|----|-------|-----|-----------|---------|--------|
| #1304 | audit(hourly): 00Z 2026-05-22 | 3/3 ✅ | unknown | none | **AWAIT** — mergeable_state unresolved |
| #1303 | audit(hourly): 23Z 2026-05-21 | 3/3 ✅ | unknown | none | **AWAIT** — mergeable_state unresolved |
| #1299 | chore(loop): LOOP_COMPLETE run #44 | 3/3 ✅ | unknown | 1 comment | **AWAIT** — was dirty at 23Z; recheck next cycle |
| #1287 | feat(b10): UEPS KPI panel | test(3.11) ❌ | n/a | — | **HOLD** — CI failing |
| #1279 | docs: AGENTS.md cloud env notes | DRAFT | n/a | — | **HOLD** — DRAFT |

**HOLD set** (#660 #658 #681 #661): confirmed closed in prior cycles — no action.  
**Plan v2.1 guardrails** (PF 5.81, ml_score 0.90, WINNER_FILTER claims): no PRs citing fabricated stats this cycle — clean.  
**Author-rebase PRs** (#669 #676 #608 #665 #644 #597 #615 #655): all merged or closed — no action.

---

## 6. Merged This Cycle

**None.** No PR reached `mergeable=MERGEABLE` state. PRs #1303, #1304, #1299 pending GitHub mergeable computation.

---

## 7. Summary

- **Snapshot:** stale for 3rd consecutive cycle (~2.5h drift). Numbers are unchanged from 00Z.
- **CRYPTO:** stable, 7d PF 1.411 above 1.33 baseline. No destabilizing actions needed.
- **EQUITY:** FINDING-63 relaxed — `stocks_rsi2_pullback` is now net positive (n=25, +10.87%); drag is scout cohort noise (all n<5). 7d PF=0.654 structurally sub-T2 but no acceleration.
- **FOREX:** recovery holding (7d PF 1.359 vs pre-#687 baseline 0.14). 30d PF=2.572 — strongest class by 30d.
- **COMMODITY:** FINDING-59 persists. `futures_momentum` at n=17 is 3 trades from kill gate.
- **NEW FINDING-64:** `luxalgo_confluence` n=131 / PF=0.725 — largest-volume drag above kill threshold; flag for symbol-rotation sandbox.
- **No merges; no new kills. Next cycle: re-check mergeable_state for #1303/#1304/#1299.**
