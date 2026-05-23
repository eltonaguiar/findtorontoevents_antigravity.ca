"""
whale_alert_scanner.py - Alpha Engine: Whale Transfer Signal Scanner
=====================================================================
Tracks large crypto transfers (>$1M) via Whale Alert free API.
Derives bullish/bearish signals from exchange flow patterns.

FREE tier: 10 req/min, last 1 hour of transactions, no credit card.
Get API key: https://whale-alert.io/signup

Signal logic:
  Exchange -> Unknown (BTC/ETH)  = Bullish (accumulation / cold storage)
  Unknown -> Exchange (BTC/ETH)  = Bearish (deposit to sell)
  Mint (USDT/USDC)               = Bullish (fresh buying power)
  Burn (USDT/USDC)               = Bearish (capital leaving crypto)

Output: alpha_engine/data/whale_signals.json

Environment:
  WHALE_ALERT_API_KEY  - API key from https://whale-alert.io/
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / "whale_signals.json"

WHALE_ALERT_BASE = "https://api.whale-alert.io/v1"
MIN_VALUE_USD = 1_000_000  # $1M+ transfers only

# SSL context for Windows compatibility
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

class WhaleAlertScanner:
    """Scan Whale Alert API for large crypto transfers and derive signals."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("WHALE_ALERT_API_KEY", "")
        if not self.api_key:
            logger.warning("No WHALE_ALERT_API_KEY set - scanner will return empty results")

    def _get(self, endpoint: str, params: dict) -> dict:
        """Make authenticated GET request to Whale Alert API."""
        params["api_key"] = self.api_key
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{WHALE_ALERT_BASE}/{endpoint}?{qs}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
            logger.error(f"Whale Alert API error: {e}")
            return {"result": "error", "message": str(e)}

    def get_recent_whales(self, min_value: int = MIN_VALUE_USD,
                          lookback_seconds: int = 3600) -> List[dict]:
        """Fetch whale transactions from the last hour (free tier limit)."""
        if not self.api_key:
            return []
        start = int(time.time()) - lookback_seconds
        result = self._get("transactions", {
            "min_value": min_value,
            "start": start,
        })
        if result.get("result") != "success":
            logger.warning(f"Whale Alert returned: {result.get('message', 'unknown error')}")
            return []
        return result.get("transactions", [])

    def classify_signal(self, tx: dict) -> dict:
        """Classify a single whale transaction into a trading signal."""
        from_type = tx.get("from", {}).get("owner_type", "unknown")
        to_type = tx.get("to", {}).get("owner_type", "unknown")
        from_owner = tx.get("from", {}).get("owner", "unknown").lower()
        to_owner = tx.get("to", {}).get("owner", "unknown").lower()
        symbol = tx.get("symbol", "").upper()
        amount_usd = tx.get("amount_usd", 0)
        tx_type = tx.get("transaction_type", "transfer")

        signal = "neutral"
        reason = ""
        strength = 0  # 0-100

        # Stablecoin minting = new capital entering crypto
        if tx_type == "mint" and symbol in ("USDT", "USDC", "DAI", "BUSD"):
            signal = "bullish"
            reason = f"${amount_usd/1e6:.1f}M {symbol} minted - fresh buying power"
            strength = min(80, int(amount_usd / 5e6))

        # Stablecoin burning = capital leaving
        elif tx_type == "burn" and symbol in ("USDT", "USDC", "DAI", "BUSD"):
            signal = "bearish"
            reason = f"${amount_usd/1e6:.1f}M {symbol} burned - capital redeemed"
            strength = min(70, int(amount_usd / 5e6))

        # Exchange -> Unknown = withdrawal to cold storage (accumulation)
        elif from_type == "exchange" and to_type == "unknown":
            signal = "bullish"
            reason = f"${amount_usd/1e6:.1f}M {symbol} withdrawn from {from_owner} - accumulation"
            strength = min(70, int(amount_usd / 2e6))

        # Unknown -> Exchange = deposit to sell
        elif from_type == "unknown" and to_type == "exchange":
            signal = "bearish"
            reason = f"${amount_usd/1e6:.1f}M {symbol} deposited to {to_owner} - potential sell"
            strength = min(70, int(amount_usd / 2e6))

        # Exchange -> Exchange = rebalancing
        elif from_type == "exchange" and to_type == "exchange":
            signal = "neutral"
            reason = f"${amount_usd/1e6:.1f}M {symbol} moved {from_owner} -> {to_owner}"
            strength = 20

        else:
            reason = f"${amount_usd/1e6:.1f}M {symbol} transfer ({from_owner} -> {to_owner})"
            strength = 10

        return {
            "symbol": symbol,
            "signal": signal,
            "reason": reason,
            "strength": strength,
            "amount_usd": amount_usd,
            "from": from_owner,
            "to": to_owner,
            "timestamp": tx.get("timestamp", 0),
            "tx_hash": tx.get("hash", ""),
            "blockchain": tx.get("blockchain", ""),
        }

    def get_aggregate_signals(self, min_value: int = MIN_VALUE_USD) -> Dict[str, Any]:
        """Aggregate whale movements into per-symbol trading signals."""
        txns = self.get_recent_whales(min_value)
        if not txns:
            return {}

        classified = [self.classify_signal(tx) for tx in txns]

        # Aggregate by symbol
        by_symbol: Dict[str, dict] = defaultdict(
            lambda: {"bullish": 0, "bearish": 0, "neutral": 0,
                     "total_usd": 0, "signals": []}
        )
        for sig in classified:
            sym = sig["symbol"]
            by_symbol[sym][sig["signal"]] += 1
            by_symbol[sym]["total_usd"] += sig["amount_usd"]
            by_symbol[sym]["signals"].append(sig)

        # Calculate net sentiment per symbol
        results = {}
        for sym, data in by_symbol.items():
            bull = data["bullish"]
            bear = data["bearish"]
            total = bull + bear + data["neutral"]
            if total == 0:
                continue
            net_score = (bull - bear) / total  # -1 to +1
            results[sym] = {
                "symbol": sym,
                "net_score": round(net_score, 3),
                "direction": "bullish" if net_score > 0.2 else (
                    "bearish" if net_score < -0.2 else "neutral"),
                "bullish_count": bull,
                "bearish_count": bear,
                "total_volume_usd": data["total_usd"],
                "transaction_count": total,
                "top_signals": sorted(
                    data["signals"], key=lambda x: x["amount_usd"], reverse=True
                )[:5],
            }

        return dict(sorted(
            results.items(), key=lambda x: x[1]["total_volume_usd"], reverse=True
        ))

    def run(self) -> Dict[str, Any]:
        """Run full scan and save results."""
        logger.info("Running Whale Alert scan...")
        signals = self.get_aggregate_signals()

        output = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "whale_alert",
            "min_value_usd": MIN_VALUE_USD,
            "symbols_detected": len(signals),
            "signals": signals,
        }

        # Save to disk
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(output, f, indent=2, default=str)
        logger.info(f"Whale signals saved to {OUTPUT_FILE} ({len(signals)} symbols)")

        return output


