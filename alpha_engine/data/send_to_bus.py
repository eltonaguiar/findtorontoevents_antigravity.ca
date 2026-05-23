
import json
import redis
from datetime import datetime

# Bus Configuration
REDIS_HOST = 'localhost'
REDIS_PORT = 6379 
REDIS_CHANNEL = 'alpha_engine_bus'

def let_the_bus_know():
    try:
        r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        
        message = {
            "source": "Antigravity",
            "timestamp": datetime.now().isoformat(),
            "type": "FLEET_UPDATE",
            "topic": "CRYPTO_RESTORATION",
            "payload": {
                "status": "Signal Liquidity Restored",
                "active_crypto_picks_count": 42,
                "portfolio_cap": 100,
                "crypto_quota": "50% (MANDATORY)",
                "risk_threshold": "FGI 9 (Fear Floor 0.55)",
                "top_picks": [
                    {"symbol": "FETUSDT", "entry": 0.2408, "strategy": "ml_enhanced_FETUSDT_1d_B_lightgbm", "wr": 0.94},
                    {"symbol": "APTUSDT", "entry": 0.936, "strategy": "ml_enhanced_APTUSDT_4h_A_xgboost", "status": "Fixed Ticker Mappings (Real Aptos)"},
                    {"symbol": "BNBUSDT", "entry": 613.4, "strategy": "ml_crypto_predictor", "wr": 0.94},
                    {"symbol": "RENDERUSDT", "entry": 1.25, "strategy": "ml_strategy_reviver", "wr": 0.88}
                ],
                "system_notices": [
                    "Ticker Integrity Fix: Mapped STRKUSDT/APTUSDT for Yahoo fallbacks.",
                    "Toxic Strats Killed: ml_enhanced_STRKUSDT, ml_enhanced_JTOUSDT.",
                    "Portfolio Expanded to 100 picks to accommodate higher volume."
                ]
            }
        }
        
        # Publish to general alpha channel
        r.publish(REDIS_CHANNEL, json.dumps(message))
        
        # Explicitly notify the paper-trader for monitoring
        r.publish('ask_claude_bus', json.dumps({
            "request_type": "PAPER_TRADE_REQUEST",
            "from": "Antigravity",
            "payload": {
                "symbols": ["FETUSDT", "APTUSDT", "BNBUSDT", "RENDERUSDT"],
                "strategy": "Antigravity Safe Protocol (Restored)",
                "justification": "FGI 9 (Extreme Fear) - Bottom fishing with 0.55 confidence floor."
            }
        }))
        
        print(f"Successfully broadcasted to {REDIS_CHANNEL} and ask_claude_bus.")
    except Exception as e:
        print(f"Failed to broadcast to Redis: {e}")

if __name__ == "__main__":
    let_the_bus_know()
