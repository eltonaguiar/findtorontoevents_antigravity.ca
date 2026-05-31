# Money-Maker-Ready Audit — 2026-05-15T21:19:49Z

Skill v1.1 | Primary source: `audit_dashboard/data/dashboard_data.json`
n-citation discipline enforced: all `n` values are `resolved_n` = `wins+losses`
after `_is_valid_resolved_pick` filter — NOT raw `closed`.

---

## 0. Freshness Preflight

```
dashboard_data.json generated_at: 2026-05-15T20:20:48.554482+00:00
age: 0.88h — FRESH (< 2h threshold)
walkforward.generated_at: 2026-05-15T20:20:06.057698+00:00 — FRESH
```

**PROCEED.**

---

## 1. Per-Class Baseline (verdict-grade)

Source: `dashboard_data.json::performance.asset_class_health`

| Class | n (resolved) | WR % | PF | sizing_allowed | Tier vs Charter | Notes |
|---|---|---|---|---|---|---|
| **COMMODITY** | 339 | 60.5% | 2.360 | ✅ | **T1 candidate** | CT=F 73% concentration, cot_positioning 42% share — verify post-PR-#994 |
| **EQUITY** | 425 | 51.5% | 1.550 | ✅ | **T2** ✓ | VIX-regime gate branch ready — +PF lift unverified |
| **ETF** | 108 | 57.4% | 1.330 | ✅ | **T3** (PF<1.5) | OOS WR=76%, Sharpe=10.7, decay=+21 — strongest WF of all classes |
| **CRYPTO** | 8122 | 46.1% | 1.300 | ✅ | **Below T3** (WR<47%) | n_eff≈200-400 after autocorr — WR statistically ≈ coin flip |
| **FOREX** | 305 | 55.4% | 0.870 | ✅ ⚠️ | **BELOW FLOOR** | **PF<1.0 with sizing_allowed=True — DANGER** |
| BOND | 11 | 54.5% | 0.660 | ❌ (thin) | below floor | n=11 → BOND_ELITE_FLOOR=33 now live, n accrual pending |
| FUTURES | 0 | 0% | 0.000 | ❌ | insufficient | 4 strategies coded but =F routing to COMMODITY kills tile |

**FABRICATION CHECK — FOREX:** WR=55.4% with PF=0.870 is arithmetically consistent
with a mix of high-WR low-RR LONG picks being losers by PnL (common in carry strategies
where wins are small and losses are large). Both numbers are from `asset_class_health`
and are post-filter — this is NOT data error, it is a broken strategy set.

**CRITICAL:** FOREX has `sizing_allowed=True` despite PF=0.870 < 1.0.
This means the system will size real money into a net-losing class.
The circuit breaker is NOT protecting this because `realized_n_30d=0`
(30d WR tracking not populated — cold_start). **Immediate risk.**

---

## 2. Walk-Forward Verification (OOS)

Source: `dashboard_data.json::walkforward.by_class` (generated 2026-05-15T20:20:06Z)

| Class | Folds | OOS WR% | OOS Sharpe | Consistency | Decay | Status |
|---|---|---|---|---|---|---|
| **ETF** | 5 | 76.0% | 10.685 | **100%** | **+21.0** | ✅ EXCEPTIONAL — OOS outperforms IS |
| **EQUITY** | 8 | 62.2% | 7.586 | **100%** | **+2.0** | ✅ STRONG — every fold profitable |
| BOND | 8 | 56.2% | 16.224 | 50% | +2.1 | ⚠️ UNSTABLE — 4/8 folds losing, n=11 too thin |
| CRYPTO | 52 | 45.7% | 1.866 | 73.1% | **-0.1** | ⚠️ BORDERLINE — below 50% WR OOS, tiny decay |
| COMMODITY | — | — | — | — | — | ❌ MISSING from walkforward |
| FOREX | — | — | — | — | — | ❌ MISSING from walkforward |
| FUTURES | — | — | — | — | — | ❌ MISSING from walkforward |

**Key finding:** ETF is the standout class on WF evidence (decay=+21.0 means every fold
improves OOS vs IS). EQUITY is T2 with 100% fold consistency. CRYPTO is below coin-flip
OOS. COMMODITY and FOREX have no walkforward — cannot be called T1/T2 without it.

---

## 3. System Winners (Tier-2-MDD-Verified)

Source: `dashboard_data.json::systems` | Filter: PF≥1.5, WR≥50%, n≥100, MDD≤20%

