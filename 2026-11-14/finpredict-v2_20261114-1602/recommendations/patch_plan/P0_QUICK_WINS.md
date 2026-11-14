# P0 Quick Wins — cross-cutting remediation (CI / data contract / metrics / honesty)

**Audit frame:** 2026-11-14T16:20Z · repo `finpredict-v2` (read-only) · live evidence in `../MASTER_AUDIT.md`, `../sub/{A,B,E,F}*.md`, `../raw/`.
**P0 rule:** each item ≤ 1 engineering day, low blast radius, independently revertible.
**No fabricated numbers.** Every count below was re-derived from `../raw/*.json` or re-read from the named source line. Line numbers were verified with `grep -n` / `nl -ba` on 2026-11-14.

Ranked by (impact ÷ risk). Top 5 are called out in the final report.

| Rank | Fix | Root cause (audited number) | Effort | Risk | Owner area |
|---:|---|---|---|---|---|
| **P0-1** | Guard the forex direction bucket | `KeyError: 'LONG'` killed **93 runs/24 h** (ALPHA 47 + FAST 46) | S (30 min) | Low | alpha_engine |
| **P0-2** | Single-population `summary_picks` query + clamp/assert | **7 classes report WR > 100 %** (max INDEX 1,141.2 %); 8 classes have `wins+losses > resolved` | S (2 h) | Low | tools |
| **P0-3** | Stop `update-environment: false` from resolving Python 3.14 | **8 enumerated workflows** fail compiling `pandas==2.1.4` (audit note: ≥9); log shows `python found: YES 3.14` despite `python-version: '3.11'` | S (2 h) | Low | CI |
| **P0-4** | Space the audit-dashboard cron to its real runtime | **61/168 runs cancelled in 7 d**; median success **84.5 min** vs hourly cron | S (15 min) | Low | CI |
| **P0-5** | Emit `UNQUOTED` instead of a stale 0.00 % | **19/20** curated picks show `pnl_pct == 0`; **7** have `current_price == entry_price` exactly; **3,584/4,148** raw rows have null `current_price` | S/M (4 h) | Low/Med | dashboard_generator |
| **P0-6** | Populate `sym_track_*` from the closed ledger, not the active slice | Track empty on **18/20**; `sym_track_total` is 0 on **20/20** | S (1 h) | Low | dashboard_generator |
| **P0-7** | Sidecar freshness manifest + hide-if-stale | **10+ sidecars 79–245 d old** (`operator_review_today` 79.2 d, `strong_signals` 213 d, AI `top_picks*` ~245 d) | M (6 h) | Low | dashboard + deploy |
| **P0-8** | Dedup key + prune + CI assertion | **4,148 rows / 3,851 unique IDs**; **3,377 EXPIRED** in `active_raw`; **22,947 ghost rows** | M (8 h) | Med | dashboard_generator + tools |

---

## P0-1 — Guard the forex direction bucket (`KeyError: 'LONG'`)

**Problem (audited):** 93 failed runs/24 h. Latest ALPHA run `43609547717` traceback ends at `alpha_engine/scanner.py:2942`:
`_forex_by_sym[s["symbol"]][sig_type].append(s)` → `KeyError: 'LONG'` (`raw/logs/43609547717.log:1040`; same in `raw/logs/43608586741.log:946`).

**Verified source:**
- `alpha_engine/scanner.py:2937` — `_forex_by_sym = _dd(lambda: {"BUY": [], "SELL": []})`
- `alpha_engine/scanner.py:2942` — `_forex_by_sym[s["symbol"]][sig_type].append(s)`
- `alpha_engine/production_scanner.py:2319` / `:2449` — upstream picks carry `current_price`, not `signal_type="BUY"`; FX rows can carry `signal_type="LONG"`/`"SHORT"`.

`defaultdict` only lazily creates **symbol** keys; the inner value is a plain dict with only `BUY`/`SELL`, so any `LONG`/`SHORT`/`SELL_SHORT` value raises.

