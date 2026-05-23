# Shin Devig Backtest -- 2026-04-26

Validation of `sports_value_devig_shin()` introduced in PR #401
(`live-monitor/api/sports_value_analyze_lib.php`). Compares Shin (1993)
bisection devig against the prior proportional inverse-normalize on a
snapshot of the production DB (`ejaguiar1_sportsbet.sql`).

## Methodology

- Re-implemented the PHP `sports_value_devig_shin()` in Python (stdlib).
- Parsed `lm_sports_odds` h2h rows; kept buckets with both Pinnacle home
  and away prices.
- For each bucket: Shin fair probs vs proportional fair probs.
- Cross-referenced settled `lm_sports_bets` (won/lost) and computed Brier
  score per method against realized win.

## Results

```
odds rows parsed:         19730
h2h buckets total:        342
Pinnacle h2h buckets:     158
settled h2h bets:         19
settled & Pinnacle-anchored: 6
mean Shin-Prop favorite delta (pp): +0.2784
Shin Brier:               0.197497
Proportional Brier:       0.198140
Brier diff (Prop - Shin): +0.000644  (Shin better)
```

## Verdict

**INCONCLUSIVE.** Pinnacle-anchored settled bets in the snapshot are
below the 20-sample threshold for a meaningful Brier comparison.
Will rerun once `lm_sports_odds_history` populates from the new
`*/5 * * * *` Pinnacle scraper cron and additional bets settle.

The favorite-side mean delta is still informative as a structural
check: Shin is expected to push the favorite slightly higher than
proportional (positive pp) when both books are vigged.

## Reproduce

```
python tools/backtest_shin_devig.py
```

Source: `tools/backtest_shin_devig.py`. Read-only on the SQL dump.
Stdlib Python only; no network calls.
