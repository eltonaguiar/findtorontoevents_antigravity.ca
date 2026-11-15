# 02 — Finalized Plan (Gated, Evidence-First)

## Objective
Move from "unmeasured/unreliable" to "answerable" by fixing measurement, then running frozen, benchmark-relative, net-of-cost validation. **Do not claim profitability before gates pass.**

## Phase 0 — Freeze & integrity (P0, blocks all claims)
1. **Canonical truth:** single reconciled cohort (IDs, lifecycle, terminal states) with `filter_hash`, `pnl_source`, `resolution_method/kind`, `quote_status`, timestamps/timezones.
2. **PnL correctness:** recompute PnL from verified entry/exit/current marks and side; eliminate `pnl*=100` heuristics, null/zero-entry coercion, sign/calc mismatches; store gross & net (fees/spread/slippage/funding/roll/borrow per class).
3. **Mark/provenance:** remove hardcoded/expected prices; restore live feeds; label `UNQUOTED/STALE/ESTIMATED`; never silently coerce missing to 0.0/0%.
4. **Fill realism:** gap-aware/conservative intrabar fills; investigate SL_HIT-inside-stop (B4) and route known mis-routed systems through resolver.
5. **Freshness & sync:** enforce SLA; reconcile `live_picks`/`audit_trail`/dashboard/JSON/MySQL/bond/ETF sources; drain zombies/expired bias.

**Exit:** deterministic reconciliation report with 0 critical unit/sign/calc mismatches on audited cohort; freshness green.

## Phase 1 — QA & validation harness (P0/P1)
1. Execute `05_qa_plan/QA_PLAN.md`: validate every 0% PnL and every blank/null critical field for **open and recently closed (≤30d)** picks against market data/reasonableness.
2. Build/refresh fixed evaluation windows, leakage-safe labels, benchmark series per class, and reproducible configs/seeds/hashes.
3. CI gates: parse/lint, PnL/sync/resolver unit tests, freshness/TTL fail, loop safety; record trial counts.

**Exit:** QA report with per-pick disposition (`VALIDATED_*`/`SUSPECT_*`/`UNQUOTED`/`STALE`) and reproducible harness.

## Phase 2 — Pre-registered candidate tests (P1, only after Phase 0–1)
| Slot | Candidate | Test | Pass (minimum, pre-registered) | Kill |
|---|---|---|---|---|
| A | Crypto Vol-Targeted TSMOM (IT-005) / POSITION-only sub-bucket | Bear+subperiod, net-of-cost, vs B&H/risk-matched, frozen params | PF≥1.3–1.5, Sharpe≥1.0, MDD<20% (pref <15%), bootstrap/DSR positive, stable; n≥100 forward | any gate fail / drift>30% / drawdown breach |
| B | Crypto VWAP-MR core (BTC,ETH,SOL,XRP,ADA) | >730d 4h walk-forward, cost stress 20/30/50bps, CSCV/PBO, net | PF≥1.2, Sharpe≥1.0, MDD<15–20%, **PBO<0.3**, DSR>0.95, n sufficient | PBO≥0.3, OOS decay, unstable subperiods |
| C (parallel, non-crypto baseline) | Equity/ETF low-fee trend/TAA or $0-min MF/ETF sleeve | Net-of-fee OOS vs SPY/risk-matched benchmark, next-NAV/MF constraints | benchmark-relative net edge or justified risk-adjusted overlay, controlled MDD | underperforms benchmark net-of-cost / no evidence |

- **Multiple testing:** register all trials; require DSR (effective-N) and BH/Bonferroni-adjusted significance; do not mine until pass.
- **Paper forward:** 90 days / n≥30–100 (per class liquidity) with live marks before any capital.

## Phase 3 — Gated promotion (P2, conditional)
- Promote only slots passing all gates with monitored paper-forward, position/risk limits, and automated kill-switch. Otherwise **wind down / keep as research**.

## MF/ETF-specific plan (viability = evidence-to-build)
- Build/repair: class wiring, symbol universe/marks, expense/load/NAV constraints, net-of-fee accounting.
- Evaluate low-capital/low-fee subset (e.g. FXAIX/FSKAX/SWPPX/SWTSX/FXNAX, SCHB/VTI/ITOT/BND/SGOV) as **baseline/overlay**, not alpha claim.
- Accept only with net-of-fee, benchmark-relative, risk-adjusted OOS + paper evidence and controlled drawdown.

## 90-day milestones
| Window | Deliverable | Go/No-Go |
|---|---|---|
| W1–2 | Phase 0 integrity + CI/freshness + 0%/blank QA | trusted cohort or halt claims |
| W2–4 | Repro runs for A/B/C (frozen), trial registry | continue only if pre-reg metrics computable & sane |
| W4–10 | Paper-forward A/B/C with live marks | advance if interim gates on-track |
| W10–13 | Gate review vs benchmarks/costs/DSR/PBO | promote (capped) / iterate / retire |

## Kill conditions (any)
Gate failure in paper (2 consecutive checks), monthly drawdown > cap (e.g. −20%), data staleness > SLA, unresolved critical PnL/mark defect, or benchmark-relative net underperformance with no stable subperiod edge.
