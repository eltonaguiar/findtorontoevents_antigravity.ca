# HF Performance Validation Handoff (2026-04-09)

## Purpose
Provide a reproducible, independent-validation brief for another IDE agent to:
- verify HF vs non-HF performance numbers,
- confirm timeframe logic,
- and propose/code optimizations with feedback.

---

## Timeframe Used (Exact)

### 1) Strict window requested
- **Definition:** "Since the last code change today"
- **Cutoff source:** git log timestamp
- **Value used:** `2026-04-09 11:01:08 -0400` = `2026-04-09T15:01:08Z`

### 2) Data-availability fallback window
- **Reason:** latest audit payload in repo predates strict cutoff.
- **Payload source:** `audit_trail/data/dashboard_payload.json`
- **Payload generated_at:** `2026-04-09T00:04:12.262857+00:00`

### Why both were used
- Strict post-change window returned no rows (payload is older than cutoff).
- Fallback window used latest available snapshot to provide actionable insights.

---

## Data Sources Used

- `audit_trail/data/dashboard_payload.json`
  - `picks.active` -> unrealized analysis
  - `picks.recent_closed` -> realized analysis
- `alpha_engine/conviction_stack.py`
  - `classify_hf_conviction_tier(pick, cfg)` used for join/classification when tier absent.

---

## Definitions Used

- **HF pick:** `hf_conviction_tier` or `conviction_tier` in `{S, A, B}`
- **Non-HF pick:** not in `{S, A, B}`
- **Unrealized pnl:**
  - prefer `unrealized_pnl_pct`
  - fallback:
    - long: `(current_price - entry_price) / entry_price * 100`
    - short/sell: `(entry_price - current_price) / entry_price * 100`
- **Realized pnl:** `pnl_pct`
- **Win rate:** count of pnl > 0 divided by rows with numeric pnl
- **Avg pnl:** arithmetic mean pnl over rows with numeric pnl

---

## Key Finding: Strict Post-Change Window

- Cutoff: `2026-04-09T15:01:08Z`
- Latest payload: `2026-04-09T00:04:12Z`
- **Result:** no rows exist in strict post-change window.

---

## Snapshot Results (Latest Available Payload)

### Counts
- Active: HF `34`, Non-HF `38`
- Closed: HF `433`, Non-HF `3067`

### Unrealized (Active) — HF vs Non-HF by Asset Class

- **HF**
  - CRYPTO: n=29, WR=17.24%, avg=+0.0762%, sum=+2.2099%
  - EQUITY: n=4, WR=50.00%, avg=+1.6730%, sum=+6.6920%
  - FOREX: n=1, WR=0.00%, avg=-0.5012%, sum=-0.5012%

- **Non-HF**
  - CRYPTO: n=30, WR=23.33%, avg=-0.0975%, sum=-2.9238%
  - EQUITY: n=8, WR=0.00%, avg=-0.3082%, sum=-2.4654%
  - FOREX: n=0 in non-HF active snapshot

### Realized (Closed) — HF vs Non-HF by Asset Class

- **HF**
  - CRYPTO: n=433, WR=60.97%, avg=+0.7095%, sum=+307.2170%
  - (No HF-labeled non-crypto closed rows in this snapshot path)

- **Non-HF**
  - CRYPTO: n=2365, WR=49.05%, avg=+0.3677%, sum=+869.6099%
  - EQUITY: n=516, WR=36.05%, avg=-0.6828%, sum=-352.3329%
  - FOREX: n=159, WR=33.33%, avg=-0.2280%, sum=-36.2599%
  - COMMODITY: n=12, WR=8.33%, avg=-1.4753%, sum=-17.7031%
  - ETF: n=12, WR=41.67%, avg=-0.9511%, sum=-11.4127%
  - FUTURES: n=3, WR=0.00%, avg=-0.4489%, sum=-1.3467%

---

## Plain-English Interpretation

- **Crypto unrealized:** HF slightly positive on avg pnl; non-HF slightly negative.
- **Crypto realized:** HF clearly stronger than non-HF on WR and avg pnl.
- **Non-crypto realized:** currently negative in non-HF buckets in this snapshot; HF non-crypto closed coverage is not yet present in reliable volume.

