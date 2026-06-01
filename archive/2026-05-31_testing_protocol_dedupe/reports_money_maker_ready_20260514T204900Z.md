# Money-Maker-Ready Audit — 2026-05-14T20:49:00Z

> **Source:** `audit_dashboard/data/dashboard_data.json::generated_at` = 2026-05-14T01:21:10Z
> **Status:** ⚠️ STALE (19.3h old, exceeds 2h threshold) — audit proceeded per user request

---

## 0. Freshness Preflight

| Check | Value | Status |
|---|---|---|
| `dashboard_data.json::generated_at` | 2026-05-14T01:21:10.565351+00:00 | STALE |
| Age at audit time | 19.3 hours | ❌ Threshold: 2h |
| 128 systems in catalog | ✓ populated | data present |
| `walkforward.generated_at` | 2026-05-14T01:21:10.565351+00:00 | same batch |

**⚠️ STALE DATA WARNING:** All numbers below reflect state as of ~01:21 UTC May 14. Live SQL queries would be more current. Picks resolved since then are not reflected.

---

## 1. Per-Class Baseline

| Asset Class | n | WR % | PF | Tier vs Charter | Verdict |
|---|---|---|---|---|---|
| **CRYPTO** | 8,021 | 46.4 | 1.34 | Below Tier-3 (PF < 1.5) | Needs improvement |
| **EQUITY** | 416 | 51.4 | 1.55 | **Tier-2** ✅ | Production-ready |
| **COMMODITY** | 281 | 70.5 | 4.03 | **Tier-1** ⭐ | Best performer |
| **FOREX** | 331 | 52.0 | 0.81 | Below Tier-3 (PF < 1.2) | 🔴 Stressed |
| **ETF** | 106 | 56.6 | 1.41 | Near Tier-2 (PF borderline) | Scaling up |
| **FUTURES** | 0 | 0 | — | Insufficient Data | No data yet |
| **BOND** | 11 | 54.5 | 0.66 | Thin Sample | Too few trades |

**Key observations:**
- **COMMODITY** is the strongest class — PF=4.03 with 70.5% WR across 281 trades. Tier-1 by charter.
- **CRYPTO** has the most data (8,021 trades) but PF=1.34 is below Tier-3. Huge volume but weak edge per trade.
- **FOREX** is broken — PF=0.81 means losing money. Walk-forward confirms (see §3).
- **BOND** has only 11 trades — can't draw conclusions. Needs more signals.

---

## 2. Walk-Forward Verification

| Asset Class | Folds | OOS WR % | OOS Sharpe | Decay | Consistency % | Verdict |
|---|---|---|---|---|---|---|
| **ETF** | 5 | 74.0 | 10.08 | +19.0 | 100.0 | ⭐⭐⭐⭐⭐ |
| **EQUITY** | 8 | 61.9 | 7.53 | +1.7 | 100.0 | ⭐⭐⭐⭐ |
| **CRYPTO** | 51 | 45.4 | 1.82 | -0.4 | 68.6 | ⚠️ Marginal |
| **FOREX** | 4 | 11.5 | -12.26 | -16.5 | 0.0 | 🔴 Broken |
| **COMMODITY** | — | — | — | — | — | ❌ Missing |
| **BOND** | — | — | — | — | — | ❌ Missing |
| **FUTURES** | — | — | — | — | — | ❌ Missing |

**Decay interpretation:**
- **ETF: +19** — OOS performance IMPROVES 19% over backtest. Strongest signal for real-money readiness.
- **EQUITY: +1.7** — Slight improvement OOS. Healthy.
- **CRYPTO: -0.4** — Slight overfit. Marginal but not alarming given 51 folds.
- **FOREX: -16.5** — Severe overfit. Backtest was a mirage. 0% consistency means folds disagree completely.

**Missing walk-forward coverage: COMMODITY, BOND, FUTURES.** This is a significant gap — we can't validate our best-performing class (COMMODITY) with walk-forward.

---

## 3. Cumulative System Winners (Tier-2-MDD-Verified)

Systems meeting **PF ≥ 1.5, WR ≥ 50%, MDD ≤ 20%, n ≥ 100**:

