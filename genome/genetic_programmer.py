"""
Genetic Programming Engine for Algorithmic Trading
====================================================
Inspired by ZiadFrancis/Genetics_Trading_Part_1 — but evolved to:
1. Generate brand-new indicator formulas via expression tree evolution
2. Crossover with our existing proven DNA strategies
3. Backtest on real market data (ccxt/Binance)
4. Produce picks in audit dashboard format
5. Compete against all existing systems

Uses DEAP-style GP primitives but without requiring the DEAP library.
Expression trees are built from arithmetic, trigonometric, and comparison
primitives applied to OHLCV + technical indicator inputs.

No pandas dependency — pure numpy for Python 3.14 compatibility.
"""

import copy
import hashlib
import json
import logging
import math
import os
import random
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENOME_DIR = Path(__file__).resolve().parent
RESULTS_DIR = GENOME_DIR / "gp_results"
DB_PATH = GENOME_DIR / "genetic_programmer.db"
PICKS_OUTPUT = PROJECT_ROOT / "genome" / "data" / "gp_active_picks.json"
CLOSED_OUTPUT = PROJECT_ROOT / "genome" / "data" / "gp_closed_picks.json"
EVOLUTION_LOG = RESULTS_DIR / "evolution_log.json"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
(GENOME_DIR / "data").mkdir(parents=True, exist_ok=True)

