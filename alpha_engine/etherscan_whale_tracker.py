"""
etherscan_whale_tracker.py - Alpha Engine: ETH Whale Wallet Monitor
====================================================================
Tracks known whale/fund wallets on Ethereum via Etherscan free API.
Analyzes ERC-20 token transfers to detect accumulation/distribution patterns.

FREE tier: 5 req/sec, 100K calls/day.
Get API key: https://etherscan.io/register

Strategy:
  - Monitor labeled whale addresses (funds, market makers, individuals)
  - Track net token flow: accumulating = bullish, distributing = bearish
  - Stablecoin accumulation = dry powder (bullish for crypto overall)
  - Consensus: when 2+ whales accumulate the same token = strong signal

Output: alpha_engine/data/etherscan_whale_signals.json

Environment:
  ETHERSCAN_API_KEY or ETHERSCAN_KEY  - API key from https://etherscan.io/
  Falls back to Windows User-level env vars via PowerShell.
"""

from __future__ import annotations

import json
import logging
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# -- Windows UTF-8 fix --
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

logger = logging.getLogger(__name__)


def _get_etherscan_key() -> str:
    """
    Load Etherscan API key from environment variables.
    Checks: ETHERSCAN_API_KEY, ETHERSCAN_KEY (common variants).
    Falls back to Windows User-level env vars via PowerShell if not in shell env.
    """
    key = os.environ.get("ETHERSCAN_API_KEY", "") or os.environ.get("ETHERSCAN_KEY", "")
    if key:
        return key

    # On Windows, try reading from User-level registry if not in shell env
    if sys.platform == "win32":
        try:
            import subprocess
            for name in ("ETHERSCAN_API_KEY", "ETHERSCAN_KEY"):
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     f"[Environment]::GetEnvironmentVariable('{name}', 'User')"],
                    capture_output=True, text=True, timeout=5
                )
                val = result.stdout.strip()
                if val:
                    return val
        except Exception:
            pass

    return ""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / "etherscan_whale_signals.json"

ETHERSCAN_BASE = "https://api.etherscan.io/api"

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# Known whale addresses to monitor
WHALE_WALLETS = {
    "0x176F3DAb24a159341c0509bB36B833E7fdd0a132": "Justin Sun",
    "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045": "Vitalik Buterin",
    "0x0000006daea1723962647b7e189d311d757Fb793": "Wintermute",
    "0x9507c04B10486547584C37bCBd931B2a4FeE9A41": "Jump Trading",
    "0x28C6c06298d514Db089934071355E5743bf21d60": "Binance Hot Wallet",
    "0x71660c4005BA85c37ccec55d0C4493E66Fe775d3": "Coinbase Hot Wallet",
    "0xF977814e90dA44bFA03b6295A0616a897441aceC": "Binance Cold Wallet",
    "0x2FAF487A4414Fe77e2327F0bf4AE2a264a776AD2": "FTX Estate",
    "0x56Eddb7aa87536c09CCc2793473599fD21A8b17F": "Alameda Research",
    "0x1B29DD8ff0eb3240238bf97caFD6edA190c3A3FC": "Cumberland",
}

# Stablecoin contracts
STABLECOINS = {
    "0xdac17f958d2ee523a2206206994597c13d831ec7": "USDT",
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "USDC",
    "0x6b175474e89094c44da98b954eedeac495271d0f": "DAI",
}

# Major token contracts (lowercase for matching)
TOKEN_CONTRACTS = {
    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599": "WBTC",
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "WETH",
    "0x514910771af9ca656af840dff83e8264ecf986ca": "LINK",
    "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984": "UNI",
    "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9": "AAVE",
    "0x6982508145454ce325ddbe47a25d4ec3d2311933": "PEPE",
    "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce": "SHIB",
    "0xb131f4a55907b10d1f0a50d8ab8fa09ec342cd74": "MEME",
    "0x582d872a1b094fc48f5de31d3b73f2d9be47def1": "TON",
}

ALL_KNOWN_TOKENS = {**STABLECOINS, **TOKEN_CONTRACTS}


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

