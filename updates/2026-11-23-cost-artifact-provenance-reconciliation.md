# Cost artifact provenance reconciliation — 2026-11-23

**Artifact:** `reports/cost_measurement_new_classes/class_cost_new_20261123.json`
**Read from:** branch `cost/new-classes-2026-11-23` @ `7379044` (commit `7379044708046852583ea24b0131f380152718d6`), via `git show 7379044:<path>` into `/tmp` — never from the shared working tree.
**Code:** `tools/equity_cost_measure.py` @ `origin/main`, blob `b3ef58b76b53a566582b7e6c2d2c810d0bd085a0` (966 lines). Line numbers below are that blob's.
**Method:** did not regenerate the artifact; did not edit any number. Both fields were re-derived arithmetically from the per-name records stored inside the artifact itself.

---

## 1. The disagreement, stated exactly

Headline = `classes.<C>.aggregate.range_ub_rt_bp.median`.
Field = `classes.<C>.aggregate.corwin_schultz_rt_bp_median`.

| Class | Headline RT (median 1-min bar range) | `corwin_schultz_rt_bp_median` | n names | ratio headline/field |
|---|---|---|---|---|
| BOND | 1.2124854142213006 bp | 0.07237047103355476 bp | 10 | 16.75× |
| COMMODITY_FUTURES | 6.318231955551324 bp | 0.0 bp | 7 | ∞ |
| PENNY_STOCK | 21.297365081989422 bp | 8.793277275523144 bp | 7 | 2.42× |

The ratio is not constant (16.75, ∞, 2.42), so no single factor (2×, ½×) relates the two. They are not the same quantity in different units.

---

## 2. Formula for EACH number, from the code

Both are written in the same dict, in [`measure_class()`](tools/equity_cost_measure.py:564):

```python
# tools/equity_cost_measure.py:596-611
    if ubs:
        vals = sorted(v for _, v in ubs)
        n = len(vals)
        rec["aggregate"] = {
            "n_names_with_data": n,
            "range_ub_rt_bp": {"min": vals[0], "p25": vals[n // 4],
                                "median": statistics.median(vals),
                                "p75": vals[3 * n // 4],
                                "p90": vals[int(0.9 * (n - 1))], "max": vals[-1]},
            "per_name_rt_bp": dict(ubs),
            "corwin_schultz_rt_bp_median": statistics.median(css) if css else None,
```

with the inputs gathered at [`tools/equity_cost_measure.py:584-592`](tools/equity_cost_measure.py:584):

```python
# tools/equity_cost_measure.py:584-592
    ubs, css = [], []
    for sym in universe:
        r = measure_spread(sym)
        rec["per_name"][sym] = r
        if r.get("range_upper_bound_rt_bp"):
            ubs.append((sym, r["range_upper_bound_rt_bp"]["median"]))
            cs = r.get("corwin_schultz", {}).get("median_bp")
            if cs is not None:
                css.append(cs)
```

### 2a. Headline

`HEADLINE(C) = statistics.median( { median_bar_range(sym) : sym in C } )`

The per-name inner value is built at [`tools/equity_cost_measure.py:224-241`](tools/equity_cost_measure.py:224):

```python
# tools/equity_cost_measure.py:224
    ranges = sorted((h - l) / c * 1e4 for h, l, c in zip(highs, lows, closes) if c > 0)
...
# tools/equity_cost_measure.py:240
            "median": ranges[n // 2], "p25": ranges[n // 4],
```

So each name contributes the **1-min bar range `(high − low)/close × 1e4`**, which is the round-trip quoted-spread **upper bound** (both bid and ask lie inside `[low, high]`), aggregated per name as `ranges[n // 2]` (the **upper** middle element of the sorted range list, not `statistics.median`), then taken across names with `statistics.median`.

### 2b. CS field

`FIELD(C) = statistics.median( { median_pair_CS_bp(sym) : sym in C } )`

The per-name inner value comes from [`corwin_schultz()`](tools/equity_cost_measure.py:147):

```python
# tools/equity_cost_measure.py:147-174 (abridged, verbatim on the key lines)
def corwin_schultz(highs, lows) -> dict:
    """Corwin & Schultz (2012) on consecutive bar pairs. Floors negatives at 0."""
    ...
    beta = statistics.mean(beta_terms)
    gamma = statistics.mean(gamma_terms)
    k = 3 - 2 * math.sqrt(2)
    alpha = (math.sqrt(2 * beta) - math.sqrt(beta)) / k - math.sqrt(gamma / k)
    s = 2 * (math.exp(alpha) - 1) / (1 + math.exp(alpha))
    vals = []
    for b, g in zip(beta_terms, gamma_terms):
        a = (math.sqrt(2 * b) - math.sqrt(b)) / k - math.sqrt(g / k)
        v = 2 * (math.exp(a) - 1) / (1 + math.exp(a))
        vals.append(v * 1e4)
    vals.sort()
    return {"n_pairs": len(vals), "pooled_bp": max(0.0, s * 1e4),
            "median_bp": statistics.median(vals),
            "p25_bp": vals[len(vals) // 4], "p75_bp": vals[3 * len(vals) // 4],
            "frac_floored": sum(1 for v in vals if v <= 0) / len(vals)}
```

