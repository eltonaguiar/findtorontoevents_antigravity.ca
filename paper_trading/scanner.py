"""Main scanner entry point - runs all strategies, feeds portfolio manager, reports to Discord.

Integrates with central audit trail (ejaguiar1_stocks MySQL) to track all picks and outcomes.

CODERED fixes (2026-04-14):
  - Quality gate enforcement: PERMANENTLY_KILLED_STRATEGIES are auto-excluded
  - Position limits passed to PortfolioManager (max 1 per symbol+direction, SHORT cap 60%)
  - Confidence calibration: self-assigned confidence overridden by rolling forward WR
  - Fix 5: CI-based promotion pipeline (incubator → probation → standard → killed)
"""
import logging
from datetime import datetime, timezone

from paper_trading.strategies import ALL_STRATEGIES
from paper_trading.portfolio_manager import PortfolioManager
from paper_trading import discord_reporter
from paper_trading.multi_source import clear_cache as clear_price_cache, get_cache_stats

# ── CODERED Fix 1: Quality gate enforcement ──
# Import the main engine's kill list so toxic strategies (0% WR, six-figure losses)
# are auto-excluded from paper trading scans.
try:
    from audit_trail.quality_gates import PERMANENTLY_KILLED_STRATEGIES as _KILLED
    _KILLED_LOWER = {s.lower() for s in _KILLED}
except ImportError:
    _KILLED_LOWER = set()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("paper_trading")


def _source_system_for_strategy(strategy_name: str) -> str:
    """Map strategy name to audit trail source_system identifier.

    Uses the actual strategy display_name so audit trail shows
    'Hoffman Kalman Trend' instead of 'paper_hoffman_irb'.
    """
    from paper_trading.strategies import STRATEGY_METADATA
    meta = STRATEGY_METADATA.get(strategy_name)
    if meta:
        return meta["display_name"]
    # Fallback for unknown strategies
    return strategy_name.replace("_", " ").title()


def _audit_raw_picks(picks, run_id):
    """Record all raw picks to the audit trail. Returns pick_id map."""
    try:
        from audit_trail import record_raw_pick, record_filter
    except ImportError:
        logger.warning("audit_trail module not available — skipping audit recording")
        return {}

    pick_id_map = {}  # NormalizedPick.id -> audit pick_id
    for pick in picks:
        source = _source_system_for_strategy(pick.strategy)
        from paper_trading.strategies import STRATEGY_METADATA
        meta = STRATEGY_METADATA.get(pick.strategy)
        pick_dict = {
            "symbol": pick.symbol,
            "direction": pick.direction,
            "entry_price": pick.entry_price,
            "take_profit": pick.tp,
            "stop_loss": pick.sl,
            "confidence": pick.confidence,
            "strategy": pick.strategy_name,
            "timestamp": pick.picked_at,
            "reason": pick.reason,
            "risk_reward": pick.risk_reward,
            "category": getattr(pick, "category", ""),
            "system_name": meta.get("system_name", "") if meta else "",
            "dashboard_url": meta.get("dashboard_url", "") if meta else "",
            "raw_signal": getattr(pick, "raw_signal", None),
            "data_source": meta.get("source", "Multi-Source") if meta else "Multi-Source",
        }
        try:
            audit_id = record_raw_pick(source, pick_dict, run_id)
            if audit_id:
                pick_id_map[pick.id] = audit_id
        except Exception as e:
            logger.debug(f"Audit record_raw_pick failed for {pick.symbol}: {e}")
    return pick_id_map


