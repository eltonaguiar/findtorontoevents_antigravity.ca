#!/usr/bin/env python3
"""
Strategy Runner — Connects proven strategies to AsterDEX execution.

Runs on a loop (or single-shot), evaluates market conditions,
generates signals from the best strategies, and routes to executor.

Strategies:
  - whale_confirmed_rsi      (70.6% WR, Sharpe 5.73)
  - atr_regime_rsi            (56.2% WR, Sharpe 3.45)
  - multi_period_rsi_confluence (72.7% WR, Sharpe 10.86)
  - contrarian_predictions    (84.4% inv WR, paper only)

Usage:
    # Paper trading (default)
    python -m trading.strategy_runner --mode paper --balance 1000

    # Single scan (no loop)
    python -m trading.strategy_runner --mode paper --once

    # Live trading (requires API keys in .env)
    python -m trading.strategy_runner --mode live --balance 1000
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from trading.position_manager import PositionManager
from trading.asterdex_executor import AsterDEXExecutor
from trading.proven_strategies import scan_all_strategies


# ── Configuration ──

# Symbols to scan (from playbook research — high activity + good liquidity)
SCAN_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "APTUSDT", "TIAUSDT",
    "DOTUSDT", "ADAUSDT", "AVAXUSDT", "XLMUSDT", "ALGOUSDT",
]

# Scan interval
SCAN_INTERVAL_SEC = 300  # 5 minutes


def _fetch_klines(symbol: str, interval: str = "15m", limit: int = 100) -> List:
    """Fetch klines from Binance (free, no API key)."""
    try:
        url = (
            f"https://api.binance.com/api/v3/klines"
            f"?symbol={symbol}&interval={interval}&limit={limit}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [ERROR] Klines fetch failed for {symbol}: {e}")
        return []


def _load_contrarian_signals() -> List[Dict]:
    """Load contrarian prediction signals if the DB exists."""
    try:
        from trading.contrarian_predictions import ContrarianPredictions
        cp = ContrarianPredictions()
        if cp.db_path.exists():
            return cp.scan()
    except Exception as e:
        print(f"  [WARN] Contrarian predictions unavailable: {e}")
    return []


class StrategyRunner:
    """Scan markets and generate trading signals."""

    def __init__(self, executor: AsterDEXExecutor):
        self.executor = executor
        self.signals_log: List[Dict] = []

    def scan_all(self) -> List[Dict]:
        """Scan all symbols with proven strategies + contrarian predictions."""
        signals = []

        # ── Proven strategies (from Battleground) ──
        for symbol in SCAN_SYMBOLS:
            klines = _fetch_klines(symbol, "15m", 100)
            if not klines:
                continue

            sym_signals = scan_all_strategies(symbol, klines)
            signals.extend(sym_signals)

        # ── Contrarian predictions ──
        contrarian = _load_contrarian_signals()
        signals.extend(contrarian)

        # Sort by confidence descending
        signals.sort(key=lambda s: s["confidence"], reverse=True)
        return signals

    def execute_signals(self, signals: List[Dict], max_new: int = 2) -> List[Dict]:
        """Execute the top signals (respecting position limits)."""
        executed = []

        for sig in signals[:max_new]:
            # Calculate position size (1% of balance)
            balance = self.executor.pm.get_balance()
            risk_usd = balance * 0.01
            quantity = round(risk_usd / sig["entry_price"], 6)

            if quantity <= 0:
                continue

            result = self.executor.place_order(
                symbol=sig["symbol"],
                direction=sig["direction"],
                quantity=quantity,
                entry_price=sig["entry_price"],
                take_profit=sig["take_profit"],
                stop_loss=sig["stop_loss"],
                strategy=sig["strategy"],
            )

            if result:
                executed.append(result)
                self.signals_log.append({
                    **sig,
                    "executed": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            else:
                self.signals_log.append({
                    **sig,
                    "executed": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        return executed

    def run_loop(self, interval: int = SCAN_INTERVAL_SEC):
        """Main trading loop."""
        strategy_names = [
            "whale_confirmed_rsi", "atr_regime_rsi",
            "multi_period_rsi_confluence", "contrarian_predictions",
        ]
        print(f"\n{'='*60}")
        print(f"  STRATEGY RUNNER — {'PAPER' if self.executor.paper_mode else 'LIVE'} MODE")
        print(f"  Scanning {len(SCAN_SYMBOLS)} symbols every {interval}s")
        print(f"  Strategies: {', '.join(strategy_names)}")
        print(f"{'='*60}\n")

        while True:
            try:
                now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
                print(f"\n[{now}] Scanning...")

                # Check TP/SL on open positions
                closed = self.executor.check_tp_sl()
                if closed:
                    for c in closed:
                        print(f"  [AUTO-CLOSE] {c['symbol']} {c['reason']} | PnL: ${c['pnl_usd']:+.2f}")

                # Scan for new signals
                signals = self.scan_all()
                print(f"  Found {len(signals)} signals")

                for sig in signals[:5]:
                    print(
                        f"    {sig['symbol']:12s} {sig['direction']:5s} "
                        f"conf={sig['confidence']:.3f} "
                        f"RSI={sig['indicators'].get('rsi14', '?')} "
                        f"vol={sig['indicators'].get('vol_ratio', '?')}x "
                        f"[{sig['strategy']}]"
                    )

                # Execute top signals
                if signals:
                    executed = self.execute_signals(signals, max_new=2)
                    if executed:
                        print(f"  Executed {len(executed)} orders")

                # Dashboard
                self.executor.pm.print_dashboard()

                # Save signal log
                log_path = Path("trading/data/signals_log.json")
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.write_text(
                    json.dumps(self.signals_log[-100:], indent=2, default=str),
                    encoding="utf-8",
                )

                time.sleep(interval)

            except KeyboardInterrupt:
                print("\n\nStopping strategy runner...")
                self.executor.pm.print_dashboard()
                break
            except Exception as e:
                print(f"  [ERROR] {e}")
                time.sleep(30)

    def run_once(self):
        """Single scan + execute (no loop)."""
        # Check TP/SL first
        closed = self.executor.check_tp_sl()

        # Scan
        signals = self.scan_all()
        print(f"\nFound {len(signals)} signals:")
        for sig in signals:
            print(
                f"  {sig['symbol']:12s} {sig['direction']:5s} "
                f"conf={sig['confidence']:.3f} | "
                f"RSI={sig['indicators'].get('rsi14', '?')} "
                f"vol={sig['indicators'].get('vol_ratio', '?')}x "
                f"[{sig['strategy']}]"
            )

        if signals:
            executed = self.execute_signals(signals, max_new=2)
            print(f"\nExecuted {len(executed)} orders")

        self.executor.pm.print_dashboard()
        return signals


def main():
    parser = argparse.ArgumentParser(description="Strategy Runner for AsterDEX")
    parser.add_argument("--mode", choices=["paper", "live"], default="paper")
    parser.add_argument("--balance", type=float, default=1000.0)
    parser.add_argument("--once", action="store_true", help="Single scan, no loop")
    parser.add_argument("--interval", type=int, default=SCAN_INTERVAL_SEC)
    args = parser.parse_args()

    pm = PositionManager(initial_balance=args.balance)
    executor = AsterDEXExecutor(pm, paper_mode=(args.mode == "paper"))
    runner = StrategyRunner(executor)

    if args.once:
        runner.run_once()
    else:
        runner.run_loop(interval=args.interval)


if __name__ == "__main__":
    main()
