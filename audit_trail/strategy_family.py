"""
Strategy-family attribution: name -> family, with the judgement made explicit.

WHY THIS FILE EXISTS
--------------------
The operator approved "strategy_family attribution -> /audit" as the top priority with three
conditions, and this module exists to satisfy all three:

  (i)   ADDITIVE ONLY. `universal_pick_resolver._extract_pick_fields` gains two keys
        (`strategy_family`, `strategy_family_provenance`). No existing key is renamed,
        reordered or removed. Consumers that ignore the new keys are unaffected.

  (ii)  THE MAPPING IS A JUDGEMENT, NOT A MEASUREMENT, AND IS LABELLED AS SUCH.
        Every value produced here carries a provenance tag:
            "declared"  the pick record itself stated a family -- trusted as-is
            "mapped"    we matched a name pattern -> THIS IS A JUDGEMENT
            "unmapped"  nothing matched; family is "unknown" and we say so
        The rule table is committed at reports/strategy_family_mapping.json so a reviewer can
        disagree with a specific rule rather than with an opaque function.

  (iii) AFTER BACKFILL, THE 80% CLAIM MUST BE RE-RUN. tools/hub_signal_share.py --by-family
        does that. The claim is a hypothesis now; the test is the deliverable.

WHY "mapped" IS NOT "declared"
------------------------------
A scanner named `breakout_a_sr` is *named* breakout. It does not follow that the logic is
breakout -- and it certainly does not follow that the strategy INSIDE `aggregated_picks` is
momentum, because a scanner name says nothing about the family of the signal it emits. This
module therefore refuses to guess from a system name alone when it can see the strategy name,
and marks everything inferred.

Usage:
    from audit_trail.strategy_family import family_of
    fam, prov = family_of(strategy="volume_spike_breakout", system="alpha_engine")
"""
from __future__ import annotations

import json
import re
from pathlib import Path

FAMILIES = (
    "momentum", "breakout", "mean_reversion", "trend_following", "volatility",
    "carry", "funding_carry", "pairs_trading", "value_quality", "prediction_market",
    "copy_trade", "contrarian", "positioning", "regime", "ensemble", "ml_composite",
    "gainer_chase", "unknown",
)

# ORDERED RULES — first match wins. ORDER IS PART OF THE MAPPING, not an implementation detail.
#
# BUGFIX 2026-11-23: the first draft put `momentum` before `mean_reversion` and matched a bare
# `rsi`, which misfiled B_flip_PriceRocMeanReversion as momentum (the name says MeanReversion)
# and would have misfiled every `*_rsi_*` combo. Two changes: mean_reversion now precedes
# momentum, and the reversion pattern no longer matches a bare `rsi` -- only constructs that
# actually signal reversion. Indicator names (macd/stochrsi/supertrend) stay momentum.
_RULES: list[tuple[str, str]] = [
    # -- the three families the hub's claim is about, kept first and explicit --
    (r"breakout|squeeze|spike|donchian|channel",                      "breakout"),
    (r"ichimoku",                                                      "trend_following"),
    # mean_reversion BEFORE momentum: 'PriceRocMeanReversion' must not read as momentum.
    (r"reversion|meanrev|mean_rev|fade|zscore|bounce|divergence",      "mean_reversion"),
    (r"momentum|momo|tsmom|roc|macd|stochrsi|supertrend",              "momentum"),
    # -- other families --
    (r"trend|ema|faber|moving_average|sma",                            "trend_following"),
    (r"atr|volatility|bb_|bollinger",                                  "volatility"),
    (r"funding",                                                       "funding_carry"),
    (r"carry",                                                         "carry"),
    (r"pairs|cointegrat|spread_arb",                                   "pairs_trading"),
    (r"bab|qmj|hml|value|quality|junk|betting_against_beta",           "value_quality"),
    (r"prediction_market|polymarket|kalshi|consensus_market",          "prediction_market"),
    (r"clone_hl_copy|copy_trader|copy_|analyst",                        "copy_trade"),
    (r"contrarian|sentiment|ig_|fear_greed",                           "contrarian"),
    (r"cot|positioning",                                               "positioning"),
    (r"regime",                                                        "regime"),
    (r"ensemble|combined_confidence|confluence|consensus|voting|vote", "ensemble"),
    (r"gainer|top_gainer|gainers",                                     "gainer_chase"),
    (r"ml_|_ml\b|lstm|xgb|transformer|neural",                          "ml_composite"),
]

_COMPILED = [(re.compile(p, re.I), fam) for p, fam in _RULES]

# Explicit strategy-name overrides beat pattern order. These are the cases where a naive
# pattern read would be wrong, kept here so the correction is visible and reviewable.
_OVERRIDES: dict[str, str] = {
    # MACD is a momentum indicator, but a "confluence" of MACD+RSI is closer to an ensemble
    # vote than a pure momentum signal; keep it momentum (explicit) so the rule is auditable.
    "macd_rsi_confluence": "momentum",
    "prediction_market_consensus": "prediction_market",
    "combined_confidence": "ensemble",
    "clone_hl_copy_lb_None": "copy_trade",
}

MAPPING_PATH = Path("reports/strategy_family_mapping.json")


def _classify(name: str) -> str | None:
    key = (name or "").strip().lower()
    if not key:
        return None
    if key in _OVERRIDES:
        return _OVERRIDES[key]
    for rx, fam in _COMPILED:
        if rx.search(key):
            return fam
    return None


def family_of(strategy: str | None = None, system: str | None = None) -> tuple[str, str]:
    """Return (family, provenance).

    Strategy name wins over system name: a scanner's name does not describe the signal it
    emits, so falling back to it is a weaker inference and is still marked "mapped".
    """
    for candidate in (strategy, system):
        fam = _classify(candidate or "")
        if fam:
            return fam, "mapped"
    return "unknown", "unmapped"


def is_claim_family(family: str) -> bool:
    """The three families named in the hub's '80%+' claim."""
    return family in ("momentum", "breakout", "trend_following")


def dump_mapping(extra_names: list[str] | None = None) -> dict:
    """Emit the committed rule table so a reviewer can challenge a specific rule."""
    rows = []
    for name in sorted(set(extra_names or [])):
        fam, prov = family_of(name, None)
        rows.append({"name": name, "family": fam, "provenance": prov})
    return {
        "generated_for": "operator condition (ii): the mapping is a judgement, committed for review",
        "status": "JUDGEMENT_NOT_MEASUREMENT",
        "families": list(FAMILIES),
        "ordered_rules": [{"pattern": p, "family": f} for p, f in _RULES],
        "explicit_overrides": _OVERRIDES,
        "claim_families": ["momentum", "breakout", "trend_following"],
        "note": (
            "First match wins, so rule ORDER is part of the mapping. 'breakout' precedes "
            "'momentum' deliberately. Changing the order changes the answer and should be "
            "treated as a new trial."
        ),
        "resolved_names": rows,
    }


if __name__ == "__main__":
    import sys

    names = sys.argv[1:]
    out = dump_mapping(names)
    MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
    MAPPING_PATH.write_text(json.dumps(out, indent=1))
    print(f"wrote {MAPPING_PATH}  ({len(out['resolved_names'])} names)")
    for r in out["resolved_names"]:
        print(f"  {r['provenance']:8s} {r['family']:16s} {r['name']}")
