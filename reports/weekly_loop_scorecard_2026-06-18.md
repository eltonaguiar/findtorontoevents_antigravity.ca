# Weekly Loop Scorecard — 2026-06-18 (money-maker-ready June edition)

Cycle run by claude-opus-4-8 (gx10). Canonical plan: `docs/MONEY_READY_MASTER_LOOP_2026-06.md`.
Every number below re-verified by direct SQL against `ejaguiar1_stocks` (intrabar canonical surface
`at_signal_outcomes`, `intrabar_status IN ('TP_HIT','SL_HIT')` for decisive WR/PF). Read-only.

## TL;DR
**0/9 classes pass; no promotable candidate this cycle — and the headline finding is structural, not
strategy-level: the entire fresh decisive intrabar cohort is a single-day (2026-06-09) snapshot, and the
resolution lane has not produced new decisive evidence since ~06-13 (~5 days stale).** Every per-class
verdict this week is therefore a single-regime reading, not a durable class assessment. The master-loop's
own defenses (n_eff + time-split + CI-LB) correctly caught two would-be "winners" (COMMODITY, FOREX rsi2)
as single-day mirages.

## MEASURE — honest ledger (intrabar canonical, 2026-06-18)
| Class | n | WR% | PF | avg pnl% | verdict |
|---|---|---|---|---|---|
| CRYPTO | 1155 | 32.4 | 0.727 | −0.406 | FAIL |
| EQUITY | 119 | 34.5 | 0.46 | −1.237 | FAIL |
| COMMODITY | 115 | 34.8 | 1.048 | +0.068 | FAIL (n=100 crossed — see FORWARD) |
| FOREX | 95 | 41.1 | 1.102 | +0.031 | INSUFFICIENT_N (approaching 100) |
| ETF | 16 | 0.0 | 0.0 | −2.849 | INSUFFICIENT_N |
| BOND | 6 | 33.3 | 2.242 | +0.516 | INSUFFICIENT_N |
| FUTURES | 16 | 31.2 | 0.49 | −0.602 | INSUFFICIENT_N |

Only T2-shaped strategy lead surfaced: FOREX `forex_rsi2_mean_reversion` (n=20, WR 60%, PF 2.15) — verified in ACT below.

## DIAGNOSE — H1–H5 (focus classes CRYPTO + FOREX)
- **H1 (resolver/measurement): NOT RED (amber).** The one-sided checker FAILs (FINDING#12: 33 strategies
  100% one-sided) but that is on the **raw lane `at_raw_picks`** (16 news/social + 17 strategies). Cross-checked
  the 17 strategies against the canonical intrabar surface: the large ones (`crypto_liquidity_wick_reversal_v1`
  4904, `atr_percentile_gate` 3306) are **100% TIME_EXIT** there (excluded from decisive WR — reachability, not a
  one-sided bug); `cross_sectional_reversal` is mixed (1 TP / 7 SL). So the focus-class honest numbers are
  trustworthy; FINDING#12 is a raw-lane coarse-resolver artifact (H5), already filed. **No HALT.**
- **H5 (coverage): THE dominant issue this week (see below).**
- CRYPTO → **H2** (genuine no/negative edge: PF 0.727 at n=1155 is not measurement). FOREX → **H3** (thin: n=95; lead at n=20).

## H5 HEADLINE — the cohort is a single day, and the lane has stalled
Decisive intrabar rows by resolution day, per class:
| Class | decisive n | % on 2026-06-09 | # distinct days |
|---|---|---|---|
| CRYPTO | 1155 | **87%** (1005) | 3 |
| FOREX | 95 | **92%** (87) | 3 |
| COMMODITY | 115 | **70%** (81) | 3 |
| EQUITY | 119 | **87%** (104) | 3 |

- Whole-surface `intrabar_status`: **TIME_EXIT 41,547 (96.3%)**, SL_HIT 1,082, TP_HIT 525. Decisive = 3.7%
  → the reachability problem at scale (TPs are not reached; "resolution" is overwhelmingly time-out).
