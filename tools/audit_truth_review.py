#!/usr/bin/env python3
"""
Read-only audit: reverse splits, stale payloads, EST display gaps, high-WR skew.
Run from repo root: python3 tools/audit_truth_review.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_REPO = Path("/home/eaguiar2015/findtorontoevents_antigravity.ca")
sys.path.insert(0, str(MAIN_REPO))

try:
    from audit_trail.reverse_split_symbols import REVERSE_SPLIT_SYMBOLS, is_reverse_split_affected
except ImportError:
    REVERSE_SPLIT_SYMBOLS = {
        "LODE": ("1-for-10", "2025-02-05"),
        "FFIE": ("1-for-40", "2024-01-01"),
        "WKHS": ("1-for-20", "2024-01-01"),
        "KULR": ("1-for-8", "2025-06-23"),
        "HOLO": ("1-for-40", "2025-04-21"),
        "GSAT": ("1-for-15", "2025-02-11"),
    }

    def is_reverse_split_affected(symbol: str) -> bool:
        return str(symbol or "").strip().upper() in REVERSE_SPLIT_SYMBOLS


UA = "Mozilla/5.0 (audit-truth-review/2026-06-04)"


def fetch_json(url: str) -> dict:
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=35) as resp:
        return json.loads(resp.read().decode())


def load_json(rel: str) -> dict | list | None:
    p = REPO_ROOT / rel
    if not p.exists():
        return None
    with p.open(encoding="utf-8") as fh:
        return json.load(fh)


def read_generated_at_huge(rel: str) -> str | None:
    p = REPO_ROOT / rel
    if not p.exists():
        return None
    with p.open(encoding="utf-8") as fh:
        head = fh.read(12000)
    m = re.search(r'"generated_at"\s*:\s*"([^"]+)"', head)
    return m.group(1) if m else None


def age_hours(iso: str | None) -> float | None:
    if not iso:
        return None
    s = str(iso).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0


def staleness_flag(hours: float | None) -> str:
    if hours is None:
        return "unknown"
    if hours > 24:
        return "STALE>24h"
    if hours > 2:
        return "STALE>2h"
    return "ok"


def fmt_age(hours: float | None) -> str:
    if hours is None:
        return "n/a"
    return f"{hours:.1f}"


def print_staleness() -> None:
    print("\n## STALENESS (generated_at / as_of)")
    checks = [
        ("local_dashboard", "audit_dashboard/data/dashboard_data.json", None),
        ("local_tournament", "audit_dashboard/data/ai_tournament_model_summary.json", "generated_at"),
        ("local_leaderboard", "audit_dashboard/data/ai_leaderboard/ai_leaderboard_index.json", "as_of"),
        ("local_picks_latest", "audit_dashboard/data/ai_tournament_picks_latest.json", "generated_at"),
        ("local_14d", "audit_dashboard/data/pick_summary_stats_14d.json", "generated_at"),
        ("local_48h", "audit_dashboard/data/pick_summary_stats_48h.json", "generated_at"),
    ]
    for name, path, key in checks:
        if path.endswith("dashboard_data.json"):
            ts = read_generated_at_huge(path)
        else:
            data = load_json(path)
            ts = (data or {}).get(key) if isinstance(data, dict) else None
        hrs = age_hours(ts)
        print(f"  {name:22} ts={ts} age_h={fmt_age(hrs):>6} {staleness_flag(hrs)}")

    live_urls = [
        ("live_dashboard", "https://findtorontoevents.ca/audit/data/dashboard_data.json"),
        ("live_tournament", "https://findtorontoevents.ca/audit/data/ai_tournament_model_summary.json"),
        ("live_leaderboard", "https://findtorontoevents.ca/audit/data/ai_leaderboard/ai_leaderboard_index.json"),
        ("live_14d", "https://findtorontoevents.ca/audit/data/pick_summary_stats_14d.json"),
        ("live_48h", "https://findtorontoevents.ca/audit/data/pick_summary_stats_48h.json"),
    ]
    for name, url in live_urls:
        try:
            data = fetch_json(url)
            ts = data.get("generated_at") or data.get("as_of")
            hrs = age_hours(ts)
            print(f"  {name:22} ts={ts} age_h={fmt_age(hrs):>6} {staleness_flag(hrs)} [LIVE]")
        except Exception as exc:
            print(f"  {name:22} LIVE_FAIL: {exc}")


def tournament_wr_buckets() -> None:
    print("\n## AI TOURNAMENT — model WR tiers (post-MISPRICED pipeline)")
    ms = load_json("audit_dashboard/data/ai_tournament_model_summary.json") or {}
    models = ms.get("models") or []

    def wr(m: dict) -> float:
        return float(m.get("win_rate_pct") or m.get("win_rate") or m.get("wr") or 0)

    def n_res(m: dict) -> int:
        return int(m.get("resolved") or m.get("n_resolved") or 0)

    models = sorted([m for m in models if isinstance(m, dict)], key=wr, reverse=True)
    tiers = [
        (">=80%", 80, 200),
        ("70-79%", 70, 79.99),
        ("60-69%", 60, 69.99),
        ("50-59%", 50, 59.99),
    ]
    for label, lo, hi in tiers:
        bucket = [m for m in models if lo <= wr(m) <= hi and n_res(m) >= 5]
        if not bucket:
            continue
        print(f"\n  ### WR {label} (resolved n>=5)")
        for m in bucket[:15]:
            mid = m.get("model_id") or m.get("model") or "?"
            print(
                f"    {mid}: WR={wr(m):.1f}% resolved={n_res(m)} "
                f"pf={m.get('pf')} avg_pnl={m.get('avg_pnl_pct')}"
            )


def scan_tournament_picks() -> None:
    print("\n## TOURNAMENT PICKS LATEST — reverse splits & extreme PnL")
    picks_d = load_json("audit_dashboard/data/ai_tournament_picks_latest.json") or {}
    picks = picks_d.get("picks") if isinstance(picks_d, dict) else picks_d
    if not isinstance(picks, list):
        picks = []
    rs_hits = []
    extreme = []
    mispriced_syms = []
    for p in picks:
        if not isinstance(p, dict):
            continue
        sym = str(p.get("symbol") or p.get("ticker") or "").upper()
        status = p.get("status") or ""
        if is_reverse_split_affected(sym):
            rs_hits.append(
                (sym, status, p.get("pnl_pct"), p.get("entry_price"), p.get("model_id") or p.get("model"))
            )
        if status == "MISPRICED_ENTRY":
            mispriced_syms.append(sym)
        try:
            pnl = float(p.get("pnl_pct") or 0)
        except (TypeError, ValueError):
            pnl = 0
        if abs(pnl) > 100:
            extreme.append((sym, pnl, status, p.get("model_id") or p.get("model")))

    print(f"  picks in latest file: {len(picks)}")
    print(f"  MISPRICED_ENTRY: {len(mispriced_syms)} ({len(set(mispriced_syms))} unique symbols)")
    print(f"  registry reverse-split symbols present: {len(rs_hits)}")
    for row in rs_hits[:20]:
        print(f"    RS {row}")
    print(f"  |pnl_pct|>100: {len(extreme)}")
    for row in sorted(extreme, key=lambda x: -abs(x[1]))[:12]:
        print(f"    EXTREME {row}")


def pick_summary_by_class(label: str, rel: str) -> None:
    s = load_json(rel)
    if not s or not isinstance(s, dict):
        print(f"\n## PICK SUMMARY {label}: MISSING")
        return
    print(f"\n## PICK SUMMARY {label} (generated {s.get('generated_at')})")
    by = s.get("by_asset_class") or s.get("asset_classes") or {}
    if not isinstance(by, dict):
        return
    rows = []
    for cls, info in by.items():
        if not isinstance(info, dict):
            continue
        wr_v = float(info.get("win_rate") or info.get("wr") or 0)
        n_v = info.get("n") or info.get("closed") or info.get("n_closed")
        rows.append((wr_v, cls, n_v, info.get("profit_factor") or info.get("pf")))
    rows.sort(reverse=True)
    for wr_v, cls, n_v, pf in rows:
        if wr_v >= 50 or (n_v is not None and int(n_v) >= 5):
            skew = ""
            if wr_v >= 80 and n_v is not None and int(n_v) < 30:
                skew = " ⚠ HIGH-WR LOW-N"
            print(f"    {cls}: WR={wr_v}% n={n_v} pf={pf}{skew}")


def leaderboard_high_wr() -> None:
    print("\n## AI LEADERBOARD INDEX — per-class WR (research engines)")
    idx = load_json("audit_dashboard/data/ai_leaderboard/ai_leaderboard_index.json") or {}
    print(f"  as_of={idx.get('as_of')} age_h={fmt_age(age_hours(idx.get('as_of')))} {staleness_flag(age_hours(idx.get('as_of')))}")
    for eng in idx.get("engines") or []:
        if not isinstance(eng, dict):
            continue
        name = eng.get("engine") or "?"
        by = eng.get("by_asset_class") or {}
        for cls, info in sorted(by.items(), key=lambda kv: -(float((kv[1] or {}).get("wr") or 0))):
            if not isinstance(info, dict):
                continue
            wr_v = float(info.get("wr") or 0)
            n_v = int(info.get("n") or 0)
            if wr_v >= 50 and n_v >= 5:
                note = ""
                if wr_v >= 70 and n_v < 25:
                    note = " ⚠ small-n / possible skew"
                print(f"    {name} / {cls}: WR={wr_v}% n={n_v} pf={info.get('pf')}{note}")


def html_est_audit() -> None:
    print("\n## HTML — EST helpers vs raw UTC labels")
    pages = [
        "audit_dashboard/pick_funnel.html",
        "audit_dashboard/ai_leaderboard.html",
        "audit_dashboard/ai-tournament.html",
        "audit_dashboard/template.html",
        "audit_dashboard/curated_picks_20260524.html",
    ]
    for rel in pages:
        p = REPO_ROOT / rel
        if not p.exists():
            print(f"  {rel}: MISSING")
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        has_est = "toEST" in txt or "_fmtEST" in txt or "America/New_York" in txt
        utc_leak = bool(re.search(r"When \(UTC\)|\bUTC\)</th>|cutoff_utc", txt))
        static_date = "20260524" in rel
        print(
            f"  {rel}: EST={has_est} UTC_leak={utc_leak} "
            f"static_snapshot={static_date}"
        )


def main() -> int:
    print("=" * 70)
    print("AUDIT TRUTH REVIEW")
    print("worktree:", REPO_ROOT)
    print("reverse_split registry:", sorted(REVERSE_SPLIT_SYMBOLS.keys()))
    print("=" * 70)
    print_staleness()
    tournament_wr_buckets()
    scan_tournament_picks()
    pick_summary_by_class("14d", "audit_dashboard/data/pick_summary_stats_14d.json")
    pick_summary_by_class("48h", "audit_dashboard/data/pick_summary_stats_48h.json")
    leaderboard_high_wr()
    html_est_audit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