**Concrete change (safe default, no behavior change for BUY/SELL):**

```python
# alpha_engine/scanner.py, replace lines 2937-2942
def _dir_bucket(raw) -> str:
    d = str(raw or "BUY").strip().upper()
    return {"LONG": "BUY", "SHORT": "SELL", "BUY": "BUY", "SELL": "SELL"}.get(d, "BUY")

_forex_by_sym = _dd(lambda: {"BUY": [], "SELL": [], "OTHER": []})
_non_forex = []
for s in signals:
    if s.get("category") == "forex":
        bucket = _dir_bucket(s.get("signal_type", "BUY"))
        _forex_by_sym[s["symbol"]][bucket].append(s)   # never raises
    else:
        _non_forex.append(s)
```

Then in the conflict loop, treat `"OTHER"` as "skip pair, log once" (or fold into the majority only if > 70 %). This preserves the existing 70 % majority rule for BUY/SELL and prevents a single malformed emitter from killing the whole scan.

**Expected impact:** removes the dominant 24 h failure cluster (93 runs) and re-enables the two Alpha scanners that feed `picks.active_raw`.
**Risk:** if an FX signal legitimately means `LONG` and was previously silently dropped, it now participates in conflict resolution. Mitigation: log `[FX DIR] normalized LONG->BUY` at DEBUG; count `OTHER` and emit one warning per symbol.
**Rollback:** revert the 6-line block; no data migration.
**Validation:** see `acceptance_tests.md#at-p0-1`.

### P0-1b (same PR) — xgboost parity + Binance 451 backoff

**xgboost is guarded, not fatal — verify before "fixing" it:** `alpha_engine/ml_ranker.py:139-149` wraps `import xgboost` in `try/except ImportError` and falls back to LightGBM/RandomForest. The `No module named xgboost` line in the logs is therefore a *warning*, not the crash. Still, the two Alpha workflows differ:
- `.github/workflows/dynamic-alpha-engine.yml:150` installs `xgboost lightgbm pyarrow pytz`.
- `.github/workflows/alpha-engine-fast.yml:40` installs only `yfinance pandas numpy scikit-learn joblib requests`.

Add `xgboost lightgbm` to `.github/workflows/alpha-engine-fast.yml:40` so the fast and full scanners use the same ranker. Low risk because the import is already guarded.

**Binance HTTP 451:** failover already exists (`alpha_engine/production_scanner.py:2253-2293`, plus `alpha_engine/config.py:1238 BINANCE_FALLBACK_URLS`), and `audit_trail/dashboard_generator.py:1179` tries Binance → Binance Vision → Binance US. What is missing is **backoff/jitter** on repeated 451/403 during one run. Add:
```python
# alpha_engine/production_scanner.py, around the direct Binance loop (~:2280)
import time, random
def _get_with_backoff(session, url, attempts=3, base=0.5):
    for i in range(attempts):
        r = session.get(url, timeout=HTTP_TIMEOUT)
        if r.status_code not in (451, 403, 418, 429):
            return r
        time.sleep(base * (2 ** i) + random.uniform(0, 0.25))
    return r
```
and cache the last successful ticker snapshot in `alpha_engine/data/` for the process lifetime, so every emitter does not re-hit a geo-blocked endpoint. This is a same-day change; the fatal bug remains P0-1.

---

## P0-2 — `summary_picks.json` WR > 100 %: one population, clamp, assert

**Problem (audited):** `summary_picks.json` is 1.63 h fresh but arithmetically impossible. Re-derived from `raw/summary_picks.json`:

| Class | resolved | wins | losses | wins+losses | reported WR |
|---|---:|---:|---:|---:|---:|
| INDEX | 17 | 194 | 251 | 445 | **1,141.2 %** |
| FUTURES | 61 | 222 | 357 | 579 | **363.9 %** |
| COMMODITY | 1,447 | 3,476 | 3,466 | 6,942 | **240.2 %** |
| ETF | 73 | 170 | 183 | 353 | **232.9 %** |
| EQUITY | 820 | 1,332 | 2,148 | 3,480 | **162.4 %** |
| FOREX | 5,806 | 8,536 | 8,968 | 17,504 | **147.0 %** |
| BOND | 72 | 92 | 156 | 248 | **127.8 %** |
| CRYPTO | 10,444 | 10,262 | 13,746 | 24,008 | 98.3 % |

7 classes report WR > 100 %; 8 classes have `wins+losses > resolved`. CRYPTO is the tell: 24,008 outcome rows vs 10,444 resolved.

**Verified source:**
- `tools/sync_summary_picks_json.py:15` — `RESOLVED` set (includes `EXPIRED`, excludes `STOPPED`/`TARGET_HIT`).
- `tools/sync_summary_picks_json.py:63` — `resolved` counts `status IN ('WON','LOST','CLOSED','EXPIRED','TP_HIT','SL_HIT')`.
- `tools/sync_summary_picks_json.py:64` — `wins` counts `status='WON' OR pnl_pct>0` over **all** rows (open included).
- `tools/sync_summary_picks_json.py:65` — `losses` counts `status='LOST' OR pnl_pct<0` over **all** rows.
- `tools/sync_summary_picks_json.py:161` — `win_rate_pct = 100*wins/resolved`.
- Called from `.github/workflows/audit-dashboard.yml:627`.

**Concrete change — single terminal population; PnL sign is the outcome:**

```sql
-- tools/sync_summary_picks_json.py:59-71 (MySQL path)
SELECT category,
       COUNT(*) AS resolved,
       SUM(CASE WHEN pnl_pct IS NOT NULL AND pnl_pct > 0 THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN pnl_pct IS NOT NULL AND pnl_pct < 0 THEN 1 ELSE 0 END) AS losses,
       SUM(CASE WHEN pnl_pct IS NULL OR pnl_pct = 0 THEN 1 ELSE 0 END) AS flat,
       AVG(pnl_pct) AS avg_pnl_pct,
       MAX(COALESCE(created_at, updated_at)) AS last_pick
FROM trading_picks
WHERE category IS NOT NULL AND category != ''
  AND status IN ('WON','LOST','CLOSED','EXPIRED','TP_HIT','SL_HIT','STOPPED','TARGET_HIT')
GROUP BY category
```

Invariant: `wins + losses + flat == resolved`, so `wins <= resolved` always. Add a hard gate in `_format_payload`:

```python
# tools/sync_summary_picks_json.py:149-164
for ac in sorted(stats.keys()):
    s = stats[ac]
    resolved, wins, losses = s["resolved"], s["wins"], s["losses"]
    assert wins + losses <= resolved, f"{ac}: wins+losses {wins+losses} > resolved {resolved}"
    raw_wr = (100.0 * wins / resolved) if resolved else None
    wr = None if raw_wr is None else max(0.0, min(100.0, raw_wr))   # clamp
```

Also align the local-JSON path (`:128-142`) to the same rule: only count `wins`/`losses` when `st in RESOLVED` (currently `pnl is not None` also increments `resolved` for open rows).

**Expected impact:** removes 7 impossible rows from a published payload; name surfaces stop contradicting `pf_registry` (WR 42.21 %, PF 0.2657) and `money_ready_verdict` (0/9).
**Risk:** consumers that keyed on the inflated numbers will see a step change — which is the point. `summary_picks` is **not** in the trust hierarchy (`sub/E_statistical.md:§7.2`).
**Rollback:** the file is regenerated hourly from MySQL; revert the commit.
**Validation:** `acceptance_tests.md#at-p0-2`.

---

## P0-3 — Python 3.14 masquerade (`update-environment: false`)

