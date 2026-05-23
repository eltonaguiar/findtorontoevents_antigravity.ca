"""

Comprehensive Audit Trail Backfill

====================================

Reads ALL available historical signal data and imports into:

  1. Local SQLite  data/audit_trail.db   (raw_picks table)

  2. MySQL SQL     audit_trail/backfill_import.sql  (for ejaguiar1_stocks)



Sources scanned:

  - closed_picks.json  (alpha_engine, mercury2, battleground, ml_battleground, etc.)

  - active_picks.json  (open positions from all systems)

  - freshpicks_sent.json / freshpicks_consensus_sent.json  (Discord-sent picks)

  - freshpicks_gate_state.json  (Discord gate tracking)

  - SQLite databases   (kimi_trading.db, signal_tracker.db, dna_master, genome, etc.)

  - signal_history.json / signal_tracking.json  (KIMI signals)



Usage:  python -m audit_trail.backfill

"""



import datetime as dt

import hashlib

import json

import os

import pathlib

import sqlite3

import sys

import uuid



REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO_ROOT))



from audit_trail.db import get_connection

from audit_trail.recorder import derive_asset_class, compute_dedup_hash

from audit_trail.asset_classification import canonicalize_symbol



# ── Extended asset class derivation ──



_FOREX_PAIRS = {

    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD",

    "EURGBP", "EURJPY", "GBPJPY", "AUDCAD", "AUDCHF", "AUDNZD", "CADJPY",

    "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURNZD", "GBPAUD", "GBPCAD",

    "GBPCHF", "GBPNZD", "NZDCAD", "NZDJPY", "DXY", "XAUUSD", "XAGUSD",

}



_MEMECOIN_BASES = {

    "DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "MEME", "TURBO",

    "BRETT", "NEIRO", "POPCAT", "MOG", "MYRO", "SATS", "RATS", "ORDI",

    "DOG", "BOME", "SLERF", "PONKE",

}



_CRYPTO_SUFFIXES = ("USDT", "BTC", "ETH", "BUSD", "USDC")

_FOREX_PREFIXES = ("EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD")





def derive_asset_class_ext(symbol, source_system="", entry_price=0):

    """Extended asset class derivation with memecoin / penny stock detection."""

    s = symbol.upper().replace("-", "").replace("/", "").replace("_", "")

    # strip =X suffix (Yahoo Finance forex convention)

    s = s.replace("=X", "")



    base = s

    for sfx in _CRYPTO_SUFFIXES:

        if s.endswith(sfx):

            base = s[: -len(sfx)]

            break



    if base in _MEMECOIN_BASES:

        return "MEMECOIN"



    # forex

    if s in _FOREX_PAIRS:

        return "FOREX"

    if len(s) == 6 and s[:3] in set(_FOREX_PREFIXES) and s[3:] in set(_FOREX_PREFIXES):

        return "FOREX"



    # crypto

    if any(s.endswith(sfx) for sfx in _CRYPTO_SUFFIXES):

        return "CRYPTO"

    if base in ("BTC", "ETH", "SOL", "XRP", "ADA", "BNB", "AVAX", "DOT",

                "LINK", "MATIC", "UNI", "AAVE", "NEAR", "SUI", "FIL", "INJ",

                "TON", "SEI", "TIA", "RENDER", "FET", "AR", "OP", "ARB",

                "APT", "ATOM", "ALGO", "ICP", "HBAR", "VET", "FTM", "CRV"):

        return "CRYPTO"



    # penny stock by source

    if source_system in ("penny_picks", "penny_stocks"):

        return "PENNY_STOCK"



    # penny stock by price

    if entry_price and 0 < entry_price < 5:

        return "PENNY_STOCK"



    return "EQUITY"





# ── Helpers ──



def _now_iso():

    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()





def _mysql_esc(val):

    """Escape a value for MySQL INSERT."""

    if val is None:

        return "NULL"

    if isinstance(val, bool):

        return "1" if val else "0"

    if isinstance(val, (int, float)):

        if val != val:  # NaN

            return "NULL"

        return str(val)

    s = str(val)

    s = s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")

    return f"'{s}'"





def _safe_float(val, default=None):

    if val is None:

        return default

    try:

        f = float(val)

        return default if f != f else f  # NaN guard

    except (ValueError, TypeError):

        return default





def _norm_symbol(raw):

    s = str(raw or "").upper().strip().replace("-", "").replace("/", "").replace("_", "")

    s = s.replace("=X", "")

    # strip junk numeric IDs like PEPE24478

    # but only add T for crypto-like USD pairs

    if s.endswith("USD") and not s.endswith("USDT") and not s.endswith("BUSD"):

        if len(s) <= 10:

            s += "T"

    return s





def _norm_direction(raw):

    d = str(raw or "").upper().strip()

    if d in ("LONG", "BUY", "STRONG_BUY"):

        return "LONG"

    if d in ("SHORT", "SELL", "STRONG_SELL"):

        return "SHORT"

    return None





def _norm_status(raw, exit_price=None):

    s = str(raw or "").upper().strip()

    if s in ("WON", "WIN", "CLOSED_TP", "TP_HIT"):

        return "WON"

    if s in ("LOST", "LOSS", "CLOSED_SL", "SL_HIT", "STOPPED"):

        return "LOST"

    if s in ("EXPIRED", "TIMEOUT"):

        return "EXPIRED"

    if s in ("ACTIVE", "OPEN", "PENDING"):

        return "OPEN"

    return "CLOSED" if exit_price else "OPEN"





