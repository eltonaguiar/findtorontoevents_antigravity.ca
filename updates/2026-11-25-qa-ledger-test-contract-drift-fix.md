# `CI Tests` was red for every PR — a stale test fixture, not a product bug

**Date:** 2026-11-25
**Scope:** `tests/test_qa_ledger_rules.py` (test-only; no production behaviour changed)
**Blast radius:** every pull request in the repo. `CI Tests` is one of the nine
checks on every PR, and it ran `5 failed, 7977 passed` on both Python 3.11 and
3.12.

---

## 1. What was broken

`bd6f9e30de9d` — *"fix(gha): one Pages publisher, no double deploy, honest
hub-sync, fresh QA gate"* (2026-11-25 21:52Z) — added a freshness gate to
`tools/qa_ledger.py`. When the picks snapshot has no parsable `generated_at`,
the ledger now raises a **critical** `STALE_SNAPSHOT` flag and exits `1`:

```python
# tools/qa_ledger.py:143-145
{"symbol": "-", "asset_class": "SNAPSHOT", "verdict": "STALE_SNAPSHOT",
 "detail": f"picks snapshot has no parsable generated_at "
           f"(got {d.get('generated_at')!r}); freshness cannot be established"}
```

That is correct behaviour. A snapshot you cannot prove is current must not be
reported clean.