**Problem (audited):** the pandas source-build cluster hits **8 enumerated workflows** in the 24 h failure table — Signal Tracking (11 fails), Forward Test (6), Live Trading Bot (6), Canada (6), Canada FREE (6), Autonomous (5), Crypto Dispatch (5), Self-Optimizing (5) — and the audit's root-cause note says “at least 9” (DNA fails separately on `OSError: Too many open files`). Log `raw/logs/43602685216.log:49` says `Run-time dependency python found: YES 3.14` even though the workflow pins `python-version: '3.11'`.

**Verified source:**
- `.github/workflows/signal_tracking.yml:35` — `update-environment: false`
- `.github/workflows/signal_tracking.yml:36` — `python-version: '3.11'`
- `requirements.txt:2` — `pandas==2.1.4` (no cp314 wheel; compiles from sdist)
- Same pattern in `.github/workflows/alpha-engine-fast.yml:35`, `.github/workflows/forward-test-new-strategies.yml:25`, `.github/workflows/autonomous_trading.yml:37`, `.github/workflows/copy-trader-intelligence.yml:30`.
- Repo-wide: **197** workflow files contain `update-environment: false` (`rg -l` count).

`actions/setup-python`'s `update-environment: false` suppresses the PATH/env mutation, so the job's `python`/`pip` resolve to the runner system interpreter (3.14). The pinned 3.11 is installed but never used.

**Concrete change (minimal, reversible):**
1. In the 8 failing cluster workflows, delete the `update-environment: false` line (or set `true`).
2. Keep `python-version: '3.11'`.
3. Add an explicit guard step before install:
   ```yaml
   - name: Assert interpreter
     run: python -c "import sys; assert sys.version_info[:2]==(3,11), sys.version"
   ```
4. Optional hardening: bump `pandas==2.1.4` → `pandas==2.2.3` in `requirements.txt:2` only after (1)–(3) pass.

Do **not** bulk-edit all 197 files in P0; fix the failing cluster, then migrate the rest under P1-3.

**Expected impact:** unblocks ~5 % of all 24 h failures and restores `signal_tracking`/forward-track/paper-bot freshness.
**Risk:** none to code; the risk is leaving some workflow on the old pattern. The guard step makes the failure loud instead of a 4-minute source build.
**Rollback:** re-add the line; `python -c` guard will then fail fast.
**Validation:** `acceptance_tests.md#at-p0-3`.

---

## P0-4 — Audit-dashboard runtime vs cron (cancellation cascade)

**Problem (audited):** `audit-dashboard.yml` has **61 cancelled / 168 runs in 7 d** and **10 cancelled / 24 runs in 24 h**; median successful job **84.5 min** (range 79.6–104.2) against an hourly cron. 9 of the 24 h cancels were **zero-job queued** runs in the `dashboard-publish` group.

**Verified source:**
- `.github/workflows/audit-dashboard.yml:5` — `- cron: '10 * * * *'`
- `.github/workflows/audit-dashboard.yml:41` — `group: dashboard-publish`
- `.github/workflows/audit-dashboard.yml:42` — `cancel-in-progress: false`
- `.github/workflows/audit-dashboard.yml:55` — job `timeout-minutes: 115`
- `.github/workflows/audit-dashboard.yml:129` — resolver step `timeout-minutes: 40`
- `.github/workflows/audit-dashboard.yml:493` — another step `timeout-minutes: 30`

With `cancel-in-progress: false`, runs queue; GitHub keeps only the newest pending run per group and cancels older queued ones. Hourly cron + 85 min runtime guarantees a standing queue.

