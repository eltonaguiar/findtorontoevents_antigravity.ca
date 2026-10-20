# /audit Cohort Reconciliation Instrument Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pure, unit-tested module that reads the published /audit JSONs and writes `audit_dashboard/data/cohort_reconciliation.json` recomputing rolling PF/WR over matched windows and flagging blocklist-bypass, batch-artefact closes, and published-file disagreement.

**Architecture:** A single dependency-free module `tools/cohort_reconciliation.py` with pure functions (load, recompute metrics, coverage, three flags, assemble) plus a thin `main()` CLI. Tests live in `tests/test_cohort_reconciliation.py` with hand-made fixtures. No live DB reads, no dashboard wiring, no trade triggers.

**Tech Stack:** Python 3 stdlib (`json`, `argparse`, `datetime`, `collections`); `pytest` for tests; imports blocklist via `alpha_engine/strategy_blocklist.py`.

**Spec:** `docs/superpowers/specs/2026-10-20-audit-cohort-reconciliation-design.md`

---

## Data/API facts (verified 2026-10-20)

- `audit_dashboard/data/dashboard_data.json` top-level has `generated_at` (ISO with `+00:00`) and `picks.recent_closed` (3,500 records). Each record has `strategy`, `source_system`, `asset_class`, `pnl_pct`, `closed_at`, `entry_time`. `closed_at` range observed 2026-02-21 → 2026-10-19 (covers 14d).
- `audit_dashboard/data/pick_summary_stats_14d.json` / `_48h.json` have `window_hours` (336 / 48), `generated_at`, and `by_class` keyed by class (`CRYPTO`, `EQUITY`, `FUTURES`, `FOREX`, `ETF`, `BOND`, `UNKNOWN`). Each class dict has `n_closed`, `wins`, `losses`, `wr_pct`, `pf`. (Both currently stale: generated 2026-06-21.)
- `alpha_engine/strategy_blocklist.py` exports `is_blocked_strategy(name, asset_class="")`, `block_reason(name, asset_class="")` (returns `retired`/`paper-only`/`fx-kill`/`commodity-inverse-kill`/`""`). No block-date API exists → issue-time unknown.
- PF formula (matches report): `PF = Σ pos pnl_pct / |Σ neg pnl_pct|`.

## File map

| File | Responsibility |
|------|----------------|
| `tools/cohort_reconciliation.py` (create) | Pure functions + `main()` CLI. |
| `tests/test_cohort_reconciliation.py` (create) | Fixtures + unit tests per task. |

---

### Task 1: Module skeleton + `load_json` + `parse_ts` + sys.path bootstrap

**Files:**
- Create: `tools/cohort_reconciliation.py`
- Test: `tests/test_cohort_reconciliation.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cohort_reconciliation.py
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.cohort_reconciliation import load_json, parse_ts


def _write_tmp(tmp_path, data):
    p = tmp_path / "f.json"
    p.write_text(json.dumps(data))
    return str(p)


def test_load_json_reads_valid(tmp_path):
    p = _write_tmp(tmp_path, {"a": 1})
    assert load_json(p) == {"a": 1}


def test_load_json_returns_none_when_missing(tmp_path):
    assert load_json(str(tmp_path / "nope.json")) is None


def test_load_json_raises_on_malformed(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    try:
        load_json(str(p))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_parse_ts_normalizes_z_and_microseconds():
    dt = parse_ts("2026-10-19T19:32:56.089767Z")
    assert dt.isoformat().startswith("2026-10-19T19:32:56")
    assert dt.tzinfo is not None
    dt2 = parse_ts("2026-06-21T06:31:08+00:00")
    assert dt2.tzinfo is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_cohort_reconciliation.py -v`
Expected: FAIL with `ModuleNotFoundError` / `ImportError: cannot import name 'load_json'`.

- [ ] **Step 3: Write minimal implementation**

```python
# tools/cohort_reconciliation.py
"""Pure cohort reconciliation for /audit published JSONs (measurement only).

Reads only published files; never touches the live DB.
No trade triggers. Output contains no READY/ENTER wording.
"""
import sys
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCHEMA_VERSION = "1.1.0"


def utcnow_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_ts(ts):
    """Parse an ISO timestamp; tolerate trailing 'Z' and microseconds."""
    if ts is None:
        raise ValueError("parse_ts(None)")
    s = str(ts).strip()
    if s.endswith("Z") or s.endswith("z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def load_json(path):
    """Load JSON. Return None if missing; raise ValueError if malformed."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"malformed JSON in {path}: {e}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_cohort_reconciliation.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/cohort_reconciliation.py tests/test_cohort_reconciliation.py
git commit -m "feat: cohort reconciliation skeleton + load_json/parse_ts"
```

