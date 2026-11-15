# final_v5 — Childlike-Airport (2026-11-14T23:06:42Z)

**Reviewer:** Kilo (Glyph Cluster) — worktree `childlike-airport`  
**Scope:** 24h financial-prediction review (local + `origin/main`), peer `final_v4` cross-check, finalized plan, QA/PnL validation plan, MF/ETF viability/picks assessment, and risk-management webpage artifact. Evidence synthesis only; no production trading/deployment claim.

## Bottom line (conservative)
- **No strategy/asset class is proven reliably profitable or money-ready.** Measurement/integrity remains the blocker (stale/unresolved picks, PnL unit/sign/calc defects, stop/fill semantics, 0.25% regime coverage, single-source concentration, multiple-testing/benchmark failures). See `01_24h_review/24H_REVIEW.md`.
- **Best validation candidates (not money-ready):** (1) **Crypto Vol-Targeted TSMOM / IT-005** (7.4y CAGR 23.0%, Sharpe 2.13, PF 1.40, MDD −17.4%, bootstrap CI [1.25,3.25]) and (2) **Crypto Regime-Filtered VWAP-MR core (BTC,ETH,SOL,XRP,ADA)** (v11 PF 1.435 Sharpe 7.10 MDD 3.5% n=65; v12 pooled PF 1.210 Sharpe 3.758 MDD 9.994% n=129, **PBO 0.489 fails strict <0.3**). Both require net-of-cost, benchmark-relative, bear/subperiod, leak-safe OOS and paper-forward proof.
- **MF/ETF:** not currently a proven trading edge in this system. Low-cost, $0-min, no-load MF/ETF sleeves are plausible **validated baseline/overlay** candidates only if data pipelines, marks, and costed walk-forward/paper evidence are built; current evidence is insufficient/misaligned (ETF verdict insufficient, MF wiring/closed evidence gaps). See `06_picks_probability_risk/MF_ETF_PICKS.md`.
- **Picks showing 0% P/L:** cannot be assumed real or false without per-pick validation. 0% can reflect flat mark, stale/unquoted price, unresolved lifecycle, or unit/coercion bugs. QA must mark `VALIDATED_ZERO` / `SUSPECT_ZERO` / `UNQUOTED` / `STALE` with explicit reason. See `05_qa_plan/QA_PLAN.md`.

## Deliverables
| Path | Purpose |
|---|---|
| `01_24h_review/24H_REVIEW.md` | 24h remote/local/peer review |
| `02_finalized_plan/FINALIZED_PLAN.md` | Finalized, gated improvement/validation plan |
| `03_peer_crosscheck/PEER_CROSSCHECK.md` | Cross-check of peer `final_v4` packages |
| `04_proposed_edits/PROPOSED_EDITS.md` | Concrete proposed edits (adjudicated) |
| `05_qa_plan/QA_PLAN.md` | QA: 0% PnL market-data validation + blank-field checks (open & recently closed) |
| `06_picks_probability_risk/MF_ETF_PICKS.md` | MF/ETF solid-pick candidates with probability, risk, risk-adjusted, methodologies |
| `07_risk_management_web/index.html` | Standalone risk-management webpage |

## Promotion gates (all required before any money-ready claim)
Clean/provenanced data; net-of-realistic-costs OOS/walk-forward; benchmark-relative; stability (no drift/regime-only luck); **PF≥1.5 target (≥1.2 contextual), Sharpe≥1.0, MDD<20% (prefer <15%), WR contextual, PBO<0.3, DSR>0.95 (effective-N), n≥100 (≥500 preferred crypto)**; no leakage; independent reproduction; monitored paper-forward; explicit kill-switch. Mutual funds/baselines judged net-of-fee vs risk-matched benchmark, not on raw alpha alone.
