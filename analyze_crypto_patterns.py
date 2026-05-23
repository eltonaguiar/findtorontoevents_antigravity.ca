#!/usr/bin/env python3
"""Analyze crypto picks in the current audit payload and surface repeatable winner criteria."""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path
from typing import Callable, Iterable


PAYLOAD_PATH = Path("audit_trail/data/dashboard_payload.json")
REPORT_PATH = Path("reports/crypto_golden_criteria_report.md")


def to_float(value):
    if value in (None, "", "n/a", "N/A"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value, default=0):
    if value in (None, "", "n/a", "N/A"):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_dt(value):
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"\s+EST$", "-05:00", text)
    text = re.sub(r"\s+EDT$", "-04:00", text)
    text = re.sub(r"\s+UTC$", "+00:00", text)
    text = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def pearson(xs, ys):
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


def label_wr(value):
    if value is None:
        return "n/a"
    return f"{value:.1f}%"


def fmt_pct(value):
    if value is None:
        return "n/a"
    return f"{value:+.2f}%"


def fmt_num(value, digits=3):
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def is_long(direction):
    return str(direction or "").upper() in {"LONG", "BUY"}


def is_short(direction):
    return str(direction or "").upper() in {"SHORT", "SELL"}


def derive_alignment(row):
    direction = str(row.get("direction") or "").upper()
    if not direction:
        return None

    for field in ("htf_bias", "htf_alignment", "regime_at_entry", "regime_trend_direction"):
        text = str(row.get(field) or "").upper()
        if not text:
            continue
        if "BULL" in text and "WEAK" not in text:
            return is_long(direction)
        if "BEAR" in text and "WEAK" not in text:
            return is_short(direction)

    align = str(row.get("technical_alignment_str") or "").upper()
    match = re.search(r"(\d+)\s*/\s*(\d+)\s+(BUY|SELL)", align)
    if not match:
        return None

    primary = int(match.group(1))
    total = int(match.group(2))
    label = match.group(3)
    if total <= 0:
        return None

    if label == "BUY":
        buy_count = primary
        sell_count = total - primary
    else:
        sell_count = primary
        buy_count = total - primary

    if buy_count == sell_count:
        return None
    if is_long(direction):
        return buy_count > sell_count
    if is_short(direction):
        return sell_count > buy_count
    return None


def score_bucket(score):
    if score >= 70:
        return "70+"
    if score >= 55:
        return "55-69"
    if score >= 40:
        return "40-54"
    return "<40"


def track_bucket(track_wr):
    if track_wr is None:
        return "none"
    if track_wr >= 60:
        return "60+"
    if track_wr >= 50:
        return "50-59"
    if track_wr >= 40:
        return "40-49"
    return "<40"


def agree_bucket(agreement):
    if agreement <= 0:
        return "0"
    if agreement == 1:
        return "1"
    if agreement == 2:
        return "2"
    if agreement <= 4:
        return "3-4"
    return "5+"


def build_row(raw):
    track_wr = to_float(raw.get("strat_fwd_wr"))
    if track_wr is None:
        track_wr = to_float(raw.get("forward_wr"))

    confidence = to_float(raw.get("confidence"))
    if confidence is not None and confidence <= 1.0:
        confidence *= 100.0

    row = dict(raw)
    row["score"] = to_float(raw.get("score")) or 0.0
    row["pnl_pct"] = to_float(raw.get("pnl_pct")) or 0.0
    row["win"] = row["pnl_pct"] > 0
    row["closed_dt"] = parse_dt(raw.get("closed_at"))
    row["entry_dt"] = parse_dt(raw.get("timestamp") or raw.get("entry_time"))
    row["agreement_count"] = to_int(raw.get("agreement_count"), 0)
    row["track_wr"] = track_wr
    row["track_level"] = str(raw.get("track_level") or "none").lower()
    row["confidence_pct"] = confidence
    row["rr_ratio"] = to_float(raw.get("rr_ratio"))
    row["ml_composite_score"] = to_float(raw.get("ml_composite_score"))
    row["trust_tier"] = str(raw.get("trust_tier") or "UNKNOWN").upper()
    row["strong_flag"] = raw.get("strong") is True
    row["strong_missing"] = raw.get("strong") is None
    row["alignment_match"] = derive_alignment(raw)
    row["score_bucket"] = score_bucket(row["score"])
    row["track_bucket"] = track_bucket(row["track_wr"])
    row["agree_bucket"] = agree_bucket(row["agreement_count"])
    row["multi_agree"] = row["agreement_count"] >= 3
    tag_text = " | ".join(
        str(raw.get(key) or "")
        for key in ("strategy", "notes", "reason", "research_cohort", "source_subsystem")
    ).upper()
    row["a_viable"] = "A-VIABLE" in tag_text
    return row


