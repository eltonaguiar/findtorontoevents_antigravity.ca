#!/usr/bin/env python3
"""
Contrarian Consensus Flip -- Cross-AI validated meta-strategy
=============================================================
Cross-AI consensus (Gemini + Claude, 6/6 agree):
  "Consensus = contrarian signal. When 3+ strategies agree on direction,
   flip to opposite."

When 3+ independent strategies agree on the same symbol + direction,
the WIN RATE is historically ~18% (vs 35% for solo picks). Consensus
in crypto = crowded trade = stop-hunted by market makers.

Quality-weighted analysis:
  - Weight strategies by WR (from trust_adjustments.json), trade count,
    and confidence to avoid treating all signals equally
  - Only fires when consensus is LOW QUALITY (avg weighted conf < 0.75)
    OR when symbol is in a mean-reverting regime (ranging/sideways via ADX)
  - Max 2 contrarian picks per cycle
  - Tighter TP/SL (5%/3%) -- contrarian trades are riskier

Data sources:
  - In-memory all_signals from current scan cycle
  - alpha_engine/data/active_picks.json (our strategies, on-disk)
  - copy_trader_intel/data/active_picks.json (copy trader signals)
  - alpha_engine/data/trust_adjustments.json (strategy quality scores)

Standalone runnable:
  python alpha_engine/contrarian_consensus.py
"""

from __future__ import annotations

import io
import json
import logging
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Windows UTF-8 fix ──────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    import pandas as pd
except ImportError:
    pd = None

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"
COPY_TRADER_DIR = BASE / "copy_trader_intel" / "data"
PAYLOAD_PATH = BASE / "audit_trail" / "data" / "dashboard_payload.json"
TRUST_PATH = DATA_DIR / "trust_adjustments.json"
ALPHA_PICKS_PATH = DATA_DIR / "active_picks.json"
CT_PICKS_PATH = COPY_TRADER_DIR / "active_picks.json"
OUTPUT_PATH = DATA_DIR / "contrarian_picks.json"

# ── Configuration ──────────────────────────────────────────────────
MIN_AGREEING_STRATEGIES = 3       # Need 3+ independent strategies
MAX_CONTRARIAN_PICKS = 2          # Cap contrarian picks per cycle
BASE_CONFIDENCE = 0.72
CONFIDENCE_BONUS_PER_EXTRA = 0.02  # +0.02 per additional agreeing strategy
MAX_CONFIDENCE = 0.82
TP_PCT = 0.05                     # 5% take profit (tighter -- contrarian is riskier)
SL_PCT = 0.03                     # 3% stop loss
LOW_QUALITY_THRESHOLD = 0.75      # Avg confidence below this = low-quality consensus
VPIN_THRESHOLD = 0.4              # VPIN toxic flow threshold (boosts signal)


# ── Helpers ────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(val: float) -> float:
    """Round price to sensible precision."""
    if val >= 1000:
        return round(val, 2)
    if val >= 1:
        return round(val, 4)
    return round(val, 6)


def _load_json(path: Path) -> Any:
    """Safely load a JSON file, return None on failure."""
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning("Failed to load %s: %s", path, e)
    return None


def _normalize_symbol(symbol: str) -> str:
    """Normalize symbol for cross-system matching.
    BTC-USD, BTCUSD, BTCUSDT, BTC-USDT all -> BTCUSDT
    """
    s = symbol.upper().replace("-", "").replace("/", "")
    # Strip yfinance suffix
    if s.endswith("=X"):
        s = s[:-2]
    # Normalize USD -> USDT for crypto (but not forex)
    if s.endswith("USD") and not s.endswith("USDT"):
        base = s[:-3]
        # Only convert short bases (crypto tickers), not forex like EURUSD
        if len(base) <= 5 and base.isalpha() and len(base) >= 2:
            # Exclude known forex bases
            forex_bases = {"EUR", "GBP", "AUD", "NZD", "CAD", "CHF", "JPY", "SGD", "HKD", "NOK", "SEK"}
            if base not in forex_bases:
                s = base + "USDT"
    return s


def _normalize_direction(pick: dict) -> str:
    """Extract normalized direction from a pick."""
    d = str(pick.get("direction", pick.get("signal_type", ""))).upper()
    if d in ("BUY", "LONG"):
        return "LONG"
    if d in ("SELL", "SHORT"):
        return "SHORT"
    return ""