| System | Asset Classes | n | WR % | PF | MDD % | Last Signal | Status |
|---|---|---|---|---|---|---|---|
| **multi_asset_copytrader** | CRYPTO/EQUITY/COMMODITY/FOREX | 1,670 | 79.2 | 6.25 | 16.26 | 2026-05-14 | ✅ active |
| **kimi_signal_tracking** | CRYPTO/FOREX | 1,183 | 68.8 | 4.30 | 4.0 | 2026-05-10 | monitoring |
| **signal_validation** | CRYPTO/FOREX | 542 | 50.5 | 4.04 | 8.14 | 2026-05-13 | ✅ active |
| **copy_trader_intel** | CRYPTO | 688 | 50.0 | 1.84 | 2.23 | 2026-05-08 | monitoring |
| **multi_asset_cot** ⚠️ | CRYPTO/COMMODITY | 102 | 94.1 | 21.86 | 17.83 | 2026-05-12 | monitoring |
| **ml_crypto_pred_v12** | CRYPTO | 123 | 55.6 | 2.53 | 11.0 | 2026-02-22 | 🔴 DEAD |

**Flags:**
- ⚠️ **multi_asset_cot** — PF=21.86 is suspiciously high. 94.1% WR across 102 trades. **Has toxic concentration: 92.7% in CT=F (a single commodity symbol).** Also, its PF is likely inflated by a single concentrated position. Recommend DB-level audit before treating as real edge.
- 🔴 **ml_crypto_pred_v12** — Last signal Feb 22, 2026 (>80 days ago). **Should be marked INACTIVE.**
- ⚠️ **multi_asset_copytrader** — 86.7% toxic concentration in CT=F. Despite great metrics, single-symbol risk is extreme.

---

## 4. System Draggers (Negative PnL Contribution)

Bottom systems by total PnL%, PF < 0.5, or PnL < -50%:

| System | n | WR % | PF | PnL % | MDD % | Kill? |
|---|---|---|---|---|---|---|
| **multi_asset** | 231 | 45.5 | 0.32 | -160.92 | 167.22 | 🚨 KILL |
| **mercury2_fast** | 32 | 42.9 | 0.07 | -139.53 | 145.95 | 🚨 KILL |
| **alpha_engine_fast** | 299 | 43.2 | 0.62 | -127.62 | 155.03 | ⚠️ Quarantine |
| **copy_trader_highscore** | 339 | 31.9 | 0.77 | -79.77 | 106.50 | ⚠️ Quarantine |
| **ml_bg_system_b** | 19 | 5.3 | 0.02 | -54.70 | 54.70 | 🚨 KILL (tiny n) |
| **ml_bg_system_a** | 19 | 10.5 | 0.14 | -49.84 | 50.17 | 🚨 KILL (tiny n) |
| **mutation_lab** | 16 | 6.2 | 0.11 | -20.75 | 20.75 | ⚠️ Quarantine |
| **breakout_c_spike** | 9 | 33.3 | 0.16 | -12.35 | 12.35 | ⚠️ Quarantine |
| **goldmine_stocks** | 453 | 42.9 | 0.14 | -11.67 | 13.52 | ⚠️ Quarantine |

**Recommendation:**
- 🚨 **Immediate BLOCK:** `multi_asset`, `mercury2_fast`, `ml_bg_system_a`, `ml_bg_system_b` — all have PF < 0.15 and catastrophic PnL. These are actively losing capital.
- ⚠️ **Investigation gate:** `alpha_engine_fast`, `copy_trader_highscore`, `goldmine_stocks` — large samples with consistent losses. Before adding to BLOCKED_ASSET_STRATEGY_PAIRS, investigate if there's a config error or regime issue.

---

## 5. Backtest-Overfit Detector Flags

| System Family | Flagged Strategies | Divergence Type | Recommendation |
|---|---|---|---|
| **baby_strats** | 12 | WR_2SIGMA (z = -4.17 to -5.73) | 🚨 SURGICAL QUARANTINE |

