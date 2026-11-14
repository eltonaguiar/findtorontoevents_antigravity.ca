# final_v2 / finpredict-v2 — Final Profitability Review

**Verdict:** no asset class has a proved edge; the live system is not profitable. This package is a
prioritized path to a defensible sleeve, not a profitability claim.

## Read order

1. `05_final/FINAL_V2_SYNTHESIS.md` — verdict, corrections, per-class priorities, peer review.
2. `05_final/PER_CLASS_PRIORITY_MATRIX.md` — the ranked table and experiments.
3. `02_per_asset_class_profitability/*.md` — one playbook per class.
4. `01_audit/CORRECTIONS_v2.md` — scoped corrections (exit_reason, PnL units, stop-fill, 170 ledgers).
5. `04_peer_reviews/FP6_final_v2_peers.md` — review of peers' final_v2 packages.
6. `01_audit/MASTER_AUDIT.md` + `03_research/profitability/` — the underlying evidence.

## Structure

```
final_v2/finpredict-v2/
  01_audit/            audit, sub/A–G, recommendations, CORRECTIONS_v2
  02_per_asset_class_profitability/  CRYPTO, EQUITY, ETF, FOREX, BOND,
                                     FUTURES, COMMODITY, MUTUAL_FUNDS + 00_INDEX
  03_research/         pre-registered v1–v4 program (protocols, runs, verdicts)
  04_peer_reviews/     FP1–FP6, PF/RR, VWAP replication/review, FP5 erratum
  04_actions/          Actions deep dive + 365-workflow matrix
  05_final/            FINAL_V2_SYNTHESIS, PER_CLASS_PRIORITY_MATRIX,
                       reference_final_2026_11_14/
  06_evidence/         manifests and provenance
```

## The short version

- **Best realistic paths:** futures TSMOM+carry, crypto funding/basis carry (capital-adjusted),
  bond curve carry/roll-down, equity PEAD/SUE, ETF covered-call/VRP.
- **Do first:** C0–C6 measurement fixes (PnL units, exits/fills, gate, dedup, quote surface,
  stop-fill fidelity). The crypto stop-fill defect alone explains 98.8% of the class loss.
- **Do not:** enable mega_mutation, build a MUTUAL_FUND signal class, run another price-only
  parameter sweep, or size real money before a clean forward OOS.

No fabricated numbers; `UNVERIFIED` items are marked in the per-class files and reviews.
