# Sports Picks + Prediction Market Overlay (Suggested Fixes)

Date: 2026-04-24

## What was broken

- The live sports picks flow in live-monitor/api/sports_picks.php used sportsbook EV only.
- Prediction market data was available in the repo ecosystem, but not wired into sports picks output.
- The strict Polymarket pipeline in alpha_engine/polymarket_signals.py intentionally rejects sports markets, so sports-specific PM context never reached the sports dashboard.

## What changed

1. Added a new additive bridge script:
- prediction_market_agents/sports_prediction_market_bridge.py

This script:
- pulls active Polymarket markets,
- keeps sports-relevant, high-liquidity markets only,
- applies confidence and volume thresholds,
- writes a compact signals file to:
  - alpha_engine/data/sports_prediction_market_signals.json
  - live-monitor/backfill/sports_prediction_market_signals.json

2. Added safe PM overlay logic into sports API:
- live-monitor/api/sports_picks.php

New behavior in action=today:
- loads sports PM signals if the JSON file exists,
- fuzzy-matches PM market question text to home/away teams,
- attaches PM context to each value bet when matched:
  - prediction_market_source
  - prediction_market_confidence
  - prediction_market_volume_usd
  - prediction_market_hint
- appends a PM confirmation sentence into rating_reasons.
- adds summary.pm_matched_count to response payload.

No existing EV/grade calculation was removed. This is additive context only.

## Why this improves pick quality

- Adds an independent market signal channel without replacing existing sportsbook EV logic.
- Gives a fast confidence/volume check when PM and sportsbook perspectives align.
- Creates the foundation for a future weighted consensus scorer while staying low-risk now.

## How this was verified

- Code review verification:
  - no changes to strict crypto pipeline behavior in alpha_engine/polymarket_signals.py
  - sports_picks.php remains backward compatible when PM JSON file is absent
  - PM fields are additive and non-breaking for current frontend rendering
- Runtime safety:
  - if PM signal files are missing or malformed, sports API continues normal output
  - no DB schema migration required for this initial integration

## Next recommended follow-up

- Add a scheduled step in the sports refresh workflow to run:
  - python3 prediction_market_agents/sports_prediction_market_bridge.py
- Optionally add frontend badge display for PM-confirmed picks in sports-betting.html.
