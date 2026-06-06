#!/usr/bin/env python3
"""
Universal Pick Resolver — checks TP/SL/time exits for ALL systems.

This script runs as part of the audit trail pipeline and resolves active picks
across ALL trading systems by checking live prices against TP/SL levels.
Systems that already have their own tracker (rapid_fire, alpha_engine) are skipped
unless they have stale active picks.

The resolver writes resolved (closed) picks to a unified file that the
dashboard_generator reads during payload generation.

Usage:  python -m audit_trail.universal_pick_resolver
"""
import json
import logging
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from audit_trail.pnl_ingest_sanity import apply_pnl_clamp_to_pick
from alpha_engine.asset_class import normalize_asset_class
from audit_trail.asset_classification import classify_asset
from audit_trail.reverse_split_symbols import should_adjust_for_split

MAX_HOLD_HOURS = 48  # Default auto-expire (CRYPTO; unchanged)
RESOLVER_VERSION = "universal_v2.1"  # EAGLE2 2026-06-02: provenance tracking
RESOLVER_SOURCE_ID = "universal_pick_resolver"  # EAGLE2 2026-06-02: source provenance tag
# 2026-05-03 (CLAUDE_DEBUGGING_GUIDE.MD Step 7): non-crypto markets resolve
# slower than crypto. 24-48h was biased against forex/bonds (5-14 days to
# resolve TP/SL). Per-class hold window prevents premature TIME_EXIT closes
# from masking true win rate on slow markets while preserving crypto cadence.
MAX_HOLD_HOURS_BY_CLASS = {
    "CRYPTO": 48,
    "EQUITY": 96,
    "ETF": 96,
    "COMMODITY": 96,
    "FUTURES": 96,
    "FOREX": 72,  # EAGLE2 2026-06-02: unified to 72h (was 120)
    "BOND": 120,
}


def _max_hold_hours_for(pick: dict) -> int:
    """Return the per-asset-class TIME_EXIT window in hours.

    Bug fix 2026-05-04 (post-#745, swarm 6/7 R2 verdict): normalize_asset_class
    expects a pick dict, not a pre-extracted string. Passing the original `ac`
    string raised AttributeError silently swallowed by `except Exception`, so
    symbol-based classification (e.g. EURUSD=X with no `asset_class` field)
    fell back to MAX_HOLD_HOURS=48 instead of FOREX=120.
    """
    raw = str(pick.get("asset_class", "") or "").upper()
    try:
        normalized = normalize_asset_class(pick)
        ac = (normalized or raw).upper()
    except (AttributeError, TypeError):
        ac = raw
    return MAX_HOLD_HOURS_BY_CLASS.get(ac, MAX_HOLD_HOURS)


RESOLVED_FILE = ROOT / "audit_trail" / "data" / "universal_resolved_picks.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("universal_resolver")

# Systems that have their own tracker and should skip universal resolution
# (unless their picks are stale > 48h)
SELF_TRACKED_SYSTEMS = {"alpha_engine", "alpha_engine_fast", "rapid_fire", "paper_trading"}
CLOSED_STATUSES = {
    "CLOSED", "RESOLVED", "TIME_EXIT", "EXPIRED",
    "TP_HIT", "SL_HIT", "TRAIL", "MAX_HOLD",
    "FORCE_CLOSED", "WON", "LOST", "FLAT",
}

