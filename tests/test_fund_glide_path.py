"""D6/D7: tests for tools/fund_glide_path.py."""
import json
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEEP = REPO_ROOT / "2026-11-15_AM_profitability-plan/copilot-financial-review/market_prices.csv"


@pytest.fixture(scope="module")
def glide(tmp_path_factory):
    if not DEEP.exists():
        pytest.skip("price CSV not present in this checkout")
    out = tmp_path_factory.mktemp("glide") / "g.json"
    p = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "fund_glide_path.py"), "--json", str(out)],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert p.returncode == 0, p.stdout + p.stderr
    return json.loads(out.read_text())


def test_every_mix_is_reported(glide):
    for label, block in glide["paths"].items():
        assert len(block["rows"]) == 7, label
        eqs = [r["equity_pct"] for r in block["rows"]]
        assert eqs == sorted(eqs, reverse=True)


def test_net_never_exceeds_gross(glide):
    """The gross/net confusion produced a false bug report once - keep them apart."""
    for block in glide["paths"].values():
        for r in block["rows"]:
            assert r["net_cagr_pct"] <= r["cagr_pct"] + 1e-9


def test_more_bonds_lowers_return(glide):
    """In this window bonds were a drag; the table must say so, not the reverse."""
    for label, block in glide["paths"].items():
        rets = [r["net_cagr_pct"] for r in block["rows"]]
        assert rets == sorted(rets, reverse=True), f"{label}: {rets}"


def test_more_bonds_lowers_volatility(glide):
    # rows run highest-equity first, so volatility should also fall down the table
    for label, block in glide["paths"].items():
        vols = [r["vol_pct"] for r in block["rows"]]
        assert vols == sorted(vols, reverse=True), f"{label}: {vols}"


def test_full_equity_is_identical_under_both_rules(glide):
    """With one sleeve there is nothing to rebalance, so the paths must match."""
    bh = {r["equity_pct"]: r for r in glide["paths"]["buy & hold"]["rows"]}
    q = {r["equity_pct"]: r for r in glide["paths"]["quarterly (63d)"]["rows"]}
    assert bh[100]["net_cagr_pct"] == pytest.approx(q[100]["net_cagr_pct"])
    assert bh[100]["turnover"] == 0.0


def test_rebalancing_costs_turnover_and_does_not_help(glide):
    """Buy & hold beat quarterly in this window; assert the turnover is real so
    a silent 'rebal ignored' regression (plan item D1) cannot return."""
    for label, block in glide["paths"].items():
        for r in block["rows"]:
            if r["equity_pct"] == 100:
                assert r["turnover"] == 0.0
            elif label == "quarterly (63d)":
                assert r["turnover"] > 0.0
            else:
                assert r["turnover"] == 0.0


def test_frontier_callouts_exist(glide):
    for block in glide["paths"].values():
        assert "max_sharpe_equity_pct" in block
        assert "min_vol_equity_pct" in block
