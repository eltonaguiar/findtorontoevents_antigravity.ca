import json
from datetime import datetime, timezone
from pathlib import Path

def check_forex():
    # Use absolute path or relative to script root
    script_dir = Path(__file__).resolve().parent
    ap_path = script_dir / "data" / "active_picks.json"
    if not ap_path.exists():
        print("active_picks.json not found")
        return

    with open(ap_path) as f:
        ap = json.load(f)

    # Forex picks
    forex = [p for p in ap if p.get("asset_class") == "forex" or p.get("category") == "forex" or "=X" in p.get("symbol", "")]
    print(f"Total forex picks: {len(forex)}")

    now = datetime.now(timezone.utc)
    
    for p in forex:
        symbol = p.get("symbol", "?")
        strat = p.get("strategy", "?")
        score = p.get("elite_score", 0)
        pnl = p.get("pnl_pct", 0)
        
        # Check staleness
        ts_str = p.get("timestamp") or p.get("last_checked")
        stale = False
        if ts_str:
            try:
                # Remove Z and replace with +00:00 for ISO format
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                diff = now - ts
                if diff.total_seconds() > 86400: # 24h
                    stale = True
                    stale_hours = diff.total_seconds() / 3600
            except (ValueError, TypeError):
                stale = "error"
        
        status_msg = f"  {symbol:12s} {strat:40s} score={score:2d} pnl={pnl:7.2f}%"
        if stale == True:
            status_msg += f" [STALE: {stale_hours:.1f}h]"
        elif stale == "error":
            status_msg += " [TS_ERROR]"
            
        print(status_msg)

if __name__ == "__main__":
    check_forex()
