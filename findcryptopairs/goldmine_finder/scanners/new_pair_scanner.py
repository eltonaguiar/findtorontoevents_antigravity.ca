#!/usr/bin/env python3
"""
New Pair Scanner - Finds fresh gems before they pump
Monitors DEXs for new listings with 100x potential
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class NewPair:
    symbol: str
    address: str
    chain: str
    launch_time: datetime
    market_cap: float
    liquidity: float
    volume_24h: float
    holder_count: int
    price_change_24h: float
    dex: str
    contract_verified: bool
    
    @property
    def liquidity_locked(self) -> bool:
        """Check if liquidity is locked (safety)"""
        # Would query blockchain in production
        return False  # Default to False until verified
    
    @property
    def gem_score(self) -> int:
        """Calculate gem potential 0-100"""
        score = 0
        
        # Market cap sweet spot (0-30 points)
        if 50000 <= self.market_cap <= 1000000:
            score += 30
        elif 1000000 <= self.market_cap <= 10000000:
            score += 20
        elif self.market_cap < 50000:
            score += 10  # Too small, risky
        
        # Liquidity (0-25 points)
        if self.liquidity >= 200000:
            score += 25
        elif self.liquidity >= 100000:
            score += 20
        elif self.liquidity >= 50000:
            score += 15
        
        # Volume activity (0-25 points)
        vol_to_mcap = self.volume_24h / self.market_cap if self.market_cap > 0 else 0
        if vol_to_mcap > 0.5:  # High volume relative to mcap
            score += 25
        elif vol_to_mcap > 0.2:
            score += 15
        elif vol_to_mcap > 0.1:
            score += 10
        
        # Holder growth (0-20 points)
        if self.holder_count > 1000:
            score += 20
        elif self.holder_count > 500:
            score += 15
        elif self.holder_count > 100:
            score += 10
        
        return score


class NewPairScanner:
    """Scans multiple DEXs for new pairs with 100x potential"""
    
    def __init__(self):
        self.discovered_pairs = []
        self.watched_chains = ['solana', 'base', 'ethereum', 'arbitrum']
        
    def scan_dexscreener(self, chain: str = 'solana', min_liquidity: float = 50000) -> List[NewPair]:
        """
        Scan DexScreener for new pairs
        API: https://api.dexscreener.com/latest/dex/search?q=query
        """
        pairs = []
        
        try:
            # Get trending pairs on chain
            url = f"https://api.dexscreener.com/token-boosts/top/v1"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data:
                    # Filter by chain and liquidity
                    if item.get('chainId') != chain:
                        continue
                    
                    liquidity = item.get('liquidityUsd', 0)
                    if liquidity < min_liquidity:
                        continue
                    
                    pair = NewPair(
                        symbol=item.get('tokenAddress', 'Unknown')[:8],
                        address=item.get('tokenAddress', ''),
                        chain=chain,
                        launch_time=datetime.now(),  # Would parse from data
                        market_cap=item.get('marketCap', 0),
                        liquidity=liquidity,
                        volume_24h=item.get('volume24h', 0),
                        holder_count=item.get('holderCount', 0),
                        price_change_24h=item.get('priceChange24h', 0),
                        dex=item.get('dexId', 'Unknown'),
                        contract_verified=False
                    )
                    
                    pairs.append(pair)
                    
        except Exception as e:
            print(f"Error scanning DexScreener: {e}")
        
        return pairs
    
    def scan_birdeye(self, chain: str = 'solana') -> List[NewPair]:
        """
        Scan Birdeye for Solana new pairs
        Requires API key for full access
        """
        # Birdeye API integration
        # Free tier has limited calls
        pairs = []
        
        try:
            url = f"https://public-api.birdeye.so/public/tokenlist?chain={chain}"
            headers = {
                'X-API-KEY': 'YOUR_API_KEY'  # Free tier available
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                for token in data.get('data', []):
                    # Filter new tokens
                    if token.get('liquidity', 0) < 50000:
                        continue
                    
                    pair = NewPair(
                        symbol=token.get('symbol', 'Unknown'),
                        address=token.get('address', ''),
                        chain=chain,
                        launch_time=datetime.now(),
                        market_cap=token.get('marketCap', 0),
                        liquidity=token.get('liquidity', 0),
                        volume_24h=token.get('v24h', 0),
                        holder_count=token.get('holder', 0),
                        price_change_24h=token.get('priceChange24h', 0),
                        dex='Raydium',  # Most common on Solana
                        contract_verified=token.get('verified', False)
                    )
                    
                    pairs.append(pair)
                    
        except Exception as e:
            print(f"Error scanning Birdeye: {e}")
        
        return pairs
    
    def scan_apex(self) -> List[NewPair]:
        """
        Scan Apex for Base chain opportunities
        Base ecosystem tracker
        """
        pairs = []
        # Apex/Base specific scanning
        return pairs
    
    def detect_volume_anomaly(self, pair: NewPair, baseline_days: int = 7) -> bool:
        """
        Detect if current volume is anomalous vs baseline
        3x+ volume without price move = accumulation
        """
        # Would fetch historical volume data
        # Compare current vs 7-day average
        
        vol_ratio = pair.volume_24h / pair.market_cap if pair.market_cap > 0 else 0
        
        # High volume ratio suggests interest
        return vol_ratio > 0.3  # 30% of mcap in daily volume
    
    def score_potential(self, pair: NewPair) -> Dict:
        """
        Score the 100x potential of a new pair
        """
        score = pair.gem_score
        reasons = []
        risks = []
        
        # Gem score breakdown
        if score >= 80:
            tier = "💎 HIGH POTENTIAL"
        elif score >= 60:
            tier = "🥈 MODERATE"
        elif score >= 40:
            tier = "🥉 WATCH"
        else:
            tier = "❌ PASS"
        
        # Reasons
        if 50000 <= pair.market_cap <= 1000000:
            reasons.append("Market cap in 100x sweet spot")
        
        if pair.liquidity >= 100000:
            reasons.append("Good liquidity for entry/exit")
        
        if pair.volume_24h / pair.market_cap > 0.3:
            reasons.append("Volume anomaly detected (accumulation)")
        
        if pair.holder_count > 500:
            reasons.append("Strong holder growth")
        
        if pair.price_change_24h < 50:
            reasons.append("Not pumped yet (early)")
        
        # Risks
        if pair.market_cap < 50000:
            risks.append("Very low cap - high rug risk")
        
        if pair.liquidity < 50000:
            risks.append("Low liquidity - may not be able to exit")
        
        if pair.price_change_24h > 200:
            risks.append("Already pumped - may be top")
        
        return {
            'score': score,
            'tier': tier,
            'reasons': reasons,
            'risks': risks,
            'recommendation': 'RESEARCH' if score >= 60 else 'PASS'
        }
    
    def find_gems(self, chains: List[str] = None) -> List[Dict]:
        """
        Main scanning function
        Returns scored opportunities
        """
        if chains is None:
            chains = ['solana', 'base']
        
        all_pairs = []
        
        for chain in chains:
            print(f"Scanning {chain}...")
            
            if chain == 'solana':
                pairs = self.scan_birdeye(chain)
            else:
                pairs = self.scan_dexscreener(chain)
            
            # Score and filter
            for pair in pairs:
                analysis = self.score_potential(pair)
                
                if analysis['score'] >= 60:  # Only high potentials
                    all_pairs.append({
                        'pair': pair,
                        'analysis': analysis
                    })
        
        # Sort by score
        all_pairs.sort(key=lambda x: x['analysis']['score'], reverse=True)
        
        return all_pairs
    
    def save_discovery(self, gem: Dict):
        """Log discovered gem for tracking"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"discoveries/gem_{gem['pair'].symbol}_{timestamp}.json"
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'symbol': gem['pair'].symbol,
            'address': gem['pair'].address,
            'chain': gem['pair'].chain,
            'market_cap': gem['pair'].market_cap,
            'liquidity': gem['pair'].liquidity,
            'score': gem['analysis']['score'],
            'tier': gem['analysis']['tier'],
            'reasons': gem['analysis']['reasons'],
            'risks': gem['analysis']['risks']
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"💎 Saved discovery: {filename}")
        except Exception as e:
            print(f"Error saving: {e}")


