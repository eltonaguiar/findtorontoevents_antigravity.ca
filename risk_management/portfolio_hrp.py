import numpy as np
import pandas as pd
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class HierarchicalRiskParity:
    """
    Hierarchical Risk Parity (HRP) Optimizer.
    Implemented as a robust, numpy/pandas-only version to avoid 
    heavy dependencies and potential Windows import issues.
    
    Ref: Lopez de Prado, M. (2016) "Building Hierarchical Diversity into Financial Portfolios"
    """
    
    def __init__(self):
        pass

    def get_cluster_var(self, cov: np.ndarray, cluster_indices: List[int]) -> float:
        """Compute the variance of a cluster."""
        # cov is the full covariance matrix
        # cluster_indices are integer indices into that matrix
        cov_slice = cov[np.ix_(cluster_indices, cluster_indices)]
        
        # Simple Inverse-variance weights within the cluster
        # v_i is the variance of asset i
        # Weight w_i = (1/v_i) / (sum(1/v_j))
        diag_elements = np.diag(cov_slice)
        ivp = 1.0 / np.where(diag_elements > 0, diag_elements, 1e-10)
        ivp /= ivp.sum()
        
        w = ivp.reshape(-1, 1)
        cluster_variance = (w.T @ cov_slice @ w)[0, 0]
        return cluster_variance

    def get_rec_bisec(self, cov: np.ndarray, sort_ix: List[int]) -> pd.Series:
        """
        Recursive bisection to find allocation weights.
        """
        w = pd.Series(1.0, index=sort_ix)
        top_clusters = [sort_ix]
        
        while len(top_clusters) > 0:
            new_clusters = []
            for cluster in top_clusters:
                if len(cluster) <= 1:
                    continue
                # Split current cluster into two halves
                half = len(cluster) // 2
                c1 = cluster[:half]
                c2 = cluster[half:]
                
                # Compute variance of each half
                v1 = self.get_cluster_var(cov, c1)
                v2 = self.get_cluster_var(cov, c2)
                
                # Risk parity split: allocation alpha = 1 - v1/(v1+v2)
                alpha = 1.0 - v1 / (v1 + v2)
                
                # Apply weights recursively
                for idx in c1:
                    w[idx] *= alpha
                for idx in c2:
                    w[idx] *= (1.0 - alpha)
                
                new_clusters.extend([c1, c2])
            top_clusters = new_clusters
        return w

    def compute_hrp_weights(self, returns_df: pd.DataFrame) -> Dict[str, float]:
        """
        Main HRP entry point.
        Returns a dictionary of {symbol: weight}.
        """
        if returns_df.empty:
            return {}
            
        symbols = returns_df.columns.tolist()
        n = len(symbols)
        if n == 1:
            return {symbols[0]: 1.0}
            
        # 1. Covariance matrix
        cov = returns_df.cov().values
        
        # 2. Distance Matrix Calculation (simplified for robustness)
        # Using correlation distance directly for clustering
        corr = returns_df.corr().values
        dist = np.sqrt(np.clip(0.5 * (1.0 - corr), 0, 1))
        
        # 3. Simple Clustering: Sort by average correlation to the leader
        # This provides a stable, deterministic quasi-diagonalization for small portfolios
        # High volatility assets are grouped separately
        leader_idx = np.argmax(np.mean(corr, axis=1)) # Broadest correlated asset
        sorted_indices = list(np.argsort(corr[leader_idx]))
        
        # 4. Recursive Bisection
        hrp_weights = self.get_rec_bisec(cov, sorted_indices)
        
        # Clean up output
        result = {}
        for i, weight in hrp_weights.items():
            result[symbols[i]] = float(weight)
            
        return result

if __name__ == "__main__":
    # Test with dummy data
    import random
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOTUSDT', 'LINKUSDT']
    data = {}
    np.random.seed(42)
    for sym in symbols:
        data[sym] = np.random.normal(0.001, 0.03, 100)
    
    # Force correlation between BTC and others
    df = pd.DataFrame(data)
    df['ETHUSDT'] = df['BTCUSDT'] * 0.85 + df['ETHUSDT'] * 0.15
    df['SOLUSDT'] = df['BTCUSDT'] * 0.70 + df['SOLUSDT'] * 0.30
    
    hrp = HierarchicalRiskParity()
    weights = hrp.compute_hrp_weights(df)
    
    print("\n🏢 HRP Portfolio Weights (Institutional Allocation):")
    total_w = 0
    for sym, w in sorted(weights.items(), key=lambda x: x[1], reverse=True):
        print(f"  {sym}: {w:6.2%}")
        total_w += w
    print(f"  {'='*15}\n  Total: {total_w:6.2%}")
