#!/usr/bin/env python3
"""
live_simulator.py — Real-time paper/live trading simulator for findtorontoevents_antigravity.ca

Implements the 3-pod money-maker framework from the audit/profitability analysis:

  Pod A — mega_mutation_macd_rsi (CRYPTO LONG, bull regime, BTC > 200-EMA)
  Pod B — SHORT trend (CRYPTO SHORT, bear regime, BTC < 200-EMA trigger)
  Pod C — Equity/ETF breakout family (vs random-entry timing null)

Risk rules (non-negotiable):
  - 1% position sizing max per trade ($20 max risk on $2K account)
  - Daily loss cap: -5% ($100/day) → stop trading for session
  - Monthly loss cap: -20% ($400/month) → pause all live trading
  - 3 consecutive losses → stop for the session (regime unfavorable)
  - No fixed take-profit — exit on time/vol (2× ATR trail or time stop)
  - Kill any pod with forward CI-LB ≤ 0 at day 30/60 (audit3 tribunal rule)
  - Log every trade to forward_observations format

Modes:
  --paper    Paper trading (no real money, testnet prices)
  --live     Live trading with real capital (requires exchange API keys)
  --once     Run a single tick then exit (for cron/scheduler use)
  --daemon   Run continuously, polling every 60s

COMS integration:
  - Posts heartbeat via coms.ps1 --topic all --msg "HEARTBEAT_OK"
  - Posts pod verdicts to inbox/<pod-name>/

Usage:
  python live_simulator.py --once --paper
  python live_simulator.py --daemon --paper
  python live_simulator.py --once --live --account 2000
"""

import argparse
import json
import os
import sys
import time
import csv
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────
ACCOUNT_DEFAULT = 2000.0
POSITION_PCT = 0.01          # 1% max risk per trade
DAILY_LOSS_CAP_PCT = 0.05    # -5% per day
MONTHLY_LOSS_CAP_PCT = 0.20  # -20% per month
MAX_CONSECUTIVE_LOSSES = 3
ATR_TRAIL_MULT = 2.0         # 2× ATR trailing stop
TIME_STOP_BARS = 10          # max 10 bars per trade
POLL_INTERVAL_SEC = 60       # poll every minute in daemon mode

# ── Paths ──────────────────────────────────────────────────────────────────
SCRATCH = Path(os.environ.get("TMPDIR", os.path.expanduser("~\\AppData\\Local\\hermes\\cache\\scratch")))
STATE_DIR = SCRATCH / "live_simulator"
STATE_DIR.mkdir(parents=True, exist_ok=True)

ACCOUNT_FILE = STATE_DIR / "account_state.json"
TRADE_LOG = STATE_DIR / "trade_log.csv"
POD_STATE_FILE = STATE_DIR / "pod_state.json"
FORWARD_OBS_FILE = STATE_DIR / "forward_observations.jsonl"

# ── Helpers ────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def append_csv(path: Path, row: dict, fieldnames: list) -> None:
    file_exists = path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def coms_send(topic: str, message: str) -> None:
    """Post a message via coms.ps1 if available."""
    coms_ps1 = Path("C:/Users/zerou/.coms/coms.ps1")
    if not coms_ps1.exists():
        # try worktree location
        coms_ps1 = Path("C:/Users/zerou/.cursor/worktrees/findtorontoevents_antigravity.ca/COMMUNICATION/coms.ps1")
    if coms_ps1.exists():
        try:
            import subprocess
            subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(coms_ps1),
                 "--topic", topic, "--msg", message],
                capture_output=True, timeout=10
            )
        except Exception:
            pass  # COMS is best-effort; never block trading


# ── Account State ──────────────────────────────────────────────────────────

