#!/usr/bin/env python3
"""
seed_quarantine.py — detect and filter FABRICATED wallet addresses in the trader seed lists.

WHY THIS EXISTS
---------------
`hyperliquid_scraper.py` hardcodes 113 `(address, label)` seeds. Twenty-three of them contain
impossible sequential-hex patterns and seven are not valid Ethereum addresses. They also carry
provenance labels naming real vendors (`nansen_smart_*`, `arkham_tracked_*`, `copin_top_*`,
`inst_vault_*`), so a reviewer reading the file sees invented entities attributed to reputable
data providers.

Verified against the live API (2026-11-24):
    0x4bcd6a4b5c6d7e8f9012345678abcdef01234567  (inst_vault_1)      -> accountValue 0.0, 0 positions
    0x29ab4e2f3a4b5c6d7e8f9012345678abcdef0123  (highROI_7)         -> accountValue 0.0, 0 positions
    0x9012bf9012345678abcdef012345678abcdef01   (arkham_tracked_2)  -> HTTP 422 (not an address)
    0x87f9cd15f5050a9283f9c2c08c6a1c4b7e2dc3f1  (a real seed)       -> accountValue 20,351,874.61

Any skill score, ranking or backtest computed over an unfiltered seed list is measuring invented
entities. This module makes the defect *detectable and testable* instead of a paragraph in a report.

STATUS: opt-in sidecar. It does NOT change any existing behaviour — no caller imports it yet.
Wiring plan: `hyperliquid_scraper.py` should call `filter_seeds(HIGH_PERFORMING_WALLETS)` where it
builds its address list, and log the rejected count. See reports/HL_HANDOFF_AND_DEPLOYMENT_PLAN_*.md.
"""
from __future__ import annotations

import re
from pathlib import Path

# A real Ethereum address is exactly 0x + 40 hex chars.
_ADDR = re.compile(r"^0x[0-9a-fA-F]{40}$")

# Substrings that cannot plausibly occur in a randomly generated 40-hex-char address.
# A single 16-char cycle appearing once is already ~1e-19 likely; these seeds contain several.
SEQ_SIGNATURES = (
    "0123456789abcdef",
    "0123456789",
    "1234567890",
    "0123abcdef",
    "abcdef0123",
    "abcdefabcdef",
    "89abcdef",
    "9abcdef0",
)


def is_valid_address(addr: str) -> bool:
    """True if `addr` is structurally a valid Ethereum address."""
    return bool(_ADDR.match(addr or ""))


def looks_fabricated(addr: str) -> bool:
    """True if the address is malformed or contains an implausible sequential hex cycle."""
    a = (addr or "").lower()
    if not is_valid_address(a):
        return True
    return any(sig in a for sig in SEQ_SIGNATURES)


def filter_seeds(seeds):
    """Split an iterable of (address, label) into (kept, rejected).

    Deterministic and order-preserving. Never raises on malformed input; a non-pair entry
    is rejected rather than crashing a live scraper.
    """
    kept, rejected = [], []
    for item in seeds:
        try:
            addr, label = item[0], item[1]
        except (TypeError, IndexError):
            rejected.append((item, "malformed seed entry"))
            continue
        if not is_valid_address(addr):
            rejected.append((addr, f"invalid address (len={len(addr or '')}, need 42)"))
        elif looks_fabricated(addr):
            rejected.append((addr, "sequential-hex signature"))
        else:
            kept.append((addr, label))
    return kept, rejected


def audit_file(path: str | Path):
    """Audit a scraper source file for `("0x…", "label")` seed tuples.

    The two failure modes OVERLAP: several short addresses also carry sequential
    signatures. They are therefore reported as non-exclusive counts, not a partition,
    so neither defect can be hidden behind the other's classification order.
    """
    src = Path(path).read_text(encoding="utf-8", errors="replace")
    tuples = re.findall(r'\(\s*"(0x[0-9a-fA-F]*)"\s*,\s*"([^"]*)"', src)
    kept, rejected = filter_seeds(tuples)
    rej_addrs = [str(a).lower() for a, _ in rejected]
    return {
        "file": str(path),
        "total": len(tuples),
        "kept": len(kept),
        "rejected": len(rejected),
        "invalid_length": sum(1 for a in rej_addrs if not is_valid_address(a)),
        "sequential": sum(1 for a in rej_addrs
                          if any(sig in a for sig in SEQ_SIGNATURES)),
        "rejected_detail": rejected,
    }


def _main() -> int:
    import json
    import sys

    here = Path(__file__).resolve().parent
    targets = sys.argv[1:] or [here / "hyperliquid_scraper.py"]
    out = []
    for t in targets:
        try:
            rep = audit_file(t)
        except FileNotFoundError:
            print(f"  MISSING: {t}")
            continue
        out.append(rep)
        print(f"\n{rep['file']}")
        print(f"  total seeds      : {rep['total']}")
        print(f"  kept (plausible) : {rep['kept']}")
        print(f"  REJECTED         : {rep['rejected']}")
        print(f"    invalid length : {rep['invalid_length']}")
        print(f"    sequential hex : {rep['sequential']}")
        for a, why in rep["rejected_detail"][:8]:
            print(f"      {a}  <- {why}")
        if rep["rejected"] > 8:
            print(f"      ... and {rep['rejected'] - 8} more")
    if out:
        p = here / "fabricated_seeds.json"
        p.write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
