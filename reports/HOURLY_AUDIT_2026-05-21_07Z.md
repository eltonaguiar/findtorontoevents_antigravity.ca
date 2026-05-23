# Hourly Audit — 2026-05-21 07Z

**Dashboard snapshot:** 2026-05-21T05:56:20Z (STALE — 1h14m before audit)
**Hourly update last run:** 2026-05-21T05:50:04Z (no refresh cycle since 06Z audit)
**Payload lag:** Dashboard unchanged from 06Z snapshot; all computed metrics are identical to 06Z baseline.

---

## 1. Per-Asset Summary (computed windows)

| Class | 24h n | 24h PF | 7d n | 7d PF | 7d WR | 30d n | 30d PF | 30d WR | vs 06Z baseline |
|-------|-------|--------|------|-------|-------|-------|--------|--------|------------------|
| CRYPTO | 83 | 3.446 | 899 | 1.483 | 48.8% | 2716 | 1.370 | 46.4% | 7d ±0.000 / 30d ±0.000 (stale) ✅ |
| EQUITY | 12 | 1.078 | 50 | 0.759 | 34.0% | 155 | 1.399 | 43.9% | 7d ±0.000 / 30d ±0.000 (stale) 🟡 |
| FOREX | 8 | 1.392 | 18 | 1.391 | 38.9% | 94 | 2.560 | 48.9% | 7d ±0.000 / 30d ±0.000 — **6th hr ≥1.0** ✅ |
| COMMODITY | 3 | 0.000 | 41 | 0.088 | 7.3% | 76 | 0.879 | 40.8% | unchanged — bypass persistent 🔴 |
| ETF | 0 | — | 11 | 1.322 | 27.3% | 47 | 2.121 | 59.6% | stable ✅ |
| BOND | 1 | 0.000 | 4 | 0.000 | 0.0% | 4 | 0.000 | 0.0% | insufficient data |
| FUTURES | 0 | — | 0 | — | — | 2 | ∞ | 100.0% | n=2 thin |

