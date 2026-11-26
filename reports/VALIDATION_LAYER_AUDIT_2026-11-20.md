# Validation Layer Audit — 2026-11-20

Directive (Grok, relayed): *"Wire the existing PBO/CPCV/DSR code you already have
before any new signal work. Fix the zero-PnL data pipeline first — otherwise every
backtest is garbage."*

Verdict: **the code exists in abundance, and that is the problem.** Wiring it is
not a mechanical task because there are ~23 implementations of three statistics
with different contracts, and at least four are materially defective.

All numbers below are reproducible from this repo's own modules on synthetic
series with known truth, or on real SPY/QQQ/IWM/TLT data.

---

## 1. Implementation census (main tree, excluding worktrees)

| Statistic | Count | Locations |
|---|---|---|
| Deflated Sharpe | **10** | `alpha_engine/deflated_sharpe.py`, `alpha_engine/anti_overfit_validator.py`, `alpha_engine/validation/statistical_gates.py`, `alpha_engine/validation/sharpe_metrics.py`, `alpha_engine/statistical_rigor.py`, `alpha_engine/backtest_etf_dual_momentum.py`, `alpha_engine/run_massive_mutations.py`, `alpha_engine/audit3_tribunal.py`, `research/profitability/backtest.py`, `probabilistic_sharpe_engine.py` |
| PBO / CSCV | **7** | `alpha_engine/anti_overfit_validator.py`, `alpha_engine/rigorous_backtest_harness.py`, `alpha_engine/strategy_verification_engine.py`, `tools/pbo.py`, `tools/pbo_cscv.py`, `ml_crypto_predictor/enhanced_models/advanced_validation.py`, `research/profitability/backtest.py` |
| Walk-forward / purged CV | **6** | `crypto_ml_edge/validation.py`, `tools/strategy_prover/strategy_prover.py`, `alpha_engine/backtest_etf_dual_momentum.py`, `ml_battleground/system_c_deeplearn/train_model.py`, `ml_crypto_predictor/enhanced_models/advanced_validation.py`, `tools/wfe.py` |

Three statistics, twenty-three implementations, no two of which are guaranteed to
return the same number. **The verdict a strategy receives depends on which import
the auditor happens to use.** That is not a validation layer; it is a lottery.

---

## 2. The good news (verified, not assumed)

The production path is using a **correct** implementation:

`tools/anti_overfit_audit_sidecar.py` imports
`from alpha_engine.anti_overfit_validator import cpcv_pbo, deflated_sharpe`,
computes `sharpe = mu / sd` (**per-period — correct units**), sets
`n_trials = len(strat_returns)`, and grades `dsr >= 0.95 → EDGE_LIKELY_REAL`.

On a series with provably zero edge (best of 1,000 pure-noise draws, 500 obs,
annualised IS Sharpe 2.51), the two correct implementations agree:

| implementation | DSR | correct? |
|---|---|---|
| `anti_overfit_validator.deflated_sharpe` (per-period) | **0.6139** | yes — rejects |
| `statistical_rigor.deflated_sharpe_ratio` | **0.6111** | yes — rejects |

Agreement to 0.003. So there is a real, usable core. The rest of this document is
about the ways that core is surrounded by traps.

---

## 3. Defect A — silent unit footgun in the canonical DSR (LATENT)

`alpha_engine/anti_overfit_validator.py::deflated_sharpe` documents:

> `strategy_sharpe`: observed (un-annualized **OR** annualized -- consistent with
> the returns_array sampling rate) Sharpe of the candidate.

That "or" is wrong. The Lo (2002) variance
`sr_var = (1/n)(1 - skew*SR + (kurt/4)*SR²)` requires **per-period** SR. Passing
an annualised SR does not raise — it returns a *higher* DSR:

| argument passed | DSR | verdict |
|---|---|---|
| per-period SR 0.1582 | 0.6139 | correctly rejects |
| annualised SR 2.5113 | **1.0000** | **PASSES** |
| `n_trials=1` | → `e_max = 0` | multiple testing silently disabled |

Same series, zero true edge. The production caller happens to get this right, so
this is **latent, not live** — but the docstring actively invites the wrong call,
and the failure mode is a silent 1.0, the maximum-confidence answer.

**Fix:** reject `abs(strategy_sharpe) > 1.0` with a clear "per-period Sharpe
required" error, or add an explicit `annualised: bool` parameter. Never let a
unit error return a passing grade.

