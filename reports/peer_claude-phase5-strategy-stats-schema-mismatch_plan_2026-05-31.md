# Phase-5 Plan — `at_strategy_stats.strategy` Schema Mismatch (Diagnose Only)

**Date:** 2026-05-31
**Scope:** docs-only diagnosis. No data change, no code change.
**Status:** OPEN — fix proposed below, ship in follow-up after data-semantics review.

## TL;DR

`at_strategy_stats.strategy` (varchar(200), PRIMARY KEY column) is populated with **confidence-tier labels** (`STRONG`, `MODERATE`, `SUPER`, `high_conviction`, `medium_conviction`, `speculative`) — not strategy/source-system names. The column is mis-named relative to what `refresh_strategy_stats_mysql()` writes into it. This is a code-side semantic bug in `audit_trail/mysql_client.py:868`, **not** a wire-up bug. The wave-3 wire-up correctly invoked the function; the function does exactly what it was coded to do.

## Evidence

### 1. Current table contents

`SELECT strategy, COUNT(*) FROM at_strategy_stats GROUP BY strategy ORDER BY 2 DESC` (ejaguiar1_stocks, 2026-05-31 04:52 UTC, n=175):

| strategy | rows |
|---|---|
| MODERATE | 58 |
| STRONG | 52 |
| SUPER | 39 |
| high_conviction | 12 |
| medium_conviction | 7 |
| speculative | 7 |

Only 6 distinct values. All six are confidence-tier labels emitted by the consensus engine, not strategy names. By contrast, `source_system` (20+ distinct values: `alpha_engine`, `crypto_ml_edge`, `kimi`, `claude_gainer_st`, `genome`, `rapid_fire`, `coinglass_strategies`, ...) is correct.

### 2. Root cause — `audit_trail/mysql_client.py:867-868`

```sql
SELECT
    COALESCE(cp.consensus_tier, 'unknown') AS strategy,
    jt.source_system,
    cp.asset_class,
    COUNT(*) AS total_picks,
    ...
FROM at_consensus_picks cp,
     JSON_TABLE(cp.source_systems, '$[*]' COLUMNS (source_system VARCHAR(100) PATH '$')) jt
WHERE cp.status != 'OPEN'
GROUP BY strategy, jt.source_system, cp.asset_class
```

`consensus_tier` is the confidence label. The query aliases it AS `strategy` and writes it into the `strategy` PRIMARY KEY column. Schema (`audit_trail/mysql_schema.sql:138`) defines `strategy VARCHAR(200) NOT NULL` with no semantic comment, so the schema itself is ambiguous, but the *intent* (and the column name) is clearly strategy name.

### 3. Wave-3 wire-up is correct

Caller chain:
- `.github/workflows/audit-dashboard.yml` invokes `tools/refresh_strategy_stats.py` hourly (per phase-4 result report).
- `sync_all_picks_to_mysql.py:1054` also calls `refresh_strategy_stats_mysql()` at end of sync cycle.
- Both call paths reach `audit_trail/mysql_client.py:854`.

The wire-up populated the table; the table populated with the wrong semantics because the SQL is wrong.

### 4. No active downstream breakage

`grep -rn "at_strategy_stats" audit_dashboard/ alpha_engine/ audit_trail/`:
- `alpha_engine/check_*_strategy_stats*.py` — diagnostic scripts only, do not feed dashboards. They aggregate `COUNT(*) GROUP BY asset_class`, so the misuse of `strategy` does not affect their output.
- `alpha_engine/calculate_statistical_edge.py` — mentioned in docstring as a data source but its actual SQL pulls from `bt_backtest_trades` + `at_signal_outcomes`, not from `at_strategy_stats`.
- `audit_dashboard/incidents.html` — incident-row text, not a consumer.
- No dashboard generator, no `dashboard_data.json` build step, no Smart-Picks/HC gate reads this column expecting strategy names.

So the live `/audit` surface is **not** producing wrong numbers because of this — it is producing **no numbers** from this table at all. The bug is dormant data with no live downstream, but it blocks the intended feedback loop (per-strategy WR/PF tracking).

### 5. Why incident #40 made this visible

Before the recent #40 fix, the function was emitting a 1062 duplicate-key error (`'STRONG-rapid_fire'` collision when `(consensus_tier, source_system)` collapsed multi-asset-class rows under the wrong PK semantics). The exception was caught at `mysql_client.py:892-895` and silently downgraded to a WARNING + return 0, so the table stayed empty for weeks. The incident-40 fix restored execution but did not fix the column-semantic root cause — the table now populates with the wrong content instead of staying empty.

## Diagnosis

