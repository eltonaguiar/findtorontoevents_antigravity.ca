# Stage-B / CI-Cancellation Consult — 2026-05-19

Multi-AI consult on a 2-part infrastructure problem, consensus synthesis, and the
fixes implemented. Engines: **Grok** (xAI headless) + swarm **deepseek / xai / kilo**
(`consensus-3` + `fast-cheap` presets) — 4 distinct models, 5 responses.

---

## The Problem

### Problem A — wasteful CI cancellations
`.github/workflows/audit-dashboard.yml` ("Unified Audit Dashboard") regenerates
`findtorontoevents.ca/audit`. It had `concurrency: group=dashboard-publish-{push|cron}`,
`cancel-in-progress: false`, an hourly `schedule` (`10 * * * *`), AND a `push` trigger on
~70 dashboard source-code paths. The job runs ~35 min. In this storm-commit repo,
push-triggered runs pile into the `push` concurrency group faster than the 35-min job
drains; with `cancel-in-progress: false` GitHub keeps the running run + the newest queued
run and auto-cancels the **intermediate** queued runs (verified: cancelled runs have
`jobs_executed=0` — never started). Benign for correctness (latest always completes,
hourly cron in a separate group always survives) but wasteful, and a specific commit's
dashboard refresh can be skipped.

### Problem B — resolver `no_price` blocks safe Stage-B writes
`alpha_engine/active_picks_sync.py` is a MySQL-native resolver that reads `at_raw_picks`
OPEN rows, fetches live prices, detects TP/SL/time-exit, and writes terminal verdicts.
The Stage-A dry-run log showed pervasive `no_price` for non-crypto classes: multi_asset
35/35, stocks_competition 123/124, regime_terminal 9/9, alpha_engine 49/84. The non-crypto
path used `yf.Tickers(" ".join(symbols)).history(period="1d", interval="1m")` then read
`data["Close"][sym]`. CRYPTO (api_failover) worked fine.

**IMPORTANT live-state finding (surfaced during this task):** the workflow on `origin/main`
*already has Stage B flipped to `--apply`* (`ACTIVE_PICKS_SYNC_APPLY: '1'` + `--apply`,
audit-dashboard.yml step "Active picks sync (LIVE...)"). A peer/earlier session did the
flip on 2026-05-18. So the `--apply` writer is **live now**. It is only "safe-ish" because
`no_price` picks are *skipped* (stay OPEN) — meaning Stage B currently does almost nothing
for non-crypto. This makes the Q-B fix urgent: once `no_price` drops, the writer must be
fetching the *correct* price form. (Per task scope, this consult did NOT touch the
`--apply` flag itself — see "Operator-gated remaining" below.)

---

## Questions

- **Q-A:** Drop the `push` trigger, keep it, or add a debounce?
- **Q-B:** Concrete fix to drop the `no_price` rate so Stage-B `--apply` is safe — symbol
  normalization, per-class fallback, or are the symbols genuinely dead?

---

## Each AI's Answer

### Grok (xAI headless)
- **Q-A:** Drop the push trigger entirely. Hourly cron + `workflow_dispatch` suffice;
  removing it deletes ~60 lines of conditional path/skip-ci logic and lets concurrency
  collapse to one group. Trade-off: occasional sub-hour staleness — negligible for a
  trading dashboard.
- **Q-B:** Systemic fetch bug, **not** delisted symbols. `yf.Tickers(...).history()` for a
  multi-symbol request returns a **MultiIndex-column DataFrame**, so the guard
  `"Close" in data.columns` is False and every symbol silently falls through to
  `no_price`. Fix: use `yf.download(group_by="ticker")` (stable per-ticker MultiIndex) or
  per-symbol `yf.Ticker().history()` (flat frame, always has "Close"); keep canonical
  `=X`/`=F` suffixes — that IS the yfinance form. Confirmed equity classes
  (multi_asset / stocks_competition) imply plain valid tickers, so a 35/35 / 123/124
  all-fail rate is structural, not 35 dead stocks.

### swarm — deepseek (consensus-3)
- **Q-A:** Remove push, rely on hourly cron; add `workflow_dispatch` as an emergency
  valve. Rejects debounce (needs external infra; the problem is queue depth, not trigger
  frequency).
- **Q-B:** Option (1) — systemic fetch bug. Replace `yf.Tickers()` with per-symbol
  `yf.Ticker().history()` so one bad symbol can't poison the batch. Optional Stooq
  fallback (free, no key). Explicitly: "Do NOT mark as resolved-as-expired — the all-fail
  rate proves it's a fetch bug."

### swarm — xai (consensus-3)
- **Q-A:** Drop the push trigger; cron covers it. If sub-hour latency is ever wanted,
  re-add push with `cancel-in-progress: true` on the push group only — never `false`.
- **Q-B:** Format mismatch, not dead symbols. Switch to
  `yf.download(tickers=..., group_by="ticker")` and read `(sym, "Close")` from the
  MultiIndex; fall back to `api_failover` / Stooq for stragglers.

