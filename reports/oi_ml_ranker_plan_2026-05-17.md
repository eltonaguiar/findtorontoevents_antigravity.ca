# OI -> ml_ranker — approach, swarm review, decision (2026-05-17)

## Task
Wire `oi_change_24h` (crypto futures open-interest 24h % change) into the
pick-quality model. Originally framed as "add it to `ml_ranker.FEATURE_LIST`".

## Swarm design (swarm_run: deepseek + xai + grok-4.3)
Both substantive engines converged:
- Adding a feature to `FEATURE_LIST` mandates a **full retrain** (incremental
  train warm-starts a fixed-width XGBoost booster — cannot grow feature count).
- Needs a predict-time version guard (align live vector to the cached model's
  `trained_feature_names`) to survive the skew window before the retrain.
- **xai go/no-go: NO-GO as an ML feature** given only a few hundred closed
  crypto picks — low statistical power, high overfit / Boruta-reject risk.
  Recommended a rule-based OI-extreme gate instead.
- This converges with the earlier Grok + Cerebras reviews this session
  ("prefer hard rules over ML columns at small N").

## Vetting — the blocking finding
Checked the data: **0 of 6884 closed crypto picks carry `oi_change_24h`**, and
0 active picks. `scanner.py` injects it onto live *signals* but it was never
written into `compute_ml_features_at_entry()` (the persisted `ml_features_at_entry`
record the model trains on). Therefore:
- ML feature  -> impossible now: the model would train on an all-missing column.
- Rule gate   -> impossible now: no history to set or validate a threshold.

The true first step is **data persistence**, not the model change.

## Executed (this PR)
`compute_ml_features_at_entry()` now fetches `oi_change_24h` via
`coinalyze_client.get_open_interest()` and stamps it into `ml_features_at_entry`.
Additive + harmless: the ml_ranker vectorizer only reads keys present in
`FEATURE_LIST`, so an extra dict key changes nothing until deliberately wired.

## Staged roadmap (after ~30-60 days of accumulated data)
1. Backtest: do closed crypto picks with extreme `|oi_change_24h|` show
   materially worse WR/PF? Derive the threshold from data, not a guess.
2. If signal is real -> EITHER
   - rule gate: env-gated, default-OFF, shadow-first OI-extreme gate in
     `quality_gates.py` (repo pattern: ONCHAIN_REGIME_GATE / M-034); OR
   - ML feature: add `oi_change_24h` to `FEATURE_LIST` END + vectorizer, add a
     predict-time length guard, force ONE full retrain, gate promotion through
     the existing champion/challenger `model_comparison.json` check.
3. If no signal -> close the task: OI does not predict; do not add it.

## Decision
Do not touch `ml_ranker.FEATURE_LIST` now. Persist the data (done), revisit in
~30-60 days with real history. Low-risk, evidence-first.
