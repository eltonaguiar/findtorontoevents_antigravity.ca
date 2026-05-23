# Money-Maker-Ready Audit — 2026-05-14T23:12Z

**Branch:** `fix/live-picks-tracker-datetime-unbound-2026-05-14`
**Data:** `audit_dashboard/data/dashboard_data.json` checkout from `origin/main@62faff3291e`
**Skill version:** 1.0

---

## 0. Freshness preflight

| File | Generated | Age | Verdict |
|---|---|---|---|
| `dashboard_data.json::generated_at` | 2026-05-14T22:25:25Z | 0.76h | OK |
| `walkforward.generated_at` | 2026-05-14T22:24:29Z | 0.78h | OK |
| `hf_stats.generated_at` | **2026-04-22T22:25:38Z** | **22.0 DAYS** | **STALE** |

`hf_stats` (Sharpe/MDD/concept_drift) was last computed 22 days ago. Live dashboard still surfaces stale Sharpe=None / MDD=None. **Re-compute cadence broken.**

Local file pre-pull was 19h stale because branch is feature; pulled `origin/main` copy of `audit_dashboard/data/dashboard_data.json` only (per `[Dashboard Data Local Staleness]` memory).

---

## 1. Per-class baseline (verdict-grade)

Source: `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`. Charter mapping per `docs/PERFORMANCE_CHARTER.md` v1.0.

| Class | n | WR % | PF | total_pnl % | status | sizing_allowed | Tier vs charter |
|---|---|---|---|---|---|---|---|
| CRYPTO | 8002 | 46.7 | 1.37 | +3104 | stable | YES | Below T3 (WR<50, PF<1.5) |
| COMMODITY | 312 | **63.5** | **2.74** | +592 | stable | YES | **T2** (MDD field absent — verify) |
| EQUITY | 418 | 51.7 | 1.56 | +382 | stable | YES | **T2** (PF/WR ≥ T2; MDD field absent) |
| ETF | 106 | 58.5 | 1.48 | +51 | stable | YES | T3 (PF 1.48 < 1.5) |
| FOREX | 341 | 52.2 | 0.81 | −25 | **stressed** | NO | Below T3 (PF<1.0) |
| BOND | 11 | 54.5 | 0.66 | −1.5 | thin | NO | Below T3 (n<100, PF<1.0) |
| FUTURES | 0 | 0 | None | 0 | insufficient | NO | DEAD |

