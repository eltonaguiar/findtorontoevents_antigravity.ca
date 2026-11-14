# Acceptance tests — must pass after each fix

Conventions:
- Run from the repo root (`finpredict-v2`), Python 3.11.
- Tests marked **[NEW]** do not exist yet; add them at the path shown.
- Every fix has (a) a deterministic unit/contract test and (b) a live-artifact smoke check.
- CI already runs pytest from `.github/workflows/ci-tests.yml:203` (`python -m pytest tests/ paper_trading/tests/ alpha_engine/tests/ tools/tests/`), so **[NEW]** tests land in `tests/` and are picked up automatically.
- For live checks, use the archived fixtures in `../raw/` first; the network commands are optional verification.

---

## AT-P0-1 — forex direction bucket

**[NEW]** `tests/test_scanner_forex_direction_bucket.py`

```python
from alpha_engine.scanner import rank_and_filter_signals  # adjust import if the
# function is re-exported elsewhere; verified definition at scanner.py:2860-ish

def _sig(symbol, signal_type, category="forex"):
    return {"symbol": symbol, "signal_type": signal_type, "category": category,
            "entry_price": 1.0, "take_profit": 1.1, "stop_loss": 0.9,
            "confidence": 0.6, "strategy": "t"}

def test_long_short_do_not_raise(monkeypatch):
    # Regression for KeyError: 'LONG' at scanner.py:2942
    sigs = [_sig("EURUSD=X", "LONG"), _sig("EURUSD=X", "SHORT")]
    # Pass an empty ranker/db/market_data; the conflict-resolution block runs first.
    out = rank_and_filter_signals(sigs, ranker=None, db=None, market_data={})
    assert isinstance(out, list)

def test_mixed_case_and_alias():
    sigs = [_sig("GBPUSD=X", "long"), _sig("GBPUSD=X", "buy"),
            _sig("GBPUSD=X", "SELL")]
    assert isinstance(rank_and_filter_signals(sigs, None, None, {}), list)
```

**Exact command:**
```bash
python -m pytest tests/test_scanner_forex_direction_bucket.py -q
```

**Smoke (replay the archived production signals if available):**
```bash
# If a signals fixture exists, feed it; otherwise re-run the scanner is NOT required.
python - <<'PY'
import json, pathlib
p = pathlib.Path("2026-11-14/finpredict-v2_20261114-1602/raw/representative_picks.json")
if p.exists():
    picks = json.loads(p.read_text())
    print("fixture picks:", len(picks), "types:", {str(x.get("signal_type")) for x in picks})
PY
```

**Pass criteria:** pytest exit 0; workflow log for the next ALPHA/FAST run has no `KeyError: 'LONG'`.

---

## AT-P0-2 — summary_picks population invariant

**[NEW]** `tests/test_summary_picks_population.py`

```python
import importlib.util, json, pathlib

SPEC = importlib.util.spec_from_file_location(
    "sync_summary", pathlib.Path("tools/sync_summary_picks_json.py"))
sync_summary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync_summary)

def test_format_payload_rejects_overlapping_populations():
    stats = {"CRYPTO": {"total_picks": 100, "resolved": 10, "wins": 12,
                        "losses": 3, "pnl_sum": 0.0, "pnl_n": 0, "last_pick": ""}}
    try:
        sync_summary._format_payload(stats, source="test")
    except AssertionError:
        return
    raise SystemExit("expected AssertionError for wins+losses > resolved")

def test_win_rate_is_clamped_and_consistent():
    stats = {"ETF": {"total_picks": 50, "resolved": 20, "wins": 11,
                     "losses": 4, "pnl_sum": 0.0, "pnl_n": 0, "last_pick": ""}}
    out = sync_summary._format_payload(stats, source="test")
    row = out["asset_classes"][0]
    assert row["wins"] + row["losses"] <= row["resolved"]
    assert 0.0 <= row["win_rate_pct"] <= 100.0

def test_archived_snapshot_has_no_impossible_rows():
    p = pathlib.Path("2026-11-14/finpredict-v2_20261114-1602/raw/summary_picks.json")
    if not p.exists():
        return  # archived evidence not present in this checkout
    for c in json.loads(p.read_text())["asset_classes"]:
        if c["win_rate_pct"] is None:
            continue
        assert c["wins"] + c["losses"] <= c["resolved"], c["asset_class"]
        assert c["win_rate_pct"] <= 100.0, c["asset_class"]
```

