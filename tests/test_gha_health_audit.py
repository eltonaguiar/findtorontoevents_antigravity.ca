"""Tests for tools/gha_health_audit.py — cancel bucketing (R6/R7).

Covers the R7 re-diagnosis from GHACTIONS_2026-11-16/
2026-11-15_21-45_EST_ghactions/08_FOLLOWUP_RESULTS.md section 3: cancelled runs are
bucketed by REAL mechanics (timeout-shaped / eviction-shaped / stack-kill / pr-close),
with only the `external` residual as the true R7 signal. R6 excludes timeout-shaped
cancels from its churn ratio and reports them as `timeout-kill` with the step name.
"""

from __future__ import annotations

from datetime import timedelta

from tools import gha_health_audit as gha
from tools.gha_health_audit import (
    CANCEL_BUCKETS,
    Ctx,
    FixtureClient,
    TriggerInfo,
    build_fixtures,
    cancel_killing_step,
    classify_cancel_run,
    main,
    rule_r6,
    rule_r7,
)


# ---------------------------------------------------------------------------
# fixture run dicts (pure-function level)
# ---------------------------------------------------------------------------

def mk_run(rid=1, wid=900, name="wf", branch="main", *, conclusion="cancelled",
           created="2026-11-16T00:00:00Z", started="2026-11-16T00:00:10Z",
           ended="2026-11-16T00:15:14Z", **extra):
    run = {
        "id": rid, "workflow_id": wid, "name": name, "head_branch": branch,
        "status": "completed", "conclusion": conclusion, "event": "schedule",
        "created_at": created, "run_started_at": started,
        "run_ended_at": ended, "updated_at": ended,
    }
    run.update(extra)
    return run


def started_job(name="report", started="2026-11-16T00:00:10Z", **extra):
    job = {"name": name, "conclusion": "cancelled", "started_at": started, "steps": []}
    job.update(extra)
    return [job]


def make_ctx(runs, workflows, triggers, jobs_map):
    cli = FixtureClient({"jobs": jobs_map, "latest": {}})
    now = gha.FIXTURE_NOW
    return Ctx(now, "eltonaguiar/findtorontoevents_antigravity.ca",
               now - timedelta(days=8), runs, [], [], workflows, triggers, [], cli, False)


# ---------------------------------------------------------------------------
# classify_cancel_run — bucket definitions
# ---------------------------------------------------------------------------

def test_timeout_shaped_lifetime_within_tolerance_of_job_timeout():
    jobs = started_job(timeout_minutes=15)
    # lifetime 904s vs 15m (900s) job timeout -> the sign-coherence-gate shape (08 §3)
    run = mk_run()  # started 00:00:10, ended 00:15:14 => 904s
    assert classify_cancel_run(run, jobs=jobs, job_timeouts_s=[900]) == "timeout-shaped"
    assert classify_cancel_run(run, jobs=jobs, job_timeouts_s=900) == "timeout-shaped"


def test_timeout_shaped_tolerance_boundary_30s():
    jobs = started_job(timeout_minutes=15)
    ok = mk_run(ended="2026-11-16T00:15:40Z")     # 930s = 900 + 30 -> inside
    out = mk_run(ended="2026-11-16T00:15:41Z")    # 931s -> outside
    assert classify_cancel_run(ok, jobs=jobs, job_timeouts_s=[900]) == "timeout-shaped"
    assert classify_cancel_run(out, jobs=jobs, job_timeouts_s=[900]) == "external"


def test_eviction_shaped_zero_jobs_materialized():
    never = mk_run(started=None, ended="2026-11-16T00:05:00Z")
    assert classify_cancel_run(never, jobs=[], job_timeouts_s=None) == "eviction-shaped"
    # unprobed (jobs=None) degrades to the run never having started
    assert classify_cancel_run(never, jobs=None, job_timeouts_s=None) == "eviction-shaped"
    # job row exists but never started -> still 0 jobs ever started
    queued_job = [{"name": "j", "conclusion": None, "started_at": None, "steps": []}]
    assert classify_cancel_run(never, jobs=queued_job, job_timeouts_s=None) == "eviction-shaped"


def test_stack_kill_shaped_cluster_near_newer_run():
    run = mk_run(created="2026-11-16T00:00:00Z", started="2026-11-16T00:00:02Z",
                 ended="2026-11-16T00:00:47Z")
    siblings = [
        mk_run(rid=2, created="2026-11-16T00:00:03Z"),
        mk_run(rid=3, created="2026-11-16T00:00:06Z"),
    ]
    newer = mk_run(rid=4, conclusion="success", created="2026-11-16T00:00:20Z",
                   started="2026-11-16T00:00:20Z", ended="2026-11-16T00:05:00Z")
    assert classify_cancel_run(run, jobs=started_job(), job_timeouts_s=None,
                               siblings=siblings, newer_run=newer) == "stack-kill"


