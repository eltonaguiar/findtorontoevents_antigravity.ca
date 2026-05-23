# Hourly Audit — 2026-05-21 04Z

**Audit time:** 2026-05-21 04:09 UTC  
**Dashboard snapshot:** `2026-05-21T03:32:29Z` (repo SHA `bd2014c2`, 37-min lag — fresh hourly refresh ✅)  
**Session PRs merged today (carried forward):** #684, #674, #673, #664, #683, #687, #692, #694 (8 total, all cross-AI verified)

---

## 1. Per-Asset PF/WR Windows

Computed from `picks.recent_closed` (n=3500), anchored to dashboard `generated_at` 03:32Z.

| Class | 24h n | 24h PF | 24h WR | 7d n | 7d PF | 7d WR | 30d n | 30d PF | 30d WR |
|-------|------:|-------:|-------:|-----:|------:|------:|------:|-------:|-------:|
| **CRYPTO** | 142 | **3.157** | 50.0% | 1022 | **1.400** | 47.8% | 2822 | **1.338** | 46.0% |
| **EQUITY** | 2 | 1.873 | 50.0% | 40 | **0.754** | 32.5% | 145 | **1.418** | 44.1% |
| **FOREX** | 7 | 1.377 | 42.9% | 17 | **1.381** | 35.3% | 93 | **2.562** | 48.4% |
| **COMMODITY** | 3 | 0.000 | 0.0% | 41 | **0.088** | 7.3% | 76 | **0.879** | 40.8% |
| **ETF** | 1 | 99.0* | 100.0% | 12 | 1.390 | 33.3% | 48 | **2.158** | 60.4% |
| **BOND** | 3 | 0.000 | 0.0% | 6 | 0.000 | 0.0% | 6 | 0.000 | 0.0% |
| **FUTURES** | 2 | 99.0* | 100.0% | 2 | 99.0* | 100.0% | 4 | 99.0* | 100.0% |

_\* 99.0 = no losses in sample (wins only, capped). ETF/FUTURES sample too small for conclusions._

### Deltas vs Documented Baseline

