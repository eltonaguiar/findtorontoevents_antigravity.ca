# Paper Trading Portfolio System — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a 10-strategy paper trading system using free crypto APIs, tracked across 9 portfolios, posting results to Discord #paper-trade every 4 hours.

**Architecture:** Modular strategy engine → portfolio manager → Discord reporter. Each strategy fetches from free APIs (CoinGecko, Binance, DeFiLlama, Alternative.me, Kraken, CryptoQuant), produces picks in standard format, portfolio manager allocates to 9 portfolios (6 by type + 3 by conviction tier), Discord reporter posts embeds via webhook.

**Tech Stack:** Python 3.11, requests, sqlite3, pydantic (validation), matplotlib (optional heatmap), GitHub Actions

---

### Task 1: Scaffold directory structure and helpers

**Files:**
- Create: `paper_trading/__init__.py`
- Create: `paper_trading/__main__.py`
- Create: `paper_trading/helpers.py`
- Create: `paper_trading/models.py`
- Create: `paper_trading/strategies/__init__.py`
- Create: `paper_trading/data/.gitkeep`

**Step 1: Create directories**

```bash
mkdir -p paper_trading/strategies paper_trading/data
```

**Step 2: Write `paper_trading/__init__.py`**

```python
"""Paper Trading Portfolio System — 10 free-API strategies, 9 portfolios."""
```

**Step 3: Write `paper_trading/__main__.py`**

```python
"""Entry point: python -m paper_trading"""
from paper_trading.scanner import main
main()
```

**Step 4: Write `paper_trading/models.py` — Pydantic schemas**

```python
"""Data models for picks, portfolios, and performance metrics."""
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Literal
from datetime import datetime, timezone
import json

@dataclass
class NormalizedPick:
    symbol: str                                     # e.g. "BTCUSDT"
    direction: str                                  # "LONG" or "SHORT"
    entry_price: float
    tp: float
    sl: float
    strategy: str                                   # e.g. "defi_tvl_momentum"
    strategy_name: str                              # e.g. "DeFi TVL Momentum"
    category: str                                   # "crypto", "defi", "derivatives"
    confidence: float = 0.5                         # 0-1
    reason: str = ""
    raw_signal: Optional[dict] = None
    risk_reward: float = 0.0
    picked_at: str = ""
    expires_at: Optional[str] = None
    id: str = ""

    def __post_init__(self):
        if not self.picked_at:
            self.picked_at = datetime.now(timezone.utc).isoformat()
        if not self.id:
            date_part = self.picked_at[:10]
            self.id = f"{self.strategy}::{self.symbol}::{date_part}"
        if self.risk_reward == 0 and self.entry_price and self.sl:
            dist_tp = abs(self.tp - self.entry_price)
            dist_sl = abs(self.entry_price - self.sl)
            self.risk_reward = round(dist_tp / dist_sl, 2) if dist_sl > 0 else 0

    def to_dict(self) -> dict:
        d = asdict(self)
        # Remove None values for cleaner JSON
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class Position:
    pick_id: str
    symbol: str
    direction: str
    entry_price: float
    current_price: float
    tp: float
    sl: float
    strategy: str
    strategy_name: str
    portfolio_type: str           # "technical", "onchain", etc.
    conviction_tier: str          # "high", "medium", "speculative"
    position_size_usd: float
    shares: float
    entry_date: str
    status: str = "ACTIVE"        # ACTIVE, TP_HIT, SL_HIT, EXPIRED, MANUAL_CLOSE
    exit_price: Optional[float] = None
    exit_date: Optional[str] = None
    pnl_pct: float = 0.0
    pnl_usd: float = 0.0
    mfe: float = 0.0              # max favorable excursion %
    mae: float = 0.0              # max adverse excursion %
    confidence: float = 0.5
    reason: str = ""


@dataclass
class Portfolio:
    name: str
    portfolio_type: str           # "strategy_type" or "conviction_tier"
    starting_capital: float = 10000.0
    cash: float = 10000.0
    equity: float = 10000.0
    positions: List[dict] = field(default_factory=list)
    closed_trades: List[dict] = field(default_factory=list)
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    peak_equity: float = 10000.0
    max_drawdown_pct: float = 0.0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @property
    def win_rate(self) -> float:
        return (self.wins / self.total_trades * 100) if self.total_trades > 0 else 0.0

    @property
    def pnl_pct(self) -> float:
        return ((self.equity - self.starting_capital) / self.starting_capital) * 100

    def to_dict(self) -> dict:
        d = asdict(self)
        d["win_rate"] = self.win_rate
        d["pnl_pct"] = round(self.pnl_pct, 2)
        return d
```

**Step 5: Write `paper_trading/helpers.py` — Rate-limit, cache, fallback**

```python
"""Rate-limiting, caching, and fallback helpers for free API access."""
import json
import logging
import os
import pathlib
import time
import requests
from functools import wraps

logger = logging.getLogger("paper_trading")

CACHE_DIR = pathlib.Path(__file__).parent / "data" / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Track last call time per source
_last_call: dict = {}


def rate_limited(source: str, min_interval: float = 1.0):
    """Decorator: enforce minimum interval between calls to same source."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = source
            elapsed = time.time() - _last_call.get(key, 0)
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            try:
                result = func(*args, **kwargs)
                _last_call[key] = time.time()
                return result
            except Exception as e:
                _last_call[key] = time.time()
                raise
        return wrapper
    return decorator


def cached(ttl_seconds: int = 900):
    """Decorator: cache function result to disk with TTL."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function name + args
            cache_key = f"{func.__name__}_{'_'.join(str(a) for a in args)}"
            cache_key = cache_key.replace("/", "_").replace(":", "_")[:200]
            cache_file = CACHE_DIR / f"{cache_key}.json"

            if cache_file.is_file():
                try:
                    data = json.loads(cache_file.read_text())
                    if time.time() - data.get("_ts", 0) < ttl_seconds:
                        return data["payload"]
                except Exception:
                    pass

            payload = func(*args, **kwargs)
            try:
                cache_file.write_text(json.dumps({"_ts": time.time(), "payload": payload}))
            except Exception:
                pass
            return payload
        return wrapper
    return decorator


def fetch_json(url: str, params: dict = None, headers: dict = None,
               timeout: int = 15, retries: int = 3) -> dict:
    """Fetch JSON with retry and exponential backoff."""
    hdrs = {"User-Agent": "PaperTrading/1.0"}
    if headers:
        hdrs.update(headers)
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=hdrs, timeout=timeout)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 2 ** (attempt + 1)))
                logger.warning(f"Rate limited on {url}, waiting {wait}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            logger.error(f"Failed to fetch {url}: {e}")
            raise
    return {}


def fetch_with_fallback(primary_fn, fallback_fn, *args, **kwargs):
    """Try primary function, fall back to secondary on failure."""
    try:
        return primary_fn(*args, **kwargs)
    except Exception as e:
        logger.warning(f"{primary_fn.__name__} failed ({e}), trying fallback")
        return fallback_fn(*args, **kwargs)
```

**Step 6: Create `.gitkeep` in data dir**

```bash
touch paper_trading/data/.gitkeep
```

**Step 7: Commit**

```bash
git add paper_trading/
git commit -m "feat(paper-trading): scaffold directory, models, and helpers"
```

---

### Task 2: Base strategy class and first 3 strategies

**Files:**
- Create: `paper_trading/strategies/base_strategy.py`
- Create: `paper_trading/strategies/defi_tvl_momentum.py`
- Create: `paper_trading/strategies/fear_greed_contrarian.py`
- Create: `paper_trading/strategies/funding_rate_carry.py`

**Step 1: Write `base_strategy.py`**

```python
"""Abstract base class for all paper trading strategies."""
from abc import ABC, abstractmethod
from typing import List
from paper_trading.models import NormalizedPick
import logging

logger = logging.getLogger("paper_trading")


class BaseStrategy(ABC):
    name: str = "unnamed"
    display_name: str = "Unnamed Strategy"
    source: str = "unknown"
    category: str = "crypto"
    portfolio_type: str = "technical"   # which strategy-type portfolio
    symbols: List[str] = []             # symbols this strategy covers

    @abstractmethod
    def fetch_data(self) -> dict:
        """Fetch raw data from API. Returns raw payload for audit trail."""
        ...

    @abstractmethod
    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        """Analyze data and return list of normalized picks."""
        ...

    def run(self) -> List[NormalizedPick]:
        """Execute strategy: fetch + generate."""
        try:
            logger.info(f"Running strategy: {self.display_name}")
            data = self.fetch_data()
            picks = self.generate_picks(data)
            logger.info(f"  → {len(picks)} picks from {self.display_name}")
            return picks
        except Exception as e:
            logger.error(f"Strategy {self.name} failed: {e}")
            return []
```

**Step 2: Write `defi_tvl_momentum.py`** — DeFiLlama (free, no key)

