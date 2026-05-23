#!/usr/bin/env python3
"""Validate worker JSON output against tools/swarm/schema_review.json.

Exit 0 = valid. Exit non-zero = invalid (errors printed to stderr).

Usage:
    python tools/swarm/schema_validate.py path/to/output.json
    python tools/swarm/schema_validate.py -                    # stdin
    python tools/swarm/schema_validate.py path --strictness lenient

Strictness levels:
    strict (default) — required fields + enums + blocking/major evidence >=10 chars
    lenient          — required fields + enums + blocking/major evidence >=1 char
    off              — required fields ONLY (no enum, no evidence checks)

Falls back to a hand-rolled validator when `jsonschema` is unavailable.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO / "tools" / "swarm" / "schema_review.json"

VALID_STRICTNESS = ("strict", "lenient", "off")


def _load(path: str) -> dict:
    if path == "-":
        return json.loads(sys.stdin.read())
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _strip_strict_only_constraints(schema: dict) -> dict:
    """Recursively drop `if`/`then`/`else` blocks (additive in strict mode only)."""
    if isinstance(schema, dict):
        out = {}
        for k, v in schema.items():
            if k in ("if", "then", "else"):
                continue
            out[k] = _strip_strict_only_constraints(v)
        return out
    if isinstance(schema, list):
        return [_strip_strict_only_constraints(x) for x in schema]
    return schema


def _strip_enum_constraints(schema: dict) -> dict:
    """Recursively drop `enum` constraints. Used for strictness=off."""
    if isinstance(schema, dict):
        out = {}
        for k, v in schema.items():
            if k == "enum":
                continue
            out[k] = _strip_enum_constraints(v)
        return out
    if isinstance(schema, list):
        return [_strip_enum_constraints(x) for x in schema]
    return schema


def _validate_with_jsonschema(data: dict, schema: dict, strictness: str = "strict") -> list[str]:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return _validate_handrolled(data, schema, strictness)
    # Always strip if/then/else for non-strict modes.
    if strictness != "strict":
        schema = _strip_strict_only_constraints(schema)
    if strictness == "off":
        # off => required fields only, drop enum constraints too.
        schema = _strip_enum_constraints(schema)
    errors: list[str] = []
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        errors.append(f"{list(e.absolute_path)}: {e.message}")
    return errors


def _validate_handrolled(data: dict, schema: dict, strictness: str = "strict") -> list[str]:
    errors: list[str] = []
    # Required-fields check fires at every strictness level.
    for k in schema.get("required", []):
        if k not in data:
            errors.append(f"missing required key: {k}")
    props = schema.get("properties", {})

    if strictness != "off":
        # Enum checks fire at strict + lenient.
        if "verdict" in data and "verdict" in props:
            if data["verdict"] not in props["verdict"]["enum"]:
                errors.append(f"verdict: '{data['verdict']}' not in {props['verdict']['enum']}")
        if "confidence" in data and "confidence" in props:
            if data["confidence"] not in props["confidence"]["enum"]:
                errors.append(f"confidence: '{data['confidence']}' not in {props['confidence']['enum']}")
        if "fabrication_risk" in data:
            fr = data["fabrication_risk"]
            if not isinstance(fr, dict):
                errors.append("fabrication_risk must be object")
            else:
                for rk in ("level", "notes"):
                    if rk not in fr:
                        errors.append(f"fabrication_risk.{rk} missing")
                if fr.get("level") not in (None, "LOW", "MEDIUM", "HIGH"):
                    errors.append(f"fabrication_risk.level: '{fr['level']}' invalid")

        # Concerns structural + evidence checks. strict => >=10 chars; lenient => non-empty.
        evidence_min = 10 if strictness == "strict" else 1
        for i, c in enumerate(data.get("concerns", [])):
            for rk in ("severity", "claim", "evidence", "requested_fix"):
                if rk not in c:
                    errors.append(f"concerns[{i}].{rk} missing")
            if c.get("severity") not in ("blocking", "major", "minor", "question"):
                errors.append(f"concerns[{i}].severity: '{c.get('severity')}' invalid")
            if c.get("severity") in ("blocking", "major"):
                ev = (c.get("evidence") or "").strip()
                if len(ev) < evidence_min:
                    errors.append(
                        f"concerns[{i}]: severity='{c['severity']}' requires evidence "
                        f">={evidence_min} char(s) (got {len(ev)})"
                    )
        for i, s in enumerate(data.get("strengths", [])):
            if not (s.get("evidence") or "").strip():
                errors.append(f"strengths[{i}]: missing evidence")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate worker JSON against schema_review.json")
    parser.add_argument("path", help="Path to JSON file, or '-' for stdin")
    parser.add_argument(
        "--strictness",
        choices=VALID_STRICTNESS,
        default="strict",
        help="strict (default) | lenient | off",
    )
    args = parser.parse_args()

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        data = _load(args.path)
    except json.JSONDecodeError as e:
        print(f"invalid json: {e}", file=sys.stderr)
        return 3
    errs = _validate_with_jsonschema(data, schema, args.strictness)
    if errs:
        for e in errs:
            print(f"FAIL {e}", file=sys.stderr)
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