def _load_trust_adjustments() -> dict:
    """Load strategy trust adjustments (WR, trade count, profit factor)."""
    data = _load_json(TRUST_PATH)
    if data and isinstance(data, dict):
        return data.get("strategy_adjustments", {})
    return {}


def _compute_strategy_weight(strategy_name: str, trust_data: dict) -> float:
    """Compute quality weight for a strategy based on trust data.
    Higher WR + more trades + better profit factor = higher weight.
    Returns weight in [0.05, ~2.0].
    """
    info = trust_data.get(strategy_name, {})
    wr = float(info.get("wr_last10", info.get("wr_last20", 0.5)))
    trades = int(info.get("total_trades", 0))
    pf = float(info.get("profit_factor", 1.0))

    # Trade count factor: more trades = more reliable (log scale, caps at ~1.0 for 50 trades)
    trade_factor = min(1.0, math.log1p(trades) / math.log1p(50))

    # WR factor: higher is better, floor at 0.1
    wr_factor = max(0.1, wr)

    # Profit factor: capped contribution [0.5, 1.5]
    pf_factor = min(1.5, max(0.5, pf / 2.0))

    return wr_factor * trade_factor * pf_factor


def _detect_regime_from_data(data: dict, symbol: str) -> str:
    """Detect market regime for a symbol using ADX.
    Returns 'ranging', 'trending', 'transitional', or 'unknown'.
    """
    if pd is None or data is None:
        return "unknown"

    df = data.get(symbol)
    if df is None or len(df) < 30:
        return "unknown"

    try:
        high = df["High"] if "High" in df.columns else df.get("high")
        low = df["Low"] if "Low" in df.columns else df.get("low")
        close = df["Close"] if "Close" in df.columns else df.get("close")

        if high is None or low is None or close is None:
            return "unknown"

        period = 14

        # +DM / -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

        # True Range
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr_val = tr.rolling(period).mean()

        # +DI / -DI -> DX -> ADX
        plus_di = 100.0 * (plus_dm.rolling(period).mean() / (atr_val + 1e-10))
        minus_di = 100.0 * (minus_dm.rolling(period).mean() / (atr_val + 1e-10))
        dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
        adx = dx.rolling(period).mean()

        current_adx = float(adx.iloc[-1])
        if math.isnan(current_adx):
            return "unknown"

        if current_adx <= 20:
            return "ranging"
        elif current_adx >= 25:
            return "trending"
        else:
            return "transitional"
    except Exception:
        return "unknown"


def _get_current_price(data: dict, symbol: str) -> float | None:
    """Get current price from market data."""
    if pd is None or data is None:
        return None
    df = data.get(symbol)
    if df is None or len(df) < 1:
        return None
    close = df["Close"] if "Close" in df.columns else df.get("close")
    if close is None:
        return None
    try:
        val = float(close.iloc[-1])
        return val if not math.isnan(val) else None
    except Exception:
        return None


def _check_vpin(picks: list[dict]) -> tuple[bool, float]:
    """Check if any pick in a consensus group has VPIN data suggesting toxic flow."""
    for p in picks:
        extra = p.get("extra", {}) if isinstance(p.get("extra"), dict) else {}
        vpin = p.get("vpin") or p.get("_vpin") or extra.get("vpin") or 0
        if isinstance(vpin, (int, float)) and vpin > VPIN_THRESHOLD:
            return True, float(vpin)
    return False, 0.0


def _estimate_entry_from_pick(pick: dict) -> float:
    """Get entry price from a pick dict."""
    return float(pick.get("entry_price", 0) or 0)


# ── Core Logic ─────────────────────────────────────────────────────

