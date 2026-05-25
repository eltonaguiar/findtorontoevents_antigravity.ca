"""
Build the Navigation-surface edge matrix for /audit/pick_funnel.html.

For each clickable filter/tab on /audit, compute honest WR / PF / holdout-PF /
why-no-edge per asset class, using the closed-pool from
audit_dashboard/data/dashboard_data.json::picks.recent_closed (or
audit/data/dashboard_data.json — whichever is largest/most recent).

Output: audit_dashboard/data/nav_surface_edge_matrix.json

Columns per (surface, asset_class):
  - n          : closed-trade count (WIN+LOSS only)
  - wr_pct     : raw wins/n
  - wr_shrunk_pct : Bayesian shrink (wins+10)/(n+20), prior 0.5 x 20
  - pf         : sum(+pnl) / |sum(-pnl)|
  - train_pf   : PF on the chrono first-60% slice
  - holdout_pf : PF on the chrono last-40% slice
  - pass_holdout : holdout_pf >= 1.2
  - pass_bonferroni : two-tailed z-test against WR=0.5, alpha=0.05/8_surfaces
  - why_no_edge : auto-generated reason when not edge

Per surface: rolls up an overall verdict ("edge" vs "no-edge").
"""
from __future__ import annotations
import json, math
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[2]

# Surfaces, in display order. Each entry: id, label, predicate(pick) -> bool.
SURFACES = [
    ("verified_alpha", "Verified Alpha",
     lambda p: (p.get("trust_tier") == "PROVEN") and (p.get("source_system") in {
         "polymarket_signals", "kalshi_signals", "copytrader_clone",
         "verified_alpha_engine", "audited_copytrader", "ml_crypto_pred",
     } or (p.get("strat_fwd_wr") or 0) >= 55)),

    ("smart_picks", "Smart Picks",
     lambda p: (p.get("elite_score") or 0) >= 60 and (p.get("confidence") or 0) >= 0.60),

    ("money_ready", "Money Ready",
     lambda p: _money_ready(p)),

    ("high_conviction", "High-Conviction",
     lambda p: (p.get("elite_score") or 0) >= 80 and (p.get("confidence") or 0) >= 0.75
               and (p.get("trust_score") or 0) >= 6),

    ("ueps_long_term", "US Equity — Long-term value",
     lambda p: p.get("asset_class") == "EQUITY" and (p.get("trade_timeframe") or "").upper() in {"POSITION", "SWING"}
               and (p.get("source_system") or "") in {
                   "stocks_competition", "ml_bg_system_f", "alpha_engine_fast",
                   "kimi_riseoftheclaw", "institutional_picks_engine",
                   "multi_asset_institutional",
               }),

    ("ueps_swing", "US Equity — Swing plays",
     lambda p: p.get("asset_class") == "EQUITY" and (p.get("trade_timeframe") or "").upper() == "SWING"),

    ("ueps_closed", "US Equity — Closed holds",
     lambda p: p.get("asset_class") == "EQUITY" and p.get("status") in {"WON", "LOST", "CLOSED"}),

    ("elite_display_tier", "ELITE display tier (SOXX/XLK gold)",
     lambda p: _is_elite_display(p)),
]

_MR_STRATEGIES = {
    "cot_positioning", "cftc_cot_commercial_signal", "stocks_rsi2_pullback",
}
_MR_ML_PREFIXES = (
    "ml_enhanced_INJUSDT", "ml_enhanced_FETUSDT",
    "ml_enhanced_DYDXUSDT", "ml_enhanced_RENDERUSDT",
)


def _money_ready(p) -> bool:
    s = (p.get("strategy") or "")
    return s in _MR_STRATEGIES or s.startswith(_MR_ML_PREFIXES)


def _is_elite_display(p) -> bool:
    # ELITE = the gold-gradient row on /audit. In closed data the display_tier
    # column is sparse, so approximate using ETF + (elite_grade A/B or
    # trust_tier PROVEN/RELIABLE). The autopsy
    # (reports/2026-05-25_etf_golden_long_audit.md) is ETF-specific.
    if p.get("asset_class") == "ETF":
        return True
    # Crypto elite_grade=A is the strongest tier shown in gold on /audit.
    return p.get("elite_grade") == "A" and p.get("asset_class") == "CRYPTO"


# ---------- stats helpers ----------

def _decisive(picks):
    return [p for p in picks if p.get("status") in {"WON", "LOST"} and p.get("pnl_pct") is not None]


def _wins(picks): return sum(1 for p in picks if p.get("status") == "WON")


