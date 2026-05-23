# 2026-05-01 — B23: Wire `tradingagents` into resolver SYSTEM_SOURCES

## Summary

PR #544 added the TradingAgents emitter; PR #582 registered
`ueps_picks.json` in the dashboard's `JSON_PICK_SOURCES`. But Cursor's
audit (and v2 of the action plan post-5-AI-review) flagged that
`tradingagents_picks.json` was never registered in the **resolver's**
`SYSTEM_SOURCES`.

Without that entry, the resolver never tracks TP/SL/TIME_EXIT outcomes
for TradingAgents picks — they would render on `/audit` but stay
permanently `OPEN`.

## Empirical verification (2026-05-01 ~21:35 UTC)

```bash
$ grep -n "tradingagents" audit_trail/universal_pick_resolver.py
(no matches before this PR)
```

Confirmed gap. PR #544 acknowledged it would need a follow-up; this is
that follow-up. FreeBuff's session referenced doing this fix on a
separate branch but it never landed on main (likely the same
auto-update overwrite race that affected B28).

## Fix

`audit_trail/universal_pick_resolver.py:182` — append the same entry
that's already in `dashboard_generator.JSON_PICK_SOURCES`:

```python
("tradingagents", "alpha_engine/data/tradingagents_picks.json"),
```

## Tests

`tests/test_b23_tradingagents_resolver_wireup.py` — 2 cases:

1. `tradingagents` is registered in `SYSTEM_SOURCES` with the canonical
   pick file path.
2. The path in resolver's `SYSTEM_SOURCES` matches the path in
   dashboard's `JSON_PICK_SOURCES` (no drift between the two).

Both pass.

## Risk: LOW

- Single-line addition to a list constant.
- Resolver gracefully handles missing files via `_safe_json` (returns
  None → empty list) so registering a source whose file may be missing
  on first runs is safe.
- Mirrors the existing pattern for every other registered source.

## Verification

After merge + next resolver pass:
- TradingAgents picks (NVDA, SOFI from prior runs, plus any new
  emissions) should transition from permanent OPEN to resolved
  (TP_HIT / SL_HIT / TIME_EXIT) based on live price tracking.
- The B26 end-to-end smoke test (when shipped) should observe outcomes
  on tradingagents picks.

## Sequence

This is **Item 2** of action plan v2
(`reports/ACTION_PLAN_2026_05_01_V2.md`). v2 was the post-5-AI-review
revision; the consensus blocker analysis confirmed B23 as a critical
1-line gap. Final reviewer (DeepSeek) approved with SHIP-WITH-MINOR-EDITS.

Next item in v2: **Item 3** B2-redux Asset-Class × Timeframe grid panel
(diagnostic tool for the EQUITY regression below).