---

## Repro Instructions (Independent Agent)

1. Confirm strict cutoff:
   - `git log --since="today 00:00" --date=iso --pretty=format:"%H|%ad|%s" -n 1`
2. Confirm payload recency:
   - read `audit_trail/data/dashboard_payload.json` -> `generated_at`
3. Load:
   - `picks.active`
   - `picks.recent_closed`
4. HF tagging logic:
   - if row has `hf_conviction_tier`/`conviction_tier`, use it
   - otherwise classify via `alpha_engine.conviction_stack.classify_hf_conviction_tier`
5. Aggregate matrix:
   - dimensions: `{HF, Non-HF} x {asset_class} x {unrealized, realized}`
   - metrics: `n`, `n_numeric_pnl`, `win_rate`, `avg_pnl_pct`, `sum_pnl_pct`
6. Output:
   - strict window result
   - fallback snapshot result (if strict is empty)

---

## Optimization / Code-Review Targets

1. **HF stamping parity**
   - Ensure HF tier stamping applies to `recent_closed` consistently, not only active.
2. **Statistical significance gating**
   - Add minimum sample checks and significance tests before "HF beats Non-HF" claims:
     - two-proportion z-test on win rate
     - CI reporting (Wilson intervals)
3. **Canonical payload block**
   - Add `summary.hf_performance_by_asset` computed server-side.
4. **Data lag visibility**
   - Add metadata field for "last code change vs payload generated_at lag".
5. **Action policy**
   - If sample too small, emit explicit "waiting for more data" status in summary/updates.

---

## Pending Note (Current Status)

We are currently **waiting for post-change data** to evaluate strict "since last code change today" performance, because payload generation time predates the code-change cutoff.

---

## External Review Reconciliation (Xiomi Claw)

This section reconciles external feedback with this handoff and sets execution priorities.

### What we agree with (high confidence)

- **Methodology quality:** strict-vs-fallback timeframe handling is correct and reproducible.
- **Core data-lag problem:** strict post-change attribution is impossible when payload `generated_at` predates the code-change cutoff.
- **Crypto signal quality:** HF appears materially stronger than non-HF in crypto on realized metrics.
- **HF parity gap:** HF tagging/stamping must be consistent for `recent_closed`, not only active.
- **Statistical guardrails needed:** non-crypto buckets are underpowered; confidence intervals/tests and minimum-`n` policy are required.

### Known risk points to validate explicitly

- **Classifier parity risk:** ensure `classify_hf_conviction_tier(...)` output matches stored tier fields where both exist.
- **Closed non-crypto HF scarcity:** determine if this is true strategy behavior vs. missing/stale tier stamping.
- **Metric interpretation risk:** do not over-weight `sum_pnl_pct` without also reporting mean/median/dispersion and sample size.

---

## Immediate Execution Checklist (for validating agent)

1. **Reproduce snapshot metrics**
   - Recompute counts and performance matrix from `dashboard_payload.json`.
   - Confirm values match this handoff (or document snapshot drift if payload changed).

2. **HF classifier parity audit**
   - On rows where `hf_conviction_tier` exists, re-run `classify_hf_conviction_tier`.
   - Produce mismatch report: count, percentage, and examples.

3. **Closed-pick HF backfill simulation**
   - Run classifier on `picks.recent_closed` in dry-run mode.
   - Report newly-HF-tagged counts by asset class and expected impact on comparisons.

4. **Add statistical confidence block**
   - For each asset class and HF/non-HF cohort, add:
     - win-rate CI (Wilson; Clopper-Pearson for tiny `n`)
     - mean pnl CI (bootstrap)
     - HF vs non-HF tests (win-rate and mean pnl)
     - effect size
   - Enforce `insufficient_data` when `n < min_n` (recommend `min_n = 10`).

5. **Publish canonical payload summary**
   - Add `summary.hf_vs_nonhf` (and optionally rollups) so consumers do not recompute ad hoc.

