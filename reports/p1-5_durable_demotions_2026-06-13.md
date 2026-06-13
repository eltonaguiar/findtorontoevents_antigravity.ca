# P1-5 durable demotions — setup, dry-run, and operator approval gate

**Date:** 2026-06-13
**Author:** claude (session worker)
**Worktree:** `feat-minimax-next-steps`
**Commit-of-record target:** (not yet committed — see "Commit plan" below)

## 1. Setup

This report ships the dry-run output and tooling for a **one-time, operator-approved
MySQL mutation** that makes the P1-5 portfolio demotions durable. Per PR #581 body
("P1-5 (follow-up)"): the prior commit `a82ac1b57f` demoted 5 conservative portfolios
in `audit_dashboard/data/pf_portfolios.json` and the per-portfolio detail files, but
those JSONs are **regenerated daily** by the GHA workflow from the MySQL `PF_PORTFOLIO`
table, so the demotions would be silently overwritten on the next regen.

The mitigation: surgical, transactional UPDATE on the underlying `PF_PORTFOLIO` rows.
A new tool, `tools/persist_p1_5_demotions.py`, performs the migration (ALTER TABLE for
the two missing reason/timestamp columns) + UPDATE in a single transaction with
verify-after-commit. Default is `--dry-run` / ROLLBACK; `--execute` commits.

## 2. Previous demotion commit summary (`a82ac1b57f`)

```
feat(portfolios): P1-5 demote 5 confirmed losing conservative portfolios to shadow_paper_only
Author: eltonaguiar  Date: 2026-06-12 20:10 UTC

5 demoted (PF<0.5, WR<=20%, negative Sharpe):
  aimlapi_gpt4o__conservative       PF=0.10 WR=11% sharpe=-7.09
  gh_models_gpt4o__conservative     PF=0.10 WR=11% sharpe=-7.06
  gpt4o__conservative               PF=0.11 WR=10% sharpe=-6.52
  gpt5_chat__conservative           PF=0.32 WR=20% sharpe=-4.98
  deepseek_r1__conservative         PF=0.43 WR=20% sharpe=-3.16
Borderline groq_kimi_k2__conservative (PF=0.63 Sharpe=+0.69) KEPT ACTIVE.
Touched ONLY per-portfolio JSONs — pf_registry.json and money_ready_verdict.json
are strategy×class aggregations, not portfolio statuses.
```

Fields set in each per-portfolio JSON:
- `status: "shadow_paper_only"`
- `status_reason: "DEMOTED_2026-06-12: PF<0.5, WR<=20%, negative Sharpe, n_closed>=9 — fails TIER-2 by all measures. See PLAN_INSIGHTS_NEXT_STEPS_TRACKER P1-5."`
- `status_changed_at: "2026-06-12T20:10:00Z"`

## 3. Live DB schema + current state of the 5 portfolios

**Table:** `ejaguiar1_stocks.PF_PORTFOLIO` (123 rows total)
**Identifier column:** `portfolio_key` (UNIQUE), NOT `name`.

Schema (current — confirmed via `DESCRIBE PF_PORTFOLIO` 2026-06-13 04:57 UTC):
```
id                bigint       NO   PRI  auto_increment
portfolio_key     varchar(255) NO   UNI
model_id          varchar(255) YES  MUL
risk_appetite     varchar(32)  NO
kind              varchar(16)  NO        default 'model'
starting_nav      decimal(18,4) NO        default 100000.0000
status            varchar(16)  NO   MUL  default 'active'
config_snapshot   json         YES
created_at        datetime     NO        default CURRENT_TIMESTAMP
```

**Schema gap:** `status_reason` and `status_changed_at` columns do NOT exist
yet. The previous commit added those fields directly to the JSON files; they
will be wiped on next regen. To make them durable, this script ships an
idempotent ALTER TABLE migration as part of the same transaction.

**Current state of the 5 portfolios (all `active` — demotions have NOT been
propagated to MySQL yet):**
```
id   portfolio_key                       model_id            risk_appetite  status
16   aimlapi_gpt4o__conservative         aimlapi_gpt4o       conservative   active
13   deepseek_r1__conservative           deepseek_r1         conservative   active
19   gh_models_gpt4o__conservative       gh_models_gpt4o     conservative   active
58   gpt4o__conservative                 gpt4o               conservative   active
70   gpt5_chat__conservative             gpt5_chat           conservative   active
```
All 5 found. 5/5 of the demotion set is present in MySQL (no missing portfolios).

