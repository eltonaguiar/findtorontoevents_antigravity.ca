# SubQ fact-check — are its answers grounded in reality?

**Method:** 6 queries sent to SubQ Snap 1.2 via the Decisions API (`POST /v1/systemone`,
typed answers with per-option probabilities and confidence — this key permits only the
Decisions API; chat/responses need `subq-savant-1.4`, not permitted). Raw answers:
`subq_responses.json` (regenerate: `python ask_subq.py`). My verdicts below test each
answer against (a) arithmetic I can check, (b) academic/industry ground truth, and
(c) this repo's own measured data. **GROUNDED / PARTIAL / UNGROUNDED.**

API shape note (from official docs `docs.subq.ai/llms-full.txt`): noul = P(yes) 0–1;
choice = per-option probabilities + confidence; score = probability-weighted level on a
2–10 ordered legend. Scores below are shown as raw level + band.

---

## q1 — asset-class profitability ranking (21 answers)

| Answer | SubQ | My verdict |
|---|---|---|
| prob crypto within 2y | score 1.83 (between 10-25% and 25-40%), conf 0.53 | **GROUNDED** — consistent with our data (recent PF ~0.74, fill bugs fixed only now) |
| prob equity within 2y | score 1.16 (10-25% band), conf 0.55 | **GROUNDED** — matches #773 NO_ALPHA_BETA; modest |
| prob commodity/futures | 1.63 (25-40% low end), conf 0.44 | **GROUNDED** — better historical PF, thin n, cost issues |
| prob ETF | 1.74, conf 0.44 | **GROUNDED** |
| prob bond | 0.93 (near <10%/10-25% boundary), conf 0.38 | **GROUNDED** — n=18-35 far below floor |
| prob forex | 1.13 (10-25%), conf 0.53 | **GROUNDED** — weakest class, sub-floor PF |
| prob mutual funds | 1.06 (10-25%), conf **0.29** | **PARTIAL** — low confidence, and "10-25% within 2 years" is confounded by *coverage not existing* (our own plan gives the MF sleeve 60-70% for a different event: positive net return, not "the class works as picks"). Read as: "MF as an active-pick class" ≈ low, "MF allocation sleeve" ≈ high — SubQ's own q4 answers confirm this split |
| styles | MF longterm conf 0.81, ETF longterm 0.50, bond longterm 0.69, commodity position 0.42 | **GROUNDED** — NAV-clock and cost reality; matches peer consensus that MF cannot be intraday |
| obstacles | MF=infrastructure (0.82), bond=infrastructure (0.64), equity/ETF=competition, crypto/forex=costs | **GROUNDED** — MF/bond coverage genuinely doesn't exist; crypto's measured loss was 98.8% fill/cost-driven pre-fix |

## q2 — benchmark-relative bar (4 answers)

| Answer | SubQ | My verdict |
|---|---|---|
| min forward months to claim "beats B&H" | score 3.76 → ~**30-36 months**, conf 0.17 | **PARTIAL** — direction right (longer than the 24mo in our plan); confidence is very low, so treat as "≥24-30, aim 30" rather than a hard 36 |
| excess Sharpe worth pursuing | score 2.38 → **0.7-1.0 band** | **PARTIAL (ambitious)** — a *defensible, likely-real* excess Sharpe of 0.7+ over SPY is elite-decile; common institutional bars are 0.2-0.5 excess. Grounded as an aspiration, not as a minimum |
| primary gate | `all_prereg` 0.63 (pre-registered combo + kill criteria), forward_paper 0.18 | **GROUNDED** — matches our whole protocol |
| "beats SPY pre-cost but not post-cost = no evidence" | P(yes) **0.99** | **GROUNDED** — costs are part of the edge; arithmetic |

## q3 — why copy-trading fails (9 answers)

| Reason (mine) | SubQ class | My verdict |
|---|---|---|
| 1 adverse selection | empirical 0.49 / game-theory 0.30 | **GROUNDED** (my label: probabilistic — compatible) |
| 2 latency/slippage | quantifiable 0.50 | **GROUNDED** — directly measurable basis |
| 3 fee/spread arithmetic | **arithmetic 0.46** | **GROUNDED** — 1¢+1¢ on a 50¢ contract = 4% is pure arithmetic |
| 4 quote-vs-resolution mismatch | empirical 0.62 | **GROUNDED** |
| 5 small-n randomness | quantifiable 0.65 | **GROUNDED** — the ±17pp CI at n=30 is computable |
| 6 winner non-stationarity | empirical 0.77 | **GROUNDED** |
| 7 self-defeating volume | **game-theory 0.80**, conf 0.73 | **GROUNDED** — the clearest equilibrium argument |
| "sub-second mirroring removes most failures" | P(yes) **0.14** | **GROUNDED** — selection + non-stationarity survive any speed |
| "n≥100 + Wilson CI bar is reasonable" | P(yes) 0.59 | **GROUNDED** (moderate — right direction) |

