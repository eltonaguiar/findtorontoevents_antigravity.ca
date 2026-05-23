# inverse_wrapper — Design Note

**Date:** 2026-04-14
**Status:** Approved (fast-path)
**Source:** Cross-reference from [TRADING_INSIGHTS_FROM_AI4TRADE.md](../../TRADING_INSIGHTS_FROM_AI4TRADE.md) §6a, Mercury review endorsement, live `dashboard_data.json` worst-strategy data.

## What this is

A generic pure-function **pick transformer** that consumes picks from a named source strategy and emits inverted copies (direction flipped, TP/SL swapped) tagged under a new strategy name. First caller is `quan_engine` (2.8% WR on n=36), but the module is reusable for `Value + Quality` (7.8% WR on n=51) and any future inversion candidate.

## Why not a blind whole-strategy flip

Reading [alpha_engine/elite_scorer.py:497-502](../../../alpha_engine/elite_scorer.py#L497-L502) and [alpha_engine/elite_scorer.py:63](../../../alpha_engine/elite_scorer.py#L63) reveals prior knowledge:

1. **Confidence bands are inverted for quan_engine.** 0.50–0.59 conf = 36.7% WR (best), 0.60–0.69 conf = 19.8% WR (worst). Inverting only the high-confidence band is a surgical fix.
2. **Edge is concentrated in 3 symbols.** `TAOUSDT`, `HYPEUSDT`, `TRXUSDT` — these are where quan_engine actually works. Inverting picks on these symbols would flip profit into loss.

A blind whole-strategy flip ignores this and would produce a strictly worse result than the selective version.

## Architecture

```python
inverse_wrapper.transform(
    picks: list[dict],
    source_strategy: str,
    new_strategy_name: str,
    only_if_confidence_in: tuple[float, float] | None = None,
    exclude_symbols: set[str] | None = None,
) -> list[dict]
```

Pure function. No I/O. Returns a new list of inverted pick dicts. Each input pick that passes the filters gets:
- `direction` flipped (LONG ↔ SHORT, BUY ↔ SELL)
- `take_profit` and `stop_loss` swapped on the price axis (entry ± same magnitude, opposite side)
- `strategy` set to `new_strategy_name`
- `source_system` set to `inverse_<source_strategy>`
- `confidence` unchanged
- `extra.inverted_from` = original strategy + original direction (for audit)

Picks that fail the filters (wrong conf band, excluded symbol, unknown direction) are **dropped**, not passed through. The wrapper is selective: only the part of the source strategy we believe is salvageable gets inverted.

## First caller config (`quan_engine` inversion)

```python
transform(
    picks=quan_engine_picks,
    source_strategy="quan_engine",
    new_strategy_name="quan_engine_inverse",
    only_if_confidence_in=(0.60, 0.69),
    exclude_symbols={"TAOUSDT", "HYPEUSDT", "TRXUSDT"},
)
```

This inverts *only* the 0.60–0.69 confidence band on symbols outside quan_engine's known edge set. Targets the 19.8% WR subset, which should flip to ~80% if the band's edge is purely sign-inverted.

## Second caller (`Value + Quality` inversion)

Initial config (no prior band/symbol analysis yet):

```python
transform(
    picks=value_quality_picks,
    source_strategy="Value + Quality",
    new_strategy_name="value_quality_inverse",
    only_if_confidence_in=None,  # invert the whole thing first, refine later
    exclude_symbols=None,
)
```

Forward-validate. If WR flips from 7.8% to ~92%, promote. If not, drill into the confidence and symbol distributions before refining.

## What this does NOT do

- **No pipeline wiring.** The transform function lives in `baby_strategies/inverse_wrapper.py` and is not imported by the scanner. Activation is a manual step: a user adds a small adapter in `antigravity_strategies.py` (or equivalent) that calls `transform` with live quan_engine picks and feeds the output into the pick stream.
- **No historical backfill.** We do not rerun historical quan_engine trades through the inverter and claim a backtest. Today's session has made it clear that in-sample backtest claims don't survive scrutiny. Forward-validate from activation forward.
- **No trade execution.** This module only produces pick dicts. The existing pick pipeline handles validation, forward tracking, and TP/SL fills.
- **No default whole-strategy flip.** Every caller must explicitly specify filters or explicitly set them to None. Making the blind case require an explicit `None` forces the caller to think about it.

## Files

| File | Est. lines | Role |
|---|---|---|
| `baby_strategies/inverse_wrapper.py` | ~160 | Transform function + small helper for price-axis flipping |
| `baby_strategies/inverse_wrapper.meta.json` | ~50 | Attribution + two configured callers (quan_engine, value_quality) |
| `tests/test_inverse_wrapper.py` | ~220 | Unit tests: direction flip, TP/SL swap, conf band filter, symbol exclusion, unknown direction rejection, round-trip idempotence |

## Success criteria

- `py_compile` clean.
- All unit tests green covering: (1) LONG→SHORT flip, (2) BUY→SELL flip, (3) TP/SL swap math, (4) confidence band filter inclusive/exclusive boundaries, (5) symbol exclusion, (6) NEUTRAL / unknown direction dropped, (7) idempotence property (`transform(transform(picks, ...flipped_config...))` returns original picks), (8) `extra.inverted_from` audit trail populated.
- Zero modifications to `scanner.py`, `config.py`, `antigravity_strategies.py`.
- The module is reusable for `Value + Quality` by changing one string.

## Risk

- **The inversion hypothesis may not hold.** If quan_engine's losses are driven by slippage, timing, or market-impact rather than wrong-direction signal, flipping will not produce the expected 80% WR. Forward-validation will tell us in 2–4 weeks.
- **Symbol exclusion list may be stale.** Edge-concentration data in `elite_scorer.py:63` is frozen at commit time; if quan_engine's edge shifts symbols, the exclusion list will be wrong. Mitigation: the exclusion list is a constructor argument, not hardcoded in the transform function.
- **Tagging collision.** A future scanner run must not confuse `quan_engine_inverse` with `quan_engine` itself. The transform sets both `strategy` and `source_system` to distinct values, and downstream aggregators key on `strategy` not symbol, so collisions are impossible unless a consumer re-tags.
