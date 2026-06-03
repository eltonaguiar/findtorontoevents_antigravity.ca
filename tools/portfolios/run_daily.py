"""EOD orchestrator for the AI-model paper portfolios (Phase 3).

NOTE — SNAPSHOT-RESOLVER ARTIFACT + TOURNAMENT-SOURCED (2026-06-03): this portfolio
consumes AI-tournament picks and resolves via daily-close TP/SL with no intrabar OHLC
path, so its WR/PF is inflated (intraday SL touches missed). Do not size up on these
numbers. See docs/RESOLVER_SNAPSHOT_ARTIFACT_AFFECTED_PORTFOLIOS_2026-06-03.md


Pipeline (docs/DESIGN_AI_MODEL_HEDGE_FUND_PORTFOLIOS_2026-05-29.md §5/§7):

  1. Load active portfolios from PF_PORTFOLIO. If empty, SEED them: for each
     edge-eligible model on the AI-tournament leaderboard (``pf_ci_lo > 1.0``),
     create model x appetite books at $100k starting NAV. Seeding is idempotent
     (UNIQUE portfolio_key + INSERT ... ON DUPLICATE / INSERT OR IGNORE).
  2. For each active portfolio:
       a. ingest new eligible tournament picks (that model's recent picks not
          already held) through engine.evaluate_entry  -> PF_POSITION rows
       b. mark + evaluate_exit all open positions      -> close rows on exit
       c. write a PF_NAV_SNAPSHOT for asof_date
       d. log PF_RULE_EVENT for rejects / exits / breaker
       e. compute PF_DAILY_METRICS (sharpe_30d, max_dd, pf_to_date, wr_to_date)
  3. Idempotent on asof_date: re-running a day overwrites that day, never
     double-counts (NAV/metrics keyed by (portfolio_id, asof_date); a re-run
     deletes that day's rule events + same-day-opened positions first).

SAFETY: defaults to --dry-run, which runs the FULL logic against an in-memory
sqlite DB seeded from the local/remote tournament JSONs and prints what WOULD
happen. The live MySQL is touched ONLY with --apply.

Usage:
    python tools/portfolios/run_daily.py                 # dry-run (default)
    python tools/portfolios/run_daily.py --dry-run
    python tools/portfolios/run_daily.py --apply         # write to MySQL
    python tools/portfolios/run_daily.py --asof 2026-05-29
    python tools/portfolios/run_daily.py --picks /tmp/picks.json --leaderboard /tmp/lb.json

Env (same convention as tools/portfolios/init_db.py):
    DB_HOST_STOCKS / DB_USER_STOCKS / DB_PASS_STOCKS / DB_NAME_STOCKS
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.portfolios import engine, prices  # noqa: E402
from tools.portfolios.profiles import load_profiles  # noqa: E402

DATA_DIR = REPO_ROOT / "audit_dashboard" / "data"
DEFAULT_PICKS = DATA_DIR / "ai_tournament_picks_latest.json"
DEFAULT_LEADERBOARD = DATA_DIR / "ai_tournament_leaderboard.json"

APPETITES = ("conservative", "balanced", "aggressive")
STARTING_NAV = 100000.0
PF_CI_LO_EDGE_BAR = 1.0
# How many recent OPEN picks per model we consider for ingestion each run.
MAX_INGEST_PER_MODEL = 25
# MA-window per appetite is read from the profile (trend_filter_ma_days);
# realized-vol / ATR lookback for sizing.
VOL_WINDOW = 20
HISTORY_LOOKBACK = 60


# --------------------------------------------------------------------------- #
# DB abstraction: works for both pymysql (live) and sqlite3 (dry-run in-memory)
# --------------------------------------------------------------------------- #
class DB:
    """Thin wrapper presenting a ``?``-style paramstyle for both backends.

    The live backend uses pymysql (``%s`` paramstyle) on the real schema;
    the dry-run backend uses an in-memory sqlite created from a translated
    schema. We author all SQL with ``?`` placeholders and translate to ``%s``
    for MySQL.
    """

    def __init__(self, backend: str):
        self.backend = backend  # 'mysql' | 'sqlite'
        self.conn = None

    # --- connection ---
    def connect_mysql(self):
        import pymysql

        self.conn = pymysql.connect(
            host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
            user=os.environ.get("DB_USER_STOCKS", "ejaguiar1_stocks"),
            password=os.environ.get("DB_PASS_STOCKS", "stocks1234560"),
            database=os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"),
            port=3306, connect_timeout=20, autocommit=False,
        )

    def connect_sqlite(self):
        import sqlite3

        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._build_sqlite_schema()

    def _build_sqlite_schema(self):
        # Minimal sqlite mirror of schema.sql (no FKs/JSON enforcement needed).
        ddl = [
            """CREATE TABLE PF_PORTFOLIO (
                id INTEGER PRIMARY KEY AUTOINCREMENT, portfolio_key TEXT UNIQUE,
                model_id TEXT, risk_appetite TEXT, kind TEXT DEFAULT 'model',
                starting_nav REAL DEFAULT 100000, status TEXT DEFAULT 'active',
                config_snapshot TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE PF_POSITION (
                id INTEGER PRIMARY KEY AUTOINCREMENT, portfolio_id INTEGER,
                symbol TEXT, asset_class TEXT, direction TEXT,
                status TEXT DEFAULT 'open', entry_date TEXT, entry_price REAL,
                qty REAL, weight_at_entry REAL, tp_price REAL, sl_price REAL,
                exit_date TEXT, exit_price REAL, exit_reason TEXT,
                realized_pnl_pct REAL, realized_pnl_usd REAL, source_pick_id TEXT,
                entry_reason TEXT, sizing_reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE PF_NAV_SNAPSHOT (
                id INTEGER PRIMARY KEY AUTOINCREMENT, portfolio_id INTEGER,
                asof_date TEXT, nav_usd REAL, cash_usd REAL,
                gross_exposure_pct REAL, n_open INTEGER, daily_return_pct REAL,
                drawdown_pct REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(portfolio_id, asof_date))""",
            """CREATE TABLE PF_RULE_EVENT (
                id INTEGER PRIMARY KEY AUTOINCREMENT, portfolio_id INTEGER,
                asof_date TEXT, event_type TEXT, symbol TEXT, detail TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE PF_DAILY_METRICS (
                id INTEGER PRIMARY KEY AUTOINCREMENT, portfolio_id INTEGER,
                asof_date TEXT, sharpe_30d REAL, sortino_30d REAL, max_dd REAL,
                cagr REAL, vol_realized REAL, pf_to_date REAL, wr_to_date REAL,
                turnover REAL, exposure_by_class TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(portfolio_id, asof_date))""",
        ]
        cur = self.conn.cursor()
        for stmt in ddl:
            cur.execute(stmt)
        self.conn.commit()

    # --- query helpers (author with ? placeholders) ---
    def _sql(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.backend == "mysql" else sql

    def execute(self, sql: str, params=()):
        cur = self.conn.cursor()
        cur.execute(self._sql(sql), params)
        return cur

    def query(self, sql: str, params=()) -> list[dict]:
        cur = self.execute(sql, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def lastrowid(self, cur) -> int:
        return cur.lastrowid

    def commit(self):
        self.conn.commit()

    def rollback(self):
        if self.conn:
            self.conn.rollback()

    def close(self):
        if self.conn:
            self.conn.close()


# --------------------------------------------------------------------------- #
# JSON loaders
# --------------------------------------------------------------------------- #
def _load_json(path: Path):
    with open(path) as fh:
        return json.load(fh)


def load_leaderboard(path: Path) -> list[dict]:
    raw = _load_json(path)
    if isinstance(raw, dict):
        return raw.get("models") or []
    return raw or []


def load_picks(path: Path) -> list[dict]:
    raw = _load_json(path)
    if isinstance(raw, dict):
        return raw.get("picks") or []
    return raw or []


def edge_eligible_models(models: list[dict]) -> list[dict]:
    out = []
    for m in models:
        ci = m.get("pf_ci_lo")
        if isinstance(ci, (int, float)) and ci > PF_CI_LO_EDGE_BAR:
            out.append(m)
    return out


def edge_signal_for(model: dict) -> float:
    """Map a model's overall pf_ci_lo to a [0,1] edge_signal for sizing.

    pf_ci_lo of 1.0 -> 0; saturates toward 1.0 as pf_ci_lo rises. Falls back
    to a thin-CI proxy (wr) when pf_ci_lo missing.
    """
    ci = model.get("pf_ci_lo")
    if isinstance(ci, (int, float)) and ci > 1.0:
        # logistic-ish squash: pf_ci_lo 1.0->0, 2.0->~0.5, 3.0->~0.67
        return max(0.0, min(1.0, (ci - 1.0) / (ci)))
    wr = model.get("wr")
    if isinstance(wr, (int, float)):
        return max(0.0, min(1.0, wr))
    return 0.0


# --------------------------------------------------------------------------- #
# Seeding
# --------------------------------------------------------------------------- #
def seed_portfolios(db: DB, models: list[dict], profiles: dict) -> int:
    """Idempotently create model x appetite portfolios for edge-eligible models."""
    created = 0
    for m in edge_eligible_models(models):
        model_id = m.get("model_id")
        if not model_id:
            continue
        for appetite in APPETITES:
            key = f"{model_id}__{appetite}"
            existing = db.query(
                "SELECT id FROM PF_PORTFOLIO WHERE portfolio_key=?", (key,))
            if existing:
                continue
            cfg = json.dumps({
                "appetite": appetite,
                "edge_signal": round(edge_signal_for(m), 4),
                "pf_ci_lo": m.get("pf_ci_lo"),
                "seeded_from": "ai_tournament_leaderboard.json",
            })
            db.execute(
                "INSERT INTO PF_PORTFOLIO "
                "(portfolio_key, model_id, risk_appetite, kind, starting_nav, "
                " status, config_snapshot) VALUES (?,?,?,?,?,?,?)",
                (key, model_id, appetite, "model", STARTING_NAV, "active", cfg))
            created += 1
    db.commit()
    return created


# --------------------------------------------------------------------------- #
# Lifecycle per portfolio
# --------------------------------------------------------------------------- #
def _norm_dir(d: str) -> str:
    d = (d or "").strip().lower()
    return "short" if d in ("short", "sell") else "long"


# Vendor-route aliases for portfolios whose model_id is a re-branding of an
# upstream pick-emitter (same base model, different vendor route). The
# leaderboard shows them as separate entries to track per-route reliability,
# but they share the underlying picks. 2026-06-03: aimlapi_gpt4o and
# gh_models_gpt4o both emit nothing under their own ID — they pull from
# `gpt4o` (the canonical OpenAI gpt-4o emitter, 406 picks/day).
MODEL_PICK_ALIASES: dict[str, str] = {
    "aimlapi_gpt4o": "gpt4o",
    "gh_models_gpt4o": "gpt4o",
}


def model_picks(picks: list[dict], model_id: str,
                allowed_classes: set | None = None) -> list[dict]:
    """Return up to MAX_INGEST_PER_MODEL newest OPEN picks for this model.

    2026-06-03 fix: previously sliced [:MAX_INGEST_PER_MODEL] BEFORE the
    risk-profile asset-class allowlist was applied downstream. Result: a
    portfolio with a narrow allowlist (e.g. conservative=[BOND,ETF,EQUITY,FOREX])
    could get all 25 newest picks rejected as `class_not_allowed` while
    older eligible picks were never considered.
    Example: gemini_2_5_flash__conservative — 39 OPEN picks total of which
    16 were allowlist-eligible (10 EQUITY + 3 BOND + 2 ETF + 1 FOREX), but
    the 25 newest were all PENNY/COMMODITY/CRYPTO → 0 positions opened.
    Pass `allowed_classes` (the appetite's asset_class_allowlist) to filter
    BEFORE slicing so the 25-cap is spent on candidates that have a chance.
    """
    target = MODEL_PICK_ALIASES.get(model_id, model_id)
    out = [p for p in picks if (p.get("model_id") == target
                                and str(p.get("status", "")).upper() == "OPEN")]
    if allowed_classes:
        allowed_upper = {str(c).upper() for c in allowed_classes}
        out = [p for p in out
               if str(p.get("asset_class", "")).upper() in allowed_upper]
    # newest-first by submitted_at
    out.sort(key=lambda p: p.get("submitted_at", ""), reverse=True)
    return out[:MAX_INGEST_PER_MODEL]


def open_positions(db: DB, portfolio_id: int) -> list[dict]:
    return db.query(
        "SELECT * FROM PF_POSITION WHERE portfolio_id=? AND status='open'",
        (portfolio_id,))


def _market_for(symbol: str, asset_class: str, ma_days, allow_net: bool) -> dict:
    """Build the engine ``market`` dict. In dry-run we still try the network
    (read-only) so the lifecycle is exercised, but tolerate total failure."""
    if not allow_net:
        return {"price": None, "ma_value": None, "realized_vol": None, "atr": None}
    hist = prices.get_history(symbol, asset_class, lookback=HISTORY_LOOKBACK)
    price = hist[-1] if hist else None
    ma_value = None
    if ma_days:
        ma_value = prices.get_ma(symbol, asset_class, int(ma_days))
    from tools.portfolios.sizing import realized_vol
    rvol = realized_vol(hist, window=VOL_WINDOW) if hist else None
    atr = prices.get_atr(symbol, asset_class, period=14)
    return {"price": price, "ma_value": ma_value, "realized_vol": rvol, "atr": atr}


def portfolio_state(db: DB, portfolio_id: int, starting_nav: float,
                    marks: dict) -> dict:
    """Compute current nav/cash/open_positions from DB + fresh marks.

    NAV = cash + sum(market_value of open positions). Cash is starting_nav
    minus net deployed cost basis plus realized PnL from closed trades.
    """
    opens = open_positions(db, portfolio_id)
    closed = db.query(
        "SELECT realized_pnl_usd FROM PF_POSITION "
        "WHERE portfolio_id=? AND status='closed'", (portfolio_id,))
    realized = sum(float(c.get("realized_pnl_usd") or 0.0) for c in closed)

    deployed_cost = 0.0
    mkt_value = 0.0
    state_positions = []
    for p in opens:
        qty = float(p.get("qty") or 0.0)
        entry = float(p.get("entry_price") or 0.0)
        deployed_cost += qty * entry
        cur_price = marks.get(p["symbol"], entry)
        mkt_value += qty * (cur_price if cur_price else entry)
        state_positions.append({
            "symbol": p["symbol"],
            "asset_class": p["asset_class"],
            "direction": p["direction"],
            "entry_price": entry,
            "qty": qty,
            "weight_at_entry": float(p.get("weight_at_entry") or 0.0),
            "tp_price": p.get("tp_price"),
            "sl_price": p.get("sl_price"),
            "entry_date": p.get("entry_date"),
        })
    cash = starting_nav - deployed_cost + realized
    nav = cash + mkt_value
    # crude MTD proxy = total return vs starting nav (good enough for the breaker)
    mtd = (nav - starting_nav) / starting_nav * 100.0 if starting_nav else 0.0
    return {"nav_usd": nav, "cash_usd": cash,
            "open_positions": state_positions, "mtd_return_pct": mtd}


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def compute_metrics(db: DB, portfolio_id: int) -> dict:
    navs = db.query(
        "SELECT asof_date, nav_usd, daily_return_pct FROM PF_NAV_SNAPSHOT "
        "WHERE portfolio_id=? ORDER BY asof_date ASC", (portfolio_id,))
    rets = [float(n["daily_return_pct"] or 0.0) / 100.0 for n in navs
            if n.get("daily_return_pct") is not None]
    nav_series = [float(n["nav_usd"]) for n in navs]

    sharpe = None
    if len(rets) >= 2:
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        sd = math.sqrt(var)
        if sd > 0:
            sharpe = (mean / sd) * math.sqrt(252)

    max_dd = None
    if nav_series:
        peak = nav_series[0]
        mdd = 0.0
        for v in nav_series:
            peak = max(peak, v)
            if peak > 0:
                mdd = min(mdd, (v - peak) / peak)
        max_dd = mdd * 100.0

    closed = db.query(
        "SELECT realized_pnl_usd FROM PF_POSITION "
        "WHERE portfolio_id=? AND status='closed'", (portfolio_id,))
    gains = sum(float(c["realized_pnl_usd"]) for c in closed
                if float(c.get("realized_pnl_usd") or 0.0) > 0)
    losses = -sum(float(c["realized_pnl_usd"]) for c in closed
                  if float(c.get("realized_pnl_usd") or 0.0) < 0)
    pf = (gains / losses) if losses > 0 else (None if gains == 0 else 999.0)
    n_closed = len(closed)
    n_win = sum(1 for c in closed if float(c.get("realized_pnl_usd") or 0.0) > 0)
    wr = (n_win / n_closed) if n_closed else None

    # CAGR — annualized geometric NAV growth (EAGLE-3 action #7).
    # Schema columns PF_DAILY_METRICS.cagr + .sortino_30d existed but were
    # never populated, leaving CAGR + SORTINO 30D cells on /audit/pf.html
    # drill pages blank.
    cagr = None
    if nav_series and len(nav_series) >= 2:
        n_days = len(nav_series)
        start = nav_series[0]
        end = nav_series[-1]
        if start > 0 and end > 0:
            try:
                cagr = ((end / start) ** (252.0 / n_days) - 1.0) * 100.0
            except (OverflowError, ZeroDivisionError):
                cagr = None

    # Sortino 30D — like Sharpe but only penalizes downside deviation
    # (MAR=0). Same window as sharpe_30d above.
    sortino = None
    if len(rets) >= 2:
        downside = [r for r in rets if r < 0]
        if downside:
            mean_r = sum(rets) / len(rets)
            d_var = sum(r * r for r in downside) / len(downside)
            d_sd = math.sqrt(d_var)
            if d_sd > 0:
                sortino = (mean_r / d_sd) * math.sqrt(252)
        elif rets:
            # No downside days in window -> sortino is mathematically
            # infinite; sentinel so downstream consumers can distinguish
            # "no losing days" from "no data".
            sortino = 999.0

    return {"sharpe_30d": sharpe, "max_dd": max_dd, "pf_to_date": pf,
            "wr_to_date": wr, "cagr": cagr, "sortino_30d": sortino}


# --------------------------------------------------------------------------- #
# Idempotency: wipe a day before re-writing it
# --------------------------------------------------------------------------- #
def clear_day(db: DB, portfolio_id: int, asof: str):
    db.execute("DELETE FROM PF_NAV_SNAPSHOT WHERE portfolio_id=? AND asof_date=?",
               (portfolio_id, asof))
    db.execute("DELETE FROM PF_DAILY_METRICS WHERE portfolio_id=? AND asof_date=?",
               (portfolio_id, asof))
    db.execute("DELETE FROM PF_RULE_EVENT WHERE portfolio_id=? AND asof_date=?",
               (portfolio_id, asof))
    # remove positions opened today (re-run re-opens them) and re-open positions
    # that were closed today.
    db.execute("DELETE FROM PF_POSITION WHERE portfolio_id=? AND entry_date=?",
               (portfolio_id, asof))
    db.execute(
        "UPDATE PF_POSITION SET status='open', exit_date=NULL, exit_price=NULL, "
        "exit_reason=NULL, realized_pnl_pct=NULL, realized_pnl_usd=NULL "
        "WHERE portfolio_id=? AND exit_date=?", (portfolio_id, asof))


def log_event(db: DB, portfolio_id: int, asof: str, event_type: str,
              symbol, detail: dict):
    db.execute(
        "INSERT INTO PF_RULE_EVENT (portfolio_id, asof_date, event_type, symbol, "
        "detail) VALUES (?,?,?,?,?)",
        (portfolio_id, asof, event_type, symbol, json.dumps(detail)))


# --------------------------------------------------------------------------- #
# Main per-portfolio run
# --------------------------------------------------------------------------- #
def run_portfolio(db: DB, pf: dict, picks: list[dict], profiles: dict,
                  asof: str, allow_net: bool, summary: dict):
    pid = pf["id"]
    appetite_name = pf["risk_appetite"]
    appetite = profiles[appetite_name]
    ma_days = appetite.get("trend_filter_ma_days")
    starting_nav = float(pf.get("starting_nav") or STARTING_NAV)
    frozen = pf.get("status") == "frozen"

    clear_day(db, pid, asof)

    # collect symbols we'll need marks for (open positions + candidate picks)
    opens = open_positions(db, pid)
    _allowed_classes = appetite.get("asset_class_allowlist") or None
    cand_picks = [] if frozen else model_picks(
        picks, pf["model_id"], allowed_classes=_allowed_classes)

    # ---- (b) mark + exit existing open positions ----
    marks: dict = {}
    for p in opens:
        mkt = _market_for(p["symbol"], p["asset_class"], ma_days, allow_net)
        marks[p["symbol"]] = mkt["price"] if mkt["price"] else float(p["entry_price"])
        decision = engine.evaluate_exit(p, mkt, asof_date=asof)
        if decision["action"] == "exit" and mkt["price"]:
            db.execute(
                "UPDATE PF_POSITION SET status='closed', exit_date=?, exit_price=?, "
                "exit_reason=?, realized_pnl_pct=?, realized_pnl_usd=? WHERE id=?",
                (asof, decision["exit_price"], decision["reason"],
                 decision["realized_pnl_pct"], decision["realized_pnl_usd"], p["id"]))
            log_event(db, pid, asof, "exit", p["symbol"],
                      {"reason": decision["reason"],
                       "pnl_pct": decision["realized_pnl_pct"]})
            summary["exits"] += 1

    # ---- (a) ingest new eligible picks ----
    if not frozen:
        for pick in cand_picks:
            sym = pick.get("symbol")
            if not sym:
                continue
            state = portfolio_state(db, pid, starting_nav, marks)
            if engine.evaluate_entry.__doc__:  # noop guard for linters
                pass
            mkt = _market_for(sym, pick.get("asset_class"), ma_days, allow_net)
            if mkt["price"]:
                marks[sym] = mkt["price"]
            epick = {
                "model": pf["model_id"],
                "symbol": sym,
                "direction": _norm_dir(pick.get("direction")),
                "asset_class": (pick.get("asset_class") or "").upper(),
                "confidence": pick.get("confidence"),
                "thesis": pick.get("thesis") or pick.get("strategy_name") or "",
                "edge_signal": json.loads(pf["config_snapshot"]).get("edge_signal", 0.0)
                if pf.get("config_snapshot") else 0.0,
                "source_pick_id": pick.get("id") or f"{pf['model_id']}:{sym}:{pick.get('submitted_at','')}",
            }
            decision = engine.evaluate_entry(epick, state, appetite, mkt)
            if decision["action"] == "open":
                pos = decision["position"]
                db.execute(
                    "INSERT INTO PF_POSITION (portfolio_id, symbol, asset_class, "
                    "direction, status, entry_date, entry_price, qty, "
                    "weight_at_entry, tp_price, sl_price, source_pick_id, "
                    "entry_reason, sizing_reason) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (pid, pos["symbol"], pos["asset_class"], pos["direction"],
                     "open", asof, pos["entry_price"], pos["qty"],
                     pos["weight_at_entry"], pos["tp_price"], pos["sl_price"],
                     pos["source_pick_id"], pos["entry_reason"], pos["sizing_reason"]))
                summary["entries"] += 1
            else:
                log_event(db, pid, asof, "reject", sym,
                          {"reason": decision.get("reason")})
                summary["rejects"] += 1
                if decision.get("reason") == "drawdown_breaker":
                    log_event(db, pid, asof, "breaker", None,
                              {"mtd_return_pct": state["mtd_return_pct"]})

    # ---- (c) NAV snapshot ----
    state = portfolio_state(db, pid, starting_nav, marks)
    nav = state["nav_usd"]
    cash = state["cash_usd"]
    n_open = len(state["open_positions"])
    gross = sum(abs(float(sp.get("weight_at_entry") or 0.0))
                for sp in state["open_positions"]) * 100.0
    prev = db.query(
        "SELECT nav_usd FROM PF_NAV_SNAPSHOT WHERE portfolio_id=? "
        "AND asof_date < ? ORDER BY asof_date DESC LIMIT 1", (pid, asof))
    prev_nav = float(prev[0]["nav_usd"]) if prev else starting_nav
    daily_ret = ((nav - prev_nav) / prev_nav * 100.0) if prev_nav else 0.0
    # drawdown vs running peak across history + today
    all_nav = [float(r["nav_usd"]) for r in db.query(
        "SELECT nav_usd FROM PF_NAV_SNAPSHOT WHERE portfolio_id=? "
        "ORDER BY asof_date ASC", (pid,))] + [nav]
    peak = max(all_nav) if all_nav else nav
    dd = ((nav - peak) / peak * 100.0) if peak else 0.0

    db.execute(
        "INSERT INTO PF_NAV_SNAPSHOT (portfolio_id, asof_date, nav_usd, cash_usd, "
        "gross_exposure_pct, n_open, daily_return_pct, drawdown_pct) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (pid, asof, nav, cash, gross, n_open, daily_ret, dd))
    summary["nav_snapshots"] += 1

    # ---- (e) daily metrics ----
    m = compute_metrics(db, pid)
    exposure_by_class: dict = {}
    for sp in state["open_positions"]:
        exposure_by_class[sp["asset_class"]] = exposure_by_class.get(
            sp["asset_class"], 0.0) + abs(float(sp.get("weight_at_entry") or 0.0)) * 100.0
    db.execute(
        "INSERT INTO PF_DAILY_METRICS (portfolio_id, asof_date, sharpe_30d, "
        "sortino_30d, max_dd, cagr, pf_to_date, wr_to_date, exposure_by_class) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (pid, asof, m["sharpe_30d"], m["sortino_30d"], m["max_dd"],
         m["cagr"], m["pf_to_date"], m["wr_to_date"],
         json.dumps(exposure_by_class)))

    db.commit()


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="EOD AI-model paper-portfolio runner")
    ap.add_argument("--apply", action="store_true",
                    help="write to live MySQL (default is dry-run, in-memory)")
    ap.add_argument("--dry-run", action="store_true",
                    help="explicit dry-run (default behavior)")
    ap.add_argument("--asof", help="asof date YYYY-MM-DD (default: today UTC)")
    ap.add_argument("--picks", default=str(DEFAULT_PICKS))
    ap.add_argument("--leaderboard", default=str(DEFAULT_LEADERBOARD))
    ap.add_argument("--no-net", action="store_true",
                    help="skip price network calls (offline syntax/path test)")
    args = ap.parse_args(argv)

    apply = args.apply and not args.dry_run
    asof = args.asof or date.today().isoformat()
    allow_net = not args.no_net

    profiles = load_profiles()
    picks_path = Path(args.picks)
    lb_path = Path(args.leaderboard)
    if not picks_path.exists() or not lb_path.exists():
        print(f"::warning title=run_daily::missing JSONs "
              f"(picks={picks_path.exists()}, lb={lb_path.exists()})",
              file=sys.stderr)
    models = load_leaderboard(lb_path) if lb_path.exists() else []
    picks = load_picks(picks_path) if picks_path.exists() else []

    print(f"[run_daily] mode={'APPLY' if apply else 'DRY-RUN'} asof={asof} "
          f"models={len(models)} picks={len(picks)} net={allow_net}")

    db = DB("mysql" if apply else "sqlite")
    try:
        if apply:
            db.connect_mysql()
        else:
            db.connect_sqlite()
    except Exception as exc:  # noqa: BLE001
        print(f"::error title=run_daily::DB connect failed: {exc}", file=sys.stderr)
        return 1

    summary = {"seeded": 0, "entries": 0, "exits": 0, "rejects": 0,
               "nav_snapshots": 0}
    try:
        summary["seeded"] = seed_portfolios(db, models, profiles)
        active = db.query(
            "SELECT * FROM PF_PORTFOLIO WHERE status IN ('active','frozen')")
        print(f"[run_daily] {len(active)} portfolio(s) "
              f"({summary['seeded']} newly seeded)")
        for pf in active:
            run_portfolio(db, pf, picks, profiles, asof, allow_net, summary)
        if not apply:
            print("[run_daily] DRY-RUN: nothing written to MySQL (in-memory only)")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("\n[run_daily] SUMMARY")
    print(f"  portfolios seeded : {summary['seeded']}")
    print(f"  entries opened    : {summary['entries']}")
    print(f"  exits closed      : {summary['exits']}")
    print(f"  rejects logged    : {summary['rejects']}")
    print(f"  NAV snapshots     : {summary['nav_snapshots']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
