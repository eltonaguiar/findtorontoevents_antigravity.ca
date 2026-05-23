#!/usr/bin/env python3
"""
Multi-Symbol Backtest Runner
=============================

Tests baby strategies across ALL available symbols in crypto_data.db,
not just BTC/USDT. Produces per-strategy-per-symbol results and updates:
1. TIER1_STRATEGIES validation_stats in forward_signal_scanner.py
2. MySQL at_strategy_symbol_performance table
3. JSON results file for analysis

Usage:
    python incubator/backtest_team/multi_symbol_backtest.py [--max N] [--symbols SYM1,SYM2]
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import sqlite3
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "crypto_data.db"
BABY_DIR = ROOT / "baby_strategies"
RESULTS_DIR = ROOT / "incubator" / "backtest_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Strategy files to test (class_name -> file_path)
BABY_STRATEGY_FILES = {
    "ADXTrendStrengthRSIStrategy": "baby_strategies/adx_trend_rsi.py",
    "ConnorsR4MeanReversionStrategy": "baby_strategies/connors_r4_mean_reversion.py",
    "CorrEltonNetConsensusStrategy": "baby_strategies/corr_elton_net_consensus.py",
    "CorrHmaEltonConfluenceStrategy": "baby_strategies/corr_hma_elton_confluence.py",
    "CorrHmaTrendStrategy": "baby_strategies/corr_hma_trend.py",
    "CorrKamaAdaptiveStrategy": "baby_strategies/corr_kama_adaptive.py",
    "CorrKamaRsiTrendStrategy": "baby_strategies/corr_kama_rsi_trend.py",
    "CorrRsiMomentumStrategy": "baby_strategies/corr_rsi_momentum.py",
    "CorrTripleCrownStrategy": "baby_strategies/corr_triple_crown.py",
    "CorrVwapReversionStrategy": "baby_strategies/corr_vwap_reversion.py",
    "CorrVwapZscoreReversionStrategy": "baby_strategies/corr_vwap_zscore_reversion.py",
    "CorrZscoreExtremeStrategy": "baby_strategies/corr_zscore_extreme.py",
    "FRADXRegimeStrategy": "baby_strategies/fr_adx_regime.py",
    "FRBaseReversalStrategy": "baby_strategies/fr_base_reversal.py",
    "FRFullConfluenceStrategy": "baby_strategies/fr_full_confluence.py",
    "FRLiquidityFilteredStrategy": "baby_strategies/fr_liquidity_filtered.py",
    "FRMTFAlignedStrategy": "baby_strategies/fr_mtf_aligned.py",
    "FRPullbackEntryStrategy": "baby_strategies/fr_pullback_entry.py",
    "FRRSIDivergenceStrategy": "baby_strategies/fr_rsi_divergence.py",
    "FRVolumeSpikeStrategy": "baby_strategies/fr_volume_spike.py",
    "FibRSIDivergenceStrategy": "baby_strategies/fib_rsi_divergence.py",
    "IRBHoffmanStrategy": "baby_strategies/irb_hoffman.py",
    "KeltnerChannelReversionStrategy": "baby_strategies/keltner_channel_reversion.py",
    "KeltnerRSIConfluenceStrategy": "baby_strategies/keltner_rsi_confluence.py",
    "KimiEma60040MomentumStrategy": "baby_strategies/kimi_ema600_40_momentum.py",
    "KimiLgbmFeatureProxyStrategy": "baby_strategies/kimi_lgbm_features.py",
    "KimiVolatilityMomentumBlendStrategy": "baby_strategies/kimi_volatility_momentum_blend.py",
    "KimiVpinReversionStrategy": "baby_strategies/kimi_vpin_reversion.py",
    "MLEnsembleStrategy": "baby_strategies/ml_ensemble_strategy.py",
    "MercuryAggressiveStrategy": "baby_strategies/mercury_aggressive.py",
    "MercuryConservativeStrategy": "baby_strategies/mercury_conservative.py",
    "MercuryFundingEnhancedStrategy": "baby_strategies/mercury_funding_enhanced.py",
    "MercuryHmaFilteredStrategy": "baby_strategies/mercury_hma_filtered.py",
    "MercuryVolCrossoverStrategy": "baby_strategies/mercury_vol_crossover.py",
    "ProtectiveMomentumStrategy": "baby_strategies/protective_momentum.py",
    "SimpletonMercuryHybridStrategy": "baby_strategies/simpleton_mercury_hybrid.py",
    "SimpletonTrendReversalStrategy": "baby_strategies/simpleton_trend_reversal.py",
    "StochasticRSIDivergenceStrategy": "baby_strategies/stochastic_rsi_divergence.py",
    "SuperTrendMultiTimeframeStrategy": "baby_strategies/supertrend_multi_timeframe.py",
    "TripleConfirmationStrategy": "baby_strategies/triple_confirmation.py",
    "UltimateOmniscientStrategy": "baby_strategies/strategy_ultimate_omniscient_v1.py",
    "VerifiedBtc50maMomentumStrategy": "baby_strategies/verified_btc_50ma_momentum.py",
    "VerifiedDonchianTurtleStrategy": "baby_strategies/verified_donchian_turtle.py",
    "VerifiedEmaStackStrategy": "baby_strategies/verified_ema_stack.py",
    "VerifiedKeltnerBreakoutStrategy": "baby_strategies/verified_keltner_breakout.py",
    "VerifiedStochRsiStrategy": "baby_strategies/verified_stoch_rsi.py",
    "VerifiedSupertrendAiStrategy": "baby_strategies/verified_supertrend_ai.py",
    "VerifiedWavetrendStrategy": "baby_strategies/verified_wavetrend.py",
    "VerifiedWilliamsRStrategy": "baby_strategies/verified_williams_r.py",
    "VolScaledKeltnerStrategy": "baby_strategies/vol_scaled_keltner.py",
    "WilliamsPercentRExtremeStrategy": "baby_strategies/williams_percent_r_extreme.py",
    "WorldClassEnsembleStrategy": "baby_strategies/strategy_999_worldclass_ensemble.py",
}

# Core symbols to test every strategy on
CORE_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
# Extended symbols for strategies that pass on core
EXTENDED_SYMBOLS = [
    "XRP/USDT", "DOGE/USDT", "DOT/USDT", "ARB/USDT",
    "INJ/USDT", "FET/USDT", "SHIB/USDT", "DYDX/USDT",
    "TRX/USDT", "APE/USDT", "ALGO/USDT",
]


@dataclass
class Trade:
    entry_time: str
    exit_time: str
    direction: str
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    exit_reason: str
    bars_held: int


@dataclass
class SymbolResult:
    symbol: str
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    total_pnl_pct: float = 0.0
    avg_pnl_pct: float = 0.0
    sharpe: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    best_trade_pct: float = 0.0
    worst_trade_pct: float = 0.0
    trades: List[Trade] = field(default_factory=list)


@dataclass
class StrategyResult:
    strategy_name: str
    class_name: str
    file_path: str
    status: str = "pending"
    error_message: str = ""
    symbol_results: Dict[str, SymbolResult] = field(default_factory=dict)
    # Aggregate stats
    total_trades: int = 0
    total_wins: int = 0
    overall_win_rate: float = 0.0
    overall_sharpe: float = 0.0
    overall_pnl_pct: float = 0.0
    symbols_profitable: int = 0
    symbols_tested: int = 0
    best_symbol: str = ""
    best_symbol_sharpe: float = 0.0
    passed_symbols: List[str] = field(default_factory=list)


def load_pair_data(pair: str, db_path: Path) -> pd.DataFrame:
    """Load OHLCV data for a specific pair."""
    query = """
    SELECT pair, timestamp, open, high, low, close, volume
    FROM klines WHERE pair = ? ORDER BY timestamp ASC
    """
    with sqlite3.connect(str(db_path)) as conn:
        df = pd.read_sql_query(query, conn, params=[pair])
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["timestamp", "open", "high", "low", "close", "volume"])
    return df.sort_values("timestamp").reset_index(drop=True)


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    x = df.set_index("timestamp")
    y = x.resample(rule).agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum",
    }).dropna()
    return y.reset_index()


def expand_to_subhour(df: pd.DataFrame, step_minutes: int) -> pd.DataFrame:
    rows = []
    n = int(60 / step_minutes)
    for _, r in df.iterrows():
        ts, o, c, h, l, v = r["timestamp"], float(r["open"]), float(r["close"]), float(r["high"]), float(r["low"]), float(r["volume"])
        for i in range(n):
            frac = (i + 1) / n
            px = o + (c - o) * frac
            rows.append({
                "timestamp": ts + pd.Timedelta(minutes=i * step_minutes),
                "open": px, "high": max(px * 1.0008, l, px), "low": min(px * 0.9992, h, px),
                "close": px, "volume": v / n,
            })
    return pd.DataFrame(rows)


def build_context(ohlcv: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """Build the full context dict that strategies expect."""
    ret = ohlcv["close"].pct_change().fillna(0.0)
    vol = ret.rolling(24).std().fillna(0.0)

    # Synthetic correlated data
    spx_ret = 0.35 * ret + 0.65 * ret.rolling(6, min_periods=1).mean() + 0.00005
    dxy_ret = -0.25 * ret + 0.75 * (-ret).rolling(6, min_periods=1).mean() + 0.00002
    spx_close = 4500 * (1 + spx_ret).cumprod()
    dxy_close = 100 * (1 + dxy_ret).cumprod()
    vix_close = 16 + (vol * 1200).clip(0, 35)

    def _make_ohlcv(close_s, spread_h=0.003, spread_l=0.003, vol_val=1_000_000):
        return pd.DataFrame({
            "timestamp": ohlcv["timestamp"],
            "open": close_s * (1 - spread_l * 0.3),
            "high": close_s * (1 + spread_h),
            "low": close_s * (1 - spread_l),
            "close": close_s,
            "volume": vol_val,
        })

    spx = _make_ohlcv(spx_close, vol_val=1_000_000 + ohlcv["volume"].rolling(8, min_periods=1).mean() * 40)
    dxy = _make_ohlcv(dxy_close, 0.001, 0.001, 100_000)
    vix = _make_ohlcv(vix_close, 0.01, 0.01, 10_000)
    ratio_close = (spx_close / ohlcv["close"]).replace([np.inf, -np.inf], np.nan).ffill()
    ratio = _make_ohlcv(ratio_close, 0.002, 0.002, 1.0)

    flow = pd.Series((-ret * 1800).rolling(4, min_periods=1).mean().values, index=ohlcv["timestamp"], name="flow")
    whale_inflow = pd.Series(
        (ohlcv["volume"] * ohlcv["close"] * 0.001).rolling(8, min_periods=1).mean().values,
        index=ohlcv["timestamp"], name="whale_inflow",
    )
    funding = pd.Series(np.tanh(ret.rolling(8, min_periods=1).mean().values * 50) * 0.01, index=ohlcv["timestamp"], name="funding")
    gov = pd.Series((100 + (ohlcv["volume"].pct_change().fillna(0) * 400).clip(-80, 80)).values, index=ohlcv["timestamp"], name="gov")
    social = pd.Series((500 + (ret.abs() * 8000)).values, index=ohlcv["timestamp"], name="social")
    liquidation = pd.DataFrame({
        "timestamp": ohlcv["timestamp"],
        "usd_value": ((ret.abs() * ohlcv["volume"] * ohlcv["close"]) * 0.08).fillna(0.0),
    })

    # Normalize symbol for strategies expecting BTCUSDT format
    sym_norm = symbol.replace("/", "")

    return {
        "btc": ohlcv,
        "btc_1h": ohlcv,
        "btc_4h": resample_ohlcv(ohlcv, "4h"),
        "btc_15m": expand_to_subhour(ohlcv, 15),
        "btc_5m": expand_to_subhour(ohlcv, 5),
        "spx": spx,
        "dxy": dxy,
        "vix": vix,
        "spxbtc_ratio": ratio,
        "flow": flow,
        "whale_inflow": whale_inflow,
        "funding": funding,
        "gov": gov,
        "social": social,
        "liquidation": liquidation,
        "symbol": sym_norm,
    }


def load_strategy_class(py_file: Path, target_class: str = None) -> Tuple[Optional[type], Optional[str]]:
    """Load strategy class from file. If target_class given, look for that specific class."""
    try:
        name = f"msweep_{py_file.stem}_{int(time.time_ns() % 1_000_000)}"
        spec = importlib.util.spec_from_file_location(name, py_file)
        if spec is None or spec.loader is None:
            return None, "spec loader unavailable"
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Prefer target class
        if target_class and hasattr(mod, target_class):
            cls = getattr(mod, target_class)
            if isinstance(cls, type):
                return cls, None

        # Fallback: find any *Strategy class
        for k in dir(mod):
            v = getattr(mod, k)
            if isinstance(v, type) and k.endswith("Strategy") and k != "Strategy":
                return v, None
        return None, "No Strategy class found"
    except Exception as exc:
        return None, f"Import error: {exc}"


def infer_side(direction) -> Optional[str]:
    if direction is None:
        return None
    d = str(direction).upper().strip()
    if d == "EXIT":
        return None
    if d.startswith("BUY") or d.startswith("LONG"):
        return "BUY"
    if d.startswith("SELL") or d.startswith("SHORT"):
        return "SELL"
    if "BUY" in d or ("LONG" in d and "SHORT" not in d):
        return "BUY"
    if "SELL" in d or ("SHORT" in d and "LONG" not in d):
        return "SELL"
    return None


def slice_df(df: pd.DataFrame, ts: pd.Timestamp) -> pd.DataFrame:
    return df[df["timestamp"] <= ts].copy()


def slice_series(s: pd.Series, ts: pd.Timestamp) -> pd.Series:
    return s[s.index <= ts].copy()


def build_kwargs(param_names: List[str], ctx: Dict, ts: pd.Timestamp, equity: float) -> Dict[str, Any]:
    kwargs = {}
    for p in param_names:
        if p == "symbol":
            kwargs[p] = ctx["symbol"]
        elif p in ("data", "btc_data", "data_1h"):
            kwargs[p] = slice_df(ctx["btc"], ts)
        elif p == "data_4h":
            kwargs[p] = slice_df(ctx["btc_4h"], ts)
        elif p == "data_5m":
            kwargs[p] = slice_df(ctx["btc_5m"], ts)
        elif p == "data_15m":
            kwargs[p] = slice_df(ctx["btc_15m"], ts)
        elif p == "spx_data":
            kwargs[p] = slice_df(ctx["spx"], ts)
        elif p == "dxy_data":
            kwargs[p] = slice_df(ctx["dxy"], ts)
        elif p == "vix_data":
            kwargs[p] = slice_df(ctx["vix"], ts)
        elif p == "flow_data":
            kwargs[p] = slice_series(ctx["flow"], ts)
        elif p == "whale_inflow":
            kwargs[p] = slice_series(ctx["whale_inflow"], ts)
        elif p == "funding_rate":
            fs = slice_series(ctx["funding"], ts)
            kwargs[p] = float(fs.iloc[-1]) if len(fs) else 0.0
        elif p == "gov_data":
            kwargs[p] = slice_series(ctx["gov"], ts)
        elif p == "social_data":
            kwargs[p] = slice_series(ctx["social"], ts)
        elif p == "liquidation_data":
            kwargs[p] = slice_df(ctx["liquidation"], ts)
        elif p == "account_balance":
            kwargs[p] = float(equity)
        else:
            kwargs[p] = None
    return kwargs


def simulate_trade(signal, entry_idx: int, exec_df: pd.DataFrame,
                   max_hold_bars: int = 20, commission: float = 0.001) -> Optional[Trade]:
    side = infer_side(getattr(signal, "direction", None))
    if side is None:
        return None
    try:
        entry = float(getattr(signal, "entry_price"))
        tp = float(getattr(signal, "take_profit"))
        sl = float(getattr(signal, "stop_loss"))
    except Exception:
        return None
    if entry <= 0:
        return None

    if entry_idx >= len(exec_df) - 1:
        return None

    entry_time = pd.to_datetime(exec_df.iloc[entry_idx]["timestamp"], utc=True).isoformat()
    last_idx = min(entry_idx + max_hold_bars, len(exec_df) - 1)

    for i in range(entry_idx + 1, last_idx + 1):
        px = float(exec_df.iloc[i]["close"])
        exit_time = pd.to_datetime(exec_df.iloc[i]["timestamp"], utc=True).isoformat()
        bars_held = i - entry_idx

        if side == "BUY":
            if px >= tp:
                return Trade(entry_time, exit_time, "LONG", entry, tp, (tp - entry) * 0.1 * (1 - commission), (tp - entry) / entry, "TP", bars_held)
            if px <= sl:
                return Trade(entry_time, exit_time, "LONG", entry, sl, (sl - entry) * 0.1 * (1 - commission), (sl - entry) / entry, "SL", bars_held)
        else:
            if px <= tp:
                return Trade(entry_time, exit_time, "SHORT", entry, tp, (entry - tp) * 0.1 * (1 - commission), (entry - tp) / entry, "TP", bars_held)
            if px >= sl:
                return Trade(entry_time, exit_time, "SHORT", entry, sl, (entry - sl) * 0.1 * (1 - commission), (entry - sl) / entry, "SL", bars_held)

    px = float(exec_df.iloc[last_idx]["close"])
    exit_time = pd.to_datetime(exec_df.iloc[last_idx]["timestamp"], utc=True).isoformat()
    bars_held = last_idx - entry_idx
    if side == "BUY":
        pnl_pct = (px - entry) / entry
    else:
        pnl_pct = (entry - px) / entry
    return Trade(entry_time, exit_time, side, entry, px, pnl_pct * entry * 0.1 * (1 - commission), pnl_pct, "TIME", bars_held)


def compute_metrics(trades: List[Trade]) -> Dict[str, float]:
    """Compute strategy metrics from trade list."""
    if not trades:
        return {"sharpe": 0.0, "win_rate": 0.0, "max_drawdown": 0.0, "profit_factor": 0.0, "total_pnl_pct": 0.0}

    pnls = np.array([t.pnl_pct for t in trades])
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]

    win_rate = float((pnls > 0).mean())
    gp = float(wins.sum()) if len(wins) else 0.0
    gl = float(abs(losses.sum())) if len(losses) else 0.0
    pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)

    eq = 10_000.0
    curve = [eq]
    for p in pnls:
        eq *= (1 + p)
        curve.append(eq)

    peak = curve[0]
    max_dd = 0.0
    for e in curve:
        if e > peak:
            peak = e
        dd = (peak - e) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

    ret = np.diff(curve) / np.array(curve[:-1])
    sharpe = 0.0
    if len(ret) > 1 and np.std(ret) > 0:
        sharpe = float(np.mean(ret) / np.std(ret) * np.sqrt(252))

    return {
        "sharpe": round(sharpe, 3),
        "win_rate": round(win_rate, 4),
        "max_drawdown": round(max_dd, 4),
        "profit_factor": round(min(pf, 999), 3),
        "total_pnl_pct": round(float(pnls.sum()), 4),
    }


def run_strategy_on_symbol(
    strategy_cls: type,
    ohlcv: pd.DataFrame,
    symbol: str,
    min_bars: int = 80,
    bar_step: int = 2,
    max_hold_bars: int = 20,
    timeout_sec: int = 30,
) -> SymbolResult:
    """Run a single strategy against a single symbol's data."""
    result = SymbolResult(symbol=symbol)
    ctx = build_context(ohlcv, symbol)
    sym_norm = symbol.replace("/", "")

    try:
        strategy = strategy_cls()
    except Exception:
        try:
            strategy = strategy_cls(symbol=sym_norm)
        except Exception:
            return result

    # Find generate_signals method
    gen_method = None
    for method_name in ("generate_signals", "generate_signal", "scan", "run"):
        if hasattr(strategy, method_name):
            gen_method = getattr(strategy, method_name)
            break
    if gen_method is None:
        return result

    params = list(inspect.signature(gen_method).parameters.keys())
    start_time = time.time()

    for idx in range(min_bars, len(ohlcv), bar_step):
        if time.time() - start_time > timeout_sec:
            break

        ts = ohlcv.iloc[idx]["timestamp"]
        kwargs = build_kwargs(params, ctx, ts, 10_000.0)

        try:
            raw = gen_method(**kwargs)
        except Exception:
            continue

        signals = raw if isinstance(raw, list) else ([] if raw is None else [raw])
        for sig in signals:
            if isinstance(sig, dict):
                sig = SimpleNamespace(**sig)
            if sig is None:
                continue
            if infer_side(getattr(sig, "direction", None)) is None:
                continue

            trade = simulate_trade(sig, idx, ohlcv, max_hold_bars)
            if trade is not None:
                result.trades.append(trade)

    # Compute metrics
    if result.trades:
        metrics = compute_metrics(result.trades)
        result.total_trades = len(result.trades)
        result.wins = sum(1 for t in result.trades if t.pnl_pct > 0)
        result.losses = result.total_trades - result.wins
        result.win_rate = metrics["win_rate"]
        result.total_pnl_pct = metrics["total_pnl_pct"]
        result.avg_pnl_pct = result.total_pnl_pct / result.total_trades if result.total_trades else 0.0
        result.sharpe = metrics["sharpe"]
        result.profit_factor = metrics["profit_factor"]
        result.max_drawdown = metrics["max_drawdown"]
        pnls = [t.pnl_pct for t in result.trades]
        result.best_trade_pct = max(pnls)
        result.worst_trade_pct = min(pnls)

    return result


