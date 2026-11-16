"""Tests for tools/gha_health_audit.py — cancel bucketing (R6/R7).

Covers the R7 re-diagnosis from GHACTIONS_2026-11-16/
2026-11-15_21-45_EST_ghactions/08_FOLLOWUP_RESULTS.md section 3: cancelled runs are
bucketed by REAL mechanics (timeout-shaped / eviction-shaped / stack-kill / pr-close),
with only the `external` residual as the true R7 signal. R6 excludes timeout-shaped
cancels from its churn ratio and reports them as `timeout-kill` with the step name.

Also covers the v1.2 cancel-bucket calibration (2026-11-16): the live v1.1 report's
"external: 14" run shapes (dup-guard pre-fix copies / CI Tests supersede / RoC deploy
cancel) are GitHub supersede-cancels ("Canceling since a higher priority waiting
request for X exists" + a newer same/referenced run within ~10m) and bucket as the
`supersede` sub-bucket reported under `stack-kill`; 13 of the 14 reclassify, 1 stays
`external` (the true residual the run-ID-level manual analysis kept).
"""

from __future__ import annotations

from datetime import timedelta

from tools import gha_health_audit as gha
from tools.gha_health_audit import (
    CANCEL_BUCKETS,
    CANCEL_STACK_SUBS,
    CANCEL_SUPERSEDE_MARKER,
    Ctx,
    FixtureClient,
    TriggerInfo,
    build_fixtures,
    cancel_killing_step,
    classify_cancel_run,
    classify_cancel_run_detail,
    main,
    rule_r6,
    rule_r7,
)

