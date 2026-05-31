# Phase 10b — /money-maker-readyv2 plan (EQUITY)

**Date:** 2026-05-31 06:30Z
**Categories:** `LOWER(category) IN ('equity','stock','stocks')`
**Source:** live `ejaguiar1_stocks.trading_picks` (peer-mode read), cross-referenced vs `reports/QUANT_STRATEGY_REVIEW_2026-05-28.md`, Phase 3 MC watchlist (PR #179), `alpha_engine/config.py` BLOCKED_SOURCE_SYSTEMS / smart_picks gates.

## Methodology

1. Pull live trading_picks rows for the EQUITY union — categorize closed (`status IN ('WON','LOST','TP_HIT','EXPIRED','TIME_EXIT')`), and split signal vs noise via `pnl_pct != 0`.
2. Aggregate **two** verdict views:
   - `naive` — only legacy `status IN ('WON','LOST')` (what older dashboards used).
   - `unified, excl pnl=0` — modern resolver semantics, excluding the `TIME_EXIT` zero-pnl resolver-artifact rows (n=1576 with pnl=0; status TIME_EXIT but resolver wrote 0 instead of intrabar-computed exit).
3. Compute PF, WR, avg_pnl, Sharpe-proxy (avg/SD × √252), and 14d/48h recency.
4. Cross-reference the BLOCKED_SOURCE_SYSTEMS entries in `alpha_engine/config.py:262-280` against the live stats — flag any kill whose current n / WR / PF contradicts the kill rationale.
5. Confirm Phase 3 MC candidate (`stocks_rsi2_pullback`) status — is it currently emitting, blocked, or already retired?
6. Identify resolver risk: count `TIME_EXIT` zero-pnl rows + NULL pnl_pct in closed EQUITY (Phase 4 finding).

## Inputs verified live

- `trading_picks` schema columns confirmed (`status`, `pnl_pct`, `source_system`, `strategy`, `category`).
- Status enum observed: `ACTIVE, EXPIRED, LOST, OPEN, TIME_EXIT, TP_HIT, WON`.
- `pf_registry.by_asset_class_policy_clean_net` 2026-05-25T04Z baseline (CLAUDE.md): EQUITY PF 0.90 / WR 33% / n=33 — agrees with naive view direction; unified view shows class is bigger and worse than the policy-clean view suggests.

## Output

See companion result MD.
