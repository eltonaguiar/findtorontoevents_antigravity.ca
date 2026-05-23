#!/usr/bin/env python3
"""
volatile_alt_scanner.py — High-Volatility Altcoin Scanner (Hyperliquid)
=======================================================================
Targets mid-cap altcoins on Hyperliquid with extreme funding, big moves,
and inefficient pricing — the same niche where copy-traders like BLOB
pull +$58 single-trade wins on tokens like TAO/1AOUSDT.

Signals:
  1. Funding rate fade — extreme positive → SHORT, extreme negative → LONG
  2. Momentum continuation — 5%+ in 4h + volume spike → LONG
  3. Mean reversion — down 8%+ in 24h + RSI < 30 → LONG bounce
  4. Breakout — new 24h high + volume > 2x avg → LONG

TP: 4-6%  |  SL: 2-3%  |  Max hold: 12h

API: Hyperliquid REST (no auth required)
  POST https://api.hyperliquid.xyz/info
  {"type": "metaAndAssetCtxs"} — all market data + funding
  {"type": "candleSnapshot", "coin": "TAO", "interval": "1h", "startTime": ms}

Output: standard active_picks.json format with source_system: "volatile_alt_scanner"
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Windows UTF-8 fix
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = _THIS_DIR / "data"
PICKS_FILE = DATA_DIR / "volatile_alt_picks.json"
ACTIVE_PICKS_FILE = DATA_DIR / "active_picks.json"

HL_INFO_URL = "https://api.hyperliquid.xyz/info"

# Exclude top-10 by market cap — we want mid/small caps only
EXCLUDE_COINS = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "DOT",
    # Also exclude stables
    "USDC", "USDT", "DAI", "FDUSD",
}

# Thresholds for token qualification
MIN_VOLUME_24H = 500_000       # $500K daily volume
MIN_ABS_CHANGE_24H = 3.0       # 3% either direction
MIN_ABS_FUNDING = 0.0001       # 0.01% funding rate (extreme)

# Signal-specific thresholds
MOMENTUM_MIN_CHANGE_4H = 5.0   # 5% in 4h for momentum continuation
MEAN_REVERT_MIN_DROP = 8.0     # 8% drop in 24h
MEAN_REVERT_RSI_MAX = 35       # RSI below 35
BREAKOUT_VOL_MULT = 2.0        # Volume > 2x average

# TP/SL for volatile alts (wider than majors)
TP_RANGE = (0.04, 0.06)        # 4-6%
SL_RANGE = (0.02, 0.03)        # 2-3%
MAX_HOLD_HOURS = 12

# Allocation
DEFAULT_ALLOCATION = 200.0     # $200 per pick (small size for volatile alts)
MAX_VOLATILE_PICKS = 8         # Cap concurrent volatile alt picks

# Last-run data-fetch diagnostics. Populated by run_scan() so the CLI entry
# point can distinguish a real-empty market (exit 0 + ::warning::) from a
# data-provider outage (exit 1 + ::error::). Without this the scanner exited
# GitHub Actions GREEN on a total Hyperliquid API failure — "fail-open
# masking". Mirrors etf_scanner.py / bond_scanner.py. Resolver-fix Step 2.
# The Hyperliquid metaAndAssetCtxs fetch is all-or-nothing, so symbols_loaded
# is 0 on an outage (ratio 0.0 -> ::error::) or the full universe size on
# success (ratio 1.0 -> healthy); symbols_requested is a sentinel 1.
LAST_RUN_DIAGNOSTICS: dict = {
    "symbols_requested": 0,
    "symbols_loaded": 0,
    "raw_signals": 0,
}


# ---------------------------------------------------------------------------
# Hyperliquid API helpers
# ---------------------------------------------------------------------------

def _hl_post(payload: dict, timeout: int = 15) -> Optional[dict]:
    """POST to Hyperliquid info API with retries."""
    for attempt in range(3):
        try:
            resp = requests.post(HL_INFO_URL, json=payload, timeout=timeout, headers={
                "Content-Type": "application/json",
            })
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == 2:
                print(f"[HL API] Failed after 3 attempts: {e}")
                return None
            time.sleep(1)


def fetch_meta_and_contexts() -> Optional[Tuple[List[dict], List[dict]]]:
    """Fetch all Hyperliquid perp metadata + asset contexts.
    Returns (meta_list, ctx_list) — parallel arrays indexed by coin position.
    """
    data = _hl_post({"type": "metaAndAssetCtxs"})
    if not data or not isinstance(data, list) or len(data) < 2:
        print("[HL] metaAndAssetCtxs returned unexpected shape")
        return None
    meta_universe = data[0].get("universe", [])
    contexts = data[1]
    if len(meta_universe) != len(contexts):
        print(f"[HL] meta ({len(meta_universe)}) vs ctx ({len(contexts)}) length mismatch")
        return None
    return meta_universe, contexts


def fetch_candles(coin: str, interval: str = "1h", hours_back: int = 24) -> List[dict]:
    """Fetch OHLCV candles for a coin from Hyperliquid."""
    start_ms = int((datetime.now(timezone.utc) - timedelta(hours=hours_back)).timestamp() * 1000)
    data = _hl_post({
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": start_ms,
            "endTime": int(datetime.now(timezone.utc).timestamp() * 1000),
        }
    })
    if not data or not isinstance(data, list):
        return []
    return data


# ---------------------------------------------------------------------------
# Technical indicators (lightweight, no pandas dependency)
# ---------------------------------------------------------------------------

def compute_rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """Compute RSI from a list of closing prices."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    # Use last `period` values
    gains = gains[-period:]
    losses = losses[-period:]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_avg_volume(candles: List[dict]) -> float:
    """Average volume from candle data."""
    vols = []
    for c in candles:
        try:
            v = float(c.get("v", c.get("vlm", 0)) or 0)
            vols.append(v)
        except (ValueError, TypeError):
            pass
    return sum(vols) / len(vols) if vols else 0


