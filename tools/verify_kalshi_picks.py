#!/usr/bin/env python3
"""
Cross-check curated UFC / Tennis / Golf / NBA sports picks against Kalshi
prediction-market prices.

Mirrors the Polymarket verifier pattern (`tools/verify_manual_sports_picks.py`
when present, or `tools/polymarket_whale_validate.py` stub style) but uses
the Kalshi feed produced by `tools/kalshi_sports_fetch.py`.

Reads picks from (in order of preference):
  1) --picks <path>             (explicit JSON file)
  2) data/goldmine/sports_picks.json (live picks file used by the dashboard)
  3) live-monitor/sports-betting.html embedded ufcPicksData/tennisPicksData/
     golfPicksData arrays (regex extraction; tolerated as absent)

Each curated pick is matched to the closest open Kalshi market by:
  - sport name match (ufc -> KXUFC, tennis -> KXATPMATCH, ...)
  - fuzzy overlap of competitor surnames in market title
  - final picks without a Kalshi market are tagged `no_kalshi_match`

Output: reports/MANUAL_SPORTS_PICKS_VERIFICATION_KALSHI_<UTC>.md (and a
sibling .json with the structured detail for downstream tooling).

Read-only. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO / "reports"
SNAP_DIR = REPO / "data" / "kalshi_snapshots"
PICKS_DEFAULT = REPO / "data" / "goldmine" / "sports_picks.json"
SPORTS_HTML = REPO / "live-monitor" / "sports-betting.html"
TARGET_SPORTS = {"ufc", "mma", "tennis", "golf", "nba"}

STOPWORDS = {"the", "vs", "v", "at", "@", "win", "winner", "match",
             "round", "of", "over", "under", "ml", "moneyline", "to",
             "will", "the", "in", "fight"}


def stamp_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"[verify] could not read {path}: {e}", file=sys.stderr)
        return None


def normalize(s: str) -> set[str]:
    if not s:
        return set()
    parts = re.split(r"[^a-z0-9]+", s.lower())
    return {p for p in parts if p and p not in STOPWORDS and len(p) > 2}


def load_picks_from_html(html_path: Path) -> list[dict]:
    """Extract `<sport>PicksData = [ ... ];` arrays embedded in the HTML."""
    try:
        text = html_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    out: list[dict] = []
    for sport in ("ufc", "tennis", "golf"):
        pat = re.compile(
            r"(?:var|let|const)\s+" + sport +
            r"PicksData\s*=\s*(\[.*?\]);", re.DOTALL | re.IGNORECASE)
        m = pat.search(text)
        if not m:
            continue
        try:
            arr = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        for entry in arr:
            if isinstance(entry, dict):
                entry.setdefault("sport", sport)
                out.append(entry)
    return out


def load_picks(explicit: Path | None) -> tuple[list[dict], str]:
    """Returns (picks, source_label)."""
    if explicit and explicit.exists():
        data = read_json(explicit)
        return _flatten_picks(data), str(explicit)
    if PICKS_DEFAULT.exists():
        data = read_json(PICKS_DEFAULT)
        return _flatten_picks(data), str(PICKS_DEFAULT)
    if SPORTS_HTML.exists():
        return load_picks_from_html(SPORTS_HTML), str(SPORTS_HTML)
    return [], "(no picks source found)"


def _flatten_picks(data) -> list[dict]:
    if not data:
        return []
    if isinstance(data, list):
        return [p for p in data if isinstance(p, dict)]
    if isinstance(data, dict):
        for key in ("value_bets", "picks", "ufcPicks", "tennisPicks",
                    "golfPicks"):
            arr = data.get(key)
            if isinstance(arr, list):
                return [p for p in arr if isinstance(p, dict)]
    return []


def pick_sport_norm(pick: dict) -> str:
    raw = (pick.get("sport") or pick.get("sport_short") or "").lower()
    if "ufc" in raw or "mma" in raw:
        return "ufc"
    if "tennis" in raw or raw in ("atp", "wta"):
        return "tennis"
    if "golf" in raw or raw == "pga":
        return "golf"
    if "basketball_nba" in raw or raw == "nba":
        return "nba"
    return raw


def pick_signature(pick: dict) -> str:
    """Build a string we can fuzz-match against Kalshi market titles."""
    parts = [
        pick.get("home_team", ""),
        pick.get("away_team", ""),
        pick.get("outcome_name", ""),
        pick.get("bet_type", ""),
        pick.get("player", ""),
        pick.get("event", ""),
        pick.get("title", ""),
    ]
    return " ".join(p for p in parts if p)


def match_market(pick: dict, markets: list[dict]) -> tuple[dict | None, float]:
    sport = pick_sport_norm(pick)
    target_tokens = normalize(pick_signature(pick))
    if not target_tokens:
        return None, 0.0
    best, best_score = None, 0.0
    for m in markets:
        if sport and m.get("sport") and m["sport"] != sport:
            continue
        title = (m.get("title") or "")
        m_tokens = normalize(title)
        if not m_tokens:
            continue
        overlap = len(target_tokens & m_tokens)
        if overlap == 0:
            continue
        score = overlap / max(1, len(target_tokens))
        if score > best_score:
            best, best_score = m, score
    return best, best_score


def mid_price(m: dict) -> float | None:
    yb, ya = m.get("yes_bid"), m.get("yes_ask")
    if yb is not None and ya is not None:
        return round((yb + ya) / 2.0, 4)
    return m.get("last_price")


def implied_prob_from_pick(pick: dict) -> float | None:
    wp = pick.get("win_probability")
    if wp is not None:
        try:
            f = float(wp)
        except (TypeError, ValueError):
            return None
        return round(f / 100.0 if f > 1.0 else f, 4)
    odds = pick.get("best_odds") or pick.get("decimal_odds")
    if odds:
        try:
            f = float(odds)
            if f > 1.0:
                return round(1.0 / f, 4)
        except (TypeError, ValueError):
            pass
    return None


def fetch_or_load_snapshot(snapshot: Path | None,
                            sport_filter: str) -> dict | None:
    if snapshot and snapshot.exists():
        data = read_json(snapshot)
        return data if isinstance(data, dict) else None
    # try latest in SNAP_DIR
    if SNAP_DIR.exists():
        cands = sorted(SNAP_DIR.glob("*.json"))
        if cands:
            data = read_json(cands[-1])
            if isinstance(data, dict):
                return data
    # fall back to live fetch
    fetcher = REPO / "tools" / "kalshi_sports_fetch.py"
    if not fetcher.exists():
        return None
    try:
        out = subprocess.run(
            [sys.executable, str(fetcher), "--sport", sport_filter, "--stdout"],
            capture_output=True, text=True, timeout=120, check=False,
        )
        if out.returncode != 0 or not out.stdout.strip():
            print(f"[verify] live fetch failed: rc={out.returncode} "
                  f"stderr={out.stderr[:200]}", file=sys.stderr)
            return None
        return json.loads(out.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError) as e:
        print(f"[verify] live fetch error: {e}", file=sys.stderr)
        return None


def render_md(payload: dict) -> str:
    lines = [
        "# Manual Sports Picks Verification — Kalshi",
        "",
        f"**As of:** {payload['as_of']}",
        f"**Picks source:** `{payload['picks_source']}`",
        f"**Kalshi snapshot:** `{payload['kalshi_snapshot']}`  "
        f"({payload['n_markets']} markets across "
        f"{payload['n_series_probed']} series)",
        f"**Picks examined:** {payload['n_picks']}  "
        f"(target sports = {', '.join(sorted(TARGET_SPORTS))})",
        "",
        "## Summary",
        "",
        f"- matched: **{payload['summary']['matched']}**",
        f"- no_kalshi_match: **{payload['summary']['no_kalshi_match']}**",
        f"- skipped (off-sport): **{payload['summary']['skipped']}**",
        "",
        "## Per-pick detail",
        "",
        "| sport | pick | book_prob | kalshi_mid | edge_pp | "
        "kalshi_market | match_score |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in payload["rows"]:
        if r["status"] == "skipped":
            continue
        prob = r.get("book_prob")
        mid = r.get("kalshi_mid")
        edge = r.get("edge_pp")
        prob_s = f"{prob:.3f}" if isinstance(prob, (int, float)) else "-"
        mid_s = f"{mid:.3f}" if isinstance(mid, (int, float)) else "-"
        edge_s = f"{edge:+.1f}" if isinstance(edge, (int, float)) else "-"
        title = (r.get("kalshi_title") or "no_kalshi_match")[:80]
        score = r.get("match_score")
        score_s = f"{score:.2f}" if isinstance(score, (int, float)) else "-"
        sig = (r.get("pick_signature") or "")[:60]
        lines.append(
            f"| {r['sport']} | {sig} | {prob_s} | {mid_s} | {edge_s} | "
            f"{title} | {score_s} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- `book_prob` = pick win-probability from sportsbook odds.",
        "- `kalshi_mid` = (yes_bid + yes_ask) / 2 of the matched Kalshi market.",
        "- `edge_pp` = book_prob − kalshi_mid, in percentage points. "
        "Positive = sportsbook is more bullish than Kalshi crowd.",
        "- Match score is fraction of pick-signature tokens overlapping "
        "Kalshi market title; >= 0.5 is high confidence.",
        "- This is an opt-in sidecar verifier. It does NOT alter "
        "live-monitor pick generation. See "
        "`updates/2026-04-26-kalshi-sports-adapter-wiring-plan.md`.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--picks", default=None,
                    help="Path to picks JSON. Default: goldmine sports_picks.json"
                         " (then HTML fallback).")
    ap.add_argument("--snapshot", default=None,
                    help="Pre-fetched Kalshi snapshot JSON. Default: latest in "
                         "data/kalshi_snapshots/, then live fetch.")
    ap.add_argument("--sport", default="all",
                    help="Sport filter for live-fetch fallback.")
    ap.add_argument("--out-md", default=None)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    picks, picks_source = load_picks(Path(args.picks) if args.picks else None)
    snapshot = fetch_or_load_snapshot(
        Path(args.snapshot) if args.snapshot else None, args.sport)
    if snapshot is None:
        snapshot = {"markets": [], "series_probed": [], "n_markets": 0,
                    "as_of": stamp_utc()}
    markets = snapshot.get("markets", [])

    rows: list[dict] = []
    n_matched = n_nomatch = n_skipped = 0
    for pick in picks:
        sport = pick_sport_norm(pick)
        if sport not in TARGET_SPORTS:
            n_skipped += 1
            rows.append({
                "status": "skipped",
                "sport": sport or "(unknown)",
                "pick_signature": pick_signature(pick)[:120],
            })
            continue
        prob = implied_prob_from_pick(pick)
        m, score = match_market(pick, markets)
        row = {
            "sport": sport,
            "pick_signature": pick_signature(pick)[:120],
            "book_prob": prob,
            "kalshi_market": m.get("ticker") if m else None,
            "kalshi_title": m.get("title") if m else None,
            "kalshi_mid": mid_price(m) if m else None,
            "match_score": round(score, 3) if m else None,
        }
        if m:
            n_matched += 1
            row["status"] = "matched"
            mid = row["kalshi_mid"]
            if isinstance(prob, (int, float)) and isinstance(mid, (int, float)):
                row["edge_pp"] = round((prob - mid) * 100, 2)
        else:
            n_nomatch += 1
            row["status"] = "no_kalshi_match"
        rows.append(row)

    payload = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "picks_source": picks_source,
        "kalshi_snapshot": snapshot.get("as_of", "unknown"),
        "kalshi_host": snapshot.get("host", "unknown"),
        "n_markets": snapshot.get("n_markets", len(markets)),
        "n_series_probed": len(snapshot.get("series_probed", []) or []),
        "n_picks": len(picks),
        "summary": {
            "matched": n_matched,
            "no_kalshi_match": n_nomatch,
            "skipped": n_skipped,
        },
        "rows": rows,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = stamp_utc()
    md_path = (Path(args.out_md) if args.out_md
               else REPORTS_DIR /
               f"MANUAL_SPORTS_PICKS_VERIFICATION_KALSHI_{stamp}.md")
    json_path = (Path(args.out_json) if args.out_json
                 else REPORTS_DIR /
                 f"MANUAL_SPORTS_PICKS_VERIFICATION_KALSHI_{stamp}.json")
    md_path.write_text(render_md(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    print(f"  matched={n_matched}  no_kalshi_match={n_nomatch}  "
          f"skipped={n_skipped}  picks={len(picks)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
