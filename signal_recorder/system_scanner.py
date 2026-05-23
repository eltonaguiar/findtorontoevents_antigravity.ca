"""Read all trading system outputs and log signals."""
import json
import pathlib
import requests
from datetime import datetime, timezone

import sys

# API failover: never rely on a single Binance endpoint
try:
    from alpha_engine import api_failover
except ImportError:
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
    from alpha_engine import api_failover

from signal_recorder.db import get_db, log_signal

ROOT = pathlib.Path(__file__).parent.parent

SYSTEMS = {
    "mercury2":         "mercury2/data/active_picks.json",
    "alpha_engine":     "alpha_engine/data/active_picks.json",
    "kimi_rotc":        "KIMI_RISEOFTHECLAW/data/active_picks.json",
    "crypto_ml_edge":   "crypto_ml_edge/data/active_picks.json",
    "claude_gainer":    "claude_gainer_ml/tracker/claude_live_picks.json",
    "ml_bg_a":          "ml_battleground/system_a_filter/data/active_picks.json",
    "ml_bg_b":          "ml_battleground/system_b_regime/data/active_picks.json",
    "ml_bg_c":          "ml_battleground/system_c_deeplearn/data/active_picks.json",
    "ml_bg_d":          "ml_battleground/system_d_carry/data/active_picks.json",
    "ml_bg_e":          "ml_battleground/system_e_momentum/data/active_picks.json",
    "claws_of_doom":    "ml_battleground/system_f_clawsofdoom/data/active_picks.json",
    "signal_engine":    "crypto_signal_engine/data/active_picks.json",
    "breakout_a":       "breakout_arena/approach_a_sr_breakout/data/active_picks.json",
    "breakout_b":       "breakout_arena/approach_b_ml_breakout/data/active_picks.json",
    "breakout_c":       "breakout_arena/approach_c_spike_reverse/data/active_picks.json",
    "ensemble":         "ml_battleground/ensemble_data/active_picks.json",
    "regime_terminal":  "regime_terminal/data/active_signals.json",
    "kimi_feb17":       "KIMI_FEB172026/data/latest_signals.json",
    "ml_crypto_pred":   "ml_crypto_predictor/enhanced_models/live_picks/active_picks.json",
    "fc_crypto_pro":    "data/fc_crypto_pro_picks.json",
    "crypto_gainer":    "crypto_gainer_ml/tracker/live_picks.json",
    "incubator_fwd":    "incubator/backtest_results/forward_signals.json",
    "quantum_fusion":   "quantum_fusion_report.json",
    "social_predict":   "predictions/data/active_predictions.json",
    "goldmine":         "data/goldmine/unified_picks.json",
    "stocks_comp":      "STOCKS/competition/forward_picks.json",
    "cross_agg":        "data/aggregated_picks.json",
}

SYMBOL_ALIASES = {
    "BTC-USD": "BTCUSDT", "BTCUSD": "BTCUSDT", "BTC": "BTCUSDT",
    "ETH-USD": "ETHUSDT", "ETHUSD": "ETHUSDT", "ETH": "ETHUSDT",
    "SOL-USD": "SOLUSDT", "SOLUSD": "SOLUSDT", "SOL": "SOLUSDT",
    "DOGE-USD": "DOGEUSDT", "DOGEUSD": "DOGEUSDT", "DOGE": "DOGEUSDT",
    "XRP-USD": "XRPUSDT", "XRPUSD": "XRPUSDT", "XRP": "XRPUSDT",
    "ADA-USD": "ADAUSDT", "ADAUSD": "ADAUSDT", "ADA": "ADAUSDT",
    "LINK-USD": "LINKUSDT", "LINKUSD": "LINKUSDT", "LINK": "LINKUSDT",
    "DOT-USD": "DOTUSDT", "DOTUSD": "DOTUSDT", "DOT": "DOTUSDT",
    "BNB-USD": "BNBUSDT", "BNBUSD": "BNBUSDT", "BNB": "BNBUSDT",
    "AVAX-USD": "AVAXUSDT", "AVAXUSD": "AVAXUSDT", "AVAX": "AVAXUSDT",
}

