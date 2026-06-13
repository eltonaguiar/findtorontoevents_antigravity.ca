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

2026-06-12 fetcher fix: both platform fetchers were silent no-ops from launch
(Kalshi schema drift: 'active' status + string-dollar fields; Polymarket
/markets?search= ignores its search param). Rewritten against live-verified
schemas: Kalshi KXFEDDECISION per-meeting Cut/Hike/Hold legs + Polymarket
/public-search per-meeting binaries. The 60-day acceptance clock above starts
2026-06-12 (first day signals could actually flow), not 2026-06-06.
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

# API schemas verified live 2026-06-12 (see pm_odds_history.py, which shares them):
#   Kalshi v2: status='active' (not 'open'), string-dollar prices
#     (last_price_dollars / yes_bid_dollars), volume_fp. The KXFEDDECISION series
#     has explicit per-meeting Cut/Hike/Hold legs (ticker suffix C25/C26/H0/H25/
#     H26) — no keyword classification needed.
#   Polymarket: /markets?search= IGNORES the search param; use /public-search?q=.
#     Per-meeting binaries "Fed rate cut by <Month Year> meeting?" + hike
#     equivalents; endDate is unreliable — parse the meeting month from the
#     question text instead.
KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
POLYMARKET_SEARCH = "https://gamma-api.polymarket.com/public-search"
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


def _kalshi_price(market: dict) -> Optional[float]:
    """Probability from current (string-dollar) fields, legacy cent ints as fallback."""
    for field in ("last_price_dollars", "yes_bid_dollars", "last_price", "yes_bid"):
        raw = market.get(field)
        if raw in (None, "", 0):
            continue
        try:
            prob = float(raw)
        except (TypeError, ValueError):
            continue
        if prob > 1:  # legacy cent-int fields
            prob /= 100.0
        if 0 < prob <= 1:
            return prob
    return None


def fetch_kalshi_fed_probability() -> Optional[tuple[str, float]]:
    """Return (action, probability) for the NEAREST upcoming FOMC meeting on Kalshi.

    Uses the KXFEDDECISION series, whose per-meeting markets have explicit legs:
    ticker suffix C25/C26 = cut (25bps / >25bps), H0 = no change (hold),
    H25/H26 = hike. p(action) = sum of that action's legs — no keyword guessing.
    Returns None if the series is empty or the API is down.
    """
    data = _get(f"{KALSHI_API}/markets?series_ticker=KXFEDDECISION&limit=100&status=open")
    markets = [m for m in (data or {}).get("markets", [])
               if m.get("status") in ("active", "open")]
    if not markets:
        logger.info("Kalshi: no open KXFEDDECISION markets found")
        return None

    # Group by meeting (event_ticker), pick the nearest future close_time
    now = datetime.now(timezone.utc)
    events: dict[str, list[dict]] = {}
    for m in markets:
        events.setdefault(m.get("event_ticker") or "?", []).append(m)

    def _close_time(ms: list[dict]) -> datetime:
        try:
            return datetime.fromisoformat(
                (ms[0].get("close_time") or "").replace("Z", "+00:00"))
        except ValueError:
            return now.replace(year=now.year + 10)

    upcoming = {ev: ms for ev, ms in events.items() if _close_time(ms) > now}
    if not upcoming:
        logger.info("Kalshi: KXFEDDECISION has no future-dated meetings")
        return None
    nearest_ev = min(upcoming, key=lambda ev: _close_time(upcoming[ev]))

    probs = {"cut": 0.0, "hike": 0.0, "hold": 0.0}
    for m in upcoming[nearest_ev]:
        leg = (m.get("ticker") or "").rsplit("-", 1)[-1].upper()
        prob = _kalshi_price(m)
        if prob is None:
            continue
        if leg.startswith("C"):
            probs["cut"] += prob
        elif leg == "H0":
            probs["hold"] += prob
        elif leg.startswith("H"):
            probs["hike"] += prob

    if not any(probs.values()):
        logger.info("Kalshi: %s legs had no usable prices", nearest_ev)
        return None
    action = max(probs, key=lambda a: probs[a])
    prob = min(probs[action], 1.0)
    logger.info("Kalshi %s: cut=%.1f%% hike=%.1f%% hold=%.1f%% -> action=%s",
                nearest_ev, probs["cut"] * 100, probs["hike"] * 100,
                probs["hold"] * 100, action)
    return action, prob


