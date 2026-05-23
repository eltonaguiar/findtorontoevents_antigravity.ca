# Sports-Betting & Events WIP — 2026-04-26 04:05 UTC

End-of-session inventory after a multi-hour autonomous round. **20 PRs merged**, all currently-deployed code green via smoke + Playwright + hourly drift CI. This doc is the durable hand-off so the next agent / operator picks up cleanly.

## Session totals

| Metric | Value |
|---|---|
| PRs merged this session | 20 (#401–#410, #412–#415, #417, #420, #422–#426, #429) |
| Production outages caused | 4 (all detected + fixed within 5 min) |
| FTP deploys | 8 individual + 1 backfill of 90 stale update docs |
| Tests added | 6 pytest smoke + 5 Playwright (× 4 device profiles = 20 cases) |
| Remote agents scheduled | 3 (DB-fix verifier 2026-05-09, sweep verifier 2026-05-10, weekly sports-pick verifier Mondays) |

## Steps completed

### Tier 1 — Foundational fixes (operator-grade improvements)
- [x] **#401 Pinnacle Shin devig** — sharper anchor than proportional inverse-normalize; falls back to multiplicative on numerical degeneracy. Wires up the orphan `tools/pinnacle_anchor_scrape.py`.
- [x] **#402 grade_manual + lookback_days + totals fallback** — admin endpoint to settle stuck tickets when The Odds API `/scores` returns empty. Cleared the Apr 6–25 backlog (+$71 PnL).
- [x] **#404 DB audit + FINISHED filter** — server-side `is_finished` boolean + colored W/L/P/V pills, hidden by default with toggle.
- [x] **#412 Hotfix conflict-marker recovery** — PR #399 squash committed unresolved conflict markers; production 500 fixed within 5 min.
- [x] **#417 pick_history bets-fallback fix** — `COALESCE(NULLIF(game_date, '0000-00-00'), LEFT(commence_time, 10))` — bets fallback was never firing because '0000-00-00' isn't NULL. Empty Pick History → 18 days post-fix.
- [x] **#429 AWAITING GRADE pill (DeepSeek B1 fix)** — picks past commence_time but ungraded now show amber 'AWAITING GRADE' instead of misleading grey 'FINISHED' with no W/L color.

### Tier 2 — Edge-detection plumbing
- [x] **#403 NHL goalie scraper Phase 1** — Python sidecar pulls confirmed starters + GSAx/SV% to `data/nhl_goalies_today.json`.
- [x] **#406 Mercury PR 1** — `lm_sports_odds_history` table + steam-move detector + 2-leg arb scanner + WNBA filter button.
- [x] **#413 Kalshi sports adapter** — `tools/kalshi_sports_fetch.py` + verifier; pulls 273 markets across 24 series from `api.elections.kalshi.com` (no auth).
- [x] **#415 NHL goalie overlay Phase 2** — PHP lib + analyzer hook adjusts NHL h2h `true_prob` by goalie GSAx delta with hard ±5pp cap.
- [x] **#420 Sport-specific auto-place policy v2** — `config/auto_place_policy.json` + loader. **enabled: false by default** (operator flips to activate).

### Tier 3 — UI / analytics
- [x] **#409 Tier × Sport ROI matrix** — heat-mapped grid on Performance tab.
- [x] **#414 CLV trend chart + sport-gate evidence panel** — 12-week CLV time series + actionable sport-specific gate recommendations.
- [x] **#426 Wilson 95% CI on tier × sport cells** — surfaces small-sample reality (NBA STRONG TAKE n=3 → "WR 100% [30-100]").

### Tier 4 — Tooling / hardening
- [x] **#405 Polymarket whale validator stub** — `tools/polymarket_whale_validate.py` + 5-wallet seed (placeholder addresses).
- [x] **#407 Shin devig backtest harness** — first run inconclusive at n=6; rerun gated on cron data accumulation.
- [x] **#410 GHA workflow `sports-data-snapshots.yml`** — replaces host crons (50webs has no shell). */15min Pinnacle scrape + daily NHL goalie + steam/arb HTTP triggers + FTP-upload + snapshot pruning.
- [x] **#422 CI smoke + Playwright + hourly drift guard** — pytest 6/6 + Playwright 5/5 across 4 device profiles + SHA-256 git-vs-FTP drift check on 11 sports files.
- [x] **#423 `tools/deploy_sports_files.sh` + CLAUDE.md sequencing rule** — one-command deploy with pre+post smoke gate.
- [x] **#425 Deploy helper covers `updates/*.md` + `index.html`** — caught 90 stale doc files in real-world test.
- [x] **#429 CI auto-comment with last-known-good revert command** — cuts MTTR on the next regression.

### Tier 5 — Documentation
- [x] **#408 Sports betting improvements doc** — verifiable-vs-expected audit of state.
- [x] **#424 Next-steps roadmap doc** — `updates/2026-04-26-sports-next-steps.md` + dated entry on the updates page.
- [x] **DeepSeek + Cerebras review** — saved at `reports/consult_deepseek_20260426T035325Z_*.md` and `reports/consult_cerebras_20260426T035310Z.md`. DeepSeek B1 confirmed live + fixed in #429; B2/B3 false positives. Cerebras gpt-oss-120b returned hallucinated specifics; concerns directionally right but evidence fabricated.

## Remaining — operator-gated (cannot be progressed autonomously)

### Tier 1 ops (the highest-ROI moves all live here)
1. **Activate sport-specific auto-place policy v2** — flip `enabled: true` in `config/auto_place_policy.json`, run `tools/deploy_sports_files.sh`. ~1 min total. Live data backs the rules: NBA TAKE +55%, NHL STRONG TAKE −100%, MLS all-red.
2. **Apply 2 SQL migrations via phpMyAdmin** — `live-monitor/sql/sports_plan_migrations_v2.sql` (10 idempotent CREATE TABLE incl. `lm_sports_odds_history`) + `reports/sql_migrations/2026_04_25_sportsbet_fixes.sql` (DB audit fixes). ~5 min each.
3. **Subscribe The Odds API $20/mo paid tier** — current free tier (500 calls/mo, 17.2% used) can't drive 1-min refresh; paid tier is the foundational unblock for steam/RLM/arb detection. Single arb capture pays months.
4. **Capture 5 Polymarket wallet addresses** — manually visit `polymarket.com/profile/<addr>` for Swiss Tony / HyperLiquid0xb / ColdMath / RN1 / distinct-baguette; populate `data/polymarket_whale_seed.json`. Polymarket has no public username search.
5. **Re-title + merge PR #397** — title says "Sports Betting Edge Detection" but body is "Policy v3 / asset_class / 186 tests" upgrade. Re-title to match body; CI all-green; safe to merge.
6. **Split-or-flag-merge PR #400** — +5999/-617 over 13 commits. Triage report recommends splitting into PR-400a (PM sync only), PR-400b (arb scanner + situational, feature-flagged), PR-400c (sports_edge_finder rewrite, requires staging validation). Merging as-is is acceptable if all new orchestrators stay flag-disabled.

### Pre-existing security concerns (worth hardening before any real-money mode)
- **`grade_manual` static key (`livetrader2026`)** — DeepSeek + Cerebras both flagged. No IP allowlist, no rate limit, no HMAC. Trivially exploitable if the key leaks via log / error message / client JS. Defer until real-money flips on; keep paper-only mode.

## Areas of improvement — autonomous-actionable next round

In priority order (highest ROI first), can ship without operator action:

| Item | Effort | Risk | Benefit |
|---|---|---|---|
| **2.6 Per-bookmaker tier breakdown** | M (half-day) | Low | DeepSeek's #1 "ship now" recommendation. Identifies which book gives best lines per (sport, tier) cell. Pure SQL aggregation on existing `bookmaker_key`. |
| **2.3 Kalshi UI surface (Phase 2)** | M | Low | Free tier of Kalshi data-api already works. PHP reader + "K ✓ XX%" pill mirroring PM badge gives independent triangulation on h2h fights. DeepSeek noted: needs a `kalshi_implied` DB column — gated on operator action #2 above. |
| **Per-sport PM badge threshold** | S | Low | Replace the single 3pp gate with per-sport thresholds in a JSON config (mirror of `auto_place_policy.json`). DeepSeek + Cerebras both flagged this. |
| **Goalie scraper failure-mode fallback** | S | Medium | Currently NHL auto-place deadlocks if goalie scraper down 24h. Add "use last-known-good overlay (≤7d old)" or "skip overlay, place at original p" fallback. Behavioral change — needs careful gate. |
| **Pinnacle Shin fallback logging** | S | Low | DeepSeek's D-tier finding: silent fallback to proportional masks failures. Add a `shin_fallback_count` counter + nightly log. |
| **Goalie Phase 3 A/B columns** | M | Low | Add `goalie_overlay_applied` + `goalie_shift_pp` columns to `lm_sports_bets` (gated on operator's phpMyAdmin step). Then the Performance tab can split goalie-cohort vs non-cohort PnL. |

## Known caveats / things explicitly NOT done

- **Real-money execution** — out of scope. 100+ settled bets needed; current paper count is ~41. Honesty banner stays.
- **NBA series Monte Carlo wiring** — code exists (`tools/nba_series_simulator.py`); gated on 4 weeks of post-Shin CLV trend before relying on upstream `p`.
- **Domain-specialized NHL/NBA models** — needs ≥200 settled bets per sport; we're at ~41 across all sports.
- **Dixon-Coles for soccer** — `penaltyblog` is in `requirements.txt` but never wired. Same n problem.
- **WNBA / CS2 niche pilots** — gated on Odds API paid tier (refresh frequency).

## Production verification commands

```bash
# Smoke (1.5s)
python3 -m pytest tests/test_sports_endpoints_smoke.py -v

# Playwright (~20s)
npx playwright test tests/sports_betting_js_errors.spec.js --project='Desktop Chrome'

# Live API check
curl -s https://findtorontoevents.ca/live-monitor/api/sports_picks.php?action=today | jq '.value_bet_count'
curl -s https://findtorontoevents.ca/live-monitor/api/sports_bets.php?action=dashboard | jq '.by_recommendation_sport[0]'

# Drift check (manually trigger CI)
gh workflow run sports-smoke-and-e2e.yml

# One-command FTP redeploy
tools/deploy_sports_files.sh                  # diff + upload + verify
tools/deploy_sports_files.sh --dry-run        # show diff only
```

## File map for the next agent

- **Active config** — `config/auto_place_policy.json` (sport-specific gate, currently disabled)
- **Endpoint contract** — `live-monitor/api/sports_picks.php`, `sports_bets.php`, `sports_ml.php`, `sports_steam.php`, `sports_arb.php`
- **Hotpath analyzer** — `live-monitor/api/sports_value_analyze_lib.php` (Shin devig, NHL goalie hook)
- **Test gates** — `tests/test_sports_endpoints_smoke.py`, `tests/sports_betting_js_errors.spec.js`
- **CI** — `.github/workflows/sports-smoke-and-e2e.yml` + `.github/workflows/sports-data-snapshots.yml`
- **Deploy helper** — `tools/deploy_sports_files.sh`
- **Documents** — `updates/2026-04-26-sports-betting-improvements.md` (state), `updates/2026-04-26-sports-next-steps.md` (roadmap)
- **Reviews** — `reports/consult_deepseek_20260426T035325Z_*.md` (real findings), `reports/consult_cerebras_20260426T035310Z.md` (mostly hallucinated, treat as concern list not bug list)