**(a) refresh_strategy_stats_mysql writing the wrong column.** Confirmed.

The column was meant to store a strategy identifier. The SQL writes a confidence-tier instead. There is no second writer for this table (no other INSERT/UPDATE in the codebase touches `at_strategy_stats` — only the `DELETE` + `INSERT` pair in `refresh_strategy_stats_mysql`).

Wave-3 wire-up is innocent. The original PR #91 (commit `6cc819a5c` / `92c466bd6` — "fix(audit): add BOND to asset_class ENUM + implement refresh_strategy_stats_mysql") shipped the wrong column alias on day one.

## Proposed Fix (do NOT ship from this PR — touches data semantics)

Three options, escalating in invasiveness:

### Option A — Change the SQL alias (minimal, preserves schema)

`audit_trail/mysql_client.py:868` — replace:

```sql
COALESCE(cp.consensus_tier, 'unknown') AS strategy,
```

with:

```sql
COALESCE(jt.source_system, 'unknown') AS strategy,
```

…and drop the duplicate `jt.source_system` selection (or keep both columns identical). The PK `(strategy, source_system, asset_class)` would then be redundant on the first two columns. Net: rows become per-source-system × asset-class WR/PF stats. This is what `tools/strategy_tier_tracker.py` already produces independently — bringing this table in line with that registry.

**Risk:** PK redundancy is ugly. n drops from 175 → ~30 (one row per source_system × asset_class).

### Option B — Add `consensus_tier` column, fix `strategy` semantics (cleaner)

Migration:

```sql
ALTER TABLE at_strategy_stats
  ADD COLUMN consensus_tier VARCHAR(40) NOT NULL DEFAULT 'unknown' AFTER strategy,
  DROP PRIMARY KEY,
  ADD PRIMARY KEY (strategy, source_system, asset_class, consensus_tier);
```

…then update SQL to select strategy name (currently `source_system` is the closest proxy until a true strategy identifier exists on `at_consensus_picks`) AND `consensus_tier` separately. n grows: ~30 × 6 tiers ≈ 180 rows, which is roughly the current 175.

**Risk:** Schema migration on a live ENUM-extended table. Need `migration_add_*.sql` companion file. Coordinate with any consumer reading column order.

### Option C — Rename the column (most explicit, breaks any future consumer)

`ALTER TABLE at_strategy_stats CHANGE strategy consensus_tier VARCHAR(200) NOT NULL;` — admits the column is actually a tier and stops the semantic confusion.

**Risk:** Loses the original intent (per-strategy stats), so this is a tactical retreat, not a fix. Would need a parallel `at_consensus_tier_stats` table or to repurpose the existing one with a rename PR + schema-doc update.

### Recommendation

Ship **Option B**. It:
- preserves the original intent (per-strategy stats for the feedback loop in the major-goal-#1 wiring),
- adds the tier dimension as a first-class column so existing data is not lost,
- keeps `(strategy, source_system, asset_class, consensus_tier)` as the natural composite key,
- is the easiest to back out (`DROP COLUMN consensus_tier` if rolled back),
- aligns with the `strategy_tier_tracker.py` output shape already used in `reports/`.

Until a true strategy identifier exists on `at_consensus_picks` (e.g. a `strategy_name` column populated from the emitter), `strategy` should fall back to `source_system` — that is the most stable identifier the consensus engine currently emits, and matches how `tools/strategy_tier_tracker.py` aggregates.

## Acceptance Criteria for the Fix PR

1. `SELECT DISTINCT strategy FROM at_strategy_stats` returns source-system / strategy-engine names (`alpha_engine`, `kimi`, `crypto_ml_edge`, ...), not tier labels.
2. `SELECT DISTINCT consensus_tier FROM at_strategy_stats` returns `STRONG/MODERATE/SUPER/high_conviction/medium_conviction/speculative/unknown`.
3. `refresh_strategy_stats_mysql()` returns >0 without raising 1062 duplicate-key.
4. `tools/strategy_tier_tracker.py` and any new consumer can JOIN on `(strategy, source_system, asset_class)` without ambiguity.
5. Schema diff documented in `updates/2026-05-XX-at-strategy-stats-schema-fix.md` and `audit_trail/mysql_schema.sql` updated to match.
6. Also fix the silent-exception-swallow in `mysql_client.py:892-895` to log at ERROR (not WARNING) so future regressions don't hide for weeks (cross-link: incident #40 result report flagged this).

## Files Touched by This Diagnosis PR

- `reports/peer_claude-phase5-strategy-stats-schema-mismatch_plan_2026-05-31.md` (this file — new)

No code change. No DB change. No workflow change.
