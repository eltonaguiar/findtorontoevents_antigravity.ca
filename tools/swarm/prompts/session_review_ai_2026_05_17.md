# Session AI Review — 2026-05-17

## Context
Continuation of autonomous trading-edge improvement session. Follows Session AH (M-078 FOREX session gate fail-closed, M-079 VIX 4H retest archived, CT=F COT verified).

## Deliverables This Session

### 1. `tools/verify_realized_30d.py` (NEW)
Compares 30-day realized performance vs all-time dashboard numbers per asset class.
Surfaces survivorship bias warnings, dedup artifacts, and pre-gate noise.

Key findings from running the tool:
```
Class         All-time n  All-time PF  30d n  30d WR  30d PF  Warning
EQUITY               240         2.04     42   33.3%    0.67  ⚠ 30d dominated by pre-gate stocks_rsi2_pullback (blocked May 16)
COMMODITY            228         7.71    352   60.5%    2.29  ⚠ All-time PF inflated by COT dedup; 30d is more reliable
CRYPTO             6,833         1.43    183   51.4%    0.27  ⚠ SPA-failing ml_enhanced drag; SPA-passing subset healthy
FOREX                 98         2.23    888   25.2%    0.33  ⚠ 30d includes pre-gate picks; FOREX LONG hard-blocked May 14
ETF                   74         2.49      0   —         —    No 30d resolved picks
BOND                  12         0.66      1   0.0%     0.0   n too thin
```

### 2. Weekly Filter `reports/weekly_filter_2026-05-17T1337Z.md` (NEW)
Updated weekly filter with:
- 30d realized vs all-time divergence table (all 6 classes)
- COMMODITY survivorship bias warning (use 30d PF=2.29, not all-time 7.71)
- CRYPTO SPA-passing subset filter (FETUS/INJ/RENDER/STRKUSDT + cot_positioning)
- Kelly sizing: EQUITY 7.4%, COMMODITY 5.8%, CRYPTO 4.0%
- Pre-gate noise warnings for EQUITY and FOREX 30d metrics

### 3. FOOLPROOF Line 172 Updated
- Line 172 (Auto-commit A/B panel): now ✅ wired — `.github/workflows/ab_analysis.yml` runs daily at 05:30 UTC, auto-commits results
- Line 171 (COT feature_store): [~] blocked — CFTC pipeline needed

## Review Questions

1. **COMMODITY 30d n=352 > all-time n=228**: The closed_picks.json has 352 COMMODITY picks
   closed in the last 30 days, but the dashboard shows only 228 all-time. This means the
   dashboard deduplication is removing 124+ picks from the all-time count. Is this expected,
   or does it indicate that the dashboard generator is applying a different dedup window
   than the closed_picks.json file?

2. **EQUITY 30d WR=33.3% with pre-gate context**: `stocks_rsi2_pullback` was blocked on
   May 16 but 37 picks closed in the 30d window from that strategy. Current active picks
   still show 11 stocks_rsi2_pullback EQUITY picks in active_picks.json (from pre-gate
   admissions that haven't closed yet). Should a prune step be added to clear stale
   pre-gate active picks, or let them close naturally?

3. **CRYPTO SPA-passing subset isolation**: SPA test shows 5 ml_enhanced strategies pass
   (FETUS, INJ, RENDERUSDT, DYDXUSDT, STRKUSDT) but other ml_enhanced variants fail.
   The failing variants (ADAUSDT, DOGEUSDT, INJUSDT 15m, ALGOUSDT, APEUSDT, TRXUSDT)
   appear to still be active and generating picks. Should these failing SPA strategies
   be blocked in BLOCKED_ASSET_STRATEGY_PAIRS? (Requires explicit user approval per CLAUDE.md)

4. **FOREX all-time n=98 vs 30d n=888**: The dashboard shows 98 all-time FOREX picks,
   but 888 FOREX picks closed in the last 30 days. This extreme discrepancy suggests
   the dashboard all-time n applies heavy filtering (only post-gate SHORT picks pass),
   while closed_picks.json includes everything including pre-gate LONG picks. Is the
   dashboard n=98 trustworthy for the FOREX PF=2.23 stat?

5. **realized_n_30d tool gap**: The tool compares exit_date >= cutoff from raw closed_picks.
   A more accurate comparison would filter picks through passes_active_gate() before
   computing 30d stats. Should the tool add a "post-gate 30d" column for apples-to-apples
   comparison with the dashboard numbers?

## Output Format Required
Provide a JSON assessment:
- verdict: APPROVE, REQUEST_CHANGES, or NEEDS_DISCUSSION
- concerns: list of {severity, area, issue, recommendation}
- action_items: list of {priority, description, file, rationale}
- summary: one paragraph overall assessment
