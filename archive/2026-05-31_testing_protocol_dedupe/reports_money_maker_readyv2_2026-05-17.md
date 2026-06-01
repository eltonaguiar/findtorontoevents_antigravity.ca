# /money-maker-readyv2 — Statistical Edge Audit 2026-05-17

> ## ⚠️ CORRECTION (post-concentration check) — supersedes the verdict below
>
> The original headline claimed two Tier-1 edges. **Both fail the
> concentration gate; neither is money-ready.** Isolated-verdict follow-up:
>
> - **`cot_positioning`** — DSR 1.0000, SPA-pass, PF 4.64 — *but* **85.1% of
>   its 134 picks are CT=F (cotton)**. CT=F carries the COT-row-duplication
>   artifact that got `cftc_cot_commercial_signal` retired (Phase 2-D,
>   2026-05-16). **Excluding CT=F: n=20, WR 30%, PF 0.51 — a loser.** The
>   entire `cot_positioning` "edge" *is* the CT=F artifact. NOT money-ready.
> - **`cta_cross_asset_tsmom` SHORT** — **93.2% USDJPY=X** (109/117). A
>   single-pair USDJPY-short bet, not a FOREX class edge. Fails concentration
>   <30% massively. Excluding USDJPY: n=8.
>
> **Real verdict: no money-ready edge exists.** Both candidates are
> single-symbol concentration that DSR and SPA *passed* — because DSR/SPA test
> only the return series, not symbol concentration nor whether the underlying
> data is corrupted. **Empirical proof the concentration gate must run as a
> hard, early filter** — SPA/DSR-passing is necessary, nowhere near sufficient.
> It also confirms the `cftc_cot_commercial_signal` retirement was correct, and
> that `cot_positioning` should be reviewed for the same CT=F-duplication kill.
>
> Lesson (repeat of `multi_ai_convergence_trap` + the cotton stale-data trap):
> gaudy PF + SPA-pass + DSR-pass on a strategy that is 85% one corrupted symbol
> is not an edge. Concentration-check before calling any edge real.
>
> ---
>
Data: `dashboard_data.json` (gen 2026-05-17T21:41Z, age 0.5h — fresh) +
`closed_picks.json` (8,421 resolved) via `tools/asset_class_edge_report.py`.
Companion to the auto-generated `reports/weekly_filter_2026-05-17.md`.

## Verdict

**No asset class is class-aggregate money-ready.** Verdict-grade
`asset_class_health` PFs: COMMODITY 1.17 · CRYPTO 1.28 · FOREX 0.33 ·
EQUITY 0.72 · FUTURES 0.96 · BOND/PENNY n≤1. None clears PF≥1.5.

But class aggregates **bury two Tier-1-grade per-strategy edges.** The
money-ready path is *strategy isolation*, not class-wide sizing.

## The two real edges

