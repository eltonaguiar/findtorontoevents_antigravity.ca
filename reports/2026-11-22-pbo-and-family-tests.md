# Item 26 (PBO block length) and item 27 (family-wide data snooping) — 2026-11-22

**Programme:** `plans/2026-11-22-50-action-items.md` · **Owner:** buffy
**Artifacts:** `reports/pbo_reality_check_2026-11-22.json`, `reports/per_class_edge_series_2026-11-22.csv`,
`reports/per_class_edge_excess_2026-11-22.csv`, `reports/h232_invvol_2026-11-22.json`

Both items were blocked on the same missing object: the frozen
`reports/per_class_edge_2026-11-22.json` stored per-cell *summaries* (`pbo_cscv`,
`boot_ci_lb_bps`, …) and neither a CSCV block-length sweep nor a family-wide p-value can be
computed from summaries. The harness now persists the T×N daily matrices, so both are
answered here.

---

## 0. What the harness change produced, and its first validation

`python3 tools/per_class_edge_harness.py --n-trials 29` (fresh fetch, `RC=0`):

- `reports/per_class_edge_series_2026-11-22.csv` — **5157 × 39** net daily returns, one column per cell.
- `reports/per_class_edge_excess_2026-11-22.csv` — the same shape, excess vs each cell's **own** class benchmark.
- 40 cells produced; **39** have a shared time axis. **H-222 (PEAD)** is an event cell with no
  shared calendar, so it is absent from the matrix by construction. The family is 39 cells, not 40 —
  stated rather than papered over.

**The frozen scalar reproduced exactly.** Re-running the untouched PBO at `s_blocks=16`
returns **0.345** against the stored **0.345**, |diff| 0.0. The number was never stale; it is
simply computed on a biased matrix (see §1).

---

## 1. Item 26 — is PBO = 0.345 an artefact of `s = 16`?

| s_blocks | block length (days) | PBO, harness convention (NaN→0) | PBO, common window |
|---|---|---|---|
| 8 | 644.6 | 0.350 | **0.570** |
| 16 | 322.3 | 0.345 | **0.535** |
| 24 | 214.9 | 0.315 | **0.505** |

Two conclusions, and the second is the uncomfortable one.

**(a) PBO is not an artefact of the block length.** Within each convention the number moves by at
most 0.065 across a 3× change in block size. `s=16` was not cherry-picked.

**(b) PBO *is* an artefact of how the matrix was built.** The harness fills ragged NaN with
`0.0`, so a cell that starts in 2017 is credited with 0% returns for 2012–2016. Because those
cells have positive means, adding zeros *depresses* their full-sample Sharpe — the winner of the
in-sample half is chosen from a field whose later entrants are systematically handicapped. The
same matrix restricted to the **common window** (1478 days, 2021-01-04 → 2026-11-20, where no cell
is scored on a day it did not trade) gives **0.505–0.570**.

The direction matters: the honest number is **worse** than the published one. PBO of 0.54 means
the in-sample Sharpe winner lands below the out-of-sample median **more often than not** — the
selection carries no information. The frozen 0.345 was optimistic, and it was optimistic for a
mechanical reason, not by choice.

**Verdict: 0.345 is block-length robust and convention-fragile; the admissible value is ≈0.53.**
Recorded as a defect of the harness's PBO construction, not of the CSCV method.

---

## 2. Item 27 — does the best cell survive a family-wide search?

The registered test is White's Reality Check. It is reported first, and the variants are reported
because they disagree — which is itself the finding.

### All-cells common window (39 cells, 1478 days, 2021-01-04 → 2026-11-20)

| test | best cell | observed | p | uncorrected p |
|---|---|---|---|---|
| **Reality Check (raw) — the registered test** | H-200:NVDA | 10.258 bp/day | **0.4794** | 0.0529 |
| Reality Check (studentised) | H-201 | 5.471 bp/day | 0.5322 | 0.0357 |
| Hansen SPA | H-201 | 5.471 bp/day | 0.5018 | 0.0357 |
| RC, spread-zero diagnostic only | H-200:NVDA | 7.462 bp/day | 0.2232 | 0.0017 |

### Full-history family (34 cells present from 2012-01-03, 3735 days)

| test | best cell | observed | p | uncorrected p |
|---|---|---|---|---|
| **Reality Check (raw) — the registered test** | H-200:NVDA | 9.444 bp/day | **0.1436** | 0.0028 |
| Reality Check (studentised) | H-201 | 5.512 bp/day | **0.0156** | 0.0008 |
| Hansen SPA | H-201 | 5.512 bp/day | **0.0152** | 0.0008 |

**The registered statistic does not reject at any conventional level on either window.** The
best cell's excess is 5–10 bp/day against an uncorrected p as low as 0.0008, and once the search
over 34 cells is charged for, the raw Reality Check puts it at p = 0.144.

**Two Hansen-style variants do reject, at ~1.5%.** The disagreement is not noise and not a bug —
it is the known behaviour of these tests:

- Reality Check recentres **every** cell on its own mean. A family containing ~20 cells with
  genuinely negative excess therefore drags a wide bootstrap null over the winner. Hansen (2005)
  wrote SPA specifically because RC is *severely conservative* when the model set contains junk,
  which ours does.
