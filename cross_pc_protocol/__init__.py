"""Cross-PC protocol package (debug-first transport abstraction)."""

from .schema import normalize_envelope, new_envelope, ProtocolValidationError
from .gateway import ProtocolGateway

__all__ = [
    "ProtocolGateway",
    "ProtocolValidationError",
    "new_envelope",
    "normalize_envelope",
]
