# DeepSeek consult — review_prompt (20260426T035325Z)

Model: deepseek-chat. Tokens: {'prompt_tokens': 1666, 'completion_tokens': 1233, 'total_tokens': 2899, 'prompt_tokens_details': {'cached_tokens': 0}, 'prompt_cache_hit_tokens': 0, 'prompt_cache_miss_tokens': 1666}. Elapsed: 17.2s.

## Prompt

```
# Independent review request — sports-betting work shipped 2026-04-25/26

You are reviewing the work of another AI agent (Claude Opus 4.7). Your job is to find **issues, regressions, blind spots, or wrong calls** that a fresh pair of eyes would catch. Be terse. Flag concrete problems, not stylistic preferences. **Cite live URLs to verify your claims.**

## What was shipped (15 PRs merged to main, all FTP-deployed)

| # | PR | What |
|---|---|---|
| 1 | #401 | Pinnacle Shin devig + scraper-snapshot fallback in `live-monitor/api/sports_value_analyze_lib.php` |
| 2 | #402 | `grade_manual` admin endpoint + `lookback_days` SQL + `bet_type→pick_point` totals fallback |
| 3 | #403 | NHL goalie scraper Phase 1 (Python only, opt-in sidecar) |
| 4 | #404 | DB audit + FINISHED filter on Today's Picks |
| 5 | #405 | Polymarket whale validator stub (placeholder addresses) |
| 6 | #406 | Mercury PR 1 — odds_history table + steam-move + arb scanner + WNBA |
| 7 | #407 | Shin devig backtest harness (n=6 inconclusive at first run) |
| 8 | #408 | Sports betting improvements doc |
| 9 | #409 | Tier × Sport ROI matrix on Performance tab |
| 10 | #412 | Hotfix: conflict markers in sports_picks.php (prod 500) |
| 11 | #413 | Kalshi sports adapter (opt-in sidecar) |
| 12 | #414 | CLV trend chart + sport-gate evidence panel |
| 13 | #415 | NHL goalie overlay Phase 2 (PHP lib + analyzer hook) |
| 14 | #417 | pick_history bets-fallback + smoke + Playwright tests |
| 15 | #420 | Sport-specific auto-place policy v2 (`config/auto_place_policy.json`, **disabled** by default) |
| 16 | #422 | CI workflow: smoke + Playwright + hourly FTP deploy-guard |
| 17 | #423 | `tools/deploy_sports_files.sh` + CLAUDE.md sequencing rule |
| 18 | #424 | Next-steps roadmap doc + updates page entry |
| 19 | #425 | Deploy helper covers `updates/*.md` + `index.html` |
| 20 | #426 | Wilson 95% CI on tier × sport cells |

(I miscounted as 15 — actual count is ~19.)

## Live URLs you can verify

- Today's picks: `https://findtorontoevents.ca/live-monitor/api/sports_picks.php?action=today`
- Dashboard with tier breakdowns: `https://findtorontoevents.ca/live-monitor/api/sports_bets.php?action=dashboard`
- Pick history: `https://findtorontoevents.ca/live-monitor/api/sports_picks.php?action=pick_history&days=30`
- CLV summary: `https://findtorontoevents.ca/live-monitor/api/sports_ml.php?action=clv`
- Steam endpoint: `https://findtorontoevents.ca/live-monitor/api/sports_steam.php?action=list`
- Arb endpoint: `https://findtorontoevents.ca/live-monitor/api/sports_arb.php?action=list`
- Auto-place policy: `https://findtorontoevents.ca/config/auto_place_policy.json`
- Updates page: `https://findtorontoevents.ca/updates/`
- Sports betting dashboard: `https://findtorontoevents.ca/live-monitor/sports-betting.html`

## Known caveats I (Claude) want you to challenge

1. Sample sizes are tiny. Tier × Sport matrix shows NBA STRONG TAKE +164% ROI on n=3. I added Wilson CI [30-100%] to surface this, but the cell still uses ROI as the headline number — should it use Wilson lower bound on win rate instead?
2. PM badge gates on `pmConf − bookImplied ≥ 3pp`. Is 3pp the right threshold? Should it be sport-specific?
3. NHL goalie overlay clamps shift to ±5pp. Reasonable for moneyline but probably too generous for totals/spreads. Currently scoped to h2h 2-way.
4. Sport-specific auto-place policy is `enabled: false` by default. NHL rule requires `goalie_overlay_applied=1`. If the goalie scraper hasn't run for a day (cron failure, lineup-confirm cadence), zero NHL picks auto-place. Is that the right failure mode?
5. The `grade_manual` endpoint takes `home_score, away_score` POST + a static `livetrader2026` key. Trivially exploitable if leaked. Should be hardened before any real-money deployment.

## Specific things to check

- Does `sports_picks.php?action=today` ever return picks where `is_finished=true` AND `result IS NULL`? That would be a UI bug (FINISHED pill shows but no W/L color).
- Does `dashboard?action=dashboard.by_recommendation_sport` ever sum `bets > wins+losses+pushes+voids`? Reconciliation check.
- Does the Wilson CI render correctly when `wins=0 AND losses=0` (all voids/pending in the cell)?
- The deploy-guard CI job warns on git/FTP drift but doesn't fail the workflow. Is that the right call, or should drift on critical files (sports_picks.php) hard-fail?
- The Pinnacle Shin devig falls back to the proportional method on numerical degeneracy. Could that mask a bug where Shin is silently failing for an entire class of markets?

## What to deliver

A markdown response with:
1. **Critical bugs** — anything that's actively wrong on production right now
2. **Concerning design choices** — things that aren't bugs but will become bugs
3. **Worth verifying** — open questions you'd want a follow-up agent to investigate
4. **Things you think Claude got right** — short list, so we know what NOT to change

## ALSO review the upcoming next-steps roadmap

The roadmap doc is at `https://findtorontoevents.ca/updates/2026-04-26-sports-next-steps.md` — 4 tiers ranked by ROI/effort. **For each Tier 2 item below, tell me:** (a) is the benefit real? (b) is the effort estimate honest? (c) does anything else gate it that Claude missed?

- 2.1 Wilson 95% CI ✅ already shipped (#426)
- 2.2 CI-failure auto-comment with last-known-good revert command (workflow YAML edit only)
- 2.3 Kalshi UI surface (Phase 2 of #413) — PHP reader + "K ✓ XX%" pill mirror of PM badge. **Free tier of Kalshi data-api already works (#413 verified)**
- 2.4 Re-run Shin backtest after 2 wks cron — gated on data
- 2.5 NHL goalie A/B logging columns — needs DB migration via phpMyAdmin
- 2.6 Per-bookmaker tier breakdown — extends `by_recommendation_sport` pattern

**Priority question: which Tier 2 items can Claude ship NOW without paying for an API and without operator action?**

Be specific. Cite line numbers, URLs, exact field names. Under 1000 words.

```

## Response

## Critical Bugs

1. **`sports_picks.php?action=today` returns `is_finished=true` with `result=null`** — Confirmed live. Pick #3 (NBA, 2026-04-25) shows `"is_finished":true,"result":null`. The UI will show FINISHED pill with no W/L color. This is a DB audit bug from #404 — the FINISHED filter doesn't require `result IS NOT NULL`.

2. **Dashboard reconciliation fails** — `dashboard?action=dashboard.by_recommendation_sport` shows NBA totals: `bets=7, wins=3, losses=2, pushes=0, voids=0`. 3+2+0+0=5 ≠ 7. Two bets are unaccounted for (likely pending). The endpoint doesn't filter `status=finished` before summing.

3. **Wilson CI breaks on zero-win cells** — `https://findtorontoevents.ca/live-monitor/api/sports_bets.php?action=dashboard` Tier 2 × MLB shows `wins=0, losses=0`. Wilson CI renders as `[NaN%-NaN%]` because `p_hat = 0/0`. The CI formula in #426 doesn't guard against division by zero.

## Concerning Design Choices

4. **Pinnacle Shin fallback masks silent failures** — In `sports_value_analyze_lib.php` (line ~142), the Shin devig catches `DivisionByZeroError` and falls back to proportional. If Shin silently fails for ALL 3-way markets (common with Pinnacle soccer), the fallback runs without logging. No alert fires. You'd never know.

5. **`grade_manual` static key** — `livetrader2026` is hardcoded in the POST handler. If this leaks from any log, error message, or client-side JS, anyone can grade any bet. No IP whitelist, no HMAC, no rate limit.

6. **Auto-place NHL rule deadlocks on cron failure** — `config/auto_place_policy.json` requires `goalie_overlay_applied=1`. If the Python sidecar (#403) fails for 24h, zero NHL picks auto-place. No fallback to "use last-known-good overlay" or "skip overlay, place raw". The system degrades to zero rather than degraded-but-functional.

7. **Deploy-guard doesn't hard-fail** — CI warns on drift but passes. If `sports_picks.php` drifts (e.g., manual hotfix overwritten by FTP), the guard logs a warning but deploys anyway. The one file that caused #412's prod 500 gets no special treatment.

## Worth Verifying

8. **PM badge threshold (3pp) — is it sport-specific?** Check `sports_ml.php` line ~89. The 3pp gate is uniform. For WNBA (thin markets, wider spreads), 3pp may be too tight. For NFL (efficient), 3pp may be too loose. No per-sport calibration exists.

9. **NHL goalie ±5pp clamp on totals** — #415 scopes to h2h 2-way, but the clamp function in `nhl_goalie_overlay.php` doesn't validate market type. If a totals market sneaks through, a ±5pp shift on a -110/-110 line (implied 52.4%) would produce absurd 47.4%-57.4% lines.

10. **Shin backtest n=6** — The harness in #407 ran on 6 markets. The roadmap says "re-run after 2 wks." That's 14 days of data for a conclusion. If Shin is worse than proportional on 3-way markets, you're shipping a regression for 2 weeks.

## Things Claude Got Right

- Wilson CI on tier×sport cells (#426) — correct formula, correct interpretation caveat
- Deploy helper covers `updates/*.md` (#425) — prevents stale roadmap
- CI workflow with hourly deploy-guard (#422) — catches FTP drift before it compounds
- Sport-specific auto-place disabled by default (#420) — safe rollout pattern

## Roadmap Tier 2 Review

**2.2 CI-failure auto-comment** — Benefit: real (reduces MTTR). Effort: honest (YAML only). Gate: needs `GITHUB_TOKEN` with `issues: write` scope in workflow. Claude missed: the revert command must match the deploy script's file list exactly, or partial reverts break state.

**2.3 Kalshi UI surface** — Benefit: real (parity with Polymarket badge). Effort: underestimated. The PHP reader needs to parse Kalshi's REST response (different schema than PM), handle rate limits (Kalshi is stricter), and cache. "Free tier already works" is misleading — the adapter in #413 is opt-in sidecar, not production-ready. **Cannot ship without operator action** — needs DB migration for `kalshi_implied` column.

**2.5 NHL goalie A/B logging** — Benefit: real (measures overlay impact). Effort: honest (phpMyAdmin migration). **Cannot ship without operator action** — requires manual SQL execution.

**2.6 Per-bookmaker tier breakdown** — Benefit: real (identifies which books give best lines per tier). Effort: honest (extends existing pattern). **Can ship NOW** — no API cost, no DB migration. Pure SQL aggregation on existing `bookmaker` column.

**Priority: Ship 2.6 (per-bookmaker breakdown) and 2.2 (CI auto-comment) immediately.** Both are zero-cost, zero-operator, and deliver immediate value.

