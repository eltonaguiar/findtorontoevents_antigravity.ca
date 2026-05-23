"""
AsterDEX Paper Trader — Autonomous Signal Executor
====================================================
Reads signals from Alpha Engine + KIMI Rise of the Claw,
executes paper trades on AsterDEX perpetual futures,
tracks positions and P&L in SQLite.

Modes:
  --mode paper    Simulate trades locally, verify against AsterDEX prices (default)
  --mode live     Place real orders on AsterDEX (requires ASTERDEX_PAPER_MODE=false)

Usage:
  py asterdex_paper/paper_trader.py                  # paper mode scan
  py asterdex_paper/paper_trader.py --mode live      # live execution
  py asterdex_paper/paper_trader.py --dashboard      # output dashboard JSON
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from asterdex_paper.client import AsterDEXClient, map_symbol, PAPER_MODE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("asterdex_paper")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "paper_trades.db"
PORTFOLIO_PATH = DATA_DIR / "portfolio_state.json"
DASHBOARD_PATH = DATA_DIR / "dashboard.json"

# Signal sources
KIMI_SIGNALS = ROOT / "KIMI_RISEOFTHECLAW" / "data" / "live_signals_now.json"
ALPHA_PICKS = ROOT / "alpha_engine" / "data" / "active_picks.json"
HMM_REGIME = ROOT / "alpha_engine" / "data" / "hmm_regime.json"

# ---------------------------------------------------------------------------
# Risk parameters
# ---------------------------------------------------------------------------
STARTING_CAPITAL = 10_000.0
MAX_RISK_PER_TRADE = 0.02       # 2% of capital per trade
MAX_POSITION_SIZE = 0.15        # 15% of capital in any single position
MAX_TOTAL_EXPOSURE = 0.80       # 80% max deployed
MAX_OPEN_POSITIONS = 30
DEFAULT_LEVERAGE = 5            # Conservative for paper trading
MIN_CONFIDENCE = 0.50           # Minimum signal confidence to trade
MIN_RISK_REWARD = 1.5           # Minimum risk:reward ratio

# ---------------------------------------------------------------------------
# Strategy intelligence — from proven backtests & live forward tests
# ---------------------------------------------------------------------------

# Strategies with statistically proven edge (p < 0.05)
PROVEN_STRATEGIES = {
    "connors_rsi2",             # SPY 75.7%, QQQ 75.3%, BTC 62.5%
    "vix_spike_reversal",       # SPY 72%, Sharpe 6.20
    "multi_sigma_reversal",     # ATOM 100% live (2/2 wins)
    "rsi_hidden_divergence",    # ATOM 100% live (1/1 win)
    "variance_ratio_momentum",  # BTC currently green
    "m2_liquidity_lag",         # BTC currently green
}

# Strategies that are FAILING in live forward tests — block them
BLOCKED_STRATEGIES = {
    "smart_money_fvg",              # 34.2% WR, Sharpe -1.59, 0/1 live
    "community_ict_fvg_selective",  # 0/3 live, all SL hits
    "mvrv_sma_proxy",              # 0/1 live
}

# Boost confidence for proven strategies (they get priority allocation)
PROVEN_CONFIDENCE_BOOST = 0.15

# HMM regime bearish states — block longs for these symbols
BEAR_REGIMES = {"Strong Bear", "Crash", "Mild Bear"}


# ===========================================================================
# SQLite persistence
# ===========================================================================
def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            asterdex_symbol TEXT,
            side TEXT NOT NULL,
            strategy TEXT,
            source TEXT,
            entry_price REAL NOT NULL,
            current_price REAL,
            quantity REAL NOT NULL,
            notional REAL,
            leverage INTEGER DEFAULT 5,
            take_profit REAL,
            stop_loss REAL,
            confidence REAL,
            risk_reward REAL,
            status TEXT DEFAULT 'OPEN',
            pnl_pct REAL DEFAULT 0.0,
            pnl_usd REAL DEFAULT 0.0,
            mfe REAL DEFAULT 0.0,
            mae REAL DEFAULT 0.0,
            opened_at TEXT NOT NULL,
            closed_at TEXT,
            close_reason TEXT,
            order_id TEXT,
            metadata TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            capital REAL NOT NULL,
            deployed REAL DEFAULT 0.0,
            total_pnl REAL DEFAULT 0.0,
            total_trades INTEGER DEFAULT 0,
            winning_trades INTEGER DEFAULT 0,
            losing_trades INTEGER DEFAULT 0,
            best_trade_pct REAL DEFAULT 0.0,
            worst_trade_pct REAL DEFAULT 0.0,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trade_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id TEXT,
            action TEXT,
            price REAL,
            details TEXT,
            timestamp TEXT
        )
    """)
    # Initialize portfolio if not exists
    cur = conn.execute("SELECT COUNT(*) FROM portfolio")
    if cur.fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO portfolio (id, capital, updated_at) VALUES (1, ?, ?)",
            (STARTING_CAPITAL, _now())
        )
    conn.commit()
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ===========================================================================
# Signal reader — ingests from KIMI + Alpha Engine
# ===========================================================================
def read_signals() -> list[dict]:
    """Read and normalize signals from all sources."""
    signals = []

    # --- KIMI Rise of the Claw ---
    if KIMI_SIGNALS.exists():
        try:
            data = json.loads(KIMI_SIGNALS.read_text())
            for sig in data.get("crypto_signals", []) + data.get("forex_signals", []):
                asterdex_sym = map_symbol(sig.get("symbol", ""))
                if not asterdex_sym:
                    continue
                signals.append({
                    "id": f"kimi::{sig['symbol']}::{sig.get('algorithm', 'unknown')}",
                    "symbol": sig["symbol"],
                    "asterdex_symbol": asterdex_sym,
                    "side": sig.get("signal", "BUY"),
                    "strategy": sig.get("algorithm", "kimi"),
                    "source": "KIMI",
                    "entry_price": sig.get("price", 0),
                    "take_profit": sig.get("take_profit", 0),
                    "stop_loss": sig.get("stop_loss", 0),
                    "confidence": sig.get("confidence", 50) / 100
                        if sig.get("confidence", 0) > 1 else sig.get("confidence", 0.5),
                    "risk_reward": sig.get("risk_reward", 0),
                    "reasons": sig.get("reasons", []),
                })
        except (json.JSONDecodeError, KeyError) as e:
            log.warning(f"KIMI signals read error: {e}")

    # --- Alpha Engine ---
    if ALPHA_PICKS.exists():
        try:
            data = json.loads(ALPHA_PICKS.read_text())
            picks = data if isinstance(data, list) else data.get("picks", [])
            for pick in picks:
                if pick.get("status") != "OPEN":
                    continue
                asterdex_sym = map_symbol(pick.get("symbol", ""))
                if not asterdex_sym:
                    continue
                signals.append({
                    "id": pick.get("id", f"alpha::{pick['symbol']}"),
                    "symbol": pick["symbol"],
                    "asterdex_symbol": asterdex_sym,
                    "side": pick.get("signal_type", "BUY"),
                    "strategy": pick.get("strategy", "alpha"),
                    "source": "ALPHA",
                    "entry_price": pick.get("entry_price", 0),
                    "take_profit": pick.get("take_profit", 0),
                    "stop_loss": pick.get("stop_loss", 0),
                    "confidence": pick.get("confidence", 0.5),
                    "risk_reward": pick.get("risk_reward", 0),
                    "reasons": [pick.get("reason", "")],
                })
        except (json.JSONDecodeError, KeyError) as e:
            log.warning(f"Alpha Engine signals read error: {e}")

    log.info(f"Read {len(signals)} raw signals ({sum(1 for s in signals if s['source']=='KIMI')} KIMI, "
             f"{sum(1 for s in signals if s['source']=='ALPHA')} Alpha)")

    # --- Apply intelligence filters ---
    regime = _read_regime()
    filtered = []
    for sig in signals:
        strategy = sig["strategy"]
        symbol = sig["symbol"]
        side = sig["side"]

        # Block failing strategies
        if strategy in BLOCKED_STRATEGIES:
            log.info(f"  BLOCKED {symbol} [{strategy}] — strategy is failing in live tests")
            continue

        # Block longs in bear regime
        sym_regime = regime.get(symbol, "")
        if side == "BUY" and sym_regime in BEAR_REGIMES:
            log.info(f"  BLOCKED {symbol} LONG [{strategy}] — HMM regime: {sym_regime}")
            continue

        # Boost proven strategies
        if strategy in PROVEN_STRATEGIES:
            sig["confidence"] = min(1.0, sig["confidence"] + PROVEN_CONFIDENCE_BOOST)
            log.debug(f"  BOOSTED {symbol} [{strategy}] confidence +{PROVEN_CONFIDENCE_BOOST}")

        filtered.append(sig)

    log.info(f"After filters: {len(filtered)} signals ({len(signals) - len(filtered)} blocked)")
    return filtered


