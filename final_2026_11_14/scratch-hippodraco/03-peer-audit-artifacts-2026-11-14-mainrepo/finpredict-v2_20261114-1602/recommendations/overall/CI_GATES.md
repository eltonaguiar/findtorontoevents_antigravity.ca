# CI_GATES — workflow and gate changes

**Purpose:** encode the `DATA_CONTRACT.md` invariants and the P0/P1 fixes as CI gates so the failure classes cannot silently return. Each gate names the workflow/file and the exact insertion point (verified line numbers as of 2026-11-14).

Principles:
- Gates that protect **published truth** (WR, PnL, quote honesty) **fail hard**.
- Gates that protect **freshness** fail hard for the hourly pipeline, `--warn-only` for weekly/monthly sources.
- Gates must be cheap (< 60 s) and deterministic; no live network required for the contract suite.
- Never re-enable the `push:` trigger on `audit-dashboard.yml` (documented removal rationale at `.github/workflows/audit-dashboard.yml:6-15`).

---

## Gate map

| Gate | Where | Trigger | Failure mode |
|---|---|---|---|
| G1 summary population | `ci-tests.yml` + `audit-dashboard.yml` | every PR + hourly build | hard fail |
| G2 quote honesty | `audit-dashboard.yml` (post-generator) | hourly build | hard fail |
| G3 metric liveness | `audit-dashboard.yml` (post-generator) | hourly build | hard fail |
| G4 dedup/identity | `audit-dashboard.yml` (pre-deploy) | hourly build | hard fail |
| G5 sidecar freshness | `audit-dashboard.yml` + deploy | hourly build | hide panel / hard fail |
| G6 strict JSON | `audit-dashboard.yml` (pre-deploy) | hourly build | hard fail |
| G7 workflow hygiene lint | `ci-tests.yml` | every PR | hard fail |
| G8 scheduler guard | `ci-tests.yml` (static) | every PR | hard fail |
| G9 DB freshness | existing `db-freshness-guardian.yml` | hourly | hard fail (already exists) |
| G10 open-pick backlog | `db-freshness-guardian.yml` | hourly | hard fail |
| G11 source authenticity | nightly | hard fail |
| G12 push contention | `ci-tests.yml` static + run audit | PR + nightly | warn |
| G13 secret scan | existing `db-password-leak-guard.yml` | push/PR | hard fail |

---

## G1 — Summary population invariants

**File:** new `tests/test_summary_picks_population.py` (see `../patch_plan/acceptance_tests.md#at-p0-2`).

**CI wiring:**
- `.github/workflows/ci-tests.yml:203` already runs `python -m pytest tests/ ...`; the test is picked up automatically.
- In `.github/workflows/audit-dashboard.yml`, immediately after `python tools/sync_summary_picks_json.py` at **:627**, add:
  ```yaml
  - name: Gate G1 — summary population
    run: |
      python - <<'PY'
      import json
      d=json.load(open("audit_dashboard/data/summary_picks.json"))
      bad=[c for c in d["asset_classes"]
           if c["win_rate_pct"] is not None
           and (c["wins"]+c["losses"]>c["resolved"] or c["win_rate_pct"]>100)]
      assert not bad, bad
      print("G1 OK:", d["n_asset_classes"], "classes")
      PY
  ```

**Blocks:** re-introduction of `tools/sync_summary_picks_json.py:63-65,161` overlapping populations (7 classes > 100 %).

---

## G2 — Quote honesty (no fabricated 0.00 %)

**File:** new `tests/test_quote_contract.py`.

