# Session Review Round 4 — 2026-05-17 Final Check

## What was shipped this goal-loop

| Item | Status |
|------|--------|
| CI fix: EMITTER_DEDUP=0 in TestArchiveDedupGuard | ✅ DONE |
| M-045 EQUITY VIX filter gate (shadow OFF default) | ✅ DONE |
| quan_engine investigation doc (pre-block protocol) | ✅ DONE |
| Weekly real-money filter report + Kelly sizing | ✅ DONE |
| EQUITY T2 confirmed: PF=1.65, WR=53.2%, n=393 | ✅ CONFIRMED |

## Current gate inventory (full)

Gates ON (blocking):
- FOREX_HARD_DISABLE=1 (class PF=0.85, FOREX disabled)
- M-041 SWARM_TIER_GATE=1 (single-tier swarm picks blocked)
- M-042 COMMODITY_SHORT_ONLY=1 (LONG commodity blocked)
- M-043 BOND_MIN_N_GATE=1 (BOND n=11 < 20 floor)
- ETF_TIGHT_GATE=1 (score floor 60 for ETF)
- VIX_YC_SCORE_BONUS_ENABLED=1 (+15 EQUITY bonus in favorable VIX regime)

Gates OFF (shadow):
- M-038 NUPL_GATE_ENFORCE=0 (30d shadow until 2026-06-16)
- M-039 EXCHANGE_DIVERGENCE_GATE=0 (needs multi-exchange feed)
- M-040 OBI_GATE_ENFORCE=0 (needs 12-sample warm-up)
- M-044 CRYPTO_MIN_TRADE_AGE=0 (skeleton only)
- M-045 EQUITY_VIX_FILTER=0 (shadow, enable when VIX>25)
- ETF_MACRO_VETO=0 (enable at n>=150)
- PCG5_ENFORCE=0 (shadow mode, log only)

## Dashboard performance (2026-05-17, fresh)

- EQUITY: n=393, WR=53.2%, PF=1.65 — T2 CERTIFIED
- ETF: n=75, WR=66.7%, PF=2.25 — T1 performance, paper-only
- COMMODITY: n=228, PF=7.71 (dashboard inflated), verified SHORT PF=2.10
- CRYPTO: n=7563, WR=47%, PF=1.32 — quan_engine (18%/PF=0.70) is drag
- BOND: n=11, blocked by M-043
- FOREX: disabled

## Review questions

1. Is there any critical gate interaction or configuration that could cause unintended silent blocking in production?
2. Given EQUITY T2 is confirmed (PF=1.65), what's the single most impactful next step to push toward T1 (PF>2)?
3. The ETF class has T1 performance (PF=2.25/WR=66.7%) at n=75. Should ETF_TIGHT_GATE=1 remain ON even at n<100?
4. FOREX WR=57.8% but PF=0.85 — is this a systematic TP/SL miscalibration? What would fix it?
5. Any gaps or risks in the weekly_filter_2026-05-17.md document that would mislead a user applying these filters?

## Constraints
- Never block strategies without mutation analysis
- Never add to BLOCKED_ASSET_STRATEGY_PAIRS without user approval
- Gates must be fail-open, env-var gated