def summarize(rows):
    rows = list(rows)
    total = len(rows)
    wins = sum(1 for row in rows if row["win"])
    total_pnl = sum(row["pnl_pct"] for row in rows)
    return Stats(
        count=total,
        wins=wins,
        win_rate=(wins / total * 100.0) if total else 0.0,
        avg_pnl=(total_pnl / total) if total else 0.0,
        total_pnl=total_pnl,
    )


def bucket_stats(rows, key_fn):
    buckets = {}
    for row in rows:
        key = key_fn(row)
        buckets.setdefault(key, []).append(row)
    return {key: summarize(group) for key, group in buckets.items()}


def correlation_rows(rows):
    metrics = {
        "score": lambda row: row["score"],
        "track_wr": lambda row: row["track_wr"],
        "confidence_pct": lambda row: row["confidence_pct"],
        "agreement_count": lambda row: row["agreement_count"],
        "rr_ratio": lambda row: row["rr_ratio"],
        "ml_composite_score": lambda row: row["ml_composite_score"],
    }
    output = []
    for name, getter in metrics.items():
        pairs = [
            (getter(row), row["pnl_pct"], 1 if row["win"] else 0)
            for row in rows
            if getter(row) is not None
        ]
        if len(pairs) < 20:
            continue
        xs = [item[0] for item in pairs]
        pnls = [item[1] for item in pairs]
        wins = [item[2] for item in pairs]
        output.append(
            {
                "metric": name,
                "count": len(pairs),
                "corr_pnl": pearson(xs, pnls),
                "corr_win": pearson(xs, wins),
            }
        )
    return sorted(output, key=lambda item: abs(item["corr_pnl"] or 0), reverse=True)


@dataclass
class Stats:
    count: int
    wins: int
    win_rate: float
    avg_pnl: float
    total_pnl: float


@dataclass
class RuleCombo:
    labels: tuple[str, ...]
    recent: Stats
    overall: Stats
    active_matches: list[dict]
    score: float


def metadata_coverage(rows, active_rows):
    def pct(part, whole):
        return (part / whole * 100.0) if whole else 0.0

    closed = rows
    active = active_rows
    direct_htf_closed = sum(
        1
        for row in closed
        if any(row.get(field) not in (None, "") for field in ("htf_bias", "htf_alignment", "regime_at_entry"))
    )
    directional_closed = sum(1 for row in closed if row["alignment_match"] is not None)
    directional_active = sum(1 for row in active if row["alignment_match"] is not None)
    strong_closed = sum(1 for row in closed if not row["strong_missing"])
    strong_active = sum(1 for row in active if not row["strong_missing"])
    a_viable_closed = sum(1 for row in closed if row["a_viable"])
    a_viable_active = sum(1 for row in active if row["a_viable"])

    return {
        "closed_direct_htf_pct": pct(direct_htf_closed, len(closed)),
        "closed_directional_alignment_pct": pct(directional_closed, len(closed)),
        "active_directional_alignment_pct": pct(directional_active, len(active)),
        "closed_strong_pct": pct(strong_closed, len(closed)),
        "active_strong_pct": pct(strong_active, len(active)),
        "closed_a_viable_pct": pct(a_viable_closed, len(closed)),
        "active_a_viable_pct": pct(a_viable_active, len(active)),
    }


