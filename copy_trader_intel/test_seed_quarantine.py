#!/usr/bin/env python3
"""Tests for seed_quarantine. Run: python3 copy_trader_intel/test_seed_quarantine.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from seed_quarantine import (  # noqa: E402
    audit_file,
    filter_seeds,
    is_valid_address,
    looks_fabricated,
)

REAL = "0x87f9cd15f5050a9283f9c2c08c6a1c4b7e2dc3f1"
FAKE_SEQ = "0x4bcd6a4b5c6d7e8f9012345678abcdef01234567"
FAKE_SHORT = "0x9012bf9012345678abcdef012345678abcdef01"

cases = []


def check(name, got, want):
    cases.append((name, got == want, got, want))


# --- address validity
check("valid real address", is_valid_address(REAL), True)
check("41-char rejected", is_valid_address(FAKE_SHORT), False)
check("empty rejected", is_valid_address(""), False)
check("non-hex rejected", is_valid_address("0x" + "z" * 40), False)
check("uppercase hex accepted", is_valid_address("0x" + "A" * 40), True)

# --- fabrication detection
check("sequential seed flagged", looks_fabricated(FAKE_SEQ), True)
check("short seed flagged", looks_fabricated(FAKE_SHORT), True)
check("real seed NOT flagged", looks_fabricated(REAL), False)

# --- the detector must not be a rubber stamp: a random-looking address with no
#     cycle must survive, otherwise the filter would silently empty the universe.
check("plausible address survives", looks_fabricated("0x3f7a1c9e5b2d8460fa17c3e9b528d0f47a6c1e93"), False)

# --- filter splits correctly and preserves order
kept, rejected = filter_seeds([(REAL, "real"), (FAKE_SEQ, "inst_vault_1"), (FAKE_SHORT, "arkham_tracked_2")])
check("filter keeps 1", len(kept), 1)
check("filter rejects 2", len(rejected), 2)
check("filter preserves label", kept[0][1], "real")
check("rejection reason invalid-length",
      any("invalid address" in why for _, why in rejected), True)
check("rejection reason sequential",
      any(why == "sequential-hex signature" for _, why in rejected), True)

# --- malformed input must not crash a live scraper
kept2, rej2 = filter_seeds(["not-a-pair", (REAL, "ok")])
check("malformed entry rejected, no crash", (len(kept2), len(rej2)), (1, 1))

# --- negative control: an all-real list must pass through untouched
real_list = [(REAL, "a"), ("0x3f7a1c9e5b2d8460fa17c3e9b528d0f47a6c1e93", "b")]
k3, r3 = filter_seeds(real_list)
check("all-real list untouched", (len(k3), len(r3)), (2, 0))

# --- audit on the actual scraper file (skipped if absent)
target = Path(__file__).resolve().parent / "hyperliquid_scraper.py"
if target.exists():
    rep = audit_file(target)
    check("audit found seeds", rep["total"] > 50, True)
    check("audit found rejections", rep["rejected"] >= 20, True)
    check("audit found sequential", rep["sequential"] >= 20, True)
    check("audit found invalid length", rep["invalid_length"] >= 5, True)

failed = [c for c in cases if not c[1]]
for name, ok, got, want in cases:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  got={got!r} want={want!r}"))
print(f"\n{len(cases) - len(failed)}/{len(cases)} passed")
sys.exit(1 if failed else 0)
