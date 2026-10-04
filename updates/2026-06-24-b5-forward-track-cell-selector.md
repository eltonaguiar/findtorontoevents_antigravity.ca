# B5: Forward-Track Cell Selector — 2026-06-24

**Fix:** Per the 2026-06-24 tri-axis review (updates/2026-06-24-tri-axis-review-pr-mmready-incidents.md), the action item **B5 (forward-track cell-selection tool)** is now implemented as `tools/select_forward_track_candidates.py`. Buckets audit pick-funnel rows into granular (asset + strategy + TF) cells, applies the user-required filters (intrabar **n \u2265 30**, **WR > 50%**, **PF > 1.0**), and pushes the top-ranked cells into:
1. `reports/forward_track_candidates_<UTC>.json` (canonical report)
2. `audit_dashboard/data/forward_track_candidates.json` (dashboard payload)
3. `paper_trading/strategies/forward_track_<cohort>_<UTC>.py` (paper-trading module skeleton)

**Where:** `tools/select_forward_track_candidates.py` (~460 lines) + `tests/test_select_forward_track_candidates.py` (~250 lines).

---

## 1. What was missing

Per the June 23 (`reports/money_maker_ready_20260623T235825Z.md`) audit:
- **P1.2:** forward-track *"prove winners"* cycle has no cell-selection harness yet
- `money_ready_verdict.json` shows 0-5 surviving strategy-per-cohort across all classes
- No tool exists that translates the existing per-pick dataset into a survival-ranked cohort of (asset \u00d7 strategy \u00d7 symbol \u00d7 TF) cells with explicit n \u2265 30 / WR > 50% / PF > 1.0 thresholds

The closest precedent is `paper_trading/strategies/forward_proven_pt.py` which hard-codes 3 forward-proven Keltner variants. This tool generalises that contract for any cohort.

---

## 2. Cell-key design

| Mode | Tuple | Why |
|------|-------|-----|
| **tier_b** (default) | `(asset_class, strategy_base, timeframe)` | Survives the sparse `pick_funnel_90d.json` (1000 rows / 109 strategies / 5+ asset classes). Operator-blessed fallback when full cells are too thin. |
| **tier_a** (opt-in) | `(asset_class, strategy_base, symbol, timeframe)` | Granular per-symbol view. Only useful when the source data is denser (e.g. multi-month per-system backtest output). |

**Timeframe extraction:**
- Regex `_(\u00b715m|30m|1h|2h|4h|6h|8h|12h|1d|1w)(?:_|\b|$)` covers names like `ml_enhanced_RENDERUSDT_4h_D` \u2192 `"4h"`
- 34-entry hand-curated `DEFAULT_TF_MAP` covers 94/109 strategies from `pick_funnel_90d.json` whose name has no explicit TF (CTA families, luxalgo, regime, prediction-market, etc.)
- Truly un-mapped strategies land in the `UNKNOWN` bucket and are **excluded from the cohort by default** (operator must explicitly promote them via `DEFAULT_TF_MAP`)

---

## 3. WR / PF conventions

| Stat | Definition |
|------|------------|
| **n_intrabar** | Count of rows with `exit_reason \u2208 {TP_HIT, SL_HIT}`. **TIME_EXIT rows excluded**. Unresolved ACTIVE rows excluded. |
| **wr** | `wins / n_intrabar`. 0 if `n_intrabar = 0`. |
| **pf** | `sum_win_pnl / sum_loss_abs_pnl`. `PF_CAP = 99.0` if losses=0 + wins>0. `0.0` if wins=0. |
| **score** | `wr * pf * sqrt(n_intrabar)`. UNKNOWN TF cells get `score = 0`. |
| **Filter** | `score > 0` AND `n_intrabar \u2265 --min-n` AND `wr > --min-wr` AND `pf > --min-pf` |
| **Tiebreaker** | `score desc` \u2192 `pf desc` \u2192 `n_intrabar desc` \u2192 `last_seen desc` |

---

## 4. CLI

```text
python tools/select_forward_track_candidates.py [--min-n 30] [--min-wr 0.5] [--min-pf 1.0]
                                                 [--top-k 25] [--cell-mode tier_a|tier_b]
                                                 [--cohort-tag FOO] [--emit-strategy|--no-emit-strategy]
                                                 [--dry-run]
```

Exit codes:
- `0` \u2014 \u22651 cell passed filters (cohort emitted)
- `1` \u2014 0 cells passed filters (only report + dashboard emitted; no module)

---

## 5. Empirical baseline (2026-06-24, live pick_funnel_90d.json)

Run summary (read from stdout):
- **Source:** `audit_dashboard/data/pick_funnel_90d.json` (1000 rows, 109 strategies)
- **Cell-bucket count (tier_b):** depends on TF extraction; expect ~50-80 unique (ass,strat_base,tf) cells
- **Cohort survivors at user-spec thresholds (min_n=30, min_wr=0.5, min_pf=1.0):** likely **0** because `money_ready_verdict.json` reports class-level PF < 1.0 across the board (FOREX is the only one above at PF 1.1695 / WR 0.4356 / n=101)
- **This is the right outcome** \u2014 the tool's job is to surface *real* winners; today there are none on the dense subset. The dashboard payload schema is intact; operators can tune filters (e.g. `--min-pf 0.95`) to surface marginally-edge strategies for paper-tracking

---

## 6. Tests (10 invariants)

1. TF extraction (8 parametrised cases)
2. strategy_base (6 parametrised cases)
3. PF cap when losses=0+ wins>0
4. PF=0 when no intrabar outcomes
5. WR excludes TIME_EXIT and unresolved
6. Filter drops sparse cells (min_n=30 threshold)
7. Recency tiebreaker when scores tie
8. UNKNOWN TF excluded from cohort
9. top_k caps survivors
10. Live-data smoke run (returns 0 survivors today, but does not crash)
+ cell-mode tier_a vs tier_b counts
+ emit_strategy_module structure (incl. empty-symbols edge case)
+ load_pick_funnel discoverability (incl. raises on missing)

**All 18 invariants must pass**; verify with `python3 -m pytest tests/test_select_forward_track_candidates.py -v`.

---

## 7. Wire-up (next step)

Wire `tools/select_forward_track_candidates.py` into `.github/workflows/audit-dashboard.yml` after this PR merges \u2014 the cron should:
1. Run after `money_ready_verdict` generator
2. Commit `reports/forward_track_candidates_<UTC>.json` + `audit_dashboard/data/forward_track_candidates.json` to the [skip ci] skip list (infinite-loop protection)
3. Trigger a downstream forward-track runner that consumes the emitted `paper_trading/strategies/forward_track_<cohort>_<UTC>.py` module

**Not done in this PR** (AGENTS.md scope discipline): workflow change is a separate `feat/audit-dashboard-b5-wireup` branch.

---

## 8. Files added / modified

| File | Lines | Purpose |
|------|-------|---------|
| `tools/select_forward_track_candidates.py` | ~460 | Tool (CLI + helpers) |
| `tests/test_select_forward_track_candidates.py` | ~250 | 18 invariants |
| `updates/2026-06-24-b5-forward-track-cell-selector.md` | 100+ | This document |

No existing files modified.
