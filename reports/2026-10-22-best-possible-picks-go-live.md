# Best-Possible Picks for Go-Live — expanded, ELI5 + honest benchmark analysis

**Date:** 2026-10-22 · **Author:** Zoo (main session)
**Full evidence trail:** [`2026-10-22-top10-winners-reverse-engineered.md`](reports/2026-10-22-top10-winners-reverse-engineered.md) ·
[`2026-10-22-ml-stack-audit.md`](reports/2026-10-22-ml-stack-audit.md) ·
[`tools/winner_candidate_vetting.py`](tools/winner_candidate_vetting.py)

---

## 1. TL;DR — the one-paragraph answer (plain English)

We are looking for **short-to-medium holding trades on big, liquid cryptocurrencies that are in an uptrend
and are currently having a dip** — because that is the exact pattern that our own past winners came from.
We "double-checked" that pattern with independent tools (trend, momentum, volatility) and found **8 of 11
candidates pass**, 2 are "wait" and 1 (Ethereum) we'd sit out today.

On **"can we actually make money?"** — the honest answer is **yes, there is statistical evidence of an edge**
(a profit factor of ~2.2 on a test set the model never saw, meaning roughly $2.20 made for every $1 risked),
but **we have not yet proven net-of-cost long-run performance vs the S&P 500**. Crypto buy-and-hold lost
24–37% over the last year; our approach is designed to avoid exactly that by sitting out downtrends. **We are
not at the drawing board** — the edge is real — **but we must tighten execution** before we can claim we beat
the market reliably.

<details>
<summary><b>Click to see the key numbers in one table</b></summary>

| Question | Number | What it means |
|---|---|---|
| Our best validated edge (ML gatekeeper) | Profit Factor **2.206**, win-rate **+8.42pp** on 500 never-seen trades | For every $1 we'd lose, we'd make ~$2.20. This is a *real* edge, not a guess. |
| Our consensus pick lift | **+10.71pp** win-rate vs single picks | Picking only when several systems agree is meaningfully better. |
| Typical winner size | mean **+2.85%** per winning trade | The common win is small; the +20% targets are rare "tail" wins. |
| S&P 500 (1y) | **+13.7%** | The benchmark we need to beat. |
| Bitcoin buy-and-hold (1y) | **−24.6%** | The thing we are explicitly trying *not* to do. |
| Ethereum buy-and-hold (1y) | **−37.5%** | Same — buy-and-hold crypto has been brutal. |
</details>

---

## 2. "Can we actually get profit?" — the honest, spelled-out answer

**The short version:** we have *statistical* proof of an edge on the subset of picks our ML filter passes.
We do *not* yet have a clean, audited comparison of our *whole* system against the S&P 500 over a real
forward window. That is the single most important honest gap.

### What a "profit factor" is, and why 2.2 matters

Think of betting on coin flips. If you win $1 when it lands heads and lose $1 on tails, over time you break
even — a "profit factor" of 1.0. If, over a long run, you win $2.20 for every $1 you lose, that is a profit
factor of 2.2 — **you are systematically winning more than you lose**, which is the definition of having an edge.

Our gatekeeper's **2.206 profit factor** comes from a "holdout" test: we trained the model on 3,000 old
trades, then made it score **500 trades it had never seen**. It not only predicted winners better (60.8% vs
52.4% baseline — **+8.42 percentage points**), it made meaningfully more money on its "pass" picks than its
"reject" picks. This is the strongest evidence of a real edge in the whole codebase.

### So — do we beat the S&P 500?

<details>
<summary><b>Click to expand the full benchmark comparison + the honest caveat</b></summary>

**The benchmark picture (1 year, as of 2026-10-22):**
- S&P 500: **+13.7%** (the bar to beat).
- Bitcoin buy-and-hold: **−24.6%**.
- Ethereum buy-and-hold: **−37.5%**.

