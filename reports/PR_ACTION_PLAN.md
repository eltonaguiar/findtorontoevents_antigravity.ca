docs(plan): PR action plan + integration & testing plan with timeline

## Contents
- `PR_ACTION_PLAN.md`: Merge queue for 14 open PRs + 5 new PRs to create
- `INTEGRATION_TESTING_PLAN.md`: 14-day phased rollout with testing gates

## PR Categories

### MERGE Queue (rebase needed)
- #669 B2 coverage lane grid
- #676 Data quality follow-up

### REQUEST_CHANGES (needs author work)
- #665 B17 HC after-cost (walkforward regression #696)
- #644 per-asset gate plan (scope dishonesty, n=3 thresholds)
- #615 5 scanner blockers (10 test failures)
- #597 P0 fixes + USDCHF (4 workstreams bundled)

### HOLD (fabricated stats or DO-NOT-MERGE)
- #660, #658, #681, #661

## New PRs To Create
1. PR-A: Unified gate framework (this PR #699)
2. PR-B: Strategy health monitor
3. PR-C: `run_audit.py` script (included in #699)
4. PR-D: non_crypto_consensus investigation
5. PR-E: Penny stock / meme coin integration

## Timeline
- Phase 0 (Days 0-2): Config + audit script CI integration
- Phase 1 (Days 3-7): Health monitor + investigation
- Phase 2 (Days 8-14): Volume cap enforcement + mutation review
- Phase 3 (Days 15-30): Penny/meme + optimization

## 14-Day Targets
| Asset | Current 7d | Day 14 Target |
|-------|-----------|---------------|
| CRYPTO | PF 1.33, WR 45% | PF 1.5+, WR 50%+ |
| EQUITY | PF 1.07, WR 49% | PF 1.3+, WR 50%+ |
| FOREX | PF 0.43, WR 17% | PF 0.8+, WR 35%+ |
| ETF | PF 1.57, WR 63% | PF 2.0+, WR 65%+ |
| COMMODITY | PF 1.18, WR 20% | PF 1.2+, WR 35%+ |

---
*Cross-AI verified: Kimi K2 + Claude Opus 4.7 + Grok-4*