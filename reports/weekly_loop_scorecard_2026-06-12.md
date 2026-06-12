# Weekly Loop Scorecard — 2026-06-12 (cycle #1 of the June 2026 edition)

Executor: /money-maker-ready-June112026edition · Plan: docs/MONEY_READY_MASTER_LOOP_2026-06.md
All numbers direct-SQL or fresh tool output this date; labels are (asset_class | n | timeframe).

## MEASURE (honest ledger, intrabar TP/SL first-touch SL-wins)
| class | n | WR% | PF | note |
|---|---|---|---|---|
| CRYPTO | 1155 | 32.4 | 0.727 | LONG 1051 @ 30.1%/0.684 vs SHORT 104 @ 55.8%/1.359 (INCIDENT#23) |
| COMMODITY | 115 | 34.8 | 1.048 | n=100 checkpoint executed 06-12: dedup 110→43 → FAIL (PF 0.64) |
| FOREX | 95 | 41.1 | 1.102 | n=100 gate ~days away (accruing ~5/run post-P0A) |
| EQUITY | 110 | 35.5 | 0.480 | FAIL |
| others | n<80 | — | — | measurement-only mode |

H1 guards: sign-coherence 0 ✅ · terminal NULL-pnl 164 (<200) ✅ · **7d emission dup-rate 71.5% ❌** (blocks promotion stages per preflight) · 14d resolved/emitted 42.1% · one-sided-source pathology filed (FINDING#18).
Forward lane (stamped_n=1157): crypto_rsi5070_us 108 @ 47.2/1.535 (last30 48.3/1.454 — retention holds); forex_trend_aligned 16 @ 68.8/5.333; baselines rotting (CRYPTO baseline last30 28.9/0.545).

## DIAGNOSE (rubric 0=red 3=green; hash-locked below)
| hyp | CRYPTO | COMMODITY | basis |
|---|---|---|---|
| H1 measurement | 3 | 3 | guards green; P0A lane verified ×3 runs; kimi 141,344-row purge clean; recency unfrozen |
| H2 backtest-only | 1 | 1 | #132 walk-forward stale still blocks formal scoring; handoff OOS gate Jul-9 |
| H3 data scarcity | 2 | 1 | P0A unblocked accrual; COMMODITY thin + 2-symbol concentration structural |
| H4 external signals | 1 | 1 | one-sided social/copy sources unkilled (FINDING#18) |
| H5 coverage | 1 | 2 | 42.1% resolved/emitted; 71.5% dup inflates denominator; CRYPTO 157 bad-geom unresolvable |

## ACT (this cycle)
- COMMODITY: **H-111 pre-registered** (symbol-tier mutation, mutate-before-kill after the FAIL verdict; discovery sample excluded; sizing structurally barred by 2-symbol concentration). Registry rescued: 36 local-only pre-registrations committed (41fbfa4d45; FINDING#17).
- CRYPTO: forward-confirm in flight (rsi5070 → n≥150 gate ~Jun-25); P0C LONG-block execution-ready (INCIDENT#23) with the forward-test exemption REQUIRED.
- Plumbing shipped same-day (#129 discipline): DB_PASS_BACKUPS (983413526f), recency unfreeze (d2f56ae23f), archive merge-block (f2afe5773c) — all verified green on run 27407104548.

## FORWARD gates
None due today. Calendar: pead_equity Jun-14 (MUST judge payoff asymmetry, not WR — KILO evidence) · FOREX n=100 ~days · rsi5070 n≥150 ~Jun-25 · handoff OOS Jul-9.

## RATCHET deltas
Filed this cycle: INCIDENT_CRYPTO#21/#22/#23, INCIDENT_OVERALL#134/#135, ENH#164/#165, FINDING#17/#18. ML estate audited (24 surfaces). 3 masked-failure CI bugs fixed+verified.
**Next-cycle add (from the 3× masked-failure lesson): H1 gains a freshness assertion — every critical JSON generated_at < 2h, asserted, never inferred from green checks.**

## Rubric hash-lock
scores = CRYPTO:[3,1,2,1,1] COMMODITY:[3,1,1,1,2] (H1..H5, 2026-06-12)
sha256(rubric+body) = b514ee12da163888
