# Manual Sports Picks Verification — Kalshi

**As of:** 2026-11-18T02:52:05Z
**Picks source:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/data/goldmine/sports_picks.json`
**Kalshi snapshot:** `2026-11-18T02:52:05Z`  (598 markets across 24 series)
**Picks examined:** 1  (target sports = golf, mma, nba, tennis, ufc)

## Summary

- matched: **0**
- no_kalshi_match: **0**
- skipped (off-sport): **1**

## Per-pick detail

| sport | pick | book_prob | kalshi_mid | edge_pp | kalshi_market | match_score |
|---|---|---|---|---|---|---|

## Notes

- `book_prob` = pick win-probability from sportsbook odds.
- `kalshi_mid` = (yes_bid + yes_ask) / 2 of the matched Kalshi market.
- `edge_pp` = book_prob − kalshi_mid, in percentage points. Positive = sportsbook is more bullish than Kalshi crowd.
- Match score is fraction of pick-signature tokens overlapping Kalshi market title; >= 0.5 is high confidence.
- This is an opt-in sidecar verifier. It does NOT alter live-monitor pick generation. See `updates/2026-04-26-kalshi-sports-adapter-wiring-plan.md`.