# All system JSON pick sources (system_name, active_path)
# Must mirror JSON_PICK_SOURCES in dashboard_generator.py so every system's
# picks get resolved (TP/SL checked).  Systems in SELF_TRACKED_SYSTEMS are
# still listed here so that stale picks (>48h) get time-exited.
SYSTEM_SOURCES = [
    # ── Core systems ──
    ("alpha_engine",             "alpha_engine/data/active_picks.json"),
    ("battleground",             "battleground/data/active_picks.json"),
    ("mercury2",                 "mercury2/data/active_picks.json"),
    ("paper_trading",            "paper_trading/data/active_picks.json"),
    ("crypto_signal_engine",     "crypto_signal_engine/data/active_picks.json"),
    ("coinglass",                "coinglass_strategies/data/active_picks.json"),
    ("crypto_ml_edge",           "crypto_ml_edge/data/active_picks.json"),
    ("rl_agent",                 "rl_agent/data/active_picks.json"),
    ("copy_trader_intel",        "copy_trader_intel/data/active_picks.json"),
    ("copy_trader_highscore",    "copy_trader_intel/data/highscore_active_picks.json"),
    ("copy_trader_clones",       "copy_trader_intel/data/clone_active_picks.json"),
    ("copy_trader_consensus",    "copy_trader_intel/data/consensus_active_picks.json"),
    ("genome",                   "genome/data/universal_picks.json"),
    ("predictions",              "predictions/data/active_predictions.json"),
    ("super_signals",            "cross_aggregation/data/super_signals.json"),
    ("regime_terminal",          "regime_terminal/data/active_signals.json"),
    ("quan_engine",              "quan_engine/data/active_signals.json"),
    ("ml_crypto_pred",           "ml_crypto_predictor/enhanced_models/live_picks/active_picks.json"),
    ("crypto_gainer_ml",         "crypto_gainer_ml/tracker/live_picks.json"),
    ("claude_gainer_st",         "claude_gainer_ml/tracker/short_term_active.json"),
    ("fc_crypto_pro",            "data/fc_crypto_pro_picks.json"),
    # ── ML Battleground systems ──
    ("ml_bg_system_a",           "ml_battleground/system_a_filter/data/active_picks.json"),
    ("ml_bg_system_b",           "ml_battleground/system_b_regime/data/active_picks.json"),
    ("ml_bg_system_c",           "ml_battleground/system_c_deeplearn/data/active_picks.json"),
    ("ml_bg_system_d",           "ml_battleground/system_d_carry/data/active_picks.json"),
    ("ml_bg_system_e",           "ml_battleground/system_e_momentum/data/active_picks.json"),
    ("ml_bg_system_f",           "ml_battleground/system_f_clawsofdoom/data/active_picks.json"),
    ("ml_bg_ensemble",           "ml_battleground/ensemble_data/active_picks.json"),
    # ── Breakout Arena ──
    ("breakout_a_sr",            "breakout_arena/approach_a_sr_breakout/data/active_picks.json"),
    ("breakout_b_ml",            "breakout_arena/approach_b_ml_breakout/data/active_picks.json"),
    ("breakout_c_spike",         "breakout_arena/approach_c_spike_reverse/data/active_picks.json"),
    # ── DARWIN ENGINE / Genome Evolution Systems ──
    ("genetic_programmer",       "genome/data/gp_active_picks.json"),
    ("audit_ensemble",           "genome/data/ae_active_picks.json"),
    ("mape_evolver",             "genome/data/mape_active_picks.json"),
    ("ensemble_evolver",         "genome/data/ensemble_active_picks.json"),
    ("neat_neural",              "genome/data/neat_active_picks.json"),
    ("hyperparam_dna",           "genome/data/hyperparam_active_picks.json"),
    ("failure_evolver",          "genome/data/failure_evolved_picks.json"),
    ("momentum_evolver",         "genome/data/momentum_active_picks.json"),
    ("multitf_evolver",          "genome/data/multitf_active_picks.json"),
    ("contrarian_evolver",       "genome/data/contrarian_active_picks.json"),
    ("macd_dna_mutations",       "genome/data/macd_mutation_picks.json"),
    ("mutation_lab",             "genome/data/mutation_lab_picks.json"),
    ("pumpwatch_mutations",      "genome/data/pumpwatch_mutation_picks.json"),
    ("signal_engine_mutations",  "genome/data/signal_engine_mutation_picks.json"),
    ("dna_winner_picks",         "genome/data/dna_winner_picks.json"),
    ("battleground_mutations",   "genome/data/battleground_mutation_picks.json"),
    ("mega_mutation",            "genome/data/mega_mutation_picks.json"),
    ("universal_picks",          "genome/data/universal_picks.json"),
    # ── Revival systems (stale-system reviver) ──
    ("revival_all",              "genome/data/revival_all_picks.json"),
    ("revival_battleground",     "genome/data/revival_battleground_picks.json"),
    ("revival_breakout_a",       "genome/data/revival_breakout_a_pure_sr_picks.json"),
    ("revival_breakout_b",       "genome/data/revival_breakout_b_ml_picks.json"),
    ("revival_signal_engine",    "genome/data/revival_crypto_signal_engine_picks.json"),
    ("revival_kimi",             "genome/data/revival_kimi_riseoftheclaw_picks.json"),
    ("revival_mercury2",         "genome/data/revival_mercury2_picks.json"),
    ("revival_paper_trading",    "genome/data/revival_paper_trading_picks.json"),
    ("revival_breakout_spike",   "genome/data/revival_breakout_spike_picks.json"),
    ("revival_crypto_gainer_ml", "genome/data/revival_crypto_gainer_ml_picks.json"),
    ("revival_ml_system_b_regime", "genome/data/revival_ml_system_b_regime_picks.json"),
    ("revival_ml_system_c_deeplearn", "genome/data/revival_ml_system_c_deeplearn_picks.json"),
    ("trusted_genome",           "genome/data/trusted_genome_picks_live.json"),
    ("dna_rapid_fire_mutations", "genome/data/rapid_fire_mutation_picks.json"),
    ("dna_confluence_mutations", "genome/data/confluence_mutation_picks.json"),
    # ── KIMI / Rise of the Claw ──
    ("kimi_live_signals",        "KIMI_RISEOFTHECLAW/data/live_signals_now.json"),
    ("riseoftheclaw",            "riseoftheclaw/data/active_picks.json"),
    ("kimi_signal_tracking",     "riseoftheclaw/data/signal_tracking.json"),
    ("kimi_claw_research",       "KIMI_CLAW_RESEARCH_FEB162026/data/active_picks.json"),
    ("deploy_riseoftheclaw",     "deploy_riseoftheclaw/riseoftheclaw/data/active_picks.json"),
    # ── Aggregators & Cross-System ──
    ("aggregated_picks",         "data/aggregated_picks.json"),
    ("signal_aggregator",        "signal_aggregator/data/master_picks_tracker.json"),
    ("incubator_gainer",         "incubator/agents/claude_code_01/data/gainer_scores_latest.json"),
    ("incubator_battleground",   "battleground/data/incubator_signals.json"),
    ("agreement_alpha",          "ml_battleground/ensemble_data/agreement_alpha_picks.json"),
    ("chatgpt_combined",         "battleground/data/chatgpt_combined_signals.json"),
    # ── LuxAlgo Filters ──
    ("luxalgo_filters",          "battleground/data/luxalgo_active_picks.json"),
    # ── Meme Scanner & Live Spike Trader ──
    ("meme_scanner",             "data/meme_scanner_active.json"),
    ("live_spike_trader",        "data/spike_trader_active.json"),
    # ── Prop Firm Strategies ──
    ("prop_firm_strategies",     "audit_trail/data/prop_firm_picks.json"),
    # ── Alpha Engine FAST ──
    ("alpha_engine_fast",        "alpha_engine/data/active_picks_fast.json"),
    # ── Multi-Asset (forex + equity + crypto institutional) ──
    ("multi_asset",              "multi_asset/data/active_picks.json"),
    ("multi_asset_institutional","multi_asset/data/institutional_picks.json"),
    # ── Rapid Fire (NOW.py) ──
    ("rapid_fire",               "rapid_fire_data/active_picks.json"),
    # ── Stock & Multi-Asset competitions ──
    ("stocks_competition",       "STOCKS/competition/forward_picks.json"),
    ("stocks_crypto_comp",       "STOCKS/competition/competition-crypto.json"),
    ("stocks_forex_comp",        "STOCKS/competition/competition-forex.json"),
    ("stocks_penny_comp",        "STOCKS/competition/competition-penny_stocks.json"),
    ("stocks_meme_comp",         "STOCKS/competition/competition-meme_coins.json"),
    ("goldmine_stocks",          "data/goldmine/stock_picks.json"),
    ("goldmine_meme",            "data/goldmine/meme_winners.json"),
    ("goldmine_unified",         "data/goldmine/unified_picks.json"),
    # ── ABC Forward Test ──
    ("abc_forward_a",            "ml_battleground/abc_forward_test/data/approach_a_picks.json"),
    ("abc_forward_b",            "ml_battleground/abc_forward_test/data/approach_b_picks.json"),
    ("abc_forward_c",            "ml_battleground/abc_forward_test/data/approach_c_picks.json"),
    # ── ML Crypto Predictor v1.2 archive ──
    ("ml_crypto_pred_v12",       "ml_crypto_predictor/enhanced_models/live_picks/archive_v1.2/active_picks.json"),
    # ── Signal Validation DB ──
    ("signal_validation",        "signals_database.json"),
    # ── Incubator forward signals ──
    ("forward_signals",          "incubator/backtest_results/forward_signals.json"),
    # ── Prediction market agents ──
    ("polymarket_signals",       "alpha_engine/data/polymarket_signals.json"),
    ("pm_momentum_signals",      "prediction_market_agents/data/momentum_signals.json"),
    ("pm_whale_signals",         "prediction_market_agents/data/whale_signals.json"),
    ("pm_kalshi_signals",        "prediction_market_agents/data/kalshi_signals.json"),
    # ── AI Challenge Curators ──
    ("ai_challenge_claude",          "audit_dashboard/data/ai_challenge_claude_active_picks.json"),
    ("ai_challenge_grok",            "audit_dashboard/data/ai_challenge_grok_active_picks.json"),
    ("ai_challenge_kimi_moonshot",   "audit_dashboard/data/ai_challenge_kimi_moonshot_active_picks.json"),
    ("ai_challenge_antigravity",     "audit_dashboard/data/ai_challenge_antigravity_active_picks.json"),
    ("ai_challenge_mercury",         "audit_dashboard/data/ai_challenge_mercury_active_picks.json"),
    ("ai_challenge_predictable",     "audit_dashboard/data/ai_challenge_predictable_active_picks.json"),
    ("ai_challenge_scanner",         "audit_dashboard/data/ai_challenge_scanner_active_picks.json"),
    # ── Proven Strategies (backtested, research-backed) ──
    ("proven_strategies",            "proven_strategies/data/proven_strategy_picks.json"),
    # ── TradingAgents multi-role LLM consensus (B23 wireup, 2026-05-01)
    # PR #544 added the emitter; PR #582 registered ueps_picks.json in
    # JSON_PICK_SOURCES (dashboard) but tradingagents was never registered
    # here in SYSTEM_SOURCES (resolver).  Without this entry, the resolver
    # never tracks TP/SL/TIME_EXIT outcomes for tradingagents picks —
    # they would stay permanently OPEN.
    ("tradingagents",                "alpha_engine/data/tradingagents_picks.json"),
    # ── STOCKSUNIFY2 equity picks (top-7 swarm #1 2026-05-08) ──
    # Registered in dashboard_generator.py JSON_PICK_SOURCES since 2026-05-08
    # but was MISSING from SYSTEM_SOURCES — picks never got TP/SL/TIME_EXIT
    # resolution.  Fix: phase 1, 2026-05-09.
    ("stocksunify2",                   "audit_dashboard/data/stocksunify2_active_picks.json"),
    # ── Additional systems registered in JSON_PICK_SOURCES but missing here ──
    ("skyrocket_detector",             "data/skyrocket_active.json"),
    ("ueps",                            "audit_dashboard/data/ueps_picks.json"),
    ("penny_screener",                  "data/penny_screener_active.json"),
    ("cot_positioning",                 "data/cot_positioning_active.json"),
    # ── FOREX/FUTURES orphan-source retrofit (Tier-4 #10, 2026-05-19) ──
    # alpha_engine/outcome_resolver.py writes audit_dashboard/data/forex_futures_picks.json
    # on every resolver run, and dashboard_generator.py JSON_PICK_SOURCES reads it
    # (tagged orphan_emitter_forex_futures via ORPHAN_EMITTER_SOURCES) — but it was
    # MISSING from SYSTEM_SOURCES here, so the universal resolver never time-exited
    # its stale FUTURES picks (DB_PICK_TRACEBACK_2026-05-18.md §5: ~86% of FUTURES
    # rows from this file's emitter sat OPEN 17-37 days, far past the 96h FUTURES
    # max-hold). outcome_resolver resolves the TP/SL path; this entry adds the
    # universal resolver's no-live-price TIME_EXIT fallback as a backstop so the
    # past-max-hold OPEN backlog closes out. Mirrors the tradingagents/stocksunify2
    # retrofit pattern above.
    ("forex_futures_orphan",            "audit_dashboard/data/forex_futures_picks.json"),
    # ── ML Strategy Reviver inverse sleeve (2026-06-06) ──
    # Registered in JSON_PICK_SOURCES but was missing here — inverse_ml picks
    # never got TP/SL/TIME_EXIT resolution on the standalone reviver file.
    ("ml_strategy_reviver_inverse",     "alpha_engine/data/ml_reviver_picks.json"),
]


