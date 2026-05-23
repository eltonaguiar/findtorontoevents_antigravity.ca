"""
KIMI_FEB172026 - Live Scanner (Main Integration)
Integrates all modules: Crypto Acceleration, ML Ranking, Elimination, SQLite Store
Provides live BUY NOW signals with TP/SL for crypto/forex/stocks
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

# Import our modules
from crypto_acceleration_engine import CryptoAccelerationEngine, SignalResult
from ml_signal_ranker import MLSignalRanker, SignalFeatures
from sqlite_store import SQLiteStore
from elimination_engine import EliminationEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KIMILiveScanner:
    """
    Main live scanner integrating all signal detection modules
    Generates BUY NOW signals with take profit and stop loss
    """
    
    VERSION = "11.0.0"
    ALGO_COUNT = 68
    
    def __init__(self):
        # Use data directory relative to this file's location
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize modules
        self.crypto_engine = CryptoAccelerationEngine()
        self.ml_ranker = MLSignalRanker(str(self.data_dir))
        self.store = SQLiteStore(str(self.data_dir / "kimi_trading.db"))
        self.elimination = EliminationEngine(str(self.data_dir))
        
        # Signal storage
        self.signals = []
        self.active_picks = []
        
        # Algorithm definitions (moved from after initialize() method)
        self.ALGO_DEFS = {
            # Core acceleration signals
            "pump-detector-scout": {
                "name": "Pump Acceleration Detector",
                "category": "crypto", 
                "tier": "TIER_1",
                "strategy": "PumpAcceleration",
                "symbols": ["BTC-USD","ETH-USD","SOL-USD","AVAX-USD","BNB-USD","DOGE-USD","PEPE-USD","FLOKI-USD","WIF-USD","BONK-USD","MATIC-USD","LINK-USD","INJ-USD","TIA-USD","SUI-USD"]
            },
            "telegram-call-scout": {
                "name": "Telegram Alpha Call Follower",
                "category": "crypto", 
                "tier": "TIER_1",
                "strategy": "TelegramCallFollower",
                "symbols": ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","AVAX-USD","ARB-USD","OP-USD","SUI-USD","APT-USD","TIA-USD","LINK-USD","INJ-USD","SEI-USD","JUP-USD","PYTH-USD"]
            },
            "order-book-imbalance-scout": {
                "name": "Order Book Imbalance (Binance)",
                "category": "crypto", 
                "tier": "TIER_1",
                "strategy": "OrderBookImbalance",
                "symbols": ["BTC-USD","ETH-USD","SOL-USD","AVAX-USD","BNB-USD","XRP-USD","ADA-USD","DOGE-USD","SHIB-USD","MATIC-USD","LINK-USD","DOT-USD","ATOM-USD","NEAR-USD","FIL-USD"]
            },
            "liquidation-cascade-scout": {
                "name": "Short Liquidation Cascade",
                "category": "crypto", 
                "tier": "TIER_1",
                "strategy": "LiquidationCascade",
                "symbols": ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","AVAX-USD","LINK-USD","MATIC-USD","XRP-USD","ADA-USD","INJ-USD","TIA-USD","SUI-USD","DOGE-USD"]
            },
            "twitter-alpha-scout": {
                "name": "Twitter Crypto Alpha Calls",
                "category": "crypto", 
                "tier": "TIER_1",
                "strategy": "TwitterAlphaFollower",
                "symbols": ["BTC-USD","ETH-USD","SOL-USD","AVAX-USD","BNB-USD","LINK-USD","DOGE-USD","PEPE-USD","ARB-USD","OP-USD","INJ-USD","TIA-USD","SUI-USD","SEI-USD","WIF-USD"]
            },
            "acceleration-burst-scout": {
                "name": "Momentum Acceleration (Jerk)",
                "category": "crypto",
                "tier": "TIER_1",
                "strategy": "AccelerationBurst",
                "symbols": ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","ADA-USD"]
            },
            "funding-reversal-scout": {
                "name": "Funding Rate Reversal",
                "category": "crypto",
                "tier": "TIER_1",
                "strategy": "FundingReversal",
                "symbols": ["BTC-USD","ETH-USD","SOL-USD","BNB-USD"]
            },
            "smc-order-block-scout": {
                "name": "SMC Order Block",
                "category": "crypto",
                "tier": "TIER_1",
                "strategy": "SMCOrderBlock",
                "symbols": ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD"]
            },
            "smc-fvg-scout": {
                "name": "SMC Fair Value Gap",
                "category": "crypto",
                "tier": "TIER_1",
                "strategy": "SMCFVG",
                "symbols": ["BTC-USD","ETH-USD","SOL-USD","BNB-USD"]
            },
            "whale-detector-scout": {
                "name": "Whale Trade Detector",
                "category": "crypto",
                "tier": "TIER_1",
                "strategy": "WhaleTrades",
                "symbols": ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD"]
            }
        }
    
    def initialize(self) -> bool:
        """Initialize the scanner - already done in __init__"""
        try:
            # Verify all components are ready
            if not self.store:
                logger.error("SQLite store not initialized")
                return False
            if not self.crypto_engine:
                logger.error("Crypto engine not initialized")
                return False
            logger.info("Live scanner initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            return False
    
    async def scan_crypto_signals(self) -> List[SignalResult]:
        """Run crypto acceleration engine scan"""
        logger.info("Scanning crypto acceleration signals...")
        return await self.crypto_engine.scan_all_signals()
    
    def rank_signals(self, signals: List[SignalResult]) -> List[Dict]:
        """Rank signals using ML model"""
        ranked = []
        
        # Get current market data
        market_data = self._get_market_data()
        
        for signal in signals:
            # Get algo stats
            algo_stats = self.store.get_algo_stats(signal.signal_type)
            
            # Extract features
            signal_dict = self.crypto_engine.to_dict(signal)
            features = self.ml_ranker.extract_features_from_signal(
                signal_dict, market_data, algo_stats
            )
            
            # Score signal
            win_prob = self.ml_ranker.score_signal(features)
            
            # Get recommended position size
            position_size = self.ml_ranker.recommend_position_size(win_prob)
            
            ranked.append({
                "signal": signal,
                "win_probability": win_prob,
                "position_size": position_size,
                "features": features,
                "algo_stats": algo_stats
            })
        
        # Sort by win probability
        ranked.sort(key=lambda x: x["win_probability"], reverse=True)
        return ranked
    
    def _get_market_data(self) -> Dict:
        """Get current market regime data"""
        # Try to get from database
        regime = self.store.get_current_regime()
        
        if regime:
            return {
                "regime": 1 if regime.get('regime') == 'bull' else -1 if regime.get('regime') == 'bear' else 0,
                "crypto_regime": 1 if regime.get('crypto_regime') == 'risk_on' else -1,
                "vix_proxy": 20.0,
                "hmm_confidence": regime.get('hmm_confidence', 0.5),
                "breadth_pct": regime.get('breadth_pct', 50.0),
                "vol_20d": regime.get('vol_20d', 0.02),
                "btc_eth_ratio": regime.get('btc_eth_ratio', 15.0),
                "fear_greed_crypto": 50.0,
                "fear_greed_stock": 50.0,
                "price_vs_52w_high": 0.75
            }
        
        # Default values
        return {
            "regime": 1,
            "crypto_regime": 1,
            "vix_proxy": 20.0,
            "hmm_confidence": 0.6,
            "breadth_pct": 60.0,
            "vol_20d": 0.025,
            "btc_eth_ratio": 16.0,
            "fear_greed_crypto": 55.0,
            "fear_greed_stock": 50.0,
            "price_vs_52w_high": 0.75
        }
    
    def save_signals_to_db(self, signals: List[Dict]):
        """Save generated signals to database"""
        for sig_data in signals:
            signal = sig_data["signal"]
            
            entry = {
                "timestamp": signal.timestamp.isoformat(),
                "algorithm": signal.signal_type,
                "tier": self.ALGO_DEFS.get(signal.signal_type, {}).get("tier", "SCOUT"),
                "strategy": self.ALGO_DEFS.get(signal.signal_type, {}).get("strategy", ""),
                "symbol": signal.symbol,
                "signal": signal.direction,
                "reason": signal.reason,
                "price": signal.entry_price,
                "regime": "bull",  # From market data
                "crypto_regime": "risk_on",
                "breadth_pct": 60.0,
                "vix_proxy": "normal",
                "hmm_confidence": sig_data["win_probability"],
                "metadata": {
                    "take_profit": signal.take_profit,
                    "stop_loss": signal.stop_loss,
                    "confidence": signal.confidence,
                    "win_probability": sig_data["win_probability"],
                    "position_size": sig_data["position_size"]
                }
            }
            
            self.store.write_signal(entry)
    
    def create_picks_from_signals(self, signals: List[Dict]) -> List[str]:
        """Create active picks from high-confidence signals"""
        pick_ids = []
        
        for sig_data in signals:
            # Only create picks for high-confidence signals
            if sig_data["win_probability"] < 0.5:
                continue
            
            signal = sig_data["signal"]
            
            pick = {
                "algorithm": signal.signal_type,
                "symbol": signal.symbol,
                "category": "crypto",
                "tier": self.ALGO_DEFS.get(signal.signal_type, {}).get("tier", "SCOUT"),
                "entry_price": signal.entry_price,
                "status": "OPEN",
                "reason": signal.reason,
                "regime": "bull",
                "regime_confidence": 0.6,
                "breadth_pct": 60.0,
                "vol_20d": 0.025,
                "rsi_at_entry": signal.metadata.get("rsi", 50),
                "volume_ratio": signal.metadata.get("volume_ratio", 1.0),
                "ml_win_prob": sig_data["win_probability"],
                "features": {
                    "entry": signal.entry_price,
                    "tp": signal.take_profit,
                    "sl": signal.stop_loss,
                    "win_prob": sig_data["win_probability"]
                }
            }
            
            pick_id = self.store.write_pick(pick)
            pick_ids.append(pick_id)
        
        return pick_ids
    
    async def run_full_scan(self) -> Dict:
        """Run complete scan cycle"""
        logger.info(f"=" * 80)
        logger.info(f"KIMI_FEB172026 Live Scanner v{self.VERSION}")
        logger.info(f"Running full scan with {self.ALGO_COUNT} algorithms...")
        logger.info(f"=" * 80)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "version": self.VERSION,
            "signals_generated": 0,
            "high_confidence_signals": 0,
            "picks_created": 0,
            "algorithms_checked": 0
        }
        
        # 1. Scan crypto acceleration signals
        crypto_signals = await self.scan_crypto_signals()
        results["algorithms_checked"] = len(self.ALGO_DEFS)
        
        # 2. Rank signals with ML
        ranked_signals = self.rank_signals(crypto_signals)
        results["signals_generated"] = len(ranked_signals)
        
        # 3. Filter high confidence
        high_confidence = [s for s in ranked_signals if s["win_probability"] >= 0.65]
        results["high_confidence_signals"] = len(high_confidence)
        
        # 4. Save to database
        self.save_signals_to_db(ranked_signals)
        
        # 5. Create picks
        pick_ids = self.create_picks_from_signals(high_confidence)
        results["picks_created"] = len(pick_ids)
        
        # 6. Save results to JSON for web interface
        self._save_scan_results(ranked_signals)
        
        return results
    
    def _save_scan_results(self, signals: List[Dict]):
        """Save scan results to JSON file for web display"""
        output = {
            "timestamp": datetime.now().isoformat(),
            "version": self.VERSION,
            "signals": []
        }
        
        for sig_data in signals:
            signal = sig_data["signal"]
            output["signals"].append({
                "symbol": signal.symbol,
                "signal_type": signal.signal_type,
                "direction": signal.direction,
                "confidence": round(signal.confidence, 4),
                "win_probability": round(sig_data["win_probability"], 4),
                "entry_price": round(signal.entry_price, 6),
                "take_profit": round(signal.take_profit, 6),
                "stop_loss": round(signal.stop_loss, 6),
                "reason": signal.reason,
                "position_size": sig_data["position_size"],
                "metadata": signal.metadata
            })
        
        output_path = self.data_dir / "latest_signals.json"
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"Saved {len(signals)} signals to {output_path}")
    
    def get_latest_signals(self, limit: int = 20) -> List[Dict]:
        """Get latest signals from database"""
        df = self.store.get_signals(limit=limit)
        
        signals = []
        for _, row in df.iterrows():
            metadata = json.loads(row.get('metadata', '{}'))
            signals.append({
                "timestamp": row['timestamp'],
                "symbol": row['symbol'],
                "algorithm": row['algorithm'],
                "direction": row['signal'],
                "entry": row['price'],
                "take_profit": metadata.get('take_profit'),
                "stop_loss": metadata.get('stop_loss'),
                "confidence": metadata.get('confidence'),
                "win_probability": metadata.get('win_probability'),
                "reason": row['reason']
            })
        
        return signals
    
    def get_performance_summary(self) -> Dict:
        """Get overall performance summary"""
        return self.store.get_performance_summary(days=30)
    
    def get_algo_rankings(self) -> List[Dict]:
        """Get algorithm rankings"""
        # Get all unique algorithms from picks
        df = self.store.get_picks(limit=10000)
        
        if df.empty:
            return []
        
        algo_stats = []
        for algo in df['algorithm'].unique():
            stats = self.store.get_algo_stats(algo)
            algo_stats.append(stats)
        
        # Rank using ML
        return self.ml_ranker.get_algo_ranking(algo_stats)


# =============================================================================
# FastAPI Web Interface
# =============================================================================
def create_app():
    """Create FastAPI application"""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import HTMLResponse, JSONResponse
        
        app = FastAPI(
            title="KIMI_FEB172026 Trading System",
            description="Institutional-grade crypto/forex signal generation",
            version="11.0.0"
        )
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        scanner = KIMILiveScanner()
        
        @app.get("/", response_class=HTMLResponse)
        async def root():
            """Serve main dashboard"""
            html_path = Path("KIMI_FEB172026/templates/dashboard.html")
            if html_path.exists():
                return html_path.read_text()
            return "<h1>KIMI_FEB172026 Trading System</h1><p>Dashboard loading...</p>"
        
        @app.get("/api/signals")
        async def get_signals(limit: int = 20):
            """Get latest signals"""
            signals = scanner.get_latest_signals(limit)
            return {"signals": signals, "count": len(signals)}
        
        @app.get("/api/scan")
        async def run_scan():
            """Run live scan"""
            results = await scanner.run_full_scan()
            return results
        
        @app.get("/api/performance")
        async def get_performance():
            """Get performance summary"""
            return scanner.get_performance_summary()
        
        @app.get("/api/rankings")
        async def get_rankings():
            """Get algorithm rankings"""
            rankings = scanner.get_algo_rankings()
            return {"rankings": rankings}
        
        @app.get("/api/signal/{symbol}")
        async def get_signal_for_symbol(symbol: str):
            """Get signal for specific symbol"""
            # Normalize symbol
            symbol = symbol.upper().replace("/", "-").replace("USDT", "-USD")
            
            signals = scanner.get_latest_signals(100)
            matching = [s for s in signals if s['symbol'] == symbol]
            
            if not matching:
                raise HTTPException(status_code=404, detail=f"No signals for {symbol}")
            
            return {"symbol": symbol, "signals": matching}
        
        return app
        
    except ImportError:
        logger.warning("FastAPI not installed. Web interface disabled.")
        return None


# =============================================================================
# CLI Entry Point
# =============================================================================
async def main():
    """Main CLI entry point"""
    print("=" * 80)
    print(f"KIMI_FEB172026 - Live Trading Scanner v{KIMILiveScanner.VERSION}")
    print("Institutional-Grade Crypto/Forex Signal Detection")
    print("=" * 80)
    print()
    
    scanner = KIMILiveScanner()
    
    print("Running initial scan...")
    print("-" * 80)
    
    results = await scanner.run_full_scan()
    
    print(f"\nScan Complete!")
    print(f"  Algorithms Checked: {results['algorithms_checked']}")
    print(f"  Signals Generated: {results['signals_generated']}")
    print(f"  High Confidence (≥65%): {results['high_confidence_signals']}")
    print(f"  Active Picks Created: {results['picks_created']}")
    
    # Display top signals
    print("\n" + "=" * 80)
    print("TOP SIGNALS (Win Probability >= 65%):")
    print("=" * 80)
    
    signals = scanner.get_latest_signals(10)
    for i, sig in enumerate(signals, 1):
        win_prob = sig.get('win_probability', 0)
        if win_prob >= 0.65:
            print(f"\n{i}. 🎯 {sig['symbol']} - {sig['algorithm']}")
            print(f"   Direction: {sig['direction']}")
            print(f"   Win Probability: {win_prob:.1%}")
            print(f"   Entry: ${sig['entry']:,.2f}")
            print(f"   Take Profit: ${sig['take_profit']:,.2f}")
            print(f"   Stop Loss: ${sig['stop_loss']:,.2f}")
            print(f"   Reason: {sig['reason']}")
    
    # Performance summary
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY (30 days):")
    print("=" * 80)
    
    perf = scanner.get_performance_summary()
    for key, value in perf.items():
        print(f"  {key}: {value}")
    
    # Algorithm rankings
    print("\n" + "=" * 80)
    print("ALGORITHM RANKINGS:")
    print("=" * 80)
    
    rankings = scanner.get_algo_rankings()
    for i, r in enumerate(rankings[:5], 1):
        print(f"{i}. {r['algorithm']}")
        print(f"   Expected Win Prob: {r['expected_win_prob']:.1%}")
        print(f"   Current Win Rate: {r['current_win_rate']:.1%}")
        print(f"   Sharpe: {r['sharpe']:.2f}")
    
    print("\n" + "=" * 80)
    print("Scan complete. Data saved to KIMI_FEB172026/data/")
    print("Run 'python -m uvicorn KIMI_FEB172026.live_scanner:create_app --reload'")
    print("to start the web dashboard.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
