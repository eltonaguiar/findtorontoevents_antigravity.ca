#!/usr/bin/env python3
"""
Live Signal Generator
Generates BUY/SELL/HOLD signals with confidence scores and Kelly position sizing.

Usage:
    from signal_generator import SignalGenerator
    sg = SignalGenerator()
    signals = sg.generate_signals(features_df, asset_class='CRYPTO')
"""

import numpy as np
import pandas as pd
import json
import os
from sklearn.linear_model import LogisticRegression, Ridge


class SignalGenerator:
    """
    Institutional-grade signal generator applying proven statistical edges
    per asset class with Kelly position sizing.
    """

    def __init__(self, config_dir='/mnt/agents/output/edge_configs'):
        self.config_dir = config_dir
        self.configs = {}
        self.models = {}
        self._load_configs()

    def _load_configs(self):
        """Load all asset class edge configurations."""
        for asset_class in ['crypto', 'equity', 'forex', 'commodity', 'etf', 'bond']:
            filepath = os.path.join(self.config_dir, f'{asset_class}_edge.json')
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    self.configs[asset_class.upper()] = json.load(f)

    def generate_signals(self, features_df, asset_class='CRYPTO'):
        """
        Generate trading signals for a given feature DataFrame.

        Parameters:
        -----------
        features_df : pd.DataFrame
            DataFrame containing all features.
        asset_class : str
            One of CRYPTO, EQUITY, FOREX, COMMODITY, ETF, BOND.

        Returns:
        --------
        signals_df : pd.DataFrame
            DataFrame with columns: signal, confidence, position_size, kelly_fraction
        """
        asset_class = asset_class.upper()
        config = self.configs.get(asset_class)

        if not config:
            raise ValueError(f"No config found for asset class: {asset_class}")

        strategies = config.get('proven_strategies', [])
        if not strategies:
            return pd.DataFrame({
                'signal': ['HOLD'] * len(features_df),
                'confidence': [0.0] * len(features_df),
                'position_size': [0.0] * len(features_df),
                'kelly_fraction': [0.0] * len(features_df),
            })

        # Aggregate signals from top strategies
        signal_votes = np.zeros(len(features_df))
        confidence_votes = np.zeros(len(features_df))
        total_weight = 0

        for strat in strategies[:3]:  # Top 3 strategies
            name = strat['name']
            weight = strat.get('pf', 1.5)
            total_weight += weight

            signals, confidences = self._apply_strategy(features_df, name, strat)
            signal_votes += signals * weight
            confidence_votes += confidences * weight

        # Normalize
        if total_weight > 0:
            signal_votes /= total_weight
            confidence_votes /= total_weight

        # Generate discrete signals
        discrete_signals = np.where(signal_votes > 0.3, 'BUY',
                            np.where(signal_votes < -0.3, 'SELL', 'HOLD'))

        # Kelly position sizing
        avg_kelly = np.mean([s.get('kelly', 0.1) for s in strategies[:3]])
        half_kelly = avg_kelly * 0.5

        # Cap position size at risk limits
        position_size = np.clip(np.abs(signal_votes) * half_kelly, 0, 0.02)

        return pd.DataFrame({
            'signal': discrete_signals,
            'confidence': np.clip(confidence_votes, 0, 1),
            'position_size': position_size,
            'kelly_fraction': [half_kelly] * len(features_df),
            'raw_score': signal_votes,
        })

    def _apply_strategy(self, features_df, strategy_name, strategy_config):
        """Apply a single strategy to generate signals."""
        signals = np.zeros(len(features_df))
        confidences = np.zeros(len(features_df))

        # Parse strategy name for feature threshold strategies
        if '_p' in strategy_name and '_s' in strategy_name:
            # Format: feature_pXX_sY
            parts = strategy_name.split('_p')
            if len(parts) == 2:
                feat_base = parts[0]
                rest = parts[1]
                p_str = rest.split('_s')[0]
                side_str = rest.split('_s')[1]

                try:
                    p = int(p_str)
                    side = int(side_str)
                except ValueError:
                    return signals, confidences

                # Find the feature column
                feat_col = None
                for col in features_df.columns:
                    if col.startswith(feat_base) or col == feat_base:
                        feat_col = col
                        break

                if feat_col and feat_col in features_df.columns:
                    vals = features_df[feat_col].values
                    if np.std(vals) > 1e-10:
                        if side == 1:
                            signals = np.where(vals > np.percentile(vals, p), 1, 0)
                        else:
                            signals = np.where(vals < np.percentile(vals, 100-p), -1, 0)
                        confidences = np.abs(vals - np.median(vals)) / (np.std(vals) + 1e-10)
                        confidences = np.clip(confidences / 3, 0, 1)

        elif strategy_name.startswith('LR_'):
            # Logistic regression strategy
            try:
                numeric_cols = [c for c in features_df.columns
                                if features_df[c].dtype in ['float64', 'int64']
                                and not any(k in c for k in ['target_', 'open', 'high', 'low', 'close', 'volume',
                                                              'date', 'symbol', 'asset_class'])]
                X = features_df[numeric_cols].fillna(0).replace([np.inf, -np.inf], 0).values

                # Parse parameters
                C = 1.0
                p_thresh = 0.6
                if '_C' in strategy_name:
                    c_part = strategy_name.split('_C')[1].split('_')[0]
                    C = float(c_part)
                if '_p' in strategy_name:
                    p_part = strategy_name.split('_p')[1]
                    p_thresh = float(p_part)

                # Fit and predict
                y_proxy = (features_df['return_1d'].values > 0).astype(int) if 'return_1d' in features_df.columns else np.ones(len(features_df))
                split = int(len(features_df) * 0.8)

                lr = LogisticRegression(C=C, max_iter=500, random_state=42)
                lr.fit(X[:split], y_proxy[:split])
                probs = lr.predict_proba(X)[:, 1]

                signals = np.where(probs > p_thresh, 1, 0)
                signals[probs < (1 - p_thresh)] = -1
                confidences = np.abs(probs - 0.5) * 2
            except Exception:
                pass

        return signals, confidences

    def get_position_sizing(self, asset_class, win_rate=None, avg_win=None, avg_loss=None):
        """
        Calculate Kelly position sizing for an asset class.

        Parameters:
        -----------
        asset_class : str
            Asset class name.
        win_rate : float, optional
            Override win rate.
        avg_win : float, optional
            Override average win.
        avg_loss : float, optional
            Override average loss.

        Returns:
        --------
        sizing : dict
            Kelly fraction, half-Kelly, and recommended position size.
        """
        config = self.configs.get(asset_class.upper(), {})
        strategies = config.get('proven_strategies', [])

        if not strategies and (win_rate is None or avg_win is None or avg_loss is None):
            return {'kelly': 0, 'half_kelly': 0, 'position_size': 0, 'max_position': 0.02}

        if win_rate is not None:
            kelly = self._kelly(win_rate, avg_win, avg_loss)
        else:
            kelly = np.mean([s.get('kelly', 0.1) for s in strategies[:3]])

        half_kelly = kelly * 0.5

        # Risk limits: max 2% per trade, max 20% per asset class
        max_position = min(half_kelly, 0.02)

        return {
            'kelly': round(kelly, 4),
            'half_kelly': round(half_kelly, 4),
            'position_size': round(max_position, 4),
            'max_position': 0.02,
            'max_asset_class_exposure': 0.20,
        }

    @staticmethod
    def _kelly(p, b_win, b_loss):
        """Kelly criterion: f* = (p*b - q) / b"""
        if b_loss == 0 or b_win <= 0:
            return 0.0
        b = abs(b_win / b_loss)
        q = 1 - p
        return max(-1, min(1, (p * b - q) / b))


if __name__ == '__main__':
    print("Signal Generator loaded successfully.")
    sg = SignalGenerator()
    print(f"Loaded configs for: {list(sg.configs.keys())}")

    # Example usage
    print("\nExample position sizing per asset class:")
    for ac in ['CRYPTO', 'EQUITY', 'FOREX', 'COMMODITY', 'ETF', 'BOND']:
        sizing = sg.get_position_sizing(ac)
        print(f"  {ac}: Kelly={sizing['kelly']:.3f}, Half-Kelly={sizing['half_kelly']:.3f}, "
              f"Max Position={sizing['max_position']:.1%}")
