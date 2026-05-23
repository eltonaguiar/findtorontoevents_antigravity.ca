# B26 — TradingAgents End-to-End Smoke Test (2026-05-02)

## What shipped

Added `tests/test_tradingagents_smoke.py` — a five-assertion smoke test for
the full TradingAgents emitter → resolver path, gated on
`TRADINGAGENTS_LIVE_SMOKE=1`.

## Why this matters

B24 (placeholder-text guard) and B25 (identical-metrics warning) both landed
on main, but neither had a live-integration test that exercises the actual
LLM path.  B26 closes that gap: on a developer's machine with a real API key
the suite can validate that the live pipeline is end-to-end correct before
any production flip.

## Assertions

| # | Test | Prereq fixed |
|---|------|--------------|
| 1 | `test_no_placeholder_text` — thesis/rationale ≠ placeholder strings | B24 |
| 2 | `test_at_least_two_distinct_metrics` — ≥2 of 3 picks have distinct (conf, TP, SL) | B25 |
| 3 | `test_debug_raw_env_flag` — `TRADINGAGENTS_DEBUG_RAW=1` surfaces raw LLM response in debug log | B25 |
| 4 | `test_tradingagents_registered_in_resolver` — tradingagents in SYSTEM_SOURCES | B23 (verified ✅) |
| 5 | `test_resolver_fills_entry_price` — entry_price non-None after emit (**xfail**) | blocked — see gap below |

## Documented gap (xfail: test 5)

The emitter deliberately sets `entry_price=None` (comment at
`alpha_engine/tradingagents_emitter.py:216`), expecting the resolver to fill
it via a yfinance price lookup.  That resolver helper
(`_snapshot_tradingagents_entry()`) was described in FreeBuff's 2026-04-30
session log but never landed on main.  Without it, every tradingagents pick
hits the `no_entry` skip path in the resolver (`universal_pick_resolver.py:732-734`)
and its TP/SL/TIME_EXIT outcomes are never tracked.

Fix when ready: add `_TRADINGAGENTS_SYSTEMS` set + `_snapshot_tradingagents_entry()`
to `audit_trail/universal_pick_resolver.py`, mirroring the prediction-market
snapshot pattern at lines 532-545.  Once that lands, remove the `xfail` from
test 5 and promote the test from smoke → unit.

## How to run

```bash
TRADINGAGENTS_EMITTER_ENABLED=1 TRADINGAGENTS_LIVE_SMOKE=1 \
DEEPSEEK_API_KEY=<key> pytest tests/test_tradingagents_smoke.py -v -s
```

Normal CI skips all five tests (no live API keys).

## Files changed

- `tests/test_tradingagents_smoke.py` (new)
- `updates/2026-05-02-b26-tradingagents-smoke.md` (this doc)
- `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` (B25 → ✅, B26 → 🔵)
