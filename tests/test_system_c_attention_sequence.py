"""
System C: ensure self-attention runs on a real sequence (not seq_len=1 no-op).

Historical bug: squeezing to one token before MultiheadAttention made attention decorative.
"""
import pytest

torch = pytest.importorskip("torch")

from ml_battleground.system_c_deeplearn.model_arch import GRUAttentionModel


def test_gru_attention_self_attn_sees_two_timeframes_full_length():
    """Self-attention input must span 2 * seq_len tokens (15m + 1h GRU outputs)."""
    t = 24
    f = 8
    model = GRUAttentionModel(
        input_size=f, hidden_size=16, num_layers=1, n_heads=2, dropout=0.0
    )
    model.eval()
    b = 2
    x15 = torch.randn(b, t, f)
    x1h = torch.randn(b, t, f)
    with torch.no_grad():
        entry, tp, sl, attn_weights = model(x15, x1h)
    assert entry.shape == (b,)
    assert torch.isfinite(entry).all()
    # Returned weights are from the *first* MHA (self-attn on combined sequence).
    # batch_first=True, average_attn_weights=True -> (N, L, S) with L = S = 2*t
    assert attn_weights is not None
    assert attn_weights.shape[1] == 2 * t
    assert attn_weights.shape[2] == 2 * t
