# AI Tournament Data Directory

This directory stores all AI model pick submissions and leaderboard data for the AI Prediction Tournament.

## Files

- `picks_<date>.json` — daily snapshot of all picks (open + resolved)
- `picks_latest.json` — symlink/copy of most recent picks snapshot (served to audit page)
- `leaderboard.json` — current leaderboard rankings (updated daily by GHA)
- `submissions/<model_id>_picks_<timestamp>.json` — original model submissions (immutable, append-only)
- `price_log/<date>.json` — daily price pulls with SHA-256 hashes (audit trail)

## Pick schema

See `docs/AI_PREDICTION_TOURNAMENT_METHODOLOGY.md` §6.2 for the full schema.

## Data integrity

All price data is hashed and stored in `price_log/`. Each entry contains:
- timestamp (UTC ISO)
- symbol
- price
- source (provider that delivered this price)
- sha256 hash of the full response

This creates an immutable audit trail for dispute resolution.
