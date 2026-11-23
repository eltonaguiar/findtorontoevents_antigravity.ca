# 2026-11-23 — `.github/workflows/ci.yml`: install + lint + build on every push to main

## What was missing

The repo had `ci-tests.yml` (a 747-test pytest suite, path-filtered to Python) and
`test-fast.yml`, but no general gate that runs on **every** push to main and no
workflow whose job was lint or build. There was also no lint or build config to
piggyback on:

| looked for | found |
|---|---|
| `.eslintrc*`, `eslint.config.*` | none |
| `ruff.toml`, `pyproject.toml`, `setup.cfg`, `.flake8` | none |
| root `package.json` `lint` / `build` scripts | none (only test/backtest scripts) |
| bundler | none — the site is hand-coded static HTML plus prebuilt assets |

So "lint + build" could not be `npm run lint && npm run build`; those scripts do not
exist, and inventing them plus a linter config across 161 JS / 5,820 Python files
would have been a different, much larger job. Instead both stages were defined from
what measurably exists, and **every check was run against `origin/main` in a clean
worktree before the workflow was committed**, so it landed green rather than red.

## What the workflow does

`.github/workflows/ci.yml`, two jobs on `ubuntu-latest`, `contents: read`,
`timeout-minutes: 10`, `concurrency: ci-${{ github.ref }}` with
`cancel-in-progress: false` (a cancelled run on main reports as *cancelled*, not
*failed* — that is how a red main hides; the job is short instead).

**lint**
1. `npm ci --no-audit --no-fund` — lockfile is committed, so this is reproducible.
2. `python3 -m pip install --quiet pyyaml`.
3. **JavaScript parses** — `acorn` over every tracked `*.js` outside `node_modules`.
   `acorn` is *already* a devDependency, so no new tool was added. It parses as
   `sourceType: "module"`, which accepts both CommonJS and ESM.
4. **Python compiles** — `python3 -m compileall -q tools alpha_engine audit_trail`.
5. **Workflow YAML is valid** — all 375 workflow files must parse, be a mapping, and
   have both a trigger key and `jobs`. Handles the YAML 1.1 quirk where a bare `on:`
   parses as boolean `True`.

**build** — "build" for a static site is verifying the deployable tree is internally
consistent:
1. `npm ci`.
2. Required pages exist and parse as HTML with a non-zero tag count:
   `TORONTOEVENTS_ANTIGRAVITY/index.html` (the canonical main site — there is no root
   `index.html` on main), `audit_dashboard/index.html`, `template.html`, `audit2.html`.
3. Every payload in `audit_dashboard/data/*.json` must be **strict JSON** — parsed
   with `parse_constant` set to raise, so `NaN` / `Infinity` fail. This is the exact
   defect class that previously made live panels render "no data" while still
   returning HTTP 200.

### Two pre-existing breakages, pinned instead of skipped

Neither is silently ignored: each is an exact path, so a **new** break fails the gate
and a **fixed** file prints a "stale entry, remove it" note.

| pinned set | entries | why they are not fixed here |
|---|---|---|
| `KNOWN_BROKEN` (JS) | `_builder.js`, `tools/Untitled-1.js` | pre-existing unparseable files, not part of the served site; fixing them is a separate change |
| `NON_STRICT_BASELINE` (JSON) | `audit_dashboard/data/hyro_ml_pick_rankings.json` | ships `NaN` on main today; making it fail immediately would have landed a red CI. It is a real tracked defect, reported on every run until fixed |

`node --check` was rejected as the JS linter: it failed 5 of 157 files, including two
`tests/*.spec.js` that use ESM/TS syntax. `acorn` with `sourceType: "module"` parses
those correctly, so the gate covers them instead of excluding a whole directory.

## Verification

Local, against a clean `origin/main` worktree, by extracting each `run:` block from
the committed YAML and executing it verbatim:

```
lint  Install dependencies        rc=0   (192 packages)
lint  Lint — JavaScript parses    rc=0   157 files, 0 unexpected failure(s)
lint  Lint — Python compiles      rc=0   0 errors in tools/, alpha_engine/, audit_trail/
lint  Lint — workflow YAML        rc=0   375 parsed, 0 invalid
build Build — static tree         rc=0   4 pages parsed (894 / 4939 / 1431 / 117 tags)
                                        350 payloads checked, baseline 1
```

Remote, on main:

- pushed as commit `f40eb793be29` (single file: `.github/workflows/ci.yml`), on a
  clean branch from `origin/main` — my working branch carries 159 unrelated unpushed
  commits and was **not** pushed;
- run **[45110192514](https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/45110192514)**:
  `completed / success`, both jobs `success` on every step.

Two bugs were caught by this local proof before the push, which would otherwise have
been a red first run:

1. `python` does not exist here (only `python3`) — the `compileall` and YAML steps
   exited **127**. Fixed by calling `python3` explicitly instead of relying on
   `setup-python` to provide a `python` shim.
2. The first `sed` fix missed the `run: python -m compileall` one-line form, so the
   proof still failed 127 and the push was auto-aborted by the `[ rc -ne 0 ]` guard —
   which is the proof harness doing its job.

Also: the first `git push` was rejected as non-fast-forward because main moved under
the storm commits between the worktree creation and the push. The single-file commit
was rebased onto the new tip and pushed; the retry loop exists because main moves
every few minutes.

## Notes / limitations

- The trigger is **unfiltered** `push: branches: [main]`, as requested. This repo
  receives data commits every few minutes, so this runs often; the job is ~30-60s and
  does not cancel in progress, so runs queue rather than report as cancelled.
- Committing to main necessarily triggers the other unfiltered push-to-main
  workflows already in the repo (deploy/regen jobs). That is a consequence of the
  objective, not of this file.
- `lint` is a *syntax and validity* gate, not a style linter: there is no style config
  in the repo to enforce, and adding one would flag thousands of existing files.
