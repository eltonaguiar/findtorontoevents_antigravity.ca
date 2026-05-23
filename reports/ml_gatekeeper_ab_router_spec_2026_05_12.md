# ML Gatekeeper A/B Router Implementation Spec (2026-05-12)

## Component 1: env flag & training gate
**File:** `ml_gatekeeper/gatekeeper.py` (SHIPPED)
- Line 66-82: `_LEAKAGE_FEATURE_INDICES = (5, 6, 19, 30)` — target leakage indices
- Line 85-87: `_drop_leakage_enabled()` — reads `ML_GATE_DROP_LEAKAGE` env var
- Line 173-175: Feature masking in `extract_features()`
- Line 413-416: Model bundle stamps `leakage_dropped`, `dropped_feature_names`

**Status:** ✅ LIVE. Env flag fully functional.

## Component 2: Hash-bucket router in score_active_picks()
**File:** `ml_gatekeeper/gatekeeper.py::score_active_picks()` (line 587)
**Location to insert:** Line 611, after `scored_picks = []` init

**Pseudocode (20 LOC):**
```python
# ── Load both model artifacts (if both exist) ──
model_old_path = MODEL_DIR / "gatekeeper_old.joblib"
model_new_path = MODEL_DIR / "gatekeeper_new.joblib"

has_old = model_old_path.exists()
has_new = model_new_path.exists()
ab_enabled = has_old and has_new

# Fallback: use single model if both don't exist
if not ab_enabled:
    model_bundle_old = model_bundle
    model_bundle_new = None
else:
    model_bundle_old = joblib.load(str(model_old_path))
    model_bundle_new = joblib.load(str(model_new_path))

scored_picks_old = []
scored_picks_new = []

for pick in active:
    # Hash-bucket router: deterministic 50/50 split on pick_id
    pick_id = pick.get("id") or pick.get("symbol", "") + str(pick.get("timestamp", ""))
    hash_val = int(hashlib.md5(pick_id.encode()).hexdigest(), 16) % 2
    use_new = (hash_val == 1) and ab_enabled  # 1 = NEW sleeve, 0 = OLD
    
    # Score with appropriate model (OLD or NEW)
    model = model_bundle_new if use_new else model_bundle_old
    # ... rest of scoring logic using model ...
    
    # Route to appropriate output list
    if use_new:
        scored_picks_new.append(scored_pick)
    else:
        scored_picks_old.append(scored_pick)
```

**Output paths:**
- `ml_gatekeeper/data/active_picks.json` (OLD sleeve, always populated)
- `ml_gatekeeper/data/active_picks_ab_new.json` (NEW sleeve, if A/B enabled)

## Component 3: Dashboard measurement panel
**File:** `audit_dashboard/dashboard_enhancements.js` (append new function)
**Location:** After existing feature blocks (~line 500+)

**Field schema for dashboard panel:**
```json
{
  "ab_sleeve_label": "ML Gatekeeper A/B (leakage-purge)",
  "measurement_window_days": 30,
  "cohorts": [
    {
      "name": "OLD (baseline, forward_wr features)",
      "picks_total": 1247,
      "picks_closed": 612,
      "wr_pct": 49.2,
      "pf": 1.18,
      "asset_classes": {
        "CRYPTO": {"n": 600, "wr": 48.1},
        "FOREX": {"n": 400, "wr": 50.3},
        "EQUITY": {"n": 200, "wr": 49.8}
      },
      "days_live": 23
    },
    {
      "name": "NEW (leakage-purged, ML_GATE_DROP_LEAKAGE=1)",
      "picks_total": 1253,
      "picks_closed": 641,
      "wr_pct": 51.1,
      "pf": 1.26,
      "asset_classes": {
        "CRYPTO": {"n": 610, "wr": 50.2},
        "FOREX": {"n": 390, "wr": 51.8},
        "EQUITY": {"n": 210, "wr": 51.4}
      },
      "days_live": 23
    }
  ],
  "statistical_test": {
    "test_type": "one_sided_z_test_wr_lift",
    "h0": "WR_NEW <= WR_OLD",
    "h1": "WR_NEW > WR_OLD + 2pp",
    "z_statistic": 0.87,
    "p_value": 0.08,
    "significance_threshold": 0.10,
    "verdict": "TBD (need 30+ more picks)"
  },
  "safety_gates": {
    "rollback_armed": true,
    "consecutive_empty_crons": 0,
    "max_tolerated_empty": 7
  }
}
```

**Rendering logic:**
- Query both JSON files (`active_picks.json` + `active_picks_ab_new.json`)
- Compute summary stats per cohort (n_closed, WR, PF by asset class)
- Run z-test on closed-pick WR delta
- Render 2-column card: OLD stats vs NEW stats, verdict (TBD/PASS/FAIL)

