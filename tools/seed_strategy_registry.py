"""Seed trading/data/strategy_registry.json from the audit3 pod manifest.

`trading/strategy_registry.py` declares `trading/data/strategy_registry.json` as
the institutional registry but the file was never materialized, so there was no
canonical per-strategy status source. This script registers one record per
strategy named in `reports/audit3_confirmatory.json`, at the honest governance
state implied by the pod status:

* pre_registered / observe pod strategy -> INCUBATOR / pending_review
* post_hoc or declined pod strategy     -> KILL_LIST / eliminated

It is idempotent: `Registry.register` is a no-op for an existing id, so running
it again does not overwrite a human's later promotion/demotion.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from trading.strategy_registry import StrategyRegistry  # noqa: E402

MANIFEST = REPO / "reports" / "audit3_confirmatory.json"

# Map a strategy string to the registry's coarse family vocabulary.
_FAMILY_HINTS = (
    ("vwap", "mean_reversion"),
    ("bollinger", "mean_reversion"),
    ("rsi", "mean_reversion"),
    ("faber", "momentum"),
    ("breakout", "momentum"),
    ("momentum", "momentum"),
    ("mom", "momentum"),
    ("carry", "funding_carry"),
    ("roll_yield", "funding_carry"),
    ("funding", "funding_carry"),
    ("regime", "regime_adaptive"),
)


def _family(strategy: str) -> str:
    s = strategy.casefold()
    for hint, fam in _FAMILY_HINTS:
        if hint in s:
            return fam
    return "unknown"


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    reg = StrategyRegistry()
    added = 0
    for pod in manifest.get("pods") or []:
        status = str(pod.get("status") or "").strip().lower()
        if status in {"post_hoc", "declined"}:
            tier, gov = "KILL_LIST", "eliminated"
        elif status in {"pre_registered", "observe"}:
            tier, gov = "INCUBATOR", "pending_review"
        else:
            continue
        for strategy in pod.get("strategies") or []:
            existing = reg.get_strategy(strategy)
            if existing:
                continue
            reg.register(
                strategy_id=str(strategy),
                name=str(strategy),
                family=_family(str(strategy)),
                params={"pod": pod.get("id"), "pod_status": status,
                        "asset_classes": pod.get("asset_classes"),
                        "directions": pod.get("directions")},
                tier=tier,
                status=gov,
            )
            added += 1
    reg._save()
    print(f"registered {added} new strateg(y/ies); "
          f"total={len(getattr(reg, '_data', {}).get('strategies', {}))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
