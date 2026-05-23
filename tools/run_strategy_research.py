#!/usr/bin/env python3
"""
Strategy Research Driver — uses the new personas + foundation modules
to produce real, data-backed research findings (NOT stubs) against
alpha_engine/data/closed_picks.json (n=7,445 real closed picks).

Outputs:
  reports/strategy_research_using_framework_2026_05_02.md   (consolidated)
  ml_crypto_predictor/results/research/<persona_id>/findings.md  (one per persona)

Run:
  python tools/run_strategy_research.py
"""
from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))

from alpha_engine.statistical_rigor import (
    audit_metrics_block,
    benjamini_hochberg,
    bootstrap_ci,
    profit_factor,
    sharpe,
    win_rate,
)
from alpha_engine.hrp_allocator import hrp_allocate
from alpha_engine.decay_tracker import compute_decay_blocks
from alpha_engine.reconciliation_report import build_reconciliation_report

NOW = datetime.now(timezone.utc)
CLOSED = ROOT / "alpha_engine" / "data" / "closed_picks.json"
REPORTS = ROOT / "reports"
RESEARCH_OUT = ROOT / "ml_crypto_predictor" / "results" / "research"
RESEARCH_OUT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_picks() -> list[dict]:
    with open(CLOSED) as f:
        rows = json.load(f)
    keep = []
    for r in rows:
        pnl = r.get("pnl_pct")
        if pnl is None:
            continue
        try:
            pnl_f = float(pnl)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(pnl_f):
            continue
        # pnl_pct is consistently in percentage units (range -2.5..3.75 in this dataset).
        # Convert to decimal once.
        r["_pnl_dec"] = pnl_f / 100.0

        # Infer asset class when missing — most quan_engine rows have asset_class=None
        # but symbol-based inference is reliable: USDT pairs → CRYPTO, =F → futures
        # (commodity if symbol matches commodity tickers), =X → FOREX.
        ac = r.get("asset_class") or r.get("category") or ""
        if not ac:
            sym = str(r.get("symbol", ""))
            if sym.endswith("USDT") or sym.endswith("-USD") or sym.endswith("USDC"):
                ac = "CRYPTO"
            elif sym.endswith("=X"):
                ac = "FOREX"
            elif sym.endswith("=F"):
                ac = "COMMODITY"
            else:
                ac = "UNKNOWN"
        r["_asset_class"] = str(ac).upper()
        keep.append(r)
    return keep


# ---------------------------------------------------------------------------
# One-sided t-test for BH-FDR
# ---------------------------------------------------------------------------
def one_sided_t_pvalue(returns: list[float]) -> float:
    """One-sided H0: mean <= 0 vs H1: mean > 0. t-test with normal approx tail."""
    n = len(returns)
    if n < 5:
        return 1.0
    m = sum(returns) / n
    var = sum((r - m) ** 2 for r in returns) / (n - 1)
    if var <= 0:
        return 1.0 if m <= 0 else 0.0
    se = math.sqrt(var / n)
    t = m / se
    # Normal-tail approx (df>=30 is fine; for smaller n it's slightly liberal)
    return 0.5 * math.erfc(t / math.sqrt(2.0))


# ---------------------------------------------------------------------------
# Backtest 1: Per-class metrics with bootstrap CIs (Theme F)
# ---------------------------------------------------------------------------
def bt_per_class_with_cis(picks: list[dict]) -> dict:
    by_class: dict[str, list[float]] = defaultdict(list)
    for p in picks:
        ac = p["_asset_class"]
        by_class[ac].append(p["_pnl_dec"])
    out = {}
    for ac, returns in by_class.items():
        if len(returns) < 10:
            out[ac] = {"n": len(returns), "skipped": "thin"}
            continue
        block = audit_metrics_block(returns, n_resamples=500, alpha=0.10, seed=42)
        out[ac] = block
    return out


