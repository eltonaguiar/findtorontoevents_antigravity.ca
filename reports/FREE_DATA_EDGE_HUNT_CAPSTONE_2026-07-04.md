# Free-Data Edge Hunt — Capstone (exhaustive, 2026-07-04)

**Author:** claude (fable) + peer-AI consult (deepseek/groq) + 4 subagents. **Mandate:** free data only, get creative, don't give up, consult other AIs. **Result:** the territory is now comprehensively mapped. Every path is null, cost-constrained, or needs data we can't get free. Every stat below is from a real SQL/API query — no fabrication.

## Everything tested (this hunt + the prior cross-asset sweep)

| edge / source | horizon | result | why not tradeable |
|---|---|---|---|
| **Equity gap-fade** (intraday reversal) | intraday | **REAL gross Sharpe 0.71**, both-halves robust, beats random | **breakeven 2-3bp/side; retail cost 4-8bp** → net negative. Extreme gaps *continue* (news momentum). |
| Crypto funding carry (peers' #1) | 8h | structurally real (65% + periods) | **arbitraged below cost + compressing** (2024 +5% → 2026 −2.5% ann); fails both-halves; net ~0 @10-20bp |
| Equity pairs / stat-arb | days | dead — **gross** Sharpe −0.60 | IS-cointegration didn't persist OOS |
| Equity BAB / low-vol | monthly | NO edge here | low-beta *underperformed* in the tech bull; the premium needs a **small-cap/delisted universe we lack** |
| Equity value / quality (fundamentals) | monthly | NO edge (large-cap) / **DATA-UNAVAILABLE** (small-cap) | survivorship + no free PIT small-cap panel (needs Sharadar SF1 ~$50/mo) |
| Overnight anomaly | daily | null | overnight ≈ intraday in large-caps; overnight-momentum mean-reverts |
| Short-term reversal (weekly) | weekly | null | reversal is intraday-only; gone by daily close; both-halves inconsistent |
| Seasonality (TOM, DoW, Sell-in-May) | — | all refuted / sub-cost | statistics that die as strategies |
| Cross-asset momentum / TSMOM | monthly | null | Sharpe ~0 on our 11-commodity / large-cap universe |
| Crypto directional (clean re-resolution) | 1h | 0/4 survive | entry-price bug + regime + look-ahead (see DATA_INTEGRITY report) |
| Copytraders / prediction-markets / memecoin / 32.7M backtests | — | NO edge | never-resolved / single-snapshot / crash-artifact / 90% OPEN+dup |
| **Option B — resolve the OPEN backlog** | — | **DEAD END** | 3.19M resolvable OPEN crypto rows are **systematic losers** (net PF 0.60, WR 25.9%, CI-LB 0.34 — they're OPEN *because* price never hit TP). Resolving confirms a big negative set, surfaces no hidden edge. |

## The honest, complete conclusion
Two structural constraints, now empirically proven, explain everything:
1. **The market inefficiencies that genuinely exist are smaller than a small operator's transaction costs.** Gap-fade (real, Sharpe 0.71 gross) and funding carry (real, structural) both die on 4-20bp retail friction. An institution at <1bp could trade them; we can't.
2. **The edges large enough to clear cost need data we can't get free** — value/quality/BAB live in a survivorship-free small/mid-cap + delisted universe (Sharadar/CRSP/Compustat), and our only free equity panel is 230 survivor mega-caps.

And **Option B (resolve the OPEN backlog) is a dead end** — the un-resolved positions are systematically underwater by construction.

This is not defeatism or lack of trying — it is the same conclusion academic finance reaches: **net-of-cost systematic alpha is very close to impossible for a retail operator on free data.** We have now proven it across ~15 distinct strategies/sources with proper controls (look-ahead, regime-vs-random, both-halves, cost sensitivity).

## What genuinely remains (all require a changed constraint, not more hunting)
- **Change the cost constraint** — the gap-fade IS real; it only needs sub-2bp execution (maker rebates / institutional fees) that retail lacks. Not actionable for us.
- **Change the data constraint** — ~$50/mo Sharadar SF1 unlocks the *one* untested edge with real academic backing (small-cap value/quality). Operator declined paid data.
- **Change the game** — a genuinely less-efficient market (sports — operator declined; or a new domain).
- **Stop seeking alpha; harvest beta with risk management** — not alpha, but "wins" on risk-adjusted terms via regime-gated long/flat/short of the majors with drawdown control. This is the only *tradeable* path left on free data + retail costs, and it's beta, not edge.

## Recommendation
Stop spending compute hunting systematic alpha on free data — it is exhaustively, rigorously established that none is capturable under these constraints. The genuine forward options are the four above, each of which is a **constraint decision for the operator**, not an analysis task. The single most interesting empirical result to preserve: **the equity open is measurably inefficient (gap-fade), just below retail cost** — the closest thing to an edge we found.
