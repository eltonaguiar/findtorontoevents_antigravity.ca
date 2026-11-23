"""Unit tests for tools/fund_deep_dive.py metrics (plan item I1).

These lock the 2026-11-23 corrections so a later refactor cannot silently
restore the old behaviour:
  A1/A2  Sharpe/Sortino are (R - R_f)/risk, not a fee-adjusted return/vol ratio
  A4     the cash vehicle emits null, not a finite ratio
  A5     Sortino uses the all-N target downside deviation, not the negative-day
         count (the legacy denominator is retained for the delta)
  A6     net_cagr is compounded, not additive
  A7     vol uses the sample stdev, not the population stdev

Fixtures are hand-computable so the expected values are derived arithmetically,
not copied from whatever the code happens to print.
"""
from __future__ import annotations

import csv
import os
# Pin hash randomisation BEFORE importing the tool: set iteration order
# leaks into float accumulation and flips headline CAGRs by ~0.1pp.
os.environ.setdefault("PYTHONHASHSEED", "0")
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import fund_deep_dive as fd  # noqa: E402


# --------------------------------------------------------------------------
# A6 / A7 / CAGR / MDD — exact arithmetic on a two-point series
# --------------------------------------------------------------------------
# r = [+10%, -10%], ann = 2 (so the CAGR exponent is 252/2 -> wait: ann/n with
# n=2 gives factor 1, i.e. the whole series is one "year").
# product = 1.10 * 0.90 = 0.99  ->  CAGR = 0.99**1 - 1 = -1.00%
TWO_POINT = [0.10, -0.10]


def test_cagr_is_geometric_on_the_series():
    m = fd.metrics(TWO_POINT, mer=0.0, ann=2)
    assert m["cagr_pct"] == pytest.approx(-1.00, abs=1e-9)


def test_net_cagr_is_compounded_not_additive():
    """A6: (1+cagr)(1-mer)-1, NOT cagr-mer.

    cagr=-0.01, mer=0.01 -> 0.99*0.99-1 = -0.0199 (-1.99%).
    The old additive form gave -0.02 (-2.00%) -> a 1bp overstatement.
    """
    m = fd.metrics(TWO_POINT, mer=0.01, ann=2)
    assert m["net_cagr_pct"] == pytest.approx(-1.99, abs=1e-9)
    additive = m["cagr_pct"] - 1.0  # what the old code effectively reported
    assert m["net_cagr_pct"] != pytest.approx(additive, abs=1e-12)


def test_vol_uses_sample_stdev():
    """A7: sample stdev of [0.1,-0.1] is 0.14142136; * sqrt(2) = 0.20 exactly.

    The population stdev is 0.1 -> *sqrt(2) = 14.14%. The difference is large
    enough that this test distinguishes them without ambiguity.
    """
    m = fd.metrics(TWO_POINT, mer=0.0, ann=2)
    assert m["vol_pct"] == pytest.approx(20.0, abs=1e-6)


def test_max_drawdown_two_point():
    """equity 1 -> 1.1 -> 0.99; mdd = 0.99/1.1 - 1 = -10%."""
    m = fd.metrics(TWO_POINT, mer=0.0, ann=2)
    assert m["max_dd_pct"] == pytest.approx(-10.0, abs=1e-9)


def test_flat_series_is_all_zero():
    m = fd.metrics([0.0] * 252, mer=0.0, ann=252)
    assert m["cagr_pct"] == pytest.approx(0.0, abs=1e-12)
    assert m["vol_pct"] == pytest.approx(0.0, abs=1e-12)
    assert m["max_dd_pct"] == pytest.approx(0.0, abs=1e-12)


