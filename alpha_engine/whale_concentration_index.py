"""
whale_concentration_index.py - Alpha Engine: Whale Intelligence Aggregator
========================================================================
Consolidates whale alerts, smart money wallet tracking, and prediction 
market sentiment into a single unified 'Whale Concentration Index' (WCI).

WCI Range: 0.0 (Extreme Bearish Whale Pressure) to 1.0 (Extreme Bullish).
Neutral = 0.5.

Integrated Sources:
1. WhaleAlert (Exchange Flows)
2. Etherscan (Whale Wallet Transfers)
3. Arkham Intelligence (Smart Money Entities)
4. Prediction Markets (Polymarket/Kalshi Whale Sentiment)

Usage:
    from whale_concentration_index import get_wci
    score = get_wci("BTC")
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Import sub-scanners
try:
    from whale_alert_scanner import get_whale_signal
    from etherscan_whale_tracker import get_whale_wallet_signal
    from arkham_smart_money import get_smart_money_signal
    from prediction_market_whales import generate_prediction_market_picks
    _IMPORTS_OK = True
except ImportError as e:
    logging.error(f"Whale index imports failed: {e}")
    _IMPORTS_OK = False

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / "whale_concentration_index.json"

class WhaleConcentrationIndex:
    """Aggregates multi-source whale intelligence."""

    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.last_updated: Optional[str] = None

    def load(self):
        """Load latest index from disk."""
        try:
            if OUTPUT_FILE.exists():
                with open(OUTPUT_FILE) as f:
                    content = json.load(f)
                    self.data = content.get("index", {})
                    self.last_updated = content.get("timestamp")
        except Exception as e:
            logger.error(f"Failed to load WCI: {e}")

    def get_score(self, symbol: str) -> float:
        """Get WCI for a symbol. Returns 0.5 (neutral) if unknown."""
        sym = symbol.upper().replace("USDT", "").replace("-USD", "").replace("USD", "")
        # Handle Binance-style symbols
        if sym.endswith("USDT"): sym = sym[:-4]
        
        return self.data.get(sym, {}).get("wci", 0.5)

    def calculate_all(self):
        """Run all scanners and compute aggregate index for all detected symbols."""
        if not _IMPORTS_OK:
            return {}

        all_symbols = set()
        
        # 1. Fetch raw signals
        whale_alert = {}
        etherscan = {}
        arkham = {}
        pred_market_picks = []

        try:
            # Note: In a production loop, these would be read from their respective JSONs
            # to avoid blocking for minutes on API calls.
            # Here we assume the individual scanners have already run.
            
            # For simplicity, we'll try to find symbols across a broad universe
            base_universe = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "LINK", "AVAX", "DOT", "MATIC"]
            
            for sym in base_universe:
                wa = get_whale_signal(sym)
                if wa: 
                    whale_alert[sym] = wa
                    all_symbols.add(sym)
                
                es = get_whale_wallet_signal(sym)
                if es:
                    etherscan[sym] = es
                    all_symbols.add(sym)

                ak = get_smart_money_signal(sym)
                if ak:
                    arkham[sym] = ak
                    all_symbols.add(sym)

            # Prediction market picks often contain more specific alpha
            try:
                pred_market_picks = generate_prediction_market_picks()
                for p in pred_market_picks:
                    p_sym = p.get("symbol", "").replace("USDT", "")
                    if p_sym: all_symbols.add(p_sym)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Signal aggregation failed: {e}")

        # 2. Compute Index per symbol
        new_index = {}
        for sym in all_symbols:
            score = 0.5  # Neutral base
            components = {}
            
            # WhaleAlert: net_score is -1 to 1. Weight: 0.15
            wa = whale_alert.get(sym)
            if wa:
                wa_impact = wa.get("strength", 0) * 0.15
                score += wa_impact
                components["whale_alert"] = round(wa_impact, 3)

            # Etherscan: direction-based. Weight: 0.15
            es = etherscan.get(sym)
            if es:
                es_val = 0.15 if es["direction"] == "bullish" else (-0.15 if es["direction"] == "bearish" else 0)
                score += es_val
                components["etherscan"] = es_val

            # Arkham: direction-based. Weight: 0.20 (High conviction)
            ak = arkham.get(sym)
            if ak:
                ak_val = 0.20 if ak["direction"] == "bullish" else (-0.20 if ak["direction"] == "bearish" else 0)
                score += ak_val
                components["arkham"] = ak_val

            # Prediction Markets: pick-based. Weight: 0.10
            pm_picks = [p for p in pred_market_picks if p.get("symbol", "").startswith(sym)]
            if pm_picks:
                best_pm = max(pm_picks, key=lambda x: x.get("confidence", 0))
                pm_val = 0.10 if best_pm["direction"] == "LONG" else -0.10
                score += pm_val
                components["prediction_market"] = pm_val

            # Clamp and store
            score = max(0.0, min(1.0, score))
            new_index[sym] = {
                "wci": round(score, 3),
                "sentiment": "bullish" if score > 0.6 else ("bearish" if score < 0.4 else "neutral"),
                "components": components,
                "conviction": "high" if abs(score - 0.5) > 0.25 else "normal"
            }

        output = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol_count": len(new_index),
            "index": new_index
        }

        # Save
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(output, f, indent=2)
        
        self.data = new_index
        self.last_updated = output["timestamp"]
        logger.info(f"WCI updated for {len(new_index)} symbols.")
        return new_index

# Singleton instances for easy import
_index_memo = WhaleConcentrationIndex()

def get_wci(symbol: str) -> float:
    """Helper for production_scanner.py to get whale boost."""
    if not _index_memo.data:
        _index_memo.load()
    return _index_memo.get_score(symbol)

def get_wci_boost(symbol: str) -> float:
    """
    Returns a multiplier (0.5x to 1.5x) based on whale concentration.
    Institutional conviction multiplier.
    """
    wci = get_wci(symbol)
    # 0.5 -> 1.0 (no change)
    # 1.0 -> 1.5 (50% boost)
    # 0.0 -> 0.5 (50% penalty)
    return 0.5 + wci

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    wci_engine = WhaleConcentrationIndex()
    wci_engine.calculate_all()
    print(f"WCI Calculation Complete. {len(wci_engine.data)} symbols indexed.")
    for s, d in list(wci_engine.data.items())[:5]:
        print(f"  {s}: {d['wci']} ({d['sentiment']})")
