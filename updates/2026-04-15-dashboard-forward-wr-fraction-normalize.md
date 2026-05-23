# Dashboard: normalize `forward_wr` when upstream sends a fraction

## What was wrong

Some closed/active pick rows carried `forward_wr` as a **fraction** (e.g. `0.8182` for ~81.8%) while `strat_fwd_wr` from the strategy leaderboard is always **percent** (0–100). The universal forward-stats block in `dashboard_generator.py` only fills `forward_wr` when `forward_trades` is missing or zero, so **pre-populated** picks kept the fractional value. That made **FWD WR** (fallback path) disagree with **strat_fwd_wr** and confused spot-checks.

## What changed

Before the universal forward-stats fill, if `forward_wr` is a **float** strictly in `(0, 1]`, it is converted to percent with one decimal (`* 100`, `round(..., 1)`). **Integer** `1` is left as-is (interpreted as 1% in percent units, matching common JSON patterns).

## How verified

- `python -c "import py_compile; py_compile.compile('audit_trail/dashboard_generator.py', doraise=True)"` exits 0.

## Notes (investigation summary)

- **Strategy FWD WR** (`strat_fwd_wr`) comes from `collect_strategy_leaderboard`: wins / (wins + losses) ×100 on `_filter_valid_resolved_picks`, with wins/losses from **sign of `pnl_pct`** only. **`fwd_trades`** counts every valid resolved pick, including **flat** PnL (0), so **N can exceed wins + losses**; WR denominator excludes flats.
- **High percentages** (100%, 77%, 67%) on small **n** are arithmetically correct but **high variance**; cross-check **n** and whether the cell is **symbol track** vs **strategy-wide**.
