# Methodology R2 — Hedge-fund-grade pick + backtest methodology

Design a **measurement-first** methodology to reach Tier-2 performance per asset class on findtorontoevents.ca/audit.

## Constraints

- Harness: `tools/edge_stability_harness.py` — 14-day windows, eff threshold, sign stability, 30bps cost.
- Pre-register before backtest: `reports/hypothesis_registry.json` rule M-107.
- Resolver v2: class-specific win thresholds; use `asset_class_health` not raw tiles.

## Deliverables

### 1) Pick funnel methodology (per class)

For CRYPTO and one non-crypto class of your choice:
- Emitter → dedup → resolver → pf_registry cohort → harness → forward paper table
- Name **exact files/functions** at each stage
- Define **stop rules** (when to kill vs mutate vs forward-track)

### 2) Backtest methodology that would convince a skeptical PM

- In-sample / OOS split rule
- Multiple-testing control (reference `tools/fdr_control.py` if applicable)
- Minimum n and PF gates before any "proven" label
- How to handle duplicate emissions and confidence>1.0 bugs

### 3) Intraday vs daily decision

Should the **only** new hypothesis family be tick/1m crypto? Argue Y/N with 3 sentences of causal reasoning.

### 4) Score your own methodology

Rate your proposed methodology 1–5 on: falsifiability, cost realism, repo implementability. Be harsh.
