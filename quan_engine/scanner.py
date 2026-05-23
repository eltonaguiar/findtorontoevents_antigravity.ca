"""
QuanEngine Scanner — Main Entry Point
=======================================
GitHub Actions calls this every 30 min.

Pipeline:
  1. Fetch OHLCV for all symbols
  2. RegimeRouter classifies each symbol
  3. Activate correct strategy pool per regime
  4. QuanEnsemble votes on direction
  5. ModeDispatcher calculates TP/SL/mode
  6. RiskGate approves + sizes position
  7. ForwardTracker records + validates
  8. Export active_signals.json for dashboard
"""
import os
import sys
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from quan_engine import config
from quan_engine.regime_router import RegimeRouter
from quan_engine.ensemble_layer import QuanEnsemble, Vote
from quan_engine.mode_dispatcher import ModeDispatcher
from quan_engine.risk_gate import RiskGate
from quan_engine.forward_tracker import ForwardTracker
from quan_engine.strategy_pool import StrategyPool

# Binance symbol -> yfinance ticker mapping
_YF_MAP = {
    "BTCUSDT": "BTC-USD", "ETHUSDT": "ETH-USD", "SOLUSDT": "SOL-USD",
    "BNBUSDT": "BNB-USD", "DOGEUSDT": "DOGE-USD", "XRPUSDT": "XRP-USD",
    "ADAUSDT": "ADA-USD", "AVAXUSDT": "AVAX-USD", "DOTUSDT": "DOT-USD",
    # MATICUSDT removed 2026-04-23 — Polygon rebrand (MATIC→POL) left the
    # yfinance MATIC-USD feed frozen; see project_quan_engine_matic_positive_artifact.
    "LTCUSDT": "LTC-USD", "LINKUSDT": "LINK-USD",
    "UNIUSDT": "UNI-USD", "AAVEUSDT": "AAVE-USD", "ATOMUSDT": "ATOM-USD",
    "NEARUSDT": "NEAR-USD", "APTUSDT": "APT-USD", "SUIUSDT": "SUI-USD",
    "TONUSDT": "TON-USD", "ICPUSDT": "ICP-USD", "ARBUSDT": "ARB-USD",
    "OPUSDT": "OP-USD", "MKRUSDT": "MKR-USD", "INJUSDT": "INJ-USD",
    "FETUSDT": "FET-USD", "TIAUSDT": "TIA-USD", "SEIUSDT": "SEI-USD",
    "JUPUSDT": "JUP-USD", "WIFUSDT": "WIF-USD", "PEPEUSDT": "PEPE-USD",
    "FILUSDT": "FIL-USD", "TRXUSDT": "TRX-USD", "ETCUSDT": "ETC-USD",
    "ALGOUSDT": "ALGO-USD", "XLMUSDT": "XLM-USD", "VETUSDT": "VET-USD",
    "HBARUSDT": "HBAR-USD", "SANDUSDT": "SAND-USD", "MANAUSDT": "MANA-USD",
    "AXSUSDT": "AXS-USD",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("QuanEngine.Scanner")


# Map interval -> max staleness tolerated for the most-recent bar's timestamp
# (in hours). Pads each interval by ~4x to absorb yfinance/exchange lag and
# weekend halts. If the latest bar is older than this, the feed is stale.
_INTERVAL_STALENESS_HOURS = {
    "15m": 6,
    "1h": 24,
    "4h": 72,
    "1d": 168,  # 7 days — covers long weekends + holidays
}

# If the last N closes are all identical, the feed is frozen (delisted symbol,
# rebrand placeholder, etc.). Calibrated against the MATIC->POL artifact where
# 760 picks in 28 days all carried close=0.3794 — a single 5-bar block was
# enough signal in retrospect.
_FROZEN_TAIL_BARS = 5


def _is_feed_stale(df: pd.DataFrame, interval: str, *, _now=None) -> tuple[bool, str]:
    """Return (is_stale, reason) for a fetched OHLCV dataframe.

    Two checks:
      1. Last bar's timestamp is older than _INTERVAL_STALENESS_HOURS for the
         given interval. Catches delisted symbols whose feed simply stopped
         updating (e.g., yfinance `MATIC-USD` post-MATIC->POL rebrand).
      2. Last `_FROZEN_TAIL_BARS` closes are all bit-identical. Catches the
         case where a feed continues to emit bars but with frozen prices.

    Either condition returns (True, reason). Caller should drop the symbol.

    `_now` is for test-injection; defaults to UTC now.
    """
    from datetime import datetime, timezone, timedelta

    if df is None or df.empty:
        return False, ""  # Empty df handled by caller; not "stale" per se.

    # --- Check 1: last-bar age ---
    try:
        last_ts = df.index[-1]
        if hasattr(last_ts, "to_pydatetime"):
            last_ts = last_ts.to_pydatetime()
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)
        now = _now if _now is not None else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        age_hours = (now - last_ts).total_seconds() / 3600.0
        max_age = _INTERVAL_STALENESS_HOURS.get(interval, 24)
        if age_hours > max_age:
            return True, f"last-bar age {age_hours:.1f}h > {max_age}h tolerance for interval={interval}"
    except (AttributeError, TypeError, ValueError):
        # Index isn't a timestamp — skip this check rather than fail open.
        pass

    # --- Check 2: frozen tail (last N closes identical) ---
    if "close" in df.columns and len(df) >= _FROZEN_TAIL_BARS:
        tail = df["close"].tail(_FROZEN_TAIL_BARS).tolist()
        if len(set(tail)) == 1:
            return True, f"last {_FROZEN_TAIL_BARS} closes all = {tail[0]} (frozen feed)"

    return False, ""


