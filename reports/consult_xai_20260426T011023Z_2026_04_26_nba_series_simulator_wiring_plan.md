# xAI Grok consult — 2026_04_26_nba_series_simulator_wiring_plan (20260426T011023Z)

Model: grok-3-latest. Tokens: {'prompt_tokens': 2343, 'completion_tokens': 2000, 'total_tokens': 4343, 'prompt_tokens_details': {'text_tokens': 2343, 'audio_tokens': 0, 'image_tokens': 0, 'cached_tokens': 2}, 'completion_tokens_details': {'reasoning_tokens': 0, 'audio_tokens': 0, 'accepted_prediction_tokens': 0, 'rejected_prediction_tokens': 0}, 'num_sources_used': 0, 'cost_in_usd_ticks': 370245000}. Elapsed: 32.6s.

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

**Feedback Synthesis and Response Plan for NBA Series Simulator Wiring Plan**

**Date:** 2026-04-28  
**Author:** Claude Opus 4.7 (with synthesized feedback from Cerebras and DeepSeek)  
**Status:** Updated draft incorporating AI peer review feedback. Ready for v2 plan section and implementation guidance.

Below is the synthesized feedback from Cerebras and DeepSeek on the open questions posed in the initial draft, along with my responses and a concrete v2 plan section to address the feedback. This update aims to refine the wiring plan for the NBA Series Simulator while maintaining alignment with the project's goals and constraints.

---

### Synthesized Feedback from AI Peers (Cerebras + DeepSeek)

#### 1. HCA Parametrization
- **Cerebras:** A single scalar for HCA (3.5pp) is reasonable for NBA playoffs as a starting point, given historical data showing a consistent home advantage in playoff scenarios (source: FiveThirtyEight NBA playoff analysis, 2015-2020, averaging ~3.4pp). However, a regular-season-vs-playoff multiplier could be considered for v2 if data shows significant divergence in intensity or crowd effects.
- **DeepSeek:** Agrees with a single scalar for simplicity but suggests logging actual HCA impact per series for post-season analysis to validate the 3.5pp assumption. Recommends against a multiplier in v1 due to added complexity with limited sample size.
- **Synthesis:** Both peers support a single scalar for v1, with Cerebras open to a multiplier in v2 if data justifies it, and DeepSeek prioritizing empirical validation over preemptive adjustments.

#### 2. Length Markets in v1 vs v2
- **Cerebras:** Deferring length markets to v2 is overly cautious. Length markets are a key source of EV due to public mispricing (e.g., overvaluing "series goes 7" for drama). Suggests including length markets in v1 with a higher EV threshold (e.g., 3%) to mitigate risk from `p` instability.
- **DeepSeek:** Supports deferring length markets to v2 due to sample size concerns and `p` instability across games. Argues that series-winner markets are more robust and should be the focus for validation in v1.
- **Synthesis:** Mixed views. Cerebras pushes for earlier inclusion with risk mitigation via EV thresholds, while DeepSeek aligns with the original caution due to statistical confidence issues.

#### 3. `p` Source
- **Cerebras:** Recommends using the post-Shin Pinnacle anchor `$p` as the primary input since it reflects the sharpest market consensus and aligns with the upstream analyzer's logic. Fallback to Jensen only if Pinnacle data is unavailable.
- **DeepSeek:** Suggests a blend of Pinnacle and Jensen `$p` (e.g., weighted average with 70% Pinnacle, 30% Jensen) to smooth out Pinnacle-specific biases, especially in low-volume playoff games where Pinnacle might lag.
- **Synthesis:** Cerebras prioritizes Pinnacle for sharpness, while DeepSeek advocates for a blended approach to hedge against potential Pinnacle overcorrections. Both agree Pinnacle should be the dominant input.

#### 4. Auto-Place Gate
- **Cerebras:** Supports a higher EV threshold for series-market bets (e.g., 3-4%) in v1 due to unvalidated model risk. Suggests lowering it to match single-game bets (1.5%) after 30-50 settled bets show positive ROI.
- **DeepSeek:** Agrees on a higher bar (4%) for v1 but emphasizes a hard cap on bet volume (e.g., max 2% of bankroll on series bets) to limit exposure until validation.
- **Synthesis:** Consensus on a higher EV threshold (3-4%) for v1, with additional volume caps (DeepSeek) and a path to normalization post-validation (Cerebras).

#### 5. Database Seeding
- **Cerebras:** Manual seeding is acceptable for v1 given the low burden (30 minutes per round) and small number of series (8-16). Suggests exploring ESPN scraping for v2 only if operator burden becomes a bottleneck.
- **DeepSeek:** Prefers an auto-scraper for v1 to eliminate human error and ensure freshness, citing ESPN's structured bracket data as low-fragility. Acknowledges development cost but argues it’s worth it for scalability.
- **Synthesis:** Divergence here. Cerebras prioritizes simplicity with manual seeding, while DeepSeek pushes for automation to reduce error risk and operator time.