# ---------------------------------------------------------------------------
# Integration helper for Alpha Engine scanner.py
# ---------------------------------------------------------------------------

def get_whale_signal(symbol: str = "BTC") -> Optional[Dict]:
    """
    Get whale flow signal for a specific symbol.
    Returns dict with 'direction' and 'strength' or None.
    Called by Alpha Engine strategies.
    """
    try:
        if OUTPUT_FILE.exists():
            with open(OUTPUT_FILE) as f:
                data = json.load(f)
            signals = data.get("signals", {})
            # Normalize symbol lookup (BTC -> BTC, BTCUSDT -> BTC)
            sym = symbol.upper().replace("USDT", "").replace("-USD", "").replace("USD", "")
            if sym in signals:
                return {
                    "direction": signals[sym]["direction"],
                    "strength": signals[sym].get("net_score", 0),
                    "volume_usd": signals[sym].get("total_volume_usd", 0),
                    "bullish": signals[sym].get("bullish_count", 0),
                    "bearish": signals[sym].get("bearish_count", 0),
                }
    except Exception as e:
        logger.debug(f"Whale signal lookup failed: {e}")
    return None


# ---------------------------------------------------------------------------
# Standalone
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scanner = WhaleAlertScanner()
    if not scanner.api_key:
        print("Set WHALE_ALERT_API_KEY env var. Get free key at https://whale-alert.io/signup")
        exit(1)

    result = scanner.run()
    signals = result.get("signals", {})

    print(f"\n{'='*60}")
    print(f"WHALE ALERT SIGNALS - Last 1 Hour (>${MIN_VALUE_USD/1e6:.0f}M)")
    print(f"{'='*60}")

    for sym, data in signals.items():
        tag = {"bullish": "BULL", "bearish": "BEAR", "neutral": "----"}[data["direction"]]
        print(f"\n[{tag}] {sym}: net={data['net_score']:+.2f} | "
              f"bull={data['bullish_count']} bear={data['bearish_count']} | "
              f"vol=${data['total_volume_usd']/1e6:.1f}M")
        for sig in data["top_signals"][:3]:
            print(f"  -> {sig['reason']}")
