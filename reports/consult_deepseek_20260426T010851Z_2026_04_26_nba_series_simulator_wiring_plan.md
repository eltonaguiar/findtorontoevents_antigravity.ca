# DeepSeek consult — 2026_04_26_nba_series_simulator_wiring_plan (20260426T010851Z)

Model: deepseek-chat. Tokens: {'prompt_tokens': 2494, 'completion_tokens': 2000, 'total_tokens': 4494, 'prompt_tokens_details': {'cached_tokens': 0}, 'prompt_cache_hit_tokens': 0, 'prompt_cache_miss_tokens': 2494}. Elapsed: 25.3s.

## Prompt

```
# NBA Series Simulator — Wiring Plan (consult-ready draft)

**Date:** 2026-04-26
**Author:** Claude Opus 4.7
**Status:** Draft for AI peer review (Cerebras + DeepSeek). Do **not** merge until feedback synthesized.

## What exists today

[tools/nba_series_simulator.py](tools/nba_series_simulator.py) — 179-line stdlib-only Monte Carlo for best-of-7 NBA playoff series. Inputs: per-game win probability `p`, current series score `0-0..3-3`, and home-court advantage split. Outputs: series-winner price, exact-series-length distribution (in 4/5/6/7), and the winning-team-by-game-N marginals.

It's currently **orphan** — no callers. Per CLAUDE.md Wire-Up Rule, committing it as-is would violate the breadth-only rule that closed PRs in the 2026-04-22 hedge-libs audit. This plan is the wire-up.

## Why this is high-leverage

External review (paraphrased):
> "NBA rest/B2B and series Monte Carlo (zig-zag pricing for playoff series markets) — both low-effort, high-payoff during playoffs. Move from 'market-consensus +EV hunter' to 'private-model + market-deviation hunter.'"

Series-level markets ("Lakers in 5", "series goes 7", "team to win series at -350") see far less volume than single-game lines and react slowly to per-game outcomes. After the public over-reacts to Game 1, the series-winner price for the loser is often more wrong than the next-game price — the classic "zig-zag" mispricing. A correct fair price comes from rolling out the remainder of the series via Monte Carlo from the current series score using the per-game win probability the existing analyzer already produces.

The deployed `lm_sports_clv` shows **avg CLV −1.22% across 10,101 settled events, 21.2% positive** ([sports_ml.php?action=clv](https://findtorontoevents.ca/live-monitor/api/sports_ml.php?action=clv)). Series-market mispricings are one of the largest unexploited inefficiencies the system isn't currently surfacing — every other +EV bet flows through Pinnacle/consensus devig, where books are sharpest.

## Concrete wiring (option B — full integration)

### Data flow

```
sports_picks.php?action=today
  → sports_value_analyze_run() over single-game ML buckets (existing)
  → for each NBA bucket flagged is_playoff_series=1:
      → call sports_value_nba_series_price($p_per_game, $current_series, $hca)
        → invokes a new PHP class that wraps the Python sim via shell_exec or
          consumes a precomputed JSON cache (preferred — less PHP/Python coupling)
      → emits two extra value-bet rows per bucket:
        - market='series_winner' outcome='Team A series win'
        - market='series_length' outcome='4|5|6|7' (best of available)
      → these rows go through the same EV gate, devig, and auto-place pipeline
