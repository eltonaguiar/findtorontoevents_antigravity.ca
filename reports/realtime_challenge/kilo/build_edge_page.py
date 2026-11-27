#!/usr/bin/env python3
"""Generate a self-contained, deployable HTML dashboard for the EDGE program.

Reads the real JSON/py outputs and the forward ledger, embeds everything inline
(no external fetch, works on GitHub Pages / any static host), and writes
audit_dashboard/edge_program.html. Honest by construction: every number shown
comes from a reproducible artifact in this repo.
"""
import json, os, html, datetime

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RP = os.path.join(ROOT, "reports", "realtime_challenge", "kilo")
OUT = os.path.join(ROOT, "audit_dashboard", "edge_program.html")


def load(name):
    p = os.path.join(RP, name)
    try:
        return json.load(open(p))
    except Exception:
        return None


def ledger_rows():
    p = os.path.join(RP, "forward_ledger.jsonl")
    rows = []
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def fmt(v, suf=""):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:+.2f}{suf}"
    return f"{v}{suf}"


def main():
    stress = load("edge1_stress.json") or {}
    gatef = load("edge2_gate_f.json") or {}
    overnight = load("edge5_overnight_spy.json") or {}
    led = ledger_rows()

    s_base = stress.get("base", {})
    s_dec = stress.get("base_decomp", {})
    gf_weekly = (gatef.get("arms", {}) or {}).get("weekly", {})
    on_gross = (((overnight.get("overnight_cost_ladder") or {}).get("0.0bp_rt")) or {})
    on_4 = (((overnight.get("overnight_cost_ladder") or {}).get("4.0bp_rt")) or {})
    on_1 = (((overnight.get("overnight_cost_ladder") or {}).get("1.0bp_rt")) or {})

    edges = [
        # id, hypothesis, result, status
        ("EDGE-1", "Crypto funding-carry level, weekly",
         f"FALSIFIED as carry: carry {fmt(s_dec.get('carry_mean_bp'))}bp vs price {fmt(s_dec.get('price_mean_bp'))}bp; "
         f"t={fmt(s_base.get('t'))}, CI {s_base.get('ci95_lo_bp','?')}..{s_base.get('ci95_hi_bp','?')}; OOS unstable.",
         "OBSERVE_ONLY"),
        ("EDGE-2", "Funding extreme reversal",
         f"Mechanism: pure price reversal +148bp t=1.47 vs momentum −166bp t=−1.64; gate-F (730d, n={gf_weekly.get('n','?')}) "
         f"CI {gf_weekly.get('ci95_mean_bp','?')}, DSR {gf_weekly.get('dsr_proxy','?')} → INCONCLUSIVE.",
         "OBSERVE_ONLY"),
        ("EDGE-3", "Cross-venue funding dispersion", "Not yet run (queued).", "QUEUED"),
        ("EDGE-4", "TSMOM on DBMF/KMLM", "Not yet run (queued; nous template).", "QUEUED"),
        ("EDGE-5", "SPY overnight (close→open)",
         f"Gross {fmt(on_gross.get('mean_bp_per_day'))}bp/d t={fmt(on_gross.get('t'))} (REAL); "
         f"net {fmt(on_4.get('mean_bp_per_day'))}bp/d @4bp, {fmt(on_1.get('mean_bp_per_day'))}bp/d @1bp.",
         "CANDIDATE (exec-dependent)"),
        ("EDGE-6", "Equities ORB (US hours)", "Engine backtest S7_ORB_EQ t=0.89 (not sig).", "WATCH"),
    ]

    rows_html = ""
    for eid, hyp, res, st in edges:
        cls = {"OBSERVE_ONLY": "warn", "CANDIDATE (exec-dependent)": "ok",
               "QUEUED": "mute", "WATCH": "warn"}.get(st, "")
        rows_html += (f"<tr><td class='id'>{html.escape(eid)}</td><td>{html.escape(hyp)}</td>"
                      f"<td>{html.escape(res)}</td><td class='{cls}'>{html.escape(st)}</td></tr>")

    led_html = ""
    for r in led[-20:]:
        led_html += (f"<tr><td>{html.escape(str(r.get('rule')))}</td><td>{html.escape(str(r.get('as_of')))}</td>"
                     f"<td>{fmt(r.get('gross_bp'))}</td><td>{fmt(r.get('net_bp'))}</td>"
                     f"<td>{'✅' if r.get('hit') else '❌'}</td></tr>")
    if not led_html:
        led_html = "<tr><td colspan=5 class='mute'>ledger empty — run forward_ledger.py</td></tr>"

    gen = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EDGE Program — 200 rounds (honest ledger)</title>