6. **Add lag/version metadata**
   - Add fields such as:
     - `metadata.payload_generated_at`
     - `metadata.last_code_change_sha`
     - `metadata.last_code_change_at`
     - `metadata.payload_lag_seconds`
     - `metadata.repo_sha`

---

## Decision Policy Until Fixes Land

- Treat **crypto HF vs non-HF** as the only currently actionable comparison.
- Treat **non-crypto HF conclusions** as provisional/monitor-only until sample size and tagging parity improve.
- Do not publish "HF beats non-HF" claims without confidence intervals and minimum-`n` checks in payload.

---

## Canonical Truth Set (Forensics Reconciliation Lock)

- `_classify_non_crypto_hf_tier(...)` exists in the current working tree and is invoked; conflicting reports are attributed to branch drift / stale snapshots.
- Config-gated non-crypto controls now exist in policy surface (`non_crypto`, `policy_flags`) and are wired to scoring gates.
- Direction-aware conviction scoring is implemented in `conviction_stack` behind `enable_direction_aware_conviction_v2` and defaults OFF.
- Payload metadata now includes code/policy anchors and lag fields for post-change slicing.
- Remaining high-priority work is telemetry fidelity and concentration/probation evidence quality, not missing core plumbing.

### Locked Backlog Priority

- **P0 (integrity/crash):**
  - Ensure no undefined-variable/order-of-evaluation paths in payload generation.
  - Keep all new controls fail-open when disabled.
- **P1 (risk/gating):**
  - Concentration/probation controls for `symbol×strategy` and `strategy×system` exposure (config-gated).
  - Explicit probation/quarantine counters in dashboard payload.
- **P2 (calibration/optimization):**
  - Asset-class composite weighting and direction-aware activation only after evidence gates pass.
  - Further threshold tuning deferred until sufficient realized sample.

---

## Rollout Plan (Locked)

### Day 0 (conservative defaults)

- Enable:
  - `enable_non_crypto_throughput_v2=true`
  - `enable_goldmine_floor_v2=true`
- Keep disabled:
  - `enable_direction_aware_conviction_v2=false`
  - `enable_asset_class_ml_composite_v2=false`
  - `disable_non_crypto_ml_null_penalty_v2=false`
  - `enable_concentration_probation_v2=false` (or `true` only in `mode=tag`)
- Set and preserve anchor timestamps:
  - `metadata.last_policy_change_at`
  - `metadata.last_code_change_at`
  - `metadata.payload_lag_seconds`

### Day 7 (first promotion checkpoint)

- Evaluate realized 7-day window anchored to `last_policy_change_at`.
- Promote one higher-impact flag only if strict gate passes:
  - `n >= 30`
  - `PF >= 1.1`
  - `WR >= 50%`
- If failed: keep flag OFF, record "waiting for more data".

### Day 14 (second checkpoint)

- Re-evaluate same strict gate on updated realized window.
- Consider enabling next flag (direction-aware or asset-composite) only if gate passes and no risk regression in concentration/probation telemetry.

---

## Strict Evidence Gate (Promotion to Higher-Risk Flags)

- Window: realized 7-day slice anchored to `last_policy_change_at`.
- Minimum sample: `n >= 30`.
- Profitability floor: `PF >= 1.1`.
- Consistency floor: `WR >= 50%`.
- Significance notes required in handoff: CI + test result + effect size (or explicit insufficient-data state).

---

## Residual Risks

- Non-crypto HF realized cohorts can remain underpowered; false confidence risk persists without sample-size guardrails.
- Payload recency lag can still make "since last code change" slices empty; metadata now exposes this but does not solve upstream cadence by itself.
- Concentration tagging in `mode=tag` does not actively de-risk until switched to `mode=exclude`.

---

## Defer List (Needs More Data)

- Hard activation of direction-aware conviction across all assets.
- Asset-class-specific composite weighting as default behavior.
- Aggressive non-crypto cap expansion beyond conservative throughput settings.
- Automatic kill/probation escalation rules without 7-day strict-gate evidence.

