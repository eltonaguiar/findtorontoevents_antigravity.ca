import json
from pathlib import Path

# Paths
DATA_DIR = Path("e:/findtorontoevents_antigravity.ca/alpha_engine/data")
DNA_PICKS_PATH = DATA_DIR / "dna_reviver_picks.json"
ACTIVE_PICKS_PATH = DATA_DIR / "active_picks.json"

def inject():
    if not DNA_PICKS_PATH.exists():
        print("No DNA picks found to inject.")
        return

    with open(DNA_PICKS_PATH, "r") as f:
        dna_picks = json.load(f)
    
    if not dna_picks:
        print("DNA picks list is empty.")
        return

    if ACTIVE_PICKS_PATH.exists():
        with open(ACTIVE_PICKS_PATH, "r") as f:
            try:
                active = json.load(f)
            except (IOError, json.JSONDecodeError, ValueError):
                active = []
    else:
        active = []

    # Filter out duplicates by ID
    active_ids = set([p.get('id') for p in active])
    new_picks = [p for p in dna_picks if p.get('id') not in active_ids]

    if not new_picks:
        print("All DNA picks are already in active_picks.json.")
        return

    active.extend(new_picks)
    
    with open(ACTIVE_PICKS_PATH, "w") as f:
        json.dump(active, f, indent=2, default=str)
    
    print(f"Successfully injected {len(new_picks)} DNA picks into active_picks.json.")

if __name__ == "__main__":
    inject()