def latest_rows(rows, days):
    if not rows:
        return []
    cutoff_base = max(row["closed_dt"] for row in rows if row["closed_dt"] is not None)
    cutoff = cutoff_base - timedelta(days=days)
    return [row for row in rows if row["closed_dt"] and row["closed_dt"] >= cutoff]


def evaluate_flag(rows, predicate):
    selected = [row for row in rows if predicate(row)]
    rejected = [row for row in rows if not predicate(row)]
    return summarize(selected), summarize(rejected)


def find_golden_combos(recent_rows, overall_rows, active_rows, min_recent_sample):
    rules = {
        "score >= 40": lambda row: row["score"] >= 40,
        "score >= 55": lambda row: row["score"] >= 55,
        "40 <= score < 70": lambda row: 40 <= row["score"] < 70,
        "track WR >= 50": lambda row: row["track_wr"] is not None and row["track_wr"] >= 50,
        "track WR >= 55": lambda row: row["track_wr"] is not None and row["track_wr"] >= 55,
        "track level = symbol": lambda row: row["track_level"] == "symbol",
        "trust tier reliable+": lambda row: row["trust_tier"] in {"RELIABLE", "PROVEN"},
        "trust tier proven": lambda row: row["trust_tier"] == "PROVEN",
        "agreement <= 2": lambda row: row["agreement_count"] <= 2,
        "agreement 1-2": lambda row: 1 <= row["agreement_count"] <= 2,
        "multi-agree >= 3": lambda row: row["multi_agree"],
        "strong flag": lambda row: row["strong_flag"],
        "HTF/tech matches dir": lambda row: row["alignment_match"] is True,
        "LONG": lambda row: is_long(row.get("direction")),
        "SHORT": lambda row: is_short(row.get("direction")),
    }

    baseline_recent = summarize(recent_rows)
    baseline_overall = summarize(overall_rows)
    combos = []

    for size in (2, 3, 4):
        for labels in combinations(rules.keys(), size):
            funcs = [rules[label] for label in labels]
            recent_subset = [row for row in recent_rows if all(func(row) for func in funcs)]
            if len(recent_subset) < min_recent_sample:
                continue

            overall_subset = [row for row in overall_rows if all(func(row) for func in funcs)]
            if len(overall_subset) < max(30, min_recent_sample * 2):
                continue

            recent_stats = summarize(recent_subset)
            overall_stats = summarize(overall_subset)

            if recent_stats.avg_pnl <= baseline_recent.avg_pnl:
                continue
            if recent_stats.win_rate <= baseline_recent.win_rate:
                continue
            if overall_stats.avg_pnl <= baseline_overall.avg_pnl:
                continue

            score = (
                (recent_stats.avg_pnl - baseline_recent.avg_pnl) * 1.5
                + (recent_stats.win_rate - baseline_recent.win_rate) * 0.08
                + (overall_stats.avg_pnl - baseline_overall.avg_pnl)
                + math.log(len(recent_subset) + 1.0)
            )

            active_subset = [row for row in active_rows if all(func(row) for func in funcs)]
            active_subset.sort(
                key=lambda row: (
                    row["score"],
                    row["track_wr"] if row["track_wr"] is not None else -1.0,
                    row["agreement_count"],
                ),
                reverse=True,
            )
            combos.append(
                RuleCombo(
                    labels=labels,
                    recent=recent_stats,
                    overall=overall_stats,
                    active_matches=active_subset[:12],
                    score=score,
                )
            )

    combos.sort(
        key=lambda combo: (
            combo.score,
            combo.recent.avg_pnl,
            combo.recent.win_rate,
            combo.recent.count,
        ),
        reverse=True,
    )

    deduped = []
    seen = set()
    for combo in combos:
        signature = (
            combo.recent.count,
            round(combo.recent.win_rate, 3),
            round(combo.recent.avg_pnl, 3),
            combo.overall.count,
            round(combo.overall.win_rate, 3),
            round(combo.overall.avg_pnl, 3),
            tuple((row.get("symbol"), row.get("source_system")) for row in combo.active_matches[:6]),
        )
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(combo)
        if len(deduped) >= 10:
            break
    return deduped


