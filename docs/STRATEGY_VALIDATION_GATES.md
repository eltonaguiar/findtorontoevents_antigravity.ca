# MANDATORY STRATEGY VALIDATION GATES
## Synthesis from 20+ caught fabrications — 2026-05-31
## Source: claude-opus-4-7-desktop terminal close

### Hard demands (MUST pass before any strategy goes live)

1. **n >= 500 closed trades** (Wilson LB 95% lower-bound on WR must clear 0.50)
2. **Bootstrap PF 95% lower-bound > 1.2** (10K resamples, not 100; permutation p < 0.05)
3. **Bonferroni-corrected p < 0.0071** (α=0.05 / 7 gates)
4. **Top-3 trade concentration < 50%** of total positive PnL
5. **Top-strategy + top-source share each < 60%** (HHI < 0.30)

### Required testing protocol

- **Intrabar OHLC replay** for SL/TP — NEVER cap closed pnl_pct to [SL, TP] range
- **Include TIME_EXIT trades** in win-rate denominator (pnl_pct > 0 = win)
- **Walk-forward by class**: 12mo train rolled forward 1mo, validate next 1mo, aggregate
- **DSR > 0.95** (Lopez de Prado), **PBO < 0.05**
- **Independent verification** by 2nd agent before promotion

### Caveats — every one cost us a fabrication today

| Caveat | What happened |
|--------|---------------|
| Don't filter to TP_HIT-only | Suppresses WR to 3-17%; money_ready uses pnl>0 |
| Don't winsorize raw pnl | "FOREX SHORT PF 3.43" became 1.087 when intrabar-replayed |
| Don't trust raw vs policy-clean divergence | EQUITY raw PF 3.41 vs money_ready 0.16 — cohort cascade |
| Don't claim edge from n < 100 | EQUITY n=39 WR 59% — Wilson LB 0.4344 = noise |
| Don't conflate arithmetic sum with compound | mega_mutation +318% is sum(pnl_pct), not portfolio growth |
| Don't promote single-symbol "winners" | ml_enhanced_DYDXUSDT collapsed 94%→63.5% when n grew 34→63 |
| Don't ignore permutation p-value | perm p=1.000 is NOT "PROMISING" regardless of WR/PF |
| Don't compare WRs across different win-definitions | Pin canonical definition BEFORE multi-pool harness |
| **Check verdict aggregation bugs** | ETF was "n=4 INSUFF" but edge_stability shows n=153 PF 1.44 (PR #351) |
| **Check tag misclassification** | 4 BOND strategies tagged 'CRYPTO' hid DSR 1.82 / Sharpe 4.43 (PR #346) |

### One-line broadcast

Apply n≥500 + Wilson LB + Bootstrap PF + Bonferroni + concentration check + intrabar replay (not capping) + include TIME_EXIT + independent SQL verify. Reject your own positive results until 2nd agent reproduces them. If your permutation p > 0.05, do NOT call it "PROMISING" regardless of WR/PF. Check verdict aggregation bugs (PR #351) and tag misclassification (PR #346) before declaring no-edge — the edge may already exist and be hidden.

### Hidden edges discovered TODAY

1. **ETF**: n=153, PF=1.44 — closest T2 candidate, hidden by aggregation bug (PR #351)
2. **BOND**: 4 strategies wrongly tagged 'CRYPTO' — bond_yield_curve DSR=1.82, Sharpe=4.43 (PR #346)
