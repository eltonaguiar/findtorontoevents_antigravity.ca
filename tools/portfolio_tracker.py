#!/usr/bin/env python3
"""portfolio_tracker.py — one practical portfolio book, three candidate backends.

The question this answers is not "what is our P&L" (several scripts already
print that) but *which storage design should hold the book*, and what each one
costs us operationally. Three designs are implemented and measured on the same
real positions:

  ledger     append-only JSONL event log (`FUND`/`OPEN`/`CLOSE`/`MARK`); the
             state is `replay(events)`. Every line is written once, so a crash
             can only ever truncate the tail; replay skips a partial last line
             and reports it instead of corrupting the book. This is the only
             backend that can answer "what did we know at 09:15".
  snapshot   a materialised JSON state file rewritten on every change. Cheap to
             load, O(1), but a bad write loses history and a torn write loses
             the book with no way to reconstruct it.
  roundtrip  closed trades only. Smallest and simplest, and it *cannot* answer
             live equity, exposure or open risk — which is exactly the gap that
             matters for a portfolio tracker, so the gap is measured rather than
             hidden.

All three share the arithmetic in `_apply`; the comparison therefore tests
storage behaviour (torn writes, load cost, size, recoverability) and bookkeeping
reconciliation against the raw source files, not two independent calculators.
The independent check is `verify_against_sources`, which re-derives realised
P&L straight from `data/realtime_challenge/*.json` and compares.

Paper only. No exchange keys, no orders.

Usage:
  python3 tools/portfolio_tracker.py sync
  python3 tools/portfolio_tracker.py mark
  python3 tools/portfolio_tracker.py status
  python3 tools/portfolio_tracker.py compare [--out reports/portfolio_tracking_comparison.json]
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA = ROOT / "data" / "portfolio_tracker"
LEDGER = DATA / "ledger.jsonl"
SNAPSHOT = DATA / "snapshot.json"
ROUNDTRIPS = DATA / "roundtrips.jsonl"
LATEST = DATA / "latest.json"
RT_DIR = ROOT / "data" / "realtime_challenge"
FORWARD_BOOK = ROOT / "audit_dashboard" / "data" / "forward_book.json"
FORWARD_NOTIONAL = 1000.0
EVENT_TYPES = ("FUND", "OPEN", "CLOSE", "MARK")


# ----------------------------------------------------------------- bookkeeping
def _fee(notional: float, bps: float | None) -> float:
    return notional * float(bps or 0.0) / 1e4


def _new_book(name: str) -> dict:
    return {"book": name, "fund": 0.0, "cash": 0.0, "realized": 0.0, "fees": 0.0,
            "positions": {}, "marks": {}, "closed": []}


def _apply(books: dict, evt: dict) -> None:
    """Apply one event to a materialised set of books. Shared by all backends."""
    name = evt.get("book") or "default"
    b = books.setdefault(name, _new_book(name))
    kind = evt.get("type")
    if kind == "FUND":
        amount = float(evt["amount"])
        b["fund"] += amount
        b["cash"] += amount
    elif kind == "OPEN":
        price = float(evt["price"])
        qty = float(evt["qty"])
        notional = qty * price
        fee = _fee(notional, evt.get("fee_bps"))
        b["cash"] -= notional + fee
        b["fees"] += fee
        b["positions"][evt["id"]] = {
            "id": evt["id"], "book": name, "symbol": evt["symbol"],
            "side": evt.get("side", "LONG"), "qty": qty, "price": price,
            "fee_bps": float(evt.get("fee_bps") or 0.0), "fee_entry": fee,
            "tp": evt.get("tp"), "sl": evt.get("sl"),
            "deadline": evt.get("deadline"), "opened_at": evt.get("ts"),
            "source": evt.get("source"),
        }
        b["marks"].setdefault(evt["symbol"], price)
    elif kind == "CLOSE":
        p = b["positions"].pop(evt["id"], None)
        if p is None:
            return
        price = float(evt["price"])
        notional = p["qty"] * price
        fee = _fee(notional, p["fee_bps"])
        b["cash"] += notional - fee
        b["fees"] += fee
        realized = p["qty"] * (price - p["price"]) - p["fee_entry"] - fee
        b["realized"] += realized
        b["closed"].append({**p, "exit_price": price, "closed_at": evt.get("ts"),
                            "reason": evt.get("reason"),
                            "realized": round(realized, 6)})
    elif kind == "MARK":
        b["marks"][evt["symbol"]] = float(evt["price"])
    else:
        raise ValueError(f"unknown event type: {kind!r}")


def _position_view(p: dict, marks: dict) -> dict:
    mark = float(marks.get(p["symbol"], p["price"]))
    pnl = p["qty"] * (mark - p["price"])
    out = {
        "id": p["id"], "book": p["book"], "symbol": p["symbol"], "side": p["side"],
        "qty": round(p["qty"], 8), "entry": round(p["price"], 8),
        "mark": round(mark, 8), "notional": round(p["qty"] * mark, 2),
        "pnl_usd": round(pnl, 2),
        "pnl_pct": round(100 * (mark / p["price"] - 1), 4) if p["price"] else None,
        "opened_at": p["opened_at"], "deadline": p["deadline"],
    }
    if p.get("tp"):
        out["tp"] = p["tp"]
        out["to_tp_pct"] = round(100 * (p["tp"] / mark - 1), 4)
    if p.get("sl"):
        out["sl"] = p["sl"]
        out["to_sl_pct"] = round(100 * (1 - p["sl"] / mark), 4)
    return out


def _book_view(b: dict) -> dict:
    mtm = sum(p["qty"] * float(b["marks"].get(p["symbol"], p["price"]))
              for p in b["positions"].values())
    unreal = sum(p["qty"] * (float(b["marks"].get(p["symbol"], p["price"])) - p["price"])
                 for p in b["positions"].values())
    equity = b["cash"] + mtm
    return {
        "book": b["book"], "fund": round(b["fund"], 2), "cash": round(b["cash"], 2),
        "equity": round(equity, 2), "realized": round(b["realized"], 2),
        "unrealized": round(unreal, 2), "fees": round(b["fees"], 2),
        "exposure": round(mtm, 2),
        "return_pct": round(100 * (equity / b["fund"] - 1), 4) if b["fund"] else None,
        "n_open": len(b["positions"]), "n_closed": len(b["closed"]),
        "positions": [_position_view(p, b["marks"]) for p in b["positions"].values()],
        "closed": b["closed"],
    }


def replay(events: list[dict]) -> dict:
    books: dict = {}
    for evt in events:
        _apply(books, evt)
    views = {name: _book_view(b) for name, b in books.items()}
    total_fund = sum(v["fund"] for v in views.values())
    total_equity = sum(v["equity"] for v in views.values())
    return {
        "books": views,
        "totals": {
            "fund": round(total_fund, 2), "equity": round(total_equity, 2),
            "realized": round(sum(v["realized"] for v in views.values()), 2),
            "unrealized": round(sum(v["unrealized"] for v in views.values()), 2),
            "fees": round(sum(v["fees"] for v in views.values()), 2),
            "exposure": round(sum(v["exposure"] for v in views.values()), 2),
            "return_pct": round(100 * (total_equity / total_fund - 1), 4) if total_fund else None,
            "n_open": sum(v["n_open"] for v in views.values()),
            "n_closed": sum(v["n_closed"] for v in views.values()),
        },
    }


# -------------------------------------------------------------------- backends
class EventLedger:
    """Append-only JSONL. State is a pure function of the lines on disk."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self) -> tuple[list[dict], int]:
        if not self.path.exists():
            return [], 0
        events, corrupt = [], 0
        for line in self.path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                corrupt += 1  # a torn tail write; skip, never guess
        return events, corrupt

    def append(self, evt: dict) -> None:
        with self.path.open("a") as fh:
            fh.write(json.dumps(evt, sort_keys=True) + "\n")
            fh.flush()

    def append_unique(self, evt: dict) -> bool:
        def key_of(e: dict):
            return (e.get("type"),
                    e.get("id") or f"{e.get('book')}|{e.get('symbol')}|{e.get('ts')}|"
                                  f"{e.get('amount', '')}")

        seen = {key_of(e) for e in self.read()[0]}
        key = key_of(evt)
        if key in seen:
            return False
        self.append(evt)
        return True

    def state(self) -> dict:
        events, corrupt = self.read()
        state = replay(events)
        state["ledger"] = {"path": str(self.path.relative_to(ROOT)) if self.path.is_relative_to(ROOT) else str(self.path),
                           "n_events": len(events), "corrupt_lines": corrupt,
                           "bytes": self.path.stat().st_size if self.path.exists() else 0}
        return state


