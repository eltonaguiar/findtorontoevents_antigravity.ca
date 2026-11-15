# Holding Periods & Trading Styles — Reality Check

Cost and noise dominate as the holding period shortens. This table is the single most useful reality check in the repo: **the shorter the hold, the more the edge must overcome.**

## 1. The cost wedge by style

| Style | Typical hold | Round-trip cost (retail, realistic) | Edge needed just to break even |
|---|---|---|---|
| Scalping | seconds–minutes | 0.05–0.20% (spread + fee + slip) | Very high; dozens of round-trips/week |
| Day trading | intraday, flat by close | 0.04–0.20% | High; needs HF infrastructure, not ML on OHLCV |
| Swing | 3 days – 3 weeks | 0.02–0.10% | Moderate; the only retail-viable short style |
| Position / tactical | 1–6 months | 0.02–0.05% | Low; rebalance cost amortised |
| Long-term / buy-and-hold | 1–10+ years | 0.01–0.05% | Essentially zero; beta does the work |

**Rule that follows:** at retail costs, every additional round-trip per year is a tax on the strategy. A daily strategy needs roughly 10× the per-trade edge of a monthly one just to tie it. This is why F5/F13/F21 all died at the friction step.

## 2. What the evidence in this repo says per style

| Style | Repo evidence | Verdict |
|---|---|---|
| Scalping | Not seriously tested; no tick data, no L2 book, no latency budget | **Not attempted** — do not claim it |
| Day trading | Daily-bar "day" tests only (F3, F25) — no intraday fills | Inconclusive at best; costs unmodelled at true intraday level |
| Swing | F3, F5, F21, F25, F26 — best near-misses live here | **Most promising** for retail scale |
| Position / tactical | F7, F8, F12, F16, F22, F27 | Mixed; several near-misses fail only on significance |
| Long-term | `Plan/mf_etf/`, `Plan/multi_asset/` | **Highest probability** of positive real return — beta, not alpha |
| Event-driven | F11 (token unlocks) — N too small | Needs years more data |

## 3. Named systems — with verification discipline

The temptation is to copy famous systems (Hoffman-style inventory retracement, dual momentum, CTA trend, Turtles) and declare them "proven." **Proven in someone else's market, with their costs, is not proven here.** Rules for citing any named system:

1. Cite the **original, primary source** (paper, book, published rules) — not a contest leaderboard snippet.
2. State the **market and period** it was demonstrated in.
3. Re-test it **here** with this repo's cost model and locked holdout before calling it a candidate.
4. **Never** claim a specific contest placement or parameter set unless the primary source states it. TradingView/other contest winner lists change and are frequently mis-cited — mark any such claim **UNVERIFIED** and re-test the strategy on its merits instead.

Systems worth re-testing on merit (each needs its own `run_id`):
- **Time-series momentum / CTA trend** (12-month look-back, vol-targeted) → `Plan/commodity/`
- **Dual momentum** absolute + relative (10-month SMA filter) → `Plan/etfs/`
- **Cross-sectional quality-momentum** → `Plan/equity/`
- **Carry** (FX, crypto funding) → `Plan/forex/`, `Plan/crypto/`
- **Inventory-retracement style supply/demand entries** → only after a proper intrabar fill model exists (currently F24/F25 show the fill model itself is the weak link)

## 4. What the style study implies for allocation

- Spend research effort on **swing and position** horizons — that's where the near-misses are and where costs are survivable.
- Treat **scalping/day trading as out of scope** until the repo has intraday data and a validated fill model. Claiming an intraday edge on daily bars is the most common self-deception in this space.
- The **long-term allocation** track (`Plan/mf_etf/`, `Plan/multi_asset/`) is the only path with a genuinely high probability of positive real return, because it doesn't require prediction at all.
- Any short-horizon candidate must show **edge / cost ≥ 3×** (the repo's own `REQUIRED_COST_MULTIPLE`) before it's worth a worktree.
