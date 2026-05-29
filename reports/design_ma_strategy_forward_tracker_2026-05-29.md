# Design + Test Plan — MA Strategy Forward-Tracker v2

**Author:** claude-opus-4-7-desktop · **Date:** 2026-05-29 · **Status:** DRAFT (pre-peer-review)
**Goal alignment:** Goal #1 (phenomenal performance across asset classes) — adds a transparent, *forward-tested* trend-following baseline the audit page can hold every other engine against.

---

## 1. Problem / Motivation

`tools/ma_strategy_backtest.py` (shipped 2026-05-29, commit `69400fbde`) produces a **one-shot, in-sample** backtest of 8 MA variants over 6y daily bars and writes `audit_dashboard/data/ma_strategy_leaderboard.json`, surfaced on `/audit/ai_leaderboard.html`.

Three honesty gaps make it unfit to "size up" or to compare against the live tournament:

1. **In-sample only.** All 6y used for both rule-tuning and scoring → PF 3.16 (EMA200) is optimistic; no out-of-sample (OOS) split. This is exactly the kind of unsourced/over-optimistic number CLAUDE.md warns against.
2. **No risk overlay.** The user's spec was *"risk 1–2% per trade, MA = trailing exit, no TP."* The v1 backtest is fully-invested long/flat — it does not model per-trade position sizing or a hard floor stop, so the equity curve, MaxDD and Sharpe don't reflect the intended risk policy.
3. **Not forward-tracked.** It's a snapshot. There's no record of *what signal each strategy×symbol is flashing today* (LONG/FLAT, days held, distance-to-MA) and no append-only forward log to accumulate a genuine out-of-sample track record over time.

## 2. Goals / Non-Goals

**Goals**
- G1. Add a **walk-forward / OOS split** so reported stats separate in-sample (IS) tuning from OOS performance. Headline numbers on the page become the **OOS** numbers.
- G2. Add the **risk overlay**: per-trade risk budget (default 1%, configurable 1–2%), entry next-open after close>MA, **hard floor stop** at `entry − k·ATR` (or a % floor) in addition to the MA trailing exit, no take-profit. Position size = `risk_budget · equity / stop_distance`.
- G3. Add a **forward signal-state block** per strategy×symbol: current LONG/FLAT, entry date, days held, % above/below MA, current stop level — so the page shows "what would I do tomorrow."
- G4. Append-only **forward log** (`ma_strategy_forward_log.jsonl`) so each refresh records the dated signal set; over weeks this becomes a real forward track record (no look-ahead).
- G5. Surface OOS vs IS clearly on `ai_leaderboard.html` and keep the golden-finder honest (golden requires OOS PF≥2 & OOS Sharpe≥0.5 & n_oos≥20).

**Non-Goals**
- No live order execution / broker integration. Paper/analytical only.
- No new GitHub Actions workflow (repo already has 356 — sprawl finding). Refresh is manual or folded into an existing scheduled job; decided in §6.
- No DB writes. yfinance read-only price data → JSON artifacts only.
- Not changing the v1 variant set unless peer review flags a variant as degenerate.

## 3. Design

### 3.1 Data
- Source: `yfinance` daily OHLCV, 6y, same UNIVERSE/asset-class map as v1. Add **ATR(14)** for stop sizing. Failover note: yfinance is the only price source here; on fetch failure a symbol is skipped and logged (no fabricated bars).

### 3.2 Walk-forward split
- Default: **IS = oldest 60%**, **OOS = most-recent 40%**, single split (simple, legible). Optional `--walk-forward N` for N rolling anchored windows (re-fit nothing — MA rules are non-parametric, so "fit" here only means *which window we report*; document that MA length is a fixed hyperparameter, not optimized per window, so IS/OOS mainly guards against cherry-picking the report window + regime luck).
- Headline JSON fields become `wr_oos / pf_oos / cagr_oos / maxdd_oos / sharpe_oos / n_trades_oos`, with IS kept alongside for comparison and an `is_oos_decay` ratio (pf_oos/pf_is) to flag overfit variants.