def _fetch_klines_yfinance(symbol: str, interval: str = "1h", limit: int = 500) -> pd.DataFrame:
    """Fetch OHLCV via yfinance (works from any geo, including US GitHub Actions).

    Returns an empty DataFrame when the symbol is unknown, the request fails,
    or the feed is detected as stale (delisted symbol or frozen prices) per
    `_is_feed_stale`. The caller treats empty-df as "skip this symbol".
    """
    yf_ticker = _YF_MAP.get(symbol, symbol.replace("USDT", "-USD"))
    # Map interval: yfinance uses "1h", "1d", etc. — same as our format
    # For limit: yfinance needs a period. 500 bars of 1h ≈ 21 days
    period_map = {"1h": "25d", "4h": "60d", "1d": "2y", "15m": "7d"}
    period = period_map.get(interval, "25d")
    try:
        df = yf.download(yf_ticker, period=period, interval=interval, progress=False)
        if df is None or df.empty:
            return pd.DataFrame()
        # Flatten MultiIndex columns if present (yfinance 0.2.31+)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # Normalize column names to lowercase
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low",
                                "Close": "close", "Volume": "volume"})
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        if len(df) > limit:
            df = df.tail(limit)
        # Drop the symbol entirely if the feed looks dead. Prevents the kind
        # of MATIC-USD-frozen-at-$0.3794 artifact that polluted 760 picks.
        stale, reason = _is_feed_stale(df, interval)
        if stale:
            logger.warning(f"{symbol} ({yf_ticker}): stale feed detected — {reason}; dropping")
            return pd.DataFrame()
        return df
    except Exception as e:
        logger.warning(f"yfinance failed for {symbol} ({yf_ticker}): {e}")
        return pd.DataFrame()


def _fetch_klines_binance(symbol: str, interval: str = "1h", limit: int = 500) -> pd.DataFrame:
    """Fetch klines from Binance REST API (fallback, may fail from US runners)."""
    bases = [config.BINANCE_BASE] + getattr(config, "BINANCE_FALLBACK_URLS", [])
    last_err = None
    for base in bases:
        try:
            url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "QuanEngine/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = json.loads(resp.read().decode())
            df = pd.DataFrame(raw, columns=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "quote_volume", "trades", "taker_buy_base",
                "taker_buy_quote", "ignore",
            ])
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)
            df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
            df = df.set_index("timestamp")
            return df[["open", "high", "low", "close", "volume"]]
        except Exception as e:
            last_err = e
            continue
    logger.warning(f"Binance fallback failed for {symbol}: {last_err}")
    return pd.DataFrame()


def fetch_klines(symbol: str, interval: str = "1h", limit: int = 500) -> pd.DataFrame:
    """Fetch klines with full multi-tier failover."""
    from quan_engine.failover_system import fetch_klines_with_failover
    return fetch_klines_with_failover(symbol, interval, limit)


def fetch_fear_greed() -> int:
    """Fetch current Fear & Greed index."""
    try:
        req = urllib.request.Request(config.FEAR_GREED_URL)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return int(data["data"][0]["value"])
    except Exception:
        return 50  # Default to neutral


