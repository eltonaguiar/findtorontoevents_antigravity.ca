"""Synthesize Phase 3 ranked-proposal panel responses across 7 AIs.

Outputs:
- Per-PR vote count + average rank in reranked_priority
- Aggregate session_grade (mode + median GPA)
- Top ordering_critiques by frequency of (shipped_pr, should_have_shipped_first) pair
- Top missing_actions by name canonicalization + frequency
- All ONE_BIG_LESSON_FOR_NEXT_SESSION verbatim
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

PANEL_DIR = Path(__file__).resolve().parent
SUMMARY = json.loads((PANEL_DIR / "_dispatch_summary.json").read_text(encoding="utf-8"))


def extract_parsed_json(md_path: Path) -> dict | None:
    txt = md_path.read_text(encoding="utf-8")
    m = re.search(r"## Parsed JSON\s*\n+```json\n(.*?)\n```", txt, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def grade_to_gpa(g: str) -> float:
    return {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}.get(g.strip().upper()[:1], 2.0)


def gpa_to_grade(gpa: float) -> str:
    if gpa >= 3.5:
        return "A"
    if gpa >= 2.5:
        return "B"
    if gpa >= 1.5:
        return "C"
    if gpa >= 0.5:
        return "D"
    return "F"


def main():
    panelists = []
    for r in SUMMARY["results"]:
        if not r.get("valid_json"):
            continue
        path = PANEL_DIR.parent.parent / r["file"]
        parsed = extract_parsed_json(path)
        if parsed:
            panelists.append((r["provider"], r["model"], parsed))

    print(f"Synthesizing {len(panelists)} valid panelists\n")

    # 1. Re-ranked priority: count appearances + average rank per PR
    pr_appearances = Counter()
    pr_ranks = defaultdict(list)
    for _, _, p in panelists:
        for entry in p.get("reranked_priority", []):
            pr_num = entry.get("pr")
            rank = entry.get("rank")
            if pr_num is None or rank is None:
                continue
            pr_appearances[pr_num] += 1
            pr_ranks[pr_num].append(rank)

    print("=" * 80)
    print("RE-RANKED PRIORITY — PRs by panel count + median rank")
    print("=" * 80)
    rows = []
    for pr_num, count in pr_appearances.most_common():
        ranks = sorted(pr_ranks[pr_num])
        median = ranks[len(ranks) // 2] if ranks else None
        rows.append((pr_num, count, median, ranks))
    rows.sort(key=lambda x: (-x[1], x[2] if x[2] is not None else 999))
    for pr_num, count, median, ranks in rows[:20]:
        print(f"  PR #{pr_num:<5} appearances={count}/{len(panelists)}  median_rank={median}  ranks={ranks}")

    # 2. Ordering critiques: count (shipped_pr, should_have_shipped_first) pairs
    print("\n" + "=" * 80)
    print("ORDERING CRITIQUES — frequency of (shipped, should_have_first) pairs")
    print("=" * 80)
    crit_pairs = Counter()
    crit_reasons = defaultdict(list)
    for prov, model, p in panelists:
        for entry in p.get("ordering_critiques", []):
            shipped = entry.get("shipped_pr")
            should_first = entry.get("should_have_shipped_first")
            reason = entry.get("reason", "")
            key = (shipped, should_first)
            crit_pairs[key] += 1
            crit_reasons[key].append((prov, model, reason))
    for (shipped, should_first), count in crit_pairs.most_common(8):
        print(f"  shipped=#{shipped} should_have_first=#{should_first}  ({count} panelists)")
        for prov, model, reason in crit_reasons[(shipped, should_first)][:2]:
            print(f"    [{model}] {reason[:200]}")

    # 3. Missing actions: canonicalize by lowercasing + dedup keywords
    print("\n" + "=" * 80)
    print("MISSING ACTIONS — frequency by canonical name")
    print("=" * 80)
    miss_canon = Counter()
    miss_details = defaultdict(list)
    for prov, model, p in panelists:
        for entry in p.get("missing_actions_we_didnt_ship", []):
            name = entry.get("action", "").strip().lower()
            # canonicalize by first 2-3 keywords
            canon = " ".join(re.findall(r"[a-z0-9]+", name)[:4])
            miss_canon[canon] += 1
            miss_details[canon].append((prov, model, entry))
    for canon, count in miss_canon.most_common(10):
        print(f"  '{canon}' — {count} panelists")
        for prov, model, entry in miss_details[canon][:2]:
            print(f"    [{model}] action={entry.get('action')!r:60s} priority={entry.get('priority')}")

    # 4. Session grade
    print("\n" + "=" * 80)
    print("SESSION GRADE")
    print("=" * 80)
    grades = []
    for prov, model, p in panelists:
        g = p.get("overall_session_grade", "?")
        grades.append((prov, model, g))
        print(f"  [{model}] grade={g}")
    gpas = [grade_to_gpa(g) for _, _, g in grades]
    avg_gpa = sum(gpas) / len(gpas) if gpas else 0
    print(f"\n  AVG GPA: {avg_gpa:.2f}  =>  Aggregate grade: {gpa_to_grade(avg_gpa)}")

    # 5. ONE BIG LESSON
    print("\n" + "=" * 80)
    print("ONE BIG LESSON FOR NEXT SESSION (verbatim per panelist)")
    print("=" * 80)
    for prov, model, p in panelists:
        lesson = p.get("ONE_BIG_LESSON_FOR_NEXT_SESSION", "")
        print(f"\n  [{model}]")
        print(f"  {lesson}")


if __name__ == "__main__":
    main()