> Note: the archived snapshot is the **pre-fix** payload, so the last test is expected to fail until the live file is regenerated; run it against the regenerated `audit_dashboard/data/summary_picks.json` instead:
```bash
python - <<'PY'
import json
d=json.load(open("audit_dashboard/data/summary_picks.json"))
bad=[c for c in d["asset_classes"]
     if c["win_rate_pct"] is not None and
     (c["wins"]+c["losses"]>c["resolved"] or c["win_rate_pct"]>100)]
print("bad classes:", [(c["asset_class"],c["win_rate_pct"]) for c in bad])
assert not bad, bad
PY
```

**Exact command:**
```bash
python -m pytest tests/test_summary_picks_population.py -q
python - <<'PY'
import json
d=json.load(open("audit_dashboard/data/summary_picks.json"))
bad=[c for c in d["asset_classes"] if c["win_rate_pct"] is not None and (c["wins"]+c["losses"]>c["resolved"] or c["win_rate_pct"]>100)]
assert not bad, bad
print("summary_picks OK:", d["n_asset_classes"], "classes")
PY
```

**Pass criteria:** no class with WR > 100 %; `wins+losses <= resolved` for all.

---

## AT-P0-3 — interpreter assertion

**[NEW]** `tests/test_workflow_python_env.py`

```python
import pathlib, re, yaml

CLUSTER = [
    ".github/workflows/signal_tracking.yml",
    ".github/workflows/forward-test-new-strategies.yml",
    ".github/workflows/autonomous_trading.yml",
    ".github/workflows/copy-trader-intelligence.yml",
    ".github/workflows/alpha-engine-fast.yml",
]

def test_no_update_environment_false_in_cluster():
    for f in CLUSTER:
        text = pathlib.Path(f).read_text()
        assert "update-environment: false" not in text, f

def test_cluster_pins_python_311():
    for f in CLUSTER:
        wf = yaml.safe_load(pathlib.Path(f).read_text())
        steps = wf["jobs"][next(iter(wf["jobs"]))]["steps"]
        setups = [s for s in steps if str(s.get("uses","")).startswith("actions/setup-python")]
        assert setups, f
        assert setups[0]["with"]["python-version"] == "3.11", f
```

**Exact command:**
```bash
python -m pytest tests/test_workflow_python_env.py -q
# and prove the interpreter at runtime in CI (add this step before install):
python -c "import sys; assert sys.version_info[:2]==(3,11), sys.version; print(sys.version)"
```

**Pass criteria:** pytest exit 0; the next Signal Tracking/Forward-Test/Live-Bot run logs `Python 3.11.x`, not `python found: YES 3.14`.

---

## AT-P0-4 — scheduler concurrency

**[NEW]** `tests/test_audit_dashboard_schedule.py`

```python
import yaml, pathlib

def test_cron_period_ge_runtime():
    wf = yaml.safe_load(pathlib.Path(".github/workflows/audit-dashboard.yml").read_text())
    # PyYAML parses the key `on` as True; read the raw text for the cron line.
    text = pathlib.Path(".github/workflows/audit-dashboard.yml").read_text()
    assert "cron: '10 */2 * * *'" in text, "cron must be every 2h after P0-4"

def test_concurrency_and_timeout_present():
    text = pathlib.Path(".github/workflows/audit-dashboard.yml").read_text()
    assert "group: dashboard-publish" in text
    assert "cancel-in-progress: false" in text
    assert "timeout-minutes: 115" in text
```

**Live cancellation rate check (GitHub API, requires `gh` auth):**
```bash
gh api "repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows/audit-dashboard.yml/runs?created=%3E%3D$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)&per_page=100" \
  --jq '[.workflow_runs[]|.conclusion]|group_by(.)|map({(.[0]):length})|add'
```
**Pass criteria:** cancelled count ≤ 5 % of runs over the next 7 days; no zero-job queued cancels.

---

## AT-P0-5 — UNQUOTED contract

**[NEW]** `tests/test_quote_contract.py`

