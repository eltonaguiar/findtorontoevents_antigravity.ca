"""
Genome Evolution Engine -- Intensive Parameter Optimization
============================================================
Genetic algorithm that evolves Keltner Compression Expansion parameters
across thousands of generations to find optimal trading genomes.

Approach:
  - Population of 60 genomes per generation
  - 150 generations = 9,000 unique backtests
  - Multi-symbol fitness (BTC + ETH + SOL + BNB + XRP + DOGE + AVAX)
  - Crossbreeding top performers + random mutations
  - Elitism (top 10% survive unchanged)
  - Multi-objective fitness: WR * PF * sqrt(trades) * consistency_bonus

Gene Space (14 parameters):
  - ema_period: 10-60
  - atr_period: 8-40
  - channel_mult: 1.0-3.5
  - comp_window: 30-150
  - tp_atr_mult: 0.5-4.0
  - sl_atr_mult: 0.3-2.5
  - max_hold: 4-24 bars
  - hma_period: 10-50
  - min_edge: 0.0-0.5 (minimum breakout edge to trigger)
  - vol_gate_high: 1.5-3.0 (ATR ratio for half-size)
  - vol_gate_extreme: 2.5-5.0 (ATR ratio for skip)
  - trend_strength_min: 0.0-0.01 (min HMA slope)
  - reentry_cooldown: 0-6 bars (min bars between signals)
  - volume_confirm: 0.5-3.0 (volume ratio threshold)

Usage:
    py genome_evolution.py
"""

import json
import ssl
import time
import random
import urllib.request
import math
import copy
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

# --- Configuration -------------------------------------------------------
POPULATION_SIZE = 60
NUM_GENERATIONS = 150
ELITE_PCT = 0.10        # Top 10% survive unchanged
MUTATION_RATE = 0.25     # 25% chance per gene to mutate
CROSSOVER_RATE = 0.70    # 70% of children from crossbreeding
TOURNAMENT_SIZE = 5      # Tournament selection pressure
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT"]
CANDLE_LIMIT = 500       # 500 x 1h = ~21 days
MIN_TRADES_PER_SYMBOL = 3

# --- Gene Definitions ---------------------------------------------------
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