### 3.3 Risk overlay (per trade)
```
entry      = next session open after close > MA
stop0      = max(entry - k*ATR14, entry*(1 - max_floor_pct))   # k default 2.5, max_floor 12%
trail_exit = first close < MA  -> exit next open
hard_stop  = intraday low <= current_stop -> exit at stop (gap-through: exit at open if open<stop)
size       = (risk_budget_pct * equity) / (entry - stop0)      # risk_budget_pct default 1%
```
- Trailing: stop ratchets up with MA (stop = max(stop0, recent MA-based floor)); never loosens. No take-profit (per spec).
- Compounding equity curve seeded at 100_000; one position per symbol; portfolio = equal-risk across symbols within a class.

### 3.4 Outputs
- `audit_dashboard/data/ma_strategy_leaderboard.json` — extended schema: per variant×class → {IS block, OOS block, decay, current_signal_summary}.
- `audit_dashboard/data/ma_strategy_signals.json` — per strategy×symbol current state (LONG/FLAT, entry_date, days_held, pct_vs_ma, stop_level).
- `audit_dashboard/data/ma_strategy_forward_log.jsonl` — append one dated record per refresh (UTC date passed in via `--asof`, never `Date.now()` inside logic).

### 3.5 Frontend (`ai_leaderboard.html`)
- MA table shows **OOS** headline columns; IS shown in a muted secondary row / tooltip; add `decay` column with amber when pf_oos/pf_is < 0.6.
- New "Today's MA signals" mini-panel reading `ma_strategy_signals.json` (LONG/FLAT chips).
- Golden-finder threshold tightened to OOS-based (PF_oos≥2 & Sharpe_oos≥0.5 & n_oos≥20).

## 4. Risks & Mitigations
| Risk | Mitigation |
|---|---|
| yfinance gaps/splits distort bars | use auto-adjusted close; skip+log symbols with <2y data; never fabricate |
| Survivorship bias in UNIVERSE | document it on the page; UNIVERSE is current-listed tickers only — flag as a known caveat |
| OOS still optimistic (single split lucky window) | report `decay` + offer `--walk-forward`; label headline "single 60/40 split" |
| Look-ahead in signal state | entry strictly next-open; stop checks use only same/prior-day data; `--asof` controls "today" |
| Over-trading tiny accounts | min position guard; log skipped trades where stop_distance ~0 |
| Adding CI sprawl | NO new workflow; manual/folded refresh (§6) |

## 5. Test Plan
**Unit (`tests/test_ma_forward_tracker.py`, pytest):**
- T1 HMA formula: `WMA(2·WMA(n/2) − WMA(n), √n)` matches a hand-computed 4-point fixture.
- T2 Entry timing: synthetic series crossing MA on day D → entry fills at open[D+1], never close[D] (no look-ahead).
- T3 Stop math: `size = risk%·equity/stop_dist`; loss on stop-out ≈ risk_budget% of equity (±1 tick).
- T4 Trailing exit: close<MA → exit next open; stop never loosens across bars.
- T5 OOS split: with fixed seed/series, IS and OOS trade-sets are disjoint and cover the right date ranges.
- T6 No-TP invariant: no exit is ever labeled take-profit.
- T7 Gap-through: open below stop → exit at open, not stop (no fantasy fills).
- T8 Empty/short symbol: <2y data → skipped, recorded in `skipped[]`, no crash.

**Integration / smoke:**
- I1 `python tools/ma_strategy_backtest.py --asof 2026-05-29 --self-test` runs end-to-end on 3 symbols, emits all 3 JSONs, exits 0.
- I2 Schema check: leaderboard JSON has OOS fields for every variant×class; signals JSON parses; forward_log gets exactly one new line per `--asof`.
- I3 `py_compile` clean; JSON validates (`python -m json.tool`).

**Frontend manual:**
- F1 ai_leaderboard.html renders OOS columns + signals panel without console errors (open file, not via dashboard_generator).
- F2 Golden highlight only fires on OOS thresholds; decay amber fires when pf_oos/pf_is<0.6.

**Honesty gates (must pass before "proven"):**
- H1 Headline = OOS, never IS. H2 n_oos≥20 before any variant is called golden. H3 page states "single 60/40 split, survivorship-biased universe, paper, no slippage model beyond next-open fill."

## 6. Refresh / Ops (no new CI workflow)
- Primary: manual `python tools/ma_strategy_backtest.py --asof <UTC>` then FTP-deploy the 3 JSONs via `tools/deploy_audit_files.py`.
- Optional fold-in: piggyback on an existing daily audit job if one already deploys `audit_dashboard/data/*` (TBD in review — do NOT add a 357th workflow).

