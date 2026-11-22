#!/usr/bin/env python3
"""Carry across asset classes — separating harvestable spread from ordinary beta.

WHY THIS FILE EXISTS (todo 19)
------------------------------
Funding carry on crypto perps is the one non-beta positive-expectancy stream this
programme has measured. The obvious next question is whether the same thing exists
elsewhere. The naive answer ("bonds carry 4%, equities carry 1.5%") is wrong in the
way that matters, because it conflates two different objects:

  HARVESTABLE SPREAD — return earned from holding two offsetting positions, with
      price exposure netted out. You can size it independently of market direction.
      Examples: perp-funding vs spot, FX forward points vs spot.

  BETA CARRIED — the yield you receive BECAUSE you own the asset. A 10-year bond
      yielding 4% is not a carry trade; it is a duration position that happens to
      pay a coupon. You cannot harvest it without taking the price risk.

Only the first is a candidate for this programme, because every directional bet we
have measured dies at the cost wall.

WHAT IS MEASURED HERE
  1. Bond yield levels (^IRX 13w, ^FVX 5y, ^TNX 10y, ^TYX 30y) -> coupon carry and
     curve slope, which together bound roll-down.
  2. Equity dividend yield is NOT in the price feed and is not measured. Stated as a
     gap rather than filled with a remembered number.
  3. Crypto perp funding is read from the existing measured artifact, not recomputed.
  4. FX forward carry requires the interest differential across two currencies. No
     foreign policy-rate series is available locally, so it is declared UNMEASURED.
     This matters: FX carry is the classic example and its absence is a real gap.

Scope excluded: total-return decomposition, credit spreads, commodity lease rates,
implied vol carry. Each needs data not present locally and is named rather than
guessed.

Usage: python3 tools/carry_across_asset_classes.py
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "carry_cross_class" / "carry_across_asset_classes.json"
FUNDING = ROOT / "reports" / "funding_carry" / "funding_carry_measure.json"

YIELD_SERIES = {"^IRX": "13-week bill", "^FVX": "5-year", "^TNX": "10-year",
                "^TYX": "30-year"}


def fetch_series(ticker: str) -> list[tuple[str, float]]:
    import yfinance as yf
    df = yf.download(ticker, period="5y", interval="1mo", progress=False,
                     auto_adjust=True, threads=False)
    if df is None or len(df) < 24:
        return []
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)
    s = df["Close"].dropna()
    return [(str(i)[:7], float(v)) for i, v in s.items()]


def main() -> int:
    print("=== CARRY ACROSS ASSET CLASSES ===")
    print("  The question is not 'does the class pay a yield' but 'is it a")
    print("  harvestable spread or just beta you already own'.\n")

    levels: dict[str, float] = {}
    print("--- 1. SOVEREIGN YIELD LEVELS (coupon carry for a bond holder) ---")
    print(f"  {'series':<14} {'last %':>8} {'5y mean %':>10} {'5y min %':>9} "
          f"{'5y max %':>9}  n")
    for tk, label in YIELD_SERIES.items():
        try:
            s = fetch_series(tk)
        except Exception:  # noqa: BLE001
            s = []
        if not s:
            print(f"  {label:<14} no data")
            continue
        vals = [v for _d, v in s]
        levels[tk] = vals[-1]
        print(f"  {label:<14} {vals[-1]:>8.2f} {statistics.mean(vals):>10.2f} "
              f"{min(vals):>9.2f} {max(vals):>9.2f}  {len(vals)}")

    if "^TNX" in levels and "^IRX" in levels:
        slope = levels["^TNX"] - levels["^IRX"]
        print(f"\n  10y-13w slope: {slope:+.2f} pp "
              f"({'steep -> roll-down is positive' if slope > 0 else 'inverted -> roll-down is NEGATIVE'})")
        for name, dur in (("IEF (~7.5y dur)", 7.5), ("TLT (~17y dur)", 17.0)):
            rd = slope / 9.0 * dur     # crude: carry the 10y point down the curve
            print(f"  {name:<16} crude roll-down ≈ {rd:+.2f} %/yr "
                  f"(a DURATION position, not a spread)")

    print("\n--- 2. EQUITY DIVIDEND CARRY ---")
    print("  NOT MEASURED. Dividend yield is not in the price feed available here.")
    print("  Declared UNMEASURED rather than filled with a remembered figure.")
    print("  Note the framing regardless: an equity dividend is earned because you")
    print("  own the equity. It cannot be harvested delta-neutral.")

    print("\n--- 3. CRYPTO PERP FUNDING (the one measured spread) ---")
    carry = None
    if FUNDING.exists():
        try:
            d = json.loads(FUNDING.read_text())
            carry = {"gross_mean_bp_day": d.get("gross_mean_bp_day"),
                     "gross_ann_pct": d.get("gross_ann_pct"),
                     "carry_sharpe": d.get("carry_sharpe"),
                     "pct_days_negative": d.get("pct_days_negative_funding"),
                     "max_dd_bp": d.get("max_dd_bp")}
            print(f"  gross {carry['gross_mean_bp_day']:.4f} bp/day = "
                  f"{carry['gross_ann_pct']:.2f}%/yr, Sharpe "
                  f"{carry['carry_sharpe']:.3f}")
            print(f"  negative on {carry['pct_days_negative']:.1f}% of days, "
                  f"carry-stream maxDD {carry['max_dd_bp']:.1f} bp")
            print(f"  THIS IS A SPREAD: spot long + perp short, delta 0 by")
            print(f"  construction. Forward-honest net after measured costs and")
            print(f"  funding decay is 3.18%/yr at VIP0 fees (see R1).")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            print("  artifact unreadable")
    else:
        print("  funding artifact missing")

    print("\n--- 4. FX FORWARD CARRY ---")
    print("  UNMEASURED. Forward points are driven by the interest differential")
    print("  between two currencies; no foreign policy-rate series is available")
    print("  locally. This is a REAL GAP and it is the classic delta-neutral carry")
    print("  trade, so its absence weakens any claim that crypto is 'the only'")
    print("  one. The honest statement is 'the only one MEASURED HERE'.")

    print("\n=== VERDICT ===")
    print("  Harvestable delta-neutral spreads measured in this programme: 1")
    print("    - crypto perp funding: 3.18%/yr net forward at VIP0 fees,")
    print("      which LOSES to a 3.5% T-bill, and clears only at VIP1 or better.")
    print("  Beta-carried yields (bond coupon, equity dividend, bond roll-down):")
    print("    real, but they are compensation for taking price risk you already")
    print("    bear by holding the asset. They are not candidates for a")
    print("    direction-neutral sleeve and should not be counted as alpha.")
    print("  Unmeasured and named: equity dividend carry, FX forward carry,")
    print("    credit spreads, commodity lease rates, implied-vol carry.")
    print("\n  So 'carry across asset classes' does not widen the opportunity set")
    print("  much: it mostly reveals how few genuinely market-neutral spreads are")
    print("  accessible without additional data. That is a result.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "yield_levels_pct": levels,
        "crypto_funding_spread": carry,
        "harvestable_spreads_measured": 1,
        "beta_carried_not_alpha": ["bond coupon", "bond roll-down",
                                   "equity dividend"],
        "unmeasured_declared": ["equity dividend carry", "FX forward carry",
                                "credit spreads", "commodity lease rates",
                                "implied-vol carry"],
        "evidence_class": "MEASUREMENT + CLASSIFICATION",
        "not_advice": True,
    }, indent=2))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
