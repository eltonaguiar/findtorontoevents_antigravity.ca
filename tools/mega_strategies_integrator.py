#!/usr/bin/env python3
"""
MEGA Strategies Integrator
Wires top-performing MEGA strategies to the scoring system.
"""

import sys
import os

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)

import pandas as pd
import numpy as np
import requests
import json
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]


def fetch_klines(symbol, interval="4h", limit=500):
    """Fetch klines from Binance."""
    for mirror in BINANCE_MIRRORS:
        try:
            url = f"{mirror}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            resp = requests.get(url, timeout=10)
            data = resp.json()
            df = pd.DataFrame(
                data,
                columns=[
                    "OpenTime",
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Volume",
                    "CloseTime",
                    "QuoteVolume",
                    "Trades",
                    "TakerBaseVol",
                    "TakerQuoteVol",
                    "Ignore",
                ],
            )
            for col in ["Open", "High", "Low", "Close", "Volume"]:
                df[col] = df[col].astype(float)
            df["Date"] = pd.to_datetime(df["OpenTime"], unit="ms")
            df = df.set_index("Date")
            return df
        except Exception as e:
            continue
    return None


# Top performing strategies from backtest
TOP_STRATEGIES = [
    ("signal_price_volume_corr", "CRYPTO", 1.00, 19.63),
    ("signal_open_interest", "CRYPTO", 0.995, 30.04),
    ("signal_bollinger_squeeze", "CRYPTO", 0.929, 4.48),
    ("signal_macd_histogram", "CRYPTO", 0.866, 9.23),
    ("signal_ema_crossover", "CRYPTO", 0.844, 3.18),
    ("signal_onchain_volume", "CRYPTO", 0.812, 18.69),
    ("signal_volume_atr_momentum", "CRYPTO", 0.701, 20.81),
    ("signal_heikin_ashi", "CRYPTO", 0.658, 48.93),
    ("signal_ttm_squeeze", "CRYPTO", 0.620, 27.06),
    ("signal_ichimoku", "CRYPTO", 0.572, 33.14),
]


def generate_mega_signals(symbols, strategy_names):
    """Generate signals using MEGA strategies."""
    sys.path.insert(0, REPO_DIR)
    from genome.mutation_lab import mega_crypto_strategies as mcs

    signals = []

    for symbol in symbols:
        df = fetch_klines(symbol)
        if df is None or len(df) < 100:
            continue

        for strat_name in strategy_names:
            strat_func = getattr(mcs, strat_name, None)
            if strat_func is None:
                continue

            try:
                result = strat_func(df)
                long = result.get("long", pd.Series([False] * len(df)))
                short = result.get("short", pd.Series([False] * len(df)))
                tp = result.get("tp", 0.03)
                sl = result.get("sl", 0.015)

                # Get latest signal
                if long.iloc[-1]:
                    signals.append(
                        {
                            "symbol": symbol,
                            "strategy": strat_name,
                            "signal_type": "LONG",
                            "entry_price": float(df["Close"].iloc[-1]),
                            "take_profit": float(df["Close"].iloc[-1] * (1 + tp)),
                            "stop_loss": float(df["Close"].iloc[-1] * (1 - sl)),
                            "confidence": 0.75,
                            "source": "mega_strategies",
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        }
                    )
                elif short.iloc[-1]:
                    signals.append(
                        {
                            "symbol": symbol,
                            "strategy": strat_name,
                            "signal_type": "SHORT",
                            "entry_price": float(df["Close"].iloc[-1]),
                            "take_profit": float(df["Close"].iloc[-1] * (1 - tp)),
                            "stop_loss": float(df["Close"].iloc[-1] * (1 + sl)),
                            "confidence": 0.75,
                            "source": "mega_strategies",
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        }
                    )
            except Exception as e:
                logger.warning(f"Error running {strat_name} on {symbol}: {e}")
                continue

    return signals


# Integration points in the system
INTEGRATION_CONFIG = {
    # Add to scoring system strategy weights
    "strategy_weights": {
        "signal_price_volume_corr": 2.0,  # 100% WR -> 2.0x weight
        "signal_open_interest": 1.9,  # 99.5% WR -> 1.9x weight
        "signal_bollinger_squeeze": 1.8,  # 92.9% WR -> 1.8x weight
        "signal_macd_histogram": 1.7,  # 86.6% WR -> 1.7x weight
        "signal_ema_crossover": 1.6,  # 84.4% WR -> 1.6x weight
        "signal_onchain_volume": 1.5,  # 81.2% WR -> 1.5x weight
        "signal_volume_atr_momentum": 1.4,  # 70.1% WR -> 1.4x weight
        "signal_heikin_ashi": 1.3,  # 65.8% WR -> 1.3x weight
        "signal_ttm_squeeze": 1.2,  # 62.0% WR -> 1.2x weight
        "signal_ichimoku": 1.1,  # 57.2% WR -> 1.1x weight
    },
    # Add to forward test pipeline
    "forward_test_eligible": [
        "signal_price_volume_corr",
        "signal_open_interest",
        "signal_bollinger_squeeze",
        "signal_macd_histogram",
        "signal_ema_crossover",
        "signal_onchain_volume",
    ],
    # Min WR threshold for live trading
    "min_win_rate": 0.60,
}


