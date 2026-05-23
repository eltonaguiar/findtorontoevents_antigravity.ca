# Session CD Review — 2026-05-18

## Context
Continuation of PATH_TO_PROVEN_EDGE. This session finalized M-108 by incorporating peer agent
(`tools/edge_stability_harness.py`) findings that showed `confidence` has sign-split across
walk-forward windows — triggering the M-108 v2 formula update.

## Session deliverables

### 1. M-108 v2 Formula Fix (PRIMARY DELIVERABLE)
- File: `alpha_engine/strategy_wr_ranker.py` (commit d4a07d32e9)
- **Change:** Dropped `confidence` from composite rank formula
  - Old (M-108 v1): `0.50 * strategy_rolling_wr + 0.30 * ml_composite + 0.20 * confidence`
  - New (M-108 v2): `0.70 * strategy_rolling_wr + 0.30 * ml_composite`
  - Fallback (no strategy history): `1.0 * ml_composite` (was `0.60 * ml + 0.40 * conf`)
- **Why:** Both harnesses agree confidence is inadmissible:
  - Our walk-forward harness: confidence eff=0.174 (WEAK, below 0.30 floor)
  - Peer harness (`edge_stability_harness.py`): confidence effs across 5 windows = [-0.52, -0.52, -0.04, +0.48, +0.69] — sign-split (3 negative, 2 positive), REJECTED
- **Tests:** 14 tests passing (updated `test_fallback_when_no_strategy_history`: expected 0.7 not 0.74)

### 2. Peer Harness Additional Finding: risk_reward is anti-signal
- Peer harness shows `risk_reward` eff = [-1.07, -0.25, -0.11, -0.49, -0.11]
- Consistently negative across ALL 5 windows (mean eff ≈ -0.41)
- Interpretation: higher risk_reward picks are LOSING more often than lower ones
- This is the opposite of what you'd expect — possibly a data artifact or measurement issue
- **Not yet acted on** — needs investigation before adding to quality gates

### 3. H-001 COT Allocation Cap (confirmed from session CC)
- `reports/hypothesis_registry.json`: H-001 `recommended_allocation_pct` 17.0 → 10.0
- Rationale: CT=F single-commodity concentration risk (87.1% of COMMODITY picks are CT=F)
- Quarter-Kelly says 17%, but cap overrides to 10% due to concentration risk

### 4. Strategy Block Expiry Audit (M-109, confirmed from session CC)
- `tools/research/strategy_block_expiry_audit.py` — committed 5d4151db3b
- Live result: 83 EXPIRED (>90d without documented review), 15 ACTIVE
- Does NOT modify quality_gates.py — audit only

### 5. Cross-PC Protocol
- Custom PEER_MESSAGE "hey its CLAUDE 1 from eltons laptop" sent to all peers (message_id=d2c2774d)
- Gateway healthy at 192.168.2.32:8788, 2 peers registered
- Laptop LAN auto-discovery is dead (WinError 10013 UDP), must explicitly target desktop IP

## Review questions

1. **M-108 v2 formula weights (70/30):** Is 70% strategy_rolling_wr the right weight now that
   confidence is dropped? Or should it be 80/20 (more aggressive on the proven signal) or 60/40
   (more conservative)? The only live evidence is: cot_positioning WR=78.4% (n=134),
   cftc_cot_commercial WR=74.8% (n=131). Both are COMMODITY. For EQUITY/CRYPTO strategies
   with n close to MIN_N=10, the WR estimate is noisier — does 70% overweight a noisy signal?

2. **risk_reward anti-signal finding:** The peer harness shows risk_reward eff is consistently
   negative (mean ≈ -0.41). Should we:
   a) Add a `risk_reward` cap to quality_gates.py (e.g., block picks where risk_reward > 3.0)?
   b) Add it as an INVERSE signal component in rank_score (lower risk_reward → higher rank)?
   c) Investigate the measurement first (is this a data artifact from how risk_reward is calculated
      for different asset classes)?
   d) Ignore for now (don't add inadmissible signals even if negative)?

3. **83 expired strategy blocks:** MomentumEMA (blocked since 2026-01-01, est.) and
   volume_spike_breakout (same) are the oldest. Should we:
   a) Auto-archive strategies blocked >180 days without any live activity?
   b) Keep requiring manual review per STRATEGY_INVESTIGATION_BEFORE_KILL.md?
   c) Add a scheduled workflow that pings operators weekly with expired block counts?

4. **MIN_N=10 vs strategy WR noise:** At n=10 (the minimum), a 7/10 WR is 70% but the 95% CI
   is [35%, 93%]. We're weighting this at 70% in rank_score. Is MIN_N too low? Should it be
   20 or 30? Counterargument: with MIN_N=20, only cot_positioning and cftc_cot_commercial
   qualify (n=134 and n=131), and all other strategies fall back to ml_composite. Is that the
   right trade-off?

5. **No action yet on futures_momentum (WR=2%, n=202):** Operator approval is required to block.
   In the meantime, is there a LOWER-RISK step we can take? For example:
   a) Add a soft-cap: futures_momentum picks get m108_rank_score forced to 0.0 (bottom of list)
   b) Add to shadow-track list (M-075) and monitor for 30 days
   c) Wait for operator decision (current state)

## Commits this session (CD)
- d4a07d32e9: fix(M-108 v2): drop confidence from rank composite — eff=0.174 WEAK/sign-split
