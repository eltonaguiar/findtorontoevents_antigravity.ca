# Tennis Analytics Integration Plan — 7 Open-Source Repos → Live Picks

**Authored:** 2026-04-26
**Author:** Claude Opus 4.7 (branch `claude/tennis-analytics-research-RMIY0`)
**Status:** Research + wiring proposal. **No production code changed in this PR.**
**Related:** [updates/2026-04-26-sports-next-steps.md](2026-04-26-sports-next-steps.md), [updates/2026-04-24-sports-data-sources-integration.md](2026-04-24-sports-data-sources-integration.md), `CLAUDE.md` Wire-Up Rule.

---

## TL;DR

The sports stack already covers NBA/WNBA/NCAAB/NHL/NFL/CFL/NCAAF/MLB/MLS/EPL/La Liga
but **ships zero tennis picks today**. The `tennis_atp` and `tennis_wta` sport keys
are already wired into `live-monitor/api/sports_odds.php:44-45`, so the dashboard
table, filters and downstream pick pipeline will accept tennis rows the moment we
start writing them. Adding tennis is a **horizontal expansion onto existing rails**,
not a new vertical.

Seven open-source repos in the brief replace what would otherwise be a
~$50k/yr commercial sports-analytics stack. This document audits each, scores
fit-for-purpose against our pipeline, and proposes a four-phase landing plan
where every new module has an explicit production caller per the CLAUDE.md
[Wire-Up Rule](../CLAUDE.md).

---

## 1. The seven repos — audit + verdict