```python
"""DeFi TVL Momentum — buy tokens whose protocol TVL is growing >10%/week."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited, cached

# Map DeFi protocols to their tradeable token on Binance
PROTOCOL_TOKEN_MAP = {
    "Lido": "LDOUSDT",
    "AAVE": "AAVEUSDT",
    "Uniswap": "UNIUSDT",
    "MakerDAO": "MKRUSDT",
    "Curve DEX": "CRVUSDT",
    "Compound": "COMPUSDT",
    "Synthetix": "SNXUSDT",
    "Balancer": "BALUSDT",
    "SushiSwap": "SUSHIUSDT",
    "PancakeSwap": "CAKEUSDT",
    "Convex Finance": "CVXUSDT",
    "Yearn Finance": "YFIUSDT",
    "1inch": "1INCHUSDT",
    "dYdX": "DYDXUSDT",
    "GMX": "GMXUSDT",
    "Pendle": "PENDLEUSDT",
    "Ethena": "ENAUSDT",
    "Jupiter": "JUPUSDT",
    "Raydium": "RAYUSDT",
    "Ondo Finance": "ONDOUSDT",
}

TP_PCT = 0.08      # 8% take profit
SL_PCT = 0.04      # 4% stop loss


class DefiTvlMomentum(BaseStrategy):
    name = "defi_tvl_momentum"
    display_name = "DeFi TVL Momentum"
    source = "DeFiLlama"
    category = "defi"
    portfolio_type = "onchain"

    @rate_limited("defillama", 1.0)
    @cached(ttl_seconds=3600)  # 1h cache — TVL doesn't change fast
    def fetch_data(self) -> dict:
        protocols = fetch_json("https://api.llama.fi/protocols")
        return {"protocols": protocols}

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        protocols = data.get("protocols", [])

        for p in protocols:
            name = p.get("name", "")
            token = PROTOCOL_TOKEN_MAP.get(name)
            if not token:
                continue

            tvl_now = p.get("tvl", 0) or 0
            tvl_1w = p.get("change_7d", 0) or 0  # percent change 7d

            if tvl_now < 50_000_000:  # skip small protocols < $50M TVL
                continue

            if tvl_1w > 10:  # TVL growing >10% weekly → bullish
                # Get current price from Binance ticker
                try:
                    ticker = fetch_json(
                        "https://api.binance.com/api/v3/ticker/price",
                        params={"symbol": token}
                    )
                    price = float(ticker.get("price", 0))
                except Exception:
                    continue

                if price <= 0:
                    continue

                confidence = min(0.9, 0.5 + (tvl_1w - 10) / 100)

                picks.append(NormalizedPick(
                    symbol=token,
                    direction="LONG",
                    entry_price=price,
                    tp=round(price * (1 + TP_PCT), 6),
                    sl=round(price * (1 - SL_PCT), 6),
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(confidence, 3),
                    reason=f"TVL {name}: ${tvl_now/1e6:.0f}M (+{tvl_1w:.1f}% 7d)",
                    raw_signal={"protocol": name, "tvl": tvl_now, "change_7d": tvl_1w},
                ))

        return picks[:5]  # max 5 picks per strategy
```

**Step 3: Write `fear_greed_contrarian.py`** — Alternative.me (free, no key)

```python
"""Fear & Greed Contrarian — buy when extreme fear, sell when extreme greed."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited, cached

# Top crypto tokens to trade on extreme sentiment
SENTIMENT_TOKENS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "MATICUSDT",
]

TP_PCT = 0.06      # 6% TP
SL_PCT = 0.03      # 3% SL


class FearGreedContrarian(BaseStrategy):
    name = "fear_greed_contrarian"
    display_name = "Fear & Greed Contrarian"
    source = "Alternative.me"
    category = "crypto"
    portfolio_type = "sentiment"

    @rate_limited("alternative_me", 2.0)
    @cached(ttl_seconds=3600)  # 1h cache — index updates daily
    def fetch_data(self) -> dict:
        data = fetch_json("https://api.alternative.me/fng/?limit=7")
        return data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        fng_data = data.get("data", [])
        if not fng_data:
            return picks

        current_value = int(fng_data[0].get("value", 50))
        classification = fng_data[0].get("value_classification", "Neutral")

        # Only trade on extremes
        if 20 < current_value < 80:
            return picks

        direction = "LONG" if current_value <= 20 else "SHORT"
        confidence = min(0.9, 0.5 + abs(current_value - 50) / 100)

        # Fetch prices for top tokens
        for symbol in SENTIMENT_TOKENS[:5]:  # limit to 5
            try:
                ticker = fetch_json(
                    "https://api.binance.com/api/v3/ticker/price",
                    params={"symbol": symbol}
                )
                price = float(ticker.get("price", 0))
            except Exception:
                continue

            if price <= 0:
                continue

            if direction == "LONG":
                tp = round(price * (1 + TP_PCT), 6)
                sl = round(price * (1 - SL_PCT), 6)
            else:
                tp = round(price * (1 - TP_PCT), 6)
                sl = round(price * (1 + SL_PCT), 6)

            picks.append(NormalizedPick(
                symbol=symbol,
                direction=direction,
                entry_price=price,
                tp=tp,
                sl=sl,
                strategy=self.name,
                strategy_name=self.display_name,
                category=self.category,
                confidence=round(confidence, 3),
                reason=f"F&G Index: {current_value} ({classification}) → contrarian {direction}",
                raw_signal={"fng_value": current_value, "classification": classification},
            ))

        return picks
```

**Step 4: Write `funding_rate_carry.py`** — Binance Futures (free, no key)

```python
"""Funding Rate Carry — short overheated perps (funding > 0.05%), long underfunded."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited, cached

HIGH_FUNDING_THRESHOLD = 0.0005   # 0.05% per 8h = very high
LOW_FUNDING_THRESHOLD = -0.0003   # -0.03% per 8h = underfunded
TP_PCT = 0.04
SL_PCT = 0.025


class FundingRateCarry(BaseStrategy):
    name = "funding_rate_carry"
    display_name = "Funding Rate Carry"
    source = "Binance Futures"
    category = "derivatives"
    portfolio_type = "derivatives"

    @rate_limited("binance_futures", 0.5)
    @cached(ttl_seconds=1800)  # 30 min cache — funding updates every 8h
    def fetch_data(self) -> dict:
        data = fetch_json("https://fapi.binance.com/fapi/v1/premiumIndex")
        return {"funding_rates": data}

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        rates = data.get("funding_rates", [])

        # Filter for USDT pairs with meaningful volume
        for item in rates:
            symbol = item.get("symbol", "")
            if not symbol.endswith("USDT"):
                continue

            funding = float(item.get("lastFundingRate", 0))
            mark_price = float(item.get("markPrice", 0))

            if mark_price <= 0:
                continue

            if funding > HIGH_FUNDING_THRESHOLD:
                # Overleveraged longs → short
                direction = "SHORT"
                tp = round(mark_price * (1 - TP_PCT), 6)
                sl = round(mark_price * (1 + SL_PCT), 6)
                confidence = min(0.85, 0.5 + (funding - HIGH_FUNDING_THRESHOLD) * 500)
                reason = f"High funding {funding*100:.4f}% → short carry"
            elif funding < LOW_FUNDING_THRESHOLD:
                # Overleveraged shorts → long
                direction = "LONG"
                tp = round(mark_price * (1 + TP_PCT), 6)
                sl = round(mark_price * (1 - SL_PCT), 6)
                confidence = min(0.85, 0.5 + abs(funding - LOW_FUNDING_THRESHOLD) * 500)
                reason = f"Negative funding {funding*100:.4f}% → long carry"
            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol,
                direction=direction,
                entry_price=mark_price,
                tp=tp,
                sl=sl,
                strategy=self.name,
                strategy_name=self.display_name,
                category=self.category,
                confidence=round(confidence, 3),
                reason=reason,
                raw_signal={"funding_rate": funding, "mark_price": mark_price},
            ))

        # Sort by confidence desc, return top 5
        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
```

**Step 5: Commit**

```bash
git add paper_trading/strategies/
git commit -m "feat(paper-trading): base strategy + DeFi TVL, F&G contrarian, funding rate carry"
```

---

### Task 3: Remaining 7 strategies

**Files:**
- Create: `paper_trading/strategies/volume_breakout.py`
- Create: `paper_trading/strategies/stablecoin_supply.py`
- Create: `paper_trading/strategies/exchange_netflow.py`
- Create: `paper_trading/strategies/rsi2_mean_reversion.py`
- Create: `paper_trading/strategies/whale_accumulation.py`
- Create: `paper_trading/strategies/cross_exchange_spread.py`
- Create: `paper_trading/strategies/btc_dominance_rotation.py`

**Step 1: Write `volume_breakout.py`** — CoinGecko + Binance (free)

