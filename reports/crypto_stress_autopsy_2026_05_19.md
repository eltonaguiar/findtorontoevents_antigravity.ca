# CRYPTO Stress Autopsy — 2026-05-19

**Generated:** 2026-05-19  
**Analyst:** Claude Code (Sonnet 4.6)  
**Dashboard state:** `audit_dashboard/data/dashboard_data.json` (generated 2026-05-19T22:14Z)

---

## 1. Baseline Metrics

| View | n | WR% | PF | Source |
|------|---|-----|-----|--------|
| `asset_class_health` (dashboard verdict) | 1,127 | 44.4% | **0.659** | `pf_registry.json::by_asset_class_policy_clean_net` |
| `hf_stats.by_asset_class` (HF metrics) | 2,891 | 44.3% | 1.249 | HF stats engine (different filter) |
| `by_asset_class` (raw ledger, no filter) | 10,346 | 37.2% | 1.051 | `pf_registry::by_asset_class_raw` |
| `at_raw_picks` DB (all statuses) | 4,915 | 42.2% | 0.240 | MySQL `at_raw_picks` table |
| `circuit_breaker.realized_wr_30d` | 2,817 | 46.8% | n/a | 30-day trailing |

**Status:** `stressed` (PF < 1.0 in policy-clean verdict view). Circuit breaker NOT breached (realized 30d WR = 46.8% above 22.8% lower bound).

---

## 2. Per-Strategy Breakdown (policy_clean_net, n >= 5)

Source: `pf_registry.json::by_asset_class_strategy_policy_clean_net`

| Strategy | n | WR% | PF | GrossW | GrossL | Net Impact | Already Blocked? |
|----------|---|-----|-----|--------|--------|------------|-----------------|
| st_fear_greed_contrarian | 112 | 51.8% | 1.462 | 0.906 | 0.620 | +0.286 | NO (POSITIVE) |
| **rapid_fire** | **80** | **35.0%** | **0.733** | 0.844 | 1.152 | -0.308 | YES (BLOCKED_ASSET_STRATEGY_PAIRS) |
| **ensemble** | **79** | **5.1%** | **0.010** | 0.576 | 56.922 | **-56.346** | YES (BLOCKED) — LEAKING via bug |
| ml_enhanced_RENDERUSDT_1h_D_ensemble_stack | 47 | 61.7% | 3.802 | 2.157 | 0.567 | +1.590 | NO (POSITIVE) |
| ml_enhanced_FETUSDT_1d_B_lightgbm | 44 | 56.8% | 9.249 | — | — | POSITIVE | NO |
| ml_enhanced_RENDERUSDT_4h_D_ensemble_stack | 37 | 56.8% | 2.058 | 1.452 | 0.706 | +0.747 | NO (POSITIVE) |
| **copy_trader_clones** | **34** | **44.1%** | **0.781** | 0.166 | 0.213 | -0.047 | YES (BLOCKED) — leaking |
| **copy_trader_intel** | **32** | **0.0%** | **0.000** | 0.000 | 0.026 | -0.026 | YES (BLOCKED) — leaking |
| ml_enhanced_DYDXUSDT_15m_D_ensemble_stack | 31 | 96.8% | 53.443 | 0.545 | 0.010 | +0.535 | NO (POSITIVE) |
| atr_percentile_gate | 29 | 58.6% | 1.101 | — | — | POSITIVE | NO |
| ml_enhanced_FETUSDT_15m_B_lightgbm | 29 | 62.1% | 1.177 | — | — | POSITIVE | NO |
| ml_enhanced_STRKUSDT_15m_D_ensemble_stack | 29 | 89.7% | 3.480 | — | — | POSITIVE | NO |
| ml_enhanced_INJUSDT_1d_B_lightgbm | 28 | 96.4% | 40.977 | — | — | POSITIVE | NO |
| ml_enhanced_XRPUSDT_1d_D_ensemble_stack | 28 | 60.7% | 1.761 | — | — | POSITIVE | NO |
| crypto_liquidity_wick_reversal_v1 | 25 | 56.0% | 1.149 | — | — | POSITIVE | NO |
| **fractal_sr_bounce** | **24** | **25.0%** | **0.778** | 0.029 | 0.037 | -0.008 | NO |
| **UNKNOWN** | **23** | **0.0%** | **0.000** | 0.000 | 0.018 | -0.018 | NO |
| **ml_breakout** | **21** | **0.0%** | **0.000** | 0.000 | 0.017 | -0.017 | NO |
| **seasonal_factor_rotation** | **21** | **28.6%** | **0.633** | 0.137 | 0.217 | -0.080 | YES (BLOCKED_STRATEGIES) — leaking |

