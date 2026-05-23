# Hourly Audit — 2026-05-22 02Z

**Generated:** 2026-05-22T02:08Z  
**Dashboard snapshot:** `2026-05-22T01:05:41Z` ✅ FRESH — cron fired after 3 stale cycles (23Z/00Z/01Z were all stale at 22:45Z). Age at audit time: ~63 min.

---

## Per-asset summary (02Z) — fresh snapshot

| Class | PF (24h) | PF (7d) | WR (7d) | PF (30d) | Status | vs Baseline |
|-------|----------|---------|---------|---------|--------|-------------|
| CRYPTO | **1.599** | 1.291 | 48.5% | 1.297 | Stable ✅ | 24h −1.94 vs 3.54 baseline; 7d −0.039 vs 1.33 |
| EQUITY | 0.300 | **0.654** | **30.8%** | 1.349 | Sub-T2; FINDING-63 active | 7d −0.216 vs 0.87 pre-#692; unchanged 4 cycles |
| FOREX | 1.438 | 1.363 | 30.0% | **2.574** | Recovery confirmed ✅ | 7d +1.22 vs 0.14 pre-#687; 30d +1.60 |
| COMMODITY | 1.933 | **0.246** | **11.4%** | 0.943 | FINDING-59 critical ⚠️ | 7d+30d sub-1; n=20 kill gate imminent |
| ETF | 0.000 | 0.884 | 8.3% | 2.248 | Thin n | — |
| BOND | 0.000 | 0.000 | 0.0% | 0.000 | Sub-floor (n=5-7) | — |

**asset_class_health (rolling, from fresh snapshot):**

| Class | PF | WR | n |
|-------|----|----|---|
| FOREX | 1.368 | 53.5% | 155 |
| COMMODITY | 1.296 | 50.8% | 61 |
| CRYPTO | 1.286 | 48.3% | 1137 |
| EQUITY | 0.921 | 36.4% | 55 |
| FUTURES | 0.956 | 16.7% | 12 |
| BOND | 0.000 | 0.0% | 7 |

---

## FINDING-59 (COMMODITY) — CRITICAL: 3–4 trades from n=20 kill gate

Per fresh 7d per-strategy breakdown (n=35 total COMMODITY 7d):