class SnapshotStore:
    """Materialised state rewritten in full. Fast to load, no history."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.books: dict = {}

    def load(self) -> dict:
        if self.path.exists():
            self.books = json.loads(self.path.read_text())
        return self.books

    def apply(self, evt: dict) -> None:
        _apply(self.books, evt)

    def save(self) -> None:
        self.path.write_text(json.dumps(self.books, indent=1, sort_keys=True) + "\n")

    def state(self) -> dict:
        return replay([]) if not self.books else {
            "books": {n: _book_view(b) for n, b in self.books.items()},
            "totals": {
                "fund": round(sum(b["fund"] for b in self.books.values()), 2),
                "equity": round(sum(_book_view(b)["equity"] for b in self.books.values()), 2),
                "realized": round(sum(b["realized"] for b in self.books.values()), 2),
                "unrealized": round(sum(_book_view(b)["unrealized"] for b in self.books.values()), 2),
                "fees": round(sum(b["fees"] for b in self.books.values()), 2),
                "exposure": round(sum(_book_view(b)["exposure"] for b in self.books.values()), 2),
            },
        }


class RoundTripBook:
    """Closed trades only. Cannot answer equity or open risk — on purpose."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, trades: list[dict]) -> None:
        with self.path.open("a") as fh:
            for t in trades:
                fh.write(json.dumps(t, sort_keys=True) + "\n")
            fh.flush()

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text().splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def stats(self) -> dict:
        trades = self.read()
        wins = [t for t in trades if t.get("realized", 0) > 0]
        losses = [t for t in trades if t.get("realized", 0) < 0]
        gross_win = sum(t["realized"] for t in wins)
        gross_loss = abs(sum(t["realized"] for t in losses))
        return {"n": len(trades), "wins": len(wins), "losses": len(losses),
                "realized": round(sum(t.get("realized", 0) for t in trades), 6),
                "win_rate": round(len(wins) / len(trades), 4) if trades else None,
                "profit_factor": round(gross_win / gross_loss, 4) if gross_loss else None}

    def equity(self):
        raise NotImplementedError(
            "a round-trip log has no open positions or cash, so it cannot mark to market")