def get_24h_high(candles: List[dict]) -> float:
    """Get the highest price in 24h candles."""
    highs = []
    for c in candles:
        try:
            h = float(c.get("h", 0) or 0)
            highs.append(h)
        except (ValueError, TypeError):
            pass
    return max(highs) if highs else 0


def get_recent_closes(candles: List[dict]) -> List[float]:
    """Extract closing prices from candle data."""
    closes = []
    for c in candles:
        try:
            closes.append(float(c.get("c", 0) or 0))
        except (ValueError, TypeError):
            pass
    return closes


def get_4h_change(candles_1h: List[dict]) -> Optional[float]:
    """Compute % change over last 4 hourly candles."""
    if len(candles_1h) < 5:
        return None
    try:
        price_4h_ago = float(candles_1h[-5].get("o", 0) or 0)
        price_now = float(candles_1h[-1].get("c", 0) or 0)
        if price_4h_ago <= 0:
            return None
        return ((price_now - price_4h_ago) / price_4h_ago) * 100
    except (ValueError, TypeError, IndexError):
        return None


def recent_volume(candles_1h: List[dict], hours: int = 4) -> float:
    """Sum of volume over recent N hours."""
    total = 0
    for c in candles_1h[-hours:]:
        try:
            total += float(c.get("v", c.get("vlm", 0)) or 0)
        except (ValueError, TypeError):
            pass
    return total


# ---------------------------------------------------------------------------
# Core scanning logic
# ---------------------------------------------------------------------------

