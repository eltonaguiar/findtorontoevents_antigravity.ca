"""Resolve binary prediction-market contracts on their actual outcome.

Why this exists
---------------
The /audit pipeline treated Kalshi/Polymarket rows like spot trades: it fetched
a "current price", synthesized a 2.5%/1.5% TP/SL pair, and closed them on price
geometry. A binary contract ("Will X happen?") has no spot price and no
meaningful TP/SL — it settles at 1.0 if the chosen side is correct and 0.0
otherwise. Resolving one on price movement produces a P&L that cannot exist.

This module is the contract-aware path:
  * ``is_contract_pick`` distinguishes a binary contract (market id + side)
    from a *spot trade derived from* prediction-market signals — the latter is
    a normal directional pick and belongs on the price path.
  * ``resolve_contract_pick`` settles from the market outcome when it is known
    (payout 1.0 / 0.0), leaves the pick OPEN while the market is live, and
    expires it with ``pnl_pct=None`` when the expiry passed without an outcome.
    It never invents a P&L.
  * ``load_market_outcomes`` indexes outcome records from whatever local feeds
    exist. Missing feeds simply mean "no outcome yet" — not a zero.

Settlement math (per contract, cost = entry probability):
    win : (1.0 - entry) / entry * 100
    loss: (0.0 - entry) / entry * 100 == -100%
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

ROOT = Path(__file__).resolve().parent.parent

#: Source systems that emit prediction-market-derived picks.
PM_SYSTEMS = frozenset(
    {
        "polymarket_signals",
        "pm_polymarket_re_signals",
        "pm_kalshi_signals",
        "pm_kalshi_re_signals",
        "pm_whale_signals",
        "pm_momentum_signals",
        "prediction_market_consensus",
        "prediction_market_agents",
        "kalshi_signals",
        "pm_macro_expansion",
    }
)

#: A contract pick carries a market identity plus the side being bought.
_MARKET_ID_FIELDS = ("market_id", "market_ticker", "condition_id", "ticker", "slug")
_SIDE_FIELDS = ("contract_side", "outcome", "side", "position")
_EXPIRY_FIELDS = ("end_date", "resolution_date", "expiry", "expiry_ts", "close_time")

#: Local feeds that may carry settled market outcomes.
_DEFAULT_OUTCOME_PATHS = (
    ROOT / "data" / "pm_market_outcomes.json",
    ROOT / "alpha_engine" / "data" / "pm_market_outcomes.json",
    ROOT / "alpha_engine" / "data" / "polymarket_signals.json",
    ROOT / "alpha_engine" / "data" / "kalshi_signals.json",
    ROOT / "prediction_market_agents" / "data" / "pm_market_outcomes.json",
)

#: Directories scanned for any PM feed that happens to carry settlements.
_OUTCOME_GLOBS = (
    ("data", "*polymarket*.json"),
    ("data", "*kalshi*.json"),
    ("data", "pm_market*.json"),
    ("alpha_engine/data", "*polymarket*.json"),
    ("alpha_engine/data", "*kalshi*.json"),
    ("prediction_market_agents/data", "*market*.json"),
)


def candidate_paths() -> list:
    """Every local file that could hold a settled market outcome."""
    seen = []
    for d, pattern in _OUTCOME_GLOBS:
        try:
            for path in sorted((ROOT / d).glob(pattern)):
                if path.is_file() and path not in seen:
                    seen.append(path)
        except OSError:
            continue
    for path in _DEFAULT_OUTCOME_PATHS:
        if path not in seen:
            seen.append(path)
    return seen

_CLOSED = frozenset({"WON", "LOST", "EXPIRED"})


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _market_key(pick: Dict[str, Any]) -> Optional[str]:
    for field in _MARKET_ID_FIELDS:
        value = pick.get(field)
        if value not in (None, ""):
            return str(value).strip()
    return None


def _raw_side(pick: Dict[str, Any]) -> Optional[str]:
    for field in _SIDE_FIELDS:
        value = pick.get(field)
        if value not in (None, ""):
            return str(value).strip().upper()
    # Direction is the fallback: LONG = buying YES, SHORT = buying NO.
    direction = pick.get("direction")
    if direction not in (None, ""):
        return str(direction).strip().upper()
    return None


def normalize_outcome(value: Any) -> Optional[str]:
    """Map an outcome record's resolution to YES / NO."""
    if isinstance(value, bool):
        return "YES" if value else "NO"
    if isinstance(value, (int, float)):
        return "YES" if value else "NO"
    text = str(value or "").strip().upper()
    if text in {"YES", "Y", "TRUE", "1", "WIN", "WON", "RESOLVED_YES"}:
        return "YES"
    if text in {"NO", "N", "FALSE", "0", "LOSS", "LOST", "RESOLVED_NO"}:
        return "NO"
    return None


def contract_side(pick: Dict[str, Any]) -> Optional[str]:
    """Return the YES/NO side being bought, mapping LONG/SHORT when needed."""
    raw = _raw_side(pick)
    if raw is None:
        return None
    if raw in {"YES", "Y", "TRUE", "LONG", "BUY"}:
        return "YES"
    if raw in {"NO", "N", "FALSE", "SHORT", "SELL"}:
        return "NO"
    return None


