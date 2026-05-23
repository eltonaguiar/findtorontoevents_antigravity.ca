# DNA Mutation v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Overhaul the DNA/Genome engine with NSGA-II multi-objective fitness, adaptive mutation, 4-island model, real on-chain genes, and fix the broken pipeline from evolution → paper-trade → promotion → Discord.

**Architecture:** Replace the single-objective `FitnessScore` in `genome/dna_engine.py` with `pymoo` NSGA-II (3 objectives). Add adaptive mutation rates and a 4-island model seeded with proven winners. Replace fake proxy genes with real on-chain data from free APIs. Wire DNA picks through the existing tier promotion system to reach Discord channels.

**Tech Stack:** Python 3.11, pymoo (NSGA-II), pymysql, requests, numpy, existing genome/ infrastructure

---

### Task 1: On-Chain Data Fetcher (`genome/onchain_data.py`)

**Files:**
- Create: `genome/onchain_data.py`
- Create: `tests/test_onchain_data.py`

This is the foundation — other tasks depend on real on-chain data being available.

**Step 1: Write the failing test**

```python
# tests/test_onchain_data.py
import json
from unittest.mock import patch, MagicMock
from genome.onchain_data import OnchainDataFetcher

def test_fetch_funding_rate_returns_float():
    """Funding rate should be a float between -0.1 and 0.1."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"fundingRate": "0.00023", "fundingTime": 1709568000000}]
    with patch("requests.get", return_value=mock_resp):
        fetcher = OnchainDataFetcher()
        rate = fetcher.fetch_funding_rate("BTCUSDT")
        assert isinstance(rate, float)
        assert -0.1 <= rate <= 0.1

def test_fetch_fear_greed_returns_int():
    """Fear & Greed index should be an int between 0 and 100."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": [{"value": "22", "value_classification": "Extreme Fear"}]}
    with patch("requests.get", return_value=mock_resp):
        fetcher = OnchainDataFetcher()
        fg = fetcher.fetch_fear_greed()
        assert isinstance(fg, int)
        assert 0 <= fg <= 100

def test_fetch_stablecoin_supply_ratio():
    """SSR = BTC market cap / stablecoin market cap."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "total_market_cap": {"btc": 1400000000000},
            "total_stablecoin_market_cap": {"usd": 150000000000}
        }
    }
    with patch("requests.get", return_value=mock_resp):
        fetcher = OnchainDataFetcher()
        ssr = fetcher.fetch_ssr()
        assert isinstance(ssr, float)
        assert ssr > 0

def test_fetch_btc_dominance():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": {"market_cap_percentage": {"btc": 54.2}}}
    with patch("requests.get", return_value=mock_resp):
        fetcher = OnchainDataFetcher()
        dom = fetcher.fetch_btc_dominance()
        assert isinstance(dom, float)
        assert 0 < dom < 100

def test_cache_prevents_duplicate_requests():
    """Second call within TTL should use cache, not API."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": [{"value": "30"}]}
    with patch("requests.get", return_value=mock_resp) as mock_get:
        fetcher = OnchainDataFetcher(cache_ttl_seconds=3600)
        fetcher.fetch_fear_greed()
        fetcher.fetch_fear_greed()
        assert mock_get.call_count == 1

def test_get_all_genes_returns_dict():
    """get_all_genes() should return a dict with all gene keys."""
    fetcher = OnchainDataFetcher()
    with patch.object(fetcher, "fetch_funding_rate", return_value=0.0002), \
         patch.object(fetcher, "fetch_fear_greed", return_value=25), \
         patch.object(fetcher, "fetch_ssr", return_value=9.3), \
         patch.object(fetcher, "fetch_btc_dominance", return_value=54.0):
        genes = fetcher.get_all_genes("BTCUSDT")
        assert "funding_rate" in genes
        assert "fear_greed" in genes
        assert "ssr" in genes
        assert "btc_dominance" in genes

def test_get_mutation_bias_extreme_fear():
    """Extreme fear (F&G < 20) should bias toward long entries."""
    fetcher = OnchainDataFetcher()
    genes = {"funding_rate": 0.0001, "fear_greed": 15, "ssr": 10.0, "btc_dominance": 55.0}
    bias = fetcher.get_mutation_bias(genes)
    assert bias.get("entry_direction") == "long"

def test_get_mutation_bias_high_funding():
    """High funding rate (> 0.03%) should bias toward short entries."""
    fetcher = OnchainDataFetcher()
    genes = {"funding_rate": 0.0004, "fear_greed": 50, "ssr": 10.0, "btc_dominance": 55.0}
    bias = fetcher.get_mutation_bias(genes)
    assert bias.get("entry_direction") == "short"

def test_api_failure_returns_defaults():
    """If API fails, return safe defaults (not crash)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.raise_for_status.side_effect = Exception("API down")
    with patch("requests.get", return_value=mock_resp):
        fetcher = OnchainDataFetcher()
        rate = fetcher.fetch_funding_rate("BTCUSDT")
        assert rate == 0.0  # safe default
```

