import base64
target = r"e:/findtorontoevents_antigravity.ca/ml_crypto_predictor/enhanced_models/regime_detector.py"
old = open(target, encoding="utf-8").read()
cf_s = old.index("    def _compute_features")
cf_e = old.index("    def train(", cf_s)
cf = old[cf_s:cf_e]
cf_b64 = base64.b64encode(cf.encode()).decode()
# Read rest-of-file template from b64 file and splice in cf
rest_b64 = open(r"e:/findtorontoevents_antigravity.ca/tmp/_rest.b64").read().strip()
rest = base64.b64decode(rest_b64).decode("utf-8")
# Replace placeholder with actual _compute_features
final = rest.replace("###COMPUTE_FEATURES_PLACEHOLDER###", cf)
open(target, "w", encoding="utf-8").write(final)
print(f"Written {len(final)} bytes to {target}")
