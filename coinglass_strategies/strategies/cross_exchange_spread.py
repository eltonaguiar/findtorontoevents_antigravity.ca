"""S4: Cross-Exchange Spread — divergence between exchanges.

DISABLED: This strategy requires simultaneous data from both Binance AND OKX.
Binance Futures API is geo-blocked (HTTP 451) from GitHub Actions runners,
so we can never get both sides of the spread. Rather than silently producing
nothing, we log and return None explicitly.

Re-enable when: Binance data becomes available (e.g., via proxy or new API source).
"""
import logging
from typing import Dict, Optional
from .base import Signal
from .. import config
from ..data_fetcher import fetch_binance, fetch_okx

logger = logging.getLogger(__name__)

# Set to True to re-enable when Binance data source is restored
_ENABLED = False


def run(symbol: str, **kwargs) -> Optional[Signal]:
    if not _ENABLED:
        logger.debug("S4-ExchangeSpread: disabled — requires both Binance and OKX data (Binance geo-blocked)")
        return None

    binance_ratios = fetch_binance(symbol)
    okx_ratios = fetch_okx(symbol)
    b_global = binance_ratios.get("global")
    o_global = okx_ratios.get("global")
    if b_global is None or o_global is None:
        logger.debug("S4-ExchangeSpread: missing data — Binance=%s, OKX=%s", b_global, o_global)
        return None
    spread = b_global - o_global
    if abs(spread) < config.CROSS_EXCHANGE_SPREAD_MIN:
        return None
    direction = "LONG" if b_global > 1 else "SHORT"
    conf = 0.50 + 0.05 * min(abs(spread) / 0.2, 2.0)
    conf = round(min(conf, 0.60), 3)
    return Signal(symbol=symbol, direction=direction, strategy="coinglass_exchange_spread",
                  confidence=conf, reason=f"Binance={b_global:.3f} vs OKX={o_global:.3f} (spread={spread:.3f})",
                  ratios={"binance": binance_ratios, "okx": okx_ratios})
