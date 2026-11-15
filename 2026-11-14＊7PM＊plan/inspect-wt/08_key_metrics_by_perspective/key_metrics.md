# Key metrics that must be satisfied — from six perspectives

> Item 6 of the request: the bar for "trust this with real money", viewed as a quant risk
> committee, a mutual fund manager, a bank's top prop trader, a professional investor
> (family office / PM), our own certification gates, and a retail paper-trader. SubQ's
> independent answers (Decisions API, with probabilities) in `../subq/factcheck.md` q6.

## The metric stack (what each metric actually tells you)

| Metric | What it measures | Blind spot (why it can't be alone) |
|---|---|---|
| **Sharpe** (excess, net, annualized) | return per unit vol | ignores tail shape; unstable at low n; can be gamed by smoothing/frequency |
| **Sortino** | return per *downside* unit | downside dev estimation noisy at n<100 |
| **Max drawdown (MDD)** | worst peak-to-trail loss — *permanent capital risk* | single-path dependent; one path ≠ future |
| **Calmar** (CAGR/\|MDD\|) | return per unit of pain — the benchmark-relative workhorse | CAGR window-sensitive |
| **Profit factor (PF)** | gross win / gross loss | ignores trade correlation, position sizing |
| **Hit rate + Wilson CI** | win probability, with honest uncertainty | low-WR winners can be superior (trend); must pair with W/L |
| **Excess return vs benchmark (IR/t-stat)** | does it beat *the alternative*? | benchmark choice is itself a decision — pre-register it |
| **Capacity / slippage at size** | does the edge survive your money? | most retail tests never measure it |
| **VaR/ES (95/99, stress)** | tail loss under normal/crisis | historical-only VaR misses novel regimes |
| **Turnover / cost ratio** | edge vs friction | the 0.416%/trade breakeven style of test |

## Perspective-by-perspective (who must be satisfied, and by what)

### 1. Quant hedge fund risk committee
- **Primary: tail risk** (SubQ: var_tail, P=0.66) — stress scenarios, ES95/99, kill-switch
  existence, model-change control (Two Sigma paid $165M+$90M for failing exactly here).
- **Bar:** net Sharpe ≥ 1.5 (SubQ: 1.5–2.0 band), MDD within mandate (often ≤10–15%),
  capacity documented, **dual-source data**, audit trail on every PnL number.
- **What kills approval:** unauditable numbers, single-source evidence, unbounded exposure.

### 2. Mutual fund manager (UCITS/retail constraints)
- **Primary: max drawdown** (SubQ: 0.66) — flows die on drawdowns, and UCITS/retail
  mandates hard-code diversification/exposure limits.
- **Bar:** Sharpe ≥ 1.0 net (SubQ band), MDD ≤ mandate (often 10–20%), tracking error /
  excess vs stated benchmark positive with t ≥ ~1.6, liquidity ≥ redemption needs,
  **benchmarked vs the index the marketing says** (regulatory honesty).
- **What kills it:** style drift, benchmark mismatch, redemption-driven forced sales.

### 3. Bank's top proprietary trader
- **Primary: Sharpe** (SubQ: 0.34 — low confidence; in practice: P&L attribution + risk
  limits first, Sharpe as the score).
- **Bar:** positive expectancy **after explicit cost allocation**, Sharpe ≥ ~1.5–2 at the
  desk level (SubQ band), clear attribution (which signal, which day, what risk), staying
  inside VaR limits daily — a trader who blows the limit is done regardless of Sharpe.
- **What kills it:** unexplained P&L, concentration, negative month clusters vs mandate.

### 4. Pro investor / family-office CIO (the "would I wire money" test)
- **Excess return vs SPY/60/40 with a stated metric** — if the answer needs a paragraph,
  the answer is no.
- **Calmar ≥ 0.7 net; MDD ≤ 15%; Sharpe ≥ 1.0 net;** capacity fine at our size;
  **transparent, third-party-verifiable track record** (the industry-case-study pattern:
  self-published backtests are what nobody accepts).
- **What kills it:** can't state the benchmark, or the benchmark comparison changes per
  conversation.

### 5. Our own certification gate (PLAN_FINAL Phase 4 — what WE will require)
n ≥ 100 (equity trial: n ≥ 500) · WR ≥ 50% with Wilson CI excluding 50% · PF ≥ 1.5
(crypto interim: ≥1.3 with WR ≥ 55%) · MDD < 20% at stated sizing · ≥66% walk-forward
windows positive · dual-source data · multiple-testing disclosure (total trials counted)
· **excess Sharpe vs pre-registered benchmark ≥ 0.2–0.3 over ≥24 months forward**
(SubQ: 30–36 months, low confidence) · CI-green runs only · `is_single_source_artifact=False`.

### 6. Retail trader paper-trading (survival mode)
- SubQ: maxdd (0.38) vs sharpe (0.31), both low confidence — the honest retail answer is
  **cost + survival**: (a) risk ≤1–2% per trade, (b) ¼-Kelly cap (never full Kelly —
  estimation error), (c) monthly loss limit → stop, (d) track record vs SPY monthly,
  (e) **no new strategy until the current one has n ≥ 100 forward trades or a kill**.
- Retail's real edge is *not paying for things*: costs are the one controllable input.

## The one-page summary (what ALL perspectives agree on)
1. **A number without a benchmark is not a result** (everyone demands excess-vs-something).
2. **Net-of-cost, forward, pre-registered** — no perspective accepts backtest-only.
3. **Drawdown is the metric that ends careers** (risk committee, fund manager, prop desk).
4. **n and its confidence interval** — every perspective is really asking "how sure?".
5. **Third-party-verifiable reporting** (from `07_industry_case_studies`: the pattern that
   converts a track record into trust).
6. **Kill switches and change control** — Two Sigma's $165M+$90M proves governance is
   not optional at any size.
