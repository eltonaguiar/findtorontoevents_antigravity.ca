"""Wire Copy Trader picks into AI Tournament tournament_picks format."""
import json, sys, os
from datetime import datetime, timezone

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load copy trader output
copytrader_paths = [
    "copy_trader_intel/data/stocks_copytrader_picks.json",
    "copy_trader_intel/data/forex_copytrader_picks.json",
    "copy_trader_intel/data/commodity_copytrader_picks.json",
    "alpha_engine/data/portfolio_copytrader.json",
]

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_ID = "copy_trader_v2"
PERSONA_ID = "quality_weighted_consensus"

picks = []
for relpath in copytrader_paths:
    fullpath = os.path.join(repo_root, relpath)
    if not os.path.exists(fullpath):
        continue
    try:
        data = json.load(open(fullpath))
    except (json.JSONDecodeError, UnicodeDecodeError):
        continue

    # Handle different file formats
    entries = []
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        entries = data.get("picks", []) or data.get("positions", []) or data.get("signals", [])

    for entry in entries:
        if not entry.get("symbol"):
            continue
        # Map copy trader fields to tournament format
        symbol = entry.get("symbol", "")
        direction = entry.get("direction", entry.get("side", "LONG")).upper()
        if direction not in ("LONG", "SHORT"):
            direction = "LONG"

        asset_class = entry.get("asset_class", "")
        if not asset_class:
            # Derive from source file
            if "stocks" in relpath or "equity" in relpath:
                asset_class = "EQUITY"
            elif "forex" in relpath:
                asset_class = "FOREX"
            elif "commodity" in relpath:
                asset_class = "COMMODITY"
            else:
                asset_class = "EQUITY"

        confidence = float(entry.get("confidence", entry.get("quality_score", 0.5)))
        entry_price = float(entry.get("entry_price", entry.get("price", 0)))
        thesis = entry.get("reason", entry.get("thesis", ""))
        if not thesis and entry.get("metadata"):
            thesis = str(entry["metadata"])[:500]

        picks.append({
            "symbol": symbol,
            "asset_class": asset_class,
            "direction": direction,
            "entry_price": entry_price or 0,
            "take_profit": float(entry.get("take_profit", entry.get("tp", 0))),
            "stop_loss": float(entry.get("stop_loss", entry.get("sl", 0))),
            "thesis": thesis,
            "confidence": confidence,
            "timeframe": "14d",
            "status": "OPEN",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "model_id": MODEL_ID,
            "persona_id": PERSONA_ID,
            "provider": "CopyTrader Intel V2",
            "strategy_name": entry.get("strategy", "copy_trader_consensus"),
            "data_source": "copy_trader_intel_v2",
            "data_integrity_flag": "COPY_TRADER_CONSENSUS",
            "current_price": entry_price,
            "unrealized_pnl_pct": 0,
        })

print(f"[copytrader_adapter] Converted {len(picks)} copy trader picks to tournament format")

# Output as latest tournament picks
if picks:
    out_path = os.path.join(repo_root, "data", "ai_tournament", "copy_trader_")
    out_file = os.path.join(repo_root, "audit_dashboard", "data", "copy_trader_tournament_picks.json")
    with open(out_file, "w") as f:
        json.dump(picks, f, indent=2)
    print(f"[copytrader_adapter] Written to {out_file}")
