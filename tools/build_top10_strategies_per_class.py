#!/usr/bin/env python3
"""Build TOP10_STRATEGIES_PER_ASSET_CLASS report from pf_registry + config.

Reads:
  - audit_dashboard/data/pf_registry.json (by_asset_class_strategy, class nets)
  - alpha_engine/config.py STRATEGY_FAMILIES (via import)
  - audit_dashboard/data/quarantine_manifest.json
  - alpha_engine/emitter_whitelist.py HARDCODED_TOXIC_PAIRS

Writes:
  - reports/TOP10_STRATEGIES_PER_ASSET_CLASS_<date>.md (default today UTC)
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / "audit_dashboard" / "data" / "pf_registry.json"
QUARANTINE = REPO / "audit_dashboard" / "data" / "quarantine_manifest.json"
CLASSES = ("CRYPTO", "EQUITY", "COMMODITY", "ETF", "FOREX", "BOND")
MIN_N_RANK = 5  # prefer n>=5 for ranking; pad with lower n if <10 rows


def _load_families() -> dict[str, str]:
    try:
        from alpha_engine.config import STRATEGY_FAMILIES  # noqa: WPS433

        return dict(STRATEGY_FAMILIES)
    except Exception:
        return {}


def _load_toxic() -> set[tuple[str, str]]:
    try:
        from alpha_engine.emitter_whitelist import HARDCODED_TOXIC_PAIRS  # noqa: WPS433

        return set(HARDCODED_TOXIC_PAIRS)
    except Exception:
        return set()


def _blocked_pairs(q: dict) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for item in q.get("blocked_asset_strategy_pairs") or []:
        ac = str(item.get("asset_class", "")).upper()
        st = str(item.get("strategy", "")).strip()
        if ac and st:
            out.add((ac, st))
    return out


def _fmt_pf(pf: object) -> str:
    if pf is None:
        return "—"
    try:
        v = float(pf)
        if v != v:
            return "—"
        return f"{v:.3f}"
    except (TypeError, ValueError):
        return "—"


def _rank_rows(rows: list[dict], toxic: set[tuple[str, str]], blocked: set[tuple[str, str]]) -> list[dict]:
    def score(r: dict) -> tuple:
        n = int(r.get("n") or 0)
        pf = r.get("profit_factor")
        try:
            pf_f = float(pf) if pf is not None else -1.0
        except (TypeError, ValueError):
            pf_f = -1.0
        return (pf_f, n)

    hi_n = [r for r in rows if int(r.get("n") or 0) >= MIN_N_RANK]
    pool = hi_n if len(hi_n) >= 10 else rows
    ranked = sorted(pool, key=score, reverse=True)[:10]
    out = []
    for i, r in enumerate(ranked, 1):
        ac = str(r.get("asset_class", "")).upper()
        st = str(r.get("strategy", ""))
        pair = (ac, st)
        flags = []
        if pair in toxic:
            flags.append("TOXIC_EMITTER")
        if pair in blocked:
            flags.append("QUARANTINE")
        out.append(
            {
                "rank": i,
                "strategy": st,
                "n": int(r.get("n") or 0),
                "wr_pct": r.get("win_rate_pct"),
                "pf": r.get("profit_factor"),
                "total_pnl_pct": r.get("total_pnl_pct"),
                "family": _load_families().get(st, "—"),
                "flags": ",".join(flags) if flags else "",
            }
        )
    return out


def build_report(out_path: Path) -> str:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    q = json.loads(QUARANTINE.read_text(encoding="utf-8")) if QUARANTINE.is_file() else {}
    toxic = _load_toxic()
    blocked = _blocked_pairs(q)
    families = _load_families()

    class_net = {r["asset_class"]: r for r in data.get("by_asset_class_policy_clean_net", [])}
    by_class: dict[str, list[dict]] = defaultdict(list)
    for r in data.get("by_asset_class_strategy", []):
        ac = str(r.get("asset_class", "")).upper()
        if ac in CLASSES:
            by_class[ac].append(r)

    gen = data.get("generated_utc", "?")
    lines = [
        f"# Top 10 strategies per asset class (pf_registry)",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')}  ",
        f"**Registry snapshot:** `{gen}`  ",
        f"**Canonical view:** `{data.get('canonical_view', 'by_asset_class_policy_clean_net')}`  ",
        f"**Ranking:** `by_asset_class_strategy` sorted by profit_factor (prefer n≥{MIN_N_RANK}).",
        "",
        "## Codebase configuration spec (for meta-prompts / debate)",
        "",
        "| Knob | Value / path |",
        "|------|----------------|",
        "| PF source | `audit_dashboard/data/pf_registry.json` |",
        "| Dedup key | strategy(source_system\\|strategy), symbol, direction, trade_date, entry~2p |",
        "| Emitter gate | `alpha_engine/emitter_whitelist.py` — `EMITTER_REGISTRY_GATE=1`, enforce off by default |",
        "| Hardcoded toxic pairs | quan_engine/CRYPTO; cta_replicator/COMMODITY; multi_asset_copytrader/FOREX,EQUITY |",
        "| Harness | `tools/edge_stability_harness.py` — 11/11 daily-bar causal **KILLED** |",
        "| Quarantine | `audit_dashboard/data/quarantine_manifest.json` size_caps + blocked pairs |",
        "| Strategy families | `alpha_engine/config.py` → `STRATEGY_FAMILIES` |",
        "",
        "### Class size caps (quarantine_manifest)",
        "",
    ]
    for ac in CLASSES:
        cap = (q.get("size_caps") or {}).get(ac, {})
        if isinstance(cap, dict):
            lines.append(f"- **{ac}:** max_risk {cap.get('max_pct_of_risk', '?')}% — {cap.get('rationale', '')[:120]}")
        else:
            lines.append(f"- **{ac}:** {cap}")
    lines.append("")

    for ac in CLASSES:
        net = class_net.get(ac, {})
        lines.extend(
            [
                f"## {ac}",
                "",
                f"**Class policy_clean_net:** n={net.get('n', '?')} | "
                f"PF={_fmt_pf(net.get('profit_factor'))} | WR={net.get('win_rate_pct', '?')}% | "
                f"MDD={net.get('max_drawdown_pct', '—')}",
                "",
                "| Rank | Strategy | n | WR% | PF | Family | Flags |",
                "|------|----------|---|-----|-----|--------|-------|",
            ]
        )
        ranked = _rank_rows(by_class.get(ac, []), toxic, blocked)
        if not ranked:
            lines.append("| — | *(no strategies in registry slice)* | — | — | — | — | — |")
        else:
            for row in ranked:
                wr = row["wr_pct"]
                wr_s = f"{wr:.1f}" if isinstance(wr, (int, float)) else "—"
                lines.append(
                    f"| {row['rank']} | `{row['strategy']}` | {row['n']} | {wr_s} | "
                    f"{_fmt_pf(row['pf'])} | {row['family']} | {row['flags'] or '—'} |"
                )
        lines.append("")
        # Wire hints: top non-toxic with n>=20
        good = [
            r
            for r in ranked
            if "TOXIC" not in r["flags"] and r["n"] >= 20 and (row_pf := r["pf"]) is not None
        ]
        try:
            good = [r for r in ranked if "TOXIC" not in r["flags"] and r["n"] >= 20 and float(r["pf"] or 0) >= 1.2]
        except (TypeError, ValueError):
            good = []
        if good:
            lines.append(f"**Rescue candidates ({ac}):** " + ", ".join(f"`{g['strategy']}`" for g in good[:3]))
        else:
            lines.append(f"**Rescue candidates ({ac}):** none pass PF≥1.2 n≥20 non-toxic in this slice — mutation or new hypothesis required.")
        lines.append("")

    lines.extend(
        [
            "## Meta-prompt usage",
            "",
            "Feed this file to:",
            "- `docs/swarm_prompts/META_DEBATE_PER_CLASS_v1.md` (cloud: argue rescue vs kill per rank)",
            "- `docs/swarm_prompts/STRATEGY_HARVEST_EXECUTE_v1.md` (local: P0 wire plan)",
            "",
            "Regenerate: `python tools/build_top10_strategies_per_class.py`",
            "",
        ]
    )
    text = "\n".join(lines)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return str(out_path)


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = REPO / "reports" / f"TOP10_STRATEGIES_PER_ASSET_CLASS_{stamp}.md"
    path = build_report(out)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