DIRECTION_MAP = {
    "BUY": "BUY", "LONG": "BUY", "BULLISH": "BUY",
    "SELL": "SELL", "SHORT": "SELL", "BEARISH": "SELL",
    "STRONG_BUY": "BUY", "STRONG_SELL": "SELL",
    "NEUTRAL": "NEUTRAL",
}


def normalize_symbol(sym):
    s = sym.upper().strip()
    return SYMBOL_ALIASES.get(s, s)


def normalize_direction(d):
    return DIRECTION_MAP.get(d.upper().strip(), d.upper().strip())


def fetch_binance_prices():
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


def _extract_picks_from_json(data, system_id):
    picks = []
    if isinstance(data, list):
        raw_picks = data
    elif isinstance(data, dict):
        for key in ("active_picks", "picks", "active_predictions", "signals",
                     "active_calls", "active_signals", "forward_signals",
                     "consensus_picks", "data"):
            if key in data and isinstance(data[key], list):
                raw_picks = data[key]
                break
        else:
            raw_picks = []
    else:
        return []

    for p in raw_picks:
        if not isinstance(p, dict):
            continue
        symbol = p.get("symbol") or p.get("pair") or p.get("ticker") or ""
        if not symbol:
            continue
        symbol = normalize_symbol(symbol)

        direction = (p.get("direction") or p.get("signal") or
                     p.get("side") or p.get("action") or "")
        if not direction:
            continue
        direction = normalize_direction(direction)

        strength = (p.get("confidence") or p.get("strength") or
                    p.get("score") or p.get("consensus_score") or 0.5)
        if isinstance(strength, str):
            try:
                strength = float(strength)
            except ValueError:
                strength = 0.5

        entry = p.get("entry_price") or p.get("entry") or p.get("entryPrice")
        tp = p.get("take_profit") or p.get("tp") or p.get("targetPrice") or p.get("target")
        sl = p.get("stop_loss") or p.get("sl") or p.get("stopPrice") or p.get("stop")

        strategy = (p.get("strategy") or p.get("strategy_name") or
                    p.get("source") or p.get("predictor_id") or "")

        picks.append({
            "symbol": symbol,
            "direction": direction,
            "strength": float(strength) if strength else 0.5,
            "entry_price": float(entry) if entry else None,
            "take_profit": float(tp) if tp else None,
            "stop_loss": float(sl) if sl else None,
            "extra": {"strategy": strategy, "system": system_id},
        })

    return picks


def scan_all_systems(batch_id=None):
    if not batch_id:
        batch_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    prices = fetch_binance_prices()
    conn = get_db()
    stats = {"systems_read": 0, "signals_logged": 0, "errors": []}

    for system_id, rel_path in SYSTEMS.items():
        path = ROOT / rel_path
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
            picks = _extract_picks_from_json(data, system_id)
            for pick in picks:
                sym = pick["symbol"]
                price = prices.get(sym, None)
                log_signal(
                    conn, system_id=system_id, symbol=sym,
                    signal=pick["direction"], strength=pick["strength"],
                    price_at_signal=price,
                    entry_price=pick.get("entry_price"),
                    take_profit=pick.get("take_profit"),
                    stop_loss=pick.get("stop_loss"),
                    extra=pick.get("extra"),
                    batch_id=batch_id,
                )
                stats["signals_logged"] += 1
            stats["systems_read"] += 1
        except Exception as e:
            stats["errors"].append(f"{system_id}: {e}")

    conn.close()
    return stats


if __name__ == "__main__":
    stats = scan_all_systems()
    print(f"Systems read: {stats['systems_read']}")
    print(f"Signals logged: {stats['signals_logged']}")
    if stats["errors"]:
        print(f"Errors: {len(stats['errors'])}")
        for err in stats["errors"][:5]:
            print(f"  {err}")
