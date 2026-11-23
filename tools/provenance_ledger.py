#!/usr/bin/env python3
"""Append-only provenance ledger: write picks BEFORE their outcome exists.

WHY THIS IS THE NEXT STEP
    Every refutation in this programme is robust, and every promotion is blocked by
    one thing: no artifact records when a pick was created relative to when its
    outcome became known.

        resolved_closed_picks_net.json   10,968 picks   no created_at  -> test impossible
        forward_observations.jsonl          430 rows    has created_at -> 430/430 backfilled

    Mega_mutation demonstrated the consequence concretely: it hits take-profit first
    56.4% of the time where a driftless random walk at the realised TP/SL distances
    implies 40.9% (binomial p = 1.7e-3). That is either genuine directional skill or
    TP/SL levels placed with hindsight, and no test on that data can distinguish the
    two. The statistics are not the limitation; the recording is.

    This module is the recording.

WHAT IT GUARANTEES
    1. `created_at` is stamped at write time, from the system clock, and cannot be
       supplied by the caller.
    2. Each record carries `seq`, `prev_sha256` and `sha256`, forming a hash chain.
       Editing, reordering, inserting or deleting any record breaks verification at
       that record and every one after it.
    3. TP/SL levels are recorded at emit time. A later resolver reads them; it does
       not choose them.
    4. Verification is a separate, read-only operation that reports the FIRST broken
       index and the reason, rather than a boolean.

WHAT IT DOES NOT DO
    * It cannot stop someone rewriting the whole file and re-running from scratch.
      That is why `verify()` also reports `first_record_utc` and total seq -- an
      operator can see when a chain starts. Publishing the chain head (e.g. to a
      commit or an external log) is the out-of-band anchor this cannot provide.
    * It does not fetch prices or resolve outcomes. It only records intent.

Read-only for verify; append-only for emit. No orders, no keys. Not advice.

Usage:
    python3 tools/provenance_ledger.py --emit-file picks.json
    python3 tools/provenance_ledger.py --verify
    python3 tools/provenance_ledger.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "reports/provenance/picks_provenance.jsonl"
GENESIS = "0" * 64

REQUIRED = ("symbol", "side", "entry_ref", "tp", "sl", "strategy", "source_system")
NUMERIC = ("entry_ref", "tp", "sl")


def _canon(rec: dict) -> bytes:
    """Deterministic bytes for hashing. Sort keys, fixed separators."""
    return json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()


def _sha(rec: dict) -> str:
    return hashlib.sha256(_canon(rec)).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def validate_pick(p: dict) -> tuple[bool, str]:
    for k in REQUIRED:
        if k not in p or p[k] in (None, ""):
            return False, f"missing field {k!r}"
    for k in NUMERIC:
        try:
            float(p[k])
        except (TypeError, ValueError):
            return False, f"field {k!r} is not numeric ({p[k]!r})"
    if float(p["tp"]) == float(p["sl"]):
        return False, "tp equals sl"
    side = str(p["side"]).upper()
    if side not in ("LONG", "SHORT"):
        return False, f"side must be LONG or SHORT (got {p['side']!r})"
    e, tp, sl = float(p["entry_ref"]), float(p["tp"]), float(p["sl"])
    if e <= 0:
        return False, "entry_ref must be positive"
    # TP/SL must be on the correct side of entry for the stated direction.
    # This is the check that would have caught an inverted-protection position.
    if side == "LONG" and not (sl < e < tp):
        return False, f"LONG requires sl < entry_ref < tp (got {sl}, {e}, {tp})"
    if side == "SHORT" and not (tp < e < sl):
        return False, f"SHORT requires tp < entry_ref < sl (got {tp}, {e}, {sl})"
    return True, ""


def read_all(path: Path = LEDGER) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def chain_head(path: Path = LEDGER) -> dict:
    recs = read_all(path)
    if not recs:
        return {"seq": 0, "head_sha256": GENESIS, "first_record_utc": None,
                "last_record_utc": None}
    return {"seq": recs[-1]["seq"], "head_sha256": recs[-1]["sha256"],
            "first_record_utc": recs[0]["created_at"],
            "last_record_utc": recs[-1]["created_at"]}


def emit(picks: list[dict], path: Path = LEDGER, dry_run: bool = False) -> list[dict]:
    """Append picks. created_at is stamped HERE and cannot be passed in."""
    head = chain_head(path)
    seq = head["seq"]
    prev = head["head_sha256"]
    written, rejected = [], []
    for p in picks:
        if "created_at" in p:
            # Refuse rather than silently overwrite: a caller supplying created_at
            # is exactly the backfill this ledger exists to prevent.
            rejected.append((p, "caller supplied created_at -- refused"))
            continue
        ok, why = validate_pick(p)
        if not ok:
            rejected.append((p, why))
            continue
        seq += 1
        rec = {
            "seq": seq,
            "created_at": _now(),
            "signal_ts": p.get("signal_ts") or p.get("as_of") or None,
            "symbol": str(p["symbol"]).upper(),
            "side": str(p["side"]).upper(),
            "entry_ref": float(p["entry_ref"]),
            "tp": float(p["tp"]),
            "sl": float(p["sl"]),
            "strategy": p["strategy"],
            "source_system": p["source_system"],
            "horizon_hours": p.get("horizon_hours"),
            "prev_sha256": prev,
        }
        rec["sha256"] = _sha(rec)
        prev = rec["sha256"]
        written.append(rec)
    if not dry_run and written:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            for rec in written:
                f.write(json.dumps(rec, sort_keys=True) + "\n")
    return written, rejected


def verify(path: Path = LEDGER) -> dict:
    """Walk the chain. Report the FIRST failure, not a boolean."""
    recs = read_all(path)
    if not recs:
        return {"ok": True, "n": 0, "reason": "empty ledger (nothing to verify)"}
    prev = GENESIS
    prev_created = None
    for i, rec in enumerate(recs):
        stored = rec.get("sha256")
        body = {k: v for k, v in rec.items() if k != "sha256"}
        if rec.get("seq") != i + 1:
            return {"ok": False, "n": len(recs), "index": i,
                    "reason": f"seq gap: expected {i+1}, found {rec.get('seq')}"}
        if rec.get("prev_sha256") != prev:
            return {"ok": False, "n": len(recs), "index": i,
                    "reason": "prev_sha256 does not match previous record"}
        if _sha(body) != stored:
            return {"ok": False, "n": len(recs), "index": i,
                    "reason": "sha256 mismatch: record was modified after write"}
        c = datetime.fromisoformat(rec["created_at"])
        if prev_created and c < prev_created:
            return {"ok": False, "n": len(recs), "index": i,
                    "reason": "created_at went backwards"}
        prev_created = c
        prev = stored
    return {"ok": True, "n": len(recs), "head_sha256": prev,
            "first_record_utc": recs[0]["created_at"],
            "last_record_utc": recs[-1]["created_at"]}


def forward_credit(picks_ledger: Path = LEDGER, outcomes: Path | None = None) -> dict:
    """How many emitted picks are genuinely forward (created before outcome)?"""
    recs = read_all(picks_ledger)
    if not recs or outcomes is None or not Path(outcomes).exists():
        return {"n_emitted": len(recs), "n_resolved": 0, "n_forward": 0,
                "note": "no outcomes file supplied -- nothing resolved yet"}
    closed = {}
    for line in Path(outcomes).open():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        k = (r.get("hypothesis_id"), r.get("symbol"))
        if r.get("closed_at"):
            closed[k] = r["closed_at"]
    fwd = 0
    resolved = 0
    for rec in recs:
        k = (rec.get("strategy"), rec["symbol"])
        c = closed.get(k)
        if not c:
            continue
        resolved += 1
        if datetime.fromisoformat(rec["created_at"]) < datetime.fromisoformat(c):
            fwd += 1
    return {"n_emitted": len(recs), "n_resolved": resolved, "n_forward": fwd,
            "pct_forward": (100 * fwd / resolved) if resolved else None}


# ---------------------------------------------------------------- selftest
def selftest() -> int:
    """The control that must fail: prove tamper detection actually works."""
    print("=" * 78)
    print("SELFTEST -- prove the chain detects edits, deletions and reordering")
    print("=" * 78)
    tmp = Path(tempfile.mkdtemp()) / "t.jsonl"
    picks = [
        {"symbol": "BTCUSDT", "side": "LONG", "entry_ref": 60000, "tp": 63000,
         "sl": 58500, "strategy": "t", "source_system": "selftest"},
        {"symbol": "ETHUSDT", "side": "SHORT", "entry_ref": 3000, "tp": 2850,
         "sl": 3100, "strategy": "t", "source_system": "selftest"},
        {"symbol": "SOLUSDT", "side": "LONG", "entry_ref": 150, "tp": 165,
         "sl": 142, "strategy": "t", "source_system": "selftest"},
    ]
    w, rej = emit(picks, tmp)
    print(f"  emitted {len(w)}  rejected {len(rej)}")
    v = verify(tmp)
    print(f"  verify clean chain        -> ok={v['ok']} n={v.get('n')}")
    assert v["ok"], v

    # 1. tamper with a value
    recs = read_all(tmp)
    recs[1]["tp"] = 2000.0                      # move the take-profit
    tmp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in recs))
    v = verify(tmp)
    print(f"  after editing record 2    -> ok={v['ok']} index={v.get('index')} "
          f"reason={v.get('reason')}")
    assert not v["ok"], "edit NOT detected"

    # 2. rewrite the hash to cover the edit
    recs = read_all(tmp)
    body = {k: x for k, x in recs[1].items() if k != "sha256"}
    recs[1]["sha256"] = _sha(body)
    # re-link subsequent records so only the CONTENT is wrong, not the links
    for i in range(2, len(recs)):
        recs[i]["prev_sha256"] = recs[i - 1]["sha256"]
        b = {k: x for k, x in recs[i].items() if k != "sha256"}
        recs[i]["sha256"] = _sha(b)
    tmp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in recs))
    v = verify(tmp)
    print(f"  after re-hashing the edit -> ok={v['ok']}"
          f"{' (chain re-linked, so this is the known limitation)' if v['ok'] else ''}")

    # 3. delete a record
    tmp2 = Path(tempfile.mkdtemp()) / "t2.jsonl"
    emit(picks, tmp2)
    recs = read_all(tmp2)
    del recs[1]
    tmp2.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in recs))
    v = verify(tmp2)
    print(f"  after deleting record 2   -> ok={v['ok']} index={v.get('index')} "
          f"reason={v.get('reason')}")
    assert not v["ok"], "deletion NOT detected"

    # 4. caller-supplied created_at is refused
    _, rej = emit([dict(picks[0], created_at="2020-01-01T00:00:00+00:00")], tmp2)
    print(f"  caller-supplied created_at -> rejected {len(rej)}: "
          f"{rej[0][1] if rej else 'NOT REJECTED'}")
    assert rej, "caller-supplied created_at was accepted"

    # 5. inverted TP/SL is refused
    _, rej = emit([{"symbol": "X", "side": "LONG", "entry_ref": 100, "tp": 90,
                    "sl": 110, "strategy": "t", "source_system": "s"}], tmp2)
    print(f"  LONG with tp<sl            -> rejected {len(rej)}: "
          f"{rej[0][1] if rej else 'NOT REJECTED'}")
    assert rej, "inverted TP/SL was accepted"

    print("\n  ALL SELFTESTS PASSED")
    print("  KNOWN LIMITATION PROVEN, NOT ASSERTED: re-hashing an edit and")
    print("  re-linking the chain is undetectable by verify() alone. That is why")
    print("  chain_head() exposes seq + head_sha256 so the head can be anchored")
    print("  out of band (commit message, external log). An unanchored chain only")
    print("  proves internal consistency.")
    return 0


STATUS = REPO / "reports/provenance/status.json"


def write_status(outcomes: Path | None = None, path: Path = LEDGER) -> dict:
    """Emit reports/provenance/status.json for the weekly scorecard to read."""
    v = verify(path)
    fc = forward_credit(path, outcomes)
    st = {
        "generated_utc": _now(),
        "chain_ok": bool(v.get("ok")),
        "fail_index": v.get("index"),
        "fail_reason": v.get("reason"),
        "n_records": v.get("n", 0),
        "head_sha256": v.get("head_sha256"),
        "first_record_utc": v.get("first_record_utc"),
        "last_record_utc": v.get("last_record_utc"),
        "n_forward": fc.get("n_forward"),
        "n_resolved": fc.get("n_resolved"),
        "pct_forward": fc.get("pct_forward"),
        "note": fc.get("note"),
    }
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(st, indent=1))
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-file", help="JSON file containing a list of picks")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--head", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--status", action="store_true",
                    help="Write reports/provenance/status.json (weekly gate input)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--outcomes", help="outcomes JSONL for forward-credit")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if a.status:
        st = write_status(Path(a.outcomes) if a.outcomes else None)
        print(json.dumps(st, indent=1))
        print(f"\nwrote {STATUS.relative_to(REPO)}")
        return 0 if st["chain_ok"] else 1
    if a.verify:
        v = verify()
        print(json.dumps(v, indent=1))
        if not v["ok"]:
            print(f"\nFAIL: {v['reason']} at index {v.get('index')}")
            return 1
        print(f"\nOK: {v['n']} records, chain intact")
        return 0
    if a.head:
        print(json.dumps(chain_head(), indent=1))
        return 0
    if a.stats:
        print(json.dumps(forward_credit(outcomes=a.outcomes), indent=1))
        return 0
    if a.emit_file:
        picks = json.loads(Path(a.emit_file).read_text())
        if isinstance(picks, dict):
            picks = picks.get("picks", [])
        w, rej = emit(picks, dry_run=a.dry_run)
        print(f"emitted {len(w)}{' (dry run)' if a.dry_run else ''}")
        for p, why in rej:
            print(f"  REJECTED {p.get('symbol')}: {why}")
        if w:
            print(f"chain head now seq={w[-1]['seq']} sha={w[-1]['sha256'][:16]}...")
            print("ANCHOR THIS: put the head sha in the commit message so the\n"
                  "chain cannot be silently rewritten.")
        return 0 if not rej else 2
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
