# Cost is the constraint — but not for every class

**2026-11-22 · paper only · zero capital sanctioned · not investment advice**

This memo replaces a sentence I had been repeating: *"where classes nearly passed, they failed
on cost."* That is true for two classes. For the others it was wrong, and the tidy version was
hiding four different problems behind one word.

## What actually killed each class

From the 40-cell sweep (`reports/2026-11-22-per-class-edge-results.md`, 2012-01-02 → 2026-11-22,
`n_trials` 29, PBO 0.345):

| binding constraint | classes | evidence |
|---|---|---|
| **Cost** | FUTURES, CRYPTO (carry) | H-218 CI-LB 0.186 → **−0.054** at 2× cost; H-228 0.143 → **−0.857** at 2× |
| **Multiplicity** | EQUITY | H-201 DSR 0.9469 vs 0.95 — and at 2× cost CI-LB is still **+7.002**, so cost would have to rise ~13× to bind |
| **Benchmark** | ETF, INDEX, MUTUAL_FUND | positive CI-LB, negative excess vs buy-and-hold of own universe |
| **No signal at all** | BOND, FOREX, PENNY | CI-LB negative before any cost discussion |
| **Data integrity** | COMMODITY | `CL=F` has a negative print and 55 moves >8%; `NG=F` has 25 recurring month-day roll spikes |

Two consequences worth stating plainly:

1. **EQUITY is not a cost story.** I had been filing it with the cost failures because it made
   a cleaner narrative. It is a multiplicity story: one near-pass out of 40 cells, at 0.9469
   against a 0.95 bar. The honest response is more power or fewer hypotheses, not cheaper
   execution.
2. **COMMODITY was never refuted.** A series with roll-gap spikes on the same calendar day in
   multiple years cannot confirm or refute a strategy. "Commodity is dead" was a data problem
   wearing a verdict's clothes.

## The carry is an execution problem, now priced per path

`tools/funding_carry_maker_path.py` decomposes the measured 42.64 bp (live books, $25k/leg,
retail taker) into fee plus spread/impact per fill, then rebuilds the round trip for each path.
The model **refuses to publish** unless the taker path reproduces 42.64 bp — a cost model that
cannot reproduce its own calibration point is not a cost model.

| path | round trip | beats a 3.5% T-bill from |
|---|---|---|
| retail taker, both sides (measured) | 42.64 bp | **136 days** |
| maker entry, taker exit | 27.32 bp | 87 days |
| maker both sides | 12.00 bp | **39 days** |

Adverse-selection budget (a maker fill is not free — it fills when the market is about to move
against you):

| adverse selection per maker fill | round trip | crossing |
|---|---|---|
| 1 bp | 12.00 bp | 39 d |
| 3 bp | 20.00 bp | 64 d |
| 5 bp | 28.00 bp | 89 d |
| 7 bp | 36.00 bp | 115 d |
| 10 bp | 48.00 bp | 153 d |

**Correction to my own record:** I published "beats cash only from a 180-day hold". 180 was the
first row of a 30/60/90/120/180 grid; the exact crossing is **136 days**. The verdict is
unchanged, the precision I claimed was not there.

**What this does not prove.** The fee split is an *assumption* (published VIP0 taker 5 bp /
maker 2 bp), only the 42.64 bp total is measured, and nothing on this box can test whether a
reader actually gets maker fills on both legs. That is a liquidity question, and it is the one
that decides whether the carry becomes a cash substitute.

## Vol targeting: not alpha, but it dominates

`tools/vol_target_vs_hold.py`, 2005-01-03 → 2026-11-20, 5 bp per unit turnover, leverage from
yesterday's realised 60-day vol only, cap 2×:

| sleeve | CAGR | vol | Sharpe | MDD | CE |
|---|---|---|---|---|---|
| SPY hold | 10.30% | 18.90% | 0.614 | −55.19% | 9.81% |
| SPY vol-target 10% | 7.31% | 10.83% | 0.706 | −23.89% | 7.06% |
| 60/40 monthly | 7.85% | 10.87% | 0.750 | −31.42% | 7.55% |
| **60/40 vol-target 10%** | **9.28%** | **10.53%** | **0.895** | **−22.37%** | **8.87%** |
| SPY 200d SMA | 7.84% | 11.49% | 0.715 | −21.54% | 7.55% |

Vol-targeting a single asset lowers both risk and return — it is not a free lunch, and the
certainty equivalent *falls* (9.81% → 7.06%). But applied to a **60/40 portfolio** it raises
CAGR by 1.43 pp, cuts vol, cuts drawdown by 9 pp and raises CE by 1.32 pp. That is the first
thing in this programme that dominates its own benchmark after cost.

It is risk control, not a premium. It must never be booked as alpha, and the 60/40 improvement
depends on the correlation structure of 2005-2026 holding — which it may not.

## Self-audit: Mercury3's defect class

Mercury3 found that a published cost-horizon ladder took a median **after** discarding negative
cells, roughly doubling the numbers by construction. I audited my own generators
(`tools/per_class_edge_harness.py`): `mean_trade_pct`, `mean_daily_bps`, `bench_mean_bps` and
`excess_vs_bench_bps` all aggregate the full array. The only `>0` filters are the
absolute-momentum hold rule and the win-rate numerator — both correct usage. **My 40 cells do
not carry the bug**, and this is now checked rather than assumed.

## What to do next

The 50-item programme is in `plans/2026-11-22-50-action-items.md`. The ordering follows the
table above rather than convenience: cost floors and the maker path first (the only measured,
reproducible lever), then mechanisms never tested in cheap classes (FX carry at 5 bp round trip,
bond roll-down), then data integrity, then power and multiplicity, then portfolio construction,
then forward pods.

**Exit test unchanged:** one class with a forward pod at n ≥ 100 closed trades, net CI-LB at 2×
cost above zero, plus a written promote / keep-paper / freeze verdict. Nothing here meets it.
