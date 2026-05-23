"""Real-data backtest harness for mimo_strategies/ — v2 (corrected).

Supersedes scripts/backtest_mimo_on_real_bars.py, which relies on
`strat['backtest']` — a method that exists in only 1 of the 7 MIMO
strategies. As a result, v1 silently returned 0 trades for 6/7
strategies (see mimo_strategies/backtest_results.json).

v2 uses `generate_signals()` on all strategies (which ALL 7 expose)
and runs a strategy-agnostic position tracker that fixes the 1-bar
exit-lag bug documented in the futures_* strategies.

v2 also uses alpha_engine.scanner.fetch_market_data (multi-endpoint
failover) instead of raw yf.Ticker(), satisfying CLAUDE.md's API
failover rule.

Output: mimo_strategies/backtest_results_v2.json
"""
from __future__ import annotations

import glob
import importlib.util
import json
import os
import sys
import traceback
from datetime import datetime, timezone

import numpy as np
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from alpha_engine import config as app_cfg  # noqa: E402

# NOTE: we deliberately do NOT import alpha_engine.scanner. On Windows,
# importing scanner corrupts sys.stderr when stdout is piped, crashing
# any harness run. MIMO strategies target non-crypto asset classes so
# we use yfinance directly without the Binance failover chain.
import yfinance as yf  # noqa: E402


UNIVERSES: dict[str, list[str]] = {
    "BOND": list(app_cfg.BOND_SYMBOLS.keys()),
    "COMMODITY": list(app_cfg.COMMODITY_SYMBOLS.keys())[:10],
    "COMMODITIES": list(app_cfg.COMMODITY_SYMBOLS.keys())[:10],
    "EQUITY": list(app_cfg.EQUITY_SYMBOLS.keys())[:15],
    "ETF": list(app_cfg.ETF_SYMBOLS.keys()),
    "FOREX": list(app_cfg.FOREX_SYMBOLS.keys())[:8],
    "FUTURES": list(app_cfg.FUTURES_SYMBOLS.keys()),
    "BONDS": list(app_cfg.BOND_SYMBOLS.keys()),
}

TIMEFRAME_FETCH = {
    "1d": {"period": "2y", "interval": "1d", "resample": None},
    "4h": {"period": "730d", "interval": "1h", "resample": "4h"},
    "1h": {"period": "730d", "interval": "1h", "resample": None},
}


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = pd.DataFrame(index=df.index)
    for want in ("open", "high", "low", "close", "volume"):
        if want in df.columns:
            out[want] = df[want]
        elif want.capitalize() in df.columns:
            out[want] = df[want.capitalize()]
    out = out.dropna(subset=["close"]) if "close" in out.columns else out
    if not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index, errors="coerce")
    return out


def _resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    if df.empty:
        return df
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    avail = {k: v for k, v in agg.items() if k in df.columns}
    return df.resample(rule).agg(avail).dropna(subset=["close"])


_FETCH_CACHE: dict[tuple[str, str], dict[str, pd.DataFrame]] = {}


def _yf_download_one(symbol: str, period: str, interval: str) -> pd.DataFrame:
    try:
        df = yf.download(symbol, period=period, interval=interval,
                         progress=False, auto_adjust=False, threads=False)
    except Exception as e:  # noqa: BLE001
        print(f"  yf.download({symbol}) failed: {e}", flush=True)
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    return df


def fetch_universe_bars(symbols: list[str], timeframe: str) -> dict[str, pd.DataFrame]:
    cfg = TIMEFRAME_FETCH.get(timeframe, TIMEFRAME_FETCH["1d"])
    cache_key = (tuple(symbols), cfg["period"] + cfg["interval"])
    if cache_key in _FETCH_CACHE:
        return _FETCH_CACHE[cache_key]
    out: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        raw = _yf_download_one(sym, cfg["period"], cfg["interval"])
        norm = _normalize_ohlcv(raw)
        if cfg["resample"]:
            norm = _resample(norm, cfg["resample"])
        if not norm.empty and len(norm) >= 60:
            out[sym] = norm
            print(f"  {sym}: {len(norm)} bars", flush=True)
        else:
            print(f"  {sym}: insufficient bars ({len(norm)})", flush=True)
    _FETCH_CACHE[cache_key] = out
    return out