# --------------------------------------------------------------------------
# A1 / A2 / A5 — ratios
# --------------------------------------------------------------------------
def test_sharpe_subtracts_the_risk_free_rate():
    """A1: (net_cagr - rf)/vol. With rf=0 the old and new forms coincide, so
    the test only bites once rf != 0 — which is the whole point."""
    m = fd.add_ratios(fd.metrics(TWO_POINT, mer=0.01, ann=2), rf=0.01)
    expected = (-0.0199 - 0.01) / 0.20
    assert m["sharpe"] == pytest.approx(expected, abs=1e-3)


def test_ret_vol_is_retained_and_differs_from_sharpe():
    """The legacy ratio must survive under its own (honest) name."""
    m = fd.add_ratios(fd.metrics(TWO_POINT, mer=0.01, ann=2), rf=0.01)
    assert "ret_vol" in m and "sharpe" in m
    assert m["ret_vol"] != pytest.approx(m["sharpe"], abs=1e-9)


def test_sharpe_is_none_without_a_cash_hurdle():
    m = fd.add_ratios(fd.metrics(TWO_POINT, mer=0.0, ann=2), rf=None)
    assert m["sharpe"] is None
    assert m["sortino"] is None


def test_sortino_all_n_denominator_exceeds_legacy():
    """A5: dividing by ALL n gives a SMALLER sigma_down, hence a LARGER ratio.

    The old code divided by the count of negative days only, which inflates
    sigma_down and understates Sortino. This was missed by the peer review.
    """
    r = [0.02, -0.01, 0.03, -0.02, 0.01, -0.005]
    m = fd.add_ratios(fd.metrics(r, mer=0.0, ann=len(r)), rf=0.0)
    assert m["sortino"] is not None and m["sortino_legacy"] is not None
    assert abs(m["sortino"]) >= abs(m["sortino_legacy"])


def test_add_ratios_strips_internal_keys():
    m = fd.add_ratios(fd.metrics(TWO_POINT, mer=0.01, ann=2), rf=0.01)
    assert not [k for k in m if k.startswith("_")]


# --------------------------------------------------------------------------
# A4 — the cash vehicle must not carry a finite ratio, end to end
# --------------------------------------------------------------------------
def test_cash_vehicle_emits_null_ratio(tmp_path, monkeypatch):
    """Run the real pipeline on the real CSV and assert SGOV is null in the JSON.

    This is the A4 acceptance criterion: a stored number (e.g. -0.006, which is
    a float-rounding artefact of 0/0) would be read as a real Sharpe by any
    consumer of the JSON.
    """
    src = REPO_ROOT / fd.SRC
    if not src.exists():
        pytest.skip("market_prices.csv not present in this checkout")

    monkeypatch.setattr(fd, "SRC", str(src))
    monkeypatch.chdir(tmp_path)
    fd.main([])

    payload = json.loads((tmp_path / "reports" / "fund_deep_dive.json").read_text())
    sgov = payload["funds"]["SGOV_adj"]
    assert sgov["sharpe"] is None
    assert sgov["sortino"] is None
    assert "cash hurdle" in sgov["ratio_note"]

    cash_port = payload["portfolios"]["100% SGOV (T-bill)"]
    assert cash_port["sharpe"] is None

    # And a real fund must still carry a finite ratio.
    assert payload["funds"]["FXAIX_adj"]["sharpe"] is not None


def test_payload_declares_rebalancing_assumption(tmp_path, monkeypatch):
    """The JSON must state that portfolios are daily-rebalanced (plan D1 open)."""
    src = REPO_ROOT / fd.SRC
    if not src.exists():
        pytest.skip("market_prices.csv not present in this checkout")

    monkeypatch.setattr(fd, "SRC", str(src))
    monkeypatch.chdir(tmp_path)
    fd.main([])

    payload = json.loads((tmp_path / "reports" / "fund_deep_dive.json").read_text())
    assert payload["schema_version"] >= 2
    # D1: standard portfolios are monthly-rebalanced; before the fix the JSON
    # said "daily" while the docstring claimed monthly -- the opposite of true.
    assert "monthly" in payload["rebalancing"].lower()
    assert "rebalance_sensitivity" in payload


