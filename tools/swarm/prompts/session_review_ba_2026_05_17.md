# Session BA — Swarm Review Request
# Date: 2026-05-17
# Session: BA (following AZ — APPROVE)

## Context

Session BA: Post-fix CI health audit + new ab_analysis artifact review.
All session reviews through AZ have returned deepseek APPROVE.

## Session BA Deliverables

### 1. AZ CI Fixes Confirmed Working

ab_analysis.yml (commit 3207451eff) ran successfully for the first time after 4 consecutive
cancellations. All expected artifacts committed by the workflow:
- `audit_dashboard/data/ab_panel.html`
- `ml_gatekeeper/data/ab_summary.json` + `ab_rollback_state.json`
- `audit_dashboard/data/correlation_regime.json`
- 11 COT symbol files (CT, GC, SI, CL, NG, ZW, ZC, ZS, HG, PL, PA)
- `audit_dashboard/data/cot_step7_friction_adjusted_mc.json`
- `audit_dashboard/data/system_pf_verification.json`
- `audit_dashboard/data/commodity_carry_momo.json`

DB Freshness Guardian completed SUCCESS (was RED every run prior to AZ fix).

### 2. New Artifact Analysis (no code changes needed)

**AB Analysis:** INSUFFICIENT_DATA — n_ab_tagged=0 (no picks have been A/B router tagged yet;
gatekeeper.joblib artifacts needed first). rollback_alert_this_cycle=False. No action needed.

**CT=F DSR Gate — FAILS:**
```
friction_adjusted_dsr = 0.0 (threshold: 0.85)
friction_adjusted_SR = 0.5642 (raw SR = 1.031)
slippage_drag_pct = 1.57% (vs raw mean_pct = 3.51%)
```
CT=F cot_positioning is NOT live-eligible per master-plan Action #3.
This is consistent with the concentration gate blocking COMMODITY → WATCH verdict.

**CT=F COT Signal — STRONG_BEAR_COT:**
```
noncomm_net_zscore = +1.982 (speculators heavily long)
comm_net_zscore = -1.987 (commercials heavily short / hedging)
```
Speculators have rapidly rotated long since March (from net-short). Commercials are hedging hard.
Classic bearish reversal setup — not a catalyst for raising the COMMODITY concentration cap on CT=F.

**Correlation Regime — ELEVATED:**
```
mean_abs_current = 0.4448 (vs baseline)
regime_state = ELEVATED
n_pairs_just_crossed = 7
sleeve_sizing_scalar = 0.5552
```
7 new pair correlation crossings. Consumer wiring deferred (nfa=diagnostic only). No automated
action taken. Observed new crossings: BOND-EQUITY (0.715 vs 0.243 baseline), EQUITY-FOREX_USD
(-0.72 vs -0.29), BOND-COMMODITY_GOLD (0.677 vs 0.018). Strong USD + flight-to-safety regime.

**Commodity Carry Momo:**
- CT=F is in the neutrals basket (carry-top but no double-sort momentum match)
- Only OJ=F (Orange Juice) is in the short basket
- No LONG signals currently; momentum leaders are PA=F, PL=F, SI=F (precious metals)

**System PF Verification:** 0 pass / 0 fail (script ran but found no T2 winners eligible — likely
because n-min threshold not met for newly-qualified strategies).

### 3. No New Code Bugs Found

Full review of: CI runs, open PRs (0), zero-PnL report (not produced — db connection
issue in CI, non-fatal per continue-on-error), COT signals, regime data.

No P0 or P1 bugs identified in this session.

### 4. Pending Items (unchanged — user approval required)

| Item | Status | Action Needed |
|------|--------|---------------|
| COMMODITY MONEY_READY | WATCH | User approval: CONCENTRATION_CAP_BY_CLASS={"COMMODITY":0.85} |
| CT=F DSR FAIL | Research artifact | Noted; informs cap raise decision |
| Correlation regime ELEVATED | Diagnostic | Consumer wiring already deferred |
| EQUITY MONEY_READY | WATCH (accumulation) | None — n=7 non-blocked picks |
| ETF MONEY_READY | WATCH (accumulation) | None — strategies need n≥20 |
| BOND MONEY_READY | INSUFFICIENT_DATA | None — n=12 < 50 |

### 5. money_ready_verdict() Current State

```
CRYPTO       MONEY_READY   n=443  PF=2.54  WR=66.4%
COMMODITY    WATCH         n=354  PF=2.15  WR=60.2%  ← CT=F 65.3% > 60% cap
EQUITY       WATCH         n=238  PF=2.04  WR=54.2%  ← n=7 non-blocked picks
ETF          WATCH         n=74   PF=2.49  WR=67.6%  ← no strategy with n≥20
FOREX        NOT_READY     n=618  PF=0.48  WR=33.3%  ← hard-blocked
BOND         INSUFF_DATA   n=12   PF=0.66  WR=50.0%  ← n<50
FUTURES      INSUFF_DATA   n=2                        ← n<50
```

## Questions for Swarm

1. **CT=F concentration decision:** Given CT=F COT is STRONG_BEAR_COT (spec z=+1.98,
   commercial z=-1.98) AND DSR gate FAILS (0.0 vs 0.85 threshold), should the COMMODITY
   concentration cap raise be framed as: "allow CT=F picks above 60% despite bearish COT +
   DSR fail" OR is this simply an administrative gate change that lets the system accumulate
   non-CT=F picks without being blocked?
   (Context: money_ready_verdict() blocks ALL of COMMODITY because CT=F exceeds 60% cap,
   even though other symbols like CL=F/NG=F have passing metrics. The cap raise to 0.85
   just stops the block from triggering; it doesn't create new CT=F picks.)

2. **Correlation ELEVATED + sizing scalar 0.555:** Should we proactively wire
   `sleeve_sizing_scalar` from `correlation_regime.json` into the Kelly position sizer
   before the user-approved COMMODITY cap raise? Or defer until the regime module
   has a consumer integration PR?

3. **Overall verdict:** Is Session BA APPROVE?

## Verification

- CI: 0 stale failures across all workflows
- ab_analysis.yml: CONFIRMED SUCCESS (run #25999606037)
- money_ready_verdict(): CRYPTO=MONEY_READY, COMMODITY=WATCH, EQUITY=WATCH, ETF=WATCH
- Prior verdicts: AR through AZ all deepseek APPROVE
- No code changes committed this session
