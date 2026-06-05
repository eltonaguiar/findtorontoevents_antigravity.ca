# COMMODITY + BOND Edge Hunt v2 — 2026-06-06

**Goal #1 audit.** Time-boxed v2 pass on `commodity_term_cot`, `feature_signals`, COT data, `bond_scanner`, `bond_tlt_ief_v3`, `bond_duration_momentum`, and `at_raw_picks` 14d panels.

**Verdict: neither class is real-money ready.** COMMODITY = `INSUFFICIENT_DATA` (policy-clean n=7). BOND = frozen `backfill_no_data` in verdict JSON despite 45+ live closes in `at_raw_picks`. Do not size up.

All numbers below are **re-derived 2026-06-06** from `pf_registry.json`, `money_ready_verdict.json`, `pick_summary_stats_14d.json`, `commodity_term_cot_signals.json`, `bond_tlt_ief_v3_24m.json`, and live `ejaguiar1_stocks.at_raw_picks` queries. No fabricated stats.

---

## Executive summary

| Class | Policy-clean n | at_raw clean decisive (excl 2026-06-04) | 14d at_raw closed | Fastest path to n=30 clean forward |
|-------|---------------:|----------------------------------------:|------------------:|-------------------------------------|
| **COMMODITY** | 7 (WR 42.9%, PF 1.74) | 0 rows (`asset_class='COMMODITY'` empty in DB) | — (lives under `FUTURES`) | Wire `commodity_term_cot` always-on + paper pilot; ~8 daily scans × 3 picks |
| **BOND** | 0 in `policy_clean_net`; registry raw n=8 | **50** decisive | **45** (WR 46.7%, PF 1.12) | Unfreeze verdict pipeline + promote `bond_yield_curve_slope`; wire orphan `bond_tlt_ief_v3` |

---

## COMMODITY

### 1. Canonical verdict layer (`pf_registry` / `money_ready_verdict`)

| Slice | n | WR | PF | Notes |
|-------|--:|---:|---:|-------|
| `by_asset_class_policy_clean_net` | 7 | 42.9% | 1.74 | `INSUFFICIENT_DATA`; n&lt;30 gate |
| `by_asset_class_raw` (undeduped) | 84 | 7.1% | 0.41 | Dominated by `multi_asset_copytrader`; do not cite |
| `money_ready_verdict` COMMODITY | 7 | 42.9% | 1.74 | `data_source: closed_picks`, `policy_frozen: true` |

Per-strategy policy-clean (all `INSUFF_N`):

| Strategy | n | WR | PF |
|----------|--:|---:|---:|
| `commodity_tsmom_12m` | 2 | 0% | 0.00 |
| `cta_golden_cross` | 1 | 100% | — |
| `feature_signals` | 1 | 0% | 0.00 (NG=F loss) |
| `multi_asset_copytrader` | 1 | 100% | — |
| `regime_terminal` | 1 | 100% | — |

`commodity_term_cot`: **0 closed forward** (sidecar only).

### 2. Backfill contamination (mandatory filter)

- `at_raw_picks`: `asset_class='COMMODITY'` has **0 rows** — commodity emissions land in **`FUTURES`**.
- FUTURES decisive on `2026-06-04` only: **18 rows** (not the full class; most FUTURES history is pre-backfill).
- **Always filter** `DATE(closed_at) != '2026-06-04'` before tier review. Prior deep-dive cited 5,960 closes that day across resolver backfill; today's DB shows 18 decisive FUTURES on that date — still treat as contaminated batch.

Post-filter FUTURES COT-adjacent sleeves (decisive, excl 2026-06-04):

| Strategy | n | WR |
|----------|--:|---:|
| `cta_commodity_momentum_term` | 631 | 35.7% |
| `cot_positioning` | 518 | 43.6% |
| `cftc_cot_commercial_signal` | 273 | 9.2% |

None are tier-grade; `cot_positioning` is the least bad but still sub-50% WR with heavy over-emission risk (prior 7.33× dedup finding on Ring/COT sleeve).

### 3. `commodity_term_cot` + `feature_signals` state

**`tools/feature_signals/commodity_term_cot.py`**
- Erb-Harvey roll yield + Sanders COT, 50/50 composite, 8-symbol universe.
- Latest `commodity_term_cot_signals.json` (2026-06-05T07:20Z): 8/8 term+COT legs, **3 picks** (HG=F, ZW=F, ZC=F), `production_enable: false`.

**`tools/feature_signals/orchestrator.py`**
- `commodity_momentum` (CL/NG 20d): **always on** when `FEATURE_SIGNALS_ENABLED=1` (default ON).
- `commodity_term_cot`: gated behind **`FACTOR_EMITTERS_ENABLED=0` (default OFF)**.
- `merge_feature_signals()` is wired in `production_scanner.py` but does **not** check `production_enable` on picks.

**`feature_signals_latest.json` sleeves:** `commodity_momentum: 1`, `vix_regime_overlay: 1`, `commodity_term_cot: 0` (not emitted without env flag).