# -------------------------------------------------------------------- sources
def _open_event(book: str, source: str, **kw) -> dict:
    evt = {"type": "OPEN", "book": book, "source": source}
    evt.update(kw)
    return evt


def events_from_realtime(path: Path) -> list[dict]:
    """Positions and closed trips from a realtime_challenge state file.

    Fills already include the 2 bps slippage in their prices, so only the 10 bps
    per-side fee is applied here; double-charging slippage would misstate the book.
    """
    state = json.loads(Path(path).read_text())
    book = state.get("tag") or Path(path).stem
    src = str(Path(path).relative_to(ROOT)) if Path(path).is_relative_to(ROOT) else str(path)
    out = [{"type": "FUND", "book": book, "amount": float(state.get("book_usd", 10000.0)),
            "ts": state.get("opened_at"), "source": src}]
    for p in state.get("positions", []):
        out.append(_open_event(book, src, id=p["id"], symbol=p["symbol"],
                               qty=p["qty"], price=p["entry_price"], fee_bps=10.0,
                               side=p.get("side", "LONG"), tp=p.get("tp_price"),
                               sl=p.get("sl_price"), deadline=p.get("deadline"),
                               ts=p.get("opened_at")))
    for c in state.get("closed", []):
        out.append(_open_event(book, src, id=c["id"], symbol=c["symbol"],
                               qty=c["qty"], price=c["entry_price"], fee_bps=10.0,
                               side=c.get("side", "LONG"), tp=c.get("tp_price"),
                               sl=c.get("sl_price"), deadline=c.get("deadline"),
                               ts=c.get("opened_at")))
        out.append({"type": "CLOSE", "book": book, "id": c["id"],
                    "price": c["exit_price"], "ts": c.get("closed_at"),
                    "reason": c.get("exit_reason"), "source": src})
    return out


