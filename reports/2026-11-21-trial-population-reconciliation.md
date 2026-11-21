# Trial-population reconciliation — audit3 cells vs pf_registry strategies

- audit3 ledger generated: `2026-11-21T00:45:30.275459+00:00`
- pf_registry generated: `2026-11-21T11:05:48Z`
- Grain: `asset_class x strategy`
- **Primary N:** distinct (asset_class, strategy) in pf_registry.by_asset_class_strategy_policy_clean_net -- the book the class verdict reads
- **Upper bound:** distinct (asset_class, strategy) in audit3 cells U pf_registry policy-clean cells -- adopt if a crosswalk proves the audit3-only labels are distinct strategies

## Finding

NOT a filter: the artifacts use different strategy taxonomies and disagree in both directions, so neither is the trial count on its own and N is bracketed [primary, union]

| quantity | count |
|---|---|
| audit3 `cells` rows (direction × namespace split) | 367 |
| audit3 distinct (class, strategy) | 342 |
| pf_registry policy-clean (class, strategy) | 695 |
| pf_registry (class, strategy, symbol) | 745 |
| shared | 124 |
| **audit3-only** (pf does not carry) | **218** |
| **pf-only** (audit3 does not score) | **571** |
| union (upper bound) | 913 |

The disagreement is mutual, so it is not a filter setting: audit3 rows collapse 1.07x onto pairs (direction/namespace are subdivisions), and the two label sets overlap on only 124 of 913 pairs (13.6%).

## Per class

| class | N primary | N union | pf | audit3 | audit3/pf | shared | audit3-only |
|---|---|---|---|---|---|---|---|
| BOND | **2** | 13 | 2 | 12 | 600.0% | 1 | 11 |
| CHEAP_STOCKS | **1** | 1 | 1 | 0 | 0.0% | 0 | 0 |
| COMMODITY | **9** | 11 | 9 | 6 | 66.7% | 4 | 2 |
| CRYPTO | **629** | 737 | 629 | 210 | 33.4% | 102 | 108 |
| EQUITY | **19** | 67 | 19 | 54 | 284.2% | 6 | 48 |
| ETF | **12** | 49 | 12 | 40 | 333.3% | 3 | 37 |
| FOREX | **18** | 30 | 18 | 19 | 105.6% | 7 | 12 |
| FUTURES | **3** | 3 | 3 | 1 | 33.3% | 1 | 0 |
| MEME | **1** | 1 | 1 | 0 | 0.0% | 0 | 0 |
| PENNY_STOCK | **1** | 1 | 1 | 0 | 0.0% | 0 | 0 |

## Subset test

FAIL — 218 audit3 pairs are absent from pf_registry. The two artifacts are two taxonomies, not two filter settings. Sample of pairs only audit3 scored:

- `BOND` / `adx-trend-scout`
- `BOND` / `betting-against-beta`
- `BOND` / `ema_stack_momentum`
- `BOND` / `mtf-align-scout`
- `BOND` / `pairs-trading`
- `BOND` / `rs-breakout-scout`
- `BOND` / `rsi-divergence-scout`
- `BOND` / `strong consensus (alpha_engine, kimi)`
- `BOND` / `volume-anomaly-scout`
- `BOND` / `vwap-reclaim-scout`
- `BOND` / `vwap-reversion-scout`
- `COMMODITY` / `commodity_term_cot`

## Why not the other available grains

- `by_asset_class_strategy_symbol` (745 cells): the scanner selects at strategy level; one strategy firing on 40 symbols is one decision examined, not 40. Using it triple-counts and is not comparable to the strategy rows the verdict reads.
- audit3 `cells`: it is not a filter of the registry book and it is not a superset of it either. It cannot supply N alone.
- Neither count alone. The honest statement is a bracket: N_primary 695 to N_union 913. Using the primary is the internally consistent choice because the deflated statistic is computed from that same book; the union is the conservative bound to adopt once the crosswalk lands.

Raising N can only kill a class, never save one — DSR is monotone decreasing in N.

**Open fix:** Build a strategy-name crosswalk (at_raw_picks.source_system <-> pipeline `strategy` string). Until it exists the two artifacts cannot be compared and N stays bracketed.
