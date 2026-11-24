"""Write a compact, machine-readable status contract for the audit surfaces.

Monitoring should not have to parse a 45 KB ledger and a page sidecar to answer
"is the book publishing, how fresh is it, and is anything promoted?". This writes
one small file (`audit_dashboard/data/audit3_public_status.json`) with the
answers, so a cron check is a single fetch.

Schema (stable):
  schema, generated_at, ledger_generated_at, coverage{scored,total,valid,mode},
  verdicts{proven,candidate,weak,kill}, persistence{on,churn}, denials{n,by_class},
  forward{rows,enforced,eligible_pods,blocked[hypothesis,reason]}, stale(bool),
  stale_after(ISO) -- compare to your clock; 'stale' is frozen at build time
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LEDGER = REPO / "audit_dashboard" / "data" / "audit3_ledger.json"
FORWARD = REPO / "audit_dashboard" / "data" / "audit2_forward.json"
OUT = REPO / "audit_dashboard" / "data" / "audit3_public_status.json"

STALE_HOURS = 12.0


def build_status(ledger: dict, forward: dict | None = None,
                 now: datetime | None = None) -> dict:
    """Pure: ledger (+ optional forward sidecar) -> the public contract."""
    now = now or datetime.now(timezone.utc)
    cov = ledger.get("coverage") or {}
    summ = ledger.get("summary") or {}
    pers = ledger.get("persistence") or {}
    churn = ledger.get("verdict_churn") or {}
    hits = ledger.get("denylist_hits") or {}
    gate = ledger.get("forward_gate") or {}
    fwd = (forward or {}).get("by_hypothesis") or {}

    blocked = []
    for hid, g in (gate.get("hypotheses") or {}).items():
        gg = (fwd.get(hid) or {}).get("gate") or {}
        reasons = gg.get("reasons") or g.get("reasons") or []
        if reasons and not gg.get("eligible", g.get("eligible")):
            blocked.append({"hypothesis": hid, "reason": reasons[0]})

    gen = ledger.get("generated_at")
    age_h = None
    stale_after = None
    try:
        dt = datetime.fromisoformat(str(gen).replace("Z", "+00:00"))
        age_h = round((now - dt).total_seconds() / 3600.0, 2)
        # The file is a static snapshot rebuilt only by the ledger workflow, so a
        # boolean computed at build time is frozen until the next build and can
        # never go true between runs. Publish the moment it SHOULD be considered
        # stale instead, so any consumer can compare it to its own clock.
        stale_after = (dt + timedelta(hours=STALE_HOURS)).isoformat()
    except (TypeError, ValueError):
        pass

    return {
        "schema": "audit3.public_status.v1",
        "generated_at": now.isoformat(),
        "ledger_generated_at": gen,
        "age_hours": age_h,
        "stale": bool(age_h is None or age_h > STALE_HOURS),
        "stale_after": stale_after,
        "stale_note": ("'stale' is evaluated at build time and is frozen between rebuilds; "
                       "consumers must compare stale_after to their own clock."),
        "coverage": {
            "mode": (cov.get("denominator") or {}).get("mode"),
            "scored": cov.get("scored_rows"),
            "total": cov.get("total_closed_picks"),
            "valid": cov.get("valid_closed_picks"),
            "valid_basis": cov.get("valid_closed_picks_basis"),
        },
        "verdicts": {
            "proven": summ.get("n_proven"),
            "candidate": summ.get("n_candidate"),
            "weak": summ.get("n_weak"),
            "kill": summ.get("n_kill"),
        },
        "persistence": {"on": pers.get("available"),
                        "churn_flipped": churn.get("n_flipped"),
                        "churn_tracked": churn.get("n_tracked")},
        "denials": {"n": hits.get("n"), "by_class": hits.get("by_class") or {}},
        "forward": {
            "rows": gate.get("n_rows"),
            "enforced": gate.get("enforced"),
            "eligible_pods": sum(1 for p in (gate.get("pods") or {}).values()
                                 if p.get("eligible")),
            "blocked": blocked[:10],
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--forward", default=str(FORWARD))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    forward = None
    try:
        forward = json.loads(Path(args.forward).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        forward = None
    status = build_status(ledger, forward)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(status, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out}: stale={status['stale']} scored={status['coverage']['scored']} "
          f"forward_rows={status['forward']['rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