```python
import importlib, pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd()))
from audit_trail import dashboard_generator as dg

def _pick(**kw):
    base = {"symbol":"BTCUSDT","entry_price":100.0,"current_price":100.0,
            "pnl_pct":0.0,"status":"OPEN","strategy":"s","direction":"LONG"}
    base.update(kw); return base

def test_unquoted_when_current_equals_entry():
    p = _pick()
    dg._enrich_live_pnl([p])          # no network in unit env → no quote
    assert p.get("quote_status") == "UNQUOTED"
    assert p["pnl_pct"] is None

def test_unquoted_when_price_missing():
    p = _pick(current_price=None, pnl_pct=None)
    dg._enrich_live_pnl([p])
    assert p.get("quote_status") == "UNQUOTED"
    assert p["pnl_pct"] is None

def test_quoted_keeps_numeric_pnl():
    p = _pick(current_price=101.0, pnl_pct=1.0)
    p["quote_source"] = "BINANCE"; p["quote_at"] = "2026-11-14T16:00:00Z"
    dg._enrich_live_pnl([p])
    assert p.get("quote_status") == "QUOTED"
    assert isinstance(p["pnl_pct"], (int,float))
```

**Live payload check:**
```bash
python - <<'PY'
import json
d=json.load(open("audit_dashboard/data/dashboard_data.json"))
a=d["picks"]["active"]
bad=[]
for p in a:
    cp,ep,pnl=p.get("current_price"),p.get("entry_price"),p.get("pnl_pct")
    if cp is not None and ep not in (None,0) and abs(float(cp)-float(ep))<1e-9 and pnl==0.0:
        bad.append((p.get("symbol"),pnl,p.get("quote_status")))
print("frozen-at-entry with pnl 0:", bad)
assert not bad, bad
PY
```
**Pass criteria:** no row with `current_price == entry_price` and `pnl_pct == 0.0`; every active row has `quote_status` in `{QUOTED, UNQUOTED}`.

---

## AT-P0-6 — sym_track population

**[NEW]** `tests/test_sym_track_population.py`

```python
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd()))
from audit_trail import dashboard_generator as dg

def test_track_stats_use_closed_history():
    closed = [{"strategy":"s1","symbol":"AAAUSDT","status":"WON","pnl_pct":2.0,"exit_reason":"TP_HIT"},
              {"strategy":"s1","symbol":"AAAUSDT","status":"LOST","pnl_pct":-1.0,"exit_reason":"SL_HIT"}]
    active = [{"strategy":"s1","symbol":"AAAUSDT","status":"OPEN","entry_price":1.0,
               "current_price":1.01,"pnl_pct":1.0}]
    out = dg._enrich_live_pnl(active, closed_history=closed)
    assert out[0].get("sym_track_total") == 2
    assert out[0].get("sym_track_wr") == 50.0
```

**Live check:**
```bash
python - <<'PY'
import json
d=json.load(open("audit_dashboard/data/dashboard_data.json"))
a=d["picks"]["active"]
n=sum(1 for p in a if (p.get("sym_track_total") or 0)>0)
print(f"sym_track_total>0: {n}/{len(a)}")
assert n >= 1, "Track still structurally empty"
PY
```
**Pass criteria:** unit test passes; on live data, at least one active pick has `sym_track_total > 0` (exact coverage depends on `(strategy,symbol)` presence in closed history).

---

## AT-P0-7 — sidecar freshness manifest

**[NEW]** `tests/test_sidecar_freshness_manifest.py`

```python
import json, pathlib, datetime as dt

MAX_H = 24

def _age_hours(ts):
    if not ts: return None
    t = dt.datetime.fromisoformat(str(ts).replace("Z","+00:00"))
    if t.tzinfo is None: t = t.replace(tzinfo=dt.timezone.utc)
    return (dt.datetime.now(dt.timezone.utc)-t).total_seconds()/3600

def test_manifest_exists_and_covers_known_sidecars():
    p = pathlib.Path("audit_dashboard/data/sidecar_freshness_manifest.json")
    assert p.exists(), "manifest not generated"
    m = json.loads(p.read_text())
    for name in ("regime_report.json","strong_signals.json","operator_review_today.json",
                 "pilot_forward_dashboard.json","strategy_admissibility.json"):
        assert name in m["sidecars"], name

def test_stale_panels_are_marked():
    m = json.loads(pathlib.Path("audit_dashboard/data/sidecar_freshness_manifest.json").read_text())
    for name, s in m["sidecars"].items():
        if s.get("age_hours") is None: continue
        expected = "STALE" if s["age_hours"] > m.get("max_age_hours", MAX_H) else "FRESH"
        assert s["status"] == expected, (name, s)
```

