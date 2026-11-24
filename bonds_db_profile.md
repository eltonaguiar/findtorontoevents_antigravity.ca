# backups DB Profile (ejaguiar1_backups)

**Generated:** 2026-11-16  
**Connection:** mysql.50webs.com / ejaguiar1_backups / backups1234560  
**Tables:** 414 (brief said 412)  
**Total Rows:** 34,580,324  
**Total Size:** 33.65 GB

---

## Summary of Findings

| Category | Count | Notes |
|----------|-------|-------|
| Production Duplicates | 333 | `stocks__*` prefixed tables mirroring production stocks DB |
| Only Surviving Copies | 10 | Tables in backups that do NOT exist in production |
| Orphaned (Zero-Row) | 5 | `INCIDENT_*` tables created but never populated |
| Stale Snapshots | ~85 | Tables from May/June 2026 (4-6 months old) |
| Row Count Anomalies | 20+ | Backup has MORE rows than production (possible prod data loss) |

---

## 1. Production Duplicates (`stocks__*` prefix)

**333 tables** with `stocks__` prefix are backup copies of production `ejaguiar1_stocks` DB.

**Comparison with production:**
- 323 tables matched by base name (after stripping `stocks__` prefix)
- 10 tables exist ONLY in backups (not in production)
- 86 tables exist in production but not in backups
- 20+ tables have **MORE rows in backup than production**

**Largest duplicate:**
| Table | Backup Rows | Prod Rows | Diff |
|-------|-------------|-----------|------|
| `bt_backtest_trades` | 31,010,964 | 27,212,129 | +3.8M rows |
| `at_filter_log` | 810,353 | 505,080 | +305k rows |
| `at_raw_picks` | 137,455 | 97,195 | +40k rows |
| `at_discord_notifications` | 40,936 | 4,637 | +36k rows |

**Interpretation:** Either:
1. Production experienced data loss/corruption after backup snapshot
2. Backup was taken at a later point than production's current state
3. Production DB was rebuilt/reset from a subset of data

---

## 2. Only Surviving Copies (CRITICAL)

**10 tables** in backups DB that do NOT exist in production stocks DB:

| Table | Rows | Size (MB) |
|-------|------|-----------|
| `stocks__at_raw_picks_bak_20260518` | 127,612 | 285.39 |
| `stocks__at_signal_outcomes_20260531` | 106,457 | 31.61 |
| `stocks__at_signal_outcomes_100x_dedup_20260531` | 99,760 | — |
| `stocks__trading_picks_trust_backfill_20260531` | 8,060 | — |
| `stocks__trading_picks_pnl_fixes_20260531` | 1,230 | — |
| `stocks__trading_picks_ghost_dedup_20260531` | 243 | — |
| `stocks__trading_picks_stocks_7_backfill_20260531` | 105 | — |
| `stocks__at_signal_outcomes_outcome_fixes_20260531` | 88 | — |
| `stocks__at_signal_outcomes_cot_dedup_20260531` | 21 | — |
| `stocks__at_raw_picks_forex_clamp_20260531` | 2 | — |

**Recommendation:** These are the ONLY copies of this data. If production lost these tables due to migration/refactor, these backups are the sole recovery source.

---

## 3. Orphaned Tables (Zero-Row INCIDENT tables)

**5 tables** created as part of incident response but never populated:

| Table | Created | Size |
|-------|---------|------|
| `INCIDENT_COMMODITIES_pre_cot_reconcile_20260531` | 2026-05-31 04:49:50 | 0.02 MB |
| `INCIDENT_OVERALL_backup_2026_05_31` | 2026-05-31 02:46:32 | 0.02 MB |
| `INCIDENT_OVERALL_bk_20260610T182348Z` | 2026-06-10 18:23:49 | 0.02 MB |
| `INCIDENT_OVERALL_pre_cot_dedup_close_20260531` | 2026-05-31 03:58:59 | 0.02 MB |
| `INCIDENT_OVERALL_pre_ipo_disclaim_20260531` | 2026-05-31 04:13:26 | 0.02 MB |

