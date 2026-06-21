# Carryover status — daily_prices + active-picks score=NULL (2026-06-20)
**Author:** claude-opus · loop tick · all SQL/endpoint-verified

## (1) daily_prices restore — STILL FROZEN
- Both writer endpoints still **404** (`/findstocks/portfolio2/api/fetch_prices.php`, `/findstocks/api/fetch_prices.php`), verified 2026-06-20.
- `daily_prices` max(trade_date) = **2026-04-29** (49,340 rows) — unchanged.
- The unmask shipped earlier (`9f501250`) now makes `daily-price-refresh.yml` fail loudly (red) instead of false-green. **Status: awaiting operator endpoint restore** (FTP-redeploy `fetch_prices.php` OR rewire `scripts/api_integrations.py`), per `MONEY_READY_NEXT_STEPS_BUILD_PLAN_2026-06-19.md`. Gates EQUITY honest n (H-126).

## (2) active-picks score=NULL — CLASSIFIED: NOT a bug (intended funnel)
The "1 active pick" question chain resolved. Of 1,950 `active_raw` picks: **348 carry a dashboard `score`, 1,602 are score-NULL/0.**
- The dashboard `score` field is set by the production scanner for picks **it generates** (alpha_engine, alpha_engine_fast, orphan_emitter, top_gainer_predictor…). `calculate_smart_score` (quality_gates.py:10222) produces a *separate* `smart_score` (0-1), not this field.
- The score-NULL sources are **merged external / experimental / banned feeds**: signal_validation (409), inverse_mutations (252), copy_trader_highscore (108, **BANNED**), stocks_competition (100, **BANNED**), copy_trader_clones (93), kimi_signal_tracking (82), multi_asset_copytrader (79), kimi_riseoftheclaw (48). They are pooled into `active_raw` for visibility ("Show All Picks") but never run through production scoring → correctly excluded from the **scored, gated Active view** (which requires `score>0`).
- **Verdict: intended funnel design, not a pipeline break.** Banned sources unscored+rejected is correct; external/tracking feeds unscored is by architecture. One mild inconsistency: `kimi_riseoftheclaw` splits 24 scored / 48 unscored — worth a look if it's meant to be a tradeable candidate, but not a P-level bug.

## Conclusion on the original "1 active pick — broken or too strict?"
**NOT broken.** The single active pick is the intended result of (a) the scoring funnel (only production-scored picks carry `score`; external/experimental/banned feeds excluded) + (b) deliberately strict gates: THRESHOLD FREEZE non-crypto score≥55 (locked to 2026-08-18), banned-source rejection, and the bearish-regime filter favoring the lone regime-aligned SHORT. The strictness is a deliberate post-pick-inflation safety choice — working as designed, not a malfunction. All picks remain visible via "Show All Picks (1948)".