_MONTHS = {name: i + 1 for i, name in enumerate(
    ["january", "february", "march", "april", "may", "june",
     "july", "august", "september", "october", "november", "december"])}


def _poly_meeting_probs(query: str) -> dict[tuple[int, int], float]:
    """{(year, month): YES prob} from per-meeting binaries via /public-search.

    Matches questions like 'Fed rate cut by June 2026 meeting?'. The endDate
    field is unreliable on these markets, so the meeting month comes from the
    question text.
    """
    import re
    out: dict[tuple[int, int], float] = {}
    data = _get(f"{POLYMARKET_SEARCH}?q={query}&limit_per_type=10")
    for ev in (data or {}).get("events") or []:
        if ev.get("closed"):
            continue
        for m in ev.get("markets") or []:
            if m.get("closed"):
                continue
            question = m.get("question") or m.get("title") or ""
            match = re.search(
                r"by\s+(january|february|march|april|may|june|july|august|"
                r"september|october|november|december)\s+(\d{4})\s+meeting",
                question, re.IGNORECASE)
            if not match:
                continue
            outcome_prices = m.get("outcomePrices")
            if isinstance(outcome_prices, str):
                try:
                    outcome_prices = json.loads(outcome_prices)
                except Exception:
                    outcome_prices = None
            try:
                prob = float(outcome_prices[0]) if outcome_prices else None
            except (TypeError, ValueError, IndexError):
                prob = None
            if prob is None or not (0 <= prob <= 1):
                continue
            key = (int(match.group(2)), _MONTHS[match.group(1).lower()])
            # Keep the first (most relevant) market per meeting month
            out.setdefault(key, prob)
    return out


def fetch_polymarket_fed_probability() -> Optional[tuple[str, float]]:
    """Return (action, probability) for the NEAREST upcoming FOMC meeting on Polymarket.

    Combines the per-meeting 'Fed rate cut by <Month Year> meeting?' and
    'Fed Rate Hike by <Month Year> Meeting?' binaries for the same nearest
    meeting; hold = 1 - cut - hike. 'Cut by meeting X' ≈ 'cut at meeting X'
    for the nearest meeting, since no earlier meeting exists.
    """
    cut_by_meeting = _poly_meeting_probs("fed+rate+cut")
    hike_by_meeting = _poly_meeting_probs("fed+rate+hike")
    if not cut_by_meeting and not hike_by_meeting:
        logger.info("Polymarket: no per-meeting Fed rate markets found")
        return None

    now = datetime.now(timezone.utc)
    candidates = [k for k in set(cut_by_meeting) | set(hike_by_meeting)
                  if k >= (now.year, now.month)]
    if not candidates:
        logger.info("Polymarket: no future-dated Fed meeting markets")
        return None
    meeting = min(candidates)

    p_cut = cut_by_meeting.get(meeting, 0.0)
    p_hike = hike_by_meeting.get(meeting, 0.0)
    probs = {"cut": p_cut, "hike": p_hike, "hold": max(0.0, 1.0 - p_cut - p_hike)}
    action = max(probs, key=lambda a: probs[a])
    logger.info("Polymarket meeting %d-%02d: cut=%.1f%% hike=%.1f%% hold=%.1f%% -> action=%s",
                meeting[0], meeting[1], p_cut * 100, p_hike * 100,
                probs["hold"] * 100, action)
    return action, probs[action]


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
