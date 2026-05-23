"""P3 backtest runner — translates StrategySpec → BacktestResult.

v2: REAL prices via yfinance + REAL backtest math (SMA crossover as a
simplified signal translation since spec.entry is natural-language).
Falls back to stub on data-fetch failure.

The simplified signal translation is clearly marked in
`BacktestResult.notes`. A faithful spec→signal translator is the next
upgrade — likely an LLM call in P3 itself or a structured-spec schema
extension in P2.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from .data_fetcher import fetch_universe
from .schemas import BacktestResult, StrategySpec
from .signal_handlers import positions_for_spec

# Sane defaults for the simplified signal translation
FAST_SMA = 50
SLOW_SMA = 200
HOLDING_DAYS_PER_TRADE = 21  # ~monthly
COST_BPS_ROUND_TRIP = 5.0


def _stub_metrics(spec_id: str) -> dict:
    """Fallback when data fetch fails. Deterministic, clearly marked."""
    h = hashlib.md5(spec_id.encode()).digest()
    return {
        "pf": round(0.8 + (h[0] / 255) * 1.4, 2),
        "wr": round(35.0 + (h[1] / 255) * 30.0, 1),
        "mdd": round(8.0 + (h[2] / 255) * 27.0, 1),
        "sharpe": round(-0.3 + (h[3] / 255) * 1.8, 2),
        "n_trades": 40 + (h[4] % 120),
    }


def _backtest_returns(prices: pd.Series, spec_entry_text: str) -> tuple[pd.DataFrame, str]:
    """Long-only backtest, signal type chosen by keyword routing.

    Returns (DataFrame, signal_type_used).
    """
    prices = prices.dropna()
    if len(prices) < SLOW_SMA + 5:
        return pd.DataFrame(), "insufficient_bars"
    pos, sig_type = positions_for_spec(spec_entry_text, prices)
    df = pd.DataFrame({"price": prices, "position": pos.reindex(prices.index).fillna(0)})
    df["price_ret"] = df["price"].pct_change().fillna(0)
    df["gross_return"] = df["position"] * df["price_ret"]
    df["pos_change"] = df["position"].diff().abs().fillna(0)
    df["cost"] = df["pos_change"] * (COST_BPS_ROUND_TRIP / 2.0 / 1e4)
    df["net_return"] = df["gross_return"] - df["cost"]
    df["trade_id"] = (df["position"].diff().abs() > 0).cumsum() * (df["position"] > 0)
    return df, sig_type


def _compute_metrics_from_returns(rets: pd.Series, prices: pd.Series) -> dict:
    """PF / WR / MDD / Sharpe / n_trades from returns series."""
    if rets.empty or rets.std() == 0:
        return {"pf": 0.0, "wr": 0.0, "mdd": 0.0, "sharpe": 0.0, "n_trades": 0}

    # Equity curve
    equity = (1 + rets).cumprod()
    peak = equity.cummax()
    drawdown = (equity - peak) / peak
    mdd_pct = abs(drawdown.min()) * 100.0

    # Annualized Sharpe (daily rets)
    sharpe = float((rets.mean() / rets.std()) * np.sqrt(252))

    # PF / WR / n_trades — group returns by trade_id from caller's df
    # caller passes the per-day rets; for trade-level metrics we need
    # holding-period chunks. Approximate: each holding-period block.
    chunks = []
    pos_run_rets: list[float] = []
    for r in rets.values:
        if r != 0:
            pos_run_rets.append(r)
        else:
            if pos_run_rets:
                chunks.append(float(np.prod([1 + x for x in pos_run_rets]) - 1))
                pos_run_rets = []
    if pos_run_rets:
        chunks.append(float(np.prod([1 + x for x in pos_run_rets]) - 1))

    wins = [c for c in chunks if c > 0]
    losses = [c for c in chunks if c < 0]
    n_trades = len(wins) + len(losses)
    gross_win = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    pf = (gross_win / gross_loss) if gross_loss > 1e-9 else (gross_win * 100 if gross_win else 0.0)
    wr = (100.0 * len(wins) / n_trades) if n_trades else 0.0

    return {
        "pf": round(pf, 2),
        "wr": round(wr, 1),
        "mdd": round(mdd_pct, 1),
        "sharpe": round(sharpe, 2),
        "n_trades": int(n_trades),
    }


def _walk_forward_metrics(rets: pd.Series, prices: pd.Series, n_folds: int = 5) -> list[dict]:
    """Split returns into n equal-time folds; per-fold metrics."""
    folds: list[dict] = []
    if rets.empty:
        return folds
    n = len(rets)
    chunk = n // n_folds
    if chunk < 30:
        return folds  # too short for meaningful folds
    for i in range(n_folds):
        start = i * chunk
        end = (i + 1) * chunk if i < n_folds - 1 else n
        sub_rets = rets.iloc[start:end]
        sub_prices = prices.iloc[start:end]
        if sub_rets.empty:
            continue
        m = _compute_metrics_from_returns(sub_rets, sub_prices)
        folds.append({
            "fold": i + 1,
            "start": str(sub_rets.index[0])[:10],
            "end": str(sub_rets.index[-1])[:10],
            **m,
        })
    return folds


def run_candidate(spec: StrategySpec, walk_forward: bool = True) -> BacktestResult:
    """Run real backtest on spec's primary ETF using simplified SMA-crossover.

    Falls back to stub metrics if data fetch fails (no internet, ticker
    delisted, etc.).
    """
    if not spec.universe:
        m = _stub_metrics(spec.spec_id)
        return BacktestResult(
            spec_id=spec.spec_id,
            **m,
            data_window_start="",
            data_window_end="",
            cost_assumption="N/A (empty universe → stub fallback)",
            notes="STUB — spec has empty universe, no real backtest possible.",
        )

    primary = spec.universe[0]
    prices_df = fetch_universe([primary], period="5y")
    if prices_df.empty or primary not in prices_df.columns:
        m = _stub_metrics(spec.spec_id)
        return BacktestResult(
            spec_id=spec.spec_id,
            **m,
            data_window_start="",
            data_window_end="",
            cost_assumption="N/A (data fetch failed → stub fallback)",
            notes=f"STUB — yfinance fetch failed for {primary}. Numbers are deterministic from spec_id hash.",
        )

    prices = prices_df[primary].dropna()
    bt_df, sig_type = _backtest_returns(prices, spec.entry)
    if bt_df.empty:
        m = _stub_metrics(spec.spec_id)
        return BacktestResult(
            spec_id=spec.spec_id,
            **m,
            data_window_start="",
            data_window_end="",
            cost_assumption="N/A (insufficient bars → stub fallback)",
            notes=f"STUB — only {len(prices)} bars for {primary}, need {SLOW_SMA + 5}+. signal_type={sig_type}",
        )

    rets = bt_df["net_return"]
    metrics = _compute_metrics_from_returns(rets, prices)
    folds = _walk_forward_metrics(rets, prices) if walk_forward else []

    return BacktestResult(
        spec_id=spec.spec_id,
        pf=metrics["pf"],
        wr=metrics["wr"],
        mdd=metrics["mdd"],
        sharpe=metrics["sharpe"],
        n_trades=metrics["n_trades"],
        walk_forward_folds=folds,
        data_window_start=str(prices.index[0])[:10],
        data_window_end=str(prices.index[-1])[:10],
        cost_assumption=f"{COST_BPS_ROUND_TRIP:.1f}bp round-trip per leg",
        notes=(
            f"v3a REAL — yfinance prices for {primary} ({len(prices)} bars). "
            f"Signal: {sig_type} (keyword-routed from spec.entry). "
            f"LLM-driven signal translation queued for v3b."
        ),
    )


def run_all(specs: list[StrategySpec]) -> list[BacktestResult]:
    return [run_candidate(s) for s in specs]
