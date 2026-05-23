# Money-Maker-Ready Audit — 2026-05-16T00:01:06Z

## 0. Freshness Preflight

| Source | `generated_at` | Age | Status |
|---|---|---|---|
| `dashboard_data.json` | 2026-05-15T23:35:45Z | 0.4h | **FRESH** |
| `walkforward.by_class` | 2026-05-15T23:35:08Z | 0.5h | **FRESH** |
| `hf_stats` | 2026-05-14T23:28:42Z | ~24h | **STALE** — one day behind |

**Verdict: Proceed.** Main payload is fresh. `hf_stats` Sharpe/MDD/Calmar cards are 24h stale — flag in Sections 2 and 6.

---

## 1. Per-Class Baseline (Verdict-Grade)

Source: `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`
n = `resolved_n` (wins + losses after `_is_valid_resolved_pick` filter — NOT raw closed).

| Class | n (resolved) | WR % | PF | Tier vs Charter | Notes |
|---|---|---|---|---|---|
| COMMODITY | 345 | 61.2% | 2.48 | **T1 candidate** (PF✓ WR✓ n✓ MDD=?) | MDD not in health payload; verify separately |
| EQUITY | 426 | 51.4% | 1.55 | **T2 candidate** (PF✓ WR✓ n✓ MDD=?) | Static banner claims WR=52.8%/n=428 — **MISMATCH** |
| ETF | 108 | 57.4% | 1.33 | **T3** (PF<1.5; WR✓ n✓) | Static banner claims n=88 — **MISMATCH: ETF already ≥100** |
| CRYPTO | 8115 | 46.3% | 1.30 | **Below T3** (WR<45% floor, PF<1.2) | quan_engine drag; sub-T2 |
| FOREX | 309 | 55.0% | 0.86 | **Sub-floor** (PF<1.0) | Loss-making; mutation protocol required |
| BOND | 11 | 54.5% | 0.66 | **Blocked** (n<100 charter floor, PF<1.0) | Static banner claimed PF=1.72 — **CRITICAL MISMATCH** |
| FUTURES | 0 | 0% | — | **Dead** | No emitter producing picks |

**Critical discrepancies between static banner HTML and live JSON:**
- BOND: banner says PF 1.72 (T2-pass) → actual **PF 0.66** (loss-making). Most dangerous mismatch.
- COMMODITY: banner n=816 → actual **n=345** (2.4× overstated)
- FOREX: banner n=1249 → actual **n=309** (4× overstated); banner PF=0.28 → actual 0.86
- ETF: banner n=88 → actual **n=108** (already crossed charter floor)
- EQUITY: banner WR=52.8% → actual 51.4%; n=428 → 426

---

## 2. Walk-Forward Verification (OOS, Per Class)

Source: `audit_dashboard/data/dashboard_data.json::walkforward.by_class` (fresh, 2026-05-15T23:35Z)

| Class | Folds | OOS WR % | OOS Sharpe | Decay | Consistency | Worst-Fold WR | Assessment |
|---|---|---|---|---|---|---|---|
| ETF | 5 | 76.0% | 10.685 | +21.0 | 100% | 70% | **Strong** — but bull-regime period, monitor for reversion |
| EQUITY | 9 | 59.2% | 7.014 | **−1.7** | 100% | 25% | Negative decay = mild backtest overfit concern; worst fold 25% is red flag |
| BOND | 8 | 56.2% | 16.224 | +2.1 | 50% | 0% | **UNRELIABLE** — n=11 total; Sharpe artifact (n=2 test folds, std≈0 → Sharpe→∞); suppress label "N_INSUFFICIENT" |
| CRYPTO | 53 | 45.7% | 1.834 | 0.0 | 66% | 31% | Flat decay (stable OOS degradation); consistency 66% = unstable |
| COMMODITY | — | — | — | — | — | — | **MISSING from walk-forward** — cannot verify OOS edge |
| FOREX | — | — | — | — | — | — | **MISSING from walk-forward** |

**Flags:**
- BOND Sharpe 16.224 = arithmetic artifact of 2-pick test folds. Do NOT cite as performance evidence.
- ETF Sharpe 10.685 — valid at pick-level (not annual) but concentrated in bull-regime period. Add caveat.
- EQUITY negative decay (−1.7pp) with worst-fold 25% WR suggests the strategy works in calm markets but breaks in stressed folds.
- COMMODITY and FOREX absent from walk-forward = unverified OOS — cannot assert hedge-fund grade without it.

