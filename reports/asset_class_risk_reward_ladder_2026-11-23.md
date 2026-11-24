# The ladder: what is stable, what pays, and what could actually be proven

**2026-11-23 · paper only · zero capital sanctioned · not investment advice**

The right way to run money is boring-first: hold something stable, prove the small improvement on
it, then climb. This memo orders everything the programme has measured into that ladder, states
what each rung is worth, and says exactly what evidence would promote it. Every number below comes
from an artifact in this repo; the claim IDs are in `reports/claim_register.json`.

---

## Tier 0 — The risk control that replicated, and the return gain that did not

**Volatility-targeted 60/40.** C-014, 2005-01-03..2026-11-20, SPY/TLT, 5 bp/unit turnover, leverage
from *yesterday's* realised 60-day vol, cap 2x:

| | CAGR | vol | Sharpe | max DD | certainty equiv |
|---|---|---|---|---|---|
| plain 60/40 | 7.85% | 10.87% | 0.750 | −31.42% | 7.55% |
| 60/40 vol-target 10% | **9.28%** | **10.53%** | **0.895** | **−22.37%** | **8.87%** |

That is +1.43 pp CAGR, lower vol, and a drawdown cut by 9 pp — from a rule with no forecast in it.
C-008 reproduces the same mechanism on SPY alone (maxDD 21.0% → 11.4%, CAGR 8.38% → 6.64%): the
drawdown half is real and repeatable, the return half is not free.

**Read it correctly:** this is risk control, not alpha. It does not beat buy-and-hold SPY on
absolute return (7.31% vs 10.30% when applied to a single asset — C-014), and its drawdown benefit
is **granularity-dependent**. The −22.37% vs −31.42% pair above is the **monthly**-rebalanced basis
(verified against the artifact); a genuine **daily** reset gives −22.03% vs −30.04% on the full
sample, plain CAGR 8.16% and vol-target 9.39%. Rebalance frequency must travel with the number — an
earlier version of this memo quoted a “daily” figure that was in fact a never-rebalanced book.

### H-233: I tested this properly and it failed on the return half

I pre-registered the replication (`plans/2026-11-23-prereg-H-233-vol-target-replication.md`), filed
it in the registry, and ran it before looking — then reported the verdict the rule pointed at.

| window | plain CE | vol-target CE | ΔCE | 95% CI | plain CAGR → VT | max DD plain → VT |
|---|---|---|---|---|---|---|
| A 2005-2015 | 7.64% | 9.67% | **+2.03pp** | [−0.81, +4.84] | 7.94% → 10.15% | −30.04% → −21.12% |
| B 2016-2026 | 8.05% | 8.28% | **+0.23pp** | [−2.52, +2.89] | 8.38% → 8.63% | −27.29% → −22.03% |
| FULL (diagnostic) | 7.84% | 8.98% | +1.14pp | [−0.87, +3.09] | 8.16% → 9.39% | −30.04% → −22.03% |

**Verdict: `REFUTED_OOS`, on criterion 2 only.** With the basis bug fixed (see below) the point
estimate is **positive in both windows** (+2.03pp and +0.23pp) and the sign now agrees — but the CI
contains zero in every window, including the full sample (+1.14pp, [−0.87, +3.09]). So this is a
**power** failure, not a sign flip: the effect is roughly a fifth of the interval width. The
pre-registered rule still fires, because criterion 2 (CI lower bound > 0) was written in advance and
I am not moving it. I also do not switch to the monthly basis: its point estimate is larger
(+1.32pp) but it was never bootstrapped, so calling it a pass would be an overclaim.

**What survives, and it is not nothing:** the drawdown reduction appears in **both** windows (−30.04
→ −21.12 and −27.29 → −22.03) and criterion 3 passed. H-235 then tested it outside this sample:
it held in all three books tested (−9.21 → −8.99 pre-2005, −30.04 → −22.03 US 2005-2026,
−42.61 → −28.22 non-US), though the pre-2005 margin is 0.22pp and therefore says nothing, and in
the ex-US book the drawdown gain cost real return (CAGR 2.95% → 1.35%). So the honest tier-0 recommendation is now
**"risk control only — no demonstrated return gain"**. It reduces drawdown; it does not reliably pay
you for it. C-014's "raises CAGR" does not generalise, and this memo's earlier claim that the stable
rung had a +1.43 pp tailwind is **withdrawn**. The full-sample daily ΔCE CI [−1.03, +3.00] also
contains zero, so even the original point estimate was never statistically distinguishable.