- **Last intrabar resolution processing ~2026-06-13; ~5 days (122h) with no new resolutions.** The hourly
  re-resolve driver (Addendum J P0A) appears stalled **again** — a recurring failure that **starves every
  pre-registered forward checkpoint** (rsi5070 n≥150, handoff OOS, pead).

**Implication:** all per-class WR/PF this week are ~70–92% a single regime day (06-09). They are not
durable. Fixing the lane stall + de-concentrating the cohort across days is prerequisite to any class verdict.

## FORWARD — pre-registered checkpoint judgments (overdue, now judged)
- **pead_equity (06-14 gate): CONTINUE-SHADOW.** Shadow log `verified_strategies/paper_pilot/equity_pead_drift_paper_log.jsonl`
  = 76 SIGNAL rows, **0 resolved** (30-day holds; earliest 06-05 signals mature ~07-05). Below the 100-pick bar,
  no PF/WR computable. Data-starved (H3, cache = 46 stale symbols), **not failing — do not kill.** Reassess ~07-05.
  (Hygiene flag: first log row symbol is placeholder "XYZ".)
- **COMMODITY n=100 verdict: FAIL (definitive).** n=115 but **n_eff = 32.4** (21 symbol-day clusters, ρ=0.57);
  cluster **CI-LB = 0.177** (≪1.15 bar); **time-split IS (all 06-09) PF 2.78 / WR 56% → OOS PF 0.255 / WR 14%**;
  concentration HHI 0.184 (SI=F 30%). Single-day mirage. **Stays rotated out.**
- **FOREX n=100: not yet crossed** (n=95). Approaching; judge next cycle with the same battery.

## ACT — verified the lone lead (no batch pre-registered)
**FOREX `forex_rsi2_mean_reversion`: PROMISING-BUT-NOT-PROMOTABLE.** n=24 decisive:
- **NET-of-cost PF 2.89** (2bp majors / 6bp JPY; gross 3.25) — *survives cost*, unlike the FOREX consensus that
  died sub-1bp. Cluster CI-LB 2.09.
- **But fails the bars:** n_eff = **18.6** (≪80); **time-split IS (all 06-09) PF 11.26 / WR 92% → OOS PF 0.988 / WR 42%**;
  AUDUSD concentration 38% (>35%). Same single-day-06-09 dominance as COMMODITY.
- **Decision: HOLD in shadow-forward; grow n across DISTINCT days/regimes.** No tuning batch pre-registered —
  there is no falsifiable hypothesis beyond "accrue more days" (and the lane is stalled, so accrual is blocked
  pending the H5 fix). Do-not-tune until n_eff and time-split can be assessed off >1 regime day.

## RATCHET — next-cycle actions (priority order)
1. **P1 (operational, highest leverage): restart/repair the intrabar re-resolve driver.** It has not produced
   new resolutions since ~06-13 (~5 days). Until it accrues, the forward-confirmation engine is dead and every
   checkpoint starves. This is the recurring stall (Addendum J) — needs a durable fix + a freshness alarm
   (alert if `MAX(intrabar_resolved_at)` is >24h stale), not another one-shot kick.
2. **De-concentrate before trusting any verdict:** require a cohort to span ≥N distinct resolution days (e.g. ≥5)
   before a class/strategy verdict is published; the 06-09 single-day dominance invalidates point estimates.
3. **FOREX rsi2:** keep in shadow-forward; re-judge when n_eff≥80 across distinct days (blocked on #1).
4. **CRYPTO:** no-edge hold (PF 0.727 at n=1155); rely on forward candidate `crypto_rsi5070_us` (~06-25 gate, n≥150) — also blocked on #1.
5. **pead_equity:** reassess ~07-05 when 30-day holds mature.
6. **Build the missing `tools/monkey_test_benchmark.py`** (Addendum H called it the top unbuilt defense; absent from main).

## Hard-rule compliance
Every figure direct-SQL re-verified · no backtest run (no pre-registration needed this cycle) · do-not-relitigate
respected (FOREX rsi2 small-n was on the list; it is HELD, not promoted) · read-only DB · isolated worktree.
