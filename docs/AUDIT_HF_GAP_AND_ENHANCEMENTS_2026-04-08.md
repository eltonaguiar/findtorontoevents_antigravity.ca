# Audit dashboard vs hedge-fund-grade picks — gap analysis and enhancements

**NFA:** Research and engineering backlog — not investment advice.

This document ties the live **https://findtorontoevents.ca/audit/** experience (Active / Smart / Verified Alpha / high-conviction UI) to concrete repo levers and a prioritized enhancement list. It is meant to support a single PR-sized narrative; implementation can be split across follow-up PRs.

---

## 1. What the tabs represent (today)

| Surface | Role | Repo touchpoints |
|--------|------|------------------|
| **Active Picks** | Full candidate book after dashboard gates; sortable/filterable in `audit_dashboard/template.html` | `audit_trail/dashboard_generator.py`, `audit_trail/quality_gates.py` |
| **Smart Picks** | Backend-gated subset (`passes_smart_gate`, anti-overfit, score floors) | `alpha_engine/smart_picks_engine.py`, `audit_trail/quality_gates.py` |
| **Verified Alpha** | Audited-source filter + summary stats | `dashboard_generator` + VA rules in quality gates / payload |
| **HIGH CONVICTION / HF tiers** | Client + payload: rule-based tags (e.g. `hf_conviction_tier`, `extreme_conviction`) | `audit_dashboard/template.html`, `alpha_engine/conviction_stack.py`, generator wiring |

**Cross-asset:** Crypto dominates volume; equity/forex/commodity rows use the same scorer with asset-class branches (time windows, age soft caps, non-crypto policy). See `audit_trail/non_crypto_policy.py`, `config/hf_quality_gates.json`, and asset-class memos under `docs/`.

---

## 2. Distance from “top-notch” hedge-fund *pick quality* (honest framing)

Institutional bars usually include: **out-of-sample edge**, **calibrated probabilities**, **capacity and liquidity**, **TCA**, **risk parity / CVaR**, **no look-ahead**, and **stable promotion rules**. This stack has strong **research artifacts** (closed picks, DSR/AOF hooks, strategy×symbol registry — see `DEFINITIVE_HEDGE_FUND_PIPELINE.md`) but the **live book** still mixes many low-edge lanes.

**Concrete gaps:**

1. **Smart gate funnel** — Historical snapshots showed **0** picks passing with **anti_overfit** as the dominant first failure; until the funnel matches product intent, “Smart” will under-represent true edge or stay empty. *Action:* align `tools/audit_smart_gate_funnel.py` diagnostics with `passes_smart_gate` and document intended trade-off (breadth vs purity).
2. **Score ↔ PnL alignment** — Open-book Spearman near **0** has been reported; closed-book IC is stronger for some fields. *Action:* treat **closed outcomes** as calibration source; avoid re-introducing zeroed anti-predictive components (`config/score_component_calibration.json`, `elite_scorer.py`).
3. **Truth layer** — Payload must match generator version on CDN/FTP; stale `index.html` vs `template.html` confuses users. *Action:* single deploy path for audit artifacts (CI + FTP), plus snapshot tool `tools/fetch_audit_dashboard_snapshot.py`.
4. **Non-crypto** — Structural bleed in equity/forex in past audits; needs **allowlists / kill lanes**, not only reweighting. *Action:* `non_crypto_quality_gate.py`, VA tags, and smaller universes until metrics recover.
5. **Execution realism** — Wide R:R and static TP/SL without fees/slippage overstate win rate. *Action:* unify geometry + costs (see `docs/AUDIT_CRYPTO_PREDICTION_TP_SL_QUALITY_2026-04-02.md`, Mercury/risk paths).

---

## 3. Enhancements (quant PM backlog)

### P0 — Correctness and observability

- **Single source of truth:** Regenerate `audit_dashboard/index.html` from `template.html` in CI; verify live `dashboard_data.json` includes `extreme_conviction` / `hf_conviction_tier` when HF block is enabled.
- **Smart vs Active reconciliation:** Publish weekly `SMART_GATE_FUNNEL_STATS` (`tools/bus_post_smart_gate_funnel.py`) from the same JSON the site loads; alert on `passed=0` if product expects non-zero.
- **Conflict-free artifacts:** No `<<<<<<<` in tracked JSON/HTML/Pine; clean or gitignore generated noise under `alpha_engine/data/*.tmp`.

### P1 — Edge preservation (crypto-first, cross-asset aware)

- **Strategy×symbol registry** — Keep `tools/build_strategy_symbol_edge_registry.py` in the loop for fear/greed and other tier-S narratives; ensure dashboard scores consume registry deltas (`elite_scorer.py` / `quality_gates.py` affinity block — avoid double-count with `sharp_fear_greed`).
- **Conviction stack** — Maintain denylist for proven bad pairs (UNI/OP/APT × fear_greed) in `alpha_engine/conviction_stack.py` + smart engine; document in `DEFINITIVE_HEDGE_FUND_PIPELINE.md`.
- **Per-asset calibration** — Separate crypto vs non-crypto rank transforms or floors (per `docs/ASSET_CLASS_EDGE_SCORING_FLAWS_*` and closed-pick lessons).

### P2 — Institutional adjacent

- **Walk-forward calibration** — Use `tools/crypto_walk_forward_engine.py` / isotonic path (`docs/REDIS_BUS_CRYPTO_WF.md`) for **confidence → E[PnL]** mapping; do not calibrate on the same closes used to tune gates without purge.
- **Portfolio layer** — Correlation caps, gross/net limits, and drawdown brakes (`advanced_risk_system.py`, hedge-fund risk snapshot) wired to **position suggestions** on the audit UI (display-only first).
- **TCA and fills** — Even a stub schema for spread/slippage assumptions per asset class improves honest tier labels.

---

## 4. Suggested acceptance checks (for future PRs)

- `pytest tests/test_quality_gates.py tests/test_hf_quality_gate.py` (and scoring tests if touched).
- `python tools/audit_smart_gate_funnel.py` on a fresh `dashboard_data.json` snapshot.
- No regression: **Tier A** bear shorts and **zeroed ml_score** design per `GOLDEN_STANDARD_ACTION_PLAN.md` peer review on Redis bus — do not apply blanket crypto SHORT blocks or ml floors without exemptions.

---

## 5. Redis bus

Topic **`AUDIT_HF_GAP_AND_ENHANCEMENTS`**: `tools/bus_post_audit_hf_gap_enhancements.py`.

---

## References (in-repo)

- `DEFINITIVE_HEDGE_FUND_PIPELINE.md` — edge map and phase plan  
- `docs/HF_MERGED_EXECUTION_PLAN_2026-04-02.md` — merged roadmap  
- `docs/AUDIT_PICKS_EDGE_ANALYSIS_2026-04-06.md` — live JSON analysis  
- `TRACE_LOG.MD` — pipeline trace  
- `docs/REDIS_BUS_SCHEMA.md` — fleet envelope