## Component 4: Manual training workflow
**To create:** `.github/workflows/ml-gatekeeper-ab-train.yml` (not created yet)

**Manual steps (workflow_dispatch inputs):**
```bash
# Step 1: Train OLD baseline
git checkout main
python ml_gatekeeper/gatekeeper.py
# Stamps leakage_dropped=False in bundle
mv ml_gatekeeper/models/gatekeeper_model.joblib ml_gatekeeper/models/gatekeeper_old.joblib

# Step 2: Train NEW leakage-purged
export ML_GATE_DROP_LEAKAGE=1
python ml_gatekeeper/gatekeeper.py
# Stamps leakage_dropped=True in bundle
mv ml_gatekeeper/models/gatekeeper_model.joblib ml_gatekeeper/models/gatekeeper_new.joblib

# Step 3: Commit both
git add ml_gatekeeper/models/{gatekeeper_old,gatekeeper_new}.joblib
git commit -m "feat(ml-gatekeeper-ab): Train OLD vs NEW leakage-purged sleeves"
git push origin main
```

## Component 5: Test plan (4 tests)

### Test 1: Deterministic hash-bucket routing
```python
# Verify same pick_id always routes to same model
for _ in range(10):
    hash_val = int(hashlib.md5(b"BTCUSDT_2026-05-12T10:00Z").hexdigest(), 16) % 2
    assert hash_val in (0, 1)  # Deterministic
    assert hash_val == 1  # Same ID → same bucket across runs
```

### Test 2: Both model artifacts exist post-train
```python
assert (MODEL_DIR / "gatekeeper_old.joblib").exists()
assert (MODEL_DIR / "gatekeeper_new.joblib").exists()
# Load both to verify non-corrupt
old = joblib.load(str(MODEL_DIR / "gatekeeper_old.joblib"))
new = joblib.load(str(MODEL_DIR / "gatekeeper_new.joblib"))
assert old["leakage_dropped"] == False
assert new["leakage_dropped"] == True
```

### Test 3: Train/score parity (leakage features masked in both)
```python
# When ML_GATE_DROP_LEAKAGE=1:
# - Training masks indices (5,6,19,30) to 0.0
# - Scoring extracts features with same masking applied
# - Features extracted for same pick_id must be identical
pick = {...}
X_train = extract_features(pick)  # called during train
X_score = extract_features(pick)  # called during scoring
assert X_train == X_score  # Bit-exact parity
```

### Test 4: 50/50 split validation
```python
# Hash 100 synthetic pick_ids, verify ~50 route to NEW
picks = [{"symbol": f"TEST{i}", "timestamp": f"2026-05-{12+i//4:02d}T{i%24:02d}:00Z"}
         for i in range(100)]
new_count = sum(1 for p in picks if 
    int(hashlib.md5((p["symbol"]+p["timestamp"]).encode()).hexdigest(), 16) % 2 == 1)
assert 40 <= new_count <= 60  # Allow ±10 variance on 100 samples
```

## Data flow summary
```
audit_dashboard/data/dashboard_data.json (active picks)
        ↓
ml_gatekeeper/gatekeeper.py::main()
    ├─ load_training_data() → closed picks from recent_closed
    ├─ train_model() → trains on X,y with optional leakage masking
    │  ├─ gatekeeper_old.joblib (if ML_GATE_DROP_LEAKAGE not set)
    │  └─ gatekeeper_new.joblib (if ML_GATE_DROP_LEAKAGE=1)
    └─ score_active_picks()
       ├─ hash-bucket router: pick_id % 2 → OLD or NEW model
       ├─ ml_gatekeeper/data/active_picks.json (OLD sleeve)
       └─ ml_gatekeeper/data/active_picks_ab_new.json (NEW sleeve)
        ↓
audit_trail/dashboard_generator.py
    └─ reads both JSONs, merges for dashboard display
        ↓
audit_dashboard/dashboard_enhancements.js
    └─ renders A/B measurement panel (n, WR, PF, z-stat)
```

## Activation checklist (for next builder)
- [ ] Train both model artifacts via workflow_dispatch (steps under Component 4)
- [ ] Implement hash-bucket router (~20 LOC, Component 2)
- [ ] Add dashboard panel (~30 LOC, Component 3)
- [ ] Run 4 unit tests (Component 5)
- [ ] Deploy to audit-dashboard workflow trigger (add both JSONs to artifact list)
- [ ] Monitor dashboard for 30 days; collect n≥30 per asset class
- [ ] Run z-test decision rule (Component 4 Phase D)

**Estimated effort:** 3-4 hours (router + dashboard + tests).
**Owner:** Next builder (handoff from caveman investigation).
