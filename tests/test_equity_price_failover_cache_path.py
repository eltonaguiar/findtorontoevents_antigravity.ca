"""Defense-in-depth tests for _cache_path sanitization.

Per cross-AI review 2026-04-29, the original implementation only stripped
'/' from tickers — '..' and '\' survived. While ticker input is trusted
internal data today, harden the path sanitizer to prevent any future
caller from escaping CACHE_DIR via a malformed ticker.
"""
from __future__ import annotations
import os
import tempfile
from pathlib import Path

import pytest

# Force a tmpdir-rooted CACHE_DIR before importing the module under test
@pytest.fixture(autouse=True)
def _isolated_cache_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("EQUITY_QUOTE_CACHE_DIR", str(tmp_path))
    # Reload to pick up the env var
    import importlib
    import alpha_engine.equity_price_failover as m
    importlib.reload(m)
    yield tmp_path


def test_cache_path_normal_ticker():
    from alpha_engine.equity_price_failover import _cache_path, CACHE_DIR
    p = _cache_path("AAPL", "quote")
    assert p.parent == CACHE_DIR
    assert p.name == "AAPL.quote.json"


def test_cache_path_strips_slash():
    from alpha_engine.equity_price_failover import _cache_path, CACHE_DIR
    p = _cache_path("BRK/B", "quote")
    assert p.parent == CACHE_DIR
    assert "/" not in p.name
    assert "BRK_B" in p.name


def test_cache_path_blocks_dotdot():
    """`..` cannot escape CACHE_DIR — even if `.` survives as filename
    char, the parent must still be CACHE_DIR (no path traversal)."""
    from alpha_engine.equity_price_failover import _cache_path, CACHE_DIR
    p = _cache_path("..", "quote")
    # Resolve and check it's still under CACHE_DIR (no traversal)
    assert p.resolve().parent.resolve() == CACHE_DIR.resolve()


def test_cache_path_blocks_backslash():
    """Backslash cannot create subpaths even on Windows."""
    from alpha_engine.equity_price_failover import _cache_path, CACHE_DIR
    p = _cache_path("FOO\BAR", "quote")
    assert p.parent == CACHE_DIR
    assert "\\" not in p.name


def test_cache_path_blocks_path_traversal():
    """`../etc/passwd` style traversal — must stay in CACHE_DIR."""
    from alpha_engine.equity_price_failover import _cache_path, CACHE_DIR
    p = _cache_path("../../etc/passwd", "quote")
    assert p.resolve().parent.resolve() == CACHE_DIR.resolve()


def test_cache_path_keeps_dot_dash_underscore():
    """Common ticker conventions (BRK.B, BRK-B, BRK_B) preserved."""
    from alpha_engine.equity_price_failover import _cache_path
    assert "BRK.B" in _cache_path("BRK.B", "quote").stem or "BRK_B" in _cache_path("BRK.B", "quote").stem
    assert "BRK-B" in _cache_path("BRK-B", "quote").name
    assert "BRK_B" in _cache_path("BRK_B", "quote").name
