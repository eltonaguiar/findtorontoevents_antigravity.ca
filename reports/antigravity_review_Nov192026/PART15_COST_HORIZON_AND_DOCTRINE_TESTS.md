# PART 15 — THE COST-HORIZON LADDER, AND A DOCTRINE CLAIM THAT FAILS

**Author:** `githubcopilot-mercury3AI`
**Date:** 2026-11-22 05:05 EST
**Precedes:** PART13 (cost wall), PART14 (portfolio tracking + funding carry)
**Status:** phase complete · 1 new defect found and fixed in my own code · 1 audit2 doctrine claim refuted

---

## 1. WHAT THIS PHASE ASKED

PART13 established that gross edge is real and 6–9× smaller than the fee needed
to capture it at 5-minute horizons. The obvious next question is not "is there
alpha" but:

> **At which (strategy × horizon × instrument) does gross edge per trade clear
> the round-trip cost by the Gate-C factor of 3?**

Method: measure gross edge per trade and derive the **maximum affordable**
round-trip cost (`gross / 3`), then compare against what the venue actually
charges. This inverts the usual presentation deliberately — the usual
presentation hides the answer inside the fee assumption, which is exactly what
peer buffy flagged.

Reproducer: `python3 tools/cost_horizon_ladder.py`
Output: `reports/cost_horizon/cost_horizon_ladder.json`

---

## 2. DEFECT FOUND IN MY OWN TOOL MID-PHASE (disclosed, fixed)

**Overlapping positions.** My first `simulate()` entered **every** signal,
including every bar of a sustained breakout. A Donchian rule emits a signal on
each bar of a trend, so the same move was counted many times, inflating both
`n` and the t-statistic.

Impact of the fix (one-position-at-a-time):

| cell | n before | n after | t before | t after |
|---|---:|---:|---:|---:|
| BTC-USD 1D donchian | 379 | **188** | 5.01 | **2.88** |
| SPY 1D donchian | 1,043 | **395** | 4.07 | **2.91** |
| GLD 1h donchian | 414 | **181** | 3.91 | **3.56** |
| BH-FDR survivors (of 48 cells) | 10 | **4** | | |

**The original result was half inflated.** No conclusions below use the pre-fix
numbers. This is the fifth self-found defect in this program, and the pattern is
consistent: my errors have all over-stated evidence.

---

## 3. THE MAIN RESULT: EDGE PER TRADE RISES MONOTONICALLY WITH HORIZON

Median gross edge per trade across all positive cells:

| horizon | n positive cells | median gross |
|---|---:|---:|
| 15m | 5 | **+2.48 bp** |
| 1h | 7 | **+7.49 bp** |
| 4h | 8 | **+21.16 bp** |
| 1D | 12 | **+24.21 bp** |

**Monotone increasing.** Cost per trade does *not* rise with horizon, so
edge/cost improves monotonically with horizon. This mechanism does not depend on
any single cell's t-stat, which is precisely why it is the finding to trust:
it is a statement about the *shape* of the data, not about a lucky cell.

It also explains every earlier result in this program without contradiction:
- `live_daytrade_sim`'s 5m strategies lost 616% of gross to fees ✓ (lowest edge/trade)
- My 5m challenge lost 889% of gross to fees ✓
- Daily trend overlays survived ✓ (highest edge/trade)
- The peer agent's FX mean-reversion "+4.3bp gross vs 10bp cost" ✓

---

## 4. THE FOUR CELLS THAT SURVIVE MULTIPLICITY CONTROL

48 cells tested → 15 raw p<0.05 → expected false positives 2.4 → **4 survive BH-FDR**:

| inst | hz | strategy | n | gross bp | t | maxCost | taker | years | Gate C |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| BTC-USD | 1D | donchian | 188 | **+111.36** | 2.88 | 37.12 | 20.0 | 17.7 | PASS taker |
| SPY | 1D | donchian | 395 | **+22.87** | 2.91 | 7.62 | 4.0 | 33.8 | PASS taker |
| GLD | 1h | donchian | 181 | **+17.46** | 3.56 | 5.82 | 4.0 | **3.1** | PASS taker |
| GLD | 15m | donchian | 39 | −12.22 | −3.01 | −4.07 | 4.0 | 0.2 | FAIL (negative) |

The list contains **a genuinely negative cell** as well as positives, which is
the sign that the control is discriminating rather than just passing everything.

### 4.1 Verification — split-half and parameter plateau

| cell | first half | second half | stable? |
|---|---|---|---|
| GLD 1h donchian | +19.72 bp (t=3.39) | +15.23 bp (t=1.92) | **yes** |
| SPY 1D donchian | **+5.49 bp (t=0.47)** | +40.70 bp (t=3.91) | nominally, but see below |
| BTC 1D donchian | +143.88 bp (t=2.58) | +78.84 bp (t=1.47) | yes, decaying |

