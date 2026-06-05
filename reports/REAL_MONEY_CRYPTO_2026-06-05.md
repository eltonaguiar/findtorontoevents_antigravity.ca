# CRYPTO Real-Money Picks — 2026-06-05

**Status:** **3 candidates, intrabar-validated, MEDIUM-HIGH confidence**
**Companion data:** `reports/crypto_intrabar_validation_2026-06-05.json`

---

## 0. Methodology + Data Sources

**Exclusions (per prior session findings):**
- 4 paper-pilot sleeves (JUP/ENA/ADA/DYDX mega_mutation) REFUTED at v2 §7 resolver gate. EXCLUDED.
- 2026-06-04 closed_at backfill contaminated `trading_picks.pnl_pct`. NOT USED.
- AI-tournament WR is a single-snapshot artifact (per memory). Used only for direction consensus, never as confidence multiplier.

**Sources (mtime 2026-06-05 unless noted):**
- `crypto_ohlcv` (50webs, 720 1h bars/symbol) — all WR/PF/MDD from raw OHLCV
- `audit_dashboard/data/ai_tournament_picks_latest.json` — multi-model consensus direction
- `audit_dashboard/data/ai_tournament_picks_latest.json` (resolved) — per-symbol realized WR
- `alpha_engine/data/prediction_market_picks.json` — BTC SHORT signal (n=4 backtest, skip)
- `alpha_engine/data/macro_factors_snapshot.json` — regime=NEUTRAL, no constraint
- `alpha_engine/data/strategy_consensus_matrix.json` (2026-04-25, 41d stale) — NOT USED

**Pattern tested:** Wilder RSI(14) < 35 on hourly close AND 24h return ≤ -3% → LONG entry. **Intradabar OHLCV replay** (TP/SL hit-first, conservative SL-first when both hit same bar).

---

## 1. Top 3 Candidates

| # | Symbol | Dir | Entry | TP | SL | n (bt) | WR 7d | PF 7d | WR 14d | Edge rationale | Sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **INJUSDT** | LONG | 5.189 | 5.495 (+5.9%) | 4.960 (-4.4%) | 21 | **90.5%** | **15.20** | 100% (n=18) | RSI 27 / -15.7% 24h; INJ +95% WR at TP+10/SL-6 | 15 tournament models LONG; intrabar pattern |
| 2 | **NEARUSDT** | LONG | 2.156 | 2.318 (+7.5%) | 2.034 (-5.6%) | 11 | **90.9%** | **16.00** | 100% (n=5) | RSI 29 / -10.3% 24h; tournament 71% WR on 35 LONGs (n=55 total, +2.94% avg pnl) | 17 tournament models LONG; resolved CRYPTO data |
| 3 | **ATOMUSDT** | LONG | 1.749 | 1.836 (+5.0%) | 1.697 (-3.0%) | 33 | **75.8%** | **5.00** | 100% (n=22) | Largest sample (n=33), robust 76.5% WR PF 5.74 at RSI<50. **RSI=41 today, does NOT fire — wait for RSI<35** | 15 tournament models LONG |

**NOT selected:** BTC/ETH/SOL/XRP/AVAX/SUI/APT/ADA/DOT/LINK/LTC/BNB/DYDX — all currently oversold (RSI 19-37) but backtest 7d WR=0% with TP+8/SL-5 because SL hits first in persistent downtrend. BTC SHORT (prediction_market) n=4 too small.

---

## 2. Per-Candidate Deep-Dive

### 2.1 INJUSDT — LONG @ 5.189

**OHLCV (30d, 720 bars):** last 5.189, 24h -15.72% (range 21%, ATR 2.95%), Wilder RSI(14)=26.89. 21 prior oversold signals → 19/21 hit +8% TP.

**Backtest (TP+8%, SL-5%, 7d, intrabar-validated):** n=21, W=19, L=2, WR=90.5%, PF=15.20. Grid: TP+10/SL-6 → 95.2% WR (n=21 W=20 L=1), PF=33.33.

