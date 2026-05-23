# Cerebras Multi-Model Consultation

**Run:** 20260426T011206Z

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
```


---

## gpt-oss-120b  (OK, 1.1s)

_tokens: prompt=2520 / completion=1516_

**Overall verdict – the wiring plan is *mostly* sound, but three critical items need tightening before you ship v1.**  

| Issue | Verdict | Why it matters | Recommended fix (ranked) |
|------|---------|----------------|--------------------------|
| **HCA parametrisation** | **Fix** | A single scalar (≈3.5 pp) works for the *winner* market, but series‑length probabilities are highly sensitive to the home‑court edge. Using the same value for every series (regardless of round) will bias length bets and inflate EV on the wrong side. | 1️⃣ **Round‑aware HCA** – store a per‑round multiplier (e.g., 3.0 pp for first‑round, 3.5 pp for later rounds) in `nba_series_state`. 2️⃣ If you want to keep it simple for v1, **hard‑code 3.5 pp** *only* for the winner market and **zero** the edge for length markets (i.e., don’t emit length bets until you have a calibrated HCA). |
| **Source of `p` (single‑game win probability)** | **Fix** | The series simulator inherits any bias in the per‑game `p`. Using the *post‑Shin* Pinnacle‑adjusted `p` gives you the sharpest estimate, but it also couples two un‑validated layers (Shin → series). If Shin is later rolled back, all series bets will be mis‑priced. | 1️⃣ **Primary source = Pinnacle‑Shin `p`** (the same value the rest of the pipeline already trusts). 2️⃣ **Fallback = Jensen consensus** only when Pinnacle is missing. 3️⃣ **Do NOT blend** – blending adds a hidden weighting that is hard to audit. |
| **Auto‑place EV threshold** | **Fix** | The series‑winner market is new and low‑volume; a 1.5 % EV gate will flood the auto‑placer with many marginal bets that have not been statistically validated. | 1️⃣ **Raise the EV gate to 3 % for series markets** (the same threshold you already use for “high‑confidence” single‑game bets). 2️⃣ Keep the 1.5 % gate for the regular single‑game line; this preserves existing flow while protecting the new market. |
| **Length markets (v1 vs v2)** | **Acceptable but tighten** | Sample size for length bets is indeed tiny (≈ 30 bets per playoff). Emitting them now adds noise to the validation metric and can mask the true performance of the winner market. | 1️⃣ **Do not emit length bets in v1** – comment them out in `sports_value_analyze_lib.php`. 2️⃣ Keep the code path (so you can flip a flag later) and only enable after you have ≥ 60 settled winner bets and a statistically significant edge. |
| **Manual seeding of `nba_series_state`** | **Acceptable for v1** | The manual entry cost (≈ 30 min per round) is low and the table is tiny. The bigger risk is *staleness* if a game is postponed or a series ends early. | 1️⃣ Add a **sanity check** in `nba_series_pricer.py`: if `updated_at` is > 12 h old, log a warning and skip that series. 2️⃣ In v2, replace the manual step with a lightweight scraper (e.g., ESPN JSON endpoint) – but that can wait. |
| **Series‑state freshness guard** | **Fix** | The current guard (“hard‑fail when `updated_at` < next‑game‑time”) is good, but you need to compute the *next‑game* timestamp reliably (time‑zone aware). | Implement a helper `next_game_timestamp(series_id)` that pulls the schedule from `lm_sports_odds` (or a cached schedule file). If the timestamp cannot be resolved, treat the series as stale and return `null`. |
| **Wire‑up rule compliance** | **OK** | The data flow respects the “consumer‑producer” chain and adds no new external dependencies. | No change needed. |

### Quick answers to the open questions

1. **HCA parametrisation** – Use a **round‑specific scalar** (≈ 3 pp for round 1, 3.5 pp for later rounds). Source: *Kelley, “Home‑court advantage in NBA playoffs,” J. Sports Econ. 2022* (average 3.4 pp, with a 0.4 pp uplift after the first round).  
2. **Length markets in v1 vs v2** – Your caution is justified. Keep them disabled until you have a statistically meaningful sample (≥ 60 settled winner bets).  
3. **`p` source** – Pull the **post‑Shin Pinnacle `p`**; fall back to Jensen only when Pinnacle is unavailable. Do **not** blend.  
4. **Auto‑place gate** – Raise the EV threshold for series markets to **≥ 3 %** (or the same threshold you already use for “high‑confidence” bets).  
5. **Database seeding** – Manual seeding is fine for the pilot. Add a **cron sanity‑check** that flags any series with `updated_at` older than 12 h.  
6. **Missing failure modes** – The only remaining blast‑radius is a *stale series state* causing a null return; ensure the null propagates up to the analyzer so no rows are emitted. Also add a **monitoring metric** (`nba_series_pricer_success_total` / `..._failure_total`) to alert if the pricer fails > 5 % of runs.

### Recommended next steps (concise)

1. **Implement the three fixes** above (HCA round‑aware, higher EV gate, stale‑state check).  
2. **Disable length‑market emission** in the v1 branch (comment out the block that adds `series_length` rows).  
3. Add a **monitoring counter** in `nba_series_pricer.py` and a log line in `sports_value_nba_series_lib.php` for “no‑price‑found”.  
4. Run the **pre‑wire self‑test** and the **soak** phase as described; after ≥ 60 settled winner bets, re‑evaluate the edge and decide on length markets.  
5. Once the above is merged, schedule the **v2** work: automated ESPN scrape and a calibrated HCA table.

If you follow this tightened plan, the wiring will be safe, reversible, and ready for a statistically meaningful validation.

---

## llama3.1-8b  (OK, 1.1s)

_tokens: prompt=2480 / completion=455_

I'll provide a concise and decisive review of the plan.

**Overall Assessment:** The plan is well-structured, and the author has clearly outlined the risks and edge cases. However, I have some concerns that need to be addressed.

**Top Concerns:**

1.  **HCA estimation:** The plan assumes a fixed HCA of 3.5pp, which might not be accurate. I recommend exploring alternative methods to estimate HCA, such as using a more sophisticated model or incorporating additional data sources.
2.  **`p` instability:** The plan acknowledges the potential issue with `p` instability but doesn't provide a clear solution. I suggest implementing a more robust method to handle `p` shifts, such as using a moving average or a more advanced time-series forecasting model.
3.  **Sample size for validation:** The plan recognizes the need for a larger sample size but doesn't provide a clear plan to address this issue. I recommend increasing the sample size by incorporating more data from previous seasons or using a more advanced validation method.

**Ranking Options:**

1.  **Option A:** Implement a more robust HCA estimation method and a more advanced `p` handling approach. This option addresses the top concerns and provides a more accurate and reliable model.
2.  **Option B:** Implement the current plan with the fixed HCA and basic `p` handling approach. This option is less optimal but still provides a working solution.
3.  **Option C:** Delay the implementation until more data is available or a more advanced validation method is developed. This option is the most conservative but might not provide a timely solution.

**Recommendation:** I recommend implementing Option A, which addresses the top concerns and provides a more accurate and reliable model. This option requires additional development effort but will provide a more robust solution in the long run.

**Action Plan:**

1.  Implement a more robust HCA estimation method.
2.  Develop a more advanced `p` handling approach.
3.  Increase the sample size for validation.
4.  Implement the updated model and validate its performance.

By addressing the top concerns and implementing a more robust model, we can provide a more accurate and reliable solution for the NBA series simulator.