The docstring says "Floors negatives at 0", but the floor is applied only to `pooled_bp` at line 171 (`max(0.0, s * 1e4)`) — **not** to `median_bp`. That is why `median_bp` is negative for some names, e.g. TLH −0.318.

### 2c. What the two measure

- **Headline** = median across names of each name's median bar range. A **market-observation upper bound on the round-trip quoted spread**, unit bp, of the price.
- **Field** = median across names of each name's median per-pair Corwin-Schultz estimate. A **noise-dominated point estimator** of the round-trip spread. Its per-pair distribution straddles zero (p25 negative for every name), because CS is `α = f(beta, gamma)` and the estimator is only reliable when `gamma` materially exceeds `beta`; in 1-min bars of liquid instruments the two are nearly equal, so `α` is a small difference of large, noisy terms, and roughly half the pairs land ≤ 0.

**They measure the same target (RT spread) with different estimators.** They are not a RT/per-side pair: the headline is explicitly RT (line 17-19 docstring; line 608 basis string), and CS is a RT estimator by construction (`s` is a spread of price levels, not half of one). The 2× hypothesis is rejected outright by the numbers: for BOND `2 × 0.0724 = 0.1448 ≠ 1.2125`, and for PENNY `2 × 8.7933 = 17.587 ≠ 21.297`.

---

## 3. The `0.0` for COMMODITY_FUTURES, mechanically

`FIELD(COMMODITY) = median` of the 7 per-name CS medians, sorted:

`[-0.11395 (HG=F), -0.00161 (SI=F), 0.0 (NG=F), 0.0 (ZC=F), 0.0 (ZS=F), 0.08058 (CL=F), 0.58556 (GC=F)]`

With n = 7, `statistics.median` returns the **4th** element = `0.0`. The exact `0.0` comes from three names whose per-pair CS median is exactly zero, not from a filter or a clamp:

1. **No filter removed anything.** All 7 names have data; `n_names_with_data = 7` and `aggregate_excl_truncated.n_names_clean = 7` with `excluded_truncated = []`. The truncation suspect flag (`frac_zero_range > 0.5`, line 246) is `False` for all 7 (max is ZS=F at 0.30).
2. **The zeros are exact zeros from the CS algebra.** For a bar pair where the second bar is *nested inside* the first (which includes any flat second bar, `h2 == l2`), `H = h1` and `L = l1`, so `gamma = log(h1/l1)²`, and `beta = log(h1/l1)² + log(h2/l2)²` with the second term exactly 0.0. The two values are then the **same floating-point number** (same inputs summed in the same order), so `alpha = (√2b − √b)/k − √(g/k) = 0` exactly when `g == b`, and `v = 2(e⁰−1)/(1+e⁰) = 0` exactly. Verified numerically: `bar1=[100,101], flat bar2 ∈ {100, 100.5, 101}` gives `b == g == 9.9009084087508847e-05` and `v_bp = 0.000000`.
3. **`frac_floored` for the three zero names** is ZC=F 0.679, ZS=F 0.705, NG=F 0.557 — i.e. **the majority of their bar pairs produce CS ≤ 0**. Their median is thus the boundary value 0.0 (an even/symmetric split around zero), not a positive spread.

So the `0.0` means: **for these futures, the CS estimator is not resolving a spread** (ratio of `gamma` to `beta` ≈ 1 across most pairs, plus coarse tick grids on ZC/ZS with 30–41% zero-range bars). It is not a market observation of zero spread. The headline's per-name range medians (2.057 … 9.604 bp) are the only numbers there that reflect the market. Whether the true futures spread is nearer 2 bp or 9 bp, CS says nothing usable.

---

## 4. BOND arithmetic check against stored per-name data

The per-name values **are** stored (`classes.BOND.aggregate.per_name_rt_bp`), so the headline is fully reproducible:

Sorted per-name range medians (10 values):
`0.5442160617406485 (JNK), 0.614441572047355 (SHY), 0.9482495176476757 (TIP), 1.0506708894546648 (AGG), 1.120316017117481 (IEF), 1.3046548113251202 (HYG), 1.4009980114031308 (BND), 1.4540632859226852 (LQD), 1.5904847129514699 (TLH), 2.5126261380006722 (TLT)`

n = 10 (even) ⇒ `statistics.median` = mean of the 5th and 6th = (1.120316017117481 + 1.3046548113251202) / 2 = **1.2124854142213006 bp**. ✓ Equal to the stored headline to all digits.

