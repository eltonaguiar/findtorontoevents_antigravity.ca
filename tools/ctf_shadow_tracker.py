"""D-001 CT=F (Cotton #2) COT-filtered shadow PnL tracker.

Accumulates forward paper PnL for CT=F picks that pass COT_STALE_GATE into
alpha_engine/data/ctf_shadow_log.jsonl. Runs daily in CI (or manually).
Never writes to active_picks.json or production paths. Fail-open: 0 picks OK.

60-day validation window per swarm D-001 Option C decision (2026-05-19).
CT=F COT-filtered edge: WR=77.5%, PF=4.69, n=40 (elite subset).

Usage:
    python tools/ctf_shadow_tracker.py [--dry-run] [--summary]
    python tools/ctf_shadow_tracker.py --summary   # just print rolling PnL

Exit codes: 0=success (even if 0 signals — fail-open).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_ACTIVE_PICKS = REPO_ROOT / "alpha_engine" / "data" / "active_picks.json"
_SHADOW_LOG = REPO_ROOT / "alpha_engine" / "data" / "ctf_shadow_log.jsonl"
_VALIDATION_DAYS = 60   # D-001 window
_MAX_HOLD_DAYS = 10     # time-stop: exit if neither TP nor SL hit after N days
_COT_STALE_DAYS = 10    # mirrors COT_STALE_GATE default (M-001)
_PRUNE_DAYS = 90        # discard log entries older than this


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _prune_old(lines: list[str], cutoff_ts: float) -> list[str]:
    kept = []
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
            ts_str = obj.get("_runner_ts", "")
            if ts_str:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
                if ts >= cutoff_ts:
                    kept.append(raw)
            else:
                kept.append(raw)  # no timestamp → keep (defensive)
        except Exception:
            kept.append(raw)
    return kept


def _cot_pass(pick: dict) -> bool:
    """Return True if the pick's COT data is within _COT_STALE_DAYS."""
    cot_date_str = (pick.get("extra") or {}).get("latest_cot_date", "")
    if not cot_date_str:
        return False  # no COT date → gate fails
    try:
        cot_date = datetime.fromisoformat(cot_date_str).date()
        age_days = (datetime.now(timezone.utc).date() - cot_date).days
        return age_days <= _COT_STALE_DAYS
    except Exception:
        return False


def _fetch_ctf_price() -> float | None:
    """Fetch latest CT=F daily close via yfinance. Returns None on failure."""
    try:
        import yfinance as yf  # noqa: PLC0415
        hist = yf.Ticker("CT=F").history(period="5d", interval="1d", auto_adjust=False)
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def _load_existing_log(log_path: Path) -> list[str]:
    if not log_path.exists():
        return []
    return log_path.read_text(encoding="utf-8").splitlines()


def _pick_already_logged(pick_id: str, log_lines: list[str]) -> bool:
    for raw in log_lines:
        try:
            obj = json.loads(raw)
            if obj.get("pick_id") == pick_id and obj.get("_entry_logged"):
                return True
        except Exception:
            pass
    return False


# ---------------------------------------------------------------------------
# Exit check
# ---------------------------------------------------------------------------

def _check_exits(log_lines: list[str], current_price: float | None,
                 today: str) -> list[str]:
    """Mark open shadow entries as exited if TP/SL/time-stop triggered.

    Modifies in-place (returns new list with exit fields appended).
    """
    updated = []
    for raw in log_lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            updated.append(raw)
            continue

        if obj.get("_exited") or not obj.get("_entry_logged"):
            updated.append(raw)
            continue

        # Time-stop check
        entry_date = obj.get("entry_date", "")
        if entry_date:
            try:
                held_days = (datetime.fromisoformat(today) -
                             datetime.fromisoformat(entry_date)).days
                if held_days >= _MAX_HOLD_DAYS:
                    exit_px = current_price or obj.get("entry_price", 0)
                    obj["_exited"] = True
                    obj["exit_reason"] = "time_stop"
                    obj["exit_date"] = today
                    obj["exit_price"] = exit_px
                    obj["_pnl_pct"] = _calc_pnl(obj, exit_px)
                    updated.append(json.dumps(obj, separators=(",", ":")))
                    continue
            except Exception:
                pass

        if current_price is None:
            updated.append(raw)
            continue

        direction = obj.get("direction", "LONG").upper()
        tp = obj.get("take_profit")
        sl = obj.get("stop_loss")

        hit_tp = (tp is not None and (
            (direction == "LONG" and current_price >= tp) or
            (direction == "SHORT" and current_price <= tp)
        ))
        hit_sl = (sl is not None and (
            (direction == "LONG" and current_price <= sl) or
            (direction == "SHORT" and current_price >= sl)
        ))

        if hit_tp or hit_sl:
            obj["_exited"] = True
            obj["exit_reason"] = "tp" if hit_tp else "sl"
            obj["exit_date"] = today
            obj["exit_price"] = current_price
            obj["_pnl_pct"] = _calc_pnl(obj, current_price)
        updated.append(json.dumps(obj, separators=(",", ":")))
    return updated