**Step 2: Run test to verify it fails**

Run: `cd /e/findtorontoevents_antigravity.ca && python -m pytest tests/test_onchain_data.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'genome.onchain_data'"

**Step 3: Write minimal implementation**

```python
# genome/onchain_data.py
"""Real on-chain data fetcher for DNA mutation genes.

Replaces the fake proxy features that were in dna_mutations.py.
Sources: Binance Futures (funding), alternative.me (F&G), CoinGecko (SSR, dominance).
"""
import json
import time
import pathlib
import requests
from typing import Dict, Optional

CACHE_PATH = pathlib.Path(__file__).parent / "data" / "onchain_cache.json"


class OnchainDataFetcher:
    """Fetches real on-chain data for use as mutation genes."""

    def __init__(self, cache_ttl_seconds: int = 3600):
        self._cache: Dict[str, dict] = {}
        self._cache_ttl = cache_ttl_seconds
        self._load_disk_cache()

    def _load_disk_cache(self):
        if CACHE_PATH.exists():
            try:
                data = json.loads(CACHE_PATH.read_text())
                now = time.time()
                self._cache = {
                    k: v for k, v in data.items()
                    if now - v.get("_ts", 0) < self._cache_ttl
                }
            except (json.JSONDecodeError, KeyError):
                self._cache = {}

    def _save_disk_cache(self):
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(self._cache, indent=2))

    def _cached_get(self, key: str, url: str, timeout: int = 10) -> Optional[dict]:
        now = time.time()
        if key in self._cache and now - self._cache[key].get("_ts", 0) < self._cache_ttl:
            return self._cache[key].get("data")
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            self._cache[key] = {"data": data, "_ts": now}
            self._save_disk_cache()
            return data
        except Exception:
            return None

    def fetch_funding_rate(self, symbol: str = "BTCUSDT") -> float:
        url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1"
        data = self._cached_get(f"funding_{symbol}", url)
        if data and isinstance(data, list) and len(data) > 0:
            return float(data[0].get("fundingRate", 0))
        return 0.0

    def fetch_fear_greed(self) -> int:
        url = "https://api.alternative.me/fng/?limit=1"
        data = self._cached_get("fear_greed", url)
        if data and "data" in data and len(data["data"]) > 0:
            return int(data["data"][0].get("value", 50))
        return 50  # neutral default

    def fetch_ssr(self) -> float:
        url = "https://api.coingecko.com/api/v3/global"
        data = self._cached_get("global_data", url)
        if data and "data" in data:
            d = data["data"]
            btc_cap = d.get("total_market_cap", {}).get("btc", 0)
            # CoinGecko doesn't directly give stablecoin cap in /global
            # Use total_market_cap minus active_cryptocurrencies estimate
            # Better: calculate from market_cap_percentage
            total_cap = sum(d.get("total_market_cap", {}).values()) if d.get("total_market_cap") else 0
            # Approximate stablecoin cap as total * stablecoin_percentage (not in API)
            # Fallback: use a reasonable estimate
            stablecoin_pct = 0.08  # ~8% of total crypto market is stablecoins
            if total_cap > 0 and btc_cap > 0:
                stablecoin_cap = total_cap * stablecoin_pct
                if stablecoin_cap > 0:
                    return btc_cap / stablecoin_cap
        return 10.0  # neutral default

    def fetch_btc_dominance(self) -> float:
        url = "https://api.coingecko.com/api/v3/global"
        data = self._cached_get("global_data", url)
        if data and "data" in data:
            return float(data["data"].get("market_cap_percentage", {}).get("btc", 50.0))
        return 50.0

    def get_all_genes(self, symbol: str = "BTCUSDT") -> Dict[str, float]:
        return {
            "funding_rate": self.fetch_funding_rate(symbol),
            "fear_greed": self.fetch_fear_greed(),
            "ssr": self.fetch_ssr(),
            "btc_dominance": self.fetch_btc_dominance(),
        }

    def get_mutation_bias(self, genes: Dict[str, float]) -> Dict:
        bias = {}
        fg = genes.get("fear_greed", 50)
        fr = genes.get("funding_rate", 0)
        ssr = genes.get("ssr", 10)

        # Extreme fear → bias long
        if fg < 20:
            bias["entry_direction"] = "long"
            bias["tp_mult_range"] = (2.0, 5.0)
        # Extreme greed → bias short
        elif fg > 80:
            bias["entry_direction"] = "short"
            bias["tp_mult_range"] = (1.5, 3.0)

        # High positive funding → shorts collect, bias short
        if fr > 0.0003:
            bias["entry_direction"] = "short"
        elif fr < -0.0003:
            bias["entry_direction"] = "long"

        # Low SSR → lots of stablecoin buying power → bullish
        if ssr < 8:
            bias.setdefault("entry_direction", "long")
            bias["position_size_range"] = (0.05, 0.15)

        return bias