**Exact command:**
```bash
python -m pytest tests/test_sidecar_freshness_manifest.py -q
# CI gate (fails on any sidecar older than its declared max_age_hours):
python tools/assert_sidecar_freshness.py --max-age-hours 24
```
**Pass criteria:** every sidecar listed with `status`; no "FRESH" label on a >24 h file; UI hides stale panels (manual check of `/audit/`).

---

## AT-P0-8 — dedup/prune

**[NEW]** `tests/test_active_raw_dedup.py`

```python
import json, pathlib
from collections import Counter

def test_active_raw_ids_unique():
    d = json.load(open("audit_dashboard/data/dashboard_data.json"))
    rows = d["picks"].get("active_raw", [])
    ids = [r.get("id") for r in rows if r.get("id")]
    dup = {k:v for k,v in Counter(ids).items() if v>1}
    assert not dup, f"{len(dup)} duplicated ids, {sum(v-1 for v in dup.values())} extra rows"

def test_expired_share_bounded():
    d = json.load(open("audit_dashboard/data/dashboard_data.json"))
    rows = d["picks"].get("active_raw", [])
    if not rows: return
    expired = sum(1 for r in rows if str(r.get("status","")).upper()=="EXPIRED")
    assert expired/len(rows) <= 0.05, f"{expired}/{len(rows)} EXPIRED"

def test_no_cross_surface_id_collisions():
    d = json.load(open("audit_dashboard/data/dashboard_data.json"))
    a = {r.get("id") for r in d["picks"].get("active_raw", []) if r.get("id")}
    c = {r.get("id") for r in d["picks"].get("recent_closed", []) if r.get("id")}
    assert not (a & c), f"{len(a & c)} ids in both surfaces"
```

**Exact command:**
```bash
python -m pytest tests/test_active_raw_dedup.py -q
# DB ghost cohort assertion (requires DB_PASS_STOCKS):
python - <<'PY'
import json, subprocess, sys
out = subprocess.check_output([sys.executable, "tools/db_health_check.py"], text=True)
d = json.loads(out)
ghost = d["checks"]["ghost_rows"]["data"]["total_ghost_rows"]
print("ghost rows:", ghost)
assert ghost < 1000, ghost
PY
```
**Pass criteria:** IDs unique; EXPIRED ≤ 5 %; cross-surface collisions 0; ghost cohorts < 1,000 (green tier in `tools/db_health_check.py:238`).

---

## AT-P0-9 — secret hygiene

**Commands (no secret values printed):**
```bash
git grep -nE "AIza[0-9A-Za-z_-]{20,}" -- . || true       # expect no matches after rotation
git check-ignore -v dbpasses.txt                          # expect a match after .gitignore update
# repo already ships a leak guard; run it:
bash -lc 'test -f .github/workflows/db-password-leak-guard.yml && echo leak-guard-present'
```
**Pass criteria:** no high-entropy Google key literals tracked; `dbpasses.txt` ignored; leak-guard workflow present.

---

## AT-P1-1 — data contract

```bash
python -m pytest tests/test_pick_schema.py -q          # [NEW] validates every active_raw/closed row
python - <<'PY'
import json, jsonschema, pathlib
schema = json.loads(pathlib.Path("audit_dashboard/data/schemas/pick.schema.json").read_text())
for f in ("audit_dashboard/data/dashboard_data.json",):
    d = json.load(open(f))
    for pop in ("active","active_raw","recent_closed"):
        for row in d["picks"].get(pop, []):
            jsonschema.validate(row, schema)
print("schema OK")
PY
```
**Pass:** every published pick validates; `schema_version` present in each payload.

---

## AT-P1-2 — open backlog

```bash
python tools/db_freshness_check.py --json | python -c "
import sys,json; d=json.load(sys.stdin)
o=d['checks']['open_bloat'] if 'checks' in d else d
print(o); assert (o['open_count']/o['total_count'])<=0.40, o
"
```
**Pass:** `open_count/total_count ≤ 0.40` and falling for 7 consecutive days; `hours_since_last_close < 6`.

---

## AT-P1-3 — workflow hygiene lint

```bash
python tools/lint_workflows.py --fail-on update-environment-false,missing-concurrency,missing-timeout
rg -l "update-environment: false" .github/workflows/ | wc -l   # target: 0
```
**Pass:** lint exit 0; no `ModuleNotFoundError: No module named 'tools'` in the next 24 h.

