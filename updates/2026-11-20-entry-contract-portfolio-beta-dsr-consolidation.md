# Entry contract, portfolio beta, and retiring the broken DSR engine

Date: 2026-11-20
Author: freebuff (deepseek-v4-flash)

## 1. Entry fields are now a contract, and backfilled where derivable

**What was broken.** 51.5% of the 3,500 resolved picks in `dashboard_data.json` carried
an empty `entry_time`. The dashboard ingest derived `entry_ts` from a key list and then
wrote it verbatim, so a pick whose timestamps lived under `timestamp` came out blank —
and every regime, hedge, path and time-in-market analysis silently lost that row.
H-147 could only cover 331 of 3,500 picks because of it.

**What changed.**
- `alpha_engine/pick_contract.py` (new): one priority order for deriving
  `entry_time`/`entry_price` (`entry_time` → `entry_date` → `opened_at` → `signal_time`
  → `generated_at` → `created_at` → `timestamp`), normalising to `YYYY-MM-DDTHH:MM:SSZ`
  (naive = UTC, offset-aware converted). It **never invents a price**: zero and missing
  both stay `None`, and `entry_fields_complete` records the difference. `coverage()`
  reports the percentages so a report can state what it covers.
- `audit_trail/dashboard_generator.py`: `"entry_time": entry_ts` → `entry_ts or ts or ""`.
  One line, at the single point every ingested pick passes through.
- `tools/backfill_entry_fields.py` (new): writes `audit_dashboard/data/entry_fields_backfill.json`,
  a joinable sidecar of derived fields for rows emitted before the contract. The published
  payload is generated, so it is not rewritten in place.

**Measured effect on the existing book:** `entry_time` coverage **51.46% → 96.91%**
(1,801 native + 1,591 derived from `timestamp`); `both` coverage **51.46% → 96.91%**
(entry_price was already 100%). The remaining 3.1% carry no timestamp of any kind.

## 2. H-147 decided at portfolio level

`tools/portfolio_beta_regression.py` regresses the equal-weight book's daily return on SPY.
Result: **β = 0.046** (t = 2.91), **alpha +4.92%/yr (t = 1.49)**, 1,792 picks, 168 days.
The book is market-neutral — so the edge is not beta — but the alpha is not significant.
Both the "it's just beta" and the "it's real selection" readings fail. See
`reports/H147_beta_hedge_selection_alpha_2026-11-20.md` for the caveats (even-accrual
smoothing understates β and overstates t).

## 3. Three DSR implementations → one trustworthy one

| implementation | status |
|---|---|
| `alpha_engine/deflated_sharpe.py` (Bailey/López de Prado, takes `nb_trials`) | **canonical** — promotion path uses it |
| `alpha_engine/validation/sharpe_metrics.py` | Sharpe/SE — a **t-statistic**, no trial correction. Docstring said "DSR"; now says what it actually is and points to the canonical one. |
| `probabilistic_sharpe_engine.py` (root) | **retired**: it scored 1.0282 on zero-edge noise |

**Why it was wrong.** `_calculate_expected_max_sharpe(n)` used `sqrt(2/n·log(n))` with
`n` = **sample length**, so a longer backtest of one strategy looked like more
multiplicity, and the returned `deflated_sharpe` was a Sharpe-unit difference that callers
read as a probability — hence 1.0282. It now takes `n_trials` explicitly, computes
`sd_sr · ((1−γ)Z⁻¹(1−1/N) + γZ⁻¹(1−1/(Ne)))` with γ = 0.5772, and returns a genuine
probability in [0,1]. Results carry `deprecated: True` and `use_instead`. Nothing in the
tree imports it, so this is a trap removed before it was triggered.

## 4. Verification

```
python3 -m pytest tests/test_pick_contract_2026_11_20.py -q   ->  14 passed
python3 -m pytest tests/test_profit_program_math_2026_11_20.py \
                 tests/test_profit_program_policies_2026_11_20.py -q  ->  16 passed (unchanged)
python3 -c "import py_compile; ..."  ->  generator, engine, contract, sharpe_metrics compile
python3 tools/backfill_entry_fields.py  ->  before 51.46% / after 96.91%
python3 tools/portfolio_beta_regression.py  ->  beta 0.046, alpha t 1.49
```

Noise test: seeded zero-edge returns with `n_trials=100` yield `deflated_sharpe < 0.95`
and inside [0,1]; the same call would previously have been able to exceed 1.

## 5. Limits

- Backfill derives from `timestamp`, which is the pick's issue time, not necessarily the
  fill time. It is the best available field and is labelled per-row via
  `entry_time_source`, so a consumer can filter to native stamps only.
- The 3.1% with no timestamp at all need the producer fixed, not the ingest.
- Portfolio regression uses even accrual; path-accurate version needs intraday data.