| # | Repo | Replaces | License | Fit | Phase |
|---|---|---|---|---|---|
| 1 | [JeffSackmann/tennis_atp](https://github.com/JeffSackmann/tennis_atp) | Paid stat feeds (~$500/mo) | CC-BY-NC-SA 4.0 | **Excellent.** Every ATP match since 1968. CSV-per-year, raw GitHub URL. | P1 (Data) |
| 2 | [JeffSackmann/tennis_slam_pointbypoint](https://github.com/JeffSackmann/tennis_slam_pointbypoint) | Point-level feeds (~$200/mo) | CC-BY-NC-SA 4.0 | **Excellent for in-match priors.** Scraped from the four Grand Slam sites since 2011. | P2 (Models) |
| 3 | [JeffSackmann/tennis_MatchChartingProject](https://github.com/JeffSackmann/tennis_MatchChartingProject) | Shot-by-shot scouting reports | CC-BY-NC-SA 4.0 | **Good, sparse.** 5,000+ matches charted; depth/direction/error-type. Use as a *style features* sidecar. | P2 (Models) |
| 4 | [jgollub1/tennis_match_prediction](https://github.com/jgollub1/tennis_match_prediction) | Pre-match + in-match prediction services | (check repo) | **Best-in-class for our use case.** ELO + 12-month serve/return → win probability, updates during the match. Built on Sackmann data → drop-in. | P2 (Models) |
| 5 | [yastrebksv/TennisProject](https://github.com/yastrebksv/TennisProject) | Ball-trajectory + bounce prediction | (check repo) | **Strong CV pipeline** (TrackNet → court keypoints → CatBoost bounce). Heavy. **Out of scope for first delivery** unless we already have broadcast frames. | P4 (Stretch) |
| 6 | Tennis CV / homography pipeline (player tracking + speed in meters from broadcast) | Hawkeye-level analysis | varies | The brief named a `zostaff/tennis…` repo we couldn't resolve; the closest matches by description are [abdullahtarek/tennis_analysis](https://github.com/abdullahtarek/tennis_analysis) and [SaadAbdElGhaffar/tennis-analysis-system](https://github.com/SaadAbdElGhaffar/tennis-analysis-system). YOLO + ResNet50 keypoints + homography. **Same scope as #5; defer.** | P4 (Stretch) |
| 7 | [Polymarket CLOB API](https://docs.polymarket.com) | Bookmaker APIs | Public read | **Already integrated for crypto** ([predictions/POLYMARKET_INTEGRATION.md](../predictions/POLYMARKET_INTEGRATION.md), [alpha_engine/polymarket_signals.py](../alpha_engine/polymarket_signals.py)). Tennis Grand Slams are a known PM market — extend the existing scraper, do **not** add a parallel one. | P3 (Live) |

**Licensing reality.** Sackmann's three datasets are CC-BY-NC-SA 4.0 — non-commercial.
Our paper-trading mode is fine; any switch to real-money would require either a
commercial agreement with Sackmann or an alternative source. This matches the
existing "100+ settled bets, paper-only until then" honesty banner on
`live-monitor/sports-betting.html` — no change in posture.

---

## 2. What's already in place (and it's a lot)

We are not greenfielding. The tennis vertical reuses:

- **Sport keys** — `tennis_atp` + `tennis_wta` already in
  [`live-monitor/api/sports_odds.php:44-45`](../live-monitor/api/sports_odds.php).
  Filters, dashboard cards, pick history queries all accept these out of the box.
- **Auto-place policy v2** — [`config/auto_place_policy.json`](../config/auto_place_policy.json)
  takes a per-sport block. Tennis enters with `pause: true` until ≥30 settled bets
  per (tier, sport) cell, mirroring the MLS posture today.
- **Deploy gate** — [`tools/deploy_sports_files.sh`](../tools/deploy_sports_files.sh)
  + the hourly `sports-smoke-and-e2e.yml` drift guard already cover any new
  `live-monitor/*.{html,js,php}` we touch.
- **Polymarket scraper** — [`predictions/scrapers/polymarket_scraper.py`](../predictions/scrapers/polymarket_scraper.py)
  + [`alpha_engine/polymarket_signals.py`](../alpha_engine/polymarket_signals.py)
  filter for "crypto-related" today; we add a `sport_tennis` filter, not a new file.
- **GHA snapshot pipeline** — `.github/workflows/sports-data-snapshots.yml`
  runs `*/15min` and uploads JSON via FTP. New tennis snapshot job slots in
  alongside Pinnacle + NHL goalie.
- **Backtest harness** — [`live-monitor/sportsbetting_lib/backtest_runner.py`](../live-monitor/sportsbetting_lib/backtest_runner.py)
  is the existing devig+EV retro-runner. It accepts any sport via `--sports`;
  we add `tennis_atp,tennis_wta` once tennis odds rows exist.

---

## 3. Proposed phasing

Each phase is a separately-reviewable PR. Every new module names its production
caller in the PR body so the Wire-Up Rule is satisfied at merge time.

### Phase 1 — Data backfill (S, low-risk, additive only)

**Goal.** Land Sackmann ATP+WTA history into a queryable sidecar so model
features can be computed offline.

| New file | Production caller (wire-up) |
|---|---|
| `tools/tennis_sackmann_backfill.py` | Cron-invoked from `.github/workflows/sports-data-snapshots.yml` (new step `tennis_sackmann_backfill`, gated to weekly Sundays). Writes `data/tennis/atp_matches_*.csv` + `data/tennis/wta_matches_*.csv`. |
| `live-monitor/sql/tennis_schema.sql` | Idempotent `CREATE TABLE IF NOT EXISTS lm_tennis_matches`, `lm_tennis_players`, `lm_tennis_rankings`. Applied via phpMyAdmin (same operator path as `sports_plan_migrations_v2.sql`). |
| `live-monitor/tennis_results_loader.py` | Triggered from the same GHA step; loads CSV → MySQL via `sports_value_analyze_cli.php`-style code-gen (matches existing pattern, no Python MySQL deps). |

**Acceptance.** `SELECT COUNT(*) FROM lm_tennis_matches` returns ≥800k rows
(ATP since '68 + WTA since '84). Smoke test: `pytest -k tennis_backfill` passes
in CI.

**Effort:** S (≤3h). **Risk:** Low (read-only, sidecar tables).

### Phase 2 — Pre-match + in-match models (M, opt-in sidecar)

**Goal.** Produce a `p_win` for any upcoming ATP/WTA match using ELO + 12-month
serve/return percentages, backed by jgollub1's published methodology.

| New file | Production caller (wire-up) |
|---|---|
| `alpha_engine/tennis_elo.py` | Called from new `tools/tennis_score_picks.py` (cron) which writes scores into `lm_sports_value_bets` for any tennis odds row. |
| `alpha_engine/tennis_serve_return.py` | Same caller. Computes serve-hold% and break% over a 12-month rolling window per player. |
| `alpha_engine/tennis_in_match.py` | Loaded by `live-monitor/api/sports_value_analyze_lib.php` only when `live_score` is present (Polymarket bid moves mid-match). Off by default behind `feature_flag: tennis.in_match_model`. |
| `tests/test_tennis_elo.py` | Reproduces three example matches from the jgollub1 README within ±2 percentage-points to lock parity. |

**Wire-up sentinel.** PR body must be able to answer YES to:
```
grep -rln "from alpha_engine\.tennis_elo\|import tennis_elo" \
    audit_trail/ alpha_engine/ tools/ live-monitor/
```
…with at least one hit in `tools/tennis_score_picks.py`. If only `tests/`
hits, the PR is breadth-only and gets closed per the Wire-Up Rule.

**Effort:** M (full day). **Risk:** Low — sidecar; no change to existing scoring path.

### Phase 3 — Live picks, end-to-end (M, behind feature flag)

**Goal.** Tennis picks appear on `sports-betting.html`, settle automatically,
flow into the Performance tab tier × sport matrix.

Concrete deliverables:

1. **Odds source.** The Odds API (paid tier — already gated as Tier-1 op #3 in
   `2026-04-26-sports-next-steps.md`) returns `tennis_atp` and `tennis_wta` h2h
   markets. Existing `sports-betting-refresh.yml` rotation just needs the two
   sport keys added.
2. **Polymarket overlay.** Extend
   [`predictions/scrapers/polymarket_scraper.py`](../predictions/scrapers/polymarket_scraper.py)
   filter to include tennis. Reuse the existing
   [`alpha_engine/polymarket_merger.py`](../alpha_engine/polymarket_merger.py)
   to compute `pm_implied_prob` per match. Same "PM ✓ XX%" pill currently shown
   on NBA/NHL cards, no new UI primitive.
3. **Auto-place gate.** Add to `config/auto_place_policy.json`:
   ```json
   "tennis_atp": {
     "min_ev_pct": 99.0,
     "require_recommendation_in": ["STRONG TAKE"],
     "pause": true,
     "comment": "New sport. Manual review until ≥30 settled bets per tier."
   }
   ```
   Same posture as MLS today. Operator flips `pause: false` after data accrues.
4. **Settlement.** Reuse
   [`live-monitor/sportsbetting_lib/backtest_runner.py`](../live-monitor/sportsbetting_lib/backtest_runner.py)
   pattern + The Odds API `/scores` endpoint. No new settlement code.

**Effort:** M (full day). **Risk:** Medium — touches the live picks list, but
the `pause: true` gate keeps any auto-place blast radius at zero.

### Phase 4 — Computer-vision sidecar (XL, **explicitly out of scope for first PR**)

The CV repos (#5, #6) are excellent but solve a problem we don't have:
**we don't ingest broadcast video.** Without a frame source, TrackNet + court
keypoints + CatBoost bounce prediction are inert. Three honest options:

- **A. Defer indefinitely.** Tag the modules as "P4 stretch" in this doc and
  ignore until a frame-source initiative starts.
- **B. Build the stretch sidecar opt-in.** Wire up under
  `tools/tennis_cv_sandbox/` with a clear `## Wiring Plan` in any PR (per
  Wire-Up Rule). Production callers: zero by design; the goal is an offline
  notebook for ad-hoc match review, not a live signal.
- **C. Partner with a broadcast-feed source.** Out of scope for engineering.

**Recommendation: A for now, B if curiosity outweighs effort.**

---

## 4. First-PR scope (suggested, smallest useful slice)

Land Phase 1 only. One PR, one commit pattern, low risk:

1. `tools/tennis_sackmann_backfill.py` (new, ≤200 LOC).
2. `live-monitor/sql/tennis_schema.sql` (new, idempotent CREATE TABLEs).
3. `live-monitor/tennis_results_loader.py` (new, code-gen for SQL inserts).
4. `.github/workflows/sports-data-snapshots.yml` (extend with weekly Sunday step).
5. `tests/test_tennis_backfill.py` (asserts CSV → DataFrame parse + row counts).
6. `requirements-sports-extra.txt` (add `pandas` if not present; nothing else).

**Rolling out.** No FTP deploy needed (no `live-monitor/*.{html,js,php}` changes).
Running on schedule writes data only. Phase 2 and 3 PRs follow once Phase 1 is
in production for ≥1 weekly cycle.

---

## 5. Risks + things explicitly NOT proposed

- **Real-money tennis.** Same paper-only posture as the rest of the stack;
  100+ settled bets minimum, then real-money flag flip is an operator decision.
- **Sackmann commercial use.** CC-BY-NC-SA prevents real-money launch on this
  data alone. Document attribution in `data/tennis/README.md`.
- **The Odds API tennis quota.** Tennis is a heavy sport-key (many concurrent
  matches at Slams). Confirm the paid-tier $20/mo tier covers it before Phase 3
  ships.
- **Live in-match priors.** jgollub1's in-match model is the holy grail but
  needs live point-by-point data, which The Odds API does not provide. Either
  scrape the four Slam sites (Sackmann's pattern) — reasonable but operationally
  fragile — or accept "pre-match only" for v1. **Recommended: pre-match only
  for v1.**
- **CV pipeline.** Defer per Phase 4.A. Building it without a frame source
  produces orphan modules — exactly the failure mode the Wire-Up Rule was
  written to prevent (`reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md`).

---

## 6. What this PR does

This PR adds **only this document**. No code changes, no schema changes, no CI
changes. It is the design artifact you can comment on, redirect, or reject
before any of the four phases lands.

If approved, the natural next step is the Phase-1 PR described in §4.

---

## Sources

- [JeffSackmann/tennis_atp](https://github.com/JeffSackmann/tennis_atp)
- [JeffSackmann/tennis_slam_pointbypoint](https://github.com/JeffSackmann/tennis_slam_pointbypoint)
- [JeffSackmann/tennis_MatchChartingProject](https://github.com/JeffSackmann/tennis_MatchChartingProject)
- [jgollub1/tennis_match_prediction](https://github.com/jgollub1/tennis_match_prediction)
- [yastrebksv/TennisProject](https://github.com/yastrebksv/TennisProject)
- [yastrebksv/TennisCourtDetector](https://github.com/yastrebksv/TennisCourtDetector)
- [abdullahtarek/tennis_analysis](https://github.com/abdullahtarek/tennis_analysis) (closest match for the unresolved `zostaff/tennis…` reference)
- [SaadAbdElGhaffar/tennis-analysis-system](https://github.com/SaadAbdElGhaffar/tennis-analysis-system) (alt CV reference)
- [Polymarket CLOB Endpoints](https://docs.polymarket.com/quickstart/reference/endpoints)
- [Polymarket py-clob-client](https://github.com/Polymarket/py-clob-client)