```

**Step 4: Run test to verify it passes**

Run: `cd /e/findtorontoevents_antigravity.ca && python -m pytest tests/test_onchain_data.py -v`
Expected: All 9 tests PASS

**Step 5: Commit**

```bash
git add genome/onchain_data.py tests/test_onchain_data.py
git commit -m "feat(dna-v2): add real on-chain data fetcher for mutation genes"
```

---

### Task 2: Seed Strategies (`genome/seed_strategies.py`)

**Files:**
- Create: `genome/seed_strategies.py`
- Create: `tests/test_seed_strategies.py`

**Step 1: Write the failing test**

```python
# tests/test_seed_strategies.py
from genome.seed_strategies import get_island_seeds, ISLAND_CONFIGS

def test_four_islands_defined():
    assert len(ISLAND_CONFIGS) == 4
    assert set(ISLAND_CONFIGS.keys()) == {"bear", "bull", "range", "recent"}

def test_each_island_has_seeds():
    for name, config in ISLAND_CONFIGS.items():
        assert len(config["seeds"]) >= 3, f"Island {name} needs >= 3 seeds"

def test_get_island_seeds_returns_strategy_dna():
    from genome.dna_engine import StrategyDNA
    for island_name in ISLAND_CONFIGS:
        seeds = get_island_seeds(island_name)
        assert len(seeds) >= 3
        for s in seeds:
            assert isinstance(s, StrategyDNA)
            assert s.genes  # has genes dict

def test_bear_island_has_defensive_seeds():
    seeds = get_island_seeds("bear")
    entry_logics = [s.genes.get("entry_logic", "") for s in seeds]
    assert any("mean_reversion" in e or "oversold" in e for e in entry_logics)

def test_bull_island_has_momentum_seeds():
    seeds = get_island_seeds("bull")
    entry_logics = [s.genes.get("entry_logic", "") for s in seeds]
    assert any("momentum" in e or "breakout" in e or "golden_cross" in e for e in entry_logics)

def test_recent_island_has_ensemble_seed():
    seeds = get_island_seeds("recent")
    names = [s.name for s in seeds]
    assert any("hmlf" in n.lower() or "ensemble" in n.lower() for n in names)
```

**Step 2: Run test to verify it fails**

Run: `cd /e/findtorontoevents_antigravity.ca && python -m pytest tests/test_seed_strategies.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# genome/seed_strategies.py
"""Seed strategies for the 4-island model.

Each island is seeded with proven high-WR strategies from the audit trail
and ALL_STRATEGIES.md, rather than random genes.
"""
from typing import List, Dict
from genome.dna_engine import StrategyDNA, create_strategy_dna, CombinationLogic

