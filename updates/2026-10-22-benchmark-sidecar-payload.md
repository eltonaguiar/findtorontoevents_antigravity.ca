# 2026-10-22 — Benchmark Sidecar wired into the Measurement Hygiene payload (Task 5)

## What was broken / missing

`alpha_engine.benchmark_closed_ledger.build_report()` existed, was fully tested
(33 deterministic tests), and generated everything the dashboard needed — per-ledger
benchmark, paired bootstrap vs the same-window SPY / BTC-USD series, and random-entry
Monte Carlo timing — but **it was never called from `generate()`**. The only consumer
was the per-pick reader `attach_benchmark_column()`, which reads the on-disk sidecar
file `audit_dashboard/data/benchmark_ledger_proof.json`. That sidecar file is not
generated anywhere in the pipeline, so every pick carried `benchmark: None`. The
dashboard could not answer the core question: *"did this ledger beat SPY / BTC-USD
on its own trading window?"*

## What changed

1. New fail-soft, module-level helper `_build_benchmark_sidecar(rows)` in
   `audit_trail/dashboard_generator.py` (placed immediately after
   `_build_ledger_measurement_block`, before `generate()`). It calls
   `build_report(rows, prices_by_sym={}, n_boot=10_000, n_perm=10_000, seed=42)`
   in memory and returns `{"benchmark_sidecar": <ledgers list>}`.
   - Fail-soft: returns `{"benchmark_sidecar": None}` when `rows` is empty, when
     `build_report` raises (capped at 200 chars via `benchmark_error`), or when the
     report carries no `ledgers`. It never raises — a benchmark failure must never
     break the dashboard.
2. Wired into the gated block inside `generate()` (only when
   `MEASUREMENT_HYGIENE_V1` is on), after `stamp_net_of_cost` so the benchmark runs
   on net-of-cost rows: `_measurement_block.update(_build_benchmark_sidecar(resolved_closed))`.
3. Result surfaces at `payload["summary"]["measurement_hygiene"]["benchmark_sidecar"]`
   (the existing `measurement_hygiene` block already carries it; no new top-level key).

**`prices_by_sym` choice:** passed `{}`, not `None`. `benchmark_ledger()` calls
`prices_by_sym.get(...)` in two places (the benchmark-series lookup and `_own_series`),
so `None` would raise `AttributeError`. `{}` is safe and semantically identical to
"no external price data" — leading to the documented "timing tests skipped" notes.

## How verified

- New: `pytest tests/test_benchmark_sidecar_payload.py -q` → **4 passed** in 0.47s.
- Regression: `pytest tests/test_ledger_gates.py tests/test_dashboard_generator_net_pf_wireup.py tests/test_compound_overlap_aware.py tests/test_dashboard_generator_measurement_hygiene.py -q` → **29 passed** in 0.79s.
- Syntax: `python3 -c "import py_compile; py_compile.compile('audit_trail/dashboard_generator.py', doraise=True)"` → clean.

## Acronyms, expanded

- **PF** — Profit Factor (gross profit ÷ gross loss).
- **MDD** — Maximum Drawdown (largest peak-to-trough decline).
- **CI** — Confidence Interval (here: Wilson interval around win rate / PF).
- **PnL** — Profit and Loss.
- **MC** — Monte Carlo (random-entry timing test).
- **SPY** — SPDR S&P 500 ETF Trust (US large-cap benchmark).
- **BTC-USD** — Bitcoin / US Dollar (crypto benchmark).
- **TDD** — Test-Driven Development (write the failing test first, watch it fail, implement, watch it pass).
- **JSON** — JavaScript Object Notation.
- **API** — Application Programming Interface.

## ELI5

Imagine you're a student grading your own homework and you never look at anybody
else's answers. You might think you did great, but you have no outside reference
to compare against. This change writes down what a boring index fund (SPY for
stocks, BTC-USD for crypto) would have made over the *exact same dates* each
strategy was trading. Now the dashboard can show whether a strategy actually added
anything beyond just investing in the index — that is the "did this ledger beat the
benchmark" question. Because the benchmark is built in memory directly from the
closed ledger, we get the comparison even when the on-disk sidecar file doesn't
exist yet, and if the benchmark computation ever fails it degrades gracefully
instead of breaking the whole dashboard.
