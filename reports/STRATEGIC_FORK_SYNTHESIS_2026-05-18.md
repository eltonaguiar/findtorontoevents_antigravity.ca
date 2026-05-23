# Strategic Fork — Cloud Swarm Synthesis (2026-05-18)

After 7 harness kills (`reports/EDGE_HUNT_CONCLUSION_2026-05-18.md`), the 3
options — (1) new input class, (2) research-sandbox, (3) structure alpha —
were put to a 4-model cloud swarm (DeepSeek-reasoner, xAI Grok-3, Kimi,
OpenRouter/deepseek-chat). Raw answers: `reports/strategic_fork/<model>.md`.
Tool: `tools/strategic_fork_consult.py`.

## Convergence — unanimous across all 4 models

**1. NOT mutually exclusive — but parallel execution is lethal for a small team.**
Option 2 (sandbox) is the always-on *posture*, costs nothing, runs alongside
anything. Options 1 and 3 each need a dedicated full-time person + data/exec
infra; splitting that person across both guarantees neither clears the gate.
**Verdict: Option 2 stays permanently on; pick exactly ONE of 1 or 3 for a
time-boxed 90-day sprint.**

**2. Base rates — ranked, honest (probability of a harness-passing edge in 6-12mo):**

| Option | DeepSeek | xAI | Kimi | OpenRouter | Read |
|--------|----------|-----|------|------------|------|
| 3 — structure alpha | 10-15% | 15-20% | 15-25% | 40% | **highest — recommended active path** |
| 1 — new input class | 3-8% | 8-12% | 10-20% | 5% | low; needs paid data; often pre-arbitraged |
| 2 — sandbox | 0% | 0% | 5-10% | 10% | cost-avoidance, not edge — produces nothing by design |

Rank, unanimous: **3 > 1 >> 2.**

**3. Structure alpha is genuinely different — not the same trap.** You are paid
for providing liquidity / financing / carry, not for predicting direction.
That removes the burden that produced all 7 kills (forecasting price). The
warning all 4 repeat: most teams *re-label* directional bets as "structural"
and fall back into the trap — the test is "am I being paid to carry, or am I
still predicting?"

**4. The 90-day plan converges (30/60/90 with hard kill-gates):**
- **Days 1-30:** ONE narrow structural probe, *public data only, zero
  purchases*. Kill if net carry after realistic costs is too thin.
- **Days 31-60:** minimal paper-execution engine; run through the existing
  `edge_stability_harness` PLUS a capital-realism gate — round-trip cost
  (fees + clearing + half-tick slippage) must leave ≥60% of gross edge.
- **Days 61-90:** live microlot, or kill back to sandbox.

## Where the models split — and the resolution

DeepSeek + Kimi's single highest-EV pick: **"stop spending, stay sandbox"** —
the most conservative read, given the 7-kill record. xAI + OpenRouter: **run
the Option-3 structural probe** with a hard kill rule.

**Resolution — the capital constraint settles it.** The models' headline
structural example (Treasury-futures basis / calendar spreads) needs
$100k-$2mm margin — not viable here (sandbox budget is $200-$1000). But
DeepSeek's *week-1* concrete pick is not: **crypto perpetual funding-rate
arbitrage** — hold spot, short the perp (or vice versa), delta-neutral,
collect the funding payment. That runs at ≤0.5 ETH notional, fits the budget,
and is the structural strategy with the cleanest "paid to carry" test.

Note the distinction from kill #6: H-006 traded funding rate as a *directional
signal* (predict price from funding z-score) — killed. Funding-rate
*arbitrage* is the opposite — you take no directional view, you are delta-
neutral and collect the funding cash flow. Different strategy, different trap.

## Recommendation

**Active path: Option 3 — crypto funding-rate (basis) arbitrage, 90-day sprint.**
Highest base rate (~15-20% realistic), fits the small budget, genuinely
outside the directional-prediction trap. Option 2 (sandbox + harness gate)
stays the standing posture. Option 1 (new inputs) parked — lowest base rate,
needs paid data, revisit only if Option 3 dies.

**Day-1 gate before any code:** confirm reliable funding-rate + spot/perp
basis data with low lag (DeepSeek's <500ms is HFT-grade and unnecessary for an
8h-funding-cycle strategy — minutes of lag is fine). Then build the delta-
neutral funding-capture backtest, 2-year history, through the harness + the
≥60%-of-gross-survives-cost gate.

**This is a user decision** — it commits a 90-day sprint and (at day 61) a
~$1000 live microlot. Awaiting go/no-go.
