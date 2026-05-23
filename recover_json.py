import re

files = [
    r"e:\findtorontoevents_antigravity.ca\alpha_engine\data\closed_picks.json",
    r"e:\findtorontoevents_antigravity.ca\alpha_engine\data\active_picks.json",
    r"e:\findtorontoevents_antigravity.ca\alpha_engine\data\circuit_breaker.json"
]

def fix_file(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    new_lines = []
    in_conflict = False
    keep_side = False # False = part 1 (upstream), True = part 2 (stashed)
    
    # We'll keep the 'Stashed changes' (bottom) side by default
    for line in lines:
        if line.startswith("<<<<<<<"):
            in_conflict = True
            keep_side = False
            continue
        if line.startswith("======="):
            keep_side = True
            continue
        if line.startswith(">>>>>>>"):
            in_conflict = False
            continue
        
        if in_conflict:
            if keep_side:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"Fixed {path}")

import os
for f in files:
    fix_file(f)