The CS field is likewise reproducible: sorted CS medians `[-0.318031, 0.0, 0.0, 0.0, 0.0, 0.144741, 0.180030, 0.205724, 0.275916, 0.372285]`, n = 10 ⇒ mean of 5th and 6th = (0.0 + 0.14474094206710952)/2 = **0.07237047103355476 bp**. ✓

COMMODITY headline reproduces (median of 7 = 6.318231955551324) and PENNY headline reproduces (median of 7 = 21.297365081989422). Nothing in the artifact fails to reproduce.

---

## 5. Verdict per class

The question is which number is the cost a trader pays. The headline is a rigorous **upper bound** on the RT quoted spread from observed bar ranges; CS is an unsignable point estimator that here produces zero or negative medians for most names. Neither is an NBBO. But only one is a defensible headline cost.

| Class | Verdict | Why |
|---|---|---|
| BOND | **HEADLINE CORRECT** (as an upper bound) | 1.2125 bp is the median bar range, reproducible, strictly positive, and bounded below by every name's own range. CS median 0.0724 bp is unusable: 4/10 names floor at 0.0, one is negative, `frac_floored` 0.29–0.69. The true NBBO is ≤ 1.2125 bp, not ≈ 0.07 bp. |
| COMMODITY_FUTURES | **HEADLINE CORRECT** (as an upper bound); field is meaningless here | 6.3182 bp is the median bar range across 7 contracts. CS median 0.0 is not a cost observation (see §3) — it is the estimator collapsing. Do not quote 0.0 as the futures cost. |
| PENNY_STOCK | **HEADLINE CORRECT** (as an upper bound); field is a low-biased point estimate, not the headline | 21.2974 bp vs CS 8.7933 bp. CS is floored/negative for 2/7 names (SIRI −1.30, GPRO 0.0) and its per-pair p25 is negative for all 7; for penny names the survivor-selected sample biases both numbers **downward**, so the gap is not evidence the cost is lower. The range bound is the honest one. |

No class gets `FIELD IS THE CORRECT COST`. No class gets `HEADLINE UNSUPPORTED`: every headline reproduces exactly from stored data.

The one caveat that is not a hedge but a precise distinction: the headline is an **upper bound**, so "the cost a trader pays" is `≤ headline`, and the CS field is `not a reliable estimate of it` — not `0.0724` or `0.0`. The upper bound is the correct number to *report*; the true spread is below it and is not measurable from 1-min bars without an NBBO.

---

## 6. Does any published verdict word have to change?

**No.** Documents 15/22/23/24/26 carry these verdict words:

- **BOND (doc 22 §2.4, doc 26 §2.4):** `DEAD-NOT-REOPENED`, break-even **0 bp/side**.
- **COMMODITY (doc 22 §2.5, doc 26 §2.5):** `DEAD-NOT-REOPENED` (momentum); carry `BLOCKED_MISSING_DATA`.
- **PENNY_STOCK (doc 26 §2.9):** `KILLED` on **instrument availability** (`NO_INSTRUMENT_IN_REPO`), a cost-independent ground.

The arithmetic in the docs is `net = gross − 2·cost`, `c* = gross/2`, and for bond and commodity momentum `gross ≤ 0` at zero cost, so `c* ≤ 0`. Then `cost > 0 ≥ c*` ⇒ `net < 0` at any positive cost. **This does not depend on the size of the cost, only its sign**:

- If the headline is right (it is) → cost > 0 → verdicts hold.
- Even if the headline were wrong and the field were right → BOND 0.0724 > 0, COMMODITY 0.0. For COMMODITY, a field of exactly 0.0 is the one case where `cost > 0` is not strictly established; but the per-name range bound (min 2.06 bp) proves the cost is not zero, and at cost = 0 the verdict is `gross ≤ 0` ⇒ still not investable. So the verdict is unchanged in every branch.
- PENNY's `KILLED` rests on no instrument, so cost is irrelevant to it.

The correction would matter only if a number were being used to *reopen* a class, and none is. The blunt statement: the headline column was correct as reported (upper-bound cost), the CS field must never be quoted as the cost, and no verdict word needs to change.

---

## 7. Provenance failures worth recording

1. `corwin_schultz_rt_bp_median` sits beside a round-trip upper bound in the same `aggregate` dict with no unit/estimator label, inviting exactly the misreading that prompted this task. It is a **different estimator of the same target**, not a second measurement to reconcile.
2. The CS docstring says "Floors negatives at 0" but `median_bp` is not floored (only `pooled_bp` is). The stored negative medians are correct behaviour, but the docstring misdescribes it.
3. Per-name `range_upper_bound_rt_bp.median` is `ranges[n // 2]`, an order statistic, not `statistics.median`; for even n it is the upper of the two middle values (a small upward bias). The class-level headline does use `statistics.median`. The two levels use different median definitions.
