#!/usr/bin/env python3
"""One-command check: has the excluded-cohort summary been fed yet?

Background (Blocks 58-61). ``coverage.excluded_summary`` in the audit3 ledger
is built from the ``_excluded_cohort_rows`` block the dashboard generator
publishes in ``dashboard_data.json``. Two different things can be wrong, and
they look identical from a distance:

* the **wiring** is missing  -> the payload has no ``_excluded_cohort_rows`` key
  at all, so ``excluded_summary`` is ``None`` and the ledger shows zeros;
* the **measurement** is not fed -> the key exists but summarises to
  ``total: 0`` / ``by_class: {}``.

``total: 0`` is therefore indistinguishable from the un-wired default and must
never be read as "no excluded rows exist". This tool prints which of the two
states you are in, and only exits 0 when the summary is actually populated.

Manual operator tool only: it is deliberately NOT wired into any workflow,
because a CI gate would fail every hour until the next dashboard build lands.

Usage::

    python3 tools/check_excluded_summary.py \
        --payload https://findtorontoevents.ca/audit/data/dashboard_data.json \
        --ledger audit_dashboard/data/audit3_ledger.json

    python3 tools/check_excluded_summary.py \
        --payload /tmp/downloaded_dashboard_data.json

Exit codes: 0 = fed (key present, total >= --expect-min, by_class non-empty);
1 = anything else, with a one-line reason on stderr.

Stdlib only. Network is touched only when the operator passes a URL.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "excluded-summary-checker/1.0 (manual operator tool)"
TIMEOUT = 30

# Distinct, greppable messages. The Block 59/60 trap is that an absent key and a
# zero total get conflated; each state gets its own sentence so they cannot be.
MSG_KEY_ABSENT = (
    "wiring check FAILED: `_excluded_cohort_rows` key absent from the payload "
    "(the build predates the wiring, or this is not the dashboard payload)"
)
MSG_NOT_YET_FED = (
    "measurement not yet fed: excluded_summary.total = 0 "
    "(the wiring may be present, but no excluded row was summarised)"
)
MSG_BY_CLASS_EMPTY = (
    "measurement incomplete: excluded_summary.total > 0 but by_class is empty"
)
MSG_FLAT_LIST = (
    "warning: `_excluded_cohort_rows` is a flat list, not a cohort mapping; "
    "summarize_excluded_rows() treats that as zero rows"
)


def _say(line: str = "") -> None:
    print(line)


def _fail(reason: str) -> int:
    print(reason, file=sys.stderr)
    return 1


def load_json(source: str) -> tuple[object | None, str | None]:
    """Read JSON from a local path or an http(s) URL.

    Returns ``(data, error)``. Errors are returned, never raised, so expected
    conditions (missing file, HTTP failure, malformed JSON) never print a
    traceback.
    """
    if source.startswith(("http://", "https://")):
        req = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            return None, f"HTTP {exc.code} fetching {source}"
        except urllib.error.URLError as exc:
            return None, f"could not reach {source}: {exc.reason}"
        except (TimeoutError, OSError) as exc:
            return None, f"could not read {source}: {exc}"
    else:
        path = Path(source)
        if not path.exists():
            return None, f"no such file: {source}"
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            return None, f"could not read {source}: {exc}"
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return None, f"malformed JSON in {source}: {exc}"


def _row_class(row: object) -> str:
    if not isinstance(row, dict):
        return "UNKNOWN"
    cls = str(row.get("asset_class") or "").strip().upper()
    return cls or "UNKNOWN"


def inspect_payload(payload: object) -> dict:
    """Wiring state of the dashboard payload.

    Mirrors ``audit_trail.excluded_cohorts.summarize_excluded_rows``: only a
    cohort *mapping* produces rows, and rows shared by two cohorts are counted
    once (here by canonical content, since JSON gives every row a new identity).
    """
    info = {
        "key_present": False,
        "rows_nonempty": False,
        "total": 0,
        "by_class": {},
        "repo_sha": None,
        "cohorts": {},
        "note": None,
    }
    if not isinstance(payload, dict):
        info["note"] = "payload is not a JSON object"
        return info
    meta = payload.get("metadata")
    if isinstance(meta, dict) and meta.get("repo_sha"):
        info["repo_sha"] = str(meta["repo_sha"])
    if "_excluded_cohort_rows" not in payload:
        return info
    info["key_present"] = True
    block = payload.get("_excluded_cohort_rows")
    if isinstance(block, list):
        info["note"] = MSG_FLAT_LIST
        return info
    if not isinstance(block, dict):
        info["note"] = "`_excluded_cohort_rows` is neither a mapping nor a list"
        return info
    seen: set[str] = set()
    for cohort, rows in block.items():
        rows = rows if isinstance(rows, list) else []
        info["cohorts"][str(cohort)] = len(rows)
        for row in rows:
            key = json.dumps(row, sort_keys=True, default=str)
            if key in seen:
                continue
            seen.add(key)
            info["total"] += 1
            cls = _row_class(row)
            info["by_class"][cls] = info["by_class"].get(cls, 0) + 1
    info["by_class"] = dict(sorted(info["by_class"].items()))
    info["rows_nonempty"] = info["total"] > 0
    return info


def inspect_ledger(ledger: object) -> dict:
    """``coverage.excluded_summary`` from an audit3 ledger."""
    info = {"present": False, "total": 0, "by_class": {}, "by_reason": {},
            "note": None}
    if not isinstance(ledger, dict):
        info["note"] = "ledger is not a JSON object"
        return info
    coverage = ledger.get("coverage")
    summary = coverage.get("excluded_summary") if isinstance(coverage, dict) else None
    if not isinstance(summary, dict):
        info["note"] = "ledger has no coverage.excluded_summary object"
        return info
    info["present"] = True
    try:
        info["total"] = int(summary.get("total") or 0)
    except (TypeError, ValueError):
        info["total"] = 0
    by_class = summary.get("by_class")
    info["by_class"] = dict(by_class) if isinstance(by_class, dict) else {}
    by_reason = summary.get("by_reason")
    info["by_reason"] = dict(by_reason) if isinstance(by_reason, dict) else {}
    return info


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check whether coverage.excluded_summary has been fed "
                    "(manual operator tool; never wired into CI).",
    )
    parser.add_argument("--payload", required=True, metavar="PATH_OR_URL",
                        help="dashboard_data.json, local path or http(s) URL")
    parser.add_argument("--ledger", default=None, metavar="PATH_OR_URL",
                        help="optional audit3 ledger JSON, local path or URL")
    parser.add_argument("--expect-min", type=int, default=1, metavar="N",
                        help="minimum excluded_summary.total considered fed "
                             "(default: 1)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    _say(f"payload: {args.payload}")
    payload, err = load_json(args.payload)
    if err:
        _say("  unreadable")
        return _fail(f"error: {err}")
    pinfo = inspect_payload(payload)
    if pinfo["repo_sha"]:
        _say(f"  metadata.repo_sha: {pinfo['repo_sha']}")
    else:
        _say("  metadata.repo_sha: (absent)")
    if not pinfo["key_present"]:
        _say("  _excluded_cohort_rows: ABSENT")
    else:
        cohorts = ", ".join(f"{k}={v}" for k, v in pinfo["cohorts"].items()) or "none"
        _say(f"  _excluded_cohort_rows: present ({cohorts}; "
             f"{pinfo['total']} distinct rows)")
        _say(f"  payload-derived by_class: {json.dumps(pinfo['by_class'])}")
    if pinfo["note"]:
        _say(f"  {pinfo['note']}")

    linfo = None
    if args.ledger:
        _say(f"ledger: {args.ledger}")
        ledger, lerr = load_json(args.ledger)
        if lerr:
            _say("  unreadable")
            return _fail(f"error: {lerr}")
        linfo = inspect_ledger(ledger)
        if linfo["present"]:
            _say(f"  coverage.excluded_summary.total: {linfo['total']}")
            _say(f"  by_class: {json.dumps(linfo['by_class'])}")
            _say(f"  by_reason: {json.dumps(linfo['by_reason'])}")
        else:
            _say(f"  {linfo['note']}")

    # Verdict. The ledger is audit3's actual measurement, so it wins when given;
    # otherwise fall back to what the payload's rows say.
    if linfo is not None:
        total, by_class = linfo["total"], linfo["by_class"]
    else:
        total, by_class = pinfo["total"], pinfo["by_class"]

    if not pinfo["key_present"]:
        _say("verdict: NOT FED (exit 1)")
        return _fail(MSG_KEY_ABSENT)
    if total == 0:
        _say("verdict: NOT FED (exit 1)")
        return _fail(MSG_NOT_YET_FED)
    if total < args.expect_min:
        _say("verdict: NOT FED (exit 1)")
        return _fail(f"measurement below threshold: total {total} < "
                     f"--expect-min {args.expect_min}")
    if not by_class:
        _say("verdict: NOT FED (exit 1)")
        return _fail(MSG_BY_CLASS_EMPTY)
    _say(f"verdict: FED (exit 0) - {total} excluded rows across "
         f"{len(by_class)} class(es)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
