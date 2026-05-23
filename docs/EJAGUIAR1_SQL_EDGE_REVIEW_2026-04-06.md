# ejaguiar1_stocks SQL Extract Review

Source reviewed: `C:\Users\zerou\Downloads\ejaguiar1_stocks_apr62026_extract.sql`

## Scope

This is a large MySQL dump with several generations of the picks system in one file:

- `alpha_*` tables: upstream equity-style research and factor-pick generation
- `at_*` tables: live aggregation, consensus, outcomes, and strategy tracking
- `backtest_*` / `bt_*` tables: offline test artifacts

The important distinction is that the dump contains both narrative algorithm definitions and realized trading evidence. They do not align cleanly.

## What Looks Real vs What Looks Promotional

### High-confidence operational layer

These tables look like the real execution and scoring layer:

- `at_raw_picks`
- `at_consensus_picks`
- `at_signal_outcomes`
- `at_strategy_stats`
- `at_strategy_symbol_performance`

These are the tables to trust for scoring and routing decisions.

### Lower-confidence narrative layer

These tables look more like idea generation / marketing / upstream ranking:

- `algorithms`
- `alpha_picks`
- `algorithm_performance`
- `algorithm_rolling_perf`

Examples of narrative vs reality mismatch:

- `algorithms` describes `Blue Chip Growth`, `ETF Masters`, `13F Hedge Fund Clone`, and `Alpha Factor Composite` as robust alpha ideas.
- `algorithm_performance` shows very poor realized snapshots:
  - `Blue Chip Growth`: 298 trades, 7.05% WR, `-6.4194%` avg return
  - `ETF Masters`: 349 trades, 6.02% WR, `-5.8657%` avg return
  - `Alpha Factor Composite`: 313 trades, 4.15% WR, `-8.9299%` avg return
  - `13F Hedge Fund Clone`: 153 trades, 29.41% WR, `-2.8388%` avg return

Conclusion: descriptive text in the DB is not evidence. The system needs to score from realized outcomes, not from algorithm stories.

## Main Structural Problems

### 1. Multiple incompatible truth layers

`alpha_picks` uses a clean equity recommendation format with:

- `score`
- `conviction`
- static `stop_loss_pct`
- static `take_profit_pct`

But the live system uses `at_raw_picks` / `at_consensus_picks` with:

- source-level `confidence`
- direction
- live TP/SL prices
- consensus tiers
- realized `pnl_pct`

This means a single global score language is probably mixing incompatible meanings:

- equity factor ranks
- crypto signal confidence
- consensus count
- backfilled paper-trade confidence

Recommendation:

- keep separate score families by pipeline:
  - `research_score`
  - `execution_confidence`
  - `consensus_strength`
  - `validated_edge_score`

Do not let `alpha_picks.score` and `at_consensus_picks.confidence` masquerade as the same thing.

### 2. Data-geometry bugs still exist in live-style rows

The dump still contains impossible trade geometry.

Example from `at_raw_picks`:

- `TRXUSDT`, `SHORT`, entry `0.3103`, TP `0.31405088`, SL `0.30879965`

For a short:

- TP should be below entry
- SL should be above entry

This row is inverted.

Recommendation:

- hard-reject any pick where TP/SL direction is inconsistent with trade direction
- do this before scoring, consensus, and audit ingestion
- log these as data-quality failures, not as real trades

### 3. PnL scaling / import normalization problems

There are rows where raw source PnL and stored PnL appear to use different scales.

Example from `at_raw_picks`:

- raw payload PnL: `-0.610755...`
- stored `pnl_pct`: `-61.0755`

That looks like a decimal-vs-percent conversion bug.

Recommendation:

- normalize all imported PnL to one convention at ingest
- add an ingest check:
  - if absolute PnL is `> 100%`, quarantine unless leverage metadata explains it
- store both:
  - `pnl_fraction`
  - `pnl_pct`

### 4. Outcome taxonomy is fragmented

`at_signal_outcomes` uses labels like:

- `WIN`
- `LOSS`
- `TP_HIT`
- `SL_HIT`
- `EXPIRED`
- `OPEN`
- `CLOSED`

`at_raw_picks` / `at_consensus_picks` use:

- `WON`
- `LOST`
- `EXPIRED`
- `CLOSED`
- `OPEN`

This makes aggregation and reliability analysis fragile.

Recommendation:

- standardize outcomes into one canonical enum:
  - `OPEN`
  - `TP_HIT`
  - `SL_HIT`
  - `TIME_EXIT`
  - `MANUAL_EXIT`
  - `INVALID`
- derive any display aliases downstream

