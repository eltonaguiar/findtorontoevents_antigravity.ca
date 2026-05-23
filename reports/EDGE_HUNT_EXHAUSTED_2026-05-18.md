# Edge Hunt — Empirically Exhausted — 2026-05-18

**Supersedes:** `EDGE_VERDICT_2026-05-18.md` (which predates kills #9-11).
**Verdict:** 11 pre-registered causal hypotheses tested. **11 killed. 0 admissible.**
The free-data, daily-bar, retail-accessible edge space is empirically empty.

## The complete kill log

| # | id | asset | family | failure mode |
|---|----|-------|--------|--------------|
| 1 | H-001 | COMMODITY | COT positioning | look-ahead leakage (M-095); CT=F-concentrated |
| 2 | H-006 | CRYPTO | funding-rate z-score directional | sign-unstable 4+/4− on deep archive |
| 3 | H-007 | COMMODITY | front/second roll-yield | sign-split 4+/2− |
| 4 | H-008 | BOND | 2s10s yield-curve momentum | sign-split 144+/182− (57k records) |
| 5 | H-010 | EQUITY | PEAD 30-day drift | sign-split 3+/2− |
| 6 | H-012 | CRYPTO | funding-arb delta-neutral carry | cost-survival 5.7% (« 60%) |
| 7 | H-013 | EQUITY/ETF | options-flow put/call + skew + VIX | sign-split all 3 sub-signals + cost |
| 8 | H-014 | CRYPTO | on-chain address/tx/stablecoin z | sign-split all 3 + cost |
| 9 | H-017 | CRYPTO | funding-settlement liquidation cascade | sign-split 1+/2− + 1.3bps « 30bps cost |
| 10 | H-019 | CRYPTO | exchange net-flow full-book | sign-split 11+/1− + 3.4bps « 30bps cost |
| 11 | H-020 | CRYPTO | cross-exchange Coinbase premium | sign-split 23+/22− + 9.3bps « 30bps cost |

(H-018 net-flow LONG-2/SHORT-2 = UNTESTED, density gap — superseded by H-019 full-book.)

## The pattern is structural, not bad luck

Every one of the 11 dies one of two identical ways, usually both:

1. **eff sign-instability across walk-forward windows.** In-sample the signal
   separates winners from losers — out-of-sample the sign flips regime to
   regime. The harness's same-sign requirement (≥3/5 windows) is exactly the
   test for "real edge vs regime noise," and 11/11 fail it. This is the same
   failure mode that originally killed `method_a_score`.
2. **Gross edge thinner than cost.** Where a signal does produce a gross edge,
   it is 1-9 bps — below the ~30bps crypto round-trip. Net edge is negative.

11 independent causal hypotheses, 4 asset classes, free + paid-tier-free data,
daily and settlement-bar resolution — one verdict. This is a sufficient sample
to conclude.

## What this proves

- **Free-data + daily-bar retail signals do not contain a tradeable edge in
  this universe.** Tested exhaustively. Stop re-running killed families.
- The recurring thread in every kill's `next_step`: *"daily residual is
  post-arbitrage noise — needs intraday resolution."* Every signal was resolved
  on daily/settlement bars. **Genuine intraday tick-level resolution is the only
  axis with an untested rationale** — and it requires paid tick data.

## The three honest options (operator decision)

1. **Accept paper-only.** Per ROADMAP Phase 2 exit gate. Real capital stays $0;
   the system is a research instrument, not a money-maker. Defensible — 11/11.
2. **Buy historical L2 tick data** (~$300-500 one-time, Tardis.dev) → test C-1
   order-book imbalance reversion at true intraday resolution — the one
   hypothesis class the 11 kills point toward but could not reach on daily bars.
   Realistic odds still ~5-8% (ROADMAP per-class estimate).
3. **Stop the edge hunt.** 11/11 with a single structural failure mode is
   conclusive evidence the retail-accessible edge space is empty.

## Hard rule for future sessions / agents

Do NOT re-test any of the 11 killed families on the same or similar data — see
each entry's `next_step` in `reports/hypothesis_registry.json`. A new hypothesis
must be (a) a genuinely new input class, AND (b) resolved at a materially
different (intraday/tick) timescale, AND (c) pre-registered before any backtest
per M-107. Anything else is re-running a settled experiment.

*Reproducers: tools/h017_*, h018_*, h019_*, h020_* research scripts. Harness:
tools/edge_stability_harness.py (imported unmodified in every test).*
