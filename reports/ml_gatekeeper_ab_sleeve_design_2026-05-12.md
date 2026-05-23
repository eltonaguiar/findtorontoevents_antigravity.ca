# ml_gatekeeper A/B Sleeve Design — OLD vs NEW (leakage-purged)

Per investigator `aaf75c71ecfcbca85` + quant_rescue_master_plan THE ONE
THING. Compares ml_gatekeeper trained WITH leakage features vs trained
WITHOUT (`ML_GATE_DROP_LEAKAGE=1` env-flag shipped this commit).

## Why

3-round quant swarm convergence: `forward_wr` (idx 5), `strat_fwd_wr`
(idx 6), `eb_forward_wr` (idx 19), `age_hours` (idx 30) are downstream
proxies of the target. The +9.21pp CV lift is partly illusory.

## Mechanism (shipped this commit)

- `ML_GATE_DROP_LEAKAGE=1` env var masks the 4 leakage features to 0.0
  in BOTH training and scoring.
- Model bundle stamps `leakage_dropped`, `dropped_feature_names`,
  `dropped_feature_indices`, `trained_at_iso` so scoring can verify
  train/score parity.

## A/B operational plan

### Phase A — train two models in parallel (Week 2)

```bash
# OLD baseline (current production)
python ml_gatekeeper/gatekeeper.py train
# stamps leakage_dropped=False
mv ml_gatekeeper/models/gatekeeper_model.joblib ml_gatekeeper/models/gatekeeper_old.joblib

# NEW leakage-purged
ML_GATE_DROP_LEAKAGE=1 python ml_gatekeeper/gatekeeper.py train
# stamps leakage_dropped=True
mv ml_gatekeeper/models/gatekeeper_model.joblib ml_gatekeeper/models/gatekeeper_new.joblib
```

### Phase B — split live emission (Week 2-3)

Hash-bucket on pick_id mod 2 (deterministic + replayable):
- Even hash → score with `gatekeeper_old.joblib` → `active_picks.json`
- Odd hash → score with `gatekeeper_new.joblib` → `active_picks_ab_new.json`

Both files committed each cron via existing commit-list infra.

### Phase C — measurement window (Week 3-7)

- **Duration:** 30 days forward observation
- **Per-class min n:** 30 picks per class before declaring significance
- **Extend to 45 days** if any class undersamples

Expected volume: ~50-80 NEW picks/day at 50% split → n≈1500-2400 picks
over 30 days. Per-class: CRYPTO ~600, FOREX ~400, EQUITY ~300, others ~200.

### Phase D — decision rule (end of window)

One-sided z-test: H0: WR_NEW ≤ WR_OLD ; H1: WR_NEW > WR_OLD + 2pp.

- z > 1.28 (p < 0.10) → NEW wins; replace production gatekeeper
- z ≤ 1.28 → OLD remains; forward-wr features are not liabilities (likely the +9.21pp CV was real, not leak-driven)

### Phase E — rollback safety

If `active_picks_ab_new.json` is empty/null for 7 consecutive cron cycles
(NEW emits 0 picks), auto-freeze NEW + alert. Dashboard reverts to OLD
only until human investigation.

## Dashboard visibility

Extend `audit_dashboard/dashboard_enhancements.js` with a new section
reading both JSONs. Show:

```
┌─ ML Gatekeeper A/B (30-day window) ──────────────┐
│ OLD: 1,247 picks · 49.2% WR · 23d live          │
│ NEW: 1,253 picks · 51.1% WR · 23d live          │
│ Winner: TBD (p=0.08, need 30 more picks)        │
│ Rollback: ARMED                                  │
└──────────────────────────────────────────────────┘
```

## Status

**Phase A unblocked this commit** — env flag works (smoke test
verified). Phase B+ requires:
1. Two trained model artifacts (manual `workflow_dispatch` trigger of
   `.github/workflows/enhanced-ml-crypto.yml` train mode with + without
   the env var)
2. Hash-bucket router in `score_active_picks()` (~20 LOC)
3. Dashboard panel (~30 LOC in dashboard_enhancements.js)

Total ~3-4h follow-up to complete the A/B mechanism.

## NFA

Research surface. No real-money sizing impact from the leakage purge
itself; impact is on which picks get gated. The 10-step Lopez de Prado
AFML readiness pipeline remains the canonical bar.

## Refs

- `reports/quant_rescue_master_plan_2026-05-12.md` (THE ONE THING)
- `reports/ml_staleness_audit_2026-05-12.md` (gatekeeper feature importance)
- Investigator `ad0d03c475517f6ff` (leakage locations)
- Investigator `aaf75c71ecfcbca85` (A/B design)
