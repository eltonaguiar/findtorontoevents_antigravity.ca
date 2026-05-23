# Confidence Score Inversion Root Cause Analysis

You are a quantitative researcher with Lopez de Prado level expertise.

## Context
A trading system has an `ml_score` field that shows INVERTED correlation with forward win rate:
- Higher `ml_score` → worse actual WR (negative correlation)
- System uses walk-forward eff-stability gate across 5 14-day windows
- Scores are normalized from 0-100 format to 0.0-1.0 via `_normalize_confidence`
- EQUITY class: PF~1.55, WR~51%, n=426 post-resolver

## Task
Name the 3 most likely root causes of ml_score inversion. For each:
1. Root cause name
2. How it produces a NEGATIVE correlation (mechanistic explanation)
3. How to diagnose it (one specific test or query)
4. How to fix it

Then rank which is most likely given this context:
(a) Label leakage — future price data leaked into training features
(b) Overfit on in-sample period — model memorized regime that has since reversed
(c) Regime change — market structure changed post-training
(d) Wrong loss function — model optimized for wrong objective (e.g., accuracy on balanced dataset)

Provide the ranking with brief statistical reasoning. Be direct — no preamble.