def events_from_forward_book(path: Path, notional: float = FORWARD_NOTIONAL) -> list[dict]:
    """Equal-notional entries from the pre-registered forward book.

    `cost_bps` is a round-trip figure, so it is split evenly across the two sides.
    """
    book = json.loads(Path(path).read_text())
    entries = book.get("entries", [])
    src = str(Path(path).relative_to(ROOT)) if Path(path).is_relative_to(ROOT) else str(path)
    out = [{"type": "FUND", "book": "forward_book", "amount": notional * len(entries),
            "ts": book.get("created_at"), "source": src}]
    for e in entries:
        price = float(e["entry_price"])
        out.append({"type": "OPEN", "book": "forward_book", "source": src,
                    "id": "fb-" + e["id"], "symbol": e["symbol"],
                    "qty": notional / price, "price": price,
                    "fee_bps": float(e.get("cost_bps", 0)) / 2.0,
                    "side": e.get("direction", "LONG"),
                    "tp": e.get("take_profit"), "sl": e.get("stop_loss"),
                    "ts": e.get("entry_date")})
        res = e.get("resolution") or {}
        if e.get("status") == "RESOLVED" and res.get("exit_price") is not None:
            out.append({"type": "CLOSE", "book": "forward_book", "id": "fb-" + e["id"],
                        "price": float(res["exit_price"]), "ts": res.get("exit_date"),
                        "reason": res.get("reason"), "source": src})
    return out


def collect_events() -> list[dict]:
    events: list[dict] = []
    for path in sorted(RT_DIR.glob("*.json")):
        if path.name.endswith("_summary.json"):
            continue
        events.extend(events_from_realtime(path))
    if FORWARD_BOOK.exists():
        events.extend(events_from_forward_book(FORWARD_BOOK))
    return events


