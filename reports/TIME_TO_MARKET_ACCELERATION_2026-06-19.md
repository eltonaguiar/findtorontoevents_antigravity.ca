# Time-to-Market Acceleration — getting to a SAFELY-recommendable, trustworthy winner faster
**Lens:** hedge-fund PM + quant team · 2026-06-19 · **Author:** claude-opus

## Define the finish line (so we can measure "time")
"Time-to-market" = calendar time until a candidate **clears the promotion bar AND the surface is trustworthy**:
> net-of-cost PF **CI-LB > 1.15** at **n_eff ≥ 80** on the **FORWARD** window, time-split-robust, single-symbol concentration **< 35%**.

**Where we are (SQL-verified 2026-06-19):** **0/10** classes pass. Exactly **one** honest lead — `crypto_rsi5070_us` (CRYPTO ∧ RSI(14,1h)∈[50,70] ∧ US session): net@16bp **PF 1.36**, IS/OOS **1.44/1.30**, but **CI-LB 0.95 < 1.15 at n=108**. Gate = n≥150 (~Jun-25, **now slipped** by the 6-day ledger freeze). Everything else is honestly refuted (FOREX consensus = daily-resolution artifact; 307-strategy sweep = 0; daily-only sources = phantoms).

## The binding constraint
The dominant cost is **calendar time on FORWARD honest-n accrual**, compounded by **measurement-integrity outages** (we just lost 6 days) and **edge scarcity**. So acceleration = (a) protect & speed the accrual clock, (b) clear the bar with less raw n, (c) run more parallel shots, (d) make "trustworthy" automatic.

## Ranked proactive activities (by leverage)

### TIER 1 — protect & accelerate the accrual clock (highest leverage; the gate is n-limited)
1. **Never lose accrual days again — ship the un-mask + freshness monitor (P0-5).** A frozen ledger behind green CI cost us **6 days = 6 days of slipped gate**. Make the resolver/sync **fail-hard** (CI red) + alert if `at_signal_outcomes max(created_at) > 2h`. *This is the single biggest time-saver: a freeze is pure dead time.* (Partially covered by peer #610; finish the fail-hard exit-code piece.)
2. **Widen the lead's qualifying universe (more honest picks/day).** Confirm every liquid crypto symbol is scanned for the rsi5070_us condition each US session — do NOT change the condition, just maximize its emission breadth so n→150 arrives in days, not weeks. (Audit the scanner universe for an artificial cap.)
3. **Retroactive honest replay to KNOW NOW if the lead will clear (de-risk the wait).** Run the SAME condition's honest first-touch on historical bars (strictly OOS, pre-registered) to get a **larger-n estimate of the net CI-LB today**. Replay ≠ forward-promotable, but if the replay CI-LB at n≈300 is, say, 1.05, the forward gate will likely fail → we pivot **now** instead of waiting to Jun-25 to learn it. Saves weeks of dead accrual on a loser.

### TIER 2 — clear the bar with LESS raw n (tighten CI-LB faster)
4. **Raise n_eff (diversify entries).** The CI-LB is wide because n_eff < n (symbol-day clustering). Spreading entries across more symbols/days lifts n_eff toward 80 faster → the bar clears at lower raw n. Concentration discipline doubles as a speed lever.
5. **Lower the cost basis (maker execution).** net CI-LB is cost-sensitive (sweep: 0.95→0.86 across 16→30bp). If we prove **maker fills (~5bp)** vs 16bp taker for the condition's entries, net PF rises and the bar clears at the **same n**. Quant task: measure the achievable maker fraction / realized spread for rsi5070_us entries.

### TIER 3 — more shots on goal (parallel candidates; the search is exhausted on current signals)
6. **New-mechanism candidates from free data (H3).** The honest-edge search found 0 on existing signals — new candidates need **new data, not re-fishing**: FRED macro regime gates, CFTC COT positioning, EDGAR/PEAD earnings. Pre-register a small FDR-controlled batch per new data class → independent forward lanes accruing in parallel. More lanes ⇒ sooner one clears.
7. **External replication of the lead.** Cross-check rsi5070_us against published microstructure effects (RSI mid-band momentum × liquid-session). External corroboration is *faster confidence* than pure n accrual and strengthens the eventual recommendation.

### TIER 4 — make "trustworthy" automatic (so recommending is SAFE, not just statistically passed)
8. **Honest-first-touch as the ONLY promotion input** — lock out daily-resolved numbers on every surface (the months-of-false-candidates root cause: daily inflates PF ~2-3×). Mostly done; finish the guard.
9. **Enforce concentration + time-split BEFORE DSR/SPA** — close the open P0 (2 false-Tier-1 PASSes because concentration wasn't gated first). Trust fix.
10. **Pre-build the gated execution path** — paper→small-live deploy harness GATED on the bar, ready to fire the moment a candidate clears, so there's zero build-delay on the execution side.

## The two highest-ROI moves to start now
- **#1 (freshness fail-hard)** — stop bleeding accrual days; we cannot afford another silent freeze.
- **#3 (retroactive replay of the lead)** — learn *this week* whether crypto_rsi5070_us will actually clear at n≥150, instead of spending two weeks of accrual to find out.

Both attack the dominant cost (calendar time) directly. #2 (universe breadth) and #5 (maker cost) are the next two, each of which can pull the gate in by days–weeks.

## Honest caveat
None of this manufactures edge that isn't there. If the retroactive replay (#3) shows the lead's CI-LB won't reach 1.15 even at large n, the fastest path to a *trustworthy* winner is TIER 3 (new-data candidates) — and the honest answer may remain "no sizeable edge yet," which is itself a valuable, money-protecting verdict.
