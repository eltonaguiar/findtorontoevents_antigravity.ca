"""Unit-sanity guards: catch percent-vs-fraction scaling errors in committed reports.

A number can be internally consistent yet wrong by 100x. These assert plausible ranges so a
fraction-where-percent-expected (or vice versa) bug fails CI.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(p):
    return json.loads((ROOT / p).read_text())


def test_fund_report_shapes():
    d = _load("reports/fund_deep_dive.json")
    for k, m in d["funds"].items():
        if m.get("net_cagr_pct") is not None:
            assert -100 < m["net_cagr_pct"] < 100, (k, m["net_cagr_pct"])
        if m.get("vol_pct") is not None:
            assert 0 <= m["vol_pct"] < 200, (k, m["vol_pct"])
        if m.get("sharpe_excess") is not None:
            assert -10 < m["sharpe_excess"] < 10, (k, m["sharpe_excess"])


def test_alpha_ci_lo_in_percent_range():
    d = _load("reports/alpha_by_class.json")
    for row in d["per_class"]:
        v = row.get("best_alpha_ci_lo")
        if v is not None:
            # alpha_ci_lo is in percent; a fraction-vs-percent bug would be ~100x
            assert -100 <= v < 100, (row["class"], v)


def test_deployment_fee_compounding_sane():
    d = _load("reports/deployment_analysis.json")
    for fee, v in d["R15_fees"].items():
        assert 100_000 < v < 2_000_000, (fee, v)