# ---------------------------------------------------------------------- prices
def last_price(symbol: str, asset_class: str = "CRYPTO") -> float:
    if str(asset_class).upper() in ("EQUITY", "ETF"):
        import yfinance as yf
        t = yf.Ticker(symbol)
        try:
            return float(t.fast_info["last_price"])
        except Exception:  # noqa: BLE001 — fall back to the last daily close
            df = yf.download(symbol, period="5d", progress=False, auto_adjust=True)
            return float(df["Close"].iloc[-1])
    from tools.ohlc_bars import binance_symbol
    sym = binance_symbol(symbol)
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={sym}"
    req = urllib.request.Request(url, headers={"User-Agent": "portfolio-tracker/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return float(json.loads(r.read())["price"])


EQUITY_SYMBOLS = {"AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META",
                  "JPM", "XOM", "UNH", "JNJ", "SPY", "QQQ", "IWM"}


def _mark_events(state: dict) -> list[dict]:
    out, ts = [], time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for view in state["books"].values():
        for p in view["positions"]:
            cls = "EQUITY" if p["symbol"] in EQUITY_SYMBOLS else "CRYPTO"
            try:
                px = last_price(p["symbol"], cls)
            except Exception as exc:  # noqa: BLE001 — a stale mark beats no book
                print(f"  mark {p['symbol']}: skipped ({type(exc).__name__}: {exc})")
                continue
            out.append({"type": "MARK", "book": p["book"], "symbol": p["symbol"],
                        "price": px, "ts": ts, "source": "quote"})
    return out


# ------------------------------------------------------------------ operations
def regenerate() -> dict:
    """Rebuild the derived views from the canonical ledger."""
    state = EventLedger(LEDGER).state()
    Data = state
    DATA.mkdir(parents=True, exist_ok=True)
    snapshot = SnapshotStore(SNAPSHOT)
    events, _ = EventLedger(LEDGER).read()
    for evt in events:
        snapshot.apply(evt)
    snapshot.save()
    trips = [{"id": c["id"], "book": c["book"], "symbol": c["symbol"],
              "qty": c["qty"], "entry": c["price"], "exit": c["exit_price"],
              "realized": c["realized"], "reason": c.get("reason"),
              "closed_at": c.get("closed_at")}
             for v in Data["books"].values() for c in v["closed"]]
    ROUNDTRIPS.write_text("".join(json.dumps(t, sort_keys=True) + "\n" for t in trips))
    Data["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    LATEST.write_text(json.dumps(Data, indent=1) + "\n")
    return Data


def cmd_sync() -> int:
    ledger = EventLedger(LEDGER)
    events = collect_events()
    added = sum(1 for e in events if ledger.append_unique(e))
    print(f"sync: {len(events)} source events, {added} new lines")
    state = regenerate()
    t = state["totals"]
    print(f"book: fund ${t['fund']:,.2f} equity ${t['equity']:,.2f} "
          f"realized ${t['realized']:,.2f} unrealized ${t['unrealized']:,.2f} "
          f"({t['n_open']} open / {t['n_closed']} closed)")
    return 0


def cmd_mark() -> int:
    ledger = EventLedger(LEDGER)
    state = ledger.state()
    if not state["totals"]["n_open"]:
        print("mark: no open positions")
        return 0
    marks = _mark_events(state)
    for evt in marks:
        ledger.append(evt)
    print(f"mark: {len(marks)} quotes appended")
    state = regenerate()
    for view in state["books"].values():
        for p in view["positions"]:
            print(f"  {p['book']:12s} {p['symbol']:9s} mark={p['mark']:<12} "
                  f"pnl={p['pnl_pct']:+.3f}% (${p['pnl_usd']:+.2f})")
    return 0


def cmd_status(as_json: bool = False) -> int:
    state = EventLedger(LEDGER).state()
    if as_json:
        print(json.dumps(state, indent=1))
        return 0
    t = state["totals"]
    print(f"BOOK  fund ${t['fund']:,.2f}  equity ${t['equity']:,.2f}  "
          f"return {t['return_pct']:+.3f}%")
    print(f"      realized ${t['realized']:+,.2f}  unrealized ${t['unrealized']:+,.2f}  "
          f"fees ${t['fees']:,.2f}  exposure ${t['exposure']:,.2f}")
    for name, view in state["books"].items():
        print(f"\n[{name}] equity ${view['equity']:,.2f} ({view['return_pct']:+.3f}%) "
              f"open={view['n_open']} closed={view['n_closed']}")
        for p in view["positions"]:
            extra = ""
            if "to_tp_pct" in p:
                extra = f" tp {p['to_tp_pct']:+.2f}% away"
            print(f"   {p['symbol']:9s} {p['side']:4s} entry={p['entry']:<12} "
                  f"mark={p['mark']:<12} pnl={p['pnl_pct']:+.3f}%{extra}")
        for c in view["closed"]:
            print(f"   {c['symbol']:9s} CLOSED {str(c.get('reason')):12s} "
                  f"net=${c['realized']:+.2f}")
    print(f"\nledger: {state['ledger']['n_events']} events, "
          f"{state['ledger']['bytes']} bytes, corrupt={state['ledger']['corrupt_lines']}")
    return 0


def verify_against_sources(state: dict) -> dict:
    """Re-derive realised P&L straight from the raw state files and compare."""
    out = {}
    for path in sorted(RT_DIR.glob("*.json")):
        if path.name.endswith("_summary.json"):
            continue
        raw = json.loads(path.read_text())
        book = raw.get("tag") or path.stem
        source_total = round(sum(c["pnl_usd"] for c in raw.get("closed", [])), 2)
        view = state["books"].get(book)
        ledger_total = round(view["realized"], 2) if view else None
        out[book] = {"source_pnl_usd": source_total, "ledger_realized_usd": ledger_total,
                     "diff": (None if ledger_total is None
                              else round(ledger_total - source_total, 2))}
    return out


def compare(events: list[dict], out_path: Path | None = None) -> dict:
    """Run the same events through all three backends and measure the differences."""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ledger = EventLedger(td / "ledger.jsonl")
        t0 = time.perf_counter()
        for evt in events:
            ledger.append(evt)
        write_ms = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter()
        lstate = ledger.state()
        load_ms = (time.perf_counter() - t0) * 1000

        snap = SnapshotStore(td / "snapshot.json")
        for evt in events:
            snap.apply(evt)
        snap.save()
        sstate = snap.state()

        trips = RoundTripBook(td / "roundtrips.jsonl")
        flat = [c for v in lstate["books"].values() for c in v["closed"]]
        trips.record([{"id": c["id"], "symbol": c["symbol"], "realized": c["realized"]}
                      for c in flat])

        # Torn write: a crash mid-append leaves a partial last line. The ledger
        # must ignore it and keep the book identical; the snapshot has no such
        # recovery path, which is the measured difference between the two.
        before = ledger.state()["totals"]
        with (td / "ledger.jsonl").open("a") as fh:
            fh.write('{"type": "OPEN", "id": "torn-wri')
        after_state = ledger.state()
        after = after_state["totals"]

        max_diff = 0.0
        for view in lstate["books"]:
            a, b = lstate["books"][view], sstate["books"].get(view, {})
            for k in ("cash", "realized", "equity"):
                if k in b:
                    max_diff = max(max_diff, abs(a[k] - b[k]))

        result = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "n_events": len(events),
            "books": sorted(lstate["books"]),
            "ledger": {"bytes": (td / "ledger.jsonl").stat().st_size,
                       "events": lstate["ledger"]["n_events"],
                       "write_ms": round(write_ms, 2), "load_ms": round(load_ms, 3),
                       "torn_write_recovered": after == before,
                       "corrupt_lines_after_torn_write": after_state["ledger"]["corrupt_lines"]},
            "snapshot": {"bytes": (td / "snapshot.json").stat().st_size,
                         "totals": sstate["totals"]},
            "roundtrip": {"bytes": (td / "roundtrips.jsonl").stat().st_size,
                          **trips.stats(),
                          "can_answer_equity": False},
            "agreement": {"max_abs_diff_usd": round(max_diff, 6),
                          "ledger_equals_snapshot": max_diff < 0.01},
            "reconciliation": verify_against_sources(lstate),
        }
        result["bytes_per_event"] = round(result["ledger"]["bytes"] / max(1, len(events)), 1)
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(json.dumps(result, indent=1) + "\n")
        print(f"wrote {out_path}")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Practical portfolio tracking (paper only)")
    ap.add_argument("cmd", choices=["sync", "mark", "status", "compare"])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.cmd == "sync":
        return cmd_sync()
    if a.cmd == "mark":
        return cmd_mark()
    if a.cmd == "status":
        return cmd_status(a.json)
    result = compare(collect_events(), Path(a.out) if a.out else None)
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