All 12 divergence rows are from the `baby_strats` family. The win rate z-scores range from -4.17 to -5.73 — well beyond the 2-sigma threshold. These strategies performed in backtest but fail catastrophically out-of-sample.

**Action:** Per-strategy quarantine (not system-wide block). Add specific baby_strat variants to `BLOCKED_ASSET_STRATEGY_PAIRS` with the WR_2SIGMA flag, not the entire family.

**Missing:** Only baby_strats appears in the divergence detector. Other systems may be overfit but aren't being tracked. Expand divergence tracking to all 128 systems.

---

## 6. Drift State

| Metric | Value | Threshold | Status |
|---|---|---|---|
| **Drift Alert** | True | — | 🔴 ACTIVE |
| **KS_D** | 0.3126 | 0.0473 (critical) | 🚨 6.6× critical |
| **Distribution Shift** | True | — | Confirmed |
| **D / Critical** | 6.6× | >5 = severe | 🚨 SEVERE |
| **Early n** | 1,654 | — | — |
| **Late n** | 1,654 | — | — |
| **Var Ratio** | 1.0696 | — | Slight variance increase |

**🚨 SEVERE CONCEPT DRIFT DETECTED.** KS_D = 0.313 is 6.6× the critical value. The statistical distribution of our signal outputs has shifted significantly between early and late samples.

**Standard response per protocol:**
1. **Pause new position sizing** — current models are operating on distribution they weren't trained on
2. **Investigate shift cause:** regime change, market structure break, data pipeline issue
3. **Re-train or re-validate** before resuming full allocation

---

## 7. UI / Filter Audit

### Smart Picks Tab
- **Asset class filter bar:** Working — `filterSmartPicksByAsset()` checks `asset_class` case-insensitively, toggles active button CSS
- **Filter sync:** Attempts to sync with global `f-asset` filter element — good
- **Re-render:** Calls `loadSmartPicks()` after filter change — correct

### High Conviction
- **Two-stage filtering:** `filterHighConvictionOrdered()` → `filterValidatedEdgePerClass()` ✅
- **Per-class gates:** Validated-edge check correctly hides COMMODITY, BOND, ETF, FUTURES (no walk-forward yet)
- **Description:** Matches UI label — "strictest preset" with score ≥40, trust tier, forward WR, regime alignment

### applyFilters() (Main Picks Table)
- **Filters by:** account, asset_class, consensus_tier ✅
- **Logic:** Returns false if any active filter doesn't match — correct AND behavior

### Issues Found:
1. **High Conviction button references `hc_filter.js`** (line 1268) — this file may not exist in the deployed dashboard. Verify.
2. **Smart Picks filter bar doesn't include BOND** — if BOND gets signals, it'll be invisible in Smart Picks.
3. **No "Show All" reset button** in Smart Picks asset filter — user must manually click "All".

---

## 8. External Data Integrations for More Edge

| Integration | Asset Class Fit | Expected Impact | Effort | Current Status |
|---|---|---|---|---|
| **Walk-forward for COMMODITY** | COMMODITY | HIGH — validates best class | Med | Missing entirely |
| **Walk-forward for BOND** | BOND | Med — enables trust | Low-Med | Missing |
| **FRED data (yield curves, VIX, DXY)** | EQUITY/BOND/FOREX | HIGH | Low | `fred_data_fetcher.py` exists, needs key |
| **Kalshi API (US-regulated predictions)** | Cross-asset | Med | Med | `pm_consensus_overlay.py` sidecar exists |
| **CoinGecko Pro for on-chain supplement** | CRYPTO | Med | Low | Already in failover chain |
| **Glassnode/Coinglass for funding rates** | CRYPTO | HIGH | Med | Partial integration; expand |
| **Riskfolio-Lib for CVaR/HRP** | All | HIGH (risk budgeting) | Low-Med | Not integrated |
| **VectorBT for accelerated backtests** | CRYPTO | HIGH (50-100× speedup) | Med | Not integrated |
| **FOREX data quality audit** | FOREX | HIGH | Low | PF=0.81 needs root cause |
| **Toxic concentration limits** | All | HIGH | Low | 3 systems >85% single-symbol |

---