SUPERSEDE_REASON = (
    "Canceling since a higher priority waiting request for ci-tests exists"
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


def make_ctx(runs, workflows, triggers, jobs_map, annotations=None):
    cli = FixtureClient({"jobs": jobs_map, "latest": {}, "annotations": annotations or {}})
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
    # v1.2: `supersede` is a SUB-bucket reported under stack-kill, not a 6th bucket
    assert CANCEL_STACK_SUBS == ("supersede", "cancel-in-progress")


# ---------------------------------------------------------------------------
# v1.2 supersede sub-bucket (reported under stack-kill)
# mechanic: "Canceling since a higher priority waiting request for X exists"
# + a newer run of the same OR referenced workflow started within ~10m
# ---------------------------------------------------------------------------

def test_supersede_marker_plus_newer_run_is_stack_kill_supersede():
    run = mk_run(created="2026-11-16T00:00:00Z", started="2026-11-16T00:00:02Z",
                 ended="2026-11-16T00:04:00Z", cancel_reason=SUPERSEDE_REASON)
    newer = mk_run(rid=2, conclusion="success", created="2026-11-16T00:03:00Z",
                   started="2026-11-16T00:03:00Z", ended="2026-11-16T00:09:00Z")
    jobs = started_job()
    assert classify_cancel_run(run, jobs=jobs, job_timeouts_s=None,
                               related_newer=[newer]) == "stack-kill"
    assert classify_cancel_run_detail(run, jobs=jobs, job_timeouts_s=None,
                                      related_newer=[newer]) == ("stack-kill", "supersede")


def test_supersede_needs_marker_and_near_newer_run():
    newer = mk_run(rid=2, conclusion="success", created="2026-11-16T00:03:00Z",
                   started="2026-11-16T00:03:00Z", ended="2026-11-16T00:09:00Z")
    jobs = started_job()
    # no marker -> the newer run alone is not supersede evidence
    plain = mk_run(created="2026-11-16T00:00:00Z", started="2026-11-16T00:00:02Z",
                   ended="2026-11-16T00:04:00Z")
    assert classify_cancel_run(plain, jobs=jobs, job_timeouts_s=None,
                               related_newer=[newer]) == "external"
    # marker but the newer run starts OUTSIDE the ~10m window -> not supersede
    marked_far = mk_run(created="2026-11-16T00:00:00Z", started="2026-11-16T00:00:02Z",
                        ended="2026-11-16T00:04:00Z", cancel_reason=SUPERSEDE_REASON)
    far_newer = mk_run(rid=3, conclusion="success", created="2026-11-16T00:21:00Z",
                       started="2026-11-16T00:21:00Z", ended="2026-11-16T00:27:00Z")
    assert classify_cancel_run(marked_far, jobs=jobs, job_timeouts_s=None,
                               related_newer=[far_newer]) == "external"
    # marker but NO newer run at all -> not supersede
    assert classify_cancel_run(marked_far, jobs=jobs, job_timeouts_s=None,
                               related_newer=[]) == "external"


def test_supersede_window_boundary_10m_and_eviction_precedence():
    jobs = started_job()
    run = mk_run(created="2026-11-16T00:00:00Z", started="2026-11-16T00:00:02Z",
                 ended="2026-11-16T00:04:00Z", cancel_reason=SUPERSEDE_REASON)
    near = mk_run(rid=2, conclusion="success", created="2026-11-16T00:09:00Z",
                  started="2026-11-16T00:09:00Z", ended="2026-11-16T00:15:00Z")
    outside = mk_run(rid=3, conclusion="success", created="2026-11-16T00:11:00Z",
                     started="2026-11-16T00:11:00Z", ended="2026-11-16T00:17:00Z")
    assert classify_cancel_run_detail(run, jobs=jobs, job_timeouts_s=None,
                                      related_newer=[near]) == ("stack-kill", "supersede")
    assert classify_cancel_run(run, jobs=jobs, job_timeouts_s=None,
                               related_newer=[outside]) == "external"
    # (b) 0-jobs pending kills stay eviction-shaped even with marker + near newer run
    never = mk_run(started=None, ended="2026-11-16T00:05:00Z", cancel_reason=SUPERSEDE_REASON)
    assert classify_cancel_run(never, jobs=[], job_timeouts_s=None,
                               related_newer=[near]) == "eviction-shaped"


def test_supersede_accepts_referenced_workflow_newer_runs():
    # the newer run may belong to a REFERENCED (workflow_run upstream / shared
    # concurrency group) workflow — the RoC deploy cancel shape
    run = mk_run(rid=10, wid=900, created="2026-11-16T00:00:00Z",
                 started="2026-11-16T00:00:02Z", ended="2026-11-16T00:05:00Z",
                 cancel_reason=SUPERSEDE_REASON)
    upstream_newer = mk_run(rid=11, wid=901, conclusion="success",
                            created="2026-11-16T00:04:00Z",
                            started="2026-11-16T00:04:30Z", ended="2026-11-16T00:10:00Z")
    assert classify_cancel_run_detail(run, jobs=started_job(), job_timeouts_s=None,
                                      related_newer=[upstream_newer]
                                      ) == ("stack-kill", "supersede")


def test_cancel_reason_text_scans_annotations_and_job_descriptions():
    # live shape: the reason arrives via the /actions/runs/<id>/annotations payload
    run = mk_run(created="2026-11-16T00:00:00Z", started="2026-11-16T00:00:02Z",
                 ended="2026-11-16T00:04:00Z")
    newer = mk_run(rid=2, conclusion="success", created="2026-11-16T00:02:00Z",
                   started="2026-11-16T00:02:00Z", ended="2026-11-16T00:08:00Z")
    anns = [{"message": SUPERSEDE_REASON}]
    assert classify_cancel_run_detail(run, jobs=started_job(), job_timeouts_s=None,
                                      related_newer=[newer], annotations=anns
                                      ) == ("stack-kill", "supersede")
    jobs_desc = [{"name": "j", "conclusion": "cancelled",
                  "description": SUPERSEDE_REASON, "started_at": "2026-11-16T00:00:02Z",
                  "steps": []}]
    assert classify_cancel_run(run, jobs=jobs_desc, job_timeouts_s=None,
                               related_newer=[newer]) == "stack-kill"
    assert CANCEL_SUPERSEDE_MARKER in SUPERSEDE_REASON


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
    ctx = make_ctx(runs, workflows, triggers, fx["jobs"], fx.get("annotations"))
    res = rule_r7(ctx)
    # v1.2 calibration: the 13 supersede shapes land under stack-kill; external keeps
    # only the 2 true residuals (billing-sync + the 14th calibration run).
    assert res["bucket_counts"] == {
        "timeout-shaped": 3, "eviction-shaped": 17, "stack-kill": 16,
        "pr-close": 2, "external": 2,
    }
    assert res["stack_kill_subs"] == {"supersede": 13, "cancel-in-progress": 3}
    assert res["cancelled_examined"] == 40
    assert res["jobs_probed"] <= gha.MAX_CANCEL_JOB_PROBES
    assert res["annotation_probes"] <= gha.MAX_CANCEL_ANNOTATION_PROBES
    ext = res["rows"]
    assert len(ext) == 2
    assert {x["workflow"] for x in ext} == {"billing-sync", "CI Tests"}
    assert all(x["class"] == "external" for x in ext)
    assert all("true R7 signal" in x["verdict"] for x in ext)


def test_calibration_real_14_run_shapes_reclassify_13_of_14():
    """The real v1.1 "external: 14" shapes — dup-guard pre-fix copies, CI Tests
    supersede, RoC deploy cancel — 13 reclassify out of `external` into
    stack-kill/supersede; the 14th (no marker, no near newer run) stays external.

    BEFORE (v1.1 rule set — no supersede rule): all 14 landed in `external` (the
    live v1.1 report's external:14). That is reproduced below by draining the
    supersede evidence (related_newer=[] / no annotations).
    """
    runs, _queued, _running, workflows, triggers, fx = build_fixtures()
    ctx = make_ctx(runs, workflows, triggers, fx["jobs"], fx.get("annotations"))
    calib = fx["calibration"]
    by_id = {r["id"]: r for r in runs}
    sup_ids = calib["supersede_ids"]
    ext_ids = calib["external_ids"]
    assert len(sup_ids) == 13 and len(ext_ids) == 1  # the real 14-run split

    # AFTER: 13 x ("stack-kill", "supersede"), 1 x ("external", None)
    for rid in sup_ids:
        assert ctx.cancel_detail(by_id[rid]) == ("stack-kill", "supersede"), rid
    for rid in ext_ids:
        assert ctx.cancel_detail(by_id[rid]) == ("external", None), rid

    # one of the 13 carries its reason ONLY via the /annotations payload (live shape)
    inline = [by_id[rid] for rid in sup_ids if by_id[rid].get("cancel_reason")]
    assert len(inline) == 12
    ann_only = [by_id[rid] for rid in sup_ids if not by_id[rid].get("cancel_reason")]
    assert len(ann_only) == 1
    assert ctx.cancel_annotations_for(ann_only[0])  # fetched from the annotations endpoint

    # BEFORE: the v1.1 classifier (timeout/eviction/120s-stack/pr-close only) put
    # every one of the 14 in `external` — the supersede evidence is what reclassifies.
    for rid in sup_ids + ext_ids:
        r = by_id[rid]
        jobs = ctx.cancel_jobs_for(r)
        assert not gha._stack_kill_shaped(r, siblings=[], newer_run=ctx._newer_run_for(r),
                                          window_s=gha.CANCEL_STACK_WINDOW_S)
        assert not gha._pr_close_shaped(r)
        assert classify_cancel_run(r, jobs=jobs, job_timeouts_s=[],
                                   siblings=[], newer_run=ctx._newer_run_for(r),
                                   related_newer=[]) == "external"


def test_dry_run_exits_zero():
    assert main(["--dry-run"]) == 0
