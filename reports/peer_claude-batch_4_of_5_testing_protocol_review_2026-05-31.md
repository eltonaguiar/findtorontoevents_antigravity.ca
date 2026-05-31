# Batch 4/5 — Testing / Protocol / Methodology Review (2026-05-31)

Author: peer_claude (Opus 4.7)
Source list: `reports/peer_claude-DUPE_SCAN_TESTING_PROTOCOL_2026-05-31.md` (Batch 04, 16 files)
Anchor for conflict-check: `docs/PAPER_PILOT_HARNESS.md` (cursor statistical framework — `n_closed >= 500`, Wilson LB, Bonferroni `0.05/7 = 0.007142857`, bootstrap PF CI 1000 resamples).

## Files reviewed (16)

| # | File | LAST_MODIFIED | WHAT_IT_DEFINES |
|---|------|---------------|-----------------|
| 1 | `./TESTING_PROTOCOL.MD` | 2026-05-25 | Master 7-layer testing stack (Data Integrity → Promotion Gate), Layer 2.5 data-driven gates (Score≥40 hard / Score≥60 promo; Trust≥4 for LONGs; toxic LONG+Conf≥0.90 kill; rehab-first philosophy 6 stages); auto-rehab at WR<35% on ≥10 picks; weekly walk-forward min 200 picks/run |
| 2 | `./tests/test_charter_concentration_gate_optin.py` | 2026-05-25 | Unit tests for Charter §X concentration gate (opt-in mode) |
| 3 | `./tests/test_charter_drift_circuit_breaker.py` | 2026-05-25 | Unit tests for drift circuit-breaker (Charter §8) |
| 4 | `./tests/test_charter_position_sizer.py` | 2026-05-25 | Unit tests for Kelly/vol-target sizer (Charter §7) |
| 5 | `./tests/test_charter_risk_budget.py` | 2026-05-25 | Unit tests for cross-class risk allocator (P0.5-6) |
| 6 | `./tests/test_charter_slippage.py` | 2026-05-25 | Unit tests for execution-cost model (CRYPTO=8bp, EQUITY=6bp, COMMODITY=12bp round-trip; M-069 fraction units) |
| 7 | `./tests/test_cross_pc_protocol.py` | 2026-05-25 | Unit tests for cross-PC gateway envelope/ACK/replay |
| 8 | `./tests/test_money_ready_verdict.py` | **2026-05-31** | Tests the money-ready verdict including `test_insufficient_data_below_min_n` → uses `MIN_N_CLASS=50` |
| 9 | `./tests/test_production_scanner_charter_sizer_wire.py` | 2026-05-25 | Regression: charter_position_sizer wired into production_scanner; caps notional at 5% per Charter §7 |
| 10 | `./tools/ci_gate_money_ready_vs_registry.py` | 2026-05-25 | CI gate: blocks merge if `money_ready_verdict` declares MONEY_READY where `pf_registry` shows PF<1.5 or concentration bypass (top symbol >60%); PF_FLOOR=1.5, CONC_LIMIT_DEFAULT=0.60 |
| 11 | `./tools/money_ready_snapshot.py` | 2026-05-25 | Subprocess-decoupled snapshot producer for `/audit` Money Ready tab; writes daily archives + drift block |
| 12 | `./tools/swarm/agent_personas/score-methodology-auditor.md` | 2026-05-25 | Persona for score-stack auditor; defines taxonomy of F-Score, ml_score, confidence, elite_score, blended_conf, Beta Confluence, trust_score; calibration thresholds (conf 0.70-0.79 = 57% WR sweet spot, 0.90+ overconfidence penalty) |
| 13 | `./tools/swarm/METHODOLOGY.md` | 2026-05-25 | Swarm-soundness threat model (T1-T8: hallucination, confidence inflation, stale snapshot, prompt injection, cost runaway, silent failure, engine self-spoofing, stale state) + defenses; not a trading methodology |
| 14 | `./tools/swarm/prompts/ai_tournament_methodology_review_20260519.md` | 2026-05-25 | Prompt asking external reviewers to grade AI-tournament methodology; defines Tier-1/2/3 (T1 PF≥2.0/WR≥55%, T2 PF≥1.5/WR≥50%, T3 PF≥1.3/WR≥45%) and per-class resolution windows (EQUITY 30d, CRYPTO 14d, COMMODITY 28d, FOREX 10d, ETF 30d, BOND 60d) |
| 15 | `./updates/2026-04-23-audit-whatif-hc-scoping-methodology.md` | 2026-05-25 | One-off audit-page what-if for HIGH CONVICTION scoping; documents `filterHcStrict` per-class validated-edge gating (CRYPTO/EQUITY/FOREX only); historical, not active spec |
| 16 | `./updates/2026-05-28-commodity-fv-exempt-revoke-money-ready-sync.md` | 2026-05-29 | Operational note: revoked COMMODITY FV-exempt status after money-ready sync — incident log, not protocol |

## REDUNDANT_WITH (within-batch + cross-batch references)

- **Tier table (T1/T2/T3 PF+WR floors)** — duplicated across `TESTING_PROTOCOL.MD` §13 (implicit), `tools/swarm/prompts/ai_tournament_methodology_review_20260519.md`, `docs/PERFORMANCE_CHARTER.md` (Batch 1), `reports/PHENOMENAL_PERFORMANCE_METHODOLOGY.md` (Batch 3), `reports/MONEY_READY_METHODOLOGY.md` (Batch 3). Canonical recommendation: `docs/PERFORMANCE_CHARTER.md`.
- **Score≥40 floor / Trust≥4 / toxic LONG+Conf≥0.90** — defined in `TESTING_PROTOCOL.MD` §2 Layer 2.5; also referenced by `tools/swarm/agent_personas/score-methodology-auditor.md`. Persona file is a downstream consumer, not a redundant spec.
- **`updates/2026-04-23-audit-whatif-hc-scoping-methodology.md`** — its HC-strict per-class gating is now codified in `audit_dashboard/hc_filter.js` + `template.html`; doc is historical context, **candidate for `updates/archive/`**.
- **`tools/swarm/METHODOLOGY.md`** — swarm-orchestration soundness; **NOT redundant** with any trading-methodology doc (different domain). Already noted in scan-report filename-collision section.

