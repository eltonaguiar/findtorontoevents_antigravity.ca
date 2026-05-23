import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPANSION_JSON = ROOT / "audit_dashboard" / "data" / "strategy_expansion_backtests.json"
OUT_CANDIDATES = ROOT / "alpha_engine" / "data" / "expansion_forward_candidates.json"
OUT_RANKED = ROOT / "alpha_engine" / "data" / "expansion_promotion_ranked.json"


def _load_json(path: Path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _family_to_strategy(family: str) -> str:
    if "lightgbm" in family:
        return "ml_enhanced_lightgbm_transfer"
    return "ml_enhanced_ensemble_transfer"


def main():
    d = _load_json(EXPANSION_JSON)
    rows = d.get("expansion_backtests", [])

    # Expansion score favors positive expectancy + robust payoff (PF) + sample size.
    scored = []
    for r in rows:
        trades = int(r.get("trades", 0) or 0)
        wr = float(r.get("wr", 0) or 0)
        pf = float(r.get("pf", 0) or 0)
        avg = float(r.get("avg", 0) or 0)
        if trades < 40:
            continue
        if pf < 1.25 or avg <= 0:
            continue

        score = (pf * 30.0) + (avg * 20.0) + min(trades, 120) * 0.2 + (wr * 0.1)
        scored.append(
            {
                **r,
                "strategy": _family_to_strategy(r.get("family", "")),
                "expansion_score": round(score, 3),
            }
        )

    scored.sort(key=lambda x: x["expansion_score"], reverse=True)
    top6 = scored[:6]

    candidates = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selection_rule": {
            "min_trades": 40,
            "min_pf": 1.25,
            "min_avg_pnl": 0,
            "top_n": 6,
        },
        "candidates": [],
    }

    for i, x in enumerate(top6, 1):
        direction_bias = "LONG_BIAS" if x.get("avg", 0) > 0 else "NEUTRAL"
        candidates["candidates"].append(
            {
                "rank": i,
                "strategy": x["strategy"],
                "source_family": x.get("family"),
                "asset_class": x.get("asset_class"),
                "symbol": x.get("symbol"),
                "direction_bias": direction_bias,
                "expected_metrics": {
                    "trades": x.get("trades"),
                    "win_rate_pct": x.get("wr"),
                    "profit_factor": x.get("pf"),
                    "avg_pnl_pct": x.get("avg"),
                    "total_pnl_pct": x.get("total"),
                },
                "expansion_score": x.get("expansion_score"),
                "status": "FORWARD_TEST_CANDIDATE",
                "notes": "Auto-selected from expansion sweep; route through forward validator before promotion.",
            }
        )

    ranked = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entries": [],
    }

    for c in candidates["candidates"]:
        m = c["expected_metrics"]
        # Promotion pre-rank: soft approximation before actual forward data arrives.
        pass_prefilter = (
            (m.get("trades", 0) or 0) >= 40
            and (m.get("profit_factor", 0) or 0) >= 1.30
            and (m.get("avg_pnl_pct", 0) or 0) > 0
        )
        ranked["entries"].append(
            {
                "strategy": c["strategy"],
                "symbol": c["symbol"],
                "asset_class": c["asset_class"],
                "expansion_score": c["expansion_score"],
                "pre_forward_rank": "HIGH" if pass_prefilter else "MEDIUM",
                "pre_forward_pass": pass_prefilter,
                "required_next_checks": [
                    "forward_validator.passes_forward_gate",
                    "walkforward_validator.oos_wr_stability",
                    "promotion_gate.deflated_sharpe",
                ],
            }
        )

    OUT_CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
    OUT_CANDIDATES.write_text(json.dumps(candidates, indent=2), encoding="utf-8")
    OUT_RANKED.write_text(json.dumps(ranked, indent=2), encoding="utf-8")

    print(f"Wrote {OUT_CANDIDATES}")
    print(f"Wrote {OUT_RANKED}")
    print(f"top_candidates={len(candidates['candidates'])}")


if __name__ == "__main__":
    main()
