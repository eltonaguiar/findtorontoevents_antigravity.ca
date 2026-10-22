"""Tests for the P1-1 standing CI artifact-cell check."""

import json

from tools.check_walkforward_artifact_cells import check_report, main


def _write_report(tmp_path, name, artifact_cells, n_cleaned=100, n_test=50):
    p = tmp_path / name
    p.write_text(
        json.dumps(
            {
                "n_cleaned": n_cleaned,
                "n_test": n_test,
                "artifact_cells": artifact_cells,
            }
        ),
        encoding="utf-8",
    )
    return p


def test_clean_report_passes(tmp_path):
    p = _write_report(tmp_path, "clean.json", [])
    assert check_report(p)["n_artifact_cells"] == 0
    assert main(["--report", str(p)]) == 0


def test_artifact_report_fails(tmp_path):
    p = _write_report(tmp_path, "bad.json", ["CRYPTO|BTCUSDT|atr_percentile_gate|LONG"])
    assert check_report(p)["n_artifact_cells"] == 1
    assert main(["--report", str(p)]) == 1


def test_multiple_artifacts_all_listed(tmp_path):
    p = _write_report(
        tmp_path,
        "multi.json",
        ["A|x|s|LONG", "B|y|t|SHORT", "C|z|u|LONG"],
    )
    res = check_report(p)
    assert res["n_artifact_cells"] == 3
    assert len(res["artifact_cells"]) == 3


def test_missing_report_usage_error(tmp_path):
    assert main(["--report", str(tmp_path / "nope.json")]) == 2


def test_latest_glob_returns_newest(tmp_path, monkeypatch):
    from tools.check_walkforward_artifact_cells import REPORTS_DIR

    monkeypatch.setattr("tools.check_walkforward_artifact_cells.REPORTS_DIR", tmp_path)
    old = tmp_path / "walkforward_strategy_eval_2026-10-20.json"
    new = tmp_path / "walkforward_strategy_eval_2026-10-22.json"
    old.write_text(json.dumps({"artifact_cells": []}), encoding="utf-8")
    new.write_text(json.dumps({"artifact_cells": ["X"]}), encoding="utf-8")
    # Ensure `new` is newest by mtime.
    new.touch()
    from tools.check_walkforward_artifact_cells import _latest_report

    assert _latest_report().name == new.name
