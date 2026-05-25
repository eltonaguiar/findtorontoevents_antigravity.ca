"""
Deploy generated /audit/* artifacts to findtorontoevents.ca via FTPS.

WHY: 50webs has no shell — nightly GH-Actions commits land on git/main but
the live site keeps serving stale files until someone FTP-uploads. This
script closes that gap for the audit-dashboard artifacts (incidents page,
pick-funnel page, sidecar JSONs, the updates index, etc).

USAGE
  FTP_USER=ejaguiar1 FTP_PASS=... python3 tools/deploy_audit_files.py
  FTP_USER=ejaguiar1 FTP_PASS=... python3 tools/deploy_audit_files.py --dry-run
  FTP_USER=ejaguiar1 FTP_PASS=... python3 tools/deploy_audit_files.py --only incidents

Each upload is logged with size + post-upload HTTP HEAD verification. Soft-fail
on individual files so one missing file doesn't abort the whole batch (matches
the GH-Actions soft-fail pattern).
"""
from __future__ import annotations
import os, ssl, sys, argparse, urllib.request
from ftplib import FTP_TLS
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# (local_path_relative_to_repo, remote_path_on_50webs, optional_tag)
UPLOADS = [
    ("audit_dashboard/incidents.html",                       "/findtorontoevents.ca/audit/incidents.html",                        "incidents"),
    ("audit_dashboard/data/incidents_enhancements_feed.json","/findtorontoevents.ca/audit/data/incidents_enhancements_feed.json", "incidents"),
    ("audit_dashboard/pick_funnel.html",                     "/findtorontoevents.ca/audit/pick_funnel.html",                      "pick_funnel"),
    ("audit_dashboard/data/pick_funnel_today.json",          "/findtorontoevents.ca/audit/data/pick_funnel_today.json",           "pick_funnel"),
    ("audit_dashboard/data/pick_funnel_90d.json",            "/findtorontoevents.ca/audit/data/pick_funnel_90d.json",             "pick_funnel"),
    ("audit_dashboard/data/pick_funnel_rejected_universe.json", "/findtorontoevents.ca/audit/data/pick_funnel_rejected_universe.json", "pick_funnel"),
    ("audit_dashboard/data/top_edges_per_class.json",        "/findtorontoevents.ca/audit/data/top_edges_per_class.json",         "pick_funnel"),
    ("audit_dashboard/model.html",                           "/findtorontoevents.ca/audit/model.html",                            "model"),
    ("audit_dashboard/ai-tournament.html",                   "/findtorontoevents.ca/audit/ai-tournament.html",                    "ai_tournament"),
    ("audit_dashboard/data/ai_tournament_picks_latest.json", "/findtorontoevents.ca/audit/data/ai_tournament_picks_latest.json",  "ai_tournament"),
    ("audit_dashboard/data/ai_tournament_model_summary.json","/findtorontoevents.ca/audit/data/ai_tournament_model_summary.json", "ai_tournament"),
    ("audit_dashboard/data/ai_tournament_leaderboard.json",  "/findtorontoevents.ca/audit/data/ai_tournament_leaderboard.json",   "ai_tournament"),
    ("updates/index.html",                                   "/findtorontoevents.ca/updates/index.html",                          "updates"),
]


def upload(ftps: FTP_TLS, local: Path, remote: str, dry_run: bool) -> tuple[bool, str]:
    if not local.exists():
        return False, "local missing"
    parts = remote.strip("/").split("/")
    dirs, fname = parts[:-1], parts[-1]
    if dry_run:
        return True, f"DRY-RUN would upload {local.stat().st_size:,} bytes"
    try:
        ftps.cwd("/")
        for d in dirs:
            try: ftps.mkd(d)
            except Exception: pass
            ftps.cwd(d)
        with open(local, "rb") as f:
            ftps.storbinary(f"STOR {fname}", f)
        return True, f"{local.stat().st_size:,} bytes"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def verify(remote: str) -> tuple[bool, str]:
    """50webs Apache returns 412 on default urllib HEAD, so use GET with Range:0-0
    and a real User-Agent. Validates the file exists + is reachable without
    downloading the whole body."""
    url = "https://findtorontoevents.ca" + remote.replace("/findtorontoevents.ca", "")
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 audit-deploy-verify",
            "Range": "bytes=0-0",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            cl = resp.headers.get("content-range", resp.headers.get("content-length", "?"))
            return resp.status in (200, 206), f"HTTP {resp.status} · {cl}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", help="Only upload files with this tag (incidents/pick_funnel/model/ai_tournament/updates)")
    ap.add_argument("--no-verify", action="store_true", help="Skip post-upload HTTP HEAD")
    args = ap.parse_args()

    user = os.environ.get("FTP_USER")
    pw = os.environ.get("FTP_PASS")
    host = os.environ.get("FTP_SERVER", "ftps2.50webs.com")
    if not (user and pw):
        print("ERROR: FTP_USER + FTP_PASS env vars required", file=sys.stderr)
        sys.exit(2)

    targets = UPLOADS if not args.only else [t for t in UPLOADS if t[2] == args.only]
    if not targets:
        print(f"No uploads match --only {args.only}", file=sys.stderr); sys.exit(2)

    print(f"Target host: {host}  user: {user}  uploads: {len(targets)}  dry-run: {args.dry_run}")
    ftps = None
    if not args.dry_run:
        ftps = FTP_TLS(host, timeout=30)
        ftps.login(user, pw)
        ftps.prot_p()

    ok = fail = 0
    verify_results = []
    for local_rel, remote, tag in targets:
        local = REPO / local_rel
        success, msg = upload(ftps, local, remote, args.dry_run)
        marker = "  OK  " if success else "  FAIL"
        print(f"{marker}  [{tag:14s}] {remote}  ({msg})")
        ok += int(success); fail += int(not success)
        if success and not args.dry_run and not args.no_verify:
            ok_v, msg_v = verify(remote)
            verify_results.append((remote, ok_v, msg_v))

    if ftps:
        try: ftps.quit()
        except Exception: pass

    if verify_results:
        print("\nVerify (HTTP HEAD on live URLs):")
        for r, ok_v, msg_v in verify_results:
            marker = "  OK  " if ok_v else "  FAIL"
            print(f"{marker}  https://findtorontoevents.ca{r.replace('/findtorontoevents.ca','')}  ({msg_v})")

    print(f"\n{ok} uploaded, {fail} failed")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
