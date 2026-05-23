"""
Incubator — Permutation Engine
================================
Generates parameter permutations using Latin Hypercube Sampling (LHS)
for uniform coverage of the search space with controlled sample count.

Supports:
  - Latin Hypercube Sampling (default, scipy.stats.qmc)
  - Sobol sequences (quasi-random, lower discrepancy)
  - Grid sampling (fallback if scipy unavailable)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .parameter_space import Param, StrategyArchetype, ARCHETYPES


@dataclass
class Permutation:
    """A single parameter permutation ready for backtesting."""
    perm_id: str
    archetype: str
    params: dict[str, Any]
    seed_strategy: str = ""  # which live strategy inspired this

    def to_dict(self) -> dict:
        return {
            "perm_id": self.perm_id,
            "archetype": self.archetype,
            "params": self.params,
            "seed_strategy": self.seed_strategy,
        }

    @staticmethod
    def make_id(archetype: str, params: dict) -> str:
        """Deterministic hash ID from archetype + params."""
        raw = f"{archetype}::{json.dumps(params, sort_keys=True)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]


def generate_permutations(
    archetypes: list[StrategyArchetype] | None = None,
    total_budget: int = 8000,
    method: str = "lhs",
    seed: int = 42,
) -> list[Permutation]:
    """Generate parameter permutations across all archetypes.

    Args:
        archetypes: List of archetypes to permute. Defaults to all.
        total_budget: Total permutation budget across all archetypes.
        method: 'lhs' (Latin Hypercube), 'sobol', or 'grid'.
        seed: Random seed for reproducibility.

    Returns:
        List of Permutation objects ready for backtesting.
    """
    if archetypes is None:
        archetypes = ARCHETYPES

    # Allocate budget proportionally to parameter space size
    total_combos = sum(a.total_combos() for a in archetypes)
    allocations = {}
    for a in archetypes:
        # Proportional allocation with minimum of 50 per archetype
        share = max(50, int(total_budget * a.total_combos() / max(total_combos, 1)))
        allocations[a.name] = min(share, a.total_combos())

    # Scale down if over budget
    total_alloc = sum(allocations.values())
    if total_alloc > total_budget:
        scale = total_budget / total_alloc
        allocations = {k: max(20, int(v * scale)) for k, v in allocations.items()}

    print(f"[permutation_engine] Generating {sum(allocations.values())} permutations "
          f"across {len(archetypes)} archetypes (method={method})")

    all_perms: list[Permutation] = []
    for archetype in archetypes:
        n_samples = allocations.get(archetype.name, 50)
        perms = _sample_archetype(archetype, n_samples, method, seed)
        all_perms.extend(perms)
        seed += 1  # different seed per archetype

    print(f"[permutation_engine] Total permutations generated: {len(all_perms)}")
    return all_perms


def _sample_archetype(
    archetype: StrategyArchetype,
    n_samples: int,
    method: str,
    seed: int,
) -> list[Permutation]:
    """Sample n_samples parameter sets for a single archetype."""
    params = archetype.params
    n_dims = len(params)

    if n_dims == 0:
        return []

    # Generate unit hypercube samples [0, 1]^d
    if method == "lhs":
        samples = _latin_hypercube(n_samples, n_dims, seed)
    elif method == "sobol":
        samples = _sobol_sequence(n_samples, n_dims, seed)
    else:
        samples = _grid_sample(n_samples, n_dims, seed)

    # Map unit samples to actual parameter values
    permutations = []
    for i in range(n_samples):
        param_dict = {}
        for j, p in enumerate(params):
            val = _map_to_param(samples[i, j], p)
            param_dict[p.name] = val

        perm_id = Permutation.make_id(archetype.name, param_dict)
        permutations.append(Permutation(
            perm_id=perm_id,
            archetype=archetype.name,
            params=param_dict,
        ))

    return permutations


def _map_to_param(unit_val: float, param: Param) -> Any:
    """Map a [0, 1] value to the actual parameter range."""
    if param.dtype == "bool":
        return bool(unit_val >= 0.5)

    raw = param.min_val + unit_val * (param.max_val - param.min_val)

    if param.dtype == "int":
        if param.step > 0:
            # Snap to grid
            raw = param.min_val + round((raw - param.min_val) / param.step) * param.step
        return int(round(raw))

    if param.step > 0:
        raw = param.min_val + round((raw - param.min_val) / param.step) * param.step

    return round(raw, 6)


def _latin_hypercube(n: int, d: int, seed: int) -> np.ndarray:
    """Latin Hypercube Sampling. Uses scipy if available, else manual."""
    try:
        from scipy.stats.qmc import LatinHypercube
        sampler = LatinHypercube(d=d, seed=seed)
        return sampler.random(n=n)
    except ImportError:
        return _manual_lhs(n, d, seed)


def _manual_lhs(n: int, d: int, seed: int) -> np.ndarray:
    """Manual LHS implementation (no scipy dependency)."""
    rng = np.random.default_rng(seed)
    samples = np.zeros((n, d))
    for j in range(d):
        # Divide [0, 1] into n equal strata, sample one point per stratum
        perm = rng.permutation(n)
        for i in range(n):
            samples[i, j] = (perm[i] + rng.random()) / n
    return samples


def _sobol_sequence(n: int, d: int, seed: int) -> np.ndarray:
    """Sobol quasi-random sequence. Falls back to LHS if scipy unavailable."""
    try:
        from scipy.stats.qmc import Sobol
        sampler = Sobol(d=d, seed=seed)
        # Sobol requires power-of-2 samples, take closest
        m = int(np.ceil(np.log2(max(n, 2))))
        raw = sampler.random_base2(m=m)
        return raw[:n]
    except ImportError:
        return _manual_lhs(n, d, seed)


def _grid_sample(n: int, d: int, seed: int) -> np.ndarray:
    """Uniform grid sampling with jitter."""
    rng = np.random.default_rng(seed)
    # n_per_dim = n^(1/d), but approximate
    n_per_dim = max(2, int(n ** (1.0 / d)))
    grids = [np.linspace(0, 1, n_per_dim) for _ in range(d)]
    mesh = np.array(np.meshgrid(*grids)).T.reshape(-1, d)
    # Add small jitter
    mesh += rng.uniform(-0.02, 0.02, mesh.shape)
    mesh = np.clip(mesh, 0, 1)
    # Subsample if too many
    if len(mesh) > n:
        idx = rng.choice(len(mesh), n, replace=False)
        mesh = mesh[idx]
    return mesh


if __name__ == "__main__":
    perms = generate_permutations(total_budget=100)  # small test
    print(f"\nSample permutations (first 5):")
    for p in perms[:5]:
        print(f"  [{p.archetype}] {p.perm_id}: {p.params}")
