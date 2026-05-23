"""
Strict pick dict validation / coercion at ingest boundaries (optional).

Requires ``pydantic`` (see root ``requirements.txt``). If not installed,
``validate_and_coerce_pick`` returns the input dict unchanged with a note.

Environment (copy-trader consensus builder):

- ``PICK_SCHEMA_VALIDATE=1`` — coerce rows through :class:`PickIngestV1` after
  field normalization (see ``copy_trader_intel/consensus_pick_builder.py``).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:
    from pydantic import BaseModel, ConfigDict, model_validator
except ImportError:
    BaseModel = None  # type: ignore[misc, assignment]
    model_validator = None  # type: ignore[misc, assignment]

PYDANTIC_AVAILABLE = BaseModel is not None

if PYDANTIC_AVAILABLE:

    class PickIngestV1(BaseModel):  # type: ignore[misc, valid-type]
        """Versioned ingest schema: core trade fields + passthrough extras."""

        model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

        id: Optional[str] = None
        symbol: Optional[str] = None
        pair: Optional[str] = None
        ticker: Optional[str] = None
        instrument: Optional[str] = None
        direction: Optional[str] = None
        signal_type: Optional[str] = None
        asset_class: Optional[str] = None
        category: Optional[str] = None
        source_system: Optional[str] = None
        strategy: Optional[str] = None
        status: Optional[str] = None
        entry_price: Optional[float] = None
        take_profit: Optional[float] = None
        stop_loss: Optional[float] = None
        confidence: Optional[float] = None
        score: Optional[float] = None
        ml_score: Optional[float] = None
        risk_reward: Optional[float] = None

        @model_validator(mode="after")
        def unify_symbol_aliases(self) -> PickIngestV1:
            if not self.symbol:
                for attr in ("pair", "ticker", "instrument"):
                    v = getattr(self, attr, None)
                    if v:
                        self.symbol = str(v).strip()
                        break
            return self

else:
    PickIngestV1 = None  # type: ignore[misc, assignment]


def validate_and_coerce_pick(raw: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate ``raw`` and return a coerced dict (includes extra keys).

    Returns:
        (ok, messages, result_dict)
    """
    if not PYDANTIC_AVAILABLE or PickIngestV1 is None:
        return True, ["pydantic_not_installed"], dict(raw)
    from pydantic import ValidationError

    try:
        m = PickIngestV1.model_validate(raw)  # type: ignore[union-attr]
        out = m.model_dump(mode="python")
        return True, [], out
    except ValidationError as exc:
        errs = [f"{e.get('loc')}: {e.get('msg')}" for e in exc.errors()]
        return False, errs, dict(raw)


def pick_schema_validate_enabled() -> bool:
    import os

    v = str(os.environ.get("PICK_SCHEMA_VALIDATE", "") or "").strip().lower()
    return v in ("1", "true", "yes", "on")
