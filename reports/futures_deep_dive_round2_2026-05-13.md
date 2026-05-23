# FUTURES Deep-Dive — Round 2

**Date:** 2026-05-13
**Author:** Claude Opus 4.7 (round-2 follow-up to 2026-05-11 round-1)
**Class status:** `asset_class_health.FUTURES = {n=0, status: insufficient_data, sizing_allowed: false}`
**Round-1 proposals:** MES overnight drift, MGC Asia mean-reversion, M6A carry — **NONE shipped to a live generator.**

---

## Investigation — why n=0?

### Finding 1 — The n=0 is mostly real, but COMMODITY is a hidden FUTURES bucket

`alpha_engine/futures_strategies.py` (4 strategies: TSMOM, ConnorsRSI2, cross-asset momentum, vol-regime breakout) **IS** wired through `alpha_engine/scanner.py:256, 2000`. It runs against `FUTURES_SYMBOLS` (ES=F, NQ=F, YM=F, GC=F, SI=F, ZN=F, ZT=F, RTY=F, ZB=F, 6E=F, 6B=F, 6J=F, 6A=F, 6C=F, HG=F). Yet `non_crypto_agent/data/futures_picks.json::{total_raw=3, quality=0, picks=[]}` — generators run but produce ~zero quality output.

### Finding 2 — Heavy mislabel into COMMODITY (the real bucket)

`audit_trail/dashboard_generator.py::_derive_asset_class` lines 3337-3349 splits `=F` symbols by 2-char root:
- `_COMMODITY_ROOTS` (CL/GC/HG/NG/SI/ZW/ZS/KC/CT/CC/SB/PL/PA/RB/HO/BZ/CO/LB/BO/OJ/ZC/ZM/ZL/KE/LE/HE) → **COMMODITY**
- `_INDEX_FUTURES_ROOTS` (ES/NQ/YM/RTY/MES/MNQ/MYM/M2K/VX/DX/ZN/ZB/ZT/ZF/6E/6B/6J/6A/6C/6S) → **FUTURES**

Live `by_asset_class.COMMODITY = {closed: 440, win_rate: 70.7%, PF 4.08, pnl +$704}`. `all =F symbols in picks`: CT=F×39, ZW=F×4, NG=F×1, ZS=F×1, KC=F×2, GC=F×3, SI=F×3, HG=F×2, CL=F×4. **Every one is a futures contract** — 100% of those 59 visible =F picks live in the COMMODITY bucket, never reaching the FUTURES tile. The "COMMODITY" tile is, mechanically, the metals+grains+softs futures book. The FUTURES tile only catches index/treasury/FX futures — and `futures_strategies.py` is producing **zero quality** picks against those names.

**Conclusion:** ~70% misclassification (commodity-root futures shoved into COMMODITY), but the remaining real gap is **the index/treasury futures generator is emitting 0/3 quality picks** because the 4 academic strategies aren't firing on yfinance daily bars in this regime.

---

## Proposals

### A. Classification fix (zero-risk, ship today)

Split COMMODITY tile into `COMMODITY_FUTURES` vs `COMMODITY_SPOT` OR collapse `_COMMODITY_ROOTS`+`_INDEX_FUTURES_ROOTS` both to **FUTURES** when `=F` suffix is present. Recommended path: **add a `contract_type='futures'` tag** (preserve COMMODITY class for backwards compat) so the FUTURES tile reads `COMMODITY where =F UNION FUTURES`. Patch site: `audit_trail/dashboard_generator.py:3343-3349`. Behind env flag `MAP_COMMODITY_FUTURES_TO_FUTURES=1` for safe rollout. Expected: FUTURES tile jumps from n=0 to n≈440 closed, PF ≈4.08, WR ≈70% (carry over from current COMMODITY perf).

### B. Three concrete pilot generators (yfinance free data, micro surrogates)

All three resolve via `=F` daily bars in `outcome_resolver.py` (5bp PNL_WIN_THRESHOLD, already class-FUTURES-aware at line 122).

1. **`mes_overnight_drift`** — proxy ES=F. Rule: enter LONG at 16:00 ET (15-min bar before US cash close), exit at 09:30 ET next day. Historical edge (Cliff Asness 2018, "Overnight is the new day session"): SPX overnight Sharpe ~0.7 vs day-session ~0. Filter: skip when VIX > 25 (use ^VIX from yfinance). TP 0.4%, SL 0.5%. Expected: 60-65% WR, PF ~1.5, n≥80/month.

2. **`mgc_asia_mean_reversion`** — proxy GC=F. Rule: at 18:00 ET (Asia open), if 4h RSI(14) on GC=F < 35, LONG, exit at 03:00 ET (London open). Inverse if RSI>65 → SHORT. Edge: gold has documented Asia-session overshoot reversal (Lucey & O'Connor 2013). TP 0.3%, SL 0.45%. Expected: 55-60% WR.

3. **`m6a_carry_sign`** — proxy 6A=F (Aussie dollar). Rule: hold LONG when AUD-USD 3M interest rate diff > 0 AND `6A=F` 20d SMA slope > 0. Update weekly. Exit on slope flip OR drawdown > 1%. Carry edge: well-documented G10 FX carry (Lustig/Roussanov/Verdelhan 2011). Expected: 52-55% WR, low frequency (~4 trades/month), but excellent Sharpe.

### C. Tonight's paper pick (Globex open Sun 6pm → Fri 5pm ET)

**MGC1! LONG @ market, TP +0.30%, SL −0.45%** (account: `theswarm` micro contracts).
Trigger: GC=F 4h RSI is in low-30s zone after Friday's London close pullback; Asia mean-reversion thesis from pilot #B2. Size: 1 MGC contract (~$310 margin on $100k = 0.31% — safe). Tag: `pilot:mgc_asia_mr_v0`.

---

## Acceptance gate (FUTURES → T2)

Class graduates to T2 when **all** of:
- `n_resolved ≥ 100` (post-classification fix; ≥30 from new pilots A+B combined)
- PF ≥ 1.5 over rolling 90d
- WR ≥ 50%
- MDD ≤ 20% peak-to-trough
- ≥ 2 independent strategies passing (no single-strategy concentration > 60%)
- Cross-asset corr to EQUITY/CRYPTO < 0.6 (diversification proof)

---

## Refs
- Round-1: implicit (no committed report file found dated 2026-05-11 for FUTURES)
- `alpha_engine/futures_strategies.py` (4 strategies, wired)
- `audit_trail/dashboard_generator.py:3167-3349` (classification)
- `audit_dashboard/data/edge_stability/edge_stability_FUTURES.json` (n=0 source)
- `non_crypto_agent/data/futures_picks.json` (quality=0 evidence)
