# 2026-10-06 — Recent picks: stats by open date × asset class

## What was missing

The `/audit` payload already exposed **per-asset-class** aggregates
(`performance.by_asset_class`, `performance.asset_class_health` with
`max_drawdown_pct`) and a nightly DB table (`at_pick_flow_daily`), but there was
**no breakdown of recent picks by the date they were opened** anywhere — not in
the payload, not on `/audit`, and not on the public updates page.

The public updates page (`findtorontoevents.ca/updates/index.html`) is generated
from `main` (commit → CI → FTP), so the request was to add an entry there that
gives, per open date × asset class: **open date, current P/L, profit factor and
drawdown**.

## What changed

DeepSeek V4.1 Flash (`buffyy`) added:

1. **`tools/recent_picks_by_date_class_stats.py`** — a read-only tool that reads
   the live payload (`https://findtorontoevents.ca/audit/data/dashboard_data.json`,
   overridable with `--json`), combines:
   - `picks.recent_closed` (realized) and
   - `picks.active_raw[status=OPEN]` (unrealized "current" P/L),

   and emits, per **open-date × asset-class** cohort and per **asset class**:
   `n`, closed/open split, wins/losses, win-rate, **Σ P/L%** (sum of per-pick
   `pnl_pct`, equal-weight), **profit factor**, **max drawdown** (max
   peak-to-trough of the cumulative P/L series) and average P/L per pick.
   Outputs Markdown / HTML fragment / JSON. Stdlib only.

   Open date is resolved honestly: `entry_time` when present, else `timestamp`
   when it differs from `closed_at`, else unknown (excluded from the by-date
   table, still counted in the by-class table). Coverage is reported in the
   output, not hidden.

2. **`reports/RECENT_PICKS_BY_DATE_CLASS_2026-10-06.md`** — the generated report.

3. **`updates/index.html`** — a new dated entry at the top of the update list
   (after the `INSERT NEW ENTRY BELOW THIS LINE` marker), rendering both tables
   with the page's dark theme.

## Verified

- `py_compile` OK; runs clean against the live URL and against a cached copy.
- Headline numbers recomputed by an **independent** script — exact match for
  every asset class (CRYPTO n=2617 W/L=1146/1190 WR=49.1% ΣP/L=+1690.64% PF=1.48;
  EQUITY 737, COMPANY/… etc. — see report).
- `max_drawdown()` unit-tested on a controlled 3-trade series (expected 3.0 → got 3.0).
- HTML insertion is byte-verified balanced: exactly +5 `<div` and +5 `</div>`
  versus the base `main` file, matching the generated fragment.

## Units / caveats (also stated on the page)

- Σ P/L is a sum of per-pick percentage returns (equal-weight, 1 unit/pick),
  **not** a compounded portfolio return; realized for closed picks, current
  (unrealized) for still-open picks.
- PF is gross-win ÷ gross-loss in the same pp terms; `n/a` when there are no losses.
- Drawdown is the max peak-to-trough of the cumulative Σ P/L series (pp).
- Open-date coverage (live run): closed 3395/3500, active 824/829.
- Not financial advice — research/educational.

## Handoff

The change is delivered on branch `feat/recent-picks-by-date-class-stats`
(based on `origin/main`) and pushed as a PR. The live page was also FTP-deployed
immediately so it is visible now; merging the PR is what makes it durable, since
`incidents-enhancements-nightly.yml` re-uploads `updates/index.html` from `main`
at 04:30 UTC daily.
