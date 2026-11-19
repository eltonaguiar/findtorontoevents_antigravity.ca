import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine import audit3_denylist_hits as hits  # noqa: E402


PICK = {"strategy": "rsi_bounce", "symbol": "BTCUSDT", "asset_class": "CRYPTO",
        "direction": "LONG", "source_system": "alpha_engine"}
REASON = "audit3 KILL: CRYPTO BTC LONG n=407 net=-0.84%/trade"


def _enable(monkeypatch, tmp_path):
    monkeypatch.delenv("AUDIT3_DENYLIST_DISABLED", raising=False)
    monkeypatch.setenv("AUDIT3_DENYLIST_HIT_LOG", str(tmp_path / "hits.jsonl"))


def test_record_writes_one_line(monkeypatch, tmp_path):
    _enable(monkeypatch, tmp_path)
    assert hits.record(PICK, REASON) is True
    lines = (tmp_path / "hits.jsonl").read_text().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["strategy"] == "rsi_bounce" and row["symbol"] == "BTCUSDT"
    assert row["reason"].startswith("audit3 KILL")


def test_no_reason_writes_nothing(monkeypatch, tmp_path):
    _enable(monkeypatch, tmp_path)
    assert hits.record(PICK, "") is False
    assert not (tmp_path / "hits.jsonl").exists()


def test_disabled_by_kill_switch(monkeypatch, tmp_path):
    _enable(monkeypatch, tmp_path)
    monkeypatch.setenv("AUDIT3_DENYLIST_DISABLED", "1")
    assert hits.record(PICK, REASON) is False
    assert not (tmp_path / "hits.jsonl").exists()


def test_can_be_disabled_by_log_env(monkeypatch, tmp_path):
    monkeypatch.delenv("AUDIT3_DENYLIST_DISABLED", raising=False)
    monkeypatch.setenv("AUDIT3_DENYLIST_HIT_LOG", "0")
    assert hits.record(PICK, REASON, path=tmp_path / "hits.jsonl") is False


def test_summarize_counts(monkeypatch, tmp_path):
    _enable(monkeypatch, tmp_path)
    hits.record(PICK, REASON)
    hits.record(dict(PICK, symbol="ETHUSDT"), REASON)
    hits.record(dict(PICK, asset_class="FOREX", symbol="EURUSD"), "audit3 KILL: FOREX")
    out = hits.summarize(tmp_path / "hits.jsonl")
    assert out["n"] == 3
    assert out["by_symbol"]["BTCUSDT"] == 1
    assert out["by_class"]["CRYPTO"] == 2
    assert out["first_ts"] and out["last_ts"]


def test_summarize_missing_file_is_empty(tmp_path):
    out = hits.summarize(tmp_path / "nope.jsonl")
    assert out["n"] == 0 and out["by_strategy"] == {}


def test_rotation_keeps_tail(monkeypatch, tmp_path):
    _enable(monkeypatch, tmp_path)
    target = tmp_path / "hits.jsonl"
    monkeypatch.setattr(hits, "MAX_BYTES", 200)
    monkeypatch.setattr(hits, "KEEP_LINES", 3)
    for _ in range(10):
        hits.record(PICK, REASON)
    lines = target.read_text().splitlines()
    assert len(lines) <= 3
