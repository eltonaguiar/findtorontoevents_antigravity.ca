# PROMOTION GATE — one page, non-negotiable

**Status:** 0 of 9 asset classes pass. **Nothing is sized. Zero capital sanctioned.**
**Last revised:** 2026-11-22 · Owner: mercury3/copilot · Applies to every class, every strategy, every future PR.

---

## The rule

A strategy may be **sized with real capital** only when it clears all five gates
**in order**, on **one population of picks**, with **every number reproducible from
a committed artifact**.

### Gate 0 — Provenance (binary, no partial credit)

The evidence must be **genuine forward data**. A forward observation is written
**before** its outcome exists: `created_at < closed_at` for every row.

- Rows failing this are **backfilled** and count for **nothing**. Not a discount — **zero**.
- Rows resolved before the hypothesis was registered count for **nothing**.
- Required: `n_forward ≥ 100` per class.

> Why first: this alone rejected H-119, which the registry called *"the project's
> strongest HONEST money-ready lead"* — 430 rows, **0** forward, median write-lag
> 103 days, 25% pre-registration.

### Gate 1 — Cost (was the binding constraint; superseded by Gate 0, see below)

Report **gross, fees and net separately, always**. Net must be positive after the
**measured** round trip for the venue and size you will actually trade.

- An **assumed** cost may gate a **rejection**, never a **promotion**.
- ETF execution cost is currently **UNMEASURED** (daily OHLC cannot resolve sub-2bp;
  Corwin-Schultz and Roll both fail structurally — 0/7 usable). Until NBBO or L2 data
  exists, **no ETF strategy can pass this gate.**
- Required: net > 0 at **2× your believed cost**.

> Why: five independent measures — intraday crypto (2.5bp vs ≥12bp), ETF breakout
> (4.7 vs 5.1), the breakout pod (PF 1.479→1.00), funding carry (3.18%/yr vs 3.5%
> T-bill), H-119 (+12.8bp vs 16bp) — all landed on *gross edge ≈ round-trip cost*.

### Gate 2 — Statistical survival

| test | requirement |
|---|---|
| cluster-robust CI | Sharpe / PF CI-LB > 1.15, clustered by **symbol-day**, not trade |
| trials disclosed | `n_trials` published with every result; DSR computed against it |
| PBO (CSCV) | ≤ 0.35. **PBO = 0.50 means selection is a coin flip; PBO = 0.70 means it is worse.** |
| stress | survives **both** 2000–02 and 2008, or the gap is named as untested |
| stability | effect present in **≥2 consecutive** sub-periods, split basis **stated** |

> Why: the monthly tactical search scored **PBO = 0.700**. The cost-horizon ladder
> was once published as a median over **positive cells only**, doubling it.

### Gate 3 — Falsification

The strategy must have survived a **pre-registered kill test** whose thresholds were
committed **before** the statistic was computed.

- Registration commit hash recorded in the result file.
- Registration **after** seeing the number is **inadmissible** — say so explicitly.
- Editing a threshold voids the test permanently.

### Gate 4 — Forward clock

After passing 0–3, **paper-trade forward** for ≥12 months or ≥200 prints, whichever
is longer, and re-run gates 1–3 on the **forward** population only.

- Backfilled or in-sample data may **not** be used to shorten the clock.
- Live paper book must be **mark-to-market**, never realised-only (a realised-only
  book hides drawdown while you are in the trade).

---

## Labels — use these words exactly

| label | means |
|---|---|
| **SIZED** | passed all five. None exist. |
| **SHADOW** | passed 0–3, on the forward clock |
| **CANDIDATE** | positive but fails ≥1 of 0–3 |
| **NOT ESTABLISHED** | insufficient data in either direction |
| **REFUTED** | failed a pre-registered kill test |
| **UNMEASURED** | the number does not exist yet — never substitute an assumption |

Never write "promising", "strong", "proven", "edge" without one of these labels
attached and the gate it refers to.

---

## Current state (2026-11-22, updated end of round 31)

Superseded values are struck through rather than deleted, so a reader who saw the
earlier table can see what changed and why.