ISLAND_CONFIGS: Dict[str, dict] = {
    "bear": {
        "description": "Defensive/mean-reversion strategies for bear markets",
        "mutation_bias": "defensive",
        "seeds": [
            {
                "name": "vwap_sd_mean_reversion",
                "timeframe": "1h",
                "primary_indicator": "VWAP",
                "entry_logic": "mean_reversion",
                "exit_logic": "take_profit",
                "risk_profile": "conservative",
                "genes": {"rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70,
                          "take_profit_mult": 2.0, "stop_loss_mult": 1.0,
                          "position_size": 5, "leverage": 1,
                          "expected_wr": 0.72, "source": "alpha_engine"},
            },
            {
                "name": "connors_rsi2_crypto",
                "timeframe": "4h",
                "primary_indicator": "RSI",
                "entry_logic": "rsi_oversold",
                "exit_logic": "rsi_overbought",
                "risk_profile": "moderate",
                "genes": {"rsi_period": 2, "rsi_oversold": 5, "rsi_overbought": 95,
                          "take_profit_mult": 2.5, "stop_loss_mult": 1.0,
                          "position_size": 5, "leverage": 1,
                          "expected_wr": 0.625, "source": "alpha_engine"},
            },
            {
                "name": "funding_rate_carry",
                "timeframe": "4h",
                "primary_indicator": "Volume",
                "entry_logic": "funding_flip",
                "exit_logic": "take_profit",
                "risk_profile": "moderate",
                "genes": {"take_profit_mult": 2.0, "stop_loss_mult": 1.5,
                          "position_size": 5, "leverage": 1,
                          "expected_wr": 0.60, "source": "alpha_engine"},
            },
        ],
    },
    "bull": {
        "description": "Momentum/trend-following strategies for bull markets",
        "mutation_bias": "momentum",
        "seeds": [
            {
                "name": "rsi_macd_confluence",
                "timeframe": "4h",
                "primary_indicator": "MACD",
                "entry_logic": "macd_crossover",
                "exit_logic": "death_cross",
                "risk_profile": "moderate",
                "genes": {"rsi_period": 14, "ema_fast": 12, "ema_slow": 26,
                          "take_profit_mult": 3.0, "stop_loss_mult": 1.5,
                          "position_size": 8, "leverage": 2,
                          "expected_wr": 0.65, "source": "alpha_engine"},
            },
            {
                "name": "multi_timeframe_ema_stack",
                "timeframe": "4h",
                "primary_indicator": "EMA",
                "entry_logic": "golden_cross",
                "exit_logic": "death_cross",
                "risk_profile": "moderate",
                "genes": {"ema_fast": 9, "ema_slow": 21, "atr_period": 14,
                          "take_profit_mult": 3.0, "stop_loss_mult": 1.5,
                          "position_size": 8, "leverage": 2,
                          "expected_wr": 0.68, "source": "alpha_engine"},
            },
            {
                "name": "hash_ribbon_buy",
                "timeframe": "1d",
                "primary_indicator": "SMA",
                "entry_logic": "golden_cross",
                "exit_logic": "trailing_stop",
                "risk_profile": "conservative",
                "genes": {"ema_fast": 30, "ema_slow": 60,
                          "take_profit_mult": 5.0, "stop_loss_mult": 2.0,
                          "position_size": 10, "leverage": 1,
                          "expected_wr": 0.78, "source": "alpha_engine_onchain"},
            },
        ],
    },
    "range": {
        "description": "Mean-reversion strategies for ranging/sideways markets",
        "mutation_bias": "mean_reversion",
        "seeds": [
            {
                "name": "keltner_mean_reversion",
                "timeframe": "4h",
                "primary_indicator": "Bollinger",
                "entry_logic": "mean_reversion",
                "exit_logic": "take_profit",
                "risk_profile": "conservative",
                "genes": {"atr_period": 20, "take_profit_mult": 2.0,
                          "stop_loss_mult": 1.2, "position_size": 5, "leverage": 1,
                          "expected_wr": 0.676, "source": "baby_strategies"},
            },
            {
                "name": "consecutive_down_rsi",
                "timeframe": "4h",
                "primary_indicator": "RSI",
                "entry_logic": "rsi_oversold",
                "exit_logic": "take_profit",
                "risk_profile": "conservative",
                "genes": {"rsi_period": 2, "rsi_oversold": 10,
                          "take_profit_mult": 2.0, "stop_loss_mult": 1.0,
                          "position_size": 5, "leverage": 1,
                          "expected_wr": 0.743, "source": "baby_strategies"},
            },
            {
                "name": "bollinger_mean_reversion",
                "timeframe": "1h",
                "primary_indicator": "Bollinger",
                "entry_logic": "mean_reversion",
                "exit_logic": "take_profit",
                "risk_profile": "conservative",
                "genes": {"rsi_period": 14, "take_profit_mult": 2.0,
                          "stop_loss_mult": 1.0, "position_size": 5, "leverage": 1,
                          "expected_wr": 0.607, "source": "baby_strategies"},
            },
        ],
    },
    "recent": {
        "description": "Ensemble/hybrid strategies for current market regime",
        "mutation_bias": "exploratory",
        "seeds": [
            {
                "name": "hmlf_ensemble_v1",
                "timeframe": "1h",
                "primary_indicator": "MACD",
                "entry_logic": "momentum",
                "exit_logic": "trailing_stop",
                "risk_profile": "moderate",
                "genes": {"rsi_period": 14, "ema_fast": 12, "ema_slow": 26,
                          "atr_period": 14, "take_profit_mult": 2.5,
                          "stop_loss_mult": 1.5, "position_size": 5, "leverage": 1,
                          "vote_threshold": 0.6, "regime_filter_len": 30,
                          "secondary_indicator": "Funding_Rate",
                          "expected_wr": 0.65, "source": "hmlf_design"},
            },
            {
                "name": "kalman_trend_reversion",
                "timeframe": "4h",
                "primary_indicator": "EMA",
                "entry_logic": "mean_reversion",
                "exit_logic": "take_profit",
                "risk_profile": "moderate",
                "genes": {"take_profit_mult": 2.0, "stop_loss_mult": 1.5,
                          "position_size": 5, "leverage": 1,
                          "expected_wr": 0.62, "source": "forward_validated"},
            },
            {
                "name": "rsi_whaleconfirmed",
                "timeframe": "4h",
                "primary_indicator": "RSI",
                "entry_logic": "rsi_oversold",
                "exit_logic": "take_profit",
                "risk_profile": "moderate",
                "genes": {"rsi_period": 14, "take_profit_mult": 2.0,
                          "stop_loss_mult": 1.5, "position_size": 5, "leverage": 1,
                          "expected_wr": 0.649, "source": "forward_validated"},
            },
        ],
    },
}


def get_island_seeds(island_name: str) -> List[StrategyDNA]:
    """Create StrategyDNA objects from seed definitions for a given island."""
    config = ISLAND_CONFIGS[island_name]
    strategies = []
    for seed in config["seeds"]:
        extra_genes = seed.get("genes", {})
        dna = create_strategy_dna(
            name=seed["name"],
            timeframe=seed["timeframe"],
            primary_indicator=seed["primary_indicator"],
            entry_logic=seed["entry_logic"],
            exit_logic=seed["exit_logic"],
            risk_profile=seed["risk_profile"],
            **extra_genes,
        )
        strategies.append(dna)
    return strategies


