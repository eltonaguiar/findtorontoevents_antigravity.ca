# Draft PR — Asset-Class Signal Contract for `/audit`

## Proposed title

`feat(audit): preserve asset-class signal context for PEAD, carry, COT, ETF rotation, and crypto microstructure`

## Why

The current `/audit` stack is good at ranking rows with **generic** signals
(`trust_score`, `strat_fwd_wr`, `strat_fwd_pf`) but bad at learning
**class-specific** edges because the published contract drops too much
context.

The current repo state proves the gap:

- `audit_trail/dashboard_generator.py` keeps a narrow closed-pick field set and
  mostly preserves generic trust/forward metadata.
- `audit_trail/pick_feature_store.py` persists technical / crypto-ish features,
  but it does not persist the full event/macro/term-structure context needed
  for equity, ETF, FX, and commodity research.
- `alpha_engine/vt_baby_strategies.py` already contains event-driven equity
  wrappers (`vt_earnings_pead`, `vt_edgar_insider_cluster`,
  `vt_sc13d_activist`), but those event features do not survive into the audit
  contract in a normalized way.
- `audit_dashboard/data/ueps_picks.json` can emit `n_long=30`, yet the active
  book still shows `0` `pick_type=long_term_value` rows in the observed
  snapshot. Long-term equity still does not have an audit-grade forward book.

Result:

- We can see that some sleeves work.
- We cannot yet explain **why** they work well enough to scale them safely.

## Goal

Keep the audit payload lightweight while making it class-aware enough to:

1. identify genuine high-conviction setups,
2. mutate only the right parent strategies,
3. avoid expanding broad weak sleeves,
4. finally make long-term equity / PEAD / catalyst work measurable inside the
   same `/audit` framework as crypto and FX.

## Scope

### In scope

- Add a minimal **asset-class signal contract** to the published active/closed
  pick rows.
- Preserve a compact set of `at_issue_*` class-specific fields on closed rows.
- Persist missing event / macro / term-structure inputs into the feature store.
- Upgrade PEAD and long-term equity rows so they can be tracked inside the main
  audit loop.
- Add class-specific high-conviction rules that combine existing
  trust/forward fields with the new class-aware fields.

### Out of scope

- Rebuilding the whole dashboard payload shape.
- Re-running large backtests in this PR.
- Broad strategy proliferation before telemetry is fixed.

## Proposed files

| File | Proposed change |
|---|---|
| `audit_trail/dashboard_generator.py` | Extend `_CLOSED_PICK_KEEP_FIELDS` and the `at_issue_*` snapshot logic to retain a compact class-specific field set. |
| `audit_trail/pick_feature_store.py` | Add side-table / SQLite columns for event-driven equity, FX carry/COT, commodity curve, and ETF breadth fields. |
| `audit_trail/universal_pick_resolver.py` | Preserve the new class-specific fields when rows move from active to resolved. |
| `alpha_engine/vt_baby_strategies.py` | Export PEAD / insider / activist metadata in normalized top-level keys instead of burying everything inside `extra`. |
| `alpha_engine/long_term_pick_contract.py` | Ensure long-term fields survive promotion into the main active/audit path. |
| `tools/asset_class_edge_audit.py` | Use as the read-only verification harness for rollout checks. |
| `tests/*` | Add regression coverage for contract preservation and class-aware gating. |

## Asset-class signal contract

Keep the contract small. The point is not to publish every raw input. The point
is to preserve the 5-10 fields per class that actually explain the edge.

### Shared fields for all classes

These already matter and should remain first-class:

- `trust_score`
- `trust_tier`
- `strat_fwd_wr`
- `strat_fwd_pf`
- `strat_fwd_trades`
- `confidence`
- `risk_reward`
- `source_system`
- `strategy`
- `asset_class`

### Equity / PEAD / long-term value

Add:

- `earn_surprise_pct`
- `earn_surprise_z`
- `revision_momentum_7d`
- `consecutive_beats`
- `days_since_earnings`
- `hours_to_next_earnings`
- `sector_etf`
- `rel_strength_63d`
- `insider_cluster_score`
- `activist_13d_score`

Why:

- This aligns with the repo’s existing PEAD direction and with official SEC
  event sources (`data.sec.gov`, Form 4, Schedule 13D).
- It also fits the actual local winners: `quality-minus-junk`,
  `rs-breakout-scout`, and `post-earnings-rev-scout`.

### ETF

Add:

- `sector_theme`
- `bench_rel_mom_63d`
- `breadth_above_50dma_pct`
- `breadth_above_200dma_pct`
- `vol_regime`
- `corr_cluster`
- `hrp_weight`
- `macro_beta_tag`

Why:

- ETF edge in the current book is narrow and looks sector/flow driven.
- If we do not keep breadth/correlation context, we cannot tell a true rotation
  signal from a random ETF long.

### Forex

Add:

- `carry_diff_bps`
- `real_rate_diff_bps`
- `cftc_net_spec_z`
- `macro_event_proximity_h`
- `session_regime`
- `vol_scale`
- `dxy_beta`

Why:

- Local evidence says `cta_cross_asset_tsmom SHORT` and
  `fx_smart_carry_trade_momentum LONG` are workable.
