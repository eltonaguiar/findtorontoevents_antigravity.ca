"""
External Signal Confluence — Deribit + Binance Contrarian + Free Data Feeds
confidence modifiers.

Fetches external market signals (options flow, crowd positioning, regime context)
and uses them to boost or penalize pick confidence. Does NOT generate new picks —
only modifies existing ones.

Signal sources:
  1. Deribit: Options P/C ratio, DVOL, futures basis -> composite BUY/SELL/NEUTRAL
  2. Binance Contrarian: Crowd L/S, taker momentum, smart money, OI squeeze, CB premium
  3. Free Data Feeds: Fear & Greed, funding rates, volume, BTC dominance, spreads,
     yield curve -> regime signals (BUY/SELL/NEUTRAL/AVOID/RISK_OFF/ALT_SEASON)

Usage in any system scanner:
    from shared.external_signals import fetch_external_signals, apply_external_confluence

    # At scan start (once per cycle):
    ext_signals = fetch_external_signals()

    # For each pick:
    pick = apply_external_confluence(pick, ext_signals)
    if pick is None:
        continue  # confidence dropped below 0.45, skip

Graceful degradation: if API calls fail, returns neutral signals (no modification).
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Timeout for external API calls (seconds)
EXTERNAL_TIMEOUT = 10

# Confidence modification thresholds
BOOST_BOTH_AGREE = 0.10       # +10% when both Deribit + Binance agree with direction
PENALTY_BOTH_DISAGREE = 0.15  # -15% when both disagree
MIN_CONFIDENCE_FLOOR = 0.45   # Skip pick if confidence drops below this

# Regime signal confidence modifiers (from free_data_feeds)
REGIME_BOOST_FEAR_BUY = 0.05    # +5% when F&G says BUY and pick is BUY (extreme fear contrarian)
REGIME_BOOST_FEAR_SELL = 0.05   # +5% when F&G says SELL and pick is SELL (extreme greed contrarian)
REGIME_PENALTY_AVOID = 0.08     # -8% when spread signal says AVOID (low liquidity)
REGIME_PENALTY_RISK_OFF = 0.05  # -5% when yield curve inverted or BTC dominance RISK_OFF
REGIME_BOOST_FUNDING = 0.04     # +4% when funding rate signal agrees with direction

# Symbol mapping: Battleground symbols -> Deribit currency + Binance contrarian symbol
# Deribit only has BTC and ETH; Binance contrarian covers BTC, ETH, SOL, XRP
DERIBIT_CURRENCY_MAP = {
    "BTCUSDT": "BTC",
    "ETHUSDT": "ETH",
    # SOL, XRP, etc. have no Deribit options — use BTC as market proxy
}

BINANCE_SYMBOL_MAP = {
    "BTCUSDT": "BTCUSDT",
    "ETHUSDT": "ETHUSDT",
    "SOLUSDT": "SOLUSDT",
    "XRPUSDT": "XRPUSDT",
    # Other pairs: use BTC composite as market-wide proxy
}


def _get_battleground_path():
    """Return the path to the battleground/ directory."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "battleground"
    )


def _import_deribit_signals():
    """Lazy import of battleground.deribit_signals module."""
    try:
        battleground_path = _get_battleground_path()
        if battleground_path not in sys.path:
            sys.path.insert(0, battleground_path)
        import deribit_signals
        return deribit_signals
    except ImportError as e:
        logger.warning(f"Could not import deribit_signals: {e}")
        return None


def _import_binance_contrarian():
    """Lazy import of battleground.binance_contrarian_signals module."""
    try:
        battleground_path = _get_battleground_path()
        if battleground_path not in sys.path:
            sys.path.insert(0, battleground_path)
        import binance_contrarian_signals
        return binance_contrarian_signals
    except ImportError as e:
        logger.warning(f"Could not import binance_contrarian_signals: {e}")
        return None


def _import_free_data_feeds():
    """Lazy import of battleground.free_data_feeds module."""
    try:
        battleground_path = _get_battleground_path()
        if battleground_path not in sys.path:
            sys.path.insert(0, battleground_path)
        import free_data_feeds
        return free_data_feeds
    except ImportError as e:
        logger.warning(f"Could not import free_data_feeds: {e}")
        return None


