"""
ValidationPipeline - Strategy Promotion Pipeline
================================================

Three-stage validation before strategies can enter production:
1. BACKTEST: Statistical validation (Sharpe, DSR, PSR)
2. PAPER: 30-day paper trading simulation
3. PROMOTION: Move to ml_battleground System F+

Gates at each stage prevent overfit/strategies from advancing.
"""

import os
import json
import sys
import shutil
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from incubator.shared_infra.sandbox import AgentSandbox
from incubator.shared_infra.fingerprinter import StrategyFingerprinter, StrategyFingerprint

logger = logging.getLogger(__name__)

# Paths
CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
THRESHOLDS_FILE = CONFIG_DIR / "resource_limits.json"
PROMOTION_TARGET = PROJECT_ROOT / "ml_battleground" / "system_f_incubator"


class ValidationStage(Enum):
    """Stages in validation pipeline."""
    BACKTEST = "backtest"
    PAPER = "paper_trading"
    PROMOTION = "promotion"
    REJECTED = "rejected"


class ValidationResult(Enum):
    """Outcome of validation."""
    PASS = "pass"
    FAIL = "fail"
    HOLD = "hold"  # Need more data


@dataclass
class ValidationReport:
    """Complete validation report for a strategy."""
    strategy_name: str
    agent_id: str
    stage: ValidationStage
    result: ValidationResult
    metrics: Dict
    timestamp: str
    reason: str
    next_stage: Optional[ValidationStage]


