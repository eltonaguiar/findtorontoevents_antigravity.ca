# Daily Idea #7 — Destructive-Op Backup Policy

**Date:** 2026-05-31
**Agent:** claude-opus-4-7 (subagent)
**Idea slug:** `destructive-op-backup-policy`
**Idea type:** Policy / tooling (NOT a statistical-edge hypothesis)

---

## 1. Verbatim user idea

> any database operation that can be destructive, should make a backup to ejaguiar1_backtests

**Suggested action (from idea file):**
> Codify and enforce: every destructive SQL op (DELETE/UPDATE/DROP/TRUNCATE) on ejaguiar1_stocks must snapshot affected rows to ejaguiar1_backtests.backup_<table>_<ts> first. Add tools/safe_destructive.py wrapper + pre-commit hook check.

---

## 2. Hypothesis (re-framed)

Because this is a **policy idea**, not an edge hypothesis, the investigation is:

> **H_policy:** A formal destructive-op archive policy is NEEDED because current production tooling routinely runs DELETE/UPDATE on `ejaguiar1_stocks` without first snapshotting affected rows, creating non-recoverable mutation risk.

Falsifiable by either:
- Showing such a policy/tool already exists AND is universally adopted (kill the idea), or
- Showing the gap is real and quantifying it (accept + design enforcement).

---

## 3. Methodology

Investigation surfaces:
1. Inventory destructive SQL usage across `tools/` + `alpha_engine/`.
2. Check whether any backup/archive helper already exists.
3. Measure adoption rate of that helper.
4. Verify whether the proposed target DB (`ejaguiar1_backtests`) is the right one — repo convention.
5. Inspect the archive log for evidence of historical use.

---

## 4. Findings — RAW (inline, no fabrication)

### 4.1 Existing infrastructure ALREADY implements this idea

```
tools/db_backup.py         -> defines archive_table_slice(source_table, where, purpose, apply, ...)
                              default backup_db="ejaguiar1_backups"  (NOT _backtests)
                              docstring: "any tool that writes to ejaguiar1_stocks ...
                              MUST call archive_table_slice(..., apply=True) immediately
                              before --apply writes."
tools/safe_db_archive.py   -> CLI wrapper. Dry-run default. Implements Hermes rule #1:
                              "Before any significant table modification, archive the
                              affected slice ... into ejaguiar1_backups.<source_table>_<purpose>_<utc_ts>"
                              + 1000-row batch insert (Hermes rule #3)
                              + row-count parity check
                              + appends entry to reports/db_archives_log.md
```

So the idea is **already codified in tooling**. The CORRECT target DB per repo convention is `ejaguiar1_backups`, not `ejaguiar1_backtests` (the latter is the tournament/backtest results DB — a different concern).

### 4.2 Adoption metric — quantitative

```bash
# Files containing DELETE FROM | UPDATE … SET | TRUNCATE | DROP TABLE
$ grep -rlE 'DELETE FROM|UPDATE [a-z_]+ SET|TRUNCATE|DROP TABLE' tools/ alpha_engine/ \
    | grep -v '\.md$' | wc -l
28

# Files that call archive_table_slice or safe_db_archive
$ grep -rl 'archive_table_slice\|safe_db_archive' tools/ alpha_engine/ | wc -l
3   # = tools/db_backup.py (defines), tools/safe_db_archive.py (CLI),
    #   tools/orphan_resolver_dryrun.py (one caller)
```

**Adoption rate: 1 / 28 = 3.6%** of destructive scripts actually use the archive helper before mutating. (Excluding the 2 files that ARE the helper.)

### 4.3 Non-adopting destructive scripts (sample, high-risk)

```
tools/fix_forex_pnl_clamping.py        — UPDATE trading_picks SET realized_pnl …
tools/clamp_forex_pnl_extremes.py      — UPDATE trading_picks
tools/resolve_stale_open_picks.py      — UPDATE trading_picks SET status, closed_at
tools/db_p0_integrity_remediation.py   — DELETE / UPDATE on ejaguiar1_stocks
tools/cleanup_ghost_rows.py            — DELETE FROM trading_picks (ghost rows)
tools/audit_won_picks_auto.py          — UPDATE trading_picks
tools/db_symbol_normalize_2026-05-18.py — UPDATE trading_picks symbol normalization
tools/audit_pick_funnel/seed_incidents_enhancements.py — UPDATE incidents
alpha_engine/active_picks_sync.py      — UPDATE / DELETE
alpha_engine/scripts/prune_correlated_picks.py — DELETE correlated picks
alpha_engine/pick_lifecycle_logger.py  — UPDATE
alpha_engine/audit_push.py             — UPDATE
alpha_engine/tournament_engine.py      — UPDATE / DELETE
```

