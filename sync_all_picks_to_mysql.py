"""
Comprehensive Pick Sync to MySQL (ejaguiar1_stocks)
====================================================
Syncs ALL local pick data sources into MySQL at_raw_picks table.

Sources synced:
  1. JSON active_picks.json from all systems
  2. JSON closed_picks.json from all systems
  3. SQLite databases (live_picks.db, kimi_trading.db, signal_tracker.db, etc.)
  4. Portfolio state (claudes_test_state.json)
  5. Discord sent tracking JSON files

Usage:  python sync_all_picks_to_mysql.py [--dry-run]
"""

import datetime as dt
import hashlib
import json
import os
import pathlib
import sqlite3
import sys
import uuid

REPO_ROOT = pathlib.Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from audit_trail.asset_classification import canonicalize_symbol

# ── MySQL config ──
os.environ.setdefault("AUDIT_DB_HOST", "mysql.50webs.com")
os.environ.setdefault("AUDIT_DB_USER", "ejaguiar1_stocks")
os.environ.setdefault("AUDIT_DB_PASS", "stocks")
os.environ.setdefault("AUDIT_DB_NAME", "ejaguiar1_stocks")

# ── Asset class derivation ──

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
_CRYPTO_BASES = {
    "BTC", "ETH", "SOL", "XRP", "ADA", "BNB", "AVAX", "DOT",
    "LINK", "MATIC", "UNI", "AAVE", "NEAR", "SUI", "FIL", "INJ",
    "TON", "SEI", "TIA", "RENDER", "FET", "AR", "OP", "ARB",
    "APT", "ATOM", "ALGO", "ICP", "HBAR", "VET", "FTM", "CRV",
    "LTC", "BCH", "ETC", "TRX", "ZEC", "SAND", "MANA", "AXS",
}
_CRYPTO_SUFFIXES = ("USDT", "BTC", "ETH", "BUSD", "USDC")
_FOREX_PREFIXES = {"EUR", "GBP", "USD", "JPY", "AUD", "CAD", "CHF", "NZD"}
_EQUITY_SYMS = {
    "SPY", "QQQ", "IWM", "TLT", "GLD", "SLV", "COPX", "VIX", "DIA",
    "AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "META", "GOOG", "NFLX",
    "AMD", "INTC", "COST", "LLY", "JPM", "BAC", "WFC", "GS",
    "GOOGL", "V",
}
_FUTURES_SYMS = {
    "ES=F", "NQ=F", "YM=F", "CL=F", "GC=F", "SI=F", "ZN=F",
    "ES", "NQ", "YM", "CL", "GC", "SI", "ZN",
    "ESF", "NQF", "YMF", "CLF", "GCF", "SIF", "ZNF",
    "RTY=F", "HG=F", "NG=F", "ZB=F", "ZC=F", "ZS=F", "ZW=F",
}
_ETF_SYMS = {
    "SPY", "QQQ", "DIA", "IWM",
    "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLB", "XLU",
    "XLRE", "XLC", "GLD", "SLV", "TLT", "HYG", "LQD",
    "EEM", "VWO", "AGG", "BND", "ARKK", "ARKG",
}
_PENNY_SYMS = {
    "SOFI", "NIO", "PLTR", "MARA", "RIOT", "IONQ", "RIVN", "LCID",
    "SNDL", "GME", "AMC",
}
# Map category field values from multi_asset/scanner.py to DB enum
_CATEGORY_TO_ASSET_CLASS = {
    "futures": "FUTURES", "stock": "EQUITY", "forex": "FOREX",
    "etf": "ETF", "penny": "PENNY_STOCK", "crypto": "CRYPTO",
    "meme": "MEMECOIN",
}


def derive_asset_class(symbol, source="", entry_price=0, category=""):
    """Derive DB-compatible asset_class from symbol, source, price, or category hint."""
    # If caller provides a category hint (e.g. from multi_asset scanner), honor it
    if category:
        mapped = _CATEGORY_TO_ASSET_CLASS.get(category.lower())
        if mapped:
            return mapped

    raw = str(symbol or "").upper().strip()
    # Check futures first (before stripping =F)
    if raw in _FUTURES_SYMS or raw.endswith("=F"):
        return "FUTURES"

    s = raw.replace("-", "").replace("/", "").replace("_", "").replace("=X", "")
    base = s
    # Strip crypto suffixes to get base symbol (check longer suffixes first)
    for sfx in sorted(_CRYPTO_SUFFIXES, key=len, reverse=True):
        if s.endswith(sfx):
            base = s[:-len(sfx)]
            break
    # Also check plain USD suffix for yfinance format (e.g. PEPE-USD -> PEPEUSD -> base=PEPE)
    if base == s and s.endswith("USD") and len(s) > 3:
        base = s[:-3]
    if base in _MEMECOIN_BASES:
        return "MEMECOIN"
    if s in _FOREX_PAIRS:
        return "FOREX"
    if len(s) == 6 and s[:3] in _FOREX_PREFIXES and s[3:] in _FOREX_PREFIXES:
        return "FOREX"
    if raw in _ETF_SYMS or s in _ETF_SYMS:
        return "ETF"
    if raw in _PENNY_SYMS or s in _PENNY_SYMS:
        return "PENNY_STOCK"
    if s in _EQUITY_SYMS or base in _EQUITY_SYMS:
        return "EQUITY"
    if any(s.endswith(sfx) for sfx in _CRYPTO_SUFFIXES):
        return "CRYPTO"
    if base in _CRYPTO_BASES:
        return "CRYPTO"
    if source in ("penny_picks", "penny_stocks", "multi_asset_scanner") and entry_price and 0 < entry_price < 5:
        return "PENNY_STOCK"
    if entry_price and 0 < entry_price < 5:
        return "PENNY_STOCK"
    return "EQUITY"


