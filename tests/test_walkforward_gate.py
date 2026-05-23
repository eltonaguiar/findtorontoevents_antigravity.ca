"""Tests for tools/check_walkforward_gate.py."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "tools" / "check_walkforward_gate.py"


def _write_backtest(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "bt.json"
    p.write_text(json.dumps({"results": rows}), encoding="utf-8")
    return p


def _write_walkforward(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "wf.json"
    p.write_text(json.dumps({"strategies": rows}), encoding="utf-8")
    return p


def _run(backtest: Path, walkforward: Path, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Make sure rollback flag is unset by default
    env.pop("WALKFORWARD_GATE_DISABLED", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--backtest",
            str(backtest),
            "--walkforward",
            str(walkforward),
        ],
        capture_output=True,
        text=True,
        env=env,
    )


def test_high_bt_wr_with_proven_walkforward_passes(tmp_path):
    # win_rate as fraction (0..1) — 90% > 85% threshold
    bt = _write_backtest(tmp_path, [{"strategy_name": "alpha", "win_rate": 0.90}])
    wf = _write_walkforward(tmp_path, [{"strategy": "alpha", "verdict": "STRONG"}])
    res = _run(bt, wf)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "gated_count: 0" in res.stdout
    assert "passed_count: 1" in res.stdout


def test_high_bt_wr_with_failed_walkforward_blocks(tmp_path):
    bt = _write_backtest(tmp_path, [{"strategy_name": "beta", "win_rate": 0.92}])
    wf = _write_walkforward(tmp_path, [{"strategy": "beta", "verdict": "FAILING"}])
    res = _run(bt, wf)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "gated_count: 1" in res.stdout
    assert "beta" in res.stdout


def test_high_bt_wr_with_missing_walkforward_blocks(tmp_path):
    bt = _write_backtest(tmp_path, [{"strategy_name": "gamma", "win_rate": 0.88}])
    wf = _write_walkforward(tmp_path, [])  # no walk-forward entry at all
    res = _run(bt, wf)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "MISSING" in res.stdout


def test_low_bt_wr_passes_without_walkforward(tmp_path):
    bt = _write_backtest(tmp_path, [{"strategy_name": "delta", "win_rate": 0.60}])
    wf = _write_walkforward(tmp_path, [])
    res = _run(bt, wf)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "gated_count: 0" in res.stdout
    assert "skipped_low_wr_count: 1" in res.stdout


def test_disabled_env_short_circuits(tmp_path):
    # Even with a clearly failing strategy, env flag should force exit 0
    bt = _write_backtest(tmp_path, [{"strategy_name": "epsilon", "win_rate": 0.99}])
    wf = _write_walkforward(tmp_path, [{"strategy": "epsilon", "verdict": "FAILING"}])
    res = _run(bt, wf, env_extra={"WALKFORWARD_GATE_DISABLED": "1"})
    assert res.returncode == 0, res.stdout + res.stderr
    assert "DISABLED" in res.stdout


def test_no_backtest_data_warns_and_passes(tmp_path):
    bt = tmp_path / "missing.json"  # does not exist
    wf = _write_walkforward(tmp_path, [])
    res = _run(bt, wf)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "no backtest data" in res.stdout


def test_winrate_already_in_percent(tmp_path):
    # Some files (walk-forward dump) store 75.7-style percent. Ensure no double
    # multiplication. 86 should still trigger the gate.
    bt = _write_backtest(tmp_path, [{"strategy_name": "zeta", "win_rate": 86.0}])
    wf = _write_walkforward(tmp_path, [{"strategy": "zeta", "verdict": "FAILING"}])
    res = _run(bt, wf)
    assert res.returncode == 1, res.stdout + res.stderr


# ── diff-aware gate (--diff-base) ───────────────────────────────────────


def _run_args(extra: list[str], env_extra: dict | None = None) -> subprocess.CompletedProcess:
    """Run the gate with arbitrary extra CLI args."""
    env = os.environ.copy()
    env.pop("WALKFORWARD_GATE_DISABLED", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *extra],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
    )


def test_diff_base_no_changed_files_passes(tmp_path):
    # A gated strategy in a tmp backtest file. With --diff-base HEAD the gate
    # diffs incubator/backtest_results/ HEAD...HEAD (empty) — the tmp file is
    # not under that path, so 0 changed files => gate not applicable => PASS.
    bt = _write_backtest(tmp_path, [{"strategy_name": "gamma", "win_rate": 0.99}])
    wf = _write_walkforward(tmp_path, [])
    res = _run_args(["--backtest", str(bt), "--walkforward", str(wf),
                     "--diff-base", "HEAD"])
    assert res.returncode == 0, res.stdout + res.stderr
    assert "no changed backtest files" in res.stdout


def test_diff_base_bad_ref_falls_back_to_full_eval(tmp_path):
    # An unresolvable ref makes `git diff` exit non-zero. Fail-safe: fall back
    # to full evaluation rather than skipping the gate — the gated strategy in
    # --backtest must still block (exit 1).
    bt = _write_backtest(tmp_path, [{"strategy_name": "delta", "win_rate": 0.97}])
    wf = _write_walkforward(tmp_path, [{"strategy": "delta", "verdict": "FAILING"}])
    res = _run_args(["--backtest", str(bt), "--walkforward", str(wf),
                     "--diff-base", "nonexistent-ref-zzz-9999"])
    assert res.returncode == 1, res.stdout + res.stderr
    assert "falling back to full evaluation" in res.stdout


def test_no_diff_base_unchanged_behavior(tmp_path):
    # Without --diff-base the gate evaluates everything passed via --backtest.
    bt = _write_backtest(tmp_path, [{"strategy_name": "eps", "win_rate": 0.98}])
    wf = _write_walkforward(tmp_path, [{"strategy": "eps", "verdict": "FAILING"}])
    res = _run_args(["--backtest", str(bt), "--walkforward", str(wf)])
    assert res.returncode == 1, res.stdout + res.stderr


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
