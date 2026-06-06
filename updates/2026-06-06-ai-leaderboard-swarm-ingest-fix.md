# AI Leaderboard refresh + swarm_picks ingest fix (2026-06-06)

## What was broken

- `/audit/ai_leaderboard.html` showed **25h stale** data (`as_of` 2026-06-05T02:38Z).
- `swarm_picks.json` was **frozen at 38 picks** (newest 2026-05-12) because nightly `promote_tournament_picks.py` crashed on schema validation: tournament submissions use horizon labels (`14d`, `30d`, `equity_default`) not in `swarm_pick_schema.VALID_TIMEFRAMES`.

## What changed

1. **`tools/swarm/promote_tournament_picks.py`** — added `normalize_timeframe()` mapping tournament horizons → valid schema timeframes (`14d`→`1M`, `7d`→`1W`, etc.).
2. Ran `promote_tournament_picks.py` locally → **+151 picks** (store now 189).
3. Ran `python tools/ai_attribution/build_ai_leaderboard.py` → fresh `as_of` 2026-06-06T03:37Z, 43 engines, `pick_date_range.newest` today.
4. Deployed via `python3 tools/deploy_audit_files.py --only ai_leaderboard`.

## Verification

```bash
python3 tools/swarm/promote_tournament_picks.py   # idempotent; 0 new on re-run
python3 tools/ai_attribution/build_ai_leaderboard.py
curl -s 'https://findtorontoevents.ca/audit/data/ai_leaderboard/ai_leaderboard_index.json' | jq '.as_of,.totals,.pick_date_range'
```

Live check: `as_of` 2026-06-06T03:37Z, `totals.picks` 189, `engines` 43.

## Money-ready caveat (unchanged)

Leaderboard still has only **29 resolved** picks — not Tier-2 money-ready (n≥100). New tournament picks need nightly `outcome_resolver_swarm.py` resolution before WR/PF moves. Goal #1 sizing remains on `audit_surface_truth.json` / policy-clean ledger only.