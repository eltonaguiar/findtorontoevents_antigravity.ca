# Fix: VIX+YC Bonus Default + Test Parity Drift (2026-05-16)

## What Was Broken

1. **VIX+YC bonus undersized**: The synthesis report `daily_ideas_synthesis_2026-05-16.md` called for a +15 score bonus when VIX<22 + YC>0 (OOS WR=76.6%), but `audit_trail/quality_gates.py` defaulted to +12.

2. **Test parity drift — ETF floor**: `tests/test_quality_gates.py::test_smart_picks_score_floors_snapshot` expected ETF floor=40, but production `alpha_engine/config.py` lowered it to 35 on 2026-05-14. The snapshot test had not been updated.

3. **Test parity drift — AAPL un-ban**: `tests/test_hedge_fund_quality_gate.py` still asserted AAPL rejection, but `alpha_engine/hedge_fund_quality_gate.py` un-banned AAPL on 2026-05-16 (n=17, PF=1.03, fwd_wr=73.0% — above 30-pick charter floor). This caused 3 cascading test failures:
   - `test_aapl_rejected`
   - `test_stocks_alias_maps_to_equity` (used AAPL as proxy for EQUITY rejection)
   - `test_batch_evaluate_counts` (counted AAPL as rejected)

## What Changed

| File | Change | Lines |
|---|---|---|
| `audit_trail/quality_gates.py` | `VIX_YC_SCORE_BONUS_SIZE` default `12` → `15` | ~3834 |
| `tests/test_quality_gates.py` | ETF expected floor `40` → `35` | ~1259 |
| `tests/test_hedge_fund_quality_gate.py` | `test_aapl_rejected` → `test_aapl_passes` with justification comment | ~58 |
| `tests/test_hedge_fund_quality_gate.py` | `test_stocks_alias_maps_to_equity` uses CVX+conf=0.62 reject band instead of AAPL | ~238 |
| `tests/test_hedge_fund_quality_gate.py` | `test_batch_evaluate_counts` updated counts (2 kept / 2 rejected) | ~261 |

## Verification

- `python -m py_compile audit_trail/quality_gates.py` → OK
- `python -m py_compile alpha_engine/config.py` → OK
- `python -m pytest tests/test_quality_gates.py tests/test_hedge_fund_quality_gate.py -v` → **236 passed, 0 failed**
- `python -m pytest tests/ -k "vix_yc_combined_gate or crypto_high_conf_guard" -v` → **15 passed, 0 failed**

## Related

- `reports/daily_ideas_synthesis_2026-05-16.md` §2.6 (VIX+YC +15 bonus)
- `alpha_engine/hedge_fund_quality_gate.py` lines 59-61 (AAPL un-ban rationale)
- `alpha_engine/config.py` lines 249-250 (ETF floor 35)