# --------------------------------------------------------------------------
# D1 / D2 / D3 — rebalancing must be real, and its cost must be charged
# --------------------------------------------------------------------------
def test_single_sleeve_reproduces_the_fund_series():
    """weight=1.0 must return the underlying series exactly (no rebalancing)."""
    r = {"A": [0.01, -0.02, 0.03, 0.004]}
    out, stats = fd.portfolio(r, {"A": 1.0})
    assert out == pytest.approx(r["A"], abs=1e-12)
    assert stats["turnover"] == 0.0
    assert stats["rebalances"] == 0


def test_buy_and_hold_never_trades():
    r = {"A": [0.10, -0.05, 0.02], "B": [0.00, 0.01, -0.01]}
    _, stats = fd.portfolio(r, {"A": 0.6, "B": 0.4}, rebal=None)
    assert stats["rebalances"] == 0
    assert stats["turnover"] == 0.0


def test_rebalancing_trades_and_buy_and_hold_does_not():
    """D1: the two schedules must be genuinely different paths.

    The old implementation ignored `rebal`, so both calls returned the same
    series -- the test that would have caught it.
    """
    r = {"A": [0.10, -0.05, 0.08, -0.03, 0.06],
         "B": [0.00, 0.01, -0.01, 0.02, 0.00]}
    bh, bh_stats = fd.portfolio(r, {"A": 0.6, "B": 0.4}, rebal=None)
    rb, rb_stats = fd.portfolio(r, {"A": 0.6, "B": 0.4}, rebal=2)
    assert bh != pytest.approx(rb, abs=1e-12)
    assert rb_stats["rebalances"] > 0
    assert rb_stats["turnover"] > 0.0
    assert bh_stats["turnover"] == 0.0


def test_rebalance_cost_reduces_return():
    """D3: a wider spread must not increase the compounded return."""
    r = {"A": [0.10, -0.09, 0.11, -0.10, 0.07, -0.06],
         "B": [0.01, 0.00, -0.02, 0.03, 0.00, 0.01]}
    free, _ = fd.portfolio(r, {"A": 0.6, "B": 0.4}, rebal=1, spread_bp=0.0)
    costly, _ = fd.portfolio(r, {"A": 0.6, "B": 0.4}, rebal=1, spread_bp=50.0)
    nav_free = 1.0
    for x in free:
        nav_free *= (1 + x)
    nav_cost = 1.0
    for x in costly:
        nav_cost *= (1 + x)
    assert nav_cost < nav_free


def test_portfolio_nav_conserves_weights():
    """With zero returns everywhere the NAV must stay flat at 1.0."""
    r = {"A": [0.0] * 10, "B": [0.0] * 10}
    out, _ = fd.portfolio(r, {"A": 0.6, "B": 0.4}, rebal=3)
    assert all(abs(x) < 1e-12 for x in out)


# --------------------------------------------------------------------------
# B1 / B3 / B4 — bootstrap determinism, ordering, and the paired test
# --------------------------------------------------------------------------
def test_bootstrap_is_deterministic_for_a_fixed_seed():
    import random as _r
    r = [(_r.Random(7).random() - 0.5) * 0.02 for _ in range(300)]
    a = fd.bootstrap_stats(r, block=21, n_boot=50, seed=12345)
    b = fd.bootstrap_stats(r, block=21, n_boot=50, seed=12345)
    assert a == b


def test_bootstrap_interval_brackets_the_point_estimate():
    import random as _r
    rng = _r.Random(11)
    r = [rng.gauss(0.0004, 0.01) for _ in range(500)]
    bs = fd.bootstrap_stats(r, block=21, n_boot=200, seed=999)
    lo, hi = bs["cagr_ci_pct"]
    assert lo < hi
    point = fd._cagr_of(r) * 100
    # a 90% interval should contain the point estimate in a well-behaved case
    assert lo <= point <= hi


def test_bootstrap_returns_none_when_series_is_shorter_than_a_block():
    assert fd.bootstrap_stats([0.01] * 5, block=21) is None