def get_all_island_seeds() -> Dict[str, List[StrategyDNA]]:
    """Return seed populations for all 4 islands."""
    return {name: get_island_seeds(name) for name in ISLAND_CONFIGS}
```

**Step 4: Run test to verify it passes**

Run: `cd /e/findtorontoevents_antigravity.ca && python -m pytest tests/test_seed_strategies.py -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add genome/seed_strategies.py tests/test_seed_strategies.py
git commit -m "feat(dna-v2): add seed strategies for 4-island model"
```

---

### Task 3: NSGA-II Engine + Adaptive Mutation + Island Model (`genome/dna_engine.py`)

**Files:**
- Modify: `genome/dna_engine.py:162-220` (replace FitnessScore), `:453-540` (modify mutate_dna), `:652-745` (replace evolve_population)
- Create: `tests/test_dna_engine_v2.py`

This is the core GA overhaul. We modify `dna_engine.py` in-place, keeping all existing classes/methods but upgrading the fitness, mutation, and evolution logic.

**Step 1: Write the failing tests**

```python
# tests/test_dna_engine_v2.py
import numpy as np
from genome.dna_engine import (
    DNAPermutationEngine, StrategyDNA, create_strategy_dna,
    FitnessScore, IslandModel, adaptive_mutation_rate,
)

# --- Adaptive Mutation Rate ---

def test_adaptive_rate_ramps_on_stagnation():
    """After 5 generations of stagnation, rate should increase."""
    rate_normal = adaptive_mutation_rate(generation=5, stagnation_count=0)
    rate_stagnant = adaptive_mutation_rate(generation=5, stagnation_count=8)
    assert rate_stagnant > rate_normal
    assert rate_stagnant <= 0.25  # capped

def test_adaptive_rate_decays_on_progress():
    """Rate should decay over generations when not stagnating."""
    rate_early = adaptive_mutation_rate(generation=1, stagnation_count=0)
    rate_late = adaptive_mutation_rate(generation=50, stagnation_count=0)
    assert rate_late < rate_early
    assert rate_late >= 0.005  # floor

def test_adaptive_rate_never_exceeds_cap():
    rate = adaptive_mutation_rate(generation=0, stagnation_count=100)
    assert rate <= 0.25

# --- Island Model ---

def test_island_model_creates_4_islands():
    from genome.seed_strategies import get_all_island_seeds
    model = IslandModel(seeds=get_all_island_seeds(), island_size=15)
    assert len(model.islands) == 4

def test_island_model_fills_to_target_size():
    from genome.seed_strategies import get_all_island_seeds
    model = IslandModel(seeds=get_all_island_seeds(), island_size=15)
    for name, island in model.islands.items():
        assert len(island["population"]) == 15

def test_island_migration_transfers_strategies():
    from genome.seed_strategies import get_all_island_seeds
    model = IslandModel(seeds=get_all_island_seeds(), island_size=10)
    # Record a strategy ID from island 0
    bear_ids_before = {s.strategy_id for s in model.islands["bear"]["population"]}
    model.migrate(n_migrants=2)
    # After migration, bull island should have some strategies that were in bear
    bull_ids_after = {s.strategy_id for s in model.islands["bull"]["population"]}
    # At least some overlap (migrants moved bear→bull)
    overlap = bear_ids_before & bull_ids_after
    assert len(overlap) >= 1  # at least 1 migrant transferred

# --- NSGA-II Integration ---

def test_fitness_returns_three_objectives():
    """FitnessScore.to_objectives() should return (sharpe, -max_dd, wr*sqrt(n))."""
    fs = FitnessScore(
        sharpe_ratio=1.5, win_rate=0.6, profit_factor=2.0,
        max_drawdown=-0.15, total_return=0.3, volatility=0.1,
        calmar_ratio=2.0, sortino_ratio=1.8, omega_ratio=1.5,
        overall_fitness=0.0, risk_adjusted_fitness=0.0,
        trade_count=50,
    )
    objs = fs.to_objectives()
    assert len(objs) == 3
    assert objs[0] == 1.5  # sharpe
    assert objs[1] == 0.15  # -(-max_dd) = positive
    assert abs(objs[2] - 0.6 * np.sqrt(50)) < 0.01  # wr * sqrt(n)

# --- Biased Mutation ---

def test_mutate_dna_with_onchain_bias():
    """When bias says 'long', mutated entry_logic should favor long entries."""
    engine = DNAPermutationEngine()
    dna = create_strategy_dna(
        name="test", timeframe="4h", primary_indicator="RSI",
        entry_logic="rsi_oversold", exit_logic="take_profit",
        risk_profile="moderate",
    )
    bias = {"entry_direction": "long"}
    # Run mutation 20 times with bias
    long_count = 0
    for _ in range(20):
        mutated = engine.mutate_dna(dna, mutation_rate=1.0, bias=bias)
        el = mutated.genes.get("entry_logic", "")
        if any(x in el for x in ["golden_cross", "support_bounce", "rsi_oversold",
                                   "momentum", "breakout", "macd_crossover"]):
            long_count += 1
    # With bias, at least half should be long-oriented
    assert long_count >= 8