## CONFLICT_WITH (vs. `docs/PAPER_PILOT_HARNESS.md` cursor framework)

| Knob | PAPER_PILOT_HARNESS (canonical for paper pilot) | Batch-4 file | Verdict |
|------|--------------------------------------------------|--------------|---------|
| **Graduation n-floor** | `n_closed >= 500` | `tests/test_money_ready_verdict.py` enforces `MIN_N_CLASS = 50` (via `alpha_engine/money_ready_verdict.py:137`); `MIN_N_STRATEGY = 20`; `MIN_N_RISK = 10` | **CONFLICT (#1, severity HIGH)** — two parallel n-floors. Money-ready verdict can flip a class to MONEY_READY at n=50 while a paper-pilot strategy still needs n=500 to graduate. Either rename the surfaces (verdict ≠ graduation) or align floors. |
| **Auto-rehab trigger** | not in scope | `TESTING_PROTOCOL.MD` §2 Layer 7: "any strategy with ≥10 resolved picks and WR<35% → auto-route to rehab" | **CONFLICT (#2, severity MEDIUM)** — TESTING_PROTOCOL acts on n=10 (rehab decision), framework needs n=500 (graduation). Decisions at n=10 are statistically noise-dominated relative to cursor framework. Acceptable IFF rehab is non-promotion (it is); flag for protocol-index doc. |
| **Significance test** | one-sided exact binomial vs break-even WR; `p < 0.007142857` (Bonferroni `0.05/7`) | `TESTING_PROTOCOL.MD` §2 Layer 4: BH (FDR) + Bonferroni + Fisher combined p-value — no per-test alpha specified | **NO HARD CONFLICT** but TESTING_PROTOCOL leaves Bonferroni denominator undefined; harness pins it to 7. If TESTING_PROTOCOL is invoked for a different strategy count, denominators drift. |
| **CI / bootstrap** | Bootstrap PF CI 1000 resamples, seed 17, Wilson LB 95% (z=1.96) | `TESTING_PROTOCOL.MD` §2 Layer 5: "Bootstrap / Monte Carlo confidence intervals" — no resample count, no seed | **NO HARD CONFLICT** but TESTING_PROTOCOL is under-specified; PAPER_PILOT_HARNESS is the operational source of truth on resamples + seed. |
| **Tier thresholds (PF+WR)** | not stated (graduation is binary on the four gates) | `tools/swarm/prompts/ai_tournament_methodology_review_20260519.md`: T1 PF≥2.0/WR≥55%, T2 PF≥1.5/WR≥50%, T3 PF≥1.3/WR≥45% | **NO CONFLICT** — orthogonal axes (gate-passing vs tier-grading). |
| **Concentration / PF floor at MONEY_READY** | not stated | `tools/ci_gate_money_ready_vs_registry.py`: PF_FLOOR=1.5 + CONC_LIMIT_DEFAULT=0.60 (top-symbol-share) | **NO CONFLICT** — this gate is independent and protects the dashboard from divergence with `pf_registry`. Good complement to harness gates. |
| **Slippage model** | implicit (assumed already applied upstream) | `tests/test_charter_slippage.py` codifies CRYPTO=8bp, EQUITY=6bp, COMMODITY=12bp, default=16bp round-trip | **NO CONFLICT** — concrete numbers PAPER_PILOT_HARNESS could cite; recommend cross-link. |

## Canonical recommendations

1. **n-floor index doc** (NEW): create `docs/TESTING_N_FLOORS_INDEX.md` listing the three distinct n-floors (paper-pilot graduation=500, money-ready verdict=50, charter rehab trigger=10) with explicit "use when" guidance. This removes the apparent conflict by naming the surfaces.
2. **TESTING_PROTOCOL.MD §2 Layer 4 + 5**: append a reference paragraph "For paper-pilot strategies the cursor statistical framework is the operational source of truth (`docs/PAPER_PILOT_HARNESS.md` §Cursor statistical framework)" with the exact Bonferroni denominator + bootstrap params. No threshold change needed.
3. **Archive `updates/2026-04-23-audit-whatif-hc-scoping-methodology.md`** to `updates/archive/2026-04/` — it is historical scoping, not active protocol; the active spec is in `audit_dashboard/hc_filter.js`.
4. **`tools/swarm/METHODOLOGY.md` retained as-is** — swarm-orchestration domain, no overlap with trading methodology.
5. **`tools/ci_gate_money_ready_vs_registry.py`** — keep; this is the only gate that protects the dashboard from `money_ready_verdict` vs `pf_registry` divergence. Reference it from PAPER_PILOT_HARNESS as the "live-money guard" layer.
6. **No file in batch 4 is byte-redundant with any other**; only logical-overlaps as itemized above.

## Summary numbers

- files_reviewed: 16
- redundant_pairs: 0 byte-identical; 2 logical overlaps (tier table; HC scoping)
- conflicts: 2 hard (#1 n-floor 50 vs 500; #2 rehab n=10 vs graduation n=500), 0 silent disagreements on bootstrap/Bonferroni (under-specified, not contradicting)
- archive candidates: 1 (`updates/2026-04-23-audit-whatif-hc-scoping-methodology.md`)
- new docs proposed: 1 (`docs/TESTING_N_FLOORS_INDEX.md`)
