"""Summarize gh run list JSON: failures per workflow, stalled runs."""
import json
import subprocess
import sys
from collections import defaultdict

def main():
    raw = subprocess.check_output(
        ["gh", "run", "list", "--limit", "500", "--json",
         "workflowName,conclusion,status,createdAt,updatedAt,databaseId,headBranch"],
        text=True,
    )
    data = json.loads(raw)
    stats = defaultdict(
        lambda: {
            "fail": 0,
            "success": 0,
            "cancelled": 0,
            "other": 0,
            "last_success": None,
            "last_fail": None,
            "in_prog": [],
        }
    )
    for r in data:
        w = r["workflowName"]
        c = r.get("conclusion") or ""
        st = r.get("status") or ""
        if st in ("in_progress", "queued", "pending", "waiting"):
            stats[w]["in_prog"].append((r["databaseId"], st, r["updatedAt"], r.get("headBranch")))
        if c == "failure":
            stats[w]["fail"] += 1
            stats[w]["last_fail"] = stats[w]["last_fail"] or r["createdAt"]
        elif c == "success":
            stats[w]["success"] += 1
            ls = stats[w]["last_success"]
            if not ls or r["createdAt"] > ls:
                stats[w]["last_success"] = r["createdAt"]
        elif c == "cancelled":
            stats[w]["cancelled"] += 1
        elif c:
            stats[w]["other"] += 1

    rows = []
    for w, s in stats.items():
        total = s["fail"] + s["success"] + s["cancelled"] + s["other"]
        if total < 2 and s["fail"] < 2 and not s["in_prog"]:
            continue
        failr = s["fail"] / max(total, 1)
        rows.append(
            (s["fail"], failr, s["success"], w, s["last_success"], s["last_fail"], len(s["in_prog"]))
        )
    rows.sort(key=lambda x: (-x[0], -x[1]))

    print("=== High failure count (last 500 runs, all branches) ===")
    for row in rows[:30]:
        print(
            f"fail={row[0]} ok={row[2]} rate={row[1]:.2f} active={row[6]} | {row[3][:75]}"
        )
        print(f"    last_success={row[4]}  (in sample)")

    print("\n=== Workflows with NO success in sample but 2+ failures ===")
    for row in rows:
        if row[2] == 0 and row[0] >= 2:
            print(f"fail={row[0]} | {row[3]}")

    print("\n=== Currently active (from sample) ===")
    for w, s in sorted(stats.items(), key=lambda x: -len(x[1]["in_prog"])):
        if not s["in_prog"]:
            continue
        print(f"{w}: {len(s['in_prog'])} runs")
        for tid, st, upd, br in s["in_prog"][:5]:
            print(f"  id={tid} {st} branch={br} updated={upd}")


if __name__ == "__main__":
    main()
