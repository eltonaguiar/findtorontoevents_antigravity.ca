"""Portfolio manager - allocates picks to portfolios, tracks P&L, manages positions.

NOTE — SNAPSHOT-RESOLVER ARTIFACT (2026-06-03): WR/PF here is inflated by single
daily-snapshot TP/SL resolution (no intrabar OHLC path) — intraday SL touches are missed.
Do not size up on these numbers. See docs/RESOLVER_SNAPSHOT_ARTIFACT_AFFECTED_PORTFOLIOS_2026-06-03.md

CODERED fixes (2026-04-14):
  - Position limits: max 1 pick per symbol per direction globally (no stacking)
  - SHORT cap: max 60% of open positions may be SHORT to prevent directional blowup
  - Confidence calibration: self-assigned confidence overridden by rolling forward WR
  - Fix 5: CI-based promotion pipeline — tier-based position sizing, killed-tier block
"""
import json
import logging
import pathlib
from collections import defaultdict
from datetime import datetime, timezone
from typing import List, Dict, Tuple

from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json, rate_limited
from paper_trading.multi_source import fetch_price as multi_fetch_price
from paper_trading.db import get_conn, init_portfolios
from paper_trading.strategies import STRATEGY_PORTFOLIO_MAP
from paper_trading.strategy_promotion_pipeline import (
    generate_tier_map, get_tier_multiplier, TIER_KILLED,
)

logger = logging.getLogger("paper_trading")

RISK_PER_TRADE = 0.02        # 2% of portfolio equity
MAX_SYMBOL_EXPOSURE = 0.10   # 10% max per symbol
TRANSACTION_COST = 0.007     # 0.7% round-trip for crypto
MAX_POSITIONS_PER_PORTFOLIO = 10
MAX_HOLD_DAYS = 7
DATA_DIR = pathlib.Path(__file__).parent / "data"

# ── CODERED Fix 2: Portfolio-level position limits ──
# Max 1 active position per (symbol, direction) across ALL portfolios.
# Prevents correlated stacking (e.g. 4 SOLUSDT shorts from different strategies).
MAX_POSITIONS_PER_SYMBOL_DIRECTION = 1
# Cap net SHORT exposure at this fraction of total active positions.
# 72% SHORT was observed in a rallying market — catastrophic.
MAX_SHORT_FRACTION = 0.60

# ── CODERED Fix 3: Confidence calibration ──
# When a strategy has >= MIN_CALIBRATION_TRADES closed picks with documented
# forward WR, override its self-assigned confidence with the calibrated value.
# Self-assigned confidence is algebraic (y = mx + b clamped to 0.55-0.90)
# and has zero correlation with actual win probability.
MIN_CALIBRATION_TRADES = 10
_CALIBRATION_CACHE: Dict[str, dict] = {}  # strategy_name -> {wr, n, calibrated_conf}


