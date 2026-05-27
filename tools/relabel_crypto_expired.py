#!/usr/bin/env python3
"""
Relabel CRYPTO closed picks where exit_reason is EXPIRED/TIME_EXIT/MAX_HOLD
but status is WON or LOST (intraday-drift mislabeling).

DRY-RUN by default. Pass --apply to mutate the file.

See: reports/2026-05-25_crypto_78pct_wr_verification.md
v2.3 fix: outcome_resolver.py now labels EXPIRED exits as status=EXPIRED
"""
import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_EXPIRED_PREFIXES = ("EXPIRED", "TIME_EXIT", "MAX_HOLD")


def is_expired_exit(pick: dict) -> bool:
    """Check if exit_reason matches EXPIRED/TIME_EXIT/MAX_HOLD prefix."""
    er = str(pick.get("exit_reason") or "").upper()
    return any(er.startswith(p) for p in _EXPIRED_PREFIXES)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="alpha_engine/data/closed_picks_enriched.json")
    ap.add_argument("--apply", action="store_true", help="Mutate the file. Default is dry-run.")
    args = ap.parse_args()

    src = Path(args.source)
    if not src.exists():
        # Try alternate path
        src = Path("alpha_engine/data/closed_picks.json")
    if not src.exists():
        raise SystemExit(f"Source not found: {args.source}")

    data = json.loads(src.read_text())
    picks = data["picks"] if isinstance(data, dict) and "picks" in data else data

    print(f"Total picks: {len(picks)}")

    # ── Filter: CRYPTO only, closed-decisive (has exit_price + pnl_pct) ──
    crypto_picks = [
        p for p in picks
        if str(p.get("asset_class") or "").upper() == "CRYPTO"
        and p.get("exit_price") is not None
        and p.get("pnl_pct") is not None
    ]
    print(f"\n=== CRYPTO closed-decisive: {len(crypto_picks)} ===")

    # Current status breakdown
    status_counts = Counter(p.get("status", "?") for p in crypto_picks)
    print(f"Current status: {dict(status_counts)}")

    # ── EXPIRED-like exit reasons currently labeled WON/LOST ──
    mislabeled = [
        p for p in crypto_picks
        if is_expired_exit(p)
        and str(p.get("status") or "").upper() in ("WON", "LOST", "CLOSED", "FLAT")
    ]
    print(f"\nEXPIRED-like exit, currently WON/LOST/CLOSED: {len(mislabeled)}")
    if mislabeled:
        mis_status = Counter(str(p.get("status","")).upper() for p in mislabeled)
        mis_reason = Counter(str(p.get("exit_reason","")).upper() for p in mislabeled)
        print(f"  Status breakdown: {dict(mis_status)}")
        print(f"  Exit reason breakdown: {dict(mis_reason)}")

        # PnL distribution
        pnls = [float(p.get("pnl_pct", 0) or 0) for p in mislabeled]
        print(f"  PnL range: {min(pnls):.4f} to {max(pnls):.4f}")
        print(f"  PnL mean: {sum(pnls)/len(pnls):.4f}")
        pos_pnl = sum(1 for x in pnls if x > 0)
        neg_pnl = sum(1 for x in pnls if x < 0)
        print(f"  Positive PnL: {pos_pnl}, Negative PnL: {neg_pnl}")

        # Source concentration
        src_count = Counter(str(p.get("source_system") or p.get("strategy") or "?") for p in mislabeled)
        print(f"  Top sources: {src_count.most_common(5)}")

    # ── ALL CRYPTO with EXPIRED-like exit (including already EXPIRED status) ──
    all_expired_exit = [p for p in crypto_picks if is_expired_exit(p)]
    print(f"\nAll CRYPTO with EXPIRED-like exit: {len(all_expired_exit)}")
    all_exp_status = Counter(str(p.get("status","")).upper() for p in all_expired_exit)
    print(f"  Status breakdown: {dict(all_exp_status)}")

    # ── Projected impact ──
    if mislabeled:
        # What would happen after relabel
        new_wins = sum(1 for p in crypto_picks if str(p.get("status","")).upper() == "WON") - sum(
            1 for p in mislabeled if str(p.get("status","")).upper() == "WON"
        )
        new_losses = sum(1 for p in crypto_picks if str(p.get("status","")).upper() == "LOST") - sum(
            1 for p in mislabeled if str(p.get("status","")).upper() == "LOST"
        )
        new_expired = sum(1 for p in crypto_picks if str(p.get("status","")).upper() == "EXPIRED") + len(mislabeled)
        new_wr = round(new_wins / max(new_wins + new_losses, 1) * 100, 1)
        old_wins = sum(1 for p in crypto_picks if str(p.get("status","")).upper() == "WON")
        old_losses = sum(1 for p in crypto_picks if str(p.get("status","")).upper() == "LOST")
        old_wr = round(old_wins / max(old_wins + old_losses, 1) * 100, 1)
        print(f"\n=== PROJECTED IMPACT ===")
        print(f"  WON:  {old_wins} → {new_wins}  ({old_wins - new_wins} removed)")
        print(f"  LOST: {old_losses} → {new_losses}  ({old_losses - new_losses} removed)")
        print(f"  EXPIRED: +{len(mislabeled)}")
        print(f"  WR:   {old_wr}% → {new_wr}%")

    # ── Apply changes ──
    if args.apply and mislabeled:
        bak = src.with_suffix(src.suffix + ".bak.relabel_expired")
        shutil.copy2(src, bak)
        print(f"\nBackup: {bak}")

        changed = 0
        for p in mislabeled:
            p["_pre_relabel_status"] = p.get("status")
            p["status"] = "EXPIRED"
            p["_relabeled_at"] = datetime.now(timezone.utc).isoformat()
            p["_relabel_reason"] = "v2.3 EXPIRED re-label (intraday-drift fix)"
            p["_resolver_subversion"] = "v2.3"
            changed += 1

        src.write_text(json.dumps(data, indent=2))
        print(f"Applied: {changed} picks relabeled to EXPIRED")
    elif not args.apply:
        print("\nDry-run only. Re-run with --apply to mutate.")
    else:
        print("\nNothing to relabel.")


if __name__ == "__main__":
    main()
