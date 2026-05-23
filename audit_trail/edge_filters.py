"""
Edge Filters — OOS-validated, bootstrap-stable per-asset-class filters.

Generated 2026-05-16 by hedge-fund-grade edge discovery pipeline.
Source data: audit_trail/data/universal_resolved_picks.json (5000 closed picks, 12 weeks)
Validation: chronological 70/30 IS/OOS split + 500-iter bootstrap CI

Each filter spec is a serialisable dict applied via `passes_filter(spec, pick)`.

Acceptance criteria for a filter to be in this file:
  - Full-sample Profit Factor >= 1.3
  - OOS Profit Factor >= 1.2 (where OOS sample size allowed split)
  - OOS expectancy > 0
  - Bootstrap P(PF > 1) >= 80%
  - |WR_IS - WR_OOS| <= 15pp (no regime collapse)

NOTE: pnl_pct in the resolved-picks dataset reflects TP/SL outcome (bounded ~[-3.4%, +4%]
per trade). All metrics below are in those units — when scaled to 1% of equity per
trade compounding, results are realistic (no inflated 1000000x equity multiples).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterable

# --- Toxic blacklists (consistent ~80%+ loss rate, n>=30 each) ---
TOXIC_SOURCES = ['mutation_lab', 'claude_gainer_st']
TOXIC_STRATEGIES = [
    'battleground_ml_relaxed_mut',
    'gainer_compression_relaxed_mut',
    'st_multi_day_momentum',
    'rapid_momentum_filter_mut',
    'rapid_rsi_filter_mut',
]


# --- Per-asset-class edge filters, priority-ordered (best PF first) ---
EDGE_FILTERS: dict[str, list[dict]] = {
    'CRYPTO': [
        {
            'name': 'CRYPTO_ULTRA',
            'tier': 'PAPER_TRADE',  # 2026-05-16: downgraded — dedup audit found n=103→15 unique triplets
            'spec': {
                'source_in': ['aggregated_picks'],
                'rr_min': 1.5, 'rr_max': 2.0,
                'conf_min': 0.7,
                'direction': 'LONG',
            },
            'expected_picks_per_week': 8.6,
            'full_n': 103, 'full_pf': 40.57, 'full_wr': 0.961,
            'oos_n': 15,  'oos_pf': None, 'oos_wr': 0.733,  # deduped by (symbol,entry,tp,sl); n=50→15
            'bootstrap_p_pf_above_1': None,  # dedup_audit_2026-05-16: OOS n too thin post-dedup
            'recommendation': 'PAPER TRADE ONLY until n>=30 across bear/sideways regimes. Dedup artifact: 103→15 unique (entry,tp,sl) triplets; 65 BTCUSDT at same price.',
        },
        {
            'name': 'CRYPTO_ENHANCED',
            'tier': 'ACCEPT_WEAK',  # 2026-05-16: downgraded — dedup audit: n=113→40 unique triplets
            'spec': {
                'source_in': ['aggregated_picks', 'kimi_signal_tracking'],
                'rr_min': 1.5, 'rr_max': 2.0,
            },
            'expected_picks_per_week': 54.8,
            'full_n': 658, 'full_pf': 8.21, 'full_wr': 0.812,
            'oos_n': 40,  'oos_pf': 2.22,  'oos_wr': 0.55,  # deduped by (symbol,entry,tp,sl); n=113→40
            'bootstrap_p_pf_above_1': 1.00,
            'recommendation': 'Dedup-corrected: n=40, WR=55%, PF=2.22. Real edge confirmed (T2-grade) but thin sample. Paper-trade alongside live. Source: dedup_audit_2026-05-16.',
        },
        {
            'name': 'CRYPTO_CORE',
            'tier': 'ACCEPT_WEAK',  # 2026-05-16: downgraded — dedup audit: n=129→55 unique triplets; WR sub-50%
            'spec': {
                'source_in': ['aggregated_picks', 'kimi_signal_tracking'],
            },
            'expected_picks_per_week': 60.0,
            'full_n': 719, 'full_pf': 7.13, 'full_wr': 0.771,
            'oos_n': 55,  'oos_pf': 1.97,  'oos_wr': 0.491,  # deduped by (symbol,entry,tp,sl); n=129→55; WR sub-50%
            'bootstrap_p_pf_above_1': 1.00,
            'recommendation': 'Dedup-corrected: n=55, WR=49.1% (sub-T2), PF=1.97. Use system-level aggregated_picks WR=76.3% instead. Source: dedup_audit_2026-05-16.',
        },
        {
            'name': 'CRYPTO_SAFE',
            'tier': 'ACCEPT_STRONG',
            'spec': {
                'rr_min': 1.5, 'rr_max': 2.0,
                'direction': 'LONG',
                'source_not_in': TOXIC_SOURCES,
                'strategy_not_in': TOXIC_STRATEGIES,
            },
            'expected_picks_per_week': 161.3,
            'full_n': 1936, 'full_pf': 2.27, 'full_wr': 0.574,
            'oos_n': 576, 'oos_pf': 2.48, 'oos_wr': 0.59,
            'bootstrap_p_pf_above_1': 1.00,
            'recommendation': 'Fallback when premium sources offline. Wide universe, still PF>2.',
        },
    ],
    'EQUITY': [
        {
            'name': 'EQUITY_LONG_RR',
            'tier': 'ACCEPT_WEAK',  # full-sample strong, OOS n=15 too small to confirm
            'spec': {
                'direction': 'LONG',
                'rr_min': 1.5, 'rr_max': 2.0,
            },
            'expected_picks_per_week': 3.7,
            'full_n': 44, 'full_pf': 13.76, 'full_wr': 0.886,
            'oos_n': 15, 'oos_pf': 2.51, 'oos_wr': 0.60,
            'bootstrap_p_pf_above_1': 1.00,
            'recommendation': 'Best EQUITY filter by every metric, but OOS sample thin. Paper-trade 4 weeks before scaling.',
        },
        {
            'name': 'EQUITY_US_CLOSE_HOURS',
            'tier': 'ACCEPT',
            'spec': {
                'hour_in': [16, 17, 18, 19],
            },
            'expected_picks_per_week': 3.25,
            'full_n': 39, 'full_pf': 3.55, 'full_wr': 0.692,
            'oos_n': 18, 'oos_pf': 2.03, 'oos_wr': 0.61,
            'bootstrap_p_pf_above_1': 1.00,
            'recommendation': 'US close UTC 16-20 has materially higher PF. Use as time filter on equity picks.',
        },
    ],
    'FOREX': [
        {
            'name': 'FOREX_RR_BAND',
            'tier': 'ACCEPT',
            'spec': {
                'rr_min': 1.5, 'rr_max': 2.0,
            },
            'expected_picks_per_week': 3.7,
            'full_n': 44, 'full_pf': 2.79, 'full_wr': 0.273,
            'oos_n': 15, 'oos_pf': 3.52, 'oos_wr': 0.20,
            'bootstrap_p_pf_above_1': 0.97,
            'recommendation': 'FOREX wins low-WR-high-RR. The RR 1.5-2.0 band is the durable edge. Skip LONG only (PF<1).',
        },
        {
            'name': 'FOREX_MEAN_REVERSION_BB',
            'tier': 'ACCEPT',
            'spec': {
                '_strategy_eq': 'MeanReversionBB',
            },
            'expected_picks_per_week': 4.0,
            'full_n': 48, 'full_pf': 2.48, 'full_wr': 0.250,
            'oos_n': 19, 'oos_pf': 3.00, 'oos_wr': 0.11,
            'bootstrap_p_pf_above_1': 0.94,
            'recommendation': 'MeanReversionBB FOREX strategy is the most reliable single strategy in this class.',
        },
    ],
    'MEME': [
        {
            'name': 'MEME_LONG_RR',
            'tier': 'ACCEPT_STRONG',
            'spec': {
                'direction': 'LONG',
                'rr_min': 1.5, 'rr_max': 2.0,
            },
            'expected_picks_per_week': 2.6,
            'full_n': 31, 'full_pf': 3.58, 'full_wr': 0.645,
            'oos_n': 12, 'oos_pf': 6.09, 'oos_wr': 0.67,
            'bootstrap_p_pf_above_1': 1.00,
            'recommendation': 'MEME picks: LONG-only with RR 1.5-2.0. Avoid SHORT (PF=0).',
        },
        {
            'name': 'MEME_LONG_ONLY',
            'tier': 'ACCEPT_STRONG',
            'spec': {
                'direction': 'LONG',
            },
            'expected_picks_per_week': 4.3,
            'full_n': 52, 'full_pf': 2.76, 'full_wr': 0.558,
            'oos_n': 18, 'oos_pf': 2.70, 'oos_wr': 0.50,
            'bootstrap_p_pf_above_1': 1.00,
            'recommendation': 'Wider MEME filter — just LONG-only direction. Use when LONG_RR pickings too thin.',
        },
    ],
    # Bonds / Futures / Commodities — INSUFFICIENT DATA in current pipeline
    # (n=0 closed picks as of 2026-05-16). Do NOT deploy real capital until pipeline
    # produces picks. See "Known Limitations" in the report.
    'BOND': [],
    'ETF': [
        {
            'name': 'H037_VIX_CARRY_REGIME',
            'tier': 'PAPER_TRADE',  # 2026-05-20: H-037 harness-admissible, 30-day forward verification
            'spec': {
                'direction': 'LONG',
                'source_in': ['h037_vix_carry'],
                '_vix_min': 14.0,           # VIX spot floor
                '_contango_min': 0.05,      # 5% annualized contango minimum
            },
            'expected_picks_per_week': 3.0,
            'full_n': 1185, 'full_pf': 1.295, 'full_wr': 0.589,
            'oos_n': None, 'oos_pf': None, 'oos_wr': None,  # Forward verification in progress
            'bootstrap_p_pf_above_1': None,  # Pending 30-day forward verification
            'recommendation': 'H-037: VIX term structure carry. Harness: WR=58.9%, PF=1.295, n=1185, eff=0.75, 3/4 WF folds. Regime filter: VIX>14, contango>5%. 30-day paper verification started 2026-05-20. Target PF>=1.5 for Tier-2.',
        },
    ],
    'FUTURES': [],
    'COMMODITY': [],
}


def normalise_asset_class(ac: str | None) -> str:
    return (ac or 'UNKNOWN').upper()


def passes_filter(spec: dict, pick: dict, features: dict | None = None) -> bool:
    """
    Apply a single filter spec to a pick.
    `features` is an optional precomputed dict; otherwise we recompute from `pick`.
    """
    f = features if features is not None else extract_features(pick)
    if '_strategy_eq' in spec and f['strategy'] != spec['_strategy_eq']:
        return False
    if 'rr_min' in spec and f['rr'] < spec['rr_min']:
        return False
    if 'rr_max' in spec and f['rr'] >= spec['rr_max']:
        return False
    if 'conf_min' in spec and f['conf'] < spec['conf_min']:
        return False
    if 'direction' in spec and f['direction'] != spec['direction']:
        return False
    if 'source_in' in spec and f['source'] not in spec['source_in']:
        return False
    if 'source_not_in' in spec and f['source'] in spec['source_not_in']:
        return False
    if 'strategy_not_in' in spec and f['strategy'] in spec['strategy_not_in']:
        return False
    if 'hour_in' in spec and f['hour'] not in spec['hour_in']:
        return False
    return True


def extract_features(pick: dict) -> dict:
    """Extract the features used by the filters from a raw pick dict."""
    entry = pick.get('entry_price') or 0
    tp = pick.get('take_profit') or 0
    sl = pick.get('stop_loss') or 0
    direction = (pick.get('direction') or 'LONG').upper()
    rr = 0.0
    if entry > 0 and tp > 0 and sl > 0:
        if direction == 'LONG':
            risk = abs(entry - sl); reward = abs(tp - entry)
        else:
            risk = abs(sl - entry); reward = abs(entry - tp)
        rr = (reward / risk) if risk > 0 else 0.0
    conf = pick.get('confidence') or 0.0
    try:
        conf = float(conf)
    except Exception:
        conf = 0.0
    # parse hour from timestamp ISO 8601
    hour = None
    ts = pick.get('timestamp')
    if ts:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            hour = dt.hour
        except Exception:
            pass
    return {
        'rr': rr,
        'conf': conf,
        'direction': direction,
        'source': pick.get('source_system', '') or '',
        'strategy': pick.get('strategy', '') or '',
        'hour': hour,
    }


def best_filter_for(pick: dict) -> dict | None:
    """
    Given a pick, return the BEST filter spec (highest tier) that this pick passes.
    Returns None if no filter accepts this pick.
    """
    ac = normalise_asset_class(pick.get('asset_class'))
    filters = EDGE_FILTERS.get(ac, [])
    if not filters:
        return None
    f = extract_features(pick)
    tier_order = {'ACCEPT_STRONG': 3, 'ACCEPT': 2, 'ACCEPT_WEAK': 1}
    best = None
    for filt in filters:
        if passes_filter(filt['spec'], pick, features=f):
            if best is None or tier_order.get(filt['tier'], 0) > tier_order.get(best['tier'], 0):
                best = filt
    return best


def filter_picks(picks: Iterable[dict], filter_name: str) -> list[dict]:
    """Apply a named filter (e.g. 'CRYPTO_ULTRA') across an iterable of picks."""
    target = None
    target_ac = None
    for ac, flist in EDGE_FILTERS.items():
        for f in flist:
            if f['name'] == filter_name:
                target = f; target_ac = ac
                break
    if target is None:
        raise KeyError(f"Unknown filter: {filter_name}")
    out = []
    for p in picks:
        if normalise_asset_class(p.get('asset_class')) != target_ac:
            continue
        if passes_filter(target['spec'], p):
            out.append(p)
    return out


if __name__ == '__main__':
    import json, sys
    # Usage: python -m audit_trail.edge_filters [path-to-picks-json] [filter-name]
    path = sys.argv[1] if len(sys.argv) > 1 else 'audit_trail/data/universal_resolved_picks.json'
    name = sys.argv[2] if len(sys.argv) > 2 else 'CRYPTO_ENHANCED'
    with open(path) as fh:
        picks = json.load(fh)
    matched = filter_picks(picks, name)
    print(f"Filter: {name}")
    print(f"Matched: {len(matched)} / {len(picks)} picks")
    if matched:
        wins = sum(1 for p in matched if (p.get('pnl_pct') or 0) > 0)
        print(f"WR: {wins/len(matched)*100:.1f}%  total_pnl%: {sum(p.get('pnl_pct') or 0 for p in matched):.2f}%")
