import os
import glob
import json
import pandas as pd
from datetime import datetime

def inject_signals():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    signals_dir = os.path.join(base_dir, 'data_lake', 'feature_store', 'signals')
    active_picks_path = os.path.join(base_dir, 'alpha_engine', 'data', 'active_picks.json')
    
    # Load existing active picks
    active_picks = []
    if os.path.exists(active_picks_path):
        try:
            with open(active_picks_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    active_picks = data.get("picks", [])
                elif isinstance(data, list):
                    active_picks = data
        except Exception as e:
            print(f"Error reading active_picks.json: {e}")
            
    # Track existing IDs to avoid duplicates
    existing_ids = {p.get("id") for p in active_picks if p.get("id")}
    
    new_picks_added = 0
    today_str = datetime.now().strftime('%Y%m%d')
    date_iso = datetime.now().strftime('%Y-%m-%d')
    timestamp_iso = datetime.now().isoformat()
    
    # 1. Process Volume Anomalies
    vol_files = glob.glob(os.path.join(signals_dir, f'volume_anomalies_*.json'))
    if vol_files:
        latest_vol = max(vol_files, key=os.path.getmtime)
        try:
            with open(latest_vol, 'r') as f:
                vol_data = json.load(f)
                
            for v in vol_data:
                sym = v.get("Symbol", "")
                direction = v.get("Direction", "BULLISH")
                close_px = float(v.get("Close", 0))
                
                sig_type = "BUY" if direction == "BULLISH" else "SELL"
                tp = close_px * 1.15 if sig_type == "BUY" else close_px * 0.85
                sl = close_px * 0.90 if sig_type == "BUY" else close_px * 1.10
                
                pick_id = f"volume_anomaly_scanner::{sym}::{date_iso}"
                
                if pick_id not in existing_ids and close_px > 0:
                    new_pick = {
                        "id": pick_id,
                        "strategy": "volume_anomaly_scanner",
                        "symbol": sym,
                        "category": v.get("Category", "meme_coins"),
                        "signal_type": sig_type,
                        "direction": "LONG" if sig_type == "BUY" else "SHORT",
                        "entry_price": close_px,
                        "entry_date": date_iso,
                        "timestamp": timestamp_iso,
                        "take_profit": tp,
                        "stop_loss": sl,
                        "confidence": v.get("Sentiment_Score", 0.6),
                        "ml_score": 0.0,
                        "risk_reward": abs(tp - close_px) / abs(sl - close_px) if sl != close_px else 0,
                        "reason": f"Volume spike ({v.get('Vol_Multiple', 0)}x) with {direction} price move",
                        "status": "OPEN",
                        "vol_multiple": v.get("Vol_Multiple", 0)
                    }
                    active_picks.append(new_pick)
                    existing_ids.add(pick_id)
                    new_picks_added += 1
        except Exception as e:
            print(f"Error processing volume anomalies: {e}")
            
    # 2. Process Insider Buys
    insider_files = glob.glob(os.path.join(signals_dir, f'insider_buys_*.json'))
    if insider_files:
        latest_insider = max(insider_files, key=os.path.getmtime)
        try:
            with open(latest_insider, 'r') as f:
                in_data = json.load(f)
                
            for i in in_data:
                sym = i.get("Symbol", "")
                vol = i.get("Volume", 0)
                
                pick_id = f"insider_filing_scanner::{sym}::{date_iso}"
                
                if pick_id not in existing_ids:
                    # We often lack direct current price for insiders in this JSON,
                    # so we just emit a signal without rigid TP/SL if missing,
                    # or set placeholders.
                    new_pick = {
                        "id": pick_id,
                        "strategy": "insider_filing_scanner",
                        "symbol": sym,
                        "category": "stocks",
                        "signal_type": "BUY",
                        "direction": "LONG",
                        "entry_price": 0.0, # Placeholder, hub will update if possible
                        "entry_date": date_iso,
                        "timestamp": timestamp_iso,
                        "take_profit": 0.0,
                        "stop_loss": 0.0,
                        "confidence": 0.8,
                        "ml_score": 0.0,
                        "risk_reward": 2.0,
                        "reason": f"Significant insider buy detected: {vol} shares",
                        "status": "OPEN",
                        "insider_volume": vol
                    }
                    active_picks.append(new_pick)
                    existing_ids.add(pick_id)
                    new_picks_added += 1
        except Exception as e:
            print(f"Error processing insider buys: {e}")
            
    # Save back
    if new_picks_added > 0:
        print(f"Injecting {new_picks_added} new scanner signals into active_picks.json...")
        try:
            # Check original structure
            with open(active_picks_path, 'r') as f:
                orig_data = json.load(f)
                
            if isinstance(orig_data, dict):
                orig_data["picks"] = active_picks
                out_data = orig_data
            else:
                out_data = active_picks
                
            with open(active_picks_path, 'w') as f:
                json.dump(out_data, f, indent=2)
            print("Successfully injected sentiment/volume picks.")
        except Exception as e:
            print(f"Error saving updated active_picks.json: {e}")
    else:
        print("No new scanner signals to inject.")

if __name__ == "__main__":
    inject_signals()
