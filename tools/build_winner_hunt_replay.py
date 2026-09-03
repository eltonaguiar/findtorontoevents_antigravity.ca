#!/usr/bin/env python3
"""build_winner_hunt_replay.py — monthly winner-hunt replay (READ-ONLY analytics →
auto-committed verdict doc).

Why
---
Today the operator runs the STA-09 hunt manually when rsi5070 nears the n>=150
promotion bar. With many picks accruing across the cohort, by the time the gate is
crossed someone has to re-run + diff + alert. This cron replaces that manual
walk.

Pipeline
--------
Inputs (from the prior two workflow steps):
- /tmp/staff.json     — curated 6 conditions from tools/stamp_entry_conditions.py --stdout
- /tmp/mine.json      — exhaustive (class x dir x RSI-band x session) cells with FDR
                       from tools/mine_entry_condition_cells.py

Inputs (committed artifacts):
- audit_dashboard/data/crypto_rsi5070_us_forward_status.json — canonical lead-cell n
- audit_dashboard/data/entry_conditions_forward.json — per-cell live cohort
- audit_dashboard/data/winner_hunt_replay_payload.json — prior cycle's payload
                                                       (baseline for drift diff;
                                                        absent on first run)

Outputs:
- audit_dashboard/data/winner_hunt_replay_payload.json — today's payload
- updates/YYYY-MM-DD-winner-hunt-replay.md              — verdict doc (append-only,
                                                          one new file per cycle)
- GroupMarkers on stderr (GHA picks these up):
    ::error::   lead n >= 150  (PROMOTE THE LEAD)
    ::warning:: new_cell_found  (a fresh net-positive cell outside the 6 curated)

Usage
-----
    python3 tools/build_winner_hunt_replay.py --apply     # write JSON + MD, emit alerts
    python3 tools/build_winner_hunt_replay.py --stdout   # print payload, do not write
    python3 tools/build_winner_hunt_replay.py --strict   # refuse if no new payload
                                                        # (default: still write
                                                        # 'no change' verdict)
    python3 tools/build_winner_hunt_replay.py --skip-md  # don't write MD this cycle
                                                        # (used by manual dispatches
                                                        # that only want JSON)

Discipline
----------
- READ-ONLY against MySQL (the two hunt scripts own the DB queries; this script
  reads only the JSONs they wrote).
- NEVER mutates audit_dashboard/data/entry_conditions_forward.json or
  crypto_rsi5070_us_forward_status.json — those are owned by the forward-tracker
  cron.
- The verdict-doc filename is YYYY-MM-DD-winner-hunt-replay.md (idempotent on
  repeat runs of the same day: the workflow's `git diff --cached --quiet` skips
  the no-op commit; this script overwrites the MD if a same-day run is forced
  manually).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from typing import Any

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

STAFF_PATH = "/tmp/staff.json"
MINE_PATH = "/tmp/mine.json"
R5070_STATUS_PATH = os.path.join(
    REPO, "audit_dashboard", "data", "crypto_rsi5070_us_forward_status.json"
)
ENTRY_CONDS_PATH = os.path.join(
    REPO, "audit_dashboard", "data", "entry_conditions_forward.json"
)
PRIOR_PAYLOAD_PATH = os.path.join(
    REPO, "audit_dashboard", "data", "winner_hunt_replay_payload.json"
)
OUT_PAYLOAD_PATH = PRIOR_PAYLOAD_PATH  # overwrite in place; the workflow commits it
UPDATES_DIR = os.path.join(REPO, "updates")

LEAD_CELL_KEY = "crypto_rsi5070_us"
LEAD_N_GATE = 150

# FDR-pass + net-positive cell threshold (mirrors mine_entry_condition_cells.py):
#   net_pf >= 1.5 AND n >= MIN_N AND fdr_pass: true
# Steady-state policy: n >= 30 (matches MIN_N in mine); same bar as the source-of-truth
# alphas. First cycle policy (no prior baseline yet): n >= 100 — defensive bump to
# avoid alert spam on the very first run, when no drift diff exists.
NEW_CELL_MIN_N = 30
NEW_CELL_FIRST_CYCLE_MIN_N = 100
NEW_CELL_MIN_NET_PF = 1.5


def _load(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        print(f"::error::could not parse {path}: {exc}", file=sys.stderr)
        return None


def _load_curated_keys(staff: dict | None) -> set[str]:
    """The 6 canonical cell keys the stamp script curates — baseline for 'new' detection."""
    if not staff:
        return set()
    conds = staff.get("conditions") or {}
    return {k for k in conds.keys() if not k.startswith("baseline_")}


def _lead_status(r5070: dict | None, entry_conds: dict | None) -> dict[str, Any]:
    """Compose the lead-cell status block from BOTH canonical sources.

    Priority: forward_status (canonicalized verdict trail with verdict enum) > entry_conds
    (live per-cell cohort stats, refreshes hourly).
    """
    out: dict[str, Any] = {"cell": LEAD_CELL_KEY, "n_gate": LEAD_N_GATE}
    r5070_n = None
    r5070_status = None
    r5070_pf = None
    r5070_wr = None
    if r5070:
        # Forward-status file fields
        r5070_n = r5070.get("n") or r5070.get("forward_test_n")
        r5070_status = r5070.get("status") or r5070.get("verdict")
        r5070_pf = r5070.get("net_pf") or r5070.get("gross_pf")
        r5070_wr = r5070.get("wr_pct")
        out["source"] = "crypto_rsi5070_us_forward_status.json"
        out["failing_gates"] = r5070.get("failing_gates") or []
        out["gate_eta"] = r5070.get("gate_eta")
    if entry_conds:
        ec_cell = (entry_conds.get("conditions") or {}).get(LEAD_CELL_KEY) or {}
        if r5070_n is None:
            r5070_n = ec_cell.get("n")
        if r5070_wr is None:
            r5070_wr = ec_cell.get("wr")
        if r5070_pf is None:
            r5070_pf = ec_cell.get("net_pf") or ec_cell.get("pf")
        out["entry_conds_n"] = ec_cell.get("n")
        out["entry_conds_net_pf"] = ec_cell.get("net_pf")
        out["entry_conds_verdict_note"] = ec_cell.get("verdict_note")
    out["n"] = r5070_n
    out["wr_pct"] = r5070_wr
    out["net_pf"] = r5070_pf
    out["status"] = r5070_status
    out["passed_n150"] = (r5070_n is not None and r5070_n >= LEAD_N_GATE)
    return out


def _new_cells(mine: dict | None, curated_keys: set[str],
               prior_payload: dict | None) -> list[dict]:
    """Cells that pass net_pf>=NEW_CELL_MIN_NET_PF AND n>=NEW_CELL_MIN_N AND fdr_pass
    AND are NOT in the curated set AND were NOT in last cycle's baseline.

    First-cycle mode: when prior_payload is None (the very first run after the cron
    ships, no drift baseline yet), bump threshold from n>=30 to n>=100 so the alert
    isn't spammed by sub-promotion small-n cells. After one cycle, prior_payload
    naturally constrains alerts to the diff alone.
    """
    if not mine:
        return []
    prior_pass_keys = set()
    prior_payload_loaded = prior_payload is not None
    if prior_payload:
        prior_pass_keys = {
            c.get("cell") for c in (prior_payload.get("new_cells") or [])
            if c.get("cell")
        }
        # Also remember the lead and the curated set (defense in depth)
        for k in (prior_payload.get("lead") or {}).get("cell"),:
            prior_pass_keys.add(k)
    # First cycle: no baseline baseline = set is empty; all qualifying cells would
    # qualify. Bump threshold to n>=100 + emit a ::notice:: so the operator can see
    # we raised the bar defensively. After one cycle, prior_pass_keys naturally
    # constrains the diff.
    if not prior_payload_loaded:
        print("::notice::WINNER-HUNT first-cycle baseline missing; "
              f"new-cell threshold raised to n>={NEW_CELL_FIRST_CYCLE_MIN_N} "
              "(downstream cycles use n>=30 per the curated 6 discipline)",
              file=sys.stderr)
    eff_min_n = NEW_CELL_FIRST_CYCLE_MIN_N if not prior_payload_loaded else NEW_CELL_MIN_N
    candidates = []
    winners = mine.get("fdr_passing_net_pf_ge_1_5") or []
    for c in winners:
        cell_key = c.get("cell") or ""
        if cell_key in curated_keys:
            continue
        if cell_key == LEAD_CELL_KEY:
            continue
        if cell_key in prior_pass_keys:
            continue
        n = c.get("n") or 0
        net_pf = c.get("net_pf")
        fdr_pass = c.get("fdr_pass", False)
        if n >= eff_min_n and (net_pf is not None) and net_pf >= NEW_CELL_MIN_NET_PF and fdr_pass:
            candidates.append({
                "cell": cell_key, "n": n, "wr": c.get("wr"),
                "pf": c.get("pf"), "net_pf": net_pf,
                "p_value": c.get("p"), "fdr_pass": fdr_pass,
            })
    candidates.sort(key=lambda x: (-(x.get("net_pf") or 0), -x.get("n", 0)))
    return candidates


def _drift_table(current: dict | None, prior: dict | None) -> list[dict]:
    """Diff: current top-N net-positive FDR-pass cells vs prior cycle's same set.
    Delta columns are useful; +N=cell newly net-positive, -N=cell newly lost edge."""
    def keys(p):
        if not p:
            return set()
        s = set()
        for c in (p.get("new_cells") or []):
            ckey = c.get("cell")
            if ckey:
                s.add(ckey)
        s.add((p.get("lead") or {}).get("cell") or LEAD_CELL_KEY)
        return s
    cur_keys = keys(current)
    prior_keys = keys(prior)
    added = sorted(cur_keys - prior_keys)
    removed = sorted(prior_keys - cur_keys)
    return [
        {"change": "added_cell",   "cell": k, "implication": "freshly net-positive FDR-pass"}
        for k in added
    ] + [
        {"change": "lost_cell",    "cell": k, "implication": "no longer in net-positive row"}
        for k in removed
    ]


def _render_md(payload: dict) -> str:
    """Author the verdict-doc markdown from the JSON payload. DRY-git mode: cites
    canonical paths; inlines ONLY today's alert + lead n/pf + drift table cells —
    everything else is a link."""
    today = payload.get("generated_at", "")[:10] or dt.date.today().isoformat()
    lead = payload.get("lead") or {}
    new_cells = payload.get("new_cells") or []
    drift = payload.get("drift_table") or []
    alert_paths = payload.get("alerts") or {}

    md = []
    md.append(f"# Winner-hunt replay — {today}")
    md.append("")
    md.append(f"**Cycle:** monthly STA-09 re-audit, cron `0 8 1 * *` UTC.")
    md.append(f"**Generated:** {payload.get('generated_at')}")
    md.append(f"**Cohort size:** {payload.get('cohort_n')} picks · "
              f"{payload.get('stamped_n')} stamped.")
    md.append(f"**Ref lineage:** see `updates/2026-06-22-winner-hunt-replay-cron.md` "
              "(sibling spec).")
    md.append("")
    md.append("**DRY.git discipline:** this file cites canonical artifacts; raw hunt-output "
              "tables live in `/tmp/staff.json` + `/tmp/mine.json` (ephemeral on runner; "
              "see §8 of `updates/2026-06-22-winner-hunt-rsi5070-only.md` for what to read "
              "if those are gone). Re-derive the truth from the canonical JSONs.")
    md.append("")

    # Alerts
    md.append("## 1. Alerts")
    md.append("")
    if alert_paths.get("promote"):
        md.append(f"> **🔴 ::error:: PROMOTE THE LEAD.** `crypto_rsi5070_us` crossed the "
                  f"`n >= {LEAD_N_GATE}` promotion bar this cycle. `n = {lead.get('n')}` · "
                  f"WR% = {lead.get('wr_pct')} · net_pf = {lead.get('net_pf')}. Re-run R1/R2/R3 "
                  "and promote out of shadow-tracking in `audit_trail/quality_gates.py`.")
    elif alert_paths.get("new_cell"):
        cell_list = ", ".join(f"`{c.get('cell')}` (n={c.get('n')} net_pf={c.get('net_pf')})"
                              for c in new_cells)
        md.append(f"> **🟡 ::warning:: FRESH LEAD CANDIDATE(S).** {cell_list}. Outside the "
                  "curated 6 and outside last cycle's baseline — flag on the operator-review "
                  "sidecar next pass.")
    else:
        md.append("> **🟢 No new alerts.** Lead still in SHADOW_TRACKING; no fresh cells.")
    md.append("")

    # Lead
    md.append("## 2. Lead status — `crypto_rsi5070_us`")
    md.append("")
    md.append(f"- **n:** `{lead.get('n')}` (gate: `{LEAD_N_GATE}`) → "
              f"`{'✅ passed' if lead.get('passed_n150') else '⏳ still accruing'}`")
    md.append(f"- **WR%:** `{lead.get('wr_pct')}`")
    md.append(f"- **net_pf:** `{lead.get('net_pf')}`")
    md.append(f"- **status:** `{lead.get('status')}`")
    fd = lead.get("failing_gates") or []
    if fd:
        md.append(f"- **failing gates (forward-status):** `{', '.join(fd)}`")
    md.append("")
    md.append("Read the canonical truth at "
              "`audit_dashboard/data/crypto_rsi5070_us_forward_status.json` (refreshed hourly "
              "by `tools/crypto_rsi5070_forward_tracker.py`).")
    md.append("")

    # New cells
    md.append("## 3. Fresh cells (net-positive FDR-pass, NOT in curated set)")
    md.append("")
    if not new_cells:
        md.append("_None this cycle. rsi5070 remains the lone survivor._")
    else:
        md.append("| Cell | n | WR% | net_pf | FDR-pass |")
        md.append("|---|---|---|---|---|")
        for c in new_cells:
            md.append(f"| `{c.get('cell')}` | {c.get('n')} | "
                      f"{c.get('wr')} | {c.get('net_pf')} | {c.get('fdr_pass')} |")
    md.append("")

    # Drift
    md.append("## 4. Drift vs prior cycle")
    md.append("")
    if not drift:
        md.append("_No drift — top-N set from this cycle matches last cycle's set "
                  "(modulo n deltas)._")
    else:
        md.append("| Change | Cell | Implication |")
        md.append("|---|---|---|")
        for d in drift:
            md.append(f"| {d.get('change')} | `{d.get('cell')}` | {d.get('implication')} |")
    md.append("")
    md.append("Baseline lives at `audit_dashboard/data/winner_hunt_replay_payload.json` "
              "(this file's committed sibling). The current cycle's payload overwrites the "
              "baseline on the next monthly run.")
    md.append("")

    # Verdict
    md.append("## 5. Verdict")
    md.append("")
    if alert_paths.get("promote"):
        md.append("**PROMOTE.** The lead crossed the n≥150 promotion bar. Next step: re-run "
                  "R1/R2/R3 gates per `tools/crypto_rsi5070_forward_tracker.py` and lift the "
                  "shadow-tracking flag in `audit_trail/quality_gates.py` if all gates pass.")
    elif alert_paths.get("new_cell"):
        md.append("**WATCH.** A new net-positive FDR-pass cell surfaced. Manually review it "
                  "via the operator-review sidecar and decide if it warrants its own "
                  "forward-tracker before the next monthly cycle.")
    else:
        md.append("**HOLD.** rsi5070 accruing as expected; no fresh leads. Continue monthly "
                  "cadence.")
    md.append("")

    # Maintenance
    md.append("## 6. Maintenance")
    md.append("")
    md.append("Trigger `gh workflow run winner-hunt-replay.yml --ref main` to force a manual "
              "replay. Append-only: this filename (YYYY-MM-DD) prevents collision.")
    md.append("")
    return "\n".join(md) + "\n"


def build_payload() -> dict[str, Any]:
    staff = _load(STAFF_PATH)
    mine = _load(MINE_PATH)
    r5070 = _load(R5070_STATUS_PATH)
    entry_conds = _load(ENTRY_CONDS_PATH)
    prior = _load(PRIOR_PAYLOAD_PATH)

    curated_keys = _load_curated_keys(staff)
    lead = _lead_status(r5070, entry_conds)
    new_cells = _new_cells(mine, curated_keys, prior)
    drift = _drift_table({"new_cells": new_cells, "lead": lead}, prior)

    alerts = {
        "promote":   bool(lead.get("passed_n150")),
        "new_cell":  bool(new_cells),
    }

    payload = {
        "_schema_note": "Generated by tools/build_winner_hunt_replay.py; "
                        "winner-hunt-replay-only payload (ALERT data, "
                        "not sizing input). Read-only replay of the "
                        "STA-09 hunt. NEVER treat as sizing input.",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "generated_by": "tools/build_winner_hunt_replay.py",
        "winner_hunt_replay_only": True,
        "cohort_n": (staff or {}).get("cohort_n") or (mine or {}).get("cohort_n"),
        "stamped_n": (staff or {}).get("stamped_n") or (mine or {}).get("stamped_n"),
        "cell_under_audit": LEAD_CELL_KEY,
        "n_gate": LEAD_N_GATE,
        "lead": lead,
        "new_cells": new_cells,
        "drift_table": drift,
        "alerts": alerts,
        "discipline_note": "Forward-shadow only; never a sizing input until n>=150 + "
                           "R1/R2/R3 re-pass. See updates/2026-06-22-winner-hunt-replay-cron.md.",
    }

    # === GHA groupMarkers ===
    if alerts["promote"]:
        print(f"::error::WINNER-HUNT PROMOTE lead={LEAD_CELL_KEY} "
              f"n={lead.get('n')} wr_pct={lead.get('wr_pct')} net_pf={lead.get('net_pf')}",
              file=sys.stderr)
    if alerts["new_cell"]:
        cells_str = ", ".join(f"{c.get('cell')} (n={c.get('n')}, net_pf={c.get('net_pf')})"
                              for c in new_cells)
        print(f"::warning::WINNER-HUNT NEW_CELL_FOUND {cells_str}", file=sys.stderr)
    if not (alerts["promote"] or alerts["new_cell"]):
        print(f"::notice::WINNER-HUNT no alerts; lead still accruing "
              f"(n={lead.get('n')}/{LEAD_N_GATE})", file=sys.stderr)

    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Write payload.json + verdict MD to disk.")
    ap.add_argument("--stdout", action="store_true", help="Print payload JSON to stdout; do not write.")
    ap.add_argument("--strict", action="store_true", help="Refuse to run if /tmp/staff.json OR "
                                                         "/tmp/mine.json is missing (default: warn + run).")
    ap.add_argument("--skip-md", action="store_true", help="Don't write the verdict MD this cycle "
                                                          "(manual dispatches sometimes want JSON only).")
    args = ap.parse_args()

    if args.strict and (not os.path.exists(STAFF_PATH) or not os.path.exists(MINE_PATH)):
        missing = [p for p in (STAFF_PATH, MINE_PATH) if not os.path.exists(p)]
        raise SystemExit(f"STRICT: missing input JSON(s): {missing}")

    payload = build_payload()
    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    today_iso = payload["generated_at"][:10] or dt.date.today().isoformat()
    # Time-suffix on force=true reruns: don't overwrite today's verdict doc; create a
    # sibling with HHMM suffix. Workflow dispatcher can pass env var; default nameless.
    suffix = (os.environ.get("WINNER_HUNT_TIME_SUFFIX", "") or "").strip()
    md_basename = f"{today_iso}-winner-hunt-replay{('-' + suffix) if suffix else ''}.md"
    md_path = os.path.join(UPDATES_DIR, md_basename)

    if args.stdout or not args.apply:
        print(serialized)
        if not args.apply:
            return 0

    if args.apply:
        # Atomic write pattern: write_to_tmp + os.replace. Avoids partial-write on
        # runner crash causing next cycle's `_load()` to read corrupt baseline.
        os.makedirs(os.path.dirname(OUT_PAYLOAD_PATH), exist_ok=True)
        tmp_payload = OUT_PAYLOAD_PATH + ".tmp"
        with open(tmp_payload, "w", encoding="utf-8") as fh:
            fh.write(serialized + "\n")
        os.replace(tmp_payload, OUT_PAYLOAD_PATH)
        os.chmod(OUT_PAYLOAD_PATH, 0o644)
        print(f"OK wrote {OUT_PAYLOAD_PATH} ({os.path.getsize(OUT_PAYLOAD_PATH)}B)", file=sys.stderr)

        if not args.skip_md:
            os.makedirs(UPDATES_DIR, exist_ok=True)
            tmp_md = md_path + ".tmp"
            with open(tmp_md, "w", encoding="utf-8") as fh:
                fh.write(_render_md(payload))
            os.replace(tmp_md, md_path)
            os.chmod(md_path, 0o644)
            print(f"OK wrote {md_path} ({os.path.getsize(md_path)}B; "
                  f"alerts={list((payload.get('alerts') or {}).keys())})", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