def _pf(picks):
    pos = sum(p.get("pnl_pct") for p in picks if (p.get("pnl_pct") or 0) > 0)
    neg = sum(p.get("pnl_pct") for p in picks if (p.get("pnl_pct") or 0) < 0)
    if neg == 0:
        return None if pos == 0 else float("inf")
    return round(pos / abs(neg), 3)


def _bayes_wr(wins, n, prior_w=10, prior_n=20):
    return (wins + prior_w) / (n + prior_n) if (n + prior_n) > 0 else 0.5


def _bonferroni_test(wins, n, n_surfaces=8, alpha=0.05):
    if n < 20:
        return False
    p_hat = wins / n
    se = math.sqrt(0.25 / n)  # H0: p=0.5
    z = (p_hat - 0.5) / se if se > 0 else 0
    # two-tailed corrected
    crit = abs(_norm_ppf(1 - (alpha / n_surfaces) / 2))
    return abs(z) >= crit


def _norm_ppf(q: float) -> float:
    # Inverse standard normal CDF — Beasley-Springer-Moro approximation
    # (no scipy dep). Accurate to ~1e-9 in the [0.001,0.999] range we use.
    if q <= 0 or q >= 1:
        return float("nan")
    a = [-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if q < plow:
        u = math.sqrt(-2 * math.log(q))
        return (((((c[0]*u+c[1])*u+c[2])*u+c[3])*u+c[4])*u+c[5]) / \
               ((((d[0]*u+d[1])*u+d[2])*u+d[3])*u+1)
    if q > phigh:
        u = math.sqrt(-2 * math.log(1-q))
        return -(((((c[0]*u+c[1])*u+c[2])*u+c[3])*u+c[4])*u+c[5]) / \
                ((((d[0]*u+d[1])*u+d[2])*u+d[3])*u+1)
    u = q - 0.5
    r = u*u
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*u / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def _chrono_split_pf(picks):
    """Split by closed_at chrono, 60/40. Return (train_pf, holdout_pf)."""
    keyed = []
    for p in picks:
        ts = p.get("closed_at") or p.get("timestamp")
        if not ts:
            continue
        keyed.append((ts, p))
    keyed.sort(key=lambda x: x[0])
    if len(keyed) < 10:
        return None, None
    cut = int(len(keyed) * 0.6)
    train = [k[1] for k in keyed[:cut]]
    hold = [k[1] for k in keyed[cut:]]
    return _pf(train), _pf(hold)


def _why_no_edge(picks, surface_id, ac, wr_pct, pf, train_pf, holdout_pf, pass_bonferroni):
    reasons = []
    n = len(picks)
    if n < 30:
        reasons.append(f"small_n=n<{n}")
    # Overfit gap
    if train_pf is not None and holdout_pf is not None:
        gap = (train_pf if train_pf != float("inf") else 0) - (holdout_pf if holdout_pf != float("inf") else 0)
        if gap > 1.5:
            reasons.append(f"overfit=train_pf-holdout_pf={round(gap,2)}")
    # Concentration
    syms = Counter(p.get("symbol") for p in picks)
    if syms:
        top, top_n = syms.most_common(1)[0]
        share = top_n / n
        if share > 0.40:
            reasons.append(f"concentration=top_symbol_share={int(share*100)}% ({top})")
    # Source-quality
    src_pf = {}
    for p in picks:
        src = p.get("source_system") or "unknown"
        src_pf.setdefault(src, []).append(p)
    if src_pf:
        worst_src, worst_pf_val = None, None
        best_src, best_pf_val = None, None
        for s, ps in src_pf.items():
            v = _pf(ps)
            if v is None or v == float("inf"):
                continue
            if best_pf_val is None or v > best_pf_val:
                best_pf_val, best_src = v, s
            if worst_pf_val is None or v < worst_pf_val:
                worst_pf_val, worst_src = v, s
        if best_pf_val is not None and best_pf_val < 0.7:
            reasons.append(f"source_quality=top_source_PF={best_pf_val} ({best_src})")
    # TIME_EXIT inflation (ELITE surface)
    if surface_id == "elite_display_tier":
        te = sum(1 for p in picks if "TIME" in (p.get("exit_reason") or "").upper())
        te_share = te / n if n else 0
        if te_share > 0.30:
            reasons.append(f"TIME_EXIT_inflation=time_exit_pct={int(te_share*100)}%")
        # Embed the autopsy finding when ETF
        if ac in {"ETF", "_overall"}:
            reasons.append("autopsy=ETF ELITE forward-30d-WR inflated by TIME_EXIT (see reports/2026-05-25_etf_golden_long_audit.md)")
    # Regime — only_wins_in_BULL placeholder: we lack a regime tag in
    # recent_closed, so this is skipped (not falsely asserted).
    # PF / WR / significance fallbacks
    if not reasons:
        if (pf is None or (pf != float("inf") and pf < 1.2)) and not pass_bonferroni:
            reasons.append(f"sub_threshold=PF={pf} wr={wr_pct}% not_bonferroni_sig")
    return ", ".join(reasons) if reasons else ""


# ---------- main ----------

def _find_dashboard_data() -> Path:
    candidates = [
        REPO / "audit_dashboard" / "data" / "dashboard_data.json",
        REPO / "audit" / "data" / "dashboard_data.json",
        REPO / "tmp" / "dashboard_data.json",
    ]
    cands = [c for c in candidates if c.exists()]
    if not cands:
        raise SystemExit("No dashboard_data.json found — checked audit_dashboard/, audit/, tmp/")
    return max(cands, key=lambda p: p.stat().st_size)


def build():
    src = _find_dashboard_data()
    print(f"[build_nav_surface_matrix] reading {src} ({src.stat().st_size:,} bytes)")
    with src.open("r") as f:
        data = json.load(f)
    rc = data.get("picks", {}).get("recent_closed", [])
    print(f"[build_nav_surface_matrix] recent_closed n={len(rc)}")

    classes = sorted({p.get("asset_class") for p in rc if p.get("asset_class")})
    n_surfaces = len(SURFACES)

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": str(src.relative_to(REPO)),
        "n_recent_closed": len(rc),
        "n_surfaces": n_surfaces,
        "bonferroni_alpha": 0.05 / n_surfaces,
        "asset_classes": classes,
        "surfaces": [],
    }

    for sid, label, pred in SURFACES:
        # All picks matching this surface across all classes
        matched_all = [p for p in rc if pred(p)]
        per_class_rows = []
        edge_classes = []
        for ac in classes + ["_overall"]:
            if ac == "_overall":
                bucket = _decisive(matched_all)
            else:
                bucket = _decisive([p for p in matched_all if p.get("asset_class") == ac])
            n = len(bucket)
            if n == 0:
                per_class_rows.append({
                    "asset_class": ac, "n": 0, "wr_pct": None, "wr_shrunk_pct": None,
                    "pf": None, "train_pf": None, "holdout_pf": None,
                    "pass_holdout": False, "pass_bonferroni": False,
                    "why_no_edge": "no_closed_picks",
                })
                continue
            wins = _wins(bucket)
            wr = round(100 * wins / n, 1)
            wrs = round(100 * _bayes_wr(wins, n), 1)
            pf = _pf(bucket)
            tr_pf, ho_pf = _chrono_split_pf(bucket)
            pass_ho = ho_pf is not None and ho_pf != float("inf") and ho_pf >= 1.2
            pass_bf = _bonferroni_test(wins, n, n_surfaces=n_surfaces)
            why = _why_no_edge(bucket, sid, ac, wr, pf, tr_pf, ho_pf, pass_bf)
            is_edge = pass_ho and pass_bf and (pf is not None and (pf == float("inf") or pf >= 1.5))
            if is_edge and ac != "_overall":
                edge_classes.append(ac)
            per_class_rows.append({
                "asset_class": ac,
                "n": n,
                "wr_pct": wr,
                "wr_shrunk_pct": wrs,
                "pf": pf if pf != float("inf") else "inf",
                "train_pf": tr_pf if tr_pf != float("inf") else ("inf" if tr_pf == float("inf") else None),
                "holdout_pf": ho_pf if ho_pf != float("inf") else ("inf" if ho_pf == float("inf") else None),
                "pass_holdout": bool(pass_ho),
                "pass_bonferroni": bool(pass_bf),
                "is_edge": bool(is_edge),
                "why_no_edge": "" if is_edge else why,
            })
        verdict = "edge" if edge_classes else "no-edge"
        out["surfaces"].append({
            "id": sid,
            "label": label,
            "verdict": verdict,
            "edge_classes": edge_classes,
            "n_total": len(_decisive(matched_all)),
            "rows": per_class_rows,
        })

    out_path = REPO / "audit_dashboard" / "data" / "nav_surface_edge_matrix.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"[build_nav_surface_matrix] wrote {out_path} ({out_path.stat().st_size:,} bytes)")
    # Console summary
    for s in out["surfaces"]:
        print(f"  {s['id']:<22} verdict={s['verdict']:<8} n_total={s['n_total']:<5} edge_classes={s['edge_classes']}")
    return out


if __name__ == "__main__":
    build()
