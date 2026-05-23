"""Unit tests for tools/data_integrity/feature_drift.py."""
from __future__ import annotations

import json
import os
import random
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from tools.data_integrity import feature_drift as fd  # noqa: E402


def test_manual_ks_similar_distributions():
    random.seed(0)
    a = [random.gauss(0, 1) for _ in range(200)]
    b = [random.gauss(0, 1) for _ in range(200)]
    p = fd._manual_ks_pvalue(a, b)
    assert p > 0.05  # shouldn't flag


def test_manual_ks_shifted_distributions():
    random.seed(1)
    a = [random.gauss(0, 1) for _ in range(200)]
    b = [random.gauss(3, 1) for _ in range(200)]
    p = fd._manual_ks_pvalue(a, b)
    assert p < 0.001


def test_kl_hist_identical_is_zero():
    a = [1.0, 2.0, 3.0, 4.0, 5.0] * 20
    kl = fd.kl_hist(a, list(a))
    assert abs(kl) < 1e-6


def test_kl_hist_shifted_is_positive():
    a = [1.0, 2.0, 3.0] * 30
    b = [7.0, 8.0, 9.0] * 30
    assert fd.kl_hist(a, b) > 1.0


def test_main_detects_drift(tmp_path):
    rows = []
    # Historical: confidence ~ 0.3
    for i in range(60):
        rows.append({
            "created_at": "2026-02-01 00:00:00",
            "confidence": 0.3 + (i % 5) * 0.01,
            "pnl_pct": 1.0, "risk_reward": 2.0,
        })
    # Recent: confidence ~ 0.8
    for i in range(60):
        rows.append({
            "created_at": "2026-04-10 00:00:00",
            "confidence": 0.8 + (i % 5) * 0.01,
            "pnl_pct": 1.0, "risk_reward": 2.0,
        })
    p = tmp_path / "closed.json"
    p.write_text(json.dumps(rows))
    rc = fd.main([
        "--closed", str(p),
        "--now", "2026-04-12T00:00:00Z",
        "--window-days", "30",
        "--min-n", "20",
        "--alpha", "0.01",
    ])
    assert rc == 2  # drift detected


def test_main_no_drift(tmp_path):
    rows = []
    for i in range(60):
        rows.append({
            "created_at": "2026-02-01 00:00:00",
            "confidence": 0.5, "pnl_pct": 1.0, "risk_reward": 2.0,
        })
    for i in range(60):
        rows.append({
            "created_at": "2026-04-10 00:00:00",
            "confidence": 0.5, "pnl_pct": 1.0, "risk_reward": 2.0,
        })
    p = tmp_path / "closed.json"
    p.write_text(json.dumps(rows))
    rc = fd.main([
        "--closed", str(p),
        "--now", "2026-04-12T00:00:00Z",
        "--window-days", "30",
    ])
    assert rc == 0
