# Strategy crosswalk — closing the trial-count bracket

- crosswalk generated: `2026-11-21T22:57:43.575373Z`
- pf_registry generated: `2026-11-21T11:05:48Z`
- policy-clean rows analysed: 23732

## Reproduction check

- shipped registry cells: **695**
- cells this recount rebuilds: **695**
- exact match: **True** (missing 0, extra 0)

## Root cause

`tools/build_pf_registry.py::_strategy` keys each row as
`source_system or strategy`, i.e. by **emission engine** when the pick has one.
audit3 keys on the pick's own `strategy` string. The two artifacts are two
**granularities** of the same picks, not two taxonomies — so comparing their
label sets 1:1 manufactures drift that is really collapsing.

## Resolved counts

| quantity | count |
|---|---|
| registry cells, engine grain (`n_engine`) | 695 |
| distinct (class, strategy) in the policy-clean book | 690 |
| unnamed (class, label) buckets with no strategy string | 6 |
| **CLOSED trial count (named strategies + unnamed buckets)** | **696** |
| audit3 distinct pairs | 342 |
| union at strategy grain (sensitivity) | 897 |

### How audit3's 342 pairs classify against the book

| bucket | count | meaning |
|---|---|---|
| DIRECT | 124 | registry cell under its own name |
| COLLAPSED | 13 | in the book, filed under another label |
| ABSENT | 205 | nowhere in the policy-clean book |

### Why the absent pairs are absent

| cause | count | meaning |
|---|---|---|
| policy_excluded | 2 | ingested and closed, then dropped by `_is_policy_excluded` |
| dropped_pre_aggregation | 18 | reached the loader, failed dedup / spot-flicker |
| not_in_inputs | 185 | no loaded input row carries this strategy |

## Per class

| class | engine grain | strategy grain | **closed** |
|---|---|---|---|
| BOND | 2 | 2 | **2** |
| CHEAP_STOCKS | 1 | 1 | **1** |
| COMMODITY | 9 | 9 | **9** |
| CRYPTO | 629 | 625 | **627** |
| EQUITY | 19 | 17 | **18** |
| ETF | 12 | 15 | **15** |
| FOREX | 18 | 14 | **16** |
| FUTURES | 3 | 6 | **6** |
| MEME | 1 | 0 | **1** |
| PENNY_STOCK | 1 | 1 | **1** |

## Umbrella labels that collapse strategies

11 labels cover more than one strategy string.
Largest fan-outs:

| class | label | strategies under it |
|---|---|---|
| CRYPTO | `copy_trader_clones` | 7 |
| FUTURES | `multi_asset_scanner` | 4 |
| CRYPTO | `ml_strategy_reviver_inverse` | 3 |
| EQUITY | `regime_terminal` | 3 |
| ETF | `etf_all_strategies` | 3 |
| COMMODITY | `feature_signals` | 2 |
| CRYPTO | `mega_mutation` | 2 |
| ETF | `institutional_picks_engine` | 2 |
| FOREX | `forex_copy_trader` | 2 |
| FOREX | `multi_asset_copytrader` | 2 |
| FOREX | `multi_asset_scanner` | 2 |

## Verification

- Rows come from `build_pf_registry.load_rows()` + `classify_rows()` and the same
  `_is_policy_excluded` filter the artifact uses, so this explains the shipped
  695 rather than a parallel recount.
- Unattributable policy-clean rows: **0**.
- Rows with no strategy string (cannot be attributed to a trial): 4804.