def qualify_tokens(meta: List[dict], ctxs: List[dict]) -> List[dict]:
    """Filter Hyperliquid tokens to those meeting volatile alt criteria.
    Returns list of dicts with coin info + context merged.
    """
    qualified = []
    for m, ctx in zip(meta, ctxs):
        coin = m.get("name", "")
        if coin.upper() in EXCLUDE_COINS:
            continue

        try:
            # dayNtlVlm = 24h notional volume in USD
            vol_24h = float(ctx.get("dayNtlVlm", 0) or 0)
            # prevDayPx = previous day close; markPx = current mark price
            mark_px = float(ctx.get("markPx", 0) or 0)
            prev_px = float(ctx.get("prevDayPx", 0) or 0)
            funding = float(ctx.get("funding", 0) or 0)
            open_interest = float(ctx.get("openInterest", 0) or 0)
        except (ValueError, TypeError):
            continue

        if mark_px <= 0 or prev_px <= 0:
            continue

        pct_change_24h = ((mark_px - prev_px) / prev_px) * 100

        # Apply filters
        if vol_24h < MIN_VOLUME_24H:
            continue
        if abs(pct_change_24h) < MIN_ABS_CHANGE_24H:
            continue
        if abs(funding) < MIN_ABS_FUNDING:
            continue

        qualified.append({
            "coin": coin,
            "mark_price": mark_px,
            "prev_day_price": prev_px,
            "volume_24h": vol_24h,
            "price_change_24h": round(pct_change_24h, 2),
            "funding_rate": funding,
            "open_interest": open_interest,
            "max_leverage": m.get("maxLeverage", 1),
        })

    # Sort by absolute price change (biggest movers first)
    qualified.sort(key=lambda x: abs(x["price_change_24h"]), reverse=True)
    print(f"[Qualify] {len(qualified)} tokens passed volatile alt filters")
    for q in qualified[:10]:
        print(f"  {q['coin']:>8s}  chg={q['price_change_24h']:+.1f}%  vol=${q['volume_24h']:,.0f}  funding={q['funding_rate']:.6f}")
    return qualified


def generate_signals(qualified: List[dict]) -> List[dict]:
    """Run 4 signal generators on qualified tokens. Returns pick dicts."""
    signals = []
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).isoformat()

    for token in qualified:
        coin = token["coin"]
        mark = token["mark_price"]
        funding = token["funding_rate"]
        pct_24h = token["price_change_24h"]
        vol_24h = token["volume_24h"]

        # Fetch 1h candles for detailed analysis
        candles = fetch_candles(coin, interval="1h", hours_back=25)
        closes = get_recent_closes(candles)
        rsi = compute_rsi(closes)
        change_4h = get_4h_change(candles)
        avg_vol = compute_avg_volume(candles)
        high_24h = get_24h_high(candles)
        vol_4h = recent_volume(candles, hours=4)
        avg_vol_4h = (avg_vol * 4) if avg_vol > 0 else 1

        # --- Signal 1: Funding Rate Fade ---
        if abs(funding) >= 0.0001:  # 0.01%+ = extreme funding
            if funding > 0:
                # Extreme positive funding → market overleveraged long → SHORT
                direction = "SHORT"
                signal_type = "SELL"
                tp_pct = 0.05  # 5% TP
                sl_pct = 0.025
                confidence = min(0.85, 0.65 + abs(funding) * 100)
                reason = f"Extreme positive funding {funding:.4%} — overleveraged longs, fade SHORT"
            else:
                # Extreme negative funding → overleveraged short → LONG
                direction = "LONG"
                signal_type = "BUY"
                tp_pct = 0.05
                sl_pct = 0.025
                confidence = min(0.85, 0.65 + abs(funding) * 100)
                reason = f"Extreme negative funding {funding:.4%} — overleveraged shorts, fade LONG"

            signals.append(_make_pick(
                coin=coin, mark=mark, direction=direction, signal_type=signal_type,
                tp_pct=tp_pct, sl_pct=sl_pct, confidence=confidence,
                strategy="hl_funding_fade", reason=reason,
                token=token, rsi=rsi, date_str=now_str, iso_str=now_iso,
            ))

        # --- Signal 2: Momentum Continuation ---
        if change_4h is not None and change_4h >= MOMENTUM_MIN_CHANGE_4H:
            # Volume must be spiking too (recent 4h vol > 1.5x average 4h)
            if avg_vol_4h > 0 and vol_4h > 1.5 * avg_vol_4h:
                confidence = min(0.80, 0.55 + (change_4h / 100) + (vol_4h / avg_vol_4h - 1) * 0.1)
                reason = (f"4h momentum +{change_4h:.1f}% with volume spike "
                          f"({vol_4h/avg_vol_4h:.1f}x avg) — ride the wave")
                signals.append(_make_pick(
                    coin=coin, mark=mark, direction="LONG", signal_type="BUY",
                    tp_pct=0.06, sl_pct=0.03, confidence=confidence,
                    strategy="hl_momentum_continuation", reason=reason,
                    token=token, rsi=rsi, date_str=now_str, iso_str=now_iso,
                ))

        # --- Signal 3: Mean Reversion ---
        if pct_24h <= -MEAN_REVERT_MIN_DROP and rsi is not None and rsi < MEAN_REVERT_RSI_MAX:
            confidence = min(0.82, 0.60 + (abs(pct_24h) / 100) + (30 - rsi) / 100)
            reason = (f"Down {pct_24h:.1f}% in 24h with RSI={rsi:.0f} — "
                      f"oversold bounce setup")
            signals.append(_make_pick(
                coin=coin, mark=mark, direction="LONG", signal_type="BUY",
                tp_pct=0.05, sl_pct=0.025, confidence=confidence,
                strategy="hl_mean_reversion", reason=reason,
                token=token, rsi=rsi, date_str=now_str, iso_str=now_iso,
            ))

        # --- Signal 4: Breakout ---
        if high_24h > 0 and mark >= high_24h * 0.998:  # Within 0.2% of 24h high
            if avg_vol_4h > 0 and vol_4h > BREAKOUT_VOL_MULT * avg_vol_4h:
                confidence = min(0.78, 0.55 + (vol_4h / avg_vol_4h - 1) * 0.1)
                reason = (f"Breaking 24h high ${high_24h:.4f} with {vol_4h/avg_vol_4h:.1f}x "
                          f"volume — breakout LONG")
                signals.append(_make_pick(
                    coin=coin, mark=mark, direction="LONG", signal_type="BUY",
                    tp_pct=0.06, sl_pct=0.03, confidence=confidence,
                    strategy="hl_breakout", reason=reason,
                    token=token, rsi=rsi, date_str=now_str, iso_str=now_iso,
                ))

    print(f"[Signals] Generated {len(signals)} raw signals")
    return signals