### COMMODITY — `cot_positioning`  ·  WR 78.2% / PF 4.64 / n=133
Best edge in the entire book. COT commercial-positioning signal. LIVE, not
blocked. Class COMMODITY PF (1.17) is dragged down by everything *around* it
— `cot_positioning` alone is Renaissance-tier.
- ¼-Kelly ≈ 15% → cap at charter max **10%/pick**.
- Caveat: not present in the current OPEN-pick set — confirm the emitter still
  runs (`project_strategy_state_2026_05_03.md` flagged "top-winners-stopped-
  emitting").

### FOREX — `cta_cross_asset_tsmom` **SHORT**  ·  WR 65.8% / PF 2.89 / n=117
Direction-split (verified vs `closed_picks.json`):
- SHORT: n=117, WR 65.8%, PF 2.89 — **edge** (quality_gates autopsy: USDJPY
  SHORT n=109 WR 71% PF 3.61 = T1).
- LONG: n=60, WR 41.7%, PF 1.07 — already BLOCKED `("FOREX","cta_cross_asset_tsmom","LONG")`, correct.
Class FOREX aggregates to PF 0.33; this one direction-strategy pair is T1.
- ¼-Kelly ≈ 11% → cap **10%/pick**. Filter: `FOREX + cta_cross_asset_tsmom + SHORT`.

### CRYPTO — watch only
`macd_crossover` PF 4.09 / WR 68.8% / **n=16** — credible shape, sample too thin
to size. The headline `ml_enhanced_*_ensemble_stack` "edges" (PF 60.5 n=31,
PF 999 n=9) are **overfit-suspect** — single-symbol micro-samples. Do not size.
Grow `macd_crossover` to n≥50, re-test.

## Bug found + fixed this run — PR #1183

`tools/edge_filter_engine_v3.py` (auto-generates the weekly real-money filter)
had **zero blocklist awareness**. The 2026-05-17 auto-filter recommended
**`cftc_cot_commercial_signal`** (51.6% of COMMODITY picks + a live OPEN pick)
— a strategy **retired 2026-05-02** per `strategy_blocklist.py::_RETIRED_STRATEGIES`.
Fix: filter all pick lists through `is_blocked_pick()` before any metric. The
genuine `cot_positioning` edge is unaffected (not blocked).

## `cftc_cot_commercial_signal` mis-ban question — resolved

`asset_class_edge_report.py` flags `cftc_cot_commercial_signal` (WR 74.8% /
PF 4.52 / n=131) as a possible mis-ban. **It is not** — the strategy's gaudy
record is a COT-row-duplication artifact on CT=F/CL=F (per the 2026-05-16
COMMODITY Phase 2-D re-audit). The 2026-05-02 retirement stands. Use
`cot_positioning` (clean) as the COMMODITY edge, not the retired duplicate.

## Success criteria — 3 / 7 met

| # | Criterion | Status |
|---|-----------|--------|
| 1 | EQUITY filter ≥5 picks WR≥55% | ❌ n=31/44, PF 0.72 — no edge |
| 2 | CRYPTO sub-class WR≥50% PF≥1.5 n≥100 | ❌ overfit-suspect or n=16 |
| 3 | COMMODITY top strategy PF≥1.5 | ✅ `cot_positioning` PF 4.64 |
| 4 | ETF n≥150 PF≥1.3 | ❌ ETF absent from `asset_class_health` |
| 5 | FOREX directional filter WR≥50% | ✅ `cta_cross_asset_tsmom` SHORT |
| 6 | BOND top strategy n≥20 | ❌ n=1 |
| 7 | Kelly sizing computed | ✅ above |

The 4 unmet fail on **data reality** (thin samples / no edge), not analysis.

## Next actions (ranked)

1. **Confirm `cot_positioning` emitter is live** — if stopped, the #1 edge is
   stranded in history.
2. **Run `money_ready_verdict.py` on COMMODITY-`cot_positioning` and
   FOREX-`cta_cross_asset_tsmom`-SHORT in isolation** — DSR/PBO/SPA. If they
   clear, they are the first real-money sizing candidates.
3. Merge PR #1183 so the auto weekly-filter stops recommending retired strategies.
4. Grow CRYPTO `macd_crossover` to n≥50, re-test.
5. EQUITY/FUTURES/BOND — accrue closed picks; no edge to size today.

---

## .MD review (past 2 weeks) — cross-validation

Reviewed recent `reports/` — two directly corroborate / sharpen the above:

### `whites_reality_check_2026-05-17.md` — SPA test (today)

24 strategies, 500-bootstrap White's Reality Check + Hansen SPA. Family-wide
edge SURVIVES; 9/24 pass SPA (p≤0.05). Key rows:

- **`cot_positioning` n=134, MeanRet 3.28% — PASSES SPA.** Strongest possible
  corroboration: the COMMODITY edge is statistically real, not data-mined. This
  promotes `cot_positioning` from "candidate" to **SPA-validated** — the single
  best money-ready prospect in the system.
- `stocks_rsi2_pullback` FAILS SPA (p=0.376) — EQUITY no-edge confirmed.
- **All FOREX strategies in the run FAIL SPA** (`forex_carry_momentum` -0.41%,
  `forex_rsi2_mean_reversion` -0.35%, `fx_smart_carry_trade_momentum` -0.09%).
  Note: `cta_cross_asset_tsmom` was **NOT in the 24-strategy SPA run** — the
  FOREX-SHORT edge above is unproven against SPA. **Must be SPA-tested in
  isolation before any sizing** (reinforces next-action #2).

### CRYPTO `ml_enhanced_*` SPA-pass is a FALSE POSITIVE

`whites_reality_check` shows `ml_enhanced_FETUSDT/INJUSDT/RENDERUSDT/DYDXUSDT/
STRKUSDT` all PASS SPA. **Do not trust this.** `verified_edge_per_asset_class_
2026-05-09.md` independently flags the same strategies as **placeholder-stat
artifacts** — WR>90% with `sum_pnl`<5% and `avg_loss` ≈ −0.01% to −0.03%
(near-zero-loss closures). SPA tests whether the mean return is significantly
positive; against an artificially ~0 loss series the mean is trivially
positive-significant. SPA **cannot** detect the corrupted-`avg_loss` artifact.
→ The CRYPTO `ml_enhanced` "edges" remain overfit/placeholder-suspect; SPA
passing them is an artifact of the same corrupted data. Confirmed: CRYPTO has
**no verified-live edge**.

### `verified_edge_per_asset_class_2026-05-09.md`

Zero filters passed strict thresholds across all rolling windows. Historical
CRYPTO winners (`source=battleground` PF 2.92, `prediction_market_consensus`
PF 2.52) **stopped emitting** — dead sources, last close 2026-04-10/20. The
"top-winners-stopped-emitting" pattern is real and recurring — it is the single
biggest structural drag: edges are found, then the emitter dies.

### Net synthesis

The .MD review does not surface a *new* edge. It **hardens** the verdict:
- `cot_positioning` (COMMODITY) is the one SPA-validated edge — pursue it.
- CRYPTO `ml_enhanced` SPA-passes are placeholder-stat false positives — discard.
- FOREX `cta_cross_asset_tsmom`-SHORT is promising but **SPA-untested** — gate it.
- Structural priority: fix the **emitter-death** problem (winners stop emitting)
  — no edge matters if the strategy that found it goes silent.