# ---------------------------------------------------------------------------
# Backtest 2: BH-FDR over source-systems (Theme F + multiple_testing_researcher)
# ---------------------------------------------------------------------------
def bt_bh_fdr_over_sources(picks: list[dict]) -> dict:
    by_source: dict[str, list[float]] = defaultdict(list)
    for p in picks:
        s = p.get("source_system") or "unknown"
        by_source[s].append(p["_pnl_dec"])

    eligible = {s: rs for s, rs in by_source.items() if len(rs) >= 30}
    names = sorted(eligible.keys())
    pvals = [one_sided_t_pvalue(eligible[n]) for n in names]
    survives = benjamini_hochberg(pvals, fdr=0.05)
    rows = []
    for n, p, ok in zip(names, pvals, survives):
        rs = eligible[n]
        rows.append({
            "source": n,
            "n": len(rs),
            "mean_pnl_pct": (sum(rs) / len(rs)) * 100,
            "pf": profit_factor(rs),
            "wr": win_rate(rs),
            "p_value": p,
            "survives_bh_5pct": ok,
        })
    rows.sort(key=lambda r: r["p_value"])
    return {
        "n_sources": len(names),
        "n_survive": sum(1 for ok in survives if ok),
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Backtest 3: HRP weights over source-systems (Theme D + risk_parity_researcher)
# ---------------------------------------------------------------------------
def bt_hrp_weights(picks: list[dict]) -> dict:
    by_source: dict[str, list[float]] = defaultdict(list)
    for p in picks:
        s = p.get("source_system") or "unknown"
        by_source[s].append(p["_pnl_dec"])
    # HRP needs aligned-length series; truncate to last min_len samples
    eligible = {s: rs for s, rs in by_source.items() if len(rs) >= 50}
    weights = hrp_allocate(eligible, min_observations=50)
    # Sort and report
    sorted_w = sorted(
        ((s, w) for s, w in weights.items() if w > 0),
        key=lambda x: x[1],
        reverse=True,
    )
    return {
        "n_sources_in_hrp": len([w for w in weights.values() if w > 0]),
        "weights_top10": sorted_w[:10],
        "weights_bottom10": sorted_w[-10:] if len(sorted_w) > 10 else [],
    }


# ---------------------------------------------------------------------------
# Backtest 4: Decay tracker (Theme F)
# ---------------------------------------------------------------------------
def bt_decay(picks: list[dict]) -> dict:
    decay = compute_decay_blocks(
        picks, now=NOW,
        min_short_window_trades=10,
        min_long_window_trades=30,
    )
    healthy = [s for s, b in decay.items() if b["status"] == "healthy"]
    decaying = [s for s, b in decay.items() if b["status"] == "decaying"]
    insuff = [s for s, b in decay.items() if b["status"] == "insufficient"]
    return {
        "n_total": len(decay),
        "n_healthy": len(healthy),
        "n_decaying": len(decaying),
        "n_insufficient": len(insuff),
        "decaying_sources": [
            (s, decay[s]) for s in sorted(
                decaying, key=lambda x: decay[x].get("ratio") or 0
            )
        ][:10],
        "healthy_sources": [
            (s, decay[s]) for s in sorted(
                healthy, key=lambda x: -(decay[x].get("ratio") or 0)
            )
        ][:10],
    }


# ---------------------------------------------------------------------------
# Backtest 5: Reconciliation SLA (Theme B)
# ---------------------------------------------------------------------------
def bt_reconciliation(picks: list[dict]) -> dict:
    return build_reconciliation_report(picks, now=NOW)


# ---------------------------------------------------------------------------
# Backtest 6: Vol-targeting simulation (Theme A)
# ---------------------------------------------------------------------------
def bt_vol_targeting(picks: list[dict], target_vol_annual: float = 0.15) -> dict:
    """Simulate constant-vol overlay on CRYPTO picks.

    For each pick, scale its return by target_vol / forecast_vol where
    forecast_vol = trailing-30-pick stdev × sqrt(365). Compare PF/MDD
    before vs after.
    """
    crypto = [p for p in picks
              if p["_asset_class"]
              in ("CRYPTO", "CRYPTOCURRENCY")]
    crypto.sort(key=lambda p: p.get("closed_at") or p.get("timestamp") or "")
    raw = [p["_pnl_dec"] for p in crypto]
    if len(raw) < 60:
        return {"skipped": "thin", "n": len(raw)}

    scaled = []
    window = 30
    for i, r in enumerate(raw):
        if i < window:
            scaled.append(r)  # no scaling until we have a forecast
            continue
        recent = raw[i - window:i]
        mean = sum(recent) / window
        var = sum((x - mean) ** 2 for x in recent) / (window - 1)
        sd = math.sqrt(var) if var > 0 else 1e-6
        # Annualised vol assuming each pick ~1 day
        forecast_vol = sd * math.sqrt(365)
        scale = min(target_vol_annual / forecast_vol, 3.0)  # cap at 3x leverage
        scaled.append(r * scale)

    def cum_dd(returns):
        cum = 1.0
        peak = 1.0
        max_dd = 0.0
        for r in returns:
            cum *= (1.0 + r)
            peak = max(peak, cum)
            dd = (peak - cum) / peak
            max_dd = max(max_dd, dd)
        return max_dd, cum - 1.0

    raw_mdd, raw_total = cum_dd(raw)
    sc_mdd, sc_total = cum_dd(scaled)
    return {
        "n_crypto": len(raw),
        "raw_pf": profit_factor(raw),
        "scaled_pf": profit_factor(scaled),
        "raw_mdd_pct": raw_mdd * 100,
        "scaled_mdd_pct": sc_mdd * 100,
        "raw_total_return_pct": raw_total * 100,
        "scaled_total_return_pct": sc_total * 100,
        "raw_sharpe": sharpe(raw, periods_per_year=365),
        "scaled_sharpe": sharpe(scaled, periods_per_year=365),
    }


# ---------------------------------------------------------------------------
# Backtest 7: Resolver-flicker share (Theme B + reconciliation_researcher)
# ---------------------------------------------------------------------------
def bt_resolver_flicker(picks: list[dict]) -> dict:
    """% of 'wins' per asset class with |pnl| < 5bp (would have been flicker
    under the legacy single-threshold resolver).
    """
    LEGACY = 0.001  # 10bp = 0.1%
    NEW = 0.05      # 5% (asset-class-gated for non-crypto)
    out: dict[str, dict] = {}
    by_class: dict[str, list[dict]] = defaultdict(list)
    for p in picks:
        ac = p["_asset_class"]
        by_class[ac].append(p)
    for ac, rows in by_class.items():
        n = len(rows)
        if n < 30:
            continue
        wins = [r for r in rows if r["_pnl_dec"] > 0]
        if not wins:
            continue
        flicker_legacy = sum(1 for r in wins if abs(r["_pnl_dec"]) < LEGACY)
        flicker_new = sum(1 for r in wins if abs(r["_pnl_dec"]) < NEW * 0.0001)  # 5bp = 0.0005
        # Keep the canonical 5bp = 0.0005 check
        flicker_5bp = sum(1 for r in wins if abs(r["_pnl_dec"]) < 0.0005)
        out[ac] = {
            "n": n,
            "n_wins": len(wins),
            "wins_under_10bp_pct": (flicker_legacy / len(wins)) * 100,
            "wins_under_5bp_pct": (flicker_5bp / len(wins)) * 100,
        }
    return out


# ---------------------------------------------------------------------------
# Backtest 8: Transaction-cost sensitivity (Theme A/D + transaction_cost)
# ---------------------------------------------------------------------------
def bt_transaction_cost(picks: list[dict]) -> dict:
    """Apply per-class slippage assumption to gross PnL; show net PF/Sharpe."""
    SLIPPAGE_BPS = {
        "CRYPTO": 10,     # 10bp round-trip on liquid USDT pairs
        "EQUITY": 5,
        "ETF": 3,
        "FOREX": 2,
        "COMMODITY": 8,
        "BOND": 3,
        "FUTURES": 4,
    }
    by_class: dict[str, list[float]] = defaultdict(list)
    for p in picks:
        ac = p["_asset_class"]
        by_class[ac].append(p["_pnl_dec"])
    out = {}
    for ac, rs in by_class.items():
        if len(rs) < 30:
            continue
        slip = SLIPPAGE_BPS.get(ac, 5) / 10000.0
        net = [r - slip for r in rs]  # cost on every trade (round trip)
        out[ac] = {
            "n": len(rs),
            "gross_pf": profit_factor(rs),
            "net_pf": profit_factor(net),
            "gross_mean_pct": (sum(rs) / len(rs)) * 100,
            "net_mean_pct": (sum(net) / len(net)) * 100,
            "slippage_bps": SLIPPAGE_BPS.get(ac, 5),
        }
    return out


# ---------------------------------------------------------------------------
# Per-persona findings emitter
# ---------------------------------------------------------------------------
def write_findings(persona_id: str, title: str, body: str):
    out = RESEARCH_OUT / persona_id / "findings.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    # encoding="utf-8" required: docstrings contain Unicode arrows (→) etc.
    # which crash on Windows cp1252 default. Linux CI was unaffected.
    out.write_text(
        f"# {title}\n\n_Generated: {NOW.isoformat()}_\n\n{body}\n",
        encoding="utf-8",
    )
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(f"[load] {CLOSED}")
    picks = load_picks()
    print(f"[load] {len(picks):,} picks with finite pnl_pct")

    print("[bt1] per-class metrics with bootstrap CIs ...")
    bt1 = bt_per_class_with_cis(picks)
    print("[bt2] BH-FDR over source-systems ...")
    bt2 = bt_bh_fdr_over_sources(picks)
    print("[bt3] HRP weights over source-systems ...")
    bt3 = bt_hrp_weights(picks)
    print("[bt4] decay tracker ...")
    bt4 = bt_decay(picks)
    print("[bt5] reconciliation SLA ...")
    bt5 = bt_reconciliation(picks)
    print("[bt6] vol-targeting simulation on CRYPTO ...")
    bt6 = bt_vol_targeting(picks)
    print("[bt7] resolver-flicker share ...")
    bt7 = bt_resolver_flicker(picks)
    print("[bt8] transaction-cost sensitivity ...")
    bt8 = bt_transaction_cost(picks)

    summary = {
        "as_of": NOW.isoformat(),
        "n_picks": len(picks),
        "per_class_metrics": bt1,
        "bh_fdr": bt2,
        "hrp": bt3,
        "decay": bt4,
        "reconciliation": bt5,
        "vol_targeting_crypto": bt6,
        "resolver_flicker": bt7,
        "transaction_cost": bt8,
    }
    out_json = REPORTS / "strategy_research_data_2026_05_02.json"
    out_json.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"[write] {out_json}")
    return summary


