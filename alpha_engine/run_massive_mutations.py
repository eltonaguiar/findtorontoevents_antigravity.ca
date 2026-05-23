"""
Massive Mutation Runner -- Multi-Fidelity Island-Model Evolution
================================================================
Orchestrates hundreds of thousands of genome mutations through a
multi-fidelity funnel to find robust trading strategies while
aggressively filtering overfitting.

Architecture:
  - 4 islands with heterogeneous objectives (Sharpe, activity, novelty, robustness)
  - 3-tier candle fidelity: 100 -> 500 -> 2000 candles
  - Differential Evolution + Gaussian mutation + inverse + random injection
  - Anti-overfit: min trades, multi-symbol, DSR, walk-forward, noise injection, L2 reg

Usage:
    python alpha_engine/run_massive_mutations.py
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
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

# --- Logging -------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("massive_mutations")

# ═════════════════════════════════════════════════════════════════════════
# 1. CONFIGURATION
# ═════════════════════════════════════════════════════════════════════════
POPULATION = 200          # per island
NUM_ISLANDS = 4
GENERATIONS = 500
TOTAL_EVALS = POPULATION * NUM_ISLANDS * GENERATIONS  # = 400,000
SYMBOLS = ["BTCUSDT", "SOLUSDT", "ETHUSDT", "BNBUSDT", "DOGEUSDT", "AVAXUSDT"]
CANDLE_COUNTS = [100, 500, 2000]  # multi-fidelity tiers

MIGRATION_INTERVAL = 25   # migrate every N generations
MIGRATION_COUNT = 2        # top N from each island migrate clockwise
ELITE_COUNT = 5            # elites preserved per island
TOURNAMENT_SIZE = 5
SLIPPAGE_PCT = 0.05        # 0.05% per trade

# Anti-overfit thresholds
MIN_TRADES_PER_SYMBOL = 20
MIN_PROFITABLE_SYMBOLS = 3
NOISE_PCT = 0.001          # 0.1%
NOISE_SEEDS = 3
WALK_FORWARD_TRAIN_PCT = 0.60
OOS_VS_IS_FLOOR = 0.50    # OOS must be >50% of IS performance

# ═════════════════════════════════════════════════════════════════════════
# 2. GENE RANGES (from genome_evolution_v2.py)
# ═════════════════════════════════════════════════════════════════════════
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

GENE_NAMES = sorted(GENE_RANGES.keys())


# ═════════════════════════════════════════════════════════════════════════
# 3. DATA CLASSES
# ═════════════════════════════════════════════════════════════════════════
@dataclass
class Genome:
    genes: Dict
    fitness: float = 0.0
    details: Dict = field(default_factory=dict)
    generation: int = 0
    genome_id: str = ""
    island: int = 0

    def __post_init__(self):
        if not self.genome_id:
            self.genome_id = f"MM-{random.randint(10000, 99999)}"

    def to_dict(self):
        return {
            "genome_id": self.genome_id,
            "genes": self.genes,
            "fitness": round(self.fitness, 6),
            "details": self.details,
            "generation": self.generation,
            "island": self.island,
        }


# ═════════════════════════════════════════════════════════════════════════
# 4. MARKET DATA FETCHING (urllib only, cached)
# ═════════════════════════════════════════════════════════════════════════
_market_cache: Dict[str, list] = {}


def fetch_candles(symbol: str, interval: str = "1h", limit: int = 2000) -> list:
    """Fetch OHLCV candles with Binance mirror failover + CoinGecko fallback."""
    cache_key = f"{symbol}_{interval}_{limit}"
    if cache_key in _market_cache:
        return _market_cache[cache_key]

    ctx = ssl.create_default_context()

    # Binance mirror failover chain (mandatory per project rules)
    binance_mirrors = [
        "https://api1.binance.com", "https://api2.binance.com",
        "https://api3.binance.com", "https://api4.binance.com",
        "https://api.binance.com",
    ]
    random.shuffle(binance_mirrors)

    for base_url in binance_mirrors:
        url = f"{base_url}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            resp = urllib.request.urlopen(req, timeout=20, context=ctx)
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
            _market_cache[cache_key] = candles
            log.info(f"Fetched {symbol}: {len(candles)} candles ({interval}) via {base_url}")
            return candles
        except Exception as e:
            log.warning(f"Mirror {base_url} failed for {symbol}: {e}")
            time.sleep(1)

    # CoinGecko fallback for major pairs
    coin_map = {
        "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
        "BNBUSDT": "binancecoin", "DOGEUSDT": "dogecoin", "AVAXUSDT": "avalanche-2",
        "XRPUSDT": "ripple", "ADAUSDT": "cardano", "LINKUSDT": "chainlink",
    }
    coin_id = coin_map.get(symbol)
    if coin_id:
        try:
            days = max(limit // 24, 7)
            cg_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency=usd&days={days}"
            req = urllib.request.Request(cg_url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=20, context=ctx)
            data = json.loads(resp.read())
            candles = []
            for k in data:
                candles.append({
                    "ts": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": 0.0,
                })
            if candles:
                _market_cache[cache_key] = candles
                log.info(f"CoinGecko fallback for {symbol}: {len(candles)} candles")
                return candles
        except Exception as e:
            log.warning(f"CoinGecko fallback failed for {symbol}: {e}")

    log.warning(f"All sources failed for {symbol}")
    return []


def candles_to_arrays(candles: list):
    """Convert candle list to parallel arrays (closes, highs, lows, volumes)."""
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    volumes = [c["volume"] for c in candles]
    return closes, highs, lows, volumes


# ═════════════════════════════════════════════════════════════════════════
# 5. TECHNICAL INDICATORS (pure Python fallback)
# ═════════════════════════════════════════════════════════════════════════
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


# ═════════════════════════════════════════════════════════════════════════
# 6. BACKTEST ENGINE
# ═════════════════════════════════════════════════════════════════════════
# Try to import vectorized backtest; fall back to pure Python
try:
    from vectorized_backtest import backtest_genome_vectorized as _vec_bt
    HAS_VECTORIZED = True
    log.info("Using vectorized backtest engine (numpy)")
except ImportError:
    HAS_VECTORIZED = False
    log.info("Vectorized backtest not available; using pure-Python fallback")


def backtest_genome(candles: list, genes: Dict) -> list:
    """Run Keltner Compression Expansion backtest. Returns list of pnl floats."""
    n = len(candles)
    if n < 160:
        return []

    closes, highs, lows, volumes = candles_to_arrays(candles)

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
    vol_sma = calc_sma(volumes, 20)
    atr_sma = calc_sma(atr_vals, 30)

    widths = [channel_mult * atr_vals[i] / (ema_vals[i] + 1e-12) for i in range(n)]

    trades_pnl = []
    min_bars = max(160, comp_window + 5)
    last_signal_bar = -999

    for i in range(min_bars, n - max_hold - 1):
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

        slippage = px * SLIPPAGE_PCT / 100
        entry_px = px + slippage if direction == "LONG" else px - slippage

        tp_dist = tp_atr_mult * a
        sl_dist = sl_atr_mult * a

        if direction == "LONG":
            tp_price = entry_px + tp_dist
            sl_price = entry_px - sl_dist
        else:
            tp_price = entry_px - tp_dist
            sl_price = entry_px + sl_dist

        pnl = None
        for j in range(i + 1, min(i + 1 + max_hold, n)):
            if direction == "LONG":
                if highs[j] >= tp_price:
                    exit_px = tp_price - slippage
                    pnl = (exit_px - entry_px) / entry_px * 100
                    break
                if lows[j] <= sl_price:
                    exit_px = sl_price - slippage
                    pnl = (exit_px - entry_px) / entry_px * 100
                    break
            else:
                if lows[j] <= tp_price:
                    exit_px = tp_price + slippage
                    pnl = (entry_px - exit_px) / entry_px * 100
                    break
                if highs[j] >= sl_price:
                    exit_px = sl_price + slippage
                    pnl = (entry_px - exit_px) / entry_px * 100
                    break

        if pnl is None:
            exit_bar = min(i + max_hold, n - 1)
            exit_px = closes[exit_bar]
            if direction == "LONG":
                exit_px -= slippage
                pnl = (exit_px - entry_px) / entry_px * 100
            else:
                exit_px += slippage
                pnl = (entry_px - exit_px) / entry_px * 100

        pnl *= position_scale
        trades_pnl.append(pnl)
        last_signal_bar = i

    return trades_pnl


# ═════════════════════════════════════════════════════════════════════════
# 7. GENOME CREATION & MUTATION OPERATORS
# ═════════════════════════════════════════════════════════════════════════
def random_genome(generation: int = 0) -> Genome:
    """Create a fully random genome within GENE_RANGES."""
    genes = {}
    for name, (lo, hi, dtype) in GENE_RANGES.items():
        if dtype == "int":
            genes[name] = random.randint(int(lo), int(hi))
        else:
            genes[name] = round(random.uniform(lo, hi), 4)
    return Genome(genes=genes, generation=generation)


def clip_gene(name: str, value: float) -> float:
    """Clip a gene value to its valid range."""
    lo, hi, dtype = GENE_RANGES[name]
    if dtype == "int":
        return max(int(lo), min(int(hi), int(round(value))))
    return max(lo, min(hi, round(value, 4)))


def differential_evolution_mutate(best: Genome, rand1: Genome, rand2: Genome,
                                   F: float = 0.8) -> Dict:
    """DE/best/1 mutation: child_genes = best + F * (rand1 - rand2)."""
    child_genes = {}
    for name in GENE_NAMES:
        val = best.genes[name] + F * (rand1.genes[name] - rand2.genes[name])
        child_genes[name] = clip_gene(name, val)
    return child_genes


def gaussian_mutate(genome: Genome, rate: float, sigma: float) -> Dict:
    """Standard Gaussian mutation with annealing support.

    Args:
        genome: Parent genome.
        rate: Per-gene mutation probability (0-1).
        sigma: Mutation strength as fraction of gene range (0-1).
    """
    child_genes = copy.deepcopy(genome.genes)
    for name, (lo, hi, dtype) in GENE_RANGES.items():
        if random.random() < rate:
            spread = (hi - lo) * sigma
            val = child_genes[name] + random.gauss(0, spread)
            child_genes[name] = clip_gene(name, val)
    return child_genes


def inverse_strategy(genome: Genome) -> Dict:
    """Flip direction: swap TP/SL logic and invert trend filter."""
    inv = copy.deepcopy(genome.genes)
    # Swap TP and SL multipliers
    inv["tp_atr_mult"], inv["sl_atr_mult"] = inv["sl_atr_mult"], inv["tp_atr_mult"]
    # Invert channel_mult symmetrically within range
    lo, hi, _ = GENE_RANGES["channel_mult"]
    inv["channel_mult"] = hi - inv["channel_mult"] + lo
    # Negate trend strength to reverse direction bias
    inv["trend_strength_min"] = clip_gene(
        "trend_strength_min",
        GENE_RANGES["trend_strength_min"][1] - inv["trend_strength_min"]
    )
    return inv


# ═════════════════════════════════════════════════════════════════════════
# 8. FITNESS HELPERS
# ═════════════════════════════════════════════════════════════════════════
# DEPRECATED: Use alpha_engine.validation.sharpe_metrics instead (canonical implementation per TESTING_PROTOCOL v4.0)
def calc_sharpe(pnl_list: list) -> float:
    """Sharpe ratio from per-trade P&L list."""
    if len(pnl_list) < 2:
        return 0.0
    mean = sum(pnl_list) / len(pnl_list)
    var = sum((x - mean) ** 2 for x in pnl_list) / (len(pnl_list) - 1)
    std = math.sqrt(var) if var > 0 else 1e-12
    return mean / std


def calc_profit_factor(pnl_list: list) -> float:
    """Profit factor = gross wins / gross losses."""
    gross_win = sum(p for p in pnl_list if p > 0)
    gross_loss = abs(sum(p for p in pnl_list if p <= 0))
    if gross_loss < 1e-12:
        return 10.0 if gross_win > 0 else 0.0
    return min(gross_win / gross_loss, 10.0)


def calc_win_rate(pnl_list: list) -> float:
    if not pnl_list:
        return 0.0
    return sum(1 for p in pnl_list if p > 0) / len(pnl_list)


def calc_regularization_penalty(genes: Dict) -> float:
    """L2 penalty for distance from proven defaults."""
    penalty = 0.0
    n = 0
    for name, (lo, hi, dtype) in GENE_RANGES.items():
        default_val = DEFAULT_GENOME.get(name, (lo + hi) / 2)
        gene_range = hi - lo
        if gene_range < 1e-12:
            continue
        dist = abs(genes[name] - default_val) / gene_range
        penalty += dist ** 2
        n += 1
    return penalty / n if n > 0 else 0.0


def inject_noise(candles: list, noise_pct: float, seed: int) -> list:
    """Add random noise to OHLCV prices for robustness testing."""
    rng = random.Random(seed)
    noisy = []
    for c in candles:
        fo = 1.0 + rng.uniform(-noise_pct, noise_pct)
        fh = 1.0 + rng.uniform(-noise_pct, noise_pct)
        fl = 1.0 + rng.uniform(-noise_pct, noise_pct)
        fc = 1.0 + rng.uniform(-noise_pct, noise_pct)
        o = c["open"] * fo
        h = c["high"] * fh
        l = c["low"] * fl
        cl = c["close"] * fc
        real_h = max(o, h, cl)
        real_l = min(o, l, cl)
        noisy.append({
            "ts": c["ts"], "open": o, "high": real_h,
            "low": real_l, "close": cl, "volume": c["volume"],
        })
    return noisy


# DEPRECATED: Use alpha_engine.validation.sharpe_metrics instead (canonical implementation per TESTING_PROTOCOL v4.0)
def deflated_sharpe_ratio(observed_sharpe: float, num_trials: int,
                           avg_sharpe: float, std_sharpe: float,
                           num_trades: int) -> float:
    """Lopez de Prado (2014) Deflated Sharpe Ratio.

    Returns p-value: probability the observed Sharpe is due to chance
    given the number of trials. A genome is REAL if p < 0.05.
    """
    if num_trades < 3 or std_sharpe < 1e-12 or num_trials < 2:
        return 1.0

    euler_mascheroni = 0.5772

    # Approximate inverse normal CDF for extreme quantiles
    def inv_norm(p):
        """Rational approximation of inverse normal CDF (Abramowitz & Stegun)."""
        if p <= 0 or p >= 1:
            return 0.0
        if p < 0.5:
            return -_inv_norm_inner(1 - p)
        return _inv_norm_inner(p)

    def _inv_norm_inner(p):
        c0, c1, c2 = 2.515517, 0.802853, 0.010328
        d1, d2, d3 = 1.432788, 0.189269, 0.001308
        t = math.sqrt(-2.0 * math.log(1 - p))
        return t - (c0 + c1 * t + c2 * t * t) / (1 + d1 * t + d2 * t * t + d3 * t * t * t)

    # Normal CDF
    def norm_cdf(x):
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    q1 = 1 - 1.0 / num_trials
    q2 = 1 - 1.0 / (num_trials * math.e)
    e_max_sharpe = avg_sharpe + std_sharpe * (
        (1 - euler_mascheroni) * inv_norm(min(q1, 0.9999))
        + euler_mascheroni * inv_norm(min(q2, 0.9999))
    )

    se_sharpe = math.sqrt(
        (1 + 0.5 * observed_sharpe ** 2) / max(num_trades - 1, 1)
    )

    if se_sharpe < 1e-12:
        return 1.0

    z = (observed_sharpe - e_max_sharpe) / se_sharpe
    p_value = 1 - norm_cdf(z)
    return p_value


# ═════════════════════════════════════════════════════════════════════════
# 9. NOVELTY SEARCH
# ═════════════════════════════════════════════════════════════════════════
_novelty_archive: List[list] = []


def behavior_vector(details: Dict) -> list:
    """Extract behavior descriptor from genome details."""
    return [
        details.get("trade_count", 0) / 100.0,
        details.get("win_rate", 0.5),
        details.get("sharpe", 0),
        details.get("profit_factor", 1.0) / 5.0,
        details.get("symbols_profitable", 0) / len(SYMBOLS),
    ]


def novelty_score(genome: Genome, population: List[Genome], k: int = 5) -> float:
    """Average distance to k nearest neighbors in behavior space."""
    target_bv = behavior_vector(genome.details)

    all_bvs = []
    for other in population:
        if other.genome_id == genome.genome_id:
            continue
        all_bvs.append(behavior_vector(other.details))

    # Also compare to archive
    for abv in _novelty_archive:
        all_bvs.append(abv)

    if not all_bvs:
        return 0.0

    distances = []
    for bv in all_bvs:
        d = math.sqrt(sum((a - b) ** 2 for a, b in zip(target_bv, bv)))
        distances.append(d)

    distances.sort()
    return sum(distances[:k]) / min(k, len(distances))


# ═════════════════════════════════════════════════════════════════════════
# 10. ISLAND MODEL WITH HETEROGENEOUS OBJECTIVES
# ═════════════════════════════════════════════════════════════════════════
def island_fitness(genome: Genome, island_id: int,
                   population: List[Genome]) -> float:
    """Compute fitness according to island-specific objective.

    Island 0: Maximize Sharpe (standard quality)
    Island 1: Maximize trade count (find active strategies)
    Island 2: Novelty search (behavioral diversity from archive)
    Island 3: Robustness (worst-case symbol performance)
    """
    d = genome.details
    base_sharpe = d.get("sharpe", 0)
    trade_count = d.get("trade_count", 0)

    if island_id == 0:
        # Pure Sharpe maximization
        return base_sharpe

    elif island_id == 1:
        # Activity-weighted Sharpe: reward more trades
        activity_bonus = min(trade_count / 200.0, 1.0)
        return max(0, base_sharpe) * (0.5 + 0.5 * activity_bonus)

    elif island_id == 2:
        # Novelty-weighted: 80% fitness + 20% novelty
        nov = novelty_score(genome, population)
        genome.details["novelty_score"] = round(nov, 4)
        return 0.8 * max(0, base_sharpe) + 0.2 * nov

    elif island_id == 3:
        # Robustness: worst-case symbol performance
        symbol_sharpes = d.get("symbol_sharpes", {})
        if not symbol_sharpes:
            return base_sharpe
        worst = min(symbol_sharpes.values())
        return worst

    return base_sharpe


# ═════════════════════════════════════════════════════════════════════════
# 11. MULTI-FIDELITY EVALUATION
# ═════════════════════════════════════════════════════════════════════════
def evaluate_tier1(genome: Genome, btc_candles_100: list) -> bool:
    """Tier 1: Cheap screen on 100 candles, single symbol.
    Returns True if genome passes minimum viability.
    """
    trades = backtest_genome(btc_candles_100, genome.genes)
    if len(trades) < 3:
        return False
    wr = calc_win_rate(trades)
    if wr < 0.40:
        return False
    total_pnl = sum(trades)
    if total_pnl <= 0:
        return False
    pf = calc_profit_factor(trades)
    genome.details = {
        "trade_count": len(trades),
        "win_rate": round(wr, 4),
        "total_pnl": round(total_pnl, 4),
        "profit_factor": round(pf, 4),
    }
    genome.fitness = total_pnl
    return True


def evaluate_tier2(genome: Genome, symbol_candles_500: Dict[str, list]) -> bool:
    """Tier 2: 500 candles, multiple symbols, walk-forward split.
    Returns True if genome passes OOS validation.
    """
    all_oos_pnl = []
    symbols_profitable = 0

    for sym, candles in symbol_candles_500.items():
        if not candles:
            continue
        n = len(candles)
        split = int(n * WALK_FORWARD_TRAIN_PCT)

        train_candles = candles[:split]
        test_candles = candles[split:]

        is_trades = backtest_genome(train_candles, genome.genes)
        oos_trades = backtest_genome(test_candles, genome.genes)

        if not oos_trades:
            continue

        oos_pnl = sum(oos_trades)
        all_oos_pnl.extend(oos_trades)

        if oos_pnl > 0 and len(oos_trades) >= 5:
            symbols_profitable += 1

        # Walk-forward check: OOS must be reasonable vs IS
        is_pnl = sum(is_trades) if is_trades else 0
        if is_pnl > 0 and oos_pnl < is_pnl * OOS_VS_IS_FLOOR * -1:
            return False  # massive OOS degradation

    if not all_oos_pnl or len(all_oos_pnl) < 10:
        return False

    oos_wr = calc_win_rate(all_oos_pnl)
    oos_pf = calc_profit_factor(all_oos_pnl)
    oos_sharpe = calc_sharpe(all_oos_pnl)

    if oos_wr < 0.45 or oos_pf < 1.0:
        return False

    genome.details.update({
        "oos_trade_count": len(all_oos_pnl),
        "oos_win_rate": round(oos_wr, 4),
        "oos_pf": round(oos_pf, 4),
        "oos_sharpe": round(oos_sharpe, 4),
        "symbols_profitable": symbols_profitable,
    })
    genome.fitness = oos_sharpe
    return True


def evaluate_full(genome: Genome, symbol_candles_2000: Dict[str, list]) -> bool:
    """Full evaluation: 2000 candles, all 6 symbols, walk-forward,
    noise injection, cross-symbol gate, regularization penalty.
    """
    symbol_sharpes = {}
    symbol_trades = {}
    all_oos_pnl = []
    all_is_pnl = []
    symbols_profitable = 0
    total_oos_trades = 0

    for sym, candles in symbol_candles_2000.items():
        if not candles or len(candles) < 200:
            continue

        n = len(candles)
        split = int(n * WALK_FORWARD_TRAIN_PCT)
        train = candles[:split]
        test = candles[split:]

        is_trades = backtest_genome(train, genome.genes)
        oos_trades = backtest_genome(test, genome.genes)

        is_pnl_list = is_trades
        oos_pnl_list = oos_trades

        if len(oos_pnl_list) < MIN_TRADES_PER_SYMBOL:
            symbol_sharpes[sym] = 0.0
            symbol_trades[sym] = len(oos_pnl_list)
            continue

        oos_sharpe = calc_sharpe(oos_pnl_list)
        symbol_sharpes[sym] = round(oos_sharpe, 4)
        symbol_trades[sym] = len(oos_pnl_list)
        all_oos_pnl.extend(oos_pnl_list)
        all_is_pnl.extend(is_pnl_list)
        total_oos_trades += len(oos_pnl_list)

        if sum(oos_pnl_list) > 0:
            symbols_profitable += 1

    # -- Anti-overfit gate: must be profitable on 3+ symbols --
    if symbols_profitable < MIN_PROFITABLE_SYMBOLS:
        genome.fitness = 0.0
        return False

    if not all_oos_pnl or total_oos_trades < 30:
        genome.fitness = 0.0
        return False

    # -- Walk-forward OOS vs IS check --
    is_total = sum(all_is_pnl)
    oos_total = sum(all_oos_pnl)
    if is_total > 0 and oos_total < is_total * OOS_VS_IS_FLOOR * -1:
        genome.fitness = 0.0
        return False

    # -- Noise injection: take worst of NOISE_SEEDS runs --
    noise_sharpes = []
    for seed in range(NOISE_SEEDS):
        noise_pnl = []
        for sym, candles in symbol_candles_2000.items():
            if not candles or len(candles) < 200:
                continue
            noisy = inject_noise(candles, NOISE_PCT, seed * 1000 + hash(sym) % 10000)
            split = int(len(noisy) * WALK_FORWARD_TRAIN_PCT)
            oos_noisy = backtest_genome(noisy[split:], genome.genes)
            noise_pnl.extend(oos_noisy)
        if noise_pnl:
            noise_sharpes.append(calc_sharpe(noise_pnl))
        else:
            noise_sharpes.append(0.0)

    worst_noise_sharpe = min(noise_sharpes) if noise_sharpes else 0.0

    # -- Regularization penalty --
    reg_penalty = calc_regularization_penalty(genome.genes)

    # -- Combined fitness --
    oos_sharpe = calc_sharpe(all_oos_pnl)
    oos_wr = calc_win_rate(all_oos_pnl)
    oos_pf = calc_profit_factor(all_oos_pnl)

    # Fitness = weighted combination
    fitness = (
        0.40 * oos_sharpe
        + 0.25 * worst_noise_sharpe
        + 0.15 * min(oos_pf / 3.0, 1.0)
        + 0.10 * min(symbols_profitable / len(SYMBOLS), 1.0)
        + 0.10 * oos_wr
        - 0.05 * reg_penalty
    )

    genome.fitness = round(fitness, 6)
    genome.details.update({
        "sharpe": round(oos_sharpe, 4),
        "noise_sharpe_worst": round(worst_noise_sharpe, 4),
        "win_rate": round(oos_wr, 4),
        "profit_factor": round(oos_pf, 4),
        "trade_count": total_oos_trades,
        "total_oos_pnl": round(oos_total, 4),
        "symbols_profitable": symbols_profitable,
        "symbol_sharpes": symbol_sharpes,
        "symbol_trades": symbol_trades,
        "reg_penalty": round(reg_penalty, 4),
    })
    return True


# ═════════════════════════════════════════════════════════════════════════
# 12. SELECTION & BREEDING
# ═════════════════════════════════════════════════════════════════════════
def tournament_select(population: List[Genome], k: int = TOURNAMENT_SIZE) -> Genome:
    """Tournament selection: pick k random, return the best."""
    candidates = random.sample(population, min(k, len(population)))
    return max(candidates, key=lambda g: g.fitness)


def breed_next_generation(population: List[Genome], island_id: int,
                           generation: int) -> List[Genome]:
    """Create next generation for one island using mixed mutation operators.

    Operator mix:
      - 40% Differential Evolution (DE/best/1)
      - 30% Gaussian mutation (with annealing)
      - 10% Inverse strategy
      - 10% Crossover (uniform) between two parents
      - 10% Fresh random genomes
    """
    pop_sorted = sorted(population, key=lambda g: g.fitness, reverse=True)
    elites = [copy.deepcopy(g) for g in pop_sorted[:ELITE_COUNT]]
    best = pop_sorted[0]

    # Anneal mutation strength: strong early, gentle late
    progress = generation / max(GENERATIONS, 1)
    sigma = 0.3 * (1 - 0.6 * progress)  # 0.3 -> 0.12
    mut_rate = 0.35 * (1 - 0.4 * progress)  # 0.35 -> 0.21

    children = list(elites)
    target_size = POPULATION

    while len(children) < target_size:
        roll = random.random()

        if roll < 0.40:
            # Differential Evolution
            r1 = tournament_select(population)
            r2 = tournament_select(population)
            # Ensure distinct genomes
            attempts = 0
            while r2.genome_id == r1.genome_id and attempts < 5:
                r2 = tournament_select(population)
                attempts += 1
            child_genes = differential_evolution_mutate(best, r1, r2, F=0.8)

        elif roll < 0.70:
            # Gaussian mutation
            parent = tournament_select(population)
            child_genes = gaussian_mutate(parent, mut_rate, sigma)

        elif roll < 0.80:
            # Inverse strategy
            parent = tournament_select(population)
            child_genes = inverse_strategy(parent)

        elif roll < 0.90:
            # Uniform crossover between two parents
            p1 = tournament_select(population)
            p2 = tournament_select(population)
            child_genes = {}
            for name in GENE_NAMES:
                child_genes[name] = p1.genes[name] if random.random() < 0.5 else p2.genes[name]

        else:
            # Fresh random genome (exploration)
            child_genes = random_genome(generation).genes

        child = Genome(genes=child_genes, generation=generation, island=island_id)
        children.append(child)

    return children[:target_size]


def migrate(islands: List[List[Genome]], generation: int):
    """Ring migration: top MIGRATION_COUNT from each island move clockwise."""
    migrants = []
    for island in islands:
        island_sorted = sorted(island, key=lambda g: g.fitness, reverse=True)
        migrants.append([copy.deepcopy(g) for g in island_sorted[:MIGRATION_COUNT]])

    for i in range(NUM_ISLANDS):
        src = (i - 1) % NUM_ISLANDS  # clockwise: island 3 -> 0, 0 -> 1, etc.
        incoming = migrants[src]
        # Replace worst genomes in target island
        islands[i].sort(key=lambda g: g.fitness)
        for j, migrant in enumerate(incoming):
            migrant.island = i
            islands[i][j] = migrant

    log.info(f"  [Gen {generation}] Migration complete: "
             f"{MIGRATION_COUNT} genomes moved between islands")


# ═════════════════════════════════════════════════════════════════════════
# 13. MAIN EVOLUTION LOOP
# ═════════════════════════════════════════════════════════════════════════
def run_evolution():
    """Run the full multi-fidelity island-model evolution."""
    global _novelty_archive

    start_time = time.time()
    log.info("=" * 70)
    log.info("MASSIVE MUTATION ENGINE -- Multi-Fidelity Island Evolution")
    log.info(f"Population: {POPULATION} x {NUM_ISLANDS} islands = "
             f"{POPULATION * NUM_ISLANDS} per generation")
    log.info(f"Generations: {GENERATIONS}")
    log.info(f"Total evaluations budget: {TOTAL_EVALS:,}")
    log.info(f"Symbols: {SYMBOLS}")
    log.info(f"Candle tiers: {CANDLE_COUNTS}")
    log.info("=" * 70)

    # -- Fetch market data at all fidelity tiers --
    log.info("Fetching market data...")
    data_100 = {}
    data_500 = {}
    data_2000 = {}

    for sym in SYMBOLS:
        data_100[sym] = fetch_candles(sym, "1h", CANDLE_COUNTS[0])
        time.sleep(0.3)  # rate limit
        data_500[sym] = fetch_candles(sym, "1h", CANDLE_COUNTS[1])
        time.sleep(0.3)
        data_2000[sym] = fetch_candles(sym, "1h", CANDLE_COUNTS[2])
        time.sleep(0.3)

    btc_100 = data_100.get("BTCUSDT", [])
    if not btc_100:
        log.error("Failed to fetch BTC candles. Cannot proceed.")
        return None

    log.info(f"Data fetched: {sum(1 for v in data_2000.values() if v)} symbols ready")

    # -- Initialize islands --
    islands: List[List[Genome]] = []
    for island_id in range(NUM_ISLANDS):
        island_pop = []
        for _ in range(POPULATION):
            g = random_genome(generation=0)
            g.island = island_id
            island_pop.append(g)
        islands.append(island_pop)

    log.info(f"Initialized {NUM_ISLANDS} islands x {POPULATION} genomes")

    # -- Tracking --
    total_evals_done = 0
    best_ever_fitness = -999
    best_ever_genome = None
    all_sharpes_seen = []  # for DSR calculation
    tier2_pass_count = 0
    tier3_pass_count = 0

    # -- Evolution loop --
    for gen in range(GENERATIONS):
        gen_start = time.time()

        for island_id in range(NUM_ISLANDS):
            population = islands[island_id]

            # -- TIER 1: Quick screen on 100 BTC candles --
            tier1_survivors = []
            for genome in population:
                passed = evaluate_tier1(genome, btc_100)
                total_evals_done += 1
                if passed:
                    tier1_survivors.append(genome)
                else:
                    genome.fitness = 0.0

            # -- TIER 2: Medium screen on 500 candles, 2 symbols --
            tier2_data = {s: data_500[s] for s in ["BTCUSDT", "SOLUSDT"] if s in data_500}
            for genome in tier1_survivors:
                passed = evaluate_tier2(genome, tier2_data)
                total_evals_done += 1
                if passed:
                    tier2_pass_count += 1

            # -- Compute island-specific fitness --
            for genome in population:
                if genome.fitness > 0:
                    genome.fitness = island_fitness(genome, island_id, population)
                    all_sharpes_seen.append(genome.details.get("oos_sharpe",
                                            genome.details.get("sharpe", 0)))

            # -- Breed next generation --
            islands[island_id] = breed_next_generation(
                population, island_id, gen + 1
            )

        # -- Migration --
        if gen > 0 and gen % MIGRATION_INTERVAL == 0:
            migrate(islands, gen)

        # -- Update novelty archive --
        for island in islands:
            for g in island:
                if g.fitness > 0 and random.random() < 0.02:
                    _novelty_archive.append(behavior_vector(g.details))
        # Keep archive bounded
        if len(_novelty_archive) > 500:
            _novelty_archive = _novelty_archive[-500:]

        # -- Track best --
        all_genomes = [g for island in islands for g in island]
        gen_best = max(all_genomes, key=lambda g: g.fitness)
        if gen_best.fitness > best_ever_fitness:
            best_ever_fitness = gen_best.fitness
            best_ever_genome = copy.deepcopy(gen_best)

        # -- Progress report every 50 generations --
        if gen % 50 == 0 or gen == GENERATIONS - 1:
            elapsed = time.time() - start_time
            gen_time = time.time() - gen_start
            log.info(f"[Gen {gen:>4}/{GENERATIONS}] "
                     f"Best={best_ever_fitness:.4f} "
                     f"GenBest={gen_best.fitness:.4f} "
                     f"T1surv={sum(1 for isl in islands for g in isl if g.fitness > 0)} "
                     f"T2pass={tier2_pass_count} "
                     f"Evals={total_evals_done:,} "
                     f"Time={elapsed:.0f}s "
                     f"GenTime={gen_time:.1f}s")

    # ═════════════════════════════════════════════════════════════════════
    # 14. FULL EVALUATION (TIER 3) ON TOP SURVIVORS
    # ═════════════════════════════════════════════════════════════════════
    log.info("=" * 70)
    log.info("TIER 3: Full evaluation of top candidates on 2000 candles x 6 symbols")
    log.info("=" * 70)

    # Collect top genomes from all islands
    all_genomes = [g for island in islands for g in island]
    all_genomes.sort(key=lambda g: g.fitness, reverse=True)
    tier3_candidates = all_genomes[:200]  # top 200 for full eval

    tier3_survivors = []
    for i, genome in enumerate(tier3_candidates):
        passed = evaluate_full(genome, data_2000)
        total_evals_done += 1
        if passed:
            tier3_survivors.append(genome)
            tier3_pass_count += 1
            if i < 20 or genome.fitness > 0.5:
                log.info(f"  TIER3 PASS: {genome.genome_id} "
                         f"fitness={genome.fitness:.4f} "
                         f"sharpe={genome.details.get('sharpe', 0):.3f} "
                         f"WR={genome.details.get('win_rate', 0):.1%} "
                         f"PF={genome.details.get('profit_factor', 0):.2f} "
                         f"trades={genome.details.get('trade_count', 0)} "
                         f"sym_ok={genome.details.get('symbols_profitable', 0)}")

    log.info(f"TIER 3 results: {tier3_pass_count}/{len(tier3_candidates)} passed")

    # ═════════════════════════════════════════════════════════════════════
    # 15. DEFLATED SHARPE RATIO CORRECTION
    # ═════════════════════════════════════════════════════════════════════
    log.info("Applying Deflated Sharpe Ratio correction...")

    if all_sharpes_seen and tier3_survivors:
        avg_sharpe = sum(all_sharpes_seen) / len(all_sharpes_seen)
        if len(all_sharpes_seen) > 1:
            var_s = sum((s - avg_sharpe) ** 2 for s in all_sharpes_seen) / (len(all_sharpes_seen) - 1)
            std_sharpe = math.sqrt(var_s) if var_s > 0 else 0.1
        else:
            std_sharpe = 0.1

        dsr_validated = []
        for genome in tier3_survivors:
            obs_sharpe = genome.details.get("sharpe", 0)
            n_trades = genome.details.get("trade_count", 0)

            p_val = deflated_sharpe_ratio(
                observed_sharpe=obs_sharpe,
                num_trials=total_evals_done,
                avg_sharpe=avg_sharpe,
                std_sharpe=std_sharpe,
                num_trades=n_trades,
            )
            genome.details["dsr_p_value"] = round(p_val, 6)

            if p_val < 0.05:
                dsr_validated.append(genome)
                log.info(f"  DSR PASS: {genome.genome_id} "
                         f"sharpe={obs_sharpe:.3f} p={p_val:.4f}")
            else:
                log.info(f"  DSR FAIL: {genome.genome_id} "
                         f"sharpe={obs_sharpe:.3f} p={p_val:.4f}")

        # If DSR is too strict (no survivors), fall back to top by fitness
        if not dsr_validated:
            log.warning("No genomes passed DSR at p<0.05. "
                        "Taking top 10 by fitness as fallback.")
            dsr_validated = sorted(tier3_survivors,
                                    key=lambda g: g.fitness, reverse=True)[:10]
    else:
        dsr_validated = tier3_survivors

    # ═════════════════════════════════════════════════════════════════════
    # 16. OUTPUT RESULTS
    # ═════════════════════════════════════════════════════════════════════
    elapsed_total = time.time() - start_time

    # Sort by fitness, take top 50
    final_survivors = sorted(dsr_validated, key=lambda g: g.fitness, reverse=True)[:50]

    results = {
        "metadata": {
            "run_time_seconds": round(elapsed_total, 1),
            "total_generations": GENERATIONS,
            "total_evals": total_evals_done,
            "population_per_island": POPULATION,
            "num_islands": NUM_ISLANDS,
            "symbols": SYMBOLS,
            "candle_tiers": CANDLE_COUNTS,
            "tier1_total": POPULATION * NUM_ISLANDS * GENERATIONS,
            "tier2_passed": tier2_pass_count,
            "tier3_candidates": len(tier3_candidates) if 'tier3_candidates' in dir() else 0,
            "tier3_passed": tier3_pass_count,
            "dsr_passed": len(dsr_validated),
            "final_survivors": len(final_survivors),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
        "top_genomes": [g.to_dict() for g in final_survivors],
    }

    # Ensure output directory exists
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        script_dir = os.path.join(os.getcwd(), "alpha_engine")
    output_dir = os.path.join(script_dir, "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "massive_mutation_results.json")

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    log.info("=" * 70)
    log.info("EVOLUTION COMPLETE")
    log.info(f"  Total time:      {elapsed_total:.0f}s ({elapsed_total / 60:.1f} min)")
    log.info(f"  Total evals:     {total_evals_done:,}")
    log.info(f"  Tier 2 passed:   {tier2_pass_count}")
    log.info(f"  Tier 3 passed:   {tier3_pass_count}")
    log.info(f"  DSR validated:   {len(dsr_validated)}")
    log.info(f"  Final survivors: {len(final_survivors)}")
    log.info(f"  Best fitness:    {best_ever_fitness:.4f}")
    if final_survivors:
        top = final_survivors[0]
        log.info(f"  Top genome:      {top.genome_id}")
        log.info(f"    Sharpe:  {top.details.get('sharpe', 'N/A')}")
        log.info(f"    WR:      {top.details.get('win_rate', 'N/A')}")
        log.info(f"    PF:      {top.details.get('profit_factor', 'N/A')}")
        log.info(f"    Trades:  {top.details.get('trade_count', 'N/A')}")
        log.info(f"    Symbols: {top.details.get('symbols_profitable', 'N/A')}/{len(SYMBOLS)}")
    log.info(f"  Results saved:   {output_path}")
    log.info("=" * 70)

    return results


# ═════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    results = run_evolution()
    if results:
        n = len(results.get("top_genomes", []))
        print(f"\nDone. {n} genomes survived all anti-overfit gates.")
    else:
        print("\nEvolution failed -- check logs above.")
        sys.exit(1)