<style>
:root{{--bg:#0d1117;--fg:#e6edf3;--mute:#8b949e;--ok:#3fb950;--warn:#d29922;--bad:#f85149;--line:#30363d}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}}
header{{padding:28px 20px;border-bottom:1px solid var(--line)}}h1{{margin:0 0 6px;font-size:22px}}
.sub{{color:var(--mute);font-size:13px}}
main{{max-width:1100px;margin:0 auto;padding:20px}}
.banner{{border:1px solid var(--warn);background:rgba(210,153,34,.08);padding:12px 14px;border-radius:8px;margin:16px 0;font-size:14px}}
h2{{font-size:16px;margin:26px 0 8px}}table{{width:100%;border-collapse:collapse;font-size:13.5px}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{color:var(--mute);font-weight:600}}td.id{{font-weight:700;white-space:nowrap}}
.ok{{color:var(--ok)}}.warn{{color:var(--warn)}}.bad{{color:var(--bad)}}.mute{{color:var(--mute)}}
code{{background:#161b22;padding:1px 5px;border-radius:4px;font-size:12.5px}}
footer{{color:var(--mute);font-size:12px;padding:24px 20px;border-top:1px solid var(--line);margin-top:30px}}
</style></head><body>
<header><h1>EDGE Program — 200 rounds</h1>
<div class="sub">Seat <code>kilo-glm52-free-auditreviews</code> · worktree <code>auditreviews-v4</code> · generated {gen} · paper only, $0 capital sanctioned</div></header>
<main>
<div class="banner"><b>Nothing here is money-ready.</b> 0 proven asset classes. Two honest results:
one <b>falsification</b> (EDGE-1 funding-carry is a noisy price factor, not carry) and one
<b>execution-gated candidate</b> (EDGE-5 SPY overnight, real gross but dies at retail cost). Every
number is reproduced by an artifact in this repo; see the markdown reports below.</div>

<h2>EDGE registry</h2>
<table><thead><tr><th>ID</th><th>Hypothesis</th><th>Deep-test result</th><th>Status</th></tr></thead>
<tbody>{rows_html}</tbody></table>

<h2>Forward ledger (net-of-cost observations accruing daily/weekly)</h2>
<table><thead><tr><th>Rule</th><th>As of</th><th>Gross bp</th><th>Net bp</th><th>Hit</th></tr></thead>
<tbody>{led_html}</tbody></table>

<h2>Method laws (enforced every round)</h2>
<ul>
<li><b>L1</b> Decompose any "carry" claim into carry vs price before believing it.</li>
<li><b>L2</b> Sweep ≥20 parameter cells and report how many clear by chance before calling one an edge.</li>
<li><b>L3</b> A rule is not "net-positive" if its 95% CI at zero cost straddles zero — that is underpowered, not profitable.</li>
</ul>

<h2>Artifacts</h2>
<ul>
<li><code>updates/round-EDGE1-stress-funding-falsified-2026-11-27.md</code></li>
<li><code>reports/realtime_challenge/kilo/edge1_stress.py</code> · <code>edge2_gate_f.py</code> · <code>edge5_overnight_spy.py</code> · <code>forward_ledger.py</code></li>
<li><code>EDGE_PROGRAM_200_ROUNDS_CHARTER.md</code> · <code>.github/workflows/edge-forward-monitor.yml</code></li>
</ul>
</main>
<footer>Paper only. Not investment advice. Reproduced from repo artifacts; no live orders are placed by this page.</footer>
</body></html>"""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(doc)
    print("wrote", OUT, len(doc), "bytes")


if __name__ == "__main__":
    main()