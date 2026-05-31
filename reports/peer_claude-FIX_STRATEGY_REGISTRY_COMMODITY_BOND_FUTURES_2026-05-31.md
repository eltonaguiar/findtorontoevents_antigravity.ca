# strategy_registry asset_class fix — COMMODITY / BOND / FUTURES (2026-05-31)

**Author:** claude (peer)
**DB:** mysql.50webs.com / ejaguiar1_stocks

## TL;DR

User observation was partially right but wrong-framed: COMMODITY/BOND/FUTURES strategies are NOT missing from `strategy_registry` — every strategy emitting those picks already has a registry row. The real bug is that they are **mislabeled as `asset_class='CRYPTO'`** even though their pick stream is 70-100% commodity/bond/futures.

That is functionally identical to "missing": any code path that filters `strategy_registry WHERE asset_class='COMMODITY'` (or BOND/FUTURES) gets zero rows and the class cannot be promoted/scored.

Fix: surgical `UPDATE` of 11 high-confidence strategies (dominant emission category, n>=10 picks, >=50% share). Originals preserved in `ejaguiar1_backups.strategy_registry_backup_20260531`.

## Diagnosis

### Q1 — registry asset_class distribution (pre-fix)

| asset_class | n     |
|-------------|-------|
| CRYPTO      | 1215  |
| MULTI       | 695   |
| EQUITY      | 17    |
| FOREX       | 12    |
| COMMODITY   | 0     |
| BOND        | 0     |
| FUTURES     | 0     |

### Q2 — trading_picks per target category

| category   | n_distinct_strategies | n_picks |
|------------|----------------------:|--------:|
| commodity  | 19                    | 6866    |
| futures    | 15                    | 430     |
| bond       | 11                    | 164     |

### Q3 — gap

0 truly missing rows. All 45 strategies emitting BOND/COMMODITY/FUTURES picks are present in `strategy_registry` — but registered as `asset_class='CRYPTO'` (7460 picks mislabeled).

## Backup

`ejaguiar1_backups.strategy_registry_backup_20260531` — full 1939 rows copied (count verified pre-UPDATE).

Recovery:
```sql
UPDATE ejaguiar1_stocks.strategy_registry sr
JOIN ejaguiar1_backups.strategy_registry_backup_20260531 bk ON sr.id = bk.id
SET sr.asset_class = bk.asset_class, sr.notes = bk.notes
WHERE sr.notes LIKE '%[2026-05-31 auto-fix]%';
```

## Reframed Step 4 — UPDATE (not INSERT)

Selection rule: total picks >=10 AND dominant category in {COMMODITY, BOND, FUTURES} AND dominant share >=50%.

### 11 strategies updated

| strategy                       | new asset_class | dom_n | total | %    |
|--------------------------------|-----------------|------:|------:|-----:|
| bond_yield_momentum            | BOND            | 16    | 23    | 70%  |
| cftc_cot_commercial_signal     | COMMODITY       | 55    | 55    | 100% |
| contango_roll_yield            | FUTURES         | 10    | 10    | 100% |
| cot_positioning                | COMMODITY       | 119   | 119   | 100% |
| cta_commodity_momentum_term    | COMMODITY       | 2012  | 2012  | 100% |
| cta_golden_cross_200           | COMMODITY       | 255   | 332   | 77%  |
| futures_bb_mean_reversion      | COMMODITY       | 251   | 460   | 55%  |
| futures_connors_rsi2           | FUTURES         | 373   | 495   | 75%  |
| futures_cross_asset_momentum   | FUTURES         | 14    | 14    | 100% |
| futures_ema_stack_momentum     | COMMODITY       | 308   | 344   | 90%  |
| futures_momentum               | COMMODITY       | 2063  | 2079  | 99%  |

### Deferred (not updated)

- `cta_cross_asset_tsmom` (COMMODITY 46% / FOREX 46% / EQUITY 5% / BOND 3%) — genuinely multi-asset.
- `non_crypto_consensus` (FOREX 74% / COMMODITY 22%) — flipping solo would misroute COMMODITY picks; should be FOREX or MULTI.
- `combined_confidence` (CRYPTO 42% / COMMODITY 28% / FOREX 27%) — true multi.
- `bond_yield_curve_slope` (n=6 < 10 floor), `commodity_tsmom_12m` (n=9), and all other n<10 strategies.

Audit trail in `notes`: `[2026-05-31 auto-fix] asset_class CRYPTO->COMMODITY (dominant pick category: 2012/2012 = 100%)`.

## Verify

### Post-fix registry distribution

| asset_class | n    | delta |
|-------------|-----:|------:|
| CRYPTO      | 1204 | -11   |
| COMMODITY   | 7    | +7    |
| FUTURES     | 3    | +3    |
| BOND        | 1    | +1    |

### Pick-stream coverage

| category  | matched | mislabeled | unregistered | picks |
|-----------|--------:|-----------:|-------------:|------:|
| BOND      | 16      | 148        | 0            | 164   |
| COMMODITY | 5063    | 1803       | 0            | 6866  |
| FUTURES   | 397     | 33         | 0            | 430   |

74% of COMMODITY picks and 92% of FUTURES picks now map to a correctly-labeled registry row. Remaining mislabeled are the deferred multi-class strategies above.

## Root cause

`strategy_registry.asset_class` defaults to `'CRYPTO'`. Seed/auto-discovery scripts likely INSERT without overriding it, so non-crypto strategies inherit the default.

Recommend follow-up PR:
1. Patch seed scripts to set `asset_class` from `module_file` path (e.g. `baby_strategies/futures_*` -> FUTURES, `cta_commodity_*` -> COMMODITY, `bond_*` -> BOND).
2. CI guard: fail seed if a new row has `asset_class='CRYPTO'` AND `strategy_id` matches `^bond_|^futures_|^cot_|^cta_commodity|^commodity_`.

## Follow-ups

1. Multi-class reclassification pass — `cta_cross_asset_tsmom`, `non_crypto_consensus`, `combined_confidence`. (MULTI already exists in the enum.)
2. Verify `audit_dashboard/data/pf_registry.json` and `money_ready_verdict.json` regenerate cleanly after the UPDATE.
3. Repeat scan for EQUITY/ETF/STOCKS — same pattern likely (e.g. `luxalgo_confluence`, `etf_*`, `vix_reversal`).

## Reproducer (local /tmp/, gitignored)

- `/tmp/registry_diagnose.py` — Q1/Q3/DESCRIBE
- `/tmp/registry_diagnose2.py` — gap classification
- `/tmp/registry_diagnose3.py` — dominant-category recommendation
- `/tmp/registry_fix.py` — backup + UPDATE + verify
