# Quant Rescue — Multi-AI Swarm Verdict (2026-05-19)

**Question source:** `swarm_runs/_prompts/quant_rescue_deepdive_2026-05-19.md`
**Synthesis of:** 4 swarm rounds + 2 Grok headless calls. Honest count of
*substantive* responders below — several engines produced empty or off-topic
output and are explicitly excluded from the consensus tally.

## Engines consulted (signal vs noise)

| Round | Engine | Status | Used in synthesis? |
|---|---|---|---|
| R1 all-free-api | groq | substantive | yes |
| R1 | ollama_local | substantive (shallow) | yes (weak weight) |
| R1 | gemini_api, pollinations, ofox | **empty output** | NO — failed |
| R2 consensus-3 | deepseek | substantive, detailed | yes |
| R2 | xai (Grok-4.3) | substantive, detailed | yes |
| R2 | kilo | substantive | yes |
| R3 all-cli | claude | substantive, deepest | yes |
| R3 | opencode | substantive, deepest | yes |
| R3 | gemini | substantive | yes |
| R3 | copilot | substantive (architecture-only, didn't fully answer Q1-5) | partial |
| R3 | agent | **off-topic** — narrated tooling, never answered | NO |
| R3 | kilo | no output file | NO |
| R4 tie-break | claude, deepseek, kilo | substantive, detailed | yes |
| Grok call 1 | grok headless | substantive, detailed | yes |
| Grok call 2 (Q4 press) | grok headless | substantive, detailed | yes |

**Skeptic's note (per the "convergence trap" rule).** All engines read the same
prompt, which already states the 11/11-kill verdict. Convergence on "paper-only"
is therefore NOT independent verification — it is mostly the engines agreeing
with a premise they were handed. The independent signal is in the *reasoning
quality* and the *disagreements*, not the headcount. Two engines (agent,
copilot) essentially rephrased the prompt / narrated architecture without
answering; `gemini` (R3) also leaned heavily on restating repo docs
(`EDGE_HUNT_EXHAUSTED`, `benchmark_comparison.md`) rather than reasoning fresh.
The load-bearing analysis is from **claude, opencode, deepseek, and Grok** —
they each added a *new mechanism-level argument* not present in the prompt.

---

## 1. Consensus answer: salvageable, or paper-only?

**CONSENSUS: Not salvageable for live money now. Paper-only is the honest
posture.** Every substantive engine agreed. No dissent.

The 11/11 kill is not bad luck — it is the structural signature of an
arbitraged-away signal space at daily-bar resolution on free data. The single
strongest independent argument (opencode, claude): **PEAD — the most
out-of-sample-robust anomaly in academic finance — failed the harness
identically.** If even PEAD sign-splits here, the daily/free-data space is
empirically empty, and that is a fact about markets, not a bug in the system.

The harness itself is *correct* (pre-registration + walk-forward + eff>=0.30 is
institutional-grade). The system is working exactly as a kill-loop should: it
caught 11 fake edges before they cost real money. That is a research win, not a
money-maker.

**Per-class verdict (claude's table, endorsed by the swarm):**

| Class | Verdict | Why |
|---|---|---|
| CRYPTO | Conditional / research only | Only class with N to run the harness |
| EQUITY | Blocked | n=33 clean, 45% unresolved — can't measure what you can't resolve |
| FOREX | Paper-only | PF 0.27, 22% resolution |
| FUTURES | Paper-only | n=12 clean — statistically meaningless |
| BOND | Watch | n~18, below charter floor |
| COMMODITY | Watch | PF 1.78 but needs resolver fix before any verdict |

The lone in-sample-profitable non-artifact cohort — CRYPTO `mega_mutation`
(n=72, PF 2.19) — is forward-unproven and harness-untestable (too few windows).
It justifies paper-tracking, **not** live capital. Multiple engines flagged it
as a likely in-sample overfit.

---

## 2. The ONE highest-leverage change the swarm converged on

**A DATA-LAYER FIX, executed BEFORE any signal work — fix the writer.**

This is where the swarm genuinely converged (kilo, opencode, deepseek, claude,
all R4 engines). The ledger is ~83% noise (4,830 duplicate re-emissions +
policy-excluded rows out of 14,705 raw). Concretely:

1. **Dedup at the writer.** The `dedup_hash` column exists (UNIQUE char(64)) but
   4,830 dupes still landed — the INSERT path is not using `INSERT IGNORE` /
   `ON DUPLICATE KEY UPDATE`. One-line fix.
2. **Clamp `confidence > 1.0` at ingestion** (146 rows hold values 15–78).
3. **Clear the resolver backlog** (~29k CRYPTO picks OPEN >14 days; ~31k
   resolved rows with NULL pnl_pct).

Rationale, stated bluntly by kilo and deepseek: **every harness verdict and
every "edge" claim is suspect until the writer is fixed** — you cannot trust a
test run on poisoned data. claude (R4) made this a *blocking gate*: without the
data fix, the odds of the 3-month bet drop from ~10% to ~3%.

**Secondary lever (scope):** narrow to CRYPTO. Not because crypto has proven
edge — it hasn't — but because it is the only class with the sample size to
*ever execute the harness* (EQUITY n=33, FUTURES n=12). Concentration creates
the *conditions* for edge detection; it does not create edge.

Note the framing split: Grok/xai/opencode called the scope change the #1 lever;
kilo/deepseek/claude called the data-layer fix #1. These are not really in
conflict — the data fix is the *prerequisite*, the scope narrowing is the
*allocation decision*. Both come before any signal experiment.

---

## 3. Verdict on symbol-universe widening: real lever or noise?

**Mostly NOISE. It is asset-class- and hypothesis-type-dependent — and for the
asset class that matters (CRYPTO) it is a noise amplifier.**

- **CRYPTO: noise amplifier.** The scanner already covers ~131–200 of ~400+
  liquid pairs. Widening to 400 adds the illiquid long tail (wider spreads, more
  noise) without adding edge. The consensus gate already rejects ~87 scanned-but-
  consensus-starved symbols — more symbols just means more rejected rows.
- **EQUITY: a marginal, one-shot lever.** 37 of ~500 S&P names traded, 69% WR on
  that narrow set. opencode's caution is the key insight: that 69% may be
  *survivorship bias* — the scanner only scans names it already likes. Worth
  exactly one honest attempt, low cost, but do not assume it generalizes.
- **The real distinction (claude):** widening helps *only* a cross-sectional
  ranking hypothesis (where breadth = statistical power for one test). It does
  NOT help the directional hypotheses already killed — running a dead mechanism
  on 500 symbols just buys 500 independent tests of a dead mechanism.

Bottom line: widening the aperture is **not** the lever. It cannot manufacture
edge; at best it adds power to a cross-sectional test that does not yet exist.

---

## 4. Which untested approach is worth the 3-month bet — and the odds

The prompt named four: intraday/tick resolution, cross-sectional ranking,
meta-labeling, causal-inference feature selection. **This is where the engines
genuinely disagreed**, and the R4 tie-breaker round was run specifically to
resolve it. Disagreement surfaced below — NOT averaged away.

### The disagreement as it stood after R1–R3

- **Camp A (Grok, claude-R3, gemini): intraday/tick crypto is #1.** Mechanism: a
  structural liquidity tax / order-flow imbalance / funding-settlement pressure
  that does not sign-flip because it is a friction cost paid by noise traders,
  not a directional macro bet. Odds quoted: **14–22%**.
- **Camp B (opencode, groq): meta-labeling is #1.** Mechanism: works *with*
  existing weak scores, needs no new data, sizes/filters bets rather than
  predicting direction. Odds quoted: **15–20%**.
- **Grok internally dissented from Camp B:** meta-labeling is *dead-on-arrival*,
  strictly zero EV, because it needs a primary with positive lift and 0/11
  admissible means no primary worth sizing.

### How the R4 tie-breaker resolved it

**On meta-labeling — Grok was right; opencode was wrong.** Unanimous in R4
(claude, deepseek, kilo). The decisive argument (claude, sharpened by deepseek):
the 11 hypotheses failed on **two** modes — small effect size *and* sign-flip
across walk-forward windows. The sign-flip is fatal. A meta-labeler trained on
"good" windows and tested on "flip" windows is just fitting noise with extra
steps. opencode's distinction ("no primary passes the DIRECTION harness" ≠ "no
primary has any lift") is *technically* true but **irrelevant**: a nonzero mean
on a sign-unstable series has zero expected value across the deployment
distribution, and meta-labeling cannot flip a sign it inherits. Meta-labeling
remains a valid *method* — but only on a NEW primary that first shows
sign-stable lift. Applied to the 11 dead families, it is zero-EV.
→ **Meta-labeling odds revised down to ~2%.**

**On intraday/tick crypto — Camp A's mechanism is real but its conclusion is
wrong for THIS system.** Also unanimous in R4. The "liquidity tax doesn't
sign-flip" argument is sound *for a market-maker who posts limit orders and
collects the spread*. But this system is a **cron-scheduled GitHub Actions taker
with 30–60s+ latency and retail taker fees**. It sits on the *paying* side of
the tax, not the collecting side. For tick-resolution signals (order-flow
imbalance, liquidation cascades — alpha decays in 1–5 min or faster), a 60s-late
taker enters *after* smart money has already compressed the edge. deepseek put
it plainly: "for your latency profile, the sign *does* flip — you are the noise
trader paying the tax."

**The one survivor (claude's refinement, the most valuable single insight in
the whole exercise):** Camp A named the right asset class (CRYPTO) and the right
mechanism *type* (a friction cost, not a macro bet) but the **wrong resolution
tier**. Tick ≠ the 8-hour funding cycle. Funding-rate settlement pressure
operates on an 8h reset; its alpha window is *hours*, so 30–60s latency is
irrelevant. It is also OUTSIDE the 11 killed families (the killed "funding-rate
directional" and "funding-arb carry" hypotheses are not the same as an
8h-settlement-pressure timing bet — though this must be pre-registered carefully
to ensure it is genuinely distinct, not a relabel).

### Final answer to Q4

| Approach | Honest 3-mo odds of admissible edge | Verdict |
|---|---|---|
| **Crypto funding-rate / 8h-settlement-pressure timing** | **~9–12%** (claude); ~5% (deepseek/kilo) | The only bet worth considering |
| Intraday/tick order-flow imbalance | <5% | System is on the paying side — skip |
| Meta-labeling (on existing scores) | ~2% | Dead-on-arrival until a primary exists |
| Cross-sectional ranking | ~9–15% standalone but a **2-step bet** (fix universe coverage THEN rank → compounded low odds, single digits) | Not in 3 months |
| Causal-inference feature selection | ~2–8% | Hygiene, not a standalone bet; the problem is empty signal, not feature selection |

**Grok's joint number (Q4 follow-up): ~8% that ANY of the four produces a
forward-confirmed admissible edge in 3 months** — and the individual odds are
positively correlated (all face the same base-rate problem), so the union does
NOT add up.

### The genuine residual disagreement (NOT averaged away)

The engines did **not** fully converge on whether to make the bet at all:

- **claude (R4): make ONE bet** — crypto 8h funding-rate signal as primary,
  meta-labeling as a *conditional overlay only if* the primary shows lift in
  weeks 1–2. Odds ~10% (conditional on data fix). Rationale: the funding-cycle
  space is genuinely un-pre-registered; stopping wastes the one untested
  hypothesis.
- **deepseek (R4): run NEITHER — paper-only-and-stop.** Odds of either path
  <2%. Rationale: don't burn 3 months on a near-zero-EV bet; revisit only if a
  primary passes the harness *after* the data fix.
- **kilo (R4): paper-only for live money, but run both as cheap data-gathering
  probes** — and, notably, kilo adds a hardware caveat: the latency mismatch is
  only fixable by abandoning GitHub Actions cron for a low-latency VPS
  (<50ms to Binance, WebSocket feed). Under the current cron architecture even
  the funding bet is handicapped.
- **Grok (Q4 follow-up): a 4-week time-boxed falsification probe, not a 3-month
  build** — stand up the funding/imbalance feature, run the *existing* harness
  on 6–9 months of history, and stop hard if zero windows clear the gate
  (the expected outcome).

**The honest synthesis of this disagreement:** the engines agree the *3-month
build-out* is negative-EV. They split on whether a *short, cheap, time-boxed
probe* is worth running. The mature position is Grok's + claude's merged: do
**not** commit 3 months; commit a **2–4 week time-boxed falsification probe** on
the crypto 8h funding-rate hypothesis, gated hard on the harness, expected to
fail. If it clears, *then* consider extending. This respects both "don't waste
the one untested idea" (claude) and "don't burn 3 months at <2–10% odds"
(deepseek).

---

## 5. The concrete week-1 action plan the swarm recommends

Ordered. Steps 1–4 are **independent of** whether you decide to make the bet —
every engine agreed they are prerequisites for any future work. Step 5 is the
fork.

1. **Fix the data layer at the writer (BLOCKING GATE).**
   - Dedup at the INSERT path (`INSERT IGNORE` / `ON DUPLICATE KEY UPDATE` on
     the existing `dedup_hash` UNIQUE key).
   - Clamp `confidence > 1.0` at ingestion (146 bad rows).
   - Clear the resolver backlog (~29k stale-OPEN CRYPTO picks; fix
     `outcome_resolver.py` to close the backlog, including a yfinance fallback
     for stale EQUITY picks).
   - Regenerate `pf_registry.json` and confirm CRYPTO pick counts stabilize.
   - No signal test is valid until this is done.

2. **Flip the dashboard to truth.** Default `AUDIT_HEALTH_SOURCE` to
   `pf_registry` (issue #1221) so `/audit` shows canonical numbers, not inflated
   tiles. Add a per-pick harness-verdict badge (RESEARCH / WATCHED / ADMISSIBLE /
   MONEY-READY) — currently zero picks are ADMISSIBLE; the page should say so.

3. **Zero-cost diagnostic before spending anything.** Pull resolved CRYPTO picks
   from `at_raw_picks` (exclude `quan_engine`, `unknown`) and run a time-of-day
   win-rate analysis (the documented 08-09 UTC death-zone vs 22 UTC peak). If
   that structure is real, it is cheap evidence that intraday structure exists
   and the funding probe is worth running. If it evaporates after the data fix,
   that is a strong stop signal.

4. **Pre-register ONE hypothesis in writing, before touching data** (rule
   M-107). The candidate: *crypto 8h funding-rate extreme → directional bias in
   the 2–4h pre-settlement window*, with an explicit predicted sign and
   eff>=0.30 threshold. Log it in `reports/hypothesis_registry.json`. Verify it
   is genuinely distinct from the already-killed "funding-rate directional" and
   "funding-arb carry" families — if it is not, do not register it.

5. **THE FORK — run the harness, then decide.**
   - Backfill 6–12 months of Binance 1h/funding data for the top ~10–15 liquid
     perps into a new `at_intraday_ohlcv` table (one ~20-min job, free API).
   - Run the existing `edge_stability_harness.py` against the pre-registered
     hypothesis on the historical windows. **Do not peek before running.**
   - **Decision rule (binary, no fudging):** >=3/5 same-sign AND eff>=0.30 AND
     >=80 picks/window → extend into a forward paper probe. Anything else →
     declare the domain exhausted, archive the probe, write the stop-bet memo,
     and run the system as paper-only research infrastructure.
   - Do NOT pivot to meta-labeling if step 5 fails — a failed primary is
     precisely the case where meta-labeling has nothing to size.

**What NOT to do in week 1** (explicit, multiple engines): do not buy tick data
yet; do not re-test any of the 11 killed families at new parameters; do not
widen the scanner universe; do not build a regime-conditional harness before
the regime backfill is real.

---

## Bottom line

The system is **not salvageable for live money** and the honest posture is
**paper-only**. It is not broken — it is a research kill-loop working correctly,
having caught 11 fake edges before they cost real capital. The signal space it
was pointed at (free data, daily bars, retail-accessible) is empirically empty,
and that is a property of markets.

- **#1 lever:** fix the data layer at the writer — it is the blocking
  prerequisite that makes every other number trustworthy.
- **3-month bet:** do NOT commit 3 months. Commit a **2–4 week time-boxed
  falsification probe** on a crypto 8h-funding-rate-settlement hypothesis (the
  one mechanism with a friction-cost rationale AND a latency-tolerant time
  scale). Honest odds it clears the harness: **~8–10%, conditional on the data
  fix; ~3% without it.** Expected outcome is failure — and a clean failure is
  itself a valuable, publishable result.
- **Symbol-universe widening:** not the lever — a noise amplifier for CRYPTO,
  a one-shot survivorship-risk gamble for EQUITY.
- **Meta-labeling, intraday/tick order-flow, cross-sectional ranking, causal
  feature selection:** none clears a 10% bar on this architecture; meta-labeling
  is ~2% (dead-on-arrival without a primary).

The unresolved fork the swarm hands back to the operator: **claude says run the
one probe (~10%); deepseek says run neither (<2%, paper-only-and-stop); Grok
says run a hard-gated 4-week probe expecting failure.** All three agree a full
3-month build is negative-EV. The decision between "one cheap probe" and "stop
now" is a risk-appetite call for the human — the swarm cannot make it, and
should not pretend the numbers do.
