"""Regression tests for WIN_RATE_TRAP_BLACKLIST added to quality_gates 2026-05-09.

xai swarm blind spot from swarm_runs/next_steps_perf_2026-05-09/inception.json.raw.txt:
"the WR/PnL divergence on equity is the same pattern as ETHUSDT — small wins,
catastrophic losses". DB drilldown confirmed: 6 crypto symbols + 2 equity
symbols all show WR>=50% (or low-WR for NIO/BCH) with negative sum_pnl over
90d at n>=10 sample.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audit_trail.quality_gates import WIN_RATE_TRAP_BLACKLIST


def test_dydxusdt_blocked():
    """70.1% WR but PF<0.1 — worst trap. n=67, sum -21.6%."""
    assert "DYDXUSDT" in WIN_RATE_TRAP_BLACKLIST


def test_ethusdt_blocked():
    """51.5% WR / sum -37.2% — biggest sum loss. n=68."""
    assert "ETHUSDT" in WIN_RATE_TRAP_BLACKLIST


def test_injusdt_blocked():
    assert "INJUSDT" in WIN_RATE_TRAP_BLACKLIST


def test_fetusdt_blocked():
    assert "FETUSDT" in WIN_RATE_TRAP_BLACKLIST


def test_strkusdt_blocked():
    """69% WR but +0.01% avg win — wins are tiny."""
    assert "STRKUSDT" in WIN_RATE_TRAP_BLACKLIST


def test_etcusdt_blocked():
    assert "ETCUSDT" in WIN_RATE_TRAP_BLACKLIST


def test_nio_equity_blocked():
    """Real equity bleed: n=11 WR 27% sum -48.9%. Not a trap, just a loser."""
    assert "NIO" in WIN_RATE_TRAP_BLACKLIST


def test_bch_usd_blocked():
    """Yahoo-style BCH-USD: n=4 sum -17.3%. Complements PR #884."""
    assert "BCH-USD" in WIN_RATE_TRAP_BLACKLIST


def test_blacklist_is_frozenset():
    """Immutability — prevents accidental runtime mutation."""
    assert isinstance(WIN_RATE_TRAP_BLACKLIST, frozenset)


def test_blacklist_size_is_8():
    """Sanity: should have exactly 8 entries (6 crypto traps + 2 equity)."""
    assert len(WIN_RATE_TRAP_BLACKLIST) == 8


def test_winners_NOT_blocked():
    """Top 30d winners must NOT be in the trap list (sanity check vs PR #862 Q2)."""
    for sym in ("BTCUSDT", "JUPUSDT", "SOLUSDT", "ENAUSDT", "RENDERUSDT",
                "WIFUSDT", "XRPUSDT", "ADAUSDT", "NEARUSDT", "STXUSDT"):
        assert sym not in WIN_RATE_TRAP_BLACKLIST, f"{sym} is a top winner — must not be blocked"
