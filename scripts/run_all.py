#!/usr/bin/env python3
"""
Master orchestrator for Smart Money Intelligence + World-Class Algorithm scripts.

Usage:
  python run_all.py --all           Run everything
  python run_all.py --13f           SEC 13F tracker only
  python run_all.py --insider       Insider tracker only
  python run_all.py --wsb           WSB sentiment only
  python run_all.py --consensus     Consensus engine only (always runs)
  python run_all.py --perf          Performance tracker only
  python run_all.py --regime        Regime detector (HMM + Hurst + Macro)
  python run_all.py --sizing        Position sizer (Half-Kelly + EWMA)
  python run_all.py --meta          Meta-labeler (XGBoost training)
  python run_all.py --alphas        WorldQuant alphas + cross-asset
  python run_all.py --bundles       Signal bundle consolidation
  python run_all.py --validate      Walk-forward validation
  python run_all.py --finbert       FinBERT sentiment analysis
  python run_all.py --cusum         CUSUM change-point decay detection
  python run_all.py --optimize      Bayesian hyperparameter optimization
  python run_all.py --congress      Congressional trading tracker
  python run_all.py --options       Options flow / Gamma Exposure (GEX)
  python run_all.py --onchain       On-chain crypto analytics
  python run_all.py --portfolio     Black-Litterman + Risk Parity optimizer
  python run_all.py --entropy       Transfer entropy causal analysis
  python run_all.py --commission    Commission impact analysis + trade frequency optimization
  python run_all.py --pause         Auto-pause failing algorithms (>20 consecutive losses)
  python run_all.py --prune         Correlation pruner (remove >0.7 correlated signals)
  python run_all.py --ensemble      Ensemble model stacking
  python run_all.py --features      Automated feature selection (RFE + LASSO + Boruta)
  python run_all.py --stoploss      Stop-loss failure analysis + gap protection
  python run_all.py --dynsize       Dynamic volatility-based position sizing
  python run_all.py --momcrash      Momentum crash protection (VIX + MVR gate)
  python run_all.py --fred           FRED macro overlay (yield curve, VIX, unemployment)
  python run_all.py --deploy        Alpha engine deployment
  python run_all.py                 Consensus engine only (default)

Multiple flags can be combined:
  python run_all.py --13f --wsb --regime   Run 13F + WSB + regime + consensus
  python run_all.py --finbert --cusum --congress  Run Sprint 1 quick wins
  python run_all.py --commission --pause --prune  Run Phase 0 emergency triage

Exit code: 0 if all steps succeed, 1 if any step fails.
"""
import sys
import os
import traceback
import logging

# Ensure scripts directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('run_all')


def run_step(name, func):
    """Run a step, catch errors, continue."""
    try:
        logger.info(f"=== Starting: {name} ===")
        result = func()
        logger.info(f"=== Completed: {name} ===")
        return True
    except Exception as e:
        logger.error(f"=== FAILED: {name} -- {e} ===")
        traceback.print_exc()
        return False


