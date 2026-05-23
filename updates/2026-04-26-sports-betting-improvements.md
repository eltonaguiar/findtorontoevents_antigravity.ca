# Sports Betting Improvements — 2026-04-26

> **Status snapshot** at the time of writing. What's *verifiable on production* vs *expected after deploy* is called out per item — no marketing language.

## What's live on findtorontoevents.ca/live-monitor/sports-betting.html *right now*

**Deployed via FTP this session (PR #404 + peer's earlier `grade_manual` work):**

| Improvement | Verifiable proof |
|---|---|
| `is_finished` boolean on every "Today's Picks" row (true if `result IS NOT NULL` OR `commence_time < NOW() − 3h`) | `curl /live-monitor/api/sports_picks.php?action=today` returns `is_finished: true` for every row past 3h |
| FINISHED · WON/LOST/PUSH/VOID coloured pill on each finished card | `data-finished="1"` attribute now in deployed HTML; CSS rule hides them by default |
| "Show finished bets" toggle (persists in `localStorage`) | Toggle bar appears only when finished picks exist; counter shows `(+N finished)` |
| `grade_manual` admin endpoint on `sports_bets.php` + `sports_picks.php` | Apr 6–25 backlog of 14+ pending tickets graded; bankroll moved $1000 → $1071.18 (+$71 net) |
| `lookback_days` SQL fix (default 30, max 120) split from Odds-API `days_from` (≤3) | Settlement no longer ignores tickets older than 3 days; the same backlog clear above is the proof |
| `bet_type → pick_point` regex fallback for backlog totals | 5 NHL Coolbet "Over 5.50" tickets that previously couldn't grade are now reachable by the matcher |
| Multi-book Jensen-corrected devig + Pinnacle anchor (existing) | `sports_picks.php?action=today` shows `EV%`, `composite_score`, `recommendation` per row |

## Polymarket integration — honest audit

**Code that exists in this repo:**

| File | Purpose | State |
|---|---|---|
| `prediction_market_agents/sports_prediction_market_bridge.py` | Fetches sports markets from Polymarket Gamma API, writes a JSON signal file `sports_pm_signals.json` for `sports_picks.php` to read | **Written 2026-04-24, never put on a schedule. Signal file goes stale within hours.** PR #399 (Copilot, **DRAFT**) was supposed to wire it into the `sports-betting-refresh.yml` cron. Not merged. |
| `prediction_market_agents/polymarket_momentum_agent.py` | Polymarket momentum signals (crypto-focused) | Live for crypto picks; not consumed by sports pipeline |
| `prediction_market_agents/polymarket_whale_tracker.py` | Whale-wallet position tracker (crypto-focused) | Live for crypto picks; sports-specific whale tracker is the **#405 stub** (placeholder addresses) |
| `prediction_market_agents/cross_market_consensus.py` | Cross-platform consensus (Polymarket × Kalshi) | Live for crypto/politics; sports markets not yet routed through |
| `tools/polymarket_edge_scan.py` | Polymarket vs sportsbook devig'd consensus comparison; emits a markdown gap report | **Standalone CLI** — runnable (`python tools/polymarket_edge_scan.py --min-gap-pp 4 --sport mma`), not on a cron, not surfaced in the UI |
| `tools/verify_manual_sports_picks.py` (mine, this branch family) | Cross-checks the curated UFC/Tennis/Golf picks against Polymarket Gamma API | **Live, scheduled weekly** (`weekly-sports-pick-verifier-clv-trend` remote agent). Honest finding from first run: most manual picks have **no comparable Polymarket market** — sparse coverage for h2h fights and early-round tennis |
| `tools/polymarket_whale_validate.py` (PR #405) | Address-keyed wallet validator using `data-api.polymarket.com` | **Stub** — addresses are placeholder; operator must capture from `polymarket.com/profile/<addr>` URLs (no public username search) |

**What this means in plain terms:**

> **Polymarket is *plumbed in*, not *integrated*.** We have working clients for the Gamma API (markets) and the data-api (positions/trades). We have a sports-specific bridge module ready. We have a verifier already running weekly. **But the live `sports-betting.html` page does not yet display any Polymarket-derived signal**, because:
>
> 1. The sports bridge cron is not scheduled (PR #399 is the wire-up — DRAFT).
> 2. The composite score in `sports_picks.php?action=today` does not currently include a PM-confirmation nudge (Copilot's PR #399 adds `sports_pm_score_nudge()` — DRAFT).
> 3. The whale-tracker seed file has placeholder addresses (no operator capture yet).

**Verifiable today via the standalone CLI tools** (run on demand):
- `python tools/polymarket_edge_scan.py --sport ufc` → markdown report of UFC moneylines where Polymarket disagrees with the sportsbook consensus by ≥ N pp
- `python tools/verify_manual_sports_picks.py` → markdown report cross-checking the curated UFC/Tennis/Golf picks (the weekly remote agent already runs this and would open a GitHub issue on `polymarket_disagrees_strongly`)

**Not yet verifiable on the live page** (would require operator action):
- "PM-confirmed ✓" pill on each pick card — needs PR #399 merged + FTP-deployed
- Polymarket consensus column on the Odds Comparison tab — needs additional work
- Whale-tracker activity panel — needs PR #405 merged + 5 wallet addresses captured + Phase 2.10 PHP reader

## Other live improvements verifiable today

| Item | Where | Verifiable proof |
|---|---|---|
| CLV tracking with `lm_sports_clv` (10,101 settled events) | `sports_ml.php?action=clv` | Live response: `avg_clv_pct: −1.219, positive_clv_pct: 21.21, total_events: 10101` |
| Profitability segmentation by recommendation tier | this analysis | `dashboard?action=...history` parsed by `recommendation`: **TAKE +37% ROI**, STRONG TAKE +1.8% ROI, post-guardrail cohort `value_bet_gr202604` +27.9% ROI |
| Manual-pick verifier for UFC/Tennis/Golf | weekly remote agent `weekly-sports-pick-verifier-clv-trend` | First run report at `reports/MANUAL_SPORTS_PICKS_VERIFICATION_*.md`; opens a GitHub issue on disagreement |
| DB audit + planned migration | `reports/SPORTSBET_DB_AUDIT_2026_04_25.md` + `reports/sql_migrations/2026_04_25_sportsbet_fixes.sql` | 7 findings flagged; idempotent SQL ready to apply via phpMyAdmin |

## Improvements *expected* after PRs merge + operator deploys

These are queued and ready, gated on review/merge/deploy. Non-trivial value, but not currently visible on the page.

| PR | What it ships | Expected outcome |
|---|---|---|
| **#401** Pinnacle Shin devig | `sports_value_truep_pinnacle()` upgraded from proportional to Shin (1993); scraper-snapshot fallback when Odds API drops Pinnacle | Sharper anchor → directional CLV improvement on every NBA/NHL/MLB/NFL pick. Backtest harness #407 confirmed +0.28pp shift in the right direction; calibration test inconclusive at n=6 settled bets — **rerun after `lm_sports_odds_history` accumulates** |
| **#402** `grade_manual` + `lookback_days` + totals fallback | Already production-deployed via FTP | Backlog cleared — same +$71 PnL above |
| **#403** NHL goalie scraper Phase 1 | Daily scrape of confirmed starters + GSAx/SV% from `api-web.nhle.com` + MoneyPuck CSV | NHL ML overlay (Phase 2, gated on #401) — adjust `true_prob` by goalie-quality delta with hard ±5pp cap |
| **#404** DB audit + FINISHED filter | Already deployed via FTP this session | Carolina @ Ottawa now correctly hidden by default — same proof above |
| **#405** Polymarket whale validator stub | Address-keyed wallet activity puller | Whale-tracker panel (Phase 2.10) — needs operator to capture 5 addresses + Copilot's Phase 2.10 PHP reader |
| **#406** Copilot Mercury PR 1 | Steam-move detector + 2-leg arbitrage scanner + `lm_sports_odds_history` table + WNBA filter | Two new tabs (⚡ Arbitrage, 🔥 Steam Moves), idempotent migrations for 10 future tables, paid-tier rate-limit detection |
| **#407** Shin devig backtest harness | `tools/backtest_shin_devig.py` + first calibration report | Re-runnable validation each time `lm_sports_odds_history` grows |
| **#399** Copilot PM bridge wire-up | Schedules `sports_prediction_market_bridge.py` in CI; adds `sports_pm_score_nudge()` to composite score; renders PM pill on each card | **The actual Polymarket integration into the visible UI** — currently DRAFT |

## Top priorities (operator action)

1. **Decide on the 4-PR sports-edge contest** (#396/#397/#398/#400) — close 3 as superseded; merge #400.
2. **Merge #401, #402, #404, #406, #407, #399 in some sane order** (see `reports/SPORTS_PRS_TRIAGE_2026_04_26.md`).
3. **Apply two SQL migrations** via phpMyAdmin (`2026_04_25_sportsbet_fixes.sql` + `sports_plan_migrations_v2.sql`).
4. **Subscribe The Odds API $20/mo paid tier** — current free tier is the foundational bottleneck (2-3h refresh; paid tier = ~1min). Kimi research and external review both rank this #1.
5. **Add 4 cron entries on the deploy host:**
   - `*/5 * * * *` Pinnacle anchor scrape
   - `0 17 * * *` NHL goalie scrape
   - `*/5 * * * *` Steam detector
   - `*/5 * * * *` Arb scanner
6. **Capture 5 Polymarket wallet addresses** (Swiss Tony / HyperLiquid0xb / RN1 / distinct-baguette / ColdMath) from `polymarket.com/profile/<addr>` URLs — populate `data/polymarket_whale_seed.json`.
7. **Consider raising the auto-place gate from 1.5% → 5% EV** — current data: TAKE tier +37% ROI vs STRONG TAKE +1.8% (sample n=12+9, directional but not statistically conclusive).

## Summary in one sentence

Foundations are real and growing fast — Pinnacle Shin, scraper snapshot, FINISHED filter, grade_manual, DB audit, NHL goalie data feed, whale validator stub, backtest harness, and a working Polymarket Gamma API client are all shipped or in PR — but **the only Polymarket-derived signal currently *visible to a sports bettor on the page* is via the standalone CLI tools**; the in-page integration (PR #399's PM pill + score nudge) is one merge + FTP-deploy away.