def load_integration_config():
    """Load config from repo ``config/mega_strategies_integration.json``."""
    config_path = os.path.join(REPO_DIR, "config", "mega_strategies_integration.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(INTEGRATION_CONFIG, f, indent=2)

    logger.info("Created integration config: %s", config_path)
    return INTEGRATION_CONFIG


def wire_to_scoring(signal):
    """Add MEGA strategy scoring boost to a pick."""
    strat = signal.get("strategy", "")
    config = load_integration_config()

    if strat in config.get("strategy_weights", {}):
        weight = config["strategy_weights"][strat]
        current_conf = signal.get("confidence", 0.5)

        # Boost confidence based on strategy performance
        signal["confidence"] = min(0.99, current_conf * weight)
        signal["mega_strategy"] = True
        signal["mega_weight"] = weight

        logger.info(
            f"Boosted {strat} confidence: {current_conf:.2f} -> {signal['confidence']:.2f}"
        )

    return signal


def is_forward_test_eligible(signal):
    """Check if pick is eligible for forward test."""
    config = load_integration_config()
    strat = signal.get("strategy", "")

    return strat in config.get("forward_test_eligible", [])


def main():
    config = load_integration_config()

    logger.info("=" * 60)
    logger.info("MEGA STRATEGIES INTEGRATOR")
    logger.info("=" * 60)
    logger.info(f"Top strategies: {len(TOP_STRATEGIES)}")
    logger.info(f"Strategy weights: {config['strategy_weights']}")
    logger.info(f"Forward test eligible: {config['forward_test_eligible']}")

    # Test symbols
    test_symbols = [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "BNBUSDT",
        "XRPUSDT",
        "DOGEUSDT",
        "ADAUSDT",
        "AVAXUSDT",
        "DOTUSDT",
        "LINKUSDT",
        "SHIBUSDT",
        "TRXUSDT",
        "MATICUSDT",
        "LTCUSDT",
        "ETCUSDT",
    ]

    # Generate signals
    strat_names = [s[0] for s in TOP_STRATEGIES]
    signals = generate_mega_signals(test_symbols, strat_names)

    logger.info(
        f"Generated {len(signals)} signals from top {len(strat_names)} strategies"
    )

    # Apply scoring boosts
    wired_signals = []
    for sig in signals:
        wired = wire_to_scoring(sig)
        if is_forward_test_eligible(wired):
            wired["forward_test_ready"] = True
        wired_signals.append(wired)

    # Save to same artifact as forward runner (dashboard + smart_picks)
    picks_path = os.path.join(REPO_DIR, "alpha_engine", "data", "mega_strategy_picks.json")
    os.makedirs(os.path.dirname(picks_path), exist_ok=True)

    _ts = datetime.utcnow().isoformat() + "Z"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": _ts,
                "picks": wired_signals,
                "signals": wired_signals,
                "config": config,
            },
            f,
            indent=2,
        )

    logger.info("Saved %d signals to %s", len(wired_signals), picks_path)

    # Post to redis bus
    try:
        import redis

        r = redis.Redis(host="localhost", port=6379)

        payload = {
            "event": "MEGA_STRATEGIES_WIRED",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "strategies_wired": len(strat_names),
            "signals_generated": len(signals),
            "forward_test_ready": len(
                [s for s in wired_signals if s.get("forward_test_ready")]
            ),
            "strategy_weights": config["strategy_weights"],
            "status": "wired_to_scoring",
        }

        r.publish("AntigravityUpdates", json.dumps(payload))
        r.set("last_mega_wired", json.dumps(payload))
        logger.info("Posted to redis: MEGA_STRATEGIES_WIRED")
    except Exception as e:
        logger.warning(f"Redis not available: {e}")

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("WIRED SIGNALS SUMMARY")
    logger.info("=" * 60)

    for sig in wired_signals[:10]:
        logger.info(
            f"  {sig['symbol']:10} | {sig['strategy']:25} | {sig['signal_type']:5} | conf: {sig['confidence']:.2f}"
        )

    return wired_signals


if __name__ == "__main__":
    main()