def _load_calibration_data() -> Dict[str, dict]:
    """Load closed picks and compute per-strategy rolling forward WR for confidence calibration.

    CODERED Fix 3: Self-assigned confidence is a deterministic algebraic output
    (signal distance mapped via y=mx+b, clamped to 0.55-0.90) that has ZERO
    correlation with actual win probability. Replace it with the empirical
    forward WR when sufficient data exists (n >= MIN_CALIBRATION_TRADES).
    """
    global _CALIBRATION_CACHE
    # Invalidate cache if closed_picks.json has been updated since last load
    closed_path = DATA_DIR / "closed_picks.json"
    try:
        _mtime = closed_path.stat().st_mtime if closed_path.exists() else 0
    except OSError:
        _mtime = 0
    if _CALIBRATION_CACHE and _CALIBRATION_CACHE.get("_mtime") == _mtime:
        return _CALIBRATION_CACHE
    _CALIBRATION_CACHE.clear()
    _CALIBRATION_CACHE["_mtime"] = _mtime  # store for invalidation check

    try:
        with open(closed_path, "r", encoding="utf-8") as f:
            closed_picks = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _CALIBRATION_CACHE

    # Group by strategy, compute WR
    by_strat: Dict[str, list] = defaultdict(list)
    for p in closed_picks:
        strat = p.get("strategy", p.get("algorithm", ""))
        if strat:
            by_strat[strat].append(p)

    for strat, trades in by_strat.items():
        n = len(trades)
        if n < MIN_CALIBRATION_TRADES:
            continue
        wins = sum(1 for t in trades if float(t.get("pnl_pct", 0) or 0) > 0)
        wr = wins / n  # 0.0 - 1.0
        # Map WR to calibrated confidence:
        # Formula: calibrated = 0.20 + 0.60 * WR, clamped to [0.40, 0.85]
        # WR 0.50 (coin flip) → conf 0.50 (no edge = low confidence)
        # WR 0.60 → conf 0.56, WR 0.70 → conf 0.62, WR 0.80+ → conf 0.68
        calibrated = max(0.40, min(0.85, 0.20 + 0.60 * wr))
        _CALIBRATION_CACHE[strat] = {
            "wr": round(wr, 4),
            "n": n,
            "calibrated_conf": round(calibrated, 3),
        }

    if _CALIBRATION_CACHE:
        logger.info(
            "CODERED Fix 3: Confidence calibration loaded for %d strategies (n>=%d): %s",
            len(_CALIBRATION_CACHE),
            MIN_CALIBRATION_TRADES,
            {k: f"WR={v['wr']:.0%}→conf={v['calibrated_conf']}" for k, v in _CALIBRATION_CACHE.items()},
        )
    return _CALIBRATION_CACHE


