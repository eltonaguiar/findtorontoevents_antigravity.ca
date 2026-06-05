# BOND Edge Hunt — 2026-06-05

**Goal #1 audit.** Sources: `pf_registry.json`, `money_ready_verdict.json`, `pick_summary_stats_14d.json`, orphan backtest JSONs.

## Verdict: **INSUFF-N — no real-money edge**

| Layer | n | WR | PF | Status |
|-------|---|----|----|--------|
| `money_ready_verdict` | 0 resolved | — | — | INSUFFICIENT_DATA |
| `pf_registry` raw | 8 | 25% | 2.74 | single-source artifact |
| `pf_registry` deduped | 6 | 33% | 3.16 | absent from `policy_clean_net` |
| `at_raw_picks` 14d | 45 closed | 46.7% | 1.12 | accumulating, n<100 |

**Tier gate:** n≥100 required. Registry n=6–8; ~78 `at_raw_picks` rows per `/audit` banner (up from 2 on 2026-05-31). Emissions real; resolved sample not.

## 1. Accumulation (pf_registry + at_raw_picks)

- **Emitter:** `bond_scanner` (100% of closed registry rows). Strategies: `bond_yield_momentum`, `bond_yield_curve_slope`.
- **14d panel:** 70 touched / 45 closed; top symbol IEF (44%); 80% AlphaEngine concentration.
- **48h:** 3 active (HYG×2, LQD×1), 0 closed — resolver lag, not silence.
- **Symbols traded:** TLT, HYG, SHY, EMB, BNDX — universe still **4–5 symbols** in `non_crypto_policy.BOND_SYMBOLS` (TLT, IEF, HYG, ZN=F).

## 2. Orphan backtests (proven offline, zero production callers)

| Backtest | Universe | PF | WR | MDD |
|----------|----------|----|----|-----|
| `bond_tlt_ief_v3_24m` | TLT/IEF/SHY | **1.29** | 54.3% | 23.0% |
| `bond_hyg_lqd_v1` | HYG/LQD | **1.62** | 62.7% | 29.1% |

**0 production_scanner callers** — Wire-Up violation. Cousin `bond_hyg_lqd_momentum_winner` lives in `priority_picks_emitter` only.

## 3. `bond_duration_momentum.py` wiring

- Registered in `tools/feature_signals/orchestrator.py` sleeve `bond_duration_momentum`.
- **Gated OFF:** requires `FACTOR_EMITTERS_ENABLED=1`; module sets `production_enable: False`.
- `feature_signals_20260605.json`: no BOND sleeves emitted. Output file `bond_duration_momentum_signals.json` does not exist.
- **Status:** opt-in sidecar only; not in live pick path.

## 4. FRED / yield-curve signals

- `fred_macro_context.py`: DGS10, DGS2, **T10Y2Y** → `curve_regime` {inverted/flat/steep}. Dashboard-wired via `summarize_for_dashboard()`.
- `bond_scanner.py`: fetches FRED via `fetch_bond_bundle` for `bond_yield_curve_slope` — **separate path**, not `fred_macro_context`.
- Curve_regime → bt_pf shrinkage overlay is **doc-only**; not in `bond_scanner`.

## 5. Fast path — paper pilot from backtest

**Highest-EV low-effort action:**

1. **Wire `bond_tlt_ief_v3` rotation** into `bond_scanner.STRATEGIES` (24m dual-momentum TLT/IEF/SHY). Backtest PF 1.29 / WR 54% is sub-T2 but best duration signal in repo.
2. **Enable `bond_hyg_lqd_momentum_winner`** paper pilot (`paper_pilot: True` already set) — mirrors `bond_hyg_lqd_v1` PF 1.62 logic.
3. Expand `BOND_SYMBOLS` to include LQD, SHY, AGG (scanner already knows them; policy whitelist blocks).

Existing pilots: `risk_parity_bond_tlt_short` / `shy_short` — hist n=5, forward n=0. Not rotation.

## Ranked actions

| # | Action | Evidence | ETA |
|---|--------|----------|-----|
| 1 | Wire orphan TLT/IEF rotation → `bond_scanner` | PF 1.29 backtest | 1 PR |
| 2 | Paper-pilot HYG/LQD winner via priority emitter | PF 1.62 backtest | same PR |
| 3 | `FACTOR_EMITTERS_ENABLED=1` + flip `production_enable` on duration momentum | module exists | after #1 review |
| 4 | Hook `fred_macro_context.curve_regime` into bond confidence | wiring plan §3 | next sprint |

**Do not size up.** Forward n<10; backtest edge is orphan; live WR 25–47% on tiny n. Paper-only until n≥100 post-wire-up.

*Reproducers:* `python3 tools/backtest_bond_tlt_ief_momentum.py`; `audit_dashboard/data/bond_tlt_ief_v3_24m.json`; `python3 -m alpha_engine.priority_picks_emitter --dry-run`
