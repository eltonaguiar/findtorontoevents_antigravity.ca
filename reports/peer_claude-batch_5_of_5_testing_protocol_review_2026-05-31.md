# Batch 5 of 5 — Testing / Protocol / Methodology File Review (2026-05-31)

Author: peer_claude (Opus 4.7)
Source list: `reports/peer_claude-DUPE_SCAN_TESTING_PROTOCOL_2026-05-31.md` "Batch 04" (16 files).
Canonical reference for conflict comparison: `docs/PAPER_PILOT_HARNESS.md` (cursor statistical framework, n_closed >= 500, Bonferroni alpha = 0.05/7, Wilson LB 95%, bootstrap PF 95%).

## Files reviewed (16)

| # | File | mtime | WHAT_IT_DEFINES | REDUNDANT_WITH | CONFLICT_WITH PAPER_PILOT_HARNESS |
|---|------|-------|-----------------|----------------|-----------------------------------|
| 1 | `TESTING_PROTOCOL.MD` (63KB) | 2026-05-25 | Master 14-section testing pipeline: IS/OOS/walk-forward, p-value+FDR+Bonferroni, MC/regime/FGI, scarcity, rehab-first 6-stage ladder, 2.5 data-driven gates (Score>=40 floor, Trust>=4 LONG, toxic-combo kill LONG+Conf>=0.90). | None — canonical for layered backtest pipeline. | YES — minor: §3 "weekly walk-forward minimum 200 picks per run"; §7 "trades < 25" = noise. Cursor framework demands n_closed >= 500 for graduation. These are different gates (per-run vs per-strategy lifetime) but ANY agent reading just one will pick a different floor. Needs an explicit cross-reference. |
| 2 | `tests/test_charter_concentration_gate_optin.py` | 2026-05-25 | Regression test for `CHARTER_CONCENTRATION_ENFORCE` env flag in `passes_active_gate`. Validates opt-in/opt-out behavior of duplicate-symbol + sector-cap rejection. | None | None — implementation test, not a protocol claim. |
| 3 | `tests/test_charter_drift_circuit_breaker.py` | 2026-05-25 | Tests Charter §7 drift CB: realized WR 30d window, `DEFAULT_MIN_REALIZED_N`, `is_sizing_breached`, per-class evaluation. | None | None — but uses its own `MIN_REALIZED_N` default (separate from MIN_N_CLASS=50 and n_closed>=500). Third "n floor" in the stack. |
| 4 | `tests/test_charter_position_sizer.py` | 2026-05-25 | Tests `compute_position_size`, `daily_loss_kill_switch`, `validate_concentration` against $100k equity baseline. | None | None |
| 5 | `tests/test_charter_risk_budget.py` | 2026-05-25 | Tests cross-class allocator caps (CRYPTO 0.25 default). | None | None |
| 6 | `tests/test_charter_slippage.py` | 2026-05-25 | Tests per-class one-way bps (CRYPTO 4, EQUITY 3, ETF 2, COMMODITY 6, FOREX 1, BOND 3, FUTURES 4), `stamp_pick_net_pnl`. | None | None — but `TESTING_PROTOCOL.MD` does NOT enumerate these per-class slippage bps. The numbers are only in `alpha_engine/charter_slippage.py` + this test. Single source of truth at the code/test layer. |
| 7 | `tests/test_cross_pc_protocol.py` | 2026-05-25 | Envelope schema + ACK normalization tests for cross-PC gateway. | None | None — not in scope of testing-protocol family (different domain). |
| 8 | `tests/test_money_ready_verdict.py` (39KB, MODIFIED today) | 2026-05-31 | Comprehensive money-ready verdict tests: MIN_N_CLASS gate, MIN_N_STRATEGY=20 SPA gate, M-070 single-symbol concentration guard, 2026-05-28 Tier-0 source-concentration cap, MDD/CVaR gate. | None | YES — imports `MIN_N_CLASS` (=50) and `MIN_N_STRATEGY` (=20) from `alpha_engine/money_ready_verdict.py`. These are 10x and 25x lower than `n_closed>=500` graduation floor in PAPER_PILOT_HARNESS.md. Different surfaces (verdict vs graduation), but both produce "is this class ready?" answers visible on /audit. |
| 9 | `tests/test_production_scanner_charter_sizer_wire.py` | 2026-05-25 | Regression that `production_scanner` stamps `_charter_notional_pct` + `_charter_concentration_warn` after quality gates. Informational, non-gating. | None | None |
| 10 | `tools/ci_gate_money_ready_vs_registry.py` | 2026-05-25 | CI gate: blocks build if `money_ready_verdict.py` declares MONEY_READY on a class whose canonical `pf_registry.json` PF < 1.5 (Tier-2 floor) OR concentration-bypassed (top_symbol_share > 0.60 default, with per-class overrides e.g. COMMODITY 0.85). | Partial — PF 1.5 floor + 0.60 concentration are also stated in `docs/PERFORMANCE_CHARTER.md`. | None — enforces Tier-2 floor (PF 1.5) which aligns with TESTING_PROTOCOL goal table. NOT contradicting cursor framework (different surface). |
| 11 | `tools/money_ready_snapshot.py` | 2026-05-25 | Subprocess-isolated producer for `audit_dashboard/data/money_ready_verdict.json` + daily archive + drift. Hard-decoupled from `money_ready_verdict.py` (exec'd as subprocess on purpose). | None | None — operational tool, no methodology claims of its own. |
| 12 | `tools/swarm/agent_personas/score-methodology-auditor.md` | 2026-05-25 | Persona for swarm agent that audits Piotroski F-Score, ml_score, confidence, elite_score, blended_conf, Beta Confluence, trust_score. Cites SCORE_CALIBRATION_AUDIT_2026-04-06 (n=3,500) + Kimi dim02 inverted-U (Conf 0.70-0.79 = 57% WR, 0.90+ = 47% WR). | Partial overlap with `TESTING_PROTOCOL.MD §2.5` "Toxic Combo Kill: LONG+Conf>=0.90 = 19.5% WR." Same finding, different score (47% vs 19.5%) because populations differ. | YES (low severity) — Conf 0.90+ has two divergent WR figures across these docs (47% from Kimi dim02 vs 19.5% from TESTING_PROTOCOL §2.5 LONG-only). Each is internally consistent (one is all-direction, one is LONG-only). Document the segmentation to prevent peer agents from picking the wrong number. |
| 13 | `tools/swarm/METHODOLOGY.md` | 2026-05-25 | Soundness argument for swarm orchestrator: 8-threat model (T1-T8) + per-threat mechanism (schema-enforced evidence field, fabrication red-team, snapshot freshness checks, prompt-injection defenses). | None | None — swarm-orchestration domain, not strategy-graduation domain. |
| 14 | `tools/swarm/prompts/ai_tournament_methodology_review_20260519.md` | 2026-05-25 | Review prompt for AI tournament methodology. Sets tier thresholds: T1 PF>=2.0/WR>=55, T2 PF>=1.5/WR>=50, T3 PF>=1.3/WR>=45. Hallucination check tolerance +/-5%. | Tier thresholds match CLAUDE.md MAJOR GOAL #1 + `docs/PERFORMANCE_CHARTER.md`. | None for tiers. Note: T3 (PF 1.3 / WR 45) is NOT in PAPER_PILOT_HARNESS (which only graduates above n=500 with PF_lo>1.0). T3 is a tournament-display tier, not a real-money gate. Worth a stub clarifying. |
| 15 | `updates/2026-04-23-audit-whatif-hc-scoping-methodology.md` | 2026-05-25 | Operational walk-through: HIGH CONVICTION button = `filterHighConvictionOrdered` + `passesValidatedEdgePerClass` (validated-edge classes: CRYPTO/EQUITY/FOREX only; BOND/ETF/FUTURES rejected). | Live UI authority is `audit_dashboard/hc_filter.js` + `template.html`. This doc is a snapshot. | None — narrative/operational, references code as authoritative. |
| 16 | `updates/2026-05-28-commodity-fv-exempt-revoke-money-ready-sync.md` | 2026-05-29 | Records 2 fixes: (a) `_COMMODITY_FV_EXEMPT` reduced from {commodity_cot_contrarian, multi_asset_cot, multi_asset_copytrader} → {commodity_cot_contrarian} only; (b) `money_ready_verdict.json` refresh moved daily → hourly via `audit-dashboard.yml`. | None | None — operational; pins money-ready cadence in line with hourly dashboard data. |

## Conflicts highlighted

Three n-floors live simultaneously in this batch alone, each governing a different surface:

| Surface | n-floor | Source |
|---------|---------|--------|
| Per-class money-ready verdict (`/audit` MONEY_READY badge) | **n_resolved >= 50** | `alpha_engine/money_ready_verdict.py:137` `MIN_N_CLASS`, asserted in `tests/test_money_ready_verdict.py` |
| Per-strategy SPA inclusion (PBO/SPA gates) | **n >= 20** | same module, `MIN_N_STRATEGY` |
| Cursor-framework graduation (paper-pilot -> live-money eligibility) | **n_closed >= 500** | `docs/PAPER_PILOT_HARNESS.md` |
| Walk-forward weekly refresh | **>= 200 picks per run** | `TESTING_PROTOCOL.MD §3` |
| Closed-trade scarcity flag | **< 25 trades** | `TESTING_PROTOCOL.MD §7` |
| Charter drift circuit-breaker realized-WR window | `DEFAULT_MIN_REALIZED_N` (separate constant) | `alpha_engine/charter_drift_circuit_breaker.py` |

These are *not* technically contradictions — each gates a different decision — but a peer agent reading any single doc will likely assert "the n floor is X" without qualification. The audit dashboard already exposes both: MONEY_READY (n>=50) appears on /audit while the same class is *not* paper-pilot-graduated (n>=500). This is a documentation gap, not a code bug.

Other findings:

- **Conf 0.90+ WR discrepancy** (score-methodology-auditor persona vs TESTING_PROTOCOL §2.5): 47% (all directions, Kimi dim02 n unspecified) vs 19.5% (LONG-only, n=41). Both correct in scope, but a careless reader will quote the wrong number. Adding a one-line "segmented by direction" annotation to the persona doc would close this.
- **Per-class slippage bps** (`charter_slippage.py` + `test_charter_slippage.py`) are not referenced anywhere in `TESTING_PROTOCOL.MD §0 / §6` (cost & slippage). Single source of truth lives in code only.
- **Tier-3 tournament thresholds** (PF 1.3 / WR 45) appear only in `ai_tournament_methodology_review_20260519.md`; not in PERFORMANCE_CHARTER tiers. Tournament-display only; safe but worth a stub.

## Canonical recommendations

1. **Add a top-of-doc "n-floor decoder" table to `TESTING_PROTOCOL.MD`** enumerating the 6 simultaneous n-floors above with their surface + authoritative file. Prevents peer-agent confusion and is the single highest-ROI cleanup in this batch.
2. **Keep `TESTING_PROTOCOL.MD` as canonical** for layered backtest + rehabilitation pipeline. No competing doc in this batch.
3. **Keep `docs/PAPER_PILOT_HARNESS.md` as canonical** for graduation gate (n>=500, Wilson LB, Bonferroni 0.05/7, PF_lo>1.0).
4. **Keep `tools/ci_gate_money_ready_vs_registry.py` as the enforcement gate** between money_ready_verdict and pf_registry (PF 1.5 + concentration policy).
5. **Add a 1-line cross-reference in `score-methodology-auditor.md`** noting that the 47%/19.5% Conf>=0.90 figures are population-segmented (all vs LONG-only), not contradictory.
6. **Move per-class slippage bps into TESTING_PROTOCOL.MD §6** (or add a "see `alpha_engine/charter_slippage.py`" pointer) so the cost model is discoverable from the testing protocol, not only from code.
7. **No archival or deletion needed** for any file in this batch — every file is live and serving a distinct purpose.

## Notes

- No byte-identical duplicates in batch (matches scan report).
- `tests/test_money_ready_verdict.py` was modified TODAY (2026-05-31 22:05 UTC) — verify any open PRs touching `money_ready_verdict.py` before relying on the assertions in this report.
- `tests/test_cross_pc_protocol.py` is unrelated to testing-protocol family; it tests the cross-PC gateway envelope schema. Scan may have matched on filename "protocol".
