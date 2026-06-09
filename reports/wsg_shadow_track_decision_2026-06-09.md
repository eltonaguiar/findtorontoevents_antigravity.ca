# WS-G: Forward-Track Blocked Leads — Swarm Decision (2026-06-09)

**Question:** should two BLOCKED but intrabar-promising strategies be un-banned into the
SHADOW lane (`forward_test_only=1`, never sized, excluded from the money-ready DSR/PBO verdict)
to grow honest n for a future evidence-based sizing decision?

## Verdict: **YES shadow-track BOTH** (deepseek + gemini unanimous; xai pending = decisive)
- **`futures_momentum` (COMMODITY)** — YES. The 2026-05-06 kill (0% WR, n=56) + H-005 re-block
  were on the **FUTURES** asset_class; the **COMMODITY** cohort (n=57, WR 63%, PF 2.68) is a
  divergent, never-tested cohort. Shadow = zero capital risk; grows n toward the 100 threshold.
- **`forex_rsi2_mean_reversion` (FOREX)** — YES. It was a casualty of the *blanket* FOREX
  consolidation (PR #6, all FOREX blocked except cta_cross_asset_tsmom SHORT), not a
  strategy-specific kill. Intrabar n=19, WR 63%, PF 2.43.

The narrow "blocked-but-shadow-track" allowlist mechanism (only these two emit as shadow; all
other blocked strategies stay fully blocked) was endorsed as sound.

## Required guardrails (consensus — MUST ship with the implementation)
1. **Auto-expire / kill-switch:** after +30–50 additional shadow trades, if forward WR < 50%
   OR PF < 1.2 → re-block permanently (shadow lane is for measurement, not hope).
2. **Cap shadow n** (deepseek: 200; gemini: +50 OOS) → re-block if not money-ready by the cap.
3. **Irreversible tagging:** every emitted pick carries `forward_test_only=1` +
   `shadow_origin="resurrected_blocked"` so it can NEVER be picked up for sizing.
4. **Clear dashboard labeling:** "SHADOW — NO CAPITAL — PRE-VALIDATION" (red), distinct from live.
5. **PREREQUISITE — re-validate the `futures_momentum` kill basis** before enabling: confirm the
   FUTURES-class kill cohort (n=56, 0% WR) is genuinely distinct from the COMMODITY cohort
   (different instrument list / timestamp source), not the same trades re-labeled. Do NOT enable
   shadow-track until this is confirmed.

## Implementation spec (deliberate follow-up — NOT rushed; emission-path change)
```
SHADOW_TRACK_STRATEGIES = {"futures_momentum", "forex_rsi2_mean_reversion"}  # blocked-but-shadow
```
- At the emission gate: if `is_strategy_blocked(strat, ac)` AND `strat in SHADOW_TRACK_STRATEGIES`
  → DO NOT reject; instead emit with `forward_test_only=True, shadow_origin="resurrected_blocked"`.
  All OTHER blocked strategies are still rejected entirely.
- The Option-A shadow lane already: bypasses the per-class sized cap (`is_daily_cap_reached(...,
  forward_test_only=True)`) and is excluded from the sized count — so shadow picks build n
  without contaminating the verdict. (Verdict/DSR cohort must also exclude `forward_test_only`.)
- Add the auto-expire + n-cap checks (guardrails 1–2) at the emit point or a nightly monitor.
- Coordinates with DeepSeek WS3 (emission queue) — the shadow lane is the natural home for these.

## Status
DECISION recorded. Implementation is **gated on guardrail #5 (kill re-validation)** + building the
auto-expire/cap monitor. Swarm output: `swarm_runs/wsg_unban_2026-06-09/`. Leads already documented
in `intrabar_truth_by_class.json` (t2_shaped_strategy_leads) + `registry_block_verification_2026-06-09.md`.
