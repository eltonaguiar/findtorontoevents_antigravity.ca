#!/usr/bin/env python3
"""
CLAUDE CODE — TP/SL Tracker
============================
Tracks active picks and checks Take-Profit / Stop-Loss levels
against real-time CoinGecko prices.

Usage:
    python tp_sl_tracker.py [--no-discord]
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
TRACKER_DIR = BASE_DIR / "tracker"
TRACKER_DIR.mkdir(parents=True, exist_ok=True)

LIVE_PICKS_FILE = TRACKER_DIR / "claude_live_picks.json"
PICK_HISTORY_FILE = TRACKER_DIR / "claude_pick_history.json"
PERFORMANCE_FILE = TRACKER_DIR / "claude_performance.json"

# ── CoinGecko ────────────────────────────────────────────────────────────
CG_SIMPLE_PRICE = "https://api.coingecko.com/api/v3/simple/price"
RATE_LIMIT_DELAY = 1.6

# ── Discord ──────────────────────────────────────────────────────────────
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")


def _fmt_price(val) -> str:
    """Format price without scientific notation."""
    if val is None or val == 0:
        return "$0"
    val = float(val)
    if val >= 1000:
        return f"${val:,.2f}"
    elif val >= 1:
        return f"${val:.4f}"
    elif val >= 0.001:
        return f"${val:.6f}"
    else:
        return f"${val:.10f}"


# ═══════════════════════════════════════════════════════════════════════════
#  PRICE FETCHING
# ═══════════════════════════════════════════════════════════════════════════

def fetch_current_prices(coin_ids):
    """Fetch current prices with CoinGecko → Binance → OKX failover.

    CoinGecko /simple/price supports batching up to ~50 IDs per request.
    Falls back to exchange APIs if CoinGecko fails or rate limits.
    """
    prices = {}
    batch_size = 50

    # Source 1: CoinGecko (primary — supports coin IDs natively)
    for i in range(0, len(coin_ids), batch_size):
        batch = coin_ids[i:i + batch_size]
        ids_str = ",".join(batch)

        try:
            r = requests.get(
                CG_SIMPLE_PRICE,
                params={"ids": ids_str, "vs_currencies": "usd"},
                timeout=30,
            )
            if r.status_code == 429:
                print("  [CG] Rate limited — trying fallback exchanges")
                break  # Fall through to exchange APIs
            r.raise_for_status()
            data = r.json()

            for coin_id, price_data in data.items():
                if "usd" in price_data:
                    prices[coin_id] = price_data["usd"]

            time.sleep(RATE_LIMIT_DELAY)
        except Exception as e:
            print(f"  [CG] Price fetch error: {e}")
            time.sleep(RATE_LIMIT_DELAY)

    # Source 2+3: Binance/OKX fallback for any missing coin IDs
    missing = [cid for cid in coin_ids if cid not in prices]
    if missing:
        print(f"  [Fallback] {len(missing)} coins missing from CoinGecko, trying exchanges...")
        for coin_id in missing:
            price = _fetch_exchange_price(coin_id)
            if price:
                prices[coin_id] = price

    return prices


# Mapping from CoinGecko coin IDs to exchange symbols
_CG_TO_EXCHANGE = {
    "bitcoin": "BTCUSDT", "ethereum": "ETHUSDT", "solana": "SOLUSDT",
    "binancecoin": "BNBUSDT", "ripple": "XRPUSDT", "dogecoin": "DOGEUSDT",
    "cardano": "ADAUSDT", "avalanche-2": "AVAXUSDT", "polkadot": "DOTUSDT",
    "chainlink": "LINKUSDT", "near": "NEARUSDT", "sui": "SUIUSDT",
    "aptos": "APTUSDT", "injective-protocol": "INJUSDT", "fetch-ai": "FETUSDT",
    "litecoin": "LTCUSDT", "uniswap": "UNIUSDT", "aave": "AAVEUSDT",
    "arbitrum": "ARBUSDT", "optimism": "OPUSDT", "celestia": "TIAUSDT",
    "sei-network": "SEIUSDT", "filecoin": "FILUSDT", "pepe": "PEPEUSDT",
    "tao": "TAOUSDT",
}


def _fetch_exchange_price(coin_id: str) -> float | None:
    """Fetch price from Binance → OKX for a single coin ID."""
    symbol = _CG_TO_EXCHANGE.get(coin_id)
    if not symbol:
        return None

    # Binance
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price",
                         params={"symbol": symbol}, timeout=5)
        if r.ok:
            return float(r.json()["price"])
    except Exception:
        pass

    # OKX
    try:
        okx_sym = symbol.replace("USDT", "-USDT")
        r = requests.get("https://www.okx.com/api/v5/market/ticker",
                         params={"instId": okx_sym}, timeout=5)
        if r.ok:
            data = r.json().get("data", [])
            if data:
                return float(data[0]["last"])
    except Exception:
        pass

    return None


# ═══════════════════════════════════════════════════════════════════════════
#  PICK EVALUATION
# ═══════════════════════════════════════════════════════════════════════════

def evaluate_picks(picks, current_prices):
    """Check each active pick against TP/SL levels."""
    now = datetime.now(timezone.utc)
    resolved = []
    still_active = []

    for pick in picks:
        if pick.get("status") != "ACTIVE":
            still_active.append(pick)  # Already resolved, keep as-is
            continue

        coin_id = pick.get("coin_id", "")
        symbol = pick.get("symbol", "")
        entry_price = pick.get("entry_price", 0)
        tp1_price = pick.get("tp1_price", 0)
        tp2_price = pick.get("tp2_price", 0)
        sl_price = pick.get("sl_price", 0)

        current_price = current_prices.get(coin_id)

        # Fallback: try Binance if CoinGecko failed
        if current_price is None:
            _pair = pick.get("pair", f"{symbol}USDT")
            try:
                import urllib.request as _ur
                for _base in ["https://api.binance.com", "https://api1.binance.com"]:
                    try:
                        _url = f"{_base}/api/v3/ticker/price?symbol={_pair}"
                        _req = _ur.Request(_url, headers={"User-Agent": "Mozilla/5.0"})
                        with _ur.urlopen(_req, timeout=5) as _resp:
                            _data = json.loads(_resp.read())
                            current_price = float(_data.get("price", 0))
                            if current_price > 0:
                                break
                    except Exception:
                        continue
            except Exception:
                pass

        # Force-close zombies: picks 7+ days past expiry with no price data
        if current_price is None:
            entry_time_str = pick.get("entry_time", "")
            try:
                _et = datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
                _age_days = (now - _et).total_seconds() / 86400
                if _age_days > 7:
                    pick["status"] = "RESOLVED"
                    pick["exit_reason"] = "ZOMBIE_FORCE_CLOSE"
                    pick["exit_time"] = now.isoformat()
                    pick["pnl_pct"] = 0.0
                    pick["exit_price"] = entry_price
                    resolved.append(pick)
                    print(f"  [{symbol}] ZOMBIE FORCE CLOSE — {_age_days:.0f} days old, no price data")
                    continue
            except Exception:
                pass
            print(f"  [{symbol}] No price data — keeping active")
            still_active.append(pick)
            continue

        pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0

        # Check expiry (time exit)
        entry_time = datetime.fromisoformat(pick.get("entry_time", now.isoformat()))
        expiry_time = datetime.fromisoformat(pick.get("expiry_time", (now + timedelta(days=8)).isoformat()))
        time_expired = now >= expiry_time

        exit_reason = None
        exit_price = None

        # Priority: SL > TP2 > TP1 > Time Exit
        if current_price <= sl_price:
            exit_reason = "STOP_LOSS"
            exit_price = sl_price
            pick["sl_hit"] = True
            print(f"  [{symbol}] SL HIT @ ${current_price:.6f} (entry ${entry_price:.6f}, PnL {pnl_pct:+.1f}%)")

        elif current_price >= tp2_price:
            exit_reason = "TAKE_PROFIT_2"
            exit_price = tp2_price
            pick["tp1_hit"] = True
            pick["tp2_hit"] = True
            print(f"  [{symbol}] TP2 HIT @ ${current_price:.6f} (entry ${entry_price:.6f}, PnL {pnl_pct:+.1f}%)")

        elif current_price >= tp1_price:
            pick["tp1_hit"] = True
            if time_expired:
                # TP1 hit but time expired — close at current price as a win
                exit_reason = "TAKE_PROFIT_1"
                exit_price = current_price
                print(f"  [{symbol}] TP1 HIT + TIME EXIT @ ${current_price:.6f} (entry ${entry_price:.6f}, PnL {pnl_pct:+.1f}%)")
            else:
                # TP1 hit — keep active for TP2 chance
                print(f"  [{symbol}] TP1 HIT @ ${current_price:.6f} — staying active for TP2")
                still_active.append(pick)
                continue

        elif time_expired:
            exit_reason = "TIME_EXIT"
            exit_price = current_price
            print(f"  [{symbol}] TIME EXIT @ ${current_price:.6f} (entry ${entry_price:.6f}, PnL {pnl_pct:+.1f}%)")

        if exit_reason:
            pick["status"] = "RESOLVED"
            pick["exit_price"] = exit_price
            pick["exit_time"] = now.isoformat()
            pick["exit_reason"] = exit_reason
            pick["pnl_pct"] = round(pnl_pct, 2)
            pick["final_price"] = current_price
            resolved.append(pick)
        else:
            # Still active — update current PnL
            pick["unrealized_pnl_pct"] = round(pnl_pct, 2)
            pick["last_checked"] = now.isoformat()
            pick["last_price"] = current_price
            still_active.append(pick)

    return still_active, resolved


# ═══════════════════════════════════════════════════════════════════════════
#  PERFORMANCE TRACKING
# ═══════════════════════════════════════════════════════════════════════════

def update_performance(resolved_picks, all_picks):
    """Calculate and save cumulative performance metrics."""
    # Load existing history
    history = []
    if PICK_HISTORY_FILE.exists():
        with open(PICK_HISTORY_FILE) as f:
            history = json.load(f)

    # Append newly resolved picks
    for pick in resolved_picks:
        # Persist ML features for training (fixes train/serve skew)
        # The 'features' dict from live_scanner.py contains the enriched
        # features computed at prediction time — preserve them with the outcome
        if "ml_features_at_entry" not in pick and pick.get("features"):
            pick["ml_features_at_entry"] = pick["features"]
        elif "ml_features_at_entry" not in pick:
            pick["ml_features_at_entry"] = {
                "pump_probability": pick.get("pump_probability"),
                "confidence": pick.get("confidence"),
                "rsi_at_entry": pick.get("rsi_at_entry"),
                "volume_ratio": pick.get("volume_ratio"),
                "atr_pct": pick.get("atr_pct"),
                "market_cap_rank": pick.get("market_cap_rank"),
                "signal_count": len(pick.get("signals", [])),
            }

        history.append({
            "pick_id": pick.get("pick_id"),
            "symbol": pick.get("symbol"),
            "coin_id": pick.get("coin_id"),
            "entry_price": pick.get("entry_price"),
            "exit_price": pick.get("exit_price"),
            "final_price": pick.get("final_price"),
            "entry_time": pick.get("entry_time"),
            "exit_time": pick.get("exit_time"),
            "exit_reason": pick.get("exit_reason"),
            "pnl_pct": pick.get("pnl_pct"),
            "pump_probability": pick.get("pump_probability"),
            "confidence": pick.get("confidence"),
            "tp1_hit": pick.get("tp1_hit"),
            "tp2_hit": pick.get("tp2_hit"),
            "sl_hit": pick.get("sl_hit"),
            "signals": pick.get("signals"),
            "ml_features_at_entry": pick.get("ml_features_at_entry"),
            "features": pick.get("features"),
        })

    with open(PICK_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

    # Calculate performance summary
    total_resolved = len(history)
    if total_resolved == 0:
        print("[PERF] No resolved picks yet — writing stub performance file")
        stub = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_picks": 0,
            "active_picks": sum(1 for p in all_picks if p.get("status") == "ACTIVE"),
            "win_rate": 0, "total_wins": 0, "total_losses": 0,
            "avg_pnl_pct": 0, "total_pnl_pct": 0,
            "avg_win_pct": 0, "avg_loss_pct": 0,
            "profit_factor": 0, "sharpe_ratio": 0, "max_drawdown_pct": 0,
            "tp1_hit_rate": 0, "tp2_hit_rate": 0, "sl_hit_rate": 0, "time_exit_rate": 0,
            "by_confidence": {}, "recent_10": [],
        }
        with open(PERFORMANCE_FILE, "w") as f:
            json.dump(stub, f, indent=2)
        return

    wins = [p for p in history if (p.get("pnl_pct") or 0) > 0]
    losses = [p for p in history if (p.get("pnl_pct") or 0) <= 0]
    tp1_hits = [p for p in history if p.get("tp1_hit")]
    tp2_hits = [p for p in history if p.get("tp2_hit")]
    sl_hits = [p for p in history if p.get("sl_hit")]
    time_exits = [p for p in history if p.get("exit_reason") == "TIME_EXIT"]

    pnls = [float(p.get("pnl_pct", 0) or 0) for p in history]
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0
    total_pnl = sum(pnls)
    win_rate = len(wins) / total_resolved * 100 if total_resolved > 0 else 0

    avg_win = sum(float(p.get("pnl_pct", 0) or 0) for p in wins) / len(wins) if wins else 0
    avg_loss = sum(float(p.get("pnl_pct", 0) or 0) for p in losses) / len(losses) if losses else 0
    profit_factor = abs(avg_win * len(wins)) / abs(avg_loss * len(losses)) if losses and avg_loss != 0 else float("inf")

    # Sharpe-like ratio (annualized, assuming daily picks)
    import numpy as np
    pnl_arr = np.array(pnls)
    if len(pnl_arr) > 1 and pnl_arr.std() > 0:
        sharpe = (pnl_arr.mean() / pnl_arr.std()) * (252 ** 0.5)
    else:
        sharpe = 0.0

    # Max drawdown
    cumulative = np.cumsum(pnl_arr)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = cumulative - running_max
    max_dd = float(drawdowns.min()) if len(drawdowns) > 0 else 0

    performance = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_picks": total_resolved,
        "active_picks": sum(1 for p in all_picks if p.get("status") == "ACTIVE"),
        "win_rate": round(win_rate, 2),
        "total_wins": len(wins),
        "total_losses": len(losses),
        "avg_pnl_pct": round(avg_pnl, 2),
        "total_pnl_pct": round(total_pnl, 2),
        "avg_win_pct": round(avg_win, 2),
        "avg_loss_pct": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else "inf",
        "sharpe_ratio": round(float(sharpe), 2),
        "max_drawdown_pct": round(max_dd, 2),
        "tp1_hit_rate": round(len(tp1_hits) / total_resolved * 100, 2) if total_resolved > 0 else 0,
        "tp2_hit_rate": round(len(tp2_hits) / total_resolved * 100, 2) if total_resolved > 0 else 0,
        "sl_hit_rate": round(len(sl_hits) / total_resolved * 100, 2) if total_resolved > 0 else 0,
        "time_exit_rate": round(len(time_exits) / total_resolved * 100, 2) if total_resolved > 0 else 0,
        "by_confidence": {},
        "recent_10": [],
    }

    # Breakdown by confidence level
    for conf_level in ["VERY HIGH", "HIGH", "MEDIUM", "LOW"]:
        conf_picks = [p for p in history if p.get("confidence") == conf_level]
        if conf_picks:
            conf_pnls = [float(p.get("pnl_pct", 0) or 0) for p in conf_picks]
            conf_wins = [p for p in conf_picks if (p.get("pnl_pct") or 0) > 0]
            performance["by_confidence"][conf_level] = {
                "count": len(conf_picks),
                "win_rate": round(len(conf_wins) / len(conf_picks) * 100, 2),
                "avg_pnl": round(sum(conf_pnls) / len(conf_pnls), 2),
            }

    # Recent 10 picks
    for p in history[-10:]:
        performance["recent_10"].append({
            "symbol": p.get("symbol"),
            "pnl_pct": p.get("pnl_pct"),
            "exit_reason": p.get("exit_reason"),
            "confidence": p.get("confidence"),
        })

    with open(PERFORMANCE_FILE, "w") as f:
        json.dump(performance, f, indent=2)

    # Print summary
    print("\n" + "=" * 50)
    print("  PERFORMANCE SUMMARY")
    print("=" * 50)
    print(f"  Total picks:     {total_resolved}")
    print(f"  Win rate:        {win_rate:.1f}%")
    print(f"  Avg PnL:         {avg_pnl:+.2f}%")
    print(f"  Total PnL:       {total_pnl:+.2f}%")
    print(f"  Profit factor:   {profit_factor:.2f}" if profit_factor != float("inf") else f"  Profit factor:   inf")
    print(f"  Sharpe (ann.):   {sharpe:.2f}")
    print(f"  Max drawdown:    {max_dd:.2f}%")
    print(f"  TP1 hit rate:    {performance['tp1_hit_rate']:.1f}%")
    print(f"  TP2 hit rate:    {performance['tp2_hit_rate']:.1f}%")
    print(f"  SL hit rate:     {performance['sl_hit_rate']:.1f}%")


# ═══════════════════════════════════════════════════════════════════════════
#  DISCORD EXIT NOTIFICATION
# ═══════════════════════════════════════════════════════════════════════════

def send_exit_alerts(resolved_picks):
    """Send Discord notifications for resolved picks."""
    if not DISCORD_WEBHOOK_URL or not resolved_picks:
        return

    fields = []
    for pick in resolved_picks[:10]:
        pnl = pick.get("pnl_pct", 0)
        emoji = "profit" if pnl > 0 else "loss"
        # Asset class detection
        sym = pick.get("symbol", "").upper().replace("-", "").replace("/", "")
        ac = pick.get("asset_class", "")
        if not ac:
            if any(sym.endswith(sfx) for sfx in ("USDT", "BTC", "ETH", "BUSD", "USDC")):
                ac = "CRYPTO"
            elif len(sym) == 6 and sym[:3] in ("EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD"):
                ac = "FOREX"
            else:
                ac = "EQUITY"
        ac_tag = {"CRYPTO": "\U0001fa99", "FOREX": "\U0001f4b1", "EQUITY": "\U0001f4c8", "MEMECOIN": "\U0001f436"}.get(ac.upper(), "\U0001f4ca")
        fields.append({
            "name": f"{ac_tag} {pick['symbol']} — {pick['exit_reason']} [{ac}]",
            "value": (
                f"Entry: {_fmt_price(pick.get('entry_price', 0))}\n"
                f"Exit: {_fmt_price(pick.get('exit_price', 0))}\n"
                f"PnL: {pnl:+.2f}% ({emoji})\n"
                f"Duration: {pick.get('entry_time', 'N/A')} -> {pick.get('exit_time', 'N/A')}"
            ),
            "inline": False,
        })

    payload = {
        "content": "**CLAUDE CODE — Pick Exits**",
        "embeds": [{
            "title": f"{len(resolved_picks)} Pick(s) Resolved",
            "color": 0xff4444 if any(float(p.get("pnl_pct", 0) or 0) < 0 for p in resolved_picks) else 0x44ff44,
            "fields": fields,
            "footer": {"text": "CLAUDE CODE TP/SL Tracker"},
        }],
    }

    import time as _dtime
    for _attempt in range(3):
        try:
            r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            if r.status_code in (200, 204):
                print(f"[DISCORD] Exit alert sent ({len(resolved_picks)} picks)")
                break
            if r.status_code == 429:
                _dtime.sleep(r.json().get("retry_after", 3))
                continue
            print(f"[DISCORD] Exit alert failed: {r.status_code}")
            if _attempt < 2:
                _dtime.sleep(2 * (_attempt + 1))
            break
        except Exception as e:
            if _attempt == 2:
                print(f"[DISCORD] Error after 3 attempts: {e}")
            else:
                _dtime.sleep(2 * (_attempt + 1))


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def run_tracker(send_alerts=True):
    """Execute one tracking cycle."""
    print("\n" + "=" * 70)
    print("  CLAUDE CODE — TP/SL Tracker")
    print(f"  Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)

    # Load active picks
    if not LIVE_PICKS_FILE.exists():
        print("[INFO] No picks file found — nothing to track")
        return

    with open(LIVE_PICKS_FILE) as f:
        picks_data = json.load(f)

    all_picks = picks_data.get("picks", [])
    active_picks = [p for p in all_picks if p.get("status") == "ACTIVE"]

    print(f"[TRACK] {len(active_picks)} active picks / {len(all_picks)} total")

    if not active_picks:
        print("[INFO] No active picks to track")
        return

    # Fetch current prices
    coin_ids = list(set(p.get("coin_id", "") for p in active_picks if p.get("coin_id")))
    print(f"[TRACK] Fetching prices for {len(coin_ids)} coins...")
    current_prices = fetch_current_prices(coin_ids)
    print(f"[TRACK] Got prices for {len(current_prices)} coins")

    # Evaluate picks
    print("\n[EVAL] Checking TP/SL levels...")
    still_active, resolved = evaluate_picks(all_picks, current_prices)

    # Update picks file
    updated_data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_active": sum(1 for p in still_active if p.get("status") == "ACTIVE"),
        "total_resolved": sum(1 for p in still_active if p.get("status") != "ACTIVE") + len(resolved),
        "picks": still_active + resolved,  # resolved at the end
    }
    # Actually, keep resolved picks in the list but merge properly
    merged = []
    resolved_ids = {p.get("pick_id") for p in resolved}
    for p in still_active:
        if p.get("pick_id") not in resolved_ids:
            merged.append(p)
    merged.extend(resolved)

    updated_data["picks"] = merged
    updated_data["total_active"] = sum(1 for p in merged if p.get("status") == "ACTIVE")
    updated_data["total_resolved"] = sum(1 for p in merged if p.get("status") != "ACTIVE")

    with open(LIVE_PICKS_FILE, "w") as f:
        json.dump(updated_data, f, indent=2)

    print(f"\n[TRACK] {len(resolved)} picks resolved, {updated_data['total_active']} still active")

    # Update performance
    if resolved:
        update_performance(resolved, merged)

    # Discord exit alerts
    if send_alerts and resolved:
        send_exit_alerts(resolved)

    # Print active picks status
    active_remaining = [p for p in merged if p.get("status") == "ACTIVE"]
    if active_remaining:
        print("\n  Active Picks Status:")
        print(f"  {'Symbol':<8} {'Entry':>10} {'Current':>10} {'PnL':>8} {'TP1':>5} {'Prob':>6}")
        print("  " + "-" * 50)
        for p in active_remaining:
            unrealized = p.get("unrealized_pnl_pct", 0)
            tp1 = "YES" if p.get("tp1_hit") else "no"
            print(f"  {p['symbol']:<8} ${p['entry_price']:>9.4f} ${p.get('last_price', 0):>9.4f} "
                  f"{unrealized:>+7.1f}% {tp1:>5} {p['pump_probability']:>5.0%}")


def main():
    parser = argparse.ArgumentParser(description="CLAUDE CODE — TP/SL Tracker")
    parser.add_argument("--no-discord", action="store_true", help="Disable Discord alerts")
    parser.add_argument("--loop", action="store_true", help="Run continuously (every 15 min)")
    args = parser.parse_args()

    if args.loop:
        print("[LOOP] Running tracker every 15 minutes...")
        while True:
            try:
                run_tracker(send_alerts=not args.no_discord)
            except Exception as e:
                print(f"[ERROR] Tracker failed: {e}")
            print("\n[LOOP] Sleeping 15 minutes...")
            time.sleep(900)
    else:
        run_tracker(send_alerts=not args.no_discord)


if __name__ == "__main__":
    main()
