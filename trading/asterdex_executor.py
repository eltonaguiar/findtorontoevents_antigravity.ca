#!/usr/bin/env python3
"""
AsterDEX Executor — Live order execution via aster-connector-python SDK.

This module handles all interaction with AsterDEX:
- Place limit/market orders with TP/SL
- Monitor open orders
- Cancel orders
- Check balances

SAFETY: All orders go through PositionManager risk checks first.
SETUP:  pip install aster-connector-python
        Set ASTERDEX_API_KEY and ASTERDEX_API_SECRET in .env
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from trading.position_manager import PositionManager


# Fee rates (AsterDEX Pro Mode perps)
MAKER_FEE = 0.0001   # 0.01%
TAKER_FEE = 0.00035  # 0.035%


def _load_env():
    """Load .env file if it exists."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())


class AsterDEXExecutor:
    """Execute trades on AsterDEX via their Python SDK."""

    def __init__(self, position_manager: PositionManager, paper_mode: bool = True):
        self.pm = position_manager
        self.paper_mode = paper_mode
        self.client = None

        if not paper_mode:
            self._init_client()

    def _init_client(self):
        """Initialize the AsterDEX REST client."""
        _load_env()
        api_key = os.environ.get("ASTERDEX_API_KEY", "")
        api_secret = os.environ.get("ASTERDEX_API_SECRET", "")

        if not api_key or not api_secret:
            raise ValueError(
                "ASTERDEX_API_KEY and ASTERDEX_API_SECRET must be set in .env or environment"
            )

        try:
            from aster.rest_api import Client
            self.client = Client(key=api_key, secret=api_secret)
            # Test connectivity
            self.client.ping()
            print("[AsterDEX] Connected successfully")
        except ImportError:
            raise ImportError(
                "aster-connector-python not installed. Run: pip install aster-connector-python"
            )
        except Exception as e:
            raise ConnectionError(f"AsterDEX connection failed: {e}")

    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        if self.paper_mode:
            return self._get_binance_price(symbol)

        try:
            result = self.client.ticker_price(symbol=symbol)
            return float(result["price"])
        except Exception as e:
            print(f"[AsterDEX] Price fetch failed for {symbol}: {e}")
            # Fallback to Binance for price data
            return self._get_binance_price(symbol)

    def _get_binance_price(self, symbol: str) -> Optional[float]:
        """Fallback price from Binance (free, no API key)."""
        try:
            import urllib.request
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                return float(data["price"])
        except Exception:
            return None

    def place_order(
        self,
        symbol: str,
        direction: str,
        quantity: float,
        entry_price: Optional[float] = None,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
        strategy: str = "manual",
        order_type: str = "MARKET",
    ) -> Optional[Dict]:
        """
        Place an order on AsterDEX with TP/SL.

        Returns order details dict or None if blocked by risk checks.
        """
        # Get current price if not specified
        if entry_price is None:
            entry_price = self.get_price(symbol)
            if entry_price is None:
                print(f"[ERROR] Cannot get price for {symbol}")
                return None

        notional = entry_price * quantity
        fees = notional * TAKER_FEE

        # Risk check via position manager
        allowed, reason = self.pm.can_open_position(symbol, direction, notional)
        if not allowed:
            print(f"[BLOCKED] {symbol} {direction}: {reason}")
            return None

        # Default TP/SL if not provided (2% TP, 1% SL)
        if take_profit is None:
            if direction == "LONG":
                take_profit = round(entry_price * 1.02, 8)
            else:
                take_profit = round(entry_price * 0.98, 8)

        if stop_loss is None:
            if direction == "LONG":
                stop_loss = round(entry_price * 0.99, 8)
            else:
                stop_loss = round(entry_price * 1.01, 8)

        if self.paper_mode:
            return self._paper_order(
                symbol, direction, quantity, entry_price,
                take_profit, stop_loss, strategy, fees
            )
        else:
            return self._live_order(
                symbol, direction, quantity, entry_price,
                take_profit, stop_loss, strategy, order_type, fees
            )

    def _paper_order(
        self, symbol, direction, quantity, entry_price,
        take_profit, stop_loss, strategy, fees
    ) -> Dict:
        """Simulate order execution locally."""
        pos = self.pm.open_position(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            quantity=quantity,
            take_profit=take_profit,
            stop_loss=stop_loss,
            strategy=strategy,
            fees=fees,
        )
        if pos is None:
            return None

        return {
            "order_id": f"PAPER_{pos.id}",
            "position_id": pos.id,
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "quantity": quantity,
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "fees": fees,
            "mode": "PAPER",
            "status": "FILLED",
        }

    def _live_order(
        self, symbol, direction, quantity, entry_price,
        take_profit, stop_loss, strategy, order_type, fees
    ) -> Optional[Dict]:
        """Execute real order on AsterDEX."""
        if not self.client:
            print("[ERROR] AsterDEX client not initialized")
            return None

        side = "BUY" if direction == "LONG" else "SELL"

        try:
            # Main entry order
            if order_type == "MARKET":
                order = self.client.new_order(
                    symbol=symbol,
                    side=side,
                    type="MARKET",
                    quantity=quantity,
                )
            else:
                order = self.client.new_order(
                    symbol=symbol,
                    side=side,
                    type="LIMIT",
                    timeInForce="GTC",
                    quantity=quantity,
                    price=entry_price,
                )

            actual_price = float(order.get("avgPrice", entry_price))

            # Place TP order
            tp_side = "SELL" if direction == "LONG" else "BUY"
            self.client.new_order(
                symbol=symbol,
                side=tp_side,
                type="TAKE_PROFIT_MARKET",
                stopPrice=take_profit,
                quantity=quantity,
                closePosition="true",
            )

            # Place SL order
            self.client.new_order(
                symbol=symbol,
                side=tp_side,
                type="STOP_MARKET",
                stopPrice=stop_loss,
                quantity=quantity,
                closePosition="true",
            )

            # Record in position manager
            pos = self.pm.open_position(
                symbol=symbol,
                direction=direction,
                entry_price=actual_price,
                quantity=quantity,
                take_profit=take_profit,
                stop_loss=stop_loss,
                strategy=strategy,
                fees=fees,
            )

            return {
                "order_id": order.get("orderId"),
                "position_id": pos.id if pos else None,
                "symbol": symbol,
                "direction": direction,
                "entry_price": actual_price,
                "quantity": quantity,
                "take_profit": take_profit,
                "stop_loss": stop_loss,
                "fees": fees,
                "mode": "LIVE",
                "status": order.get("status", "UNKNOWN"),
            }

        except Exception as e:
            print(f"[ERROR] AsterDEX order failed: {e}")
            return None

    def check_tp_sl(self) -> List[Dict]:
        """Check open positions against current prices for TP/SL hits (paper mode)."""
        if not self.paper_mode:
            return []  # AsterDEX handles TP/SL natively in live mode

        closed = []
        for pos in self.pm.get_open_positions():
            price = self.get_price(pos.symbol)
            if price is None:
                continue

            hit = None
            if pos.direction == "LONG":
                if price >= pos.take_profit:
                    hit = ("TP_HIT", pos.take_profit)
                elif price <= pos.stop_loss:
                    hit = ("SL_HIT", pos.stop_loss)
            else:  # SHORT
                if price <= pos.take_profit:
                    hit = ("TP_HIT", pos.take_profit)
                elif price >= pos.stop_loss:
                    hit = ("SL_HIT", pos.stop_loss)

            if hit:
                reason, exit_price = hit
                fees = pos.notional_usd * TAKER_FEE
                result = self.pm.close_position(pos.id, exit_price, reason, fees)
                if result:
                    closed.append({
                        "position_id": pos.id,
                        "symbol": pos.symbol,
                        "reason": reason,
                        "exit_price": exit_price,
                        "pnl_usd": result.pnl_usd,
                        "pnl_pct": result.pnl_pct,
                    })

        return closed

    def get_account_info(self) -> Dict:
        """Get account balance and position info."""
        if self.paper_mode:
            stats = self.pm.get_stats()
            return {
                "mode": "PAPER",
                "balance": stats.get("current_balance", 0),
                "total_pnl": stats.get("total_pnl_usd", 0),
                "open_positions": stats.get("open_positions", 0),
                "win_rate": stats.get("win_rate", 0),
            }

        try:
            account = self.client.account()
            return {
                "mode": "LIVE",
                "balance": float(account.get("totalWalletBalance", 0)),
                "unrealized_pnl": float(account.get("totalUnrealizedProfit", 0)),
                "margin_balance": float(account.get("totalMarginBalance", 0)),
                "available_balance": float(account.get("availableBalance", 0)),
            }
        except Exception as e:
            return {"mode": "LIVE", "error": str(e)}


if __name__ == "__main__":
    # Demo: paper trading mode
    pm = PositionManager(initial_balance=1000.0)
    executor = AsterDEXExecutor(pm, paper_mode=True)

    print("AsterDEX Executor — Paper Mode")
    print(f"BTC price: ${executor.get_price('BTCUSDT'):,.2f}")

    info = executor.get_account_info()
    print(f"Account: {json.dumps(info, indent=2)}")
