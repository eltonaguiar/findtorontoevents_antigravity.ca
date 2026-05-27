# EAGLE: End-to-End Strategy Review — All Asset Classes
**Date:** 2026-05-27 02:26 EST | **Model:** Claude Opus 4.7 (via CommandCode)
**Branch:** `feat/EAGLE-2026-05-27-end-to-end-review`
**Sources:** 9 asset class 90-day plans (2026-05-15), master action plan, institutional readiness plan, live dashboard_data.json, safety gates (quality_gates.py ~10,500 lines), roadmap, DAILY_IDEAS.MD, incidents/enhancements DB schema

---

## Executive Summary

**Reviewed 9 asset classes end-to-end from symbol universe → scanners → strategies → scoring → quality gates → safety gates → resolver → dashboard.** Here's the honest state:

| Class | n | PF | WR | sizing | Real Tier |
|---|---|---|---|---|---|
| CRYPTO | 8,011 | 1.36 | 46.7% | True | Sub-T2 — shrunk to liquid core could reach T2 |
| EQUITY | 420 | 1.57 | 51.9% | True | **T2-candidate** — nearest to institutional ready |
| COMMODITY | 322 | 2.49 | 61.5% | True | **FALSIFIED** — COT over-emission inflates; real post-dedup n≈5 PF≈0.17 |
| ETF | 106 | 1.48 | 58.5% | True | Viable — backtest 3.22 PF with VIX gate unwired |
| FOREX | 342 | 0.81 | 52.3% | False | HARD_DISABLE active; SHORT-only sleeve PF8.11 on n=29 |
| BOND | 11 | 0.66 | 54.5% | False | Statistically meaningless; 3 academic pilots unwired |
| FUTURES | 0 | null | 0% | False | Dead tile (70% activity misrouted to COMMODITY) |
| PENNY | 148 | 0.19 | 6.8% | False | Catastrophic — PERMANENTLY QUARANTINED |
| MEME | 1,869 | 0.50 | 15.7% | False | Catastrophic — PERMANENTLY QUARANTINED |

**Verdict:** No class is institutional-ready today. EQUITY is closest (PF 1.57 on liquid momentum, VIX<22 backtest PF 5.37 awaiting wire-up). COMMODITY's headline PF 2.49 is a data artifact. CRYPTO is volume-king but quality-poor. ETF has the clearest path (backtest 3.22 PF awaiting wire-up). FOREX, BOND, FUTURES, PENNY/MEME should stay disabled/quarantined until proven otherwise.

---

## 1. CRYPTO — Sub-T2 (PF 1.36 / WR 46.7% / n=8,011)

**Universe (179 symbols from production):** 2 majors (BTC/ETH), ~20 L1, ~12 DeFi, 9 memes, 6 AI, 5 gaming, 3 L2, various others. Dynamic via top_gainer_capture + smart_picks_engine. **NO runtime ADV/liquidity gate.**

**Source performance (from recent_closed n=2,891):**
| Source | n | Share | PF | WR | Verdict |
|---|---|---|---|---|---|
| luxalgo_filters | 678 | 23% | 1.07 | 45.1% | DILUTER — tighten to BTC/ETH only |
| alpha_engine | 335 | 12% | 0.99 | 42.7% | DILUTER |
| quan_engine | 305 | 10.5% | 1.36 | 35.4% | DILUTER — low WR |
| copy_trader_highscore | 99 | 3.4% | 0.80 | 30.3% | DELETE |
| battleground | 63 | 2.2% | 0.65 | — | QUARANTINE |
| mega_mutation | 87 | 3% | 2.29 | — | PROMOTE |
| dna_winner_picks | 103 | 3.6% | 1.88 | — | PROMOTE |

**5+ sources contribute ~40%+ volume at PF<1.1 or WR<40%.** On-chain data (Glassnode MVRV-Z) exists but CRYPTO_ONCHAIN_MOMENTUM_ENABLED=0 in prod.

**Confidence band analysis:** conf 0.85-0.90: WR=82% ✅ | conf >0.90: WR=14% (correctly blocked) ✅ | conf 0.65-0.75: WR=26.2% dead zone (shadow) ⚠️