def test_stack_kill_needs_cluster_and_newer_run():
    run = mk_run(created="2026-11-16T00:00:00Z", started="2026-11-16T00:00:02Z",
                 ended="2026-11-16T00:00:47Z")
    far_siblings = [mk_run(rid=2, created="2026-11-16T00:10:00Z")]   # > 120s apart
    near_siblings = [mk_run(rid=2, created="2026-11-16T00:00:03Z")]
    newer = mk_run(rid=4, conclusion="success", created="2026-11-16T00:00:20Z",
                   started="2026-11-16T00:00:20Z", ended="2026-11-16T00:05:00Z")
    far_newer = mk_run(rid=5, conclusion="success", created="2026-11-16T00:10:00Z",
                       started="2026-11-16T00:10:00Z", ended="2026-11-16T00:15:00Z")
    # no newer run at all -> not stack-kill
    assert classify_cancel_run(run, jobs=started_job(), siblings=near_siblings,
                               newer_run=None) == "external"
    # siblings created outside the 120s window -> not stack-kill
    assert classify_cancel_run(run, jobs=started_job(), siblings=far_siblings,
                               newer_run=newer) == "external"
    # newer run's start far from the cluster -> not stack-kill
    assert classify_cancel_run(run, jobs=started_job(), siblings=near_siblings,
                               newer_run=far_newer) == "external"


def test_pr_close_shaped_deleted_branch_or_closed_pr():
    deleted = mk_run(branch=None)
    assert classify_cancel_run(deleted, jobs=started_job()) == "pr-close"
    closed_pr = mk_run(branch="feat/pr1", pull_requests=[{"number": 7, "state": "closed"}])
    assert classify_cancel_run(closed_pr, jobs=started_job()) == "pr-close"


def test_external_is_the_unexplained_residual():
    run = mk_run(branch="main")
    assert classify_cancel_run(run, jobs=started_job(), job_timeouts_s=None,
                               siblings=[], newer_run=None) == "external"


def test_precedence_eviction_before_stack_kill_and_pr_close():
    # 0 jobs materialized wins over every other signature (documented precedence)
    never = mk_run(started=None, ended="2026-11-16T00:05:00Z", branch=None)
    siblings = [mk_run(rid=2, created="2026-11-16T00:00:03Z", started=None)]
    newer = mk_run(rid=3, conclusion="success", created="2026-11-16T00:00:10Z",
                   started="2026-11-16T00:00:10Z")
    assert classify_cancel_run(never, jobs=[], siblings=siblings,
                               newer_run=newer) == "eviction-shaped"


def test_bucket_names_are_the_documented_five():
    assert CANCEL_BUCKETS == ("timeout-shaped", "eviction-shaped", "stack-kill",
                              "pr-close", "external")


# ---------------------------------------------------------------------------
# cancel_killing_step — timeout-kill step attribution
# ---------------------------------------------------------------------------

def test_cancel_killing_step_prefers_in_flight_step():
    jobs = [{"name": "report", "steps": [
        {"name": "Build report", "conclusion": "success",
         "started_at": "2026-11-16T00:00:10Z", "completed_at": "2026-11-16T00:01:00Z"},
        {"name": "Commit JSON report", "conclusion": "cancelled",
         "started_at": "2026-11-16T00:01:00Z", "completed_at": None},
    ]}]
    assert cancel_killing_step(jobs) == "Commit JSON report"


def test_cancel_killing_step_longest_cancelled_step_and_empty():
    jobs = [{"name": "report", "steps": [
        {"name": "quick", "conclusion": "cancelled",
         "started_at": "2026-11-16T00:00:00Z", "completed_at": "2026-11-16T00:00:10Z"},
        {"name": "slow push", "conclusion": "timed_out",
         "started_at": "2026-11-16T00:00:10Z", "completed_at": "2026-11-16T00:14:43Z"},
    ]}]
    assert cancel_killing_step(jobs) == "slow push"
    assert cancel_killing_step([{"steps": [{"name": "ok", "conclusion": "success"}]}]) is None
    assert cancel_killing_step(None) is None


# ---------------------------------------------------------------------------
# timeout candidate resolution (jobs API payload first, then checked-out YAML)
# ---------------------------------------------------------------------------

