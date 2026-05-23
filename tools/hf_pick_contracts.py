"""
Typed pick contracts for HF validation pipelines (Mercury 2 / quant hygiene).

Requires: pip install pydantic>=2  (see tools/requirements-hf-validation.txt)

Use for optional strict validation of dict rows before tier logic — does not
replace production dict-based pipelines; opt-in at tool boundaries.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

try:
    from pydantic import BaseModel, ConfigDict, Field, field_validator
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "hf_pick_contracts requires pydantic>=2. Install: pip install -r tools/requirements-hf-validation.txt"
    ) from e


def _parse_ts(v: Any) -> Optional[datetime]:
    if v is None or v == "":
        return None
    s = str(v).replace("Z", "+00:00").replace(" EST", "")
    if "T" not in s and " " in s:
        s = s.replace(" ", "T")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


class PickValidationRow(BaseModel):
    """Loose contract aligned with audit / closed-pick JSON (not every field required)."""

    symbol: str = Field(..., min_length=1)
    asset_class: Optional[str] = None
    strategy: Optional[str] = None
    score: Optional[float] = Field(default=None)
    confidence: Optional[float] = Field(default=None)
    trust_score: Optional[float] = Field(default=None)
    trust_score_1: Optional[float] = Field(default=None)
    strat_fwd_wr: Optional[float] = Field(default=None)
    forward_wr: Optional[float] = Field(default=None)
    direction: Optional[str] = None
    status: Optional[str] = None
    pnl_pct: Optional[float] = None
    timestamp: Optional[str] = None
    entry_time: Optional[str] = None
    created_at: Optional[str] = None

    @field_validator("score", mode="before")
    @classmethod
    def score_bounds(cls, v: Any) -> Any:
        if v is None:
            return v
        try:
            f = float(v)
        except (TypeError, ValueError):
            return v
        if f > 100:
            return min(100.0, f)
        return f

    model_config = ConfigDict(extra="allow")


def validate_pick_dict(row: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Return (ok, errors). Extra keys allowed; core fields validated when present.
    """
    errs: list[str] = []
    try:
        PickValidationRow.model_validate(row)
    except Exception as e:
        errs.append(str(e))
        return False, errs
    sym = str(row.get("symbol") or "").strip()
    if not sym:
        return False, ["empty symbol"]
    return True, []


def pick_age_days(row: dict[str, Any], *, now: Optional[datetime] = None) -> Optional[float]:
    """Best-effort staleness in days from timestamp-like fields."""
    now = now or datetime.utcnow()
    for key in ("timestamp", "entry_time", "created_at", "opened_at", "generated_at"):
        raw = row.get(key)
        if not raw:
            continue
        dt = _parse_ts(raw)
        if dt is None:
            continue
        try:
            delta = now - dt.replace(tzinfo=None)
            return delta.total_seconds() / 86400.0
        except Exception:
            continue
    return None
