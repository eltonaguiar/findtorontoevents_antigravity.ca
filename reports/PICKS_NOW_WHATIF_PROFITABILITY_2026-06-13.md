# PICKS-NOW What-If Profitability — Honest First-Touch Re-Resolution

**Date:** 2026-06-13  |  **Mode:** READ-ONLY (no commits / no DB writes / no generators)
**Skill:** /money-maker-ready  |  **Author:** money-ready subagent

> Headline question: *would the picks-now picks have been profitable?* Answered with
> conservative SL-wins-ties first-touch against real OHLC bars, net of cost, per asset
> class and per source/score-bucket, with cluster-bootstrap PF CI-LB.

---

## 0. Cohort & method

- **Engine write target:** `picks_now_tracker` (ejaguiar1_stocks) — NOT `trading_picks`.
  Writers: `tools/picks_now_professional.py` (inline) + `tools/save_picks_to_db.py`.
  Deduped view: `vw_picks_now_dedup` (1 row / symbol / direction / UTC-day).
- **Raw rows in table:** 647.  **Deduped (sym|dir|date, tp/sl>0):** 186.
- **Direction:** 100% STRONG_BUY (long-only). There is NO short cohort — a long-only vs
  short-only what-if is moot.
- **Bars:** stock_ohlcv 1h (EQUITY/ETF/COMMODITY); crypto_ohlcv 1h (none in cohort);
  fx_prices/fxp_price_history daily (FOREX). Bars end **2026-06-12T18:30:00+00:00**.
- **Horizon:** 10d / 240 1h-bars (matches engine TIME_EXIT). First-touch: LONG low<=SL -> SL_HIT
  else high>=TP -> TP_HIT; same-bar tie -> SL (conservative).
- **Cost (round-trip, %):** CRYPTO 0.16, EQUITY/ETF 0.04, COMMODITY 0.03, FOREX 0.02 (0.06 JPY).

### Resolution status of the deduped cohort

| status | n | meaning |
|---|---|---|
| TP_HIT | 13 | hit take-profit first (WON) — verdict-grade |
| SL_HIT | 31 | hit stop-loss first (LOST) — verdict-grade |
| TIME_EXIT | 0 | full 10d elapsed, neither touched — verdict-grade |
| MTM_OPEN | 130 | horizon NOT elapsed; interim mark-to-market only |
| NO_DATA | 12 | no forward bars (all 8 FOREX + 4 equity picks dated on/after last bar) |

**Verdict-grade decisive n = 44** (TP_HIT+SL_HIT+TIME_EXIT). The other
130 are too recent to have a 10-day outcome — bars only run to 2026-06-12.

---

## 1. Whole-cohort honest verdict

| cohort | n | WR% | gross PF | net PF | net CI-LB | net CI-UB | n_eff | avg net% | cum net% |
|---|---|---|---|---|---|---|---|---|---|
| ALL decisive (TP/SL/TIME) | 44 | 29.5 | 0.832 | 0.823 | 0.397 | 1.286 | 44 | -0.662 | -29.15 |
| ALL still-open (interim MTM) | 130 | 60.0 | 3.633 | 3.497 | 2.625 | 5.064 | 130 | 1.473 | 191.43 |
| ALL rows (decisive + interim MTM) | 174 | 52.3 | 1.712 | 1.674 | 1.175 | 2.358 | 174 | 0.933 | 162.28 |

**Confirms the displayed -14.4% direction.** The live panel (`picks_now_track_record.json`: 47/206 resolved, WR 31.9%, avg -0.31%, cum -14.4%) is
HONEST and if anything generous. My independent first-touch on the decisive subset gives
net PF **0.823**, WR **29.5%**, cum **-29.15%** over n=44.
The still-open 130 picks show a POSITIVE interim mark (net PF 3.497), but that is an
UNREALISED mark-to-market in a one-week megacap rally — none has had time to hit its SL, so it is
not an outcome. On REALISED first-touch the cohort is **NET-LOSING**: net PF well below 1.0 and a
CI-LB (0.397) nowhere near the 1.15 gate.

---

## 2. Per-class verdict (decisive only)

| class | n | WR% | gross PF | net PF | net CI-LB | n_eff | avg net% | cum net% |
|---|---|---|---|---|---|---|---|---|
| EQUITY | 42 | 31.0 | 0.875 | 0.865 | 0.397 | 42 | -0.502 | -21.08 |
| ETF | 1 | 0.0 | 0.0 | 0.0 | n/a | 1 | -4.04 | -4.04 |
| COMMODITY | 1 | 0.0 | 0.0 | 0.0 | n/a | 1 | -4.03 | -4.03 |

