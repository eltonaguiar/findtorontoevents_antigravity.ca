# Manual Sports Picks Verification — Kalshi

**As of:** 2026-04-26T02:54:32Z
**Picks source:** `C:\findtorontoevents_antigravity.ca\data\goldmine\sports_picks.json`
**Kalshi snapshot:** `2026-04-26T02:54:27Z`  (273 markets across 24 series)
**Picks examined:** 6  (target sports = golf, mma, nba, tennis, ufc)

## Summary

- matched: **2**
- no_kalshi_match: **0**
- skipped (off-sport): **4**

## Per-pick detail

| sport | pick | book_prob | kalshi_mid | edge_pp | kalshi_market | match_score |
|---|---|---|---|---|---|---|
| nba | Phoenix Suns Oklahoma City Thunder Phoenix Suns Phoenix Suns | 0.222 | - | - | Game 4: Oklahoma City at Phoenix Winner? | 0.60 |
| nba | Atlanta Hawks New York Knicks New York Knicks New York Knick | 0.535 | - | - | Game 5: Atlanta at New York Winner? | 0.60 |

## Notes

- `book_prob` = pick win-probability from sportsbook odds.
- `kalshi_mid` = (yes_bid + yes_ask) / 2 of the matched Kalshi market.
- `edge_pp` = book_prob − kalshi_mid, in percentage points. Positive = sportsbook is more bullish than Kalshi crowd.
- Match score is fraction of pick-signature tokens overlapping Kalshi market title; >= 0.5 is high confidence.
- This is an opt-in sidecar verifier. It does NOT alter live-monitor pick generation. See `updates/2026-04-26-kalshi-sports-adapter-wiring-plan.md`.
