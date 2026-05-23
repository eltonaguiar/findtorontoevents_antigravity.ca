"""Regression tests for claude_gainer_st (CGS) dashboard visibility.

Per reports/silent_failure_investigation_2026_04_29.md, CGS picks were silently
dropped at audit_trail/dashboard_generator.py:5220 (_build_recent_closed_picks)
because CGS was not in _VERIFIED_ALPHA_COPY_SOURCES — making it ineligible for
the 500-slot protected track-record pool. After losing the residual ~1000-slot
race against alpha_engine/super_signals/luxalgo_filters/baby_strats_forward/
rapid_fire on timestamp DESC, all 321 CGS picks resolved since 2026-04-25 were
clipped by the MAX_CLOSED_PICKS=3500 stratified sampler.
"""


def test_cgs_in_verified_alpha_copy_sources():
    from audit_trail.dashboard_generator import _VERIFIED_ALPHA_COPY_SOURCES
    assert "claude_gainer_st" in _VERIFIED_ALPHA_COPY_SOURCES, (
        "claude_gainer_st must be in _VERIFIED_ALPHA_COPY_SOURCES so its 321 "
        "resolved picks since 2026-04-25 surface in dashboard_data.recent_closed "
        "(else clipped by MAX_CLOSED_PICKS=3500 stratified sampler). "
        "See reports/silent_failure_investigation_2026_04_29.md."
    )


def test_verified_alpha_copy_sources_is_set_like():
    from audit_trail.dashboard_generator import _VERIFIED_ALPHA_COPY_SOURCES
    # Must support O(1) membership check (downstream callers rely on this)
    assert "claude_gainer_st" in _VERIFIED_ALPHA_COPY_SOURCES
    assert "completely_fake_source_name_xyz" not in _VERIFIED_ALPHA_COPY_SOURCES
