# Asset-class-specific fixes

Each class gets: what the ledger says today, what is structurally wrong with *that* class, the specific
fix, and the gate that would let it emit again. A class is not "improved" by trying harder; it is
improved by removing a defect or by proving an edge on a pre-registered test.

Baseline (3,500 closed rows, 2026-02-21 → 2026-11-14):

| Class | n | WR | PF | total pp | mean/trade | after-cost WR margin | 3× cost test |
|---|---:|---:|---:|---:|---:|---:|---|
| CRYPTO | 1,966 | 39.3% | 0.768 | −837.8 | −0.426% | −9.5pp | 0.58× ❌ |
| EQUITY | 738 | 47.0% | 1.154 | +238.3 | +0.323% | **+2.9pp** | 3.23× ✅ |
| ETF | 567 | 44.3% | 1.036 | +22.9 | +0.040% | −0.2pp | 0.40× ❌ |
| FOREX | 187 | 39.0% | 0.634 | −29.0 | −0.155% | −16.2pp | −1.94× ❌ |
| BOND | 35 | 37.1% | 0.586 | −7.7 | −0.221% | −16.0pp | −4.41× ❌ |
| COMMODITY | 7 | 42.9% | 0.604 | −4.2 | −0.598% | — | thin sample ❌ |

---

## CRYPTO — the class where the fix is worth more than any new signal

**Defect:** stop fills. Planned 1.919%, realized 2.956% (**1.54×**). 703 of 773 stopped trades exited
somewhere other than the declared stop. Overshoot **+832.4pp** against a class loss of −837.8pp.
94% of it (`+727.3pp`) comes from **one source system**, `kimi_riseoftheclaw` (n=174).

**Fixes, in order:**
1. **crypto fills (DONE TODAY):** gap-aware fill in the resolver; `stop_fill.py` provenance fields.
   Expected: PF 0.768 → ≈1.00. Breakeven, not profit.
2. **`kimi_riseoftheclaw` exit writer:** its rows carry `resolver_version = NULL`, so they never reached
   the intrabar path. Route them through the resolver (or port the fill logic into that tracker).
   Largest single-PnL item in the repo.
3. **Kill SWING-horizon emission:** SWING n=243, PF 0.457, −328.6pp (39% of the class loss). POSITION
   n=33, PF 3.180, +74.4pp — freeze that rule set and forward-test it (gate: PF ≥ 1.3, WR ≥ 55%,
   n ≥ 100).
4. **Re-measure before any signal work.** Until fills are honest, every crypto strategy ranking is
   measuring execution, not prediction.

**Re-emit gate:** post-fix forward PF ≥ 1.15 at n ≥ 300, with the stop-slippage share of gross PnL
< 10%.

---

## EQUITY — the only class above breakeven, and probably just beta

**Defect:** none confirmed. It is the only class clearing 3× cost (mean +0.323% vs 0.30% required) and
the only one whose losses stay inside the plan (0.91× — exits land *inside* the stop, not past it).
But t=1.52 (p=0.12), n=738, and second-half PF fell 1.342 → 0.977.

**Fixes:**
1. **Settle the stop semantics (B4/D1):** 66% of its `SL_HIT` rows exited before the stop. If that is a
   trailing stop, the label is wrong; if not, the class's exit stats are contaminated. Record
   `stop_loss_at_exit`.
2. **Extend to 24 months and benchmark SPY total return**, not zero.
3. **Keep emitting** — it is the only class with a positive margin, and the cost gate allows it.

**Re-emit gate (pre-registered in `final_2026_11_14`):** OOS Sharpe ≥ SPY Sharpe **and** PF ≥ 1.15 at
n ≥ 500, both halves ≥ 1.05. Expect beta; test it anyway.

---

## ETF — 267% of average PnL is cost; this class cannot win as configured

**Defect:** the system's own slippage validator puts ETF slippage at **267% of average PnL**, and mean
PnL is +0.040% against a 0.10% round-trip cost. 79% of its stops exit inside the stop. The 85× win-rate
spread between cohorts (2.22% intrabar vs 73.3% policy-clean) means the class is not even measured
consistently (B2).

**Fixes:**
1. **Stop emitting intraday ETF picks.** At 0.0187% expected per trade against a 0.05% cost assumption,
   every trade is negative-EV before the signal is considered.
