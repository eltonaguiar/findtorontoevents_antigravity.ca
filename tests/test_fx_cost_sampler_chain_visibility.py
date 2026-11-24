"""Chain-visibility contract for tools/fx_cost_sampler.py (2026-11-23).

Why this exists
    run_overlap() swallows any strategy-chain failure into
    ``chain = {"state": "CHAIN_FAILED", "error": repr(exc)}`` and still exits 0.
    The console summary printed status, cost and verdict but never the chain
    state or its error, so a green GitHub Actions run with
    ``verdict: UNCHANGED_UNKNOWN`` gave a maintainer no hint that a subsystem
    failed - the evidence lived only in the committed JSON artifact.

    The contract enforced here:
      1. A failed chain prints a WARNING line carrying BOTH the state and the
         error text (plus the consequence note).
      2. A ``None`` chain prints an explicit "not run" line.
      3. A successful chain prints an informational line and NO warning.
      4. The exit code is 0 in the CHAIN_FAILED case - the fix is stdout only
         and must not change behaviour.

    No network: ``sample_loop`` and ``run_strategy_chain`` are monkeypatched.
"""
import argparse
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import fx_cost_sampler as fxs


def _fake_samples(pairs, n=40):
    """Plausible, varied quotes: n>=30, distinct, stable, ~3bp median."""
    out = []
    for p in pairs:
        for i in range(n):
            spread = 2.0 + 0.05 * i            # distinct every poll, all < 8bp
            mid = 1.1000 + i * 0.0001
            half = (spread / 1e4 / 2.0) * mid
            out.append({
                "pair": p,
                "plausible": True,
                "full_spread_bp": spread,
                "bid": mid - half,
                "ask": mid + half,
                "mid": mid,
            })
    return out


def _args(tmp_path, **over):
    a = argparse.Namespace(
        pairs="eurusd,gbpusd",
        interval=1.0,
        max_minutes=0.0,
        until_samples=30,
        max_polls=1,
        dry_run=False,
        ignore_session=True,
        no_chain=False,
        chain_shuffles=10,
        seed=42,
        out=str(tmp_path / "FOREX_COST_test_overlap.json"),
        out_md="",
    )
    for k, v in over.items():
        setattr(a, k, v)
    return a


@pytest.fixture
def sampled(monkeypatch):
    """Real run_overlap, stubbed sampling - no network."""
    pairs = ["eurusd", "gbpusd"]

    def fake_loop(pairs_, token, interval, max_minutes, until_samples, max_polls):
        return {"samples": _fake_samples(pairs_), "poll_count": 1,
                "api_unreachable": False,
                "window_start_utc": "2026-11-23T13:48:00+00:00",
                "window_end_utc": "2026-11-23T13:49:00+00:00"}

    monkeypatch.setenv("TIINGO_API_KEY", "test-token")
    monkeypatch.setattr(fxs, "sample_loop", fake_loop)
    return pairs


def _run(args, capsys):
    rc = fxs.run_overlap(args)
    return rc, capsys.readouterr().out


def test_chain_failed_warning_carries_state_and_error(sampled, monkeypatch, tmp_path, capsys):
    def boom(cost_bp, shuffles, seed):
        raise RuntimeError("chain exploded: no meanrev module")

    monkeypatch.setattr(fxs, "run_strategy_chain", boom)
    rc, out = _run(_args(tmp_path), capsys)

    assert "WARNING" in out
    assert "CHAIN_FAILED" in out
    assert "chain exploded: no meanrev module" in out
    assert "NOTE:" in out


def test_chain_failed_exit_code_unchanged(sampled, monkeypatch, tmp_path, capsys):
    """Behaviour-preservation proof: passes before AND after the stdout fix."""
    def boom(cost_bp, shuffles, seed):
        raise RuntimeError("chain exploded")

    monkeypatch.setattr(fxs, "run_strategy_chain", boom)
    rc, _ = _run(_args(tmp_path), capsys)
    assert rc == 0


def test_chain_none_prints_not_run_line(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("TIINGO_API_KEY", "test-token")
    monkeypatch.setattr(fxs, "sample_loop", lambda *a, **k: {
        "samples": [], "poll_count": 1, "api_unreachable": False,
        "window_start_utc": "x", "window_end_utc": "y"})
    rc, out = _run(_args(tmp_path), capsys)

    assert rc == 0
    assert "strategy chain" in out
    assert "NOT RUN" in out
    assert "WARNING" not in out


def test_chain_success_prints_info_and_no_warning(sampled, monkeypatch, tmp_path, capsys):
    def ran(cost_bp, shuffles, seed):
        return {
            "state": "RAN",
            "module": "tools/fx_meanrev_research.py",
            "universe": "primary (dedup_55)",
            "seed": seed,
            "n_shuffles": shuffles,
            "cost_bp_round_trip": cost_bp,
            "break_even_bp_derived_from_run": 4.0,
            "break_even_bp_documented": 4.3038,
            "break_even_drift_bp": 4.0 - 4.3038,
            "cost_minus_break_even_bp": cost_bp - 4.0,
            "mean_gross_bp": 4.0,
            "mean_net_bp": 1.0,
            "mean_net_bp_2x": 1.0,
            "ci95_net_bp": [-1.0, 1.0],
            "ci95_net_bp_window_clustered": [-1.0, 1.0],
            "ci_window_clustered_includes_zero": True,
            "n_pair_rebalances": 10,
            "n_rebalance_windows": 5,
            "research_runner_verdict_at_cost": "WEAK",
            "research_runner_verdict_note": "context only",
        }

    monkeypatch.setattr(fxs, "run_strategy_chain", ran)
    rc, out = _run(_args(tmp_path), capsys)

    assert rc == 0
    assert "strategy chain: RAN" in out
    assert "WARNING" not in out
