# Per-class paths to profitability

One page per class. Format: **what is binding → what would have to be true → the specific test that
decides it.** Nothing here is a recommendation to allocate capital; it is the shortest honest route
to finding out whether a class can ever clear its own costs.

---

## CRYPTO — n=1,966, PF 0.768, −837.8pp

**Binding constraint:** nothing about signal selection. The stops fill 56% worse than placed
(+828.0pp of leakage against a −837.8pp total, 98.8% of the loss). Effective R:R is 1.08 against a
planned 1.69, which lifts the breakeven win rate from 37.2% to 48.0% while the class delivers 39.3%.

**What would have to be true:** fills at or near the declared stop. Not "better entries" — the same
entries, executed at the price the risk model assumed.

**The test:** re-resolve all 773 stopped crypto trades against intrabar OHLCV, filling at the stop
price when the bar's low/high breaches it, and at the bar close only when it gaps through. Gate:
realized loss median within 5% of planned risk. Expected outcome PF 0.768 → ≈1.00, i.e. breakeven.

**Then, and only then,** signal work: at PF 1.00 the class needs positive expectancy from selection.
The two candidates worth a forward test are CRYPTO POSITION (n=33, WR 69.7%, PF 3.18, +74.4pp) and a
strict rules-cut of `luxalgo_confluence` (the largest strategy in the ledger at n=1,278, PF 1.116,
t=1.72 — plausible but not significant, and the payload's own benchmark ledger scores it at n=1,211,
PF 1.0287, cumulative **−26.4%**, bootstrap pass **false**).

**Kill:** CRYPTO SWING. n=243, WR 28.4%, PF 0.457, −328.6pp. It is the worst bucket in the ledger and
39% of the class loss on its own.

**Do not expect rescue from structural edges at retail size:** the peer research program tested three
funding-carry variants (H21/H22/H23); the best, BTC-only, is 4.8% capital-adjusted CAGR with n=10
rebalances, and the diversified versions return 3.7–4.1% against 4.5% cash.

---

## EQUITY — n=738, PF 1.154, +238.3pp — the only class above water

**Binding constraint:** sample and stability, not structure. This is the only class with a positive
after-cost win-rate margin (+2.9pp: needs 44.1%, delivers 47.0%), stops that stay inside plan
(avg loss −0.84R), and a time-exit bucket that works (n=220, WR 61.4%, PF 1.988).

**What would have to be true:** the 2.9pp margin is real. Right now t=1.52 (p=0.12) and the second
half fell to PF 0.977, so it is a candidate, not a finding.

**The test:** extend to ≥2 years of the same rules, and benchmark against SPY rather than zero. Two
outcomes matter: if equity picks beat SPY's Sharpe at n≥500 with the half-to-half decay controlled,
this is the one class that can carry a paper allocation; if the margin sits inside the confidence
interval, the class is beta and should be replaced by an index.

Relevant peer evidence, and it is unflattering: the independent research program tested RSI(2) on
SPY/QQQ three ways — H7 Sharpe 1.50 vs 18.6% B&H, H10 Sharpe 1.83 (downgraded for contaminated OOS
and 2-day-lag Sharpe 0.696), H8 sector variant DSR 0.603. None beat buy-and-hold. Any equity
strategy here has to beat SPY, not zero.

**Note:** SPY and QQQ are miscategorised as EQUITY in `multi_asset_picks.json`; the class total
includes ETFs, which flatters it.

---

## ETF — n=567, PF 1.036, +22.9pp — exactly at zero after costs

**Binding constraint:** cost. Average slippage is 0.05% per trade against an average PnL of 0.0187%.
That means **one tick of assumed slippage consumes 267% of the average trade** — the system is
trading an instrument whose edge (if any) is an order of magnitude smaller than its cost.

**What would have to be true:** holding periods long enough that 5bp stops mattering. The peer
research already points the right way — ETF cross-sectional momentum (12-1, monthly, H16) produces
Sharpe 0.98 against a 1.18 benchmark, and ETF TSMOM breadth (H18) 1.00. Both are *monthly* strategies
being run here as intraday picks.