**Concrete change (smallest correct fix first):**
1. Change cron to a period ≥ p95 runtime: `- cron: '10 */2 * * *'` (every 2 h). One-line, immediate.
2. Keep `cancel-in-progress: false` and `timeout-minutes: 115`.
3. Add a cheap preflight job that exits when the live payload is fresh, so manual/dispatch and quiet periods cost ~10 s:
   ```yaml
   - name: Skip if payload < 75 min old
     run: |
       python - <<'PY'
       import json,os,datetime as dt,urllib.request
       try:
           d=json.load(urllib.request.urlopen("https://findtorontoevents.ca/audit/data/dashboard_data.json",timeout=10))
           age=(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(d["generated_at"].replace("Z","+00:00"))).total_seconds()/60
           print("payload age min:",round(age,1))
           if age < 75: print("::notice::fresh — skipping build"); raise SystemExit(0)
       except SystemExit: raise
       except Exception as e: print("preflight unavailable:",e)
       PY
   ```
   (Place after checkout; guard the later build with `if: steps.preflight.outputs.skip != 'true'`.)
4. Do not raise `timeout-minutes` further — runtime is the problem, not the cap.

**Expected impact:** cancels drop toward zero, live payload age stabilises at ~2 h instead of the observed 1.4–1.6 h jitter, and runner-minute waste (61 × ~85 min) stops.
**Risk:** dashboard refresh cadence becomes 2 h. Documented current cadence is already ~1.5–2 h because of cancels. If 1 h is required, P1-4 profiles the 84.5 min.
**Rollback:** restore `'10 * * * *'`.
**Validation:** `acceptance_tests.md#at-p0-4`.

---

## P0-5 — `UNQUOTED` contract: never publish `0.00 %` for an unquoted row

**Problem (audited, re-derived from `raw/dashboard_payload.json`):**
- `picks.active` n=20: **19** have `pnl_pct == 0.0`; **7** have `current_price == entry_price` exactly; **19** are within `1e-4` relative. Only NEARUSDT is genuinely marked (2.74 %).
- `picks.active_raw` n=4,148: **3,584** have `current_price is None`; **3,832** have `pnl_pct == 0.0`; **202** have exact `current_price == entry_price`.
- A 0.00 % display is an arithmetic identity, not an observation.

**Verified source (generator):**
- `audit_trail/dashboard_generator.py:1618` `_enrich_live_pnl(...)`.
- `:1757-1763` — when no live quote is fetched, the code `continue`s and **keeps the inherited `pnl_pct`/`current_price`** (which is often `0.0` / `entry_price`).
- `:1798` / `:1822` — only writes `current_price` when a quote exists.
- `:1846` — function returns.
- `:14551` — only call site: `active = _enrich_live_pnl(active)`.
- `alpha_engine/production_scanner.py:2449-2456` — sets `entry_price = live_price` for informational non-crypto picks, producing exact `current == entry` at birth.

**Concrete change — provenance fields + build-time normalization (default ON):**

At the end of `_enrich_live_pnl` (before `return picks`, `:1846`):

```python
UNQUOTED = "UNQUOTED"
for p in picks:
    cp, ep = p.get("current_price"), p.get("entry_price")
    try:
        cp_f = float(cp) if cp is not None else None
        ep_f = float(ep) if ep is not None else None
    except (TypeError, ValueError):
        cp_f = ep_f = None
    quoted = (
        cp_f is not None and cp_f > 0
        and ep_f is not None and ep_f > 0
        and abs(cp_f - ep_f) > 1e-9
        and p.get("quote_source") not in (None, "", "NONE")
    )
    if not quoted:
        p["quote_status"] = UNQUOTED
        p["pnl_pct"] = None            # never a fabricated 0.00
        p["pnl_status"] = "UNQUOTED"
        p["quote_at"] = p.get("quote_at")   # may be None
        p["quote_source"] = p.get("quote_source") or "NONE"
    else:
        p["quote_status"] = "QUOTED"
        p["pnl_status"] = "UNREALIZED"
```

