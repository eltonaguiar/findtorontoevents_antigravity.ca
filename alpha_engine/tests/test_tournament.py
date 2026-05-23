"""Tests for TournamentEngine — EMA demotion, per-regime tiers, promotion logic."""

import sys
import os
import pytest
import sqlite3
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _make_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def test_new_strategy_starts_as_challenger():
    from tournament_engine import TournamentEngine
    db = _make_db()
    try:
        te = TournamentEngine(db, "moderate")
        assert te.get_tier("new_strat") == "challenger"
    finally:
        os.unlink(db)


def test_promote_to_bronze():
    from tournament_engine import TournamentEngine
    db = _make_db()
    try:
        te = TournamentEngine(db, "moderate")
        for i in range(10):
            te.record_trade("s1", won=(i < 6), pnl_pct=(3.0 if i < 6 else -2.0))
        assert te.evaluate("s1") == "bronze"
    finally:
        os.unlink(db)


def test_ema_demotion_not_triggered_by_3_losses():
    """EMA smoothing should prevent demotion from just 3 consecutive losses."""
    from tournament_engine import TournamentEngine
    db = _make_db()
    try:
        te = TournamentEngine(db, "moderate")
        # Get to bronze
        for i in range(10):
            te.record_trade("s2", won=(i < 6), pnl_pct=(3.0 if i < 6 else -2.0))
        te.evaluate("s2")
        assert te.get_tier("s2") == "bronze"
        # 3 consecutive losses should NOT demote (EMA-based)
        for _ in range(3):
            te.record_trade("s2", won=False, pnl_pct=-2.0)
        te.evaluate("s2")
        assert te.get_tier("s2") == "bronze", "3 consecutive losses should not demote with EMA"
    finally:
        os.unlink(db)


def test_ema_demotion_triggered_by_sustained_poor():
    """Sustained poor performance should eventually demote."""
    from tournament_engine import TournamentEngine
    db = _make_db()
    try:
        te = TournamentEngine(db, "moderate")
        for i in range(10):
            te.record_trade("s3", won=(i < 6), pnl_pct=(3.0 if i < 6 else -2.0))
        te.evaluate("s3")
        # Many losses to drive EMA down + 5 consecutive bad evals
        for _ in range(20):
            te.record_trade("s3", won=False, pnl_pct=-2.0)
            te.evaluate("s3")
        assert te.get_tier("s3") == "challenger"
    finally:
        os.unlink(db)


def test_combo_id():
    from tournament_engine import TournamentEngine
    db = _make_db()
    try:
        te = TournamentEngine(db, "moderate")
        assert te.get_combo_id(["vol_a", "rsi_b"]) == "rsi_b+vol_a"
    finally:
        os.unlink(db)


def test_per_regime_tracking():
    from tournament_engine import TournamentEngine
    db = _make_db()
    try:
        te = TournamentEngine(db, "moderate")
        # Record good performance in trending
        for i in range(10):
            te.record_trade("s4", won=(i < 7), pnl_pct=(3.0 if i < 7 else -2.0), regime="trending")
        te.evaluate("s4", regime="trending")
        # Record bad performance in ranging
        for i in range(10):
            te.record_trade("s4", won=(i < 3), pnl_pct=(3.0 if i < 3 else -2.0), regime="ranging")
        te.evaluate("s4", regime="ranging")
        # Different tiers per regime
        assert te.get_tier("s4", regime="trending") == "bronze"
        assert te.get_tier("s4", regime="ranging") == "challenger"
    finally:
        os.unlink(db)


def test_risk_per_tier():
    from tournament_engine import TournamentEngine
    db = _make_db()
    try:
        te = TournamentEngine(db, "moderate")
        assert te.get_risk_pct("challenger") == 0.0
        assert te.get_risk_pct("bronze") == 0.005
        assert te.get_risk_pct("silver") == 0.01
        assert te.get_risk_pct("gold") == 0.02
    finally:
        os.unlink(db)


def test_get_state_returns_full_dict():
    from tournament_engine import TournamentEngine
    db = _make_db()
    try:
        te = TournamentEngine(db, "moderate")
        te.record_trade("s5", won=True, pnl_pct=2.5)
        state = te.get_state("s5")
        assert state["entity_id"] == "s5"
        assert state["total_trades"] == 1
        assert state["wins"] == 1
        assert state["tier"] == "challenger"
    finally:
        os.unlink(db)


def test_get_all_states():
    from tournament_engine import TournamentEngine
    db = _make_db()
    try:
        te = TournamentEngine(db, "moderate")
        te.record_trade("a1", won=True, pnl_pct=1.0)
        te.record_trade("a2", won=False, pnl_pct=-1.0)
        states = te.get_all_states()
        ids = {s["entity_id"] for s in states}
        assert "a1" in ids
        assert "a2" in ids
    finally:
        os.unlink(db)


def test_conservative_higher_threshold():
    """Conservative portfolio requires WR >= 60%, so 55% WR should NOT promote."""
    from tournament_engine import TournamentEngine
    db = _make_db()
    try:
        te = TournamentEngine(db, "conservative")
        # 55% win rate: 11 wins out of 20
        for i in range(20):
            te.record_trade("s6", won=(i < 11), pnl_pct=(3.0 if i < 11 else -2.0))
        result = te.evaluate("s6")
        # With EMA starting at 0.5, after 20 trades the EMA should be around the actual WR
        # but may not exceed 0.60 threshold for conservative
        assert result == "challenger", "55% WR should not promote in conservative portfolio"
    finally:
        os.unlink(db)