---

## 3. Cumulative System Winners (Tier-2-MDD-Verified)

Source: `dashboard_data.json::systems` — PF≥1.5, WR≥50%, n≥100

| System | Classes | n | WR % | PF | MDD % | MDD-T2 Pass? | Status |
|---|---|---|---|---|---|---|---|
| kimi_signal_tracking | CRYPTO, FOREX | 1198 | 76.2% | 5.80 | **4.0%** | **YES (T1)** | Active |
| signal_validation | CRYPTO, FOREX | 564 | 60.3% | 4.70 | **8.14%** | **YES (T1)** | Active |
| ml_crypto_pred_v12 | CRYPTO | 123 | 55.6% | 2.53 | **11.0%** | **YES (T1)** | Active |
| aggregated_picks | CRYPTO, EQUITY, FOREX | 426 | 76.7% | 5.64 | 75.55% | **NO** (MDD>>20%) | Active |
| multi_asset_cot | COMMODITY | 129 | 79.1% | 4.57 | 79.97% | **NO** (MDD>>20%) | Active |
| multi_asset_copytrader | COMMODITY, EQUITY, FOREX | 1811 | 65.6% | 3.05 | 85.88% | **NO** (MDD>>20%) | Active |
| mega_mutation | CRYPTO | 289 | 58.3% | 2.40 | 44.59% | **NO** (MDD>20%) | Active |
| claude_gainer | CRYPTO | 965 | 56.2% | 2.23 | 33.48% | **NO** (MDD>20%) | Active |
| copy_trader_intel | CRYPTO | 738 | 50.0% | 1.84 | **2.23%** | **YES (T2)** | Active |

**Tier-1 confirmed (all three: PF≥2, WR≥55%, MDD≤10%):**
- `kimi_signal_tracking` (CRYPTO+FOREX | n=1198 | all-time) — **only system fully hedge-fund grade**
- `signal_validation` (CRYPTO+FOREX | n=564 | all-time)
- `ml_crypto_pred_v12` (CRYPTO | n=123 | all-time)

**Note:** MDD figures for `aggregated_picks`, `multi_asset_cot`, `multi_asset_copytrader` are catastrophic (75-86%). These pass PF/WR thresholds but would trigger margin calls in any real fund. The MDD-bloated systems require per-trade position sizing caps, not system-level promotion.

---

## 4. System Draggers (Negative PnL Contributors)

Source: `dashboard_data.json::systems`, PF<0.5

| System | PF | WR % | n | Action |
|---|---|---|---|---|
| ml_bg_system_b | 0.02 | 5.3% | 19 | Kill-eligible (n<100 floor; investigate first per STRATEGY_INVESTIGATION_BEFORE_KILL.md) |
| ml_bg_system_a | 0.14 | 10.5% | 19 | Kill-eligible |
| breakout_c_spike | 0.16 | 33.3% | 9 | Kill-eligible (n=9 sub-floor) |
| goldmine_stocks | 0.14 | 42.9% | **453** | **P0 — highest-volume dragger. n=453 large enough to confirm. Apply mutation protocol.** |
| mercury2_fast | 0.07 | 42.9% | 32 | Investigate (n<100 but pattern clear) |
| multi_asset | 0.34 | 45.6% | 268 | Mutation protocol — check directional split |
| mutation_lab | 0.36 | 18.2% | 22 | Investigate |

**`goldmine_stocks` (EQUITY | n=453 | PF=0.14) is the single largest confirmed dragger by volume.** With 453 closed picks at 42.9% WR and PF 0.14, it is destroying EQUITY class metrics. Per MUTATION_THREE_AXIS_PROTOCOL: export closed CSV → run `python tools/mutation_analysis.py` → check directional and symbol splits before kill.

---

## 5. Backtest-Overfit Detector Flags

Source: `dashboard_data.json::fwd_vs_bt_divergence.rows` — 12 flagged strategies, all from `baby_strats` system, all CRYPTO.

