# Audit Findings — OpenCode 2026-10-22

Source: local repo `/home/eaguiar2015/findtorontoevents_antigravity.ca`, MySQL `ejaguiar1_stocks` (read-only), `.github/workflows/audit-dashboard.yml`, `audit_trail/`, `audit_dashboard/`, existing root-cause docs.

## 1. Executive summary

- **Mutual funds exist, but as a separate, half-dead subsystem.** Two incompatible DB families (`mf_*` US funds, `mf2_*` Canadian RBC/TD funds). Only `mf2_*` has any resolved outcomes (75 tracked picks, 35 closed). The rating is **inverted** on that sample (score↔return corr -0.28; Strong Buy avg -7.09% vs Buy +5.04%). The pipeline (pick + NAV generation) froze 2026-03-29; only a heartbeat log is alive.
- **No mutual-fund asset class in `/audit`.** `MUTUAL_FUND` is only a classification branch in `audit_dashboard/database_consolidation.py` and a placeholder in `institutional_readiness_plan.html`. Mutual funds are not in `at_raw_picks`/`at_consensus_picks` and are not ingested.
- **Stocks/crypto/bonds/ETFs/commodities/prediction failed for systemic, compounding reasons**, not one bug: outlier/sentinel contamination, soft-resolution inflation, over-broad/leaky blocklists, frozen score floors, missing emitters, mis-modeled costs/tracking windows, and copy-trader/kimi layers that are net losers still treated as winners.
- **Published consensus is broken for equity:** `at_consensus_picks` EQUITY = 9 wins / 398 losses (2.2% WR, PF 0.09). CRYPTO consensus = 40.3% WR / PF 1.27.
- **Pipeline health is degraded but not dead:** `pipeline_health.json` = degraded (walk-forward validation failed); DB freshness RED on `backtests` (MySQL timeout), resolver YELLOW (~9.3h stale); dashboard payload on disk stale (2026-05-31) vs current run (2026-10-20). 196 incidents / 208 enhancements open.

## 2. Mutual funds — where they live

**DB (`ejaguiar1_stocks`)**

| Family | Tables | Funds | State |
|---|---|---:|---|
| `mf_*` (v1, US: Vanguard/Fidelity) | 18 | 20 | Dead since 2026-02-09; backtests/benchmarks/simulation tables **empty**; only 15 picks + 34 selections, no outcomes |
| `mf2_*` (v2, Canadian RBC/TD) | 15 | 15 | Half-alive: audit log + algo performance heartbeat 2026-05-08; `mf2_fund_picks` (600), `mf2_nav_history` (6,860, through 2026-03-27), `mf2_tracked_picks` (75) frozen since 2026-02-15/2026-03-29 |

**Repo code**

- `findmutualfunds2/portfolio2/api/` — only `debug_navs.php`, `fix_dates.php`, `test_bt.php`. `fix_dates.php` literally DELETEs tracked picks/backtests and rewrites pick dates (manual reset, not a resolver).
- `investments/index.html`, `investments/all-dashboards.html` — link to `/findmutualfunds/portfolio1/` and `/findmutualfunds2/portfolio2/`.
- `v1 findmutualfunds/` is **not in the repo**.
- Schema/docs: `schema-baseline.sql`, `docs/DB_SCHEMA_stocks_backtests_2026-05-15.md`, `reports/uncharted_tables_recon_2026-05-08.md`, `reports/investment_hub_hidden_edge_and_honesty_tiers_2026-05-29.md`.
- `audit_dashboard/database_consolidation.py` — `classify_asset` returns `MUTUAL_FUND`, but nothing is harvested.

## 3. Mutual-fund performance quality