**SPY's edge is almost entirely post-2010.** The first half (1993–2009) is
statistically indistinguishable from zero (t=0.47). So the SPY result is not a
33-year effect; it is a ~15-year effect that I would have over-claimed by
presenting the full-sample t-stat.

**Parameter plateau (SPY 1D, breakout lookback):**

| look | n | mean bp | t |
|---:|---:|---:|---:|
| 10 | 482 | +12.86 | 1.66 |
| 15 | 431 | +12.20 | 1.60 |
| **20** | 395 | **+22.57** | **2.87** |
| 25 | 375 | +15.17 | 1.93 |
| 30 | 360 | +11.92 | 1.56 |
| 40 | 336 | +11.51 | 1.52 |

**All neighbours are positive** — this is a real effect region, not a fitted
spike. But look=20 is ~1.6× its neighbours, so the honest effect size is
**+12 to +15 bp**, not +22.6. At 4 bp taker cost, +13 bp gives edge/cost ≈ 3.3 —
it *just* clears Gate C, with no margin for error.

---

## 5. AN AUDIT2 DOCTRINE CLAIM THAT FAILS ITS OWN TEST

audit2 states as doctrine:

> "Volatility scaling is free alpha. Simply scaling positions by inverse
> realized vol improves Sharpe by 0.3+ for **any** momentum strategy."

This is quantitative and falsifiable, so I tested it: inverse-vol weights from
trailing 12-month realised vol, signal lagged, **capped at 1.0× (no leverage)**,
excess in cash.

| series | strategy | Sharpe | vol-targeted | ΔSharpe |
|---|---|---:|---:|---:|
| SPY | 12m momentum | 0.90 | 0.85 | **−0.05** |
| GLD | 12m momentum | 0.58 | 0.61 | **+0.03** |
| DBC | 12m momentum | 0.27 | 0.30 | **+0.04** |
| AGG | 12m momentum | 0.76 | 0.78 | **+0.01** |
| | **mean** | | | **+0.01** |

**The claim does not reproduce. Measured mean delta is +0.01, not ≥ +0.30 — off
by a factor of ~30.**

**Why, mechanically:** with no leverage, vol targeting can only *reduce*
exposure. It lowers return and volatility roughly proportionally, leaving Sharpe
flat. What actually improved risk-adjusted return in these same runs was the
**signal** — SPY 12m momentum scored 0.90 vs buy-and-hold 0.75 with max drawdown
−19.5% vs −50.8% — not the sizing rule on top of it.

Audit2's own wording partly anticipates this ("changes statistics more than the
signal does"), but the "+0.3 for any momentum strategy" figure is not
supportable in this data, and it is the kind of number that gets copied forward
without being re-derived. **Recommendation: demote that line from doctrine to a
labelled hypothesis, or attach the conditions under which it holds (leverage
permitted; borrow cost modelled).**

---

## 6. CONVERGENCE WITH audit3 (independent confirmation)

audit3 reports: *"Breakout continuation on liquid US equities/ETFs is the one
family where this system already shows positive out-of-sample statistics
(EQUITY OOS Sharpe +0.61 on 33 folds, ETF +0.21 on 53)"*, and
`POD-EQUITY-BREAKOUT` is its **only** `pre_registered` pod.

My ladder reached the same family by a completely different route (free daily
bars, Donchian breakout, ATR exits, Gate-C cost framing, BH-FDR over 48 cells).
Two independent methods pointing at **equity breakout continuation at daily
horizon** is the strongest convergence in this program.

### 6.1 A conflict that needs resolution, not smoothing

audit3 measures *"ETF slippage ≈234% of per-trade PnL (monthly cadence only,
intraday cost artefact)"* and marks ETF `WEAK`. My ladder measures SPY 1D
breakout at **+22.9 bp gross vs ~4 bp taker cost** — i.e. cost is ~17% of gross,
not 234%.

**These are not reconcilable as stated.** The likely explanation is that the
objects differ: audit3 is scoring *published picks* whose per-trade PnL is thin,
whereas the ladder scores a 2:1 ATR-exit breakout with a 10-bar hold. If so,
audit3's ETF verdict is about its pick flow, **not** about ETF breakout as a
strategy family — and the two statements can both be true while reading as
contradictory. **This must be tested, not assumed** (see §8 R4).

---

## 7. ANSWER TO THE HORIZON QUESTION (what the evidence supports)

Asked: day trading, swing trading, mutual funds, stocks, bonds, ETFs, futures,
forex, crypto, commodities, a GIC, or cash?

Everything in this program now says the answer is **governed by edge-per-trade
versus cost**, and that ordering is stable:

| horizon | verdict from measurement | what I would actually do |
|---|---|---|
| **Intraday / day trading** | Gross edge +2 bp vs 4–20 bp cost. **Failed on every venue at every fee schedule tested.** | Do not. Not "hard" — arithmetically negative. |
| **Swing (days–weeks)** | 4h/1h cells show +17 to +21 bp gross, but the free intraday history is 2–3 years and the one 3-year cell that passed is GLD. Not enough evidence. | Paper only. |
| **Daily/position (weeks–months)** | Best-supported region: +12–15 bp/trade at look=10–40, edge/cost ≈3.3 on taker, plateau-wide. SPY effect is post-2010 only. | The only trading family I would fund, small, with the post-2010 caveat written down. |
| **Long-term core** | PART14: SPY buy & hold beat every overlay on terminal wealth ($287k vs $41k). Overlays buy drawdown insurance at ~1.4pp CAGR. | Core = cheap broad index. Accept the drawdown or pay for the overlay. |
| **GIC / cash** | 3.5% assumed GIC → $19.8k vs SPY $286k over 20y, MDD 0%. Loses badly on growth, wins absolutely on certainty. | Correct vehicle for money needed in <3 years and for the emergency fund. Not a growth strategy. |
| **Bonds** | AGG Sharpe 0.68, MDD −17%. Bond *trading* is WEAK in audit3 (n=37). | Hold for ballast/term premium; do not trade. |
| **Crypto** | audit3 KILL (n=6,926, −0.42%/trade). My ladder: negative gross at every crypto cell except 1D donchian. | Only the delta-neutral **funding carry** (PART14: +7.28%/yr, Sharpe 3.42, reproduced) has positive expectancy — and that is a carry trade, not a directional bet. |
| **Commodities** | audit3 KILL; my PART12 ETF-proxy trend was positive but buffy's CI-LB gate refuted the class. **Unresolved conflict.** | Nothing until the conflict is settled. |
| **Forex** | audit3 WEAK/honest-exhausted; a peer measured net −36.9 bp worse than random. | Nothing. |
| **Futures** | n=4 in audit3, insufficient; free roll-adjusted curves are unusable (both desks confirmed). | Nothing; cannot even measure it. |
| **Mutual funds** | MER is a permanent negative selection alpha. Same underlying exposure as ETFs. | Only if no cheap ETF exists for the exposure. |

**The one-sentence answer:** fund the floor with cash/GICs, fund growth with a
cheap broad index, and let at most a small sleeve trade the single family that
survives cost — daily equity breakout continuation — under audit3's forward
gate, with the post-2010 concentration disclosed.

---

## 8. FRESH TODOS — DEEP REVIEW OF audit2 / audit3 + REAL BACKTESTS

| # | Task | Why | Deliverable |
|---|---|---|---|
| R1 | **Test the "234% slippage" vs my "17% cost" conflict** on one ETF and one window, same dates | §6.1. The two numbers cannot both describe the same object | `reports/etf_slippage_reconciliation.md` |
| R2 | Read `audit3_ledger.json` and recompute one class verdict from raw rows | Never trust a dashboard's arithmetic | Verdict reproduction log |
| R3 | **Re-derive audit2's remaining doctrine claims** as hypotheses (currently stated as fact) | One claim already failed by 30× | Doctrine → hypothesis table |
| R4 | Test vol targeting **with leverage permitted** + borrow cost | The claim may hold under leverage; then say so precisely | Delta table with/without cap |
| R5 | Run a **real backtest of POD-EQUITY-BREAKOUT's exact rule** on 1993–2026 | It is audit3's only pre-registered pod | Gross/net/CI by decade |
| R6 | Test whether SPY breakout edge survives **post-2010 only** with honest costs | §4.1 shows t=0.47 pre-2010 | Split-regime table |
| R7 | Reconcile audit3's `required_n` = 3,388,052 for ETF | That number needs a sanity check; it implies the effect is ~0 | Derivation + critique |
| R8 | Investigate the **430 orphan H-119 rows** (audit2 flags this) | An orphan hypothesis cannot promote anything; it is wasted forward evidence | Attribution fix or written-off |
| R9 | Test `POD-LUXALGO-SHORT` asymmetry (shorts positive, long book KILL) | Most interesting live thread in audit3 | Independent replication |
| R10 | Build the **horizon allocation calculator** from §7 as a tool | Turns this table into something usable | `tools/horizon_allocator.py` |
| R11 | Register the daily-breakout hypothesis with kill criteria **before** forward data | M-107 compliance | Registry entry |
| R12 | Resolve COMMODITY conflict with buffy (their CI-LB refutes my ETF-proxy trend) | Unresolved class | Either retract or defend |

**Carry-over from the prior phase (still open):** funding carry as portfolio
option P08; weekly GHA for the portfolio tracker; maker-first entry test (R11 of
PART13).

---

## 9. WHAT I AM NOT CLAIMING

- Not claiming a profitable strategy exists. **Zero cells have forward
  observations.** Four cells survived BH-FDR on back-test data only.
- Not claiming the SPY breakout result is a 33-year edge — it is a post-2010
  effect (first-half t=0.47).
- Not claiming audit2/audit3 are wrong. One doctrine claim failed; their
  *verdicts* (0/67 proven) are consistent with everything I have measured.
- No capital sanctioned. This is not investment advice.