# ── Helpers ──

def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _safe_json(payload, max_len=4000):
    """Serialize payload to JSON, truncating safely (never mid-string)."""
    if not payload:
        return None
    try:
        s = json.dumps(payload, default=str, ensure_ascii=False)
        if len(s) <= max_len:
            return s
        # Truncate to valid JSON by dropping keys
        if isinstance(payload, dict):
            trimmed = {k: v for k, v in list(payload.items())[:10]}
            return json.dumps(trimmed, default=str, ensure_ascii=False)[:max_len]
        return s[:max_len - 1] + "}"
    except Exception:
        return None


def _safe_float(val, default=None):
    if val is None:
        return default
    try:
        f = float(val)
        return default if f != f else f
    except (ValueError, TypeError):
        return default


def _norm_symbol(raw):
    # NOTE: do NOT strip "=X"/"=F" — those yfinance suffixes are part of the
    # canonical symbol form for FOREX/FUTURES. Stripping them re-introduced the
    # EURUSD vs EURUSD=X split in at_raw_picks (RESOLUTION_PIPELINE_FIX_PLAN
    # 2026-05-18, Defect 1b). Strip only separators for crypto base detection.
    raw_str = str(raw or "").upper().strip()
    s = raw_str.replace("-", "").replace("/", "").replace("_", "")
    # Preserve a yfinance suffix while cleaning separators from the root.
    suffix = ""
    if s.endswith("=X") or s.endswith("=F"):
        suffix, s = s[-2:], s[:-2]
    if not suffix and s.endswith("USD") and not s.endswith("USDT") and not s.endswith("BUSD"):
        if len(s) <= 10 and any(s.startswith(b) for b in _CRYPTO_BASES):
            s += "T"
    result = s + suffix
    # Route through the shared canonicalizer so FOREX pairs regain "=X" and
    # FUTURES roots regain "=F" even when the source emitted the bare form.
    return canonicalize_symbol(result, derive_asset_class(result))


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
            return str(v)[:200]
    dna = pick.get("strategy_dna")
    if isinstance(dna, dict):
        return dna.get("strategy_id", dna.get("name", ""))[:200]
    return ""


def _compute_dedup(symbol, direction, entry_price, timestamp):
    """SHA-256 dedup hash. Rounds timestamp to 5-min window to match recorder.py logic."""
    epoch_rounded = 0
    if timestamp:
        try:
            ts_clean = str(timestamp)
            for sfx in (" EST", " EDT", " UTC", " GMT"):
                ts_clean = ts_clean.replace(sfx, "")
            ts_clean = ts_clean.replace("Z", "+00:00")
            ts_obj = dt.datetime.fromisoformat(ts_clean)
            epoch_rounded = int(ts_obj.timestamp() / 300) * 300
        except (ValueError, TypeError, AttributeError):
            epoch_rounded = 0
    raw = f"{symbol}|{direction}|{entry_price or 0:.8f}|{epoch_rounded}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _compute_rr(direction, entry, tp, sl):
    if not (entry and tp and sl and entry > 0):
        return None
    try:
        if direction == "LONG" and (entry - sl) > 0:
            return round((tp - entry) / (entry - sl), 2)
        elif direction == "SHORT" and (sl - entry) > 0:
            return round((entry - tp) / (sl - entry), 2)
    except (ZeroDivisionError, TypeError):
        pass
    return None