| Source | Rows | Key numbers |
|---|---:|---|
| `mf2_tracked_picks` | 75 (35 closed) | WR **40.0%** (14/35), avg return **-2.47%**, avg win +5.41%, avg loss -7.73%, **PF ≈ 0.47**. Exits: sl_hit 16, max_hold 12, tp_hit 4, take_profit 2, stop_loss 1; avg hold 123 days |
| `mf2_tracking_daily` | 3 | WR 55%→48%→40%; avg return 0.22%→-1.04%→-2.47% |
| `mf2_backtest_results` | 10 | Total return 0.20%–13.66%; WR 46.67–60%; PF 0.91–2.30; `annualized_return_pct = 0.0000` on every run |
| `mf2_backtest_trades` | 450 | One run (2026-02-12); per-algo avg return -3.06% (Risk Parity) to +3.06% (Momentum) |
| `mf2_algo_performance` | 10 | Learning-scan aggregates, synthetic-looking (e.g. Balanced Composite 97.5% WR / +31.88%; Quality Growth 3.75% / -9.85%) |
| `mf2_fund_picks` | 600 | Score/rating only — **no outcome columns** (unresolved). `rationale_json` NULL on all rows, `pick_hash` empty |
| `mf_*` (v1) | 15 picks, 34 selections | **No outcome tracking at all**; backtests empty |

**Rating is inverted on the only resolved sample (n=35):**

- `corr(score, final_return) = -0.282` (Spearman -0.269). Winners avg score 75.5 vs losers 78.0.
- By rating (closed): **Strong Buy avg -7.09%** (n=11) vs **Buy +5.04%** (n=12); Hold -6.71%; Speculative +4.84%.
- Rating is just a static per-symbol score bucket (e.g. TDB911 always 92, RBF559 always 60); score never recomputed from outcomes.
- Lessons contradict data: claim "optimal score 80+" while 80+ buckets average -8.79% (score 90) / -8.49% (score 92).
- Backtest trades show the opposite weak trend (+0.059 corr) — inconsistent, tiny n.

## 4. Can we make a strong mutual-fund rating system?

**Yes, but only after fixing the data plumbing.** Feasible building blocks exist: 15-fund catalogs (both US and Canadian) with expense ratio / Morningstar / asset class; 11,860 NAV rows; 10 strategy definitions; 450 backtest trades; a tracked-pick outcome template (entry/current/peak/trough/exit/hold_days/score/rating).

**Blockers to fix first:**

1. **Outcome resolver** — `mf2_fund_picks` (600) has no status/pnl/exit. `mf2_tracked_picks` is hand-seeded (75, frozen). Need an automated resolver joining picks→`mf2_nav_history` (or live NAV feed) with TP/SL/time-exit rules. Pick generator + NAV feed dead since 2026-03-29.
2. **NAV freshness** — NAV history stops 2026-03-27; no live feed wired.
3. **Benchmarks** — `mf_benchmarks` empty (0 rows); backtest `annualized_return_pct` is 0.0000 everywhere. Need index/benchmark series (S&P 500, TSX) for relative performance.
4. **Fees/loads** — v2 portfolios have commission_buy/sell = 0.00 and redemption_fee_pct = 0.00, but real funds carry MER 0.33–2.24% plus possible loads (v1 has front_load_pct/back_load_pct). Backtest fees appear but portfolio config ignores them → inflated results.
5. **Sample size** — only 35 closed tracked picks; need n≥50–200 per the charter for any defensible WR/PF/expectancy.
6. **Transparency** — rating formula is undocumented (static per symbol, null rationale, empty hash). Need a documented, recomputable score.
7. **Asset-class integration** — no `MUTUAL_FUND` class in `/audit` (`asset_classification`); mutual funds are out of the pick flow. `mf2_tracked_picks` is not in `at_raw_picks`.
8. **Holdings/style data** — no holdings, manager tenure, or style exposure; only NAV + static fund metadata.

**Recommendation:** Treat all MF metrics as 🟠 Unverified per `docs/METRIC_HONESTY_TIERS.md` until the resolver + NAV feed + benchmarks + ≥100 hard-resolved (TP/SL, not soft max-hold) outcomes per rating bucket exist. Do not promote MF to `/audit` or real capital before that.

## 5. What went wrong across stocks/crypto/bonds/ETFs/commodities/prediction

Evidence: `ROOT_CAUSE_ANALYSIS_NON_CRYPTO.md`, `reports/investment_hub_hidden_edge_and_honesty_tiers_2026-05-29.md`, `at_raw_picks` (108,476 rows), `at_consensus_picks` (11,919 rows).

### Top root causes (ranked by evidence strength)

