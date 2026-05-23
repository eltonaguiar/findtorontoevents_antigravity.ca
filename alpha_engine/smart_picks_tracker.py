#!/usr/bin/env python3
"""
Smart Picks Tracker — monitors each batch of recommended picks
and records their actual performance over time.

Each batch is versioned: "SP-v001 (Mar 22, 2:30 AM EST)"
Every 20 minutes, checks live prices against the batch and records PnL.
After a batch is 24h old, it's "resolved" and final performance computed.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

_DIR = Path(__file__).resolve().parent
_DATA = _DIR / "data"
_SMART_PICKS = _DATA / "smart_picks.json"
_HISTORY = _DATA / "smart_picks_history.json"
_MAX_BATCHES = 50
_RESOLVE_HOURS = 24

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("sp_tracker")

# -- Binance 3+ mirror failover (per API failover rule) + CoinGecko/KuCoin/CryptoCompare
SPOT_URLS = [
    "https://api.binance.com", "https://api1.binance.com",
    "https://api2.binance.com", "https://api3.binance.com",
    "https://data-api.binance.vision", "https://api.binance.us",
]
_HDR = {"User-Agent": "SmartPicksTracker/1.0"}


def _http_json(url: str, timeout: int = 8):
    try:
        req = urllib.request.Request(url, headers=_HDR)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def fetch_live_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch prices with full failover: Binance mirrors -> CoinGecko -> KuCoin -> CryptoCompare."""
    prices: dict[str, float] = {}

    # Binance mirrors
    for base in SPOT_URLS:
        data = _http_json(f"{base}/api/v3/ticker/price")
        if isinstance(data, list):
            lut = {d["symbol"]: float(d["price"]) for d in data}
            for s in symbols:
                if s in lut:
                    prices[s] = lut[s]
            break

    missing = [s for s in symbols if s not in prices]

    # CoinGecko fallback
    for sym in list(missing):
        bc = sym.replace("USDT", "").replace("USD", "").lower()
        cg = _http_json(f"https://api.coingecko.com/api/v3/simple/price?ids={bc}&vs_currencies=usd")
        if isinstance(cg, dict) and bc in cg and cg[bc].get("usd"):
            prices[sym] = cg[bc]["usd"]
            missing.remove(sym)

    # KuCoin fallback
    for sym in list(missing):
        pair = sym.replace("USDT", "-USDT")
        kc = _http_json(f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={pair}")
        if isinstance(kc, dict) and kc.get("data", {}).get("price"):
            prices[sym] = float(kc["data"]["price"])
            missing.remove(sym)

    # CryptoCompare fallback
    for sym in list(missing):
        bc = sym.replace("USDT", "").replace("USD", "")
        cc = _http_json(f"https://min-api.cryptocompare.com/data/price?fsym={bc}&tsyms=USD")
        if isinstance(cc, dict) and "USD" in cc:
            prices[sym] = cc["USD"]
            missing.remove(sym)

    return prices


def _batch_fingerprint(picks: list[dict]) -> str:
    """Create a deterministic fingerprint from the pick symbols + entries."""
    parts = sorted(f"{p.get('symbol', '')}:{p.get('entry', 0)}" for p in picks)
    return hashlib.md5("|".join(parts).encode()).hexdigest()[:12]


def _compute_pnl(pick: dict, live_price: float) -> float:
    """Compute PnL % for a single pick given its live price."""
    entry = pick.get("entry", 0) or pick.get("entry_price", 0)
    direction = pick.get("direction", "LONG").upper()
    if not entry or not live_price:
        return 0.0
    if direction == "LONG":
        return round((live_price - entry) / entry * 100, 3)
    else:
        return round((entry - live_price) / entry * 100, 3)


def _pick_status(pick: dict, live_price: float) -> str:
    """Determine if pick hit TP, SL, or is still open."""
    direction = pick.get("direction", "LONG").upper()
    tp = pick.get("tp", 0) or pick.get("take_profit", 0)
    sl = pick.get("sl", 0) or pick.get("stop_loss", 0)
    if not live_price:
        return "no_price"
    if tp:
        if (direction == "LONG" and live_price >= tp) or (direction == "SHORT" and live_price <= tp):
            return "tp_hit"
    if sl:
        if (direction == "LONG" and live_price <= sl) or (direction == "SHORT" and live_price >= sl):
            return "sl_hit"
    return "open"


def _resolve_batch(batch: dict) -> None:
    """Compute final stats for a resolved batch using its last snapshot."""
    snapshots = batch.get("snapshots", [])
    if not snapshots:
        batch["resolved"] = True
        batch["final_wr"] = 0.0
        batch["final_avg_pnl"] = 0.0
        batch["final_pf"] = 0.0
        return

    last = snapshots[-1]
    pnls = last.get("picks_pnl", [])
    statuses = last.get("picks_status", [])
    if not pnls:
        batch["resolved"] = True
        batch["final_wr"] = 0.0
        batch["final_avg_pnl"] = 0.0
        batch["final_pf"] = 0.0
        return

    winners = sum(1 for p in pnls if p > 0)
    total = len(pnls)
    wr = round(winners / total * 100, 1) if total else 0.0
    avg_pnl = round(sum(pnls) / total, 2) if total else 0.0

    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    pf = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

    batch["resolved"] = True
    batch["final_wr"] = wr
    batch["final_avg_pnl"] = avg_pnl
    batch["final_pf"] = pf
    batch["resolved_at"] = datetime.now(timezone.utc).isoformat()

    tp_hits = statuses.count("tp_hit") if statuses else 0
    sl_hits = statuses.count("sl_hit") if statuses else 0
    batch["final_tp_hits"] = tp_hits
    batch["final_sl_hits"] = sl_hits


def load_history() -> dict:
    """Load smart_picks_history.json or create empty structure."""
    if _HISTORY.exists():
        try:
            return json.loads(_HISTORY.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, Exception) as e:
            log.warning("Corrupt history file, starting fresh: %s", e)
    return {"batches": []}


def save_history(history: dict) -> None:
    """Save history, keeping only the last N batches."""
    history["batches"] = history["batches"][-_MAX_BATCHES:]
    history["last_updated"] = datetime.now(timezone.utc).isoformat()
    _HISTORY.write_text(json.dumps(history, indent=2), encoding="utf-8")
    log.info("Saved history with %d batches", len(history["batches"]))


def run():
    now = datetime.now(timezone.utc)

    # Load current smart picks
    if not _SMART_PICKS.exists():
        log.error("smart_picks.json not found — run smart_picks_engine.py first")
        return

    current = json.loads(_SMART_PICKS.read_text(encoding="utf-8"))
    current_picks = current.get("picks", [])
    if not current_picks:
        log.warning("No picks in smart_picks.json, nothing to track")
        return

    history = load_history()
    batches = history["batches"]

    # Determine next version number
    existing_versions = [b.get("version", "") for b in batches]
    max_v = 0
    for v in existing_versions:
        try:
            num = int(v.split("-v")[1].split(" ")[0])
            if num > max_v:
                max_v = num
        except (IndexError, ValueError):
            pass

    # Check if we need a new batch (different picks from latest unresolved)
    current_fp = _batch_fingerprint(current_picks)
    latest_unresolved = None
    for b in reversed(batches):
        if not b.get("resolved", False):
            latest_unresolved = b
            break

    need_new_batch = True
    if latest_unresolved:
        if latest_unresolved.get("fingerprint") == current_fp:
            need_new_batch = False
        else:
            log.info("Smart picks changed — new batch needed")

    if need_new_batch:
        max_v += 1
        version = f"SP-v{max_v:03d}"
        est_offset = timedelta(hours=-5)
        est_now = now + est_offset
        version_label = f"{version} ({est_now.strftime('%b %d, %-I:%M %p')} EST)"
        new_batch = {
            "version": version,
            "version_label": version_label,
            "generated_at": current.get("generated_at", now.isoformat()),
            "regime": current.get("regime", "UNKNOWN"),
            "fear_greed": current.get("fear_greed", 0),
            "btc_price_at_open": current.get("btc_price", 0),
            "fingerprint": current_fp,
            "picks": [
                {
                    "symbol": p.get("symbol", ""),
                    "direction": p.get("direction", "LONG"),
                    "entry": p.get("entry", 0) or p.get("live", 0),
                    "tp": p.get("tp", 0),
                    "sl": p.get("sl", 0),
                    "smart_score": p.get("smart_score", 0),
                    "strategy": p.get("strategy", ""),
                }
                for p in current_picks
            ],
            "snapshots": [],
            "resolved": False,
        }
        batches.append(new_batch)
        log.info("Created new batch: %s with %d picks", version_label, len(current_picks))

    # Collect all symbols from active batches
    active_batches = [b for b in batches if not b.get("resolved", False)]
    all_symbols = set()
    for b in active_batches:
        for p in b.get("picks", []):
            sym = p.get("symbol", "")
            if sym:
                all_symbols.add(sym)

    if not all_symbols:
        log.info("No active batches to track")
        save_history(history)
        return

    # Fetch live prices
    log.info("Fetching prices for %d symbols across %d active batches...",
             len(all_symbols), len(active_batches))
    prices = fetch_live_prices(list(all_symbols))
    btc_price = prices.get("BTCUSDT", prices.get("BTCUSD", 0))
    log.info("Got prices for %d/%d symbols", len(prices), len(all_symbols))

    # Process each active batch
    for batch in active_batches:
        gen_at = batch.get("generated_at", "")
        try:
            batch_time = datetime.fromisoformat(gen_at)
            if batch_time.tzinfo is None:
                batch_time = batch_time.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            batch_time = now

        age_hours = (now - batch_time).total_seconds() / 3600

        # Compute PnL for each pick
        picks_pnl = []
        picks_status = []
        for p in batch.get("picks", []):
            sym = p.get("symbol", "")
            lp = prices.get(sym, 0)
            pnl = _compute_pnl(p, lp)
            status = _pick_status(p, lp)
            picks_pnl.append(pnl)
            picks_status.append(status)

        snapshot = {
            "timestamp": now.isoformat(),
            "age_hours": round(age_hours, 1),
            "btc": btc_price,
            "picks_pnl": picks_pnl,
            "picks_status": picks_status,
        }
        batch.setdefault("snapshots", []).append(snapshot)

        # Resolve if older than 24h
        if age_hours >= _RESOLVE_HOURS:
            log.info("Resolving %s (%.1fh old)", batch.get("version", "?"), age_hours)
            _resolve_batch(batch)

    # Print summary
    print(f"\n{'='*60}")
    print(f"SMART PICKS TRACKER | {now.strftime('%Y-%m-%d %H:%M')} UTC | BTC ${btc_price:,.0f}")
    print(f"{'='*60}")

    for batch in batches[-10:]:
        version = batch.get("version", "?")
        resolved = batch.get("resolved", False)
        picks_list = batch.get("picks", [])
        total = len(picks_list)

        if resolved:
            wr = batch.get("final_wr", 0)
            avg = batch.get("final_avg_pnl", 0)
            pf = batch.get("final_pf", 0)
            print(f"  {version}: RESOLVED | WR {wr:.0f}% | Avg {avg:+.2f}% | PF {pf:.1f}")
        else:
            snaps = batch.get("snapshots", [])
            if snaps:
                last_pnl = snaps[-1].get("picks_pnl", [])
                winners = sum(1 for p in last_pnl if p > 0)
                avg = sum(last_pnl) / len(last_pnl) if last_pnl else 0
                gross_p = sum(p for p in last_pnl if p > 0)
                gross_l = abs(sum(p for p in last_pnl if p < 0))
                pf = round(gross_p / gross_l, 1) if gross_l > 0 else 99.0
                # 2026-03-23: Label as "snapshot" not "WR" — only SP-v001 resolved shows true WR.
                # Snapshot WR counts picks with unrealized PnL > 0; picks can reverse to SL hits later.
                snap_wr_pct = round(winners / len(last_pnl) * 100) if last_pnl else 0
                batch["snapshot_wr"] = snap_wr_pct
                batch["is_resolved"] = False
                print(f"  {version}: {winners}/{total} snapshot winning ({snap_wr_pct}% snapshot WR, NOT final), avg {avg:+.1f}%, PF {pf}")
            else:
                batch.setdefault("is_resolved", False)
                print(f"  {version}: {total} picks — awaiting first snapshot")

    save_history(history)
    print(f"\nTotal batches tracked: {len(batches)} (max {_MAX_BATCHES})")


if __name__ == "__main__":
    run()
