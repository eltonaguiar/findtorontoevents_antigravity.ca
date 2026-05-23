"""
AI Strategy Lab — closed-loop: council proposes → MySQL stores → forward test tracks → results feed back.

Usage:
    python tools/ai_strategy_lab/council_to_forwardtest.py
    python tools/ai_strategy_lab/council_to_forwardtest.py --source pollinations --symbols AAPL TSLA NVDA
    python tools/ai_strategy_lab/council_to_forwardtest.py --leaderboard
    python tools/ai_strategy_lab/council_to_forwardtest.py --proposal-id 1 --symbols AAPL TSLA

Database target: ejaguiar1_stocks (ejaguiar1_backtests is not accessible to ejaguiar1_stocks user).
Tables: ai_strategy_proposals, ai_strategy_forward_tests
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _db_creds():
    raw = os.environ.get("DB_PASSWORDS_JSON")
    if not raw and os.path.exists(".env.dbpw"):
        raw = open(".env.dbpw").read()
    if not raw:
        raise SystemExit("DB_PASSWORDS_JSON not set — see docs/db_remediation.md")
    return json.loads(raw)


DB_CONFIG = dict(
    host="mysql.50webs.com",
    user="ejaguiar1_stocks",
    password=_db_creds()["stocks"],
    database="ejaguiar1_stocks",
    connection_timeout=15,
)


def _get_conn():
    import mysql.connector
    return mysql.connector.connect(**DB_CONFIG)


# ---------------------------------------------------------------------------
# Strategy prompt templates
# ---------------------------------------------------------------------------

STRATEGY_PROMPT_TEMPLATE = """You are a quantitative trading researcher with 20 years of experience.

Propose ONE specific, testable trading strategy for {asset_class} assets.

You MUST provide ALL of the following fields (be precise, no hand-waving):

1. STRATEGY_NAME: A short descriptive name (e.g. "5d/30d Cross-sectional Momentum")
2. SIGNAL_RULE: The exact signal calculation (e.g. "Rank stocks by 5d_return / 30d_return, buy top quintile")
3. ENTRY_CONDITION: Precise entry trigger (e.g. "rank <= 0.20 AND volume_ratio > 1.5")
4. EXIT_CONDITION: Precise exit trigger (e.g. "rank > 0.50 OR hold_days >= 20 OR SL -5%")
5. HOLD_DAYS: Expected hold period in days (integer)
6. DIRECTION: LONG, SHORT, or BOTH
7. METHODOLOGY: Why this strategy has an economic edge (1-2 sentences, causal not correlational)
8. ACADEMIC_BACKING: Cite 1-2 papers by author + year that support this (real citations only)
9. SELF_CRITIQUE: What would make this strategy FAIL? Name 2 specific failure modes.
10. FIRST_3_TRADES: What would the first 3 trades have been in the last 30 days?
    Format: DATE | SYMBOL | DIRECTION | EXPECTED_RETURN
11. CONFIDENCE: Your confidence this beats buy-and-hold after costs (0.0 to 1.0)

Format each field as: FIELD_NAME: value
"""

FEEDBACK_PROMPT_TEMPLATE = """You are a quantitative trading researcher. Review your previously proposed strategy and its live results.

ORIGINAL STRATEGY:
Name: {strategy_name}
Signal rule: {signal_rule}
Entry: {entry_condition}
Exit: {exit_condition}
Methodology: {methodology}

LIVE FORWARD TEST RESULTS (last {n_trades} trades):
Win rate: {win_rate:.1%}
Profit factor: {profit_factor:.2f}
Best trade: +{best_pnl:.2f}%
Worst trade: {worst_pnl:.2f}%