**CI wiring (post-generator, before deploy):** add after the generator step in `.github/workflows/audit-dashboard.yml` (the generator is invoked around `:628`, `python -m audit_trail.dashboard_generator`):
```yaml
- name: Gate G2 — quote honesty
  run: |
    python - <<'PY'
    import json
    d=json.load(open("audit_dashboard/data/dashboard_data.json"))
    bad=[]
    for p in d["picks"]["active"]:
        cp,ep,pnl=p.get("current_price"),p.get("entry_price"),p.get("pnl_pct")
        if p.get("quote_status") not in ("QUOTED","UNQUOTED"):
            bad.append((p.get("symbol"),"missing quote_status"))
        if cp not in (None,0) and ep not in (None,0) \
           and abs(float(cp)-float(ep))<1e-9 and pnl==0.0:
            bad.append((p.get("symbol"),"frozen at entry, pnl 0"))
    assert not bad, bad[:10]
    print("G2 OK")
    PY
```

**Blocks:** regression of `_enrich_live_pnl` (`audit_trail/dashboard_generator.py:1618-1846`) to inherited `pnl_pct: 0.0` on unquoted rows. Current violations: 19/20 active, 202 exact `current==entry` raw rows.

---

## G3 — Metric liveness

**File:** new `tests/test_sym_track_population.py` (unit) + live check.

**CI wiring:** after G2:
```yaml
- name: Gate G3 — metric liveness
  run: |
    python - <<'PY'
    import json
    d=json.load(open("audit_dashboard/data/dashboard_data.json"))
    a=d["picks"]["active"]
    track=sum(1 for p in a if (p.get("sym_track_total") or 0)>0)
    fwd=sum(1 for p in a if p.get("strat_fwd_wr") is not None)
    print(f"Track populated {track}/{len(a)}; FWD WR populated {fwd}/{len(a)}")
    # Hard floor: at least one populated Track and one populated FWD WR while
    # the closed ledger has >= 100 rows. INSUFFICIENT is allowed per-column,
    # but a fully dead column on a 20-row panel is a regression.
    assert track >= 1, "Track structurally empty (sym_track builder population bug)"
    PY
```

**Blocks:** `_build_strategy_symbol_track_stats` being fed the active slice (`audit_trail/dashboard_generator.py:1830-1832`, call site `:14551`) instead of the closed pool.

**Display contract:** the template must render `INSUFFICIENT` rather than a bare dash for missing metrics:
- `audit_dashboard/template.html:8699` (Track) — replace `\u2014` with the `INSUFFICIENT` badge when `n == 0`.
- `audit_dashboard/template.html:9043` (EDGE) — replace `&mdash;` with `INSUFFICIENT`.
- `audit_dashboard/template.html:9050` (FWD WR) — same.
- `audit_dashboard/template.html:9067` (FWD N) — show `n<5` / `INSUFFICIENT` when `n < 5` instead of a red `0`.

---

## G4 — Dedup / identity invariants

**File:** new `tests/test_active_raw_dedup.py`.

**CI wiring:** pre-deploy:
```yaml
- name: Gate G4 — dedup/identity
  run: |
    python - <<'PY'
    import json
    from collections import Counter
    d=json.load(open("audit_dashboard/data/dashboard_data.json"))
    rows=d["picks"]["active_raw"]
    ids=[r.get("id") for r in rows if r.get("id")]
    dup={k:v for k,v in Counter(ids).items() if v>1}
    expired=sum(1 for r in rows if str(r.get("status","")).upper()=="EXPIRED")
    x=({r.get("id") for r in rows if r.get("id")} &
       {r.get("id") for r in d["picks"]["recent_closed"] if r.get("id")})
    assert not dup, f"{len(dup)} duplicate ids"
    assert not x, f"{len(x)} cross-surface ids"
    assert expired/max(1,len(rows)) <= 0.05, f"EXPIRED {expired}/{len(rows)}"
    print("G4 OK")
    PY
```

**Blocks:** the current 4,148/3,851 split, 3,377 `EXPIRED` inventory rows, 56 cross-surface collisions, and regression to pre-prune `active_raw` (capture at `audit_trail/dashboard_generator.py:9538`, assignment at `:17481`).

---

## G5 — Sidecar freshness manifest

**Files:** `tools/assert_sidecar_freshness.py` (new; model on `tools/assert_model_freshness.py:1-50`) + `audit_dashboard/data/sidecar_freshness_manifest.json`.