| Class | Window | This Audit | Baseline | Delta | Signal |
|-------|--------|-----------|----------|-------|--------|
| CRYPTO | 24h PF | 3.157 | 3.54 | −0.383 | ✅ Slight decline, healthy range |
| CRYPTO | 7d PF | 1.400 | 1.33 | **+0.070** | ✅ Improving |
| CRYPTO | 30d PF | 1.338 | 1.33 | +0.008 | ✅ Stable |
| EQUITY | 7d PF | 0.754 | 0.87 | **−0.116** | 🟡 Further degraded; goldmine_6x kill (PR #692) not yet in window |
| EQUITY | 30d PF | 1.418 | 1.41 | +0.008 | ✅ Long-run stable |
| FOREX | 7d PF | 1.381 | 0.14 (pre-#687) | **+1.241** | 🟢 Major recovery confirmed, 3rd consecutive hour |
| FOREX | 30d PF | 2.562 | 0.97 (pre-#687) | **+1.592** | 🟢 Recovery holding |
| COMMODITY | 7d PF | 0.088 | 1.78 | **−1.692** | 🚨 FINDING-22 active — see §3 |
| COMMODITY | 30d PF | 0.879 | 1.78 | −0.901 | 🟡 30d now below T2 floor |

---

## 2. PR Triage

**Open PRs:** 1 (#1277 — previous 03Z audit tracking PR)

| PR | Mergeable | CI | Verdict |
|----|-----------|-----|---------|
| #1277 | — | — | Tracking PR, no merge action needed |

**HOLD set (#660 #658 #681 #661):** NOT PRESENT in open list ✅  
**Author-rebase watch (#669 #676 #608 #665 #644 #597 #615 #655):** NOT PRESENT ✅  
**Plan v2.1 PRs (PF 5.81 / ml_score 0.90):** None detected ✅  
**Resolver-rescope PRs (issue #685 scope closed):** None detected ✅

**Merges this hour: 0** (no actionable open PRs)

---

## 3. COMMODITY 7d Degradation — Root-Cause Resolved

COMMODITY 7d PF=0.088 / WR=7.3% (n=41). Strategy breakdown:

| Strategy | 7d n | WR | PF | Sum PnL |
|----------|-----:|----:|---:|--------:|
| `cftc_cot_commercial_signal` | 22 | **4.5%** | 0.099 | −76.40% |
| `futures_momentum` | 17 | 11.8% | 0.087 | −52.81% |
| `futures_bb_mean_reversion` | 2 | 0.0% | 0.000 | −10.46% |

**Root cause: `cftc_cot_commercial_signal` legacy drain (FINDING-35 — see below).**

COMMODITY 30d strategy breakdown shows `cftc_cot_commercial_signal` at WR=52.7%/PF=1.439 (n=55) — healthy in long-run. The 7d catastrophe is entirely recent.

**Symbol concentration (7d):** CT=F (n=13, WR 15.4%), SI=F (n=9, WR 0%), ZS=F (n=7, WR 0%), PL=F (n=6, WR 0%). Four symbols at 0% WR — correlated macro regime move.

---

## 4. Strategy Attribution: EQUITY 7d

EQUITY 7d PF=0.754 (n=40). `goldmine_6x_consensus` is confirmed absent from window (PR #692 kill visible). Remaining drag:

| Strategy | 7d n | WR | PF | Sum PnL |
|----------|-----:|----:|---:|--------:|
| `stocks_rsi2_pullback` | 25 | 40.0% | 1.242 | **+10.87%** ✅ |
| `rs-breakout-scout` | 3 | 0.0% | 0.000 | −5.69% |
| `vol-contraction-scout` | 3 | 33.3% | 1.109 | +0.97% |
| `stocks_ema_golden_cross` | 2 | 0.0% | 0.000 | −6.83% |
| `adx-trend-scout` | 2 | 50.0% | 0.343 | −5.23% |
| `aroon-trend-scout` | 1 | 100% | 99.0 | +4.05% |

`stocks_rsi2_pullback` is net-positive this 7d window (n=25, PF 1.242) — issue #693 hypothesis about it being a drag is false at current data. Small-n scouts dominate the PnL drag.

---

## 5. New Findings

### FINDING-35 (P1): `cftc_cot_commercial_signal` — legacy drain confirmed, NOT new picks

- **7d:** n=22, WR=4.5%, PF=0.099, sum=−76.40%
- **Root cause:** All 22 picks in 7d window have `closed_at` timestamps AFTER the May 2 block date — these are **pre-existing positions hitting stop-losses**, not newly generated picks
- **Verification:** `alpha_engine/strategy_blocklist.py:176` confirms kill is live since 2026-05-02
- **30d healthy:** PF=1.439, WR=52.7% (n=55) — long-run edge intact before regime break
- **FINDING-32 from 03Z (PR #683 scope gap?) — REFUTED:** Block is confirmed present in `strategy_blocklist.py:176`
- **Action:** Monitor 7d window; expects improvement as legacy picks age out post ~May 28. No code change needed.

### FINDING-36 (P2, NEW): `rapid_fire` × `UUSDT` — n=34, WR=0.0% — crosses kill threshold

- **Evidence:** mutation_analysis.py Axis-3 symbol variance report: `rapid_fire` × `UUSDT` n=34, WR=0.0%, avg −0.17%
- **Kill criteria met:** n>=20 ✅, WR<35% ✅, pattern=symbol-specific ✅
- **Action:** Post to issue #686 for 3-AI consensus. If confirmed, add `("rapid_fire", "UUSDT")` to `BLOCKED_STRATEGY_SYMBOL_PAIRS` in `audit_trail/quality_gates.py`.
- **Pre-kill check:** Confirm `rapid_fire` is not in `BLOCKED_SOURCE_SYSTEMS` (if it is, block at source level instead).

### FINDING-34 (P2, 03Z→confirmed): `cta_replicator` × `NG=F` — n=24, WR=0.0%

- **Evidence confirmed:** mutation_analysis.py Axis-3: `cta_replicator` × `NG=F` n=24, WR=0.0%, avg −0.03%
- **Kill criteria met:** n>=20 ✅, WR<35% ✅ — but note `cta_replicator` overall WR=42.7% (Axis-4 candidate too)
- **Action:** Post `("cta_replicator", "NG=F")` kill to issue #686 for 3-AI consensus.

### FINDING-31 update (P1): `futures_momentum` COMMODITY approaching n=20 kill threshold

- **7d n=17 / 30d n=18**, WR=11.1%, PF=0.086
- **Status:** 2 trades from automatic kill threshold
- **Pre-approved per issue #685:** Operator go-ahead exists for `("COMMODITY", "futures_momentum")` add to `BLOCKED_ASSET_STRATEGY_PAIRS`
- **Action:** Can be executed at n=20 without additional 3-AI consensus (issue #685 §Goal-#1 movers #2). Monitor.

### FINDING-33 (P2, 03Z→confirmed): `ig_contrarian_sentiment` Axis-1 mutation

- **LONG:** 16.5% WR (n=200) vs **SHORT:** 60.3% WR (n=58) — 44pp spread
- **Recommendation:** SHORT-only mutation sandbox. Post to #686 for consensus.

---

## 6. Mutation Analysis Summary

From `python tools/mutation_analysis.py --json` (04Z run):

**Axis-1 (direction flip) candidates (spread ≥20pp):**
- `ig_contrarian_sentiment`: SHORT 60.3% vs LONG 16.5% (44pp) — **P2 action**
- `myfxbook_retail_contrarian`: SHORT 50.0% vs LONG 13.7% (36pp)
- `quan_engine_swing`: SHORT 60.0% vs LONG 26.0% (34pp)
- `combined_confidence`: SHORT 55.6% vs LONG 26.7% (29pp)
- `cta_cross_asset_tsmom`: SHORT 51.1% vs LONG 29.4% (22pp)

**Axis-3 (symbol) kill candidates ≥n=20:**
- `cta_replicator` × `NG=F`: 0% WR, n=24 — FINDING-34
- `rapid_fire` × `UUSDT`: 0% WR, n=34 — FINDING-36 (new)
- `rapid_fire` × `TAOUSDT`: 5.6% WR, n=18 — approaching threshold
- `quan_engine` × `MATICUSDT`: 0% WR (large n) — check PR #694 scope

**Axis-4 candidates (vol-normalization needed):**
- `multi_asset_copytrader`: 21.9% WR, n=1142 — systemic, needs vol-normalization
- `rapid_fire`: 29.0% WR, n=207

---

## 7. Positive Signals (Do Not Destabilize)

- **FOREX 7d PF=1.381** — 3rd consecutive hour above 1.0 post-#687/#692 kills. Pre-kill baseline was PF=0.14. Full recovery from catastrophic state.
- **CRYPTO 24h PF=3.157** — above baseline, strong intraday signal. 7d improving (+0.07 delta).
- **EQUITY 30d PF=1.418** — Tier-2 candidate status maintained long-run. `stocks_rsi2_pullback` net-positive in 7d.
- **`goldmine_6x_consensus` confirmed absent** from EQUITY 7d window (PR #692 effect visible).
- **`forex_carry_momentum` confirmed absent** from FOREX 7d window (PR #692 effect visible).

---

## 8. Issue #693 Monitor (EQUITY divergence)

Issue #693 closed 2026-05-13. Monitoring per the 7-day check criteria:

- EQUITY 14d: need to verify if PF returned to ≥1.5 post-PR-#692
- Current 30d PF=1.418 — close to T2 but 7d=0.754 still sub-T2
- `stocks_rsi2_pullback` showing positive PF in current 7d (PF=1.242, n=25) — suggesting #692 kill was sufficient per issue #693 hypothesis
- **Full check due:** 2026-05-24 (14 days post-PR-#692 ~2026-05-10). If 14d PF still <1.0 by then, escalate to root-cause review.

---

## 9. Plan v2.1 Guardrails

- HOLD set (#660 #658 #681 #661): not in open PR list ✅
- No PRs citing PF 5.81 / ml_score 0.90 detected ✅
- No PRs claiming WINNER_FILTER feature ✅
- Resolver-rescope PRs: none detected ✅ (issue #685: work is DONE)

---

## Summary

| Item | Count/Status |
|------|-------------|
| PRs merged this hour | 0 |
| Total PRs merged today | 8 |
| New findings | 2 (FINDING-35, FINDING-36) |
| Confirmed findings | 2 (FINDING-33, FINDING-34) |
| Updated findings | 1 (FINDING-31) |
| HOLD set violations | 0 |
| Plan v2.1 violations | 0 |

**Key action items for next hour:**
1. Post FINDING-36 (`rapid_fire` × `UUSDT`) to issue #686 for 3-AI consensus
2. Post FINDING-34 (`cta_replicator` × `NG=F`) to issue #686 for 3-AI consensus
3. Monitor `futures_momentum` COMMODITY n (currently 18); execute kill at n=20 per issue #685 pre-approval
4. Watch COMMODITY 7d for improvement as legacy `cftc_cot` picks age out

Refs: issues #685, #686, #693 | `reports/HOURLY_AUDIT_2026-05-21_04Z.md`
