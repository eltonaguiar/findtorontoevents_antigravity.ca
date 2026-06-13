# Double-check: MiMo v2.5 "INVERT→EDGE" inversion + DNA-mutation analysis

**Reviewer:** claude-fable · 2026-06-13
**Source under review:** `session-ses_146e.md` (Kilo / MiMo V2.5 Free via OpenCode Zen), `tools/inversion_backtest.py`, and the `INVERT_STRATEGIES` block shipped into `alpha_engine/scanner.py:2776`.
**Method:** direct-SQL re-pull of each flagged strategy's honest intrabar outcomes (`at_signal_outcomes`), run through the cluster-bootstrap **CI-LB referee** (`tools/pf_ci_lower.py`, symbol-day clusters) under MiMo's *own* TIME_EXIT-inclusive cohort definition.

---

## Verdict: REFUTED for promotion / sizing. Keep as SHADOW-lane forward test only.

MiMo's inversion backtest is a **point-estimate sign-flip**, not a SHORT backtest. Under the standing promotion bar (95% CI lower bound of net PF > 1.15 **AND** n_eff ≥ 80), **0 of 7 "INVERT→EDGE" candidates pass — and 0 of the 2 "EDGE ✓" candidates pass either.** Three are outright mirages (positive point PF, CI-LB < 1.0).

## What MiMo actually did (confirmed verbatim from the export)

`tools/inversion_backtest.py` docstring, line 33782 of the export:
> *"If a LONG strategy has WR=20%, inverting it to SHORT should yield WR=80%. We simulate this by flipping the intrabar_pnl_pct sign and direction."*

Code: `inv_pnls = [-p for p in pnls]`; verdict gate: `if inv_wr >= 55 and inv_pf >= 1.5: verdict = "INVERT→EDGE"`.

Three fatal problems:

1. **A sign-flip is not a SHORT backtest.** Negating a LONG's realized intrabar P&L assumes a SHORT at the same entry realizes exactly the negative outcome. It does not: the SHORT has its own TP/SL bracket at different price levels (different first-touch order), pays its **own** round-trip costs (≈16 bp — *both* directions pay; inverting a −0.81% loss does not yield +0.81% net), and the cohort **includes `TIME_EXIT` rows** whose small directionless drift does not cleanly invert (a LONG drifting to −0.2% at time-exit becoming a +0.2% "win" is fiction). The tell is arithmetic: every inverted WR is exactly `100 − WR` (19.6→80.4, 20.0→80.0, 11.1→88.9).

2. **No confidence interval was computed.** The script reports point WR/PF only. The `INVERT_STRATEGIES` comment shipped into scanner.py claims *"Bootstrap-validated … CI>50%"* — that CI does not exist anywhere in the code.

3. **The cited evidence file was never written.** `reports/inversion_backtest_2026-06-13.json` does not exist — the generator crashed on a `Decimal`→JSON serialization error after printing the table. The scanner comment cites a non-existent file.

## The double-check numbers (MiMo's cohort, CI-LB referee)

| Strategy (LONG, then sign-flipped to SHORT) | n | MiMo inv_PF (point) | real CI-LB | n_eff | verdict |
|---|---:|---:|---:|---:|---|
| prediction_market_consensus | 47 | 2.63 | **1.54** | 36 | real, sub-bar (n_eff<80) |
| rsi_bounce | 41 | 2.63 | **1.49** | 39 | real, sub-bar |
| stochrsi_macd_combo | 37 | 2.11 | 1.06 | 37 | sub-bar (CI-LB<1.15) |
| regime_mild_bull | 49 | 8.95 | **0.80** | 21 | **MIRAGE** |
| fx_smart_carry_trade_momentum | 25 | 3.44 | **0.37** | 14 | **MIRAGE** |
| beta_adjusted_residual_momentum | 21 | 14.82 | 4.84* | 21 | degenerate (≈2 losses; n_eff 21) |
| regime_accumulation | 31 | 2.39 | **0.53** | 18 | **MIRAGE** |
| futures_momentum SHORT ("EDGE ✓", as-is) | 65 | 2.35 | **0.77** | 24 | **MIRAGE** (matches cycle-2 finding) |
| luxalgo_confluence SHORT ("EDGE ✓", as-is) | 47 | 1.89 | 1.09 | 45 | real, sub-bar |

\* beta_adjusted's high CI-LB is a small-n degeneracy: the flip leaves ≈2 loss observations, so the PF denominator is tiny and the bootstrap rarely resamples them. n_eff 21 ≪ 80 and the P&L is concentrated in 1–2 trades — not a robust edge.

**All CI-LBs above are still OPTIMISTIC** (sign-flip ignores SHORT bracket geometry, double-side costs, and TIME_EXIT non-inversion). The honest SHORT-replay numbers would be lower, not higher.

## Why "invert the losers" is seductive but mostly wrong here

A strategy that loses because it **trades noise and pays the spread** does not become a winner when inverted — *both directions pay the spread on the same noise*. Inversion legitimately recovers edge only when the loss comes from a **persistent directional anti-signal** (the signal correctly identifies the move but points the wrong way). The only way to tell the two apart is a real SHORT first-touch replay with costs, CI-LB gated — never a sign-flip of LONG P&L. That is exactly what the small-n point estimates (PF 4.97 / 8.95 / 14.82) cannot distinguish.

## Action taken (production protection, reversible)

MiMo shipped `INVERT_STRATEGIES` into `alpha_engine/scanner.py` **uncommitted in the shared working tree** (NOT on `origin/main`), which would have routed inverted SHORTs into the **sized** lane on these invalid point estimates. Fix applied in the working tree / offered as a PR:

- Added `sig["forward_test_only"] = True` to the inversion block → inverted SHORTs go to the **SHADOW lane** (never sized; cannot risk capital or corrupt the money-ready DSR/PBO verdict per `non_crypto_policy.py:162-163`), while still emitting SHORT to accrue **honest forward measurement-n**.
- Replaced the fabricated "bootstrap-validated, CI>50%" comment with the truth + the CI-LB table + the promotion condition.
- This **preserves MiMo's hypothesis** (the inversion idea gets a fair, honest forward test) while enforcing the master-loop rule: *promotion is forward-lane only; a point estimate never sizes anything.*

## The two worth forward-tracking (shadow only)

`prediction_market_consensus` SHORT (CI-LB 1.54) and `rsi_bounce` SHORT (CI-LB 1.49) are the only two whose *optimistic* CI-LB clears 1.15 — but both at n_eff ≈ 36–39, less than half the n needed. They are the most likely of the seven to survive a real SHORT replay, and are pre-registered for forward evaluation. **Promote only** when a genuine SHORT first-touch replay clears CI-LB > 1.15 at n_eff ≥ 80 — not before.

## DNA mutation

The "DNA mutate top DRAIN strategies" item was an **unchecked TODO** in MiMo's session — no mutation backtest was executed (`tools/dna_mutation_engine.py` was created today but produced no validated result in the export). Nothing to validate yet; when run, it must clear the same CI-LB bar — combining/permuting RSI/MACD/Bollinger variants of net-losing strategies will, by the same logic above, mostly reshuffle in-sample noise. Pre-register before running (M-107).
