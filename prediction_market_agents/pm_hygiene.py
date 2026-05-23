import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
RESOLVED_FILE = ROOT / "audit_trail" / "data" / "universal_resolved_picks.json"
MAX_CLOSED_AGE_HOURS = 24

def load_resolved_ids() -> set[str]:
    """Load IDs of picks that have been resolved by the audit trail."""
    if not RESOLVED_FILE.exists():
        return set()
    try:
        with open(RESOLVED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            resolved = data if isinstance(data, list) else data.get("resolved", [])
            # We use a composite key for PM signals: symbol + direction + strategy
            ids = set()
            for r in resolved:
                sym = r.get("symbol", "").upper()
                direction = r.get("direction", "").upper()
                strat = r.get("strategy", "").lower()
                if sym and direction:
                    ids.add(f"{sym}_{direction}_{strat}")
            return ids
    except Exception as e:
        logger.warning(f"Failed to load resolved IDs: {e}")
        return set()

def apply_pm_persistence(current_signals: List[Dict[str, Any]], previous_file: Path) -> List[Dict[str, Any]]:
    """
    Apply persistence logic to prediction market signals:
    1. Carry over previously CLOSED signals for 24h.
    2. Mark currently OPEN signals as CLOSED if they've been resolved in the audit trail.
    3. Filter out OLD closed signals to prevent bloat.
    """
    now = datetime.now(timezone.utc)
    resolved_ids = load_resolved_ids()
    
    # Load previous signals
    previous_signals = []
    if previous_file.exists():
        try:
            with open(previous_file, "r", encoding="utf-8") as f:
                content = json.load(f)
                if isinstance(content, list):
                    previous_signals = content
                elif isinstance(content, dict):
                    previous_signals = content.get("signals", [])
        except Exception as e:
            logger.warning(f"Failed to load previous signals from {previous_file}: {e}")

    # Index current signals by composite key
    new_signals_map = {}
    for s in current_signals:
        key = f"{s.get('symbol', '').upper()}_{s.get('direction', '').upper()}_{s.get('strategy', '').lower()}"
        new_signals_map[key] = s

    # Process previous signals to keep CLOSED ones
    persistent_signals = []
    seen_keys = set()

    # 1. Start with currently active signals
    for key, sig in new_signals_map.items():
        # If this signal was previously CLOSED, check if it should stay CLOSED
        # Actually, if the scanner still sees it as a valid signal (OPEN), we keep it OPEN
        # UNLESS the audit trail says it hit TP/SL.
        if key in resolved_ids:
            sig["status"] = "CLOSED"
            if not sig.get("resolved_at"):
                sig["resolved_at"] = now.isoformat()
        
        persistent_signals.append(sig)
        seen_keys.add(key)

    # 2. Add previous CLOSED signals that are still within the age limit
    for ps in previous_signals:
        if ps.get("status") == "CLOSED":
            key = f"{ps.get('symbol', '').upper()}_{ps.get('direction', '').upper()}_{ps.get('strategy', '').lower()}"
            if key in seen_keys:
                continue
            
            # Check age
            res_at = ps.get("resolved_at") or ps.get("timestamp")
            try:
                dt = datetime.fromisoformat(res_at.replace("Z", "+00:00"))
                if (now - dt).total_seconds() < MAX_CLOSED_AGE_HOURS * 3600:
                    persistent_signals.append(ps)
                    seen_keys.add(key)
            except Exception:
                # If we can't parse the timestamp, drop it to be safe (prevent infinite bloat)
                pass

    return persistent_signals
