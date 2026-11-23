"""Regenerate the measured table in the corrected doc FROM the canonical JSON.

Transcription is how the stale 11.48%/10.49% figures got into a document that
claimed to be corrected. This script removes the human copy step entirely.
"""
import json, pathlib, re

root = pathlib.Path("/tmp/fund-fix")
d = json.loads((root / "reports" / "fund_deep_dive.json").read_text())
f = d["funds"]

# doc order, display name, type, MER text
ROWS = [
    ("FXAIX_adj", "Fidelity 500 Index (FXAIX)", "MF", "0.015%", True),
    ("SPY_adj",   "SPDR S&P 500 (SPY)",        "ETF", "0.0945%", True),
    ("FZROX_adj", "Fidelity ZERO Total Mkt (FZROX)", "MF", "0.00%", False),
    ("VTI_adj",   "Vanguard Total Mkt (VTI)",  "ETF", "0.03%", False),
    ("VTSAX_adj", "Vanguard Total Stock (VTSAX)", "MF", "0.04%", False),
    ("BND_adj",   "Vanguard Total Bond (BND)", "ETF", "0.03%", True),
    ("SGOV_adj",  "iShares 0-3mo T-bill (SGOV)", "ETF", "0.09%", True),
]

NEG = "\u2212"          # the doc's tables use U+2212 MINUS


def pct(v):
    return "n/a (cash)" if v is None else f"{v:.2f}%"


def num(v, bold=False):
    if v is None:
        return "**n/a (cash)**" if bold else "n/a"
    s = f"{v:.3f}".replace("-", NEG)
    return f"**{s}**" if bold else s


lines = ["| instrument | MER | net CAGR | vol | Sharpe | Sortino | max DD |",
         "|---|---:|---:|---:|---:|---:|---:|"]
for key, name, typ, mer, bold in ROWS:
    v = f[key]
    lines.append(
        f"| {'**'+name+'**' if bold else name} {typ} | {mer} | "
        f"{pct(v['net_cagr_pct'])} | {v['vol_pct']:.1f}% | "
        f"{num(v['sharpe'], bold)} | {num(v['sortino'])} | "
        f"{('**'+str(v['max_dd_pct']).replace('-', NEG)+'%**') if bold else str(v['max_dd_pct']).replace('-', NEG)+'%'} |"
    )
table = "\n".join(lines)

doc = root / "docs" / "edge_research" / "FUNDS_WHAT_TO_BUY_2026-11-23_CORRECTED.md"
text = doc.read_text()
start = text.index("| instrument | MER |")
end = text.index("\n\n", text.index("SGOV", start))
text = text[:start] + table + text[end:]

# refresh the Rf sentence from the data, not from memory
rf = f["SGOV_adj"]["rf_pct"]
text = re.sub(r"Cash hurdle \*\*R_f = [\d.]+%/yr\*\*",
              f"Cash hurdle **R_f = {rf:.2f}%/yr**", text)
doc.write_text(text)
print(table)
print(f"\n  rf sentence -> {rf:.2f}%")


# --------------------------------------------------------------------------
# The bootstrap CI table was hand-transcribed and drifted from the JSON
# (VTI lower bound read -1.34 where the payload rounds to -1.33). Its "CAGR"
# column also showed GROSS while the measured table shows NET, which is the
# same gross/net confusion that produced a false bug report. Generate it, and
# label the column for what it is.
# --------------------------------------------------------------------------
CI_ORDER = [
    ("SPY_adj", "SPY"),
    ("FXAIX_adj", "FXAIX"),
    ("FZROX_adj", "FZROX"),
    ("VTI_adj", "VTI"),
    ("VTSAX_adj", "VTSAX"),
    ("BND_adj", "BND"),
    ("SGOV_adj", "SGOV"),
]


def gen_ci_table(payload):
    rows = ["| fund | CAGR (gross) | 90% CI |", "|---|---:|---|"]
    for key, name in CI_ORDER:
        m = payload["funds"][key]
        bs = m.get("bootstrap") or {}
        ci = bs.get("cagr_ci_pct")
        g = f"{m['cagr_pct']:.2f}%".replace("-", NEG)
        if ci is None:
            span = "n/a"
        else:
            lo, hi = ci
            span = "[" + f"{lo:.2f}".replace("-", NEG) + ", " + f"{hi:.2f}".replace("-", NEG) + "]"
            if key in ("SPY_adj", "FXAIX_adj"):
                span = f"**{span}**"
        rows.append(f"| {name} | {g} | {span} |")
    return "\n".join(rows)


ci_table = gen_ci_table(d)
text = doc.read_text()
hdr = "| fund | CAGR | 90% CI |"
if hdr in text:
    start = text.index(hdr)
    end = text.index("\n\n", text.index("SGOV", start))
    text = text[:start] + ci_table + text[end:]
    doc.write_text(text)
    print("\n  regenerated the CI table (labelled gross)")
else:
    print("\n  WARNING: CI table header not found")
