"""Canonical envelope schema and validation helpers."""
from __future__ import annotations

import copy
import datetime as dt
import uuid
from typing import Any, Dict, Optional

SCHEMA_VERSION = "cross-pc/v1"
DEFAULT_TTL_SEC = 300
MAX_TTL_SEC = 3600


class ProtocolValidationError(ValueError):
    """Raised when a protocol envelope cannot be validated."""


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtocolValidationError(f"Field '{field_name}' must be a non-empty string.")
    return value.strip()


def _coerce_ttl(value: Any) -> int:
    try:
        ttl = int(value)
    except (TypeError, ValueError) as exc:
        raise ProtocolValidationError("Field 'ttl_sec' must be an integer.") from exc
    if ttl < 1 or ttl > MAX_TTL_SEC:
        raise ProtocolValidationError(f"Field 'ttl_sec' must be between 1 and {MAX_TTL_SEC}.")
    return ttl


def new_envelope(
    *,
    sender: str,
    topic: str,
    payload: Optional[Dict[str, Any]] = None,
    target: str = "",
    trace_id: str = "",
    causation_id: str = "",
    require_ack: bool = False,
    ttl_sec: int = DEFAULT_TTL_SEC,
    debug: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a fresh canonical envelope."""
    normalized_trace = trace_id.strip() if trace_id else uuid.uuid4().hex
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "message_id": str(uuid.uuid4()),
        "trace_id": normalized_trace,
        "causation_id": causation_id.strip(),
        "from": sender.strip(),
        "to": target.strip(),
        "topic": topic.strip(),
        "ts_utc": utc_now_iso(),
        "require_ack": bool(require_ack),
        "ttl_sec": int(ttl_sec),
        "payload": payload or {},
        "debug": debug or {},
    }
    return normalize_envelope(envelope)


def normalize_envelope(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize an inbound envelope."""
    if not isinstance(raw, dict):
        raise ProtocolValidationError("Envelope must be an object.")

    data = copy.deepcopy(raw)
    schema_version = data.get("schema_version", SCHEMA_VERSION)
    if schema_version != SCHEMA_VERSION:
        raise ProtocolValidationError(
            f"Unsupported schema_version '{schema_version}'. Expected '{SCHEMA_VERSION}'."
        )

    message_id = _as_non_empty_str(data.get("message_id"), "message_id")
    trace_id = _as_non_empty_str(data.get("trace_id"), "trace_id")
    sender = _as_non_empty_str(data.get("from"), "from")
    topic = _as_non_empty_str(data.get("topic"), "topic")
    ts_utc = _as_non_empty_str(data.get("ts_utc"), "ts_utc")

    payload = data.get("payload", {})
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ProtocolValidationError("Field 'payload' must be an object.")

    normalized = {
        "schema_version": SCHEMA_VERSION,
        "message_id": message_id,
        "trace_id": trace_id,
        "causation_id": str(data.get("causation_id", "") or "").strip(),
        "from": sender,
        "to": str(data.get("to", "") or "").strip(),
        "topic": topic,
        "ts_utc": ts_utc,
        "require_ack": bool(data.get("require_ack", False)),
        "ttl_sec": _coerce_ttl(data.get("ttl_sec", DEFAULT_TTL_SEC)),
        "payload": payload,
        "debug": data.get("debug", {}) if isinstance(data.get("debug", {}), dict) else {},
    }
    return normalized