class PortfolioManager:
    def __init__(self):
        self.conn = get_conn()
        init_portfolios(self.conn)

    def process_picks(self, picks: List[NormalizedPick]) -> Dict[str, list]:
        """Main entry: allocate picks to portfolios, check TP/SL, return events."""
        events = {"entries": [], "exits": [], "updates": []}

        # 1. Check existing positions for TP/SL hits
        exits = self._check_exits()
        events["exits"] = exits

        # 1b. CODERED Fix 3: Calibrate confidence using rolling forward WR
        calibration = _load_calibration_data()
        for pick in picks:
            cal = calibration.get(pick.strategy)
            if cal:
                original_conf = pick.confidence
                pick.confidence = cal["calibrated_conf"]
                if abs(original_conf - pick.confidence) > 0.05:
                    logger.info(
                        "CODERED Fix 3: %s %s confidence %.2f → %.2f (WR=%.0f%%, n=%d)",
                        pick.strategy, pick.symbol, original_conf,
                        pick.confidence, cal["wr"] * 100, cal["n"],
                    )

        # 1c. CODERED Fix 5: Load CI-based tier map for position sizing + kill filter
        # NOTE: This is defense-in-depth — scanner.py (Fix 1) already skips
        # PERMANENTLY_KILLED_STRATEGIES before running them. This filter catches
        # strategies the pipeline demotes via CI evidence (e.g. WR lower-bound ≤ 50%)
        # even if they aren't on the explicit kill list.
        tier_map = generate_tier_map()
        killed_picks = [p for p in picks if tier_map.get(p.strategy) == TIER_KILLED]
        if killed_picks:
            killed_names = set(p.strategy for p in killed_picks)
            logger.warning(
                "CODERED Fix 5: Dropping %d picks from killed-tier strategies: %s",
                len(killed_picks), killed_names,
            )
            picks = [p for p in picks if tier_map.get(p.strategy) != TIER_KILLED]

        # 2. Assign conviction tiers
        tiered_picks = self._assign_conviction_tiers(picks)

        # 3. Allocate to strategy-type portfolios
        # CODERED Fix 2: Track global position counts for SHORT cap enforcement
        global_short_count = self._count_active_shorts()
        global_active_count = self._count_active_total()

        for pick, tier in tiered_picks:
            portfolio_type = STRATEGY_PORTFOLIO_MAP.get(pick.strategy, "technical")

            # CODERED Fix 2: Enforce max 1 position per symbol+direction globally
            existing_same_dir = self.conn.execute(
                "SELECT COUNT(*) FROM positions WHERE symbol=? AND direction=? AND status='ACTIVE'",
                (pick.symbol, pick.direction)
            ).fetchone()[0]
            if existing_same_dir >= MAX_POSITIONS_PER_SYMBOL_DIRECTION:
                logger.info(
                    "CODERED Fix 2: Rejected %s %s — already %d active %s position(s)",
                    pick.symbol, pick.direction, existing_same_dir, pick.direction,
                )
                continue

            # CODERED Fix 2: Enforce SHORT cap (max 60% of total positions)
            if pick.direction == "SHORT":
                projected_shorts = global_short_count + 1
                projected_total = global_active_count + 1
                short_fraction = projected_shorts / projected_total if projected_total > 0 else 0
                if short_fraction > MAX_SHORT_FRACTION:
                    logger.info(
                        "CODERED Fix 2: Rejected %s SHORT — would make %d/%d (%.0f%%) SHORTs, cap is %.0f%%",
                        pick.symbol, projected_shorts, projected_total,
                        short_fraction * 100, MAX_SHORT_FRACTION * 100,
                    )
                    continue

            entry_event = self._try_open_position(pick, portfolio_type, tier, tier_map)
            if entry_event:
                events["entries"].append(entry_event)
                global_active_count += 1  # track for SHORT cap calc
                if pick.direction == "SHORT":
                    global_short_count += 1  # only increment on successful open

        # 4. Snapshot equity
        self._snapshot_equity()

        # 5. Export JSON files
        self._export_json()

        return events

    def _count_active_shorts(self) -> int:
        """Count total active SHORT positions across all portfolios (CODERED Fix 2)."""
        row = self.conn.execute(
            "SELECT COUNT(*) FROM positions WHERE direction='SHORT' AND status='ACTIVE'"
        ).fetchone()
        return row[0] if row else 0

    def _count_active_total(self) -> int:
        """Count total active positions across all portfolios (CODERED Fix 2)."""
        row = self.conn.execute(
            "SELECT COUNT(*) FROM positions WHERE status='ACTIVE'"
        ).fetchone()
        return row[0] if row else 0

    def _assign_conviction_tiers(self, picks: List[NormalizedPick]) -> List[Tuple[NormalizedPick, str]]:
        """Group picks by (symbol, direction), assign conviction tier."""
        groups = defaultdict(list)
        for p in picks:
            key = (p.symbol, p.direction)
            groups[key].append(p)

        result = []
        for (symbol, direction), group in groups.items():
            if len(group) >= 3:
                tier = "high_conviction"
            elif len(group) == 2:
                tier = "medium_conviction"
            else:
                tier = "speculative"

            # Keep best pick per group (highest confidence)
            best = max(group, key=lambda p: p.confidence)
            # Boost confidence for consensus
            if len(group) >= 2:
                avg_conf = sum(p.confidence for p in group) / len(group)
                best.confidence = min(0.95, avg_conf + 0.05 * len(group))

            result.append((best, tier))

        return result

    def _try_open_position(self, pick: NormalizedPick, portfolio_type: str, tier: str,
                           tier_map: Dict[str, str] = None) -> dict:
        """Try to open a position in the given portfolio. Returns event dict or None.

        Args:
            tier: conviction tier (high_conviction / medium_conviction / speculative) —
                  aggregation-based, from _assign_conviction_tiers()
            tier_map: strategy promotion tier map from Fix 5 (incubator / probation /
                  standard / killed) — CI-based, for position sizing multiplier
        """
        # Check if already have this symbol in this portfolio
        existing = self.conn.execute(
            "SELECT COUNT(*) FROM positions WHERE symbol=? AND portfolio_type=? AND status='ACTIVE'",
            (pick.symbol, portfolio_type)
        ).fetchone()[0]
        if existing > 0:
            return None

        # Check position count limit
        active_count = self.conn.execute(
            "SELECT COUNT(*) FROM positions WHERE portfolio_type=? AND status='ACTIVE'",
            (portfolio_type,)
        ).fetchone()[0]
        if active_count >= MAX_POSITIONS_PER_PORTFOLIO:
            return None

        # Get portfolio state
        pf = self.conn.execute("SELECT * FROM portfolios WHERE name=?", (portfolio_type,)).fetchone()
        if not pf:
            return None
        cash = pf["cash"]
        equity = pf["equity"]

        # Position sizing: base 2% risk × promotion-tier multiplier (CODERED Fix 5)
        # Promotion tiers: incubator=0.25x, probation=0.50x, standard=1.0x, killed=0.0x
        dist_sl = abs(pick.entry_price - pick.sl)
        if dist_sl <= 0:
            return None
        tier_multiplier = get_tier_multiplier(pick.strategy, tier_map)
        risk_amount = equity * RISK_PER_TRADE * tier_multiplier
        if tier_multiplier != 1.0:
            logger.info(
                "CODERED Fix 5: %s %s position sizing %.2fx (promotion tier=%s)",
                pick.symbol, pick.direction, tier_multiplier,
                tier_map.get(pick.strategy, "incubator") if tier_map else "incubator",
            )
        shares = risk_amount / dist_sl
        position_usd = shares * pick.entry_price

        # Cap at max symbol exposure
        max_pos = equity * MAX_SYMBOL_EXPOSURE
        if position_usd > max_pos:
            position_usd = max_pos
            shares = position_usd / pick.entry_price

        # Check cash
        if position_usd > cash:
            return None

        now = datetime.now(timezone.utc).isoformat()
        pos_id = f"pt_{pick.strategy}::{pick.symbol}::{now[:19]}"

        # Insert position
        self.conn.execute("""
            INSERT OR REPLACE INTO positions
            (id, symbol, direction, entry_price, current_price, tp, sl,
             strategy, strategy_name, portfolio_type, conviction_tier,
             position_size_usd, shares, entry_date, status, confidence, reason)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (pos_id, pick.symbol, pick.direction, pick.entry_price, pick.entry_price,
              pick.tp, pick.sl, pick.strategy, pick.strategy_name,
              portfolio_type, tier, round(position_usd, 2), round(shares, 6),
              now, "ACTIVE", pick.confidence, pick.reason))

        # Update portfolio cash
        new_cash = cash - position_usd
        self.conn.execute("UPDATE portfolios SET cash=? WHERE name=?", (round(new_cash, 2), portfolio_type))

        # Also open in conviction-tier portfolio
        tier_pf = self.conn.execute("SELECT * FROM portfolios WHERE name=?", (tier,)).fetchone()
        if tier_pf:
            tier_cash = tier_pf["cash"]
            if position_usd <= tier_cash:
                tier_pos_id = f"pt_{tier}_{pick.strategy}::{pick.symbol}::{now[:19]}"
                existing_tier = self.conn.execute(
                    "SELECT COUNT(*) FROM positions WHERE symbol=? AND portfolio_type=? AND status='ACTIVE'",
                    (pick.symbol, tier)
                ).fetchone()[0]
                if existing_tier == 0:
                    self.conn.execute("""
                        INSERT OR REPLACE INTO positions
                        (id, symbol, direction, entry_price, current_price, tp, sl,
                         strategy, strategy_name, portfolio_type, conviction_tier,
                         position_size_usd, shares, entry_date, status, confidence, reason)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (tier_pos_id, pick.symbol, pick.direction, pick.entry_price, pick.entry_price,
                          pick.tp, pick.sl, pick.strategy, pick.strategy_name,
                          tier, tier, round(position_usd, 2), round(shares, 6),
                          now, "ACTIVE", pick.confidence, pick.reason))
                    self.conn.execute("UPDATE portfolios SET cash=? WHERE name=?",
                                     (round(tier_cash - position_usd, 2), tier))

        self.conn.commit()

        return {
            "type": "entry",
            "symbol": pick.symbol,
            "direction": pick.direction,
            "entry_price": pick.entry_price,
            "tp": pick.tp,
            "sl": pick.sl,
            "position_usd": round(position_usd, 2),
            "portfolio": portfolio_type,
            "tier": tier,
            "strategy": pick.strategy_name,
            "confidence": pick.confidence,
            "reason": pick.reason,
            "risk_reward": pick.risk_reward,
        }

    def _check_exits(self) -> list:
        """Check all active positions for TP/SL hits using latest prices."""
        exits = []
        active = self.conn.execute("SELECT * FROM positions WHERE status='ACTIVE'").fetchall()

        # Group by symbol for efficient price fetching
        symbols = set(row["symbol"] for row in active)
        prices = {}
        for sym in symbols:
            try:
                ticker = self._fetch_price(sym)
                prices[sym] = float(ticker.get("price", 0))
            except Exception:
                continue

        now = datetime.now(timezone.utc).isoformat()

        for pos in active:
            symbol = pos["symbol"]
            current = prices.get(symbol, 0)
            if current <= 0:
                continue

            entry = pos["entry_price"]
            direction = pos["direction"]

            if direction == "LONG":
                pnl_pct = ((current - entry) / entry) * 100
                mfe = max(pos["mfe"], pnl_pct)
                mae = min(pos["mae"], pnl_pct)
                tp_hit = current >= pos["tp"]
                sl_hit = current <= pos["sl"]
            else:  # SHORT
                pnl_pct = ((entry - current) / entry) * 100
                mfe = max(pos["mfe"], pnl_pct)
                mae = min(pos["mae"], pnl_pct)
                tp_hit = current <= pos["tp"]
                sl_hit = current >= pos["sl"]

            # Check max hold
            try:
                entry_dt = datetime.fromisoformat(pos["entry_date"].replace("Z", "+00:00"))
            except ValueError:
                entry_dt = datetime.now(timezone.utc)
            now_dt = datetime.now(timezone.utc)
            hold_days = (now_dt - entry_dt).days
            expired = hold_days >= MAX_HOLD_DAYS

            status = "ACTIVE"
            exit_reason = ""
            if tp_hit:
                status = "TP_HIT"
                exit_reason = "Take profit hit"
            elif sl_hit:
                status = "SL_HIT"
                exit_reason = "Stop loss hit"
            elif expired:
                status = "EXPIRED"
                exit_reason = f"Max hold {hold_days}d exceeded"

            # Apply transaction costs to P&L
            net_pnl_pct = pnl_pct - (TRANSACTION_COST * 100)
            pnl_usd = pos["position_size_usd"] * net_pnl_pct / 100

            # Update position
            self.conn.execute("""
                UPDATE positions SET current_price=?, pnl_pct=?, pnl_usd=?,
                mfe=?, mae=?, status=?, exit_price=?, exit_date=?
                WHERE id=?
            """, (current, round(net_pnl_pct, 3), round(pnl_usd, 2),
                  round(mfe, 3), round(mae, 3),
                  status,
                  current if status != "ACTIVE" else None,
                  now if status != "ACTIVE" else None,
                  pos["id"]))

            if status != "ACTIVE":
                # Update portfolio
                portfolio = pos["portfolio_type"]
                pf = self.conn.execute("SELECT * FROM portfolios WHERE name=?", (portfolio,)).fetchone()
                if pf:
                    new_cash = pf["cash"] + pos["position_size_usd"] + pnl_usd
                    new_equity = new_cash + self._get_active_value(portfolio)
                    new_trades = pf["total_trades"] + 1
                    new_wins = pf["wins"] + (1 if pnl_usd > 0 else 0)
                    new_losses = pf["losses"] + (1 if pnl_usd <= 0 else 0)
                    new_peak = max(pf["peak_equity"], new_equity)
                    dd = ((new_peak - new_equity) / new_peak * 100) if new_peak > 0 else 0
                    new_dd = max(pf["max_drawdown_pct"], dd)

                    self.conn.execute("""
                        UPDATE portfolios SET cash=?, equity=?, total_trades=?,
                        wins=?, losses=?, peak_equity=?, max_drawdown_pct=?
                        WHERE name=?
                    """, (round(new_cash, 2), round(new_equity, 2), new_trades,
                          new_wins, new_losses, round(new_peak, 2), round(new_dd, 2),
                          portfolio))

                exits.append({
                    "type": "exit",
                    "symbol": symbol,
                    "direction": direction,
                    "status": status,
                    "entry_price": entry,
                    "exit_price": current,
                    "pnl_pct": round(net_pnl_pct, 2),
                    "pnl_usd": round(pnl_usd, 2),
                    "hold_days": hold_days,
                    "portfolio": portfolio,
                    "strategy": pos["strategy_name"],
                    "reason": exit_reason,
                })

        self.conn.commit()
        return exits

    def _get_active_value(self, portfolio_name: str) -> float:
        """Sum of current market value for active positions in portfolio."""
        rows = self.conn.execute(
            "SELECT position_size_usd, pnl_usd FROM positions WHERE portfolio_type=? AND status='ACTIVE'",
            (portfolio_name,)
        ).fetchall()
        return sum(r["position_size_usd"] + r["pnl_usd"] for r in rows)

    def _fetch_price(self, symbol: str) -> dict:
        return multi_fetch_price(symbol)

    def _snapshot_equity(self):
        """Take equity snapshot for all portfolios."""
        now = datetime.now(timezone.utc).isoformat()
        portfolios = self.conn.execute("SELECT * FROM portfolios").fetchall()
        for pf in portfolios:
            active_value = self._get_active_value(pf["name"])
            equity = pf["cash"] + active_value
            self.conn.execute("UPDATE portfolios SET equity=? WHERE name=?",
                              (round(equity, 2), pf["name"]))
            self.conn.execute(
                "INSERT INTO equity_snapshots (portfolio_name, equity, timestamp) VALUES (?,?,?)",
                (pf["name"], round(equity, 2), now))
        self.conn.commit()

    def get_portfolio_summary(self) -> list:
        """Return all portfolio stats for Discord reporting."""
        portfolios = self.conn.execute("SELECT * FROM portfolios ORDER BY portfolio_type, name").fetchall()
        result = []
        for pf in portfolios:
            active = self.conn.execute(
                "SELECT COUNT(*) FROM positions WHERE portfolio_type=? AND status='ACTIVE'",
                (pf["name"],)
            ).fetchone()[0]
            wr = (pf["wins"] / pf["total_trades"] * 100) if pf["total_trades"] > 0 else 0
            pnl_pct = ((pf["equity"] - pf["starting_capital"]) / pf["starting_capital"]) * 100

            result.append({
                "name": pf["name"],
                "type": pf["portfolio_type"],
                "equity": pf["equity"],
                "cash": pf["cash"],
                "pnl_pct": round(pnl_pct, 2),
                "total_trades": pf["total_trades"],
                "wins": pf["wins"],
                "losses": pf["losses"],
                "win_rate": round(wr, 1),
                "active_positions": active,
                "max_drawdown": pf["max_drawdown_pct"],
            })
        return result

    def _export_json(self):
        """Export current state to JSON files for Git commits."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Active picks — enriched with strategy metadata
        active = self.conn.execute("SELECT * FROM positions WHERE status='ACTIVE'").fetchall()
        active_list = []
        try:
            from paper_trading.strategies import STRATEGY_METADATA
        except ImportError:
            STRATEGY_METADATA = {}
        for r in active:
            pick = dict(r)
            meta = STRATEGY_METADATA.get(pick.get("strategy", ""), {})
            pick["system_name"] = meta.get("system_name", "Paper Trading")
            pick["dashboard_url"] = meta.get("dashboard_url", "")
            pick["display_name"] = meta.get("display_name", pick.get("strategy_name", ""))
            active_list.append(pick)
        (DATA_DIR / "active_picks.json").write_text(json.dumps(active_list, indent=2))

        # Closed picks
        closed = self.conn.execute(
            "SELECT * FROM positions WHERE status!='ACTIVE' ORDER BY exit_date DESC LIMIT 500"
        ).fetchall()
        closed_list = [dict(r) for r in closed]
        (DATA_DIR / "closed_picks.json").write_text(json.dumps(closed_list, indent=2))

        # Portfolio summary
        summary = self.get_portfolio_summary()
        (DATA_DIR / "portfolios.json").write_text(json.dumps(summary, indent=2))

        # Performance with history
        perf = {"portfolios": summary, "updated_at": datetime.now(timezone.utc).isoformat()}
        (DATA_DIR / "performance.json").write_text(json.dumps(perf, indent=2))

    def close(self):
        self.conn.close()