---

## 4. Defect B — `tools/pbo.py` is blind to selection (SEVERE)

`tools/pbo.py::probability_of_backtest_overfitting(returns, n_splits=8)` claims
to compute PBO from a single series by embedding it beside a `1e-6`-scale noise
column "so the candidate isn't trivially dominant."

PBO exists for exactly one purpose: to detect the selection bias created by
picking the best of N candidates. This implementation never sees N.

Measured — series selected as best-of-N from **pure noise**, 12 trials each:

| source of the series | mean `tools/pbo.py` |
|---|---|
| best of 1 | 0.3905 |
| **best of 50** | **0.0000** (all 12 trials) |

Gate 3 is `PBO < 0.05`. So a strategy that is provably pure noise, chosen from 50
candidates, **passes gate 3 with PBO = 0.0000**. Selection makes the score look
*safe* rather than risky — the statistic is inverted with respect to its purpose.

Compare the honest CSCV engine on the same candidate matrices:

| matrix | `tools/pbo_cscv.compute_pbo` |
|---|---|
| 2-strategy noise | 0.0000 |
| 50-strategy noise | **0.8286** — correctly rejects |

Root cause: any series with a slightly positive mean beats a `1e-6` bench-mark
out-of-sample, so the "PBO" collapses toward 0 for *any* positive-drift input.
It measures "is the mean positive", not "does the in-sample winner survive".

**Fix:** delete or hard-deprecate `tools/pbo.py`; redirect its one caller
(`tools/h037_forward_verification.py`) to `tools/pbo_cscv.compute_pbo` with a
real candidate matrix. If no matrix is available, return `nan` — an unavailable
statistic must not masquerade as a passing one.

---

## 5. Defect C — `evaluate_strategy()` fabricates its peer cohort

`alpha_engine/anti_overfit_validator.py::evaluate_strategy` computes PBO against
**synthetic zero-mean series** generated from the strategy's own standard
deviation. Its docstring concedes "degraded mode" but the degraded value is what
callers receive:

| input | PBO |
|---|---|
| pure noise series (6 draws) | 0.222 – 0.844 |
| honest 40-column noise matrix | 0.333 |
| `evaluate_strategy` on one column | **0.267** |

Not a valid PBO, and not obviously conservative. **Fix:** require the candidate
matrix; return `nan` when absent.

---

## 6. Defect D — `tools/wfe.py`: single split, and the docstring lies about embargo

Grok's gate 2 is "WFA ≥5 splits, WFE > 60%". `tools/wfe.py`:

- `walk_forward_split()` is **one** contiguous 70/30 cut. Not ≥5 splits.
- Module docstring: *"Implements the standard 70/30 IS/OOS split (**with
  embargo**)"* — there is no embargo and no purge anywhere in the file. The
  function body is `r[:split]`, `r[split:]`.
- It returns `max(0, min(2, oos_sharpe / is_sharpe))`, clipping a strongly
  *negative* OOS Sharpe to 0.0 — loss of magnitude information.
- It is **orphaned in the main tree**; its only importers are
  `tools/h037_forward_verification.py` copies inside worktrees.

Meanwhile a genuinely good implementation exists and is unused by the gate path:
`crypto_ml_edge/validation.py::WalkForwardSplit` — 5 folds, expanding or rolling
windows, `purge_gap=20` bars, `embargo_pct=0.01`, `min_train`/`min_test` floors,
and a regime-coverage check that asserts a 2022 bear window appears in at least
one test fold. This is the one to standardise on.

---

## 7. Defect E — CI runs the gates but nothing can fail

Correcting an earlier overstatement of mine. The gates **are** invoked:

- `.github/workflows/audit-dashboard.yml:279` →
  `python tools/anti_overfit_audit_sidecar.py --min-n 20 || echo "::warning ..."`
  with `continue-on-error: true`.
- `.github/workflows/audit-dashboard.yml:696` — a freshness tripwire on
  `anti_overfit_audit.json` (24 h) and `walkforward_results.json` (8 d), also
  `continue-on-error: true`, and it asserts **staleness, not values**.
- `.github/workflows/strategy-funnel-hourly.yml:73` only *reads* precomputed
  `dsr, pbo` columns out of `strategy_summary` for display.

So CI proves the audit **ran**. It never fails on the audit's **result**. Every
gate is advisory. A strategy with DSR 0.10 and PBO 0.90 produces a green build
plus a warning annotation.

