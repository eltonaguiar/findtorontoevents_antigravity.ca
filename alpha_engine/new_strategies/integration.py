
import json
import os
from datetime import datetime, timezone
from pathlib import Path

def save_live_pick(strategy_name, symbol, signal, entry_price, tp=None, sl=None, confidence=0.7, category="crypto"):
    """
    Saves a live pick to alpha_engine/new_strategies/active_picks.json
    so it can be picked up by the isolated_signal_integrator.
    """
    picks_path = Path(__file__).resolve().parent / "active_picks.json"
    
    # Load existing
    picks = []
    if picks_path.exists():
        try:
            with open(picks_path, "r", encoding="utf-8") as f:
                picks = json.load(f)
        except:
            picks = []
    
    # Create new pick
    timestamp = datetime.now(timezone.utc).isoformat()
    direction = "LONG" if signal > 0 else "SHORT"
    
    # Default TP/SL if not provided (ATR based usually, let's just use 2% TP / 1% SL as fallback)
    if tp is None:
        tp = entry_price * (1.02 if signal > 0 else 0.98)
    if sl is None:
        sl = entry_price * (0.99 if signal > 0 else 1.01)
        
    pick_id = f"new_strat_{strategy_name}_{symbol}_{int(datetime.now().timestamp())}"
    
    new_pick = {
        "id": pick_id,
        "symbol": symbol,
        "direction": direction,
        "signal_type": direction,
        "strategy": strategy_name,
        "entry_price": float(entry_price),
        "take_profit": float(tp),
        "stop_loss": float(sl),
        "confidence": float(confidence),
        "category": category,
        "status": "ACTIVE",
        "created_at": timestamp,
        "source_system": "antigravity_experimental"
    }
    
    # Deduplicate (latest one for same symbol/strategy)
    picks = [p for p in picks if not (p["symbol"] == symbol and p["strategy"] == strategy_name)]
    picks.append(new_pick)
    
    # Save
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=4)
    
    print(f"  [INTEGRATION] Saved {direction} pick for {symbol} ({strategy_name})")
