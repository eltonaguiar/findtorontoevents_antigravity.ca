# Trial budget — what a trial costs, and what earns one

**Date:** 2026-11-23 · **Backlog:** C1–C7 in `docs/BACKLOG_100_2026-11-23.md`
**Sources:** `reports/trial_debt_audit_2026-11-23.json`, `reports/TRIAL_N_RECONCILIATION_2026-11-23.md`, `notes/buffy-dsr-multiplicity-one-trial-margin-2026-11-22`, `deflation_programme.json` (vanilla-handsaw worktree)
Paper only. Zero capital. Not investment advice.

---

## 1. The count (C1, C2)

`tools/trial_debt_audit.py` over `reports/hypothesis_registry.json`, all 19 hypothesis-bearing lists:

| measure | value |
|---|---:|
| total rows | 166 |
| **distinct ids** | **154** |
| duplicate ids (cross-list re-files) | 12 |
| ran / has a result | 94 |
| running forward (trial already spent) | 28 |
| registered, never ran | 27 |
| registered, permanent data gap | 2 |
| status outside the derived vocabulary | 3 |

**Defensible N = 122** (ran + running forward), because a forward-registered test has already consumed degrees of freedom. N=94 if you count only closed results.

**The 12 duplicate ids** (inflate any naive `len()`): `H-005, H-015, H-016, H-017, H-018, H-019, H-020, H-028v2, H-028v3, H-034, H-144, H-145` — each appears in `hypotheses` **and** in a satellite archive list. They are re-files, not second trials.

**And the count is not settleable from one path.** Seven checkouts hold six different `hypotheses` counts: main tree **120**, vanilla-handsaw 109, moneyresearch/vh-hotfix/vh-mainport 108, review-main 106, vanilla-handsaw-audit3 99.

---

## 2. What one trial costs (C3) — measured two independent ways

Two grids exist in the estate, built by different agents from different data. They agree.

**Grid A — deflated Sharpe**, `notes/buffy-dsr-multiplicity-one-trial-margin-2026-11-22`:

| N | DSR | Δ per trial |
|---:|---:|---:|
| 20 | 0.9678 | — |
| 26 | 0.9547 | −0.00218 |
| 29 | 0.9483 | **−0.00213** |
| 40 | 0.9261 | −0.00202 |
| 100 | 0.8344 | −0.00153 |
| 500 | 0.5967 | −0.00059 |

**Grid B — SR\*** (the annualised hurdle), `deflation_programme.json`, σ_sr = 0.6488:

| N | SR\* | Δ per trial |
|---:|---:|---:|
| 25 | 1.30 | — |
| 90 | 1.6176 | +0.00489 |
| 108 | 1.6592 | +0.00231 |
| 146 | 1.7264 | **+0.00177** |
| 362 | 1.9165 | +0.00088 |
| 658 | 2.0333 | +0.00039 |

**Near the decision region both grids price a trial at ≈ 0.002** — 0.0021 DSR, 0.0018–0.0023 SR\*. Two independent methods landing on the same number is the strongest evidence here that the quantity is real and not a modelling artefact.

### The number that matters most

At N=26 the best near-miss cell sits at DSR 0.9547, which is **+0.0047 above the 0.95 threshold**. At 0.0021 per trial, that headroom is **2.2 trials**.

> The programme's closest miss had **two trials of headroom**. Spending three more tests destroys it.

### The price is front-loaded, not linear

−0.0021/trial at N≈26 but −0.0006/trial at N=100–500. **The damage is done early.** Going 26 → 29 was catastrophic; going 500 → 501 is nearly free. This is why "we already have 154 trials, one more can't hurt" is true and irrelevant — the harm was already taken, and the only way back is a *forward* measurement, which costs one trial rather than five.

---

## 3. What earns a trial (C5)

A new trial is admissible only if it meets **at least one**:

1. **A data axis no prior trial has touched.** Not a new parameter on an old axis — a genuinely different information source. Candidates named but not yet run: options-implied skew term structure, 10-K "major customer" supply-chain graph edges, short-interest/borrow-fee crowding, prediction-market calibration against a matched underlying.
2. **A forward-only measurement.** Pre-registered by construction, so it costs **one** trial instead of the ~5 a grid search implicitly spends.

It is **not** admissible as: another configuration of an existing family; a re-run at a different cost assumption; a re-labelling of a prior test; or anything whose kill rule is written after the result is seen.

**Every trial must arrive with the kill rule frozen and the trial count declared before the run.** A test without those is not an edge test, it is another data point on the pile.

---

## 4. Forward-only inventory (C6) — the debt-free path

| instrument | state | notes |
|---|---|---|
| `tools/etf_trend_forward_clock.py` | frozen 2026-11-23, `n_records: 0` | 20 ETFs, top-5 by 252-day momentum, monthly; refuses pre-freeze dates |
| crypto intraday paper sim (`verified_strategies/paper_pilot/crypto_intraday_sim.py`) | running, closes its own rows on every :07/:37 tick | paper-only, prop-firm guardrails |
| H-201 pod recorder | 15 days / 3 trades, `NO_VERDICT_TOO_FEW_DAYS_FOR_INFERENCE` | needs ~77 more days; universe pinned so it cannot drift |

These three are the only genuinely debt-free measurements in the estate, and the ETF clock is the only one that has never been fitted to anything.

---

## 5. Programme SR\* with the corrected N (C7)

Using σ_sr = 0.6488 (Grid B) and the defensible N=122 → SR\* ≈ **1.68** (interpolating between N=108's 1.6592 and N=146's 1.7264).

**Every candidate N leaves 0 of 6 classes surviving.** The best observed Sharpe is ETF at 1.05; the lowest hurdle any candidate produces is SR\* = 1.30 at N=25. The gap is not close under *any* of the six counts in circulation. That robustness is the useful result — the verdict does not depend on winning the N argument.

**Unresolved and flagged:** my earlier pass reported SR\* = 1.259 from a pooled σ_SR = 0.031848; Grid B reports 1.6176 at N=90 from σ_sr = 0.6488. Different scales, not comparable at equal N. Until one reproduces the other, neither SR\* figure should be quoted as *the* hurdle — only the ordering (nothing survives) is safe.

---

## 6. The rule this document exists to enforce

**Stop producing trials. Start producing measurements.**

The binding constraint is not ideas, not data, and not compute. It is that each trial costs ~0.002 of the only statistic that decides anything, and the best near-miss had 0.0047 of headroom. A fleet that responds to "0 proven edges" by running more tests does not get more chances — it gets a worse threshold and the same zero.

Zero capital sanctioned. Paper only. Not investment advice.
