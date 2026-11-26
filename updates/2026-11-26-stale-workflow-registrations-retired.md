# Stale workflow registrations retired — `db-secret-scan.yml`, `mermaid-test-deploy.yml`

**Date:** 2026-11-26
**Scope:** GitHub Actions registration cleanup for
`eltonaguiar/findtorontoevents_antigravity.ca`

## Symptom

The repo's Actions sidebar listed two workflows in `state=active` whose files
return HTTP 404 on `main`:

| workflow id | name | path |
|---|---|---|
| 289640843 | DB Secret Scan | `.github/workflows/db-secret-scan.yml` |
| 416710543 | Mermaid Test Deploy | `.github/workflows/mermaid-test-deploy.yml` |

A 404 on a file that is also listed as an active workflow is the classic
"deleted by accident" signature, so this needed a history check before deciding
between restore and retire.

## Finding: neither file was ever on `main` — nothing was deleted

Evidence:

```
gh api "repos/.../commits?path=.github/workflows/db-secret-scan.yml"
  -> []   (0 commits on the default branch touch this path)

gh api "repos/.../commits?path=.github/workflows/mermaid-test-deploy.yml"
  -> []   (0 commits on the default branch touch this path)

gh api "repos/.../contents/.github/workflows/db-secret-scan.yml"          -> 404
gh api "repos/.../contents/.github/workflows/mermaid-test-deploy.yml"     -> 404
```

GitHub registers a workflow for **any** branch, not just the default branch, which
is why both appear in the sidebar while their files are absent from `main`.

### `db-secret-scan.yml` — abandoned PR branch, superseded

- Only ever existed on `fix/md-action-items-2026-06-05`, which no longer exists on
  the remote (`git ls-remote --heads origin fix/md-action-items-2026-06-05` → empty).
- Its only two runs were both **failures**, both `pull_request`, 2026-06-05
  06:05:26Z and 06:57:28Z.
- Its content survives only as a snippet in
  `HANDOFF_CLAUDE_CLI_2026-06-03.md` §6.3 (a `grep -r "stocks1234560"` gate).
- **Already replaced on `main`** by `db-password-leak-guard.yml`, which blocks *new*
  hardcoded DB password literals in `.py` / `.sh` / `.yml` / `.yaml` on PRs
  (`INCIDENT_OVERALL #89` forward fence).

### `mermaid-test-deploy.yml` — scratch branch experiment

- Entire file (338 bytes) lives only on branch `wiring`:

  ```yaml
  name: Mermaid Test Deploy
  on:
    push:
      branches: [ wiring ]
  ```

- All 5 runs failed, all `push` on `wiring`, 2026-11-13 and 2026-11-14.
- It publishes `./docs/mermaid_tests` with `peaceiris/actions-gh-pages@v3`. That
  directory does **not** exist on `main` (404); on `wiring` it contains a single
  file, `broken.html`.

## Decision: retire both (not restore)

Restoring `db-secret-scan.yml` would create a second, weaker duplicate of
`db-password-leak-guard.yml` (it scans for one literal on push *and* PR, and it
failed both times it ran). Restoring `mermaid-test-deploy.yml` would deploy a
directory that does not exist on `main`, from a v3 publish action that has since
been superseded.

## Change applied

```
gh api -X PUT "repos/.../actions/workflows/289640843/disable"   -> HTTP 204
gh api -X PUT "repos/.../actions/workflows/416710543/disable"   -> HTTP 204
```

Verification (re-query of the workflow list):

```
289640843   disabled_manually   .github/workflows/db-secret-scan.yml
416710543   disabled_manually   .github/workflows/mermaid-test-deploy.yml
```

Both now sit in the same `disabled_manually` bucket as the 8 sports workflows, so
they no longer present as broken/active in the sidebar.

**Reversal** (if either is ever wanted back):

```
gh api -X PUT "repos/.../actions/workflows/289640843/enable"
gh api -X PUT "repos/.../actions/workflows/416710543/enable"
```

Note that `enable` alone will not make them runnable — the `.yml` file still has to
be committed to a branch that a trigger matches (and, for
`mermaid-test-deploy.yml`, `docs/mermaid_tests/` has to exist).

## Related

- `reports/gha_pr_review_2026-11-26.md` listed both as "registered active, absent
  from the tree" without resolving them; this document closes that item.
- No workflow file on `main` references either path, so nothing else needs a change.
