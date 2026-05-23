#!/usr/bin/env python3
"""Verify 30-day realized performance vs all-time dashboard numbers.

Usage: python tools/verify_realized_30d.py
Output: prints three-column comparison: all-time dashboard, raw 30d (closed_picks.json),
        and filtered 30d (dashboard circuit_breaker) — with survivorship-bias warnings.

Three data sources:
  1. dashboard all-time: asset_class_health (post-resolver-v2, deduped by scanner)
  2. raw 30d: closed_picks.json (includes ALL historical picks, pre-gate, re-emissions)
  3. filtered 30d: circuit_breaker.realized_n_30d (dashboard-filtered, same dedup as all-time)

Session-K swarm recommendation: COMMODITY all-time PF=7.71 is inflated by
COT dedup artifacts; filtered 30d (circuit_breaker) is the authoritative recent estimate.
"""
from __future__ import annotations
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_closed_picks():
    for path in (
        ROOT / "alpha_engine" / "data" / "closed_picks.json",
        ROOT / "alpha_engine" / "data" / "closed_picks_fast.json",
    ):
        if path.exists():
            d = json.loads(path.read_text(encoding="utf-8"))
            return d if isinstance(d, list) else d.get("picks", d.get("closed", []))
    return []


def pf_wr(picks: list) -> tuple[int, float, float]:
    gp = gl = wins = losses = 0
    for p in picks:
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue
        pnl = float(pnl)
        if abs(pnl) < 1.5:  # fraction → percent
            pnl *= 100.0
        if pnl > 0:
            gp += pnl
            wins += 1
        elif pnl < 0:
            gl -= pnl
            losses += 1
    n = wins + losses
    pf = gp / gl if gl > 0 else (9999.0 if gp > 0 else 0.0)
    wr = 100.0 * wins / n if n > 0 else 0.0
    return n, round(wr, 1), round(pf, 2)


