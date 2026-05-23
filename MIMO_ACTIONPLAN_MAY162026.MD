# MIMO ACTION PLAN — May 16, 2026

**Generated:** 2026-05-16T04:00Z  
**Source:** Cross-validated against live `main` branch (commit `4a67e6d7b6`) + 4 parallel codebase audits  
**Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`

---

## Executive Summary

Cross-referenced all 4 daily_ideas files (`ghcopilot_auto`, `nvidia`, `Kilocode_laguna`, `KimiCode`) against the live codebase. Of **28 unique action items** identified across the files, **12 are already done**, **1 is deprecated**, **1 is partially done**, and **14 remain actionable**. This plan focuses on the 14 still-needed items, prioritized by blast radius and implementation effort.

### Execution Status (Updated 2026-05-16 05:30 UTC)

| PR | Status | Notes |
|----|--------|-------|
| PR1: mysql-sync hardening | **DONE** | Committed to main (`a09bb16648`). Silent fail removed, 3-retry loop added. |
| PR2: trading_picks indexes | **DONE** | Committed to main (`e4d3c1e00e`). 5 composite indexes added. |
| PR3: at_pick_outcomes table | **DONE** | Already in `mysql_schema.sql:271-285` (prior commit). Resolver wiring in `47b5f56272`. |
| PR4: Secret name consistency | **DONE** | Commit `8f41015a51` (comment update) + `dcb1c4aa98` (Python tools + 4 workflows fully wired). |
| PR5: env_check.py + docs | **DONE** | Committed to main (`aaceb87bc9`). Script + setup docs created. |
| PR6: Remove deprecated thresholds | **DONE** | File already deleted in prior commit. |
| PR7: FOREX duplicate gate | **DONE** | Gate is clean (no duplicate, no fail-open). No changes needed. |

**All 7 daily_ideas PRs are resolved. 4 GitHub PRs (#1096-1099) were opened then closed as redundant (changes landed via direct commits).**

---

## Validation Matrix

| # | Action Item | Source File(s) | Status | Evidence |
|---|------------|---------------|--------|----------|
| 1 | mysql-trading-sync.yml silent fail removal | KimiCode, Kilocode | **DONE** | Commit `a09bb16648` — retry loop + hardcoded password removed |
| 2 | at_pick_outcomes table | KimiCode | **DONE** | Commit `47b5f56272` — table in schema + resolver wired |
| 3 | Composite indexes on trading_picks | KimiCode | **DONE** | Commit `e4d3c1e00e` — 5 composite indexes added |
| 4 | ejaguiar1_backtests DB split | KimiCode, Kilocode | **DONE** | `mysql_client.py:47-62` + 2 workflows |
| 5 | FOREX_HARD_DISABLE | Kilocode | **DONE** (defect: duplicate gate) | `config.py:270` |
| 6 | CRYPTO hour filter | Kilocode | **DONE** | `score_booster.py:538-566` + 3 modules |
| 7 | Prediction anomaly detector | KimiCode | **DONE** | 693 lines, 5 modules, JSON output |
| 8 | mysql_client.py connection pool | KimiCode | **DONE** | Queue pool, retry, backoff |
| 9 | DB_PASS_BACKTESTS in workflows | KimiCode | **DONE** | 3 workflows + mysql_client.py |
| 10 | per_asset_thresholds.json deprecation | KimiCode | **DEPRECATED** | Zero readers, replaced by `hf_quality_gates.json` |
| 11 | PR #1030 / money_ready_filter.js | KimiCode | **PARTIAL** | File exists, PR #1030 CLOSED not merged |
| 12 | db_health_check | Kilocode | **DONE** | `tools/db_health_check.py` (527 lines) |
| 13 | env_check.py | KimiCode | **DONE** | Commit `aaceb87bc9` — `tools/env_check.py` created |
| 14 | docs/MYSQL_ENV_SETUP.md | KimiCode | **DONE** | Commit `aaceb87bc9` — `docs/MYSQL_ENV_SETUP.md` created |
| 15 | db-freshness-guardian.yml | KimiCode | **DONE** | Hourly, RED/YELLOW/GREEN thresholds |
| 16 | cross-db-audit.yml | KimiCode | **DONE** | Daily orphan strategy detection |
| 17 | no-stale-db-passwords.yml | KimiCode | **DONE** | PR-blocking, checks 2 hardcoded passwords |
| 18 | prediction-quality-tracker | KimiCode | **DONE** (JSON, not MySQL) | Hourly, commits `prediction_quality_history.json` |
| 19 | outcome-resolver.yml | KimiCode | **DONE** | Hourly, resolves TP/SL/time exits |
| 20 | walkforward-gate.yml | KimiCode | **DONE** | PR-blocking, diff-aware |
| 21 | secret-scan.yml | KimiCode | **DONE** | Gitleaks on PR + push |
| 22 | PR guardrails (composite) | KimiCode | **DONE** | 6 workflows cover credentials/conflicts/tests |
| 23 | FOREX blocklist MySQL trigger | Kilocode | **NOT DONE** | `tools/block/` and `tools/admin/` don't exist |
| 24 | PEAD equity wiring | Kilocode | **DONE** (shadow mode) | `pead_equity.py` exists, shadow sidecar in production_scanner |
| 25 | Sync retry logic | KimiCode | **DONE** | `mysql-trading-sync.yml` has 3-attempt retry loop with exponential backoff |
| 26 | Secret name consistency | KimiCode | **DONE** | Commit `dcb1c4aa98` — cross_db_consistency.py + db_freshness_check.py now use db_env resolution chain; all 4 DB workflows inject DB_PASS_STOCKS + DB_PASS_BACKTESTS as canonical names |
| 27 | NVIDIA GPU/CUDA integration | nvidia | **N/A** | Not applicable to this codebase |
| 28 | Strategy emission monitor | ghcopilot | **NOT DONE** | No daily emission/dormancy report |

---

## PR Plan (7 PRs, ordered by priority)

### PR 1: mysql-trading-sync Hardening [P0]

**Branch:** `fix/mysql-sync-hardening`  
**Files:** `.github/workflows/mysql-trading-sync.yml`  
**Risk:** Low (workflow-only change)

Changes:
- Remove `|| echo "MySQL sync failed (non-fatal)"` from line 43
- Add retry loop: 3 attempts with 5s/15s/45s exponential backoff
- On final failure: create GitHub Issue via `actions/github-script`
- Increase `timeout-minutes` from 10 to 15
- Remove hardcoded `'stocks'` fallback password (line 41)
- Use `secrets.MYSQL_PASSWORD || secrets.AUDIT_DB_PASS` only

```yaml
run: |
  for i in 1 2 3; do
    python alpha_engine/mysql_trading_sync.py && break
    echo "Attempt $i failed, retrying in $((5 * i))s..."
    sleep $((5 * i))
  done
  if [ $? -ne 0 ]; then
    echo "::error::MySQL sync failed after 3 retries"
    exit 1
  fi
