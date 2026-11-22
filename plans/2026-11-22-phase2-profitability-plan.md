# Phase 2 Profitability Plan (Item 49)

> **Status:** planning document. It runs no analysis, changes no code, registers no pod, and commits nothing.
> **Programme context:** thirteen strategies tested, twelve killed, one marginal, zero cleared the hurdle
> (US 3-month T-bill **4.32%**; beat-SPY requires Sharpe **1.114**). Honest verdict today: **we would not invest.**
> **Sources:** the item-49 brief (programme endpoint and binding constraints), [`docs/edge_research/12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md`](../docs/edge_research/12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md:90),
> [`plans/2026-11-22-fleet-programme-of-record.md`](2026-11-22-fleet-programme-of-record.md).
> Where a number is quoted, its source is cited inline.

---

## Section 0 — The one-sentence thesis

**Phase 2 exists to convert assumptions into measurements, so that a future verdict can be cost-honest and
certifiable — not to find a new strategy.**

The programme's marginal rate of new-idea generation is not the bottleneck: twelve strategies were killed and
one is marginal. Its bottleneck is that almost every verdict rests on a number nobody measured. This plan is
therefore an agenda of measurements and unblocks, and it is deliberately unoptimistic: nothing in the current
programme is investable, and phase 2 does not change that today.

---

## Section 1 — The measurement backlog, ranked

Ranked by how much of the programme's verdict space each measurement unblocks. Effort is deliberately coarse.

| # | What is missing | Why it blocks progress | How to obtain it | Effort |
|---|---|---|---|---|
| M1 | **Equity transaction cost** — spread + slippage (+ commission) | Every equity verdict is cost-honest only against an *assumed* number. US equities are now largely zero-commission, so the real cost is spread and slippage, and it must be measured, not assumed at 5bp. | Record top-of-book bid/ask for the traded symbols over several weekday sessions; compare intended vs realised fills where any exist; derive a per-symbol median spread plus a slippage distribution. | **Small** |
| M2 | **FX live spread** | The previous attempt returned `BLOCKED_LIVE_MEASUREMENT` because markets were closed on a Sunday. The fix is trivial: a weekday run. Any FX result is currently uninterpretable. | Re-run the same live-spread probe on a weekday during London/NY overlap; log per-pair median spread in pips. | **Small** |
| M3 | **ETF cost** (spread + expense) | ETF strategies inherit the same unmeasured cost problem as equities, plus an expense drag that is never charged. | Same procedure as M1 on the traded ETFs; add the fund expense ratio as a deterministic daily drag. | **Medium** |
| M4 | **Dividend-adjustment method** (equity ETF and bond ETF) | The bond-momentum test explicitly flagged its dividend method as `UNMEASURED`. A total-return series built on the wrong adjustment silently rewrites every momentum result. | Declare one method (total-return index vs adjusted close), implement it in one shared helper, and validate it by reconciling a known ETF's adjusted series against its published total return over a fixed window. | **Medium** |
| M5 | **Commodity futures commission + roll slippage** | Buffy substantiated **roll artifacts**: CL=F −37.63, ZC=F ~−23.6% on 07-15 three years running, NG=F recurring spikes. Until the series is roll-adjusted and the commission charged, no commodity result is trustworthy. | Build a back-adjusted continuous series from individual contracts (roll on volume/OI, not calendar); charge exchange commission and a roll slippage estimate per roll; verify that the known 07-15 artifacts disappear. | **Large** |
| M6 | **Bond accrual / coupon handling** | Bond and bond-ETF returns are price-only unless coupon accrual is modelled; the 4.32% T-bill hurdle is itself a carry number, so comparing price-only bond returns to it is apples-to-oranges. | Carry accrual explicitly (daily coupon or yield-based accrual) and reconcile against a published bond-ETF total return. | **Medium** |
| M7 | **The live machinery's own cost** | The live/paper machinery is currently `UNMEASURED`: we do not know what it actually costs per fill, so any live-vs-backtest comparison conflates strategy edge with machinery drag. | Instrument the execution path to log intended vs filled price and fees per order; aggregate over a month of live/paper rows. | **Medium** |
| M8 | **Slippage scaling for the 2× stress factor** | The programme applies a 2× slippage stress to every fill ([`docs/edge_research/12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md`](../docs/edge_research/12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md:110)), but the base slippage it doubles is itself an assumption for most asset classes. | Derive the base from M1/M2/M5 fills; document the multiplier's justification; re-express the stress tests against a measured base. | **Small** (after M1/M2) |

