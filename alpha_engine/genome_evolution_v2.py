"""
Genome Evolution Engine v2 -- Anti-Overfit Genetic Algorithm
============================================================
Successor to genome_evolution.py after v1's G51883 (98.6% WR) collapsed
96% out-of-sample. The tight-TP scalper (0.5x ATR TP / 2.1x ATR SL) won
many small trades but net profit was near zero after slippage.

v2 Anti-Overfit Techniques:
  1. Walk-Forward Anchored Fitness (5-fold sequential)
  2. Noise Injection (0.1% OHLCV perturbation, 3 seeds, worst score)
  3. Parameter Regularization (L2 penalty from defaults)
  4. Island Model (4 islands x 15 genomes, ring migration every 10 gen)
  5. Minimum Trade Count (30 total across all folds)
  6. Multi-Objective Fitness (Sharpe + robustness + PF + confidence - penalties)
  7. Inverse Strategy Detection (flip worst genomes if p < 0.05)
  8. Ensemble Output (top genome per island, correlation < 0.7)

Usage:
    py genome_evolution_v2.py
"""

import json
import ssl
import time
import random
import urllib.request
import math
import copy
import logging
import os
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

# --- Logging -------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("genome_v2")

# --- Configuration -------------------------------------------------------
NUM_ISLANDS = 4
ISLAND_SIZE = 15
POPULATION_SIZE = NUM_ISLANDS * ISLAND_SIZE  # 60 total
NUM_GENERATIONS = 100
ELITE_PCT = 0.13          # Top 2 per island survive unchanged
MUTATION_RATE = 0.25
CROSSOVER_RATE = 0.70
TOURNAMENT_SIZE = 4
MIGRATION_INTERVAL = 10   # Migrate every N generations
MIGRATION_COUNT = 2       # Top N genomes migrate between islands
NOISE_PCT = 0.001         # 0.1% price noise
NOISE_EVALS = 3           # Evaluate each genome 3 times with different noise
WALK_FORWARD_FOLDS = 5    # 5-fold sequential walk-forward
MIN_TOTAL_TRADES = 30     # Minimum trades across ALL folds
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT"]
CANDLE_LIMIT = 1000       # 1000 x 1h = ~42 days (more data for walk-forward)
SLIPPAGE_PCT = 0.05       # 0.05% slippage per trade (round-trip = 0.1%)
ENSEMBLE_MAX_CORR = 0.7   # Max signal correlation for ensemble diversity

# --- Gene Definitions (same 14 parameters as v1) ------------------------
GENE_RANGES = {
    "ema_period":         (10, 60, "int"),
    "atr_period":         (8, 40, "int"),
    "channel_mult":       (1.0, 3.5, "float"),
    "comp_window":        (30, 150, "int"),
    "tp_atr_mult":        (0.5, 4.0, "float"),
    "sl_atr_mult":        (0.3, 2.5, "float"),
    "max_hold":           (4, 24, "int"),
    "hma_period":         (10, 50, "int"),
    "min_edge":           (0.0, 0.5, "float"),
    "vol_gate_high":      (1.5, 3.0, "float"),
    "vol_gate_extreme":   (2.5, 5.0, "float"),
    "trend_strength_min": (0.0, 0.01, "float"),
    "reentry_cooldown":   (0, 6, "int"),
    "volume_confirm":     (0.5, 3.0, "float"),
}

# Default (base) genome -- used for regularization penalty
DEFAULT_GENOME = {
    "ema_period": 30,
    "atr_period": 20,
    "channel_mult": 1.8,
    "comp_window": 80,
    "tp_atr_mult": 2.3,
    "sl_atr_mult": 1.3,
    "max_hold": 12,
    "hma_period": 21,
    "min_edge": 0.0,
    "vol_gate_high": 2.0,
    "vol_gate_extreme": 3.0,
    "trend_strength_min": 0.0,
    "reentry_cooldown": 0,
    "volume_confirm": 0.0,
}


# --- Data Classes --------------------------------------------------------
@dataclass
class TradeResult:
    direction: str
    entry_price: float
    exit_price: float
    pnl_pct: float
    bars_held: int
    bar_index: int  # When the trade was entered (for signal correlation)


@dataclass
class FoldResult:
    """Results from one walk-forward fold."""
    trades: List[TradeResult]
    sharpe: float
    pf: float
    wr: float
    total_pnl: float
    trade_count: int
    is_oos: bool  # True if this is out-of-sample


@dataclass
class Genome:
    genes: Dict
    fitness: float = 0.0
    details: Dict = field(default_factory=dict)
    generation: int = 0
    genome_id: str = ""
    island: int = 0
    # Cached signal indices for correlation check
    signal_bars: List[int] = field(default_factory=list)

    def __post_init__(self):
        if not self.genome_id:
            self.genome_id = f"V2-{random.randint(10000, 99999)}"


# --- Market Data ---------------------------------------------------------
_market_data_cache: Dict[str, list] = {}


