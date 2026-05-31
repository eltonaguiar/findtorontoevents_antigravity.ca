# Result — INCIDENT_STOCKS #7 residual mistag backfill (2026-05-31)

## Status: DONE — DB_FIX

## What was done
1. Verified live state in `ejaguiar1_stocks.trading_picks` (2026-05-31):
   - (a) `category='crypto'` AND symbol not crypto-like: **10 rows**
   - (b) `category IN ('equity','stock','stocks')` AND symbol IS crypto: **9 rows**
   - **Residual after prior PR #147 cleanups: 19 rows total** (well under 100 → inline backfill).

2. Created targeted backup table
   `ejaguiar1_backups.trading_picks_pre_stocks7_mistag_20260531` (19 rows of the affected
   ids, full column set). Check constraints stripped from CREATE to avoid name collision
   with existing tables in the backups DB; data fidelity unchanged.

3. Applied 19 UPDATE statements assigning correct `category` based on symbol suffix:
   - `=X` → `forex` (5 rows: USDJPY/EURGBP×3/AUDUSD/AUDJPY)
   - `=F` → `commodity` (5 rows: SI=F×2, PL=F, CT=F, ... )
   - USDT/USDC/`-USD` / CLUSD / BCH-USD → `crypto` (9 rows)

   Authority: `symbol` column (not `id`, which had pre-existing copy-paste mismatches in
   the `iso_regime_terminal_*` family — separate incident, not addressed here).

4. Post-fix verification: residual (a)=0, residual (b)=0.

## Before / After (full `trading_picks` distribution)

| category   | before | after | delta |
|------------|--------|-------|-------|
| crypto     | 16102  | 16101 | -1    |
| forex      | 14868  | 14874 | +6    |
| commodity  | 6512   | 6516  | +4    |
| equity     | 2007   | 2001  | -6    |
| stocks     | 267    | 264   | -3    |
| (others)   | unchanged | unchanged | 0 |

Net effect: 10 crypto-tagged forex/commodity rows moved out of CRYPTO bucket; 9
crypto-symbol rows moved out of EQUITY/STOCKS into CRYPTO. EQUITY class metrics
on /audit are now marginally more honest (the 9 misattributed rows — 2 EXPIRED,
4 SL_HIT, 2 TP_HIT, 1 LOST — no longer pollute EQUITY PF/WR).

## Files / PR
- Plan: `reports/peer_claude-stocks7-mistag-backfill_plan_2026-05-31.md`
- Result: this file
- PR: writeup branch `fix/stocks7-mistag-residual-backfill-2026-05-31` (docs-only — DB
  mutation already committed; PR carries plan + result for review trail).

## Edge impact
- EQUITY 9 rows removed → cleaner per-class PF/WR going forward.
- CRYPTO 1 row net change → negligible at n=16k.
- Source-code root cause already fixed in PR #147 (MERGED). Recurrence prevented by
  `alpha_engine/mysql_trading_sync.py:pick_to_row` classifier-override defense-in-depth.

## Follow-ups (out of scope)
- `iso_regime_terminal_*` ids embed equity tickers (SPY/AMD/QQQ) while symbol col is
  crypto (BNBUSDT/LINKUSDT/AVAXUSDT) — id/symbol mismatch from a prior copy-paste bug.
  Filed as a separate incident; not addressed by this backfill.
- The 240 rows with `category=''` (empty string) — likely a feed parser missing-default
  bug; not in scope of STOCKS #7 cross-class mistag.
