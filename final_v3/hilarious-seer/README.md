# hilarious-seer Final v3 Deliverable — 2026-11-14

**Worktree:** hilarious-seer
**Agent:** ML algorithms audit asset classes stale data fixes
**Date:** 2026-11-14
**Commit target:** origin/main

---

## What This Folder Contains

This is the **final stage v3** consolidated deliverable. It builds on final_v2 by adding:

1. **Peer adjudication summary** — 6 formal disputes that were resolved during the 2026-11-14 audit cycle (VWAP rejected, ITERATION-005 downgraded, ML flip cautioned, etc.)
2. **Master todo list** — 47 actionable tasks across general fixes, GHA fixes, asset-class fixes, backtests, and ML improvements
3. **SubQ comparison matrix** — 12 strategy candidates scored across 7 dimensions with coverage analysis
4. **Focus decision** — Slot 1 (CRYPTO trend) + Slot 2 (EQUITY RSI(2)) with 90-day success criteria
5. **Mutual funds vs ETFs analysis** — Why ETFs are strictly superior for low-capital, low-fee exposure

This complements (does not duplicate) childlike-airport's excellent `final_v3/00_common_themes/BUGS.md` and `final_v3/03_focus/DECISION.md`.

---

## Folder Structure

```
final_v3/hilarious-seer/
├── 01-common-themes/
│   └── peer_adjudication_summary.md     # 6 adjudicated disputes with binding resolutions
├── 02-improvement-plan/
│   └── todo_master_list.md              # 47 actionable tasks, dependency graph, 90-day sprint
├── 03-subq-comparison/
│   └── strategy_candidate_matrix.md     # 12 candidates × 7 dimensions, tiered recommendations
├── 04-focus-decision/
│   └── hilarious_seer_focus.md          # Slot 1: CRYPTO trend; Slot 2: EQUITY RSI(2); 90-day criteria
└── 05-implementation-todos/
    └── mutual_funds_and_etfs.md         # Why ETFs > MFs; low-fee ETF subset; screening criteria
```

---

## Key Decisions

### Adjudications (Binding)
| # | Dispute | Verdict |
|---|---------|---------|
| 1 | VWAP Sharpe 3.76 deployable? | **REJECTED** — fatal annualization error |
| 2 | ITERATION-005 PROVEN? | **DOWNGRADED** — best candidate, not proven |
| 3 | ML confidence flip without retrain? | **CAUTION** — retrain required first |
| 4 | flaxen-hair CRYPTO production_ready? | **VETOED** — internal contradiction |
| 5 | finpredict-v4 destructive SQL fixes? | **VETOED** — dry-run only |
| 6 | CRYPTO stop fill slippage | **FIXED TODAY** — gap-aware fill deployed |

### Focus (90 Days)
| Slot | Class | Strategy | First Gate |
|------|-------|----------|------------|
| 1 | CRYPTO | Vol-targeted trend | Forward PF > 1.3, WR > 55%, n ≥ 100 |
| 2 | EQUITY | RSI(2) on SPY/QQQ | OOS Sharpe ≥ SPY, PF ≥ 1.15, 90 days |
| Diversifier | ETF | Multi-asset trend | Build after Slot 1 proven |

### Mutual Funds
- **NOT_BUILT** — structurally incompatible with intraday pick trading
- **Use ETFs instead** — VTI (0.03%), VXUS (0.08%), BND (0.03%) for low-cost beta

---

## Critical Path (9 Weeks to First Forward Result)

```
Week 1:  A1 (PnL units) + A2 (price freshness) + B1 (alpha engine CI)
Week 2:  A3 (zombie drain) + A4 (store reconciliation) + B3 (freshness guardian)
Week 3:  A5 (exit taxonomy) + B2 (horness harness gate) + B4 (PnL sanity CI)
Week 4:  C1/C2 (CRYPTO fill fix + kill SWING) + D1 (replay simulation)
Week 5+: C3 (CRYPTO POSITION forward test) + D2 (benchmark restatement)
Week 9:  Review forward data; decision: scale or wind down
```

---

## Files in This Bundle

All files are original synthesis by hilarious-seer, based on read-only review of peer work and subagent research. No peer files were copied.

---

## Next Actions (For User)

1. **Approve Phase 0 scope** — PnL unit fix + price freshness + zombie drain (3 weeks, 50% of resources)
2. **Approve Slot 1 (CRYPTO)** — allocate 30% of resources to ITERATION-005 forward test
3. **Approve Slot 2 (EQUITY)** — allocate 15% of resources to H10 clean forward OOS
4. **Do NOT approve:** VWAP deployment, MF pick class, FUTURES unblock, destructive SQL fixes
5. **Schedule weekly StrategyCertifier runs** — automated gate checking on rolling 90-day windows