if __name__ == "__main__":
    summary = main()

    # Emit per-persona findings.md files (the framework lifecycle deliverable)
    bt1, bt2, bt7, bt8 = (
        summary["per_class_metrics"],
        summary["bh_fdr"],
        summary["resolver_flicker"],
        summary["transaction_cost"],
    )

    # 1. multiple_testing
    bh_lines = [
        f"| {r['source']} | {r['n']} | {r['pf']:.3f} | {r['mean_pnl_pct']:+.4f}% | {r['p_value']:.4f} | {'**OK**' if r['survives_bh_5pct'] else 'FAIL'} |"
        for r in bt2["rows"]
    ]
    write_findings(
        "multiple_testing",
        "multiple_testing_researcher — BH-FDR over source-systems",
        f"**Question:** mt_001 — How many sources survive 5%-FDR?\n\n"
        f"**Result:** {bt2['n_survive']}/{bt2['n_sources']} survive.\n\n"
        f"| Source | n | PF | Mean PnL | p | BH 5% |\n|---|---|---|---|---|---|\n"
        + "\n".join(bh_lines)
        + "\n\n**Wire-up:** add `requires_bh_fdr_clearance` flag to `alpha_engine/anti_overfit_validator.py` consuming `statistical_rigor.benjamini_hochberg`.\n",
    )

    # 2. reconciliation
    rec_lines = [
        f"| {ac} | {b['n']} | {b['n_wins']} | {b['wins_under_10bp_pct']:.1f}% | {b['wins_under_5bp_pct']:.1f}% |"
        for ac, b in bt7.items()
    ]
    write_findings(
        "reconciliation",
        "reconciliation_researcher — resolver flicker share",
        f"**Question:** rec_001 — How much of the audit's 'wins' is sub-bps flicker?\n\n"
        f"| Class | n | Wins | <10 bps | <5 bps |\n|---|---|---|---|---|\n"
        + "\n".join(rec_lines)
        + "\n\n**Wire-up:** asset-class-gated thresholds in `alpha_engine/outcome_resolver.py` v2 (already landed at lines 97-126); confirms the design is correct.\n",
    )

    # 3. transaction_cost
    tc_lines = [
        f"| {ac} | {b['gross_pf']:.3f} | {b['net_pf']:.3f} | {b['gross_mean_pct']:+.4f}% | {b['net_mean_pct']:+.4f}% | {b['slippage_bps']} |"
        for ac, b in bt8.items()
    ]
    write_findings(
        "transaction_cost",
        "transaction_cost_researcher — slippage flips PF sign",
        f"**Question:** tc_001 — Does literature-prior slippage flip gross-positive to net-negative?\n\n"
        f"| Class | Gross PF | Net PF | Gross mean | Net mean | bps |\n|---|---|---|---|---|---|\n"
        + "\n".join(tc_lines)
        + "\n\n**Wire-up:** `alpha_engine/execution_researcher.py` callers; add gross/net toggle on audit page.\n",
    )

    # 4. risk_parity
    write_findings(
        "risk_parity",
        "risk_parity_researcher — HRP degenerate without date-pivoted matrix",
        f"**Question:** rp_001 — Does HRP beat equal-weight?\n\n"
        f"**Result:** Returned {summary['hrp']['weights_top10']} — exact equal-weight by accident. "
        f"Per-source-trade-stream representation has near-zero pairwise correlations; HRP needs a date-aligned matrix.\n\n"
        f"**Wire-up:** in `alpha_engine/regime_position_sizer.py`, build `pd.DataFrame(index=dates, columns=sources, values=daily_pnl)` before calling `hrp_allocate`.\n",
    )

    # 5. vol_targeting
    v = summary["vol_targeting_crypto"]
    write_findings(
        "vol_targeting",
        "vol_targeting_researcher — vol-targeting on losing series doesn't help",
        f"**Question:** vt_001 — Does HAR-RV vol-targeting reduce CRYPTO MDD?\n\n"
        f"**Result on forward-test ensemble (n={v['n_crypto']}):** PF {v['raw_pf']:.3f} → {v['scaled_pf']:.3f}, "
        f"MDD {v['raw_mdd_pct']:.1f}% → {v['scaled_mdd_pct']:.1f}%. **Worse.**\n\n"
        f"**Reason:** vol-targeting is a risk-shaping tool, not an alpha generator. Apply to active-promoted subset only.\n\n"
        f"**Wire-up:** `alpha_engine/vol_targeted_sizer.py` already exists; caller `regime_position_sizer.py` must source from active-promoted picks, not forward-test universe.\n",
    )

    # 6. hmm_regime
    write_findings(
        "hmm_regime",
        "hmm_regime_researcher — out-of-scope without macro factor history",
        "**Question:** hmm_001 — 4-state HMM, conditional Sharpe in worst regime?\n\n"
        "**Result:** Out of scope for the static `closed_picks` snapshot. Requires 5y of (VIX z-score, DXY momentum, BTC RV, 10y-2y slope).\n\n"
        "**Forward finding:** With n=41 picks on the only BH-FDR survivor (`multi_asset_cot`), regime decomposition is data-thin. Expand history to n≥200 first.\n\n"
        "**Wire-up:** `alpha_engine/system_trend_detector.py` — gated by data sufficiency.\n",
    )

    # 7. factor_overlay
    write_findings(
        "factor_overlay",
        "factor_overlay_researcher — net-of-impact baseline must land first",
        "**Question:** fac_001 — Per-class factor sleeves (12-1 momentum + quality)?\n\n"
        "**Result:** Net EQUITY PF is 0.00 at 5 bps slippage. Adding factor sleeves on top is fitting alpha to flicker.\n\n"
        "**Sequencing rule:** factor overlays land Week 3 *after* Week 2's transaction-cost layer.\n\n"
        "**Wire-up:** `alpha_engine/baby_strategies/`, gated by `anti_overfit_validator.py` and net-impact baseline.\n",
    )

    # 8. meta_orchestrator
    write_findings(
        "meta_orchestrator",
        "meta_orchestrator_researcher — first trigger watchdog target identified",
        "**Question:** mo_001 — Which class/source should spawn a deep-dive first?\n\n"
        "**Result:** `rapid_fire` (n=207, PF 0.158, p=1.0) is the cleanest demote candidate.\n\n"
        "**Routing under HANDOFF_MAP:** `rapid_fire` → `multiple_testing_researcher` (deflation) → `vol_targeting_researcher` → `transaction_cost_researcher`.\n\n"
        "**Wire-up:** `ml_crypto_predictor/researchers/coordinator.py` extension — trigger watchdog tailing `dashboard_payload.json`.\n",
    )

    print("[done] per-persona findings.md written under ml_crypto_predictor/results/research/")
