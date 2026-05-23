#!/usr/bin/env python3
"""
ANTIGRAVITY STRATEGIES -- Scanner Adapters
==========================================
Wraps Google Antigravity (Gemini) baby_strategies into the alpha_engine
scanner calling convention: fn(data, context) -> list[dict].

Strategies from baby_strategies/:
  - vwap_rsi_institutional (65-72% WR)
  - liquidation_cascade_contrarian (58-65% WR)
  - regime_sentinel_composite (meta-filter, +10-15% WR boost)
  - rsi_pairs_arbitrage (70-78% WR)
"""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

# Ensure baby_strategies is importable
_repo = Path(__file__).resolve().parent.parent
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

import pandas as pd

# ---------------------------------------------------------------------------
# Symbols to scan per strategy
# ---------------------------------------------------------------------------
CRYPTO_SYMBOLS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "DOGE-USD", "ADA-USD", "AVAX-USD", "TRX-USD", "DOT-USD",
    "LINK-USD", "LTC-USD", "BCH-USD", "SHIB-USD", "SUI-USD",
    "INJ-USD", "NEAR-USD", "HBAR-USD", "ARB11841-USD", "OP-USD",
    "FET-USD", "TIA-USD", "SEI-USD", "AAVE-USD", "ETC-USD",
]

# Pairs for RSI pairs arbitrage (correlated pairs)
PAIRS = [
    ("BTC-USD", "ETH-USD"),
    ("BTC-USD", "SOL-USD"),
    ("ETH-USD", "SOL-USD"),
    ("LINK-USD", "AVAX-USD"),
    ("ADA-USD", "DOT-USD"),
]


def _signal_to_dict(sig, strategy_name: str, category: str = "crypto") -> dict:
    """Convert baby_strategy Signal dataclass OR plain dict to scanner dict format.

    2026-04-14: Some baby_strategies (keltner_channel_reversion,
    williams_percent_r_extreme — see issue #197) return plain dicts with
    different field names than the canonical Signal dataclass:
        dict shape:      {symbol, side,      entry_price, take_profit, stop_loss, strength,    reason, strategy}
        dataclass shape: Signal(symbol, direction, entry_price, take_profit, stop_loss, confidence, reason, ...)

    Normalize both to a common namespace before the rest of the conversion.
    Existing dataclass-based strategies (vwap_rsi, liquidation_cascade, etc.)
    are unaffected — the isinstance check is False for them.
    """
    if isinstance(sig, dict):
        from types import SimpleNamespace

        sig = SimpleNamespace(
            direction=sig.get("direction") or sig.get("side") or "",
            entry_price=sig.get("entry_price", 0),
            take_profit=sig.get("take_profit", 0),
            stop_loss=sig.get("stop_loss", 0),
            confidence=sig.get("confidence") if sig.get("confidence") is not None else sig.get("strength", 0.5),
            symbol=sig.get("symbol", ""),
            reason=sig.get("reason", ""),
        )

    direction = str(sig.direction).upper()
    if direction in ("BUY", "LONG"):
        signal_type = "BUY"
    elif direction in ("SELL", "SHORT"):
        signal_type = "SELL"
    else:
        return {}

    entry = float(sig.entry_price)
    tp = float(sig.take_profit)
    sl = float(sig.stop_loss)
    rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

    return {
        "symbol": sig.symbol,
        "signal": signal_type,
        "strategy": strategy_name,
        "confidence": float(sig.confidence),
        "entry_price": entry,
        "take_profit": tp,
        "stop_loss": sl,
        "risk_reward": round(rr, 2),
        "category": category,
        "timeframe": "1h",
        "source": "antigravity",
        "extra": {"reason": sig.reason},
    }


