"""
InformerLite — Lightweight Transformer-Based Price Forecaster (NumPy Only)
==========================================================================
A simplified attention-based model for crypto price direction prediction.
No PyTorch, TensorFlow, or sklearn required — pure numpy implementation.

Architecture:
  - Input projection (input_dim -> d_model)
  - Positional encoding (sinusoidal)
  - N x TransformerBlock (self-attention + FFN + layer norm + residual)
  - Mean pooling -> output projection -> predicted return

Designed for hourly crypto data with ~2-5K trainable parameters.
Runs on GitHub Actions Python 3.11 with just `pip install numpy requests`.

Author: Antigravity ML Research
"""

import numpy as np
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """Numerically stable softmax."""
    e = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e / (e.sum(axis=axis, keepdims=True) + 1e-12)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid."""
    return np.where(
        x >= 0,
        1.0 / (1.0 + np.exp(-x)),
        np.exp(x) / (1.0 + np.exp(x)),
    )


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0, x)


def _layer_norm(x: np.ndarray, gamma: np.ndarray, beta: np.ndarray,
                eps: float = 1e-5) -> np.ndarray:
    """Layer normalization over the last axis."""
    mean = x.mean(axis=-1, keepdims=True)
    var = x.var(axis=-1, keepdims=True)
    return gamma * (x - mean) / np.sqrt(var + eps) + beta


def _xavier_init(fan_in: int, fan_out: int, rng: np.random.RandomState) -> np.ndarray:
    """Xavier/Glorot uniform initialization."""
    limit = np.sqrt(6.0 / (fan_in + fan_out))
    return rng.uniform(-limit, limit, (fan_in, fan_out)).astype(np.float64)


def _sinusoidal_encoding(seq_len: int, d_model: int) -> np.ndarray:
    """Sinusoidal positional encoding (Vaswani et al. 2017)."""
    pe = np.zeros((seq_len, d_model))
    pos = np.arange(seq_len)[:, None]
    div = np.exp(np.arange(0, d_model, 2) * (-np.log(10000.0) / d_model))
    pe[:, 0::2] = np.sin(pos * div)
    pe[:, 1::2] = np.cos(pos * div[:d_model // 2])  # handle odd d_model
    return pe


# ---------------------------------------------------------------------------
# Technical indicator helpers (pure numpy, no TA-lib)
# ---------------------------------------------------------------------------

def _compute_rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """RSI via exponential moving average of gains/losses."""
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    # Seed with SMA
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    rsi = np.full(len(closes), 50.0)
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i + 1] = 100.0 - 100.0 / (1.0 + rs)
    return rsi


def _compute_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                 period: int = 14) -> np.ndarray:
    """Average True Range."""
    tr = np.maximum(highs[1:] - lows[1:],
                    np.maximum(np.abs(highs[1:] - closes[:-1]),
                               np.abs(lows[1:] - closes[:-1])))
    atr = np.full(len(closes), np.mean(tr[:period]))
    for i in range(period, len(tr)):
        atr[i + 1] = (atr[i] * (period - 1) + tr[i]) / period
    return atr


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average."""
    alpha = 2.0 / (period + 1)
    out = np.empty_like(data)
    out[0] = data[0]
    for i in range(1, len(data)):
        out[i] = alpha * data[i] + (1 - alpha) * out[i - 1]
    return out


# ---------------------------------------------------------------------------
# Core transformer components
# ---------------------------------------------------------------------------

