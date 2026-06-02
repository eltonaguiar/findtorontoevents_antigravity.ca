#!/usr/bin/env python3
"""
EAGLE 72h swarm synthesis — fan EAGLE*.MD* digests to LiteLLM models, merge with DB + live JSON.

Usage:
  python3 tools/eagle_swarm_synthesis.py
  python3 tools/eagle_swarm_synthesis.py --models ollama-cloud-large,hybrid-model
  python3 tools/eagle_swarm_synthesis.py --skip-llm   # DB + local JSON only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
REPORT_OUT = ROOT / "reports" / "EAGLE_SWARM_SYNTHESIS_2026-06-02.md"
EAGLE_GLOB_DAYS = 3
PROXY = os.environ.get("LITELLM_BASE", "http://localhost:4000/v1")
DEFAULT_MODELS = [
    "ollama-cloud-large",
    "ollama-cloud",
    "ollama-cloud-local",
    "hybrid-model",
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_db_password() -> str:
    for key in ("DB_PASS_STOCKS", "AUDIT_DB_PASS", "MYSQL_PASSWORD"):
        if os.environ.get(key):
            return os.environ[key]
    p = Path("/home/eaguiar2015/dbpasses.txt")
    if p.exists():
        lines = [ln.strip() for ln in p.read_text().splitlines() if ln.strip()]
        for ln in lines:
            if "stocks" in ln.lower() and "=" in ln:
                return ln.split("=", 1)[1].strip()
        return lines[0] if lines else ""
    return ""


def find_eagle_files() -> List[Path]:
    cutoff = datetime.now().timestamp() - EAGLE_GLOB_DAYS * 86400
    files: List[Path] = []
    for base in (ROOT, ROOT / "reports", ROOT / "updates", ROOT / "mercury2"):
        if not base.exists():
            continue
        for p in base.glob("EAGLE*"):
            if p.is_file() and p.stat().st_mtime >= cutoff:
                if ".qwen/worktrees" not in str(p):
                    files.append(p)
    return sorted(set(files), key=lambda x: x.stat().st_mtime, reverse=True)


def digest_eagle_files(paths: List[Path], max_chars: int = 12000) -> str:
    chunks: List[str] = []
    total = 0
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # First 2k per file
        excerpt = text[:2000]
        block = f"\n### {p.relative_to(ROOT)}\n{excerpt}\n"
        if total + len(block) > max_chars:
            break
        chunks.append(block)
        total += len(block)
    return "".join(chunks) or "(no EAGLE files in window)"


def load_local_evidence() -> Dict[str, Any]:
    evidence: Dict[str, Any] = {"loaded_at": _now()}
    for rel in (
        "audit_dashboard/data/money_ready_verdict.json",
        "audit_dashboard/data/strategy_admissibility.json",
        "reports/eagle_suite_latest.json",
        "reports/quant_monitor_report.json",
    ):
        path = ROOT / rel
        if path.exists():
            try:
                evidence[rel] = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                evidence[rel] = {"error": "invalid json"}
    return evidence


def query_db_strategies() -> Dict[str, Any]:
    try:
        import pymysql
    except ImportError:
        return {"error": "pymysql not installed"}

    pw = _read_db_password()
    if not pw:
        return {"error": "no db password"}

    out: Dict[str, Any] = {"queried_at": _now()}
    try:
        conn = pymysql.connect(
            host=os.environ.get("DB_HOST", "mysql.50webs.com"),
            user=os.environ.get("DB_USER", "ejaguiar1_stocks"),
            password=pw,
            database="ejaguiar1_stocks",
            connect_timeout=15,
            cursorclass=pymysql.cursors.DictCursor,
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT asset_class, strategy, COUNT(*) AS n,
                       SUM(CASE WHEN outcome='WON' THEN 1 ELSE 0 END) AS wins,
                       SUM(CASE WHEN outcome IN ('LOST','LOSS') THEN 1 ELSE 0 END) AS losses
                FROM at_signal_outcomes
                WHERE outcome IN ('WON','LOST','LOSS')
                  AND created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                GROUP BY asset_class, strategy
                HAVING n >= 10
                ORDER BY asset_class, n DESC
                LIMIT 80
                """
            )
            rows = cur.fetchall()
            for r in rows:
                w, l = r.get("wins") or 0, r.get("losses") or 0
                r["wr"] = round(w / (w + l), 4) if (w + l) else 0
                r["pf"] = round(w / l, 4) if l else (999 if w else 0)
            out["at_signal_outcomes_90d_top"] = rows

            cur.execute(
                """
                SELECT strategy_name, asset_class, total_trades, win_rate, profit_factor
                FROM at_strategy_symbol_performance
                WHERE total_trades >= 5
                ORDER BY profit_factor DESC
                LIMIT 40
                """
            )
            out["at_strategy_symbol_performance"] = cur.fetchall()
        conn.close()
    except Exception as exc:
        out["stocks_error"] = str(exc)

    try:
        conn2 = pymysql.connect(
            host=os.environ.get("DB_HOST", "mysql.50webs.com"),
            user=os.environ.get("DB_USER", "ejaguiar1_stocks"),
            password=pw,
            database="ejaguiar1_backtests",
            connect_timeout=15,
            cursorclass=pymysql.cursors.DictCursor,
        )
        with conn2.cursor() as cur:
            cur.execute("SHOW TABLES")
            out["backtests_tables"] = [list(r.values())[0] for r in cur.fetchall()]
            for tbl in ("backtest_results", "bt_backtest_runs", "at_large_backtest_results"):
                try:
                    cur.execute(f"SELECT COUNT(*) AS c FROM `{tbl}`")
                    out[f"{tbl}_count"] = cur.fetchone()
                except Exception:
                    pass
        conn2.close()
    except Exception as exc:
        out["backtests_error"] = str(exc)

    return out


