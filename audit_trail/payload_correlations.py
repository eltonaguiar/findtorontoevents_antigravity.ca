"""
Payload Correlation Analysis — recomputes Spearman correlations after each payload build.

Reads dashboard_payload.json and computes:
  - Spearman rank correlation of key fields vs pnl_pct (closed crypto picks)
  - Win rate by score bucket, trust tier, regime alignment, HTF alignment
  - System-level conflict accuracy

Run:  python -m audit_trail.payload_correlations
Output: audit_trail/data/correlation_report.json  (consumed by dashboard)
"""

import json
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
PAYLOAD_PATH = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
OUTPUT_PATH = ROOT / "audit_trail" / "data" / "correlation_report.json"


def _float(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default


def _spearman(xs, ys):
    """Spearman rank correlation (no scipy dependency)."""
    n = len(xs)
    if n < 5:
        return None

    def _rank(vals):
        indexed = sorted(enumerate(vals), key=lambda t: t[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx = _rank(xs)
    ry = _rank(ys)
    d_sq = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return round(1 - (6 * d_sq) / (n * (n * n - 1)), 4)


def _wr(picks):
    """Win rate from a list of picks with pnl_pct."""
    if not picks:
        return None
    wins = sum(1 for p in picks if _float(p.get("pnl_pct")) > 0)
    return round(wins / len(picks) * 100, 1)


def analyze(payload_path=None):
    path = Path(payload_path) if payload_path else PAYLOAD_PATH
    if not path.exists():
        log.error("Payload not found: %s", path)
        return None

    data = json.loads(path.read_text(encoding="utf-8"))
    closed = data.get("picks", {}).get("recent_closed", [])

    # Filter to crypto with valid PnL
    crypto = [
        p for p in closed
        if (p.get("asset_class") or "").upper() == "CRYPTO"
        and p.get("pnl_pct") is not None
        and p.get("symbol", "").upper().endswith("USDT")
    ]

    if len(crypto) < 10:
        log.warning("Only %d closed crypto picks — too few for meaningful analysis", len(crypto))
        return {"error": "insufficient_data", "count": len(crypto)}

    pnls = [_float(p.get("pnl_pct")) for p in crypto]

    # ── Spearman correlations vs pnl_pct ──
    fields = {
        "trust_score": lambda p: _float(p.get("trust_score")),
        "score": lambda p: _float(p.get("score")),
        "confidence": lambda p: _float(p.get("confidence")),
        "strat_fwd_wr": lambda p: _float(p.get("strat_fwd_wr")),
        "forward_wr": lambda p: _float(p.get("forward_wr")),
        "agreement_count": lambda p: _float(p.get("agreement_count")),
        "ml_composite_score": lambda p: _float(p.get("ml_composite_score")),
        "rr_ratio": lambda p: _float(p.get("rr_ratio")),
    }

    correlations = {}
    for name, extractor in fields.items():
        vals = [extractor(p) for p in crypto]
        # Only compute if we have non-zero variance
        valid = [(v, pnl) for v, pnl in zip(vals, pnls) if v != 0]
        if len(valid) >= 10:
            xs, ys = zip(*valid)
            correlations[name] = {
                "spearman": _spearman(list(xs), list(ys)),
                "n": len(valid),
            }

    # ── Win rate by score bucket ──
    score_buckets = {}
    for lo, hi in [(0, 25), (25, 40), (40, 55), (55, 70), (70, 85), (85, 101)]:
        label = f"{lo}-{hi-1}"
        bucket = [p for p in crypto if lo <= _float(p.get("score")) < hi]
        if bucket:
            score_buckets[label] = {
                "wr": _wr(bucket),
                "n": len(bucket),
                "avg_pnl": round(sum(_float(p.get("pnl_pct")) for p in bucket) / len(bucket), 2),
            }

    # ── Win rate by trust tier ──
    trust_tiers = {}
    for tier in ["PROVEN", "VALIDATED", "PROBATION", "SANDBOX", "UNPROVEN", "DEMOTED"]:
        group = [p for p in crypto if (p.get("trust_tier") or "").upper() == tier]
        if group:
            trust_tiers[tier] = {
                "wr": _wr(group),
                "n": len(group),
                "avg_pnl": round(sum(_float(p.get("pnl_pct")) for p in group) / len(group), 2),
            }

    # ── HTF alignment vs outcome ──
    htf_stats = {"aligned": [], "misaligned": [], "unknown": []}
    for p in crypto:
        htf = (p.get("htf_bias") or "").upper()
        direction = (p.get("direction") or "").upper()
        if not htf or htf == "NEUTRAL":
            htf_stats["unknown"].append(p)
        elif (direction == "LONG" and htf == "BULL") or (direction == "SHORT" and htf == "BEAR"):
            htf_stats["aligned"].append(p)
        else:
            htf_stats["misaligned"].append(p)

    htf_result = {}
    for key, group in htf_stats.items():
        if group:
            htf_result[key] = {
                "wr": _wr(group),
                "n": len(group),
                "avg_pnl": round(sum(_float(p.get("pnl_pct")) for p in group) / len(group), 2),
            }

    # ── Regime alignment vs outcome ──
    regime_stats = {"aligned": [], "misaligned": [], "unknown": []}
    for p in crypto:
        regime = (p.get("regime_at_entry") or p.get("regime") or "").upper()
        direction = (p.get("direction") or "").upper()
        if not regime or "CHOP" in regime or "UNKNOWN" in regime:
            regime_stats["unknown"].append(p)
        elif (direction == "LONG" and "BULL" in regime) or (direction == "SHORT" and "BEAR" in regime):
            regime_stats["aligned"].append(p)
        else:
            regime_stats["misaligned"].append(p)

    regime_result = {}
    for key, group in regime_stats.items():
        if group:
            regime_result[key] = {
                "wr": _wr(group),
                "n": len(group),
                "avg_pnl": round(sum(_float(p.get("pnl_pct")) for p in group) / len(group), 2),
            }

    # ── System-level W/L on conflicts ──
    by_symbol = {}
    for p in crypto:
        sym = p.get("symbol", "")
        by_symbol.setdefault(sym, []).append(p)

    system_conflict_accuracy = {}
    for sym, group in by_symbol.items():
        dirs = set((p.get("direction") or "").upper() for p in group)
        if len(dirs) < 2:
            continue
        for p in group:
            sys = p.get("source_system", "unknown")
            if sys not in system_conflict_accuracy:
                system_conflict_accuracy[sys] = {"wins": 0, "losses": 0, "total_pnl": 0}
            pnl = _float(p.get("pnl_pct"))
            if pnl > 0:
                system_conflict_accuracy[sys]["wins"] += 1
            else:
                system_conflict_accuracy[sys]["losses"] += 1
            system_conflict_accuracy[sys]["total_pnl"] = round(
                system_conflict_accuracy[sys]["total_pnl"] + pnl, 2
            )

    # Add WR to conflict accuracy
    for sys, stats in system_conflict_accuracy.items():
        total = stats["wins"] + stats["losses"]
        stats["wr"] = round(stats["wins"] / total * 100, 1) if total > 0 else 0
        stats["n"] = total

    # Sort by WR desc
    system_conflict_accuracy = dict(
        sorted(system_conflict_accuracy.items(), key=lambda x: -x[1].get("wr", 0))
    )

    # ── Agreement count vs WR ──
    agreement_wr = {}
    for ac in sorted(set(int(_float(p.get("agreement_count"))) for p in crypto)):
        group = [p for p in crypto if int(_float(p.get("agreement_count"))) == ac]
        if len(group) >= 3:
            agreement_wr[str(ac)] = {
                "wr": _wr(group),
                "n": len(group),
                "avg_pnl": round(sum(_float(p.get("pnl_pct")) for p in group) / len(group), 2),
            }

    report = {
        "generated_from": str(path.name),
        "total_closed_crypto": len(crypto),
        "spearman_vs_pnl": correlations,
        "score_buckets": score_buckets,
        "trust_tier_performance": trust_tiers,
        "htf_alignment": htf_result,
        "regime_alignment": regime_result,
        "agreement_count_wr": agreement_wr,
        "system_conflict_accuracy": dict(list(system_conflict_accuracy.items())[:30]),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log.info("Correlation report written to %s (%d picks analyzed)", OUTPUT_PATH, len(crypto))

    # Print summary
    print(f"\n{'='*60}")
    print(f"Payload Correlation Report — {len(crypto)} closed crypto picks")
    print(f"{'='*60}")

    print("\nSpearman vs PnL:")
    for name, data in sorted(correlations.items(), key=lambda x: abs(x[1].get("spearman") or 0), reverse=True):
        r = data["spearman"]
        print(f"  {name:25s}  r={r:+.4f}  (n={data['n']})")

    print("\nHTF Alignment:")
    for key, data in htf_result.items():
        print(f"  {key:15s}  WR={data['wr']:5.1f}%  avg_pnl={data['avg_pnl']:+.2f}%  (n={data['n']})")

    print("\nRegime Alignment:")
    for key, data in regime_result.items():
        print(f"  {key:15s}  WR={data['wr']:5.1f}%  avg_pnl={data['avg_pnl']:+.2f}%  (n={data['n']})")

    print("\nTop 10 Systems in Conflicts (by WR):")
    for sys, stats in list(system_conflict_accuracy.items())[:10]:
        print(f"  {sys:30s}  WR={stats['wr']:5.1f}%  PnL={stats['total_pnl']:+.1f}%  (n={stats['n']})")

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    path = sys.argv[1] if len(sys.argv) > 1 else None
    analyze(path)