---

### Task 2: `_pf`, `metric_block`, `recompute_rolling_metrics` + coverage

**Files:**
- Modify: `tools/cohort_reconciliation.py` (append functions)
- Test: `tests/test_cohort_reconciliation.py` (append)

**Contract:**

- `_pf(rows) -> float|None|'inf'` — `Σpos / |Σneg|`; `None` when no trades; `'inf'` when no losses but wins exist.
- `metric_block(rows) -> dict` — `{n, wins, losses, win_rate, win_rate_hidden, pf}`; hide `win_rate` (set `None`, `win_rate_hidden=True`) when `n < 20`.
- `recompute_rolling_metrics(records, window_hours, generated_at) -> dict` — filter records to the window (`closed_at >= generated_at - window_hours`); compute `coverage` (status `complete` if oldest `closed_at` ≤ window start else `incomplete_coverage`), `by_class`, `by_strategy`.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_cohort_reconciliation.py
from tools.cohort_reconciliation import _pf, metric_block, recompute_rolling_metrics


def _rec(pnl, closed_at, strategy="s1", asset_class="EQUITY"):
    return {"strategy": strategy, "asset_class": asset_class,
            "pnl_pct": pnl, "closed_at": closed_at,
            "source_system": "alpha_engine", "id": "x"}


def test_pf_basic():
    rows = [_rec(2.0, "2026-10-19T00:00:00Z"), _rec(-1.0, "2026-10-19T00:00:00Z")]
    assert _pf(rows) == 2.0


def test_pf_no_losses_is_inf():
    assert _pf([_rec(1.0, "2026-10-19T00:00:00Z")]) == "inf"


def test_pf_empty_is_none():
    assert _pf([]) is None


def test_metric_block_hides_wr_below_20():
    rows = [_rec(1.0 if i % 2 == 0 else -1.0, "2026-10-19T00:00:00Z") for i in range(10)]
    m = metric_block(rows)
    assert m["n"] == 10
    assert m["win_rate"] is None
    assert m["win_rate_hidden"] is True


def test_metric_block_shows_wr_at_20():
    rows = [_rec(1.0 if i % 2 == 0 else -1.0, "2026-10-19T00:00:00Z") for i in range(20)]
    m = metric_block(rows)
    assert m["win_rate"] == 0.5
    assert m["win_rate_hidden"] is False


def test_recompute_coverage_complete():
    generated = "2026-10-20T00:00:00Z"
    start = "2026-10-05T00:00:00Z"  # 15d before -> covers 14d window
    records = [_rec(1.0, start), _rec(-1.0, "2026-10-19T00:00:00Z")]
    out = recompute_rolling_metrics(records, 336, generated)
    assert out["coverage"]["status"] == "complete"
    assert out["by_class"]["EQUITY"]["n"] == 2


def test_recompute_coverage_incomplete():
    generated = "2026-10-20T00:00:00Z"
    start = "2026-10-18T00:00:00Z"  # only 2d back -> incomplete for 14d
    records = [_rec(1.0, start)]
    out = recompute_rolling_metrics(records, 336, generated)
    assert out["coverage"]["status"] == "incomplete_coverage"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_cohort_reconciliation.py -v`
Expected: FAIL with `ImportError: cannot import name '_pf'`.

- [ ] **Step 3: Write minimal implementation**

```python
# append to tools/cohort_reconciliation.py
def _pf(rows):
    rows = [r for r in rows if r.get("pnl_pct") is not None]
    if not rows:
        return None
    pos = sum(r["pnl_pct"] for r in rows if r["pnl_pct"] > 0)
    neg = abs(sum(r["pnl_pct"] for r in rows if r["pnl_pct"] < 0))
    if neg == 0:
        return "inf" if pos > 0 else 0.0
    return pos / neg


