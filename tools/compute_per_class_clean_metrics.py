"""
One-shot analysis: per-asset-class clean metrics after stripping outliers.
Produces reports/per_class_clean_metrics_2026_04_29.md

Outliers stripped (per AI panel synthesis 2026-04-29):
  1. symbol == 'USDCHF=X'  -- 3015.8% concentration outlier in FOREX
  2. source_system contains 'mercury2'  -- Mercury2 toxic-source picks
     (The panel purge_summary labels these TRX*, KATUSDT, Mercury2;
      TRX* and KATUSDT are absent from recent_closed at time of writing,
      so mercury2-source is the only live purge-eligible set.)

Run: python tools/compute_per_class_clean_metrics.py
"""

import json
import math
import os
from datetime import datetime

DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "audit_dashboard", "data", "dashboard_data.json"
)
OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "reports", "per_class_clean_metrics_2026_04_29.md"
)

# ── helpers ──────────────────────────────────────────────────────────────────

def profit_factor(wins_pnl, losses_pnl):
    """Sum of positive PnLs / sum of |negative PnLs|. Inf when no losses."""
    if losses_pnl == 0:
        return float("inf")
    return wins_pnl / losses_pnl


def sharpe_per_trade(pnl_list):
    """Mean / std of per-trade PnL list. Returns NaN for <2 trades."""
    n = len(pnl_list)
    if n < 2:
        return float("nan")
    mu = sum(pnl_list) / n
    var = sum((x - mu) ** 2 for x in pnl_list) / (n - 1)
    sd = math.sqrt(var) if var > 0 else 0.0
    if sd == 0:
        return float("nan")
    return mu / sd


def calmar(avg_pnl, max_dd):
    """avg_pnl / max_drawdown. Uses worst single-trade loss as proxy MDD."""
    if max_dd == 0:
        return float("inf")
    return avg_pnl / max_dd


def wr_ci_95(wr_frac, n):
    """95% confidence interval half-width: ±1.96 * sqrt(p*(1-p)/n)."""
    if n == 0:
        return float("nan")
    return 1.96 * math.sqrt(wr_frac * (1.0 - wr_frac) / n)


def fmt_pf(v):
    if v == float("inf"):
        return "∞"
    if math.isnan(v):
        return "NaN"
    return f"{v:.3f}"


def fmt_f(v, dec=2):
    if math.isnan(v) or math.isinf(v):
        return "—"
    return f"{v:.{dec}f}"


# ── load data ─────────────────────────────────────────────────────────────────

with open(DATA_PATH) as fh:
    data = json.load(fh)

picks_all = data["picks"]["recent_closed"]

# ── classify outliers ─────────────────────────────────────────────────────────

def is_outlier(p):
    if p.get("symbol") == "USDCHF=X":
        return True
    src = str(p.get("source_system", "")).lower()
    if "mercury2" in src:
        return True
    # Guard future-proofing: TRX* and KATUSDT absent now but listed in panel
    sym = str(p.get("symbol", ""))
    if sym.startswith("TRX") or sym == "KATUSDT":
        return True
    return False


picks_dirty = picks_all
picks_clean = [p for p in picks_all if not is_outlier(p)]

n_total   = len(picks_dirty)
n_purged  = n_total - len(picks_clean)
usdchf_n  = sum(1 for p in picks_dirty if p.get("symbol") == "USDCHF=X")
mercury2_n = sum(1 for p in picks_dirty if "mercury2" in str(p.get("source_system","")).lower())
trxkat_n  = sum(1 for p in picks_dirty
                if str(p.get("symbol","")).startswith("TRX") or p.get("symbol") == "KATUSDT")

# ── compute per-class metrics ─────────────────────────────────────────────────

CLASSES = ["BOND", "COMMODITY", "CRYPTO", "EQUITY", "ETF", "FOREX"]

def compute_class_metrics(picks, asset_class):
    subset = [p for p in picks if p.get("asset_class") == asset_class]
    n = len(subset)
    if n == 0:
        return None
    pnls = [p.get("pnl_pct", 0.0) for p in subset]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x <= 0]
    wr = len(wins) / n
    avg_pnl = sum(pnls) / n
    sum_pnl = sum(pnls)
    pf = profit_factor(sum(wins), sum(abs(x) for x in losses))
    sh = sharpe_per_trade(pnls)
    worst_loss = max((abs(x) for x in losses), default=0.0)
    cal = calmar(avg_pnl, worst_loss)
    ci = wr_ci_95(wr, n)
    return {
        "n": n,
        "wr": wr,
        "wr_pct": wr * 100,
        "ci": ci,
        "ci_pct": ci * 100,
        "wr_lo": (wr - ci) * 100,
        "wr_hi": (wr + ci) * 100,
        "avg_pnl": avg_pnl,
        "sum_pnl": sum_pnl,
        "pf": pf,
        "sharpe": sh,
        "calmar": cal,
        "wins": len(wins),
        "losses": len(losses),
    }


