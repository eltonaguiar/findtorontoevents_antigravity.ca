# Phase-2 Performance Audit Plan — BOND

Author: peer_claude (Opus 4.7) — 2026-05-31
Scope: READ-ONLY. Per-asset-class performance audit for `category='bond'` in `ejaguiar1_stocks.trading_picks`.

## Data source
- DB: `ejaguiar1_stocks.trading_picks` on `mysql.50webs.com` (pymysql, read-only).
- Cross-check: `audit_dashboard/data/pf_registry.json` (`by_asset_class*` + `by_asset_class_strategy`).

## Filter
- `LOWER(category) IN ('bond')` — no plural variant exists in this DB; spot-check confirmed.
- Closed cohort: `closed_at IS NOT NULL` (primary).
- Resolved-cohort (sensitivity view): `status IN ('WON','LOST','TP_HIT','SL_HIT','TIME_EXIT','EXPIRED')` to capture rows where outcome is recorded but `closed_at` was never stamped (BOND has 125 such rows — material).

## Queries
1. Per-strategy aggregate (closed_at NOT NULL): standard query (n, wins, WR, avg_pnl, PF, worst, best). `HAVING n>=10`.
2. Class-aggregate row: same metrics no GROUP BY, both cohorts.
3. Status distribution to surface anomalies (resolved+closed_at-NULL leakage).
4. Per-symbol distribution — concentration check.
5. Cross-check vs `pf_registry.json` BOND entries:
   - `by_asset_class_raw`, `by_asset_class`, `by_asset_class_policy_clean`, `by_asset_class_policy_clean_net`, `by_asset_class_strategy_policy_clean_net`, `by_asset_class_strategy`.

## T2 / T1 thresholds (hedge-fund tier table)
- T2 (Tier-2): PF>=1.5, WR>=50%, MDD<20%, n>=100.
- T1 (Renaissance): PF>=2.0, WR>=55%, MDD<10%, n>=100.

## Known caveats / risks
- **CLAUDE.md note**: BOND class-aggregate per `pf_registry.by_asset_class_policy_clean_net` shows INSUFF-N (n=8 in May-24 snapshot). The current `audit_dashboard` snapshot is even thinner (n=2). This audit will likely echo INSUFF-N.
- **Anomaly already visible**: 125 BOND picks have a resolved `status` (TIME_EXIT/LOST) but `closed_at IS NULL`. The standard `closed_at IS NOT NULL` filter (used by `pf_registry` and most analytics) drops them — but they are real outcomes. Need to flag this as a resolver/closer plumbing bug analogous to the FOREX/COMMODITY resolver fixes (M-067, PR #166).
- **Mis-tagged symbol IDs**: spot-check found id `iso_regime_terminal_GBPUSD=X_2674967031` with symbol=IEF and category=bond — id-vs-symbol mismatch (legacy ISO regime carry-over). Flag for ID-pipeline review.
- **`ZN=F` as BOND vs FUTURES**: ZN=F (10Y T-Note futures) is correctly classed as BOND (underlying = US Treasury). Not a tagging bug. Confirm with category schema doc if needed.
- **Cannot compute true MDD** from per-pick PnL alone without equity-curve series; will provide proxy "worst single trade" + signed avg as a directional indicator and explicitly mark MDD as "not computable from this query".
- **MDD verdict caveat**: T2 MDD<20% axis cannot be evaluated in this READ-ONLY pass — will mark `n/a` and recommend the equity-curve generator (`tools/equity_curve.py` or similar) be run before any sizing decision.
- **PF is fragile at small n**: BOND closed cohort is 5 rows. PF=362 is driven by a single 5%-PnL win against three near-zero TIME_EXIT-style outcomes — not statistically meaningful. Will flag as a *de facto* INSUFF-N PASS that should NOT be graduated.

## Output
- `reports/peer_claude-phase2-perf-bond_result_2026-05-31.md` with class-aggregate, per-strategy table, T2 verdict per axis, promotable/watchlist/dead lists, pf_registry divergences, and 1-2 line recommendation.

## PR plan
- Server-side `gh api` PR off `origin/main`, title `docs(phase2): per-asset-class performance audit — BOND`, single-file scope (result MD + this plan MD), admin-merge.
