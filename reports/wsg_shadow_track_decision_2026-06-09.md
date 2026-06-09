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

## GUARDRAIL #5 EXECUTED (2026-06-09, live trading_picks) — AMENDS the decision
Direct re-validation **does NOT confirm** the swarm's "clean divergent COMMODITY edge" premise:
- **FUTURES-class `futures_momentum`: n=0** resolved rows in current `trading_picks` — the
  "0% WR on 56 closed" kill cohort is no longer present (it lived in a different table/snapshot),
  so the FUTURES-vs-COMMODITY "distinct cohort" claim can't be confirmed against live data.
- **COMMODITY-class `futures_momentum`: n=2029, WR 42.0%** (symbols CT=F,GC=F,HG=F,KC=F,NG=F,
  PL=F,SB=F,SI=F,ZC=F,ZS=F,ZW=F; 2026-03-26..06-05) — **sub-coin-flip in bulk**. The encouraging
  intrabar "n=57, WR 63%, PF 2.68" is only **2.8% of the 2029 raw trades** — a small subset, not
  a divergence the bulk supports.

**Amended verdict:**
- `futures_momentum` → **HOLD (do NOT shadow-track yet).** First investigate WHY the 57-row
  intrabar subset (63%) diverges from the 2029-row bulk (42%) — recency? single-symbol? resolver
  subset bias? Resurrecting on a 2.8% subset would repeat the "small-n artifact" trap.
- `forex_rsi2_mean_reversion` → shadow-track remains **more defensible** (it was a *blanket*
  FOREX-block casualty, never strategy-specifically killed) — but n=19 intrabar is tiny; treat as
  low-priority shadow with the same auto-expire guardrails.

## Status
DECISION recorded + guardrail #5 executed. NET: shadow-track is **NOT activated** — futures_momentum
is on HOLD pending subset-divergence investigation; forex_rsi2 is a low-priority defensible shadow.
This is the "investigate before resurrect" discipline working. Swarm output: `swarm_runs/wsg_unban_2026-06-09/`.