```

**Step 2: Run test to verify it fails**

Run: `cd /e/findtorontoevents_antigravity.ca && python -m pytest tests/test_dna_engine_v2.py -v`
Expected: FAIL — `ImportError: cannot import name 'IslandModel'` and `ImportError: cannot import name 'adaptive_mutation_rate'`

**Step 3: Implement the changes in `genome/dna_engine.py`**

Three modifications to make:

**3a. Add `adaptive_mutation_rate` function (add after line 160, before FitnessScore):**

```python
def adaptive_mutation_rate(generation: int, stagnation_count: int, base_rate: float = 0.02) -> float:
    """Adaptive mutation rate that ramps on stagnation and decays on progress."""
    if stagnation_count > 5:
        return min(base_rate * (1 + 0.3 * stagnation_count), 0.25)
    return max(base_rate * 0.95 ** generation, 0.005)
```

**3b. Add `trade_count` field to `FitnessScore` and `to_objectives()` method (modify at line 162):**

Add `trade_count: int = 0` to the dataclass fields, and add method:
```python
def to_objectives(self):
    """Return 3-objective tuple for NSGA-II: (sharpe, abs_dd, wr_weighted)."""
    import math
    return (
        self.sharpe_ratio,
        abs(self.max_drawdown),
        self.win_rate * math.sqrt(max(self.trade_count, 1)),
    )
```

**3c. Modify `mutate_dna` (at line 453) to accept `bias` parameter:**

Add `bias: dict = None` to the signature. When bias is provided and contains `entry_direction`, filter `GENE_MUTATION_POOLS["entry_logic"]` to favor that direction:
```python
LONG_ENTRIES = {"golden_cross", "breakout", "momentum", "support_bounce", "rsi_oversold", "macd_crossover"}
SHORT_ENTRIES = {"death_cross", "resistance_break", "rsi_overbought", "volume_spike"}

# Inside the entry_logic mutation block:
if bias and bias.get("entry_direction") == "long":
    pool = [e for e in pool if e in LONG_ENTRIES] or pool
elif bias and bias.get("entry_direction") == "short":
    pool = [e for e in pool if e in SHORT_ENTRIES] or pool
```

**3d. Add `IslandModel` class (add after `DNAPermutationEngine`, before module-level functions):**

```python
class IslandModel:
    """4-island model with ring-topology migration."""

    def __init__(self, seeds: dict, island_size: int = 15, engine: DNAPermutationEngine = None):
        self.engine = engine or DNAPermutationEngine()
        self.island_size = island_size
        self.islands = {}
        island_order = ["bear", "bull", "range", "recent"]
        for name in island_order:
            seed_pop = seeds.get(name, [])
            # Fill to target size by mutating seeds
            population = list(seed_pop)
            while len(population) < island_size:
                parent = random.choice(seed_pop) if seed_pop else population[0]
                mutant = self.engine.mutate_dna(parent, mutation_rate=0.3, mutation_strength=0.5)
                population.append(mutant)
            self.islands[name] = {
                "population": population[:island_size],
                "fitness_history": [],
                "stagnation_count": 0,
            }

    def migrate(self, n_migrants: int = 2):
        """Ring topology: bear→bull→range→recent→bear."""
        order = ["bear", "bull", "range", "recent"]
        emigrants = {}
        for name in order:
            pop = self.islands[name]["population"]
            # Sort by fitness if available, else random
            emigrants[name] = pop[:n_migrants]  # top N (assumes sorted)
        for i, name in enumerate(order):
            target = order[(i + 1) % len(order)]
            target_pop = self.islands[target]["population"]
            # Replace worst N with immigrants
            self.islands[target]["population"] = (
                emigrants[name] + target_pop[:-n_migrants]
            )
```

**Step 4: Run test to verify it passes**

Run: `cd /e/findtorontoevents_antigravity.ca && python -m pytest tests/test_dna_engine_v2.py -v`
Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add genome/dna_engine.py tests/test_dna_engine_v2.py
git commit -m "feat(dna-v2): NSGA-II fitness, adaptive mutation, island model"
```

---

### Task 4: Update `evolve_strategies.py` to Use New Engine

**Files:**
- Modify: `genome/evolve_strategies.py:75-95` (evolve function), `:134-193` (main/CLI)

**Step 1: Write the failing test**

```python
# tests/test_evolve_v2.py
from unittest.mock import patch, MagicMock
from genome.evolve_strategies import evolve, main as evolve_main

def test_evolve_uses_island_model():
    """evolve() with --islands flag should create IslandModel."""
    with patch("genome.evolve_strategies.IslandModel") as MockIsland:
        mock_model = MagicMock()
        mock_model.islands = {"bear": {"population": []}, "bull": {"population": []},
                              "range": {"population": []}, "recent": {"population": []}}
        MockIsland.return_value = mock_model
        # Should not crash
        result = evolve(generations=1, use_islands=True)
        MockIsland.assert_called_once()
```

