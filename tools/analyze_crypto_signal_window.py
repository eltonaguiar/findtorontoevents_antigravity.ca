#!/usr/bin/env python3
"""
Rolling-window analysis of closed CRYPTO picks from audit_trail/data/dashboard_payload.json.

Methodology (documented in reports/crypto_signal_confluence_analysis_2026-03-28.md):
- Cohort: recent_closed rows with asset_class CRYPTO and closed_at in [generated_at - hours, generated_at].
- Outcomes: WON / TP_HIT -> win; LOST / SL_HIT -> loss.
- Buckets: agreement_count (0, 1-2, 3-4, 5+), rsi_at_entry bands, volume_ratio bands.
- Parses closed_at with Z, +offset, or trailing EST/EDT (fixed offset; not DST-perfect).

Usage:
  python tools/analyze_crypto_signal_window.py --hours 3
  python tools/analyze_crypto_signal_window.py --hours 24 --json
  python tools/analyze_crypto_signal_window.py --compare
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PAYLOAD = ROOT / "audit_trail" / "data" / "dashboard_payload.json"


def parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    raw = str(s).strip()
    try:
        if raw.endswith(" EST"):
            raw = raw[: -len(" EST")] + "-05:00"
        elif raw.endswith(" EDT"):
            raw = raw[: -len(" EDT")] + "-04:00"
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def classify_outcome(row: dict) -> str:
    st = (row.get("status") or "").upper()
    er = (row.get("exit_reason") or "").upper()
    if st == "WON" or er == "TP_HIT":
        return "win"
    if st == "LOST" or er == "SL_HIT":
        return "loss"
    return "other"


def rsi_bucket(v) -> str:
    if v is None:
        return "missing"
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "missing"
    if x < 35:
        return "<35"
    if x < 45:
        return "35-45"
    if x < 55:
        return "45-55"
    if x < 65:
        return "55-65"
    return "65+"


def agree_bucket(r: dict) -> str:
    a = r.get("agreement_count")
    if a is None:
        return "missing"
    try:
        ai = int(float(a))
    except (TypeError, ValueError):
        return "missing"
    if ai == 0:
        return "0"
    if ai <= 2:
        return "1-2"
    if ai <= 4:
        return "3-4"
    return "5+"


def vol_bucket(r: dict) -> str:
    v = r.get("volume_ratio")
    if v is None:
        return "missing"
    try:
        vf = float(v)
    except (TypeError, ValueError):
        return "missing"
    if vf < 1:
        return "<1"
    if vf < 1.5:
        return "1-1.5"
    return "1.5+"


def effective_rsi(row: dict) -> float | None:
    """Prefer rsi_at_entry; fall back to technical_rsi_4h when entry RSI is absent."""
    v = row.get("rsi_at_entry")
    if v is not None:
        try:
            return float(v)
        except (TypeError, ValueError):
            pass
    v2 = row.get("technical_rsi_4h")
    if v2 is not None:
        try:
            return float(v2)
        except (TypeError, ValueError):
            pass
    return None


def load_cohort(payload_path: Path, hours: int) -> tuple[datetime, list[dict]]:
    with payload_path.open(encoding="utf-8") as f:
        d = json.load(f)
    gen = parse_dt(d.get("generated_at"))
    if gen is None:
        raise SystemExit("payload missing or invalid generated_at")
    cutoff = gen - timedelta(hours=hours)
    rows: list[dict] = []
    for r in d.get("picks", {}).get("recent_closed", []):
        if (r.get("asset_class") or "").upper() != "CRYPTO":
            continue
        ca = parse_dt(r.get("closed_at"))
        if ca is None or ca < cutoff:
            continue
        oc = classify_outcome(r)
        rsi_at = r.get("rsi_at_entry")
        rows.append(
            {
                "symbol": r.get("symbol"),
                "strategy": r.get("strategy") or r.get("source_system"),
                "outcome": oc,
                "rsi": rsi_at,
                "rsi_effective": effective_rsi(r),
                "agreement_count": r.get("agreement_count"),
                "volume_ratio": r.get("volume_ratio"),
                "score": r.get("score"),
                "confluence_score": r.get("confluence_score"),
                "trust_tier": r.get("trust_tier"),
                "closed_at": ca.isoformat(),
            }
        )
    return gen, rows


def bucket_stats(rows: list[dict], key_fn) -> dict:
    b: dict[str, dict[str, int]] = defaultdict(lambda: {"w": 0, "l": 0})
    for r in rows:
        if r["outcome"] == "win":
            b[key_fn(r)]["w"] += 1
        elif r["outcome"] == "loss":
            b[key_fn(r)]["l"] += 1
    out: dict[str, dict] = {}
    for k, v in b.items():
        t = v["w"] + v["l"]
        out[k] = {
            "wins": v["w"],
            "losses": v["l"],
            "win_rate_pct": round(100.0 * v["w"] / t, 1) if t else 0.0,
        }
    return out


def mean_score(rows: list[dict], outcome: str) -> tuple[float | None, int]:
    vals = []
    for r in rows:
        if r["outcome"] != outcome:
            continue
        s = r["score"]
        if s is None:
            continue
        try:
            vals.append(float(s))
        except (TypeError, ValueError):
            continue
    if not vals:
        return None, 0
    return round(statistics.mean(vals), 2), len(vals)


def trust_bucket(r: dict) -> str:
    t = r.get("trust_tier")
    if t is None or str(t).strip() == "":
        return "missing"
    return str(t).strip().upper()


def top_strategies(rows: list[dict], min_trades: int = 5) -> list[dict]:
    sc: dict[str, dict[str, int]] = defaultdict(lambda: {"w": 0, "l": 0})
    for r in rows:
        if r["outcome"] not in ("win", "loss"):
            continue
        s = r["strategy"] or "unknown"
        if r["outcome"] == "win":
            sc[s]["w"] += 1
        else:
            sc[s]["l"] += 1
    ranked = []
    for strat, v in sc.items():
        t = v["w"] + v["l"]
        if t < min_trades:
            continue
        ranked.append(
            {
                "strategy": strat,
                "wins": v["w"],
                "losses": v["l"],
                "win_rate_pct": round(100.0 * v["w"] / t, 1),
            }
        )
    ranked.sort(key=lambda x: (-x["win_rate_pct"], -(x["wins"] + x["losses"])))
    return ranked[:25]


def data_quality(rows: list[dict]) -> dict:
    decided = [r for r in rows if r["outcome"] in ("win", "loss")]
    n = len(decided)
    if not n:
        return {
            "decided_trades": 0,
            "rsi_at_entry_missing_pct": None,
            "volume_ratio_missing_pct": None,
            "rsi_effective_missing_pct": None,
        }
    miss_rsi = sum(1 for r in decided if r["rsi"] is None)
    miss_vol = sum(1 for r in decided if r.get("volume_ratio") is None)
    miss_eff = sum(1 for r in decided if r.get("rsi_effective") is None)
    return {
        "decided_trades": n,
        "rsi_at_entry_missing_pct": round(100.0 * miss_rsi / n, 1),
        "volume_ratio_missing_pct": round(100.0 * miss_vol / n, 1),
        "rsi_effective_missing_pct": round(100.0 * miss_eff / n, 1),
    }


def top_pairs(rows: list[dict], min_trades: int = 2) -> list[dict]:
    pair_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"w": 0, "l": 0})
    for r in rows:
        if r["outcome"] not in ("win", "loss"):
            continue
        pair = f"{r['strategy']}::{r['symbol']}"
        if r["outcome"] == "win":
            pair_counts[pair]["w"] += 1
        else:
            pair_counts[pair]["l"] += 1
    ranked = []
    for pair, v in pair_counts.items():
        t = v["w"] + v["l"]
        if t < min_trades:
            continue
        wr = v["w"] / t
        ranked.append(
            {
                "pair": pair,
                "wins": v["w"],
                "losses": v["l"],
                "win_rate_pct": round(100.0 * wr, 1),
            }
        )
    ranked.sort(key=lambda x: (-x["win_rate_pct"], -(x["wins"] + x["losses"])))
    return ranked[:20]


def score_inversion_warning(mw: float | None, ml: float | None) -> str | None:
    if mw is None or ml is None:
        return None
    if mw < ml:
        return (
            "Mean score is LOWER on winners than losers in this window - "
            "do not use score as a directional filter without a longer sample."
        )
    return None


def build_report(gen: datetime, hours: int, rows: list[dict]) -> dict:
    wins = sum(1 for r in rows if r["outcome"] == "win")
    losses = sum(1 for r in rows if r["outcome"] == "loss")
    other = len(rows) - wins - losses
    decided = wins + losses
    wr = round(100.0 * wins / decided, 1) if decided else 0.0
    mw, nw = mean_score(rows, "win")
    ml, nl = mean_score(rows, "loss")
    return {
        "payload_generated_at": gen.isoformat(),
        "window_hours": hours,
        "total_trades": len(rows),
        "wins": wins,
        "losses": losses,
        "other_outcomes": other,
        "win_rate_pct": wr,
        "mean_score_winners": mw,
        "mean_score_winners_n": nw,
        "mean_score_losers": ml,
        "mean_score_losers_n": nl,
        "mean_score_gap": round(mw - ml, 2) if mw is not None and ml is not None else None,
        "score_note": score_inversion_warning(mw, ml),
        "data_quality": data_quality(rows),
        "agreement_buckets": bucket_stats(rows, agree_bucket),
        "trust_tier_buckets": bucket_stats(rows, trust_bucket),
        "rsi_buckets_entry_only": bucket_stats(rows, lambda r: rsi_bucket(r["rsi"])),
        "rsi_buckets_effective": bucket_stats(
            rows, lambda r: rsi_bucket(r.get("rsi_effective"))
        ),
        "volume_ratio_buckets": bucket_stats(rows, vol_bucket),
        "top_strategy_symbol_pairs": top_pairs(rows),
        "top_strategies_min5": top_strategies(rows, min_trades=5),
    }


def print_report_human(report: dict, *, top_pairs_n: int = 10) -> None:
    print("Payload generated_at:", report["payload_generated_at"])
    print("Window: last", report["window_hours"], "h | Crypto closed picks:", report["total_trades"])
    print(
        "Win rate:",
        f"{report['win_rate_pct']}%",
        f"({report['wins']}W / {report['losses']}L, other={report['other_outcomes']})",
    )
    dq = report.get("data_quality") or {}
    if dq.get("decided_trades"):
        print(
            "Data quality: RSI@entry missing",
            f"{dq.get('rsi_at_entry_missing_pct')}%",
            "| vol_ratio missing",
            f"{dq.get('volume_ratio_missing_pct')}%",
            "| RSI effective missing",
            f"{dq.get('rsi_effective_missing_pct')}%",
        )
    if report["mean_score_winners_n"] or report["mean_score_losers_n"]:
        print(
            "Mean score: winners",
            report["mean_score_winners"],
            f"n={report['mean_score_winners_n']}",
            "| losers",
            report["mean_score_losers"],
            f"n={report['mean_score_losers_n']}",
            "| gap",
            report.get("mean_score_gap"),
        )
    if report.get("score_note"):
        print("NOTE:", report["score_note"])
    print("\nAgreement buckets:", json.dumps(report["agreement_buckets"], indent=2))
    print("\nTrust tier buckets:", json.dumps(report["trust_tier_buckets"], indent=2))
    print("\nRSI buckets (entry only):", json.dumps(report["rsi_buckets_entry_only"], indent=2))
    print("\nRSI buckets (effective = entry or technical_rsi_4h):", json.dumps(report["rsi_buckets_effective"], indent=2))
    print("\nVolume ratio buckets:", json.dumps(report["volume_ratio_buckets"], indent=2))
    print("\nTop strategies (min 5 trades):", json.dumps(report["top_strategies_min5"][:10], indent=2))
    print(
        "\nTop pairs (min 2 trades):",
        json.dumps(report["top_strategy_symbol_pairs"][:top_pairs_n], indent=2),
    )


def run_compare(payload_path: Path) -> None:
    with payload_path.open(encoding="utf-8") as f:
        d = json.load(f)
    gen = parse_dt(d.get("generated_at"))
    if gen is None:
        raise SystemExit("payload missing or invalid generated_at")
    print("Payload generated_at:", gen.isoformat())
    print("\n=== Multi-window summary (CRYPTO, closed_at) ===\n")
    hdr = f"{'hrs':>4} {'n':>5} {'WR%':>6} {'5+WR':>7} {'3-4WR':>7} {'0WR':>7} {'sc_gap':>8}"
    print(hdr)
    print("-" * len(hdr))
    for h in (3, 24, 72, 168):
        _, rows = load_cohort(payload_path, h)
        rep = build_report(gen, h, rows)
        ab = rep["agreement_buckets"]
        g5 = ab.get("5+", {})
        g34 = ab.get("3-4", {})
        g0 = ab.get("0", {})
        dlt = rep.get("mean_score_gap")
        dlt_s = f"{dlt:+.2f}" if dlt is not None else "n/a"
        print(
            f"{h:>4} {rep['total_trades']:>5} {rep['win_rate_pct']:>5.1f}% "
            f"{g5.get('win_rate_pct', 0):>6.1f}% {g34.get('win_rate_pct', 0):>6.1f}% "
            f"{g0.get('win_rate_pct', 0):>6.1f}% {dlt_s:>8}"
        )
    print(
        "\nLegend: 5+/3-4/0 = win rate inside agreement_count bucket. "
        "sc_gap = mean(score|win) - mean(score|loss). "
        "Negative sc_gap means score is inverted for that window."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze closed crypto picks over a time window.")
    ap.add_argument("--hours", type=int, default=3, help="Hours before payload generated_at (default 3)")
    ap.add_argument(
        "--payload",
        type=Path,
        default=DEFAULT_PAYLOAD,
        help="Path to dashboard_payload.json",
    )
    ap.add_argument("--json", action="store_true", help="Print JSON only")
    ap.add_argument(
        "--compare",
        action="store_true",
        help="Print 3/24/72/168h comparison table (ignores --hours for main report)",
    )
    args = ap.parse_args()

    if not args.payload.is_file():
        raise SystemExit(f"Payload not found: {args.payload}")

    if args.compare:
        run_compare(args.payload)
        return

    gen, rows = load_cohort(args.payload, args.hours)
    report = build_report(gen, args.hours, rows)

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print_report_human(report)


if __name__ == "__main__":
    main()