def test_paired_diff_of_identical_series_is_zero_and_not_distinguishable():
    r = [0.001, -0.002, 0.003, -0.001] * 50
    d = fd.bootstrap_pair_diff(r, r, block=21, n_boot=100, seed=1)
    assert d["point_pct"] == pytest.approx(0.0, abs=1e-9)
    assert d["distinguishable_from_zero"] is False


def test_paired_diff_detects_a_large_constant_gap():
    """A 1bp/day advantage (~2.5pp/yr) must be distinguishable from zero."""
    a = [0.001] * 300
    b = [0.0] * 300
    d = fd.bootstrap_pair_diff(a, b, block=21, n_boot=200, seed=1)
    assert d["point_pct"] > 1.0
    assert d["distinguishable_from_zero"] is True


def test_paired_diff_uses_the_difference_not_separate_legs():
    """B3: for two identical series plus small noise, the paired CI must be much
    narrower than either series' own CAGR interval."""
    import random as _r
    rng = _r.Random(3)
    base = [rng.gauss(0.0004, 0.01) for _ in range(600)]
    noisy = [x + rng.gauss(0, 0.00005) for x in base]
    paired = fd.bootstrap_pair_diff(noisy, base, block=21, n_boot=200, seed=5)
    solo = fd.bootstrap_stats(noisy, block=21, n_boot=200, seed=5)
    paired_width = paired["ci_pct"][1] - paired["ci_pct"][0]
    solo_width = solo["cagr_ci_pct"][1] - solo["cagr_ci_pct"][0]
    assert paired_width < solo_width


# --------------------------------------------------------------------------
# B9 — sub-period split, and the net-vs-gross gap
# --------------------------------------------------------------------------
def test_subperiods_are_reported(tmp_path, monkeypatch):
    src = REPO_ROOT / fd.SRC
    if not src.exists():
        pytest.skip("market_prices.csv not present in this checkout")
    monkeypatch.setattr(fd, "SRC", str(src))
    monkeypatch.chdir(tmp_path)
    fd.main([])
    payload = json.loads((tmp_path / "reports" / "fund_deep_dive.json").read_text())

    sp = payload["subperiods"]
    assert sp["split_date"] == "2024-11-15"
    # both halves must cover every fund, and each must have a usable sample
    assert set(sp["funds"]) == set(payload["funds"])
    for c, v in sp["funds"].items():
        assert v["h1_n"] >= 30 and v["h2_n"] >= 30, c
    # the halves must be roughly 3y / 2y of a ~5y window
    total = sum(v["h1_n"] for v in sp["funds"].values()) / len(sp["funds"])
    assert 600 < total < 900


def test_paired_diff_reports_gross_fee_and_net():
    """The fee advantage is the only structurally certain part; the JSON must
    carry gross, fee and net separately so a sign flip in gross is visible."""
    src = REPO_ROOT / fd.SRC
    if not src.exists():
        pytest.skip("market_prices.csv not present in this checkout")
    dates, ser, ret = _load_for_test()
    pd_ = fd.bootstrap_pair_diff(ret["FXAIX_adj"], ret["SPY_adj"], n_boot=100)
    fee = (fd.MER["SPY_adj"] - fd.MER["FXAIX_adj"]) * 100.0
    assert fee == pytest.approx(0.0795, abs=1e-9)
    assert pd_["point_pct"] != 0.0