- FX conviction should be “carry + trend + positioning + regime”, not “pair has
  a score”.

### Commodity / futures

Add:

- `commercial_net_z`
- `managed_money_net_z`
- `curve_slope_bps`
- `roll_yield_bps`
- `inventory_proxy`
- `usd_beta`
- `seasonality_bucket`

Why:

- The current commodity edge is concentrated in
  `cftc_cot_commercial_signal SHORT`.
- Recent kill-switch work improved the sleeve by removing weak sub-classes.
- The next step is not adding more generic commodity momentum. It is preserving
  the COT + curve context of the surviving edge.

### Crypto

Add or consistently preserve:

- `funding_rate_raw`
- `basis_bps`
- `open_interest_delta`
- `liquidation_cluster_score`
- `orderbook_imbalance`
- `btc_rel_strength`
- `vol_regime`

Why:

- These are already close to the right abstraction for crypto and some are
  partly in the feature store already.
- Crypto should be the first class to get a complete contract because the local
  mutation winners already prove the model.

## High-conviction policy changes

Do not replace the existing trust/forward framework. Extend it.

### New rule

High-conviction = shared trust/forward quality **plus** class-specific proof.

Examples:

- `EQUITY`: require strong `trust_score` / `strat_fwd_wr` and at least one of:
  PEAD surprise/revision alignment, QMJ profile, sector-relative strength, or
  insider/activist event support.
- `ETF`: require sector/breadth confirmation, not just score.
- `FOREX`: require carry or macro differential confirmation plus acceptable COT
  / session / volatility context.
- `COMMODITY`: require COT or curve confirmation; block generic commodity
  longs that do not have class-specific backing.
- `CRYPTO`: require microstructure / funding / OI confirmation for mutated
  breakout and mean-reversion variants.

### What should not drive HC by itself

- Raw `confidence`

The local audit snapshot shows `confidence` is inconsistent across classes.
`trust_score`, `strat_fwd_wr`, and `strat_fwd_pf` are much better filters.

## Mutation lanes to expand

Mutate only around strategies that already show real edge in the audit data.

### Equity mutation lanes

- `rs-breakout-scout` × `quality-minus-junk`
- `post-earnings-rev-scout` × PEAD surprise z-score
- `post-earnings-rev-scout` × insider cluster
- `quality-minus-junk` × sector-relative strength

### ETF mutation lanes

- `intermarket-flow-scout` × breadth regime
- sector rotation × VIX regime
- QMJ-style ETF basket × breadth / correlation filter

### Forex mutation lanes

- `cta_cross_asset_tsmom SHORT` × carry differential
- `fx_smart_carry_trade_momentum LONG` × volatility scaling
- `forex_rsi2_mean_reversion` × session filter / macro blackout window

### Commodity mutation lanes

- `cftc_cot_commercial_signal` × curve slope
- copper/platinum-only variants × USD filter
- commercial-vs-managed-money spread variants

### Crypto mutation lanes

- `atr_percentile_gate` × funding / OI confirmation
- `MeanReversionBB SHORT` × liquidation / order-book confirmation
- `claude_ml_moderate_mut` × BTC-relative-strength regime
- mutate around proven winners, not around broad `quan_engine`-style weak
  sleeves

## Mutation lanes to quarantine

Do not expand these until the contract is fixed and/or performance improves:

- broad commodity momentum clones
- broad ETF exposure without sector/breadth context
- PEAD clones without revision/event fields
- any class where the parent strategy does not survive trust/forward filters

## Rollout plan

### Phase 1 — telemetry only

- Ship the new class-specific fields into active + closed rows.
- No gating change yet.
- Use shadow reporting to confirm the fields populate as expected.

### Phase 2 — dashboard visibility

- Add the new fields to row detail / debug tooltips only.
- Confirm they survive resolution.

### Phase 3 — high-conviction gating

- Add class-aware HC rules behind env flags.
- Compare against the current strict HC feed with `tools/asset_class_edge_audit.py`.

### Phase 4 — mutation promotion

- Only after telemetry stabilizes, promote class-specific mutation families.
- Require minimum sample floors before default-on promotion.

## Verification plan

### Code-level

- Unit tests for contract preservation through:
  - active ingest
  - closed slim-down
  - universal resolution
- Regression tests for PEAD / UEPS / long-term value rows

### Data-level

- `python tools/asset_class_edge_audit.py`
- confirm:
  - `ueps_picks.json` longs can be seen as `long_term_value` rows in active
  - PEAD-like rows appear in active as well as closed
  - new fields survive onto `recent_closed`

### Promotion-level

Only promote a new class-aware gate if:

- sample size is meaningful,
- high bucket PF is materially above low bucket PF,
- the new class-specific field adds information beyond trust/forward alone.

## Expected outcome

This PR should not be judged by “number of strategies added”.

It should be judged by whether `/audit` finally becomes capable of answering:

- which **equity** setups are true PEAD / QMJ / catalyst edges,
- which **ETF** rows are real rotation signals,
- which **FX** rows are carry/tsmom/COT aligned,
- which **commodity** rows survive curve + positioning scrutiny,
- which **crypto** mutations deserve real promotion.

If that contract is fixed, the next wave of baby-strategy and DNA-mutation work
will be grounded in evidence instead of guesswork.