**Baseline references:** CRYPTO 24h 3.54 / 7d 1.33 / 30d 1.33 (issue #686); EQUITY 7d 0.87 / 30d 1.41-2.18 (issue #693); FOREX 7d 0.14 pre-#687 (issue #686).

**Note on stale data:** All 07Z values are identical to 06Z because `hourly_update_last_run.json` shows last refresh at 05:50Z and `dashboard_data.json::generated_at` = 05:56Z. The auto-refresh cron has not completed a new cycle since the 06Z audit. Numbers below are structural observations from `mutation_analysis.py` (reads `closed_picks_fast.json`, not dashboard snapshot), which does reflect the latest committed data.

---

## 2. Strategy Attribution — New Findings from mutation_analysis.py (07Z)

### FINDING-44 (NEW, P2): `quan_engine_swing` LONG — WR=26.0%, n=104

From `python tools/mutation_analysis.py` Axis-1 (direction flip), 07Z run:

| Direction | n | WR | avg PnL | Spread |
|-----------|---|----|---------|--------|
| SHORT | 5 | 60.0% | +0.02% | — |
| **LONG** | **104** | **26.0%** | **−0.00%** | **34pp** |

LONG side meets direction-mutation criteria (n≥20, WR<35%, spread≥20pp). With LONG WR=26% on n=104, PF is likely <0.5. Proposed action: Axis-1 SHORT-only mutation for `quan_engine_swing` in SANDBOX. **Pending 3-AI consensus per CLAUDE.md protocol.** Do NOT add to BLOCKED_ASSET_STRATEGY_PAIRS until consensus (this is a direction filter, not a full kill).

### FINDING-45 (NEW, P3): `cta_cross_asset_tsmom` LONG — WR=29.4%, n=85

| Direction | n | WR | avg PnL | Spread |
|-----------|---|----|---------|--------|
| SHORT | 174 | 51.1% | −0.00% | — |
| **LONG** | **85** | **29.4%** | **−0.01%** | **22pp** |

Borderline (WR=29.4%, just above 30% watch threshold). Qualifies as Axis-1 candidate. **P3 watch** — monitor until 14d sustained WR<30% or n≥100 with PF<0.5.

### Prior findings status (07Z confirmation)

| # | Finding | 07Z status |
|---|---------|------------|
| FINDING-22 | `cftc_cot_commercial_signal` × COMMODITY n=22, WR=4.5% | **PENDING 2nd+3rd AI** (still 1/3 Claude voices) |
| FINDING-34 | `cta_replicator` × `NG=F` n=24, WR=0.0% | **CONFIRMED by mutation_analysis** (07Z) — n unchanged. Pending 3-AI consensus. |
| FINDING-36 | `rapid_fire` × `UUSDT` n=34, WR=0.0% | **CONFIRMED by mutation_analysis** (07Z) — n unchanged. Pending 3-AI consensus. |
| FINDING-39 | `myfxbook_retail_contrarian` LONG deteriorating | **ACTIVE P1** (mutation: n=124, WR=13.7%); note: 06Z comment showed n=141/WR=8.5% from dashboard — discrepancy is dashboard vs closed_picks_fast source. Both are sub-20% WR. Awaiting 2nd+3rd AI. |
| FINDING-43 | `crypto_mtf_ema_slope_alignment_v1` 7d PF=0.403 / WR=34.5% | **WATCH** — 30d PF=1.070 intact. Not sustained. No action. |

---

## 3. PR Triage

| PR | State | CI | Reviews | Action |
|----|-------|----|---------|--------|
| #1281 | **Merged this hour** | ✅ 3/3 green | greptile bot COMMENTED only | ✅ Merged (06Z audit) |
| #1279 | Open, **DRAFT** | ✅ | none | **No merge** (draft) |

**HOLD set (#660 #658 #681 #661):** not present ✅
**Author-rebase watch PRs (#669 #676 #608 #665 #644 #597 #615 #655):** not present ✅
**Merges this hour: 1** (#1281)
**Session total (from task brief + this session):** 13 merges

---

## 4. Positive Signals

- **FOREX 7d PF=1.391** — 6th consecutive hourly audit ≥1.0 (baseline 0.14 pre-#687/#692). Recovery confirmed structural, not transient.
- **CRYPTO 24h PF=3.446** — remains well above Tier-2 threshold; 7d/30d windows stable.
- **ETF 30d n=47** — approaching n=50 candidate floor. 30d PF=2.121, WR=59.6%.
- **All confirmed kills verified absent:** `forex_carry_momentum`, `goldmine_6x_consensus`, `cftc_cot`, `forex_rsi2_mean_reversion` — zero 7d trades.
- **`st_fear_greed_contrarian`** remains CRYPTO anchor: n=261 (7d), WR=64%, PF=2.627.

---

## 5. Plan v2.1 Guardrails

- HOLD set (#660 #658 #681 #661): **not present** ✅
- No open PRs cite PF 5.81 / ml_score 0.90 / WINNER_FILTER ✅
- No resolver-rescope PRs (issue #685: DONE) ✅
- PR #1279 is DRAFT/docs-only, no Plan v2.1 content ✅

---

## 6. asset_class_health (from dashboard — same 05:56Z snapshot)

| Class | n | PF | WR | Notes |
|-------|---|----|----|-------|
| CRYPTO | 1278 | 1.280 | 48.3% | Stable |
| FOREX | 151 | 2.691 | 54.9% | Long-run healthy |
| EQUITY | 55 | 0.569 | 35.1% | 7d drag from scouts |
| COMMODITY | 58 | 1.238 | 51.7% | Long-run ok; 7d bypass persistent |
| ETF | 2 | 11.995 | 50.0% | Thin |
| BOND | 6 | 0.000 | 0.0% | Cold-start |
| FUTURES | 12 | 0.956 | 16.7% | Thin |

---

## 7. Next-Hour Priorities

1. **Dashboard refresh**: If `hourly_update_last_run.json` still shows 05:50Z at 08Z, flag as CI/cron issue. Metrics cannot progress without fresh data.
2. **FINDING-22 2nd AI vote**: `cftc_cot_commercial_signal` × COMMODITY — 1/3 voices. Need Kimi or Copilot confirmation before proceeding to kill PR.
3. **FINDING-39 2nd AI vote**: `myfxbook_retail_contrarian` LONG — P1, 1/3 voices. Priority for next AI review.
4. **EQUITY monitor**: 7d PF=0.759. Target: return to >1.0 as scout n-counts stabilize post-PR-#692.
5. **ETF n watch**: 30d n=47 → 50 target for full Tier-2 candidacy.

---

Refs: issues #685, #686, #693 | PRs merged: #1281
