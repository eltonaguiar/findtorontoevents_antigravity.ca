from audit_trail.stamp_pick_quality import stamp_picks


def _base_pick():
    return {
        "strategy": "s1",
        "symbol": "AAPL",
        "entry_price": 100.0,
        "take_profit": 106.0,
        "stop_loss": 97.0,
        "direction": "LONG",
        "confidence": 0.85,
        "elite_score": 70,
    }


def test_dsr_negative_blocks_proven_promotion():
    p = _base_pick()
    p["dsr"] = -0.25
    stats = {"s1": {"n": 20, "wr": 0.70, "avg_pnl": 0.02}}
    summary = stamp_picks([p], stats, dry_run=True)
    assert p["trust_tier"] == "WATCH"
    assert "dsr_lt_zero" in p["trust_promotion_block_reason"]
    assert summary["dsr_promotions_blocked"] == 1


def test_dsr_non_negative_keeps_proven_promotion():
    p = _base_pick()
    p["dsr"] = 0.10
    stats = {"s1": {"n": 20, "wr": 0.70, "avg_pnl": 0.02}}
    summary = stamp_picks([p], stats, dry_run=True)
    assert p["trust_tier"] == "PROVEN"
    assert summary["dsr_promotions_blocked"] == 0


# ---------------------------------------------------------------------------
# Wave-2 regression: DSR-missing / DSR-None must preserve legacy behavior.
# The DSR gate at audit_trail/stamp_pick_quality.py:369 is gated on
# `dsr is not None`, so absent / None DSR must not flip a PROVEN pick to
# demoted, must not raise, and must not increment dsr_promotions_blocked.
# ---------------------------------------------------------------------------


def test_dsr_missing_keeps_legacy_promotion_behavior_for_promoted_pick():
    """Pick that legacy logic would PROMOTE — no `dsr` key at all.

    Strategy stats clear the PROVEN gate (n=20 >= 10, wr=0.70 >= 0.55).
    With DSR absent, _extract_dsr returns None, the gate is skipped, and
    legacy WR/N path stamps PROVEN.
    """
    p = _base_pick()
    assert "dsr" not in p
    stats = {"s1": {"n": 20, "wr": 0.70, "avg_pnl": 0.02}}
    summary = stamp_picks([p], stats, dry_run=True)
    assert p["trust_tier"] == "PROVEN"
    assert "trust_promotion_block_reason" not in p
    assert summary["dsr_promotions_blocked"] == 0


def test_dsr_explicit_none_keeps_legacy_behavior():
    """Pick with `dsr=None` must behave identically to dsr-absent."""
    p = _base_pick()
    p["dsr"] = None
    stats = {"s1": {"n": 20, "wr": 0.70, "avg_pnl": 0.02}}
    summary = stamp_picks([p], stats, dry_run=True)
    assert p["trust_tier"] == "PROVEN"
    assert "trust_promotion_block_reason" not in p
    assert summary["dsr_promotions_blocked"] == 0


def test_dsr_missing_does_not_raise_on_demoted_pick():
    """Pick that legacy logic would NOT promote — DSR field absent.

    With n=4 wr=0.20 the strategy fails PROVEN (n<10) and WATCH (n<5),
    landing in MONITOR (n>=MONITOR_N=3). Goal: confirm the function runs
    cleanly without AttributeError/KeyError when DSR is absent on a
    non-promoted pick, and the legacy demoted tier is stamped.
    """
    p = _base_pick()
    assert "dsr" not in p
    stats = {"s1": {"n": 4, "wr": 0.20, "avg_pnl": -0.01}}
    summary = stamp_picks([p], stats, dry_run=True)
    assert p["trust_tier"] == "MONITOR"
    assert "trust_promotion_block_reason" not in p
    assert summary["dsr_promotions_blocked"] == 0


def test_dsr_missing_via_extra_dict_keeps_legacy_behavior():
    """`extra` dict present but with no DSR keys — _extract_dsr still returns None."""
    p = _base_pick()
    p["extra"] = {"unrelated_field": 42}
    stats = {"s1": {"n": 20, "wr": 0.70, "avg_pnl": 0.02}}
    summary = stamp_picks([p], stats, dry_run=True)
    assert p["trust_tier"] == "PROVEN"
    assert summary["dsr_promotions_blocked"] == 0
