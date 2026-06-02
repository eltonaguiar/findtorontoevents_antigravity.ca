"""OHLCV / pick-frame admissibility rules (EAGLE2 §3.1)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class AdmissibilityRules:
    drop_disputed_rows: bool = True
    drop_duplicates: bool = True


def enforce_data_rules(df: pd.DataFrame, rules: AdmissibilityRules | None = None) -> pd.DataFrame:
    """Filter disputed rows and duplicates; require core columns."""
    rules = rules or AdmissibilityRules()
    required = {
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source_id",
        "resolver_dispute_flag",
        "duplicate_key",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    out = df.sort_values("timestamp").copy()

    if rules.drop_duplicates:
        out = out.drop_duplicates(subset=["duplicate_key"], keep="last")

    if rules.drop_disputed_rows:
        out = out[~out["resolver_dispute_flag"].astype(bool)].copy()

    if out["timestamp"].dt.tz is None:
        out["timestamp"] = out["timestamp"].dt.tz_localize("UTC")

    return out