| System | n | WR% | PF | MDD% | Classes | Status |
|---|---|---|---|---|---|---|
| `signal_validation` | 562 | 61.0% | 4.70 | 8.1% | CRYPTO, FOREX | ✅ Active |
| `ml_crypto_pred_v12` | 123 | 55.6% | 2.53 | 11.0% | CRYPTO | ✅ Active |
| `copy_trader_intel` | 738 | 50.0% | 1.84 | 2.2% | CRYPTO | ✅ Active |

**⚠️ DATA INTEGRITY FLAG:** `kimi_signal_tracking` appears in winners list
(n=1198, WR=76.2%, PF=5.80, MDD=4.0%) but is in `BLOCKED_ASSET_STRATEGY_PAIRS`
at `audit_trail/quality_gates.py:1980-1982`. The `systems` table is not filtering
out blocked strategies — historical WR/PF includes pre-block picks. This is a
known behavioral issue (blocked picks contribute to historical aggregates until
`_is_historical_blocked_pick` is applied to each row). **Do not size up
`kimi_signal_tracking` — it is BLOCKED.**

Only 3 genuine winners clear all 4 Tier-2 MDD filters. Very thin bench.

---

## 4. System Draggers (Negative PnL)

Source: `dashboard_data.json::systems` | Filter: PF<0.5 OR PnL<-50%

| System | n | WR% | PF | PnL% | Classes | Gate Status |
|---|---|---|---|---|---|---|
| `multi_asset` | 258 | 45.9% | 0.34 | -164% | COMMODITY, FOREX | Partially blocked (AA-7 deferred) |
| `mercury2_fast` | 32 | 42.9% | 0.07 | -140% | CRYPTO | ✅ BLOCKED |
| `alpha_engine_fast` | 299 | 43.2% | 0.62 | -128% | All 7 classes | ✅ BLOCKED |
| `rapid_fire` | 609 | 37.4% | 0.83 | -80% | CRYPTO, FOREX | ❌ Not blocked |
| `super_signals` | 159 | 36.0% | 0.81 | -68% | CRYPTO, EQUITY, FOREX | ❌ Not blocked |
| `goldmine_stocks` | 453 | 42.9% | 0.14 | -12% | EQUITY, ETF | ❌ Not blocked (ETF variant) |

**Unblocked draggers requiring investigation:**
- `rapid_fire` (n=609, PF=0.83, -80% PnL): High volume, sub-1 PF across CRYPTO+FOREX
- `super_signals` (n=159, PF=0.81, -68%): 3-class drag
- `goldmine_stocks` EQUITY/ETF variant: 453 closed, PF=0.14 (nearly zero), existing
  `goldmine_*_consensus` EQUITY blocks don't cover the `goldmine_stocks` system name

Per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — run 3-axis autopsy before blocking.

---

## 5. Backtest-Overfit Detector Flags

Source: `dashboard_data.json::fwd_vs_bt_divergence.rows` (12 flags)

All 12 flags are in `baby_strats` family. Sorted by severity:

| Strategy | BT WR% | FWD WR% | Decay | Severity | Blocked? |
|---|---|---|---|---|---|
| crypto_soc_proxy_decoupling_a03_v1 | 66.0 | 33.8 | -32.2 | **5.73** | ✅ Yes |
| crypto_soc_orderflow_absorption_a07_v1 | 55.0 | 39.0 | -16.0 | 5.27 | ✅ Yes |
| crypto_soc_delta_divergence_a07_v1 | 60.0 | 38.4 | -21.6 | 4.93 | ✅ Yes |
| crypto_soc_orderflow_absorption_a04_v1 | 51.0 | 34.9 | -16.1 | 4.87 | ❌ **NOT BLOCKED** |
| crypto_soc_orderflow_absorption_a03_v1 | 57.0 | 39.9 | -17.1 | 4.86 | ❌ **NOT BLOCKED** |
| crypto_adx_pullback_trendresume_v1 | 63.0 | 36.0 | -27.0 | 4.84 | ❌ **NOT BLOCKED** |
| crypto_soc_delta_divergence_a02_v1 | 58.0 | 38.6 | -19.4 | 4.73 | ❌ **NOT BLOCKED** |
| crypto_soc_orderflow_absorption_a08_v1 | 49.0 | 34.5 | -14.5 | 4.71 | ❌ **NOT BLOCKED** |
| crypto_soc_proxy_decoupling_a07_v1 | 62.0 | 38.9 | -23.1 | 4.64 | ❌ **NOT BLOCKED** |
| crypto_soc_orderflow_absorption_a02_v1 | 54.0 | 41.1 | -12.9 | 4.37 | ❌ **NOT BLOCKED** |
| crypto_choppiness_regime_switch_v1 | 58.0 | 36.4 | -21.6 | 4.35 | ❌ **NOT BLOCKED** |
| crypto_soc_orderflow_absorption_a09_v1 | 51.0 | 34.9 | -16.1 | 4.15 | ❌ **NOT BLOCKED** |