1. **Data leakage / backtest overfit + fabricated outliers (CRITICAL).** Predictions CRYPTO: WR 31.0% but PF 4.37, driven by a single `BTCUSDT` row entry $20 → exit $74,190 = +370,850% PnL (wrong entry price). Top 1% of rows = 126% of total PnL. `orphan_emitter_forex_futures` FUTURES: `YM=F` row with 999,999.9999% PnL (decimal column-max sentinel) inflates FUTURES PF to 89.6. Reported PFs are not tradable edge. Matches the report's "fabricated summary values" landmine.
2. **Copy-trader layer is a net loser / suspiciously perfect.** `multi_asset_copytrader` FOREX: 88.9% WR / PF 10.24 on 1,961 resolved, but winners are ~1–2% moves and many symbols show 99–100% WR with ~$0 losses (USDCAD, EURJPY, USDCHF all 100% WR, 0 losses) → likely soft/zero-loss resolution. `copy_trader_intel` CRYPTO: 0.0% WR (0W/37L); `copy_trader_polymarket`: 0.0% WR (0W/66L). `non_crypto_consensus` is in `_RETIRED_STRATEGIES` (0% WR on 87 trades) yet still appears in FUTURES rows (11 picks, 3W/8L).
3. **Blocklists: over-broad in some places, leaky in others.** `_RETIRED_STRATEGIES`: 28 entries; `_PAPER_ONLY_STRATEGIES`: 51; `_RETIRED_SYSTEM_STRATEGY_PAIRS`: 12 pairs. 11,901 of 108,476 raw picks flagged `was_banned=1`. Bonds: 6 of 9 strategies blocked (67%); Forex: 5 of 9 (56%); Commodity: 2 of 6 (33%) + `cta_commodity_momentum_term` (PF 0.02, 58% flat exits) still active and toxic. Non-crypto starved of emitters while toxic ones leak through.
4. **Score floors vs achievable scores (partially fixed, frozen).** `SMART_PICKS_MIN_SCORE = 60` frozen to 2026-08-18 while non-crypto boosters can only reach ~30–55. Floors: FOREX 40, COMMODITY 30, BOND 35, FUTURES 45, ETF 35, EQUITY 50; `ASSET_CLASS_SMART_THRESHOLDS` still sets CRYPTO min_score 65.0. Elite-grade gate hard-blocks D/F picks; bonds naturally score lower → blocked even after floor cuts (bond T2 picks with ml_score 0.859/0.839/0.743 blocked).
5. **Emitters / asset-class coverage gaps.** `COMMODITY` asset class has **0 rows** in `at_raw_picks` (commodity picks misclassified as FUTURES or never persisted). BOND: only 214 raw picks total. Bond workflow `alpha-engine-bond.yml` is `.disabled`. Consensus table: only 1 COMMODITY and 1 FOREX pick total — consensus aggregation effectively absent for these classes.
6. **Soft-resolution inflation.** ETF: 59.4% of resolutions soft (TIME_EXIT/EXPIRED/STALE); EQUITY 45.3%; FOREX 40.7%; CRYPTO 37.4%. Report: `miracle_picks2 / Mean Reversion Sniper` shows 62.5% WR / PF 2.04 with **zero actual winners** (8 losers + 40 expired scored by PnL sign). WR/PF look acceptable while no TP was ever hit.
7. **Tracking windows too short for slow markets.** 10–23% of picks unresolved (OPEN/EXPIRED/ABANDONED): EQUITY 10.1%, CRYPTO 22.8%, FOREX 15.8%, ETF 15.8%, FUTURES 13.7%, BOND 15.0%, PENNY 73.1%. 24h resolution systematically biases Forex/Bonds (need 5–14 days).
8. **Transaction costs not modeled for non-crypto.** `alpha_engine/transaction_costs.py` `COST_MODELS` has no `bond`/`commodity`/`futures` keys; `_CATEGORY_TO_COST_MODEL` lacks them → default to `stocks_etf` at 0.03% round-trip. Real non-crypto costs higher → backtested WR/PF overstated.
9. **Kimi poisoning (FOREX).** `kimi_signal_tracking/default` on FOREX: n=158, WR 30.4%, avg -6.17%/trade, total -974.66%; accounts for 98% of FOREX bleed. In `_RETIRED_SYSTEM_STRATEGY_PAIRS`, but enforcement inconsistent: still referenced in `genome/dna_winner_mutations.py`, `strategies/source_quality_filter_v1.py`, `tools/weekly_filter_picks.py`, `tools/edge_analysis/asset_class_edge_registry.py` with glowing claims (75% WR, PF 5.43). Recent DB shows only 18 `kimi_signal_tracking` FOREX rows (5W/1L) — legacy code still treats it as a winner.
10. **Prediction markets: no verified edge.** Predictions CRYPTO: 31.0% WR (752W/1672L), PF inflated by the +370k outlier. `polymarket_signals`: 4 rows, 0 resolved; `copy_trader_polymarket`: 0% WR (0W/66L). ~14,200 Hub picks with no outcome columns; `*_backtest_trades` tables empty; `*_algo_performance` contains 999,999% sentinel.

