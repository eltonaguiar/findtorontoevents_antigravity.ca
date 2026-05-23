#!/usr/bin/env python3
"""
Permutation Portfolio Analyzer - Analyzes which systems/strategies can be trusted.

Generates reports comparing:
- Solo systems vs combinations
- Strategy categories and confluence levels
- Performance by agreement count
- Best and worst performing combinations

Usage:
    python -m paper_trading.permutation_analyzer --report full
    python -m paper_trading.permutation_analyzer --report systems
    python -m paper_trading.permutation_analyzer --report strategies
    python -m paper_trading.permutation_analyzer --export-html
"""
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict

from paper_trading.db import DB_PATH

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).parent / "data"


@dataclass
class PortfolioStats:
    id: str
    name: str
    portfolio_type: str  # 'system' or 'strategy'
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    pnl_pct: float
    max_drawdown: float
    profit_factor: float = 0.0
    expectancy: float = 0.0
    avg_trade: float = 0.0
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.portfolio_type,
            "trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.win_rate,
            "pnl_pct": self.pnl_pct,
            "max_drawdown": self.max_drawdown,
            "profit_factor": self.profit_factor,
            "expectancy": self.expectancy,
            "avg_trade": self.avg_trade,
            "trust_score": self.calculate_trust_score()
        }
    
    def calculate_trust_score(self) -> float:
        """Calculate a trust score (0-100) based on multiple factors."""
        if self.total_trades < 10:
            return 0  # Insufficient data
        
        score = 0
        # Win rate component (max 40 points)
        score += min(40, self.win_rate * 0.4)
        
        # PnL component (max 30 points)
        score += min(30, max(0, self.pnl_pct * 1.5))
        
        # Sample size component (max 20 points)
        score += min(20, self.total_trades * 0.2)
        
        # Drawdown penalty
        score -= self.max_drawdown * 0.5
        
        return round(max(0, min(100, score)), 1)


