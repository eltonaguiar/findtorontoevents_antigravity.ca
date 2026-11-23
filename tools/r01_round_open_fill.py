#!/usr/bin/env python3
"""r01_round_open_fill — the first *genuine* R01 fill.

The R01 contest opens at the US equity open (09:30 ET = 14:30Z on 2026-11-23).
Everything scored so far was scored against a 04:05Z price snapshot, which is
~10h before the open: a fill taken there is a price the entrants never had to
face, and it silently rewards whoever guessed the pre-open drift.

This tool does the only honest thing: it refuses to produce a fill until at
least one bar exists at or after the round start, per instrument. It writes an
artefact either way, so "we cannot fill yet" is a recorded result rather than a
silence, and it exits 3 (not 0) in that case so CI cannot mistake it for a
scored round.

  python3 tools/r01_round_open_fill.py \
      --picks /tmp/r01_field.json \
      --round-start 2026-11-23T14:30:00Z \
      --out reports/r01_round_open_fill_2026-11-23.json

Bar sources (repo convention, AGENTS.md "API Failover Rule"):
  * crypto      -> tools/crypto_bars.fetch_klines (Binance mirrors -> KuCoin -> CryptoCompare)
  * equity/ETF/FX/gold -> yfinance, with backoff (Yahoo 429s freely)
  * mutual funds -> no intraday series exists; never fetched, always VOID at fill

[] from a fetcher is "no evidence", never "flat price" -- the same contract
crypto_bars documents. No bar is ever synthesised or carried forward.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.crypto_bars import fetch_klines  # noqa: E402

CRYPTO = {"BTCUSD": "BTCUSDT", "ETHUSD": "ETHUSDT"}
# Yahoo's own tickers, not ours: EURUSD is EURUSD=X, USDJPY is JPY=X (USD/JPY),
# XAUUSD is the COMEX front month. Mapping is explicit so a silent rename shows
# up as "no bar" instead of as a wrong instrument's price.
YAHOO_ALIAS = {
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "JPY=X",
    "XAUUSD": "GC=F", "BRK.B": "BRK-B",
}
# Mutual funds publish a single NAV after the close. No intraday bar will ever
# exist, so they are excluded from the coverage gate and VOID by rule.
FUNDS = {"FZROX", "VBIRX", "VFIAX", "VTSAX", "VWINX", "FUSEX"}

INTERVAL = {"crypto": "5m", "yahoo": "5m"}
# Equities/ETFs are served here as DAILY bars only (the 5m feed returns empty),
# and Yahoo stamps a daily bar at 00:00 exchange-local. That stamp is before any
# round start, so using it unchanged would make a post-open fill look pre-open.
# A daily bar's open IS the session open, so it is stamped at the US open:
# 09:30 ET == 14:30Z under EST. Stated explicitly rather than inferred.
DAILY_SESSION_OPEN_UTC = "14:30:00Z"


def iso(epoch_s: float) -> str:
    return dt.datetime.fromtimestamp(epoch_s, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(value: str) -> int:
    value = value.strip().replace("Z", "+00:00")
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return int(parsed.timestamp())


def fetch_crypto(symbol: str, start_s: int, end_s: int) -> list[dict]:
    ticker = CRYPTO[symbol]
    raw = fetch_klines(ticker, INTERVAL["crypto"], start_s * 1000, end_s * 1000, limit=1000)
    return [{
        "ts": iso(b["timestamp"] / 1000.0),
        "open": b["open"], "high": b["high"], "low": b["low"], "close": b["close"],
    } for b in raw]


def fetch_yahoo(symbol: str, start_s: int, end_s: int, attempts: int = 2) -> tuple[list[dict], str]:
    """5m bars if the feed has them, else daily bars stamped at the session open."""
    ticker = YAHOO_ALIAS.get(symbol, symbol)
    last_err = ""
    for interval in (INTERVAL["yahoo"], "1d"):
        for attempt in range(attempts):
            try:
                frame = yf.Ticker(ticker).history(
                    start=iso(start_s)[:10], end=iso(end_s + 86400)[:10],
                    interval=interval, auto_adjust=False,
                )
                if frame is not None and not frame.empty:
                    out = []
                    for stamp, row in frame.iterrows():
                        if interval == "1d":
                            day = stamp.strftime("%Y-%m-%d")
                            ts = parse_ts(f"{day}T{DAILY_SESSION_OPEN_UTC}")
                        else:
                            ts = int(stamp.timestamp())
                        if ts < start_s:
                            continue
                        out.append({
                            "ts": iso(ts),
                            "open": float(row["Open"]), "high": float(row["High"]),
                            "low": float(row["Low"]), "close": float(row["Close"]),
                            "interval": interval,
                        })
                    if out:
                        return out, ""
                    last_err = f"{interval}: no bars at/after round start"
                else:
                    last_err = f"{interval}: empty frame"
            except Exception as exc:  # noqa: BLE001 — 429/parse/network all retried the same way
                last_err = f"{interval}: {type(exc).__name__}: {exc}"
            time.sleep(1.5 * (attempt + 1))
    return [], last_err


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--picks", required=True, help="aggregated picks file: {picks:[{symbol,...}]}")
    ap.add_argument("--round-start", required=True, metavar="TS")
    ap.add_argument("--out", required=True, help="fill artefact (JSON)")
    ap.add_argument("--panel-out", help="bars panel for the scorer (JSON)")
    ap.add_argument("--scorer", default="/home/eaguiar2015/antigravity_review_Nov192026/CONTEST/tools/assess_contest.py")
    ap.add_argument("--no-score", action="store_true")
    args = ap.parse_args()

    round_start = parse_ts(args.round_start)
    now = int(time.time())
    field = json.load(open(args.picks, encoding="utf-8"))
    picks = field["picks"] if isinstance(field, dict) else field
    symbols = sorted({str(p["symbol"]).upper() for p in picks})
    tradable = [s for s in symbols if s not in FUNDS]

    artefact: dict = {
        "schema": "r01.round_open_fill.v1",
        "generated_at": iso(now),
        "round_start": iso(round_start),
        "now": iso(now),
        "seconds_until_round_start": max(0, round_start - now),
        "picks": len(picks),
        "symbols": len(symbols),
        "fund_nav_picks": sum(1 for p in picks if str(p["symbol"]).upper() in FUNDS),
        "gate": "a fill needs >=1 bar with ts >= round_start, per instrument",
        "instruments": {},
    }

    # Three days of context, not one: over a weekend the last real bar is Friday's,
    # and a 24h window would silently report bars=0 instead of "last bar 3 days ago".
    # Recency is evidence; zero-bars is not the same thing as no data.
    window_start = round_start - 3 * 86400
    panel: dict[str, list[dict]] = {}
    for symbol in tradable:
        if symbol in CRYPTO:
            bars, err = fetch_crypto(symbol, window_start, now), ""
        else:
            bars, err = fetch_yahoo(symbol, window_start, now)
        post = [b for b in bars if parse_ts(b["ts"]) >= round_start]
        artefact["instruments"][symbol] = {
            "bars": len(bars),
            "post_open_bars": len(post),
            "last_bar": bars[-1]["ts"] if bars else None,
            "first_post_open_bar": post[0]["ts"] if post else None,
            "error": err or None,
        }
        if post:
            panel[symbol] = post

    for fund in sorted(set(symbols) & FUNDS):
        artefact["instruments"][fund] = {
            "bars": 0, "post_open_bars": 0, "last_bar": None,
            "first_post_open_bar": None,
            "error": "mutual fund: no intraday series exists; VOID by rule",
        }

    covered = [s for s in tradable if artefact["instruments"][s]["post_open_bars"] > 0]
    artefact["coverage"] = {
        "tradable_instruments": len(tradable),
        "with_post_open_bar": len(covered),
        "missing": [s for s in tradable if s not in covered],
    }

    if not covered:
        artefact["status"] = (
            "NOT_OPEN_YET" if now < round_start else "NO_POST_OPEN_BARS"
        )
        artefact["verdict"] = (
            f"0/{len(tradable)} tradable instruments have a bar at or after "
            f"{iso(round_start)}. Nothing is filled. This is a refusal, not a result."
        )
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(artefact, indent=2) + "\n", encoding="utf-8")
        print(f"{artefact['status']}: {artefact['verdict']}")
        print(f"artefact -> {args.out}")
        return 3

    artefact["status"] = "FILLED" if len(covered) == len(tradable) else "PARTIAL"
    panel_path = args.panel_out or str(Path(args.out).with_name("r01_round_open_panel.json"))
    Path(panel_path).write_text(json.dumps(panel, indent=2) + "\n", encoding="utf-8")
    artefact["panel"] = panel_path

    if not args.no_score:
        import subprocess
        cmd = [sys.executable, args.scorer, "--picks", args.picks,
               "--prices", panel_path, "--round-start", iso(round_start), "--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        artefact["scorer"] = {
            "cmd": " ".join(cmd), "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-2000:],
        }
        try:
            artefact["scored"] = json.loads(proc.stdout)
        except Exception:  # noqa: BLE001 — scorer prints a table, not always JSON
            pass

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(artefact, indent=2) + "\n", encoding="utf-8")
    print(f"{artefact['status']}: {len(covered)}/{len(tradable)} instruments covered")
    print(f"artefact -> {args.out}")
    return 0 if artefact["status"] == "FILLED" else 4


if __name__ == "__main__":
    raise SystemExit(main())