**9 of 12 flagged strategies still emitting live picks.** These are the remaining
baby_strats:crypto_soc_* variants not yet quarantined. All show the same pattern:
BT WR 49-66%, FWD WR 33-41%, meaning the strategy finds an in-sample edge that
vanishes live. Block all 9 via BLOCKED_ASSET_STRATEGY_PAIRS before next capital sizing.

---

## 6. Drift State

Source: `dashboard_data.json::hf_stats.concept_drift`

```
drift_alert:         True
ks_D:                0.0498
ks_critical_05:      0.0460
D / critical:        1.08  (8% above threshold — marginal)
distribution_shift:  True
var_ratio:           1.43  (late-period variance 43% higher than early)
early_n / late_n:    1746 / 1746
```

**Assessment:** Drift is REAL but MARGINAL (D/critical=1.08). The var_ratio=1.43
indicates late picks are more volatile — consistent with FOREX degradation
(high-WR but low-RR strategy mixes). The drift threshold is breached but barely.

**Recommendation:** Do NOT auto-pause ALL classes — EQUITY and ETF have 100%
WF consistency. Apply selective pause: block new FOREX sizing immediately
(it is already PF<1.0), review CRYPTO volume scaling. EQUITY/ETF/COMMODITY
can continue under tighter monitoring.

---

## 7. UI/Filter Audit

Source: `audit_dashboard/template.html` (live — do not edit index.html)

**Smart Picks** (`btn-smart-picks`, `tab-smartpicks`):
- Correctly described as "top-ranked picks by ML pipeline scoring 5 dimensions"
- Filter calls `applySmartPicks()` — pulls from `smart_picks_feed` data
- Warning in tooltip: "Closed-pick analysis shows confluence/score fields are missing
  from most historical records, so Smart Picks filter cannot be verified as edge on
  closed data." — **this caveat is correct and should stay**

**High Conviction** (`btn-conviction-picks-hero`):
- Applies `hc_filter.js` gates: score≥40 compound, trust, forward WR≥55% (≥70% for
  CRYPTO/EQUITY/FOREX), regime, consensus
- Tooltip says "Recommended (all asset classes)" — **MISMATCH:** FOREX hc_filter gate
  uses 70% forward WR threshold, but FOREX class WR is only 55.4% in live data. This
  means FOREX picks would need strategy-level FWD WR ≥ 70% to pass — effectively
  filtering out most FOREX. This is correct behavior but the UI doesn't explain the
  FOREX filter is much tighter. Consider adding FOREX-specific note to tooltip.

**Asset class concentration warning:** The UI says "COMMODITY edge = cot_positioning
on CT=F (73% of class PnL)" is shown in `asset_class_concentration` — verify
dashboard template surfaces this WARN tier correctly.

---

## 8. External Data Integrations — Ranked by Impact

| Priority | Integration | Class | Expected Impact | Status | Action |
|---|---|---|---|---|---|
| **P0** | **FRED_API_KEY** | BOND, EQUITY, COMMODITY | Unlocks T10Y2Y yield curve, VIX, DXY macro signals | `bond-agent.yml:65` has key param, no secret set | Set `FRED_API_KEY` in GitHub secrets |
| **P1** | **Glassnode/Coinglass** widening | CRYPTO | On-chain whale flows + funding rate precision | Partially integrated | Wire wider endpoint coverage |
| **P2** | **Polymarket/Kalshi consensus** | Cross-asset | Prediction-market signal already wired (`pm_consensus_overlay.py`) | Opt-in sidecar | Add second caller in production path |
| **P3** | **QuantStats** reporting | Reporting | Professional per-class PDF reports | Not integrated | Low effort, high legibility gain |
| **P3** | **Riskfolio-Lib** | All | CVaR/HRP risk budgeting at class level | Not integrated | Fills risk-cap audit gap |
| **P4** | **VectorBT** | CRYPTO | 50-100x faster backtests | Not integrated | Backtest acceleration |

---

## 9. Top Statistical Edges Per Asset Class

