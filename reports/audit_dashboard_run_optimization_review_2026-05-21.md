# Audit Dashboard GHA Run Optimization Review (2026-05-21)

## Executive summary

**Unified Audit Dashboard** (`audit-dashboard.yml`) failed on every scheduled run from ~07:30 UTC through 01:43 UTC due to `UnboundLocalError: pnl_pct` in `universal_pick_resolver.py` (F-1 cap block outside `if result:`). Fix **`bd2014c20be`** is on `main`; manual dispatch run **26202177578** passed **Resolve active picks** at ~03:00 UTC.

This session adds: **pymysql install before resolver**, **empty valid `stock_picks.json`**, **HTML skip guard in resolver**, **goldmine collector `curl -fsS` + JSON validation**.

---

## Related workflows

| Workflow file | Display name | Trigger | Touches `/audit` deploy |
|---------------|--------------|---------|-------------------------|
| `audit-dashboard.yml` | Unified Audit Dashboard | cron `:10`, `workflow_dispatch` | **Yes** — generator + FTP 3 sites |
| `audit-hourly-update.yml` | Audit Hourly Update | hourly | Partial — lighter refresh |
| `audit-frontend-manifest.yml` | Audit Frontend Manifest | daily + path push | Template/manifest only |
| `audit-drift-telemetry.yml` | (drift telemetry) | 6h cron | Read-only drift |
| `audit-impact-tracker.yml` | Audit Impact Tracker | schedule | Analytics |
| `db-freshness-guardian.yml` | DB Freshness Guardian | hourly | No deploy — DB gate |
| `db-freshness-check.yml` | DB Freshness Check | schedule | No deploy |
| `cross-db-audit.yml` | Cross-DB Strategy Consistency Audit | daily | No deploy |
| `cross-db-consistency.yml` | Cross-DB Consistency | push paths | No deploy |
| `kimi-goldmine-collector.yml` | KIMI Goldmine Data Collection | 2h cron | Feeds `data/goldmine/*` → dashboard |
| `deploy-alpha-dashboard.yml` | Deploy Alpha Engine Dashboard | path push (stale) | Separate alpha UI |
| `deploy-riseoftheclaw.yml` | Deploy Rise of the Claw Dashboard | schedule | GH Pages `/audit/` mirror |
| `mysql-stale-picks-resolver.yml` | MySQL Stale Picks Resolver | schedule | Resolver overlap |
| `paper-trading.yml` | Paper Trading | schedule | `paper_trade_mysql_writer` overlap |
| `hyro-bridge-regen.yml` / `hyro-daily.yml` | Hyro bridge | schedule | Hyro JSON on `/audit` |
| `quant-auditor-fast-pr.yml` | Quant Auditor Fast PR | PR paths | CI on generator changes |
| `growth-stock-screener-daily.yml` | Growth Stock Screener | daily | `growth_stock_picks.json` |

**Push-trigger paths** for generator/resolver (from grep): `quant-auditor-fast-pr.yml`, `audit-frontend-manifest.yml`, `audit-drift-telemetry.yml`, `cross-db-audit.yml`, `cross-db-consistency.yml`, plus the inventory in `AGENTS.md` for `audit-dashboard.yml` (push trigger removed 2026-05-19 — cron + dispatch only).

### Last run status (2026-05-21 ~03:25 UTC)

| Workflow | Last status |
|----------|-------------|
| Unified Audit Dashboard | `pending` / in_progress (dispatch 26202177578, 26202182804) — resolver step **passed** post-bd2014c20be |
| DB Freshness Guardian | `success` (26203283526) |
| Cross-DB Strategy Consistency Audit | `success` (26147648761, daily) |
| KIMI Goldmine Data Collection | `in_progress` (26203169210) |
| Audit Hourly Update | `success` (26199771242) |
| Audit Frontend Manifest | `success` (push-triggered on path change) |

---

## Prior run failures

### Last 3 failed scheduled runs (Unified Audit Dashboard)

| Run ID | Started (UTC) | Duration | Failed step | Root cause |
|--------|---------------|----------|-------------|------------|
| 26199614362 | 2026-05-21 01:17 | 31m55s | Resolve active picks | `UnboundLocalError: pnl_pct` at line 1019 — F-1 cap ran when `check_tp_sl()` returned `None` |
| 26196346964 | 2026-05-20 23:39 | 33m4s | Resolve active picks | Same |
| 26194211601 | 2026-05-20 22:42 | 31m28s | Resolve active picks | Same |

**Log excerpt (26199614362):**

```text
if pnl_pct is not None:
   ^^^^^^^
UnboundLocalError: cannot access local variable 'pnl_pct' where it is not associated with a value
```

**Fix already on main:** `bd2014c20be` — `fix(resolver): guard F-1 pnl_pct cap inside check_tp_sl hit branch` (also `18d125eacc2` stack). Doc: `updates/2026-05-21-audit-dashboard-stale-resolver-unboundlocal.md`.

### Run 26202177578 (workflow_dispatch, post-fix)

- **Status at investigation:** in progress (~43 min), past resolver + paper trade sync + stock prices.
- **Confirms:** resolver regression fixed on current `main`.

### Secondary stale-data contributors (not blocking resolver)

