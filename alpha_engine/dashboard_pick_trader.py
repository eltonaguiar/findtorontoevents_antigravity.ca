#!/usr/bin/env python3
"""
Dashboard Pick Trader - Enters top-scoring picks from the audit dashboard into portfolios.

The portfolio tracker only enters Alpha Engine picks, but the BEST picks come from
super_signals (68.6% WR, PF 3.78), claude_gainer_st (72.3% WR, PF 6.23), and other
proven systems visible on the dashboard. This module bridges that gap.

Flow:
1. Read dashboard_payload.json (updated by audit-dashboard CI)
2. Filter for crypto picks with score >= 70, confidence >= 0.60
3. Prefer picks from proven systems (super_signals, claude_gainer_st, etc.)
4. Validate with live Binance price (skip stale/chasing/over trades)
5. Enter up to 2 new positions per cycle into both 1x and 20x portfolios
6. Log all decisions
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

# ---------- Config ----------

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DASHBOARD_PAYLOAD = os.path.join(os.path.dirname(__file__), "..", "audit_trail", "data", "dashboard_payload.json")
PORTFOLIO_1X_FILE = os.path.join(DATA_DIR, "portfolio_1x.json")
PORTFOLIO_20X_FILE = os.path.join(DATA_DIR, "portfolio_20x.json")
LOG_FILE = os.path.join(DATA_DIR, "dashboard_trader_log.json")

# Proven systems with validated forward WR >= 60% and significant sample size
PROVEN_SYSTEMS = [
    "super_signals",
    "claude_gainer_st",
    "battleground",
    "kimi_claw_research",
    "ml_crypto_predictor",
    "multi_asset_institutional",
    "alpha_engine",
]

MIN_SCORE = 70
MIN_CONFIDENCE = 0.60
MAX_NEW_ENTRIES_PER_CYCLE = 2
MAX_AGE_HOURS = 24
MAX_CHASE_PCT = 0.03  # Skip if live price is >3% above entry
MAX_POSITIONS_1X = 3
MAX_POSITIONS_20X = 3

# Position sizing
POSITION_SIZE_PCT_1X = 0.02   # 2% of balance
POSITION_SIZE_PCT_20X = 0.01  # 1% of balance


def fetch_live_prices():
    """Fetch live prices with 3+ API fallback chain (CRITICAL RULE)."""
    apis = [
        ("https://api.binance.com/api/v3/ticker/price", "binance"),
        ("https://api1.binance.com/api/v3/ticker/price", "binance_mirror1"),
        ("https://api2.binance.com/api/v3/ticker/price", "binance_mirror2"),
        ("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,dogecoin,ripple,cardano,avalanche-2,chainlink,polkadot,near,shiba-inu,filecoin,bnb,fetch-ai,render-token&vs_currencies=usd", "coingecko"),
        ("https://api.kucoin.com/api/v1/market/allTickers", "kucoin"),
    ]

    for url, source in apis:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())

            if source.startswith("binance"):
                return {t["symbol"]: float(t["price"]) for t in data}
            elif source == "coingecko":
                mapping = {
                    "bitcoin": "BTCUSDT", "ethereum": "ETHUSDT", "solana": "SOLUSDT",
                    "dogecoin": "DOGEUSDT", "ripple": "XRPUSDT", "cardano": "ADAUSDT",
                    "avalanche-2": "AVAXUSDT", "chainlink": "LINKUSDT", "polkadot": "DOTUSDT",
                    "near": "NEARUSDT", "shiba-inu": "SHIBUSDT", "filecoin": "FILUSDT",
                    "bnb": "BNBUSDT", "fetch-ai": "FETUSDT", "render-token": "RENDERUSDT",
                }
                prices = {}
                for cg_id, sym in mapping.items():
                    if cg_id in data and "usd" in data[cg_id]:
                        prices[sym] = float(data[cg_id]["usd"])
                return prices
            elif source == "kucoin":
                prices = {}
                for t in data.get("data", {}).get("ticker", []):
                    sym = t.get("symbol", "").replace("-", "")
                    if sym.endswith("USDT") and t.get("last"):
                        prices[sym] = float(t["last"])
                if prices:
                    return prices
        except Exception as e:
            print(f"  [API] {source} failed: {e}")
            continue

    return {}


def normalize_symbol(sym):
    """Normalize symbol to Binance format (BTCUSDT)."""
    sym = sym.upper().replace("-USD", "USDT").replace("/", "")
    if not sym.endswith("USDT") and "USD" in sym and "=" not in sym:
        sym += "T"
    return sym


def get_score_tier(score):
    """Return tier label for a score."""
    if score >= 80:
        return "80+"
    elif score >= 70:
        return "70-79"
    elif score >= 60:
        return "60-69"
    else:
        return "50-59"


def load_json(path):
    """Load JSON file safely."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [WARN] Could not load {path}: {e}")
        return None