2. If ETF coverage is wanted, it must be **daily-or-slower**, with costs measured rather than assumed
   (maker fills or a wider expected move).
3. Fix the cohort inconsistency before quoting any ETF number.

**Re-emit gate:** mean PnL ≥ 3× measured cost at n ≥ 200 on a daily horizon.

---

## FOREX — worst structural margin, plus the class is contaminated

**Defect:** breakeven gap **−16.2pp** (widest in the ledger). 49/277 rows are not spot FX (44 currency
ETFs + 5 `EURUSDT`). 105/277 carry date-only timestamps, 44 unparseable EST stamps. The currency
allowlist is defined once and enforced zero times. 59% of stops exit inside the stop.

**Fixes:**
1. Enforce the allowlist at emit; reclassify currency ETFs to ETF; drop `EURUSDT`.
2. Reject unparseable timestamps at ingest (a date-only entry cannot support an intraday stop).
3. **Do not attempt to close a 16pp gap with signal work.** The class needs a structural change — carry
   with a funding/basis model, weekly horizon — not better entry timing.

**Re-emit gate:** PF ≥ 1.15 at n ≥ 300 on a weekly horizon, measured cost ≤ 20% of gross PnL.

---

## BOND — n=35 with 86% of stops exiting inside the stop

**Defect:** sample too small to rank, and the exit semantics are broken worst here (18 of 21 stopped
rows exited before the stop). WR depends on the definition: 34.3% under `status=WON`, 37.1% under
`pnl_c > 0` (finpredict-v2 C-F). Both should be published; neither supports a decision at n=35.

**Fixes:**
1. Publish both WR definitions with the denominator; never quote one alone.
2. Fix the exit labelling (trail vs mislabel) before any bond metric is used.
3. Treat BOND as a **duration/rates exposure question**, not a pick class — same logic as mutual funds.

**Re-emit gate:** n ≥ 200, PF ≥ 1.15, cost ≤ 20% of gross PnL.

---

## COMMODITY — n=7, but the only class with a testable non-exhausted data source

**Defect:** n=7 is not a sample. `slippage_validation` reports **422% of average PnL** — the worst cost
ratio in the system. Its `WATCH` label (PF 1.026 on n=229 in a *different* cohort) is not a
profitability finding.

**The COT test (run today, gate FAILED):** pre-registered as OOS PF ≥ 1.15 at n ≥ 100, slippage < 25% of
average PnL, beating an equal-weight commodity benchmark. Result: **all four checks fail** —
see `../01_plan/BACKTEST_SIMULATIONS.md` §3.

**Fixes:**
1. **Do not emit commodity intraday.** 422% cost ratio is a hard no.
2. If COT is revisited: the sign is likely wrong (the inverse/momentum direction scored better OOS:
   PF 1.087 vs 0.861). A momentum version at z ≥ 2.0 with a 2-week hold is the honest next test — and it
   must be pre-registered as a *new* trial, not a re-read of the old one.
3. Fix the cost model first: 10–15bp is an assumption, and 422% says it is optimistic.

**Re-emit gate:** any commodity emission requires measured cost ≤ 25% of gross PnL.

---

## Classes that exist in `readiness` but not in the ledger

`FUTURES`, `MEME`, `PENNY_STOCK` appear in `readiness.by_class` with `sizing_allowed: false`, and have
**zero** rows in the 3,500-row ledger. `fix-p0` reports FUTURES n=52 and MEME n=10 from other stores.
Either they emit somewhere the audit cannot see, or the readiness rows describe classes that do not
exist. Trace one pick per class end to end (D7) before adding anything to them.

`MUTUAL_FUND` does not exist in either — see `../03_focus/MUTUAL_FUNDS_SUBSET.md`.

---

## What each class needs before it may emit again

| Class | Binding constraint | Fix status |
|---|---|---|
| CRYPTO | fill fidelity (94% one system) | resolver fixed; that tracker still not routed |
| EQUITY | prove alpha vs SPY | allowed now; OOS test pending |
| ETF | cost > edge | blocked by 3× gate |
| FOREX | contamination + 16pp gap | blocked by 3× gate |
| BOND | sample + exit labels | blocked by 3× gate |
| COMMODITY | 422% cost, failed COT gate | blocked; thin sample |

Only EQUITY may emit today. That is the cost gate working as designed, not a bug in it.
