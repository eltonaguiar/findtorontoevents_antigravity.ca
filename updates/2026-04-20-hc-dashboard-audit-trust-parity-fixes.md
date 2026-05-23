# HC Dashboard Audit — Trust Parity, Config Completeness, UX Fixes

**Date:** 2026-04-20  
**Branch:** `fix/audit-scoring-optimizations` (local fixes staged)  
**Plan:** `C:\Users\zerou\.cursor\plans\audit_hc_dashboard_pr_8438e4b1.plan.md`

## What Was Broken

1. **Trust threshold copy vs enforcement (HIGH)**  
   `template.html` `hcEdgeManifest()` and `passesValidatedEdgePerClass()` hardcoded `trust >= 3` for CRYPTO/EQUITY, but the actual shared gates in `hc_filter.js` enforce `trustScoreMinCrypto: 6` / `trustScoreMinOther: 5`. Users read "Trust ≥ 3" but picks with trust 3–5 were silently rejected.

2. **Config file incomplete (MEDIUM)**  
   `config/hc_gate_params.json` was missing per-asset FWD WR and score floors for COMMODITY, FUTURES, BOND, and ETF. Operators editing JSON alone could not tune these classes.

3. **Python/JS signal-group parity (MEDIUM)**  
   `dashboard_hc_rules.py` still listed retired `ai_challenge_antigravity`, `ai_challenge_grok`, `ai_challenge_mercury` entries that `hc_filter.js` removed on 2026-04-18.

4. **Score bucket naming confusion (MEDIUM)**  
   `_cryptoScoreBucket()` labeled score thresholds as "S-Tier", "A-Tier", etc. — conflating `p.score` bands with stamped HF conviction tiers.

5. **PF explosion on zero losses (LOW)**  
   Profit factor displayed as `∞` (coded as 999) when a small slice had no losses.

6. **Non-crypto aggregate ignored Recent-N (MEDIUM)**  
   Per-category cards respected `_PERF_RECENT_N`, but the top aggregate header always used full history.

## What Was Changed

| File | Change |
|------|--------|
| `audit_dashboard/template.html` | `hcEdgeManifest()` now reads trust floors from `getHcGateParams()`; `passesValidatedEdgePerClass()` uses dynamic `trustFloor`; renamed score buckets to "Score band X"; capped PF at 99.9 with "n/a (no losses)" display; aggregate header now applies `_PERF_RECENT_N` |
| `config/hc_gate_params.json` | Added `forwardWRMinPct{Commodity,Futures,Bond,ETF}`, `scoreFloor{Commodity,Futures,Bond,ETF}`, `forexRelaxedWRMinPct` |
| `tools/dashboard_hc_rules.py` | Synced `ai_challenge` signal group with JS (retired old LLM tournament entries) |
| `tools/audit_pick_schema.py` | **New** — schema null checks, score distribution, fwd-WR scale audit |
| `tools/hc_rolling_impact.py` | **New** — last-N baseline vs HC comparison per asset class + 70/30 blend |
| `docs/reports/hc_audit_2026-04-20.md` | **New** — comprehensive audit report |
| `docs/MERCURY2_HC_VALIDATION_PIPELINE.md` | Added `audit_pick_schema.py` and `hc_rolling_impact.py` to command list |

## How It Was Verified

- `python tools/validate_dashboard_parity.py` — parity check passes (no new disagreements introduced)
- `python tools/backtest_hc_filter.py` — backtest numbers unchanged (expected, since logic was UX/copy fixes + config expansion, not gate relaxation)
- `python tools/audit_pick_schema.py` — confirmed 15.8% of active picks lack `strat_fwd_wr`
- `python tools/hc_rolling_impact.py` — confirmed recent crypto (last 10 WR 90%) produces 0 HC passes

## Key Data Finding

Recent crypto picks have **90% WR (last 10)** but **0 pass HC gates**. This is likely because:
- 15.8% of active picks lack `strat_fwd_wr` (hard-blocked by forward-trades gate)
- `scoreFloorCrypto: 55` may be overfit to older regimes (train/test gap 71% → 32% WR)

Recommendation: backfill `strat_fwd_wr` from strategy history and consider lowering crypto score floor temporarily.