def position_backtest(df: pd.DataFrame, max_hold: int = 20) -> list[dict]:
    if df.empty or "signal" not in df.columns:
        return []
    has_tp = "tp_long" in df.columns and "tp_short" in df.columns
    closes = df["close"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float) if "high" in df.columns else closes
    lows = df["low"].to_numpy(dtype=float) if "low" in df.columns else closes
    signals = df["signal"].fillna(0).astype(int).to_numpy()
    stops_long = df["stop_long"].to_numpy(dtype=float) if "stop_long" in df.columns else np.full(len(df), np.nan)
    stops_short = df["stop_short"].to_numpy(dtype=float) if "stop_short" in df.columns else np.full(len(df), np.nan)
    tps_long = df["tp_long"].to_numpy(dtype=float) if has_tp else np.full(len(df), np.nan)
    tps_short = df["tp_short"].to_numpy(dtype=float) if has_tp else np.full(len(df), np.nan)

    trades: list[dict] = []
    position = 0
    entry_price = entry_stop = entry_tp = 0.0
    entry_bar = 0

    for i in range(1, len(df)):
        if position == 0:
            sig = int(signals[i])
            if sig == 0:
                continue
            position = 1 if sig > 0 else -1
            entry_price = float(closes[i])
            entry_bar = i
            if position > 0:
                entry_stop = float(stops_long[i]) if np.isfinite(stops_long[i]) else entry_price * 0.95
                entry_tp = float(tps_long[i]) if has_tp and np.isfinite(tps_long[i]) else float("nan")
            else:
                entry_stop = float(stops_short[i]) if np.isfinite(stops_short[i]) else entry_price * 1.05
                entry_tp = float(tps_short[i]) if has_tp and np.isfinite(tps_short[i]) else float("nan")
            continue

        exit_price = None
        reason = None
        if position > 0:
            if lows[i] <= entry_stop:
                exit_price, reason = entry_stop, "SL"
            elif has_tp and np.isfinite(entry_tp) and highs[i] >= entry_tp:
                exit_price, reason = entry_tp, "TP"
            elif signals[i] < 0:
                exit_price, reason = float(closes[i]), "REVERSE"
        else:
            if highs[i] >= entry_stop:
                exit_price, reason = entry_stop, "SL"
            elif has_tp and np.isfinite(entry_tp) and lows[i] <= entry_tp:
                exit_price, reason = entry_tp, "TP"
            elif signals[i] > 0:
                exit_price, reason = float(closes[i]), "REVERSE"

        if exit_price is None and (i - entry_bar) >= max_hold:
            exit_price, reason = float(closes[i]), "TIME"

        if exit_price is not None:
            pnl_pct = (exit_price - entry_price) / entry_price * 100.0 * position
            trades.append({
                "entry_bar": int(entry_bar),
                "exit_bar": int(i),
                "direction": "LONG" if position > 0 else "SHORT",
                "entry_price": round(entry_price, 6),
                "exit_price": round(float(exit_price), 6),
                "pnl_pct": round(pnl_pct, 4),
                "exit_reason": reason,
                "bars_held": int(i - entry_bar),
            })
            position = 0

    return trades


def compute_metrics(trades: list[dict], n_boot: int = 1000) -> dict:
    if not trades:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "pf_ci_lower": 0.0,
                "pf_ci_upper": 0.0, "avg_pnl_pct": 0.0, "max_dd_pct": 0.0,
                "sharpe": 0.0, "long_n": 0, "short_n": 0}
    pnls = np.array([t["pnl_pct"] for t in trades], dtype=float)
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    gp = float(wins.sum())
    gl = float(abs(losses.sum()))
    pf = gp / gl if gl > 0 else 99.0
    wr = float((pnls > 0).mean() * 100)

    equity = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity)
    max_dd = float(abs((equity - peak).min())) if len(equity) else 0.0

    sharpe = float(pnls.mean() / pnls.std() * np.sqrt(252)) if pnls.std() > 0 else 0.0

    pf_ci_lower = pf
    pf_ci_upper = pf
    if len(pnls) >= 10:
        rng = np.random.default_rng(42)
        boots = []
        for _ in range(n_boot):
            s = rng.choice(pnls, size=len(pnls), replace=True)
            sgp = s[s > 0].sum()
            sgl = abs(s[s <= 0].sum())
            if sgl > 0:
                boots.append(sgp / sgl)
        if boots:
            pf_ci_lower = float(np.percentile(boots, 2.5))
            pf_ci_upper = float(np.percentile(boots, 97.5))

    directions = np.array([t["direction"] for t in trades])
    return {
        "n": len(trades),
        "wr": round(wr, 2),
        "pf": round(float(pf), 3),
        "pf_ci_lower": round(pf_ci_lower, 3),
        "pf_ci_upper": round(pf_ci_upper, 3),
        "avg_pnl_pct": round(float(pnls.mean()), 4),
        "max_dd_pct": round(max_dd, 3),
        "sharpe": round(sharpe, 3),
        "long_n": int((directions == "LONG").sum()),
        "short_n": int((directions == "SHORT").sum()),
    }