**Why it is still Tier 0:** it is the only rung whose *risk* effect replicated on data disjoint from
where it was found, the mechanism is arithmetic (constant risk instead of constant weights), and the
cost is 5 bp/unit — orders of magnitude below every cost floor here. And it remains the honest answer
to "give me something relatively stable": the stability is the deliverable, and it is now the *only*
deliverable.

**What would promote it back:** another disjoint window (pre-2005, or non-US books) where the CE sign
agrees, or a forward clock on the overlay alone. Not a different rebalance convention.

**HRP as the risk-only variant** (C-020): vol 8.87 vs 10.28 and maxDD −17.79 vs −28.45 versus
60/40, but its certainty equivalent does **not** beat 60/40 — 0 of 5 paired bootstraps exclude zero
(HRP −1.93, CI [−4.82, +0.93]). Sell it as lower risk, never as higher return.

---

## Tier 1 — One cell with a real number, blocked on time not on skill

**EQUITY H-201, cross-sectional 6-month momentum, top 3 of a broad universe.** CI-LB
**+7.246 bp/day** over 3,744 days, 179 trades. Cost is irrelevant here: the floor is a **614 bp**
round trip (30.7x the assumed 10 bp) — C-017.

It is `NOT_PROVEN` for two arithmetic reasons, not for a bad result (C-019, C-024; both figures
**corrected by C-029** on 2026-11-23):
- **Multiplicity:** DSR **0.9469** at N=29 against a 0.95 bar — and **0.9490 even at N=28** once
the series' own skew (−0.050) and kurtosis (12.254) are in the denominator. The cell therefore
  clears only at **N ≤ 27**, while 30–31 trials are declared. The effective trial count is ~25
  (band 20–30), so the pass boundary sits *inside* the uncertainty band — unresolvable at this
  sample size.
- **Data margin:** needs 0.073872 daily Sharpe, has 0.073600 — **137 more trading days** at N=29
  (232 at N=30, 327 at N=31). C-019's 76.7 days used a normal-returns denominator; the measured
  kurtosis of 12.254 widens it to 1.0094.

And the honest ceiling: on a survivorship-free universe it may not survive. The 44-name PIT
universe meets the count bar but is `PARTIAL_NON_DELISTING_AWARE`, so the pod caps its verdict at
`CANDIDATE_SURVIVORSHIP_FLAGGED`. The vol-matched CI-LB is **−0.533**: when scaled to SPY's
volatility the excess goes *negative*, which is what a beta proxy looks like (C-022).

**What would promote it:** **137** forward trading days at the same effect size (corrected from 77
by C-029; the pod is day 15 of a 20-day gate, and that gate is a clock check, not a significance
test), and a non-overlapping second universe. Both are already specified; neither can be hurried.


---

## Tier 2 — Positive numbers that are not edge

**ETF and INDEX** both have positive CI-LB and **negative excess versus their own benchmark**
(C-016). They are the asset class doing the work, not the signal. Their cost floors (165 bp, 73 bp)
are comfortable, which is exactly why the failure cannot be blamed on cost.

**FUTURES** is the opposite: CI-LB 0.186 bp/day against an 18 bp floor (**1.8x**) — cost binds
immediately. Its MDE is 4.32 bp/day, so the cell is at its own detection limit.

---

## Tier 3 — Real mechanism, zero allocation

**Delta-neutral funding carry.** 1.9252 bp/day measured across 5 coins, 2,152 days (C-010/C-013/
C-018). The construction was corrected to a quantity-matched book: net delta is zero by algebra,
rehedge drag is **0.0 bp/day**, and cash crossings are 111 / 71 / 32 days for taker / maker-entry /
maker-both. On paper that is the best risk-adjusted thing in the programme.