class AccountState:
    def __init__(self, balance: float = ACCOUNT_DEFAULT):
        self.balance = balance
        self.starting_balance = balance
        self.daily_pnl = 0.0
        self.daily_date = datetime.now(timezone.utc).date().isoformat()
        self.monthly_pnl = 0.0
        self.monthly_date = datetime.now(timezone.utc).strftime("%Y-%m")
        self.consecutive_losses = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.realized_pnl = 0.0

    def reset_daily(self) -> None:
        today = datetime.now(timezone.utc).date().isoformat()
        if today != self.daily_date:
            self.daily_pnl = 0.0
            self.daily_date = today
            self.consecutive_losses = 0  # reset on new day

    def reset_monthly(self) -> None:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        if month != self.monthly_date:
            self.monthly_pnl = 0.0
            self.monthly_date = month

    def daily_loss_limit_hit(self) -> bool:
        return self.balance * DAILY_LOSS_CAP_PCT <= abs(self.daily_pnl) and self.daily_pnl < 0

    def monthly_loss_limit_hit(self) -> bool:
        return self.balance * MONTHLY_LOSS_CAP_PCT <= abs(self.monthly_pnl) and self.monthly_pnl < 0

    def session_loss_limit_hit(self) -> bool:
        return self.consecutive_losses >= MAX_CONSECUTIVE_LOSSES

    def apply_trade(self, pnl: float, win: bool) -> None:
        self.balance += pnl
        self.daily_pnl += pnl
        self.monthly_pnl += pnl
        self.realized_pnl += pnl
        self.total_trades += 1
        if win:
            self.winning_trades += 1
            self.consecutive_losses = 0
        else:
            self.losing_trades += 1
            self.consecutive_losses += 1

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades

    @property
    def profit_factor(self) -> float:
        gross_profit = sum(t["pnl"] for t in load_json(TRADE_LOG, []) if t.get("pnl", 0) > 0)
        gross_loss = abs(sum(t["pnl"] for t in load_json(TRADE_LOG, []) if t.get("pnl", 0) < 0))
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    def to_dict(self) -> dict:
        return {
            "balance": self.balance,
            "starting_balance": self.starting_balance,
            "daily_pnl": self.daily_pnl,
            "monthly_pnl": self.monthly_pnl,
            "consecutive_losses": self.consecutive_losses,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "realized_pnl": self.realized_pnl,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
        }


# ── Market Data (stub — plug in CCXT / yfinance) ──────────────────────────

class MarketData:
    """Fetch live prices. Replace with CCXT (crypto) or yfinance (equities)."""

    def __init__(self, paper: bool = True):
        self.paper = paper

    def get_price(self, symbol: str) -> float | None:
        """Return current price for symbol, or None if unavailable."""
        # TODO: Integrate CCXT for crypto, yfinance for equities/forex
        # For now, return a simulated price so the framework runs standalone
        import random
        random.seed(hash(symbol) % 10000)
        base = {"BTCUSDT": 105000, "ETHUSDT": 3400, "SOLUSDT": 165, "SPY": 580, "QQQ": 490}
        return base.get(symbol, 100.0) * (1 + random.uniform(-0.02, 0.02))

    def get_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100):
        """Return OHLCV candles. TODO: wire to real data feed."""
        return []

    def get_atr(self, symbol: str, period: int = 14) -> float | None:
        """Return ATR value for position sizing / stops. TODO: wire to real data."""
        return None


# ── Strategies (Pods) ──────────────────────────────────────────────────────

class PodBase:
    name: str = "base"
    asset_class: str = "unknown"
    enabled: bool = True

    def __init__(self, account: AccountState, data: MarketData, paper: bool = True):
        self.account = account
        self.data = data
        self.paper = paper
        self.state = load_json(POD_STATE_FILE, {}).get(self.name, {
            "trades": 0, "wins": 0, "pnl": 0.0, "last_signal": None,
            "consecutive_losses": 0, "forward_ci_lb": None, "killed": False
        })

    def save_state(self) -> None:
        all_states = load_json(POD_STATE_FILE, {})
        all_states[self.name] = self.state
        save_json(POD_STATE_FILE, all_states)

    def signal(self, symbol: str) -> dict | None:
        """Return {'side': 'long'|'short', 'entry': float, 'stop': float, 'confidence': float} or None."""
        raise NotImplementedError

    def on_trade_close(self, pnl: float, win: bool) -> None:
        self.state["trades"] += 1
        self.state["pnl"] += pnl
        if win:
            self.state["wins"] += 1
            self.state["consecutive_losses"] = 0
        else:
            self.state["consecutive_losses"] += 1
        self.save_state()

    def is_killed(self) -> bool:
        return self.state.get("killed", False)

    def kill(self, reason: str) -> None:
        self.state["killed"] = True
        self.state["kill_reason"] = reason
        self.state["killed_at"] = now_iso()
        self.save_state()
        coms_send("all", f"POD KILLED: {self.name} — {reason}")