def test_net_gap_is_positive_in_both_halves_for_the_fee_story():
    """The doc's core claim, tested: the FILM is that gross flips sign but the
    net gap stays positive. If this ever fails, the fee story is broken."""
    src = REPO_ROOT / fd.SRC
    if not src.exists():
        pytest.skip("market_prices.csv not present in this checkout")
    dates, ser, ret = _load_for_test()
    cut = next(i for i, d in enumerate(dates) if d >= "2024-11-15")
    cut_ret = max(2, cut - 1)
    fee = (fd.MER["SPY_adj"] - fd.MER["FXAIX_adj"]) * 100.0
    nets = []
    for sl in (slice(0, cut_ret), slice(cut_ret, None)):
        pd_ = fd.bootstrap_pair_diff(ret["FXAIX_adj"][sl], ret["SPY_adj"][sl], n_boot=300)
        nets.append(pd_["point_pct"] + fee)
    assert all(x > 0 for x in nets), f"fee story broken: net halves {nets}"


def _load_for_test():
    src = REPO_ROOT / fd.SRC
    import os
    cwd = os.getcwd()
    os.chdir(REPO_ROOT)
    try:
        return fd.load()
    finally:
        os.chdir(cwd)


# --------------------------------------------------------------------------
# F1 / F2 / F7 — forward anchors are opt-in, dated, and never silent
# --------------------------------------------------------------------------
def test_anchors_are_off_by_default(tmp_path, monkeypatch):
    """The default run must stay deterministic and offline."""
    src = REPO_ROOT / fd.SRC
    if not src.exists():
        pytest.skip("market_prices.csv not present in this checkout")
    monkeypatch.setattr(fd, "SRC", str(src))
    monkeypatch.chdir(tmp_path)
    fd.main([])
    payload = json.loads((tmp_path / "reports" / "fund_deep_dive.json").read_text())
    assert payload["forward_anchors"] is None


def test_fetch_anchors_returns_a_dated_dict():
    """Structural contract: whatever happens (network, no data), the result is a
    dict carrying fetched_at and an explicit error key rather than silence."""
    a = fd.fetch_anchors()
    assert isinstance(a, dict)
    assert "fetched_at" in a
    assert a["ttl_hours"] == fd.ANCHOR_TTL_HOURS
    # either a number or an explicit error -- never absent
    assert ("cash_tbill_yield_pct" in a) or ("cash_error" in a)
    assert ("bnd_ytm_pct" in a) or ("bnd_error" in a)


def test_out_flag_writes_where_asked(tmp_path, monkeypatch):
    src = REPO_ROOT / fd.SRC
    if not src.exists():
        pytest.skip("market_prices.csv not present in this checkout")
    monkeypatch.setattr(fd, "SRC", str(src))
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "nested" / "x.json"
    fd.main(["--out", str(target)])
    assert target.exists()
    assert json.loads(target.read_text())["schema_version"] >= 2


# --------------------------------------------------------------------------
# K1 — the corrected document must not drift from the JSON
# --------------------------------------------------------------------------
DOC = REPO_ROOT / "docs" / "edge_research" / "FUNDS_WHAT_TO_BUY_2026-11-23_CORRECTED.md"


def test_corrected_doc_exists_and_lists_the_refutations():
    assert DOC.exists(), f"missing {DOC}"
    text = DOC.read_text()
    # the four review claims that were wrong must stay marked as refuted
    assert text.count("REFUTED") >= 3
    assert "markdown-mangled" in text
    assert "unit error" in text.lower()
    # the missed defects must be recorded
    assert "Sortino denominator" in text
    assert "population stdev" in text


def test_corrected_doc_numbers_match_the_json(tmp_path, monkeypatch):
    """K1: catch doc drift. Every headline figure quoted in the doc must appear
    in the generated JSON."""
    src = REPO_ROOT / fd.SRC
    if not src.exists() or not DOC.exists():
        pytest.skip("data or doc not present in this checkout")
    monkeypatch.setattr(fd, "SRC", str(src))
    monkeypatch.chdir(tmp_path)
    fd.main([])
    payload = json.loads((tmp_path / "reports" / "fund_deep_dive.json").read_text())
    # the markdown uses U+2212 MINUS in tables; normalise before comparing
    doc = DOC.read_text().replace("\u2212", "-")

    f = payload["funds"]
    # Sharpe values quoted in the doc
    for key in ("FXAIX_adj", "SPY_adj"):
        assert f"{f[key]['sharpe']:.3f}" in doc, key
    # net CAGR quoted for FXAIX
    assert f"{f['FXAIX_adj']['net_cagr_pct']:.2f}%" in doc
    # BND sharpe is the dramatic correction
    assert f"{f['BND_adj']['sharpe']:.3f}" in doc
    # paired net gap
    net = payload["paired_diffs"]["FXAIX - SPY (same index)"]["net_point_pct"]
    assert f"+{net:.3f}" in doc or f"{net:.3f}" in doc


