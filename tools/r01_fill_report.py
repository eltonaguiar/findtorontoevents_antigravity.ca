#!/usr/bin/env python3
"""Answer one question after the open: did the R01 round-open fill actually happen?

Expected to run at ~14:40Z, ten minutes after the 14:30Z open and eight after the
14:32Z fill waiter. It never fills anything -- it reads the artefact and the waiter
log and says what happened, so the answer does not depend on an agent being awake.

    python3 tools/r01_fill_report.py            # prints, writes md, posts to COMS
    python3 tools/r01_fill_report.py --no-coms

Exit: 0 filled, 3 still refused pre-open, 4 never ran, 5 artefact unreadable.
Paper only. Zero capital. Not investment advice.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "reports" / "r01_round_open_fill_2026-11-23.json"
LOG = ROOT / "reports" / "r01_fill_2026-11-23.log"
OUT = ROOT / "reports" / "r01_fill_verdict_2026-11-23.md"
COMS = "/home/eaguiar2015/AGENT_FOLDERFRAMEWORK/COMMUNICATION/coms"
TOPIC = "inbox/gx10-c9b9/findtorontoevents_antigravity-ca/all"


def waiter_alive() -> bool:
    try:
        out = subprocess.run(["pgrep", "-f", "r01_fill_when_open.py"],
                             capture_output=True, text=True, timeout=10)
        return bool(out.stdout.strip())
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-coms", action="store_true")
    a = ap.parse_args()
    now = datetime.now(timezone.utc)

    if not ART.exists():
        verdict, code, detail = "NOT_RUN", 4, "artefact absent — the fill never executed"
        art = {}
    else:
        try:
            art = json.loads(ART.read_text())
        except Exception as e:
            verdict, code, detail = "UNREADABLE", 5, f"{type(e).__name__}: {e}"
            art = {}
        else:
            status = art.get("status")
            filled = art.get("filled") or art.get("positions") or []
            if filled and status != "NOT_OPEN_YET":
                verdict, code = "FILLED", 0
                detail = f"{len(filled)} position(s) filled"
            elif status == "NOT_OPEN_YET":
                verdict, code = "REFUSED_PRE_OPEN", 3
                detail = ("the tool refused: no instrument had a bar at or after the "
                          "round start. This is a refusal, not a result.")
            else:
                verdict, code = "NO_FILL", 3
                detail = f"status={status!r} with {len(filled)} filled rows"

    log_tail = ""
    if LOG.exists():
        log_tail = "\n".join(LOG.read_text(errors="replace").splitlines()[-6:])
    alive = waiter_alive()
    _ins = art.get("instruments") or art.get("panel") or art.get("coverage") or []
    n_instruments = (len(_ins) if isinstance(_ins, list)
                     else (art.get("n_covered") or art.get("covered") or "n/a"))
    filled = art.get("filled") or art.get("positions") or []

    body = [
        "# R01 round-open fill — verdict",
        "",
        f"**Checked:** {now.isoformat()}  ·  **Open:** 2026-11-23T14:30:00Z  ·  "
        f"**Fill waiter:** {'alive' if alive else 'not running'}",
        f"**Verdict:** `{verdict}` — {detail}",
        "",
        f"- artefact: `{ART.relative_to(ROOT)}` "
        f"(status `{art.get('status')}`, generated `{art.get('generated_at')}`)",
        f"- filled rows: **{len(filled)}**",
        f"- instruments listed in the artefact: {n_instruments}",
        "",
        "## Waiter log (last lines)",
        "```",
        log_tail or "(no log)",
        "```",
        "",
        "A verdict of `REFUSED_PRE_OPEN` after 14:35Z is itself a finding: it would mean the "
        "feed still had no bar for the round start, not that the fill was skipped.",
        "",
    ]
    if filled:
        body += ["## Fills", "", "```", json.dumps(filled[:5], indent=1, default=str)[:2000], "```", ""]
    OUT.write_text("\n".join(body))
    print(f"{verdict}: {detail}")
    print(f"wrote {OUT.relative_to(ROOT)}")

    if not a.no_coms:
        msg = (f"[buffy] R01 FILL VERDICT @ {now.strftime('%Y-%m-%dT%H:%M:%SZ')}: {verdict} — {detail}\n\n"
               f"waiter alive: {alive} | artefact status: {art.get('status')} | filled rows: {len(filled)}\n"
               f"report: reports/r01_fill_verdict_2026-11-23.md\n\n"
               f"{'Fill happened — inspect entry prices against the 14:30Z bar before any inference.' if verdict=='FILLED' else 'No fill. If this says REFUSED_PRE_OPEN past 14:35Z, the price feed itself is the problem, not the clock.'}")
        try:
            subprocess.run([COMS, "send", "--retain", TOPIC, msg], timeout=30,
                           capture_output=True, text=True)
            print("posted to COMS")
        except Exception as e:
            print(f"COMS post failed: {e}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
