"""
CLI for creating + updating rows in INCIDENT_<CLASS> / ENHANCEMENT_<CLASS>
tables on the live ejaguiar1_stocks DB. Wraps idempotent UPSERT so the same
title in the same class is updated, not duplicated. Outputs the row id +
public link so the skill can hand it back to the user.

Usage examples:

  # create or update an incident
  python tools/audit_pick_funnel/cli_track.py incident \\
      --class CRYPTO \\
      --title "quan_engine_scalp PF 0.42 drag on CRYPTO PF" \\
      --severity P1 --status OPEN \\
      --component "alpha_engine/quan_engine.py" \\
      --description "..." --fix "cut volume share or kill" \\
      --reporter claude-opus-4-7 \\
      --link-md "reports/2026-05-25_audit_ui_edge_audit.md" \\
      --link-github 4102b2b6

  # resolve an existing incident by id
  python tools/audit_pick_funnel/cli_track.py update-incident \\
      --class OVERALL --id 4 --status RESOLVED \\
      --resolution-notes "fixed in commits 702eac27 + c5fcbdc1"

  # bulk export (for jq / grep)
  python tools/audit_pick_funnel/cli_track.py list --class OVERALL --status OPEN --severity P0,P1
"""
from __future__ import annotations
import argparse, json, os, sys
import pymysql

