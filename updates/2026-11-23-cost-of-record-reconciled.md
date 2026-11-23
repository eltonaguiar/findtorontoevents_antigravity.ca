# Five round-trip costs, 10× apart — reconciled, and no verdict flips

**Date:** 2026-11-23
**Backlog:** A1–A4 in `docs/BACKLOG_100_2026-11-23.md`
**Files:** `tools/cost_of_record.py` (new), `reports/cost_of_record_2026-11-23.json` (generated)
**Result:** the programme carries **five** equity round-trip costs spanning **4.98 → 50.00 bp (10.04×)**. Four of the five are used to make published alive/dead decisions. Only one is measured. At the measured cost of record, **no class flips** — the "0 of 6 survive" headline is cost-robust.

---

## What was broken

`alpha_engine/backtest/engine.py:115` defaults to `CostModel.interactive_brokers()`:

```python
self.cost_model = cost_model or CostModel.interactive_brokers()
```

That factory is **entirely assumed** — `slippage_bps=5`, `spread_bps=3`, `exchange_fee_per_share=0.003`, `ecn_fee=0.0035`, `commission_per_share=0.005` — with no measurement and no cited source. It computes to **16.52 bp** round trip at a $50,000 position.

Meanwhile the **only measured** model in the repo, `questrade_canada()` at **4.98 bp**, has **zero call sites**. So the programme measured a cost and then ran every backtest on a different, invented one, at 3.3× the measured value.

That is not a coding bug, it is a *decision* bug: verdicts computed at 50bp and at 4.98bp are not comparable, so "0 of 6 classes survive" was five different claims sharing one sentence.

## Measured — the five costs in flight

| id | round trip | provenance | verdict-grade? |
|---|---:|---|---|
| `questrade_measured` | **4.98 bp** | MEASURED, n=191 names, 238,810 daily + 356,271 minute bars | no — zero call sites |
| `freebuff_upper_bound` | 12.07 bp | UPPER BOUND, 13 symbols; author states it is superseded | yes (zoo EQUITY) |
| `ib_default` | 16.52 bp | **ASSUMED**, production default, 4/7 fields with no source | yes (production) |
| `zoo_breakout_25bp_per_side` | 50.00 bp | ASSUMED stress case, not a measured cost | yes (zoo breakout) |
| `subq_forex` | 7.53 bp | CLAIMED, `reports/fx_meanrev_cost_sweep/sweep.json`, not reproduced | yes (zoo FOREX) |

**Cost of record = 4.98 bp** (2× stress = 9.96 bp), because it is the only measured number.

## The honest caveat that cuts against my own pick

`questrade_canada()` sets `commission_per_share=0.0`, `ecn_fee=0.0`, `exchange_fee_per_share=0.0`. Those are **zero by construction**, not measured. So 4.98 bp is a **lower bound**: it is the *spread* cost only, excluding any commission. For a stock trade at a real broker the true round trip is 4.98 bp **plus commission**.

Consequence: "cost of record = 4.98bp" should be read as *the floor*, and a test that fails at the floor fails for signal reasons, not cost reasons. That is the conservative direction for a kill-based programme, which is the right direction to be wrong in.

## Does any verdict flip at the cost of record?

No — and that is the genuinely useful finding.

| class | gross | cost used | net | net at 4.98bp | flips? |
|---|---:|---:|---:|---:|---|
| FOREX mean-rev | 4.30 bp | 7.53 | **−3.23** | **−0.68** | no |
| ETF breakout | 4.70 bp | 5.10 | −0.40 | −0.28 | no |
| EQUITY breakout | PF 0.9917 | 50.0 | PF<1 | PF<1 | no — signal failure |

Two precise statements fall out:

1. **FOREX is not a decisive kill.** At the cost of record its net is **−0.68 bp**, which is inside measurement noise rather than clearly negative. It should be reclassified **CANDIDATE-CONDITIONAL — cost unpublished**, not DEAD. The 7.53 bp that killed it is claimed and unreproduced; if the true cost is under 4.30 bp the sign flips.
2. **EQUITY's breakout death is cost-robust.** PF 0.9917 < 1 at 25 bp/side, and PF < 1 survives *any* cost reduction because it is a hit-rate/payoff failure. That verdict stands regardless of which of the five costs is right.

## How it was verified

```
python3 tools/cost_of_record.py
  -> spread 4.98 .. 50.00 bp = 10.04x
  -> cost of record 4.98bp, 2x stress 9.96bp
  -> verdict-grade costs NOT measured: ib_default, freebuff_upper_bound,
     zoo_breakout_25bp_per_side, subq_forex
  -> classes that flip: [] (none)
written: reports/cost_of_record_2026-11-23.json
```

Factory provenance audit — number of ASSUMED fields per factory:

| factory | round trip | ASSUMED fields |
|---|---:|---|
| `interactive_brokers` | 16.52 bp | 4/7 |
| `questrade_canada` | 4.98 bp | 4/7 (3 of which are 0 by construction) |
| `zero_cost` | 0.00 bp | 4/7 |

## What remains (not done here)

- A5/A6/A7 — reproduce FOREX 7.53bp, BOND 42.64bp, CRYPTO 12–20bp from their committed artifacts. Until then those three costs are citations, not measurements.
- A3 has not been written into `costs.py` as a documented default — that changes production behaviour and needs the operator's call on which broker the programme is actually trading through.
- A11 — COMMODITY still uses a 4.97 bp **PROXY** inherited from EQUITY. It is labelled a proxy in every output, but it is not measured.

Zero capital sanctioned. Paper only. Not investment advice.