### 4. COMMODITY — fastest path to n=30 clean forward

**Gap:** policy-clean n=7 → need **+23** clean resolved.

**Ranked plan (ETA ~8–12 trading days paper-only):**

| # | Action | Why | ETA |
|---|--------|-----|-----|
| 1 | **Promote `commodity_term_cot` to always-on orchestrator sleeve** (same tier as `commodity_momentum`; keep `production_enable` audit flag but emit through scanner) | 3 picks/scan from live COT+term; module already complete | 1 PR |
| 2 | **Paper-pilot ledger** with one-trade-per-CFTC-release dedup + `closed_at != 2026-06-04` filter | Prevents CT=F / COT over-emission repeat | same PR |
| 3 | Set `FEATURE_SIGNALS_REFRESH=1` on `etf-bond-scanner.yml` / production scan cron | Ensures picks reach `at_raw_picks` with `asset_class=COMMODITY` tag (today they would land as FUTURES) | 1 workflow edit |
| 4 | Fix asset-class tagging: `commodity_term_cot` picks → `COMMODITY` not `FUTURES` | Required for policy-clean cohort to see them | 1 line in `_stamp()` / emitter |
| 5 | Hold `commodity_tsmom_12m` banned; do not ramp `cot_positioning` without dedup | Backtest REJECTED; COT sleeve WR 43.6% on 518 | — |

**Math:** 3 picks × 8 daily scans ≈ 24 new + 7 existing ≈ **31** (assuming ~21d horizon resolution). Bottleneck is **wire-up + asset_class tagging**, not signal generation.

---

## BOND

### 1. Verdict vs live DB disconnect (critical)

| Layer | n | WR | PF | Source |
|-------|--:|---:|---:|--------|
| `money_ready_verdict` BOND | **0** | — | — | `data_source: backfill_no_data`, `policy_frozen: true` |
| `pf_registry` `policy_clean_net` | **absent** | — | — | BOND not in array |
| `pf_registry` raw / deduped | 8 / 6 | 25–33% | 2.74–3.16 | `bond_scanner` only; single-source artifact |
| **`at_raw_picks` 14d** | **45** closed | **46.7%** | **1.12** | `pick_summary_stats_14d.json` |
| **`at_raw_picks` clean decisive** (excl 2026-06-04) | **50** | ~48% | — | live DB query 2026-06-06 |

**Reading:** BOND **already exceeds n=30** in raw forward DB, but the **verdict pipeline does not ingest it** (`money_ready_verdict.py` backfills empty BOND when `closed_picks` path has zero rows). Fastest n-ramp is a **pipeline fix**, not more emission.

### 2. `at_raw_picks` 14d breakdown (2026-06-05 panel)

From `pick_summary_stats_14d.json` + live DB:

| Source | Strategy | n (14d) | Wins |
|--------|----------|--------:|-----:|
| AlphaEngine | `bond_yield_momentum` | 25 | 3 |
| AlphaEngine | `bond_yield_curve_slope` | 9 | **9** |
| alpha_engine_unified | `cta_cross_asset_tsmom` | 8 | 8 |
| AlphaEngine | `cta_golden_cross_200` | 2 | 0 |

All-time clean `bond_yield_curve_slope`: **n=11, 11 wins** (excl 2026-06-04).

Top symbol IEF (44% share). Top source AlphaEngine (80%).

### 3. `bond_scanner` + orphan backtests

**`alpha_engine/bond_scanner.py`** — wired, 7 strategies registered (`bond_yield_momentum`, `bond_duration_rotation`, `bond_mean_reversion`, `bond_yield_curve_slope`, etc.). Writes `active_picks_bond.json`.

**Provenance gap:** `at_raw_picks` shows `source_system='AlphaEngine'`, not `bond_scanner`. Registry `bond_scanner` rows (n=6–8) come from file-based picks, not the live 14d stream.

**`bond_tlt_ief_v3_24m.json`** (orphan backtest, 2026-05-13):

| Metric | Value |
|--------|------:|
| Universe | TLT / IEF / SHY |
| n_periods | 254 |
| WR | 54.3% |
| PF | **1.29** |
| MDD | 23.0% |

**0 production callers** — `grep bond_tlt_ief alpha_engine/` returns empty. Wire-Up violation. Reproducer: `python3 tools/backtest_bond_tlt_ief_momentum.py`.

**`bond_hyg_lqd_momentum_winner`:** lives in `eight_class_flagship_strategies.py` / `priority_picks_emitter` only; backtest cousin `bond_hyg_lqd_v1` PF 1.62 — also orphan from `bond_scanner`.

### 4. `bond_duration_momentum.py`

- Registered in orchestrator sleeve `bond_duration_momentum`.
- **`FACTOR_EMITTERS_ENABLED=0` default** + `production_enable: false`.
- `bond_duration_momentum_signals.json` **does not exist** (never run in prod).
- Intentionally avoids `bond_yield_momentum` name (BLOCKED_SOURCE_SYSTEMS collision).

