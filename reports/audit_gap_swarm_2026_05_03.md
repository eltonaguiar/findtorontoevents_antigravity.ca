# Audit Gap Swarm Review - 2026-05-03

## Scope

Compared two Kimi Prediction Edge Audit attachments against current repo evidence for `findtorontoevents.ca/audit`.

Smoke prompt: `swarm_runs/audit_attachment_smoke_prompt_2026_05_03.md`

Gap prompt: `swarm_runs/audit_gap_research_prompt_2026_05_03.md`

## Swarm Health

Attachment smoke test:

- `copilot`, `inception` (Mercury), and `xai` (Grok) produced substantive raw responses after runner fixes.
- Inspector still marked prose smoke responses as `PARSE_FAILED` because the smoke prompt was not the review JSON schema.

Gap research swarm:

- Healthy JSON outputs: `deepseek`, `inception` (Mercury), `xai` (Grok).
- Failed or zero outputs in the original 5-engine run: `copilot` on the larger JSON prompt, `cerebras` due missing `cerebras-cloud-sdk`.
- Follow-up Copilot retry after bypassing the Windows `.cmd` shim produced substantive raw commentary but still failed JSON schema parsing. Treat it as corroborating commentary, not a schema-valid vote.
- Artifacts: `swarm_runs/audit_gap_research_2026_05_03/`.
  Copilot retry artifact: `swarm_runs/audit_gap_research_2026_05_03_copilot_retry2/`.

## Consensus Gaps

Labeling note: the structured consensus below is from 3 healthy JSON outputs out of the original 5-engine gap run (`deepseek`, Mercury/Inception, Grok). Copilot later corroborated the same gap cluster in raw malformed-JSON commentary; Cerebras remained unavailable.

### P0 - R:R Policy Drift

The prior Kimi report says R:R `1.5-2.0` is the golden zone and `>2.0` is dangerous. Current `audit_dashboard/template.html` says crypto R:R `>=2.0` is highest PF, while a nearby footnote says R:R `>=1.5` underperforms every asset class.

Backend gates also remain permissive:

- `audit_trail/forward_test_gates.py`: `MIN_RR = 1.2`
- `audit_trail/forward_test_gates.py`: `GateFilter.MIN_RR = 1.2`
- No hard `R:R <= 2.0` ceiling was found in that gate.

Action: reconcile Guide copy with current data, then make backend gates match the chosen policy.

### P0/P1 - ML Score Threshold Drift

The prior attachment says the ML threshold should be verified around `0.90`. Current gate code uses:

- `MIN_ML_SCORE = 0.50`
- `GateFilter.MIN_ML_SCORE = 0.50`

Action: verify current closed-pick performance by ML-score bucket before raising globally; if the `0.90` claim still holds, gate and Guide should be updated together.

### P1 - Verified Alpha / High Conviction Are Not Fully Wired

`audit_trail/feed_membership.py` shows:

- `VERIFIED_ALPHA_SOURCES = {"claws_of_doom"}` only.
- `evaluate_hc_tier()` explicitly labels its thresholds as placeholders.
- Parity with `audit_dashboard/hc_filter.js` is deferred to Phase 3.

Action: complete parity testing and either expand verified sources with evidence or add UI caveats that these feeds are not yet broad empirical guarantees.

### P1 - UNKNOWN Asset Class Resolver Risk

Current `dashboard_data.json` includes:

- `UNKNOWN`: WR `60.0`, PF `4.59`, status `insufficient_data`.

But `alpha_engine/outcome_resolver.py` falls back to crypto-tight `PNL_WIN_THRESHOLD_DEFAULT = 0.00001` for unknown classes.

Action: inspect the UNKNOWN picks and reclassify them or apply conservative non-crypto thresholds before treating their PF/WR as edge.

### P1 - Forex Halt Not Reflected In Current Evidence

Current asset health shows FOREX:

- WR `46.3`
- PF `0.27`
- total PnL `-987.03`
- status `stressed`

The prior report recommended halting Forex, but no Forex-specific halt was evident in the supplied gate evidence.

Action: either implement a hard Forex block/quarantine gate or document why mutate-before-kill remains active despite the current drawdown.

### P2 - UEPS Closed Picks Are Stubbed

The UEPS nested-comment issue appears mitigated in `audit_dashboard/template.html`, but the UEPS client still contains:

- `const closedPicks = []; // closed UEPS picks not yet emitted; stub for filter`

Action: populate real UEPS closed-pick data or hide/caveat the closed UEPS tab until it exists.

### P2 - Tier Card Data Consistency

The swarm flagged two `tier2_proven_strategies` inconsistencies:

- `signal_validation`: `is_strict_tier2: True` but `thin_sample: True`.
- `claude_gainer`: total PnL positive while the 90d sparkline ends deeply negative.

Action: verify whether these fields use different windows or if the sparkline/card generation is mixing incompatible cumulative bases.

## Claims To Downgrade Until Reverified

- R:R `1.5-2.0` as PF `5.81` golden zone.
- Global ML score threshold `>=0.90` as safe without per-asset revalidation.
- `trust_score >= 5` as `68-71%` WR unless current data still proves it.
- Meme coin `99.7%` risk-of-ruin claim unless current source data and formula are present.
- "Equity only safe edge" as a blanket statement, because current asset health also shows commodity PF `1.78` and bond PF `1.72` with important caveats.
