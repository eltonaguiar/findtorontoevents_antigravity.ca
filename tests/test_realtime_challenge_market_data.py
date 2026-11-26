#!/usr/bin/env python3
"""Market-data host fallback for tools/realtime_challenge.py.

Regression for run 45163680658 (2026-11-23): api.binance.com answered HTTP 451
to the GitHub-hosted runner, every symbol failed, and the cycle exited 2 so the
scheduled run showed red. klines() now falls through to the venue's public
market-data mirror and only fails when *no* host answers.
"""
import importlib.util
import json
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("realtime_challenge", ROOT / "tools" / "realtime_challenge.py")
rtc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rtc)

BARS = [[1_700_000_000_000 + i * 300_000, "100.0", "101.0", "99.0", "100.5", "12.5"]
        for i in range(3)]


class _Resp:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http_451(url):
    raise urllib.error.HTTPError(url, 451, "Unavailable For Legal Reasons", {}, None)


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(rtc, "_API_BASE", None)
    monkeypatch.setattr(rtc.time, "sleep", lambda *_: None)
    yield


def test_falls_back_to_mirror_when_primary_is_451(monkeypatch):
    seen = []

    def fake_urlopen(url, timeout=15):
        seen.append(url)
        if "api.binance.com" in url:
            _http_451(url)
        return _Resp(BARS)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    bars = rtc.klines("BTCUSDT")

    assert [b["close"] for b in bars] == [100.5, 100.5, 100.5]
    assert len(bars) == 3
    assert rtc._API_BASE == rtc.API_MIRRORS[0]
    # primary was tried first, then the mirror
    assert "api.binance.com" in seen[0]
    assert rtc.API_MIRRORS[0] in seen[-1]


def test_cached_host_is_used_on_the_next_symbol(monkeypatch):
    seen = []

    def fake_urlopen(url, timeout=15):
        seen.append(url)
        if "api.binance.com" in url:
            _http_451(url)
        return _Resp(BARS)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    rtc.klines("BTCUSDT")          # discovers the mirror
    seen.clear()
    rtc.klines("ETHUSDT")          # should not re-pay the 451

    assert all("api.binance.com" not in u for u in seen), seen
    assert rtc.API_MIRRORS[0] in seen[0]


def test_raises_only_when_every_host_fails(monkeypatch):
    def fake_urlopen(url, timeout=15):
        _http_451(url)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError) as exc:
        rtc.klines("BTCUSDT")

    msg = str(exc.value)
    assert "all market-data hosts failed" in msg
    assert rtc.API in msg and rtc.API_MIRRORS[0] in msg


def test_frozen_rules_are_untouched():
    """The fallback must not have moved any pre-registered constant."""
    assert rtc.API == "https://api.binance.com/api/v3"
    assert (rtc.TP_PCT, rtc.SL_PCT, rtc.TIME_STOP_MIN, rtc.SLOTS) == (0.0060, 0.0040, 60, 3)
    assert rtc.FEE_BPS_PER_SIDE == 10.0 and rtc.SLIP_BPS_PER_SIDE == 2.0
