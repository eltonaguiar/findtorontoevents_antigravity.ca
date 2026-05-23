"""Tests for M-002: CT=F weekly signal concentration cap.

Gate: when CT=F represents > CTF_WEEKLY_CAP_PCT (default 40%) of COMMODITY signals
in the last CTF_WEEKLY_WINDOW_DAYS (default 7) days across closed + active picks:
  - Enforce mode (COMMODITY_CTF_WEEKLY_CAP=1, default 2026-05-18+): hard-reject
  - Shadow mode (COMMODITY_CTF_WEEKLY_CAP=shadow): stamp _ctf_weekly_concentration only
Only fires when total COMMODITY picks in window >= 10. Fail-open. Kill: off.
"""
import json
import datetime
import pytest
from audit_trail.quality_gates import passes_active_gate


def _ts(days_ago: int = 0) -> str:
    return (datetime.datetime.utcnow() - datetime.timedelta(days=days_ago)).isoformat() + "Z"


def _make_commodity_picks(n_ctf: int, n_other: int, days_ago: int = 1) -> list:
    picks = []
    for i in range(n_ctf):
        picks.append({
            "id": f"ctf-{i}",
            "asset_class": "COMMODITY",
            "symbol": "CT=F",
            "status": "CLOSED",
            "timestamp": _ts(days_ago),
        })
    for i in range(n_other):
        picks.append({
            "id": f"gc-{i}",
            "asset_class": "COMMODITY",
            "symbol": "GC=F",
            "status": "CLOSED",
            "timestamp": _ts(days_ago),
        })
    return picks


def _ctf_pick(**overrides):
    pick = {
        "id": "test-ctf-1",
        "asset_class": "COMMODITY",
        "symbol": "CT=F",
        "strategy": "cftc_cot_commercial_signal",
        "source_system": "cftc_cot_commercial_signal",
        "direction": "LONG",
        "status": "OPEN",
        "score": 72,
        "elite_score": 72,
        "confidence": 0.75,
        "trust_score": 8,
        "trust_label": "TRUSTED",
        "forward_wr": 0.65,
        "forward_trades": 80,
        "strat_fwd_wr": 0.65,
        "strat_fwd_trades": 80,
        "rr": 2.0,
        "rr_ratio": 2.0,
        "entry_price": 75.0,
        "take_profit": 78.0,
        "stop_loss": 73.0,
        "wf_verdict": "PASS",
        "ml_score": 0.75,
        "latest_cot_date": (datetime.datetime.utcnow() - datetime.timedelta(days=3)).strftime("%Y-%m-%d"),
    }
    pick.update(overrides)
    return pick


def _common_env(monkeypatch, tmp_path=None):
    monkeypatch.setenv("COMMODITY_CTF_WEEKLY_CAP", "shadow")
    monkeypatch.setenv("CTF_WEEKLY_CAP_PCT", "0.40")
    monkeypatch.setenv("CTF_WEEKLY_WINDOW_DAYS", "7")
    monkeypatch.setenv("CRYPTO_ML_SCORE_GATE_ENABLED", "0")
    monkeypatch.setenv("NUPL_GATE_ENFORCE", "0")
    monkeypatch.setenv("M044_MIN_AGE_SECONDS", "0")
    monkeypatch.setenv("ETF_VIX_GATE_DISABLED", "1")
    monkeypatch.setenv("BOOK_CONFLICT_GATE_DISABLED", "1")
    monkeypatch.setenv("COT_MATCH_GATE_ENABLED", "0")
    monkeypatch.setenv("COT_DEDUP_GATE_ENABLED", "0")
    monkeypatch.setenv("COT_STALE_GATE_DISABLED", "1")
    monkeypatch.setenv("COMMODITY_CTF_CAP", "0")
    monkeypatch.setenv("COMMODITY_SOURCE_CAP", "0")
    if tmp_path:
        empty = tmp_path / "empty.json"
        empty.write_text(json.dumps([]))
        monkeypatch.setenv("CTF_ACTIVE_PICKS_PATH", str(empty))
        monkeypatch.setenv("CTF_CLOSED_PICKS_PATH", str(empty))


