"""v3b Signal Translator — Structured Signal Specification (Pydantic model).

Per `reports/v3b_signal_translator_spec_2026-05-12.md` and
`reports/week1_draft_prs_2026-05-12.md`. Replaces the brittle SMA(50/200)
proxy with a JSON-schema-validated `signal_spec` that the existing
handler registry can dispatch deterministically.

## Why

v3a keyword router (commit a060a87b3c8) routes only 2/14 BOND specs off
the SMA proxy default. Every NO_EDGE verdict across 7 asset classes is
caused by the SMA proxy not parsing natural-language `spec.entry`. v3b
parses arbitrary entry/exit rules into a structured form so the handler
registry can dispatch real signals (pair-strategies, regime-gated entries,
multi-leg sizing).

## Wire-up status (per CLAUDE.md Wire-Up Rule)

PR #1 (this file): schema + validator + handler-registry import path.
**Opt-in sidecar — no production caller yet.** Production wire-in
queued for PR #2 (`research_orchestrator` input path) per
`reports/week1_draft_prs_2026-05-12.md`.

Smoke test:
    python -m tools.research.signal_spec

## Schema version

`v3b/v1` — bumps on any breaking change. Backward-compat reader for
v3a's free-text spec is NOT included here; that lives in the orchestrator
input path so the validator stays strict.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

try:
    from pydantic import BaseModel, Field, field_validator
except ImportError as e:
    raise ImportError(
        "v3b signal_spec requires pydantic. Install: pip install pydantic"
    ) from e


SCHEMA_VERSION = "v3b/v1"


ALLOWED_ASSET_CLASSES = (
    "CRYPTO", "EQUITY", "FOREX", "COMMODITY",
    "ETF", "BOND", "FUTURES", "MEMECOIN", "PENNY_STOCK",
)

ALLOWED_DIRECTIONS = (
    "LONG", "SHORT", "NEUTRAL", "SKIP",
    "PAIR_LONG", "PAIR_SHORT",  # pair-trade extension
)


class Feature(BaseModel):
    """Single feature input to the signal."""
    name: str
    value: Any
    source: Optional[str] = None  # e.g. "yfinance", "binance", "fred", "cot"


class RegimeGate(BaseModel):
    """Optional regime filter. None = no gate (signal fires unconditionally)."""
    vix_max: Optional[float] = None
    dxy_trend: Optional[str] = None  # "RISING" | "FALLING" | "FLAT"
    session_utc: Optional[List[str]] = None  # ["07:00-17:00"] etc.
    hmm_state: Optional[str] = None
    cot_sentiment: Optional[str] = None

    @field_validator("dxy_trend")
    @classmethod
    def _validate_dxy_trend(cls, v):
        if v is None:
            return v
        allowed = {"RISING", "FALLING", "FLAT"}
        if v not in allowed:
            raise ValueError(f"dxy_trend must be one of {allowed}; got {v!r}")
        return v


class SignalSpec(BaseModel):
    """v3b structured signal specification."""

    schema_version: str = Field(default=SCHEMA_VERSION)

    signal_id: str = Field(..., pattern=r"^[a-z0-9_]+$")
    asset_class: str
    direction: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    valid_from: datetime
    valid_to: Optional[datetime] = None

    primary_ticker: str
    secondary_ticker: Optional[str] = None

    regime_gate: Optional[RegimeGate] = None
    features: List[Feature] = Field(default_factory=list)
    rationale: Optional[str] = Field(None, max_length=800)

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, v):
        if v != SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be {SCHEMA_VERSION!r}; got {v!r}"
            )
        return v

    @field_validator("asset_class")
    @classmethod
    def _validate_asset_class(cls, v):
        if v not in ALLOWED_ASSET_CLASSES:
            raise ValueError(
                f"asset_class must be one of {ALLOWED_ASSET_CLASSES}; got {v!r}"
            )
        return v

    @field_validator("direction")
    @classmethod
    def _validate_direction(cls, v):
        if v not in ALLOWED_DIRECTIONS:
            raise ValueError(
                f"direction must be one of {ALLOWED_DIRECTIONS}; got {v!r}"
            )
        return v

    @field_validator("confidence")
    @classmethod
    def _validate_confidence_floor(cls, v):
        # Per Grok 2026-05-12 spec: confidence < 0.4 should be SKIP, not a
        # half-hearted LONG/SHORT. Caller can override by setting
        # direction='SKIP' if they want to keep the row.
        return v

    @field_validator("valid_to")
    @classmethod
    def _validate_valid_to_after_from(cls, v, info):
        if v is None:
            return v
        valid_from = info.data.get("valid_from")
        if valid_from is not None and v <= valid_from:
            raise ValueError("valid_to must be strictly after valid_from")
        return v


def validate(payload: dict) -> SignalSpec:
    """Validate a raw dict against the v3b schema.

    Returns the parsed SignalSpec on success, raises pydantic.ValidationError
    on failure. Callers should log validation errors to v3b_rejects.jsonl
    per the spec document.
    """
    return SignalSpec(**payload)


def _smoke_test():
    """Minimal smoke test. Run via: python -m tools.research.signal_spec"""
    example = {
        "signal_id": "cot_steepener_ctf_20260512",
        "asset_class": "COMMODITY",
        "direction": "LONG",
        "confidence": 0.78,
        "valid_from": "2026-05-12T14:00:00Z",
        "valid_to": "2026-05-19T14:00:00Z",
        "primary_ticker": "CT=F",
        "regime_gate": {
            "vix_max": 22,
            "dxy_trend": "FALLING",
        },
        "features": [
            {"name": "cot_net_position_zscore", "value": 1.84, "source": "CFTC"},
            {"name": "roll_yield_pct", "value": 8.2, "source": "futures_curve"},
            {"name": "seasonality_factor", "value": 1.37, "source": "historical"},
        ],
        "rationale": "Strong commercial net positioning + positive roll yield in backwardation regime",
    }
    spec = validate(example)
    print(f"OK signal_id={spec.signal_id} asset_class={spec.asset_class} "
          f"direction={spec.direction} confidence={spec.confidence}")

    # Negative test — bad direction
    bad = dict(example)
    bad["direction"] = "FOO"
    try:
        validate(bad)
        print("FAIL: bad direction should have raised")
    except Exception as e:
        print(f"OK bad direction rejected: {type(e).__name__}")

    # Negative test — confidence out of range
    bad = dict(example)
    bad["confidence"] = 1.5
    try:
        validate(bad)
        print("FAIL: confidence>1.0 should have raised")
    except Exception as e:
        print(f"OK confidence>1.0 rejected: {type(e).__name__}")

    # Negative test — valid_to before valid_from
    bad = dict(example)
    bad["valid_to"] = "2024-01-01T00:00:00Z"
    try:
        validate(bad)
        print("FAIL: valid_to before valid_from should have raised")
    except Exception as e:
        print(f"OK valid_to-before-valid_from rejected: {type(e).__name__}")


if __name__ == "__main__":
    _smoke_test()
