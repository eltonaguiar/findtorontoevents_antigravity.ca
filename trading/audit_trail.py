#!/usr/bin/env python3
"""
trading/audit_trail.py — Append-only, tamper-evident audit trail for trading decisions.

Every signal that passes through the gate stack — accepted or rejected — is
written here as a single JSON line.  Each entry carries:

  * A SHA-256 hash of the raw input signal so post-hoc tampering is detectable.
  * A chain hash: SHA-256 of (previous_chain_hash + current_entry_json), giving a
    cryptographic link between consecutive entries (similar to a blockchain).

Usage (embedded in a scanner or strategy runner):
    from trading.audit_trail import AuditTrailLogger

    log = AuditTrailLogger()                     # persistent file
    log = AuditTrailLogger(rotate_daily=True)    # new file per UTC day

    entry = log.record(
        signal   = {"symbol": "BTCUSDT", "direction": "LONG", ...},
        gates    = {"rr": True, "freshness": True, ...},
        scores   = {"bayesian_p50": 0.92, "meta_score": 0.78, "regime_weight": 0.85},
        sizing   = {"kelly_full": 0.045, "kelly_frac": 0.0225,
                    "final_pct": 0.018, "dd_mult": 1.0},
        decision = "ACCEPT",
        reason   = "all_gates_passed",
        model_version = "funding_carry_v3_gen2",
    )

    ok, errors = log.verify_integrity()
    recent_rejects = log.query_rejections(limit=20, since_hours=24)
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent / "data"
_BASE_NAME = "audit_trail"
_SENTINEL_HASH = "0" * 64  # genesis chain hash (no previous entry)


def _utc_now_iso() -> str:
    """Return the current UTC time in ISO-8601 format (always ends with 'Z')."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_suffix() -> str:
    """Return today's date string used for daily-rotated file names."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def _sha256(text: str) -> str:
    """Return lowercase hex SHA-256 digest of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).digest().hex()