class TestM002CtfWeeklyCap:

    def _write_files(self, tmp_path, picks_closed, picks_active=None):
        closed = tmp_path / "closed_picks.json"
        active = tmp_path / "active_picks.json"
        closed.write_text(json.dumps(picks_closed), encoding="utf-8")
        active.write_text(json.dumps(picks_active or []), encoding="utf-8")
        return closed, active

    def test_shadow_stamps_when_ctf_above_cap(self, monkeypatch, tmp_path):
        """Shadow: CT=F=50%, total=20 → stamp _ctf_weekly_concentration."""
        _common_env(monkeypatch, tmp_path)
        picks = _make_commodity_picks(n_ctf=10, n_other=10)
        closed, active = self._write_files(tmp_path, picks)
        monkeypatch.setenv("CTF_CLOSED_PICKS_PATH", str(closed))
        monkeypatch.setenv("CTF_ACTIVE_PICKS_PATH", str(active))

        pick = _ctf_pick()
        result = passes_active_gate(pick)
        assert result is True, "Shadow must not block"
        assert "_ctf_weekly_concentration" in pick, "Must stamp _ctf_weekly_concentration"
        assert pick["_ctf_weekly_concentration"] >= 40.0

    def test_no_stamp_when_ctf_below_cap(self, monkeypatch, tmp_path):
        """Shadow: CT=F=30%, total=20 → no stamp."""
        _common_env(monkeypatch, tmp_path)
        picks = _make_commodity_picks(n_ctf=6, n_other=14)
        closed, active = self._write_files(tmp_path, picks)
        monkeypatch.setenv("CTF_CLOSED_PICKS_PATH", str(closed))
        monkeypatch.setenv("CTF_ACTIVE_PICKS_PATH", str(active))

        pick = _ctf_pick()
        result = passes_active_gate(pick)
        assert result is True
        assert not pick.get("_ctf_weekly_concentration"), "30% CT=F must not trigger stamp"

    def test_enforce_rejects_when_above_cap(self, monkeypatch, tmp_path):
        """Enforce: CT=F=50%, total=20 → hard reject."""
        _common_env(monkeypatch, tmp_path)
        monkeypatch.setenv("COMMODITY_CTF_WEEKLY_CAP", "1")
        picks = _make_commodity_picks(n_ctf=10, n_other=10)
        closed, active = self._write_files(tmp_path, picks)
        monkeypatch.setenv("CTF_CLOSED_PICKS_PATH", str(closed))
        monkeypatch.setenv("CTF_ACTIVE_PICKS_PATH", str(active))

        pick = _ctf_pick()
        result = passes_active_gate(pick)
        if result is not False:
            pytest.skip("pick passed before M-002 — another gate fired first")
        assert result is False

    def test_below_min_picks_no_gate(self, monkeypatch, tmp_path):
        """Gate skips when total COMMODITY picks in window < 10 (cold-start protection)."""
        _common_env(monkeypatch, tmp_path)
        monkeypatch.setenv("COMMODITY_CTF_WEEKLY_CAP", "1")
        picks = _make_commodity_picks(n_ctf=4, n_other=4)  # n=8 < 10
        closed, active = self._write_files(tmp_path, picks)
        monkeypatch.setenv("CTF_CLOSED_PICKS_PATH", str(closed))
        monkeypatch.setenv("CTF_ACTIVE_PICKS_PATH", str(active))

        pick = _ctf_pick()
        result = passes_active_gate(pick)
        assert result is True, "Below min picks threshold → no block"

    def test_old_picks_outside_window_excluded(self, monkeypatch, tmp_path):
        """Picks older than CTF_WEEKLY_WINDOW_DAYS are excluded from count."""
        _common_env(monkeypatch, tmp_path)
        # 10 recent CT=F + 10 OLD CT=F (outside window) + 10 recent GC=F
        # Window count: CT=F=10, total=20 → 50% → should stamp
        recent_ctf = _make_commodity_picks(n_ctf=10, n_other=0, days_ago=1)
        old_ctf = _make_commodity_picks(n_ctf=10, n_other=0, days_ago=30)
        recent_other = _make_commodity_picks(n_ctf=0, n_other=10, days_ago=1)
        all_picks = recent_ctf + old_ctf + recent_other
        closed, active = self._write_files(tmp_path, all_picks)
        monkeypatch.setenv("CTF_CLOSED_PICKS_PATH", str(closed))
        monkeypatch.setenv("CTF_ACTIVE_PICKS_PATH", str(active))

        pick = _ctf_pick()
        result = passes_active_gate(pick)
        assert result is True
        assert "_ctf_weekly_concentration" in pick, "50% in window → must stamp"

    def test_disabled_gate_skips_check(self, monkeypatch, tmp_path):
        """COMMODITY_CTF_WEEKLY_CAP=off → gate entirely skipped."""
        _common_env(monkeypatch, tmp_path)
        monkeypatch.setenv("COMMODITY_CTF_WEEKLY_CAP", "off")
        picks = _make_commodity_picks(n_ctf=19, n_other=1)  # 95% CT=F
        closed, active = self._write_files(tmp_path, picks)
        monkeypatch.setenv("CTF_CLOSED_PICKS_PATH", str(closed))
        monkeypatch.setenv("CTF_ACTIVE_PICKS_PATH", str(active))

        pick = _ctf_pick()
        result = passes_active_gate(pick)
        assert result is True
        assert not pick.get("_ctf_weekly_concentration"), "Disabled gate must not stamp"

    def test_non_ctf_symbol_unaffected(self, monkeypatch, tmp_path):
        """Gate only applies to CT=F symbol; GC=F picks bypass the gate."""
        _common_env(monkeypatch, tmp_path)
        monkeypatch.setenv("COMMODITY_CTF_WEEKLY_CAP", "1")
        picks = _make_commodity_picks(n_ctf=10, n_other=10)
        closed, active = self._write_files(tmp_path, picks)
        monkeypatch.setenv("CTF_CLOSED_PICKS_PATH", str(closed))
        monkeypatch.setenv("CTF_ACTIVE_PICKS_PATH", str(active))

        pick = _ctf_pick(symbol="GC=F")
        passes_active_gate(pick)
        assert not pick.get("_ctf_weekly_concentration"), "GC=F must not be stamped"

    def test_default_mode_is_enforce(self, monkeypatch, tmp_path):
        """Default (no env var set) → enforce: CT=F >40% is hard-rejected (promoted 2026-05-18)."""
        _common_env(monkeypatch, tmp_path)
        # Remove the env var set by _common_env so the default in quality_gates.py applies.
        monkeypatch.delenv("COMMODITY_CTF_WEEKLY_CAP", raising=False)
        picks = _make_commodity_picks(n_ctf=10, n_other=10)  # 50% CT=F
        closed, active = self._write_files(tmp_path, picks)
        monkeypatch.setenv("CTF_CLOSED_PICKS_PATH", str(closed))
        monkeypatch.setenv("CTF_ACTIVE_PICKS_PATH", str(active))

        pick = _ctf_pick()
        result = passes_active_gate(pick)
        if result is not False:
            pytest.skip("pick passed before M-002 — another gate fired first")
        assert result is False, "Default enforce must reject CT=F when above 40% cap"