It stays at **0%** for two reasons that are not statistical:
1. **The fee tier.** The whole result rests on VIP0 maker 2 bp / taker 5 bp; adverse-selection
   budget survives only to ~5 bp/fill (73 days) and is worse than taker above ~7 bp/fill.
2. **Funding decay.** The carry's sign is persistent, not iid (P(neg|neg)=0.666), and the obvious
   overlay is priced and dead: exiting on negative funding avoids 1,738 bp and costs 15,440 bp.

**CRYPTO momentum** is the high-vol cell: 43% vol, MDE 11.48 bp/day, **632 years** of daily data to
detect a 1.92 bp/day effect. BTC buy-and-hold did 49.1% CAGR with Sharpe 0.911 — but with an −83%
drawdown, and that is beta, not a pick (C-005).

---

## Tier 4 — Untouchable, and the reason is arithmetic

**PENNY_STOCK**: MDE 19.73 bp/day, **1,572 years** of daily data to detect a tradable effect, and
its universe is a seed list with no volume history, so a liquidity haircut would refine a number
that cannot be trusted.

**COMMODITY**: `DATA_INTEGRITY_FAIL`, not an economic refutation — CL=F has a negative print and 55
moves >8%, NG=F has 25 roll spikes. **MEME**: cost unmeasurable (SHIB had 53 distinct highs across
7,135 bars and 84.3% zero-range bars). You cannot prove anything about a class whose price series
is not a price series.

---

## The one table that decides everything

MDE versus CI-LB, per class (from `reports/2026-11-22-cost-floor-and-power.md`):

| class | MDE (bp/day) | CI-LB | at detection limit? |
|---|---|---|---|
| EQUITY | 7.17 | 7.246 | **yes — CI-LB ≈ MDE** |
| CRYPTO | 11.48 | 8.452 | yes |
| ETF | 4.86 | 2.007 | yes |
| INDEX | 4.63 | 1.613 | yes |
| FUTURES | 4.32 | 0.186 | yes |
| BOND / FOREX / COMMODITY / PENNY | 1.98 / 2.50 / 2.60 / 19.73 | negative | no — already negative |

**18 of 40 cells have a CI lower bound below their own detection limit.** If the true effect is
1.92 bp/day (twice the cash hurdle), the years of daily data needed are: BOND 15.8, FOREX 26.2,
COMMODITY 27.2, MUTUAL_FUND 73.7, FUTURES 75.4, INDEX 89.7, ETF 95.5, EQUITY 207.5, CRYPTO 632.7,
PENNY 1,572.

**That is the answer to "find us an edge": more years will not do it.** The response is more
independent observations per year — event-driven / per-trade sampling (H-201's n=179 trades, not
15,000 daily means) — or a question whose effect is larger than 1.9 bp/day.

---

## How a quant would actually prove the next thing

The programme's failure mode has been claiming a win that a paired test could not support, so the
proof standard is fixed and non-negotiable:

1. **Pre-register before the first run** (rule M-107). H-232 is the model: registered, committed
   (`b9ff7faab3e`), *then* run — and it came back negative (−1.826 bp/day, CI [−2.754, −0.922]),
   which is what an honest test looks like.
2. **Paired bootstrap CI on the DIFFERENCE vs the class's own benchmark.** A positive CI-LB alone
   is how ETF and INDEX got called signals while underperforming their own index.
3. **Cost at measured levels, with the floor disclosed.** k* = cost multiple at which CI-LB hits
   zero; if k* < 1.5 the cell is a cost question, not an edge question.
4. **Multiplicity charged at the effective trial count (~25), not at 1.** The family has already
   been charged; a new cell raises N.
5. **A pre-registered kill rule** on forward rows only, CI-LB ≤ 0.
6. **Report the vol-matched number beside the raw one, always.** H-201's raw +7.246 and matched
   −0.533 are the same cell.

## What to do, in order

1. **Compute nothing new on the stable tier.** Ship the vol-target 60/40 *as risk control*, state
   the rebalance frequency, and hold it. It is the only thing that passes a test today.
2. **Let H-201's clock run.** Day 15 of a 20-day gate; 77 days to a verdict. Five more sessions
   before it is even allowed an opinion. Buying delisting-aware data is what would let that
   verdict be a PASS instead of a flagged candidate.