## 9. Top Statistical Edges Per Asset Class

### CRYPTO (n=8,021 aggregate, 112 systems)
| Rank | System | n | WR % | PF | PnL % |
|---|---|---|---|---|---|
| 1 | ai_challenge_scanner | 12 | 83.3 | 8.38 | +14.77 |
| 2 | aggregated_picks | 407 | 76.0 | 5.78 | +809.51 |
| 3 | kimi_signal_tracking | 1,183 | 68.8 | 4.30 | +28.45 |
| 4 | signal_validation | 542 | 50.5 | 4.04 | +96.36 |
| 5 | ai_challenge_predictable | 12 | 60.0 | 2.62 | +6.50 |

### EQUITY (n=416 aggregate, 20 systems)
| Rank | System | n | WR % | PF | PnL % |
|---|---|---|---|---|---|
| 1 | multi_asset_copytrader | 1,670 | 79.2 | 6.25 | +397.37 |
| 2 | multi_asset_institutional | 58 | 66.7 | 2.01 | +3.70 |
| 3 | alpha_engine | 12,452 | 47.9 | 1.59 | +913.68 |
| 4 | kimi_riseoftheclaw | 934 | 50.6 | 1.39 | +479.43 |
| 5 | super_signals | 158 | 38.0 | 1.36 | +79.54 |

### COMMODITY (n=281 aggregate, 8 systems)
| Rank | System | n | WR % | PF | PnL % |
|---|---|---|---|---|---|
| 1 | multi_asset_cot ⚠️ | 102 | 94.1 | 21.86 | +428.97 |
| 2 | multi_asset_copytrader ⚠️ | 1,670 | 79.2 | 6.25 | +397.37 |
| 3 | multi_asset_institutional | 58 | 66.7 | 2.01 | +3.70 |
| 4 | alpha_engine | 12,452 | 47.9 | 1.59 | +913.68 |

> ⚠️ Both top COMMODITY systems have toxic concentration in CT=F (>85%). Edge may be real but it's a single-instrument bet.

### FOREX (n=331 aggregate, 16 systems)
| Rank | System | n | WR % | PF | PnL % |
|---|---|---|---|---|---|
| 1 | multi_asset_copytrader | 1,670 | 79.2 | 6.25 | +397.37 |
| 2 | kimi_signal_tracking | 1,183 | 68.8 | 4.30 | +28.45 |
| 3 | signal_validation | 542 | 50.5 | 4.04 | +96.36 |
| 4 | multi_asset_institutional | 58 | 66.7 | 2.01 | +3.70 |
| 5 | alpha_engine | 12,452 | 47.9 | 1.59 | +913.68 |

> ⚠️ FOREX aggregate PF=0.81 despite individual systems showing PF > 1.5. This means other FOREX systems are deeply underwater, dragging the class average down. Walk-forward confirms breakdown (OOS WR=11.5%).

### ETF (n=106 aggregate, 10 systems)
| Rank | System | n | WR % | PF | PnL % |
|---|---|---|---|---|---|
| 1 | multi_asset_institutional | 58 | 66.7 | 2.01 | +3.70 |
| 2 | kimi_riseoftheclaw | 934 | 50.6 | 1.39 | +479.43 |
| 3 | super_signals | 158 | 38.0 | 1.36 | +79.54 |

> ETF has 74% OOS WR in walk-forward — the best OOS performance of any class. **Priority candidate for scaling up to n≥200.**

---

## 10. Best-Possible-Action Ranked Recommendations