def _audit_entries(entries, run_id):
    """Record opened positions as consensus picks in the audit trail."""
    try:
        from audit_trail import record_consensus_pick, record_event
    except ImportError:
        return

    for entry in entries:
        source = _source_system_for_strategy(entry.get("strategy", ""))

        # Get rich metadata for this strategy
        from paper_trading.strategies import STRATEGY_METADATA
        meta = STRATEGY_METADATA.get(entry.get("strategy", ""), {})
        system_name = meta.get("system_name", source)
        dashboard_url = meta.get("dashboard_url", "")

        pick_dict = {
            "symbol": entry["symbol"],
            "direction": entry["direction"],
            "entry_price": entry["entry_price"],
            "take_profit": entry["tp"],
            "stop_loss": entry["sl"],
            "confidence": entry.get("confidence", 0.5),
            "agreement_count": 1,
            "source_systems": [source],
            "source_strategies": {source: entry.get("strategy", "")},
            "consensus_tier": entry.get("tier", "speculative"),
            "classification": entry.get("portfolio", ""),
            "system_name": system_name,
            "dashboard_url": dashboard_url,
        }
        try:
            pick_id = record_consensus_pick(pick_dict, run_id)
            record_event(
                "PAPER_POSITION_OPENED",
                pick_id=pick_id,
                run_id=run_id,
                symbol=entry["symbol"],
                payload={
                    "portfolio": entry.get("portfolio"),
                    "position_usd": entry.get("position_usd"),
                    "risk_reward": entry.get("risk_reward"),
                    "strategy": entry.get("strategy"),
                },
                origin="paper_trading",
            )
        except Exception as e:
            logger.debug(f"Audit record_consensus_pick failed for {entry['symbol']}: {e}")


def _audit_exits(exits, run_id):
    """Record closed positions in the audit trail."""
    try:
        from audit_trail import record_event
    except ImportError:
        return

    for ex in exits:
        status = ex.get("status", "EXPIRED")
        outcome = "WON" if ex.get("pnl_usd", 0) > 0 else "LOST"
        try:
            record_event(
                f"PAPER_POSITION_CLOSED_{outcome}",
                run_id=run_id,
                symbol=ex["symbol"],
                payload={
                    "direction": ex["direction"],
                    "entry_price": ex["entry_price"],
                    "exit_price": ex["exit_price"],
                    "pnl_pct": ex.get("pnl_pct"),
                    "pnl_usd": ex.get("pnl_usd"),
                    "hold_days": ex.get("hold_days"),
                    "portfolio": ex.get("portfolio"),
                    "strategy": ex.get("strategy"),
                    "exit_reason": ex.get("reason", status),
                },
                origin="paper_trading",
            )
        except Exception as e:
            logger.debug(f"Audit exit event failed for {ex['symbol']}: {e}")


