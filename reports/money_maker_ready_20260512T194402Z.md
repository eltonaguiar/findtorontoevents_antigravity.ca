# Money-Maker-Ready Audit — 2026-05-12T19:44:02Z

**Generated:** 2026-05-12T19:44:02Z (skill v1.0)
**Branch:** `main` @ `9cec9f1a958`
**Caveat:** every number tagged `(asset_class | n | timeframe)`.

---

## 0. Freshness preflight — FAIL (stale 13.7h)

| Field | Value |
|---|---|
| `dashboard_data.json::generated_at` | 2026-05-12T06:01:50Z |
| Age | **13.7h** (>2h threshold) |
| Status | **STALE — all numbers below tagged `(stale-13.7h)`** |

Per skill protocol: should abort. Proceeding per explicit user "make progress" direction; verdict-grade numbers are 13.7h-old snapshot.

---

## 1. Per-class baseline (verdict-grade) — STILL BROKEN (n=0 bug persists)

Source: `dashboard_data.json::performance.asset_class_health` (stale-13.7h)

All classes report `n=0  WR=0  PF=0` despite non-zero `walkforward` populations downstream. **Same `asset_class_health.n=0` bug from the 2026-05-11 audit plan has not been fixed.**

| Class | n | WR | PF | MDD | Tier |
|---|---|---|---|---|---|
| FOREX | 0 | 0.0 | 0.00 | ? | PHANTOM |
| CRYPTO | 0 | 0.0 | 0.00 | ? | PHANTOM |
| COMMODITY | 0 | 0.0 | 0.00 | ? | PHANTOM |
| EQUITY | 0 | 0.0 | 0.00 | ? | PHANTOM |
| ETF | 0 | 0.0 | 0.00 | ? | PHANTOM |
| FUTURES | 0 | 0.0 | 0.00 | ? | PHANTOM |
| BOND | 0 | 0.0 | 0.00 | ? | PHANTOM |
| UNKNOWN | 0 | 0.0 | 0.00 | ? | PHANTOM |

**No tier verdict possible.** Every downstream verdict tagged UNVERIFIED until `_compute_asset_class_health()` is fixed in `audit_trail/dashboard_generator.py`.

---

## 2. Walk-forward verification — partial coverage

Source: `dashboard_data.json::walkforward.by_class` (generated_at 2026-05-12T06:01:03Z, stale-13.7h)

| Class | folds | oos_wr | oos_sharpe | decay | consistency | Verdict |
|---|---|---|---|---|---|---|
| ETF | 4 | 76.20 | 11.372 | +28.80 | 100.00 | T1+ OOS (n_folds=4 too low) |
| CRYPTO | 32 | 45.70 | 1.780 | +0.30 | 68.80 | T2 (consistency below 80% floor) |
| EQUITY | 9 | 63.30 | 6.635 | +2.50 | 88.90 | T1+ OOS |
| FOREX | 36 | 45.20 | **-1.162** | -1.20 | 41.70 | **CONFIRMED SUB-FLOOR** |

**MISSING:** COMMODITY, BOND, FUTURES, SPORTS, UNKNOWN. Cannot certify those classes.

Edge surfaced: ETF OOS is the strongest signal in the entire payload (sharpe 11.4 on 4 folds), but n_folds=4 is too few to trust. COMMODITY and BOND walk-forward must populate before LIVE_ELIGIBLE for those classes.

---

## 3. Cumulative system winners (Tier-2-MDD verified) — 4 PASS GATE

Source: `dashboard_data.json::systems` (stale-13.7h). Filter: PF≥1.5, WR≥50, MDD≤20, n≥100.

| Rank | System | PF | WR % | n | MDD % | last_signal | Status |
|---|---|---|---|---|---|---|---|
| 1 | multi_asset_cot | **19.93** | 87.4 | 135 | 17.8 | 2026-05-11 | **IMPLAUSIBLE PF — verify or quarantine** |
| 2 | signal_validation | 4.32 | 52.7 | 523 | 8.1 | 2026-05-11 | validator-as-pick-source — meta-eval risk |
| 3 | ml_crypto_pred_v12 | 2.53 | 55.6 | 123 | 11.0 | **2026-02-22 (80d)** | **DEAD — last_signal >30d** |
| 4 | copy_trader_intel | 1.84 | 50.0 | 690 | 2.23 | 2026-05-12 | MDD 2.23% with n=690 looks synthetic |