Also set `quote_at`/`quote_source` inside the two fetch helpers when a quote is accepted:
- `audit_trail/dashboard_generator.py:1179` `_fetch_prices_with_failover` → return `{sym: {"price","source","quote_at"}}` or a parallel `_quote_meta` dict (preferred: parallel dict to avoid touching every caller).
- `:1480` `_fetch_equity_prices` → same.
- Keep `pnl_pct` numeric for genuinely quoted rows; the template already renders `null` as `—`.

Template side (minimum honesty): `audit_dashboard/template.html:8889-8904` (the `pnl_pct` cell) — when `p.quote_status === 'UNQUOTED'`, render a grey `UNQUOTED` badge (tooltip: `No quote at build; PnL not measurable`) instead of letting `fmtPct(null)` collapse to `—`/`0 %`.

**Expected impact:** the Active Picks panel stops showing 19 fake `0.00 %` values; `money_ready`/`pf_registry` are unaffected (separate closed ledger). Consumers can filter `quote_status == 'QUOTED'` for mark-to-market stats.
**Risk:** downstream code that assumed `pnl_pct` is always a float may do `float(None)`. Mitigation: the template already handles null in several cells; grep `float(.*pnl_pct` before merge and add `or 0` only where display-only. Keep the flag `HONEST_QUOTE_CONTRACT=0` to disable normalization for one release.
**Rollback:** env flag off, or revert the block; `data/*.json` regenerates hourly.
**Validation:** `acceptance_tests.md#at-p0-5`.

---

## P0-6 — Populate `sym_track_*` from the closed ledger (Track column)

**Problem (audited):** Track is empty on **18/20** active picks; `sym_track_total` is **0 on 20/20**; repo-wide `sym_track_wr` is populated on only **2.7–3.6 %** of 691 OPEN rows (`sub/B_dashboard_freshness.md:§5`).

**Verified root cause:** `_enrich_live_pnl` builds symbol statistics from **the active list it is enriching**, filtered to closed statuses:

- `audit_trail/dashboard_generator.py:1830-1832`:
  ```python
  track_stats = _build_strategy_symbol_track_stats(
      [p for p in picks if str(p.get("status")).upper() in ("CLOSED","RESOLVED","WON","LOST","SL_HIT","TP_HIT")]
  )
  ```
- `audit_trail/dashboard_generator.py:14551` passes `active` only.
- `audit_trail/dashboard_generator.py:5661` documents the argument as `closed_picks`.

So the builder almost always receives `[]`. It is a correct function called with the wrong population.

**Concrete change:** pass the already-collected closed pool into `_enrich_live_pnl`:
```python
# :14551
active = _enrich_live_pnl(active, closed_history=closed)   # closed from :14548
# :1618
def _enrich_live_pnl(picks: list, closed_history: list | None = None) -> list:
    ...
    # :1830
    track_stats = _build_strategy_symbol_track_stats(closed_history or [])
```
`closed` is in scope at the call site (`:14548`), so this is a 2-line change.

**Expected impact:** Track becomes populated wherever the `(strategy,symbol)` pair exists in the 3,500-row closed feed; `sym_dir_fwd_*` remains the preferred source. Directly addresses "Edge/Track/FWD alive?" (Track 2/20 → expected materially higher, capped by pair coverage).
**Risk:** the closed pool includes 120-day-old rows. Mitigate by passing a 90-day window: `closed_history=[c for c in closed if _within_days(c, 90)]`, or accept all-time (the UI tooltips already label the source). No effect on PnL/gates.
**Rollback:** revert the signature change (default `None` keeps behavior).
**Validation:** `acceptance_tests.md#at-p0-6`.

---

## P0-7 — Sidecar freshness manifest + hide-if-stale

**Problem (audited):** the core payload is 1.63 h fresh, but 10+ sidecars are dead:

| Sidecar | Age | Verdict |
|---|---:|---|
| `hyro_pick_performance.json` | 157.9 h | STALE |
| `hyrotrader_picks.json` (`last_session_date`) | 5,296 h (220.7 d) | DEAD |
| `regime_report.json` | 3,896.9 h (162 d) | DEAD |
| `strategy_ic_analysis.json` | 4,060.4 h (169 d) | DEAD |
| `strong_signals.json` | 5,120.8 h (213 d) | DEAD |
| `stock_forex_prices.json` | 5,211.9 h (217 d) | DEAD |
| `pilot_forward_dashboard.json` | 3,877.6 h (161.6 d) | DEAD |
| `strategy_admissibility.json` | 3,877.6 h (161.6 d) | DEAD |
| `operator_review_today.json` | 1,901.7 h (79.2 d) | DEAD |
| `claude/grok/kimi/mercury/ag_top_picks*.json` | ~5,890 h (~245 d) | DEAD |

**Verified consumers (panels that still fetch them):**
- `audit_dashboard/dashboard_enhancements.js:115` — `fetch('data/operator_review_today.json', {cache:'no-cache'})` every load.
- `audit_dashboard/template.html:17656` — `fetch('data/claude_top_picks.json...')`.
- `audit_dashboard/template.html:17744` — `fetch('data/regime_report.json...')`.
- `audit_dashboard/template.html:1329` — `fetch('./data/strategy_ic_analysis.json...')`.
- `audit_dashboard/template.html:17763-17765` — `strong_signals.json` chain.
- Existing pattern to reuse: `tools/assert_model_freshness.py:1-50` (tracked artifacts + thresholds + CI exit codes).

**Concrete change:**
1. Emit `audit_dashboard/data/sidecar_freshness_manifest.json` from the generator/deploy step:
   ```json
   {"generated_at":"...","max_age_hours":24,
    "sidecars":{"regime_report.json":{"ts":"2026-06-05T07:15Z","age_hours":3896.9,"status":"STALE"},
                "strong_signals.json":{"status":"STALE"}, "...":{"status":"FRESH"}}}
   ```
   Source of truth: each file's internal timestamp field (`generated_at`/`updated_at`/`timestamp`/`last_session_date`), fallback file mtime.
2. Client gate: a tiny `loadSidecarIfFresh(url, panelId, maxAgeHours)` helper wraps the existing fetch sites; when stale, render
   `Panel hidden — last updated <date> (<N> d). <toggle>` instead of stale numbers. Default hidden for `> 24 h`, configurable per sidecar (e.g. 168 h for weekly).
3. CI: extend `tools/assert_model_freshness.py` (or new `tools/assert_sidecar_freshness.py`) with the same list and `--warn-only` for release week, then hard-fail. Wire into `.github/workflows/audit-dashboard.yml` after the generator (near `:627`).

**Expected impact:** no re-used 79–245-day numbers on the dashboard; real failures become visible in CI instead of silently stale panels.
**Risk:** hiding a panel could look like a regression. Mitigate: banner explicitly says "stale, hidden", plus the manifest is downloadable.
**Rollback:** set `HIDE_STALE_SIDECARS=0` (client) / remove the CI step.
**Validation:** `acceptance_tests.md#at-p0-7`.

---

## P0-8 — Dedup key, prune job, CI assertion

**Problem (audited, re-derived):**
- `picks.active_raw`: **4,148 rows / 3,851 unique IDs** → 297 extra rows across **248** duplicated IDs.
- Same `(symbol, strategy, direction)`: **381** duplicated groups carrying **3,213** extra rows (e.g. max-group re-emissions).
- **3,377 `EXPIRED`** rows still counted as inventory (`status` split: EXPIRED 3,377 · OPEN 691 · SL_HIT 55 · TP_HIT 25).
- `db_health.ghost_rows`: **22,947** rows in **10** constant-PnL cohorts; top `DOGEUSDT LONG pnl 1.3226 n=3,569 distinct_entries=1` (`raw/db_health.json`, `tools/db_health_check.py:172-240`).
- **56** IDs appear in both `active_raw` and `recent_closed`.

