# Hourly Audit — 2026-05-21 06Z

**Dashboard snapshot:** `2026-05-21T05:56:20Z` (fresh, +1h14m since 05Z snapshot)  
**Computed at:** 2026-05-21T06:09Z  
**Refs:** issues #685, #686, #693 | prev: `reports/HOURLY_AUDIT_2026-05-21_05Z.md` (PR #1280)

---

## Per-Asset Summary (windowed metrics from `picks.recent_closed`, n=3500)

| Class | 24h PF | 24h n | 7d PF | 7d WR | 7d n | 30d PF | 30d WR | 30d n |
|-------|--------|-------|-------|-------|------|--------|--------|-------|
| CRYPTO | 3.489 | 82 | 1.483 | 48.8% | 899 | 1.370 | 46.4% | 2714 |
| EQUITY | 1.078 | 12 | 0.759 | 34.0% | 50 | 1.399 | 43.9% | 155 |
| FOREX | 1.392 | 8 | 1.391 | 38.9% | 18 | 2.560 | 48.9% | 94 |
| COMMODITY | 0.000 | 3 | 0.088 | 7.3% | 41 | 0.879 | 40.8% | 76 |
| ETF | — | 0 | 1.322 | 27.3% | 11 | 2.121 | 59.6% | 47 |
| BOND | 0.000 | 1 | 0.000 | 0.0% | 4 | 0.000 | 0.0% | 4 |

### `asset_class_health` (resolver-v2, long-run)

| Class | PF | WR | n | Status |
|-------|----|----|---|--------|
| CRYPTO | 1.280 | 48.3% | 1117 | stable / sizing_allowed |
| FOREX | 2.691 | 54.9% | 153 | stable / sizing_allowed |
| COMMODITY | 1.238 | 51.7% | 58 | candidate |
| EQUITY | 0.569 | 35.1% | 57 | candidate |
| ETF | 11.99 | 50.0% | 2 | insufficient_data |
| BOND | 0.000 | 0.0% | 6 | insufficient_data |

---

## Deltas vs 05Z Baseline (PR #1280)

| Class | 7d PF delta | 30d PF delta | Signal |
|-------|-------------|--------------|--------|
| CRYPTO 7d | 1.476 → 1.483 | **+0.007** | ✅ |
| CRYPTO 30d | 1.365 → 1.370 | **+0.005** | ✅ |
| EQUITY 7d | 0.754 → 0.759 | **+0.005** | 🟡 |
| EQUITY 30d | 1.418 → 1.399 | **−0.019** | 🟡 |
| FOREX 7d | 1.350 → 1.391 | **+0.041** | ✅ 5th consecutive hr ≥1.0 |
| FOREX 30d | 2.545 → 2.560 | **+0.015** | ✅ |
| COMMODITY 7d | 0.088 → 0.088 | **±0.000** | 🔴 bypass persistent |

---

## PR Triage

