"""
arkham_smart_money.py - Alpha Engine: Smart Money Tracker via Arkham Intelligence
==================================================================================
Tracks labeled smart money entities (VC funds, market makers, whales) via
Arkham Intelligence API. Identifies accumulation/distribution patterns and
consensus picks when multiple entities buy the same token.

FREE tier: 10 req/min, basic entity data, transfer alerts.
Sign up: https://platform.arkhamintelligence.com/

Strategy:
  - Search for known smart money entities (Paradigm, a16z, Jump, etc.)
  - Analyze their recent transfers for accumulation vs distribution
  - Find consensus: 2+ entities accumulating same token = strong signal
  - Track portfolio compositions for position sizing hints

Output: alpha_engine/data/arkham_smart_money.json

Environment:
  ARKHAM_API_KEY  - API key from Arkham Intelligence
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
OUTPUT_FILE = DATA_DIR / "arkham_smart_money.json"

ARKHAM_BASE = "https://api.arkhamintelligence.com/intelligence"

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# Smart money entities to track
SMART_MONEY_ENTITIES = [
    "paradigm",
    "a16z",
    "jump-trading",
    "wintermute",
    "galaxy-digital",
    "pantera-capital",
    "dragonfly-capital",
    "polychain-capital",
    "multicoin-capital",
    "delphi-digital",
    "framework-ventures",
    "coinbase-ventures",
]

# Notable individual whale addresses (Ethereum)
WHALE_ADDRESSES = {
    "0x176F3DAb24a159341c0509bB36B833E7fdd0a132": "Justin Sun",
    "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045": "Vitalik Buterin",
    "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B": "Vitalik (old)",
}


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

class ArkhamScanner:
    """Track labeled smart money via Arkham Intelligence API."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("ARKHAM_API_KEY", "")
        self.rate_limit_delay = 6.5  # ~10 req/min = 1 every 6s
        if not self.api_key:
            logger.warning("No ARKHAM_API_KEY set - scanner will return empty results")

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        """Make authenticated GET request to Arkham API."""
        url = f"{ARKHAM_BASE}/{path}"
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{qs}"
        req = urllib.request.Request(url, headers={
            "API-Key": self.api_key,
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        })
        time.sleep(self.rate_limit_delay)
        try:
            with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode()[:200]
            except Exception:
                pass
            logger.error(f"Arkham API HTTP {e.code}: {body}")
            return {"error": str(e), "status": e.code}
        except Exception as e:
            logger.error(f"Arkham API error: {e}")
            return {"error": str(e)}

    def search_entity(self, query: str) -> dict:
        """Search for a labeled entity by name."""
        if not self.api_key:
            return {"error": "No API key"}
        return self._get("entity/search", {"query": query})

    def get_portfolio(self, address: str) -> dict:
        """Get current portfolio holdings for an address."""
        if not self.api_key:
            return {"error": "No API key"}
        return self._get(f"address/{address}/portfolio")

    def get_transfers(self, address: str, limit: int = 50) -> List[dict]:
        """Get recent transfers for an address."""
        if not self.api_key:
            return []
        result = self._get("transfers", {"address": address, "limit": limit})
        if isinstance(result, list):
            return result
        return result.get("transfers", result.get("data", []))

    def analyze_entity(self, entity_name: str) -> dict:
        """Full analysis of a smart money entity."""
        # Step 1: Find entity and get addresses
        search = self.search_entity(entity_name)
        if not search or "error" in search:
            return {
                "entity": entity_name,
                "error": f"Entity not found or API error: {search.get('error', 'unknown')}",
                "signals": [],
            }

        # Extract primary address from search results
        entities = search if isinstance(search, list) else search.get("entities", [search])
        if not entities:
            return {"entity": entity_name, "error": "No results", "signals": []}

        entity = entities[0] if isinstance(entities, list) else entities
        label = entity.get("name", entity_name)

        # Try to get address from various response formats
        address = ""
        if "address" in entity:
            address = entity["address"]
        elif "addresses" in entity and entity["addresses"]:
            addr_list = entity["addresses"]
            if isinstance(addr_list, list) and addr_list:
                addr_item = addr_list[0]
                address = addr_item.get("address", "") if isinstance(addr_item, dict) else str(addr_item)

        if not address:
            return {
                "entity": entity_name,
                "label": label,
                "error": "No address found in entity data",
                "raw_entity_keys": list(entity.keys()) if isinstance(entity, dict) else [],
                "signals": [],
            }

        # Step 2: Get portfolio (if available)
        portfolio = self.get_portfolio(address)

        # Step 3: Get recent transfers
        transfers = self.get_transfers(address, limit=20)

        # Step 4: Derive signals
        signals = self._derive_signals(portfolio, transfers, label)

        return {
            "entity": entity_name,
            "label": label,
            "address": address,
            "portfolio_summary": self._summarize_portfolio(portfolio),
            "recent_transfer_count": len(transfers) if isinstance(transfers, list) else 0,
            "signals": signals,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
        }

    def _summarize_portfolio(self, portfolio: dict) -> dict:
        """Summarize portfolio into top holdings."""
        if not isinstance(portfolio, dict):
            return {}
        tokens = portfolio.get("tokens", [])
        if not tokens:
            return {"total_value": portfolio.get("totalValue", 0)}

        top = sorted(tokens, key=lambda x: float(x.get("value", 0)), reverse=True)[:10]
        return {
            "total_value": portfolio.get("totalValue", 0),
            "top_holdings": [
                {"symbol": t.get("symbol", "?"), "value_usd": float(t.get("value", 0))}
                for t in top
            ],
        }

    def _derive_signals(self, portfolio: dict, transfers, label: str) -> List[dict]:
        """Derive trading signals from portfolio and transfers."""
        signals = []

        # Analyze transfers for accumulation/distribution
        if isinstance(transfers, list):
            token_flow: Dict[str, float] = defaultdict(float)
            for tx in transfers:
                # Handle different Arkham response formats
                token = (
                    tx.get("tokenSymbol")
                    or tx.get("token", {}).get("symbol", "")
                    or "ETH"
                )
                # Try to determine direction
                to_entity = ""
                from_entity = ""
                if isinstance(tx.get("toAddress"), dict):
                    to_entity = tx["toAddress"].get("arkhamEntity", {}).get("name", "")
                if isinstance(tx.get("fromAddress"), dict):
                    from_entity = tx["fromAddress"].get("arkhamEntity", {}).get("name", "")

                amount_usd = 0
                try:
                    unit_price = float(tx.get("unitPrice", 0) or 0)
                    value = float(tx.get("value", 0) or 0)
                    amount_usd = unit_price * value
                except (ValueError, TypeError):
                    pass

                if label.lower() in to_entity.lower():
                    token_flow[token] += amount_usd
                elif label.lower() in from_entity.lower():
                    token_flow[token] -= amount_usd

            for token, net_usd in token_flow.items():
                if abs(net_usd) > 50_000:  # Only significant movements
                    direction = "accumulating" if net_usd > 0 else "distributing"
                    signals.append({
                        "entity": label,
                        "token": token,
                        "direction": direction,
                        "signal": "bullish" if direction == "accumulating" else "bearish",
                        "net_usd": net_usd,
                        "reason": f"{label} {direction} {token} (net ${abs(net_usd):,.0f})",
                    })

        # Portfolio-level signals
        if isinstance(portfolio, dict) and "tokens" in portfolio:
            top_holdings = sorted(
                portfolio["tokens"],
                key=lambda x: float(x.get("value", 0)),
                reverse=True
            )[:5]
            for h in top_holdings:
                val = float(h.get("value", 0))
                if val > 100_000:
                    signals.append({
                        "entity": label,
                        "token": h.get("symbol", "?"),
                        "direction": "holding",
                        "signal": "watch",
                        "value_usd": val,
                        "reason": f"{label} holds ${val:,.0f} in {h.get('symbol', '?')}",
                    })

        return signals

    def analyze_whale_address(self, address: str, label: str) -> dict:
        """Analyze a specific whale address (not entity search)."""
        portfolio = self.get_portfolio(address)
        transfers = self.get_transfers(address, limit=20)
        signals = self._derive_signals(portfolio, transfers, label)

        return {
            "entity": label,
            "address": address,
            "portfolio_summary": self._summarize_portfolio(portfolio),
            "signals": signals,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
        }

    def scan_all_smart_money(self) -> dict:
        """Scan all tracked smart money entities and whale addresses."""
        reports = []
        all_signals = []

        # Scan named entities
        for entity in SMART_MONEY_ENTITIES:
            logger.info(f"Scanning entity: {entity}...")
            report = self.analyze_entity(entity)
            reports.append(report)
            all_signals.extend(report.get("signals", []))

        # Scan known whale addresses
        for address, label in WHALE_ADDRESSES.items():
            logger.info(f"Scanning whale: {label}...")
            report = self.analyze_whale_address(address, label)
            reports.append(report)
            all_signals.extend(report.get("signals", []))

        # Consensus: which tokens are multiple entities accumulating?
        token_consensus: Dict[str, dict] = defaultdict(
            lambda: {"accumulating": [], "distributing": [], "holding": []}
        )
        for sig in all_signals:
            token = sig.get("token", "?")
            direction = sig.get("direction", "unknown")
            entity = sig.get("entity", "?")
            if direction in token_consensus[token]:
                token_consensus[token][direction].append(entity)

        # Find consensus picks (2+ entities accumulating same token)
        consensus_picks = {}
        for token, data in token_consensus.items():
            acc_entities = list(set(data["accumulating"]))  # Deduplicate
            acc_count = len(acc_entities)
            if acc_count >= 2:
                consensus_picks[token] = {
                    "token": token,
                    "signal": "strong_buy" if acc_count >= 3 else "buy",
                    "accumulating_entities": acc_entities,
                    "count": acc_count,
                    "reason": (
                        f"{acc_count} smart money entities accumulating {token}: "
                        f"{', '.join(acc_entities)}"
                    ),
                }

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "arkham_intelligence",
            "entities_scanned": len(SMART_MONEY_ENTITIES) + len(WHALE_ADDRESSES),
            "total_signals": len(all_signals),
            "consensus_picks": consensus_picks,
            "token_consensus": {
                k: {
                    "accumulating": v["accumulating"],
                    "distributing": v["distributing"],
                    "holding_count": len(v["holding"]),
                }
                for k, v in token_consensus.items()
            },
            "entity_reports": reports,
        }

    def run(self) -> dict:
        """Run full scan and save results."""
        logger.info("Running Arkham smart money scan...")
        result = self.scan_all_smart_money()

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"Arkham smart money data saved to {OUTPUT_FILE}")

        return result


