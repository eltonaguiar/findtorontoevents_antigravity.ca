# Per-Asset-Class Current → Ideal Algorithm — 2026-05-17

Generic improvement algorithm per asset class: VERIFIED current state → IDEAL
state → the concrete path. Grounded in this session's independent verification
(2 recomputation subagents + repo cross-checks), NOT in any single AI auditor's
unverified pitch. Corrects two fantasy items repeated across AI reports:
**(a)** inverse-edge is NOT `1/PF` — needs a friction-costed backtest;
**(b)** no "institutional grade NOW" — every promotion is gate-earned.

## IDEAL state (the target for every class)
Tier-2 charter: **PF > 1.5, WR > 50%, MDD < 20%, n ≥ 100 clean** (post-resolver-v2.1,
deduped) AND walk-forward decay ≥ 0 across ≥ 5 folds AND DSR ≥ 0.95 / PBO < 0.05.
Until all hold on a 30-day rolling-clean window: NOT real-money.

---

## CRYPTO
- **Current (verified):** deduped PF ~0.41–0.74, WR ~32–36%. `quan_engine_scalp`
  = 70% of the ledger, PF 0.38 — **already blocked** in 9+ structures
  (`quality_gates.py`); its −960% is dead historical data, not live bleed.
  The conf≥0.8 "edge" (n=126, PF 3.67) is **3 overfit ML models on 3 tokens**
  (87% RENDER/FET/BNB), LONG-only — not a confidence effect.
- **Algorithm:** (1) confirm `quan_engine_scalp` block holds (done). (2) Rebuild
  per-class stats from the canonical PF registry (A8) so dead blocked-source
  history stops dragging the aggregate. (3) Do NOT promote the ml_enhanced
  cohort — ACCUMULATE n per symbol; re-evaluate per-symbol at n≥100 each.
  (4) UTC-hour filter shipped (A-program). (5) Do NOT add a `confidence≥0.6`
  gate — confidence is anti-predictive; gating on it selects noise.
- **Gate ETA:** 60–90 days of post-block rolling-clean accumulation.

## COMMODITY
- **Current (verified):** dashboard PF 7.71 is **INFLATED** — deduped real ~1.1.
  The entire class "edge" is the leaked CT=F COT-SHORT cohort; non-COT commodity
  is WR 12% / PF 0.22.
- **Algorithm:** (1) `cot_paper_pilot` dedup fix shipped (PR #1140 — tier now
  `SHADOW_INSUFFICIENT_N`). (2) Purge pre-patch COT rows from the registry.
  (3) The genuine COMMODITY path is a NEW non-COT strategy — cross-sectional
  commodity momentum (CSMOM) is a reasonable RESEARCH candidate (Wire-Up-Rule
  gated, own walk-forward first; do NOT trust an external backtest's WR).
  (4) Gate after 100 clean NON-COT trades.
- **Gate ETA:** ~Aug 2026.

## EQUITY
- **Current (verified):** only ~32–44 clean picks in the repo ledger (dashboard
  shows 393 — the rest live in the MySQL `at_raw_picks` table). The problem is
  **statistical power (n), not strategy quality.** EQUITY is the closest-to-T2 class.
- **Algorithm:** stop tuning. (1) Sync the DB `at_raw_picks` equity rows into a
  unified ledger view so n is real. (2) Widen the symbol universe. (3) Accumulate
  to n≥100 clean. No filter change needed — just sample.
- **Gate ETA:** ~Oct 2026 (n-bound).

## FOREX
- **Current (verified):** deduped PF ~0.32–0.36 — catastrophic. `multi_asset_copytrader`
  is the drag (n=696, WR 16.5%, PF 0.23). The `cta_replicator` "subset" that
  looks like PF 2.20 is **177/179 resolver-REPLAY rows** (not live closes),
  +0.18% real PnL — an artifact, NOT a deployable edge.
- **Algorithm:** (1) Block `multi_asset_copytrader` from FOREX — defensible
  drag-removal (verified loser), NOT an institutional unlock. (2) FOREX stays
  hard-disabled for emission. (3) Carry-factor is the documented rescue but must
  be validated on genuinely live-closed trades, not `non_crypto_resolver` replay.
  (4) Fix the walk-forward-vs-live divergence (validator rates RSI2 VIABLE while
  live WR is ~8–12%).
- **Gate ETA:** regime-dependent; not before carry-factor clears on live closes.

## ETF
- **Current (verified):** n ~75 — too thin. Empty-class problem.
- **Algorithm:** accumulate to n≥100. GEM dual-momentum is a reasonable NEW
  research scaffold to seed the class (Wire-Up-Rule gated). First 6 months =
  calibration (monthly strategies accumulate n slowly).
- **Gate ETA:** ~Sep–Oct 2026.

## FUTURES
- **Current:** near-dead, tiny n. `futures_momentum` WR ~2% — do NOT "inverse it
  to 98%": inverting a PF-0.03 strategy does NOT yield PF-30 (friction paid
  twice, SL/TP geometry asymmetric — see `CLOUD_AGENT_AUDIT_VERIFICATION_PROMPT.md`
  §0b). Diagnose root cause first.
- **Algorithm:** stop live emission; route any futures exposure through the
  COMMODITY CSMOM research path.

## BOND
- **Current:** n=11–18 — no conclusion possible.
- **Algorithm:** cheapest path — cover bond exposure via the ETF GEM strategy's
  TLT risk-off allocation rather than building a separate bond strategy.

---

## Universal 5-gate promotion process (every new/changed strategy)
1. **Backtest integrity** — dedup + spot-sanitize the ledger first; cumulative-
   since-inception and last-10/last-50 windows are INADMISSIBLE.
2. **Walk-forward** — ≥5 folds, decay ≥ 0, OOS Sharpe ≥ 70% of in-sample.
3. **Paper** — 30-day shadow, post-resolver-v2.1, n ≥ 100.
4. **Small live** — 0.1% sizing, friction-costed, reconcile daily.
5. **Full allocation** — only after DSR ≥ 0.95, PBO < 0.05 hold on rolling-clean.

**Anti-fantasy rules (hard):** no inverse-PF projection without a friction-costed
backtest of the actual inverted trades; no recency cherry-pick; no "institutional
NOW" — promotion is always gate-earned.

*Synthesized 2026-05-17 from verified findings. Sauna's `class_improvement_algorithms.md`
playbook is process-sound but repeats the inverse-PF fantasy (FUTURES "WR 3.5%
→ 96.5% inverse") — corrected here.*