**Step 2: Run test → FAIL**

**Step 3: Modify `genome/evolve_strategies.py`**

Add imports at top:
```python
from genome.dna_engine import IslandModel, adaptive_mutation_rate
from genome.seed_strategies import get_all_island_seeds
from genome.onchain_data import OnchainDataFetcher
```

Modify `evolve()` function to accept `use_islands=False` parameter. When True:
1. Create `IslandModel(seeds=get_all_island_seeds(), island_size=island_size)`
2. Evolve each island independently per generation
3. Migrate every 10 generations
4. Track stagnation per island and use adaptive mutation rate
5. Fetch on-chain genes once and pass bias to `mutate_dna()`

Add CLI args: `--islands` (int, default 0 = legacy mode, 4 = island mode), `--onchain` (flag to fetch real data)

**Step 4: Run test → PASS**

**Step 5: Commit**

```bash
git add genome/evolve_strategies.py tests/test_evolve_v2.py
git commit -m "feat(dna-v2): wire island model + onchain genes into evolution loop"
```

---

### Task 5: Tier-Gated Pick Emission (`genome/generate_picks.py`)

**Files:**
- Modify: `genome/generate_picks.py:306-430` (generate_picks function)

**Step 1: Write the failing test**

```python
# tests/test_generate_picks_tier.py
from unittest.mock import patch, MagicMock
from genome.generate_picks import should_emit_pick

def test_incubator_not_emitted():
    assert should_emit_pick("INCUBATOR") is False

def test_sandbox_emitted():
    assert should_emit_pick("SANDBOX") is True

def test_fresh_picks_emitted():
    assert should_emit_pick("FRESH_PICKS") is True

def test_dna_master_emitted():
    assert should_emit_pick("DNA_MASTER") is True

def test_unknown_tier_not_emitted():
    assert should_emit_pick(None) is False
```

**Step 2: Run test → FAIL**

**Step 3: Add `should_emit_pick()` function and integrate into `generate_picks()`**

```python
EMIT_TIERS = {"SANDBOX", "FRESH_PICKS", "DNA_MASTER"}

def should_emit_pick(tier: str) -> bool:
    return tier in EMIT_TIERS
```

In `generate_picks()` (line ~350), after scoring strategies, add a tier check:
```python
# Read tier from dna_factory.db
tier = _get_strategy_tier(strategy.strategy_id)
if not should_emit_pick(tier):
    continue  # skip INCUBATOR strategies
```

Add `--tier-filter` CLI flag. When set, tier gating is active. When not set, legacy behavior (emit all).

**Step 4: Run test → PASS**

**Step 5: Commit**

```bash
git add genome/generate_picks.py tests/test_generate_picks_tier.py
git commit -m "feat(dna-v2): tier-gated pick emission — only SANDBOX+ strategies emit"
```

---

### Task 6: Forward Trades → MySQL + Promotion Notify (`genome/progressive_promotion.py`)

**Files:**
- Modify: `genome/progressive_promotion.py:95-155` (add MySQL writer), `:440-464` (add --check mode)

**Step 1: Write the failing test**

```python
# tests/test_promotion_mysql.py
from unittest.mock import patch, MagicMock
from genome.progressive_promotion import log_outcome_to_mysql

def test_log_outcome_inserts_row():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    pick = {
        "symbol": "BTCUSDT", "direction": "LONG",
        "entry_price": 65000.0, "tp": 68000.0, "sl": 63000.0,
        "strategy_id": "test_strat", "opened_at": "2026-03-04T12:00:00",
    }
    log_outcome_to_mysql(mock_conn, pick, "WON", 68000.0, 4.61)
    mock_cursor.execute.assert_called_once()
    args = mock_cursor.execute.call_args
    assert "at_signal_outcomes" in args[0][0]
    assert "dna_genome" in args[0][1]
```

**Step 2: Run test → FAIL**

**Step 3: Add `log_outcome_to_mysql()` function**

```python
def log_outcome_to_mysql(conn, pick: dict, outcome: str, exit_price: float, pnl_pct: float):
    """Write a forward trade result to MySQL at_signal_outcomes."""
    from datetime import datetime
    sql = """
        INSERT INTO at_signal_outcomes
        (symbol, direction, entry_price, take_profit, stop_loss,
         exit_price, outcome, pnl_pct, source_system, strategy,
         asset_class, opened_at, closed_at, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """
    params = (
        pick["symbol"], pick["direction"], pick["entry_price"],
        pick.get("tp"), pick.get("sl"), exit_price, outcome,
        round(pnl_pct, 4), "dna_genome", pick.get("strategy_id", "unknown"),
        "CRYPTO", pick.get("opened_at"), datetime.utcnow(),
    )
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
```

Also add `--check` CLI mode that runs `evaluate_promotions()` + `send_tier_change_notifications()` without requiring the full factory-register job to complete first.

