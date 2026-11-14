# MUTUAL FUNDS — quick wins

## 1. Remove/relabel the unbuilt "mutual funds" claim (S / L)
- **Problem:** The original brief lists mutual funds as an asset class, but it is UNBUILT: `alpha_engine/mutual_fund_ranker.py` and `/audit/mutual-funds.html` do **not** exist. Only `multi_asset/portfolio_defs.py` defines the `mutual_fund` class + `tactical_fund_rotation` strategy; `_NON_CRYPTO_ASSET_CLASSES` (`dashboard_generator.py:5565`) already excludes `MUTUAL_FUND`, so nothing scans it.
- **Fix (minimal/honest):** relabel the `/audit/mutual-funds.html` reference as "planned / not built" (or delete the link). Build the ranker + page only if explicitly scoped.
- **Targets:** `audit_dashboard/institutional_readiness_plan.html:190` (the claim); reference `multi_asset/portfolio_defs.py:382/677/773`.
- **Verify:** no live page links to `/audit/mutual-funds.html`; claim reads "not built".

## 2. (If building) Scope the ranker
- New `alpha_engine/mutual_fund_ranker.py` (mirror `value_screener.py` structure) + `audit_dashboard/mutual-funds.html` + a deploy entry in `tools/deploy_audit_files.py`. Out of quick-win scope — flag for the master plan.
