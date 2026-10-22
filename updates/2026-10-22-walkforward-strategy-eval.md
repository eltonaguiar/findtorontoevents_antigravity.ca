# Walk-forward strategy evaluation harness — 2026-10-22

## What was broken / missing
The system had no "closest to forward test" tool: hundreds of strategies exist, but no
strict, leakage-controlled out-of-sample evaluation that ranks cells by whether an edge
*survives* a future window. Retrospective aggregate PF can't be trusted (frozen-exit
artifacts, sentinels, flat-zero rows).

## What was added
- [`tools/walkforward_strategy_eval.py`](../tools/walkforward_strategy_eval.py) — reads
  closed resolved picks (`dashboard_data.json` → `picks.recent_closed`), drops sentinel /
  flat-zero / missing-pnl / duplicate-id rows, flags frozen-exit cluster cells
  (wins > 2 × distinct exit dates), splits chronologically 50/50, and ranks
  (asset_class, symbol, strategy, direction) cells whose edge is stable out-of-sample.
- [`tests/test_walkforward_strategy_eval.py`](../tests/test_walkforward_strategy_eval.py) — 8 tests, all pass.
- [`reports/walkforward_strategy_eval_2026-10-22.json`](../reports/walkforward_strategy_eval_2026-10-22.json) — run output.

## Winner gate (strict)
test n ≥ min_n, test PF ≥ 1.15, test WR ≥ 0.50, train PF > 1.0, and not an artifact cell.

## Results (2026-10-22 run)
- raw=3500, clean=3446 (54 sentinel/flat dropped), train=1669 / test=1669.
- **19 frozen-exit artifact cells flagged** (e.g. `CRYPTO|ADA|momentum_breakout|LONG`,
  `CRYPTO|BTCUSDT|atr_percentile_gate|LONG`).
- **Zero cells pass the strict winner gate** on this dataset. No asset class has a
  statistically proven winning sleeve yet.
- Class-level (test half): FOREX n=26 PF 3.15 (small n), CRYPTO n=1430 PF 1.27
  (WR 44% < 50%), EQUITY n=120 PF 0.98, ETF n=82 PF 0.72.
- Closest clean candidates (each fails ≥1 gate): `CRYPTO|JUPUSDT|mega_mutation_macd_rsi_m048|LONG`
  (te n=11 WR 63.6% PF 3.99, but train n < 10), and `luxalgo_confluence` crypto cells
  (PF > 1 but WR < 50%).

## Honest interpretation
This is the closest-to-forward evidence we can produce pre-paper-trading. It supports the
cross-agent conclusion: the problem is measurement + no surviving edge yet, not a lack of
ideas. The gate is intentionally strict so that a promoted cell is actually defensible.

## How verified
- Unit tests: `python3 -m pytest tests/test_walkforward_strategy_eval.py -q` → 8 passed.
- Live run: `python3 tools/walkforward_strategy_eval.py --input audit_dashboard/data/dashboard_data.json` → exit 0, JSON report written.
- No production behavior changed; this tool is read-only.