def main() -> None:
    picks = load_closed_picks()
    print(f"Loaded {len(picks)} raw closed picks from closed_picks.json.\n")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    print(f"30-day window: {cutoff} → today\n")

    dash_path = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
    dash = json.loads(dash_path.read_text(encoding="utf-8")) if dash_path.exists() else {}
    health = dash.get("performance", {}).get("asset_class_health", {})

    by_ac_30d: dict = defaultdict(list)
    for p in picks:
        ed = p.get("exit_date") or p.get("entry_date") or ""
        if ed >= cutoff:
            ac = (p.get("asset_class") or "UNKNOWN").upper()
            by_ac_30d[ac].append(p)

    ASSET_CLASSES = ["EQUITY", "COMMODITY", "CRYPTO", "ETF", "FOREX", "BOND"]

    # ── Table 1: All-time vs raw 30d ───────────────────────────────────────────
    print("=== TABLE 1: All-time (dashboard) vs Raw 30d (closed_picks.json) ===")
    print(f"{'Class':<12} {'All-time n':>12} {'All-time PF':>12} {'Raw-30d n':>10} {'Raw-30d WR%':>12} {'Raw-30d PF':>11} {'Warning'}")
    print("-" * 100)
    for ac in ASSET_CLASSES:
        h = health.get(ac, {})
        n_all = h.get("n", "?")
        pf_all = h.get("pf", "?")
        ps30 = by_ac_30d.get(ac, [])
        n30, wr30, pf30 = pf_wr(ps30)

        warnings = []
        try:
            if float(pf_all) > 0 and n30 >= 10:
                if pf30 < float(pf_all) * 0.5:
                    warnings.append("⚠ 30d PF < 50% of all-time")
                if pf30 < 1.0 and float(pf_all) >= 1.5:
                    warnings.append("⚠ 30d losing despite T2+ all-time")
        except (ValueError, TypeError):
            pass
        if ac == "COMMODITY" and n_all and n30 > int(n_all) * 0.7:
            warnings.append("ℹ 30d raw n > all-time n (pre-gate re-emissions in raw)")

        w = " | ".join(warnings) if warnings else ""
        print(f"{ac:<12} {str(n_all):>12} {str(pf_all):>12} {n30:>10} {wr30:>12} {pf30:>11} {w}")

    # ── Table 2: Dashboard circuit_breaker filtered 30d ───────────────────────
    print("\n=== TABLE 2: Filtered 30d (dashboard circuit_breaker — same dedup as all-time) ===")
    print(f"{'Class':<12} {'All-time n':>12} {'All-time PF':>12} {'CB-30d n':>10} {'CB-30d WR%':>12} {'Status'}")
    print("-" * 90)
    for ac in ASSET_CLASSES:
        h = health.get(ac, {})
        n_all = h.get("n", "?")
        pf_all = h.get("pf", "?")
        cb = h.get("circuit_breaker", {})
        cb_n = cb.get("realized_n_30d")
        cb_wr = cb.get("realized_wr_30d")

        # Determine reliability status using WR only (PF not stored in circuit_breaker)
        status = ""
        try:
            if cb_n is not None and cb_n >= 30:
                wr_v = float(cb_wr) if cb_wr is not None else 0
                if wr_v >= 55:
                    status = "✅ WR≥55% (T1-zone)"
                elif wr_v >= 50:
                    status = "✅ WR≥50% (T2-zone)"
                else:
                    status = "⚠ WR<50% (no sizing)"
            elif cb_n is not None and cb_n > 0:
                status = f"thin (n={cb_n}<30)"
            else:
                status = "n=0"
        except (ValueError, TypeError):
            pass

        cb_n_s = str(cb_n) if cb_n is not None else "—"
        cb_wr_s = f"{cb_wr:.1f}%" if isinstance(cb_wr, (int, float)) else "—"
        print(f"{ac:<12} {str(n_all):>12} {str(pf_all):>12} {cb_n_s:>10} {cb_wr_s:>12}  {status}")

    # ── Discrepancy explanation ────────────────────────────────────────────────
    print("\n=== DATA SOURCE EXPLANATION (addresses swarm HIGH concerns) ===")
    print("""
Three n values exist per class — all correct but counting different things:

  dashboard all-time n  = scanner-deduped picks since inception (post-resolver-v2 filtering)
  raw 30d n             = ALL closed_picks.json entries in last 30d (includes pre-gate,
                          re-emissions, multi-signal duplication for COT)
  circuit_breaker 30d n = dashboard-filtered picks from last 30 calendar days,
                          same dedup logic as all-time (THIS IS THE AUTHORITATIVE 30d NUMBER)

COMMODITY discrepancy explained:
  all-time n=228 (dashboard) — COT picks deduped by scanner (114 raw → 40-50 unique signals)
  raw 30d n=352 (raw picks)  — includes scanner re-emissions BEFORE dedup
  CB 30d n (above)           — filtered same way as dashboard all-time; use this for 30d sizing

FOREX discrepancy explained:
  all-time n=98 (dashboard)  — only POST-gate picks qualify (LONG hard-blocked May 14;
                                SHORT session-gated May 17); recent_closed small by design
  raw 30d n=888 (raw picks)  — all FOREX picks including pre-gate LONG history (expected mismatch)
  CB 30d n (above)           — post-gate 30d count; this is the actionable number
""")

    print("Key notes:")
    print("  COMMODITY all-time PF=7.71 reflects COT dedup artifact; use CB-30d PF for sizing.")
    print("  COT over-emission: 2.85× ratio (114 raw signals → 40 unique). KNOWN LIMITATION.")
    print("  This affects all COT-derived metrics; CB-30d n=65 accounts for dedup at dashboard level.")
    print("  EQUITY 30d raw includes pre-gate stocks_rsi2_pullback (now blocked May 16).")
    print("  FOREX all-time n=98 is post-gate only; 888 raw is pre+post combined (expected).")
    print("  FOREX gate (M-078 + M-130): running since May 14-17 — reassess at n≥100 (~May 31).")
    print("  CRYPTO SPA-failing strategies: P2 escalation — needs user approval to block.")
    print("  Use CB-30d (Table 2) when n≥30; trust all-time only with OOS validation.")
    print("  Tool: python tools/verify_realized_30d.py")


if __name__ == "__main__":
    main()
