#!/usr/bin/env python3
"""Overconfidence-decay A/B attribution harness report (A2).

Pairs with `alpha_engine/score_booster.py::_apply_overconfidence_decay`.

When the pipeline runs with env `OVERCONFIDENCE_DECAY=1` (default), the score
booster stamps every pick with `_overconfidence_arm` ('A' = control / no decay,
'B' = treatment / decay applied). The decay is hash-bucketed on
hash(id or symbol+timestamp) % 2, so its effect is finally measurable against
a control arm. With `OVERCONFIDENCE_DECAY=0` the kill-switch is active: no
stamp, no decay.

This tool reads closed picks, filters to those carrying `_overconfidence_arm`,
groups by arm, and reports per-arm realized performance — focused on the
top-quartile (by score), since that is where overconfidence decay actually
bites.

Per-arm metrics:
  n                    closed picks in the arm
  WR                   win rate (WON, or terminal-status with pnl_pct > 0)
  PF                   profit factor (sum gains / abs sum losses)
  top-quartile n/WR    n and WR of the top 25% of the arm ranked by score

Verdict (acceptance bar from the A2 plan):
  TREATMENT-OK         arm B top-quartile WR >= arm A top-quartile WR - 1pp,
                       AND both arms have top-quartile n >= MIN_N
  REGRESSION           both arms have n >= MIN_N but arm B top-quartile WR
                       falls more than 1pp below arm A
  INSUFFICIENT-N       either arm has top-quartile n < MIN_N (expected until
                       the flag has run live for ~30 days)

Usage:
    python tools/overconfidence_ab_report.py [--closed PATH] [--min-n N]
    python tools/overconfidence_ab_report.py --selftest

The self-test proves the hash bucketing (mirrored from score_booster) is
deterministic and ~50/50, and that arm tagging is stamped by the booster.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLOSED = _REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"

# INSUFFICIENT-N below this many top-quartile closed picks per arm.
MIN_N = 50
# Acceptance bar: arm B top-quartile WR must be within 1pp of arm A.
ACCEPT_MARGIN_PP = 1.0

# Score field preference order (closed picks may not carry the live `score`).
_SCORE_FIELDS = ("score", "elite_score", "ml_composite_score", "method_a_score")


# --------------------------------------------------------------------------
# Bucketing — kept in sync with score_booster._overconf_ab_key/_bucket.
# --------------------------------------------------------------------------
def overconf_ab_key(pick: dict) -> str:
    """Stable identity key. MUST match score_booster._overconf_ab_key."""
    pid = pick.get("id")
    if pid:
        return str(pid)
    sym = str(pick.get("symbol", "") or "")
    ts = str(pick.get("created_at") or pick.get("timestamp") or "")
    return (sym + "|" + ts).strip("|")


def overconf_ab_bucket(key: str) -> str:
    """Stable 50/50 hash bucket. MUST match score_booster._overconf_ab_bucket."""
    if not key:
        return "A"
    h = int(hashlib.sha1(str(key).encode("utf-8")).hexdigest(), 16)
    return "B" if (h % 2 == 1) else "A"


# --------------------------------------------------------------------------
# Outcome helpers
# --------------------------------------------------------------------------
def _is_closed(pick: dict) -> bool:
    return str(pick.get("status", "")).upper() in ("WON", "LOST", "CLOSED", "EXPIRED")


def _pnl(pick: dict) -> float:
    try:
        return float(pick.get("pnl_pct") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _is_win(pick: dict) -> bool:
    """Win = explicit WON status, else terminal status with positive pnl_pct."""
    status = str(pick.get("status", "")).upper()
    if status == "WON":
        return True
    if status == "LOST":
        return False
    return _pnl(pick) > 0.0


def _score(pick: dict) -> float:
    for f in _SCORE_FIELDS:
        v = pick.get(f)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return 0.0


def _pf(picks: list[dict]) -> float:
    gains = sum(_pnl(p) for p in picks if _pnl(p) > 0)
    losses = sum(-_pnl(p) for p in picks if _pnl(p) < 0)
    if losses > 0:
        return gains / losses
    return float("inf") if gains > 0 else 0.0


# --------------------------------------------------------------------------
# Per-arm metrics
# --------------------------------------------------------------------------
def _arm_metrics(picks: list[dict]) -> dict:
    n = len(picks)
    if n == 0:
        return {"n": 0, "wr": 0.0, "pf": 0.0,
                "tq_n": 0, "tq_wr": 0.0, "tq_pf": 0.0}

    wins = sum(1 for p in picks if _is_win(p))
    wr = 100.0 * wins / n
    pf = _pf(picks)

    # Top quartile by score.
    ranked = sorted(picks, key=_score, reverse=True)
    tq_n = max(1, n // 4)
    tq = ranked[:tq_n]
    tq_wins = sum(1 for p in tq if _is_win(p))
    tq_wr = 100.0 * tq_wins / len(tq)
    tq_pf = _pf(tq)

    return {"n": n, "wr": wr, "pf": pf,
            "tq_n": len(tq), "tq_wr": tq_wr, "tq_pf": tq_pf}


def build_report(closed_path: Path, min_n: int = MIN_N) -> dict:
    with open(closed_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        picks = data
    elif isinstance(data, dict):
        # Common shapes: {"picks": [...]} or {"closed": [...]} or {<id>: {...}}.
        for k in ("picks", "closed", "closed_picks", "data"):
            if isinstance(data.get(k), list):
                picks = data[k]
                break
        else:
            vals = list(data.values())
            picks = vals[0] if (vals and isinstance(vals[0], list)) else \
                [v for v in vals if isinstance(v, dict)]
    else:
        picks = []

    closed = [p for p in picks if isinstance(p, dict) and _is_closed(p)]

    arms: dict[str, list[dict]] = {"A": [], "B": [], "UNTAGGED": []}
    for p in closed:
        arm = p.get("_overconfidence_arm")
        if arm in ("A", "B"):
            arms[arm].append(p)
        else:
            arms["UNTAGGED"].append(p)

    metrics = {a: _arm_metrics(arms[a]) for a in ("A", "B")}
    untagged_n = len(arms["UNTAGGED"])

    a, b = metrics["A"], metrics["B"]
    if a["tq_n"] < min_n or b["tq_n"] < min_n:
        verdict = "INSUFFICIENT-N"
        reason = (f"top-quartile n below threshold (min_n={min_n}): "
                  f"A tq_n={a['tq_n']}, B tq_n={b['tq_n']}")
        if a["n"] == 0 and b["n"] == 0:
            reason += " -- NO picks tagged yet (expected until the flag runs live)"
    else:
        delta = b["tq_wr"] - a["tq_wr"]
        if delta >= -ACCEPT_MARGIN_PP:
            verdict = "TREATMENT-OK"
            reason = (f"arm B top-quartile WR {b['tq_wr']:.1f}% >= "
                      f"arm A {a['tq_wr']:.1f}% - {ACCEPT_MARGIN_PP:.0f}pp "
                      f"(delta {delta:+.1f}pp)")
        else:
            verdict = "REGRESSION"
            reason = (f"arm B top-quartile WR {b['tq_wr']:.1f}% < "
                      f"arm A {a['tq_wr']:.1f}% - {ACCEPT_MARGIN_PP:.0f}pp "
                      f"(delta {delta:+.1f}pp)")

    return {
        "metrics": metrics,
        "untagged_n": untagged_n,
        "verdict": verdict,
        "reason": reason,
        "min_n": min_n,
    }


def _fmt_pf(pf: float) -> str:
    return "inf" if pf == float("inf") else f"{pf:.2f}"


def print_report(rep: dict) -> None:
    a, b = rep["metrics"]["A"], rep["metrics"]["B"]
    print()
    print("=" * 62)
    print(" OVERCONFIDENCE-DECAY A/B REPORT (A2)")
    print("=" * 62)
    print(f"{'metric':<24}{'arm A (control)':>18}{'arm B (decay)':>18}")
    print("-" * 62)
    print(f"{'n (closed)':<24}{a['n']:>18}{b['n']:>18}")
    print(f"{'WR %':<24}{a['wr']:>18.1f}{b['wr']:>18.1f}")
    print(f"{'PF':<24}{_fmt_pf(a['pf']):>18}{_fmt_pf(b['pf']):>18}")
    print(f"{'top-quartile n':<24}{a['tq_n']:>18}{b['tq_n']:>18}")
    print(f"{'top-quartile WR %':<24}{a['tq_wr']:>18.1f}{b['tq_wr']:>18.1f}")
    print(f"{'top-quartile PF':<24}{_fmt_pf(a['tq_pf']):>18}{_fmt_pf(b['tq_pf']):>18}")
    print("-" * 62)
    if rep["untagged_n"]:
        print(f"untagged closed picks (no _overconfidence_arm): {rep['untagged_n']}")
        print("  -> run pipeline with OVERCONFIDENCE_DECAY=1 to tag new picks")
    print(f"VERDICT: {rep['verdict']}")
    print(f"  {rep['reason']}")
    print("=" * 62)
    print()


# --------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------
def _selftest() -> int:
    failures = []

    sample_ids = [f"strat::SYM{i}::2026-05-17_{i:04d}" for i in range(2000)]

    # 1. Deterministic: same key -> same bucket every call.
    first = {pid: overconf_ab_bucket(pid) for pid in sample_ids}
    for pid in sample_ids:
        if overconf_ab_bucket(pid) != first[pid]:
            failures.append(f"non-deterministic bucket for {pid}")
            break
    else:
        print("PASS  bucketing is deterministic (2000 keys x2)")

    # 2. Buckets are only 'A' or 'B'.
    if set(first.values()) <= {"A", "B"}:
        print("PASS  buckets are exactly {A, B}")
    else:
        failures.append(f"unexpected bucket values: {set(first.values())}")

    # 3. ~50/50 split (allow 45-55%).
    b_count = sum(1 for v in first.values() if v == "B")
    b_pct = 100.0 * b_count / len(sample_ids)
    if 45.0 <= b_pct <= 55.0:
        print(f"PASS  bucket split ~50/50 (B = {b_pct:.1f}%)")
    else:
        failures.append(f"bucket split skewed: B={b_pct:.1f}%")

    # 4. Empty key -> control arm 'A'.
    if overconf_ab_bucket("") == "A":
        print("PASS  empty key falls to control arm A")
    else:
        failures.append("empty key did not map to arm A")

    # 5. id-less pick falls back to symbol+timestamp key.
    p_noid = {"symbol": "BTCUSDT", "timestamp": "2026-05-17T12:00:00Z"}
    if overconf_ab_key(p_noid) == "BTCUSDT|2026-05-17T12:00:00Z":
        print("PASS  id-less pick keys on symbol+timestamp")
    else:
        failures.append(f"id-less key wrong: {overconf_ab_key(p_noid)!r}")

    # 6. Matches score_booster bucketing exactly.
    try:
        sys.path.insert(0, str(_REPO_ROOT))
        from alpha_engine.score_booster import (
            _overconf_ab_bucket as _booster_bucket,
            _overconf_ab_key as _booster_key,
        )
        mismatch = [pid for pid in sample_ids[:500]
                    if _booster_bucket(pid) != overconf_ab_bucket(pid)]
        key_ok = _booster_key({"id": "X"}) == overconf_ab_key({"id": "X"}) and \
            _booster_key(p_noid) == overconf_ab_key(p_noid)
        if not mismatch and key_ok:
            print("PASS  bucketing/keying matches score_booster")
        else:
            failures.append(
                f"mismatch vs score_booster: {len(mismatch)} ids, key_ok={key_ok}")
    except Exception as exc:  # pragma: no cover
        failures.append(f"could not import score_booster: {exc}")

    # 7. score_booster stamps _overconfidence_arm; modes 1 / 0 behave correctly.
    try:
        from alpha_engine.score_booster import _apply_overconfidence_decay
        b_id = next(pid for pid in sample_ids if overconf_ab_bucket(pid) == "B")
        a_id = next(pid for pid in sample_ids if overconf_ab_bucket(pid) == "A")

        # Mode 1 (default A/B): stamp both, decay only B.
        os.environ["OVERCONFIDENCE_DECAY"] = "1"
        pb = {"id": b_id, "score": 95.0}
        pa = {"id": a_id, "score": 95.0}
        adj_b = _apply_overconfidence_decay(pb)
        adj_a = _apply_overconfidence_decay(pa)
        if pb.get("_overconfidence_arm") != "B" or pa.get("_overconfidence_arm") != "A":
            failures.append("mode 1: arm not stamped correctly")
        elif adj_b >= 0 or adj_a != 0:
            failures.append(
                f"mode 1: expected B decayed / A untouched, got B={adj_b} A={adj_a}")

        # Mode 0 (kill-switch): no stamp, no decay.
        os.environ["OVERCONFIDENCE_DECAY"] = "0"
        pb2 = {"id": b_id, "score": 95.0}
        pa2 = {"id": a_id, "score": 95.0}
        adj_b2 = _apply_overconfidence_decay(pb2)
        adj_a2 = _apply_overconfidence_decay(pa2)
        if adj_b2 != 0 or adj_a2 != 0:
            failures.append(f"mode 0: expected no decay, got B={adj_b2} A={adj_a2}")
        elif "_overconfidence_arm" in pb2 or "_overconfidence_arm" in pa2:
            failures.append("mode 0: kill-switch should not stamp an arm")

        if not any("mode" in f for f in failures):
            print("PASS  score_booster stamps _overconfidence_arm; "
                  "modes 1/0 behave correctly")
    except Exception as exc:  # pragma: no cover
        failures.append(f"booster stamp test failed: {exc}")
    finally:
        os.environ.pop("OVERCONFIDENCE_DECAY", None)

    print()
    if failures:
        for f in failures:
            print(f"FAIL  {f}")
        print(f"\n{len(failures)} self-test failure(s)")
        return 1
    print("ALL SELF-TESTS PASSED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Overconfidence-decay A/B report")
    ap.add_argument("--closed", type=Path, default=DEFAULT_CLOSED,
                    help="path to closed_picks.json")
    ap.add_argument("--min-n", type=int, default=MIN_N,
                    help="per-arm top-quartile n below which verdict is INSUFFICIENT-N")
    ap.add_argument("--selftest", action="store_true",
                    help="run the bucketing + arm-tagging self-test and exit")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    if not args.closed.exists():
        print(f"ERROR: closed picks file not found: {args.closed}", file=sys.stderr)
        print("  (no closed picks on disk yet — verdict would be INSUFFICIENT-N, n=0)",
              file=sys.stderr)
        return 2

    rep = build_report(args.closed, min_n=args.min_n)
    print_report(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