def shortlist_active(combo, limit=8):
    rows = combo.active_matches[:limit]
    return [
        {
            "symbol": row.get("symbol"),
            "direction": row.get("direction"),
            "source_system": row.get("source_system"),
            "strategy": row.get("strategy"),
            "score": row["score"],
            "track_wr": row["track_wr"],
            "agreement_count": row["agreement_count"],
            "pnl_pct": row.get("pnl_pct"),
            "trust_tier": row.get("trust_tier"),
        }
        for row in rows
    ]


def render_bucket_table(title, stats_map, order=None):
    lines = [f"### {title}", "", "| Bucket | Trades | Win Rate | Avg PnL | Total PnL |", "| --- | ---: | ---: | ---: | ---: |"]
    keys = order or sorted(stats_map.keys())
    for key in keys:
        stats = stats_map.get(key)
        if not stats:
            continue
        lines.append(
            f"| {key} | {stats.count} | {stats.win_rate:.1f}% | {stats.avg_pnl:+.2f}% | {stats.total_pnl:+.2f}% |"
        )
    lines.append("")
    return lines


def render_summary_block(name, stats):
    return [
        f"### {name}",
        "",
        f"- Trades: {stats.count}",
        f"- Win rate: {stats.win_rate:.1f}%",
        f"- Avg PnL: {stats.avg_pnl:+.2f}%",
        f"- Total PnL: {stats.total_pnl:+.2f}%",
        "",
    ]


