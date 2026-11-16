"""Tests for tools/gha_health_audit.py — cancel bucketing (R6/R7) + guardian v1.1.

Covers the R7 re-diagnosis from GHACTIONS_2026-11-16/
2026-11-15_21-45_EST_ghactions/08_FOLLOWUP_RESULTS.md section 3: cancelled runs are
bucketed by REAL mechanics (timeout-shaped / eviction-shaped / stack-kill / pr-close),
with only the `external` residual as the true R7 signal. R6 excludes timeout-shaped
cancels from its churn ratio and reports them as `timeout-kill` with the step name.

Also covers the guardian v1.1 rule re-reads (09_NEXT_PRACTICE_ENGAGEMENTS.md section 4):
R1/R2/R3 surface timeout-shaped `cancelled` kills as broken/flapping (step attribution
via `cancel_killing_step`); R5 excludes timeout-shaped lifetimes from the p90 hog
baseline; R9 re-derives stale/never-run verdicts at run-ID level and withholds verdicts
a truncated bulk sample cannot confirm (the "235 stale"-class artifact).
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
    rule_r1,
    rule_r2,
    rule_r3,
    rule_r5,
    rule_r6,
    rule_r7,
    rule_r9,
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


def make_ctx(runs, workflows, triggers, jobs_map, *, latest=None, truncated=False,
             running=None, queued=None):
    cli = FixtureClient({"jobs": jobs_map, "latest": latest or {}})
    now = gha.FIXTURE_NOW
    return Ctx(now, "eltonaguiar/findtorontoevents_antigravity.ca",
               now - timedelta(days=8), runs, queued or [], running or [], workflows,
               triggers, [], cli, truncated)


def timed_out_kill_jobs(step="Commit JSON report"):
    """Jobs payload for a timeout-shaped kill: one started job, step in flight."""
    return {"jobs": [{
        "name": "report", "conclusion": "cancelled", "timeout_minutes": 15,
        "started_at": "2026-11-16T00:00:10Z", "completed_at": "2026-11-16T00:15:14Z",
        "steps": [
            {"name": "Build report", "conclusion": "success", "number": 1,
             "started_at": "2026-11-16T00:00:10Z", "completed_at": "2026-11-16T00:01:00Z"},
            {"name": step, "conclusion": "cancelled", "number": 2,
             "started_at": "2026-11-16T00:01:00Z", "completed_at": None},
        ]}]}


def daily_trigger(path, name, job_timeouts=None):
    trig = TriggerInfo(path)
    trig.name = name
    trig.events = ["schedule"]
    trig.crons = ["0 6 * * *"]
    trig.job_timeouts = dict(job_timeouts or {})
    return trig


def rel_run(rid, wid, name, hours_ago, *, conclusion="cancelled", life_s=904.0,
            started=True, event="schedule", branch="main"):
    """Completed run whose start/end sit `hours_ago` before FIXTURE_NOW (life = life_s)."""
    base = gha.FIXTURE_NOW - timedelta(hours=hours_ago)
    start = (base + timedelta(seconds=10)) if started else None
    end = (start or base) + timedelta(seconds=life_s)
    return {
        "id": rid, "workflow_id": wid, "name": name, "head_branch": branch,
        "status": "completed", "conclusion": conclusion, "event": event,
        "created_at": base.isoformat().replace("+00:00", "Z"),
        "run_started_at": start.isoformat().replace("+00:00", "Z") if start else None,
        "run_ended_at": end.isoformat().replace("+00:00", "Z"),
        "updated_at": end.isoformat().replace("+00:00", "Z"),
    }


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


# ---------------------------------------------------------------------------
# guardian v1.1 (09 §4) — R1/R2: timeout-shaped `cancelled` kills are BROKEN
# ---------------------------------------------------------------------------

def _timeout_kill_ctx(extra=()):
    """Nightly workflow whose runs all die at the 15m job timeout (904s kills)."""
    runs, jobs_map = [], {}
    path = ".github/workflows/nightly-timeout.yml"
    trig = daily_trigger(path, "nightly-timeout", job_timeouts={"report": 15})
    for i, h in enumerate((2.0, 26.0, 50.0)):
        rid = 7000 + i
        runs.append(rel_run(rid, 901, "nightly-timeout", h, life_s=904.0))
        jobs_map[str(rid)] = timed_out_kill_jobs()
    runs.extend(extra)
    workflows = [{"id": 901, "name": "nightly-timeout", "path": path, "state": "active"}]
    return make_ctx(runs, workflows, {path: trig}, jobs_map), runs


def test_r1_surfaces_timeout_shaped_cancel_kills_as_broken():
    ctx, _runs = _timeout_kill_ctx()
    res = rule_r1(ctx)
    rows = res["rows"]
    assert len(rows) == 1
    row = rows[0]
    assert row["workflow"] == "nightly-timeout"
    assert row["conclusion"] == "cancelled"          # BAD_CONCLUSIONS skips cancelled...
    assert row["class"] == "broken"                  # ...but a timeout kill is degraded
    assert row["timeout_kill"] is True
    assert row["killing_step"] == "Commit JSON report"
    assert "timeout-shaped" in row["verdict"]


def test_r1_timeout_kill_group_not_counted_recovered_or_plain_green():
    ctx, _runs = _timeout_kill_ctx()
    rule_r1(ctx)
    assert ctx.recovered == 0
    assert ctx.plain_green == 0


def test_r1_recovered_when_success_follows_timeout_kills():
    newer_success = rel_run(7010, 901, "nightly-timeout", 1.0, conclusion="success", life_s=300.0)
    ctx, _runs = _timeout_kill_ctx(extra=(newer_success,))
    assert rule_r1(ctx)["rows"] == []
    assert ctx.recovered == 1


def test_r1_ignores_eviction_cancels_they_are_kill_mechanics():
    # eviction-shaped cancels (0 jobs ever started) are mechanics (08 §3), not health
    runs = [rel_run(7020 + i, 902, "evict-wf", 3.0 + i, life_s=300.0, started=False)
            for i in range(3)]
    path = ".github/workflows/evict-wf.yml"
    trig = daily_trigger(path, "evict-wf", job_timeouts={"build": 5})
    workflows = [{"id": 902, "name": "evict-wf", "path": path, "state": "active"}]
    ctx = make_ctx(runs, workflows, {path: trig}, {str(r["id"]): {"jobs": []} for r in runs})
    assert rule_r1(ctx)["rows"] == []
    assert ctx.plain_green == 1


def test_r2_watches_timeout_kill_r1_candidates():
    ctx, _runs = _timeout_kill_ctx()
    r1_rows = rule_r1(ctx)["rows"]
    res = rule_r2(ctx, r1_rows)
    watch = res["rows"]
    assert any(w["workflow"] == "nightly-timeout" and w["state"] == "watching" for w in watch)
    entry = next(w for w in watch if w["workflow"] == "nightly-timeout")
    assert entry["expect_by"] is not None
    assert entry["cadence_hours"] == 24.0


# ---------------------------------------------------------------------------
# guardian v1.1 (09 §4) — R3: timeout kills count as flapping fails, step named
# ---------------------------------------------------------------------------

def _flap_timeout_ctx(life_s=904.0):
    """15 hourly runs: 1 latest green, 5 interleaved kills/fails, 9 clean greens."""
    runs, jobs_map = [], {}
    path = ".github/workflows/flap-timeout.yml"
    trig = TriggerInfo(path)
    trig.name = "flap-timeout"
    trig.events = ["schedule"]
    trig.crons = ["0 * * * *"]
    trig.job_timeouts = {"build": 15}
    for i in range(15):
        rid = 7300 + i
        hours_ago = 1.0 + i * 1.0
        if i in (1, 3, 5, 7, 9):
            runs.append(rel_run(rid, 903, "flap-timeout", hours_ago, life_s=life_s))
            jobs_map[str(rid)] = timed_out_kill_jobs(step="Slow push")
        else:
            runs.append(rel_run(rid, 903, "flap-timeout", hours_ago,
                               conclusion="success", life_s=600.0))
    workflows = [{"id": 903, "name": "flap-timeout", "path": path, "state": "active"}]
    return make_ctx(runs, workflows, {path: trig}, jobs_map), runs


def test_r3_counts_timeout_kills_as_flapping_failures_with_killing_step():
    ctx, _runs = _flap_timeout_ctx(life_s=904.0)
    res = rule_r3(ctx)
    assert len(res["rows"]) == 1
    row = res["rows"][0]
    assert row["workflow"] == "flap-timeout"
    assert row["fails_in_window"] == 5
    assert row["window"] == 15
    assert "Slow push" in row["failing_steps"]         # via cancel_killing_step
    assert row["split"]["real_bug"] + row["split"]["infra_flake"] >= 2


def test_r3_excludes_plain_cancel_mechanics_from_failures():
    # same shape but lifetimes 3000s — not timeout-shaped (external cancels) => no flapper
    ctx, _runs = _flap_timeout_ctx(life_s=3000.0)
    assert rule_r3(ctx)["rows"] == []


# ---------------------------------------------------------------------------
# guardian v1.1 (09 §4) — R5: timeout-shaped lifetimes excluded from p90 baseline
# ---------------------------------------------------------------------------

def _hog_ctx(kill_life_s):
    """4 clean 0.2h runs + 4 kills at `kill_life_s` (job timeout 114m) + a 1h runner."""
    runs, jobs_map = [], {}
    path = ".github/workflows/hog-wf.yml"
    trig = TriggerInfo(path)
    trig.name = "hog-wf"
    trig.events = ["schedule"]
    trig.crons = ["0 * * * *"]
    trig.job_timeouts = {"build": 114}
    for i in range(4):
        runs.append(rel_run(7400 + i, 904, "hog-wf", 3.0 + i, conclusion="success", life_s=720.0))
        rid_k = 7410 + i
        runs.append(rel_run(rid_k, 904, "hog-wf", 5.0 + i, life_s=kill_life_s))
        jobs_map[str(rid_k)] = {"jobs": [{"name": "build", "conclusion": "cancelled",
                                          "timeout_minutes": 114,
                                          "started_at": "2026-11-15T00:00:00Z"}]}
    start_1h_ago = (gha.FIXTURE_NOW - timedelta(hours=1.0)).isoformat().replace("+00:00", "Z")
    running_run = {
        "id": 7450, "workflow_id": 904, "name": "hog-wf", "head_branch": "main",
        "status": "in_progress", "conclusion": None, "event": "schedule",
        "created_at": start_1h_ago, "run_started_at": start_1h_ago, "updated_at": start_1h_ago,
    }
    workflows = [{"id": 904, "name": "hog-wf", "path": path, "state": "active"}]
    ctx = make_ctx(runs, workflows, {path: trig}, jobs_map, running=[running_run])
    return ctx


def test_r5_p90_baseline_excludes_timeout_shaped_lifetimes():
    # kills at 6840s = exactly the 114m timeout -> timeout-shaped -> baseline is 0.2h
    ctx = _hog_ctx(kill_life_s=6840.0)
    res = rule_r5(ctx)
    assert len(res["rows"]) == 1
    row = res["rows"][0]
    assert row["workflow"] == "hog-wf"
    assert row["workflow_p90_hours"] == 0.2           # clean runtimes only
    assert "> 2x p90" in row["reason"]


def test_r5_polluted_baseline_would_silence_the_hog():
    # kills at 9000s are NOT timeout-shaped (|9000-6840| > 30) -> stay in the baseline
    # -> p90 inflates to 2.5h -> the 1h runner no longer trips > 2x p90 (the old miss)
    ctx = _hog_ctx(kill_life_s=9000.0)
    assert rule_r5(ctx)["rows"] == []


# ---------------------------------------------------------------------------
# guardian v1.1 (09 §4) — R9: stale/never-run verdicts re-derived at run-ID level
# ---------------------------------------------------------------------------

def _r9_ctx(truncated, latest_map, runs=None):
    path = ".github/workflows/old-daily-wf.yml"
    trig = daily_trigger(path, "old-daily-wf")
    workflows = [{"id": 905, "name": "old-daily-wf", "path": path, "state": "active"}]
    return make_ctx(runs or [], workflows, {path: trig}, {},
                    latest=latest_map, truncated=truncated)


def test_r9_stale_verdict_re_derived_at_run_id_level():
    old = rel_run(7500, 905, "old-daily-wf", hours_ago=24 * 45, conclusion="success", life_s=300.0)
    ctx = _r9_ctx(truncated=True, latest_map={"905": {"workflow_runs": [old]}})
    res = rule_r9(ctx)
    rows = res["rows"]
    assert len(rows) == 1
    row = rows[0]
    assert row["workflow"] == "old-daily-wf"
    assert row["derived_from"] == "run-id-probe"       # not the bulk-window cache
    assert row["age_days"] > gha.STALE_THRESHOLD_DAYS["daily"]
    assert "stale by cadence" in row["verdict"]


def test_r9_withholds_stale_verdict_when_probe_budget_exhausted():
    # "235 stale"-class trap: truncated bulk sample hints stale, no run-ID-level probe
    # budget left -> the stale verdict must be WITHHELD, not emitted from cached figures
    hint = rel_run(7501, 905, "old-daily-wf", hours_ago=24 * 45, conclusion="success", life_s=300.0)
    ctx = _r9_ctx(truncated=True, latest_map={}, runs=[hint])
    saved = gha.MAX_R9_PROBES
    gha.MAX_R9_PROBES = 0
    try:
        res = rule_r9(ctx)
    finally:
        gha.MAX_R9_PROBES = saved
    rows = res["rows"]
    assert len(rows) == 1
    assert rows[0]["age_days"] == "SKIPPED(truncated-window)"
    assert "withheld" in rows[0]["verdict"]
    assert not any(isinstance(r.get("age_days"), (int, float)) for r in rows)


def test_r9_never_run_requires_run_id_probe():
    ctx = _r9_ctx(truncated=False, latest_map={"905": {"workflow_runs": []}})
    res = rule_r9(ctx)
    rows = res["rows"]
    assert len(rows) == 1
    assert rows[0]["age_days"] is None
    assert rows[0]["last_run"] is None
    assert rows[0]["derived_from"] == "run-id-probe"
    assert "NEVER RUN" in rows[0]["verdict"]


def test_r9_fresh_window_run_produces_no_stale_row():
    fresh = rel_run(7502, 905, "old-daily-wf", hours_ago=2.0, conclusion="success", life_s=300.0)
    ctx = _r9_ctx(truncated=True, latest_map={}, runs=[fresh])
    assert rule_r9(ctx)["rows"] == []