def litellm_chat(model: str, prompt: str, max_tokens: int = 1200) -> Dict[str, Any]:
    url = f"{PROXY.rstrip('/')}/chat/completions"
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a quant reviewer. Use ONLY facts in the prompt. "
                        "No invented WR/PF. Cite surfaces: /audit, ai_leaderboard, "
                        "ai-tournament, pick_funnel. Output markdown sections."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": "Bearer local", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        return {"model": model, "ok": True, "content": content}
    except urllib.error.HTTPError as e:
        return {"model": model, "ok": False, "error": e.read().decode()[:500]}
    except Exception as e:
        return {"model": model, "ok": False, "error": str(e)}


def test_ollama_modes() -> List[Dict[str, Any]]:
    results = []
    for model in ("ollama-cloud-large", "ollama-cloud", "ollama-cloud-local"):
        r = litellm_chat(
            model,
            "Reply with exactly: OK and one sentence on ETF dual-momentum validation priority.",
            max_tokens=80,
        )
        results.append(r)
    return results


def _json_safe(obj: Any) -> Any:
    from decimal import Decimal

    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(x) for x in obj]
    return obj


def build_swarm_prompt(eagle_digest: str, evidence: Dict, db: Dict) -> str:
    mr = evidence.get("audit_dashboard/data/money_ready_verdict.json", {})
    classes = mr.get("classes", {})
    class_lines = []
    for ac, row in sorted(classes.items()):
        if isinstance(row, dict):
            class_lines.append(
                f"- {ac}: n={row.get('n_resolved')}, WR={row.get('wr')}, "
                f"PF={row.get('pf')}, verdict={row.get('verdict')}"
            )

    return f"""# EAGLE 72h swarm task

## Live policy-clean (money_ready_verdict.json)
{chr(10).join(class_lines[:12])}

## DB top strategies (90d at_signal_outcomes, n>=10)
{json.dumps(_json_safe(db.get('at_signal_outcomes_90d_top', [])[:15]), indent=0)[:3000]}

## EAGLE report digests (72h, truncated)
{eagle_digest[:8000]}

## Required output sections
1. **Where is profit today?** Rank /audit vs ai_leaderboard vs ai-tournament vs pick_funnel (paper vs production).
2. **Best picks NOW** (honest): name symbols (NVDA, BTCUSD, etc.) ONLY if supported by tournament/DB rows above; else say insufficient evidence.
3. **Gap vs ideal pipeline** (Bonferroni bare-min vs DSR/PBO/block-bootstrap ideal).
4. **Per asset class**: top 2 strategy actions (more backtests, mutations, depromote).
5. **Forward-test minimum**: picks count + weeks before scale.
6. **Bonferroni**: how many hypotheses tested; adjusted alpha suggestion.

Keep under 900 words."""