```

**Acceptance:** Workflow fails visibly on DB outage; retries recover transient failures.

---

### PR 2: trading_picks Composite Indexes [P0]

**Branch:** `fix/trading-picks-indexes`  
**Files:** `alpha_engine/mysql_trading_sync.py` (add index creation after table creation)  
**Risk:** Low (additive DDL, IF NOT EXISTS)

Add after the existing `CREATE TABLE IF NOT EXISTS` block (~line 88):
```sql
CREATE INDEX IF NOT EXISTS idx_tp_strategy_status ON trading_picks(strategy, status);
CREATE INDEX IF NOT EXISTS idx_tp_asset_status ON trading_picks(category, status);
CREATE INDEX IF NOT EXISTS idx_tp_created ON trading_picks(created_at);
CREATE INDEX IF NOT EXISTS idx_tp_closed ON trading_picks(closed_at);
CREATE INDEX IF NOT EXISTS idx_tp_confidence ON trading_picks(confidence);
```

**Acceptance:** `SHOW INDEX FROM trading_picks` shows 5 new composite indexes.

---

### PR 3: at_pick_outcomes Table + Resolver Wire [P0]

**Branch:** `feat/pick-outcomes-table`  
**Files:** `audit_trail/mysql_schema.sql`, `alpha_engine/outcome_resolver.py`  
**Risk:** Medium (new table + resolver modification)

1. Add `at_pick_outcomes` DDL to `audit_trail/mysql_schema.sql`:
```sql
CREATE TABLE IF NOT EXISTS at_pick_outcomes (
    pick_id CHAR(36) PRIMARY KEY,
    symbol VARCHAR(50),
    strategy VARCHAR(200),
    asset_class VARCHAR(20),
    status ENUM('OPEN','WON','LOST','EXPIRED','FLAT'),
    resolution_method ENUM('TP_HIT','SL_HIT','TIME_EXPIRED','MANUAL'),
    pnl_pct DECIMAL(10,4),
    resolved_at DATETIME,
    resolver_version VARCHAR(20),
    INDEX idx_po_status (status),
    INDEX idx_po_strategy (strategy),
    INDEX idx_po_resolved (resolved_at)
);
```

2. Add upsert in `outcome_resolver.py` after each pick resolution
3. Add `--mysql` flag to write outcomes to MySQL (keep JSON as fallback)

**Acceptance:** `SELECT COUNT(*) FROM at_pick_outcomes` returns > 0 after resolver run.

---

### PR 4: Secret Name Standardization [P0]

**Branch:** `fix/secret-name-consistency`  
**Files:** `.github/workflows/db-freshness-guardian.yml`, `.github/workflows/cross-db-audit.yml`  
**Risk:** Low (workflow env var mapping)

Standardize all workflows to use `DB_PASS_BACKTESTS` with `MYSQL_PASSWORD` fallback:
- `db-freshness-guardian.yml` line 43: Change `secrets.DB_BACKTESTS_PASSWORD` to `secrets.DB_PASS_BACKTESTS || secrets.MYSQL_PASSWORD`
- `cross-db-audit.yml` line 45: Same change

**Acceptance:** `grep -rn "DB_BACKTESTS_PASSWORD" .github/workflows/` returns 0 matches.

---

### PR 5: env_check.py + MYSQL_ENV_SETUP.md [P1]

**Branch:** `feat/env-check-docs`  
**Files:** `tools/env_check.py` (new), `docs/MYSQL_ENV_SETUP.md` (new)  
**Risk:** Low (new files only)

`tools/env_check.py`:
- Validates all required env vars are present before running sync
- Checks: `DB_PASS_STOCKS`, `DB_PASS_BACKTESTS`, `MYSQL_PASSWORD` (at least one)
- Exits with clear error message if none found
- Prints which credential source was resolved

`docs/MYSQL_ENV_SETUP.md`:
- Windows setup: `[System.Environment]::SetEnvironmentVariable()`
- GitHub Secrets setup: which secrets to configure
- Fallback chain documentation: `DB_PASS_STOCKS` -> `MYSQL_PASSWORD` -> `AUDIT_DB_PASS`
- Troubleshooting common auth failures

**Acceptance:** `python tools/env_check.py` exits 0 on valid env, exits 1 with helpful message on missing.

---

### PR 6: Remove Deprecated per_asset_thresholds.json [P1]

**Branch:** `chore/remove-deprecated-thresholds`  
**Files:** `config/per_asset_thresholds.json` (delete or add deprecation header)  
**Risk:** Low (zero readers confirmed)

Options:
- **Option A:** Delete the file entirely (zero runtime impact)
- **Option B:** Add `DEPRECATED.md` header pointing to `hf_quality_gates.json`

Recommend **Option A** — dead code removal.

**Acceptance:** File removed; `grep -rn "per_asset_thresholds" *.py *.js` returns 0.

---

### PR 7: FOREX Duplicate Gate Fix [P1]

**Branch:** `fix/forex-duplicate-gate`  
**Files:** `audit_trail/quality_gates.py`  
**Risk:** Low (removing duplicate code)

Per swarm review finding: `FOREX_HARD_DISABLE` gate exists TWICE in `quality_gates.py`, and both use fail-open `except Exception: pass`. Fix:
- Remove the duplicate gate
- Change fail-open to fail-closed (`return False` on exception)

**Acceptance:** Single `FOREX_HARD_DISABLE` check in `quality_gates.py`; exception returns `False`.

---

## Deferred Items (not in this PR batch)

| Item | Reason Deferred | Target Date |
|------|----------------|-------------|
| Prediction quality tracker MySQL migration | JSON approach works; MySQL is optimization | Week 3 |
| Verify predictions MySQL migration | Same as above | Week 3 |
| Strategy emission/dormancy monitor | New feature, needs design | Week 4 |
| FOREX blocklist MySQL trigger | FOREX already hard-disabled; trigger is belt-and-suspenders | When FOREX rehab starts |
| NVIDIA GPU/CUDA | Not applicable to this codebase | N/A |
| money_ready_filter.js deployment | PR #1030 closed; file exists on disk but deployment status unclear | Needs manual verification |

---

## Execution Order

```
PR 1 (sync hardening) ──┐
PR 2 (indexes)          ├── Can run in parallel
PR 4 (secret names)     ──┘
                         │