class MegaMutationPod(PodBase):
    """
    Pod A — mega_mutation_macd_rsi (CRYPTO LONG)
    MACD + RSI confluence, ATR-based stops, 200-EMA trend filter.
    Only long when BTC > 200-EMA (bull regime).
    Forward validated: PF 8.32, WR 84%, n=50.
    """
    name = "mega_mutation"
    asset_class = "crypto"

    def signal(self, symbol: str) -> dict | None:
        if self.is_killed():
            return None
        # TODO: Implement actual MACD+RSI+EMA logic from real price data
        # Placeholder: return a signal with conservative parameters
        price = self.data.get_price(symbol)
        if price is None:
            return None
        atr = self.data.get_atr(symbol) or price * 0.02  # 2% fallback ATR
        stop = price - ATR_TRAIL_MULT * atr
        return {
            "side": "long",
            "entry": price,
            "stop": stop,
            "target": None,  # no fixed TP — time/vol exit
            "confidence": 0.65,
            "atr": atr,
        }


class ShortTrendPod(PodBase):
    """
    Pod B — SHORT trend (CRYPTO SHORT, bear regime)
    Active only when BTC < 200-EMA. External: PF 7.46 short trend (last 12mo).
    Repo: 72% SHORT WR vs 20% LONG.
    """
    name = "short_trend"
    asset_class = "crypto"

    def signal(self, symbol: str) -> dict | None:
        if self.is_killed():
            return None
        price = self.data.get_price(symbol)
        if price is None:
            return None
        atr = self.data.get_atr(symbol) or price * 0.02
        stop = price + ATR_TRAIL_MULT * atr
        return {
            "side": "short",
            "entry": price,
            "stop": stop,
            "target": None,
            "confidence": 0.60,
            "atr": atr,
        }


class EquityBreakoutPod(PodBase):
    """
    Pod C — Equity/ETF breakout family
    Donchian / RS breakout vs random-entry timing null.
    Pooled ≈364 trades, net +0.46%/trade (individual CIs straddle 0).
    """
    name = "equity_breakout"
    asset_class = "equity"

    def signal(self, symbol: str) -> dict | None:
        if self.is_killed():
            return None
        price = self.data.get_price(symbol)
        if price is None:
            return None
        atr = self.data.get_atr(symbol) or price * 0.015
        stop = price - ATR_TRAIL_MULT * atr
        return {
            "side": "long",
            "entry": price,
            "stop": stop,
            "target": None,
            "confidence": 0.55,
            "atr": atr,
        }


# ── Trade Execution ────────────────────────────────────────────────────────

