#!/usr/bin/env python3
"""
pm_macro_overlay.py — IDEA-H Phase 1 (2026-06-06)
====================================================
Extends the PM infrastructure from crypto-only to macro instruments.

Queries Kalshi + Polymarket for Fed rate meeting outcome probabilities.
When both platforms agree on a direction at >70% probability, emits:
  - FOREX picks: EUR/GBP/NZD/AUD LONG on rate-cut consensus
                  EUR/GBP/NZD/AUD SHORT on rate-hike consensus
  - Bond ETF picks: TLT/BND LONG on rate-cut, TLT/BND SHORT on rate-hike
  - Picks tagged forward_test_only=True (paper-trade until 60d / n≥30)

Wiring: called by alpha-engine-live.yml and audit-dashboard.yml AFTER
the existing Kalshi signal agent runs.

Acceptance criteria (90-day checkpoint per DAILY_IDEAS IDEA-H):
  PF≥1.25 AND WR≥50% on ≥30 resolved signals → promote to production weight
  PF<1.0 OR resolved n<10 after 60d → deactivate this module entirely.

No new dependencies; reuses urllib/json/pathlib from existing PM agents.
"""

from __future__ import annotations

import json
import logging
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = DATA_DIR / "pm_macro_overlay_signals.json"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [pm_macro] %(message)s")

KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
POLYMARKET_GAMMA = "https://gamma-api.polymarket.com/markets"
TIMEOUT = 20

CONSENSUS_THRESHOLD = 0.70   # both platforms must agree at ≥70% to emit
SOURCE_SYSTEM = "pm_macro_overlay"

# Fed rate outcome → instrument map
# Key: ("action", direction)  action = "cut" | "hike" | "hold"
RATE_INSTRUMENT_MAP = {
    "cut": {
        "forex_longs": ["EURUSD=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X"],
        "forex_shorts": [],
        "etf_longs": ["TLT", "BND", "IEF"],  # long duration bonds benefit from cuts
        "etf_shorts": [],
        "reason_template": "Fed rate-cut consensus: Kalshi={k_prob:.1%} Polymarket={p_prob:.1%}. Rate cuts weaken USD and rally long-duration bonds.",
    },
    "hike": {
        "forex_longs": [],
        "forex_shorts": ["EURUSD=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X"],
        "etf_longs": [],
        "etf_shorts": ["TLT", "BND", "IEF"],  # rate hikes crush long-duration bonds
        "reason_template": "Fed rate-hike consensus: Kalshi={k_prob:.1%} Polymarket={p_prob:.1%}. Rate hikes strengthen USD and pressure long-duration bonds.",
    },
}

# TP/SL parameters per asset class (fraction of entry)
FOREX_TP_PCT = 0.012    # 1.2% TP for FOREX (cleared 1.0% ATR per project SL_CAP_FOREX)
FOREX_SL_PCT = 0.008    # 0.8% SL
ETF_TP_PCT = 0.04       # 4% TP for bond ETFs (macro moves are slower/larger)
ETF_SL_PCT = 0.025      # 2.5% SL

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def _get(url: str, timeout: int = TIMEOUT) -> Optional[dict]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        logger.warning("GET %s failed: %s", url, exc)
        return None


