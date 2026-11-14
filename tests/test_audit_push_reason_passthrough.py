"""Regression tests — emitters must not drop the pick rationale.

2026-10-04 incident
-------------------
Every ``*_audit_push.py`` emitter rebuilt its pick from a fixed 8-key dict
(symbol / direction / entry_price / take_profit / stop_loss / confidence /
strategy / timestamp). That ``normalize()`` step discarded the human-readable
``reason``, so ``at_raw_picks.raw_payload`` carried no rationale and the
``/audit`` row tooltip — which renders a "Why now:" block from ``p.reason`` —
came up empty for every pick emitted through those systems.

Verified live before the fix: all 30 AlphaEngine picks recorded 2026-10-04 had
``JSON_LENGTH(raw_payload) = 8`` with no reason-ish key, while the upstream
``alpha_engine/data/active_picks.json`` carried ~200 fields per pick including a
populated ``reason``.

These tests pin the passthrough so it cannot silently regress again.
"""
from __future__ import annotations

import importlib
import json

import pytest

from audit_trail.pick_reason import (
    DEFAULT_MAX_LEN,
    extract_reason,
    with_pick_reason,
)

# ---------------------------------------------------------------------------
# Realistic upstream pick (shape taken from alpha_engine/data/active_picks.json)
# ---------------------------------------------------------------------------
UPSTREAM_PICK = {
    "id": "regime_accumulation::BTCUSDT::2026-10-04",
    "strategy": "regime_accumulation",
    "symbol": "BTCUSDT",
    "direction": "LONG",
    "entry_price": 84497.21,
    "take_profit": 90834.5,
    "stop_loss": 80694.84,
    "confidence": 0.855,
    "timestamp": "2026-10-04T02:04:46+00:00",
    "reason": (
        "Residual momentum #2: beta=1.28, residual_7d=-2.3%, residual_14d=27.9%, "
        "RSI=64. Blitz et al. (2011 JFE): pure alpha after beta removal."
    ),
    "confluence_strategies": ["regime_accumulation", "ttm_squeeze_carter"],
    "concept_family": "momentum",
    "rsi_at_entry": 64.0,
    "volume_ratio": 1.4,
}

# ---------------------------------------------------------------------------
# The 10 emitters and how to call each one's normalizer
# name -> (module path, callable name, passes_source_system)
# ---------------------------------------------------------------------------
EMITTERS = {
    "alpha_engine": ("alpha_engine.audit_push", "normalize", False),
    "breakout_arena": ("breakout_arena.audit_push", "normalize_pick", True),
    "coinglass_strategies": ("coinglass_strategies.audit_push", "normalize", False),
    "crypto_ml_edge": ("crypto_ml_edge.audit_push", "normalize", False),
    "crypto_signal_engine": ("crypto_signal_engine.audit_push", "normalize", False),
    "kimi": ("KIMI_RISEOFTHECLAW.audit_push", "normalize", False),
    "mercury2": ("mercury2.audit_push", "normalize", False),
    "ml_battleground": ("ml_battleground.audit_push", "normalize", False),
    "predictions": ("predictions.audit_push", "normalize", False),
    "signal_aggregator": ("signal_aggregator.audit_push", "normalize", False),
}


def _load_emitter(name):
    mod_path, fn_name, passes_source = EMITTERS[name]
    try:
        mod = importlib.import_module(mod_path)
    except Exception as exc:  # pragma: no cover - optional emitter deps
        pytest.skip(f"{mod_path} not importable in this env: {exc}")
    return getattr(mod, fn_name), passes_source


def _call(fn, passes_source, pick):
    return fn(pick, "test_system") if passes_source else fn(pick)


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------

def test_extract_reason_prefers_reason_key():
    assert extract_reason({"reason": "  why  "}) == "why"


def test_extract_reason_falls_back_through_chain():
    for key in ("signal_reason", "entry_reason", "raw_reason", "reasoning",
                "confluence_reason", "notes"):
        assert extract_reason({key: f"via {key}"}) == f"via {key}"


def test_antigravity_tooltip_is_not_treated_as_entry_reason():
    """It is a safety-protocol note rendered in its own tooltip row."""
    assert extract_reason({"antigravity_tooltip": "Under Threshold"}) == ""
    out = with_pick_reason({}, {"antigravity_tooltip": "Under Threshold"})
    assert "reason" not in out
    assert out["antigravity_tooltip"] == "Under Threshold"


