"""Apply passesHighConvictionPick tweaks to audit_dashboard/index.html (CRLF-safe)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "audit_dashboard" / "index.html"
text = p.read_text(encoding="utf-8")
t = text.replace("\r\n", "\n")

replacements = [
    (
        "    // Score-based for equity\n    if (sc >= 65) return true;\n",
        "    // Score-only path: require trust or forward-history support (score-alone was too loose vs baseline)\n"
        "    if (sc >= 65 && (trust >= 4.0 || fwdWr >= 0.38)) return true;\n",
    ),
    (
        "    // High score threshold for forex\n    if (sc >= 70) return true;\n",
        "    // High score: align with trust or proven bollinger family (score-alone underperformed in book)\n"
        "    if (sc >= 70 && (trust >= 4.0 || strat.indexOf('bollinger') !== -1)) return true;\n",
    ),
    (
        "    if (trust >= 5.0 && fwdWr >= 0.45) return true;\n    if (sc >= 65) return true;\n",
        "    if (trust >= 5.0 && fwdWr >= 0.45) return true;\n"
        "    if (sc >= 65 && trust >= 4.0) return true;\n",
    ),
    (
        "['GLD','SLV','USO','UNG','DBC','DBE','PDBC',' GOLD','SILVER','OIL','NATURAL']",
        "['GLD','SLV','USO','UNG','DBC','DBE','PDBC','GOLD','SILVER','OIL','NATURAL']",
    ),
]

for a, b in replacements:
    if a not in t:
        raise SystemExit(f"MISSING chunk: {a[:80]!r}")
    t = t.replace(a, b, 1)

p.write_text(t.replace("\n", "\r\n"), encoding="utf-8")
print("patched", p)
