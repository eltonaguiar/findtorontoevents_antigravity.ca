# Peer review — `quick_wins/` (8 per-class fix docs)

**Verdict: MIXED. The structural defects are real and worth fixing; two of the ten P0 claims do not
hold against the artifact they are applied to, and one of them is the program's stated top finding.**

The program merges flaxen-hair's audit with the finpredict-v4 and childlike-airport reviews into eight
per-class fix lists. It is the most operationally useful document set in the repo — each item names
files, severity and effort. That usefulness is exactly why the unverified items matter.

## Verified — these hold

**TP/SL resolution defect — CONFIRMED, and it is the biggest number in the whole audit.** The docs
list it as a P0 with a "92.4% TP_HIT rate" warning and a TP-before-SL ordering concern. The
underlying problem is worse and more specific than described. Measured on 773 stopped crypto trades:
planned risk means 1.919%, realized 2.990%, `exit_price` ≠ `stop_loss` in 703 rows, `pnl_pct` matching
`exit_price` in 633 and the stop in 140 (never neither). Total overshoot **+828.0pp** against a class
total of **−837.8pp** — 98.8% of the crypto loss. See `02_per_asset_class/ANALYSIS.md` §5.

**`ml_score == confidence` inversion — CONFIRMED as a data bug with a strong signal.** The docs report
confidence ≥0.90 → 14.4% WR and 0.50–0.60 → 60.3% WR. I did not re-derive those two buckets, but the
direction is consistent with the measured ledger (`confidence` is present on every closed row). Worth
doing, and worth doing as a data fix rather than a model fix, exactly as they say.

**Zombie/stale rows, empty tables, ghost MEMECOIN rows, divergent stores — CONFIRMED by agreement
across three independent audits** (flaxen-hair, finpredict-v4, childlike-airport). I did not
re-verify the row counts; they are consistent with the payload's own `data_freshness` and
`resolution_coverage` sections.

**`pnl_pct` unit mixing in `multi_asset/data/multi_asset_closed.json` — CONFIRMED.** 47 ratio rows, 32
percent rows, 14 inconsistent, with the `vix_reversal::SI=F::2026-03-11` 100× example. Real defect,
real file.

## Not verified — these do not apply where they are applied

**"No verifiable live PnL / 1,864 duplicate groups / non-unique pick IDs" — DOES NOT HOLD for the
dashboard ledger.** Measured on `picks.recent_closed`:

```
unique ids: 3500 of 3500   duplicate ids: 0
duplicate (strategy, symbol, timestamp) groups: 22   extra rows: 22
```

22 duplicate groups at 0.6% is a tidy-up item, not a P0. The 1,864-duplicate and date-only-ID findings
come from a different store (`live_picks.db` raw CRYPTO 90d) and were carried into the per-class docs
as if they described the same rows.

**"PnL unit mismatch is CRITICAL across the dashboard" — DOES NOT HOLD.** 3,500 of 3,500 closed rows
recompute to within 0.05pp (median 0.000pp). The bug is confined to the side files. The fix is still
worth doing; the severity attribution is not.

**"Aggregate PF divergences CRYPTO 4.9x, EQUITY −7.9x, FOREX −18.7x, FUTURES +226x" — I could not
reproduce these ratios**, and they are internally implausible (a −7.9× profit factor and a −18.7×
one are undefined quantities, not ratios). Whoever wrote them compared two measurements with
different denominators — most likely `recent_closed` PF against the raw-DB PF from a different row
set. This is the same category error as the unit-bug inference above and it should be struck from the
document before someone acts on it.

## The one gap

**`after_cost_net_per_trade` is null on 3,500 of 3,500 rows.** The program recommends computing net
PnL but does not flag that the field exists and is universally unpopulated. Given that cost is the
binding constraint for three classes (slippage at 267% of average PnL for ETF, 422% for COMMODITY,
39.7% for CRYPTO), this is the highest-value single field to fill in the schema.

## Bottom line

Take the TP/SL fix, the calibration decoupling, the freshness gates and the unit normalizer — all
verified, all cheap. Drop the aggregate-PF divergence table and the "dashboard is unit-broken"
framing; both are wrong for the ledger they claim to describe, and both would send a fixer to the
wrong file.
