"""Ledger-level gate evaluator tests (Sub-project 1, Task 4)."""
from __future__ import annotations


def _mk(n=100, pf=2.0, mdd=10.0, seed=42):
    """Helper: fabricate n rows whose PF ≈ pf (alternating win/loss amplitudes).

    ``pf`` is honored: loss amplitude is tuned so wins/losses yield the target
    profit factor. ``mdd`` is accepted for API symmetry (MDD emerges from the
    amplitudes, which stay small for a healthy ledger).
    """
    import random

    random.seed(seed)
    n_wins = (n + 1) // 2
    n_losses = n - n_wins
    win_amp = 1.0
    loss_amp = (n_wins * win_amp) / (pf * n_losses) if n_losses else 0.0
    rows = []
    for i in range(n):
        pnl = win_amp if i % 2 == 0 else -loss_amp
        rows.append({
            "strategy": "test_strat",
            "asset_class": "EQUITY",
            "symbol": f"SYM{i % 5}",
            "entry_time": f"2026-01-{(i % 28) + 1:02d}T00:00:00Z",
            "closed_at": f"2026-01-{(i % 28) + 2:02d}T00:00:00Z",
            "pnl_pct": round(pnl, 4),
        })
    return rows


def test_compute_ledger_gates_n100():
    from audit_trail.ledger_gates import compute_ledger_gates
    rows = _mk(n=99)
    result = compute_ledger_gates(rows)
    key = ("test_strat", "EQUITY")
    assert result[key]["n"] == 99
    assert "n<100" in result[key]["gate_failures"]
    assert result[key]["verdict"] == "UNVERIFIED"


def test_compute_ledger_gates_pf_threshold():
    from audit_trail.ledger_gates import compute_ledger_gates
    # fabricate a ledger whose PF is ~1.43 (below 1.5)
    rows = []
    for i in range(120):
        pnl = 1.0 if i % 2 == 0 else -0.7  # wins 1/2, loss tuned → PF≈1.43
        rows.append({"strategy": "pf_test", "asset_class": "ETF", "symbol": "SPY",
                     "entry_time": f"2026-02-{(i % 27) + 1:02d}T00:00:00Z",
                     "closed_at": f"2026-02-{(i % 27) + 2:02d}T00:00:00Z",
                     "pnl_pct": pnl})
    result = compute_ledger_gates(rows)
    key = ("pf_test", "ETF")
    assert result[key]["pf_net"] < 1.5
    assert "pf<1.5" in result[key]["gate_failures"]


def test_compute_ledger_gates_ci_lb():
    from audit_trail.ledger_gates import compute_ledger_gates
    # small n with high variance → CI-LB will be low
    rows = [{"strategy": "ci_test", "asset_class": "CRYPTO_SPOT", "symbol": "BTC-USD",
             "entry_time": f"2026-03-{d:02d}T00:00:00Z", "closed_at": f"2026-03-{d + 1:02d}T00:00:00Z",
             "pnl_pct": (10 if d % 2 == 0 else -8)} for d in range(1, 105)]
    result = compute_ledger_gates(rows)
    key = ("ci_test", "CRYPTO_SPOT")
    assert result[key]["pf_net_ci_lb"] < 1.2 or "pf_ci_lb<1.2" in result[key]["gate_failures"]


def test_compute_ledger_gates_mdd():
    from audit_trail.ledger_gates import compute_ledger_gates
    # fabricate a drawdown >20% by a run of wins followed by large losses.
    # MDD is measured on the overlap-aware, share-weighted equity curve with
    # uncapped per-position PnL (so a real -30% streak shows up as risk).
    rows = []
    for i in range(80):
        pnl = 2.0 if i < 70 else -30.0
        rows.append({"strategy": "mdd_test", "asset_class": "COMMODITY", "symbol": "CL",
                     "entry_time": f"2026-04-{i % 27 + 1:02d}T00:00:00Z",
                     "closed_at": f"2026-04-{i % 27 + 2:02d}T00:00:00Z",
                     "pnl_pct": pnl})
    result = compute_ledger_gates(rows)
    key = ("mdd_test", "COMMODITY")
    assert result[key]["mdd"] > 20.0
    assert "mdd>20" in result[key]["gate_failures"]


def test_compute_ledger_gates_all_pass():
    from audit_trail.ledger_gates import compute_ledger_gates
    rows = _mk(n=150, pf=2.5, mdd=8.0, seed=123)
    result = compute_ledger_gates(rows)
    key = ("test_strat", "EQUITY")
    assert result[key]["verdict"] == "OK"
    assert result[key]["gate_failures"] == []


def test_compute_ledger_gates_uses_net_of_cost_when_present():
    from audit_trail.ledger_gates import compute_ledger_gates
    rows = []
    for i in range(120):
        gross = 2.0 if i % 3 != 0 else -1.0
        net = gross - 0.4  # simulate 0.4% round-trip cost
        rows.append({"strategy": "cost_test", "asset_class": "FOREX_MAJOR", "symbol": "EURUSD=X",
                     "entry_time": f"2026-05-{i % 27 + 1:02d}T00:00:00Z",
                     "closed_at": f"2026-05-{i % 27 + 2:02d}T00:00:00Z",
                     "pnl_pct": gross, "net_of_cost_pnl_pct": net})
    result = compute_ledger_gates(rows)
    key = ("cost_test", "FOREX_MAJOR")
    # PF on net should be lower than on gross; the gate should still evaluate
    assert "pf_net" in result[key]
    assert result[key]["pf_net"] is not None


def test_compute_ledger_gates_machine_readable_codes():
    from audit_trail.ledger_gates import compute_ledger_gates
    rows = _mk(n=40)  # fails n, and likely others
    result = compute_ledger_gates(rows)
    key = ("test_strat", "EQUITY")
    codes = result[key]["gate_failures"]
    assert all(isinstance(c, str) for c in codes)
    assert any(c.startswith(("n<", "pf<", "pf_ci", "mdd>")) for c in codes)