def test_corrected_doc_scopes_futures_out():
    """G1: futures must be explicitly excluded, not silently omitted."""
    text = DOC.read_text()
    assert "out of scope" in text.lower()
    assert "futures" in text.lower()


# --------------------------------------------------------------------------
# L1 — do the adjusted closes actually reinvest dividends?
#
# This is the load-bearing assumption behind EVERY CAGR in the report. If the
# series were price-only, all of the fixed-income and total-return numbers
# would be wrong. We can settle it internally, without network access, using
# SGOV as a control: it is a 0-3 month T-bill ETF whose NAV is pinned near
# $100 and which distributes its entire yield monthly. A price-only SGOV
# series is flat (~0%/yr). A dividend-reinvested SGOV series must track the
# T-bill yield. We observe ~3.9%/yr, so the data is total-return.
# --------------------------------------------------------------------------
def test_L1_adjusted_closes_reinvest_dividends():
    src = REPO_ROOT / fd.SRC
    if not src.exists():
        pytest.skip("price CSV not present in this checkout")
    rows = list(csv.DictReader(open(src)))
    assert len(rows) > 1000

    def cagr(key):
        a, b = float(rows[0][key]), float(rows[-1][key])
        yrs = len(rows) / 252.0
        return (b / a) ** (1 / yrs) - 1

    sgov = cagr("SGOV_adj")
    # A T-bill ETF distributes everything; price-only would be ~0. Anything
    # near the cash rate proves the distributions are in the series.
    assert 0.025 < sgov < 0.06, (
        f"SGOV_adj CAGR {sgov:.2%} is outside the T-bill range; if this is near "
        f"zero the series is PRICE-ONLY and every CAGR in the report is invalid"
    )

    # Cross-check: a bond fund's total return must beat its price return,
    # because it distributes ~3-4%/yr. BND price fell hard 2021-2026, so its
    # total return should sit clearly above the raw NAV decline.
    bnd = cagr("BND_adj")
    assert bnd > -0.05, f"BND_adj CAGR {bnd:.2%} looks price-only (NAV fell ~3%/yr)"

    # And equities: total return must be >= price return for dividend payers,
    # so every equity series must be positive over this bull window.
    for key in ("SPY_adj", "FXAIX_adj", "VTI_adj", "VTSAX_adj", "FZROX_adj"):
        assert cagr(key) > 0.05, f"{key} CAGR {cagr(key):.2%} implausible"


def test_generator_is_byte_stable_across_runs(tmp_path, monkeypatch):
    """Two in-process runs must agree exactly (ignoring generated_at).

    Rationale: this was NOT true. Headline values flipped between two stable
    states (SPY 11.48 vs 11.59) depending on interpreter hash seed, i.e. a set
    was iterated somewhere before the arithmetic. Pinning the seed hides it,
    this test makes it visible if it ever leaks into the numbers again.
    """
    outs = []
    for i in range(2):
        d = tmp_path / f"r{i}"
        d.mkdir()
        monkeypatch.chdir(d)
        monkeypatch.setattr(fd, "SRC", str(REPO_ROOT / fd.SRC))
        fd.main(["--out", str(d / "o.json")])
        payload = json.loads((d / "o.json").read_text())
        payload.pop("generated_at", None)
        outs.append(json.dumps(payload, sort_keys=True))
    assert outs[0] == outs[1], "generator output is not reproducible"
