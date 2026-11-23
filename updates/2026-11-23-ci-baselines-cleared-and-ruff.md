# 2026-11-23 — CI allowlists emptied (three real repairs) + a changed-files ruff gate

Follow-up to `updates/2026-11-23-ci-workflow-lint-build.md`, which shipped `.github/workflows/ci.yml`
with two pinned allowlists because fixing the underlying files was out of scope. This removes both
allowlists by fixing the causes, so the gate now has **no exceptions**.

## 1. `"cv_accuracy": NaN` — fixed in the generator, not just the payload

`audit_dashboard/data/hyro_ml_pick_rankings.json` contained a bare `NaN`, which is invalid JSON:
browsers reject the entire document, so the panel renders empty while the HTTP status stays 200.
Fixing only the committed file would have been undone by the next scheduled write.

`tools/hyro_ml_pick_optimizer.py`:
- added `_finite_or_none(value, digits)` — rounds a finite float, returns `None` for `NaN`/`±inf`
  and for non-numeric input;
- both `cv_accuracy` emission points now go through it. The previous guard was
  `if model_info.get("cv_accuracy")`, and **`bool(float("nan"))` is `True`**, so `NaN` passed
  straight through. That is the actual root cause, not a formatting slip;
- the rankings write now uses `json.dump(..., allow_nan=False)`, so if a `NaN` ever reaches it the
  job fails loudly instead of shipping a payload that silently blanks a panel.

## 2. `_builder.js` — was not parseable JavaScript

Its string array embedded unescaped double quotes (`"…require("playwright")…"`), so the file could
not be parsed at all and had never run. Rewritten with correct quoting, keeping the behaviour (emit a
Playwright smoke test for `torontoevent.net/MOVIESHOWS3/`). Three fixes to the code it *emits*, which
could never have worked as written, are called out in a header comment:
`page.$` → `page.$$` (`.length` on a single ElementHandle is `undefined`), `page.eval` → `page.$eval`
(`page.eval` is not a Playwright API), and the `"$"` concatenation trick written plainly.

## 3. `tools/Untitled-1.js` — is not JavaScript

Twelve lines of captured console output (`symbol: "…"`, `score: 41 | elite: 24`, a fragment of a
`regime_validation` object). Renamed to `tools/untitled-1-capture.txt`; nothing imports it.

## 4. `ruff.toml` + a changed-files-only style step

There is no style config in the repo, and repo-wide style rules would flag thousands of existing
files, so the step lints **only the Python files changed in the push**:

- `ruff.toml` selects `E9` (syntax), `F63` (broken `%`/format strings), `F7` (invalid `except` /
  `__all__` constructs) — rules that are essentially never a matter of taste;
- the workflow resolves `github.event.before`, falls back to `HEAD~1` for `workflow_dispatch` or a
  force-push, prints the file list, and exits 0 when a push changes no Python;
- **the sha is passed through `env: PUSH_BEFORE`, not interpolated with `${{ }}` inside `run:`** — a
  push payload is attacker-influenced text and interpolating it into a shell is code execution. My
  first version got this wrong and my own step-harness caught it;
- `fetch-depth: 0` added to the lint checkout, because `github.event.before` is not resolvable in a
  shallow clone.

## Verification

| check | result |
|---|---|
| acorn over every tracked `*.js`, allowlist empty | 156 files, 0 failures |
| strict-JSON over `audit_dashboard/data/*.json`, baseline empty | 350 payloads, 0 non-strict |
| `python3 -m compileall -q tools alpha_engine audit_trail` | OK |
| `ruff check --select E9,F63,F7` on the changed file | clean (rc=0) |
| every `run:` step of the patched `ci.yml`, executed verbatim with its `env:` | all rc=0 |
| `_builder.js` | `node --check` passes; executing it emits a 22-line test using `page.$$` |

## Mistakes made here, for the record

Two process errors, both mine, both found by checking rather than assuming:

1. A `git commit --amend` ran while HEAD was still on `origin/main`'s bot commit, so it amended
   **someone else's commit** (locally only; nothing was pushed and the worktree was discarded).
   Cause: the previous `git push` had aborted, so the expected commit was never created, and I did
   not re-check `HEAD` before amending.
2. `git add … tools/Untitled-1.js` after `git mv` aborted the entire add (pathspec no longer exists)
   and the commit contained only the rename. I pushed it without checking the staged set. The
   remaining five files went in the next commit; nothing was force-pushed or rewritten.
3. A COMS note was published with a `run null` header because it was assembled before the run
   existed. Corrected on the same topic with the real run id.

Peer claims re-checked, not taken on trust: copilot's `alpha_engine/two_hurdle_gate.py` and
`tools/paired_bootstrap_vs_benchmark.py` are **absent from `origin/main`** and commits
`cd44a8cab33` / `378fdd23fad` are reachable from no `origin/*` ref, matching Zoo's `NOT LANDED`
verdict. `tools/capacity_model.py` is likewise absent from main, so Zoo's B11 stays `NOT LANDED`.