## q4 — mutual funds (5 answers)

| Answer | SubQ | My verdict |
|---|---|---|
| active MF selection beats index after costs | P(yes) **0.03** | **GROUNDED** — fees + survivorship + lag; consistent with literature (most active underperforms) |
| simple rotation sleeve beats cash+fees | P(yes) **0.99** | **PARTIAL (optimistic)** — with an absolute-momentum filter, positive expectancy is plausible (our backtest: 10/14 positive years) but 0.99 ignores long flat/grind regimes; treat as "likely, not certain" |
| P(rotation positive over 10y) | score 4.16 → **55-70%** band | **PARTIAL** — MORE conservative than my page's 85-90% for "positive net return". SubQ likely prices timing-drag risk; my number priced historical frequency of equity-risk strategies. **Divergence worth keeping visible** — I keep 85-90% for the narrow event (positive over 10y) and note SubQ's 55-70% as the skeptical view |
| minimal first infrastructure | `pit_universe` 0.87 | **GROUNDED** — survivorship is the #1 fund-research trap (NAV cache is the parallel prerequisite; both are in our plan) |
| P(active selection positive vs index) | score 1.15 → 10-25%, conf 0.65 | **GROUNDED** — same as first answer |

## q5 — evidence quality of algorithm families (11 answers)

| Family | SubQ | My verdict |
|---|---|---|
| market making | 4.57 (strong, durable, capacity-tested) | **GROUNDED** — but capacity/capital bars are huge; not retail-reachable |
| momentum factor | 4.33 | **GROUNDED** — Jegadeesh-Titman, decades of replication |
| value factor | 4.27 | **GROUNDED** — with post-2010 decay noted in the state |
| trend following | 4.23 | **GROUNDED** — CTA real-money track records |
| vol risk premium | 4.14 | **GROUNDED** — documented, with crash-tail caveats |
| carry | 4.09 | **GROUNDED** — but crisis-unwind failure mode known |
| pairs/stat-arb | 3.76 | **GROUNDED** — capacity decayed for retail |
| RSI(2) mean reversion | 3.45 (academically replicated) | **GROUNDED** — short-horizon reversal is in the literature; net-of-cost at retail size is the catch |
| **ICT/FVG** | **0.69 — "retail folklore only"**, + noul "has peer-reviewed evidence?" P(yes)=**0.01** | **GROUNDED** — matches our research (0 of 648 backtests beat B&H) |
| typical TradingView indicators | 1.06 — retail folklore | **GROUNDED** — no published audited track records |

## q6 — key metrics by perspective (8 answers)

| Perspective | SubQ most-critical | min Sharpe | My verdict |
|---|---|---|---|
| Quant HF risk committee | **tail risk (VaR/ES)** 0.66 | 1.5-2.0 | **GROUNDED** — RCs exist to prevent blowups; Sharpe bar is high but within HF range |
| Mutual fund manager | **max drawdown** 0.66 | 1.0-1.5 | **GROUNDED** — UCITS/retail flows die on drawdowns |
| Bank top prop trader | Sharpe 0.34 (low conf) | 1.5-2.0 | **PARTIAL** — low confidence; bank desks usually care about P&L attribution + risk limits first; Sharpe plausible as the return metric |
| Retail paper-trader | maxdd 0.38 vs sharpe 0.31 (low conf) | 1.0-1.5 | **PARTIAL** — low confidence; correct answer for retail is arguably *cost+survival*, neither of which was an option |

### Cross-cutting verdict
**Overall: GROUNDED with noted optimism spots.** SubQ's arithmetic-class claims
(costs, small-n CIs, active-fund underperformance, ICT evidence absence) all check out
against ground truth and our own measurements. Its soft spots: (1) min-forward-months
and min-Sharpe bars run *stricter/looser* than common practice at low confidence —
don't adopt them as hard gates without our own justification; (2) rotation-beats-cash
0.99 is optimistic; (3) it priced the MF sleeve event differently than my page did —
both numbers are kept visible rather than averaged. **No answer was fabricated or
contradicted basic arithmetic** — the main failure mode of LLM consults did not appear
here because the Decisions API forces typed outputs with calibrated probabilities.
