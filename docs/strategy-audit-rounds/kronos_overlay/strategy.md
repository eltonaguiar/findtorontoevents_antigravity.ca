# Kronos Foundation-Model Overlay

**Asset Class:** MULTI (any class with OHLCV history >= 16 bars)
**Type:** Sidecar / confidence multiplier (NOT a stand-alone strategy)
**Status:** opt-in, NOT wired to production pick generation

## What It Is

A confidence-multiplier sidecar built on top of [Kronos](https://github.com/shiyu-coder/Kronos)
(MIT, Shi Yu et al.), a decoder-only transformer foundation model pre-trained
on OHLCV data across 45+ exchanges. The model ships in four sizes:

| Variant       | Params  |
|---------------|---------|
| Kronos-mini   |   4.1M  |
| Kronos-small  |  24.7M  |
| Kronos-base   | 102.3M  |
| Kronos-large  | 499.2M  |

This repo does NOT bake any weights in. Operators who want the overlay
hot must `pip install torch kronos` themselves; otherwise the sidecar
no-ops with `multiplier = 1.0`.

## Hypothesis

Existing pick sources (technical strategies, copy-trader cohorts,
sentiment scrapers, polymarket vol filter, etc.) produce direction +
confidence. A foundation model trained on cross-market OHLCV likely
contains a directional prior orthogonal to those signals. Aligning
direction with Kronos forecast should:

1. **Boost confidence on agreement** (1.1x default, 1.2x on |Δ|>2%).
2. **Dampen confidence on disagreement** (0.8x default, 0.6x on |Δ|>2%).
3. **Pass through neutral forecasts** unchanged (1.0x).

Net expected effect at the portfolio level: tighter dispersion of
realized PnL around the picks Kronos agrees with, and reduced exposure
to picks the model directly contradicts.

## Architecture

```
existing pick generators
        │
        ▼
  feed_hygiene.py  ──►  polymarket_vol_filter v2  ──►  [WIRE-UP TARGET]
                                                              │
                                                              ▼
                                                  kronos_overlay_picks()
                                                              │
                                                              ▼
                                              score_pick / smart_picks_engine
```

Wire-up is gated on:

- `KRONOS_OVERLAY_ENABLED=1` env (default off)
- A forward-validated tier bump documented in this folder's
  `performance-report.json`

Until both gates are satisfied the module exists only as a sidecar
runnable from `__main__` or unit tests.

## Multiplier Table

| Pick direction vs Kronos | Predicted |Δ| | Multiplier |
|--------------------------|--------------|------------|
| AGREE                    | > 2%         | **1.2**    |
| AGREE                    | <= 2%        | 1.1        |
| forecast NEUTRAL         | n/a          | 1.0        |
| DISAGREE                 | <= 2%        | 0.8        |
| DISAGREE                 | > 2%         | **0.6**    |
| pick has no direction    | n/a          | 1.0        |
| Kronos UNAVAILABLE       | n/a          | 1.0        |

## Rollback

Two env-vars provide instant kill / shadow-eval respectively:

- `KRONOS_OVERLAY_DISABLED=1` -- skip overlay entirely
- `KRONOS_OVERLAY_DRY_RUN=1`  -- compute scores + stamp `_kronos_overlay`,
                                  but DO NOT mutate `pick["confidence"]`

## References

- Repo: https://github.com/shiyu-coder/Kronos
- License: MIT
- Pipeline call site (planned): `alpha_engine/feed_hygiene.py`
- Implementation: `alpha_engine/kronos_overlay.py`
- Tests: `tests/test_kronos_overlay.py`
