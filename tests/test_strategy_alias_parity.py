"""Tests for tools/validate_strategy_alias_parity.py."""

import pytest

from tools.validate_strategy_alias_parity import (
    _parse_js_alias_body,
    compare_maps,
    extract_js_leaderboard_aliases,
)


def test_parse_js_alias_body_simple():
    body = """
  mean_reversion_bb: 'MeanReversionBB',
  // comment
  connors_rsi2: 'connors_rsi2_scanner',
"""
    assert _parse_js_alias_body(body) == {
        "mean_reversion_bb": "MeanReversionBB",
        "connors_rsi2": "connors_rsi2_scanner",
    }


def test_compare_maps_detects_mismatch():
    ok, errs = compare_maps({"a": "X"}, {"a": "Y"})
    assert not ok
    assert any("mismatch" in e for e in errs)


def test_template_matches_config(repo_root):
    """Integration: live template.html must match STRATEGY_TRACK_ALIASES."""
    template = repo_root / "audit_dashboard" / "template.html"
    if not template.is_file():
        pytest.skip("template.html not present")
    html = template.read_text(encoding="utf-8", errors="replace")
    js_map = extract_js_leaderboard_aliases(html)
    from alpha_engine.config import STRATEGY_TRACK_ALIASES

    ok, errs = compare_maps(dict(STRATEGY_TRACK_ALIASES), js_map)
    assert ok, "\n".join(errs)


def test_index_leaderboard_matches_template(repo_root):
    """Built index.html must not drift from template on LEADERBOARD_STRATEGY_ALIASES."""
    template = repo_root / "audit_dashboard" / "template.html"
    index = repo_root / "audit_dashboard" / "index.html"
    if not template.is_file() or not index.is_file():
        pytest.skip("template or index not present")
    tmap = extract_js_leaderboard_aliases(
        template.read_text(encoding="utf-8", errors="replace")
    )
    imap = extract_js_leaderboard_aliases(
        index.read_text(encoding="utf-8", errors="replace")
    )
    ok, errs = compare_maps(tmap, imap)
    assert ok, "\n".join(errs)


@pytest.fixture
def repo_root():
    import pathlib

    return pathlib.Path(__file__).resolve().parents[1]