def _make_pick(*, coin: str, mark: float, direction: str, signal_type: str,
               tp_pct: float, sl_pct: float, confidence: float,
               strategy: str, reason: str, token: dict,
               rsi: Optional[float], date_str: str, iso_str: str) -> dict:
    """Build a pick dict in standard alpha_engine format."""
    if direction == "LONG":
        tp_price = mark * (1 + tp_pct)
        sl_price = mark * (1 - sl_pct)
    else:
        tp_price = mark * (1 - tp_pct)
        sl_price = mark * (1 + sl_pct)

    symbol = f"{coin}USDT"
    pick_id = f"{strategy}::{symbol}::{date_str}"

    return {
        "id": pick_id,
        "strategy": strategy,
        "symbol": symbol,
        "category": "crypto",
        "signal_type": signal_type,
        "direction": direction,
        "entry_price": mark,
        "entry_date": date_str,
        "take_profit": round(tp_price, 6),
        "stop_loss": round(sl_price, 6),
        "confidence": round(confidence, 3),
        "ml_score": None,
        "exit_price": None,
        "exit_date": None,
        "exit_reason": None,
        "pnl_pct": None,
        "pnl_dollar": None,
        "high_water_mark": None,
        "status": "OPEN",
        "hold_days": None,
        "allocation": DEFAULT_ALLOCATION,
        "position_sizing": "fixed",
        "risk_per_trade_pct": 0.02,
        "forward_test_only": True,
        "source": "hyperliquid",
        "source_system": "volatile_alt_scanner",
        "reason": reason,
        "max_hold_hours": MAX_HOLD_HOURS,
        "timestamp": iso_str,
        # Volatile alt metadata
        "funding_rate": token["funding_rate"],
        "volume_24h": token["volume_24h"],
        "price_change_24h": token["price_change_24h"],
        "open_interest": token["open_interest"],
        "rsi": rsi,
        "exchange": "hyperliquid",
    }


