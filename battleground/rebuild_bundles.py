#!/usr/bin/env python3
"""Rebuild baby bundles with actual forward-tested strategy names."""
import glob
import json
from datetime import datetime, timezone
from pathlib import Path

DASHBOARD = Path(__file__).parent / "data" / "baby_strats_dashboard.json"
ROOT = Path(__file__).resolve().parents[1]

def main():
    data = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    strats = data.get("strategies", [])

    # Build strategy lookup with forward data
    strat_map = {}
    for s in strats:
        ft = s.get("forward_trades", [])
        if not ft:
            continue
        wins = sum(1 for t in ft if (t.get("pnl_pct") or 0) > 0)
        pnl = sum(t.get("pnl_pct", 0) or 0 for t in ft)
        wr = wins / len(ft) * 100 if ft else 0
        dirs = set()
        for t in ft:
            d = str(t.get("direction", "")).upper()
            if "LONG" in d or "BUY" in d:
                dirs.add("LONG")
            elif "SHORT" in d or "SELL" in d:
                dirs.add("SHORT")
        strat_map[s["name"]] = {
            "closed": len(ft), "wins": wins, "losses": len(ft) - wins,
            "wr": wr, "pnl": pnl, "directions": dirs,
            "category": s.get("category", ""),
        }

    # Also load backtest sweep results for strategies without forward trades
    bt_map = {}
    sweep_files = sorted(glob.glob(str(ROOT / "incubator" / "backtest_results" / "real_data_sweep_*.json")))
    if sweep_files:
        sweep = json.loads(Path(sweep_files[-1]).read_text(encoding="utf-8"))
        for r in sweep.get("results", []):
            if r.get("status") == "passed":
                wr = (r.get("win_rate") or 0) * 100
                bt_map[r["strategy_name"]] = {
                    "closed": r.get("total_trades", 0),
                    "wins": int(r.get("total_trades", 0) * (r.get("win_rate") or 0)),
                    "losses": r.get("total_trades", 0) - int(r.get("total_trades", 0) * (r.get("win_rate") or 0)),
                    "wr": wr,
                    "pnl": (r.get("total_return") or 0) * 100,
                    "directions": set(),
                    "category": "",
                    "source": "backtest",
                }

    # Define new bundles based on actual forward-tested strategies
    bundles = [
        {
            "bundle_id": "bundle_proven_winners_long_20260304",
            "name": "Proven Winners (Long Only)",
            "classification": {"symbol_scope": "multi_symbol", "timeframe_scope": "multi_timeframe", "direction_bias": "long_only"},
            "strategies": ["crypto_rsi_whaleconfirmed_v1", "multi_period_rsi_confluence", "drawdown_recovery_rsi", "atr_regime_rsi"],
        },
        {
            "bundle_id": "bundle_kalman_vwap_meanrev_20260304",
            "name": "Hybrid Quant Mean Reversion",
            "classification": {"symbol_scope": "multi_symbol", "timeframe_scope": "multi_timeframe", "direction_bias": "both_directions"},
            "strategies": ["crypto_kalman_trend_residual_reversion_v1", "crypto_vwap_deviation_reversion_volfilter_v1", "crypto_vwap_volprofile_reversion_v1", "crypto_choppiness_regime_switch_v1"],
        },
        {
            "bundle_id": "bundle_proven_aggressive_20260309",
            "name": "Proven Winners Aggressive (More Signals)",
            "classification": {"symbol_scope": "multi_symbol", "timeframe_scope": "multi_timeframe", "direction_bias": "both_directions"},
            "strategies": [
                "vwap_reversion_aggressive",
                "drawdown_recovery_rsi_eth_agg",
                "multi_rsi_confluence_eth_agg",
                "multi_rsi_confluence_xrp_agg",
                "triple_rsi_fast",
                "vwap_rsi_combo",
                "drawdown_recovery_rsi_fast",
            ],
        },
        {
            "bundle_id": "bundle_orb_pivots_20260304",
            "name": "ORB Pivot Traders (Social-Inspired)",
            "classification": {"symbol_scope": "single_symbol", "timeframe_scope": "multi_timeframe", "direction_bias": "both_directions"},
            "strategies": ["crypto_soc_mtf_orb_pivots_a01_v1", "crypto_soc_mtf_orb_pivots_a02_v1", "crypto_soc_mtf_orb_pivots_a07_v1", "crypto_soc_mtf_orb_pivots_a08_v1"],
        },
        {
            "bundle_id": "bundle_proxy_decoupling_20260304",
            "name": "Proxy Decoupling Alpha",
            "classification": {"symbol_scope": "single_symbol", "timeframe_scope": "multi_timeframe", "direction_bias": "both_directions"},
            "strategies": ["crypto_soc_proxy_decoupling_a01_v1", "crypto_soc_proxy_decoupling_a02_v1", "crypto_soc_proxy_decoupling_a06_v1", "crypto_soc_proxy_decoupling_a08_v1"],
        },
        {
            "bundle_id": "bundle_orderflow_absorption_20260304",
            "name": "Orderflow Absorption (High Volume)",
            "classification": {"symbol_scope": "multi_symbol", "timeframe_scope": "single_timeframe", "direction_bias": "both_directions"},
            "strategies": ["crypto_soc_orderflow_absorption_a01_v1", "crypto_soc_orderflow_absorption_a02_v1", "crypto_soc_orderflow_absorption_a06_v1", "crypto_soc_orderflow_absorption_a08_v1"],
        },
        {
            "bundle_id": "bundle_delta_divergence_20260304",
            "name": "Delta Divergence Scanner",
            "classification": {"symbol_scope": "multi_symbol", "timeframe_scope": "multi_timeframe", "direction_bias": "both_directions"},
            "strategies": ["crypto_soc_delta_divergence_a01_v1", "crypto_soc_delta_divergence_a06_v1", "crypto_soc_delta_divergence_a02_v1", "crypto_soc_delta_divergence_a08_v1"],
        },
        {
            "bundle_id": "bundle_dynamic_risk_heat_20260304",
            "name": "Dynamic Risk Heat Map",
            "classification": {"symbol_scope": "single_symbol", "timeframe_scope": "multi_timeframe", "direction_bias": "both_directions"},
            "strategies": ["crypto_soc_dynamic_risk_heat_a01_v1", "crypto_soc_dynamic_risk_heat_a02_v1", "crypto_soc_dynamic_risk_heat_a07_v1", "crypto_soc_dynamic_risk_heat_a08_v1"],
        },
        {
            "bundle_id": "bundle_volume_momentum_20260304",
            "name": "Volume & Momentum Blend",
            "classification": {"symbol_scope": "multi_symbol", "timeframe_scope": "single_timeframe", "direction_bias": "both_directions"},
            "strategies": ["crypto_volume_spike_momentum_v1", "crypto_mtf_ema_slope_alignment_v1", "mean_reversion_momentum", "volume_breakout_regime_switch"],
        },
        {
            "bundle_id": "bundle_vol_expansion_20260304",
            "name": "Volatility Expansion Index",
            "classification": {"symbol_scope": "single_symbol", "timeframe_scope": "single_timeframe", "direction_bias": "long_only"},
            "strategies": ["crypto_soc_vol_expansion_index_a01_v1", "crypto_soc_vol_expansion_index_a02_v1", "crypto_soc_vol_expansion_index_a08_v1"],
        },
        {
            "bundle_id": "bundle_funding_momentum_20260304",
            "name": "Funding Rate Momentum (High Freq)",
            "classification": {"symbol_scope": "multi_symbol", "timeframe_scope": "single_timeframe", "direction_bias": "both_directions"},
            "strategies": ["funding_momentum"],
        },
        {
            "bundle_id": "bundle_volume_breakout_20260305",
            "name": "Volume-Confirmed Breakout",
            "classification": {"symbol_scope": "multi_symbol", "timeframe_scope": "multi_timeframe", "direction_bias": "long_only"},
            "strategies": [
                "vwap_reclaim_volume_surge",
                "relative_volume_breakout",
                "engulfing_pattern_filter",
                "crypto_keltner_compression_expansion_v1",
            ],
        },
        {
            "bundle_id": "bundle_crossasset_divergence_20260305",
            "name": "Cross-Asset Divergence Quant",
            "classification": {"symbol_scope": "multi_symbol", "timeframe_scope": "multi_timeframe", "direction_bias": "both_directions"},
            "strategies": [
                "crossasset_spxbtc_zscore_divergence_v1",
                "crypto_drawdown_convexity_recovery_v1",
                "dxy_weekly_drop",
                "crypto_entropy_hurst_dual_engine_v1",
            ],
        },
        {
            "bundle_id": "bundle_shortterm_ignition_20260305",
            "name": "Short-Term Ignition Pack",
            "classification": {"symbol_scope": "single_symbol", "timeframe_scope": "single_timeframe", "direction_bias": "both_directions"},
            "strategies": [
                "crypto_shortterm_nr_er_vwma_ignition_v1",
                "crypto_shortterm_nr_er_keltner_ignition_v1",
                "crypto_shortterm_nr_er_cci_ignition_v1",
                "crypto_shortterm_nr_er_obv_ignition_v1",
            ],
        },
    ]

    now = datetime.now(timezone.utc).isoformat()
    for b in bundles:
        fwd_closed = 0
        fwd_wins = 0
        fwd_pnl = 0.0
        bt_closed = 0
        bt_wins = 0
        bt_pnl = 0.0
        for sn in b["strategies"]:
            fwd = strat_map.get(sn)
            if fwd:
                fwd_closed += fwd.get("closed", 0)
                fwd_wins += fwd.get("wins", 0)
                fwd_pnl += fwd.get("pnl", 0)
            else:
                bt = bt_map.get(sn, {})
                bt_closed += bt.get("closed", 0)
                bt_wins += bt.get("wins", 0)
                bt_pnl += bt.get("pnl", 0)

        total_closed = fwd_closed + bt_closed
        total_wins = fwd_wins + bt_wins
        total_pnl = fwd_pnl + bt_pnl
        wr = total_wins / total_closed * 100 if total_closed > 0 else 0
        fwd_wr = fwd_wins / fwd_closed * 100 if fwd_closed > 0 else 0

        # Confidence: forward-confirmed (>50% trades from forward),
        # mixed (some forward), or backtest-projected (no forward)
        if fwd_closed > 0 and fwd_closed >= total_closed * 0.5:
            confidence = "forward-confirmed"
        elif fwd_closed > 0:
            confidence = "mixed"
        else:
            confidence = "backtest-projected"

        b["backtest"] = {
            "sharpe": 0, "win_rate": round(wr, 1), "max_dd": 0,
            "trades": total_closed, "total_return": round(total_pnl, 2),
        }
        b["forward"] = {
            "status": "paper", "start_date": "2026-02-27",
            "sharpe": 0, "win_rate": round(fwd_wr, 1) if fwd_closed else round(wr, 1), "max_dd": 0,
            "trades": fwd_closed,
            "realized_pnl": round(fwd_pnl, 2), "unrealized_pnl": 0,
        }
        b["confidence"] = confidence
        b["trade_breakdown"] = {
            "forward_trades": fwd_closed,
            "backtest_trades": bt_closed,
            "forward_wr": round(fwd_wr, 1) if fwd_closed else None,
            "backtest_wr": round(bt_wins / bt_closed * 100, 1) if bt_closed else None,
            "blended_wr": round(wr, 1),
        }
        b["quality_score"] = round(wr * min(total_closed / 50, 1), 1)
        b["rank"] = 0

    bundles.sort(key=lambda x: x["quality_score"], reverse=True)
    for i, b in enumerate(bundles):
        b["rank"] = i + 1

    sections = data.get("sections", [])
    bundle_idx = next(
        (i for i, s in enumerate(sections) if s.get("section") == "BUNDLE_BABIES_TOP"),
        None,
    )
    new_section = {
        "section": "BUNDLE_BABIES_TOP",
        "description": "Forward-tested strategy bundles - THE MAIN THING",
        "updated_at": now,
        "bundles": bundles,
    }
    if bundle_idx is not None:
        sections[bundle_idx] = new_section
    else:
        sections.insert(0, new_section)

    data["sections"] = sections
    DASHBOARD.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print("=== BUNDLES REGENERATED ===")
    for b in bundles:
        tb = b["trade_breakdown"]
        conf = b["confidence"]
        conf_tag = {"forward-confirmed": "FWD", "mixed": "MIX", "backtest-projected": "BT"}[conf]
        wr = tb["blended_wr"]
        pnl = b["backtest"]["total_return"]
        fwd_t = tb["forward_trades"]
        bt_t = tb["backtest_trades"]
        print(f"  #{b['rank']} [{conf_tag:>3}] {b['name']:<40} fwd={fwd_t:>3} bt={bt_t:>3} WR={wr:>5.1f}% PnL={pnl:>+8.2f}%")

    print(f"\nTotal bundles: {len(bundles)}")
    print("Dashboard JSON updated.")


if __name__ == "__main__":
    main()
