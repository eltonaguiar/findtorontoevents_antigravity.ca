# Is the equity cost constant 5–25× too high — and does that invalidate our KILLs?

**Date:** 2026-11-23
**Owner:** `copilot-cli-deepseek-flash`
**Tool:** `tools/cost_sensitivity.py` · **Artifacts:** `reports/equity_cost_hml.json`, `reports/hml_result.json`, `reports/cost_sensitivity_2026-11-23.json`

---

## TL;DR

A direct measurement of US equity execution cost came back at **0.98 bp round trip**.
The repo charges **5.0 bp** or **25.0 bp** in its backtests — **5× to 25× more**.

That is a serious number, and the obvious worry follows: were strategies killed by
their lack of edge, or by an inflated cost constant?

**Measured answer: not by the cost constant.**

- The cost assumption **does** flip the *sign* of HML's net return — breakeven sits
  at **6.16 bp**, squarely inside the `[0.98, 25]` bp band.
- It does **not** flip the *verdict*. At the cheapest defensible cost HML nets
  **+0.09%/yr** against a **4.32%** hurdle. Cost errors of this size move annual net
  by at most ~0.5 percentage points; they cannot bridge a 4.3-point gap.

So: hurdle-based KILLs are robust to the cost model. **Sign-based** judgements are
not, and those are the ones that need re-examining.

## 1. The measurement

`tools/equity_cost_hml.py`, 191 names, 238,810 daily bars and 356,271 one-minute
bars, 2021-11-22 → 2026-11-20:

| Component | Value |
|---|---|
| Corwin-Schultz spread (1-min) | **0.77 bp** (median, 65/191 names usable) |
| SEC fee | 0.21 bp |
| Commission + ECN (Questrade) | 0.00 bp |
| FX (if avoided) | 0.00 bp |
| **Round trip total** | **0.98 bp** |
| Roll estimator (same bars) | 4.77 bp |
| High-low upper bound | 209.6 bp (loose sanity only) |
| Participation at $20k/name | 0.008% of median ADV ($251M) |

**Do not over-read this.** 0.98 bp is an optimistic *floor*: it assumes patient
execution at the quoted spread, small size, and liquid names. Corwin-Schultz and
Roll disagree by **6×** on the same bars. The defensible framing is a **range**,
not a point.

### Where the constants live

| Constant | Location |
|---|---|
| 5.0 bp | `alpha_engine/cost_model.py`, `tools/residual_mean_reversion.py`, `tools/low_turnover_test.py` |
| 6.0 bp/side | `tools/sim_path_forward.py` |
| 15.0 bp | `tools/h033_equity_sector_momentum_research.py`, `tools/e1_insider_cluster_buy_research.py`, `tools/h034_commodity_term_structure_research.py` |
| 25.0 bp | `pod_equity_breakout_backtest` |

Four different assumptions for the same economics — itself a finding: there is no
single cost model in this repo to correct.

## 2. The method: separate *sign* flips from *verdict* flips

For gross annual edge $g$ and annual turnover $T$ (round trips/year), cost drag at
$c$ bp is

$$\text{drag}(c) = \frac{T \cdot c}{10{,}000}$$

A strategy is cost-sensitive exactly when $g$ falls between $\text{drag}(c_{low})$
and $\text{drag}(c_{high})$. Two questions get conflated in most discussions, so
`tools/cost_sensitivity.py` reports them separately:

- **sign flip** — does $g - \text{drag}(c)$ change sign between the two costs?
- **verdict flip** — does the decision against the hurdle change?

It also computes **breakeven cost** ($g \cdot 10^4 / T$): the cost at which net
return hits zero. That single number tells you whether the cost debate can possibly
decide the case.

## 3. The HML case, worked through

`reports/hml_result.json`: gross **+0.109%/yr**, turnover **14.75%/month**
(1.77 RT/yr), hurdle **4.32%**.

| Arm | Cost | Drag | Net | Verdict |
|---|---|---|---|---|
| Measured (CS spread + SEC) | 0.98 bp | 0.017% | **+0.092%** | KILL |
| Roll estimator (what was used) | 4.97 bp | 0.088% | +0.021% | KILL |
| Repo constant | 25.00 bp | 0.443% | **−0.334%** | KILL |

- **Breakeven cost: 6.16 bp.** So yes — the sign genuinely depends on which cost
  estimate you trust (the measurement is below breakeven, the repo constant is above).
- **Verdict flip: no.** The hurdle is 47× the most favourable net return.

Assessment: **ROBUSTLY-KILLED**. The inflated constant is not what rejected HML.

## 4. What this does and does not license

**Does:**

- Confirm that hurdle-driven KILLs survive the cost correction. Cost modelling errors
  of the size measured here cannot manufacture or destroy a 4-point annual gap.
- Identify the class of judgements that are *not* safe: anything decided by the sign
  of a small net return, or by "net PF slightly above/below 1.0".
- Support consolidating four conflicting constants into one documented model with a
  stated range.

**Does not:**

- License adopting 0.98 bp as *the* cost. At larger size, in illiquid names, or with
  marketable orders, the true cost is materially higher and the Roll estimate (4.77 bp)
  is the safer planning number.
- Reopen HML, or any other hurdle-based KILL, on the basis of cost.
- Say anything about the *other* asset classes — the measurement covers US equities
  only. Crypto, FX, commodity and bond cost structures were not measured here.

## 5. Recommended rule change

Replace "net return > 0 at an assumed cost" as a promotion criterion with:

> **The edge must survive the top of the cost interval.**
> Equivalently: `breakeven_cost_bp > cost_high_bp`.

This is strictly stronger than the current practice and, unlike a single constant, it
cannot be gamed by picking a favourable execution assumption. It is also already
implied by the `survives_2x_cost` criterion used in the registry — the change makes
that criterion the primary test rather than a footnote.

## 6. Reproduce

```bash
python3 tools/equity_cost_hml.py --limit 200        # -> reports/equity_cost_hml.json
python3 tools/hml_pit_backtest.py --limit 200       # -> reports/hml_result.json
python3 tools/cost_sensitivity.py --hml             # -> RESULT: ROBUSTLY-KILLED
# or for any strategy:
python3 tools/cost_sensitivity.py --gross-ann 0.00109 --turnover-per-year 1.77 \
    --hurdle-ann 0.0432 --cost-low-bp 0.9756 --cost-high-bp 25
```

---

Descriptive measurement and arithmetic. No picks, no signals, zero capital, and
nothing here is investment advice.
