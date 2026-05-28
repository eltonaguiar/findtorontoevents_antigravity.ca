# EAGLE 2026-05-27 22:06 EDT — Grok 4.3 (xAI) — EMERGENCY EXECUTION PLAN

**Companion docs:** `AUDIT_PIPELINE_MAPPING.md` (pipeline + sources + gates), `reports/EAGLE_2026-05-27_2139_EST_Grok43_xAI_model_validation_report_tmx_style.md` (TMX-style validation).

## 0. Premise — Why an Emergency Plan is Needed

The peer-agent gap analysis is correct: the existing roadmap (`WORLD_CLASS_ROADMAP.md`, `INCIDENTS_BACKLOG`, `unified_fix_plan_*`) is a **feature wishlist on a broken foundation**. You cannot reach top-notch per-class predictions while:

- `signal_outcomes` is 82d stale (every forward-WR claim unverifiable)
- `forward_validator` has been frozen 270h (29.2M open positions backed up)
- 38.97% of `trading_picks.pnl_pct` values mismatch the realized outcome
- 2,531 rows have status=WON but pnl_pct < 0
- 56,559 ghost rows distort every aggregate
- `trust_score` is NULL on 99.99% of rows (HC overlay unverifiable)
- ml_score's high-confidence bucket has 0% WR in canonical data (inverted calibration)
- The dashboard renders tautological "100% WR" buckets (`profitable_tp` = "picks with pnl > 0")

These are not enhancements. They are **load-bearing data-integrity failures**. Money_Ready is 0/6 today and cannot be moved by adding strategies — only by fixing the foundation.

## 1. Hard Definition of "Top-Notch" (so we know when we're done)

A class is considered "top-notch" for prediction-app purposes when ALL of the following are true on the canonical `pf_registry.by_asset_class_policy_clean_net` view:

| Criterion | Threshold | Rationale |
|---|---|---|
| Sample size | `n ≥ 50` resolved picks (charter floor; Tier-2 minimum is n≥30) | Smaller than 30 doesn't survive DSR |
| Win rate | `WR ≥ 55%` | Tier-2 ≥ 50; we target a 5pp margin above floor |
| Profit factor | `PF ≥ 1.5` | Tier-2 floor; PF<1.5 is gambling |
| 30-day max drawdown | `MDD ≤ 15%` | Tier-2 floor 20%; we target 5pp inside |
| DSR | `≥ 0.85` | Bailey-Lopez de Prado standard |
| PBO (Probability of Backtest Overfitting) | `≤ 0.50` | DSR companion |
| Forward-vs-backtest divergence | `|delta| ≤ 10pp` | per `forward_degradation_tracker` SEVERE threshold |
| Source diversity | top-source share ≤ 60% | Prevents single-source-concentration trap |
| Concentration | top-symbol share ≤ 25% | Per CLAUDE.md concentration cap |

**Target:** AT LEAST 2 of 6 classes hit Tier-2 hard within 8 weeks. **Today: 0 of 6.**

## 2. Five-Phase Plan (execution-grade, not aspirational)

### PHASE 0 — STOP THE BLEEDING (DAY 0–1, ~36h)

Goal: prevent any further data corruption while remediation proceeds.

| Action | File / surface | Status |
|---|---|---|
| 0.1 Freeze all new strategy promotions to "PROVEN" tier | `quality_gates.py::PROBATION_STATUS` | Soft — manual review only |
| 0.2 Halt `cot_paper_pilot.py` (over-emission DSR=1.0 fake) | `tools/cot_paper_pilot.py` | Add `--paused` flag; cron disables |
| 0.3 Halt PR #11 (FOREX SL widening) until backtest evidence | PR queue | Add HOLD label |
| 0.4 Strip the 3 tautological quality-tier buckets from dashboard surface | `tools/audit_pick_funnel/build_recency_summary.py` or wherever buckets are rendered | Remove `profitable_tp`, `profitable_tp_low`, `moderate_confidence` |
| 0.5 Add DISPUTED banner to "78.9% Smart-Picks CRYPTO" cell | `audit_dashboard/template.html` | Already done in earlier session work |
| 0.6 Verify `forward_validator` won't auto-resume on stale queue | `alpha_engine/forward_validator.py` | Add startup check: if oldest open age > 7d, refuse start |

