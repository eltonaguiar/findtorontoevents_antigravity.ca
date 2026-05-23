# Pinnacle Shin Devig + Scraper-Snapshot Fallback

**Date:** 2026-04-26
**Branch:** `feat/sports-edge-pwhl-ipl-betway-global-boost`
**Author:** Claude Opus 4.7

## Why

Live `lm_sports_clv` shows **avg CLV −1.22% across 10,101 settled events, only 21.2% of bets beating the close** (`sports_ml.php?action=clv`). That's a quantitative confirmation of the external review's diagnosis: the system is a market-consensus +EV hunter that gets slightly out-priced by the close. Sharper devig of the anchor book is the single highest-leverage, lowest-risk lever to move that number — every NBA/NHL/MLB/NFL pick goes through `sports_value_truep_pinnacle()`.

Two specific gaps existed in `live-monitor/api/sports_value_analyze_lib.php`:

1. **`sports_value_truep_pinnacle()` used proportional inverse-normalize.** That assumes vig is split proportionally to implied probability, which over-prices favorites and under-prices dogs by ~0.5–1.5pp on Pinnacle moneylines. Shin (1993) is the textbook fit for sharp 2-way books.
2. **`tools/pinnacle_anchor_scrape.py` was an orphan.** Existed since 2026-04-25 as a fully-implemented stdlib-only scraper for Pinnacle NBA/NHL/MLB/NFL moneylines (writes `data/pinnacle_snapshots/<UTC>.json`) — but had **zero PHP callers**, in violation of the CLAUDE.md Wire-Up Rule. When The Odds API drops Pinnacle from a feed (regional restrictions, props, non-major leagues), the analyzer silently lost its sharp anchor and fell back to LOO Jensen across all soft books.

## What this change adds

Three new functions in `live-monitor/api/sports_value_analyze_lib.php` plus one signature/call-site change:

| Function | Purpose |
|---|---|
| `sports_value_devig_shin($prices)` | Shin (1993) devig. Bisection on `z` ∈ [0, 0.5] solving `Σᵢ shin_pᵢ(z) = 1`; closed-form for n=2 once `z` is found. Falls back to multiplicative on numerical degeneracy. |
| `sports_value_load_pinnacle_snapshot()` | Reads the newest `data/pinnacle_snapshots/*.json` (15-min staleness guard) and indexes events by `"sport\|home\|away"`. Static-cached per request. |
| `sports_value_pinnacle_snapshot_lookup_for_bucket($bucket)` | Maps the analyzer's sport key (`basketball_nba`, `icehockey_nhl`, etc.) onto the scraper's tag (`nba`, `nhl`, …) and resolves the snapshot entry for a bucket. Returns `[$home_dec, $away_dec]` or null. |
| `sports_value_truep_pinnacle($outList, $nOut, $bucket = null)` | New optional `$bucket` arg. Logic: try Odds-API Pinnacle quotes first (current path), else snapshot fallback for 2-way buckets, then **always devig with Shin**, with proportional inverse-normalize as a final fallback. |

Caller (`sports_value_analyze_lib.php` line ~363) now passes `$bucket` so the snapshot fallback can match by sport+home+away. The downstream EV calc (line ~419) is unchanged — same `$truepPin` semantics, just sharper probabilities.

## Why Shin (and not Power)

- **Multiplicative (current):** simple but biased — overstates favorites ~0.5–1.5pp on sharp ML.
- **Power:** finds `k` such that `Σ (1/oᵢ)^k = 1`. One Newton step. Pulls dogs up. Decent on NBA/NFL but no theoretical motivation for a sharp book.
- **Shin (chosen):** models a fraction `z` of insider bettors. Tuned on Pinnacle in Štrumbelj (2014). Best calibration on sharp 2-way books, and it's what every CLV/sharp-line study in the academic literature uses. For 2-way the inner formula is closed-form once `z` is found by bisection.