class PermutationAnalyzer:
    """Analyzes permutation portfolio performance."""
    
    def __init__(self):
        self.conn = sqlite3.connect(str(DB_PATH))
        self.conn.row_factory = sqlite3.Row
        self.stats: Dict[str, PortfolioStats] = {}
        self.system_stats: Dict[str, PortfolioStats] = {}
        self.strategy_stats: Dict[str, PortfolioStats] = {}
        
    def load_stats(self):
        """Load statistics from database."""
        rows = self.conn.execute("""
            SELECT * FROM permutation_portfolios 
            WHERE total_trades > 0
            ORDER BY (wins * 1.0 / total_trades) DESC
        """).fetchall()
        
        for row in rows:
            # Calculate derived metrics
            total_trades = row["total_trades"]
            wins = row["wins"]
            losses = row["losses"]
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            # Get closed positions for PF calculation
            positions = self.conn.execute("""
                SELECT pnl_pct FROM permutation_positions 
                WHERE portfolio_id=? AND status='CLOSED'
            """, (row["id"],)).fetchall()
            
            win_pnl = sum(p["pnl_pct"] for p in positions if p["pnl_pct"] > 0)
            loss_pnl = abs(sum(p["pnl_pct"] for p in positions if p["pnl_pct"] < 0))
            profit_factor = round(win_pnl / loss_pnl, 2) if loss_pnl > 0 else 0
            
            avg_win = win_pnl / wins if wins > 0 else 0
            avg_loss = loss_pnl / losses if losses > 0 else 0
            expectancy = round((win_rate/100 * avg_win) - ((1-win_rate/100) * avg_loss), 2)
            avg_trade = sum(p["pnl_pct"] for p in positions) / len(positions) if positions else 0
            
            stats = PortfolioStats(
                id=row["id"],
                name=row["name"],
                portfolio_type=row["portfolio_type"],
                total_trades=total_trades,
                wins=wins,
                losses=losses,
                win_rate=round(win_rate, 1),
                pnl_pct=round(((row["equity"] - 10000) / 10000 * 100), 2),
                max_drawdown=row["max_drawdown_pct"],
                profit_factor=profit_factor,
                expectancy=expectancy,
                avg_trade=round(avg_trade, 2)
            )
            
            self.stats[row["id"]] = stats
            if row["portfolio_type"] == "system":
                self.system_stats[row["id"]] = stats
            else:
                self.strategy_stats[row["id"]] = stats
    
    def analyze_system_permutations(self) -> dict:
        """Analyze which system combinations work best."""
        results = {
            "solo_performance": [],
            "pair_performance": [],
            "triplet_performance": [],
            "consensus_performance": [],
            "best_combinations": [],
            "worst_combinations": [],
            "agreement_analysis": defaultdict(list)
        }
        
        for pf_id, stats in self.system_stats.items():
            if "solo_" in pf_id:
                results["solo_performance"].append(stats.to_dict())
            elif "pair_" in pf_id:
                results["pair_performance"].append(stats.to_dict())
            elif "triple_" in pf_id:
                results["triplet_performance"].append(stats.to_dict())
            elif "flex_" in pf_id or "conf_" in pf_id:
                results["consensus_performance"].append(stats.to_dict())
            elif "hp_" in pf_id:
                results["agreement_analysis"]["high_performance"].append(stats.to_dict())
            elif "ml_" in pf_id:
                results["agreement_analysis"]["ml_based"].append(stats.to_dict())
            elif "rf_" in pf_id:
                results["agreement_analysis"]["rapid_fire"].append(stats.to_dict())
        
        # Sort by trust score
        all_systems = list(self.system_stats.values())
        all_systems.sort(key=lambda x: x.calculate_trust_score(), reverse=True)
        
        results["best_combinations"] = [s.to_dict() for s in all_systems[:5]]
        results["worst_combinations"] = [s.to_dict() for s in all_systems[-5:]]
        
        # Compare solo vs pairs vs triplets
        if results["solo_performance"] and results["pair_performance"]:
            solo_avg_wr = sum(s["win_rate"] for s in results["solo_performance"]) / len(results["solo_performance"])
            pair_avg_wr = sum(s["win_rate"] for s in results["pair_performance"]) / len(results["pair_performance"])
            results["comparison"] = {
                "solo_avg_win_rate": round(solo_avg_wr, 1),
                "pair_avg_win_rate": round(pair_avg_wr, 1),
                "improvement_from_pairs": round(pair_avg_wr - solo_avg_wr, 1)
            }
        
        return results
    
    def analyze_strategy_combinations(self) -> dict:
        """Analyze which strategy combinations work best."""
        results = {
            "solo_performance": [],
            "confluence_performance": [],
            "category_performance": [],
            "tier_performance": [],
            "champion_performance": [],
            "hoffman_performance": [],
            "prop_firm_performance": [],
            "kimi_ml_performance": [],
            "best_combinations": [],
            "worst_combinations": []
        }
        
        for pf_id, stats in self.strategy_stats.items():
            if "solo_" in pf_id:
                results["solo_performance"].append(stats.to_dict())
            elif "conf_" in pf_id:
                results["confluence_performance"].append(stats.to_dict())
            elif "cat_" in pf_id:
                results["category_performance"].append(stats.to_dict())
            elif "tier" in pf_id:
                results["tier_performance"].append(stats.to_dict())
            elif "champ_" in pf_id:
                results["champion_performance"].append(stats.to_dict())
            elif "hoff_" in pf_id:
                results["hoffman_performance"].append(stats.to_dict())
            elif "prop_" in pf_id:
                results["prop_firm_performance"].append(stats.to_dict())
            elif "kimi_" in pf_id:
                results["kimi_ml_performance"].append(stats.to_dict())
        
        # Sort by trust score
        all_strategies = list(self.strategy_stats.values())
        all_strategies.sort(key=lambda x: x.calculate_trust_score(), reverse=True)
        
        results["best_combinations"] = [s.to_dict() for s in all_strategies[:10]]
        results["worst_combinations"] = [s.to_dict() for s in all_strategies[-10:]]
        
        # Compare solo vs confluence
        if results["solo_performance"] and results["confluence_performance"]:
            solo_avg_wr = sum(s["win_rate"] for s in results["solo_performance"]) / len(results["solo_performance"])
            conf_avg_wr = sum(s["win_rate"] for s in results["confluence_performance"]) / len(results["confluence_performance"])
            results["confluence_comparison"] = {
                "solo_avg_win_rate": round(solo_avg_wr, 1),
                "confluence_avg_win_rate": round(conf_avg_wr, 1),
                "confluence_benefit": round(conf_avg_wr - solo_avg_wr, 1)
            }
        
        return results
    
    def generate_trust_rankings(self) -> dict:
        """Generate trust rankings for all portfolios."""
        all_stats = list(self.stats.values())
        all_stats.sort(key=lambda x: x.calculate_trust_score(), reverse=True)
        
        tiers = {
            "tier_1_highly_trusted": [],  # Trust score 70+
            "tier_2_trusted": [],         # Trust score 50-69
            "tier_3_promising": [],       # Trust score 30-49
            "tier_4_unproven": [],        # Trust score < 30
            "tier_5_untrustworthy": []    # Negative PnL or WR < 40%
        }
        
        for stats in all_stats:
            score = stats.calculate_trust_score()
            data = stats.to_dict()
            
            if stats.pnl_pct < 0 or stats.win_rate < 40:
                tiers["tier_5_untrustworthy"].append(data)
            elif score >= 70:
                tiers["tier_1_highly_trusted"].append(data)
            elif score >= 50:
                tiers["tier_2_trusted"].append(data)
            elif score >= 30:
                tiers["tier_3_promising"].append(data)
            else:
                tiers["tier_4_unproven"].append(data)
        
        return tiers
    
    def generate_recommendations(self) -> List[dict]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Analyze solo vs combination performance
        solo_wr = []
        combo_wr = []
        
        for pf_id, stats in self.system_stats.items():
            if "solo_" in pf_id:
                solo_wr.append(stats.win_rate)
            else:
                combo_wr.append(stats.win_rate)
        
        if solo_wr and combo_wr:
            avg_solo = sum(solo_wr) / len(solo_wr)
            avg_combo = sum(combo_wr) / len(combo_wr)
            
            if avg_combo > avg_solo + 5:
                recommendations.append({
                    "type": "system_combination",
                    "priority": "high",
                    "recommendation": "System combinations outperform solo systems",
                    "detail": f"Combinations avg {avg_combo:.1f}% WR vs solo {avg_solo:.1f}% WR",
                    "action": "Focus on multi-system agreement strategies"
                })
        
        # Find best single system
        best_solo = None
        for pf_id, stats in self.system_stats.items():
            if "solo_" in pf_id:
                if not best_solo or stats.win_rate > best_solo.win_rate:
                    best_solo = stats
        
        if best_solo:
            recommendations.append({
                "type": "best_solo_system",
                "priority": "high",
                "recommendation": f"Best performing solo system: {best_solo.name}",
                "detail": f"Win rate: {best_solo.win_rate}%, PnL: {best_solo.pnl_pct}%",
                "action": f"Consider {best_solo.id} as baseline for comparisons"
            })
        
        # Find best combination
        best_combo = max(self.stats.values(), key=lambda x: x.calculate_trust_score()) if self.stats else None
        if best_combo:
            recommendations.append({
                "type": "best_combination",
                "priority": "high",
                "recommendation": f"Most trusted combination: {best_combo.name}",
                "detail": f"Trust score: {best_combo.calculate_trust_score()}/100, WR: {best_combo.win_rate}%",
                "action": "Increase allocation to this combination"
            })
        
        # Find worst performers to avoid
        worst = sorted(self.stats.values(), key=lambda x: x.calculate_trust_score())[:3]
        if worst:
            recommendations.append({
                "type": "avoid",
                "priority": "medium",
                "recommendation": "Avoid these underperforming combinations",
                "detail": ", ".join([f"{w.name} ({w.win_rate}% WR)" for w in worst]),
                "action": "Reduce or eliminate allocation"
            })
        
        return recommendations
    
    def generate_full_report(self) -> dict:
        """Generate complete analysis report."""
        self.load_stats()
        
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_portfolios": len(self.stats),
                "system_portfolios": len(self.system_stats),
                "strategy_portfolios": len(self.strategy_stats),
                "total_trades": sum(s.total_trades for s in self.stats.values()),
                "avg_win_rate": round(sum(s.win_rate for s in self.stats.values()) / len(self.stats), 1) if self.stats else 0
            },
            "system_analysis": self.analyze_system_permutations(),
            "strategy_analysis": self.analyze_strategy_combinations(),
            "trust_rankings": self.generate_trust_rankings(),
            "recommendations": self.generate_recommendations()
        }
        
        return report
    
    def export_html_report(self, report: dict, output_path: Optional[Path] = None):
        """Export report as HTML dashboard."""
        if output_path is None:
            output_path = DATA_DIR / "permutation_report.html"
        
        html = self._generate_html(report)
        output_path.write_text(html)
        print(f"HTML report exported to {output_path}")
    
    def _generate_html(self, report: dict) -> str:
        """Generate HTML report."""
        # Build rankings tables
        trust_tiers = report["trust_rankings"]
        
        def build_table(data: list, columns: list) -> str:
            if not data:
                return "<p>No data available</p>"
            
            html = '<table class="data-table"><thead><tr>'
            for col in columns:
                html += f'<th>{col}</th>'
            html += '</tr></thead><tbody>'
            
            for row in data:
                html += '<tr>'
                for col in columns:
                    val = row.get(col.lower().replace(' ', '_'), '-')
                    html += f'<td>{val}</td>'
                html += '</tr>'
            html += '</tbody></table>'
            return html
        
        recommendations_html = '<div class="recommendations">'
        for rec in report["recommendations"]:
            recommendations_html += f'''
                <div class="rec-box {rec["priority"]}">
                    <h4>{rec["recommendation"]}</h4>
                    <p>{rec["detail"]}</p>
                    <p><strong>Action:</strong> {rec["action"]}</p>
                </div>
            '''
        recommendations_html += '</div>'
        
        html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Permutation Portfolio Analysis Report</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; background: #0a0a12; color: #e0e0e0; }}
        h1, h2, h3 {{ color: #a78bfa; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #1a1a2e; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-card .value {{ font-size: 32px; font-weight: bold; color: #4caf50; }}
        .stat-card .label {{ color: #888; font-size: 14px; margin-top: 8px; }}
        .data-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }}
        .data-table th {{ background: #0f1628; padding: 12px; text-align: left; text-transform: uppercase; font-size: 12px; color: #888; }}
        .data-table td {{ padding: 10px 12px; border-bottom: 1px solid #2a2a4a; }}
        .data-table tr:hover {{ background: #1f1f3a; }}
        .tier-1 {{ border-left: 4px solid #4caf50; }}
        .tier-2 {{ border-left: 4px solid #60a5fa; }}
        .tier-3 {{ border-left: 4px solid #f59e0b; }}
        .tier-4 {{ border-left: 4px solid #888; }}
        .tier-5 {{ border-left: 4px solid #f44336; }}
        .rec-box {{ background: #1a1a2e; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #60a5fa; }}
        .rec-box.high {{ border-color: #f44336; }}
        .rec-box.medium {{ border-color: #f59e0b; }}
        .positive {{ color: #4caf50; }}
        .negative {{ color: #f44336; }}
        .section {{ margin: 40px 0; }}
    </style>
</head>
<body>
    <h1>🎯 Permutation Portfolio Analysis Report</h1>
    <p>Generated: {report["generated_at"][:19]}</p>
    
    <div class="summary">
        <div class="stat-card">
            <div class="value">{report["summary"]["total_portfolios"]}</div>
            <div class="label">Total Portfolios</div>
        </div>
        <div class="stat-card">
            <div class="value">{report["summary"]["system_portfolios"]}</div>
            <div class="label">System Portfolios</div>
        </div>
        <div class="stat-card">
            <div class="value">{report["summary"]["strategy_portfolios"]}</div>
            <div class="label">Strategy Portfolios</div>
        </div>
        <div class="stat-card">
            <div class="value">{report["summary"]["total_trades"]}</div>
            <div class="label">Total Trades</div>
        </div>
        <div class="stat-card">
            <div class="value">{report["summary"]["avg_win_rate"]}%</div>
            <div class="label">Avg Win Rate</div>
        </div>
    </div>
    
    <div class="section">
        <h2>🎯 Key Recommendations</h2>
        {recommendations_html}
    </div>
    
    <div class="section">
        <h2>⭐ Tier 1 - Highly Trusted (Score 70+)</h2>
        {build_table(trust_tiers["tier_1_highly_trusted"], ["Name", "Trades", "Win Rate", "PnL %", "Trust Score"])}
    </div>
    
    <div class="section">
        <h2>✅ Tier 2 - Trusted (Score 50-69)</h2>
        {build_table(trust_tiers["tier_2_trusted"], ["Name", "Trades", "Win Rate", "PnL %", "Trust Score"])}
    </div>
    
    <div class="section">
        <h2>📊 Best System Combinations</h2>
        {build_table(report["system_analysis"]["best_combinations"], ["Name", "Trades", "Win Rate", "PnL %", "Trust Score"])}
    </div>
    
    <div class="section">
        <h2>📈 Best Strategy Combinations</h2>
        {build_table(report["strategy_analysis"]["best_combinations"], ["Name", "Trades", "Win Rate", "PnL %", "Trust Score"])}
    </div>
    
    <div class="section">
        <h2>⚠️ Underperforming - Avoid</h2>
        {build_table(report["trust_rankings"]["tier_5_untrustworthy"], ["Name", "Trades", "Win Rate", "PnL %", "Trust Score"])}
    </div>
</body>
</html>'''
        return html


def main():
    parser = argparse.ArgumentParser(description="Permutation Portfolio Analyzer")
    parser.add_argument("--report", choices=["full", "systems", "strategies", "trust"], default="full")
    parser.add_argument("--export-html", action="store_true", help="Export HTML report")
    parser.add_argument("--export-json", type=str, help="Export JSON report to file")
    
    args = parser.parse_args()
    
    analyzer = PermutationAnalyzer()
    analyzer.load_stats()
    
    if args.report == "full":
        report = analyzer.generate_full_report()
        print(json.dumps(report, indent=2))
    elif args.report == "systems":
        results = analyzer.analyze_system_permutations()
        print(json.dumps(results, indent=2))
    elif args.report == "strategies":
        results = analyzer.analyze_strategy_combinations()
        print(json.dumps(results, indent=2))
    elif args.report == "trust":
        results = analyzer.generate_trust_rankings()
        print(json.dumps(results, indent=2))
    
    if args.export_html:
        report = analyzer.generate_full_report()
        analyzer.export_html_report(report)
    
    if args.export_json:
        report = analyzer.generate_full_report()
        Path(args.export_json).write_text(json.dumps(report, indent=2))
        print(f"Report exported to {args.export_json}")


if __name__ == "__main__":
    main()
