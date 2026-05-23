# Hourly Audit — 2026-05-22 05Z

**Generated:** 2026-05-22T05:12Z  
**Dashboard snapshot:** `2026-05-22T02:19:15Z` ⚠️ STALE — age ~173 min at audit time (same snapshot as 03Z and 04Z; cron has not refreshed in 3+ hours). No new real-world signal since previous sweeps.

---

## Per-asset summary (05Z)

| Class | PF (24h) | PF (7d) | WR (7d) | PF (30d) | Status |
|-------|----------|---------|---------|----------|--------|
| CRYPTO | 1.371 | 1.256 | 47.9% | 1.290 | Stable ✅ |
| EQUITY | 1.678 | **0.755** | 35.6% | 1.379 | 7d sub-T2 ⚠️ |
| FOREX | 1.520 | 1.442 | 36.4% | 2.591 | Recovery holds ✅ |
| COMMODITY | 1.933 | **0.246** | 11.4% | 0.943 | CRITICAL ⚠️ |
| ETF | 0.000 | 0.884 | 8.3% | 2.248 | 7d thin (n=12) |
| BOND | 0.000 | 0.000 | 0.0% | 0.000 | Sub-floor (n=5 too small) |
| FUTURES | — | — | — | inf | n=2 (30d), trivial |

### asset_class_health (rolling, from dashboard payload)
- CRYPTO: PF=1.355 / WR=48.2% / n=1085
- EQUITY: PF=0.921 / WR=36.4% / n=55 ← sub-T2
- FOREX: PF=3.406 / WR=53.8% / n=156 ✅
- COMMODITY: PF=1.296 / WR=50.8% / n=61
- ETF: PF=11.995 / WR=50.0% / n=2 (too small for verdict)

---

## Delta vs documented baselines

