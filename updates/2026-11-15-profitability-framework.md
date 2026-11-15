# Profitability Framework — 2026-11-15

**Status:** proposed framework, not yet adopted
**Author:** Buffy (Codebuff)
**Evidence:** live payload `findtorontoevents.ca/audit/data/dashboard_data.json` @ `2026-11-14T22:34:02Z`
**Reproduce:** `python3 tools/asset_class_measurability.py --payload <payload.json>`

---

## 0. Corpus review — what you asked me to read, and what I found

Every file in your Windows list exists on `origin/main`. The 400+ paths collapse to 14 distinct
documents, duplicated across worktrees (`.inspect-wt`, `fta-audit-inspect`, `.claude/worktrees/agent-*`,
`tmp/ghcopilot-main-*`). No file is missing from the remote.

| Your path | On `origin/main` | Note |
|---|---|---|
| `updates/2026-05-13-money-maker-action-plan.md` | ✅ | quoted in full in your message |
| `updates/2026-05-11-money-maker-{master-plan,multi-agent-comparison}.html` | ✅ | 92KB + 23KB |
| `updates/2026-05-11-money-maker-{kimi,cursor,copilot,codex,claude-code}.html` | ✅ | 5 model-authored plans |
| `reports/peer_claude-phase10b-money-maker-*/{plan,result}_2026-05-31.md` | ✅ | 16 files, 8 classes |
| `.claude/skills/money-maker-ready/`, `...-readyv2/` | ✅ | v1 21KB, v2 43KB |
| `…money-maker-ready-june112026edition.skill` (Downloads) | ✅ | **and a July 2026 edition exists that you may not have** |

Two versions on the remote are **newer than what's in your Downloads folder**:
`.claude/skills/money-maker-ready-June112026edition/` and `...-July112026edition/`.

Also reviewed: `docs/ALL_STRATEGIES.md` (84KB, 700+ strategies), `docs/STRATEGY_FAILURE_ANALYSIS_FRAMEWORK.md`
(the 5-pillar diagnosis), `STRATEGY_GRAVEYARD.md` (27 killed, −$12,839), `reports/MONEY_MAKER_READY_JUNE_2026_EDITION.md`,
`reports/2026-05-26_money_maker_v2_unblock_plan.md`.

**The corpus already contains the answer to your question, and it says no.** The v2 skill's
2026-06-09 addendum states: *"As of 2026-06-09 the clean-cohort screen returns **0 confirmed
survivors** in any class."* It lists six mandatory integrity filters that must be applied before any
WR/PF is trusted. That policy exists. It is simply not enforced where the data is written.

---

## 1. Every asset class this repo attempts to predict

13 attempted classes. 9 appear in the live ledger. 4 are attempted in code but never reach a verdict.

| # | Class | Attempted in | In live ledger | Verdict surface |
|---|---|---|---|---|
| 1 | CRYPTO | 361 strategies, 14 families, 18 on-chain | ✅ 22,077 resolved | `/audit` |
| 2 | EQUITY | alpha_engine, copy_trader, regime_* | ✅ 474 | `/audit` + US Equity tab |
| 3 | ETF | etf_scanner, etf_all_strategies, leveraged_etf_decay | ✅ 19 | `/audit` |
| 4 | FOREX | ig_contrarian, myfxbook, cta_cross_asset | ✅ 432 | `/audit` |
| 5 | COMMODITY | COT family (multi_asset_cot) | ✅ 14 | `/audit` |
| 6 | FUTURES | futures_connors_rsi2, term_structure | ✅ 13 | `/audit` |
| 7 | BOND | BOND scanner (blocked on FRED) | ✅ 1 | `/audit` |
| 8 | MEMECOIN | 29 strategies, class-wide quarantine | ✅ 10 | `/audit` |
| 9 | PENNY_STOCK | penny_deep_oversold, skyrocket_detector | ✅ 4 | `/audit` |
| 10 | INDEX_STOCK | `edge_stability.py`, `portfolio_gates.py` | ❌ | none |
| 11 | SPORTS | `swarm_pick_schema.py`, `_sportsbet` DB | ❌ | none |
| 12 | PREDICTION MARKET | Polymarket, Kalshi, pm_consensus_overlay | ❌ | none (sources only) |
| 13 | MUTUAL_FUND | nothing but `recon_uncharted_tables.py` | ❌ | none |

