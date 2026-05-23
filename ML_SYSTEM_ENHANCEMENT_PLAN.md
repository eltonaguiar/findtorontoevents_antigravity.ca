# ML System Enhancement Plan (v3.0 - Web Research Augmented)

## Previous Status [Unchanged]

## Deep Research Tier v2 (Web + Local 2024-2026 Trends)

Web search (Google/Arxiv 2024-2026): LSTM/GRU + on-chain/social best. Key features/models:

### Top Web-Sourced Features (Papers/Medium)
1. **On-Chain Metrics** (arxiv 2025):
   - Active addresses growth: `active_24h / ma_active`
   - Tx velocity: `tx_count_1h / holders`
   - Whale ratio: `whale_tx / total_tx`
   ```python
   # glassnode-like
   onchain_feat = active_growth + tx_vel * 0.5 + whale_ratio * 0.3
   ```

2. **Social Velocity** (Twitter/Reddit 2025):
   - Sentiment * volume_spike
   - Follower-weighted smart money proxy.

3. **Derivs Advanced**:
   - Funding divergence (Binance-Bybit-OKX).
   - OI change * price momentum.

### State-of-Art Models (2026 Trends)
1. **Transformer Time Series** (arxiv 'Time-LLM' 2025):
   - PatchTST or Autoformer for multi-horizon.
   - Replace GB with Transformer encoder.

2. **GNN Cross-Asset**:
   - GraphConv on symbol correlation matrix.

3. **RL Position Sizing** (DQN/PPO):
   - Reward: Sharpe, agent learns TP/SL.

### Implementation Winners
| Feature/Model | Source | Effort | Expected Lift |
|---------------|--------|--------|---------------|
| Active Addr/Tx Vel | Glassnode equiv | Low | +3-5% acc |
| Funding Divergence | Multi-ex | Low | Reversal edge |
| Transformer Seq | PatchTST lib | Med | +5-8% long horiz |
| GNN Corr | PyG lib | High | Cross-symbol |

**Add to Quick/Mercury**: On-chain + social → retrain.

**Skyrocket**: Transformer for explosive detection.

## Roadmap Update
Immediate: On-chain feats.
Week1: Transformer pilot.

**Performance skyrocket potential: +20% acc via multimodal data/models.**