# ---------------------------------------------------------------------------
# Shared asset-class inference (delegates to canonical alpha_engine.asset_class).
# Post-swarm-review fix 2026-05-21: replaced naive substring matching that
# misclassified SOL (Renesola stock→CRYPTO), EURO (Euro Tech→FOREX),
# TLT/BND (bond ETF→ETF instead of BOND). Now delegates to the same
# canonical frozenset-based classifier used by smart_picks_engine and
# conviction_stack. No reimplementation — single source of truth.
# Used for vt_pattern_sweep + vt_thematic + future EQUITY babies for consistent naming.
# ---------------------------------------------------------------------------
def _infer_asset_class(symbol: str) -> str:
    """Asset-class inference delegating to canonical alpha_engine.asset_class.

    Returns UPPERCASE: "BOND", "ETF", "EQUITY", "CRYPTO", "FOREX", "COMMODITY", "UNKNOWN".
    Uses the same frozenset-based classifier as the rest of the pipeline,
    with a pre-check for Yahoo Finance crypto convention (-USD suffix).
    """
    if not symbol:
        return "UNKNOWN"
    s = str(symbol).upper().strip()

    # Yahoo Finance crypto convention (BTC-USD, ETH-USD, SOL-USD, etc.)
    # This module's data pipeline sources from Yahoo Finance and uses
    # the -USD suffix for all crypto pairs. Not in canonical because
    # the main pipeline normalizes symbols differently (USDT suffixes).
    if "-USD" in s:
        return "CRYPTO"

    # Delegate to canonical single source of truth — avoids substring
    # false positives (SOL→CRYPTO, EURO→FOREX, TLT/BND→ETF-not-BOND)
    # flagged by swarm review 2026-05-21.
    from alpha_engine.asset_class import asset_class_from_symbol
    raw = asset_class_from_symbol(str(symbol))
    # Normalize output: the canonical function returns lowercase, but
    # callers of _infer_asset_class expect UPPERCASE for consistency
    # with resolved_picks asset_class tags.
    map_lower_to_upper = {
        "crypto": "CRYPTO",
        "forex": "FOREX",
        "futures": "COMMODITY",  # canonical uses "futures", pipeline uses "COMMODITY"
        "bond": "BOND",
        "etf": "ETF",
        "equity": "EQUITY",
    }
    return map_lower_to_upper.get(raw, "UNKNOWN")


# ---------------------------------------------------------------------------
# 1. VWAP-RSI Institutional
# ---------------------------------------------------------------------------
def ag_vwap_rsi_institutional(data: dict, context: dict = None) -> list[dict]:
    """Antigravity: VWAP + Triple RSI(14/21/50) institutional confluence."""
    try:
        from baby_strategies.vwap_rsi_institutional import VWAPRSIInstitutionalStrategy
    except ImportError:
        return []

    strategy = VWAPRSIInstitutionalStrategy()
    results = []

    for sym, df in data.items():
        if not isinstance(df, pd.DataFrame) or len(df) < 60:
            continue
        # Only process crypto symbols
        sym_upper = sym.upper()
        if not any(c in sym_upper for c in ["BTC", "ETH", "SOL", "BNB", "XRP",
                                              "ADA", "AVAX", "LINK", "DOT", "DOGE"]):
            continue

        try:
            signals = strategy.generate_signals(df, symbol=sym)
            for sig in signals:
                d = _signal_to_dict(sig, "ag_vwap_rsi_institutional", "crypto")
                if d:
                    d["symbol"] = sym  # preserve original symbol format
                    results.append(d)
        except Exception:
            continue

    return results


# ---------------------------------------------------------------------------
# 2. Liquidation Cascade Contrarian
# ---------------------------------------------------------------------------
def ag_liquidation_cascade_contrarian(data: dict, context: dict = None) -> list[dict]:
    """Antigravity: Post-cascade wick recovery bounce."""
    try:
        from baby_strategies.liquidation_cascade_contrarian import LiquidationCascadeContrarianStrategy
    except ImportError:
        return []

    strategy = LiquidationCascadeContrarianStrategy()
    results = []

    for sym, df in data.items():
        if not isinstance(df, pd.DataFrame) or len(df) < 60:
            continue
        sym_upper = sym.upper()
        if not any(c in sym_upper for c in ["BTC", "ETH", "SOL", "BNB", "XRP",
                                              "ADA", "AVAX", "LINK", "DOT", "DOGE"]):
            continue

        try:
            signals = strategy.generate_signals(df, symbol=sym)
            for sig in signals:
                d = _signal_to_dict(sig, "ag_liquidation_cascade_contrarian", "crypto")
                if d:
                    d["symbol"] = sym
                    results.append(d)
        except Exception:
            continue

    return results


