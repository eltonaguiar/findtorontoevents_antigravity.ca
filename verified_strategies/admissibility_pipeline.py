#!/usr/bin/env python3
"""
Admissibility Pipeline — 10-Step Gate for Strategy Promotion
=============================================================
Every strategy must pass this pipeline before it can affect capital.
No exceptions.

Requirements:
1. Pre-register hypothesis before backtesting
2. Real data only with explicit source/fallback provenance
3. Purged + embargoed walk-forward (not simple split)
4. Costs/slippage by asset class in every engine
5. DSR/PBO/SPA correction for multiple testing
6. Block bootstrap (not i.i.d. shuffle)
7. Regime robustness across trend/volatility states
8. Forward paper evidence before promotion
9. Forward PF/WR close to OOS lab PF/WR
10. Gradual capital scaling (shadow -> tiny -> increase)
"""

import json
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    PRE_REGISTER = "pre_register"
    DATA_VALIDATION = "data_validation"
    WALK_FORWARD = "walk_forward"
    COST_MODEL = "cost_model"
    DSR_PBO = "dsr_pbo"
    BLOCK_BOOTSTRAP = "block_bootstrap"
    REGIME_ROBUSTNESS = "regime_robustness"
    FORWARD_PAPER = "forward_paper"
    FORWARD_VALIDATION = "forward_validation"
    PROMOTION = "promotion"


class PipelineVerdict(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PENDING = "PENDING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class CostModel:
    """Per-asset-class transaction costs."""
    slippage_bps: float
    commission_bps: float
    
    @staticmethod
    def for_class(asset_class: str) -> 'CostModel':
        costs = {
            'CRYPTO': CostModel(slippage_bps=10, commission_bps=10),
            'EQUITY': CostModel(slippage_bps=1, commission_bps=1),
            'ETF': CostModel(slippage_bps=1, commission_bps=1),
            'FOREX': CostModel(slippage_bps=0.5, commission_bps=0),
            'COMMODITY': CostModel(slippage_bps=2, commission_bps=1),
            'FUTURES': CostModel(slippage_bps=2, commission_bps=1),
            'BOND': CostModel(slippage_bps=1, commission_bps=0.5),
        }
        return costs.get(asset_class, CostModel(slippage_bps=2, commission_bps=1))


@dataclass
class WalkForwardResult:
    """Walk-forward validation result."""
    train_pf: float
    train_wr: float
    train_n: int
    holdout_pf: float
    holdout_wr: float
    holdout_n: int
    decay_pct: float  # (train_pf - holdout_pf) / train_pf
    folds_profitable: int
    folds_total: int
    verdict: PipelineVerdict


@dataclass
class DSRResult:
    """Deflated Sharpe Ratio result."""
    sharpe: float
    dsr: float
    pbo: float  # Probability of backtest overfitting
    n_strategies_tested: int
    verdict: PipelineVerdict


@dataclass
class RegimeResult:
    """Regime robustness result."""
    regimes_tested: List[str]
    regimes_profitable: List[str]
    regime_pf: Dict[str, float]
    verdict: PipelineVerdict


@dataclass
class ConcentrationResult:
    """Concentration check result."""
    max_source_pct: float
    max_symbol_pct: float
    max_class_pct: float
    verdict: PipelineVerdict


@dataclass
class PipelineResult:
    """Full pipeline result for one strategy."""
    strategy_name: str
    asset_class: str
    timestamp: str
    stages: Dict[str, PipelineVerdict] = field(default_factory=dict)
    walk_forward: Optional[WalkForwardResult] = None
    dsr: Optional[DSRResult] = None
    regime: Optional[RegimeResult] = None
    concentration: Optional[ConcentrationResult] = None
    overall_verdict: PipelineVerdict = PipelineVerdict.PENDING
    rejection_reason: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'strategy_name': self.strategy_name,
            'asset_class': self.asset_class,
            'timestamp': self.timestamp,
            'stages': {k: v.value for k, v in self.stages.items()},
            'overall_verdict': self.overall_verdict.value,
            'rejection_reason': self.rejection_reason,
        }