def fetch_kalshi_fed_probability() -> Optional[tuple[str, float]]:
    """Return (action, probability) for the most liquid Fed rate market on Kalshi.

    action is one of 'cut', 'hike', 'hold'.
    Returns None if no Fed market found or API is down.
    """
    # Kalshi Fed series: KXFED (rate decision), FOMC, etc.
    series_to_try = ["KXFED", "FOMC", "FEDRATE", "FED"]
    for series in series_to_try:
        url = f"{KALSHI_API}/markets?series_ticker={series}&limit=20"
        data = _get(url)
        if not data:
            continue
        markets = data.get("markets", [])
        if not markets:
            continue

        # Find the most liquid open market
        open_markets = [m for m in markets if m.get("status") == "open"]
        if not open_markets:
            continue
        market = max(open_markets, key=lambda m: m.get("volume", 0))

        yes_price = market.get("yes_bid") or market.get("last_price") or 0
        no_price = market.get("no_bid") or (1 - yes_price) if yes_price else 0

        title = (market.get("title") or "").lower()
        subtitle = (market.get("subtitle") or "").lower()
        combined = title + " " + subtitle

        # Map market title to action
        if any(w in combined for w in ("cut", "lower", "decrease", "reduce")):
            action = "cut"
        elif any(w in combined for w in ("hike", "raise", "increase")):
            action = "hike"
        else:
            action = "hold"

        prob = float(yes_price) / 100 if yes_price > 1 else float(yes_price)
        if prob > 0:
            logger.info("Kalshi %s: action=%s prob=%.1f%%", series, action, prob * 100)
            return action, prob

    logger.info("Kalshi: no Fed markets found — tried %s", series_to_try)
    return None


def fetch_polymarket_fed_probability() -> Optional[tuple[str, float]]:
    """Return (action, probability) from Polymarket Gamma API for Fed rate markets."""
    url = f"{POLYMARKET_GAMMA}?search=federal+reserve+rate&limit=10&active=true"
    data = _get(url)
    if not data:
        # Try with slug-based search
        data = _get(f"{POLYMARKET_GAMMA}?search=fed+rate+cut&limit=10")
    if not data:
        return None

    markets = data if isinstance(data, list) else data.get("results", data.get("markets", []))
    if not markets:
        return None

    # Find the most liquid Fed rate market
    best = None
    best_vol = 0
    for m in markets:
        title = (m.get("question") or m.get("title") or "").lower()
        vol = float(m.get("volume") or m.get("volumeNum") or 0)
        if "fed" in title or "fomc" in title or "federal reserve" in title:
            if vol > best_vol:
                best_vol = vol
                best = m

    if not best:
        logger.info("Polymarket: no Fed markets found")
        return None

    title = (best.get("question") or best.get("title") or "").lower()
    # Probability: outcomePrices[0] (YES) is the probability
    outcome_prices = best.get("outcomePrices")
    if isinstance(outcome_prices, str):
        try:
            outcome_prices = json.loads(outcome_prices)
        except Exception:
            outcome_prices = None

    prob = 0.0
    if outcome_prices and len(outcome_prices) >= 1:
        try:
            prob = float(outcome_prices[0])
        except (ValueError, TypeError):
            prob = float(best.get("bestBid", 0) or 0)

    if prob > 1:
        prob /= 100

    if any(w in title for w in ("cut", "lower", "decrease")):
        action = "cut"
    elif any(w in title for w in ("hike", "raise", "increase")):
        action = "hike"
    else:
        action = "hold"

    logger.info("Polymarket Fed: action=%s prob=%.1f%% (vol=%.0f)", action, prob * 100, best_vol)
    return action, prob


def _build_pick(symbol: str, direction: str, confidence: float, reason: str, now: datetime, is_etf: bool) -> dict:
    """Build a standardized pick dict for macro overlay signals."""
    import yfinance as yf
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d", interval="1d")
        entry = float(hist["Close"].iloc[-1]) if len(hist) > 0 else 0.0
    except Exception:
        entry = 0.0

    if entry <= 0:
        logger.warning("Could not fetch price for %s — skipping pick", symbol)
        return {}

    tp_pct = ETF_TP_PCT if is_etf else FOREX_TP_PCT
    sl_pct = ETF_SL_PCT if is_etf else FOREX_SL_PCT

    if direction == "LONG":
        tp = round(entry * (1 + tp_pct), 6)
        sl = round(entry * (1 - sl_pct), 6)
        rr = tp_pct / sl_pct
    else:
        tp = round(entry * (1 - tp_pct), 6)
        sl = round(entry * (1 + sl_pct), 6)
        rr = tp_pct / sl_pct

    asset_class = "ETF" if is_etf else "FOREX"
    category = "etf" if is_etf else "forex"

    return {
        "id": f"pm_macro_{symbol}_{direction[0]}_{now.strftime('%Y%m%d%H%M')}",
        "strategy": "pm_fed_rate_overlay",
        "symbol": symbol,
        "category": category,
        "asset_class": asset_class,
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "direction": direction,
        "entry_price": round(entry, 6),
        "take_profit": tp,
        "stop_loss": sl,
        "confidence": round(confidence, 4),
        "risk_reward": round(rr, 2),
        "status": "OPEN",
        "source_system": SOURCE_SYSTEM,
        "signal_timestamp": now.strftime("%Y-%m-%dT00:00:00+00:00"),
        "timestamp": now.isoformat(),
        "reason": reason,
        "forward_test_only": True,
        "forward_validated": False,
    }