def _float(v):
    try:
        return float(v) if v else 0.0
    except (ValueError, TypeError):
        return 0.0


def _compute_pnl(entry: float, exit_price: float, direction: str) -> float:
    """Compute PnL % with zero-safeguard fallback.

    If the rounded PnL computes to exactly 0.0 for a resolved pick,
    fallback to the unrounded formula so that WON/LOST picks do not
    end up with zero PnL in at_pick_outcomes.
    """
    if not entry or entry <= 0:
        return 0.0
    mult = 1.0 if direction == "LONG" else -1.0
    pnl = round(((exit_price - entry) / entry) * 100 * mult, 2)
    if pnl == 0.0:
        fallback = ((exit_price - entry) / entry) * 100 * mult
        if fallback != 0.0:
            log.warning(
                "[ZERO-PNL-SAFEGUARD] PnL computed as 0.0 for %s pick "
                "(entry=%s exit=%s). Fallback recompute: %.4f%%",
                direction, entry, exit_price, fallback,
            )
            return fallback
    return pnl


_PREDICTION_MARKET_SYSTEMS = {
    "polymarket_signals",
    "pm_momentum_signals",
    "pm_whale_signals",
    "pm_kalshi_signals",
}


# CoinGecko symbol mapping (for failover when Binance is geo-blocked)
_CG_MAP = {
    "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
    "BNBUSDT": "binancecoin", "XRPUSDT": "ripple", "DOGEUSDT": "dogecoin",
    "ADAUSDT": "cardano", "AVAXUSDT": "avalanche-2", "DOTUSDT": "polkadot",
    "LINKUSDT": "chainlink", "MATICUSDT": "matic-network", "LTCUSDT": "litecoin",
    "NEARUSDT": "near", "ATOMUSDT": "cosmos", "APTUSDT": "aptos",
    "ARBUSDT": "arbitrum", "OPUSDT": "optimism", "SUIUSDT": "sui",
    "TRXUSDT": "tron", "SHIBUSDT": "shiba-inu", "PEPEUSDT": "pepe",
    "RENDERUSDT": "render-token", "FETUSDT": "fetch-ai", "INJUSDT": "injective-protocol",
    "FILUSDT": "filecoin", "GALAUSDT": "gala", "WLDUSDT": "worldcoin-wld",
    "HBARUSDT": "hedera-hashgraph", "SEIUSDT": "sei-network", "KASUSDT": "kaspa",
    "WIFUSDT": "dogwifcoin", "BONKUSDT": "bonk", "FLOKIUSDT": "floki",
    "UNIUSDT": "uniswap", "AAVEUSDT": "aave",
}


