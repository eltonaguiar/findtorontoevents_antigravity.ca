# Sports Betting — Next Potential Steps & Benefits

**Authored:** 2026-04-26 03:35 UTC
**Author:** Claude Opus 4.7
**Context:** End-of-session inventory after 13 PRs merged in one autonomous round. All currently-shipped infrastructure is documented in [updates/2026-04-26-sports-betting-improvements.md](2026-04-26-sports-betting-improvements.md). This doc enumerates what's *not* yet shipped, ranked by ROI ÷ effort, with explicit benefits per item so the operator can pick the next round.

## How to read this

- **Effort** = realistic implementation time. "S" = under 1 hour, "M" = half-day, "L" = full day, "XL" = multi-day.
- **Risk** = revertability + production blast radius. "Low" = additive, opt-in. "Medium" = changes a code path. "High" = touches money math or hot-path PHP.
- **Gating** = anything that has to land first.
- **Benefit** is the one-sentence "why bother."

---

## Tier 1 — Operator decisions (zero new code, biggest ROI)

These unblock everything else and require **no engineering** — just a flip + verify.

### 1.1 Activate sport-specific auto-place gate (PR #420 already shipped, disabled)
- **Effort:** S — flip `enabled: true` in `config/auto_place_policy.json`, run `tools/deploy_sports_files.sh`
- **Risk:** Low — rollback is editing one boolean back to `false` (30 sec)
- **Gating:** none
- **Benefit:** Live data shows TAKE +37% ROI vs STRONG TAKE +1.8% globally; tier × sport matrix shows NBA STRONG TAKE +164% but NHL STRONG TAKE −100%. The current global 1.5% EV gate is throwing away signal. Activating the sport-specific gate paused MLS (every tier red) and required goalie overlay for NHL — both directly evidence-based.
- **Validation after:** Watch the `policy_skip_reasons` block in `auto_place` response for the next 7 days. Expected: MLS picks → `sport_paused`; NHL picks without confirmed goalies → `goalie_overlay_required`.

### 1.2 Apply two SQL migrations via phpMyAdmin
- **Effort:** S — copy/paste two files into phpMyAdmin, ~5 min each
- **Risk:** Low for both — both are `IF NOT EXISTS` / additive
- **Gating:** none
- **Files:**
  - `live-monitor/sql/sports_plan_migrations_v2.sql` — creates 10 new tables (lm_sports_odds_history, lm_sports_steam_moves, lm_sports_arbs, lm_predmarket_quotes, lm_event_weather, lm_nhl_goalie_starts, lm_esports_odds, lm_polymarket_wallets, lm_polymarket_positions, etc.)
  - `reports/sql_migrations/2026_04_25_sportsbet_fixes.sql` — DB audit fixes (A2 trim, A5 unique key on daily_picks, A6 prune `lm_sports_value_bets > 30 days`)
- **Benefit:** Steam-move detector and arb scanner currently return `count: 0` because their target tables don't exist yet. Hourly GHA cron fires successfully but writes nowhere. Applying migration v2 unlocks both detectors immediately.

### 1.3 Subscribe The Odds API $20/mo paid tier
- **Effort:** S — ~20 min including key-rotation + env update
- **Risk:** Low — graceful key swap; old key still works for the rest of its quota
- **Gating:** none
- **Benefit:** Free tier = 2–3h refresh, which structurally prevents steam-move detection (a steam move is a 30-sec to 5-min coordinated line shift across books — invisible at 3h cadence). Paid tier = ~1min refresh. **Single arbitrage capture pays months of subscription.** External review (Kimi Swarm) ranked this their #1 recommendation.