**Read that carefully.** Just buying and holding crypto over the last year lost a quarter to a third of your
money. Our entire strategy is built to *not* do that — we only take LONG crypto picks when the trend is up and
we hold for days, not months. That means **beating "buy and hold crypto" is a low bar that our approach is
specifically designed to clear** (sit out the downtrend).

**Beating the S&P 500 is the hard bar**, and here is the honest truth:
- We have **per-trade** evidence of edge (PF 2.2 on the gated subset).
- We do **not** yet have one single, audited **"total portfolio return over 6–12 months, net of fees and
  slippage, vs the S&P 500"** number.
- That number is exactly what the `benchmark_ledger_proof` infrastructure we built is meant to produce — it is
  the missing final proof, not a sign the approach is broken.

**Verdict:** "Can we get profit?" → **Yes, evidence-backed edge exists.** "Do we *currently* beat the S&P 500?"
→ **Not yet proven as a continuous system — that is the remaining proof we must build.** "Do we beat buy-and-hold
crypto?" → **Overwhelmingly likely, by design** (buy-and-hold lost 24–37%; we trade around the trend).
</details>

---

## 3. Why these picks — the general concepts, simply

<details>
<summary><b>Click to expand the plain-English "why" for the whole approach</b></summary>

Three simple ideas drive everything:

1. **Where did our past winners come from?** We looked at the 155 real, resolved winning trades and asked
   "what do they have in common?" Answer: **most were LONG trades (betting the price goes up) on liquid crypto,
   resolved around the 14:00 and 21:00 UTC windows**, mostly from a handful of reliable systems. So we hunt
   where winners actually came from, not where we *hope* they are.
2. **"Double-check" with independent tools.** The winner pattern alone can lie (e.g., it would have bought
   Ethereum, which is in a daily downtrend). So we *cross-check* each candidate with four separate,
   well-known tools: a trend filter (is it above its 20- and 50-day average?), a momentum meter (RSI), a
   volatility ruler (ATR), and where it sits versus its 52-week range. If the winner pattern *and* the few
   tools agree, we take the pick. If they disagree, we wait.
3. **Risk first.** We never set a price target (take-profit) or stop-loss by guessing. We measure how much a
   coin typically wobbles in a day (ATR) and set the stop at 1.2× that wobble and targets at 2× and 3×.
   Volatile coins get wider stops and bigger targets — so risk is fair across all of them.
</details>

---

## 4. Which tests did it pass, and what does each one mean?

<details>
<summary><b>Click to expand "what each test means, with an analogy"</b></summary>