def _hash_signal(signal: Dict[str, Any]) -> str:
    """
    Deterministic SHA-256 of a signal dict.

    Keys are sorted so that dict insertion order cannot change the hash.
    Prefixed with 'sha256:' for readability in the stored entry.
    """
    canonical = json.dumps(signal, sort_keys=True, separators=(",", ":"))
    return "sha256:" + _sha256(canonical)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class AuditTrailLogger:
    """
    Append-only, tamper-evident audit trail for trading decisions.

    File format
    -----------
    One JSON object per line (JSON-Lines / NDJSON).  Each line is a complete,
    self-contained record.  The file is never rewritten — only appended.

    Tamper evidence
    ---------------
    Two independent mechanisms protect integrity:

    1. ``data_hash``    — SHA-256 of the *input* signal dict.  If anyone edits
                          a signal field after logging, re-hashing will not match.

    2. ``chain_hash``   — SHA-256 of (previous chain hash + current entry JSON).
                          Any edit anywhere in the file breaks every subsequent
                          chain hash, making silent tampering detectable via
                          ``verify_integrity()``.

    Parameters
    ----------
    data_dir     : Directory where log files are written.  Created automatically.
    rotate_daily : When True, a new file is started each UTC day:
                   ``audit_trail_2026-03-03.jsonl``.
                   When False (default), a single ``audit_trail.jsonl`` is used.
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        rotate_daily: bool = False,
    ) -> None:
        self._data_dir = Path(data_dir) if data_dir else _DATA_DIR
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._rotate_daily = rotate_daily

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def record(
        self,
        signal: Dict[str, Any],
        gates: Dict[str, bool],
        scores: Dict[str, float],
        sizing: Dict[str, float],
        decision: str,
        reason: str,
        model_version: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Build and append one audit entry, then return it.

        Parameters
        ----------
        signal        : Raw signal dict (symbol, direction, entry, tp, sl, rr,
                        strategy, and any extra fields).  Stored verbatim except
                        that a ``data_hash`` is computed from it for tamper
                        evidence.
        gates         : Gate pass/fail map, e.g.::

                            {
                              "rr": True, "freshness": True, "consensus": True,
                              "direction": True, "kill_list": True, "regime": True,
                            }

        scores        : Bayesian / model / regime scores, e.g.::

                            {"bayesian_p50": 0.92, "meta_score": 0.78,
                             "regime_weight": 0.85}

        sizing        : Position sizing breakdown, e.g.::

                            {"kelly_full": 0.045, "kelly_frac": 0.0225,
                             "final_pct": 0.018, "dd_mult": 1.0}

        decision      : ``"ACCEPT"`` or ``"REJECT"``.
        reason        : Short machine-readable reason string,
                        e.g. ``"all_gates_passed"`` or ``"rr_gate_failed"``.
        model_version : Strategy variant / version identifier.

        Returns
        -------
        dict
            The fully-formed entry that was written to disk.
        """
        # 1. Derive standard fields from signal dict
        entry: Dict[str, Any] = {
            "ts":            _utc_now_iso(),
            "symbol":        signal.get("symbol", "UNKNOWN"),
            "strategy":      signal.get("strategy", model_version),
            "direction":     signal.get("direction", "UNKNOWN"),
            "entry":         signal.get("entry"),
            "tp":            signal.get("tp"),
            "sl":            signal.get("sl"),
            "rr":            signal.get("rr"),
            "gates":         gates,
            "scores":        scores,
            "sizing":        sizing,
            "decision":      decision.upper(),
            "reason":        reason,
            "data_hash":     _hash_signal(signal),
            "model_version": model_version,
        }

        # 2. Read the previous chain hash, then compute and store the new one
        prev_hash = self._last_chain_hash()
        entry_json = json.dumps(entry, sort_keys=True, separators=(",", ":"))
        entry["chain_hash"] = _sha256(prev_hash + entry_json)

        # 3. Append to the log file (one JSON line)
        log_path = self._current_log_path()
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, separators=(",", ":")) + "\n")

        return entry

    # ------------------------------------------------------------------

    def verify_integrity(
        self,
        log_path: Optional[Path] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Walk the log file and verify every chain hash.

        Each entry's ``chain_hash`` is recomputed from
        ``SHA-256(previous_chain_hash + entry_json_without_chain_hash)``
        and compared to the stored value.

        Parameters
        ----------
        log_path : Path to the JSONL file to verify.  Defaults to the current
                   log file (respects ``rotate_daily``).

        Returns
        -------
        (ok, errors)
            ``ok`` is True if all hashes verified successfully.
            ``errors`` is a list of human-readable problem descriptions.
        """
        target = log_path or self._current_log_path()
        errors: List[str] = []

        if not target.exists():
            return True, []  # empty / non-existent file is trivially valid

        prev_hash = _SENTINEL_HASH
        line_no = 0

        with target.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                line_no += 1
                raw_line = raw_line.strip()
                if not raw_line:
                    continue

                try:
                    entry = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    errors.append(f"Line {line_no}: JSON parse error — {exc}")
                    continue

                stored_chain = entry.pop("chain_hash", None)
                if stored_chain is None:
                    errors.append(
                        f"Line {line_no} (ts={entry.get('ts')}): missing chain_hash field"
                    )
                    # Treat prev_hash as broken; continue to surface further errors
                    continue

                # Recompute the chain hash exactly as record() did
                entry_json = json.dumps(entry, sort_keys=True, separators=(",", ":"))
                expected = _sha256(prev_hash + entry_json)

                if stored_chain != expected:
                    errors.append(
                        f"Line {line_no} (ts={entry.get('ts')}, "
                        f"symbol={entry.get('symbol')}): "
                        f"chain_hash mismatch — stored={stored_chain[:12]}… "
                        f"expected={expected[:12]}…"
                    )

                # Always advance using the stored hash so that one bad entry
                # doesn't cascade failures to every subsequent line.
                prev_hash = stored_chain

        ok = len(errors) == 0
        return ok, errors

    # ------------------------------------------------------------------

    def query_rejections(
        self,
        limit: int = 50,
        since_hours: Optional[float] = None,
        log_path: Optional[Path] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return recent ``REJECT`` entries, newest first.

        Parameters
        ----------
        limit       : Maximum number of entries to return.
        since_hours : If given, only include entries whose ``ts`` is within
                      this many hours of now (UTC).  Useful for dashboards.
        log_path    : Override which file to read (defaults to current log).

        Returns
        -------
        list of dict
            Each dict is a parsed audit entry with ``decision == "REJECT"``.
        """
        target = log_path or self._current_log_path()
        if not target.exists():
            return []

        cutoff_ts: Optional[str] = None
        if since_hours is not None:
            from datetime import timedelta
            cutoff_dt = datetime.now(tz=timezone.utc) - timedelta(hours=since_hours)
            cutoff_ts = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        results: List[Dict[str, Any]] = []

        with target.open("r", encoding="utf-8") as fh:
            lines = fh.readlines()

        # Iterate newest-first by reversing the line list
        for raw_line in reversed(lines):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                entry = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            if entry.get("decision") != "REJECT":
                continue

            if cutoff_ts and entry.get("ts", "") < cutoff_ts:
                # Because we iterate newest-first and timestamps are monotone,
                # once we fall below the cutoff we can stop.
                break

            results.append(entry)
            if len(results) >= limit:
                break

        return results

    # ------------------------------------------------------------------

    def query_recent(
        self,
        limit: int = 50,
        decision_filter: Optional[str] = None,
        log_path: Optional[Path] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return the most recent audit entries, newest first.

        Parameters
        ----------
        limit           : Maximum entries to return.
        decision_filter : If given (e.g. ``"ACCEPT"`` or ``"REJECT"``), only
                          return entries matching that decision.
        log_path        : Override which file to read.

        Returns
        -------
        list of dict
        """
        target = log_path or self._current_log_path()
        if not target.exists():
            return []

        results: List[Dict[str, Any]] = []

        with target.open("r", encoding="utf-8") as fh:
            lines = fh.readlines()

        for raw_line in reversed(lines):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                entry = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            if decision_filter and entry.get("decision") != decision_filter.upper():
                continue

            results.append(entry)
            if len(results) >= limit:
                break

        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _current_log_path(self) -> Path:
        """Return the path of the log file that should be written to right now."""
        if self._rotate_daily:
            name = f"{_BASE_NAME}_{_today_suffix()}.jsonl"
        else:
            name = f"{_BASE_NAME}.jsonl"
        return self._data_dir / name

    def _last_chain_hash(self) -> str:
        """
        Read the final chain_hash from the current log file.

        Returns the genesis sentinel if the file is empty or does not exist.
        """
        log_path = self._current_log_path()
        if not log_path.exists():
            return _SENTINEL_HASH

        # Read the last non-empty line efficiently
        last_line: Optional[str] = None
        with log_path.open("rb") as fh:
            # Seek from the end to find the last line without loading the whole file
            try:
                fh.seek(0, 2)  # end of file
                size = fh.tell()
                if size == 0:
                    return _SENTINEL_HASH

                pos = size - 1
                buf = b""
                # Walk backwards until we've collected at least one full line
                while pos >= 0:
                    chunk_size = min(4096, pos + 1)
                    pos -= chunk_size
                    fh.seek(max(pos + 1, 0))
                    chunk = fh.read(chunk_size)
                    buf = chunk + buf
                    lines_found = buf.splitlines()
                    # Filter empty lines
                    non_empty = [ln for ln in lines_found if ln.strip()]
                    if non_empty:
                        last_line = non_empty[-1].decode("utf-8", errors="replace")
                        break
            except OSError:
                return _SENTINEL_HASH

        if last_line is None:
            return _SENTINEL_HASH

        try:
            entry = json.loads(last_line)
            return entry.get("chain_hash", _SENTINEL_HASH)
        except json.JSONDecodeError:
            return _SENTINEL_HASH


# ---------------------------------------------------------------------------
# Convenience factory — module-level singleton for simple usage
# ---------------------------------------------------------------------------

_default_logger: Optional[AuditTrailLogger] = None


def get_logger(rotate_daily: bool = False) -> AuditTrailLogger:
    """
    Return (or create) the module-level default ``AuditTrailLogger``.

    Useful for scripts that don't want to instantiate their own logger::

        from trading.audit_trail import get_logger
        log = get_logger()
        log.record(signal=..., gates=..., scores=..., sizing=...,
                   decision="ACCEPT", reason="all_gates_passed",
                   model_version="rsi2_v1")
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = AuditTrailLogger(rotate_daily=rotate_daily)
    return _default_logger


# ---------------------------------------------------------------------------
# CLI — quick integrity check or tail view
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Audit trail utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify integrity of the default log
  python -m trading.audit_trail verify

  # Verify a specific file
  python -m trading.audit_trail verify --file trading/data/audit_trail_2026-03-03.jsonl

  # Show last 10 rejected signals from the past 24 hours
  python -m trading.audit_trail rejections --limit 10 --hours 24

  # Show last 20 entries (any decision)
  python -m trading.audit_trail tail --limit 20
""",
    )
    sub = parser.add_subparsers(dest="cmd")

    # verify
    p_verify = sub.add_parser("verify", help="Check chain hash integrity")
    p_verify.add_argument("--file", type=Path, default=None)
    p_verify.add_argument("--daily", action="store_true",
                          help="Use today's rotated file name")

    # rejections
    p_rej = sub.add_parser("rejections", help="List recent REJECT entries")
    p_rej.add_argument("--limit", type=int, default=20)
    p_rej.add_argument("--hours", type=float, default=None,
                       help="Only entries within the last N hours")
    p_rej.add_argument("--daily", action="store_true")

    # tail
    p_tail = sub.add_parser("tail", help="Show recent entries (any decision)")
    p_tail.add_argument("--limit", type=int, default=20)
    p_tail.add_argument("--decision", type=str, default=None,
                        help="Filter by decision: ACCEPT or REJECT")
    p_tail.add_argument("--daily", action="store_true")

    args = parser.parse_args()

    if args.cmd is None:
        parser.print_help()
        sys.exit(0)

    logger = AuditTrailLogger(rotate_daily=getattr(args, "daily", False))

    if args.cmd == "verify":
        ok, errors = logger.verify_integrity(
            log_path=args.file if args.file else None
        )
        if ok:
            print("Integrity OK — all chain hashes verified.")
        else:
            print(f"INTEGRITY ERRORS ({len(errors)} found):")
            for err in errors:
                print(" ", err)
            sys.exit(1)

    elif args.cmd == "rejections":
        entries = logger.query_rejections(
            limit=args.limit,
            since_hours=args.hours,
        )
        if not entries:
            print("No rejections found.")
        else:
            print(json.dumps(entries, indent=2))

    elif args.cmd == "tail":
        entries = logger.query_recent(
            limit=args.limit,
            decision_filter=args.decision,
        )
        if not entries:
            print("No entries found.")
        else:
            print(json.dumps(entries, indent=2))
