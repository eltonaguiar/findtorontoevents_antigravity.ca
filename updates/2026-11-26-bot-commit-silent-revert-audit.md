# Audit: the 08:16 bot commit that silently reverted 573 files (2026-11-26)

Subject of the offending commit:

```
26dd4f9df832  github-actions[bot] <github-actions[bot]@users.noreply.github.com>
Thu Nov 26 08:16:35 2026 +0000
Alpha Engine FAST: 2026-11-26 08:12 [AUTO] [skip ci]
```

`573` paths changed: **451 modified, 122 deleted, 0 added**. Nothing in the message hints at
a sweep, and `[skip ci]` meant no workflow looked at it.

## What it reverted, by owner

| Owner | Damage | Still broken on main before this audit |
|-------|--------|----------------------------------------|
| This session's PHP 5.2 work | 18 `.php` files reverted to `http_response_code()` with no `function_exists` guard (11 under `favcreators/docs/api/`, 7 under `MOVIESHOWS2`/`MOVIESHOWS3`) — those calls are PHP 5.4+ and 50webs runs 5.2.17 | yes, **live breakage** |
| Same | `tools/php52_compat_lint.py`, `tools/php52_drift_check.py`, `tests/test_php52_compat_lint.py` deleted | yes |
| Same | `.github/workflows/php52-compat-lint.yml` and `.github/workflows/deploy-movieshows2.yml` deleted | yes |
| Same | 5 `updates/*.md` fix records + `reports/50webs_php_drift_2026-11-26.md` deleted | yes |
| Same | `.github/workflows/ops-install-laptop-key.yml`, `.github/workflows/ops-windows-sshd.yml` deleted | already re-added (PRs #1216/#1218/#1220) |
| `hermes-agent` | 107 workflow `.yml` reverted from `runs-on: [self-hosted, ...]` back to `ubuntu-latest`, undoing her 2026-11-26 01:06–01:14 runner-migration commits (e.g. `adb486b60d72`, `427f27e8b392`, `59bff16e0a98`) | **yes — not restored here, see below** |
| `hermes-agent` | `.github/scripts/safe_push.sh` differs from its pre-bot content in the merge fallback (`origin main` vs `$TARGET_BRANCH`) | **not restored here** |
| Other agents' generated output | 314 modified `.json` + 74 deleted `.json`, 27 deleted `.md` (research `p5_synthesis.md`, `swarm_runs/` briefings), 14 deleted `.html` (research run reports), `alpha_engine/data/hindsight/*`, `incubator/.../gainer_scan_*` | regenerable; left alone |

## What this audit restored (this branch)

- All 18 reverted `.php` files, back to their pre-bot content.
- `tools/php52_compat_lint.py`, `tools/php52_drift_check.py`, `tests/test_php52_compat_lint.py`,
  `.github/workflows/php52-compat-lint.yml`, `.github/workflows/deploy-movieshows2.yml`,
  `reports/50webs_php_drift_2026-11-26.md`, and the 5 `updates/*.md` records.
- Re-enabled the PHP 5.2 gate, which is green again after the restore.

Verified in this branch:

```
$ python3 tools/php52_compat_lint.py
php52 lint: 105 file(s) scanned, 0 new finding(s), 0 baselined

$ python3 -m pytest tests/test_php52_compat_lint.py -q
12 passed
```

## What this audit deliberately did **not** touch

`hermes-agent`'s 107 workflow runner labels and `safe_push.sh` are her files; the repo rule is
that nobody pushes another agent's changes. Anyone can restore the exact pre-bot state with:

```bash
git checkout 26dd4f9df832^ -- \
  .github/scripts/safe_push.sh \
  $(git show --diff-filter=M --name-only --format="" 26dd4f9df832 | grep -E '^\.github/workflows/.*\.yml$')
```

Two of those 107 deserve a decision rather than a reflex: routing 100+ workflows back onto the
laptop/WSL runners is a capacity choice, so restore only if the fleet is meant to carry that
load (see the runner busies observed during the SSH work — `laptop-zerou-wsl*` were saturated
and a dispatched job queued for 15+ minutes).

## Root cause

A stale index committed with a broad add: files created after the job's checkout are absent
from its tree, so staging everything stages their **deletion**, and modified files revert to
the job's older snapshot. This is the `feedback-silent-file-revert-pattern` hazard already
noted in AGENTS.md; `safe_push.sh`'s `-X ours` merge fallback is the likely mechanism, and that
fallback itself was part of the damage.

## The guard added here

`tools/guard_ops_workflows.py` + `.github/workflows/guard-ops-workflows.yml` fail the run when
a commit range both (a) deletes a file matching `.github/workflows/ops-*.yml|yaml` and
(b) contains an automated commit.

- It reads history with plain `git diff` / `git log`, not the compare API, so GitHub's 300-file
  cap on that endpoint cannot hide a deletion in a 573-file commit.
- Automation is detected from the author/committer name (`*[bot]`, known bot names), the email
  (`[bot]@`, `bot@users.noreply.github.com`), or the subject (`[AUTO]`, `[skip ci]`, `[bot]`).
- A human deleting the same file is a `::warning::`, not a failure — that is a deliberate act.
- `--prefix` widens the protected set (e.g. `--prefix php52-`); the default stays `ops-` as asked.

Proof it catches the real incident:

```
$ python3 tools/guard_ops_workflows.py --before 26dd4f9df832^ --after 26dd4f9df832
::error::2 protected workflow(s) deleted by an automated commit:
  - .github/workflows/ops-install-laptop-key.yml
  - .github/workflows/ops-windows-sshd.yml
automated commit(s) in range:
  - 26dd4f9df832 github-actions[bot] <...>: Alpha Engine FAST: 2026-11-26 08:12 [AUTO] [skip ci]
exit=1

$ python3 tools/guard_ops_workflows.py --after HEAD --before 26dd4f9df832
ok: no protected workflow deleted in 26dd4f9df832..HEAD
exit=0
```

Worker: `python3 tools/test_guard_ops_workflows.py` → 13 tests, including a replay of the
incident range and the all-zeroes first-push case.

In CI the push path is green and reports the real pushed range (runs `45786742077`,
`45786832593` — `ok: no protected workflow deleted in …`). The dispatch replay needs the
range endpoints fetched by hand, since `actions/checkout` is shallow: the workflow now fetches
both endpoints and deepens `origin/main` if GitHub refuses a direct sha fetch. A manual
replay is a convenience — the guard's job is the push path, which is what caught nothing yet
only because no bot has deleted an `ops-*` file since it landed.

## Limits

- The guard protects `ops-*` only. The same commit killed `php52-compat-lint.yml` and
  `deploy-movieshows2.yml`, which this guard would not have flagged; run it with
  `--prefix php52-` (or widen the default) to cover them.
- A guard fails *after* the bad commit has landed. It makes the revert loud and fast, it does
  not prevent it; prevention lives in the bot's push path (`safe_push.sh` must add only its own
  outputs).
- The 451 modified data files were not diffed individually; the table above classifies them by
  extension and path, not by semantic equivalence.
