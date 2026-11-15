# Review — `2026-11-14_PM_plan/grok_agent/`

**Reviewer:** Buffy · **Date:** 2026-11-15 · **Method:** read all 11 files from `origin/main` via `git show`
(the folder is **not in this local worktree** — see §6), cross-checked against measured ledger data,
SubQ runs, and primary sources.

---

## 1. Verdict

**Good package, real work, correctly aimed — and it should not be dispatched as-is.** It is a strong
*prompt and strategy-menu* layer. It is not a *measurement* layer, and one of its instructions is not
executable as written.

| Dimension | Grade | Why |
|---|---|---|
| Aim / framing | **A** | Buy-and-hold benchmark requirement appears 12×; "no edge found" is an accepted outcome |
| Strategy menu | **A−** | Names the right classical families (12-1 momentum, quality/ROIC, dual momentum, low-vol) |
| Prediction-market diagnosis | **B** | Directionally right, but misses the two findings that block measurement in *this* repo |
| Quantitative gates | **D** | No measured numbers anywhere; gates are qualitative |
| Executability of SubQ instruction | **F** | SubQ cannot fetch primary sources — it scores what you paste |
| Provenance discipline | **C** | Tells agents to tag unverified claims, then states unverified claims itself |

---

## 2. Where it is right, and where it corrects me

### 2.1 Rob Hoffman — they are right, I was wrong

I previously reported that I could not verify a contest winner named "Hoffman" and flagged it rather than
invent one. Their file names **Rob Hoffman Inventory Retracement Bar**, and that is correct:

- **Rob Hoffman**, two-time International Trading Champion; won live, real-money competitions (International
  Traders Expo, Infinity Futures Live Trading Challenge, Salon du Trading Paris 2012).
- **IRB rule:** EMA-20 slope defines trend; a bar that opens and closes ≥45% of its range away from its
  high (uptrend) or low (downtrend) marks retracement; entry on break of that bar's extreme.
- Implementations exist on TradingView, NinjaTrader and thinkorswim — it is a real, documented method.

**My earlier note stands corrected.** Hoffman is not a World Cup winner; he is a competition winner and the
originator of a widely implemented indicator. Their package got this right and mine was incomplete.

### 2.2 TradingView "The Leap" — correctly labelled as paper

They say: *"Paper trading competitions… Paper results systematically overstate real-money performance."*
That is accurate, and worth putting numbers on for whoever reads this next:

- September 2026 AMP Futures edition: **103,158 participants**, 4.9M+ trades, #1 at **+1,673.74%** — on
  **virtual** capital ($100k virtual in the July TradeStation edition, 30 days).
- So a Leap winner is a **paper-leaderboard** result. It is evidence of nothing about real-money edge.

Their framing is right. I would add only that the same logic applies to World Cup *single-year* results:
audited, but one year ≠ a track record.

### 2.3 The benchmark requirement is first-class

`buy-and-hold` appears 12 times. That is the gap they correctly identified in my metrics work, and their
per-class prompts carry it into the agent instructions. Good.

### 2.4 The strategy menu is genuinely useful

My prompt pack tells agents *how to test*. Theirs tells them *what to try* — 12-1 cross-sectional
momentum, quality (ROIC/accruals), low-volatility, dual momentum, CTA trend, carry. That is a better
candidate list than mine and should be merged into it.

---

## 3. Five problems, with evidence

### 3.1 Zero measured numbers — the gates are qualitative

Grep across all 11 files on `origin/main`:

```
"48" → 0    "forged" → 0    "SPIVA" → 0    "92.89" → 0
"3.5%" → 0  "deflated" → 0  "DSR" → 0
```

Their strongest quantitative gate is `IR ≥ 0.3–0.5` and `PF ≥ 1.15`. Nothing in the package tells an agent
that **48.1% of closed rows carry no price information**. Consequence: an agent following these prompts
faithfully will compute PF on a half-forged ledger and report it as a clean result. The gate cannot catch
what the prompt never mentions.

### 3.2 The SubQ instruction is not executable — this is the important one

Their README says *"Require them to fact-check claims via SubQ … against public data and academic
literature"*, and the guardrail says *"Cross-check important numbers against primary sources."*

**SubQ cannot do that.** I ran it 40 times across three arms. The Decisions API (`POST /v1/systemone`,
`subq-snap-1.2`) has **no browsing and no retrieval**: it scores the `state` string you give it and returns
typed probabilities. It will happily score a claim with no sources attached and sound confident doing it.
The chat model (`subq-preview`) is not enabled on this key, and even it would need sources supplied.

As written, an agent will believe SubQ verified something when SubQ only *judged what it was handed*.
Correct instruction:

> Fetch the primary source yourself; paste the relevant numbers into SubQ's `state`; ask for a
> noul/choice decision; record the source URL alongside the probability. SubQ scores evidence — it does
> not gather it.

A working client exists: `tools/subq_consult.py` (records request SHA-256, HTTP status, token usage).

### 3.3 The prediction-market analysis misses the two blockers in *this* repo