def test_cancel_timeout_candidates_payload_then_yaml_then_all():
    trig = TriggerInfo(".github/workflows/wf.yml")
    trig.job_timeouts = {"report": 15, "other": 30}
    workflows = [{"id": 900, "name": "wf", "path": ".github/workflows/wf.yml", "state": "active"}]
    ctx = make_ctx([mk_run()], workflows, {".github/workflows/wf.yml": trig}, {})
    payload = started_job(timeout_minutes=5)
    assert ctx.cancel_timeout_candidates(mk_run(), payload) == [300]
    yaml_by_name = started_job()  # payload without timeout -> YAML match on job name
    assert ctx.cancel_timeout_candidates(mk_run(), yaml_by_name) == [900]
    assert ctx.cancel_timeout_candidates(mk_run(), None) == [900, 1800]


# ---------------------------------------------------------------------------
# R6 — churn ratio must NOT be inflated by timeout-shaped cancels
# ---------------------------------------------------------------------------

def _churn_ctx(life_s):
    """15 hourly runs of one workflow: 8 cancelled (own-tick spacing) + 7 success."""
    runs, jobs_map = [], {}
    trig = TriggerInfo(".github/workflows/churn-wf.yml")
    trig.name = "churn-wf"
    trig.events = ["schedule"]
    trig.crons = ["0 * * * *"]
    trig.job_timeouts = {"build": 15}
    for i in range(15):
        rid = 9000 + i
        base = gha.FIXTURE_NOW - timedelta(hours=15 - i)
        started = (base + timedelta(seconds=10)).isoformat().replace("+00:00", "Z")
        ended = (base + timedelta(seconds=10 + life_s)).isoformat().replace("+00:00", "Z")
        conclusion = "cancelled" if i < 8 else "success"
        runs.append(mk_run(rid, 900, "churn-wf", conclusion=conclusion,
                           created=base.isoformat().replace("+00:00", "Z"),
                           started=started, ended=ended))
        jobs_map[str(rid)] = {"jobs": [{
            "name": "build", "conclusion": "cancelled", "started_at": started,
            "steps": [{"name": "Commit JSON report", "conclusion": "cancelled",
                       "number": 1, "started_at": started, "completed_at": None}]}]}
    workflows = [{"id": 900, "name": "churn-wf", "path": ".github/workflows/churn-wf.yml",
                  "state": "active"}]
    ctx = make_ctx(runs, workflows, {".github/workflows/churn-wf.yml": trig}, jobs_map)
    return ctx, runs


def test_r6_excludes_timeout_shaped_cancels_from_churn_ratio():
    ctx, runs = _churn_ctx(life_s=904)  # 904s ~= the 15m job timeout -> timeout-shaped
    raw_ratio = 8 / 15
    assert raw_ratio >= gha.CHURN_CANCEL_MIN  # WITHOUT the exclusion this WOULD be churn
    res = rule_r6(ctx)
    assert res["rows"] == []                      # timeout kills do not inflate the ratio
    assert len(res["timeout_kills"]) == 8
    for row in res["timeout_kills"]:
        assert row["class"] == "timeout-kill"
        assert row["step"] == "Commit JSON report"
        assert row["workflow"] == "churn-wf"
        assert row["lifetime_s"] == 904


def test_r6_still_counts_plain_cancels_as_churn():
    ctx, _runs = _churn_ctx(life_s=3000)  # nowhere near the 900s timeout -> not timeout-shaped
    res = rule_r6(ctx)
    assert res["timeout_kills"] == []
    assert len(res["rows"]) == 1
    row = res["rows"][0]
    assert row["cancelled"] == 8
    assert row["window"] == 15
    assert row["cancel_ratio"] == round(8 / 15, 2)
    assert row["own_tick_spacing"] is True
    assert row["verdict"].startswith("concurrency cancel-loop")


# ---------------------------------------------------------------------------
# R7 — CANCEL BUCKETS on the built-in fixture fleet (dry-run parity)
# ---------------------------------------------------------------------------

def test_r7_bucket_counts_and_external_residual_by_run_id():
    runs, _queued, _running, workflows, triggers, fx = build_fixtures()
    ctx = make_ctx(runs, workflows, triggers, fx["jobs"])
    res = rule_r7(ctx)
    assert res["bucket_counts"] == {
        "timeout-shaped": 3, "eviction-shaped": 17, "stack-kill": 3,
        "pr-close": 2, "external": 1,
    }
    assert res["cancelled_examined"] == 26
    assert res["jobs_probed"] <= gha.MAX_CANCEL_JOB_PROBES
    ext = res["rows"]
    assert len(ext) == 1
    assert ext[0]["workflow"] == "billing-sync"
    assert ext[0]["run_id"] is not None
    assert ext[0]["class"] == "external"
    assert "true R7 signal" in ext[0]["verdict"]


def test_dry_run_exits_zero():
    assert main(["--dry-run"]) == 0