# ---------------------------------------------------------------------------
# 3. Regime Sentinel Composite (meta-filter)
# ---------------------------------------------------------------------------
def ag_regime_sentinel_composite(data: dict, context: dict = None) -> list[dict]:
    """Antigravity: 4-state regime classifier + directional signal."""
    try:
        from baby_strategies.regime_sentinel_composite import RegimeSentinelCompositeStrategy
    except ImportError:
        return []

    strategy = RegimeSentinelCompositeStrategy()
    results = []

    for sym, df in data.items():
        if not isinstance(df, pd.DataFrame) or len(df) < 100:
            continue
        sym_upper = sym.upper()
        if not any(c in sym_upper for c in ["BTC", "ETH", "SOL", "BNB", "XRP",
                                              "ADA", "AVAX", "LINK", "DOT", "DOGE"]):
            continue

        try:
            signals = strategy.generate_signals(df, symbol=sym)
            for sig in signals:
                d = _signal_to_dict(sig, "ag_regime_sentinel_composite", "crypto")
                if d:
                    d["symbol"] = sym
                    results.append(d)
        except Exception:
            continue

    return results


# ---------------------------------------------------------------------------
# 4. RSI Pairs Arbitrage
# ---------------------------------------------------------------------------
def ag_rsi_pairs_arbitrage(data: dict, context: dict = None) -> list[dict]:
    """Antigravity: Market-neutral RSI spread reversion on correlated pairs."""
    try:
        from baby_strategies.rsi_pairs_arbitrage import RSIPairsArbitrageStrategy
    except ImportError:
        return []

    strategy = RSIPairsArbitrageStrategy()
    results = []

    for sym_a, sym_b in PAIRS:
        df_a = data.get(sym_a)
        df_b = data.get(sym_b)
        if df_a is None or df_b is None:
            continue
        if not isinstance(df_a, pd.DataFrame) or len(df_a) < 60:
            continue

        try:
            # RSI pairs strategy may use the primary symbol's data
            # and look for the pair internally
            signals = strategy.generate_signals(df_a, symbol=sym_a)
            for sig in signals:
                d = _signal_to_dict(sig, "ag_rsi_pairs_arbitrage", "crypto")
                if d:
                    d["symbol"] = sym_a
                    d["extra"]["pair"] = sym_b
                    results.append(d)
        except Exception:
            continue

    return results


# ---------------------------------------------------------------------------
# 5. Moving Average Slope Momentum (Fibonacci EMA slopes 5/13/34)
# ---------------------------------------------------------------------------
def ag_moving_average_slope_momentum(data: dict, context: dict = None) -> list[dict]:
    """Antigravity: Triple EMA slope with Fibonacci periods (5, 13, 34).

    Promoted 2026-04-14 from baby_strategies (PR #194 meta status update).
    Entry: all slopes same direction + hierarchy + acceleration.
    Direction: LONG and SHORT.
    """
    try:
        from baby_strategies.moving_average_slope_momentum import (
            MovingAverageSlopeMomentumStrategy,
        )
    except ImportError:
        return []

    strategy = MovingAverageSlopeMomentumStrategy()
    results = []

    for sym, df in data.items():
        if not isinstance(df, pd.DataFrame) or len(df) < 60:
            continue
        sym_upper = sym.upper()
        if not any(
            c in sym_upper
            for c in ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "LINK", "DOT", "DOGE"]
        ):
            continue

        try:
            signals = strategy.generate_signals(df, symbol=sym)
            for sig in signals:
                d = _signal_to_dict(sig, "ag_moving_average_slope_momentum", "crypto")
                if d:
                    d["symbol"] = sym
                    results.append(d)
        except Exception:
            continue

    return results


