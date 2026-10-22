import copy
import json
from datetime import datetime, timedelta, timezone

from tools.audit_scorecard import build_verdicts, main


def row(i=0, **changes):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=i)
    result = {
        "id": str(i), "strategy": "test", "symbol": "SPY",
        "asset_class": "ETF", "direction": "LONG", "entry_price": 100,
        "exit_price": 102 if i % 2 else 99, "pnl_pct": 999,
        "timestamp": start.isoformat(), "entry_time": "",
        "closed_at": (start + timedelta(hours=1)).isoformat(),
    }
    result.update(changes)
    return result


def payload(rows):
    return {"generated_at": "2026-10-22T20:00:00Z",
            "summary": {"total_closed_picks": len(rows)},
            "picks": {"recent_closed": rows}}


def stats(data):
    return build_verdicts(data)["strategies"][0]


def test_artifact_fixture():
    rows = [row(0, exit_price=0), row(1, pnl_pct=0, exit_price=100, status="F"),
            row(2, exit_price=999999), row(3), row(4, id="3"),
            row(5, closed_at="2026-01-06T00:01:00Z"),
            row(6, symbol="BTCUSDT", asset_class="EQUITY"),
            row(7, timestamp="", entry_time=""), row(8, exit_price=None)]
    result = build_verdicts(payload(rows))
    assert result["excluded"] == {
        "zero_exit_price": 1, "placeholder_flat": 1, "sentinel_price": 1,
        "duplicate_id": 1, "hold_under_2_minutes": 1, "wrong_asset_class": 1,
        "missing_entry_timestamp": 1, "missing_exit_price": 1}
    assert sum(s["n"] for s in result["strategies"]) == 1
    assert result["top_verified"] == []


def test_wr_hidden_at_19_visible_at_20():
    assert stats(payload([row(i) for i in range(19)]))["win_rate"] is None
    assert stats(payload([row(i) for i in range(20)]))["win_rate"] == 50


def test_short_sign_and_reported_pnl_not_trusted():
    result = stats(payload([row(direction="SHORT", exit_price=90, pnl_pct=-10)]))
    assert result["sum_trade_pct"] == 10
    assert result["wins"] == 1
    assert result["inconsistent"] is False
    assert result["pnl_disagreement_n"] == 1


def test_flat_requires_proof():
    result = build_verdicts(payload([
        row(0, exit_price=100, pnl_pct=0, status="F"),
        row(1, exit_price=100, pnl_pct=0, genuine_flat=True),
    ]))
    # A static genuine_flat claim is not proof of an executable flat exit.
    assert result["excluded"]["placeholder_flat"] == 2


def test_nonzero_return_with_reported_zero_is_not_flat_placeholder():
    assert stats(payload([row(exit_price=101, pnl_pct=0)]))["n"] == 1


def test_execution_backed_flat_is_preserved():
    result = stats(payload([row(exit_price=100, pnl_pct=0,
                                exit_reason="BREAKEVEN", entry_fill_id="entry1",
                                exit_fill_id="exit1")]))
    assert result["n"] == 1
    assert result["wins"] == 0
    assert result["losses"] == 1  # Genuine gross flat loses under scenario costs.


def test_date_only_entry_falls_back_to_precise_signal_proxy():
    result = stats(payload([row(entry_time="2026-01-01")]))
    assert result["n"] == 1
    assert result["gates"]["L1"]["status"] == "N/A"


def test_missing_cost_model_keeps_cost_stats_and_gates_unverified():
    result = stats(payload([row(asset_class="FOREX", symbol="EURUSD=X")]))
    assert result["pf"] is None
    assert result["pf_2x_cost"] is None
    assert result["gates"]["C1"]["status"] == "N/A"
    assert result["gates"]["S2"]["status"] == "N/A"


def test_no_summary_total_does_not_claim_full_history():
    data = payload([row()])
    data.pop("summary")
    result = build_verdicts(data)
    assert result["source"]["total_known"] is False
    assert result["source"]["total_closed_n"] is None
    assert result["strategies"][0]["gates"]["R8"]["status"] == "N/A"