These are exactly the scripts that have caused / can cause the audit incidents catalogued this session (resolver mislabels, ghost rows, FOREX P&L clamping mistakes, mass UEPS retag, etc.).

### 4.4 Archive log evidence

```bash
$ ls reports/db_archives_log.md
ls: cannot access 'reports/db_archives_log.md': No such file or directory
```

The log the helper appends to **does not exist** → `safe_db_archive.py --apply` has likely never been used in production. The infrastructure is dormant.

### 4.5 Recent commit signal

```
e5ab7ac01  chore(incidents): P0 batch follow-ups — resolver hardening, backup infra, verifier tools
1e3b606e6  (dup)  resolver hardening, backup infra, verifier tools
```

Active session work has been touching backup infra — corroborates that the gap is recognized but unfinished.

---

## 5. Statistical computations

This is a policy idea — no PF/WR/Wilson applicable. The relevant counts:

| Metric | Value |
|---|---|
| Destructive-SQL files in `tools/` + `alpha_engine/` | **28** |
| Files invoking `archive_table_slice` | **1** (excluding definitions) |
| Adoption rate | **3.6%** |
| `reports/db_archives_log.md` entries | **0** (file absent) |
| n threshold for `INSUFFICIENT_N` | N/A (policy, not edge) |

Bonferroni / multiple-testing: N/A.

---

## 6. Cross-check against today's NO_EDGE verdict

The session-wide swarm verdict (`NO_EDGE` across asset classes, money-ready blocked on plumbing) is *consistent* with this idea, not contradicting:

- The CLAUDE.md memory note **`Money-ready 2026-05-31 — bottleneck is PLUMBING (wire dormant backtest edges + fix resolvers/mislabels), not strategies/MC`** directly identifies the same class of failure: tools mutating `trading_picks` without traceability is *exactly* how resolver mislabels and FOREX clamping incidents survived.
- A destructive-op backup policy is therefore a **plumbing-tier fix that protects future edge investigations** — it does not create alpha, but it preserves the ground truth that every alpha audit depends on.

This is NOT cherry-picking, NOT thin-sample noise, NOT look-ahead. It is a verified infra-gap, file-count based, with zero inference.

---

## 7. Verdict

**Category:** Policy / process improvement (does not map to PF/WR tier system).

**Mapped verdict:** **`INFRA_FIX_APPROVED`** — the idea is correct in spirit, but two refinements are mandatory:

1. **Target DB correction.** The user wrote `ejaguiar1_backtests`. The correct DB per existing infra + Hermes rule #1 is `ejaguiar1_backups`. Using `_backtests` would pollute the tournament/backtest results DB.
2. **Stop building a new wrapper.** `tools/safe_db_archive.py` + `tools/db_backup.py::archive_table_slice` already exist and are well-designed (dry-run default, batch insert, parity check, audit log). The fix is **enforcement + adoption**, not a new `tools/safe_destructive.py`.

**Confidence:** HIGH. Evidence is file-system grep + import-graph, not statistical inference.

---

## 8. Recommended next step

`recommend=enforce-existing-archive-helper`

Specifically:

1. **Pre-commit hook** (`.git/hooks/pre-commit` registered via `tools/git_hooks/`): scan staged `.py` files in `tools/` + `alpha_engine/` for `cur.execute(...DELETE|UPDATE|TRUNCATE|DROP...)` against `ejaguiar1_stocks` and warn if the file does not also import `archive_table_slice` OR pass a `--no-archive` opt-out flag with justification comment.
2. **Retrofit the top-5 highest-risk scripts first** (sorted by recent mutation incident attribution):
   - `tools/cleanup_ghost_rows.py` (mass DELETE)
   - `alpha_engine/scripts/prune_correlated_picks.py` (mass DELETE)
   - `tools/db_p0_integrity_remediation.py`
   - `tools/resolve_stale_open_picks.py`
   - `tools/audit_won_picks_auto.py`
3. **Create `reports/db_archives_log.md`** with a header so first --apply run does not silently no-op the append.
4. **Document the policy in `CLAUDE.md`** under "Critical File Rules" as: *"Any tool that mutates `ejaguiar1_stocks` MUST call `archive_table_slice(..., apply=True)` (or its CLI `tools/safe_db_archive.py`) before the mutation. The pre-commit hook enforces this."*

No live SQL was executed for this investigation (policy idea, not edge query). No production rows changed.

---

## 9. References

- `tools/db_backup.py` — `archive_table_slice()` definition
- `tools/safe_db_archive.py` — CLI wrapper, Hermes rules #1 + #3
- `tools/orphan_resolver_dryrun.py` — only existing caller (model the retrofit on this)
- CLAUDE.md memory: `project-money-ready-2026-05-31` (plumbing bottleneck)
- CLAUDE.md memory: `feedback-incident-page-stale-vs-live-db` (mutation-traceability incidents)
