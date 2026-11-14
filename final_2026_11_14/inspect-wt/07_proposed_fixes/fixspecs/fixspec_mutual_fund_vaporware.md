# Fix spec — Mutual funds: honest options (vaporware today)

## Problem (evidence)
- Searched live payloads + registries (Nov 14) for mutual_fund / mf_ / VTSAX / VBTLX / VFINX:
  **no live mutual-fund picks exist** on findtorontoevents.ca/audit.
- `alpha_engine/mutual_fund_ranker.py` and `/audit/mutual-funds.html` (institutional plan item F2)
  **do not exist** in the repo (June snapshot; verify on rebase).
- What exists: DB strategy families `mutual_fund_v1/v2` (`mf_`/`mf2_` tables via
  `tools/recon_uncharted_tables.py`) and a tactical-rotation portfolio definition in
  `multi_asset/portfolio_defs.py` (Vanguard/iShares universe).

## Option A (recommended, one day): remove the claim
- Remove "mutual funds" from any live-surface asset-class claims/nav until the ranker exists.
- Honest and free. The audit already lists the class as VAPORWARE.

## Option B (one engineer-week): implement the ranker as specified in the plan
1. `alpha_engine/mutual_fund_ranker.py` — composite per the plan doc:
   `0.30·(1−ER) + 0.25·Sharpe + 0.20·Liquidity + 0.15·5y-Perf + 0.10·ESG`
   + upside/downside capture + information ratio; entry gates ER ≤ 0.50%, 5y alpha > 0,
   max-DD < 25%, AUM > $100M.
2. Universe: the Vanguard/iShares list already in `multi_asset/portfolio_defs.py` (VTSAX, VBTLX,
   VTIAX, VGSLX, VPMAX, VWELX, VGHCX, VITAX + iShares/Fidelity) — NAVs via yfinance
   (FAILOVER_API_PRIORITY already lists yfinance with mutual_fund support).
3. Weekly emit → `audit_dashboard/data/mutual_fund_rankings.json`; FTP-deploy; page
   `/audit/mutual-funds.html` rendered from it; freshness tripwire entry (168h).
4. Gate: do NOT surface until forward n≥100 resolved rows (mirror the surface_truth bridge rule).

## Acceptance test
- Either: zero mutual-fund mentions on live surfaces (Option A), or: live rankings file < 7d old
  with the stated gates visible on the page (Option B).