1. **`data/goldmine/stock_picks.json`** — Apache HTML 404 body (`Object not found!`) committed; breaks JSON parse / feed health. Fixed to `{"consensus_picks":[]}`.
2. **`kimi-goldmine-collector.yml`** — `curl -s` silently saved HTML on 404. Fixed with `curl -fsS` + inline JSON validator + empty fallbacks.
3. **Long cron backlog** — 15+ consecutive failures left `/audit` banner stale; next successful FTP deploy from a full green run still required.

---

## Fixes applied (this session)

| # | Change | File(s) |
|---|--------|---------|
| 1 | `pip install pymysql -q` **before** resolver (no `\|\| true`) | `.github/workflows/audit-dashboard.yml` |
| 2 | Replace corrupt HTML with valid empty JSON | `data/goldmine/stock_picks.json` |
| 3 | `_load_json_source()` skips HTML/invalid JSON with warning | `audit_trail/universal_pick_resolver.py` |
| 4 | Goldmine collector: `curl -fsS`, empty fallback, JSON validate | `.github/workflows/kimi-goldmine-collector.yml` |

**Not changed:** `dashboard_generator` (do not run locally per charter). **Already on main:** pnl_pct fix `bd2014c20be`.

---

## Verification

```bash
python3 -c "import py_compile; py_compile.compile('audit_trail/universal_pick_resolver.py', doraise=True)"
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/audit-dashboard.yml'))"
```

Watch dispatch runs 26202177578 / 26202182804 through **Commit updated data** + **Deploy to all 3 FTP sites** for live `/audit` freshness.

---

## Recommendations

1. After next green **Unified Audit Dashboard** run, confirm `https://findtorontoevents.ca/audit/` `dashboard_data.json` `generated_at` advances.
2. Restore `findstocks/.../consolidated_picks.php` on server or keep empty `consensus_picks` until API returns JSON.
3. Consider workflow alert when >2 consecutive resolver failures (actions-failure-guardian already logs DEGRADED).

---

## Post-run update (run 26202177578)

**Recorded:** 2026-05-21T03:48:00Z UTC  
**Run:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26202177578  
**Job:** https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs/26202177578/job/77094254204

### Final verdict

| Field | Value |
|-------|--------|
| **Conclusion** | **success** |
| **Wall clock** | **67.4 min** (02:39:10Z → 03:46:34Z UTC) |
| **Failed step** | None |
| **Duplicate dispatch 26202182804** | **cancelled** (did not compete with primary run) |

### Step timeline (critical path)

| Step | Name | Approx. duration | Notes |
|------|------|------------------|--------|
| 7 | Resolve active picks (TP/SL/time exits) | **~14 min** | 03:04:55 → 03:18:39 UTC; `UnboundLocalError` fix on `main` held; no resolver abort |
| 8–34 | Sidecars (Hyro, ML, DB health, etc.) | **~13 min** | All steps **success** in API job summary |
| 35 | Generate dashboard payload and build HTML | **~6 min** | 03:32:08 → 03:37:45; artifact **~42.5 MB** `dashboard_data.json` |
| 43–42 | Commit + JS validate | **~2 min** | `[skip ci]` commit included refreshed data |
| 44 | Deploy to all 3 FTP sites (parallel) | **~6 min** | 03:40:20 → 03:46:18; `dashboard_data.json` **43,472,947 B** uploaded last per site |
| 45 | Verify URLs | **~2 s** | `/audit` and mirror hosts **HTTP 200** |

**Bottleneck ranking (this run):** resolver ≈ sidecar bundle ≈ FTP (each ~6–14 min); `dashboard_generator` faster than historical 45m-cancel pattern.

### Live `/audit` freshness

| Check | Result |
|-------|--------|
| URL | `https://findtorontoevents.ca/audit/data/dashboard_data.json` |
| **`generated_at` (live curl)** | **2026-05-21T03:32:29.802564+00:00** |
| Advanced past 2026-05-19T08:28:00? | **Yes** (~46h gap closed) |
| P0 stale `/audit` acceptance | **Met** for this dispatch |

### P0 / P1 recommendation updates (post-outcome)

| ID | Prior recommendation | Post-run status |
|----|----------------------|-----------------|
| **P0** | Stale `/audit` until green FTP deploy | **Closed** — run 26202177578 succeeded; live `generated_at` current |
| **P1** | `stock_picks.json` corrupt XML/HTML | **Monitor** — session fixes (`_load_json_source` guard + valid empty JSON) did not block this run; confirm goldmine collector next cron |
| **P1** | Binance `.com` 451 → try `.us` first on GHA | **Still open** — optimization only (noise/latency) |
| **P1** | Duplicate `workflow_dispatch` | **Partially mitigated** — 26202182804 **cancelled**; add concurrency group to prevent double dispatch |
| **P2** | Resolver step timeout vs >36m on step 7 | **Clarified** — step 7 ~14m wall time; earlier “>36m on step 7” was poll timing while sidecars had advanced (API lag) |
| **P2** | Post-deploy `generated_at` guard in CI | **Still recommended** — would have caught pre-2026-05-21 stale regressions automatically |

### Operator follow-ups

1. Rely on **cron** + `workflow_dispatch` only when needed; stale banner should stay green while hourly/dispatch succeeds.
2. Implement **concurrency group** `audit-dashboard` (single-flight) before next manual double-click dispatch.
3. Optional: curl `generated_at` in step 45 Verify URLs and fail if older than 6h.