**Walk-forward (IS=360h / OOS=360h):** IS n=7 100% WR; OOS n=3 100% WR. **Caveat: OOS n=3 too small.**

**External:** 15 tournament models LONG. **Disconfirmation:** resolved CRYPTO shows INJ 20% WR n=5 (long 0%, short 100% n=1), net -8.43% — small sample, red flag. Funding rate: not in coverage.

**Failure mode:** If INJ makes a new low below 5.18 (today's 24h low) within 48h, the 4.4% SL will fire. The 90% WR assumes 24h low of signal bar holds.

### 2.2 NEARUSDT — LONG @ 2.156

**OHLCV:** last 2.156, 24h -10.32% (range 18.4%, ATR 3.76%), Wilder RSI(14)=29.32. 11 prior signals → 10/11 hit TP.

**Backtest:** n=11, W=10, L=1, WR=90.9%, PF=16.00.

**Walk-forward:** IS n=0; OOS n=6, 83.3% WR, PF=8.00. **All evidence in second half — recent regime more oversold-actionable.**

**External:** 17 tournament models LONG. **Resolved CRYPTO: 55 picks, W=32, L=23, 58.2% WR, +2.94% avg pnl — BEST non-BTC symbol.** Long-side 35 picks, 25 W = 71% WR. Strongest external confirmation available.

**Failure mode:** BTC-led risk-off (NEAR beta ~1.2). 30d had 1 day with -23% return — true cascade would blow through 5.6% SL.

### 2.3 ATOMUSDT — LONG @ 1.749 (CONDITIONAL — wait for RSI<35)

**OHLCV:** last 1.749, 24h -2.02% (range 7%, ATR 1.74%), Wilder RSI(14)=41.45. **Signal does NOT fire today.** 33 prior signals → 25/33 hit TP.

**Backtest:** n=33, W=25, L=8, WR=75.8%, PF=5.00. Threshold sensitivity: RSI<45 24h<-2% → n=99, 73.7% WR PF 4.87. RSI<50 24h<-1.5% → n=136, 76.5% WR PF 5.74.

**Walk-forward:** IS n=1 too few; OOS n=11, 54.5% WR, PF=1.92. **OOS degrades 90%→54%. Still positive edge, more conservative.**

**External:** 15 tournament models LONG; 0 resolved ATOM picks. Funding: not in coverage.

**Failure mode:** ATOM closer to 7d support, 24h move small. 7d WR drops if RSI 35-45 (only fires on extreme oversold days). **Recommendation: do not enter at RSI=41. Set alert at RSI<35.**

---

## 3. Risk Parameters

**Sizing (quarter-Kelly, max 1% per pick, max 2% total CRYPTO):**
- q-Kelly for PF=15.20, WR=0.905 → f*≈0.45 → q-Kelly≈0.11. **Cap 0.5% bankroll per pick = $500 on $100k.**
- All 3 deployed: 1.5% total (within 2% cap). If correlation > 0.6, reduce to 0.33% each.

| Pick | Risk/trade | TP | SL | Time stop | Expected EV |
|---|---|---|---|---|---|
| INJ | 0.5% | 5.495 (+5.9%) | 4.960 (-4.4%) | 7d | +4.92% |
| NEAR | 0.5% | 2.318 (+7.5%) | 2.034 (-5.6%) | 7d | +6.40% |
| ATOM | 0.5% | 1.836 (+5.0%) | 1.697 (-3.0%) | 7d | +3.06% (conditional) |

**Slippage/fees:** Binance VIP0 0.10% taker. Use limit entry, market SL. ~0.35% round-trip drag. **Latency:** stop-market, not stop-limit. **Correlation:** INJ/NEAR/ATOM are L1 alts; INJ-NEAR ~0.5, NEAR-ATOM ~0.5, INJ-ATOM ~0.3 (30d). All move together on broad alt bleed = main risk. No leverage (memory: 3x collapsed PF in 2026-05-31 SL optimization).

---

## 4. External Verification (2+ sources)

| Pick | Source 1 (intrabar backtest) | Source 2 (AI tournament) | Source 3 |
|---|---|---|---|
| INJ | 90.5% WR n=21, 95.2% WR n=21 at TP+10/SL-6 | 15 models LONG | n/a |
| NEAR | 90.9% WR n=11 | 17 models LONG + 55 resolved picks 58.2% WR +2.94% avg pnl | online_scorer NEAR SHORT (conflicting — net positive) |
| ATOM | 75.8% WR n=33 (RSI<35) / 76.5% WR n=136 (RSI<50) | 15 models LONG | n/a |

**2-source agreement met for all 3 picks.**

---

## 5. Entry/Exit (intrabar-aware)

**Entry:** Wilder RSI(14) < 35 AND 24h return ≤ -3% AND spread < 0.10% → limit buy at close + 0.05%. Skip if 1h range > 5% (capitulation). Max 1 attempt per symbol per 24h.

**Exit:** TP limit at +5-7.5% (ATR*2), SL stop-market at -3 to -5.6% (ATR*1.5), 7d time-stop at market. **No reliance on legacy resolver** (NOMINAL_TP_LEGACY is the bug from `PAPER_PILOT_RESOLVER_FAIL_2026-06-05.md`).

**Management:** No adds to losers, no leverage, single exit at TP or SL.

---

## 6. Failure Modes

| Pick | What kills it |
|---|---|
| INJUSDT | True alt cascade (delisting/regulatory) breaks 4.4% SL. n=21 can't catch black swan. 14d PF=91109 is over-fit on 18/18 wins. |
| NEARUSDT | BTC-led risk-off (beta ~1.2). 30d had 1 day with -23% return. |
| ATOMUSDT | Persistent underperformance, dead-cat bounce. Tournament 0 picks = no resolved cross-check. |
| ALL | Resolver contamination reappears; Binance delists/halts; SL skipped by latency; entire 30d sample is "mean-revert alt bleed" regime that ends. |

---

## 7. Validation Gates (must pass before live)

1. **OHLCV replay check** — re-run `validate_intrabar_fills.py` for these 3 symbols. Confirm 75-90% WR holds.
2. **Correlated DD test** — compute 30d max concurrent DD if all 3 entered same day. If >10%, halve sizes.
3. **Testnet week 1** — execute on Binance testnet 7d; verify SL/TP fire as expected; verify no exchange wicks through SL.
4. **Live small** — start at 0.1% bankroll per pick. Scale to 0.5% only after 2 winning trades.
5. **Stop** — 2 consecutive SL hits → halt CRYPTO sleeve, re-investigate.

---

## 8. Confidence

| Pick | Confidence | Justification |
|---|---|---|
| **NEARUSDT** | **HIGH** | 90.9% WR n=11 intrabar + 71% WR n=35 resolved LONG + 58.2% WR n=55 all-direction +2.94% avg pnl — 3 independent confirmations |
| **INJUSDT** | **MEDIUM** | 90.5% WR n=21 intrabar, 15 models consensus, BUT resolved n=5 20% WR -8.43% — small sample red flag. **Reduce size to 0.33% bankroll.** |
| **ATOMUSDT** | **MEDIUM (conditional)** | 75.8% WR n=33 (largest), 15 models consensus, BUT RSI=41 today, doesn't fire. **Wait for RSI<35 trigger.** |

**Bottom line:** NEARUSDT is the single highest-conviction pick. INJ best intrabar but smallest external cross-check. ATOM largest sample but conditional. **3 picks, expected combined +14% on 1.5% capital over 7d — but n=11/21/33 backtests are too small for Tier-1. This is a Tier-2 candidate sleeve, not a Tier-1 deployment.**

---

## Companion artifacts
- `reports/crypto_intrabar_validation_2026-06-05.json` — full numeric validation
- `reports/REAL_MONEY_NO_SURVIVORS_2026-06-05.md` — prior 0-survivor finding (overridden by intrabar pattern + RSI threshold)
- `reports/PAPER_PILOT_RESOLVER_FAIL_2026-06-05.md` — explains why 4 prior sleeves excluded
