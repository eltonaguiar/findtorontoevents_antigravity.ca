"""Tripwire (2026-11-22 provenance repair): a quoted cost metric MUST exist in
the artifact it cites.

Why this exists
    The M1 equity-cost write-up quoted 12.07 bp round-trip while its committed
    artifact recorded ``n_symbols_with_data: 0`` / ``SKIPPED_OFFLINE_OR_NO_KEY``.
    The number was real (it reproduces exactly from yfinance 1-min bars) but the
    artifact could not support it, because a key-gated re-run overwrote the good
    run. A reader could not tell a real measurement from a fabricated one.

    This is deliberately small: one validator plus three tests. It is not a
    framework. It fails loudly on the exact shape of that defect.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = ROOT / "reports" / "equity_cost_measurement" / "equity_cost_20261122.json"
CLASS_ARTIFACT = ROOT / "reports" / "equity_cost_measurement" / "class_cost_20261122.json"
WRITEUP = ROOT / "updates" / "2026-11-22-m1-equity-cost-measurement.md"
CLASS_WRITEUP = ROOT / "updates" / "2026-11-22-m3-cost-triage.md"
TOL_BP = 0.01          # the write-up rounds 12.0749 -> 12.07
CLASS_TOL_BP = 0.01    # the write-up rounds 6.7122 -> 6.71, 8.0325 -> 8.03, 6.7938 -> 6.79


def assert_quoted_metric_supported(artifact: dict, quoted_bp: float,
                                   tol_bp: float = TOL_BP) -> bool:
    """A quoted spread figure is only allowed if the artifact contains it.

    Rejects: no per-symbol data, a null median, or a median that does not match
    the quoted value. Returns True when supported, raises AssertionError otherwise.
    """
    agg = artifact.get("spread_aggregate") or {}
    n = agg.get("n_symbols_with_data")
    median = agg.get("range_upper_bound_rt_bp_median")
    assert isinstance(n, int) and n > 0, (
        f"a {quoted_bp}bp figure is quoted but the artifact has "
        f"n_symbols_with_data={n!r} - no spread data to support it")
    assert median is not None, (
        f"a {quoted_bp}bp figure is quoted but the artifact median is null")
    assert abs(float(median) - float(quoted_bp)) <= tol_bp, (
        f"quoted {quoted_bp}bp but the artifact median is {float(median):.4f}bp "
        f"(tolerance {tol_bp}bp)")
    return True


@pytest.mark.skipif(not ARTIFACT.exists(), reason="M1 artifact not present")
def test_committed_artifact_contains_the_quoted_median():
    art = json.loads(ARTIFACT.read_text())
    # the value the M1 write-up quotes, rounded to 2 dp
    assert_quoted_metric_supported(art, 12.07)
    agg = art["spread_aggregate"]
    assert agg["n_symbols_with_data"] == 13
    assert len(agg["per_name_rt_bp"]) == 13
    assert agg["provenance_self_check"] == "PASS"


@pytest.mark.skipif(not WRITEUP.exists(), reason="M1 write-up not present")
def test_every_quoted_round_trip_bp_in_the_writeup_is_supported():
    art = json.loads(ARTIFACT.read_text())
    text = WRITEUP.read_text()
    # the write-up's canonical quoted RT bound
    m = re.search(r"\*\*(12\.07) bp\*\* round trip", text)
    assert m, "expected the 12.07 bp round-trip quote in the M1 write-up"
    assert_quoted_metric_supported(art, float(m.group(1)))


def test_tripwire_rejects_the_stale_artifact_shape():
    """Fail-before proof: the shape actually committed at 22:49:21Z is rejected.

    Kept inline so the regression is durable and needs no network or /tmp file.
    """
    stale = {
        "spread": {"status": "SKIPPED_OFFLINE_OR_NO_KEY"},
        "spread_aggregate": {
            "n_symbols_with_data": 0,
            "range_upper_bound_rt_bp_median": None,
        },
    }
    with pytest.raises(AssertionError, match="n_symbols_with_data"):
        assert_quoted_metric_supported(stale, 12.07)


def test_tripwire_rejects_a_real_count_but_wrong_median():
    """A non-zero count is not enough - the value must match too."""
    wrong = {"spread_aggregate": {"n_symbols_with_data": 13,
                                  "range_upper_bound_rt_bp_median": 8.31}}
    with pytest.raises(AssertionError, match="median is 8.3100bp"):
        assert_quoted_metric_supported(wrong, 12.07)


# --------------------------------------------------------------------------
# DEFECT 2 extension (2026-11-22): a quoted CLASS bp figure must have a matching
# artifact with a non-empty ``classes`` object and a positive per-class count.
# The class figures (ETF 6.71 / INDEX 8.03 / MEME DOGE 6.79) were quoted while a
# reader believed the artifact was empty; this makes that belief a hard failure.
# --------------------------------------------------------------------------

CLASS_QUOTES = {"ETF": 6.71, "INDEX_alias_of_ETF": 8.03}


def assert_quoted_class_metric_supported(artifact: dict, class_name: str,
                                        quoted_bp: float,
                                        tol_bp: float = CLASS_TOL_BP,
                                        per_name: str = None) -> bool:
    """A quoted class figure is only allowed if the artifact supports it.

    Rejects: an empty/missing ``classes`` object, a class with no data, a class
    whose median does not match the quote, and (when ``per_name`` is given) a
    per-name value that does not match. Returns True when supported.
    """
    classes = artifact.get("classes") or {}
    assert classes, (
        f"a {quoted_bp}bp class figure is quoted for {class_name} but the artifact "
        f"has an EMPTY classes object - no class data to support it")
    entry = classes.get(class_name)
    assert entry is not None, (
        f"a {quoted_bp}bp figure is quoted for {class_name} but the artifact has no "
        f"such class (has {sorted(classes)})")
    agg = entry.get("aggregate") or {}
    n = agg.get("n_names_with_data")
    assert isinstance(n, int) and n > 0, (
        f"a {quoted_bp}bp figure is quoted for {class_name} but n_names_with_data={n!r}")
    if per_name is not None:
        pn = (agg.get("per_name_rt_bp") or {}).get(per_name)
        assert pn is not None, f"no per-name value for {per_name} in {class_name}"
        assert abs(float(pn) - float(quoted_bp)) <= tol_bp, (
            f"quoted {quoted_bp}bp for {per_name} but the artifact has {float(pn):.4f}bp")
        return True
    median = (agg.get("range_ub_rt_bp") or {}).get("median")
    assert median is not None, f"a {quoted_bp}bp figure is quoted but {class_name} median is null"
    assert abs(float(median) - float(quoted_bp)) <= tol_bp, (
        f"quoted {quoted_bp}bp for {class_name} but the artifact median is "
        f"{float(median):.4f}bp (tolerance {tol_bp}bp)")
    return True


@pytest.mark.skipif(not CLASS_ARTIFACT.exists(), reason="M3 class artifact not present")
def test_class_artifact_is_not_empty_and_supports_the_quoted_medians():
    art = json.loads(CLASS_ARTIFACT.read_text())
    assert art.get("classes"), "class_cost artifact has an empty classes object"
    for cls, bp in CLASS_QUOTES.items():
        assert_quoted_class_metric_supported(art, cls, bp)
    # MEME: only DOGE-USD is quotable; SHIB is tick-truncated and must not be a 0.00 quote
    assert_quoted_class_metric_supported(art, "MEME", 6.79, per_name="DOGE-USD")
    meme = art["classes"]["MEME"]["aggregate"]["per_name_rt_bp"]
    assert meme.get("SHIB-USD") == 0.0, "SHIB's 0.00 bp is truncation, expected exactly 0.0"


@pytest.mark.skipif(not CLASS_WRITEUP.exists(), reason="M3 write-up not present")
def test_every_class_bp_in_the_m3_writeup_is_supported():
    art = json.loads(CLASS_ARTIFACT.read_text())
    text = CLASS_WRITEUP.read_text()
    # ETF and INDEX are quoted as CLASS MEDIANS; MEME's 6.79 is DOGE's PER-NAME
    # value (the MEME class median is 3.40 because SHIB's truncated 0.00 is in it,
    # so quoting 6.79 as a class median would itself be a defect).
    for cls, bp, label, name in (("ETF", 6.71, r"\*\*6\.71\*\*", None),
                                ("INDEX_alias_of_ETF", 8.03, r"\*\*8\.03\*\*", None),
                                ("MEME", 6.79, r"6\.79", "DOGE-USD")):
        assert re.search(label, text), f"expected {bp} bp quoted in the M3 write-up"
        assert_quoted_class_metric_supported(art, cls, bp, per_name=name)


def test_meme_class_median_is_not_quoted_as_a_spread():
    """SHIB's 0.00 (tick-truncated) drags MEME's class median to 3.40 - not a quote."""
    art = json.loads(CLASS_ARTIFACT.read_text())
    meme = art["classes"]["MEME"]
    shib = meme["per_name"]["SHIB-USD"]
    assert shib["range_upper_bound_rt_bp"]["median"] == 0.0
    assert shib["tick_truncation"]["frac_zero_range"] > 0.5, (
        "SHIB's zero is only allowed to be called truncation if zero-range bars dominate")
    assert meme["aggregate"]["range_ub_rt_bp"]["median"] != pytest.approx(6.79, abs=0.01), (
        "MEME's class median must not be the DOGE per-name value")


def test_tripwire_rejects_the_empty_classes_shape():
    """Fail-before proof: an empty ``classes`` object is rejected even with a plausible quote."""
    empty = {"classes": {}}
    with pytest.raises(AssertionError, match="EMPTY classes object"):
        assert_quoted_class_metric_supported(empty, "ETF", 6.71)


def test_tripwire_rejects_a_class_with_null_aggregate():
    """PENNY_STOCK is blocked (aggregate null) - a figure for it must be rejected."""
    nullagg = {"classes": {"PENNY_STOCK": {"aggregate": None}}}
    with pytest.raises(AssertionError, match="n_names_with_data"):
        assert_quoted_class_metric_supported(nullagg, "PENNY_STOCK", 6.71)
