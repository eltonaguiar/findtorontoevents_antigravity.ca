# Hedge-Fund Enhancements Implementation Explainer (2026-04-09)

This document explains every code file modified to implement the pending Hedge-Fund Enhancements Plan todos, what changed, and why each change should improve system quality and risk-adjusted outcomes.

## Scope

Implemented todo coverage:

- `breadth-recovery`
- `active-pass-watchlist`
- `score-tier-validation`
- `claude-gainer-audit`
- `fast-stocks-decision`
- `choppy-regime-model`
- `super-signals-anomaly`
- `forex-sleeve-cap`
- `equity-concentration-risk`
- `rapid-fire-upweight-study`
- `kimi-condition-mining`
- `redis-peer-loop`
- `engine-hit-list-2026-04`

---

## 1) `alpha_engine/elite_scorer.py`

### What changed

- Added a **confidence-score coherence guard**:
  - if `elite_score < 10` and score health is `DATA_MISSING`, effective confidence is clamped.
  - emitted diagnostics in breakdown (`_confidence_effective`, `_confidence_clamped`).
  - exposed `confidence_effective` in scorer output.
- Added **equity macro cap logic**:
  - for equity-like assets (`EQUITY`/`STOCK`/`ETF`), if macro flags are bearish (`equity_macro_ok == False`, bearish `spy_trend`, or elevated `vix > 30`), cap final score at 60.

### Why it was changed

- Removes pipeline inconsistency where low/empty evidence still appeared with high confidence.
- Integrates equity macro risk into conviction routing rather than relying on downstream-only blocking.

### Expected benefits

- Fewer false high-conviction picks from broken/empty evidence paths.
- Lower probability of equity conviction entries during macro-hostile periods.
- Better transparency for debugging via explicit coherence flags.

---

## 2) `alpha_engine/smart_picks_engine.py`

### What changed

- Added `fast_stocks_competition` to `BANNED_SYSTEMS`.
- Tightened FOREX non-crypto policy confidence band:
  - from `0.55-0.75` to `0.80-0.92`.
- Added ML composite/fallback penalties for:
  - `claude_gainer*` strategies (discounted score),
  - blocked weak trust tiers (`SANDBOX`, `UNTRUSTED`, `UNPROVEN`, `DEMOTED`).
- Added forex bypass protection:
  - if a row is classified as FOREX but symbol is not an actual FX pair, block with `forex_symbol_mismatch`.
- Added CHOPPY direction-score handling:
  - `choppy_tight` = very low direction contribution,
  - `choppy_wide` = partial directional contribution.
- Added `rapid_fire` proven-system boost floor.
- Added `kimi_riseoftheclaw` condition gate:
  - crypto-only and minimum forward WR evidence.
- Added breadth-recovery budget logic:
  - non-crypto budget expands/contracts based on latest governance report pass-rate and non-crypto rollup.
- Added equity concentration control:
  - if fewer than 2 validated equity systems exist, cap per-system equity contribution to 1 pick.
- Normalized regime mapping so choppy states are interpreted consistently.

### Why it was changed

- Enforces sleeve governance directly inside selection.
- Reduces synthetic inflation pathways and weak-tier promotion.
- Prevents asset-class proxy bypasses.
- Aligns pick construction with concentration/risk-budget goals.

### Expected benefits

- Cleaner high-conviction cohort quality.
- Lower single-system fragility in equity sleeve.
- Stronger forex sleeve integrity.
- Controlled non-crypto breadth recovery without immediate quality dilution.

---

## 3) `alpha_engine/regime_detector.py`

### What changed

- Added CHOPPY sub-regimes:
  - `CHOPPY_TIGHT`
  - `CHOPPY_WIDE`
- Adjusted regime confidence for these choppy states.
- Updated direction suggestion:
  - choppy/mean-reverting states default to `BOTH` instead of forcing trend direction.
- Updated strategy compatibility map to include choppy states for mean-reversion-style strategies.

### Why it was changed