- SPA recentres only cells that are not *clearly* bad (t above `−√(2 log log T)`, here **−2.053**),
  which removes the dead cells from the null without removing them from the search count.

**So the two tests answer "should including hopeless models widen the null?" differently, and our
family is mostly hopeless models.** That is the whole of the 0.14 vs 0.015 gap.

### The tension with the DSR, stated plainly

H-201's single-cell DSR at 29 declared trials is **0.9483** — it fails the 0.95 bar — and that is
what produced the `NOT_PROVEN` label. But the DSR deflates using the *observed scatter of
Sharpe ratios* under an **independence** assumption across trials. These 39 cells are near
duplicates of each other (twelve of them are the same 12-1 TSMOM rule on different tickers). SPA,
by resampling the actual matrix, preserves the cross-cell correlation and effectively measures a
much smaller number of independent trials — so it is the *less* punitive correction, and the DSR
is the conservative one.

**Direction of the correction is therefore not settled in one direction any more.** An earlier
version of this programme's reasoning treated the multiplicity penalty as definitely fatal; the
family-wide bootstrap says the penalty is smaller than the independence-assuming deflation
implies. Both are in the range, and neither is strong enough to *promote* the cell.

### Why none of this promotes H-201

The full-history winner is a cell drawn from a universe of **today's ten largest companies**.
Item 16 measured **0 of 79 series ending early** — a current-constituent universe that already
knows which names survived. The Reality Check bootstraps **time**, not the universe, so it cannot
correct survivorship, and the cell it most flatters (H-201's momentum on 2012–2026 mega-caps) is
the most contaminated cell in the matrix. A p-value from a survivorship-contaminated panel is not
admissible evidence of a tradable edge, however small it is.

**Verdict on item 27: reported as a range, not a decision.** Registered RC p ∈ [0.144, 0.479] →
no rejection; studentised/SPA p ≈ 0.015 on the full-history family → rejection, driven by H-201.
The honest summary is *"the multiplicity penalty is somewhere between small and fatal, and the
cell that would benefit most from the favourable end of that range is the one most contaminated by
survivorship."* H-201 stays **`NOT_PROVEN`**: not because item 27 kills it, but because item 16
means nothing here can promote it.

---

## 3. Item 15 — inverse-vol sizing inside the H-201 basket (H-232)

Pre-registered as **H-232** in `reports/hypothesis_registry.json` and committed
(`b9ff7faab3e`) **before** the first execution, with a stated prior of "expecting a negative
result". Window 2012-01-03 → 2026-11-20, 3744 days, 10 names, exposure fixed at 1.0, 10 bp/side —
identical to H-201 except the weight split.

| leg | mean daily (bp) | CI-LB (bp) | excess vs SPY (bp) |
|---|---|---|---|
| H-232 inverse-vol | 9.695 | 5.675 | 3.958 |
| H-201 equal weight, same days | 11.521 | **7.246** | 5.784 |

**Paired difference (invvol − equal), same days: −1.826 bp/day, 95% CI [−2.754, −0.922],
t = −4.23 → CI excludes zero.**

Inverse-vol weighting inside the basket is **significantly worse**, not better. The mechanism is
visible: the low-vol mega-cap is also the one with the weaker momentum, so shifting weight to it
trades away return for variance reduction that the gate does not reward.

Cross-check worth stating: the equal-weight leg's CI-LB reproduces the frozen **7.246 bp** exactly
on the same construction, which is the same number §2's DSR memo is built on. The two runs agree.

| gate | value |
|---|---|
| boot CI-LB | 5.675 bp |
| boot CI-LB at 2× cost | 5.365 bp |
| split halves | [8.306, 11.083] bp |
| DSR (n_trials = 30, raised for this cell) | **0.8491** |
| DSR (n_trials = 29, comparison only) | 0.8685 |
| excess vs SPY | 3.958 bp |
| vol-matched excess CI-LB | −1.329 bp |

**Verdict: FAILS.** The trial count was **raised** from 29 to 30 to charge this cell for its own
search, never lowered. And the control separates the two effects: random top-3 with the *same*
inverse-vol sizing averages 8.011 bp/day (5–95%: 6.177 → 9.960), and the observed cell sits at the
**92.4th percentile** of that null — so momentum *selection* carries information, while the
*sizing* change destroys 1.83 bp/day of it. Item 15 is now closed: both the vol-matching answer
(no) and the position-level answer (worse) are measured.

---

## 4. Method notes and limits

1. **Bootstrap block length** for RC/SPA is `T^(1/3)` (≈15.5 days at T=3735), 5000 draws, seed 11,
   fixed sd in the studentised statistic (the standard convention).
2. **Breaks in the family:** the 39-cell count excludes H-222 by necessity, and includes the two
   `integrity_flag` commodity-futures cells (H-210/H-211) whose underlying series is contaminated.
   Keeping them **widens** the null; dropping them would have been the flattering choice.
3. **The full-history family is a subset chosen by data availability**, not by performance
   (present from 2012-01-03). It is not a second look at a different result.
4. **What item 27 does not cover:** the 200-round programme's wider search history. RC/SPA correct
   for these 34–39 cells and nothing else.
5. **What no bootstrap here can fix:** the point-in-time universe. Every number in this report
   rests on a survivorship-contaminated panel.