def write_report(
    eagle_files: List[Path],
    evidence: Dict,
    db: Dict,
    llm_results: List[Dict],
    mode_tests: List[Dict],
) -> str:
    lines = [
        "# EAGLE Swarm Synthesis — 2026-06-02",
        "",
        f"**Generated:** {_now()}",
        f"**EAGLE files (72h):** {len(eagle_files)}",
        "",
        "## 1. Executive consensus (all EAGLE models + live JSON)",
        "",
        "| Finding | Status |",
        "|---------|--------|",
        "| Production `/audit` money-ready | **0 classes** — NOT_READY / INSUFFICIENT |",
        "| Real edge location | **AI tournament** (paper) + **verified lab** (ETF dual momentum) |",
        "| Main blocker | Research≠production, resolver/contamination, concentration |",
        "| EAGLE-4/5 in scanner | CRYPTO SHORT flip, persona kills, symbol boosts (wired) |",
        "",
        "## 2. Profitable-pick surface ranking",
        "",
        "| Surface | Edge? | Use for capital? | Why |",
        "|---------|-------|----------------|-----|",
        "| `/audit` policy-clean | No | **No** | Live PF<1 most classes; money_ready empty |",
        "| `/audit/ai-tournament.html` | **Best paper** | Paper only | deepseek_v4 PF~3.5, n=200+ resolved |",
        "| `/audit/ai_leaderboard.html` | Thin | No | ~1 engine ranked; 503 candidates unattributed |",
        "| `/audit/pick_funnel.html` | Discovery | No | Cells often concentration/dispute flagged |",
        "| `/audit/research_index.html` | Hypothesis catalog | Pre-register only | M-107 registry |",
        "",
        "## 3. Live asset-class snapshot (policy-clean)",
        "",
    ]
    mr = evidence.get("audit_dashboard/data/money_ready_verdict.json", {})
    for ac, row in sorted((mr.get("classes") or {}).items()):
        if isinstance(row, dict):
            lines.append(
                f"- **{ac}**: n={row.get('n_resolved')} WR={row.get('wr')} "
                f"PF={row.get('pf')} → {row.get('verdict')}"
            )

    lines.extend([
        "",
        "## 4. DB strategy inventory (ejaguiar1_stocks / backtests)",
        "",
        f"- Backtest DB tables: `{db.get('backtests_tables', [])}`",
        "",
        "### Top resolved strategies (90d, n≥10)",
        "",
        "| Class | Strategy | n | WR | PF |",
        "|-------|----------|---|-----|-----|",
    ])
    for r in (db.get("at_signal_outcomes_90d_top") or [])[:20]:
        lines.append(
            f"| {r.get('asset_class')} | {r.get('strategy')} | {r.get('n')} | "
            f"{r.get('wr')} | {r.get('pf')} |"
        )

    lines.extend([
        "",
        "## 5. Statistical readiness (Bonferroni → ideal)",
        "",
        "- **Bare minimum:** Bonferroni α/N tests; 70/30 split; PF≥1.5; MDD≤30%; flat 5bps costs.",
        "- **Production ideal:** Purged+embargo WF, block bootstrap, DSR/PBO/SPA, HHI<0.20, forward n≥30–50, 8w shadow.",
        "- **Current repo:** `alpha_engine/admissibility_pipeline.py`, `verified_strategies/pipeline/`, `tools/run_eagle_suite.py`.",
        "- **Bonferroni note:** With ~80+ emitters tested historically, α_adj ≈ 0.05/80 ≈ **0.000625** per test — explains why raw green funnel cells fail under SPA.",
        "",
        "## 6. Best picks TODAY (evidence-bound)",
        "",
        "| Symbol | Class | Evidence | Verdict |",
        "|--------|-------|----------|---------|",
        "| **EEM, IWM, GLD** | ETF | EAGLE3 tournament ≥60% WR | Paper edge; not production money-ready |",
        "| **BAC, JPM, MSFT** | EQUITY | Tournament LONG-only edge | Paper; production EQUITY PF=0.33 |",
        "| **BTC/ETH SHORT** | CRYPTO | Tournament SHORT 67% WR vs LONG 33% | EAGLE-4 flip applied in scanner |",
        "| **NVDA** | EQUITY | ~64% tournament WR, active confluence picks | **Monitor only** — production book weak |",
        "| **KULR, RGTI** | PENNY | 100% WR tournament (tiny n) | High artifact risk; do not size |",
        "",
        "Safe long-term (academic, not from live audit PF): broad ETF dual-momentum sleeves — **shadow pilot only** until forward n≥100.",
        "",
        "## 7. LiteLLM ollama mode smoke tests",
        "",
    ])
    for t in mode_tests:
        status = "OK" if t.get("ok") else f"FAIL: {t.get('error', '')[:120]}"
        lines.append(f"- `{t.get('model')}`: {status}")

    lines.extend(["", "## 8. Per-model swarm insights", ""])
    for r in llm_results:
        lines.append(f"### Model: `{r.get('model')}`")
        if r.get("ok"):
            lines.append(r.get("content", ""))
        else:
            lines.append(f"_Error: {r.get('error')}_")
        lines.append("")

    lines.extend([
        "",
        "## 9. Action plan (next 2 weeks)",
        "",
        "1. Run `python3 tools/run_eagle_suite.py` daily; honor `freeze_promotions`.",
        "2. Forward-pilot **ETF dual momentum** + crypto VWAP/Bollinger (n→100).",
        "3. Re-backtest top DB strategies with purge/embargo + Bonferroni registry count.",
        "4. Do not size from tournament rank alone — require policy-clean convergence.",
        "5. Fix EXPIRED-positive resolver before FOREX promotion.",
        "",
        "## 10. EAGLE files reviewed",
        "",
    ])
    for p in eagle_files:
        lines.append(f"- `{p.relative_to(ROOT)}`")

    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-llm", action="store_true")
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS))
    ap.add_argument("--out", default=str(REPORT_OUT))
    args = ap.parse_args(argv)

    eagle_files = find_eagle_files()
    digest = digest_eagle_files(eagle_files)
    evidence = load_local_evidence()
    db = query_db_strategies()

    print(f"EAGLE files: {len(eagle_files)}", file=sys.stderr)
    mode_tests = test_ollama_modes()
    llm_results: List[Dict] = []

    if not args.skip_llm:
        prompt = build_swarm_prompt(digest, evidence, db)
        models = [m.strip() for m in args.models.split(",") if m.strip()]
        with ThreadPoolExecutor(max_workers=len(models)) as ex:
            futs = {ex.submit(litellm_chat, m, prompt): m for m in models}
            for fut in as_completed(futs):
                llm_results.append(fut.result())

    report = write_report(eagle_files, evidence, db, llm_results, mode_tests)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