CLASSES = ["OVERALL", "STOCKS", "ETFS", "CRYPTO", "FOREX", "COMMODITIES", "BONDS", "FUTURES", "PENNY"]
SEVERITIES = ["P0", "P1", "P2", "P3", "INFO"]
INC_STATUS = ["OPEN", "TRIAGED", "IN_PROGRESS", "RESOLVED", "WONTFIX", "DUPLICATE"]
ENH_STATUS = ["BACKLOG", "VALIDATED", "ACCEPTED", "IMPLEMENTED", "REJECTED", "SUPERSEDED"]
ENH_CATEGORIES = ["SCORING", "GATE", "DATA_FEED", "UI", "METHODOLOGY", "PERSONA", "OTHER"]
IMPACTS = ["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
EFFORTS = ["S", "M", "L", "XL"]
FINDING_SEVERITIES = ["P0", "P1", "P2", "P3", "INFO", "NOTEWORTHY"]
FINDING_STATUS = ["OPEN", "INVESTIGATING", "CONFIRMED", "RESOLVED", "WONTFIX"]


def _connect():
    return pymysql.connect(
        host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
        user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
        password=os.environ["DB_PASS_STOCKS"],
        database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
        port=3306, connect_timeout=20, autocommit=False,
        cursorclass=pymysql.cursors.DictCursor)


def _resolve_table(kind: str, cls: str) -> str:
    cls = cls.upper()
    if cls not in CLASSES:
        sys.exit(f"--class must be one of {CLASSES}")
    return f"{kind}_{cls}"


def cmd_incident(args):
    """Create-or-update an incident keyed on (table, title)."""
    if args.severity not in SEVERITIES: sys.exit(f"--severity must be {SEVERITIES}")
    if args.status not in INC_STATUS:   sys.exit(f"--status must be {INC_STATUS}")
    tbl = _resolve_table("INCIDENT", args.cls)
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute(f"SELECT incident_id FROM {tbl} WHERE title=%s", (args.title,))
        existing = cur.fetchone()
        if existing:
            cur.execute(f"""UPDATE {tbl} SET description=%s, severity=%s, status=%s,
                affected_component=%s, recommended_fix=%s, reported_by=%s,
                link_md_path=%s, link_url=%s, link_github_ref=%s,
                target_release=COALESCE(%s, target_release),
                resolution_notes=COALESCE(%s, resolution_notes),
                resolved_at=CASE WHEN %s IN ('RESOLVED','WONTFIX','DUPLICATE') AND resolved_at IS NULL THEN NOW() ELSE resolved_at END
                WHERE incident_id=%s""",
                (args.description, args.severity, args.status, args.component,
                 args.fix, args.reporter, args.link_md, args.link_url, args.link_github,
                 args.target_release, args.resolution_notes, args.status, existing["incident_id"]))
            conn.commit()
            print(f"UPDATED  {tbl}.incident_id={existing['incident_id']}  title={args.title!r}")
        else:
            cur.execute(f"""INSERT INTO {tbl}
                (title, description, severity, status, affected_component, recommended_fix,
                 reported_by, link_md_path, link_url, link_github_ref, target_release)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (args.title, args.description, args.severity, args.status, args.component,
                 args.fix, args.reporter, args.link_md, args.link_url, args.link_github, args.target_release))
            new_id = cur.lastrowid
            conn.commit()
            print(f"CREATED  {tbl}.incident_id={new_id}  title={args.title!r}")
    conn.close()


def cmd_update_incident(args):
    """Patch one column on an existing row by id (lightweight 'resolve' / 'reassign')."""
    tbl = _resolve_table("INCIDENT", args.cls)
    sets, params = [], []
    if args.status:
        if args.status not in INC_STATUS: sys.exit(f"--status must be {INC_STATUS}")
        sets.append("status=%s"); params.append(args.status)
        if args.status in ("RESOLVED", "WONTFIX", "DUPLICATE"):
            sets.append("resolved_at=IFNULL(resolved_at, NOW())")
    if args.severity:
        if args.severity not in SEVERITIES: sys.exit(f"--severity must be {SEVERITIES}")
        sets.append("severity=%s"); params.append(args.severity)
    if args.resolution_notes is not None:
        sets.append("resolution_notes=%s"); params.append(args.resolution_notes)
    if args.assigned_to:
        sets.append("assigned_to=%s"); params.append(args.assigned_to)
    if args.link_github:
        sets.append("link_github_ref=%s"); params.append(args.link_github)
    if not sets:
        sys.exit("nothing to update — pass at least one of --status / --severity / --resolution-notes / --assigned-to / --link-github")
    conn = _connect()
    with conn.cursor() as cur:
        params.append(args.id)
        cur.execute(f"UPDATE {tbl} SET {', '.join(sets)} WHERE incident_id=%s", params)
        if cur.rowcount == 0:
            sys.exit(f"no row matched {tbl}.incident_id={args.id}")
    conn.commit()
    conn.close()
    print(f"UPDATED  {tbl}.incident_id={args.id}  fields={[s.split('=')[0] for s in sets]}")


def cmd_enhancement(args):
    """Create-or-update an enhancement keyed on (table, title)."""
    if args.category not in ENH_CATEGORIES: sys.exit(f"--category must be {ENH_CATEGORIES}")
    if args.impact   not in IMPACTS:        sys.exit(f"--impact must be {IMPACTS}")
    if args.effort   not in EFFORTS:        sys.exit(f"--effort must be {EFFORTS}")
    if args.status   not in ENH_STATUS:     sys.exit(f"--status must be {ENH_STATUS}")
    tbl = _resolve_table("ENHANCEMENT", args.cls)
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute(f"SELECT enhancement_id FROM {tbl} WHERE title=%s", (args.title,))
        existing = cur.fetchone()
        if existing:
            cur.execute(f"""UPDATE {tbl} SET description=%s, category=%s, expected_impact=%s,
                effort=%s, status=%s, proposed_by=%s, related_persona_id=%s, success_metric=%s,
                link_md_path=%s, link_url=%s, link_github_ref=%s,
                target_release=COALESCE(%s, target_release),
                enhancement_plan=COALESCE(%s, enhancement_plan),
                implementation_pr=COALESCE(%s, implementation_pr),
                implemented_at=CASE WHEN %s='IMPLEMENTED' AND implemented_at IS NULL THEN NOW() ELSE implemented_at END
                WHERE enhancement_id=%s""",
                (args.description, args.category, args.impact, args.effort, args.status,
                 args.proposed_by, args.persona, args.success_metric,
                 args.link_md, args.link_url, args.link_github, args.target_release,
                 args.enhancement_plan, args.implementation_pr,
                 args.status, existing["enhancement_id"]))
            conn.commit()
            print(f"UPDATED  {tbl}.enhancement_id={existing['enhancement_id']}  title={args.title!r}")
        else:
            cur.execute(f"""INSERT INTO {tbl}
                (title, description, category, expected_impact, effort, status, proposed_by,
                 related_persona_id, success_metric, link_md_path, link_url, link_github_ref,
                 target_release, enhancement_plan)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (args.title, args.description, args.category, args.impact, args.effort, args.status,
                 args.proposed_by, args.persona, args.success_metric,
                 args.link_md, args.link_url, args.link_github, args.target_release,
                 args.enhancement_plan))
            new_id = cur.lastrowid
            conn.commit()
            print(f"CREATED  {tbl}.enhancement_id={new_id}  title={args.title!r}")
    conn.close()


def cmd_finding(args):
    """Create-or-update a FINDING (per-class FINDING_<CLASS> table, upsert by title).

    Findings are dated, agent-logged notes (some standalone NOTEWORTHY observations,
    some linked to an incident/enhancement). created_at_utc is left to the DB default
    (UTC CURRENT_TIMESTAMP); EST is derived at render time — never store EST here.

    Mirrors INCIDENT_<CLASS> / ENHANCEMENT_<CLASS> upsert semantics (idempotent by
    title within the class table).
    """
    if args.severity not in FINDING_SEVERITIES:
        sys.exit(f"--severity must be {FINDING_SEVERITIES}")
    if args.status not in FINDING_STATUS:
        sys.exit(f"--status must be {FINDING_STATUS}")
    tbl = _resolve_table("FINDING", args.cls)
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute(f"SELECT id FROM {tbl} WHERE title=%s", (args.title,))
        existing = cur.fetchone()
        if existing:
            cur.execute(f"""INSERT INTO {tbl}
                    (id, title, description, severity, status, agent, evidence,
                     linked_incident_id, linked_enhancement_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    description=COALESCE(VALUES(description), description),
                    severity=VALUES(severity),
                    status=VALUES(status),
                    agent=COALESCE(VALUES(agent), agent),
                    evidence=COALESCE(VALUES(evidence), evidence),
                    linked_incident_id=COALESCE(VALUES(linked_incident_id), linked_incident_id),
                    linked_enhancement_id=COALESCE(VALUES(linked_enhancement_id), linked_enhancement_id)""",
                (existing["id"], args.title, args.description, args.severity, args.status,
                 args.agent, args.evidence, args.linked_incident, args.linked_enhancement))
            conn.commit()
            row_id = existing["id"]
        else:
            cur.execute(f"""INSERT INTO {tbl}
                    (title, description, severity, status, agent, evidence,
                     linked_incident_id, linked_enhancement_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    description=COALESCE(VALUES(description), description),
                    severity=VALUES(severity),
                    status=VALUES(status),
                    agent=COALESCE(VALUES(agent), agent),
                    evidence=COALESCE(VALUES(evidence), evidence),
                    linked_incident_id=COALESCE(VALUES(linked_incident_id), linked_incident_id),
                    linked_enhancement_id=COALESCE(VALUES(linked_enhancement_id), linked_enhancement_id)""",
                (args.title, args.description, args.severity, args.status,
                 args.agent, args.evidence, args.linked_incident, args.linked_enhancement))
            row_id = cur.lastrowid
            conn.commit()
    conn.close()
    print(f"[finding] {tbl}#{row_id} {args.severity} {args.title}")


def cmd_list(args):
    """Quick search / triage view."""
    kind = args.kind.upper()
    if kind not in ("INCIDENT", "ENHANCEMENT"): sys.exit("--kind must be INCIDENT or ENHANCEMENT")
    view = "vw_all_incidents" if kind == "INCIDENT" else "vw_all_enhancements"
    where, params = [], []
    if args.cls:
        cs = [c.upper() for c in args.cls.split(",")]
        where.append(f"asset_class IN ({','.join(['%s']*len(cs))})"); params += cs
    if args.status:
        ss = args.status.split(",")
        where.append(f"status IN ({','.join(['%s']*len(ss))})"); params += ss
    if args.severity and kind == "INCIDENT":
        sv = args.severity.split(",")
        where.append(f"severity IN ({','.join(['%s']*len(sv))})"); params += sv
    if args.reporter:
        where.append("(reported_by LIKE %s OR proposed_by LIKE %s)"); params += [f"%{args.reporter}%"]*2
    sql = f"SELECT * FROM {view}"
    if where: sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY " + ("FIELD(severity,'P0','P1','P2','P3','INFO')" if kind == "INCIDENT" else "FIELD(expected_impact,'HIGH','MEDIUM','LOW','UNKNOWN')")
    sql += ", created_at DESC LIMIT %s"; params.append(args.limit)
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    conn.close()
    if args.json:
        print(json.dumps(rows, indent=2, default=str))
        return
    for r in rows:
        if kind == "INCIDENT":
            print(f"  [{r['severity']}/{r['status']:>11s}] {r['asset_class']:11s} #{r['incident_id']:<4d} {r['title']}")
        else:
            print(f"  [{r['expected_impact']}/{r['effort']}/{r['status']:>11s}] {r['asset_class']:11s} #{r['enhancement_id']:<4d} {r['title']}")
    print(f"\n{len(rows)} row(s)")


def main():
    p = argparse.ArgumentParser(description="Create/update INCIDENT_* + ENHANCEMENT_* + FINDING_* rows on live ejaguiar1_stocks.")
    sub = p.add_subparsers(dest="cmd", required=True)

    inc = sub.add_parser("incident", help="Create or update an incident (upsert by title within class).")
    inc.add_argument("--class", dest="cls", required=True, help=f"One of {CLASSES}")
    inc.add_argument("--title", required=True)
    inc.add_argument("--description", default=None)
    inc.add_argument("--severity", default="P2", help=f"One of {SEVERITIES}")
    inc.add_argument("--status", default="OPEN", help=f"One of {INC_STATUS}")
    inc.add_argument("--component", default=None, help="affected_component (file path / table name)")
    inc.add_argument("--fix", default=None, help="recommended_fix")
    inc.add_argument("--reporter", default=None)
    inc.add_argument("--link-md", default=None, help="repo-relative path to a doc, e.g. reports/foo.md")
    inc.add_argument("--link-url", default=None, help="public URL of affected page")
    inc.add_argument("--link-github", default=None, help="PR #, issue #, or commit SHA (comma-separated)")
    inc.add_argument("--target-release", dest="target_release", default=None, help="ETA, e.g. '2026-06-15 17:00 EST' or 'YYYY-MM-DD'")
    inc.add_argument("--resolution-notes", default=None)
    inc.set_defaults(func=cmd_incident)

    up = sub.add_parser("update-incident", help="Patch one or more fields on an existing incident by id.")
    up.add_argument("--class", dest="cls", required=True)
    up.add_argument("--id", type=int, required=True)
    up.add_argument("--status", default=None)
    up.add_argument("--severity", default=None)
    up.add_argument("--resolution-notes", default=None)
    up.add_argument("--assigned-to", default=None)
    up.add_argument("--link-github", default=None)
    up.set_defaults(func=cmd_update_incident)

    enh = sub.add_parser("enhancement", help="Create or update an enhancement (upsert by title within class).")
    enh.add_argument("--class", dest="cls", required=True)
    enh.add_argument("--title", required=True)
    enh.add_argument("--description", default=None)
    enh.add_argument("--category", default="OTHER", help=f"One of {ENH_CATEGORIES}")
    enh.add_argument("--impact", default="UNKNOWN", help=f"One of {IMPACTS}")
    enh.add_argument("--effort", default="M", help=f"One of {EFFORTS}")
    enh.add_argument("--status", default="BACKLOG", help=f"One of {ENH_STATUS}")
    enh.add_argument("--proposed-by", default=None)
    enh.add_argument("--persona", default=None, help="related_persona_id")
    enh.add_argument("--success-metric", default=None)
    enh.add_argument("--link-md", default=None)
    enh.add_argument("--link-url", default=None)
    enh.add_argument("--link-github", default=None)
    enh.add_argument("--target-release", dest="target_release", default=None, help="ETA, e.g. '2026-06-15 17:00 EST' or 'YYYY-MM-DD'")
    enh.add_argument("--enhancement-plan", dest="enhancement_plan", default=None,
        help="Free-text implementation plan; can be extracted from linked reports")
    enh.add_argument("--implementation-pr", default=None)
    enh.set_defaults(func=cmd_enhancement)

    fnd = sub.add_parser("finding", help="Log a dated finding in FINDING_<CLASS> (upsert by title; optionally link to incident/enhancement).")
    fnd.add_argument("--class", dest="cls", required=True, help=f"One of {CLASSES}")
    fnd.add_argument("--title", required=True, help="Upsert key — same title within a class updates the existing row")
    fnd.add_argument("--description", default=None)
    fnd.add_argument("--severity", default="INFO", help=f"One of {FINDING_SEVERITIES}")
    fnd.add_argument("--status", default="OPEN", help=f"One of {FINDING_STATUS}")
    fnd.add_argument("--agent", default=None, help="Who logged it (e.g. claude-opus-4-7, grok-4.3, freebuff)")
    fnd.add_argument("--evidence", default=None, help="file:line refs, cite reports/, etc.")
    fnd.add_argument("--linked-incident-id", dest="linked_incident", type=int, default=None, help="INCIDENT_<class>.incident_id")
    fnd.add_argument("--linked-enhancement-id", dest="linked_enhancement", type=int, default=None, help="ENHANCEMENT_<class>.enhancement_id")
    fnd.set_defaults(func=cmd_finding)

    ls = sub.add_parser("list", help="List/search rows.")
    ls.add_argument("--kind", required=True, help="incident | enhancement")
    ls.add_argument("--class", dest="cls", default=None, help="comma-separated class filter")
    ls.add_argument("--status", default=None, help="comma-separated status filter")
    ls.add_argument("--severity", default=None, help="comma-separated severity filter (incidents only)")
    ls.add_argument("--reporter", default=None, help="LIKE match on reported_by or proposed_by")
    ls.add_argument("--limit", type=int, default=50)
    ls.add_argument("--json", action="store_true")
    ls.set_defaults(func=cmd_list)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
