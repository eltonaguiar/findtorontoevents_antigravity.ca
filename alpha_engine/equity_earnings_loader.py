"""Load structured earnings snapshots from data/earnings/<TICKER>/latest.json for PEAD shadow."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
EARNINGS_DIR = REPO_ROOT / "data" / "earnings"

def normalize_ticker(ticker: str) -> str:
    """Normalize ticker by stripping exchange suffixes and handling share classes."""
    if not ticker:
        return ""
    t = ticker.upper().strip()
    # Strip exchange suffixes: AAPL.N, MSFT.O, BRK.B.N
    t = re.sub(r'\.[A-Z]{1,2}$', '', t)
    # Handle share classes: BRK.B -> BRK-B, BF.A -> BF-A
    t = t.replace('.', '-')
    return t

def load_pead_event_for_ticker(
    ticker: str,
    *,
    max_age_days: int = 14,
    assume_guidance_on_beat: bool = False,
) -> Optional[dict[str, Any]]:
    """Fetch the latest PEAD event for a specific ticker from cache."""
    events = load_pead_events_from_earnings_cache(
        max_age_days=max_age_days,
        assume_guidance_on_beat=assume_guidance_on_beat
    )
    norm_target = normalize_ticker(ticker)
    
    # Filter for matching ticker
    matches = [e for e in events if normalize_ticker(e["symbol"]) == norm_target]
    if not matches:
        return None
        
    # Return the most recent one
    return sorted(matches, key=lambda x: x["earnings_date"], reverse=True)[0]

def load_pead_events_from_earnings_cache(
    *,
    max_age_days: int = 14,
    assume_guidance_on_beat: bool = False,
) -> list[dict[str, Any]]:
    """
    Convert data/earnings/*/latest.json rows into PEAD event dicts.

    guidance_raised defaults True on >=5% surprise when assume_guidance_on_beat
    (shadow probation — real filings should replace this later).
    """
    if not EARNINGS_DIR.is_dir():
        return []

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max(1, max_age_days))
    events: list[dict[str, Any]] = []

    for path in sorted(EARNINGS_DIR.glob("*/latest.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("earnings cache read failed %s: %s", path, exc)
            continue

        ticker = str(raw.get("ticker") or path.parent.name).upper().strip()
        if not ticker:
            continue

        history = raw.get("history") or []
        if not isinstance(history, list):
            continue

        for row in history:
            if not isinstance(row, dict):
                continue
            surprise = row.get("surprise_pct")
            eps_actual = row.get("eps_actual")
            eps_estimate = row.get("eps_estimate")
            if surprise is None or eps_actual is None or eps_estimate is None:
                continue
            try:
                surprise_f = float(surprise)
                if surprise_f < 5.0:
                    continue
            except (TypeError, ValueError):
                continue

            ed = row.get("date")
            if not ed:
                continue

            try:
                ed_s = str(ed).replace("Z", "+00:00")
                ed_dt = datetime.fromisoformat(ed_s)
                if ed_dt.tzinfo is None:
                    ed_dt = ed_dt.replace(tzinfo=timezone.utc)
                if ed_dt < cutoff:
                    continue
            except (TypeError, ValueError):
                continue

            guidance = bool(row.get("guidance_raised", False))
            if not guidance and assume_guidance_on_beat:
                guidance = True

            events.append(
                {
                    "symbol": ticker,
                    "earnings_date": ed,
                    "eps_actual": eps_actual,
                    "eps_estimate": eps_estimate,
                    "surprise_pct": surprise_f,
                    "guidance_raised": guidance,
                    "asset_class": "EQUITY",
                    "source": "data/earnings",
                }
            )

    log.info("PEAD earnings cache: %d events from %s", len(events), EARNINGS_DIR)
    return events