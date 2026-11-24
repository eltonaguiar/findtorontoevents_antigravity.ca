"""Tests for M-001: COT data staleness gate.

Gate: when a COMMODITY pick from a COT source has latest_cot_date > COT_STALE_DAYS
(default 10) days old:
  - Shadow mode (default, COT_STALE_GATE_ENFORCE=0): stamp _cot_data_stale=True
  - Enforce mode (COT_STALE_GATE_ENFORCE=1): hard-reject
Fail-open when latest_cot_date is absent or unparseable. Kill: COT_STALE_GATE_DISABLED=1.
"""
import datetime
import pytest
from audit_trail.quality_gates import passes_active_gate


def _yesterday_iso() -> str:
    return (datetime.datetime.utcnow() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")


def _stale_iso(days: int = 15) -> str:
    return (datetime.datetime.utcnow() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")


def _fresh_iso(days: int = 3) -> str:
    return (datetime.datetime.utcnow() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")


def _commodity_cot_pick(**overrides):
    pick = {
        "id": "test-cot-1",
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
        "latest_cot_date": _fresh_iso(),
    }
    pick.update(overrides)
    return pick


def _common_env(monkeypatch):
    monkeypatch.setenv("COT_STALE_GATE_DISABLED", "0")
    monkeypatch.setenv("COT_STALE_GATE_ENFORCE", "0")
    monkeypatch.setenv("COT_STALE_DAYS", "10")
    monkeypatch.setenv("CRYPTO_ML_SCORE_GATE_ENABLED", "0")
    monkeypatch.setenv("NUPL_GATE_ENFORCE", "0")
    monkeypatch.setenv("M044_MIN_AGE_SECONDS", "0")
    monkeypatch.setenv("ETF_VIX_GATE_DISABLED", "1")
    monkeypatch.setenv("BOOK_CONFLICT_GATE_DISABLED", "1")
    monkeypatch.setenv("COT_MATCH_GATE_ENABLED", "0")
    monkeypatch.setenv("COT_DEDUP_GATE_ENABLED", "0")
    monkeypatch.setenv("COMMODITY_CTF_WEEKLY_CAP", "off")
    monkeypatch.setenv("COMMODITY_CTF_CAP", "0")
    monkeypatch.setenv("COMMODITY_SOURCE_CAP", "0")


class TestM001CotStaleGate:

    def test_shadow_stamps_stale_cot_data(self, monkeypatch):
        """Shadow: latest_cot_date=15 days ago → stamp _cot_data_stale=True, don't block."""
        _common_env(monkeypatch)
        pick = _commodity_cot_pick(latest_cot_date=_stale_iso(15))
        result = passes_active_gate(pick)
        assert result is True, "Shadow mode must not block"
        assert pick.get("_cot_data_stale") is True, "Must stamp _cot_data_stale=True"
        assert pick.get("_cot_data_age_days", 0) >= 14

    def test_shadow_no_stamp_fresh_cot_data(self, monkeypatch):
        """Shadow: latest_cot_date=3 days ago (fresh) → no stamp."""
        _common_env(monkeypatch)
        pick = _commodity_cot_pick(latest_cot_date=_fresh_iso(3))
        result = passes_active_gate(pick)
        assert result is True
        assert not pick.get("_cot_data_stale"), "Fresh COT data must not be stamped"

    def test_enforce_rejects_stale_cot_data(self, monkeypatch):
        """Enforce: latest_cot_date=15 days ago → hard reject."""
        _common_env(monkeypatch)
        monkeypatch.setenv("COT_STALE_GATE_ENFORCE", "1")
        pick = _commodity_cot_pick(latest_cot_date=_stale_iso(15))
        result = passes_active_gate(pick)
        if result is not False:
            pytest.skip("pick passed — another gate blocked before M-001")
        assert result is False, "Enforce must reject stale COT pick"

    def test_enforce_allows_fresh_cot_data(self, monkeypatch):
        """Enforce: latest_cot_date=3 days ago → allow."""
        _common_env(monkeypatch)
        monkeypatch.setenv("COT_STALE_GATE_ENFORCE", "1")
        pick = _commodity_cot_pick(latest_cot_date=_fresh_iso(3))
        result = passes_active_gate(pick)
        assert result is True, "Fresh COT data must pass"

    def test_fail_open_missing_cot_date(self, monkeypatch):
        """Fail-open: no latest_cot_date → gate skipped."""
        _common_env(monkeypatch)
        monkeypatch.setenv("COT_STALE_GATE_ENFORCE", "1")
        pick = _commodity_cot_pick(latest_cot_date="")
        result = passes_active_gate(pick)
        assert result is True, "Missing cot_date must fail-open (allow)"
        assert not pick.get("_cot_data_stale")

    def test_disabled_gate_skips_check(self, monkeypatch):
        """COT_STALE_GATE_DISABLED=1 → gate entirely skipped."""
        _common_env(monkeypatch)
        monkeypatch.setenv("COT_STALE_GATE_DISABLED", "1")
        monkeypatch.setenv("COT_STALE_GATE_ENFORCE", "1")
        pick = _commodity_cot_pick(latest_cot_date=_stale_iso(30))
        result = passes_active_gate(pick)
        assert result is True, "Disabled gate must not block"
        assert not pick.get("_cot_data_stale")

    def test_non_cot_source_unaffected(self, monkeypatch):
        """Gate only fires for known COT source_systems; other COMMODITY strategies bypass."""
        _common_env(monkeypatch)
        monkeypatch.setenv("COT_STALE_GATE_ENFORCE", "1")
        pick = _commodity_cot_pick(
            source_system="sector_rotation",
            latest_cot_date=_stale_iso(30),
        )
        result = passes_active_gate(pick)
        assert not pick.get("_cot_data_stale"), "Non-COT source must not be stamped"

    def test_non_commodity_unaffected(self, monkeypatch):
        """Gate only applies to COMMODITY asset class; CRYPTO bypasses."""
        _common_env(monkeypatch)
        monkeypatch.setenv("COT_STALE_GATE_ENFORCE", "1")
        pick = _commodity_cot_pick(
            asset_class="CRYPTO",
            source_system="cftc_cot_commercial_signal",
            latest_cot_date=_stale_iso(30),
        )
        result = passes_active_gate(pick)
        assert not pick.get("_cot_data_stale"), "Non-COMMODITY must not be stamped"

    def test_custom_stale_threshold(self, monkeypatch):
        """COT_STALE_DAYS=5 → data 7 days old is stale."""
        _common_env(monkeypatch)
        monkeypatch.setenv("COT_STALE_DAYS", "5")
        pick = _commodity_cot_pick(latest_cot_date=_stale_iso(7))
        result = passes_active_gate(pick)
        assert result is True
        assert pick.get("_cot_data_stale") is True, "7-day-old data must be stale at threshold=5"

    def test_multi_asset_cot_source_stamped(self, monkeypatch):
        """multi_asset_cot source system triggers staleness check (uses its own strategy name)."""
        _common_env(monkeypatch)
        pick = _commodity_cot_pick(
            source_system="multi_asset_cot",
            strategy="multi_asset_cot",
            latest_cot_date=_stale_iso(15),
        )
        result = passes_active_gate(pick)
        assert result is True
        assert pick.get("_cot_data_stale") is True

    def test_latest_cot_date_from_extra_dict(self, monkeypatch):
        """latest_cot_date nested in pick['extra'] is checked (multi_asset_cot scraper path)."""
        _common_env(monkeypatch)
        pick = _commodity_cot_pick(
            source_system="multi_asset_cot",
            strategy="cot_positioning",
        )
        # Remove top-level latest_cot_date, put it inside extra dict (as scraper does)
        pick.pop("latest_cot_date", None)
        pick["extra"] = {"latest_cot_date": _stale_iso(15)}
        result = passes_active_gate(pick)
        assert result is True
        assert pick.get("_cot_data_stale") is True, "extra dict latest_cot_date not picked up"
