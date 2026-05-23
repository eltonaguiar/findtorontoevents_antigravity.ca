#!/usr/bin/env python3
"""
Variation Forward Tester
=========================
Lightweight forward-test tracker that manages ALL strategy variations
simultaneously. Each variation tracks its own capital, positions, and
performance independently.

Position sizing: $50 per trade (small since we're testing many variations).
Max 1 position per variation at a time.
Entry: only when a matching pick appears AND current hour matches entry hours.

Kill/Promote thresholds (after 10 trades):
  KILL:      WR < 40% OR total PnL < -5%
  PROBATION: WR 40-50% (give 10 more trades)
  PROMOTE:   WR > 55% and PnL > 0 -> size 1.5x
  STAR:      WR > 65% after 20 trades -> graduate to main portfolio

State: copy_trader_intel/data/variation_forward_test.json
"""

import sys
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

VARIATIONS_FILE = DATA_DIR / "strategy_variations.json"
STATE_FILE = DATA_DIR / "variation_forward_test.json"

# Position sizing
BASE_TRADE_SIZE = 50.0       # $50 per trade (small for testing)
PROMOTED_MULTIPLIER = 1.5    # 1.5x size for promoted variations
STAR_MULTIPLIER = 2.0        # 2x size for star variations

# Kill/Promote thresholds
MIN_TRADES_FOR_EVAL = 10
KILL_WR_THRESHOLD = 0.40
KILL_PNL_THRESHOLD = -5.0    # -5% total PnL
PROBATION_WR_LOW = 0.40
PROBATION_WR_HIGH = 0.50
PROMOTE_WR_THRESHOLD = 0.55
STAR_WR_THRESHOLD = 0.65
STAR_MIN_TRADES = 20
PROBATION_EXTRA_TRADES = 10  # Give probation variations 10 more trades

# Entry matching
ENTRY_PRICE_TOLERANCE = 0.05  # 5% max gap between pick price and current price