def metric_block(rows):
    rows = [r for r in rows if r.get("pnl_pct") is not None]
    n = len(rows)
    wins = sum(1 for r in rows if r["pnl_pct"] > 0)
    losses = sum(1 for r in rows if r["pnl_pct"] < 0)
    hidden = n < 20
    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "win_rate": None if hidden else (wins / n if n else None),
        "win_rate_hidden": hidden,
        "pf": _pf(rows),
    }


def _window_filter(records, window_hours, generated_dt):
    cutoff = generated_dt - timedelta(hours=window_hours)
    out = []
    for r in records:
        try:
            ts = parse_ts(r.get("closed_at"))
        except Exception:
            continue
        if ts >= cutoff:
            out.append(r)
    return out


def _coverage(filtered, window_hours, generated_dt):
    ats = [parse_ts(r["closed_at"]) for r in filtered if r.get("closed_at")]
    window_start = generated_dt - timedelta(hours=window_hours)
    if not ats:
        return {"status": "incomplete_coverage", "oldest_closed_at": None,
                "window_start_utc": window_start.isoformat(), "covers_window": False}
    oldest = min(ats)
    return {"oldest_closed_at": oldest.isoformat(),
            "window_start_utc": window_start.isoformat(),
            "covers_window": oldest <= window_start,
            "status": "complete" if oldest <= window_start else "incomplete_coverage"}


def _group_metrics(filtered):
    by_class = {}
    by_strategy = {}
    for r in filtered:
        cls = r.get("asset_class") or "UNKNOWN"
        strat = r.get("strategy") or "UNKNOWN"
        by_class.setdefault(cls, []).append(r)
        by_strategy.setdefault(strat, []).append(r)
    return ({"class": k, "metrics": metric_block(v)} for k, v in by_class.items()), \
           ({"strategy": k, "metrics": metric_block(v)} for k, v in by_strategy.items())


def recompute_rolling_metrics(records, window_hours, generated_at):
    generated_dt = parse_ts(generated_at)
    filtered = _window_filter(records, window_hours, generated_dt)
    cov = _coverage(filtered, window_hours, generated_dt)
    by_class = {it["class"]: it["metrics"] for it in _group_metrics(filtered)[0]}
    by_strategy = {it["strategy"]: it["metrics"] for it in _group_metrics(filtered)[1]}
    return {"window_hours": window_hours, "coverage": cov,
            "by_class": by_class, "by_strategy": by_strategy}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_cohort_reconciliation.py -v`
Expected: PASS (all Task 1 + Task 2 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/cohort_reconciliation.py tests/test_cohort_reconciliation.py
git commit -m "feat: rolling PF/WR metrics + coverage check"
```

---

### Task 3: `flag_blocklist_bypass` (issue-time aware)

**Files:**
- Modify: `tools/cohort_reconciliation.py` (append)
- Test: `tests/test_cohort_reconciliation.py` (append)

**Contract:**

- `flag_blocklist_bypass(records, block_dates=None) -> dict` — for each record where `is_blocked_strategy(strategy, asset_class)` is true, emit `{pick_id, symbol, direction, strategy, asset_class, reason, issue_time_known, bypass}`. With no `block_dates` (the real situation), always `issue_time_known=False` and `bypass="blocked_now_issue_time_unknown"`. If `block_dates` is a dict mapping strategy→ISO date, and the record has `entry_time` ≥ block date, emit `issue_time_known=True`, `bypass="blocked_at_issue_time"`; if `entry_time` < block date, **do not flag** (was not blocked at issue).

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_cohort_reconciliation.py
from tools.cohort_reconciliation import flag_blocklist_bypass


def _pie(strategy, asset_class="FOREX", pick_id="p1", entry="2026-10-01T00:00:00Z"):
    return {"id": pick_id, "symbol": "EURUSD", "direction": "SHORT",
            "strategy": strategy, "asset_class": asset_class,
            "entry_time": entry, "pnl_pct": 0.5, "closed_at": "2026-10-19T00:00:00Z"}


def test_blocklist_bypass_flags_blocked_now_unknown():
    # 'forex_rsi2_mean_reversion' is FX-killed (verified in strategy_blocklist.py)
    recs = [_pie("forex_rsi2_mean_reversion")]
    out = flag_blocklist_bypass(recs)
    assert out["flagged"] is True
    assert out["count"] == 1
    assert out["issues"][0]["bypass"] == "blocked_now_issue_time_unknown"
    assert out["issues"][0]["issue_time_known"] is False