```python
"""Volume Breakout — buy on 3x avg volume + price above 20d SMA."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited, cached

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT",
           "DOGEUSDT", "SHIBUSDT", "NEARUSDT", "APTUSDT", "SUIUSDT"]

TP_PCT = 0.07
SL_PCT = 0.035


class VolumeBreakout(BaseStrategy):
    name = "volume_breakout"
    display_name = "Volume Breakout"
    source = "Binance"
    category = "crypto"
    portfolio_type = "technical"

    def fetch_data(self) -> dict:
        """Fetch 30-day klines for each symbol."""
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self._fetch_klines(sym)
                all_data[sym] = klines
            except Exception:
                continue
        return all_data

    @rate_limited("binance", 0.2)
    def _fetch_klines(self, symbol: str) -> list:
        return fetch_json(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": symbol, "interval": "1d", "limit": 30}
        )

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 21:
                continue

            closes = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]
            current_price = closes[-1]
            current_vol = volumes[-1]

            # 20-day SMA
            sma_20 = sum(closes[-20:]) / 20
            # Average volume (exclude last day)
            avg_vol = sum(volumes[:-1]) / len(volumes[:-1])

            # Signal: price above SMA + 3x volume
            if current_price > sma_20 and current_vol > avg_vol * 3:
                vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0
                confidence = min(0.9, 0.5 + (vol_ratio - 3) / 20)

                picks.append(NormalizedPick(
                    symbol=symbol,
                    direction="LONG",
                    entry_price=current_price,
                    tp=round(current_price * (1 + TP_PCT), 6),
                    sl=round(current_price * (1 - SL_PCT), 6),
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(confidence, 3),
                    reason=f"Volume {vol_ratio:.1f}x avg, price above 20d SMA (${sma_20:.2f})",
                    raw_signal={"vol_ratio": vol_ratio, "sma_20": sma_20, "price": current_price},
                ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
```

**Step 2: Write `stablecoin_supply.py`** — CoinGecko (free)

```python
"""Stablecoin Supply Ratio — SSR declining = buying power building."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited, cached

BUY_TOKENS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
TP_PCT = 0.06
SL_PCT = 0.03


class StablecoinSupply(BaseStrategy):
    name = "stablecoin_supply"
    display_name = "Stablecoin Supply Ratio"
    source = "CoinGecko"
    category = "crypto"
    portfolio_type = "onchain"

    @rate_limited("coingecko", 1.5)
    @cached(ttl_seconds=7200)  # 2h cache
    def fetch_data(self) -> dict:
        btc = fetch_json("https://api.coingecko.com/api/v3/coins/bitcoin",
                         params={"localization": "false", "tickers": "false",
                                 "community_data": "false", "developer_data": "false"})
        usdt = fetch_json("https://api.coingecko.com/api/v3/coins/tether",
                          params={"localization": "false", "tickers": "false",
                                  "community_data": "false", "developer_data": "false"})
        usdc = fetch_json("https://api.coingecko.com/api/v3/coins/usd-coin",
                          params={"localization": "false", "tickers": "false",
                                  "community_data": "false", "developer_data": "false"})
        return {"btc": btc, "usdt": usdt, "usdc": usdc}

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        try:
            btc_mcap = data["btc"]["market_data"]["market_cap"]["usd"]
            usdt_mcap = data["usdt"]["market_data"]["market_cap"]["usd"]
            usdc_mcap = data["usdc"]["market_data"]["market_cap"]["usd"]
            stable_mcap = usdt_mcap + usdc_mcap

            # SSR = BTC market cap / stablecoin market cap
            ssr = btc_mcap / stable_mcap if stable_mcap > 0 else 999

            # Low SSR (<5) = lots of stablecoin buying power relative to BTC → bullish
            if ssr < 5:
                confidence = min(0.85, 0.5 + (5 - ssr) / 10)
                for symbol in BUY_TOKENS:
                    try:
                        ticker = fetch_json(
                            "https://api.binance.com/api/v3/ticker/price",
                            params={"symbol": symbol}
                        )
                        price = float(ticker.get("price", 0))
                    except Exception:
                        continue

                    if price <= 0:
                        continue

                    picks.append(NormalizedPick(
                        symbol=symbol,
                        direction="LONG",
                        entry_price=price,
                        tp=round(price * (1 + TP_PCT), 6),
                        sl=round(price * (1 - SL_PCT), 6),
                        strategy=self.name,
                        strategy_name=self.display_name,
                        category=self.category,
                        confidence=round(confidence, 3),
                        reason=f"SSR={ssr:.2f} (low) — stablecoin buying power building",
                        raw_signal={"ssr": ssr, "btc_mcap": btc_mcap, "stable_mcap": stable_mcap},
                    ))
        except (KeyError, TypeError):
            pass

        return picks
```

**Step 3: Write `exchange_netflow.py`** — CryptoQuant (key required, with fallback)

```python
"""Exchange Netflow — large outflows = accumulation signal."""
from typing import List
import os
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited, cached

CRYPTOQUANT_KEY = os.environ.get("CRYPTOQUANT_API_KEY", "")
TP_PCT = 0.06
SL_PCT = 0.03


class ExchangeNetflow(BaseStrategy):
    name = "exchange_netflow"
    display_name = "Exchange Netflow"
    source = "CryptoQuant"
    category = "crypto"
    portfolio_type = "onchain"

    @rate_limited("cryptoquant", 3.0)
    @cached(ttl_seconds=7200)
    def fetch_data(self) -> dict:
        if not CRYPTOQUANT_KEY:
            # Fallback: use Binance volume as a proxy for flow
            return self._fallback_binance_flow()
        headers = {"Authorization": f"Bearer {CRYPTOQUANT_KEY}"}
        try:
            data = fetch_json(
                "https://api.cryptoquant.com/v1/btc/exchange-flows/netflow",
                params={"window": "day", "limit": 7},
                headers=headers
            )
            return {"source": "cryptoquant", "data": data}
        except Exception:
            return self._fallback_binance_flow()

    def _fallback_binance_flow(self) -> dict:
        """Use volume change as a rough proxy for netflow."""
        klines = fetch_json(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": "BTCUSDT", "interval": "1d", "limit": 7}
        )
        return {"source": "binance_proxy", "klines": klines}

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        source = data.get("source", "")

        if source == "cryptoquant":
            result = data.get("data", {}).get("result", {}).get("data", [])
            if len(result) >= 2:
                latest = float(result[-1].get("value", 0))
                prev = float(result[-2].get("value", 0))
                # Negative netflow = outflow = accumulation
                if latest < -1000 and latest < prev:
                    self._add_btc_pick(picks, confidence=0.7,
                                       reason=f"BTC exchange outflow: {latest:.0f} BTC (accumulation)")
        elif source == "binance_proxy":
            klines = data.get("klines", [])
            if len(klines) >= 7:
                volumes = [float(k[5]) for k in klines]
                prices = [float(k[4]) for k in klines]
                # Rising volume + falling price = accumulation proxy
                vol_trend = volumes[-1] / (sum(volumes[:-1]) / max(len(volumes) - 1, 1))
                price_change = (prices[-1] - prices[-3]) / prices[-3] if prices[-3] else 0
                if vol_trend > 1.5 and price_change < -0.02:
                    self._add_btc_pick(picks, confidence=0.6,
                                       reason=f"Volume proxy: {vol_trend:.1f}x avg + price dip {price_change*100:.1f}%")

        return picks

    def _add_btc_pick(self, picks: list, confidence: float, reason: str):
        try:
            ticker = fetch_json("https://api.binance.com/api/v3/ticker/price",
                                params={"symbol": "BTCUSDT"})
            price = float(ticker.get("price", 0))
            if price > 0:
                picks.append(NormalizedPick(
                    symbol="BTCUSDT",
                    direction="LONG",
                    entry_price=price,
                    tp=round(price * (1 + TP_PCT), 6),
                    sl=round(price * (1 - SL_PCT), 6),
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=confidence,
                    reason=reason,
                ))
        except Exception:
            pass
```

**Step 4: Write `rsi2_mean_reversion.py`** — Binance Klines (free)