class SelfAttention:
    """Multi-head self-attention using numpy matmul.

    Parameters
    ----------
    d_model : int
        Model dimensionality.
    n_heads : int
        Number of attention heads. d_model must be divisible by n_heads.
    """

    def __init__(self, d_model: int, n_heads: int,
                 rng: np.random.RandomState):
        assert d_model % n_heads == 0, "d_model must be divisible by n_heads"
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads

        # Q, K, V projection matrices: (d_model, d_model)
        self.W_q = _xavier_init(d_model, d_model, rng)
        self.W_k = _xavier_init(d_model, d_model, rng)
        self.W_v = _xavier_init(d_model, d_model, rng)
        self.W_o = _xavier_init(d_model, d_model, rng)

        # Cache for backward pass
        self._cache: Dict = {}

    def forward(self, x: np.ndarray) -> np.ndarray:
        """
        Parameters
        ----------
        x : np.ndarray, shape (batch, seq_len, d_model)

        Returns
        -------
        np.ndarray, shape (batch, seq_len, d_model)
        """
        B, T, D = x.shape

        # Linear projections
        Q = x @ self.W_q  # (B, T, D)
        K = x @ self.W_k
        V = x @ self.W_v

        # Reshape to (B, n_heads, T, d_k)
        Q = Q.reshape(B, T, self.n_heads, self.d_k).transpose(0, 2, 1, 3)
        K = K.reshape(B, T, self.n_heads, self.d_k).transpose(0, 2, 1, 3)
        V = V.reshape(B, T, self.n_heads, self.d_k).transpose(0, 2, 1, 3)

        # Scaled dot-product attention
        scale = np.sqrt(self.d_k)
        scores = (Q @ K.transpose(0, 1, 3, 2)) / scale  # (B, n_heads, T, T)
        attn_weights = _softmax(scores, axis=-1)

        # Weighted sum of values
        context = attn_weights @ V  # (B, n_heads, T, d_k)

        # Concatenate heads and project
        context = context.transpose(0, 2, 1, 3).reshape(B, T, D)
        output = context @ self.W_o

        # Cache for training
        self._cache = {
            "x": x, "Q": Q, "K": K, "V": V,
            "attn_weights": attn_weights, "context": context,
        }

        return output

    def get_params(self):
        return [self.W_q, self.W_k, self.W_v, self.W_o]

    def set_params(self, params):
        self.W_q, self.W_k, self.W_v, self.W_o = params


class FeedForward:
    """Two-layer MLP with ReLU activation.

    Parameters
    ----------
    d_model : int
        Input/output dimensionality.
    d_ff : int
        Hidden layer dimensionality.
    """

    def __init__(self, d_model: int, d_ff: int,
                 rng: np.random.RandomState):
        self.W1 = _xavier_init(d_model, d_ff, rng)
        self.b1 = np.zeros(d_ff)
        self.W2 = _xavier_init(d_ff, d_model, rng)
        self.b2 = np.zeros(d_model)
        self._cache: Dict = {}

    def forward(self, x: np.ndarray) -> np.ndarray:
        """
        Parameters
        ----------
        x : np.ndarray, shape (batch, seq_len, d_model)

        Returns
        -------
        np.ndarray, shape (batch, seq_len, d_model)
        """
        hidden = _relu(x @ self.W1 + self.b1)
        output = hidden @ self.W2 + self.b2
        self._cache = {"x": x, "hidden": hidden}
        return output

    def get_params(self):
        return [self.W1, self.b1, self.W2, self.b2]

    def set_params(self, params):
        self.W1, self.b1, self.W2, self.b2 = params


class TransformerBlock:
    """Single transformer encoder block: self-attention + FFN + layer norm + residual.

    Parameters
    ----------
    d_model : int
        Model dimensionality.
    n_heads : int
        Number of attention heads.
    d_ff : int
        Feed-forward hidden dimensionality.
    """

    def __init__(self, d_model: int, n_heads: int, d_ff: int,
                 rng: np.random.RandomState):
        self.attention = SelfAttention(d_model, n_heads, rng)
        self.ffn = FeedForward(d_model, d_ff, rng)

        # Layer norm parameters (two norms: post-attention, post-FFN)
        self.ln1_gamma = np.ones(d_model)
        self.ln1_beta = np.zeros(d_model)
        self.ln2_gamma = np.ones(d_model)
        self.ln2_beta = np.zeros(d_model)

    def forward(self, x: np.ndarray) -> np.ndarray:
        """
        Parameters
        ----------
        x : np.ndarray, shape (batch, seq_len, d_model)

        Returns
        -------
        np.ndarray, shape (batch, seq_len, d_model)
        """
        # Self-attention + residual + layer norm
        attn_out = self.attention.forward(x)
        x = _layer_norm(x + attn_out, self.ln1_gamma, self.ln1_beta)

        # Feed-forward + residual + layer norm
        ffn_out = self.ffn.forward(x)
        x = _layer_norm(x + ffn_out, self.ln2_gamma, self.ln2_beta)

        return x

    def get_params(self):
        return (
            self.attention.get_params()
            + self.ffn.get_params()
            + [self.ln1_gamma, self.ln1_beta,
               self.ln2_gamma, self.ln2_beta]
        )

    def set_params(self, params):
        self.attention.set_params(params[:4])
        self.ffn.set_params(params[4:8])
        self.ln1_gamma, self.ln1_beta = params[8], params[9]
        self.ln2_gamma, self.ln2_beta = params[10], params[11]


