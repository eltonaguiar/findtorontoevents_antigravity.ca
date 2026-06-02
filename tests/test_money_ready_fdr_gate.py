"""Tests for the ENHANCEMENT #64 multiple-testing (Bonferroni/BH-FDR) pre-gate
in alpha_engine/money_ready_verdict.py. Pure-function tests — no DB/pipeline."""
import os
import sys
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "alpha_engine"))
import money_ready_verdict as m  # noqa: E402


def _strat_picks(name, mean, sd, n, seed):
    rng = random.Random(seed)
    return [{"strategy": name, "pnl_pct": mean + rng.gauss(0, sd)} for _ in range(n)]


def test_one_sided_pvalue_strong_winner_is_tiny():
    p = m._one_sided_t_pvalue([1.0] * 30)   # zero-variance certain win
    assert p == 0.0


def test_one_sided_pvalue_small_sample_returns_none():
    assert m._one_sided_t_pvalue([1.0] * (m.MIN_N_STRATEGY - 1)) is None


def test_fdr_gate_passes_with_a_real_winner():
    picks = _strat_picks("strong", 1.0, 0.4, 40, 1) + _strat_picks("noise", 0.0, 1.0, 30, 2)
    g = m._fdr_gate(picks)
    assert g["ok"] is True
    assert g["n_fdr_pass"] >= 1
    assert g["n_tested"] == 2


def test_fdr_gate_fail_open_with_single_strategy():
    g = m._fdr_gate(_strat_picks("only", 1.0, 0.4, 30, 3))
    assert g["ok"] is None          # <2 testable strategies -> never blocks
    assert g["n_tested"] == 1


def test_verdict_shadow_default_does_not_downgrade():
    # flag OFF: a failing FDR gate must NOT change the verdict
    assert m._FDR_GATE_ENFORCE is False
    v = m._verdict(200, 0.60, 2.0, {"ok": True}, {"ok": True}, {"ok": True},
                   asset_class="CRYPTO", top_symbol_share=0.1, top_source_share=0.1,
                   mdd_cvar_gate_ok=None, fdr_gate_ok=False)
    assert v == "MONEY_READY"


def test_verdict_enforced_downgrades_only_on_explicit_false(monkeypatch):
    monkeypatch.setattr(m, "_FDR_GATE_ENFORCE", True)
    common = dict(asset_class="CRYPTO", top_symbol_share=0.1, top_source_share=0.1,
                  mdd_cvar_gate_ok=None)
    assert m._verdict(200, 0.60, 2.0, {"ok": True}, {"ok": True}, {"ok": True},
                      fdr_gate_ok=False, **common) == "NOT_READY"
    assert m._verdict(200, 0.60, 2.0, {"ok": True}, {"ok": True}, {"ok": True},
                      fdr_gate_ok=True, **common) == "MONEY_READY"
    # None (insufficient strategies) is fail-open — must not downgrade
    assert m._verdict(200, 0.60, 2.0, {"ok": True}, {"ok": True}, {"ok": True},
                      fdr_gate_ok=None, **common) == "MONEY_READY"


# --- ENHANCEMENT #65: single-source-artifact gate ---

def _src_picks(name, src, mean, n, seed):
    rng = random.Random(seed)
    return [{"strategy": name, "source_system": src,
             "pnl_pct": mean + rng.gauss(0, 0.5)} for _ in range(n)]


def test_single_source_gate_flags_all_single_source_profitable():
    # two profitable sleeves, each from one (different) source -> both single-source
    picks = _src_picks("a", "feedX", 0.5, 30, 1) + _src_picks("b", "feedY", 0.5, 30, 2)
    g = m._single_source_gate(picks)
    assert g["ok"] is False
    assert g["n_profitable_multi_source"] == 0
    assert g["n_profitable_single_source"] == 2


def test_single_source_gate_ok_with_a_multi_source_sleeve():
    multi = _src_picks("m", "feedX", 0.5, 20, 3) + _src_picks("m", "feedY", 0.5, 20, 4)
    g = m._single_source_gate(multi)
    assert g["ok"] is True
    assert g["n_profitable_multi_source"] >= 1


def test_single_source_gate_fail_open_when_no_profitable():
    g = m._single_source_gate(_src_picks("loser", "feedX", -0.5, 30, 5))
    assert g["ok"] is None


def test_verdict_single_source_enforced_downgrade(monkeypatch):
    monkeypatch.setattr(m, "_SINGLE_SOURCE_GATE_ENFORCE", True)
    common = dict(asset_class="CRYPTO", top_symbol_share=0.1, top_source_share=0.1,
                  mdd_cvar_gate_ok=None)
    assert m._verdict(200, 0.60, 2.0, {"ok": True}, {"ok": True}, {"ok": True},
                      single_source_gate_ok=False, **common) == "NOT_READY"
    assert m._verdict(200, 0.60, 2.0, {"ok": True}, {"ok": True}, {"ok": True},
                      single_source_gate_ok=True, **common) == "MONEY_READY"