def _read_regime() -> dict[str, str]:
    """Read HMM regime data to block longs in bear markets."""
    if not HMM_REGIME.exists():
        return {}
    try:
        data = json.loads(HMM_REGIME.read_text())
        regimes = {}
        for entry in data if isinstance(data, list) else data.get("regimes", []):
            sym = entry.get("symbol", "")
            regime = entry.get("regime", entry.get("regime_name", ""))
            if sym and regime:
                regimes[sym] = regime
        return regimes
    except (json.JSONDecodeError, KeyError):
        return {}


# ===========================================================================
# Position sizing
# ===========================================================================
def calculate_position_size(signal: dict, capital: float, leverage: int) -> float | None:
    """Risk-based position sizing: risk_amount / stop_distance."""
    entry = signal["entry_price"]
    sl = signal["stop_loss"]
    if entry <= 0 or sl <= 0:
        return None

    stop_distance_pct = abs(entry - sl) / entry
    if stop_distance_pct < 0.001:  # < 0.1% stop = too tight
        return None

    risk_amount = capital * MAX_RISK_PER_TRADE  # e.g., $200 on $10K
    max_notional = capital * MAX_POSITION_SIZE   # e.g., $1,500

    # Notional = risk / stop_distance (how much capital for this risk)
    notional = min(risk_amount / stop_distance_pct, max_notional)
    # Apply leverage
    margin_required = notional / leverage
    quantity = notional / entry

    return round(quantity, 8)