3. **Do not touch crypto carry until the venue fee tier is a measured number**, not a published
   assumption.
4. **Stop testing PENNY, MEME and COMMODITY** until their price series pass a data-integrity gate.
   Effort there produces noise with a p-value attached.

**The honest summary a fund manager should take from this:** the stable rung's *risk* effect is
real and replicated on disjoint data, while its *return* effect did not (H-233, `REFUTED_OOS`: the
certainty-equivalent gain changes sign between sub-periods and both CIs contain zero); the profitable-looking rungs are either beta, blocked on time, or blocked on
data; and the largest remaining lever is not a better model, it is a delisting-aware universe plus a
measured venue fee tier. Buying those two datasets is worth more than any further backtest in this
repo.

---

## Cross-check against the peer measurement (copilot, `notes/asset-class-risk-edge-copilot-20261123`)

The same question was answered independently on the bus with 79 symbols and 5 years of daily bars,
reporting per-class medians. Where the two measurements disagree, theirs is the better risk
measurement and I take it.

| class | peer: vol / maxDD / return / Sharpe (n) | this memo's claim | verdict |
|---|---|---|---|
| CRYPTO | 68.5% / −87.8% / −14.9%/yr / −0.21 (15) | most risky, 43% vol, −83% MDD | **agree — most risky on both axes** |
| EQUITY | 34.7% / −52.0% / +10.5%/yr / 0.29 (20) | 43%-vol neighbours, beta proxy | agree |
| COMMODITY/FUTURES | 24.6% / −41.1% / +5.7%/yr / 0.22 (10) | data-integrity fail | agree on risk; my rejection is data quality, not volatility |
| ETF | 16.2% / −25.9% / +4.4%/yr / **0.44** (24) | positive CI-LB, negative benchmark excess | **both true — see below** |
| FOREX | 8.8% / −16.1% / −0.2%/yr / −0.03 (10) | CI-LB negative | agree; and it corrects my "BOND is the stable rung" phrasing |

**Where they corrected me.** I ranked BOND first for stability on an unmeasured basis. Their point is
the right one: lowest volatility with zero or negative return is not safety, it is slow, and the
comparison every class must clear is T-bills at the 4.32% hurdle, not another asset class. FOREX at
8.8% vol and −0.03 Sharpe is the clearest example.

**Where I think the ranking is being read one step too generously.** ETF's Sharpe 0.44 is the
**asset's** risk-adjusted return, not a signal's. A buy-and-hold ETF is 100% beta by construction,
and this programme already made that mistake once: ETF and INDEX show positive CI-LB (2.007 and
1.613 bp/day) while running **negative excess against their own benchmark** (C-016). So "best
risk-adjusted class" is a reason to *hold* ETFs and a reason to be *cheap* about trading them; it is
not evidence of an edge. Ranking a class by its Sharpe is ranking the beta, and the whole point of
the exercise is to find what is left after beta.

**Their proposed ETF trend rule — the hole in the kill rule.** "annualised net ≤ 4.32%" is a cash
hurdle. A rule that is long SPY 90% of the time passes it on beta alone while contributing nothing.
The gate needs two hurdles, not one: net > 4.32% **and** a paired bootstrap CI on the difference vs
buy-and-hold SPY that excludes zero. The second is the one that tells you whether the *signal* did
anything, and it is the rule this programme adopted precisely because a positive CI-LB alone already
misclassified two classes.

**On the multiplicity debt.** We agree it is the binding constraint and we agree that forward-only
testing is the only escape. The sizes differ because the families differ: they count 146 declared
hypotheses at σ_SR 0.439 annualised; my near-miss cell runs at 29 declared trials with
√var_sr = 0.0228 daily (≈0.362 annualised — the same order). Going from 29 to 146 trials multiplies
the expected-max-Sharpe term by roughly 1.3x, so "146 trials" sounds catastrophic and is bounded; the
real reason 0/55 survive is that their cells have annualised Sharpe *below* the deflated bar, not
that the bar exploded. That is a different diagnosis with a different remedy: it argues for fewer,
larger effects, exactly as this memo's arithmetic section says.