- Existing `CHOPPY/NEUTRAL` behavior was too coarse and reduced discriminative scoring power.

### Expected benefits

- Better regime granularity for downstream scoring.
- Reduced trend-overconfidence in range markets.
- Cleaner strategy-to-regime alignment.

---

## 4) `alpha_engine/mtf_gate.py`

### What changed

- Added fallback OHLCV path using CryptoCompare when Binance mirrors are unavailable/blocked.
- Applied fallback per timeframe (`1h`, `4h`, `1d`) inside MTF alignment checks.

### Why it was changed

- Binance geo-block/unavailable states disabled MTF confirmation, removing a key quality gate.

### Expected benefits

- Higher gate uptime across regions/environments.
- Less silent degradation of the MTF signal.

---

## 5) `alpha_engine/ensemble_gate.py`

### What changed

- Added `spot_proxy` sub-signal:
  - uses spot 24h change/volume behavior when funding/OI futures endpoints are unavailable.
- Integrated this proxy into market-structure confirmation when both funding and OI are absent.

### Why it was changed

- Binance futures dependencies could leave ensemble market-structure blind in blocked environments.

### Expected benefits

- More resilient ensemble gate behavior under exchange API constraints.
- Fewer false "no data" cases in confirmation logic.

---

## 6) `tools/hf_enhancement_review.py`

### What changed

- Added enhanced-profile pass classifier and active pass watchlist metrics:
  - pass count/rate,
  - top symbol/system/asset-class concentration shares,
  - guardrail checks (6-15% pass rate, symbol concentration <= 30%).
- Added score-tier validation:
  - monotonicity checks across buckets (`<30`, `30-49`, `50-69`, `70+`) for WR and avg PnL.
- Added strategy diagnostics:
  - `claude_gainer_audit` (fixed-TP clustering),
  - `fast_stocks_decision` (retire/de-risk signal),
  - `rapid_fire_upweight_study`,
  - `kimi_condition_mining` (asset class x direction conditions).
- Added non-crypto rollup and breadth-recovery state outputs.
- Added additional manager monitor flags from new diagnostics.

### Why it was changed

- Needed operational outputs for newly added governance todos and review cadence.

### Expected benefits

- Stronger governance visibility and faster intervention loops.
- Better evidence for scaling/de-risking decisions by sleeve/system.

---

## 7) `tools/run_hf_weekly_verify.py`

### What changed

- Added validation for:
  - enhanced pass-rate guardrail (6-15%),
  - pass-set symbol concentration limit,
  - score-tier monotonicity checks.
- Added remediation-task generator:
  - writes structured actions to `audit_trail/data/hf_remediation_tasks.json` on failure.

### Why it was changed

- Weekly verification needed to evolve from pass/fail logging into actionable governance output.

### Expected benefits

- Faster follow-through after failed targets.
- Consistent, machine-readable remediation workflow.

---

## 8) `tools/bus_post_hf_governance_cycle.py`

### What changed

- Expanded Redis payload snapshot to include:
  - `active_pass_watchlist`,
  - `score_tier_validation`,
  - `strategy_diagnostics`.
- Added explicit peer validation requests:
  - tier bypass controls,
  - stale docs cleanup,
  - sleeve cap bypass checks.

### Why it was changed

- Governance loop needed richer cycle payloads and targeted peer directives.

### Expected benefits

- Better cross-agent coordination quality.
- Reduced blind spots during multi-agent governance review.

---

## Runtime verification evidence

- `python -m py_compile ...` on all modified Python modules: **PASS**
- `python tools/run_hf_weekly_verify.py ...`: executed successfully and produced expected policy failure output based on current live metrics; remediation tasks written.
- `python tools/bus_post_hf_governance_cycle.py ...`: **published OK**.

---

## Net expected portfolio impact

- Better integrity for high-conviction scoring and routing.
- Stronger concentration control and sleeve-level governance.
- Higher resilience under external API availability failures.
- Improved observability and weekly remediation discipline.
- Safer path to non-crypto breadth recovery with explicit rollback signals.