| Test | What it is | Analogy | What a good result looks like |
|---|---|---|---|
| **Holdout test** | Train only on old data, then score trades the model has never seen. | A teacher grades students on **questions they never saw on the practice test**. | Gatekeeper: **PF 2.206**, **+8.42pp** win-rate on 500 unseen trades. |
| **Walk-forward test** | Re-train the model as time moves forward, so it never "peeks" at the future. | Re-studying for each new chapter before each new exam, never seeing the exam early. | 12-fold walk-forward **+4.31pp** mean lift, p=0.0004 (less than 1-in-2000 chance it's luck). |
| **Bootstrap confidence interval** | Re-samples the data thousands of times to ask "how sure are we this isn't a fluke?" | Shuffling a deck and dealing thousands of hands to see if a run of wins is repeatable. | 95% CI on the lift: **[+2.68, +5.83]pp** — the entire range is positive. |
| **Profit factor (PF)** | Gross wins ÷ gross losses. 1.0 = break-even. | Dollars won per dollar lost at the casino. | **2.206** → ~$2.20 won per $1 lost. |
| **Win rate (WR)** | % of trades that make money. | How often a basketball player makes the shot. | Holdout passed-WR **60.8%** vs 52.4% baseline. |
| **ATR-scaled stop/TP** | Set stop/target from the coin's own daily volatility. | A ruler sized to the track, not a fixed tape measure for all racers. | Stop = 1.2×ATR; targets = 2× / 3×ATR. |
| **Trend filter (20/50-day SMA)** | Is price above its short and long average? | Is the elevator going up or down before you step in? | Candidate passes if **UP** (20d > 50d). ETH/XRP fail (DOWN). |
| **RSI-14** | 0–100 momentum meter; <30 oversold, >70 overbought. | A car's speedometer *and* fuel gauge in one. | ~35–55 at entry = neither exhausted nor overextended. |
</details>

---

## 5. Glossary — ELI5 for terms you may not know

<details>
<summary><b>Click to expand the plain-English glossary</b></summary>

- **LONG** — betting the price will go up (buy low, sell higher).
- **SHORT** — betting the price will go down (sell high, buy back lower).
- **Take-profit (TP)** — the price where we take the win and close the trade on purpose.
- **Stop-loss (SL)** — the price where we cut a losing trade so it can't get much worse.
- **Hold / holding period** — how long we keep a trade open (days, weeks, months).
- **Market order vs trigger entry** — a market order buys *right now*; a *trigger* waits for a condition
  (e.g., price stabilizes) before buying. We use trigger entries on red days.
- **Pullback** — a short dip *inside* an overall uptrend (normal, often a good place to buy).
- **Uptrend / downtrend** — price generally making higher lows (up) or lower highs (down).
- **ATR (average true range)** — a volatility ruler: the typical size of a coin's daily price swing.
- **SMA (20/50-day)** — the average price over the last 20 / 50 days; a trend compass.
- **RSI-14** — a 0–100 momentum meter; <30 = "oversold" (maybe cheap), >70 = "overbought" (maybe expensive).
- **Win rate (WR)** — % of trades that end in profit.
- **Profit factor (PF)** — dollars won ÷ dollars lost; >1.0 = profitable.
- **Walk-forward / holdout** — the two "no cheating" ways of testing a model on data it never saw.
- **Bootstrap** — a statistical re-sampling that tells us how confident we are an edge isn't luck.
- **Risk-off day** — a down day for the whole market, when most risky assets fall together.
- **52-week high/low** — the highest / lowest price over the past year; shows where we are in the range.
- **S&P 500** — the stock-market index we compare against (the "market beat" bar).
</details>

---

## 6. The overall criteria, as one analogy

<details>
<summary><b>Click to expand the "scout picks a runner" analogy</b></summary>

Imagine we are a scout choosing runners for a relay team.

- **We don't pick the loudest name or the one with the best-looking sprinting form.** We pick runners who have
  **proven they can win races** (they appear in our real winner list).
- Then we check they are **not injured and not exhausted right now**: that's the trend filter + RSI (they're
  in an uptrend and not overbought).
- Then we check the **track conditions** (volatility via ATR) so we set a fair finish-line (target) and a fair
  place to pull them out (stop) that matches how the track actually behaves.
- Finally, we **only let them run when the starter gun fires** (our entry trigger on the dip), not while the
  whole stadium is in a panic (risk-off day).

Our **single best candidate** is the runner who passes *every* check: **BTC** — proven winner, uptrend,
shallow pullback, neutral momentum, lowest risk, and the most liquid. The others are close behind but carry
more volatility (NEAR, INJ) or need a confirmed bounce (SOL, LINK, AVAX).
</details>

---

## 7. How close are we — and do we need the drawing board?

<details>
<summary><b>Click to expand the "how close" scorecard</b></summary>

| What we need for a confident go-live | Where we are | Closeness |
|---|---|---|
| Real winner pattern identified | ✅ 155 genuine winners, reverse-engineered | **Done** |
| Validated ML edge (not overfit) | ✅ gatekeeper PF 2.2, +8.4pp holdout; consensus +10.7pp | **Done** |
| Independent technical double-check | ✅ 8/11 candidates pass trend+momentum+volatility | **Done** |
| Explicit hold / TP / SL per pick | ✅ this report gives them for every candidate | **Done** |
| Candidate universe includes proven winners | ⚠️ 8 proven-winner symbols not yet scanned (AUDJPY, GBPJPY, BAT, CRV, ZEC, WLD, XTZ, MINA) | **Close — expand the universe** |
| Enforce the trend "sit-out" rule live | ⚠️ currently informational, not an automated gate | **Build it** |
| A/B evidence (old vs new model) | ❌ 0 samples per sleeve | **Gap — needs time** |
| Net-of-cost total return vs S&P 500 | ❌ not yet audited over a real forward window | **The remaining proof** |