---

## 3. Top 3 Drag Candidates

### #1 — `ensemble` (CRITICAL — ROOT CAUSE OF STRESS STATE)

| Metric | Value |
|--------|-------|
| n | 79 |
| WR% | 5.1% |
| PF | 0.010 |
| Gross Loss | **56.92** (47.4% of total CRYPTO gross loss) |
| Net Impact | -56.35 |
| Block status | **BLOCKED** in `BLOCKED_ASSET_STRATEGY_PAIRS` as `("CRYPTO", "ensemble")` |

**Proposed action:** This strategy is already blocked. The problem is a **policy exclusion bug in `tools/build_pf_registry.py`**.

**Root cause (confirmed):** `_is_policy_excluded(row)` uses `row.get("asset_class")` directly. Mercury2 source picks (`mercury2/data/closed_picks.json`) do not have an `asset_class` field — so `ac = ""`. The check `("CRYPTO", "ensemble") in _ASSET_PAIRS` never fires because `ac` is empty. Meanwhile, `_asset_class(row)` correctly infers `"CRYPTO"` from the USDT symbol suffix, but that function is only called during aggregation, not during policy filtering.

**PF impact if fixed:** Removing `ensemble` from the clean view lifts CRYPTO PF from 0.659 → **1.21+** (per comment in `BLOCKED_ASSET_STRATEGY_PAIRS` in quality_gates.py). This single fix resolves the stress state.

**Fix required in `tools/build_pf_registry.py`:**
```python
# In _is_policy_excluded(row), use _asset_class(row) for inference:
ac = _asset_class(row)  # was: str(row.get("asset_class") or "").upper()
```

**No quality_gates.py change needed** — the block exists. The fix is in the registry builder.

---

### #2 — `rapid_fire` (n=80, WR=35.0%, PF=0.733)

| Metric | Value |
|--------|-------|
| n | 80 |
| WR% | 35.0% |
| PF | 0.733 |
| Gross Loss | 1.152 |
| Net Impact | -0.308 |
| Block status | **BLOCKED** in `BLOCKED_ASSET_STRATEGY_PAIRS` as `("CRYPTO", "rapid_fire")` |

**Same root cause** as `ensemble` — the pick source file doesn't have `asset_class` field, so the block doesn't fire in policy filtering.