def compute_atr_pct(df: pd.DataFrame, period: int = 14) -> float:
    """Compute ATR as a percentage of current price."""
    if len(df) < period + 1:
        return 0.0

    high = df["high"].values
    low = df["low"].values
    close = df["close"].values

    tr = np.zeros(len(df))
    tr[0] = high[0] - low[0]
    for i in range(1, len(df)):
        tr[i] = max(high[i] - low[i],
                     abs(high[i] - close[i-1]),
                     abs(low[i] - close[i-1]))

    atr = np.mean(tr[-period:])
    current_price = close[-1]
    return (atr / current_price * 100) if current_price > 0 else 0.0


def run_scan():
    """Main scan loop."""
    logger.info("=" * 60)
    logger.info(f"QuanEngine Scan — {datetime.utcnow().isoformat()}")
    logger.info("=" * 60)

    # Initialize components
    router = RegimeRouter()
    ensemble = QuanEnsemble()
    dispatcher = ModeDispatcher()
    risk_gate = RiskGate()
    tracker = ForwardTracker()

    # Initialize strategy pools
    trending_pool = StrategyPool("TRENDING")
    mr_pool = StrategyPool("MEAN_REVERSION")
    prop_pool = StrategyPool("PROP")

    # Fetch Fear & Greed
    fng = fetch_fear_greed()
    logger.info(f"Fear & Greed: {fng}")

    # Inject F&G into contrarian strategy
    fgc = prop_pool.strategies.get("fear_greed_contrarian")
    if fgc and hasattr(fgc, "set_fear_greed"):
        fgc.set_fear_greed(fng)

    # Fetch BTC data for health check
    btc_df = fetch_klines("BTCUSDT", "1h", 500)

    # Validate existing active signals first
    closed = tracker.validate_active_signals()
    if closed:
        logger.info(f"Closed {len(closed)} signals: {closed}")

    new_signals = []

    for symbol in config.SYMBOLS:
        try:
            logger.info(f"--- Scanning {symbol} ---")

            # Fetch data
            df = fetch_klines(symbol, "1h", 500)
            if df.empty or len(df) < 200:
                logger.warning(f"{symbol}: insufficient data ({len(df)} bars)")
                continue

            # 1. Regime classification
            close_prices = df["close"].values
            regime = router.classify(close_prices)
            hurst_val = router._hurst._compute_hurst(
                close_prices[-config.HURST_WINDOW:]
            )
            logger.info(f"{symbol}: Regime={regime}, H={hurst_val:.3f}")

            # 2. Run ALL strategy pools — regime pool at full weight, others at 0.8x
            #    PROP pool always runs at full weight (always-on strategies)
            #    RANDOM regime: still run prop pool (prop firm can't sit idle)
            trending_votes = trending_pool.get_votes(df, symbol)
            mr_votes = mr_pool.get_votes(df, symbol)
            prop_votes = prop_pool.get_votes(df, symbol)

            if regime == "RANDOM":
                # In random regime, discount regime-specific strategies but keep prop
                for v in trending_votes + mr_votes:
                    if v["direction"] != "ABSTAIN":
                        v["confidence"] = v.get("confidence", 0) * 0.7
            elif regime == "TRENDING":
                for v in mr_votes:
                    if v["direction"] != "ABSTAIN":
                        v["confidence"] = v.get("confidence", 0) * 0.8
            else:
                for v in trending_votes:
                    if v["direction"] != "ABSTAIN":
                        v["confidence"] = v.get("confidence", 0) * 0.8

            votes_raw = trending_votes + mr_votes + prop_votes
            active_count = sum(1 for v in votes_raw if v["direction"] != "ABSTAIN")
            logger.info(f"{symbol}: {active_count} active votes out of {len(votes_raw)} total")

            # Convert to Vote objects
            votes = []
            for v in votes_raw:
                votes.append(Vote(
                    strategy=v["strategy"],
                    direction=v["direction"],
                    confidence=v.get("confidence", 0),
                    metadata={
                        "entry_price": v.get("entry_price"),
                        "take_profit": v.get("take_profit"),
                        "stop_loss": v.get("stop_loss"),
                        "reason": v.get("reason", ""),
                    }
                ))

            # 3. Ensemble voting
            active_votes = [v for v in votes if v.direction in ("BUY", "SELL")]
            logger.info(f"{symbol}: {len(active_votes)} active votes out of {len(votes)} total")
            signal = ensemble.vote(votes)
            if signal is None:
                logger.info(f"{symbol}: No consensus (need {config.CONSENSUS_THRESHOLD:.0%})")
                continue

            logger.info(
                f"{symbol}: CONSENSUS {signal.direction} "
                f"({signal.consensus_pct:.0%}, conf={signal.avg_confidence:.3f})"
            )

            # 3b. Contrarian guardrail: block signals into extremes
            #     Extreme fear  (F&G <= 25) -> block SHORT (market already oversold)
            #     Extreme greed (F&G >= 75) -> block LONG  (market already overbought)
            if fng <= 25 and signal.direction == "SELL":
                logger.info(
                    f"{symbol}: BLOCKED SHORT — F&G={fng} (extreme fear, market oversold)"
                )
                continue
            if fng >= 75 and signal.direction == "BUY":
                logger.info(
                    f"{symbol}: BLOCKED LONG — F&G={fng} (extreme greed, market overbought)"
                )
                continue

            # 4. Mode dispatch
            atr_pct = compute_atr_pct(df)
            atr_abs = df["close"].values[-1] * atr_pct / 100
            entry_price = df["close"].values[-1]

            setup = dispatcher.create_setup(
                symbol=symbol,
                direction=signal.direction,
                entry_price=entry_price,
                confidence=signal.avg_confidence,
                consensus_pct=signal.consensus_pct,
                strategies_agreed=[v.strategy for v in signal.votes if v.direction == signal.direction],
                atr=atr_abs,
                hurst_value=hurst_val,
                atr_pct=atr_pct,
            )

            logger.info(
                f"{symbol}: Mode={setup.mode}, TP={setup.take_profit:.4f}, "
                f"SL={setup.stop_loss:.4f}, R:R={setup.rr_ratio:.1f}"
            )

            # 5. Risk gate
            # Compute symbol returns for correlation check
            symbol_returns = {}
            for s in [symbol] + [p.symbol for p in risk_gate.active_positions]:
                sdf = fetch_klines(s, "1h", 50) if s != symbol else df
                if not sdf.empty:
                    symbol_returns[s] = sdf["close"].pct_change().dropna().values

            risk_result = risk_gate.evaluate(
                setup=setup,
                fear_greed=fng,
                btc_df=btc_df if not btc_df.empty else None,
                symbol_returns=symbol_returns,
            )

            if not risk_result["approved"]:
                logger.info(f"{symbol}: REJECTED — {risk_result['reason']}")
                continue

            logger.info(
                f"{symbol}: APPROVED — size={risk_result['position_size']:.4f}, "
                f"health={risk_result.get('health', 'N/A')}"
            )

            # 6. Record signal
            signal_id = tracker.record_signal(
                setup=setup,
                position_size=risk_result["position_size"],
                health=risk_result.get("health", "SAFE"),
            )
            risk_gate.add_position(setup)

            new_signals.append({
                "id": signal_id,
                "symbol": symbol,
                "direction": setup.direction,
                "mode": setup.mode,
                "entry_price": setup.entry_price,
                "take_profit": setup.take_profit,
                "stop_loss": setup.stop_loss,
                "confidence": setup.confidence,
                "consensus_pct": setup.consensus_pct,
                "position_size": risk_result["position_size"],
                "entry_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            })

        except Exception as e:
            logger.error(f"{symbol}: Error — {e}", exc_info=True)
            continue

    # 7. Export results
    output_path = tracker.export_active_json()
    logger.info(f"Exported active signals to {output_path}")

    # Summary
    logger.info("=" * 60)
    logger.info(f"Scan complete: {len(new_signals)} new signals")
    perf = tracker.compute_performance()
    logger.info(
        f"Performance: {perf.get('total_trades', 0)} total trades, "
        f"WR={perf.get('win_rate', 0):.1%}, "
        f"Sharpe={perf.get('sharpe', 0):.2f}, "
        f"PF={perf.get('profit_factor', 0):.2f}"
    )
    logger.info("=" * 60)

    tracker.close()

    # Run extended market analysis (next-best picks + full overview)
    try:
        from quan_engine.market_analysis import run_market_analysis
        logger.info("Running extended market analysis...")
        analysis = run_market_analysis()
        logger.info(
            f"Market analysis: {analysis['market_summary']['symbols_scanned']} pairs, "
            f"bias={analysis['market_summary']['market_bias']}, "
            f"next-best-buys={len(analysis.get('next_best_buys', []))}"
        )
    except Exception as e:
        logger.error(f"Market analysis failed (non-fatal): {e}", exc_info=True)

    return new_signals


if __name__ == "__main__":
    run_scan()