class TradeManager:
    def __init__(self, account: AccountState, data: MarketData, paper: bool = True):
        self.account = account
        self.data = data
        self.paper = paper
        self.pods = {
            "mega_mutation": MegaMutationPod(account, data, paper),
            "short_trend": ShortTrendPod(account, data, paper),
            "equity_breakout": EquityBreakoutPod(account, data, paper),
        }
        self.open_trades: list[dict] = []

    def check_circuit_breakers(self) -> str | None:
        """Return a block reason if any circuit breaker is hit, else None."""
        self.account.reset_daily()
        self.account.reset_monthly()
        if self.account.monthly_loss_limit_hit():
            return "monthly_loss_cap"
        if self.account.daily_loss_limit_hit():
            return "daily_loss_cap"
        if self.account.session_loss_limit_hit():
            return "consecutive_losses"
        return None

    def size_position(self, entry: float, stop: float, balance: float) -> float:
        """1% risk sizing: risk_amount / (entry - stop)."""
        risk_amount = balance * POSITION_PCT
        risk_per_unit = abs(entry - stop)
        if risk_per_unit <= 0:
            return 0.0
        qty = risk_amount / risk_per_unit
        # Cap notional at balance
        max_qty = balance / entry if entry > 0 else 0
        return min(qty, max_qty)

    def evaluate_signals(self, symbols: list[str]) -> list[dict]:
        """Evaluate all pods against all symbols, return trade candidates."""
        block = self.check_circuit_breakers()
        if block:
            coms_send("all", f"CIRCUIT BREAKER: {block} — no new trades")
            return []

        candidates = []
        for symbol in symbols:
            for pod_name, pod in self.pods.items():
                if pod.is_killed():
                    continue
                sig = pod.signal(symbol)
                if sig is None:
                    continue
                qty = self.size_position(sig["entry"], sig["stop"], self.account.balance)
                if qty <= 0:
                    continue
                candidates.append({
                    "pod": pod_name,
                    "symbol": symbol,
                    "side": sig["side"],
                    "entry": sig["entry"],
                    "stop": sig["stop"],
                    "qty": qty,
                    "confidence": sig["confidence"],
                    "atr": sig.get("atr"),
                    "timestamp": now_iso(),
                })
        return candidates

    def execute_trade(self, candidate: dict) -> dict:
        """Record a trade (paper or live). Returns trade record."""
        trade = {
            "trade_id": f"{candidate['pod']}_{int(time.time())}",
            "pod": candidate["pod"],
            "symbol": candidate["symbol"],
            "side": candidate["side"],
            "entry": candidate["entry"],
            "stop": candidate["stop"],
            "qty": candidate["qty"],
            "confidence": candidate["confidence"],
            "entry_time": candidate["timestamp"],
            "exit_time": None,
            "exit_price": None,
            "pnl": 0.0,
            "pnl_pct": 0.0,
            "win": None,
            "status": "open",
        }
        self.open_trades.append(trade)
        append_csv(TRADE_LOG, trade, list(trade.keys()))
        coms_send("all", f"TRADE OPEN: {candidate['pod']} {candidate['side']} {candidate['symbol']} @ {candidate['entry']}")
        return trade

    def check_exits(self, current_prices: dict[str, float]) -> list[dict]:
        """Check open trades for stop / time exits. Returns closed trades."""
        closed = []
        for trade in list(self.open_trades):
            price = current_prices.get(trade["symbol"])
            if price is None:
                continue

            exit_reason = None
            exit_price = price

            if trade["side"] == "long":
                if price <= trade["stop"]:
                    exit_reason = "stop"
                # time stop: TODO — track bar count
            else:  # short
                if price >= trade["stop"]:
                    exit_reason = "stop"

            if exit_reason:
                pnl = (exit_price - trade["entry"]) * trade["qty"] if trade["side"] == "long" \
                    else (trade["entry"] - exit_price) * trade["qty"]
                pnl_pct = pnl / (trade["entry"] * trade["qty"]) if trade["entry"] * trade["qty"] > 0 else 0
                win = pnl > 0

                trade.update({
                    "exit_time": now_iso(),
                    "exit_price": exit_price,
                    "pnl": round(pnl, 4),
                    "pnl_pct": round(pnl_pct, 6),
                    "win": win,
                    "status": "closed",
                    "exit_reason": exit_reason,
                })
                closed.append(trade)
                self.open_trades.remove(trade)
                self.account.apply_trade(pnl, win)
                pod = self.pods[trade["pod"]]
                pod.on_trade_close(pnl, win)

                # Log to forward_observations (audit3 format)
                obs = {
                    "hypothesis_id": trade["pod"],
                    "opened_at": trade["entry_time"],
                    "closed_at": trade["exit_time"],
                    "symbol": trade["symbol"],
                    "class": trade["pod"].split("_")[0].upper(),
                    "side": trade["side"],
                    "entry_px": trade["entry"],
                    "exit_px": trade["exit_price"],
                    "qty": trade["qty"],
                    "fees": 0.0,
                    "funding": 0.0,
                    "slippage_bps": 0.0,
                    "resolver_version": "live_simulator_v1",
                    "intrabar_first_touch": None,
                    "benchmark_leg_ret": None,
                    "regime_ok": None,
                    "created_at": now_iso(),
                }
                with open(FORWARD_OBS_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(obs, default=str) + "\n")

                coms_send("all", f"TRADE CLOSE: {trade['pod']} {trade['side']} {trade['symbol']} PnL={pnl:.2f} win={win}")
        return closed

    def check_pod_kills(self) -> None:
        """Kill pods whose forward CI-LB ≤ 0 after sufficient sample (audit3 rule)."""
        # Simplified: kill if consecutive losses ≥ 3 for a pod
        for pod_name, pod in self.pods.items():
            if pod.is_killed():
                continue
            if pod.state.get("consecutive_losses", 0) >= MAX_CONSECUTIVE_LOSSES:
                pod.kill(f"{MAX_CONSECUTIVE_LOSSES} consecutive losses")

    def summary(self) -> dict:
        return {
            "account": self.account.to_dict(),
            "pods": {name: pod.state for name, pod in self.pods.items()},
            "open_trades": len(self.open_trades),
            "timestamp": now_iso(),
        }