QUESTION: Based on these results, how should the strategy be improved?
Provide specific, actionable parameter changes. If WR < 50% or PF < 1.2, recommend KILL or major revision.
"""


# ---------------------------------------------------------------------------
# Parser: convert AI free-text response to structured strategy
# ---------------------------------------------------------------------------

def parse_strategy_response(response: str, ai_source: str, asset_class: str) -> dict[str, Any]:
    """Parse AI strategy response into structured fields."""
    def extract(field: str) -> str:
        pattern = rf"{field}:\s*(.+?)(?=\n[A-Z_]+:|$)"
        m = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else ""

    strategy_name = extract("STRATEGY_NAME") or f"AI-proposed strategy ({ai_source})"
    signal_rule = extract("SIGNAL_RULE")
    entry_condition = extract("ENTRY_CONDITION")
    exit_condition = extract("EXIT_CONDITION")
    methodology = extract("METHODOLOGY")
    academic_backing = extract("ACADEMIC_BACKING")

    # Hold days: extract integer
    hold_str = extract("HOLD_DAYS")
    try:
        hold_days = int(re.search(r"\d+", hold_str).group())
    except Exception:
        hold_days = 20

    # Direction: normalize
    dir_raw = extract("DIRECTION").upper()
    direction = "BOTH" if "BOTH" in dir_raw else ("SHORT" if "SHORT" in dir_raw else "LONG")

    # Confidence: extract float
    conf_str = extract("CONFIDENCE")
    try:
        confidence = float(re.search(r"[\d.]+", conf_str).group())
        if confidence > 1.0:
            confidence = confidence / 100.0
        confidence = max(0.0, min(1.0, confidence))
    except Exception:
        confidence = 0.5

    return {
        "ai_source": ai_source,
        "asset_class": asset_class,
        "strategy_name": strategy_name,
        "signal_rule": signal_rule,
        "entry_condition": entry_condition,
        "exit_condition": exit_condition,
        "hold_days": hold_days,
        "direction": direction,
        "methodology": methodology,
        "academic_backing": academic_backing,
        "confidence_score": confidence,
        "raw_response": response,
    }


# ---------------------------------------------------------------------------
# propose_strategy: query AI, parse, store in MySQL
# ---------------------------------------------------------------------------

async def _ask_pollinations(prompt: str, timeout: int = 30) -> str:
    """Query Pollinations.ai (free, no auth required)."""
    from urllib.parse import quote
    url = "https://text.pollinations.ai/" + quote(prompt, safe="")
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url)
        if r.status_code == 200 and r.text.strip():
            return r.text.strip()
    return ""


async def _ask_swarm_engine(prompt: str, engine: str = "deepseek", timeout: int = 60) -> str:
    """Query a swarm engine via the worker_runner subprocess."""
    import subprocess
    import tempfile
    worker = REPO_ROOT / "tools" / "swarm" / "worker_runner.py"
    if not worker.exists():
        return ""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(prompt)
        prompt_file = f.name
    try:
        result = subprocess.run(
            [sys.executable, str(worker), "--engine", engine, "--prompt-file", prompt_file],
            capture_output=True, text=True, timeout=timeout,
        )
        out = result.stdout.strip()
        # Worker outputs JSON; extract response field if present
        try:
            data = json.loads(out)
            return data.get("response", "") or data.get("content", "") or out
        except Exception:
            return out
    except Exception as e:
        return f"[engine error: {e}]"
    finally:
        try:
            os.unlink(prompt_file)
        except Exception:
            pass


async def propose_strategy(
    ai_source: str = "pollinations",
    asset_class: str = "EQUITY",
    prompt_template: str = STRATEGY_PROMPT_TEMPLATE,
    hypothesis_id: str | None = None,
) -> int | None:
    """Query an AI for a strategy proposal, parse it, store in MySQL.

    Returns the inserted row ID, or None if insertion failed.
    """
    prompt = prompt_template.format(asset_class=asset_class)

    print(f"[propose_strategy] querying {ai_source} for {asset_class} strategy...")
    t0 = time.time()

    if ai_source in ("pollinations",):
        raw = await _ask_pollinations(prompt)
    elif ai_source in ("deepseek", "kilo", "xai", "cerebras", "groq"):
        raw = await _ask_swarm_engine(prompt, engine=ai_source)
    else:
        print(f"[propose_strategy] unknown source {ai_source!r}, falling back to pollinations")
        raw = await _ask_pollinations(prompt)

    elapsed = round(time.time() - t0, 1)

    if not raw or len(raw) < 50:
        print(f"[propose_strategy] {ai_source} returned empty/short response ({elapsed}s)")
        return None

    print(f"[propose_strategy] got {len(raw)} chars from {ai_source} in {elapsed}s")

    parsed = parse_strategy_response(raw, ai_source=ai_source, asset_class=asset_class)

    # Generate hypothesis_id if not provided
    if not hypothesis_id:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        hypothesis_id = f"AI-{ai_source[:4].upper()}-{ts}"

    conn = _get_conn()
    cur = conn.cursor()
    sql = """
        INSERT INTO ai_strategy_proposals
            (ai_source, asset_class, strategy_name, signal_rule, entry_condition,
             exit_condition, hold_days, direction, methodology, academic_backing,
             confidence_score, hypothesis_id, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'proposed')
    """
    cur.execute(sql, (
        parsed["ai_source"], parsed["asset_class"], parsed["strategy_name"],
        parsed["signal_rule"], parsed["entry_condition"], parsed["exit_condition"],
        parsed["hold_days"], parsed["direction"], parsed["methodology"],
        parsed["academic_backing"], parsed["confidence_score"], hypothesis_id,
    ))
    conn.commit()
    row_id = cur.lastrowid
    conn.close()

    print(f"[propose_strategy] stored proposal ID={row_id} hypothesis={hypothesis_id}")
    return row_id


# ---------------------------------------------------------------------------
# run_forward_test: yfinance-based forward test, store results in MySQL
# ---------------------------------------------------------------------------

def run_forward_test(
    proposal_id: int,
    symbols: list[str],
    start_date: str | None = None,
    lookback_days: int = 30,
) -> list[dict]:
    """Run a simple yfinance-based forward test for a proposal.

    For each symbol, fetches OHLCV, applies the signal from the proposal's
    signal_rule (momentum proxy: 5d/30d ratio), simulates entry at close,
    exit at hold_days or end-of-window, and stores results.

    Returns list of result dicts.
    """
    import yfinance as yf

    if start_date is None:
        dt = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        start_date = dt.strftime("%Y-%m-%d")

    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT hold_days, direction, signal_rule FROM ai_strategy_proposals WHERE id=%s",
        (proposal_id,)
    )
    row = cur.fetchone()
    if not row:
        print(f"[forward_test] proposal {proposal_id} not found")
        conn.close()
        return []
    hold_days, direction, signal_rule = row
    conn.close()

    print(f"[forward_test] proposal={proposal_id} symbols={symbols} start={start_date} hold={hold_days}d")

    results = []
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            # Fetch enough history for momentum calculation
            hist = ticker.history(
                start=(datetime.fromisoformat(start_date) - timedelta(days=60)).strftime("%Y-%m-%d"),
                end=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            )
            if hist.empty or len(hist) < 10:
                print(f"  [SKIP] {symbol} — insufficient history")
                continue

            # Simple momentum signal: 5d_return / 30d_return
            closes = hist["Close"]
            if len(closes) >= 30:
                ret_5d = (closes.iloc[-1] - closes.iloc[-5]) / closes.iloc[-5]
                ret_30d = (closes.iloc[-1] - closes.iloc[-30]) / closes.iloc[-30]
                signal_value = float(ret_5d / ret_30d) if ret_30d != 0 else 0.0
            else:
                ret_5d = (closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0]
                signal_value = float(ret_5d)

            # Simulate entry at the start_date close (or first available)
            start_mask = hist.index >= start_date
            if not start_mask.any():
                print(f"  [SKIP] {symbol} — no data after {start_date}")
                continue

            entry_bar = hist[start_mask].iloc[0]
            entry_price = float(entry_bar["Close"])
            entry_date = entry_bar.name.date().isoformat()

            # Simulate exit at hold_days later (or end of data)
            future_bars = hist[start_mask]
            if len(future_bars) >= hold_days:
                exit_bar = future_bars.iloc[hold_days - 1]
            else:
                exit_bar = future_bars.iloc[-1]

            exit_price = float(exit_bar["Close"])
            exit_date = exit_bar.name.date().isoformat()

            direction_mult = -1.0 if direction == "SHORT" else 1.0
            pnl_pct = (exit_price - entry_price) / entry_price * direction_mult * 100
            outcome = "OPEN" if exit_date == datetime.now(timezone.utc).strftime("%Y-%m-%d") \
                else ("WIN" if pnl_pct > 0 else "LOSS")

            result = {
                "proposal_id": proposal_id,
                "symbol": symbol,
                "entry_date": entry_date,
                "exit_date": exit_date,
                "entry_price": round(entry_price, 4),
                "exit_price": round(exit_price, 4),
                "pnl_pct": round(pnl_pct, 4),
                "outcome": outcome,
                "signal_value": round(signal_value, 4),
                "notes": f"signal_rule='{signal_rule[:80]}'; auto-sim {hold_days}d hold",
            }
            results.append(result)
            print(f"  [{outcome:4s}] {symbol:6s} entry={entry_price:.2f} exit={exit_price:.2f} pnl={pnl_pct:+.2f}%")
            time.sleep(0.2)  # rate limit

        except Exception as e:
            print(f"  [ERR]  {symbol} — {e}")
            continue

    if results:
        conn = _get_conn()
        cur = conn.cursor()
        sql = """
            INSERT INTO ai_strategy_forward_tests
                (proposal_id, symbol, entry_date, exit_date, entry_price, exit_price,
                 pnl_pct, outcome, signal_value, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        for r in results:
            cur.execute(sql, (
                r["proposal_id"], r["symbol"], r["entry_date"], r["exit_date"],
                r["entry_price"], r["exit_price"], r["pnl_pct"], r["outcome"],
                r["signal_value"], r["notes"],
            ))
        conn.commit()
        conn.close()
        print(f"[forward_test] stored {len(results)} trades for proposal {proposal_id}")

    return results


# ---------------------------------------------------------------------------
# get_leaderboard: rank AI sources by WR/PF of their proposed strategies
# ---------------------------------------------------------------------------

def get_leaderboard() -> list[dict]:
    """Rank AI sources by WR/PF of their forward-tested proposals."""
    conn = _get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT
            p.ai_source,
            COUNT(t.id) AS n_trades,
            SUM(CASE WHEN t.outcome = 'WIN' THEN 1 ELSE 0 END) AS n_wins,
            AVG(t.pnl_pct) AS avg_pnl,
            SUM(CASE WHEN t.pnl_pct > 0 THEN t.pnl_pct ELSE 0 END) AS gross_wins,
            SUM(CASE WHEN t.pnl_pct < 0 THEN ABS(t.pnl_pct) ELSE 0 END) AS gross_losses
        FROM ai_strategy_proposals p
        JOIN ai_strategy_forward_tests t ON p.id = t.proposal_id
        WHERE t.outcome IN ('WIN', 'LOSS')
        GROUP BY p.ai_source
        ORDER BY n_wins / n_trades DESC
    """)
    rows = cur.fetchall()
    conn.close()

    board = []
    for r in rows:
        n = r["n_trades"] or 0
        wins = r["n_wins"] or 0
        wr = wins / n if n > 0 else 0.0
        gw = float(r["gross_wins"] or 0)
        gl = float(r["gross_losses"] or 0)
        pf = gw / gl if gl > 0 else (10.0 if gw > 0 else 0.0)
        board.append({
            "ai_source": r["ai_source"],
            "n_trades": n,
            "win_rate": round(wr, 4),
            "profit_factor": round(pf, 3),
            "avg_pnl_pct": round(float(r["avg_pnl"] or 0), 4),
            "tier": "T1" if pf >= 2.0 and wr >= 0.55 else
                    "T2" if pf >= 1.5 and wr >= 0.50 else
                    "T3" if pf >= 1.3 and wr >= 0.45 else "BELOW",
        })

    if board:
        print("\n=== AI STRATEGY LAB LEADERBOARD ===")
        print(f"{'Source':<30} {'N':>6} {'WR':>8} {'PF':>8} {'avgPnL':>8} {'Tier'}")
        print("-" * 70)
        for b in board:
            print(f"{b['ai_source']:<30} {b['n_trades']:>6} {b['win_rate']:>8.1%} "
                  f"{b['profit_factor']:>8.2f} {b['avg_pnl_pct']:>8.2f}% {b['tier']}")
    else:
        print("[leaderboard] no resolved forward tests yet")

    return board


# ---------------------------------------------------------------------------
# generate_feedback: build a feedback prompt from forward test results
# ---------------------------------------------------------------------------

def generate_feedback_prompt(proposal_id: int) -> str:
    """Build a feedback prompt showing an AI its strategy's live results."""
    conn = _get_conn()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM ai_strategy_proposals WHERE id=%s", (proposal_id,))
    proposal = cur.fetchone()
    if not proposal:
        conn.close()
        return ""

    cur.execute("""
        SELECT pnl_pct, outcome FROM ai_strategy_forward_tests
        WHERE proposal_id=%s AND outcome IN ('WIN','LOSS')
    """, (proposal_id,))
    trades = cur.fetchall()
    conn.close()

    if not trades:
        return f"[feedback] no resolved trades yet for proposal {proposal_id}"

    pnls = [float(t["pnl_pct"]) for t in trades]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    wr = wins / n
    gross_wins = sum(p for p in pnls if p > 0)
    gross_losses = abs(sum(p for p in pnls if p < 0))
    pf = gross_wins / gross_losses if gross_losses > 0 else 10.0

    return FEEDBACK_PROMPT_TEMPLATE.format(
        strategy_name=proposal["strategy_name"],
        signal_rule=proposal["signal_rule"],
        entry_condition=proposal["entry_condition"],
        exit_condition=proposal["exit_condition"],
        methodology=proposal["methodology"],
        n_trades=n,
        win_rate=wr,
        profit_factor=pf,
        best_pnl=max(pnls),
        worst_pnl=min(pnls),
    )


# ---------------------------------------------------------------------------
# main: full cycle demo
# ---------------------------------------------------------------------------

async def _full_cycle(source: str, symbols: list[str]) -> None:
    print(f"\n{'='*60}")
    print(" AI STRATEGY LAB — FULL CYCLE RUN")
    print(f" Source: {source} | Symbols: {symbols}")
    print(f" Time: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")

    # Step 1: propose
    proposal_id = await propose_strategy(ai_source=source, asset_class="EQUITY")
    if proposal_id is None:
        print("[cycle] proposal failed — aborting")
        return

    # Step 2: forward test
    results = run_forward_test(proposal_id, symbols=symbols)
    if not results:
        print("[cycle] no forward test results — check yfinance connectivity")

    # Step 3: leaderboard
    get_leaderboard()

    # Step 4: feedback prompt (if we have enough trades)
    feedback = generate_feedback_prompt(proposal_id)
    if feedback and not feedback.startswith("[feedback]"):
        print("\n=== FEEDBACK PROMPT (send back to AI) ===")
        print(feedback[:500] + "..." if len(feedback) > 500 else feedback)

    print(f"\n[cycle] done. proposal_id={proposal_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Strategy Lab — closed-loop runner")
    parser.add_argument("--source", default="pollinations",
                        help="AI source to query (pollinations, deepseek, kilo, xai, cerebras, groq)")
    parser.add_argument("--asset-class", default="EQUITY",
                        help="Asset class to propose strategy for")
    parser.add_argument("--symbols", nargs="+", default=["AAPL", "TSLA"],
                        help="Symbols to forward-test against")
    parser.add_argument("--proposal-id", type=int, default=None,
                        help="Run forward test on an existing proposal ID (skip proposal step)")
    parser.add_argument("--leaderboard", action="store_true",
                        help="Print leaderboard and exit")
    parser.add_argument("--feedback", type=int, default=None,
                        help="Print feedback prompt for a proposal ID")
    args = parser.parse_args()

    if args.leaderboard:
        get_leaderboard()
        return

    if args.feedback is not None:
        print(generate_feedback_prompt(args.feedback))
        return

    if args.proposal_id is not None:
        run_forward_test(args.proposal_id, symbols=args.symbols)
        get_leaderboard()
        return

    asyncio.run(_full_cycle(source=args.source, symbols=args.symbols))


if __name__ == "__main__":
    main()