**MUTUAL_FUND is not a pick class anywhere in the codebase.** Your instinct that funds matter is
right, but they cannot enter this pipeline at all — see §6.

Scale check: **361 registered strategies** in `alpha_engine/config.py::STRATEGY_FAMILIES` across
**14 families** (momentum 80, volatility 59, sentiment 55, trend 46, structure 34, volume 31,
mean_reversion 24, on_chain 18, community 4, carry 3, regime 3, macro 2, earnings 1,
commodity_seasonal 1). `ALL_STRATEGIES.md` claims 700+ including baby/incubator strategies.
27 are in the graveyard.

---

## 2. Measured reality: 48% of the ledger is unmarked

This is the finding the framework rests on, and it is new — nobody has published a per-class
contamination rate before.

| Class | Closed rows | Forged flat | Contam. | Verified marks | WR% | PF | Sharpe/trade | Measurability |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| CRYPTO | 5,135 | 3,021 | **59%** | 2,114 | 40 | 1.02 | 0.005 | PARTIAL |
| EQUITY | 835 | 97 | 12% | 738 | 47 | 1.15 | 0.054 | **MEASURABLE** |
| ETF | 575 | 9 | **2%** | 566 | 44 | 1.04 | 0.014 | **MEASURABLE** |
| FOREX | 355 | 197 | **56%** | 158 | 46 | 1.16 | 0.061 | PARTIAL |
| BOND | 35 | 0 | 0% | 35 | 37 | 0.59 | −0.248 | MEASURABLE (thin) |
| COMMODITY | 23 | 16 | 70% | 7 | 43 | 0.60 | −0.201 | THIN_N |
| FUTURES | 10 | 10 | **100%** | **0** | — | — | — | NO MARKS |
| **TOTAL** | **6,968** | **3,350** | **48.1%** | **3,618** | | | | **3 of 7 measurable** |

"Forged flat" = terminal row where `exit_price == entry_price` or `pnl_pct == 0.0`. These rows carry
no price information. A `TIME_EXIT` that returns the entry price is not a 0.0% trade, it is a row
that was never marked to market. There are 3,350 of them.

**Only 3 of 7 classes can currently be judged: EQUITY, ETF, BOND.** Two cannot be judged at all.