| PR | Status | Action |
|----|--------|--------|
| #1280 (05Z audit) | CI ✅ all green; 0 REQUEST_CHANGES; `mergeable_state=unknown` | **HOLD** — main force-pushed after branch creation; mergeability unresolved |
| #1279 (AGENTS.md docs, DRAFT) | DRAFT | **No merge** |
| HOLD set (#660 #658 #681 #661) | Not present | ✅ |
| Author-rebase watch (#669 #676 #608 #665 #644 #597 #615 #655) | Not present | ✅ — previously merged |

**Merges this hour: 0**  
**Session total (from task brief + prior audit merges): 12** (#684 #674 #673 #664 #683 #687 #692 #694 #1277 #1278 + 0 this hour)

---

## Strategy Attribution Breakdowns

### COMMODITY 7d (n=41) — bypass confirmed

| Strategy | n | WR | Sum PnL% | Kill threshold? |
|----------|---|----|-----------|----------------|
| `cftc_cot_commercial_signal` | **22** | **4.5%** | **−76.40%** | ✅ YES (n≥20, WR<35%) |
| `futures_momentum` | 17 | 11.8% | −52.81% | ⚠ n<20 (3 from floor) |
| `futures_bb_mean_reversion` | 2 | 0.0% | −10.46% | ❌ n<20 |

`cftc_cot_commercial_signal` n grew from 20 → 22 vs last session (2 more losing trades). WR degraded 5.0% → 4.5%. Root cause (from 19Z deep-dive): `multi_asset_copytrader` bypass — picks emitted under `source_system=multi_asset_copytrader` evade the `BLOCKED_SOURCE_SYSTEMS` check.

### EQUITY 7d (n=50) — stocks_rsi2_pullback recovered

| Strategy | n | WR | Sum PnL% | Note |
|----------|---|----|-----------|------|
| `stocks_rsi2_pullback` | 29 | **44.8%** | **+13.47%** | ✅ Recovered! |
| `inverse_stocks_rsi2_pullback` | 6 | 16.7% | −4.09% | n<20 watch |
| `rs-breakout-scout` | 3 | 0.0% | −5.69% | n<20 |
| `vol-contraction-scout` | 3 | 33.3% | +0.97% | n<20 |
| Various scouts | ≤2 each | mixed | negative | n<20 each |

`stocks_rsi2_pullback` recovered strongly (WR 34.8%→44.8%, sum turned positive +13.47%). EQUITY 7d PF=0.759 is dragged by small-n scouts (most n=1-3) — structural noise at low volume, not kill candidates.

### CRYPTO 7d anchors (n≥20)

| Strategy | n | WR | PF | Sum PnL% | Note |
|----------|---|----|----|-----------|------|
| `st_fear_greed_contrarian` | 261 | **64.0%** | **2.627** | +149.62% | ✅ Tier-1 anchor |
| `luxalgo_confluence` | 145 | 42.1% | 1.047 | +8.47% | marginal |
| `unknown` | 140 | 35.0% | 1.286 | +34.85% | OK |
| `claude_ml_moderate_mut` | 41 | 51.2% | 1.779 | +24.37% | ✅ solid |
| `crypto_mtf_ema_slope_alignment_v1` | 29 | 34.5% | 0.403 | −5.66% | ⚠ see below |

---

## New Findings

### FINDING-39 (ESCALATED to P1): `myfxbook_retail_contrarian` LONG WR deteriorating

| Audit | n (LONG) | WR (LONG) | Delta |
|-------|----------|-----------|-------|
| 23Z 2026-05-20 | 138 | 13.7% | — |
| 06Z 2026-05-21 | **141** | **8.5%** | −5.2pp WR in 7h |

From `mutation_analysis.py` (06Z run):
- LONG: n=141, WR=8.5%, avg=−0.00%
- SHORT: n=8, WR=37.5%
- Spread: **29pp**

All 3 kill criteria met per CLAUDE.md (n≥20 ✅, WR<35% ✅, pattern matches FOREX kills ✅). This is the **7th consecutive Claude confirmation** (1/3 AI voice). WR declining each audit, n growing — not noise. **Awaiting Kimi/Copilot/Cursor for 2nd + 3rd voice.**

### FINDING-22 (6th consecutive, still 1/3 AI): `cftc_cot_commercial_signal` × COMMODITY

n grew 20→22 (2 more losses since 05Z). WR degraded 5.0%→4.5%. All kill criteria met:
- (a) Pattern matches: `cot_positioning` in `BLOCKED_SOURCE_SYSTEMS` ✅
- (b) n=22 ≥ 20 ✅
- (c) WR 4.5% << 35% ✅

Fix requires closing the `multi_asset_copytrader` bypass by adding `("COMMODITY", "cftc_cot_commercial_signal")` to `BLOCKED_ASSET_STRATEGY_PAIRS` in `audit_trail/quality_gates.py`. **Awaiting Kimi/Copilot/Cursor 2nd + 3rd voice.**

### FINDING-43 (NEW, WATCH ONLY): `crypto_mtf_ema_slope_alignment_v1` 7d dip

| Window | n | WR | PF |
|--------|---|----|----|
| 7d | 29 | 34.5% | **0.403** |
| 30d | 89 | 47.2% | 1.070 |

7d meets PF<0.5+n≥20 threshold but 30d long-run is healthy (PF=1.070, WR=47.2%). Per CLAUDE.md "sustained" qualifier: WR<35% NOT sustained across windows. **Watch only — no action.** Will flag if 30d degrades below PF=0.5.

---

## Prior Findings Status

| # | Finding | Status at 06Z |
|---|---------|---------------|
| FINDING-37 (`ig_contrarian_sentiment` LONG n=0) | `mutation_analysis.py` shows LONG n=200, WR=16.5% — 05Z claim partially resolved, LONGs are active | ⚠ Updated |
| FINDING-38 (`macd-hidden-div-scout` EQUITY 30d) | n=1 in 7d window now — below kill floor | 🟡 Watch |
| FINDING-31 (`futures_momentum` COMMODITY) | n=17 / WR=11.8% — still 3 picks from n=20 floor | 🔴 Active |
| FINDING-35 (`cftc_cot` legacy drag) | `cftc_cot_commercial_signal` ≠ blocked `cftc_cot` source — distinct strategy still active | 🔴 Reclassified |
| FINDING-41 (`stocks_rsi2_pullback` mutation candidate) | 7d WR recovered 34.8%→44.8%, PF positive — **de-escalated** | ✅ Resolved |

---

## Mutation Analysis Summary (from `python tools/mutation_analysis.py`)

### Axis-1 direction failures (persistent, all await 3-AI consensus)

| Strategy | LONG n | LONG WR | SHORT WR | Spread | Status |
|----------|--------|---------|---------|--------|--------|
| `ig_contrarian_sentiment` | 200 | 16.5% | 57.1% (n=7) | 41pp | 7th Claude voice |
| `myfxbook_retail_contrarian` | 141 | 8.5% | 37.5% (n=8) | 29pp | 7th Claude voice ↑ ESCALATED |
| `forex_rsi2_mean_reversion` | 124 | 12.1% | 34.8% (n=23) | 23pp | ongoing |
| `cta_cross_asset_tsmom` | 85 | 29.4% | 51.1% (n=174) | 22pp | borderline |

### Axis-3 symbol-block candidates (persistent)

| System | Symbol | n | WR | Status |
|--------|--------|---|----|--------|
| `cta_replicator` | NG=F | 24 | 0.0% | ≥20 kill criteria met; 3-AI pending |
| `rapid_fire` | UUSDT | 34 | 0.0% | ≥20 kill criteria met; 3-AI pending |
| `cta_replicator` | CL=F | 47 | 19.1% | WR sub-floor; 3-axis mutation needed |

---

## Positive Signals

- CRYPTO improving across ALL three windows for 5th consecutive hour ✅
- `st_fear_greed_contrarian` holding Tier-1 anchor: n=261/7d, WR=64%, PF=2.627 ✅
- FOREX 7d PF=1.391 — **5th consecutive hour ≥1.0** (baseline 0.14 pre-#687/#692) ✅
- `stocks_rsi2_pullback` recovered to WR=44.8% / sum=+13.47% (was dragging EQUITY 7d) ✅
- All confirmed kills absent from 7d window: `forex_carry_momentum` / `goldmine_6x_consensus` / `cftc_cot` / `forex_rsi2_mean_reversion` ✅

---

## Plan v2.1 Guardrails

- HOLD set (#660 #658 #681 #661): not present ✅
- No PRs citing PF 5.81 / ml_score 0.90 / WINNER_FILTER ✅
- Resolver-rescope: none detected ✅ (issue #685 still open for tracking)

---

## Next Action Queue

| Priority | Action | Gate |
|----------|--------|------|
| P1 | `cftc_cot_commercial_signal` × COMMODITY kill: add `("COMMODITY", "cftc_cot_commercial_signal")` to `BLOCKED_ASSET_STRATEGY_PAIRS` | **2nd + 3rd AI vote needed** |
| P1 | `myfxbook_retail_contrarian` LONG-block | **2nd + 3rd AI vote needed** |
| P2 | `ig_contrarian_sentiment` LONG-block | **2nd + 3rd AI vote needed** |
| P2 | `cta_replicator × NG=F` symbol-block | **2nd + 3rd AI vote needed** |
| P3 | `futures_momentum` COMMODITY: watch until n≥20 | Monitor |
| P3 | FINDING-43 `crypto_mtf_ema_slope_alignment_v1` | Watch only |

---

_Generated by Claude Sonnet 4.6 — 2026-05-21T06Z_  
_Full context: issues #685 #686 #693_