**The test:** stop emitting intraday ETF picks. Re-run as monthly rebalance, hold to next rebalance,
and gate on average PnL ≥ 3× round-trip cost. Expect most of the 557 intraday picks to disappear —
which is the point.

**Caution:** the payload's own intrabar check is brutal here — n=45, WR **2.22%**, PF **0.0216**
against a daily PF of 1.8358, an **85× inflation**. The published ETF "73.3% WR / PF 1.84" comes from
a 15-row policy_clean subset; the intrabar truth is 45 rows at PF 0.02. Do not trust the headline.

---

## FOREX — n=187, PF 0.634, −29.0pp — structurally impossible as configured

**Binding constraint:** reward-to-risk is inverted. Average win 0.69% against average loss 0.76%.
At 1:1 the class needs a 52.5% win rate before costs (55.3% after); it delivers 39.0%. It is
**13.5pp short before costs and 16.2pp short after** — the largest gap in the ledger.

**What would have to be true:** wins larger than losses. Either widen targets (planned median R:R is
1.50, which is adequate — the realized ratio of 0.91 says targets are being cut short or losses
allowed to run), or cut trade count to the setups that actually produce >1R.

**The test:** recompute on R-multiples after fixing exit handling; the class already keeps losses
inside plan (avg −0.67R, only 13.4% worse than −1R), so the problem is on the *win* side — median
realized win 0.63% against a planned R:R of 1.50 means winners are exiting at roughly 0.5R. Gate:
find why TP_HIT fills at 0.63% when the planned target implies ~1.5R. That single question probably
explains the class.

**Also:** FOREX carries the second-highest concentration risk (top-5 winners = 22.4% of gross), so
any future positive result needs n≥300 before it means anything.

---

## BOND — n=35, PF 0.586, −7.7pp — insufficient and probably wrong instrument set

**Binding constraint:** sample. n=35 with the top 5 winners producing 56% of gross profit is noise.
The intrabar truth set is n=26 at WR 7.69%, PF 0.3915, and `sizing_allowed: false`.

**What would have to be true:** a bond strategy traded at bond horizons. There is no duration model
in the codebase (peer finding, corroborated by hilarious-seer: "no specific bond duration or
fixed-income ML"), so the picks are equity-style signals applied to bond instruments.

**The test:** either build a duration/carry model (rate level + curve slope, monthly rebalance) or
declare BOND out of scope. Continuing to emit 35 equity-flavoured bond picks per 9 months produces
neither evidence nor profit. **Recommendation: declare out of scope.**

---

## COMMODITY — n=7 in the ledger, 229 intrabar, PF 1.026 — the only unexplored class with a sample

**Binding constraint:** two contradictory measurements, both thin. Ledger n=7 (PF 0.604, −4.2pp);
intrabar truth n=229 (WR 40.17%, **PF 1.0256**) against a policy_clean n=14 (PF 0.1718). Slippage is
flagged CRITICAL at 422% of average PnL.

**What would have to be true:** the 229-row intrabar set is the real measure and PF 1.026 is a floor
rather than a ceiling. That is the **only class in the system with n≥200 at intrabar truth and PF≥1**.

**The test:** a CFTC Commitments-of-Traders contrarian strategy at weekly frequency, which is the one
commodity family with a documented, low-cost, low-turnover basis — and the payload already has a
`commodity_cot_contrarian` sidecar in `sidecar_promotion_status`. Gate: OOS PF ≥1.15 at weekly
rebalance with slippage under 25% of average PnL, on n≥100 trades. This is the highest
information-per-dollar test available.

---

## MUTUAL_FUNDS — zero coverage

**Finding:** no mutual fund picks exist in any store (corroborated independently by flaxen-hair and
the finpredict family). **Recommendation: declare out of scope rather than building coverage.** These
are index products priced daily with no intraday edge; a system losing 0.176pp per trade on liquid
instruments will not find an edge in products that price once a day and carry fees.
