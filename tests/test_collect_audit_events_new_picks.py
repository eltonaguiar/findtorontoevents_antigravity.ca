"""collect_audit_events must not crash when CSE audit.json stores a count."""

import audit_trail.dashboard_generator as dg


def _patch(monkeypatch, payload):
    monkeypatch.setattr(dg, "_safe_sqlite", lambda *a, **k: [])

    def _json(path):
        if str(path).endswith("crypto_signal_engine/data/audit.json"):
            return payload
        return None

    monkeypatch.setattr(dg, "_safe_json", _json)


def test_int_new_picks_does_not_crash(monkeypatch):
    _patch(monkeypatch, {"new_picks": 12, "timestamp_utc": "2026-11-16T00:00:00Z"})
    assert dg.collect_audit_events(5) == []


def test_list_new_picks_still_recorded(monkeypatch):
    _patch(
        monkeypatch,
        {
            "new_picks": [{"symbol": "BTCUSDT", "strategy": "x", "direction": "LONG"}],
            "timestamp_utc": "2026-11-16T00:00:00Z",
        },
    )
    events = dg.collect_audit_events(5)
    assert len(events) == 1
    assert events[0]["symbol"] == "BTCUSDT"
    assert events[0]["event_type"] == "CSE_NEW_PICK"
