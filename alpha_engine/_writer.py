import sys
target = r"E:/findtorontoevents_antigravity.ca/alpha_engine/momentum_crash_cot.py"
lines = sys.stdin.read()
open(target, "w", encoding="utf-8").write(lines)
print("Written", len(lines), "chars to", target)
