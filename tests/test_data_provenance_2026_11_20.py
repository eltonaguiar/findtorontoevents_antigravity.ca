"""P0.9 survivorship stamp + P0.8 ALFRED vintage fetch."""
import json

import pytest

from alpha_engine import data_provenance
from tools import fred_vintage


def test_yfinance_universe_is_stamped_flattered():
    a = data_provenance.stamp_provenance({"symbols": ["AAPL"]}, "yfinance", "2026-11-20")
    assert a["survivorship_flattered"] is True
    assert a["provenance_source"] == "yfinance"
    assert data_provenance.is_flattered(a) is True


@pytest.mark.parametrize("src", ["sec_edgar", "ALFRED", "cftc"])
def test_point_in_time_sources_are_not_flattered(src):
    a = data_provenance.stamp_provenance({}, src, "2026-11-20")
    assert a["survivorship_flattered"] is False
    assert data_provenance.is_flattered(a) is False


def test_missing_stamp_counts_as_flattered():
    assert data_provenance.is_flattered({}) is True
    assert data_provenance.is_flattered({"survivorship_flattered": None}) is True


def test_stamp_does_not_mutate_input():
    src = {"symbols": ["AAPL"]}
    data_provenance.stamp_provenance(src, "yfinance")
    assert "survivorship_flattered" not in src


def test_vintage_fetch_parses_and_caches(tmp_path):
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return json.dumps({"realtime_start": "2026-01-15",
                           "observations": [{"date": "2025-12-01", "value": "1.5"}]})

    out = fred_vintage.fetch_vintage("CPIAUCSL", "2026-01-15", api_key="k",
                                     fetch=fake_fetch, cache_dir=tmp_path)
    assert out["n"] == 1 and out["observations"][0]["value"] == "1.5"
    assert "realtime_start=2026-01-15" in calls[0]
    # second call must hit the cache, not the network
    fred_vintage.fetch_vintage("CPIAUCSL", "2026-01-15", api_key="k",
                               fetch=fake_fetch, cache_dir=tmp_path)
    assert len(calls) == 1


def test_vintage_fetch_requires_a_key(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        fred_vintage.fetch_vintage("CPIAUCSL", "2026-01-15", api_key=None,
                                   fetch=lambda u: "{}", cache_dir="/tmp/x_vintage_test")