### swarm — kilo (consensus-3)
- **Q-A:** Drop the push trigger; hourly cron gives refresh within the hour.
- **Q-B:** Replace lines 256-276 of `active_picks_sync.py` with
  `yf.download(..., group_by="ticker", threads=True)`, handling the 1-symbol flat-column
  case vs the multi-symbol per-ticker MultiIndex case, with per-symbol `try/except`.
  Provided an exact diff.

### swarm — deepseek (fast-cheap, breadth round)
- **Q-A:** Same — remove `push:`, add `workflow_dispatch`.
- **Q-B:** Same root cause. **Minor dissent:** suggested *stripping* `=X`/`=F` suffixes
  before the yfinance call. This is **wrong** — yfinance *requires* `EURUSD=X` / `ES=F`;
  stripping breaks forex/futures fetches. Overruled by the 3 consensus-3 engines + Grok,
  which all keep the suffix. (`canonicalize_symbol()` in `asset_classification.py` only
  *adds* `=X`/`=F` for FOREX/FUTURES and leaves equity/ETF tickers untouched — so the DB
  already holds the correct yfinance form; no stripping needed.)

---

## Consensus

### Q-A — UNANIMOUS (4/4 engines): drop the `push` trigger.
Hourly cron (`10 * * * *`) guarantees a refresh within the hour; `workflow_dispatch`
is the emergency valve. No debounce (queue-depth problem, not trigger-frequency problem).
With `push:` gone, the concurrency group collapses to a single `dashboard-publish`.

### Q-B — UNANIMOUS (4/4 engines): systemic yfinance fetch bug; symbols are NOT dead.
Root cause: `yf.Tickers(" ".join(symbols)).history()` returns a MultiIndex-column
DataFrame for multi-symbol requests, so `"Close" in data.columns` is False and 100% of
non-crypto symbols silently become `no_price`. Fix: switch to
`yf.download(..., group_by="ticker")`, handle the single-symbol flat-column case vs the
multi-symbol per-ticker MultiIndex case, with per-symbol `try/except`. **Keep** the
canonical `=X`/`=F` suffixes — that is the form yfinance expects. The only dissent
(fast-cheap deepseek suggesting suffix-stripping) is technically incorrect and overruled.

---

## What Was Implemented

### Q-A — `.github/workflows/audit-dashboard.yml`
1. Removed the entire `push:` trigger block (~70 path entries + comments). `on:` now has
   only `schedule` + `workflow_dispatch`.
2. Collapsed `concurrency.group` from
   `dashboard-publish-${{ github.event_name == 'push' && 'push' || 'cron' }}` to a static
   `dashboard-publish`. `cancel-in-progress: false` kept (scheduled/dispatch runs queue
   and finish in order). The job-level `if: github.event_name != 'push' || ...` guard is
   now always-true but left in place — harmless, and protective if `push:` is ever re-added.
3. YAML validated: `python -c "import yaml; yaml.safe_load(...)"` -> triggers
   `['schedule', 'workflow_dispatch']`, concurrency `{group: dashboard-publish,
   cancel-in-progress: False}`.

### Q-B — `alpha_engine/active_picks_sync.py::fetch_live_prices`
Replaced the non-crypto branch's `yf.Tickers(...).history()` + `"Close" in data.columns`
pattern with `yf.download(tickers=" ".join(symbols), period="1d", interval="1m",
group_by="ticker", auto_adjust=False, prepost=False, threads=True, progress=False)`.
Per-symbol read: single-symbol -> flat `data["Close"]`; multi-symbol -> per-ticker
MultiIndex `data[sym]["Close"]`. Per-symbol `try/except` so one bad ticker can't poison
the rest. Canonical `=X`/`=F` symbols kept as-is. `py_compile` passes. The existing
fail-loud guard (0/N prices in APPLY mode raises) is untouched and now backstops the new
path.

---

## Operator-Gated / Remaining

- **Stage-B `--apply` itself was NOT touched** by this task (per scope). It is *already*
  ON in `origin/main` (`ACTIVE_PICKS_SYNC_APPLY: '1'`). Recommended operator follow-up:
  after this Q-B fix merges and one scheduled run completes, **verify the `no_price` rate
  actually dropped** (inspect `reports/active_picks_sync_dryrun_*` / the LIVE-step log /
  `apply_results.db_updates_ok`). If `no_price` is still high, the fail-loud guard will
  now raise in APPLY mode rather than mass-skip — that is the intended safety behavior,
  but it means the LIVE step will go red until the fetch is genuinely fixed.
- **Stooq / AlphaVantage per-class fallback** (deepseek + xai suggested it as optional)
  was NOT implemented — out of scope for a bounded surgical fix, and the `yf.download`
  switch alone should clear the systemic all-fail. Queue as a follow-up if a residual
  `no_price` tail remains after verification.
- No symbols were mass-marked resolved-as-expired — all 4 engines agreed the all-fail rate
  is a fetch bug, not delisting.

---

*Generated 2026-05-19. Engines: Grok (xAI) + swarm deepseek/xai/kilo.
Swarm runs: `swarm_runs/stageb_consult_c3`, `swarm_runs/stageb_consult_fc`.*
