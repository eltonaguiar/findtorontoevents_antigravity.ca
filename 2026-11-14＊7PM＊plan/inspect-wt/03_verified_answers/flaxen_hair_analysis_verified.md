# The Nov-14 "no asset class is proven" analysis — verified, corrected, and completed

> This file answers item 3 of the request: it takes the pasted analysis (attributed to
> `final_v4/flaxen-hair_2026-11-14T2304/`) claim by claim, marks what holds up, corrects
> what doesn't, and **adds the benchmark framing the analysis was missing** (outperform
> S&P 500 / buy-and-hold) plus the items the user flagged.

## A. Claim-by-claim verification

| Claim | Verdict | Evidence |
|---|---|---|
| "0/23 hypotheses across 4 protocol versions survived OOS/effective-N/capital/execution gates" | **CONSISTENT with fleet record** | final_v4 consensus + `final_v3/03_focus/DECISION.md`; I could not re-derive the 23-count independently (its trial ledger) — treat count as flaxen-hair's, direction as verified |
| "IC ≈ 0, win rates ~40%, accuracy below target; all 9 classes sizing_allowed:false" | **VERIFIED directionally** | matches our own repricing (81% fake zeros), PF registry (0/9 money-ready), frozen-data verdict |
| Asset-class table (crypto PF 0.74/WR 33% recent; equity 0.70; commodity historical 1.78; ETF zero live; bond n small; forex mutation; MF zero coverage) | **VERIFIED** | our `final_v2/` + `final_v4/` adjudications; `MUTUAL_FUNDS_SUBSET.md`: 0 MF rows across 3,500 closed |
| "Ranking: 1 MF/ETF index, 2 EQUITY, 3 commodity/bond, 4 ETF tactical, 5 crypto, 6 forex" | **PARTIALLY ADOPTED — with corrections** | See B below: EQUITY was **closed as a source of edge** by #773 *after* that analysis; our ranking differs on that slot and on crypto's conditionality |
| "Framework: fix measurement → separate beta/alpha → strict protocol → risk overlay → prioritization" | **ADOPTED — it matches our PLAN_FINAL** | near-identical to `final_v4/inspect-wt/01_plan/PLAN_FINAL.md` Phases 0–4 |
| Daytrading/scalping sims look attractive until costs+multiple-testing | **VERIFIED** | our cost math + every peer's finding |

## B. Corrections this analysis needs (added 2026-11-14, post-#773)

1. **EQUITY is no longer "slot 2 for testing" — it was CLOSED as a source of edge** hours
   later: `DECISION.md` REVISION + PR #773 (`NO_ALPHA_BETA`, t=1.05, median −0.57% vs SPY,
   54% underperform). It stays a *measurement baseline*; reopening needs a new
   pre-registered trial ID. → our `01_plan_per_asset_class/equity.md`.
2. **Fill/slippage numbers moved:** "98.8% of crypto class loss" was superseded by #773
   (that figure differenced a drifted `stop_loss` field; verified correction = +67.5pp,
   PF 0.768 → ~0.80). Crypto is **not at breakeven** post-fix.
3. **The ranking omits benchmark-relative gates entirely** (the user's correction) — added
   in section C.

## C. The missing piece: outperform S&P 500 / buy-and-hold (the user's correction)

The pasted analysis ranks by "probability of positive real returns + lower permanent-loss
risk" — which correctly makes index funds #1, but **never states the event as beating an
alternative**. Every allocation decision is relative to *something*; ours:

| Capital alternative | Benchmark our candidates must beat | Why this one |
|---|---|---|
| Long-only equity capital | **SPY buy-and-hold** (total return; we use price-only = conservative) | if a strategy can't beat just holding SPY on a risk-adjusted basis, holding SPY IS the strategy |
| Balanced capital | **60/40 SPY/AGG** (Calmar/Sharpe basis) | the realistic default for capital that can't take full equity vol |
| Ballast / MF sleeve | **AGG + cash (T-bill)**, plus SPY on a *drawdown-adjusted* basis | bonds' alternative is bonds; the sleeve's sellable claim is "near-SPY returns with ≥30% less drawdown" — never raw CAGR |
| Any class's "positive PnL" claim | **cash + that class's own beta** (e.g., crypto strategy vs holding BTC) | the TSMOM objection from PEER_WORK_REVIEW: 2.13 Sharpe < B&H ≈2.2 means the "edge" is just beta |

**Adopted gates (all candidates):** excess Sharpe ≥ 0.2–0.3 vs the stated benchmark over
≥24 months forward (SubQ's independent bar: ~30–36 months, low confidence), OR equal
return with ≥30% lower max drawdown, plus the absolute gates (PF/n/Wilson). Numbers
produced by our own backtest: rotation sleeve 8.2% vs SPY 12.8% full-cycle — it *loses*
on CAGR by design and earns its place on drawdown/stress (2022: −6.2% vs −19.5%),
which is exactly how a benchmark-relative claim must be framed.

## D. "Mutual funds would be winners given enough time" — the honest version

**Agreed, with the event stated precisely:** a low-cost, broad, diversified MF/ETF
allocation has a **~85–90%** (our estimate) / 55–70% (SubQ's skeptical estimate)
probability of positive net return over 10 years — because it is *paid to take risk*
(equity/bond premia), not paid for prediction. What is **NOT** agreed: that *the
prediction system* can add alpha on top — active selection after costs: P ≈ 10–25%
(SubQ: 0.03 for "reliably beats index after costs"). So: **the winners are the funds
themselves; our job is to not destroy their beta and to honestly test, once, whether
slow rotation adds anything.** Infrastructure-first (PIT universe, SubQ's top pick
conf 0.87), then one pre-registered relative-strength trial.

## E. What the analysis got right that we adopt verbatim
- Measurement-first ordering (it is our Phase 0/1).
- Beta-vs-alpha separation with a *parallel* deployment track (it is our Phase 2 slot 3).
- Risk overlay independent of signal quality (1–2% risk, ¼-Kelly cap, ATR stops,
  drawdown halts — our Phase 3; note: our own monthly DD-stop backtest **failed**,
  so overlays are applied as *risk budget + kill criteria*, not as a tested timing rule).
- "Kill or mutate paths that fail; FOREX on mutation protocol" (our forex.md).
