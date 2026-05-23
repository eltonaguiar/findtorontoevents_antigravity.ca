# Sports Betting Edge Integration — Findings & Suggested Fixes

Date: 2026-04-26
Scope: `https://findtorontoevents.ca/live-monitor/sports-betting.html`,
       `https://www.olg.ca/en/sports/prolineplus.html#home`,
       `https://betway.com/g/en-ca/sports`

## TL;DR

The pipeline already has most of the heavy machinery in place:

- Multi-book consensus de-vig (`live-monitor/api/sports_value_analyze_lib.php` —
  Jensen-corrected `E[1/price]` + Pinnacle anchor when present).
- ON-licensed book scrapers feeding `lm_sports_odds`
  (`olg_prolineplus_scraper.py`, `betway_ca_scraper.py` — both Playwright,
  both wired into `.github/workflows/sports-betting-refresh.yml`).
- A Polymarket sports-market bridge written but **not yet scheduled** in CI
  (`prediction_market_agents/sports_prediction_market_bridge.py`).
- PM data attached to picks server-side **but never displayed to the user** and
  with **zero impact on composite score**, EV%, grade, or recommendation.
- Front-page "STRONG TAKE" (EV >= 10%) picks are rare because per-event book
  count after de-vig hovers around the 3-book threshold; the OLG/Betway
  scrapers are the de-vig anchor that pushes events past it.

This PR lands three minimal-but-high-leverage fixes:

1. **Wire the PM bridge into the scheduled refresh** so the JSON consumed by
   `sports_picks.php` is fresh on every run.
2. **Render a `PM ✓ <conf%>` badge** on each pick card whenever a liquid
   prediction-market signal confirms the side, with a tooltip showing
   confidence, volume, and the matched market question.
3. **Additive composite-score nudge** (capped at +6) when the PM signal is
   high-confidence (>=0.65) and high-volume (>=$25k). EV%, grade, Kelly bet,
   and `recommendation` are intentionally left unchanged — the nudge moves the
   visible composite/sort order, not the underlying pricing model.

The rest of this document is the cross-reference + roadmap for the remaining
edge sources investigated, with concrete file paths so the next iteration is
purely mechanical.

---

## 1. Current pipeline (what's live today)

### 1.1 Data sources feeding `lm_sports_odds`

