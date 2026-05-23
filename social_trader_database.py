#!/usr/bin/env python3
"""
SOCIAL MEDIA ALGO TRADER DATABASE
Collects and verifies algo traders from Reddit, Discord, Twitter
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class TraderProfile:
    """Profile of a social media algo trader"""
    username: str
    platform: str  # Reddit, Discord, Twitter, YouTube
    strategy_type: str
    assets_traded: List[str]
    posting_frequency: str  # Daily, Weekly, Monthly
    evidence_quality: int  # 0-100
    verification_status: str  # Verified, Suspicious, Fake
    claimed_returns: Optional[float] = None
    claimed_win_rate: Optional[float] = None
    broker_screenshots: bool = False
    video_proof: bool = False
    third_party_verified: bool = False
    red_flags: List[str] = None
    community_reputation: str = ""  # Positive, Mixed, Negative
    notes: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)

class SocialMediaTraderDatabase:
    """Database of verified social media traders"""
    
    def __init__(self, db_file: str = "social_traders.json"):
        self.db_file = db_file
        self.traders: List[TraderProfile] = []
        self.load_database()
    
    def load_database(self):
        """Load existing database"""
        try:
            with open(self.db_file, 'r') as f:
                data = json.load(f)
                self.traders = [TraderProfile(**t) for t in data.get('traders', [])]
        except FileNotFoundError:
            self.traders = []
    
    def save_database(self):
        """Save database to file"""
        data = {
            'last_updated': datetime.now().isoformat(),
            'total_traders': len(self.traders),
            'verified_count': len([t for t in self.traders if t.verification_status == 'Verified']),
            'suspicious_count': len([t for t in self.traders if t.verification_status == 'Suspicious']),
            'fake_count': len([t for t in self.traders if t.verification_status == 'Fake']),
            'traders': [t.to_dict() for t in self.traders]
        }
        
        with open(self.db_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_trader(self, trader: TraderProfile):
        """Add a trader to the database"""
        # Check if already exists
        existing = [t for t in self.traders if t.username == trader.username and t.platform == trader.platform]
        
        if existing:
            # Update existing
            idx = self.traders.index(existing[0])
            self.traders[idx] = trader
        else:
            # Add new
            self.traders.append(trader)
        
        self.save_database()
    
    def get_verified_traders(self) -> List[TraderProfile]:
        """Get all verified traders"""
        return [t for t in self.traders if t.verification_status == 'Verified']
    
    def get_by_platform(self, platform: str) -> List[TraderProfile]:
        """Get traders by platform"""
        return [t for t in self.traders if t.platform == platform]
    
    def get_by_strategy(self, strategy_type: str) -> List[TraderProfile]:
        """Get traders by strategy type"""
        return [t for t in self.traders if strategy_type.lower() in t.strategy_type.lower()]
    
    def generate_report(self) -> str:
        """Generate summary report"""
        verified = self.get_verified_traders()
        
        report = []
        report.append("# Social Media Algo Trader Database Report")
        report.append(f"\n**Generated:** {datetime.now().isoformat()}")
        report.append(f"\n## Summary Statistics")
        report.append(f"- **Total Traders:** {len(self.traders)}")
        report.append(f"- **Verified:** {len([t for t in self.traders if t.verification_status == 'Verified'])}")
        report.append(f"- **Suspicious:** {len([t for t in self.traders if t.verification_status == 'Suspicious'])}")
        report.append(f"- **Fake:** {len([t for t in self.traders if t.verification_status == 'Fake'])}")
        
        # By platform
        report.append(f"\n## By Platform")
        platforms = set(t.platform for t in self.traders)
        for platform in platforms:
            count = len(self.get_by_platform(platform))
            verified_count = len([t for t in self.get_by_platform(platform) if t.verification_status == 'Verified'])
            report.append(f"- **{platform}:** {count} traders ({verified_count} verified)")
        
        # Top verified traders
        report.append(f"\n## Top Verified Traders")
        for i, trader in enumerate(verified[:10], 1):
            report.append(f"\n### {i}. {trader.username} ({trader.platform})")
            report.append(f"- **Strategy:** {trader.strategy_type}")
            report.append(f"- **Assets:** {', '.join(trader.assets_traded)}")
            report.append(f"- **Evidence Score:** {trader.evidence_quality}/100")
            if trader.claimed_returns:
                report.append(f"- **Claimed Returns:** {trader.claimed_returns:.1%}")
            if trader.claimed_win_rate:
                report.append(f"- **Claimed Win Rate:** {trader.claimed_win_rate:.1%}")
            report.append(f"- **Proof:** {'✅' if trader.broker_screenshots else '❌'} Screenshots | {'✅' if trader.video_proof else '❌'} Video | {'✅' if trader.third_party_verified else '❌'} 3rd Party")
            if trader.notes:
                report.append(f"- **Notes:** {trader.notes}")
        
        return "\n".join(report)

# Example usage
def main():
    db = SocialMediaTraderDatabase()
    
    # Add example traders (would be populated by agents)
    example_traders = [
        TraderProfile(
            username="u/AlgoTrader_Pro",
            platform="Reddit",
            strategy_type="Mean Reversion",
            assets_traded=["SPY", "QQQ"],
            posting_frequency="Daily",
            evidence_quality=85,
            verification_status="Verified",
            claimed_returns=0.45,
            claimed_win_rate=0.62,
            broker_screenshots=True,
            video_proof=True,
            third_party_verified=True,
            notes="Consistent posting for 18 months, transparent about losses"
        ),
        TraderProfile(
            username="@CryptoScalperXYZ",
            platform="Twitter",
            strategy_type="Momentum",
            assets_traded=["BTC", "ETH", "SOL"],
            posting_frequency="Multiple daily",
            evidence_quality=45,
            verification_status="Suspicious",
            claimed_returns=2.50,
            claimed_win_rate=0.85,
            broker_screenshots=False,
            video_proof=False,
            third_party_verified=False,
            red_flags=["Only posts wins", "Unrealistic returns", "Selling course"],
            notes="Claims 250% monthly returns, no proof provided"
        )
    ]
    
    for trader in example_traders:
        db.add_trader(trader)
    
    # Generate report
    report = db.generate_report()
    print(report)
    
    # Save to file
    with open("SOCIAL_TRADER_REPORT.md", "w") as f:
        f.write(report)
    
    print(f"\n✅ Database saved with {len(db.traders)} traders")

if __name__ == "__main__":
    main()
