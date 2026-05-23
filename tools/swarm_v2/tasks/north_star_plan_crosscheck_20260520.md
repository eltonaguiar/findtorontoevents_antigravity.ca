# Swarm Task: Cross-Check North Star Action Plan — 2026-05-20

**Task ID:** north-star-plan-crosscheck-20260520
**Priority:** P0
**Mode:** research + critique (no code changes)

## Context

We have a trading system (findtorontoevents.ca/audit) with 7 asset classes.
Goal: hedge-fund-grade statistical edge per class (Tier-2: PF≥1.5, WR≥50%, MDD<20%, n≥100).

### Current State (LIVE from hypothesis_registry.json)

| Hypothesis | Class | Status | Key Metrics |
|---|---|---|---|
| H-037 VIX term structure carry | ETF | **PASSED** harness | WR=58.9%, PF=1.295, n=1185, eff=0.75, 3/4 WF folds |
| H-001 COT positioning | COMMODITY | LIVE_TESTING | WR=78.4%, n=134, 2/3 windows stable |
| H-021 COT small spec exhaustion | COMMODITY | NEAR_ADMISSIBLE | — |
| ~14 others | Various | KILLED | Sign instability dominant failure mode |

### Canonical pf_registry (policy_clean_net)

| Class | n | PF | WR% |
|---|--:|---:|---:|
| CRYPTO | 1116 | 0.64 | 44.1% |
| FOREX | 148 | 1.49 | 56.1% |
| COMMODITY | 55 | 1.42 | 54.5% |
| EQUITY | 5 | 0.25 | 20.0% |
| ETF | 2 | — | 50.0% |
| BOND | 5 | 0.00 | 0.0% |

### Plan Actions (Phase 0 — Next 48h)

1. **D0-1:** Stand up H-037 paper trading (30-day forward verification)
2. **D0-2:** Ship DSR/PBO/WFE/FDR tools (tools/dsr.py, pbo.py, wfe.py, fdr_control.py)
3. **D0-3:** H-037 PF boost — vol-scaled sizing + tighter stops (target +0.22 PF → 1.52)
4. **D0-4:** H-001 COT 3rd window — lock parameters, pre-commit end date
5. **D0-5:** Kill H-035 intraday crypto probe (5-20% odds too low)
6. **D0-6:** Rewrite plan baseline (done — "0 admissible" → "1 passed, 1 live")

### Peer Review Findings (5 engines: Grok WSL x2, DeepSeek, xAI, Cerebras)

- H-037 is first admissible but PF=1.295 < 1.5 Tier-2 gate
- H-001 COT gets priority over H-037 (WR=78.4% > 58.9%)
- KILL H-035 intraday crypto probe
- PF boost of +0.22 achievable via vol-scaled sizing + tighter stops

## Research Questions

### Agent 1 — H-037 Viability
Is H-037 (VIX term structure carry, ETF) genuinely the first real edge?
- PF=1.295 is below Tier-2 PF≥1.5. Can it realistically reach 1.5?
- What are the specific risks of paper-trading this now?
- Should we wait for H-001 COT to reach full admissibility first?

### Agent 2 — H-001 COT Priority
H-001 has WR=78.4%, n=134, 2/3 windows stable.
- What's the fastest path to 3rd window given CFTC release schedule?
- Is WR=78.4% sustainable or likely mean-reverting?
- What kill criteria should we pre-commit for H-001?

### Agent 3 — Resource Allocation
Given limited engineering bandwidth:
- Should we parallelize H-037 paper + H-001 live, or sequence them?
- Is the PF boost work (D0-3) worth the effort vs. just waiting for more data?
- What's the single highest-ROI action in the next 7 days?

## Constraints
- NEVER run dashboard_generator.py
- NEVER invent numbers — all figures must come from actual files
- Output: 3 concise reports, one per agent
