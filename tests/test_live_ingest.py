"""Test live Parquet ingestion pipeline."""
import sys
import pandas as pd
import numpy as np
import pytest
from pathlib import Path

sys.path.insert(0, '.')

# These tests require a parquet engine (pyarrow or fastparquet).
# Skip the entire module when neither is installed.
try:
    import pyarrow  # noqa: F401
    _PARQUET_AVAILABLE = True
except ImportError:
    try:
        import fastparquet  # noqa: F401
        _PARQUET_AVAILABLE = True
    except ImportError:
        _PARQUET_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _PARQUET_AVAILABLE,
    reason="pyarrow or fastparquet required for parquet support",
)


def test_ingest_pair_with_mock(monkeypatch, tmp_path):
    """Ingest should write Parquet and return new bar count."""
    from data_pipeline import live_ingest

    # Mock fetch_single
    def mock_fetch(pair, interval="1h", limit=500):
        n = min(limit, 100)
        df = pd.DataFrame({
            "timestamp": pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC"),
            "Open": np.random.uniform(50000, 60000, n),
            "High": np.random.uniform(60000, 65000, n),
            "Low": np.random.uniform(45000, 50000, n),
            "Close": np.random.uniform(50000, 60000, n),
            "Volume": np.random.uniform(100, 1000, n),
        })
        df.set_index("timestamp", inplace=True)
        return df

    import ml_battleground.shared.data_fetcher as df_mod
    monkeypatch.setattr(df_mod, "fetch_single", mock_fetch)

    new_bars = live_ingest.ingest_pair("BTCUSDT", "1h", limit=100, base_dir=tmp_path)
    assert new_bars == 100

    # Verify file exists
    path = tmp_path / "BTCUSDT" / "1h.parquet"
    assert path.exists()

    # Read back
    df = pd.read_parquet(path)
    assert len(df) == 100


def test_dedup_on_reingest(monkeypatch, tmp_path):
    """Re-ingesting same data should not duplicate."""
    from data_pipeline import live_ingest

    def mock_fetch(pair, interval="1h", limit=500):
        df = pd.DataFrame({
            "timestamp": pd.date_range("2026-01-01", periods=50, freq="1h", tz="UTC"),
            "Open": range(50), "High": range(50), "Low": range(50),
            "Close": range(50), "Volume": range(50),
        })
        df.set_index("timestamp", inplace=True)
        return df

    import ml_battleground.shared.data_fetcher as df_mod
    monkeypatch.setattr(df_mod, "fetch_single", mock_fetch)

    n1 = live_ingest.ingest_pair("ETHUSDT", "1h", base_dir=tmp_path)
    assert n1 == 50

    n2 = live_ingest.ingest_pair("ETHUSDT", "1h", base_dir=tmp_path)
    assert n2 == 0  # no new bars

    df = pd.read_parquet(tmp_path / "ETHUSDT" / "1h.parquet")
    assert len(df) == 50  # still 50, not 100


def test_get_pair_data(monkeypatch, tmp_path):
    """get_pair_data should read back ingested data."""
    from data_pipeline import live_ingest

    def mock_fetch(pair, interval="1h", limit=500):
        df = pd.DataFrame({
            "timestamp": pd.date_range("2026-01-01", periods=20, freq="1h", tz="UTC"),
            "Close": range(20),
        })
        df.set_index("timestamp", inplace=True)
        return df

    import ml_battleground.shared.data_fetcher as df_mod
    monkeypatch.setattr(df_mod, "fetch_single", mock_fetch)

    live_ingest.ingest_pair("SOLUSDT", "4h", base_dir=tmp_path)

    df = live_ingest.get_pair_data("SOLUSDT", "4h", base_dir=tmp_path)
    assert len(df) == 20

    # Test last_n
    df = live_ingest.get_pair_data("SOLUSDT", "4h", last_n=5, base_dir=tmp_path)
    assert len(df) == 5
