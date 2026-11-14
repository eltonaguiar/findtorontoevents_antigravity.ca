# FINAL_V2 — finpredict-v3 (2026-11-14, final stage)

Last-pass review focused on **profitability per asset class** and final peer adjudication.
This v2 folder is the closing deliverable; it re-derives the honest per-class profit
picture and proposes concrete, capital-aware paths to profitability.

## Contents

| Folder | Purpose |
|---|---|
| `00_INDEX.md` | this file |
| `01_profitability_per_asset_class/` | per-class reality + how to get profitable there |
| `02_peer_reviews/` | final adjudication of peers (incl. the VWAP dispute) |
| `03_ideas_proposals/` | concrete proposals (methods, gates, infra) |
| `04_evidence/` | evidence manifest + links to run artifacts |

## Bottom line

- **Real profitable signal families found** (not noise): time-series momentum/trend
  (vol-targeted), funding/carry, and regime-filtered mean-reversion — but all have
  honest caveats (survivorship, beta-vs-B&H, capacity, capital intensity).
- **A disputed claim was adjudicated**: childlike-airport's "VWAP Sharpe 3.76" is
  refuted by the quant-audit peer (annualization unit error → real Sharpe ≈1.18).
  Do NOT adopt it as a headline "validated" edge.
- **The path to profitability is a small portfolio of 2–4 verified risk-premium
  strategies with capital/execution gates** — not mining more signals.
