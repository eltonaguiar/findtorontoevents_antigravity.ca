# ITERATION-003 — Out-of-sample time-split validation (2026-11-14 18:24Z)

Pre-registered the sole candidate `rs-breakout-scout` (from ITERATION-002) as a single hypothesis and ran a 70/30 in-sample/out-of-sample time split on the clean closed ledger, plus the two secondary candidates. A single pre-registered OOS test needs only nominal significance (no 683-way correction).

## Results

| strategy | IS n/PF/t | OOS n/PF/t | OOS p | verdict |
|---|---|---|---|---|
| `rs-breakout-scout` | 93 / 1.695 / 2.07 | 40 / 1.539 / **1.16** | 0.124 | **OOS FAILS** (t decays 2.07→1.16; not significant) |
| `luxalgo_confluence` | 902 / 1.070 / 0.88 | 388 / 1.235 / 1.85 | 0.032 | **FAILS PF bar** (OOS PF 1.235 < 1.5) |
| `vol-contraction-scout` | 56 / 1.427 / 1.06 | 25 / **0.487** / −1.37 | 0.915 | **OOS REVERSES** (PF 1.43 → 0.49, loses money) |

- `rs-breakout-scout`: the "best" edge decays from t=2.07 in-sample to t=1.16 out-of-sample — the exact signature of in-sample selection. Its OOS PF (1.539) is a fluke of a 40-trade window; the mean is not significant (p=0.124) even under the lenient single-hypothesis framing.
- `vol-contraction-scout`: a textbook overfit — profitable in-sample (PF 1.43), **reverses** out-of-sample (PF 0.49, mean −1.06%).
- `luxalgo_confluence`: OOS PF improves to 1.235 but stays below the 1.5 bar; its t=1.85 is marginal and it's a CRYPTO copy-trader artifact (single-source).

## Final research conclusion (iterations 001–003)

**No profitable approach is provable on this system.** The three honest iterations establish, with exact numbers:

1. The apparent "edges" (87–97% WR, PF 10–56) are frozen-price/fabricated artifacts in the ACTIVE/summary surfaces, not real returns.
2. The clean closed ledger is **net-negative**: n=3,488, sum PnL **−469.5%**, mean −0.135%/trade.
3. The single surviving candidate `rs-breakout-scout` (PF 1.65) **fails Bonferroni** across 683 strategies (p=0.009 vs α=7.3e-5) and **fails out-of-sample** (t 2.07→1.16, p=0.124).
4. Every secondary candidate loses money or reverses out-of-sample.

**Recommendation:** size all strategies to zero for live capital; keep the system as a research/telemetry harness only. The real fixes are the data-integrity items already in the master plan (`master-plan/PLAN.md` Phase 0) — until prices are honestly marked and the ledger is clean, no edge can even be evaluated, let alone proven.

This concludes the research loop honestly: the answer to "is there a provably profitable approach" is **no**, supported by multiple-testing-corrected in-sample tests and out-of-sample reversal, not by fabrication.