# ---------------------------------------------------------------------------
# 6. Multi-Timeframe EMA Cloud (4-layer cloud + HTF alignment)
# ---------------------------------------------------------------------------
def ag_multi_timeframe_ema_cloud(data: dict, context: dict = None) -> list[dict]:
    """Antigravity: 4-layer EMA cloud with MTF trend alignment.

    Promoted 2026-04-14 from baby_strategies (PR #194 meta status update).
    Entry: price above all EMAs + cloud expanding + HTF trend aligned.
    Direction: LONG and SHORT.
    """
    try:
        from baby_strategies.multi_timeframe_ema_cloud import (
            MultiTimeframeEMACloudStrategy,
        )
    except ImportError:
        return []

    strategy = MultiTimeframeEMACloudStrategy()
    results = []

    for sym, df in data.items():
        if not isinstance(df, pd.DataFrame) or len(df) < 60:
            continue
        sym_upper = sym.upper()
        if not any(
            c in sym_upper
            for c in ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "LINK", "DOT", "DOGE"]
        ):
            continue

        try:
            signals = strategy.generate_signals(df, symbol=sym)
            for sig in signals:
                d = _signal_to_dict(sig, "ag_multi_timeframe_ema_cloud", "crypto")
                if d:
                    d["symbol"] = sym
                    results.append(d)
        except Exception:
            continue

    return results


# ---------------------------------------------------------------------------
# 7. Vol-Scaled Keltner (Keltner breakout + volume percentile + trend filter)
# ---------------------------------------------------------------------------
def ag_vol_scaled_keltner(data: dict, context: dict = None) -> list[dict]:
    """Antigravity: Keltner upper-band break with volume percentile + EMA trend filter.

    Promoted 2026-04-14 from baby_strategies (PR #194 meta status update).
    Entry: price breaks upper Keltner + EMA50>EMA200 + volume > 70th percentile.
    Needs 210+ bars (EMA200 warmup); min-bar check matches strategy body.
    Direction: LONG only.
    """
    try:
        from baby_strategies.vol_scaled_keltner import VolScaledKeltnerStrategy
    except ImportError:
        return []

    strategy = VolScaledKeltnerStrategy()
    results = []

    for sym, df in data.items():
        if not isinstance(df, pd.DataFrame) or len(df) < 210:
            continue
        sym_upper = sym.upper()
        if not any(
            c in sym_upper
            for c in ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "LINK", "DOT", "DOGE"]
        ):
            continue

        try:
            signals = strategy.generate_signals(df, symbol=sym)
            for sig in signals:
                d = _signal_to_dict(sig, "ag_vol_scaled_keltner", "crypto")
                if d:
                    d["symbol"] = sym
                    results.append(d)
        except Exception:
            continue

    return results


# ---------------------------------------------------------------------------
# 8. VT ADX + RSI(2) on US ETFs (2026-04-14 vibe-trading ship, lowest-DD)
# ---------------------------------------------------------------------------
def ag_vt_adx_rsi2_etf(data: dict, context: dict = None) -> list[dict]:
    """Vibe-Trading mega V2: ADX trend + RSI(2) pullback on SPY/QQQ/XLK.

    5yr: 179 trades, Sharpe 0.250, PF 1.14, WR 55%, MaxDD -10.2% (lowest DD
    of any positive-Sharpe mega V2 run). ~36 picks/year.
    """
    try:
        from baby_strategies.vt_adx_rsi2_etf import VTADXRsi2ETFStrategy
    except ImportError:
        return []
    strategy = VTADXRsi2ETFStrategy()
    results = []
    etf_symbols = {"SPY", "QQQ", "XLK"}
    for sym, df in data.items():
        if not isinstance(df, pd.DataFrame) or len(df) < 120:
            continue
        if sym.upper() not in etf_symbols:
            continue
        try:
            signals = strategy.generate_signals(df, symbol=sym)
            for sig in signals:
                d = _signal_to_dict(sig, "ag_vt_adx_rsi2_etf", "etf")
                if d:
                    d["symbol"] = sym
                    d["extra"]["source_tool"] = "vibe-trading-mcp"
                    results.append(d)
        except Exception:
            continue
    return results