```python
"""RSI-2 Mean Reversion — Connors RSI-2 oversold/overbought on crypto."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT"]

RSI_OVERSOLD = 10     # RSI-2 < 10 → buy
RSI_OVERBOUGHT = 90   # RSI-2 > 90 → sell
TP_PCT = 0.04
SL_PCT = 0.02


class Rsi2MeanReversion(BaseStrategy):
    name = "rsi2_mean_reversion"
    display_name = "RSI-2 Mean Reversion"
    source = "Binance"
    category = "crypto"
    portfolio_type = "technical"

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self._fetch(sym)
                all_data[sym] = klines
            except Exception:
                continue
        return all_data

    @rate_limited("binance", 0.2)
    def _fetch(self, symbol: str) -> list:
        return fetch_json(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": symbol, "interval": "1d", "limit": 10}
        )

    def _rsi(self, closes: list, period: int = 2) -> float:
        """Calculate RSI for given period."""
        if len(closes) < period + 1:
            return 50.0
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]
        avg_gain = sum(gains[-period:]) / period if gains else 0.001
        avg_loss = sum(losses[-period:]) / period if losses else 0.001
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        return 100 - (100 / (1 + rs))

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 5:
                continue

            closes = [float(k[4]) for k in klines]
            price = closes[-1]
            rsi = self._rsi(closes, period=2)

            if rsi < RSI_OVERSOLD:
                direction = "LONG"
                tp = round(price * (1 + TP_PCT), 6)
                sl = round(price * (1 - SL_PCT), 6)
                confidence = min(0.9, 0.5 + (RSI_OVERSOLD - rsi) / 20)
                reason = f"RSI(2)={rsi:.1f} oversold → mean reversion LONG"
            elif rsi > RSI_OVERBOUGHT:
                direction = "SHORT"
                tp = round(price * (1 - TP_PCT), 6)
                sl = round(price * (1 + SL_PCT), 6)
                confidence = min(0.9, 0.5 + (rsi - RSI_OVERBOUGHT) / 20)
                reason = f"RSI(2)={rsi:.1f} overbought → mean reversion SHORT"
            else:
                continue

            picks.append(NormalizedPick(
                symbol=symbol,
                direction=direction,
                entry_price=price,
                tp=tp, sl=sl,
                strategy=self.name,
                strategy_name=self.display_name,
                category=self.category,
                confidence=round(confidence, 3),
                reason=reason,
                raw_signal={"rsi2": rsi, "price": price},
            ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:5]
```

**Step 5: Write `whale_accumulation.py`**

```python
"""Whale Accumulation — unusual volume spike + price dip = smart money buying."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "NEARUSDT"]

TP_PCT = 0.06
SL_PCT = 0.03


class WhaleAccumulation(BaseStrategy):
    name = "whale_accumulation"
    display_name = "Whale Accumulation"
    source = "Binance"
    category = "crypto"
    portfolio_type = "smart_money"

    def fetch_data(self) -> dict:
        all_data = {}
        for sym in SYMBOLS:
            try:
                klines = self._fetch(sym)
                all_data[sym] = klines
            except Exception:
                continue
        return all_data

    @rate_limited("binance", 0.2)
    def _fetch(self, symbol: str) -> list:
        return fetch_json(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": symbol, "interval": "1d", "limit": 30}
        )

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        for symbol, klines in data.items():
            if len(klines) < 20:
                continue

            closes = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]
            price = closes[-1]
            current_vol = volumes[-1]
            avg_vol = sum(volumes[-20:-1]) / 19

            # Price dip: below 10-day SMA
            sma_10 = sum(closes[-10:]) / 10
            price_below_sma = price < sma_10

            # Volume spike: 5x+ average
            vol_ratio = current_vol / avg_vol if avg_vol > 0 else 0

            if vol_ratio >= 5 and price_below_sma:
                confidence = min(0.9, 0.55 + (vol_ratio - 5) / 30)
                picks.append(NormalizedPick(
                    symbol=symbol,
                    direction="LONG",
                    entry_price=price,
                    tp=round(price * (1 + TP_PCT), 6),
                    sl=round(price * (1 - SL_PCT), 6),
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(confidence, 3),
                    reason=f"Vol {vol_ratio:.1f}x avg + price below 10d SMA — whale accumulation",
                    raw_signal={"vol_ratio": vol_ratio, "sma_10": sma_10, "price": price},
                ))

        picks.sort(key=lambda p: p.confidence, reverse=True)
        return picks[:3]
```

**Step 6: Write `cross_exchange_spread.py`**

```python
"""Cross-Exchange Spread — price divergence between Binance and Kraken."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited

# Pairs available on both Binance and Kraken
PAIRS = {
    "BTCUSDT": "XXBTZUSD",
    "ETHUSDT": "XETHZUSD",
    "SOLUSDT": "SOLUSD",
    "ADAUSDT": "ADAUSD",
    "DOTUSDT": "DOTUSD",
    "LINKUSDT": "LINKUSD",
    "XRPUSDT": "XXRPZUSD",
    "AVAXUSDT": "AVAXUSD",
}

SPREAD_THRESHOLD = 0.003  # 0.3% divergence triggers
TP_PCT = 0.025
SL_PCT = 0.015


class CrossExchangeSpread(BaseStrategy):
    name = "cross_exchange_spread"
    display_name = "Cross-Exchange Spread"
    source = "Binance + Kraken"
    category = "crypto"
    portfolio_type = "smart_money"

    def fetch_data(self) -> dict:
        binance_prices = {}
        kraken_prices = {}

        for binance_sym in PAIRS:
            try:
                t = self._fetch_binance(binance_sym)
                binance_prices[binance_sym] = float(t.get("price", 0))
            except Exception:
                continue

        try:
            kraken_data = self._fetch_kraken()
            for binance_sym, kraken_sym in PAIRS.items():
                pair_data = kraken_data.get("result", {}).get(kraken_sym)
                if pair_data:
                    kraken_prices[binance_sym] = float(pair_data["c"][0])
        except Exception:
            pass

        return {"binance": binance_prices, "kraken": kraken_prices}

    @rate_limited("binance", 0.2)
    def _fetch_binance(self, symbol: str) -> dict:
        return fetch_json("https://api.binance.com/api/v3/ticker/price",
                          params={"symbol": symbol})

    @rate_limited("kraken", 1.0)
    @cached(ttl_seconds=300)
    def _fetch_kraken(self) -> dict:
        pairs = ",".join(PAIRS.values())
        return fetch_json("https://api.kraken.com/0/public/Ticker",
                          params={"pair": pairs})

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        binance = data.get("binance", {})
        kraken = data.get("kraken", {})

        for symbol in PAIRS:
            b_price = binance.get(symbol, 0)
            k_price = kraken.get(symbol, 0)
            if b_price <= 0 or k_price <= 0:
                continue

            mid = (b_price + k_price) / 2
            spread = (b_price - k_price) / mid

            if abs(spread) > SPREAD_THRESHOLD:
                # Binance expensive → sell (expect convergence)
                # Binance cheap → buy (expect convergence)
                if spread > SPREAD_THRESHOLD:
                    direction = "SHORT"
                    reason = f"Binance premium +{spread*100:.2f}% vs Kraken → convergence SHORT"
                else:
                    direction = "LONG"
                    reason = f"Binance discount {spread*100:.2f}% vs Kraken → convergence LONG"

                entry = b_price  # trade on Binance
                if direction == "LONG":
                    tp = round(entry * (1 + TP_PCT), 6)
                    sl = round(entry * (1 - SL_PCT), 6)
                else:
                    tp = round(entry * (1 - TP_PCT), 6)
                    sl = round(entry * (1 + SL_PCT), 6)

                confidence = min(0.8, 0.5 + abs(spread) * 50)

                picks.append(NormalizedPick(
                    symbol=symbol,
                    direction=direction,
                    entry_price=entry,
                    tp=tp, sl=sl,
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=round(confidence, 3),
                    reason=reason,
                    raw_signal={"binance_price": b_price, "kraken_price": k_price, "spread": spread},
                ))

        return picks
```

**Step 7: Write `btc_dominance_rotation.py`**