def fetch_external_signals():
    """Fetch Deribit, Binance contrarian, and free data feed regime signals.

    Call once per scan cycle.

    Returns dict with:
        {
            "deribit": {<generate_signals() output>} or None,
            "binance": {symbol: {<scan_symbol() output>}, ...} or None,
            "regime": {signal_name: {signal, value, reason}, ...} or None,
            "timestamp": "...",
            "errors": [...]
        }

    On failure, returns neutral structure (None values) — scanner continues normally.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    result = {
        "deribit": None,
        "binance": None,
        "regime": None,
        "timestamp": timestamp,
        "errors": [],
    }

    # --- Deribit signals ---
    try:
        deribit_mod = _import_deribit_signals()
        if deribit_mod is not None:
            # Temporarily override timeout if module supports it
            old_timeout = getattr(deribit_mod, 'TIMEOUT', 15)
            deribit_mod.TIMEOUT = EXTERNAL_TIMEOUT
            try:
                deribit_data = deribit_mod.generate_signals()
                result["deribit"] = deribit_data
                comp = deribit_data.get("signals", {}).get("composite_signal", "NEUTRAL")
                strength = deribit_data.get("signals", {}).get("composite_strength", 0)
                logger.info(f"[ExtSignals] Deribit: {comp} (strength={strength:+.3f})")
                print(f"  [ExtSignals] Deribit composite: {comp} (strength={strength:+.3f})")
            finally:
                deribit_mod.TIMEOUT = old_timeout
        else:
            result["errors"].append("deribit_signals module not available")
    except Exception as e:
        result["errors"].append(f"Deribit fetch failed: {str(e)[:200]}")
        logger.warning(f"[ExtSignals] Deribit fetch failed: {e}")
        print(f"  [ExtSignals] Deribit fetch failed (graceful skip): {e}")

    # --- Binance contrarian signals ---
    try:
        binance_mod = _import_binance_contrarian()
        if binance_mod is not None:
            # Override timeout
            old_timeout = getattr(binance_mod, 'TIMEOUT', 10)
            binance_mod.TIMEOUT = EXTERNAL_TIMEOUT
            try:
                binance_results = {}
                for symbol in binance_mod.SYMBOLS:
                    try:
                        sym_data = binance_mod.scan_symbol(symbol)
                        binance_results[symbol] = sym_data
                    except Exception as e:
                        result["errors"].append(f"Binance {symbol}: {str(e)[:100]}")
                        logger.warning(f"[ExtSignals] Binance {symbol} failed: {e}")
                result["binance"] = binance_results if binance_results else None
                if binance_results:
                    symbols_scanned = list(binance_results.keys())
                    composites = {
                        s: binance_results[s].get("signals", {}).get("composite", {}).get("signal", "?")
                        for s in symbols_scanned
                    }
                    print(f"  [ExtSignals] Binance contrarian: {composites}")
            finally:
                binance_mod.TIMEOUT = old_timeout
        else:
            result["errors"].append("binance_contrarian_signals module not available")
    except Exception as e:
        result["errors"].append(f"Binance fetch failed: {str(e)[:200]}")
        logger.warning(f"[ExtSignals] Binance fetch failed: {e}")
        print(f"  [ExtSignals] Binance fetch failed (graceful skip): {e}")

    # --- Free data feed regime signals ---
    try:
        feeds_mod = _import_free_data_feeds()
        if feeds_mod is not None:
            old_timeout = getattr(feeds_mod, 'TIMEOUT', 10)
            feeds_mod.TIMEOUT = EXTERNAL_TIMEOUT
            try:
                snapshot = feeds_mod.get_market_snapshot()
                regime_signals = feeds_mod.generate_regime_signals(snapshot)
                result["regime"] = regime_signals
                # Log key regime signals
                active_regimes = [
                    f"{name}={sig.get('signal', '?')}"
                    for name, sig in regime_signals.items()
                    if sig.get("signal") not in ("NEUTRAL", "GOOD", "NO_DATA")
                ]
                if active_regimes:
                    print(f"  [ExtSignals] Regime signals: {', '.join(active_regimes)}")
                else:
                    print(f"  [ExtSignals] Regime signals: all neutral")
            finally:
                feeds_mod.TIMEOUT = old_timeout
        else:
            result["errors"].append("free_data_feeds module not available")
    except Exception as e:
        result["errors"].append(f"Regime feeds fetch failed: {str(e)[:200]}")
        logger.warning(f"[ExtSignals] Regime feeds fetch failed: {e}")
        print(f"  [ExtSignals] Regime feeds fetch failed (graceful skip): {e}")

    if result["errors"]:
        print(f"  [ExtSignals] Warnings: {result['errors']}")

    return result


def _get_deribit_direction(ext_signals, symbol):
    """Extract Deribit composite direction for a given symbol.

    Returns: "BUY", "SELL", or "NEUTRAL"
    """
    deribit = ext_signals.get("deribit")
    if deribit is None:
        return "NEUTRAL"

    signals = deribit.get("signals", {})
    composite = signals.get("composite_signal", "NEUTRAL")

    # Deribit only covers BTC/ETH. For other symbols, use BTC as market proxy.
    currency = DERIBIT_CURRENCY_MAP.get(symbol)
    if currency is None:
        # Use BTC composite as market-wide proxy for non-BTC/ETH pairs
        return composite

    # For ETH specifically, check if ETH-specific metrics diverge significantly
    # from BTC. If they don't, just use the BTC-based composite (which is what
    # generate_signals() already returns).
    return composite


def _get_binance_direction(ext_signals, symbol):
    """Extract Binance contrarian composite direction for a given symbol.

    Returns: "LONG", "SHORT", or "neutral"
    """
    binance = ext_signals.get("binance")
    if binance is None:
        return "neutral"

    # Direct match
    mapped_symbol = BINANCE_SYMBOL_MAP.get(symbol, symbol)
    if mapped_symbol in binance:
        sym_data = binance[mapped_symbol]
        composite = sym_data.get("signals", {}).get("composite", {})
        return composite.get("signal", "neutral")

    # Fallback: use BTCUSDT as market proxy
    if "BTCUSDT" in binance:
        btc_data = binance["BTCUSDT"]
        composite = btc_data.get("signals", {}).get("composite", {})
        return composite.get("signal", "neutral")

    return "neutral"


def _normalize_direction(signal_type):
    """Normalize pick direction to comparable format.

    Pick signal_type is "BUY" or "SELL".
    Deribit uses "BUY"/"SELL"/"NEUTRAL".
    Binance uses "LONG"/"SHORT"/"neutral"/"SQUEEZE".
    """
    s = str(signal_type).upper()
    if s in ("BUY", "LONG"):
        return "BULLISH"
    elif s in ("SELL", "SHORT"):
        return "BEARISH"
    return "NEUTRAL"


def apply_external_confluence(pick, ext_signals):
    """Apply external signal confluence to a single pick.

    Modifies pick confidence based on Deribit + Binance agreement/disagreement:
      - Both agree with pick direction  -> confidence += 0.10 (boost)
      - Both disagree                   -> confidence -= 0.15 (penalty)
      - Mixed signals                   -> no change

    Adds metadata fields:
      - deribit_signal: str ("BUY"/"SELL"/"NEUTRAL")
      - binance_contrarian_signal: str ("LONG"/"SHORT"/"neutral")
      - external_confluence: str ("AGREE"/"DISAGREE"/"MIXED"/"UNAVAILABLE")

    Returns:
      - Modified pick dict (mutated in-place), or
      - None if confidence drops below MIN_CONFIDENCE_FLOOR (pick should be skipped)
    """
    if ext_signals is None:
        pick["deribit_signal"] = "UNAVAILABLE"
        pick["binance_contrarian_signal"] = "UNAVAILABLE"
        pick["external_confluence"] = "UNAVAILABLE"
        return pick

    symbol = pick.get("symbol", "")
    pick_direction = _normalize_direction(pick.get("signal_type", "BUY"))

    # Get external directions
    deribit_raw = _get_deribit_direction(ext_signals, symbol)
    binance_raw = _get_binance_direction(ext_signals, symbol)

    deribit_dir = _normalize_direction(deribit_raw)
    binance_dir = _normalize_direction(binance_raw)

    # Store raw signals as metadata
    pick["deribit_signal"] = deribit_raw
    pick["binance_contrarian_signal"] = binance_raw

    # Determine confluence
    deribit_agrees = (deribit_dir == pick_direction) if deribit_dir != "NEUTRAL" else None
    binance_agrees = (binance_dir == pick_direction) if binance_dir != "NEUTRAL" else None

    original_confidence = pick.get("confidence", 0.5)

    if deribit_agrees is True and binance_agrees is True:
        # Both external sources agree with pick direction -> boost
        pick["external_confluence"] = "AGREE"
        new_confidence = min(original_confidence + BOOST_BOTH_AGREE, 1.0)
        pick["confidence"] = round(new_confidence, 4)
        print(f"    [ExtConfl] {symbol}: BOTH AGREE with {pick.get('signal_type','?')} "
              f"-> confidence {original_confidence:.3f} -> {new_confidence:.3f} (+{BOOST_BOTH_AGREE})")

    elif deribit_agrees is False and binance_agrees is False:
        # Both external sources disagree with pick direction -> penalty
        pick["external_confluence"] = "DISAGREE"
        new_confidence = original_confidence - PENALTY_BOTH_DISAGREE
        pick["confidence"] = round(new_confidence, 4)
        print(f"    [ExtConfl] {symbol}: BOTH DISAGREE with {pick.get('signal_type','?')} "
              f"(Deribit={deribit_raw}, Binance={binance_raw}) "
              f"-> confidence {original_confidence:.3f} -> {new_confidence:.3f} (-{PENALTY_BOTH_DISAGREE})")

        if new_confidence < MIN_CONFIDENCE_FLOOR:
            print(f"    [ExtConfl] {symbol}: SKIPPED — confidence {new_confidence:.3f} < floor {MIN_CONFIDENCE_FLOOR}")
            return None
    else:
        # Mixed or neutral signals -> no change
        pick["external_confluence"] = "MIXED"
        # Log only when at least one source has a directional opinion
        if deribit_dir != "NEUTRAL" or binance_dir != "NEUTRAL":
            print(f"    [ExtConfl] {symbol}: MIXED (Deribit={deribit_raw}, Binance={binance_raw}) "
                  f"-> confidence unchanged ({original_confidence:.3f})")

    # --- Regime signal modifiers (from free_data_feeds) ---
    regime = ext_signals.get("regime")
    regime_adj = 0.0
    regime_notes = []

    if regime:
        pick_dir = pick.get("signal_type", "BUY")

        # Fear & Greed: extreme fear favors BUY (contrarian), extreme greed favors SELL
        fg_sig = regime.get("fear_greed_signal", {})
        fg_direction = fg_sig.get("signal", "NEUTRAL")
        if fg_direction == "BUY" and pick_dir == "BUY":
            regime_adj += REGIME_BOOST_FEAR_BUY
            regime_notes.append(f"F&G={fg_sig.get('value','?')}->BUY_boost")
        elif fg_direction == "SELL" and pick_dir == "SELL":
            regime_adj += REGIME_BOOST_FEAR_SELL
            regime_notes.append(f"F&G={fg_sig.get('value','?')}->SELL_boost")

        # Funding rate: negative funding + BUY = squeeze potential (boost)
        #               positive funding + SELL = squeeze potential (boost)
        fund_sig = regime.get("funding_signal", {})
        fund_direction = fund_sig.get("signal", "NEUTRAL")
        if fund_direction == "BUY" and pick_dir == "BUY":
            regime_adj += REGIME_BOOST_FUNDING
            regime_notes.append(f"funding={fund_sig.get('value','?')}->BUY_boost")
        elif fund_direction == "SELL" and pick_dir == "SELL":
            regime_adj += REGIME_BOOST_FUNDING
            regime_notes.append(f"funding={fund_sig.get('value','?')}->SELL_boost")

        # Spread signal: AVOID = low liquidity, penalize all directions
        spread_sig = regime.get("spread_signal", {})
        if spread_sig.get("signal") == "AVOID":
            regime_adj -= REGIME_PENALTY_AVOID
            regime_notes.append(f"spread=AVOID({spread_sig.get('value',0)}bps)")

        # Yield curve / dominance: RISK_OFF penalizes BUY (risk-on) trades
        yc_sig = regime.get("yield_curve_signal", {})
        dom_sig = regime.get("dominance_signal", {})
        if yc_sig.get("signal") == "RISK_OFF" and pick_dir == "BUY":
            regime_adj -= REGIME_PENALTY_RISK_OFF
            regime_notes.append("yield_curve=RISK_OFF")
        if dom_sig.get("signal") == "RISK_OFF" and pick_dir == "BUY":
            regime_adj -= REGIME_PENALTY_RISK_OFF
            regime_notes.append("dominance=RISK_OFF")

    # Apply regime adjustment
    if regime_adj != 0.0:
        pre_regime_conf = pick.get("confidence", 0.5)
        new_conf = max(0.0, min(1.0, pre_regime_conf + regime_adj))
        pick["confidence"] = round(new_conf, 4)
        pick["regime_adjustment"] = round(regime_adj, 4)
        print(f"    [Regime] {symbol}: {', '.join(regime_notes)} "
              f"-> confidence {pre_regime_conf:.3f} -> {new_conf:.3f} ({regime_adj:+.3f})")

        if new_conf < MIN_CONFIDENCE_FLOOR:
            print(f"    [Regime] {symbol}: SKIPPED — confidence {new_conf:.3f} < floor {MIN_CONFIDENCE_FLOOR}")
            return None
    else:
        pick["regime_adjustment"] = 0.0

    pick["regime_signals_used"] = regime_notes if regime_notes else []

    # Also update pick_reason if present
    if "pick_reason" in pick:
        regime_str = f", Regime=[{', '.join(regime_notes)}]" if regime_notes else ""
        pick["pick_reason"] += (
            f" | ExtConfl={pick['external_confluence']}"
            f" (Deribit={deribit_raw}, Binance={binance_raw}{regime_str})"
        )

    return pick


def apply_external_confluence_batch(picks, ext_signals):
    """Apply external confluence to a list of picks.

    Returns filtered list (picks with confidence below floor are removed).
    """
    if not picks:
        return picks

    result = []
    skipped = 0
    for pick in picks:
        modified = apply_external_confluence(pick, ext_signals)
        if modified is not None:
            result.append(modified)
        else:
            skipped += 1

    if skipped > 0:
        print(f"  [ExtConfl] Batch result: {len(result)} kept, {skipped} skipped (below confidence floor)")

    return result


def log_external_signals_summary(ext_signals):
    """Log a summary of external signals for audit trail. Call at scan start."""
    if ext_signals is None:
        print("  [ExtSignals] External signals: UNAVAILABLE (all APIs failed)")
        return

    lines = ["  [ExtSignals] === External Signal Summary ==="]

    # Deribit summary
    deribit = ext_signals.get("deribit")
    if deribit:
        sigs = deribit.get("signals", {})
        lines.append(
            f"  [ExtSignals]   Deribit: composite={sigs.get('composite_signal','?')} "
            f"(str={sigs.get('composite_strength', 0):+.3f}) | "
            f"DVOL={sigs.get('dvol_signal','?')}, P/C={sigs.get('put_call_signal','?')}, "
            f"Basis={sigs.get('basis_signal','?')}"
        )
        lines.append(
            f"  [ExtSignals]   BTC: spot=${deribit.get('btc_spot_price', 0):,.0f}, "
            f"DVOL={deribit.get('btc_dvol', 0):.1f}, "
            f"P/C={deribit.get('btc_put_call_ratio', 0):.3f}, "
            f"basis={deribit.get('btc_futures_basis_annualized', 0):+.1f}%"
        )
    else:
        lines.append("  [ExtSignals]   Deribit: UNAVAILABLE")

    # Binance summary
    binance = ext_signals.get("binance")
    if binance:
        for sym, data in binance.items():
            comp = data.get("signals", {}).get("composite", {})
            squeeze = " [SQUEEZE]" if comp.get("squeeze_warning") else ""
            lines.append(
                f"  [ExtSignals]   Binance {sym}: composite={comp.get('signal','?')} "
                f"(str={comp.get('strength', 0):+.3f}){squeeze}"
            )
    else:
        lines.append("  [ExtSignals]   Binance: UNAVAILABLE")

    # Regime signals (free data feeds)
    regime = ext_signals.get("regime")
    if regime:
        active_regimes = []
        for name, sig in sorted(regime.items()):
            signal = sig.get("signal", "?")
            value = sig.get("value", "?")
            if signal not in ("NEUTRAL", "GOOD", "NO_DATA"):
                active_regimes.append(f"{name}={signal}({value})")
        if active_regimes:
            lines.append(f"  [ExtSignals]   Regime: {', '.join(active_regimes)}")
        else:
            lines.append("  [ExtSignals]   Regime: all neutral")
    else:
        lines.append("  [ExtSignals]   Regime: UNAVAILABLE")

    # Errors
    errors = ext_signals.get("errors", [])
    if errors:
        lines.append(f"  [ExtSignals]   Errors: {errors}")

    lines.append("  [ExtSignals] ================================")

    for line in lines:
        print(line)