Their six reasons (zero-sum, bot dominance, adverse selection, favorite-longshot bias, copy-trading
implementation, fees) are all true and better-written than mine. But they are **market-level** reasons, and
they do not explain why *this system* has never had a winner, which is a repo-level question:

1. **There is no PREDICTION asset class in the ledger.** Classes present: CRYPTO, EQUITY, ETF, FOREX,
   COMMODITY, BOND, FUTURES, SPORTS. PM rows from `pm_kalshi_signals` / `prediction_market_consensus` are
   tagged **CRYPTO** (32 rows) — a BTC price-range contract filed as a crypto pick. **No class ⇒ no verdict
   ⇒ no learning, ever.** Fix this before any copy-trading work.
2. **The fee arithmetic is absent, and it is decisive:** Kalshi `ceil(0.07 × C × P × (1−P))` = **3.5% of
   stake at 50¢, 6.3% at 10¢, 0.7% at 90¢**; Polymarket `θ·C·P·(1−P)` with θ 0.04–0.07; **makers pay 0 and
   receive 15–25% rebates.** A 2-point calibration edge at 50¢ is *below the fee*. "Fees favour
   sophisticated participants" is true but not actionable; the curve is.

### 3.4 Their own unverified claims

The package instructs agents to tag unverified claims — then states, unsourced:

- IRB: *"~60% win rates and positive PF on short samples (BTC, Solana)"* — no test count, no period, no cost model.
- *"Ordinary Kalshi users lost hundreds of millions in aggregate"* — no study named.
- *"0.1% of accounts captured ~67% of profits in one major study"* — no citation.

These may well be true (the zero-sum and concentration findings are consistent with published work), but
under their own rule they are `<unverified>` until sourced. Theirs is a memo about provenance; it should
model the behaviour it demands.

### 3.5 Two prompt packs, two different bars

| | Theirs | Mine |
|---|---|---|
| Size | 4.1 KB | 17.2 KB |
| Benchmark-relative | ✅ required | ✅ required + formulas + matched exposure |
| DSR / trial count | ✗ absent | ✅ DSR ≥0.95 at N=361 |
| Kelly / ruin gate | ✗ absent | ✅ Kelly>0, ruin<5% |
| Survives 2× costs | ✗ | ✅ |
| Ledger-integrity precondition | ✗ | ✅ A6 blocking agent |
| Forward paper pilot | mentioned | ✅ ≥30 round trips / 90 days |
| Machine-readable result | ✗ | ✅ `results_schema.json` |
| Strategy menu | ✅ **better** | weaker |

If both are dispatched to parallel agents, results are **incomparable** — one pack accepts IR 0.3, the
other demands DSR at 361 trials. Pick one canonical gate set before dispatch.

---

## 4. Recommended merge (do this, don't run both)

| Keep from theirs | Keep from mine |
|---|---|
| Strategy menu (momentum/quality/low-vol/dual momentum/CTA) | Ten-gate bar + `results_schema.json` |
| Readable PM narrative (zero-sum, bot dominance) | PM structural findings (no class, fee curve) |
| Hoffman / Leap framing | Labelled sourcing + "verified ≠ intrabar" caveats |
| Short per-class prompt wording | A6 ledger-repair blocking agent + A0 harness |

**Canonical:** my `01_agent_prompts/AGENT_PROMPTS.md` gates + schema, with their §2.4 strategy menu pasted
into each agent's "approaches to test" section. Then archive the duplicate.

## 5. Fix list for their package (ranked)

1. **Rewrite the SubQ instruction** (§3.2) — fetch sources yourself, paste into `state`, record URLs.
2. **Add the ledger precondition**: "do not compute any metric until forged-flat rows are excluded; 48.1% of closed rows qualify."
3. **Add the fee curve** to the PM doc, plus the "no PREDICTION class" finding.
4. **Tag their own unsourced claims** `<unverified>` and add sample sizes.
5. **Adopt one gate set** and delete the other, or mark one as deprecated.
6. **Add a red-team agent** — theirs has no adversarial step; every claimed win passes unexamined.
7. Minor: list `STRUCTURED_AGENT_PROMPT.md` in the README (11th file, absent from the summary).

## 6. Repo-state problem found while reviewing

The folder exists on `origin/main` but **not in local `main`**, which has diverged. Consequence: my two
packages from this session (`2026-11-15_1227AM_profitability/`, `2026-11-15_1233AM_winning-strategies/`) are
**local-only** and their commits are not on the remote. Anyone reading the repo on GitHub sees their
package and not mine; anyone on this machine sees the reverse.

**Resolve before dispatching agents**, or half your fleet will read a different prompt pack than the other
half. That is a coordination bug, not a content bug.

## 7. One-line summary

**Their package is the better *menu* and the better *narrative*; mine is the better *gate*. Merge the menu
into the gate, fix the SubQ instruction, and reconcile the two branches before any agent runs — otherwise
the parallel fleet will produce incomparable results from two different definitions of "proven".**
