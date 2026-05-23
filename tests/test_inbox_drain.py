"""Tests for cross_pc_protocol.inbox_drain — the send-only-agent fix."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cross_pc_protocol.inbox_drain as idrain


def _fake_poll(mapping):
    """Return a _poll_queue stand-in that serves `mapping[peer_id]`."""
    def _poll(peer_id, http_base, limit):
        return list(mapping.get(peer_id, []))
    return _poll


def test_drains_dm_and_broadcast(monkeypatch):
    monkeypatch.setattr(idrain, "_poll_queue", _fake_poll({
        "agent-x": [{"message_id": "d1", "topic": "dm"}],
        "all": [{"message_id": "b1", "topic": "broadcast"}],
    }))
    out = idrain.drain_inbox("agent-x")
    ids = [m["message_id"] for m in out]
    assert ids == ["d1", "b1"]  # DMs first, then broadcasts


def test_dedup_by_message_id(monkeypatch):
    monkeypatch.setattr(idrain, "_poll_queue", _fake_poll({
        "agent-x": [{"message_id": "x", "topic": "dm"}],
        "all": [{"message_id": "x", "topic": "broadcast"}],  # same id
    }))
    out = idrain.drain_inbox("agent-x")
    assert len(out) == 1 and out[0]["topic"] == "dm"


def test_gateway_down_returns_empty(monkeypatch):
    # real _poll_queue against a dead host must fail-soft to []
    monkeypatch.setattr(idrain, "DEFAULT_HTTP_BASE", "http://127.0.0.1:59999")
    out = idrain.drain_inbox("agent-x", http_base="http://127.0.0.1:59999")
    assert out == []


def test_drain_does_not_raise_on_bad_base(monkeypatch):
    # garbage base url -> [], no exception
    out = idrain.drain_inbox("agent-x", http_base="http://nonexistent.invalid:1")
    assert out == []


def test_empty_queues(monkeypatch):
    monkeypatch.setattr(idrain, "_poll_queue", _fake_poll({}))
    assert idrain.drain_inbox("agent-x") == []


def test_empty_peer_id():
    assert idrain.drain_inbox("") == []


def test_startup_inbox_check_returns_and_logs(monkeypatch, caplog):
    monkeypatch.setattr(idrain, "_poll_queue", _fake_poll({
        "agent-x": [{"message_id": "d1"}, {"message_id": "d2"}],
        "all": [],
    }))
    import logging
    with caplog.at_level(logging.INFO, logger="cross_pc.inbox_drain"):
        out = idrain.startup_inbox_check("agent-x")
    assert len(out) == 2
    assert any("2 message(s) for agent-x" in r.message for r in caplog.records)


def test_non_dict_messages_skipped(monkeypatch):
    monkeypatch.setattr(idrain, "_poll_queue", _fake_poll({
        "agent-x": [{"message_id": "ok"}, "garbage", 123],
        "all": [],
    }))
    out = idrain.drain_inbox("agent-x")
    assert len(out) == 1 and out[0]["message_id"] == "ok"