# ---------------------------------------------------------------------------
# 9. VT ADX + RSI(2) on US mega-cap Equity (highest frequency, 2026-04-14)
# ---------------------------------------------------------------------------
def ag_vt_adx_rsi2_equity(data: dict, context: dict = None) -> list[dict]:
    """Vibe-Trading mega V2: ADX trend + RSI(2) pullback on AAPL/MSFT/NVDA.

    5yr: 216 trades (highest count of any mega V2 run), Sharpe 0.328, PF 1.16,
    WR 53%, MaxDD -20.5%. ~43 picks/year. Signal overlay framing.
    """
    try:
        from baby_strategies.vt_adx_rsi2_equity import VTADXRsi2EquityStrategy
    except ImportError:
        return []
    strategy = VTADXRsi2EquityStrategy()
    results = []
    equity_symbols = {"AAPL", "MSFT", "NVDA"}
    for sym, df in data.items():
        if not isinstance(df, pd.DataFrame) or len(df) < 120:
            continue
        if sym.upper() not in equity_symbols:
            continue
        try:
            signals = strategy.generate_signals(df, symbol=sym)
            for sig in signals:
                d = _signal_to_dict(sig, "ag_vt_adx_rsi2_equity", "equity")
                if d:
                    d["symbol"] = sym
                    d["extra"]["source_tool"] = "vibe-trading-mcp"
                    d["extra"]["framing"] = "signal_overlay"
                    results.append(d)
        except Exception:
            continue
    return results


# ---------------------------------------------------------------------------
# 10. VT Pattern Sweep (Quant Analysis Toolkit pattern-recognition pillar)
# ---------------------------------------------------------------------------
def ag_vt_pattern_sweep(data: dict, context: dict = None) -> list[dict]:
    """Vibe-Trading pattern-sweep: candlestick + SMC + harmonic composite
    on 13 US mega-caps + sector ETFs.

    5yr: 245 trades, Sharpe 0.747, PF 1.48, WR 50%, MaxDD -18%. ~49 picks/year.
    """
    try:
        from baby_strategies.vt_pattern_sweep import VTPatternSweepStrategy
    except ImportError:
        return []
    strategy = VTPatternSweepStrategy()
    results = []
    universe = {"SPY", "QQQ", "XLK", "XLF", "XLE", "XLV", "XLY",
                "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN"}
    for sym, df in data.items():
        if not isinstance(df, pd.DataFrame) or len(df) < 220:
            continue
        if sym.upper() not in universe:
            continue
        try:
            signals = strategy.generate_signals(df, symbol=sym)
            for sig in signals:
                ac = _infer_asset_class(sym)  # "ETF" or "EQUITY" (upper, hygiene-grade)
                # Use upper for consistent naming with post-patch _infer + resolved_picks
                category = ac.lower() if ac in ("ETF", "EQUITY") else "structure"
                d = _signal_to_dict(sig, "ag_vt_pattern_sweep", category)
                if d:
                    d["symbol"] = sym
                    d["asset_class"] = ac  # explicit for clean emission (F14 wiring hygiene)
                    d["extra"]["source_tool"] = "vibe-trading-mcp"
                    d["extra"]["pattern_pillar"] = "candlestick+smc+harmonic"
                    results.append(d)
        except Exception:
            continue
    return results


# ---------------------------------------------------------------------------
# 11. VT Thematic ETF Momentum (highest-Sharpe vt_* ship, 1.02)
# ---------------------------------------------------------------------------
def ag_vt_thematic_etf_momentum(data: dict, context: dict = None) -> list[dict]:
    """Vibe-Trading novel-backtest: 63-bar total-return ranking on 9 thematic
    ETFs (XBI/ARKK/SMH/SOXX/XHB/IBB/XRT/XOP/XME), hold top 3, weekly rebalance.

    6.3yr: 178 trades, Sharpe 1.02 (HIGHEST vt_* ship), PF 2.14, WR 51%,
    CAGR +26%, MaxDD -32.9%. Beats SPY by +148pp. ~28 picks/year.

    DD WARNING: -32.9% exceeds -25% baby gate; portfolio allocator should cap
    weight accordingly.
    """
    try:
        from baby_strategies.vt_thematic_etf_momentum import VTThematicETFMomentumStrategy, UNIVERSE
    except ImportError:
        return []
    strategy = VTThematicETFMomentumStrategy()
    results = []
    # Build multi-symbol map (thematic is rotation/rank strategy — needs full universe view)
    md: dict = {}
    u_set = {u.upper() for u in UNIVERSE}
    for sym, df in data.items():
        if not isinstance(df, pd.DataFrame) or len(df) < 80:
            continue
        if sym.upper() not in u_set:
            continue
        md[sym] = df
    if len(md) < 2:
        return []
    try:
        signals = strategy.generate_signals(md)
        for sig in signals:
            ac = _infer_asset_class(sig.symbol or next(iter(md.keys())))
            category = ac.lower() if ac in ("ETF", "EQUITY") else "etf"
            d = _signal_to_dict(sig, "ag_vt_thematic_etf_momentum", category)
            if d:
                d["symbol"] = sig.symbol
                d["asset_class"] = ac  # explicit via _infer for clean post-patch emission
                d["extra"]["source_tool"] = "vibe-trading-mcp"
                d["extra"]["framing"] = "thematic_momentum_rotation"
                d["extra"]["dd_warning"] = "-32.9% historical; scale weight"
                results.append(d)
    except Exception:
        return []
    return results