def run_full_sweep(
    symbols: List[str] = None,
    max_strategies: int = 0,
    timeout_per_symbol: int = 30,
) -> List[StrategyResult]:
    """Run all strategies across all symbols."""
    if symbols is None:
        symbols = CORE_SYMBOLS + EXTENDED_SYMBOLS

    # Load all symbol data upfront
    print(f"Loading market data for {len(symbols)} symbols...")
    symbol_data = {}
    for sym in symbols:
        df = load_pair_data(sym, DB_PATH)
        if not df.empty:
            symbol_data[sym] = df
            print(f"  {sym}: {len(df)} bars")
        else:
            print(f"  {sym}: NO DATA — skipping")

    if not symbol_data:
        print("ERROR: No market data available!")
        return []

    strategies_to_test = list(BABY_STRATEGY_FILES.items())
    if max_strategies > 0:
        strategies_to_test = strategies_to_test[:max_strategies]

    results = []
    total = len(strategies_to_test)

    for i, (class_name, file_rel) in enumerate(strategies_to_test, 1):
        file_path = ROOT / file_rel
        print(f"\n[{i}/{total}] {class_name} ({file_path.name})")

        strat_result = StrategyResult(
            strategy_name=file_path.stem,
            class_name=class_name,
            file_path=file_rel,
        )

        # Load strategy class
        cls, err = load_strategy_class(file_path, class_name)
        if cls is None:
            strat_result.status = "error"
            strat_result.error_message = err or "Failed to load"
            print(f"  ERROR: {err}")
            results.append(strat_result)
            continue

        # Test on core symbols first
        core_passed = False
        for sym in CORE_SYMBOLS:
            if sym not in symbol_data:
                continue
            print(f"  Testing on {sym}...", end=" ", flush=True)
            try:
                sym_result = run_strategy_on_symbol(
                    cls, symbol_data[sym], sym, timeout_sec=timeout_per_symbol,
                )
                strat_result.symbol_results[sym] = sym_result
                print(f"{sym_result.total_trades} trades, WR={sym_result.win_rate:.1%}, Sharpe={sym_result.sharpe:.2f}")
                if sym_result.total_trades >= 3 and sym_result.sharpe > 0:
                    core_passed = True
            except Exception as e:
                print(f"ERROR: {e}")
                strat_result.symbol_results[sym] = SymbolResult(symbol=sym)

        # If passed on any core symbol, test extended symbols
        if core_passed:
            for sym in EXTENDED_SYMBOLS:
                if sym not in symbol_data:
                    continue
                print(f"  Testing on {sym}...", end=" ", flush=True)
                try:
                    sym_result = run_strategy_on_symbol(
                        cls, symbol_data[sym], sym, timeout_sec=timeout_per_symbol,
                    )
                    strat_result.symbol_results[sym] = sym_result
                    print(f"{sym_result.total_trades} trades, WR={sym_result.win_rate:.1%}, Sharpe={sym_result.sharpe:.2f}")
                except Exception as e:
                    print(f"ERROR: {e}")

        # Aggregate stats
        all_trades = []
        profitable_syms = 0
        best_sharpe = -999
        best_sym = ""
        passed_syms = []

        for sym, sr in strat_result.symbol_results.items():
            all_trades.extend(sr.trades)
            if sr.total_trades >= 2 and sr.total_pnl_pct > 0:
                profitable_syms += 1
            if sr.sharpe > best_sharpe and sr.total_trades >= 2:
                best_sharpe = sr.sharpe
                best_sym = sym
            if sr.total_trades >= 3 and sr.sharpe > 0:
                passed_syms.append(sym.replace("/", ""))

        strat_result.total_trades = len(all_trades)
        strat_result.total_wins = sum(1 for t in all_trades if t.pnl_pct > 0)
        strat_result.overall_win_rate = strat_result.total_wins / strat_result.total_trades if strat_result.total_trades else 0
        strat_result.symbols_profitable = profitable_syms
        strat_result.symbols_tested = len(strat_result.symbol_results)
        strat_result.best_symbol = best_sym
        strat_result.best_symbol_sharpe = max(best_sharpe, 0)
        strat_result.passed_symbols = passed_syms

        if all_trades:
            metrics = compute_metrics(all_trades)
            strat_result.overall_sharpe = metrics["sharpe"]
            strat_result.overall_pnl_pct = metrics["total_pnl_pct"]

        if strat_result.total_trades >= 5 and strat_result.overall_sharpe > 0:
            strat_result.status = "passed"
        elif strat_result.total_trades == 0:
            strat_result.status = "no_trades"
        else:
            strat_result.status = "failed"

        print(f"  => {strat_result.status.upper()}: {strat_result.total_trades} total trades, "
              f"Sharpe={strat_result.overall_sharpe:.2f}, WR={strat_result.overall_win_rate:.1%}, "
              f"profitable on {profitable_syms}/{strat_result.symbols_tested} symbols, "
              f"passed: {passed_syms}")

        results.append(strat_result)

    return results


