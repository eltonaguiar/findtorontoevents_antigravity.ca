"""Tests for audit_trail.auto_rollback_triggers."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from audit_trail import auto_rollback_triggers as art


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_pick(
    *,
    pick_id: str,
    asset_class: str = "CRYPTO",
    pnl_pct: float = 0.0,
    closed_at: datetime | None = None,
    strategy: str = "dummy_strategy",
    source_system: str = "alpha_engine",
    status: str = "WON",
) -> dict:
    return {
        "id": pick_id,
        "symbol": "BTCUSDT",
        "asset_class": asset_class,
        "pnl_pct": pnl_pct,
        "closed_at": (closed_at or datetime.now(timezone.utc)).isoformat(),
        "strategy": strategy,
        "source_system": source_system,
        "status": status,
    }


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def fixture_paths(tmp_path: Path):
    paths = {
        "dashboard": tmp_path / "dashboard_data.json",
        "active": tmp_path / "active_picks.json",
        "whitelist": tmp_path / "core_whitelist.json",
    }
    return paths


# ---------------------------------------------------------------------------
# Trigger 1: banned_id_emit
# ---------------------------------------------------------------------------


def test_banned_id_fires_on_active_match(fixture_paths):
    p = fixture_paths
    now = datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc)

    _write(p["whitelist"], {"kill_list": ["banned_strategy", "ml_crypto_pred"]})
    _write(p["dashboard"], {
        "picks": {
            "active": [{
                "id": "x1",
                "strategy": "banned_strategy",
                "source_system": "alpha_engine",
                "asset_class": "CRYPTO",
            }],
            "active_raw": [],
            "recent_closed": [],
        }
    })
    _write(p["active"], [])

    triggers = art.check_rollback_conditions(
        dashboard_data_path=p["dashboard"],
        active_picks_path=p["active"],
        whitelist_path=p["whitelist"],
        now=now,
    )
    banned = [t for t in triggers if t["trigger"] == "banned_id_emit"]
    assert len(banned) == 1
    assert banned[0]["severity"] == "critical"
    assert banned[0]["details"]["bucket"] == "active"
    assert "banned_strategy" in banned[0]["details"]["matched_kill_entries"]


def test_banned_id_fires_on_active_raw_match(fixture_paths):
    p = fixture_paths
    now = datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc)
    _write(p["whitelist"], {"kill_list": ["alpha_engine::ml_crypto_pred"]})
    _write(p["dashboard"], {
        "picks": {
            "active": [],
            "active_raw": [{
                "id": "raw1",
                "strategy": "ml_crypto_pred",
                "source_system": "alpha_engine",
            }],
            "recent_closed": [],
        }
    })
    _write(p["active"], [])

    triggers = art.check_rollback_conditions(
        dashboard_data_path=p["dashboard"],
        active_picks_path=p["active"],
        whitelist_path=p["whitelist"],
        now=now,
    )
    banned = [t for t in triggers if t["trigger"] == "banned_id_emit"]
    assert len(banned) == 1
    assert banned[0]["details"]["bucket"] == "active_raw"


def test_banned_id_suppressed_when_auto_expired(fixture_paths):
    p = fixture_paths
    now = datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc)
    _write(p["whitelist"], {
        "kill_list": ["banned_strategy"],
        "kill_list_metadata": {"auto_expired": True},
    })
    _write(p["dashboard"], {
        "picks": {
            "active": [{"id": "x1", "strategy": "banned_strategy"}],
            "active_raw": [],
            "recent_closed": [],
        }
    })
    _write(p["active"], [])

    triggers = art.check_rollback_conditions(
        dashboard_data_path=p["dashboard"],
        active_picks_path=p["active"],
        whitelist_path=p["whitelist"],
        now=now,
    )
    assert not any(t["trigger"] == "banned_id_emit" for t in triggers)


def test_banned_id_no_match_no_trigger(fixture_paths):
    p = fixture_paths
    now = datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc)
    _write(p["whitelist"], {"kill_list": ["banned_strategy"]})
    _write(p["dashboard"], {
        "picks": {
            "active": [{"id": "x1", "strategy": "good_strategy"}],
            "active_raw": [],
            "recent_closed": [],
        }
    })
    _write(p["active"], [])

    triggers = art.check_rollback_conditions(
        dashboard_data_path=p["dashboard"],
        active_picks_path=p["active"],
        whitelist_path=p["whitelist"],
        now=now,
    )
    assert not any(t["trigger"] == "banned_id_emit" for t in triggers)


# ---------------------------------------------------------------------------
# Trigger 2: WR < 28% over 3d
# ---------------------------------------------------------------------------


def test_wr_below_28_fires(fixture_paths):
    p = fixture_paths
    now = datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc)
    # 25 trades over last 3d, only 5 winners -> 20% WR.
    rc = []
    for i in range(25):
        rc.append(_make_pick(
            pick_id=f"c-{i}",
            asset_class="CRYPTO",
            pnl_pct=1.0 if i < 5 else -1.0,
            closed_at=now - timedelta(hours=i),
        ))
    _write(p["dashboard"], {"picks": {"active": [], "active_raw": [], "recent_closed": rc}})
    _write(p["whitelist"], {"kill_list": []})
    _write(p["active"], [])

    triggers = art.check_rollback_conditions(
        asset_class="CRYPTO",
        window_days=3,
        dashboard_data_path=p["dashboard"],
        active_picks_path=p["active"],
        whitelist_path=p["whitelist"],
        now=now,
    )
    wr = [t for t in triggers if t["trigger"] == "wr_3d_below_28"]
    assert len(wr) == 1
    assert wr[0]["asset_class"] == "CRYPTO"
    assert wr[0]["wr_pct"] == 20.0
    assert wr[0]["n"] == 25


def test_wr_does_not_fire_below_min_n(fixture_paths):
    p = fixture_paths
    now = datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc)
    rc = [
        _make_pick(pick_id=f"c-{i}", pnl_pct=-1.0, closed_at=now - timedelta(hours=i))
        for i in range(10)  # below min n=20
    ]
    _write(p["dashboard"], {"picks": {"active": [], "active_raw": [], "recent_closed": rc}})
    _write(p["whitelist"], {"kill_list": []})
    _write(p["active"], [])

    triggers = art.check_rollback_conditions(
        dashboard_data_path=p["dashboard"],
        active_picks_path=p["active"],
        whitelist_path=p["whitelist"],
        now=now,
    )
    assert not any(t["trigger"] == "wr_3d_below_28" for t in triggers)


def test_wr_does_not_fire_above_threshold(fixture_paths):
    p = fixture_paths
    now = datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc)
    # 30 trades, 18 winners -> 60% WR
    rc = [
        _make_pick(
            pick_id=f"c-{i}",
            pnl_pct=1.0 if i < 18 else -1.0,
            closed_at=now - timedelta(hours=i),
        )
        for i in range(30)
    ]
    _write(p["dashboard"], {"picks": {"active": [], "active_raw": [], "recent_closed": rc}})
    _write(p["whitelist"], {"kill_list": []})
    _write(p["active"], [])

    triggers = art.check_rollback_conditions(
        dashboard_data_path=p["dashboard"],
        active_picks_path=p["active"],
        whitelist_path=p["whitelist"],
        now=now,
    )
    assert not any(t["trigger"] == "wr_3d_below_28" for t in triggers)


def test_wr_filters_by_window(fixture_paths):
    p = fixture_paths
    now = datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc)
    # Old picks (>3d) all losers; should be excluded.
    rc = [
        _make_pick(pick_id=f"old-{i}", pnl_pct=-1.0, closed_at=now - timedelta(days=10))
        for i in range(50)
    ]
    _write(p["dashboard"], {"picks": {"active": [], "active_raw": [], "recent_closed": rc}})
    _write(p["whitelist"], {"kill_list": []})
    _write(p["active"], [])

    triggers = art.check_rollback_conditions(
        window_days=3,
        dashboard_data_path=p["dashboard"],
        active_picks_path=p["active"],
        whitelist_path=p["whitelist"],
        now=now,
    )
    assert not any(t["trigger"] == "wr_3d_below_28" for t in triggers)


# ---------------------------------------------------------------------------
# Trigger 3: MDD breach
# ---------------------------------------------------------------------------


def test_compute_mdd_basic_curve():
    # Cumulative: 0 -> 10 -> 7 -> 12 -> 2 -> 5
    # Peaks: 10 -> 10 -> 12 -> 12 -> 12; MDD = 12 - 2 = 10.
    now = datetime(2026, 4, 29, tzinfo=timezone.utc)
    picks = []
    for i, pnl in enumerate([10.0, -3.0, 5.0, -10.0, 3.0]):
        picks.append(_make_pick(pick_id=f"c-{i}", pnl_pct=pnl,
                                closed_at=now + timedelta(minutes=i)))
    mdd = art.compute_mdd_pct(picks)
    assert mdd == pytest.approx(10.0, abs=1e-9)


def test_compute_mdd_no_drawdown():
    now = datetime(2026, 4, 29, tzinfo=timezone.utc)
    picks = [
        _make_pick(pick_id=f"c-{i}", pnl_pct=1.0, closed_at=now + timedelta(minutes=i))
        for i in range(10)
    ]
    assert art.compute_mdd_pct(picks) == 0.0


def test_mdd_trigger_fires_when_above_30(fixture_paths):
    p = fixture_paths
    now = datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc)
    # +20, +20, then -50 -> peak 40, trough -10, MDD 50.
    rc = [
        _make_pick(pick_id="c-1", pnl_pct=20.0, closed_at=now - timedelta(hours=3)),
        _make_pick(pick_id="c-2", pnl_pct=20.0, closed_at=now - timedelta(hours=2)),
        _make_pick(pick_id="c-3", pnl_pct=-50.0, closed_at=now - timedelta(hours=1)),
    ]
    _write(p["dashboard"], {"picks": {"active": [], "active_raw": [], "recent_closed": rc}})
    _write(p["whitelist"], {"kill_list": []})
    _write(p["active"], [])

    triggers = art.check_rollback_conditions(
        asset_class="CRYPTO",
        window_days=3,
        dashboard_data_path=p["dashboard"],
        active_picks_path=p["active"],
        whitelist_path=p["whitelist"],
        now=now,
    )
    mdd = [t for t in triggers if t["trigger"] == "mdd_breach"]
    assert len(mdd) == 1
    assert mdd[0]["asset_class"] == "CRYPTO"
    assert mdd[0]["threshold_pct"] == 30.0
    assert mdd[0]["mdd_pct"] >= 30.0


def test_mdd_trigger_does_not_fire_below_threshold(fixture_paths):
    p = fixture_paths
    now = datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc)
    # Tiny drawdown: peak 10, trough 0 -> MDD 10 (< 30).
    rc = [
        _make_pick(pick_id="c-1", pnl_pct=10.0, closed_at=now - timedelta(hours=2)),
        _make_pick(pick_id="c-2", pnl_pct=-10.0, closed_at=now - timedelta(hours=1)),
    ]
    _write(p["dashboard"], {"picks": {"active": [], "active_raw": [], "recent_closed": rc}})
    _write(p["whitelist"], {"kill_list": []})
    _write(p["active"], [])

    triggers = art.check_rollback_conditions(
        dashboard_data_path=p["dashboard"],
        active_picks_path=p["active"],
        whitelist_path=p["whitelist"],
        now=now,
    )
    assert not any(t["trigger"] == "mdd_breach" for t in triggers)


def test_mdd_filters_by_asset_class(fixture_paths):
    p = fixture_paths
    now = datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc)
    # CRYPTO has a 50% drawdown but FOREX is calm; checking FOREX must not fire.
    rc = [
        _make_pick(pick_id="c-1", asset_class="CRYPTO", pnl_pct=50.0,
                   closed_at=now - timedelta(hours=2)),
        _make_pick(pick_id="c-2", asset_class="CRYPTO", pnl_pct=-50.0,
                   closed_at=now - timedelta(hours=1)),
        _make_pick(pick_id="f-1", asset_class="FOREX", pnl_pct=0.5,
                   closed_at=now - timedelta(hours=1)),
    ]
    _write(p["dashboard"], {"picks": {"active": [], "active_raw": [], "recent_closed": rc}})
    _write(p["whitelist"], {"kill_list": []})
    _write(p["active"], [])

    triggers = art.check_rollback_conditions(
        asset_class="FOREX",
        dashboard_data_path=p["dashboard"],
        active_picks_path=p["active"],
        whitelist_path=p["whitelist"],
        now=now,
    )
    assert not any(t["trigger"] == "mdd_breach" for t in triggers)


def test_no_triggers_returns_empty_list(fixture_paths):
    p = fixture_paths
    now = datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc)
    _write(p["dashboard"], {"picks": {"active": [], "active_raw": [], "recent_closed": []}})
    _write(p["whitelist"], {"kill_list": []})
    _write(p["active"], [])

    triggers = art.check_rollback_conditions(
        dashboard_data_path=p["dashboard"],
        active_picks_path=p["active"],
        whitelist_path=p["whitelist"],
        now=now,
    )
    assert triggers == []


def test_threshold_constants_are_panel_corrected():
    # Pin the sentinel: tests will fail if someone reverts to the broken 195%.
    assert art.MDD_THRESHOLD_PCT == 30.0
    assert art.WR_3D_THRESHOLD_PCT == 28.0
    assert art.WR_3D_MIN_TRADES == 20


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
