"""
GNN On-Chain Risk Scorer — Whale-Cluster Detection via Graph Convolution
=========================================================================
A simplified Graph Neural Network that analyzes on-chain data to produce
"whale-cluster risk" scores. Uses aggregated node categories (retail, whales,
exchanges, miners) instead of individual wallet addresses.

Architecture:
  - Fetch on-chain metrics from free APIs (blockchain.info, CoinGecko)
  - Build a simplified flow graph (4 nodes: retail, whales, exchanges, miners)
  - 2-layer GCN: H' = ReLU(A_norm @ H @ W)  with symmetric normalization
  - Mean pooling readout -> output layer -> sigmoid -> risk score (0-1)

Risk Levels:
  0.00-0.25  LOW      Normal on-chain activity, safe to trade
  0.25-0.50  MEDIUM   Elevated whale activity, use caution
  0.50-0.75  HIGH     Significant whale movements, reduce exposure
  0.75-1.00  EXTREME  Massive on-chain flows, likely imminent dump/pump

Dependencies: numpy + requests ONLY. Runs on GitHub Actions Python 3.11.

Author: Antigravity ML Research
"""

import numpy as np
import requests
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NODE_RETAIL = 0
NODE_WHALES = 1
NODE_EXCHANGES = 2
NODE_MINERS = 3
NODE_NAMES = ["retail", "whales", "exchanges", "miners"]
NUM_NODES = 4

# Feature indices per node
FEAT_VOLUME = 0       # Normalized transaction volume
FEAT_TX_COUNT = 1     # Normalized transaction count
FEAT_AVG_SIZE = 2     # Average transaction size (normalized)
FEAT_FLOW_DIR = 3     # Net flow direction (-1 outflow to +1 inflow)
INPUT_DIM = 4

RISK_THRESHOLDS = {
    "LOW": (0.0, 0.25),
    "MEDIUM": (0.25, 0.50),
    "HIGH": (0.50, 0.75),
    "EXTREME": (0.75, 1.0),
}

# Cache directory
_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
_CACHE_FILE = os.path.join(_CACHE_DIR, "onchain_cache.json")
_CACHE_TTL = 300  # 5 minutes