| class | label | blocking gate |
|---|---|---|
| CRYPTO directional | **REFUTED** | −16.04 bp, PF 0.90 (CI-LB 0.84), n=8,733. Gate 0 (0 forward) + Gate 3 (OUTSIDE-2 killed, worst 50-window −152bp) |
| CRYPTO funding carry | **REFUTED** ~~CANDIDATE~~ | Gate 2 — +3.555%/yr mean vs 3.50% T-bill is **5 bp** of headroom, but the halves disagree (+5.96%/yr → **+1.24%/yr**) and 6/28 rolling blocks are negative. Window-dependent, not persistent. |
| ETF breakout | **REFUTED** | Gate 3 (OUTSIDE-1 killed, both conditions). Gross edge is real (+22.43 bp, t=+7.32); Gate 1 spread is **UNMEASURED** — sampler live, zero samples. |
| ETF tactical allocation | **REFUTED** ~~CANDIDATE~~ | Gate 2 — loses to static 60/40 (Sharpe 0.81 vs 0.86); PBO 0.70 |
| EQUITY | **NOT ESTABLISHED** | +19.29 bp but PF CI-LB 0.89; Gate 0 + Gate 1 unmeasured |
| COMMODITY trend | **REFUTED** | −369.80 bp, PF 0.08 (CI-LB 0.02), n=43 |
| FOREX | **REFUTED** | −15.45 bp, PF 0.66, n=251; three desks negative |
| BOND | **REFUTED** ~~NOT ESTABLISHED~~ | −18.22 bp, PF 0.66, n=35 |
| FUTURES / vol scaling / breakout pod | **REFUTED** | unreproduced or refuted (FUTURES n=12, INSUFF-N) |
| `mega_mutation` emitter | **QUARANTINE** ~~CANDIDATE~~ | 4/6 falsification tests: median CI includes zero; 16/105 duplicate rows |
| Vol risk premium | **ESTABLISHED** (existence) / harvest **RUINED** | +357.9 bp, t=+46.50 — and equity ≤ 0 at 2020-03 when harvested |
| GDX/SLV pairs | **REFUTED** | ADF OOS +0.15 (need < −2.86); nets +2.23%/yr < cash |
| Polymarket calibration | **ESTABLISHED** | Brier skill +0.4956, n=362. Mid-range deviation is SHADOW (p≈0.086, spread unmeasured). |

**Controls that catch most of what gets past a human reviewer**
- **Clairvoyance control:** a strategy that sees next period's return must dominate.
  If it does not, the harness is broken. (This caught a look-ahead that produced
  Sharpe 1.83 vs 0.73 real.)
- **All-cells reporting:** never a median over a filtered subset.
- **Named split basis:** `trades` / `calendar` / `symbols` are three different tests.

---

## THE BINDING CONSTRAINT IS NOW PROVENANCE, NOT STATISTICS (2026-11-22, round 31)

Every statistical avenue has been walked to its end. The programme now knows:

- **0 of 7 asset classes** clears a cluster-robust PF of 1.0. All-classes net is
  **−13.40 bp/pick at t = −3.38** over 10,593 de-duplicated picks.
- **0 of 67 emitters** is established. The last candidate (`mega_mutation`) scored
  **4/6** on a falsification battery and is **QUARANTINED**.
- Four independent hypothesis families were tested and refuted this round:
  vol risk premium harvest (**RUINED**, equity ≤ 0 at 2020-03), GDX/SLV pairs
  (**REFUTED**, ADF OOS +0.15), cross-venue funding arb (**REFUTED**, best
  +1.56%/yr), funding carry (**REFUTED** as a stable cash-beater).

What remains is one gap that no further statistics can close:

| artifact | `created_at` present? | provenance test possible? |
|---|---|---|
| `resolved_closed_picks_net.json` (10,968 picks) | **no** | **no** |
| `forward_observations.jsonl` (430 H-119 rows) | yes | **yes — result: 430/430 backfilled** |

So the single test that separates **skill from hindsight** — was the pick written
before its outcome? — has been run on the only artifact that permits it, and it
failed completely. On every other artifact it cannot be run at all.

**Concrete demonstration of why this decides everything:** `mega_mutation` hits its
take-profit first 56.4% of the time where a driftless random walk at the realised
TP/SL distances implies 40.9% (binomial p = 1.7 × 10⁻³). That is either genuine
directional skill or TP/SL levels placed with hindsight. **No test available on
this data can distinguish those two explanations.** The statistics are not the
limitation; the recording is.

**Therefore Gate 0 is the only gate that matters until it is fixed.** The next
round of work should not be another backtest. It should be making the system write
`created_at`, `signal_ts`, and the TP/SL levels **at emit time**, immutably,
before any outcome exists. Until that exists, every result — positive or negative —
is unfalsifiable in the one direction that counts.

---

## What this page is for

It exists so a rejection cannot be argued into a promotion after the fact, and so a
promotion cannot be assembled out of parts that were never compatible. Every time
this programme has believed a positive result, one of these five gates was the
thing that had been skipped.

*Backtests and single measurements only. Not investment advice.*