---

## AT-P1-4 — runtime profile

```bash
gh run view <run_id> --repo eltonaguiar/findtorontoevents_antigravity.ca --json jobs \
  --jq '.jobs[] | {name, started_at, completed_at}'
python tools/assert_dashboard_runtime.py --p95-max-min 45
```
**Pass:** p95 job duration ≤ 45 min over 7 days; hourly cron restored.

---

## AT-P1-5 — push contention

```bash
rg -n "git push" .github/workflows/ .github/scripts/ | grep -v safe_push.sh   # target: only approvals
gh api "repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/runs?created=%3E%3D$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)&per_page=100" \
  --jq '[.workflow_runs[]|select(.conclusion=="failure")|.name]|unique'
```
**Pass:** no `All N push attempts failed` in 24 h; failure names do not include Live Spike / H-002 PEAD.

---

## AT-P1-6 — honest statistics

```bash
python -m pytest tests/test_multiple_testing.py -q
python - <<'PY'
import json
a=json.load(open("audit_dashboard/data/anti_overfit_audit.json"))
pbo=a["portfolio_diagnostics"]["pbo"]
assert pbo.get("n_observations",0) >= 4*pbo.get("n_folds",5), pbo
assert pbo.get("value") != 0.0 or pbo.get("verdict")=="INSUFFICIENT_T", pbo
rc=a["portfolio_diagnostics"].get("reality_check",{})
assert "error" not in rc, rc
PY
```
**Pass:** PBO not computed on T=20; DSR `n_trials ≥ 600`; Reality Check has a p-value; `single_source_pct >= 0.95` rows excluded from "significant winners".

---

## AT-P1-7 — sidecar lifecycle

```bash
python tools/sidecar_lifecycle.py --check
python -c "import json;m=json.load(open('audit_dashboard/data/sidecar_freshness_manifest.json'));print([k for k,v in m['sidecars'].items() if v['status']=='STALE'])"
```
**Pass:** every STALE entry has an owner + `on_stale` policy; no 404 sidecar referenced by HTML (grep for `strategy_tribunal_latest` yields 0 live references).

---

## AT-P1-8 — source authenticity

```bash
curl -s -o /dev/null -w "%{http_code}\n" "https://data-api.polymarket.com/v2/leaderboard?limit=1"   # expect 200
curl -s -o /dev/null -w "%{http_code}\n" "https://data-api.polymarket.com/v1/leaderboard?limit=1"   # expect 410 (deprecated)
python -m pytest tests/test_source_authenticity.py -q     # [NEW] no live system marked dead while producing
```
**Pass:** v2 used; no HTTP 410 in CI logs; `copy_trader_intel` not `status=dead`; consensus excludes `resolved_n < 30`.

---

## AT-P1-9 — JSON strictness

```bash
python - <<'PY'
import json, glob
bad=[]
for f in glob.glob("audit_dashboard/data/*.json"):
    t=open(f, "rb").read()
    if b"NaN" in t or b"Infinity" in t: bad.append(f)
    try: json.loads(t)
    except Exception as e: bad.append((f,str(e)))
print("non-standard JSON:", bad)
assert not bad, bad
PY
```
**Pass:** zero `NaN`/`Infinity`; all payloads parse with strict `json.loads`.

---

## One-shot pre-merge gate (paste into CI)

```bash
set -e
python -m pytest tests/test_scanner_forex_direction_bucket.py \
                 tests/test_summary_picks_population.py \
                 tests/test_workflow_python_env.py \
                 tests/test_audit_dashboard_schedule.py \
                 tests/test_quote_contract.py \
                 tests/test_sym_track_population.py \
                 tests/test_sidecar_freshness_manifest.py \
                 tests/test_active_raw_dedup.py -q
python tools/assert_sidecar_freshness.py --max-age-hours 24
python - <<'PY'
import json
d=json.load(open("audit_dashboard/data/summary_picks.json"))
assert all(c["win_rate_pct"] is None or c["win_rate_pct"]<=100 for c in d["asset_classes"])
d=json.load(open("audit_dashboard/data/dashboard_data.json"))
assert not [p for p in d["picks"]["active"]
            if p.get("current_price") not in (None,0) and p.get("entry_price")
            and abs(float(p["current_price"])-float(p["entry_price"]))<1e-9
            and p.get("pnl_pct")==0.0]
print("cross-cutting gate OK")
PY
```
