# Multi-AI "Real-Money Ready" Roadmap — Validation — 2026-05-17

Four external AIs (Claude Sonnet 4.6-search, Perplexity sonar-reasoning-pro,
Grok-4.2-multiagent, ChatGPT o3-search) each produced a "real-money-ready roadmap" for /audit.
All three audited the **public GitHub-Pages `premium.html`** — NOT the repo
(repo is private). Validated each claimed "gap" by grep against the live repo.

## Verdict: most claimed gaps are FALSE — they already exist

| Claimed gap (Sonnet / ppl-sonar) | Reality (verified in repo) |
|---|---|
| "No walk-forward validation" | **FALSE** — `alpha_engine/walkforward_validator.py` (`walk_forward_by_class`), hourly cron |
| "No safety nets / kill-switch / circuit breaker" | **FALSE** — `breaker_namespaces.py`, `advanced_risk_system.py`, `charter_position_sizer.py`; HALT flag exists |
| "No regime gating" | **FALSE** — `bayesian_regime_reference.py`, `equity_vix_regime_momentum.py`, HMM 7-state |
| "No position sizing" | **FALSE** — `alpha_engine/backtest/position_sizing.py` (Kelly, vol-target, the A3 `vol_scalar_cap`) |
| "No anti-overfit / DSR" | **FALSE** — `deflated_sharpe.py`, `tools/pbo_cscv.py`, `anti_overfit_validator.py` |
| "168 strategies, no statistical filter" | **PARTLY false** — quality_gates + DSR + PBO + blocklists exist; but see the one real gap below |
| "No shadow mode" | **FALSE** — SHADOW tier in the strategy state machine; cot paper-pilot ran in SHADOW |

**Grok-4.2 was the only one that got it right** — it correctly stated "this is
NOT a simple monolithic backtester... already a sophisticated research/audit/
forward-validation layer with institutional anti-overfit thinking." Sonnet 4.6
and ppl-sonar both hallucinated the absence of a validation layer because they
only saw the static `premium.html` placeholder page (all `--` values).

## Genuinely NEW — worth adding

1. **White's Reality Check / Hansen's SPA / Model Confidence Set** — grep for
   `reality.check`, `bootstrap MCS`, `SPA test`, `model_confidence_set` returns
   **NOTHING**. The repo has PBO/CSCV + DSR (per-strategy) but no family-wise
   multiple-comparison correction across the full strategy set. With ~168-369
   strategies this is a real p-hacking exposure. Adding a bootstrap SPA test is
   a legitimate, novel hardening — distinct from per-strategy DSR.
2. **CIRO event-contract regulatory note** — informational. CIRO (2026-03-26)
   authorized event-contract trading; election/political contracts banned;
   30-day min maturity; no leverage. Relevant only to the events/prediction
   surface, NOT to the technical price-signal /audit. A pure price-signal
   dashboard is outside event-contract rules — but worth a one-line awareness
   note. Not an engineering action.

## What is NOT new (reject as MASTER_ACTION_PLAN items)
Live WebSocket feeds, kill-switch, circuit breaker, regime gating, position
sizing, shadow mode, DSR, transaction-cost model — all already in the repo.
The roadmaps' Pillars 1-5 are ~80% re-describing existing infrastructure.

**ChatGPT o3-search (4th report):** same pattern — claims "incomplete risk
layer / no kill-switch / no broker adapter." Risk layer + circuit breaker
ALREADY exist (verified above). "No broker adapter" is TRUE but BY DESIGN —
/audit is a signal/audit/forward-test platform; live order routing is paper
via TradingView, intentionally not a repo concern. o3's only fair points:
Dockerfile/env-lock absence (irrelevant — runs in GitHub-Actions CI, not
containers) and a credentials-hygiene flag (memory `feedback_db_credentials_env`
+ `reference_db_credentials_env` confirm DB creds are env vars, NOT hardcoded —
o3 likely saw config that *references* env keys). o3 adds nothing new.

*Validated by direct repo grep, 2026-05-17 — more rigorous than a swarm vote
(3 AIs agreeing on "no walk-forward" does not make it true; `walkforward_validator.py`
exists). Convergence-trap avoided.*
