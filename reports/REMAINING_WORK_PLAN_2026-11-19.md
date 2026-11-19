# Remaining Work Plan — 2026-11-19 (post-Sprint 1-4)

## Goal
Complete the remaining high-impact items to make the money-maker strategy "proper and viable."

## Remaining items (prioritized)

### P0 — Blocks money-readiness
| # | Item | Status | Effort | Notes |
|---|---|---|---|---|
| R1 | Sleeve ingestion into audit3 tribunal | OPEN | Medium | Add top_sleeves (AuditEnsemble_LONG, CorrKama, etc.) to audit3 cell scoring. Single-source flag. |
| R2 | ML recalibration (upstream generators) | OPEN | High | _calibrate_confidence exists in score_booster.py but upstream generators not fixed. Need to find and fix the source of inverted confidence. |

### P1 — Improves signal quality
| # | Item | Status | Effort | Notes |
|---|---|---|---|---|
| R3 | Random-entry MC wiring | OPEN | Medium | benchmark_closed_ledger.py has random-entry MC. Wire into audit3 for timing-null companion report. |
| R4 | Mutual fund screener weekly workflow | DONE | Low | Created + committed. Needs testing. |
| R5 | ETF forward pilot unstick | PARTIAL | Medium | Writer added to faber_taa_pilot.py. Need more closes to reach n=100. |
| R6 | Hypothesis status normalization | OPEN | Low | 99 hypotheses, fragmented vocabulary (PRE_REGISTERED vs PRE-REGISTERED). |
| R7 | Bond screener | OPEN | Medium | Doesn't exist. Duration + credit + real yield. |
| R8 | Commodity term-structure rebuild | OPEN | Medium | Replace falsified COT with backwardation/contango + inventory. |
| R9 | Mutual fund screener wiring | PARTIAL | Low | Runner + workflow created. Needs testing in CI. |

### P2 — Hygiene/UX
| # | Item | Status | Effort | Notes |
|---|---|---|---|---|
| R10 | Collapse dual PF/WR per class | OPEN | Low | One canonical figure + window label. |
| R11 | Demote post-hoc segment numbers | OPEN | Low | Behind toggle. |
| R12 | Remove DEAD cells from "Best filter" table | OPEN | Low | Stocks PF 0.77. |
| R13 | Disambiguate "PROVEN" | OPEN | Low | Strategy vs trust-tier vs PROVEN_T2. |
| R14 | Re-test schedule for killed cells | OPEN | Low | No "since when" on kills. |
| R15 | Serve reports/ for live forward clock | OPEN | Medium | Pod registry static snapshot. |
| R16 | CSV export on audit3 tabs | OPEN | Low | No export button. |
| R17 | Fix "unknown" strategy rows | OPEN | Low | n=260, WR 28.1%. |
| R18 | Fix class mismatches (11 rows) | OPEN | Low | FOREX labeled CRYPTO, CT=F labeled FUTURES. |
| R19 | Fix FUTURES n=4 vs intrabar n=52 | OPEN | Medium | Large discrepancy. |
| R20 | Fix UEPS n=0/100 | OPEN | Medium | No IV-attainment resolver wired. |

### Sprint 4 — $2,000 micro-futures ORB
| # | Item | Status | Effort | Notes |
|---|---|---|---|---|
| R21 | 30-session paper trading protocol | OPEN | 6 weeks | ForTraders methodology. |
| R22 | Shadow mode (live-plus-shadow) | OPEN | 2-4 weeks | NeuraTrade PR #260. |
| R23 | Live micro-size (1 contract, 1% risk) | OPEN | Ongoing | Kill switch, progressive drawdown ladder. |
| R24 | Parallel variant testing (5 ORB variants) | OPEN | 2-4 weeks | Never promote without ≥2 weeks shadow. |

## Execution order (by impact/effort ratio)

1. **R6** (hypothesis normalization) — Low effort, improves data quality. START HERE.
2. **R3** (random-entry MC wiring) — Medium effort, completes audit3 timing-null.
3. **R2** (ML recalibration) — High effort, but critical for signal quality.
4. **R1** (sleeve ingestion into audit3) — Medium effort, elevates P0 finding.
5. **R8** (commodity term-structure) — Medium effort, replaces falsified COT.
6. **R7** (bond screener) — Medium effort, completes asset-class coverage.
7. **R5** (ETF pilot unstick) — Medium effort, needs more closes.
8. **R10-R20** (P2 hygiene) — Low effort, batch these.
9. **R21-R24** (Sprint 4) — Long effort, depends on R21 starting first.

## What "proper and viable" means

A money-maker strategy is "proper and viable" when:
1. It has POSITIVE selection alpha (currently NEGATIVE: -0.128%)
2. It survives cost stress at 2× slippage (G9 gate)
3. It has n≥100 forward rows with intrabar first-touch
4. It passes BH multiple-testing correction (q≤0.1)
5. It has stable split-half (both halves net mean > 0)
6. No single symbol > 60% of trades
7. No single source > 90% of trades
8. DSR ≥ 0.95

Current status: 0/8 criteria met for any strategy. The only viable path is:
- ETF TAA (Faber GTAA: Sharpe 0.915, MDD -20.5%, OOS 1.13) — risk reduction, not selection
- Mutual fund passive core (8 funds pass hard gates) — lowest risk

All short-term strategies are research/sandbox until the forward gate promotes them.