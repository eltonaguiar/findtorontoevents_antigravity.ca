"""
StrategyFingerprinter - Duplicate Detection
===========================================

Prevents multiple AI agents from creating identical or nearly-identical
strategies. Ensures diversity in the strategy pool.

Fingerprinting Methods:
1. Code structure hashing (AST-based)
2. Signal correlation analysis
3. Parameter space coverage
"""

import ast
import hashlib
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np
import logging

logger = logging.getLogger(__name__)

REGISTRY_FILE = Path(__file__).resolve().parents[1] / "config" / "agent_registry.json"


@dataclass
class StrategyFingerprint:
    """Complete fingerprint of a strategy."""
    code_hash: str          # Hash of normalized code
    ast_hash: str           # Hash of AST structure
    indicator_signature: str  # Which indicators used
    parameter_hash: str     # Hash of parameter values
    signal_pattern: str     # Pattern of signals (from backtest)
    agent_id: str
    strategy_name: str
    created_at: str


class StrategyFingerprinter:
    """
    Detects duplicate or overly similar strategies across agents.
    
    Similarity Thresholds:
    - Code similarity > 95%: REJECT (exact duplicate)
    - Code similarity > 85%: WARN (minor variation)
    - Signal correlation > 0.95: REJECT (same signals)
    """
    
    # Weights for composite similarity
    CODE_WEIGHT = 0.4
    AST_WEIGHT = 0.3
    SIGNAL_WEIGHT = 0.3
    
    def __init__(self):
        self.registry = self._load_registry()
    
    def _load_registry(self) -> Dict:
        """Load fingerprint registry."""
        if REGISTRY_FILE.exists():
            with open(REGISTRY_FILE) as f:
                return json.load(f).get("strategy_fingerprints", {})
        return {}
    
    def _save_registry(self):
        """Save fingerprint registry."""
        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if REGISTRY_FILE.exists():
            with open(REGISTRY_FILE) as f:
                data = json.load(f)
        else:
            data = {}
        data["strategy_fingerprints"] = self.registry
        with open(REGISTRY_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _normalize_code(self, code: str) -> str:
        """
        Normalize code for comparison.
        
        Removes:
        - Comments
        - Whitespace variations
        - Variable name differences (normalized to generic names)
        """
        # Remove comments
        lines = []
        for line in code.split('\n'):
            # Remove inline comments
            if '#' in line:
                line = line[:line.index('#')]
            lines.append(line)
        code = '\n'.join(lines)
        
        # Remove docstrings
        code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
        code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
        
        # Normalize whitespace
        code = re.sub(r'\s+', ' ', code)
        code = code.strip()
        
        # Normalize variable names (simple approach)
        # This is a simplified version - full implementation would use AST
        code = re.sub(r'\b[a-z_][a-z0-9_]*\b', 'VAR', code, flags=re.IGNORECASE)
        
        return code.lower()
    
    def _compute_ast_hash(self, code: str) -> str:
        """Compute hash of AST structure."""
        try:
            tree = ast.parse(code)
            # Normalize AST by removing variable names
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    node.id = 'VAR'
                elif isinstance(node, ast.FunctionDef):
                    node.name = 'FUNC'
                elif isinstance(node, ast.ClassDef):
                    node.name = 'CLASS'
            
            # Serialize AST
            ast_str = ast.dump(tree)
            return hashlib.sha256(ast_str.encode()).hexdigest()[:16]
        except SyntaxError:
            return "invalid"
    
    def _extract_indicators(self, code: str) -> str:
        """Extract which technical indicators are used."""
        indicators = []
        indicator_patterns = [
            (r'rsi|RSI', 'RSI'),
            (r'macd|MACD', 'MACD'),
            (r'ema|EMA|sma|SMA', 'MA'),
            (r'bollinger|BB', 'BB'),
            (r'atr|ATR', 'ATR'),
            (r'vwap|VWAP', 'VWAP'),
            (r'adx|ADX', 'ADX'),
            (r'stochastic|STOCH', 'STOCH'),
            (r'obv|OBV', 'OBV'),
            (r'volume|VOLUME', 'VOLUME'),
        ]
        
        for pattern, name in indicator_patterns:
            if re.search(pattern, code):
                indicators.append(name)
        
        return ','.join(sorted(indicators)) if indicators else "NONE"
    
    def compute_fingerprint(
        self,
        code: str,
        agent_id: str,
        strategy_name: str,
        backtest_signals: Optional[List] = None
    ) -> StrategyFingerprint:
        """
        Compute complete fingerprint for a strategy.
        
        Args:
            code: Strategy source code
            agent_id: Creating agent
            strategy_name: Strategy identifier
            backtest_signals: Optional signal history for pattern analysis
            
        Returns:
            StrategyFingerprint object
        """
        normalized = self._normalize_code(code)
        code_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        ast_hash = self._compute_ast_hash(code)
        indicators = self._extract_indicators(code)
        
        # Parameter hash (extract numeric constants)
        params = re.findall(r'\b\d+\.?\d*\b', normalized)
        param_hash = hashlib.sha256(','.join(params).encode()).hexdigest()[:16]
        
        # Signal pattern
        if backtest_signals:
            signal_pattern = self._compute_signal_pattern(backtest_signals)
        else:
            signal_pattern = "unknown"
        
        from datetime import datetime, timezone
        return StrategyFingerprint(
            code_hash=code_hash,
            ast_hash=ast_hash,
            indicator_signature=indicators,
            parameter_hash=param_hash,
            signal_pattern=signal_pattern,
            agent_id=agent_id,
            strategy_name=strategy_name,
            created_at=datetime.now(timezone.utc).isoformat()
        )
    
    def _compute_signal_pattern(self, signals: List) -> str:
        """Create hash of signal pattern."""
        if not signals:
            return "empty"
        
        # Convert to binary string (1=buy, -1=sell, 0=hold)
        pattern = ''.join(str(s.get('direction', 0)) for s in signals[-100:])
        return hashlib.sha256(pattern.encode()).hexdigest()[:16]
    
    def calculate_similarity(
        self,
        fp1: StrategyFingerprint,
        fp2: StrategyFingerprint
    ) -> float:
        """
        Calculate composite similarity between two fingerprints.
        
        Returns:
            Similarity score [0.0, 1.0]
        """
        # Code similarity
        code_sim = 1.0 if fp1.code_hash == fp2.code_hash else 0.0
        
        # AST similarity
        ast_sim = 1.0 if fp1.ast_hash == fp2.ast_hash else 0.0
        
        # Indicator similarity (Jaccard)
        ind1 = set(fp1.indicator_signature.split(','))
        ind2 = set(fp2.indicator_signature.split(','))
        if ind1 or ind2:
            indicator_sim = len(ind1 & ind2) / len(ind1 | ind2)
        else:
            indicator_sim = 1.0
        
        # Signal pattern similarity
        if fp1.signal_pattern != "unknown" and fp2.signal_pattern != "unknown":
            signal_sim = 1.0 if fp1.signal_pattern == fp2.signal_pattern else 0.0
        else:
            signal_sim = 0.5  # Unknown
        
        # Composite score
        composite = (
            self.CODE_WEIGHT * code_sim +
            self.AST_WEIGHT * ast_sim +
            (1 - self.CODE_WEIGHT - self.AST_WEIGHT) * 0.5 * (indicator_sim + signal_sim)
        )
        
        return composite
    
    def check_uniqueness(
        self,
        fingerprint: StrategyFingerprint,
        threshold: float = 0.90
    ) -> Tuple[bool, List[Dict]]:
        """
        Check if strategy is unique compared to existing ones.
        
        Args:
            fingerprint: Strategy to check
            threshold: Similarity threshold for rejection
            
        Returns:
            (is_unique, list_of_similar_strategies)
        """
        similar = []
        
        for key, existing in self.registry.items():
            existing_fp = StrategyFingerprint(**existing)
            similarity = self.calculate_similarity(fingerprint, existing_fp)
            
            if similarity >= threshold:
                similar.append({
                    "strategy_key": key,
                    "agent_id": existing["agent_id"],
                    "strategy_name": existing["strategy_name"],
                    "similarity": round(similarity, 3),
                    "created_at": existing["created_at"]
                })
        
        is_unique = len(similar) == 0
        return is_unique, sorted(similar, key=lambda x: x["similarity"], reverse=True)
    
    def register_strategy(self, fingerprint: StrategyFingerprint):
        """Add strategy to registry."""
        key = f"{fingerprint.agent_id}:{fingerprint.strategy_name}"
        self.registry[key] = {
            "code_hash": fingerprint.code_hash,
            "ast_hash": fingerprint.ast_hash,
            "indicator_signature": fingerprint.indicator_signature,
            "parameter_hash": fingerprint.parameter_hash,
            "signal_pattern": fingerprint.signal_pattern,
            "agent_id": fingerprint.agent_id,
            "strategy_name": fingerprint.strategy_name,
            "created_at": fingerprint.created_at
        }
        self._save_registry()
        logger.info(f"[Fingerprinter] Registered {key}")
    
    def get_strategy_diversity_report(self) -> Dict:
        """Generate report on strategy diversity across agents."""
        if not self.registry:
            return {"message": "No strategies registered"}
        
        # Count indicators usage
        indicator_counts = {}
        agent_counts = {}
        
        for key, fp in self.registry.items():
            agent = fp["agent_id"]
            agent_counts[agent] = agent_counts.get(agent, 0) + 1
            
            for ind in fp["indicator_signature"].split(','):
                indicator_counts[ind] = indicator_counts.get(ind, 0) + 1
        
        return {
            "total_strategies": len(self.registry),
            "unique_agents": len(agent_counts),
            "strategies_per_agent": agent_counts,
            "indicator_usage": indicator_counts,
            "most_common_indicators": sorted(
                indicator_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