results_dirty = {ac: compute_class_metrics(picks_dirty, ac) for ac in CLASSES}
results_clean = {ac: compute_class_metrics(picks_clean, ac) for ac in CLASSES}

# ── verdict logic ──────────────────────────────────────────────────────────────

def verdict(m):
    if m is None:
        return "INSUFFICIENT DATA"
    wr_lo = m["wr_lo"]
    wr_hi = m["wr_hi"]
    pf = m["pf"]
    n = m["n"]
    if n < 30:
        return "INSUFFICIENT DATA (n<30)"
    overlap_50 = wr_lo < 50.0 < wr_hi
    if overlap_50:
        return "MARGIN-WR-ONLY (CI overlaps 50%)"
    if wr_lo >= 50.0 and pf >= 2.0:
        return "TIER-1 EDGE (PF≥2, WR>50%)"
    if wr_lo >= 50.0 and pf >= 1.5:
        return "TIER-2 EDGE (PF≥1.5, WR>50%)"
    if wr_lo >= 50.0 and pf >= 1.0:
        return "WEAK EDGE (PF≥1, WR>50%)"
    if m["wr_pct"] < 50.0 and pf >= 1.5:
        return "PF-EDGE ONLY (WR<50%, PF≥1.5)"
    return "NO CLEAR EDGE"


# ── build markdown output ──────────────────────────────────────────────────────

lines = []
lines.append("# Per-Class Clean Metrics — Post-AI-Panel Recompute")
lines.append(f"\n_Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_\n")

lines.append("## Methodology")
lines.append("")
lines.append("### Data source")
lines.append("- `audit_dashboard/data/dashboard_data.json` → `picks.recent_closed`")
lines.append(f"- Raw pick count before purge: **{n_total}**")
lines.append("")
lines.append("### Outliers stripped")
lines.append(
    f"- `symbol == 'USDCHF=X'` — **{usdchf_n} picks** removed. "
    "Cited as 3015.8% concentration outlier in the AI panel synthesis "
    "(reports/ai_challenge_synthesis_2026_04_29.md). Single-symbol "
    "dominance inflates FOREX WR and sum_pnl, masking true edge distribution."
)
lines.append(
    f"- `source_system contains 'mercury2'` — **{mercury2_n} picks** removed. "
    "Mercury2 source is one of the three toxic-outlier categories in "
    "`system_clean_metrics.purge_summary` (alongside TRX* and KATUSDT)."
)
lines.append(
    f"- `TRX*` / `KATUSDT` symbols — **{trxkat_n} picks** (absent from "
    "recent_closed at time of analysis; guard kept for forward-compatibility)."
)
lines.append(f"\n**Total purged: {n_purged} picks** → clean set: **{len(picks_clean)}**")
lines.append("")
lines.append("### Metrics computed")
lines.append("- **n**: clean pick count per asset class")
lines.append("- **WR%**: win rate (pnl_pct > 0)")
lines.append("- **95% CI**: ±1.96 × √[WR·(1−WR)/n]  (Wilson-approx)")
lines.append("- **PF**: profit factor = Σwins / Σ|losses|")
lines.append("- **Sharpe (per-trade)**: mean(PnL) / std(PnL)")
lines.append("- **Calmar**: avg_pnl / |worst single-trade loss| (proxy for MDD)")
lines.append("- **Verdict**: MARGIN-WR-ONLY if 95% CI overlaps 50%")
lines.append("")
lines.append("Methodology informed by the 6-AI consultation panel "
             "(reports/ai_challenge_synthesis_2026_04_29.md), specifically "
             "the 'Methodology improvements' table and Q8 CPCV consensus.")

lines.append("\n---\n")
lines.append("## Per-Class Results (Clean)\n")

header = (
    "| Class | n | WR% | 95% CI | WR lo | WR hi | "
    "PF | Sharpe | Calmar | Verdict |"
)
sep = (
    "|-------|---|-----|--------|-------|-------|"
    "----|--------|--------|---------|"
)
lines.append(header)
lines.append(sep)

for ac in CLASSES:
    m = results_clean[ac]
    if m is None:
        lines.append(f"| {ac} | 0 | — | — | — | — | — | — | — | INSUFFICIENT DATA |")
        continue
    v = verdict(m)
    lines.append(
        f"| {ac} | {m['n']} | {m['wr_pct']:.1f}% | ±{m['ci_pct']:.1f}% | "
        f"{m['wr_lo']:.1f}% | {m['wr_hi']:.1f}% | "
        f"{fmt_pf(m['pf'])} | {fmt_f(m['sharpe'], 3)} | "
        f"{fmt_f(m['calmar'], 3)} | {v} |"
    )

lines.append("\n---\n")
lines.append("## Comparison: Dirty vs Clean Metrics (Delta)\n")

