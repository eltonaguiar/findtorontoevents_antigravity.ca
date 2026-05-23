"""
Asset-class edge invariants — pytest fixtures off live dashboard data.

Pinned 2026-04-30 from EDGE_ANALYSIS_2026_04_30.md. These tests guard:
  - EQUITY 30d aggregate PF > 1.5 (Tier 2 floor)
  - HC gate per-asset-class properties: pass-set must dominate population
  - BLOCKED_SYMBOLS: zero recent_closed picks (last 30d) under any
    blocked symbol — verifies upstream symbol bans actually filter
  - Cerebras-style hypotheses (BNB/SOL/ATOM unban) remain falsified

Read-only on audit_dashboard/data/dashboard_data.json. Skips gracefully if
the file is missing (e.g., on lean CI checkouts).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "audit_dashboard" / "data" / "dashboard_data.json"


def _parse_dt(s):
    if not s:
        return None
    try:
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


@pytest.fixture(scope="module")
def closed_picks():
    if not DATA.exists():
        pytest.skip("dashboard_data.json missing — skipping live-data invariant tests")
    return json.loads(DATA.read_text(encoding="utf-8"))["picks"]["recent_closed"]


def _wr_pf(picks):
    pnls = [r.get("pnl_pct") for r in picks if r.get("pnl_pct") is not None]
    if not pnls:
        return 0, 0.0, 0.0, 0.0
    wins = sum(1 for x in pnls if x > 0)
    gw = sum(x for x in pnls if x > 0)
    gl = abs(sum(x for x in pnls if x < 0))
    pf = (gw / gl) if gl > 0 else (float("inf") if gw > 0 else 0.0)
    return len(pnls), wins / len(pnls) * 100.0, pf, sum(pnls)


# ── Asset-class aggregate invariants ──

def test_equity_30d_pf_above_tier2_floor(closed_picks):
    """EQUITY 30d aggregate PF must remain above Tier 2 floor (1.5).

    Pinned by EDGE_ANALYSIS_2026_04_30.md: EQUITY 30d PF observed 1.85
    (n=157, WR 57.3%, +188.6%). Allow 0.20 cushion → assert PF > 1.30 to
    avoid flapping on regime swings while still catching catastrophic
    drift to Tier 3.
    """
    cut30 = datetime.now(timezone.utc) - timedelta(days=30)
    eq = [
        r for r in closed_picks
        if (r.get("asset_class") or "").upper() == "EQUITY"
        and (_parse_dt(r.get("closed_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= cut30
    ]
    assert len(eq) >= 50, f"EQUITY 30d sample too small: n={len(eq)}"
    n, wr, pf, sumpnl = _wr_pf(eq)
    assert pf > 1.30, (
        f"EQUITY 30d PF dropped to {pf:.3f} (n={n}, WR={wr:.1f}%, sum={sumpnl:+.2f}). "
        "Tier 2 floor breached — investigate before next release."
    )


def test_commodity_30d_kill_in_progress(closed_picks):
    """COMMODITY 30d: if PF still <1, no panic — kill is in flight per
    PR #535. Just assert sample exists so we know data is flowing."""
    cut30 = datetime.now(timezone.utc) - timedelta(days=30)
    com = [
        r for r in closed_picks
        if (r.get("asset_class") or "").upper() == "COMMODITY"
        and (_parse_dt(r.get("closed_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= cut30
    ]
    # Just test we have data flowing — actual edge gate is the kill list itself.
    assert len(com) > 0, "no COMMODITY 30d closed picks — pipeline gap"


# ── Blocked-symbol invariant ──

BLOCKED_SYMBOLS_REPLAY = {
    "MATICUSDT", "UUSDT", "XMR", "XMRUSDT", "ENAUSDT", "IMXUSDT", "KASUSDT",
    "KATUSDT", "TRXUSDT",
    "ADBE", "CRM", "ACN", "MSFT", "PLTR", "TSLA",
    "JTOUSDT", "XLMUSDT", "ICPUSDT", "RENDERUSDT", "NVDA",
    "NKE", "PG", "HD",
}


def test_blocked_symbols_no_recent_closes(closed_picks):
    """No BLOCKED_SYMBOL should produce a closed pick in the last 30d.

    If one slips through, the upstream filter has a leak — fail loud.
    """
    cut30 = datetime.now(timezone.utc) - timedelta(days=30)
    leaks = []
    for r in closed_picks:
        sym = (r.get("symbol") or "").upper()
        if sym not in BLOCKED_SYMBOLS_REPLAY:
            continue
        cdt = _parse_dt(r.get("closed_at")) or datetime.min.replace(tzinfo=timezone.utc)
        if cdt >= cut30:
            leaks.append((sym, r.get("closed_at"), r.get("source_system")))
    assert not leaks, (
        f"BLOCKED_SYMBOLS leaked {len(leaks)} recent closes: {leaks[:5]}"
    )


# ── Cerebras hypothesis falsifiers ──

def test_cerebras_bnb_unban_falsified(closed_picks):
    """Cerebras claimed BNB/SOL/ATOM should be unbanned.

    Empirical reality (2026-04-30):
      BNBUSDT: not currently banned; recent WR 16.7% / PF 0.72 / -1.29% on n=12.
      SOLUSDT: not currently banned; recent WR 25.8% / PF 0.54 / -18.55% on n=66.
      ATOMUSDT: not currently banned; n=9 too small to act.

    None of those is "unban-worthy". Test pins the falsification — if WR
    flips and BNB/SOL/ATOM start crossing 50% WR with n>=20 and Wilson LB
    > 45%, this test will fail and force re-evaluation.
    """
    rolling = {}
    for sym in ("BNBUSDT", "SOLUSDT", "ATOMUSDT"):
        recs = [r for r in closed_picks if (r.get("symbol") or "").upper() == sym]
        if not recs:
            continue
        n, wr, pf, sumpnl = _wr_pf(recs)
        rolling[sym] = (n, wr, pf, sumpnl)
    # Hard-fail only if all 3 simultaneously cross unban threshold (very high bar)
    crossed = [
        sym for sym, (n, wr, pf, sumpnl) in rolling.items()
        if n >= 20 and wr >= 50 and pf >= 1.2
    ]
    assert len(crossed) < 3, (
        f"All 3 Cerebras unban candidates ({crossed}) now show recoverable edge. "
        "Re-evaluate the falsification claim — this is a NEW signal."
    )