def is_contract_pick(pick: Dict[str, Any]) -> bool:
    """True only for binary contracts — not spot trades derived from PM signals."""
    if not isinstance(pick, dict):
        return False
    asset_class = str(pick.get("asset_class") or "").upper()
    if asset_class in {"PREDICTION_MARKET", "PREDICTION_MARKETS", "EVENT_CONTRACT"}:
        return True
    return _market_key(pick) is not None and contract_side(pick) is not None


def classify_pick_kind(pick: Dict[str, Any]) -> str:
    """'contract' for binary contracts, 'spot_derived' otherwise (PM-sourced)."""
    return "contract" if is_contract_pick(pick) else "spot_derived"


def pnl_pct_for(entry: float, payout: float) -> Optional[float]:
    """Return per-contract % P&L, or None when entry is not a probability."""
    if entry <= 0 or entry > 1.0:
        return None
    return round((payout - entry) / entry * 100.0, 4)


def _parse_dt(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _expiry(pick: Dict[str, Any], market: Optional[Dict[str, Any]]) -> Optional[datetime]:
    for source in (market or {}, pick):
        for field in _EXPIRY_FIELDS:
            dt = _parse_dt(source.get(field))
            if dt is not None:
                return dt
    return None


def _lookup_market(
    pick: Dict[str, Any], markets: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    if not markets:
        return None
    for field in _MARKET_ID_FIELDS:
        key = pick.get(field)
        if key not in (None, "") and str(key) in markets:
            return markets[str(key)]
    return None


def resolve_contract_pick(
    pick: Dict[str, Any],
    markets: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Settle a binary contract from its market outcome.

    Returns a copy of the pick with ``status`` in {WON, LOST, EXPIRED, OPEN}:
      * outcome known        -> WON/LOST with payout-based ``pnl_pct``
      * expired, no outcome  -> EXPIRED with ``pnl_pct=None`` (never a fake 0)
      * still live           -> OPEN, untouched
    """
    now = now or datetime.now(timezone.utc)
    out = dict(pick)
    out.setdefault("status", "OPEN")
    side = contract_side(pick)
    if side is None:
        out["pm_resolution_status"] = "missing_contract_side"
        return out

    market = _lookup_market(pick, markets) or {}
    outcome = normalize_outcome(
        market.get("outcome")
        or market.get("resolution")
        or market.get("resolved_outcome")
        or pick.get("resolved_outcome")
    )
    entry = _float(pick.get("entry_price"), default=0.0)

    if outcome is not None:
        won = side == outcome
        payout = 1.0 if won else 0.0
        pnl = pnl_pct_for(entry, payout)
        out.update(
            {
                "status": "WON" if won else "LOST",
                "exit_price": payout,
                "exit_reason": "CONTRACT_RESOLVED",
                "closed_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "resolved_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "pnl_pct": pnl,
                "pm_resolution_status": "resolved",
                "pm_resolved_outcome": outcome,
                "pm_contract_side": side,
                "pm_resolution_source": market.get("source") or "market_outcome",
            }
        )
        if pnl is None:
            out["pm_pnl_unavailable_reason"] = "entry_price_not_a_probability"
        return out

    expiry = _expiry(pick, market)
    if expiry is not None and now >= expiry:
        out.update(
            {
                "status": "EXPIRED",
                "exit_price": None,
                "exit_reason": "CONTRACT_UNRESOLVED",
                "closed_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "resolved_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "pnl_pct": None,
                "pm_resolution_status": "awaiting_outcome",
                "pm_contract_side": side,
            }
        )
        return out

    out["pm_resolution_status"] = "open"
    return out


def _records(payload: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("markets", "picks", "active_picks", "signals", "resolved", "outcomes"):
            value = payload.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
        return [payload]
    return []


def index_outcomes(records: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Index outcome records by every market identifier they carry."""
    index: Dict[str, Dict[str, Any]] = {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        outcome = normalize_outcome(
            rec.get("outcome")
            or rec.get("resolution")
            or rec.get("resolved_outcome")
            or rec.get("result")
        )
        if outcome is None:
            continue
        entry = {
            "outcome": outcome,
            "end_date": rec.get("end_date") or rec.get("resolution_date") or rec.get("expiry"),
            "source": rec.get("source") or rec.get("platform") or "local_feed",
        }
        for field in _MARKET_ID_FIELDS + ("id",):
            key = rec.get(field)
            if key not in (None, ""):
                index[str(key)] = entry
    return index


@lru_cache(maxsize=1)
def load_market_outcomes(paths: Optional[tuple] = None) -> Dict[str, Dict[str, Any]]:
    """Load and index settled outcomes from whatever local feeds exist."""
    candidates = [Path(p) for p in paths] if paths else candidate_paths()
    index: Dict[str, Dict[str, Any]] = {}
    for path in candidates:
        try:
            if not path.exists():
                continue
            payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        index.update(index_outcomes(_records(payload)))
    return index