```python
"""BTC Dominance Rotation — rotate to alts when BTC.D falling, back to BTC when rising."""
from typing import List
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited, cached

ALT_TOKENS = ["ETHUSDT", "SOLUSDT", "AVAXUSDT", "ADAUSDT", "DOTUSDT",
              "LINKUSDT", "NEARUSDT", "APTUSDT", "SUIUSDT", "ARBUSDT"]

TP_PCT = 0.08
SL_PCT = 0.04


class BtcDominanceRotation(BaseStrategy):
    name = "btc_dominance_rotation"
    display_name = "BTC Dominance Rotation"
    source = "CoinGecko"
    category = "crypto"
    portfolio_type = "macro"

    @rate_limited("coingecko", 1.5)
    @cached(ttl_seconds=7200)  # 2h
    def fetch_data(self) -> dict:
        global_data = fetch_json("https://api.coingecko.com/api/v3/global")
        return global_data

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        picks = []
        try:
            market_data = data.get("data", {})
            btc_dom = market_data.get("market_cap_percentage", {}).get("btc", 50)
            btc_dom_change = market_data.get("market_cap_change_percentage_24h_usd", 0)

            # BTC dominance falling + market rising → alt season
            if btc_dom < 55 and btc_dom_change < -1:
                for symbol in ALT_TOKENS[:5]:
                    try:
                        ticker = fetch_json(
                            "https://api.binance.com/api/v3/ticker/price",
                            params={"symbol": symbol}
                        )
                        price = float(ticker.get("price", 0))
                    except Exception:
                        continue

                    if price <= 0:
                        continue

                    confidence = min(0.8, 0.5 + (55 - btc_dom) / 30)
                    picks.append(NormalizedPick(
                        symbol=symbol,
                        direction="LONG",
                        entry_price=price,
                        tp=round(price * (1 + TP_PCT), 6),
                        sl=round(price * (1 - SL_PCT), 6),
                        strategy=self.name,
                        strategy_name=self.display_name,
                        category=self.category,
                        confidence=round(confidence, 3),
                        reason=f"BTC.D={btc_dom:.1f}% falling ({btc_dom_change:+.1f}% 24h) → alt rotation",
                        raw_signal={"btc_dominance": btc_dom, "change_24h": btc_dom_change},
                    ))

            # BTC dominance rising sharply → flight to BTC
            elif btc_dom > 55 and btc_dom_change > 1:
                try:
                    ticker = fetch_json("https://api.binance.com/api/v3/ticker/price",
                                        params={"symbol": "BTCUSDT"})
                    price = float(ticker.get("price", 0))
                    if price > 0:
                        confidence = min(0.8, 0.5 + (btc_dom - 55) / 30)
                        picks.append(NormalizedPick(
                            symbol="BTCUSDT",
                            direction="LONG",
                            entry_price=price,
                            tp=round(price * (1 + TP_PCT), 6),
                            sl=round(price * (1 - SL_PCT), 6),
                            strategy=self.name,
                            strategy_name=self.display_name,
                            category=self.category,
                            confidence=round(confidence, 3),
                            reason=f"BTC.D={btc_dom:.1f}% rising ({btc_dom_change:+.1f}%) → flight to BTC",
                            raw_signal={"btc_dominance": btc_dom, "change_24h": btc_dom_change},
                        ))
                except Exception:
                    pass

        except (KeyError, TypeError):
            pass

        return picks
```

**Step 8: Update `paper_trading/strategies/__init__.py`**

```python
"""All paper trading strategies."""
from paper_trading.strategies.defi_tvl_momentum import DefiTvlMomentum
from paper_trading.strategies.fear_greed_contrarian import FearGreedContrarian
from paper_trading.strategies.funding_rate_carry import FundingRateCarry
from paper_trading.strategies.volume_breakout import VolumeBreakout
from paper_trading.strategies.stablecoin_supply import StablecoinSupply
from paper_trading.strategies.exchange_netflow import ExchangeNetflow
from paper_trading.strategies.rsi2_mean_reversion import Rsi2MeanReversion
from paper_trading.strategies.whale_accumulation import WhaleAccumulation
from paper_trading.strategies.cross_exchange_spread import CrossExchangeSpread
from paper_trading.strategies.btc_dominance_rotation import BtcDominanceRotation

ALL_STRATEGIES = [
    DefiTvlMomentum(),
    FearGreedContrarian(),
    FundingRateCarry(),
    VolumeBreakout(),
    StablecoinSupply(),
    ExchangeNetflow(),
    Rsi2MeanReversion(),
    WhaleAccumulation(),
    CrossExchangeSpread(),
    BtcDominanceRotation(),
]

# Map strategy name → portfolio type
STRATEGY_PORTFOLIO_MAP = {s.name: s.portfolio_type for s in ALL_STRATEGIES}
```

**Step 9: Commit**

```bash
git add paper_trading/strategies/
git commit -m "feat(paper-trading): add 7 remaining strategies (volume, SSR, netflow, RSI-2, whale, spread, BTC.D)"
```

---

### Task 4: Portfolio manager with SQLite persistence

**Files:**
- Create: `paper_trading/portfolio_manager.py`
- Create: `paper_trading/db.py`

**Step 1: Write `paper_trading/db.py`**

```python
"""SQLite persistence for paper trading portfolios."""
import json
import sqlite3
import pathlib
from datetime import datetime, timezone

DB_PATH = pathlib.Path(__file__).parent / "data" / "paper.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init_tables(conn)
    return conn


def _init_tables(conn: sqlite3.Connection):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS positions (
        id TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL,
        entry_price REAL NOT NULL,
        current_price REAL NOT NULL,
        tp REAL NOT NULL,
        sl REAL NOT NULL,
        strategy TEXT NOT NULL,
        strategy_name TEXT NOT NULL,
        portfolio_type TEXT NOT NULL,
        conviction_tier TEXT NOT NULL,
        position_size_usd REAL NOT NULL,
        shares REAL NOT NULL,
        entry_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        exit_price REAL,
        exit_date TEXT,
        pnl_pct REAL DEFAULT 0.0,
        pnl_usd REAL DEFAULT 0.0,
        mfe REAL DEFAULT 0.0,
        mae REAL DEFAULT 0.0,
        confidence REAL DEFAULT 0.5,
        reason TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS portfolios (
        name TEXT PRIMARY KEY,
        portfolio_type TEXT NOT NULL,
        starting_capital REAL NOT NULL DEFAULT 10000.0,
        cash REAL NOT NULL DEFAULT 10000.0,
        equity REAL NOT NULL DEFAULT 10000.0,
        total_trades INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        peak_equity REAL DEFAULT 10000.0,
        max_drawdown_pct REAL DEFAULT 0.0,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS equity_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        portfolio_name TEXT NOT NULL,
        equity REAL NOT NULL,
        timestamp TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_pos_status ON positions(status);
    CREATE INDEX IF NOT EXISTS idx_pos_portfolio ON positions(portfolio_type);
    CREATE INDEX IF NOT EXISTS idx_snap_portfolio ON equity_snapshots(portfolio_name);
    """)
    conn.commit()


def init_portfolios(conn: sqlite3.Connection):
    """Initialize all 9 portfolios if they don't exist."""
    now = datetime.now(timezone.utc).isoformat()
    portfolios = [
        # By strategy type
        ("technical", "strategy_type"),
        ("sentiment", "strategy_type"),
        ("onchain", "strategy_type"),
        ("derivatives", "strategy_type"),
        ("smart_money", "strategy_type"),
        ("macro", "strategy_type"),
        # By conviction tier
        ("high_conviction", "conviction_tier"),
        ("medium_conviction", "conviction_tier"),
        ("speculative", "conviction_tier"),
    ]
    for name, ptype in portfolios:
        conn.execute("""
            INSERT OR IGNORE INTO portfolios (name, portfolio_type, created_at)
            VALUES (?, ?, ?)
        """, (name, ptype, now))
    conn.commit()
```

**Step 2: Write `paper_trading/portfolio_manager.py`**