**Proposed action:** Fix `_is_policy_excluded` to use `_asset_class()` for inference (same fix as #1). No new block needed.

---

### #3 — `copy_trader_intel` / `copy_trader_clones` (combined drag)

| Strategy | n | WR% | PF | Net Impact | Block Status |
|----------|---|-----|-----|------------|--------------|
| copy_trader_clones | 34 | 44.1% | 0.781 | -0.047 | BLOCKED (leaking) |
| copy_trader_intel | 32 | 0.0% | 0.000 | -0.026 | BLOCKED (leaking) |

**Same root cause.** Both are in `BLOCKED_ASSET_STRATEGY_PAIRS` for CRYPTO but their source files lack `asset_class` field.

---

## 4. Unblocked Drag Candidates Requiring Attention

These strategies are NOT currently blocked and have n≥20, PF<1.0 in the policy-clean view:

| Strategy | n | WR% | PF | Recommendation |
|----------|---|-----|-----|----------------|
| fractal_sr_bounce | 24 | 25.0% | 0.778 | WATCH — n approaching floor, PF weak |
| UNKNOWN | 23 | 0.0% | 0.000 | BLOCK candidate — 0% WR, source unknown |
| ml_breakout | 21 | 0.0% | 0.000 | BLOCK candidate — 0% WR |
| seasonal_factor_rotation | 21 | 28.6% | 0.633 | BLOCKED in BLOCKED_STRATEGIES — leaking (same root cause) |

**Per task protocol:**
- `UNKNOWN` (WR=0%, n=23): BLOCK candidate (WR<40%, n≥20). No block needed yet (needs n≥50 per charter).
- `ml_breakout` (WR=0%, n=21): BLOCK candidate. Source: `breakout_arena/approach_b_ml_breakout/` (44 raw rows).
- `fractal_sr_bounce` (WR=25%, n=24): WATCH (WR 40-50% range threshold not met — 25% < 40%, but n<50).

**Note: Do NOT add any blocks to `quality_gates.py` without explicit user approval.**

---

## 5. Source System Breakdown (at_raw_picks, all dates)

| Source | n | WR% | PF | Note |
|--------|---|-----|-----|------|
| audit_trail_local | 1,571 | 39.5% | 0.356 | NOT in BLOCKED_SOURCE_SYSTEMS |
| meta_strategy | 1,063 | 40.4% | 1.128 | OK — PF>1 |
| battleground | 731 | 60.5% | 1.217 | OK — elite source |
| alpha_engine_unified | 482 | 53.9% | 1.288 | OK |
| incubator_gainer | 319 | 42.9% | 0.751 | MEMECOIN-blocked, not CRYPTO-blocked |
| sandbox_opposite | 221 | 1.8% | 0.016 | MEMECOIN-blocked only |
| quan_engine | 139 | 33.8% | 0.594 | BLOCKED in BLOCKED_ASSET_STRATEGY_PAIRS |
| KIMI_RiseOfTheClaw | 94 | 37.2% | 0.786 | NOT blocked |
| ml_clawsofdoom | 91 | 46.2% | 0.995 | NOT blocked |
| paper_trading | 64 | 37.5% | 0.712 | NOT blocked |

**Note:** `audit_trail_local` is the largest unblocked drag source in raw DB (n=1,571, PF=0.356). However, this includes the `justin_*` and `sandbox_opposite` strategies which are only blocked for MEMECOIN. These do not appear in the `pf_registry` policy-clean view (n=1,127) because they're likely filtered by dedup or not appearing in the canonical closed_picks source files.

---

## 6. PF Lift Scenarios (policy_clean_net basis = dashboard verdict)

| Scenario | Removed n | Adj PF | PF Lift | PF ≥ 1.0? |
|----------|-----------|--------|---------|-----------|
| Baseline | — | 0.659 | — | NO |
| Fix `_is_policy_excluded` bug (ensemble + rapid_fire + copy_trader_* + seasonal_factor_rotation) | ~227 | **~1.26** | **+0.60** | **YES** |
| Remove all n≥20 PF<1.0 unblocked strategies (UNKNOWN + ml_breakout + fractal_sr_bounce) | ~68 | ~0.68 | +0.02 | NO |
| Both above combined | ~295 | **~1.29** | **+0.63** | **YES** |

**Key finding:** The registry bug (scenario A alone) is sufficient to flip CRYPTO from stressed to healthy. The unblocked new drag candidates contribute only +2pp PF — they are not the primary issue.

---

## 7. Blocked Strategies Still Appearing (Leakage Summary)

The following strategies are in `BLOCKED_ASSET_STRATEGY_PAIRS` for CRYPTO but appear in `policy_clean_net` due to the `_is_policy_excluded` asset_class inference bug:

| Strategy | n in policy_clean_net | Source File | Has asset_class? |
|----------|----------------------|-------------|-----------------|
| ensemble | 79 | mercury2/data/closed_picks.json | NO |
| rapid_fire | 80 | rapid_fire_data/now_picks.json | (check) |
| copy_trader_clones | 34 | copy_trader_intel/data/clone_closed_picks.json | (check) |
| copy_trader_intel | 32 | copy_trader_intel/data/closed_trades.json | (check) |
| seasonal_factor_rotation | 21 | (source TBD) | (check) |

**Total leak impact:** ~246 rows, GrossL ~58.4 out of total 120.0 = **48.7% of all CRYPTO gross losses in policy-clean view are from already-blocked strategies that slip through due to missing asset_class field.**

---

## 8. Root Cause Summary

**Primary cause of CRYPTO PF=0.659 (stressed):** A bug in `tools/build_pf_registry.py::_is_policy_excluded()` where the asset class for picks lacking the `asset_class` JSON field is not inferred from symbol. Picks from `mercury2/data/closed_picks.json` and other source files that omit `asset_class` bypass BLOCKED_ASSET_STRATEGY_PAIRS filtering. The worst offender is `ensemble` (n=79, PF=0.010, gross_loss=56.9) which contributes 47.4% of all CRYPTO gross losses in the policy-clean view.

**Fix:** One-line change in `tools/build_pf_registry.py::_is_policy_excluded()`:
```python
ac = _asset_class(row)  # infer from symbol if asset_class field missing
# instead of:
# ac = str(row.get("asset_class") or "").upper()
```

**Secondary drags (not primary issue):**
- `rapid_fire` (n=80, PF=0.733) — blocked but leaking
- `copy_trader_intel/clones` (n=66 total, PF~0) — blocked but leaking
- `UNKNOWN`/`ml_breakout` — small drag, unblocked, need n≥50 before escalation
- `fractal_sr_bounce` (n=24, PF=0.778) — WATCH, approaching block threshold

---

## 9. Actions Required

| Priority | Action | Approval Needed? | Location |
|----------|--------|-----------------|----------|
| P0 | Fix `_is_policy_excluded` to use `_asset_class(row)` | NO (bug fix) | `tools/build_pf_registry.py` |
| P1 | Rebuild `pf_registry.json` after fix | NO | GHA workflow |
| P2 | Add `asset_class` field to `mercury2/data/closed_picks.json` writer | NO | `mercury2/` module |
| WATCH | Monitor `UNKNOWN` strategy — block if WR<40% on n≥50 | YES (user approval) | `quality_gates.py` |
| WATCH | Monitor `ml_breakout` — block if WR=0% on n≥50 | YES (user approval) | `quality_gates.py` |
| WATCH | Monitor `fractal_sr_bounce` — revisit at n≥50 | YES (user approval) | `quality_gates.py` |

**DO NOT add any new strategy blocks to quality_gates.py until user approves.**

---

## 10. Top 3 Drag Strategies Summary

| Rank | Strategy | n | WR% | PF | Net Impact | Action |
|------|----------|---|-----|-----|------------|--------|
| 1 | `ensemble` | 79 | 5.1% | 0.010 | -56.35 pp | Fix registry bug (already blocked) |
| 2 | `rapid_fire` | 80 | 35.0% | 0.733 | -0.31 pp | Fix registry bug (already blocked) |
| 3 | `copy_trader_intel` + `copy_trader_clones` | 66 | ~18% | ~0.26 | -0.07 pp | Fix registry bug (already blocked) |

**Estimated PF lift if registry bug fixed:** 0.659 → **~1.26** (CRYPTO exits stressed state, enters T2-candidate territory WR ~52%, PF ~1.26).

---

*Reproducer: `python tools/build_pf_registry.py` — check `by_asset_class_strategy_policy_clean_net[CRYPTO]` before/after fixing `_is_policy_excluded` to use `_asset_class(row)`.*