def _fetch_prices_failover():
    """Fetch prices with multi-API failover chain.
    Order: Binance → Binance.us → data-api → Bybit, then backfill gaps with
    CoinGecko and CryptoCompare for symbols missing from the primary source.
    Returns {SYMBOL: price} dict."""
    prices = {}
    primary_source = None

    # 1. Binance (multiple hosts for region failover)
    for host in ("api.binance.com", "api1.binance.com", "api2.binance.com",
                 "api.binance.us", "data-api.binance.vision"):
        try:
            req = urllib.request.Request(
                f"https://{host}/api/v3/ticker/price",
                headers={"User-Agent": "UniversalResolver/1.0"}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read())
            prices = {t["symbol"]: float(t["price"]) for t in data if "symbol" in t and "price" in t}
            if prices:
                primary_source = host
                break
        except Exception as e:
            log.warning("Binance %s failed: %s", host, e)

    # 2. Bybit (no geo-block issues)
    if not prices:
        try:
            req = urllib.request.Request(
                "https://api.bybit.com/v5/market/tickers?category=spot",
                headers={"User-Agent": "UniversalResolver/1.0"}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read())
            for t in data.get("result", {}).get("list", []):
                sym = t.get("symbol", "")
                lp = t.get("lastPrice")
                if sym and lp:
                    prices[sym] = float(lp)
            if prices:
                primary_source = "Bybit"
        except Exception as e:
            log.warning("Bybit failed: %s", e)

    if primary_source:
        log.info("Primary prices from %s: %d tickers", primary_source, len(prices))

    # 3. CoinGecko backfill for symbols missing from the primary source.
    try:
        ids_str = ",".join(set(_CG_MAP.values()))
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd"
        req = urllib.request.Request(url, headers={"User-Agent": "UniversalResolver/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        id_to_sym = {v: k for k, v in _CG_MAP.items()}
        cg_filled = 0
        for cg_id, price_data in data.items():
            sym = id_to_sym.get(cg_id)
            if sym and sym not in prices and "usd" in price_data:
                prices[sym] = float(price_data["usd"])
                cg_filled += 1
        if cg_filled:
            log.info("CoinGecko backfilled %d missing symbols", cg_filled)
        elif not primary_source and prices:
            log.info("Prices from CoinGecko: %d tickers", len(prices))
    except Exception as e:
        log.warning("CoinGecko failed: %s", e)

    # 4. CryptoCompare final backfill for any still-missing mapped symbols.
    try:
        bases = list({sym.replace("USDT", "") for sym in _CG_MAP.keys()})
        url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={','.join(bases[:30])}&tsyms=USD"
        req = urllib.request.Request(url, headers={"User-Agent": "UniversalResolver/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        cc_filled = 0
        for base, obj in data.items():
            if isinstance(obj, dict) and "USD" in obj:
                sym = base + "USDT"
                if sym not in prices:
                    prices[sym] = float(obj["USD"])
                    cc_filled += 1
        if cc_filled:
            log.info("CryptoCompare backfilled %d missing symbols", cc_filled)
        elif not primary_source and prices:
            log.info("Prices from CryptoCompare: %d tickers", len(prices))
    except Exception as e:
        log.warning("CryptoCompare failed: %s", e)

    if prices:
        return prices

    log.error("ALL price APIs failed — no live prices available")
    return prices


# Non-crypto symbols that need yfinance for price resolution
# (futures =F, forex =X, equities, ETFs)
_YFINANCE_SUFFIXES = {"=F", "=X"}
_EQUITY_ETF_TICKERS = {
    "SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META",
    "TSLA", "JPM", "V", "JNJ", "WMT", "PG", "XOM", "UNH", "HD", "KO", "PEP",
    "CVX", "MRK", "ABBV", "SOFI", "NIO", "PLTR", "MARA", "RIOT", "IONQ",
    "LCID", "RIVN", "HOOD", "OPEN", "CLOV", "BB", "NOK", "SNDL", "AMC",
    "XLK", "XLF", "XLE", "XLV", "XLP", "XLY", "XLI", "XLB", "XLC", "XLRE",
    "XLU", "GLD", "SLV", "TLT", "HYG", "DBC", "SOXX", "ARKK",
    "COIN", "MSTR", "BA", "GS", "MA", "AMD", "NFLX", "DIS",
}


def _is_non_crypto_symbol(sym: str) -> bool:
    """Check if a symbol needs yfinance (not available on Binance/Bybit)."""
    if not sym:
        return False
    if any(sym.endswith(s) for s in _YFINANCE_SUFFIXES):
        return True
    base = sym.replace("=F", "").replace("=X", "")
    return base in _EQUITY_ETF_TICKERS


def _fetch_yfinance_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch prices for non-crypto symbols via yfinance (batch).

    Returns {symbol: price} dict for successfully fetched symbols.
    """
    if not symbols:
        return {}
    try:
        import yfinance as yf
    except ImportError:
        log.debug("yfinance not available for non-crypto price resolution")
        return {}

    prices = {}
    try:
        # Batch download for efficiency
        data = yf.download(symbols, period="1d", interval="1d",
                           progress=False, threads=True)
        if data is not None and not data.empty:
            if len(symbols) == 1:
                # Single symbol: data is flat
                if "Close" in data.columns and len(data) > 0:
                    prices[symbols[0]] = float(data["Close"].iloc[-1])
            else:
                # Multi symbol: data is multi-indexed
                for sym in symbols:
                    try:
                        close = data[sym]["Close"] if sym in data.columns.get_level_values(0) else None
                        if close is not None and len(close.dropna()) > 0:
                            prices[sym] = float(close.dropna().iloc[-1])
                    except Exception:
                        pass
        if prices:
            log.info("yfinance fetched %d non-crypto prices (%s...)",
                     len(prices), list(prices.keys())[:3])
    except Exception as e:
        log.warning("yfinance batch fetch failed: %s", e)

    # Fallback: individual fetches for missing symbols
    missing = [s for s in symbols if s not in prices]
    for sym in missing[:10]:  # Cap at 10 individual fetches
        try:
            import yfinance as yf
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="1d")
            if hist is not None and not hist.empty:
                prices[sym] = float(hist["Close"].iloc[-1])
        except Exception:
            pass

    return prices


def _fetch_yfinance_ohlcv(symbol: str, period: str = "5d", interval: str = "1h") -> list[dict]:
    """Fetch intrabar OHLCV for a non-crypto symbol via yfinance.

    Returns list of {open, high, low, close, volume} dicts sorted by time.
    Used for intrabar TP/SL checking (not just daily close).
    """
    try:
        import yfinance as yf
    except ImportError:
        return []

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval, progress=False)
        if hist is None or hist.empty:
            return []

        bars = []
        for _, row in hist.iterrows():
            bars.append({
                "open": float(row.get("Open", 0)),
                "high": float(row.get("High", 0)),
                "low": float(row.get("Low", 0)),
                "close": float(row.get("Close", 0)),
                "volume": float(row.get("Volume", 0)),
            })
        if bars:
            log.debug("  yfinance intrabar: %s -> %d bars (%s)", symbol, len(bars), interval)
        return bars
    except Exception as e:
        log.debug("  yfinance intrabar failed for %s: %s", symbol, e)
        return []


def _fetch_binance_klines_ohlcv(symbol: str, interval: str = "1h", limit: int = 48) -> list[dict]:
    """Fetch intrabar OHLCV for crypto symbols via Binance klines.

    Returns list of {open, high, low, close, volume} dicts sorted by time.
    Uses 4-mirror failover. Used for intrabar TP/SL checking on crypto picks.
    """
    hosts = (
        "api.binance.com", "api1.binance.com",
        "api2.binance.com", "api3.binance.com",
    )
    for host in hosts:
        try:
            url = f"https://{host}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "UniversalResolver/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            if not data or not isinstance(data, list):
                continue
            bars = []
            for k in data:
                # Binance kline format: [open_time, open, high, low, close, volume, ...]
                if len(k) < 5:
                    continue
                bars.append({
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]) if len(k) > 5 else 0,
                })
            if bars:
                log.debug("  binance intrabar: %s -> %d bars (%s)", symbol, len(bars), interval)
                return bars
        except Exception as e:
            log.debug("  binance intrabar failed for %s on %s: %s", symbol, host, e)
            continue
    return []


def _check_tp_sl_intrabar(pick: dict, ohlcv_bars: list[dict]):
    """Check TP/SL against intrabar OHLC data (not just close price).

    For each bar, check if high/low crossed TP or SL levels.
    Returns (reason, exit_price, pnl_pct) or None.
    This is more accurate than close-only checking — catches wicks that hit TP/SL.
    """
    direction = pick["direction"]
    entry = pick["entry_price"]
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)

    if not entry or (not tp and not sl):
        return None

    for bar in ohlcv_bars:
        high = bar.get("high", 0)
        low = bar.get("low", 0)
        if not high or not low:
            continue

        # SL-first conservative ordering (mirrors tournament's _scan_bars_for_touch).
        if direction == "LONG":
            if sl and low <= sl:
                pnl = _compute_pnl(entry, sl, direction)
                return ("SL_HIT", sl, pnl)
            if tp and high >= tp:
                pnl = _compute_pnl(entry, tp, direction)
                return ("TP_HIT", tp, pnl)
        else:  # SHORT
            if sl and high >= sl:
                pnl = _compute_pnl(entry, sl, direction)
                return ("SL_HIT", sl, pnl)
            if tp and low <= tp:
                pnl = _compute_pnl(entry, tp, direction)
                return ("TP_HIT", tp, pnl)

    return None


def _normalize_symbol(sym):
    """Normalize symbol for price lookup (BTC-USD -> BTCUSDT)."""
    if not sym:
        return sym
    s = sym.strip().upper().replace("-", "").replace("_", "").replace("/", "")
    # 2026-05-19: yfinance-suffixed symbols already correct.
    if s.endswith("=X") or s.endswith("=F"):
        return s
    # FOREX guard: 6-char symbol with both halves fiat = forex pair (EURUSD),
    # NOT crypto (BTCUSD). Appending T mangled it -> EURUSDT -> yfinance no_price.
    _FIAT = {"USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"}
    if len(s) == 6 and s.isalpha() and s[:3] in _FIAT and s[3:] in _FIAT:
        return s + "=X"
    if s.endswith("USD") and not s.endswith("USDT") and not s.endswith("BUSD"):
        s += "T"
    return s


def _parse_timestamp(ts_str):
    """Parse various timestamp formats."""
    if not ts_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(str(ts_str)[:26].rstrip('Z'), fmt.rstrip('Z').replace('%z', ''))
            return dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


# Scoring/quality fields to preserve when resolving picks
# These are CRITICAL for quality analysis and must NOT be lost
_SCORING_FIELDS = [
    "elite_score", "method_a_score", "ml_composite_score", "antigravity_score",
    "elite_grade", "method_a_grade", "ml_composite_grade", "ag_grade",
    "elite_breakdown", "method_a_breakdown", "ml_composite_breakdown",
    "trust_score", "trust_tier", "Trust Tier", "Trust Score",
    "consensus_pct", "consensus_votes", "high_conviction",
    "forward_wr", "forward_trades", "forward_status",
    "confidence", "signal_probability", "tp_probability",
    "risk_reward", "risk_reward_ratio", "atrValue",
    "rsi_at_entry", "volume_ratio", "regime", "market_regime",
    "enrichment", "ml_features", "signal_sources", "source_count",
    "grade", "Score", "quality_score", "conviction_tier",
    # Copy trader specific
    "whale_score", "institutional_score", "hf_conviction_tier",
    # Prediction market specific
    "pm_consensus", "pm_confidence", "prediction_market_sources",
    # C5 (crypto_edge_artifact_audit_2026_05_17.md §C5): preserve original
    # signal timestamps so analytics can distinguish signal_time from the
    # run-time stamp written into pick["timestamp"] by _extract_pick_fields.
    # Without these, age_hours / staleness metrics read run-time as entry age.
    "signal_time", "entry_time", "closed_at", "opened_at", "resolved_at",
]


def _extract_pick_fields(raw, system_name):
    """Extract normalized pick fields from any source format.
    
    PRESERVES CRITICAL SCORING METADATA - this is essential for quality analysis.
    Without scoring fields, resolved picks have no quality metrics and appear
    to perform poorly when filtered by score/grade.
    """
    symbol = raw.get("symbol", raw.get("pair", raw.get("ticker", "")))

    direction = str(raw.get("direction", raw.get("signal_type",
                    raw.get("signal", raw.get("action", ""))))).upper()
    if "BUY" in direction or "LONG" in direction:
        direction = "LONG"
    elif "SELL" in direction or "SHORT" in direction:
        direction = "SHORT"
    else:
        direction = "LONG"  # default

    entry = _float(raw.get("entry_price", raw.get("entryPrice",
                    raw.get("entry", raw.get("price", 0)))))
    tp = _float(raw.get("take_profit", raw.get("targetPrice",
                 raw.get("tp", raw.get("tp_price", raw.get("tp1_price",
                 raw.get("tp_price_1_5", 0)))))))
    sl = _float(raw.get("stop_loss", raw.get("stopPrice",
                 raw.get("sl", raw.get("sl_price", 0)))))

    # Timestamp
    ts = ""
    for k in ("timestamp", "entry_date", "created_at", "generated_at",
              "signal_time", "opened_at", "scan_time", "entry_time",
              "scraped_at", "entryDate", "resolution_date", "resolved_at"):
        if raw.get(k):
            ts = str(raw[k])
            break

    strategy = raw.get("strategy", raw.get("strategy_name",
                raw.get("algorithm", raw.get("predictor_id",
                raw.get("analyst_category", raw.get("platform", "unknown"))))))

    # Build base pick with required fields
    pick = {
        "id": raw.get("id", raw.get("pick_id", raw.get("signal_id", raw.get("prediction_id", "")))) or "",
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry,
        "take_profit": tp,
        "stop_loss": sl,
        "timestamp": ts,
        "strategy": strategy,
        "source_system": system_name,
    }
    # Populate asset_class so consumers reading universal_resolved_picks.json
    # directly (not via dashboard_generator._normalize_pick) see a labeled class.
    pick["asset_class"] = normalize_asset_class({**raw, **pick})
    
    # ── PRESERVE ALL SCORING METADATA ──
    # This is the critical fix - without this, quality metrics are lost on resolution
    for field in _SCORING_FIELDS:
        if field in raw and raw[field] is not None:
            pick[field] = raw[field]
    
    # Also preserve any enrichment data (nested dict with market context)
    if raw.get("enrichment"):
        pick["enrichment"] = raw["enrichment"]
    
    # Preserve original source_system if different from current system_name
    if raw.get("source_system") and raw["source_system"] != system_name:
        pick["original_source_system"] = raw["source_system"]
    
    return pick


def _is_prediction_market_pick(system_name: str, pick: dict) -> bool:
    source_hint = " ".join(
        [
            str(system_name or ""),
            str(pick.get("source_system", "") or ""),
            str(pick.get("strategy", "") or ""),
        ]
    ).lower()
    return (
        system_name in _PREDICTION_MARKET_SYSTEMS
        or "polymarket" in source_hint
        or "kalshi" in source_hint
        or "pm_" in source_hint
    )


def _snapshot_prediction_market_entry(pick: dict, current_price: float) -> bool:
    if pick.get("entry_price") or current_price <= 0:
        return False

    entry = round(float(current_price), 8)
    pick["entry_price"] = entry
    if not pick.get("take_profit") and not pick.get("stop_loss"):
        if pick.get("direction") == "SHORT":
            pick["take_profit"] = round(entry * 0.975, 8)
            pick["stop_loss"] = round(entry * 1.015, 8)
        else:
            pick["take_profit"] = round(entry * 1.025, 8)
            pick["stop_loss"] = round(entry * 0.985, 8)
    return True


def check_tp_sl(pick, current_price):
    """Check if a pick has hit TP or SL. Returns (reason, exit_price, pnl_pct) or None."""
    direction = pick["direction"]
    entry = pick["entry_price"]
    tp = pick["take_profit"]
    sl = pick["stop_loss"]

    if not entry or (not tp and not sl):
        return None

    if direction == "LONG":
        if tp and current_price >= tp:
            pnl = _compute_pnl(entry, tp, direction)
            return ("TP_HIT", tp, pnl)
        if sl and current_price <= sl:
            pnl = _compute_pnl(entry, sl, direction)
            return ("SL_HIT", sl, pnl)
    else:  # SHORT
        if tp and current_price <= tp:
            pnl = _compute_pnl(entry, tp, direction)
            return ("TP_HIT", tp, pnl)
        if sl and current_price >= sl:
            pnl = _compute_pnl(entry, sl, direction)
            return ("SL_HIT", sl, pnl)
    return None


def _load_json_source(path, rel_path):
    """Load a pick-source JSON file; skip HTML error pages (404/Apache bodies)."""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace").lstrip()
    head = text[:256].upper()
    if text.startswith("<") or "<!DOCTYPE" in head or "<HTML" in head:
        log.warning("Skipping non-JSON (HTML) source: %s", rel_path)
        return None
    try:
        return json.loads(text)
    except Exception as e:
        log.warning("Failed to load %s: %s", rel_path, e)
        return None


def load_existing_resolved():
    """Load previously resolved picks to avoid duplicates."""
    if RESOLVED_FILE.exists():
        try:
            data = json.loads(RESOLVED_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else data.get("resolved", [])
        except Exception:
            return []
    return []


def make_pick_id(pick):
    """Create a unique ID for a pick to detect duplicates.
    Prefer a stable raw id when available; otherwise fall back to a richer signature."""
    raw_id = pick.get("id", "")
    if raw_id not in (None, ""):
        return f"id::{pick.get('source_system', '')}::{raw_id}"
    sym = _normalize_symbol(pick.get('symbol', ''))
    entry = round(_float(pick.get("entry_price", 0) or 0), 8)
    ts = str(pick.get("timestamp", "") or "").strip()[:19]
    return (
        f"fallback::{pick.get('source_system', '')}::{sym}::{pick.get('direction', '')}"
        f"::{pick.get('strategy', '')}::{entry}::{ts}"
    )


def _is_closed_like_raw_pick(raw: dict) -> bool:
    """Skip rows that are already resolved inside mixed active ledgers."""
    status = str(raw.get("status", "") or raw.get("outcome", raw.get("exit_reason", ""))).upper().strip()
    if status in CLOSED_STATUSES:
        return True
    if raw.get("resolved_at") or raw.get("closed_at") or raw.get("exit_time") or raw.get("close_time"):
        return True
    exit_price = _float(raw.get("exit_price", raw.get("close_price", raw.get("current_price", raw.get("currentPrice", 0)))))
    if exit_price > 0:
        return True
    pnl_raw = raw.get("pnl_pct", raw.get("actual_pnl_pct", raw.get("outcome_pnl_pct", raw.get("pnlPct", None))))
    try:
        if pnl_raw not in (None, "") and abs(float(pnl_raw)) > 0.01:
            return True
    except (TypeError, ValueError):
        pass
    return False


def _write_outcomes_to_mysql(resolved_picks: list) -> int:
    """Upsert resolved pick outcomes into ejaguiar1_stocks.at_pick_outcomes.

    Gated by PICK_OUTCOMES_MYSQL_ENABLED env var (truthy = on; DEFAULT NOW "1" per 2026-05-20 bug fix that revealed 99.91% MySQL outcomes write was dead via wrong default).
    Returns number of picks written / updated.
    """
    if not os.environ.get("PICK_OUTCOMES_MYSQL_ENABLED", "1").lower() in ("1", "true", "yes", "on"):
        logging.info("[mysql] PICK_OUTCOMES_MYSQL_ENABLED not set — skipping outcomes write")
        return 0

    try:
        import pymysql
    except ImportError:
        logging.warning("[mysql] pymysql not installed — skipping outcomes write")
        return 0

    host = os.environ.get("DB_STOCKS_HOST", os.environ.get("DB_HOST", "mysql.50webs.com"))
    port = int(os.environ.get("DB_STOCKS_PORT", os.environ.get("DB_PORT", "3306")))
    user = os.environ.get("DB_STOCKS_USER", os.environ.get("AUDIT_DB_USER", "ejaguiar1_stocks"))
    password = os.environ.get("DB_PASS_STOCKS", os.environ.get("DB_STOCKS_PASSWORD", os.environ.get("AUDIT_DB_PASS", "")))
    database = os.environ.get("DB_STOCKS_NAME", os.environ.get("DB_NAME_STOCKS", "ejaguiar1_stocks"))

    UPSERT_SQL = """
        INSERT INTO at_pick_outcomes
            (pick_id, symbol, strategy, asset_class,
             status, resolution_method, pnl_pct, resolved_at, resolver_version)
        VALUES
            (%(pick_id)s, %(symbol)s, %(strategy)s, %(asset_class)s,
             %(status)s, %(resolution_method)s, %(pnl_pct)s, %(resolved_at)s, %(resolver_version)s)
        ON DUPLICATE KEY UPDATE
            status            = VALUES(status),
            resolution_method = VALUES(resolution_method),
            pnl_pct           = VALUES(pnl_pct),
            resolved_at       = VALUES(resolved_at)
    """

    written = 0
    try:
        conn = pymysql.connect(
            host=host, port=port, user=user,
            password=password, database=database,
            charset="utf8mb4", autocommit=True,
        )
        with conn.cursor() as cur:
            for pick in resolved_picks:
                try:
                    symbol = str(pick.get("symbol", pick.get("ticker", "")))[:50]
                    if not symbol:
                        continue
                    strategy = str(pick.get("strategy", pick.get("algorithm_name", "")))[:100]
                    asset_class = str(pick.get("asset_class", "CRYPTO"))[:20]

                    # Map exit_reason to at_pick_outcomes status/resolution_method enums
                    exit_reason = str(pick.get("exit_reason", pick.get("status", ""))).upper()
                    if exit_reason in ("TP_HIT", "TAKE_PROFIT", "WON", "WIN", "TP"):
                        status = "WON"
                        resolution_method = "TP_HIT"
                    elif exit_reason in ("SL_HIT", "STOP_LOSS", "LOST", "LOSS", "SL"):
                        status = "LOST"
                        resolution_method = "SL_HIT"
                    elif exit_reason in ("TIME_EXIT", "EXPIRED", "TIME", "TIMEOUT", "MAX_HOLD"):
                        status = "EXPIRED"
                        resolution_method = "TIME_EXPIRED"
                    elif exit_reason in ("FLAT", "FORCE_CLOSED", "CLOSED", "RESOLVED"):
                        status = "FLAT"
                        resolution_method = "MANUAL"
                    elif exit_reason in ("OPEN", "ACTIVE"):
                        status = "OPEN"
                        resolution_method = None
                    else:
                        status = "EXPIRED"
                        resolution_method = "TIME_EXPIRED"

                    pnl_raw = float(pick.get("pnl_pct", pick.get("pnl", 0)) or 0)
                    pnl_pct = round(max(-100.0, min(100.0, pnl_raw)), 4)

                    resolved_at = None
                    for ts_key in ("resolved_at", "closed_at", "exit_date", "timestamp"):
                        ts_val = pick.get(ts_key)
                        if ts_val:
                            try:
                                resolved_at = str(ts_val).replace("T", " ").replace("Z", "")[:19]
                            except Exception:
                                pass
                            break

                    params = {
                        "symbol": symbol,
                        "strategy": strategy,
                        "asset_class": asset_class,
                        "status": status,
                        "resolution_method": resolution_method,
                        "pnl_pct": pnl_pct,
                        "resolved_at": resolved_at,
                        "resolver_version": "universal_v2",
                    }
                    # P0 §15 dedup harmonization (TON-validated 2026-06-01): use canonical helper
                    from alpha_engine.dedup import build_canonical_outcomes_pick_id
                    params["pick_id"] = build_canonical_outcomes_pick_id(pick)
                    cur.execute(UPSERT_SQL, params)
                    written += 1
                except Exception as e:
                    logging.warning(f"[mysql] failed to write pick {symbol}: {e}")

        logging.info(f"[mysql] wrote/updated {written} outcomes to at_pick_outcomes")
    except Exception as e:
        logging.warning(f"[mysql] connection/upsert error: {e}")

    return written


def main():
    now = datetime.now(timezone.utc)
    log.info("=== Universal Pick Resolver starting ===")

    # Load live prices (multi-API failover)
    prices = _fetch_prices_failover()

    # Scan all pick sources for non-crypto symbols (=F, =X, equities)
    # and fetch their prices via yfinance
    non_crypto_syms = set()
    for _, rel_path in SYSTEM_SOURCES:
        fpath = ROOT / rel_path
        if not fpath.exists():
            continue
        raw_data = _load_json_source(fpath, rel_path)
        if raw_data is None:
            continue
        try:
            if isinstance(raw_data, list):
                pl = raw_data
            elif isinstance(raw_data, dict):
                pl = (raw_data.get("active_picks") or raw_data.get("picks") or
                      raw_data.get("signals") or raw_data.get("open_picks") or
                      raw_data.get("activePicks") or [])
                if not isinstance(pl, list):
                    pl = []
            else:
                continue
            for rp in pl:
                if isinstance(rp, dict):
                    sym = rp.get("symbol", rp.get("pair", rp.get("ticker", "")))
                    if sym and _is_non_crypto_symbol(sym) and sym not in prices:
                        non_crypto_syms.add(sym)
        except Exception:
            pass

    if non_crypto_syms:
        log.info("Found %d non-crypto symbols needing yfinance: %s",
                 len(non_crypto_syms), list(non_crypto_syms)[:10])
        yf_prices = _fetch_yfinance_prices(list(non_crypto_syms))
        prices.update(yf_prices)

    # Pre-fetch intrabar OHLC for ALL symbols (unified cache).
    ohlc_bars_cache: dict[str, list[dict]] = {}
    all_syms_ohlc: set[tuple[str, bool]] = set()
    for _, rel_path in SYSTEM_SOURCES:
        fpath = ROOT / rel_path
        if not fpath.exists():
            continue
        raw_data = _load_json_source(fpath, rel_path)
        if raw_data is None:
            continue
        try:
            if isinstance(raw_data, list):
                pl = raw_data
            elif isinstance(raw_data, dict):
                pl = (raw_data.get("active_picks") or raw_data.get("picks") or
                      raw_data.get("signals") or raw_data.get("open_picks") or
                      raw_data.get("activePicks") or [])
                if not isinstance(pl, list):
                    pl = []
            else:
                continue
            for rp in pl:
                if not isinstance(rp, dict):
                    continue
                sym = rp.get("symbol", rp.get("pair", rp.get("ticker", "")))
                if not sym:
                    continue
                norm = _normalize_symbol(sym)
                is_nc = _is_non_crypto_symbol(norm)
                all_syms_ohlc.add((norm, is_nc))
        except Exception:
            pass
    if all_syms_ohlc:
        nc_count = sum(1 for _, is_nc in all_syms_ohlc if is_nc)
        c_count = len(all_syms_ohlc) - nc_count
        log.info("Pre-fetching intrabar OHLC: %d non-crypto + %d crypto symbols", nc_count, c_count)
        for norm_sym, is_nc in sorted(all_syms_ohlc, key=lambda x: x[0]):
            try:
                if is_nc:
                    bars = _fetch_yfinance_ohlcv(norm_sym, period="5d", interval="1h")
                else:
                    bars = _fetch_binance_klines_ohlcv(norm_sym, interval="1h", limit=48)
                if bars:
                    ohlc_bars_cache[norm_sym] = bars
            except Exception as e:
                log.debug("OHLC pre-fetch failed for %s: %s", norm_sym, e)
            time.sleep(0.1)
        n_cached = sum(1 for v in ohlc_bars_cache.values() if v)
        log.info("Intrabar OHLC cached for %d/%d symbols", n_cached, len(all_syms_ohlc))

    if not prices:
        log.error("No prices available from any API — aborting")
        return

    # Load existing resolved picks
    existing_resolved = load_existing_resolved()
    resolved_ids = {make_pick_id(r) for r in existing_resolved if isinstance(r, dict)}

    newly_resolved = []
    stats = defaultdict(lambda: {"checked": 0, "tp_hit": 0, "sl_hit": 0, "expired": 0, "no_price": 0, "no_entry": 0})

    for system_name, rel_path in SYSTEM_SOURCES:
        path = ROOT / rel_path
        if not path.exists():
            continue

        data = _load_json_source(path, rel_path)
        if data is None:
            continue

        # Extract picks list from various formats
        if isinstance(data, list):
            picks_list = data
        elif isinstance(data, dict):
            picks_list = (data.get("active_picks") or data.get("picks") or
                         data.get("signals") or data.get("open_picks") or
                         data.get("activePicks") or [])
            if not isinstance(picks_list, list):
                picks_list = []
        else:
            continue

        if not picks_list:
            continue

        for raw in picks_list:
            if not isinstance(raw, dict):
                continue
            if _is_closed_like_raw_pick(raw):
                continue

            pick = _extract_pick_fields(raw, system_name)
            
            # Enrich with RSI/volume if missing (for better dashboard display)
            try:
                from audit_trail.feature_enricher import enrich_pick_with_features
                pick = enrich_pick_with_features(pick)
            except Exception as e:
                log.debug("Feature enrichment failed for %s: %s", pick.get("symbol", "?"), e)
            
            pick_id = make_pick_id(pick)

            # Skip if already resolved
            if pick_id in resolved_ids:
                continue

            stats[system_name]["checked"] += 1

            # Normalize symbol for price lookup
            orig_sym = pick["symbol"]
            norm_sym = _normalize_symbol(orig_sym)
            current_price = prices.get(norm_sym) or prices.get(orig_sym)

            if current_price is None:
                stats[system_name]["no_price"] += 1
                # ── TIME_EXIT fallback for picks without live prices ──
                # loop2 fix #9 2026-05-08: Non-crypto picks (FOREX like EURUSD,
                # penny stocks, etc.) that can't get live prices from Binance/
                # Bybit/yfinance would skip BOTH TP/SL and TIME_EXIT checks,
                # accumulating forever in active ledgers. The dashboard stale-
                # filter eventually catches them as auto-expired (phantom
                # EXPIRED, 15,744 rows). Now they resolve as TIME_EXIT after
                # their per-asset-class hold window.
                pick_dt = _parse_timestamp(pick["timestamp"])
                _max_hold = _max_hold_hours_for(pick)
                if pick_dt and pick.get("entry_price") and (now - pick_dt).total_seconds() > _max_hold * 3600:
                    entry = pick["entry_price"]
                    hold_hours = round((now - pick_dt).total_seconds() / 3600, 1)
                    resolved = {
                        **pick,
                        "exit_price": entry,
                        "pnl_pct": 0.0,
                        "exit_reason": "TIME_EXIT",
                        "status": "CLOSED",
                        "resolved_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "hold_hours": hold_hours,
                        "_note": "no-live-price",
                        "_resolver_version": RESOLVER_VERSION,
                        "_resolver_source": RESOLVER_SOURCE_ID,
                    }
                    apply_pnl_clamp_to_pick(resolved)
                    newly_resolved.append(resolved)
                    resolved_ids.add(pick_id)
                    stats[system_name]["expired"] += 1
                    log.info(
                        "  TIME_EXIT (no-live-price) %s %s %s pnl=0.0%% (held %.0fh)",
                        system_name, pick["symbol"], pick["direction"], hold_hours,
                    )
                continue

            if (not pick["entry_price"] or pick["entry_price"] == 0) and _is_prediction_market_pick(system_name, pick):
                _snapshot_prediction_market_entry(pick, current_price)

            if not pick["entry_price"] or pick["entry_price"] == 0:
                stats[system_name]["no_entry"] += 1
                continue

            # ── Reverse-split entry-price adjustment ─────────────────
            # When a stock has undergone a reverse split (e.g. LODE 1-for-10),
            # picks submitted with pre-split prices must be scaled up to match
            # post-split yfinance OHLC, otherwise TP/SL checks and PnL are
            # computed on incompatible scales.
            # Two adjustment paths:
            #   1. Date guard: pick submitted BEFORE split → always adjust
            #   2. Price heuristic: pick submitted AFTER split but entry_price * factor
            #      ≈ current_price → the model used stale pre-split data → adjust anyway
            _pick_ts = pick.get("timestamp", "")
            _should_adj, _factor = should_adjust_for_split(
                pick.get("symbol", ""), _pick_ts)
            # Price-range fallback: if date guard says don't adjust, check whether
            # entry_price * factor matches the current market price.
            # If so, the entry is pre-split despite the post-split submission date.
            if not _should_adj and _factor and pick["entry_price"] > 0 and current_price > 0:
                _adjusted_candidate = pick["entry_price"] * _factor
                _ratio = _adjusted_candidate / current_price if current_price else 999
                # Wide bounds (0.3–2.0) to catch PENNY stocks that appreciated post-split
                if 0.3 <= _ratio <= 2.0:
                    _should_adj = True
                    log.info("  reverse-split-HEURISTIC %s: entry $%s x%d=$%s ≈ price $%s -> adjusting",
                             pick["symbol"], pick["entry_price"], _factor,
                             _adjusted_candidate, current_price)
            if _should_adj and _factor and pick["entry_price"] > 0:
                _old_entry = pick["entry_price"]
                pick["entry_price"] = round(
                    _old_entry * _factor, 8)
                if pick.get("take_profit"):
                    pick["take_profit"] = round(
                        pick["take_profit"] * _factor, 8)
                if pick.get("stop_loss"):
                    pick["stop_loss"] = round(
                        pick["stop_loss"] * _factor, 8)
                pick["_reverse_split_adjusted"] = True
                pick["_split_factor"] = _factor
                log.info("  reverse-split %s: entry $%s -> $%s"
                         " (x%d, pre-split pick)",
                         pick["symbol"], _old_entry,
                         pick["entry_price"], _factor)

            # Auto-compute missing TP/SL with improved defaults (3% TP / 1.5% SL = 2:1 R:R)
            entry = pick["entry_price"]
            if not pick["take_profit"] and not pick["stop_loss"]:
                if pick["direction"] == "LONG":
                    pick["take_profit"] = round(entry * 1.03, 8)   # 3% TP
                    pick["stop_loss"] = round(entry * 0.985, 8)    # 1.5% SL
                else:
                    pick["take_profit"] = round(entry * 0.97, 8)
                    pick["stop_loss"] = round(entry * 1.015, 8)
            elif not pick["take_profit"] and pick["stop_loss"]:
                sl_dist = abs(entry - pick["stop_loss"])
                if pick["direction"] == "LONG":
                    pick["take_profit"] = round(entry + sl_dist * 2.0, 8)
                else:
                    pick["take_profit"] = round(entry - sl_dist * 2.0, 8)
            elif pick["take_profit"] and not pick["stop_loss"]:
                tp_dist = abs(pick["take_profit"] - entry)
                if pick["direction"] == "LONG":
                    pick["stop_loss"] = round(entry - tp_dist / 2.0, 8)
                else:
                    pick["stop_loss"] = round(entry + tp_dist / 2.0, 8)

            # ── TP/SL CLAMP ──
            # Data shows: TP 2-3% = 40% WR (sweet spot), TP 5%+ = 0% WR (never hits)
            # Enforce: min TP 2%, max TP 4%, min SL 1%, max SL 2.5%
            tp = pick["take_profit"]
            sl = pick["stop_loss"]
            if entry > 0 and tp and sl:
                tp_pct = abs(tp - entry) / entry * 100
                sl_pct = abs(sl - entry) / entry * 100

                # Clamp TP to 2-4% range
                if tp_pct < 2.0:
                    if pick["direction"] == "LONG":
                        pick["take_profit"] = round(entry * 1.025, 8)
                    else:
                        pick["take_profit"] = round(entry * 0.975, 8)
                elif tp_pct > 4.0:
                    if pick["direction"] == "LONG":
                        pick["take_profit"] = round(entry * 1.035, 8)
                    else:
                        pick["take_profit"] = round(entry * 0.965, 8)

                # Clamp SL to 1-2.5% range
                if sl_pct < 1.0:
                    if pick["direction"] == "LONG":
                        pick["stop_loss"] = round(entry * 0.99, 8)
                    else:
                        pick["stop_loss"] = round(entry * 1.01, 8)
                elif sl_pct > 2.5:
                    if pick["direction"] == "LONG":
                        pick["stop_loss"] = round(entry * 0.98, 8)
                    else:
                        pick["stop_loss"] = round(entry * 1.02, 8)

            # Check TP/SL — unified intrabar OHLC replay for ALL symbols
            result = None
            intrabar_bars = ohlc_bars_cache.get(norm_sym, [])
            if intrabar_bars:
                result = _check_tp_sl_intrabar(pick, intrabar_bars)
                if result:
                    log.debug("  intrabar hit for %s %s", norm_sym, pick["direction"])
            # Fallback to close-price check
            if result is None:
                result = check_tp_sl(pick, current_price)
            if result:
                reason, exit_price, pnl_pct = result
                # F-1 PnL outlier cap +/-100% applied to JSON-side resolution too
                pnl_pct_raw_json = pnl_pct
                pnl_pct = max(-100.0, min(100.0, float(pnl_pct)))
                if abs(pnl_pct_raw_json) > 100.0:
                    import logging as _log
                    _log.warning(f"[F-1] pnl_pct outlier capped: raw={pnl_pct_raw_json:.2f}% -> {pnl_pct:.2f}% (symbol={pick.get('symbol','?')} strategy={pick.get('strategy','?')})")
                resolved = {
                    **pick,
                    "exit_price": exit_price,
                    "pnl_pct": pnl_pct,
                    "exit_reason": reason,
                    "status": "CLOSED",
                    "resolved_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "current_price_at_resolve": current_price,
                    "_resolver_version": RESOLVER_VERSION,
                    "_resolver_source": RESOLVER_SOURCE_ID,
                }
                apply_pnl_clamp_to_pick(resolved)
                newly_resolved.append(resolved)
                resolved_ids.add(pick_id)

                if reason == "TP_HIT":
                    stats[system_name]["tp_hit"] += 1
                else:
                    stats[system_name]["sl_hit"] += 1

                log.info("  %s %s %s %s pnl=%+.2f%%", reason, system_name, pick["symbol"], pick["direction"], pnl_pct)
                continue

            # Check for time expiry (per-asset-class window — see MAX_HOLD_HOURS_BY_CLASS)
            pick_dt = _parse_timestamp(pick["timestamp"])
            _max_hold = _max_hold_hours_for(pick)
            if pick_dt and (now - pick_dt).total_seconds() > _max_hold * 3600:
                # Time exit — compute PnL at current price
                pnl = _compute_pnl(entry, current_price, pick["direction"])

                resolved = {
                    **pick,
                    "exit_price": current_price,
                    "pnl_pct": pnl,
                    "exit_reason": "TIME_EXIT",
                    "status": "CLOSED",
                    "resolved_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "_resolver_version": RESOLVER_VERSION,
                    "_resolver_source": RESOLVER_SOURCE_ID,
                    "hold_hours": round((now - pick_dt).total_seconds() / 3600, 1),
                }
                apply_pnl_clamp_to_pick(resolved)
                newly_resolved.append(resolved)
                resolved_ids.add(pick_id)
                stats[system_name]["expired"] += 1
                log.info(
                    "  TIME_EXIT %s %s %s pnl=%+.2f%% (held %.0fh)",
                    system_name,
                    pick["symbol"],
                    pick["direction"],
                    float(resolved.get("pnl_pct", 0) or 0),
                    (now - pick_dt).total_seconds() / 3600,
                )

    # Save resolved picks
    all_resolved = existing_resolved + newly_resolved

    # Cap resolved picks at 5000 (LRU)
    if len(all_resolved) > 5000:
        all_resolved = all_resolved[-5000:]

    # --- Sync resolved outcomes to MySQL (at_pick_outcomes) ---
    try:
        written = _write_outcomes_to_mysql(all_resolved)
        log.info(f"MySQL sync: %d outcomes written to at_pick_outcomes", written)
    except Exception as exc:
        log.warning(f"MySQL sync skipped (non-fatal): %s", exc)

    # Fix 2026-05-04: enrich all picks with asset_class if missing (92% were UNKNOWN)
    def enrich_pick_with_asset_class(pick):
        """Add asset_class to pick dict if missing."""
        if isinstance(pick, dict):
            if 'asset_class' not in pick or not pick.get('asset_class'):
                symbol = pick.get('symbol', '')
                try:
                    asset_class = classify_asset(symbol)
                    pick['asset_class'] = asset_class.value
                except Exception:
                    pick['asset_class'] = 'UNKNOWN'
        return pick

    all_resolved = [enrich_pick_with_asset_class(p) for p in all_resolved]

    RESOLVED_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESOLVED_FILE.write_text(
        json.dumps(all_resolved, indent=2, default=str),
        encoding="utf-8"
    )

    # Print summary
    log.info("")
    log.info("=" * 70)
    log.info("UNIVERSAL PICK RESOLVER — Summary")
    log.info("=" * 70)

    total_checked = sum(s["checked"] for s in stats.values())
    total_tp = sum(s["tp_hit"] for s in stats.values())
    total_sl = sum(s["sl_hit"] for s in stats.values())
    total_expired = sum(s["expired"] for s in stats.values())
    total_resolved = total_tp + total_sl + total_expired

    log.info("Systems scanned: %d", len(stats))
    log.info("Active picks checked: %d", total_checked)
    log.info("Newly resolved: %d (TP: %d, SL: %d, Expired: %d)", total_resolved, total_tp, total_sl, total_expired)
    log.info("Total resolved (cumulative): %d", len(all_resolved))

    if stats:
        log.info("")
        log.info("Per-system breakdown:")
        for sys_name in sorted(stats):
            s = stats[sys_name]
            resolved = s["tp_hit"] + s["sl_hit"] + s["expired"]
            log.info("  %-30s checked=%d resolved=%d (TP:%d SL:%d EXP:%d) no_price=%d",
                    sys_name, s["checked"], resolved, s["tp_hit"], s["sl_hit"], s["expired"], s["no_price"])

    log.info("=" * 70)
    log.info("Resolved picks saved to: %s", RESOLVED_FILE)
    return all_resolved


if __name__ == "__main__":
    main()
