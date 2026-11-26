"""Tests for tools/gha_usage_triage.py — the billing-export/cost triage join.

Context: the GitHub Actions usage export is the only source that says what the
Actions bill is actually spent on. Joining it to the repo inventory has two
traps that silently inflate "work to do": GitHub-managed workflows that have no
file at all, and workflows whose billed name is an older name for a file that
still exists. These tests pin both.
"""

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.gha_usage_triage import (  # noqa: E402
    _leading_token,
    _rename_target,
    audit_bucket,
    classify_missing,
    main,
)


def test_leading_token_ignores_short_prefixes():
    assert _leading_token("cross-db-audit.yml") == "cross"
    assert _leading_token("daily-prices-yf-refresh.yml") == "daily"
    assert _leading_token("_dynamic-runner-template.yml") == "dynamic"


def test_rename_target_follows_the_subject_of_the_workflow():
    repo = {"daily-prices-yf-refresh.yml", "cross-db-audit.yml", "live_trading_canada.yml"}
    assert _rename_target("daily-price-refresh.yml", repo) == "daily-prices-yf-refresh.yml"
    assert _rename_target("cross-db-consistency.yml", repo) == "cross-db-audit.yml"
    assert _rename_target("live_trading_canada_free.yml", repo) == "live_trading_canada.yml"


def test_rename_target_does_not_guess_from_a_shared_suffix():
    # both contain "deploy", but mermaid-test-deploy was not renamed to this
    repo = {"backtest-and-deploy.yml"}
    assert _rename_target("mermaid-test-deploy.yml", repo) is None


def test_classify_missing_separates_managed_disabled_and_deleted(tmp_path):
    repo = {"backtest-and-deploy.yml", "daily-prices-yf-refresh.yml"}
    (tmp_path / "old-thing.yml.disabled").write_text("name: old\n")
    assert classify_missing("pages-build-deployment", repo, str(tmp_path))[0] == "MANAGED"
    assert classify_missing("old-thing.yml", repo, str(tmp_path))[0] == "DISABLED"
    assert classify_missing("daily-price-refresh.yml", repo, str(tmp_path))[0] == "RENAMED"
    assert classify_missing("mermaid-test-deploy.yml", repo, str(tmp_path))[0] == "DELETED"


def test_audit_bucket_marks_a_run_that_had_no_log_to_read():
    entry = {"file": "x.yml", "audited": False, "reason": "no run on record"}
    assert audit_bucket(entry, runs_seen=5) == "AUDIT_INCOMPLETE"
    # nothing to read and nothing to run is simply unknown, not incomplete
    assert audit_bucket(entry, runs_seen=0) == "UNAUDITED"


def test_audit_bucket_passes_through_verdicts():
    assert audit_bucket({"verdict": "ERRORS"}, 1) == "ERRORS"
    assert audit_bucket({"verdict": "CLEAN"}, 1) == "CLEAN"
    assert audit_bucket(None, 1) == "UNAUDITED"


def _write_csvs(tmp_path):
    jobs = tmp_path / "jobs.csv"
    with open(jobs, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Job", "Workflow", "Total minutes", "Job runs", "Runner type", "Runner labels"])
        w.writerow(["aggregate", ".github/workflows/cross-aggregator.yml", "15009", "1204", "hosted", "ubuntu-latest"])
        w.writerow(["mirror", ".github/workflows/mirror-site.yml", "8329", "325", "hosted", "ubuntu-latest"])

    wfs = tmp_path / "workflows.csv"
    with open(wfs, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Workflow", "Total minutes", "Workflow runs", "Jobs", "Runner type", "Runtime OS"])
        w.writerow([".github/workflows/cross-aggregator.yml", "15009", "1204", "1", "hosted", "linux"])
        w.writerow([".github/workflows/mirror-site.yml", "8329", "325", "1", "hosted", "linux"])
        w.writerow([".github/workflows/ghost.yml", "42", "7", "1", "hosted", "linux"])
        w.writerow(["pages-build-deployment", "10", "2", "1", "hosted", "linux"])
    return jobs, wfs


def test_end_to_end_join_and_report(tmp_path):
    jobs, wfs = _write_csvs(tmp_path)
    wfdir = tmp_path / "workflows"
    wfdir.mkdir()
    (wfdir / "cross-aggregator.yml").write_text("name: x\n")
    (wfdir / "mirror-site.yml").write_text("name: y\n")
    (wfdir / "never-run.yml").write_text("name: z\n")

    matrix = tmp_path / "matrix.json"
    matrix.write_text(
        json.dumps(
            [
                {"file": "cross-aggregator.yml", "runs_seen": 3, "latest_run": {"conclusion": "success"}},
                {"file": "mirror-site.yml", "runs_seen": 2, "latest_run": {"conclusion": "failure"}},
                {"file": "never-run.yml", "runs_seen": 0},
            ]
        )
    )
    audit = tmp_path / "audit.json"
    audit.write_text(
        json.dumps(
            [
                {"file": "cross-aggregator.yml", "audited": True, "verdict": "ERRORS", "errors": 20},
                {"file": "mirror-site.yml", "audited": True, "verdict": "SUSPICIOUS", "suspicious": 2},
            ]
        )
    )

    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"
    rc = main(
        [
            "--jobs-csv", str(jobs),
            "--workflows-csv", str(wfs),
            "--workflows-dir", str(wfdir),
            "--matrix", str(matrix),
            "--audit", str(audit),
            "--out-md", str(out_md),
            "--out-json", str(out_json),
        ]
    )
    assert rc == 0

    data = json.loads(out_json.read_text())
    t = data["totals"]
    assert t["workflows_in_repo"] == 3
    assert t["total_minutes"] == 15009 + 8329 + 42 + 10
    assert t["total_runs"] == 1204 + 325 + 7 + 2

    by_file = {r["file"]: r for r in data["rows"]}
    assert by_file["cross-aggregator.yml"]["bucket"] == "ERRORS"
    assert by_file["mirror-site.yml"]["bucket"] == "SUSPICIOUS"
    assert by_file["never-run.yml"]["bucket"] == "NEVER_RAN"
    assert by_file["ghost.yml"]["bucket"] == "DELETED"
    assert by_file["pages-build-deployment"]["bucket"] == "MANAGED"

    # errors + suspicious + never-ran + a billed file that is gone; the two
    # GitHub-managed names are excluded because there is no file to fix
    assert t["needs_investigation"] == 4

    md = out_md.read_text()
    assert "# GitHub Actions Usage Triage" in md
    assert "Cost concentration" in md
    assert "Billed under a name the repo no longer has" in md

    # deterministic output for the same inputs
    main(
        [
            "--jobs-csv", str(jobs),
            "--workflows-csv", str(wfs),
            "--workflows-dir", str(wfdir),
            "--matrix", str(matrix),
            "--audit", str(audit),
            "--out-md", str(out_md),
            "--out-json", str(out_json),
        ]
    )
    assert json.loads(out_json.read_text()) == data
