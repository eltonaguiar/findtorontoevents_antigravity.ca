#!/usr/bin/env python3
"""Contract tests for the DSR artifact that two LIVE pick gates read.

WHY THIS FILE EXISTS
    `tools/deflated_sharpe_results.json` is not a report. It is an INPUT to
    production pick filtering:

        alpha_engine/eagle_gates.py      -> _load_dsr_noise()
        alpha_engine/dsr_pick_filter.py  -> get_dsr_survivors() / get_dsr_noise()

    Both build a "noise set" from `if not entry.get("survives")` and use it to
    suppress picks. Regenerating the artifact with corrected maths (2026-11-22)
    moved that noise set from 16 to 55 strategies -- 21 previously-tradeable
    strategies would have been silently blocked by a *bug fix*.

    A tooling fix must not change what the system trades. These tests pin:
      1. the fields the consumers need are present,
      2. both consumers agree with each other,
      3. a default (non-deploy) run cannot touch the live artifact,
      4. the corrected results live in a separate file and differ in the
         documented direction.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
for p in (str(REPO), str(REPO / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

LIVE = REPO / "tools" / "deflated_sharpe_results.json"
CORRECTED_DIR = REPO / "reports"


def _dsr():
    """Load tools/deflated_sharpe.py BY PATH.

    `import deflated_sharpe` is NOT safe here: a second module with the same name
    exists at alpha_engine/deflated_sharpe.py, and any earlier test that puts
    alpha_engine/ on sys.path registers it under the top-level name first. The
    contract tests then operate on the wrong module and fail with AttributeError --
    only in a full-suite run, never when this file is run alone. Loading by path is
    deterministic and independent of pytest's import order.
    """
    import importlib.util

    path = REPO / "tools" / "deflated_sharpe.py"
    spec = importlib.util.spec_from_file_location("_dsr_tools_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_live():
    if not LIVE.exists():
        pytest.skip("live DSR artifact not present")
    return json.loads(LIVE.read_text())


class TestConsumerContract:
    """The fields the live gates read must keep existing."""

    def test_live_artifact_has_the_fields_consumers_read(self):
        d = _load_live()
        for field in ("key", "survives", "trades"):
            missing = [e.get("key") for e in d["all_strategies"] if field not in e]
            assert not missing, f"field {field!r} missing on {missing[:3]} -- the " \
                                f"live pick gates read it"

    def test_summary_matches_the_rows(self):
        d = _load_live()
        rows = d["all_strategies"]
        assert d["summary"]["strategies_analysed"] == len(rows)
        assert d["summary"]["strategies_surviving"] == sum(
            1 for e in rows if e.get("survives"))


class TestConsumersAgree:
    """Two modules build the same noise set; they must not drift apart."""

    def test_both_consumers_compute_the_same_noise_set(self):
        from alpha_engine.dsr_pick_filter import get_dsr_noise, get_dsr_survivors
        from alpha_engine.eagle_gates import _load_dsr_noise

        eagle = _load_dsr_noise()
        filter_noise = get_dsr_noise()
        survivors = get_dsr_survivors()

        assert set(eagle) == set(filter_noise), (
            "eagle_gates and dsr_pick_filter disagree on the noise set -- one of "
            "them would block picks the other allows")
        # survivors and noise must partition the analysed strategies
        assert not (survivors & filter_noise), "a strategy is both survivor and noise"

    def test_noise_set_is_not_everything(self):
        """If every strategy is noise, the gates would suppress the whole book.

        That is a legitimate possible outcome of correct maths, but it must be a
        DECISION (via --deploy) rather than an accident. If this test ever fails
        because the live artifact genuinely should flag everything, that is a
        deliberate change -- record it and update this test with the reason.
        """
        from alpha_engine.eagle_gates import _load_dsr_noise

        d = _load_live()
        n = len(d["all_strategies"])
        noise = _load_dsr_noise()
        assert len(noise) < n, (
            f"ALL {n} strategies are in the live DSR noise set. The pick gates "
            f"would suppress every pick. Deploying corrected DSR maths is a policy "
            f"change -- see updates/2026-11-22-dsr-artifact-contract.md")


class TestDeployGuard:
    """A default run must not overwrite the file the live gates read."""

    def test_default_run_targets_a_review_path_not_the_live_file(self, monkeypatch, tmp_path):
        ds = _dsr()

        written = {}

        def _fake_analyse(out_path=None, deploy=False):
            written["path"] = out_path
            written["deploy"] = deploy
            return {}

        monkeypatch.setattr(ds, "analyse", _fake_analyse)
        monkeypatch.setattr(sys, "argv", ["deflated_sharpe.py"])
        ds.main()

        assert written["deploy"] is False, "default run must not deploy"
        assert Path(written["path"]).name != "deflated_sharpe_results.json", (
            "default run wrote to the LIVE artifact path")
        assert "deflated_sharpe_corrected_" in Path(written["path"]).name

    def test_deploy_flag_targets_the_live_file(self, monkeypatch):
        ds = _dsr()

        written = {}

        def _fake_analyse(out_path=None, deploy=False):
            written["path"] = out_path
            written["deploy"] = deploy
            return {}

        monkeypatch.setattr(ds, "analyse", _fake_analyse)
        monkeypatch.setattr(sys, "argv", ["deflated_sharpe.py", "--deploy"])
        ds.main()
        assert written["deploy"] is True
        assert Path(written["path"]).name == "deflated_sharpe_results.json"

    def test_live_artifact_untouched_by_a_dry_run(self, tmp_path):
        """End-to-end: run analyse to a temp path and hash the live file.

        Skipped when the analysis input is absent: `audit_dashboard/data/
        dashboard_data.json` is an 18 MB GENERATED file that is not committed, so a
        clean worktree legitimately does not have it. A skip here means "cannot
        evaluate", never "passed".
        """
        ds = _dsr()

        if not Path(ds.DATA_PATH).exists():
            pytest.skip("dashboard_data.json absent (generated, not committed) -- "
                        "cannot evaluate the dry-run guard here")
        before = LIVE.read_bytes()
        ds.analyse(out_path=str(tmp_path / "out.json"), deploy=False)
        assert LIVE.read_bytes() == before, "a non-deploy run modified the live artifact"


class TestCorrectedIsSeparate:
    def test_corrected_artifact_is_a_distinct_file_when_present(self):
        files = sorted(CORRECTED_DIR.glob("deflated_sharpe_corrected_*.json"))
        if not files:
            pytest.skip("no corrected artifact generated yet")
        corr = json.loads(files[-1].read_text())
        live = _load_live()
        # the correction must be visible, not silent
        assert "semantics" in corr and "headline_withdrawn" in corr["semantics"]
        assert corr["config"].get("confidence") == 0.95
        # and it must flag at least as many strategies as the live one (corrected
        # maths is strictly harsher here -- inflated Sharpes were the old defect)
        n_corr_noise = sum(1 for e in corr["all_strategies"] if not e.get("survives"))
        n_live_noise = sum(1 for e in live["all_strategies"] if not e.get("survives"))
        assert n_corr_noise >= n_live_noise, (
            "the corrected artifact is LESS harsh than the live one -- that would "
            "mean the correction is wrong, since the old maths inflated every Sharpe")
