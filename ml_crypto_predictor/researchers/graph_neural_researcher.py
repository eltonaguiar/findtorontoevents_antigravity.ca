"""
GraphNeuralResearcher — Graph Neural Networks for Crypto Correlation Networks
==============================================================================

Specializes in graph-based deep learning for cryptocurrency analysis:
  - Graph Neural Networks (GNN) for cross-asset correlation
  - Graph Attention Networks (GAT) for dynamic relationship learning
  - Heterogeneous graphs (different node types: coins, exchanges, entities)
  - Temporal Graph Networks (TGN) for evolving relationships
  - Knowledge Graph Embeddings for on-chain data integration

Academic foundations:
  - "Graph Neural Networks: A Review of Methods and Applications" (Zhang et al., 2021)
  - "Temporal Graph Networks for Dynamic Graphs" (Rossi et al., 2020)
  - "Heterogeneous Graph Neural Networks" (Wang et al., 2021)
  - "GAT: Graph Attention Networks" (Veličković et al., 2018)

Key research questions:
  1. Can GNNs capture cross-crypto correlation structures better than traditional correlation?
  2. Does dynamic graph updating improve prediction accuracy?
  3. Can heterogeneous graphs incorporate on-chain metrics (exchange flows, whale movements)?
  4. How does graph structure evolve during market regime changes?
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np
import pandas as pd

from .base import Researcher, ResearchQuestion, ResearchResult

try:
    import torch
    import torch.nn as nn
    import torch_geometric.nn as pyg_nn
    from torch_geometric.data import Data, Batch
    HAS_TORCH_GEOM = True
except ImportError:
    HAS_TORCH_GEOM = False


class GraphNeuralResearcher(Researcher):
    """
    Researcher specializing in Graph Neural Networks for crypto analysis.
    
    Investigates graph-based approaches to model relationships between
    cryptocurrencies, on-chain entities, and market dynamics.
    """
    
    researcher_id = "graph_neural"
    name = "Graph Neural Researcher"
    specialization = "Graph neural networks (GNN, GAT, heterogeneous graphs)"
    literature = [
        "Graph Neural Networks: A Review (Zhang et al., 2021)",
        "Graph Attention Networks (Veličković et al., 2018)",
        "Temporal Graph Networks (Rossi et al., 2020)",
        "Heterogeneous GNNs (Wang et al., 2021)",
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.base_dir = Path(config.get("base_dir", "ml_crypto_predictor")) if config else Path("ml_crypto_predictor")
        self.data_dir = self.base_dir / "data"
        self.models_dir = self.base_dir / "models" / "graph"
        self.results_dir = self.base_dir / "results" / "research" / "graph"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def formulate_questions(self) -> List[ResearchQuestion]:
        """Define research questions for Graph Neural Networks."""
        return [
            ResearchQuestion(
                id="gnn_001",
                title="Static Correlation Graph vs Dynamic Graph: Which is Better?",
                description="Build a static correlation graph (nodes=coins, edges=rolling correlation) "
                          "and compare with dynamic graph where edge weights update every bar. "
                          "Dynamic graphs should capture regime changes better.",
                hypothesis="Dynamic graph construction will improve prediction AUC by 3-5% "
                          "because correlation structures change during bull/bear transitions. "
                          "Static graphs are too rigid for crypto markets.",
                methodology="1. Compute rolling 24h returns for top 30 coins\n"
                          "2. Static graph: correlation matrix over entire training period\n"
                          "3. Dynamic graph: recompute correlation matrix per timestep\n"
                          "4. Train GCN (Graph Convolutional Network) on both\n"
                          "5. Compare performance on test set\n"
                          "6. Analyze if dynamic graphs capture regime shifts",
                success_criteria={
                    "dynamic_better_than_static": True,
                    "auc_improvement": 0.03,
                    "captures_regime_changes": True,
                },
                priority=1,
            ),
            ResearchQuestion(
                id="gnn_002",
                title="Graph Attention Networks (GAT) for Weighted Relationships",
                description="Use GAT to learn attention weights between coins instead of "
                          "predefined correlation. Does the learned attention match known "
                          "market narratives (e.g., BTC-ETH correlation, meme coin clusters)?",
                hypothesis="GAT will learn meaningful attention patterns: "
                          "- BTC gets attention from all coins (market driver)\n"
                          "- Meme coins cluster together (DOGE, SHIB, PEPE)\n"
                          "- DeFi tokens form another cluster (UNI, AAVE)\n"
                          "These emergent structures will improve predictions.",
                methodology="1. Build initial graph with all-to-all edges (fully connected)\n"
                          "2. Use GAT with 2-3 attention heads\n"
                          "3. Train end-to-end for prediction\n"
                          "4. Extract attention weights and visualize per timeframe\n"
                          "5. Compare attention patterns across bull/bear markets\n"
                          "6. Correlate attention clusters with known sector rotations",
                success_criteria={
                    "attention_clusters_match_sectors": True,
                    "gat_beats_gcn": True,
                    "improvement_over_gcn": 0.02,
                },
                priority=1,
                dependencies=["gnn_001"],
            ),
            ResearchQuestion(
                id="gnn_003",
                title="Heterogeneous Graph: Coins + Exchanges + On-Chain Entities",
                description="Expand beyond coin-coin graphs to include exchange wallets, "
                          "whale addresses, and DeFi protocols as different node types. "
                          "Use heterogeneous GNN to propagate signals across node types.",
                hypothesis="Incorporating on-chain entities (exchange flows, whale movements) "
                          "will improve prediction accuracy by 5-8% because these are leading "
                          "indicators of price movements (smart money flows).",
                methodology="1. Construct heterogeneous graph with node types:\n"
                          "   - Coin nodes (30 cryptos)\n"
                          "   - Exchange wallet nodes (Binance, Coinbase)\n"
                          "   - Whale address nodes (top 100 holders)\n"
                          "   - DeFi protocol nodes (Uniswap, Aave)\n"
                          "2. Edges: transactions, correlations, holdings\n"
                          "3. Use RGCN (Relational GCN) to handle edge types\n"
                          "4. Predict coin price movements using graph embeddings\n"
                          "5. Ablate: remove non-coin nodes to measure contribution",
                success_criteria={
                    "heterogeneous_better_than_homogeneous": True,
                    "onchain_nodes_add_value": True,
                    "auc_improvement": 0.05,
                },
                priority=2,
                dependencies=["gnn_002"],
            ),
            ResearchQuestion(
                id="gnn_004",
                title="Temporal Graph Networks for Evolving Correlation Structures",
                description="Implement a Temporal Graph Network (TGN) that maintains "
                          "memory of past graph states. Test if capturing temporal evolution "
                          "of correlations improves long-horizon predictions (4h, 1d).",
                hypothesis="TGN will outperform static/dynamic GNNs on 4h and 1d timeframes "
                          "because it explicitly models how relationships evolve over time. "
                          "Expected AUC improvement: 4-6% on daily timeframe.",
                methodology="1. Implement TGN with memory module (GRU-based)\n"
                          "2. Build graph snapshots every 1h\n"
                          "3. Propagate messages between snapshots\n"
                          "4. Use memory state to inform next prediction\n"
                          "5. Compare with non-temporal GNN baselines\n"
                          "6. Visualize how edge weights change over time",
                success_criteria={
                    "tgn_best_on_long_timeframes": True,
                    "memory_helps": True,
                    "improvement_4h_1d": 0.04,
                },
                priority=2,
                dependencies=["gnn_001", "gnn_002"],
            ),
            ResearchQuestion(
                id="gnn_005",
                title="Graph Structure Learning: Can the Model Learn the Graph?",
                description="Instead of predefined correlation edges, use structure learning "
                          "(e.g., Graph Convolutional Matrix Completion) to infer the graph "
                          "directly from data. Does learned graph match known market topology?",
                hypothesis="End-to-end graph structure learning will discover meaningful "
                          "relationships without human-defined correlations. The learned graph "
                          "will be sparse (only strong relationships) and stable across regimes.",
                methodology="1. Use Graph Structure Learning (GSL) to generate adjacency\n"
                          "2. Train GNN on learned graph in end-to-end fashion\n"
                          "3. Compare with correlation-based graph\n"
                          "4. Analyze sparsity and stability of learned edges\n"
                          "5. Check if learned edges correspond to known relationships\n"
                          "   (e.g., BTC-ETH, SOL-ETH, meme coin clusters)",
                success_criteria={
                    "gsl_matches_known_topology": True,
                    "sparsity_learned": True,  # Graph becomes sparse
                    "performance_comparable": True,
                },
                priority=3,
                dependencies=["gnn_001"],
            ),
        ]
    
    def prepare_data(self, question: ResearchQuestion) -> Dict[str, Any]:
        """Prepare graph data for GNN experiments."""
        from ml_crypto_predictor.enhanced_models.data_fetcher import fetch_klines
        from ml_crypto_predictor.enhanced_models.config import CRYPTO_PAIRS
        
        # Get top coins by market cap (first 10 for speed)
        pairs = CRYPTO_PAIRS[:10]
        timeframe = "1h"
        
        # Fetch data for all pairs
        price_data = {}
        for pair in pairs:
            df = fetch_klines(pair, "1h", 1000)
            if not df.empty:
                price_data[pair] = df["close"].pct_change().fillna(0)
        
        if len(price_data) < 5:
            return {"error": "insufficient_data"}
        
        # Build correlation matrix
        returns_df = pd.DataFrame(price_data)
        corr_matrix = returns_df.rolling(24).corr().iloc[-len(pairs):]  # Last 24h correlation
        
        # Create graph nodes (one per coin)
        node_features = []
        for pair in pairs:
            if pair in price_data:
                # Use last 24h of returns as node features
                features = price_data[pair].iloc[-24:].values
                node_features.append(features)
        
        node_features = np.array(node_features, dtype=np.float32)
        
        # Build edge index from correlation matrix
        edges = []
        edge_weights = []
        threshold = 0.3  # Only keep edges with |corr| > 0.3
        for i in range(len(pairs)):
            for j in range(len(pairs)):
                if i != j and abs(corr_matrix.iloc[i, j]) > threshold:
                    edges.append([i, j])
                    edge_weights.append(corr_matrix.iloc[i, j])
        
        edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous() if edges else torch.zeros((2, 0), dtype=torch.long)
        edge_attr = torch.tensor(edge_weights, dtype=torch.float32).unsqueeze(1) if edge_weights else torch.zeros((0, 1))
        
        # Build PyTorch Geometric Data object
        x = torch.tensor(node_features, dtype=torch.float32)
        data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr)
        
        return {
            "graph_data": data,
            "pairs": pairs,
            "n_nodes": len(pairs),
            "n_features": node_features.shape[1],
            "timeframe": timeframe,
        }
    
    def conduct_experiment(self, question: ResearchQuestion,
                          data: Dict[str, Any]) -> ResearchResult:
        """Run GNN experiments."""
        if not HAS_TORCH_GEOM:
            return ResearchResult(
                researcher_id=self.researcher_id,
                question_id=question.id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                findings="PyTorch Geometric not available. Cannot run GNN experiments.",
                metrics={},
                confidence=0.0,
                reproducible=False,
                limitations=["PyTorch Geometric dependency missing"],
            )
        
        if "error" in data:
            return ResearchResult(
                researcher_id=self.researcher_id,
                question_id=question.id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                findings=f"Data preparation failed: {data['error']}",
                metrics={},
                confidence=0.0,
            )
        
        if question.id == "gnn_001":
            result = self._run_static_vs_dynamic(question, data)
        elif question.id == "gnn_002":
            result = self._run_gat_experiment(question, data)
        elif question.id == "gnn_003":
            result = self._run_heterogeneous_graph(question, data)
        elif question.id == "gnn_004":
            result = self._run_temporal_gnn(question, data)
        elif question.id == "gnn_005":
            result = self._run_structure_learning(question, data)
        else:
            result = ResearchResult(
                researcher_id=self.researcher_id,
                question_id=question.id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                findings="Unknown question ID",
                metrics={},
                confidence=0.0,
            )
        
        return result
    
    def _run_static_vs_dynamic(self, question: ResearchQuestion,
                              data: Dict[str, Any]) -> ResearchResult:
        """Compare static vs dynamic graph construction."""
        findings = []
        
        # For this simplified version, we'll just demonstrate the concept
        graph_data = data["graph_data"]
        n_nodes = data["n_nodes"]
        
        findings.append(f"Graph built with {n_nodes} nodes")
        findings.append(f"Edges: {graph_data.edge_index.shape[1]}")
        
        # Simulate training a GCN
        model = self._build_gcn(graph_data.x.shape[1], hidden_dim=64)
        findings.append("GCN model built successfully")
        
        # In a full implementation, we would:
        # 1. Build static graph (fixed correlation)
        # 2. Build dynamic graph (updated per timestep)
        # 3. Train both and compare
        
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Static vs dynamic graph experiment initialized\n" + "\n".join(findings),
            metrics={"graph_nodes": n_nodes, "graph_edges": graph_data.edge_index.shape[1]},
            confidence=0.6,
            reproducible=True,
            limitations=["Simplified implementation", "Need full training pipeline"],
            recommendations={"next": "Implement full training loop with walk-forward validation"},
        )
    
    def _build_gcn(self, n_features: int, hidden_dim: int = 64) -> nn.Module:
        """Build a Graph Convolutional Network."""
        class GCN(nn.Module):
            def __init__(self, input_dim, hidden_dim):
                super().__init__()
                self.conv1 = pyg_nn.GCNConv(input_dim, hidden_dim)
                self.conv2 = pyg_nn.GCNConv(hidden_dim, hidden_dim)
                self.fc = nn.Linear(hidden_dim, 2)
                self.dropout = nn.Dropout(0.3)
            
            def forward(self, data):
                x, edge_index = data.x, data.edge_index
                x = torch.relu(self.conv1(x, edge_index))
                x = self.dropout(x)
                x = torch.relu(self.conv2(x, edge_index))
                x = self.fc(x.mean(dim=0, keepdim=True))  # Global pooling
                return x
        
        return GCN(n_features, hidden_dim)
    
    def _run_gat_experiment(self, question: ResearchQuestion,
                           data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="GAT experiment not yet fully implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_heterogeneous_graph(self, question: ResearchQuestion,
                                data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Heterogeneous graph experiment not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_temporal_gnn(self, question: ResearchQuestion,
                         data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Temporal GNN experiment not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def _run_structure_learning(self, question: ResearchQuestion,
                              data: Dict[str, Any]) -> ResearchResult:
        return ResearchResult(
            researcher_id=self.researcher_id,
            question_id=question.id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            findings="Graph structure learning not yet implemented",
            metrics={},
            confidence=0.3,
        )
    
    def validate_findings(self, result: ResearchResult) -> Dict[str, Any]:
        """Validate GNN results."""
        validation = {
            "confidence": 0.6,
            "reproducible": True,
            "limitations": [],
        }
        
        if result.metrics:
            n_nodes = result.metrics.get("graph_nodes", 0)
            if n_nodes < 5:
                validation["limitations"].append("Very small graph may not be representative")
                validation["confidence"] *= 0.7
        
        return validation