def save_results(results: List[StrategyResult]) -> str:
    """Save results to JSON file."""
    now = datetime.now(timezone.utc)
    out_file = RESULTS_DIR / f"multi_symbol_sweep_{now.strftime('%Y%m%d_%H%M%S')}.json"

    data = {
        "run_at": now.isoformat(),
        "total_tested": len(results),
        "passed": sum(1 for r in results if r.status == "passed"),
        "failed": sum(1 for r in results if r.status == "failed"),
        "no_trades": sum(1 for r in results if r.status == "no_trades"),
        "errors": sum(1 for r in results if r.status == "error"),
        "results": [],
    }

    for r in results:
        entry = {
            "strategy_name": r.strategy_name,
            "class_name": r.class_name,
            "file_path": r.file_path,
            "status": r.status,
            "error_message": r.error_message,
            "total_trades": r.total_trades,
            "total_wins": r.total_wins,
            "overall_win_rate": r.overall_win_rate,
            "overall_sharpe": r.overall_sharpe,
            "overall_pnl_pct": r.overall_pnl_pct,
            "symbols_profitable": r.symbols_profitable,
            "symbols_tested": r.symbols_tested,
            "best_symbol": r.best_symbol,
            "best_symbol_sharpe": r.best_symbol_sharpe,
            "passed_symbols": r.passed_symbols,
            "per_symbol": {},
        }
        for sym, sr in r.symbol_results.items():
            entry["per_symbol"][sym] = {
                "total_trades": sr.total_trades,
                "wins": sr.wins,
                "losses": sr.losses,
                "win_rate": sr.win_rate,
                "total_pnl_pct": sr.total_pnl_pct,
                "avg_pnl_pct": sr.avg_pnl_pct,
                "sharpe": sr.sharpe,
                "profit_factor": sr.profit_factor,
                "max_drawdown": sr.max_drawdown,
                "best_trade_pct": sr.best_trade_pct,
                "worst_trade_pct": sr.worst_trade_pct,
            }
        data["results"].append(entry)

    with open(out_file, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"\nResults saved to {out_file}")
    return str(out_file)


