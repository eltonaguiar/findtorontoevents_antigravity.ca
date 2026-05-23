"""
Base Researcher — Common Interface for All Academic Researchers
===============================================================

Defines the standard interface that all specialized researchers must implement.
Ensures consistency across the multi-agent research framework.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from pathlib import Path
import json

# Import data access types (with fallbacks for type hints)
try:
    from .data_access import (
        Exchange,
        OnChainMetric,
        SentimentSource,
        DataFrequency,
        DataManager,
    )
    HAS_DATA_ACCESS_TYPES = True
    HAS_DATA_ACCESS = True
except ImportError:
    # Define placeholder types for type hints if data_access not available
    HAS_DATA_ACCESS_TYPES = False
    HAS_DATA_ACCESS = False
    DataManager = None  # type: ignore[assignment]
    
    class Exchange:
        BINANCE = "binance"
        COINBASE = "coinbase"
        KRAKEN = "kraken"
    
    class OnChainMetric:
        EXCHANGE_INFLOW = "exchange_inflow"
        EXCHANGE_OUTFLOW = "exchange_outflow"
        EXCHANGE_NET_FLOW = "exchange_net_flow"
        SOPR = "sopr"
        MVRV = "mvrv"
        NUPL = "nupl"
        ACTIVE_ADDRESSES = "active_addresses"
        TRANSACTION_COUNT = "transaction_count"
        TRANSACTION_VOLUME = "transaction_volume"
        HASH_RATE = "hash_rate"
        DIFFICULTY = "difficulty"
    
    class SentimentSource:
        NEWS = "news"
        TWITTER = "twitter"
        REDDIT = "reddit"
        OPTIONS_FLOW = "options_flow"
    
    class DataFrequency:
        MINUTE_1 = "1m"
        MINUTE_5 = "5m"
        MINUTE_15 = "15m"
        HOUR_1 = "1h"
        HOUR_4 = "4h"
        DAY_1 = "1d"


@dataclass
class ResearchQuestion:
    """
    A specific research question that a researcher will investigate.
    
    Attributes:
        id: Unique identifier
        title: Short descriptive title
        description: Detailed explanation of the research question
        hypothesis: Expected outcome based on literature
        methodology: Experimental approach
        success_criteria: How to determine if the hypothesis is supported
    """
    id: str
    title: str
    description: str
    hypothesis: str
    methodology: str
    success_criteria: Dict[str, Any]
    priority: int = 1  # 1=high, 2=medium, 3=low
    dependencies: List[str] = field(default_factory=list)  # Other research IDs


@dataclass
class ResearchResult:
    """
    Results from a completed research investigation.
    
    Attributes:
        researcher_id: Which researcher produced this result
        question_id: Which research question was answered
        timestamp: When the research was completed
        findings: Key findings and insights
        metrics: Quantitative performance metrics
        model_path: Path to saved model (if applicable)
        code: Implementation code
        confidence: Statistical confidence level (0-1)
        reproducible: Whether results can be reproduced
        limitations: Known limitations and caveats
    """
    researcher_id: str
    question_id: str
    timestamp: str
    findings: str
    metrics: Dict[str, float]
    model_path: Optional[str] = None
    code: Optional[str] = None
    confidence: float = 0.0
    reproducible: bool = True
    limitations: List[str] = field(default_factory=list)
    recommendations: Dict[str, Any] = field(default_factory=dict)


class Researcher(ABC):
    """
    Abstract base class for all specialized researchers.
    
    Each researcher represents a specific academic deep learning approach
    and must implement the standard research lifecycle.
    
    Research Lifecycle:
      1. formulate_questions() → List[ResearchQuestion]
      2. prepare_data() → Prepared datasets
      3. conduct_experiment() → ResearchResult
      4. validate_findings() → Validation report
      5. share_knowledge() → Knowledge base contribution
    
    All researchers maintain:
      - A unique identifier
      - Specialization area
      - Knowledge of relevant literature
      - Standardized experimental protocols
    """
    
    # Class-level metadata (must be overridden by subclasses)
    researcher_id: str = "base"
    name: str = "Base Researcher"
    specialization: str = "General deep learning"
    literature: List[str] = []
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize researcher with optional configuration.
        
        Args:
            config: Configuration dictionary (model params, data paths, etc.)
        """
        self.config = config or {}
        self.questions: List[ResearchQuestion] = []
        self.results: Dict[str, ResearchResult] = {}
        self.knowledge_base: Dict[str, Any] = {}
        
        # Standard paths (can be overridden in config)
        self.base_dir = Path(self.config.get("base_dir", "ml_crypto_predictor"))
        self.data_dir = self.base_dir / "data"
        self.models_dir = self.base_dir / "models"
        self.results_dir = self.base_dir / "results" / "research"
        
        # Create directories
        for d in [self.data_dir, self.models_dir, self.results_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Initialize DataManager for unified data access
        if HAS_DATA_ACCESS:
            self.data_manager = DataManager(
                cache_dir=self.data_dir,
                cache_ttl_hours=self.config.get("cache_ttl_hours", 1.0),
                rate_limit_delay=self.config.get("rate_limit_delay", 0.15),
                log_level=self.config.get("log_level", "INFO")
            )
        else:
            self.data_manager = None
            print("[WARN] DataManager not available. Data access methods will fail.")
    
    @abstractmethod
    def formulate_questions(self) -> List[ResearchQuestion]:
        """
        Define the research questions this investigator will address.
        
        This method should:
          - Review relevant academic literature
          - Identify gaps in current approaches
          - Formulate testable hypotheses
          - Define experimental methodology
          - Specify success criteria
        
        Returns:
            List of ResearchQuestion objects
        """
        pass
    
    @abstractmethod
    def prepare_data(self, question: ResearchQuestion) -> Dict[str, Any]:
        """
        Prepare data for the specific research question.
        
        This may include:
          - Fetching market data
          - Feature engineering
          - Data augmentation
          - Train/validation/test splits
          - Cross-validation setup
        
        Returns:
            Dictionary containing prepared datasets and metadata
        """
        pass
    
    @abstractmethod
    def conduct_experiment(self, question: ResearchQuestion,
                          data: Dict[str, Any]) -> ResearchResult:
        """
        Execute the main experiment for a research question.
        
        This should:
          - Implement the proposed methodology
          - Train models with proper validation
          - Collect metrics and findings
          - Save models if successful
          - Document limitations
        
        Returns:
            ResearchResult with complete findings
        """
        pass
    
    @abstractmethod
    def validate_findings(self, result: ResearchResult) -> Dict[str, Any]:
        """
        Perform validation checks on the experiment results.
        
        Should verify:
          - Statistical significance
          - Robustness across different time periods
          - Absence of data leakage
          - Reproducibility
          - Overfitting checks
        
        Returns:
            Validation report with pass/fail status and diagnostics
        """
        pass

    # ============================================================================
    # Data Access Convenience Methods
    # ============================================================================
    
    def get_price_data(
        self,
        symbol: str,
        exchange: Union[str, Exchange] = "binance",
        timeframe: Union[str, DataFrequency] = "1h",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        include_indicators: bool = False
    ) -> pd.DataFrame:
        """
        Convenience wrapper for DataManager.get_price_data().
        
        Returns OHLCV price data for the specified symbol and timeframe.
        """
        if not self.data_manager:
            raise RuntimeError("DataManager not initialized. Cannot fetch price data.")
        
        return self.data_manager.get_price_data(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            start=start,
            end=end,
            include_indicators=include_indicators
        )
    
    def get_onchain_metrics(
        self,
        coin: str,
        metric: Union[str, OnChainMetric],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        frequency: Union[str, DataFrequency] = "1d"
    ) -> pd.DataFrame:
        """
        Convenience wrapper for DataManager.get_onchain_metrics().
        
        Returns on-chain blockchain metrics.
        """
        if not self.data_manager:
            raise RuntimeError("DataManager not initialized. Cannot fetch on-chain data.")
        
        return self.data_manager.get_onchain_metrics(
            coin=coin,
            metric=metric,
            start=start,
            end=end,
            frequency=frequency
        )
    
    def get_sentiment_data(
        self,
        coin: str,
        source: Union[str, SentimentSource],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        frequency: Union[str, DataFrequency] = "1h"
    ) -> pd.DataFrame:
        """
        Convenience wrapper for DataManager.get_sentiment_data().
        
        Returns sentiment data from specified source.
        """
        if not self.data_manager:
            raise RuntimeError("DataManager not initialized. Cannot fetch sentiment data.")
        
        return self.data_manager.get_sentiment_data(
            coin=coin,
            source=source,
            start=start,
            end=end,
            frequency=frequency
        )
    
    def get_google_trends(
        self,
        keyword: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        frequency: Union[str, DataFrequency] = "1d"
    ) -> pd.DataFrame:
        """
        Convenience wrapper for DataManager.get_google_trends().
        
        Returns Google Trends data.
        """
        if not self.data_manager:
            raise RuntimeError("DataManager not initialized. Cannot fetch Google Trends data.")
        
        return self.data_manager.get_google_trends(
            keyword=keyword,
            start=start,
            end=end,
            frequency=frequency
        )
    
    def get_github_activity(
        self,
        repo: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        frequency: Union[str, DataFrequency] = "1d"
    ) -> pd.DataFrame:
        """
        Convenience wrapper for DataManager.get_github_activity().
        
        Returns GitHub repository activity metrics.
        """
        if not self.data_manager:
            raise RuntimeError("DataManager not initialized. Cannot fetch GitHub activity.")
        
        return self.data_manager.get_github_activity(
            repo=repo,
            start=start,
            end=end,
            frequency=frequency
        )
    
    def clear_data_cache(self, data_type: Optional[str] = None):
        """
        Clear cached data.
        
        Args:
            data_type: Type of data to clear (price, onchain, sentiment, alternative)
                      If None, clears all caches.
        """
        if self.data_manager:
            self.data_manager.clear_cache(data_type)
        else:
            print("[WARN] DataManager not initialized. Cannot clear cache.")
    
    def share_knowledge(self) -> Dict[str, Any]:
        """
        Contribute findings to the shared knowledge base.
        
        This allows other researchers to:
          - Learn from this researcher's discoveries
          - Build upon previous work
          - Avoid repeating experiments
          - Cross-validate findings
        
        Returns:
            Knowledge contribution dictionary
        """
        contribution = {
            "researcher_id": self.researcher_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "findings": {qid: res.findings for qid, res in self.results.items()},
            "metrics": {qid: res.metrics for qid, res in self.results.items()},
            "recommendations": {
                qid: res.recommendations for qid, res in self.results.items()
            },
        }
        
        # Save to shared knowledge base
        kb_path = self.results_dir / "knowledge_base.json"
        existing = {}
        if kb_path.exists():
            try:
                with open(kb_path) as f:
                    existing = json.load(f)
            except Exception:
                pass
        
        # Merge with existing knowledge
        if "contributions" not in existing:
            existing["contributions"] = []
        existing["contributions"].append(contribution)
        
        with open(kb_path, "w") as f:
            json.dump(existing, f, indent=2, default=str)
        
        self.knowledge_base = existing
        return contribution
    
    def run_full_investigation(self, question_id: Optional[str] = None) -> Dict[str, ResearchResult]:
        """
        Execute the complete research lifecycle for all or specific questions.
        
        Args:
            question_id: If provided, only run this question; else run all
            
        Returns:
            Dictionary mapping question_id → ResearchResult
        """
        if not self.questions:
            self.questions = self.formulate_questions()
        
        results = {}
        questions_to_run = self.questions
        if question_id:
            questions_to_run = [q for q in self.questions if q.id == question_id]
        
        for question in questions_to_run:
            print(f"\n[{self.name}] Investigating: {question.title}")
            print(f"  Hypothesis: {question.hypothesis}")
            
            # Step 1: Prepare data
            print("  Preparing data...")
            data = self.prepare_data(question)
            
            # Step 2: Conduct experiment
            print("  Running experiment...")
            result = self.conduct_experiment(question, data)
            self.results[question.id] = result
            
            # Step 3: Validate findings
            print("  Validating findings...")
            validation = self.validate_findings(result)
            result.confidence = validation.get("confidence", 0.0)
            result.reproducible = validation.get("reproducible", True)
            result.limitations = validation.get("limitations", [])
            
            # Save result
            self._save_result(result)
            
            print(f"  ✓ Complete: {result.findings[:100]}...")
            results[question.id] = result
        
        # Share knowledge
        print(f"\n[{self.name}] Sharing knowledge with research community...")
        self.share_knowledge()
        
        return results
    
    def _save_result(self, result: ResearchResult):
        """Save research result to disk."""
        result_path = self.results_dir / f"{self.researcher_id}_{result.question_id}.json"
        with open(result_path, "w") as f:
            json.dump({
                "researcher_id": result.researcher_id,
                "question_id": result.question_id,
                "timestamp": result.timestamp,
                "findings": result.findings,
                "metrics": result.metrics,
                "model_path": result.model_path,
                "code": result.code,
                "confidence": result.confidence,
                "reproducible": result.reproducible,
                "limitations": result.limitations,
                "recommendations": result.recommendations,
            }, f, indent=2, default=str)
    
    def get_relevant_knowledge(self, topic: str) -> List[Dict[str, Any]]:
        """
        Retrieve relevant knowledge from other researchers.
        
        Args:
            topic: Topic of interest (e.g., "lstm", "attention", "regime")
            
        Returns:
            List of relevant knowledge contributions
        """
        if not self.knowledge_base:
            self._load_knowledge_base()
        
        relevant = []
        for contrib in self.knowledge_base.get("contributions", []):
            # Simple keyword matching (could be enhanced with embeddings)
            contrib_text = json.dumps(contrib).lower()
            if topic.lower() in contrib_text:
                relevant.append(contrib)
        
        return relevant
    
    def _load_knowledge_base(self):
        """Load shared knowledge base."""
        kb_path = self.results_dir / "knowledge_base.json"
        if kb_path.exists():
            try:
                with open(kb_path) as f:
                    self.knowledge_base = json.load(f)
            except Exception:
                self.knowledge_base = {}