*(The `asset_class_health` block reports larger cohorts — CRYPTO 22,077, PF 0.258 — against the
5,135 closed rows I could parse. Those two numbers are not comparable, and the 4× PF disagreement on
the same class is itself a blocker: the dashboard's number is the one users see.)*

---

## 3. Why profitability was never actually tested

Five structural defects. Each one independently invalidates an edge claim; together they explain
why every prior audit found an "edge" and every subsequent one found it gone.

**D1 — The resolver forges flat closes.** 3,350 rows (48.1%). Confirmed against real closes:
V stamped 383.90 vs actual 425.76 (−9.83%), GOOGL 342.00 vs 295.77 (+15.63%), LLY 1,189.41 vs
1,443.50 (−17.60%). FUTURES is 100% forged; COMMODITY 70%.

**D2 — Wins are mislabeled as neither-win-nor-loss.** The 2026-05-31 peer audit found 147
`TP_HIT` rows for `ml_crypto_predictor` LONG alone, avg +7.17%, all invisible to any query
filtering `status IN ('WON','LOST')`. Same strategy reads 0% WR or ~51% WR depending on which
query you run. The display layer counts TP_HIT as a win; the verdict layer does not.

**D3 — The kill switch is cosmetic.** `BLOCKED_SOURCE_STRATEGY_PAIRS` is enforced in
`build_pf_registry.py` (display) but **not at the emitter**. Banned strategies still wrote 370
picks/week: `ml_crypto_predictor` LONG 206 in 7 days, `alpha_engine_fast` 163 — both banned months
earlier. The blocklist filters what you *see*, not what you *trade*.

**D4 — Concentration masquerades as edge.** One emitter (`kimi_riseoftheclaw`) is 1,687 picks =
48.2% of the ledger; HHI 0.385 (ceiling 0.30). `futures_connors_rsi2` is 87% of FUTURES; the
e-mini index basket is 91.8% of the class and all four legs are the same equity beta. These are
single bets reported as class performance.

**D5 — Kills are decided on samples too small to decide anything.** `stocks_rsi2_pullback` was
blocked at **n=10** (WR 30%, PF 0.032). At n=78 it reads WR 44.9%, PF 1.11 — the only EQUITY
strategy with both edge and depth. The kill was noise. Meanwhile 361 strategies are tested
simultaneously, so at α=0.05 roughly **18 will look significant by pure chance** — and nothing in
the pipeline deflates for that.

The pattern: **the system measures emission, not outcome.** Every number above is a measurement
artifact of the pipeline, not a property of the market.

---

## 4. The framework — five layers, each with a gate

The principle: **no capital decision may consume a number that failed the layer below it.** Most of
these gates already exist as code or policy somewhere in the repo; the change is *where they bind* —
at write time, not read time.

### L0 — Truth layer (blocks everything)

| Gate | Pass criterion |
|---|---|
| Terminal row has a real mark | `exit_price ≠ entry_price`, or an intrabar-verified same-bar fill |
| `closed_at` populated | non-null on every terminal row |
| No forged flats | 0 rows with `status='TIME_EXIT' AND pnl_pct=0` |
| TP_HIT promoted | `TP_HIT→WON`, `SL_HIT→LOST` at resolve time |
| Price sanity per class | `\|pnl\| ≤ 95 CRYPTO / 50 EQUITY / 20 FOREX / 30 COMMODITY / 25 BOND` |
| Unmarked budget | < 1% of closed rows per class |

**Owner:** `alpha_engine/outcome_resolver.py`. **Enforced:** write path. Gate tool already built:
`tools/pnl_zero_validator.py` (exits 1 on the live payload today — 37 fabricated flats).
Measurement tool: `tools/asset_class_measurability.py`.

### L1 — Measurement layer (makes an edge claim legal)

A WR/PF may be quoted only if: verified marks only · intrabar-replayed (`tools/reresolve_intrabar.py`) ·
per-class sane-pnl guard · **≥3 distinct months at n≥30/month** · pre-registered hypothesis before
the backtest (rule M-107, `reports/hypothesis_registry.json`) · Deflated Sharpe reported alongside raw.

Why ≥3 months: the same data yields a 4–6× PF spread by resolver version (CRYPTO June PF 0.51 vs
2.15). A single strong month is selection bias.

### L2 — Ranking layer (risk-adjusted, not win-rate)

Rank by, in order: **Sharpe per trade → PF → CVaR95 → max drawdown (compounded) → Kelly**.
Any class or strategy with **Kelly ≤ 0 is sized at zero**, regardless of PF. Costs are subtracted
per class before ranking (bps round-trip: ETF 2–5, EQUITY 5–10, FOREX 10–20, CRYPTO 15–30).
A strategy whose edge is smaller than its class cost is not a strategy.

Current state: CRYPTO Sharpe/trade 0.005, ETF 0.014 — both below their own cost floor. EQUITY 0.054,
FOREX 0.061 — above it, but not by enough to survive a bad month.

### L3 — Allocation layer (where money actually goes)

Only classes passing L0–L2 receive capital, and they receive it as either **beta** (buy-and-hold,
monthly clock) or **alpha** (systematic picks, daily clock). These are different products and must
never share a performance number. Fund/ETF allocation runs on a monthly clock; picks run daily.
Beta positions carry no edge claim and are reported as market exposure.

### L4 — Kill/mutate discipline

Adopt the repo's own 5-pillar diagnosis (statistical / structural / execution / data / risk) with two
additions:
- **n ≥ 120 verified closures before any kill** (fixes D5; `stocks_rsi2_pullback` dies at n=10 under the current rule).
- **A `PROBATION_WATCHLIST`** for candidates between n=30 and n=120, protected from dedupe/suppression.

---

## 5. Where profitability plausibly exists — ranked

Your hypothesis was mutual funds and ETFs. Half right: **right for the product, wrong for the
edge.** Here is the ranking, separating measured fact from judgement.

| Rank | Vehicle | P(positive, 10y) | Risk | Horizon | Basis |
|---|---|---|---|---|---|
| 1 | **Index ETF, buy & hold** (SPY/VOO core) | **~90%** | maxDD −52%, vol 14.7% | 10y+ | Measured: 90.2% of SPY's 10y windows positive over 407 months; CAGR 8.71%, Sharpe 0.64 |
| 2 | **Global/sector ETF, rules-based rotation** (Faber 200dma) | 65–75% (judgement) | maxDD est. −25 to −35% | 1–3y | Documented OOS in literature; **not yet measured here** — in-repo ETF ledger is PF 1.04 |
| 3 | **Concentrated mega-cap basket** (NVDA-type) | 60–70% (judgement) | maxDD −60 to −80% single-name | 5y+ | This is beta + concentration, not alpha. Highest expected return, worst tail |
| 4 | **ETF/equity mean-reversion picks** (`stocks_rsi2_pullback`) | 50–55% | PF 1.15, thin edge | weeks | Best *measurable in-repo* signal: 738 verified EQUITY marks, WR 47% |
| 5 | **Crypto tactical** | ~45% | vol 60–80%, maxDD > −80% | days–weeks | PF 1.02 on 2,114 verified marks = break-even before costs, and 59% of the class is unmarked |
| 6 | **Forex systematic** | ~45% | low MDD, high churn | hours–days | PF 1.16 on only 158 verified; spread eats most of it |
| 7 | **Bond tactical** | ~30% | PF 0.59 | — | Measured negative. No |
| — | **Commodity / Futures** | **cannot be ranked** | — | — | 7 and 0 verified marks respectively |
| — | **Memecoin / Penny / Sports / Prediction** | ~0 | — | — | Dead, dormant, or never verdicted |

**The sharpest finding for your ETF thesis:** ETF has the *best data quality in the entire system* —
2% contamination, the only class where the ledger is nearly clean — and it shows **PF 1.04, WR 44%**.
That is a coin flip. Because the data is trustworthy there, this is the one class where the negative
answer is real. Which means the "edges" reported in less-clean classes deserve proportionally less
credibility, not more.

---

## 6. Straight answers to the four options you raised

**Mutual funds — cannot be a pick class (structural, not fixable).** NAV is struck once daily after
the close; orders fill at the *next* unknown NAV; TP/SL can only execute there; 30-day
frequent-trading limits prohibit the turnover these strategies need. The resolver's intrabar model is
meaningless for them. **What funds can be:** the allocation wrapper. A monthly clock, low-cost index
funds, rebalanced — with measured base rates (90.2% of 10y windows positive) and fees treated as the
first-order cost: 0.60% vs 0.03% expense ratio costs **~10% of terminal value over 20 years**.

**ETFs — best vehicle, no edge found.** Cleanest ledger (2% contamination) and the class a
quant would trust most, and it says PF 1.04. The 200-day-MA trend/rotation family is the one
research-backed candidate worth pre-registering and measuring properly; the current
`etf_rsi2_pullback` cohort closed 33 picks at exactly 0.0% — i.e. never marked — so it has never
been tested.

**NVDA-style concentrated basket — legitimate, but stop calling it a prediction.** It is a
levered bet on mega-cap earnings continuation. It needs no strategy, no resolver, and no backtest;
it needs position sizing and an exit rule. Expected return is highest of anything on this list;
so is single-name drawdown. Label it beta and size it as such — do not let it inherit credibility
from a dashboard of "picks".

**Daytrading / scalping — the data says no, and the cost model says no twice.** At PF 1.02–1.16
with WR 40–47%, edge per trade is a few bps. Sharpe/trade is 0.005 (CRYPTO) to 0.061 (FOREX).
Retail round-trip cost on liquid instruments is 5–20 bps. **Break-even slippage is under 5 bps for
most of these strategies**, and the repo's own Pillar-3 rule says <5 bps = FAIL. More simulations
will not fix a cost structure.

---

## 7. Sequencing — 30 / 60 / 90 days

**Days 1–30 — make the ledger true.** This is the only thing that unblocks everything else.
1. Fix the resolver `TIME_EXIT` path: mark to market at `t_exit`; never write `pnl=0`; set `closed_at`.
2. Backfill the 3,350 forged rows (intrabar replay where OHLCV exists; else `EXPIRED`, not 0).
3. Promote `TP_HIT→WON`, `SL_HIT→LOST` at resolve time; backfill history.
4. Move `BLOCKED_SOURCE_STRATEGY_PAIRS` enforcement into the **emitter**, not the display.
5. Wire `tools/pnl_zero_validator.py` into CI as a blocking gate (it already exits 1).

*Exit criterion: <1% unmarked rows in every class; 7/7 classes measurable.*

**Days 31–60 — measure honestly.** Re-run per-class stats on verified marks; preregister the 3
candidates worth testing (`stocks_rsi2_pullback` at n≥120, ETF 200dma trend, one crypto funding-rate
mean-reversion); compute Deflated Sharpe against 361 trials; publish a per-class verdict page where
"insufficient data" is a valid, visible outcome.

**Days 61–90 — allocate by evidence.** Split the book explicitly: beta sleeve (index ETF, monthly
clock) and alpha sleeve (only classes that cleared L2). Paper-pilot the alpha sleeve ≥4 weeks
forward before capital. Any class still unmeasurable at day 90 gets a **DORMANT** label on the
dashboard rather than a silent zero.

---

## 8. Kill criteria — what would change this framework's conclusions

Falsifiable triggers, so this document can be wrong in a useful way:

- **A class clears the money-ready bar** (n≥100 verified, ≥3 months, PF>1.5, WR>52%, intrabar-validated, costs subtracted) → promote it and re-rank.
- **ETF PF holds >1.3 at n≥150 verified** → the trend/rotation thesis survives; fund it.
- **`stocks_rsi2_pullback` holds PF>1.3 at n≥120** → EQUITY becomes the first alpha class.
- **Post-cleanup CRYPTO PF stays >1.2 at n≥1,000 verified** → the 59% contamination was hiding a real edge; say so plainly.
- **A strategy's edge is smaller than its class round-trip cost** → kill it, irrespective of WR.

---

## 9. What this document does not claim

- It does not claim any class is profitable. Nothing in this repo currently is, at a money-ready bar.
- It does not claim the 3,618 verified marks are clean — they are *marked*, not intrabar-validated.
  Intrabar replay (`tools/reresolve_intrabar.py`) historically reclassifies ~26% of TP_HIT to SL_HIT.
- The probability estimates in §5 for ranks 2 and 3 are **judgement anchored to measured base rates**,
  not measurements. Ranks 1 and 5–7 are measured.
- The per-class PF here and the dashboard's `asset_class_health` PF disagree by up to 4× on different
  cohorts. Neither is authoritative until L0 passes.
- No real-money deployment is recommended by this framework. The gating dependency remains the
  ledger, not the strategy catalogue.

---

*Companion artefacts: `tools/asset_class_measurability.py`, `reports/asset_class_measurability.json`,
`tools/pnl_zero_validator.py`, `audit_dashboard/risk_management.html`.*
