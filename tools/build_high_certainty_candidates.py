import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COPY_DB = ROOT / "copy_trader_intel" / "data" / "copytrader_database.json"
PM_PICKS = ROOT / "alpha_engine" / "data" / "prediction_market_picks.json"
OUT_JSON = ROOT / "audit_dashboard" / "data" / "copy_pm_high_certainty_candidates.json"


def _safe_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    copy_db = _safe_json(COPY_DB) or {}
    pm = _safe_json(PM_PICKS) or {}

    copy_candidates = []
    for t in copy_db.get("crypto_traders", []):
        wr = float(t.get("win_rate", 0) or 0)
        trades = int(t.get("total_trades", 0) or 0)
        pnl = float(t.get("total_realized_pnl", 0) or 0)
        score = (wr * 0.5) + (min(trades, 1500) / 1500 * 30) + (15 if pnl > 0 else 0)
        if wr >= 58 and trades >= 120 and pnl > 0:
            copy_candidates.append(
                {
                    "platform": t.get("platform"),
                    "trader_id": t.get("trader_id"),
                    "name": t.get("name"),
                    "win_rate": wr,
                    "trades": trades,
                    "total_realized_pnl": pnl,
                    "quality_score": round(score, 2),
                    "why": "High sample, positive realized PnL, stable WR",
                }
            )

    copy_candidates.sort(key=lambda x: (x["quality_score"], x["win_rate"], x["trades"]), reverse=True)

    pm_candidates = []
    for p in pm.get("picks", []):
        conf = float(p.get("confidence", 0) or 0)
        src = int(p.get("source_count", 0) or 0)
        direction = p.get("direction")
        symbol = p.get("symbol")
        score = conf * 100 + src * 5
        if conf >= 0.80 and src >= 2:
            pm_candidates.append(
                {
                    "symbol": symbol,
                    "direction": direction,
                    "confidence": conf,
                    "source_count": src,
                    "consensus_sources": p.get("source_systems") or p.get("sources") or [],
                    "reason": p.get("reason", ""),
                    "quality_score": round(score, 2),
                }
            )

    pm_candidates.sort(key=lambda x: x["quality_score"], reverse=True)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "copy_candidates": copy_candidates[:25],
        "prediction_market_candidates": pm_candidates[:25],
        "summary": {
            "copy_candidates": len(copy_candidates),
            "prediction_market_candidates": len(pm_candidates),
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {OUT_JSON}")
    print(f"copy={len(copy_candidates)} pm={len(pm_candidates)}")


if __name__ == "__main__":
    main()
