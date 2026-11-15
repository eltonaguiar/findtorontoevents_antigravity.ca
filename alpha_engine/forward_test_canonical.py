#!/usr/bin/env python3
"""
Canonical Forward-Test Tracker
==============================
Consolidates four legacy forward-test trackers into one unified module:

1. simulations/forward_test_tracker.py       -> absolute promotion gates + fast elimination
2. tools/forward_test_tracker.py             -> benchmark-relative excess (vs SPY/BTC/GLD/BND)
3. alpha_engine/data/forward_testing/forward_tracker.py -> K1-K8 kill / P1-P7 promote signals
4. cross_aggregation/forward_test_tracker.py -> pick-level TP/SL live tracking

Plus QA ledger integration:
- tools/qa_ledger.py -> audit_dashboard/data/qa_market_validation.json

Output:
- alpha_engine/data/forward_testing/forward_test_canonical.json
- alpha_engine/data/forward_testing/forward_test_canonical.csv

Usage:
    python -m alpha_engine.forward_test_canonical --mode strategy --results-dir <dir>
    python -m alpha_engine.forward_test_canonical --mode pick
    python -m alpha_engine.forward_test_canonical --mode unified
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Allow running as script
if __name__ == "__main__" and __package__ is None:
    REPO_ROOT = Path(__file__).resolve().parents[1]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

# Optional deps — benchmark mode needs pandas/numpy/yfinance
try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
    _HAS_YFINANCE = True
except Exception:  # noqa: BLE001
    _HAS_YFINANCE = False
    np = pd = yf = None  # type: ignore

REPO = Path(__file__).resolve().parents[1]
DATA_DIR = REPO / "alpha_engine" / "data" / "forward_testing"
DASH_DATA = REPO / "audit_dashboard" / "data"
OUT_JSON = DATA_DIR / "forward_test_canonical.json"
OUT_CSV = DATA_DIR / "forward_test_canonical.csv"

# ═════════════════════════════════════════════════════════════════════════════
# 1. ABSOLUTE GATES (from simulations/forward_test_tracker.py)
# ═════════════════════════════════════════════════════════════════════════════

GATES = {
    "paper": {
        "n_min": 10,
        "pf_min": 0.80,
        "wr_min": 0.40,
        "max_dd_max": -0.25,
        "sharpe_min": 0.0,
        "max_days": 30,
    },
    "probation": {
        "n_min": 30,
        "pf_min": 1.00,
        "wr_min": 0.48,
        "max_dd_max": -0.20,
        "sharpe_min": 0.3,
        "max_days": 90,
    },
    "small_live": {
        "n_min": 100,
        "pf_min": 1.30,
        "wr_min": 0.55,
        "max_dd_max": -0.15,
        "sharpe_min": 0.8,
        "max_days": 180,
    },
    "full_live": {
        "n_min": 300,
        "pf_min": 1.50,
        "wr_min": 0.55,
        "max_dd_max": -0.15,
        "sharpe_min": 1.0,
        "max_days": 365,
    },
}

FAST_ELIMINATION = {
    "n_min": 10,
    "pf_max": 0.70,
    "wr_max": 0.30,
    "max_dd_min": -0.35,
    "consecutive_losses": 7,
    "days_without_trade": 14,
}

# ═════════════════════════════════════════════════════════════════════════════
# 2. BENCHMARK-RELATIVE CONFIG (from tools/forward_test_tracker.py)
# ═════════════════════════════════════════════════════════════════════════════

BENCH_TICKERS = {
    "EQUITY": "SPY",
    "ETF": "SPY",
    "MUTUAL_FUNDS": "SPY",
    "CRYPTO": "BTC-USD",
    "BOND": "BND",
    "COMMODITY": "GLD",
    "FUTURES": "GLD",
    "FOREX": "^DXY",
    "": "SPY",
}

BENCH_ELIM = {
    "min_n": 30,
    "pct_excess": 0.45,
    "sharpe": 0.4,
    "max_dd": 0.20,
    "hold_n": 60,
}

# ═════════════════════════════════════════════════════════════════════════════
# 3. K1-K8 KILL / P1-P7 PROMOTE (from alpha_engine/data/forward_testing/forward_tracker.py)
# ═════════════════════════════════════════════════════════════════════════════

KILL_SIGNALS = [
    ("K1", lambda s: s["total_trades"] >= 20 and s["net_pnl_pct"] < 0, "net PnL < 0 after 20 trades"),
    ("K2", lambda s: s["total_trades"] >= 30 and s["win_rate_pct"] < 35, "WR < 35% after 30 trades"),
    ("K3", lambda s: s["total_trades"] >= 25 and s["profit_factor"] < 0.80, "PF < 0.80 after 25 trades"),
    ("K4", lambda s: s["max_drawdown_pct"] > 15, "maxDD > 15%"),
    ("K5", lambda s: s["total_trades"] >= 30 and s["sharpe"] < 0, "Sharpe < 0 after 30 trades"),
    ("K6", lambda s: s["days_active"] >= 14 and s["total_trades"] == 0, "no trades in 14 days"),
    ("K7", lambda s: s["consecutive_losses"] >= 8, "8 consecutive losses"),
    ("K8", lambda s: s["total_trades"] >= 10 and s["cost_ratio_pct"] > 200, "cost ratio > 200% after 10 trades"),
]

PROMOTE_SIGNALS = {
    "min_trades": 30,
    "net_pnl_pct": 0,
    "win_rate_pct": 45,
    "profit_factor": 1.10,
    "max_drawdown_pct": 10,
    "sharpe": 0.5,
    "trades_per_week": 1,
    "max_consecutive_losses": 5,
}

# ═════════════════════════════════════════════════════════════════════════════
# 4. PICK-TRACKER CONSTANTS (from cross_aggregation/forward_test_tracker.py)
# ═════════════════════════════════════════════════════════════════════════════

PICK_SCORE_THRESHOLD = 75.0
PICK_EXPIRE_HOURS = 48
PICK_FRESH_MAX_H = 2.0
PICK_STALE_MIN_H = 4.0
PICK_MAX_CLOSED = 300

_CG_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin", "SOL": "solana",
    "XRP": "ripple", "ADA": "cardano", "AVAX": "avalanche-2", "DOT": "polkadot",
    "LINK": "chainlink", "MATIC": "matic-network", "LTC": "litecoin", "DOGE": "dogecoin",
    "SHIB": "shiba-inu", "UNI": "uniswap", "AAVE": "aave", "ATOM": "cosmos",
    "NEAR": "near", "FIL": "filecoin", "ICP": "internet-computer", "TRX": "tron",
    "ETC": "ethereum-classic", "BCH": "bitcoin-cash", "ALGO": "algorand",
    "HBAR": "hedera-hashgraph", "VET": "vechain", "PEPE": "pepe", "ZEC": "zcash",
    "APT": "aptos", "OP": "optimism", "ARB": "arbitrum", "SUI": "sui",
    "SEI": "sei-network", "INJ": "injective-protocol", "FTM": "fantom",
    "RUNE": "thorchain", "GRT": "the-graph", "MKR": "maker", "STX": "blockstack",
    "FLOKI": "floki", "BONK": "bonk", "WIF": "dogwifcoin", "FET": "fetch-ai",
    "RNDR": "render-token", "IMX": "immutable-x", "TIA": "celestia",
    "TON": "toncoin", "GALA": "gala", "APE": "apecoin", "CHZ": "chiliz",
    "STRK": "starknet", "JTO": "jito-governance-token", "W": "wormhole",
    "ZRO": "layerzero", "RENDER": "render-token",
}

_BINANCE_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]

_UA = {"User-Agent": "CanonicalForwardTest/1.0"}


# ═════════════════════════════════════════════════════════════════════════════
# Utilities
# ═════════════════════════════════════════════════════════════════════════════

def _f(v) -> Optional[float]:
    try:
        out = float(v)
        return out if out == out else None
    except (TypeError, ValueError):
        return None


def _dt(v) -> Optional[datetime]:
    if not v:
        return None
    try:
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _parse_iso(ts: str) -> Optional[datetime]:
    return _dt(ts)


def _safe_mean(values: List[float]) -> float:
    return statistics.mean(values) if values else 0.0


def _safe_median(values: List[float]) -> float:
    return statistics.median(values) if values else 0.0


def _safe_stdev(values: List[float]) -> float:
    return statistics.pstdev(values) if len(values) > 1 else 0.0


# ═════════════════════════════════════════════════════════════════════════════
# Price Fetchers (unified)
# ═════════════════════════════════════════════════════════════════════════════

def _http_json(url: str, timeout: int = 10) -> Optional[dict]:
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _normalize_symbol(symbol: str) -> str:
    s = symbol.strip().upper().replace("-", "").replace("/", "")
    if s.endswith("=X"):
        s = s[:-2]
    bare = {
        "BTC", "ETH", "SOL", "XRP", "ADA", "BNB", "DOGE", "AVAX",
        "LINK", "DOT", "NEAR", "FIL", "RENDER", "SUI", "ATOM", "ALGO",
        "TON", "AAVE", "FET", "INJ", "ARB", "TIA", "SHIB", "ETC",
        "BONK", "WIF", "GALA", "APE", "CHZ", "STRK", "JTO", "W", "ZRO",
    }
    if s in bare:
        s += "USDT"
    return s


def _is_crypto(symbol: str) -> bool:
    s = symbol.upper()
    return any(s.endswith(sfx) for sfx in ("USDT", "BUSD", "USDC", "BTC", "ETH"))


def _binance_price(symbol: str) -> Optional[float]:
    for base in _BINANCE_BASES:
        data = _http_json(f"{base}/api/v3/ticker/price?symbol={symbol}")
        if data and "price" in data:
            try:
                return float(data["price"])
            except (ValueError, TypeError):
                pass
    return None


def _coingecko_price(symbol: str) -> Optional[float]:
    base = symbol.replace("USDT", "").replace("BUSD", "").replace("USDC", "")
    cg_id = _CG_MAP.get(base)
    if not cg_id:
        return None
    headers = dict(_UA)
    cg_key = os.environ.get("COINGECKO_API_KEY", "")
    if cg_key:
        headers["x-cg-demo-api-key"] = cg_key
    try:
        req = urllib.request.Request(
            f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        if data and isinstance(data, dict):
            usd = data.get(cg_id, {}).get("usd")
            if usd:
                return float(usd)
    except Exception:
        pass
    return None


def _yahoo_price(symbol: str) -> Optional[float]:
    try:
        req = urllib.request.Request(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d",
            headers={**_UA, "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        meta = data["chart"]["result"][0]["meta"]
        return float(meta["regularMarketPrice"])
    except Exception:
        return None


def get_current_price(symbol: str) -> Optional[float]:
    sym = _normalize_symbol(symbol)
    if _is_crypto(sym):
        p = _binance_price(sym)
        if p is not None:
            return p
        p = _coingecko_price(sym)
        if p is not None:
            return p
    return _yahoo_price(symbol)


# ═════════════════════════════════════════════════════════════════════════════
# Benchmark Loader (optional yfinance)
# ═════════════════════════════════════════════════════════════════════════════

def load_benchmark(ticker: str, start, end) -> Optional["pd.Series"]:
    if not _HAS_YFINANCE:
        return None
    px = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if px.empty:
        return pd.Series(dtype=float)
    close = px["Close"].squeeze()
    return close.dropna()


def bench_return(bench: "pd.Series", entry_dt, exit_dt) -> Optional[float]:
    if bench is None or bench.empty:
        return None
    a, b = bench.index.searchsorted([entry_dt, exit_dt])
    if b <= a:
        return None
    seg = bench.iloc[a:b]
    if len(seg) < 2:
        return None
    return seg.iloc[-1] / seg.iloc[0] - 1.0


# ═════════════════════════════════════════════════════════════════════════════
# QA Ledger Filter
# ═════════════════════════════════════════════════════════════════════════════

class QALedgerFilter:
    """Consumes audit_dashboard/data/qa_market_validation.json"""

    def __init__(self, qa_path: Optional[Path] = None):
        self.qa_path = qa_path or DASH_DATA / "qa_market_validation.json"
        self.flags: List[dict] = []
        self._critical_symbols: set = set()
        self._load()

    def _load(self):
        if not self.qa_path.exists():
            return
        try:
            data = json.loads(self.qa_path.read_text(encoding="utf-8"))
            self.flags = data.get("flags", [])
            critical = {"UNPRICED", "UNVERIFIED_ZERO", "MISMATCH", "PNL_OUT_OF_BOUNDS"}
            self._critical_symbols = {
                f["symbol"] for f in self.flags if f.get("verdict") in critical
            }
        except (json.JSONDecodeError, OSError):
            pass

    def is_flagged(self, symbol: str) -> bool:
        return symbol.upper() in {s.upper() for s in self._critical_symbols}

    def get_flags_for(self, symbol: str) -> List[dict]:
        return [f for f in self.flags if f.get("symbol", "").upper() == symbol.upper()]

    def summary(self) -> dict:
        return {
            "total_flags": len(self.flags),
            "critical_symbols": sorted(self._critical_symbols),
        }


# ═════════════════════════════════════════════════════════════════════════════
# Strategy-Level Tracker
# ═════════════════════════════════════════════════════════════════════════════

class StrategyTracker:
    """
    Replaces:
      - simulations/forward_test_tracker.py (gates + fast elimination)
      - tools/forward_test_tracker.py (benchmark excess)
      - alpha_engine/data/forward_testing/forward_tracker.py (K1-K8 + CSV)
    """

    def __init__(self):
        self.bench_cache: dict = {}
        self.qa = QALedgerFilter()

    # ── Stats computation ──────────────────────────────────────────────────

    @staticmethod
    def compute_stats(trades: List[dict]) -> dict:
        pnls = [_f(t.get("pnl_pct")) for t in trades]
        pnls = [p for p in pnls if p is not None]
        if not pnls:
            return {
                "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
                "win_rate_pct": 0.0, "gross_profit_pct": 0.0, "gross_loss_pct": 0.0,
                "profit_factor": 0.0, "net_pnl_pct": 0.0, "max_drawdown_pct": 0.0,
                "sharpe": 0.0, "consecutive_losses": 0, "max_consecutive_losses": 0,
                "cost_ratio_pct": 0.0, "days_active": 0, "trades_per_week": 0.0,
            }

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        pf = gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0)

        cum = peak = max_dd = 0.0
        consec = max_consec = 0
        for p in pnls:
            cum += p
            peak = max(peak, cum)
            max_dd = max(max_dd, peak - cum)
            if p <= 0:
                consec += 1
                max_consec = max(max_consec, consec)
            else:
                consec = 0

        sharpe = (_safe_mean(pnls) / _safe_stdev(pnls) * (len(pnls) ** 0.5)) if len(pnls) > 1 else 0.0

        fee_pct = 0.0
        for t in trades:
            entry_p = _f(t.get("entry")) or 0
            if entry_p > 0:
                fee_pct += abs(_f(t.get("fees")) or 0) / entry_p * 100.0
        cost_ratio = (fee_pct / gross_profit * 100.0) if gross_profit > 0 else 0.0

        opened = [t.get("opened") or "" for t in trades if t.get("opened")]
        closed = [t.get("closed") or "" for t in trades if t.get("closed")]
        days = 1
        if opened and closed:
            try:
                a = min(datetime.fromisoformat(o.replace("Z", "+00:00")) for o in opened)
                b = max(datetime.fromisoformat(c.replace("Z", "+00:00")) for c in closed)
                days = max(1, int((b - a).total_seconds() / 86400) + 1)
            except ValueError:
                days = max(1, len(trades))

        return {
            "total_trades": len(pnls),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate_pct": round(len(wins) / len(pnls) * 100.0, 2),
            "gross_profit_pct": round(gross_profit, 4),
            "gross_loss_pct": round(gross_loss, 4),
            "profit_factor": round(pf, 3),
            "net_pnl_pct": round(sum(pnls), 4),
            "max_drawdown_pct": round(max_dd, 4),
            "sharpe": round(sharpe, 3),
            "consecutive_losses": consec,
            "max_consecutive_losses": max_consec,
            "cost_ratio_pct": round(cost_ratio, 2),
            "days_active": days,
            "trades_per_week": round(len(pnls) / max(days / 7.0, 0.1), 2),
        }

    # ── Kill signals ───────────────────────────────────────────────────────

    @staticmethod
    def check_kill(stats: dict) -> Tuple[bool, Optional[str], Optional[str]]:
        for code, predicate, reason in KILL_SIGNALS:
            if predicate(stats):
                return True, code, reason
        return False, None, None

    # ── Promote signals ────────────────────────────────────────────────────

    @staticmethod
    def check_promote(stats: dict) -> Tuple[bool, List[str]]:
        failures = []
        if stats["total_trades"] < PROMOTE_SIGNALS["min_trades"]:
            failures.append(f"n={stats['total_trades']} < {PROMOTE_SIGNALS['min_trades']}")
        if stats["net_pnl_pct"] <= PROMOTE_SIGNALS["net_pnl_pct"]:
            failures.append(f"net_pnl={stats['net_pnl_pct']}% <= 0")
        if stats["win_rate_pct"] < PROMOTE_SIGNALS["win_rate_pct"]:
            failures.append(f"WR={stats['win_rate_pct']}% < {PROMOTE_SIGNALS['win_rate_pct']}%")
        if stats["profit_factor"] < PROMOTE_SIGNALS["profit_factor"]:
            failures.append(f"PF={stats['profit_factor']} < {PROMOTE_SIGNALS['profit_factor']}")
        if stats["max_drawdown_pct"] > PROMOTE_SIGNALS["max_drawdown_pct"]:
            failures.append(f"maxDD={stats['max_drawdown_pct']}% > {PROMOTE_SIGNALS['max_drawdown_pct']}%")
        if stats["sharpe"] < PROMOTE_SIGNALS["sharpe"]:
            failures.append(f"Sharpe={stats['sharpe']} < {PROMOTE_SIGNALS['sharpe']}")
        if stats["trades_per_week"] < PROMOTE_SIGNALS["trades_per_week"]:
            failures.append(f"tpw={stats['trades_per_week']} < {PROMOTE_SIGNALS['trades_per_week']}")
        if stats["max_consecutive_losses"] > PROMOTE_SIGNALS["max_consecutive_losses"]:
            failures.append(f"max_consec={stats['max_consecutive_losses']} > {PROMOTE_SIGNALS['max_consecutive_losses']}")
        return len(failures) == 0, failures

    # ── Absolute gates ─────────────────────────────────────────────────────

    @staticmethod
    def check_gate(results: dict, gate_name: str) -> Tuple[bool, List[str]]:
        gate = GATES[gate_name]
        tmetrics = results.get("trade_metrics", {})
        pmetrics = results.get("portfolio_metrics", {})
        failures = []

        n = tmetrics.get("n", 0)
        pf = tmetrics.get("profit_factor", tmetrics.get("pf", 0))
        wr = tmetrics.get("win_rate", tmetrics.get("wr", 0))
        max_dd = tmetrics.get("max_drawdown", tmetrics.get("max_dd", 0))
        sharpe = tmetrics.get("sharpe_ratio", tmetrics.get("sharpe", 0))

        if n == 0 and pmetrics:
            pf = pmetrics.get("profit_factor", 0)
            wr = pmetrics.get("win_rate_daily", pmetrics.get("win_rate_monthly", 0))
            max_dd = pmetrics.get("max_drawdown", 0)
            sharpe = pmetrics.get("sharpe_ratio", 0)
            n = 9999

        checks = [
            ("n", n, gate["n_min"], ">="),
            ("profit_factor", pf, gate["pf_min"], ">="),
            ("win_rate", wr, gate["wr_min"], ">="),
            ("max_drawdown", max_dd, gate["max_dd_max"], ">="),
            ("sharpe_ratio", sharpe, gate["sharpe_min"], ">="),
        ]

        for name, value, threshold, op in checks:
            if op == ">=" and value < threshold:
                failures.append(f"{name}={value:.4f} < {threshold}")

        return len(failures) == 0, failures

    @staticmethod
    def check_fast_elimination(results: dict) -> Tuple[bool, Optional[str]]:
        tmetrics = results.get("trade_metrics", {})
        pmetrics = results.get("portfolio_metrics", {})
        n = tmetrics.get("n", 0)
        pf = tmetrics.get("profit_factor", tmetrics.get("pf", 0))
        wr = tmetrics.get("win_rate", tmetrics.get("wr", 0))
        max_dd = tmetrics.get("max_drawdown", tmetrics.get("max_dd", 0))

        if n >= FAST_ELIMINATION["n_min"]:
            if pf < FAST_ELIMINATION["pf_max"]:
                return True, f"PF={pf:.2f} < {FAST_ELIMINATION['pf_max']} after n={n}"
            if wr < FAST_ELIMINATION["wr_max"]:
                return True, f"WR={wr:.1%} < {FAST_ELIMINATION['wr_max']} after n={n}"

        if n == 0 and pmetrics:
            max_dd = pmetrics.get("max_drawdown", 0)

        if max_dd < FAST_ELIMINATION["max_dd_min"]:
            return True, f"MaxDD={max_dd:.1%} < {FAST_ELIMINATION['max_dd_min']}"

        return False, None

    # ── Benchmark-relative ─────────────────────────────────────────────────

    def compute_benchmark_excess(self, picks: List[dict]) -> dict:
        if not _HAS_YFINANCE:
            return {"verdict": "NO_YFINANCE", "n": len(picks)}

        entry_dts = [_dt(p.get("entry_date") or p.get("generated_at")) for p in picks]
        exit_dts = [_dt(p.get("exit_date") or p.get("closed_at")) for p in picks]
        entry_dts = [d for d in entry_dts if d is not None]
        exit_dts = [d for d in exit_dts if d is not None]
        if not entry_dts or not exit_dts:
            return {"verdict": "NO_DATA", "n": 0}

        global_start = min(entry_dts) - pd.Timedelta(days=40)
        global_end = max(exit_dts) + pd.Timedelta(days=10)

        rows = []
        for p in picks:
            aclass = (p.get("asset_class") or "").upper()
            bench_ticker = BENCH_TICKERS.get(aclass, BENCH_TICKERS[""])
            entry_dt = _dt(p.get("entry_date") or p.get("generated_at"))
            exit_dt = _dt(p.get("exit_date") or p.get("closed_at"))
            pnl = _f(p.get("pnl_pct"))
            if entry_dt is None or exit_dt is None or pnl is None:
                continue

            bench = self.bench_cache.setdefault(bench_ticker, {})
            if "s" not in bench:
                s = load_benchmark(bench_ticker, global_start, global_end)
                if s is None or s.empty:
                    continue
                bench["s"] = s

            br = bench_return(bench["s"], entry_dt, exit_dt)
            if br is None:
                continue

            direction = str(p.get("direction", "")).upper()
            bench_pnl = -br * 100.0 if direction in ("SHORT", "SELL", "STRONG_SELL") else br * 100.0
            excess = pnl - bench_pnl
            rows.append({
                "symbol": p.get("symbol", ""),
                "asset_class": aclass,
                "pnl_pct": pnl,
                "bench_pnl_pct": round(bench_pnl, 4),
                "excess_pct": round(excess, 4),
                "hold_days": int((exit_dt - entry_dt).days),
            })

        if not rows:
            return {"verdict": "NO_DATA", "n": 0}

        n = len(rows)
        pct_pos = sum(1 for r in rows if r["excess_pct"] > 0) / n
        med_excess = _safe_median([r["excess_pct"] for r in rows])

        ex = pd.Series([r["excess_pct"] for r in rows])
        sharpe = (ex.mean() / ex.std() * math.sqrt(52)) if ex.std() > 0 else 0.0
        eq = (1 + ex / 100).cumprod()
        dd = float((eq / eq.cummax() - 1).min()) if len(eq) else 0.0

        if n >= BENCH_ELIM["min_n"] and (pct_pos < BENCH_ELIM["pct_excess"] or med_excess < 0):
            verdict = "ELIMINATE_FAST"
            reason = (f"{pct_pos:.0%} excess>0 (<{BENCH_ELIM['pct_excess']:.0%})" if pct_pos < BENCH_ELIM["pct_excess"]
                      else f"median excess {med_excess:.2f}% < 0")
        elif n >= BENCH_ELIM["hold_n"] and (sharpe < BENCH_ELIM["sharpe"] or dd < -BENCH_ELIM["max_dd"]):
            verdict = "ELIMINATE_FAST"
            reason = (f"sharpe {sharpe:.2f} < {BENCH_ELIM['sharpe']}" if sharpe < BENCH_ELIM["sharpe"]
                      else f"maxDD {dd:.1%} < -{BENCH_ELIM['max_dd']:.0%}")
        else:
            verdict = "HOLD_EXTEND" if n >= BENCH_ELIM["hold_n"] else "MONITOR"
            reason = f"need {BENCH_ELIM['min_n']} trades for elimination gate (have {n})" if n < BENCH_ELIM["min_n"] else "consistent excess"

        return {
            "verdict": verdict,
            "reason": reason,
            "n": n,
            "pct_excess_gt_0": round(pct_pos, 4),
            "median_excess_pct": round(med_excess, 4),
            "sharpe_weekly": round(float(sharpe), 3),
            "max_drawdown_pct": round(dd * 100, 2),
            "rows": rows,
        }

    # ── Full decision ──────────────────────────────────────────────────────

    def decide(self, strategy_id: str, trades: List[dict], results_json: Optional[dict] = None) -> dict:
        stats = self.compute_stats(trades)
        kill, kill_code, kill_reason = self.check_kill(stats)
        promoted, promote_failures = self.check_promote(stats)

        # Absolute gates
        gate_pass = None
        gate_failures = []
        current_gate = None
        next_gate = None
        if results_json:
            elim, elim_reason = self.check_fast_elimination(results_json)
            if elim:
                kill = True
                kill_code = "FAST_ELIM"
                kill_reason = elim_reason
            for gname in ["paper", "probation", "small_live", "full_live"]:
                passes, failures = self.check_gate(results_json, gname)
                if passes:
                    current_gate = gname
                    gate_failures = []
                else:
                    next_gate = gname
                    gate_failures = failures
                    break

        # Benchmark excess
        bench = self.compute_benchmark_excess(trades)

        # QA filter
        symbols = {t.get("symbol", "") for t in trades}
        qa_flags = any(self.qa.is_flagged(s) for s in symbols if s)

        # Final status
        if kill:
            status = "ELIMINATED"
            action = f"STOP. {kill_code}: {kill_reason}"
        elif promoted:
            status = "EXTENDED"
            action = "PROMOTED — meets P1-P7 criteria"
        elif current_gate == "full_live":
            status = "FULL_LIVE"
            action = "Fully deployed. Monitor daily."
        elif current_gate:
            status = current_gate.upper()
            action = f"Continue at {current_gate}. Next gate: {next_gate}."
        else:
            status = "HOLD"
            action = "Continue paper trading."

        if qa_flags:
            action += " | QA_FLAGGED (see qa_market_validation.json)"

        return {
            "strategy_id": strategy_id,
            "status": status,
            "kill_code": kill_code,
            "kill_reason": kill_reason,
            "current_gate": current_gate,
            "next_gate": next_gate,
            "gate_failures": gate_failures,
            "promote_failures": promote_failures if not promoted else [],
            "metrics": stats,
            "benchmark_excess": bench,
            "qa_flagged": qa_flags,
            "action": action,
            "protocol_version": "2026-11-15-v2-canonical",
        }


# ═════════════════════════════════════════════════════════════════════════════
# Pick-Level Tracker (absorbs cross_aggregation/forward_test_tracker.py)
# ═════════════════════════════════════════════════════════════════════════════

class PickTracker:
    def __init__(self):
        self.results_file = REPO / "cross_aggregation" / "data" / "forward_test_results.json"
        self.qa = QALedgerFilter()

    def _load_results(self) -> dict:
        if self.results_file.exists():
            try:
                return json.loads(self.results_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "tracked_picks": [],
            "stats": {
                "total": 0, "active": 0, "resolved": 0, "won": 0, "lost": 0,
                "expired": 0, "wr_overall": None, "wr_fresh": None, "wr_stale": None,
                "wr_by_score": {"75-80": None, "80-85": None, "85-90": None, "90+": None},
                "avg_pnl_fresh": None, "avg_pnl_stale": None, "avg_pnl_overall": None,
                "tracking_since": None,
            },
            "last_updated": None,
        }

    def _save_results(self, data: dict):
        self.results_file.parent.mkdir(parents=True, exist_ok=True)
        self.results_file.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    @staticmethod
    def _pick_key(symbol: str, direction: str, entry: float) -> str:
        return f"{symbol.upper()}__{direction.upper()}__{round(float(entry), 4)}"

    @staticmethod
    def _similar_entry(a: float, b: float) -> bool:
        if a == 0 or b == 0:
            return False
        return abs(a - b) / max(abs(a), abs(b)) < 0.005

    @staticmethod
    def _score_bucket(score: float) -> str:
        if score >= 90:
            return "90+"
        if score >= 85:
            return "85-90"
        if score >= 80:
            return "80-85"
        return "75-80"

    def ingest(self, picks: List[dict], source_label: str = "generic") -> int:
        results = self._load_results()
        now = datetime.now(timezone.utc)
        existing_keys = {
            self._pick_key(p["symbol"], p["direction"], p["entry_price"])
            for p in results["tracked_picks"]
        }
        new_count = 0

        for pick in picks:
            symbol = pick.get("symbol", "")
            direction = pick.get("direction", "")
            entry = _f(pick.get("entry") or pick.get("entry_price") or 0)
            tp = _f(pick.get("tp") or pick.get("take_profit") or 0)
            sl = _f(pick.get("sl") or pick.get("stop_loss") or 0)
            confidence = _f(pick.get("confidence", 0))
            if not symbol or not direction or entry <= 0 or tp <= 0 or sl <= 0:
                continue
            score = confidence * 100 if confidence <= 1.0 else confidence
            if score < PICK_SCORE_THRESHOLD:
                continue

            # QA filter: skip flagged symbols at ingestion
            if self.qa.is_flagged(symbol):
                continue

            key = self._pick_key(symbol, direction, entry)
            if key in existing_keys:
                continue
            if any(
                ep["symbol"] == symbol.upper()
                and ep["direction"] == direction.upper()
                and self._similar_entry(ep["entry_price"], entry)
                for ep in results["tracked_picks"]
            ):
                continue

            age_h = 0.0
            generated_at = pick.get("generated_at", "")
            if generated_at:
                dt = _parse_iso(generated_at)
                if dt:
                    age_h = max(0.0, (now - dt).total_seconds() / 3600)

            freshness = (
                "fresh"
                if age_h <= PICK_FRESH_MAX_H
                else ("stale" if age_h >= PICK_STALE_MIN_H else "mid")
            )

            live_price = get_current_price(symbol)

            captured = {
                "symbol": symbol.upper(),
                "direction": direction.upper(),
                "entry_price": entry,
                "tp_price": tp,
                "sl_price": sl,
                "score": round(score, 1),
                "score_bucket": self._score_bucket(score),
                "confidence_raw": round(confidence, 4),
                "agreement_count": int(pick.get("agreement_count", 0)),
                "source_systems": pick.get("source_systems", pick.get("agreeing_systems", [])),
                "consensus_tier": pick.get("consensus_tier", pick.get("signal_tier", "MODERATE")),
                "source": source_label,
                "generated_at": generated_at,
                "status": "OPEN",
                "captured_at": now.isoformat(),
                "age_at_capture_hours": round(age_h, 2),
                "freshness": freshness,
                "price_at_capture": live_price,
            }
            results["tracked_picks"].append(captured)
            existing_keys.add(key)
            new_count += 1

        self._save_results(results)
        return new_count

    def check_outcomes(self) -> List[dict]:
        results = self._load_results()
        now = datetime.now(timezone.utc)
        closed_this_run = []

        for pick in results["tracked_picks"]:
            if pick.get("status") != "OPEN":
                continue

            symbol = pick["symbol"]
            direction = pick["direction"]
            entry = pick["entry_price"]
            tp = pick["tp_price"]
            sl = pick["sl_price"]

            captured_dt = _parse_iso(pick.get("captured_at", ""))
            age_h = (now - captured_dt).total_seconds() / 3600 if captured_dt else 0.0
            if age_h > PICK_EXPIRE_HOURS:
                pick["status"] = "EXPIRED"
                pick["resolved_at"] = now.isoformat()
                pick["pnl_pct"] = 0.0
                pick["close_reason"] = f"Expired after {age_h:.0f}h (limit: {PICK_EXPIRE_HOURS}h)"
                closed_this_run.append(pick)
                continue

            price = get_current_price(symbol)
            if price is None:
                continue

            pick["last_price"] = price
            pick["last_checked"] = now.isoformat()

            if direction == "LONG":
                pick["unrealized_pnl_pct"] = round((price / entry - 1) * 100, 4)
            else:
                pick["unrealized_pnl_pct"] = round((1 - price / entry) * 100, 4)

            outcome = None
            pnl = 0.0
            if direction == "LONG":
                if price >= tp:
                    outcome = "WON"
                    pnl = (tp / entry - 1) * 100
                elif price <= sl:
                    outcome = "LOST"
                    pnl = (sl / entry - 1) * 100
            else:
                if price <= tp:
                    outcome = "WON"
                    pnl = (1 - tp / entry) * 100
                elif price >= sl:
                    outcome = "LOST"
                    pnl = (1 - sl / entry) * 100

            if outcome:
                pick["status"] = outcome
                pick["exit_price"] = price
                pick["pnl_pct"] = round(pnl, 4)
                pick["resolved_at"] = now.isoformat()
                closed_this_run.append(pick)

        self._save_results(results)
        self._recompute_stats(results)
        return closed_this_run

    def _recompute_stats(self, results: dict):
        all_picks = results["tracked_picks"]
        open_picks = [p for p in all_picks if p.get("status") == "OPEN"]
        won = [p for p in all_picks if p.get("status") == "WON"]
        lost = [p for p in all_picks if p.get("status") == "LOST"]
        expired = [p for p in all_picks if p.get("status") == "EXPIRED"]
        resolved = won + lost

        def _wr(picks):
            decided = [p for p in picks if p.get("status") in ("WON", "LOST")]
            if not decided:
                return None
            return round(sum(1 for p in decided if p.get("status") == "WON") / len(decided) * 100, 1)

        def _avg_pnl(picks):
            decided = [p for p in picks if p.get("status") in ("WON", "LOST")]
            if not decided:
                return None
            return round(sum(float(p.get("pnl_pct", 0) or 0) for p in decided) / len(decided), 2)

        fresh = [p for p in all_picks if p.get("freshness") == "fresh"]
        stale = [p for p in all_picks if p.get("freshness") == "stale"]

        buckets = {"75-80": [], "80-85": [], "85-90": [], "90+": []}
        for p in all_picks:
            b = p.get("score_bucket", "75-80")
            if b in buckets:
                buckets[b].append(p)

        all_times = [p.get("captured_at", "") for p in all_picks if p.get("captured_at")]
        results["stats"] = {
            "total": len(all_picks),
            "active": len(open_picks),
            "resolved": len(resolved),
            "won": len(won),
            "lost": len(lost),
            "expired": len(expired),
            "wr_overall": _wr(resolved) if resolved else None,
            "wr_fresh": _wr(fresh),
            "wr_stale": _wr(stale),
            "wr_by_score": {b: _wr(picks) for b, picks in buckets.items()},
            "avg_pnl_fresh": _avg_pnl(fresh),
            "avg_pnl_stale": _avg_pnl(stale),
            "avg_pnl_overall": _avg_pnl(resolved),
            "tracking_since": min(all_times) if all_times else None,
            "count_fresh": len(fresh),
            "count_stale": len(stale),
            "count_mid": len([p for p in all_picks if p.get("freshness") == "mid"]),
            "count_by_score": {b: len(picks) for b, picks in buckets.items()},
        }

        resolved_sorted = sorted(
            [p for p in all_picks if p.get("status") != "OPEN"],
            key=lambda p: p.get("resolved_at", p.get("captured_at", "")),
        )
        if len(resolved_sorted) > PICK_MAX_CLOSED:
            resolved_sorted = resolved_sorted[-PICK_MAX_CLOSED:]
        results["tracked_picks"] = open_picks + resolved_sorted
        results["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save_results(results)


# ═════════════════════════════════════════════════════════════════════════════
# Legacy CSV Adapter
# ═════════════════════════════════════════════════════════════════════════════

class LegacyCSVAdapter:
    """Reads legacy CSVs from alpha_engine/data/forward_testing/"""

    TRACKER_CSV = DATA_DIR / "forward_test_tracker.csv"
    LEDGER_CSV = DATA_DIR / "forward_test_trades.csv"
    ELIMINATED_CSV = DATA_DIR / "forward_test_eliminated.csv"

    @staticmethod
    def read_csv(path: Path) -> List[dict]:
        if not path.exists():
            return []
        with path.open(newline="") as fh:
            return [dict(r) for r in csv.DictReader(fh)]

    def load_trades(self, strategy_id: Optional[str] = None) -> List[dict]:
        rows = self.read_csv(self.LEDGER_CSV)
        if strategy_id:
            rows = [r for r in rows if r.get("strategy_id") == strategy_id]
        return rows

    def load_all_strategies(self) -> List[dict]:
        tracker = self.read_csv(self.TRACKER_CSV)
        eliminated = self.read_csv(self.ELIMINATED_CSV)
        return tracker + eliminated


# ═════════════════════════════════════════════════════════════════════════════
# CLI / Main
# ═════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical Forward-Test Tracker")
    parser.add_argument("--mode", choices=["strategy", "pick", "unified"], default="unified")
    parser.add_argument("--results-dir", type=Path, default=None, help="Directory of result JSONs for strategy mode")
    parser.add_argument("--strategy-id", type=str, default=None, help="Single strategy to evaluate")
    parser.add_argument("--picks-json", type=Path, default=None, help="JSON of picks to ingest for pick mode")
    parser.add_argument("--output-json", type=Path, default=OUT_JSON)
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if args.mode == "strategy":
        tracker = StrategyTracker()
        adapter = LegacyCSVAdapter()
        decisions = []

        if args.strategy_id:
            trades = adapter.load_trades(args.strategy_id)
            res_json = None
            if args.results_dir:
                for f in args.results_dir.glob("results_*.json"):
                    try:
                        d = json.loads(f.read_text())
                        if d.get("simulation") == args.strategy_id:
                            res_json = d
                            break
                    except Exception:
                        pass
            decision = tracker.decide(args.strategy_id, trades, res_json)
            decisions.append(decision)
            print(f"{decision['strategy_id']} -> {decision['status']} | {decision['action']}")
        else:
            strategies = adapter.load_all_strategies()
            seen = set()
            for row in strategies:
                sid = row.get("strategy_id")
                if not sid or sid in seen:
                    continue
                seen.add(sid)
                trades = adapter.load_trades(sid)
                decision = tracker.decide(sid, trades)
                decisions.append(decision)
                print(f"{sid:30s} -> {decision['status']:12s} | {decision['action'][:60]}")

        args.output_json.write_text(json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "strategy",
            "decisions": decisions,
        }, indent=2))
        print(f"\nWrote {args.output_json}")

    elif args.mode == "pick":
        pick_tracker = PickTracker()
        if args.picks_json:
            picks = json.loads(args.picks_json.read_text())
            if isinstance(picks, dict):
                picks = picks.get("picks", picks.get("consensus_picks", []))
            new = pick_tracker.ingest(picks)
            print(f"Ingested {new} new picks")
        exits = pick_tracker.check_outcomes()
        print(f"Exits this run: {len(exits)}")
        results = pick_tracker._load_results()
        s = results["stats"]
        print(f"Total: {s['total']} Active: {s['active']} Won: {s['won']} Lost: {s['lost']} Expired: {s['expired']}")

    else:  # unified
        tracker = StrategyTracker()
        adapter = LegacyCSVAdapter()
        strategies = adapter.load_all_strategies()
        seen = set()
        strategy_decisions = []
        for row in strategies:
            sid = row.get("strategy_id")
            if not sid or sid in seen:
                continue
            seen.add(sid)
            trades = adapter.load_trades(sid)
            strategy_decisions.append(tracker.decide(sid, trades))

        pick_tracker = PickTracker()
        pick_exits = pick_tracker.check_outcomes()
        pick_results = pick_tracker._load_results()

        unified = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "protocol_version": "2026-11-15-v2-canonical",
            "mode": "unified",
            "strategy_decisions": strategy_decisions,
            "pick_stats": pick_results.get("stats", {}),
            "pick_exits_this_run": len(pick_exits),
            "qa_summary": tracker.qa.summary(),
        }
        args.output_json.write_text(json.dumps(unified, indent=2))
        print(f"Unified output: {args.output_json}")
        print(f"Strategies evaluated: {len(strategy_decisions)}")
        print(f"Pick exits: {len(pick_exits)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