| Strategy Family | Count | Avg BT WR | Avg OOS WR | Avg WR Decay | Severity | Action |
|---|---|---|---|---|---|---|
| `crypto_soc_orderflow_absorption` (a02-a09) | 7 | 53% | 37% | −16pp | 4.15–5.27σ | **Surgical quarantine** |
| `crypto_soc_proxy_decoupling` (a03, a07) | 2 | 64% | 36% | −27pp | 4.64–5.73σ | **Quarantine** |
| `crypto_soc_delta_divergence` (a02, a07) | 2 | 59% | 38.5% | −20pp | 4.73–4.93σ | **Quarantine** |
| `crypto_adx_pullback_trendresume_v1` | 1 | 63% | 36% | −27pp | 4.84σ | **Quarantine** |
| `crypto_choppiness_regime_switch_v1` | 1 | 58% | 36.4% | −21.6pp | 4.35σ | **Quarantine** |

**All 12 are in the `crypto_soc_*` / `baby_strats` family. Recommendation: Add all 12 to `BLOCKED_ASSET_STRATEGY_PAIRS` as `(CRYPTO, <strategy_name>)` via surgical quarantine.** Do NOT block the entire `baby_strats` system — other baby strats are unaffected.

Template reference: `reports/baby_strats_overfit_quarantine_proposal_2026_05_10.md`

---

## 6. Drift State

Source: `dashboard_data.json::hf_stats.concept_drift`

| Metric | Value | Threshold | Status |
|---|---|---|---|
| KS_D | 0.049828 | 0.046029 (critical@0.05) | **DRIFT ALERT** |
| D/critical ratio | **1.08×** | 1.0 = trigger | Mild (not the 6.6× cited in older reports) |
| var_ratio | 1.43 | — | Moderate variance inflation |
| early_n / late_n | 1746 / 1746 | — | Balanced split |
| drift_alert | **True** | — | Auto-pause recommended |
| hf_stats age | 24h stale | <2h | Drift numbers may be slightly behind |

**Assessment: MILD drift (1.08× critical), not the severe 6.6× cited in the MD analysis agent's output — that figure may be from a prior measurement.** The D/critical ratio is just barely above threshold. Still, `drift_alert=True` triggers the standard response:
- **Do NOT increase position sizing** on new picks until drift resolves
- New picks should be shadow-validated for 7 days before live sizing
- EQUITY VIX regime gate (already coded, `quality_gates.py:5653-5672`) — enable in shadow mode

---

## 7. UI / Filter Audit

From the dashboard stats fact-check agent's findings:

| Finding | Severity | Location |
|---|---|---|
| Static MAJOR GOAL banner has wrong PF/WR/n for ALL 6 classes | **HIGH** | `audit_dashboard/template.html` ~L808-820 static fallback text |
| BOND: static says PF 1.72 (T2-pass); live JSON says PF 0.66 | **CRITICAL** | Misleads users about BOND readiness |
| COMMODITY: static n=816; live n=345 — 2.4× overstated | HIGH | Risk of oversizing decisions |
| FOREX: static n=1249, PF=0.28; live n=309, PF=0.86 — 4× n overstatement | HIGH | n overstatement hides thin sample |
| ETF: static n=88 "borderline n→100"; live n=108 — already crossed charter floor | MEDIUM | Wrong guidance to operators |
| TRUTH LAYER 55,510 raw count from 2026-05-12 — current JSON shows 29,249 | MEDIUM | Historical disclosure no longer reconcilable |
| "Ghost Rows: 0 / 0 cohorts" — this section does NOT exist in template.html | N/A | Claim in audit request cannot be verified |
| CRYPTO walkforward: displayed 52 folds; actual 53 | LOW | Dynamic render shows correct value |
| EQUITY walkforward: displayed 8 folds/62.2%/7.586; actual 9/59.2%/7.014 | LOW | Dynamic render shows correct value |
| BOND Sharpe 16.224 displayed without "N_INSUFFICIENT" warning | HIGH | Statistically meaningless at n=11 |

**Priority fix:** The static fallback text in `audit_dashboard/template.html` must be updated to match `asset_class_health` live values OR the JS `updateMajorGoalBanner()` must run before first paint (no-JS fallback is always wrong).

---

## 8. External Data Integrations to Consider

