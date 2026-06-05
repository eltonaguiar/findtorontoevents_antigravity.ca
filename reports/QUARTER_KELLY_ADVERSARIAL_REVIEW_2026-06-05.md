# Quarter-Kelly Adversarial Review — 4 CRYPTO Sleeves Pilot

Date: 2026-06-05
Cohort: JUP/ENA/ADA × mega_mutation + DYDX × alpha_engine
Peer recommendation under review: **Quarter-Kelly (16-19%) as "sane cap"**

## Adversarial Position: Quarter-Kelly is STILL too aggressive

### 1. Effective-n collapse from correlation (the deal-breaker)
The peer flagged 37–60% same-day exit correlation across JUP/ENA/ADA. Three correlated symbols on **one shared edge** (mega_mutation) is not 3 sleeves — it is **~1.5 effective sleeves**. Kelly fractions are derived assuming i.i.d. bets. When ρ ≈ 0.5, the realised variance per dollar deployed is ~`1 + (n-1)ρ` higher → for n=3, ρ=0.5, variance multiplier ≈ 2.0×. The correct fractional-Kelly adjustment is to divide by √(variance multiplier) ≈ **1.41×**, dropping Quarter-Kelly (0.25) → effective **0.177× = ~Sixth-Kelly** before any other haircut.

### 2. Resolver mismatch on mega_mutation is a model-error, not a risk-multiplier
TP=±2.0% but realised PnL 3–11% at "0h hold" means the resolver is **not measuring the true distribution** — it is measuring the candle's worst/best print, not the actual fill. Kelly requires honest (p, b/a). With single-snapshot resolver contamination (per MEMORY.md ai-tournament-wr-artifact 2026-06-03 + backfill_data_quality 2026-06-05), realised win-rate is **upward-biased**. Adversarial estimate: true p is 5–15 percentage points lower than stated. Re-running Kelly with p−0.10 collapses the raw Kelly to **~40-50%**, so Quarter-Kelly on the **honest** distribution would already be ~10-12%.

### 3. DYDX brittleness: 0.84 win/loss ratio
89% WR carrying a sub-unity W/L ratio means **any 3-loss streak wipes ~7 winners**. The expected loss-streak length in 100 trades at p=0.89 is ~2-3, expected max ~4. Kelly is monotonic in p; a 5pp drop in true p (89→84) cuts the Kelly fraction by ~40%. DYDX should size **half** of mega_mutation per dollar, not equal.

### 4. n is still tiny (n=25-30 per sleeve) → DSR/SPA-grade uncertainty bands wide
Per MEMORY ohlcv-replay-dedup-2026-06-05, mega_mutation n=204 dedup is the ONLY T1. Per-symbol n=25-30 has 95% CI on PF spanning ~[1.4, 4.5] — pre-trade we cannot distinguish PF=1.6 (size small) from PF=3.0 (size up). **Sample-size-aware Kelly says: shrink toward zero proportional to 1/√n until n ≥ 100 per symbol.**

## Verdict Structure

1. **Right sizing fraction:** **Eighth-Kelly (0.125×) on the EDGE, not the symbol** — i.e. 12.5% × honest-p Kelly on mega_mutation as **one** position spread across JUP/ENA/ADA, and a SEPARATE Eighth-Kelly on DYDX. Effective per-symbol exposure ≈ **2-4% of bankroll** during pilot.
2. **Per-trade max cap:** **1.0% of bankroll at risk (SL distance × size)** — matches `_MAX_PORTFOLIO_PCT=50` logic but tightened for pilot. Hard cap regardless of Kelly output.
3. **Per-day max cap:** **3% bankroll at risk/day**, max 4 concurrent positions (3 mega_mutation + 1 DYDX). Reject signal #5.
4. **Total cohort exposure cap:** **8% notional / 4% risk-at-stop**, treating mega_mutation symbols as ONE correlated bucket capped at 6% notional + DYDX capped at 2% notional.
5. **Kill-switch:** **3 consecutive losing days OR −5% bankroll drawdown OR resolver-vs-fill divergence >50bp on any single trade** → full halt, post-mortem before resume. (Matches existing `tests/test_kelly_dd_halt.py` pattern at 30d DD halt; tighten for pilot.)
6. **Minority "no real-money this week" rationale:** **YES, flag it.** The mega_mutation resolver mismatch (TP 2% → realised 3-11%) is unresolved per MEMORY backfill_data_quality_2026-06-05. Until intrabar OHLC replay confirms the fill distribution matches the resolver assumption, **paper-only for 2 more weeks** is the defensible call. Going live this week sizes on a distribution we have NOT verified.

## Recommended pilot ladder (if operator overrides minority)
- Week 1: Eighth-Kelly (~2% per symbol), live-fire 4 trades max, compare realised PnL vs resolver expectation per trade.
- Week 2: If realised within ±20% of expected → Sixth-Kelly (~3%). Else halt.
- Week 4: If n≥40 per symbol AND DSR > 0.95 → Quarter-Kelly. Earliest defensible Quarter-Kelly date: **2026-07-03**.

## Reference baselines used
- `alpha_engine/kelly_position_sizer.py` ships `fraction=0.25` default + `_MAX_PORTFOLIO_PCT=50` cap (Quarter-Kelly IS the codebase default — peer rec restates current code).
- `alpha_engine/eagle_gates.py` `_EAGLE6_MAX_SOURCE_HHI=0.20`, `_EAGLE6_MAX_PBO_GLOBAL=0.5`.
- `audit_trail/quality_gates.py` `SMART_PICKS_MAX_CONFIDENCE=0.95`, `CRYPTO_HARD_MAX_AGE_HOURS=72`.
- `tests/test_kelly_dd_halt.py` enforces drawdown halt — extend to 5% pilot threshold.