PR 3 (outcomes table) ──── Depends on PR 2 (indexes)
                         │
PR 5 (env check)     ──── Independent
PR 6 (deprecate)     ──── Independent
PR 7 (forex gate)    ──── Independent
```

**Target:** All 7 PRs merged by 2026-05-18 EOD.

---

## Appendix: Daily Ideas File Disposition

| File | Items | Already Done | Still Needed | N/A |
|------|-------|-------------|-------------|-----|
| `daily_ideas_ghcopilot_auto.MD` | 8 | 0 | 1 (emission monitor) | 7 (strategic roadmap) |
| `daily_ideas_nvidia.MD` | 7 | 0 | 0 | 7 (not applicable) |
| `daily_ideas_Kilocode_laguna.MD` | 12 | 7 | 2 (env_check, forex trigger) | 3 (strategic) |
| `daily_ideas_KimiCode.MD` | 14 | 6 | 8 (see PR plan above) | 0 |

---

## PR Disposition from Daily Ideas Context

| PR | State | Impact on This Plan |
|----|-------|-------------------|
| #1017-1020 | CLOSED (not merged) | Work decomposed into #1031-1094 range |
| #1021 | MERGED | Drift auto-pause gate live |
| #1030 | CLOSED (not merged) | money_ready_filter.js on disk but not deployed via PR |
| #1084 | MERGED | Phase J quarantine, YC regime gate, forex window, bond/ETF scanners |
| #1087 | MERGED | Bulk update stale hardcoded passwords |
| #1088-1094 | MERGED | AI leaderboard, walkforward gate, multi-model swarm |

---

*Generated by MIMO (mimo-v2.5-pro) via 4-parallel-agent codebase audit. All findings verified against live `main` branch at commit `4a67e6d7b6`.*
