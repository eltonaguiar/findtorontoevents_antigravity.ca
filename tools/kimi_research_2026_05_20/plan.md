# Plan: FindTorontoEvents AntiGravity Trading System Overhaul

## Goal
Improve `findtorontoevents.ca/audit` picks per asset class to be statistically proven winners (not flukes) by deploying a multi-strategy validation system.

## Asset Classes
- CRYPTO, FOREX, EQUITY, COMMODITY, ETF, FUTURES, BOND, PENNY_STOCK, STOCKS

## Stages

### Stage 1: Discovery
- Fetch GitHub repo: `https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/`
- Identify codebase structure, ASCII diagram files (.MD with box drawings)
- Locate key modules: pf_registry, hypothesis registry, quality gates, outcome resolver
- Identify current performance per asset class

### Stage 2: Analysis (Parallel Subagents)
- Deploy 1 subagent per major asset class (7-8 agents):
  1. CRYPTO agent
  2. FOREX agent
  3. EQUITY agent
  4. COMMODITY agent
  5. ETF agent
  6. BOND/FUTURES agent
  7. PENNY_STOCK agent
  8. Infrastructure/Data Integrity agent (outcome resolver, DB integrity, edge stability)

### Stage 3: Strategy Engine Build
- Multi-strategy generation per asset class
- Statistical validation (Sharpe, p-values, FDR correction, walk-forward testing)
- Ensemble construction
- Back-testing harness

### Stage 4: Integration & Deploy
- Integrate improvements into codebase
- Validate with audit class
- Deploy updated system

## Current Date: 2026-05-20