**CI wiring:** in `.github/workflows/audit-dashboard.yml`, after all sidecar build steps and before deploy:
```yaml
- name: Build sidecar manifest
  run: python tools/build_sidecar_freshness_manifest.py
- name: Gate G5 — sidecar freshness
  run: python tools/assert_sidecar_freshness.py --max-age-hours 24
```

**Declared thresholds** (override per file in `audit_dashboard/data/sidecars.yaml`):

| Sidecar | max_age_hours | on stale |
|---|---:|---|
| `dashboard_data.json` / `dashboard_payload.json` | 3 | fail |
| `money_ready_verdict.json`, `pf_registry.json`, `anti_overfit_audit.json` | 3 | fail |
| `summary_picks.json`, `db_health.json` | 3 | fail |
| `ma_strategy_leaderboard.json` | 48 | warn |
| `hyro_pick_performance.json` | 168 | hide |
| `hyrotrader_picks.json` | 168 | hide (or mark static) |
| `regime_report.json`, `strategy_ic_analysis.json`, `strong_signals.json`, `stock_forex_prices.json`, `pilot_forward_dashboard.json`, `strategy_admissibility.json`, `operator_review_today.json` | 24 | hide |
| `claude/grok/kimi/mercury/ag_top_picks*.json` | 24 | hide/retire |
| `strategy_tribunal_latest.json` | 24 | hide (currently 404) |

**Client behavior:** one helper `loadSidecarIfFresh(url, panelId)` wraps the fetch sites at `audit_dashboard/dashboard_enhancements.js:115`, `audit_dashboard/template.html:1329`, `:17656`, `:17744`, `:17763-17765`; when stale, render `Panel hidden — last updated <date> (<N> d)`.

**Blocks:** re-serving 79–245-day-old numbers as current (10+ sidecars).

---

## G6 — Strict JSON

**CI wiring:** pre-deploy:
```yaml
- name: Gate G6 — strict JSON
  run: |
    python - <<'PY'
    import json, glob
    bad=[]
    for f in glob.glob("audit_dashboard/data/*.json"):
        t=open(f,"rb").read()
        if b"NaN" in t or b"Infinity" in t: bad.append((f,"non-finite literal"))
        try: json.loads(t)
        except Exception as e: bad.append((f,str(e)))
    assert not bad, bad
    print("G6 OK")
    PY
```
**Blocks:** `money_ready_verdict.json` (`NaN`) and `strategy_ic_analysis.json` (`Infinity`), which currently throw in browser `JSON.parse`.

---

## G7 — Workflow hygiene lint

**Files:** new `tools/lint_workflows.py`; wire into `.github/workflows/ci-tests.yml` (add a step near the matrix jobs at `:45-55`).

Rules enforced:
1. No `update-environment: false` (197 files today; P0-3 fixes 9, P1-3 the rest).
2. Every workflow that runs `git push` must use `.github/scripts/safe_push.sh`.
3. Every job has `timeout-minutes`.
4. Every push-capable workflow has a `concurrency.group`.
5. Direct-invoked `tools/*.py` modules use the absolute-import bootstrap from AGENTS.md (catches the `no module named 'tools'` class).

**Blocks:** the Python 3.14 cluster and the `ModuleNotFoundError: No module named 'tools'` failure.

---

## G8 — Scheduler guard

**File:** new `tests/test_audit_dashboard_schedule.py`.

Static assertions:
- `.github/workflows/audit-dashboard.yml` cron period ≥ p95 runtime (after P0-4: `'10 */2 * * *'`).
- `group: dashboard-publish` and `cancel-in-progress: false` remain.
- `timeout-minutes` present on the job (`:55`).
- `push:` trigger remains absent (`:6-15`).

Runtime gate (nightly):
```bash
gh api "repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows/audit-dashboard.yml/runs?created=%3E%3D$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)&per_page=100" \
  --jq '[.workflow_runs[]|select(.conclusion=="cancelled")]|length'   # must be <= 5% of runs
```

