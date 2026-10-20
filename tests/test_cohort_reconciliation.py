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


def test_parse_ts_handles_est_edt_abbrev():
    # real published dashboard contains e.g. "2026-10-18T14:48:19 EST"
    dt_est = parse_ts("2026-10-18T14:48:19 EST")
    assert dt_est.tzinfo is not None
    assert dt_est.utcoffset().total_seconds() == -5 * 3600
    dt_edt = parse_ts("2026-10-18T14:48:19 EDT")
    assert dt_edt.tzinfo is not None
    assert dt_edt.utcoffset().total_seconds() == -4 * 3600


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
    # Only the in-window record (>= window start 2026-10-06) counts toward metrics
    assert out["by_class"]["EQUITY"]["n"] == 1


def test_recompute_coverage_incomplete():
    generated = "2026-10-20T00:00:00Z"
    start = "2026-10-18T00:00:00Z"  # only 2d back -> incomplete for 14d
    records = [_rec(1.0, start)]
    out = recompute_rolling_metrics(records, 336, generated)
    assert out["coverage"]["status"] == "incomplete_coverage"


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
    assert c["metrics_excl_batch"]["win_rate"] is None
    assert c["metrics_excl_batch"]["win_rate_hidden"] is True
    assert c["metrics_excl_batch"]["win_rate_low_n"] == 0.5


def test_batch_artefact_no_flag_below_min_cluster():
    rows = [_rec(1.0, "2026-10-19T22:43:12Z") for _ in range(3)]
    assert flag_batch_artefact(rows)["flagged"] is False


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
    # stale summary is a different-time cohort: no spurious per-class disagreement
    assert len(out["checks"]) == 1
    assert out["flagged"] is False


from tools.cohort_reconciliation import assemble_output, main
import subprocess


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
