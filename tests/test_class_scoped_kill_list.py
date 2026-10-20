"""Tests for the 2026-10-20 operator kill-list class-scoped block (mutation-before-kill approved)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.strategy_blocklist import (
    _class_scoped_pair_is_blocked,
    _CLASS_SCOPED_BLOCKED_PAIRS,
    is_blocked_pick,
    is_blocked_strategy,
    pick_block_reason,
)


def _mk(strategy: str, asset_class: str = "CRYPTO", source_system: str = "") -> dict:
    return {"strategy": strategy, "asset_class": asset_class, "source_system": source_system}


def test_luxalgo_confluence_frozen_paper_only():
    # Operator FREEZE: re-added to _PAPER_ONLY_STRATEGIES.
    assert is_blocked_strategy("luxalgo_confluence") is True
    assert pick_block_reason(_mk("luxalgo_confluence")) == "paper-only"


def test_etf_rs_breakout_scout_kept():
    # Explicit operator exception — must survive the class-scoped kill.
    assert _class_scoped_pair_is_blocked("ETF", "rs-breakout-scout") is False
    assert is_blocked_pick(_mk("rs-breakout-scout", "ETF")) is False


def test_bond_rs_breakout_scout_killed():
    # Same strategy name killed in BOND while surviving in ETF -> proves class-scoping.
    assert is_blocked_pick(_mk("rs-breakout-scout", "BOND")) is True
    assert pick_block_reason(_mk("rs-breakout-scout", "BOND")) == "retired-class-scoped"


def test_equity_adx_trend_scout_killed():
    assert is_blocked_pick(_mk("adx-trend-scout", "EQUITY")) is True


def test_etf_adx_trend_scout_killed():
    assert is_blocked_pick(_mk("adx-trend-scout", "ETF")) is True


def test_multi_asset_copytrader_forex_killed():
    assert is_blocked_pick(_mk("multi_asset_copytrader", "FOREX")) is True


def test_futures_cross_asset_momentum_killed():
    assert is_blocked_pick(_mk("futures_cross_asset_momentum", "FUTURES")) is True


def test_class_scoped_case_insensitive():
    assert _class_scoped_pair_is_blocked("etf", "ADX-Trend-Scout") is True


def test_unlisted_pair_not_killed():
    assert is_blocked_pick(_mk("some-unlisted-strategy", "CRYPTO")) is False


def test_kill_list_population_counts():
    # BANNED(5) + n>=30&PF<1(7) + BOND(12) + FUTURES(2) + ETF(30) = 56 pairs
    assert len(_CLASS_SCOPED_BLOCKED_PAIRS) == 56
