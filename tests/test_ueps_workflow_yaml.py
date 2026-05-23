"""Validation tests for UEPS Phase 14 GitHub Actions workflow YAMLs.

Phase 14 of the long-term-value (UEPS) project introduces 4 new workflow files:

  1. .github/workflows/value_screener_weekly.yml      (Mon 06:00 UTC cron)
  2. .github/workflows/swing_screener_daily.yml       (Mon-Fri 14:00 UTC cron)
  3. .github/workflows/value_resolver_quarterly.yml   (Quarterly 1st @ 07:00 UTC)
  4. .github/workflows/ueps_smoke_tests.yml           (PR-triggered pytest gate)

This test module enforces the patterns codified in PR #436
(``audit-dashboard.yml``):

  - The YAML must parse cleanly (catches typos, indent errors, the
    "<<<<<<<" conflict markers a previous shipping cycle leaked into prod).
  - Each runtime workflow declares a ``concurrency`` block that splits by
    event_name — push/manual cancel-in-progress, cron queues. Without this
    we re-introduce the manual-cancellation toil PR #436 fixed.
  - At least one critical step in each workflow has ``if: always()`` so
    artifact uploads / step summaries fire even when the runner step
    crashes. PR #436 added this to the FTP deploy step after a stale-site
    outage.
  - ``permissions:`` is explicit on every workflow (least-privilege; GitHub
    flips defaults occasionally and we do not want surprise PR-write
    grants).
  - Checkouts use ``fetch-depth: 0`` to avoid the slow
    ``git fetch --unshallow`` cost in commit-back paths.
  - Every cron schedule expression has the canonical 5 whitespace-separated
    fields (catches off-by-one cron typos that silently never fire).

Invocation: ``python -m pytest tests/test_ueps_workflow_yaml.py -v``
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

# Path resolution: this file lives at tests/test_ueps_workflow_yaml.py;
# the repo root is the parent of `tests/`.
REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

# All four workflow files Phase 14 introduces. Tuple of (filename, is_runtime).
# `is_runtime=True` means the workflow runs the screener/resolver runner on a
# schedule and therefore MUST have the audit-dashboard concurrency split.
# `is_runtime=False` (the smoke-test gate) is PR-triggered and uses a simpler
# branch-keyed concurrency group.
UEPS_WORKFLOWS: list[tuple[str, bool]] = [
    ("value_screener_weekly.yml", True),
    ("swing_screener_daily.yml", True),
    ("value_resolver_quarterly.yml", True),
    ("ueps_smoke_tests.yml", False),
]

# YAML quirk: PyYAML parses the `on:` key as Python boolean True (because
# YAML 1.1 treats `on`/`off` as booleans). Workflows quote the key as
# `'on':` to keep YAML 1.1 from doing this — but PyYAML still ends up with
# `True` as the dict key in some configurations. Probe both.
ON_KEYS = ("on", True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow(filename: str) -> dict[str, Any]:
    """Load and yaml.safe_load a workflow file. Raises if it does not exist."""
    path = WORKFLOWS_DIR / filename
    assert path.exists(), f"Workflow file missing: {path}"
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_workflow_text(filename: str) -> str:
    """Read the raw YAML text — used for the comment / opt-in marker checks."""
    path = WORKFLOWS_DIR / filename
    return path.read_text(encoding="utf-8")


def get_on(workflow: dict[str, Any]) -> dict[str, Any]:
    """Fetch the workflow's `on:` block, tolerating PyYAML's True-key quirk."""
    for key in ON_KEYS:
        if key in workflow:
            return workflow[key]
    raise AssertionError(f"Workflow has no `on:` block. Keys: {list(workflow)}")


def collect_steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten all steps across all jobs in a workflow."""
    steps: list[dict[str, Any]] = []
    for _job_id, job in (workflow.get("jobs") or {}).items():
        steps.extend(job.get("steps") or [])
    return steps


def is_valid_cron(expr: str) -> bool:
    """5-field POSIX cron sanity check.

    Accepts: digits, `*`, `,`, `-`, `/`, `?`, and named day-of-week tokens
    (MON-SUN). This is intentionally permissive — the goal is to catch
    obvious typos like a 4-field or 6-field expression, not to reimplement
    the GitHub Actions cron parser.
    """
    if not isinstance(expr, str):
        return False
    parts = expr.split()
    if len(parts) != 5:
        return False
    field_re = re.compile(r"^[\d\*,\-/?A-Za-z]+$")
    return all(field_re.match(p) for p in parts)


# ---------------------------------------------------------------------------
# 1. Per-workflow: each file parses cleanly and exists
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename,_is_runtime", UEPS_WORKFLOWS)
def test_workflow_file_parses(filename: str, _is_runtime: bool) -> None:
    """Each Phase 14 workflow YAML loads via yaml.safe_load without error."""
    workflow = load_workflow(filename)
    assert isinstance(workflow, dict), (
        f"{filename} did not parse to a dict (got {type(workflow).__name__})"
    )
    assert "name" in workflow, f"{filename} missing top-level `name:`"
    assert "jobs" in workflow and workflow["jobs"], (
        f"{filename} missing or empty `jobs:` block"
    )


