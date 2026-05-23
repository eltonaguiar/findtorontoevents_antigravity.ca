#!/usr/bin/env python3
"""
Strategy Validator Agent
========================

The "quality assurance" agent that:
1. Checks for duplicate strategies (via fingerprinting)
2. Validates code quality and structure
3. Ensures compliance with Baby Strat requirements
4. Verifies no overfitting indicators

Usage:
    from backtest_team.validator import StrategyValidator
    validator = StrategyValidator()
    result = validator.validate(strategy_file)
"""

import ast
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of strategy validation."""
    strategy_name: str
    agent_id: str
    passed: bool
    errors: List[str]
    warnings: List[str]
    fingerprint: str
    is_duplicate: bool
    duplicate_of: Optional[str] = None


class StrategyFingerprint:
    """
    Generates unique fingerprints for strategies.
    
    Extracts:
    - Indicator types used
    - Signal logic structure
    - Entry/exit conditions
    - Parameter count and values
    
    Two strategies with similar fingerprints = likely duplicates
    """
    
    INDICATOR_KEYWORDS = [
        'rsi', 'macd', 'ema', 'sma', 'bollinger', 'atr', 'volume',
        'stochastic', 'obv', 'adx', 'cci', 'momentum', 'correlation',
        'vwap', 'ichimoku', 'parabolic', 'williams', 'mfi'
    ]
    
    def __init__(self):
        self.known_fingerprints: Dict[str, str] = {}  # fingerprint -> strategy_name
        
    def extract(self, code: str) -> Dict:
        """Extract fingerprint components from strategy code."""
        code_lower = code.lower()
        
        # Find indicators
        indicators = [ind for ind in self.INDICATOR_KEYWORDS if ind in code_lower]
        
        # Count parameters (rough estimate from __init__)
        param_count = code_lower.count('self.params.get') + code_lower.count('self.')
        
        # Detect signal types
        signal_types = []
        if 'mean reversion' in code_lower or 'oversold' in code_lower or 'overbought' in code_lower:
            signal_types.append('mean_reversion')
        if 'momentum' in code_lower or 'breakout' in code_lower:
            signal_types.append('momentum')
        if 'trend' in code_lower:
            signal_types.append('trend_following')
        if 'correlation' in code_lower or 'cross-asset' in code_lower:
            signal_types.append('cross_asset')
        
        # Extract entry conditions
        entry_conditions = []
        if 'oversold' in code_lower:
            entry_conditions.append('oversold')
        if 'overbought' in code_lower:
            entry_conditions.append('overbought')
        if 'crossover' in code_lower or 'cross over' in code_lower:
            entry_conditions.append('crossover')
        if 'breakdown' in code_lower:
            entry_conditions.append('breakdown')
        
        return {
            'indicators': sorted(indicators),
            'param_count': param_count,
            'signal_types': signal_types,
            'entry_conditions': entry_conditions
        }
    
    def generate(self, code: str) -> str:
        """Generate unique fingerprint hash."""
        fingerprint = self.extract(code)
        # Create deterministic hash
        fingerprint_str = json.dumps(fingerprint, sort_keys=True)
        return hashlib.md5(fingerprint_str.encode()).hexdigest()[:16]
    
    def check_duplicate(self, fingerprint_hash: str, strategy_name: str) -> Optional[str]:
        """Check if fingerprint already exists."""
        if fingerprint_hash in self.known_fingerprints:
            existing = self.known_fingerprints[fingerprint_hash]
            if existing != strategy_name:
                return existing
        self.known_fingerprints[fingerprint_hash] = strategy_name
        return None


class StrategyValidator:
    """
    Validates Baby Strat strategies against quality criteria.
    """
    
    def __init__(self):
        self.fingerprinter = StrategyFingerprint()
        self.load_existing_fingerprints()
        
    def load_existing_fingerprints(self):
        """Load fingerprints from existing strategies."""
        incubator_path = Path(__file__).parent.parent
        agents_path = incubator_path / "agents"
        
        for agent_dir in agents_path.iterdir():
            if not agent_dir.is_dir():
                continue
            for py_file in agent_dir.glob("*.py"):
                if py_file.name.endswith("_test.py"):
                    continue
                try:
                    code = py_file.read_text()
                    fp = self.fingerprinter.generate(code)
                    self.fingerprinter.known_fingerprints[fp] = py_file.stem
                except:
                    pass
    
    def validate(self, strategy_file: Path, meta: Dict) -> ValidationResult:
        """Validate a strategy file."""
        errors = []
        warnings = []
        
        # Read code
        try:
            code = strategy_file.read_text()
        except Exception as e:
            return ValidationResult(
                strategy_name=meta.get('strategy_name', 'unknown'),
                agent_id=meta.get('agent_id', 'unknown'),
                passed=False,
                errors=[f"Cannot read file: {e}"],
                warnings=[],
                fingerprint="",
                is_duplicate=False
            )
        
        # Check syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
            return ValidationResult(
                strategy_name=meta.get('strategy_name', 'unknown'),
                agent_id=meta.get('agent_id', 'unknown'),
                passed=False,
                errors=errors,
                warnings=[],
                fingerprint="",
                is_duplicate=False
            )
        
        # Generate fingerprint
        fingerprint = self.fingerprinter.generate(code)
        
        # Check for duplicates
        duplicate_of = self.fingerprinter.check_duplicate(fingerprint, meta.get('strategy_name'))
        if duplicate_of:
            warnings.append(f"Similar to existing strategy: {duplicate_of}")
        
        # Check required components
        if 'generate_signals' not in code:
            errors.append("Missing generate_signals() method")
        
        if 'Signal' not in code or 'dataclass' not in code:
            warnings.append("May not use standard Signal dataclass")
        
        # Check parameter count
        param_count = code.count('self.params.get')
        if param_count > 10:
            warnings.append(f"High parameter count ({param_count}) - overfit risk")
        elif param_count < 2:
            warnings.append(f"Very few parameters ({param_count}) - may be too simple")
        
        # Check risk management
        has_stop_loss = 'stop_loss' in code.lower() or 'sl' in code.lower()
        has_take_profit = 'take_profit' in code.lower() or 'tp' in code.lower()
        
        if not has_stop_loss:
            errors.append("Missing stop loss mechanism")
        if not has_take_profit:
            warnings.append("Missing take profit mechanism")
        
        # Check for hardcoded values (potential overfit)
        magic_numbers = ['0.618', '1.618', '3.14', '14', '21', '50', '200']
        for num in magic_numbers:
            if num in code and f'#{num}' not in code:  # Not in comment
                warnings.append(f"Uses magic number: {num}")
        
        # Check for future peeking
        if '.iloc[' in code and '+1' in code:
            warnings.append("Potential future peeking detected")
        
        # Check docstring quality
        has_docstring = '"""' in code or "'''" in code
        if not has_docstring:
            warnings.append("Missing module docstring")
        
        passed = len(errors) == 0
        
        return ValidationResult(
            strategy_name=meta.get('strategy_name', 'unknown'),
            agent_id=meta.get('agent_id', 'unknown'),
            passed=passed,
            errors=errors,
            warnings=warnings,
            fingerprint=fingerprint,
            is_duplicate=duplicate_of is not None,
            duplicate_of=duplicate_of
        )
    
    def validate_all(self) -> List[ValidationResult]:
        """Validate all strategies in incubator."""
        results = []
        incubator_path = Path(__file__).parent.parent
        agents_path = incubator_path / "agents"
        
        for agent_dir in agents_path.iterdir():
            if not agent_dir.is_dir():
                continue
            for py_file in agent_dir.glob("*.py"):
                meta_file = Path(str(py_file) + ".meta.json")
                if not meta_file.exists():
                    continue
                
                with open(meta_file) as f:
                    meta = json.load(f)
                
                result = self.validate(py_file, meta)
                results.append(result)
        
        return results


def print_validation_report(results: List[ValidationResult]):
    """Print validation report."""
    print("\n" + "=" * 60)
    print("STRATEGY VALIDATION REPORT")
    print("=" * 60)
    
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        dup_icon = " [DUP]" if r.is_duplicate else ""
        print(f"\n{status}: {r.strategy_name} ({r.agent_id}){dup_icon}")
        print(f"  Fingerprint: {r.fingerprint}")
        
        if r.errors:
            print("  Errors:")
            for e in r.errors:
                print(f"    - {e}")
        
        if r.warnings:
            print("  Warnings:")
            for w in r.warnings:
                print(f"    - {w}")
    
    print("\n" + "=" * 60)
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    duplicates = sum(1 for r in results if r.is_duplicate)
    print(f"Total: {total} | Passed: {passed} | Failed: {total - passed} | Duplicates: {duplicates}")
    print("=" * 60)


if __name__ == "__main__":
    validator = StrategyValidator()
    results = validator.validate_all()
    print_validation_report(results)
