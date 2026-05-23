# HF Quality Fixes - 4 Gaps Implemented
## 2026-04-07

### Gap Fixes Applied:

1. **HF Validator Recalibration** (`audit_trail/hf_strict_smart_gate.py`)
   - Changed min_risk_reward: 2.5 → 1.2
   - Data: RR 1.0-1.5 = 56% WR (vs 2.5 = 25% WR)

2. **Conviction Tier Persistence** (`tools/save_conviction_tiers.py`)
   - Created tool to save conviction tiers to config/hf_conviction_tiers.json
   - Enables "High Conviction" button with persistent data

3. **quan_engine_scalp Hard Block** (`audit_trail/quality_gates.py`)
   - Increased score penalty: -15 → -25
   - Data: 21% WR, 2340 picks at -25 penalty

4. **backfill_picks Wire** (`audit_trail/dashboard_generator.py`)
   - Already wired at line 10855 (was already done!)

---

### Files Modified:
- audit_trail/hf_strict_smart_gate.py (RR threshold)
- audit_trail/quality_gates.py (quan_engine_scalp penalty)
- tools/save_conviction_tiers.py (NEW)
- tools/pipeline_monitor.py (NEW)