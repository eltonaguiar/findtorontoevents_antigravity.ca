"""Whale consensus confidence booster — adds direction weight from Polymarket whales."""
import json, os, sys

def load_whale_signals() -> dict[str, str]:
    """Load whale signals and return {symbol: majority_direction} if 2+ whales agree."""
    whale_paths = [
        "alpha_engine/data/polymarket_signals.json",
        "copy_trader_intel/data/polymarket_picks.json",
    ]
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    whale_votes: dict[str, dict[str, int]] = {}
    for relpath in whale_paths:
        fullpath = os.path.join(repo_root, relpath)
        if not os.path.exists(fullpath):
            continue
        try:
            data = json.load(open(fullpath))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        
        picks = []
        if isinstance(data, list):
            picks = data
        elif isinstance(data, dict):
            picks = data.get("picks", []) or data.get("signals", [])
        
        for p in picks:
            sym = p.get("symbol", "").upper()
            direction = p.get("direction", "").upper()
            if sym and direction in ("LONG", "SHORT"):
                if sym not in whale_votes:
                    whale_votes[sym] = {"LONG": 0, "SHORT": 0}
                whale_votes[sym][direction] += 1
    
    # Only return if 2+ whales agree
    consensus = {}
    for sym, votes in whale_votes.items():
        total = sum(votes.values())
        if total >= 2:
            if votes["LONG"] > votes["SHORT"]:
                consensus[sym] = "LONG"
            elif votes["SHORT"] > votes["LONG"]:
                consensus[sym] = "SHORT"
    
    return consensus


def boost_with_whale_consensus(picks: list[dict], boost_factor: float = 0.10) -> list[dict]:
    """Boost confidence for picks that align with whale consensus direction.
    
    If a pick's direction matches the whale consensus, add boost_factor to confidence.
    If it opposes, subtract boost_factor (penalty for contrarian bet).
    Clamps to [0.20, 0.90] range.
    """
    whale_consensus = load_whale_signals()
    if not whale_consensus:
        print("[whale_boost] No whale signals available — skipping")
        return picks
    
    boosted = 0
    penalized = 0
    for p in picks:
        sym = p.get("symbol", "").upper()
        if sym not in whale_consensus:
            continue
        
        direction = p.get("direction", "").upper()
        conf = float(p.get("confidence", 0.5))
        
        whale_dir = whale_consensus[sym]
        if direction == whale_dir:
            p["confidence"] = round(min(0.90, conf + boost_factor), 4)
            boosted += 1
        else:
            p["confidence"] = round(max(0.20, conf - boost_factor), 4)
            penalized += 1
    
    print(f"[whale_boost] Applied: {boosted} boosted, {penalized} penalized")
    return picks


if __name__ == "__main__":
    # Test: load picks and demonstrate boosting
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    picks_path = os.path.join(repo_root, "audit_dashboard", "data", "ai_tournament_picks_latest.json")
    if os.path.exists(picks_path):
        picks = json.load(open(picks_path))
        whale = load_whale_signals()
        print(f"Whale consensus: {len(whale)} symbols with 2+ whale agreement")
        for sym, d in list(whale.items())[:5]:
            print(f"  {sym} → {d}")
    else:
        print("No picks file found for demo")
