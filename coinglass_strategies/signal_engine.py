"""Signal engine — runs all 13 strategies, deduplicates, emits picks."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from . import config
from .data_fetcher import fetch_all_ratios, fetch_funding_rate, fetch_current_price, fetch_atr
from . import ratio_store
from .strategies import (
    extreme_reversion,
    top_trader_divergence,
    ratio_momentum,
    cross_exchange_spread,
    leverage_adjusted,
    funding_confirmation,
    sentiment_index,
    spike_detection,
    calendar_spread,
    roll_yield,
    options_volatility,
    news_sentiment,
    risk_parity,
)
from .strategies.base import Signal

logger = logging.getLogger(__name__)

STRATEGIES = [
    ("S2-WhaleDivergence", top_trader_divergence),
    ("S1-ExtremeReversion", extreme_reversion),
    ("S6-FundingConfluence", funding_confirmation),
    ("S5-LeverageSqueeze", leverage_adjusted),
    ("S7-SentimentComposite", sentiment_index),
    ("S3-RatioMomentum", ratio_momentum),
    ("S8-SpikeDetector", spike_detection),
    ("S4-ExchangeSpread", cross_exchange_spread),
    ("S9-CalendarSpread", calendar_spread),
    ("S10-RollYield", roll_yield),
    ("S11-OptionsVolatility", options_volatility),
    ("S12-NewsSentiment", news_sentiment),
    ("S13-RiskParity", risk_parity),
]

ACTIVE_PICKS_PATH = config.DATA_DIR / "active_picks.json"


def fetch_and_store(symbol: str) -> Dict:
    ratios = fetch_all_ratios(symbol)
    funding = fetch_funding_rate(symbol)
    # Only store if we got data from at least one source
    if ratios.get("source") is not None:
        ratio_store.store_ratios(symbol, ratios, funding_rate=funding)
    return ratios


def run_strategies(symbol: str, current_ratios: Dict) -> List[Signal]:
    recent = ratio_store.get_recent_ratios(symbol, window_minutes=config.ZSCORE_WINDOW_MINUTES)
    signals = []
    for name, strategy_mod in STRATEGIES:
        try:
            if strategy_mod == cross_exchange_spread:
                sig = strategy_mod.run(symbol)
            else:
                sig = strategy_mod.run(symbol, recent, current_ratios)
            if sig:
                if sig.confidence < config.MIN_SIGNAL_CONFIDENCE:
                    logger.debug("[%s] %s -> filtered out (conf=%.3f < %.2f min)",
                                 name, symbol, sig.confidence, config.MIN_SIGNAL_CONFIDENCE)
                else:
                    signals.append(sig)
                    logger.info("[%s] %s -> %s %s (conf=%.3f)", name, symbol, sig.direction, sig.strategy, sig.confidence)
        except Exception as exc:
            logger.warning("[%s] %s failed: %s", name, symbol, exc)
    return signals


def deduplicate(signals: List[Signal]) -> List[Signal]:
    best = {}
    for sig in signals:
        key = f"{sig.symbol}_{sig.direction}"
        if key not in best or sig.confidence > best[key].confidence:
            best[key] = sig
    return list(best.values())


def add_price_levels(signals: List[Signal]):
    for sig in signals:
        price = fetch_current_price(sig.symbol)
        atr = fetch_atr(sig.symbol)
        if price is None or atr is None:
            continue
        sig.entry_price = price
        if sig.direction == "LONG":
            sig.take_profit = round(price + atr * config.TP_ATR_MULT, 2)
            sig.stop_loss = round(price - atr * config.SL_ATR_MULT, 2)
        else:
            sig.take_profit = round(price - atr * config.TP_ATR_MULT, 2)
            sig.stop_loss = round(price + atr * config.SL_ATR_MULT, 2)


def scan_all() -> List[Dict]:
    ratio_store.init_db()
    all_signals = []
    for symbol in config.SYMBOLS:
        logger.info("Scanning %s ...", symbol)
        current_ratios = fetch_and_store(symbol)
        if current_ratios.get("source") is None:
            logger.warning("No data for %s, skipping", symbol)
            continue
        signals = run_strategies(symbol, current_ratios)
        all_signals.extend(signals)
    deduped = deduplicate(all_signals)
    add_price_levels(deduped)
    for sig in deduped:
        ratio_store.store_signal(sig.to_dict())
    picks = [sig.to_dict() for sig in deduped if sig.entry_price > 0]
    try:
        from alpha_engine.feed_hygiene import sanitize_active_picks
    except ImportError:
        sanitize_active_picks = lambda picks, label="": picks
    picks = sanitize_active_picks(picks, "coinglass")
    ACTIVE_PICKS_PATH.write_text(json.dumps(picks, indent=2, default=str))
    logger.info("Wrote %d picks to %s", len(picks), ACTIVE_PICKS_PATH)
    return picks
