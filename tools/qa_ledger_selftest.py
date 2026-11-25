#!/usr/bin/env python3
"""Network-free selftest for tools/qa_ledger.py.

Run:  python3 tools/qa_ledger_selftest.py

Covers the 2026-11-25 fix: BLANK_TP_SL must apply to actionable picks only (demoted
WATCH / SKIP_* rows carry no target by design), and the external cross-check must not
report ordinary intra-hour drift as a MISMATCH while still catching a wrong symbol or
price scale. No network: fetch_external is replaced with a fixed quote.
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import tools.qa_ledger as qa  # noqa: E402

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(("PASS  " if cond else "FAIL  ") + name + (f"  [{detail}]" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


def run_case(picks: list, generated_at: str, quote: float):
    """Point the ledger at a temp snapshot, stub the quote, return (rc, report)."""
    tmp = Path(tempfile.mkdtemp(prefix="qa_ledger_selftest_"))
    live, out = tmp / "live.json", tmp / "out.json"
    live.write_text(json.dumps({"generated_at": generated_at, "picks": picks}))
    qa.LIVE_JSON, qa.OUT_JSON = live, out
    qa._EXT_CACHE.clear()
    qa.fetch_external = lambda symbol, aclass: (quote, "selftest")
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = qa.run()
    report = json.loads(out.read_text()) if out.exists() else {}
    return rc, report, buf.getvalue()


def verdicts(report: dict) -> list:
    return [f["verdict"] for f in report.get("flags", [])]


def pick(**kw) -> dict:
    base = {"symbol": "AAA", "asset_class": "EQUITY", "direction": "STRONG_BUY",
            "entry_price": 100.0, "current_price": 100.6, "pnl_pct": 0.6,
            "tp_pct": 8.0, "sl_pct": -4.0, "price_source": "selftest"}
    base.update(kw)
    return base


def main() -> int:
    now = datetime.now(timezone.utc)

    # ── snapshot age parsing ────────────────────────────────────────────────
    check("age: iso with +00:00 parses",
          qa._snapshot_age_minutes({"generated_at": "2026-11-25T20:00:00+00:00"}) is not None)
    check("age: Z suffix parses",
          qa._snapshot_age_minutes({"generated_at": "2026-11-25T20:00:00Z"}) is not None)
    check("age: garbage -> None",
          qa._snapshot_age_minutes({"generated_at": "not-a-date"}) is None)
    check("age: missing -> None", qa._snapshot_age_minutes({}) is None)
    age = qa._snapshot_age_minutes({"generated_at": (now - timedelta(minutes=90)).isoformat()})
    check("age: 90 minutes ago reads ~90", age is not None and 89 < age < 91, str(age))

    # ── population: demoted rows are not "blank TP/SL" picks ────────────────
    rc, rep, _ = run_case([pick(direction="WATCH", tp_pct=None, sl_pct=None)],
                          now.isoformat(), quote=100.6)
    check("WATCH row with no TP/SL is not critical", rc == 0, str(rep.get("flag_counts")))
    check("WATCH row counted as demoted_no_tpsl",
          rep.get("by_class", {}).get("EQUITY", {}).get("demoted_no_tpsl") == 1)
    check("WATCH row produces no BLANK_TP_SL flag", "BLANK_TP_SL" not in verdicts(rep))

    rc, rep, _ = run_case([pick(direction="SKIP_VOL", tp_pct=None, sl_pct=None)],
                          now.isoformat(), quote=100.6)
    check("SKIP_VOL row with no TP/SL is not critical", rc == 0)

    # BLANK_TP_SL is a NON-critical flag upstream (it is absent from the `critical`
    # tuple), so it never drives the exit code -- the 2026-11-25 red came from the
    # 8 MISMATCH flags. The fix must keep flagging actionable blanks while dropping
    # the 6 demoted rows from that count.
    rc, rep, _ = run_case([pick(direction="STRONG_BUY", tp_pct=None, sl_pct=None)],
                          now.isoformat(), quote=100.6)
    check("actionable row with no TP/SL is flagged BLANK_TP_SL",
          "BLANK_TP_SL" in verdicts(rep))
    check("actionable blank TP/SL counted in blank_tp_sl",
          rep.get("by_class", {}).get("EQUITY", {}).get("blank_tp_sl") == 1)
    check("actionable blank TP/SL stays non-critical (upstream severity)", rc == 0)

    # ── freshness: drift is not a mismatch, wrong scale still is ────────────
    stale = (now - timedelta(minutes=60)).isoformat()
    rc, rep, out = run_case([pick()], stale, quote=101.2)   # 0.6pp drift
    check("stale snapshot + 0.6pp drift is NOT critical", rc == 0, out)
    check("stale drift counted as stale_price",
          rep.get("by_class", {}).get("EQUITY", {}).get("stale_price") == 1)
    check("stale drift produces no MISMATCH", "MISMATCH" not in verdicts(rep))
    check("report records snapshot age",
          (rep.get("snapshot_age_minutes") or 0) > 55, str(rep.get("snapshot_age_minutes")))

    rc, rep, _ = run_case([pick()], stale, quote=112.0)     # 11% apart
    check("stale snapshot + 11% price divergence IS critical", rc == 1)
    check("divergence flagged PRICE_DIVERGENCE", "PRICE_DIVERGENCE" in verdicts(rep))

    rc, rep, _ = run_case([pick()], now.isoformat(), quote=101.2)
    check("fresh snapshot + 0.6pp drift IS critical", rc == 1)
    check("fresh drift flagged MISMATCH", "MISMATCH" in verdicts(rep))
    check("fresh snapshot is not flagged stale", "STALE_SNAPSHOT" not in verdicts(rep))

    # ── staleness assertion: a stale snapshot must fail loudly ──────────────
    over = int(qa._MAX_SNAPSHOT_MIN) + 120
    rc, rep, _ = run_case([pick()], (now - timedelta(minutes=over)).isoformat(), quote=100.6)
    check(f"snapshot older than {int(qa._MAX_SNAPSHOT_MIN)} min IS critical", rc == 1)
    check("staleness flagged STALE_SNAPSHOT", "STALE_SNAPSHOT" in verdicts(rep))

    rc, rep, _ = run_case([pick()], "", quote=100.6)
    check("unparsable snapshot age IS critical", rc == 1)
    check("missing generated_at flagged STALE_SNAPSHOT", "STALE_SNAPSHOT" in verdicts(rep))

    rc, rep, _ = run_case([pick()], "garbage-timestamp", quote=100.6)
    check("garbage generated_at IS critical", rc == 1)

    # ── pre-existing guards must survive the edit ──────────────────────────
    rc, rep, _ = run_case([pick(pnl_pct=5.0)], now.isoformat(), quote=100.6)
    check("published PnL not implied by own prices is critical", rc == 1)
    check("self-inconsistency flagged", "SELF_INCONSISTENT" in verdicts(rep))

    rc, rep, _ = run_case([pick(current_price=None, pnl_pct=None)], now.isoformat(), quote=100.6)
    check("unpriced row is critical", rc == 1)
    check("unpriced flagged", "UNPRICED" in verdicts(rep))

    rc, rep, _ = run_case([pick(quarantined=True, pnl_pct=3.0)], now.isoformat(), quote=100.6)
    check("quarantined row publishing a PnL is critical", rc == 1)
    check("quarantine leak flagged", "QUARANTINE_LEAK" in verdicts(rep))

    print()
    if FAILS:
        print(f"{len(FAILS)} FAILING: {', '.join(FAILS)}")
        return 1
    print("all qa_ledger selftests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
