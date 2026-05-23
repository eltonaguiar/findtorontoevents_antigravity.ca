"""Multi-AI consensus research orchestrator for per-asset-class picks.

Produces sourced, backtested, cross-tested, multi-AI-consensus
strategy candidates per asset class for `findtorontoevents.ca/audit`.

5-pass protocol per asset class:
  P1  LITERATURE   — swarm gathers cited sources (URL + access_date + claim)
  P2  CANDIDATES   — swarm proposes ≥5 backtestable strategy specs
  P3  BACKTEST     — orchestrator runs each via alpha_engine.backtest.engine
  P4  CROSS-TEST   — overlap test vs existing repo strategies
  P5  SYNTHESIS    — swarm votes go/no-go, drafts wiring plan, renders HTML

Design: see `updates/2026-05-11-research-orchestrator-design.md`.
"""