class EtherscanWhaleTracker:
    """Track whale wallet activity on Ethereum via Etherscan API."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or _get_etherscan_key()
        self.rate_limit_delay = 0.25  # 4 req/sec (leave margin from 5/sec limit)
        if not self.api_key:
            logger.warning("No ETHERSCAN_API_KEY/ETHERSCAN_KEY set - scanner will return empty results")

    def _get(self, params: dict) -> dict:
        """Make authenticated GET request to Etherscan API."""
        params["apikey"] = self.api_key
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{ETHERSCAN_BASE}?{qs}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        time.sleep(self.rate_limit_delay)
        try:
            with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
            logger.error(f"Etherscan API error: {e}")
            return {"status": "0", "message": str(e), "result": []}

    def get_token_transfers(self, address: str, limit: int = 100) -> List[dict]:
        """Get recent ERC-20 token transfers for a wallet."""
        if not self.api_key:
            return []
        result = self._get({
            "module": "account",
            "action": "tokentx",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "sort": "desc",
            "page": 1,
            "offset": limit,
        })
        if result.get("status") != "1":
            return []
        return result.get("result", [])

    def get_eth_balance(self, address: str) -> float:
        """Get ETH balance in ETH."""
        if not self.api_key:
            return 0.0
        result = self._get({
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest",
        })
        if result.get("status") != "1":
            return 0.0
        return int(result.get("result", "0")) / 1e18

    def analyze_whale_activity(self, address: str, label: str = "Unknown") -> dict:
        """Analyze recent token movements for a whale address."""
        transfers = self.get_token_transfers(address, limit=50)
        if not transfers:
            return {"address": address, "label": label, "activity": [],
                    "net_flow": {}, "signals": []}

        activity = []
        accumulating: Dict[str, float] = defaultdict(float)
        selling: Dict[str, float] = defaultdict(float)

        addr_lower = address.lower()

        for tx in transfers:
            token_addr = tx.get("contractAddress", "").lower()
            token_name = ALL_KNOWN_TOKENS.get(
                token_addr, tx.get("tokenSymbol", "UNKNOWN")
            )
            decimals = int(tx.get("tokenDecimal", 18) or 18)
            raw_value = int(tx.get("value", 0) or 0)
            if decimals > 0:
                amount = raw_value / (10 ** decimals)
            else:
                amount = float(raw_value)
            ts = int(tx.get("timeStamp", 0) or 0)

            is_incoming = tx.get("to", "").lower() == addr_lower
            direction = "received" if is_incoming else "sent"

            if is_incoming:
                accumulating[token_name] += amount
            else:
                selling[token_name] += amount

            activity.append({
                "token": token_name,
                "direction": direction,
                "amount": amount,
                "timestamp": ts,
                "datetime": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else "",
                "tx_hash": tx.get("hash", ""),
            })

        # Net flow per token
        net_flow = {}
        all_tokens = set(list(accumulating.keys()) + list(selling.keys()))
        for token in all_tokens:
            bought = accumulating.get(token, 0)
            sold = selling.get(token, 0)
            net = bought - sold
            if abs(net) > 0:
                net_flow[token] = {
                    "net_amount": net,
                    "direction": "accumulating" if net > 0 else "distributing",
                    "bought": bought,
                    "sold": sold,
                }

        signals = self._derive_signals(net_flow, label)

        return {
            "address": address,
            "label": label,
            "recent_transfers": len(activity),
            "net_flow": net_flow,
            "signals": signals,
            "activity": activity[:10],
        }

    def _derive_signals(self, net_flow: dict, label: str) -> List[dict]:
        """Derive trading signals from whale net flow."""
        signals = []
        for token, data in net_flow.items():
            if token in ("USDT", "USDC", "DAI", "BUSD"):
                if data["direction"] == "accumulating" and data["net_amount"] > 100_000:
                    signals.append({
                        "type": "stablecoin_accumulation",
                        "signal": "bullish_overall",
                        "token": token,
                        "strength": min(80, int(data["net_amount"] / 500_000 * 50)),
                        "reason": f"{label} accumulated {data['net_amount']:,.0f} {token} - building dry powder",
                    })
            else:
                if data["direction"] == "accumulating":
                    signals.append({
                        "type": "token_accumulation",
                        "signal": "bullish",
                        "token": token,
                        "strength": 60,
                        "reason": f"{label} net bought {data['net_amount']:,.2f} {token}",
                    })
                elif data["direction"] == "distributing":
                    signals.append({
                        "type": "token_distribution",
                        "signal": "bearish",
                        "token": token,
                        "strength": 55,
                        "reason": f"{label} net sold {abs(data['net_amount']):,.2f} {token}",
                    })
        return signals

    def scan_all_whales(self) -> dict:
        """Scan all known whale wallets and aggregate signals."""
        all_signals = []
        whale_reports = []

        for address, label in WHALE_WALLETS.items():
            logger.info(f"Scanning {label} ({address[:10]}...)...")
            report = self.analyze_whale_activity(address, label)
            whale_reports.append(report)
            all_signals.extend(report.get("signals", []))
            time.sleep(0.5)  # Extra politeness between whales

        # Aggregate signals by token
        token_consensus: Dict[str, dict] = defaultdict(
            lambda: {"bullish": 0, "bearish": 0, "entities": [], "reasons": []}
        )
        for sig in all_signals:
            token = sig.get("token", "OVERALL")
            is_bull = "bullish" in sig["signal"]
            direction_key = "bullish" if is_bull else "bearish"
            token_consensus[token][direction_key] += 1
            token_consensus[token]["entities"].append(sig.get("reason", "").split(" ")[0])
            token_consensus[token]["reasons"].append(sig["reason"])

        # Find consensus (2+ whales same direction)
        consensus_picks = {}
        for token, data in token_consensus.items():
            if data["bullish"] >= 2:
                consensus_picks[token] = {
                    "token": token,
                    "signal": "strong_buy",
                    "count": data["bullish"],
                    "reason": f"{data['bullish']} whales accumulating {token}",
                }
            elif data["bearish"] >= 2:
                consensus_picks[token] = {
                    "token": token,
                    "signal": "strong_sell",
                    "count": data["bearish"],
                    "reason": f"{data['bearish']} whales distributing {token}",
                }

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "etherscan_whales",
            "whales_scanned": len(WHALE_WALLETS),
            "total_signals": len(all_signals),
            "token_consensus": dict(token_consensus),
            "consensus_picks": consensus_picks,
            "whale_reports": whale_reports,
        }

    def run(self) -> dict:
        """Run full scan and save results."""
        logger.info("Running Etherscan whale scan...")
        result = self.scan_all_whales()

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"Etherscan whale signals saved to {OUTPUT_FILE}")

        return result


# ---------------------------------------------------------------------------
# Integration helper for Alpha Engine
# ---------------------------------------------------------------------------

def get_whale_wallet_signal(symbol: str = "ETH") -> Optional[Dict]:
    """
    Get whale wallet signal for a specific token.
    Returns dict with 'direction' and 'strength' or None.
    """
    try:
        if OUTPUT_FILE.exists():
            with open(OUTPUT_FILE) as f:
                data = json.load(f)
            consensus = data.get("token_consensus", {})
            sym = symbol.upper().replace("USDT", "").replace("-USD", "").replace("USD", "")
            # Try direct match and common variations
            for try_sym in [sym, f"W{sym}", sym.replace("W", "")]:
                if try_sym in consensus:
                    c = consensus[try_sym]
                    bull = c.get("bullish", 0)
                    bear = c.get("bearish", 0)
                    if bull + bear == 0:
                        continue
                    return {
                        "direction": "bullish" if bull > bear else (
                            "bearish" if bear > bull else "neutral"),
                        "strength": abs(bull - bear) / (bull + bear),
                        "bullish_whales": bull,
                        "bearish_whales": bear,
                    }
    except Exception as e:
        logger.debug(f"Whale wallet signal lookup failed: {e}")
    return None


# ---------------------------------------------------------------------------
# Standalone
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    tracker = EtherscanWhaleTracker()
    if not tracker.api_key:
        print("Set ETHERSCAN_API_KEY or ETHERSCAN_KEY env var. Get free key at https://etherscan.io/register")
        exit(1)

    print("Scanning whale wallets...")
    result = tracker.run()

    print(f"\n{'='*60}")
    print(f"ETH WHALE SIGNALS - {result['whales_scanned']} wallets scanned")
    print(f"{'='*60}")

    for token, data in result.get("token_consensus", {}).items():
        bull = data.get("bullish", 0)
        bear = data.get("bearish", 0)
        if bull + bear == 0:
            continue
        tag = "BULL" if bull > bear else ("BEAR" if bear > bull else "----")
        print(f"\n[{tag}] {token}: {bull} bullish / {bear} bearish")
        for r in data.get("reasons", [])[:3]:
            print(f"  -> {r}")

    if result.get("consensus_picks"):
        print(f"\n{'='*60}")
        print("CONSENSUS PICKS (2+ whales same direction):")
        for token, pick in result["consensus_picks"].items():
            print(f"  [{pick['signal'].upper()}] {token} - {pick['reason']}")