def test_same_minute_duplicate_and_cross_direction_overlap():
    duplicate = row(1, timestamp="2026-01-01T00:00:30Z",
                    closed_at="2026-01-01T02:00:00Z")
    result = build_verdicts(payload([row(), duplicate]))
    assert result["excluded"] == {"duplicate_signal_minute": 1}
    duplicate["direction"] = "SHORT"
    assert build_verdicts(payload([row(), duplicate]))["excluded"] == {"same_symbol_overlap": 1}


def test_all_source_rows_invalid_still_visible():
    result = build_verdicts(payload([row(exit_price=0)]))
    assert result["classes"]["ETF"]["n"] == 0
    assert result["classes"]["ETF"]["excluded_n"] == 1
    assert result["classes"]["ETF"]["gates"]["D1"]["status"] == "FAIL"


def test_missing_generated_at_has_deterministic_null_not_wall_clock():
    data = payload([])
    data.pop("generated_at")
    assert build_verdicts(data)["generated_at"] is None


def test_generation_timestamp_preserves_source_string_for_ui_binding():
    data = payload([])
    data["generated_at"] = "2026-10-22T22:14:47.662743+00:00"
    assert build_verdicts(data)["generated_at"] == data["generated_at"]
    result = build_verdicts(data, as_of="2026-10-22T23:00:00+00:00")
    assert result["generated_at"] == data["generated_at"]
    assert result["source"]["generated_at"] == data["generated_at"]
    assert result["evaluated_at"] == "2026-10-22T23:00:00+00:00"


def test_dirty_snapshot_does_not_claim_endpoint_failure():
    result = stats(payload([row(exit_price=0)]))
    assert result["health"] == "OK"
    assert result["warning"] is False
    assert "error_message" not in result


def test_endpoint_health_is_sanitized_and_missing_snapshot_empty():
    data = payload([])
    data["endpoint_health"] = {
        "ETF": {"health": "BROKEN", "error_message": "secret password"},
        "OPTIONS": {"health": "OK"}, "CRYPTO": {"health": "arbitrary"},
    }
    result = build_verdicts(data)
    assert result["classes"]["ETF"]["health"] == "BROKEN"
    assert result["classes"]["OPTIONS"]["health"] == "EMPTY"
    assert result["classes"]["CRYPTO"]["health"] == "EMPTY"
    assert "secret password" not in json.dumps(result)


def test_staleness_is_snapshot_update_not_last_trade():
    data = payload([row()])
    assert build_verdicts(data)["classes"]["ETF"]["health"] == "OK"
    result = build_verdicts(data, as_of="2026-11-01T20:00:00Z")
    assert result["classes"]["ETF"]["health"] == "STALE"
    assert result["source"]["snapshot_age_days"] == 10


def test_warning_is_boolean_and_only_too_good_thresholds():
    result = stats(payload([row(i) for i in range(50)]))
    assert result["warning"] is False
    assert isinstance(result["limitations"], str)
    assert stats(payload([row(i, exit_price=102) for i in range(50)]))["warning"] is True
    assert stats(payload([row(exit_price=106)]))["warning"] is True


def test_pnl_sentinel_quarantined_with_plausible_prices():
    for value in (999999, -999999):
        result = build_verdicts(payload([row(pnl_pct=value)]))
        assert result["excluded"] == {"sentinel_pnl": 1}
        assert result["classes"]["ETF"]["gates"]["D1"]["status"] == "FAIL"


def test_net_wins_consistent_with_scenario_pf_and_unknown_hidden():
    result = stats(payload([row(i, exit_price=100.01) for i in range(20)]))
    assert result["wins"] == 0
    assert result["losses"] == 20
    assert result["win_rate"] == 0
    assert result["pf"] == 0
    assert result["wins_basis"] == "price_derived_scenario_net"
    unknown = stats(payload([row(i, asset_class="FOREX", symbol="EURUSD=X") for i in range(20)]))
    assert unknown["wins"] is unknown["losses"] is unknown["win_rate"] is None


def test_independence_and_legacy_baseline_not_fabricated():
    result = stats(payload([row(i) for i in range(100)]))
    assert result["gates"]["S1"]["status"] == "N/A"
    assert "old" not in result


def test_taxonomy_and_noncrypto_usd_quote_not_rejected():
    for asset, symbol in (("PENSION", "TEST"), ("MEME", "DOGEUSDT"),
                          ("PENNY", "TEST"), ("COMMODITY", "XAU-USD")):
        result = build_verdicts(payload([row(asset_class=asset, symbol=symbol)]))
        assert result["excluded"] == {}
        assert result["classes"][asset]["n"] == 1


