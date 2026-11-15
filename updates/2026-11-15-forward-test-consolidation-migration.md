# Forward-Test Tracker Consolidation — Migration Guide

**Date:** 2026-11-15  
**Worktree:** hilarious-seer  
**Canonical module:** `alpha_engine/forward_test_canonical.py`

---

## Problem

Four independent forward-test trackers had diverged, each implementing a subset of the forward-test protocol:

| File | Purpose | Data model |
|------|---------|------------|
| `simulations/forward_test_tracker.py` | Absolute promotion gates (paper→probation→small_live→full_live) | JSON results files |
| `tools/forward_test_tracker.py` | Benchmark-relative excess vs SPY/BTC/GLD/BND | Closed-pick JSON |
| `alpha_engine/data/forward_testing/forward_tracker.py` | K1-K8 kill / P1-P7 promote signals | CSV ledger |
| `cross_aggregation/forward_test_tracker.py` | Pick-level TP/SL live tracking | JSON pick outcomes |

None of them talked to each other, and the QA ledger (`tools/qa_ledger.py`) was a separate validation layer that downstream systems ignored.

---

## Solution

A single **canonical module** unifies all four trackers plus the QA ledger filter.

### New canonical file

```
alpha_engine/forward_test_canonical.py
```

### What it does

1. **StrategyTracker** — strategy-level forward testing
   - Absolute gates (paper / probation / small_live / full_live)
   - Fast elimination triggers (PF<0.70, WR<30%, maxDD<-35%, etc.)
   - K1-K8 kill signals
   - P1-P7 promotion criteria
   - Benchmark-relative excess computation (vs SPY/BTC/GLD/BND/^DXY)
   - QA ledger flag ingestion (skips/flags symbols with CRITICAL QA flags)

2. **PickTracker** — pick-level TP/SL tracking
   - Ingests high-score picks (confidence >= 75)
   - Checks live prices against TP/SL
   - 48-hour expiry
   - Freshness buckets (fresh / mid / stale)
   - Score-bucket WR analytics
   - QA filter at ingestion time (drops flagged symbols)

3. **LegacyCSVAdapter** — backward compatibility
   - Reads existing `alpha_engine/data/forward_testing/*.csv` files
   - Lets you migrate historical data without reformatting

4. **QALedgerFilter** — unified QA input
   - Reads `audit_dashboard/data/qa_market_validation.json`
   - Surfaces critical flags (UNPRICED, UNVERIFIED_ZERO, MISMATCH, PNL_OUT_OF_BOUNDS)
   - Both StrategyTracker and PickTracker consume this filter

---

## Deprecation & Migration

### Deprecated files (do not edit — migrate to canonical)

| Deprecated file | Replacement in canonical | Action required |
|-----------------|--------------------------|-----------------|
| `simulations/forward_test_tracker.py` | `StrategyTracker.check_gate()` + `check_fast_elimination()` | Port `--batch` calls to `python -m alpha_engine.forward_test_canonical --mode strategy --results-dir <dir>` |
| `tools/forward_test_tracker.py` | `StrategyTracker.compute_benchmark_excess()` | Port `--picks` calls to `python -m alpha_engine.forward_test_canonical --mode strategy` |
| `alpha_engine/data/forward_testing/forward_tracker.py` | `StrategyTracker.check_kill()` + `check_promote()` + `LegacyCSVAdapter` | Continue logging trades to legacy CSVs, or migrate to canonical JSON output |
| `cross_aggregation/forward_test_tracker.py` | `PickTracker` | Continue using same output path (`cross_aggregation/data/forward_test_results.json`); logic is now imported/callable from canonical module |

### QA ledger integration

`tools/qa_ledger.py` is **not deprecated** — it still produces `audit_dashboard/data/qa_market_validation.json`.  
The canonical tracker now **consumes** that JSON as a first-class input, so QA flags actually block bad picks/strategies instead of just sitting in a report.

---

## CLI Usage

### Strategy mode (replaces simulations + tools trackers)

```bash
# Evaluate all strategies from legacy CSVs
python -m alpha_engine.forward_test_canonical --mode strategy

# Evaluate one strategy + load its result JSON for gate checks
python -m alpha_engine.forward_test_canonical \
  --mode strategy \
  --strategy-id MyStrategy \
  --results-dir simulations/
```

### Pick mode (replaces cross_aggregation tracker)

```bash
# Ingest new picks and check outcomes
python -m alpha_engine.forward_test_canonical --mode pick --picks-json data/aggregated_picks.json

# Check outcomes only
python -m alpha_engine.forward_test_canonical --mode pick
```

### Unified mode (recommended for CI / cron)

```bash
python -m alpha_engine.forward_test_canonical --mode unified
```

Outputs: `alpha_engine/data/forward_testing/forward_test_canonical.json`

---

## Output Schema (unified mode)

```json
{
  "generated_at": "2026-11-15T05:...",
  "protocol_version": "2026-11-15-v2-canonical",
  "mode": "unified",
  "strategy_decisions": [
    {
      "strategy_id": "...",
      "status": "ELIMINATED|EXTENDED|FULL_LIVE|HOLD|...",
      "kill_code": "K3",
      "kill_reason": "PF < 0.80 after 25 trades",
      "current_gate": "probation",
      "next_gate": "small_live",
      "metrics": { "total_trades": ..., "win_rate_pct": ..., "sharpe": ..., ... },
      "benchmark_excess": { "verdict": "MONITOR|ELIMINATE_FAST|HOLD_EXTEND", "n": ..., ... },
      "qa_flagged": true|false,
      "action": "..."
    }
  ],
  "pick_stats": { "total": ..., "active": ..., "won": ..., "lost": ..., "wr_overall": ... },
  "pick_exits_this_run": 0,
  "qa_summary": { "total_flags": 698, "critical_symbols": [...] }
}
```

---

## Blockers / Risks

1. **yfinance dependency** — benchmark-relative mode requires `pandas`, `numpy`, and `yfinance`. If these are missing, the module falls back to `"verdict": "NO_YFINANCE"` but still runs gates and K1-K8.
2. **CSV location** — `LegacyCSVAdapter` expects legacy CSVs at `alpha_engine/data/forward_testing/*.csv`. If your worktree stores them elsewhere, pass a symlink or edit `LegacyCSVAdapter.*_CSV` paths.
3. **PickTracker output path** — still writes to `cross_aggregation/data/forward_test_results.json` to avoid breaking existing dashboard consumers.
4. **QA ledger staleness** — canonical consumes whatever `qa_market_validation.json` is on disk. Run `tools/qa_ledger.py` first if you need fresh flags.

---

## Rollback Plan

No files were deleted. All four legacy trackers remain in place. If the canonical module misbehaves:

1. Stop calling `alpha_engine.forward_test_canonical`
2. Re-enable calls to the legacy tracker of your choice
3. File a bug in `updates/` describing the mismatch

---

## Checklist for other worktrees

- [ ] Read this migration doc
- [ ] Run `python -m alpha_engine.forward_test_canonical --mode unified` and inspect `forward_test_canonical.json`
- [ ] Verify that `strategy_decisions` include all strategies you care about
- [ ] Verify that `pick_stats` align with `cross_aggregation/data/forward_test_results.json`
- [ ] If benchmark-relative decisions differ from the old `tools/forward_test_tracker.py`, diff the `rows` array in `benchmark_excess`
- [ ] Update any CI cron jobs to call the canonical module instead of legacy trackers
- [ ] Update documentation / runbooks that reference the old file paths