def test_extract_reason_precedence_order():
    pick = {"reason": "first", "signal_reason": "second"}
    assert extract_reason(pick) == "first"


def test_extract_reason_reads_nested_parents():
    assert extract_reason({"extra": {"reason": "nested"}}) == "nested"
    assert extract_reason({"audit": {"reasoning": "nested2"}}) == "nested2"
    assert extract_reason({"metadata": {"notes": "nested3"}}) == "nested3"


def test_extract_reason_ignores_non_scalar_values():
    # A dict/list/None/bool is not a rationale
    for bad in ({"a": 1}, ["x"], None, True):
        assert extract_reason({"reason": bad}) == ""


def test_extract_reason_returns_empty_when_absent():
    assert extract_reason({}) == ""
    assert extract_reason({"symbol": "BTCUSDT"}) == ""
    assert extract_reason(None) == ""


def test_extract_reason_truncates_to_max_len():
    long = "x" * (DEFAULT_MAX_LEN + 500)
    assert len(extract_reason({"reason": long})) == DEFAULT_MAX_LEN
    assert len(extract_reason({"reason": long}, max_len=25)) == 25


def test_with_pick_reason_adds_reason_and_evidence():
    out = with_pick_reason({"symbol": "BTCUSDT"}, UPSTREAM_PICK)
    assert out["reason"] == UPSTREAM_PICK["reason"]
    assert out["confluence_strategies"] == UPSTREAM_PICK["confluence_strategies"]
    assert out["concept_family"] == "momentum"
    # untouched keys preserved
    assert out["symbol"] == "BTCUSDT"


def test_with_pick_reason_is_additive_only():
    """An existing non-empty value must win."""
    out = with_pick_reason({"reason": "mine"}, {"reason": "theirs"})
    assert out["reason"] == "mine"


def test_with_pick_reason_no_reason_upstream_leaves_payload_clean():
    out = with_pick_reason({"symbol": "X"}, {"symbol": "X"})
    assert "reason" not in out


def test_with_pick_reason_never_raises_on_junk():
    assert with_pick_reason({"a": 1}, None) == {"a": 1}
    assert with_pick_reason(None, {"reason": "x"}) is None
    assert with_pick_reason({"a": 1}, "not-a-dict") == {"a": 1}


def test_with_pick_reason_output_is_json_serializable():
    """raw_payload lands in a MySQL JSON column — must serialize."""
    out = with_pick_reason({"symbol": "BTCUSDT"}, UPSTREAM_PICK)
    assert json.loads(json.dumps(out))["reason"] == UPSTREAM_PICK["reason"]


# ---------------------------------------------------------------------------
# Emitter integration tests — the actual regression
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(EMITTERS))
def test_every_emitter_normalize_preserves_reason(name):
    """THE regression: normalize() must not drop the rationale."""
    fn, passes_source = _load_emitter(name)
    out = _call(fn, passes_source, UPSTREAM_PICK)
    assert out.get("reason") == UPSTREAM_PICK["reason"], (
        f"{name}.normalize() dropped the rationale — at_raw_picks.raw_payload "
        f"will carry no 'reason' and the /audit tooltip will be empty"
    )


@pytest.mark.parametrize("name", sorted(EMITTERS))
def test_every_emitter_output_is_json_serializable(name):
    fn, passes_source = _load_emitter(name)
    out = _call(fn, passes_source, UPSTREAM_PICK)
    json.loads(json.dumps(out))  # must not raise


@pytest.mark.parametrize("name", sorted(EMITTERS))
def test_every_emitter_still_returns_the_core_fields(name):
    """Passthrough must not disturb the columns at_raw_picks needs."""
    fn, passes_source = _load_emitter(name)
    out = _call(fn, passes_source, UPSTREAM_PICK)
    for key in ("symbol", "direction", "entry_price", "take_profit",
                "stop_loss", "confidence", "strategy", "timestamp"):
        assert key in out, f"{name}.normalize() lost required key {key!r}"


@pytest.mark.parametrize("name", sorted(EMITTERS))
def test_every_emitter_handles_pick_without_reason(name):
    """A reasonless pick must normalize exactly as before (no 'reason' key)."""
    fn, passes_source = _load_emitter(name)
    bare = {k: v for k, v in UPSTREAM_PICK.items()
            if k not in ("reason", "confluence_strategies", "concept_family")}
    out = _call(fn, passes_source, bare)
    assert not str(out.get("reason") or "").strip()
