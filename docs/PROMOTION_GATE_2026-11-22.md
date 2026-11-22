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

### Gate 1 — Cost (the binding constraint)

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

## Current state (2026-11-22)

| class | label | blocking gate |
|---|---|---|
| CRYPTO directional | **REFUTED** | Gate 0 (0 forward) + Gate 3 (OUTSIDE-2 killed, worst 50-window −152bp) |
| CRYPTO funding carry | **CANDIDATE** | Gate 1 — 3.18%/yr net at VIP0 vs 3.5% T-bill. Clears at VIP1. Delta drift measured at exactly 0. |
| ETF breakout | **REFUTED** | Gate 3 (OUTSIDE-1 killed, both conditions) |
| ETF tactical allocation | **CANDIDATE** | Gate 2 — loses to static 60/40 on Sharpe; PBO 0.70 |
| EQUITY | **NOT ESTABLISHED** | Gate 0 + Gate 1 unmeasured |
| COMMODITY trend | **NOT ESTABLISHED** | spec-dependent: basket-binary = 43% duty cycle; per-member SMA differs |
| FOREX | **REFUTED** | three desks negative |
| BOND | **NOT ESTABLISHED** | n too small; ballast only |
| FUTURES / vol scaling / breakout pod | **REFUTED** | unreproduced or refuted |

**Controls that catch most of what gets past a human reviewer**
- **Clairvoyance control:** a strategy that sees next period's return must dominate.
  If it does not, the harness is broken. (This caught a look-ahead that produced
  Sharpe 1.83 vs 0.73 real.)
- **All-cells reporting:** never a median over a filtered subset.
- **Named split basis:** `trades` / `calendar` / `symbols` are three different tests.

---

## What this page is for

It exists so a rejection cannot be argued into a promotion after the fact, and so a
promotion cannot be assembled out of parts that were never compatible. Every time
this programme has believed a positive result, one of these five gates was the
thing that had been skipped.

*Backtests and single measurements only. Not investment advice.*
