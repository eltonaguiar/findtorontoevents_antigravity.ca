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
- **Bounded blast radius.** ~180 LoC of new code + 30 LoC analyzer hook + 1 small DB table. Failure mode is "no series bets emitted," not "wrong picks."

## Open questions for AI peers

1. **HCA parametrization** — single scalar OK for NBA playoffs, or do we need a regular-season-vs-playoff multiplier? Cite a source if you have one.
2. **Length markets in v1 vs v2** — am I over-cautious deferring length markets, or is the sample-size argument right?
3. **`p` source** — should the series sim consume the post-Shin Pinnacle anchor `$p`, or the consensus Jensen `$p`, or some blend? The deployed analyzer uses Pinnacle when present, falls back to Jensen.
4. **Auto-place gate** — the existing pipeline auto-places at `EV ≥ 1.5%` with min-books gates. Should series-market bets clear a higher bar (e.g., `EV ≥ 4%`) given the model is unvalidated?
5. **Database seeding** — manual seed (current proposal) vs scrape ESPN bracket for v1. Cost-benefit on the operator burden vs. fragility of an auto-scraper.
6. **Anything missing** — any failure mode or wiring-rule violation I haven't flagged.

## Action plan after consult

1. Synthesize Cerebras + DeepSeek feedback into a v2 plan section at the bottom of this doc.
2. Implement against the v2 plan on this branch (`feat/pinnacle-shin-devig` → may rename).
3. Open the PR with consult outputs linked in the body.
4. Do **not** merge until at least one human reviewer has approved.

---

## v2 Plan — synthesis from AI peer review (2026-04-26)

Consultations completed (real responses, see `reports/`):
- **DeepSeek `deepseek-chat`** — comprehensive 8-point review.
- **Cerebras `gpt-oss-120b`** — table-format verdicts, very actionable.
- **Cerebras `llama3.1-8b`** — high-level concerns only, low signal.
- **xAI `grok-3-latest`** — DROPPED. Hallucinated synthesis of Cerebras+DeepSeek before either had returned. Treat as untrustworthy peer.

### Consensus changes from v1 → v2

| # | Item | v1 plan | v2 plan (consensus) | Source |
|---|---|---|---|---|
| 1 | **HCA** | 3.5pp single scalar | **Round-aware: 3.0pp first round, 3.5pp later rounds**. Config constant. Log actual HCA per series for v3 calibration. | DeepSeek (3.0pp NBA playoffs <reg season) + Cerebras (round-aware) |
| 2 | **Length markets** | Deferred v2 | **Confirmed deferred.** Comment out the `series_length` emission block, keep code path. Re-enable only after ≥60 settled winner bets show Wilson lower bound > 50%. | Both peers strongly concur |
| 3 | **`p` source** | TBD | **Post-Shin Pinnacle `$p` primary, Jensen fallback. No blending.** Pass `$p_source` through for later cohort analysis. | Both peers strongly concur |
| 4 | **Auto-place gate** | TBD (default 1.5%) | **EV ≥ 4% for series-winner bets.** Cap volume at 2% bankroll on series bets. Tiered: <2% ignore, 2–4% manual review, ≥4% auto-place. Lower to 3% only after 30+ settled bets show >55% WR. | DeepSeek (4%) + Cerebras (3%) — go with the more conservative 4% for unvalidated model |
| 5 | **Staleness guards** | 15-min cache + commence_time check | **Add (a) 12h sanity-check warn + skip in `nba_series_pricer.py` (Cerebras), (b) 24h hard-disable cache check in `sports_value_nba_series_lib.php` (DeepSeek), (c) monitoring counter `nba_series_pricer_success_total` / `..._failure_total`.** | Both peers; orthogonal protections |
| 6 | **DB seeding** | Manual | **Manual seed v1 + auto-update after `settle_by_scores`** (DeepSeek). Ship with one nightly cron that joins settled rows back into `nba_series_state.current_*_wins`. | Both peers |
| 7 | **Schema** | n/a | **Add `series_id` column to events table** (nullable INT, FK to `nba_series_state`). Populate manually alongside seed. | DeepSeek; missing from v1 |
| 8 | **Timing** | Daily 6:30 AM cron | **Add second cron run immediately after the last game of the night** (event-driven, triggered by `settle_by_scores`). The 6:30 AM run misses the peak zig-zag window. | DeepSeek; high-EV finding |
| 9 | **Edge-case unit tests** | n/a | **Add tests** for 3-0, 3-3, 0-3 series states. Sim should naturally handle but verify. | DeepSeek |
| 10 | **Wire-Up Rule** | Satisfied via `sports_value_nba_series_lib.php` → analyzer | **Confirmed OK.** No change. | Cerebras |

### Items NOT changed from v1

- File targets (same 4 files + 1 new DB table — adding `series_id` column to existing `lm_sports_odds`/events table is +1 small migration)
- Validation phases (pre-wire self-test → soak → 60-bet decision)
- Out-of-scope list (per-game `p` adjustments, live in-game pricing, length markets, spread/totals, other sports)

### Items rejected from peer feedback

- **DeepSeek's blended `p` proposal** (70% Pinnacle / 30% Jensen): rejected by both me and Cerebras for the same reason — adds hidden weighting that's hard to audit, no evidence of Pinnacle bias in playoff context worth correcting for.
- **Cerebras llama3.1-8b's "more advanced time-series for `p`"**: out of scope for v1; per-game `p` adjustment is explicitly v2 work.
- **xAI's recommendation to set EV at 3.5%**: dropping the entire xAI consult since it was hallucinated.

### Pre-implementation gate

Before wiring code, the operator should confirm:

1. PR #401 (Pinnacle Shin) is **merged and the cron is running** so post-Shin `p` is the live value the series sim will consume.
2. CLV trend after Shin (4 weeks of data) — does `avg_clv_pct` move from −1.22% toward 0? If it gets worse, do not proceed with series sim until root cause is understood.
3. The schema change (`series_id` column) is approved.

If any of these are blocked, hold the series-sim wire-up. The plan is reversible — `nba_series_state` empty disables all emissions.
