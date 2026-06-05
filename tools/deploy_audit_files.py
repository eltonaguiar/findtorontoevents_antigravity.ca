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
    ("audit_dashboard/strategy_audit_summary.html",          "/findtorontoevents.ca/audit/strategy_audit_summary.html",          "pick_funnel"),
    ("audit_dashboard/strategy_complete_summary.html",       "/findtorontoevents.ca/audit/strategy_complete_summary.html",       "pick_funnel"),
    ("audit_dashboard/pick_funnel.html",                     "/findtorontoevents.ca/audit/pick_funnel.html",                      "pick_funnel"),
    ("audit_dashboard/data/pick_funnel_today.json",          "/findtorontoevents.ca/audit/data/pick_funnel_today.json",           "pick_funnel"),
    ("audit_dashboard/data/pick_funnel_90d.json",            "/findtorontoevents.ca/audit/data/pick_funnel_90d.json",             "pick_funnel"),
    ("audit_dashboard/data/pick_funnel_rejected_universe.json", "/findtorontoevents.ca/audit/data/pick_funnel_rejected_universe.json", "pick_funnel"),
    ("audit_dashboard/data/top_edges_per_class.json",        "/findtorontoevents.ca/audit/data/top_edges_per_class.json",         "pick_funnel"),
    ("audit_dashboard/data/strategy_funnel_data.json",        "/findtorontoevents.ca/audit/data/strategy_funnel_data.json",         "pick_funnel"),
    ("audit_dashboard/data/nav_surface_edge_matrix.json",    "/findtorontoevents.ca/audit/data/nav_surface_edge_matrix.json",     "pick_funnel"),
    ("audit_dashboard/data/strategy_ic_analysis.json",        "/findtorontoevents.ca/audit/data/strategy_ic_analysis.json",         "pick_funnel"),
    ("audit_dashboard/model.html",                           "/findtorontoevents.ca/audit/model.html",                            "model"),
    ("audit_dashboard/ai-tournament.html",                   "/findtorontoevents.ca/audit/ai-tournament.html",                    "ai_tournament"),
    ("audit_dashboard/ai_postmortem_helper.js",              "/findtorontoevents.ca/audit/ai_postmortem_helper.js",               "ai_tournament"),
    ("audit_dashboard/data/ai_tournament_picks_latest.json", "/findtorontoevents.ca/audit/data/ai_tournament_picks_latest.json",  "ai_tournament"),
    ("audit_dashboard/data/ai_tournament_model_summary.json","/findtorontoevents.ca/audit/data/ai_tournament_model_summary.json", "ai_tournament"),
    ("audit_dashboard/data/ai_tournament_leaderboard.json",  "/findtorontoevents.ca/audit/data/ai_tournament_leaderboard.json",   "ai_tournament"),
    ("audit_dashboard/data/tier_rating_algorithms.json",     "/findtorontoevents.ca/audit/data/tier_rating_algorithms.json",      "ai_tournament"),
    ("audit_dashboard/data/money_ready_verdict.json",        "/findtorontoevents.ca/audit/data/money_ready_verdict.json",         "audit_data"),
    ("audit_dashboard/data/audit_surface_truth.json",        "/findtorontoevents.ca/audit/data/audit_surface_truth.json",         "audit_data"),
    ("audit_dashboard/audit_surface_truth_banner.js",        "/findtorontoevents.ca/audit/audit_surface_truth_banner.js",         "audit_data"),
    ("alpha_engine/data/regime_report.json",                 "/findtorontoevents.ca/audit/data/regime_report.json",              "audit_data"),
    ("audit_dashboard/data/ai_tournament_model_diagnostics.json", "/findtorontoevents.ca/audit/data/ai_tournament_model_diagnostics.json", "ai_tournament"),
    ("audit_dashboard/pf.html",                              "/findtorontoevents.ca/audit/pf.html",                               "ai_portfolios"),
    ("audit_dashboard/data/pf_portfolios.json",              "/findtorontoevents.ca/audit/data/pf_portfolios.json",               "ai_portfolios"),
    # 2026-06-04: daily top-picks filter from AI tournament robust panel
    # (deepseek_v4 + claude_haiku_4_5 + cursor_agent + gpt4o + deepseek_r1 +
    # mercury). Output of tools/daily_top_picks_filter.py.
    ("audit_dashboard/data/daily_top_picks_filter.json",     "/findtorontoevents.ca/audit/data/daily_top_picks_filter.json",      "ai_portfolios"),
    ("audit_dashboard/data/verified_edge_status.json",       "/findtorontoevents.ca/audit/data/verified_edge_status.json",        "ai_portfolios"),
    ("audit_dashboard/data/strategy_admissibility.json",     "/findtorontoevents.ca/audit/data/strategy_admissibility.json",    "ai_portfolios"),
    ("audit_dashboard/data/pilot_forward_dashboard.json",    "/findtorontoevents.ca/audit/data/pilot_forward_dashboard.json",     "ai_portfolios"),
    ("audit_dashboard/data/tournament_shadow_book.json",     "/findtorontoevents.ca/audit/data/tournament_shadow_book.json",      "ai_portfolios"),
    ("audit_dashboard/data/strategy_perf_by_class.json",     "/findtorontoevents.ca/audit/data/strategy_perf_by_class.json",      "pick_funnel"),
    ("audit_dashboard/strategy_perf_by_class.html",          "/findtorontoevents.ca/audit/strategy_perf_by_class.html",           "pick_funnel"),
    ("audit_dashboard/data/phase3_promotion_readiness.json", "/findtorontoevents.ca/audit/data/phase3_promotion_readiness.json",  "ai_portfolios"),
    ("audit_dashboard/data/bootstrap_forward_stats.json",    "/findtorontoevents.ca/audit/data/bootstrap_forward_stats.json",     "ai_portfolios"),
    ("audit_dashboard/data/pf_portfolio_portfolio_mix__aggressive_top5.json", "/findtorontoevents.ca/audit/data/pf_portfolio_portfolio_mix__aggressive_top5.json", "ai_portfolios"),
    ("audit_dashboard/data/pf_portfolio_portfolio_mix__balanced_top3.json", "/findtorontoevents.ca/audit/data/pf_portfolio_portfolio_mix__balanced_top3.json", "ai_portfolios"),
    ("audit_dashboard/data/pf_portfolio_portfolio_mix__conservative_top1.json", "/findtorontoevents.ca/audit/data/pf_portfolio_portfolio_mix__conservative_top1.json", "ai_portfolios"),
    ("audit_dashboard/data/pf_portfolio_portfolio_mix__diversified_per_class.json", "/findtorontoevents.ca/audit/data/pf_portfolio_portfolio_mix__diversified_per_class.json", "ai_portfolios"),
    ("audit_dashboard/data/pf_portfolio_portfolio_mix__sharpe_optimized.json", "/findtorontoevents.ca/audit/data/pf_portfolio_portfolio_mix__sharpe_optimized.json", "ai_portfolios"),
    ("audit_dashboard/data/pick_summary_stats_2w.json",      "/findtorontoevents.ca/audit/data/pick_summary_stats_2w.json",       "pick_funnel"),
    ("audit_dashboard/data/pick_summary_stats_14d.json",     "/findtorontoevents.ca/audit/data/pick_summary_stats_14d.json",      "pick_funnel"),
    ("audit_dashboard/data/pick_summary_stats_48h.json",     "/findtorontoevents.ca/audit/data/pick_summary_stats_48h.json",      "pick_funnel"),
    ("audit_dashboard/data/feature_signals_latest.json",     "/findtorontoevents.ca/audit/data/feature_signals_latest.json",      "pick_funnel"),
    ("audit_dashboard/portfolio_history.html",               "/findtorontoevents.ca/audit/portfolio_history.html",                "portfolio_history"),
    ("audit_dashboard/data/portfolio_classification.json",   "/findtorontoevents.ca/audit/data/portfolio_classification.json",    "portfolio_history"),
    ("updates/index.html",                                   "/findtorontoevents.ca/updates/index.html",                          "updates"),
    ("updates/eagle-best-picks-guide-2026-06-02.html",         "/findtorontoevents.ca/updates/eagle-best-picks-guide-2026-06-02.html", "updates"),
    ("updates/eagle2-swarm-session-summary-2026-06-02.html",   "/findtorontoevents.ca/updates/eagle2-swarm-session-summary-2026-06-02.html", "updates"),
    ("updates/eagle2-swarm-consolidated-findings-2026-06-02.html", "/findtorontoevents.ca/updates/eagle2-swarm-consolidated-findings-2026-06-02.html", "updates"),
    ("updates/2026-06-02-pr465-merged-post-steps.md",          "/findtorontoevents.ca/updates/2026-06-02-pr465-merged-post-steps.md", "updates"),
    ("updates/2026-06-02-eagle2-pr465-session-findings.md",    "/findtorontoevents.ca/updates/2026-06-02-eagle2-pr465-session-findings.md", "updates"),
    ("updates/2026-06-02-active-stale-resolver-p0.md",        "/findtorontoevents.ca/updates/2026-06-02-active-stale-resolver-p0.md", "updates"),
    ("updates/2026-06-02-resolver-hygiene-wave3.md",          "/findtorontoevents.ca/updates/2026-06-02-resolver-hygiene-wave3.md", "updates"),
    ("updates/2026-06-02-resolver-ci-hygiene.md",             "/findtorontoevents.ca/updates/2026-06-02-resolver-ci-hygiene.md", "updates"),
    ("updates/2026-06-03-stale-resolver-pagination-fix.md",    "/findtorontoevents.ca/updates/2026-06-03-stale-resolver-pagination-fix.md", "updates"),
    ("updates/2026-06-03-bootstrap-forward-paper-pilots.md",   "/findtorontoevents.ca/updates/2026-06-03-bootstrap-forward-paper-pilots.md", "updates"),
    ("updates/2026-06-03-outcome-resolver-max-batches.md",     "/findtorontoevents.ca/updates/2026-06-03-outcome-resolver-max-batches.md", "updates"),
    ("audit_dashboard/ai_leaderboard.html",                  "/findtorontoevents.ca/audit/ai_leaderboard.html",                   "ai_leaderboard"),
    ("audit_dashboard/data/ai_leaderboard/ai_leaderboard_index.json", "/findtorontoevents.ca/audit/data/ai_leaderboard/ai_leaderboard_index.json", "ai_leaderboard"),
    ("audit_dashboard/data/ma_strategy_leaderboard.json",    "/findtorontoevents.ca/audit/data/ma_strategy_leaderboard.json",     "ai_leaderboard"),
    ("audit_dashboard/data/ma_strategy_signals.json",        "/findtorontoevents.ca/audit/data/ma_strategy_signals.json",         "ai_leaderboard"),
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