# ===========================================================================
# Core paper trading engine
# ===========================================================================
class PaperTrader:
    def __init__(self, mode: str = "paper"):
        self.client = AsterDEXClient()
        self.conn = init_db()
        self.mode = mode
        self.available_symbols: set[str] = set()

    def _fetch_available_symbols(self):
        """Fetch tradeable symbols from AsterDEX."""
        info = self.client.exchange_info()
        if isinstance(info, dict) and "symbols" in info:
            self.available_symbols = {
                s["symbol"] for s in info["symbols"]
                if s.get("status") == "TRADING"
            }
            log.info(f"AsterDEX: {len(self.available_symbols)} tradeable symbols")
        else:
            log.warning(f"Could not fetch exchange info: {info}")

    def _get_portfolio(self) -> dict:
        row = self.conn.execute("SELECT * FROM portfolio WHERE id = 1").fetchone()
        return dict(row) if row else {"capital": STARTING_CAPITAL, "deployed": 0}

    def _get_open_trades(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM trades WHERE status = 'OPEN'").fetchall()
        return [dict(r) for r in rows]

    def _trade_exists(self, trade_id: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM trades WHERE id = ? AND status = 'OPEN'",
                                (trade_id,)).fetchone()
        return row is not None

    def open_trade(self, signal: dict, quantity: float, leverage: int = DEFAULT_LEVERAGE):
        """Open a paper trade (or real order in live mode)."""
        trade_id = signal["id"]
        asterdex_sym = signal["asterdex_symbol"]
        entry = signal["entry_price"]
        notional = quantity * entry
        order_id = None

        # Live mode: place real order on AsterDEX
        if self.mode == "live" and not PAPER_MODE:
            log.info(f"LIVE ORDER: {signal['side']} {quantity} {asterdex_sym} @ market")
            # Set leverage
            self.client.set_leverage(asterdex_sym, leverage)
            # Place entry + TP + SL
            result = self.client.place_order_with_tp_sl(
                symbol=asterdex_sym,
                side=signal["side"],
                quantity=quantity,
                take_profit=signal["take_profit"],
                stop_loss=signal["stop_loss"],
            )
            if isinstance(result, list) and len(result) > 0:
                order_id = str(result[0].get("orderId", ""))
                log.info(f"  Order placed: {order_id}")
            else:
                log.error(f"  Order failed: {result}")
                return
        else:
            log.info(f"PAPER TRADE: {signal['side']} {quantity:.6f} {asterdex_sym} "
                     f"@ ${entry:,.2f} | TP: ${signal['take_profit']:,.2f} | "
                     f"SL: ${signal['stop_loss']:,.2f} | [{signal['strategy']}]")

        # Record in SQLite
        self.conn.execute("""
            INSERT OR REPLACE INTO trades
            (id, symbol, asterdex_symbol, side, strategy, source, entry_price,
             current_price, quantity, notional, leverage, take_profit, stop_loss,
             confidence, risk_reward, status, opened_at, order_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?)
        """, (
            trade_id, signal["symbol"], asterdex_sym, signal["side"],
            signal["strategy"], signal["source"], entry, entry,
            quantity, notional, leverage, signal["take_profit"], signal["stop_loss"],
            signal["confidence"], signal["risk_reward"], _now(), order_id,
            json.dumps(signal.get("reasons", [])),
        ))
        # Update portfolio deployed amount
        portfolio = self._get_portfolio()
        self.conn.execute(
            "UPDATE portfolio SET deployed = deployed + ?, total_trades = total_trades + 1, updated_at = ?",
            (notional / leverage, _now())
        )
        self.conn.commit()

        # Log
        self.conn.execute(
            "INSERT INTO trade_log (trade_id, action, price, details, timestamp) VALUES (?, ?, ?, ?, ?)",
            (trade_id, "OPEN", entry, f"{signal['side']} {quantity:.6f} {asterdex_sym}", _now())
        )
        self.conn.commit()

    def _get_candle_extremes(self, symbol: str) -> tuple[float, float, float] | None:
        """Fetch 5m klines for the last 35 min and return (high, low, close).

        This catches every wick between scan cycles so TP/SL hits are never
        missed, even if the price touched the level for only seconds.
        """
        # 7 candles × 5 min = 35 min of coverage (exceeds 30-min scan gap)
        klines = self.client.get_klines(symbol, interval="5m", limit=7)
        if not isinstance(klines, list) or len(klines) == 0:
            return None
        # kline format: [open_time, open, high, low, close, volume, ...]
        period_high = max(float(k[2]) for k in klines)
        period_low = min(float(k[3]) for k in klines)
        last_close = float(klines[-1][4])
        return period_high, period_low, last_close

    def check_tp_sl(self, prices: dict[str, float]):
        """Check open trades using candle high/low (not just last price).

        Fetches 5-minute klines covering the full interval between scans,
        so a wick that touches TP or SL for even one second is detected.
        """
        open_trades = self._get_open_trades()
        for trade in open_trades:
            sym = trade["asterdex_symbol"]
            entry = trade["entry_price"]
            tp = trade["take_profit"]
            sl = trade["stop_loss"]
            side = trade["side"]

            # Fetch candle high/low for full inter-scan coverage
            extremes = self._get_candle_extremes(sym)
            if extremes is None:
                # Fallback to snapshot price if klines unavailable
                if sym not in prices:
                    continue
                period_high = period_low = current = prices[sym]
            else:
                period_high, period_low, current = extremes

            # Check TP/SL against candle extremes (catches every wick)
            if side == "BUY":
                pnl_pct = (current - entry) / entry
                hit_tp = period_high >= tp if tp > 0 else False
                hit_sl = period_low <= sl if sl > 0 else False
                # MFE/MAE from extremes
                mfe_candidate = (period_high - entry) / entry
                mae_candidate = (period_low - entry) / entry
            else:  # SELL / SHORT
                pnl_pct = (entry - current) / entry
                hit_tp = period_low <= tp if tp > 0 else False
                hit_sl = period_high >= sl if sl > 0 else False
                mfe_candidate = (entry - period_low) / entry
                mae_candidate = (entry - period_high) / entry

            pnl_usd = pnl_pct * trade["notional"]
            mfe = max(trade["mfe"], mfe_candidate)
            mae = min(trade["mae"], mae_candidate)

            close_reason = None
            # If both TP and SL hit in same period (huge wick), be
            # conservative: assume SL hit first (worst case)
            if hit_tp and hit_sl:
                close_reason = "STOP_LOSS"
                log.warning(f"  {sym}: both TP & SL wicked in same period — "
                            f"assuming SL hit first (conservative)")
            elif hit_tp:
                close_reason = "TAKE_PROFIT"
            elif hit_sl:
                close_reason = "STOP_LOSS"

            if close_reason == "TAKE_PROFIT":
                if side == "BUY":
                    pnl_pct = (tp - entry) / entry
                else:
                    pnl_pct = (entry - tp) / entry
                pnl_usd = pnl_pct * trade["notional"]
            elif close_reason == "STOP_LOSS":
                if side == "BUY":
                    pnl_pct = (sl - entry) / entry
                else:
                    pnl_pct = (entry - sl) / entry
                pnl_usd = pnl_pct * trade["notional"]

            if close_reason:
                # Close the trade
                self.conn.execute("""
                    UPDATE trades SET status = 'CLOSED', current_price = ?,
                    pnl_pct = ?, pnl_usd = ?, mfe = ?, mae = ?,
                    closed_at = ?, close_reason = ?
                    WHERE id = ?
                """, (current, pnl_pct, pnl_usd, mfe, mae, _now(), close_reason, trade["id"]))

                # Update portfolio
                win = 1 if pnl_pct > 0 else 0
                self.conn.execute("""
                    UPDATE portfolio SET
                        capital = capital + ?,
                        deployed = MAX(0, deployed - ?),
                        total_pnl = total_pnl + ?,
                        winning_trades = winning_trades + ?,
                        losing_trades = losing_trades + ?,
                        best_trade_pct = MAX(best_trade_pct, ?),
                        worst_trade_pct = MIN(worst_trade_pct, ?),
                        updated_at = ?
                    WHERE id = 1
                """, (pnl_usd, trade["notional"] / trade["leverage"],
                      pnl_usd, win, 1 - win, pnl_pct, pnl_pct, _now()))

                # Live mode: cancel remaining TP/SL orders
                if self.mode == "live" and not PAPER_MODE:
                    self.client.cancel_all_orders(sym)

                log.info(f"  CLOSED {trade['id']}: {close_reason} "
                         f"(high=${period_high:,.2f} low=${period_low:,.2f}) | "
                         f"P&L: {pnl_pct:+.2%} (${pnl_usd:+,.2f})")

                self.conn.execute(
                    "INSERT INTO trade_log (trade_id, action, price, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (trade["id"], close_reason, current,
                     f"P&L: {pnl_pct:+.2%} (${pnl_usd:+,.2f}) | "
                     f"high={period_high:.2f} low={period_low:.2f}", _now())
                )
            else:
                # Update current price and MFE/MAE
                self.conn.execute("""
                    UPDATE trades SET current_price = ?, pnl_pct = ?, pnl_usd = ?,
                    mfe = ?, mae = ? WHERE id = ?
                """, (current, pnl_pct, pnl_usd, mfe, mae, trade["id"]))

        self.conn.commit()

    def run_scan(self):
        """Main scan cycle: read signals → filter → size → execute → check TP/SL."""
        log.info("=" * 70)
        log.info(f"AsterDEX Paper Trader — {self.mode.upper()} MODE")
        log.info("=" * 70)

        # 1. Fetch available symbols and prices
        self._fetch_available_symbols()
        all_prices = self.client.get_all_prices()
        if not all_prices:
            log.error("Could not fetch AsterDEX prices. Aborting.")
            return

        log.info(f"Fetched {len(all_prices)} prices from AsterDEX")

        # 2. Check existing positions for TP/SL
        self.check_tp_sl(all_prices)

        # 3. Read new signals
        signals = read_signals()
        portfolio = self._get_portfolio()
        open_trades = self._get_open_trades()
        open_symbols = {t["asterdex_symbol"] for t in open_trades}

        log.info(f"Portfolio: ${portfolio['capital']:,.2f} | "
                 f"Deployed: ${portfolio['deployed']:,.2f} | "
                 f"Open: {len(open_trades)}/{MAX_OPEN_POSITIONS}")

        # 4. Filter and execute new signals
        new_trades = 0
        for sig in signals:
            # Skip if already have this trade open
            if self._trade_exists(sig["id"]):
                continue
            # Skip if already have position in this symbol
            if sig["asterdex_symbol"] in open_symbols:
                continue
            # Skip if symbol not on AsterDEX
            if self.available_symbols and sig["asterdex_symbol"] not in self.available_symbols:
                log.debug(f"  Skip {sig['asterdex_symbol']}: not on AsterDEX")
                continue
            # Skip low confidence
            if sig["confidence"] < MIN_CONFIDENCE:
                continue
            # Skip low R:R
            if sig["risk_reward"] > 0 and sig["risk_reward"] < MIN_RISK_REWARD:
                continue
            # Skip if max positions reached
            if len(open_trades) + new_trades >= MAX_OPEN_POSITIONS:
                break
            # Skip if max exposure reached
            if portfolio["deployed"] >= portfolio["capital"] * MAX_TOTAL_EXPOSURE:
                break

            # Calculate position size
            qty = calculate_position_size(sig, portfolio["capital"], DEFAULT_LEVERAGE)
            if qty is None or qty <= 0:
                continue

            # Use real AsterDEX price if available
            real_price = all_prices.get(sig["asterdex_symbol"])
            if real_price:
                sig["entry_price"] = real_price

            self.open_trade(sig, qty)
            open_symbols.add(sig["asterdex_symbol"])
            new_trades += 1

        log.info(f"Opened {new_trades} new trades this cycle")

        # 5. Generate dashboard output
        self._write_dashboard(all_prices)

    def _write_dashboard(self, prices: dict[str, float]):
        """Write dashboard JSON for the HTML frontend."""
        portfolio = self._get_portfolio()
        open_trades = self._get_open_trades()
        closed = self.conn.execute(
            "SELECT * FROM trades WHERE status = 'CLOSED' ORDER BY closed_at DESC LIMIT 50"
        ).fetchall()

        total_trades = portfolio.get("total_trades", 0)
        wins = portfolio.get("winning_trades", 0)
        losses = portfolio.get("losing_trades", 0)
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

        dashboard = {
            "generated_at": _now(),
            "mode": self.mode,
            "portfolio": {
                "starting_capital": STARTING_CAPITAL,
                "current_capital": portfolio["capital"],
                "deployed": portfolio["deployed"],
                "available": portfolio["capital"] - portfolio["deployed"],
                "total_pnl": portfolio.get("total_pnl", 0),
                "total_pnl_pct": (portfolio.get("total_pnl", 0) / STARTING_CAPITAL) * 100,
                "total_trades": total_trades,
                "winning_trades": wins,
                "losing_trades": losses,
                "win_rate": win_rate,
                "best_trade": portfolio.get("best_trade_pct", 0),
                "worst_trade": portfolio.get("worst_trade_pct", 0),
            },
            "open_positions": [],
            "recent_closed": [],
            "signal_sources": {
                "kimi_signals": KIMI_SIGNALS.exists(),
                "alpha_picks": ALPHA_PICKS.exists(),
            }
        }

        for t in open_trades:
            current = prices.get(t["asterdex_symbol"], t["current_price"] or t["entry_price"])
            side = t["side"]
            if side == "BUY":
                pnl_pct = (current - t["entry_price"]) / t["entry_price"]
            else:
                pnl_pct = (t["entry_price"] - current) / t["entry_price"]
            dashboard["open_positions"].append({
                "id": t["id"],
                "symbol": t["symbol"],
                "asterdex_symbol": t["asterdex_symbol"],
                "side": side,
                "strategy": t["strategy"],
                "source": t["source"],
                "entry_price": t["entry_price"],
                "current_price": current,
                "take_profit": t["take_profit"],
                "stop_loss": t["stop_loss"],
                "quantity": t["quantity"],
                "leverage": t["leverage"],
                "confidence": t["confidence"],
                "pnl_pct": pnl_pct,
                "pnl_usd": pnl_pct * t["notional"],
                "opened_at": t["opened_at"],
            })

        for t in [dict(r) for r in closed]:
            dashboard["recent_closed"].append({
                "id": t["id"],
                "symbol": t["symbol"],
                "side": t["side"],
                "strategy": t["strategy"],
                "source": t["source"],
                "entry_price": t["entry_price"],
                "pnl_pct": t["pnl_pct"],
                "pnl_usd": t["pnl_usd"],
                "close_reason": t["close_reason"],
                "opened_at": t["opened_at"],
                "closed_at": t["closed_at"],
            })

        DASHBOARD_PATH.write_text(json.dumps(dashboard, indent=2))
        log.info(f"Dashboard written: {DASHBOARD_PATH}")

        # Also write portfolio state
        PORTFOLIO_PATH.write_text(json.dumps(dashboard["portfolio"], indent=2))

        return dashboard


# ===========================================================================
# CLI
# ===========================================================================
def main():
    parser = argparse.ArgumentParser(description="AsterDEX Paper Trader")
    parser.add_argument("--mode", choices=["paper", "live"], default="paper")
    parser.add_argument("--dashboard", action="store_true", help="Only output dashboard")
    args = parser.parse_args()

    trader = PaperTrader(mode=args.mode)

    if args.mode == "live" and PAPER_MODE:
        log.error("Live mode blocked: ASTERDEX_PAPER_MODE=true in .env")
        log.error("Set ASTERDEX_PAPER_MODE=false to enable live trading")
        sys.exit(1)

    if args.dashboard:
        prices = trader.client.get_all_prices()
        trader._write_dashboard(prices)
    else:
        trader.run_scan()


if __name__ == "__main__":
    main()