| Strategy | n | WR | sumPnL% | Status |
|----------|---|----|---------|--------|
| `futures_momentum` | 17 | **11.8%** | **−52.81%** | ⚠️ 3 trades from kill gate (n=20) |
| `cftc_cot_commercial_signal` | 16 | **12.5%** | **−42.92%** | 4 trades from gate (already killed in PR #683 — residual) |
| `futures_bb_mean_reversion` | 2 | 0.0% | −10.46% | n<20, monitor |

**Action:** `futures_momentum` is 3 trades away from the n=20 kill gate. At current rate (~5 trades/day), kill gate will be hit within 24–48h. Per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`: begin Axis-1 (direction flip) mutation prep now so the kill PR is ready when n=20 triggers. Do NOT wait until gate is hit to start mutation analysis.

`cftc_cot_commercial_signal` n=16: PR #683 killed this. The n=16 in recent_closed is residual from pre-kill picks. No action.

---

## FINDING-63 (EQUITY) — Unchanged; scout cohort is drag

Per fresh 7d per-strategy breakdown (n=39 total EQUITY 7d):

| Strategy | n | WR | sumPnL% |
|----------|---|----|---------|
| `stocks_rsi2_pullback` | 25 | **40.0%** | **+10.87%** | ✅ positive contributor |
| `rs-breakout-scout` | 3 | 0.0% | −8.65% | n<20 |
| `vol-contraction-scout` | 3 | 0.0% | −10.18% | n<20 |
| `stocks_ema_golden_cross` | 2 | 0.0% | −6.83% | n<20 |
| `adx-trend-scout` | 2 | 50.0% | −6.68% | n<20 |
| `macd-hidden-div-scout` | 1 | 0.0% | −6.68% | n<20 |
| `price-accel-scout` | 1 | 0.0% | −6.92% | n<20 |

Consistent with 00Z/01Z attribution. `stocks_rsi2_pullback` is **positive** (+10.87%). The 7d drag is entirely from the scout cohort (n=1-3 each), all below kill floor. **No kill action required.** FINDING-63 status: **MONITORING** — trigger `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` if `stocks_rsi2_pullback` WR falls below 40% at n≥50.

---

## FINDING-64 (CRYPTO) — `luxalgo_confluence` volume drag (persists)

Per fresh 7d CRYPTO per-strategy (underperformers with n≥20):

| Strategy | n | WR | PF | sumPnL% |
|----------|---|----|----|---------|
| `luxalgo_confluence` | 131 | 34.4% | **0.727** | **−52.38%** |
| `crypto_mtf_ema_slope_alignment_v1` | 21 | 47.6% | **0.626** | −2.28% |

**`luxalgo_confluence`**: PF=0.727 is above the PF<0.5 kill gate but is the single largest-n drag on system-wide CRYPTO PF. Axis-2 (symbol rotation) sandbox flagged per 01Z audit. **No kill action this cycle.**

**NEW — FINDING-65: `crypto_mtf_ema_slope_alignment_v1`** n=21, WR=47.6%, PF=0.626. Crosses n=20 kill gate for the first time this cycle. PF=0.626 is above PF<0.5 threshold — **no kill**, but flag for 3-AI review per mutation protocol. Post to issue #686.

**CRYPTO positive signals:** `st_fear_greed_contrarian` n=282, WR=63.5%, PF=2.542 (strong); `strong consensus (alpha_engine, ml_crypto_pred)` n=111, WR=54.1%, PF=1.898 (strong). 24h WR=50.0% / PF=1.599 — healthy short-term.

---

## Mutation analysis — no new kills

`python tools/mutation_analysis.py --json` output reviewed (fresh run):

**No new strategies meet PF<0.5 + n≥20 kill criteria.**

Closest-to-gate:
- `futures_momentum` (COMMODITY): n=17, WR=11.8% — 3 from kill gate. Axis-1 prep now.
- `cta_replicator`×NG=F (FINDING-60): n=24, WR=0% — awaiting 3-AI consensus.
- `rapid_fire`×UUSDT (FINDING-61): n=34, WR=0% — awaiting 3-AI consensus.
- `crypto_mtf_ema_slope_alignment_v1` (FINDING-65): n=21, PF=0.626 — above threshold, flag only.

Direction-flip candidates (Axis-1, no kill pending 3-AI consensus):
- `ig_contrarian_sentiment` LONG WR=16.5% (n=200)
- `myfxbook_retail_contrarian` LONG WR=13.7% (n=124)
- `cta_cross_asset_tsmom` LONG WR=29.4% (n=85)

---

## PR triage

| PR | Title | CI | Mergeable | Reviews | Action |
|----|-------|----|-----------|---------|--------|
| #1303 | audit 23Z 2026-05-21 | 3/3 ✅ | clean | Greptile COMMENTED only | **MERGED** ✅ |
| #1304 | audit 00Z 2026-05-22 | 3/3 ✅ | clean | Greptile COMMENTED only | **MERGED** ✅ |
| #1305 | audit 01Z 2026-05-22 | 3/3 ✅ | clean | Greptile COMMENTED only | **MERGED** ✅ |
| #1299 | chore(loop): LOOP_COMPLETE | 3/3 ✅ | **dirty** | — | HOLD (conflict) |
| #1287 | feat(B10) UEPS KPI panel | test(3.11) ❌ | — | — | HOLD (CI failure) |
| #1279 | docs: correct AGENTS.md | — | — | — | HOLD (DRAFT) |

**HOLD set (#660 #658 #681 #661):** all closed per previous audits ✅  
**Author-rebase PRs (#669 #676 #608 #665 #644 #597 #615 #655):** all merged/closed per 23Z audit ✅  
**Plan v2.1 guardrails:** clean ✅  
**Issue #685 directive:** resolver-rescope PRs auto-rejected; no such PRs open ✅

---

## Deltas vs documented baseline

| Metric | Baseline | Current | Delta | Note |
|--------|----------|---------|-------|------|
| CRYPTO 24h PF | 3.54 | 1.599 | −1.94 | Baseline from 2026-05-02; long-run normal |
| CRYPTO 7d PF | 1.33 | 1.291 | −0.039 | Flat |
| CRYPTO 30d PF | 1.33 | 1.297 | −0.033 | Flat |
| EQUITY 7d PF | 0.87 pre-#692 | 0.654 | −0.216 | Persistent; scout cohort drag (n<20) |
| EQUITY 30d PF | 1.41–2.18 | 1.349 | Near floor | Monitor |
| FOREX 7d PF | 0.14 pre-#687 | 1.363 | **+1.22** | PR #687 JPY-cross fix holding ✅ |
| FOREX 30d PF | 0.97 pre-#687 | 2.574 | **+1.60** | PR #687 JPY-cross fix holding ✅ |
| COMMODITY 7d PF | — | 0.246 | Sub-floor | FINDING-59: n=20 gate imminent |

---

## Summary

- **Snapshot:** FRESH (cron finally fired at 01:05Z after 2.5h stale period).
- **Merges:** #1303, #1304, #1305 merged ✅ (3 previous audit PRs).
- **No new kills:** mutation gate clean. `futures_momentum` is 3 trades from kill gate — prep Axis-1 mutation now.
- **FINDING-65 (NEW):** `crypto_mtf_ema_slope_alignment_v1` n=21, PF=0.626 — above kill gate but flagged for 3-AI consensus.
- **FINDING-59 (CRITICAL):** `futures_momentum` n=17 approaching kill gate; COMMODITY 7d PF=0.246 worst in system.
- **FOREX recovery confirmed** across both windowed and rolling metrics.
- **EQUITY 7d drag** unchanged — scout cohort n<20, no kill; `stocks_rsi2_pullback` is now positive.

Refs: issues #685 #686 #693 | `tools/mutation_analysis.py` (fresh run 2026-05-22T02:08Z)