def _parse_ts(raw_ts):
    """Parse various timestamp formats to MySQL DATETIME string."""
    if not raw_ts:
        return None
    s = str(raw_ts).replace("Z", "+00:00")
    for sfx in (" EST", " EDT", " UTC", " GMT"):
        s = s.replace(sfx, "")
    try:
        parsed = dt.datetime.fromisoformat(s)
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    # Try epoch
    try:
        f = float(raw_ts)
        if f > 1e12:
            f /= 1000
        return dt.datetime.fromtimestamp(f, tz=dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return None


# ── JSON source definitions ──

JSON_SOURCES = [
    # (directory, source_system_name)
    ("alpha_engine/data", "alpha_engine"),
    ("battleground/data", "battleground"),
    ("coinglass_strategies/data", "coinglass_strategies"),
    ("crypto_ml_edge/data", "crypto_ml_edge"),
    ("crypto_signal_engine/data", "crypto_signal_engine"),
    ("mercury2/data", "mercury2"),
    ("paper_trading/data", "paper_trading"),
    ("rl_agent/data", "rl_agent"),
    ("KIMI_RISEOFTHECLAW/data", "KIMI_RiseOfTheClaw"),
    ("rapid_fire_data", "rapid_fire"),
    ("breakout_arena/approach_a_sr_breakout/data", "BreakoutArena_A"),
    ("breakout_arena/approach_b_ml_breakout/data", "BreakoutArena_B"),
    ("breakout_arena/approach_c_spike_reverse/data", "BreakoutArena_C"),
    ("ml_battleground/system_a_filter/data", "ml_bg_a"),
    ("ml_battleground/system_b_regime/data", "ml_bg_b"),
    ("ml_battleground/system_c_deeplearn/data", "ml_bg_c"),
    ("ml_battleground/system_d_carry/data", "ml_bg_d"),
    ("ml_battleground/system_e_momentum/data", "ml_bg_e"),
    ("ml_battleground/system_f_clawsofdoom/data", "ml_clawsofdoom"),
    ("ml_battleground/ensemble_data", "ml_bg_ensemble"),
    ("ml_crypto_predictor/enhanced_models/live_picks", "ml_crypto_pred"),
    ("genome", "genome"),
    ("genome/data", "mega_mutation"),
    ("riseoftheclaw/data", "riseoftheclaw_deploy"),
    ("multi_asset/data", "multi_asset_scanner"),
    # ── Added 2026-03-13: Sources found missing in comprehensive audit ──
    ("deploy_riseoftheclaw/riseoftheclaw/data", "riseoftheclaw_deployed"),
    ("KIMI_CLAW_RESEARCH_FEB162026/data", "KIMI_ClawResearch"),
    ("ml_crypto_predictor/enhanced_models/live_picks/archive_v1.2", "ml_crypto_pred_v1.2"),
    ("cross_aggregation/data", "cross_aggregation"),
    ("regime_terminal/data", "regime_terminal"),
    # ── Added: copy_trader_intel + smart_money were missing from MySQL sync ──
    ("copy_trader_intel/data", "copy_trader_intel"),
    ("smart_money/data", "smart_money"),
]


def _load_dashboard_json_file_sources():
    """Import explicit dashboard pick files that directory scanning misses."""
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from audit_trail.dashboard_generator import JSON_PICK_SOURCES as dashboard_sources
    except Exception as exc:
        print(f"[WARN] Could not import dashboard JSON_PICK_SOURCES: {exc}")
        return []

    covered_paths = set()
    for directory, _source in JSON_SOURCES:
        base = REPO_ROOT / directory
        covered_paths.add(str((base / "active_picks.json").resolve()))
        covered_paths.add(str((base / "closed_picks.json").resolve()))

    file_sources = []
    seen_paths = set()
    for source_system, active_rel, closed_rel in dashboard_sources:
        for rel_path, is_closed in ((active_rel, False), (closed_rel, True)):
            if not rel_path:
                continue
            abs_path = str((REPO_ROOT / rel_path).resolve())
            if abs_path in covered_paths or abs_path in seen_paths:
                continue
            seen_paths.add(abs_path)
            file_sources.append((rel_path, source_system, is_closed))
    return file_sources


DASHBOARD_JSON_FILE_SOURCES = _load_dashboard_json_file_sources()

# SQLite databases to sync
SQLITE_SOURCES = [
    ("data/live_picks.db", "live_picks_tracker"),
    # REMOVED: ("data/audit_trail.db", "audit_trail_local") — this DB is already
    # dual-written to MySQL by audit_trail/recorder.py via mysql_record_raw_pick().
    # Syncing it here caused runaway duplicates (5,198 rows, 519 BTCUSDT LONG in 3 min)
    # because _compute_dedup used a different hash than recorder.py's compute_dedup_hash.
    ("KIMI_RISEOFTHECLAW/data/kimi_trading.db", "KIMI_RiseOfTheClaw"),
    ("KIMI_RISEOFTHECLAW/data/signal_tracker.db", "KIMI_signal_tracker"),
    ("coinglass_strategies/data/coinglass.db", "coinglass_strategies"),
    ("signal_recorder/data/signal_log.db", "signal_recorder"),
    ("paper_trading/data/paper.db", "paper_trading"),
    ("sandbox/data/opposite_day.db", "sandbox_opposite"),
    ("genome/darwin_portfolios.db", "genome_darwin"),
    ("genome/strategy_registry.db", "genome_registry"),
    ("incubator/forward_test.db", "incubator"),
    ("meta_strategy/data/meta_strategy.db", "meta_strategy"),
    ("quan_engine/data/quan_engine.db", "quan_engine"),
    ("trading/data/positions.db", "trading_positions"),
    ("battleground/data/bundle_babies.db", "battleground_bundles"),
    ("KIMI_FEB172026/data/kimi_trading.db", "kimi_feb17"),
    # ── Added 2026-03-13: Missing DBs found in comprehensive audit ──
    ("alpha_engine/data/alpha.db", "alpha_engine_db"),
    ("alpha_engine/data/incubator.db", "alpha_incubator"),
    ("battleground/data/dna_factory.db", "dna_factory"),
    ("forward_testing/forward_signals.db", "forward_testing"),
    ("predictions/data/predictions.db", "predictions"),
    ("trading/data/atm_challenge.db", "atm_challenge"),
    ("quant_lab/permutation_results.db", "quant_lab"),
]


class PickSyncer:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.conn = None
        self.run_id = str(uuid.uuid4())
        # In-memory dedup state: dedup_hash -> best seen rank (OPEN=0, CLOSED-like=1)
        # This allows OPEN -> CLOSED progression within the same sync run.
        self._seen_dedup_state = {}
        self._recent_inserts = {}  # Rate limit: {(symbol,direction,source) -> last_insert_time}
        self._RATE_LIMIT_SECONDS = 3600  # Max 1 insert per symbol+direction+source per hour
        self.stats = {
            "json_active_inserted": 0,
            "json_closed_inserted": 0,
            "json_closed_updated": 0,
            "sqlite_inserted": 0,
            "bt_trades_inserted": 0,
            "dupes_skipped": 0,
            "rate_limited": 0,
            "errors": 0,
            "sources_processed": 0,
        }

    def connect(self):
        try:
            import pymysql
        except ImportError:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import pymysql

        self.conn = pymysql.connect(
            host=os.environ.get("AUDIT_DB_HOST", "mysql.50webs.com"),
            port=int(os.environ.get("AUDIT_DB_PORT", "3306")),
            user=os.environ.get("AUDIT_DB_USER", "ejaguiar1_stocks"),
            password=os.environ.get("AUDIT_DB_PASS", "stocks"),
            database=os.environ.get("AUDIT_DB_NAME", "ejaguiar1_stocks"),
            connect_timeout=15,
            read_timeout=30,
            write_timeout=30,
            charset="utf8mb4",
            autocommit=True,
        )
        print(f"Connected to MySQL: {os.environ.get('AUDIT_DB_HOST')}")

    def _register_run(self):
        """Register this sync run in at_aggregation_runs."""
        if self.dry_run:
            return
        cur = self.conn.cursor()
        cur.execute(
            "INSERT IGNORE INTO at_aggregation_runs "
            "(run_id, started_at, status, source) VALUES (%s, %s, 'RUNNING', 'full_sync')",
            (self.run_id, _now())
        )

    def _finish_run(self):
        """Mark run as completed with stats."""
        if self.dry_run:
            return
        cur = self.conn.cursor()
        total = (self.stats["json_active_inserted"] + self.stats["json_closed_inserted"]
                 + self.stats["sqlite_inserted"])
        cur.execute(
            "UPDATE at_aggregation_runs SET finished_at=%s, status='COMPLETED', "
            "raw_picks_count=%s, systems_loaded=%s WHERE run_id=%s",
            (_now(), total, self.stats["sources_processed"], self.run_id)
        )

    def _fail_run(self, reason: str = ""):
        """Mark run as failed if an unrecoverable exception occurred."""
        if self.dry_run:
            return
        try:
            cur = self.conn.cursor()
            cur.execute(
                "UPDATE at_aggregation_runs SET finished_at=%s, status='FAILED' "
                "WHERE run_id=%s AND status='RUNNING'",
                (_now(), self.run_id),
            )
            if reason:
                print(f"[WARN] Marked run FAILED: {reason}")
        except Exception as e:
            print(f"[WARN] Could not mark run FAILED: {e}")

    def _insert_raw_pick(self, source_system, symbol, asset_class, direction,
                         entry, tp, sl, confidence, strategy, signal_ts,
                         status, exit_price, pnl_pct, exit_reason, payload=None):
        """Upsert a pick into at_raw_picks. Returns True if inserted/updated."""
        if not symbol or not direction:
            return False

        pick_id = str(uuid.uuid4())
        dedup = _compute_dedup(symbol, direction, entry, signal_ts)
        rr = _compute_rr(direction, entry, tp, sl)
        parsed_ts = _parse_ts(signal_ts)

        # ── Guard 1: In-memory dedup with status precedence (OPEN < CLOSED-like)
        # Allow OPEN -> CLOSED progression in the same run; reject only same/lower precedence dupes.
        status_rank = 0 if status == "OPEN" else 1
        seen_rank = self._seen_dedup_state.get(dedup, -1)
        if seen_rank >= status_rank:
            self.stats["dupes_skipped"] += 1
            return False
        self._seen_dedup_state[dedup] = status_rank

        # ── Guard 2: Rate limit — max 1 insert per symbol+direction+source per hour
        rate_key = (symbol, direction, source_system)
        now_epoch = dt.datetime.now(dt.timezone.utc).timestamp()
        last_insert = self._recent_inserts.get(rate_key, 0)
        if status == "OPEN" and (now_epoch - last_insert) < self._RATE_LIMIT_SECONDS:
            self.stats["rate_limited"] += 1
            return False

        # ── Guard 3: Check MySQL for existing OPEN pick with same symbol+direction+source
        if status == "OPEN" and not self.dry_run:
            try:
                cur = self.conn.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM at_raw_picks "
                    "WHERE symbol=%s AND direction=%s AND source_system=%s AND status='OPEN'",
                    (symbol, direction, source_system)
                )
                existing = cur.fetchone()[0]
                if existing > 0:
                    self.stats["dupes_skipped"] += 1
                    return False
            except Exception:
                pass  # If check fails, proceed with UPSERT as fallback

        if self.dry_run:
            self.stats["json_active_inserted" if status == "OPEN" else "json_closed_inserted"] += 1
            return True

        try:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO at_raw_picks "
                "(id, aggregation_run_id, source_system, symbol, asset_class, direction, "
                "entry_price, take_profit, stop_loss, risk_reward, confidence, strategy, "
                "raw_payload, signal_timestamp, recorded_at, dedup_hash, created_by, "
                "status, exit_price, pnl_pct, exit_reason) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON DUPLICATE KEY UPDATE "
                "aggregation_run_id = VALUES(aggregation_run_id), "
                "recorded_at = VALUES(recorded_at), "
                "raw_payload = COALESCE(VALUES(raw_payload), raw_payload), "
                "confidence = COALESCE(VALUES(confidence), confidence), "
                "risk_reward = COALESCE(VALUES(risk_reward), risk_reward), "
                "take_profit = COALESCE(VALUES(take_profit), take_profit), "
                "stop_loss = COALESCE(VALUES(stop_loss), stop_loss), "
                "status = CASE "
                "  WHEN VALUES(status) <> 'OPEN' THEN VALUES(status) "
                "  ELSE status "
                "END, "
                "exit_price = CASE "
                "  WHEN VALUES(status) <> 'OPEN' AND VALUES(exit_price) IS NOT NULL THEN VALUES(exit_price) "
                "  ELSE exit_price "
                "END, "
                "pnl_pct = CASE "
                "  WHEN VALUES(status) <> 'OPEN' AND VALUES(pnl_pct) IS NOT NULL THEN VALUES(pnl_pct) "
                "  ELSE pnl_pct "
                "END, "
                "exit_reason = CASE "
                "  WHEN VALUES(status) <> 'OPEN' AND NULLIF(VALUES(exit_reason), '') IS NOT NULL THEN VALUES(exit_reason) "
                "  ELSE exit_reason "
                "END, "
                "closed_at = CASE "
                "  WHEN VALUES(status) <> 'OPEN' THEN COALESCE(closed_at, VALUES(recorded_at)) "
                "  ELSE closed_at "
                "END",
                (pick_id, self.run_id, source_system, symbol, asset_class, direction,
                 _safe_float(entry), _safe_float(tp), _safe_float(sl), _safe_float(rr),
                 _safe_float(confidence), strategy,
                 _safe_json(payload),
                 parsed_ts, _now(), dedup, "full_sync",
                 status, _safe_float(exit_price), _safe_float(pnl_pct), exit_reason)
            )
            if cur.rowcount > 0:
                if status == "OPEN":
                    self.stats["json_active_inserted"] += 1
                else:
                    if cur.rowcount == 1:
                        self.stats["json_closed_inserted"] += 1
                    else:
                        self.stats["json_closed_updated"] += 1
                # Track insert time for rate limiting
                self._recent_inserts[rate_key] = now_epoch
                return True
            else:
                self.stats["dupes_skipped"] += 1
                return False
        except Exception as e:
            self.stats["errors"] += 1
            if self.stats["errors"] <= 5:
                print(f"    ERROR inserting {symbol}: {e}")
            return False

    def _insert_bt_trade(self, source_db, source_table, symbol, asset_class,
                         direction, strategy, entry, exit_price, tp, sl,
                         entry_time, exit_time, pnl, status, conf, raw_data):
        """Insert into bt_backtest_trades."""
        if self.dry_run:
            self.stats["bt_trades_inserted"] += 1
            return True
        try:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO bt_backtest_trades "
                "(source_db, source_table, symbol, asset_class, direction, strategy, "
                "entry_price, exit_price, take_profit, stop_loss, entry_time, exit_time, "
                "pnl_pct, status, confidence, raw_data, imported_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (source_db, source_table, symbol, asset_class, direction, strategy,
                 _safe_float(entry), _safe_float(exit_price), _safe_float(tp), _safe_float(sl),
                 _parse_ts(entry_time), _parse_ts(exit_time),
                 _safe_float(pnl), status, _safe_float(conf),
                 _safe_json(raw_data),
                 _now())
            )
            self.stats["bt_trades_inserted"] += 1
            return True
        except Exception as e:
            self.stats["errors"] += 1
            return False

    # ── JSON processors ──

    def _parse_pick_fields(self, p):
        """Extract common fields from a pick dict."""
        sym = _norm_symbol(p.get("symbol", p.get("pair", p.get("asset", ""))))
        direction = _norm_direction(
            p.get("direction", p.get("signal_type", p.get("signal", "LONG")))
        )
        entry = _safe_float(p.get("entry_price", p.get("entryPrice",
                            p.get("entry", p.get("price")))))
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

        return {
            "symbol": sym, "direction": direction, "entry": entry,
            "tp": tp, "sl": sl, "confidence": conf, "strategy": strategy,
            "timestamp": ts, "exit_price": exit_price, "pnl": pnl,
            "status": status, "exit_reason": exit_reason,
        }

    def _load_json(self, path):
        """Load raw JSON payload from disk."""
        try:
            return json.load(open(path))
        except Exception:
            return None

    def _extract_pick_lists(self, raw):
        """Extract active and closed pick lists from mixed JSON payloads."""
        if isinstance(raw, list):
            return raw, []
        if not isinstance(raw, dict):
            return [], []

        active = []
        for active_key in (
            "picks",
            "active_picks",
            "activePicks",
            "signals",
            "active_signals",
            "crypto_signals",
            "stock_signals",
            "forex_signals",
            "active",
            "open_picks",
            "open_trades",
            "forward_signals",
            "predictions",
        ):
            items = raw.get(active_key)
            if isinstance(items, list):
                active = items
                break

        closed = []
        for closed_key in (
            "closed_picks",
            "closedPicks",
            "closed",
            "closed_trades",
            "resolved_picks",
        ):
            items = raw.get(closed_key)
            if isinstance(items, list):
                closed = items
                break

        return active, closed

    def _process_pick_file(self, path, source_system, is_closed, processed_paths=None):
        """Process one explicit JSON pick file."""
        path = pathlib.Path(path)
        if not path.exists():
            return 0
        resolved = str(path.resolve())
        if processed_paths is not None and resolved in processed_paths:
            return 0
        if processed_paths is not None:
            processed_paths.add(resolved)

        raw = self._load_json(str(path))
        if raw is None:
            return 0
        active_picks, closed_picks = self._extract_pick_lists(raw)
        picks = closed_picks if is_closed else active_picks
        if not picks:
            return 0

        inserted = 0
        for p in picks:
            f = self._parse_pick_fields(p)
            if not f["symbol"] or not f["entry"] or f["entry"] <= 0:
                continue
            cat_hint = p.get("category", p.get("asset_class", ""))
            ac = derive_asset_class(f["symbol"], source_system, f["entry"], cat_hint)
            status = f["status"] if is_closed else "OPEN"
            if is_closed and status == "OPEN":
                status = "CLOSED"
            if self._insert_raw_pick(
                source_system,
                f["symbol"],
                ac,
                f["direction"] or "LONG",
                f["entry"],
                f["tp"],
                f["sl"],
                f["confidence"],
                f["strategy"],
                f["timestamp"],
                status,
                f["exit_price"] if is_closed else None,
                f["pnl"] if is_closed else None,
                f["exit_reason"] if is_closed else None,
                p,
            ):
                inserted += 1

        if inserted:
            self.stats["sources_processed"] += 1
            try:
                display_path = path.relative_to(REPO_ROOT)
            except ValueError:
                display_path = path
            print(f"  {display_path}: {inserted} picks synced")
        return inserted

    def process_json_source(self, directory, source_system, processed_paths=None):
        """Process active_picks.json and closed_picks.json from a directory."""
        base = REPO_ROOT / directory
        inserted = 0

        for filename in ("active_picks.json", "closed_picks.json"):
            inserted += self._process_pick_file(
                base / filename,
                source_system,
                is_closed=("closed" in filename),
                processed_paths=processed_paths,
            )

        return inserted

    def process_dashboard_json_file(self, rel_path, source_system, is_closed, processed_paths=None):
        """Process a dashboard-registered pick file with a non-standard filename."""
        return self._process_pick_file(
            REPO_ROOT / rel_path,
            source_system,
            is_closed=is_closed,
            processed_paths=processed_paths,
        )

    def process_sqlite_source(self, db_path_rel, source_name):
        """Process a SQLite database — sync tables with symbol data to MySQL."""
        db_path = REPO_ROOT / db_path_rel
        if not db_path.exists():
            return 0

        try:
            src = sqlite3.connect(str(db_path), timeout=10)
            src.row_factory = sqlite3.Row
        except Exception as e:
            print(f"  SKIP {db_path_rel}: {e}")
            return 0

        tables = [r[0] for r in src.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()]

        total_inserted = 0
        for table in tables:
            try:
                cols = [r[1] for r in src.execute(f"PRAGMA table_info('{table}')").fetchall()]
                has_symbol = any(c in cols for c in ("symbol", "pair", "ticker"))
                if not has_symbol:
                    continue

                rows = src.execute(f"SELECT * FROM [{table}] LIMIT 10000").fetchall()
                if not rows:
                    continue

                inserted = 0
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
                    strategy = str(d.get("strategy", d.get("strategy_name",
                               d.get("algorithm", d.get("algorithm_name", source_name)))) or "")[:200]
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
                    ts = d.get("signal_timestamp", d.get("timestamp",
                         d.get("created_at", d.get("entry_time",
                         d.get("entry_date", d.get("generated_at", ""))))))
                    exit_time = d.get("exit_time", d.get("exit_date", d.get("closed_at", ""))    )
                    status = _norm_status(d.get("status", ""), exit_price)
                    exit_reason = str(d.get("exit_reason", d.get("close_reason", "")) or "")
                    ac = derive_asset_class(sym, source_name, entry or 0)

                    # Insert into at_raw_picks if valid entry
                    if entry and entry > 0 and direction:
                        if self._insert_raw_pick(
                            source_name, sym, ac, direction, entry, tp, sl, conf,
                            strategy, ts, status, exit_price, pnl, exit_reason, d
                        ):
                            inserted += 1

                    # Also insert into bt_backtest_trades for complete history
                    self._insert_bt_trade(
                        db_path_rel, table, sym, ac, direction, strategy,
                        entry, exit_price, tp, sl, ts, exit_time, pnl, status, conf, d
                    )

                if inserted:
                    total_inserted += inserted
                    print(f"    {db_path_rel}/{table}: {inserted} picks + bt_trades")

            except Exception as e:
                self.stats["errors"] += 1
                print(f"    ERROR {db_path_rel}/{table}: {e}")

        src.close()
        if total_inserted:
            self.stats["sources_processed"] += 1
            self.stats["sqlite_inserted"] += total_inserted
        return total_inserted

    def process_portfolio_state(self):
        """Sync portfolio positions from claudes_test_state.json."""
        state_path = REPO_ROOT / "audit_dashboard" / "data" / "claudes_test_state.json"
        if not state_path.exists():
            return 0

        try:
            data = json.load(open(state_path))
        except Exception:
            return 0

        inserted = 0
        for pname, pdata in data.items():
            if not isinstance(pdata, dict) or "positions" not in pdata:
                continue
            positions = pdata.get("positions", [])
            if not isinstance(positions, list):
                continue
            for pos in positions:
                sym = _norm_symbol(pos.get("symbol", ""))
                if not sym:
                    continue
                direction = _norm_direction(pos.get("direction", "LONG"))
                entry = _safe_float(pos.get("entry_price"))
                if not entry or entry <= 0:
                    continue
                tp = _safe_float(pos.get("take_profit", pos.get("tp")))
                sl = _safe_float(pos.get("stop_loss", pos.get("sl")))
                conf = _safe_float(pos.get("confidence", 0.5))
                strategy = pos.get("strategy", pos.get("strategy_name", f"portfolio_{pname}"))
                ts = pos.get("entry_time", pos.get("timestamp", ""))
                ac = derive_asset_class(sym, f"portfolio_{pname}", entry)
                status = _norm_status(pos.get("status", ""), None)

                if self._insert_raw_pick(
                    f"portfolio_{pname}", sym, ac, direction or "LONG",
                    entry, tp, sl, conf, strategy, ts,
                    status, None, None, None, pos
                ):
                    inserted += 1

        if inserted:
            self.stats["sources_processed"] += 1
            print(f"  portfolio_state: {inserted} positions synced")
        return inserted

    def process_discord_sent(self):
        """Sync Discord sent tracking files."""
        files = [
            ("data/freshpicks_consensus_sent.json", "consensus"),
            ("data/freshpicks_gate_state.json", "freshpicks"),
        ]
        # System-specific sent files
        for system_dir in ["alpha_engine/data", "KIMI_RISEOFTHECLAW/data", "battleground/data"]:
            sent_path = REPO_ROOT / system_dir / "freshpicks_sent.json"
            if sent_path.exists():
                files.append((str(pathlib.Path(system_dir) / "freshpicks_sent.json"),
                              pathlib.Path(system_dir).parts[0]))

        total = 0
        for rel_path, channel in files:
            path = REPO_ROOT / rel_path
            if not path.exists():
                continue
            try:
                data = json.load(open(path))
            except Exception:
                continue

            if isinstance(data, list):
                # List of dedup keys
                for key in data:
                    parts = str(key).split("__")
                    if len(parts) >= 2:
                        sym = _norm_symbol(parts[0])
                        direction = _norm_direction(parts[1])
                        entry = _safe_float(parts[2]) if len(parts) >= 3 else None
                        ac = derive_asset_class(sym, channel, entry or 0)
                        if sym and direction and not self.dry_run:
                            try:
                                cur = self.conn.cursor()
                                cur.execute(
                                    "INSERT IGNORE INTO at_discord_sent "
                                    "(channel, symbol, asset_class, direction, entry_price, "
                                    "dedup_key, sent_at, source_system) "
                                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                                    (channel, sym, ac, direction, _safe_float(entry),
                                     key, _now(), "cross_aggregator")
                                )
                                total += cur.rowcount
                            except Exception:
                                pass
            elif isinstance(data, dict) and "dedup" in data:
                # Gate state dict
                for key, info in data.get("dedup", {}).items():
                    parts = key.split("__")
                    sym = _norm_symbol(parts[0]) if parts else ""
                    direction = _norm_direction(parts[1]) if len(parts) >= 2 else None
                    entry = _safe_float(info.get("entry") if isinstance(info, dict) else None)
                    ac = derive_asset_class(sym, "freshpicks", entry or 0)
                    if sym and not self.dry_run:
                        try:
                            cur = self.conn.cursor()
                            cur.execute(
                                "INSERT IGNORE INTO at_discord_sent "
                                "(channel, symbol, asset_class, direction, entry_price, "
                                "confidence, dedup_key, sent_at, source_system) "
                                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                ("fresh-picks", sym, ac, direction, _safe_float(entry),
                                 _safe_float(info.get("confidence") if isinstance(info, dict) else None),
                                 key, info.get("sent_at", _now()) if isinstance(info, dict) else _now(),
                                 info.get("system", "unknown") if isinstance(info, dict) else "unknown")
                            )
                            total += cur.rowcount
                        except Exception:
                            pass

        if total:
            print(f"  discord_sent: {total} entries synced")
        return total

    def run(self):
        """Execute full sync."""
        print("=" * 60)
        print(f"Full Pick Sync to MySQL {'(DRY RUN)' if self.dry_run else ''}")
        print(f"Run ID: {self.run_id}")
        print(f"Started: {_now()}")
        print("=" * 60)

        try:
            if not self.dry_run:
                self.connect()
                self._register_run()

            # 1. JSON sources
            print("\n--- JSON Pick Sources ---")
            processed_json_paths = set()
            for directory, source in JSON_SOURCES:
                self.process_json_source(directory, source, processed_json_paths)

            if DASHBOARD_JSON_FILE_SOURCES:
                print("\n--- Dashboard-Registered JSON Pick Files ---")
                for rel_path, source_system, is_closed in DASHBOARD_JSON_FILE_SOURCES:
                    self.process_dashboard_json_file(
                        rel_path,
                        source_system,
                        is_closed,
                        processed_json_paths,
                    )

            # 2. SQLite databases
            print("\n--- SQLite Databases ---")
            for db_path, source in SQLITE_SOURCES:
                self.process_sqlite_source(db_path, source)

            # 3. Portfolio state
            print("\n--- Portfolio State ---")
            self.process_portfolio_state()

            # 4. Discord sent tracking
            print("\n--- Discord Sent Tracking ---")
            self.process_discord_sent()

            # Finish success
            if not self.dry_run:
                self._finish_run()
        except Exception as e:
            self.stats["errors"] += 1
            self._fail_run(str(e))
            raise

        print("\n" + "=" * 60)
        print("SYNC COMPLETE")
        print("=" * 60)
        print(f"  Active picks inserted:  {self.stats['json_active_inserted']}")
        print(f"  Closed picks inserted:  {self.stats['json_closed_inserted']}")
        print(f"  Closed picks updated:   {self.stats['json_closed_updated']}")
        print(f"  SQLite picks inserted:  {self.stats['sqlite_inserted']}")
        print(f"  BT trades inserted:     {self.stats['bt_trades_inserted']}")
        print(f"  Dupes skipped:          {self.stats['dupes_skipped']}")
        print(f"  Rate limited:           {self.stats['rate_limited']}")
        print(f"  Errors:                 {self.stats['errors']}")
        print(f"  Sources processed:      {self.stats['sources_processed']}")
        total = (self.stats['json_active_inserted'] + self.stats['json_closed_inserted']
                 + self.stats['sqlite_inserted'])
        print(f"  TOTAL NEW PICKS:        {total}")
        print("=" * 60)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    syncer = PickSyncer(dry_run=dry_run)
    syncer.run()