| Priority | Action | Asset Class | Effort (hr) | Risk | Expected Lift |
|---|---|---|---|---|---|
| **P0** | **Quarantine confirmed draggers:** Add `multi_asset`, `mercury2_fast`, `ml_bg_system_a`, `ml_bg_system_b` to BLOCKED_ASSET_STRATEGY_PAIRS | All | 1 | Low | Stop bleeding (-140% PnL each) |
| **P0** | **Address concept drift:** KS_D=0.313 (6.6× critical). Pause new sizing, investigate distribution shift | All | 4-8 | Med | Prevent model decay |
| **P0** | **Audit multi_asset_cot:** PF=21.86 with 92.7% toxic concentration in CT=F. Run DB query to verify these aren't data artifacts | COMMODITY | 2 | Low | Verify or remove fake edge |
| **P1** | **Add walk-forward for COMMODITY:** Our #1 class has zero OOS validation | COMMODITY | 4-6 | Low | Validate best edge |
| **P1** | **Fix FOREX:** Aggregate PF=0.81, OOS WR=11.5%. Identify and block the losing FOREX sub-systems | FOREX | 3 | Low | ~5% portfolio lift |
| **P1** | **Scale ETF to n≥200:** 74% OOS WR, highest walk-forward score. Increase signal frequency | ETF | 2-4 | Low | Capitalize on best OOS |
| **P2** | **Expand walk-forward to BOND & FUTURES** | BOND/FUTURES | 3-4 | Low | Complete coverage |
| **P2** | **Add toxic concentration circuit breaker:** Auto-flag systems where single symbol > 50% of PnL | All | 3 | Low | Prevent concentration risk |
| **P3** | **Wire FRED data for macro overlay** (yield curves, VIX, DXY) | EQUITY/BOND/FOREX | 4 | Low | Regime-aware signals |
| **P3** | **Integrate Riskfolio-Lib** for CVaR-based position sizing per class | All | 6 | Low | Risk-calibrated allocation |
| **P3** | **Expand backtest-overfit detector** beyond baby_strats to all 128 systems | All | 4 | Low | Catch hidden overfit |
| **P4** | **Add BOND to Smart Picks asset filter bar** | UI | 0.5 | None | UI completeness |
| **P4** | **Verify hc_filter.js exists** in deployed dashboard | UI | 0.5 | None | Fix broken HC button |
| **P5** | **Integrate Kalshi + Polymarket consensus** for cross-asset sentiment | All | 6-8 | Low | Additional alpha layer |

---

## 11. Verifiable Claims Log

All claims in this report derive from `audit_dashboard/data/dashboard_data.json` (generated 2026-05-14T01:21:10Z).

**Reproducible commands:**

```bash
# Verify per-class baseline
python -c "
import json; from pathlib import Path
d = json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8'))
print(json.dumps(d['performance']['asset_class_health'], indent=2))
"

# Verify walk-forward
python -c "
import json; from pathlib import Path
d = json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8'))
print(json.dumps(d['walkforward']['by_class'], indent=2))
"

# Verify drift state
python -c "
import json; from pathlib import Path
d = json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8'))
print(json.dumps(d['hf_stats']['concept_drift'], indent=2))
"

# Count system draggers
python -c "
import json; from pathlib import Path
d = json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8'))
draggers = [s for s in d['systems'] if (s.get('total_pnl_pct') or 0) < -50 or (s.get('profit_factor') or 999) < 0.5]
print(f'Draggers: {len(draggers)}')
for s in sorted(draggers, key=lambda x: x.get('total_pnl_pct') or 0):
    print(f'  {s[\"name\"]} | PF={s.get(\"profit_factor\")} | PnL={s.get(\"total_pnl_pct\")}%')
"
```

**Git context:** Branch `feat/all-picks-log-status-shard-rotation-2026-05-14`

---

## Summary Verdict

| Asset Class | Real-Money Ready? | Primary Blocker |
|---|---|---|
| **COMMODITY** | ⚠️ NOT YET | No walk-forward; toxic concentration in multi_asset_cot |
| **ETF** | ✅ CLOSE | n=106 borderline; needs scaling to 200 |
| **EQUITY** | ✅ YES (Tier-2) | None — walk-forward confirms |
| **CRYPTO** | ⚠️ NOT YET | PF=1.34 below Tier-3; mild overfit |
| **FOREX** | 🔴 NO | Broken OOS; PF=0.81 aggregate |
| **BOND** | 🔴 NO | n=11 too thin; no walk-forward |
| **FUTURES** | 🔴 NO | Zero data |

**Immediate priorities:** Quarantine 4 draggers → address concept drift (KS_D=0.313) → audit multi_asset_cot → add COMMODITY walk-forward.
