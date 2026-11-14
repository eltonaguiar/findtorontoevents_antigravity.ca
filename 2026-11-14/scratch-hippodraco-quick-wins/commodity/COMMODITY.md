# COMMODITY Quick Wins
Audit: §4.1 — only class with intrabar PF>1: **PF 1.03 / WR 40.2%** (n=229) **WATCH**; but daily PF 0.17, DB lane stale since **2026-10-22** (oldest of all classes), walkforward n≈27, and the class carries the audit's worst garbage: `MAX|pnl_pct| = 999,999.9999`, class avg |pnl| 1,985%. Displayed COMMODITY picks score 17–21 (below its own 30 floor).

## QW-COMMODITY-1 · Quarantine the garbage PnL rows (S, part of QW-ALL-3)
- **Problem:** 999,999.9999% rows (unit/price errors — likely bad prints on illiquid contracts or `=F` mapping to wrong series) poison every commodity aggregate; avg |pnl| of 1,985% proves it's not one row.
- **Fix:** Write-time bound for COMMODITY (suggest ±60% per pick absent a documented contract event); backfill-quarantine existing |pnl|>200 rows to `pnl_pct=NULL, pnl_quarantine_reason` with counts published. Do not delete.
- **Verify:** `MAX(ABS(pnl_pct))` sane; class avg |pnl| in single digits; quarantine count in payload.

## QW-COMMODITY-2 · Restart the stalest lane (S–M)
- **Problem:** COMMODITY outcomes froze 2026-10-22 — three weeks before the audit — while the class holds the only PF>1. Nobody noticed because no per-class freshness exists (QW-ALL-1/6).
- **Fix:** Same pattern as QW-FUTURES-1: diagnose (suspect `=F` continuous-contract price fetch, incl. the hardcoded-metals fallback path `dashboard_generator.py:1453-1464` for GC/SI), add per-class MAX(closed_at) guardian gate.
- **Verify:** Fresh COMMODITY outcomes; guardian per-class table all <24h.

## QW-COMMODITY-3 · Decide what GC=F/SI=F/CL=F *are* (S)
- **Problem:** Live DB classes GC=F/SI=F/CL=F/HE=F as COMMODITY; `asset_class.py` has GLD/SLV/USO as ETF; walkforward and config maps disagree (see BOND QW-BOND-3). Exposure vs wrapper confusion splits one economic bet across two class buckets.
- **Fix:** Unified classifier with `exposure_class` (QW-ETF-4): futures = FUTURES instrument, COMMODITY exposure; report commodity stats on exposure so GC=F and GLD land together for edge purposes, separately for execution.
- **Verify:** One exposure table in payload; historical restatement disclosed.

## Subagent-refined (verified file:line)
- **Clamp-reject mechanics:** `pnl_ingest_sanity.py:12-14,36-45` clamps 999,999% to +200 where it still pollutes PF (applied at resolver `:1333,1488,1534`). Add reject path: non-crypto |pnl|>200 → `integrity_excluded=True, pnl_pct_pre_clamp=<raw>`, excluded from PF/WR (dashboard already supports integrity exclusion); clamp only within (−100,200]. One-off dry-run flag script under `tools/` for existing COMMODITY rows.
- **WATCH-only WF:** HG=F-only universe (`walkforward_validator.py:182`, PL=F emitted zero), config `min_trades=20,train=10,test=5` (`:210`) → raise to 60 per the file's own comment; keep intrabar PF 1.03 as WATCH in `money_ready_verdict`, suppress only the over-precise Sharpe. Publish `symbols_allowed/symbols_filtered_out` (`:297-302`).
- **Hardcoded metals — delete, don't just flag:** remove XAG $33.50 (`dashboard_generator.py:1453-1456`) and XAU $3050 (`:1463-1464`); symbol unpriced → `price_source="unavailable"`, excluded from PnL. (Stronger than QW-ALL-3's flag-and-exclude; adopt deletion with the flag as the mechanism.)
- **Root→class map (M, 12h):** one explicit map in `asset_class.py` by `COMMODITY_SYMBOLS` (`:62-69`); `config.py` tables and dashboard `_COMMODITY_ROOTS` (`dashboard_generator.py:3286,3497-3499`) derive/mirror it; delete duplicates. Before/after count diff on `recent_closed` required.
- **CT=F guard non-bypassable:** env-bypassable monitors (`dashboard_generator.py:5995-5996,6348-6349`, subclass-kill `:15267`, concentration WARN 0.70 `:15519-15524`) → hard-exclude `COMMODITY_BLACKLIST` from headline PF accumulator (`:15436-15482`) and publish `pnl_concentration_top_symbol` (`:15515-15524`) on the card. Expect a downward restatement — disclose it.

## QW-COMMODITY-4 · Protect the only lead: accrue, don't promote (policy, S)
- **Problem:** PF 1.03 on n=229 with a stale lane and garbage rows removed could move either way; WATCH is the right verdict and must not drift into promotion by enthusiasm.
- **Fix:** Freeze promotion; after QW-COMMODITY-1/2, require n≥300 clean intrabar rows + PF≥1.1 sustained 4 weeks before re-verdict; publish the clean-room recomputation (post-quarantine PF) as the new baseline.
- **Verify:** Baseline PF republished post-cleanup with n and date range on the card.