**Backlog size: 8 measurements.** The single cheapest high-value one is **M2 (weekday FX spread)** — one
weekday run of an existing probe, which converts a blocked measurement into a fact.

---

## Section 2 — The three unblocks that change the verdict

These are the only three changes that can move the programme from "nothing investable" to "a verdict that is
worth trusting". Each is stated as a concrete, testable change with what it unlocks.

### U1 — A historical universe / delisting record

- **What it is:** a point-in-time universe of symbols that existed on each date, including those that later
  delisted or were acquired, plus their delisting returns.
- **Why it changes the verdict:** survivorship bias is unresolved. Its direction is **upward by construction**,
  and its magnitude is `UNMEASURED` because no historical universe exists offline; the 79-symbol panel has
  **zero dead series**. Until this exists, no positive result can be distinguished from a survivorship artifact.
- **Testable form:** re-run the 79-symbol panel against a point-in-time universe with dead series included;
  the delta between the two Sharpe estimates is the measured survivorship magnitude. If the delta is small,
  prior results survive; if it is large, they are condemned.
- **Unlocks:** adjudicates funding carry (Section 3) and retroactively re-prices every equity/crypto result.
- **Effort: large** — it is the highest-value and slowest item.

### U2 — A genuine pre-registered pod with forward rows

- **What it is:** a *prospective* pre-registration, not a relabel. The gate cannot certify anything today
  because 9 of 12 pods are `observe` and the gate hard-codes
  `if status != "pre_registered": res["eligible"] = False` ([`alpha_engine/audit3_tribunal.py:1642`](../alpha_engine/audit3_tribunal.py:1642)),
  and zero ledger rows sit on any pod's own hypothesis.
- **Concrete registration** (from the item-26 memo,
  [`docs/edge_research/12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md`](../docs/edge_research/12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md:104)):
  - Pod `POD-CRYPTO-VWAP-REVERSION-LAGGED`, hypothesis `H-2026-11-22-VWAP-REVERSION-LAGGED-01`.
  - Rule: enter at the **next bar open** after the signal close (**1-bar lag**, never same-bar), z-entry in
    **[1.5, 2.5]**, intrabar first-touch stops (not close-only), **2× slippage** on every fill, no overrides.
  - Minimum **n ≥ 100** forward rows closed after registration.
  - Kill: **CI-LB ≤ 0** at 2× slippage at **day 30 or day 60**. At n ≥ 100: kill if net PF CI-LB ≤ 1.0, or
    IR < 0.5 vs a matched BTC/ETH benchmark, or split-half unstable.
- **The honest tension (must be recorded in the registration itself):** the cryo mean-reversion rule this name
  derives from was **just KILLED at 0bp**. Registering it prospectively is therefore justified as *"a rule we
  can certify"*, **not** *"a rule we expect to win"*. The pre-registration must state that expectation
  explicitly, so it cannot later be relabelled as a candidate that was expected to succeed.
- **Unlocks:** the first forward clock that the gate can actually certify.

### U3 — Measured non-crypto costs

- **What it is:** M1–M6 executed, so each asset class has a measured cost basis instead of an assumption.
- **Why it changes the verdict:** no non-crypto result in this programme is cost-honest. Every equity, ETF,
  FX, commodity and bond verdict currently rests on an assumed number.
