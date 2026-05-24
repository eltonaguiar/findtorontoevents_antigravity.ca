"""
Tournament Analytics Engine — portfolio risk metrics, ML predictions, and data loading.

Provides compute_basic_risk_metrics, ml_price_prediction, and data loaders
for the AI Prediction Tournament. Uses standard finance concepts (VaR, Sharpe,
Markowitz, LSTM) that are universal mathematical methods.
"""
from __future__ import annotations

import json
import os
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO_ROOT = Path(__file__).resolve().parent.parent

# ── Data loading per asset class ──

ASSET_CLASS_TICKERS: dict[str, list[str]] = {
    "CRYPTO": ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
               "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "LTC-USD"],
    "EQUITY": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
               "JPM", "V", "JNJ", "WMT", "MA"],
    "FOREX": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCHF=X"],
    "COMMODITY": ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F"],
    "ETF": ["SPY", "QQQ", "IWM", "EEM", "GLD"],
    "BOND": ["^TNX", "^TYX"],
    "PENNY": ["KULR", "LODE", "CTM", "MVST", "RGTI", "QBTS", "IONQ",
              "FFIE", "ASTS", "GSAT", "RKLB", "WULF", "CLSK", "MARA"],
}


def yahoo_to_tournament_symbol(ticker: str) -> str:
    """Convert yahoo ticker to tournament symbol."""
    m = {"-USD": "USDT", "=X": "", "=F": "=F", "^": "^"}
    for k, v in m.items():
        ticker = ticker.replace(k, v)
    return ticker


def load_price_data(asset_class: str, period: str = "6mo") -> pd.DataFrame | None:
    """Load historical prices for an asset class via yfinance."""
    tickers = ASSET_CLASS_TICKERS.get(asset_class, [])
    if not tickers:
        return None
    try:
        import yfinance as yf
        data = yf.download(tickers, period=period, progress=False, auto_adjust=True)
        if data.empty:
            return None
        # yfinance returns MultiIndex columns in newer versions
        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"]
        else:
            close = data
        return close.dropna(axis=1, how="all")
    except Exception as e:
        print(f"  [data] {asset_class}: load failed — {e}")
        return None


# ── Risk metrics (standard finance formulas) ──