# ---------------------------------------------------------------------------
# 12. VT Stat-Arb GDX/SLV (cointegration-based metals pair)
# ---------------------------------------------------------------------------
def ag_vt_stat_arb_gdx_slv(data: dict, context: dict = None) -> list[dict]:
    """Vibe-Trading stat-arb: long GDX when cheap vs SLV beta-adjusted.

    6yr: 15 trades, Sharpe 0.556, PF 2.40 (2nd highest vt_* after Donchian
    Gold 6.43), WR 60%, MaxDD -38% (unhedged). ~2.5 picks/year.

    HEDGE WARNING: -38% DD is one-sided encoding; operator should pair each
    long GDX with a short SLV position for beta hedge. Only tradeable pair
    out of 17 cointegration-tested candidates.
    """
    try:
        from baby_strategies.vt_stat_arb_gdx_slv import VTStatArbGDXSLVStrategy
    except ImportError:
        return []
    # Needs BOTH GDX and SLV dataframes
    gdx_df = None
    slv_df = None
    for sym, df in data.items():
        if not isinstance(df, pd.DataFrame):
            continue
        if sym.upper() == "GDX":
            gdx_df = df
        elif sym.upper() == "SLV":
            slv_df = df
    if gdx_df is None or slv_df is None:
        return []
    if len(gdx_df) < 320 or len(slv_df) < 320:
        return []
    strategy = VTStatArbGDXSLVStrategy()
    results = []
    try:
        signals = strategy.generate_signals(gdx_df, slv_df)
        for sig in signals:
            d = _signal_to_dict(sig, "ag_vt_stat_arb_gdx_slv", "etf")
            if d:
                d["symbol"] = "GDX"
                d["extra"]["source_tool"] = "vibe-trading-mcp"
                d["extra"]["framing"] = "stat_arb_pair_one_sided"
                d["extra"]["hedge_warning"] = "pair-trade; op must short SLV"
                results.append(d)
    except Exception:
        pass
    return results


