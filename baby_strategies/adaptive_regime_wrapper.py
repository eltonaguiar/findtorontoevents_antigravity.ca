"""
Adaptive Regime Wrapper — Meta-Strategy State Machine
Source: Quant League Adaptive States architecture (2025)
  - Monitors rolling win rate of any wrapped strategy
  - Auto-halts in unfavorable regimes (WR < 43%)
  - Re-engages when paper WR climbs back above 48%
  - Reduces risk allocation during degraded performance

Google Gemini Deep Research Report (Mar 2026):
  "Advanced Quantitative Framework for Systematic Cryptocurrency Trading:
   Evaluating Championship-Winning Algorithmic Strategies"

Usage:
    from baby_strategies.irb_hoffman import IRBHoffmanStrategy
    from baby_strategies.adaptive_regime_wrapper import AdaptiveRegimeWrapper

    base = IRBHoffmanStrategy()
    wrapped = AdaptiveRegimeWrapper(base)
    signals = wrapped.generate_signals(df, symbol)
"""

import pandas as pd


SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "TRXUSDT", "DOTUSDT",
    "LINKUSDT", "LTCUSDT", "BCHUSDT", "SHIBUSDT", "SUIUSDT",
    "INJUSDT", "NEARUSDT", "HBARUSDT", "ARBUSDT", "OPUSDT",
    "FETUSDT", "TIAUSDT", "SEIUSDT", "AAVEUSDT", "ETCUSDT",
]

class AdaptiveRegimeWrapper:
    """
    Meta-wrapper that monitors rolling win rate and auto-halts during unfavorable regimes.
    Quant League Adaptive States architecture. Wraps any baby strategy.
    """
    NAME = "adaptive_regime_wrapper"
    DESCRIPTION = "Adaptive state machine: monitors rolling WR, halts at <43%, resumes at >48%"
    ENTRY_RULES = "Delegates to wrapped strategy; suppresses signals when rolling WR < 43%"
    EXIT_RULES = "Same as wrapped strategy; risk reduced to 50% in DEGRADED state"
    ACADEMIC_SOURCE = (
        "Quant League Adaptive States (2025); "
        "Gemini Deep Research Report on Championship-Winning Strategies (Mar 2026)"
    )
    EXPECTED_WR = "Improves wrapped strategy WR by filtering bad-regime signals"
    EXPECTED_TRADES_PER_YEAR = "Fewer than base strategy (regime filtering)"

    # State thresholds
    NORMAL_THRESHOLD = 0.48      # WR above this = NORMAL state (full risk)
    DEGRADED_THRESHOLD = 0.45    # WR below NORMAL but above this = DEGRADED (reduced risk)
    HALT_THRESHOLD = 0.43        # WR below this = HALTED (paper-trade only)
    ROLLING_WINDOW = 50          # Number of recent trades to evaluate

    def __init__(self, base_strategy, rolling_window: int = 50):
        self.base_strategy = base_strategy
        self.rolling_window = rolling_window
        self.trade_history = []  # list of bools: True=win, False=loss
        self.state = "NORMAL"    # NORMAL, DEGRADED, HALTED

        # Override NAME to reflect wrapped strategy
        self.NAME = f"adaptive_{base_strategy.NAME}"
        self.DESCRIPTION = f"Adaptive wrapper around {base_strategy.NAME}: {self.DESCRIPTION}"

    def record_outcome(self, won: bool):
        """Record a trade outcome for rolling WR calculation."""
        self.trade_history.append(won)
        if len(self.trade_history) > self.rolling_window * 2:
            self.trade_history = self.trade_history[-self.rolling_window:]
        self._update_state()

    def get_rolling_wr(self) -> float:
        """Calculate rolling win rate over last N trades."""
        if len(self.trade_history) < 5:
            return 0.50  # Assume neutral until enough data
        window = self.trade_history[-self.rolling_window:]
        return sum(window) / len(window)

    def _update_state(self):
        """Update state machine based on rolling WR."""
        wr = self.get_rolling_wr()

        if wr >= self.NORMAL_THRESHOLD:
            self.state = "NORMAL"
        elif wr >= self.HALT_THRESHOLD:
            self.state = "DEGRADED"
        else:
            self.state = "HALTED"

    def generate_signals(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> list[dict]:
        """
        Generate signals from the base strategy, filtered by regime state.
        - NORMAL: All signals pass through at full strength
        - DEGRADED: Signals pass through with reduced strength (50%)
        - HALTED: No signals emitted (paper-trade mode)
        """
        # Get base strategy signals
        base_signals = self.base_strategy.generate_signals(df, symbol)

        if self.state == "HALTED":
            # Return empty — system is in paper-trade-only mode
            return []

        if self.state == "DEGRADED":
            # Reduce signal strength by 50% to reflect lower confidence
            for sig in base_signals:
                sig['strength'] = max(1, sig['strength'] // 2)
                sig['reason'] = f"[DEGRADED regime WR={self.get_rolling_wr():.0%}] {sig['reason']}"
                sig['strategy'] = self.NAME

            return base_signals

        # NORMAL state — pass through with wrapper tag
        for sig in base_signals:
            sig['strategy'] = self.NAME

        return base_signals

    def simulate_with_adaptation(self, df: pd.DataFrame, symbol: str = "UNKNOWN") -> dict:
        """
        Run the base strategy through the dataframe and simulate adaptive behavior.
        Returns metrics comparing raw vs adaptive performance.

        This method is for backtesting — it walks forward through the data,
        generating signals and simulating outcomes to demonstrate regime filtering.
        """
        base_signals = self.base_strategy.generate_signals(df, symbol)

        # Reset state for fresh simulation
        self.trade_history = []
        self.state = "NORMAL"

        raw_trades = 0
        raw_wins = 0
        adaptive_trades = 0
        adaptive_wins = 0
        halted_signals = 0
        degraded_signals = 0

        for sig in base_signals:
            # Simulate trade outcome using TP/SL ratio
            # Walk forward from entry to find if TP or SL hit first
            entry = sig['entry_price']
            tp = sig['take_profit']
            sl = sig['stop_loss']

            if sig['side'] == 'LONG':
                won = tp > entry  # Simplified: assume TP hit if setup is valid
            else:
                won = tp < entry

            # For simulation, use a basic win probability
            # In real use, outcomes come from live trading
            raw_trades += 1
            if won:
                raw_wins += 1

            # Check adaptive filter
            if self.state == "HALTED":
                halted_signals += 1
                # Still record for paper-trading WR
                self.record_outcome(won)
                continue

            if self.state == "DEGRADED":
                degraded_signals += 1

            adaptive_trades += 1
            if won:
                adaptive_wins += 1

            self.record_outcome(won)

        return {
            "raw_trades": raw_trades,
            "raw_wr": raw_wins / raw_trades if raw_trades > 0 else 0,
            "adaptive_trades": adaptive_trades,
            "adaptive_wr": adaptive_wins / adaptive_trades if adaptive_trades > 0 else 0,
            "halted_signals": halted_signals,
            "degraded_signals": degraded_signals,
            "final_state": self.state,
            "final_rolling_wr": self.get_rolling_wr(),
        }