def _collect_all_picks(all_signals: list[dict] | None = None) -> list[dict]:
    """Collect picks from in-memory signals AND external JSON files.

    Cross-references:
      - all_signals: live signals from current scan cycle
      - alpha_engine/data/active_picks.json
      - copy_trader_intel/data/active_picks.json
    """
    picks = []
    seen_keys = set()  # (strategy, normalized_symbol) for dedup

    def _add_pick(strategy, symbol, raw_symbol, direction, confidence, source, extra=None, entry_price=0.0):
        key = (strategy, symbol)
        if key in seen_keys:
            return
        seen_keys.add(key)
        picks.append({
            "strategy": strategy,
            "symbol": symbol,
            "raw_symbol": raw_symbol,
            "direction": direction,
            "confidence": confidence,
            "source": source,
            "extra": extra or {},
            "entry_price": entry_price,
        })

    # 1. In-memory signals from current scan cycle
    if all_signals:
        for sig in all_signals:
            strat = sig.get("strategy", "")
            raw_sym = sig.get("symbol", "")
            norm_sym = _normalize_symbol(raw_sym)
            direction = _normalize_direction(sig)
            conf = float(sig.get("confidence", 0.5))
            ep = float(sig.get("entry_price", 0) or 0)
            if strat and norm_sym and direction:
                _add_pick(strat, norm_sym, raw_sym, direction, conf,
                          "alpha_engine_live", sig.get("extra"), ep)

    # 2. Alpha engine active picks (on-disk)
    alpha_picks = _load_json(ALPHA_PICKS_PATH)
    if isinstance(alpha_picks, list):
        for p in alpha_picks:
            if str(p.get("status", "")).upper() != "OPEN":
                continue
            strat = p.get("strategy", "")
            raw_sym = p.get("symbol", "")
            norm_sym = _normalize_symbol(raw_sym)
            direction = _normalize_direction(p)
            conf = float(p.get("confidence", p.get("ml_score", 0.5)))
            ep = float(p.get("entry_price", 0) or 0)
            if strat and norm_sym and direction:
                _add_pick(strat, norm_sym, raw_sym, direction, conf,
                          "alpha_engine_disk", p.get("extra"), ep)

    # 3. Copy trader intel active picks
    ct_picks = _load_json(CT_PICKS_PATH)
    if isinstance(ct_picks, list):
        for p in ct_picks:
            if str(p.get("status", "")).upper() != "OPEN":
                continue
            strat = p.get("strategy", "")
            raw_sym = p.get("symbol", "")
            norm_sym = _normalize_symbol(raw_sym)
            direction = _normalize_direction(p)
            conf = float(p.get("confidence", p.get("ml_score", 0.5)))
            ep = float(p.get("entry_price", 0) or 0)
            if strat and norm_sym and direction:
                _add_pick(strat, norm_sym, raw_sym, direction, conf,
                          "copy_trader_intel", p.get("extra"), ep)

    # 4. Dashboard payload (fallback if no live signals)
    if not all_signals:
        payload = _load_json(PAYLOAD_PATH)
        if payload:
            active = payload.get("picks", {}).get("active", [])
            for p in active:
                strat = p.get("strategy", "")
                raw_sym = p.get("symbol", "")
                norm_sym = _normalize_symbol(raw_sym)
                direction = _normalize_direction(p)
                conf = float(p.get("confidence", p.get("ml_score", 0.5)))
                ep = float(p.get("entry_price", 0) or 0)
                if strat and norm_sym and direction:
                    _add_pick(strat, norm_sym, raw_sym, direction, conf,
                              "dashboard_payload", p.get("extra"), ep)

    return picks


