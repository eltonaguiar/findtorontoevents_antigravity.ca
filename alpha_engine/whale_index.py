import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from whale_alert_scanner import get_whale_signal
    from etherscan_whale_tracker import get_whale_wallet_signal
    from arkham_smart_money import get_smart_money_signal
except ImportError:
    # Fallback/mock if not in same directory or missing
    def get_whale_signal(symbol): return None
    def get_whale_wallet_signal(symbol): return None
    def get_smart_money_signal(symbol): return None

logger = logging.getLogger(__name__)

class WhaleIndex:
    """
    Ag
    gregates whale intelligence from Whale Alert, Etherscan, and Arkham.
    Provides a unified Whale Concentration Index (0-100).
    """
    
    @staticmethod
    def get_symbol_index(symbol: str) -> Dict[str, Any]:
        """
        Compute composite whale index for a symbol.
        Returns details on direction, strength, and source signals.
        """
        sym = symbol.upper().replace("USDT", "").replace("-USD", "").replace("USD", "")
        
        wa_signal = get_whale_signal(symbol)
        ew_signal = get_whale_wallet_signal(symbol)
        as_signal = get_smart_money_signal(symbol)
        
        signals = []
        if wa_signal: signals.append(wa_signal)
        if ew_signal: signals.append(ew_signal)
        if as_signal: signals.append(as_signal)
        
        if not signals:
            return {
                "index": 50,
                "direction": "neutral",
                "confidence": 0,
                "sources": 0,
                "reason": "No whale signals detected"
            }
            
        # Compute weighted average direction
        # Bullish = +1, Bearish = -1, Neutral = 0
        score = 0
        total_strength = 0
        
        sources = {
            "whale_alert": wa_signal,
            "etherscan": ew_signal,
            "arkham": as_signal
        }
        
        for name, sig in sources.items():
            if not sig: continue
            
            direction = sig.get("direction", "neutral")
            strength = float(sig.get("strength", 50))
            
            weight = 1.0
            if name == "arkham": weight = 1.2 # Smart money consensus is higher quality
            if name == "etherscan": weight = 1.1 # Direct wallet tracking
            
            if direction == "bullish":
                score += strength * weight
            elif direction == "bearish":
                score -= strength * weight
            
            total_strength += strength * weight
            
        normalized_score = 50 + (score / max(total_strength, 1)) * 50
        normalized_score = max(0, min(100, normalized_score))
        
        direction = "neutral"
        if normalized_score > 60: direction = "bullish"
        elif normalized_score < 40: direction = "bearish"
        
        reasons = [sig.get("reason", "") for sig in signals if sig.get("reason")]
        
        return {
            "index": round(normalized_score, 1),
            "direction": direction,
            "confidence": round(len(signals) / 3.0, 2),
            "sources": len(signals),
            "reason": "; ".join(reasons[:2]),
            "details": {k: v for k, v in sources.items() if v}
        }

def get_whale_concentration_index(symbol: str) -> Dict[str, Any]:
    return WhaleIndex.get_symbol_index(symbol)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_sym = "BTC"
    print(f"Whale Index for {test_sym}:")
    print(json.dumps(get_whale_concentration_index(test_sym), indent=2))