```

### File targets

| File | Change |
|---|---|
| `tools/nba_series_simulator.py` | **No code change.** Add a `--json-out <path>` flag if missing (already supports `--stdout` per docstring). Document expected invocation. |
| `tools/nba_series_pricer.py` | **New ~80 LoC.** Daily cron-driven driver. For each active NBA playoff series (read from `lm_sports_odds` joined with a small `nba_series_state` table containing `series_id, home_team, away_team, series_score, hca_team`), call the simulator and write `data/nba_series_prices.json` indexed by `series_id`. |
| `live-monitor/api/sports_value_nba_series_lib.php` | **New ~60 LoC.** Reads `data/nba_series_prices.json` (15-min staleness guard, same pattern as the new Pinnacle snapshot loader). Exposes `sports_value_nba_series_lookup($eventId): ?array` returning `{ series_winner_prob_home, series_winner_prob_away, length_probs: {4,5,6,7}, ... }`. |
| `live-monitor/api/sports_value_analyze_lib.php` | **+30 LoC.** After `$truepPin` / Jensen consensus produces `$p` for the single-game ML, lookup the series price; if hit, emit additional bucket entries for `series_winner` and `series_length` markets. Reuse existing EV calc, devig comparison, auto-place gate. |
| `live-monitor/api/sports_picks.php` | **+10 LoC.** Surface the new market types in `action=today` (already iterates by bucket — just needs the new market labels in the response shaper). |
| Database | **New table `nba_series_state`** (manual seed: 8–16 rows during playoffs). Columns: `series_id INT PK, home_team VARCHAR, away_team VARCHAR, current_home_wins TINYINT, current_away_wins TINYINT, hca_team CHAR(4), updated_at TIMESTAMP`. Seeded by hand from ESPN once per playoff round; updated nightly by a small cron after `settle_by_scores`. |

### Cron

```
30 6 * * *  python3 tools/nba_series_pricer.py
```

(After the daily settle pass; pulls the freshest `current_*_wins` from settled rows.)

### Wire-Up Rule satisfaction

`tools/nba_series_simulator.py` is consumed by `tools/nba_series_pricer.py`, whose JSON output is consumed by `sports_value_nba_series_lib.php`, which is called from `sports_value_analyze_lib.php` — invoked on every `sports_picks.php?action=today`. Production caller: `sports_value_analyze_run()`.

## Risks / edge cases

1. **HCA estimation.** The simulator takes a single home-edge parameter. NBA playoff HCA is ~3.5pp on win prob (regular season is ~3pp). Mis-estimating drives the series-length distribution more than the winner — most of the EV here is on length markets. Mitigation: park HCA at 3.5pp and revisit after 30+ settled length tickets.
2. **`p` instability across games.** The simulator assumes constant `p`. Real per-game `p` shifts with injuries, foul trouble, rest. Series-winner pricing is robust to this (the variance washes out over 4–7 games); length pricing is not. Mitigation: only emit `series_winner` bets in v1. Length markets behind a separate flag.
3. **Sample size for validation.** Playoffs = ~75 series-equivalent games per year. Statistical confidence on PnL takes 2+ playoff cycles. Mitigation: tag every series bet with `algorithm='series_sim_v1'`; gate further development on the 60-day cohort delta vs `value_bet_gr202604`.
4. **Series state freshness.** If `current_home_wins`/`current_away_wins` are stale by one game, the model prices a series that no longer exists. Mitigation: hard-fail (return null) when `nba_series_state.updated_at < commence_time of next game in the series`.
5. **Manual seeding burden.** First-round (16 series) → ~30 minutes one-time per round. Acceptable for v1; automate from ESPN scoreboards in v2 if proven.
6. **Coupling to Pinnacle Shin commit.** The series price uses the same `$p` that Shin produces upstream. The two changes compound — Shin sharpens `p`, series sim leverages the sharper `p` into series markets. Cleaner to land Shin first, then series sim against the new baseline.

## Validation plan

| Phase | Action | Success metric |
|---|---|---|
| Pre-wire | Sim self-test: `p=0.55, hca=home, series=0-0` should return ~62% series-win for the favorite (matches published NBA elasticities). | Pass / fail vs reference. |
| Soak | After wire-up, run for one playoff round (≈10 days, ~16 series, ~64 series-bet candidates after EV ≥ 2pp gate). Tag with `algorithm='series_sim_v1'`. | At least 8 directional outcomes; net PnL within 1.5σ of zero. |
| Decision | After 60 settled directional series bets, compute Wilson CI on win rate vs the `value_bet_gr202604` cohort. | If lower bound > 50%, expand to length markets. If lower bound < 45%, kill. |

## What v1 explicitly does NOT include

- Per-game `p` adjustments (rest, injuries, fouls)
- Live in-game pricing (only pre-game)
- Length markets ("series goes 7") — gated to v2 after winner-market validation
- Spread/total markets — independent project
- Other sports (NHL Stanley Cup, MLB postseason) — copy-paste pattern but scope creep here

## Why this is reviewable in one pass

- **No new dependencies.** Stdlib Python + plain PHP file reads.
- **Additive.** Existing analyzer behavior unchanged for non-NBA buckets and for NBA games not flagged `is_playoff_series=1`.
- **Reversible.** Setting `nba_series_state` to empty disables all new emissions. No downstream coupling.
- **Bounde
```

