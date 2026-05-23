#!/usr/bin/env python3
"""
Opt-in sidecar: Polymarket BTC 5-minute up/down signal agent (DRY_RUN only).

Inspired by JLowo/gengar_polymarket_bot architecture:
  - Quarter-Kelly sizing
  - Brownian-motion probability model with calibrated volatility
  - Circuit breaker (max 3 consecutive losses before halt)
  - CLOB v2 read-only (no private key required in dry-run mode)

## Wiring Plan
Target caller: prediction_market_agents/orchestrator.py (aggregate_signals)
Wire-up: read data/btc_updown_signals.json; if signal.edge >= 0.08 and DRY_RUN=false,
         pass to prediction_market_agents/cross_market_consensus.py for confirmation
Expected PR/date: after ≥4 weeks of dry-run validation + paper P&L ≥0 (target 2026-07-01)

Environment vars:
  DRY_RUN=true (default, NEVER trade live without explicit =false)
  PM_BTC_SYMBOLS=BTC-UP-5MIN,BTC-DOWN-5MIN  (market slugs to watch)
  PM_MIN_EDGE=0.06       (minimum edge required to signal)
  PM_MAX_KELLY_FRACTION=0.25  (quarter-Kelly cap)
  PM_BANKROLL=100        (virtual bankroll for sizing)
  PM_CIRCUIT_BREAKER=3   (consecutive loss limit)
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_OUT = Path(__file__).resolve().parent / "data" / "btc_updown_signals.json"

DRY_RUN = os.environ.get("DRY_RUN", "true").lower() not in ("false", "0", "no")
CLOB_HOST = os.environ.get("CLOB_HOST", "https://clob.polymarket.com")
PM_MIN_EDGE = float(os.environ.get("PM_MIN_EDGE", "0.06"))
PM_MAX_KELLY = float(os.environ.get("PM_MAX_KELLY_FRACTION", "0.25"))
PM_BANKROLL = float(os.environ.get("PM_BANKROLL", "100.0"))
PM_CIRCUIT_BREAKER = int(os.environ.get("PM_CIRCUIT_BREAKER", "3"))

_BINANCE_FALLBACK_CHAIN = [
    "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
    "https://api1.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
    "https://api2.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
    "https://api3.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
]


def _fetch_btc_price() -> float | None:
    """Fetch BTC spot price with 4-endpoint fallback chain per API Failover Rule."""
    try:
        import urllib.request

        for url in _BINANCE_FALLBACK_CHAIN:
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310
                    data = json.loads(resp.read())
                    return float(data["price"])
            except Exception:
                continue
        # CoinGecko fallback
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        with urllib.request.urlopen(url, timeout=8) as resp:  # noqa: S310
            data = json.loads(resp.read())
            return float(data["bitcoin"]["usd"])
    except Exception as exc:
        log.warning("BTC price fetch failed: %s", exc)
        return None


def _fetch_clob_market(market_slug: str) -> dict | None:
    """Fetch Polymarket CLOB v2 market data (read-only, no key needed)."""
    try:
        import urllib.request
        import urllib.parse

        url = f"{CLOB_HOST}/markets?slug={urllib.parse.quote(market_slug)}"
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read())
            markets = data if isinstance(data, list) else data.get("data", [])
            return markets[0] if markets else None
    except Exception as exc:
        log.warning("CLOB market fetch failed for %s: %s", market_slug, exc)
        return None


def _brownian_probability(
    current_price: float,
    strike_price: float,
    vol_daily: float,
    minutes_remaining: int,
) -> float:
    """
    Log-normal probability BTC ends above strike at expiry.
    Uses Brownian motion model: P(S_T > K) = N(d2)
    where d2 = (ln(S/K) + (- 0.5*sigma^2)*T) / (sigma * sqrt(T))
    """
    if minutes_remaining <= 0 or current_price <= 0 or strike_price <= 0:
        return 0.5

    T = minutes_remaining / (252 * 390)  # fraction of trading year
    sigma = vol_daily * math.sqrt(T / (1 / 390))  # rescale daily vol to T

    try:
        d2 = (math.log(current_price / strike_price) - 0.5 * sigma ** 2 * T) / (
            sigma * math.sqrt(T)
        )
        # Normal CDF approximation (Abramowitz & Stegun)
        return _norm_cdf(d2)
    except (ZeroDivisionError, ValueError):
        return 0.5


def _norm_cdf(x: float) -> float:
    """Approximation of the standard normal CDF."""
    t = 1.0 / (1.0 + 0.2316419 * abs(x))
    poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
    cdf = 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * x * x) * poly
    return cdf if x >= 0 else 1.0 - cdf


def _quarter_kelly(p_win: float, b_odds: float) -> float:
    """Quarter-Kelly fraction: f* = (p*b - q) / b * 0.25"""
    q = 1.0 - p_win
    kelly = (p_win * b_odds - q) / b_odds
    return max(0.0, min(kelly * 0.25, PM_MAX_KELLY))


def _derive_signal(
    btc_price: float,
    market_data: dict | None,
    side: str,
    vol_daily: float = 0.04,
) -> dict:
    """Build a signal dict for one side (UP or DOWN) of a 5-min BTC market."""
    now_utc = datetime.now(timezone.utc)
    base = {
        "side": side,
        "btc_spot": btc_price,
        "generated_at": now_utc.isoformat(),
        "dry_run": DRY_RUN,
        "signal": "no_edge",
        "edge": 0.0,
        "kelly_fraction": 0.0,
        "size_usdc": 0.0,
    }

    if market_data is None:
        base["signal"] = "market_unavailable"
        return base

    tokens = market_data.get("tokens", [])
    if not tokens:
        base["signal"] = "no_tokens"
        return base

    # Find YES token price (the "up" side market)
    yes_token = next((t for t in tokens if t.get("outcome", "").upper() in ("YES", "UP")), tokens[0])
    market_price = float(yes_token.get("price", 0.5))
    strike = float(market_data.get("question", {}).get("strike", btc_price) if isinstance(market_data.get("question"), dict) else btc_price)
    minutes_remaining = 5  # default for 5-min markets

    end_date_ms = market_data.get("end_date_iso") or market_data.get("endDateIso")
    if end_date_ms:
        try:
            import re
            ts_str = str(end_date_ms)
            end_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            minutes_remaining = max(1, int((end_ts - now_utc).total_seconds() / 60))
        except Exception:
            pass

    # Model probability
    model_prob = _brownian_probability(btc_price, strike, vol_daily, minutes_remaining)
    if side.upper() == "DOWN":
        model_prob = 1.0 - model_prob

    edge = model_prob - market_price
    if abs(edge) < PM_MIN_EDGE:
        base.update({"signal": "no_edge", "edge": round(edge, 4), "model_prob": round(model_prob, 4), "market_price": market_price})
        return base

    # Kelly sizing
    payout_odds = (1.0 - market_price) / market_price if market_price < 1 else 1.0
    kelly_f = _quarter_kelly(model_prob, payout_odds)
    size = round(PM_BANKROLL * kelly_f, 2)

    base.update({
        "signal": "buy" if edge > 0 else "sell",
        "edge": round(edge, 4),
        "model_prob": round(model_prob, 4),
        "market_price": market_price,
        "kelly_fraction": round(kelly_f, 4),
        "size_usdc": size,
        "minutes_remaining": minutes_remaining,
        "market_id": market_data.get("condition_id") or market_data.get("id"),
        "token_id": yes_token.get("token_id"),
    })
    return base


def _load_circuit_state() -> dict:
    state_path = DATA_OUT.parent / "btc_agent_circuit_state.json"
    if state_path.exists():
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"consecutive_losses": 0, "halted_until": None}


def _check_circuit_breaker() -> bool:
    """Return True if circuit breaker is tripped (should skip this iteration)."""
    state = _load_circuit_state()
    if state.get("consecutive_losses", 0) >= PM_CIRCUIT_BREAKER:
        halted_until = state.get("halted_until")
        if halted_until:
            try:
                resume_ts = datetime.fromisoformat(halted_until)
                if datetime.now(timezone.utc) < resume_ts:
                    log.warning("Circuit breaker active until %s — skipping", halted_until)
                    return True
            except Exception:
                pass
    return False


def run(*, vol_daily: float = 0.04) -> dict:
    """Main entry point. Returns the full signal payload written to disk."""
    now_utc = datetime.now(timezone.utc)

    if not DRY_RUN:
        log.error("LIVE MODE NOT SUPPORTED — set DRY_RUN=true or remove DRY_RUN=false")
        raise RuntimeError("Live trading requires a dedicated wallet key flow. Keep DRY_RUN=true.")

    log.info("BTC up/down agent starting (DRY_RUN=%s)", DRY_RUN)

    if _check_circuit_breaker():
        payload = {
            "generated_at": now_utc.isoformat(),
            "dry_run": True,
            "status": "circuit_breaker_tripped",
            "signals": [],
        }
        DATA_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    btc_price = _fetch_btc_price()
    if btc_price is None:
        payload = {
            "generated_at": now_utc.isoformat(),
            "dry_run": True,
            "status": "btc_price_unavailable",
            "signals": [],
        }
        DATA_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    log.info("BTC spot: $%.2f", btc_price)

    # Fetch CLOB market data for BTC 5-min markets
    up_slug = os.environ.get("PM_BTC_UP_SLUG", "btc-up-1")
    dn_slug = os.environ.get("PM_BTC_DOWN_SLUG", "btc-down-1")

    up_market = _fetch_clob_market(up_slug)
    dn_market = _fetch_clob_market(dn_slug)

    up_signal = _derive_signal(btc_price, up_market, "UP", vol_daily)
    dn_signal = _derive_signal(btc_price, dn_market, "DOWN", vol_daily)

    payload = {
        "generated_at": now_utc.isoformat(),
        "dry_run": True,
        "btc_spot": btc_price,
        "status": "ok",
        "signals": [up_signal, dn_signal],
        "_note": "All signals are dry-run only. Set DRY_RUN=false only after 4-week paper validation with PF>=1.5.",
    }

    DATA_OUT.parent.mkdir(parents=True, exist_ok=True)
    DATA_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info("Wrote %s signals to %s", len(payload["signals"]), DATA_OUT)
    return payload


if __name__ == "__main__":
    result = run()
    actionable = [s for s in result.get("signals", []) if s.get("signal") == "buy"]
    log.info("Actionable signals (DRY RUN): %d", len(actionable))
    for sig in actionable:
        log.info("  %s edge=%.3f size=$%.2f", sig["side"], sig["edge"], sig["size_usdc"])
