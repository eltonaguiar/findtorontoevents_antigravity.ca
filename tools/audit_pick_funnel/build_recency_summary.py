"""
Build recency-subset summaries (14-day + 48-hour) for /audit/pick_funnel.html.

Two output sidecars:
  - audit_dashboard/data/pick_summary_stats_2w.json   (last 14 days)
  - audit_dashboard/data/pick_summary_stats_48h.json  (last 48 hours, with per-pick rows)

Both restrict to picks OPENED OR CLOSED inside the window
(`signal_timestamp >= cutoff OR closed_at >= cutoff`). Per asset class we
compute: n_touched, n_active, n_closed, wins, losses, raw WR, Bayes-shrunk WR
(Beta(a=10,b=10)), PF, mean PnL%, top symbol, top source, top-source share, +
leakage caveats (dup groups, EXPIRED-mislabeled-WON share, single-source
concentration > 60%).

Mirrors the leakage caveats from
reports/2026-05-25_crypto_78pct_wr_verification.md and the Bayes prior used by
the existing pick_summary_stats.json builder.

If the DB is unreachable, falls back to
audit/data/dashboard_data.json::picks.recent_closed filtered by closed_at —
this loses opened-but-not-closed visibility and is noted in the JSON.
"""
from __future__ import annotations
import json, os, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

PRIOR_A = 10
PRIOR_B = 10
PRIOR_N = PRIOR_A + PRIOR_B  # 20
PRIOR_MEAN = PRIOR_A / PRIOR_N  # 0.5

WIN_STATUSES = {"WON"}
LOSS_STATUSES = {"LOST"}
DECISIVE_STATUSES = WIN_STATUSES | LOSS_STATUSES
ACTIVE_STATUSES = {"OPEN", "ACTIVE"}

INSUFF_N = 10  # below this we emit "INSUFFICIENT n" instead of WR


def _bayes_wr(wins: int, n: int) -> float | None:
    if n <= 0:
        return None
    return round(100 * (wins + PRIOR_A) / (n + PRIOR_N), 2)


def _pf(rows) -> float | None:
    pos = sum(float(r["pnl_pct"]) for r in rows if r.get("pnl_pct") is not None and float(r["pnl_pct"]) > 0)
    neg = sum(float(r["pnl_pct"]) for r in rows if r.get("pnl_pct") is not None and float(r["pnl_pct"]) < 0)
    if neg == 0:
        return None if pos == 0 else float("inf")
    return round(pos / abs(neg), 3)


def _serialize_pf(pf):
    if pf is None:
        return None
    if pf == float("inf"):
        return "inf"
    return pf


def _dedup_key(r):
    return (r.get("symbol"), r.get("signal_timestamp"), r.get("source_system"))


