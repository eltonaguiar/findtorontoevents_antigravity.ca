# TESTING_PROTOCOL Summary — Agent Vetting Checklist
**Source:** Claude (2026-06-01T00:08 UTC) — condensed from TESTING_PROTOCOL.MD + PR #410

## Per-Pick Vetting (Layer 2.5 — apply BEFORE forward test)
18 rules, first fail = reject. See TESTING_PROTOCOL.MD for full details.

## Per-Strategy Promotion (Layers 0-7)
| Layer | Pass bar |
|-------|----------|
| 0 | Data integrity (adjusted prices, UTC, slippage metadata) |
| 1 | IS backtest (fixed universe, params+seed) |
| 2 | OOS split (IS 70% / OOS-val 15% / holdout 15%) |
| 2.5 | Quality gates (18 rules on every pick) |
| 3 | Walk-forward (2yr train + 3mo forward, ≥200 picks) |
| 4 | Significance (BH-FDR + Holm-Bonferroni, NOT plain Bonferroni) |
| 5 | Robustness (bootstrap/MC 10K, regime checks, FGI, hold-time) |
| 6 | Forward test (≥20 resolved, decay ≤15pp) |
| 7 | Promotion (n≥500, Wilson LB, Bootstrap PF LB, DSR>0.95) |

## Definition of Done
WF pass + corrected significance + bootstrap CI + forward positive + symbol coverage + Layer 2.5 pass + registry = DATA_VALIDATED/PRODUCTION + not REHAB/EXHAUSTED

## Live numbers source
money_ready_verdict.json + pf_registry.json (NOT the stale 2026-04 figures in the doc)
