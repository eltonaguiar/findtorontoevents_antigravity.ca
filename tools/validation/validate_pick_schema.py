"""
tools/validation/validate_pick_schema.py — M-046 pick payload schema validator.
Run: python tools/validation/validate_pick_schema.py [pick_json_file]
Exit 0 = all picks pass schema. Exit 1 = schema violations found.

Default input: alpha_engine/data/active_picks.json
"""
import json
import sys
import os

REQUIRED_FIELDS = [
    "symbol",
    "asset_class",
    "source_system",
    "strategy",
    "score",
    "confidence",
    "status",
    "direction",
    "entry_price",
    "take_profit",
    "stop_loss",
    "timestamp",
]

VALID_ASSET_CLASSES = {"CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF", "BOND", "FUTURES"}
VALID_DIRECTIONS = {"LONG", "SHORT"}
VALID_STATUSES = {"OPEN", "CLOSED", "CANCELLED"}


def _validate_pick(pick, idx):
    """Validate a single pick dict. Returns a list of violation strings."""
    violations = []

    if not isinstance(pick, dict):
        return [f"Pick #{idx}: not a dict (got {type(pick).__name__})"]

    symbol_label = pick.get("symbol") or f"pick#{idx}"

    # --- required fields presence ---
    for field in REQUIRED_FIELDS:
        if field not in pick:
            violations.append(f"[{symbol_label}] missing required field: {field!r}")

    # --- score: int, 0-100 ---
    score = pick.get("score")
    if score is not None:
        try:
            score_int = int(score)
            if not (0 <= score_int <= 100):
                violations.append(
                    f"[{symbol_label}] score out of range [0,100]: {score!r}"
                )
        except (TypeError, ValueError):
            violations.append(
                f"[{symbol_label}] score not convertible to int: {score!r}"
            )

    # --- confidence: float or None, if present must be in [0.0, 1.0] ---
    confidence = pick.get("confidence")
    if confidence is not None:
        try:
            conf_float = float(confidence)
            if not (0.0 <= conf_float <= 1.0):
                violations.append(
                    f"[{symbol_label}] confidence out of range [0.0,1.0]: {confidence!r}"
                )
        except (TypeError, ValueError):
            violations.append(
                f"[{symbol_label}] confidence not convertible to float: {confidence!r}"
            )

    # --- asset_class ---
    asset_class = pick.get("asset_class")
    if asset_class is not None and str(asset_class).upper() not in VALID_ASSET_CLASSES:
        violations.append(
            f"[{symbol_label}] invalid asset_class {asset_class!r}; "
            f"must be one of {sorted(VALID_ASSET_CLASSES)}"
        )

    # --- direction ---
    direction = pick.get("direction")
    if direction is not None and str(direction).upper() not in VALID_DIRECTIONS:
        violations.append(
            f"[{symbol_label}] invalid direction {direction!r}; "
            f"must be one of {sorted(VALID_DIRECTIONS)}"
        )

    # --- status ---
    status = pick.get("status")
    if status is not None and str(status).upper() not in VALID_STATUSES:
        violations.append(
            f"[{symbol_label}] invalid status {status!r}; "
            f"must be one of {sorted(VALID_STATUSES)}"
        )

    # --- entry_price, take_profit, stop_loss: float > 0 ---
    for price_field in ("entry_price", "take_profit", "stop_loss"):
        val = pick.get(price_field)
        if val is not None:
            try:
                fval = float(val)
                if fval <= 0:
                    violations.append(
                        f"[{symbol_label}] {price_field} must be > 0, got {val!r}"
                    )
            except (TypeError, ValueError):
                violations.append(
                    f"[{symbol_label}] {price_field} not convertible to float: {val!r}"
                )

    return violations


def validate_file(path):
    """Load JSON file, validate each pick, print violations, return (pass_count, fail_count)."""
    if not os.path.exists(path):
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            print(f"ERROR: invalid JSON in {path}: {exc}", file=sys.stderr)
            sys.exit(1)

    if isinstance(data, dict):
        # Some files wrap the list under a key
        picks = data.get("picks") or data.get("active_picks") or data.get("data") or []
        if not picks and isinstance(data, dict):
            # Try flat dict-of-picks or list-of-picks at top level
            picks = list(data.values()) if all(isinstance(v, dict) for v in data.values()) else []
    elif isinstance(data, list):
        picks = data
    else:
        print(f"ERROR: unexpected JSON structure in {path}: {type(data).__name__}", file=sys.stderr)
        sys.exit(1)

    pass_count = 0
    fail_count = 0
    all_violations = []

    for idx, pick in enumerate(picks):
        violations = _validate_pick(pick, idx)
        if violations:
            fail_count += 1
            all_violations.extend(violations)
        else:
            pass_count += 1

    total = pass_count + fail_count
    print(f"Validated {total} pick(s) from: {path}")
    print(f"  PASS: {pass_count}  |  FAIL: {fail_count}")

    if all_violations:
        print(f"\nSchema violations ({len(all_violations)} total):")
        for v in all_violations:
            print(f"  - {v}")
        return pass_count, fail_count

    print("\nAll picks pass schema.")
    return pass_count, fail_count


def main():
    # Resolve repo root relative to this file's location
    this_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(this_dir))  # tools/validation -> tools -> repo

    default_path = os.path.join(repo_root, "alpha_engine", "data", "active_picks.json")

    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        input_path = default_path

    pass_count, fail_count = validate_file(input_path)
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
