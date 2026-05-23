"""Tests for PortfolioManager and Portfolio classes."""

import os
import sys
import tempfile
import time

import pytest

# Ensure alpha_engine is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from alpha_engine.portfolio_manager import (
    COOLDOWN_SECONDS,
    PORTFOLIO_CONFIGS,
    Portfolio,
    PortfolioManager,
)
from alpha_engine.tournament_engine import TournamentEngine


@pytest.fixture
def tmp_db(tmp_path):
    """Provide a temporary SQLite database path."""
    return str(tmp_path / "test_tournament.db")


@pytest.fixture
def manager(tmp_db):
    """Create a PortfolioManager with a temp DB."""
    return PortfolioManager(db_path=tmp_db)


# ---- Test: three independent portfolios -------------------------------------

def test_three_portfolios_independent(manager):
    """PortfolioManager creates exactly 3 portfolios with separate state."""
    assert len(manager.portfolios) == 3
    names = set(manager.portfolios.keys())
    assert names == {"conservative", "moderate", "aggressive"}

    # Each has its own tournament engine
    tournaments = [p.tournament for p in manager.portfolios.values()]
    assert len(set(id(t) for t in tournaments)) == 3

    # Each starts with its own config
    for name, portfolio in manager.portfolios.items():
        assert portfolio.config == PORTFOLIO_CONFIGS[name]
        assert portfolio.current_capital == 10_000.0


# ---- Test: conservative requires 3 families ---------------------------------

def test_conservative_requires_three_families(manager):
    """Conservative portfolio rejects signals with fewer than 3 families."""
    conservative = manager.portfolios["conservative"]

    assert not conservative.accepts_confluence(1)
    assert not conservative.accepts_confluence(2)
    assert conservative.accepts_confluence(3)
    assert conservative.accepts_confluence(4)


# ---- Test: circuit breaker freezes -------------------------------------------

def test_circuit_breaker_freezes(tmp_db):
    """5% drawdown freezes conservative portfolio."""
    tournament = TournamentEngine(db_path=tmp_db, portfolio="conservative")
    portfolio = Portfolio("conservative", PORTFOLIO_CONFIGS["conservative"], tournament)

    # Starting capital is 10,000. Lose $500 = 5% drawdown.
    portfolio.record_pnl(-500.0)

    assert portfolio.drawdown_pct == pytest.approx(0.05, abs=1e-6)
    assert portfolio.is_frozen()
    assert not portfolio.can_open_position("BTCUSDT", "BUY")


# ---- Test: position limits --------------------------------------------------

def test_position_limits(tmp_db):
    """max_positions is respected by can_open_position."""
    tournament = TournamentEngine(db_path=tmp_db, portfolio="aggressive")
    config = PORTFOLIO_CONFIGS["aggressive"]  # max_positions=30
    portfolio = Portfolio("aggressive", config, tournament)

    # Directly fill positions to max (bypass can_open_position to avoid
    # direction limit interference -- we test direction limits separately)
    for i in range(config["max_positions"]):
        direction = ["BUY", "SELL", "SHORT", "LONG"][i % 4]
        portfolio.open_position(f"SYM{i}", direction)

    assert len(portfolio._positions) == config["max_positions"]
    # Next one should be rejected
    assert not portfolio.can_open_position("SYM_EXTRA", "BUY")


def test_max_per_symbol(tmp_db):
    """max_per_symbol limit is enforced."""
    tournament = TournamentEngine(db_path=tmp_db, portfolio="moderate")
    config = PORTFOLIO_CONFIGS["moderate"]  # max_per_symbol=2
    portfolio = Portfolio("moderate", config, tournament)

    portfolio.open_position("BTCUSDT", "BUY")
    assert portfolio.can_open_position("BTCUSDT", "BUY")
    portfolio.open_position("BTCUSDT", "BUY")
    assert not portfolio.can_open_position("BTCUSDT", "BUY")

    # Different symbol is still fine
    assert portfolio.can_open_position("ETHUSDT", "BUY")