_BINANCE_KLINE_BASES = [
    "https://api.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]


def fetch_candles(symbol: str, interval: str = "1h", limit: int = 1000) -> list:
    """Fetch OHLCV candles from Binance with endpoint failover."""
    cache_key = f"{symbol}_{interval}_{limit}"
    if cache_key in _market_data_cache:
        return _market_data_cache[cache_key]

    ctx = ssl.create_default_context()

    for base in _BINANCE_KLINE_BASES:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            resp = urllib.request.urlopen(req, timeout=15, context=ctx)
            data = json.loads(resp.read())
            candles = []
            for k in data:
                candles.append({
                    "ts": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                })
            _market_data_cache[cache_key] = candles
            log.info(f"Fetched {symbol}: {len(candles)} candles from {base}")
            return candles
        except urllib.error.HTTPError as e:
            if e.code in (451, 403):
                continue  # geo-blocked, try next
            time.sleep(1)
        except Exception:
            time.sleep(1)
            continue

    log.warning(f"Failed to fetch {symbol} from all Binance endpoints")
    return []


# --- Noise Injection -----------------------------------------------------
def inject_noise(candles: list, noise_pct: float, seed: int) -> list:
    """Add random noise to OHLCV prices. Volume is left unchanged.
    Each candle's O/H/L/C is multiplied by (1 + uniform(-noise_pct, +noise_pct)).
    Uses a deterministic seed for reproducibility.
    """
    rng = random.Random(seed)
    noisy = []
    for c in candles:
        factor_o = 1.0 + rng.uniform(-noise_pct, noise_pct)
        factor_h = 1.0 + rng.uniform(-noise_pct, noise_pct)
        factor_l = 1.0 + rng.uniform(-noise_pct, noise_pct)
        factor_c = 1.0 + rng.uniform(-noise_pct, noise_pct)
        o = c["open"] * factor_o
        h = c["high"] * factor_h
        l = c["low"] * factor_l
        cl = c["close"] * factor_c
        # Maintain H >= max(O,C) and L <= min(O,C) invariant
        real_h = max(o, h, cl)
        real_l = min(o, l, cl)
        noisy.append({
            "ts": c["ts"],
            "open": o,
            "high": real_h,
            "low": real_l,
            "close": cl,
            "volume": c["volume"],
        })
    return noisy


# --- Walk-Forward Data Splitting -----------------------------------------
def create_walk_forward_folds(candles: list, n_folds: int = 5) -> List[Tuple[list, list]]:
    """Create sequential walk-forward folds with anchored (expanding) training window.

    For n_folds=5 with 1000 candles:
      Fold 0: train=[0:400],   test=[400:520]
      Fold 1: train=[0:520],   test=[520:640]
      Fold 2: train=[0:640],   test=[640:760]
      Fold 3: train=[0:760],   test=[760:880]
      Fold 4: train=[0:880],   test=[880:1000]

    The training window is anchored at the start and grows. This prevents
    look-ahead bias and tests temporal robustness.
    """
    n = len(candles)
    # Reserve 60% for the initial training window, split remaining into folds
    initial_train_pct = 0.40
    initial_train_end = int(n * initial_train_pct)
    remaining = n - initial_train_end
    fold_size = remaining // n_folds

    if fold_size < 80:
        log.warning(f"Fold size too small ({fold_size}), reducing to 3 folds")
        n_folds = 3
        fold_size = remaining // n_folds

    folds = []
    for i in range(n_folds):
        test_start = initial_train_end + i * fold_size
        test_end = test_start + fold_size
        if i == n_folds - 1:
            test_end = n  # Last fold gets remaining data
        train_data = candles[:test_start]
        test_data = candles[test_start:test_end]
        folds.append((train_data, test_data))

    return folds


# --- Technical Indicators (pure Python, same as v1) ---------------------
def calc_ema(values: list, period: int) -> list:
    result = [0.0] * len(values)
    mult = 2.0 / (period + 1)
    result[0] = values[0]
    for i in range(1, len(values)):
        result[i] = values[i] * mult + result[i - 1] * (1 - mult)
    return result


def calc_atr(highs: list, lows: list, closes: list, period: int) -> list:
    n = len(closes)
    trs = [0.0] * n
    trs[0] = highs[0] - lows[0]
    for i in range(1, n):
        trs[i] = max(highs[i] - lows[i],
                      abs(highs[i] - closes[i - 1]),
                      abs(lows[i] - closes[i - 1]))
    result = [0.0] * n
    for i in range(n):
        start = max(0, i - period + 1)
        result[i] = sum(trs[start:i + 1]) / (i - start + 1)
    return result


def calc_hma(values: list, period: int) -> list:
    half = max(1, period // 2)
    sqrt_n = max(1, int(period ** 0.5))
    wma_half = calc_ema(values, half)
    wma_full = calc_ema(values, period)
    raw = [2 * wma_half[i] - wma_full[i] for i in range(len(values))]
    return calc_ema(raw, sqrt_n)


def calc_sma(values: list, period: int) -> list:
    result = [0.0] * len(values)
    for i in range(len(values)):
        start = max(0, i - period + 1)
        result[i] = sum(values[start:i + 1]) / (i - start + 1)
    return result


def calc_volume_sma(volumes: list, period: int = 20) -> list:
    return calc_sma(volumes, period)


# --- Backtest Engine (enhanced with slippage and bar tracking) -----------
def backtest_genome(candles: list, genes: Dict) -> List[TradeResult]:
    """Run the Keltner Compression Expansion strategy with given genome parameters.
    Enhanced from v1: includes slippage and tracks bar indices for correlation.
    """
    if len(candles) < 160:
        return []

    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    volumes = [c["volume"] for c in candles]

    ema_period = genes["ema_period"]
    atr_period = genes["atr_period"]
    channel_mult = genes["channel_mult"]
    comp_window = genes["comp_window"]
    tp_atr_mult = genes["tp_atr_mult"]
    sl_atr_mult = genes["sl_atr_mult"]
    max_hold = genes["max_hold"]
    hma_period = genes["hma_period"]
    min_edge = genes["min_edge"]
    vol_gate_high = genes["vol_gate_high"]
    vol_gate_extreme = genes["vol_gate_extreme"]
    trend_min = genes["trend_strength_min"]
    cooldown = genes["reentry_cooldown"]
    vol_confirm = genes["volume_confirm"]

    ema_vals = calc_ema(closes, ema_period)
    atr_vals = calc_atr(highs, lows, closes, atr_period)
    hma_vals = calc_hma(closes, hma_period)
    vol_sma = calc_volume_sma(volumes, 20)
    atr_sma = calc_sma(atr_vals, 30)

    # Precompute channel widths
    widths = [channel_mult * atr_vals[i] / (ema_vals[i] + 1e-12) for i in range(len(closes))]

    trades = []
    min_bars = max(160, comp_window + 5)
    last_signal_bar = -999

    for i in range(min_bars, len(candles) - max_hold - 1):
        if i - last_signal_bar < cooldown:
            continue

        a = atr_vals[i]
        if a < 1e-12:
            continue

        atr_mean = atr_sma[i]
        atr_ratio = a / atr_mean if atr_mean > 0 else 1.0

        if atr_ratio > vol_gate_extreme:
            continue

        position_scale = 0.5 if atr_ratio > vol_gate_high else 1.0

        # Compression check
        window_start = max(0, i - comp_window)
        window_widths = widths[window_start:i]
        if len(window_widths) < 10:
            continue
        sorted_w = sorted(window_widths)
        q25 = sorted_w[len(sorted_w) // 4]
        compressed = widths[i - 1] < q25

        if not compressed:
            continue

        upper = ema_vals[i] + channel_mult * a
        lower = ema_vals[i] - channel_mult * a
        px = closes[i]

        hma_slope = (hma_vals[i] - hma_vals[i - 1]) / (closes[i] + 1e-12)
        hma_rising = hma_slope > trend_min
        hma_falling = hma_slope < -trend_min

        if vol_confirm > 0 and vol_sma[i] > 0:
            vol_ratio = volumes[i] / vol_sma[i]
            if vol_ratio < vol_confirm:
                continue

        edge_buy = max(0.0, (px - upper) / (a + 1e-12))
        edge_sell = max(0.0, (lower - px) / (a + 1e-12))

        direction = None
        if px > upper and hma_rising and edge_buy >= min_edge:
            direction = "LONG"
        elif px < lower and hma_falling and edge_sell >= min_edge:
            direction = "SHORT"

        if direction is None:
            continue

        # Apply slippage to entry
        slippage = px * SLIPPAGE_PCT / 100
        if direction == "LONG":
            entry_px = px + slippage  # Worse fill for longs
        else:
            entry_px = px - slippage  # Worse fill for shorts

        tp_dist = tp_atr_mult * a
        sl_dist = sl_atr_mult * a

        if direction == "LONG":
            tp_price = entry_px + tp_dist
            sl_price = entry_px - sl_dist
        else:
            tp_price = entry_px - tp_dist
            sl_price = entry_px + sl_dist

        pnl = None
        exit_px = None
        bars_held = 0
        for j in range(i + 1, min(i + 1 + max_hold, len(candles))):
            bars_held = j - i
            if direction == "LONG":
                if candles[j]["high"] >= tp_price:
                    exit_px = tp_price - slippage  # Slippage on exit
                    pnl = (exit_px - entry_px) / entry_px * 100
                    break
                if candles[j]["low"] <= sl_price:
                    exit_px = sl_price - slippage
                    pnl = (exit_px - entry_px) / entry_px * 100
                    break
            else:
                if candles[j]["low"] <= tp_price:
                    exit_px = tp_price + slippage
                    pnl = (entry_px - exit_px) / entry_px * 100
                    break
                if candles[j]["high"] >= sl_price:
                    exit_px = sl_price + slippage
                    pnl = (entry_px - exit_px) / entry_px * 100
                    break

        if pnl is None:
            exit_bar = min(i + max_hold, len(candles) - 1)
            exit_px = candles[exit_bar]["close"]
            # Apply exit slippage
            if direction == "LONG":
                exit_px -= slippage
                pnl = (exit_px - entry_px) / entry_px * 100
            else:
                exit_px += slippage
                pnl = (entry_px - exit_px) / entry_px * 100
            bars_held = exit_bar - i

        pnl *= position_scale
        trades.append(TradeResult(direction, entry_px, exit_px, pnl, bars_held, i))
        last_signal_bar = i

    return trades


# --- Sharpe Ratio Calculation --------------------------------------------
def calc_sharpe(pnl_series: list, annualize_factor: float = math.sqrt(252 * 24)) -> float:
    """Calculate Sharpe ratio from a list of per-trade P&L percentages.
    Annualized assuming hourly bars (~8760 per year, but using trading hours).
    """
    if len(pnl_series) < 2:
        return 0.0
    mean = sum(pnl_series) / len(pnl_series)
    variance = sum((x - mean) ** 2 for x in pnl_series) / (len(pnl_series) - 1)
    std = math.sqrt(variance) if variance > 0 else 1e-12
    # Simple Sharpe (not annualized to avoid inflating short samples)
    return mean / std


# --- Parameter Regularization --------------------------------------------
def calc_regularization_penalty(genes: Dict) -> float:
    """L2-style penalty for parameters far from defaults.
    Returns a value in [0, 1+] where 0 = at defaults, higher = more extreme.

    Each gene's deviation is normalized by its range, then squared and summed.
    This catches the v1 failure mode where tp_atr_mult=0.5 (default 2.3) and
    sl_atr_mult=2.1 (default 1.3) created an extreme asymmetric scalper.
    """
    penalty = 0.0
    n_genes = 0
    for name, (lo, hi, dtype) in GENE_RANGES.items():
        default_val = DEFAULT_GENOME.get(name, (lo + hi) / 2)
        gene_range = hi - lo
        if gene_range < 1e-12:
            continue
        # Normalized distance from default (0 to 1 scale)
        dist = abs(genes[name] - default_val) / gene_range
        penalty += dist ** 2
        n_genes += 1

    # Normalize so average genome gets ~0.3 penalty
    if n_genes > 0:
        penalty = penalty / n_genes
    return penalty


# --- Walk-Forward Fitness Evaluation -------------------------------------
def evaluate_fold(candles: list, genes: Dict) -> FoldResult:
    """Run backtest on a fold and compute metrics."""
    trades = backtest_genome(candles, genes)
    n = len(trades)
    if n == 0:
        return FoldResult(trades=[], sharpe=0.0, pf=0.0, wr=0.0,
                          total_pnl=0.0, trade_count=0, is_oos=False)

    pnl_list = [t.pnl_pct for t in trades]
    wins = sum(1 for p in pnl_list if p > 0)
    wr = wins / n if n > 0 else 0.0
    total_pnl = sum(pnl_list)
    gross_wins = sum(p for p in pnl_list if p > 0)
    gross_losses = abs(sum(p for p in pnl_list if p <= 0))
    pf = gross_wins / gross_losses if gross_losses > 0 else (10.0 if gross_wins > 0 else 0.0)
    sharpe = calc_sharpe(pnl_list)

    return FoldResult(
        trades=trades, sharpe=sharpe, pf=min(pf, 10.0), wr=wr,
        total_pnl=total_pnl, trade_count=n, is_oos=False,
    )


def walk_forward_evaluate(folds: List[Tuple[list, list]], genes: Dict) -> Dict:
    """Run walk-forward evaluation across all folds.

    Returns dict with:
      - oos_sharpes: list of OOS Sharpe per fold
      - is_sharpes: list of IS Sharpe per fold
      - mean_oos_sharpe: average OOS Sharpe
      - oos_variance: variance of OOS Sharpe across folds
      - total_oos_trades: total trades in OOS segments
      - mean_oos_pf: average OOS profit factor
      - overfit_penalty: abs(1 - OOS_pnl / IS_pnl)
      - all_oos_trades: flat list of all OOS trade results
    """
    oos_sharpes = []
    is_sharpes = []
    oos_pfs = []
    total_oos_trades = 0
    total_is_pnl = 0.0
    total_oos_pnl = 0.0
    all_oos_trades = []

    for train_data, test_data in folds:
        is_result = evaluate_fold(train_data, genes)
        oos_result = evaluate_fold(test_data, genes)

        is_sharpes.append(is_result.sharpe)
        oos_sharpes.append(oos_result.sharpe)
        oos_pfs.append(oos_result.pf)
        total_oos_trades += oos_result.trade_count
        total_is_pnl += is_result.total_pnl
        total_oos_pnl += oos_result.total_pnl
        all_oos_trades.extend(oos_result.trades)

    # Mean and variance of OOS Sharpe
    mean_oos_sharpe = sum(oos_sharpes) / len(oos_sharpes) if oos_sharpes else 0.0
    if len(oos_sharpes) > 1:
        oos_variance = sum((s - mean_oos_sharpe) ** 2 for s in oos_sharpes) / (len(oos_sharpes) - 1)
    else:
        oos_variance = 0.0

    mean_oos_pf = sum(oos_pfs) / len(oos_pfs) if oos_pfs else 0.0

    # Overfit penalty: how much IS and OOS diverge
    if abs(total_is_pnl) > 0.01:
        overfit_ratio = total_oos_pnl / total_is_pnl
        overfit_penalty = abs(1.0 - overfit_ratio)
    else:
        overfit_penalty = 1.0 if total_oos_pnl <= 0 else 0.0

    return {
        "oos_sharpes": oos_sharpes,
        "is_sharpes": is_sharpes,
        "mean_oos_sharpe": mean_oos_sharpe,
        "oos_variance": oos_variance,
        "total_oos_trades": total_oos_trades,
        "mean_oos_pf": mean_oos_pf,
        "total_is_pnl": total_is_pnl,
        "total_oos_pnl": total_oos_pnl,
        "overfit_penalty": overfit_penalty,
        "all_oos_trades": all_oos_trades,
    }


# --- Noise Robustness Evaluation ----------------------------------------
def noise_robustness_score(all_candles: Dict[str, list], genes: Dict,
                           n_evals: int = NOISE_EVALS) -> float:
    """Evaluate genome on noisy data multiple times, return WORST Sharpe.
    A robust genome should perform similarly with and without noise.
    """
    worst_sharpe = float("inf")
    base_seed = hash(str(genes)) & 0xFFFFFFFF

    for eval_idx in range(n_evals):
        seed = base_seed + eval_idx * 12345
        total_pnl_list = []

        for symbol, candles in all_candles.items():
            if not candles:
                continue
            noisy_candles = inject_noise(candles, NOISE_PCT, seed + hash(symbol))
            trades = backtest_genome(noisy_candles, genes)
            total_pnl_list.extend([t.pnl_pct for t in trades])

        if len(total_pnl_list) < 5:
            return -1.0

        sharpe = calc_sharpe(total_pnl_list)
        worst_sharpe = min(worst_sharpe, sharpe)

    return worst_sharpe if worst_sharpe != float("inf") else 0.0


# --- Multi-Objective Fitness Function ------------------------------------
def calculate_fitness_v2(genome: Genome, all_candles: Dict[str, list],
                         all_folds: Dict[str, List[Tuple[list, list]]]) -> float:
    """
    Multi-Objective Fitness:
      fitness = 0.4 * walk_forward_sharpe
             + 0.3 * noise_robustness
             + 0.2 * profit_factor
             + 0.1 * trade_count_confidence
             - 0.2 * regularization_penalty
             - 0.3 * overfit_penalty

    A genome that works in 1 fold but fails in 4 is killed via variance penalty.
    """
    genes = genome.genes

    # -- Step 1: Walk-Forward across all symbols --
    combined_oos_sharpes = []
    combined_oos_pfs = []
    total_oos_trades = 0
    total_is_pnl = 0.0
    total_oos_pnl = 0.0
    all_oos_trades = []
    symbols_profitable = 0
    per_symbol_details = {}

    for symbol in SYMBOLS:
        if symbol not in all_folds or not all_folds[symbol]:
            continue

        wf = walk_forward_evaluate(all_folds[symbol], genes)
        combined_oos_sharpes.extend(wf["oos_sharpes"])
        combined_oos_pfs.append(wf["mean_oos_pf"])
        total_oos_trades += wf["total_oos_trades"]
        total_is_pnl += wf["total_is_pnl"]
        total_oos_pnl += wf["total_oos_pnl"]
        all_oos_trades.extend(wf["all_oos_trades"])

        if wf["total_oos_pnl"] > 0:
            symbols_profitable += 1

        per_symbol_details[symbol] = {
            "oos_trades": wf["total_oos_trades"],
            "oos_pnl": round(wf["total_oos_pnl"], 2),
            "mean_oos_sharpe": round(wf["mean_oos_sharpe"], 4),
            "mean_oos_pf": round(wf["mean_oos_pf"], 2),
        }

    # -- Minimum trade count gate (Technique 5) --
    if total_oos_trades < MIN_TOTAL_TRADES:
        genome.fitness = 0.0
        genome.details = {
            "reason": "insufficient_trades",
            "total_oos_trades": total_oos_trades,
            "min_required": MIN_TOTAL_TRADES,
        }
        return 0.0

    # -- Walk-Forward Sharpe (Technique 1) --
    if combined_oos_sharpes:
        mean_wf_sharpe = sum(combined_oos_sharpes) / len(combined_oos_sharpes)
        if len(combined_oos_sharpes) > 1:
            wf_variance = sum((s - mean_wf_sharpe) ** 2 for s in combined_oos_sharpes) / (len(combined_oos_sharpes) - 1)
        else:
            wf_variance = 0.0
        # Penalize high variance across folds -- a genome that works in 1/5 folds is bad
        wf_sharpe_score = max(0.0, mean_wf_sharpe - 0.5 * math.sqrt(wf_variance))
    else:
        wf_sharpe_score = 0.0
        wf_variance = 0.0

    # -- Noise Robustness (Technique 2) --
    noise_score = noise_robustness_score(all_candles, genes)

    # -- Profit Factor --
    mean_pf = sum(combined_oos_pfs) / len(combined_oos_pfs) if combined_oos_pfs else 0.0
    pf_score = min(mean_pf, 5.0)  # Cap at 5 to avoid extreme PF dominating

    # -- Trade Count Confidence --
    # Sigmoid-like: approaches 1.0 at ~100 trades, low at <30
    trade_conf = 1.0 - math.exp(-total_oos_trades / 50.0)

    # -- Regularization Penalty (Technique 3) --
    reg_penalty = calc_regularization_penalty(genes)

    # -- Overfit Penalty (Technique 6) --
    if abs(total_is_pnl) > 0.01:
        overfit_ratio = total_oos_pnl / total_is_pnl
        overfit_penalty = abs(1.0 - overfit_ratio)
        # Extra penalty if OOS is wildly better (suspicious) or much worse
        overfit_penalty = min(overfit_penalty, 3.0)  # Cap so it doesn't dominate
    else:
        overfit_penalty = 1.0 if total_oos_pnl <= 0 else 0.5

    # -- Win rate and PnL sanity --
    oos_pnl_list = [t.pnl_pct for t in all_oos_trades]
    oos_wins = sum(1 for p in oos_pnl_list if p > 0)
    oos_wr = oos_wins / len(oos_pnl_list) if oos_pnl_list else 0.0

    # -- Combined Multi-Objective Fitness (Technique 6) --
    fitness = (
        0.4 * wf_sharpe_score
        + 0.3 * noise_score
        + 0.2 * pf_score
        + 0.1 * trade_conf
        - 0.2 * reg_penalty
        - 0.3 * overfit_penalty
    )

    # Store signal bar indices for later correlation check
    genome.signal_bars = [t.bar_index for t in all_oos_trades]

    genome.fitness = round(fitness, 6)
    genome.details = {
        "total_oos_trades": total_oos_trades,
        "oos_wr": round(oos_wr * 100, 1),
        "oos_pnl": round(total_oos_pnl, 2),
        "is_pnl": round(total_is_pnl, 2),
        "wf_sharpe": round(wf_sharpe_score, 4),
        "wf_variance": round(wf_variance, 4),
        "noise_score": round(noise_score, 4),
        "pf_score": round(pf_score, 4),
        "trade_confidence": round(trade_conf, 4),
        "reg_penalty": round(reg_penalty, 4),
        "overfit_penalty": round(overfit_penalty, 4),
        "symbols_profitable": symbols_profitable,
        "per_symbol": per_symbol_details,
    }
    return fitness


# --- Genetic Operators ---------------------------------------------------
def random_genome(generation: int = 0, island: int = 0) -> Genome:
    genes = {}
    for name, (lo, hi, dtype) in GENE_RANGES.items():
        if dtype == "int":
            genes[name] = random.randint(int(lo), int(hi))
        else:
            genes[name] = round(random.uniform(lo, hi), 4)
    return Genome(genes=genes, generation=generation, island=island)


def mutate(genome: Genome, generation: int, rate: float = MUTATION_RATE) -> Genome:
    """Mutate genes with decreasing magnitude over generations."""
    new_genes = copy.deepcopy(genome.genes)
    decay = max(0.3, 1.0 - generation / (NUM_GENERATIONS * 1.5))

    for name, (lo, hi, dtype) in GENE_RANGES.items():
        if random.random() < rate:
            span = hi - lo
            delta = random.gauss(0, span * 0.15 * decay)
            if dtype == "int":
                new_genes[name] = max(int(lo), min(int(hi), int(new_genes[name] + delta)))
            else:
                new_genes[name] = max(lo, min(hi, round(new_genes[name] + delta, 4)))

    child = Genome(genes=new_genes, generation=generation, island=genome.island)
    return child


def crossover(parent1: Genome, parent2: Genome, generation: int) -> Genome:
    """Uniform crossover with occasional gene averaging."""
    child_genes = {}
    for name in GENE_RANGES:
        r = random.random()
        if r < 0.45:
            child_genes[name] = parent1.genes[name]
        elif r < 0.90:
            child_genes[name] = parent2.genes[name]
        else:
            val = (parent1.genes[name] + parent2.genes[name]) / 2
            _, _, dtype = GENE_RANGES[name]
            if dtype == "int":
                child_genes[name] = int(round(val))
            else:
                child_genes[name] = round(val, 4)

    return Genome(genes=child_genes, generation=generation, island=parent1.island)


def tournament_select(population: List[Genome], k: int = TOURNAMENT_SIZE) -> Genome:
    contestants = random.sample(population, min(k, len(population)))
    return max(contestants, key=lambda g: g.fitness)


# --- Island Model (Technique 4) -----------------------------------------
def migrate_islands(islands: List[List[Genome]], generation: int):
    """Ring topology migration: island i sends top MIGRATION_COUNT to island (i+1) % n.
    Migrants replace the worst genomes on the receiving island.
    """
    n_islands = len(islands)
    migrants = []

    # Collect migrants from each island (top performers)
    for i in range(n_islands):
        islands[i].sort(key=lambda g: g.fitness, reverse=True)
        island_migrants = []
        for g in islands[i][:MIGRATION_COUNT]:
            migrant = copy.deepcopy(g)
            island_migrants.append(migrant)
        migrants.append(island_migrants)

    # Send to next island (ring topology)
    for i in range(n_islands):
        target = (i + 1) % n_islands
        for j, migrant in enumerate(migrants[i]):
            migrant.island = target
            migrant.generation = generation
            # Replace worst genomes on target island
            islands[target].sort(key=lambda g: g.fitness)
            if j < len(islands[target]):
                islands[target][j] = migrant

    log.info(f"  Migration complete (gen {generation}): "
             f"{MIGRATION_COUNT} genomes moved between {n_islands} islands (ring)")


# --- Signal Correlation for Ensemble Diversity ---------------------------
def signal_correlation(bars_a: List[int], bars_b: List[int], total_bars: int) -> float:
    """Compute Jaccard similarity between two genomes' signal bar sets.
    Returns value in [0, 1] where 1 = identical signals.
    """
    if not bars_a or not bars_b:
        return 0.0
    set_a = set(bars_a)
    set_b = set(bars_b)
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


# --- Inverse Strategy Detection (Technique 7) ---------------------------
def check_inverse_candidates(population: List[Genome], all_candles: Dict[str, list],
                             all_folds: Dict[str, List[Tuple[list, list]]]) -> List[Genome]:
    """Check worst genomes for statistically significant negative edge.
    If a genome consistently loses more than 2x transaction costs,
    create an inverse variant (swap LONG/SHORT triggers).

    We approximate inversion by swapping tp_atr_mult and sl_atr_mult
    and inverting the trend filter direction (negative trend_strength_min).
    """
    inverse_genomes = []

    # Look at bottom 10% of population
    sorted_pop = sorted(population, key=lambda g: g.fitness)
    bottom = sorted_pop[:max(3, len(sorted_pop) // 10)]

    for genome in bottom:
        # Need enough trades to be statistically significant
        total_trades = genome.details.get("total_oos_trades", 0)
        oos_pnl = genome.details.get("oos_pnl", 0.0)

        if total_trades < 20 or oos_pnl >= 0:
            continue

        # Check if loss is significant: avg loss per trade > 2x slippage cost
        avg_loss = abs(oos_pnl) / total_trades
        if avg_loss < SLIPPAGE_PCT * 4:  # Need to be worse than 4x slippage round-trip
            continue

        # Simple z-test for negative mean
        # H0: mean PnL = 0, H1: mean PnL < 0
        # We approximate using the Sharpe ratio as test statistic
        noise_sharpe = genome.details.get("noise_score", 0.0)
        wf_sharpe = genome.details.get("wf_sharpe", 0.0)
        # If consistently negative Sharpe across noise evaluations
        if wf_sharpe >= 0 or noise_sharpe >= 0:
            continue

        # z-statistic approximation: sharpe * sqrt(n)
        z_stat = abs(wf_sharpe) * math.sqrt(total_trades)
        # p < 0.05 corresponds to z > 1.645 (one-tailed)
        if z_stat < 1.645:
            continue

        log.info(f"  INVERSE CANDIDATE: {genome.genome_id} "
                 f"(trades={total_trades}, pnl={oos_pnl:.2f}%, z={z_stat:.2f})")

        # Create inverse: swap TP direction by inverting the trend filter
        inv_genes = copy.deepcopy(genome.genes)
        # Inversion approach: the strategy normally goes LONG on uptrend breakout
        # and SHORT on downtrend breakout. We invert by making it go LONG when
        # original would SHORT (contrarian). Approximate by negating min_edge
        # to require counter-trend entries, and swapping TP/SL to profit from
        # mean reversion.
        inv_genes["tp_atr_mult"], inv_genes["sl_atr_mult"] = (
            inv_genes["sl_atr_mult"], inv_genes["tp_atr_mult"]
        )
        # Shift channel mult to catch the opposite breakout
        inv_genes["channel_mult"] = max(1.0, min(3.5,
            GENE_RANGES["channel_mult"][1] - inv_genes["channel_mult"] + GENE_RANGES["channel_mult"][0]
        ))

        inv_genome = Genome(
            genes=inv_genes,
            generation=genome.generation,
            island=genome.island,
            genome_id=f"INV-{genome.genome_id}",
        )

        # Evaluate the inverse
        calculate_fitness_v2(inv_genome, all_candles, all_folds)
        if inv_genome.fitness > 0:
            log.info(f"  INVERSE VIABLE: {inv_genome.genome_id} "
                     f"fitness={inv_genome.fitness:.4f}")
            inverse_genomes.append(inv_genome)

    return inverse_genomes


# --- Ensemble Builder (Technique 8) -------------------------------------
def build_ensemble(islands: List[List[Genome]], max_corr: float = ENSEMBLE_MAX_CORR) -> List[Genome]:
    """Take top genome from each island, filter for behavioral diversity.
    Remove genomes whose signal correlation with an already-selected genome > max_corr.
    """
    candidates = []
    for i, island in enumerate(islands):
        island.sort(key=lambda g: g.fitness, reverse=True)
        if island and island[0].fitness > 0:
            candidates.append(island[0])

    if not candidates:
        return []

    # Sort by fitness descending
    candidates.sort(key=lambda g: g.fitness, reverse=True)

    ensemble = [candidates[0]]
    total_bars = max(1000, max(
        max(g.signal_bars) if g.signal_bars else 0 for g in candidates
    ) + 1) if candidates else 1000

    for candidate in candidates[1:]:
        # Check correlation with all already-selected ensemble members
        is_diverse = True
        for member in ensemble:
            corr = signal_correlation(candidate.signal_bars, member.signal_bars, total_bars)
            if corr > max_corr:
                log.info(f"  Ensemble: REJECTED {candidate.genome_id} "
                         f"(corr={corr:.2f} with {member.genome_id})")
                is_diverse = False
                break
        if is_diverse:
            ensemble.append(candidate)
            log.info(f"  Ensemble: ACCEPTED {candidate.genome_id} "
                     f"(fitness={candidate.fitness:.4f})")

    return ensemble


# --- Main Evolution Engine -----------------------------------------------
def evolve():
    log.info("=" * 80)
    log.info("  GENOME EVOLUTION ENGINE v2 -- Anti-Overfit Genetic Algorithm")
    log.info(f"  Islands: {NUM_ISLANDS} x {ISLAND_SIZE} = {POPULATION_SIZE} genomes")
    log.info(f"  Generations: {NUM_GENERATIONS} | Walk-Forward Folds: {WALK_FORWARD_FOLDS}")
    log.info(f"  Noise: {NOISE_PCT*100:.1f}% x {NOISE_EVALS} evals | Slippage: {SLIPPAGE_PCT}%")
    log.info(f"  Min trades: {MIN_TOTAL_TRADES} | Migration every {MIGRATION_INTERVAL} gen")
    log.info(f"  Symbols: {', '.join(SYMBOLS)}")
    log.info("=" * 80)

    # -- Step 1: Fetch market data --
    log.info("[1/5] Fetching market data...")
    all_candles = {}
    for sym in SYMBOLS:
        candles = fetch_candles(sym, "1h", CANDLE_LIMIT)
        all_candles[sym] = candles
        time.sleep(0.3)

    # -- Step 2: Create walk-forward folds --
    log.info("[2/5] Creating walk-forward folds...")
    all_folds: Dict[str, List[Tuple[list, list]]] = {}
    for sym, candles in all_candles.items():
        if candles:
            folds = create_walk_forward_folds(candles, WALK_FORWARD_FOLDS)
            all_folds[sym] = folds
            log.info(f"  {sym}: {len(folds)} folds, "
                     f"train sizes={[len(f[0]) for f in folds]}, "
                     f"test sizes={[len(f[1]) for f in folds]}")

    # -- Step 3: Initialize islands --
    log.info(f"[3/5] Initializing {NUM_ISLANDS} islands of {ISLAND_SIZE} genomes each...")
    islands: List[List[Genome]] = []

    for island_idx in range(NUM_ISLANDS):
        island: List[Genome] = []

        # Seed first island with base genome variants
        if island_idx == 0:
            base = Genome(genes=copy.deepcopy(DEFAULT_GENOME), generation=0,
                          island=0, genome_id="V2-BASE")
            island.append(base)
            for i in range(2):
                variant = mutate(base, 0, rate=0.4)
                variant.genome_id = f"V2-BASE-V{i}"
                variant.island = 0
                island.append(variant)

        # Fill with random genomes
        while len(island) < ISLAND_SIZE:
            island.append(random_genome(0, island_idx))

        islands.append(island)

    # Evaluate initial populations
    log.info("  Evaluating initial populations...")
    for island_idx, island in enumerate(islands):
        for g in island:
            calculate_fitness_v2(g, all_candles, all_folds)
        island.sort(key=lambda g: g.fitness, reverse=True)
        best = island[0]
        log.info(f"  Island {island_idx}: best={best.genome_id} "
                 f"fitness={best.fitness:.4f} "
                 f"trades={best.details.get('total_oos_trades', 0)} "
                 f"wr={best.details.get('oos_wr', 0)}%")

    # Track global best
    all_genomes = [g for island in islands for g in island]
    all_genomes.sort(key=lambda g: g.fitness, reverse=True)
    best_ever = copy.deepcopy(all_genomes[0])
    log.info(f"  Global best: {best_ever.genome_id} fitness={best_ever.fitness:.4f}")

    # -- Step 4: Evolution loop --
    log.info(f"[4/5] Evolving {NUM_GENERATIONS} generations...")
    hall_of_fame: List[Genome] = []
    stagnation_counter = 0
    generation_stats = []

    for gen in range(1, NUM_GENERATIONS + 1):
        gen_start = time.time()
        elite_count = max(2, int(ISLAND_SIZE * ELITE_PCT))

        # Evolve each island independently
        for island_idx in range(NUM_ISLANDS):
            island = islands[island_idx]
            island.sort(key=lambda g: g.fitness, reverse=True)
            new_island = []

            # Elitism
            for g in island[:elite_count]:
                elite = copy.deepcopy(g)
                elite.generation = gen
                new_island.append(elite)

            # Generate children
            while len(new_island) < ISLAND_SIZE:
                if random.random() < CROSSOVER_RATE:
                    p1 = tournament_select(island)
                    p2 = tournament_select(island)
                    child = crossover(p1, p2, gen)
                    if random.random() < 0.5:
                        child = mutate(child, gen, rate=MUTATION_RATE * 0.7)
                else:
                    parent = tournament_select(island)
                    child = mutate(parent, gen)

                child.island = island_idx
                new_island.append(child)

            # Inject fresh blood every 25 generations
            if gen % 25 == 0:
                new_island[-1] = random_genome(gen, island_idx)
                new_island[-2] = random_genome(gen, island_idx)

            # Evaluate new genomes
            for g in new_island:
                if g.fitness == 0.0 or g.generation == gen:
                    calculate_fitness_v2(g, all_candles, all_folds)

            new_island.sort(key=lambda g: g.fitness, reverse=True)
            islands[island_idx] = new_island

        # -- Migration (Technique 4) --
        if gen % MIGRATION_INTERVAL == 0:
            migrate_islands(islands, gen)

        # Track global best across all islands
        gen_all = [g for island in islands for g in island]
        gen_all.sort(key=lambda g: g.fitness, reverse=True)
        gen_best = gen_all[0]

        if gen_best.fitness > best_ever.fitness:
            best_ever = copy.deepcopy(gen_best)
            stagnation_counter = 0
            marker = " *** NEW BEST ***"
        else:
            stagnation_counter += 1
            marker = ""

        # Hall of fame
        if gen_best.fitness > 0 and gen_best.details.get("oos_wr", 0) >= 50:
            if not any(g.genome_id == gen_best.genome_id for g in hall_of_fame):
                hall_of_fame.append(copy.deepcopy(gen_best))

        gen_elapsed = time.time() - gen_start

        # Stats collection
        avg_fitness = sum(g.fitness for g in gen_all) / len(gen_all)
        island_bests = [max(island, key=lambda g: g.fitness).fitness for island in islands]

        gen_stat = {
            "gen": gen,
            "best_fitness": round(gen_best.fitness, 4),
            "avg_fitness": round(avg_fitness, 4),
            "island_bests": [round(f, 4) for f in island_bests],
            "elapsed_s": round(gen_elapsed, 1),
        }
        generation_stats.append(gen_stat)

        # Status logging
        if gen % 5 == 0 or marker:
            d = gen_best.details
            log.info(
                f"  Gen {gen:>3}: best={gen_best.fitness:>8.4f} "
                f"avg={avg_fitness:>7.4f} "
                f"WR={d.get('oos_wr', 0):>5.1f}% "
                f"trades={d.get('total_oos_trades', 0):>3} "
                f"pnl={d.get('oos_pnl', 0):>+7.2f}% "
                f"sharpe={d.get('wf_sharpe', 0):>6.3f} "
                f"noise={d.get('noise_score', 0):>6.3f} "
                f"overfit={d.get('overfit_penalty', 0):>5.3f} "
                f"reg={d.get('reg_penalty', 0):>5.3f} "
                f"islands=[{', '.join(f'{b:.2f}' for b in island_bests)}] "
                f"({gen_elapsed:.1f}s){marker}"
            )

        # Adaptive mutation on stagnation
        if stagnation_counter > 20:
            log.info(f"  Stagnation detected ({stagnation_counter} gen), increasing mutation")
            # Inject random genomes into weakest island
            weakest_island_idx = island_bests.index(min(island_bests))
            for _ in range(3):
                islands[weakest_island_idx][-1] = random_genome(gen, weakest_island_idx)
                calculate_fitness_v2(islands[weakest_island_idx][-1], all_candles, all_folds)
            stagnation_counter = 0

    # -- Step 5: Post-Evolution Analysis --
    log.info("[5/5] Post-evolution analysis...")

    # Inverse strategy detection (Technique 7)
    log.info("  Checking for inverse strategy candidates...")
    all_genomes_final = [g for island in islands for g in island]
    inverse_genomes = check_inverse_candidates(all_genomes_final, all_candles, all_folds)
    if inverse_genomes:
        log.info(f"  Found {len(inverse_genomes)} viable inverse strategies")
        hall_of_fame.extend(inverse_genomes)

    # Build ensemble (Technique 8)
    log.info("  Building diverse ensemble...")
    ensemble = build_ensemble(islands)
    # Also consider inverse genomes for ensemble
    if inverse_genomes:
        for inv in inverse_genomes:
            is_diverse = True
            for member in ensemble:
                corr = signal_correlation(inv.signal_bars, member.signal_bars, 1000)
                if corr > ENSEMBLE_MAX_CORR:
                    is_diverse = False
                    break
            if is_diverse:
                ensemble.append(inv)

    # --- Results ---------------------------------------------------------
    log.info("")
    log.info("=" * 80)
    log.info("  EVOLUTION v2 COMPLETE")
    log.info("=" * 80)

    # Best genome summary
    log.info(f"\n  Best genome: {best_ever.genome_id}")
    log.info(f"  Generation: {best_ever.generation}")
    log.info(f"  Fitness: {best_ever.fitness:.6f}")
    d = best_ever.details
    log.info(f"  OOS Win Rate: {d.get('oos_wr', 0):.1f}%")
    log.info(f"  OOS Trades: {d.get('total_oos_trades', 0)}")
    log.info(f"  OOS P/L: {d.get('oos_pnl', 0):+.2f}%")
    log.info(f"  IS P/L: {d.get('is_pnl', 0):+.2f}%")
    log.info(f"  WF Sharpe: {d.get('wf_sharpe', 0):.4f}")
    log.info(f"  Noise Score: {d.get('noise_score', 0):.4f}")
    log.info(f"  Overfit Penalty: {d.get('overfit_penalty', 0):.4f}")
    log.info(f"  Reg Penalty: {d.get('reg_penalty', 0):.4f}")
    log.info(f"  Symbols Profitable: {d.get('symbols_profitable', 0)}/{len(SYMBOLS)}")

    log.info(f"\n  Genome Parameters:")
    for k, v in best_ever.genes.items():
        base_v = DEFAULT_GENOME.get(k, "N/A")
        diff = ""
        if isinstance(v, (int, float)) and isinstance(base_v, (int, float)):
            if v != base_v:
                diff = f"  (default: {base_v})"
        log.info(f"    {k:<24} = {v}{diff}")

    log.info(f"\n  Per-Symbol OOS Breakdown:")
    for sym, sd in d.get("per_symbol", {}).items():
        log.info(f"    {sym:<12} trades={sd.get('oos_trades', 0):>3} "
                 f"pnl={sd.get('oos_pnl', 0):>+7.2f}% "
                 f"sharpe={sd.get('mean_oos_sharpe', 0):>6.4f} "
                 f"pf={sd.get('mean_oos_pf', 0):>5.2f}")

    # Ensemble summary
    log.info(f"\n  {'-' * 76}")
    log.info(f"  ENSEMBLE -- {len(ensemble)} diverse genomes")
    log.info(f"  {'-' * 76}")
    for i, g in enumerate(ensemble):
        gd = g.details
        log.info(f"  [{i+1}] {g.genome_id:<16} island={g.island} "
                 f"fitness={g.fitness:>8.4f} "
                 f"WR={gd.get('oos_wr', 0):>5.1f}% "
                 f"trades={gd.get('total_oos_trades', 0):>3} "
                 f"pnl={gd.get('oos_pnl', 0):>+7.2f}% "
                 f"sharpe={gd.get('wf_sharpe', 0):>6.3f} "
                 f"overfit={gd.get('overfit_penalty', 0):>5.3f}")

    # Hall of fame
    hall_of_fame.sort(key=lambda g: g.fitness, reverse=True)
    hall_of_fame = hall_of_fame[:20]

    log.info(f"\n  {'-' * 76}")
    log.info(f"  HALL OF FAME -- Top 10")
    log.info(f"  {'-' * 76}")
    for i, g in enumerate(hall_of_fame[:10]):
        gd = g.details
        log.info(f"  {i+1:<3} {g.genome_id:<16} gen={g.generation:<4} "
                 f"fitness={g.fitness:>8.4f} "
                 f"WR={gd.get('oos_wr', 0):>5.1f}% "
                 f"trades={gd.get('total_oos_trades', 0):>3} "
                 f"pnl={gd.get('oos_pnl', 0):>+7.2f}% "
                 f"overfit={gd.get('overfit_penalty', 0):>5.3f}")

    # --- Save Results ----------------------------------------------------
    results = {
        "version": "2.0",
        "config": {
            "num_islands": NUM_ISLANDS,
            "island_size": ISLAND_SIZE,
            "population": POPULATION_SIZE,
            "generations": NUM_GENERATIONS,
            "walk_forward_folds": WALK_FORWARD_FOLDS,
            "noise_pct": NOISE_PCT,
            "noise_evals": NOISE_EVALS,
            "slippage_pct": SLIPPAGE_PCT,
            "min_trades": MIN_TOTAL_TRADES,
            "symbols": SYMBOLS,
            "candle_limit": CANDLE_LIMIT,
            "migration_interval": MIGRATION_INTERVAL,
            "ensemble_max_corr": ENSEMBLE_MAX_CORR,
        },
        "anti_overfit_techniques": [
            "walk_forward_anchored_5fold",
            "noise_injection_0.1pct_worst_of_3",
            "parameter_regularization_L2",
            "island_model_4x15_ring_migration",
            "min_30_trades_gate",
            "multi_objective_fitness",
            "inverse_strategy_detection",
            "ensemble_diversity_corr_0.7",
        ],
        "best_genome": {
            "id": best_ever.genome_id,
            "generation": best_ever.generation,
            "island": best_ever.island,
            "fitness": best_ever.fitness,
            "genes": best_ever.genes,
            "details": best_ever.details,
        },
        "ensemble": [
            {
                "id": g.genome_id,
                "island": g.island,
                "fitness": g.fitness,
                "genes": g.genes,
                "details": g.details,
            }
            for g in ensemble
        ],
        "hall_of_fame": [
            {
                "id": g.genome_id,
                "generation": g.generation,
                "island": g.island,
                "fitness": g.fitness,
                "genes": g.genes,
                "details": g.details,
            }
            for g in hall_of_fame[:20]
        ],
        "inverse_strategies": [
            {
                "id": g.genome_id,
                "fitness": g.fitness,
                "genes": g.genes,
                "details": g.details,
            }
            for g in inverse_genomes
        ],
        "generation_stats": generation_stats,
        "v1_comparison": {
            "v1_best_genome": "G51883",
            "v1_fitness": 424.68,
            "v1_wr": 98.6,
            "v1_tp_atr_mult": 0.5,
            "v1_sl_atr_mult": 2.1246,
            "v1_failure": "Tight-TP scalper: 0.5x ATR TP / 2.1x ATR SL. "
                          "98.6% WR in-sample but PnL collapsed 96% on 4h timeframe. "
                          "Many small wins, net profit near zero after slippage.",
            "v2_mitigations": {
                "walk_forward": "5-fold sequential prevents single-period overfit",
                "noise_injection": "Worst-of-3 noise evals kills fragile genomes",
                "regularization": "L2 penalty prevents extreme TP/SL asymmetry",
                "slippage": f"{SLIPPAGE_PCT}% slippage kills micro-profit scalpers",
                "min_trades": f"{MIN_TOTAL_TRADES} trades across all folds",
                "island_model": "4 independent populations maintain diversity",
            },
        },
    }

    # Determine output path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "data", "genome_evolution_v2_results.json")

    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        log.info(f"\n  Results saved to {output_path}")
    except Exception as e:
        log.warning(f"Could not save to {output_path}: {e}")
        fallback = "genome_evolution_v2_results.json"
        try:
            with open(fallback, "w") as f:
                json.dump(results, f, indent=2, default=str)
            log.info(f"  Saved to {fallback} instead")
        except Exception:
            pass

    return results


if __name__ == "__main__":
    start = time.time()
    results = evolve()
    elapsed = time.time() - start

    log.info(f"\n  Total time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    # Approximate total fitness evaluations:
    # Each generation: ~POPULATION_SIZE new evals
    # Each eval: WALK_FORWARD_FOLDS * len(SYMBOLS) backtests + NOISE_EVALS * len(SYMBOLS) noise backtests
    backtests_per_eval = (WALK_FORWARD_FOLDS * 2 + NOISE_EVALS) * len(SYMBOLS)
    total_evals = POPULATION_SIZE * NUM_GENERATIONS
    total_backtests = total_evals * backtests_per_eval
    log.info(f"  ~{total_evals:,} fitness evaluations")
    log.info(f"  ~{total_backtests:,} individual backtests")
    if elapsed > 0:
        log.info(f"  Speed: {total_backtests / elapsed:.0f} backtests/sec")