- **Testable form:** for each non-crypto strategy, re-state its net return with the measured cost; the
  strategy's verdict is honest only if it survives at the measured cost, not the assumed one.
- **Unlocks:** the first cost-honest non-crypto verdicts, including a fair comparison to the 4.32% T-bill.

---

## Section 3 — What to do about funding carry specifically

Funding carry is the **only non-negative result**. Its numbers are, from the brief: **break-even hold 16.398d**
against a **1.93–2.33d median episode** (an **~8×** structural mismatch), and at median hold **no deployed size
beats the 4.32% T-bill**. It should be settled, not celebrated.

### 3.1 Funding-regime persistence study

- **Question:** how often does a positive-funding episode last **≥ 16.4 days**, historically and per symbol?
- **Design:** classify each symbol's funding rate as positive/negative per interval (8h) from available history;
  compute episode lengths (run lengths of positive funding); report the full distribution, the fraction of
  episodes reaching 16.4 days, and the fraction by symbol and by regime (e.g. trending vs range-bound).
- **Interpretation:**
  - If the answer is **"rarely"** → the strategy is dead and must be recorded as dead, not parked.
  - If **"sometimes, in specific regimes"** → name the regime and treat it as a conditional hypothesis, not a
    general edge.

### 3.2 Maker-execution feasibility test

- **Question:** can the **4 taker fills** be replaced with maker fills, and what fill rate and adverse-selection
  cost follows?
- **Design:** for each leg, measure historical fill probability at the passive price and the subsequent
  adverse move when the maker order fills (adverse selection). Net the maker rebate against that.
- **Stated risk (not a free lunch):** maker fills on **both legs** of a delta-neutral pair is a real
  constraint. If one leg fills and the other does not, the position is **unhedged** directional exposure.
  The test must report the two-legs-both-fill rate separately, and the unhedged-loss distribution for the
  one-leg-filled cases.

### 3.3 Kill condition

**If fewer than ~10% of funding episodes reach 16.4 days, close the file.** Record it as killed with that
number as the reason, and stop re-testing it.

---

## Section 4 — Plumbing work that must precede any new measurement

Four small items. Each is concrete and names its file. None of them produces a result; they only make results
possible.

1. **Give the equity-breakout emitter a real `take_profit`.**
   [`tools/emit_equity_breakout_pod.py:209`](../tools/emit_equity_breakout_pod.py:209) writes
   `"take_profit": None`, and the INSERT at
   [`tools/emit_equity_breakout_pod.py:273`](../tools/emit_equity_breakout_pod.py:273) carries it into
   `trading_picks`. The emitted pod rows are therefore structurally unresolvable: all **131** rows have
   `take_profit = None` (brief). Set a rule-derived `take_profit` (e.g. ATR- or structure-based, declared in the
   strategy) so the resolver has an exit to resolve.

2. **Wire the closed-row mirror into a workflow, or delete it as dead code.**
   [`tools/repair_data_integrity.py:269`](../tools/repair_data_integrity.py:269) defines
   `_repair_signal_outcomes`, which truncates and rebuilds `at_signal_outcomes` from closed `trading_picks`
   rows. A grep of `.github/workflows/` finds **no reference** to `repair_data_integrity` today, so this mirror
   never runs. Either schedule it (dry-run first) or remove it. Leaving it dormant is the worst option: it
   looks like plumbing that exists while never executing.

3. **Land the `audit3-canonical-rows` artifact.**
   Branch `push/n1-n8-research-integrity` at `532413a292e` is **unmerged**, and 4 runs show `total_count: 0`
   (brief). Until it lands, the resolver's output is not retrievable as an artifact, and the digest guard
   (item 4) cannot pass.