def generate_contrarian_consensus_picks(
    data: dict | None = None,
    all_signals: list[dict] | None = None,
) -> list[dict]:
    """
    Main entry point for scanner integration.

    Analyze consensus across ALL active strategies and copy trader signals.
    When 3+ independent strategies agree on the same symbol+direction,
    generate a CONTRARIAN pick in the OPPOSITE direction.

    Quality gates:
      - Weight strategies by WR, trade count, profit factor
      - Only fire when avg weighted confidence < 0.75 (low-quality consensus)
        OR when symbol is in a mean-reverting regime (ranging via ADX <= 20)
      - Cap at 2 contrarian picks per cycle

    Args:
        data: dict of symbol -> DataFrame (market data for regime detection + pricing)
        all_signals: list of signal dicts from current scan cycle

    Returns:
        list of contrarian pick dicts (max MAX_CONTRARIAN_PICKS)
    """
    picks = _collect_all_picks(all_signals)
    if not picks:
        return []

    trust_data = _load_trust_adjustments()

    # Group by normalized symbol + direction
    consensus_groups: dict[tuple[str, str], list[dict]] = {}
    for p in picks:
        sym = p["symbol"]
        d = p["direction"]
        if not sym or not d:
            continue
        key = (sym, d)
        consensus_groups.setdefault(key, []).append(p)

    # Find consensus candidates and score them
    candidates = []

    for (symbol, direction), agreeing_picks in consensus_groups.items():
        # De-duplicate by strategy name
        seen_strategies: set[str] = set()
        unique_picks: list[dict] = []
        for p in agreeing_picks:
            strat = p["strategy"]
            if strat not in seen_strategies:
                seen_strategies.add(strat)
                unique_picks.append(p)

        num_agreeing = len(unique_picks)
        if num_agreeing < MIN_AGREEING_STRATEGIES:
            continue

        # ── Quality-weighted consensus score ──────────────────────
        total_weight = 0.0
        weighted_confidence_sum = 0.0
        for p in unique_picks:
            w = _compute_strategy_weight(p["strategy"], trust_data)
            total_weight += w
            weighted_confidence_sum += w * p["confidence"]

        avg_confidence = (
            weighted_confidence_sum / total_weight
            if total_weight > 0
            else sum(p["confidence"] for p in unique_picks) / num_agreeing
        )

        # ── Regime detection ──────────────────────────────────────
        raw_sym = unique_picks[0].get("raw_symbol", symbol)
        regime = _detect_regime_from_data(data, raw_sym) if data else "unknown"

        # ── Quality gate: only fire when consensus is likely WRONG ─
        low_quality = avg_confidence < LOW_QUALITY_THRESHOLD
        mean_reverting = regime in ("ranging",)

        if not low_quality and not mean_reverting:
            # High-quality consensus in a trending market -- don't fade
            continue

        # ── VPIN toxic flow check (boosts confidence) ─────────────
        has_vpin, vpin_val = _check_vpin(unique_picks)

        # ── Contrarian direction ──────────────────────────────────
        contra_direction = "SHORT" if direction == "LONG" else "LONG"
        contra_signal_type = "SELL" if direction == "LONG" else "BUY"

        # ── Pricing ───────────────────────────────────────────────
        price = _get_current_price(data, raw_sym) if data else None
        if price is None or price <= 0:
            # Fall back to average entry price from consensus picks
            valid_entries = [_estimate_entry_from_pick(p) for p in unique_picks
                            if _estimate_entry_from_pick(p) > 0]
            # Also check original full picks for entry_price
            if not valid_entries and all_signals:
                for sig in all_signals:
                    if _normalize_symbol(sig.get("symbol", "")) == symbol:
                        ep = float(sig.get("entry_price", 0) or 0)
                        if ep > 0:
                            valid_entries.append(ep)
            if not valid_entries:
                continue
            price = sum(valid_entries) / len(valid_entries)

        # ── TP / SL ──────────────────────────────────────────────
        if contra_direction == "LONG":
            tp = price * (1 + TP_PCT)
            sl = price * (1 - SL_PCT)
        else:
            tp = price * (1 - TP_PCT)
            sl = price * (1 + SL_PCT)

        rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0
        if rr < 1.0:
            continue

        # ── Confidence: base + bonus per extra, VPIN boost ────────
        extra_count = max(0, num_agreeing - MIN_AGREEING_STRATEGIES)
        confidence = min(MAX_CONFIDENCE, BASE_CONFIDENCE + extra_count * CONFIDENCE_BONUS_PER_EXTRA)
        if has_vpin:
            confidence = min(confidence + 0.05, 0.90)

        # ── Build reason string ───────────────────────────────────
        sources = sorted(set(p["source"] for p in unique_picks))
        source_str = " + ".join(sources)

        fire_parts = []
        if low_quality:
            fire_parts.append(f"low-quality consensus (avg conf={avg_confidence:.2f}<{LOW_QUALITY_THRESHOLD})")
        if mean_reverting:
            fire_parts.append("mean-reverting regime (ADX<=20)")
        fire_reason = " AND ".join(fire_parts)

        strat_names = sorted(seen_strategies)
        if len(strat_names) > 5:
            strat_display = ", ".join(strat_names[:5]) + f" +{len(strat_names)-5} more"
        else:
            strat_display = ", ".join(strat_names)

        vpin_note = f" VPIN={vpin_val:.2f} confirms toxic flow." if has_vpin else ""

        reason = (
            f"Contrarian consensus flip: {num_agreeing} strategies agree "
            f"{direction} on {symbol} [{strat_display}]. "
            f"Flipping to {contra_direction}. "
            f"Trigger: {fire_reason}.{vpin_note} "
            f"Sources: {source_str}. "
            f"Weighted avg conf={avg_confidence:.2f}."
        )

        # ── Detect category ───────────────────────────────────────
        category = "crypto"
        if "=X" in raw_sym or raw_sym.endswith(("JPY", "USD", "GBP", "EUR", "AUD", "CHF", "CAD")):
            # Check if it's a forex pair (6+ chars base like GBPJPY)
            stripped = raw_sym.replace("=X", "")
            if len(stripped) == 6 and stripped.isalpha():
                category = "forex"
        equity_suffixes = ("SPY", "QQQ", "AAPL", "MSFT", "TSLA", "AMZN", "GOOG", "META", "NVDA")
        if any(raw_sym.upper().startswith(s) or raw_sym.upper().endswith(s) for s in equity_suffixes):
            category = "equity"

        candidates.append({
            "strategy": "contrarian_consensus_flip",
            "symbol": raw_sym,
            "category": category,
            "signal_type": contra_signal_type,
            "direction": contra_direction,
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(confidence, 2),
            "risk_reward": round(rr, 2),
            "reason": reason,
            "timeframe": "1d",
            "timestamp": _now_iso(),
            "extra": {
                "num_agreeing": num_agreeing,
                "agreeing_strategies": sorted(seen_strategies),
                "original_direction": direction,
                "avg_confidence": round(avg_confidence, 4),
                "weighted_score": round(total_weight, 4),
                "regime": regime,
                "low_quality_consensus": low_quality,
                "mean_reverting_regime": mean_reverting,
                "sources": sources,
                "tp_pct": TP_PCT,
                "sl_pct": SL_PCT,
                "vpin_toxic": has_vpin,
                "vpin_value": round(vpin_val, 4),
            },
        })

    if not candidates:
        return []

    # Sort by number of agreeing strategies (more agreement = stronger contrarian signal)
    candidates.sort(key=lambda c: c["extra"]["num_agreeing"], reverse=True)

    # Cap at MAX_CONTRARIAN_PICKS
    result = candidates[:MAX_CONTRARIAN_PICKS]

    for pick in result:
        logger.info(
            "Contrarian consensus flip: %s %s conf=%.2f (from %d agreeing strategies)",
            pick["direction"], pick["symbol"], pick["confidence"],
            pick["extra"]["num_agreeing"],
        )

    return result


