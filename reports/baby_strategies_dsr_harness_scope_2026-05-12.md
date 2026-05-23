# Baby-Strategies Batch Backtest Harness — Scope 2026-05-12

Per Investigator `a25c3ebf9b4cf8455`. Five-step plan to turn 206 dormant
files in `baby_strategies/` into a ranked DSR table that surfaces top
candidates for production promotion.

## Current state

- **206 .py files** in `baby_strategies/`
- All are **signal-emitters** (Signal dataclass) — NOT self-contained
  backtesters. Each emits `Signal(symbol, direction, confidence, entry_price)`
  but requires an external harness to run a backtest.
- **Zero wired** to production scanner (`alpha_engine/production_scanner.py`).
- **Existing infra**:
  - `alpha_engine/vectorized_backtest.py` — pure-numpy 2ms/backtest Keltner kernel
  - `alpha_engine/incubator/fast_backtester.py:76` — yfinance + parquet cache
  - `alpha_engine/incubator/run_incubator.py:38` — orchestrator (seed→permute→batch→rank→SQLite)
  - `alpha_engine/data/price_loader.py:29 PriceLoader.load()` — canonical OHLCV loader
  - `tools/anti_overfit_audit_sidecar.py:72-92` — DSR via Lopez de Prado eq 14.5
    + `deflated_sharpe()` function (reuse, don't reinvent)
- **`anti_overfit_audit_sidecar.py` input shape**: `{strategy_name: [pnl_pct_1, pnl_pct_2, ...]}`
  with n ≥ 10 (configurable via `--min-n`). Pulls from MySQL
  `trading_picks` by default; harness needs to feed it the in-memory dict.

## 5-step harness plan

### Step 1 — Adapter layer (smallest unit)

**File**: `baby_strategies/_adapter.py` (~150 lines).

Wrap each `baby_strategies/` signal-emitter in a standard interface:
```python
def backtest_strategy(strategy_module, ohlcv_df) -> list[Trade]:
    """Returns list of (entry_idx, exit_idx, entry_price, exit_price, direction) tuples."""
```
Reuse `vectorized_backtest.py` TP/SL/slippage logic; don't reinvent.

### Step 2 — Batch loader

**File**: `tools/batch_baby_backtest.py` (~250 lines).

1. Scan `baby_strategies/*.py` for `SYMBOLS` constant + `Signal` class.
2. Load OHLCV via `price_loader.PriceLoader` for each symbol (1y history,
   parquet cache at `alpha_engine/data/prices/`).
3. Iterate 206 strategies × symbols; call adapter; collect trade arrays.

### Step 3 — DSR compute

Feed trade PnL arrays into `anti_overfit_audit_sidecar.deflated_sharpe()`
(reuse existing implementation). Output schema:
```json
{
  "strategy_name": {
    "n": int, "wr_pct": float, "pf": float,
    "sharpe": float, "dsr": float, "verdict": "EDGE_LIKELY_REAL|NEEDS_MORE_DATA|OVERFIT_LIKELY"
  }
}
```
Gate at DSR ≥ 0.95 ("EDGE_LIKELY_REAL").

### Step 4 — Rank + export

**Output**:
- `audit_dashboard/data/baby_strategies_dsr.json` — full ranking table
- `reports/baby_strategies_dsr_ranking_YYYY-MM-DD.md` — top-50 markdown
  report with cite (backtest start/end, symbol set, slippage assumptions)
- `reports/baby_strategies_ready_for_promotion.json` — top candidates
  flagged for production-scanner wiring

### Step 5 — Promotion gate (no auto-wire)

Each top candidate tagged with `"NEXT_STEP": "wire to production_scanner OR run real-money paper sandbox via TradingView"`. **Do NOT auto-wire**. Promotion requires explicit PR per CLAUDE.md Wire-Up Rule.

## Constraints honored

- ✓ Reuses `anti_overfit_audit_sidecar.py::deflated_sharpe()` — no duplicate Lopez de Prado implementation
- ✓ Uses canonical `price_loader.py` — no new yfinance call paths
- ✓ Zero changes to live production code on this PR
- ✓ Runs offline (parquet cache means second run is fast)
- ✓ ~400-500 lines total across 2 new files (adapter + batch loader)

## Effort estimate

- Step 1 adapter: 1-2h
- Step 2 batch loader: 2-3h
- Step 3 DSR wiring: 1h
- Step 4 report writer: 1h
- Step 5 promotion JSON: 30min
- **Total**: ~6h end-to-end for first run; subsequent runs cron-able

## Risk register

| Risk | Mitigation |
|---|---|
| 206 strategies × 50 symbols × 1y OHLCV = ~10k backtests | Parquet cache OHLCV; reuse vectorized_backtest's 2ms kernel → ~20s total. |
| Some strategies don't have `SYMBOLS` attribute | Skip with warning; report list of non-conformant strategies separately. |
| DSR n<10 floor excludes too many | Run with `--min-n 5` for first pass; surface ALL n≥5 candidates with separate "thin-sample" bucket. |
| Look-ahead bias in signal generation | Use only OHLCV available before signal_emit timestamp; vectorized_backtest already enforces this for Keltner kernel. |
| Promotion candidate fails live | Production wiring is a separate manual PR per Wire-Up Rule; promotion JSON is advisory only. |

## Refs

- Investigator `a25c3ebf9b4cf8455` output (2026-05-12)
- `tools/anti_overfit_audit_sidecar.py:72-92`
- `alpha_engine/vectorized_backtest.py:1-56`
- `alpha_engine/incubator/fast_backtester.py:76-80`
- `alpha_engine/data/price_loader.py:29-60`
- CLAUDE.md Wire-Up Rule (no orphan integrations)

## Status

**SCOPE COMPLETE.** Implementation queued — 2026-05-12 session ran out of
bandwidth on this. Next session can pick up Step 1 directly.
