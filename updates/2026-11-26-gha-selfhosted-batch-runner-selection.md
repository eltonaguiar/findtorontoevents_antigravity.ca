# `gha_selfhosted_batch.py`: hardcoded ARM64 label made the tool unusable

**Date:** 2026-11-26
**Status:** fixed
**File:** `tools/gha_selfhosted_batch.py`
**Base:** `814116dd4cb8` (`origin/main`)
**Goal:** Goal #1 — cost/CI hygiene for the audit pipeline.

## What was broken

Line 55 pinned every dispatch to one label set:

```python
SELF_HOSTED_LABELS = "[self-hosted, Linux, ARM64]"
```

The runner fleet at the time of writing:

| Runner | OS / arch | State |
|---|---|---|
| `gx10-arm64-native`, `gx10-arm64-linux`, `gx10-arm64-linux-2` | Linux ARM64 | online, **busy** |
| `laptop-zerou-wsl` | Linux X64 | online, **busy** |
| `desktop-081g9oh-wsl-1`, `desktop-081g9oh-wsl-2`, `gx10-wsl-runner-1` | Linux X64 | **offline** |
| `desktop-081g9oh-2`, `desktop-081g9oh-svc`, `laptop-zerou-win`, `laptop-zerou-win-2` | Windows X64 | online, **idle** |

Every ARM64 runner was busy, so a dispatch through this tool queued on a runner
that could not accept it. That does not fail fast — GitHub holds the job as
`queued` until the job timeout, which reads like a hang and burns the whole
`--timeout-min` budget before producing a verdict. The tool therefore reported a
healthy "dispatched" and then produced nothing.

## What changed

Three defects, one theme: the tool assumed the fleet was static.

1. **Label pinned at import time → selected per job.** `pick_runner()` queries
   `runners()` and only considers `status == "online" and not busy`. Labels are
   taken from the chosen runner itself, so the rewritten `runs-on:` always
   matches a box that can actually take the job.

2. **No OS check → OS-aware selection.** The first version of this fix fell
   through preference order to *any* idle runner, and on the live fleet that
   meant handing a Linux workflow to a **Windows** box. Those workflows are bash
   + `python3` + `mysql`; on the Windows self-hosted runner the shell defaults to
   pwsh and the job dies on the first step with an error that looks like a
   workflow bug. `os_of_workflow()` now reads the workflow's own `runs-on:` line
   (`ubuntu`/`linux` → `linux`, `windows` → `windows`, `macos` → `macos`) and
   `pick_runner(want_os=...)` filters the idle pool to that OS. A cross-OS
   mismatch now raises with the idle runners listed, instead of silently
   producing a confusing failure.

3. **Single probe → bounded wait.** The pool flaps: `desktop-081g9oh-wsl-1/2`
   went idle → busy → offline within two minutes of observation. `wait_for_runner()`
   retries `pick_runner()` every 15s for up to `--wait-runner SEC` (default 600;
   `0` = fail fast). Polling is cheaper than a failed dispatch.

Also added: `--runner NAME_OR_LABEL` to force a specific box. It is matched
against the idle pool only, so naming a busy runner errors with the idle list
rather than waiting on it.

`SELF_HOSTED_LABELS` is kept (callers may import it) but is no longer used for
dispatch.

## API surface added

```
--runner NAME|LABEL     force a runner; must be online+idle
--wait-runner SEC       wait up to SEC for a suitable idle runner (default 600)
```

```python
pick_runner(prefer=None, want_os=None) -> (runs_on_expr, runner_name)
wait_for_runner(prefer, want_os, wait_sec) -> (runs_on_expr, runner_name)
os_of_workflow(path) -> "linux" | "windows" | "macos" | None
```

## Why this is not a mass re-pin

This tool never touches `main`. It rewrites `runs-on:` on a throw-away
`selfhosted-batch/...` branch, dispatches, then deletes the branch, so no
workflow is left pinned to a self-hosted runner. `vars.ACTIONS_RUNNER_LABEL`
(used by 255 of 388 workflows as a single shared switch) is deliberately **not**
touched — setting it would move the whole repository onto a pool that currently
has zero idle Linux capacity.

## Verification

```
python3 -m py_compile tools/gha_selfhosted_batch.py          # OK

os_of_workflow:
  db-freshness-guardian.yml -> linux
  audit-dashboard.yml       -> linux
  ci-tests.yml              -> linux
  missing.yml               -> None

pick_runner against the live fleet:
  want=linux   -> REFUSED: "this workflow wants linux but no linux runner is
                  idle; idle right now: desktop-081g9oh-2(['Windows']), ..."
  want=windows -> ('[self-hosted, X64, Windows, desktop-081g9oh]', 'desktop-081g9oh-2')
  prefer='laptop-zerou-wsl' (busy) -> REFUSED with the idle list
  fail-fast wait_for_runner(..., 0) -> REFUSED cleanly, no hang
```

The refusal path is the important one: previously this silently queued forever.

## Known limitation / open item

The tool cannot make a Linux job run right now, because there is **no idle
Linux runner** — 3 ARM64 busy, 3 X64 offline, 1 X64 busy. The Windows runners
are the only free capacity, and they cannot run these bash workflows. Bringing
`desktop-081g9oh-wsl-1` / `-2` / `gx10-wsl-runner-1` back online is the actual
unblock; that is a host-side action, not a code change.