# ── Standalone mode ────────────────────────────────────────────────

def run():
    """Standalone entry point: load from disk, generate contrarian picks, save output."""
    print("=" * 60)
    print("  CONTRARIAN CONSENSUS FLIP -- Cross-AI Validated")
    print("  (Quality-weighted, regime-aware, cross-system)")
    print("=" * 60)

    # Generate picks (no live data, will use disk files)
    signals = generate_contrarian_consensus_picks(data=None, all_signals=None)

    # Also collect stats for display
    all_picks = _collect_all_picks(None)
    consensus_groups = defaultdict(list)
    for p in all_picks:
        key = f"{p['symbol']}|{p['direction']}"
        consensus_groups[key].append(p)

    # Filter to 3+ unique strategies
    filtered = {}
    for key, picks in consensus_groups.items():
        strats = set(p["strategy"] for p in picks)
        if len(strats) >= MIN_AGREEING_STRATEGIES:
            filtered[key] = {"picks": picks, "strategy_count": len(strats), "strategies": list(strats)}

    # Save output
    _save_output(signals, filtered)
    _print_summary(signals, filtered)


def _save_output(signals, consensus_groups):
    """Save contrarian picks to JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": _now_iso(),
        "consensus_clusters_found": len(consensus_groups),
        "contrarian_signals_generated": len(signals),
        "signals": signals,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"[contrarian] Saved {len(signals)} signals to {OUTPUT_PATH}")


def _print_summary(signals, consensus_groups):
    """Print human-readable summary."""
    print()
    print("-" * 60)
    print(f"  SUMMARY: {len(consensus_groups)} consensus clusters (3+ strategies agree)")
    print(f"           {len(signals)} contrarian signals generated (max {MAX_CONTRARIAN_PICKS})")
    print("-" * 60)

    if not signals:
        print("  No contrarian signals -- either no consensus or consensus was high-quality + trending")

    for sig in signals:
        extra = sig.get("extra", {})
        vpin_str = f" [VPIN={extra.get('vpin_value', 0):.2f}]" if extra.get("vpin_toxic") else ""
        regime_str = f" [{extra.get('regime', '?')}]"
        print(
            f"  {sig['symbol']:12s} | "
            f"Crowd={extra.get('original_direction', '?'):5s} x{extra.get('num_agreeing', 0)} -> "
            f"FADE {sig['direction']:5s} | "
            f"Conf={sig['confidence']:.2f}{vpin_str}{regime_str} | "
            f"RR={sig['risk_reward']:.2f} | "
            f"TP={TP_PCT*100:.0f}%/SL={SL_PCT*100:.0f}%"
        )

    print("-" * 60)
    print()


if __name__ == "__main__":
    run()
