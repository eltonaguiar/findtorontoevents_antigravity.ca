# EAGLE2 Quant Review & Enhancement Plan — DeepSeek v4 (Mercury 2)

**Plan ID:** EAGLE2_2026-06-02_deepseek_v4  
**Author:** DeepSeek v4 (via Mercury 2)  
**Date:** 2026-06-02  
**Status:** Peer plan — align execution with [`EAGLE2_2026-06-02_GROK.md`](EAGLE2_2026-06-02_GROK.md) (canonical engineering backlog)  
**Review:** [`EAGLE_REVIEW_2026-06-02_GROK.md`](EAGLE_REVIEW_2026-06-02_GROK.md)  
**NFA.**

---

## 1. Executive summary

**Core issue:** The production-ready audit book lacks deployable edge. Research-grade edge exists only in isolated tournament or lab sleeves, not in the live, policy-clean layer.

**Root causes:** Mismatch between research and production standards, over-broad emitter set, concentration artifacts, and resolver/label contamination.

**Goal:** Convert verified research edge into stable, capital-ready strategies while tightening data hygiene and validation pipelines.

---

## 2. Current state (as of 2026-06-02)

| Asset class | Live PF/WR (policy-clean) | Research edge | Primary pain point |
|-------------|---------------------------|---------------|-------------------|
| CRYPTO | PF ~0.89, WR ~36% | Sub-cohort / tournament | Selection/gating mismatch, concentration |
| EQUITY | PF ~0.33, WR ~27% | None in production | Weak emitters / failed holdout |
| ETF | n=3 | Dual-momentum lab | Insufficient forward data |
| FOREX | PF ~0.48 | Minor / disputed | Resolver errors, mislabeled exits |
| COMMODITY | n=4 | — | Sample size |
| FUTURES | PF ~0.52 | — | Artifact risk |
| BOND | n=0 | — | Data gap |

**Portfolio health:** 81 portfolios (66 active). `deepseek_v4__aggressive` has 11 open names — issue is mis-alignment, not empty backend.

---

## 3. Key diagnostic findings

- Inconsistent validation standards (lab vs production).
- Emitter over-breadth.
- Concentration artifacts.
- Resolver/label pollution.
- Insufficient forward sampling (ETF, crypto sub-sleeves).

---

## 4. Enhancement blueprint

### 4.1 Data & resolver hygiene

| Action | Deadline | Success metric |
|--------|----------|----------------|
| Audit disputed resolver entries (CRYPTO, FOREX) | 2 weeks | &lt; 1% disputed tags |
| Source-provenance on every price/label | 3 weeks | 100% `source_id` + fallback |
| Duplicate detection on `pf_portfolios.json` | 1 week | Zero duplicate IDs |

**Repo tools:** `alpha_engine/outcome_resolver.py`, `tools/data_reconciliation.py`, `tools/pick_quality_pulse.py`.

### 4.2 Validation pipeline standardization

| Step | Tooling in repo |
|------|-----------------|
| Pre-registration | `reports/hypothesis_registry.json` (M-107) |
| Purged walk-forward | `verified_strategies/run_phase2.py`, `walkforward_suite` |
| Costs | `alpha_engine/transaction_costs.py` |
| DSR/PBO/SPA | `alpha_engine/rigorous_backtest_harness.py`, `money_ready_verdict.py` |
| Block bootstrap | `strategy_verification_engine.py` (B3) |
| Regime robustness | `audit_trail/vix_regime_gate.py` |

**CLI:** `python3 tools/strategy_admit.py --strategy <name> --write`

### 4.3 Emitter & strategy discipline

- Emit-culling: OOS PF ≥ 0.6, WR ≥ 0.55 after corrections.
- Promotion: forward paper ≥ 2 months.
- Shadow sizing ≤ 0.5% for 4 weeks.
- Scale only if live PF within 10% of paper for 8 weeks.

**Repo:** `tools/emitter_census.py`, `alpha_engine/verified_promotion_gate.py`.

### 4.4 Targeted edge development

| Candidate | Immediate action |
|-----------|------------------|
| ETF dual-momentum | Forward pilot + shadow |
| Crypto VWAP/Bollinger | Resolver fix + mutation |
| deepseek_v4 tournament | Admissibility bridge (D-workstream) |
| GPT-4o / Grok-3 | Regime checks → promotion queue |

### 4.5 Mutation & inversion

- Mutation: feature perturbations; keep if PF +0.05 OOS.
- Inversion: only with explicit OOS proof.

**Repo:** `docs/MUTATION_THREE_AXIS_PROTOCOL.md`, `tools/mutation_analysis.py`.

### 4.6 Monitoring & governance

| Metric | Frequency | Alert threshold |
|--------|-----------|-----------------|
| Live PF | Daily | &lt; 0.4 for &gt; 5 days |
| WR vs PF divergence | Daily | WR &gt; 0.7 and PF &lt; 0.4 |
| HHI (concentration) | Weekly | &gt; **0.25** |
| Resolver dispute rate | Weekly | &gt; **2%** |
| Regime drift | Monthly | Edge shift &gt; 15% |

**Repo implementation (no Grafana required for Phase 0):** `tools/pick_quality_pulse.py` → `concentration_alerts`.

---

## 5. Timeline (12 weeks)

| Week | Milestone |
|------|-----------|
| 1–2 | Resolver audit, duplicate purge |
| 3–4 | Standardized pipeline + pre-register |
| 5–6 | WF on ETF DM + crypto VWAP/Bollinger |
| 7 | Shadow-size ETF + crypto |
| 8–9 | Mutation on failed lab sleeves |
| 10 | Promote sleeves meeting PF/WR gates |
| 11–12 | Rollout + ops dashboard |

---

## 6. Success definition (quarterly)

- ≥ 2 capital-ready sleeves (live PF ≥ 1.5, WR ≥ 50%, n ≥ 100 per charter — DeepSeek table used looser bands; **use Tier-2 from CLAUDE.md**).
- Resolver dispute &lt; 1%.
- Book HHI &lt; 0.20.
- Pipeline latency ≤ 5 min/sleeve.

---

## 7. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Resolver drift | Hourly resolver CI |
| Over-fit on mutation | Block-bootstrap + holdout |
| Policy change | `money_ready_verdict` + capital lock |
| Allocation lag | Shadow budget + `verified_promotion_gate` |

---

## 8. Grok review notes (2026-06-02)

- **Adopt:** phasing, HHI 0.25, resolver 2%, emit-culling discipline.
- **Defer:** fictional owner table; Grafana before JSON pulse.
- **Correct:** success “WR ≤ 0.6” in §6 likely meant WR ≥ 50% / PF ≥ 1.5 per project charter.
- **Canonical execution:** `reports/EAGLE2_2026-06-02_GROK.md` + `reports/EAGLE_2026-06-02_GROK.md`.

---

*Prepared by Quant Review Team — EAGLE2 Initiative (DeepSeek v4 transcript, formatted for repo).*