def main():
    results = {}
    args = sys.argv[1:]
    run_all = '--all' in args

    logger.info("=" * 60)
    logger.info("Smart Money Intelligence — Master Orchestrator")
    logger.info(f"Arguments: {args if args else '(none — consensus only)'}")
    logger.info("=" * 60)

    # Step 1: SEC 13F (weekly — run with --13f or --all)
    if '--13f' in args or run_all:
        from sec_13f_tracker import main as sec_13f_main
        results['sec_13f'] = run_step('SEC 13F Tracker', sec_13f_main)

    # Step 2: Insider Tracker
    if '--insider' in args or run_all:
        from insider_tracker import main as insider_main
        results['insider'] = run_step('Insider Tracker', insider_main)

    # Step 3: WSB Sentiment
    if '--wsb' in args or run_all:
        from wsb_sentiment import main as wsb_main
        results['wsb'] = run_step('WSB Sentiment', wsb_main)

    # Step 4: Consensus Engine (always runs unless a specific flag is given)
    if '--consensus' in args or run_all or not any(
        flag in args for flag in ['--13f', '--insider', '--wsb', '--perf',
                                  '--regime', '--sizing', '--meta', '--alphas',
                                  '--bundles', '--validate', '--finbert',
                                  '--cusum', '--optimize', '--congress',
                                  '--options', '--onchain', '--portfolio',
                                  '--entropy', '--commission', '--pause',
                                  '--prune', '--ensemble', '--features',
                                  '--stoploss', '--dynsize', '--momcrash',
                                  '--fred', '--deploy']
    ):
        from consensus_engine import main as consensus_main
        results['consensus'] = run_step('Consensus Engine', consensus_main)

    # Step 5: Performance Tracker
    if '--perf' in args or run_all:
        from performance_tracker import main as perf_main
        results['performance'] = run_step('Performance Tracker', perf_main)

    # ─── World-Class Algorithm Steps ─────────────────────────────────

    # Step 6: Regime Detector (HMM + Hurst + Macro)
    if '--regime' in args or run_all:
        from regime_detector import run_regime_detection
        results['regime'] = run_step('Regime Detector', run_regime_detection)

    # Step 7: Position Sizer (Half-Kelly + EWMA)
    if '--sizing' in args or run_all:
        from position_sizer import run_position_sizing
        results['sizing'] = run_step('Position Sizer', run_position_sizing)

    # Step 8: Meta-Labeler (XGBoost training)
    if '--meta' in args or run_all:
        from meta_labeler import main as meta_main
        results['meta_labeler'] = run_step('Meta-Labeler', meta_main)

    # Step 9: WorldQuant Alphas + Cross-Asset
    if '--alphas' in args or run_all:
        from worldquant_alphas import run_worldquant_alphas
        results['worldquant'] = run_step('WorldQuant Alphas', run_worldquant_alphas)

    # Step 10: Signal Bundle Consolidation
    if '--bundles' in args or run_all:
        from signal_bundles import run_bundle_analysis
        results['bundles'] = run_step('Signal Bundles', run_bundle_analysis)

    # Step 11: Walk-Forward Validation
    if '--validate' in args or run_all:
        from walk_forward_validator import run_validation
        results['validation'] = run_step('Walk-Forward Validation', run_validation)

    # ─── Bridge Plan: Sprint 1 — Quick Wins ──────────────────────────

    # Step 12: FinBERT Sentiment (Sprint 1.1)
    if '--finbert' in args or run_all:
        from finbert_sentiment import main as finbert_main
        results['finbert'] = run_step('FinBERT Sentiment', finbert_main)

    # Step 13: CUSUM Change-Point Detection (Sprint 1.2)
    if '--cusum' in args or run_all:
        from cusum_detector import main as cusum_main
        results['cusum'] = run_step('CUSUM Decay Detector', cusum_main)

    # Step 14: Bayesian Hyperparameter Optimization (Sprint 1.3)
    if '--optimize' in args or run_all:
        from hyperparam_optimizer import main as optimize_main
        results['optimizer'] = run_step('Bayesian Hyperparam Optimizer', optimize_main)

    # Step 15: Congressional Trading Tracker (Sprint 1.5)
    if '--congress' in args or run_all:
        from congress_tracker import main as congress_main
        results['congress'] = run_step('Congressional Tracker', congress_main)

    # ─── Bridge Plan: Sprint 2 — Alt Data + Portfolio ────────────────

    # Step 16: Options Flow / GEX (Sprint 2.1)
    if '--options' in args or run_all:
        from options_flow import main as options_main
        results['options'] = run_step('Options Flow / GEX', options_main)

    # Step 17: On-Chain Analytics (Sprint 2.2)
    if '--onchain' in args or run_all:
        from onchain_analytics import main as onchain_main
        results['onchain'] = run_step('On-Chain Analytics', onchain_main)

    # Step 18: Portfolio Optimizer — Black-Litterman + Risk Parity (Sprint 2.3+2.4)
    if '--portfolio' in args or run_all:
        from portfolio_optimizer import main as portfolio_main
        results['portfolio'] = run_step('Portfolio Optimizer', portfolio_main)

    # Step 19: Transfer Entropy — Causal Signal Detection (Sprint 2.5)
    if '--entropy' in args or run_all:
        from transfer_entropy_analyzer import main as entropy_main
        results['entropy'] = run_step('Transfer Entropy Analyzer', entropy_main)

    # ─── OPUS46 Phase 0: Emergency Triage ─────────────────────────────

    # Step 20: Commission Eliminator — analyze commission drag + optimize trade frequency
    if '--commission' in args or run_all:
        from commission_eliminator import main as commission_main
        results['commission'] = run_step('Commission Eliminator', commission_main)

    # Step 21: Algorithm Pauser — auto-pause failing algos (>20 consecutive losses)
    if '--pause' in args or run_all:
        from algorithm_pauser import main as pauser_main
        results['pauser'] = run_step('Algorithm Pauser', pauser_main)

    # Step 22: Correlation Pruner — remove >0.7 correlated signals
    if '--prune' in args or run_all:
        from corr_pruner import main as prune_main
        results['pruner'] = run_step('Correlation Pruner', prune_main)

    # Step 23: Ensemble Stacker — combine ML models via stacking
    if '--ensemble' in args or run_all:
        from ensemble_stacker import main as ensemble_main
        results['ensemble'] = run_step('Ensemble Stacker', ensemble_main)

    # Step 24: Feature Selector — RFE + LASSO + Boruta consensus feature selection
    if '--features' in args or run_all:
        from feature_selector import main as features_main
        results['features'] = run_step('Feature Selector', features_main)

    # Step 25: Stop-Loss Analyzer — investigate SL failures + gap protection
    if '--stoploss' in args or run_all:
        from stop_loss_analyzer import main as stoploss_main
        results['stoploss'] = run_step('Stop-Loss Analyzer', stoploss_main)

    # Step 26: Dynamic Position Sizer — volatility-based risk management
    if '--dynsize' in args or run_all:
        from dynamic_position_sizer import main as dynsize_main
        results['dynsize'] = run_step('Dynamic Position Sizer', dynsize_main)

    # Step 27: Momentum Crash Protector — disable momentum in high-vol regimes
    if '--momcrash' in args or run_all:
        from momentum_crash_protector import MomentumCrashProtector
        def _momcrash_run():
            protector = MomentumCrashProtector()
            tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'META',
                        'AMZN', 'AMD', 'SPY', 'QQQ', 'BTC-USD', 'ETH-USD']
            safe = protector.protect_portfolio(tickers)
            logger.info(f"Momentum safe: {len(safe)}/{len(tickers)} tickers")
        results['momcrash'] = run_step('Momentum Crash Protector', _momcrash_run)

    # ─── OPUS46 Phase 2: Macro Intelligence ───────────────────────────

    # Step 28: FRED Macro Overlay — yield curve, VIX, unemployment, Fed funds
    if '--fred' in args or run_all:
        from fred_macro import main as fred_main
        results['fred_macro'] = run_step('FRED Macro Overlay', fred_main)

    # Step 29: Alpha Engine Deployer — deploy production alpha engine
    if '--deploy' in args or run_all:
        from alpha_engine_deployer import main as deploy_main
        results['deployer'] = run_step('Alpha Engine Deployer', deploy_main)

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("MASTER ORCHESTRATOR SUMMARY")
    logger.info("=" * 60)

    all_ok = True
    for step, ok in results.items():
        status = "OK" if ok else "FAILED"
        if not ok:
            all_ok = False
        logger.info(f"  {step:20s}: {status}")

    if not results:
        logger.info("  (no steps were run)")

    logger.info("=" * 60)

    if all_ok:
        logger.info("All steps completed successfully.")
    else:
        logger.error("One or more steps FAILED. Check logs above for details.")

    # Exit with error if any step failed
    if not all_ok:
        sys.exit(1)


if __name__ == '__main__':
    main()