**Fix:** one blocking job — `if dsr < 0.95 or pbo >= 0.05: sys.exit(1)` — scoped
to the cohort actually being promoted, so it fails closed without blocking the
dashboard refresh itself.

---

## 8. Gate-status matrix (Grok's seven gates)

| # | Gate | Exists? | Correct? | Enforced? |
|---|---|---|---|---|
| 1 | Point-in-time data, no survivorship | partial | unverified | no |
| 2 | WFA ≥5 splits, WFE > 60% | yes (`crypto_ml_edge`) | yes | **no** — good impl unused; `tools/wfe.py` is 1 split |
| 3 | CPCV, PBO < 0.05 | yes | `pbo_cscv` yes / `tools/pbo` **no** | no — advisory only |
| 4 | DSR > 0.95 after trials | yes | yes, but unit footgun | no — advisory only |
| 5 | Net of realistic costs | yes (`round_trip_cost_pct`) | yes | per-module, not global |
| 6 | Paper/forward OOS 60–90 d | partial | — | no |
| 7 | Hard kill switches | partial | — | no |

Nothing is enforced. Two of the four statistic families have a defective
implementation sitting next to the correct one, and for PBO the defective one is
the one whose name reads like the obvious choice (`tools/pbo.py`).

---

## 9. Applied case study — H-01/H-03 residual mean-reversion

The peer's Layer-2 correction was right and is now implemented: `expected_pct =
max(0, |s| - EXIT_S) * sigma_eq * 100`. I ran the corrected gate.

My earlier claim that "the gate is structurally incapable of binding" was
**wrong** — measured median `sigma_eq` = 0.2470 %, just under the corrected
binding threshold of 0.2667 %, so it binds on 36/153 trades (23.5 %).

But the deeper result supersedes both my position and the peer's remedy:

| bucket | n | mean gross | mean net | win rate |
|---|---|---|---|---|
| REMOVED by gate | 36 | **+0.1497 %** | −0.0503 % | 0.222 |
| KEPT by gate | 117 | +0.0476 % | −0.1524 % | 0.248 |

The gate removes the trades with **3.1× higher** gross expectancy. It binds
*more* and is *less* informative — it is inversely informative.

Mechanism: `expected_pct ∝ (|s| - 0.5) · sigma_eq`, so gating on
`expected_pct ≤ cost` is gating on **low `sigma_eq`**. Low `sigma_eq` means a
quiet residual, and quiet residuals revert more reliably. The gate screens on
forecast *magnitude* and therefore penalises the regime where the model works.
Confirmed independently — realised gross by `|entry_s|` quartile is **monotonically
decreasing**: Q1 +0.2758 % → Q4 −0.0180 %, the exact opposite of the model's
premise.

Hedge-corrected performance (hedge P&L now booked):

```
mean_gross  = +0.0716%      mean_net = -0.1284%
win_rate    = 24.18%        PF       = 0.623
exits       = revert 54 / time 99 / stop 0   (64.7% time-capped)
cost model  = 4 fills x 5bp = 20bp round trip
```

Gross alpha +7.2 bp against a 20 bp cost. It needs round-trip cost below ~7 bp,
which a two-leg residual trade does not offer. **H-01 → NOT_PROVED.** Do not
retune.

Peer's open question — do the 64.7 % time-cap exits cluster by regime?
**No. They are uniform.** Time-exit rate across `half_life_at_entry` quartiles:
0.673 / 0.588 / 0.778 / 0.667. Across `|entry_s|` quartiles: 0.684 / 0.579 /
0.615 / 0.711. LONG 0.639 vs SHORT 0.657. By the peer's own decision rule —
"if uniformly distributed, the residual is simply not reverting" — the regime
filter (P3-c) is not worth building.

---

## 10. Ordered remediation

1. **Make one gate blocking.** Highest leverage; without it nothing else matters.
2. **Deprecate `tools/pbo.py`** (inverted), redirect to `pbo_cscv` on a real matrix.
3. **Harden `deflated_sharpe`** against annualised input returning 1.0.
4. **Standardise walk-forward on `crypto_ml_edge/validation.py`**; delete the
   embargo claim from `tools/wfe.py` or implement the embargo.
5. **Make `evaluate_strategy` return `nan`** rather than a synthetic-peer PBO.
6. Only then: new signal work, one asset class at a time, hypothesis
   pre-registered before the run.
