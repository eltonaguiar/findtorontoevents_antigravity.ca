#!/usr/bin/env python3
"""
copy_trader_intel/outcome_resolver.py

Resolves copy-trader pick outcomes by checking live price against TP/SL.
Runs in copy-trader-forward-test.yml after portfolio tracker.

Binance API failover per CLAUDE.md: api, api1, api2, api3 mirrors.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("ct_outcome_resolver")

DATA_DIR = Path(__file__).parent / "data"

# Files containing copy-trader active picks and their matching closed archives.
ACTIVE_LEDGER_TO_CLOSED_ARCHIVE = {
    DATA_DIR / "active_picks.json": DATA_DIR / "closed_trades.json",
    DATA_DIR / "highscore_active_picks.json": DATA_DIR / "highscore_closed_picks.json",
    DATA_DIR / "clone_active_picks.json": DATA_DIR / "clone_closed_picks.json",
    DATA_DIR / "consensus_active_picks.json": DATA_DIR / "consensus_closed_picks.json",
}
PICK_FILES = list(ACTIVE_LEDGER_TO_CLOSED_ARCHIVE.keys())

# Binance REST mirrors (CLAUDE.md failover rule: always 3+)
BINANCE_SPOT_MIRRORS = [
    "https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
    "https://api1.binance.com/api/v3/ticker/price?symbol={symbol}",
    "https://api2.binance.com/api/v3/ticker/price?symbol={symbol}",
    "https://api3.binance.com/api/v3/ticker/price?symbol={symbol}",
]
BINANCE_FAPI_MIRROR = "https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"

# Strategies whose picks should be ignored (confirmed bad actors)
# binance_smart_money: 45.8% WR, -0.21% PnL — net loser, illiquid alts
# hl_funding_fade: 0/11 = 0% WR — consistently wrong on funding rate reversals
BLOCKED_STRATEGIES = {
    "binance_smart_money",
    "hl_funding_fade",
}

# Max age for an OPEN pick before force-expiring (72 hours)
MAX_HOLD_HOURS = 72


def _parse_timestamp(raw_ts: str | None) -> datetime | None:
    """Parse date/time strings into timezone-aware UTC datetimes."""
    if not raw_ts:
        return None
    try:
        ts = str(raw_ts).strip()
        if not ts:
            return None
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        if " " in ts and "T" not in ts:
            ts = ts.replace(" ", "T", 1)
        parsed = datetime.fromisoformat(ts)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _is_open_status(status: str | None) -> bool:
    return str(status or "OPEN").upper() in {"", "OPEN", "ACTIVE"}


def _pick_identity_key(pick: dict) -> str:
    raw_id = str(pick.get("id") or "").strip()
    if raw_id:
        return raw_id
    parts = [
        str(pick.get("source_system") or "").strip().lower(),
        str(pick.get("strategy") or "").strip().lower(),
        str(pick.get("symbol") or "").strip().upper(),
        str(pick.get("direction") or pick.get("signal_type") or "").strip().upper(),
        str(
            pick.get("open_time")
            or pick.get("entry_date")
            or pick.get("timestamp")
            or pick.get("generated_at")
            or ""
        ).strip(),
        str(pick.get("entry_price") or "").strip(),
    ]
    return "::".join(parts)


def _load_closed_archive(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [p for p in data if isinstance(p, dict)]
    except Exception as e:
        log.error("Failed to read closed archive %s: %s", path, e)
    return []


def _merge_closed_picks(existing: list[dict], additions: list[dict]) -> list[dict]:
    merged = {}
    for pick in existing:
        merged[_pick_identity_key(pick)] = pick
    for pick in additions:
        merged[_pick_identity_key(pick)] = pick
    return sorted(
        merged.values(),
        key=lambda p: str(p.get("closed_at") or p.get("timestamp") or p.get("open_time") or ""),
        reverse=True,
    )


def _write_active_ledger(filepath: Path, wrapper, picks: list) -> None:
    if wrapper:
        wrapper[0][wrapper[1]] = picks
        if "total_consensus_picks" in wrapper[0]:
            wrapper[0]["total_consensus_picks"] = len(picks)
        output = wrapper[0]
    else:
        output = picks
    filepath.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")


def _append_closed_archive(filepath: Path, picks: list[dict]) -> int:
    if not picks:
        return 0
    existing = _load_closed_archive(filepath)
    merged = _merge_closed_picks(existing, picks)
    filepath.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    return max(0, len(merged) - len(existing))


def _fetch_price(symbol: str) -> float | None:
    """Fetch current price from Binance spot with failover."""
    symbol = symbol.upper().replace("-PERP", "").replace("/", "")
    for url_template in BINANCE_SPOT_MIRRORS:
        url = url_template.format(symbol=symbol)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read())
                price = float(data.get("price", 0))
                if price > 0:
                    return price
        except Exception:
            time.sleep(0.2)
    # Try futures (perps) as fallback
    try:
        url = BINANCE_FAPI_MIRROR.format(symbol=symbol)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
            price = float(data.get("price", 0))
            if price > 0:
                return price
    except Exception:
        pass
    return None


def _resolve_pick(pick: dict) -> dict:
    """
    Check if an OPEN pick has hit TP or SL.
    Returns the pick (possibly updated with outcome).
    """
    if not _is_open_status(pick.get("status", "OPEN")):
        return pick

    strategy = pick.get("strategy", "")
    if strategy in BLOCKED_STRATEGIES:
        log.info("Expiring blocked strategy pick: %s %s", strategy, pick.get("symbol", ""))
        expired = pick.copy()
        expired["status"] = "EXPIRED"
        expired["exit_reason"] = "blocked_strategy"
        expired["exit_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return expired

    symbol = pick.get("symbol", "")
    if not symbol:
        return pick

    entry = _safe_float(pick.get("entry_price"))
    tp = _safe_float(pick.get("take_profit"))
    sl = _safe_float(pick.get("stop_loss"))
    direction = pick.get("direction", pick.get("signal_type", "LONG")).upper()
    if direction in ("BUY", "LONG"):
        direction = "LONG"
    else:
        direction = "SHORT"

    if not entry or not tp or not sl:
        return pick  # can't resolve without prices

    # Force-expire very old picks
    open_time_str = pick.get("open_time") or pick.get("entry_date") or ""
    if open_time_str:
        try:
            ts = _parse_timestamp(open_time_str)
            if ts is None:
                raise ValueError("unparseable timestamp")
            age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
            if age_hours > MAX_HOLD_HOURS:
                current = _fetch_price(symbol)
                pnl = _calc_pnl(entry, current or entry, direction)
                pick.update({
                    "status": "CLOSED",
                    "exit_reason": "TIME_EXPIRED",
                    "outcome": "WON" if pnl > 0 else "LOST" if pnl < 0 else "FLAT",
                    "exit_price": current or entry,
                    "pnl_pct": round(pnl, 4),
                    "closed_at": datetime.now(timezone.utc).isoformat(),
                })
                log.info("TIME_EXPIRED %s %s %s → pnl=%.4f", symbol, direction, strategy, pnl)
                return pick
        except Exception:
            pass

    current = _fetch_price(symbol)
    if current is None:
        log.warning("Could not fetch price for %s", symbol)
        return pick

    # Check TP / SL hit
    outcome = None
    if direction == "LONG":
        if current >= tp:
            outcome = "TP_HIT"
            exit_price = tp
            pnl = (tp - entry) / entry
        elif current <= sl:
            outcome = "SL_HIT"
            exit_price = sl
            pnl = (sl - entry) / entry
        else:
            pick["unrealized_pnl_pct"] = round((current - entry) / entry, 4)
    else:  # SHORT
        if current <= tp:
            outcome = "TP_HIT"
            exit_price = tp
            pnl = (entry - tp) / entry
        elif current >= sl:
            outcome = "SL_HIT"
            exit_price = sl
            pnl = (entry - sl) / entry
        else:
            pick["unrealized_pnl_pct"] = round((entry - current) / entry, 4)

    if outcome:
        result = "WON" if outcome == "TP_HIT" else "LOST"
        pick.update({
            "status": "CLOSED",
            "exit_reason": outcome,
            "outcome": result,
            "exit_price": round(exit_price, 6),
            "pnl_pct": round(pnl, 4),
            "closed_at": datetime.now(timezone.utc).isoformat(),
            "forward_validated": True,
        })
        # GP-10: Slippage tracking — compare trader's entry vs our entry
        original_entry = pick.get("original_trader_entry")
        if original_entry is not None:
            try:
                orig = float(original_entry)
                if orig > 0 and entry > 0:
                    slippage = abs(entry - orig) / orig
                    pick["slippage_pct"] = round(slippage * 100, 4)
                    # Compute what the trader's PnL would have been
                    if direction == "LONG":
                        their_pnl = (exit_price - orig) / orig
                    else:
                        their_pnl = (orig - exit_price) / orig
                    pick["trader_pnl_pct"] = round(their_pnl, 4)
                    pick["pnl_gap_pct"] = round(their_pnl - pnl, 4)
                    if slippage > 0.02:
                        log.warning("HIGH SLIPPAGE %s: our_entry=%.6f trader_entry=%.6f slip=%.2f%%",
                                    symbol, entry, orig, slippage * 100)
            except (TypeError, ValueError):
                pass
        log.info("%s %s %s %s → %s pnl=%.4f", symbol, direction, strategy, outcome, result, pnl)
    else:
        log.debug("OPEN %s %s current=%.6f entry=%.6f tp=%.6f sl=%.6f",
                  symbol, direction, current, entry, tp, sl)

    return pick


def _safe_float(val) -> float | None:
    try:
        v = float(val)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def _calc_pnl(entry: float, current: float, direction: str) -> float:
    if direction == "LONG":
        return (current - entry) / entry
    return (entry - current) / entry


def _process_file(filepath: Path) -> tuple[int, int, int, int]:
    """Process one active-ledger file. Returns (total, resolved, migrated, archived)."""
    if not filepath.exists():
        log.debug("File not found: %s", filepath)
        return 0, 0, 0, 0

    try:
        raw = filepath.read_text(encoding="utf-8")
        data = json.loads(raw)
    except Exception as e:
        log.error("Failed to read %s: %s", filepath, e)
        return 0, 0, 0, 0

    # Handle both list format and dict-with-picks format
    if isinstance(data, list):
        picks = data
        wrapper = None
    elif isinstance(data, dict):
        # Find the picks list - could be 'picks', 'activePicks', etc.
        for key in ("picks", "activePicks", "active_picks", "signals"):
            if key in data and isinstance(data[key], list):
                picks = data[key]
                wrapper = (data, key)
                break
        else:
            log.warning("No picks list found in %s", filepath)
            return 0, 0, 0, 0
    else:
        return 0, 0, 0, 0

    total = len(picks)
    resolved = 0
    migrated = 0
    updated_open = []
    archived_closed = []

    for pick in picks:
        if not isinstance(pick, dict):
            updated_open.append(pick)
            continue
        original_open = _is_open_status(pick.get("status", "OPEN"))
        pick = _resolve_pick(pick) if original_open else pick
        if _is_open_status(pick.get("status", "OPEN")):
            updated_open.append(pick)
            continue
        archived_closed.append(pick)
        if original_open:
            resolved += 1
        else:
            migrated += 1

    archive_path = ACTIVE_LEDGER_TO_CLOSED_ARCHIVE[filepath]

    try:
        _write_active_ledger(filepath, wrapper, updated_open)
        archived = _append_closed_archive(archive_path, archived_closed)
        log.info(
            "Wrote %s: %d/%d resolved, %d migrated, %d open remain, %d archived to %s",
            filepath.name,
            resolved,
            total,
            migrated,
            len(updated_open),
            archived,
            archive_path.name,
        )
    except Exception as e:
        log.error("Failed to write %s: %s", filepath, e)
        return total, resolved, migrated, 0

    return total, resolved, migrated, archived


def main() -> None:
    log.info("=== Copy Trader Outcome Resolver ===")
    total_all = 0
    resolved_all = 0
    migrated_all = 0
    archived_all = 0

    for fp in PICK_FILES:
        t, r, m, a = _process_file(fp)
        total_all += t
        resolved_all += r
        migrated_all += m
        archived_all += a

    log.info(
        "Done: %d/%d picks resolved, %d stale closed rows migrated, %d archived entries updated across %d files",
        resolved_all,
        total_all,
        migrated_all,
        archived_all,
        len(PICK_FILES),
    )


if __name__ == "__main__":
    main()
