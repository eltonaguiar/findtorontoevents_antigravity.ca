# Hourly Audit — 2026-05-19T13:00Z

**Dashboard snapshot:** 2026-05-19T12:14:53Z (FRESH — regenerated mid-13Z cycle, includes all PRs merged today)  
**Recent_closed picks:** n=3500 (cap)  
**Prior audit:** PR #1252 (12Z) — merged this hour  
**Computation base:** `audit_dashboard/data/dashboard_data.json` parsed with 24h/7d/30d cutoffs from snapshot timestamp

---

## Per-Asset Metrics (24h / 7d / 30d)

| Class | 24h PF | 24h n | 7d PF | 7d n | 30d PF | 30d n | 30d WR | Delta vs 12Z |
|-------|--------|-------|-------|------|--------|-------|--------|--------------|
| **CRYPTO** | **2.472** | 279 | **1.121** | 1048 | 1.282 | 2901 | 46.1% | 24h −0.189; 7d −0.031; 30d −0.040 — mild pullback, stable trend |
| EQUITY | 0.000 | 5 | 0.238 | 15 | **1.939** | 95 | 50.5% | 7d n=15 sub-significance; 30d healthy |
| FOREX | 1.304 | 7 | 1.289 | 19 | **2.525** | 93 | 48.4% | 24h +0.025; 7d +0.016 — steady post-kill improvement |
| COMMODITY | 0.000 | 4 | 0.176 | 24 | 1.624 | 58 | 53.4% | 7d −0.017; 30d −0.123 — drag from cftc_cot_commercial_signal |
| ETF | 1.887 | 9 | 0.989 | 20 | 2.005 | 49 | 57.1% | 7d stable; 30d healthy |
| FUTURES | — | 0 | — | 0 | inf | 2 | 100% | n too small |

### Baselines for comparison

