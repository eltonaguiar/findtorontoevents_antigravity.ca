#!/usr/bin/env python3
"""
Real-data sweep runner for baby strategies.

Loads BTC OHLCV from crypto_data.db, builds a deterministic multi-input context,
and runs walk-forward trade simulation for strategy files.
"""

from __future__ import annotations

import importlib.util
import inspect
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


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
class SweepResult:
    strategy_name: str
    agent_id: str
    file_path: str
    status: str
    sharpe: Optional[float]
    win_rate: Optional[float]
    max_drawdown: Optional[float]
    profit_factor: Optional[float]
    total_return: Optional[float]
    total_trades: int
    duration_sec: float
    error: Optional[str] = None


class RealDataSweepRunner:
    def __init__(
        self,
        db_path: str,
        pair: str = "BTC/USDT",
        bars: int = 1808,
        initial_capital: float = 10_000.0,
        commission: float = 0.001,
        max_hold_bars: int = 20,
        min_bars: int = 80,
        bar_step: int = 2,
        strategy_timeout_sec: int = 25,
    ):
        self.db_path = Path(db_path)
        self.pair = pair
        self.bars = int(bars)
        self.initial_capital = float(initial_capital)
        self.commission = float(commission)
        self.max_hold_bars = int(max_hold_bars)
        self.min_bars = int(min_bars)
        self.bar_step = max(1, int(bar_step))
        self.strategy_timeout_sec = int(strategy_timeout_sec)

        self._base_ohlcv = self._load_pair_data(self.pair, self.bars)
        self._ctx = self._build_context(self._base_ohlcv)

    def _load_pair_data(self, pair: str, bars: int) -> pd.DataFrame:
        query = """
        SELECT pair, timestamp, open, high, low, close, volume
        FROM klines
        WHERE pair = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            df = pd.read_sql_query(query, conn, params=[pair, bars])
        if df.empty:
            raise RuntimeError(f"No market data found for {pair} in {self.db_path}")
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        for c in ("open", "high", "low", "close", "volume"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=["timestamp", "open", "high", "low", "close", "volume"])
        return df.sort_values("timestamp").reset_index(drop=True)

    @staticmethod
    def _resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
        x = df.set_index("timestamp")
        y = x.resample(rule).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        ).dropna()
        return y.reset_index()

    @staticmethod
    def _expand_to_subhour(df: pd.DataFrame, step_minutes: int) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        n = int(60 / step_minutes)
        for _, r in df.iterrows():
            ts = r["timestamp"]
            o = float(r["open"])
            c = float(r["close"])
            h = float(r["high"])
            l = float(r["low"])
            v = float(r["volume"])
            for i in range(n):
                frac = (i + 1) / n
                px = o + (c - o) * frac
                high = min(max(px * 1.0008, l), h)
                low = max(min(px * 0.9992, h), l)
                rows.append(
                    {
                        "timestamp": ts + pd.Timedelta(minutes=i * step_minutes),
                        "open": px,
                        "high": max(high, low),
                        "low": min(high, low),
                        "close": px,
                        "volume": v / n,
                    }
                )
        return pd.DataFrame(rows)

    def _build_context(self, btc: pd.DataFrame) -> Dict[str, Any]:
        ret = btc["close"].pct_change().fillna(0.0)
        vol = ret.rolling(24).std().fillna(0.0)

        spx_ret = 0.35 * ret + 0.65 * ret.rolling(6, min_periods=1).mean() + 0.00005
        dxy_ret = -0.25 * ret + 0.75 * (-ret).rolling(6, min_periods=1).mean() + 0.00002
        spx_close = 4500 * (1 + spx_ret).cumprod()
        dxy_close = 100 * (1 + dxy_ret).cumprod()
        vix_close = 16 + (vol * 1200).clip(0, 35)

        spx = pd.DataFrame(
            {
                "timestamp": btc["timestamp"],
                "open": spx_close * (1 - 0.001),
                "high": spx_close * (1 + 0.003),
                "low": spx_close * (1 - 0.003),
                "close": spx_close,
                "volume": 1_000_000 + btc["volume"].rolling(8, min_periods=1).mean() * 40,
            }
        )
        dxy = pd.DataFrame(
            {
                "timestamp": btc["timestamp"],
                "open": dxy_close * (1 - 0.0005),
                "high": dxy_close * (1 + 0.001),
                "low": dxy_close * (1 - 0.001),
                "close": dxy_close,
                "volume": 100_000,
            }
        )
        vix = pd.DataFrame(
            {
                "timestamp": btc["timestamp"],
                "open": vix_close,
                "high": vix_close * 1.01,
                "low": vix_close * 0.99,
                "close": vix_close,
                "volume": 10_000,
            }
        )

        flow = pd.Series((-ret * 1800).rolling(4, min_periods=1).mean().values, index=btc["timestamp"], name="flow")
        whale_inflow = pd.Series(
            (btc["volume"] * btc["close"] * 0.001).rolling(8, min_periods=1).mean().values,
            index=btc["timestamp"],
            name="whale_inflow",
        )
        funding = pd.Series(np.tanh(ret.rolling(8, min_periods=1).mean().values * 50) * 0.01, index=btc["timestamp"], name="funding")
        gov = pd.Series((100 + (btc["volume"].pct_change().fillna(0) * 400).clip(-80, 80)).values, index=btc["timestamp"], name="gov")
        social = pd.Series((500 + (ret.abs() * 8000)).values, index=btc["timestamp"], name="social")
        liquidation = pd.DataFrame(
            {
                "timestamp": btc["timestamp"],
                "usd_value": ((ret.abs() * btc["volume"] * btc["close"]) * 0.08).fillna(0.0),
            }
        )
        ratio = pd.DataFrame({"timestamp": btc["timestamp"], "close": (spx["close"] / btc["close"]).replace([np.inf, -np.inf], np.nan).ffill()})
        ratio["open"] = ratio["close"]
        ratio["high"] = ratio["close"] * 1.002
        ratio["low"] = ratio["close"] * 0.998
        ratio["volume"] = 1.0

        return {
            "btc": btc,
            "btc_1h": btc,
            "btc_4h": self._resample_ohlcv(btc, "4h"),
            "btc_15m": self._expand_to_subhour(btc, 15),
            "btc_5m": self._expand_to_subhour(btc, 5),
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
        }

    @staticmethod
    def _load_strategy_class(py_file: Path) -> Tuple[Optional[type], Optional[str]]:
        try:
            name = f"sweep_{py_file.stem}_{int(time.time_ns() % 1_000_000)}"
            spec = importlib.util.spec_from_file_location(name, py_file)
            if spec is None or spec.loader is None:
                return None, "spec loader unavailable"
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[attr-defined]
            for k in dir(mod):
                v = getattr(mod, k)
                if isinstance(v, type) and k.endswith("Strategy") and k != "Strategy":
                    return v, None
            return None, "No Strategy class found"
        except SystemExit as exc:
            # Some non-strategy helper files in baby_strategies/ call
            # `raise SystemExit("pip install ...")` at import time. SystemExit
            # derives from BaseException, so a bare `except Exception` misses it
            # and one bad file aborts the ENTIRE sweep (run 27056111987 died on
            # baby_strategies/backtest_batch_round3.py). Treat it as a per-file
            # import error so the sweep continues.
            return None, f"Import aborted (SystemExit): {exc}"
        except Exception as exc:
            return None, f"Import error: {exc}"

    @staticmethod
    def _infer_side(direction: Any) -> Optional[str]:
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

    @staticmethod
    def _slice_df(df: pd.DataFrame, ts: pd.Timestamp) -> pd.DataFrame:
        return df[df["timestamp"] <= ts].copy()

    @staticmethod
    def _slice_series(s: pd.Series, ts: pd.Timestamp) -> pd.Series:
        return s[s.index <= ts].copy()

    def _build_kwargs(self, param_names: List[str], ts: pd.Timestamp, equity: float) -> Dict[str, Any]:
        ctx = self._ctx
        kwargs: Dict[str, Any] = {}
        for p in param_names:
            if p == "symbol":
                kwargs[p] = "BTCUSDT"
            elif p in ("data", "btc_data", "data_1h"):
                kwargs[p] = self._slice_df(ctx["btc"], ts)
            elif p == "data_4h":
                kwargs[p] = self._slice_df(ctx["btc_4h"], ts)
            elif p == "data_5m":
                kwargs[p] = self._slice_df(ctx["btc_5m"], ts)
            elif p == "data_15m":
                kwargs[p] = self._slice_df(ctx["btc_15m"], ts)
            elif p == "spx_data":
                kwargs[p] = self._slice_df(ctx["spx"], ts)
            elif p == "dxy_data":
                kwargs[p] = self._slice_df(ctx["dxy"], ts)
            elif p == "vix_data":
                kwargs[p] = self._slice_df(ctx["vix"], ts)
            elif p == "flow_data":
                kwargs[p] = self._slice_series(ctx["flow"], ts)
            elif p == "whale_inflow":
                kwargs[p] = self._slice_series(ctx["whale_inflow"], ts)
            elif p == "funding_rate":
                fs = self._slice_series(ctx["funding"], ts)
                kwargs[p] = float(fs.iloc[-1]) if len(fs) else 0.0
            elif p == "gov_data":
                kwargs[p] = self._slice_series(ctx["gov"], ts)
            elif p == "social_data":
                kwargs[p] = self._slice_series(ctx["social"], ts)
            elif p == "liquidation_data":
                kwargs[p] = self._slice_df(ctx["liquidation"], ts)
            elif p == "account_balance":
                kwargs[p] = float(equity)
            else:
                kwargs[p] = None
        return kwargs

    @staticmethod
    def _to_signal_obj(sig: Any) -> Optional[Any]:
        if sig is None:
            return None
        if isinstance(sig, dict):
            return SimpleNamespace(**sig)
        return sig

    def _normalize_signals(self, raw: Any) -> List[Any]:
        signals = raw if isinstance(raw, list) else ([] if raw is None else [raw])
        out: List[Any] = []
        for sig in signals:
            obj = self._to_signal_obj(sig)
            if obj is None:
                continue
            side = self._infer_side(getattr(obj, "direction", None))
            if side is None:
                continue
            try:
                entry = float(getattr(obj, "entry_price"))
                tp = float(getattr(obj, "take_profit"))
                sl = float(getattr(obj, "stop_loss"))
            except Exception:
                continue
            if entry <= 0 or tp <= 0 or sl <= 0:
                continue
            out.append(obj)
        return out

    def _choose_exec_df(self, signal: Any) -> pd.DataFrame:
        symbol = str(getattr(signal, "symbol", "")).upper()
        direction = str(getattr(signal, "direction", "")).upper()
        if symbol in {"SPXBTC", "BTCSPX"} or ("SPX" in direction and "BTC" in direction):
            return self._ctx["spxbtc_ratio"]
        return self._ctx["btc"]

    def _simulate_trade(self, signal: Any, entry_idx: int) -> Optional[Trade]:
        side = self._infer_side(getattr(signal, "direction", None))
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

        exec_df = self._choose_exec_df(signal)
        if entry_idx >= len(exec_df) - 1:
            return None

        pos = 0.1
        entry_time = pd.to_datetime(exec_df.iloc[entry_idx]["timestamp"], utc=True).isoformat()
        last_idx = min(entry_idx + self.max_hold_bars, len(exec_df) - 1)

        for i in range(entry_idx + 1, last_idx + 1):
            px = float(exec_df.iloc[i]["close"])
            exit_time = pd.to_datetime(exec_df.iloc[i]["timestamp"], utc=True).isoformat()
            bars_held = i - entry_idx

            if side == "BUY":
                if px >= tp:
                    pnl = (tp - entry) * pos * (1 - self.commission)
                    return Trade(entry_time, exit_time, "LONG", entry, tp, float(pnl), float((tp - entry) / entry), "TP", bars_held)
                if px <= sl:
                    pnl = (sl - entry) * pos * (1 - self.commission)
                    return Trade(entry_time, exit_time, "LONG", entry, sl, float(pnl), float((sl - entry) / entry), "SL", bars_held)
            else:
                if px <= tp:
                    pnl = (entry - tp) * pos * (1 - self.commission)
                    return Trade(entry_time, exit_time, "SHORT", entry, tp, float(pnl), float((entry - tp) / entry), "TP", bars_held)
                if px >= sl:
                    pnl = (entry - sl) * pos * (1 - self.commission)
                    return Trade(entry_time, exit_time, "SHORT", entry, sl, float(pnl), float((entry - sl) / entry), "SL", bars_held)

        px = float(exec_df.iloc[last_idx]["close"])
        exit_time = pd.to_datetime(exec_df.iloc[last_idx]["timestamp"], utc=True).isoformat()
        bars_held = last_idx - entry_idx
        if side == "BUY":
            pnl = (px - entry) * pos * (1 - self.commission)
            pnl_pct = (px - entry) / entry
            direction = "LONG"
        else:
            pnl = (entry - px) * pos * (1 - self.commission)
            pnl_pct = (entry - px) / entry
            direction = "SHORT"
        return Trade(entry_time, exit_time, direction, entry, px, float(pnl), float(pnl_pct), "TIME", bars_held)

    def _metrics(self, pnls: List[float]) -> Dict[str, float]:
        if not pnls:
            return {"sharpe": 0.0, "win_rate": 0.0, "max_drawdown": 1.0, "profit_factor": 0.0, "total_return": 0.0}

        arr = np.array(pnls, dtype=float)
        wins = arr[arr > 0]
        losses = arr[arr <= 0]
        win_rate = float((arr > 0).mean())
        gp = float(wins.sum()) if len(wins) else 0.0
        gl = float(abs(losses.sum())) if len(losses) else 0.0
        pf = gp / gl if gl > 0 else 999.0

        eq = self.initial_capital
        curve = [eq]
        for p in arr:
            eq += float(p)
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
        total_return = float((curve[-1] - curve[0]) / curve[0]) if curve[0] > 0 else 0.0
        return {
            "sharpe": round(sharpe, 4),
            "win_rate": round(win_rate, 4),
            "max_drawdown": round(max_dd, 4),
            "profit_factor": round(pf, 4),
            "total_return": round(total_return, 4),
        }

    def run_strategy(self, py_file: Path) -> SweepResult:
        strategy_name = py_file.stem
        agent_id = py_file.parent.name
        started = time.time()

        klass, err = self._load_strategy_class(py_file)
        if klass is None:
            return SweepResult(strategy_name, agent_id, str(py_file), "error", None, None, None, None, None, 0, round(time.time() - started, 3), err)

        try:
            strategy = klass()
            fn = getattr(strategy, "generate_signals")
            params = list(inspect.signature(fn).parameters.keys())
        except Exception as exc:
            return SweepResult(strategy_name, agent_id, str(py_file), "error", None, None, None, None, None, 0, round(time.time() - started, 3), str(exc))

        btc = self._ctx["btc"]
        pnls: List[float] = []
        equity = self.initial_capital
        errors_seen = 0

        for end_idx in range(self.min_bars, len(btc), self.bar_step):
            if time.time() - started > self.strategy_timeout_sec:
                return SweepResult(
                    strategy_name,
                    agent_id,
                    str(py_file),
                    "timeout",
                    None,
                    None,
                    None,
                    None,
                    None,
                    len(pnls),
                    round(time.time() - started, 3),
                    f"timeout>{self.strategy_timeout_sec}s",
                )

            ts = pd.to_datetime(btc.iloc[end_idx]["timestamp"], utc=True)
            try:
                kwargs = self._build_kwargs(params, ts, equity)
                raw = fn(**kwargs)
                signals = self._normalize_signals(raw)
            except Exception:
                errors_seen += 1
                continue

            for sig in signals:
                trade = self._simulate_trade(sig, end_idx)
                if trade is None:
                    continue
                pnls.append(float(trade.pnl))
                equity += float(trade.pnl)

        m = self._metrics(pnls)
        if len(pnls) < 3:
            status = "failed_insufficient_trades"
        elif m["sharpe"] >= 1.0 and m["win_rate"] >= 0.45 and m["max_drawdown"] <= 0.20:
            status = "passed"
        else:
            status = "failed"

        err_msg = f"errors_seen={errors_seen}" if errors_seen > 0 else None
        return SweepResult(
            strategy_name=strategy_name,
            agent_id=agent_id,
            file_path=str(py_file),
            status=status,
            sharpe=m["sharpe"],
            win_rate=m["win_rate"],
            max_drawdown=m["max_drawdown"],
            profit_factor=m["profit_factor"],
            total_return=m["total_return"],
            total_trades=len(pnls),
            duration_sec=round(time.time() - started, 3),
            error=err_msg,
        )
