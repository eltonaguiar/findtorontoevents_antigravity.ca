"""
Picks Router - Route signals to appropriate Discord channels

Routes:
- #freshpicks: Regular picks (confidence 0.6-0.79)
- #master-picks: High-confidence buy-now picks (confidence >= 0.8)
- #crypto-automation: System alerts and health
- #sandbox: Decommissioned/bad systems
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path
import requests
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import master-picks tracker (try absolute then relative for CI compatibility)
try:
    from signal_aggregator.master_picks_tracker import get_tracker
    TRACKER_AVAILABLE = True
except ImportError:
    try:
        from master_picks_tracker import get_tracker
        TRACKER_AVAILABLE = True
    except ImportError:
        TRACKER_AVAILABLE = False
        logger.warning("Master-picks tracker not available")

# Import price fetcher for validation (try absolute then relative for CI compatibility)
try:
    from signal_aggregator.price_fetcher import validate_entry_price, get_current_price
    PRICE_FETCHER_AVAILABLE = True
except ImportError:
    try:
        from price_fetcher import validate_entry_price, get_current_price
        PRICE_FETCHER_AVAILABLE = True
    except ImportError:
        PRICE_FETCHER_AVAILABLE = False
    logger.warning("Price fetcher not available")

# Portfolio circuit breaker — MANDATORY for production safety
from risk_management.portfolio_circuit_breaker import PortfolioCircuitBreaker, CircuitBreakerStatus
CIRCUIT_BREAKER_AVAILABLE = True  # Always True now — import failure = module failure

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_strategy_stats(strategy_name: str) -> Optional[dict]:
    """Load per-strategy historical performance from existing tracking files."""
    if not strategy_name:
        return None

    # Try alpha_engine strategy_performance.json first
    alpha_perf = REPO_ROOT / "alpha_engine" / "data" / "strategy_performance.json"
    if alpha_perf.exists():
        try:
            data = json.loads(alpha_perf.read_text())
            if strategy_name in data:
                s = data[strategy_name]
                closed = s.get("closed_picks", s.get("total_trades", 0))
                if closed >= 3:
                    return {
                        "win_rate": s.get("win_rate"),
                        "closed": closed,
                        "profit_factor": s.get("profit_factor"),
                        "sharpe": s.get("sharpe"),
                        "pnl": s.get("total_pnl_dollar", s.get("total_pnl_pct")),
                    }
        except Exception:
            pass

    # Try component_perf_daily.json
    comp = REPO_ROOT / "data" / "component_perf_daily.json"
    if comp.exists():
        try:
            data = json.loads(comp.read_text())
            components = data.get("components", data)
            if isinstance(components, list):
                for c in components:
                    if c.get("component", c.get("strategy", "")) == strategy_name:
                        closed = c.get("total_trades", 0)
                        if closed >= 3:
                            return {
                                "win_rate": c.get("win_rate"),
                                "closed": closed,
                                "profit_factor": c.get("profit_factor"),
                                "sharpe": c.get("sharpe_annualized", c.get("sharpe")),
                                "pnl": c.get("total_pnl_usdt"),
                            }
            elif isinstance(components, dict) and strategy_name in components:
                c = components[strategy_name]
                closed = c.get("total_trades", 0)
                if closed >= 3:
                    return {
                        "win_rate": c.get("win_rate"),
                        "closed": closed,
                        "profit_factor": c.get("profit_factor"),
                        "sharpe": c.get("sharpe_annualized"),
                        "pnl": c.get("total_pnl_usdt"),
                    }
        except Exception:
            pass

    return None


# Maximum age (in seconds) for a signal to be considered fresh.
# Signals older than this are skipped to prevent acting on stale data.
SIGNAL_FRESHNESS_MAX_SECONDS = 86400  # 24 hours — was 900 (15min), which killed all signals from systems running every 15-30min


class PicksRouter:
    """
    Routes trading signals to appropriate Discord channels based on confidence.
    """

    # Confidence thresholds (see tests/test_picks_pipeline_integration.py)
    MASTER_PICKS_THRESHOLD = 0.80
    FRESHPICKS_THRESHOLD = 0.62
    MAX_OPEN_POSITIONS = 15
    
    def __init__(self):
        """Initialize router with webhook URLs from environment."""
        self.webhooks = {
            'freshpicks': os.getenv('DISCORD_FRESHPICKS'),
            'master_picks': os.getenv('DISCORD_MASTER_PICKS'),
            'general': os.getenv('DISCORD_GENERAL'),
            'notifications': os.getenv('DISCORD_NOTIFICATIONS'),
            'sandbox': os.getenv('DISCORD_SANDBOX'),
            'automation': os.getenv('DISCORD_WEBHOOK_URL'),  # crypto-automation
            'incubator': os.getenv('DISCORD_INCUBATOR') or os.getenv('DISCORD_FRESHPICKS'),  # fallback to freshpicks
        }
        self.min_master_unique_systems = max(
            1, int(os.getenv("MASTER_MIN_UNIQUE_SYSTEMS", "2"))
        )
        self.min_master_consensus_score = float(
            os.getenv("MASTER_MIN_CONSENSUS_SCORE", "0.55")
        )
        
        # Validate webhooks
        self.available_channels = [k for k, v in self.webhooks.items() if v]
        logger.info(f"Available Discord channels: {self.available_channels}")

        # Load core whitelist for strategy routing (backwards-compatible)
        self._core_whitelist = self._load_core_whitelist()

    @staticmethod
    def get_max_picks(cb_level: str) -> dict:
        """Centralized pick caps based on circuit breaker level.

        Single source of truth for how many picks each channel can send
        at each circuit breaker level.
        """
        if cb_level in ("RED", "HALT"):
            return {"master": 0, "fresh": 0, "send_allowed": False}
        if cb_level == "YELLOW":
            return {"master": 2, "fresh": 5, "send_allowed": True}
        return {"master": 5, "fresh": 10, "send_allowed": True}

    # ------------------------------------------------------------------
    # Freshness SLA
    # ------------------------------------------------------------------

    def _is_signal_fresh(self, signal: Dict) -> bool:
        """
        Return True if the signal's timestamp is within SIGNAL_FRESHNESS_MAX_SECONDS.

        Accepts ISO-8601 strings or epoch floats in the 'timestamp' field.
        If no parseable timestamp is present the signal is treated as fresh
        (backwards-compatible).
        """
        ts_raw = signal.get("timestamp")
        if ts_raw is None:
            return True  # no timestamp -> assume fresh (legacy data)

        try:
            if isinstance(ts_raw, (int, float)):
                sig_time = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
            else:
                ts_str = str(ts_raw)
                # Handle both aware and naive ISO strings
                if ts_str.endswith("Z"):
                    ts_str = ts_str[:-1] + "+00:00"
                sig_time = datetime.fromisoformat(ts_str)
                if sig_time.tzinfo is None:
                    sig_time = sig_time.replace(tzinfo=timezone.utc)
        except Exception:
            return True  # unparseable -> treat as fresh

        age_seconds = (datetime.now(tz=timezone.utc) - sig_time).total_seconds()
        if age_seconds > SIGNAL_FRESHNESS_MAX_SECONDS:
            logger.warning(
                "Stale signal for %s: age=%.0fs (max=%ds)",
                signal.get("symbol", "UNKNOWN"),
                age_seconds,
                SIGNAL_FRESHNESS_MAX_SECONDS,
            )
            return False
        return True

    # ------------------------------------------------------------------
    # Core / Incubator strategy routing
    # ------------------------------------------------------------------

    def _load_core_whitelist(self) -> Optional[Dict]:
        """
        Load trading/data/core_whitelist.json if it exists.
        Returns None when the file is missing (backwards-compatible fallthrough).
        """
        whitelist_path = Path(__file__).resolve().parent.parent / "trading" / "data" / "core_whitelist.json"
        if not whitelist_path.exists():
            logger.info("core_whitelist.json not found - using default routing")
            return None
        try:
            with open(whitelist_path, "r") as f:
                data = json.load(f)
            logger.info(
                "Loaded core whitelist: %d core, %d incubator, %d kill-list",
                len(data.get("core_strategies", [])),
                len(data.get("incubator_strategies", [])),
                len(data.get("kill_list", [])),
            )
            return data
        except Exception as e:
            logger.error("Failed to load core_whitelist.json: %s", e)
            return None

    def _get_strategy_tier(self, signal: Dict) -> str:
        """
        Classify a signal's strategy into 'core', 'incubator', 'kill', or 'unknown'.

        Checks the signal's 'strategy', 'substrategy', and 'strategy_dna' fields
        against the core whitelist.
        """
        if self._core_whitelist is None:
            return "unknown"

        # Collect all candidate strategy names from the signal
        candidates = set()
        for key in ("strategy", "substrategy", "strategy_dna"):
            val = signal.get(key)
            if val:
                candidates.add(str(val).strip().lower())

        core = {s.lower() for s in self._core_whitelist.get("core_strategies", [])}
        incubator = {s.lower() for s in self._core_whitelist.get("incubator_strategies", [])}
        protected = {s.lower() for s in self._core_whitelist.get("protected_strategies", [])}
        safe = core | incubator | protected
        kill = set()
        for _ks in self._core_whitelist.get("kill_list", []):
            _bare = _ks.split("::", 1)[1].lower() if "::" in _ks else _ks.lower()
            if _bare in safe:
                continue  # never kill protected/core/incubator strategies
            kill.add(_ks.lower())
            if "::" in _ks:
                kill.add(_bare)

        if candidates & kill:
            return "kill"
        if candidates & core:
            return "core"
        if candidates & incubator:
            return "incubator"
        return "unknown"

    def _extract_unique_systems(self, signal: Dict) -> List[str]:
        """Extract unique system names from signal metadata."""
        raw_systems = []
        for key in ("agreeing_systems", "systems"):
            value = signal.get(key)
            if isinstance(value, list):
                raw_systems.extend([str(s).strip() for s in value if s])

        base_system = signal.get("system")
        if base_system:
            raw_systems.append(str(base_system).strip())

        unique = []
        seen = set()
        for system in raw_systems:
            if system and system not in seen:
                seen.add(system)
                unique.append(system)
        return unique

    def _passes_master_consensus_gate(self, signal: Dict) -> tuple[bool, str]:
        """
        Master picks must have multi-system agreement.

        Gate rules:
        - at least `min_master_unique_systems` unique systems  (default 2)
        - consensus_score must meet threshold when provided    (default 0.55)

        Reviewed 2026-03-03: Verified defaults (2 systems, 0.55 score) are
        correctly enforced.  The forced-send guard in send_signal() also
        calls this gate so manual channel overrides cannot bypass it.
        """
        unique_systems = self._extract_unique_systems(signal)
        declared_count = signal.get("consensus_count")
        try:
            declared_count = int(declared_count) if declared_count is not None else None
        except Exception:
            declared_count = None
        consensus_count = declared_count if declared_count is not None else len(unique_systems)

        if consensus_count < self.min_master_unique_systems:
            return (
                False,
                f"consensus_count={consensus_count} < required={self.min_master_unique_systems}",
            )

        consensus_score = signal.get("consensus_score")
        if consensus_score is not None:
            try:
                c_score = float(consensus_score)
                if c_score < self.min_master_consensus_score:
                    return (
                        False,
                        f"consensus_score={c_score:.2f} < required={self.min_master_consensus_score:.2f}",
                    )
            except Exception:
                pass

        return True, "passed"
    
    def _should_allow_short(self, signal: Dict) -> Tuple[bool, str]:
        """
        Determine if a SHORT signal should be allowed.
        
        Rules:
        1. Only allow shorts in TRENDING_DOWN or CRASH regime
        2. Require low confidence (< 0.30) - model predicts down move
        3. Avoid extreme fear (F&G < 10) - potential short squeeze
        4. Require adequate volatility (> 1% daily)
        
        Returns:
            (allowed: bool, reason: str)
        """
        direction = signal.get('direction', 'LONG')
        if direction != 'SELL':
            return True, "Not a short signal"
        
        regime = signal.get('regime', 'UNKNOWN')
        confidence = signal.get('confidence', 0.5)
        fg_index = signal.get('fear_greed_index', 50)
        volatility = signal.get('volatility_20', 0)
        
        # Rule 1: Regime check
        if regime not in ["TRENDING_DOWN", "CRASH", "bear", "bear_high_vol"]:
            return False, f"Short not allowed in {regime} regime"
        
        # Rule 2: Confidence check (model should predict down move)
        if confidence > 0.35:  # Too high confidence = model thinks it goes up
            return False, f"Confidence {confidence:.2f} too high for short"
        
        # Rule 3: Extreme fear check (avoid short squeeze)
        if fg_index < 10:
            return False, f"F&G {fg_index} - extreme fear, avoid short squeeze"
        
        # Rule 4: Volatility check (need enough movement)
        daily_vol = volatility / np.sqrt(365) if volatility else 0
        if daily_vol < 0.01:  # Less than 1% daily vol
            return False, f"Volatility too low: {daily_vol:.2%}"
        
        return True, "Short signal validated"
    
    def _is_crypto_symbol(self, symbol: str) -> bool:
        """Check if symbol is a cryptocurrency (not stock/ETF)."""
        if not symbol:
            return False
        
        symbol_upper = symbol.upper()
        
        # Stock/ETF symbols to exclude
        stock_symbols = {
            'SPY', 'QQQ', 'IWM', 'VIX', 'GLD', 'SLV', 'TLT', 'HYG',
            'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'TSLA', 'META', 'NVDA',
            'NFLX', 'AMD', 'INTC', 'BA', 'DIS', 'JPM', 'V', 'MA',
            'PG', 'KO', 'PEP', 'WMT', 'TGT', 'COST', 'HD', 'LOW'
        }
        
        # Check if it's a known stock
        if symbol_upper in stock_symbols:
            return False
        
        # Check for stock patterns (no USDT, USD, BTC, ETH, etc.)
        crypto_suffixes = ('USDT', 'USD', 'BTC', 'ETH', 'BNB', 'BUSD')
        if any(symbol_upper.endswith(s) for s in crypto_suffixes):
            return True
        
        # Check for common crypto patterns
        crypto_patterns = ('-USD', '-USDT', 'PERP', 'SWAP')
        if any(p in symbol_upper for p in crypto_patterns):
            return True
        
        # Default: if it doesn't look like a stock ticker (1-4 chars, no suffix)
        # be conservative and reject
        return False
    
    def _is_valid_signal(self, signal: Dict) -> bool:
        """
        Validate signal has all required fields with reasonable values.
        
        Returns:
            True if signal is valid, False otherwise
        """
        # Check required fields exist
        required = ['symbol', 'direction', 'confidence', 'entry_price']
        for field in required:
            if field not in signal or signal[field] is None:
                return False
        
        # Filter out non-crypto symbols (stocks, ETFs)
        symbol = signal.get('symbol', '')
        if not self._is_crypto_symbol(symbol):
            logger.debug(f"Skipping non-crypto symbol: {symbol}")
            return False
        
        # Check entry price is valid (not 0 or negative)
        entry = signal.get('entry_price')
        if not entry or entry <= 0:
            logger.warning(f"Invalid entry price for {signal.get('symbol')}: {entry}")
            return False
        
        # Check TP and SL if they exist (should be positive if present)
        tp = signal.get('tp_price')
        sl = signal.get('sl_price')
        
        if tp is not None and tp <= 0:
            logger.warning(f"Invalid TP for {signal.get('symbol')}: {tp}")
            return False
        
        if sl is not None and sl <= 0:
            logger.warning(f"Invalid SL for {signal.get('symbol')}: {sl}")
            return False
        
        # Check confidence is reasonable
        confidence = signal.get('confidence', 0)
        if not (0 <= confidence <= 1):
            logger.warning(f"Invalid confidence for {signal.get('symbol')}: {confidence}")
            return False
        
        # Price sanity check: entry price should be within acceptable range of current market price
        # Uses different thresholds for LONG vs SHORT to handle surge scenarios
        symbol = signal.get('symbol', '')
        direction = signal.get('direction', 'LONG')
        
        if PRICE_FETCHER_AVAILABLE:
            current_price = get_current_price(symbol)
            
            if current_price and current_price > 0:
                deviation_pct = abs(entry - current_price) / current_price * 100
                
                # For LONG signals: entry should be AT OR BELOW current price (or very close)
                # Buying 21% above market is a guaranteed loss
                if direction == 'LONG':
                    if entry > current_price * 1.05:  # Entry > 5% above current = reject
                        logger.warning(
                            f"LONG entry TOO HIGH for {symbol}: "
                            f"entry=${entry:.2f}, current=${current_price:.2f}, "
                            f"entry is {deviation_pct:.1f}% ABOVE market!"
                        )
                        return False
                    elif entry > current_price:
                        logger.warning(
                            f"LONG entry slightly above market for {symbol}: "
                            f"entry=${entry:.2f}, current=${current_price:.2f}"
                        )
                        # Allow but warn (within 5%)
                
                # For SHORT signals: entry can be above current price (we're shorting high)
                # But not more than 40% deviation
                elif direction == 'SHORT':
                    if deviation_pct > 40.0:
                        logger.warning(
                            f"SHORT entry too far from market for {symbol}: "
                            f"entry=${entry:.2f}, current=${current_price:.2f}, "
                            f"deviation={deviation_pct:.1f}%"
                        )
                        return False
        
        return True
    
    # ------------------------------------------------------------------
    # Circuit breaker integration
    # ------------------------------------------------------------------

    def _build_equity_curve(self) -> List[float]:
        """
        Build a simple equity curve from closed picks PnL data.

        Reads master_picks_tracker.json and converts closed picks into a
        cumulative equity curve starting at 100.  Returns an empty list
        when data is unavailable so the circuit breaker defaults to GREEN.
        """
        try:
            tracker_path = (
                Path(__file__).resolve().parent / "data" / "master_picks_tracker.json"
            )
            if not tracker_path.exists():
                return []
            with open(tracker_path, "r") as f:
                data = json.load(f)

            closed = [
                p for p in data.get("active_picks", []) + data.get("closed_picks", [])
                if p.get("status") == "closed" and p.get("pnl_percent") is not None
            ]
            if not closed:
                return []

            # Sort by exit_time ascending
            closed.sort(key=lambda p: p.get("exit_time") or "")

            equity = 100.0
            curve = [equity]
            for pick in closed:
                pnl_pct = float(pick["pnl_percent"]) / 100.0
                equity = equity * (1.0 + pnl_pct)
                curve.append(round(equity, 4))
            return curve
        except Exception as e:
            logger.debug("Could not build equity curve: %s", e)
            return []

    def _get_circuit_breaker_status(self):
        """
        Return a CircuitBreakerStatus (or None if unavailable).

        Always uses a try/except so failures here never break routing.
        """
        if not CIRCUIT_BREAKER_AVAILABLE:
            return None
        try:
            equity_curve = self._build_equity_curve()
            breaker = PortfolioCircuitBreaker(portfolio_value=100.0)
            return breaker.check(equity_curve)
        except Exception as e:
            logger.error("Circuit breaker check failed: %s", e)
            return None

    def _score_signal(self, signal: Dict) -> Dict:
        """
        Run pre-trade Monte Carlo scorer on a signal.

        Enriches the signal dict with scoring metadata.
        Returns the signal dict (mutated in-place for efficiency).
        Gracefully degrades if scorer is unavailable.
        """
        try:
            from risk_management.pretrade_scorer import score_signal as mc_score

            entry = signal.get("entry_price")
            tp = signal.get("tp_price")
            sl = signal.get("sl_price")
            direction = str(signal.get("direction", "BUY")).upper()
            symbol = signal.get("symbol", "UNKNOWN")

            if not all([entry, tp, sl]):
                signal["mc_grade"] = None  # can't score without TP/SL
                return signal

            result = mc_score(
                symbol=symbol,
                entry_price=float(entry),
                target_price=float(tp),
                stop_price=float(sl),
                direction=direction,
                n_sims=300,  # fast enough for live routing
                horizon_bars=24,
            )

            signal["mc_grade"] = result["grade"]
            signal["mc_prob_tp"] = result["prob_tp"]
            signal["mc_rr_ratio"] = result["rr_ratio"]
            signal["mc_expected_net"] = result["expected_net_pnl"]
            signal["mc_vol"] = result["vol_forecast"]

        except Exception as e:
            logger.debug("Pre-trade scorer unavailable: %s", e)
            signal["mc_grade"] = None

        return signal

    def route_signal(self, signal: Dict, _cb_status=None) -> str:
        """
        Determine which channel a signal should go to.

        Returns:
            Channel name ('master_picks', 'freshpicks', 'sandbox', or 'incubator')
        """
        # --- Circuit breaker gate (runs before any other routing logic) ---
        cb = _cb_status if _cb_status is not None else self._get_circuit_breaker_status()
        if cb is not None:
            if cb.level in ("HALT", "RED"):
                logger.warning(
                    "Circuit breaker %s — routing %s to sandbox. Reasons: %s",
                    cb.level,
                    signal.get("symbol", "UNKNOWN"),
                    ", ".join(cb.reasons) or "n/a",
                )
                return 'sandbox'
            # YELLOW: allow routing but caller (send_batch) enforces reduced cap

        # Validate signal first
        if not self._is_valid_signal(signal):
            return 'sandbox'

        # Freshness SLA: skip stale signals
        if not self._is_signal_fresh(signal):
            return 'sandbox'

        confidence = signal.get('confidence', 0)
        system = signal.get('system', 'unknown')

        # Check if system is decommissioned/bad
        bad_systems = self._get_bad_systems()
        if system in bad_systems:
            return 'sandbox'

        # Core / Incubator / Kill-list routing (Task 4)
        strategy_tier = self._get_strategy_tier(signal)
        if strategy_tier == "kill":
            logger.warning(
                "Dropping kill-listed strategy for %s (strategy=%s)",
                signal.get("symbol", "UNKNOWN"),
                signal.get("strategy") or signal.get("substrategy") or signal.get("strategy_dna"),
            )
            return 'sandbox'
        # Short-side filter: only allow shorts in appropriate regimes
        if signal.get('direction') == 'SELL':
            allowed, reason = self._should_allow_short(signal)
            if not allowed:
                logger.info(
                    "Blocking short for %s: %s",
                    signal.get("symbol", "UNKNOWN"),
                    reason
                )
                return 'sandbox'
        
        if strategy_tier == "incubator" or (strategy_tier == "unknown" and self._core_whitelist is not None):
            # Incubator and unknown strategies never reach master-picks.
            # They go to the incubator channel (falls back to freshpicks webhook).
            logger.info(
                "Routing %s to incubator (tier=%s, strategy=%s)",
                signal.get("symbol", "UNKNOWN"),
                strategy_tier,
                signal.get("strategy") or signal.get("substrategy") or signal.get("strategy_dna"),
            )
            return 'incubator'

        # Pre-trade Monte Carlo scoring (enriches signal, used for downgrade decisions)
        self._score_signal(signal)

        # Route based on confidence (core strategies only reach here)
        if confidence >= self.MASTER_PICKS_THRESHOLD:
            passes, reason = self._passes_master_consensus_gate(signal)
            if passes:
                # Downgrade F-grade signals from master to freshpicks
                if signal.get("mc_grade") == "F":
                    logger.info(
                        "Downgrading %s from master-picks (MC grade F, prob_tp=%.2f, rr=%.1f)",
                        signal.get("symbol", "UNKNOWN"),
                        signal.get("mc_prob_tp", 0),
                        signal.get("mc_rr_ratio", 0),
                    )
                    return 'freshpicks'
                return 'master_picks'
            logger.info(
                "Downgrading %s from master-picks to freshpicks (%s)",
                signal.get("symbol", "UNKNOWN"),
                reason,
            )
            return 'freshpicks'
        elif confidence >= self.FRESHPICKS_THRESHOLD:
            return 'freshpicks'
        else:
            return 'sandbox'  # Low confidence goes to sandbox
    
    def _get_bad_systems(self) -> List[str]:
        """Get list of decommissioned or bad systems."""
        # This could be loaded from a config file
        return os.getenv('BAD_SYSTEMS', '').split(',') if os.getenv('BAD_SYSTEMS') else []
    
    def send_signal(self, signal: Dict, channel: Optional[str] = None) -> bool:
        """
        Send a signal to appropriate Discord channel.
        
        Args:
            signal: Signal dictionary with symbol, direction, confidence, etc.
            channel: Optional override channel
            
        Returns:
            True if sent successfully
        """
        if channel is None:
            channel = self.route_signal(signal)
        elif channel == 'master_picks':
            # Prevent manual overrides from bypassing master consensus safety.
            passes, reason = self._passes_master_consensus_gate(signal)
            if not passes:
                rerouted = self.route_signal(signal)
                logger.warning(
                    "Blocked forced master-picks send for %s (%s). Rerouting to %s",
                    signal.get("symbol", "UNKNOWN"),
                    reason,
                    rerouted,
                )
                channel = rerouted
        
        webhook_url = self.webhooks.get(channel)
        if not webhook_url:
            logger.warning(f"No webhook configured for channel: {channel}")
            return False
        
        # Build Discord embed
        embed = self._build_signal_embed(signal, channel)
        
        payload = {
            'embeds': [embed]
        }
        
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 204:
                logger.info(f"Signal sent to #{channel}: {signal.get('symbol')}")
                
                # Log to master-picks tracker if sent to master_picks
                if channel == 'master_picks' and TRACKER_AVAILABLE:
                    try:
                        tracker = get_tracker()
                        systems = signal.get('systems', [signal.get('system', 'unknown')])
                        tracker.add_pick(signal, systems)
                        logger.info(f"Logged master-pick to tracker: {signal.get('symbol')}")
                    except Exception as e:
                        logger.error(f"Failed to log master-pick: {e}")
                
                return True
            else:
                logger.error(f"Failed to send to #{channel}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending to #{channel}: {e}")
            return False
    
    def _build_signal_embed(self, signal: Dict, channel: str) -> Dict:
        """Build Discord embed for a signal."""
        symbol = signal.get('symbol', 'UNKNOWN')
        direction = signal.get('direction', 'NEUTRAL')
        confidence = signal.get('confidence', 0)
        system = signal.get('system', 'unknown')

        # Try to get substrategy info
        substrategy = signal.get('substrategy') or signal.get('strategy')
        if substrategy:
            system_display = f"{system}/{substrategy}"
        else:
            system_display = system

        # Determine color based on direction and channel
        if channel == 'master_picks':
            color = 0x00ff00  # Green for master picks
            title = f"MASTER PICK — {symbol} — {direction}"
        elif channel == 'freshpicks':
            color = 0x3498db  # Blue for fresh picks
            title = f"{symbol} {direction}"
        else:
            color = 0x95a5a6  # Gray for sandbox
            title = f"{symbol} {direction} (Low Confidence)"

        # Build fields
        fields = [
            {
                'name': 'Confidence',
                'value': f"{confidence:.1%}",
                'inline': True
            },
            {
                'name': 'System',
                'value': system_display,
                'inline': True
            }
        ]

        # Strategy performance track record
        strategy_name = signal.get('strategy') or signal.get('substrategy') or signal.get('strategy_dna') or ''
        if strategy_name:
            stats = _load_strategy_stats(strategy_name)
            if stats:
                wr = stats.get('win_rate')
                wr_str = f"{wr:.0%}" if wr is not None else "--"
                closed = stats.get('closed', 0)
                fields.append({
                    'name': f'Track Record ({closed} trades)',
                    'value': f"WR: **{wr_str}** | Sharpe: {stats.get('sharpe', '--')}",
                    'inline': True
                })

        # Add consensus info (agreeing systems)
        consensus_count = signal.get('consensus_count', 1)
        total_systems = signal.get('total_systems', 1)
        agreeing = signal.get('agreeing_systems') or signal.get('systems') or []
        if consensus_count > 1 or agreeing:
            systems_str = ", ".join(agreeing[:5]) if agreeing else f"{consensus_count} systems"
            fields.append({
                'name': f'Consensus ({consensus_count}/{total_systems})',
                'value': systems_str,
                'inline': False
            })

        # Add price info if available
        entry = signal.get('entry_price')
        tp = signal.get('tp_price')
        sl = signal.get('sl_price')

        if entry:
            fields.append({
                'name': 'Entry',
                'value': f"${entry:,.2f}",
                'inline': True
            })

        if tp:
            fields.append({
                'name': 'Target',
                'value': f"${tp:,.2f}",
                'inline': True
            })

        if sl:
            fields.append({
                'name': 'Stop Loss',
                'value': f"${sl:,.2f}",
                'inline': True
            })

        # Calculate R:R if both TP and SL available
        if tp and sl and entry:
            risk = abs(entry - sl)
            reward = abs(tp - entry)
            if risk > 0:
                rr = reward / risk
                fields.append({
                    'name': 'Risk:Reward',
                    'value': f"1:{rr:.2f}",
                    'inline': True
                })

        # Add signal expiry (15 min from now — Discord relative timestamp)
        from datetime import timedelta
        expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=15)
        fields.append({
            'name': 'Expires',
            'value': f"<t:{int(expires_at.timestamp())}:R>",
            'inline': True
        })

        # Add ML quality score if available
        quality = signal.get('ml_quality', {})
        if quality and isinstance(quality, dict):
            quality_score = quality.get('quality_score')
            if quality_score:
                fields.append({
                    'name': 'ML Quality',
                    'value': f"{quality_score:.1%}",
                    'inline': True
                })

        embed = {
            'title': title,
            'color': color,
            'fields': fields,
            'timestamp': datetime.now(tz=timezone.utc).isoformat(),
            'footer': {
                'text': f'{system} | KIMI Research'
            }
        }

        # Add description for master picks
        if channel == 'master_picks':
            embed['description'] = (
                f"**High-confidence {direction} signal**\n"
                f"Consensus: {consensus_count}/{total_systems} systems agree "
                f"({confidence:.1%} confidence)"
            )
        
        return embed
    
    def send_batch(self, signals: List[Dict]) -> Dict[str, int]:
        """
        Send multiple signals, routing each appropriately.

        Circuit breaker awareness:
        - HALT/RED: all signals go to sandbox (no Discord sends)
        - YELLOW:   max picks per channel reduced by 50%
        - GREEN:    normal routing

        Returns:
            Dict with count per channel
        """
        counts = {
            'master_picks': 0,
            'freshpicks': 0,
            'incubator': 0,
            'sandbox': 0,
            'failed': 0
        }

        # Fetch circuit breaker status once for the whole batch
        cb = self._get_circuit_breaker_status()

        if cb is not None and cb.level in ("HALT", "RED"):
            logger.warning(
                "Circuit breaker %s — entire batch routed to sandbox (%d signals). Reasons: %s",
                cb.level,
                len(signals),
                ", ".join(cb.reasons) or "n/a",
            )
            counts['sandbox'] = len(signals)
            return counts

        if cb is not None and cb.level == "YELLOW":
            logger.warning(
                "Circuit breaker YELLOW — max picks per channel reduced by 50%%. Reasons: %s",
                ", ".join(cb.reasons) or "n/a",
            )

        for signal in signals:
            channel = self.route_signal(signal, _cb_status=cb)
            if self.send_signal(signal, channel):
                counts[channel] += 1
            else:
                counts['failed'] += 1

        logger.info(f"Batch send complete: {counts}")
        return counts
    
    def send_system_alert(self, message: str, level: str = 'info') -> bool:
        """
        Send system alert to automation channel.
        
        Args:
            message: Alert message
            level: 'info', 'warning', 'critical'
        """
        webhook_url = self.webhooks.get('automation') or self.webhooks.get('notifications')
        if not webhook_url:
            return False
        
        colors = {
            'info': 0x3498db,
            'warning': 0xf39c12,
            'critical': 0xe74c3c
        }
        
        payload = {
            'embeds': [{
                'title': f'System {level.upper()}',
                'description': message,
                'color': colors.get(level, 0x3498db),
                'timestamp': datetime.now().isoformat()
            }]
        }
        
        import time as _time
        for _attempt in range(3):
            try:
                response = requests.post(webhook_url, json=payload, timeout=10)
                if response.status_code in (200, 204):
                    return True
                if response.status_code == 429:
                    _time.sleep(response.json().get("retry_after", 3))
                    continue
                if _attempt < 2:
                    _time.sleep(2 * (_attempt + 1))
                    continue
                return False
            except Exception as e:
                if _attempt == 2:
                    logger.error(f"Failed to send alert after 3 attempts: {e}")
                    return False
                _time.sleep(2 * (_attempt + 1))
        return False

    def send_health_report(self, report: Dict) -> bool:
        """Send health report to automation channel."""
        webhook_url = self.webhooks.get('automation')
        if not webhook_url:
            return False

        status = report.get('overall_status', 'UNKNOWN')
        colors = {
            'HEALTHY': 0x2ecc71,
            'WARNING': 0xf39c12,
            'ERROR': 0xe74c3c,
            'CRITICAL': 0x992d22
        }

        fields = []
        for check_name, check_data in report.get('checks', {}).items():
            status_emoji = '✅' if check_data.get('status') == 'OK' else '⚠️'
            fields.append({
                'name': f"{status_emoji} {check_name}",
                'value': check_data.get('status', 'Unknown'),
                'inline': True
            })

        payload = {
            'embeds': [{
                'title': f'🏥 Health Check: {status}',
                'color': colors.get(status, 0x95a5a6),
                'fields': fields,
                'timestamp': datetime.now().isoformat(),
                'footer': {
                    'text': 'Auto-generated health report'
                }
            }]
        }

        import time as _time
        for _attempt in range(3):
            try:
                response = requests.post(webhook_url, json=payload, timeout=10)
                if response.status_code in (200, 204):
                    return True
                if response.status_code == 429:
                    _time.sleep(response.json().get("retry_after", 3))
                    continue
                if _attempt < 2:
                    _time.sleep(2 * (_attempt + 1))
                    continue
                return False
            except Exception as e:
                if _attempt == 2:
                    logger.error(f"Failed to send health report after 3 attempts: {e}")
                    return False
                _time.sleep(2 * (_attempt + 1))
        return False
    
    def send_master_picks_health_score(self) -> bool:
        """
        Send master-picks health score to #master-picks channel.
        Returns True if sent successfully.
        """
        if not TRACKER_AVAILABLE:
            logger.warning("Master-picks tracker not available")
            return False
        
        webhook_url = self.webhooks.get('master_picks')
        if not webhook_url:
            logger.warning("No webhook configured for master_picks channel")
            return False
        
        try:
            tracker = get_tracker()
            embed = tracker.format_health_embed()
            
            payload = {'embeds': [embed]}
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 204:
                logger.info("Master-picks health score sent successfully")
                return True
            else:
                logger.error(f"Failed to send health score: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending master-picks health score: {e}")
            return False
    
    def send_closed_picks_summary(self, days: int = 30) -> bool:
        """
        Send closed picks summary to #master-picks channel.
        Use this for the !closed command.
        Returns True if sent successfully.
        """
        if not TRACKER_AVAILABLE:
            logger.warning("Master-picks tracker not available")
            return False
        
        webhook_url = self.webhooks.get('master_picks')
        if not webhook_url:
            logger.warning("No webhook configured for master_picks channel")
            return False
        
        try:
            tracker = get_tracker()
            embed = tracker.format_closed_picks_embed(days)
            
            if not embed:
                # Send "no data" message
                embed = {
                    'title': 'Closed Master-Picks',
                    'description': 'No closed picks data available',
                    'color': 0x95a5a6,
                    'timestamp': datetime.now().isoformat()
                }
            
            payload = {'embeds': [embed]}
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 204:
                logger.info(f"Closed picks summary sent successfully ({days}d)")
                return True
            else:
                logger.error(f"Failed to send closed picks: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending closed picks summary: {e}")
            return False


# Convenience function for quick routing
def route_and_send(signal: Dict) -> bool:
    """Quick function to route and send a single signal."""
    router = PicksRouter()
    return router.send_signal(signal)


if __name__ == '__main__':
    # Test routing
    router = PicksRouter()
    
    test_signals = [
        {
            'symbol': 'BTCUSDT',
            'direction': 'LONG',
            'confidence': 0.85,
            'system': 'alpha_engine',
            'entry_price': 85000,
            'tp_price': 90000,
            'sl_price': 82000
        },
        {
            'symbol': 'ETHUSDT',
            'direction': 'SHORT',
            'confidence': 0.65,
            'system': 'mercury2',
            'entry_price': 2500,
            'tp_price': 2300,
            'sl_price': 2600
        },
        {
            'symbol': 'SOLUSDT',
            'direction': 'LONG',
            'confidence': 0.45,  # Low confidence
            'system': 'test_system'
        }
    ]
    
    for signal in test_signals:
        channel = router.route_signal(signal)
        print(f"{signal['symbol']} -> #{channel}")