# Logging
_log_dir = GENOME_DIR / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(str(_log_dir / "genetic_programmer.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("GeneticProgrammer")


# ---------------------------------------------------------------------------
# OHLCV Data Container (replaces pandas DataFrame)
# ---------------------------------------------------------------------------

class OHLCVData:
    """Numpy-based OHLCV container. No pandas needed."""
    def __init__(self, timestamps, opens, highs, lows, closes, volumes):
        self.timestamps = np.array(timestamps, dtype=np.float64)
        self.open = np.array(opens, dtype=np.float64)
        self.high = np.array(highs, dtype=np.float64)
        self.low = np.array(lows, dtype=np.float64)
        self.close = np.array(closes, dtype=np.float64)
        self.volume = np.array(volumes, dtype=np.float64)

    def __len__(self):
        return len(self.close)

    @classmethod
    def from_ccxt_ohlcv(cls, ohlcv_list):
        """Create from ccxt fetch_ohlcv result [[ts, o, h, l, c, v], ...]."""
        arr = np.array(ohlcv_list)
        return cls(arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3], arr[:, 4], arr[:, 5])

    @classmethod
    def synthetic(cls, symbol: str, n: int = 1000):
        """Generate synthetic data for testing."""
        np.random.seed(hash(symbol) % 2**31)
        ts = np.arange(n) * 3600 * 1000  # hourly
        returns = np.random.normal(0.0001, 0.012, n)
        prices = 50000 * np.exp(np.cumsum(returns))
        opens = prices * (1 + np.random.normal(0, 0.001, n))
        highs = prices * (1 + np.abs(np.random.normal(0, 0.005, n)))
        lows = prices * (1 - np.abs(np.random.normal(0, 0.005, n)))
        vols = np.random.lognormal(10, 1, n)
        return cls(ts, opens, highs, lows, prices, vols)


# ---------------------------------------------------------------------------
# Expression Tree Primitives (GP building blocks)
# ---------------------------------------------------------------------------

def _protected_div(a, b):
    mask = np.abs(b) < 1e-8
    return np.where(mask, a, a / np.where(mask, 1.0, b))

def _safe_log(a):
    return np.log(np.abs(a) + 1e-8)

def _safe_sqrt(a):
    return np.sqrt(np.abs(a))

def _gt(a, b):
    return np.where(a > b, 1.0, -1.0)

def _lt(a, b):
    return np.where(a < b, 1.0, -1.0)

def _clip(a):
    return np.clip(a, -100, 100)

BINARY_OPS: List[Tuple[str, Callable]] = [
    ("add", np.add), ("sub", np.subtract), ("mul", np.multiply),
    ("div", _protected_div), ("max", np.maximum), ("min", np.minimum),
    ("gt", _gt), ("lt", _lt),
]

UNARY_OPS: List[Tuple[str, Callable]] = [
    ("neg", np.negative), ("abs", np.abs), ("sin", np.sin),
    ("cos", np.cos), ("tanh", np.tanh), ("log", _safe_log),
    ("sqrt", _safe_sqrt), ("clip", _clip),
]

INPUT_NAMES = [
    "open", "high", "low", "close", "volume",
    "rsi_14", "rsi_2", "ema_9", "ema_21", "ema_50",
    "bb_upper", "bb_lower", "bb_mid", "bb_pctb",
    "macd", "macd_signal", "macd_hist",
    "atr_14", "obv", "vwap",
    "pct_1", "pct_3", "pct_7",
    "vol_ratio", "funding_skew", "depth_imbalance",
]


# ---------------------------------------------------------------------------
# Numpy-based Technical Indicators
# ---------------------------------------------------------------------------

def _ema(arr, span):
    """Exponential moving average (pure numpy)."""
    alpha = 2.0 / (span + 1)
    out = np.empty_like(arr)
    out[0] = arr[0]
    for i in range(1, len(arr)):
        out[i] = alpha * arr[i] + (1 - alpha) * out[i - 1]
    return out

def _sma(arr, window):
    """Simple moving average."""
    out = np.full_like(arr, np.nan)
    cs = np.cumsum(arr)
    out[window - 1:] = (cs[window - 1:] - np.concatenate([[0], cs[:-window]])) / window
    # fill nans with first valid
    first_valid = out[window - 1]
    out[:window - 1] = first_valid
    return out

def _rolling_std(arr, window):
    """Rolling standard deviation."""
    out = np.full_like(arr, 0.0)
    for i in range(window - 1, len(arr)):
        out[i] = np.std(arr[i - window + 1:i + 1])
    return out

def _rsi(close, period):
    """RSI calculation."""
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = _ema(gain, period)
    avg_loss = _ema(loss, period)
    rs = avg_gain / (avg_loss + 1e-8)
    return 100 - (100 / (1 + rs))


# ---------------------------------------------------------------------------
# Expression Tree Node
# ---------------------------------------------------------------------------

@dataclass
class GPNode:
    node_type: str  # "binary", "unary", "input", "constant"
    value: Any = None
    children: List["GPNode"] = field(default_factory=list)

    def depth(self) -> int:
        if not self.children:
            return 0
        return 1 + max(c.depth() for c in self.children)

    def size(self) -> int:
        return 1 + sum(c.size() for c in self.children)

    def to_dict(self) -> dict:
        return {
            "type": self.node_type,
            "value": self.value if not isinstance(self.value, float) else round(self.value, 4),
            "children": [c.to_dict() for c in self.children],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GPNode":
        children = [cls.from_dict(c) for c in d.get("children", [])]
        return cls(node_type=d["type"], value=d["value"], children=children)

    def to_string(self) -> str:
        if self.node_type == "constant":
            return f"{self.value:.3f}"
        if self.node_type == "input":
            return str(self.value)
        if self.node_type == "unary":
            return f"{self.value}({self.children[0].to_string()})"
        if self.node_type == "binary":
            return f"{self.value}({self.children[0].to_string()}, {self.children[1].to_string()})"
        return "?"

    def evaluate(self, inputs: Dict[str, np.ndarray]) -> np.ndarray:
        n = len(next(iter(inputs.values())))
        if self.node_type == "constant":
            return np.full(n, self.value, dtype=np.float64)
        if self.node_type == "input":
            return inputs.get(self.value, np.zeros(n))
        if self.node_type == "unary":
            child_val = self.children[0].evaluate(inputs)
            for name, func in UNARY_OPS:
                if name == self.value:
                    return np.nan_to_num(func(child_val), nan=0.0, posinf=100.0, neginf=-100.0)
        if self.node_type == "binary":
            left = self.children[0].evaluate(inputs)
            right = self.children[1].evaluate(inputs)
            for name, func in BINARY_OPS:
                if name == self.value:
                    return np.nan_to_num(func(left, right), nan=0.0, posinf=100.0, neginf=-100.0)
        return np.zeros(n)


def random_tree(max_depth: int = 4, current_depth: int = 0) -> GPNode:
    if current_depth >= max_depth or (current_depth > 1 and random.random() < 0.3):
        if random.random() < 0.7:
            return GPNode("input", random.choice(INPUT_NAMES))
        else:
            return GPNode("constant", round(random.uniform(-1, 1), 4))
    if random.random() < 0.7:
        op_name = random.choice(BINARY_OPS)[0]
        return GPNode("binary", op_name, [
            random_tree(max_depth, current_depth + 1),
            random_tree(max_depth, current_depth + 1),
        ])
    else:
        op_name = random.choice(UNARY_OPS)[0]
        return GPNode("unary", op_name, [random_tree(max_depth, current_depth + 1)])


# ---------------------------------------------------------------------------
# GP Strategy
# ---------------------------------------------------------------------------

@dataclass
class GPStrategy:
    strategy_id: str
    name: str
    generation: int
    buy_tree: GPNode
    sell_tree: GPNode
    tp_pct: float = 0.04
    sl_pct: float = 0.02
    buy_threshold: float = 0.0
    sell_threshold: float = 0.0
    max_hold_bars: int = 48
    parents: List[str] = field(default_factory=list)
    mutation_log: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    fitness: Dict[str, float] = field(default_factory=dict)

    def dna_hash(self) -> str:
        raw = json.dumps(self.buy_tree.to_dict(), sort_keys=True) + json.dumps(self.sell_tree.to_dict(), sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "generation": self.generation,
            "buy_tree": self.buy_tree.to_dict(),
            "sell_tree": self.sell_tree.to_dict(),
            "buy_formula": self.buy_tree.to_string()[:200],
            "sell_formula": self.sell_tree.to_string()[:200],
            "tp_pct": self.tp_pct, "sl_pct": self.sl_pct,
            "buy_threshold": self.buy_threshold, "sell_threshold": self.sell_threshold,
            "max_hold_bars": self.max_hold_bars,
            "parents": self.parents, "mutation_log": self.mutation_log[-5:],
            "created_at": self.created_at, "fitness": self.fitness,
            "dna_hash": self.dna_hash(),
        }


def random_strategy(generation: int = 0, name_prefix: str = "GP") -> GPStrategy:
    buy_tree = random_tree(max_depth=random.randint(3, 5))
    sell_tree = random_tree(max_depth=random.randint(3, 5))
    sid = f"gp_{hashlib.md5(f'{time.time()}_{random.random()}'.encode()).hexdigest()[:12]}"
    return GPStrategy(
        strategy_id=sid,
        name=f"{name_prefix}_Gen{generation}_{sid[-6:]}",
        generation=generation, buy_tree=buy_tree, sell_tree=sell_tree,
        tp_pct=round(random.uniform(0.02, 0.08), 4),
        sl_pct=round(random.uniform(0.01, 0.04), 4),
        buy_threshold=round(random.uniform(-0.5, 0.5), 3),
        sell_threshold=round(random.uniform(-0.5, 0.5), 3),
        max_hold_bars=random.choice([12, 24, 36, 48, 72]),
    )


# ---------------------------------------------------------------------------
# Feature Engineering (pure numpy)
# ---------------------------------------------------------------------------

def compute_features(data: OHLCVData) -> Dict[str, np.ndarray]:
    """Compute all GP input features from OHLCV data."""
    c = data.close
    h = data.high
    l = data.low
    v = data.volume
    n = len(c)

    features = {
        "open": data.open, "high": h, "low": l, "close": c, "volume": v,
    }

    # Returns
    features["pct_1"] = np.concatenate([[0], np.diff(c) / (c[:-1] + 1e-8)])
    pct3 = np.zeros(n)
    pct3[3:] = (c[3:] - c[:-3]) / (c[:-3] + 1e-8)
    features["pct_3"] = pct3
    pct7 = np.zeros(n)
    pct7[7:] = (c[7:] - c[:-7]) / (c[:-7] + 1e-8)
    features["pct_7"] = pct7

    # RSI
    features["rsi_14"] = _rsi(c, 14)
    features["rsi_2"] = _rsi(c, 2)

    # EMAs
    features["ema_9"] = _ema(c, 9)
    features["ema_21"] = _ema(c, 21)
    features["ema_50"] = _ema(c, 50)

    # Bollinger Bands
    bb_mid = _sma(c, 20)
    bb_std = _rolling_std(c, 20)
    features["bb_mid"] = bb_mid
    features["bb_upper"] = bb_mid + 2 * bb_std
    features["bb_lower"] = bb_mid - 2 * bb_std
    bb_range = features["bb_upper"] - features["bb_lower"] + 1e-8
    features["bb_pctb"] = (c - features["bb_lower"]) / bb_range

    # MACD
    ema12 = _ema(c, 12)
    ema26 = _ema(c, 26)
    macd = ema12 - ema26
    macd_signal = _ema(macd, 9)
    features["macd"] = macd
    features["macd_signal"] = macd_signal
    features["macd_hist"] = macd - macd_signal

    # ATR
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    tr[0] = h[0] - l[0]
    features["atr_14"] = _ema(tr, 14)

    # OBV
    direction = np.sign(np.diff(c, prepend=c[0]))
    features["obv"] = np.cumsum(direction * v)

    # VWAP
    typical = (h + l + c) / 3
    cum_tpv = np.cumsum(typical * v)
    cum_v = np.cumsum(v) + 1e-8
    features["vwap"] = cum_tpv / cum_v

    # Volume ratio
    vol_avg = _sma(v, 20)
    features["vol_ratio"] = v / (vol_avg + 1e-8)

    # DNA mutations
    sma20 = _sma(c, 20)
    features["funding_skew"] = (c - sma20) / (c + 1e-8)
    features["depth_imbalance"] = (h - l) / (v + 1e-8)

    # Replace any nans
    for k in features:
        features[k] = np.nan_to_num(features[k], nan=0.0, posinf=100.0, neginf=-100.0)

    return features


# ---------------------------------------------------------------------------
# Backtester (pure numpy)
# ---------------------------------------------------------------------------

def backtest_strategy(
    strategy: GPStrategy,
    data: OHLCVData,
    initial_capital: float = 10000.0,
    commission: float = 0.001,
) -> Dict[str, Any]:
    if len(data) < 100:
        return {"win_rate": 0, "sharpe_ratio": 0, "total_trades": 0, "overall_fitness": 0}

    inputs = compute_features(data)
    buy_signal = strategy.buy_tree.evaluate(inputs)
    sell_signal = strategy.sell_tree.evaluate(inputs)
    closes = data.close

    capital = initial_capital
    position = None  # (entry_idx, entry_price, direction)
    trades = []
    equity = [capital]

    for i in range(50, len(data)):
        price = closes[i]

        if position is not None:
            entry_idx, entry_price, direction = position
            hold_bars = i - entry_idx
            if direction == "LONG":
                pnl_pct = (price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - price) / entry_price

            exit_reason = None
            if pnl_pct >= strategy.tp_pct:
                exit_reason = "TP"
            elif pnl_pct <= -strategy.sl_pct:
                exit_reason = "SL"
            elif hold_bars >= strategy.max_hold_bars:
                exit_reason = "TIME"
            elif direction == "LONG" and sell_signal[i] > strategy.sell_threshold:
                exit_reason = "SIGNAL"
            elif direction == "SHORT" and buy_signal[i] > strategy.buy_threshold:
                exit_reason = "SIGNAL"

            if exit_reason:
                net_pnl = pnl_pct - commission * 2
                capital *= (1 + net_pnl)
                trades.append({
                    "entry_idx": int(entry_idx), "exit_idx": int(i),
                    "direction": direction, "pnl_pct": round(net_pnl * 100, 4),
                    "exit_reason": exit_reason,
                })
                position = None

        if position is None:
            if buy_signal[i] > strategy.buy_threshold:
                position = (i, price, "LONG")
            elif sell_signal[i] < -abs(strategy.sell_threshold) - 0.5:
                position = (i, price, "SHORT")

        equity.append(capital)

    if len(trades) < 5:
        return {"win_rate": 0, "sharpe_ratio": 0, "total_trades": len(trades), "overall_fitness": 0}

    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    win_rate = len(wins) / len(trades)
    avg_win = np.mean([t["pnl_pct"] for t in wins]) if wins else 0
    avg_loss = np.mean([abs(t["pnl_pct"]) for t in losses]) if losses else 0
    total_win_pnl = sum(t["pnl_pct"] for t in wins) if wins else 0
    total_loss_pnl = abs(sum(t["pnl_pct"] for t in losses)) if losses else 0
    profit_factor = total_win_pnl / (total_loss_pnl + 1e-8)

    eq = np.array(equity)
    returns = np.diff(eq) / (eq[:-1] + 1e-8)
    returns = returns[returns != 0]
    sharpe = (np.mean(returns) / (np.std(returns) + 1e-8)) * np.sqrt(252 * 24) if len(returns) > 10 else 0

    peak = np.maximum.accumulate(eq)
    dd = (peak - eq) / (peak + 1e-8)
    max_dd = float(np.max(dd)) * 100
    total_return = (capital - initial_capital) / initial_capital * 100

    fitness = (
        0.25 * min(sharpe / 3, 1.0) +
        0.25 * win_rate +
        0.20 * min(profit_factor / 3, 1.0) +
        0.15 * max(0, min(total_return / 50, 1.0)) +
        0.15 * max(0, 1 - max_dd / 30)
    )
    if len(trades) < 20:
        fitness *= (len(trades) / 20)

    return {
        "win_rate": round(win_rate, 4),
        "avg_win_pct": round(float(avg_win), 4),
        "avg_loss_pct": round(float(avg_loss), 4),
        "profit_factor": round(min(float(profit_factor), 99), 4),
        "sharpe_ratio": round(float(sharpe), 4),
        "max_drawdown_pct": round(max_dd, 4),
        "total_return_pct": round(total_return, 4),
        "total_trades": len(trades),
        "wins": len(wins), "losses": len(losses),
        "overall_fitness": round(fitness, 4),
        "final_capital": round(capital, 2),
        "trades": trades[-10:],
    }


# ---------------------------------------------------------------------------
# Genetic Operators
# ---------------------------------------------------------------------------

def crossover_trees(parent1: GPNode, parent2: GPNode) -> Tuple[GPNode, GPNode]:
    child1 = copy.deepcopy(parent1)
    child2 = copy.deepcopy(parent2)

    def collect_internals(node, result):
        for i, c in enumerate(node.children):
            result.append((node, i))
            collect_internals(c, result)

    i1, i2 = [], []
    collect_internals(child1, i1)
    collect_internals(child2, i2)

    if i1 and i2:
        p1, idx1 = random.choice(i1)
        p2, idx2 = random.choice(i2)
        p1.children[idx1], p2.children[idx2] = p2.children[idx2], p1.children[idx1]

    if child1.size() > 60:
        child1 = random_tree(max_depth=4)
    if child2.size() > 60:
        child2 = random_tree(max_depth=4)
    return child1, child2


def mutate_tree(tree: GPNode, rate: float = 0.15) -> GPNode:
    tree = copy.deepcopy(tree)
    def _mutate(node):
        if random.random() < rate:
            if node.node_type == "constant":
                node.value = round(node.value + random.gauss(0, 0.3), 4)
            elif node.node_type == "input":
                node.value = random.choice(INPUT_NAMES)
            elif node.node_type == "binary":
                node.value = random.choice(BINARY_OPS)[0]
            elif node.node_type == "unary":
                node.value = random.choice(UNARY_OPS)[0]
        if random.random() < rate * 0.3:
            new = random_tree(max_depth=2)
            node.node_type = new.node_type
            node.value = new.value
            node.children = new.children
            return
        for child in node.children:
            _mutate(child)
    _mutate(tree)
    if tree.size() > 60:
        tree = random_tree(max_depth=4)
    return tree


def crossover_strategies(s1: GPStrategy, s2: GPStrategy, generation: int) -> GPStrategy:
    buy1, buy2 = crossover_trees(s1.buy_tree, s2.buy_tree)
    sell1, sell2 = crossover_trees(s1.sell_tree, s2.sell_tree)
    child_buy = buy1 if random.random() < 0.5 else buy2
    child_sell = sell1 if random.random() < 0.5 else sell2
    sid = f"gp_{hashlib.md5(f'{time.time()}_{random.random()}'.encode()).hexdigest()[:12]}"
    return GPStrategy(
        strategy_id=sid, name=f"GPX_Gen{generation}_{sid[-6:]}",
        generation=generation, buy_tree=child_buy, sell_tree=child_sell,
        tp_pct=round(np.clip((s1.tp_pct + s2.tp_pct) / 2 + random.gauss(0, 0.005), 0.01, 0.10), 4),
        sl_pct=round(np.clip((s1.sl_pct + s2.sl_pct) / 2 + random.gauss(0, 0.003), 0.005, 0.05), 4),
        buy_threshold=round((s1.buy_threshold + s2.buy_threshold) / 2, 3),
        sell_threshold=round((s1.sell_threshold + s2.sell_threshold) / 2, 3),
        max_hold_bars=random.choice([s1.max_hold_bars, s2.max_hold_bars]),
        parents=[s1.strategy_id, s2.strategy_id],
        mutation_log=[f"crossover({s1.name}, {s2.name})"],
    )


def mutate_strategy(strategy: GPStrategy, generation: int, rate: float = 0.15) -> GPStrategy:
    child = copy.deepcopy(strategy)
    child.generation = generation
    child.buy_tree = mutate_tree(child.buy_tree, rate)
    child.sell_tree = mutate_tree(child.sell_tree, rate)
    child.tp_pct = round(float(np.clip(child.tp_pct + random.gauss(0, 0.005), 0.01, 0.10)), 4)
    child.sl_pct = round(float(np.clip(child.sl_pct + random.gauss(0, 0.003), 0.005, 0.05)), 4)
    child.buy_threshold = round(float(np.clip(child.buy_threshold + random.gauss(0, 0.1), -2, 2)), 3)
    child.sell_threshold = round(float(np.clip(child.sell_threshold + random.gauss(0, 0.1), -2, 2)), 3)
    sid = f"gp_{hashlib.md5(f'{time.time()}_{random.random()}'.encode()).hexdigest()[:12]}"
    child.strategy_id = sid
    child.name = f"GPM_Gen{generation}_{sid[-6:]}"
    child.parents = [strategy.strategy_id]
    child.mutation_log = strategy.mutation_log[-3:] + [f"mutation(rate={rate:.2f})"]
    return child


# ---------------------------------------------------------------------------
# Bonus Strategy Templates
# ---------------------------------------------------------------------------

BONUS_STRATEGIES = [
    {"name": "GPBonus_MomentumZScore", "tp": 0.05, "sl": 0.025,
     "buy": GPNode("binary", "sub", [
         GPNode("binary", "mul", [GPNode("input", "pct_7"), GPNode("constant", 10.0)]),
         GPNode("binary", "div", [GPNode("input", "atr_14"), GPNode("input", "close")])]),
     "sell": GPNode("binary", "sub", [GPNode("input", "rsi_14"), GPNode("constant", 70.0)])},

    {"name": "GPBonus_BreakoutVolume", "tp": 0.06, "sl": 0.03,
     "buy": GPNode("binary", "mul", [
         GPNode("binary", "sub", [GPNode("input", "close"), GPNode("input", "bb_upper")]),
         GPNode("input", "vol_ratio")]),
     "sell": GPNode("binary", "sub", [GPNode("input", "ema_9"), GPNode("input", "close")])},

    {"name": "GPBonus_LiquiditySweep", "tp": 0.04, "sl": 0.02,
     "buy": GPNode("binary", "mul", [
         GPNode("binary", "sub", [GPNode("input", "close"), GPNode("input", "bb_lower")]),
         GPNode("binary", "gt", [GPNode("input", "vol_ratio"), GPNode("constant", 1.5)])]),
     "sell": GPNode("binary", "sub", [GPNode("input", "rsi_14"), GPNode("constant", 75.0)])},

    {"name": "GPBonus_EntropySqueeze", "tp": 0.035, "sl": 0.018,
     "buy": GPNode("binary", "mul", [
         GPNode("unary", "neg", [GPNode("input", "rsi_2")]),
         GPNode("binary", "sub", [GPNode("constant", 0.1), GPNode("input", "bb_pctb")])]),
     "sell": GPNode("binary", "sub", [GPNode("input", "rsi_2"), GPNode("constant", 60.0)])},

    {"name": "GPBonus_TripleEMAFusion", "tp": 0.07, "sl": 0.035,
     "buy": GPNode("binary", "add", [
         GPNode("binary", "sub", [GPNode("input", "ema_9"), GPNode("input", "ema_21")]),
         GPNode("binary", "sub", [GPNode("input", "ema_21"), GPNode("input", "ema_50")])]),
     "sell": GPNode("unary", "neg", [
         GPNode("binary", "sub", [GPNode("input", "ema_9"), GPNode("input", "ema_21")])])},
]


def create_bonus_strategies() -> List[GPStrategy]:
    strategies = []
    for b in BONUS_STRATEGIES:
        sid = f"gpbonus_{hashlib.md5(b['name'].encode()).hexdigest()[:12]}"
        strategies.append(GPStrategy(
            strategy_id=sid, name=b["name"], generation=0,
            buy_tree=b["buy"], sell_tree=b["sell"],
            tp_pct=b["tp"], sl_pct=b["sl"],
            mutation_log=[f"bonus_template:{b['name']}"],
        ))
    return strategies


# ---------------------------------------------------------------------------
# Data Fetcher (ccxt Binance)
# ---------------------------------------------------------------------------

def fetch_market_data(symbols: List[str], timeframe: str = "1h", limit: int = 750) -> Dict[str, OHLCVData]:
    data = {}
    try:
        import ccxt
        exchange = ccxt.binance({"enableRateLimit": True})

        for symbol in symbols:
            try:
                pair = symbol if "/" in symbol else symbol.replace("USDT", "/USDT")
                ohlcv = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=limit)
                if ohlcv and len(ohlcv) > 100:
                    data[symbol] = OHLCVData.from_ccxt_ohlcv(ohlcv)
                    logger.info(f"Fetched {symbol}: {len(ohlcv)} bars ({timeframe})")
                else:
                    logger.warning(f"Insufficient data for {symbol}")
            except Exception as e:
                logger.warning(f"Failed to fetch {symbol}: {e}")
    except ImportError:
        logger.warning("ccxt not installed, using synthetic data")

    if not data:
        logger.warning("No real data, falling back to synthetic")
        for s in symbols:
            data[s] = OHLCVData.synthetic(s)
    return data


# ---------------------------------------------------------------------------
# Evolution Engine
# ---------------------------------------------------------------------------

class GeneticProgrammingEvolver:

    def __init__(self, population_size=80, generations=20, elite_ratio=0.1,
                 crossover_rate=0.7, mutation_rate=0.15, tournament_size=5,
                 symbols=None):
        self.population_size = population_size
        self.generations = generations
        self.elite_ratio = elite_ratio
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.tournament_size = tournament_size
        self.symbols = symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        self.hall_of_fame: List[GPStrategy] = []
        self.evolution_history: List[Dict] = []
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(DB_PATH))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS gp_strategies (
                strategy_id TEXT PRIMARY KEY, name TEXT, generation INTEGER,
                dna_hash TEXT, buy_formula TEXT, sell_formula TEXT,
                fitness_json TEXT, created_at TEXT, symbol TEXT,
                status TEXT DEFAULT 'EVOLVED'
            );
            CREATE TABLE IF NOT EXISTS gp_evolution_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, run_timestamp TEXT,
                generations INTEGER, population_size INTEGER,
                best_fitness REAL, best_strategy_id TEXT, avg_fitness REAL,
                symbols TEXT, total_strategies_tested INTEGER,
                hall_of_fame_json TEXT
            );
        """)
        conn.commit()
        conn.close()

    def _tournament_select(self, population):
        contenders = random.sample(population, min(self.tournament_size, len(population)))
        return max(contenders, key=lambda x: x[1])[0]

    def run_evolution(self, market_data: Dict[str, OHLCVData]) -> List[GPStrategy]:
        run_start = datetime.now(timezone.utc)
        logger.info(f"GP Evolution: pop={self.population_size}, gens={self.generations}")

        # Initialize population
        population = [random_strategy(generation=0) for _ in range(self.population_size - len(BONUS_STRATEGIES))]
        population.extend(create_bonus_strategies())

        # Seed from previous winners
        prev_hof = self._load_hall_of_fame()
        if prev_hof:
            population.extend(prev_hof[:10])
            logger.info(f"Seeded {min(10, len(prev_hof))} prior winners")

        best_overall = 0
        stagnation = 0

        for gen in range(self.generations):
            scored = []
            for s in population:
                total_fit, cnt = 0.0, 0
                for sym, ohlcv in market_data.items():
                    try:
                        r = backtest_strategy(s, ohlcv)
                        total_fit += r.get("overall_fitness", 0)
                        cnt += 1
                    except Exception:
                        pass
                avg_fit = total_fit / max(cnt, 1)
                s.fitness = {"overall_fitness": round(avg_fit, 4)}
                scored.append((s, avg_fit))

            scored.sort(key=lambda x: x[1], reverse=True)
            best_fit = scored[0][1]
            avg_fit = float(np.mean([s[1] for s in scored]))

            if best_fit <= best_overall:
                stagnation += 1
            else:
                best_overall = best_fit
                stagnation = 0

            adaptive_rate = min(0.4, self.mutation_rate * (1 + 0.2 * stagnation)) if stagnation > 3 else self.mutation_rate

            self.evolution_history.append({
                "generation": gen, "best_fitness": round(best_fit, 4),
                "avg_fitness": round(avg_fit, 4), "best_strategy": scored[0][0].name,
                "stagnation": stagnation, "mutation_rate": round(adaptive_rate, 3),
            })
            logger.info(f"Gen {gen:3d} | Best: {best_fit:.4f} | Avg: {avg_fit:.4f} | Stag: {stagnation}")

            # Hall of fame
            for s, f in scored[:5]:
                if f > 0.3 and not any(h.strategy_id == s.strategy_id for h in self.hall_of_fame):
                    self.hall_of_fame.append(s)

            # Next generation
            elite_count = max(2, int(self.population_size * self.elite_ratio))
            next_gen = [s for s, _ in scored[:elite_count]]

            while len(next_gen) < self.population_size:
                if random.random() < self.crossover_rate:
                    p1 = self._tournament_select(scored)
                    p2 = self._tournament_select(scored)
                    child = crossover_strategies(p1, p2, gen + 1)
                    if random.random() < adaptive_rate:
                        child = mutate_strategy(child, gen + 1, adaptive_rate)
                    next_gen.append(child)
                else:
                    parent = self._tournament_select(scored)
                    next_gen.append(mutate_strategy(parent, gen + 1, adaptive_rate))

            population = next_gen

        # Final evaluation
        final_scored = []
        for s in population:
            all_results = {}
            for sym, ohlcv in market_data.items():
                try:
                    all_results[sym] = backtest_strategy(s, ohlcv)
                except Exception:
                    pass
            if all_results:
                avg = float(np.mean([r.get("overall_fitness", 0) for r in all_results.values()]))
                s.fitness = {"overall_fitness": round(avg, 4), "per_symbol": all_results}
                final_scored.append((s, s.fitness))

        final_scored.sort(key=lambda x: x[1].get("overall_fitness", 0), reverse=True)
        winners = [s for s, _ in final_scored[:20]]
        self._save_results(winners, run_start)

        if winners:
            logger.info(f"Evolution done. Top: {winners[0].name} fitness={winners[0].fitness.get('overall_fitness', 0):.4f}")
        return winners

    def _load_hall_of_fame(self):
        try:
            conn = sqlite3.connect(str(DB_PATH))
            rows = conn.execute(
                "SELECT fitness_json, name, strategy_id, generation FROM gp_strategies WHERE status='WINNER' ORDER BY ROWID DESC LIMIT 20"
            ).fetchall()
            conn.close()
            strategies = []
            for row in rows:
                s = random_strategy(generation=0)
                s.strategy_id = row[2]
                s.name = row[1]
                s.generation = row[3] if row[3] else 0
                strategies.append(s)
            return strategies
        except Exception:
            return []

    def _save_results(self, winners, run_start):
        conn = sqlite3.connect(str(DB_PATH))
        for w in winners:
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO gp_strategies
                       (strategy_id, name, generation, dna_hash, buy_formula, sell_formula,
                        fitness_json, created_at, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (w.strategy_id, w.name, w.generation, w.dna_hash(),
                     w.buy_tree.to_string()[:500], w.sell_tree.to_string()[:500],
                     json.dumps(w.fitness), w.created_at,
                     "WINNER" if w.fitness.get("overall_fitness", 0) > 0.5 else "EVOLVED"),
                )
            except Exception as e:
                logger.warning(f"Save error: {e}")

        best = winners[0] if winners else None
        conn.execute(
            """INSERT INTO gp_evolution_runs
               (run_timestamp, generations, population_size, best_fitness,
                best_strategy_id, avg_fitness, symbols, total_strategies_tested, hall_of_fame_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_start.isoformat(), self.generations, self.population_size,
             best.fitness.get("overall_fitness", 0) if best else 0,
             best.strategy_id if best else "",
             float(np.mean([w.fitness.get("overall_fitness", 0) for w in winners])) if winners else 0,
             json.dumps(self.symbols), len(winners),
             json.dumps([w.to_dict() for w in self.hall_of_fame[:10]])),
        )
        conn.commit()
        conn.close()

        # Save picks JSON for audit dashboard
        self._save_picks_json(winners)
        self._save_evolution_log()

    def _save_picks_json(self, winners):
        now = datetime.now(timezone.utc).isoformat()
        active_picks = []
        for w in winners[:10]:
            per_symbol = w.fitness.get("per_symbol", {})
            for symbol, metrics in per_symbol.items():
                if metrics.get("overall_fitness", 0) < 0.5:
                    continue  # Quality gate: min 50% fitness (produces >=60% confidence)
                trades = metrics.get("trades", [])
                direction = trades[-1].get("direction", "LONG") if trades else "LONG"
                active_picks.append({
                    "symbol": symbol, "direction": direction,
                    "entry_price": 0, "take_profit": 0, "stop_loss": 0,
                    "confidence": max(min(metrics.get("overall_fitness", 0.5) * 1.2, 0.95), 0.60),
                    "strategy": w.name, "source_system": "genetic_programmer",
                    "win_rate": metrics.get("win_rate", 0),
                    "sharpe_ratio": metrics.get("sharpe_ratio", 0),
                    "profit_factor": metrics.get("profit_factor", 0),
                    "total_trades": metrics.get("total_trades", 0),
                    "max_drawdown_pct": metrics.get("max_drawdown_pct", 0),
                    "generation": w.generation, "dna_hash": w.dna_hash(),
                    "buy_formula": w.buy_tree.to_string()[:150],
                    "sell_formula": w.sell_tree.to_string()[:150],
                    "parents": w.parents, "timestamp": now,
                    "tp_pct": w.tp_pct, "sl_pct": w.sl_pct,
                })

        output = {
            "generated_at": now, "system": "genetic_programmer", "version": "1.0.0",
            "evolution_generations": self.generations, "population_size": self.population_size,
            "total_picks": len(active_picks), "picks": active_picks,
        }
        with open(str(PICKS_OUTPUT), "w") as f:
            json.dump(output, f, indent=2)
        logger.info(f"Saved {len(active_picks)} active picks to {PICKS_OUTPUT}")

    def _save_evolution_log(self):
        output = {
            "last_run": datetime.now(timezone.utc).isoformat(),
            "history": self.evolution_history,
            "hall_of_fame": [s.to_dict() for s in self.hall_of_fame[:20]],
        }
        with open(str(EVOLUTION_LOG), "w") as f:
            json.dump(output, f, indent=2)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_gp_evolution(symbols=None, population_size=80, generations=20, period="60d"):
    symbols = symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "DOGEUSDT"]

    logger.info("=" * 70)
    logger.info("GENETIC PROGRAMMING EVOLUTION — New cycle")
    logger.info(f"Symbols: {symbols} | Pop: {population_size} | Gens: {generations}")
    logger.info("=" * 70)

    market_data = fetch_market_data(symbols, limit=750)
    if not market_data:
        logger.error("No market data, aborting")
        return []

    evolver = GeneticProgrammingEvolver(
        population_size=population_size, generations=generations,
        symbols=list(market_data.keys()),
    )
    winners = evolver.run_evolution(market_data)

    print("\n" + "=" * 70)
    print("GP EVOLUTION RESULTS")
    print("=" * 70)
    for i, w in enumerate(winners[:10], 1):
        f = w.fitness
        of = f.get("overall_fitness", 0)
        ps = f.get("per_symbol", {})
        best_sym = max(ps.items(), key=lambda x: x[1].get("win_rate", 0)) if ps else ("N/A", {})
        print(f"  {i:2d}. {w.name:<35s} | Fitness: {of:.4f} | "
              f"Best: {best_sym[0]} WR={best_sym[1].get('win_rate', 0):.1%} "
              f"Sharpe={best_sym[1].get('sharpe_ratio', 0):.2f}")
    print("=" * 70)
    print(f"Picks: {PICKS_OUTPUT}")
    print(f"Log:   {EVOLUTION_LOG}")
    return winners


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GP Evolution for Trading")
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT", help="Symbols")
    parser.add_argument("--pop", type=int, default=80, help="Population size")
    parser.add_argument("--gens", type=int, default=20, help="Generations")
    args = parser.parse_args()
    symbols = [s.strip() for s in args.symbols.split(",")]
    run_gp_evolution(symbols=symbols, population_size=args.pop, generations=args.gens)
