# ACK: Zoo's 11-Task List + Python DB Backup Tool Shipped
**Date:** 2026-05-31 (evening, session close)
**Author:** claude-opus-4-7 (this instance)
**Trigger:** Zoo declared swarm done via `updates/2026-05-31-MASTER_AUDIT_TRUTH_LAYER_REPORT.md`; operator forwarded zoo's "next tasks" list.

## Status table — zoo's 11 items

| # | Task | Owner(s) | Verdict |
|---|------|----------|---------|
| 1 | Audit truth layer (leverage / dir-blind PnL fixes) | zoo swarm | DONE — master report committed |
| 2 | Audit dashboard accuracy banner | zoo + claude PR #207 | DONE (db_health quick-set decoded) |
| 3 | Incident page rebuild | claude wave wnkqcqck5 (~63 PRs merged + 11 closed, 86% reduction) | DONE |
| 4 | Resolver intrabar replay | claude (tournament resolver fixed, 0→13 models n≥100) | DONE for tournament; CRYPTO intrabar remains the T2 upstream blocker |
| 5 | Strategy mutation gates | claude — concentration HHI shipped, mutation-before-kill enforced | DONE |
| 6 | Confidence / trust edges | claude — `project-confidence-trust-edges-2026-05-31` | DONE (trust_score=7 = 85.9% WR n=99) |
| 7 | Edge stability automation | claude + zoo — `.github/workflows/edge-stability-update.yml` | DONE; w5734mea6 dedupe pending |
| 8 | Update all stats | claude edge-stability + zoo automation | IN PROGRESS — DEDUPE wave w5734mea6 outstanding |
| 9 | Document everything | zoo master report + claude PRs #324, #330 | DONE |
| 10 | Verify Mercury Validation | claude wkyapjb3g (Qwen verification + Mercury2 gap synthesis) | PARTIAL — plan vetted, full validation pending paper-pilot 13:30 UTC |
| 11 | **Cross-check DBs + backups** | zoo tried `mysqldump` — **FAILED (binary missing)** | **UNCOVERED → shipped tonight ↓** |

## The one uncovered item — DB backup script

Zoo discovered `mysqldump` is not installed on the 50webs host. Shipped tonight:

- `tools/db_backup_to_backups.py` — pure pymysql + `CREATE TABLE ... AS SELECT *`, writes to `ejaguiar1_backups`, logs to `ejaguiar1_backups.db_audit_log` (table created by zoo's swarm).
- `docs/DB_BACKUP_SCRIPT.md` — operator-readable when/how.

**Features:**
- Row-count guard (`--row-limit`, default 1M; SKIP_TOO_BIG → surface to operator)
- Idempotent (UTC suffix; SKIP_EXISTS if rerun in same second)
- Dry-run flag
- Exit codes: 0 OK / 1 partial / 2 failure
- Audit-log every attempt (success or skip)

**Compile-checked** via `python3 -m py_compile`. Not executed — destructive surface (writes new tables) requires operator greenlight per CLAUDE.md.

## Operator action

Before any destructive remediation tomorrow (e.g. correcting leverage column in `trading_picks`):

```bash
python3 tools/db_backup_to_backups.py \
    --source-db ejaguiar1_stocks \
    --tables trading_picks,at_raw_picks \
    --dry-run
# then, with explicit greenlight:
python3 tools/db_backup_to_backups.py \
    --source-db ejaguiar1_stocks \
    --tables trading_picks,at_raw_picks
```

## Memory linkage

Sister entry: `project-qwen-ownership-2026-05-31.md` (Mercury2 plan vetting via Qwen).
This session: `project-zoo-tasklist-ack-2026-05-31.md` (new — created tonight).

## Session close note

Paper-pilot harness emits 13:30 UTC tomorrow. **No further churn this session.**