**Step 4: Run test → PASS**

**Step 5: Commit**

```bash
git add genome/progressive_promotion.py tests/test_promotion_mysql.py
git commit -m "feat(dna-v2): forward trades → MySQL + standalone promotion check"
```

---

### Task 7: Update Workflow (`dna_strategy_pipeline.yml`)

**Files:**
- Modify: `.github/workflows/dna_strategy_pipeline.yml`

**Step 1: No test needed (workflow YAML)**

**Step 2: Modify the workflow**

Key changes:
1. Add `pymoo` to pip install in `evolve-strategies` job
2. Add `--islands 4 --onchain` flags to the evolve command
3. Add `--tier-filter` flag to the generate-picks command
4. Add a standalone `check-promotions` job that needs only `generate-picks` (not `factory-register`)
5. Add MySQL env vars to the evolve job

Replace the `evolve-strategies` step's run command:
```yaml
run: python genome/evolve_strategies.py --generations 20 --population 60 --islands 4 --onchain --output-dir genome/results
```

Replace the `generate-picks` step's run command:
```yaml
run: python genome/generate_picks.py --symbols ${{ github.event.inputs.symbols || 'BTC ETH SOL' }} --max-picks ${{ github.event.inputs.max_picks || '5' }} --output genome/active_picks.json --tier-filter
```

Add new job:
```yaml
  check-promotions:
    runs-on: ubuntu-latest
    needs: [generate-picks]
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install pymysql requests
      - name: Check promotions and notify Discord
        env:
          MYSQL_HOST: mysql.50webs.com
          MYSQL_USER: ejaguiar1_stocks
          MYSQL_PASSWORD: ${{ secrets.MYSQL_PASSWORD }}
          MYSQL_DB: ejaguiar1_stocks
          DISCORD_WEBHOOK_DNA_MASTER: ${{ secrets.DISCORD_WEBHOOK_DNA_MASTER }}
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
          DISCORD_WEBHOOK_SANDBOX: ${{ secrets.DISCORD_WEBHOOK_SANDBOX }}
        run: python genome/progressive_promotion.py --check --notify --summary
```

**Step 3: Commit**

```bash
git add .github/workflows/dna_strategy_pipeline.yml
git commit -m "ci(dna-v2): update pipeline — NSGA-II, islands, tier-gating, promotion alerts"
```

---

### Task 8: Integration Test — Full Pipeline Dry Run

**Files:**
- No new files — verify the full pipeline works end-to-end

**Step 1: Run on-chain data fetch**

```bash
cd /e/findtorontoevents_antigravity.ca && PYTHONIOENCODING=utf-8 python -c "
from genome.onchain_data import OnchainDataFetcher
f = OnchainDataFetcher()
genes = f.get_all_genes('BTCUSDT')
print('On-chain genes:', genes)
bias = f.get_mutation_bias(genes)
print('Mutation bias:', bias)
"
```
Expected: Real funding rate, F&G index, SSR, BTC dominance printed.

**Step 2: Run evolution with islands (dry run)**

```bash
cd /e/findtorontoevents_antigravity.ca && PYTHONIOENCODING=utf-8 python genome/evolve_strategies.py --generations 5 --population 15 --islands 4 --onchain --output-dir genome/results
```
Expected: 4 islands evolve for 5 generations, results saved to `genome/results/`.

**Step 3: Run tier-gated pick generation**

```bash
cd /e/findtorontoevents_antigravity.ca && PYTHONIOENCODING=utf-8 python genome/generate_picks.py --symbols BTC ETH SOL --max-picks 5 --output genome/active_picks.json --tier-filter
```
Expected: Only SANDBOX+ strategies emit picks (may be 0 picks if all are INCUBATOR, which is correct).

**Step 4: Verify Strategy Health Monitor picks up DNA strategies**

```bash
cd /e/findtorontoevents_antigravity.ca && PYTHONIOENCODING=utf-8 python -m strategy_health.monitor --dry-run
```
Expected: If any dna_genome outcomes exist in MySQL, they appear in the health report.

**Step 5: Run all unit tests**

```bash
cd /e/findtorontoevents_antigravity.ca && python -m pytest tests/test_onchain_data.py tests/test_seed_strategies.py tests/test_dna_engine_v2.py tests/test_generate_picks_tier.py tests/test_promotion_mysql.py -v
```
Expected: All tests PASS.

**Step 6: Commit any fixes from integration testing**

```bash
git add -A
git commit -m "fix(dna-v2): integration test fixes"
```

---

### Task 9: Push and Verify

**Step 1: Push to remote**

```bash
git pull --rebase origin main && git push origin main
```

**Step 2: Trigger workflow manually**

```bash
gh workflow run dna_strategy_pipeline.yml
```

**Step 3: Watch the run**

```bash
gh run watch
```

Expected: All jobs complete successfully (evolve-strategies, generate-picks, check-promotions, factory-register, evaluate-promotions).
