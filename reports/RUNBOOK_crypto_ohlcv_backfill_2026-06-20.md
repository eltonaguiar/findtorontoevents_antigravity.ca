# Runbook — Crypto OHLCV multi-year backfill (the #1 coverage lever)
**Author:** claude-opus · 2026-06-20 · **Status:** SCOPED, greenlight-ready (NOT fired — multi-million-row write needs backup + operator OK per CLAUDE.md) · **Rationale:** `reports/MEASUREMENT_COVERAGE_BOTTLENECK_2026-06-20.md`

## Why (the unlock)
The honest intrabar ledger is 95.7% placeholders because the resolver only has price-path data for ~181 days/symbol. **Verified:** `crypto_ohlcv` holds max 4,347 bars/symbol (~181d); **0 of 315 symbols exceed 208d**. Binance serves 1h history far deeper (BTCUSDT → 2017, RENDERUSDT → 2024, probed 2026-06-20). Extending depth converts a large share of the **38,224 placeholder CRYPTO picks** into genuine first-touch resolutions → grows honest CRYPTO n far past today's 1,261, and gives H-130/H-131 (funding) + H-132 (cointegration) a fair **multi-regime** re-test instead of a single 180d window.

## Feasibility (verified)
- `tools/refresh_crypto_ohlcv.py` already supports it: `--days N` paginates 1000-bar chunks (`fetch_binance_klines_days`), no upper bound on N.
- Writes via `INSERT ... ON DUPLICATE KEY UPDATE` (`bulk_upsert`, line 222-240) — **idempotent + additive, no DELETEs**. Re-fetched existing bars rewrite the same OHLC. So the operation cannot lose existing data; the only theoretical risk is Binance returning altered values for existing timestamps (negligible).
- Universe: 447 distinct CRYPTO/MEMECOIN symbols in the pick book (`at_raw_picks`), or `--top-symbols N` by `trading_picks` volume.

## Estimates
| Scope | rows added (approx) | Binance calls | wall-clock |
|---|---|---|---|
| top-80 syms × 3yr (`--days 1095 --top-symbols 80`) | ~1.7M new (80×~26,280 − existing) | ~2,200 | ~25-30 min |
| all 447 syms × 3yr | ~9-10M new (less for newer coins) | ~12,000 | ~2.5 hr |
Final table size: ~3M (top-80) to ~11M rows (all). Manageable for InnoDB; `uk_ohlcv` unique key already indexed.

## Procedure (greenlight-required steps)
1. **BACKUP FIRST (mandatory, CLAUDE.md):** snapshot `crypto_ohlcv` (1.28M rows) to `ejaguiar1_backups`:
   `python3 tools/db_backup_to_backups.py --table crypto_ohlcv` (pymysql, row-limit guard) — or `CREATE TABLE ejaguiar1_backups.crypto_ohlcv_pre_backfill_<UTCts> AS SELECT * FROM ejaguiar1_stocks.crypto_ohlcv`.
2. **Bounded dry sanity** (optional, fetches but no write): `python3 tools/refresh_crypto_ohlcv.py --dry-run --days 1095 --top-symbols 20`.
3. **Execute bounded first:** `python3 tools/refresh_crypto_ohlcv.py --execute --days 1095 --top-symbols 80` (~25-30 min). Verify depth grew before expanding.
4. **Expand:** re-run without `--top-symbols` (all 447) once the bounded run is clean (~2.5 hr; run in background/CI).
5. **★ CRITICAL — re-run the intrabar resolver** so the new bars actually convert placeholder picks → clean resolutions (the backfill alone does NOT update `at_signal_outcomes`): trigger the outcome-resolver / `reresolve_intrabar` path over the extended history.
6. **Verify the unlock:** re-run the coverage query —
   `SELECT asset_class, COUNT(*) FROM at_signal_outcomes WHERE COALESCE(intrabar_ambiguous,0)=0 AND intrabar_pnl_pct IS NOT NULL GROUP BY asset_class` — CRYPTO clean count should jump well past 1,261. Then re-run `build_intrabar_truth_by_class.py` for honest per-class n/PF on the larger cohort.

## Scope discipline
- This does NOT help EQUITY/FOREX/COMMODITY/BOND — they need their own path feeds (equity: restore `daily_prices`, 404'd since 2026-04-29; see `MONEY_READY_NEXT_STEPS_BUILD_PLAN_2026-06-19.md`).
- Promotion stays FORWARD-lane + honest-first-touch only; the deeper history is for **candidate-selection / honest replay**, never sizing.
- Best run as a **scheduled/CI deep-backfill** (long fetch) rather than an interactive session.

## Recommendation
**GREENLIGHT the bounded top-80 run (step 1-3) first.** It's idempotent + backed-up, ~30 min, and will immediately show whether the unlock materializes (CRYPTO clean n jumps after the resolver re-run). If it does, expand to all 447. This is the single highest-leverage action in the program — above any new strategy, gate, or FRM/CFA technique.