def main():
    logger.info("=" * 60)
    logger.info(f"Paper Trading Scanner v2.1 -- {len(ALL_STRATEGIES)} strategies, audit trail")
    logger.info("=" * 60)

    # 0. Start audit trail run
    run_id = None
    try:
        from audit_trail import start_run, finish_run, refresh_strategy_stats
        run_id = start_run(regime_data={"scanner": "paper_trading", "version": "2.0"})
        logger.info(f"Audit trail run started: {run_id}")
    except Exception as e:
        logger.warning(f"Audit trail unavailable: {e}")

    # 0b. Clear multi-source price cache for fresh data
    clear_price_cache()

    # 1. Run all strategies — CODERED Fix 1: skip quality-gate-killed strategies
    all_picks = []
    skipped_killed = []
    for strategy in ALL_STRATEGIES:
        # Quality gate: skip strategies on the permanent kill list
        if strategy.name.lower() in _KILLED_LOWER:
            skipped_killed.append(strategy.name)
            logger.warning(f"CODERED: Skipping killed strategy {strategy.name}")
            continue
        try:
            picks = strategy.run()
            all_picks.extend(picks)
        except Exception as e:
            logger.error(f"Strategy {strategy.name} crashed: {e}")

    if skipped_killed:
        logger.info(f"CODERED: Skipped {len(skipped_killed)} killed strategies: {skipped_killed}")
    logger.info(f"Total raw picks: {len(all_picks)}")
    cache_stats = get_cache_stats()
    logger.info(f"Multi-source cache: {cache_stats['kline_valid']} kline entries, "
                f"{cache_stats['price_valid']} price entries (shared across strategies)")

    # 1b. Record raw picks to audit trail
    if run_id:
        _audit_raw_picks(all_picks, run_id)

    # 2. Feed to portfolio manager
    pm = PortfolioManager()
    try:
        events = pm.process_picks(all_picks)

        entries = events.get("entries", [])
        exits = events.get("exits", [])
        logger.info(f"New entries: {len(entries)}")
        logger.info(f"Exits (TP/SL/expiry): {len(exits)}")

        # 2b. Record entries and exits to audit trail
        if run_id:
            _audit_entries(entries, run_id)
            _audit_exits(exits, run_id)

        # 3. Get portfolio summary
        summary = pm.get_portfolio_summary()

        # 4. Report to Discord
        discord_reporter.send_events(events, portfolio_summary=summary)

        # 5. Print summary to stdout for CI logs
        print("\nPortfolio Summary:")
        for p in summary:
            print(f"  {p['name']:<18} ${p['equity']:>10,.2f}  {p['pnl_pct']:>+7.2f}%  "
                  f"WR: {p['win_rate']:>5.1f}%  Trades: {p['total_trades']}")

        print(f"\nScanner complete at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

        # 6. Sync positions to MySQL (for Hoffman tracker + analytics)
        try:
            from paper_trading.mysql_sync import sync_to_mysql
            synced = sync_to_mysql()
            logger.info(f"MySQL sync: {synced} positions synced to at_signal_outcomes")
        except Exception as e:
            logger.warning(f"MySQL sync failed (non-fatal): {e}")

        # 6b. Check incubator promotions (legacy binary check)
        try:
            from paper_trading.incubator_promotion import check_promotions
            promo = check_promotions()
            if promo.get("promoted"):
                names = [s["strategy"] for s in promo["promoted"]]
                logger.info(f"INCUBATOR PROMOTIONS: {names} qualified for verified!")
            needs = len(promo.get("needs_data", []))
            under = len(promo.get("underperforming", []))
            logger.info(f"Incubator status: {len(promo.get('promoted', []))} promoted, "
                        f"{needs} need data, {under} underperforming")
        except Exception as e:
            logger.debug(f"Incubator check skipped: {e}")

        # 6c. CODERED Fix 5: CI-based promotion pipeline (3-tier)
        try:
            from paper_trading.strategy_promotion_pipeline import generate_tier_map, get_promotion_report, TIER_KILLED
            tier_map = generate_tier_map()
            report = get_promotion_report()
            logger.info("CODERED Fix 5: Promotion pipeline — %s", report["summary"])
            # Export tier map for portfolio_manager to use
            import json, pathlib
            data_dir = pathlib.Path(__file__).parent / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            (data_dir / "strategy_tiers.json").write_text(
                json.dumps({"tiers": tier_map, "updated_at": datetime.now(timezone.utc).isoformat()}, indent=2)
            )
            # Log killed strategies for visibility
            killed = [s for s, t in tier_map.items() if t == TIER_KILLED]
            if killed:
                logger.warning("CODERED Fix 5: Killed strategies (0x allocation): %s", killed)
        except Exception as e:
            logger.warning(f"CODERED Fix 5: Promotion pipeline failed (non-fatal): {e}")

        # 7. Finish audit trail run & refresh stats
        if run_id:
            try:
                finish_run(run_id, consensus_count=len(entries),
                           systems_loaded=len(ALL_STRATEGIES), raw_count=len(all_picks))
                refresh_strategy_stats()
                logger.info("Audit trail run completed & stats refreshed")
            except Exception as e:
                logger.warning(f"Audit trail finish failed: {e}")

    finally:
        pm.close()


if __name__ == "__main__":
    main()