The problem is `tests/test_qa_ledger_rules.py`, last touched by
`9544e03b5543` (#1041, 2026-11-21) — **four days before** the freshness gate.
Its fixture wrote a snapshot with no timestamp:

```python
# tests/test_qa_ledger_rules.py:24 (before)
live.write_text(json.dumps({"picks": picks}), encoding="utf-8")
```

So *every* test case in the file silently picked up the critical
`STALE_SNAPSHOT` flag, `run()` returned `1`, and every `assert rc == 0` failed.
The `out_of_bounds` case saw `2 == 1` critical flags for the same reason: its
one real flag plus the snapshot flag.

### The smoking gun

`bd6f9e30de9d` shipped a **second** test suite for the same tool,
`tools/qa_ledger_selftest.py`, and that one explicitly asserts the opposite of
what the pytest file asserted:

```python
# tools/qa_ledger_selftest.py:126-127
rc, rep, _ = run_case([pick()], "", quote=100.6)
check("unparsable snapshot age IS critical", rc == 1)
check("missing generated_at flagged STALE_SNAPSHOT", "STALE_SNAPSHOT" in verdicts(rep))
```

The selftest passes 100% on `main`. The pytest file fails 5/8 on `main`. The repo
was shipping two mutually contradictory contracts for `qa_ledger.py`, and only
`CI Tests` looked at the stale one.

## 2. What changed

`tests/test_qa_ledger_rules.py` only. No production file was touched.

1. **The fixture stamps a fresh `generated_at`.** `_run()` now defaults
   `generated_at` to *now*, because an un-stamped snapshot is genuinely a
   critical condition. A sentinel (`_NOW`) is used instead of a default
   argument, because `def f(x=_fresh_stamp())` evaluates **once at import
   time** and would silently go stale in a long test session — the exact bug
   class this commit is fixing.

2. **`generated_at=None` still models the un-stamped case** for tests that want
   it.

3. **Three regression tests pin the contract in pytest**, so this file and the
   selftest cannot drift apart again:
   - `test_missing_generated_at_is_critical` — no stamp ⇒ `rc == 1` and a
     `STALE_SNAPSHOT` flag with `asset_class == "SNAPSHOT"`.
   - `test_stale_generated_at_is_critical` — a stamp 600 minutes old ⇒ same
     failure as a missing one.
   - `test_fresh_generated_at_is_not_flagged` — guards against
     over-correcting: a fresh stamp must **not** trip the gate.

4. The module docstring records the drift and the pivot commit, so the next
   person to touch either file sees why the fixture looks the way it does.

### Why the tool was not changed

The tempting "fix" is to downgrade `STALE_SNAPSHOT` to a warning or let the
ledger pass when the timestamp is absent. That would make the test green by
deleting a safety property: the ledger exists to stop stale data being
reported clean. The gate is right; the fixture was wrong.

## 3. How it was verified

The failure and the fix were both reproduced in a clean virtualenv seeded only
with the workflow's own `pip install` line — not the host environment, which
already had packages that masked the problem.

| # | Check | Result |
|---|-------|--------|
| 1 | Reproduce on a **pristine** `origin/main` worktree (`git worktree add --detach`) | `5 failed, 3 passed` — identical to CI, so not caused by any open PR |
| 2 | Dump the QA report for a single clean row | `flag_counts: {"total": 1, "critical": 1}`, one `STALE_SNAPSHOT` on `asset_class: "SNAPSHOT"` |
| 3 | `python tools/qa_ledger_selftest.py` on `main` | all checks pass — the contradictory suite |
| 4 | `git log -S'freshness cannot be established' -- tools/qa_ledger.py` | pivot commit `bd6f9e30de9d` |
| 5 | `git log -1 -- tests/test_qa_ledger_rules.py` | `9544e03b5543` (2026-11-21), four days **before** the gate |
| 6 | `pytest tests/test_qa_ledger_rules.py` after the fix | **11 passed** (was 5 failed / 3 passed) |
| 7 | `gh run view 45718551092 --log-failed` | exactly 5 `FAILED`, all in `test_qa_ledger_rules.py`, nothing else |
| 8 | CI summary line, both interpreters | `test (3.11)` → `5 failed, 7977 passed, 69 skipped, 13 deselected, 2 xfailed in 227.08s`; `test (3.12)` → `5 failed, 7977 passed, 69 skipped, 13 deselected, 2 xfailed in 437.26s` |

Check 8 is the important one: the two Python versions produce the **same** 5
failures and the same 7977 passes, so there is no version-specific behaviour
hiding here, and no second regression behind the first.

Because the numbers are identical across interpreters and all five failures are
in the one file this commit edits, the expected post-merge gating result is
`0 failed, 7985 passed` (7977 previously passing + 5 repaired + 3 new).

### A note on the local full-suite run

Running the full gating command locally in the minimal venv aborts at
collection with `SystemExit: 1` from `alpha_engine/forex_smart_picks.py:41` — a
missing optional dependency, not a test failure. The minimal venv was built to
reproduce the *validation-gates* job, which needs a small package set; the
`CI Tests` job installs the full requirements. Rather than reconstruct that
whole environment locally, the authoritative counts were taken from the real CI
run (check 8), which is stronger evidence than a local approximation.

## 4. Follow-ups

| Item | Owner | Note |
|------|-------|------|
| Consider deleting `tools/qa_ledger_selftest.py` in favour of the pytest file | owner | Two suites for one 300-line tool is what allowed the divergence. The pytest file now covers the same freshness contract, so the selftest is redundant — but removing it is a separate decision. |
| Audit other `tools/*_selftest.py` for the same dual-contract pattern | owner | If any other module has both a selftest and a pytest file, the same silent divergence is possible. |
| Add a CI step that runs `tools/*_selftest.py` | owner | The selftest is currently not run by any workflow found in `.github/workflows/`, which is *why* the contradiction went unnoticed. |

## 5. Notes for the next agent

1. **`assert 1 == 0` on a ledger/tool test is usually a fixture problem, not a
   tool problem.** Check whether the fixture satisfies every precondition the
   tool validates before blaming the tool.
2. **When a commit adds a new test suite for an existing module, the old suite
   is now suspect.** `bd6f9e30de9d` added a selftest and left the pytest file
   contradicting it; nothing ran both.
3. **Never fix a red test by weakening the assertion's subject.** The gate was
   right. Downgrading a critical flag to make a fixture pass would have removed
   the only protection against reporting stale pick data as clean.
4. **Prove "is this failure mine?" with a detached worktree at `origin/main`
   before touching your branch.** `git worktree add -q --detach /tmp/maincheck
   origin/main` then run the suspect tests there. One command, no API calls,
   definitive answer.
5. **Default arguments evaluate at import time.** `def _run(..., generated_at=
   _fresh_stamp())` would have re-introduced staleness for any long-running
   session. Use a sentinel and compute inside the function.
6. **`gh pr checks` can show superseded runs.** Always confirm the head's true
   status with
   `gh api repos/{o}/{r}/commits/{sha}/check-runs --jq '.check_runs[] | "\(.conclusion // .status)\t\(.name)"'`,
   and resolve a failing check-run to its run via the check-run's own
   `html_url`.