## Response

This is an excellent, well-structured plan. I'll provide my review as requested, addressing each open question and flagging any concerns.

## Overall Assessment

**Verdict: Approve with conditions.** The plan is sound, the blast radius is well-contained, and the reasoning is thorough. The main issues are around HCA calibration, the `p` source decision, and the auto-place gate threshold.

## Responses to Open Questions

### 1. HCA Parametrization

**Recommendation: Use a single scalar of 3.0pp for v1, not 3.5pp.**

Sources:
- NBA playoff HCA is actually *smaller* than regular season, not larger. Per [Nylon Calculus](https://nyloncalculus.com/2017/05/15/home-court-advantage-nba-playoffs/) and [FiveThirtyEight](https://fivethirtyeight.com/features/the-nba-playoffs-home-court-advantage-is-shrinking/), playoff HCA has been ~2.5-3.0pp in recent years (2015-2023), vs ~3.5pp in regular season.
- The intuition: better teams (which make playoffs) are less affected by venue; playoff intensity reduces the "comfort" gap; referees call tighter games in playoffs, reducing home-favoring bias.

**Mitigation**: Parameterize as a config constant, not a hard-coded value. Start at 3.0pp. After 30+ settled series-winner bets, you can back-test whether the actual vs predicted win rate suggests recalibration.

### 2. Length Markets in v1 vs v2

**You are correct to defer.** The sample-size argument is right, but there's a stronger reason: **length markets are path-dependent in ways that winner markets are not.**

A series-winner probability is a function of `p` and current score. A length-7 probability depends on `p`, current score, *and* the exact sequence of future outcomes. Small errors in `p` compound non-linearly in length distributions. With only ~75 series per year, you'd need 3+ years to validate length-market calibration.

**Strong recommendation**: Keep length markets gated behind a separate flag, and only enable after:
- 60+ settled series-winner bets with Wilson CI lower bound > 50%
- A separate simulation study showing length-market calibration within 2% of actual outcomes on historical data

### 3. `p` Source

**Use the Pinnacle anchor `$p` when available, fall back to consensus Jensen.**

Rationale:
- The series sim is a *pricing* model, not a *prediction* model. You want the most efficient `p` available, because you're betting against the market's series price. Using the same `p` that the market uses for single games (Pinnacle) ensures your series price is a consistent extension of the same information set.
- Jensen consensus introduces model risk: if your devig method has a systematic bias, that bias compounds across 4-7 games in the series sim.
- Exception: if Pinnacle is missing for a game (rare in playoffs), fall back to Jensen. The series sim should handle this gracefully by returning null for that series.

**Implementation note**: Pass `$p_source` through to the series price output so you can later analyze whether Pinnacle-sourced vs Jensen-sourced series bets perform differently.

### 4. Auto-Place Gate

**Yes, clear a higher bar: `EV ≥ 4%` for series-winner bets.**

Reasons:
- **Model risk is higher**: The series sim is unvalidated, uses a constant-`p` assumption, and has HCA estimation error.
- **Liquidity is lower**: Series markets are thinner. A 1.5% EV edge on a thin market may not be realizable at the quoted price.
- **Adverse selection risk**: If your model is wrong, you're systematically betting into a market that may be pricing in information you don't have (e.g., injury news, rest advantage).

**Suggested tiered approach**:
- `EV ≥ 4%`: Auto-place
- `2% ≤ EV < 4%`: Flag for manual review
- `EV < 2%`: Ignore

Revisit after 30+ settled bets. If the win rate is > 55%, lower the gate to 3%.

### 5. Database Seeding

**Manual seed for v1, but automate the *update* step immediately.**

The one-time cost of 30 minutes per round is acceptable. The real risk is **stale data** — if you forget to update after a game, the model prices a non-existent series state. This is a hard-fail scenario (your mitigation #4), but it means zero series bets for that series until the manual update happens.

**Recommendation**:
- Manual seed for initial state
- Automate the *update* step: after `settle_by_scores` runs, check if any settled event has `is_playoff_series=1` and update `current_home_wins`/`current_away_wins` accordingly
- This reduces the manual burden to once per round (initial seed) rather than after every game

### 6. Anything Missing?

**Yes, three things:**

**a. Series identification in the odds feed**
How does `sports_picks.php?action=today` know which events are part of a playoff series? The `is_playoff_series=1` flag needs to be set somewhere. Options:
- Manual flag in the database per event (fragile)
- Heuristic: if two teams play multiple times in a short window with the same matchup, it's a series (brittle)
- Explicit `series_id` column on the events table (best, but requires schema change)

**Recommendation**: Add a `series_id` column to the events table (nullable INT, FK to `nba_series_state`). Populate manually alongside the series state table. This is a one-time schema change that enables clean joins.

**b. The "zig-zag" timing window**
The classic zig-zag mispricing occurs *immediately* after a game ends — the public over-reacts to the result, and the series-winner price for the loser becomes inflated. Your daily cron at 6:30 AM may miss this window if games end at 10 PM ET and the market corrects overnight.

**Recommendation**: Add a second cron run immediately after the last game of the night (or make the pricer event-driven, triggered by `settle_by_scores`). The 6:30 AM run catches overnight corrections but may miss the peak mispricing.

**c. The `p` vs series-price relationship for extreme scores**
At `3-0`, the series is essentially over. The model should handle this gracefully:
- `3-0` with `p=0.55` → series-win probability should be ~95%+ for the leading team
- `3-3` → essentially a coin flip, slightly favoring the team with HCA in Game 7

**Recommendation**: Add a unit test for these edge cases. The simulator should naturally handle them, but verify.

## Additional Concerns

### The `--json-out` flag

You say the simulator already supports `--stdout`. If the output is clean JSON, you don't need `--json-out`. But if `--stdout` includes logging or formatting, add the flag. **Recommendation**: Keep it simple — pipe `--stdout` through `jq` or write a thin wrapper in the pricer that parses the output.

### PHP-Python coupling via shell_exec

This is fine for a daily cron, but be aware:
- `shell_exec` blocks the PHP process
- If the Python script crashes, the PHP script gets no output
- Error handling must be explicit

**Recommendation**: In `sports_value_nba_series_lib.php`, if the JSON file is missing or stale (>15 min), return null gracefully. The analyzer should treat a null series price as "no series bet available" — not an error.

### The "Shin first" dependency

You note that the series sim should land after the Shin commit. **Strongly agree.** The series sim is a downstream consumer of `p`. If `p` changes (due to Shin), the series prices change. Landing Shin first means:
- The series sim is calibrated against the final `p` pipeline
- You don't have to re-validate after Shin lands
- The two changes can be reviewed independently

## Summary of Recommendations

| # | Item | Recommendation |
|---|---|---|
| 1 | HCA | 3.0pp, not 3.5pp. Parameterize as config constant. |
| 2 | Length markets | Defer to v2. Strong agree. |
| 3 | `p` source | Pinnacle anchor first, Jensen fallback. Pass `$p_source` through. |
| 4 | Auto-place gate | 4% for series-winner bets. Tiered approach. |
| 5 | DB seeding | Manual seed, auto-update after settle. |
| 6 | Series identification | Add `series_id` column to events table. |
| 7 | Timing | Add post-game cron run for zig-zag window. |
| 8 | Edge cases | Unit test for 3-0, 3-3,