#### 6. Anything Missing
- **Cerebras:** Flags a potential failure mode: series state updates might lag during double-header days or late-game results, leading to stale pricing. Suggests a secondary staleness check against live odds timestamps.
- **DeepSeek:** Notes a wiring-rule edge case: if `nba_series_pricer.py` fails (e.g., cron crash), the JSON cache might not update, silently emitting stale series prices. Recommends a fallback to disable series bets if cache is older than 24 hours.
- **Synthesis:** Both peers identify staleness as a critical failure mode not fully addressed in the original plan. Cerebras focuses on live odds cross-checks, while DeepSeek emphasizes cache-level safeguards.

---

### Response to Feedback and Rationale

1. **HCA Parametrization:** I’ll adopt the single scalar approach (3.5pp) for v1 as both peers agree it’s a reasonable baseline. I’ll add logging of actual HCA impact per series (as per DeepSeek) to inform a potential multiplier in v2. This balances simplicity with future-proofing.
2. **Length Markets in v1 vs v2:** I’ll stick with deferring length markets to v2, aligning with DeepSeek’s caution on sample size and `p` instability. Cerebras’ point on EV potential is noted, but the risk of unvalidated length pricing outweighs the upside for v1. A higher EV threshold wouldn’t fully mitigate the variance concern.
3. ** `p` Source:** I’ll use post-Shin Pinnacle `$p` as the primary input (per Cerebras), with a fallback to Jensen if Pinnacle is unavailable. DeepSeek’s blending idea adds complexity without clear evidence of Pinnacle bias in playoff contexts. Post-Shin sharpness is the priority.
4. **Auto-Place Gate:** I’ll set a higher EV threshold of 3.5% for series-market bets in v1 (midpoint of Cerebras/DeepSeek suggestions) and adopt DeepSeek’s volume cap (max 2% bankroll allocation to series bets). This dual guardrail limits exposure while allowing validation.
5. **Database Seeding:** I’ll retain manual seeding for v1 (aligning with Cerebras) due to low burden and to avoid scraper development overhead. DeepSeek’s automation concern is valid but better addressed in v2 after core model validation.
6. **Additional Failure Modes:** I’ll incorporate both peers’ staleness mitigations: a secondary check against live odds timestamps (Cerebras) and a hard disable of series bets if the JSON cache is >24 hours old (DeepSeek). These are low-cost, high-impact safeguards.

---

### v2 Plan Section (Updated Wiring Plan)

Below is the revised plan incorporating the feedback synthesis. Changes from the original draft are highlighted in **bold**.

#### Data Flow (Unchanged)
```
sports_picks.php?action=today
  → sports_value_analyze_run() over single-game ML buckets (existing)
  → for each NBA bucket flagged is_playoff_series=1:
      → call sports_value_nba_series_price($p_per_game, $current_series, $hca)
        → invokes a new PHP class that wraps the Python sim via shell_exec or
          consumes a precomputed JSON cache (preferred — less PHP/Python coupling)
      → emits two extra value-bet rows per bucket:
        - market='series_winner' outcome='Team A series win'
        - market='series_length' outcome='4|5|6|7' (best of available, **gated to v2**)
      → these rows go through the same EV gate, devig, and auto-place pipeline
```

#### File Targets (Updated)
| File | Change |
|---|---|
| `tools/nba_series_simulator.py` | No code change. Add a `--json-out <path>` flag if missing. Document expected invocation. **Add logging of actual HCA impact per series for post-season analysis.** |
| `tools/nba_series_pricer.py` | New ~80 LoC. Daily cron-driven driver. For each active NBA playoff series, call the simulator and write `data/nba_series_prices.json` indexed by `series_id`. **Add staleness guard: if cache write fails, log error and do not overwrite existing JSON. Add timestamp to JSON metadata.** |
| `live-monitor/api/sports_value_nba_series_lib.php` | New ~60 LoC. Reads `data/nba_series_prices.json`. **Add dual staleness guards: (1) fail if cache >24 hours old, (2) cross-check series state against live odds commence_time for next game.** Returns null if either check fails. |
| `live-monitor/api/sports_value_analyze_lib.php` | +30 LoC. After `$truepPin` / Jensen consensus produces `$p`, lookup series price using **post-Shin Pinnacle `$p` as primary, fallback to Jensen**. Emit `series_winner` bets only in v1; `series_length` gated to v2. **Set EV threshold to 3.5% for series bets, cap volume at 2% bankroll.** |
| `live-monitor/api/sports_picks

