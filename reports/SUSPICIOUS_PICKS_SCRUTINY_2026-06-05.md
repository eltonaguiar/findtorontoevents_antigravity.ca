# Suspicious High-WR/PF "Picks" — Scrutiny 2026-06-05

**Source:** live `ejaguiar1_stocks.trading_picks`, `closed_at IS NOT NULL`, status in {TP_HIT, SL_HIT, LOST, TIME_EXIT, WON}. Pulled 2026-06-05 ~06:18 UTC.

**Bottom line:** Of 6 "T2-shaped" candidates surfaced from the bootstrap forward dashboard, **5 are artifacts and 1 is a single-asset crypto bet**. None are real cross-sectional strategies that would survive forward.

---

## Per-suspect verdict

### 1. `prediction_market_consensus` — **REFUTED**
- Headline: **n=89, WR 89.9%, PF 24.51** ⇒ Live DB: n=121, WR=66.1%, PF inflated.
- **Single-day batch:** 38.0% of all closes (46 of 121) stamped on 2026-04-15 — 45 wins / 1 loss. The headline WR is essentially "April 15 happened."
- **Symbol concentration:** 41.3% DOGEUSDT, 19.8% SOLUSDT — meme-heavy.
- **Fat-tail PF:** top win +80.37% XRPUSDT on 2026-04-18 carries most of the PF.
- **Zero-pnl inflation:** 32 of 121 rows have `pnl_pct=0 OR NULL` — counted as "decisive" by the dashboard's PF math.
- **Verdict:** the bootstrap PF 24.51 is one-day batch + meme concentration + one outlier. Not edge.

### 2. `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` — **SUSPECT (single-asset bet, not strategy)**
- Headline: n=34, WR 94.1%, PF 10.36 ⇒ Live DB: n=34, 32 wins, 2 losses, 22 distinct dates over 2026-02-22 → 2026-05-25.
- **100% DYDXUSDT** — single-symbol "strategy".
- Dates well-spread (max 3 closes on any one day). PnL range is modest +3.4 to +3.9% per win.
- **Verdict:** this isn't an edge — it's a 3-month DYDX rally captured by a single-asset model. Not portable; will not generalize. Cannot be promoted to a "class T2" finding.

### 3. `regime_mild_bear` — **REFUTED**
- Headline: n=34, WR 70.6%, PF 6.63 ⇒ Live DB: n=60, 24 wins, 10 losses, **26 zero-pnl rows (43%) counted as wins by the dashboard**.
- True WR = 24 / 60 = **40.0%** (loser).
- **Single-day batch:** 30% on 2026-06-02 (18 closes, 15 wins). The 2026-05-28 batch of 15 had **0 wins** — net is wash, not edge.
- **Symbol concentration:** 43.3% GOOGL.
- **Top-3 wins are the same row (+7.67% GOOGL @ 2026-06-02 13:45:14)** — duplicate row inflation. Per [[feedback-incident-page-stale-vs-live-db]] this is INCIDENT #91-style dup-group bleedover that may not have been fully purged for `regime_mild_bear`.
- **Verdict:** strongest refute. Demote to LOW_CONFIDENCE or kill.

### 4. `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` — **REFUTED**
- Headline: n=30, WR 83.3%, PF 6.83 ⇒ Live DB: n=30 (count looks right), but…
- **30% of closes on a single day (2026-03-16): 9 closes, 9 wins, top wins +34.85% / +34.07% / +32.55% all on that one date.**
- That's the RENDER pump of mid-March 2026 (verifiable via crypto historicals).
- **100% RENDERUSDT** — single-asset.
- Sibling `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` was already moved to LOW_CONFIDENCE in PR #542 ([Kimi/Cursor 30-day plan](../updates/2026-06-05-grok-masterplan-phase1-shipped.md)). The 1h variant should follow.
- **Verdict:** one-day pump captured by a single-asset model. Not edge.

