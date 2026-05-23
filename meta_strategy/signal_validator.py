"""Validate open meta-strategy signals against live Binance prices.

Checks TP/SL hit, time expiry, and records outcomes.
Also generates NEW signals from winning combos based on current system picks.
"""
import json
import sys
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

from meta_strategy.db import get_db, log_signal, resolve_signal

# API failover: never rely on a single Binance endpoint
try:
    from alpha_engine import api_failover
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from alpha_engine import api_failover

MAX_HOLD_HOURS = 168  # 7 days
TP_PCT = 0.05         # 5% take profit
SL_PCT = 0.03         # 3% stop loss

# All system active picks paths (same as signal_recorder/system_scanner.py)
REPO_ROOT = Path(__file__).parent.parent
SYSTEM_PATHS = {
    "mercury2": REPO_ROOT / "mercury2/data/active_picks.json",
    "alpha_engine": REPO_ROOT / "alpha_engine/data/active_picks.json",
    "kimi_rotc": REPO_ROOT / "KIMI_RISEOFTHECLAW/data/active_picks.json",
    "crypto_ml_edge": REPO_ROOT / "crypto_ml_edge/data/active_picks.json",
    "signal_engine": REPO_ROOT / "crypto_signal_engine/data/active_picks.json",
    "regime_terminal": REPO_ROOT / "regime_terminal/data/active_signals.json",
    "ml_crypto_pred": REPO_ROOT / "ml_crypto_predictor/enhanced_models/live_picks/active_picks.json",
    "claws_of_doom": REPO_ROOT / "ml_battleground/system_f_clawsofdoom/data/active_picks.json",
    "ensemble": REPO_ROOT / "ml_battleground/ensemble_data/active_picks.json",
    "social_predict": REPO_ROOT / "predictions/data/active_predictions.json",
    "cross_agg": REPO_ROOT / "data/aggregated_picks.json",
}

# Symbol normalizer
SYMBOL_ALIASES = {
    "BTC-USD": "BTCUSDT", "BTCUSD": "BTCUSDT", "BTC": "BTCUSDT",
    "ETH-USD": "ETHUSDT", "ETHUSD": "ETHUSDT", "ETH": "ETHUSDT",
    "SOL-USD": "SOLUSDT", "SOLUSD": "SOLUSDT", "SOL": "SOLUSDT",
    "BNB-USD": "BNBUSDT", "BNBUSD": "BNBUSDT",
    "XRP-USD": "XRPUSDT", "XRPUSD": "XRPUSDT",
    "ADA-USD": "ADAUSDT", "ADAUSD": "ADAUSDT",
    "DOGE-USD": "DOGEUSDT", "DOGEUSD": "DOGEUSDT",
    "DOT-USD": "DOTUSDT", "DOTUSD": "DOTUSDT",
    "LINK-USD": "LINKUSDT", "LINKUSD": "LINKUSDT",
    "AVAX-USD": "AVAXUSDT", "AVAXUSD": "AVAXUSDT",
}


def normalize_symbol(sym: str) -> str:
    return SYMBOL_ALIASES.get(sym, sym.upper())


def normalize_direction(d: str) -> str:
    d = (d or "").upper()
    if d in ("BUY", "LONG", "1"):
        return "BUY"
    if d in ("SELL", "SHORT", "-1"):
        return "SELL"
    return ""


def fetch_binance_prices() -> dict:
    """Fetch all ticker prices with Binance mirror rotation + fallback."""
    for base in api_failover.BINANCE_SPOT_BASES:
        try:
            resp = requests.get(f"{base}/api/v3/ticker/price", timeout=10)
            if resp.status_code == 451:
                continue  # geo-blocked, try next mirror
            resp.raise_for_status()
            return {t["symbol"]: float(t["price"]) for t in resp.json()}
        except Exception:
            continue
    print("  WARNING: All Binance mirrors failed for bulk price fetch")
    return {}