4. **Keep the new guard, even though it fails.**
   [`.github/workflows/digest-artifact-guard.yml`](../.github/workflows/digest-artifact-guard.yml:1) is a
   read-only gate asserting that every published digest has retrievable bytes. It currently **FAILS**,
   **correctly** — the artifact from item 3 is missing. Do not disable or delete it to get green; land item 3
   and let it turn green on its own.

---

## Section 5 — What phase 2 explicitly will not do

Stated so a future agent cannot quietly do them:

- **No parameter sweeps to rescue a killed strategy.** A killed strategy stays killed; a better lookback is
  fishing, not evidence.
- **No flipping a pod from `observe` to `pre_registered` to unlock promotion on existing data.** The gate at
  [`alpha_engine/audit3_tribunal.py:1642`](../alpha_engine/audit3_tribunal.py:1642) exists precisely to stop
  this; the decision memo recommends HOLD for all nine
  ([`docs/edge_research/12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md`](../docs/edge_research/12_OBSERVE_TO_PRE_REGISTERED_DECISION_MEMO_2026-11-22.md:90)).
- **No synthesising a commodity term structure from a single front-month series.** A front-month-only series
  cannot represent roll yield or backwardation; synthesising one manufactures the very artifact M5 must remove.
- **No extrapolating crypto order-book depth to equities or FX.** Different venues, different microstructure;
  crypto depth is not a proxy for equity or FX liquidity.
- **No quoting a Profit Factor without its cost basis and its Sharpe/maxDD alongside.** A PF alone is
  unfalsifiable and hides both the cost assumption and the risk taken.
- **No declaring any audit surface authoritative.** audit3's digest is `NOT_REPRODUCIBLE_BY_DESIGN`
  (post-write hashing identifies a snapshot, not a dataset version), so no surface may be treated as the
  canonical truth on its own.

**Count: 6 explicit rejections.**

---

## Section 6 — Sequencing, with dependencies

Ordered by **unblock-per-unit-effort**, not by interest. Each step lists what it depends on and what it releases.

1. **Weekday FX/equity cost measurement** (M1, M2) — **first**: small effort, and it converts the largest
   single assumption into a fact. Depends on nothing. Releases a measured base for the 2× slippage stress (M8).
2. **Roll-adjusted commodity series** (M5) — depends only on contract-level data access; unblocks *any*
   commodity result, which today are all roll-contaminated (CL=F −37.63, ZC=F ~−23.6%, NG=F spikes).
3. **Plumbing** (Section 4: `take_profit`, closed-row mirror, artifact landing) — makes existing rows
   resolvable and digests retrievable. Depends on nothing; is a prerequisite for trustworthy forward rows and
   for the guard to pass.
4. **Funding-regime persistence study** (Section 3.1) — settles the only survivor. Depends on funding-history
   availability; benefits from U1 for a survivorship-clean verdict, but can run with a stated caveat first.
5. **Prospective pre-registration** (U2) — starts the forward clock honestly. Depends on step 3 (plumbing) so
   its rows resolve, and on step 1 so its 2× slippage stress has a measured base.
6. **Historical universe acquisition** (U1) — largest effort, highest value, cannot be rushed. Depends on
   nothing but is last because it retro-adjudicates results from steps 1–5 rather than starting new work.

**Rationale in one sentence:** cheap measurements that retire a whole assumption come first, plumbing that
makes existing evidence resolvable comes next, settling the single survivor and starting an honest forward
clock follow, and the expensive retro-adjudication (the historical universe) comes last because it improves
every earlier verdict rather than enabling any of them.

---

## Deliverable summary

- **Thesis:** phase 2 converts assumptions into measurements so a future verdict can be cost-honest and
  certifiable.
- **Measurement backlog:** 8 (M1–M8); cheapest high-value: M2, weekday FX spread.
- **Three unblocks:** U1 historical universe, U2 prospective pre-registration, U3 measured non-crypto costs.
- **Funding-carry kill:** < ~10% of episodes reach 16.4 days → close the file.
- **Plumbing items:** 4.
- **Explicit rejections:** 6.