| Source | Asset Class Fit | Expected Impact | Effort | Gap |
|---|---|---|---|---|
| **FRED API** (St Louis Fed) | BOND, EQUITY, COMMODITY macro | Yield curves, VIX, DXY | Very Low | `fred_data_fetcher.py` exists; just needs `FRED_API_KEY` secret |
| **VectorBT** | CRYPTO, ETF | 50-100× faster backtests → faster iteration | Low-Med | Slow baby_strats iteration |
| **Riskfolio-Lib** | All (esp. MDD-bloated systems) | CVaR/HRP risk budgeting → fix 85% MDD systems | Low | MDD audit gap |
| **QuantStats** | Reporting | Pro perf reports for /audit | Very Low | Audit polish |
| **KeltnerRSISqueeze** (symbol-allowlisted) | CRYPTO (BTC/LTC/ARB only) | PF 8-54 on those symbols | Low | Symbol-specific adoption |
| **Glassnode / Coinglass** | CRYPTO on-chain | Whale flows, funding rates | Med | Partial integration |
| **Polymarket / Kalshi** | Cross-asset sentiment | Prediction-market consensus | Med | `pm_consensus_overlay.py` exists |
| **fx_session_continuity** (MIT harvest) | FOREX | Session-timing filter vs LONG bias | Med | Not yet coded; flagged in MIT harvest report |

---

## 9. Top Statistical Edges Per Asset Class

Source: `dashboard_data.json::systems`, filtered for n≥100, WR≥52%, PF≥1.5, MDD≤20%

### COMMODITY (n=345 | all-time)
| Strategy/System | n | WR % | PF | MDD % |
|---|---|---|---|---|
| `multi_asset_cot` | 129 | 79.1% | 4.57 | 79.97%* |
| COT + CFTC commercial signals | ~102 | 61%+ | 2.48 | ? |
*MDD disqualifies for real-money sizing despite strong WR/PF. Use position caps.

### CRYPTO (n=8115 | all-time) — Tier-1 sub-systems
| System | n | WR % | PF | MDD % |
|---|---|---|---|---|
| `kimi_signal_tracking` | 1198 | 76.2% | 5.80 | **4.0%** |
| `signal_validation` | 564 | 60.3% | 4.70 | **8.14%** |
| `ml_crypto_pred_v12` | 123 | 55.6% | 2.53 | **11.0%** |
| `copy_trader_intel` | 738 | 50.0% | 1.84 | **2.23%** |
| Elite bucket (INJUSDT/FETUSDT/DYDXUSDT) | 25-31 each | 96-100% | very high | ? |

### EQUITY (n=426 | all-time)
| System | n | WR % | PF | Notes |
|---|---|---|---|---|
| `stocks_rsi2_pullback` | ~70 | 62.9% | high | Sub-charter floor (n<100); growing |
| `rs-breakout-scout` | ~32 | 81.3% | high | Sub-floor |
| VIX<22 subset | ~134 | 57.5% | 3.06 | 30d window; Tier-1 in constrained regime |

### ETF (n=108 | all-time)
| Symbol / Strategy | Walk-forward | Notes |
|---|---|---|
| XLV — VolumePriceConfirmationReversal | OOS WR 60%, PF 1.83 | Unwired baby strategy, ready to wire |
| ETF basket OOS | 76.0% WR, Sharpe 10.685 | Bull-regime period caveat |

### FOREX (n=309 | all-time) — SHORT-axis survivors only
| Strategy | Direction | WR % | Notes |
|---|---|---|---|
| `ig_contrarian_sentiment` | SHORT | 57.1% | LONG=15.7% → directional block needed |
| `cta_cross_asset_tsmom` | Mixed | 53% | Best FOREX strategy by WR |

### BOND (n=11 | all-time) — charter blocked
Current bond_scanner generating signals (TLT/IEF/TLH/LQD) — not yet closing trades.

---

## 10. Best-Possible-Action Ranked Recommendations