### 5. Consensus quality is overstated

`at_consensus_picks` is a useful idea, but several fields reduce its trustworthiness:

- many rows have `system_confidences` all null
- some rows have zeroed `entry_price`, `take_profit`, and `stop_loss`
- `STRONG` and `SUPER` picks still show plenty of immediate losers

This implies consensus is often closer to vote count than calibrated edge.

Recommendation:

- stop rewarding agreement count alone
- require at least one of:
  - validated forward stats
  - non-null source confidence
  - non-zero executable geometry
- downgrade consensus picks with null component confidences
- add a disagreement penalty when sources agree on direction but come from the same strategy family

## Clear Edges Available

### 1. Weight sources by realized live performance, not by descriptions

Best immediate edge:

- route capital toward sources with strong `at_strategy_stats` and `at_strategy_symbol_performance`
- demote or quarantine sources that only look good in `algorithms` text or isolated rolling windows

This is more reliable than inventing new alpha.

### 2. Use symbol-level routing, not just strategy-level routing

`at_strategy_symbol_performance` is one of the most useful tables in the dump.

It supports a better policy:

- strategy good on BTC but bad on DOGE: allow BTC, suppress DOGE
- strategy good on large caps but weak on meme assets: route by symbol or bucket

Recommendation:

- score at `strategy x symbol` first
- fall back to `strategy x asset_class`
- only fall back to global strategy stats if sample is too small

### 3. Recency-weight performance instead of lifetime averages

`algorithm_rolling_perf` shows strong regime drift:

- some algorithms look excellent in short windows
- the same algorithms look terrible in overall snapshots
- many windows have `resolved_picks = 0`, which can still contaminate naive rolling analysis

Recommendation:

- use walk-forward weighting:
  - 50% recent 14-30d
  - 30% recent 60-90d
  - 20% lifetime
- ignore rolling windows with low resolved counts
- add degradation flags:
  - if recent PF collapses below threshold, auto-demote

### 4. Separate research picks from executable picks

`alpha_picks` appears useful for idea sourcing, but it is not a sufficient execution dataset.

Problems:

- static TP/SL templates
- some long-horizon picks use placeholder TP like `999`
- strong-looking factor score does not imply executable trade quality

Recommendation:

- treat `alpha_picks` as candidate generation only
- require live execution overlays before promotion:
  - volatility-aware TP/SL
  - liquidity filter
  - symbol-specific validation
  - regime fit

### 5. Duplicate / repeated exposures need stronger collapse rules

The dump shows repeated SPY / QQQ / BTC rows across multiple runs with near-identical geometry and rationale.

That creates false confidence by counting the same idea multiple times.

Recommendation:

- deduplicate on:
  - symbol
  - direction
  - normalized strategy family
  - time bucket
- consensus should count independent evidence, not repeated restatements

## Specific Scoring Tweaks

### Immediate tweaks

1. Add a hard invalidation layer before scoring

- reject zero-price rows
- reject inverted TP/SL geometry
- reject impossible PnL scaling
- reject rows with null executable fields when the system claims to be trade-ready

2. Split confidence into components

- source confidence
- historical win-rate prior
- symbol fit
- regime fit
- execution-quality score

3. Reduce blind consensus bonuses

- agreement count should help only when sources are independent and executable

4. Penalize placeholder geometry

- examples: zero entry/TP/SL, `999` TP, null SL

5. Promote validated symbol-strategy pairs

- use `at_strategy_symbol_performance` to boost combos with enough sample and PF > 1

## What I Would Build Next

### Priority 1

Create a pre-score validator for all incoming picks:

- geometry validation
- decimal normalization
- asset class normalization
- duplicate collapse
- outcome enum normalization

### Priority 2

Create a real score from live evidence:

`final_score = execution_quality + source_edge + symbol_fit + regime_fit + independent_consensus_bonus - duplication_penalty - stale_penalty`

### Priority 3

Add quarantine states:

- `INVALID_GEOMETRY`
- `INVALID_PNL_SCALE`
- `PLACEHOLDER_TARGETS`
- `DUPLICATE_EXPOSURE`
- `NARRATIVE_ONLY`

## Bottom Line

The biggest edge is not hidden inside the SQL dump as a new secret algorithm. It is in cleaning up how the system decides what is real.

Right now the stack is over-crediting:

- descriptive algorithm narratives
- raw agreement count
- incomplete consensus rows
- mixed confidence semantics

And it is under-crediting:

- live realized performance
- symbol-level edge
- execution-quality validation
- recency and regime drift

If you tighten those four areas, the system should improve before you add any new signal family.
