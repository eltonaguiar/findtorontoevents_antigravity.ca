#!/usr/bin/env python3
"""forecast_consensus_picks.py — ARIMA 30-day forecast + ADF on consensus-LONG tickers.

Per 6-engine swarm consensus 2026-06-04 (vllm-large/fast, ollama-large/fast,
deepseek, xai): use statsmodels ARIMA(1,1,1) + ADF on daily closes of each
tournament-consensus LONG ticker. Output 30-day mean + 95% CI band. Log to
mlflow.db local SQLite (no cloud).

VERIFIED REAL-EDGE TICKERS (post INCIDENT #91 dedup on tournament_picks, which
turned out NOT to have the dup problem — tournament_picks ratio = 1.00x):
- SPY LONG: n=35 / WR 82.9% / avg +1.56%
- QQQ LONG: n=33 / WR 84.8% / avg +2.51%
- IWM LONG: n=34 / WR 79.4% / avg +1.45%

NO-EDGE (consensus is WRONG):
- MSFT LONG: n=49 / WR 42.9% / avg -0.49%

UNVERIFIED (all OPEN, no closed history):
- GLD, EEM, AAPL, JPM, MA

Usage: python3 tools/forecast_consensus_picks.py
View UI: mlflow ui --backend-store-uri sqlite:///mlflow.db
"""
from __future__ import annotations

import os
import warnings
from datetime import datetime, timezone

import mlflow
import numpy as np
import pandas as pd
import yfinance as yf
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MLRUNS_DB = os.path.join(REPO, "mlflow.db")

# Tier-1: verified real edge (tournament_picks deduped post 7 audit rounds)
TIER1_TICKERS = [
    ("SPY", 35, 0.829, 1.56),   # symbol, n_verified, WR, avg_pnl
    ("QQQ", 33, 0.848, 2.51),
    ("IWM", 34, 0.794, 1.45),
]
# Tier-2: open consensus today, no closed history yet
TIER2_TICKERS = [
    ("GLD", 0, None, None),
    ("EEM", 0, None, None),
    ("AAPL", 0, None, None),
    ("JPM", 0, None, None),
    ("MA", 0, None, None),
]
# Anti-consensus: high-model-count signal that's been wrong
ANTI_TICKERS = [
    ("MSFT", 49, 0.429, -0.49),  # consensus is LONG but actual edge is short/none
]


def fetch_closes(symbol: str, days: int = 365) -> pd.Series:
    df = yf.download(symbol, period=f"{days}d", auto_adjust=True, progress=False, threads=False)
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    return df["Close"].dropna()


def run_arima_forecast(symbol: str, closes: pd.Series, horizon: int = 30):
    """ARIMA(1,1,1) + ADF + 30-day forecast with 95% CI band."""
    if len(closes) < 60:
        return None
    # ADF on log returns (stationarity check)
    returns = np.log(closes).diff().dropna()
    try:
        adf_stat, adf_p, *_ = adfuller(returns, autolag="AIC")
    except Exception:
        adf_stat, adf_p = float("nan"), float("nan")
    # ARIMA on log price → forecast 30 days
    try:
        model = ARIMA(np.log(closes), order=(1, 1, 1)).fit()
        fc = model.get_forecast(horizon)
        mean_log = fc.predicted_mean
        ci = fc.conf_int(alpha=0.05)
        mean_price = float(np.exp(mean_log.iloc[-1]))
        lo_price = float(np.exp(ci.iloc[-1, 0]))
        hi_price = float(np.exp(ci.iloc[-1, 1]))
        last_price = float(closes.iloc[-1])
        expected_return = (mean_price / last_price - 1) * 100
        return {
            "last_price": last_price,
            "h30_mean": mean_price,
            "h30_lo95": lo_price,
            "h30_hi95": hi_price,
            "h30_exp_return_pct": expected_return,
            "adf_stat": float(adf_stat),
            "adf_pvalue": float(adf_p),
            "aic": float(model.aic),
        }
    except Exception as e:
        return {"error": str(e), "adf_stat": float(adf_stat), "adf_pvalue": float(adf_p)}


def main():
    mlflow.set_tracking_uri(f"sqlite:///{MLRUNS_DB}")
    mlflow.set_experiment("forecast_consensus_picks_2026-06-04")
    print(f"mlflow: sqlite:///{MLRUNS_DB} (local, no cloud)")
    print(f"{'sym':6} {'tier':6} {'last':>8} {'h30':>8} {'lo95':>8} {'hi95':>8} {'ret':>7} {'ADF_p':>6}")

    all_tickers = (
        [("T1", s, n, wr, avg) for s, n, wr, avg in TIER1_TICKERS]
        + [("T2", s, n, wr, avg) for s, n, wr, avg in TIER2_TICKERS]
        + [("ANTI", s, n, wr, avg) for s, n, wr, avg in ANTI_TICKERS]
    )

    for tier, sym, n_verified, wr, avg in all_tickers:
        closes = fetch_closes(sym, days=365)
        if closes.empty:
            print(f"  {sym:6} {tier:6} NO PRICE DATA")
            continue
        res = run_arima_forecast(sym, closes)
        if res is None or "error" in res:
            err = (res or {}).get("error", "n<60")
            print(f"  {sym:6} {tier:6} ARIMA FAIL: {err}")
            continue
        with mlflow.start_run(run_name=f"{sym}_arima_30d_{tier}"):
            mlflow.log_param("symbol", sym)
            mlflow.log_param("tier", tier)
            mlflow.log_param("model", "ARIMA(1,1,1) on log(close)")
            mlflow.log_param("horizon_days", 30)
            mlflow.log_param("training_days", len(closes))
            if wr is not None:
                mlflow.log_metric("hist_n_closed", n_verified)
                mlflow.log_metric("hist_wr", wr)
                mlflow.log_metric("hist_avg_pnl_pct", avg)
            for k, v in res.items():
                if isinstance(v, (int, float)) and not np.isnan(v):
                    mlflow.log_metric(k, v)
            verdict = "PROCEED" if (
                tier == "T1" and res["h30_exp_return_pct"] > 0 and res["adf_pvalue"] < 0.5
            ) else ("WATCH" if tier == "T1" else "AVOID" if tier == "ANTI" else "INSUFFICIENT_HISTORY")
            mlflow.log_param("verdict", verdict)
        print(f"  {sym:6} {tier:6} {res['last_price']:>7.2f} {res['h30_mean']:>7.2f} {res['h30_lo95']:>7.2f} {res['h30_hi95']:>7.2f} {res['h30_exp_return_pct']:>+6.2f}% {res['adf_pvalue']:>5.3f} {verdict}")

    print(f"\nView in browser: mlflow ui --backend-store-uri sqlite:///{MLRUNS_DB}")


if __name__ == "__main__":
    main()