**Recommendation:** Safe to DROP. These are artifacts of failed/partial incident recovery operations.

---

## 4. Stale Snapshots

**85+ tables** are historical snapshots from May/June 2026:

- **46 tables** created May 2026
- **39 tables** created June 2026

**Key staleness indicator:**
- `stocks__trading_picks` snapshot: **2026-05-17 05:43:32**
- Production `trading_picks` live: **2026-11-16 04:54:08** (6 months later)

**Recommendation:** 
- Archive tables >90 days old to cold storage
- Keep only the most recent snapshot per table family
- Consider dropping tables where production has caught up

---

## 5. Largest Tables (by Row Count)

| Table | Rows | Size (MB) | Notes |
|-------|------|-----------|-------|
| `stocks__bt_backtest_trades` | 31,010,964 | 30,698.75 | 91% of total DB size |
| `stocks__at_filter_log` | 810,353 | 215.55 | Algorithm filter logs |
| `at_signal_outcomes_incident_91_dedup_20260605T045939Z` | 240,045 | 63.69 | Incident dedup snapshot |
| `at_signal_outcomes_incident_91_dedup_20260605T050028Z` | 238,513 | 63.69 | Duplicate incident snapshot |
| `at_raw_picks_backup_2026-05-31T04:05:57Z` | 146,544 | 292.42 | Raw picks snapshot |

**Note:** `stocks__bt_backtest_trades` alone is 30GB. This is a massive historical backtest dataset.

---

## 6. Table Prefix Distribution

| Prefix | Count | Notes |
|--------|-------|-------|
| `trading_picks` | 14 | Multiple snapshots + variants |
| `at_pick_outcomes` | 6 | Outcome tracking variants |
| `INCIDENT_OVERALL` | 6 | Incident recovery attempts |
| `at_raw_picks` | 5 | Raw signal snapshots |
| `INCIDENT_COMMODITIES` | 3 | Commodity incident tables |
| `strategy_registry` | 2 | Strategy metadata backups |
| `INCIDENT_BONDS` | 2 | Bond incident tables |

---

## 7. Recommendations

### Immediate Actions
1. **DO NOT DROP** the 10 "only surviving copy" tables — they are irrecoverable data
2. **DROP** the 5 zero-row INCIDENT tables (0.1 MB total)
3. **ARCHIVE** tables with `2026-05` or `2026-06` timestamps to cold storage

### Data Recovery Investigation
- Compare `stocks__bt_backtest_trades` (31M rows) vs production `bt_backtest_trades` (27M rows)
- Investigate why production has 4M fewer rows — possible data loss
- Check if production `at_raw_picks` (97k rows) is missing 40k rows present in backup

### Storage Optimization
- The 333 `stocks__*` tables are ~33GB of duplicate data
- Consider:
  - Dropping `stocks__*` tables if production is confirmed healthy
  - Or keeping only the "only surviving copy" tables and dropping the rest
  - Or maintaining as verified backup with periodic sync

### Backup Strategy Review
- Current backups appear to be **one-time snapshots**, not continuous replication
- No backup newer than June 2026 for most tables
- Production has diverged significantly since backup time
- Recommend implementing incremental/continuous backup for critical tables

---

## 8. Technical Notes

- **Naming convention:** `stocks__` prefix indicates dump-restore from production `ejaguiar1_stocks`
- **Timestamp patterns:** Tables use formats `YYYYMMDD`, `YYYY-MM-DDTHH:MM:SSZ`, `bk_YYYYMMDDTHHMMSSZ`
- **Incident artifacts:** `INCIDENT_*` and `*_incident_*` tables are from May/June 2026 incident recovery
- **Empty tables:** 5 tables have 0 rows (all INCIDENT-related)

---

**Report Location:** `backups_db_profile.md` (this file)  
**Raw Data:** `scratch/backups_profile.json`, `scratch/compare.json`, `scratch/orphan.json`  
**Profile Script:** `scratch/final.py`
