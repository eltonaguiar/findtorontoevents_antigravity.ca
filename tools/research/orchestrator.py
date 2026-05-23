"""Research orchestrator CLI entrypoint.

  python -m tools.research.orchestrator --class bond --budget 10

v1 mode: P3 + P4 only (textbook seed specs + stubbed backtest).
P1, P2, P5 swarms are scaffolded but NOT fired without `--enable-swarm`
+ explicit budget confirmation. The skeleton produces a real HTML page
today; live swarm wiring follows in PR 2.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

from .p1_loader import load_p1_citations
from .p2_loader import load_p2_specs
from .p3_backtest_runner import run_all as run_backtests
from .p4_cross_test import cross_test_all
from .p5_loader import load_p5_synthesis
from .render_html import write_run
from .schemas import (
    Citation,
    RunSummary,
    SynthesisRow,
)
from .textbook_bond_strategies import get_textbook_specs
from .verify_citations import verify_citations

# v3b SignalSpec wire-in (master-plan Action item). Import is best-effort —
# if pydantic is unavailable, the validator step is a no-op and the run
# continues with legacy StrategySpec only.
try:
    from .signal_spec import validate as _v3b_validate
    _V3B_AVAILABLE = True
except Exception:
    _v3b_validate = None
    _V3B_AVAILABLE = False

ASSET_CLASSES = {"bond", "equity", "forex", "crypto", "etf", "futures", "commodity"}
REPO_ROOT = Path(__file__).resolve().parents[2]


def _seed_textbook(asset_class: str):
    if asset_class == "bond":
        return get_textbook_specs()
    return []  # other classes: textbook seeds added in future PRs


def _strategy_to_v3b_dict(spec, asset_class: str) -> dict:
    """Map legacy StrategySpec -> v3b SignalSpec payload dict.

    Lossy: legacy `entry` is natural language, so direction is parsed via
    substring match (long-only / short-only / pair-trade -> SKIP) and
    confidence defaults to 0.5 absent an explicit score.
    """
    entry = str(getattr(spec, "entry", "")).lower()
    if "long" in entry and "short" in entry:
        direction = "SKIP"  # pair trade, not a single-directional signal
    elif "short" in entry:
        direction = "SHORT"
    elif "long" in entry:
        direction = "LONG"
    else:
        direction = "SKIP"
    universe = getattr(spec, "universe", None) or []
    primary = universe[0] if universe else "UNKNOWN"
    secondary = universe[1] if len(universe) > 1 else None
    now_iso = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "schema_version": "v3b/v1",
        "signal_id": getattr(spec, "spec_id", "unknown"),
        "asset_class": asset_class.upper(),
        "direction": direction,
        "confidence": 0.5,
        "valid_from": now_iso,
        "valid_to": None,
        "primary_ticker": primary,
        "secondary_ticker": secondary,
        "features": [],
        "rationale": (
            f"entry: {getattr(spec, 'entry', '')[:200]} | "
            f"regime: {getattr(spec, 'regime_filter', '')[:120]}"
        )[:800],
    }


def _validate_v3b_batch(specs: list, asset_class: str, run_dir) -> dict:
    """Validate every legacy spec against v3b/v1. Returns counts + rejects.

    Writes v3b_rejects.jsonl into run_dir if any validation fails. Safe
    no-op when pydantic unavailable.
    """
    out = {"validated": 0, "rejected": 0, "rejects_path": None}
    if not _V3B_AVAILABLE or not specs:
        return out
    rejects = []
    for s in specs:
        payload = _strategy_to_v3b_dict(s, asset_class)
        try:
            _v3b_validate(payload)
            out["validated"] += 1
        except Exception as exc:
            out["rejected"] += 1
            rejects.append({
                "signal_id": payload.get("signal_id"),
                "asset_class": payload.get("asset_class"),
                "error": str(exc)[:400],
            })
    if rejects:
        rp = run_dir / "v3b_rejects.jsonl"
        with rp.open("w", encoding="utf-8") as f:
            for r in rejects:
                f.write(json.dumps(r) + "\n")
        out["rejects_path"] = str(rp)
    return out


def _placeholder_citations(asset_class: str) -> list[Citation]:
    """Seed citations matching the textbook strategies until P1 swarm fires."""
    if asset_class == "bond":
        return [
            Citation(
                url="https://www.aeaweb.org/articles?id=10.1257/0002828053828581",
                access_date=dt.date.today().isoformat(),
                title="Bond Risk Premia",
                author="Cochrane & Piazzesi",
                year="2005",
                claim=(
                    "Tent-shaped linear combination of forward rates predicts excess "
                    "bond returns with R² up to 0.44. Used as the source for the "
                    "10y-2y slope-momentum strategy."
                ),
                evidence_strength="peer-reviewed",
                asset_class="BOND",
            ),
            Citation(
                url="https://doi.org/10.1111/jofi.12188",
                access_date=dt.date.today().isoformat(),
                title="The TIPS-Treasury Bond Puzzle",
                author="Fleckenstein, Longstaff, Lustig",
                year="2014",
                claim=(
                    "Mispricing between TIPS and Treasury STRIPS produces a mean-"
                    "reverting breakeven inflation series. Source for the TIPS "
                    "breakeven MR strategy."
                ),
                evidence_strength="peer-reviewed",
                asset_class="BOND",
            ),
            Citation(
                url="https://doi.org/10.1016/j.jfineco.2013.10.005",
                access_date=dt.date.today().isoformat(),
                title="Betting Against Beta",
                author="Frazzini & Pedersen",
                year="2014",
                claim=(
                    "Long low-beta, short high-beta produces positive risk-adjusted "
                    "returns across asset classes including IG credit. Source for "
                    "the IG carry low-vol strategy."
                ),
                evidence_strength="peer-reviewed",
                asset_class="BOND",
            ),
        ]
    return []


def _seed_synthesis(specs, backtests, cross_tests) -> list[SynthesisRow]:
    """Without a P5 swarm, derive a deterministic synthesis from P3+P4 numerics."""
    rows: list[SynthesisRow] = []
    bt_by = {b.spec_id: b for b in backtests}
    ct_by = {c.spec_id: c for c in cross_tests}
    for s in specs:
        b = bt_by.get(s.spec_id)
        c = ct_by.get(s.spec_id)
        if b is None or c is None:
            continue
        # T2 floor check from CLAUDE.md
        passes_floor = b.pf >= 1.5 and b.wr >= 50.0 and b.mdd < 20.0 and b.n_trades >= 50
        if c.verdict == "DUPLICATE":
            verdict = "NO_EDGE"
            rationale = (
                f"Backtest stub PF={b.pf:.2f}/WR={b.wr:.1f}/MDD={b.mdd:.1f}/n={b.n_trades}. "
                f"Cross-test flagged DUPLICATE vs {c.max_rho_strategy} (ρ={c.max_rho:.2f}, "
                f"symbol overlap {c.symbol_overlap_pct:.1f}%). Reject — adds no independent signal."
            )
            wiring_plan = ""
        elif passes_floor and c.verdict == "INDEPENDENT":
            verdict = "GO"
            rationale = (
                f"Backtest stub PF={b.pf:.2f}/WR={b.wr:.1f}/MDD={b.mdd:.1f}/n={b.n_trades} — "
                f"clears T2 floor. Cross-test {c.verdict} (max |ρ|={c.max_rho:.2f}). "
                f"Recommend wire-in pending real BacktestEngine numbers."
            )
            wiring_plan = (
                f"Stage `{s.spec_id}` in `alpha_engine/baby_strats/` (per CLAUDE.md "
                f"strategy factory S4 pre-emission step). After 30d paper-test + "
                f"forward-validation: promote to active emission with quality_gates "
                f"trust_score initialized at 4. Caller: `alpha_engine.smart_picks_engine` "
                f"via existing strategy registry — no new orchestrator needed."
            )
        else:
            verdict = "MIXED"
            rationale = (
                f"Backtest stub PF={b.pf:.2f}/WR={b.wr:.1f}/MDD={b.mdd:.1f}/n={b.n_trades}. "
                f"Cross-test {c.verdict} (ρ={c.max_rho:.2f}). Below T2 floor OR overlap "
                f"warning — needs deeper round before wire-in."
            )
            wiring_plan = ""
        rows.append(
            SynthesisRow(
                spec_id=s.spec_id,
                verdict=verdict,
                rationale=rationale,
                wiring_plan=wiring_plan,
                engine_votes={"deterministic_seed": verdict},
            )
        )
    return rows


def main():
    ap = argparse.ArgumentParser(prog="research.orchestrator")
    ap.add_argument(
        "--class",
        dest="asset_class",
        required=True,
        choices=sorted(ASSET_CLASSES),
        help="Asset class to research.",
    )
    ap.add_argument(
        "--budget",
        type=float,
        default=10.0,
        help="USD cap per class for swarm spend (default $10).",
    )
    ap.add_argument(
        "--enable-swarm",
        action="store_true",
        help="Load latest P1 swarm output from swarm_runs/research_<class>_p1_*/ "
        "and use real citations + HEAD-check verification. Falls back to "
        "textbook placeholders if no swarm dir exists. Does NOT fire P1 "
        "itself — run `python tools/swarm/swarm_run.py --config "
        "tools/swarm/examples/research_<class>_p1.yaml` first.",
    )
    ap.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip HEAD-check of citation URLs (faster; default off).",
    )
    ap.add_argument(
        "--out-root",
        type=Path,
        default=REPO_ROOT / "research" / "asset_class",
        help="Output root (default research/asset_class/).",
    )
    args = ap.parse_args()

    asset_class = args.asset_class.lower()
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    run_dir = args.out_root / asset_class / f"run_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    started = time.time()
    summary = RunSummary(
        asset_class=asset_class.upper(),
        run_ts_utc=ts,
    )

    # ── P1: citations ────────────────────────────────────────────────
    engine_attribution: dict[str, list[str]] = {}
    engine_weights: dict[str, float] = {}
    p1_themes: list[str] = []
    if args.enable_swarm:
        loaded = load_p1_citations(asset_class)
        if loaded["citations"]:
            citations = loaded["citations"]
            engine_attribution = loaded["engine_attribution"]
            p1_themes = loaded["themes_observed"]
            print(
                f"P1: loaded {len(citations)} citations from "
                f"{loaded['p1_dir'].name if loaded['p1_dir'] else '(unknown)'} "
                f"(engines: {', '.join(loaded['engines_seen'])})"
            )
        else:
            print("P1: --enable-swarm set but no swarm dir found; using placeholders.")
            citations = _placeholder_citations(asset_class)
    else:
        citations = _placeholder_citations(asset_class)

    if not args.skip_verify and citations:
        v = verify_citations(citations, engine_attribution=engine_attribution or None)
        citations = v["citations"]
        engine_weights = v["engine_weights"]
        print(
            f"P1 verify: {v['n_verified']}/{v['n_total']} URLs reachable "
            f"({v['n_hallucinated']} hallucinated). "
            f"Engine weights: {engine_weights}"
        )

    # ── P2: candidates ───────────────────────────────────────────────
    if args.enable_swarm:
        p2 = load_p2_specs(asset_class, engine_weights=engine_weights or None)
        if p2["specs"]:
            specs = p2["specs"]
            print(
                f"P2: loaded {len(specs)} candidate specs from "
                f"{p2['p2_dir'].name if p2['p2_dir'] else '(unknown)'} "
                f"(engines: {', '.join(p2['engines_seen'])})"
            )
        else:
            print("P2: --enable-swarm set but no P2 swarm dir found; using textbook seeds.")
            specs = _seed_textbook(asset_class)
    else:
        specs = _seed_textbook(asset_class)

    # ── v3b SignalSpec validation (master-plan Action: wire orphan validator)
    v3b_result = _validate_v3b_batch(specs, asset_class, run_dir)
    if _V3B_AVAILABLE:
        print(
            f"v3b: validated {v3b_result['validated']}/{len(specs)} specs "
            f"(rejected {v3b_result['rejected']}). "
            f"{'See v3b_rejects.jsonl' if v3b_result['rejects_path'] else ''}"
        )
    else:
        print("v3b: pydantic unavailable; skipping SignalSpec validation")

    # ── P3: backtest (real harness, stub metrics) ────────────────────
    backtests = run_backtests(specs)

    # ── P4: cross-test ───────────────────────────────────────────────
    cross_tests = cross_test_all(specs)

    # ── P5: synthesis ────────────────────────────────────────────────
    synthesis: list[SynthesisRow] = []
    p5_run_verdict: str | None = None
    if args.enable_swarm:
        p5 = load_p5_synthesis(asset_class, engine_weights=engine_weights or None)
        if p5["rows"]:
            synthesis = p5["rows"]
            p5_run_verdict = p5["run_verdict"]
            print(
                f"P5: loaded {len(synthesis)} synthesis rows from "
                f"{p5['p5_dir'].name if p5['p5_dir'] else '(unknown)'} "
                f"(engines: {', '.join(p5['engines_seen'])}, run_verdict={p5_run_verdict})"
            )
    if not synthesis:
        synthesis = _seed_synthesis(specs, backtests, cross_tests)

    # ── Verdict roll-up (P5 swarm verdict wins if available) ─────────
    if p5_run_verdict in ("GO", "MIXED", "NO_EDGE"):
        summary.verdict = p5_run_verdict
    else:
        verdicts = {s.verdict for s in synthesis}
        if not synthesis:
            summary.verdict = "ABORTED"
            summary.abort_reason = f"No textbook seed strategies for {asset_class}"
            summary.aborted = True
        elif "GO" in verdicts and "NO_EDGE" not in verdicts and "MIXED" not in verdicts:
            summary.verdict = "GO"
        elif verdicts == {"NO_EDGE"}:
            summary.verdict = "NO_EDGE"
        else:
            summary.verdict = "MIXED"

    summary.n_citations_verified = sum(1 for c in citations if c.verified)
    summary.n_citations_hallucinated = sum(1 for c in citations if not c.verified)
    summary.n_candidates = len(specs)
    summary.n_backtested = len(backtests)
    summary.n_independent_after_cross_test = sum(
        1 for c in cross_tests if c.verdict == "INDEPENDENT"
    )
    summary.n_v3b_validated = v3b_result["validated"]
    summary.n_v3b_rejected = v3b_result["rejected"]
    summary.cost_usd = 0.0  # v1 has zero swarm spend
    summary.wall_time_sec = time.time() - started

    index_path = write_run(
        run_dir, summary, citations, specs, backtests, cross_tests, synthesis
    )

    print(f"\nResearch run complete: {asset_class.upper()}")
    print(f"  verdict:        {summary.verdict}")
    print(f"  candidates:     {summary.n_candidates}")
    print(f"  backtested:     {summary.n_backtested}")
    print(f"  independent:    {summary.n_independent_after_cross_test}")
    print(f"  v3b validated:  {summary.n_v3b_validated} (rejected {summary.n_v3b_rejected})")
    print(f"  cost:           ${summary.cost_usd:.2f}")
    print(f"  wall:           {summary.wall_time_sec:.1f}s")
    print(f"  artifacts:      {run_dir}")
    print(f"  index.html:     {index_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