def store_to_mysql(results: List[StrategyResult]):
    """Store results to MySQL at_strategy_symbol_performance table."""
    try:
        import pymysql
    except ImportError:
        print("pymysql not installed — skipping MySQL store")
        return

    host = os.environ.get("MYSQL_HOST") or "mysql.50webs.com"
    user = os.environ.get("MYSQL_USER") or "ejaguiar1_stocks"
    password = os.environ.get("MYSQL_PASSWORD") or "stocks"
    database = os.environ.get("MYSQL_DB") or "ejaguiar1_stocks"

    try:
        conn = pymysql.connect(host=host, user=user, password=password, database=database, charset="utf8mb4", connect_timeout=10)
    except Exception as e:
        print(f"MySQL connection failed: {e}")
        return

    cur = conn.cursor()

    # Ensure table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS at_strategy_symbol_performance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            strategy_name VARCHAR(100) NOT NULL,
            display_name VARCHAR(200),
            symbol VARCHAR(20) NOT NULL,
            portfolio_type VARCHAR(50),
            total_trades INT DEFAULT 0,
            wins INT DEFAULT 0,
            win_rate DECIMAL(5,2) DEFAULT 0,
            avg_pnl_pct DECIMAL(8,4) DEFAULT 0,
            profit_factor DECIMAL(8,3) DEFAULT 0,
            sharpe DECIMAL(8,3) DEFAULT 0,
            max_drawdown_pct DECIMAL(8,4) DEFAULT 0,
            best_trade_pct DECIMAL(8,4) DEFAULT 0,
            worst_trade_pct DECIMAL(8,4) DEFAULT 0,
            test_interval VARCHAR(10) DEFAULT '1h',
            test_bars INT DEFAULT 500,
            is_catered TINYINT(1) DEFAULT 0,
            tested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_strat_sym (strategy_name, symbol, test_interval)
        )
    """)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows = 0

    for r in results:
        if r.status == "error":
            continue

        for sym, sr in r.symbol_results.items():
            sym_short = sym.replace("/", "")
            is_catered = 1 if sr.win_rate >= 0.50 and sr.total_trades >= 3 else 0
            try:
                cur.execute("""
                    INSERT INTO at_strategy_symbol_performance
                    (strategy_name, display_name, symbol, portfolio_type, total_trades, wins,
                     win_rate, avg_pnl_pct, profit_factor, sharpe, max_drawdown_pct,
                     best_trade_pct, worst_trade_pct, is_catered, test_interval, test_bars, tested_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        total_trades = VALUES(total_trades), wins = VALUES(wins),
                        win_rate = VALUES(win_rate), avg_pnl_pct = VALUES(avg_pnl_pct),
                        profit_factor = VALUES(profit_factor), sharpe = VALUES(sharpe),
                        max_drawdown_pct = VALUES(max_drawdown_pct),
                        best_trade_pct = VALUES(best_trade_pct), worst_trade_pct = VALUES(worst_trade_pct),
                        is_catered = VALUES(is_catered), tested_at = VALUES(tested_at)
                """, (r.class_name, r.class_name, sym_short, "baby_strategies",
                      sr.total_trades, sr.wins,
                      round(sr.win_rate * 100, 2), round(sr.avg_pnl_pct * 100, 4),
                      sr.profit_factor, sr.sharpe, round(sr.max_drawdown * 100, 4),
                      round(sr.best_trade_pct * 100, 4), round(sr.worst_trade_pct * 100, 4),
                      is_catered, "1h", 1969, now))
                rows += 1
            except Exception as e:
                print(f"  MySQL error for {r.class_name}/{sym_short}: {e}")

        # Overall row
        if r.total_trades > 0:
            try:
                cur.execute("""
                    INSERT INTO at_strategy_symbol_performance
                    (strategy_name, display_name, symbol, portfolio_type, total_trades, wins,
                     win_rate, avg_pnl_pct, sharpe, is_catered, test_interval, test_bars, tested_at)
                    VALUES (%s, %s, 'ALL', %s, %s, %s, %s, %s, %s, 0, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        total_trades = VALUES(total_trades), wins = VALUES(wins),
                        win_rate = VALUES(win_rate), avg_pnl_pct = VALUES(avg_pnl_pct),
                        sharpe = VALUES(sharpe), tested_at = VALUES(tested_at)
                """, (r.class_name, r.class_name, "baby_strategies",
                      r.total_trades, r.total_wins,
                      round(r.overall_win_rate * 100, 2),
                      round(r.overall_pnl_pct / r.total_trades * 100, 4) if r.total_trades else 0,
                      r.overall_sharpe, "1h", 1969, now))
                rows += 1
            except Exception as e:
                print(f"  MySQL error for {r.class_name}/ALL: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"Stored {rows} rows in MySQL at_strategy_symbol_performance")


def update_tier1_registry(results: List[StrategyResult]):
    """Update TIER1_STRATEGIES validation_stats with real backtest data."""
    scanner_file = ROOT / "incubator" / "backtest_team" / "forward_signal_scanner.py"
    content = scanner_file.read_text(encoding="utf-8")

    updates = 0
    for r in results:
        if r.total_trades == 0:
            continue

        class_name = r.class_name
        # Build per-symbol summary string
        sym_parts = []
        for sym, sr in sorted(r.symbol_results.items()):
            if sr.total_trades > 0:
                sym_short = sym.replace("/", "")
                sym_parts.append(f"{sym_short}: {sr.total_trades}t, {sr.win_rate:.0%} WR, Sharpe {sr.sharpe:.2f}")

        source_line = f"Multi-symbol sweep: {r.total_trades} trades across {r.symbols_tested} symbols"

        # Find and update the validation_stats block for this strategy
        old_marker = f'    "{class_name}": {{\n        "file": "{r.file_path}",'
        if old_marker not in content:
            continue

        # Build new entry
        passed_pairs_list = r.passed_symbols if r.passed_symbols else ["BTCUSDT"]
        best_pair = r.best_symbol.replace("/", "") if r.best_symbol else "BTCUSDT"

        old_block_start = content.index(old_marker)
        # Find the closing },
        depth = 0
        idx = old_block_start + len(f'    "{class_name}": ')
        while idx < len(content):
            if content[idx] == '{':
                depth += 1
            elif content[idx] == '}':
                depth -= 1
                if depth == 0:
                    break
            idx += 1
        # idx is at closing }, find the trailing comma
        end_idx = idx + 1
        if end_idx < len(content) and content[end_idx] == ',':
            end_idx += 1

        old_block = content[old_block_start:end_idx]

        new_block = f'''    "{class_name}": {{
        "file": "{r.file_path}",
        "agent": "baby_strategies",
        "best_pair": "{best_pair}",
        "best_params": {{}},
        "tier1_sharpe": {r.best_symbol_sharpe:.2f},
        "passed_pairs": {json.dumps(passed_pairs_list)},
        "survivor_validated": False,
        "validation_stats": {{
            "source": "{source_line}",
            "total_trades": {r.total_trades},
            "overall_wr": "{r.overall_win_rate:.1%}",
            "overall_sharpe": {r.overall_sharpe:.2f},
            "symbols_profitable": "{r.symbols_profitable}/{r.symbols_tested}",
            "per_symbol": "{'; '.join(sym_parts[:5])}",
        }},
    }},'''

        content = content.replace(old_block, new_block)
        updates += 1

    if updates > 0:
        scanner_file.write_text(content, encoding="utf-8")
        print(f"Updated {updates} entries in TIER1_STRATEGIES")
    else:
        print("No TIER1_STRATEGIES updates needed")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Multi-symbol backtest runner")
    parser.add_argument("--max", type=int, default=0, help="Max strategies to test (0=all)")
    parser.add_argument("--symbols", type=str, default="", help="Comma-separated symbols (empty=all)")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per symbol in seconds")
    parser.add_argument("--skip-mysql", action="store_true", help="Skip MySQL storage")
    parser.add_argument("--skip-registry", action="store_true", help="Skip TIER1_STRATEGIES update")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: crypto_data.db not found at {DB_PATH}")
        sys.exit(1)

    symbols = None
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]

    print("=" * 70)
    print("  MULTI-SYMBOL BABY STRATEGY BACKTEST SWEEP")
    print("=" * 70)
    print(f"  Strategies: {len(BABY_STRATEGY_FILES)}")
    print(f"  Symbols: {len(symbols) if symbols else len(CORE_SYMBOLS) + len(EXTENDED_SYMBOLS)}")
    print(f"  DB: {DB_PATH}")
    print()

    results = run_full_sweep(
        symbols=symbols,
        max_strategies=args.max,
        timeout_per_symbol=args.timeout,
    )

    # Save JSON results
    out_file = save_results(results)

    # Update TIER1_STRATEGIES registry
    if not args.skip_registry:
        update_tier1_registry(results)

    # Store to MySQL
    if not args.skip_mysql:
        store_to_mysql(results)

    # Summary
    print("\n" + "=" * 70)
    print("  SWEEP SUMMARY")
    print("=" * 70)
    passed = [r for r in results if r.status == "passed"]
    failed = [r for r in results if r.status == "failed"]
    no_trades = [r for r in results if r.status == "no_trades"]
    errors = [r for r in results if r.status == "error"]

    print(f"  Passed:    {len(passed)}")
    print(f"  Failed:    {len(failed)}")
    print(f"  No trades: {len(no_trades)}")
    print(f"  Errors:    {len(errors)}")

    if passed:
        print("\n  TOP PERFORMERS:")
        for r in sorted(passed, key=lambda x: x.overall_sharpe, reverse=True)[:10]:
            print(f"    {r.class_name:<45} Sharpe={r.overall_sharpe:.2f}  WR={r.overall_win_rate:.1%}  "
                  f"Trades={r.total_trades}  Symbols={r.symbols_profitable}/{r.symbols_tested}")

    return results


if __name__ == "__main__":
    main()