## 7. Rollout
1. Land tool + tests (this branch). 2. Generate JSONs locally (read-only, safe — not a dashboard generator). 3. Wire frontend. 4. FTP-deploy data + html. 5. Add an `updates/` card (above the auto-incidents marker) citing this design doc + reproducer command.

## 8. Open questions for peer review
- Q1 Is single 60/40 OOS enough, or require anchored walk-forward as the default headline?
- Q2 ATR-stop (k=2.5) vs fixed-% floor (12%) as default — which is more honest for a *trend* system that's supposed to ride winners?
- Q3 Should portfolio be equal-risk per symbol or equal-weight? (affects class-level PF/Sharpe)
- Q4 Keep all 8 v1 variants, or drop the ones that only win in-sample?
- Q5 Refresh cadence + where to fold it without adding CI sprawl.

---

## 9. Peer review incorporated — deepseek (verdict: approve-with-changes) + cerebras/ofox cross-review (2026-05-29)
Swarm run: `swarm_runs/ma-design-review-20260529T051822Z/` + `swarm_runs/ma-design-xreview-20260529T051953Z/`. Consensus: solid foundation, but three honesty gaps could still produce a misleadingly-good number. Decisions adopted into the build:

**Open questions — resolved:**
- **Q1 → anchored walk-forward is the DEFAULT headline.** 5 expanding-window folds, fixed MA params (no per-window re-fit). Report **median OOS + worst-fold OOS**, not a point estimate. Single 60/40 kept only as a labeled secondary reference. (deepseek P0; cerebras partial-agree — folds may be too few for sparse classes, so fall back to 60/40 + a `low_fold_n` flag when a class has <50 OOS trades.)
- **Q2 → ATR(2.5×) default, capped at 2× the 12% fixed floor**; vol-regime guard: if ATR14 > 2× its 50d avg, halve size. (both agree)
- **Q3 → equal-risk** per symbol (equal-weight hides volatility concentration). Emit per-symbol risk-contribution in the JSON. (both agree)
- **Q4 → keep all 8 variants BUT** add a multiple-comparisons guard: a `fdr_note` + an **expected-false-positives** count (≈ n_variants×n_classes × P(PF≥thresh | no edge)), and a **never-touched holdout = most-recent 10%** used only to validate the single best variant. (both agree)
- **Q5 → weekly (Monday UTC) refresh, folded into an existing daily job via a day-of-week conditional, NO new workflow.** (deepseek; cerebras disagreed preferring event-driven — deferred: weekly is the honest cadence for a daily-bar trend system, revisit if signals lag.)

**New requirements added to §3/§5 before "proven":**
1. **Slippage/cost model (P1).** Per-trade cost = 5bps liquid (EQUITY/ETF/major FX/large-cap CRYPTO) / 15bps illiquid (everything else), applied on entry+exit. Headline = **net-of-slippage**; raw shown muted. No more bare "next-open fill."
2. **Survivorship penalty (P0).** UNIVERSE is current-listed only. Add a quantified `survivorship_penalty_pct` (assume 5% of long trades would have been ~total losses for trend systems) → emit a `pf_oos_survivorship_adj` and a prominent page banner: "Survivorship-biased universe — live results lower."
3. **Tighter golden gate (P1).** golden = `pf_oos≥2.5 AND sharpe_oos≥0.8 AND n_oos≥50 AND beats buy-and-hold(OOS) AND passes holdout`. (was PF≥2/Sharpe≥0.5/n≥20 — too loose under multiple comparisons.)
4. **Benchmark column (P1).** Per variant×class, OOS PF/CAGR **vs buy-and-hold** of the same universe. A trend system that can't beat B&H net is not edge.
5. **Bootstrap 95% CI** on OOS PF + WR (no point estimates without n + CI).
6. **ATR look-ahead fix (P1) + test T9.** ATR(14) at entry uses bars strictly up to and including the *signal* close (day D), entry fills open[D+1]; never the entry bar's own high/low.
7. **Added tests:** T9 ATR no-look-ahead, T10 beats-B&H-in-OOS, T11 Monte-Carlo null (shuffle returns → null PF distribution), T13 20%-gap-down loss ≤ risk budget, T16 split/dividend adjustment integrity.

**Scope discipline:** market-impact / order-type / latency modeling (cerebras "missed" list) is explicitly **out of scope** for a daily-bar paper tracker — noted as a known limitation on the page, not modeled.