| Source | Script | Status | Sports |
|---|---|---|---|
| The Odds API (primary) | `live-monitor/api/sports_odds.php` | ✅ Live, every refresh | NBA, NHL, NFL, MLB, MLS, NCAAB |
| OLG ProLine+ (Ontario gov't book) | `live-monitor/olg_prolineplus_scraper.py` | ✅ Live, Playwright, every refresh | NBA, NHL, NFL, MLB |
| Betway CA (ON-licensed) | `live-monitor/betway_ca_scraper.py` | ✅ Live, Playwright, every refresh | ice-hockey, basketball, american-football, baseball, soccer |
| NFL fallback (`nflreadpy` + ESPN) | `live-monitor/nfl_odds_scraper.py` | ✅ Hot path | NFL |
| NHL enriched (NHL Web API) | `live-monitor/nhl_odds_scraper.py` | ✅ Hot path | NHL |
| CFL fallback (ESPN) | `live-monitor/cfl_odds_scraper.py` | ✅ Hot path (Jun-Nov) | CFL |
| OddsHarvester CLV backfill | `live-monitor/oddsharvester_clv_backfill.py` | ⚠️ Preview only (`--save-json`, no inject) | NBA, NHL, NFL, MLB, soccer |
| sportsdataverse history | `live-monitor/sportsdataverse_backfill.py` | ⚠️ Preview only | All majors |

### 1.2 Edge calculation

`sports_value_analyze_lib.php::sports_value_analyze_run()`:

1. Group quotes by `(event_id, market, outcome)`.
2. Filter unusable quotes (`< 1.02` or `> 80.0` decimal, Betfair, ESPNBet —
   keeps real ESPN scoreboard prices since PR #352).
3. **De-vig**: Pinnacle-only if every outcome has Pinnacle, else Jensen
   consensus (mean of `1/price` across >= 3 usable books, normalized).
4. EV% = `truep * best_price - 1`.
5. Kelly fractional bet sized off `bankroll`.
6. Persisted to `lm_sports_value_bets` and `lm_sports_daily_picks`.

### 1.3 Recommendation tiers (`sports_ev_to_rec`)

`STRONG TAKE` >=10% · `TAKE` >=6% · `LEAN` >=3% · `LOW EDGE` >=1% · `SKIP` <1%.

### 1.4 Prediction-market overlay (already partially built)

`live-monitor/api/sports_picks.php::sports_action_today()` loads
`sports_prediction_market_signals.json` (written by the bridge), fuzzy-matches
home/away to PM market questions, and attaches `prediction_market_*` fields
to each value bet. **Until this PR**: those fields were not rendered on the
frontend and did not influence ordering/score.

---

## 2. Cross-reference vs. published methodology

The investigation walked through the methodologies most-cited in the
sports-handicapping literature and the `2026-04-25` internal research doc, and
mapped each one onto where it would land in this codebase.

### 2.1 Closing-Line Value (CLV) — sports betting's only widely-respected
predictor of long-term ROI

**Method**: track the consensus odds at first detection vs. closing, and use
positive movement against you (book moved against your bet) as proof of edge.
A bettor who consistently beats the closing line ~+2% on average is generally
considered profitable.

**Where we already are**: `lm_sports_odds` retains `detected_at` and re-inserts
on price change, so the historical ladder per `(event, book, outcome)` exists.
`oddsharvester_clv_backfill.py` writes per-day JSON snapshots.

**Gap**: nothing reads them at pick time. The dashboard reports EV at *open*,
not CLV at close.

**Suggested fix** (next PR, not this one):
- Add `live-monitor/api/sports_clv.php?action=clv_for_event` that, given an
  `event_id`, returns `{ open_price, close_price, clv_pct, books_used }`
  using a windowed query over `lm_sports_odds`.
- Surface a `CLV +X.X%` badge on each settled pick in
  `Pick History` (already a tab on `sports-betting.html`).
- Add a daily aggregate: median CLV per `algorithm_name`/per sport — a hard
  floor of `+1%` after n>=20 should be a kill-switch criterion (cf. how
  `audit_dashboard` does this for crypto algos via `edge_finder.php`).

### 2.2 Sharp-book divergence (Pinnacle / OLG ProLine+ vs. the field)

**Method**: ON-licensed retail books (FanDuel, BetMGM, ESPN Bet) shade lines
toward public action; sharp books (Pinnacle, increasingly OLG ProLine+ for
Canadian-team markets where ON action is the deepest pool) move first. A line
where the sharp book disagrees with consensus by >= 8 cents (decimal) is a
classic signal.

**Where we already are**: ProLine+ and Betway prices are already in
`lm_sports_odds`, so a divergence query is just SQL.

**Gap**: no code computes `pinnacle_price - consensus_price` or
`olg_prolineplus_price - consensus_price` per outcome.

**Suggested fix** (next PR):
- New helper in `sports_value_analyze_lib.php`:
  `sports_value_sharp_divergence($outList) -> ['olg' => -0.06, 'pinnacle' => +0.03]`.
- Persist the per-outcome divergence on `lm_sports_value_bets` (new column
  `sharp_div_pct DECIMAL(6,3)`).
- Front-end: `SHARP DIVERGE` badge when `abs(div) >= 0.05`, color-coded for
  side agreement vs. side disagreement with our pick.
- Same data feeds an alert: when ProLine+ moves 5%+ within 60 min and we have
  a pick on that side, ping `goldmine-alerts.html` like the crypto pipeline
  does.

### 2.3 Per-sport methodology cross-reference

| Sport | Edge methodology | Already used | Gap → fix |
|---|---|---|---|
| **NBA** | Pace-adjusted PPG vs. `opp_ppg`, B2B/rest delta, road-trip leg, injury reports | Stats fetched (`nba_stats.php`, `schedule_intel.php`, `injury_intel.php`) and rendered on the pick card | Stats are display-only; not yet folded back into a per-team prior to compare against the de-vig probability. Next: build a per-team rolling Elo (cf. `penaltyblog`) and treat large `Elo_p - consensus_p` divergence as a flag. |
| **NHL** | Goalie confirmed start, PP%/PK%, GF/GA pace, B2B fatigue, totals shaded by ref crew | Rendered on card. Pinnacle anchor used in de-vig when present. | Goalie confirmation is **not** in our data. The most reliable NHL edge is a same-day goalie swap; need to scrape DailyFaceoff confirmed lineups and tag the pick if our outcome side flips. |
| **NFL** | Turnover margin, line vs. key numbers (3, 7, 10), home/away ATS, weather (wind > 15 mph) | TO margin + record on card. `live-monitor/sports-betting.html` flags `KEY#` near key numbers (line 1620). | Weather is missing. ESPN scoreboard exposes `weather` block on the event endpoint — already fetched by other scripts. Add it to `sports_failover_proxy.php` cache and surface as `WIND 18mph` badge for totals. |
| **MLB** | Starting pitcher xFIP/SIERA vs. opponent wOBA, bullpen rest, park factor, umpire K%/BB% | ERA + record only on card. | Starter ERA is the noisiest pitcher metric. Switch to a pulled-from-FanGraphs `xERA`/`SIERA` (FanGraphs allows manual export) cached daily. Park factor + umpire data is `pybaseball`-ready (already wrapped by `sportsdataverse_backfill.py`). |
| **MLS / soccer** | Expected goals (xG) rolling 6, home/away split, draw frequency by clock, fixture congestion | None of the above wired. The `2026-04-25-sports-quality-analysis.md` doc shows **100% void rate on MLS** because score-matching is broken on `soccer_usa_mls` — fix that **first**. | (1) Pause MLS picks until the score endpoint mismatch is resolved. (2) When re-enabled, pull xG from understat/fbref via the `sportsdataverse` Python package (it supports soccer leagues). |
| **NCAAB** | KenPom AdjEM (offense/defense efficiency margin), Bart Torvik factors, rest delta | None wired. Current sample WR 16.67% (n=6) is below random. | Pause NCAAB picks (`is_paused` flag in sport config) until AdjEM-based prior is computed. |

### 2.4 Prediction-market communities & markets reviewed

| Source | Method of edge | Reachable? | Wired? |
|---|---|---|---|
| **Polymarket** (Gamma API) | Crowd-funded probability + whale tracking; sports markets growing | ✅ Public REST | ✅ as of this PR (bridge runs in CI; PM badge surfaces on pick cards) |
| **Kalshi** | CFTC-regulated event contracts; sports volume thin but rising | ✅ REST + WS, agent at `prediction_market_agents/kalshi_signal_agent.py` | ⚠️ Module exists; no sports-specific feed yet. Mirror the Polymarket bridge for Kalshi sports markets. |
| **Betfair Exchange** | Highest liquidity globally for sports; true odds | ❌ Geo-blocked from Canada/US; needs rotating EU residential proxy | ❌ Not wired. Roadmap-only. |
| **r/sportsbook NLP signals** | Crowd sentiment | Web-scrape only | ❌ Not in scope; very noisy. |
| **Public capper consensus** (Action Network public-betting %) | Fade-the-public on >70% public side with line moving the other way | ✅ Public scrape via Action Network odds page | ❌ Worth a future scraper; pairs naturally with sharp-divergence signal from §2.2. |

### 2.5 Open-source ML frameworks evaluated (from the 2026-04-25 research)

The research doc did the long write-up — see
`updates/2026-04-25-sports-betting-signal-sources-research.md`. Distilled
priority for *this* repo (which already has its own ML stack in
`alpha_engine/`):

1. **`georgedouzas/sports-betting`** (pip install) — drop-in backtester. Wire
   it under `live-monitor/sportsbetting_lib/backtest_runner.py` so historical
   `lm_sports_odds_historical` rows can be replayed with `--strategy=...` and
   benchmarked against our current picks.
2. **`martineastwood/penaltyblog`** — Elo + Bradley-Terry for soccer. Treat
   it as the per-team prior for §2.3.
3. **`kyleskom/NBA-Machine-Learning-Sports-Betting`** — XGBoost reference
   architecture for NBA spreads. Worth porting feature-engineering only; the
   training data pipeline is too NBA-specific to adopt wholesale.

---

## 3. Concrete changes landed in this PR

### 3.1 `prediction_market_agents/sports_prediction_market_bridge.py` runs in CI

`.github/workflows/sports-betting-refresh.yml` now invokes the bridge after
the OLG line-comparison check and before the daily-picks snapshot, with
`continue-on-error: true` so a Polymarket Gamma API outage cannot block
picks. The bridge has been in the repo since 2026-04-24 and writes only
JSON; no DB writes, no schema changes.

Both consumer paths in `sports_picks.php` (`action=today` and `action=live`)
already load
`live-monitor/backfill/sports_prediction_market_signals.json` if present, so
the JSON now refreshes on every cron tick instead of being written once and
going stale.

### 3.2 PM-confirmed badge in `sports-betting.html`

Renders next to the existing `+EV` badge whenever
`b.prediction_market_source` is set on the pick:

```
[PM ✓ 78%]  ← purple chip; hover shows "Prediction market (polymarket)
              confirms this side: 78% confidence at $142,500 volume.
              Composite +6. Market: Will Lakers beat Nuggets?"
```

The badge is purely informational — sort order is unchanged unless the
composite-score nudge in §3.3 also fires.

### 3.3 Conservative composite-score nudge in `sports_picks.php`

When a pick is matched to a PM market, the existing `composite_score` is
nudged additively by:

| PM confidence | PM volume USD | Nudge |
|---|---|---|
| >= 0.60 | >= $5k | +2 |
| >= 0.65 | >= $25k | +4 |
| >= 0.70 | >= $100k | +6 |

Caps at 100. EV%, `rating_grade`, `recommendation`, and `kelly_bet` are
**unchanged** — this PR is explicitly not changing the betting model, only
how the front-end weighs the visible "Composite" sort field.

The new field `prediction_market_score_boost` is added to the pick payload
when the nudge fires, so future tooling can audit it.

---

## 4. Why this is non-breaking

- All PM file loads are `@file_get_contents` + `@json_decode` and silently
  skipped if absent (already true before this PR; not changed).
- The badge JS gates on `b.prediction_market_source` truthiness. Existing
  picks without PM data render identically.
- Composite-score nudge runs *only* inside the existing
  `if (is_array($pm))` blocks, with the same `prediction_market_*` payload
  already shipped on 2026-04-24. No new request, no new query.
- The workflow step is `continue-on-error: true`. A Polymarket Gamma API 5xx
  cannot block daily picks.

---

## 5. Verification

- `php -l live-monitor/api/sports_picks.php` → no syntax errors.
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/sports-betting-refresh.yml'))"` → parses clean.
- `python3 -m py_compile prediction_market_agents/sports_prediction_market_bridge.py` → clean.
- Inline JS in `live-monitor/sports-betting.html` extracted with `re.findall`
  and validated with `node --check` → "JS syntax OK".
- Schema-affecting changes: **none**.
- New runtime calls outside the workflow: **none** (PM JSON is read by
  `sports_picks.php` exactly as it was in 2026-04-24's PR, just refreshed
  more often).

---

## 6. Roadmap (next PRs, in priority order)

1. **Sharp-divergence signal (§2.2)** — `sharp_div_pct` column on
   `lm_sports_value_bets` + `SHARP DIVERGE` badge. Highest-leverage edge
   piece given OLG/Betway prices are already in the DB. Ticket size: ~120
   LoC + one schema migration.
2. **CLV tracking (§2.1)** — `sports_clv.php` endpoint + CLV column on
   `Pick History` rows. Required for the kill-switch criterion below.
3. **Per-algorithm kill-switch** — extend `edge_finder.php` semantics
   (currently crypto-only) to per-sport and per-strategy CLV. Auto-pause any
   strategy whose 30-day median CLV < +0.5% after n>=20.
4. **MLS / NCAAB pause flag** — `is_paused` per sport in
   `lm_sports_value_bets` analyzer config. Prevents the void-pollution
   documented in `updates/2026-04-25-sports-quality-analysis.md`.
5. **Goalie confirmation feed (§2.3 NHL row)** — DailyFaceoff scraper or
   the NHL Web API `/club-stats/now` endpoint, surfaced as a `GOALIE FLIP`
   warning on the pick card.
6. **Kalshi sports bridge** — clone of the Polymarket bridge writing the
   same signal-file shape. The PM-match function already accepts
   `signal['source']`, so no consumer change is needed.
7. **OddsHarvester from preview to inject** — the script runs in the
   workflow with `--save-json` only; once the JSON shape has been audited
   for one full week, flip it to `--inject-api` so its closing-line
   snapshots become a fourth de-vig anchor.

Each of items 1, 2, and 4 is explicitly the kind of work the existing
`AGENTS.md` "Wire-Up Rule" mandates: a working caller in the production
pick path, not a sidecar.

---

## 7. References

- Prior research: `updates/2026-04-25-sports-betting-signal-sources-research.md`
- Prior PM overlay (server-side only): `updates/2026-04-24-sports-prediction-market-overlay.md`
- Quality dashboard: `updates/2026-04-25-sports-quality-analysis.md`
- ON-licensed book scrapers: `live-monitor/olg_prolineplus_scraper.py`,
  `live-monitor/betway_ca_scraper.py`
- Edge engine: `live-monitor/api/sports_value_analyze_lib.php`,
  `live-monitor/api/sports_picks.php`
- Frontend: `live-monitor/sports-betting.html`,
  `live-monitor/sports-betting.js`