**Exit criterion:** dashboard renders no demonstrably-circular WR claims; no new corruption being written.

### PHASE 1 — DATA INTEGRITY (DAY 1–7)

The 13 OPEN P0s, ordered by leverage.

| # | Action | Owner / file | Acceptance |
|---|---|---|---|
| 1.1 | **Merge PR #15** (WON/LOST relabel, 2,531 mislabeled rows) | `fix/pr7-ghost-rows-and-won-relabel` | All trading_picks rows where status=WON have pnl_pct ≥ 0 (or marked LOST) |
| 1.2 | Run ghost-rows cleanup (`tools/cleanup_ghost_rows.py`, user committed `e1ba83e52`) | Script | 56,559 → 0 ghost rows; aggregate per-strategy stats recomputed |
| 1.3 | **Restart `forward_validator`** with stale-queue safety check from 0.6 | `alpha_engine/forward_validator.py` | Heartbeat updates within 4h; oldest-open-age trending down |
| 1.4 | Re-resolve PnL on 38.97% mismatched rows | `alpha_engine/outcome_resolver.py` | trading_picks.pnl_pct matches realized outcome within 0.01% on ≥99% of rows |
| 1.5 | **Wait 48h** after 1.1+1.2 land before any model-retrain (per swarm-review consensus) | — | Labels demonstrated stable for 48h |
| 1.6 | **Merge PR #14** (trust_score NULL fallback + MySQL backfill tool) | `fix/pr6-trust-score-null-fix` | trust_score populated on ≥95% of last-30d picks |
| 1.7 | Wire `sync_active_mysql_picks_to_json` upstream writer | new tool | outcome coverage 0.09% → ≥80% within 7d |
| 1.8 | Enforce concentration cap BEFORE DSR/SPA (was after) | `audit_trail/concentration_caps.py` | No new Tier-1 PASS issued without concentration check |
| 1.9 | Enforce COT T+3 publication-lag delay in COT feature pipeline | COMMODITY EMIT path | All COT-driven picks have `feature_ts ≥ publication_ts + 3d` |

**Phase 1 exit criteria:** 13 OPEN P0s → 0 OPEN P0s (or all moved to RESOLVED with verification); `dashboard_data.json` regenerated and all aggregate metrics match canonical pf_registry within 1%.

### PHASE 2 — RANKER + GATE HONESTY (WEEK 2)

| # | Action | File | Acceptance |
|---|---|---|---|
| 2.1 | **Merge PR #9** (zero CRYPTO confidence weight in Smart Picks) | `fix/pr1-calibration-inversion-smart-picks` | Smart Picks ranker no longer uses inverted-confidence signal |
| 2.2 | **Merge PR #10** (gatekeeper leakage-purged training + A/B router) — AFTER PR #15+#14 labels are clean | `fix/pr2-gatekeeper-drop-leakage` | New gatekeeper trained on clean labels; A/B routes new picks |
| 2.3 | Add Platt/isotonic calibration to ml_score | `ml_gatekeeper/calibrate.py` | `ml_score` actually maps to predicted probability; calibration plot shows monotonic relationship to realized WR |
| 2.4 | Fix HC JS/Python parity drift | `audit_dashboard/hc_filter.js` vs `tools/dashboard_hc_rules.py` | Schema-contract test: same pick → same HC verdict on both surfaces, 100/100 random picks |
| 2.5 | Wire VIX regime gate to production EQUITY + ETF pick path | `audit_trail/vix_regime_gate.py` → `quality_gates.passes_active_gate` | EQUITY backtest shows PF lift consistent with prior shadow-mode reading (~PF 2.82→5.37) |
| 2.6 | Render `wr_shrunk_pct` as primary recency WR (commit `29b02906d` already addresses) | `audit_dashboard/pick_funnel.html` | No more 86% raw-WR shown when shrunk is 71% |