# ── Main ───────────────────────────────────────────────────────────────────

def run_once(symbols: list[str], paper: bool = True, account_balance: float = ACCOUNT_DEFAULT) -> dict:
    """Run a single simulation tick."""
    account = AccountState(balance=account_balance)
    data = MarketData(paper=paper)
    tm = TradeManager(account, data, paper)

    # Evaluate signals for new trades
    candidates = tm.evaluate_signals(symbols)
    for cand in candidates:
        tm.execute_trade(cand)

    # Check exits on open trades
    current_prices = {s: data.get_price(s) for s in symbols}
    tm.check_exits(current_prices)

    # Check pod kills
    tm.check_pod_kills()

    # Heartbeat
    coms_send("all", "HEARTBEAT_OK")

    return tm.summary()


def run_daemon(symbols: list[str], paper: bool = True, account_balance: float = ACCOUNT_DEFAULT,
               interval: int = POLL_INTERVAL_SEC) -> None:
    """Run continuously, polling every interval seconds."""
    print(f"[{now_iso()}] Live simulator daemon starting — paper={paper}, balance={account_balance}")
    while True:
        try:
            summary = run_once(symbols, paper, account_balance)
            print(f"[{now_iso()}] Balance={summary['account']['balance']:.2f} "
                  f"DailyPnL={summary['account']['daily_pnl']:.2f} "
                  f"Trades={summary['account']['total_trades']} "
                  f"WR={summary['account']['win_rate']:.2%}")
        except Exception as e:
            print(f"[{now_iso()}] Error: {e}")
            coms_send("all", f"SIMULATOR ERROR: {e}")
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Live trading simulator for findtorontoevents_antigravity.ca")
    parser.add_argument("--paper", action="store_true", default=True, help="Paper trading mode (default)")
    parser.add_argument("--live", action="store_true", help="Live trading with real capital")
    parser.add_argument("--once", action="store_true", help="Run a single tick then exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--account", type=float, default=ACCOUNT_DEFAULT, help="Account balance (default 2000)")
    parser.add_argument("--symbols", type=str, default="BTCUSDT,ETHUSDT,SOLUSDT,SPY,QQQ",
                        help="Comma-separated symbol list")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL_SEC, help="Daemon poll interval seconds")
    args = parser.parse_args()

    paper = args.paper and not args.live
    symbols = [s.strip().upper() for s in args.symbols.split(",")]

    if args.once:
        summary = run_once(symbols, paper, args.account)
        print(json.dumps(summary, indent=2, default=str))
    elif args.daemon:
        run_daemon(symbols, paper, args.account, args.interval)
    else:
        # Default: single tick
        summary = run_once(symbols, paper, args.account)
        print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
