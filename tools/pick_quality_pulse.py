#!/usr/bin/env python3
"""10m loop helper: snapshot best picks + class health without heavy scanners.

Writes: reports/pick_quality_pulse_latest.json
Does NOT run production_scanner or smart_picks_engine.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# EAGLE2 §11 — concentration / resolver alert thresholds
HHI_CLASS_YELLOW = 0.15
HHI_CLASS_RED = 0.25
HHI_BOOK_RED = 0.25
MR_SOURCE_SHARE_RED = 0.40
FOREX_WR_PF_DIVERGE_WR = 0.55
FOREX_WR_PF_DIVERGE_PF = 0.60


def _hhi(shares: list[float]) -> float:
    return sum(s * s for s in shares if s > 0)


def _load(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "money_ready": {},
        "lab_tier2": [],
        "best_confluence": [],
        "top_smart_equity": [],
        "top_smart_crypto": [],
        "hyro_top": [],
        "nvda_active": [],
    }

    mr = _load(ROOT / "audit_dashboard/data/money_ready_verdict.json")
    alerts: list[dict] = []
    if mr:
        classes = mr.get("classes", mr)
        for cls, v in classes.items():
            if not isinstance(v, dict):
                continue
            top_src = float(v.get("top_source_share") or 0)
            verdict = v.get("verdict")
            pf = float(v.get("pf") or 0)
            wr = float(v.get("wr") or 0)
            n = int(v.get("n_resolved") or v.get("n") or 0)
            hhi_proxy = top_src * top_src if top_src else 0.0
            level = "ok"
            if top_src >= MR_SOURCE_SHARE_RED or hhi_proxy >= HHI_CLASS_RED:
                level = "red"
            elif hhi_proxy >= HHI_CLASS_YELLOW:
                level = "yellow"
            out["money_ready"][cls] = {
                "verdict": verdict,
                "pf": pf,
                "wr": wr,
                "n": n,
                "top_source_share": top_src,
                "source_concentration_capped": v.get("source_concentration_capped"),
                "hhi_proxy_top_source": round(hhi_proxy, 4),
                "alert_level": level,
            }
            if level != "ok":
                alerts.append({
                    "class": cls,
                    "level": level,
                    "reason": f"top_source_share={top_src:.2f}",
                })
            if cls == "FOREX" and n >= 30 and wr >= FOREX_WR_PF_DIVERGE_WR and pf < FOREX_WR_PF_DIVERGE_PF:
                alerts.append({
                    "class": cls,
                    "level": "red",
                    "reason": "resolver_mislabel_suspect=high_WR_low_PF",
                })
    out["concentration_alerts"] = alerts

    lab = _load(ROOT / "verified_strategies/MULTI_CLASS_LAB_REPORT.json")
    if lab:
        out["lab_tier2"] = [
            {"class": r["asset_class"], "strategy": r["strategy"], "pf": r["stats"]["pf"]}
            for r in lab.get("tier2_pass", [])
        ]
        out["lab_best"] = {
            ac: {"strategy": r["strategy"], "pf": r["stats"]["pf"], "wr": r["stats"]["wr"]}
            for ac, r in lab.get("best_per_class", {}).items()
        }

    ap_path = ROOT / "alpha_engine/data/active_picks.json"
    if ap_path.exists() and ap_path.stat().st_size < 15_000_000:
        active = _load(ap_path) or []
        key_picks: dict = {}
        for p in active:
            k = (p.get("symbol"), p.get("direction") or p.get("signal_type"))
            key_picks.setdefault(k, []).append(p)
        conf = []
        for k, ps in key_picks.items():
            avg = sum(float(x.get("smart_score") or x.get("ml_composite") or 0) for x in ps) / len(ps)
            safe_n = sum(1 for x in ps if x.get("antigravity_safe"))
            conf.append({
                "symbol": k[0],
                "direction": k[1],
                "n_strategies": len(ps),
                "avg_smart_score": round(avg, 2),
                "antigravity_safe_count": safe_n,
                "strategies": list({x.get("strategy") for x in ps})[:6],
            })
        conf.sort(key=lambda x: (-x["n_strategies"], -x["avg_smart_score"]))
        out["best_confluence"] = conf[:15]

        eq = [
            p for p in active
            if (p.get("asset_class") or "").upper() in ("EQUITY", "ETF")
            or p.get("category") in ("stock", "etf")
        ]
        eq.sort(key=lambda x: -(float(x.get("smart_score") or x.get("ml_composite") or 0)))
        out["top_smart_equity"] = [
            {
                "symbol": p.get("symbol"),
                "strategy": p.get("strategy"),
                "direction": p.get("direction", p.get("signal_type")),
                "score": p.get("smart_score", p.get("ml_composite")),
                "safe": p.get("antigravity_safe"),
            }
            for p in eq[:10]
        ]

        cr = [
            p for p in active
            if (p.get("asset_class") or "").upper() == "CRYPTO" or "USDT" in str(p.get("symbol", ""))
        ]
        cr.sort(key=lambda x: -(float(x.get("smart_score") or x.get("ml_composite") or 0)))
        out["top_smart_crypto"] = [
            {
                "symbol": p.get("symbol"),
                "strategy": p.get("strategy"),
                "direction": p.get("direction", p.get("signal_type")),
                "score": p.get("smart_score", p.get("ml_composite")),
                "safe": p.get("antigravity_safe"),
            }
            for p in cr[:10]
        ]

        out["nvda_active"] = [
            {
                "strategy": p.get("strategy"),
                "direction": p.get("direction", p.get("signal_type")),
                "score": p.get("smart_score", p.get("ml_composite")),
                "safe": p.get("antigravity_safe"),
            }
            for p in active
            if p.get("symbol") == "NVDA"
        ]

    hy = _load(ROOT / "audit_dashboard/data/hyrotrader_enhanced_picks.json")
    if hy:
        picks = hy.get("picks") or hy.get("enhanced_picks") or []
        ranked = sorted(
            [p for p in picks if isinstance(p, dict)],
            key=lambda x: -(float(x.get("enhanced_score") or x.get("rank") or 0)),
        )
        out["hyro_top"] = [
            {
                "symbol": p.get("symbol"),
                "side": p.get("side", p.get("direction")),
                "score": p.get("enhanced_score"),
                "label": p.get("label", "")[:60],
            }
            for p in ranked[:8]
        ]

    report_path = ROOT / "reports/pick_quality_pulse_latest.json"
    report_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()