class ValidationPipeline:
    """
    Orchestrates strategy validation from creation to production.
    
    Usage:
        pipeline = ValidationPipeline()
        report = pipeline.validate_backtest(agent_id, strategy_name, backtest_results)
        if report.result == ValidationResult.PASS:
            pipeline.start_paper_trading(agent_id, strategy_name)
    """
    
    def __init__(self):
        self.thresholds = self._load_thresholds()
        self.fingerprinter = StrategyFingerprinter()
        self._ensure_promotion_target()
    
    def _load_thresholds(self) -> Dict:
        """Load validation thresholds."""
        with open(THRESHOLDS_FILE) as f:
            data = json.load(f)
            return data.get("validation_thresholds", {})
    
    def _ensure_promotion_target(self):
        """Ensure promotion target directory exists."""
        PROMOTION_TARGET.mkdir(parents=True, exist_ok=True)
    
    def validate_backtest(
        self,
        agent_id: str,
        strategy_name: str,
        backtest_results: Dict,
        strategy_code: str
    ) -> ValidationReport:
        """
        Stage 1: Validate backtest results.
        
        Checks:
        - Minimum Sharpe ratio
        - Maximum drawdown
        - Minimum win rate
        - DSR probability
        - Strategy uniqueness
        """
        logger.info(f"[Validation] Backtest validation for {agent_id}/{strategy_name}")
        
        failures = []
        metrics = backtest_results.get("metrics", backtest_results)
        
        # Check Sharpe
        sharpe = metrics.get("sharpe_ratio", metrics.get("sharpe", 0))
        if sharpe < self.thresholds.get("min_backtest_sharpe", 1.0):
            failures.append(f"Sharpe {sharpe:.2f} < {self.thresholds['min_backtest_sharpe']}")
        
        # Check drawdown
        drawdown = metrics.get("max_drawdown", 0)
        if drawdown > self.thresholds.get("max_backtest_drawdown", 0.20):
            failures.append(f"Drawdown {drawdown:.1%} > {self.thresholds['max_backtest_drawdown']}")
        
        # Check win rate
        win_rate = metrics.get("win_rate", 0)
        if win_rate < self.thresholds.get("min_backtest_win_rate", 0.45):
            failures.append(f"Win rate {win_rate:.1%} < {self.thresholds['min_backtest_win_rate']}")
        
        # Check DSR (Deflated Sharpe Ratio)
        dsr = metrics.get("dsr_probability", 0.5)
        if dsr < self.thresholds.get("min_dsr_probability", 0.75):
            failures.append(f"DSR {dsr:.2f} < {self.thresholds['min_dsr_probability']}")
        
        # Check uniqueness
        signals = backtest_results.get("trades", [])
        fingerprint = self.fingerprinter.compute_fingerprint(
            code=strategy_code,
            agent_id=agent_id,
            strategy_name=strategy_name,
            backtest_signals=signals
        )
        
        is_unique, similar = self.fingerprinter.check_uniqueness(
            fingerprint,
            threshold=self.thresholds.get("max_similarity_to_existing", 0.90)
        )
        
        if not is_unique:
            sim_info = similar[0]
            failures.append(
                f"Too similar to {sim_info['agent_id']}/{sim_info['strategy_name']} "
                f"(similarity: {sim_info['similarity']:.1%})"
            )
        
        # Determine result
        if failures:
            result = ValidationResult.FAIL
            next_stage = ValidationStage.REJECTED
            reason = "; ".join(failures)
        else:
            result = ValidationResult.PASS
            next_stage = ValidationStage.PAPER
            reason = "All backtest gates passed"
            
            # Register the strategy
            self.fingerprinter.register_strategy(fingerprint)
        
        report = ValidationReport(
            strategy_name=strategy_name,
            agent_id=agent_id,
            stage=ValidationStage.BACKTEST,
            result=result,
            metrics=metrics,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason=reason,
            next_stage=next_stage
        )
        
        self._save_report(agent_id, strategy_name, report)
        logger.info(f"[Validation] Result: {result.value} - {reason}")
        
        return report
    
    def start_paper_trading(
        self,
        agent_id: str,
        strategy_name: str,
        strategy_code: str
    ) -> ValidationReport:
        """
        Stage 2: Initialize paper trading.
        
        Creates paper trading configuration that runs alongside
        production without interfering.
        """
        logger.info(f"[Validation] Starting paper trading for {agent_id}/{strategy_name}")
        
        sandbox = AgentSandbox(agent_id)
        
        # Create paper trading config
        paper_config = {
            "strategy_name": strategy_name,
            "agent_id": agent_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "paper_trading",
            "required_days": self.thresholds.get("min_paper_trade_days", 30),
            "required_trades": self.thresholds.get("min_paper_trade_trades", 20),
            "simulated_capital": 10000,
            "code_path": str(sandbox.sandbox_dir / "strategy_code" / f"{strategy_name}.py"),
            "metrics": {
                "trades_today": 0,
                "total_trades": 0,
                "winning_trades": 0,
                "total_pnl": 0,
                "start_date": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Save paper trading config
        paper_dir = sandbox.sandbox_dir / "paper_trades"
        config_file = paper_dir / f"{strategy_name}_config.json"
        with open(config_file, 'w') as f:
            json.dump(paper_config, f, indent=2)
        
        report = ValidationReport(
            strategy_name=strategy_name,
            agent_id=agent_id,
            stage=ValidationStage.PAPER,
            result=ValidationResult.HOLD,
            metrics={"paper_config": paper_config},
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason="Paper trading initialized",
            next_stage=ValidationStage.PAPER  # Stays here until complete
        )
        
        self._save_report(agent_id, strategy_name, report)
        logger.info(f"[Validation] Paper trading config created")
        
        return report
    
    def check_paper_trading_complete(
        self,
        agent_id: str,
        strategy_name: str
    ) -> ValidationReport:
        """
        Check if paper trading period is complete and valid.
        """
        sandbox = AgentSandbox(agent_id)
        config_file = sandbox.sandbox_dir / "paper_trades" / f"{strategy_name}_config.json"
        
        if not config_file.exists():
            return ValidationReport(
                strategy_name=strategy_name,
                agent_id=agent_id,
                stage=ValidationStage.PAPER,
                result=ValidationResult.FAIL,
                metrics={},
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason="Paper trading config not found",
                next_stage=ValidationStage.REJECTED
            )
        
        with open(config_file) as f:
            config = json.load(f)
        
        metrics = config.get("metrics", {})
        start_date = datetime.fromisoformat(config["start_date"])
        days_running = (datetime.now(timezone.utc) - start_date).days
        total_trades = metrics.get("total_trades", 0)
        
        # Check completion criteria
        if days_running < config["required_days"]:
            return ValidationReport(
                strategy_name=strategy_name,
                agent_id=agent_id,
                stage=ValidationStage.PAPER,
                result=ValidationResult.HOLD,
                metrics=metrics,
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason=f"Paper trading in progress: {days_running}/{config['required_days']} days",
                next_stage=ValidationStage.PAPER
            )
        
        if total_trades < config["required_trades"]:
            return ValidationReport(
                strategy_name=strategy_name,
                agent_id=agent_id,
                stage=ValidationStage.PAPER,
                result=ValidationResult.HOLD,
                metrics=metrics,
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason=f"Insufficient trades: {total_trades}/{config['required_trades']}",
                next_stage=ValidationStage.PAPER
            )
        
        # Calculate paper trading performance
        total_pnl = metrics.get("total_pnl", 0)
        winning_trades = metrics.get("winning_trades", 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Simple check: positive P&L and reasonable win rate
        if total_pnl <= 0:
            return ValidationReport(
                strategy_name=strategy_name,
                agent_id=agent_id,
                stage=ValidationStage.PAPER,
                result=ValidationResult.FAIL,
                metrics=metrics,
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason=f"Negative P&L in paper trading: {total_pnl:.2f}%",
                next_stage=ValidationStage.REJECTED
            )
        
        if win_rate < 0.40:
            return ValidationReport(
                strategy_name=strategy_name,
                agent_id=agent_id,
                stage=ValidationStage.PAPER,
                result=ValidationResult.FAIL,
                metrics=metrics,
                timestamp=datetime.now(timezone.utc).isoformat(),
                reason=f"Low win rate in paper trading: {win_rate:.1%}",
                next_stage=ValidationStage.REJECTED
            )
        
        # All checks passed - ready for promotion
        report = ValidationReport(
            strategy_name=strategy_name,
            agent_id=agent_id,
            stage=ValidationStage.PAPER,
            result=ValidationResult.PASS,
            metrics=metrics,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason=f"Paper trading complete: {total_trades} trades, {win_rate:.1%} WR, {total_pnl:+.2f}% P&L",
            next_stage=ValidationStage.PROMOTION
        )
        
        self._save_report(agent_id, strategy_name, report)
        return report
    
    def promote_to_production(
        self,
        agent_id: str,
        strategy_name: str
    ) -> ValidationReport:
        """
        Stage 3: Promote strategy to production (System F+).
        """
        logger.info(f"[Validation] Promoting {agent_id}/{strategy_name} to production")
        
        sandbox = AgentSandbox(agent_id)
        
        # Copy strategy to production
        source_code = sandbox.sandbox_dir / "strategy_code" / f"{strategy_name}.py"
        target_dir = PROMOTION_TARGET / "strategies"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Rename with agent prefix to track origin
        target_name = f"{agent_id}_{strategy_name}.py"
        target_path = target_dir / target_name
        
        shutil.copy2(source_code, target_path)
        
        # Copy metadata
        meta_source = Path(str(source_code) + '.meta.json')
        if meta_source.exists():
            meta = json.load(open(meta_source))
            meta["promoted_at"] = datetime.now(timezone.utc).isoformat()
            meta["original_agent"] = agent_id
            meta["validation_history"] = self._load_validation_history(agent_id, strategy_name)
            
            with open(target_dir / f"{target_name}.meta.json", 'w') as f:
                json.dump(meta, f, indent=2)
        
        # Archive sandbox
        sandbox.archive(reason="promoted")
        
        report = ValidationReport(
            strategy_name=strategy_name,
            agent_id=agent_id,
            stage=ValidationStage.PROMOTION,
            result=ValidationResult.PASS,
            metrics={"promoted_to": str(target_path)},
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason=f"Promoted to {PROMOTION_TARGET.name}/{target_name}",
            next_stage=None
        )
        
        self._save_report(agent_id, strategy_name, report)
        logger.info(f"[Validation] Successfully promoted to {target_path}")
        
        return report
    
    def _save_report(self, agent_id: str, strategy_name: str, report: ValidationReport):
        """Save validation report to disk."""
        sandbox = AgentSandbox(agent_id)
        reports_dir = sandbox.sandbox_dir / "metrics" / "validation_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = reports_dir / f"{strategy_name}_{report.stage.value}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "strategy_name": report.strategy_name,
                "agent_id": report.agent_id,
                "stage": report.stage.value,
                "result": report.result.value,
                "metrics": report.metrics,
                "timestamp": report.timestamp,
                "reason": report.reason,
                "next_stage": report.next_stage.value if report.next_stage else None
            }, f, indent=2)
    
    def _load_validation_history(self, agent_id: str, strategy_name: str) -> List[Dict]:
        """Load all validation reports for a strategy."""
        sandbox = AgentSandbox(agent_id)
        reports_dir = sandbox.sandbox_dir / "metrics" / "validation_reports"
        
        history = []
        if reports_dir.exists():
            for f in reports_dir.glob(f"{strategy_name}_*.json"):
                with open(f) as fp:
                    history.append(json.load(fp))
        
        return sorted(history, key=lambda x: x["timestamp"])
    
    def run_full_pipeline(
        self,
        agent_id: str,
        strategy_name: str,
        strategy_code: str,
        backtest_results: Dict
    ) -> ValidationReport:
        """
        Run complete validation pipeline.
        
        This is the main entry point for new strategies.
        """
        # Stage 1: Backtest
        report = self.validate_backtest(agent_id, strategy_name, backtest_results, strategy_code)
        
        if report.result == ValidationResult.PASS:
            # Stage 2: Start paper trading
            report = self.start_paper_trading(agent_id, strategy_name, strategy_code)
            
            # Note: Stage 3 (promotion) happens after paper trading period
            logger.info(f"[Validation] Strategy ready for paper trading")
        
        return report