# ---------------------------------------------------------------------------
# 2. Shared invariants that apply to ALL UEPS workflows
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename,_is_runtime", UEPS_WORKFLOWS)
def test_workflow_has_permissions_block(filename: str, _is_runtime: bool) -> None:
    """Least-privilege: every workflow declares its permissions explicitly.

    GitHub's default permissions can flip from `contents: write` to
    `contents: read` (and back) per-org. Pinning here removes that surprise.
    """
    workflow = load_workflow(filename)
    assert "permissions" in workflow, (
        f"{filename} must declare a top-level `permissions:` block "
        "(least-privilege requirement)"
    )
    assert workflow["permissions"], (
        f"{filename} `permissions:` block is present but empty"
    )


@pytest.mark.parametrize("filename,_is_runtime", UEPS_WORKFLOWS)
def test_workflow_has_concurrency_block(filename: str, _is_runtime: bool) -> None:
    """Every UEPS workflow has a concurrency block.

    PR #436 introduced the split-by-event-name pattern in audit-dashboard.yml
    after 7 days / 15 cancelled cron runs from manual cancellations. The
    smoke-test gate uses a simpler branch-keyed group (PR-only), but it
    still needs a concurrency block so PR pushes auto-cancel stale runs.
    """
    workflow = load_workflow(filename)
    assert "concurrency" in workflow, (
        f"{filename} must declare a `concurrency:` block "
        "(see audit-dashboard.yml line 82-93 for the canonical pattern)"
    )
    concurrency = workflow["concurrency"]
    assert isinstance(concurrency, dict), (
        f"{filename} concurrency must be a mapping with `group:` and "
        f"`cancel-in-progress:` keys, got {type(concurrency).__name__}"
    )
    assert "group" in concurrency, f"{filename} concurrency missing `group:`"
    assert "cancel-in-progress" in concurrency, (
        f"{filename} concurrency missing `cancel-in-progress:`"
    )


@pytest.mark.parametrize("filename,_is_runtime", UEPS_WORKFLOWS)
def test_workflow_checkout_uses_fetch_depth_0(filename: str, _is_runtime: bool) -> None:
    """Checkout step uses fetch-depth: 0 (PR #436 finding).

    Shallow clones force `git fetch --unshallow` (16-18 minutes on this
    repo's 5GB+ history), exhausting the push-retry budget. Full clone is
    a net win.
    """
    workflow = load_workflow(filename)
    checkout_steps = [
        step
        for step in collect_steps(workflow)
        if isinstance(step.get("uses"), str) and step["uses"].startswith("actions/checkout@")
    ]
    assert checkout_steps, f"{filename} has no actions/checkout step"
    for step in checkout_steps:
        params = step.get("with") or {}
        # fetch-depth may be int 0 or string "0" depending on YAML parser
        # state — accept both.
        depth = params.get("fetch-depth")
        assert depth in (0, "0"), (
            f"{filename} checkout step must use `fetch-depth: 0`, got {depth!r} "
            "(see audit-dashboard.yml line 132-140)"
        )


@pytest.mark.parametrize("filename,_is_runtime", UEPS_WORKFLOWS)
def test_workflow_has_if_always_step(filename: str, _is_runtime: bool) -> None:
    """At least one step uses `if: always()`.

    PR #436 added `if: always()` to the FTP deploy step in
    audit-dashboard.yml after the commit-step failure cascade left the
    live site stale. Every UEPS workflow follows the same pattern: the
    runner step may fail, but the artifact upload / step summary should
    fire regardless so we can diagnose what happened.
    """
    workflow = load_workflow(filename)
    steps = collect_steps(workflow)
    # Match `always()` even when wrapped with extra conditions like
    # `always() && steps.x.outputs.y != ''`.
    always_steps = [
        s for s in steps if "always()" in str(s.get("if", ""))
    ]
    assert always_steps, (
        f"{filename} has no step with `if: always()`. At least the "
        "artifact-upload or step-summary step must be unconditional so "
        "we can diagnose runner-step failures."
    )


@pytest.mark.parametrize("filename,_is_runtime", UEPS_WORKFLOWS)
def test_workflow_opt_in_sidecar_marker_present(filename: str, _is_runtime: bool) -> None:
    """First comment line declares opt-in sidecar status.

    CLAUDE.md Wire-Up Rule: new integration modules must be either wired or
    explicitly labeled opt-in. This marker enforces the labelling so
    breadth-only PRs cannot pass review undetected.
    """
    text = load_workflow_text(filename)
    first_lines = text.splitlines()[:3]
    joined = "\n".join(first_lines).lower()
    assert "opt-in sidecar" in joined, (
        f"{filename} first 3 lines must include the literal phrase "
        "'Opt-in sidecar' to comply with CLAUDE.md Wire-Up Rule"
    )


# ---------------------------------------------------------------------------
# 3. Runtime workflows: the 3 schedulers must split concurrency by event_name
# ---------------------------------------------------------------------------