def test_max_same_direction(tmp_db):
    """max_same_direction limit is enforced."""
    tournament = TournamentEngine(db_path=tmp_db, portfolio="conservative")
    config = PORTFOLIO_CONFIGS["conservative"]  # max_same_direction=4
    portfolio = Portfolio("conservative", config, tournament)

    for i in range(4):
        portfolio.open_position(f"SYM{i}", "BUY")

    # 5th BUY rejected
    assert not portfolio.can_open_position("SYM4", "BUY")
    # SELL direction still fine
    assert portfolio.can_open_position("SYM4", "SELL")


# ---- Test: route_signal filters by family_count -----------------------------

def test_route_signal_filters_by_family_count(manager):
    """2-family signal accepted by moderate/aggressive, rejected by conservative."""
    signal = {"family_count": 2, "symbol": "BTCUSDT", "direction": "BUY"}

    routed = manager.route_signal(signal)
    names = [name for name, _ in routed]

    assert "conservative" not in names
    assert "moderate" in names
    assert "aggressive" in names


def test_route_signal_three_families(manager):
    """3-family signal accepted by all portfolios."""
    signal = {"family_count": 3}
    routed = manager.route_signal(signal)
    names = [name for name, _ in routed]
    assert set(names) == {"conservative", "moderate", "aggressive"}


# ---- Test: graduated recovery ------------------------------------------------

def test_graduated_recovery(tmp_db):
    """After 24h cooldown, portfolio enters half_size_mode."""
    tournament = TournamentEngine(db_path=tmp_db, portfolio="moderate")
    config = PORTFOLIO_CONFIGS["moderate"]  # circuit_breaker_pct=0.10
    portfolio = Portfolio("moderate", config, tournament)

    # Trigger freeze via drawdown
    portfolio.record_pnl(-1000.0)  # 10% drawdown on 10k
    freeze_time = time.time() - COOLDOWN_SECONDS - 1  # simulate 24h+ ago
    portfolio.freeze(now=freeze_time)

    # Reset PnL above circuit breaker so drawdown check passes
    # (add back enough so drawdown < 10%)
    portfolio.record_pnl(600.0)  # now at -400, 4% drawdown

    # Check: after 24h should be unfrozen but in half_size_mode
    assert not portfolio.is_frozen()
    assert portfolio.half_size_mode


def test_hard_freeze_after_two_freezes(tmp_db):
    """Two freezes within 30 days triggers hard freeze."""
    tournament = TournamentEngine(db_path=tmp_db, portfolio="aggressive")
    config = PORTFOLIO_CONFIGS["aggressive"]
    portfolio = Portfolio("aggressive", config, tournament)

    now = time.time()
    portfolio.freeze(now=now - 86400)  # 1 day ago
    portfolio.freeze(now=now)           # now

    assert portfolio._hard_frozen
    assert portfolio.is_frozen()

    # Hard freeze means manual review -- even after recovery it stays frozen
    portfolio._pnl = 5000.0  # big profit, no drawdown
    assert portfolio.is_frozen()


# ---- Test: comparison snapshot -----------------------------------------------

def test_get_comparison(manager):
    """get_comparison returns dict with all 3 portfolio snapshots."""
    comparison = manager.get_comparison()
    assert set(comparison.keys()) == {"conservative", "moderate", "aggressive"}

    for name, snap in comparison.items():
        assert snap["name"] == name
        assert snap["current_capital"] == 10_000.0
        assert snap["frozen"] is False
        assert "drawdown_pct" in snap
        assert "half_size_mode" in snap


# ---- Test: P&L tracking -----------------------------------------------------

def test_record_pnl_updates_capital(tmp_db):
    """record_pnl correctly updates current_capital and peak."""
    tournament = TournamentEngine(db_path=tmp_db, portfolio="moderate")
    portfolio = Portfolio("moderate", PORTFOLIO_CONFIGS["moderate"], tournament)

    portfolio.record_pnl(500.0)
    assert portfolio.current_capital == 10_500.0

    portfolio.record_pnl(-200.0)
    assert portfolio.current_capital == 10_300.0
    assert portfolio.drawdown_pct == pytest.approx(200.0 / 10_500.0, abs=1e-6)