Source: `dashboard_data.json::systems` (n≥30, WR≥52%, PF≥1.5)

### COMMODITY (class n=339 | all-time)
| System | n | WR% | PF | Asset Classes |
|---|---|---|---|---|
| `multi_asset_cot` | 126 | 78.6% | 4.34 | COMMODITY |
| `multi_asset_copytrader` (COMMODITY only) | 96 | 93.8% | est >3.0 | COMMODITY (carve-out from AA-6) |
| `multi_asset_institutional` | 58 | 66.7% | 2.01 | COMMODITY, EQUITY |

**⚠️ Concentration risk:** CT=F = 73% of COMMODITY PnL mass. If CT=F rolls or
correlates break, class PF could collapse. cot_positioning = 41.6% of picks.
Need post-PR-#994 re-aggregation to confirm 60.5% WR isn't COT over-emission artifact.

### EQUITY (class n=425 | all-time)
| System | n | WR% | PF | Notes |
|---|---|---|---|---|
| `aggregated_picks` | 424 | 76.6% | 5.60 | High MDD=75.5% — sizing limit required |
| `signal_validation` | 562 | 61.0% | 4.70 | Multi-class, CRYPTO+FOREX dominant |
| `multi_asset_institutional` | 58 | 66.7% | 2.01 | Low n for EQUITY alone |

OOS validation: EQUITY folds=8, consistency=100%, decay=+2.0 — most robust class after ETF.

### ETF (class n=108 | all-time)
OOS exceptional: 76% WR, Sharpe=10.7, decay=+21, consistency=100%.
ETF sector emitter NOW LIVE (3 picks: XLK +26.5%, XLE +11.3%, IWM +5.7% above SMA200).
Faber TAA strategy producing real picks for first time since MultiIndex fix.
`goldmine_stocks` ETF variant: PF=0.14 — needs investigation and block.

### CRYPTO (class n=8122 | all-time)
| System | n | WR% | PF | Notes |
|---|---|---|---|---|
| `signal_validation` | 562 | 61.0% | 4.70 | Survivor bias likely — check raw closed |
| `ml_crypto_pred_v12` | 123 | 55.6% | 2.53 | MDD=11% — cleanest CRYPTO winner |
| `mega_mutation` | 286 | 57.5% | 2.36 | MDD=44.6% — dangerous sizing |
| `claude_gainer` | 963 | 56.2% | 2.23 | MDD=33.5% |
| `copy_trader_intel` | 738 | 50.0% | 1.84 | MDD=2.2% — best risk-adjusted CRYPTO |

**n_eff caution (CRYPTO | 8122 resolved | all-time):** with autocorr ρ≈0.4-0.6,
n_eff≈200-400. Class WR=46.1% OOS → cannot claim edge without tighter source
control. `luxalgo_filters` now capped at 10%, `quan_engine` at 5%.

### FOREX (class n=305 | all-time)
**FOREX PF=0.870 — do NOT recommend individual strategies for sizing.**
- Top strategy: `cta_fx_multifactor` on USDJPY=X (23.4% share, 48.8% PnL mass)
- FOREX LONG blocks added 2026-05-15: `fx_smart_carry_trade_momentum`, `dxy-reversal-scout`, `MeanReversionBB`
- FOREX sizing should be suspended until PF > 1.0 in verified post-filter window

### BOND (class n=11 | all-time)
n=11 — too thin for any edge claim. `BOND_ELITE_FLOOR` lowered to 33 (2026-05-15).
Next 30 days: monitor n accrual. FRED T10Y2Y wired in `bond-agent.yml`.

---

## 10. Best-Possible-Action Ranked Recommendations