### Consensus-table evidence (`at_consensus_picks`)

| Class | Total | Resolved | WR | PF |
|---|---:|---:|---:|---:|
| CRYPTO | 10,439 | 8,566 | 40.3% | 1.27 |
| EQUITY | 771 | 407 | **2.2%** | 0.09 |
| MEMECOIN | 707 | 428 | 38.3% | 0.74 |
| COMMODITY | 1 | 0 | — | — |
| FOREX | 1 | 0 | — | — |

EQUITY consensus is catastrophic (9W/398L) — consensus aggregation itself is broken for stocks.

## 6. Audit dashboard / pipeline state

- Workflow: `.github/workflows/audit-dashboard.yml` runs hourly at `:10` (115-min timeout), `workflow_dispatch` available, `push:` trigger removed, single `dashboard-publish` concurrency group.
- `audit_trail/data/pipeline_health.json` = `status: degraded` (walk-forward validation failed).
- `audit_dashboard/data/db_health.json` all checks green.
- `audit_dashboard/data/db_freshness.json` overall RED: live_picks GREEN (77,941 active, ~17.6 min stale); resolver YELLOW (~555 min stale, 8 resolved today); signal_outcomes GREEN (~326 min, 41 today); intrabar_resolution GREEN (~109 min); backtests RED (MySQL query timeout, 0 rows).
- `audit_trail/data/dashboard_payload.json` generated 2026-05-31; active picks in payload = 25; asset classes present = CRYPTO, EQUITY, FOREX, COMMODITY, FUTURES, BOND, ETF (no mutual fund).
- `audit_dashboard/data/metric_honesty_tiers.json` defines 5 tiers (`institutional_grade`, `production_viable`, `promising_not_valid`, `unverified_unresolved`, `disputed_contaminated`) plus anti-gaming gates; no `institutional_grade` live examples; `mf2_fund_picks` explicitly listed as unverified.
- `audit_dashboard/data/incidents_enhancements_feed.json` generated 2026-10-19: 196 incidents, 208 enhancements, 21 findings; many OPEN/P0/P1 items.
- Mutual funds not integrated: only classification branch in `database_consolidation.py` and "not yet ingested" placeholder in `institutional_readiness_plan.html`. No `MUTUAL_FUND` asset class in dashboard payload. `recon_uncharted_tables.py` recognizes `mf_`/`mf2_` but does not harvest them.

## 7. Plan to get wins

### Phase A — Stop the bleeding / make metrics honest (P0, 1–2 weeks)