def test_source_system_separates_performance_duplicates_and_overlap():
    first = row(id="sourceA", source_system="A")
    second = row(id="sourceB", source_system="B")
    result = build_verdicts(payload([first, second]))
    assert result["excluded"] == {}
    assert [(s["source_system"], s["n"]) for s in result["strategies"]] == [("A", 1), ("B", 1)]
    assert stats(payload([row()]))["source_system"] == "UNKNOWN"


def test_noncrypto_aggregate_uses_cleaned_rows_and_discloses_unknown_costs():
    data = payload([row(0), row(1, exit_price=0),
                    row(2, symbol="BTCUSDT", asset_class="CRYPTO"),
                    row(3, symbol="DOGEUSDT", asset_class="MEME"),
                    row(4, symbol="EURUSD=X", asset_class="FOREX")])
    result = build_verdicts(data)["classes"]["NON_CRYPTO"]
    assert result["n"] == 2
    assert result["excluded_n"] == 1
    assert result["exclusion_reasons"] == {"zero_exit_price": 1}
    assert result["sum_trade_pct"] == -2
    assert result["pf"] is result["win_rate"] is None
    assert result["gates"]["R6"]["status"] in {"PASS", "FAIL"}


def test_empty_sum_is_null_and_empty_health_explicit():
    result = build_verdicts(payload([]))
    for item in result["classes"].values():
        assert item["sum_trade_pct"] is None
        assert item["health"] == "EMPTY"


def test_deterministic_and_input_unchanged():
    data = payload([row(i) for i in range(25)])
    before = copy.deepcopy(data)
    assert json.dumps(build_verdicts(data), sort_keys=True) == json.dumps(
        build_verdicts(data), sort_keys=True)
    assert data == before


def test_no_portfolio_compounding_or_peer_evidence_promotion():
    data = payload([row(i) for i in range(20)])
    data["audit_evidence"] = {"verified": True, "mdd_pct": 1,
                              "compound_return_pct": 500, "operator_signoff": True}
    result = stats(data)
    assert result["compound_return_pct"] is None
    assert result["mdd_pct"] is None
    assert result["label"] == "FAIL"
    assert all(result["gates"][g]["status"] == "N/A"
               for g in ("S5", "S6", "S8", "S9", "F1"))


def test_cap_disclosed_and_all_gates_exist():
    data = payload([row()])
    data["summary"]["total_closed_picks"] = 3501
    result = build_verdicts(data)
    assert result["source"]["scope"] == "recent_closed_subset"
    assert result["source"]["total_known"] is True
    assert result["strategies"][0]["gates"]["R8"]["status"] == "FAIL"
    assert all(f"S{i}" in result["strategies"][0]["gates"] for i in range(1, 14))
    assert all(f"F{i}" in result["strategies"][0]["gates"] for i in range(1, 5))


def test_no_loss_pf_is_null_and_bootstrap_mass_reported():
    result = stats(payload([row(i, exit_price=102) for i in range(20)]))
    assert result["pf"] is None
    assert result["pf_ci95"] == [None, None]
    assert result["pf_bootstrap_undefined_mass"] == 1


def test_batch_and_overlap_are_removed():
    rows = [row(i, closed_at="2026-02-01T00:00:00Z") for i in range(10)]
    result = build_verdicts(payload(rows))
    assert result["excluded"] == {"batch_close_second": 10}
    data = payload([row(0), row(1, timestamp="2026-01-01T00:30:00Z",
                                closed_at="2026-01-01T02:00:00Z")])
    assert build_verdicts(data)["excluded"] == {"same_symbol_overlap": 1}


def test_empty_and_cli_deterministic(tmp_path):
    source, output = tmp_path / "source.json", tmp_path / "out.json"
    source.write_text(json.dumps(payload([])))
    main(["--input", str(source), "--output", str(output),
          "--as-of", "2026-10-22T23:00:00Z"])
    first = output.read_bytes()
    main(["--input", str(source), "--output", str(output),
          "--as-of", "2026-10-22T23:00:00Z"])
    assert output.read_bytes() == first
    assert json.loads(first)["top_verified"] == []