def build_report(payload_rows, active_rows, windows, correlations, coverage, combos):
    lines = [
        "# Crypto Golden Criteria Report",
        "",
        f"- Generated from: `{PAYLOAD_PATH}`",
        f"- Generated at UTC: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Closed crypto trades analyzed: `{len(payload_rows)}`",
        f"- Active crypto picks analyzed: `{len(active_rows)}`",
        "",
        "## Metadata Gaps",
        "",
        f"- Direct HTF bias survives into closed crypto rows only `{coverage['closed_direct_htf_pct']:.1f}%` of the time.",
        f"- Directional HTF/technical alignment is derivable on `{coverage['closed_directional_alignment_pct']:.1f}%` of closed rows and `{coverage['active_directional_alignment_pct']:.1f}%` of active rows.",
        f"- `strong` is populated on `{coverage['closed_strong_pct']:.1f}%` of closed rows and `{coverage['active_strong_pct']:.1f}%` of active rows.",
        f"- `A-viable` tagging coverage is `{coverage['closed_a_viable_pct']:.1f}%` on closed rows and `{coverage['active_a_viable_pct']:.1f}%` on active rows.",
        "",
        "## Cohort Windows",
        "",
    ]

    for name, rows in windows.items():
        lines.extend(render_summary_block(name, summarize(rows)))

    lines.extend(
        [
            "## Metric Correlations",
            "",
            "| Metric | Rows | Corr vs PnL % | Corr vs Win |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for item in correlations:
        lines.append(
            f"| {item['metric']} | {item['count']} | {fmt_num(item['corr_pnl'])} | {fmt_num(item['corr_win'])} |"
        )
    lines.append("")

    recent = windows["Last 3 Days"]
    lines.extend(
        render_bucket_table(
            "Score Buckets (Last 3 Days)",
            bucket_stats(recent, lambda row: row["score_bucket"]),
            order=["<40", "40-54", "55-69", "70+"],
        )
    )
    lines.extend(
        render_bucket_table(
            "Track WR Buckets (Last 3 Days)",
            bucket_stats(recent, lambda row: row["track_bucket"]),
            order=["none", "<40", "40-49", "50-59", "60+"],
        )
    )
    lines.extend(
        render_bucket_table(
            "Agreement Buckets (Last 3 Days)",
            bucket_stats(recent, lambda row: row["agree_bucket"]),
            order=["0", "1", "2", "3-4", "5+"],
        )
    )
    lines.extend(
        render_bucket_table(
            "Trust Tiers (Last 3 Days)",
            bucket_stats(recent, lambda row: row["trust_tier"]),
            order=["PROVEN", "RELIABLE", "WATCH", "UNTRUSTED", "BANNED"],
        )
    )

    strong_yes = evaluate_flag(recent, lambda row: row["strong_flag"])[0]
    strong_no = evaluate_flag(
        [row for row in recent if not row["strong_missing"]],
        lambda row: row["strong_flag"],
    )
    htf_yes, htf_no = evaluate_flag(
        [row for row in recent if row["alignment_match"] is not None],
        lambda row: row["alignment_match"] is True,
    )
    multi_yes, multi_no = evaluate_flag(recent, lambda row: row["multi_agree"])

    lines.extend(
        [
            "## Hypothesis Checks",
            "",
            f"- `score`: see the score buckets above. The sweet spot is where win rate and avg PnL both stay above baseline without running into overconfidence.",
            f"- `track_wr`: compare the track buckets above. This is the cleanest direct proxy for real track record.",
            f"- `multi-agree >= 3`: {multi_yes.count} trades, {multi_yes.win_rate:.1f}% WR, {multi_yes.avg_pnl:+.2f}% avg PnL. Control cohort: {multi_no.count} trades, {multi_no.win_rate:.1f}% WR, {multi_no.avg_pnl:+.2f}%.",
            f"- `strong=True`: {strong_yes.count} trades, {strong_yes.win_rate:.1f}% WR, {strong_yes.avg_pnl:+.2f}% avg PnL. Other labeled rows: {strong_no[1].count} trades, {strong_no[1].win_rate:.1f}% WR, {strong_no[1].avg_pnl:+.2f}%.",
            f"- `HTF/technical match to direction`: {htf_yes.count} trades, {htf_yes.win_rate:.1f}% WR, {htf_yes.avg_pnl:+.2f}% avg PnL. Mismatch cohort: {htf_no.count} trades, {htf_no.win_rate:.1f}% WR, {htf_no.avg_pnl:+.2f}%.",
            f"- `A-viable`: no usable sample in the current payload. This is a metadata gap, not a negative result.",
            "",
            "## Golden Criteria Candidates",
            "",
        ]
    )

    if not combos:
        lines.append("No rule combo cleared the sample and validation gates.")
        lines.append("")
    else:
        for idx, combo in enumerate(combos[:5], start=1):
            lines.extend(
                [
                    f"### Candidate {idx}",
                    "",
                    f"- Rule: `{', '.join(combo.labels)}`",
                    f"- Last 3 days: {combo.recent.count} trades, {combo.recent.win_rate:.1f}% WR, {combo.recent.avg_pnl:+.2f}% avg PnL",
                    f"- Full sample: {combo.overall.count} trades, {combo.overall.win_rate:.1f}% WR, {combo.overall.avg_pnl:+.2f}% avg PnL",
                    "",
                ]
            )
            shortlist = shortlist_active(combo)
            if shortlist:
                lines.extend(
                    [
                        "| Active Match | Dir | Score | Track WR | Agree | Trust | Source |",
                        "| --- | --- | ---: | ---: | ---: | --- | --- |",
                    ]
                )
                for row in shortlist:
                    track_text = "n/a" if row["track_wr"] is None else f"{row['track_wr']:.1f}%"
                    lines.append(
                        f"| {row['symbol']} | {row['direction']} | {row['score']:.0f} | {track_text} | {row['agreement_count']} | {row['trust_tier']} | {row['source_system']} |"
                    )
                lines.append("")

    return "\n".join(lines)


def console_summary(correlations, recent_rows, combos, coverage):
    baseline = summarize(recent_rows)
    score_stats = bucket_stats(recent_rows, lambda row: row["score_bucket"])
    track_stats = bucket_stats(recent_rows, lambda row: row["track_bucket"])
    agree_stats = bucket_stats(recent_rows, lambda row: row["agree_bucket"])
    aligned_rows = [row for row in recent_rows if row["alignment_match"] is not None]
    aligned_yes, aligned_no = evaluate_flag(aligned_rows, lambda row: row["alignment_match"] is True)

    print("=== CRYPTO GOLDEN CRITERIA ===")
    print(f"Recent closed crypto sample (last 3d): {baseline.count} trades | WR {baseline.win_rate:.1f}% | Avg PnL {baseline.avg_pnl:+.2f}%")
    print(f"Metadata gaps: direct HTF only {coverage['closed_direct_htf_pct']:.1f}% of closed rows | A-viable tags {coverage['closed_a_viable_pct']:.1f}%")
    print()
    print("Top correlations vs PnL:")
    for item in correlations[:5]:
        print(
            f"  {item['metric']:<18} corr_pnl={fmt_num(item['corr_pnl'])}  corr_win={fmt_num(item['corr_win'])}  rows={item['count']}"
        )
    print()
    print("Score buckets (last 3d):")
    for key in ("<40", "40-54", "55-69", "70+"):
        stats = score_stats.get(key)
        if stats:
            print(f"  {key:<6} {stats.count:>4} trades | WR {stats.win_rate:>5.1f}% | Avg {stats.avg_pnl:+.2f}%")
    print()
    print("Track WR buckets (last 3d):")
    for key in ("none", "<40", "40-49", "50-59", "60+"):
        stats = track_stats.get(key)
        if stats:
            print(f"  {key:<6} {stats.count:>4} trades | WR {stats.win_rate:>5.1f}% | Avg {stats.avg_pnl:+.2f}%")
    print()
    print("Agreement buckets (last 3d):")
    for key in ("0", "1", "2", "3-4", "5+"):
        stats = agree_stats.get(key)
        if stats:
            print(f"  {key:<4} {stats.count:>4} trades | WR {stats.win_rate:>5.1f}% | Avg {stats.avg_pnl:+.2f}%")
    print()
    if aligned_rows:
        print(
            "HTF/technical proxy vs direction:"
            f" match {aligned_yes.count} trades | WR {aligned_yes.win_rate:.1f}% | Avg {aligned_yes.avg_pnl:+.2f}%"
            f" ; mismatch {aligned_no.count} trades | WR {aligned_no.win_rate:.1f}% | Avg {aligned_no.avg_pnl:+.2f}%"
        )
        print()
    if combos:
        best = combos[0]
        print("Best current rule combo:")
        print(f"  {' + '.join(best.labels)}")
        print(
            f"  recent: {best.recent.count} trades | WR {best.recent.win_rate:.1f}% | Avg {best.recent.avg_pnl:+.2f}%"
        )
        print(
            f"  overall: {best.overall.count} trades | WR {best.overall.win_rate:.1f}% | Avg {best.overall.avg_pnl:+.2f}%"
        )
        if best.active_matches:
            print("  active matches:")
            for row in shortlist_active(best, limit=6):
                track_text = "n/a" if row["track_wr"] is None else f"{row['track_wr']:.1f}%"
                print(
                    f"    {row['symbol']} {row['direction']} | score {row['score']:.0f} | track {track_text} | agree {row['agreement_count']} | {row['source_system']}"
                )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default=str(REPORT_PATH), help="Path to markdown report output")
    parser.add_argument("--recent-days", type=int, default=3, help="Recent window used for golden-criteria search")
    parser.add_argument("--min-recent-sample", type=int, default=20, help="Minimum recent trades per rule combo")
    args = parser.parse_args()

    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    closed_rows = [
        build_row(row)
        for row in payload["picks"]["recent_closed"]
        if row.get("asset_class") == "CRYPTO" and parse_dt(row.get("closed_at"))
    ]
    active_rows = [
        build_row(row)
        for row in payload["picks"]["active"]
        if row.get("asset_class") == "CRYPTO"
    ]

    recent_rows = latest_rows(closed_rows, args.recent_days)
    windows = {
        "Full Sample": closed_rows,
        "Last 7 Days": latest_rows(closed_rows, 7),
        "Last 3 Days": recent_rows,
        "Last 1 Day": latest_rows(closed_rows, 1),
    }

    correlations = correlation_rows(recent_rows)
    coverage = metadata_coverage(closed_rows, active_rows)
    combos = find_golden_combos(recent_rows, closed_rows, active_rows, args.min_recent_sample)
    report = build_report(closed_rows, active_rows, windows, correlations, coverage, combos)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    console_summary(correlations, recent_rows, combos, coverage)
    print()
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