**Verified existing key (use it, don't invent a second one):**
- `tools/build_pf_registry.py:818-835` — `(strategy, normalized symbol, direction, trade_date, round(entry_price, ENTRY_PRICE_ROUND))`.
- `tools/db_health_check.py:172` `check_ghost_rows()` and SQL at `:196-207` (`HAVING COUNT(*) > 1000 AND COUNT(DISTINCT entry_price) < 5`).

**Concrete change:**
1. Add `_pick_dedup_key(p)` to `audit_trail/dashboard_generator.py` mirroring the registry key, with `trade_date = date(first of entry_at/signal_at/created_at)`.
2. In `collect_all_picks()` (call site `:14548`, raw capture `:9538`), dedup `active_raw_snapshot` **before** it is assigned at `:17481`; keep the newest by `timestamp`, tie-break on `score`.
3. Prune: do not carry `EXPIRED` rows with `pnl_pct in (None, 0)` and `age > 30 d` into `active_raw`; write them to `audit_dashboard/data/expired_archive/YYYY-MM.jsonl` (append-only, auditable) and count them in `summary.pruned_expired`.
4. CI assertion (new test): `unique(ids) == len(rows)` for `active_raw`; `EXPIRED` share ≤ 5 %; no `(symbol,strategy,direction)` group with > 5 identical-pnl rows. Reuse the ghost-cohort query as a gate in `tools/db_health_check.py`.

**Expected impact:** `active_raw` 4,148 → ~3,851 IDs (→ ~691 OPEN after prune); ghost cohort count becomes a hard CI signal; `db_health.total_ghost_rows` stops being a dashboard decoration.
**Risk:** aggressive pruning could hide genuinely re-emitted picks. Mitigation: archive JSONL + keep raw count in `summary.raw_preprune_count`; dedup is ID-key first, so distinct trades with distinct IDs are preserved.
**Rollback:** archive files + revert the dedup call; data regenerates hourly.
**Validation:** `acceptance_tests.md#at-p0-8`.

---

## P0-9 (security, 0.5 day) — remove tracked API keys, add ignore rules

**Finding (paths only — values intentionally not reproduced):**
- Tracked files contain hardcoded Google API keys: `STOCKSUNIFY/scripts/lib/stock-api-keys.ts`, `STOCKSUNIFY/STOCKSUNIFY2/scripts/lib/stock-api-keys.ts`, `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS2/scroll-fix.js`.
- `dbpasses.txt` is **not** present in this worktree and **not** tracked, but also **not** listed in `.gitignore` (verified `git check-ignore` → not ignored). `~/dbpasses.txt` exists outside the repo.
- No `print`/`log` of DB passwords was found in `tools/`, `alpha_engine/`, `audit_trail/`, `copy_trader_intel/`; secret access is env-based (e.g. `tools/ai_tournament/*.py` read `DB_PASS_STOCKS`/`MYSQL_PASSWORD`).
- `.github/workflows/pead-shadow-collector.yml:93` already sanitizes the push token in output (`sed "s|${TOKEN_FOR_PUSH}|***|g"`).

**Concrete change:** move the three hardcoded values to env/secret, rotate them, add `dbpasses.txt` + `*dbpasses*` to `.gitignore`, and add a CI `secret-scan` job (the repo already has `.github/workflows/db-password-leak-guard.yml:63` as a pattern).
**Risk:** rotation invalidates live consumers — coordinate.
**Validation:** `acceptance_tests.md#at-p0-9`.

---

## Sequencing recommendation

Do P0-1 → P0-4 first (CI unblock + scheduler; no data consumers), then P0-2/P0-6 (one generator run), then P0-5/P0-7/P0-8 (payload contract), then P0-9 with the operator.

Estimated total: ~3.5 engineer-days; P0-1..P0-4 are ~half a day combined.
