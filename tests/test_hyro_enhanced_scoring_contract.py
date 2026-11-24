"""Exit-code / stderr contract tests for alpha_engine.hyrotrader_enhanced_scoring.

Finding (2026-11-16): audit-dashboard's `hyro_enhanced_scoring` sub-step fails
loudly-but-mysteriously (raw traceback) in the env/secrets-delta class — when
the upstream `tools/hyro_quan_bridge.py` soft-fails, its output
`audit_dashboard/data/hyrotrader_picks.json` is missing/stale and this runner
crashed with an unhandled FileNotFoundError and no workflow-gateable signal.
The script now has an explicit contract:

  exit 0 = completed (per-pick issues remain warnings)
  exit 2 = env/secrets/input-delta class failure, with a clean ::error::
           annotation on stderr naming the missing upstream output
  unexpected crash = ::error:: annotation + re-raise (traceback preserved)

Zero input picks is LOUD-but-nonfatal (::warning::, exit 0).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha_engine import hyrotrader_enhanced_scoring as hyro


@pytest.fixture
def isolated_paths(monkeypatch, tmp_path):
    picks = tmp_path / "hyrotrader_picks.json"
    out = tmp_path / "hyrotrader_enhanced_picks.json"
    ml = tmp_path / "hyro_ml_pick_rankings.json"
    monkeypatch.setattr(hyro, "_PICKS_PATH", picks)
    monkeypatch.setattr(hyro, "_OUTPUT_PATH", out)
    monkeypatch.setattr(hyro, "_ML_RANKINGS_PATH", ml)
    return picks, out, ml


def test_missing_input_exits_2_with_error_annotation(isolated_paths, capsys):
    picks, _out, _ml = isolated_paths
    assert not picks.exists()
    rc = hyro._run_cli()
    err = capsys.readouterr().err
    assert rc == 2
    assert "::error::" in err
    assert "hyrotrader_picks.json" in err
    assert "hyro_quan_bridge" in err


def test_corrupt_input_exits_2_with_error_annotation(isolated_paths, capsys):
    picks, _out, _ml = isolated_paths
    picks.write_text("{not valid json", encoding="utf-8")
    rc = hyro._run_cli()
    err = capsys.readouterr().err
    assert rc == 2
    assert "::error::" in err
    assert "env/input class" in err


def test_zero_picks_is_loud_but_nonfatal(isolated_paths, capsys):
    picks, out, _ml = isolated_paths
    picks.write_text(json.dumps({"picks": []}), encoding="utf-8")
    rc = hyro._run_cli()
    captured = capsys.readouterr()
    assert rc == 0
    assert "::warning::" in captured.out
    assert "0 input picks" in captured.out
    assert "::error::" not in captured.err
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["picks"] == []


def test_unexpected_crash_annotates_and_reraises(monkeypatch, capsys):
    def _boom():
        raise ValueError("simulated explosion")

    monkeypatch.setattr(hyro, "main", _boom)
    with pytest.raises(ValueError):
        hyro._run_cli()
    err = capsys.readouterr().err
    assert "::error::" in err
    assert "unexpected" in err