# Request timeout
_TIMEOUT = 10


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _sigmoid(x: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid."""
    return np.where(
        x >= 0,
        1.0 / (1.0 + np.exp(-x)),
        np.exp(x) / (1.0 + np.exp(x)),
    )


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0, x)


def _xavier_init(fan_in: int, fan_out: int,
                 rng: np.random.RandomState) -> np.ndarray:
    """Xavier/Glorot uniform initialization."""
    limit = np.sqrt(6.0 / (fan_in + fan_out))
    return rng.uniform(-limit, limit, (fan_in, fan_out)).astype(np.float64)


def _symmetric_normalize(adj: np.ndarray) -> np.ndarray:
    """Compute D^(-1/2) A D^(-1/2) symmetric normalization."""
    # Add self-loops
    A = adj + np.eye(adj.shape[0])
    D = np.diag(A.sum(axis=1))
    D_inv_sqrt = np.diag(1.0 / np.sqrt(np.maximum(D.diagonal(), 1e-12)))
    return D_inv_sqrt @ A @ D_inv_sqrt


def _normalize_metric(value: float, baseline: float,
                      scale: float = 1.0) -> float:
    """Normalize a metric relative to a baseline, clamped to [-1, 1]."""
    if baseline <= 0:
        return 0.0
    ratio = (value - baseline) / baseline
    return float(np.clip(ratio * scale, -1.0, 1.0))


# ---------------------------------------------------------------------------
# Data Collection
# ---------------------------------------------------------------------------

def _load_cache() -> Dict:
    """Load cached on-chain data if fresh."""
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, "r") as f:
                cache = json.load(f)
            if time.time() - cache.get("_ts", 0) < _CACHE_TTL:
                return cache
    except Exception:
        pass
    return {}


def _save_cache(data: Dict) -> None:
    """Persist on-chain data to disk cache."""
    try:
        os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
        data["_ts"] = time.time()
        with open(_CACHE_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def fetch_onchain_metrics(symbol: str = "BTC") -> Dict:
    """
    Fetch on-chain metrics from free APIs.

    Sources:
      - blockchain.info (BTC-specific: tx volume, hash rate, n_tx)
      - CoinGecko (market data, volume, market cap for any coin)

    Returns dict with keys:
      active_addresses_proxy, transaction_volume, exchange_inflow,
      exchange_outflow, large_tx_count, total_tx_count, price,
      market_cap, volume_24h, price_change_24h
    """
    sym = symbol.upper()
    cache = _load_cache()
    cache_key = f"metrics_{sym}"
    if cache_key in cache:
        return cache[cache_key]

    metrics = _default_metrics(sym)

    # --- Blockchain.info (BTC only) ---
    if sym == "BTC":
        metrics = _fetch_blockchain_info(metrics)

    # --- CoinGecko (all coins) ---
    metrics = _fetch_coingecko(sym, metrics)

    # Derive large tx proxy: if BTC, estimate from volume vs tx count
    if metrics["total_tx_count"] > 0 and metrics["transaction_volume"] > 0:
        avg_tx_size = metrics["transaction_volume"] / metrics["total_tx_count"]
        # "Large" = transactions > 10x the average
        metrics["large_tx_count"] = int(
            metrics["total_tx_count"] * 0.02  # ~2% are whale-sized
            * (avg_tx_size / max(metrics.get("_baseline_avg_tx", avg_tx_size), 1e-9))
        )

    # Exchange flow proxy from volume
    if metrics["volume_24h"] > 0:
        metrics["exchange_inflow"] = metrics["volume_24h"] * 0.35
        metrics["exchange_outflow"] = metrics["volume_24h"] * 0.30

    # Cache result
    cache[cache_key] = metrics
    _save_cache(cache)

    return metrics


def _default_metrics(symbol: str) -> Dict:
    """Return fallback/estimated metrics when APIs fail."""
    defaults = {
        "BTC": {
            "active_addresses_proxy": 900_000,
            "transaction_volume": 30_000_000_000,
            "exchange_inflow": 10_500_000_000,
            "exchange_outflow": 9_000_000_000,
            "large_tx_count": 8_500,
            "total_tx_count": 350_000,
            "price": 85_000,
            "market_cap": 1_650_000_000_000,
            "volume_24h": 30_000_000_000,
            "price_change_24h": 0.0,
            "_baseline_avg_tx": 85_714,
            "_baseline_volume": 28_000_000_000,
            "_baseline_large_tx": 8_000,
            "_baseline_active_addr": 950_000,
        },
        "ETH": {
            "active_addresses_proxy": 500_000,
            "transaction_volume": 12_000_000_000,
            "exchange_inflow": 4_200_000_000,
            "exchange_outflow": 3_600_000_000,
            "large_tx_count": 5_200,
            "total_tx_count": 1_200_000,
            "price": 3_200,
            "market_cap": 385_000_000_000,
            "volume_24h": 12_000_000_000,
            "price_change_24h": 0.0,
            "_baseline_avg_tx": 10_000,
            "_baseline_volume": 11_000_000_000,
            "_baseline_large_tx": 4_800,
            "_baseline_active_addr": 520_000,
        },
        "SOL": {
            "active_addresses_proxy": 1_500_000,
            "transaction_volume": 3_000_000_000,
            "exchange_inflow": 1_050_000_000,
            "exchange_outflow": 900_000_000,
            "large_tx_count": 2_800,
            "total_tx_count": 40_000_000,
            "price": 140,
            "market_cap": 60_000_000_000,
            "volume_24h": 3_000_000_000,
            "price_change_24h": 0.0,
            "_baseline_avg_tx": 75,
            "_baseline_volume": 2_800_000_000,
            "_baseline_large_tx": 2_500,
            "_baseline_active_addr": 1_600_000,
        },
    }
    base = defaults.get(symbol, defaults["BTC"]).copy()
    base["symbol"] = symbol
    base["source"] = "fallback"
    return base


def _fetch_blockchain_info(metrics: Dict) -> Dict:
    """Fetch BTC-specific data from blockchain.info."""
    try:
        stats = requests.get(
            "https://api.blockchain.info/stats", timeout=_TIMEOUT
        ).json()
        metrics["total_tx_count"] = stats.get("n_tx", metrics["total_tx_count"])
        metrics["transaction_volume"] = stats.get(
            "trade_volume_usd", metrics["transaction_volume"]
        )
        # Hash rate can proxy miner activity
        metrics["_hash_rate"] = stats.get("hash_rate", 0)
        metrics["source"] = "blockchain.info"
    except Exception:
        pass

    # Transaction count from charts endpoint (24h)
    try:
        resp = requests.get(
            "https://api.blockchain.info/charts/n-unique-addresses"
            "?timespan=2days&format=json",
            timeout=_TIMEOUT,
        ).json()
        values = resp.get("values", [])
        if values:
            metrics["active_addresses_proxy"] = int(values[-1].get("y", 0))
    except Exception:
        pass

    return metrics


def _fetch_coingecko(symbol: str, metrics: Dict) -> Dict:
    """Fetch market data from CoinGecko free API."""
    coin_map = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "DOGE": "dogecoin",
        "XRP": "ripple",
        "ADA": "cardano",
        "AVAX": "avalanche-2",
        "DOT": "polkadot",
        "LINK": "chainlink",
        "MATIC": "matic-network",
    }
    coin_id = coin_map.get(symbol, symbol.lower())

    try:
        url = (
            f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            "?localization=false&tickers=false&community_data=false"
            "&developer_data=false"
        )
        data = requests.get(url, timeout=_TIMEOUT).json()
        md = data.get("market_data", {})

        metrics["price"] = md.get("current_price", {}).get(
            "usd", metrics["price"]
        )
        metrics["market_cap"] = md.get("market_cap", {}).get(
            "usd", metrics["market_cap"]
        )
        metrics["volume_24h"] = md.get("total_volume", {}).get(
            "usd", metrics["volume_24h"]
        )
        metrics["price_change_24h"] = md.get(
            "price_change_percentage_24h", 0.0
        )
        if metrics["source"] == "fallback":
            metrics["source"] = "coingecko"
        else:
            metrics["source"] += "+coingecko"
    except Exception:
        pass

    return metrics


# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------

def build_flow_graph(
    metrics: Dict,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build a simplified flow graph from on-chain metrics.

    Nodes (4):
      0: retail   — small transactions
      1: whales   — large transactions
      2: exchanges — known exchange flows
      3: miners   — block reward recipients (BTC) / validators

    Returns:
      adj_matrix  (4, 4) — edge weights (transaction volume between categories)
      features    (4, 4) — node feature matrix
    """
    vol = metrics.get("transaction_volume", 1.0)
    inflow = metrics.get("exchange_inflow", 0.0)
    outflow = metrics.get("exchange_outflow", 0.0)
    large_tx = metrics.get("large_tx_count", 0)
    total_tx = max(metrics.get("total_tx_count", 1), 1)
    active_addr = metrics.get("active_addresses_proxy", 1)
    price_chg = metrics.get("price_change_24h", 0.0)

    baseline_vol = metrics.get("_baseline_volume", vol)
    baseline_large = metrics.get("_baseline_large_tx", max(large_tx, 1))
    baseline_addr = metrics.get("_baseline_active_addr", active_addr)

    # --- Adjacency matrix (flow weights, normalized to [0, 1]) ---
    adj = np.zeros((NUM_NODES, NUM_NODES), dtype=np.float64)

    # Retail <-> Exchange (deposit/withdraw)
    retail_exchange = min(inflow * 0.6 / max(vol, 1e-9), 1.0)
    adj[NODE_RETAIL, NODE_EXCHANGES] = retail_exchange
    adj[NODE_EXCHANGES, NODE_RETAIL] = min(outflow * 0.6 / max(vol, 1e-9), 1.0)

    # Whale <-> Exchange (large deposits/withdrawals)
    whale_exchange = min(inflow * 0.4 / max(vol, 1e-9), 1.0)
    adj[NODE_WHALES, NODE_EXCHANGES] = whale_exchange
    adj[NODE_EXCHANGES, NODE_WHALES] = min(outflow * 0.4 / max(vol, 1e-9), 1.0)

    # Miners -> Exchange (selling) and Miners -> Retail (OTC)
    miner_sell_ratio = 0.15  # Miners typically sell ~15% of rewards
    adj[NODE_MINERS, NODE_EXCHANGES] = miner_sell_ratio
    adj[NODE_MINERS, NODE_RETAIL] = 0.05

    # Whale <-> Retail (OTC / large market orders)
    whale_retail = large_tx / max(total_tx, 1)
    adj[NODE_WHALES, NODE_RETAIL] = min(whale_retail * 2, 1.0)
    adj[NODE_RETAIL, NODE_WHALES] = min(whale_retail, 1.0)

    # --- Feature matrix (4 features per node) ---
    features = np.zeros((NUM_NODES, INPUT_DIM), dtype=np.float64)

    # Retail node
    retail_tx = total_tx - large_tx
    features[NODE_RETAIL, FEAT_VOLUME] = _normalize_metric(
        vol * 0.6, baseline_vol * 0.6
    )
    features[NODE_RETAIL, FEAT_TX_COUNT] = _normalize_metric(
        retail_tx, total_tx * 0.98
    )
    features[NODE_RETAIL, FEAT_AVG_SIZE] = 0.0  # baseline by definition
    features[NODE_RETAIL, FEAT_FLOW_DIR] = np.clip(price_chg / 10.0, -1, 1)

    # Whale node
    features[NODE_WHALES, FEAT_VOLUME] = _normalize_metric(
        vol * 0.4, baseline_vol * 0.4
    )
    features[NODE_WHALES, FEAT_TX_COUNT] = _normalize_metric(
        large_tx, baseline_large
    )
    features[NODE_WHALES, FEAT_AVG_SIZE] = _normalize_metric(
        large_tx, baseline_large, scale=1.5
    )
    # Whale flow direction: net exchange inflow = selling pressure
    net_flow = (inflow - outflow) / max(inflow + outflow, 1e-9)
    features[NODE_WHALES, FEAT_FLOW_DIR] = np.clip(net_flow, -1, 1)

    # Exchange node
    features[NODE_EXCHANGES, FEAT_VOLUME] = _normalize_metric(
        inflow + outflow, baseline_vol * 0.65
    )
    features[NODE_EXCHANGES, FEAT_TX_COUNT] = _normalize_metric(
        total_tx * 0.3, total_tx * 0.28
    )
    features[NODE_EXCHANGES, FEAT_AVG_SIZE] = _normalize_metric(
        (inflow + outflow) / max(total_tx * 0.3, 1), baseline_vol / total_tx
    )
    features[NODE_EXCHANGES, FEAT_FLOW_DIR] = np.clip(net_flow * 1.5, -1, 1)

    # Miner node
    features[NODE_MINERS, FEAT_VOLUME] = 0.0
    features[NODE_MINERS, FEAT_TX_COUNT] = 0.0
    features[NODE_MINERS, FEAT_AVG_SIZE] = 0.0
    features[NODE_MINERS, FEAT_FLOW_DIR] = -miner_sell_ratio  # Slight outflow

    return adj, features


# ---------------------------------------------------------------------------
# GNN Model (numpy-only)
# ---------------------------------------------------------------------------

class GraphConvLayer:
    """
    Simple Graph Convolutional Layer.

    Computes: H' = ReLU(A_norm @ H @ W + b)

    Where A_norm = D^(-1/2) (A + I) D^(-1/2) is the symmetric-normalized
    adjacency matrix with self-loops.
    """

    def __init__(self, in_features: int, out_features: int,
                 rng: np.random.RandomState):
        self.W = _xavier_init(in_features, out_features, rng)
        self.b = np.zeros(out_features, dtype=np.float64)
        self.in_features = in_features
        self.out_features = out_features

    def forward(self, A_norm: np.ndarray, H: np.ndarray) -> np.ndarray:
        """
        Forward pass.

        Args:
            A_norm: (N, N) normalized adjacency matrix
            H: (N, in_features) node feature matrix

        Returns:
            (N, out_features) updated node representations
        """
        # Message passing: aggregate neighbor features
        support = H @ self.W + self.b          # (N, out_features)
        out = A_norm @ support                 # (N, out_features)
        return _relu(out)

    def get_params(self) -> Dict[str, np.ndarray]:
        return {"W": self.W, "b": self.b}

    def set_params(self, params: Dict[str, np.ndarray]) -> None:
        self.W = params["W"]
        self.b = params["b"]


class GNNOnChainScorer:
    """
    Graph Neural Network for on-chain risk scoring.

    Uses a 2-layer GCN with mean-pooling readout to produce a single
    risk score in [0, 1]. Weights are initialized with heuristic rules
    that encode domain knowledge about whale/exchange flow patterns.
    """

    def __init__(
        self,
        input_dim: int = INPUT_DIM,
        hidden_dim: int = 16,
        output_dim: int = 1,
        n_layers: int = 2,
        seed: int = 42,
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.n_layers = n_layers
        self.rng = np.random.RandomState(seed)

        # Build GCN layers
        self.layers: List[GraphConvLayer] = []
        dims = [input_dim] + [hidden_dim] * (n_layers - 1)
        for i in range(n_layers):
            in_d = dims[i]
            out_d = hidden_dim
            self.layers.append(GraphConvLayer(in_d, out_d, self.rng))

        # Output projection: hidden_dim -> 1
        self.W_out = _xavier_init(hidden_dim, output_dim, self.rng)
        self.b_out = np.zeros(output_dim, dtype=np.float64)

        # Apply heuristic weight initialization
        self._init_heuristic_weights()

    def _init_heuristic_weights(self) -> None:
        """
        Initialize weights with heuristic rules encoding domain knowledge.

        Since we cannot train on labeled on-chain risk data, we encode
        known risk signals directly into the weight matrices:
          - Exchange inflow spikes -> higher risk
          - Large transaction count spikes -> higher risk
          - Active address decline -> higher risk
          - Volume spike with price decline -> distribution risk
        """
        # Layer 0: map raw features to hidden space
        # We want the model to amplify:
        #   - FEAT_FLOW_DIR (whale net inflow to exchange = selling)
        #   - FEAT_TX_COUNT (whale tx spike)
        #   - FEAT_VOLUME (volume spike)
        W0 = self.layers[0].W
        W0[:, :] = 0.0

        # Create 4 "detector" channels per feature
        for feat_idx in range(self.input_dim):
            # Each input feature activates a group of hidden neurons
            base = feat_idx * (self.hidden_dim // self.input_dim)
            span = self.hidden_dim // self.input_dim
            for j in range(span):
                W0[feat_idx, base + j] = 0.3 + 0.1 * j

        # Boost whale-related features
        # FEAT_FLOW_DIR (idx 3) is the most important risk signal
        flow_base = FEAT_FLOW_DIR * (self.hidden_dim // self.input_dim)
        for j in range(self.hidden_dim // self.input_dim):
            W0[FEAT_FLOW_DIR, flow_base + j] *= 2.0

        # FEAT_TX_COUNT (idx 1) for whale tx spikes
        tx_base = FEAT_TX_COUNT * (self.hidden_dim // self.input_dim)
        for j in range(self.hidden_dim // self.input_dim):
            W0[FEAT_TX_COUNT, tx_base + j] *= 1.5

        self.layers[0].W = W0

        # Layer 1: cross-node feature mixing (keep Xavier but scale down)
        self.layers[1].W *= 0.5

        # Output layer: positive weights so higher hidden activations -> higher risk
        self.W_out[:, 0] = 0.15

    def forward(
        self, adj_matrix: np.ndarray, features: np.ndarray
    ) -> float:
        """
        Forward pass through the GNN.

        Args:
            adj_matrix: (N, N) adjacency matrix
            features:   (N, input_dim) node feature matrix

        Returns:
            risk_score: float in [0, 1]
        """
        A_norm = _symmetric_normalize(adj_matrix)
        H = features.copy()

        # GCN layers
        for layer in self.layers:
            H = layer.forward(A_norm, H)

        # Readout: mean pooling over all nodes
        graph_embedding = H.mean(axis=0)  # (hidden_dim,)

        # Output projection + sigmoid
        logit = graph_embedding @ self.W_out + self.b_out  # (1,)
        score = float(_sigmoid(logit[0]))

        return score

    def _compute_component_scores(self, metrics: Dict) -> Dict[str, float]:
        """
        Compute interpretable component scores from raw metrics.

        Returns dict of named risk components in [0, 1].
        """
        baseline_vol = metrics.get("_baseline_volume", 1)
        baseline_large = metrics.get("_baseline_large_tx", 1)
        baseline_addr = metrics.get("_baseline_active_addr", 1)

        vol = metrics.get("transaction_volume", 0)
        inflow = metrics.get("exchange_inflow", 0)
        outflow = metrics.get("exchange_outflow", 0)
        large_tx = metrics.get("large_tx_count", 0)
        active_addr = metrics.get("active_addresses_proxy", 1)
        price_chg = metrics.get("price_change_24h", 0.0)

        # 1. Exchange inflow spike
        inflow_ratio = inflow / max(baseline_vol * 0.35, 1e-9)
        exchange_inflow_risk = float(np.clip((inflow_ratio - 1.0) * 2.0, 0, 1))

        # 2. Large transaction spike
        large_tx_ratio = large_tx / max(baseline_large, 1)
        whale_tx_risk = float(np.clip((large_tx_ratio - 1.0) * 1.5, 0, 1))

        # 3. Active address decline (fewer participants = whale-dominated)
        addr_ratio = active_addr / max(baseline_addr, 1)
        addr_decline_risk = float(np.clip((1.0 - addr_ratio) * 3.0, 0, 1))

        # 4. Volume spike + price decline (distribution pattern)
        vol_ratio = vol / max(baseline_vol, 1e-9)
        distribution_risk = 0.0
        if vol_ratio > 1.1 and price_chg < -1.0:
            distribution_risk = float(
                np.clip((vol_ratio - 1.0) * abs(price_chg) / 10.0, 0, 1)
            )

        # 5. Net exchange flow imbalance (inflow >> outflow = selling)
        net_flow = (inflow - outflow) / max(inflow + outflow, 1e-9)
        flow_imbalance_risk = float(np.clip(net_flow * 2.0, 0, 1))

        return {
            "exchange_inflow_spike": round(exchange_inflow_risk, 4),
            "whale_tx_spike": round(whale_tx_risk, 4),
            "active_address_decline": round(addr_decline_risk, 4),
            "distribution_pattern": round(distribution_risk, 4),
            "flow_imbalance": round(flow_imbalance_risk, 4),
        }

    def predict(self, symbol: str = "BTC") -> Dict:
        """
        Full prediction pipeline: fetch data -> build graph -> score.

        Returns:
            {
                symbol, risk_score, risk_level, component_scores,
                signals, metrics_source, generated_at
            }
        """
        # 1. Fetch on-chain metrics
        metrics = fetch_onchain_metrics(symbol)

        # 2. Build flow graph
        adj, features = build_flow_graph(metrics)

        # 3. GNN forward pass
        gnn_score = self.forward(adj, features)

        # 4. Heuristic component scores
        components = self._compute_component_scores(metrics)

        # 5. Blend GNN score with heuristic composite for robustness
        heuristic_score = np.mean(list(components.values()))
        # 60% GNN + 40% heuristic blend
        final_score = 0.6 * gnn_score + 0.4 * heuristic_score
        final_score = float(np.clip(final_score, 0.0, 1.0))

        # 6. Determine risk level
        risk_level = "LOW"
        for level, (lo, hi) in RISK_THRESHOLDS.items():
            if lo <= final_score < hi:
                risk_level = level
                break
        if final_score >= 0.75:
            risk_level = "EXTREME"

        # 7. Generate signals
        signals = []
        if final_score > 0.5:
            signals.append({
                "type": "WARNING",
                "message": (
                    f"{symbol} on-chain risk is {risk_level} ({final_score:.2f}). "
                    f"Whale-cluster activity detected."
                ),
            })
        if components["exchange_inflow_spike"] > 0.5:
            signals.append({
                "type": "EXCHANGE_INFLOW",
                "message": (
                    f"{symbol} exchange inflow spike detected "
                    f"(score: {components['exchange_inflow_spike']:.2f}). "
                    f"Potential selling pressure."
                ),
            })
        if components["distribution_pattern"] > 0.3:
            signals.append({
                "type": "DISTRIBUTION",
                "message": (
                    f"{symbol} distribution pattern: volume up + price down "
                    f"(score: {components['distribution_pattern']:.2f})."
                ),
            })
        if components["active_address_decline"] > 0.4:
            signals.append({
                "type": "ADDR_DECLINE",
                "message": (
                    f"{symbol} active addresses declining "
                    f"(score: {components['active_address_decline']:.2f}). "
                    f"Market becoming whale-dominated."
                ),
            })

        return {
            "symbol": symbol,
            "risk_score": round(final_score, 4),
            "risk_level": risk_level,
            "gnn_raw_score": round(gnn_score, 4),
            "component_scores": components,
            "signals": signals,
            "metrics_source": metrics.get("source", "unknown"),
            "price": metrics.get("price", 0),
            "price_change_24h": metrics.get("price_change_24h", 0),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def save(self, path: str) -> None:
        """Save model weights to .npz file."""
        params = {}
        for i, layer in enumerate(self.layers):
            lp = layer.get_params()
            params[f"layer_{i}_W"] = lp["W"]
            params[f"layer_{i}_b"] = lp["b"]
        params["W_out"] = self.W_out
        params["b_out"] = self.b_out
        params["config"] = np.array([
            self.input_dim, self.hidden_dim, self.output_dim, self.n_layers
        ])
        np.savez(path, **params)

    def load(self, path: str) -> None:
        """Load model weights from .npz file."""
        data = np.load(path)
        config = data["config"].astype(int)
        assert config[0] == self.input_dim, "input_dim mismatch"
        assert config[1] == self.hidden_dim, "hidden_dim mismatch"

        for i, layer in enumerate(self.layers):
            layer.set_params({
                "W": data[f"layer_{i}_W"],
                "b": data[f"layer_{i}_b"],
            })
        self.W_out = data["W_out"]
        self.b_out = data["b_out"]


# ---------------------------------------------------------------------------
# Signal Generation (multi-symbol)
# ---------------------------------------------------------------------------

def generate_signals(
    symbols: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Generate risk signals for multiple symbols.

    Default symbols: BTC, ETH, SOL.

    Returns list of pick-format dicts for symbols with risk > 0.5.
    """
    if symbols is None:
        symbols = ["BTC", "ETH", "SOL"]

    scorer = GNNOnChainScorer()
    results = []

    for sym in symbols:
        try:
            pred = scorer.predict(sym)
            pick = {
                "symbol": pred["symbol"],
                "direction": "SELL" if pred["risk_score"] > 0.5 else "HOLD",
                "confidence": round(pred["risk_score"] * 100, 1),
                "strategy": "gnn_onchain_risk",
                "risk_score": pred["risk_score"],
                "risk_level": pred["risk_level"],
                "reason": (
                    pred["signals"][0]["message"]
                    if pred["signals"]
                    else f"{sym} on-chain risk: {pred['risk_level']} "
                         f"({pred['risk_score']:.2f})"
                ),
                "generated_at": pred["generated_at"],
            }
            results.append(pick)
        except Exception as e:
            results.append({
                "symbol": sym,
                "direction": "HOLD",
                "confidence": 0.0,
                "strategy": "gnn_onchain_risk",
                "risk_score": 0.0,
                "risk_level": "UNKNOWN",
                "reason": f"Error scoring {sym}: {str(e)}",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })

    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    symbols = sys.argv[1:] if len(sys.argv) > 1 else ["BTC", "ETH", "SOL"]
    scorer = GNNOnChainScorer()

    for sym in symbols:
        result = scorer.predict(sym)
        print(f"\n{'='*60}")
        print(f"  {sym} On-Chain Risk Assessment")
        print(f"{'='*60}")
        print(f"  Risk Score : {result['risk_score']:.4f}")
        print(f"  Risk Level : {result['risk_level']}")
        print(f"  GNN Raw    : {result['gnn_raw_score']:.4f}")
        print(f"  Price      : ${result['price']:,.2f}")
        print(f"  24h Change : {result['price_change_24h']:+.2f}%")
        print(f"  Source     : {result['metrics_source']}")
        print(f"\n  Component Scores:")
        for k, v in result["component_scores"].items():
            bar = "#" * int(v * 20)
            print(f"    {k:30s} {v:.4f} |{bar}")
        if result["signals"]:
            print(f"\n  Signals:")
            for sig in result["signals"]:
                print(f"    [{sig['type']}] {sig['message']}")
        print(f"\n  Generated: {result['generated_at']}")