# ---------------------------------------------------------------------------
# Dedup + merge into active_picks.json
# ---------------------------------------------------------------------------

def dedup_signals(signals: List[dict], existing: List[dict]) -> List[dict]:
    """Remove signals that duplicate an already-open pick (same strategy + symbol)."""
    existing_keys = set()
    for p in existing:
        key = f"{p.get('strategy', '')}::{p.get('symbol', '')}"
        existing_keys.add(key)

    new = []
    for s in signals:
        key = f"{s['strategy']}::{s['symbol']}"
        if key not in existing_keys:
            new.append(s)
            existing_keys.add(key)  # prevent intra-batch dupes too
    return new


def _inline_quality_gate(picks: List[dict], existing: List[dict]) -> List[dict]:
    """Inline quality gates: confidence floor, stablecoin filter, kill list, dedup."""
    STABLES = {"USDCUSDT", "USDTUSDT", "BUSDUSDT", "DAIUSDT", "FDUSDUSDT", "TUSDUSDT"}
    MIN_CONF = 0.70
    # Load kill list (best-effort)
    kill_list = set()
    try:
        kl_path = DATA_DIR / "core_whitelist.json"
        if kl_path.exists():
            import json as _j
            wl = _j.loads(kl_path.read_text(encoding="utf-8"))
            _safe = set()
            for _sg in ("protected_strategies", "core_strategies", "incubator_strategies"):
                _safe.update(s.lower() for s in wl.get(_sg, []) if isinstance(s, str))
            for _ks in wl.get("kill_list", []):
                _kb = _ks.split("::", 1)[1].lower() if "::" in _ks else _ks.lower()
                if _kb not in _safe:
                    kill_list.add(_ks.lower())
                    if "::" in _ks:
                        kill_list.add(_kb)
    except Exception:
        pass
    existing_ids = {p.get("id", "") for p in existing}
    filtered = []
    for p in picks:
        sym = p.get("symbol", "")
        strat = (p.get("strategy") or "").lower()
        conf = float(p.get("confidence", 0) or 0)
        if conf < MIN_CONF:
            print(f"  [QUALITY GATE] Rejected {sym}: conf={conf:.2f} < {MIN_CONF}")
            continue
        if sym in STABLES:
            print(f"  [QUALITY GATE] Rejected {sym}: stablecoin")
            continue
        if strat in kill_list:
            print(f"  [QUALITY GATE] Rejected {sym}: strategy '{strat}' in kill list")
            continue
        if p.get("id", "") in existing_ids:
            continue
        filtered.append(p)
    return filtered