def compute_portfolio_stats(returns: pd.DataFrame) -> dict[str, Any]:
    """Compute standard portfolio risk metrics from a return series."""
    if returns is None or returns.empty:
        return {"error": "no data"}

    # Basic stats
    mean_ret = returns.mean().mean()
    std_ret = returns.std().mean()
    # Annualized (assuming daily returns)
    annual_return = mean_ret * 252
    annual_vol = std_ret * np.sqrt(252)
    sharpe = annual_return / annual_vol if annual_vol > 0 else 0.0

    # VaR (historical)
    var_95 = np.percentile(returns.values, 5)
    cvar_95 = returns.values[returns.values <= var_95].mean() if (returns.values <= var_95).any() else var_95

    # Max drawdown
    cum = (1 + returns).cumprod()
    rolling_max = cum.expanding().max()
    drawdown = (cum / rolling_max) - 1
    max_dd = drawdown.min()

    # Win rate
    win_rate = (returns > 0).mean().mean()

    return {
        "annual_return_pct": round(annual_return * 100, 2),
        "annual_vol_pct": round(annual_vol * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "var_95_pct": round(float(var_95) * 100, 2),
        "cvar_95_pct": round(float(cvar_95) * 100, 2),
        "max_drawdown_pct": round(float(max_dd) * 100, 2),
        "win_rate_pct": round(float(win_rate) * 100, 1),
        "n_assets": returns.shape[1],
        "n_observations": returns.shape[0],
    }


def compute_asset_stats(
    prices: pd.DataFrame, risk_free_rate: float = 0.04
) -> list[dict[str, Any]]:
    """Compute per-asset risk metrics."""
    if prices is None or prices.empty:
        return []

    returns = prices.pct_change().dropna()
    results = []
    for col in prices.columns:
        r = returns[col].dropna()
        if len(r) < 5:
            continue
        ann_ret = float(r.mean() * 252)
        ann_vol = float(r.std() * np.sqrt(252))
        sharpe = (ann_ret - risk_free_rate) / ann_vol if ann_vol > 0 else 0.0
        var_95 = float(np.percentile(r, 5))
        sortino_denom = float(r[r < 0].std() * np.sqrt(252))
        sortino = (ann_ret - risk_free_rate) / sortino_denom if sortino_denom > 0 else 0.0
        results.append({
            "symbol": col,
            "annual_return_pct": round(ann_ret * 100, 2),
            "annual_vol_pct": round(ann_vol * 100, 2),
            "sharpe": round(sharpe, 3),
            "sortino": round(sortino, 3),
            "var_95_pct": round(var_95 * 100, 2),
            "n_days": len(r),
        })
    return results


# ── ML price prediction (LSTM / Transformer) ──

class LSTMPredictor:
    """
    Simple LSTM/GRU-based price predictor using PyTorch.

    Standard time-series forecasting approach (sequence-to-one regression).
    Configurable: LSTM, GRU, or simple linear model.
    """
    def __init__(
        self, seq_len: int = 20, hidden: int = 64, layers: int = 2,
        model_type: str = "lstm", dropout: float = 0.2
    ):
        self.seq_len = seq_len
        self.hidden = hidden
        self.layers = layers
        self.dropout = dropout
        self.model_type = model_type
        self.model = None
        self._fitted = False

    def _build_model(self, input_dim: int):
        import torch.nn as nn
        import torch

        class _LSTM(nn.Module):
            def __init__(self, inp, hid, layers, dropout, mtype):
                super().__init__()
                if mtype == "gru":
                    self.rnn = nn.GRU(inp, hid, layers, batch_first=True, dropout=dropout if layers > 1 else 0)
                else:
                    self.rnn = nn.LSTM(inp, hid, layers, batch_first=True, dropout=dropout if layers > 1 else 0)
                self.fc = nn.Linear(hid, 1)

            def forward(self, x):
                out, _ = self.rnn(x)
                return self.fc(out[:, -1, :])

        self.model = _LSTM(input_dim, self.hidden, self.layers, self.dropout, self.model_type)

    def fit(self, prices: pd.Series, epochs: int = 50, lr: float = 0.01):
        """Fit LSTM to a price series."""
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset

        values = prices.dropna().values.astype(np.float32)
        if len(values) < self.seq_len + 10:
            return

        # Normalize
        mean, std = values.mean(), values.std()
        if std < 1e-8:
            return
        normed = (values - mean) / std

        # Build sequences
        X, y = [], []
        for i in range(len(normed) - self.seq_len):
            X.append(normed[i:i + self.seq_len])
            y.append(normed[i + self.seq_len])
        X = np.array(X).reshape(-1, self.seq_len, 1)
        y = np.array(y)

        self._build_model(1)
        loader = DataLoader(TensorDataset(torch.tensor(X), torch.tensor(y)), batch_size=32, shuffle=True)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        loss_fn = nn.MSELoss()

        self.model.train()
        for _ in range(epochs):
            for bx, by in loader:
                optimizer.zero_grad()
                loss = loss_fn(self.model(bx).squeeze(), by)
                loss.backward()
                optimizer.step()

        self._fitted = True
        self._norm_mean = mean
        self._norm_std = std

    def predict(self, last_values: np.ndarray, steps: int = 5) -> list[float]:
        """Predict next `steps` price changes."""
        if not self._fitted:
            return []
        import torch
        self.model.eval()
        normed = (last_values[-self.seq_len:] - self._norm_mean) / self._norm_std
        input_seq = torch.tensor(normed.reshape(1, self.seq_len, 1), dtype=torch.float32)
        preds = []
        with torch.no_grad():
            for _ in range(steps):
                out = self.model(input_seq).item()
                preds.append(out * self._norm_std + self._norm_mean)
                # Slide window
                next_in = np.append(input_seq.numpy()[0, 1:, 0], out)
                input_seq = torch.tensor(next_in.reshape(1, self.seq_len, 1), dtype=torch.float32)
        return preds


def run_ml_forecast(
    asset_class: str, model_type: str = "lstm", top_n: int = 5
) -> list[dict[str, Any]]:
    """
    Run ML forecast across all symbols in an asset class.
    Returns top_n predicted gainers sorted by expected return.
    """
    prices = load_price_data(asset_class, period="6mo")
    if prices is None or prices.empty:
        return []

    predictor = LSTMPredictor(model_type=model_type, seq_len=20)
    forecasts = []

    for symbol in prices.columns:
        series = prices[symbol].dropna()
        if len(series) < 30:
            continue
        predictor.fit(series, epochs=30)
        preds = predictor.predict(series.values, steps=5)
        if preds:
            current = float(series.iloc[-1])
            expected_return = (preds[-1] - current) / current
            forecasts.append({
                "symbol": yahoo_to_tournament_symbol(str(symbol)),
                "current_price": round(current, 4),
                "predicted_price": round(preds[-1], 4),
                "expected_return_pct": round(expected_return * 100, 2),
                "model_type": model_type,
            })

    forecasts.sort(key=lambda x: abs(x["expected_return_pct"]), reverse=True)
    return forecasts[:top_n]


if __name__ == "__main__":
    print("=== Tournament Analytics Engine ===")
    results = {}
    for ac in ["CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF", "BOND", "PENNY", "FUTURES"]:
        p = load_price_data(ac, "3mo")
        if p is not None:
            stats = compute_portfolio_stats(p.pct_change().dropna())
            results[ac] = stats
            print(f"{ac:15s} Sharpe={stats.get('sharpe_ratio',0):.3f} VaR={stats.get('var_95_pct',0)}% DD={stats.get('max_drawdown_pct',0)}%")

    # Write risk metrics
    import json
    from pathlib import Path
    out = Path("audit_dashboard/data/research/risk_metrics.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "asset_classes": results
    }, indent=2))
    print(f"\nWritten risk_metrics.json ({len(results)} asset classes)")
