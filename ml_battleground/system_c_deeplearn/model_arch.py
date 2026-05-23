"""
GRU-Attention architecture for System C: "The Neural Net".
Input: 60 bars x 16 features x 2 timeframes (15m and 1h)
Output: entry_prob (sigmoid), tp_dist (linear, min 0.5 ATR), sl_dist (linear, min 0.5 ATR)

Architecture:
  - GRU(128, 2 layers, dropout=0.3) per timeframe
  - Multi-Head Self-Attention (4 heads) across full GRU output sequences
  - Attentive pooling to aggregate sequence into fixed-size representation
  - 3 output heads: entry probability, TP distance, SL distance
"""

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    # Provide stub so the module can be imported without PyTorch
    class _StubModule:
        pass
    class nn:  # type: ignore[no-redef]
        Module = _StubModule

# Default sequence length — must match arch_config.json and train_model.py.
# Trained on 200-step sequences (4h bars = ~33 days of price history).
SEQ_LEN = 200


class GRUAttentionModel(nn.Module):
    """
    Dual-timeframe GRU with multi-head self-attention and 3 output heads.

    Parameters
    ----------
    input_size : int
        Number of features per bar (default 16).
    hidden_size : int
        GRU hidden dimension (default 128).
    num_layers : int
        Number of stacked GRU layers (default 2).
    n_heads : int
        Number of attention heads (default 4).
    dropout : float
        Dropout rate (default 0.3).
    """

    def __init__(
        self,
        input_size: int = 16,
        hidden_size: int = 128,
        num_layers: int = 2,
        n_heads: int = 4,
        dropout: float = 0.3,
    ):
        if not TORCH_AVAILABLE:
            raise ImportError(
                "PyTorch is required for System C. Install with: pip install torch>=2.1.0"
            )

        super().__init__()

        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.n_heads = n_heads

        # GRU encoder for 15-minute timeframe
        self.gru_15m = nn.GRU(
            input_size,
            hidden_size,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        # GRU encoder for 1-hour timeframe
        self.gru_1h = nn.GRU(
            input_size,
            hidden_size,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        # Multi-head self-attention across full GRU output sequences.
        # Applied to each timeframe's GRU outputs (embed_dim = hidden_size),
        # then the two sequences are concatenated along the time axis so
        # attention can learn cross-timeframe relationships.
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_size,
            num_heads=n_heads,
            dropout=dropout,
            batch_first=True,
        )
        self.layer_norm = nn.LayerNorm(hidden_size)

        # Attentive pooling: learnable query vector to aggregate variable-length
        # attended sequence into a single fixed-size vector.
        self.pool_query = nn.Parameter(torch.randn(1, 1, hidden_size))

        # Shared trunk after attention pooling
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
        )

        # Output heads
        self.head_entry = nn.Linear(64, 1)   # sigmoid -> entry probability
        self.head_tp = nn.Linear(64, 1)      # linear -> TP distance in ATR units
        self.head_sl = nn.Linear(64, 1)      # linear -> SL distance in ATR units

    def forward(self, x_15m, x_1h):
        """
        Forward pass through dual-timeframe GRU-Attention.

        Parameters
        ----------
        x_15m : torch.Tensor
            Shape (batch, seq_len, input_size) -- 60 bars of 15m data.
        x_1h : torch.Tensor
            Shape (batch, seq_len, input_size) -- 60 bars of 1h data.

        Returns
        -------
        entry_prob : torch.Tensor
            Shape (batch,) -- probability of a valid entry (0 to 1).
        tp_dist : torch.Tensor
            Shape (batch,) -- take-profit distance in ATR units (min 0.5).
        sl_dist : torch.Tensor
            Shape (batch,) -- stop-loss distance in ATR units (min 0.5).
        attn_weights : torch.Tensor
            Attention weight matrix for diagnostics.
        """
        # Encode each timeframe through its GRU — keep FULL output sequences
        out_15m, _ = self.gru_15m(x_15m)   # (batch, seq_15m, hidden)
        out_1h, _ = self.gru_1h(x_1h)      # (batch, seq_1h, hidden)

        # Concatenate the two timeframe sequences along the time axis so
        # attention can learn relationships across ALL timesteps from BOTH
        # timeframes (total tokens = seq_15m + seq_1h).
        combined_seq = torch.cat([out_15m, out_1h], dim=1)  # (batch, seq_15m+seq_1h, hidden)

        # Self-attention across the full combined sequence
        attn_out, attn_weights = self.attention(combined_seq, combined_seq, combined_seq)
        combined_seq = self.layer_norm(combined_seq + attn_out)  # residual + layer norm

        # Attentive pooling: use a learnable query to aggregate the attended
        # sequence into a single vector.  Expand query to match batch size.
        batch_size = combined_seq.size(0)
        query = self.pool_query.expand(batch_size, -1, -1)  # (batch, 1, hidden)
        pooled, _ = self.attention(query, combined_seq, combined_seq)  # (batch, 1, hidden)
        pooled = pooled.squeeze(1)  # (batch, hidden)

        # Shared feature extraction trunk
        features = self.fc(pooled)

        # Three output heads
        entry_prob = torch.sigmoid(self.head_entry(features))
        tp_dist = torch.relu(self.head_tp(features)) + 0.5   # minimum 0.5 ATR
        sl_dist = torch.relu(self.head_sl(features)) + 0.5   # minimum 0.5 ATR

        return (
            entry_prob.squeeze(-1),
            tp_dist.squeeze(-1),
            sl_dist.squeeze(-1),
            attn_weights,
        )


def build_model(device: str = "cpu", **kwargs) -> "GRUAttentionModel":
    """
    Factory function to create and initialize the model.

    Parameters
    ----------
    device : str
        Target device ("cpu" or "cuda").
    **kwargs
        Passed to GRUAttentionModel constructor.

    Returns
    -------
    GRUAttentionModel on the specified device.
    """
    if not TORCH_AVAILABLE:
        raise ImportError(
            "PyTorch is required for System C. Install with: pip install torch>=2.1.0"
        )

    model = GRUAttentionModel(**kwargs)
    model = model.to(device)
    return model


def count_parameters(model) -> int:
    """Count total trainable parameters."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
