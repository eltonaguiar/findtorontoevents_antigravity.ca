# 2026-11-23 — alpha denominator resolved, AUDJPY claim corrected, DSR-658 wiring pinned

Three corrections, one of them to my own earlier work, plus the R01 fill attempt.
Paper only, zero capital, not investment advice.

## 1. The `0/362` denominator — RESOLVED, and my earlier verdict was wrong

**What I said on 2026-11-23 (earlier):** `cells_total` does not reproduce; the denominator is
`UNRESOLVED`; the estate should cite "0 cells pass; denominator unresolved".

**What is actually true:** `362` reproduces exactly, from a file that has been in the repo the
whole time:

```
audit_dashboard/data/audit3_ledger.json
  generated_at          2026-11-20T01:57:23.798364+00:00
  len(cells)            362
  summary.n_cells_total 362
  summary.n_cells_tested 67
  verdicts              WEAK 59 · KILL 8 · INSUFFICIENT_N 295 · PROVEN 0 · CANDIDATE 0
```

**And it drifts — which is the more useful lesson.** The ledger copy shipped on this branch holds
**367** cells (tested 66, WEAK 57 / KILL 9 / INSUFFICIENT_N 301), the main working tree's copy holds
**362**, `review-main`/`vh-mainport` hold **359**, and the 2026-11-22 raw copies hold **374**. So `362`
was one run, not "the" population, and quoting it without its `generated_at` repeats the same fault in
the opposite direction. What is invariant across every copy examined is the answer to the actual
question: **PROVEN + CANDIDATE = 0**. The zero is the finding; the denominator is a run stamp.

**What was broken:** `tools/programme_alpha_sweep_recompute.py` measured cells against
`audit_dashboard/data/audit3_verdict_history.json` — a **verdict-history sidecar that accumulates
cells across runs** (452 entries over 2 distinct `last_seen` dates). Comparing a run-scoped
denominator to a cumulative set will never match, and I reported the mismatch as "the author's
denominator cannot be rebuilt". The author's denominator was rebuildable; my reference was wrong.

**What changed:** `reports/programme_alpha_sweep.json` `denominator_status` now reads `RESOLVED`
with the ledger as its source, the verdict breakdown, and an explicit `correction` field naming the
sidecar mistake. `0/362` is now a legitimate citation.

**The sharper statement still matters:** only **67 of 362** cells clear the n-floor, so
"0 of 67 tested cells" is a stronger sentence than "0 of 362" — and `362` should be quoted with its
run timestamp, because other copies of the same ledger hold 359 and 374 cells.

**Verified:** read `len(cells)` and `summary.n_cells_total` from the ledger in the main tree;
both 362; verdict histogram sums to 362 (59+8+295).

**One contradiction inside the ledger itself, found while fixing this.** Two cells carry
`alpha_gate.passed == true` while holding verdicts WEAK/KILL, so the ledger's own rule count says
**2** where its verdict count says **0**. I am reporting the zero (verdicts) as the answer and the
field count as the anomaly, because PROVEN/CANDIDATE is what the estate's gate means by "passes" —
but until someone with the generator in hand says whether those two cells are a scoring artefact or
a genuine pair that cleared the gate without being promoted, "0 pass" is a verdict-based claim, not
a rule-based one. `tools/programme_alpha_sweep_recompute.py` now prints both, side by side, rather
than letting one silently overwrite the other.

## 2. `AUDJPY` is not a "deterministic-loser pattern"

`ROOT_CAUSE_ANALYSIS_NON_CRYPTO.md` Root Cause #4 asserted
`AUDJPY=X: 0W/18L = 0.0% WR, -208.60% PnL (deterministic-loser pattern)`.

The pick-id reconciliation (`reports/audjpy_population_reconcile_2026-11-23.json`) found **three
disjoint populations**, sharing **zero** pick ids and zero embedded timestamps:

| population | n | mean | record |
|---|---:|---:|---|
| audit3 cells (no trade ids) | 34 | — | verdict only |
| riseoftheclaw closed picks | 24 | −2.447 % | 2W / 21L |
| dashboard closed picks | 32 | **+0.494 %** | 19W / 12L |

The `0W/18L` figure is a fourth, older slice from `kimi_signal_tracking` specifically, not "AUDJPY".
A pattern that is −2.4 % on one population and +0.5 % on another, with no shared rows, is
**not identified** — the label claimed more than 18 trades inside one retired system can support.

**What changed:** the line now carries the three-population correction inline instead of the
deterministic-loser label.

## 3. Which DSR implementation does the 658 floor depend on?