| Metric | Documented baseline (issue #686) | 12Z | 13Z (this audit) | Delta 12Z→13Z |
|--------|----------------------------------|-----|-------------------|----------------|
| CRYPTO 24h | PF 3.54 | 2.661 | **2.472** | −0.189 |
| CRYPTO 7d | PF 1.33 | 1.152 | **1.121** | −0.031 |
| CRYPTO 30d | PF 1.33 | 1.322 | **1.282** | −0.040 |
| EQUITY 7d | PF 0.87 | 0.238 | **0.238** | 0 (n=15, insignificant) |
| EQUITY 30d | PF 1.41–2.18 | 1.939 | **1.939** | 0 |
| FOREX 7d | PF 0.14 (pre-#687) | 1.273 | **1.289** | +0.016 ✅ |
| FOREX 30d | PF 0.97 | 2.514 | **2.525** | +0.011 ✅ |

**FOREX delta vs documented baseline: +1.149 (7d), +1.555 (30d) — PRs #687 + #692 confirmed effective.**

---

## PR Triage

**Open PRs:** 0 — all cleared. No merge or hold actions required.

**HOLD set status** (#660 #658 #681 #661 — Plan v2.1 fabrication family): confirmed absent from open PR list.

**Merged today (8 PRs, verified):**
- #684 (48h review), #674 (B11 ETF), #673 (B14 stress), #664 (audit credibility)
- #683 (cftc_cot kill), #687 (P0 JPY-cross BUY rule fix), #692 (kill forex_carry_momentum + goldmine_6x_consensus)
- #694 (quan_engine HYPEUSDT symbol-block)

**Kill verification:**
- `forex_carry_momentum`: 0 picks in 7d ✅
- `goldmine_6x_consensus`: 0 picks in 7d ✅
- `quan_engine/HYPEUSDT`: n=0 in 7d ✅ (PR #694 confirmed)
- `quan_engine/MATICUSDT`: n=0 in 7d ✅

---

## Mutation Analysis

**Source:** `python tools/mutation_analysis.py --json` (13Z)

### New kill candidates (PF<0.5 + n>=20, 7d window)

| Strategy | Class | n | WR | PF | Sum PnL% | Status |
|----------|-------|---|----|----|----------|--------|
| `ensemble` | CRYPTO | 25 | 20.0% | 0.290 | −31.49% | FINDING-15 CONFIRMED — awaiting 3-AI consensus |

No new kill candidates beyond the existing queue.

### FINDING-16 STATUS UPDATE — PARTIALLY RESOLVED

`crypto_mtf_ema_slope_alignment_v1` recovery in fresh dashboard snapshot:

| Snapshot | n | WR | PF |
|----------|---|----|----||
| 12Z (10:19:04Z data) | 24 | 16.7% | 0.294 |
| **13Z (12:14:53Z data)** | **24** | **37.5%** | **0.574** |

WR crossed above the 35% kill floor; PF crossed above 0.5 threshold. **FINDING-16 downgraded from "kill candidate" to "watchlist."** The 12Z snapshot was based on a stale 10:19Z data cut — with fresh 12:14Z data the recovery is confirmed. Will re-check at 14Z.

### Awaiting 3-AI consensus (updated — 7 items)

| # | Strategy | Context | WR | n |
|---|----------|---------|----|----||
| 1 | `ig_contrarian_sentiment` LONG | FOREX/CRYPTO | 16.5% | 200 (all-time) |
| 2 | `myfxbook_retail_contrarian` LONG | FOREX | 13.7% | 124 (all-time) |
| 3 | `quan_engine_swing` LONG | CRYPTO | 26.0% | 104 (all-time) |
| 4 | `forex_rsi2_mean_reversion` LONG | FOREX | 6.8% | 118 (all-time) |
| 5 | `rapid_fire`×UUSDT | CRYPTO | 0% | 34 |
| 6 | `cta_replicator`×NG=F | FUTURES | 0% | 24 |
| 7 | **`ensemble` CRYPTO** | CRYPTO | 20% | 25 (FINDING-15) |

Items 1–4 have n=0 in the 7d window (post-kill dormancy for FOREX strategies; `ig_contrarian_sentiment` 7d n=8). All-time counts from mutation_analysis.py full-pool.

### Near-threshold monitor (n<20 floor, hold)

| Strategy | Class | n (7d) | WR | PF | Note |
|----------|-------|--------|----|----|------|
| `cftc_cot_commercial_signal` | COMMODITY | 18 | 5.6% | 0.133 | 2 picks from floor; pattern matches PR #683 kill family |

**If n reaches 20 next hour: initiate 3-AI consensus for `cftc_cot_commercial_signal` (COMMODITY). Pattern matches `cftc_cot` already killed in PR #683 — criterion (a) satisfied.**

---

## Strategy Performance Snapshot (7d)

### Top winners

| Strategy | n | WR | PF | Sum PnL% |
|----------|---|----|----|----------|
| `st_fear_greed_contrarian` | 196 | 69% | 3.349 | +144.45% |
| `claude_ml_moderate_mut` | 45 | 49% | 1.575 | +21.62% |
| `luxalgo_confluence` | 182 | 44% | 1.075 | +16.92% |

### Top losers

| Strategy | n | WR | PF | Sum PnL% |
|----------|---|----|----|----------|
| `cftc_cot_commercial_signal` | 18 | 6% | 0.133 | −54.76% |
| `ensemble` | 25 | 20% | 0.290 | −31.49% |
| `strong consensus (alpha_engine, ml_crypto_pred)` | 107 | 40% | 0.868 | −19.04% |

`st_fear_greed_contrarian` is the dominant system alpha driver at 7d. Its continuation or reversal is the single most important signal to monitor.

---

## COMMODITY Degradation Flag

COMMODITY 30d PF dropped 0.123 in one hour (1.747→1.624). Driver: `cftc_cot_commercial_signal` (n=18, WR 5.6%, sum −54.76% in 7d). At n=18 this is still 2 trades below the kill floor. However, the 30d degradation combined with the near-floor status warrants escalation to FINDING-17:

**FINDING-17 NEW — `cftc_cot_commercial_signal` approaching kill threshold**

| Metric | Value | Kill threshold |
|--------|-------|----------------|
| n (7d) | 18 | >=20 (not yet met) |
| WR | 5.6% | <35% sustained ✅ |
| PF | 0.133 | <0.5 ✅ |
| Pattern match to PR #683 kill | cftc_cot family | criterion (a) ✅ |

Status: HOLD pending n>=20. Check at 14Z hourly.

---

## Issue Cross-Reference

- **Issue #685** (resolver-rescope DONE): no new PRs claiming resolver scope change observed. Constraint respected.
- **Issue #686** (per-asset attribution): FINDING-15 (ensemble) confirmed active, FINDING-16 resolved, FINDING-17 (cftc_cot_commercial_signal) new. Comment posted this hour.
- **Issue #693** (EQUITY divergence monitor, closed): EQUITY 30d PF 1.939 within documented 1.41-2.18 range ✅. 7d PF 0.238 on n=15 — insignificant sample, no action. `goldmine_6x_consensus` absent from 7d window post-PR-#692 ✅.

---

## Next Hour (14Z) Checklist

- [ ] Re-check `cftc_cot_commercial_signal` n — if >=20, post FINDING-17 to #686 and request 3-AI consensus
- [ ] Re-check `ensemble` CRYPTO — confirm n=25 stable or growing
- [ ] Monitor `crypto_mtf_ema_slope_alignment_v1` — watchlist, confirm WR holds >35%
- [ ] Monitor `st_fear_greed_contrarian` — single largest alpha source; check for reversal
- [ ] CRYPTO 7d trend: 1.152→1.121, 3rd consecutive hour. If drops below 1.0 again, re-flag FINDING-12
- [ ] COMMODITY 30d: 1.747→1.624. If drops below 1.5, escalate

---

*Audit: 2026-05-19T13:00Z | Dashboard: 12:14:53Z | Claude Sonnet 4.6*