### 1.4 Capture 5 Polymarket whale wallet addresses
- **Effort:** S — ~10 min, manually visit each polymarket.com profile, copy the 0x address
- **Risk:** None
- **Gating:** none
- **Wallets to seed** (from Kimi research + Copilot Phase 2.10): Swiss Tony, HyperLiquid0xb, ColdMath, RN1, distinct-baguette
- **Benefit:** `tools/polymarket_whale_validate.py` (PR #405) is shipped and waiting. Once seeded, the validator pulls each wallet's open positions + recent trades on a schedule. Top sports-Polymarket traders specialize narrowly (Swiss Tony soccer underdogs, HyperLiquid0xb $1.4M+ MLB profit) — copying their positions as a *signal layer* (not an execution layer) creates an independent alpha source.

### 1.5 Re-title + merge PR #397 (Policy v3 / 186 tests, all-green CI)
- **Effort:** S — edit title, click merge
- **Risk:** Low — Copilot Cloud already audited; all 186 tests pass; features are config-flagged off by default
- **Gating:** none
- **Benefit:** Unblocks the Policy v3 features (asset_class.py canonical, stat_tests.py, feature_flags.py, alerts.py, policy_backtest.py, daily_report.py, dashboard widget). Currently rotting in a stale PR because the wrong title made multiple agents (myself included) misclassify it.

---

## Tier 2 — Concrete code with measurable wins (1–4h each)

### 2.1 Add Wilson 95% CI alongside every tier × sport ROI cell
- **Effort:** M — backend computes lower/upper bounds; frontend renders as a thin band under the ROI %
- **Risk:** Low — display-only
- **Gating:** none
- **Benefit:** Current tier × sport panel shows NBA STRONG TAKE +164% (n=3). Without a CI, the operator may treat that as a real signal worth scaling up. Wilson lower bound on n=3, 100% WR is ~30% — very different decision. Surfaces the small-sample reality directly in the cell.

### 2.2 CI-failure auto-comment with last-known-good commit
- **Effort:** S — extend the `sports-smoke-and-e2e.yml` failure-comment step
- **Risk:** None — only fires on red CI
- **Benefit:** When smoke tests fail on a PR, the comment currently shows local repro commands. Adding the last-known-good main commit + a one-liner `git revert` lets the operator restore production in 60 seconds without thinking.

### 2.3 Kalshi UI surface (Phase 2 of PR #413)
- **Effort:** M — `tools/kalshi_sports_fetch.py` already shipped; need a PHP reader + a "K ✓ XX%" pill on each pick card mirror of the Polymarket badge
- **Risk:** Low — additive, opt-in; same delta-vs-bookmaker gate the PM badge uses
- **Gating:** PR #413 merged ✅; just needs the UI wire-up
- **Benefit:** Kalshi has CFTC-regulated single-event UFC + NBA contracts that Polymarket doesn't cover. Verifier's first run found 2 NBA picks matching Kalshi `Game N: A at B Winner?` markets at 0.60 confidence overlap — adding a second prediction-market column on each pick gives independent triangulation.

### 2.4 Re-run Shin devig backtest with accumulated `lm_sports_odds_history`
- **Effort:** S — re-run `tools/backtest_shin_devig.py` against the SQL dump after 2 weeks of cron
- **Risk:** None — read-only
- **Gating:** Need n ≥ 20 *settled* (game-completed) Pinnacle-anchored buckets. Realistic window: 2 weeks of */15min cron + at least 1 NBA/NHL playoff round.
- **Benefit:** First-run backtest was inconclusive at n=6 (Shin Brier 0.1975 vs Proportional 0.1981). With ~150 settled buckets after 2 weeks the calibration delta becomes statistically distinguishable. Decides whether Shin keeps shipping or rolls back to multiplicative.

### 2.5 NHL goalie Phase 3 — A/B logging columns + cohort analysis
- **Effort:** M — DB column on `lm_sports_bets` (`goalie_overlay_applied`, `goalie_shift_pp`); pick history dashboard cohort filter
- **Risk:** Low — additive columns, default 0
- **Gating:** PR #415 (Phase 2) merged ✅; need 50+ settled NHL bets after Phase 2 deploy
- **Benefit:** Today the goalie overlay applies to NHL h2h picks but we have no way to compare "goalie-applied" cohort vs "goalie-skipped" cohort PnL. Phase 3 makes the kill-switch decision data-driven.

### 2.6 Per-bookmaker tier breakdown (extension of #409)
- **Effort:** M — same pattern as `by_recommendation_sport`, sliced by `best_book_key`
- **Risk:** Low — display-only
- **Gating:** none
- **Benefit:** Does FanDuel-only TAKE outperform Bovada-only TAKE? Current tier × sport may hide a book-specific bias (e.g., Bovada thinly priced markets producing fake STRONG TAKE picks). Same n problem (compounds), but the directional signal is useful for narrowing future auto-place to specific (sport, book, tier) cells.

---

## Tier 3 — Larger structural improvements (half-day to full day)

### 3.1 Steam-move + reverse-line-movement (RLM) detection (Copilot Phase 1.2)
- **Effort:** L — needs paid Odds API tier first (gating). Code exists in PR #406 (already merged), just blocked on the SQL migration + tier upgrade.
- **Risk:** Medium — bringing latent code online
- **Gating:** Tier 1.2 (SQL migrations) AND Tier 1.3 (Odds API paid tier)
- **Benefit:** Steam moves are sub-minute coordinated line shifts across ≥3 books — historically the strongest sharp-money signal. RLM = line moves opposite to public-betting % (>70% public on side A but line moves toward B). Both produce the highest-conviction picks the system can generate.

### 3.2 NBA series Monte Carlo (zig-zag pricing for playoff series markets)
- **Effort:** L — `tools/nba_series_simulator.py` already exists; needs PHP wiring + a new market type emitter in `sports_picks.php`
- **Risk:** Medium — emits a new market category the auto-place gate doesn't yet cover
- **Gating:** PR #401 (Pinnacle Shin) merged ✅; needs 4 weeks of post-Shin CLV data to validate the upstream `p` is improving before relying on it for a downstream model
- **Benefit:** NBA series-winner markets ("Lakers in 5", "series goes 7") are notably mispriced after Game 1 of each round (zig-zag effect: public over-reacts to single results). Monte-Carloing the remaining series from the current score gives a directly-actionable fair price the books are slow to match.

### 3.3 Cross-platform arbitrage scanner — sportsbook ↔ Polymarket/Kalshi
- **Effort:** L — combine Polymarket Gamma API + Kalshi data-api (both shipped) + sportsbook odds; flag cases where the sum of complementary contract prices < 1.0 across platforms
- **Risk:** Medium — execution would require simultaneous bets at 2+ venues; *signal-only* is low risk
- **Gating:** Tier 1.4 (Polymarket whales seeded) + Kalshi UI surface (Tier 2.3)
- **Benefit:** Pure arbitrage between regulated sportsbooks is rare and fleeting; cross-platform arb (sportsbook vs prediction market) is more durable because the two markets have different liquidity dynamics. Even at signal-only (no auto-execution), surfaces situations where the operator can manually capture risk-free profit.

### 3.4 Domain-specialized NHL + NBA models
- **Effort:** XL — needs ≥200 settled bets per sport before training (currently ≈ 41 across all sports); the CLV-tagged cohort columns from #2.5 are prerequisites for label generation
- **Risk:** High — replaces the current consensus-devig path with a learned predictor
- **Gating:** Multiple sub-deliverables
- **Benefit:** External review (Kimi Swarm) and Copilot both flag this as the highest-ceiling work. Universal ML at n=41 is statistically inactive; sport-specific models at n≥200 outperform consensus devig in published research. Right answer eventually, but premature today.

---

## Tier 4 — Deferred / out-of-scope-this-round

### 4.1 WNBA + CS2 e-sports niche pilots (Copilot Phase 1.5 + 2.9)
- Gated on Odds API paid tier (Tier 1.3) for refresh frequency to make these worth the scrape effort.
- Soft-line argument is real but the sample size at our current scale takes years to validate.

### 4.2 Real-money execution
- Honestly out of scope until 100+ real settled bets and CLV trends positive for ≥4 weeks. Currently neither holds. Paper-only mode is the right default.

### 4.3 Dixon-Coles for NHL/soccer (Copilot Phase 3)
- The penaltyblog library is in `requirements.txt` but never wired. Would replace the consensus devig for NHL/soccer with a Poisson-based goal model. Same gating problem as 3.4: need ≥200 settled bets per sport for calibration.

### 4.4 Promotional calendar tracker
- Bookmaker bonuses can manufacture +EV that a pure odds-comparison engine misses (e.g., FanDuel "first goal scorer" boost). Manual seeding required. Low ROI given current scale.

---

## Recommended sequence

If the operator wants to ship one round per evening:

1. **Tonight:** Tier 1.2 (SQL migrations, 10 min) + Tier 1.3 (Odds API tier, 20 min) + Tier 1.4 (wallet seed, 10 min) + Tier 1.5 (re-title + merge #397, 5 min). **45 minutes total, unblocks everything.**
2. **Day +1:** Tier 1.1 (flip auto-place policy v2 enabled, monitor 24h).
3. **Day +2 to +7:** Tier 2.1 (Wilson CI) + Tier 2.3 (Kalshi UI surface) + Tier 2.5 (goalie A/B columns).
4. **Week +2:** Re-run Tier 2.4 (Shin backtest) with accumulated history. Decide on Shin keep/rollback.
5. **Week +4:** Begin Tier 3.1 (steam/RLM) once Odds API paid tier has produced 4 weeks of dense odds history.
6. **Defer Tier 3.4 + Tier 4** until ≥200 settled bets per sport.

---

## Cross-references

- Currently-shipped state: [updates/2026-04-26-sports-betting-improvements.md](2026-04-26-sports-betting-improvements.md)
- 13-PR merge log: see `git log --oneline main` between 2026-04-25 21:00 UTC and 2026-04-26 03:30 UTC
- Test gate: `.github/workflows/sports-smoke-and-e2e.yml` (every PR + hourly drift check)
- Deploy helper: `tools/deploy_sports_files.sh` (validates pre+post deploy)
- Sport-specific gate config: `config/auto_place_policy.json` (currently `enabled: false`)