def promotion_verdict(m: dict) -> dict:
    reasons = []
    if m["n"] < 30:
        reasons.append(f"n={m['n']} < 30")
    if m["pf_ci_lower"] < 1.20:
        reasons.append(f"pf_ci_lower={m['pf_ci_lower']} < 1.20")
    return {"viable": len(reasons) == 0, "blocked_by": reasons}


def load_module(path: str):
    name = os.path.basename(path)[:-3]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return name, mod


def run_strategy(strat_id: str, info: dict) -> dict:
    asset_class = str(info.get("asset_class", "")).upper()
    universe = UNIVERSES.get(asset_class, [])
    if not universe:
        return {"strategy": strat_id, "asset_class": asset_class,
                "error": f"no universe for {asset_class}"}
    timeframe = info.get("timeframe", "1d")
    try:
        config_instance = info["config"]() if callable(info["config"]) else info["config"]
    except Exception as e:  # noqa: BLE001
        return {"strategy": strat_id, "error": f"config init: {e}"}
    gen_signals = info["generate_signals"]

    bars_map = fetch_universe_bars(universe, timeframe)
    per_symbol = {}
    all_trades: list[dict] = []
    for sym in universe:
        df = bars_map.get(sym)
        if df is None or df.empty:
            per_symbol[sym] = {"skipped": True, "reason": "no bars"}
            continue
        try:
            sig_df = gen_signals(df, config_instance)
            trades = position_backtest(sig_df, max_hold=getattr(config_instance, "max_holding_bars", 20))
            per_symbol[sym] = {"n_bars": int(len(df)), "n_trades": len(trades)}
            for t in trades:
                t["symbol"] = sym
            all_trades.extend(trades)
        except Exception as e:  # noqa: BLE001
            per_symbol[sym] = {"error": str(e)[:150]}

    metrics = compute_metrics(all_trades)
    verdict = promotion_verdict(metrics)
    return {
        "strategy": strat_id,
        "name": info.get("name", strat_id),
        "asset_class": asset_class,
        "timeframe": timeframe,
        "n_symbols_tested": len(universe),
        "per_symbol": per_symbol,
        "metrics": metrics,
        "promotion": verdict,
        "recent_winning_trades": [t for t in all_trades if t["pnl_pct"] > 0][-5:],
    }


def main() -> int:
    strategy_files = sorted(glob.glob(os.path.join(REPO_ROOT, "mimo_strategies", "*.py")))
    strategy_files = [f for f in strategy_files if not os.path.basename(f).startswith("__")]
    results: list[dict] = []
    for path in strategy_files:
        try:
            name, mod = load_module(path)
        except Exception as e:  # noqa: BLE001
            print(f"[LOAD FAIL] {path}: {e}")
            continue
        registry = getattr(mod, "STRATEGY_REGISTRY", None)
        if not registry:
            continue
        for strat_id, info in registry.items():
            print(f"\n=== {strat_id} ({info.get('asset_class','?')}, {info.get('timeframe','?')}) ===")
            try:
                res = run_strategy(strat_id, info)
            except Exception as e:  # noqa: BLE001
                print(f"[RUN FAIL] {strat_id}: {e}")
                traceback.print_exc()
                res = {"strategy": strat_id, "error": str(e)}
            results.append(res)
            m = res.get("metrics", {})
            v = res.get("promotion", {})
            if m:
                print(f"  n={m['n']} wr={m['wr']}% pf={m['pf']} "
                      f"pf_ci_lower={m['pf_ci_lower']} sharpe={m['sharpe']}")
                print(f"  viable={v.get('viable')} blocked_by={v.get('blocked_by', [])}")

    viable = [r["strategy"] for r in results if r.get("promotion", {}).get("viable")]
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "real-data via alpha_engine.scanner.fetch_market_data",
        "promotion_gate": "n >= 30 AND pf_ci_lower >= 1.20",
        "results": results,
        "viable_strategies": viable,
        "supersedes": "scripts/backtest_mimo_on_real_bars.py (broken: relies on strat['backtest'] which only exists in 1/7 strategies)",
    }
    out_path = os.path.join(REPO_ROOT, "mimo_strategies", "backtest_results_v2.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nWrote {out_path}")
    print(f"Viable strategies: {viable}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