def generate_macro_picks() -> list[dict]:
    """Fetch PM probabilities and emit macro picks if consensus is strong enough."""
    now = datetime.now(timezone.utc)

    kalshi_result = fetch_kalshi_fed_probability()
    polymarket_result = fetch_polymarket_fed_probability()

    if not kalshi_result or not polymarket_result:
        logger.info("Insufficient PM data — Kalshi=%s Polymarket=%s", kalshi_result, polymarket_result)
        return []

    k_action, k_prob = kalshi_result
    p_action, p_prob = polymarket_result

    # Both platforms must agree on the same direction
    if k_action != p_action:
        logger.info("PM disagreement: Kalshi=%s Polymarket=%s — no signal", k_action, p_action)
        return []

    action = k_action
    # Average probability, weighted by platform reliability
    avg_prob = (k_prob * 0.5 + p_prob * 0.5)

    if avg_prob < CONSENSUS_THRESHOLD:
        logger.info("PM consensus below threshold: %.1f%% < %.0f%% — no signal",
                    avg_prob * 100, CONSENSUS_THRESHOLD * 100)
        return []

    if action == "hold":
        logger.info("PM consensus: HOLD — no directional signal emitted")
        return []

    instr = RATE_INSTRUMENT_MAP.get(action)
    if not instr:
        return []

    reason_base = instr["reason_template"].format(k_prob=k_prob, p_prob=p_prob)
    picks = []
    confidence = min(0.78, avg_prob * 0.9)  # cap at 0.78; PM macro is lower-conviction than crypto

    try:
        import yfinance as yf  # noqa: F401
        has_yf = True
    except ImportError:
        logger.warning("yfinance not available — cannot fetch prices; picks skipped")
        has_yf = False

    if not has_yf:
        return []

    # FOREX picks
    for symbol in instr["forex_longs"]:
        p = _build_pick(symbol, "LONG", confidence, reason_base + f" LONG {symbol}.", now, is_etf=False)
        if p:
            picks.append(p)
    for symbol in instr["forex_shorts"]:
        p = _build_pick(symbol, "SHORT", confidence, reason_base + f" SHORT {symbol}.", now, is_etf=False)
        if p:
            picks.append(p)

    # ETF/bond picks
    for symbol in instr["etf_longs"]:
        p = _build_pick(symbol, "LONG", confidence, reason_base + f" LONG {symbol}.", now, is_etf=True)
        if p:
            picks.append(p)
    for symbol in instr["etf_shorts"]:
        p = _build_pick(symbol, "SHORT", confidence, reason_base + f" SHORT {symbol}.", now, is_etf=True)
        if p:
            picks.append(p)

    logger.info("Emitting %d macro picks (action=%s avg_prob=%.1f%%)", len(picks), action, avg_prob * 100)
    return picks


def run() -> None:
    """Main entry point: generate picks and write to output file."""
    picks = generate_macro_picks()
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE_SYSTEM,
        "pick_count": len(picks),
        "picks": picks,
    }
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, default=str))
    logger.info("Wrote %d picks to %s", len(picks), OUTPUT_FILE)

    # Also write to alpha_engine/data/ for pick-flow ingestion
    ae_path = ROOT / "alpha_engine" / "data" / "pm_macro_overlay_picks.json"
    ae_path.write_text(json.dumps(picks, indent=2, default=str))
    logger.info("Mirrored to %s", ae_path)


if __name__ == "__main__":
    run()
