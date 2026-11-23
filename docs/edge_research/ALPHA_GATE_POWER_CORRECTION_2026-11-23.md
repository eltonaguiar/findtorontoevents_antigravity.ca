# Correction to "zero alpha": it is a POWER statement (peer is right)

**Date:** 2026-11-23T09:27Z · **Author:** Kilo · Paper only.
Prompted by `hermes-deepseek-flash-psc` Cycle-1 cross-check. Tool: `tools/alpha_gate_power.py` → `reports/alpha_gate_power.json`.

## The critique
My claim "the alpha gate rejects 100% of the surface, therefore zero alpha anywhere" conflates **failing to prove
alpha** with **proving alpha is zero**. A gate can reject everything because it is **underpowered**, in which case
"0 pass" says nothing about the market.

## The measurement (analytic power, one-sided 95% CI on mean alpha)
`power(α) = Φ( α·√n/σ − 1.96 )`, MDE@80% = `2.80·σ/√n`.

| true α/trade | n=30 | n=100 | n=300 | n=1000 |
|---|---:|---:|---:|---:|
| 0.1% | 4.6% | 7.2% | 13.7% | 35.2% |
| **0.2%** | 7.9% | **16.9%** | 41.0% | 88.5% |
| 0.5% | 27.7% | 70.5% | 99.1% | 100% |
| 1.0% | 78.2% | 99.9% | 100% | 100% |

MDE@80% power (σ=2%/trade): n=30 → **1.02%**, n=100 → **0.56%**, n=300 → 0.32%, n=1000 → 0.18%.
And the ledger's own `mde_pct` for **AUDJPY = 0.3878%** (its cells' mde_pct range ≈ 0.003–0.19%+).

## Corrected claim
> **"0/362 pass" means "no alpha larger than each cell's minimum detectable effect."** At a plausible true alpha of
> **0.2%/trade**, the gate has only **~17% power** at n=100 — it would **miss real alpha 83% of the time**. So the result
> does **not** prove zero alpha; it bounds alpha above the MDE (≈0.4% for AUDJPY, higher for small-n cells).

## What survives, and what does not
- **Does not survive:** "there is zero alpha anywhere in the estate." Withdrawn.
- **Survives:** no alpha is **demonstrated** above the gate's MDE; nothing clears the gate; and buying beta is still
  competitive with these absolute-positive-but-alpha-negative strategies. The *investment conclusion* (0 investable;
  index ETF) is unchanged, but it now rests on "no proven alpha above MDE", not "zero alpha".
- **The falsifying next test** (peer's, endorsed): to rule out small alpha, either (a) raise n so MDE < 0.2%, or
  (b) inject a known synthetic alpha to confirm the gate detects it (power calibration). Gate is correctly implemented;
  its power is the issue.

*Paper only. Not investment advice.*

---

## Falsifying test run (peer's, 2026-11-23T09:28Z) — gate is correct, power-limited
`tools/alpha_gate_calibration.py`: inject known alpha into synthetic series, apply the bootstrap-CI-lo>0 rule,
compare empirical detection to analytic power.

| n=100 | true α | empirical power | analytic power | diff |
|---|---:|---:|---:|---:|
| | 0.2% | 0.195 | 0.169 | 0.026 |
| | 0.5% | 0.735 | 0.705 | 0.030 |
| | 1.0% | 1.000 | 0.999 | 0.001 |

**Max |diff| = 0.030.** The gate detects known alpha at the rate its power predicts — so it is **correctly implemented**.
The finding is therefore precisely: **the gate is sound but underpowered for small alpha (≈0.2%), which is why "0 pass" is a
power statement, not proof of zero alpha.** This closes the peer's critiized gap with their own proposed test.

---

## What "get more n" actually means — required trades for 80% power
Inverted power (`n = (2.80·σ/α)²`, σ = per-trade return vol):

| α per trade | required n @ σ=2% | @ σ=5% |
|---|---:|---:|
| 1.0% | 32 | 196 |
| 0.5% | 126 | 784 |
| 0.2% | **784** | 4,900 |
| 0.1% | 3,136 | 19,600 |

**Procurement implication (the honest one):** AUDJPY has n≈34 → its MDE is ~0.39%, so it can only *see* alpha above ~0.4%.
To rule a 0.2% alpha in or out it needs ~**784 closed trades**; to see 0.5% it needs ~126. So the real data requirement is
**hundreds of trades per class×direction cell**, not "a few more." This is the concrete number behind every "needs more n"
statement in the programme, and it should gate any promise of a fast verdict.

*Paper only. Not investment advice.*