# Example usage
if __name__ == "__main__":
    scanner = NewPairScanner()
    
    print("🔍 Starting Goldmine Scanner...")
    print("=" * 60)
    
    # Find gems
    gems = scanner.find_gems(chains=['solana'])
    
    print(f"\n💎 Found {len(gems)} high-potential gems:\n")
    
    for i, gem in enumerate(gems[:5], 1):  # Top 5
        pair = gem['pair']
        analysis = gem['analysis']
        
        print(f"{i}. {pair.symbol} ({pair.chain.upper()})")
        print(f"   {analysis['tier']}")
        print(f"   Score: {analysis['score']}/100")
        print(f"   Market Cap: ${pair.market_cap:,.0f}")
        print(f"   Liquidity: ${pair.liquidity:,.0f}")
        print(f"   Volume 24h: ${pair.volume_24h:,.0f}")
        print(f"   Holders: {pair.holder_count}")
        print(f"   Reasons: {', '.join(analysis['reasons'][:3])}")
        
        if analysis['risks']:
            print(f"   ⚠️  Risks: {', '.join(analysis['risks'][:2])}")
        
        print()
        
        # Save discovery
        scanner.save_discovery(gem)
    
    print("=" * 60)
    print("✅ Scan complete. Check discoveries/ folder.")
