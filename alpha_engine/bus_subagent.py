import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import redis

# Configuration
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_CHANNEL = 'alpha_engine_bus'
LOG_FILE = Path(__file__).parent / "data" / "bus_communications.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BusSubagent")

class BusSubagent:
    """
    Subagent that communicates with the fleet via Redis Bus.
    Handles broadcasts for system updates and listens for coordination tasks.
    """
    def __init__(self):
        try:
            self.redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            self.pubsub = self.redis_client.pubsub()
            self.pubsub.subscribe(REDIS_CHANNEL)
            logger.info(f"Connected to Redis Bus on channel: {REDIS_CHANNEL}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    def broadcast(self, message_type: str, data: dict):
        """Broadcast a message to the fleet."""
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sender": "Antigravity_Alpha_Engine",
            "type": message_type,
            "payload": data
        }
        message_json = json.dumps(payload)
        if self.redis_client:
            self.redis_client.publish(REDIS_CHANNEL, message_json)
            logger.info(f"Broadcasted {message_type}: {data.get('summary', 'No summary')}")
        else:
            logger.warning(f"Bus Offline. Local Log only: {message_json}")

    def broadcast_alert(self, severity: str, summary: str, details: dict):
        """Broadcast an urgent alert (e.g., API failures)."""
        self.broadcast("ALERT", {
            "severity": severity,
            "summary": summary,
            "details": details
        })

    def sync_trader_status(self):
        """Broadcast status of external scrapers (e.g., Bitget)."""
        try:
            cache_path = Path("alpha_engine/data/bitget_trader_cache.json")
            if cache_path.exists():
                with open(cache_path, "r") as f:
                    cache = json.load(f)
                
                traders = cache.get("traders", {})
                self.broadcast("SCRAPER_SYNC", {
                    "summary": f"Bitget Scraper Sync: {len(traders)} traders in cache",
                    "status": "RESTRICTED" if not traders else "ACTIVE"
                })
        except Exception as e:
            logger.error(f"Trader sync failed: {e}")

    def sync_rehab_status(self):
        """Broadcast the latest strategy rehabilitation and mutation status."""
        try:
            registry_path = Path("alpha_engine/data/strategy_registry.json")
            if registry_path.exists():
                with open(registry_path, "r") as f:
                    registry = json.load(f)
                
                rehab_count = sum(1 for s in registry.get("strategies", {}).values() if s.get("status") == "REHAB_CANDIDATE")
                prod_count = sum(1 for s in registry.get("strategies", {}).values() if s.get("status") == "PRODUCTION")
                
                self.broadcast("STRATEGY_SYNC", {
                    "summary": f"Institutional Sync: {prod_count} Production, {rehab_count} Rehab Candidates",
                    "registry_version": registry.get("version"),
                    "rehab_queue_len": len(registry.get("rehabilitation_queue", []))
                })
        except Exception as e:
            logger.error(f"Sync failed: {e}")

    def sync_whale_intelligence(self):
        """Broadcast fresh WCI data."""
        try:
            wci_path = Path("alpha_engine/data/whale_concentration_index.json")
            if wci_path.exists():
                with open(wci_path, "r") as f:
                    wci = json.load(f)
                
                self.broadcast("WHALE_INTEL", {
                    "summary": f"WCI Update: {wci.get('symbol_count')} symbols indexed",
                    "btc_index": wci.get("index", {}).get("BTC", {}).get("wci"),
                    "eth_index": wci.get("index", {}).get("ETH", {}).get("wci"),
                    "timestamp": wci.get("timestamp")
                })
        except Exception as e:
            logger.error(f"Whale sync failed: {e}")

    def broadcast_hardening_plan(self):
        """Broadcast the Alpha Engine Hardening plan to the fleet."""
        self.broadcast("HARDENING_PLAN", {
            "summary": "Institutional-grade quality gates and risk policies active",
            "gates": {
                "threshold_a": "BT vs FWD win rate discrepancy > 15pp gate (n>=20)",
                "affinity_bonus": "Strategy-symbol pair performance bonus active (+10/+5 pts)",
                "risk_policy": "Unified portfolio caps and 5% symbol concentration limit"
            },
            "status": "ENFORCED",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

if __name__ == "__main__":
    bus = BusSubagent()
    print("Executing Institutional Fleet Sync...")
    bus.sync_rehab_status()
    bus.sync_whale_intelligence()
    bus.sync_trader_status()
    
    # Broadcast hardening plan (2026-04-05)
    bus.broadcast_hardening_plan()
    
    # Alert the bus about the Bitget API 403s
    bus.broadcast_alert("WARNING", "Bitget Scraper HTTP 403", {
        "reason": "Undocumented API restricted",
        "action": "Fallback to HTML scraping / Known symbols active"
    })
    
    print("Sync Complete.")