# Base genome (proven BTC parameters)
BASE_GENOME = {
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


@dataclass
class TradeResult:
    direction: str
    pnl_pct: float
    bars_held: int


@dataclass
class Genome:
    genes: Dict
    fitness: float = 0.0
    details: Dict = field(default_factory=dict)
    generation: int = 0
    genome_id: str = ""

    def __post_init__(self):
        if not self.genome_id:
            self.genome_id = f"G{random.randint(10000,99999)}"


# --- Market Data ---------------------------------------------------------
_market_data_cache: Dict[str, list] = {}


_BINANCE_KLINE_BASES = [
    "https://api.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]


def fetch_candles(symbol: str, interval: str = "1h", limit: int = 500) -> list:
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
            return candles
        except urllib.error.HTTPError as e:
            if e.code in (451, 403):
                continue  # geo-blocked, try next
            time.sleep(1)
        except Exception as e:
            time.sleep(1)
            continue

    print(f"  [WARN] Failed to fetch {symbol} from all Binance endpoints")
    return []


# --- Technical Indicators (pure Python, optimized) -----------------------
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


# --- Backtest Engine -----------------------------------------------------
def backtest_genome(candles: list, genes: Dict) -> List[TradeResult]:
    """Run the Keltner Compression Expansion strategy with given genome parameters."""
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
        # Cooldown check
        if i - last_signal_bar < cooldown:
            continue

        a = atr_vals[i]
        if a < 1e-12:
            continue

        # ATR volatility gate
        atr_mean = atr_sma[i]
        if atr_mean > 0:
            atr_ratio = a / atr_mean
        else:
            atr_ratio = 1.0

        if atr_ratio > vol_gate_extreme:
            continue  # Skip extreme volatility

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

        # HMA trend filter
        hma_slope = (hma_vals[i] - hma_vals[i - 1]) / (closes[i] + 1e-12)
        hma_rising = hma_slope > trend_min
        hma_falling = hma_slope < -trend_min

        # Volume confirmation
        if vol_confirm > 0 and vol_sma[i] > 0:
            vol_ratio = volumes[i] / vol_sma[i]
            if vol_ratio < vol_confirm:
                continue

        # Edge calculation
        edge_buy = max(0.0, (px - upper) / (a + 1e-12))
        edge_sell = max(0.0, (lower - px) / (a + 1e-12))

        direction = None
        if px > upper and hma_rising and edge_buy >= min_edge:
            direction = "LONG"
        elif px < lower and hma_falling and edge_sell >= min_edge:
            direction = "SHORT"

        if direction is None:
            continue

        # Simulate trade
        tp_dist = tp_atr_mult * a
        sl_dist = sl_atr_mult * a

        if direction == "LONG":
            tp_price = px + tp_dist
            sl_price = px - sl_dist
        else:
            tp_price = px - tp_dist
            sl_price = px + sl_dist

        pnl = None
        bars_held = 0
        for j in range(i + 1, min(i + 1 + max_hold, len(candles))):
            bars_held = j - i
            if direction == "LONG":
                if candles[j]["high"] >= tp_price:
                    pnl = (tp_price - px) / px * 100
                    break
                if candles[j]["low"] <= sl_price:
                    pnl = (sl_price - px) / px * 100
                    break
            else:
                if candles[j]["low"] <= tp_price:
                    pnl = (px - tp_price) / px * 100
                    break
                if candles[j]["high"] >= sl_price:
                    pnl = (px - sl_price) / px * 100
                    break

        if pnl is None:
            exit_bar = min(i + max_hold, len(candles) - 1)
            exit_px = candles[exit_bar]["close"]
            if direction == "LONG":
                pnl = (exit_px - px) / px * 100
            else:
                pnl = (px - exit_px) / px * 100
            bars_held = exit_bar - i

        # Apply position scale to P/L
        pnl *= position_scale

        trades.append(TradeResult(direction, pnl, bars_held))
        last_signal_bar = i

    return trades


# --- Fitness Function ----------------------------------------------------
def calculate_fitness(genome: Genome, all_candles: Dict[str, list]) -> float:
    """
    Multi-objective fitness combining:
      - Win rate (must be > 50%)
      - Profit factor (higher = better)
      - Trade count (sqrt scaling -- more trades = more confidence)
      - Consistency across symbols (bonus for working on multiple)
      - Max consecutive losses penalty
    """
    total_trades = 0
    total_wins = 0
    total_pnl = 0.0
    gross_wins = 0.0
    gross_losses = 0.0
    symbols_profitable = 0
    max_consec_loss = 0
    symbol_details = {}

    for symbol, candles in all_candles.items():
        if not candles:
            continue

        trades = backtest_genome(candles, genome.genes)
        n = len(trades)
        if n < MIN_TRADES_PER_SYMBOL:
            symbol_details[symbol] = {"trades": n, "wr": 0, "pnl": 0, "status": "INSUFFICIENT"}
            continue

        wins = sum(1 for t in trades if t.pnl_pct > 0)
        losses = n - wins
        wr = wins / n
        pnl = sum(t.pnl_pct for t in trades)
        gw = sum(t.pnl_pct for t in trades if t.pnl_pct > 0)
        gl = abs(sum(t.pnl_pct for t in trades if t.pnl_pct <= 0))

        # Max consecutive losses
        consec = 0
        for t in trades:
            if t.pnl_pct <= 0:
                consec += 1
                max_consec_loss = max(max_consec_loss, consec)
            else:
                consec = 0

        total_trades += n
        total_wins += wins
        total_pnl += pnl
        gross_wins += gw
        gross_losses += gl
        if pnl > 0:
            symbols_profitable += 1

        symbol_details[symbol] = {
            "trades": n, "wins": wins, "wr": round(wr * 100, 1),
            "pnl": round(pnl, 2), "pf": round(gw / gl, 2) if gl > 0 else 99.9,
        }

    if total_trades < 10:
        genome.fitness = 0.0
        genome.details = {"reason": "too_few_trades", "total_trades": total_trades}
        return 0.0

    overall_wr = total_wins / total_trades
    pf = gross_wins / gross_losses if gross_losses > 0 else 99.9

    # Base fitness components
    wr_score = max(0, (overall_wr - 0.45) * 10)  # 0 at 45%, 5.5 at 100%
    pf_score = min(pf, 10.0)                      # Cap PF contribution at 10
    trade_score = math.sqrt(total_trades)          # More trades = more confidence
    consistency = symbols_profitable / len(all_candles)  # What fraction of symbols profitable?
    consec_penalty = max(0, 1.0 - max_consec_loss * 0.05)  # Penalize long losing streaks

    # Penalty for extreme WR (likely overfit if > 90%)
    overfit_penalty = 1.0
    if overall_wr > 0.85:
        overfit_penalty = 0.7
    elif overall_wr > 0.80:
        overfit_penalty = 0.85

    fitness = wr_score * pf_score * trade_score * (0.5 + 0.5 * consistency) * consec_penalty * overfit_penalty

    genome.fitness = round(fitness, 4)
    genome.details = {
        "total_trades": total_trades, "wins": total_wins,
        "wr": round(overall_wr * 100, 1), "pf": round(pf, 2),
        "total_pnl": round(total_pnl, 2),
        "symbols_profitable": symbols_profitable,
        "max_consec_loss": max_consec_loss,
        "per_symbol": symbol_details,
    }
    return fitness


# --- Genetic Operators ---------------------------------------------------
def random_genome(generation: int = 0) -> Genome:
    genes = {}
    for name, (lo, hi, dtype) in GENE_RANGES.items():
        if dtype == "int":
            genes[name] = random.randint(int(lo), int(hi))
        else:
            genes[name] = round(random.uniform(lo, hi), 4)
    return Genome(genes=genes, generation=generation)


def mutate(genome: Genome, generation: int, rate: float = MUTATION_RATE) -> Genome:
    """Mutate genes with decreasing magnitude over generations."""
    new_genes = copy.deepcopy(genome.genes)
    decay = max(0.3, 1.0 - generation / (NUM_GENERATIONS * 1.5))  # Anneal mutation strength

    for name, (lo, hi, dtype) in GENE_RANGES.items():
        if random.random() < rate:
            span = hi - lo
            delta = random.gauss(0, span * 0.15 * decay)
            if dtype == "int":
                new_genes[name] = max(int(lo), min(int(hi), int(new_genes[name] + delta)))
            else:
                new_genes[name] = max(lo, min(hi, round(new_genes[name] + delta, 4)))

    child = Genome(genes=new_genes, generation=generation)
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
            # Average (blend) the two parents
            val = (parent1.genes[name] + parent2.genes[name]) / 2
            _, _, dtype = GENE_RANGES[name]
            if dtype == "int":
                child_genes[name] = int(round(val))
            else:
                child_genes[name] = round(val, 4)

    return Genome(genes=child_genes, generation=generation)


def tournament_select(population: List[Genome], k: int = TOURNAMENT_SIZE) -> Genome:
    """Tournament selection -- pick k random, return the fittest."""
    contestants = random.sample(population, min(k, len(population)))
    return max(contestants, key=lambda g: g.fitness)


# --- Evolution Engine ----------------------------------------------------
def evolve():
    print("=" * 80)
    print("  GENOME EVOLUTION ENGINE -- Keltner Compression Expansion")
    print(f"  Population: {POPULATION_SIZE} | Generations: {NUM_GENERATIONS}")
    print(f"  Symbols: {', '.join(SYMBOLS)}")
    print(f"  Total backtests: ~{POPULATION_SIZE * NUM_GENERATIONS:,}")
    print("=" * 80)

    # Fetch market data for all symbols
    print("\n[1/3] Fetching market data...")
    all_candles = {}
    for sym in SYMBOLS:
        print(f"  Fetching {sym}...", end=" ", flush=True)
        candles = fetch_candles(sym, "1h", CANDLE_LIMIT)
        all_candles[sym] = candles
        print(f"{len(candles)} candles")
        time.sleep(0.3)  # Rate limit

    # Initialize population
    print(f"\n[2/3] Initializing population of {POPULATION_SIZE}...")
    population: List[Genome] = []

    # Seed with base genome + small mutations
    base = Genome(genes=copy.deepcopy(BASE_GENOME), generation=0, genome_id="BASE_OG")
    population.append(base)

    # Seed with variations of the base
    for i in range(9):
        variant = mutate(base, 0, rate=0.4)
        variant.genome_id = f"BASE_V{i}"
        population.append(variant)

    # Fill rest with random genomes
    while len(population) < POPULATION_SIZE:
        population.append(random_genome(0))

    # Evaluate initial population
    for g in population:
        calculate_fitness(g, all_candles)

    population.sort(key=lambda g: g.fitness, reverse=True)
    best_ever = copy.deepcopy(population[0])

    print(f"  Initial best: fitness={best_ever.fitness:.2f} "
          f"WR={best_ever.details.get('wr', 0)}% "
          f"PF={best_ever.details.get('pf', 0)} "
          f"trades={best_ever.details.get('total_trades', 0)}")

    # Evolution loop
    print(f"\n[3/3] Evolving {NUM_GENERATIONS} generations...")
    hall_of_fame: List[Genome] = []
    stagnation_counter = 0

    for gen in range(1, NUM_GENERATIONS + 1):
        elite_count = max(2, int(POPULATION_SIZE * ELITE_PCT))
        new_population = []

        # Elitism -- keep top performers unchanged
        for g in population[:elite_count]:
            elite = copy.deepcopy(g)
            elite.generation = gen
            new_population.append(elite)

        # Generate children
        while len(new_population) < POPULATION_SIZE:
            if random.random() < CROSSOVER_RATE:
                p1 = tournament_select(population)
                p2 = tournament_select(population)
                child = crossover(p1, p2, gen)
                # Also mutate crossover children sometimes
                if random.random() < 0.5:
                    child = mutate(child, gen, rate=MUTATION_RATE * 0.7)
            else:
                parent = tournament_select(population)
                child = mutate(parent, gen)

            new_population.append(child)

        # Inject fresh blood every 20 generations to prevent stagnation
        if gen % 20 == 0:
            for _ in range(3):
                idx = random.randint(POPULATION_SIZE - 5, POPULATION_SIZE - 1)
                new_population[idx] = random_genome(gen)

        # Evaluate
        for g in new_population:
            if g.fitness == 0.0 or g.generation == gen:
                calculate_fitness(g, all_candles)

        new_population.sort(key=lambda g: g.fitness, reverse=True)
        population = new_population

        # Track best
        gen_best = population[0]
        if gen_best.fitness > best_ever.fitness:
            best_ever = copy.deepcopy(gen_best)
            stagnation_counter = 0
            marker = " *** NEW BEST ***"
        else:
            stagnation_counter += 1
            marker = ""

        # Hall of fame -- save unique high-performers
        if gen_best.fitness > 0 and gen_best.details.get("wr", 0) >= 55:
            if not any(g.genome_id == gen_best.genome_id for g in hall_of_fame):
                hall_of_fame.append(copy.deepcopy(gen_best))

        # Status every 10 generations
        if gen % 10 == 0 or marker:
            avg_fit = sum(g.fitness for g in population) / len(population)
            d = gen_best.details
            print(f"  Gen {gen:>3}: best={gen_best.fitness:>7.2f} "
                  f"WR={d.get('wr',0):>5.1f}% PF={d.get('pf',0):>5.2f} "
                  f"trades={d.get('total_trades',0):>3} "
                  f"pnl={d.get('total_pnl',0):>+7.2f}% "
                  f"syms={d.get('symbols_profitable',0)}/{len(SYMBOLS)} "
                  f"avg_fit={avg_fit:>6.2f}{marker}")

        # Adaptive mutation -- increase if stagnating
        if stagnation_counter > 15:
            MUTATION_RATE_EFF = min(0.5, MUTATION_RATE + 0.05)
        else:
            MUTATION_RATE_EFF = MUTATION_RATE

    # --- Results ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("  EVOLUTION COMPLETE")
    print("=" * 80)

    # Sort hall of fame
    hall_of_fame.sort(key=lambda g: g.fitness, reverse=True)
    hall_of_fame = hall_of_fame[:20]  # Keep top 20

    print(f"\n  Best genome ever: {best_ever.genome_id}")
    print(f"  Generation: {best_ever.generation}")
    print(f"  Fitness: {best_ever.fitness:.4f}")
    d = best_ever.details
    print(f"  Win Rate: {d.get('wr', 0):.1f}%")
    print(f"  Profit Factor: {d.get('pf', 0):.2f}")
    print(f"  Total Trades: {d.get('total_trades', 0)}")
    print(f"  Total P/L: {d.get('total_pnl', 0):+.2f}%")
    print(f"  Symbols Profitable: {d.get('symbols_profitable', 0)}/{len(SYMBOLS)}")
    print(f"  Max Consec Losses: {d.get('max_consec_loss', 0)}")

    print(f"\n  Genome Parameters:")
    for k, v in best_ever.genes.items():
        base_v = BASE_GENOME.get(k, "N/A")
        diff = ""
        if isinstance(v, (int, float)) and isinstance(base_v, (int, float)):
            if v != base_v:
                diff = f"  (base: {base_v})"
        print(f"    {k:<24} = {v}{diff}")

    print(f"\n  Per-Symbol Breakdown:")
    for sym, sd in d.get("per_symbol", {}).items():
        print(f"    {sym:<12} trades={sd.get('trades',0):>3} "
              f"WR={sd.get('wr',0):>5.1f}% "
              f"PnL={sd.get('pnl',0):>+7.2f}% "
              f"PF={sd.get('pf',0):>5.2f}")

    # Top 10 hall of fame
    print(f"\n  {'-' * 76}")
    print(f"  HALL OF FAME -- Top 10 Genomes")
    print(f"  {'-' * 76}")
    print(f"  {'#':<3} {'ID':<12} {'Gen':<5} {'Fitness':<9} {'WR%':<7} {'PF':<7} "
          f"{'Trades':<8} {'PnL%':<9} {'Syms':<5}")

    for i, g in enumerate(hall_of_fame[:10]):
        gd = g.details
        print(f"  {i+1:<3} {g.genome_id:<12} {g.generation:<5} {g.fitness:<9.2f} "
              f"{gd.get('wr',0):<7.1f} {gd.get('pf',0):<7.2f} "
              f"{gd.get('total_trades',0):<8} {gd.get('total_pnl',0):<+9.2f} "
              f"{gd.get('symbols_profitable',0)}/{len(SYMBOLS)}")

    # Save results
    results = {
        "config": {
            "population": POPULATION_SIZE,
            "generations": NUM_GENERATIONS,
            "symbols": SYMBOLS,
            "candle_limit": CANDLE_LIMIT,
            "total_backtests": POPULATION_SIZE * NUM_GENERATIONS,
        },
        "best_genome": {
            "id": best_ever.genome_id,
            "generation": best_ever.generation,
            "fitness": best_ever.fitness,
            "genes": best_ever.genes,
            "details": best_ever.details,
        },
        "hall_of_fame": [
            {
                "id": g.genome_id,
                "generation": g.generation,
                "fitness": g.fitness,
                "genes": g.genes,
                "details": g.details,
            }
            for g in hall_of_fame[:20]
        ],
        "base_genome_comparison": {
            k: {"evolved": best_ever.genes[k], "base": BASE_GENOME[k]}
            for k in BASE_GENOME
        },
    }

    output_path = "alpha_engine/data/genome_evolution_results.json"
    try:
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n  Results saved to {output_path}")
    except Exception as e:
        print(f"\n  [WARN] Could not save results: {e}")
        # Try alternative path
        try:
            with open("genome_evolution_results.json", "w") as f:
                json.dump(results, f, indent=2)
            print(f"  Saved to genome_evolution_results.json instead")
        except Exception:
            pass

    return results


if __name__ == "__main__":
    start = time.time()
    results = evolve()
    elapsed = time.time() - start
    print(f"\n  Total time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"  Backtests/sec: {POPULATION_SIZE * NUM_GENERATIONS / elapsed:.0f}")
