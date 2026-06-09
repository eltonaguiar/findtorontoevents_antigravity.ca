---
tags: [reference, research, personas, asset-classes]
created: 2026-06-09
status: active
---

# Per-Asset-Class Web Research & Persona Index

## Web research per asset class — DONE & current ✅
The **Research Orchestrator** (`tools/research/orchestrator.py`, workflow `research-orchestrator.yml`) runs a 5-pass cycle per class — P1 literature → P2 candidate distillation → P3 backtest → P4 out-of-sample cross-test → P5 synthesis. Live index: `findtorontoevents.ca/audit/research_index.html`.

- **Cadence:** weekly, Saturday 06:00 UTC (cron `0 6 * * 6`). **Last run 2026-06-06 = SUCCESS**, all 7 classes (crypto/equity/forex/commodity/etf/bond/futures). Not stalled — on schedule.
- **Verdicts (consistent with our 0-edge finding):** out of ~68 runs, **1 GO, ~27 MIXED, ~57 NO_EDGE**. Bond 0/14 GO; Forex best candidate PF 1.61/WR 56.7% but only n=30 (fails Tier-2 floor n≥100); Commodity candidates die on n=4–17.
- **Takeaway:** the literature/backtest research keeps producing *theoretically* plausible candidates that **fail the Tier-2 floor on sample size + cross-test** — not a research-coverage gap, a *durability* gap. Re-running won't change that until candidates get clean+intrabar+multi-month forward validation.
- **Gap/opportunity:** the orchestrator does **not** currently inject personas (`grep persona orchestrator.py` = none). Wiring the persona playbook into P2 candidate generation is a concrete enhancement.

## Useful personas (.MD)
`agent_personas/` is **empty** — the real content is here:

| File | What's useful |
|------|---------------|
| `hedge_fund_persona_playbook_v2.md` | 8 hedge-fund personas + **ideal trading style per asset class** (Equities: fundamental+momentum; ETF: tactical momentum+mean-reversion; Crypto: on-chain+narrative cycles; Commodities: macro-thematic+seasonal; Bonds: duration+rate-view). Maps cleanly to the academic sleeves (carry/TSMOM/residual-momentum). |
| `reports/persona_strategy_seed_candidates_2026-06-05.md` | Honest reality check: **no model×persona×class cell reaches n≥30**; the one apparent edge (grok3×reflexivity_trader×CRYPTO n=11 WR 72.7% PF 5.27) is a **single-15-day-window artifact**. Persona picks fail the bar too. |
| `reports/persona_strategy_seed_candidates` top models | grok3 (n=52, 67% WR, PF 2.91) + kimi_direct (n=50, 66%, 2.80) lead — but ~15-day window, no OOS; discovery-only. |
| `reports/new_persona_strategies_proposal_2026-06-05.md`, `reports/peer_claude-per-class-strategy-personas_2026-05-31.md`, `reports/persona-mix-portfolios` | Persona→strategy proposals + portfolio mixes per class. |
| `reports/mlflow_persona_edge_2026-06-04.md` | MLflow persona edge scan. |

## How personas map to the academic sleeves (the actionable link)
| Class | Persona ideal style | Academic sleeve to wire (post-resolver-fix) |
|-------|--------------------|----------------------------------------------|
| Equities | fundamental + momentum | residual momentum (Blitz) |
| Bonds | duration + rate-view | carry + roll-down (Koijen et al.) |
| Commodities | macro thematic + seasonal | term-structure / roll-yield (Gorton-Rouwenhorst) |
| Crypto/FX/all | trend | TSMOM vol-scaled (Moskowitz-Ooi-Pedersen) — already wired |

## Related
- [[reference/edge-rescue-roadmap]]
- [[strategies/strategy-catalog-clean-cohort]]
- [[sessions/2026-06-09-rescue-fixes-and-benefits]]