1. **Adopt hard-only resolution everywhere.** Only TP/SL hits count as wins/losses; OPEN/EXPIRED/TIME_EXIT never count as wins. Add soft-resolution as a separate column. This alone invalidates most "promising" cohorts (e.g. miracle_picks2 Mean Reversion Sniper).
2. **Purge outlier/sentinel contamination.** Remove or winsorize the +370,850% BTCUSDT row and the 999,999.9999% YM=F sentinel; recompute all PFs; ban any metric whose top 1% of rows > 50% of total PnL.
3. **Fix copy-trader and kimi leakage.** Remove `copy_trader_intel` (0% WR), `copy_trader_polymarket` (0% WR), and all `kimi_signal_tracking` references from `genome/dna_winner_mutations.py`, `strategies/source_quality_filter_v1.py`, `tools/weekly_filter_picks.py`, `tools/edge_analysis/asset_class_edge_registry.py`. Keep them in `_RETIRED_STRATEGIES`/`_RETIRED_SYSTEM_STRATEGY_PAIRS` and verify enforcement (no scanner bypass).
4. **Complete the blocklist cleanup.** Unblock the 11 bond/forex strategies listed in `ROOT_CAUSE_ANALYSIS_NON_CRYPTO.md` #1 (bond_credit_spread, bond_inflation_breakeven, bond_curve_steepener, bond_high_yield_rotation, bond_term_premium, bond_vol_regime_mr; forex stochastic MR, usd trend). Ban `cta_commodity_momentum_term` (PF 0.02). Keep golden combos blocked until validated.
5. **Fix transaction costs.** Add `bond`, `commodity`, `futures` keys to `COST_MODELS` and `_CATEGORY_TO_COST_MODEL` in `alpha_engine/transaction_costs.py` (bond 0.05%, commodity 0.05%, futures 0.05% round-trip).
6. **Bond elite-grade exemption.** Add bond/ETF exemption to the D/F block in `quality_gates.py` so T2 bond picks (ml_score 0.859/0.839/0.743) are not blocked.
7. **Extend tracking window** from 24h to 120h minimum in `forward_validator.py` for slow markets (forex/bonds).

### Phase B — Restore emitters and coverage (P1, 2–4 weeks)

8. **Re-enable bond workflow** (`alpha-engine-bond.yml`) and wire ETF/bond scanners into the pick flow (already created in Phase 2; verify CI runs).
9. **Fix commodity classification** so commodity picks persist as `COMMODITY` (not misclassified as FUTURES or dropped). Currently 0 COMMODITY rows in `at_raw_picks`.
10. **Unfreeze score floors** — either lower floors further or add non-crypto boosters so achievable scores clear the gate. Re-evaluate `SMART_PICKS_MIN_SCORE = 60` (frozen to 2026-08-18).
11. **Fix consensus aggregation for equity** — investigate why EQUITY consensus = 2.2% WR (9W/398L); likely a direction/labeling bug in aggregation, not strategy.
12. **Wire FRED data** into non-crypto boosters (bond_scanner already passes fred_data; verify `FRED_API_KEY` set in CI).

### Phase C — Mutual-fund rating system (P1–P2, 4–8 weeks)

13. **Restore the MF pipeline:** pick generator + NAV feed (dead since 2026-03-29). Add `mf2_tracked_picks` to `at_raw_picks` with `asset_class = MUTUAL_FUND`.
14. **Build an automated NAV-based outcome resolver** (pattern: `alpha_engine/outcome_resolver.py`) joining `mf2_fund_picks`→`mf2_nav_history` with TP/SL/time-exit rules. Remove `fix_dates.php` manual reset path.
15. **Add benchmarks** (S&P 500, TSX) to `mf_benchmarks` and compute `annualized_return_pct` correctly.
16. **Apply realistic fees** (MER 0.33–2.24%, loads) in portfolio config and backtests.
17. **Document and recompute the rating formula** from outcomes (not static per-symbol score). Replace inverted static buckets with a documented, recomputable score.
18. **Accumulate ≥100 hard-resolved (TP/SL) outcomes per rating bucket** before any promotion. Only then integrate MF into `/audit` and the honesty tiers.

### Phase D — Validation before capital (P2, ongoing)

19. **Fresh forward-test** of the lone candidate (`gm_unified_picks / ADX Trend Strength`: WR 74.3% / PF 3.29, n=70 decisive, but crypto-concentrated, stale since 2026-02-16, ~40% soft-resolved) on post-April data, hard-resolved only, before any `/audit` ingestion.
20. **Wire outcome resolvers** for Hub feeds (crypto pairs/forex) — `*_backtest_trades` schemas exist but are empty. Only then can those areas be assessed.
21. **Render honesty tooltips** from `metric_honesty_tiers.json` on `/audit` + Hub pages (deferred under remote-ops freeze).
22. **Fix pipeline health:** resolve walk-forward validation failure; fix `backtests` MySQL timeout; reduce resolver staleness (<9.3h).

### Success criteria (how we know we have wins)

