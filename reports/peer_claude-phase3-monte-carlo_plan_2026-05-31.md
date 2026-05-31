# Phase 3 — Monte Carlo on Watchlist Candidates (BEFORE)

Date: 2026-05-31
Author: peer_claude (Opus 4.7)
Branch: fix/incidents-p0-batch-2026-05-31 (read-only DB; tools/phase3_mc_watchlist.py only)

## Question

Given the observed PF/WR at small n, what's the probability the strategy holds T2 thresholds (PF>=1.5, WR>=50) at n=100? at n=200? What about T1 (PF>=2.0, WR>=55)?

## Candidates (verified against Phase 2 reports)

1. **EQUITY `stocks_rsi2_pullback`** — Phase 2 obs n=34 / WR 53% / PF 1.52
2. **FOREX `fx_smart_carry_trade_momentum`** — n=21 / WR 52% / PF 1.62
3. **COMMODITY `cta_golden_cross_200`** — Phase 2 sample-limited candidate
4. **CRYPTO (n>=100 non-degenerate)** — from Phase 2 crypto report:
   - `prediction_market_consensus` (n=95, WR 84%, PF 24.5) — sub-100 but headline candidate
   - `luxalgo_confluence` (n=1968, WR 42.6%, PF 1.10) — largest emitter, sub-T2
   - empty-strategy bucket (n=301) — un-tagged, control-only
5. **BOND `futures_momentum`** — n=8 1-trade artifact, sanity check only

Live n will be re-read from `ejaguiar1_stocks.trading_picks` (closed only, pnl_pct NOT NULL) at run time.

## Method

- Read closed-pick `pnl_pct` per (strategy, category) where `status` in ('WON','LOST','CLOSED','TP_HIT','SL_HIT','EXPIRED') AND `pnl_pct` IS NOT NULL.
- Bootstrap resample WITH replacement: 10,000 iters at target sizes n_now, 100, 200.
- For each resample compute:
  - WR = (#picks with pnl_pct > 0) / n
  - PF = sum(positive pnl_pct) / abs(sum(negative pnl_pct))
- Report P(PF>=1.5 AND WR>=50) and P(PF>=2.0 AND WR>=55) at each target n.
- Percentile CIs: 5th/50th/95th of PF and WR at each n.

## Caveats noted up front

- Bootstrap assumes the observed sample is representative of future draws (i.i.d. resampling). It does not model regime-shift or source-concentration risk.
- For thin-n candidates (n<30), CIs will be wide and the P(T2) estimate has its own sampling error.
- A high P(T2) is necessary but not sufficient; concentration gate / MDD gate / DSR are separate checks not addressed here.

## Output

- `reports/peer_claude-phase3-monte-carlo_result_2026-05-31.md` (per-candidate table + KEEP/KILL recommendation)
- `tools/phase3_mc_watchlist.py` (self-contained one-off, read-only DB)

## Safety

- READ-ONLY SELECT on `ejaguiar1_stocks.trading_picks`.
- No DB mutations; no production code touched.