### 5. `ig_contrarian_sentiment` — **REFUTED**
- Headline: n=276, WR 47.5%, PF 18.82 ⇒ Live DB: n=283, 131 wins, **145 losses** (actual WR 46.3%).
- "PF huge but WR<50%" is the bait pattern — PF 18.82 is driven by **two outsized FX wins**: +79.55% NZDUSD @ 2026-04-22 20:30, +48.01% USDCAD @ 2026-04-21 10:41.
- Remove those two outliers and PF collapses below 1.0.
- **Date concentration:** 24.7% on 2026-04-15 (likely U.S. CPI / FX vol day) — 70 closes, only 22 wins.
- **Verdict:** 2-outlier-driven PF, broad strategy with sub-50% WR, vol-day concentration. Not edge. Already in Kimi's kill list as `ig_contrarian_sentiment` (see `strategy_kill_audit.jsonl`).

### 6. `myfxbook_retail_contrarian` — **REFUTED**
- Headline: n=349, WR 48.1%, PF 3.79 ⇒ Live DB: n=359, 168 wins, 181 losses.
- **Same +79.55% NZDUSD outlier as ig_contrarian_sentiment** (2026-04-23 02:01) — suggests these two strategies are picking up the same FX dislocation and the outlier is doing the lifting for both.
- 20.6% of closes on 2026-04-22 (40 wins / 74 closes = 54% on that day; balance of trades are coin-flip losing).
- **Verdict:** same fat-tail + vol-day batch artifact as #5. Kimi's kill list already includes `myfxbook_retail_contrarian`.

---

## What's left after scrubbing the headlines

| Pattern caught | Strategies | Action |
|---|---|---|
| pnl=0 rows counted as wins | `regime_mild_bear` (26/60 = 43%) | **Bug** — `bootstrap_forward_stats` and per-class WR calc should exclude `pnl_pct=0 OR NULL` (or count them as flat, not win) |
| Single-day batch concentration | `prediction_market_consensus`, `regime_mild_bear`, `myfxbook_retail_contrarian` | Add `max_single_day_share < 25%` gate to promotion criteria |
| Single-symbol "strategies" | `ml_enhanced_DYDXUSDT_15m`, `ml_enhanced_RENDERUSDT_1h`/`_4h` | Already partly handled by Kimi's LOW_CONFIDENCE demotion — apply same rule to the 1h variant + DYDX |
| Fat-tail PF (1-2 outlier-driven) | `ig_contrarian_sentiment`, `myfxbook_retail_contrarian`, `prediction_market_consensus` | Add `PF_without_top_2_wins ≥ 1.2` gate before promotion |
| Duplicate row inflation | `regime_mild_bear` (top-3 wins are identical +7.67% GOOGL @ 2026-06-02 13:45:14) | Verify INCIDENT #91-style dedup ran on `trading_picks`, not just `at_signal_outcomes` |

## The one honest candidate from the parallel investigation

The companion deep dive (memory: [[project-true-winners-investigation-2026-06-05]]) ran the same OOS-split test on the rest of the live-forward universe. Only sleeve that survives:

- **`fx_smart_carry_trade_momentum`** — FOREX, n=25, WR 60%, PF 1.85, 1.5:1 R:R, OOS-robust on first/second-half split, 8 symbols, 12 dates, no fat tail. Needs 75 more trades to reach n=100 T2 floor (~5-6 weeks at current cadence).

This is the one real bridge candidate. Everything else flagged on `/audit` as "T2-shaped" is artifact.

## Recommended follow-up PRs

1. **Gate addition** (priority P0): in `tools/clean_ingest_v2.py` or `audit_trail/promotion_gate.py::evaluate_forward_tier2()`, add `max_single_day_share`, `pf_without_top_2_wins`, `wr_excluding_pnl_zero` filters.
2. **Demote** `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack`, `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` to LOW_CONFIDENCE (1h Render variant parallels the 4h that's already demoted).
3. **Audit** `regime_mild_bear` for INCIDENT #91-style dup rows on `trading_picks` (the +7.67% GOOGL row appears 3× in top-3 wins).
4. **Wire** `fx_smart_carry_trade_momentum` into the daily verified pilot runner with explicit n→100 tracker.

---

Filed by `/loop` blitz at 2026-06-05 ~06:20Z. Evidence is direct live-DB query (no JSON-cache reliance). Cross-references: [[project-true-winners-investigation-2026-06-05]], [[project-ai-tournament-wr-artifact-2026-06-03]], [[feedback-incident-page-stale-vs-live-db]].
