import base64, os
data = open(__file__+".b64").read()
code = base64.b64decode(data).decode("utf-8")
open(r"E:/findtorontoevents_antigravity.ca/alpha_engine/momentum_crash_cot.py", "w", encoding="utf-8").write(code)
print("Written:", len(code), "chars")