def load_current_system_signals() -> dict:
    """Load current signals from all systems, grouped by symbol."""
    by_symbol = {}

    for sys_id, path in SYSTEM_PATHS.items():
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                picks = data.get("consensus_picks", data.get("picks", data.get("predictions", data.get("signals", []))))
                if not isinstance(picks, list):
                    picks = []
            elif isinstance(data, list):
                picks = data
            else:
                continue

            for pick in picks:
                sym = normalize_symbol(
                    pick.get("symbol", pick.get("pair", pick.get("ticker", "")))
                )
                direction = normalize_direction(
                    pick.get("direction", pick.get("signal", pick.get("signal_type", "")))
                )
                if not sym or not direction:
                    continue

                if sym not in by_symbol:
                    by_symbol[sym] = {}
                by_symbol[sym][sys_id] = {
                    "direction": direction,
                    "confidence": pick.get("confidence", pick.get("strength", 0.5)),
                    "entry_price": pick.get("entry_price", pick.get("entryPrice")),
                }
        except Exception:
            continue

    return by_symbol


def generate_combo_signals() -> dict:
    """Generate signals from winning combos based on current system picks."""
    conn = get_db()
    prices = fetch_binance_prices()
    system_signals = load_current_system_signals()

    # Get winning combos
    winners = conn.execute("""
        SELECT p.combo_id, p.systems, p.logic_type, p.min_agreement,
               pr.win_rate, pr.sharpe
        FROM permutations p
        JOIN permutation_results pr ON pr.combo_id = p.combo_id
        WHERE p.status IN ('ACTIVE', 'RESURRECTED', 'PROBATION')
          AND pr.is_winner = 1
        ORDER BY pr.sharpe DESC
    """).fetchall()

    new_signals = 0
    for winner in winners:
        systems = json.loads(winner["systems"])
        logic = winner["logic_type"]
        min_agree = winner["min_agreement"]
        combo_id = winner["combo_id"]

        for symbol, sys_picks in system_signals.items():
            if symbol not in prices:
                continue

            # Count votes
            buy_votes = 0
            sell_votes = 0
            total_confidence = 0
            contributing = {}

            for sys_id in systems:
                actual_id = sys_id.replace("INV_", "")
                if actual_id not in sys_picks:
                    continue

                pick = sys_picks[actual_id]
                direction = pick["direction"]
                is_inverse = "INV_" in sys_id or logic == "inverse"

                if is_inverse:
                    direction = "SELL" if direction == "BUY" else "BUY"

                if direction == "BUY":
                    buy_votes += 1
                elif direction == "SELL":
                    sell_votes += 1

                total_confidence += pick.get("confidence", 0.5)
                contributing[sys_id] = direction

            # Check consensus
            direction = None
            if logic == "unanimous":
                if buy_votes == len(systems):
                    direction = "BUY"
                elif sell_votes == len(systems):
                    direction = "SELL"
            elif logic == "majority":
                if buy_votes >= min_agree:
                    direction = "BUY"
                elif sell_votes >= min_agree:
                    direction = "SELL"
            elif logic in ("weighted", "inverse", "consensus_plus_inverse"):
                if buy_votes > sell_votes and buy_votes >= min_agree:
                    direction = "BUY"
                elif sell_votes > buy_votes and sell_votes >= min_agree:
                    direction = "SELL"

            if not direction:
                continue

            # Check if we already have an open signal for this combo+symbol
            existing = conn.execute("""
                SELECT id FROM permutation_signals
                WHERE combo_id = ? AND symbol = ? AND status = 'OPEN'
            """, (combo_id, symbol)).fetchone()
            if existing:
                continue

            # Create signal
            current_price = prices[symbol]
            if direction == "BUY":
                tp = round(current_price * (1 + TP_PCT), 8)
                sl = round(current_price * (1 - SL_PCT), 8)
            else:
                tp = round(current_price * (1 - TP_PCT), 8)
                sl = round(current_price * (1 + SL_PCT), 8)

            avg_conf = total_confidence / max(len(contributing), 1)
            log_signal(conn, combo_id, symbol, direction, avg_conf,
                       current_price, tp, sl, contributing)
            new_signals += 1

    conn.close()
    return {"new_signals": new_signals, "combos_checked": len(winners)}


