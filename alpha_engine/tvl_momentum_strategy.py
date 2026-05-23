"""
TVL Momentum Strategy -- DefiLlama Capital Flow Signals
======================================================
Wraps defillama_signals.py into a scanner-compatible strategy that generates
tradeable BUY/SELL picks based on TVL momentum and stablecoin flows.

Logic:
  - Chain TVL rising >5% in 7d + stablecoin inflow = LONG the chain's native token
  - Chain TVL falling >5% in 7d + stablecoin outflow = SHORT the chain's native token
  - TVL-price divergence (TVL up, price down) = accumulation → contrarian LONG
  - TVL-price divergence (TVL down, price up) = distribution → SHORT

API: DefiLlama (api.llama.fi) -- 100% free, no key needed.
Evidence: TVL leads price by 1-2 weeks (DeFi Pulse 2021, Messari 2022).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Chain → tradeable symbol mapping
CHAIN_TO_SYMBOL = {
    "Ethereum": "ETH-USD",
    "Solana": "SOL-USD",
    "Avalanche": "AVAX-USD",
    "BSC": "BNB-USD",
    "Polygon": "MATIC-USD",
    "Arbitrum": "ARB-USD",
    "Near": "NEAR-USD",
    "Sui": "SUI-USD",
    "Base": "ETH-USD",        # Base TVL benefits ETH
    "Tron": "TRX-USD",
}

# TVL momentum thresholds
TVL_STRONG_INFLOW = 5.0    # >5% 7d TVL growth = strong signal
TVL_WEAK_INFLOW = 2.0      # >2% = weak signal
TVL_STRONG_OUTFLOW = -5.0   # <-5% = strong outflow
TVL_DIVERGENCE_THRESHOLD = 0.3  # Composite divergence score


def tvl_momentum_strategy(data: dict, context: dict | None = None) -> list[dict]:
    """
    Scanner-compatible strategy: generates picks from DefiLlama TVL signals.
    """
    try:
        from defillama_signals import (
            get_chain_tvl_momentum,
            get_stablecoin_supply_signal,
            get_tvl_price_divergence,
        )
    except ImportError:
        logger.warning("defillama_signals not available")
        return []

    signals = []
    now = datetime.now(timezone.utc).isoformat()

    # Get macro signal: stablecoin supply direction
    stable = get_stablecoin_supply_signal()
    stable_bullish = stable.get("signal") == "BULLISH"
    stable_bearish = stable.get("signal") == "BEARISH"

    for chain, symbol in CHAIN_TO_SYMBOL.items():
        if symbol not in data:
            continue

        try:
            df = data[symbol]
            if len(df) < 20:
                continue

            price = float(df["Close"].iloc[-1])
            # Compute 7d price change from dataframe
            if len(df) >= 7:
                price_7d_ago = float(df["Close"].iloc[-7])
                price_change_pct = ((price - price_7d_ago) / price_7d_ago) * 100
            else:
                price_change_pct = 0.0

            # Fetch TVL momentum from DefiLlama
            tvl = get_chain_tvl_momentum(chain)
            tvl_mom = tvl.get("momentum_pct", 0.0)
            tvl_signal = tvl.get("signal", "FLAT")

            # Fetch divergence
            div = get_tvl_price_divergence(chain, price_change_pct)
            div_score = div.get("divergence_score", 0.0)
            div_signal = div.get("signal", "NO_DIVERGENCE")

            # --- Signal 1: Strong TVL Inflow + Stablecoin Confirmation ---
            if tvl_mom >= TVL_STRONG_INFLOW and stable_bullish:
                conf = min(0.80, 0.55 + tvl_mom / 100)
                tp = round(price * 1.03, 2) if price > 1 else round(price * 1.03, 6)
                sl = round(price * 0.98, 2) if price > 1 else round(price * 0.98, 6)
                signals.append(_make_signal(
                    symbol, price, "BUY", "LONG", tp, sl, conf,
                    f"TVL +{tvl_mom:.1f}% 7d ({chain}) + stablecoin inflow -- capital entering DeFi",
                    tvl_mom, div_score, now,
                ))

            # --- Signal 2: TVL-Price Bullish Divergence (accumulation) ---
            elif div_signal == "BULLISH_DIVERGENCE" and tvl_mom > TVL_WEAK_INFLOW:
                conf = min(0.75, 0.50 + abs(div_score) / 2)
                tp = round(price * 1.035, 2) if price > 1 else round(price * 1.035, 6)
                sl = round(price * 0.975, 2) if price > 1 else round(price * 0.975, 6)
                signals.append(_make_signal(
                    symbol, price, "BUY", "LONG", tp, sl, conf,
                    f"TVL +{tvl_mom:.1f}% but price -{abs(price_change_pct):.1f}% ({chain}) -- accumulation divergence",
                    tvl_mom, div_score, now,
                ))

            # --- Signal 3: Strong TVL Outflow + Stablecoin Outflow ---
            elif tvl_mom <= TVL_STRONG_OUTFLOW and stable_bearish:
                conf = min(0.70, 0.50 + abs(tvl_mom) / 100)
                tp = round(price * 0.97, 2) if price > 1 else round(price * 0.97, 6)
                sl = round(price * 1.02, 2) if price > 1 else round(price * 1.02, 6)
                signals.append(_make_signal(
                    symbol, price, "SELL", "SHORT", tp, sl, conf,
                    f"TVL {tvl_mom:.1f}% 7d ({chain}) + stablecoin outflow -- capital exiting DeFi",
                    tvl_mom, div_score, now,
                ))

            # --- Signal 4: TVL-Price Bearish Divergence (distribution) ---
            elif div_signal == "BEARISH_DIVERGENCE" and tvl_mom < -TVL_WEAK_INFLOW:
                conf = min(0.65, 0.45 + abs(div_score) / 2)
                tp = round(price * 0.975, 2) if price > 1 else round(price * 0.975, 6)
                sl = round(price * 1.025, 2) if price > 1 else round(price * 1.025, 6)
                signals.append(_make_signal(
                    symbol, price, "SELL", "SHORT", tp, sl, conf,
                    f"TVL {tvl_mom:.1f}% but price +{price_change_pct:.1f}% ({chain}) -- distribution divergence",
                    tvl_mom, div_score, now,
                ))

        except Exception as e:
            logger.debug("TVL momentum error for %s: %s", chain, e)
            continue

    return signals


def _make_signal(symbol, price, signal_type, direction, tp, sl, conf,
                 reason, tvl_mom, div_score, timestamp):
    """Build a scanner-compatible pick dict."""
    rr = abs(tp - price) / abs(sl - price) if abs(sl - price) > 0 else 1.0
    return {
        "strategy": "tvl_momentum",
        "symbol": symbol,
        "category": "crypto",
        "signal_type": signal_type,
        "direction": direction,
        "entry_price": round(price, 2) if price > 1 else round(price, 6),
        "take_profit": tp,
        "stop_loss": sl,
        "confidence": round(conf, 2),
        "risk_reward": round(rr, 2),
        "reason": reason,
        "timeframe": "1w",
        "rsi_at_entry": 50,
        "volume_ratio": 1.0,
        "extra": {
            "tvl_momentum_pct": round(tvl_mom, 2),
            "divergence_score": round(div_score, 4),
            "source": "DefiLlama (free API, no key)",
            "reference": "TVL leads price by 1-2 weeks (DeFi Pulse 2021)",
        },
        "research_basis": "TVL capital flow leads token price by 1-2 weeks",
        "timestamp": timestamp,
    }


# Strategy registry for scanner integration
TVL_MOMENTUM_STRATEGIES = {
    "tvl_momentum": tvl_momentum_strategy,
}


if __name__ == "__main__":
    print("TVL Momentum Strategy -- requires scanner data context")
    print("Run via: python scanner.py (integrated)")