def merge_into_active_picks(new_picks: List[dict]) -> int:
    """Merge new volatile alt picks into the main active_picks.json.
    Returns count of picks actually added.
    """
    if not new_picks:
        return 0

    # Load existing active picks
    existing = []
    if ACTIVE_PICKS_FILE.exists():
        try:
            with open(ACTIVE_PICKS_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    # Apply quality gates before merge
    new_picks = _inline_quality_gate(new_picks, existing)
    if not new_picks:
        print("[QUALITY GATE] All picks rejected by quality gates")
        return 0

    # Count current volatile alt picks
    current_va = [p for p in existing if p.get("source_system") == "volatile_alt_scanner"
                  and p.get("status") == "OPEN"]
    slots = MAX_VOLATILE_PICKS - len(current_va)
    if slots <= 0:
        print(f"[Merge] Already at max volatile alt picks ({MAX_VOLATILE_PICKS}), skipping")
        return 0

    # Dedup against existing
    deduped = dedup_signals(new_picks, existing)
    # Sort by confidence, take best
    deduped.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    to_add = deduped[:slots]

    if to_add:
        existing.extend(to_add)

        # Score new picks with elite_scorer so they don't ship without elite_score
        try:
            from elite_scorer import enrich_picks_with_elite_score
            enrich_picks_with_elite_score(to_add, str(DATA_DIR))
            print(f"[Merge] Elite-scored {len(to_add)} new volatile alt picks")
        except Exception as _es_err:
            print(f"[Merge] Elite scoring failed (non-fatal): {_es_err}")

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(ACTIVE_PICKS_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, default=str)
        print(f"[Merge] Added {len(to_add)} volatile alt picks to active_picks.json")
    return len(to_add)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_scan(merge: bool = True) -> List[dict]:
    """Full scan pipeline. Returns generated signals."""
    print("=" * 60)
    print("  VOLATILE ALT SCANNER — Hyperliquid High-Vol Alts")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    # Step 1: Fetch all Hyperliquid perp data
    result = fetch_meta_and_contexts()
    # symbols_requested=1 is a sentinel: the metaAndAssetCtxs call is
    # all-or-nothing, so loaded=0 on failure (ratio 0.0) vs the full
    # universe size on success (ratio 1.0).
    LAST_RUN_DIAGNOSTICS["symbols_requested"] = 1
    LAST_RUN_DIAGNOSTICS["symbols_loaded"] = 0
    LAST_RUN_DIAGNOSTICS["raw_signals"] = 0
    if result is None:
        print("[FATAL] Could not fetch Hyperliquid market data")
        return []

    meta, ctxs = result
    LAST_RUN_DIAGNOSTICS["symbols_loaded"] = len(meta)
    print(f"[HL] Loaded {len(meta)} perpetual markets")

    # Step 2: Qualify tokens
    qualified = qualify_tokens(meta, ctxs)
    if not qualified:
        print("[DONE] No tokens qualify — market is calm")
        return []

    # Step 3: Generate signals
    signals = generate_signals(qualified)
    LAST_RUN_DIAGNOSTICS["raw_signals"] = len(signals)

    # Step 4: Save standalone picks file
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PICKS_FILE, "w", encoding="utf-8") as f:
        json.dump(signals, f, indent=2, default=str)
    print(f"[Save] Wrote {len(signals)} signals to {PICKS_FILE.name}")

    # Step 5: Merge into active_picks.json
    if merge and signals:
        added = merge_into_active_picks(signals)
        print(f"[Final] {added} new picks merged into active_picks.json")

    # Summary
    print("\n" + "=" * 60)
    for s in signals:
        emoji = "LONG" if s["direction"] == "LONG" else "SHORT"
        print(f"  [{emoji:>5}] {s['symbol']:>12s}  @ ${s['entry_price']:.4f}  "
              f"TP=${s['take_profit']:.4f}  SL=${s['stop_loss']:.4f}  "
              f"conf={s['confidence']:.0%}  | {s['strategy']}")
    print("=" * 60)

    return signals


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Volatile Alt Scanner — Hyperliquid")
    parser.add_argument("--no-merge", action="store_true",
                        help="Don't merge into active_picks.json (dry run)")
    args = parser.parse_args()
    picks = run_scan(merge=not args.no_merge)
    print(f"\nTotal signals: {len(picks)}")

    # ── fail-open guard ────────────────────────────────────────────────────
    # Stop the scanner from exiting GitHub Actions GREEN on a Hyperliquid API
    # outage (which otherwise looks identical to a calm market). Mirrors the
    # ratio logic in etf_scanner.py / bond_scanner.py. Resolver-fix Step 2.
    _requested = max(1, LAST_RUN_DIAGNOSTICS["symbols_requested"])
    _loaded = LAST_RUN_DIAGNOSTICS["symbols_loaded"]
    _ratio = _loaded / _requested
    if _ratio < 0.5:
        print(f"::error::DATA FETCH FAILURE — Hyperliquid metaAndAssetCtxs "
              f"returned no market data; refusing to exit green on missing "
              f"data")
        sys.exit(1)
    if LAST_RUN_DIAGNOSTICS["raw_signals"] == 0:
        print(f"::warning::Volatile alt scanner produced 0 raw signals on "
              f"healthy data ({_loaded} perp markets loaded) — real-empty "
              f"market, not a data failure")