```python
"""Portfolio manager — allocates picks to 9 portfolios, tracks P&L, manages positions."""
import json
import logging
import pathlib
from collections import defaultdict
from datetime import datetime, timezone
from typing import List, Dict, Tuple

from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited
from paper_trading.db import get_conn, init_portfolios
from paper_trading.strategies import STRATEGY_PORTFOLIO_MAP

logger = logging.getLogger("paper_trading")

RISK_PER_TRADE = 0.02        # 2% of portfolio equity
MAX_SYMBOL_EXPOSURE = 0.10   # 10% max per symbol
TRANSACTION_COST = 0.007     # 0.7% round-trip for crypto
MAX_POSITIONS_PER_PORTFOLIO = 10
DATA_DIR = pathlib.Path(__file__).parent / "data"


class PortfolioManager:
    def __init__(self):
        self.conn = get_conn()
        init_portfolios(self.conn)

    def process_picks(self, picks: List[NormalizedPick]) -> Dict[str, list]:
        """Main entry: allocate picks to portfolios, check TP/SL, return events."""
        events = {"entries": [], "exits": [], "updates": []}

        # 1. Check existing positions for TP/SL hits
        exits = self._check_exits()
        events["exits"] = exits

        # 2. Assign conviction tiers
        tiered_picks = self._assign_conviction_tiers(picks)

        # 3. Allocate to strategy-type portfolios
        for pick, tier in tiered_picks:
            portfolio_type = STRATEGY_PORTFOLIO_MAP.get(pick.strategy, "technical")
            entry_event = self._try_open_position(pick, portfolio_type, tier)
            if entry_event:
                events["entries"].append(entry_event)

        # 4. Snapshot equity
        self._snapshot_equity()

        # 5. Export JSON files
        self._export_json()

        return events

    def _assign_conviction_tiers(self, picks: List[NormalizedPick]) -> List[Tuple[NormalizedPick, str]]:
        """Group picks by (symbol, direction), assign conviction tier."""
        groups = defaultdict(list)
        for p in picks:
            key = (p.symbol, p.direction)
            groups[key].append(p)

        result = []
        for (symbol, direction), group in groups.items():
            if len(group) >= 3:
                tier = "high_conviction"
            elif len(group) == 2:
                tier = "medium_conviction"
            else:
                tier = "speculative"

            # Keep best pick per group (highest confidence)
            best = max(group, key=lambda p: p.confidence)
            # Boost confidence for consensus
            if len(group) >= 2:
                avg_conf = sum(p.confidence for p in group) / len(group)
                best.confidence = min(0.95, avg_conf + 0.05 * len(group))

            result.append((best, tier))

        return result

    def _try_open_position(self, pick: NormalizedPick, portfolio_type: str, tier: str) -> dict:
        """Try to open a position in the given portfolio. Returns event dict or None."""
        # Check if already have this symbol in this portfolio
        existing = self.conn.execute(
            "SELECT COUNT(*) FROM positions WHERE symbol=? AND portfolio_type=? AND status='ACTIVE'",
            (pick.symbol, portfolio_type)
        ).fetchone()[0]
        if existing > 0:
            return None

        # Check position count limit
        active_count = self.conn.execute(
            "SELECT COUNT(*) FROM positions WHERE portfolio_type=? AND status='ACTIVE'",
            (portfolio_type,)
        ).fetchone()[0]
        if active_count >= MAX_POSITIONS_PER_PORTFOLIO:
            return None

        # Get portfolio state
        pf = self.conn.execute("SELECT * FROM portfolios WHERE name=?", (portfolio_type,)).fetchone()
        if not pf:
            return None
        cash = pf["cash"]
        equity = pf["equity"]

        # Position sizing: 2% risk
        dist_sl = abs(pick.entry_price - pick.sl)
        if dist_sl <= 0:
            return None
        risk_amount = equity * RISK_PER_TRADE
        shares = risk_amount / dist_sl
        position_usd = shares * pick.entry_price

        # Cap at max symbol exposure
        max_pos = equity * MAX_SYMBOL_EXPOSURE
        if position_usd > max_pos:
            position_usd = max_pos
            shares = position_usd / pick.entry_price

        # Check cash
        if position_usd > cash:
            return None

        now = datetime.now(timezone.utc).isoformat()
        pos_id = f"pt_{pick.strategy}::{pick.symbol}::{now[:10]}"

        # Insert position
        self.conn.execute("""
            INSERT OR REPLACE INTO positions
            (id, symbol, direction, entry_price, current_price, tp, sl,
             strategy, strategy_name, portfolio_type, conviction_tier,
             position_size_usd, shares, entry_date, status, confidence, reason)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (pos_id, pick.symbol, pick.direction, pick.entry_price, pick.entry_price,
              pick.tp, pick.sl, pick.strategy, pick.strategy_name,
              portfolio_type, tier, round(position_usd, 2), round(shares, 6),
              now, "ACTIVE", pick.confidence, pick.reason))

        # Update portfolio cash
        new_cash = cash - position_usd
        self.conn.execute("UPDATE portfolios SET cash=? WHERE name=?", (round(new_cash, 2), portfolio_type))

        # Also open in conviction-tier portfolio
        tier_pf = self.conn.execute("SELECT * FROM portfolios WHERE name=?", (tier,)).fetchone()
        if tier_pf:
            tier_cash = tier_pf["cash"]
            if position_usd <= tier_cash:
                tier_pos_id = f"pt_{tier}_{pick.strategy}::{pick.symbol}::{now[:10]}"
                existing_tier = self.conn.execute(
                    "SELECT COUNT(*) FROM positions WHERE symbol=? AND portfolio_type=? AND status='ACTIVE'",
                    (pick.symbol, tier)
                ).fetchone()[0]
                if existing_tier == 0:
                    self.conn.execute("""
                        INSERT OR REPLACE INTO positions
                        (id, symbol, direction, entry_price, current_price, tp, sl,
                         strategy, strategy_name, portfolio_type, conviction_tier,
                         position_size_usd, shares, entry_date, status, confidence, reason)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (tier_pos_id, pick.symbol, pick.direction, pick.entry_price, pick.entry_price,
                          pick.tp, pick.sl, pick.strategy, pick.strategy_name,
                          tier, tier, round(position_usd, 2), round(shares, 6),
                          now, "ACTIVE", pick.confidence, pick.reason))
                    self.conn.execute("UPDATE portfolios SET cash=? WHERE name=?",
                                     (round(tier_cash - position_usd, 2), tier))

        self.conn.commit()

        return {
            "type": "entry",
            "symbol": pick.symbol,
            "direction": pick.direction,
            "entry_price": pick.entry_price,
            "tp": pick.tp,
            "sl": pick.sl,
            "position_usd": round(position_usd, 2),
            "portfolio": portfolio_type,
            "tier": tier,
            "strategy": pick.strategy_name,
            "confidence": pick.confidence,
            "reason": pick.reason,
            "risk_reward": pick.risk_reward,
        }

    def _check_exits(self) -> list:
        """Check all active positions for TP/SL hits using latest prices."""
        exits = []
        active = self.conn.execute("SELECT * FROM positions WHERE status='ACTIVE'").fetchall()

        # Group by symbol for efficient price fetching
        symbols = set(row["symbol"] for row in active)
        prices = {}
        for sym in symbols:
            try:
                ticker = self._fetch_price(sym)
                prices[sym] = float(ticker.get("price", 0))
            except Exception:
                continue

        now = datetime.now(timezone.utc).isoformat()

        for pos in active:
            symbol = pos["symbol"]
            current = prices.get(symbol, 0)
            if current <= 0:
                continue

            # Update current price and MFE/MAE
            entry = pos["entry_price"]
            direction = pos["direction"]

            if direction == "LONG":
                pnl_pct = ((current - entry) / entry) * 100
                mfe = max(pos["mfe"], pnl_pct)
                mae = min(pos["mae"], pnl_pct)
                tp_hit = current >= pos["tp"]
                sl_hit = current <= pos["sl"]
            else:  # SHORT
                pnl_pct = ((entry - current) / entry) * 100
                mfe = max(pos["mfe"], pnl_pct)
                mae = min(pos["mae"], pnl_pct)
                tp_hit = current <= pos["tp"]
                sl_hit = current >= pos["sl"]

            # Check max hold (7 days)
            from datetime import datetime as dt_cls
            entry_dt = dt_cls.fromisoformat(pos["entry_date"].replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            hold_days = (now_dt - entry_dt).days
            expired = hold_days >= 7

            status = "ACTIVE"
            exit_reason = ""
            if tp_hit:
                status = "TP_HIT"
                exit_reason = "Take profit hit"
            elif sl_hit:
                status = "SL_HIT"
                exit_reason = "Stop loss hit"
            elif expired:
                status = "EXPIRED"
                exit_reason = f"Max hold {hold_days}d exceeded"

            # Apply transaction costs to P&L
            net_pnl_pct = pnl_pct - (TRANSACTION_COST * 100)
            pnl_usd = pos["position_size_usd"] * net_pnl_pct / 100

            # Update position
            self.conn.execute("""
                UPDATE positions SET current_price=?, pnl_pct=?, pnl_usd=?,
                mfe=?, mae=?, status=?, exit_price=?, exit_date=?
                WHERE id=?
            """, (current, round(net_pnl_pct, 3), round(pnl_usd, 2),
                  round(mfe, 3), round(mae, 3),
                  status,
                  current if status != "ACTIVE" else None,
                  now if status != "ACTIVE" else None,
                  pos["id"]))

            if status != "ACTIVE":
                # Update portfolio
                portfolio = pos["portfolio_type"]
                pf = self.conn.execute("SELECT * FROM portfolios WHERE name=?", (portfolio,)).fetchone()
                if pf:
                    new_cash = pf["cash"] + pos["position_size_usd"] + pnl_usd
                    new_equity = new_cash + self._get_unrealized(portfolio)
                    new_trades = pf["total_trades"] + 1
                    new_wins = pf["wins"] + (1 if pnl_usd > 0 else 0)
                    new_losses = pf["losses"] + (1 if pnl_usd <= 0 else 0)
                    new_peak = max(pf["peak_equity"], new_equity)
                    dd = ((new_peak - new_equity) / new_peak * 100) if new_peak > 0 else 0
                    new_dd = max(pf["max_drawdown_pct"], dd)

                    self.conn.execute("""
                        UPDATE portfolios SET cash=?, equity=?, total_trades=?,
                        wins=?, losses=?, peak_equity=?, max_drawdown_pct=?
                        WHERE name=?
                    """, (round(new_cash, 2), round(new_equity, 2), new_trades,
                          new_wins, new_losses, round(new_peak, 2), round(new_dd, 2),
                          portfolio))

                exits.append({
                    "type": "exit",
                    "symbol": symbol,
                    "direction": direction,
                    "status": status,
                    "entry_price": entry,
                    "exit_price": current,
                    "pnl_pct": round(net_pnl_pct, 2),
                    "pnl_usd": round(pnl_usd, 2),
                    "hold_days": hold_days,
                    "portfolio": portfolio,
                    "strategy": pos["strategy_name"],
                    "reason": exit_reason,
                })

        self.conn.commit()
        return exits

    def _get_unrealized(self, portfolio_name: str) -> float:
        """Sum of unrealized P&L for active positions in portfolio."""
        rows = self.conn.execute(
            "SELECT pnl_usd FROM positions WHERE portfolio_type=? AND status='ACTIVE'",
            (portfolio_name,)
        ).fetchall()
        return sum(r["pnl_usd"] for r in rows)

    @rate_limited("binance", 0.1)
    def _fetch_price(self, symbol: str) -> dict:
        return fetch_json("https://api.binance.com/api/v3/ticker/price",
                          params={"symbol": symbol})

    def _snapshot_equity(self):
        """Take equity snapshot for all portfolios."""
        now = datetime.now(timezone.utc).isoformat()
        portfolios = self.conn.execute("SELECT * FROM portfolios").fetchall()
        for pf in portfolios:
            unrealized = self._get_unrealized(pf["name"])
            equity = pf["cash"] + unrealized
            # Update equity
            self.conn.execute("UPDATE portfolios SET equity=? WHERE name=?",
                              (round(equity, 2), pf["name"]))
            # Store snapshot
            self.conn.execute(
                "INSERT INTO equity_snapshots (portfolio_name, equity, timestamp) VALUES (?,?,?)",
                (pf["name"], round(equity, 2), now))
        self.conn.commit()

    def get_portfolio_summary(self) -> list:
        """Return all portfolio stats for Discord reporting."""
        portfolios = self.conn.execute("SELECT * FROM portfolios ORDER BY portfolio_type, name").fetchall()
        result = []
        for pf in portfolios:
            active = self.conn.execute(
                "SELECT COUNT(*) FROM positions WHERE portfolio_type=? AND status='ACTIVE'",
                (pf["name"],)
            ).fetchone()[0]
            wr = (pf["wins"] / pf["total_trades"] * 100) if pf["total_trades"] > 0 else 0
            pnl_pct = ((pf["equity"] - pf["starting_capital"]) / pf["starting_capital"]) * 100

            result.append({
                "name": pf["name"],
                "type": pf["portfolio_type"],
                "equity": pf["equity"],
                "cash": pf["cash"],
                "pnl_pct": round(pnl_pct, 2),
                "total_trades": pf["total_trades"],
                "wins": pf["wins"],
                "losses": pf["losses"],
                "win_rate": round(wr, 1),
                "active_positions": active,
                "max_drawdown": pf["max_drawdown_pct"],
            })
        return result

    def _export_json(self):
        """Export current state to JSON files for Git commits."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Active picks
        active = self.conn.execute("SELECT * FROM positions WHERE status='ACTIVE'").fetchall()
        active_list = [dict(r) for r in active]
        (DATA_DIR / "active_picks.json").write_text(json.dumps(active_list, indent=2))

        # Closed picks
        closed = self.conn.execute(
            "SELECT * FROM positions WHERE status!='ACTIVE' ORDER BY exit_date DESC LIMIT 500"
        ).fetchall()
        closed_list = [dict(r) for r in closed]
        (DATA_DIR / "closed_picks.json").write_text(json.dumps(closed_list, indent=2))

        # Portfolio summary
        summary = self.get_portfolio_summary()
        (DATA_DIR / "portfolios.json").write_text(json.dumps(summary, indent=2))

        # Performance with history
        perf = {"portfolios": summary, "updated_at": datetime.now(timezone.utc).isoformat()}
        (DATA_DIR / "performance.json").write_text(json.dumps(perf, indent=2))

    def close(self):
        self.conn.close()
```

