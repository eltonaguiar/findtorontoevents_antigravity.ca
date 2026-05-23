"""Smoke test for tools/feed_risk_metrics.py pipeline."""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

pytest.importorskip("arch", reason="arch package not installed; pip install arch")

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.feed_risk_metrics import run, SCHEMA_VERSION, PIPELINE_VERSION  # noqa: E402
from tools.pbo_cscv import compute_pbo  # noqa: E402
import numpy as np  # noqa: E402


def _synth_picks(n: int = 120, seed: int = 1) -> list[dict]:
    random.seed(seed)
    rng = random.Random(seed)
    asset_classes = ["CRYPTO", "EQUITY", "ETF", "FOREX", "COMMODITY"]
    strategies = [f"strat_{i}" for i in range(6)]
    picks = []
    for i in range(n):
        ac = rng.choice(asset_classes)
        s = rng.choice(strategies)
        # Mildly positive-expectancy distribution
        pnl = rng.gauss(0.15, 1.2)
        picks.append({
            "id": f"p{i}",
            "pnl_pct": pnl,
            "asset_class": ac,
            "strategy": s,
            "source_system": s,
            "trust_tier": rng.choice(["PROVEN", "RELIABLE", "UNTRUSTED"]),
            "grade": rng.choice(["A", "B", "C"]),
            "elite_score": rng.randint(40, 95),
            "closed_at": f"2026-01-{(i % 28) + 1:02d}T12:00:00Z",
            "forward_wr": rng.uniform(0.4, 0.7),
            "forward_trades": rng.randint(1, 20),
        })
    return picks


def test_pbo_noise_near_half():
    rng = np.random.default_rng(0)
    R = rng.standard_normal((320, 16))
    res = compute_pbo(R, S=16)
    assert res["pbo"] is not None
    # Noise should put PBO roughly mid-range; allow a broad band
    assert 0.2 <= res["pbo"] <= 0.85, f"PBO={res['pbo']}"


def test_pipeline_smoke():
    picks = _synth_picks(120)
    out = run(picks)
    # Schema basics
    assert out["schema_version"] == SCHEMA_VERSION
    assert out["pipeline_version"] == PIPELINE_VERSION
    assert "as_of" in out
    assert "feeds" in out and "All" in out["feeds"]

    feed_all = out["feeds"]["All"]
    # Required keys
    for k in (
        "n", "block_size", "insufficient_sample",
        "point_metrics_gross", "point_metrics_net",
        "bca_95_gross", "bca_95_net",
        "psr_vs_sr0", "dsr", "dsr_p_value", "pbo",
        "regime_decomposition", "banner_gate",
    ):
        assert k in feed_all, f"missing key {k}"

    # Banner gate structure
    bg = feed_all["banner_gate"]
    for k in ("pf_bca_lower_gt_1", "dsr_soft_signal", "pbo_le_0_5", "sample_ok", "banner_eligible"):
        assert k in bg

    # Point metric sanity
    pt = feed_all["point_metrics_gross"]
    assert pt["n"] == 120
    assert pt["wr"] is not None


if __name__ == "__main__":
    test_pbo_noise_near_half()
    test_pipeline_smoke()
    print("OK: all smoke tests passed")