# ---------------------------------------------------------------------------
# Integration helper for Alpha Engine
# ---------------------------------------------------------------------------

def get_smart_money_signal(symbol: str = "ETH") -> Optional[Dict]:
    """
    Get smart money consensus signal for a specific token.
    Returns dict with 'direction', 'strength', 'entities' or None.
    """
    try:
        if OUTPUT_FILE.exists():
            with open(OUTPUT_FILE) as f:
                data = json.load(f)

            # Check consensus picks first
            picks = data.get("consensus_picks", {})
            sym = symbol.upper().replace("USDT", "").replace("-USD", "").replace("USD", "")
            if sym in picks:
                pick = picks[sym]
                return {
                    "direction": "bullish",
                    "strength": min(90, pick["count"] * 30),
                    "entities": pick.get("accumulating_entities", []),
                    "reason": pick["reason"],
                }

            # Check token consensus
            consensus = data.get("token_consensus", {})
            if sym in consensus:
                c = consensus[sym]
                acc = len(c.get("accumulating", []))
                dist = len(c.get("distributing", []))
                if acc + dist > 0:
                    return {
                        "direction": "bullish" if acc > dist else (
                            "bearish" if dist > acc else "neutral"),
                        "strength": abs(acc - dist) / (acc + dist) * 70,
                        "accumulating": acc,
                        "distributing": dist,
                    }
    except Exception as e:
        logger.debug(f"Smart money signal lookup failed: {e}")
    return None


# ---------------------------------------------------------------------------
# Standalone
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    scanner = ArkhamScanner()
    if not scanner.api_key:
        print("Set ARKHAM_API_KEY env var.")
        print("Sign up free: https://platform.arkhamintelligence.com/")
        exit(1)

    print("Scanning smart money entities...")
    result = scanner.run()

    print(f"\n{'='*60}")
    print(f"SMART MONEY SIGNALS - {result['entities_scanned']} entities scanned")
    print(f"{'='*60}")

    if result.get("consensus_picks"):
        print("\nCONSENSUS PICKS (2+ entities accumulating):")
        for token, pick in result["consensus_picks"].items():
            print(f"  [{pick['signal'].upper()}] {token} - {pick['reason']}")
    else:
        print("\nNo consensus picks (normal - check individual reports)")

    for report in result.get("entity_reports", []):
        sigs = report.get("signals", [])
        if sigs:
            print(f"\n{report.get('label', report.get('entity', '?'))}:")
            for sig in sigs[:3]:
                print(f"  -> {sig['reason']}")
