# Top "proven" / famous algorithms — evidence-ranked

> Sources: `../07_industry_case_studies/research_raw.md` (live-web-sourced, links inline
> there) + SubQ's independent evidence scores (`../subq/factcheck.md` q5). **Evidence
> classes: ACADEMIC (peer-reviewed replication) · REAL-MONEY (audited/statement-verified
> track record) · FOLKLORE (popular, no credible evidence).**

## Tier 1 — Academic + real money (SubQ evidence ≥4.0/5)

| Family | Originator | Core rule | Evidence | Failure modes / decay |
|---|---|---|---|---|
| **Trend following (Donchian/Turtle/TSMOM)** | Donchian; Dennis & Eckhardt 1983 | N-day breakout entry/exit (20/55), ATR sizing | AQR century-of-evidence: positive every decade since 1880; Moskowitz/Ooi/Pedersen 2012: significant in **all 58 liquid instruments** | Whipsaw in ranges; post-2008 decay on small-tick contracts; Turtle's claimed 80%/yr NOT replicated (NTU) |
| **Momentum factor** | Jegadeesh & Titman 1993 | Long 3–12m winners, skip month | t≈3–5 originally, widely replicated | Momentum crashes; **2000–2024 pre-registered modern replication = honest null** (repo cited in research_raw) |
| **Carry** | fixed-income/futures practice | Harvest roll/interest yield, crisis-unwind protection | Strong academic + CTA real money | Crisis unwinds (2008, Mar-2020, Aug-2024): the tail is the strategy |
| **Volatility risk premium** | option markets | Sell OTM vol, harvest premium | Documented decades of premium | Crash tails (Feb-2018, Mar-2020, May-2021) — size is everything |
| **Market making** | intermediaries | Bid-ask spread capture + inventory mgmt | SubQ 4.57/5 (strongest); real firms (Jump, Optiver, XTX-class) | **Not retail-reachable**: co-location, inventory capital, adverse-selection risk |
| **Value factor** | Fama & French 1992 | Long high B/M | Academically replicated | **Weak/absent since ~2007**; AQR's own "painful period" 2017–2020 — but AQR's public turnaround (+43.5% 2022) shows thesis-persistence pays |

## Tier 2 — Contested / regime-dependent (SubQ 3.4–3.8)

| Family | Verdict | Key fact |
|---|---|---|
| **RSI(2) short mean reversion** (Connors) | Contested — results **flip on costs/universe** | Positive OOS Sharpe 0.56–0.78 net (EdgeLab NQ 2010–2026) BUT other tests: net CAGR −0.7%, only 27% of 1,791 OOS tests beat B&H |
| **Ichimoku** | Mixed — academically tested | Profitable subperiod 1 (1995–2018), "failed to create values consistently" subperiod 2 (Deng 2021) |
| **Pairs/stat-arb** | Was academic, capacity-decayed for retail | |
| **Dual momentum / Faber QTAA** (note: "Fabry" NOT FOUND — likely Faber/Antonacci confusion) | Practitioner evidence, independent tests, **not peer-reviewed** | Absolute+relative momentum with cash episodes; transaction costs decide it |
| **Opening range breakout / Darvas / Minervini** | Partial support + decay | Umeå: full-sample profitable but **not robust across sub-periods**; Darvas's $2M claim officially contested (NY AG: $216k ascertainable); Minervini US Investing Championship 1997 +155%, 2021 +334.8% (statement-verified) |

## Tier 3 — Retail folklore (SubQ ≤1.1/5): **do not build on these**

| Family | Evidence |
|---|---|
| **ICT / FVG / order blocks / "smart money"** | **0 of 648 backtests beat buy-and-hold net** (StatOasis, SPY/QQQ/DIA/IWM); arXiv: AMD model shows "no directional information beyond the daily trend" |
| **Typical TradingView indicators** (SuperTrend, Bollinger squeeze, LazyBear Squeeze Momentum, Williams %R) | Popularity only. **TradingView has NO official trading-performance contest** — "Pinefest" is a *programming* contest ($500, code-quality judged; winner alexgrover). Strategy Tester = backtest, not track record |
| **VWAP as a signal** | VWAP is a legitimate *execution benchmark* (academically grounded); price-above-VWAP ⇒ long has no peer-reviewed edge — and this repo's own audit falsified the VWAP strategy twice |
| **TTM Squeeze (John Carter)** | Book-derived retail pattern; no peer-reviewed evidence |

## "Hoffman" — resolved (the user's question)
**Rob Hoffman** ("Become A Better Trader") — markets himself as **7× International Trading
Champion, 37 live competition wins, 25th real-money win Rimini 2017**; format =
single-elimination front-of-audience with **verified live accounts** (Infinity Futures
2011 beat John Carter, Heitkoetter et al.; Salon du Trading Paris €50k judges-verified).
**Caveat: counts are self-reported via paid PR releases; no independent audit found.**
No "Hoffman" TradingView indicator/strategy exists (NOT FOUND). Full candidate table:
`../07_industry_case_studies/research_raw.md` §A2.

## Real-money contest winners — and what happened after (the lesson)
- **WCTC (since 1983/84, statement-verified real money):** Larry Williams 1987 = **11,376%**
  (record); Michelle Williams 1997 = 1,000%; Andrea Unger 2008 = 672%; 2024 Brent Carlile
  = 532%; 2025 Tirutrade 324.7%.
- **Winners themselves debunk repeatability:** Unger: *"I would be a liar"* if I claimed
  672% yearly (competition risks 20%/trade vs 1–2% sound sizing; he sat −47% drawdown);
  Kevin Davey: *"one copper trade… without that trade I would not have won."*
- Median champion needs ~11%/month compounded — i.e., **contest-winning = variance
  selection**, exactly the mechanism `../05_prediction_market_copytrading/` warns about.
- US Investing Championship itself needed a credibility repair (1996 SEC investigation of
  the operator; restarted 2018).

## What this means for our system
1. **Build only on Tier 1 families** — trend (commodity/crypto trials), short reversal
   (equity trial), momentum (MF/ETF sleeve). Each already carries the evidence burden we'd
   otherwise have to pay for ourselves.
2. **Tier 3 patterns are banned** as primary signals (they're fine as *features* inside a
   pre-registered Tier-1 test, counted as trials).
3. **Contest wins are not evidence** — treat any "proven by competition" claim the way we
   treat backtests: statement-verified, costs-included, n-disclosed, or it didn't happen.
4. Our own gate stack (pre-registration → OOS → costs → benchmark → forward) is *stricter
   than every contest above* — that's the point: contests select for lottery tickets,
   capital requires selection against them.
