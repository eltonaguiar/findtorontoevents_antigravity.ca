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

## Round 2 — deeper verification (2026-10-06, second pass)

A reconciliation + anomaly harness (`tools/_deep_verify_picks_stats.py`,
throwaway) re-derived everything from the raw payload independently of the
tool's own aggregation. It surfaced three real issues, two of which were fixed:

1. **Drawdown was order-sensitive and mis-ordered (fixed).** The cumulative
   P/L curve was ordered by *entry* time (`_sort_key`), but a pick's P/L is
   realized when it *closes*. DD is now ordered by **realization time**
   (`closed_at` for closed rows; still-open rows appended last) via a new
   `_realization_key`, so it is a genuine realized-then-unrealized equity curve.
   Effect on live data: CRYPTO 248.64 → 233.32 pp, EQUITY 152.17 → 167.12 pp.
2. **Win rate had a hidden denominator (fixed).** `WR%` is `wins ÷ (wins+losses)`,
   so flat (`pnl_pct == 0`) rows — 272 CRYPTO, 133 FOREX, 50 COMMODITY at the
   fresh run — were silently outside the base while the table only showed `N`.
   The tables now carry **`W/L/F`** and an explicit **`Decided`** column, plus a
   header note that N is not the WR base; classes with <30 decided picks are
   flagged `†` (COMMODITY, FUTURES, BOND, SPORTS).
3. **Thin-sample classes are not comparable (documented, flagged).** COMMODITY
   (12/4/50), FUTURES (7/0/3) and SPORTS (0/0/2) rest on a handful of decided
   picks; the `†` marker and footnote say so on the page.

Harness results (fresh payload): **by-date rows reconcile to by-class(window)
rows exactly** for every class (N, W/L, Σ P/L) — PASS; **realized + unrealized
== current Σ P/L** — PASS; ledger PASS.

## Verified

- `py_compile` OK; runs clean against the live URL and against a cached copy.
- Headline numbers recomputed by an **independent** script — exact match for
  every asset class (fresh run: CRYPTO n=2614 W/L/F=1148/1194/272 WR=49.0%
  ΣP/L=+1640.39% PF=1.47; EQUITY 729; see report).
- `max_drawdown()` unit-tested on a controlled 3-trade series (expected 3.0 → got 3.0).
- HTML insertion is byte-verified balanced: exactly +5 `<div`, +5 `</div>`,
  +2 `<table>` and +70 `<tr>` versus the base `main` file, matching the
  generated fragment exactly (45,766-byte file delta).
- The entry appears exactly once and the `INSERT NEW ENTRY BELOW THIS LINE`
  marker still appears exactly once.

## Units / caveats (also stated on the page)

- Σ P/L is a sum of per-pick percentage returns (equal-weight, 1 unit/pick),
  **not** a compounded portfolio return; realized for closed picks, current
  (unrealized) for still-open picks.
- PF is gross-win ÷ gross-loss in the same pp terms; `n/a` when there are no losses.
- Drawdown is the max peak-to-trough of the cumulative Σ P/L series (pp).
- Open-date coverage (fresh run): closed 3399/3500, active 799/804.
- Not financial advice — research/educational.

## ⚠️ Durability finding (why FTP-only is not a deploy)

The first pass FTP-uploaded `updates/index.html` to
`/findtorontoevents.ca/updates/index.html` and verified it live at 02:17 UTC.
**One hour later the entry was gone**: `audit-hourly-update.yml` (cron `:20`)
regenerates the *living* hourly entry from **`main`**, commits it, and the
`push:` trigger fires `deploy-competition-to-site.yml` /`torontoevent-deploy-competition.yml`,
which `lftp … put updates/index.html` back to the FTP host — clobbering any
edit that is not on `main`. Live then differed from `origin/main` only in the
hourly portfolio timestamp.

**Conclusion:** `updates/index.html` changes only persist if they land on
**`main`**. Merging this PR is the real deploy; FTP alone reverts within the hour
(at 04:30 UTC the nightly does it too).

## Handoff

The change is delivered on branch `feat/recent-picks-by-date-class-stats`
(rebased onto current `origin/main`), pushed as PR #714. Re-deployed via FTP for
immediacy, but the durable path is **merging PR #714** so `main` carries the
entry and the hourly/nightly regenerators preserve it.
