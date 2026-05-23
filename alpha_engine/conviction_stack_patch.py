"""
conviction_stack_patch.py — Drop-in patch for alpha_engine/conviction_stack.py

QUANT TEAM FIX (2026-04-09):

IMPORTANT: This patch has been REVERTED to stricter thresholds due to analysis showing:
- confidence >= 0.80 as proxy for n==0 is a cognitive bias (someone sounding confident ≠ being right)
- The original relaxed thresholds let through too much unvalidated noise
- Result: High conviction filter was performing at coin-toss levels (47-52% WR)

Changes (v2 → v3):
1. REMOVED: confidence >= 0.80 fallback when forward_trades == 0 (HARMFUL)
2. Reverted to stricter thresholds: n >= 5, wr >= 55, elite in [41,80]
3. Added hard gates: trust_tier SANDBOX/UNPROVEN auto-reject
4. Added overconfidence kill: conf > 0.90 with < 20 trades → auto-reject

Apply: copy the relevant functions into conviction_stack.py, replacing the originals.
"""

from typing import Any, Optional


# === PATCH 1: Relaxed _wr_elite_ok with fallback ===
# Replace the inner _wr_elite_ok function in classify_hf_conviction_tier

def _wr_elite_ok_strict(pick: dict, n: int, wr: float, elite: float, 
                             emin: float, emax: float, min_wr: float, min_n: int) -> bool:
    """
    Strict WR/elite check - NO confidence fallback.
    
    Quant team fix: Removed the dangerous "confidence as proxy for missing data" fallback.
    This was causing high-conviction picks to have coin-toss performance because
    unvalidated picks with high confidence were making it through.
    
    Requirements:
    - n >= min_n (typically 5)
    - wr >= min_wr (typically 55)
    - elite in [emin, emax] (typically [41, 80])
    
    Additional hard gates:
    - trust_tier SANDBOX/UNPROVEN/PROBATION/DEMOTED → fail
    - confidence > 0.90 AND forward_trades < 20 → fail (overconfidence is anti-predictive)
    """
    # GATE: Check trust tier - no unvalidated systems in high conviction
    trust_tier = str(pick.get("trust_tier", pick.get("Trust Tier", ""))).upper()
    if trust_tier in ("SANDBOX", "UNPROVEN", "PROBATION", "DEMOTED"):
        return False
    
    # GATE: Kill overconfidence - per quant analysis, extreme confidence is anti-predictive
    conf = pick.get("confidence", 0)
    if conf:
        conf_val = float(conf)
        if conf_val > 1:
            conf_val = conf_val / 100
        # Overconfident with insufficient track record
        fwd_trades = pick.get("forward_trades", pick.get("strat_fwd_trades", 0))
        try:
            fwd_trades = int(fwd_trades)
        except (TypeError, ValueError):
            fwd_trades = 0
        
        if conf_val > 0.90 and fwd_trades < 20:
            return False
    
    # Main gate: n, wr, elite thresholds
    if n >= min_n and wr >= min_wr and emin <= elite <= emax:
        return True
    
    return False


# === PATCH 2: Non-crypto tier classification ===
# Add after the existing Tier B INTRADAY block

NON_CRYPTO_TIER_B_STRATEGIES = {
    "pead_earnings_drift", "quality_minus_junk", "quality_value", 
    "earnings_drift", "pead",
}

NON_CRYPTO_TIER_A_STRATEGIES = {
    "pead_earnings_drift", "quality_value",
}


def classify_non_crypto_conviction(pick: dict, cfg: dict) -> tuple[Optional[str], list[str]]:
    """
    Non-crypto conviction tiers.
    
    Tier A: PEAD/quality strategies + confidence >= 0.82 + LONG + regime OK
    Tier B: PEAD/quality strategies + confidence >= 0.75
    """
    from alpha_engine.conviction_stack import _is_crypto_pick, _norm_sym, _pick_regime_blob, _regime_bull_neutral
    
    sym = _norm_sym(str(pick.get("symbol") or ""))
    if _is_crypto_pick(pick, sym):
        return None, []  # Crypto handled by existing logic
    
    strat = str(pick.get("strategy") or "").lower()
    direction = str(pick.get("direction") or "LONG").upper()
    conf = float(pick.get("confidence", 0) or 0)
    regime = _pick_regime_blob(pick)
    
    # Normalize confidence to 0-1
    if conf > 1:
        conf = conf / 100
    
    is_tier_a_strat = any(s in strat for s in NON_CRYPTO_TIER_A_STRATEGIES)
    is_tier_b_strat = any(s in strat for s in NON_CRYPTO_TIER_B_STRATEGIES)
    
    a_threshold = float(cfg.get("non_crypto_tier_a_confidence_threshold", 0.82))
    b_threshold = float(cfg.get("non_crypto_tier_b_confidence_threshold", 0.75))
    
    # Tier A: high-quality strategy + high confidence + regime OK
    if is_tier_a_strat and conf >= a_threshold and direction == "LONG":
        if _regime_bull_neutral(regime, cfg):
            return "A", ["non_crypto_pead_quality_high_conf"]
    
    # Tier B: proven strategy + decent confidence
    if is_tier_b_strat and conf >= b_threshold and direction == "LONG":
        return "B", ["non_crypto_proven_strategy_conf"]
    
    return None, []


# === PATCH 3: Integration instruction ===
# In classify_hf_conviction_tier(), before the final `return None, []`, add:
#
#     # Non-crypto tier paths
#     nc_tier, nc_reasons = classify_non_crypto_conviction(pick, cfg)
#     if nc_tier:
#         return nc_tier, nc_reasons
#
# Replace _wr_elite_ok() with _wr_elite_ok_strict() (no conf_threshold param).
# The confidence fallback was removed in v3 quant audit (2026-04-09).


if __name__ == '__main__':
    # Test with mock non-crypto picks
    test_picks = [
        {"symbol": "AAPL", "strategy": "pead_earnings_drift", "direction": "LONG",
         "confidence": 0.85, "regime": "bull", "asset_class": "EQUITY"},
        {"symbol": "PFE", "strategy": "quality_minus_junk", "direction": "LONG",
         "confidence": 0.76, "regime": "neutral", "asset_class": "EQUITY"},
        {"symbol": "XOM", "strategy": "momentum_cascade", "direction": "LONG",
         "confidence": 0.70, "regime": "bull", "asset_class": "EQUITY"},
    ]
    
    cfg = {"non_crypto_tier_a_confidence_threshold": 0.82, 
           "non_crypto_tier_b_confidence_threshold": 0.75,
           "bull_neutral_substrings": ["bull", "neutral"]}
    
    for pick in test_picks:
        tier, reasons = classify_non_crypto_conviction(pick, cfg)
        print(f"{pick['symbol']:6} {pick['strategy']:25} conf={pick['confidence']} → Tier: {tier} {reasons}")