def _calc_pnl(obj: dict, exit_price: float) -> float:
    entry = obj.get("entry_price", 0) or 0
    if entry == 0:
        return 0.0
    direction = obj.get("direction", "LONG").upper()
    if direction == "SHORT":
        return round((entry - exit_price) / entry * 100, 4)
    return round((exit_price - entry) / entry * 100, 4)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _print_summary(log_lines: list[str]) -> None:
    entries = []
    for raw in log_lines:
        try:
            entries.append(json.loads(raw.strip()))
        except Exception:
            pass

    logged = [e for e in entries if e.get("_entry_logged")]
    exited = [e for e in logged if e.get("_exited")]
    open_picks = [e for e in logged if not e.get("_exited")]
    wins = [e for e in exited if e.get("_pnl_pct", 0) > 0]
    losses = [e for e in exited if e.get("_pnl_pct", 0) <= 0]
    total_pnl = sum(e.get("_pnl_pct", 0) for e in exited)
    wr = len(wins) / len(exited) * 100 if exited else 0.0

    print(f"\n[ctf_shadow_tracker] D-001 CT=F Shadow Summary ({_today_utc()})")
    print(f"  Tracked picks:  {len(logged)}")
    print(f"  Open:           {len(open_picks)}")
    print(f"  Closed:         {len(exited)} (W={len(wins)} L={len(losses)})")
    print(f"  Win rate:       {wr:.1f}%")
    print(f"  Total PnL:      {total_pnl:.2f}%")
    if open_picks:
        print("  Open picks:", [p.get("pick_id", "?")[:12] for p in open_picks])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(dry_run: bool = False, summary_only: bool = False,
         log_path: Path | None = None) -> int:
    log_path = log_path or _SHADOW_LOG
    run_ts = datetime.now(timezone.utc).isoformat()
    today = _today_utc()

    existing = _load_existing_log(log_path)
    cutoff = datetime.now(timezone.utc).timestamp() - _PRUNE_DAYS * 86400
    existing = _prune_old(existing, cutoff)

    if summary_only:
        _print_summary(existing)
        return 0

    # Fetch current CT=F price for exit checks
    current_price = _fetch_ctf_price()
    print(f"[ctf_shadow_tracker] {run_ts} — CT=F price={current_price}", flush=True)

    # Load active picks and find eligible CT=F entries
    new_lines: list[str] = []
    try:
        all_picks = json.loads(_ACTIVE_PICKS.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ctf_shadow_tracker] WARN: cannot read active_picks: {e}", flush=True)
        all_picks = []

    for pick in all_picks:
        if str(pick.get("symbol", "")).upper() != "CT=F":
            continue
        if str(pick.get("asset_class", "")).upper() != "COMMODITY":
            continue
        if pick.get("status", "open").lower() not in ("open", "active"):
            continue

        # COT staleness gate (mirrors M-001)
        if not _cot_pass(pick):
            cot_date = (pick.get("extra") or {}).get("latest_cot_date", "none")
            print(f"[ctf_shadow_tracker] SKIP {pick.get('id','?')}: "
                  f"COT stale (cot_date={cot_date})", flush=True)
            continue

        pick_id = str(pick.get("id", ""))
        if _pick_already_logged(pick_id, existing):
            continue  # already tracking

        # Validate 60-day window
        entry_date_str = pick.get("entry_date", today)
        try:
            entry_date = datetime.fromisoformat(entry_date_str).date()
            validation_end = entry_date + timedelta(days=_VALIDATION_DAYS)
            if datetime.now(timezone.utc).date() > validation_end:
                continue  # beyond validation window
        except Exception:
            pass

        record = {
            "pick_id": pick_id,
            "symbol": pick.get("symbol"),
            "direction": pick.get("direction"),
            "entry_price": pick.get("entry_price"),
            "entry_date": entry_date_str,
            "take_profit": pick.get("take_profit"),
            "stop_loss": pick.get("stop_loss"),
            "confidence": pick.get("confidence"),
            "cot_date": (pick.get("extra") or {}).get("latest_cot_date"),
            "strategy": pick.get("strategy"),
            "_runner_ts": run_ts,
            "_entry_logged": True,
            "_exited": False,
        }
        line = json.dumps(record, separators=(",", ":"))
        new_lines.append(line)
        print(f"[ctf_shadow_tracker] LOG {pick_id} "
              f"{pick.get('direction')} @ {pick.get('entry_price')} "
              f"TP={pick.get('take_profit')} SL={pick.get('stop_loss')}", flush=True)

    print(f"[ctf_shadow_tracker] {len(new_lines)} new entry(ies) logged", flush=True)

    # Check exits on all entries (existing + newly logged) together
    combined = existing + new_lines
    combined = _check_exits(combined, current_price, today)

    if dry_run:
        print("[ctf_shadow_tracker] dry-run: no file written", flush=True)
        _print_summary(combined)
        return 0

    all_lines = combined
    if all_lines:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            "\n".join(all_lines) + "\n", encoding="utf-8")
    _print_summary(all_lines)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="D-001 CT=F COT-filtered shadow tracker")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print but do not write log")
    parser.add_argument("--summary", action="store_true",
                        help="Print rolling PnL summary only")
    args = parser.parse_args()
    sys.exit(main(dry_run=args.dry_run, summary_only=args.summary))