**multi_asset_cot PF=19.93** is up from 19.19 in the prior audit (n grew 130→135) — extraordinary number; must verify against `ejaguiar1_stocks` DB before relying.

**ml_crypto_pred_v12 DEAD** per skill rule (last signal 80 days ago > 30d threshold).

---

## 4. System draggers (kill candidates) — 19 critical losses

Source: `dashboard_data.json::systems` filter `total_pnl_pct < -50 OR profit_factor < 0.5`

| System | PnL % | PF | WR % | n |
|---|---|---|---|---|
| kimi_signal_tracking | **-930.4** | 0.28 | 36.4 | 669 |
| multi_asset | -163.6 | 0.30 | 40.8 | 211 |
| mercury2_fast | -139.5 | 0.07 | 42.9 | 32 |
| alpha_engine_fast | -127.6 | 0.62 | 40.3 | 362 |
| copy_trader_highscore | -79.8 | 0.77 | 31.9 | 419 |
| ml_bg_system_b | -54.7 | 0.02 | 5.3 | 19 |
| ml_bg_system_a | -49.8 | 0.14 | 10.5 | 19 |
| crypto_winners | -49.2 | 0.39 | 30.6 | 49 |
| ml_bg_ensemble | -33.0 | 0.00 | 0.0 | 8 |
| fast_stocks_competition | -22.0 | 0.00 | 0.0 | 60 |

**kimi_signal_tracking deepened -954% → -930%** but is already in `quarantine_manifest.json::blocked_strategies_class_wide` per commit 4a2d337a5dc. Verify the BLOCKED list is enforced at execution (memory: `feedback_gate_at_execution_not_generation`).

---

## 5. Backtest-overfit detector — baby_strats 12 flags (unchanged)

Source: `dashboard_data.json::fwd_vs_bt_divergence.rows`

| System | Flagged |
|---|---|
| baby_strats | **12** |

Identical to 2026-05-10 finding. Quarantine proposal `reports/baby_strats_overfit_quarantine_proposal_2026_05_10.md` ready to execute (per-strategy surgical adds to `BLOCKED_ASSET_STRATEGY_PAIRS`).

---

## 6. Drift state — SEVERE ALERT but stale

Source: `dashboard_data.json::hf_stats.concept_drift`

| Field | Value |
|---|---|
| `ks_D` | **0.312576** |
| `ks_critical_05` | 0.047292 |
| `D / critical` ratio | **6.61×** (severe) |
| `distribution_shift` | TRUE |
| `drift_alert` | TRUE |
| `hf_stats.generated_at` | 2026-04-22T22:25:38Z (**20 days stale**) |

KS_D 6.6× critical = severe distribution shift. Per skill: "If D > 0.10 → recommend auto-pause sizing". This is 3× that threshold.

**BUT hf_stats is 20 days stale.** Drift snapshot itself is no longer fresh — either the regime moved further OR the drift detector cron has been broken since 2026-04-22.

---

## 7. UI/filter audit — DEFERRED

Skipped this iteration to avoid duplicating the 2026-05-11 plan §7 findings (HC filter at `template.html:1203, 4707, 4730, 9496, 9810` confidence-inversion risk on ETF/CRYPTO per memory `project_performance_reality`). No new evidence to add until P0 items below close.

---

## 8. External data integrations — top-3 unchanged priority

1. **Riskfolio-Lib** (CVaR/HRP risk budgeting) — Low effort, Phase-8 risk-cap gap
2. **FRED macro filter** (`fred_data_fetcher.py` exists; needs `FRED_API_KEY` secret) — Low effort, regime-aware sizing
3. **QuantStats** (Pro perf reports) — Very Low effort, replaces DIY HTML