- At least one asset class with **hard-resolved** WR > break-even WR `BE = 1/(1+R:R)` on Wilson lower bound, PF > 1.0, n ≥ 100, on post-fix data (not contaminated by outliers/sentinels/soft resolution).
- No metric displayed as "resolved" unless it has ≥1 resolved outcome; all unresolved cohorts tagged 🟠 Unverified.
- Mutual-fund rating monotonic with realized returns (score↔return corr ≥ 0) on ≥100 hard-resolved picks.
- Consensus aggregation repaired: EQUITY WR no longer 2.2%.

## 8. Immediate next actions (this week)

1. Read `ROOT_CAUSE_ANALYSIS_NON_CRYPTO.md` and `reports/investment_hub_hidden_edge_and_honesty_tiers_2026-05-29.md` (already incorporated above).
2. Implement Phase A items 1–7 (honesty, outlier purge, copy-trader/kimi removal, blocklist cleanup, cost model, bond grade exemption, tracking window).
3. Run the honesty-tier recompute and confirm no `institutional_grade` claim is false.
4. Open a PR for Phase A only; do not touch Phase B/C until Phase A metrics are clean.
5. Do **not** run `check_active_picks.py` or `alpha_engine/smart_picks_engine.py` automatically (per AGENTS.md); run only on explicit user request.

---

## 8. Winning asset-class candidate (forward-looking)

After scanning all `AlphaEngine` strategies with ≥100 hard-resolved (WON/LOST) outcomes, recent activity (≥2026-09), low outlier contamination (top-1% share <15%), ≥3 symbols, and ≥60% positive months, the cleanest candidate is:

**`high_trust_momentum` (CRYPTO)** — `alpha_engine/proven_edge_strategies.py:268`

| Metric | Value |
|---|---|
| Asset class | CRYPTO |
| n (hard-resolved) | 206 |
| Win rate | 58.7% |
| Profit factor | 1.81 |
| Avg return/trade | +0.71% |
| Positive months | 5/5 (Jun–Oct 2026) |
| Symbols | 12 (BTC, ETH, SOL, XRP, BNB, AVAX, LINK, NEAR, DOT, LTC, …) |
| Top-1% pnl share | 11.8% (no outlier dependence) |
| Exit mix | TP_HIT 69 (+3.70%), TIME_EXIT 79 (+0.57%), SL_HIT 58 (−2.67%) |
| Confidence band | 0.72–0.79 (3–5 confluence factors) |
| Status | Active in `proven_edge_strategies.py`; not in `_RETIRED_STRATEGIES` |

Why this one and not the higher-PF alternatives:
- `regime_mild_bear` (EQUITY) has PF 3.34 but hyrotrader live eval shows 13.9% WR (n=36) — likely regime misclassification / different universe; do not trust until reconciled.
- `seasonal_momentum` (FUTURES) PF 2.80 but edge is concentrated in ZW=F (91% WR) and July; Aug/Oct negative — seasonal, not general.
- `cta_golden_cross_200` collapsed in Oct (17.6% WR).
- `high_trust_momentum` is the only candidate with positive average PnL in every month, multi-symbol participation, and bounded downside (worst trade −6.72%).

**Caveats (must be resolved before capital):**
- n=206 is below the charter's n≥200 institutional threshold for a single strategy; need more data.
- Includes TIME_EXIT resolutions (soft-ish); recompute on TP/SL-only subset.
- Confidence is self-assigned (0.72–0.79) based on confluence count; validate calibration.
- No transaction-cost adjustment yet (crypto cost ~0.20% round-trip; still leaves positive expectancy).
- Not currently in hyrotrader picks (different scanner); needs explicit wiring if we want it on `/audit/hyrotrader`.

**Recommended focused plan (next 4–6 weeks):**
1. Freeze all other strategy families; route 100% of new crypto picks through `high_trust_momentum` only.
2. Log every signal with full confluence factors + regime tag to `at_raw_picks` (already happening via AlphaEngine).
3. After ≥100 additional hard-resolved (TP/SL) outcomes, recompute WR/PF/Wilson lower bound vs break-even `BE = 1/(1+R:R)`.
4. If Wilson-lower-bound WR > BE and PF > 1.2 after costs → promote to `/audit` consensus tier and hyrotrader.
5. If not → retire and revisit `regime_mild_bear` after reconciling the hyrotrader discrepancy.

*Generated 2026-10-22 by OpenCode. All DB queries were read-only. No files were modified except this document.*
EOF
echo "written"