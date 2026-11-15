# From "Nothing Works" to "Trust Us With Money" — What Actually Turned Firms Around

This section answers: what did financial prediction / risk firms do to move from struggling to trustworthy? **Verification status is marked on every claim.** Anything not verifiable is labelled as such — no invented contest results, no invented buyouts, no fabricated track records.

## 1. The pattern that repeats (all verifiable, general knowledge)

| Firm | The move | Why it built trust |
|---|---|---|
| **AQR** | Published its factor research openly (momentum, value, carry, quality, low-vol) and accepted capacity limits | Trust came from *falsifiable public claims* + academic grounding, not from secrecy. Investors could check the logic. |
| **Renaissance Technologies (Medallion)** | Extreme secrecy on method, but hard capacity discipline — closed the fund to outside money and returned capital | Trust via *demonstrated, audited returns* and refusing to scale past capacity. Different mechanism, same principle: never promise more than the data supports. |
| **Bridgewater** | Systematised risk parity and wrote the process down ("Principles", daily observations) | Trust via *documented decision rules* that a client can read and challenge. |
| **Two Sigma** | Treated data quality + infrastructure as the product | Trust via *reproducibility* — same inputs, same outputs. |
| **Vanguard / index providers** | Sold the boring, provable thing: low cost + beta capture | Trust via a *measurable expected outcome* rather than a prediction. |

**UNVERIFIED / DO NOT REPEAT:** claims that any of these firms "was failing until X" with specific dates, or that one acquired another, are not established here. Treat turnaround narratives as illustrative patterns, not facts to cite to a client.

## 2. The five moves that consistently work

### Move 1 — Publish the negative result
A firm that says "we tested N strategies, zero passed, here is the evidence" is *more* credible than one still showing picks. It proves the measurement is honest. This repo is sitting on a rare asset: a rigorous negative sweep. Publishing it is the trust-building move, not a liability.

### Move 2 — Separate beta from alpha, and sell beta honestly
The highest-probability profitable product is low-cost, diversified allocation. It can pass a proof standard because its benchmark is explicit. Sell that as the core, and treat alpha as research with a public scoreboard.

### Move 3 — Make the process auditable
Every decision traceable to lagged, observable data. Every pick traceable to a `run_id`. Every claim traceable to a file path. Auditable beats clever.

### Move 4 — Enforce capacity discipline
State the AUM at which the edge dies, and refuse to exceed it. This is what separated Medallion from funds that scaled into mediocrity. For us: state the size at which each signal's slippage kills it.

### Move 5 — Pre-register and let the forward test decide
Write the hypothesis, the rules, the kill thresholds *before* running. Then publish the forward-test result whether it's good or bad. This is the single cheapest trust signal available and almost nobody does it.

## 3. What does NOT build trust (and burned years here)

- Tweaking TP/SL until a backtest turns green → converts the proof standard into a false-positive generator
- Morphing a failed strategy into variants → each variant is a fresh trial that inflates the multiple-testing burden
- Showing active picks with no benchmark, no fees, no `run_id` → these are anecdotes, not track record
- Running 20 AI agents in parallel on the same under-specified question → 20 correlated guesses, not 20 independent tests
- Claiming "proven" from a chart

## 4. The honest product ladder

1. **Now:** publish the negative result + the proof protocol. Zero capital at risk, maximum credibility gain.
2. **Next:** run the pre-registered equity quality-momentum test. Publish the verdict either way.
3. **Then:** paper-trade the near-misses (F3, F21, F25) with the tracker. 90 days, published.
4. **Then:** launch the core-satellite allocation product (`Plan/multi_asset/`) — provable, benchmarked, low-risk.
5. **Only if** a satellite signal clears all 10 proof steps: size it at quarter-Kelly, capped, with a live kill switch.

## 5. The one-line lesson

Firms became trustworthy by making claims **smaller and more checkable**, not by finding a better prediction. That is the available move here.
