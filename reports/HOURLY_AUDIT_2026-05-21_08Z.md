# Hourly Audit — 2026-05-21 08Z

**Dashboard snapshot:** `2026-05-21T07:04:40Z` (FRESH — cron ran 07:00Z, +1h08m since 06Z snapshot `05:56Z`)  
**Computed at:** 2026-05-21T08:09Z  
**Refs:** issues #685, #686, #693 | prev: `reports/HOURLY_AUDIT_2026-05-21_07Z.md` (PR #1282)

---

## Per-Asset Summary (windowed metrics from `picks.recent_closed`, n=3500)

| Class | 24h PF | 24h n | 7d PF | 7d WR | 7d n | 30d PF | 30d WR | 30d n |
|-------|--------|-------|-------|-------|------|--------|--------|-------|
| CRYPTO | 3.499 | 79 | 1.502 | 49.3% | 893 | 1.372 | 46.5% | 2703 |
| EQUITY | **1.390** | 14 | 0.864 | 38.5% | 52 | 1.411 | 45.2% | 157 |
| FOREX | 1.378 | 7 | 1.024 | 31.2% | 16 | 2.560 | 48.4% | 93 |
| COMMODITY | 0.000 | 3 | 0.088 | 7.3% | 41 | 0.879 | 40.8% | 76 |
| ETF | — | 0 | 1.322 | 27.3% | 11 | 2.121 | 59.6% | 47 |
| BOND | 0.000 | 1 | 0.000 | 0.0% | 4 | 0.000 | 0.0% | 4 |
| FUTURES | — | 0 | — | — | 0 | 999.0 | 100% | 2 |

### `asset_class_health` (resolver-v2, long-run — UPDATED from 07:04Z snapshot)

| Class | PF | WR | n | Status | Delta vs 06Z |
|-------|----|----|---|--------|-------------|
| CRYPTO | 1.280 | 48.3% | 1117 | stable | ±0 |
| FOREX | **1.408** | 54.6% | 152 | stable | **−1.283** (was 2.691) |
| COMMODITY | 1.238 | 51.7% | 58 | candidate | ±0 |
| EQUITY | **0.921** | 36.4% | 55 | candidate | **+0.352** (was 0.569) |
| ETF | 11.99 | 50.0% | 2 | insufficient_data | ±0 |
| BOND | 0.000 | 0.0% | 6 | insufficient_data | ±0 |
| FUTURES | 0.956 | 16.7% | 12 | thin_sample | (new) |