**Verdict:** Shrink to 25 liquid + source whitelist + wire on-chain. Safety gates are good. Gap: mediocre sources (luxalgo/alpha_engine/quan_engine) slip through at high volume.

---

## 2. EQUITY — T2-Candidate (PF 1.57 / WR 51.9% / n=420)

**Universe (18 tickers):** 10 large-cap, 2 ETFs, 6 penny, 2 meme. **8/18 are speculative drag.** Research backtests use 30 clean LC (PF 2.82 baseline). With VIX<22: PF 5.37/WR 75%/MDD 7.3% — Tier-1! Branch `feat/equity-vix-regime-gate-sidecar-2026-05-13` exists but UNMERGED.

**Verdict:** Most promising class. Universe split + VIX sidecar merge + expand to 20-25 LC.

---

## 3. COMMODITY — FALSIFIED

COT over-emission: 101 "trades" from only 5 weekly COT releases. Consolidated 1-per-cycle: n=5, WR 40%, PF 0.17, PnL -$52. Dashboard STILL shows PF 2.49. 73% PnL mass on single CT=F. Carry-momo double-sort (Miffre 2010, 18 symbols) fully coded but unwired.

**Verdict:** P0 dedup re-aggregation + wire carry-momo sidecar.

---

## 4. ETF — Viable (PF 1.48 / WR 58.5% / n=106)

11-Sector rotation + VIX<25: backtest PF 3.22/Sharpe 1.63/11y. VIX gate coded but NOT enforced in etf_sector_emitter production path.

**Verdict:** Easiest path to institutional trust. S effort to wire VIX gate.

---

## 5. FOREX — DISABLED (PF 0.81)

PF<1 = gross losses > gross wins. 80% LONG volume at 29.4% WR (anti-edge). SHORT-only: PF 8.11 on n=29. Survivors: AUDUSD SHORT PF 3.55.

**Verdict:** Correctly HARD_DISABLE. SHORT-only sleeve if paper-proven.

---

## 6-8. BOND / FUTURES / PENNY-MEME

**BOND:** n=11, PF 0.66 — research-only. **FUTURES:** n=0 — merge into COMMODITY. **PENNY/MEME:** PF 0.19-0.50 — permanently quarantined.

---

## 9. Safety Gates — Are They Over-Filtering Winners?

**No. Gates are calibrated correctly.** Confidence >0.90 WR=14% (correctly blocked). MEMECOIN PF=0.50 (correctly blocked). FOREX LONG WR=29.4% (correctly blocked). Elite grade D/F WR=30-33% (correctly blocked).

**Exemptions needed for:** luxalgo_filters/alpha_engine on BTC/ETH only (source whitelist for liquid core), FOREX SHORT-on-majors (DXY-gated), COMMODITY carry-momo (exempt from COT gates — different data).

---

## 10. Top Recommendation Per Asset Class

| Class | Top Strategy | Expected PF Lift | Effort |
|---|---|---|---|
| CRYPTO | Liquid Core + on-chain + source whitelist | +0.15-0.30 | M |
| EQUITY | VIX<22 12-1 Momentum on 20-25 LC | +0.3-0.8 | S-M |
| COMMODITY | Carry-momo double-sort (Miffre 2010) | T2 if n≥80 | M |
| ETF | 11-Sector Rotation + VIX<25 | +0.5-1.0 | S |
| FOREX | HARD_DISABLE; if revived SHORT-only 4 majors + DXY | PF>1.3 if paper-proven | M |
| BOND | Lower floor + 3 academic pilots | Unknown | M |
| FUTURES | Merge into COMMODITY + overnight drift | n≥50 after merge | M |
| PENNY/MEME | PERMANENTLY QUARANTINED | — | — |

---

## References
- `reports/asset_class_90day_plan_*_2026-05-15.md` (8 files)
- `reports/90day_gap_analysis_2026-05-15.md`
- `reports/MASTER_ACTION_PLAN_2026-05-15.md`
- `reports/INSTITUTIONAL_READINESS_PLAN_2026-05-24.md`
- `audit_trail/quality_gates.py` (~10,500 lines)
- `DAILY_IDEAS.MD`