RUNTIME_WORKFLOWS = [(f, r) for f, r in UEPS_WORKFLOWS if r]


@pytest.mark.parametrize("filename,_is_runtime", RUNTIME_WORKFLOWS)
def test_runtime_workflow_split_concurrency_by_event(
    filename: str, _is_runtime: bool
) -> None:
    """Runtime workflows split concurrency by github.event_name.

    The exact PR #436 pattern is:

        group: <name>-${{ github.event_name == 'push' && 'push' || 'cron' }}
        cancel-in-progress: ${{ github.event_name == 'push' }}

    This makes push / workflow_dispatch runs auto-cancel each other while
    cron runs queue normally. We assert the substring rather than the full
    expression so future cosmetic refactors don't break the test.
    """
    workflow = load_workflow(filename)
    concurrency = workflow["concurrency"]
    group_expr = str(concurrency.get("group", ""))
    cancel_expr = str(concurrency.get("cancel-in-progress", ""))
    assert "github.event_name" in group_expr, (
        f"{filename} concurrency group must reference `github.event_name` "
        "to split push/cron behaviour. See audit-dashboard.yml line 92."
    )
    assert "github.event_name" in cancel_expr, (
        f"{filename} cancel-in-progress must reference `github.event_name` "
        "so cron runs queue but push/manual runs auto-cancel."
    )


@pytest.mark.parametrize("filename,_is_runtime", RUNTIME_WORKFLOWS)
def test_runtime_workflow_has_valid_cron(
    filename: str, _is_runtime: bool
) -> None:
    """Runtime workflows have at least one valid 5-field cron expression."""
    workflow = load_workflow(filename)
    on = get_on(workflow)
    assert "schedule" in on, f"{filename} `on:` block missing `schedule:` trigger"
    schedule = on["schedule"]
    assert isinstance(schedule, list) and schedule, (
        f"{filename} schedule must be a non-empty list"
    )
    for entry in schedule:
        assert "cron" in entry, f"{filename} schedule entry missing `cron:` key"
        expr = entry["cron"]
        assert is_valid_cron(expr), (
            f"{filename} cron expression {expr!r} is not 5 fields "
            "(catch typos before they silently never fire)"
        )


@pytest.mark.parametrize("filename,_is_runtime", RUNTIME_WORKFLOWS)
def test_runtime_workflow_has_workflow_dispatch(
    filename: str, _is_runtime: bool
) -> None:
    """Runtime workflows are manually dispatchable (for ad-hoc reruns)."""
    workflow = load_workflow(filename)
    on = get_on(workflow)
    assert "workflow_dispatch" in on, (
        f"{filename} must declare `workflow_dispatch:` so on-call can "
        "trigger ad-hoc reruns when the cron misses"
    )


# ---------------------------------------------------------------------------
# 4. Per-workflow specifics: cron values match the Phase 14 spec
# ---------------------------------------------------------------------------


def _first_cron(filename: str) -> str:
    workflow = load_workflow(filename)
    return get_on(workflow)["schedule"][0]["cron"]


def test_value_screener_weekly_cron_is_monday_6am_utc() -> None:
    """value_screener_weekly: 0 6 * * 1 (Monday 06:00 UTC)."""
    assert _first_cron("value_screener_weekly.yml") == "0 6 * * 1"


def test_swing_screener_daily_cron_is_weekdays_14utc() -> None:
    """swing_screener_daily: 0 14 * * 1-5 (Mon-Fri 14:00 UTC)."""
    assert _first_cron("swing_screener_daily.yml") == "0 14 * * 1-5"


def test_value_resolver_quarterly_cron_is_first_of_quarter() -> None:
    """value_resolver_quarterly: 0 7 1 */3 * (1st of every 3rd month, 07:00 UTC)."""
    assert _first_cron("value_resolver_quarterly.yml") == "0 7 1 */3 *"


# ---------------------------------------------------------------------------
# 5. Smoke-test workflow: PR-triggered with the expected path filters
# ---------------------------------------------------------------------------


def test_smoke_workflow_triggers_on_pull_request_paths() -> None:
    """ueps_smoke_tests.yml fires on PRs touching UEPS source/test files."""
    workflow = load_workflow("ueps_smoke_tests.yml")
    on = get_on(workflow)
    assert "pull_request" in on, (
        "ueps_smoke_tests.yml must trigger on `pull_request:` "
        "(this is the PR gate)"
    )
    paths = on["pull_request"].get("paths") or []
    assert paths, "ueps_smoke_tests.yml pull_request must declare `paths:`"
    # Spot-check that the canonical UEPS source files appear in the path
    # filter — without these the gate is a no-op for the actual UEPS work.
    expected_paths = {
        "alpha_engine/long_term_pick_contract.py",
        "alpha_engine/value_screener.py",
        "alpha_engine/swing_screener.py",
        "alpha_engine/thesis_resolver.py",
        "alpha_engine/swing_resolver.py",
    }
    missing = expected_paths - set(paths)
    assert not missing, (
        f"ueps_smoke_tests.yml pull_request paths missing required entries: "
        f"{sorted(missing)}"
    )