**Step 3: Commit**

```bash
git add paper_trading/db.py paper_trading/portfolio_manager.py
git commit -m "feat(paper-trading): portfolio manager with SQLite persistence, 9 portfolios, position sizing"
```

---

### Task 5: Discord reporter

**Files:**
- Create: `paper_trading/discord_reporter.py`

**Step 1: Write `discord_reporter.py`**

```python
"""Discord reporter — posts trade events and portfolio summaries to #paper-trade."""
import json
import logging
import os
import requests
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger("paper_trading")

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_PAPER_TRADE", "")
USERNAME = "Paper Trading Bot"
AVATAR_URL = ""

COLOR_GREEN = 0x22C55E
COLOR_RED = 0xEF4444
COLOR_BLUE = 0x3B82F6
COLOR_GOLD = 0xFFD700
COLOR_GRAY = 0x6B7280
COLOR_PURPLE = 0x8B5CF6

EST = timezone(timedelta(hours=-5))


def _post_webhook(payload: dict, max_retries: int = 3):
    """Post to Discord webhook with retry/backoff."""
    if not WEBHOOK_URL:
        logger.warning("No DISCORD_WEBHOOK_PAPER_TRADE set, skipping Discord post")
        return
    for attempt in range(max_retries):
        try:
            r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", 2 ** (attempt + 1)))
                logger.warning(f"Discord rate limited, waiting {retry_after}s")
                time.sleep(retry_after)
                continue
            if r.status_code == 204 or r.ok:
                return
            logger.warning(f"Discord webhook returned {r.status_code}: {r.text[:200]}")
        except Exception as e:
            logger.error(f"Discord webhook error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    logger.error("Failed to post to Discord after retries")


def _progress_bar(value: float, total: float, length: int = 10) -> str:
    """Create a visual progress bar."""
    if total <= 0:
        return "░" * length
    filled = int(length * min(value / total, 1.0))
    return "█" * filled + "░" * (length - filled)


def send_entry_alert(event: dict):
    """Send a new entry notification."""
    symbol = event["symbol"]
    direction = event["direction"]
    color = COLOR_GREEN if direction == "LONG" else COLOR_RED
    arrow = "📈" if direction == "LONG" else "📉"

    conf_bar = _progress_bar(event.get("confidence", 0.5), 1.0, 10)
    rr = event.get("risk_reward", 0)

    embed = {
        "title": f"{arrow} NEW ENTRY | {symbol} {direction}",
        "color": color,
        "fields": [
            {"name": "Portfolio", "value": f"`{event['portfolio']}` → `{event['tier']}`", "inline": True},
            {"name": "Strategy", "value": event.get("strategy", ""), "inline": True},
            {"name": "Position Size", "value": f"${event.get('position_usd', 0):,.2f}", "inline": True},
            {"name": "Entry", "value": f"${event['entry_price']:,.4f}", "inline": True},
            {"name": "TP", "value": f"${event['tp']:,.4f}", "inline": True},
            {"name": "SL", "value": f"${event['sl']:,.4f}", "inline": True},
            {"name": "Confidence", "value": f"{conf_bar} {event.get('confidence', 0.5)*100:.0f}%", "inline": True},
            {"name": "Risk:Reward", "value": f"{rr:.1f}:1", "inline": True},
            {"name": "Reason", "value": event.get("reason", "")[:200], "inline": False},
        ],
        "footer": {"text": f"Paper Trade Only • Not Financial Advice • {datetime.now(EST).strftime('%b %d %Y %I:%M %p EST')}"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    _post_webhook({
        "username": USERNAME,
        "embeds": [embed],
    })


def send_exit_alert(event: dict):
    """Send an exit (TP/SL/expiry) notification."""
    symbol = event["symbol"]
    status = event["status"]
    pnl_pct = event.get("pnl_pct", 0)
    pnl_usd = event.get("pnl_usd", 0)

    if status == "TP_HIT":
        emoji = "✅"
        color = COLOR_GREEN
    elif status == "SL_HIT":
        emoji = "🛑"
        color = COLOR_RED
    else:
        emoji = "⏰"
        color = COLOR_GRAY

    pnl_sign = "+" if pnl_pct >= 0 else ""

    embed = {
        "title": f"{emoji} {status.replace('_', ' ')} | {symbol} {event['direction']}",
        "color": color,
        "fields": [
            {"name": "P&L", "value": f"**{pnl_sign}{pnl_pct:.2f}%** (${pnl_sign}{pnl_usd:.2f})", "inline": True},
            {"name": "Entry → Exit", "value": f"${event['entry_price']:,.4f} → ${event['exit_price']:,.4f}", "inline": True},
            {"name": "Hold Time", "value": f"{event.get('hold_days', 0)} days", "inline": True},
            {"name": "Portfolio", "value": f"`{event['portfolio']}`", "inline": True},
            {"name": "Strategy", "value": event.get("strategy", ""), "inline": True},
        ],
        "footer": {"text": f"Paper Trade Only • {datetime.now(EST).strftime('%b %d %Y %I:%M %p EST')}"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    _post_webhook({
        "username": USERNAME,
        "embeds": [embed],
    })


def send_portfolio_summary(summary: list):
    """Send the 4-hourly portfolio summary with tables."""
    now_est = datetime.now(EST).strftime("%b %d, %Y %I:%M %p EST")

    # Split by type
    strategy_type = [p for p in summary if p["type"] == "strategy_type"]
    conviction_tier = [p for p in summary if p["type"] == "conviction_tier"]

    # Build strategy type table
    st_lines = ["```"]
    st_lines.append(f"{'Portfolio':<14} {'Value':>10} {'P&L%':>7} {'Trades':>7} {'WR%':>6} {'Active':>7}")
    st_lines.append("─" * 55)
    for p in strategy_type:
        pnl_str = f"{p['pnl_pct']:+.1f}%"
        st_lines.append(
            f"{p['name']:<14} ${p['equity']:>8,.0f} {pnl_str:>7} {p['total_trades']:>7} "
            f"{p['win_rate']:>5.0f}% {p['active_positions']:>7}"
        )
    st_lines.append("```")

    # Build conviction tier table
    ct_lines = ["```"]
    ct_lines.append(f"{'Portfolio':<18} {'Value':>10} {'P&L%':>7} {'Trades':>7} {'WR%':>6}")
    ct_lines.append("─" * 52)
    for p in conviction_tier:
        pnl_str = f"{p['pnl_pct']:+.1f}%"
        ct_lines.append(
            f"{p['name']:<18} ${p['equity']:>8,.0f} {pnl_str:>7} {p['total_trades']:>7} {p['win_rate']:>5.0f}%"
        )
    ct_lines.append("```")

    # Find best/worst
    all_pf = strategy_type + conviction_tier
    if all_pf:
        best = max(all_pf, key=lambda p: p["pnl_pct"])
        worst = min(all_pf, key=lambda p: p["pnl_pct"])
        footer_text = f"🏆 Best: {best['name']} ({best['pnl_pct']:+.1f}%) | 📉 Worst: {worst['name']} ({worst['pnl_pct']:+.1f}%)"
    else:
        footer_text = "No portfolio data yet"

    total_equity = sum(p["equity"] for p in all_pf)
    total_starting = sum(10000 for _ in all_pf)
    total_pnl = ((total_equity - total_starting) / total_starting) * 100 if total_starting else 0

    embeds = [
        {
            "title": f"📊 PAPER PORTFOLIO REPORT | {now_est}",
            "description": f"**Total Equity:** ${total_equity:,.0f} / ${total_starting:,.0f} ({total_pnl:+.2f}%)",
            "color": COLOR_BLUE,
            "fields": [
                {"name": "📈 BY STRATEGY TYPE", "value": "\n".join(st_lines), "inline": False},
                {"name": "🎯 BY CONVICTION TIER", "value": "\n".join(ct_lines), "inline": False},
            ],
            "footer": {"text": footer_text},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ]

    _post_webhook({
        "username": USERNAME,
        "embeds": embeds,
    })


def send_events(events: dict, portfolio_summary: list = None):
    """Send all trade events and optionally a portfolio summary."""
    # Send entry alerts (batch up to 10 per message)
    entries = events.get("entries", [])
    for entry in entries:
        send_entry_alert(entry)
        time.sleep(0.5)  # avoid rate limits

    # Send exit alerts
    exits = events.get("exits", [])
    for exit_event in exits:
        send_exit_alert(exit_event)
        time.sleep(0.5)

    # Send summary if provided
    if portfolio_summary:
        send_portfolio_summary(portfolio_summary)
```

**Step 2: Commit**

```bash
git add paper_trading/discord_reporter.py
git commit -m "feat(paper-trading): Discord reporter with entry/exit alerts and 4-hourly portfolio summaries"
```

---

### Task 6: Scanner (main entry point)

**Files:**
- Create: `paper_trading/scanner.py`

**Step 1: Write `scanner.py`**

```python
"""Main scanner entry point — runs all strategies, feeds portfolio manager, reports to Discord."""
import json
import logging
import os
import sys
import pathlib
from datetime import datetime, timezone

from paper_trading.strategies import ALL_STRATEGIES
from paper_trading.portfolio_manager import PortfolioManager
from paper_trading import discord_reporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("paper_trading")


def main():
    logger.info("=" * 60)
    logger.info("Paper Trading Scanner v1.0 — 10 strategies, 9 portfolios")
    logger.info("=" * 60)

    # 1. Run all strategies
    all_picks = []
    for strategy in ALL_STRATEGIES:
        try:
            picks = strategy.run()
            all_picks.extend(picks)
        except Exception as e:
            logger.error(f"Strategy {strategy.name} crashed: {e}")

    logger.info(f"Total raw picks: {len(all_picks)}")

    # 2. Feed to portfolio manager
    pm = PortfolioManager()
    try:
        events = pm.process_picks(all_picks)

        entries = events.get("entries", [])
        exits = events.get("exits", [])
        logger.info(f"New entries: {len(entries)}")
        logger.info(f"Exits (TP/SL/expiry): {len(exits)}")

        # 3. Get portfolio summary
        summary = pm.get_portfolio_summary()

        # 4. Report to Discord
        # Always send trade events; send summary every run (4h cadence from workflow)
        discord_reporter.send_events(events, portfolio_summary=summary)

        # 5. Print summary to stdout for CI logs
        print("\n📊 Portfolio Summary:")
        for p in summary:
            print(f"  {p['name']:<18} ${p['equity']:>10,.2f}  {p['pnl_pct']:>+7.2f}%  "
                  f"WR: {p['win_rate']:>5.1f}%  Trades: {p['total_trades']}")

        print(f"\n✅ Scanner complete at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    finally:
        pm.close()


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add paper_trading/scanner.py paper_trading/__main__.py
git commit -m "feat(paper-trading): main scanner entry point wiring strategies → portfolio → Discord"
```

---

### Task 7: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/paper-trading.yml`

**Step 1: Write the workflow**

```yaml
name: Paper Trading Portfolio

on:
  schedule:
    - cron: '0 */4 * * *'     # Every 4 hours
  workflow_dispatch:            # Manual trigger

permissions:
  contents: write

jobs:
  run-scanner:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GH_PAT }}

      - name: Fix submodule entry
        run: |
          git rm --cached tmp/fte_clone 2>/dev/null || true
          git config --global --add safe.directory "$GITHUB_WORKSPACE"

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install requests

      - name: Run paper trading scanner
        env:
          DISCORD_WEBHOOK_PAPER_TRADE: ${{ secrets.DISCORD_WEBHOOK_PAPER_TRADE }}
          CRYPTOQUANT_API_KEY: ${{ secrets.CRYPTOQUANT_API_KEY }}
          COINGECKO_API_KEY: ${{ secrets.COINGECKO_API_KEY }}
        run: |
          echo "=== Paper Trading Scanner v1.0 ==="
          echo "Time: $(date -u)"
          python -m paper_trading

      - name: Count active positions
        id: count
        run: |
          if [ -f paper_trading/data/active_picks.json ]; then
            COUNT=$(python3 -c "import json; print(len(json.load(open('paper_trading/data/active_picks.json'))))")
          else
            COUNT=0
          fi
          echo "count=$COUNT" >> $GITHUB_OUTPUT
          echo "Active positions: $COUNT"

      - name: Commit data snapshots
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add paper_trading/data/*.json paper_trading/data/*.db 2>/dev/null || true
          TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M UTC")
          git commit -m "Paper trading scan [$TIMESTAMP] — ${{ steps.count.outputs.count }} active positions" || echo "No changes to commit"

      - name: Push with retry
        run: |
          for i in 1 2 3; do
            git pull --rebase origin main && git push && break
            echo "Push attempt $i failed, retrying..."
            sleep 5
          done
```

**Step 2: Commit**

```bash
git add .github/workflows/paper-trading.yml
git commit -m "ci(paper-trading): add GitHub Actions workflow — every 4h scan + Discord + commit"
```

---

### Task 8: Add Discord webhook secret and test

**Step 1: Add the webhook as a GitHub secret**

```bash
gh secret set DISCORD_WEBHOOK_PAPER_TRADE --body "https://discord.com/api/webhooks/1478588243459965008/9TZAjAtrgz5dTvWpV3TP7FO8Fo5JRDCz03PkPiTaSlef0EcIEdHEDUmz8Zi13sZrqgA3"
```

**Step 2: Run a local test to verify**

```bash
cd /e/findtorontoevents_antigravity.ca
DISCORD_WEBHOOK_PAPER_TRADE="https://discord.com/api/webhooks/1478588243459965008/9TZAjAtrgz5dTvWpV3TP7FO8Fo5JRDCz03PkPiTaSlef0EcIEdHEDUmz8Zi13sZrqgA3" python -m paper_trading
```

**Step 3: Verify Discord received the messages**

Check #paper-trade channel for entry alerts + portfolio summary.

**Step 4: Trigger workflow manually**

```bash
gh workflow run paper-trading.yml
gh run watch
```

---

### Task 9: Update updates page and sync

**Step 1: Add entry to `updates/index.html`**

Insert a new update entry documenting the Paper Trading Portfolio system.

**Step 2: Commit and push everything**

```bash
git add updates/index.html
git commit -m "docs: add Paper Trading Portfolio system to updates page"
git push
```