def _extract_strategy(pick):

    for k in ("strategy", "strategy_name", "algorithmName", "algorithm", "algorithm_name"):

        v = pick.get(k)

        if v:

            return str(v)

    dna = pick.get("strategy_dna")

    if isinstance(dna, dict):

        return dna.get("strategy_id") or dna.get("name") or "unknown_strategy"

    return "unknown_strategy"





# ── Main Backfiller ──



class Backfiller:

    def __init__(self):

        self.conn = get_connection()

        self.mysql = []  # MySQL INSERT lines

        self.stats = {

            "json_closed": 0,

            "json_active": 0,

            "discord_sent": 0,

            "sqlite_tables": 0,

            "raw_picks": 0,

            "bt_trades": 0,

            "dupes_skipped": 0,

            "errors": 0,

        }



        # Create backfill run

        self.run_id = str(uuid.uuid4())

        self.conn.execute(

            "INSERT OR IGNORE INTO aggregation_runs "

            "(run_id, started_at, status, regime_data) VALUES (?,?,'RUNNING',?)",

            (self.run_id, _now_iso(),

             json.dumps({"type": "backfill", "date": str(dt.date.today())})),

        )

        self.conn.commit()



        # MySQL header

        self.mysql.append("-- ==============================================")

        self.mysql.append("-- Audit Trail Backfill for ejaguiar1_stocks")

        self.mysql.append(f"-- Generated: {_now_iso()}")

        self.mysql.append("-- ==============================================")

        self.mysql.append("")

        self.mysql.append("SET NAMES utf8mb4;")

        self.mysql.append("SET FOREIGN_KEY_CHECKS=0;")

        self.mysql.append("")

        self.mysql.append(

            f"INSERT IGNORE INTO at_aggregation_runs "

            f"(run_id, started_at, status, source) VALUES "

            f"({_mysql_esc(self.run_id)}, NOW(), 'COMPLETED', 'backfill');"

        )

        self.mysql.append("")



    # ── Insert helpers ──



    def _insert_raw(self, source_system, symbol, asset_class, direction,

                    entry, tp, sl, conf, strategy, signal_ts,

                    status, exit_price, pnl, exit_reason, payload):

        """Insert into local SQLite raw_picks + generate MySQL INSERT."""

        # Canonicalize symbol so FOREX/FUTURES rows carry their yfinance suffix

        # (=X/=F) — prevents re-introducing the EURUSD vs EURUSD=X split.

        symbol = canonicalize_symbol(symbol, asset_class)

        pick_id = str(uuid.uuid4())

        dedup = compute_dedup_hash(symbol, direction or "LONG", entry or 0,

                                   signal_ts or "")

        rr = None

        if entry and tp and sl and entry > 0:

            try:

                if direction == "LONG" and (entry - sl) > 0:

                    rr = round((tp - entry) / (entry - sl), 2)

                elif direction == "SHORT" and (sl - entry) > 0:

                    rr = round((entry - tp) / (sl - entry), 2)

            except (ZeroDivisionError, TypeError):

                pass



        try:

            self.conn.execute(

                "INSERT INTO raw_picks "

                "(id, aggregation_run_id, source_system, symbol, asset_class, "

                "direction, entry_price, take_profit, stop_loss, risk_reward, "

                "confidence, strategy, raw_payload, signal_timestamp, "

                "recorded_at, dedup_hash, created_by) "

                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",

                (pick_id, self.run_id, source_system, symbol, asset_class,

                 direction or "LONG", entry, tp, sl, rr, conf, strategy,

                 json.dumps(payload, default=str) if payload else None,

                 signal_ts, _now_iso(), dedup, "backfill"),

            )

            self.conn.commit()

            self.stats["raw_picks"] += 1

        except Exception:

            self.conn.rollback()

            self.stats["dupes_skipped"] += 1

            return None



        # MySQL

        self.mysql.append(

            f"INSERT IGNORE INTO at_raw_picks "

            f"(id, aggregation_run_id, source_system, symbol, asset_class, "

            f"direction, entry_price, take_profit, stop_loss, risk_reward, "

            f"confidence, strategy, signal_timestamp, recorded_at, dedup_hash, "

            f"created_by, status, exit_price, pnl_pct, exit_reason) VALUES ("

            f"{_mysql_esc(pick_id)}, {_mysql_esc(self.run_id)}, "

            f"{_mysql_esc(source_system)}, {_mysql_esc(symbol)}, "

            f"{_mysql_esc(asset_class)}, {_mysql_esc(direction or 'LONG')}, "

            f"{entry or 'NULL'}, {tp or 'NULL'}, {sl or 'NULL'}, "

            f"{rr or 'NULL'}, {conf or 'NULL'}, {_mysql_esc(strategy)}, "

            f"{_mysql_esc(signal_ts)}, NOW(), {_mysql_esc(dedup)}, 'backfill', "

            f"{_mysql_esc(status)}, {exit_price or 'NULL'}, "

            f"{pnl or 'NULL'}, {_mysql_esc(exit_reason)});"

        )

        return pick_id



    def _insert_discord_sent(self, channel, symbol, asset_class, direction,

                             entry, tp, sl, conf, strategy, source_system,

                             dedup_key, sent_at):

        """Generate MySQL INSERT for Discord sent record."""
        symbol = canonicalize_symbol(symbol, asset_class)

        self.mysql.append(

            f"INSERT IGNORE INTO at_discord_sent "

            f"(channel, symbol, asset_class, direction, entry_price, "

            f"take_profit, stop_loss, confidence, strategy, source_system, "

            f"dedup_key, sent_at) VALUES ("

            f"{_mysql_esc(channel)}, {_mysql_esc(symbol)}, "

            f"{_mysql_esc(asset_class)}, {_mysql_esc(direction)}, "

            f"{entry or 'NULL'}, {tp or 'NULL'}, {sl or 'NULL'}, "

            f"{conf or 'NULL'}, {_mysql_esc(strategy)}, "

            f"{_mysql_esc(source_system)}, {_mysql_esc(dedup_key)}, "

            f"{_mysql_esc(sent_at)});"

        )

        self.stats["discord_sent"] += 1



    def _insert_bt_trade(self, source_db, source_table, symbol, asset_class,

                         direction, strategy, entry, exit_price, tp, sl,

                         entry_time, exit_time, pnl, status, conf, raw_data):

        """Generate MySQL INSERT for backtest trade."""
        symbol = canonicalize_symbol(symbol, asset_class)

        self.mysql.append(

            f"INSERT IGNORE INTO bt_backtest_trades "

            f"(source_db, source_table, symbol, asset_class, direction, "

            f"strategy, entry_price, exit_price, take_profit, stop_loss, "

            f"entry_time, exit_time, pnl_pct, status, confidence, "

            f"raw_data, imported_at) VALUES ("

            f"{_mysql_esc(source_db)}, {_mysql_esc(source_table)}, "

            f"{_mysql_esc(symbol)}, {_mysql_esc(asset_class)}, "

            f"{_mysql_esc(direction)}, {_mysql_esc(strategy)}, "

            f"{entry or 'NULL'}, {exit_price or 'NULL'}, "

            f"{tp or 'NULL'}, {sl or 'NULL'}, "

            f"{_mysql_esc(entry_time)}, {_mysql_esc(exit_time)}, "

            f"{pnl or 'NULL'}, {_mysql_esc(status)}, {conf or 'NULL'}, "

            f"{_mysql_esc(json.dumps(raw_data, default=str))}, NOW());"

        )

        self.stats["bt_trades"] += 1



    # ── Processors ──



    def _process_closed_json(self, path, source):

        """Process a closed_picks.json file (supports both list and {picks:[...]} format)."""

        try:

            raw = json.load(open(path))

        except Exception:

            return



        # Handle both formats: plain list or dict with "picks"/"closed_picks" key

        if isinstance(raw, dict):

            picks = raw.get("closed_picks", raw.get("picks", []))

            if not isinstance(picks, list):

                return

        elif isinstance(raw, list):

            picks = raw

        else:

            return



        if not picks:

            return



        count = 0

        for p in picks:

            sym = _norm_symbol(p.get("symbol", p.get("pair", "")))

            if not sym:

                continue

            direction = _norm_direction(

                p.get("direction", p.get("signal_type", p.get("signal", "LONG")))

            )

            entry = _safe_float(p.get("entry_price", p.get("entryPrice",

                                p.get("entry", p.get("price")))))

            if not entry or entry <= 0:

                continue



            tp = _safe_float(p.get("take_profit", p.get("targetPrice",

                             p.get("tp_price", p.get("tp", p.get("target_price"))))))

            sl = _safe_float(p.get("stop_loss", p.get("stopPrice",

                             p.get("sl_price", p.get("sl", p.get("stop_price"))))))

            conf = _safe_float(p.get("confidence", p.get("ml_score", 0.5)))

            if conf and conf > 1:

                conf = conf / 100.0

            strategy = _extract_strategy(p)

            ts = p.get("timestamp", p.get("generated_at",

                 p.get("entry_date", p.get("entry_time", p.get("time", "")))))

            exit_price = _safe_float(p.get("exit_price", p.get("exitPrice")))

            pnl = _safe_float(p.get("pnl_pct", p.get("realized_pnl_pct",

                              p.get("gross_pnl_pct", p.get("net_pnl_pct")))))

            if pnl and 0 < abs(pnl) < 1:

                pnl = pnl * 100

            status = _norm_status(p.get("status", ""), exit_price)

            exit_reason = p.get("exit_reason", p.get("close_reason", ""))

            ac = derive_asset_class_ext(sym, source, entry)



            if self._insert_raw(source, sym, ac, direction or "LONG",

                                entry, tp, sl, conf, strategy, ts,

                                status, exit_price, pnl, exit_reason, p):

                count += 1



        self.stats["json_closed"] += 1

        print(f"  {path}: {count}/{len(picks)} closed picks")



    def _process_active_json(self, path, source):

        """Process an active_picks.json file (supports both list and {picks:[...]} format)."""

        try:

            raw = json.load(open(path))

        except Exception:

            return



        # Handle both formats: plain list or dict with "picks" key

        if isinstance(raw, dict):

            picks = raw.get("picks", raw.get("closed_picks", []))

            if not isinstance(picks, list):

                return

        elif isinstance(raw, list):

            picks = raw

        else:

            return



        if not picks:

            return



        count = 0

        for p in picks:

            sym = _norm_symbol(p.get("symbol", p.get("pair", "")))

            if not sym:

                continue

            direction = _norm_direction(

                p.get("direction", p.get("signal_type", p.get("signal", "LONG")))

            )

            entry = _safe_float(p.get("entry_price", p.get("entryPrice",

                                p.get("entry", p.get("price")))))

            if not entry or entry <= 0:

                continue

            tp = _safe_float(p.get("take_profit", p.get("targetPrice",

                             p.get("tp_price", p.get("tp")))))

            sl = _safe_float(p.get("stop_loss", p.get("stopPrice",

                             p.get("sl_price", p.get("sl")))))

            conf = _safe_float(p.get("confidence", p.get("ml_score", 0.5)))

            if conf and conf > 1:

                conf = conf / 100.0

            strategy = _extract_strategy(p)

            ts = p.get("timestamp", p.get("generated_at", p.get("entry_date", "")))

            ac = derive_asset_class_ext(sym, source, entry)



            if self._insert_raw(source, sym, ac, direction or "LONG",

                                entry, tp, sl, conf, strategy, ts,

                                "OPEN", None, None, None, p):

                count += 1



        if count:

            self.stats["json_active"] += 1

            print(f"  {path}: {count}/{len(picks)} active picks")



    def _process_discord_consensus_sent(self, path):

        """Process freshpicks_consensus_sent.json (list of dedup keys)."""

        try:

            keys = json.load(open(path))

        except Exception:

            return

        if not isinstance(keys, list):

            return



        for key in keys:

            parts = str(key).split("__")

            if len(parts) >= 2:

                sym = _norm_symbol(parts[0])

                direction = _norm_direction(parts[1])

                entry = _safe_float(parts[2]) if len(parts) >= 3 else None

                ac = derive_asset_class_ext(sym, "consensus", entry or 0)

                self._insert_discord_sent(

                    "consensus", sym, ac, direction, entry,

                    None, None, None, None, "cross_aggregator", key, _now_iso()

                )

        print(f"  {path}: {len(keys)} consensus sent keys")



    def _process_discord_gate_state(self, path):

        """Process freshpicks_gate_state.json (dedup dict with send details)."""

        try:

            data = json.load(open(path))

        except Exception:

            return

        dedup = data.get("dedup", {})

        if not dedup:

            return



        for key, info in dedup.items():

            parts = key.split("__")

            sym = _norm_symbol(parts[0]) if parts else ""

            direction = _norm_direction(parts[1]) if len(parts) >= 2 else None

            entry = _safe_float(info.get("entry"))

            tp = _safe_float(info.get("tp"))

            sl = _safe_float(info.get("sl"))

            conf = _safe_float(info.get("confidence"))

            sent_at = info.get("sent_at", _now_iso())

            ac = derive_asset_class_ext(sym, "freshpicks", entry or 0)

            self._insert_discord_sent(

                "fresh-picks", sym, ac, direction, entry, tp, sl, conf,

                None, info.get("system", "unknown"), key, sent_at

            )

        print(f"  {path}: {len(dedup)} gate state entries")



    def _process_discord_system_sent(self, path, channel, source):

        """Process system-specific freshpicks_sent.json (list of dedup keys)."""

        try:

            keys = json.load(open(path))

        except Exception:

            return

        if not isinstance(keys, list):

            return



        for key in keys:

            parts = str(key).split("__")

            if len(parts) >= 2:

                sym = _norm_symbol(parts[0])

                strategy = parts[1] if len(parts) >= 2 else ""

                entry = _safe_float(parts[2]) if len(parts) >= 3 else None

                ac = derive_asset_class_ext(sym, source, entry or 0)

                self._insert_discord_sent(

                    channel, sym, ac, None, entry,

                    None, None, None, strategy, source, key, _now_iso()

                )

        print(f"  {path}: {len(keys)} {source} sent keys")



    def _process_sqlite(self, db_path, source_name):

        """Process a SQLite database — import tables with symbol data."""

        if not os.path.exists(db_path):

            return

        try:

            src = sqlite3.connect(str(db_path), timeout=10)

            src.row_factory = sqlite3.Row

        except Exception as e:

            print(f"  SKIP {db_path}: {e}")

            return



        tables = [r[0] for r in src.execute(

            "SELECT name FROM sqlite_master WHERE type='table' "

            "AND name NOT LIKE 'sqlite_%'"

        ).fetchall()]



        rel = str(pathlib.Path(db_path).relative_to(REPO_ROOT))



        for table in tables:

            try:

                self._process_sqlite_table(src, table, source_name, rel)

            except Exception as e:

                print(f"  ERROR {rel}/{table}: {e}")

                self.stats["errors"] += 1



        src.close()



    def _process_sqlite_table(self, src, table, source_name, rel_path):

        cols = [r[1] for r in src.execute(

            f"PRAGMA table_info('{table}')").fetchall()]

        has_symbol = any(c in cols for c in ("symbol", "pair", "ticker"))

        if not has_symbol:

            return



        rows = src.execute(f"SELECT * FROM {table}").fetchall()

        if not rows:

            return



        count = 0

        for row in rows:

            d = dict(row)

            sym = _norm_symbol(d.get("symbol", d.get("pair", d.get("ticker", ""))))

            if not sym:

                continue



            entry = _safe_float(d.get("entry_price", d.get("entryPrice",

                                d.get("entry", d.get("price")))))

            direction = _norm_direction(

                d.get("direction", d.get("signal_type", d.get("signal", "LONG")))

            )

            strategy = d.get("strategy", d.get("strategy_name",

                       d.get("algorithm", d.get("algorithm_name", source_name))))

            tp = _safe_float(d.get("take_profit", d.get("target_price",

                             d.get("tp", d.get("tp_price")))))

            sl = _safe_float(d.get("stop_loss", d.get("sl", d.get("sl_price",

                             d.get("stop")))))

            exit_price = _safe_float(d.get("exit_price", d.get("exitPrice")))

            pnl = _safe_float(d.get("pnl_pct", d.get("realized_pnl_pct",

                              d.get("gross_pnl_pct", d.get("pnl")))))

            if pnl and 0 < abs(pnl) < 1:

                pnl = pnl * 100

            conf = _safe_float(d.get("confidence", d.get("ml_score",

                               d.get("score", 0.5))))

            if conf and conf > 1:

                conf = conf / 100.0

            ts = d.get("timestamp", d.get("created_at", d.get("entry_time",

                 d.get("entry_date", d.get("generated_at", "")))))

            exit_time = d.get("exit_time", d.get("exit_date", d.get("closed_at", "")))

            status = _norm_status(d.get("status", ""), exit_price)

            exit_reason = d.get("exit_reason", d.get("close_reason", ""))

            ac = derive_asset_class_ext(sym, source_name, entry or 0)



            # Insert as backtest trade in MySQL

            self._insert_bt_trade(

                rel_path, table, sym, ac, direction, strategy,

                entry, exit_price, tp, sl, ts, exit_time, pnl, status, conf, d

            )



            # Also insert into local SQLite if has valid entry

            if entry and entry > 0 and direction:

                self._insert_raw(

                    f"sqlite:{source_name}", sym, ac, direction,

                    entry, tp, sl, conf, strategy, ts,

                    status, exit_price, pnl, exit_reason, d

                )

            count += 1



        if count:

            self.stats["sqlite_tables"] += 1

            self.mysql.append(

                f"INSERT IGNORE INTO at_sqlite_imports "

                f"(source_db_path, source_table, rows_imported, target_table, "

                f"asset_class, imported_at, notes) VALUES ("

                f"{_mysql_esc(rel_path)}, {_mysql_esc(table)}, {count}, "

                f"'bt_backtest_trades', 'UNKNOWN', NOW(), "

                f"{_mysql_esc(f'{count} rows from {source_name}')});"

            )

            print(f"    {rel_path}/{table}: {count} rows")



    # ── Genome mutation results processor ──



    def _process_genome_mutations(self):

        """Process genome mutation result files — register mutations as backtest trades."""

        import glob as glob_mod

        pattern = str(REPO_ROOT / "genome" / "results" / "top_performer_mutations_*.json")

        files = sorted(glob_mod.glob(pattern))

        count = 0

        for fpath in files:

            try:

                data = json.load(open(fpath))

            except Exception:

                continue

            mutations = data if isinstance(data, list) else data.get("mutations", [])

            for m in mutations:

                if not isinstance(m, dict):

                    continue

                sym = _norm_symbol(m.get("symbol", ""))

                if not sym:

                    continue

                direction = _norm_direction(m.get("direction", "LONG"))

                entry = _safe_float(m.get("entry_price"))

                tp = _safe_float(m.get("take_profit"))

                sl = _safe_float(m.get("stop_loss"))

                conf = _safe_float(m.get("confidence", 0.5))

                strategy = m.get("strategy") or m.get("mutation_name") or m.get("name") or "genome_mutation"

                ts = m.get("timestamp", m.get("generated_at", m.get("created_at", "")))

                ac = derive_asset_class_ext(sym, "genome_mutations", entry or 0)



                # Insert as raw pick so it's tracked

                if entry and entry > 0:

                    if self._insert_raw(

                        "genome_mutations", sym, ac, direction or "LONG",

                        entry, tp, sl, conf, strategy, ts,

                        "OPEN", None, None, None, m

                    ):

                        count += 1

        if count:

            print(f"  Genome mutations: {count} picks from {len(files)} result files")



    def _push_to_mysql_direct(self):

        """Push backfill SQL directly to MySQL if pymysql is available."""

        try:

            import pymysql

        except ImportError:

            print("  pymysql not available — skipping direct MySQL push")

            print("  Import SQL manually: mysql < audit_trail/backfill_import.sql")

            return



        host = os.environ.get("AUDIT_DB_HOST", "mysql.50webs.com")

        port = int(os.environ.get("AUDIT_DB_PORT", "3306"))

        # backfill writes bt_backtest_trades — route to BACKTESTS_DB_*

        # (defaults to AUDIT_DB_* for back-compat). See

        # updates/2026-05-04-bt-backtest-trades-archive-plan.md.

        user = os.environ.get(

            "BACKTESTS_DB_USER",

            os.environ.get("AUDIT_DB_USER", "ejaguiar1_stocks"),

        )

        passwd = os.environ.get(

            "BACKTESTS_DB_PASS",

            os.environ.get("AUDIT_DB_PASS", "stocks"),

        )

        db = os.environ.get(

            "BACKTESTS_DB_NAME",

            os.environ.get("AUDIT_DB_NAME", "ejaguiar1_stocks"),

        )



        try:

            conn = pymysql.connect(

                host=host, port=port, user=user, password=passwd,

                database=db, connect_timeout=15, charset="utf8mb4",

                autocommit=True,

            )

        except Exception as e:

            print(f"  MySQL connect failed: {e}")

            print("  SQL file still generated at audit_trail/backfill_import.sql")

            return



        cur = conn.cursor()

        executed = 0

        errors = 0

        for line in self.mysql:

            line = line.strip()

            if not line or line.startswith("--"):

                continue

            try:

                cur.execute(line)

                executed += 1

            except Exception:

                errors += 1



        conn.close()

        print(f"  MySQL direct push: {executed} statements executed, {errors} errors/dupes skipped")



    # ── Main run ──



    def run(self):

        print("=" * 60)

        print("AUDIT TRAIL BACKFILL")

        print("=" * 60)



        # ── 1. Closed picks JSON ──

        print("\n[1/7] Closed picks JSON files...")

        closed_sources = [

            ("alpha_engine/data/closed_picks.json", "alpha_engine"),

            ("mercury2/data/closed_picks.json", "mercury2"),

            ("battleground/data/closed_picks.json", "battleground"),

            ("ml_battleground/ensemble_data/closed_picks.json", "ml_ensemble"),

            ("ml_battleground/system_a_filter/data/closed_picks.json", "ml_system_a"),

            ("ml_battleground/system_b_regime/data/closed_picks.json", "ml_system_b"),

            ("ml_battleground/system_c_deeplearn/data/closed_picks.json", "ml_system_c"),

            ("ml_battleground/system_f_clawsofdoom/data/closed_picks.json", "ml_clawsofdoom"),

            ("breakout_arena/approach_c_spike_reverse/data/closed_picks.json", "breakout_spike"),

            ("crypto_signal_engine/data/closed_picks.json", "crypto_signal_engine"),

            ("ml_crypto_predictor/enhanced_models/live_picks/archive_v1.2/closed_picks.json", "ml_predictor"),

            # ── Added: previously missing closed pick sources ──

            ("paper_trading/data/closed_picks.json", "paper_trading"),

            ("ml_crypto_predictor/enhanced_models/live_picks/closed_picks.json", "ml_predictor_live"),

            ("breakout_arena/approach_a_sr_breakout/data/closed_picks.json", "breakout_a_pure_sr"),

            ("breakout_arena/approach_b_ml_breakout/data/closed_picks.json", "breakout_b_ml"),

            ("ml_battleground/system_d_carry/data/closed_picks.json", "ml_system_d_carry"),

            ("ml_battleground/system_e_momentum/data/closed_picks.json", "ml_system_e_momentum"),

            ("KIMI_RISEOFTHECLAW/data/closed_picks.json", "kimi_riseoftheclaw"),

            ("riseoftheclaw/data/closed_picks.json", "riseoftheclaw"),

            ("rapid_fire_data/closed_picks.json", "rapid_fire"),

            ("rl_agent/data/closed_picks.json", "rl_agent"),

            ("claude_gainer_ml/tracker/closed_picks.json", "claude_gainer_ml"),

            ("crypto_gainer_ml/tracker/closed_picks.json", "crypto_gainer_ml"),

            ("crypto_ml_edge/data/closed_picks.json", "crypto_ml_edge"),

        ]

        for rel, src in closed_sources:

            fp = REPO_ROOT / rel

            if fp.exists() and fp.stat().st_size > 10:

                self._process_closed_json(str(fp), src)



        # ── 2. Active picks JSON ──

        print("\n[2/7] Active picks JSON files...")

        active_sources = [

            ("alpha_engine/data/active_picks.json", "alpha_engine"),

            ("mercury2/data/active_picks.json", "mercury2"),

            ("KIMI_RISEOFTHECLAW/data/active_picks.json", "kimi_riseoftheclaw"),

            ("coinglass_strategies/data/active_picks.json", "coinglass"),

            ("data/aggregated_picks.json", "cross_aggregator"),

            # ── Added: previously missing active pick sources ──

            ("paper_trading/data/active_picks.json", "paper_trading"),

            ("rapid_fire_data/active_picks.json", "rapid_fire"),

            ("rapid_fire_data/now_picks.json", "rapid_fire_now"),

            ("breakout_arena/approach_a_sr_breakout/data/active_picks.json", "breakout_a_pure_sr"),

            ("breakout_arena/approach_b_ml_breakout/data/active_picks.json", "breakout_b_ml"),

            ("crypto_ml_edge/data/active_picks.json", "crypto_ml_edge"),

            ("ml_battleground/system_f_clawsofdoom/data/active_picks.json", "ml_clawsofdoom"),

            ("ml_crypto_predictor/enhanced_models/live_picks/active_picks.json", "ml_predictor_live"),

            ("rl_agent/data/active_picks.json", "rl_agent"),

            ("riseoftheclaw/data/active_picks.json", "riseoftheclaw"),

            ("KIMI_RISEOFTHECLAW/data/live_signals_now.json", "kimi_live_signals"),

            ("riseoftheclaw/data/live_signals_now.json", "riseoftheclaw_live"),

            ("claude_gainer_ml/tracker/claude_live_picks.json", "claude_gainer_ml"),

            ("battleground/data/active_picks.json", "battleground"),

            # ── Genome / DNA evolution picks ──

            ("genome/data/gp_active_picks.json", "genome_gp"),

            ("genome/data/mape_active_picks.json", "genome_mape"),

            ("genome/data/ensemble_active_picks.json", "genome_ensemble"),

            ("genome/data/momentum_active_picks.json", "genome_momentum"),

            ("genome/data/ae_active_picks.json", "genome_ae"),

            ("genome/data/contrarian_active_picks.json", "genome_contrarian"),

            ("genome/data/multitf_active_picks.json", "genome_multitf"),

            ("genome/data/hyperparam_active_picks.json", "genome_hyperparam"),

            ("genome/data/neat_active_picks.json", "genome_neat"),

            ("genome/data/failure_evolved_picks.json", "genome_failure_evolved"),

            ("genome/active_picks.json", "genome_root"),

            # ── Revival picks (from stale system mutation engine) ──

            ("genome/data/revival_all_picks.json", "genome_revival_all"),

            ("genome/data/revival_kimi_riseoftheclaw_picks.json", "genome_revival_kimi"),

            ("genome/data/revival_mercury2_picks.json", "genome_revival_mercury2"),

            ("genome/data/revival_crypto_signal_engine_picks.json", "genome_revival_crypto_signal"),

            ("genome/data/revival_breakout_b_ml_picks.json", "genome_revival_breakout_b"),

            ("genome/data/revival_breakout_a_pure_sr_picks.json", "genome_revival_breakout_a"),

            ("genome/data/revival_paper_trading_picks.json", "genome_revival_paper"),

            ("genome/data/revival_battleground_picks.json", "genome_revival_battleground"),

            ("genome/data/revival_ml_system_b_regime_picks.json", "genome_revival_ml_b"),

            ("genome/data/revival_ml_system_c_deeplearn_picks.json", "genome_revival_ml_c"),

            ("genome/data/revival_breakout_spike_picks.json", "genome_revival_breakout_c"),

            ("genome/data/revival_crypto_gainer_ml_picks.json", "genome_revival_crypto_gainer"),

        ]

        for rel, src in active_sources:

            fp = REPO_ROOT / rel

            if fp.exists() and fp.stat().st_size > 10:

                self._process_active_json(str(fp), src)



        # ── 3. Discord sent tracking ──

        print("\n[3/7] Discord sent picks tracking...")

        fp = REPO_ROOT / "data" / "freshpicks_consensus_sent.json"

        if fp.exists():

            self._process_discord_consensus_sent(str(fp))



        fp = REPO_ROOT / "data" / "freshpicks_gate_state.json"

        if fp.exists():

            self._process_discord_gate_state(str(fp))



        fp = REPO_ROOT / "alpha_engine" / "data" / "freshpicks_sent.json"

        if fp.exists():

            self._process_discord_system_sent(str(fp), "alpha-engine", "alpha_engine")



        fp = REPO_ROOT / "KIMI_RISEOFTHECLAW" / "data" / "freshpicks_sent.json"

        if fp.exists():

            self._process_discord_system_sent(str(fp), "kimi", "kimi_riseoftheclaw")



        # ── 4. Signal history JSON (KIMI) ──

        print("\n[4/7] Signal history JSON files...")

        for rel in ["KIMI_RISEOFTHECLAW/data/signal_history.json",

                     "KIMI_RISEOFTHECLAW/data/signal_tracking.json",

                     "riseoftheclaw/data/signal_tracking.json"]:

            fp = REPO_ROOT / rel

            if fp.exists() and fp.stat().st_size > 100:

                try:

                    data = json.load(open(fp))

                    if isinstance(data, list):

                        count = 0

                        for item in data:

                            # signal_history: list of run objects with signals array

                            signals = item.get("signals", [item])

                            if isinstance(signals, list):

                                for sig in signals:

                                    sym = _norm_symbol(sig.get("symbol", ""))

                                    if not sym:

                                        continue

                                    direction = _norm_direction(sig.get("direction", sig.get("signal_type", "")))

                                    levels = sig.get("levels", {})

                                    entry = _safe_float(levels.get("entry", sig.get("entry_price", sig.get("price"))))

                                    if not entry or entry <= 0:

                                        continue

                                    tp = _safe_float(levels.get("take_profit", sig.get("take_profit")))

                                    sl = _safe_float(levels.get("stop_loss", sig.get("stop_loss")))

                                    conf = _safe_float(sig.get("confidence", 0.5))

                                    if conf and conf > 1:

                                        conf = conf / 100.0

                                    ts = item.get("timestamp", sig.get("timestamp", ""))

                                    ac = derive_asset_class_ext(sym, "kimi_signals", entry)

                                    if self._insert_raw(

                                        "kimi_signals", sym, ac, direction or "LONG",

                                        entry, tp, sl, conf,

                                        sig.get("signal_type", "KIMI"),

                                        ts, "OPEN", None, None, None, sig

                                    ):

                                        count += 1

                        print(f"  {rel}: {count} signals")

                    elif isinstance(data, dict):

                        # signal_tracking: dict keyed by symbol

                        count = 0

                        for sym_key, entries in data.items():

                            if isinstance(entries, list):

                                for sig in entries:

                                    sym = _norm_symbol(sym_key)

                                    entry = _safe_float(sig.get("entry_price", sig.get("price")))

                                    if not entry or entry <= 0:

                                        continue

                                    direction = _norm_direction(sig.get("direction", sig.get("signal_type", "LONG")))

                                    tp = _safe_float(sig.get("take_profit", sig.get("tp")))

                                    sl = _safe_float(sig.get("stop_loss", sig.get("sl")))

                                    conf = _safe_float(sig.get("confidence", 0.5))

                                    ts = sig.get("timestamp", sig.get("created_at", ""))

                                    status = _norm_status(sig.get("status", ""), sig.get("exit_price"))

                                    ac = derive_asset_class_ext(sym, "kimi_tracking", entry)

                                    if self._insert_raw(

                                        "kimi_tracking", sym, ac, direction or "LONG",

                                        entry, tp, sl, conf,

                                        sig.get("strategy", "KIMI"),

                                        ts, status,

                                        _safe_float(sig.get("exit_price")),

                                        _safe_float(sig.get("pnl_pct")),

                                        sig.get("exit_reason", ""), sig

                                    ):

                                        count += 1

                        print(f"  {rel}: {count} tracked signals")

                except Exception as e:

                    print(f"  ERROR {rel}: {e}")



        # ── 5. SQLite databases ──

        print("\n[5/7] SQLite databases...")

        sqlite_sources = [

            ("KIMI_RISEOFTHECLAW/data/kimi_trading.db", "kimi"),

            ("KIMI_RISEOFTHECLAW/data/signal_tracker.db", "kimi_tracker"),

            ("data/dna_master_picks.db", "dna_master"),

            ("data/live_picks.db", "live_picks"),

            ("coinglass_strategies/data/coinglass.db", "coinglass"),

            ("signal_recorder/data/signal_log.db", "signal_recorder"),

            ("forward_testing/forward_signals.db", "forward_testing"),

            ("genome/strategy_registry.db", "genome"),

            ("genome/genetic_programmer.db", "genome_gp_db"),

            ("genome/ensemble_evolver.db", "genome_ensemble_db"),

            ("genome/mape_evolver.db", "genome_mape_db"),

            ("battleground/data/bundle_babies.db", "bundle_babies"),

            ("battleground/data/dna_factory.db", "dna_factory"),

            ("trading/data/atm_challenge.db", "atm_challenge"),

            ("trading/data/positions.db", "positions"),

            ("paper_trading/data/paper.db", "paper_trading"),

            ("sandbox/data/opposite_day.db", "opposite_day"),

            ("incubator/forward_test.db", "incubator_forward"),

            ("quant_lab/genome_results/genome.db", "quant_genome"),

            ("quant_lab/permutation_results.db", "quant_permutations"),

            ("predictions/data/predictions.db", "predictions"),

            ("meta_strategy/data/meta_strategy.db", "meta_strategy"),

            ("ab_testing_agent/ab_testing.db", "ab_testing"),

            ("KIMI_FEB172026/data/kimi_trading.db", "kimi_feb17"),

            # ── Added: previously missing SQLite databases ──

            ("alpha_engine/data/incubator.db", "alpha_incubator"),

            ("rl_agent/data/rl_agent.db", "rl_agent_db"),

            ("crypto_ml_edge/data/crypto_ml_edge.db", "crypto_ml_edge_db"),

            ("claude_gainer_ml/data/claude_gainer.db", "claude_gainer_db"),

        ]

        for rel, src in sqlite_sources:

            fp = REPO_ROOT / rel

            if fp.exists():

                print(f"  Processing {rel}...")

                self._process_sqlite(str(fp), src)



        # ── 6. Genome mutation results ──

        print("\n[6/7] Genome mutation results...")

        self._process_genome_mutations()



        # ── 7. Direct MySQL push ──

        print("\n[7/7] Direct MySQL push...")

        self._push_to_mysql_direct()



        # ── Finalize ──

        self.conn.execute(

            "UPDATE aggregation_runs SET finished_at=?, status='COMPLETED', "

            "raw_picks_count=? WHERE run_id=?",

            (_now_iso(), self.stats["raw_picks"], self.run_id),

        )

        self.conn.commit()



        self.mysql.append("")

        self.mysql.append("SET FOREIGN_KEY_CHECKS=1;")

        self.mysql.append(

            f"-- Backfill: {self.stats['raw_picks']} raw, "

            f"{self.stats['bt_trades']} backtest, "

            f"{self.stats['discord_sent']} discord sent"

        )



        out_path = REPO_ROOT / "audit_trail" / "backfill_import.sql"

        with open(out_path, "w", encoding="utf-8") as f:

            f.write("\n".join(self.mysql))



        print("\n" + "=" * 60)

        print("BACKFILL COMPLETE")

        print("=" * 60)

        for k, v in self.stats.items():

            print(f"  {k:25s} {v:>8}")

        print(f"\n  MySQL file: {out_path}")

        print(f"  SQLite DB:  {REPO_ROOT / 'data' / 'audit_trail.db'}")

        print("=" * 60)





if __name__ == "__main__":

    bf = Backfiller()

    bf.run()

