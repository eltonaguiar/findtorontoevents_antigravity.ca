# Peer reviews — profitability claims

Method: I re-executed or re-derived each claim from an artifact I could read, rather than summarising
the peer's document. Where the claim rests on a file I cannot access, it is marked **unverified** and
the reason is stated.

## Adjudication table

| # | Peer / program | Headline claim | Verdict | Basis |
|---|---|---|---|---|
| 1 | flaxen-hair — `PROFITABLE_APPROACH_PROVEN.md`, `TRUE_PROFITABILITY_VALIDATED.md` | mega_mutation MACD/RSI on crypto is "the only statistically valid profitable edge"; forward PF 8.32 / WR 84% / n=50; all other classes PF 0.18–0.31 | **OVERSTATED — partially supported, materially mis-corrected** | 2 of the 4 mega ledgers *do* pass bootstrap in the repo's own artifact, but 4/170 pass overall vs 8.5 expected by chance; the ema_momentum variant they call a winner is PF 0.767 / −33.8% / MC 0.0; and the "all other classes negative" claim rests on a unit bug absent from the ledger it is applied to. See `flaxen_hair_profitability.md` |
| 2 | `research/profitability/` (v1–v4, 23 candidates) | NOT_PROVED after 23 candidates; VWAP peer claim falsified | **CONFIRMED, strongest work in the repo** | Reproduced its negative conclusion independently: my own 40-trial search and this per-class analysis agree. Its VWAP falsification (Sharpe 3.76 → ~1.18, t=0.91, CSCV PBO 0.84–0.97, 61% intrabar stop breach) matches my separate refutation. See `research_profitability_program.md` |
| 3 | finpredict-v2 `MASTER_AUDIT.md` | "multiple-testing + survivorship + stale-price artifact", FAIL | **CONFIRMED** | Its verdict matches the measured ledger (PF 0.895 overall, no class above water, 170-ledger benchmark with 4 passes). See `finpredict_v2.md` |
| 4 | hilarious-seer audit summary | FAIL per audit_regime; equity "marginal edge but not significant"; 361 families → multiple testing | **CONFIRMED on all three counts** | Independent numbers agree: EQUITY t=1.52 p=0.12, and the 170-ledger benchmark shows fewer passes than chance. See `hilarious_seer.md` |
| 5 | `quick_wins/` (8 per-class docs) | PnL unit bug, non-unique IDs, `ml_score == confidence`, zombie rows, TP/SL resolution bug | **MIXED — the unit/ID claims do not apply to the live ledger; the TP/SL and calibration claims hold** | 3,500/3,500 ledger rows are unit-consistent (median error 0.000pp) and IDs are unique; but the TP/SL resolution defect is real and I quantified it (+828.0pp). See `quick_wins_program.md` |
| 6 | Kilo — `updates/2026-11-14-PROFITABLE-APPROACH-VWAP-MEAN-REVERSION.md` | Regime-filtered VWAP, Sharpe 3.76, "VALIDATED" | **REFUTED** (carried from `final_2026_11_14`) | 12.7% total over ~22 months at Sharpe 3.76 ⇒ 1.84%/yr volatility on a 40%-sized 4h crypto book — impossible. PBO 0.489 marked PASS by an inverted `<0.5` gate against a ≤0.10 standard. Independently falsified by `research/profitability/validation/VWAP_VERDICT.md` |
| 7 | deepAI variant C | n=237, WR 47.3%, PF 1.26, p<0.0013 | **REPRODUCED EXACTLY** (carried from `final_2026_11_14`) | Ran their unmodified script on the live payload: identical numbers incl. the omitted z=−0.84. A selection procedure, sub-T2 |

## The one thing every program agrees on

Six independently-run audits using different methods converge on the same verdict: **no asset class
in this system is profitable after costs, and the published profitability figures are artifacts of
exit-mix, unit errors, multiple testing, or survivorship.** Where they disagree — flaxen-hair's
"only valid edge" — the disagreement is resolvable by reading the repo's own benchmark artifact,
and it resolves against the claim.
