# Reverse Split Registry Fix — 2026-06-04

## What Was Broken

The `audit_trail/reverse_split_symbols.py` registry had three categories of errors:

1. **Wrong effective dates** — LODE, FFIE, and WKHS all had placeholder dates (Jan 1 or Feb 5) instead of actual effective dates.
2. **Missing cumulative splits** — WKHS and FFIE each underwent 3 reverse splits in ~18 months, but the registry only tracked the most recent one. This meant picks submitted before older splits were adjusted by only 1 split factor instead of the full cumulative product (e.g. WKHS was adjusted by 20× instead of the correct 20×12.5×12=3000×).
3. **HOLO missing older splits** — HOLO had 3 cumulative splits (10×, 20×, 40×) since 2024, but only the latest (40×) was tracked. Pre-Feb-2024 picks would only be adjusted by 40× instead of 8000×.

## What Changed

### `audit_trail/reverse_split_symbols.py`

- **Data structure:** Changed from `dict[str, tuple[str, str]]` (one split per symbol) to `dict[str, list[tuple[str, str]]]` (multiple cumulative splits per symbol, newest first).
- **`should_adjust_for_split()`:** Now iterates all splits for a symbol, computing the cumulative product of factors for splits whose effective date is AFTER the pick's submission (i.e. splits that hadn't happened yet). Splits that already occurred before submission are already priced into yfinance/Binance data and are excluded.
- **`parse_split_ratio()`:** Generalised from `1-for-N` only to handle `N-for-M` format (needed for WKHS's 8-for-100 split: factor = 100/8 = 12.5). Returns `float` internally; rounded to `int` for backward compatibility.
- **`get_reverse_split_info()`:** Return type changed from `tuple | None` to `list | None`.

### Registry corrections:

| Symbol | Was | Now |
|--------|-----|-----|
| LODE | `("1-for-10", "2025-02-05")` | `[("1-for-10", "2025-02-25")]` |
| FFIE | `("1-for-40", "2024-01-01")` | `[("1-for-40", "2024-08-19"), ("1-for-3", "2024-03-01"), ("1-for-80", "2023-08-28")]` |
| WKHS | `("1-for-20", "2024-01-01")` | `[("1-for-12", "2025-12-08"), ("8-for-100", "2025-03-17"), ("1-for-20", "2024-06-17")]` |
| HOLO | `("1-for-40", "2025-04-21")` | `[("1-for-40", "2025-04-21"), ("1-for-20", "2024-10-01"), ("1-for-10", "2024-02-01")]` |

## How It Was Verified

- 14 test cases run across all 6 symbols + a non-split symbol, covering picks submitted before all splits, between splits, and after all splits.
- All cumulative factors verified against arithmetic product of individual split factors.
- Backward-compatible: callers (`universal_pick_resolver.py`, `price_tracker.py`) expect `(bool, int | None)` return — unchanged.
- No import changes needed for callers; `is_reverse_split_affected()` unchanged.

## Impact

- **WKHS:** Pre-2024 picks now adjust by 3000× instead of 20× (150× more accurate adjustment).
- **FFIE:** Pre-2024 picks now adjust by 9600× instead of 40× (240× more accurate).
- **HOLO:** Pre-2024 picks now adjust by 8000× instead of 40× (200× more accurate).
- **LODE:** Date corrected by 20 days (Feb 25 not Feb 5). Minimal PnL impact.
- **Downstream:** More accurate entry-price adjustments → fewer MISPRICED_ENTRY false positives → fewer phantom PnL artifacts in the dashboard.

## Additional Data Quality Observations (Not Fixed Here — Known Issues)

These anomalies were found during the audit of the 14-day and 48-hour recency summaries (`pick_summary_stats_2w.json`, `pick_summary_stats_48h.json`):

1. **EQUITY 14d WR=65.5%, PF=5.32, n=8488** — 59.9% from `smart_money` source, 16.3% from `AMZN`. The volume (600+ trades/day) is elevated. PF=5.32 with avg_win≈9.8% suggests either high-concentration tail wins or entry-price artifacts. The main dashboard `asset_class_health` shows EQUITY WR=26.9% / PF=0.33 (n=52) from a different curated cohort. The 14d source is `at_raw_picks` without curation.
2. **FUTURES 14d PF=130.48, mean PnL=360%** — 87.9% from `alpha_engine_unified`, top symbol ZC=F (corn). PF 130 is implausible; likely from a small number of extreme-outlier wins with corrupted entry/exit prices. Caveats flag `dup_groups=204` and `single_source_concentration=87%`.
3. **FOREX 14d WR=83.5%, PF=0.103** — Already flagged/hard-blocked. High WR from many tiny wins; PF=0.103 from a few catastrophic losses. EXPIRED→WON mislabeling at 76%.
4. **ETF 48h WR=100% (n=13)** — All from AlphaEngine `regime_mild_bull` on SPY/QQQ. Single-source concentration flagged. 100% WR during a bull market is regime artifact, not edge. Multiple SPY entries share identical `pnl_pct` values (1.2438% appears 6×) suggesting duplicate signal emission.
5. **Stale recency data:** `pick_summary_stats_48h.json` and `pick_summary_stats_2w.json` last regenerated 2026-05-31 (~3.5 days stale as of 2026-06-04). The `pick-funnel-nightly.yml` workflow should be regenerating these daily at 04:00 UTC. Needs investigation.

Timezone formatting was verified: the frontend JS (`dashboard_freshness.js`, `dashboard_enhancements.js`) already converts UTC timestamps to EST/EDT via `America/Toronto` timezone. No changes needed.

## Sources

- Split dates and ratios: [splithistory.com](https://splithistory.com)
- Cross-verified with Yahoo Finance split history where available
- 14 non-penny-stock symbols in the penny/cheap-stocks universe (ASTS, RKLB, WULF, QBTS, IONQ, RGTI, CTM, MVST, CLSK, MARA) confirmed to have zero reverse splits in 2023-2026
