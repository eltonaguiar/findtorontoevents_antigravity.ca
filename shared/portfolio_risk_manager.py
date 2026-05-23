"""
Portfolio Risk Manager — portfolio-level circuit breaker enforcing global risk
limits across all signal systems (KIMI, Alpha Engine, Mercury, etc.).

Provides drawdown guards, turnover caps, concentration limits, leverage checks,
and automated exposure reduction recommendations.

Usage:
    from shared.portfolio_risk_manager import PortfolioRiskManager

    rm = PortfolioRiskManager()
    report = rm.generate_risk_report(positions, equity_curve, trades_today, capital)
    check = rm.check_new_trade(signal, current_portfolio)

Dependencies: numpy only.  Runs on GitHub Actions Python 3.11.
"""

from typing import Dict, List, Optional, Tuple, Union

import numpy as np

# ---------------------------------------------------------------------------
# Asset-class heuristic (shared with risk_parity_sizer)
# ---------------------------------------------------------------------------
_CRYPTO_SUFFIXES = ("USDT", "USD", "BUSD", "BTC", "ETH")
_FOREX_QUOTES = ("USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD")


def _asset_class(symbol: str) -> str:
    """Infer asset class from symbol name."""
    s = symbol.upper().strip()
    if len(s) == 6 and s.isalpha() and s[3:] in _FOREX_QUOTES:
        return "forex"
    for suf in _CRYPTO_SUFFIXES:
        if s.endswith(suf):
            return "crypto"
    if len(s) <= 5 and s.isalpha():
        return "equity"
    return "unknown"


# ---------------------------------------------------------------------------
# Singleton metaclass
# ---------------------------------------------------------------------------
class _Singleton(type):
    """Metaclass that ensures only one instance of a class exists."""
    _instances: Dict[type, object] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


