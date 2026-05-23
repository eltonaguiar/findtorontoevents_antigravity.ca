# Edge Hunt — Conclusion (2026-05-18)

**This supersedes the "path" framing in `reports/PATH_TO_PROVEN_EDGE_2026-05-18.md`.**
The gated route was run to its end. Read with `reports/EDGE_VERDICT_2026-05-18.md`.

## Result: 7 straight harness kills. Zero admissible edge.

Every candidate — the existing pick ledger, enriched features, and every
academically-grounded new signal — was put through `tools/edge_stability_harness.py`
(eff ≥ 0.30, same sign, ≥3/5 walk-forward windows). **None passed.**

| # | Candidate | Method | Kill reason |
|---|-----------|--------|-------------|
| 1 | `method_a_score` | walk-forward | sign-flips across regimes |
| 2 | `risk_reward` / R:R band | leakage-control | confound; n=17 after strip; sign-flips |
| 3 | COT / `cot_positioning` | 13yr no-look-ahead backtest | CT=F duplication leakage |
| 4 | `ml_enhanced` family (149 variants) | placeholder-stat audit | near-zero avg_loss artifact |
| 5 | qlib factors ×3 + regime score (Fork 1) | enriched-ledger harness | all 4 rejected; `pv_corr30` sign-flips |
| 5 | COMMODITY roll-yield (Fork 2 / H-007) | purged walk-forward | sign-unstable 4+/2− |
| 6a | BOND 2s10s slope-momentum (P1 / H-008) | continuous-position, 496 windows | sign-unstable 144+/182− |
| 6b | CRYPTO funding-rate z×basis (P2 / H-006) | 6yr / 4838 events, deep archive | sign-unstable 4+/4− |
| 7 | EQUITY PEAD / SUE (P4 / H-010) | 242 names, 6988 picks, 22 windows | sign-unstable 3+/2− |

The data excuses were eliminated, not worked around: H-006 got 6 years of
funding history (Fork 2 had 58 events); H-008 got 496 windows; H-010 got 242
names and 22 windows. Given real statistical power, **every signal exhibits the
same failure** — in-sample separation that does not hold a stable sign
out-of-sample. PEAD — the most out-of-sample-robust anomaly in the academic
literature — failed identically.

## What this means (honest, not defeatist)

This is no longer "we have not found the edge yet." It is a measured result:
**the input space this system draws from does not contain admissible edge** at
retail latency/cost. That space is price/volume-derived technicals, COT,
funding rate, futures term structure, and earnings surprise. All exhausted.

The harness itself is vindicated — it killed 7 candidates *in analysis, before
real money*. That is the kill-loop working, not failing.

## The remaining options — a genuine strategic fork (USER decision)

The in-house + academically-grounded candidate queue is **empty**. Three honest
paths, none of which is "run the harness on another derived signal":

1. **New input class — a program, not a sprint.** Order-flow microstructure
   (L2 book imbalance, trade-tape), options-implied signals (skew, dealer
   gamma, flow), or genuine alt-data. Requires new data acquisition + ingestion
   infrastructure. This is the only path with a non-trivial prior of finding
   edge, because it is the only one that adds *information the system has never
   seen*. Months, and likely paid data.

2. **Accept research-sandbox status.** Freeze the edge hunt. The system remains
   a paper/research environment. The harness stays as the admission gate so any
   future candidate is honestly judged. Zero capital at risk. The honest default.

3. **Execution / structure alpha, not signal alpha.** Stop hunting directional
   signals; pursue edge in market-making, funding-arb, or basis capture — where
   the "edge" is structural (you are paid to provide liquidity / carry) rather
   than predictive. Different system, different risk profile.

## Standing rules (unchanged, enforced)

- No score ranks/gates picks and no real money is sized until a signal clears
  `edge_stability_harness.py`. Today: nothing qualifies.
- Money posture: **paper-only.**
- Do not re-test any of the 7 killed families on the same sample (M-107).
- A gaudy PF / DSR / SPA / White's pass is necessary and nowhere near
  sufficient — every killed candidate had at least one of those.