| # | Priority | Action | Class Impact | Effort | Risk | Expected Lift |
|---|---|---|---|---|---|---|
| 1 | **P0** | **Disable FOREX sizing** — `sizing_allowed=True` on PF=0.870 class with no 30d CB data | FOREX | 10 min | Low | Stop active capital drain |
| 2 | **P0** | **Block 9 remaining baby_strats overfit strategies** (severity 4.15-4.87, not yet blocked) | CRYPTO | 30 min | Low (quarantine only) | Remove 9 emitters with 34-41% FWD WR |
| 3 | **P0** | **Investigate + block `rapid_fire`** (n=609, PF=0.83, -80% PnL) per STRATEGY_INVESTIGATION_BEFORE_KILL | CRYPTO, FOREX | 2h | Med (mutation first) | Stop -80% drain |
| 4 | **P0** | **Investigate + block `super_signals`** (n=159, PF=0.81, -68%) | CRYPTO, EQUITY, FOREX | 2h | Med | Stop -68% drain |
| 5 | **P0** | **Add class-wide PENNY_STOCK gate** — entirely absent from quality_gates.py; `penny_volume_breakout` emitting live | EQUITY | 1h | Low | Closes zero-gate leak |
| 6 | **P1** | **Set FRED_API_KEY** in GitHub secrets | BOND, MACRO | 5 min | None | Unlocks yield-curve signal |
| 7 | **P1** | **Re-derive COMMODITY PF/WR post-PR-#994** (COT dedup landed 2026-05-14) | COMMODITY | 2h | Info only | Verify T1 claim validity |
| 8 | **P1** | **Add walkforward for COMMODITY + FOREX** | COMMODITY, FOREX | 4h | Low | Unverified classes can't be sized safely |
| 9 | **P1** | **Block `goldmine_stocks`** (n=453, PF=0.14, -12% ETF drag) | EQUITY, ETF | 30 min | Low | Remove systematic -PF drain |
| 10 | **P2** | **Merge EQUITY VIX-regime gate** (branch ready: `feat/equity-vix-regime-gate-sidecar-2026-05-13`) | EQUITY | 2h | Low | Potential PF lift (unverified — backtest first) |
| 11 | **P2** | **Fix FUTURES =F classification** + lower conf_floor | FUTURES | 3h | Med | Enable FUTURES tile accrual |
| 12 | **P2** | **Wire `kill_gate.evaluate_kill()` into `passes_active_gate`** | All | 2h | Low | Completes kill-gate circuit |
| 13 | **P3** | **COMMODITY WF** — run walk-forward on COMMODITY before any T1 sizing claim | COMMODITY | 4h | Low | Validates/refutes PF=2.36 |
| 14 | **P3** | **Standardize `resolved_n` citation** in all reports/tools | All | 1h | None | Stops "n drift" confusion |
| 15 | **P4** | **FOREX directional autopsy → FOREX_HARD_DISABLE** (LONG side blocks now live; assess if SHORT-only mode viable) | FOREX | 4h | Med | Restore FOREX to net-positive via SHORT only |

---

## 11. Verifiable Claims Log

All numbers from `dashboard_data.json` generated 2026-05-15T20:20:48Z (0.88h ago):

```bash
# Reproduce per-class baseline
python -c "
import json; from pathlib import Path
d = json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8'))
for cls, h in sorted(d['performance']['asset_class_health'].items()):
    print(cls, h.get('n'), h.get('win_rate'), h.get('profit_factor'))
"

# Reproduce walkforward
python -c "
import json; from pathlib import Path
d = json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8'))
for cls, r in sorted(d['walkforward']['by_class'].items()):
    print(cls, r.get('oos_wr'), r.get('consistency'), r.get('decay'))
"

# Reproduce drift
python -c "
import json; from pathlib import Path
d = json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8'))
drift = d['hf_stats']['concept_drift']
print('drift_alert:', drift['drift_alert'], 'ks_D:', drift['ks_D'], 'critical:', drift['ks_critical_05'])
"

# Reproduce overfit flags
python -c "
import json; from pathlib import Path
d = json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8'))
for r in sorted(d['fwd_vs_bt_divergence']['rows'], key=lambda x: -x.get('severity',0)):
    print(r.get('strategy'), r.get('bt_wr'), r.get('fwd_wr'), r.get('severity'))
"
```

**Fixes already shipped this session (2026-05-15):**
- `enforce_cap()` wired into `production_scanner.py` ✅
- `luxalgo_filters` CRYPTO cap 10% ✅
- `BOND_ELITE_FLOOR` 40→33 in `bond-agent.yml` ✅
- FOREX directional gate: 3 LONG blocks added ✅
- ETF sector emitter re-run → 3 picks live (XLK/XLE/IWM) ✅
- M-048 API failover: 4-host Binance failover in `antigravity_picks.html`,
  `funds.html`, `btc_scalp_scanner.py` → PR #1081

**Pending (requires user approval or further investigation):**
- PENNY_STOCK class-wide gate
- 9 remaining baby_strats overfit blocks
- `rapid_fire` / `super_signals` investigation
- FOREX sizing suspension
- `FRED_API_KEY` secret

---

*Audit: Claude Code (claude-sonnet-4-6) | 2026-05-15T21:19:49Z*
*n-citation: resolved_n throughout | Sources: dashboard_data.json (live) + quality_gates.py (live)*