def _classify_rows(rows, window_label: str, cutoff_dt, include_pick_rows: bool):
    """Compute per-class rollup from raw at_raw_picks rows."""
    by_class = defaultdict(list)
    for r in rows:
        ac = (r.get("asset_class") or "UNKNOWN") or "UNKNOWN"
        by_class[ac].append(r)

    out = {}
    for ac, bucket in by_class.items():
        # Dedupe leakage flag
        seen = Counter()
        for r in bucket:
            seen[_dedup_key(r)] += 1
        dup_groups = sum(1 for k, v in seen.items() if v > 1)

        # Active = OPEN at "now" and inside window (signal_ts >= cutoff or no closed_at)
        active = [r for r in bucket if (r.get("status") in ACTIVE_STATUSES) or (r.get("status") == "OPEN")]
        # Closed inside window
        closed = [r for r in bucket if r.get("status") in (DECISIVE_STATUSES | {"EXPIRED", "CLOSED"}) and r.get("closed_at") and r["closed_at"] >= cutoff_dt]
        decisive = [r for r in closed if r.get("status") in DECISIVE_STATUSES and r.get("pnl_pct") is not None]
        wins = sum(1 for r in decisive if r.get("status") in WIN_STATUSES)
        losses = sum(1 for r in decisive if r.get("status") in LOSS_STATUSES)
        n = len(decisive)
        wr = round(100 * wins / n, 2) if n > 0 else None
        wrs = _bayes_wr(wins, n)
        pf = _pf(decisive)
        mean_pnl = round(sum(float(r["pnl_pct"]) for r in decisive) / n, 4) if n > 0 else None

        # Top symbol / source
        sym_c = Counter(r.get("symbol") for r in decisive)
        src_c = Counter(r.get("source_system") for r in decisive)
        top_sym, top_sym_n = (sym_c.most_common(1)[0] if sym_c else (None, 0))
        top_src, top_src_n = (src_c.most_common(1)[0] if src_c else (None, 0))
        top_src_share = round(top_src_n / n, 3) if n > 0 else None

        # EXPIRED-as-WON leakage check
        expired = [r for r in closed if r.get("status") == "EXPIRED"]
        expired_pos_pnl = sum(1 for r in expired if r.get("pnl_pct") is not None and float(r["pnl_pct"]) > 0)
        expired_share = round(len(expired) / max(1, len(closed)), 3)

        caveats = []
        if dup_groups > 0:
            caveats.append(f"dup_groups={dup_groups}")
        if top_src_share is not None and top_src_share > 0.60:
            caveats.append(f"single_source_concentration={int(top_src_share * 100)}%_via_{top_src}")
        if expired and expired_pos_pnl / len(expired) > 0.55:
            caveats.append(f"EXPIRED_pos_pnl_share={int(100*expired_pos_pnl/len(expired))}%_likely_mislabeled_WON")
        if n < INSUFF_N:
            caveats.append(f"INSUFF-N (n={n}<{INSUFF_N})")

        rec = {
            "window": window_label,
            "n_touched": len(bucket),
            "n_active": len(active),
            "n_closed": len(closed),
            "n_decisive": n,
            "wins": wins,
            "losses": losses,
            "wr_pct": wr if n >= INSUFF_N else None,
            "wr_pct_raw_low_n": wr if n < INSUFF_N else None,
            "wr_shrunk_pct": wrs,
            "pf": _serialize_pf(pf),
            "mean_pnl_pct": mean_pnl,
            "top_symbol": top_sym,
            "top_symbol_share": round(top_sym_n / n, 3) if n > 0 else None,
            "top_source": top_src,
            "top_source_share": top_src_share,
            "caveats": caveats,
        }

        if include_pick_rows:
            # Per-pick detail rows, capped to 50, newest first
            detail = []
            for r in sorted(closed, key=lambda x: x.get("closed_at") or x.get("signal_timestamp"), reverse=True)[:50]:
                sig = r.get("signal_timestamp")
                clo = r.get("closed_at")
                hold_min = None
                if sig and clo:
                    try:
                        hold_min = round((clo - sig).total_seconds() / 60, 1)
                    except Exception:
                        hold_min = None
                detail.append({
                    "symbol": r.get("symbol"),
                    "source_system": r.get("source_system"),
                    "strategy": r.get("strategy"),
                    "direction": r.get("direction"),
                    "opened_at": sig.isoformat() if sig else None,
                    "closed_at": clo.isoformat() if clo else None,
                    "status": r.get("status"),
                    "pnl_pct": float(r["pnl_pct"]) if r.get("pnl_pct") is not None else None,
                    "hold_minutes": hold_min,
                })
            rec["picks"] = detail
            # Also include active picks (no pnl yet)
            act_detail = []
            for r in sorted(active, key=lambda x: x.get("signal_timestamp") or datetime.min, reverse=True)[:25]:
                sig = r.get("signal_timestamp")
                act_detail.append({
                    "symbol": r.get("symbol"),
                    "source_system": r.get("source_system"),
                    "strategy": r.get("strategy"),
                    "direction": r.get("direction"),
                    "opened_at": sig.isoformat() if sig else None,
                    "status": r.get("status"),
                    "confidence": float(r["confidence"]) if r.get("confidence") is not None else None,
                })
            rec["active_picks"] = act_detail

        out[ac] = rec
    return out


def _query_window(cur, hours: int):
    """Pull rows OPENED OR CLOSED within the last `hours` hours."""
    cur.execute(
        """
        SELECT symbol, asset_class, direction, source_system, strategy, confidence,
               signal_timestamp, closed_at, status, pnl_pct
        FROM at_raw_picks
        WHERE signal_timestamp >= NOW() - INTERVAL %s HOUR
           OR closed_at         >= NOW() - INTERVAL %s HOUR
        """,
        (hours, hours),
    )
    return cur.fetchall()


def _build_from_db(hours: int, include_pick_rows: bool):
    from tools.audit_pick_funnel._db import connect_stocks
    conn = connect_stocks()
    cur = conn.cursor()
    cur.execute("SELECT NOW() AS now_utc")
    now_row = cur.fetchone()
    now_dt = now_row["now_utc"]
    cutoff = now_dt - timedelta(hours=hours)
    rows = _query_window(cur, hours)
    return rows, now_dt, cutoff, "ejaguiar1_stocks.at_raw_picks (DB)"