# ---------------------------------------------------------------------------
# Portfolio Risk Manager
# ---------------------------------------------------------------------------
class PortfolioRiskManager(metaclass=_Singleton):
    """Portfolio-level risk manager (singleton).

    Enforces global limits on drawdown, turnover, concentration, leverage,
    and correlated positions across all signal systems.

    Parameters
    ----------
    max_drawdown : float
        Maximum tolerable drawdown fraction (default 12%).
    max_daily_turnover : float
        Maximum daily trading volume as fraction of capital (default 30%).
    max_position_pct : float
        Maximum single-position size as fraction of capital (default 20%).
    max_leverage : float
        Maximum gross leverage (default 3.0x).
    max_correlated_positions : int
        Maximum number of positions in the same asset class (default 5).
    """

    def __init__(
        self,
        max_drawdown: float = 0.12,
        max_daily_turnover: float = 0.30,
        max_position_pct: float = 0.20,
        max_leverage: float = 3.0,
        max_correlated_positions: int = 5,
    ):
        self.max_drawdown = max_drawdown
        self.max_daily_turnover = max_daily_turnover
        self.max_position_pct = max_position_pct
        self.max_leverage = max_leverage
        self.max_correlated_positions = max_correlated_positions

    # -- Allow reconfiguration (useful for tests despite singleton) ----------
    def reconfigure(self, **kwargs):
        """Update parameters on the singleton instance."""
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    # -----------------------------------------------------------------------
    # check_new_trade
    # -----------------------------------------------------------------------
    def check_new_trade(
        self,
        signal: Dict,
        current_portfolio: Dict,
    ) -> Dict:
        """Decide whether a proposed trade is allowed given current portfolio state.

        Parameters
        ----------
        signal : dict
            Proposed trade with keys: symbol, direction, size_usd, volatility (optional).
        current_portfolio : dict
            Current state with keys: positions (list[dict]), equity_curve (list[float]),
            trades_today (list[dict]), capital (float).

        Returns
        -------
        dict
            {allowed, reason, adjusted_size, risk_score}
        """
        positions = current_portfolio.get("positions", [])
        equity_curve = current_portfolio.get("equity_curve", [])
        trades_today = current_portfolio.get("trades_today", [])
        capital = current_portfolio.get("capital", 0.0)

        if capital <= 0:
            return {
                "allowed": False,
                "reason": "Capital is zero or negative.",
                "adjusted_size": 0.0,
                "risk_score": 1.0,
            }

        proposed_size = signal.get("size_usd", 0.0)
        symbol = signal.get("symbol", "UNKNOWN")
        reasons = []
        scale = 1.0
        risk_score = 0.0

        # 1. Drawdown check
        dd = self.drawdown_check(equity_curve)
        if dd["is_breached"]:
            return {
                "allowed": False,
                "reason": f"Drawdown breached: {dd['current_dd_pct']*100:.1f}% "
                          f"(max {self.max_drawdown*100:.1f}%).",
                "adjusted_size": 0.0,
                "risk_score": 1.0,
            }
        if dd["scale_factor"] < 1.0:
            scale = min(scale, dd["scale_factor"])
            reasons.append(f"DD scale-down to {dd['scale_factor']*100:.0f}%")
        risk_score += dd["current_dd_pct"] / self.max_drawdown * 0.3

        # 2. Position size check
        if capital > 0 and proposed_size / capital > self.max_position_pct:
            max_allowed = capital * self.max_position_pct
            scale = min(scale, max_allowed / proposed_size)
            reasons.append(
                f"Position capped at {self.max_position_pct*100:.0f}% of capital"
            )
        risk_score += min(proposed_size / capital, 1.0) * 0.15 if capital > 0 else 0

        # 3. Correlated positions check
        new_class = _asset_class(symbol)
        same_class_count = sum(
            1 for p in positions if _asset_class(p.get("symbol", "")) == new_class
        )
        if same_class_count >= self.max_correlated_positions:
            return {
                "allowed": False,
                "reason": f"Too many correlated positions: {same_class_count} "
                          f"{new_class} positions (max {self.max_correlated_positions}).",
                "adjusted_size": 0.0,
                "risk_score": 0.8,
            }
        if same_class_count >= self.max_correlated_positions - 1:
            scale = min(scale, 0.5)
            reasons.append(f"Near correlation limit ({same_class_count} {new_class})")
        risk_score += (same_class_count / self.max_correlated_positions) * 0.2

        # 4. Turnover check
        to = self.turnover_check(trades_today, capital)
        if not to["allowed"]:
            return {
                "allowed": False,
                "reason": f"Daily turnover budget exhausted: {to['turnover_pct']*100:.1f}%.",
                "adjusted_size": 0.0,
                "risk_score": 0.9,
            }
        if to["budget_remaining_pct"] < 0.2:
            scale = min(scale, to["budget_remaining_pct"] / 0.2)
            reasons.append(
                f"Low turnover budget ({to['budget_remaining_pct']*100:.0f}% left)"
            )
        risk_score += (1.0 - to["budget_remaining_pct"]) * 0.15

        # 5. Leverage check
        lev = self.leverage_check(positions, capital)
        # Estimate what leverage would be after adding the new position
        new_gross = lev["gross_leverage"] + (proposed_size * scale) / capital if capital > 0 else 0
        if new_gross > self.max_leverage:
            headroom = max(0, self.max_leverage - lev["gross_leverage"])
            if headroom <= 0:
                return {
                    "allowed": False,
                    "reason": f"Leverage limit reached: {lev['gross_leverage']:.2f}x "
                              f"(max {self.max_leverage:.1f}x).",
                    "adjusted_size": 0.0,
                    "risk_score": 0.95,
                }
            max_add = headroom * capital
            scale = min(scale, max_add / proposed_size)
            reasons.append(f"Leverage-constrained to {headroom*capital:.0f} USD headroom")
        risk_score += (lev["gross_leverage"] / self.max_leverage) * 0.2

        # Clamp risk_score to [0, 1]
        risk_score = round(min(max(risk_score, 0.0), 1.0), 4)
        adjusted_size = round(proposed_size * scale, 2)

        reason = "Trade allowed." if not reasons else "; ".join(reasons) + "."
        return {
            "allowed": True,
            "reason": reason,
            "adjusted_size": adjusted_size,
            "risk_score": risk_score,
        }

    # -----------------------------------------------------------------------
    # compute_portfolio_risk
    # -----------------------------------------------------------------------
    def compute_portfolio_risk(self, positions: List[Dict]) -> Dict:
        """Compute aggregate portfolio risk metrics.

        Each position dict should contain: symbol, size_usd, direction
        ("LONG"/"SHORT"), and optionally volatility (annualized decimal).

        Returns
        -------
        dict
            {total_exposure, net_exposure, gross_leverage, estimated_var_95,
             max_drawdown_current, risk_budget_used_pct, concentration_score}
        """
        if not positions:
            return {
                "total_exposure": 0.0,
                "net_exposure": 0.0,
                "gross_leverage": 0.0,
                "estimated_var_95": 0.0,
                "max_drawdown_current": 0.0,
                "risk_budget_used_pct": 0.0,
                "concentration_score": 0.0,
            }

        long_exp = 0.0
        short_exp = 0.0
        var_components = []

        for p in positions:
            size = abs(p.get("size_usd", 0.0))
            direction = p.get("direction", "LONG").upper()
            vol = p.get("volatility", 0.50)  # default 50% annual vol

            if direction in ("LONG", "BUY"):
                long_exp += size
            else:
                short_exp += size

            # Parametric VaR component: size * vol * z_95 (daily)
            daily_vol = vol / np.sqrt(252)
            var_components.append(size * daily_vol * 1.645)

        total_exposure = long_exp + short_exp
        net_exposure = long_exp - short_exp

        # Portfolio VaR: sqrt-sum-of-squares (assumes zero correlation as
        # conservative simplification — actual correlated VaR would be higher)
        estimated_var_95 = float(np.sqrt(np.sum(np.array(var_components) ** 2)))

        # Concentration via HHI
        sizes = [abs(p.get("size_usd", 0.0)) for p in positions]
        total_sz = sum(sizes) if sizes else 1.0
        weights = [s / total_sz for s in sizes] if total_sz > 0 else []
        hhi = sum(w ** 2 for w in weights)

        return {
            "total_exposure": round(total_exposure, 2),
            "net_exposure": round(net_exposure, 2),
            "gross_leverage": round(total_exposure, 2),  # caller divides by capital
            "estimated_var_95": round(estimated_var_95, 2),
            "max_drawdown_current": 0.0,  # filled by generate_risk_report
            "risk_budget_used_pct": 0.0,  # filled by generate_risk_report
            "concentration_score": round(hhi, 4),
        }

    # -----------------------------------------------------------------------
    # drawdown_check
    # -----------------------------------------------------------------------
    def drawdown_check(self, equity_curve: List[float]) -> Dict:
        """Analyze drawdown from an equity curve.

        Returns
        -------
        dict
            {current_dd_pct, max_dd_pct, dd_duration_bars, is_breached, scale_factor}
        """
        if not equity_curve or len(equity_curve) < 2:
            return {
                "current_dd_pct": 0.0,
                "max_dd_pct": 0.0,
                "dd_duration_bars": 0,
                "is_breached": False,
                "scale_factor": 1.0,
            }

        arr = np.array(equity_curve, dtype=float)
        running_max = np.maximum.accumulate(arr)
        drawdowns = (running_max - arr) / np.where(running_max > 0, running_max, 1.0)

        current_dd = float(drawdowns[-1])
        max_dd = float(np.max(drawdowns))

        # Duration: how many bars since the last peak
        peak_idx = int(np.argmax(running_max == running_max[-1]))
        # More precisely: last index where equity equaled running max
        peak_indices = np.where(arr >= running_max)[0]
        if len(peak_indices) > 0:
            last_peak = int(peak_indices[-1])
            dd_duration = len(arr) - 1 - last_peak
        else:
            dd_duration = len(arr) - 1

        # Scale factor: linear ramp between threshold/2 and threshold
        half = self.max_drawdown / 2.0
        if current_dd > self.max_drawdown:
            scale_factor = 0.0
            is_breached = True
        elif current_dd > half:
            scale_factor = round((self.max_drawdown - current_dd) / half, 4)
            is_breached = False
        else:
            scale_factor = 1.0
            is_breached = False

        return {
            "current_dd_pct": round(current_dd, 6),
            "max_dd_pct": round(max_dd, 6),
            "dd_duration_bars": dd_duration,
            "is_breached": is_breached,
            "scale_factor": scale_factor,
        }

    # -----------------------------------------------------------------------
    # turnover_check
    # -----------------------------------------------------------------------
    def turnover_check(self, trades_today: List[Dict], capital: float) -> Dict:
        """Check cumulative daily trading volume against turnover cap.

        Each trade dict should have size_usd (notional value traded).

        Returns
        -------
        dict
            {turnover_pct, budget_remaining_pct, allowed}
        """
        if capital <= 0:
            return {
                "turnover_pct": 0.0,
                "budget_remaining_pct": 0.0,
                "allowed": False,
            }

        total_traded = sum(abs(t.get("size_usd", 0.0)) for t in trades_today)
        turnover_pct = total_traded / capital
        remaining = max(0.0, self.max_daily_turnover - turnover_pct)

        return {
            "turnover_pct": round(turnover_pct, 6),
            "budget_remaining_pct": round(remaining / self.max_daily_turnover, 6)
                if self.max_daily_turnover > 0 else 0.0,
            "allowed": turnover_pct < self.max_daily_turnover,
        }

    # -----------------------------------------------------------------------
    # concentration_check
    # -----------------------------------------------------------------------
    def concentration_check(self, positions: List[Dict]) -> Dict:
        """Evaluate portfolio concentration using HHI.

        Returns
        -------
        dict
            {top_position_pct, hhi_score, is_concentrated, recommendation}
        """
        if not positions:
            return {
                "top_position_pct": 0.0,
                "hhi_score": 0.0,
                "is_concentrated": False,
                "recommendation": "No positions open.",
            }

        sizes = [abs(p.get("size_usd", 0.0)) for p in positions]
        total = sum(sizes)
        if total <= 0:
            return {
                "top_position_pct": 0.0,
                "hhi_score": 0.0,
                "is_concentrated": False,
                "recommendation": "No exposure.",
            }

        weights = [s / total for s in sizes]
        top_pct = max(weights)
        hhi = sum(w ** 2 for w in weights)

        is_concentrated = top_pct > 0.25 or hhi > 0.25

        if is_concentrated:
            if top_pct > 0.25:
                rec = (
                    f"Top position is {top_pct*100:.1f}% of portfolio — "
                    f"consider trimming to below 25%."
                )
            else:
                rec = (
                    f"HHI={hhi:.3f} indicates high concentration — "
                    f"consider diversifying across more positions."
                )
        else:
            rec = f"Concentration acceptable (HHI={hhi:.3f}, top={top_pct*100:.1f}%)."

        return {
            "top_position_pct": round(top_pct, 6),
            "hhi_score": round(hhi, 6),
            "is_concentrated": is_concentrated,
            "recommendation": rec,
        }

    # -----------------------------------------------------------------------
    # leverage_check
    # -----------------------------------------------------------------------
    def leverage_check(self, positions: List[Dict], capital: float) -> Dict:
        """Check gross and net leverage.

        Returns
        -------
        dict
            {gross_leverage, net_leverage, allowed, max_allowed}
        """
        if capital <= 0 or not positions:
            return {
                "gross_leverage": 0.0,
                "net_leverage": 0.0,
                "allowed": True,
                "max_allowed": self.max_leverage,
            }

        long_exp = 0.0
        short_exp = 0.0
        for p in positions:
            size = abs(p.get("size_usd", 0.0))
            direction = p.get("direction", "LONG").upper()
            if direction in ("LONG", "BUY"):
                long_exp += size
            else:
                short_exp += size

        gross = (long_exp + short_exp) / capital
        net = (long_exp - short_exp) / capital

        return {
            "gross_leverage": round(gross, 4),
            "net_leverage": round(net, 4),
            "allowed": gross <= self.max_leverage,
            "max_allowed": self.max_leverage,
        }

    # -----------------------------------------------------------------------
    # generate_risk_report
    # -----------------------------------------------------------------------
    def generate_risk_report(
        self,
        positions: List[Dict],
        equity_curve: List[float],
        trades_today: List[Dict],
        capital: float,
    ) -> Dict:
        """Generate comprehensive portfolio risk snapshot.

        Returns
        -------
        dict
            {overall_status (GREEN/YELLOW/RED), alerts, metrics}
        """
        dd = self.drawdown_check(equity_curve)
        to = self.turnover_check(trades_today, capital)
        conc = self.concentration_check(positions)
        lev = self.leverage_check(positions, capital)
        risk = self.compute_portfolio_risk(positions)

        # Enrich risk metrics
        risk["max_drawdown_current"] = dd["current_dd_pct"]
        if capital > 0:
            risk["gross_leverage"] = round(risk["total_exposure"] / capital, 4)
        risk["risk_budget_used_pct"] = round(
            dd["current_dd_pct"] / self.max_drawdown * 100, 2
        ) if self.max_drawdown > 0 else 0.0

        # Build alerts
        alerts = []
        if dd["is_breached"]:
            alerts.append(
                f"CRITICAL: Drawdown {dd['current_dd_pct']*100:.1f}% exceeds "
                f"max {self.max_drawdown*100:.1f}%"
            )
        elif dd["scale_factor"] < 1.0:
            alerts.append(
                f"WARNING: Drawdown {dd['current_dd_pct']*100:.1f}% — "
                f"position sizing reduced to {dd['scale_factor']*100:.0f}%"
            )
        if not to["allowed"]:
            alerts.append(
                f"CRITICAL: Daily turnover {to['turnover_pct']*100:.1f}% "
                f"exceeds cap {self.max_daily_turnover*100:.0f}%"
            )
        elif to["budget_remaining_pct"] < 0.2:
            alerts.append(
                f"WARNING: Only {to['budget_remaining_pct']*100:.0f}% "
                f"of daily turnover budget remaining"
            )
        if conc["is_concentrated"]:
            alerts.append(f"WARNING: {conc['recommendation']}")
        if not lev["allowed"]:
            alerts.append(
                f"CRITICAL: Gross leverage {lev['gross_leverage']:.2f}x "
                f"exceeds max {self.max_leverage:.1f}x"
            )
        elif lev["gross_leverage"] > self.max_leverage * 0.8:
            alerts.append(
                f"WARNING: Leverage {lev['gross_leverage']:.2f}x approaching "
                f"limit {self.max_leverage:.1f}x"
            )

        # Determine overall status
        has_critical = any(a.startswith("CRITICAL") for a in alerts)
        has_warning = any(a.startswith("WARNING") for a in alerts)

        if has_critical:
            status = "RED"
        elif has_warning:
            status = "YELLOW"
        else:
            status = "GREEN"

        return {
            "overall_status": status,
            "alerts": alerts,
            "metrics": {
                "drawdown": dd,
                "turnover": to,
                "concentration": conc,
                "leverage": lev,
                "portfolio_risk": risk,
            },
        }

    # -----------------------------------------------------------------------
    # should_reduce_exposure
    # -----------------------------------------------------------------------
    def should_reduce_exposure(
        self,
        positions: List[Dict],
        equity_curve: List[float],
    ) -> Dict:
        """Recommend whether and how to reduce portfolio exposure.

        Suggests closing worst-performing and most-correlated positions first.

        Returns
        -------
        dict
            {should_reduce, target_reduction_pct, reason, positions_to_close}
        """
        if not positions:
            return {
                "should_reduce": False,
                "target_reduction_pct": 0.0,
                "reason": "No positions to reduce.",
                "positions_to_close": [],
            }

        dd = self.drawdown_check(equity_curve)

        if not dd["is_breached"] and dd["scale_factor"] >= 0.8:
            return {
                "should_reduce": False,
                "target_reduction_pct": 0.0,
                "reason": f"Drawdown {dd['current_dd_pct']*100:.1f}% within safe zone.",
                "positions_to_close": [],
            }

        # Calculate target reduction
        if dd["is_breached"]:
            target_reduction = 0.50  # Cut 50% of exposure when breached
            reason = (
                f"Drawdown {dd['current_dd_pct']*100:.1f}% exceeds "
                f"threshold {self.max_drawdown*100:.1f}%. "
                f"Recommend reducing 50% of exposure."
            )
        else:
            # Scale between 0-30% reduction as drawdown approaches threshold
            progress = dd["current_dd_pct"] / self.max_drawdown
            target_reduction = (progress - 0.5) * 0.60  # 0% at 50%, 30% at 100%
            target_reduction = max(0.0, min(target_reduction, 0.30))
            reason = (
                f"Drawdown {dd['current_dd_pct']*100:.1f}% at "
                f"{progress*100:.0f}% of threshold. "
                f"Recommend reducing {target_reduction*100:.0f}% of exposure."
            )

        # Rank positions by PnL (worst first), then by concentration
        scored = []
        for p in positions:
            pnl = p.get("pnl_pct", 0.0)
            size = abs(p.get("size_usd", 0.0))
            # Lower score = close first (worse PnL, bigger size)
            score = pnl - (size / 10000.0)  # penalize large positions
            scored.append((score, p))
        scored.sort(key=lambda x: x[0])

        # Select positions to close to meet reduction target
        total_exposure = sum(abs(p.get("size_usd", 0.0)) for p in positions)
        target_cut = total_exposure * target_reduction
        to_close = []
        cut_so_far = 0.0

        for _, p in scored:
            if cut_so_far >= target_cut:
                break
            to_close.append(p.get("symbol", "UNKNOWN"))
            cut_so_far += abs(p.get("size_usd", 0.0))

        return {
            "should_reduce": True,
            "target_reduction_pct": round(target_reduction, 4),
            "reason": reason,
            "positions_to_close": to_close,
        }


