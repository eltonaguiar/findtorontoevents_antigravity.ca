# Tennis/Golf/UFC Manual Pick Verification vs Polymarket

**Date:** 2026-04-26
**Branch:** `feature/sports-betting-edge` (PR #397)
**Author:** Claude Opus 4.7

## Problem

The sports-betting page now ships curated UFC, Tennis, and Golf picks (added
this PR by a peer agent — see `live-monitor/sports-betting.html`
`ufcPicksData` / `tennisPicksData` / `golfPicksData` arrays). These picks were
hand-researched (no automated odds source, no model). We need a way to
sanity-check them against an independent prediction-market signal before any
human acts on the recommendations.

## What this change adds

`tools/verify_manual_sports_picks.py` — read-only verifier that:

1. Parses the JS pick arrays out of `live-monitor/sports-betting.html`.
2. Queries the Polymarket Gamma API (`tag_slug=tennis|golf|mma`).
3. Fuzzy-matches each pick against the active markets, with an opponent-aware
   scorer that prefers head-to-head questions over season-long futures and
   hard-rejects noise tokens (`tour championship`, `become champion`,
   `wimbledon winner`, etc.).
4. Computes the gap between the bookmaker implied probability (from
   `best_odds`) and Polymarket's last-trade implied probability.
5. Emits a markdown + JSON report under `reports/MANUAL_SPORTS_PICKS_VERIFICATION_<UTC>.{md,json}`.

Verdicts:

- `polymarket_confirms_edge` — Polymarket and the manual `win_probability`
  lean the same way by ≥ 2pp.
- `polymarket_alone_signals_edge` — Polymarket gap ≥ 5pp but the manual model
  didn't flag it (or no manual `win_probability` was supplied).
- `polymarket_disagrees_strongly` — Polymarket and the manual call point in
  opposite directions by ≥ 5pp.
- `soft_signal` / `polymarket_neutral` — small or no gap.
- `no_polymarket_match` — no comparable market on Polymarket.

## Findings from the first run (2026-04-26)

- **UFC (4 picks):** All 4 → `no_polymarket_match`. Polymarket carries
  champion / "fight-of-the-year" futures for these fighters but no per-fight
  h2h markets at this snapshot. UFC h2h verification will require a different
  cross-source (e.g. Kalshi UFC contracts, or sharp-book consensus from The
  Odds API).
- **Golf PGA Championship outrights (3 picks):** All 3 →
  `no_polymarket_match`. Polymarket only covers the **TOUR Championship**
  outright at this snapshot, not the PGA Championship — a different event.
  Hard-rejected to avoid spurious comparison.
- **Tennis (3 picks):** Polymarket has Roland Garros tournament-winner
  outrights, which the matcher does pair, but the manual picks appear to be
  for early-round h2h (Alcaraz vs Sinner R1, etc.), so the gaps shown
  reflect a **market-structure mismatch**, not a real edge. The matcher
  flags these honestly via large gaps; reviewers should treat tennis rows as
  "needs sharper Polymarket coverage" rather than acting on the verdicts.

## Limitations / honest caveats

1. **Polymarket coverage is sparse for these sports.** Most manual picks
   (UFC h2h, golf single-tournament, tennis early-round) have no
   like-for-like Polymarket market. The verifier is most useful as a
   *gate that surfaces missing coverage* — not as a green-light signal.
2. **No devig.** Bookmaker implied probability uses raw `1/odds`; for binary
   markets the true fair probability is 1–3pp lower. Devig would matter at
   the 2pp `soft_signal` threshold.
3. **Fuzzy match can still false-positive** when Polymarket carries a
   season-long futures market we haven't added to the hard-reject list.
   Match score and the matched market title are both surfaced in the report
   for spot-check.
4. **No automated odds source for tennis/golf yet.** Until OLG / Betway
   scrapers (added by the same PR for UFC) extend to these sports, the
   manual picks remain the authoritative input — the verifier validates
   their direction, not their existence.

## Suggested follow-up (out of scope here)

1. **Add a Kalshi adapter.** Kalshi has CFTC-regulated single-event UFC
   contracts and per-major golf outrights — closer to the manual picks'
   granularity. Schema is similar to Polymarket Gamma; one new fetch
   function in `verify_manual_sports_picks.py`.
2. **Wire `tools/polymarket_edge_scan.py` into `tennis` / `golf` tags** —
   currently only NBA/NHL/NFL/MLB/MLS/MMA. The site-side `sports_picks.php`
   would also need to expose tennis/golf picks before the cross-join works
   end-to-end.
3. **Schedule the verifier weekly** (similar to the
   `weekly-event-gap-scan` remote routine), opening a GitHub issue when any
   pick rates `polymarket_disagrees_strongly`.

## Verification

```
python tools/verify_manual_sports_picks.py
# parses 4 UFC + 3 tennis + 3 golf picks
# fetches ~1750 Polymarket markets across 3 tags
# writes reports/MANUAL_SPORTS_PICKS_VERIFICATION_<UTC>.{md,json}
```

Read-only. Hits the public Polymarket Gamma API only.
