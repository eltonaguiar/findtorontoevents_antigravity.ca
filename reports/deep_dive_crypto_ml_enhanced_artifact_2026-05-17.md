# Deep-dive — CRYPTO `ml_enhanced` is a strategy-mining artifact (2026-05-17)

Triggered by: "improve money-ready per asset class — find patterns, find
incorrect data." This is the single most important data-integrity finding of
the session. It **retracts** the CRYPTO edge claims in MASTER_ACTION_PLAN §27
(M-088) and `reports/weekly_filter_20260517T221055Z.md`.

## The finding

The CRYPTO "confidence≥0.70 edge" — reported as WR 63% / PF 6.67 / n=119 in
§27 and the weekly filter — is **100% selection bias from a strategy-mining
sprawl.** Evidence, all from `closed_picks.json`, policy-clean, net-of-slippage:

| Cut | n | WR | PF |
|---|---|---|---|
| CRYPTO conf≥0.70 — ALL | 119 | 63.0% | 6.67 |
| CRYPTO conf≥0.70 — **excluding `ml_enhanced_*`** | **0** | — | — |
| CRYPTO conf≥0.50 — **excluding `ml_enhanced_*`** | **0** | — | — |
| `ml_enhanced_*` family — ALL confidences | 778 | 51.8% | **0.63** |
| CRYPTO non-`ml_enhanced` policy-clean — ALL | 108 | 30.6% | 0.33 |

Two facts kill the edge claim:

1. **Confidence ≥0.5 is emitted ONLY by the `ml_enhanced` family** — zero
   non-ml_enhanced CRYPTO picks carry confidence ≥0.5. "Confidence is a clean
   monotonic edge filter" (§27 §27.1) is false: it is not a signal quality
   axis, it is a label one family stamps on itself.
2. **The `ml_enhanced` family is a net LOSER** — 778 picks, PF 0.63. The
   conf≥0.70 slice (PF 6.67) is the **post-hoc winning tail** of a losing
   family.

## Why it happens — the mining sprawl

`ml_enhanced` is **149 distinct strategies**, one per
`ml_enhanced_<SYMBOL>_<TIMEFRAME>_<MODEL>` combination
(RENDERUSDT_1h_D_ensemble_stack, FETUSDT_1d_B_lightgbm, …). **119 of the 149
have n=1.** A few land high-PF by chance — `ml_enhanced_DYDXUSDT_15m_D_
ensemble_stack` shows PF 60.5 / WR 96.8% on n=31; `FETUSDT_1d_B_lightgbm`
PF 9.4 — alongside `JTOUSDT_1d` PF 0.30 and `APEUSDT_1d` PF 0.05. This is a
multiple-comparison factory: spawn a model per symbol×TF×algo, and the
right tail looks like genius.

## Incorrect-data / verdict-distortion consequences

1. **`pf_registry` CRYPTO net PF 1.28 is itself contaminated.** It is a blend
   of the ml_enhanced winning tail offsetting the ml_enhanced losing body +
   the catastrophic non-ml book (PF 0.33). Strip the mining sprawl and CRYPTO
   has no edge.
2. **The DSR gate under-deflates CRYPTO.** `money_ready_verdict._dsr_gate`
   uses `nb_trials = ASSET_CLASS_SOURCE_SYSTEMS["CRYPTO"] = 14` (M-076 — count
   source-system families). But each `ml_enhanced_<symbol>_<tf>_<model>` is an
   **independent trial** (different symbol, different model — not a correlated
   variant of one strategy). The true CRYPTO `nb_trials` is closer to
   14 + ~149 ≈ 160. At nb_trials=14 the DSR haircut is far too small — the
   CRYPTO "DSR PASS" is an artifact of under-counting trials.
3. **`ml_enhanced` is NOT in any block/kill list** — it is fully policy-clean,
   so it flows unfiltered into `asset_class_health`, `pf_registry`, and
   `money_ready_verdict`. Nothing currently de-weights it.

## Retractions

- **MASTER_ACTION_PLAN §27 M-088** ("hard confidence≥0.50 exec gate — highest-EV
  single change") — **RETRACTED.** A confidence gate just selects the
  ml_enhanced winning tail; it would hard-wire the selection bias.
- **`reports/weekly_filter_20260517T221055Z.md`** CRYPTO filter
  (`confidence≥0.70`) — **RETRACTED.** Not a proven edge.

## Recommended actions (supersede §27.1)

- **M-105** — treat the `ml_enhanced` family as ONE multiple-tested factory:
  either (a) run White's Reality Check / SPA (M-065) over its 149 variants and
  keep only survivors, or (b) quarantine the whole family from verdict
  aggregates until it does. Until then, `ml_enhanced` strategies must not feed
  `asset_class_health` / `pf_registry` / `money_ready_verdict`.
- **M-106** — fix `money_ready_verdict` `nb_trials`: count per-symbol ML
  variants as independent trials, not as one source system. CRYPTO nb_trials
  ≈ 160, not 14.
- **Honest CRYPTO verdict:** with the mining sprawl removed, CRYPTO
  non-ml_enhanced is PF 0.33 — a deep loser. CRYPTO is **not close** to
  real-money ready; the prior "PF 1.28, sub-T2-but-improvable" framing was too
  generous.

## How this improves money-readiness

It does not add edge — it **removes a phantom edge** that §27 + the weekly
filter were about to route capital toward. Catching the mining artifact
before it is "money-readied" is the highest-value outcome of a deep-dive: the
DSR/SPA gates exist precisely for this, and this finding shows they are
currently bypassed by the source-system trial-count under-estimate.