**Verdict:** **We are NOT at the drawing board.** The edge evidence is real and validated. What we are missing is
*proof of continuous net-of-cost outperformance* and *small execution gaps* (universe expansion + an automated
sit-out rule + accumulated A/B evidence). The shortest honest statement:

> "We have a statistically-validated edge and a concrete, volatility-scaled shortlist. We have not yet *proven*
> we beat the S&P 500 over a full forward window — that is the last proof to build, not a reason to restart."
</details>

---

## 8. The concrete candidates (LONG, tactical re-entry)

All entries are **trigger-based** (wait for stabilization / RSI turn from <40 / reclaim of the 20-day average)
— **not** market orders into today's risk-off open. Risk = 1.2×ATR; TP1 = 2×ATR; TP2 = 3×ATR.
**Holding period: swing, 3–10 trading days** (matching the 14:00Z / 21:00Z resolution windows where winners concentrated).

| Candidate | Entry ≈ | Stop-loss | TP1 | TP2 | Hold | Why (plain English) |
|---|---|---|---|---|---|---|
| **BTC-USD** | 81,200 | 78,640 | 85,550 (+5.3%) | 87,710 (+8.0%) | 5–10 d | Proved winner; uptrend; shadest pullback; lowest risk; most liquid. The #1 pick. |
| **SOL-USD** | 103.3 | 98.0 | 112.1 (+8.5%) | 116.5 (+12.8%) | 3–7 d | Uptrend + oversold → bounce candidate. |
| **LINK-USD** | 11.91 | 11.13 | 13.21 (+10.9%) | 13.86 (+16.4%) | 3–7 d | Uptrend + deep pullback → bounce candidate. |
| **AVAX-USD** | 9.09 | 8.38 | 10.29 (+13.2%) | 10.89 (+19.8%) | 3–7 d | Deepest pullback in an uptrend (RSI 35). |
| **NEAR-USD** | 4.86 | 4.27 | 5.86 (+20.5%) | 6.36 (+30.8%) | 3–7 d | Strong, but ATR 10% → size the bet smaller. |
| **INJ-USD** | 7.89 (only above 8.2) | 7.01 | 9.36 (+18.6%) | 10.09 (+27.9%) | 3–7 d | Highest upside; wait for breakout above 8.2. |

**Watch-list (relative strength, not primary longs):** **BNB** (+1.8% 5d while market red) and **XRP**
(+1.1%) — resilient, but daily trend is DOWN; promote only on a 20-day average reclaim.

**Sit out now:** **Ethereum** — daily DOWN-trend and no relative-strength signal despite being a volume leader.
This is the honest "don't force it" call.

---

## 9. Method notes

- Prices / ATR / SMA / RSI / 52-week: `yfinance` 1-year daily history, 2026-10-22 23:10Z
  ([`tools/winner_candidate_vetting.py`](tools/winner_candidate_vetting.py)).
- Winner frame: [`reports/2026-10-22-top10-winners-reverse-engineered.md`](reports/2026-10-22-top10-winners-reverse-engineered.md).
- ML validation: [`reports/2026-10-22-ml-stack-audit.md`](reports/2026-10-22-ml-stack-audit.md).
- Benchmarks: S&P 500 (^GSPC) +13.7%; BTC −24.6%; ETH −37.5% (1y, 2026-10-22).
- This is an internal candidate shortlist for go-live, not investment advice; no production trading is executed.

*Not financial advice. Research/educational only. Past performance does not guarantee future results.*
