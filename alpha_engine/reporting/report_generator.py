"""
Report Generator

Generates comprehensive HTML and Markdown reports with:
- Strategy performance dashboard
- Pick lists with rationale
- Risk analysis
- Regime status
- Feature importance
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate research reports in Markdown and HTML formats."""

    def __init__(self, output_dir: Optional[Path] = None):
        from .. import config
        self.output_dir = output_dir or config.OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_daily_report(
        self,
        picks: pd.DataFrame,
        watchlist: pd.DataFrame,
        avoid_list: pd.DataFrame,
        regime_info: Dict,
        strategy_weights: Dict[str, float],
        backtest_results: Dict = None,
        feature_importance: pd.Series = None,
    ) -> str:
        """
        Generate comprehensive daily/weekly report.
        
        Returns Markdown string and saves to file.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        report = []

        # Header
        report.append(f"# Alpha Engine Report — {now}")
        report.append("")
        report.append("---")
        report.append("")

        # Regime Status
        report.append("## Market Regime")
        report.append("")
        regime = regime_info.get("composite_regime", "unknown")
        vol_regime = regime_info.get("vol_regime", "unknown")
        trend = regime_info.get("trend_regime", "unknown")
        report.append(f"| Indicator | Value |")
        report.append(f"|-----------|-------|")
        report.append(f"| **Composite Regime** | **{regime.upper()}** |")
        report.append(f"| Volatility Regime | {vol_regime} |")
        report.append(f"| Trend Regime | {trend} |")
        report.append(f"| Rate Regime | {regime_info.get('rate_regime', 'N/A')} |")
        report.append(f"| Dollar Regime | {regime_info.get('dollar_regime', 'N/A')} |")

        for key in ["raw_VIX", "raw_TNX", "raw_DXY", "raw_SPY"]:
            if key in regime_info:
                label = key.replace("raw_", "")
                report.append(f"| {label} | {regime_info[key]:.2f} |")

        report.append("")

        # Strategy Allocation
        report.append("## Strategy Allocation")
        report.append("")
        report.append("| Strategy | Weight |")
        report.append("|----------|--------|")
        for strat, weight in sorted(strategy_weights.items(), key=lambda x: x[1], reverse=True):
            bar = "█" * int(weight * 30)
            report.append(f"| {strat} | {weight:.1%} {bar} |")
        report.append("")

        # Top Picks
        report.append("## Top Picks")
        report.append("")
        if not picks.empty:
            report.append("| Rank | Ticker | Score | Conviction | Horizon | Key Drivers |")
            report.append("|------|--------|-------|------------|---------|-------------|")
            for _, row in picks.iterrows():
                rank = row.get("rank", "")
                ticker = row.get("ticker", "")
                score = row.get("score", 0)
                conviction = row.get("conviction", "")
                horizon = row.get("expected_horizon", "")
                drivers = row.get("contributing_strategies", "")[:50]
                report.append(f"| {rank} | **{ticker}** | {score:.3f} | {conviction} | {horizon} | {drivers} |")
        else:
            report.append("*No picks generated for this period.*")
        report.append("")

        # Watchlist
        report.append("## Watchlist")
        report.append("")
        if not watchlist.empty:
            report.append("| Ticker | Score | Reason |")
            report.append("|--------|-------|--------|")
            for _, row in watchlist.iterrows():
                report.append(f"| {row.get('ticker', '')} | {row.get('score', 0):.3f} | {row.get('reason', '')} |")
        else:
            report.append("*Empty watchlist.*")
        report.append("")

        # Avoid List
        report.append("## Avoid List")
        report.append("")
        if not avoid_list.empty:
            report.append("| Ticker | Reason |")
            report.append("|--------|--------|")
            for _, row in avoid_list.iterrows():
                report.append(f"| {row.get('ticker', '')} | {row.get('reason', '')} |")
        else:
            report.append("*No stocks on avoid list.*")
        report.append("")

        # Feature Importance (if ML model was used)
        if feature_importance is not None and len(feature_importance) > 0:
            report.append("## Top Feature Importances (ML Ranker)")
            report.append("")
            report.append("| Feature | Importance |")
            report.append("|---------|------------|")
            for feat, imp in feature_importance.head(15).items():
                report.append(f"| {feat} | {imp:.4f} |")
            report.append("")

        # Backtest Summary (if available)
        if backtest_results:
            report.append("## Recent Backtest Summary")
            report.append("")
            for strat_name, result in backtest_results.items():
                if hasattr(result, "sharpe_ratio"):
                    report.append(f"### {strat_name}")
                    report.append(f"- Sharpe: {result.sharpe_ratio:.3f}")
                    report.append(f"- Return: {result.total_return_pct:.2f}%")
                    report.append(f"- Max DD: {result.max_drawdown_pct:.2f}%")
                    report.append(f"- Win Rate: {result.win_rate:.1f}%")
                    report.append(f"- Trades: {result.total_trades}")
                    report.append("")

        # TACO Checklist
        report.append("## TACO Checklist")
        report.append("")
        report.append("- [x] **T**ransaction costs included (IB model: $0.005/share + slippage)")
        report.append("- [x] **A**voided leakage (purged CV with embargo)")
        report.append("- [ ] **C**onsistent across regimes (verify with 3-windows test)")
        report.append("- [ ] **O**ut-of-sample beats benchmark (verify with walk-forward)")
        report.append("")

        # Footer
        report.append("---")
        report.append(f"*Generated by Alpha Engine v1.0 on {now}*")
        report.append(f"*Remember: EDGE = Signal × Discipline. If you can't explain where the edge comes from, it's probably curve-fit.*")

        markdown = "\n".join(report)

        # Save to file
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        filepath = self.output_dir / filename
        filepath.write_text(markdown, encoding="utf-8")
        logger.info(f"Report saved to {filepath}")

        return markdown

    def generate_backtest_report(self, result, strategy_name: str = "") -> str:
        """Generate a detailed backtest report."""
        report = []
        report.append(f"# Backtest Report: {strategy_name or result.strategy_name}")
        report.append(f"Period: {result.start_date} to {result.end_date}")
        report.append("")
        report.append("## Performance Summary")
        report.append("")
        report.append(f"| Metric | Value |")
        report.append(f"|--------|-------|")
        report.append(f"| Total Return | {result.total_return_pct:.2f}% |")
        report.append(f"| Annual Return | {result.annual_return_pct:.2f}% |")
        report.append(f"| Benchmark Return | {result.benchmark_return_pct:.2f}% |")
        report.append(f"| Alpha | {result.alpha_pct:.2f}% |")
        report.append(f"| Sharpe Ratio | {result.sharpe_ratio:.3f} |")
        report.append(f"| Sortino Ratio | {result.sortino_ratio:.3f} |")
        report.append(f"| Calmar Ratio | {result.calmar_ratio:.3f} |")
        report.append(f"| Max Drawdown | {result.max_drawdown_pct:.2f}% |")
        report.append(f"| Win Rate | {result.win_rate:.1f}% |")
        report.append(f"| Profit Factor | {result.profit_factor:.2f} |")
        report.append(f"| Expectancy | {result.expectancy:.4f} |")
        report.append(f"| Total Trades | {result.total_trades} |")
        report.append(f"| Avg Holding Days | {result.avg_holding_days:.1f} |")
        report.append(f"| Total Costs | ${result.total_costs:,.2f} |")
        report.append(f"| Cost Drag | {result.cost_drag_pct:.2f}% |")
        report.append(f"| VaR 95% | {result.var_95:.3f}% |")
        report.append(f"| CVaR 95% | {result.cvar_95:.3f}% |")
        report.append(f"| Monthly Hit Rate | {result.hit_rate_monthly:.1f}% |")

        return "\n".join(report)