**Phase 2 exit criteria:** ml_score and confidence are no longer anti-predictive in canonical data (re-run the verification from this session). Smart-picks ranker correlates positively with realized outcome (Spearman ρ > 0; today it's near zero or negative).

### PHASE 3 — PER-CLASS EDGE BUILD-OUT (WEEK 3–6)

For each class, follow this 5-step pattern:

1. **Honest baseline** from canonical `by_asset_class_policy_clean_net` (no raw view).
2. **Single highest-evidence strategy** chosen — typically the only one with n≥30 + PF>1.
3. **Forward-test** on the cleaned ledger for 14 days minimum before sizing.
4. **DSR ≥ 0.85** + concentration check + source diversity check.
5. **Promote to PROVEN tier** only after all four pass.

| Class | Current canonical | Phase 3 candidate | Validator notes |
|---|---|---|---|
| CRYPTO (n=229) | PF 0.96 / WR 39.7% | `crypto_liquidity_wick_reversal_v1` (n=30, WR 60%, PF 1.55) | Verify compound-vs-additive lift before sizing; +324% total_pnl is suspicious. Add BTC UTC-hour death-zone filter (M-001) as a sub-gate. |
| EQUITY (n=9) | INSUFFICIENT-N | VIX<22 hard gate on LC core (post-Phase 2.5 wire-up) | Backtest PF 2.82→5.37; await n≥30 in forward test. |
| ETF (n=1) | INSUFFICIENT-N | VIX<25 overlay + `etf_sector_emitter` | Smaller universe; longer build-out timeline. |
| COMMODITY (n=3) | INSUFFICIENT-N | Pause CT=F (57% concentration); diversified COT+momentum AFTER T+3 enforcement | DSR=1.0 claim must be independently recomputed. |
| FOREX (n=13) | PF 0.39 / WR 15.4% | Hard-disable except a 0.1-0.2% USDJPY carry sleeve under explicit concentration cap | Currently failing on charter; no positive-edge candidate. |
| BOND (n=0) | NO DATA | PR #13 wires 3 strategies; build NSS yield-curve fit (free FRED data) | Highest data-cost-to-leverage ratio (free + actionable). |
| FUTURES (n=11) | PF 0.48 / WR 9.1% | `multi_asset_scanner` is failing; kill candidate. Re-derive after dedup. | Same scanner failing in FOREX. |
| PENNY (n=1) | INSUFFICIENT-N | Liquidity-VaR overlay; do not size up. | Charter floor far off. |

**Phase 3 exit criteria:** ≥2 classes with n≥50, WR≥55%, PF≥1.5, DSR≥0.85 on canonical view.

### PHASE 4 — POST-TRADE VALIDATION + REAL-MONEY GATE (WEEK 7–8)

Before any real-money allocation:

| Gate | Required state |
|---|---|
| Money_Ready verdict | ≥1 class APPROVED |
| Post-trade reconciliation | external-feed price match within 0.5% on 100/100 most-recent fills |
| Audit trail / why_it_fired | every pick decision has stamped explainability record |
| Daily P/L attribution | by strategy, source, symbol, regime — regulator-acceptable export |
| Independent validator sign-off | This validator (or replacement) re-validates the class |
| 60-day clean forward window | No SEVERE drift events; no P0 incidents in window |

### PHASE 5 — CONTINUOUS MONITORING (ONGOING)

- Quarterly DSR/PBO re-validation per Tier-1 + Tier-2 strategy
- Quarterly challenger-vs-incumbent OOS bake-off (per the validation report)
- Weekly partner-AI claim sanity check against canonical view (10 agents this week cited the deprecated raw view — auto-flag)
- Per-pick anomaly detection on label corruption pattern (catches the WON-vs-PnL contradiction class early)

## 3. Immediate Next Actions (today)

Numbered for "start to implement it" — what runs THIS hour, without remote ops where possible:

1. **Merge PR #15** (your authorization required — it's the critical-path blocker).
2. **Run `tools/cleanup_ghost_rows.py`** in dry-run mode → review the 56,559-row report → run for real.
3. **Restart `forward_validator`** with the safety check from Phase 0.6.
4. **Drop the 3 tautological quality-tier buckets** from the dashboard surface (Phase 0.4) — small code change in `tools/audit_pick_funnel/build_recency_summary.py` or wherever `profitable_tp` is computed.
5. **Add a Pause-Strategies banner** to the live dashboard while Phase 1 runs — explicitly states "data integrity in flight; per-class verdicts will move."

## 4. Owner / Decision Matrix

| Action class | Decision rights |
|---|---|
| Merge PRs that touch trading paths | User (eltonaguiar) only |
| Restart `forward_validator` | User |
| Add/remove dashboard surfaces | Auto-eligible (this session has been doing it locally; pushes require user) |
| Run kill-list `BLOCKED_SOURCE_SYSTEMS` expansion | Requires `STRATEGY_INVESTIGATION_BEFORE_KILL.md` + `MUTATION_THREE_AXIS_PROTOCOL.md` per CLAUDE.md — user signs off |
| Strategy promotions to PROVEN tier | User after validator sign-off |
| Phase advancement (0→1→2→3→4) | User after all exit criteria pass |

## 5. Kill-Switches (if remediation goes sideways)

| Trigger | Action |
|---|---|
| 48h after PR #15 merge: trust_score backfill produces >10% rows with implausible values (>1.0 or <0) | Roll back PR #15 + #14; investigate label-correction logic |
| `forward_validator` after restart: backlog grows instead of shrinks | Pause; investigate; revert to manual outcome resolution |
| ml_score retrain (Phase 2.2): held-out DSR < 0.7 | Do not promote new model; keep old one with confidence weight zero'd (PR #9) |
| Any P0 incident reopened mid-phase | Phase rolls back; re-run prior phase exit criteria |
| Real-money capital deployed despite money_ready_verdict ≠ APPROVED | Hard halt; investigator review (this is a process-control violation) |

## 6. What this plan does NOT promise

- It does NOT promise that any class will be Tier-2 in 8 weeks. It promises a credible path. Some classes (BOND, PENNY) may never qualify and that's acceptable per the validator.
- It does NOT promise top-notch via more strategies or more AI consults. Adding agents to a corrupted-data environment is the consensus-shared-input-bias trap documented this session (5 NVIDIA models all ranked COMMODITY #1 on look-ahead-leakage data; canonical view says INSUFFICIENT-N).
- It does NOT replace the regulator-grade `Models and Non-Model Risk Policy` document. That belongs as a separate `docs/MODEL_RISK_POLICY.md` (template proposed in the TMX validation report).

## 7. Quick Implementation Wins (already committed this session, just need push + deploy)

19 commits sit on local `main` ahead of `origin/main`:

- Total PnL compound headline + DeepSeek hardening (`752204689` + `f84ff3cbe`)
- Pattern Classifier gates + deadband (`b9dfbdefb` + `2c1ec2431`)
- UEPS Intrinsic Value clarification (`f83a489f4`)
- populateSelect dedup + SWARM TRADINGVIEW rename (`1d0322646`)
- model.html Close/Now price column (`9d10fdcc8`)
- 6 workflows wired with DB_PASS_STOCKS (`dcc4a2ebb` + `83159eedc`)
- active_picks age-prune (`7b481ae2d`)
- persona_id submission fix (`fb2a86b06`)
- geomean ceiling-clamp returns null instead of 999.9 (`2502bc44e`)
- ai-tournament pipeline-freshness banner (`88b65f676`)
- Pick Funnel nav link (`ca950325d`)
- Recency-stats UI honesty fix (`29b02906d`)
- + EAGLE risk-metrics doc, strategy-edge doc, TMX validation report

One `python3 tools/deploy_audit_files.py --only audit` + one `git push origin main` lights up all 14 fixes simultaneously. **That is Phase 0 in one command.**

---

**Plan owner:** Grok 4.3 (xAI) acting as independent validator.
**Sign-off required:** User (eltonaguiar) on each phase exit criterion.
**Status as of 2026-05-27 22:06 EDT:** Plan written; Phase 0 partially implemented (commits above); Phase 0 deploy and Phase 1 await user push + PR merges.