def _build_from_dashboard_fallback(hours: int):
    src = REPO / "audit" / "data" / "dashboard_data.json"
    if not src.exists():
        src = REPO / "audit_dashboard" / "data" / "dashboard_data.json"
    with src.open("r") as f:
        d = json.load(f)
    rc = d.get("picks", {}).get("recent_closed", [])
    now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now_dt - timedelta(hours=hours)

    def _parse(s):
        if not s:
            return None
        # Tolerant ISO parser
        s2 = str(s).replace("Z", "").replace("EST", "").strip()
        # If has tz offset, strip
        if "+" in s2[10:]:
            s2 = s2.split("+", 1)[0]
        try:
            return datetime.fromisoformat(s2.split(".")[0])
        except Exception:
            return None

    out = []
    for p in rc:
        ca = _parse(p.get("closed_at"))
        ts = _parse(p.get("timestamp"))
        if not (ca and ca >= cutoff) and not (ts and ts >= cutoff):
            continue
        out.append({
            "symbol": p.get("symbol"),
            "asset_class": p.get("asset_class"),
            "direction": p.get("direction"),
            "source_system": p.get("source_system"),
            "strategy": p.get("strategy"),
            "confidence": p.get("confidence"),
            "signal_timestamp": ts,
            "closed_at": ca,
            "status": p.get("status"),
            "pnl_pct": p.get("pnl_pct"),
        })
    return out, now_dt, cutoff, "audit/data/dashboard_data.json::picks.recent_closed (DB unavailable — fallback, ACTIVE picks not visible)"


def _build(hours: int, label: str, include_pick_rows: bool, out_name: str):
    try:
        rows, now_dt, cutoff, source = _build_from_db(hours, include_pick_rows)
        used_fallback = False
    except Exception as e:
        print(f"[build_recency_summary] DB unreachable ({e}); falling back to dashboard JSON")
        rows, now_dt, cutoff, source = _build_from_dashboard_fallback(hours)
        used_fallback = True

    by_class = _classify_rows(rows, label, cutoff, include_pick_rows)

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_label": label,
        "window_hours": hours,
        "cutoff_utc": cutoff.isoformat() if hasattr(cutoff, "isoformat") else str(cutoff),
        "now_utc": now_dt.isoformat() if hasattr(now_dt, "isoformat") else str(now_dt),
        "source": source,
        "fallback_mode": used_fallback,
        "shrinkage_prior": f"Beta(a={PRIOR_A}, b={PRIOR_B}) — prior_n={PRIOR_N}, prior_mean={PRIOR_MEAN}",
        "insufficient_n_floor": INSUFF_N,
        "leakage_caveats_template": [
            "dup_groups: count of (symbol,signal_timestamp,source_system) groups with >1 row",
            "single_source_concentration: top-source share of decisive rows > 60% (flag)",
            "EXPIRED_pos_pnl_share: % of EXPIRED rows with pnl_pct>0; >55% suggests EXPIRED-mislabeled-WON drift",
            "INSUFF-N: n < 10 — WR omitted to avoid fabrication",
        ],
        "by_class": by_class,
    }
    out_path = REPO / "audit_dashboard" / "data" / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"[build_recency_summary] wrote {out_path} ({out_path.stat().st_size:,} bytes) — {len(by_class)} classes, cutoff={cutoff}")
    # Console summary
    for ac, b in sorted(by_class.items(), key=lambda kv: -kv[1]["n_touched"]):
        wr = b["wr_pct"] if b["wr_pct"] is not None else (f"INSUFF-N({b['n_decisive']})" if b["n_decisive"] < INSUFF_N else "—")
        print(f"  {ac:<12} touched={b['n_touched']:<5} active={b['n_active']:<4} closed={b['n_closed']:<4} decisive={b['n_decisive']:<4} WR={wr} PF={b['pf']} top_src={b['top_source']} ({b['top_source_share']})")
    return out


def main():
    print("=== 14-day window ===")
    _build(hours=24 * 14, label="last_14_days", include_pick_rows=False, out_name="pick_summary_stats_2w.json")
    print("=== 48-hour window ===")
    _build(hours=48, label="last_48_hours", include_pick_rows=True, out_name="pick_summary_stats_48h.json")
    from tools.audit_pick_funnel.sync_pick_summary_14d import main as sync_14d

    if sync_14d() != 0:
        print("[build_recency_summary] WARN: sync_pick_summary_14d failed", file=sys.stderr)


if __name__ == "__main__":
    main()
