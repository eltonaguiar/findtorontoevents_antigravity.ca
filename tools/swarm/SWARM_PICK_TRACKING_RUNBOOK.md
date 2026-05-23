# Swarm Pick Tracking — Operator Runbook

Short reference for running the swarm-pick tracking pipeline. Design lives in `docs/SWARM_PICK_TRACKING_DESIGN.md`; this is the day-to-day cheat sheet.

## Pipeline at a glance

```
[place picks on TV]  →  swarm_picks.json  →  outcome_resolver  →  weekly_review  →  swarm_leaderboard.json
                                                    ↓                       ↓
                                              outcome filled           pattern_miner  →  swarm_pattern_tags.json
                                                                          ↓
                                                                  /audit panel (template.html)
```

## Files in play

- `audit_dashboard/data/swarm_picks.json` — durable pick store (array, one record per pick)
- `audit_dashboard/data/swarm_leaderboard.json` — per-tier/per-class/per-persona/per-underlying-model rollup
- `audit_dashboard/data/swarm_pattern_tags.json` — winning/losing/sparse `(tier×class×regime)` cells
- `reports/swarm_review/YYYY_WW.md` — rolling 7d review
- `reports/swarm_review/all-time.md` — all-time review
- `reports/swarm_review/patterns_<date>.md` — pattern miner report

## Scripts

| Script | Purpose | Run cadence |
|--------|---------|-------------|
| `tools/swarm/swarm_pick_schema.py` | Validator + tier-derivation helpers | On-demand (`python tools/swarm/swarm_pick_schema.py`) |
| `tools/swarm/backfill_sessions.py` | One-shot backfill of session .MDs into store | Once per new session (manual edit) |
| `tools/swarm/outcome_resolver_swarm.py` | Resolve open picks via yfinance + CoinGecko | Nightly via GHA (`.github/workflows/swarm-pick-review.yml`) |
| `tools/swarm/weekly_review.py` | Generate per-tier + per-model leaderboard | Daily via GHA |
| `tools/swarm/pattern_miner.py` | Mine winning/losing `(tier×class×regime)` cells | Daily via GHA |

## Manual local run (Windows)

```bash
# Validate current store
python tools/swarm/swarm_pick_schema.py

# Resolve any picks that hit TP/SL since last run
python tools/swarm/outcome_resolver_swarm.py --dry-run    # preview
python tools/swarm/outcome_resolver_swarm.py              # commit

# Rolling 7d review
python tools/swarm/weekly_review.py --days 7

# All-time review (overwrites all-time.md)
python tools/swarm/weekly_review.py --all

# Pattern miner with n>=5 floor
python tools/swarm/pattern_miner.py --min-n 5
```

## Adding a new pick (from a placed TV trade)

Hand-edit `tools/swarm/backfill_sessions.py` (currently the only writer) — add a new `make_pick(...)` call inside `round1_picks()` / `round2_picks()` or a new `roundN_picks()` function, then **delete `audit_dashboard/data/swarm_picks.json`** and rerun:

```bash
rm audit_dashboard/data/swarm_picks.json
python tools/swarm/backfill_sessions.py
python tools/swarm/swarm_pick_schema.py    # validate
```

> The backfill script refuses to overwrite an existing store; this is intentional so a stale rerun doesn't wipe live outcomes. The "delete and rerun" pattern is OK because the resolver will re-fill outcomes from yfinance on the next nightly cron.

Better long-term path: build an `append_pick` helper that hot-merges into the existing store while preserving outcomes (Section F task 7 in the design doc).

## Adding a new persona

Edit `tools/swarm/backfill_sessions.py::PERSONA_ROLES` dict — `name -> role-summary` mapping. Both fields must be present on every vote per the schema.

Required vote fields (all mandatory, validator rejects missing):
- `name` (persona name, e.g., `MOMENTUM_TECH`)
- `role` (short description)
- `underlying_model` (e.g., `claude-opus-4-7`, `qwen3-coder-480b`, `kimi-k2.5`) — **Q3 decided YES on 2026-05-12**, this distinguishes persona quality from model quality
- `vote` (`LONG` / `SHORT` / `SKIP`)
- `confidence_0_100` (int 0-100)
- `timeframe` (`5m`, `15m`, `30m`, `1H`, `4H`, `1D`, `1W`, `1M`, `3M`, `6M`, `1Y`)
- `justification_summary` (one-line reasoning)

## Adding a new symbol (resolver)

Edit `tools/swarm/outcome_resolver_swarm.py::SYMBOL_MAP` (yfinance) or `COINGECKO_MAP` (CG fallback). For stocks/ETFs that yfinance handles via exchange-prefix strip, no mapping needed.

## GitHub Actions cron

`.github/workflows/swarm-pick-review.yml` runs `0 3 * * *` UTC (= 23:00 EST / 22:00 EDT). Steps:
1. Resolve open picks
2. Weekly review (7d window)
3. All-time review
4. Pattern miner
5. Validate store
6. Commit + push only if data changed

Manual trigger: `gh workflow run swarm-pick-review.yml`.

## Dashboard panel

Surfaced on `/audit` under "Swarm Pick Tracking". Reads `swarm_picks_data` payload key emitted by `audit_trail/dashboard_generator.py::_load_swarm_picks_data()`. Contract:
- `summary.{n_total, n_resolved, n_open, win_rate_pct, profit_factor}`
- `leaderboard.{by_tier, by_asset_class, by_persona, by_underlying_model}`
- `picks[]` (full pick records)
- `patterns.{winning, losing, sparse}`

## Known gotchas

- **CoinGecko rate-limit (429):** free tier is ~30 req/min. Resolver's CG fallback returns `None` on 429; pick stays open until next cron. Safe — no false fills.
- **yfinance delisted-ticker spam:** `$APT-USD: possibly delisted` printed to stderr is yfinance noise, not a real error. Resolver handles it.
- **Schema strictness:** side-sanity is enforced on write (`LONG: tp>entry>sl`, `SHORT: sl>entry>tp`). A pick with inverted TP/SL gets rejected at the validator level — caller must fix the pick, not bypass the validator.
- **Hand-mapped tiers:** the current backfill assigns consensus_tier manually (`unanimous`, `strong`, `moderate`, `single`, `control`). Once `consensus_score` is computed live from per-model votes, `derive_consensus_tier(score, n_voted)` should be used instead of hard-coded strings.

## Next-up backlog

See `docs/SWARM_PICK_TRACKING_DESIGN.md` Section F. Highest-leverage remaining tasks:
- Task 7: `append_pick()` helper for live writes (currently only backfill writer exists)
- Task 8: integrate live consensus-tier derivation into pick-placement flow (no more manual tier strings)
- Task 9: `pattern_tags` auto-population from miner (currently `[]` on every pick — miner output is global, not per-pick)
- Task 10: cross-link `swarm_picks.json` to the existing `audit_trail/dashboard_generator.py` outcome resolver (`alpha_engine/outcome_resolver.py`) so a single resolver can handle both classic picks + swarm picks