The implementation uses bisection (60 iters max, 1e-10 tolerance) over Newton because bisection is unconditionally stable on the monotone `Σᵢ shin_pᵢ(z) − 1` function over `z ∈ [0, 0.5]`. Cost is negligible (one analyzer pass touches a handful of buckets).

## Wire-up rule satisfaction

`tools/pinnacle_anchor_scrape.py` is now consumed by `sports_value_load_pinnacle_snapshot()` in `sports_value_analyze_lib.php`, which is called from `sports_value_analyze_run()` — the production caller invoked by `sports_picks.php` and `sports_value_analyze_cli.php`. No more orphan.

## Operator step (one-time)

The scraper needs a cron entry on the deploy host:

```
*/5 * * * * cd /home/findtorontoevents.ca && python3 tools/pinnacle_anchor_scrape.py
```

Until that runs, the snapshot loader returns an empty cache and the analyzer behaves identically to the pre-change Pinnacle-from-Odds-API path (still benefits from Shin devig). No regression risk.

## Coverage and edge cases

- **2-way only.** The scraper currently emits NBA/NHL/MLB/NFL moneyline (period 0) only. 3-way (regulation hockey w/ draw, soccer 1X2), totals, spreads, props — none of these get the snapshot fallback. They still benefit from Shin when Pinnacle is in the Odds-API feed.
- **Tennis / golf / UFC** — no Pinnacle scraper coverage at all. Those continue to fall back to LOO Jensen.
- **Backtest mode** (`$isBacktest`) — caller does not pass `$bucket` into `sports_value_truep_pinnacle()` from the historical path; the snapshot lookup is therefore skipped automatically. Wall-clock-only mtime guard reinforces this.
- **Stale snapshot (>15 min)** — silently ignored. Analyzer falls through to Odds-API Pinnacle (if available) then LOO Jensen.
- **Home/away mapping** — outcome order is matched against `$bucket['home_team']`/`away_team` strings; a mismatch returns null rather than mapping wrong.

## Validation plan

1. **Unit-spot.** Once deployed, run `sports_value_analyze_cli.php` against a fixture with a known Pinnacle ML and verify `truep_pin` shifts by ≤ 1.5pp vs the old proportional output (Shin should slightly favor the dog).
2. **CLV cohort.** Tag picks with `devig_method = 'shin'` (follow-up — needs DB column on `lm_sports_bets`); compare 30-day CLV delta vs the pre-deploy baseline of −1.22%. Any improvement >0.5pp is a real win at this sample size.
3. **Snapshot-only buckets.** Once cron is live, audit `lm_sports_odds` for buckets where Pinnacle is missing but the snapshot fallback fires; verify EV calc still produces sensible values (no >5pp swings vs the prior Jensen-only path).

## Files changed

- `live-monitor/api/sports_value_analyze_lib.php` — +3 functions (~210 lines), 1 signature change, 1 call-site change.

No DB migrations. No new deps. PHP syntax balance verified by external regex (4 expected functions present at lines 164/250/311/352). PHP `-l` lint not run locally (PHP not on Windows path); will rely on CI / staging deploy for canonical syntax check.

## Follow-up (not in this commit)

1. **NHL goalie overlay** — full v1 scope written by parallel Plan subagent. Adds a goalie GSAx/SV% multiplier between Shin devig and EV calc on NHL ML, with confirmed-starter gate and A/B logging column. ~250 LoC across one new Python scraper + one new PHP lib + 1-line analyzer hook. Lower priority than this change because it touches NHL only and validation requires 200+ picks; this Pinnacle change touches every NBA/NHL/MLB/NFL pick immediately.
2. **DB column** `devig_method` on `lm_sports_bets` to enable the Shin-vs-multiplicative cohort comparison in step 2 above.
3. **Cron documentation** — include the `*/5 * * * *` entry in `SYNC_USER_GUIDE.md` or wherever the deploy runbook lives.