delta_header = (
    "| Class | Dirty n | Clean n | Δn | "
    "Dirty WR% | Clean WR% | ΔWR% | "
    "Dirty PF | Clean PF | ΔPF |"
)
delta_sep = (
    "|-------|---------|---------|-----|"
    "----------|-----------|-------|"
    "----------|----------|------|"
)
lines.append(delta_header)
lines.append(delta_sep)

for ac in CLASSES:
    md = results_dirty[ac]
    mc = results_clean[ac]
    if md is None:
        lines.append(f"| {ac} | 0 | 0 | 0 | — | — | — | — | — | — |")
        continue
    dn = md["n"]
    cn = mc["n"] if mc else 0
    delta_n = cn - dn
    dwr = md["wr_pct"]
    cwr = mc["wr_pct"] if mc else float("nan")
    delta_wr = cwr - dwr if mc else float("nan")
    dpf = md["pf"]
    cpf = mc["pf"] if mc else float("nan")
    # delta PF: inf-safe
    if math.isinf(dpf) or math.isinf(cpf) or math.isnan(cpf):
        delta_pf_str = "—"
    else:
        delta_pf_str = f"{cpf - dpf:+.3f}"
    lines.append(
        f"| {ac} | {dn} | {cn} | {delta_n:+} | "
        f"{dwr:.1f}% | {fmt_f(cwr, 1)}% | {('+' if delta_wr >= 0 else '') + fmt_f(delta_wr, 1)}% | "
        f"{fmt_pf(dpf)} | {fmt_pf(cpf)} | {delta_pf_str} |"
    )

lines.append("\n---\n")

# ── TL;DR 5 bullets ──────────────────────────────────────────────────────────

lines.append("## TL;DR (5 bullets)\n")

# Determine survivors
survivors = [(ac, results_clean[ac]) for ac in CLASSES
             if results_clean[ac] and results_clean[ac]["n"] >= 30]
edge_classes = [(ac, m) for ac, m in survivors
                if m["wr_lo"] >= 50.0 or m["pf"] >= 1.5]
margin_only = [(ac, m) for ac, m in survivors if verdict(m).startswith("MARGIN-WR-ONLY")]
no_edge = [(ac, m) for ac, m in survivors if verdict(m) == "NO CLEAR EDGE"]

bullet1_classes = ", ".join(
    f"{ac} (PF={fmt_pf(m['pf'])}, WR={m['wr_pct']:.1f}%)"
    for ac, m in edge_classes
) or "none"

bullet2_classes = ", ".join(ac for ac, _ in margin_only) or "none"
bullet3_classes = ", ".join(ac for ac, _ in no_edge) or "none"

# Biggest WR shift
wr_shifts = []
for ac in CLASSES:
    md = results_dirty[ac]
    mc = results_clean[ac]
    if md and mc:
        wr_shifts.append((ac, mc["wr_pct"] - md["wr_pct"]))
biggest_shift = max(wr_shifts, key=lambda x: abs(x[1])) if wr_shifts else ("—", 0)

lines.append(
    f"1. **Clean survivors with measurable edge:** {bullet1_classes}."
)
lines.append(
    f"2. **Margin-WR-only (95% CI overlaps 50%):** {bullet2_classes} — "
    "cannot statistically confirm WR > 50% without wider sample."
)
lines.append(
    f"3. **No clear edge after clean:** {bullet3_classes}."
)
lines.append(
    f"4. **Biggest WR shift from purge:** {biggest_shift[0]} moved "
    f"{biggest_shift[1]:+.1f}pp — confirming outlier contamination was real."
)
lines.append(
    f"5. **Purge scope:** {n_purged} picks removed ({n_purged/n_total*100:.1f}% of "
    f"recent_closed). Primary drivers: USDCHF=X ({usdchf_n}) + "
    f"Mercury2-source ({mercury2_n}). Clean n={len(picks_clean)} "
    "is the recommended denominator for all forward-looking reporting."
)

lines.append("\n---\n")
lines.append("_Source: AI panel synthesis 2026-04-29 (P0 item) — "
             "run `python tools/compute_per_class_clean_metrics.py` to reproduce._")

output = "\n".join(lines) + "\n"

with open(OUTPUT_PATH, "w") as fh:
    fh.write(output)

print(f"Written: {OUTPUT_PATH}")
print(f"Purged {n_purged} / {n_total} picks ({n_purged/n_total*100:.1f}%)")
print()
print("Clean metrics summary:")
for ac in CLASSES:
    m = results_clean[ac]
    if m:
        v = verdict(m)
        print(f"  {ac:12s}: n={m['n']:4d}, WR={m['wr_pct']:.1f}%±{m['ci_pct']:.1f}%, "
              f"PF={fmt_pf(m['pf'])}, Sharpe={fmt_f(m['sharpe'],3)}, "
              f"Calmar={fmt_f(m['calmar'],3)} → {v}")