Plus this session shipped:
- `tools/correlation_regime_sidecar.py` (Action #5 / commit `459d38064a4`) — cross-class corr matrix with sleeve_sizing_scalar
- `tools/cot_step7_friction_adjusted_mc.py` (Action #3 / commit `d60a7b2656d`) — DSR gate at n_trials=500
- `tools/research/commodity_carry_momo.py` factor registry (Action #4 / commit `9cec9f1a958`)

---

## 9. Top statistical edges per asset class — UNVERIFIABLE

Same as 2026-05-11 plan §9. `cross_strategy_permutations` filter (n≥8, WR≥52, PF≥1.5) yields zero qualifying rows because `asset_class_health.n=0` bug propagates upstream. Cannot certify any per-class edge today.

Only confirmable edge from `systems` payload: **copy_trader_intel** (PF 1.84, WR 50.0, n=690, MDD 2.2%, active 2026-05-12) — but per `feedback_clone_hl_placeholder_stats` memory, copy-trader sources had placeholder-stat smell in 2026-04. Reverify against DB before sizing.

---

## 10. Best-Possible-Action ranked recommendations

| Priority | Action | Class impact | Effort | Risk | Reversibility | Expected lift |
|---|---|---|---|---|---|---|
| **P0** | Fix `asset_class_health.n=0` aggregator (`audit_trail/dashboard_generator.py`) — unchanged from 2026-05-11 plan, still blocking every downstream verdict | ALL | 2-4h | Low | Full | Unlocks every per-class tier judgment |
| **P0** | Mark `ml_crypto_pred_v12` INACTIVE in systems payload (last_signal 80d > 30d threshold) | CRYPTO | 0.5h | Low | Full | Stops the dashboard from advertising a dead model |
| **P0** | Verify `multi_asset_cot` PF=19.93 via direct DB query against `ejaguiar1_stocks` | mixed | 1h | Low | N/A | Data-integrity check — possibly remove from winners |
| **P0** | Refresh `hf_stats` cron (20d stale) AND wire drift→auto-pause logic when `KS_D > 0.10` (currently 0.31 = 6.6× critical) | ALL | 3-4h | Med | Full | Avoids sizing through a regime shift |
| **P1** | Execute baby_strats 12-flag overfit quarantine per existing proposal `reports/baby_strats_overfit_quarantine_proposal_2026_05_10.md` | mixed | 1h | Low | Full | Removes overfit drag |
| **P1** | Investigate-then-quarantine top draggers per `MUTATION_THREE_AXIS_PROTOCOL.md`: `multi_asset`, `mercury2_fast`, `ml_bg_system_a/b`, `crypto_winners`, `fast_stocks_competition`. `kimi_signal_tracking` already blocklisted — verify enforcement at exec gate. | mixed | 4-6h | Med | Reversible | Stops bleed |
| **P1** | Bootstrap gatekeeper_old + gatekeeper_new bundles. Workflow `ml-gatekeeper-ab-bootstrap.yml` redispatched (`25758017776`). Without both bundles, score_active_picks_ab() falls back to single-model and Phase D/E A/B infra is inert. | ALL | 0.5h | Low | Full | Activates A/B leakage-purge test |
| **P2** | Add walk-forward coverage for COMMODITY/BOND/FUTURES (currently missing from `walkforward.by_class`) | those classes | 3-4h | Med | Full | Per-class certification |
| **P2** | Audit `signal_validation` PF=4.32 — validator-as-pick-source = meta-evaluation risk (its picks ARE the validation set) | mixed | 2h | Low | Full | Confirms or unwinds a fake-edge |
| **P2** | HC filter audit against confidence-inversion on ETF/CRYPTO (memory `project_performance_reality`) | ETF/CRYPTO | 2-3h | Low | Full | Stops surfacing anti-edge |
| **P3** | Riskfolio-Lib opt-in sidecar with explicit Wiring Plan | ALL | 6-8h | Low | Full | Risk-cap layer |
| **P3** | Re-run cross-permutations after §1 P0 fix lands; verdict on per-class edge existence | ALL | 1h | Low | N/A | Final go/no-go for real money |
| **P4** | FRED macro-filter wire-up (need `FRED_API_KEY` to GH Secrets) | EQUITY/BOND/COMMODITY | 4-6h | Med | Full | Regime-aware sizing |
| **P5** | Kalshi pairwise consensus with Polymarket via `pm_consensus_overlay.py` | cross-asset | 6-10h | Med | Full | Real-money predictive overlay |

---

## 11. Verifiable claims log

Reproducer commands (read-only):

```bash
# §0 freshness
python -c "import json,datetime as dt; d=json.load(open('audit_dashboard/data/dashboard_data.json',encoding='utf-8')); print(d['generated_at'])"

# §1 per-class baseline (all n=0 = bug)
python -c "import json,pprint; d=json.load(open('audit_dashboard/data/dashboard_data.json',encoding='utf-8')); pprint.pprint(d['performance']['asset_class_health'])"

# §2 walk-forward (4 classes only)
python -c "import json,pprint; d=json.load(open('audit_dashboard/data/dashboard_data.json',encoding='utf-8')); pprint.pprint({k: {kk:vv for kk,vv in v.items() if kk in ('folds','oos_wr','oos_sharpe','decay','consistency')} for k,v in d['walkforward']['by_class'].items()})"

# §3 winners (4 pass T2-MDD)
python -c "import json; d=json.load(open('audit_dashboard/data/dashboard_data.json',encoding='utf-8')); num=lambda s,k,dft=0: (float(s.get(k)) if s.get(k) is not None else dft); [print(s['name'],num(s,'profit_factor'),num(s,'win_rate'),num(s,'closed_picks'),num(s,'max_drawdown'),s.get('last_signal_at')) for s in d['systems'] if num(s,'profit_factor')>=1.5 and num(s,'win_rate')>=50 and num(s,'closed_picks')>=100 and num(s,'max_drawdown',999)<=20]"

# §6 drift (KS_D 6.6x critical, stale 20d)
python -c "import json; d=json.load(open('audit_dashboard/data/dashboard_data.json',encoding='utf-8')); print(d['hf_stats']['concept_drift']); print('gen:', d['hf_stats']['generated_at'])"

# block state
grep -n BLOCKED_ASSET_STRATEGY_PAIRS audit_trail/quality_gates.py
grep -n BLACKLISTED_STRATEGIES alpha_engine/config.py
```

Branch SHA at audit time: `git log --format=%H -1 main` → `9cec9f1a958`.

---

## Delta vs 2026-05-11 plan

| Finding | 2026-05-11 | 2026-05-12 | Change |
|---|---|---|---|
| `asset_class_health.n=0` bug | YES | YES | **STILL BROKEN** |
| `walkforward.by_class` empty folds | YES (all 0) | NO (4 classes have folds; 3 missing) | partial fix |
| `multi_asset_cot` PF | 19.19 (n=130) | 19.93 (n=135) | grew — still implausible |
| `claude_gainer_st` in winners | YES (PF 6.12) | NO (dropped) | removed; check blocklist enforcement |
| `signal_validation` PF | 2.22 | 4.32 | grew (n=502→523) — meta-eval risk worse |
| `ml_crypto_pred_v12` last_signal | "NONE" | 2026-02-22 (80d) | confirmed DEAD |
| `aggregated_picks` in winners | YES (PF 6.42) | NO | dropped |
| `kimi_signal_tracking` PnL% | -954.9 | -930.4 | minor improvement (still bleeding) |
| baby_strats divergence flags | 12 | 12 | unchanged — quarantine still pending |
| Drift KS_D | 0.0 (uncomputed) | **0.31 (6.6× critical)** | **detector now working — SEVERE alert** |
| hf_stats freshness | 19d stale | 20d stale | hf_stats cron still broken |

**NEW THIS RUN:** drift detector now produces a real KS_D and emits a SEVERE alert (0.31 = 6.6× critical). hf_stats cron still hasn't refreshed since 2026-04-22.

---

## Verdict

**NOT READY for real money.** Three P0 data-layer blockers persist (asset_class_health bug, hf_stats stale, drift unhedged), plus implausible-PF winners (multi_asset_cot, signal_validation) need DB verification. Drift alert at 6.6× critical is the most immediate sizing concern — every existing strategy must be re-evaluated against the post-2026-04-22 regime.

## NFA

Research surface only. No code edits in this audit run.