def fetch_prices() -> dict:
    """Fetch live prices with 3-API fallback chain."""
    apis = [
        ("https://api.binance.com/api/v3/ticker/price", "binance"),
        ("https://api1.binance.com/api/v3/ticker/price", "binance_mirror"),
        ("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,dogecoin,ripple,cardano,avalanche-2,chainlink,polkadot,near,shiba-inu,filecoin,bnb,fetch-ai,render-token&vs_currencies=usd", "coingecko"),
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
        except Exception:
            continue
    return {}


def normalize_symbol(sym: str) -> str:
    """Normalize symbol to Binance format (BTCUSDT)."""
    sym = sym.upper().replace("-USD", "USDT").replace("/", "").replace("-PERP", "")
    if not sym.endswith("USDT") and "USD" in sym and "=" not in sym:
        sym += "T"
    return sym


class VariationTracker:
    """Tracks one strategy variation's forward-test performance."""

    def __init__(self, variation: dict, state: dict = None):
        self.id = variation["variation_id"]
        self.params = variation
        self.coin = normalize_symbol(variation.get("coin", ""))
        self.direction = variation.get("direction", "LONG")
        self.tp_pct = variation.get("tp_pct", 3.0)
        self.sl_pct = variation.get("sl_pct", 1.5)
        self.max_hold_hours = variation.get("max_hold_hours", 6.0)
        self.entry_hours = variation.get("entry_hours_utc", [])
        self.session = variation.get("session", "US_SESSION")

        # Restore state if provided
        if state:
            self.capital = state.get("capital", variation.get("starting_capital", 1000.0))
            self.position = state.get("position", None)
            self.closed_trades = state.get("closed_trades", [])
            self.status = state.get("status", "ACTIVE")
        else:
            self.capital = variation.get("starting_capital", 1000.0)
            self.position = None
            self.closed_trades = []
            self.status = "ACTIVE"

    def should_enter(self, pick: dict, current_hour_utc: int) -> bool:
        """Check if this pick matches our variation's entry rules.

        Must match: coin, direction (unless inverse), session hours.
        Must not already have a position open.
        Must be ACTIVE, PROBATION, or PROMOTED status.
        """
        if self.status in ("KILLED",):
            return False

        if self.position is not None:
            return False

        # Match coin
        pick_symbol = normalize_symbol(pick.get("symbol", ""))
        if pick_symbol != self.coin:
            return False

        # Match direction
        pick_direction = str(pick.get("direction", pick.get("signal_type", "LONG"))).upper()
        if pick_direction not in ("LONG", "SHORT", "BUY", "SELL"):
            return False
        # Normalize BUY/SELL
        if pick_direction == "BUY":
            pick_direction = "LONG"
        elif pick_direction == "SELL":
            pick_direction = "SHORT"

        if pick_direction != self.direction:
            return False

        # Match entry hours (if specified)
        if self.entry_hours and current_hour_utc not in self.entry_hours:
            return False

        return True

    def enter_position(self, entry_price: float, now_iso: str):
        """Open a position for this variation."""
        # Determine trade size based on status
        if self.status == "STAR":
            trade_size = BASE_TRADE_SIZE * STAR_MULTIPLIER
        elif self.status == "PROMOTED":
            trade_size = BASE_TRADE_SIZE * PROMOTED_MULTIPLIER
        else:
            trade_size = BASE_TRADE_SIZE

        # Don't risk more than remaining capital
        trade_size = min(trade_size, self.capital * 0.5)
        if trade_size < 10:
            return  # Not enough capital

        # Calculate TP/SL prices
        if self.direction == "LONG":
            tp_price = entry_price * (1 + self.tp_pct / 100)
            sl_price = entry_price * (1 - self.sl_pct / 100)
        else:
            tp_price = entry_price * (1 - self.tp_pct / 100)
            sl_price = entry_price * (1 + self.sl_pct / 100)

        self.position = {
            "entry_price": entry_price,
            "tp_price": round(tp_price, 8),
            "sl_price": round(sl_price, 8),
            "trade_size": round(trade_size, 2),
            "direction": self.direction,
            "opened_at": now_iso,
        }

    def check_exit(self, current_price: float, now: datetime) -> dict:
        """Check TP/SL/time exits against this variation's params.

        Returns exit info dict if exiting, None otherwise.
        """
        if self.position is None:
            return None

        entry = self.position["entry_price"]
        direction = self.position["direction"]
        tp = self.position["tp_price"]
        sl = self.position["sl_price"]
        trade_size = self.position["trade_size"]

        # Calculate current PnL
        if direction == "LONG":
            pnl_pct = (current_price - entry) / entry * 100
        else:
            pnl_pct = (entry - current_price) / entry * 100

        pnl_usd = trade_size * (pnl_pct / 100)

        # Calculate hours held
        try:
            opened = datetime.fromisoformat(self.position["opened_at"])
            hours_held = (now - opened).total_seconds() / 3600
        except Exception:
            hours_held = 0

        exit_info = None

        # Check TP
        if direction == "LONG" and current_price >= tp:
            exit_info = {"reason": "TP_HIT", "price": current_price}
        elif direction == "SHORT" and current_price <= tp:
            exit_info = {"reason": "TP_HIT", "price": current_price}

        # Check SL
        if exit_info is None:
            if direction == "LONG" and current_price <= sl:
                exit_info = {"reason": "SL_HIT", "price": current_price}
            elif direction == "SHORT" and current_price >= sl:
                exit_info = {"reason": "SL_HIT", "price": current_price}

        # Check time exit
        if exit_info is None and hours_held >= self.max_hold_hours:
            exit_info = {"reason": "TIME_EXIT", "price": current_price}

        if exit_info is not None:
            # Close the position
            trade_record = {
                "entry_price": entry,
                "exit_price": exit_info["price"],
                "direction": direction,
                "pnl_pct": round(pnl_pct, 4),
                "pnl_usd": round(pnl_usd, 2),
                "trade_size": trade_size,
                "hours_held": round(hours_held, 2),
                "reason": exit_info["reason"],
                "opened_at": self.position["opened_at"],
                "closed_at": now.isoformat(),
                "is_win": pnl_pct > 0,
            }
            self.closed_trades.append(trade_record)
            self.capital += pnl_usd
            self.position = None
            return trade_record

        return None

    def get_stats(self) -> dict:
        """Return win rate, PnL, trade count, status recommendation."""
        total = len(self.closed_trades)
        if total == 0:
            return {
                "trades": 0,
                "wins": 0,
                "wr": 0,
                "pnl_pct": 0,
                "pnl_usd": 0,
                "avg_pnl_pct": 0,
                "status_recommendation": "ACTIVE",
            }

        wins = sum(1 for t in self.closed_trades if t.get("is_win", False))
        wr = wins / total
        total_pnl_usd = sum(t.get("pnl_usd", 0) for t in self.closed_trades)
        starting = self.params.get("starting_capital", 1000.0)
        pnl_pct = ((self.capital - starting) / starting) * 100 if starting > 0 else 0
        avg_pnl = sum(t.get("pnl_pct", 0) for t in self.closed_trades) / total

        # Determine status recommendation
        recommendation = self.status
        if total >= STAR_MIN_TRADES and wr >= STAR_WR_THRESHOLD and pnl_pct > 0:
            recommendation = "STAR"
        elif total >= MIN_TRADES_FOR_EVAL:
            if wr < KILL_WR_THRESHOLD or pnl_pct < KILL_PNL_THRESHOLD:
                recommendation = "KILLED"
            elif wr < PROBATION_WR_HIGH:
                # Check if already on probation with enough extra trades
                if self.status == "PROBATION" and total >= MIN_TRADES_FOR_EVAL + PROBATION_EXTRA_TRADES:
                    if wr < PROMOTE_WR_THRESHOLD:
                        recommendation = "KILLED"
                    else:
                        recommendation = "PROMOTED"
                elif self.status != "PROBATION":
                    recommendation = "PROBATION"
            elif wr >= PROMOTE_WR_THRESHOLD and pnl_pct > 0:
                recommendation = "PROMOTED"

        return {
            "trades": total,
            "wins": wins,
            "wr": round(wr, 4),
            "pnl_pct": round(pnl_pct, 2),
            "pnl_usd": round(total_pnl_usd, 2),
            "avg_pnl_pct": round(avg_pnl, 4),
            "status_recommendation": recommendation,
        }

    def to_state(self) -> dict:
        """Serialize tracker state for persistence."""
        stats = self.get_stats()
        return {
            "params": self.params,
            "capital": round(self.capital, 2),
            "position": self.position,
            "closed_trades": self.closed_trades[-50:],  # Keep last 50 trades
            "stats": stats,
            "status": self.status,
        }


def load_state() -> dict:
    """Load existing forward test state."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"updated_at": None, "summary": {}, "variations": {}}


def save_state(state: dict):
    """Save forward test state."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)


def load_variations() -> list:
    """Load strategy variations from generated file."""
    if not VARIATIONS_FILE.exists():
        print(f"  [WARN] {VARIATIONS_FILE} not found. Run strategy_variation_engine.py first.")
        return []

    with open(VARIATIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("variations", [])


def load_active_picks() -> list:
    """Load current active picks from copy trader intel."""
    picks_file = DATA_DIR / "active_picks.json"
    if not picks_file.exists():
        return []
    try:
        with open(picks_file, "r", encoding="utf-8") as f:
            picks = json.load(f)
        return picks if isinstance(picks, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def update_all_variations(picks: list = None, prices: dict = None):
    """Main entry point - called each scan cycle.

    Loads variations + state, checks exits on open positions,
    checks entries on new picks, applies kill/promote logic.
    """
    print("\n" + "=" * 70)
    print("  VARIATION FORWARD TESTER v1.0")
    now = datetime.now(timezone.utc)
    print(f"  {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # Load data
    if picks is None:
        picks = load_active_picks()
    if prices is None:
        prices = fetch_prices()

    if not prices:
        print("  [ERROR] Failed to fetch prices from all APIs")
        return

    variations_data = load_variations()
    if not variations_data:
        print("  [WARN] No variations to test")
        return

    state = load_state()
    existing_variations = state.get("variations", {})

    current_hour = now.hour

    # Build trackers
    trackers = {}
    new_count = 0

    for var in variations_data:
        var_id = var["variation_id"]
        if var_id in existing_variations:
            # Restore existing tracker
            tracker = VariationTracker(var, existing_variations[var_id])
        else:
            # New variation
            tracker = VariationTracker(var)
            new_count += 1
        trackers[var_id] = tracker

    if new_count > 0:
        print(f"  New variations added: {new_count}")
    print(f"  Total variations tracked: {len(trackers)}")

    # === Phase 1: Check exits on open positions ===
    exits_this_cycle = 0
    for var_id, tracker in trackers.items():
        if tracker.position is None:
            continue

        coin = tracker.coin
        current_price = prices.get(coin, 0)
        if current_price <= 0:
            continue

        exit_info = tracker.check_exit(current_price, now)
        if exit_info:
            exits_this_cycle += 1
            pnl = exit_info.get("pnl_pct", 0)
            reason = exit_info.get("reason", "?")
            print(f"  EXIT [{reason}]: {var_id} | {tracker.direction} | "
                  f"PnL: {pnl:+.2f}% (${exit_info.get('pnl_usd', 0):+.2f}) | "
                  f"Hold: {exit_info.get('hours_held', 0):.1f}h")

    if exits_this_cycle > 0:
        print(f"  Exits this cycle: {exits_this_cycle}")

    # === Phase 2: Check entries on new picks ===
    entries_this_cycle = 0
    for pick in picks:
        if not isinstance(pick, dict):
            continue

        pick_symbol = normalize_symbol(pick.get("symbol", ""))
        current_price = prices.get(pick_symbol, 0)
        if current_price <= 0:
            continue

        # Check entry price tolerance
        entry_price = float(pick.get("entry_price", 0) or 0)
        if entry_price > 0:
            gap = abs(current_price - entry_price) / entry_price
            if gap > ENTRY_PRICE_TOLERANCE:
                continue
        # Use current market price for entry
        actual_entry = current_price

        for var_id, tracker in trackers.items():
            if tracker.should_enter(pick, current_hour):
                tracker.enter_position(actual_entry, now.isoformat())
                entries_this_cycle += 1
                print(f"  ENTRY: {var_id} | {tracker.direction} {pick_symbol} @ "
                      f"${actual_entry:.6f} | TP: ${tracker.position['tp_price']:.6f} "
                      f"SL: ${tracker.position['sl_price']:.6f}")

    if entries_this_cycle > 0:
        print(f"  Entries this cycle: {entries_this_cycle}")

    # === Phase 3: Apply kill/promote logic ===
    status_changes = 0
    for var_id, tracker in trackers.items():
        stats = tracker.get_stats()
        recommended = stats["status_recommendation"]

        if recommended != tracker.status:
            old_status = tracker.status
            tracker.status = recommended
            status_changes += 1

            if recommended == "KILLED":
                # Close any open position at current price
                if tracker.position is not None:
                    coin = tracker.coin
                    cp = prices.get(coin, 0)
                    if cp > 0:
                        tracker.check_exit(cp, now)
                    tracker.position = None
                print(f"  KILLED: {var_id} | WR: {stats['wr']*100:.0f}% | "
                      f"PnL: {stats['pnl_pct']:+.1f}% | Trades: {stats['trades']}")
            elif recommended == "PROMOTED":
                print(f"  PROMOTED: {var_id} | WR: {stats['wr']*100:.0f}% | "
                      f"PnL: {stats['pnl_pct']:+.1f}% | Trades: {stats['trades']} | "
                      f"Size -> {BASE_TRADE_SIZE * PROMOTED_MULTIPLIER:.0f}")
            elif recommended == "STAR":
                print(f"  ** STAR **: {var_id} | WR: {stats['wr']*100:.0f}% | "
                      f"PnL: {stats['pnl_pct']:+.1f}% | Trades: {stats['trades']} | "
                      f"GRADUATE TO MAIN PORTFOLIO")
            elif recommended == "PROBATION":
                print(f"  PROBATION: {var_id} | WR: {stats['wr']*100:.0f}% | "
                      f"Trades: {stats['trades']} | 10 more trades to prove itself")

    if status_changes > 0:
        print(f"  Status changes: {status_changes}")

    # === Phase 4: Build summary and save state ===
    status_counts = {"ACTIVE": 0, "PROBATION": 0, "PROMOTED": 0, "KILLED": 0, "STAR": 0}
    total_open_positions = 0
    total_pnl = 0
    total_trades_all = 0

    updated_variations = {}
    for var_id, tracker in trackers.items():
        var_state = tracker.to_state()
        updated_variations[var_id] = var_state
        status_counts[tracker.status] = status_counts.get(tracker.status, 0) + 1
        if tracker.position is not None:
            total_open_positions += 1
        stats = var_state["stats"]
        total_pnl += stats.get("pnl_usd", 0)
        total_trades_all += stats.get("trades", 0)

    final_state = {
        "updated_at": now.isoformat(),
        "summary": {
            "total_variations": len(trackers),
            "active": status_counts.get("ACTIVE", 0),
            "probation": status_counts.get("PROBATION", 0),
            "promoted": status_counts.get("PROMOTED", 0),
            "killed": status_counts.get("KILLED", 0),
            "star": status_counts.get("STAR", 0),
            "open_positions": total_open_positions,
            "total_trades": total_trades_all,
            "total_pnl_usd": round(total_pnl, 2),
        },
        "variations": updated_variations,
    }

    save_state(final_state)

    # Print summary
    print(f"\n{'=' * 70}")
    print(f"  VARIATION FORWARD TEST SUMMARY")
    print(f"  Total: {len(trackers)} | Active: {status_counts['ACTIVE']} | "
          f"Probation: {status_counts['PROBATION']} | Promoted: {status_counts['PROMOTED']} | "
          f"Star: {status_counts['STAR']} | Killed: {status_counts['KILLED']}")
    print(f"  Open positions: {total_open_positions} | Total trades: {total_trades_all}")
    print(f"  Total PnL: ${total_pnl:+.2f}")
    print(f"  State saved: {STATE_FILE}")

    # Top performers
    performers = []
    for var_id, tracker in trackers.items():
        stats = tracker.get_stats()
        if stats["trades"] >= 5:
            performers.append((var_id, stats))

    if performers:
        performers.sort(key=lambda x: x[1]["pnl_pct"], reverse=True)
        print(f"\n  Top 5 Performers (min 5 trades):")
        print(f"  {'Variation':<35s} {'WR':>6s} {'PnL%':>8s} {'PnL$':>8s} {'Trades':>6s} {'Status':>10s}")
        print(f"  {'-'*35} {'-'*6} {'-'*8} {'-'*8} {'-'*6} {'-'*10}")
        for var_id, stats in performers[:5]:
            print(f"  {var_id:<35s} {stats['wr']*100:5.1f}% {stats['pnl_pct']:>+7.1f}% "
                  f"${stats['pnl_usd']:>+7.2f} {stats['trades']:>6d} {stats['status_recommendation']:>10s}")

        # Worst 3
        if len(performers) > 3:
            print(f"\n  Bottom 3 Performers:")
            for var_id, stats in performers[-3:]:
                print(f"  {var_id:<35s} {stats['wr']*100:5.1f}% {stats['pnl_pct']:>+7.1f}% "
                      f"${stats['pnl_usd']:>+7.2f} {stats['trades']:>6d} {stats['status_recommendation']:>10s}")

    print(f"{'=' * 70}\n")

    return final_state


if __name__ == "__main__":
    update_all_variations()