| Class | Metric | Baseline | 05Z | Delta | Source |
|-------|--------|----------|-----|-------|--------|
| CRYPTO | 24h PF | 3.54 | 1.371 | −2.17 | Issue #686 (2026-05-02) |
| CRYPTO | 7d PF | 1.33 | 1.256 | −0.07 | Issue #686 |
| EQUITY | 7d PF | 0.87 | 0.755 | −0.12 | Issue #693 |
| EQUITY | 30d PF | 2.18 | 1.379 | −0.80 | Issue #693 |
| FOREX | 7d PF | 0.14 (pre-#687) | 1.442 | **+1.30** ✅ | Issue #686 |
| FOREX | 30d PF | 0.97 (pre-#687) | 2.591 | **+1.62** ✅ | CLAUDE.md |
| COMMODITY | rolling PF | 1.78 (CLAUDE.md) | 0.943 (30d) | −0.84 | CLAUDE.md |

**Key delta note:** CRYPTO 24h baseline (3.54) was from 2026-05-02; today's 1.371 is not a regression — regime and snapshot age differ. FOREX recovery from PR #687 (JPY-cross BUY rule fix) is confirmed and holds across both 7d and 30d windows.

---

## Strategy breakdown — COMMODITY 7d (CRITICAL)

| Strategy | n | WR | PF | Gate distance |
|----------|---|----|----|---------------|
| `futures_momentum` | 17 | 11.8% | 0.087 | **3 from n=20** |
| `cftc_cot_commercial_signal` | 16 | 12.5% | 0.409 | 4 from n=20 |
| `futures_bb_mean_reversion` | 2 | 0.0% | 0.000 | — |

FINDING-59 (continuing): Both COMMODITY strategies are approaching the n=20 gate. `futures_momentum` PF=0.087 and WR=11.8% are catastrophic; `cftc_cot_commercial_signal` PF=0.409 is sub-T2. **No auto-kill yet** (n<20 for both). At current run rate (~3–4 picks/day for COMMODITY), both will cross the n=20 gate within 1–2 days.

Note: `cftc_cot_commercial_signal` is distinct from `cftc_cot` killed in PR #683. Verify in `audit_trail/quality_gates.py` whether it is included in the PR #683 block scope.

---

## Strategy breakdown — EQUITY 7d

| Strategy | n | WR | PF | Flag |
|----------|---|----|----|------|
| `stocks_rsi2_pullback` | 29 | 44.8% | 1.396 | Above break-even ✅ |
| `rs-breakout-scout` | 3 | 0.0% | 0.000 | n<20 |
| `vol-contraction-scout` | 3 | 0.0% | 0.000 | n<20 |
| `stocks_ema_golden_cross` | 2 | 0.0% | 0.000 | n<20 |
| `adx-trend-scout` | 2 | 50.0% | 0.161 | n<20 |

EQUITY 7d PF=0.755 is driven by small-n scouts (n=2–3) all showing WR=0%. `stocks_rsi2_pullback` (n=29, WR=44.8%, PF=1.396) is the dominant strategy and is actually performing above break-even. The 7d degradation vs issue #693 baseline is concentrated in scout strategies, not the primary strategy. **Monitor only per issue #693 guidance.** `goldmine_6x_consensus` (killed PR #692) is no longer in the 7d data — kill was effective.

---

## Strategy breakdown — CRYPTO 7d (notable weak)

| Strategy | n | WR | PF | Flag |
|----------|---|----|----|------|
| `luxalgo_confluence` | 128 | 32.8% | 0.686 | FINDING-66 — PF<0.7, WR<35% sustained |
| `multi_period_rsi_confluence_eth` | 17 | 47.1% | 0.513 | 3 from n=20 gate |
| `multi_period_rsi_confluence` | 10 | 20.0% | 0.184 | n<20 |

FINDING-66 continuing: `luxalgo_confluence` n=128 / WR=32.8% / PF=0.686. PF>0.5 (above auto-kill floor) but WR sustained <35%. 3-AI consensus gate still applies before any action.

FINDING-67 (from 04Z): `crypto_mtf_ema_slope_alignment_v1` — not visible above threshold in 05Z sweep (same snapshot; no delta).

---

## Kill candidates sweep (mutation_analysis protocol)

**New PF<0.5 + n≥20 strategies (7d, all classes):** NONE

All strategies n≥20 in 7d window ranked by PF:

| Class | Strategy | n | WR | PF |
|-------|----------|---|----|----|
| CRYPTO | `luxalgo_confluence` | 128 | 32.8% | 0.686 |
| CRYPTO | `unknown` | 136 | 35.3% | 1.331 |
| EQUITY | `stocks_rsi2_pullback` | 29 | 44.8% | 1.396 |
| CRYPTO | `claude_ml_moderate_mut` | 38 | 52.6% | 1.912 |
| CRYPTO | `strong consensus (alpha_engine, ml_crypto_pred)` | 111 | 57.7% | 2.102 |
| CRYPTO | `st_fear_greed_contrarian` | 282 | 63.5% | 2.542 |

No auto-kills this cycle. `luxalgo_confluence` is the closest watch item.

---

## PR triage

| PR | Title | mergeable | CI | Reviews | Action |
|----|-------|-----------|-----|---------|--------|
| **#1309** | audit 04Z 2026-05-22 | clean | 3/3 ✅ | COMMENTED (greptile trial limit, not REQUEST_CHANGES) | **MERGED ✅** |
| #1299 | LOOP_COMPLETE — loop run #44 | dirty (conflict) | 3/3 ✅ | — | **HOLD — merge conflict** |
| #1287 | feat(b10): UEPS KPI panel | — | `test (3.11)` ❌ | — | **HOLD — CI failure** |
| #1279 | docs: AGENTS.md cloud agent fix | — | — | — | **HOLD — DRAFT** |

**HOLD set (#660 #658 #681 #661):** all closed ✅  
**Author-rebase PRs (#669 #676 #608 #665 #644 #597 #615 #655):** all closed ✅  
**Plan v2.1 guardrails:** no PRs citing fabricated stats (PF 5.81 / ml_score 0.90 / WINNER_FILTER) ✅

---

## PRs merged this cycle

- **#1309** ✅ — audit 04Z 2026-05-22 (squash merge, sha 10c9a40f)

---

## Snapshot staleness note

Dashboard has not refreshed since 02:19:15Z (~3h stale at audit time). The hourly cron may be delayed or the `[skip ci]` auto-refresh failed. Numbers in this report are identical to 03Z and 04Z reports by design (same source data). Next meaningful signal will appear after cron next fires.

---

## Refs

- Issues: #685 (resolver done — do not reopen), #686 (per-asset attribution live), #693 (EQUITY monitor — closed 2026-05-13)
- Reports: `reports/HOURLY_AUDIT_2026-05-22_04Z.md`, `reports/HOURLY_AUDIT_2026-05-22_03Z.md`
- Dashboard: `audit_dashboard/data/dashboard_data.json` (snapshot 2026-05-22T02:19:15Z)