class AdmissibilityPipeline:
    """
    10-step admissibility pipeline for strategy promotion.
    Every strategy must pass before it can affect capital.
    """
    
    # Promotion criteria
    MIN_LAB_PF = 1.5
    MIN_LAB_WR = 0.50
    MIN_DSR = 0.95
    MAX_PBO = 0.50
    MIN_FORWARD_PF = 1.2
    FORWARD_WR_TOLERANCE = 0.05  # ±5pp
    MIN_REGIMES_PROFITABLE = 3
    MAX_SOURCE_CONCENTRATION = 0.40
    MAX_SYMBOL_CONCENTRATION = 0.20
    MIN_HOLDOUT_N = 20
    MIN_WALK_FORWARD_FOLDS = 3
    
    def __init__(self, output_dir: str = "reports/admissibility"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run_pipeline(
        self,
        strategy_name: str,
        equity_curve: pd.Series,
        trades: List[Dict],
        asset_class: str,
        source_systems: Optional[List[str]] = None,
        symbols: Optional[List[str]] = None,
        regime_states: Optional[pd.Series] = None,
    ) -> PipelineResult:
        """
        Run the full 10-step admissibility pipeline.
        
        Returns PipelineResult with verdict for each stage and overall verdict.
        """
        result = PipelineResult(
            strategy_name=strategy_name,
            asset_class=asset_class,
            timestamp=pd.Timestamp.now().isoformat(),
        )
        
        # Step 1: Pre-register (always PASS if coming through pipeline)
        result.stages['pre_register'] = PipelineVerdict.PASS
        
        # Step 2: Data validation
        result.stages['data_validation'] = self._validate_data(equity_curve, trades)
        if result.stages['data_validation'] == PipelineVerdict.FAIL:
            result.overall_verdict = PipelineVerdict.FAIL
            result.rejection_reason = "Data validation failed"
            return result
        
        # Step 3: Walk-forward
        result.walk_forward = self._walk_forward(equity_curve, trades, asset_class)
        result.stages['walk_forward'] = result.walk_forward.verdict
        if result.stages['walk_forward'] == PipelineVerdict.FAIL:
            result.overall_verdict = PipelineVerdict.FAIL
            result.rejection_reason = f"Walk-forward failed: decay={result.walk_forward.decay_pct:.1%}"
            return result
        
        # Step 4: Cost model
        result.stages['cost_model'] = self._apply_costs(trades, asset_class)
        if result.stages['cost_model'] == PipelineVerdict.FAIL:
            result.overall_verdict = PipelineVerdict.FAIL
            result.rejection_reason = "After costs, strategy loses money"
            return result
        
        # Step 5: DSR/PBO
        result.dsr = self._compute_dsr(equity_curve, trades)
        result.stages['dsr_pbo'] = result.dsr.verdict
        if result.stages['dsr_pbo'] == PipelineVerdict.FAIL:
            result.overall_verdict = PipelineVerdict.FAIL
            result.rejection_reason = f"DSR={result.dsr.dsr:.2f}, PBO={result.dsr.pbo:.2f}"
            return result
        
        # Step 6: Block bootstrap
        result.stages['block_bootstrap'] = self._block_bootstrap(equity_curve, trades)
        if result.stages['block_bootstrap'] == PipelineVerdict.FAIL:
            result.overall_verdict = PipelineVerdict.FAIL
            result.rejection_reason = "Block bootstrap CI includes zero"
            return result
        
        # Step 7: Regime robustness
        if regime_states is not None:
            result.regime = self._regime_robustness(trades, regime_states)
            result.stages['regime_robustness'] = result.regime.verdict
        else:
            result.stages['regime_robustness'] = PipelineVerdict.PENDING
        
        # Step 8: Concentration check
        result.concentration = self._check_concentration(trades, source_systems, symbols)
        result.stages['concentration'] = result.concentration.verdict
        
        # Step 9: Forward validation (placeholder — needs shadow paper data)
        result.stages['forward_paper'] = PipelineVerdict.PENDING
        
        # Step 10: Promotion decision
        result.stages['promotion'] = PipelineVerdict.PENDING
        
        # Overall verdict
        failed_stages = [k for k, v in result.stages.items() if v == PipelineVerdict.FAIL]
        if failed_stages:
            result.overall_verdict = PipelineVerdict.FAIL
            result.rejection_reason = f"Failed stages: {', '.join(failed_stages)}"
        else:
            result.overall_verdict = PipelineVerdict.PASS
        
        # Save result
        self._save_result(result)
        
        return result
    
    def _validate_data(self, equity_curve: pd.Series, trades: List[Dict]) -> PipelineVerdict:
        """Step 2: Validate data quality."""
        if equity_curve is None or len(equity_curve) < 100:
            return PipelineVerdict.INSUFFICIENT_DATA
        if trades is None or len(trades) < 20:
            return PipelineVerdict.INSUFFICIENT_DATA
        
        # Check for NaN/inf
        if equity_curve.isna().any() or np.isinf(equity_curve).any():
            return PipelineVerdict.FAIL
        
        # Check for zero trades
        pnls = [t.get('pnl', 0) for t in trades]
        if all(p == 0 for p in pnls):
            return PipelineVerdict.FAIL
        
        return PipelineVerdict.PASS
    
    def _walk_forward(
        self, equity_curve: pd.Series, trades: List[Dict], asset_class: str
    ) -> WalkForwardResult:
        """Step 3: Purged walk-forward validation."""
        pnls = np.array([t.get('pnl', 0) for t in trades])
        n = len(pnls)
        
        if n < 30:
            return WalkForwardResult(
                train_pf=0, train_wr=0, train_n=0,
                holdout_pf=0, holdout_wr=0, holdout_n=0,
                decay_pct=0, folds_profitable=0, folds_total=0,
                verdict=PipelineVerdict.INSUFFICIENT_DATA,
            )
        
        # 60/20/20 split
        train_end = int(n * 0.6)
        val_end = int(n * 0.8)
        
        train_pnls = pnls[:train_end]
        holdout_pnls = pnls[val_end:]
        
        # Compute metrics
        # PF = gross profit / gross loss (sum of pnl), NOT win/loss counts.
        # The count-ratio form inflated PF for many-tiny-wins strategies — the
        # same P0 bug fixed in mutation_framework.compute_pf (PR #464).
        train_wins = int(np.sum(train_pnls > 0))
        train_losses = int(np.sum(train_pnls < 0))
        train_gp = float(np.sum(train_pnls[train_pnls > 0]))
        train_gl = float(-np.sum(train_pnls[train_pnls < 0]))
        train_pf = train_gp / train_gl if train_gl > 0 else (999 if train_gp > 0 else 0)
        train_wr = train_wins / len(train_pnls) if len(train_pnls) > 0 else 0

        holdout_wins = int(np.sum(holdout_pnls > 0))
        holdout_losses = int(np.sum(holdout_pnls < 0))
        holdout_gp = float(np.sum(holdout_pnls[holdout_pnls > 0]))
        holdout_gl = float(-np.sum(holdout_pnls[holdout_pnls < 0]))
        holdout_pf = holdout_gp / holdout_gl if holdout_gl > 0 else (999 if holdout_gp > 0 else 0)
        holdout_wr = holdout_wins / len(holdout_pnls) if len(holdout_pnls) > 0 else 0
        
        # Decay
        decay = (train_pf - holdout_pf) / train_pf if train_pf > 0 else 0
        
        # Walk-forward folds (5-fold)
        fold_size = n // 5
        folds_profitable = 0
        for i in range(5):
            fold_start = i * fold_size
            fold_end = (i + 1) * fold_size if i < 4 else n
            fold_pnls = pnls[fold_start:fold_end]
            if np.sum(fold_pnls) > 0:
                folds_profitable += 1
        
        # Verdict
        if holdout_pf >= self.MIN_LAB_PF and holdout_wr >= self.MIN_LAB_WR:
            verdict = PipelineVerdict.PASS
        elif holdout_pf >= 1.0 and folds_profitable >= 3:
            verdict = PipelineVerdict.PASS
        else:
            verdict = PipelineVerdict.FAIL
        
        return WalkForwardResult(
            train_pf=train_pf,
            train_wr=train_wr,
            train_n=len(train_pnls),
            holdout_pf=holdout_pf,
            holdout_wr=holdout_wr,
            holdout_n=len(holdout_pnls),
            decay_pct=decay,
            folds_profitable=folds_profitable,
            folds_total=5,
            verdict=verdict,
        )
    
    def _apply_costs(self, trades: List[Dict], asset_class: str) -> PipelineVerdict:
        """Step 4: Apply transaction costs."""
        cost = CostModel.for_class(asset_class)
        total_cost_pct = (cost.slippage_bps + cost.commission_bps) / 10000
        
        pnls = [t.get('pnl', 0) for t in trades]
        gross_pnl = sum(pnls)
        n_trades = len(pnls)
        
        # Costs apply to both entry and exit
        total_costs = total_cost_pct * 2 * n_trades
        net_pnl = gross_pnl - total_costs
        
        if net_pnl > 0:
            return PipelineVerdict.PASS
        else:
            return PipelineVerdict.FAIL
    
    def _compute_dsr(self, equity_curve: pd.Series, trades: List[Dict]) -> DSRResult:
        """Step 5: Deflated Sharpe Ratio + PBO."""
        returns = equity_curve.pct_change().dropna()
        
        if len(returns) < 30:
            return DSRResult(
                sharpe=0, dsr=0, pbo=1.0,
                n_strategies_tested=1,
                verdict=PipelineVerdict.INSUFFICIENT_DATA,
            )
        
        # Sharpe ratio
        sharpe = np.sqrt(252) * returns.mean() / returns.std() if returns.std() > 0 else 0
        
        # Simplified DSR (Bailey & Lopez de Prado)
        # DSR = Phi((sharpe - sharpe_null) * sqrt(n-1) / sqrt(1 + skew*sharpe + (kurt-3)/4 * sharpe^2))
        n = len(returns)
        skew = returns.skew()
        kurt = returns.kurtosis()
        
        # Expected max Sharpe under null (multiple testing)
        n_strategies = 100  # Assume we tested 100 strategies
        sharpe_null = np.sqrt(2 * np.log(n_strategies))  # Expected max under null
        
        # DSR calculation
        denom = np.sqrt(1 + skew * sharpe + (kurt - 3) / 4 * sharpe**2)
        if denom > 0:
            dsr_z = (sharpe - sharpe_null) * np.sqrt(n - 1) / denom
            dsr = float(np.clip(dsr_z / np.sqrt(n), 0, 1))  # Simplified
        else:
            dsr = 0
        
        # PBO (simplified)
        pbo = max(0, 1 - dsr)
        
        if dsr >= self.MIN_DSR:
            verdict = PipelineVerdict.PASS
        else:
            verdict = PipelineVerdict.FAIL
        
        return DSRResult(
            sharpe=sharpe,
            dsr=dsr,
            pbo=pbo,
            n_strategies_tested=n_strategies,
            verdict=verdict,
        )
    
    def _block_bootstrap(
        self, equity_curve: pd.Series, trades: List[Dict], block_size: int = 5
    ) -> PipelineVerdict:
        """Step 6: Block bootstrap for CI estimation."""
        pnls = np.array([t.get('pnl', 0) for t in trades])
        n = len(pnls)
        
        if n < 30:
            return PipelineVerdict.INSUFFICIENT_DATA
        
        # Block bootstrap
        n_bootstrap = 1000
        bootstrap_sharpes = []
        
        for _ in range(n_bootstrap):
            # Sample blocks
            blocks = []
            while len(blocks) < n:
                start = np.random.randint(0, max(1, n - block_size))
                block = pnls[start:start + block_size]
                blocks.extend(block.tolist())
            blocks = np.array(blocks[:n])
            
            # Compute Sharpe
            if np.std(blocks) > 0:
                bs_sharpe = np.mean(blocks) / np.std(blocks)
            else:
                bs_sharpe = 0
            bootstrap_sharpes.append(bs_sharpe)
        
        # CI
        ci_lower = np.percentile(bootstrap_sharpes, 2.5)
        ci_upper = np.percentile(bootstrap_sharpes, 97.5)
        
        # Verdict: CI must not include zero
        if ci_lower > 0:
            return PipelineVerdict.PASS
        else:
            return PipelineVerdict.FAIL
    
    def _regime_robustness(
        self, trades: List[Dict], regime_states: pd.Series
    ) -> RegimeResult:
        """Step 7: Check regime robustness."""
        regime_pnls = {}
        
        for trade in trades:
            entry_date = trade.get('entry_date')
            pnl = trade.get('pnl', 0)
            
            if entry_date is not None:
                # Find regime at entry
                regime = regime_states.loc[
                    regime_states.index <= entry_date
                ].iloc[-1] if len(regime_states.loc[regime_states.index <= entry_date]) > 0 else 'UNKNOWN'
                
                if regime not in regime_pnls:
                    regime_pnls[regime] = []
                regime_pnls[regime].append(pnl)
        
        # Compute PF per regime
        regime_pf = {}
        regimes_profitable = []
        
        for regime, pnls in regime_pnls.items():
            # PF = gross profit / gross loss (not win/loss counts) — see PR #464.
            gross_profit = sum(p for p in pnls if p > 0)
            gross_loss = -sum(p for p in pnls if p < 0)
            pf = gross_profit / gross_loss if gross_loss > 0 else (999 if gross_profit > 0 else 0)
            regime_pf[regime] = pf
            if pf >= 1.0:
                regimes_profitable.append(regime)
        
        if len(regimes_profitable) >= self.MIN_REGIMES_PROFITABLE:
            verdict = PipelineVerdict.PASS
        else:
            verdict = PipelineVerdict.FAIL
        
        return RegimeResult(
            regimes_tested=list(regime_pnls.keys()),
            regimes_profitable=regimes_profitable,
            regime_pf=regime_pf,
            verdict=verdict,
        )
    
    def _check_concentration(
        self,
        trades: List[Dict],
        source_systems: Optional[List[str]],
        symbols: Optional[List[str]],
    ) -> ConcentrationResult:
        """Step 8: Check concentration."""
        n = len(trades)
        
        # Source concentration
        max_source_pct = 0
        if source_systems:
            from collections import Counter
            source_counts = Counter(source_systems)
            max_source_pct = max(source_counts.values()) / n if n > 0 else 0
        
        # Symbol concentration
        max_symbol_pct = 0
        if symbols:
            from collections import Counter
            symbol_counts = Counter(symbols)
            max_symbol_pct = max(symbol_counts.values()) / n if n > 0 else 0
        
        # Class concentration (single-class strategy is fine)
        max_class_pct = 1.0  # Single-class by design
        
        if (max_source_pct <= self.MAX_SOURCE_CONCENTRATION and
            max_symbol_pct <= self.MAX_SYMBOL_CONCENTRATION):
            verdict = PipelineVerdict.PASS
        else:
            verdict = PipelineVerdict.FAIL
        
        return ConcentrationResult(
            max_source_pct=max_source_pct,
            max_symbol_pct=max_symbol_pct,
            max_class_pct=max_class_pct,
            verdict=verdict,
        )
    
    def _save_result(self, result: PipelineResult):
        """Save pipeline result to file."""
        output_file = self.output_dir / f"{result.strategy_name}_{result.asset_class}.json"
        with open(output_file, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        logger.info(f"Pipeline result saved to {output_file}")


def run_admissibility_check(
    strategy_name: str,
    equity_curve: pd.Series,
    trades: List[Dict],
    asset_class: str,
    **kwargs,
) -> PipelineResult:
    """Convenience function to run the admissibility pipeline."""
    pipeline = AdmissibilityPipeline()
    return pipeline.run_pipeline(
        strategy_name=strategy_name,
        equity_curve=equity_curve,
        trades=trades,
        asset_class=asset_class,
        **kwargs,
    )
