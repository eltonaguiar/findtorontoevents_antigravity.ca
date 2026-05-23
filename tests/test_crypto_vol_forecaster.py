"""Test crypto volatility forecaster."""
import numpy as np
import pytest
import sys
sys.path.insert(0, '.')


def test_ewma_fallback_with_mock_data(monkeypatch):
    """EWMA fallback should return reasonable vol when GARCH unavailable."""
    import risk_management.crypto_vol_forecaster as cvf
    cvf.clear_cache()

    # Mock fetch_single to return synthetic data
    import pandas as pd
    def mock_fetch(pair, interval="1h", limit=500):
        np.random.seed(42)
        n = limit
        prices = 100 * np.exp(np.cumsum(np.random.normal(0, 0.02, n)))
        return pd.DataFrame({"Close": prices})

    monkeypatch.setattr("risk_management.crypto_vol_forecaster.HAS_ARCH", False)

    # Patch the fetch_single import inside the module
    import ml_battleground.shared.data_fetcher as df_mod
    monkeypatch.setattr(df_mod, "fetch_single", mock_fetch)

    vol = cvf.forecast_crypto_vol("BTCUSDT", interval="1h", lookback=200)
    assert 0.005 <= vol <= 0.50, f"Vol {vol} out of range"
    print(f"EWMA vol for BTCUSDT: {vol:.4f}")


def test_cache_works(monkeypatch):
    """Second call should use cache."""
    import risk_management.crypto_vol_forecaster as cvf
    cvf.clear_cache()

    import pandas as pd
    call_count = [0]
    def mock_fetch(pair, interval="1h", limit=500):
        call_count[0] += 1
        np.random.seed(42)
        prices = 100 * np.exp(np.cumsum(np.random.normal(0, 0.02, limit)))
        return pd.DataFrame({"Close": prices})

    monkeypatch.setattr("risk_management.crypto_vol_forecaster.HAS_ARCH", False)
    import ml_battleground.shared.data_fetcher as df_mod
    monkeypatch.setattr(df_mod, "fetch_single", mock_fetch)

    vol1 = cvf.forecast_crypto_vol("ETHUSDT")
    vol2 = cvf.forecast_crypto_vol("ETHUSDT")
    assert vol1 == vol2
    assert call_count[0] == 1, "Should have used cache on second call"


def test_default_on_fetch_failure(monkeypatch):
    """Should return 0.02 default if data fetch fails."""
    import risk_management.crypto_vol_forecaster as cvf
    cvf.clear_cache()

    def mock_fetch_fail(pair, interval="1h", limit=500):
        raise ConnectionError("API down")

    import ml_battleground.shared.data_fetcher as df_mod
    monkeypatch.setattr(df_mod, "fetch_single", mock_fetch_fail)

    vol = cvf.forecast_crypto_vol("XYZUSDT")
    assert vol == 0.02
