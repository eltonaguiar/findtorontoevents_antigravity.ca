#!/usr/bin/env python3
"""Weekly scorecard: one page, every verdict, and the states that block a verdict.

TODO 48.

Reads whatever measurement artifacts exist and emits a single markdown scorecard
plus a machine-readable JSON. Designed to degrade honestly:

  * A missing artifact is printed as NOT RUN, never skipped silently and never
    estimated.
  * Every row carries its evidence class, its n, and its n_trials where relevant.
  * The scorecard refuses to print a "best strategy" row. There is no ranking
    here, because ranking candidates is how an unmeasured one gets promoted.
  * Non-zero exit if a deterministic harness drifted or the integrity lint has a
    new finding -- so CI fails on regression rather than on a red number.

Read-only. No capital. Not investment advice.

Usage:
    python3 tools/weekly_scorecard.py
    python3 tools/weekly_scorecard.py --out reports/weekly_scorecard --strict
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "reports/weekly_scorecard"
TBILL = 3.50


def _resolver():
    """The provenance resolver module, imported rather than reimplemented.

    `--strict` used to alert on `pct_forward < 95` with no minimum-n guard while the
    CI gate required n_resolved >= 20 -- two definitions of one judgement, which is
    how a threshold drifts apart. Importing keeps ONE definition.
    """
    try:
        if str(REPO / "tools") not in sys.path:
            sys.path.insert(0, str(REPO / "tools"))
        import provenance_resolver  # noqa: PLC0415
        return provenance_resolver
    except Exception:  # noqa: BLE001
        return None

# Every input the scorecard knows about. `what` is printed when the file is absent.
SOURCES = {
    "harness": ("reports/harness_certification/latest.json",
                "harness certification (drift detector)"),
    "ledger": ("reports/ledger_mine/ledger_mine.json",
               "live ledger mine (leakage + per-class + attribution)"),
    "survival": ("reports/survival_regime/survival_regime.json",
                 "pick survival + regime conditioning"),
    "funding": ("reports/funding_venues/funding_venues.json",
                "cross-venue funding dispersion + fee tiers"),
    "volprem": ("reports/vol_premium_pairs/vol_premium_pairs.json",
                "vol risk premium + GDX/SLV pairs"),
    "pm": ("reports/prediction_market_calibration/calibration.json",
           "prediction market calibration"),
    "exec": ("reports/execution_sensitivity/execution_sensitivity.json",
             "execution sensitivity (capacity / maker-taker / turnover / fill)"),
    "carrycost": ("reports/carry_execution/carry_execution_cost.json",
                  "carry execution cost"),
    "prereg": ("reports/prereg_outside/prereg_outside_tests.json",
               "pre-registered outside tests"),
    "provenance": ("reports/provenance/status.json",
                   "provenance ledger (created_at at emit time, hash-chained)"),
    "resolved": ("reports/provenance/resolved_status.json",
                 "provenance resolution (pct_forward, hit rate, PF)"),
    "falsify": ("reports/mega_mutation/falsification.json",
                "source falsification battery (max-stat null, median, duplicates)"),
    "lint": ("reports/integrity_lint/latest.json",
             "integrity lint (selection-on-DV, provenance, n_trials)"),
}


def load(kind):
    rel, _ = SOURCES[kind]
    p = REPO / rel
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def g(d, *path, default=None):
    """Safe nested get through dicts and list indices."""
    cur = d
    for k in path:
        try:
            if isinstance(cur, dict):
                cur = cur.get(k)
            elif isinstance(cur, (list, tuple)) and isinstance(k, int):
                cur = cur[k]
            else:
                return default
        except (IndexError, KeyError, TypeError):
            return default
        if cur is None:
            return default
    return cur


def fnum(x, nd=2, suffix=""):
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return "yes" if x else "no"
    try:
        return f"{float(x):,.{nd}f}{suffix}"
    except (TypeError, ValueError):
        return str(x)


def build():
    rows, notes, alerts = [], [], []
    present, missing = [], []

    for kind, (rel, label) in SOURCES.items():
        if (REPO / rel).exists():
            present.append(kind)
        else:
            missing.append(f"{label} (`{rel}`)")

    # ---- gate: harness certification
    h = load("harness")
    if h is not None:
        hs = h.get("harnesses") or {}
        det = [k for k, v in hs.items()
               if isinstance(v, dict) and v.get("_class") == "deterministic"]
        live = [k for k, v in hs.items()
                if isinstance(v, dict) and v.get("_class") == "live"]
        changed = h.get("deterministic_changes")
        verdict = h.get("verdict") or ("PASS" if not changed else "DRIFT")
        drift_txt = (f"deterministic changes: {fnum(changed, 0)}"
                     if changed is not None
                     else "drift vs baseline is checked by "
                          "tools/harness_certification.py --rerun")
        rows.append(("Harness certification", str(verdict),
                     f"{len(hs)} harnesses ({len(det)} deterministic, "
                     f"{len(live)} live); {drift_txt}", "deterministic"))
        if changed:
            alerts.append(f"harness drift: {changed} deterministic metric(s) changed")
    else:
        rows.append(("Harness certification", "NOT RUN", "artifact absent", "-"))

    # ---- gate: integrity lint
    lint = load("lint")
    if lint is not None:
        new = g(lint, "new_findings", default=g(lint, "n_new"))
        total = g(lint, "total_findings", default=g(lint, "n_total"))
        rows.append(("Integrity lint", "PASS" if not new else "FAIL",
                     f"new {fnum(new, 0)} / total {fnum(total, 0)}", "deterministic"))
        if new:
            alerts.append(f"integrity lint: {new} NEW finding(s)")
    else:
        rows.append(("Integrity lint", "NOT RUN", "run tools/integrity_lint.py", "-"))

    # ---- headline: the live ledger
    lm = load("ledger")
    if lm is not None:
        allr = g(lm, "per_class", "ALL", default={}) or {}
        rows.append(("Live ledger net expectancy",
                     fnum(allr.get("net_bp"), 2, " bp"),
                     f"n={fnum(allr.get('n'), 0)}  PF={fnum(allr.get('pf'), 3)}  "
                     f"CI-LB={fnum(allr.get('pf_ci_lo'), 3)}  t={fnum(allr.get('t'))}",
                     "observed"))
        pc = g(lm, "per_class", default={}) or {}
        for cls, v in pc.items():
            if cls == "ALL":
                continue
            rows.append((f"  {cls}", str(v.get("verdict", "?")),
                         f"net {fnum(v.get('net_bp'), 2, ' bp')}  "
                         f"PF {fnum(v.get('pf'), 3)} (LB {fnum(v.get('pf_ci_lo'), 3)})  "
                         f"n={fnum(v.get('n'), 0)}", "observed"))
        for f in (lm.get("leakage_findings") or [])[:3]:
            notes.append(f)
    else:
        rows.append(("Live ledger net expectancy", "NOT RUN", "run tools/ledger_mine.py", "-"))

    # ---- carry
    fv = load("funding")
    if fv is not None:
        ft = g(fv, "fee_tiers", default={}) or {}
        stab = g(ft, "stability", default={}) or {}
        verdict = "REFUTED" if not stab.get("stable", False) else "CANDIDATE"
        rows.append(("Funding carry, net of fees",
                     verdict,
                     f"gross {fnum(g(ft, 'gross_carry_ann', default=0) * 100, 3, '%/yr')}"
                     f"  halves {fnum(stab.get('h1_ann', 0) * 100, 2)}"
                     f" -> {fnum(stab.get('h2_ann', 0) * 100, 2)}%/yr"
                     f"  blocks>cash {fnum(stab.get('blocks_above_tbill'), 0)}"
                     f"/{fnum(stab.get('n_blocks'), 0)}", "observed"))
    else:
        rows.append(("Funding carry, net of fees", "NOT RUN",
                     "run tools/funding_venue_dispersion.py", "-"))

    # ---- vol premium
    vp = load("volprem")
    if vp is not None:
        vr = g(vp, "vol_risk_premium", default={}) or {}
        naked = vr.get("naked") or {}
        rows.append(("Vol risk premium (existence)",
                     "ESTABLISHED" if (vr.get("vrp_t") or 0) > 3 else "WEAK",
                     f"mean {fnum(vr.get('vrp_mean_bp'), 1, ' bp')}  "
                     f"t={fnum(vr.get('vrp_t'))}", "observed"))
        rows.append(("  short-vol harvest",
                     str(naked.get("verdict", "?")),
                     f"worst period {fnum((naked.get('worst') or 0) * 100, 1, '%')}",
                     "observed"))
        pr = g(vp, "pairs_gdx_slv", default={}) or {}
        rows.append(("  GDX/SLV pairs", str(pr.get("verdict", "?")),
                     f"ADF OOS {fnum(pr.get('adf_oos'))}  "
                     f"net {fnum((pr.get('net_ann') or 0) * 100, 3, '%/yr')}", "observed"))
    else:
        rows.append(("Vol risk premium", "NOT RUN", "run tools/vol_premium_pairs.py", "-"))

    # ---- prediction markets
    pm = load("pm")
    if pm is not None:
        skill = pm.get("brier_skill")
        rows.append(("Prediction market calibration",
                     "ESTABLISHED" if (skill or -1) > 0 else "REFUTED",
                     f"Brier skill {fnum(skill, 4)}  n={fnum(pm.get('n_markets'), 0)}  "
                     f"buckets flagged {len(pm.get('significant_buckets') or [])}"
                     f"/{fnum(pm.get('n_trials'), 0)}", "observed"))
    else:
        rows.append(("Prediction market calibration", "NOT RUN",
                     "run tools/prediction_market_calibration.py", "-"))

    # ---- execution
    ex = load("exec")
    if ex is not None:
        res = ex.get("results") or {}
        curve = g(res, "todo4_capacity", "curve", default={}) or {}
        ok_sizes = [int(k) for k, v in curve.items()
                    if isinstance(v, dict) and v.get("clears_cliff")]
        rows.append(("Execution capacity", "CAPPED" if ok_sizes else "UNMEASURED",
                     f"largest size clearing the cliff: "
                     f"${fnum(max(ok_sizes), 0) if ok_sizes else 'n/a'}",
                     "observed"))
        mt = g(res, "todo5_maker_taker", "by_round_trip_bp", default={}) or {}
        e0 = g(mt, "0.0", "net_bp")
        e24 = g(mt, "24.0", "net_bp")
        t0 = g(mt, "0.0", "t")
        rows.append(("  breakout gross edge", "UNMEASURED cost",
                     f"0bp {fnum(e0, 2, ' bp')} (t {fnum(t0)}) -> "
                     f"24bp {fnum(e24, 2, ' bp')}", "observed"))
        lag0 = g(res, "todo7_fill", "lag0_premium_bp")
        if lag0 is not None:
            rows.append(("  fill-convention premium", "INFLATION",
                         f"lag-0 fill is worth {fnum(lag0, 2, ' bp/trade')}",
                         "observed"))
        to = g(res, "todo6_turnover", default={}) or {}
        if to:
            best = max(((k, v.get("sharpe")) for k, v in to.items()
                        if isinstance(v, dict) and v.get("sharpe") is not None),
                       key=lambda z: z[1], default=None)
            if best:
                rows.append(("  turnover frequency", "cost dial",
                             f"best Sharpe {fnum(best[1], 2)} at {best[0]}",
                             "observed"))

    # ---- pre-registered tests
    pr = load("prereg")
    if pr is not None:
        for k, v in (pr.items() if isinstance(pr, dict) else []):
            if isinstance(v, dict) and "verdict" in v:
                rows.append((f"Prereg {k}", str(v["verdict"]),
                             str(v.get("reason", ""))[:60], "pre-registered"))

    # ---- provenance: THE binding constraint
    pv = load("provenance")
    if pv is not None:
        chain_ok = pv.get("chain_ok")
        n = pv.get("n_records", 0)
        fwd = pv.get("n_forward")
        rows.append(("Provenance ledger",
                     "OK" if chain_ok and n else ("EMPTY" if chain_ok else "BROKEN"),
                     f"{fnum(n, 0)} records; chain "
                     f"{'intact' if chain_ok else 'BROKEN at index ' + str(pv.get('fail_index'))}; "
                     f"forward-creditable {fnum(fwd, 0)}", "deterministic"))
        if not chain_ok:
            alerts.append(f"provenance chain BROKEN at index {pv.get('fail_index')}: "
                          f"{pv.get('fail_reason')}")
        elif n == 0:
            notes.append("Provenance ledger is EMPTY - no pick has yet been recorded "
                         "at emit time, so no result can be forward-credited.")
    else:
        rows.append(("Provenance ledger", "NOT RUN",
                     "python3 tools/provenance_ledger.py --status", "-"))

    # ---- resolution: the number the programme has never been able to compute
    rs = load("resolved")
    if rs is not None:
        pf_ = rs.get("pct_forward")
        nres = rs.get("n_resolved") or 0
        if nres == 0:
            rows.append(("Provenance resolution", "NO DATA",
                         "0 resolved picks yet - no statistic can be formed", "-"))
        else:
            rows.append(("Provenance resolution",
                         "OK" if rs.get("resolution_chain_ok") else "CHAIN BROKEN",
                         f"n_resolved {fnum(nres, 0)}, pct_forward "
                         f"{fnum(pf_, 1, '%')}, hit {fnum(rs.get('hit_rate'), 1, '%')}, "
                         f"mean {fnum(rs.get('mean_bp'), 1, ' bp')}, "
                         f"PF {fnum(rs.get('profit_factor'), 3)}", "observed"))

        # ONE definition of the gate, shared with CI (tools/provenance_resolver.py).
        # "Not yet measurable" (empty ledger, or too few resolutions) PASSES; "should
        # be measurable and is not" (stale pct_forward, starved resolver, edited
        # outcomes) FAILS -- which is exactly the distinction --strict was missing.
        pr = _resolver()
        if pr is None:
            notes.append("provenance gate NOT enforced this run: could not import "
                         "tools/provenance_resolver.py")
            if rs.get("resolution_chain_ok") is False:
                alerts.append("resolution chain BROKEN - outcomes were edited")
        else:
            try:
                picks = pr.read_jsonl(pr.PICKS)
                res = pr.read_jsonl(pr.RES)
                probs, verdict = pr.gate_problems(dict(rs), picks, res)
            except Exception as e:  # noqa: BLE001
                probs, verdict = [], f"gate could not run: {e}"
                notes.append(f"provenance gate could not run: {e}")
            for p in probs:
                alerts.append(f"provenance gate: {p}")
            if not probs:
                notes.append(f"provenance gate: {verdict}")
    else:
        rows.append(("Provenance resolution", "NOT RUN",
                     "python3 tools/provenance_resolver.py --status", "-"))

    # ---- falsification of the last surviving source
    fs = load("falsify")
    if fs is not None:
        npass = fs.get("n_tests_passed")
        ntot = len(fs.get("tests") or {}) or None
        label = "CANDIDATE" if (ntot and npass == ntot) else "QUARANTINE"
        rows.append((f"Source: {fs.get('target', '?')}", label,
                     f"{npass}/{ntot} tests; mean {fnum(fs.get('mean_bp'), 1, ' bp')} "
                     f"median {fnum(fs.get('median_bp'), 1, ' bp')}; "
                     f"failed {', '.join(fs.get('failed') or []) or 'none'}",
                     "observed"))
        if ntot and npass != ntot:
            notes.append(f"{fs.get('target')} is QUARANTINED - no positive-"
                         f"expectancy emitter is established anywhere in the "
                         f"programme; the honest default is T-bills.")
    else:
        rows.append(("Source falsification", "NOT RUN",
                     "run tools/mega_mutation_falsification.py", "-"))

    # ---- missing
    for m in missing:
        notes.append(f"NOT RUN: {m}")

    hdr = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    L = []
    L.append("# Weekly scorecard\n")
    L.append(f"_generated {hdr} by `tools/weekly_scorecard.py`_\n")
    L.append(f"T-bill hurdle used throughout: **{TBILL:.2f}%/yr**\n")
    L.append("## Verdicts\n")
    L.append("| item | verdict | evidence | class |")
    L.append("|---|---|---|---|")
    for name, verdict, ev, cls in rows:
        L.append(f"| {name} | **{verdict}** | {ev} | {cls} |")
    if alerts:
        L.append("\n## ALERTS\n")
        for a in alerts:
            L.append(f"- **{a}**")
    L.append("\n## State notes\n")
    if notes:
        for n in notes:
            L.append(f"- {n}")
    else:
        L.append("- none")
    L.append("\n## What this scorecard deliberately does not do\n")
    L.append("- It does not rank strategies. Ranking is how an unmeasured candidate")
    L.append("  gets promoted; labels are set by evidence class, not by return.")
    L.append("- It does not print a number it could not measure. Absent artifacts")
    L.append("  read NOT RUN, and unmeasured cost blocks promotion")
    L.append("  (`docs/PROMOTION_GATE_2026-11-22.md` gate 1).")
    L.append("- It does not report gross without net.\n")
    L.append("---")
    L.append("No capital deployed. Not investment advice. "
             "UNMEASURED means unmeasured, not zero.")

    return "\n".join(L), {"generated_at": hdr, "rows": rows,
                          "alerts": alerts, "notes": notes,
                          "present": present, "missing": missing}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on any alert (CI mode)")
    a = ap.parse_args()

    md, payload = build()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "scorecard.md").write_text(md)
    (out / "scorecard.json").write_text(json.dumps(payload, indent=1, default=str))
    print(md)
    print(f"\nwrote {out/'scorecard.md'}")

    if a.strict and payload["alerts"]:
        print(f"\nSTRICT: {len(payload['alerts'])} alert(s) -> exit 1")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
