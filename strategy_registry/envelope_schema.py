"""JSON envelope schema for the Strategy Registry."""

REQUIRED_FIELDS = {
    "strategy_id": str,
    "name": str,
    "type": str,
    "source_system": str,
    "backtest_results": dict,
    "tags": dict,
    "generated_at": str,
}

VALID_TYPES = {"dna", "opposite", "web", "ml", "rule", "consensus", "manual"}


def validate_envelope(envelope: dict) -> tuple[bool, list[str]]:
    """Validate a strategy envelope. Returns (ok, list_of_errors)."""
    errors = []

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in envelope:
            errors.append(f"Missing required field: {field}")
        elif not isinstance(envelope[field], expected_type):
            errors.append(f"Field '{field}' must be {expected_type.__name__}, got {type(envelope[field]).__name__}")

    if "type" in envelope and isinstance(envelope["type"], str):
        if envelope["type"] not in VALID_TYPES:
            errors.append(f"Invalid type '{envelope['type']}', must be one of {VALID_TYPES}")

    return (len(errors) == 0, errors)