## 4. Backup confirmation

Pre-mutation backup created via the canonical operator-approved tool:
```
$ python3 tools/db_backup_to_backups.py --source-db ejaguiar1_stocks --tables PF_PORTFOLIO
  [PF_PORTFOLIO] OK: ejaguiar1_backups.PF_PORTFOLIO_20260613T045737Z src=123 dst=123
Summary: OK: PF_PORTFOLIO
```

**Backup file:** `ejaguiar1_backups.PF_PORTFOLIO_20260613T045737Z` (123 rows).
Datestamped suffix follows the tool's `YYYYMMDDTHHMMSSZ` convention; idempotent
skip would re-create only if the suffix changes. Restore path (if ever needed):
```sql
RENAME TABLE ejaguiar1_stocks.PF_PORTFOLIO TO ejaguiar1_stocks.PF_PORTFOLIO_broken;
CREATE TABLE ejaguiar1_stocks.PF_PORTFOLIO LIKE ejaguiar1_backups.PF_PORTFOLIO_20260613T045737Z;
INSERT INTO ejaguiar1_stocks.PF_PORTFOLIO SELECT * FROM ejaguiar1_backups.PF_PORTFOLIO_20260613T045737Z;
```
(Or use the tool's reverse path; full procedure is in `docs/DB_BACKUP_SCRIPT.md`.)

The audit-log write step of the backup tool reported a minor non-fatal warning
(`Unknown column 'ts_utc' in 'field list'` for `db_audit_log`); the table
contents are intact, and the warning is a pre-existing schema-doc drift, not
a mutation result.

## 5. Demotion script design — `tools/persist_p1_5_demotions.py`

**Location:** `/home/eaguiar2015/findtorontoevents_antigravity.ca-worktrees/feat-minimax-next-steps/tools/persist_p1_5_demotions.py`
**Size:** 150 lines (docstring + safety commentary drives the count; executable logic is ~60 lines)

**Phases:**
1. **Phase 1 — Idempotent migration.** Check `information_schema.COLUMNS` for
   `status_reason` / `status_changed_at`; `ALTER TABLE PF_PORTFOLIO ADD COLUMN`
   for any that are missing. No-op if both already exist.
2. **Phase 2 — Transactional UPDATEs.** For each of the 5 portfolio_keys:
   - SELECT current status (idempotency / skip-if-already)
   - If `NOT_FOUND` (missing from DB) → report + skip, do NOT fail
   - If already `shadow_paper_only` → report + skip (re-runnable)
   - Otherwise UPDATE status, status_reason, status_changed_at
3. **Phase 3 — Post-UPDATE verify.** SELECT back the 5 rows; print final state.
4. **Phase 4 — COMMIT** (or ROLLBACK in dry-run mode).
5. **Exception safety:** any error → `conn.rollback()` + return code 1.

**CLI:**
```bash
python3 tools/persist_p1_5_demotions.py            # default: dry-run / rollback
python3 tools/persist_p1_5_demotions.py --execute  # actually commit
```

**CLAUDE.md "Strategy demotion" rule compliance:**
The rule directs us to `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` and
`docs/MUTATION_THREE_AXIS_PROTOCOL.md` before demoting. The P1-5 demotion
itself was an EXPLICIT operator-approved per-portfolio status change
(conservative-only, all 5 with PF<0.5, WR<=20%, n>=9 closed, neg Sharpe),
not a strategy `BLOCKED_SOURCE_SYSTEMS` expansion. The "investigation before
kill" ladder is the wrong gate for *this* script, which executes an already-
approved demotion durably. The script does **not** add any new strategy to
`BLOCKED_SOURCE_SYSTEMS`, mutate the alpha_engine, or alter the
forward-test/cohort pipeline. It only persists an already-committed decision
into MySQL.

What this script DOES change:
- `PF_PORTFOLIO.status` (one VARCHAR column) for 5 named rows
- `PF_PORTFOLIO.status_reason` and `PF_PORTFOLIO.status_changed_at`
  (two new columns, NULL until set)

What this script does NOT change:
- No `BLOCKED_SOURCE_SYSTEMS` or `BLOCKED_SOURCE_SYMBOL_PAIRS` entries
- No `BLOCKED_DIRECTION_TRIPLES`
- No scanner / quality_gates / forward_validator code
- No other rows in `PF_PORTFOLIO` (all 5 are explicitly named in
  `DEMOTED`; the SQL is `WHERE portfolio_key = <name>` per row, not
  a bulk `WHERE risk_appetite='conservative'` predicate)

## 6. SQL that will be executed (dry-run output)

```
$ python3 tools/persist_p1_5_demotions.py

[p1-5] mode=DRY-RUN target=PF_PORTFOLIO (ejaguiar1_stocks) n=5
[p1-5] SQL (migration): ALTER TABLE PF_PORTFOLIO ADD COLUMN status_changed_at DATETIME NULL
[p1-5] SQL (migration): ALTER TABLE PF_PORTFOLIO ADD COLUMN status_reason TEXT NULL
[p1-5] BEGIN TRANSACTION (will ROLLBACK)
[p1-5] SQL: UPDATE PF_PORTFOLIO
       SET status='shadow_paper_only',
           status_reason=<P1-5 reason>,
           status_changed_at='2026-06-13 04:50:00'
     WHERE portfolio_key=<PORTFOLIO_KEY_1>     -- aimlapi_gpt4o__conservative
[p1-5] SQL: UPDATE PF_PORTFOLIO
       SET status='shadow_paper_only',
           status_reason=<P1-5 reason>,
           status_changed_at='2026-06-13 04:50:00'
     WHERE portfolio_key=<PORTFOLIO_KEY_2>     -- gh_models_gpt4o__conservative
[p1-5] SQL: UPDATE PF_PORTFOLIO
       SET status='shadow_paper_only',
           status_reason=<P1-5 reason>,
           status_changed_at='2026-06-13 04:50:00'
     WHERE portfolio_key=<PORTFOLIO_KEY_3>     -- gpt4o__conservative
[p1-5] SQL: UPDATE PF_PORTFOLIO
       SET status='shadow_paper_only',
           status_reason=<P1-5 reason>,
           status_changed_at='2026-06-13 04:50:00'
     WHERE portfolio_key=<PORTFOLIO_KEY_4>     -- gpt5_chat__conservative
[p1-5] SQL: UPDATE PF_PORTFOLIO
       SET status='shadow_paper_only',
           status_reason=<P1-5 reason>,
           status_changed_at='2026-06-13 04:50:00'
     WHERE portfolio_key=<PORTFOLIO_KEY_5>     -- deepseek_r1__conservative
[p1-5] DRY-RUN complete; ROLLBACK (no changes written)
[p1-5] --- SUMMARY ---
  <PORTFOLIO_KEY_1>     rows=None state=DRY_RUN
  <PORTFOLIO_KEY_2>     rows=None state=DRY_RUN
  <PORTFOLIO_KEY_3>     rows=None state=DRY_RUN
  <PORTFOLIO_KEY_4>     rows=None state=DRY_RUN
  <PORTFOLIO_KEY_5>     rows=None state=DRY_RUN
```

The `<P1-5 reason>` placeholder in the dry-run print is a display-time
shortening; the actual `status_reason` value sent to MySQL is:
```
DEMOTED_2026-06-13 (P1-5 durable): PF<0.5, WR<=20%, negative Sharpe, n_closed>=9 — fails TIER-2. See commit a82ac1b57f + tracker P1-5.
```

## 7. PENDING OPERATOR APPROVAL — script staged but NOT executed

**The script is shipped dry-run only. The actual UPDATE was NOT executed.**

Per CLAUDE.md "do NOT autonomously produce code-diff PRs from a single agent's
imagined function names + line numbers" + the explicit task constraint
("DO NOT execute the actual UPDATE without explicit operator approval. Ship
the script + dry-run output, then STOP."), this report stops at the staging
phase. The next steps (after operator approval) are:

1. **Operator reviews** the dry-run SQL above.
2. **Operator runs** (one-liner reproducer):
   ```bash
   python3 tools/persist_p1_5_demotions.py --execute
   ```
3. **Operator verifies**:
   ```sql
   SELECT portfolio_key, status, status_changed_at
   FROM ejaguiar1_stocks.PF_PORTFOLIO
   WHERE portfolio_key IN (
     'aimlapi_gpt4o__conservative',
     'gh_models_gpt4o__conservative',
     'gpt4o__conservative',
     'gpt5_chat__conservative',
     'deepseek_r1__conservative'
   );
   ```
   All 5 should show `status='shadow_paper_only'` and a non-NULL
   `status_changed_at='2026-06-13 04:50:00'`.
4. **Operator triggers the daily GHA regen** (or waits for it): after
   `audit-dashboard.yml` runs, the next `audit_dashboard/data/pf_portfolios.json`
   will inherit the `shadow_paper_only` status from MySQL — i.e., the
   demotion is now durable.

## 8. Reproducer (one-liner to actually run after approval)

```bash
# Prereq: backup must already exist (file: ejaguiar1_backups.PF_PORTFOLIO_20260613T045737Z)
cd /home/eaguiar2015/findtorontoevents_antigravity.ca-worktrees/feat-minimax-next-steps
python3 tools/persist_p1_5_demotions.py --execute
```

Re-running the script after a successful `--execute` is safe: the idempotency
check (`SELECT status FROM PF_PORTFOLIO WHERE portfolio_key=...`) will report
`ALREADY_DEMOTED` for all 5 and skip the UPDATE.

## 9. Verif commands

```bash
# 1) Syntax check (already passed 2026-06-13 04:58 UTC, exit 0)
python3 -m py_compile tools/persist_p1_5_demotions.py

# 2) Dry-run (default; no commit)
python3 tools/persist_p1_5_demotions.py

# 3) Post-execute verify (after operator approval + --execute)
python3 -c "
from tools.db_env import get_stocks_creds
import pymysql
c = pymysql.connect(**get_stocks_creds())
cur = c.cursor()
cur.execute(\"\"\"
    SELECT portfolio_key, status, status_changed_at
    FROM PF_PORTFOLIO
    WHERE portfolio_key IN (
        'aimlapi_gpt4o__conservative',
        'gh_models_gpt4o__conservative',
        'gpt4o__conservative',
        'gpt5_chat__conservative',
        'deepseek_r1__conservative'
    )
    ORDER BY portfolio_key
\"\"\")
for r in cur.fetchall(): print(r)
"
# Expected: all 5 with status='shadow_paper_only', changed_at=2026-06-13 04:50:00
```

## 10. Commit plan (NOT YET COMMITTED)

Per task step 9, the planned commit is:
```bash
git add tools/persist_p1_5_demotions.py reports/p1-5_durable_demotions_2026-06-13.md
git commit -m "feat(audit): P1-5 durable demotions script (operator approval required)
...
Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

The commit message explicitly states "operator approval required" so any
peer who pulls the script understands it ships dry-run by default and
the executable form needs explicit operator invocation.

## 11. Open questions for operator

1. **Do you approve running `--execute` on production MySQL today?**
   If yes, run:
   ```bash
   python3 tools/persist_p1_5_demotions.py --execute
   ```
2. **Do you want the ALTER TABLE to be a separate PR** (e.g., a migration-only
   commit that runs once and is then removed from the script) so future runs
   of the script don't repeat the column-add? The current implementation is
   idempotent (information_schema check), so the migration is a no-op on
   re-run; keeping it in the same script is the simpler and safer default.
3. **Should the daily GHA `audit-dashboard.yml` be re-run after `--execute`** to
   confirm the JSON regen picks up the new MySQL state? This is not strictly
   necessary (the next scheduled run will do it), but it shortens the
   "demotion is durable" verification window from ~24h to ~5min.
4. **`status_changed_at` is stored as `DATETIME` (no timezone) per the existing
   schema convention.** UTC value `2026-06-13 04:50:00` is used. If the export
   script later adds timezone-aware formatting, this is consistent with the
   other `created_at` values in the same table.
