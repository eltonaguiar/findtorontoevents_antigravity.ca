"""
MiMo (Xiaomi) reference delivery — on-chain crypto signals. 2026-05-18.
REFERENCE ONLY — unvalidated by MiMo (could not run the harness). Vet before
reuse. Known gaps: Glassnode free tier has limited history; no post-cost gate;
harness wiring is a TODO. Good parts: real Glassnode + DefiLlama APIs (DefiLlama
stablecoin endpoint is free + historically complete), pure signal math.

Three genuinely-new input signals derived from blockchain observables:
  1. exchange_net_flow      — z-scored net BTC/ETH flow to exchange wallets
  2. stablecoin_supply_chg  — 7-day fractional change in aggregate stablecoin supply
  3. active_addr_momentum   — 14-day momentum of daily active addresses

Data sources:
  Glassnode API  (exchange flows, active addresses) — needs GLASSNODE_API_KEY
  DefiLlama API  (stablecoin supply)                — free, no auth
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Optional

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger(__name__)

GLASSNODE_BASE = "https://api.glassnode.com/v1/metrics"
DEFILLAMA_BASE = "https://stablecoins.llama.fi"
RATE_LIMIT_SLEEP = 0.15

FLOW_ZSCORE_WINDOW = 20
SUPPLY_LOOKBACK_DAYS = 7
ADDR_MOMENTUM_DAYS = 14
SIGNAL_ZSCORE_WINDOW = 20

SIGNAL_NAMES = [
    "exchange_net_flow",
    "stablecoin_supply_chg",
    "active_addr_momentum",
]


def _glassnode_get(metric: str, api_key: str, params: dict | None = None,
                   max_retries: int = 3) -> list[dict]:
    url = f"{GLASSNODE_BASE}/{metric}"
    p = {"api_key": api_key, "c": "BTC", **(params or {})}
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=p, timeout=20)
            resp.raise_for_status()
            return resp.json() or []
        except requests.RequestException as exc:
            logger.warning("Glassnode %s attempt %d: %s",
                           metric, attempt + 1, exc)
            if attempt < max_retries - 1:
                time.sleep(RATE_LIMIT_SLEEP * (attempt + 1))
    return []


def _defillama_get(path: str, max_retries: int = 3):
    url = f"{DEFILLAMA_BASE}{path}"
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.warning("DefiLlama %s attempt %d: %s",
                           path, attempt + 1, exc)
            if attempt < max_retries - 1:
                time.sleep(RATE_LIMIT_SLEEP * (attempt + 1))
    return []


def fetch_exchange_net_flows(api_key: str, currency: str = "BTC",
                             days: int = 365) -> pd.Series:
    """Daily net flow (inflows - outflows) to exchange wallets.
    Positive = net inflow -> bearish pressure."""
    raw = _glassnode_get(
        "transactions/transfers_volume_exchanges_net", api_key,
        {"c": currency, "i": "24h", "s": int(time.time()) - days * 86400},
    )
    if not raw:
        raise ValueError("Glassnode returned no exchange flow data")
    series = pd.Series(
        {datetime.fromtimestamp(r["t"], tz=timezone.utc): r["v"]
         for r in raw if "t" in r and "v" in r},
        name="exchange_net_flow",
    )
    series.index = pd.to_datetime(series.index)
    return series.sort_index()


def fetch_active_addresses(api_key: str, currency: str = "BTC",
                           days: int = 365) -> pd.Series:
    """Daily count of unique active addresses."""
    raw = _glassnode_get(
        "addresses/active_count", api_key,
        {"c": currency, "i": "24h", "s": int(time.time()) - days * 86400},
    )
    if not raw:
        raise ValueError("Glassnode returned no active address data")
    series = pd.Series(
        {datetime.fromtimestamp(r["t"], tz=timezone.utc): r["v"]
         for r in raw if "t" in r and "v" in r},
        name="active_addresses",
    )
    series.index = pd.to_datetime(series.index)
    return series.sort_index()


def fetch_stablecoin_supply_history(days: int = 365) -> pd.Series:
    """Aggregate stablecoin market-cap history (USD).
    Source: DefiLlama stablecoincharts/all — FREE, no API key."""
    raw = _defillama_get("/stablecoincharts/all")
    if not raw:
        raise ValueError("DefiLlama returned no stablecoin data")
    cutoff = time.time() - days * 86400
    series = pd.Series(
        {datetime.fromtimestamp(r["date"], tz=timezone.utc):
         float(r.get("totalCirculatingUSD", {}).get("peggedUSD", 0))
         for r in raw if r.get("date", 0) >= cutoff},
        name="stablecoin_supply",
    )
    series.index = pd.to_datetime(series.index)
    return series.sort_index()


def compute_exchange_net_flow_zscore(flows: pd.Series,
                                     window: int = FLOW_ZSCORE_WINDOW
                                     ) -> pd.Series:
    """Z-scored exchange net flow.  Positive z -> above-average inflows."""
    mu = flows.rolling(window, min_periods=window).mean()
    sigma = flows.rolling(window, min_periods=window).std().replace(0, np.nan)
    return (flows - mu) / sigma


def compute_stablecoin_supply_change(supply: pd.Series,
                                     lookback: int = SUPPLY_LOOKBACK_DAYS
                                     ) -> pd.Series:
    """Fractional change in stablecoin supply over `lookback` days."""
    return supply.pct_change(periods=lookback)


def compute_active_addr_momentum(addresses: pd.Series,
                                  lookback: int = ADDR_MOMENTUM_DAYS
                                  ) -> pd.Series:
    """Rate of change of daily active addresses over `lookback` days."""
    return addresses.pct_change(periods=lookback)


def load_historical_and_generate_signals(
    exchange_flows: pd.Series,
    stablecoin_supply: pd.Series,
    active_addresses: pd.Series,
    signals: list[str] | None = None,
) -> pd.DataFrame:
    """Build signal DataFrame from raw on-chain time series."""
    if signals is None:
        signals = list(SIGNAL_NAMES)
    parts: dict[str, pd.Series] = {}
    if "exchange_net_flow" in signals:
        parts["exchange_net_flow"] = compute_exchange_net_flow_zscore(
            exchange_flows)
    if "stablecoin_supply_chg" in signals:
        parts["stablecoin_supply_chg"] = compute_stablecoin_supply_change(
            stablecoin_supply)
    if "active_addr_momentum" in signals:
        parts["active_addr_momentum"] = compute_active_addr_momentum(
            active_addresses)
    df = pd.DataFrame(parts)
    df.index.name = "date"
    return df
