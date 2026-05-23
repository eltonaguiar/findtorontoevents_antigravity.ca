You are a senior quant auditor for a multi-asset trading system. Review the following optimization proposals based on the data provided below. Do NOT access external files — base your analysis solely on what's in this prompt.

## SYSTEM STATE (from live dashboard_data.json, 2026-05-14)

| Asset Class | PF | Status | Share of Trades |
|------------|-----|--------|-----------------|
| CRYPTO | 1.34 | stable | 93% |
| EQUITY | 1.55 | stable | <3% |
| COMMODITY | 4.03 | stable | <2% |
| FOREX | 0.81 | stressed | <2% |
| ETF | 1.41 | stable | <1% |
| BOND | 0.66 | thin_sample | <1% |
| FUTURES | None | insufficient_data | <1% |

## ARCHITECTURE FINDINGS (verified from code)

1. **Crypto-centric boosting**: MTF multi-timeframe confirmation (+8 score) and Ensemble 2-of-3 signal confirmation (+5 score) are CRYPTO-ONLY in score_booster.py lines 1015-1119. Non-crypto gets zero signal confirmation boosting.

2. **COMMODITY PF=4.03 has zero boosters**: scored identically to FOREX (PF=0.81). Gets only the penalty mechanisms. No dedicated DXY correlation, COT alignment, or roll yield bonuses.

3. **No regime protection for non-crypto**: regime_router.py line 473 only filters `sym.endswith("USDT")`. FOREX, equity, commodity picks pass through unfiltered regardless of macro conditions.

4. **All non-crypto gets -5 auto-penalty on liquidity**: score_booster.py lines 989-1004 uses TOP50_SYMBOLS (Binance crypto-only list). Non-crypto symbols not matching get -3 to -5 penalty. Bypass condition only checks `asset_class == "CRYPTO"`.

5. **Scores not normalized per asset class**: Same formula for all classes. Elite score floors are admission floors not normalizers: CRYPTO=70, EQUITY=60, COMMODITY=65, FOREX=70, ETF=50, BOND=40.

6. **FOREX PF=0.81 only gets defensive mitigations**: wider SL (0.8%), raised elite floor to 70, -15 catastrophe penalty for WR<30%. No quality-improving filters.

7. **Non-crypto consensus requires >=2 strategies**: but forex has ~3, commodity has ~5, vs crypto's 20+. forex needs 67% agreement vs crypto's 10%.

8. **IC analysis exists but unwired**: tools/analyze_audit_scores_vs_pnl.py computes per-class Spearman correlations (crypto=0.11, non-crypto=0.33 from last run) but results never feed back to tune scoring weights.

## PROPOSED OPTIMIZATIONS

### P1: Wire IC Analysis into Pipeline Feedback Loop
Auto-tune boost/penalty weights based on per-asset-class Spearman correlations.

### P2: Build Non-Crypto Signal Confirmation Gates
EQUITY: VWAP + OBV + SPY sector. FOREX: DXY + session liquidity. COMMODITY: DXY inverse + COT. +5/+8 bonuses like crypto gets.

### P3: Add Regime Protection for Non-Crypto
FOREX: DXY trend + ADX chop. EQUITY: VIX levels + SPY 200-SMA. COMMODITY: DXY inverse + COT positioning.

### P4: Normalize Scores Per Asset Class
Within-class z-score normalization. COMMODITY raw 55 would show normalized 80+.

### P6: Fix Liquidity Penalty for Non-Crypto (Quick Win)
Bypass -5 penalty for non-CRYTPO classes. 30 min work.

### P7: Differentiate Consensus Voting Minimums
Lower forex to 1 (only 3 strats), ETF/BOND to 1.

### P8: COMMODITY Signal Boosters
DXY correlation +8, COT alignment +6, roll yield +4.

### Q2: Lower COMMODITY Elite Floor 65→55
Higher PF justifies lower admission threshold.

## YOUR TASK

Return ONLY valid JSON:

```json
{
  "validation": {
    "agree": ["finding1", "finding2"],
    "disagree": [{"finding": "findingX", "reason": "why"}],
    "data_speculation": [{"proposal": "P3", "concern": "what's untestable without data"}]
  },
  "prioritization": {
    "do_first": ["P6", "Q2"],
    "do_later": ["P2", "P3"],
    "skip_or_rethink": [{"item": "P4", "reason": "why"}],
    "dependency_order": "which must precede which"
  },
  "risks": [
    {"item": "P3", "risk": "what could go wrong", "severity": "high|medium|low"}
  ],
  "alternative_approaches": [
    {"for": "P3", "alternative": "simpler approach"}
  ],
  "expected_impact": {
    "p6_commodity_lift_pct": "estimated improvement",
    "overall": "concise assessment"
  },
  "overall_verdict": "one sentence: are these on the right track?"
}
```

Base everything on the SYSTEM STATE table and ARCHITECTURE FINDINGS above. Do NOT fabricate data not provided.
