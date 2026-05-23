import os
import re

def fix_conflicts(path):
    if not os.path.exists(path):
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # regex to keep "Stashed changes" (the second block)
    # <<<<<<< Updated upstream
    # block1
    # =======
    # block2
    # >>>>>>> Stashed changes
    
    # Or keep "Updated upstream" if Stashed is missing or vice versa
    # Let's try to be robust
    
    pattern = re.compile(r'<<<<<<< Updated upstream\n(.*?)\n=======\n(.*?)\n>>>>>>> Stashed changes', re.DOTALL)
    new_content = pattern.sub(r'\2', content)
    
    # Secondary pattern for standard git markers
    pattern2 = re.compile(r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> .*?\n', re.DOTALL)
    new_content = pattern2.sub(r'\2', new_content)
    
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed conflicts in {path}")
    else:
        print(f"No conflicts found in {path}")

files = [
    "alpha_engine/data/active_picks.json",
    "alpha_engine/data/closed_picks.json",
    "alpha_engine/data/strategy_performance.json",
    "alpha_engine/data/premium_signals.json",
    "alpha_engine/data/strategy_tweaks.json",
    "alpha_engine/data/circuit_breaker.json",
    "alpha_engine/data/consecutive_loss_tracker.json",
    "battleground/data/combo_metrics.json"
]

for f in files:
    fix_conflicts(os.path.join(r"e:\findtorontoevents_antigravity.ca", f))