**Blocks:** the 61/168 cancellation cascade.

---

## G9 — DB freshness (existing, keep)

**File:** `.github/workflows/db-freshness-guardian.yml` (hourly at `:12`), driven by `tools/db_freshness_check.py`.
**Action:** no change to thresholds; add `open_bloat` (G10) to its summary if not already present.

---

## G10 — Open-pick backlog

**File:** extend `tools/db_freshness_check.py` (checks begin at `:176` `check_live_picks`, `:206` `check_resolver_outputs`, `:290` `check_intrabar_resolution`).

New check:
```python
def check_open_bloat(conn):
    # RED if open_count/total_count > 0.40 or hours_since_last_close > 12
    ...
```
**Current:** `open_count = 90,523 / 143,156 = 63.2 %`, `hours_since_last_close = 3`.
**Wiring:** `.github/workflows/db-freshness-guardian.yml` already publishes RED as a CI failure.

**Blocks:** the 63 % survivorship gap becoming invisible again.

---

## G11 — Source authenticity (nightly)

**File:** new `tests/test_source_authenticity.py` + `.github/workflows/source-authenticity-nightly.yml`.

Checks:
- `data-api.polymarket.com/v2/leaderboard` → 200; v1 → 410 (and **no v1 call in production code**).
- No dashboard system has `status: "dead"` while its artifact file was modified in the last 24 h (`copy_trader_intel` case).
- No source counted in `consensus` with `resolved_n < 30` (Kalshi `0 resolved`).
- No `funding_rate_arb`/`btc_breakout` artifact exists while the system is ghost-excluded (`audit_trail/dashboard_generator.py:8870`).

**Blocks:** dead/ghost sources being displayed or weighted.

---

## G12 — Push contention

**Static (PR):** `tools/lint_workflows.py` rejects hand-rolled push loops; PEAD's loop at `.github/workflows/pead-shadow-collector.yml:82-103` is the reference violation.

**Runtime (nightly):**
```bash
gh api "repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs?created=%3E%3D$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)&per_page=100" \
  --jq '[.workflow_runs[]|select(.conclusion=="failure")|.name]|unique'
```
Alert if any name matches `(Live Spike|PEAD|Mirror)`; do not fail the PR.

---

## G13 — Secret scan (existing, enforce)

**File:** `.github/workflows/db-password-leak-guard.yml` (already fails on env-key patterns at `:63`). Extend the pattern list to Google API keys (`AIza...`) and cloud tokens. Do not print matches; print file + line + rule id only.
**Finding to fix first:** tracked key literals in `STOCKSUNIFY/scripts/lib/stock-api-keys.ts`, `STOCKSUNIFY/STOCKSUNIFY2/scripts/lib/stock-api-keys.ts`, `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js`; add `dbpasses.txt` to `.gitignore` (currently not ignored, not tracked).

---

## Deployment order for gates

1. **Week 1:** G1, G2, G6, G8 (cheap, deterministic, no schema change). Wire into `ci-tests.yml` + post-generator hooks.
2. **Week 2:** G3, G4, G5 after P0-6/P0-8 land (they would fail today otherwise).
3. **Week 3:** G7, G10, G12 after P1-3/P1-5.
4. **Week 4:** G11, G13 after source migration and key rotation.

Gates that would fail on today's data are intentionally staged after their P0 fix; landing a gate before its fix blocks the deploy pipeline with no remediation path.

---

## Guardrails (do not regress)

- Keep `[skip ci]` on the dashboard's own commit message (infinite-loop protection).
- Do not re-add `push:` to `audit-dashboard.yml`.
- Do not use broad `paths:` globs that match generated `data/*.json`.
- Keep `cancel-in-progress: false` on `dashboard-publish` until G8 proves p95 ≤ cron period.
- Any new pipeline dependency must be added to the AGENTS.md path registry in the same PR.