def test_blocklist_bypass_no_flag_when_unblocked():
    recs = [_pie("random_unblocked_strategy", asset_class="EQUITY")]
    assert flag_blocklist_bypass(recs)["flagged"] is False


def test_blocklist_bypass_issue_time_known_blocks_after_date():
    recs = [_pie("inverse_quan_engine_scalp", asset_class="EQUITY", pick_id="q1")]
    block_dates = {"inverse_quan_engine_scalp": "2026-09-15T00:00:00Z"}
    out = flag_blocklist_bypass(recs, block_dates)
    assert out["issues"][0]["issue_time_known"] is True
    assert out["issues"][0]["bypass"] == "blocked_at_issue_time"


def test_blocklist_bypass_issue_time_before_block_not_flagged():
    recs = [_pie("inverse_quan_engine_scalp", asset_class="EQUITY", pick_id="q2",
                 entry="2026-09-01T00:00:00Z")]
    block_dates = {"inverse_quan_engine_scalp": "2026-09-15T00:00:00Z"}
    assert flag_blocklist_bypass(recs, block_dates)["flagged"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_cohort_reconciliation.py -v`
Expected: FAIL with `ImportError: cannot import name 'flag_blocklist_bypass'`.

- [ ] **Step 3: Write minimal implementation**

```python
# append to tools/cohort_reconciliation.py
import os


def _block_dates_map(block_dates):
    if not block_dates:
        return {}
    return {str(k).strip().casefold(): parse_ts(v) for k, v in block_dates.items()}


def flag_blocklist_bypass(records, block_dates=None):
    from alpha_engine.strategy_blocklist import is_blocked_strategy, block_reason
    dates = _block_dates_map(block_dates)
    issues = []
    for r in records:
        strat = r.get("strategy")
        if not strat:
            continue
        ac = r.get("asset_class") or ""
        if not is_blocked_strategy(strat, ac):
            continue
        reason = block_reason(strat, ac) or "blocked"
        entry = r.get("entry_time")
        known = False
        bypass = "blocked_now_issue_time_unknown"
        if strat.strip().casefold() in dates and entry:
            try:
                entry_dt = parse_ts(entry)
                if entry_dt >= dates[strat.strip().casefold()]:
                    known, bypass = True, "blocked_at_issue_time"
                else:
                    continue  # not blocked at issue time -> no flag
            except Exception:
                pass
        issues.append({
            "pick_id": r.get("id"),
            "symbol": r.get("symbol"),
            "direction": r.get("direction"),
            "strategy": strat,
            "asset_class": ac or "UNKNOWN",
            "reason": reason,
            "issue_time_known": known,
            "bypass": bypass,
        })
    return {"flagged": bool(issues), "count": len(issues), "issues": issues}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_cohort_reconciliation.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/cohort_reconciliation.py tests/test_cohort_reconciliation.py
git commit -m "feat: blocklist-bypass flag (issue-time aware)"
```

---

### Task 4: `flag_batch_artefact` with with/without metrics

**Files:**
- Modify: `tools/cohort_reconciliation.py` (append)
- Test: `tests/test_cohort_reconciliation.py` (append)

**Contract:**

- `flag_batch_artefact(records, min_cluster=5) -> dict` — group records by identical `closed_at`; clusters with count ≥ `min_cluster` are flagged. Each cluster includes `strategy`, `source_system`, and per-strategy base metrics + `pf_excl_batch` / `win_rate_excl_batch` (computed with those cluster rows removed from that strategy's cohort).

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_cohort_reconciliation.py
from tools.cohort_reconciliation import flag_batch_artefact


def test_batch_artefact_detects_cluster_and_excl_metrics():
    ts = "2026-10-19T22:43:12Z"
    rows = [_rec(1.0, ts, strategy="momentum_ema", asset_class="CRYPTO") for _ in range(73)]
    # add one clean non-batch win + one loss for same strategy
    rows.append(_rec(1.0, "2026-10-18T00:00:00Z", strategy="momentum_ema", asset_class="CRYPTO"))
    rows.append(_rec(-1.0, "2026-10-17T00:00:00Z", strategy="momentum_ema", asset_class="CRYPTO"))
    out = flag_batch_artefact(rows)
    assert out["flagged"] is True
    assert len(out["clusters"]) == 1
    c = out["clusters"][0]
    assert c["count"] == 73
    assert c["closed_at"] == ts
    assert c["strategy"] == "momentum_ema"
    # base includes cluster; excl drops it
    assert c["metrics"]["n"] == 75
    assert c["metrics_excl_batch"]["n"] == 2
    assert c["metrics_excl_batch"]["win_rate"] == 0.5


def test_batch_artefact_no_flag_below_min_cluster():
    rows = [_rec(1.0, "2026-10-19T22:43:12Z") for _ in range(3)]
    assert flag_batch_artefact(rows)["flagged"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_cohort_reconciliation.py -v`
Expected: FAIL with `ImportError: cannot import name 'flag_batch_artefact'`.

- [ ] **Step 3: Write minimal implementation**

```python
# append to tools/cohort_reconciliation.py
from collections import defaultdict


def flag_batch_artefact(records, min_cluster=5):
    by_ts = defaultdict(list)
    for r in records:
        ts = r.get("closed_at")
        if ts:
            by_ts[ts].append(r)
    clusters = []
    for ts, rows in sorted(by_ts.items()):
        if len(rows) < min_cluster:
            continue
        strats = {r.get("strategy") for r in rows}
        sources = {r.get("source_system") for r in rows}
        primary_strat = next(iter(strats), None)
        # base metrics for the strategy cohort (all records of that strategy)
        strat_all = [r for r in records if r.get("strategy") == primary_strat]
        # excl metrics: drop rows that share this batch timestamp AND this strategy
        strat_excl = [r for r in strat_all
                      if not (r.get("closed_at") == ts and r.get("strategy") == primary_strat)]
        clusters.append({
            "closed_at": ts,
            "count": len(rows),
            "distinct_strategies": len(strats),
            "strategy": primary_strat,
            "source_system": next(iter(sources), None),
            "metrics": metric_block(strat_all) if primary_strat else None,
            "metrics_excl_batch": metric_block(strat_excl) if primary_strat else None,
        })
    return {"flagged": bool(clusters), "clusters": clusters}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_cohort_reconciliation.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/cohort_reconciliation.py tests/test_cohort_reconciliation.py
git commit -m "feat: batch-artefact flag with with/without metrics"
```

---

### Task 5: `flag_published_disagreement` (window-matched + coverage)

**Files:**
- Modify: `tools/cohort_reconciliation.py` (append)
- Test: `tests/test_cohort_reconciliation.py` (append)

**Contract:**

- `flag_published_disagreement(dashboard_by_window, summary_stats, tol_pf=0.1, tol_n_pct=0.2) -> dict` — `dashboard_by_window` maps `window_hours` → recompute result; `summary_stats` maps path → loaded summary dict (or `None`).
- For each summary file present: match by `window_hours`. If the dashboard window's coverage status is `incomplete_coverage`, emit a check with `coverage_status="incomplete_coverage"` and `disagree=False` (skip). Otherwise compare per class: PF delta > `tol_pf` OR `n` delta > `tol_n_pct` of max → `disagree=True`.
- `_pf(rows)` returns `'inf'` for infinite PF; treat `'inf'` delta as 0 when both sides are `'inf'`; a non-inf vs inf is a disagreement.
- Emit a `stale` check when a summary file's `generated_at` is older than the dashboard's `generated_at` by > 48h.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_cohort_reconciliation.py
from tools.cohort_reconciliation import flag_published_disagreement


def _summary(pf, n_closed, wins, losses, generated=None, window_hours=336):
    return {
        "window_hours": window_hours,
        "generated_at": generated or "2026-10-20T00:00:00Z",
        "by_class": {"EQUITY": {"n_closed": n_closed, "wins": wins, "losses": losses,
                                "wr_pct": 100.0 * wins / max(n_closed, 1), "pf": pf}},
    }


def _dashboard(window_hours=336, status="complete", n=2780, pf=1.47):
    return {
        "window_hours": window_hours,
        "coverage": {"status": status},
        "by_class": {"EQUITY": {"n": n, "wins": 2000, "losses": 780,
                                "win_rate": 0.719, "win_rate_hidden": False, "pf": pf}},
    }


def test_disagreement_flags_pf_delta():
    summary = _summary(pf=1.012, n_closed=69, wins=35, losses=34)
    dashboard = _dashboard(n=2780, pf=1.47)
    out = flag_published_disagreement({336: dashboard}, {"s14": summary})
    assert out["flagged"] is True
    assert out["checks"][0]["disagree"] is True


def test_disagreement_incomplete_coverage_skipped():
    summary = _summary(pf=1.012, n_closed=69, wins=35, losses=34)
    dashboard = _dashboard(status="incomplete_coverage")
    out = flag_published_disagreement({336: dashboard}, {"s14": summary})
    assert out["checks"][0]["coverage_status"] == "incomplete_coverage"
    assert out["checks"][0]["disagree"] is False
    assert out["flagged"] is False


def test_disagreement_missing_summary_file():
    out = flag_published_disagreement({336: _dashboard()}, {"s14": None})
    assert out["checks"][0]["source"] == "missing"


def test_disagreement_stale_source_flags_age_in_days():
    summary = _summary(pf=1.1, n_closed=100, wins=50, losses=50,
                       generated="2026-06-21T00:00:00Z")
    # dashboard generated_at = 2026-10-20T00:00:00Z -> ~121 days stale
    out = flag_published_disagreement({336: _dashboard()}, {"s14": summary},
                                      dashboard_generated_at="2026-10-20T00:00:00Z")
    stale = [c for c in out["checks"] if c.get("source") == "stale"]
    assert len(stale) == 1
    assert stale[0]["stale_days"] == 121
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_cohort_reconciliation.py -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write minimal implementation**

```python
# append to tools/cohort_reconciliation.py
def _pf_delta(a, b):
    if a == b:
        return 0.0
    if a == "inf":
        return 10.0  # treat infinite vs finite as large delta
    if b == "inf":
        return 10.0
    return abs((a or 0.0) - (b or 0.0))


def flag_published_disagreement(dashboard_by_window, summary_stats,
                               tol_pf=0.1, tol_n_pct=0.2,
                               stale_hours=48, dashboard_generated_at=None):
    checks = []
    for path, summary in summary_stats.items():
        if summary is None:
            checks.append({"file": path, "source": "missing"})
            continue
        wh = summary.get("window_hours")
        dash = dashboard_by_window.get(wh)
        if dash is None:
            checks.append({"file": path, "source": "no_matching_window"})
            continue
        cov_status = dash["coverage"]["status"]
        if cov_status != "complete":
            checks.append({"file": path, "cohort": f"{wh}h",
                           "coverage_status": cov_status, "disagree": False})
            continue
        # stale check (flags with age in days per user requirement)
        try:
            gen = parse_ts(summary["generated_at"])
            if dashboard_generated_at:
                dash_gen = parse_ts(dashboard_generated_at)
                if (dash_gen - gen).total_seconds() > stale_hours * 3600:
                    stale_days = round((dash_gen - gen).total_seconds() / 86400)
                    checks.append({"file": path, "source": "stale",
                                   "stale_days": stale_days,
                                   "stale_hours": round((dash_gen - gen).total_seconds() / 3600, 1)})
        except Exception:
            pass
        for cls, sm in summary.get("by_class", {}).items():
            dm = dash["by_class"].get(cls)
            if dm is None:
                continue
            pf_delta = _pf_delta(dm.get("pf"), sm.get("pf"))
            n_delta_frac = abs(dm.get("n", 0) - sm.get("n_closed", 0)) / max(dm.get("n", 0), sm.get("n_closed", 0), 1)
            disagree = pf_delta > tol_pf or n_delta_frac > tol_n_pct
            checks.append({
                "file": path, "cohort": f"{wh}h/{cls}",
                "coverage_status": "complete",
                "dashboard_n": dm.get("n"), "dashboard_pf": dm.get("pf"),
                "summary_n": sm.get("n_closed"), "summary_pf": sm.get("pf"),
                "disagree": disagree,
            })
    return {"flagged": any(c.get("disagree") for c in checks), "checks": checks}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_cohort_reconciliation.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/cohort_reconciliation.py tests/test_cohort_reconciliation.py
git commit -m "feat: published-vs-published disagreement flag (window-matched + coverage)"
```

---

### Task 6: `assemble_output` + `main()` CLI + integration run + hygiene test

**Files:**
- Modify: `tools/cohort_reconciliation.py` (append)
- Test: `tests/test_cohort_reconciliation.py` (append)

**Contract:**

- `assemble_output(parts) -> dict` — schema_version, generated_utc, comparison_scope `"published-file-vs-published-file"`, inputs, rolling_metrics_by_window, blocklist_bypass, batch_artefact, published_disagreement, notes. **Must contain no `READY`/`ENTER` substrings** (asserted).
- `main(argv=None) -> int` — argparse: `--dashboard`, `--summary14d`, `--summary48h`, `--block-dates` (optional JSON), `--out` (default `audit_dashboard/data/cohort_reconciliation.json`), `--strict`. Reads inputs, recomputes 14d (336h) and 48h windows, assembles, writes JSON. Returns 0 on success.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_cohort_reconciliation.py
from tools.cohort_reconciliation import assemble_output, main
import subprocess
import sys


def test_assemble_has_no_ready_enter():
    out = assemble_output({
        "inputs": {}, "rolling_metrics_by_window": {}, "blocklist_bypass": {"flagged": False, "count": 0, "issues": []},
        "batch_artefact": {"flagged": False, "clusters": []},
        "published_disagreement": {"flagged": False, "checks": []}, "notes": [],
    })
    blob = json.dumps(out)
    assert "READY" not in blob
    assert "ENTER" not in blob
    assert out["comparison_scope"] == "published-file-vs-published-file"


def test_main_writes_output(tmp_path):
    dashboard = {
        "generated_at": "2026-10-20T00:00:00Z",
        "picks": {"recent_closed": [
            {"id": "a", "strategy": "s1", "asset_class": "EQUITY",
             "pnl_pct": 1.0, "closed_at": "2026-10-19T00:00:00Z", "source_system": "alpha_engine"},
            {"id": "b", "strategy": "s1", "asset_class": "EQUITY",
             "pnl_pct": -1.0, "closed_at": "2026-10-18T00:00:00Z", "source_system": "alpha_engine"},
        ]},
    }
    sum14 = {"window_hours": 336, "generated_at": "2026-10-20T00:00:00Z",
             "by_class": {"EQUITY": {"n_closed": 2, "wins": 1, "losses": 1, "wr_pct": 50.0, "pf": 1.0}}}
    sum48 = {"window_hours": 48, "generated_at": "2026-10-20T00:00:00Z",
             "by_class": {"EQUITY": {"n_closed": 1, "wins": 1, "losses": 0, "wr_pct": 100.0, "pf": "inf"}}}
    d = tmp_path / "d.json"; s14 = tmp_path / "s14.json"; s48 = tmp_path / "s48.json"
    out = tmp_path / "out.json"
    d.write_text(json.dumps(dashboard)); s14.write_text(json.dumps(sum14)); s48.write_text(json.dumps(sum48))
    rc = main(["--dashboard", str(d), "--summary14d", str(s14), "--summary48h", str(s48), "--out", str(out)])
    assert rc == 0
    data = json.loads(out.read_text())
    assert data["schema_version"] == "1.1.0"
    assert data["comparison_scope"] == "published-file-vs-published-file"
    assert "14d" in str(data["rolling_metrics_by_window"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_cohort_reconciliation.py -v`
Expected: FAIL with `ImportError: cannot import name 'assemble_output'`.

- [ ] **Step 3: Write minimal implementation**

```python
# append to tools/cohort_reconciliation.py
import argparse


def assemble_output(parts):
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": utcnow_iso(),
        "comparison_scope": "published-file-vs-published-file",
        "inputs": parts.get("inputs", {}),
        "rolling_metrics_by_window": parts.get("rolling_metrics_by_window", {}),
        "blocklist_bypass": parts.get("blocklist_bypass", {"flagged": False, "count": 0, "issues": []}),
        "batch_artefact": parts.get("batch_artefact", {"flagged": False, "clusters": []}),
        "published_disagreement": parts.get("published_disagreement", {"flagged": False, "checks": []}),
        "notes": parts.get("notes", []),
    }


def _read_inputs(dash_path, s14_path, s48_path):
    dash = load_json(dash_path)
    s14 = load_json(s14_path)
    s48 = load_json(s48_path)
    recs = []
    if dash and dash.get("picks", {}).get("recent_closed"):
        recs = dash["picks"]["recent_closed"]
    inputs = {
        "dashboard_data": {"path": dash_path, "present": dash is not None,
                           "generated_utc": (dash or {}).get("generated_at"),
                           "records": len(recs)},
        "summary_stats_14d": {"path": s14_path, "present": s14 is not None,
                              "generated_utc": (s14 or {}).get("generated_at")},
        "summary_stats_48h": {"path": s48_path, "present": s48 is not None,
                              "generated_utc": (s48 or {}).get("generated_at")},
    }
    return dash, recs, s14, s48, inputs


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cohort_reconciliation")
    ap.add_argument("--dashboard", default="audit_dashboard/data/dashboard_data.json")
    ap.add_argument("--summary14d", default="audit_dashboard/data/pick_summary_stats_14d.json")
    ap.add_argument("--summary48h", default="audit_dashboard/data/pick_summary_stats_48h.json")
    ap.add_argument("--block-dates", default=None, help="optional JSON: strategy -> block ISO date")
    ap.add_argument("--out", default="audit_dashboard/data/cohort_reconciliation.json")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)

    dash, recs, s14, s48, inputs = _read_inputs(args.dashboard, args.summary14d, args.summary48h)
    if args.strict and dash is None:
        raise FileNotFoundError(args.dashboard)

    generated_at = dash.get("generated_at") if dash else utcnow_iso()
    w14 = recompute_rolling_metrics(recs, 336, generated_at) if dash else {}
    w48 = recompute_rolling_metrics(recs, 48, generated_at) if dash else {}
    rolling = {}
    if w14:
        rolling["14d"] = w14
    if w48:
        rolling["48h"] = w48

    block_dates = None
    if args.block_dates:
        with open(args.block_dates, encoding="utf-8") as f:
            block_dates = json.load(f)
    bypass = flag_blocklist_bypass(recs, block_dates) if dash else {"flagged": False, "count": 0, "issues": []}
    batch = flag_batch_artefact(recs) if dash else {"flagged": False, "clusters": []}

    summary_map = {"14d": s14, "48h": s48}
    dash_by_window = {336: w14, 48: w48}
    disagreement = flag_published_disagreement(dash_by_window, summary_map,
                                              dashboard_generated_at=generated_at) if dash else {"flagged": False, "checks": []}

    notes = ["comparison_scope=published-file-vs-published-file; no live DB read performed"]
    if s14 and s14.get("generated_at"):
        notes.append(f"summary_stats_14d generated_at={s14.get('generated_at')}")
    if s48 and s48.get("generated_at"):
        notes.append(f"summary_stats_48h generated_at={s48.get('generated_at')}")

    out = assemble_output({"inputs": inputs, "rolling_metrics_by_window": rolling,
                           "blocklist_bypass": bypass, "batch_artefact": batch,
                           "published_disagreement": disagreement, "notes": notes})
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_cohort_reconciliation.py -v`
Expected: PASS (all 6 tasks).

- [ ] **Step 5: Run against the real published files**

Run: `python3 tools/cohort_reconciliation.py`
Expected: writes `audit_dashboard/data/cohort_reconciliation.json`; verify shape:
```bash
python3 -c "import json;d=json.load(open('audit_dashboard/data/cohort_reconciliation.json'));print(d['schema_version'], d['comparison_scope']);print(list(d['rolling_metrics_by_window'].keys()))"
```
Expected: `1.1.0 published-file-vs-published-file` and `['14d', '48h']` (14d coverage likely `complete` since data spans back to Feb; 48h coverage may be `incomplete_coverage`).

- [ ] **Step 6: Commit**

```bash
git add tools/cohort_reconciliation.py tests/test_cohort_reconciliation.py
git commit -m "feat: assemble output + CLI + real-file verification"
```

---

## Self-Review (done before handoff)

- **Spec coverage:** §4 schema → implemented in `assemble_output`; §5 functions → Tasks 1–6; coverage check (change #2) → Task 2 `_coverage`; issue-time bypass (change #3) → Task 3; batch with/without (change #4) → Task 4; window-matched disagreement → Task 5; hygiene (no READY/ENTER) → Task 6 test. All 4 approval changes covered.
- **Placeholder scan:** no TBD/TODO; every step has concrete code/tests.
- **Type consistency:** `metric_block` used by `recompute_rolling_metrics`, `flag_batch_artefact`, and `flag_published_disagreement` shares `{n, wins, losses, win_rate, win_rate_hidden, pf}`. `flag_published_disagreement` reads `dm["n"]`/`dm["pf"]` from `metric_block` output — consistent. `_pf` returns `'inf'`/`None`/float; handled in `_pf_delta`.