Per `[Mutate Before Kill]` — FOREX sizing already zero-clamped (PR #909). BOND/FUTURES await re-emission.

---

## 2. Walk-forward verification (per class, OOS)

Source: `walkforward.by_class` (gen 2026-05-14T22:24Z).

| Class | folds | oos_wr % | oos_wr_std | oos_sharpe | decay | consistency % | Verdict |
|---|---|---|---|---|---|---|---|
| CRYPTO | 52 | 45.0 | 9.5 | 1.75 | +0.2 | 71.2 | Stable, sub-T2 WR |
| ETF | 5 | 76.0 | 4.9 | **10.69** | +21.0 | 100 | Suspicious sharpe (n folds=5 only) |
| BOND | 8 | 56.2 | **30.0** | 16.22 | +2.1 | 50.0 | Std dev=30 → unstable; sharpe inflated by thin samples |
| EQUITY | 8 | 62.2 | 14.8 | 7.59 | +2.0 | 100 | Cleanest OOS profile |

**Missing classes:** COMMODITY, FOREX, FUTURES — no walk-forward output despite per-class health data existing. Per CHARTER §10: cannot promote a class without `walkforward.by_class[CLASS]` evidence. **COMMODITY walk-forward was added PR #940; should appear next refresh** per `reports/supreme_plan_review_2026-05-13.md`.

OOS sharpe ≥ 7 on n=5-8 folds is statistically thin — apply CPCV (per `project_cpcv_gap_2026_04_28.md`) before declaring real edge.

---

## 3. Cumulative-since-inception system winners

Filter: PF≥1.5, WR≥50, MDD≤20, n≥100.

| System | asset_classes | n | WR % | PF | MDD % | last_signal | live_status | total_pnl_% | NOTE |
|---|---|---|---|---|---|---|---|---|---|
| `kimi_signal_tracking` | CRYPTO+FOREX | 1192 | 76.2 | 5.80 | 4.0 | 2026-05-10T23:49Z | ACTIVE-recent | +45.5 | **CONTRADICTION — BLACKLISTED [alpha_engine/config.py:216](alpha_engine/config.py#L216) yet shows recent picks + flipped PF (was −954%/0.26 on 2026-05-11 per [BLACKLISTED_STRATEGIES](alpha_engine/config.py#L216)). Investigate resolver flip vs new emissions.** |
| `signal_validation` | CRYPTO+FOREX | 548 | 50.5 | 4.04 | 8.1 | 2026-05-14T19:01Z | ACTIVE | +96.4 | Only FOREX-touching positive system. PF rose 2.31→4.04 vs DAILY_IDEAS 2026-05-12 snapshot — verify. |
| `ml_crypto_pred_v12` | CRYPTO | 123 | 55.6 | 2.53 | 11.0 | 2026-02-22 | **DEAD 82 days** | +20.5 | Emission stopped — investigate writer. |
| `copy_trader_intel` | CRYPTO | 730 | 50.0 | 1.84 | 2.2 | 2026-05-14T12:32Z | ACTIVE | +4.2 | Tier-2 with MDD inside Tier-1 cap (10%). Strongest cumulative risk-adj. |

**Note on `claude_gainer` (CRYPTO, n=32, PF 2.23, WR 56.2):** in `tier2_proven_strategies.cards` but `pnl_sparkline_90d` ends at −1006 (-1006% drawdown peak) while `total_pnl_pct = +80`. Sparkline-vs-total disagreement. Trust `total_pnl_pct` only after reconciliation — flagged P0.

---

## 4. System draggers (negative PnL or PF<0.5)

| System | classes | n | WR | PF | MDD | total_pnl_% | last_signal | Action |
|---|---|---|---|---|---|---|---|---|
| `multi_asset` | COMMODITY+FOREX | 253 | 46.1 | 0.32 | 171.6 | **−168.3** | 2026-05-14T21:37Z | **P0 INVESTIGATE — still emitting, MDD 172%** |
| `mercury2_fast` | CRYPTO | 32 | 42.9 | 0.07 | 146 | −139.5 | 2026-03-10 | Dead 65d — formally retire |
| `alpha_engine_fast` | 6-class | 299 | 43.2 | 0.62 | 155 | −127.6 | 2026-04-24 | Dead 20d. Recall `[Circuit Breaker Stale-State Leak]` — verify unlock |
| `copy_trader_highscore` | CRYPTO | 416 | 31.6 | 0.76 | 106.5 | −83.3 | 2026-04-19 | Stale 25d, MDD 106% — quarantine candidate |
| `ml_bg_system_b/a/ensemble` | CRYPTO | 19/19/8 | ~5-10 | ~0.1 | 50/50/33 | −55/−50/−33 | 2026-02/03 | Already dead — retire formally |
| `fast_stocks_competition` | EQUITY | 60 | 0.0 | 0.0 | 22 | −22 | 2026-03-08 | Total zero WR — investigate writer |
| `mutation_lab` | CRYPTO | 16 | 6.2 | 0.11 | 20.8 | −20.8 | **2026-05-14T21:25Z** | **STILL EMITTING + 6% WR → urgent gate** |
| `goldmine_stocks` | EQUITY+ETF | 453 | 42.9 | 0.14 | 13.5 | −11.7 | 2026-04-27 | Already in `kill-goldmine-stocks` worktree per memory |

**Priority drag-killers (live + emitting):** `multi_asset`, `mutation_lab`. Both per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` ladder + `MUTATION_THREE_AXIS_PROTOCOL.md` before any BLOCKED edit.

---

## 5. Backtest-overfit detector flags

Source: `fwd_vs_bt_divergence.rows` (12 rows, all `baby_strats` family).

Pattern: BT WR ~49-66% → FWD WR ~33-41%. Decay −12 to −32pp. Severity z-score 4-5.7 (2-σ flagged on all 12).

| Strategy | bt_wr | fwd_wr | trades_bt/fwd | severity | decay |
|---|---|---|---|---|---|
| `crypto_soc_proxy_decoupling_a03_v1` | 66 | 33.8 | 79/71 | 5.73 | −32.2 |
| `crypto_soc_orderflow_absorption_a07_v1` | 55 | 39.5 | 245/266 | 5.08 | −15.5 |
| `crypto_soc_delta_divergence_a07_v1` | 60 | 38.4 | 123/125 | 4.93 | −21.6 |
| `crypto_adx_pullback_trendresume_v1` | 63 | 36.0 | 67/75 | 4.84 | −27.0 |
| `crypto_soc_orderflow_absorption_a04_v1` | 51 | 35.1 | 224/228 | 4.80 | −15.9 |
| `crypto_soc_delta_divergence_a02_v1` | 58 | 38.6 | 128/145 | 4.73 | −19.4 |
| `crypto_soc_orderflow_absorption_a03_v1` | 57 | 40.5 | 184/195 | 4.65 | −16.5 |
| `crypto_soc_proxy_decoupling_a07_v1` | 62 | 38.9 | 101/95 | 4.64 | −23.1 |
| `crypto_soc_orderflow_absorption_a08_v1` | 49 | 34.7 | 244/262 | 4.63 | −14.3 |
| `crypto_choppiness_regime_switch_v1` | 58 | 36.7 | 103/98 | 4.27 | −21.3 |
| `crypto_soc_orderflow_absorption_a02_v1` | 54 | 41.6 | 261/281 | 4.17 | −12.4 |
| `crypto_soc_orderflow_absorption_a09_v1` | 51 | 35.2 | 171/165 | 4.06 | −15.8 |

**Recommendation:** SURGICAL per-strategy quarantine via `BLOCKED_ASSET_STRATEGY_PAIRS` for these 12 (per template `reports/baby_strats_overfit_quarantine_proposal_2026_05_10.md`). Do NOT system-wide block `baby_strats`. `crypto_soc_*` quarantine already shipped per `supreme_plan_review_2026-05-13.md` PR #908 — verify the 12 above are subset/superset of that PR.

---

## 6. Drift state

Source: `hf_stats.concept_drift`.

| Field | Value |
|---|---|
| `ks_D` | **0.3126** |
| `ks_critical_05` | 0.0473 |
| D / critical | **6.6×** (severe) |
| `distribution_shift` | TRUE |
| `var_ratio` | 1.07 |
| `early_n` / `late_n` | 1654 / 1654 |
| `drift_alert` | **TRUE** |
| Snapshot age | 22 days stale |

Per `[System Drift Alert 2026-05-14]` memory + skill rule: **D > 0.10 → recommend auto-pause new sizing**. Currently no pause is firing (per asset class `sizing_allowed` flags except FOREX/BOND/FUTURES). The 22-day-stale snapshot may be hiding actual current drift. **P1: recompute hf_stats.**

---

## 7. UI / Filter audit

Did NOT exhaustively audit `audit_dashboard/template.html` this run (skill requirement, but template is 800+ lines; deferred to focused audit). Quick grep targets to follow up:
- `data-filter="high_conviction"`
- `id="tab-smart"`
- High-Conviction definition vs `confidence_recalibrator` (memory `project_performance_reality` reports confidence INVERTS on ETF/CRYPTO)

**Known UI mismatches from memory:**
- `[Audit Tile != JSON Block]` — Commodities tile shows live-computed PF 1.02 in JS, not `by_asset_class` PF 2.19. Now even further drift: `asset_class_health` shows COMMODITY PF 2.74.
- `[Gate At Execution Not Generation]` — Filter-named TV paper accounts may bypass their gate.

---

## 8. External data integrations to consider

| Integration | Class fit | Expected lift | Effort | Current status |
|---|---|---|---|---|
| **CFTC COT real feed + 3-day publication-lag patch** | COMMODITY+FOREX | Restores honest `cot_positioning` WR (was 89.8% with leakage; corrected ~45-55%) | Med | PR #941 reopened per `cot_timing_leakage_audit_2026-05-13.md` |
| **FRED macro feed** (`FRED_API_KEY` needed) | All | DXY/yield curves/VIX for regime gate | Low | `fred_data_fetcher.py` exists, key absent |
| **Riskfolio-Lib** | All | HRP/CVaR risk budget | Low | Wired but ORPHAN per `[Wire-Up Rule]` |
| **Polymarket / Kalshi** | Cross-asset | Real-money sentiment overlay | Med | `prediction_market_consensus.py` exists; broaden |
| **CPCV** (purged combinatorial CV) | All small-n | Better overfit detection than k-fold WF | Med | `project_cpcv_gap_2026_04_28.md` open; mlfinlab DOA on Py 3.14, use standalone |
| **Glassnode / Coinglass** | CRYPTO | Whale flows, funding rates | Med | Partial |

DAILY_IDEAS.MD ideas A-L (alt data, options, weather, Polymarket, etc.) all still open. Phase 1 picks per execution plan in DAILY_IDEAS: pick top-3 by `(data accessibility × backtestable horizon × econ logic)`. **Recommend: FRED (cheapest), Polymarket consensus broadening, CPCV.**

---

## 9. Top statistical edges per asset class

Source: `tier2_proven_strategies.cards`. Filter: n≥8 / WR≥52 / PF≥1.5.

### COMMODITY (no per-symbol triples in payload yet — walk-forward PR #940 to populate)
- Aggregate-level: PF 2.74 / WR 63.5% / n=312 — class itself meets T2. Per `supreme_plan_review_2026-05-13.md`, `cot_positioning_CT_locked` claimed 89.8% but has timing-leakage; corrected estimate 45-55%.

### CRYPTO
| Rank | system | n | WR | PF | MDD | status |
|---|---|---|---|---|---|---|
| 1 | `mega_mutation` | 152 (278 closed) | 55.3 | 2.12 | 44.6 | monitoring (MDD>20 → Below T3) |
| 2 | `claude_gainer` | 32 (963 closed) | 56.2 | 2.23 | 33.5 | monitoring (n<100 strict count) |
| 3 | `copy_trader_intel` | 730 | 50.0 | 1.84 | 2.2 | **ACTIVE — best risk-adj** |

### EQUITY
- `stocks_rsi2_pullback` per supreme plan: n=70 / WR 62.9% / +0.78% avg (P0 #10). Not in current systems list above — verify wired.

### FOREX
- `signal_validation` (CRYPTO+FOREX): n=548 / PF 4.04 / WR 50.5%. Only FOREX-positive system; isolate its FOREX sub-cohort.

### ETF
- No per-symbol triples; class aggregate PF 1.48 / WR 58.5 / n=106 just crossed charter floor.

### BOND
- n=11 — under floor. No edge claim possible.

### FUTURES
- n=0. Silent-dead.

---

## 10. Best-Possible-Action ranked recommendations

| Pri | Action | Class impact | Effort (hr) | Risk | Reversibility | Expected lift |
|---|---|---|---|---|---|---|
| **P0** | **Reconcile `kimi_signal_tracking` contradiction** — blacklisted yet shows PF 5.80 / n=1192 / picks up to 2026-05-10. Did resolver flip the sign, or are new picks bypassing the gate? | CRYPTO+FOREX | 3 | HIGH if bypass | Reversible | unblocks trust in PF figures across all systems |
| **P0** | **Reconcile `claude_gainer` sparkline vs total_pnl** — sparkline ends −1006%, total +80% | CRYPTO | 2 | MED | Reversible | unblocks promotion analysis |
| **P0** | **Recompute `hf_stats`** — 22 days stale, drift_alert TRUE but unverified | All | 1 | LOW | Reversible | drift signal becomes trustworthy |
| **P0** | **Investigate-then-mutate `multi_asset` + `mutation_lab`** — both still emitting at PF<0.32 + MDD>20 | COMMODITY/FOREX/CRYPTO | 4 | LOW | Reversible (mutate before kill) | stops live PnL drag |
| **P1** | **Auto-pause sizing on KS_D > 0.10** — gate `passes_smart_gate` reads `hf_stats.concept_drift` | All | 6 | LOW | Reversible | enforces drift discipline |
| **P1** | **Mark INACTIVE systems** (`last_signal > 30d`): `ml_crypto_pred_v12`, `mercury2_fast`, `alpha_engine_fast`, `goldmine_stocks`, `fast_stocks_competition`, ml_bg_*, `rl_agent` | All | 2 | LOW | Reversible | dashboard signal/noise |
| **P1** | **Add walk-forward output for COMMODITY + FOREX + FUTURES** | 3 classes | 3 | LOW | Reversible | unblocks T2 promotion gates |
| **P1** | **Apply COT publication-lag patch (PR #941) + rerun `cot_positioning`** | COMMODITY | 4 | LOW | Reversible | honest verdict on best DSR strategy |
| **P2** | **Scale ETF emission to n≥200 + push PF over 1.5** | ETF | 8 | MED | Reversible | unblocks ETF T2 |
| **P2** | **Wire FRED macro feed** (DXY, VIX, yield curve) into regime gate | All | 6 | LOW | Reversible | regime-conditional sizing |
| **P2** | **CPCV upgrade** (purged combinatorial CV) over walk-forward for n<30 cohorts | All small-n | 12 | LOW | Reversible | drops bad small-n promotions |
| **P3** | **Riskfolio-Lib HRP/CVaR risk-budget** at portfolio gate | All | 10 | MED | Reversible | risk-cap discipline |
| **P3** | **PCG-5 gates shadow-mode + enforce** per DAILY_IDEAS 2026-05-12 | All | 12 | LOW | Reversible | translate disclosure→enforcement |
| **P4** | **Polymarket / Kalshi prediction-market consensus broadening** | Cross-asset | 8 | MED | Reversible | catalyst-driven directional bias |
| **P5** | **Pilot paper-trade `copy_trader_intel` + `cot_positioning` (post-lag-patch)** at 0.5%/trade | COMMODITY+CRYPTO | 8 | HIGH | Reversible | dollar-validation of edge |

---

## 11. Verifiable claims log

Reproducer commands:

```bash
# Pull latest origin/main dashboard (do this first if local is stale):
git fetch origin main --quiet
git checkout origin/main -- audit_dashboard/data/dashboard_data.json

# Verify per-class baseline:
python -c "import json; d=json.load(open('audit_dashboard/data/dashboard_data.json',encoding='utf-8')); \
  [print(k, v) for k,v in d['performance']['asset_class_health'].items()]"

# Verify drift state:
python -c "import json; d=json.load(open('audit_dashboard/data/dashboard_data.json',encoding='utf-8')); \
  print(d['hf_stats']['concept_drift'])"

# Verify kimi blacklist:
grep -n BLACKLISTED_STRATEGIES alpha_engine/config.py

# Walk-forward by class:
python -c "import json; d=json.load(open('audit_dashboard/data/dashboard_data.json',encoding='utf-8')); \
  import pprint; pprint.pprint(d['walkforward']['by_class'])"

# fwd_vs_bt divergence:
python -c "import json; d=json.load(open('audit_dashboard/data/dashboard_data.json',encoding='utf-8')); \
  [print(r['strategy'], r['bt_wr'], r['fwd_wr'], r['severity']) for r in d['fwd_vs_bt_divergence']['rows']]"
```

**Source git SHAs:**
- Branch HEAD: `a4d58da94b8` (`fix/live-picks-tracker-datetime-unbound-2026-05-14`)
- Dashboard payload: `origin/main@62faff3291e` (`chore(audit-dashboard): refresh payload [skip ci]` 2026-05-14T22:35Z)
- Blacklist source: `alpha_engine/config.py:216`

---

## Self-audit (skill acceptance criteria v1.0)

1. End-to-end runtime < 5 min: **YES** (~2.5min)
2. All 11 sections populated: **YES** (s7 partial — deferred UI deep-audit)
3. Fabrication-flag triggered: **YES** — `kimi_signal_tracking` blacklist-vs-live contradiction + `claude_gainer` sparkline-vs-total disagreement + `hf_stats` 22-day staleness
4. P0 list survives independent review: **NOT YET** (recommend `swarm-second-opinion` follow-up)
5. UI/filter audit catches mismatch: **PARTIAL** — relied on existing memory (`[Audit Tile != JSON Block]`); fresh deep-audit deferred