> **FOREX asset_class_health drop 2.691→1.408:** likely driven by new resolved trades in the 07Z cron run (post-PR-#687 JPY-cross-fix picks rotating in). Windowed 30d PF 2.560 unchanged; this may be a resolver-version artifact resolving older pre-fix picks. Monitor — do not act.
> **EQUITY asset_class_health improvement 0.569→0.921:** consistent with goldmine_6x_consensus kill (PR #692) and stocks_rsi2_pullback 7d recovery noted in 06Z audit.

---

## Deltas vs 07Z Baseline (PR #1282, snapshot 2026-05-21T05:56Z)

| Class | Metric | 07Z | 08Z | Delta | Signal |
|-------|--------|-----|-----|-------|--------|
| CRYPTO | 24h PF | 3.446 | 3.499 | +0.053 | ✅ |
| CRYPTO | 7d PF | 1.483 | 1.502 | +0.019 | ✅ |
| CRYPTO | 30d PF | 1.370 | 1.372 | +0.002 | ✅ |
| EQUITY | 24h PF | 1.078 | **1.390** | **+0.312** | ✅✅ significant |
| EQUITY | 7d PF | 0.759 | 0.864 | +0.105 | 🟡 improving, still sub-T2 |
| EQUITY | 30d PF | 1.399 | 1.411 | +0.012 | 🟡 |
| FOREX | 7d PF | 1.391 | 1.024 | −0.367 | 🟡 drop but **7th consecutive hr ≥1.0** |
| COMMODITY | 7d PF | 0.088 | 0.088 | ±0.000 | 🔴 bypass persistent |
| ETF | 7d PF | 1.322 | 1.322 | ±0.000 | ✅ stable |

---

## PR Triage

| PR | State | CI | Reviews | Action |
|----|-------|----|---------|--------|
| #1282 (07Z audit) | open → **MERGED** ✅ | 3/3 green | greptile bot COMMENT only | Merged squash |
| #1279 (AGENTS.md docs) | DRAFT | — | — | No merge — DRAFT |
| HOLD set (#660 #658 #681 #661) | Not present | — | — | ✅ |
| Author-rebase watch (#669 #676 #608 #665 #644 #597 #615 #655) | Not present | — | — | ✅ previously merged |

**Merges this hour: 1** (#1282)  
**Session total (task brief + prior): 13** (#684 #674 #673 #664 #683 #687 #692 #694 #1277 #1278 #1281 #1282 + this hour)

---

## New Findings (08Z mutation_analysis.py run)

### FINDING-46 (WATCH): `ig_contrarian_sentiment` SHORT side surge n=7→58

`ig_contrarian_sentiment` direction split (from 08Z `mutation_analysis.py`):

| Direction | n | WR | Avg PnL% |
|-----------|---|----|----------|
| LONG | 200 | 16.5% | −0.00% |
| SHORT | **58** | **60.3%** | +0.00% |
| **Spread** | | **44pp** | |

SHORT side grew from n=7 (06Z) to n=58 — **51 new SHORT trades** in ~2 hours. LONG side (n=200, WR=16.5%) unchanged — already tracked, 7th+ Claude voice for LONG-block. **SHORT direction is performing well; LONG direction remains the kill candidate.**

Action: update FINDING-37 to reflect SHORT-side health. LONG block still awaiting 2nd + 3rd AI voice. Do NOT block SHORT direction.

### `combined_confidence` LONG WR=26.7% n=15 — BELOW FLOOR

- LONG: n=15, WR=26.7% — **n<20 kill floor, no action**
- SHORT: n=9, WR=55.6%
- Watch only; escalate when n_LONG ≥ 20

---

## Kill Queue Status (08Z)

| # | Finding | n | WR | Criteria | Status |
|---|---------|---|----|----------|--------|
| FINDING-22 | `cftc_cot_commercial_signal` × COMMODITY | 22 | 4.5% | ✅ all 3 met | 1/3 AI — awaiting 2nd+3rd |
| FINDING-34 | `cta_replicator` × NG=F | 24 | 0.0% | ✅ all 3 met | 1/3 AI — awaiting 2nd+3rd |
| FINDING-36 | `rapid_fire` × UUSDT | 34 | 0.0% | ✅ all 3 met | 1/3 AI — awaiting 2nd+3rd |
| FINDING-37 | `ig_contrarian_sentiment` LONG | 200 | 16.5% | ✅ all 3 met | 1/3 AI — awaiting 2nd+3rd |
| FINDING-39 | `myfxbook_retail_contrarian` LONG | 124 | 13.7% | ✅ all 3 met | P1, 1/3 AI — awaiting 2nd+3rd |
| FINDING-44 | `quan_engine_swing` LONG | 104 | 26.0% | ✅ all 3 met | P2, 1/3 AI — awaiting 2nd+3rd |
| FINDING-45 | `cta_cross_asset_tsmom` LONG | 85 | 29.4% | n≥20✅ WR<35%✅ sustained?⚠ | P3 watch |
| FINDING-43 | `crypto_mtf_ema_slope_alignment_v1` | 29 | 34.5% (7d) | 30d PF=1.070 healthy | Watch only |
| FINDING-31 | `futures_momentum` × COMMODITY | 17 | 11.8% | n=17<20 | 3 picks from floor |
| FINDING-46 | `combined_confidence` LONG | 15 | 26.7% | n=15<20 | Watch — not actionable |

---

## Positive Signals

- CRYPTO improving across all three windows for **6th consecutive audit** ✅
- `st_fear_greed_contrarian` Tier-1 anchor holding (from 06Z: n=261/7d, WR=64%, PF=2.627) ✅
- FOREX 7d PF=1.024 — **7th consecutive hour ≥1.0** (baseline: PF 0.14 pre-#687/#692) ✅
- EQUITY 24h PF improved significantly: 1.078→1.390, WR=57.1% (14 trades) ✅
- EQUITY asset_class_health PF improved: 0.569→0.921 ✅ (goldmine_6x kill effect)
- All confirmed kills absent from 7d window: `forex_carry_momentum` / `goldmine_6x_consensus` / `cftc_cot` ✅

---

## Plan v2.1 Guardrails

- HOLD set (#660 #658 #681 #661): not present ✅
- No PRs citing PF 5.81 / ml_score 0.90 / WINNER_FILTER ✅
- Resolver-rescope PRs: none detected ✅ (issue #685: DONE)

---

## Next Action Queue

| Priority | Action | Gate |
|----------|--------|------|
| P1 | `cftc_cot_commercial_signal` × COMMODITY kill | **2nd + 3rd AI vote needed** |
| P1 | `myfxbook_retail_contrarian` LONG-block | **2nd + 3rd AI vote needed** |
| P2 | `ig_contrarian_sentiment` LONG-block (FINDING-37/46) | **2nd + 3rd AI vote needed** |
| P2 | `cta_replicator × NG=F` symbol-block | **2nd + 3rd AI vote needed** |
| P2 | `rapid_fire × UUSDT` symbol-block | **2nd + 3rd AI vote needed** |
| P3 | `quan_engine_swing` LONG mutation (FINDING-44) | 2nd+3rd AI vote |
| P3 | COMMODITY bypass root-cause (multi_asset_copytrader loophole) | Design needed |

---

_Generated by Claude Sonnet 4.6 — 2026-05-21T08Z_  
_Full context: issues #685 #686 #693_
