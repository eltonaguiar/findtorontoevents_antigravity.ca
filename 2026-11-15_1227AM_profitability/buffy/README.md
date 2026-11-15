# 2026-11-15 · 12:27 AM · Profitability Package

**Worktree:** `buffy` · **Branch:** `main` · **Author:** Buffy (Codebuff)
**Question:** can this system find a profitable strategy, and if not, what is the shortest honest path?

---

## Bottom line

**Not today — and the reason is not the strategies.** The system has 361 registered strategies across 14
families, 9 asset classes, 3 dashboards and 9 databases. It also has **3,350 of 6,968 closed rows
(48.1%) with no price information**: `exit_price == entry_price`, stamped `TIME_EXIT`. Only **3 of 7
classes are measurable** at all.

So "we can't find profitability" is the wrong diagnosis. **Profitability has never been measured.** What
was measured is emission — and emission is abundant.

The second finding is more useful than the first: **ETF has the cleanest data in the entire system (2%
contamination) and it reads PF 1.04, WR 44%.** That is a coin flip on the one class whose numbers can be
trusted. Your instinct that ETFs are the right vehicle is correct; the hoped-for edge inside them is not
there yet, and because the data is clean, that negative answer is real.

---

## The package

| Folder | Document | What it answers |
|---|---|---|
| `01_plan/` | **PER_ASSET_CLASS_PLAN.md** | For all 13 classes: mechanism, measured state, smallest honest test, kill criterion |
| `02_style_matrix/` | **STYLE_MATRIX.md** | Class × holding period × style; contest-audited winners; which styles can pay their costs |
| `03_nov14_answers/` | **ANSWERS.md** | Confirms, corrects and extends the 2026-11-14 plan (§2 fixes four of its numbers) |
| `04_questions/` | **ESSENTIAL_QUESTIONS.md** | 15 gates before anything may be called profitable — repo answers 4 |
| `05_industry/` | **INDUSTRY_TURNAROUNDS.md** | How AQR, Man AHL, Renaissance and risk vendors earned real-money trust |
| `06_metrics/` | **METRICS_BY_PERSPECTIVE.md** | Sharpe/PF/DSR/Calmar bars by audience: bank desk, fund manager, allocator, CRO, prop challenge |
| `07_subq/` | **FACTCHECK.md** + raw runs | First real SubQ invocation in the repo; 3 arms × 8 questions; sycophancy tested |
| `08_evidence/` | **EVIDENCE_INDEX.md** | Every number, its file, its reproduction command, and what is *not* measured |

---

## What is genuinely new versus the inherited plans

1. **A per-class contamination measurement.** 48.1% overall; FUTURES 100%, COMMODITY 70%, CRYPTO 59%.
   No prior document in this repo has published this.
2. **The ETF inversion.** The cleanest class in the system is also a coin flip — which makes it the most
   trustworthy negative in the audit, not the least.
3. **SubQ actually run.** Prior plans say `NOT_RUN` because earlier agents read "SubQ" as "subagent
   query". A real key exists; 24 decisions were made with hashes and token counts stored.
4. **A behavioural fact-check** of that model: robust on capital deployment, **2.5× pressure-sensitive**
   on `equity_reliably_profitable` when the operator asserts success.
5. **Four corrections to the Nov-14 plan** — ETF is not "zero live picks" (566 verified marks),
   COMMODITY/FUTURES are not "PF 1.78" (7 and 0 verified marks), CRYPTO has three conflicting PFs, and
   DSR at N=38 understates the trial count of 361 by ~10×.

---

## The one thing to do next

**Make the ledger true.** Not more strategies, not more classes.

1. Resolver writes mark-to-market on `TIME_EXIT`; never `pnl = 0`; set `closed_at`.
2. Backfill the 3,350 forged rows (intrabar replay where OHLCV exists, else `EXPIRED`).
3. Promote `TP_HIT → WON`, `SL_HIT → LOST` at resolve time.
4. Move the blocklist from `build_pf_registry.py` (**display**) to the emitters — banned sources still
   wrote 370 picks/week.
5. Block CI on `tools/pnl_zero_validator.py` (it already exits 1).

Exit criterion: **<1% unmarked rows per class, 7/7 classes measurable.** Nothing else is worth doing
before that, because every other number is computed on it.

---

## Where the probability actually is

| Rank | Vehicle | P(positive, long horizon) | Risk | Nature |
|---|---|---|---|---|
| 1 | Low-cost index ETF / passive fund, buy & hold | **~90% at 10y** (measured: 90.2% of SPY's 10y windows) | maxDD −52% | beta |
| 2 | Rules-based ETF trend (200-DMA / Faber) | 65–75% *(judgement)* | maxDD est. −25 to −35% | beta+timing |
| 3 | Concentrated mega-cap basket (NVDA-type) | 60–70% *(judgement)* | −60 to −80% | beta + concentration |
| 4 | EQUITY swing reversion | 50–55% | PF 1.15, thin | **alpha, unproven** |
| 5 | CRYPTO tactical | ~45% | vol 60–80% | alpha, break-even pre-cost |
| 6 | FOREX systematic | ~45% | best Sharpe/trade, worst cost ratio | alpha, unlikely |
| 7 | BOND tactical | ~30% | PF 0.59 | no |
| — | COMMODITY / FUTURES | **cannot be ranked** | 7 and 0 verified marks | unmeasurable |
| — | MEME / PENNY / SPORTS | ~0 | dead or dormant | retire |

**Mutual funds cannot be a pick class** — once-daily NAV, next-NAV fills, no intrabar stops, 30-day
trading limits. They are the **allocation wrapper**, and fee drag is first-order: 0.60% vs 0.03% ER
costs ~10% of terminal value over 20 years.

**Day trading / scalping:** measured per-trade Sharpe is 0.005–0.061 against retail round-trip costs of
5–20 bps. The break-even slippage gate (<5 bps = FAIL) disqualifies the style before any simulation runs.

---

## Alignment with the 2026-11-14 plan

**Agreed:** no class is proven, 0/23 hypotheses, `sizing_allowed: false` everywhere, do not deploy.

**Corrected:** its ETF, COMMODITY/FUTURES and CRYPTO figures (§2 of `03_nov14_answers/`), and its
proposal to build mutual-fund pick infrastructure — that spend should not happen, because the class
cannot be executed as picks.

**Added:** the write-layer enforcement gap, the 15-question gate, and the industry benchmark that a
top-tier CTA (Man AHL) runs at Sharpe **0.24**.

---

## Reproduction

```bash
python3 tools/asset_class_measurability.py --payload <live dashboard_data.json> \
        --out reports/asset_class_measurability.json
python3 tools/pnl_zero_validator.py --payload <live dashboard_data.json>
python3 tools/subq_consult.py --questions 2026-11-15_1227AM_profitability/buffy/07_subq/subq_questions.json \
        --out 2026-11-15_1227AM_profitability/buffy/07_subq
```

**Status: NO-GO for real capital.** No sizing recommended in this package, in any class.
