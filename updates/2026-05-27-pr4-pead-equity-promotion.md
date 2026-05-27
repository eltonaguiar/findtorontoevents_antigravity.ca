# PR4: Promote PEAD Equity Strategy from Shadow to Production

**Date:** 2026-05-27
**Branch:** `fix/pr4-pead-equity-promotion`
**Severity:** P0 (PEAD equity stuck in shadow) + P1 (US Equity screener emits zero picks)

## Problem

The PEAD (Post-Earnings Announcement Drift) equity strategy is the **only WF-VERIFIED equity strategy** with 62.2% OOS win rate on a 2-day window, but it's stuck in shadow mode:

- `EQUITY_PEAD_ENABLED=0` (default OFF) — never emits picks
- Not in `NON_CRYPTO_STRATEGY_POLICY` allowlist — even if enabled, would be blocked
- The broken `earnings_drift` strategy (0% WR on 92 picks) was active in prod while PEAD was dormant
- EQUITY class needs strategy diversity to move from PF 1.55 toward T2 (PF 2.0+)

Academic basis: Ball & Brown (1968), Bernard & Thomas (1989), Livnat & Mendenhall (2006). Stocks systematically drift in the direction of earnings surprises for 30-60 days.

## Changes

### File: `alpha_engine/equity_pead_strategy.py`
- **Default changed:** `EQUITY_PEAD_ENABLED` from `"0"` to `"1"` (ON by default)
- Strategy emits BUY signals 1-3 days after ≥5% positive earnings surprise
- 30-day hold, 6% TP, 3% SL (2:1 R:R), confidence 0.60-0.75

### File: `alpha_engine/non_crypto_policy.py`
- **Added `equity_pead`** to `NON_CRYPTO_STRATEGY_POLICY`:
  - Categories: `{"equity"}`
  - `min_confidence: 0.58`, `min_rr: 1.50`, `min_elite_score: 50`
  - `allow_without_forward: True` (probation — build forward record)

## Impact Analysis

### Expected Improvement
- **EQUITY strategy coverage:** Adds the first WF-verified equity strategy to production
- **EQUITY PF:** Expected to contribute toward lifting EQUITY from PF 1.55 to PF 1.80+
- **Signal quality:** PEAD is one of the most well-documented anomalies in academic finance (50+ years of evidence)
- **Confidence calibration:** PEAD confidence range (0.60-0.75) aligns with the EQUITY sweet spot (0.55-0.70 per calibration data)

### Risk Assessment
- **Data dependency:** Uses yfinance `get_earnings_dates()` — may be delayed or incomplete for some symbols. Fail-open on all fetch errors.
- **Universe limitation:** Currently covers 45 large-cap US stocks. Smaller caps may have stronger PEAD but lower liquidity.
- **Hold period risk:** 30-day hold is long for a single earnings catalyst. Regime changes during hold could invalidate the thesis.
- **Forward record:** Zero forward trades — needs 5+ trades with 50% WR before graduating from probation.

### Peer Review Notes
- **Ring-2.6-1T:** "Promote pead_equity from shadow → probation. Only WF-VERIFIED equity strategy." ✅ Implemented.
- **AQR R3 (supreme plan):** "PEAD edge is real, not yet shipped." ✅ Now shipped.
- **Incident P1:** "US Equity screener emits zero picks." This partially addresses it — PEAD will emit when earnings events are detected.

## Verification

After merge:
1. Set `EQUITY_PEAD_ENABLED=1` (default now) and run `python -m alpha_engine.equity_pead_strategy`
2. Check `active_picks.json` for `equity_pead` strategy entries within next earnings cycle
3. Monitor `/audit/` EQUITY tab — should show PEAD picks alongside existing strategies
4. Track forward WR after 5+ trades — must hit ≥50% to graduate from probation

## Dependencies
- Requires `yfinance` (already installed in CI)
- Compatible with existing `non_crypto_policy` gates
- Does NOT require changes to `production_scanner.py` — PEAD emits to `active_picks.json` via the standard merge path
