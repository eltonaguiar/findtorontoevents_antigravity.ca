# Resolver Dispatch + DB Helper Scripts — Findings & Remaining Steps

**Date**: 2026-05-19 (session transcript review "all-clear" + user request to "do the remaining action items yourself" + "find the script")

**Context from transcript**:
- All autonomous work complete and committed (audit dashboard repaired, resolver code + 2 GHA workflows, sidecar harness tests REJECTED, etc.).
- 6 genuine open items (404 confirmations) = DONE.
- **Only remaining operator action**: dispatch the two resolver workflows from GitHub Actions tab (dry-run first).
- User already triggered dry-run: `gh workflow run resolver-step5-6-backfill.yml ...` → run ID 26126209814 (was `in_progress`).
- User recalled "python script for mapper/proxy or something" + "wrapper script to let us backup our database tables and write between 2 tables easily" to work around the `ejaguiar1_stocks` IP ACL (desktop IP `142.198.176.179` denied; only GHA runners allowed).

## 1. The Script(s) You Were Looking For

I searched the **main tree** (excluding `.claude/`, `.worktrees/`, `.git/`, venvs) for DB backup / table-copy / proxy / mapper / cross-DB write helpers.

### Primary match: `tools/safe_db_archive.py`
- **Purpose**: Exactly "backup our database tables and write between 2 tables easily" (Hermes rule #1).
- Copies a WHERE slice from source table (default `ejaguiar1_stocks`) → archive table in `ejaguiar1_backups.<table>_<purpose>_<utc_ts>`.
- Batch INSERT (1000-row), count verification, full dry-run by default, `--apply` to execute.
- Uses separate creds for source vs backup DB (exactly the two users you tested).
- Logs to `reports/db_archives_log.md`.
- Safe rollback via RENAME.
- **Why it doesn't help the ACL problem**: It still needs a live `ejaguiar1_stocks` connection for the SELECT side. From this desktop/WSL (same public IP), that connect is denied (see your earlier bash test + my re-test below). The script is designed to be run from an allowlisted host (GHA or your future VPS).

```bash
# Example (dry-run first)
python tools/safe_db_archive.py \
  --source-table at_raw_picks \
  --where "symbol LIKE '%=F' OR (asset_class IS NULL AND symbol NOT LIKE '%=%')" \
  --purpose resolver_defect1 \
  --apply   # only after you have verified the WHERE on an allowlisted host
```

### Secondary family: `database/db_helper_scripts/`
- `SCRIPTS_GUIDE.md` (full inventory + recommended Hermes cron queries for `bt_backtest_trades`, `at_consensus_picks`, etc.)
- `run_bigtable.py`, `run_all.py`, `run_info.py`, `run_indexed.py`, `run_queries.py`, `sql_dump_analyzer.py`
- `micro_1.py`..`micro_4.py` (one-off Kimi 2026-05-08 probes — historical)
- `run_bigtable.py` is the high-reusability chunked 30M-row scanner (reconnect-per-chunk pattern).
- All currently target the backtests DB or offline SQL dumps; none implement a remote SQL proxy or cross-DB write mapper that bypasses the per-user IP ACL.

### Other DB helpers examined (no proxy/mapper found)
- `tools/db_env.py` — only credential resolution (no transport).
- `tools/db_freshness_check.py`, `db_health_check.py`, `db_schema_snapshot.py`, `cross_db_consistency.py`
- `.ruflo/db_sync_agent.py` + root `db_sync.py` + `audit_dashboard/db_sync.py` — JSON pick store ↔ MySQL bidirectional sync (not table-to-table archive).
- `genome/mutation_lab/db_wrapper.py`, `check_db_v*.py`, `tmp/*db_audit*.py` — various audit one-offs.
- No `exec_sql.php`, `sql_api`, `mysql_proxy`, PHP endpoints, or HTTP SQL mapper anywhere in the committed main tree. (Old worktree copies and site-packages only.)

**Conclusion on "easy way around"**: There isn't one in the current codebase that would let a desktop IP with `ejaguiar1_stocks` denied perform the writes. The **resolver GHA workflows you authored** are the designed, auditable, gated, dry-run-safe, rollback-documented solution.

## 2. Why I Cannot Perform the Dispatch (or the DB Writes) Myself

- **This execution environment** = WSL on the same Windows host → identical outbound IP `142.198.176.179`.
  - Confirmed: `ejaguiar1_backups` connect fails here with "Access denied ... (using password: NO)" (no `DB_PASS_BACKUPS` in the container env).
  - `ejaguiar1_stocks` would also fail (same IP ACL you already proved).
- No `gh` CLI binary present in the agent container.
- The connected GitHub MCP ("grok_com_github", authed as `eltonaguiar`) exposes 45 tools, but **none for `workflow_dispatch`, listing/running Actions workflows, or triggering `repository_dispatch`**. Available: PR reviews, issues, branches, releases, Copilot jobs, secret scanning, collaborators, etc. — no Actions runner API surface.
- Even if I wrote a raw `curl` to the GitHub REST API (`POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches`), I have no personal access token with `workflow:write` scope in this context (MCP uses its own limited token).
- Therefore: **I cannot trigger the two resolver workflows, and I cannot execute the required `at_raw_picks` backfill or `active_picks_sync --apply` writes.**

The transcript was correct: "Only remaining action is yours: dispatch the 2 resolver workflows from the GitHub Actions tab (dry-run first)."

## 3. Exact Steps You Must Run Yourself (on your desktop with `gh` + repo auth)

You already started the dry-run for steps 5-6. Finish the sequence:

```bash
# 1. Monitor the dry-run you launched (run ID from your transcript)
gh run view 26126209814 --json status,conclusion,updatedAt
gh run view 26126209814 --log | tail -50     # or open in browser for full log

# When it reports "completed" + "success" (or "skipped" writes because dry_run=true):

# 2. Real Step 5-6 backfill (the actual symbol normalization + backup table creation)
gh workflow run resolver-step5-6-backfill.yml --ref main \
  -f confirm=APPLY-BACKFILL \
  -f dry_run=false

# 3. Step 7 — active_picks_sync writer flip (Defect 3 Stage B)
gh workflow run resolver-step7-apply.yml --ref main \
  -f confirm=APPLY-SYNC \
  -f max_rows=2000     # or whatever safe cap you want

# 4. Watch both
gh run list --workflow=resolver-step5-6-backfill.yml --limit 3
gh run list --workflow=resolver-step7-apply.yml --limit 3
```

**Via GitHub UI (recommended for the typed-confirm gate)**:
1. Go to your repo → **Actions** tab.
2. Left sidebar: "Resolver Step 5-6 — at_raw_picks Backfill".
3. **Run workflow** → choose `main` → set:
   - `confirm`: `APPLY-BACKFILL` (exact)
   - `dry_run`: **uncheck** (false) for the real run.
4. Repeat for "Resolver Step 7 — active_picks_sync APPLY" with `confirm=APPLY-SYNC`.

**After both succeed**:
- Steps 8-9 (re-test the 3 sidecars ET-1/CO-1/E-1 in harness, wire if they now pass, update docs/dashboard) become runnable locally or via follow-up PR.
- Re-run your local `python -m pytest ...` and the audit dashboard freshness check.
- The 2 backup tables created by the workflows (`at_raw_picks_bak_<run_id>`) give you instant rollback.

## 4. Suggestions / Follow-ups (for you or next autonomous session)

1. **After the backfill lands**, add a one-line verification job to `resolver-step5-6-backfill.yml` (or a new composite) that posts a Discord/audit_trail event with the exact row counts changed per defect (FUTURES `=F`, FOREX `=X`, quarantined 6 rows).

2. Consider a tiny GitHub Action that the MCP **can** trigger (repository_dispatch or a labeled issue) if you ever want "agent can start a resolver run" without you typing the confirm phrase. (The typed-confirm is the correct safety here — keep it.)

3. Promote `tools/safe_db_archive.py` + `database/db_helper_scripts/run_bigtable.py` into the official "ops" set (add CLI flags for `--db stocks|backtests`, structured logging, and wire the Discord alert helper). They are the reusable pieces you wanted.

4. Document the ACL reality once in `docs/DB_ACCESS_MODEL.md` (per-user IP allowlist on 50webs; GHA runners are the only always-allowlisted writers from CI; backups user = read-only on its own snapshot tables).

5. The dry-run you already kicked off (26126209814) is the perfect audit artifact — its log will show the exact preflight counts that the APPLY run will reproduce.

---

**Bottom line**: The "script" exists (`tools/safe_db_archive.py` is the direct table-to-table backup writer), the helper suite exists, but the **network ACL + missing gh/MCP dispatch surface** means the dispatch gate stays with you for this one final manual step. Everything else the session set out to do is already done, committed, and peer-broadcast.

Run the two `gh workflow run` (or UI) commands above, watch the green checks, and the resolver pipeline is fully live. Then we're at "steps 8-9 only."

(End of findings — no open autonomous action items remain on the agent side.)