# ---------------------------------------------------------------------------
# Main model
# ---------------------------------------------------------------------------

class InformerLite:
    """Lightweight transformer forecaster for crypto price prediction.

    Pure numpy implementation — no PyTorch, TensorFlow, or sklearn needed.
    Suitable for running on GitHub Actions with minimal dependencies.

    Parameters
    ----------
    input_dim : int
        Number of input features per timestep (default 6).
    d_model : int
        Internal model dimensionality (default 32).
    n_heads : int
        Number of attention heads (default 4).
    n_layers : int
        Number of stacked transformer blocks (default 2).
    seq_len : int
        Input sequence length in bars (default 60).
    seed : int
        Random seed for reproducibility.

    Features (6 inputs):
        0. Normalized returns (close-to-close)
        1. Normalized volume
        2. RSI / 100
        3. ATR / price (normalized volatility)
        4. EMA crossover signal (fast vs slow)
        5. Hour-of-day encoding (sin transform)
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        input_dim: int = 6,
        d_model: int = 32,
        n_heads: int = 4,
        n_layers: int = 2,
        seq_len: int = 60,
        seed: int = 42,
    ):
        self.input_dim = input_dim
        self.d_model = d_model
        self.n_heads = n_heads
        self.n_layers = n_layers
        self.seq_len = seq_len

        self.rng = np.random.RandomState(seed)

        # Input projection: (input_dim -> d_model)
        self.W_in = _xavier_init(input_dim, d_model, self.rng)
        self.b_in = np.zeros(d_model)

        # Positional encoding (fixed, not learned)
        self.pos_enc = _sinusoidal_encoding(seq_len, d_model)

        # Transformer blocks
        d_ff = d_model * 2  # standard ratio for small models
        self.blocks = [
            TransformerBlock(d_model, n_heads, d_ff, self.rng)
            for _ in range(n_layers)
        ]

        # Output projection: d_model -> 1 (predicted return)
        self.W_out = _xavier_init(d_model, 1, self.rng)
        self.b_out = np.zeros(1)

        # Training state
        self._trained = False
        self._train_loss_history: list = []

    def count_params(self) -> int:
        """Count total number of trainable parameters."""
        total = 0
        # Input projection
        total += self.W_in.size + self.b_in.size
        # Each transformer block
        for block in self.blocks:
            for p in block.get_params():
                total += p.size
        # Output projection
        total += self.W_out.size + self.b_out.size
        return total

    def _get_all_params(self) -> list:
        """Collect all trainable parameters as a flat list of arrays."""
        params = [self.W_in, self.b_in]
        for block in self.blocks:
            params.extend(block.get_params())
        params.extend([self.W_out, self.b_out])
        return params

    def _set_all_params(self, params: list):
        """Restore parameters from a flat list."""
        idx = 0
        self.W_in = params[idx]; idx += 1
        self.b_in = params[idx]; idx += 1
        for block in self.blocks:
            n_block_params = 12  # 4 attn + 4 ffn + 4 ln
            block.set_params(params[idx:idx + n_block_params])
            idx += n_block_params
        self.W_out = params[idx]; idx += 1
        self.b_out = params[idx]; idx += 1

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass through the model.

        Parameters
        ----------
        x : np.ndarray, shape (batch, seq_len, input_dim)

        Returns
        -------
        np.ndarray, shape (batch,) — predicted next-bar return.
        """
        B, T, _ = x.shape

        # Input projection
        h = x @ self.W_in + self.b_in  # (B, T, d_model)

        # Add positional encoding
        h = h + self.pos_enc[:T][None, :, :]  # broadcast over batch

        # Pass through transformer blocks
        for block in self.blocks:
            h = block.forward(h)

        # Mean pooling over sequence dimension
        h_pooled = h.mean(axis=1)  # (B, d_model)

        # Output projection
        pred = h_pooled @ self.W_out + self.b_out  # (B, 1)
        return pred.squeeze(-1)  # (B,)

    def _prepare_features(
        self,
        closes: np.ndarray,
        volumes: Optional[np.ndarray] = None,
        highs: Optional[np.ndarray] = None,
        lows: Optional[np.ndarray] = None,
        hours: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Compute the 6 input features from raw OHLCV data.

        Parameters
        ----------
        closes : np.ndarray, shape (N,)
        volumes : np.ndarray, shape (N,) or None
        highs : np.ndarray, shape (N,) or None (defaults to closes)
        lows : np.ndarray, shape (N,) or None (defaults to closes)
        hours : np.ndarray, shape (N,) or None (defaults to zeros)

        Returns
        -------
        np.ndarray, shape (N, 6)
        """
        N = len(closes)
        if highs is None:
            highs = closes
        if lows is None:
            lows = closes
        if volumes is None:
            volumes = np.ones(N)
        if hours is None:
            hours = np.zeros(N)

        # 1. Normalized returns
        returns = np.zeros(N)
        returns[1:] = (closes[1:] - closes[:-1]) / (closes[:-1] + 1e-12)
        # Clip extreme returns
        returns = np.clip(returns, -0.1, 0.1)

        # 2. Normalized volume (z-score with rolling window)
        vol_mean = np.mean(volumes) + 1e-12
        vol_std = np.std(volumes) + 1e-12
        norm_vol = (volumes - vol_mean) / vol_std
        norm_vol = np.clip(norm_vol, -3, 3) / 3.0  # scale to [-1, 1]

        # 3. RSI / 100
        rsi = _compute_rsi(closes, period=14) / 100.0

        # 4. ATR / price (normalized volatility)
        atr = _compute_atr(highs, lows, closes, period=14)
        atr_norm = atr / (closes + 1e-12)
        atr_norm = np.clip(atr_norm, 0, 0.1) / 0.1  # scale to [0, 1]

        # 5. EMA crossover signal
        ema_fast = _ema(closes, period=9)
        ema_slow = _ema(closes, period=21)
        ema_cross = (ema_fast - ema_slow) / (closes + 1e-12)
        ema_cross = np.clip(ema_cross, -0.05, 0.05) / 0.05  # scale to [-1, 1]

        # 6. Hour-of-day sin encoding
        hour_enc = np.sin(2 * np.pi * hours / 24.0)

        features = np.stack([
            returns, norm_vol, rsi, atr_norm, ema_cross, hour_enc
        ], axis=-1)  # (N, 6)

        return features

    def _make_sequences(
        self, features: np.ndarray, targets: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Slice features into overlapping sequences for training.

        Parameters
        ----------
        features : np.ndarray, shape (N, input_dim)
        targets : np.ndarray, shape (N,)

        Returns
        -------
        X : np.ndarray, shape (n_samples, seq_len, input_dim)
        y : np.ndarray, shape (n_samples,)
        """
        N = len(features)
        n_samples = N - self.seq_len
        if n_samples <= 0:
            raise ValueError(
                f"Need at least {self.seq_len + 1} data points, got {N}"
            )
        X = np.array([
            features[i:i + self.seq_len] for i in range(n_samples)
        ])
        y = targets[self.seq_len:]
        return X, y

    def _forward_with_cache(self, x: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """Forward pass that caches intermediate values for backprop.

        Returns (prediction, cache_dict).
        """
        B, T, _ = x.shape
        cache = {"input": x}

        # Input projection
        h = x @ self.W_in + self.b_in  # (B, T, d_model)
        cache["post_input_proj"] = h.copy()

        # Add positional encoding
        h = h + self.pos_enc[:T][None, :, :]
        cache["post_pos_enc"] = h.copy()

        # Transformer blocks — cache input/output of each
        cache["block_inputs"] = []
        cache["block_attn_inputs"] = []
        cache["block_attn_outputs"] = []
        cache["block_ffn_inputs"] = []
        cache["block_ffn_hidden"] = []

        for i, block in enumerate(self.blocks):
            block_in = h.copy()
            cache["block_inputs"].append(block_in)

            # Self-attention sublayer
            attn_out = block.attention.forward(h)
            cache["block_attn_inputs"].append(h.copy())
            cache["block_attn_outputs"].append(attn_out.copy())

            h_ln1 = _layer_norm(h + attn_out, block.ln1_gamma, block.ln1_beta)
            cache["block_ffn_inputs"].append(h_ln1.copy())

            # FFN sublayer
            ffn_hidden = _relu(h_ln1 @ block.ffn.W1 + block.ffn.b1)
            ffn_out = ffn_hidden @ block.ffn.W2 + block.ffn.b2
            cache["block_ffn_hidden"].append(ffn_hidden.copy())

            h = _layer_norm(h_ln1 + ffn_out, block.ln2_gamma, block.ln2_beta)

        # Mean pooling
        h_pooled = h.mean(axis=1)  # (B, d_model)
        cache["h_final"] = h
        cache["h_pooled"] = h_pooled

        # Output projection
        pred = h_pooled @ self.W_out + self.b_out  # (B, 1)
        pred = pred.squeeze(-1)
        return pred, cache

    def _backward(self, cache: Dict, y: np.ndarray,
                  pred: np.ndarray) -> Dict:
        """Manual backpropagation through the full network.

        Computes analytical gradients for all parameters.
        Approximates layer norm and attention gradients with a
        straight-through estimator for layer norm and full backprop
        through attention linear projections.

        Returns dict of gradients keyed by parameter name.
        """
        B = len(y)
        T = cache["input"].shape[1]
        grads = {}

        # Loss: MSE = mean((pred - y)^2)
        # dL/dpred = 2*(pred - y) / B
        d_pred = 2.0 * (pred - y) / B  # (B,)

        # Output projection: pred = h_pooled @ W_out + b_out
        h_pooled = cache["h_pooled"]  # (B, d_model)
        grads["W_out"] = h_pooled.T @ d_pred[:, None]  # (d_model, 1)
        grads["b_out"] = np.sum(d_pred, keepdims=True)  # (1,)

        # dL/dh_pooled = d_pred[:, None] @ W_out.T  -> (B, d_model)
        d_h_pooled = d_pred[:, None] @ self.W_out.T  # (B, d_model)

        # Mean pooling: h_pooled = h.mean(axis=1)
        # dL/dh = dL/dh_pooled / T, broadcast to (B, T, d_model)
        d_h = np.broadcast_to(
            (d_h_pooled / T)[:, None, :], (B, T, self.d_model)
        ).copy()

        # Backprop through transformer blocks (reverse order)
        for i in reversed(range(self.n_layers)):
            block = self.blocks[i]
            pfx = f"block_{i}_"

            # --- Layer norm 2 (post-FFN): straight-through estimator ---
            # LN is approximately identity for gradients when gamma~1
            # This is a common practical approximation for numpy-only backprop
            d_h_ln2_in = d_h * block.ln2_gamma[None, None, :]

            # Residual: h = LN(h_ln1 + ffn_out)
            d_ffn_out = d_h_ln2_in
            d_h_ln1_post = d_h_ln2_in.copy()

            # FFN backward: ffn_out = relu(x @ W1 + b1) @ W2 + b2
            ffn_input = cache["block_ffn_inputs"][i]  # (B, T, d_model)
            ffn_hidden = cache["block_ffn_hidden"][i]  # (B, T, d_ff)

            # d_ffn_out -> W2, b2
            d_W2 = np.einsum("bti,btj->ij", ffn_hidden, d_ffn_out)
            d_b2 = d_ffn_out.sum(axis=(0, 1))
            grads[pfx + "ffn_W2"] = d_W2
            grads[pfx + "ffn_b2"] = d_b2

            # d_hidden = d_ffn_out @ W2.T, masked by ReLU
            d_hidden = d_ffn_out @ block.ffn.W2.T
            d_hidden = d_hidden * (ffn_hidden > 0).astype(float)

            # d_W1, d_b1
            d_W1 = np.einsum("bti,btj->ij", ffn_input, d_hidden)
            d_b1 = d_hidden.sum(axis=(0, 1))
            grads[pfx + "ffn_W1"] = d_W1
            grads[pfx + "ffn_b1"] = d_b1

            # Gradient flows back into h_ln1
            d_h_ln1 = d_h_ln1_post + d_hidden @ block.ffn.W1.T

            # --- Layer norm 1 (post-attention): straight-through ---
            d_h_ln1_in = d_h_ln1 * block.ln1_gamma[None, None, :]

            # Residual: h_ln1 = LN(h + attn_out)
            d_attn_out = d_h_ln1_in
            d_h_pre_attn = d_h_ln1_in.copy()

            # Attention backward: output = concat_heads @ W_o
            attn = block.attention
            ac = attn._cache
            context = ac["context"]  # (B, T, d_model) — pre-W_o

            # d_W_o
            d_W_o = np.einsum("bti,btj->ij", context, d_attn_out)
            grads[pfx + "attn_W_o"] = d_W_o

            # d_context = d_attn_out @ W_o.T
            d_context = d_attn_out @ attn.W_o.T  # (B, T, d_model)

            # Reshape back to multi-head: (B, T, D) -> (B, n_heads, T, d_k)
            d_context_mh = d_context.reshape(
                B, T, self.n_heads, attn.d_k
            ).transpose(0, 2, 1, 3)

            # attn_weights @ V = context_mh
            # d_V = attn_weights.T @ d_context_mh
            attn_weights = ac["attn_weights"]  # (B, n_heads, T, T)
            V = ac["V"]  # (B, n_heads, T, d_k)

            d_V = attn_weights.transpose(0, 1, 3, 2) @ d_context_mh
            # d_attn_weights = d_context_mh @ V.T
            d_attn_w = d_context_mh @ V.transpose(0, 1, 3, 2)

            # softmax backward (Jacobian): d_scores = attn_w * (d_attn_w - sum(d_attn_w * attn_w))
            sum_da = (d_attn_w * attn_weights).sum(axis=-1, keepdims=True)
            d_scores = attn_weights * (d_attn_w - sum_da)
            d_scores /= np.sqrt(attn.d_k)

            # scores = Q @ K.T => d_Q = d_scores @ K, d_K = d_scores.T @ Q
            K = ac["K"]
            Q = ac["Q"]
            d_Q = d_scores @ K  # (B, n_heads, T, d_k)
            d_K = d_scores.transpose(0, 1, 3, 2) @ Q

            # Reshape back to (B, T, D)
            d_Q = d_Q.transpose(0, 2, 1, 3).reshape(B, T, self.d_model)
            d_K = d_K.transpose(0, 2, 1, 3).reshape(B, T, self.d_model)
            d_V = d_V.transpose(0, 2, 1, 3).reshape(B, T, self.d_model)

            # Projection backward: Q = x @ W_q, K = x @ W_k, V = x @ W_v
            x_attn = ac["x"]  # (B, T, d_model)
            grads[pfx + "attn_W_q"] = np.einsum("bti,btj->ij", x_attn, d_Q)
            grads[pfx + "attn_W_k"] = np.einsum("bti,btj->ij", x_attn, d_K)
            grads[pfx + "attn_W_v"] = np.einsum("bti,btj->ij", x_attn, d_V)

            # d_x from attention = d_Q @ W_q.T + d_K @ W_k.T + d_V @ W_v.T
            d_x_attn = (d_Q @ attn.W_q.T + d_K @ attn.W_k.T
                        + d_V @ attn.W_v.T)

            # Combine with residual path
            d_h = d_h_pre_attn + d_x_attn

        # Input projection backward: h = x @ W_in + b_in
        x_input = cache["input"]
        grads["W_in"] = np.einsum("bti,btj->ij", x_input, d_h)
        grads["b_in"] = d_h.sum(axis=(0, 1))

        return grads

    def train(
        self,
        closes: np.ndarray,
        volumes: Optional[np.ndarray] = None,
        highs: Optional[np.ndarray] = None,
        lows: Optional[np.ndarray] = None,
        hours: Optional[np.ndarray] = None,
        epochs: int = 50,
        lr: float = 0.001,
        momentum: float = 0.9,
        batch_size: int = 16,
        verbose: bool = True,
    ) -> Dict:
        """Train the model on historical OHLCV data.

        Uses analytical backpropagation with SGD + momentum.
        Layer norm gradients use a straight-through estimator
        (practical approximation for lightweight numpy training).

        Parameters
        ----------
        closes : np.ndarray
            Close prices, shape (N,).
        volumes, highs, lows, hours : optional arrays
        epochs : int
            Number of training epochs.
        lr : float
            Learning rate.
        momentum : float
            SGD momentum factor.
        batch_size : int
            Mini-batch size.
        verbose : bool
            Print training progress.

        Returns
        -------
        dict with training summary.
        """
        # Prepare features and targets
        features = self._prepare_features(closes, volumes, highs, lows, hours)

        # Target: next-bar return
        targets = np.zeros(len(closes))
        targets[1:] = (closes[1:] - closes[:-1]) / (closes[:-1] + 1e-12)
        targets = np.clip(targets, -0.1, 0.1)

        X, y = self._make_sequences(features, targets)
        n_samples = len(X)

        if verbose:
            print(f"InformerLite training: {n_samples} samples, "
                  f"{self.count_params()} params, {epochs} epochs")

        # Initialize momentum buffers for each named parameter
        velocity = {}

        self._train_loss_history = []

        for epoch in range(epochs):
            # Shuffle
            perm = self.rng.permutation(n_samples)
            X_shuf = X[perm]
            y_shuf = y[perm]

            epoch_loss = 0.0
            n_batches = 0

            for start in range(0, n_samples, batch_size):
                end = min(start + batch_size, n_samples)
                X_b = X_shuf[start:end]
                y_b = y_shuf[start:end]

                # Forward pass with caching
                pred, cache = self._forward_with_cache(X_b)
                loss = np.mean((pred - y_b) ** 2)
                epoch_loss += loss

                # Backward pass — analytical gradients
                grads = self._backward(cache, y_b, pred)

                # Gradient clipping (max norm)
                max_norm = 1.0
                total_norm = np.sqrt(
                    sum(np.sum(g ** 2) for g in grads.values())
                )
                clip_coeff = min(1.0, max_norm / (total_norm + 1e-12))

                # Apply gradients with momentum SGD
                # Output layer
                for name, param_ref in [
                    ("W_out", "W_out"), ("b_out", "b_out"),
                    ("W_in", "W_in"), ("b_in", "b_in"),
                ]:
                    if name not in velocity:
                        velocity[name] = np.zeros_like(getattr(self, param_ref))
                    g = grads[name] * clip_coeff
                    velocity[name] = momentum * velocity[name] - lr * g
                    setattr(self, param_ref,
                            getattr(self, param_ref) + velocity[name])

                # Transformer block parameters
                for i, block in enumerate(self.blocks):
                    pfx = f"block_{i}_"
                    attn = block.attention
                    ffn = block.ffn

                    param_map = [
                        (pfx + "attn_W_q", attn, "W_q"),
                        (pfx + "attn_W_k", attn, "W_k"),
                        (pfx + "attn_W_v", attn, "W_v"),
                        (pfx + "attn_W_o", attn, "W_o"),
                        (pfx + "ffn_W1", ffn, "W1"),
                        (pfx + "ffn_b1", ffn, "b1"),
                        (pfx + "ffn_W2", ffn, "W2"),
                        (pfx + "ffn_b2", ffn, "b2"),
                    ]
                    for gname, obj, attr in param_map:
                        if gname in grads:
                            if gname not in velocity:
                                velocity[gname] = np.zeros_like(
                                    getattr(obj, attr)
                                )
                            g = grads[gname] * clip_coeff
                            velocity[gname] = (
                                momentum * velocity[gname] - lr * g
                            )
                            setattr(obj, attr,
                                    getattr(obj, attr) + velocity[gname])

                n_batches += 1

            avg_loss = epoch_loss / max(n_batches, 1)
            self._train_loss_history.append(avg_loss)

            if verbose and (epoch + 1) % max(1, epochs // 10) == 0:
                print(f"  Epoch {epoch + 1}/{epochs}  loss={avg_loss:.6f}")

        self._trained = True

        return {
            "epochs": epochs,
            "final_loss": self._train_loss_history[-1],
            "n_samples": n_samples,
            "n_params": self.count_params(),
        }

    def predict(self, symbol: str = "BTCUSDT",
                prices: Optional[np.ndarray] = None,
                volumes: Optional[np.ndarray] = None,
                highs: Optional[np.ndarray] = None,
                lows: Optional[np.ndarray] = None,
                hours: Optional[np.ndarray] = None) -> Dict:
        """Generate a prediction for a symbol.

        If prices are provided, uses them directly. Otherwise generates
        a demo prediction with random features (for testing).

        Parameters
        ----------
        symbol : str
            Trading pair symbol.
        prices : optional np.ndarray
            Close prices (need at least seq_len bars).

        Returns
        -------
        dict with prediction details.
        """
        if prices is not None and len(prices) >= self.seq_len:
            features = self._prepare_features(
                prices, volumes, highs, lows, hours
            )
            # Take the last seq_len bars
            x = features[-self.seq_len:][None, :, :]  # (1, seq_len, 6)
        else:
            # Demo mode: random features for testing
            x = self.rng.randn(1, self.seq_len, self.input_dim) * 0.1

        predicted_return = float(self.forward(x)[0])

        # Direction from sign of predicted return
        if predicted_return > 0.0005:
            direction = "LONG"
        elif predicted_return < -0.0005:
            direction = "SHORT"
        else:
            direction = "HOLD"

        # Confidence from sigmoid of prediction magnitude
        confidence = float(_sigmoid(np.array([abs(predicted_return) * 100]))[0])
        # Scale to 0.5-0.95 range for readability
        confidence = 0.5 + 0.45 * confidence

        return {
            "symbol": symbol,
            "direction": direction,
            "confidence": round(confidence, 4),
            "predicted_return": round(predicted_return, 6),
            "strategy": "informer_lite",
            "source": "ml_crypto_predictor",
            "model_version": self.VERSION,
            "n_params": self.count_params(),
            "trained": self._trained,
            "generated_at": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        }

    def save(self, path: str):
        """Save model weights to a .npz file.

        Parameters
        ----------
        path : str
            Output file path (should end with .npz).
        """
        params = self._get_all_params()
        save_dict = {
            f"param_{i}": p for i, p in enumerate(params)
        }
        save_dict["_config"] = np.array([
            self.input_dim, self.d_model, self.n_heads,
            self.n_layers, self.seq_len,
        ])
        save_dict["_loss_history"] = np.array(
            self._train_loss_history if self._train_loss_history else [0.0]
        )
        np.savez(path, **save_dict)

    def load(self, path: str):
        """Load model weights from a .npz file.

        Parameters
        ----------
        path : str
            Path to .npz file.
        """
        if not path.endswith(".npz"):
            path += ".npz"
        data = np.load(path, allow_pickle=True)

        # Restore config
        config = data["_config"]
        assert config[0] == self.input_dim, "input_dim mismatch"
        assert config[1] == self.d_model, "d_model mismatch"

        # Restore parameters
        params = []
        i = 0
        while f"param_{i}" in data:
            params.append(data[f"param_{i}"])
            i += 1
        self._set_all_params(params)

        if "_loss_history" in data:
            self._train_loss_history = data["_loss_history"].tolist()

        self._trained = True

    def summary(self) -> str:
        """Return a human-readable model summary."""
        lines = [
            f"InformerLite v{self.VERSION}",
            f"  Input dim:    {self.input_dim}",
            f"  Model dim:    {self.d_model}",
            f"  Heads:        {self.n_heads}",
            f"  Layers:       {self.n_layers}",
            f"  Seq length:   {self.seq_len}",
            f"  Total params: {self.count_params():,}",
            f"  Trained:      {self._trained}",
        ]
        if self._train_loss_history:
            lines.append(
                f"  Final loss:   {self._train_loss_history[-1]:.6f}"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point for quick testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("InformerLite — Lightweight Transformer Forecaster")
    print("=" * 60)

    model = InformerLite()
    print(model.summary())
    print()

    # Quick forward pass test
    x_test = np.random.randn(2, 60, 6) * 0.1
    out = model.forward(x_test)
    print(f"Forward pass test: input {x_test.shape} -> output {out.shape}")
    print(f"  Predictions: {out}")
    print()

    # Quick prediction test
    pred = model.predict("BTCUSDT")
    print("Prediction (untrained, demo):")
    for k, v in pred.items():
        print(f"  {k}: {v}")
    print()

    # Quick training test with synthetic data
    print("Training on synthetic data (200 bars, 5 epochs)...")
    np.random.seed(123)
    N = 200
    synthetic_closes = 50000 + np.cumsum(np.random.randn(N) * 100)
    synthetic_volumes = np.abs(np.random.randn(N)) * 1e6
    result = model.train(
        closes=synthetic_closes,
        volumes=synthetic_volumes,
        epochs=5,
        lr=0.001,
        batch_size=16,
        verbose=True,
    )
    print(f"\nTraining result: {result}")

    # Post-training prediction
    pred2 = model.predict("BTCUSDT", prices=synthetic_closes)
    print("\nPrediction (after training):")
    for k, v in pred2.items():
        print(f"  {k}: {v}")
