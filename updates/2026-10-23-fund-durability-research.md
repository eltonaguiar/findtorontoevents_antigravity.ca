# Fund durability research and zero-expense ETF comparison

## What was missing or misleading

Recent discussions conflated historical active-fund winners with a repeatable way to select future winners, and commission-free trades with funds that actually charge no ongoing expense. A meaningful comparison also needs daily unrealized losses, equal dates/currencies, honest costs and inception-aware histories.

The new research harness initially omitted cash days if an annual schedule was skipped. Independent review identified that latent omission as inconsistent with Sharpe/Sortino annualization. None of the frozen nine trials had a missing year, but the implementation now explicitly retains benchmark-calendar cash days at zero return.

## Changes

- Added the opt-in `tools/fund_durability.py` fetch/run/compare CLI and frozen H-141 protocol.
- Evaluated 95 declared funds/ETFs and nine fixed annual selection variants, with daily marked-to-market drawdown, drifting basket weights, next-close entry, 10/20 bps per-side costs, matched benchmarks, 500 random-selection controls and 2,000 paired block bootstrap replicates.
- Added a separate descriptive comparison of BKLC/BKAG after confirming 0.00% gross and net expenses on issuer pages; the two products were not inserted into the preregistered selection universe.
- Added the [plain-English research report](../reports/fund_durability_2026-10-23.md), [all trial summaries and manifests](../reports/fund_durability_results_2026-10-23.json), and [matched fee comparisons](../reports/fund_fee_comparisons_2026-10-23.json).
- No production caller, dashboard change, strategy demotion, order, merge or FTP deployment. No unrelated harness thresholds changed.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_fund_durability.py -q -p no:cacheprovider`: **12 passed**.
- `python3 tools/fund_durability.py --help`: passed with direct-script imports.
- Full 95-series/nine-trial calculation repeated from identical hashed caches: byte-identical results.
- After the cash-day fix, the full result remained byte-identical to the original frozen run; SHA256 `ca3e56dc680f1802c8a6b33299ad32ea5718168cb986c79390f441d9a9528204`.
- All four fee-comparison groups exercised through the direct CLI, including real common-date and currency checks.
- Unit coverage includes 80% unrealized drawdown, future-blind ranking, drifting rather than daily-reset weights, both-side fees, missing prices, deterministic block bootstrap, low-volatility direction, inception matching, duplicate/currency rejection, skipped-year cash, shared-date fee stitching and subprocess CLI output.
- Independent reviewer traced annual execution, basket accounting, stitching, benchmarks, random controls and bootstrap; the identified cash-gap issue was fixed with a regression.
- Full repository test suite not run. The existing unrelated pandas `freq="ME"` collection failure from previous dashboard CI was not changed or bypassed.

## Interpretation and wiring plan

Some active funds historically beat SPY; none met the full frozen descriptive screen, and the nine selection rules did not establish durable selection skill. Legacy live-pick admissibility remains UNTESTED because annual observations do not provide enough populated 14-day windows; this is not a genuine strategy kill.

The research CLI is intentionally opt-in. No production wiring is planned in this PR. A future, separately approved dashboard integration would use `audit_trail/dashboard_generator.py` to display an explicitly historical research sidecar only after point-in-time fund membership, purchase eligibility, loads and prospective evidence are verified. It must not change `calculate_smart_score` or active-pick gates based on these survivor results.