| Priority | Action | Class Impact | Effort (hr) | Risk | Expected Lift |
|---|---|---|---|---|---|
| **P0** | Update static MAJOR GOAL banner in `template.html` with live asset_class_health values (or ensure JS runs before first paint) | ALL — credibility | 1 | Low | Fix BOND PF 1.72→0.66 critical mismatch |
| **P0** | Apply mutation analysis to `goldmine_stocks` (EQUITY, n=453, PF=0.14) — directional/symbol split → kill or carve out | EQUITY | 2 | Med | EQUITY PF lift from ~1.55 toward T2-solid |
| **P0** | Quarantine 12 `crypto_soc_*/baby_strats` strategies in `BLOCKED_ASSET_STRATEGY_PAIRS` (all 4-6σ WR decay) | CRYPTO | 1 | Low | CRYPTO WR lift ~+2-3pp |
| **P0** | Re-derive COMMODITY PF/WR on post-PR-#994 dedup picks before any Tier-1 claim | COMMODITY | 1 | Low | Prevents premature T1 promotion on possibly inflated n |
| **P1** | Set `FRED_API_KEY` in GitHub secrets — unblocks BOND scanner macro data + accelerates n growth | BOND | 0.5 | Very Low | BOND n: 11 → 50+ (30-day horizon) |
| **P1** | Add "N_INSUFFICIENT" label to BOND Sharpe 16.224 on walk-forward card in `template.html` | UI | 0.5 | Very Low | Prevents misreading artifact Sharpe as real edge |
| **P1** | Wire `kill_gate.evaluate_kill()` into `passes_active_gate()` (already modified in uncommitted `quality_gates.py`) | ALL | 0.5 | Low | Closes biggest active-gate coverage gap |
| **P1** | Block LONG direction for `ig_contrarian_sentiment` and `myfxbook_retail_contrarian` in FOREX (temp-unblock expires 2026-05-22) | FOREX | 1 | Low | FOREX PF lift; prevent reversion to 0.28 |
| **P2** | Enable VIX regime gate in shadow mode (`VIX_REGIME_GATE_ENABLED=shadow`) — EQUITY PF 4.55 with VIX<22 | EQUITY | 1 | Low | EQUITY T1 access in calm VIX regime |
| **P2** | Wire `VolumePriceConfirmationReversal` on XLV/XLK into ETF emitter | ETF | 2 | Low | ETF n growth: 108 → 130+ |
| **P2** | Run Phase 2-D commodity re-audit (CL=F, KC=F, SI=F, GC=F, ZC=F — same bad-data artifact as cotton CT=F) | COMMODITY | 3 | Med | Potentially recover 3-6 high-PF strategies |
| **P3** | Add MDD guard to system-promotion logic — prevent T2-badge on MDD>20% systems like `multi_asset_cot` | ALL | 1 | Low | Accurate tier badges |
| **P3** | Suppress ETF walk-forward Sharpe 10.685 with "bull-regime period" caveat | ETF | 0.5 | Very Low | Accurate OOS interpretation |
| **P4** | Wire `anti_overfit_validator` (currently no-ops because production picks have no `returns_history` key) | ALL | 3 | Med | DSR/PBO gate actually fires |
| **P5** | Build UEPS KPI panel in `template.html` — UEPS bypass enabled 2026-05-14, picks accumulating | ALL | 4 | Low | Visibility into UEPS-sourced picks |

---

## 11. Verifiable Claims Log

```bash
# Verify asset_class_health n counts (reproducible):
python tools/_verify_n_reproducible.py  # SHA256 must match reports/asset_class_verification_2026-05-15.md

# Verify static banner mismatches:
grep -n "EQUITY.*PF\|BOND.*PF\|COMMODITY.*PF" audit_dashboard/template.html | head -20

# Verify goldmine_stocks dragger:
python -c "
import json; from pathlib import Path
d = json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8'))
s = next(x for x in d['systems'] if x['name']=='goldmine_stocks')
print(s['profit_factor'], s['win_rate'], s['closed_picks'])
"
# Expected: 0.14, 42.9, 453

# Verify concept drift:
python -c "
import json; from pathlib import Path
d = json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8'))
cd = d['hf_stats']['concept_drift']
print(cd['ks_D'], cd['ks_critical_05'], cd['drift_alert'])
"
# Expected: 0.0498, 0.0460, True — ratio 1.08×

# Verify 12 baby_strats overfit rows:
python -c "
import json; from pathlib import Path
d = json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8'))
rows = d['fwd_vs_bt_divergence']['rows']
print(len(rows), set(r['system'] for r in rows))
"
# Expected: 12, {'baby_strats'}

# Verify kimi_signal_tracking Tier-1:
python -c "
import json; from pathlib import Path
d = json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8'))
s = next(x for x in d['systems'] if x['name']=='kimi_signal_tracking')
print(s['profit_factor'], s['win_rate'], s['max_drawdown'], s['closed_picks'])
"
# Expected: 5.8, 76.2, 4.0, 1198
```

---

*Generated by money-maker-ready skill v1.1 — 2026-05-16T00:01:06Z*
*Data source: `audit_dashboard/data/dashboard_data.json` generated 2026-05-15T23:35:45Z (0.4h old at audit time)*