def verify(remote: str, check_content: bool = False) -> tuple[bool, str]:
    """50webs Apache returns 412 on default urllib HEAD, so use GET with Range:0-0
    and a real User-Agent. Validates the file exists + is reachable without
    downloading the whole body."""
    url = "https://findtorontoevents.ca" + remote.replace("/findtorontoevents.ca", "")
    try:
        headers = {"User-Agent": "Mozilla/5.0 audit-deploy-verify"}
        if not check_content:
            headers["Range"] = "bytes=0-0"
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            if check_content and remote.endswith("ai_tournament_picks_latest.json"):
                import json
                data = json.loads(resp.read())
                n_models = len({p.get("model_id") for p in data})
                if n_models < 30:
                    return False, f"CONTENT_FAIL: only {n_models} models found (expected >=30)"
                return True, f"HTTP {status} · {n_models} models verified"
            
            cl = resp.headers.get("content-range", resp.headers.get("content-length", "?"))
            return status in (200, 206), f"HTTP {status} · {cl}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", help="Only upload files with this tag (incidents/pick_funnel/model/ai_tournament/updates)")
    ap.add_argument("--no-verify", action="store_true", help="Skip post-upload HTTP HEAD")
    ap.add_argument("--verify-content", action="store_true", help="Download and verify JSON content (e.g. model count)")
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
            ok_v, msg_v = verify(remote, args.verify_content)
            verify_results.append((remote, ok_v, msg_v))

    if ftps:
        try: ftps.quit()
        except Exception: pass

    if verify_results:
        print("\nVerify (HTTP GET/HEAD on live URLs):")
        for r, ok_v, msg_v in verify_results:
            marker = "  OK  " if ok_v else "  FAIL"
            print(f"{marker}  https://findtorontoevents.ca{r.replace('/findtorontoevents.ca','')}  ({msg_v})")
            if not ok_v:
                fail += 1 # content mismatch counts as failure

    print(f"\n{ok} uploaded, {fail} failed")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