`docs/GRADUATION_RUNBOOK.md` gates on "DSR ≥ 0.95 with declared `n_trials` (global floor 658)".
Four live implementations exist with mutually incompatible signatures:

| implementation | signature | can take σ_sr? |
|---|---|---|
| `alpha_engine.deflated_sharpe` | `(estimated_sharpe, sr_variance, nb_trials, horizon, skew, kurt)` | **yes** |
| `alpha_engine.statistical_rigor` | `(returns, n_trials, skewness, kurtosis)` | no — derives its own null |
| `crypto_ml_edge.validation` | `(observed_sharpe, n_trials, n_obs, skew, kurtosis)` | no |
| `alpha_engine.validation.sharpe_metrics` | `(returns Series, risk_free_rate, freq)` | no — fixes `n_trials` internally |

**Answer: the 658 floor can only be wired through `alpha_engine.deflated_sharpe`**, because
`docs/TRIAL_BUDGET_2026-11-23.md` pins the floor with `σ_sr = 0.6488`, and that is the only
signature that accepts a trial-dispersion parameter. The other three cannot express the floor at
all. Hurdle at DSR 0.95, N=658 (`reports/dsr_wiring_matrix_2026-11-23.json`):

| implementation | SR (per trade) | annualised ×√252 | Δ per trial |
|---|---:|---:|---:|
| `deflated_sharpe` (σ_sr 0.6488) | 3.849 | 61.1 | 0.001428 |
| `crypto_ml_edge` | 3.394 | 53.9 | 0.001815 |
| `statistical_rigor` | 0.438 | 7.0 | 0.000163 |

The spread between these three is a factor of **9** in required Sharpe, for the same stated gate.

**The peer's four-value table reproduces under no shipped wiring** — and it is internally
inconsistent: solving each published value for the `n_trials` that would produce it gives
**A 442, B 16, C 2, D 254**. One table cannot have four different trial counts under one wiring, so
the published numbers did not come from any implementation in this repo. They are not wrong because
they disagree with me; they are unverifiable because their row set and trial count are both absent.

**Verified:** `python3 tools/dsr_wiring_matrix.py` (exit 3 — it deliberately reports non-reproduction),
grid over N ∈ {26, 67, 359, 361, 362, 452, 658} × two variance conventions, plus a bisection for the
per-implementation hurdle. Deterministic, row sets stated as wins/losses, no sampling.

## 4. R01 round-open fill — the round has not opened yet

`tools/r01_round_open_fill.py` fetches bars for the 19 R01 instruments and **refuses to fill until
at least one bar exists at or after the round start**. Run at 09:42Z against a 14:30Z open
(09:30 ET):

```
NOT_OPEN_YET: 0/19 tradable instruments have a bar at or after 2026-11-23T14:30:00Z.
Nothing is filled. This is a refusal, not a result.   [exit 3]
```

Fetch path proven live: crypto 808 five-minute bars to 09:45Z, FX 211 bars to 09:45Z — all
pre-open; equities/ETFs serve daily bars only in this feed, last 2026-11-20T20:55Z (Friday). Five
mutual funds (`FZROX`, `VBIRX`, `VFIAX`, `VTSAX`, `VWINX`, `FUSEX`) have no intraday series and are
VOID by rule, not missing.

Deliberate design points, each a bug if reversed:
- daily bars are stamped at the **session open** (14:30Z under EST), never at Yahoo's 00:00 stamp —
  otherwise a post-open fill would read as pre-open and the gate would be useless;
- a 3-day context window, so a weekend's Friday bar shows as recency instead of "bars = 0";
- `[]` from a fetcher is "no evidence", never a flat price — no bar is carried forward;
- exit 3 (not 0) while unfilled, so CI cannot mistake a refusal for a scored round.

Re-run after 14:30Z:

```
python3 tools/r01_round_open_fill.py --picks /tmp/r01_field.json \
  --round-start 2026-11-23T14:30:00Z --out reports/r01_round_open_fill_2026-11-23.json
```

It writes the panel and calls the patched scorer itself once every tradable instrument has a
post-open bar.

## Files

- `reports/programme_alpha_sweep.json` — `denominator_status` RESOLVED + self-correction
- `updates/2026-11-23-programme-alpha-sweep-published-and-recomputed.md` — table and verdict corrected
- `ROOT_CAUSE_ANALYSIS_NON_CRYPTO.md` — AUDJPY deterministic-loser label corrected
- `tools/dsr_wiring_matrix.py` + `reports/dsr_wiring_matrix_2026-11-23.json` — new
- `tools/r01_round_open_fill.py` + `reports/r01_round_open_fill_2026-11-23.json` — new