# ---------------------------------------------------------------------------
# Quick sanity check when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    rm = PortfolioRiskManager()

    print("=== Portfolio Risk Manager ===\n")

    # Test with empty portfolio
    report = rm.generate_risk_report([], [10000, 9900, 9800], [], 10000)
    print(f"Empty portfolio status: {report['overall_status']}")
    print(f"  DD: {report['metrics']['drawdown']['current_dd_pct']*100:.1f}%")
    print(f"  Alerts: {report['alerts']}")

    # Test with positions
    positions = [
        {"symbol": "BTCUSDT", "size_usd": 5000, "direction": "LONG", "volatility": 0.60, "pnl_pct": -0.05},
        {"symbol": "ETHUSDT", "size_usd": 3000, "direction": "LONG", "volatility": 0.80, "pnl_pct": 0.02},
        {"symbol": "EURUSD", "size_usd": 2000, "direction": "SHORT", "volatility": 0.08, "pnl_pct": 0.01},
    ]
    report = rm.generate_risk_report(
        positions,
        [10000, 9900, 9800, 9700, 9500],
        [{"size_usd": 5000}, {"size_usd": 3000}],
        10000,
    )
    print(f"\n3-position portfolio status: {report['overall_status']}")
    print(f"  Leverage: {report['metrics']['leverage']['gross_leverage']:.2f}x")
    print(f"  Concentration HHI: {report['metrics']['concentration']['hhi_score']:.3f}")
    print(f"  VaR(95%): ${report['metrics']['portfolio_risk']['estimated_var_95']:,.2f}")
    print(f"  Alerts: {report['alerts']}")

    # Test check_new_trade
    signal = {"symbol": "SOLUSDT", "direction": "LONG", "size_usd": 4000}
    portfolio = {
        "positions": positions,
        "equity_curve": [10000, 9900, 9800],
        "trades_today": [{"size_usd": 2000}],
        "capital": 10000,
    }
    check = rm.check_new_trade(signal, portfolio)
    print(f"\nNew trade check (SOLUSDT $4k): allowed={check['allowed']}, "
          f"adjusted=${check['adjusted_size']:,.2f}, risk={check['risk_score']:.3f}")
    print(f"  Reason: {check['reason']}")