def validate_open_signals() -> dict:
    """Check open signals against live prices for TP/SL/expiry."""
    conn = get_db()
    prices = fetch_binance_prices()
    now = datetime.now(timezone.utc)

    open_signals = conn.execute("""
        SELECT * FROM permutation_signals WHERE status = 'OPEN'
    """).fetchall()

    stats = {"checked": 0, "tp_hit": 0, "sl_hit": 0, "expired": 0, "still_open": 0}

    for sig in open_signals:
        sig = dict(sig)
        sym = sig["symbol"]
        stats["checked"] += 1

        if sym not in prices:
            stats["still_open"] += 1
            continue

        current = prices[sym]
        entry = sig.get("entry_price")
        tp = sig.get("take_profit")
        sl = sig.get("stop_loss")
        direction = sig["direction"]

        if not entry:
            stats["still_open"] += 1
            continue

        # Time expiry
        try:
            sig_time = datetime.fromisoformat(sig["timestamp"])
            if (now - sig_time) > timedelta(hours=MAX_HOLD_HOURS):
                pnl = _calc_pnl(direction, entry, current)
                status = "EXPIRED_WIN" if pnl > 0 else "EXPIRED_LOSS"
                resolve_signal(conn, sig["id"], status, current, pnl)
                stats["expired"] += 1
                _update_combo_failures(conn, sig["combo_id"], pnl > 0)
                continue
        except Exception:
            pass

        # TP check
        if tp:
            hit = (current >= tp) if direction == "BUY" else (current <= tp)
            if hit:
                pnl = _calc_pnl(direction, entry, tp)
                resolve_signal(conn, sig["id"], "TP_HIT", tp, pnl)
                stats["tp_hit"] += 1
                _update_combo_failures(conn, sig["combo_id"], True)
                continue

        # SL check
        if sl:
            hit = (current <= sl) if direction == "BUY" else (current >= sl)
            if hit:
                pnl = _calc_pnl(direction, entry, sl)
                resolve_signal(conn, sig["id"], "SL_HIT", sl, pnl)
                stats["sl_hit"] += 1
                _update_combo_failures(conn, sig["combo_id"], False)
                continue

        stats["still_open"] += 1

    conn.close()
    return stats


def _calc_pnl(direction: str, entry: float, exit_price: float) -> float:
    if not entry or entry == 0:
        return 0.0
    if direction == "BUY":
        return round((exit_price - entry) / entry * 100, 4)
    return round((entry - exit_price) / entry * 100, 4)


def _update_combo_failures(conn, combo_id: str, won: bool):
    """Update consecutive failure counter for elimination tracking."""
    if won:
        conn.execute("""
            UPDATE permutations SET consecutive_failures = 0
            WHERE combo_id = ?
        """, (combo_id,))
    else:
        conn.execute("""
            UPDATE permutations SET consecutive_failures = consecutive_failures + 1
            WHERE combo_id = ?
        """, (combo_id,))
    conn.commit()


def main():
    print("Meta-Strategy Signal Validator")
    print("=" * 40)

    # Validate existing open signals
    val_stats = validate_open_signals()
    print(f"Validated: {val_stats['checked']} signals")
    print(f"  TP hit: {val_stats['tp_hit']}")
    print(f"  SL hit: {val_stats['sl_hit']}")
    print(f"  Expired: {val_stats['expired']}")
    print(f"  Still open: {val_stats['still_open']}")

    # Generate new signals from winning combos
    gen_stats = generate_combo_signals()
    print(f"\nNew signals generated: {gen_stats['new_signals']}")
    print(f"Winning combos checked: {gen_stats['combos_checked']}")


if __name__ == "__main__":
    main()
