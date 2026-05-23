# B6 — Cursor Phase 5: Concept Family UI Filter
**Date:** 2026-05-01 | **PR:** feat/b6-concept-ui-chips-2026-04-30

## What landed

Adds a **Concept Family** filter dropdown (`#f-concept`) to the `/audit`
picks filter bar. Selecting a concept shows only picks whose
`concept_family` field matches — powered by the registry introduced in B4
(PR #566, merged 2026-05-01).

## Changes (5 targeted edits to `audit_dashboard/template.html`)

| Change | Location |
|--------|----------|
| New `<select id="f-concept">` after `f-timeframe` | line ~1025 |
| `concept` key added to filter state collector | line ~6459 |
| Concept guard added to `matchFilter()` | line ~6523 |
| `'f-concept'` added to clear-all forEach | line ~4338 |
| `'f-concept'` added to event-listener forEach | line ~11317 |

## Concept families available

| Option | concept_family value | Typical strategies |
|--------|---------------------|--------------------|
| Breakout/Momentum | `breakout_momentum` | rs-breakout-scout, penny-skyrocket-detector |
| Mean Reversion | `mean_reversion` | RSI2 pullback, support-bounce |
| Trend Following | `trend_following` | EMA golden cross, MTF align |
| Value/Quality | `value_quality` | UEPS long-term value, smart_money_accumulation |
| Sentiment Driven | `sentiment_driven` | Fear/greed contrarian, fear spike |
| Statistical Arb | `statistical_arb` | Pairs trading, cointegration |
| Meme Coin | `meme_coin` | Meme scanner, meme coin scout |
| CTA Systematic | `cta_systematic` | CTA replicator, CFTC COT |
| Standard/Other | `standard` | Default fallback |

## Filter logic

`matchFilter()` now checks:
```javascript
if (f.concept && (pick.concept_family || 'standard') !== f.concept) return false;
```
Picks without `concept_family` fall back to `'standard'` so they appear
under "Standard/Other" rather than being hidden.

## Tests

`tests/test_b6_concept_filter.js` — 8/8 pass:
- All 9 concept options present in `f-concept` select
- `matchFilter` guard line exists in template
- Filter correctly rejects mismatched concept_family
- Filter passes matching concept_family
- Missing field falls back to 'standard'
- Empty filter ("All Concepts") passes all picks
- `f-concept` in clear-all forEach
- `f-concept` in event-listener forEach

## Immediate state

All 37 active picks currently show `concept_family = 'standard'` because
`dashboard_data.json` was last built before B4 (concept_registry) merged.
After the next hourly cron rebuild, picks will get richer concept
classifications (breakout_momentum for rs-breakout-scout, trend_following
for EMA strategies, value_quality for UEPS, etc.) and the filter will
become useful.

## What's deferred (B6-b)

Concept-level WR/PF aggregation panel (showing historical WR per concept
family from closed picks) is deferred to a follow-up PR. It requires
`concept_stats` to be pre-computed by `dashboard_generator.py` and added
to the payload — that's a generator change outside this PR's scope.

## Queue item

B6 from `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` (Order 25,
Cursor Phase 5). Prereq: B4 ✅ (merged 2026-05-01 21:23 UTC).