Plus what the cohort CANNOT speak to: FOREX (8 picks) and BOND/CRYPTO (0 picks) — FOREX has
no overlapping bars (fx tables end 2026-05-12) so it is **unresolvable** here, not a verdict.

### Per-class incl. interim open picks (decisive + MTM) — NOT verdict-grade

The MTM rows are unrealised marks in a favourable one-week window; they have not had time to
hit SL. Treat the PF/CI-LB here as an OPTIMISTIC upper bound, not an outcome.

| class | n | WR% | net PF | net CI-LB | avg net% | cum net% |
|---|---|---|---|---|---|---|
| EQUITY | 154 | 50.6 | 1.516 | 1.051 | 0.758 | 116.78 |
| ETF | 10 | 90.0 | 8.98 | 3.445 | 3.224 | 32.24 |
| COMMODITY | 10 | 40.0 | 2.268 | n/a | 1.326 | 13.26 |

---

## 3. Per-source / per-score-bucket (decisive only)

The engine emits a single source (the multi-factor QuantScorer); the differentiator is the
composite `score`. Buckets: STRONG_BUY>=75, 55-75, <55 (all rows are labelled STRONG_BUY but
score varies). Also split by top emitted symbols.

| score bucket | n | WR% | net PF | net CI-LB | n_eff | avg net% | cum net% |
|---|---|---|---|---|---|---|---|
| score>=90 | 43 | 30.2 | 0.843 | 0.397 | 43 | -0.584 | -25.12 |
| score 75-90 | 1 | 0.0 | 0.0 | n/a | 1 | -4.03 | -4.03 |

### Top symbols by decisive n

| symbol | class | n | WR% | net PF | avg net% | cum net% |
|---|---|---|---|---|---|---|
| ORCL | EQUITY | 6 | 0.0 | 0.0 | -7.39 | -44.34 |
| GOOGL | EQUITY | 5 | 0.0 | 0.0 | -4.12 | -20.6 |
| AMZN | EQUITY | 4 | 0.0 | 0.0 | -4.54 | -18.16 |
| AAPL | EQUITY | 4 | 0.0 | 0.0 | -4.04 | -16.16 |
| SBUX | EQUITY | 4 | 100.0 | inf | 8.31 | 33.24 |
| AMD | EQUITY | 4 | 75.0 | 4.24 | 5.71 | 22.84 |
| EQIX | EQUITY | 3 | 0.0 | 0.0 | -4.04 | -12.12 |
| PANW | EQUITY | 2 | 0.0 | 0.0 | -7.04 | -14.08 |
| MU | EQUITY | 2 | 100.0 | inf | 9.96 | 19.92 |
| MRVL | EQUITY | 2 | 100.0 | inf | 9.96 | 19.92 |
| LRCX | EQUITY | 1 | 100.0 | inf | 16.46 | 16.46 |
| AMAT | EQUITY | 1 | 100.0 | inf | 15.66 | 15.66 |
| UBER | EQUITY | 1 | 0.0 | 0.0 | -4.74 | -4.74 |
| MSFT | EQUITY | 1 | 0.0 | 0.0 | -4.84 | -4.84 |
| VGT | ETF | 1 | 0.0 | 0.0 | -4.04 | -4.04 |

---

## 4. What-if: would ANY honest subset clear net CI-LB > 1.15 @ n_eff >= 80?

Gate (Master loop §2/§7): **net PF CI-LB > 1.15 at n_eff >= 80** (forward).

**Verdict-grade subsets use DECISIVE outcomes only** (TP/SL/TIME). A subset that mixes in
still-open interim mark-to-market (MTM) is NOT verdict-grade: those picks have only had 0-6
days of an unrealised, favourable-regime mark and have not yet had a chance to hit their SL.
Including them is exactly the inflation trap this exercise guards against, so the MTM rows below
are shown for context but DISQUALIFIED from a 'pass'.

| subset | n | n_eff | net PF | net CI-LB | verdict-grade? | clears gate? |
|---|---|---|---|---|---|---|
| class=EQUITY | 42 | 42 | 0.865 | 0.397 | yes | no |
| class=ETF | 1 | 1 | 0.0 | n/a | yes | no |
| class=COMMODITY | 1 | 1 | 0.0 | n/a | yes | no |
| score>=90 | 43 | 43 | 0.843 | 0.397 | yes | no |
| score 75-90 | 1 | 1 | 0.0 | n/a | yes | no |
| ALL decisive | 44 | 44 | 0.823 | 0.397 | yes | no |
| ALL decisive+MTM (interim, NOT verdict-grade) | 174 | 174 | 1.674 | 1.175 | NO | interim-only (disqualified) |