def save_json(path, data):
    """Save JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def load_dashboard_picks():
    """Load and filter picks from dashboard payload."""
    payload = load_json(DASHBOARD_PAYLOAD)
    if not payload:
        print("[DASHBOARD TRADER] Could not load dashboard payload")
        return []

    active_picks = payload.get("picks", {}).get("active", [])
    if not active_picks:
        print("[DASHBOARD TRADER] No active picks in dashboard payload")
        return []

    print(f"[DASHBOARD TRADER] {len(active_picks)} total active picks in dashboard")

    # Filter: crypto only, score >= MIN_SCORE, confidence >= MIN_CONFIDENCE
    qualified = []
    for pick in active_picks:
        if not isinstance(pick, dict):
            continue

        asset_class = pick.get("asset_class", "").upper()
        if asset_class != "CRYPTO":
            continue

        score = float(pick.get("score", 0) or 0)
        confidence = float(pick.get("confidence", 0) or 0)
        status = pick.get("status", "").upper()

        if status != "OPEN":
            continue
        if score < MIN_SCORE:
            continue
        if confidence < MIN_CONFIDENCE:
            continue

        # Must have valid entry/tp/sl
        entry = float(pick.get("entry_price", 0) or 0)
        tp = float(pick.get("take_profit", 0) or 0)
        sl = float(pick.get("stop_loss", 0) or 0)
        if entry <= 0 or tp <= 0 or sl <= 0:
            continue

        # LONG only for now (SHORT crypto underperforms in forward tests)
        direction = str(pick.get("direction", "")).upper()
        if direction not in ("LONG", "BUY"):
            continue

        qualified.append(pick)

    print(f"[DASHBOARD TRADER] {len(qualified)} picks pass filters (score>={MIN_SCORE}, conf>={MIN_CONFIDENCE}, crypto, LONG)")

    # Sort: proven systems first, then by score descending
    def sort_key(p):
        system = p.get("source_system", "")
        is_proven = 1 if system in PROVEN_SYSTEMS else 0
        return (-is_proven, -float(p.get("score", 0) or 0))

    qualified.sort(key=sort_key)
    return qualified


def check_cooldown(portfolio):
    """Check if portfolio is in loss cooldown (from emergency fixes)."""
    closed = portfolio.get("closed_positions", [])
    if not closed:
        return False

    consecutive_losses = 0
    for cp in reversed(closed[-10:]):
        pnl = cp.get("pnl_pct", 0) or cp.get("pnl_usdt", 0) or 0
        if pnl < 0:
            consecutive_losses += 1
        else:
            break

    if consecutive_losses >= 2:
        last_close = closed[-1].get("close_time", "")
        try:
            last_time = datetime.fromisoformat(last_close)
            hours_since = (datetime.now(timezone.utc) - last_time).total_seconds() / 3600
            if hours_since < 1:
                print(f"  [COOLDOWN] {consecutive_losses} consecutive losses, last {hours_since:.1f}h ago - waiting")
                return True
        except Exception:
            pass

    return False


def get_held_symbols(portfolio):
    """Get set of normalized symbols currently held."""
    held = set()
    for pos in portfolio.get("positions", {}).values():
        held.add(normalize_symbol(pos.get("symbol", "")))
    return held


def enter_position(portfolio, pick, live_price, leverage, size_pct):
    """Enter a position into a portfolio. Returns (position_dict, skip_reason)."""
    symbol = pick["symbol"]
    norm_sym = normalize_symbol(symbol)
    now = datetime.now(timezone.utc)

    entry_price_pick = float(pick.get("entry_price", 0))
    tp = float(pick.get("take_profit", 0))
    sl = float(pick.get("stop_loss", 0))
    score = float(pick.get("score", 0))
    confidence = float(pick.get("confidence", 0))
    direction = str(pick.get("direction", "LONG")).upper()
    if direction == "BUY":
        direction = "LONG"

    age_hours = float(pick.get("age_hours", 0) or 0)

    # Skip stale picks (> 24h old)
    if age_hours > MAX_AGE_HOURS:
        return None, f"stale ({age_hours:.1f}h old > {MAX_AGE_HOURS}h max)"

    # Validate TP/SL with live price
    if direction == "LONG":
        if live_price >= tp:
            return None, f"TP already hit (live={live_price:.6f} >= tp={tp:.6f})"
        if live_price <= sl:
            return None, f"SL already hit (live={live_price:.6f} <= sl={sl:.6f})"
    else:
        if live_price <= tp:
            return None, f"TP already hit (live={live_price:.6f} <= tp={tp:.6f})"
        if live_price >= sl:
            return None, f"SL already hit (live={live_price:.6f} >= sl={sl:.6f})"

    # Skip if chasing (live price >3% above entry for LONG)
    if direction == "LONG":
        chase_pct = (live_price - entry_price_pick) / entry_price_pick
        if chase_pct > MAX_CHASE_PCT:
            return None, f"chasing (+{chase_pct*100:.1f}% above entry, max {MAX_CHASE_PCT*100:.0f}%)"
    else:
        chase_pct = (entry_price_pick - live_price) / entry_price_pick
        if chase_pct > MAX_CHASE_PCT:
            return None, f"chasing ({chase_pct*100:.1f}% below entry, max {MAX_CHASE_PCT*100:.0f}%)"

    # Use LIVE price as entry (not stale dashboard price)
    entry_price = live_price

    # Enforce min/max stop distance
    min_stop_pct = 0.02
    max_stop_pct = 0.05
    if entry_price > 0 and sl > 0:
        stop_dist = abs(entry_price - sl) / entry_price
        if stop_dist < min_stop_pct:
            if direction == "LONG":
                sl = entry_price * (1 - min_stop_pct)
            else:
                sl = entry_price * (1 + min_stop_pct)
        if stop_dist > max_stop_pct:
            if direction == "LONG":
                sl = entry_price * (1 - max_stop_pct)
            else:
                sl = entry_price * (1 + max_stop_pct)
            # Maintain at least 2:1 R:R
            risk = abs(entry_price - sl)
            if direction == "LONG":
                tp = max(tp, entry_price + risk * 2)
            else:
                tp = min(tp, entry_price - risk * 2)

    # Position sizing
    balance = float(portfolio.get("current_balance", 10000))
    position_size = round(balance * size_pct, 2)

    position = {
        "symbol": norm_sym,
        "strategy": pick.get("strategy", "unknown"),
        "direction": direction,
        "entry_price": entry_price,
        "take_profit": tp,
        "stop_loss": sl,
        "score": score,
        "score_tier": get_score_tier(score),
        "position_size": position_size,
        "leverage": leverage,
        "opened_at": now.isoformat(),
        "current_pnl_pct": 0,
        "current_pnl_usdt": 0,
        "hwm_price": entry_price,
        "trailing_stop": 0,
        "high_water_mark_pnl": 0,
        "ml_score_at_entry": confidence,
        "conformal_multiplier": 1.0,
        "source_system": pick.get("source_system", "unknown"),
        "dashboard_score": score,
        "entered_via": "dashboard_pick_trader",
    }

    return position, None


def run_trader():
    """Main trader logic - fetch dashboard picks, enter into portfolios."""
    now = datetime.now(timezone.utc)
    log_entries = []

    print(f"\n{'='*60}")
    print(f"DASHBOARD PICK TRADER - {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")

    # Load dashboard picks
    picks = load_dashboard_picks()
    if not picks:
        log_entries.append({"time": now.isoformat(), "action": "no_picks", "detail": "No qualifying picks found"})
        save_log(log_entries)
        return

    # Load portfolios
    portfolio_1x = load_json(PORTFOLIO_1X_FILE)
    portfolio_20x = load_json(PORTFOLIO_20X_FILE)

    if not portfolio_1x or not portfolio_20x:
        print("[DASHBOARD TRADER] Could not load portfolio files")
        return

    # Check cooldowns
    cooldown_1x = check_cooldown(portfolio_1x)
    cooldown_20x = check_cooldown(portfolio_20x)

    # Get currently held symbols
    held_1x = get_held_symbols(portfolio_1x)
    held_20x = get_held_symbols(portfolio_20x)
    open_count_1x = len(portfolio_1x.get("positions", {}))
    open_count_20x = len(portfolio_20x.get("positions", {}))

    print(f"  1x portfolio: {open_count_1x} open positions, cooldown={'YES' if cooldown_1x else 'NO'}")
    print(f"  20x portfolio: {open_count_20x} open positions, cooldown={'YES' if cooldown_20x else 'NO'}")

    # Fetch live prices
    prices = fetch_live_prices()
    if not prices:
        print("[DASHBOARD TRADER] Failed to fetch live prices from all APIs")
        log_entries.append({"time": now.isoformat(), "action": "price_fetch_failed"})
        save_log(log_entries)
        return

    print(f"  Fetched {len(prices)} live prices")

    # Process picks
    entries_1x = 0
    entries_20x = 0
    skipped = []

    for pick in picks:
        # Stop if we've entered enough this cycle
        if entries_1x >= MAX_NEW_ENTRIES_PER_CYCLE and entries_20x >= MAX_NEW_ENTRIES_PER_CYCLE:
            break

        symbol = pick.get("symbol", "")
        norm_sym = normalize_symbol(symbol)
        score = float(pick.get("score", 0) or 0)
        source = pick.get("source_system", "unknown")
        strategy = pick.get("strategy", "unknown")

        # Get live price
        live_price = prices.get(norm_sym, 0)
        if live_price <= 0:
            skipped.append({"symbol": symbol, "reason": "no live price available"})
            continue

        # --- Enter into 1x portfolio ---
        if (entries_1x < MAX_NEW_ENTRIES_PER_CYCLE
                and not cooldown_1x
                and open_count_1x + entries_1x < MAX_POSITIONS_1X
                and norm_sym not in held_1x):

            pos, skip_reason = enter_position(portfolio_1x, pick, live_price, leverage=1, size_pct=POSITION_SIZE_PCT_1X)
            if pos:
                pos_key = norm_sym
                portfolio_1x["positions"][pos_key] = pos
                portfolio_1x["stats"]["total_trades"] = portfolio_1x.get("stats", {}).get("total_trades", 0) + 1
                held_1x.add(norm_sym)
                entries_1x += 1
                print(f"  [1x ENTER] {norm_sym} LONG entry={live_price:.6f} score={score:.0f} source={source} strategy={strategy}")
                log_entries.append({
                    "time": now.isoformat(),
                    "action": "enter_1x",
                    "symbol": norm_sym,
                    "entry_price": live_price,
                    "score": score,
                    "source_system": source,
                    "strategy": strategy,
                    "position_size": pos["position_size"],
                })
            elif skip_reason:
                skipped.append({"symbol": symbol, "portfolio": "1x", "reason": skip_reason})

        # --- Enter into 20x portfolio ---
        if (entries_20x < MAX_NEW_ENTRIES_PER_CYCLE
                and not cooldown_20x
                and open_count_20x + entries_20x < MAX_POSITIONS_20X
                and norm_sym not in held_20x):

            pos, skip_reason = enter_position(portfolio_20x, pick, live_price, leverage=20, size_pct=POSITION_SIZE_PCT_20X)
            if pos:
                pos_key = norm_sym
                portfolio_20x["positions"][pos_key] = pos
                portfolio_20x["stats"]["total_trades"] = portfolio_20x.get("stats", {}).get("total_trades", 0) + 1
                held_20x.add(norm_sym)
                entries_20x += 1
                print(f"  [20x ENTER] {norm_sym} LONG entry={live_price:.6f} score={score:.0f} source={source} strategy={strategy}")
                log_entries.append({
                    "time": now.isoformat(),
                    "action": "enter_20x",
                    "symbol": norm_sym,
                    "entry_price": live_price,
                    "score": score,
                    "source_system": source,
                    "strategy": strategy,
                    "position_size": pos["position_size"],
                })
            elif skip_reason:
                skipped.append({"symbol": symbol, "portfolio": "20x", "reason": skip_reason})

    # Save portfolios
    if entries_1x > 0:
        save_json(PORTFOLIO_1X_FILE, portfolio_1x)
        print(f"\n  Saved 1x portfolio with {entries_1x} new entries")

    if entries_20x > 0:
        save_json(PORTFOLIO_20X_FILE, portfolio_20x)
        print(f"  Saved 20x portfolio with {entries_20x} new entries")

    # Log skipped picks (top 10)
    if skipped:
        print(f"\n  Skipped {len(skipped)} picks:")
        for s in skipped[:10]:
            print(f"    {s.get('symbol','?'):12s} ({s.get('portfolio','both'):3s}): {s.get('reason','')}")
        log_entries.append({
            "time": now.isoformat(),
            "action": "skipped_summary",
            "count": len(skipped),
            "samples": skipped[:10],
        })

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: {entries_1x} new 1x entries, {entries_20x} new 20x entries")
    print(f"{'='*60}")

    log_entries.append({
        "time": now.isoformat(),
        "action": "cycle_complete",
        "entries_1x": entries_1x,
        "entries_20x": entries_20x,
        "picks_evaluated": len(picks),
        "picks_skipped": len(skipped),
    })

    save_log(log_entries)


def save_log(new_entries):
    """Append log entries, keep last 500."""
    existing = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []

    existing.extend(new_entries)

    # Keep last 500 entries
    if len(existing) > 500:
        existing = existing[-500:]

    save_json(LOG_FILE, existing)


def main():
    """CLI entry point."""
    run_trader()


if __name__ == "__main__":
    main()
