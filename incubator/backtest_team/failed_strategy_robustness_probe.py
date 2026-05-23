#!/usr/bin/env python3
"""
Failed Strategy Robustness Probe
================================

Purpose:
- Re-test failed/insufficient baby strategies under alternate assumptions:
  1) Direction mode: both / long-only / short-only
  2) TP/SL scale: tight/base/wide
  3) Timeframe feed: 1h / 4h / 1d

Outputs:
- JSON report with per-strategy best variant and all tested variants
- CSV leaderboard of probe outcomes
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import inspect
import json
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
LATEST_SWEEP_GLOB = "real_data_sweep_*.json"


@dataclass
class ProbeVariantResult:
    strategy_name: str
    agent_id: str
    file_path: str
    baseline_status: str
    variant_id: str
    timeframe: str
    direction_mode: str
    tp_scale: float
    sl_scale: float
    status: str
    sharpe: Optional[float]
    win_rate: Optional[float]
    max_drawdown: Optional[float]
    total_trades: int
    profit_factor: Optional[float]
    total_return: Optional[float]
    duration_sec: float
    error: Optional[str] = None


class ProbeEngine:
    def __init__(
        self,
        db_path: Path,
        pair: str = "BTC/USDT",
        bars: int = 1808,
        initial_capital: float = 10000.0,
        commission: float = 0.001,
        max_hold_bars: int = 20,
        strategy_timeout_sec: int = 20,
    ):
        self.db_path = db_path
        self.pair = pair
        self.bars = bars
        self.initial_capital = initial_capital
        self.commission = commission
        self.max_hold_bars = max_hold_bars
        self.strategy_timeout_sec = strategy_timeout_sec

        self._base_ohlcv = self._load_pair_data(self.pair, self.bars)
        self._ctx_cache: Dict[str, Dict[str, Any]] = {}

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
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        for c in ("open", "high", "low", "close", "volume"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=["timestamp", "open", "high", "low", "close", "volume"])
        return df.sort_values("timestamp").reset_index(drop=True)

    def _resample_ohlcv(self, df: pd.DataFrame, rule: str) -> pd.DataFrame:
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

    def _expand_to_subhour(self, df: pd.DataFrame, step_minutes: int) -> pd.DataFrame:
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

    def _build_context(self, timeframe: str) -> Dict[str, Any]:
        if timeframe in self._ctx_cache:
            return self._ctx_cache[timeframe]

        if timeframe == "1h":
            btc = self._base_ohlcv.copy()
        elif timeframe == "4h":
            btc = self._resample_ohlcv(self._base_ohlcv, "4h")
        elif timeframe == "1d":
            btc = self._resample_ohlcv(self._base_ohlcv, "1d")
        else:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        close = btc["close"]
        ret = close.pct_change().fillna(0.0)
        vol = ret.rolling(24 if timeframe == "1h" else 8).std().fillna(0.0)

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

        ctx = {
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
        self._ctx_cache[timeframe] = ctx
        return ctx

    @staticmethod
    def _load_strategy_class(py_file: Path) -> Tuple[Optional[type], Optional[str]]:
        try:
            name = f"probe_{py_file.stem}_{int(time.time_ns() % 1_000_000)}"
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
        except Exception as e:
            return None, f"Import error: {e}"

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

    def _slice_df(self, df: pd.DataFrame, ts: pd.Timestamp) -> pd.DataFrame:
        return df[df["timestamp"] <= ts].copy()

    def _slice_series(self, s: pd.Series, ts: pd.Timestamp) -> pd.Series:
        return s[s.index <= ts].copy()

    def _build_kwargs(self, ctx: Dict[str, Any], params: List[str], ts: pd.Timestamp, equity: float) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        for p in params:
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

    def _scale_tp_sl(self, signal: Any, side: str, tp_scale: float, sl_scale: float) -> Optional[Tuple[float, float, float]]:
        entry = getattr(signal, "entry_price", None)
        tp = getattr(signal, "take_profit", None)
        sl = getattr(signal, "stop_loss", None)
        try:
            entry = float(entry)
            tp = float(tp)
            sl = float(sl)
        except Exception:
            return None
        if entry <= 0:
            return None

        if side == "BUY":
            tp_dist = max(tp - entry, 0.0)
            sl_dist = max(entry - sl, 0.0)
            if tp_dist == 0 or sl_dist == 0:
                return None
            new_tp = entry + tp_dist * tp_scale
            new_sl = entry - sl_dist * sl_scale
        else:
            tp_dist = max(entry - tp, 0.0)
            sl_dist = max(sl - entry, 0.0)
            if tp_dist == 0 or sl_dist == 0:
                return None
            new_tp = entry - tp_dist * tp_scale
            new_sl = entry + sl_dist * sl_scale
        return entry, new_tp, new_sl

    def _choose_exec_df(self, ctx: Dict[str, Any], signal: Any) -> pd.DataFrame:
        symbol = str(getattr(signal, "symbol", "")).upper()
        direction = str(getattr(signal, "direction", "")).upper()
        if symbol in {"SPXBTC", "BTCSPX"} or ("SPX" in direction and "BTC" in direction):
            return ctx["spxbtc_ratio"]
        return ctx["btc"]

    def _simulate_trade(
        self,
        ctx: Dict[str, Any],
        signal: Any,
        entry_idx: int,
        side_mode: str,
        tp_scale: float,
        sl_scale: float,
    ) -> Optional[Dict[str, float]]:
        side = self._infer_side(getattr(signal, "direction", None))
        if side is None:
            return None
        if side_mode == "long" and side != "BUY":
            return None
        if side_mode == "short" and side != "SELL":
            return None

        scaled = self._scale_tp_sl(signal, side, tp_scale, sl_scale)
        if scaled is None:
            return None
        entry, tp, sl = scaled

        exec_df = self._choose_exec_df(ctx, signal)
        if entry_idx >= len(exec_df) - 1:
            return None

        pos = 0.1
        last_idx = min(entry_idx + self.max_hold_bars, len(exec_df) - 1)
        for i in range(entry_idx + 1, last_idx + 1):
            px = float(exec_df.iloc[i]["close"])
            if side == "BUY":
                if px >= tp:
                    pnl = (tp - entry) * pos * (1 - self.commission)
                    return {"pnl": float(pnl), "pnl_pct": float((tp - entry) / entry)}
                if px <= sl:
                    pnl = (sl - entry) * pos * (1 - self.commission)
                    return {"pnl": float(pnl), "pnl_pct": float((sl - entry) / entry)}
            else:
                if px <= tp:
                    pnl = (entry - tp) * pos * (1 - self.commission)
                    return {"pnl": float(pnl), "pnl_pct": float((entry - tp) / entry)}
                if px >= sl:
                    pnl = (entry - sl) * pos * (1 - self.commission)
                    return {"pnl": float(pnl), "pnl_pct": float((entry - sl) / entry)}

        px = float(exec_df.iloc[last_idx]["close"])
        if side == "BUY":
            pnl = (px - entry) * pos * (1 - self.commission)
            pnl_pct = (px - entry) / entry
        else:
            pnl = (entry - px) * pos * (1 - self.commission)
            pnl_pct = (entry - px) / entry
        return {"pnl": float(pnl), "pnl_pct": float(pnl_pct)}

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

    def run_variant(
        self,
        py_file: Path,
        baseline_status: str,
        timeframe: str,
        direction_mode: str,
        tp_scale: float,
        sl_scale: float,
        bar_step: int,
    ) -> ProbeVariantResult:
        strategy_name = py_file.stem
        agent_id = py_file.parent.name
        started = time.time()
        variant_id = f"{timeframe}_{direction_mode}_tp{tp_scale:.2f}_sl{sl_scale:.2f}"

        klass, err = self._load_strategy_class(py_file)
        if klass is None:
            return ProbeVariantResult(
                strategy_name=strategy_name,
                agent_id=agent_id,
                file_path=str(py_file),
                baseline_status=baseline_status,
                variant_id=variant_id,
                timeframe=timeframe,
                direction_mode=direction_mode,
                tp_scale=tp_scale,
                sl_scale=sl_scale,
                status="error",
                sharpe=None,
                win_rate=None,
                max_drawdown=None,
                total_trades=0,
                profit_factor=None,
                total_return=None,
                duration_sec=round(time.time() - started, 3),
                error=err,
            )

        try:
            strategy = klass()
            fn = getattr(strategy, "generate_signals")
            params = list(inspect.signature(fn).parameters.keys())
        except Exception as e:
            return ProbeVariantResult(
                strategy_name=strategy_name,
                agent_id=agent_id,
                file_path=str(py_file),
                baseline_status=baseline_status,
                variant_id=variant_id,
                timeframe=timeframe,
                direction_mode=direction_mode,
                tp_scale=tp_scale,
                sl_scale=sl_scale,
                status="error",
                sharpe=None,
                win_rate=None,
                max_drawdown=None,
                total_trades=0,
                profit_factor=None,
                total_return=None,
                duration_sec=round(time.time() - started, 3),
                error=str(e),
            )

        ctx = self._build_context(timeframe)
        btc = ctx["btc"]
        if len(btc) < 30:
            return ProbeVariantResult(
                strategy_name=strategy_name,
                agent_id=agent_id,
                file_path=str(py_file),
                baseline_status=baseline_status,
                variant_id=variant_id,
                timeframe=timeframe,
                direction_mode=direction_mode,
                tp_scale=tp_scale,
                sl_scale=sl_scale,
                status="error",
                sharpe=None,
                win_rate=None,
                max_drawdown=None,
                total_trades=0,
                profit_factor=None,
                total_return=None,
                duration_sec=round(time.time() - started, 3),
                error="Not enough bars for timeframe",
            )

        min_bars = 80 if timeframe == "1h" else 35 if timeframe == "4h" else 20
        pnls: List[float] = []
        equity = self.initial_capital
        errors_seen = 0

        for end_idx in range(min_bars, len(btc), max(1, bar_step)):
            if time.time() - started > self.strategy_timeout_sec:
                return ProbeVariantResult(
                    strategy_name=strategy_name,
                    agent_id=agent_id,
                    file_path=str(py_file),
                    baseline_status=baseline_status,
                    variant_id=variant_id,
                    timeframe=timeframe,
                    direction_mode=direction_mode,
                    tp_scale=tp_scale,
                    sl_scale=sl_scale,
                    status="timeout",
                    sharpe=None,
                    win_rate=None,
                    max_drawdown=None,
                    total_trades=len(pnls),
                    profit_factor=None,
                    total_return=None,
                    duration_sec=round(time.time() - started, 3),
                    error=f"timeout>{self.strategy_timeout_sec}s",
                )

            ts = btc.iloc[end_idx]["timestamp"]
            try:
                kwargs = self._build_kwargs(ctx, params, ts, equity)
                raw = fn(**kwargs)
                signals = raw if isinstance(raw, list) else ([] if raw is None else [raw])
            except Exception:
                errors_seen += 1
                continue

            for sig in signals:
                t = self._simulate_trade(ctx, sig, end_idx, direction_mode, tp_scale, sl_scale)
                if t:
                    pnls.append(float(t["pnl"]))
                    equity += float(t["pnl"])

        m = self._metrics(pnls)
        if len(pnls) < 3:
            status = "failed_insufficient_trades"
        elif m["sharpe"] >= 1.0 and m["win_rate"] >= 0.45 and m["max_drawdown"] <= 0.20:
            status = "passed"
        else:
            status = "failed"

        err_msg = None
        if errors_seen > 0:
            err_msg = f"errors_seen={errors_seen}"

        return ProbeVariantResult(
            strategy_name=strategy_name,
            agent_id=agent_id,
            file_path=str(py_file),
            baseline_status=baseline_status,
            variant_id=variant_id,
            timeframe=timeframe,
            direction_mode=direction_mode,
            tp_scale=tp_scale,
            sl_scale=sl_scale,
            status=status,
            sharpe=m["sharpe"],
            win_rate=m["win_rate"],
            max_drawdown=m["max_drawdown"],
            total_trades=len(pnls),
            profit_factor=m["profit_factor"],
            total_return=m["total_return"],
            duration_sec=round(time.time() - started, 3),
            error=err_msg,
        )


def latest_sweep(path: Path) -> Path:
    files = sorted(path.glob(LATEST_SWEEP_GLOB), key=lambda p: p.stat().st_mtime)
    if not files:
        raise RuntimeError(f"No sweep files found in {path}")
    return files[-1]


def gate_distance(row: Dict[str, Any]) -> float:
    wr = float(row.get("win_rate") or 0.0)
    sh = float(row.get("sharpe") or 0.0)
    dd = float(row.get("max_drawdown") or 1.0)
    return max(0.0, 1.0 - sh) * 0.4 + max(0.0, 0.45 - wr) * 1.2 + max(0.0, dd - 0.20) * 2.0


def pick_probe_candidates(rows: List[Dict[str, Any]], top_n_failed: int, include_insufficient: bool) -> List[Dict[str, Any]]:
    failed = [r for r in rows if r.get("status") == "failed"]
    failed = sorted(failed, key=lambda r: (gate_distance(r), -(r.get("total_trades") or 0)))
    picks = failed[:top_n_failed]
    if include_insufficient:
        insuff = [r for r in rows if r.get("status") in {"failed_insufficient_trades", "timeout", "error"}]
        insuff = sorted(insuff, key=lambda r: (r.get("status"), -(r.get("total_trades") or 0)))
        picks.extend(insuff)

    seen = set()
    out = []
    for r in picks:
        k = (r.get("agent_id"), r.get("strategy_name"))
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def find_strategy_file(agent_id: str, strategy_name: str) -> Optional[Path]:
    p = ROOT / "incubator" / "agents" / agent_id / f"{strategy_name}.py"
    return p if p.exists() else None


def write_reports(results: List[ProbeVariantResult], out_dir: Path) -> Tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jpath = out_dir / f"failed_probe_{stamp}.json"
    cpath = out_dir / f"failed_probe_{stamp}.csv"

    # Per strategy best variant (pass preferred, then best gate distance proxy)
    grouped: Dict[Tuple[str, str], List[ProbeVariantResult]] = {}
    for r in results:
        grouped.setdefault((r.agent_id, r.strategy_name), []).append(r)

    best: List[Dict[str, Any]] = []
    for (agent, strat), rs in grouped.items():
        rs_sorted = sorted(
            rs,
            key=lambda x: (
                0 if x.status == "passed" else 1,
                0 if x.status == "failed" else 1,
                # Lower distance proxy better
                (max(0.0, 1.0 - (x.sharpe or 0.0)) * 0.4
                 + max(0.0, 0.45 - (x.win_rate or 0.0)) * 1.2
                 + max(0.0, (x.max_drawdown or 1.0) - 0.20) * 2.0),
                -(x.total_trades or 0),
            ),
        )
        best.append(asdict(rs_sorted[0]))

    payload = {
        "generated_at": datetime.now().isoformat(),
        "total_variants": len(results),
        "strategies_probed": len(grouped),
        "variants_passed": sum(1 for r in results if r.status == "passed"),
        "strategies_recovered": sum(1 for b in best if b["status"] == "passed"),
        "best_by_strategy": best,
        "all_variants": [asdict(r) for r in results],
    }
    jpath.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with cpath.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(results[0]).keys()) if results else [])
        if results:
            w.writeheader()
            for r in results:
                w.writerow(asdict(r))

    return jpath, cpath


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Probe failed baby strategies under alternate assumptions.")
    p.add_argument("--db-path", default="crypto_data.db")
    p.add_argument("--pair", default="BTC/USDT")
    p.add_argument("--bars", type=int, default=1808)
    p.add_argument("--top-failed", type=int, default=40, help="Probe top-N failed (near-pass) strategies.")
    p.add_argument("--include-insufficient", action="store_true", default=True)
    p.add_argument("--bar-step", type=int, default=4)
    p.add_argument("--strategy-timeout-sec", type=int, default=18)
    p.add_argument("--output-dir", default="incubator/backtest_results")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    sweep_file = latest_sweep(ROOT / "incubator" / "backtest_results")
    sweep = json.loads(sweep_file.read_text(encoding="utf-8"))
    rows = sweep.get("results", [])

    candidates = pick_probe_candidates(rows, top_n_failed=args.top_failed, include_insufficient=args.include_insufficient)
    print(f"[probe] sweep={sweep_file.name} | candidates={len(candidates)}")

    variants = [
        ("1h", "both", 1.00, 1.00),
        ("1h", "long", 1.00, 1.00),
        ("1h", "short", 1.00, 1.00),
        ("1h", "both", 0.75, 0.75),  # tighter TP/SL
        ("1h", "both", 1.25, 1.25),  # wider TP/SL
        ("4h", "both", 1.00, 1.00),
        ("1d", "both", 1.00, 1.00),
    ]

    engine = ProbeEngine(
        db_path=ROOT / args.db_path,
        pair=args.pair,
        bars=args.bars,
        strategy_timeout_sec=args.strategy_timeout_sec,
    )

    results: List[ProbeVariantResult] = []
    total_runs = len(candidates) * len(variants)
    run_i = 0

    for c in candidates:
        agent = c["agent_id"]
        strat = c["strategy_name"]
        py_file = find_strategy_file(agent, strat)
        if py_file is None:
            continue
        baseline_status = c.get("status", "failed")

        for timeframe, side_mode, tp_s, sl_s in variants:
            run_i += 1
            print(f"[{run_i}/{total_runs}] {agent}/{strat} | {timeframe} {side_mode} tp{tp_s} sl{sl_s}")
            r = engine.run_variant(
                py_file=py_file,
                baseline_status=baseline_status,
                timeframe=timeframe,
                direction_mode=side_mode,
                tp_scale=tp_s,
                sl_scale=sl_s,
                bar_step=args.bar_step,
            )
            results.append(r)
            print(
                f"    -> {r.status} | trades={r.total_trades} | wr={r.win_rate} | "
                f"sh={r.sharpe} | dd={r.max_drawdown} | {r.duration_sec:.2f}s"
            )

    jpath, cpath = write_reports(results, ROOT / args.output_dir)
    recovered = json.loads(jpath.read_text(encoding="utf-8")).get("strategies_recovered", 0)
    print("\n" + "=" * 80)
    print("FAILED STRATEGY ROBUSTNESS PROBE COMPLETE")
    print("=" * 80)
    print(f"Candidates: {len(candidates)} | Variants: {len(results)} | Strategies recovered: {recovered}")
    print(f"JSON: {jpath}")
    print(f"CSV : {cpath}")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