**RESULT: NO verdict-grade subset clears net CI-LB > 1.15 @ n_eff >= 80.** Not a single class,
score bucket, or the whole decisive cohort comes close — every one has net PF < 1.0 and a
net-PF CI-LB around 0.4. The highest-scoring picks (score>=90) are among the WORST. The ONLY
subset that nominally clears the gate is `ALL decisive+MTM` (net PF 1.67, CI-LB 1.18) and it
is an **interim mark-to-market artifact** — 130 of its 174 rows are open picks marked at a
favourable unrealised price in a one-week megacap rally, with no chance yet to hit SL. It is
DISQUALIFIED. On realised first-touch outcomes the picks were money-LOSING, not money-ready.

Long-only/short-only filter is N/A (100% long). No score threshold, class filter, or symbol
filter produces a profitable honest subset.

---

## 5. Over-emission magnitude

- **Raw rows 647 -> 186 distinct (symbol,direction,date) with valid TP/SL
  = 3.48x inflation** (and 647 -> 206 = 3.14x on the pure
  symbol|dir|date dedup, matching `vw_picks_now_dedup`). Every displayed 'open pick' count is
  ~3x the real distinct daily decisions.
- The 392-row `picks_now_live_pnl.json` 'open picks' panel is per-EMISSION: the same
  symbol-day appears many times. Worst offenders (one symbol, one day):

| symbol | date | emissions (one day) |
|---|---|---|
| AMZN | 2026-06-06 | 31 |
| AVGO | 2026-06-06 | 18 |
| GOOGL | 2026-06-06 | 18 |
| AAPL | 2026-06-06 | 18 |
| NVDA | 2026-06-06 | 18 |
| AMD | 2026-06-06 | 17 |
| MU | 2026-06-06 | 13 |

**Impact on the open-pick count:** the live page advertises 392 open picks; the true distinct
(symbol, direction, day) count is 206 (and only 186 with valid TP/SL). So **~47% of the open-pick
headcount is duplicate same-day re-emissions.** The over-emission comes from the 06/12/18 UTC
cron firing multiple times + intra-run retries with NO unique constraint on the table; the
per-symbol-day guard in both writers only dedups WITHIN a single run, not across the day's runs
that already committed (the guard reads `WHERE DATE(generated_at)=CURDATE()` so a later UTC-day
re-run on a NEW calendar day re-inserts).

**Impact on avg PnL / WR:** because dupes share one underlying price move, the raw
(un-deduped) panel would weight heavily-emitted names (AMZN 31x) far more than singly-emitted
ones, biasing avg PnL toward whatever the megacaps did on 2026-06-06. The honest figures above
are all DEDUPED, removing this bias; the displayed track-record JSON is already deduped via
`vw_picks_now_dedup` (good), but the `picks_now_live_pnl.json` open-pick surface is NOT.

---

## 6. Bottom line

1. **Honest verdict: the picks-now cohort was NET-LOSING.** Decisive n=44: WR 29.5%,
   net PF 0.823, cum -29.15%. This CONFIRMS (does not refute) the displayed
   -14.4% / 31.9% WR. First-touch agrees with the live panel.
2. **No verdict-grade profitable subset.** On REALISED first-touch outcomes, no class, score
   bucket, or symbol filter clears net CI-LB>1.15 @ n_eff>=80 — none even clears net PF 1.0
   (decisive net-PF CI-LB ~0.40). score>=90 picks are NOT better. The only nominal pass is
   decisive+MTM, an unrealised mark-to-market artifact in a 1-week megacap rally -> disqualified.
   Long-only/short-only is moot (100% long).
3. **Per-class:** EQUITY (the entire resolvable cohort, n=42) is the bleeder;
   ETF/COMMODITY n is tiny and also negative; FOREX/CRYPTO/BOND unresolvable or absent.
4. **Over-emission: 3.14x raw inflation; ~47% of the 392-pick open panel is duplicate same-day
   re-emissions** (AMZN 31x on 2026-06-06). The live track-record JSON is correctly deduped;
   the live open-pick PnL JSON is NOT and overstates the pick count.

**Action implication:** picks-now is a research/paper bridge only (it self-labels 0/9 classes
money-ready). These results reinforce: do NOT size up; the engine's STRONG_BUY long-only momentum
picks have negative honest expectancy at first-touch over 6/6-6/12. Add a UNIQUE(symbol,direction,
DATE(generated_at)) constraint to kill the over-emission, and stop surfacing raw emission counts.

**Caveats:** decisive n is small (mostly within-horizon); 130 picks are still open (interim MTM
shown, also negative). The window is one week of a strong-megacap-pullback regime. FOREX could
not be tested (no overlapping bars). Re-run after 2026-06-22 when the 10d horizons elapse.