### 5. BOND — fastest path to n=30 clean forward

**Raw forward already at n=50** (excl backfill). Target is **n=30 policy-clean / verdict-visible**.

| # | Action | Why | ETA |
|---|--------|-----|-----|
| 1 | **Unfreeze BOND in `money_ready_verdict.py`** — ingest `at_raw_picks` BOND rows (or sync `pf_registry` `policy_clean_net`) | Removes `backfill_no_data` phantom n=0 | 1 PR |
| 2 | **Tag `bond_scanner` emissions with `source_system='bond_scanner'`** in merge path | Aligns registry with DB; fixes single-source artifact | same PR |
| 3 | **Demote `bond_yield_momentum`** (25n/3W in 14d = 12% WR) **; promote `bond_yield_curve_slope`** (9/9 in 14d, 11/11 all-time clean) | Best live sleeve already exists | config/weight PR |
| 4 | **Wire `bond_tlt_ief_v3` rotation** into `bond_scanner.STRATEGIES` | Only validated offline edge (PF 1.29); monthly cadence adds ~1 pick/mo | 1 PR |
| 5 | Enable `bond_duration_momentum` via `FACTOR_EMITTERS_ENABLED=1` on bond workflow **after** #1–3 review | 8-ETF universe, ~2 picks/scan at 75th pctile | workflow flag |
| 6 | Expand `BOND_SYMBOLS` whitelist (LQD, SHY, AGG already in scanner; policy blocks some) | Increases diversification off IEF 44% | `non_crypto_policy.py` |

**Do not cite** registry PF 2.74–3.16 on n=6–8 as edge. **Do not cite** 14d PF 1.12 as tier-ready until policy-clean cohort confirms and `bond_yield_momentum` drag is gated.

---

## Wire-up gaps (action list)

| Gap | Module | Caller today | Required caller | Priority |
|-----|--------|--------------|-----------------|----------|
| G1 | `commodity_term_cot` | Sidecar JSON only | `orchestrator.emit_all()` always-on + `production_scanner.merge_feature_signals` | P0 |
| G2 | `bond_duration_momentum` | None (env gated) | `orchestrator` + `FACTOR_EMITTERS_ENABLED=1` on bond cron | P1 |
| G3 | `bond_tlt_ief_v3` backtest logic | `tools/backtest_bond_tlt_ief_momentum.py` only | `bond_scanner.STRATEGIES` new rotation fn | P0 |
| G4 | BOND verdict ingestion | `backfill_no_data` stub | `money_ready_verdict` reads at_raw / pf_registry clean | P0 |
| G5 | `bond_scanner` provenance | Emits as `AlphaEngine` in DB | Set `source_system='bond_scanner'` on merge | P1 |
| G6 | COMMODITY asset_class | 0 `COMMODITY` rows in `at_raw_picks` | Tag feature-signal commodity picks `COMMODITY` | P0 |
| G7 | `production_enable` flag | Ignored by `merge_feature_signals` | Filter or document operator override | P2 |
| G8 | `bond_hyg_lqd_momentum_winner` | `priority_picks_emitter` only | `bond_scanner` or paper pilot | P2 |

---

## Reproducers

```bash
# Policy / verdict JSON (read-only)
python3 -c "import json; pr=json.load(open('audit_dashboard/data/pf_registry.json')); print([r for r in pr['by_asset_class_policy_clean_net'] if r['asset_class'] in ('COMMODITY','BOND')])"
python3 -c "import json; m=json.load(open('audit_dashboard/data/money_ready_verdict.json')); print({k:{'n':m[k].get('n_resolved'),'ds':m[k].get('data_source')} for k in ('COMMODITY','BOND')})"

# Feature signal emitters
python3 -m tools.feature_signals.orchestrator
FACTOR_EMITTERS_ENABLED=1 python3 -m tools.feature_signals.orchestrator
python3 -m tools.feature_signals.commodity_term_cot

# Bond backtest orphan
python3 tools/backtest_bond_tlt_ief_momentum.py

# Bond scanner
python3 -m alpha_engine.bond_scanner

# 14d panel
cat audit_dashboard/data/pick_summary_stats_14d.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['by_class'].get('BOND'))"
```

---

## Bottom line

- **COMMODITY:** n=7 policy-clean; `commodity_term_cot` is built but not emitting in prod. Fastest n=30 = wire always-on + fix asset_class + paper pilot (~8–12 days).
- **BOND:** n=50 already in `at_raw_picks` (excl backfill) but verdict shows n=0. Fastest n=30 **policy-visible** = pipeline unfreeze + promote `bond_yield_curve_slope` + wire `bond_tlt_ief_v3`. No real-money sizing on either class until policy-clean n≥30 **and** WR/PF hold post-wire-up.

*Prior reports: `reports/edge_hunt_COMMODITY_2026-06-05.md`, `reports/edge_hunt_BOND_2026-06-05.md`, `reports/bond_n_ramp_analysis_2026-06-05.md`.*