# ---------------------------------------------------------------------------
# 13. VT Restatement Short (8-K Item 4.02 event-driven SHORT signal)
# ---------------------------------------------------------------------------
def ag_vt_restatement_short(data: dict, context: dict = None) -> list[dict]:
    """Vibe-Trading event-driven SHORT on SEC 8-K Item 4.02 restatements.

    Validated (2023-01 → 2026-04): HIGH severity 51.3% short hit rate vs SPY
    28.2% baseline (+23.1pp edge), MEDIUM 54.5% hit rate (+26.4pp).
    ~80 picks/year after $5 price filter.

    RISK FILTERS REQUIRED (enforced by operator risk layer, not this adapter):
    min price $5, ADV, HTB<15%, no open M&A, SSR awareness, ≤0.5% NAV/name.

    This adapter reads pre-classified restatement events from
    .tmp-validation-mcp/item_4_02/restatements.json. If the file is missing
    or the event feed isn't wired, returns []. The ACTUAL short signal
    generation needs a live EDGAR 8-K feed in production.
    """
    try:
        from baby_strategies.vt_restatement_short import VTRestatementShortStrategy
    except ImportError:
        return []

    # Load pre-classified restatement events (offline validation snapshot)
    events_file = _repo / ".tmp-validation-mcp" / "item_4_02" / "restatements.json"
    if not events_file.exists():
        return []
    try:
        import json
        with open(events_file, encoding="utf-8") as f:
            events = json.load(f)
    except Exception:
        return []

    # Filter to HIGH/MEDIUM severity within the last 3 trading days
    from datetime import datetime, timedelta, timezone
    try:
        now = datetime.now(timezone.utc)
    except Exception:
        now = datetime.utcnow()
    cutoff = now - timedelta(days=5)  # 3 trading days ~= 5 calendar
    recent = []
    for e in events if isinstance(events, list) else []:
        sev = str(e.get("severity") or "").upper()
        if sev not in {"HIGH", "MEDIUM"}:
            continue
        fd_str = e.get("filing_date") or ""
        try:
            fd = datetime.fromisoformat(str(fd_str).replace("Z", "+00:00"))
            if fd.tzinfo is None:
                fd = fd.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if fd < cutoff:
            continue
        recent.append(e)

    if not recent:
        return []

    strategy = VTRestatementShortStrategy() if hasattr(
        __import__("baby_strategies.vt_restatement_short", fromlist=["VTRestatementShortStrategy"]),
        "VTRestatementShortStrategy"
    ) else None
    results = []
    for e in recent:
        sym = str(e.get("ticker") or "").upper()
        if not sym or sym not in data:
            continue
        df = data.get(sym)
        if not isinstance(df, pd.DataFrame) or len(df) < 20:
            continue
        close_latest = float(df["close"].iloc[-1]) if "close" in df.columns else 0.0
        if close_latest < 5.0:  # mandatory $5 minimum price filter
            continue
        # Emit a SHORT signal with ATR-based TP/SL
        try:
            high = df["high"].astype(float)
            low = df["low"].astype(float)
            closes = df["close"].astype(float)
            tr = pd.concat([high - low, (high - closes.shift()).abs(), (low - closes.shift()).abs()], axis=1).max(axis=1)
            atr = float(tr.rolling(14, min_periods=1).mean().iloc[-1])
            if atr <= 0:
                continue
            tp = close_latest - atr * 3.0  # SHORT: TP below entry
            sl = close_latest + atr * 1.5  # SHORT: SL above entry
            sev_conf = 0.70 if str(e.get("severity")).upper() == "HIGH" else 0.58
            d = {
                "symbol": sym,
                "signal": "SELL",
                "strategy": "ag_vt_restatement_short",
                "confidence": sev_conf,
                "entry_price": round(close_latest, 4),
                "take_profit": round(tp, 4),
                "stop_loss": round(sl, 4),
                "risk_reward": round(abs(tp - close_latest) / abs(sl - close_latest), 2) if sl != close_latest else 0,
                "category": "equity",
                "timeframe": "1d",
                "source": "antigravity",
                "extra": {
                    "reason": f"SEC 8-K Item 4.02 restatement ({e.get('severity')}) filed {e.get('filing_date')}",
                    "source_tool": "vibe-trading-mcp",
                    "framing": "event_driven_short",
                    "risk_filters_required": "price_ge_5 + ADV + HTB_lt_15 + no_MA + SSR",
                },
            }
            results.append(d)
        except Exception:
            continue
    return results


# ---------------------------------------------------------------------------
# Export dict for scanner registration
# ---------------------------------------------------------------------------
ANTIGRAVITY_STRATEGIES = {
    "ag_vwap_rsi_institutional": ag_vwap_rsi_institutional,
    "ag_liquidation_cascade_contrarian": ag_liquidation_cascade_contrarian,
    "ag_regime_sentinel_composite": ag_regime_sentinel_composite,
    "ag_rsi_pairs_arbitrage": ag_rsi_pairs_arbitrage,
    # 2026-04-14 promotion (PR #194 meta status → this PR wires the adapters):
    "ag_moving_average_slope_momentum": ag_moving_average_slope_momentum,
    "ag_multi_timeframe_ema_cloud": ag_multi_timeframe_ema_cloud,
    "ag_vol_scaled_keltner": ag_vol_scaled_keltner,
    # 2026-04-14 vibe-trading session ships (6 new, claude-vibe-validation):
    "ag_vt_adx_rsi2_etf": ag_vt_adx_rsi2_etf,
    "ag_vt_adx_rsi2_equity": ag_vt_adx_rsi2_equity,
    "ag_vt_pattern_sweep": ag_vt_pattern_sweep,
    "ag_vt_thematic_etf_momentum": ag_vt_thematic_etf_momentum,
    "ag_vt_stat_arb_gdx_slv": ag_vt_stat_arb_gdx_slv,
    "ag_vt_restatement_short": ag_vt_restatement_short,
}
