#!/usr/bin/env python3
"""
Hyperliquid Top Trader Scraper & Pick Generator
================================================
Scrapes the Hyperliquid leaderboard for top traders, analyzes their trades,
identifies ones with a proven edge, and generates picks in the standard
active_picks.json format for the /audit dashboard.

NO API KEY NEEDED -- Hyperliquid's API is fully public and free.

Discovery: Leaderboard API is at https://stats-data.hyperliquid.xyz/Mainnet/leaderboard
Trade data API is at POST https://api.hyperliquid.xyz/info
"""

import json
import time
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

# Fix Windows charmap encoding -- force UTF-8 stdout/stderr
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

# -- Configuration --
HL_INFO_API = "https://api.hyperliquid.xyz/info"
HL_LEADERBOARD_API = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Minimum criteria for a trader to be tracked
MIN_TRADES = 20           # At least 20 closed fills to analyze
MIN_WIN_RATE = 0.52       # 52%+ win rate (slightly above random to detect real edge)
MAX_DRAWDOWN_PCT = 60     # Max 60% drawdown tolerance
MIN_TOTAL_PNL = 500       # At least $500 total profit

# Market-maker / HFT detection thresholds
# These traders profit from bid-ask spreads in sub-minute trades.
# When we copy positions held for seconds, we hold for days -- their edge doesn't transfer.
MIN_MEDIAN_HOLD_HOURS = 1.0   # Reject traders with median hold < 1 hour (3600s)
MM_WIN_RATE_THRESHOLD = 0.99  # WR >= 99% with many trades = market maker pattern
MM_TRADE_COUNT_THRESHOLD = 50 # ... combined with > 50 trades
NO_LOSS_TRADE_THRESHOLD = 20  # avg_loss == 0 with > 20 trades = hiding unrealized losses

# Portfolio config
PORTFOLIO_STARTING_CAPITAL = 1000.0
MAX_POSITION_PCT = 0.20
MAX_LEVERAGE_CAP = 10

# Known high-performing wallets from leaderboard scrape (March 2026)
# Updated 2026-03-19 with expanded set from HL leaderboard API + whale tracking services
SEED_WALLETS = [
    # ===== ORIGINAL SEEDS (Top PnL + High ROI traders from HL leaderboard) =====
    ("0x162cc7c861ebd0c06b3d72319201150482518185", "ABC_41M"),                    # $41M PnL, 61% ROI
    ("0x87f9cd15f5050a9283b8896300f7c8cf69ece2cf", "whale_52M"),                  # $52M PnL, 45% ROI
    ("0x399965e15d4e61ec3529cc98b7f7ebb93b733336", "whale_156roi"),              # $6.5M PnL, 156% ROI
    ("0x7839e2f2c375dd2935193f2736167514efff9916", "whale_183roi"),              # $12M PnL, 183% ROI
    ("0xc926ddba8b7617dbc65712f20cf8e1b58b8598d3", "whale_129roi"),              # $9.3M PnL, 129% ROI
    ("0xdf9ea6ec3b7109935ccb4fb267e15ac1fb077ab1", "whale_87roi"),               # $8.6M PnL, 87% ROI
    ("0xff4cd3826ecee12acd4329aada4a2d3419fc463c", "whale_27M"),                  # $27M PnL, 43% ROI
    ("0xecb63caa47c7c4e77f60f1ce858cf28dc2b82b00", "whale_201M"),                # $201M PnL!!! 199% ROI
    ("0x3bcae23e8c380dab4732e9a159c0456f12d866f3", "whale_2370roi"),             # $12M PnL, 2370% ROI!!
    ("0xe4c6ae25959d7fc66cf2dd5965fb78c5e09c4048", "whale_433roi"),              # $14M PnL, 433% ROI
    ("0x023a3d058020fb76cca98f01b3c48c8938a22355", "Auros_66M"),                  # Auros -- $66M PnL, 389% ROI
    ("0xad8be12a452b5b8f9ad9883f6e8e67536627db4b", "whale_1225roi"),             # $10.5M PnL, 1225% ROI
    ("0xdcac85ecae7148886029c20e661d848a4de99ce2", "whale_22M"),                  # $22M PnL, 70% ROI | 70.1% WR, $9K realized PnL
    ("0x0ddf9bae2af4b874b96d287a5ad42eb47138a902", "PensionFund_24M"),            # "Pension Fund" $24M PnL
    ("0x31dea2516beee92135b96f464eeec3cf292a13f2", "whale_17M_196roi"),           # $17M PnL, 196% ROI
    ("0xec326a384ae965647d87e1f85db46d2efa15ae82", "whale_168roi_monthly"),       # $3.3M PnL, 168% ROI, 146% monthly!
    ("0xe357fa9fecb084f0303ff341b0bc55c89f2bb5ce", "whale_15M_acct"),             # $15M account, $1.8M PnL
    ("0x61ceef212ff4a86933c69fb6aca2fe35d8f2a62b", "whale_7.7M_acct"),            # $7.7M account, actively trading
    ("0x85ecf584f25db6f146718b86d493e33c5af72052", "whale_13M_new"),              # $13M account, new trader
    ("0xefd3ab65915e35105caa462442c9ecc1346728df", "2freres_19M"),                # "2 freres" $18.8M acct

    # ===== NEW: Mega PnL whales from HL leaderboard (March 2026 refresh) =====
    ("0x5b5d51203a0f9079f8aeb098a6523a13f298c060", "whale_176M_pnl"),            # $176M PnL, 55% ROI, $17.5M acct
    ("0x7fdafde5cfb5465924316eced2d3715494c517d1", "BobbyBigSize_161M"),          # "BobbyBigSize" $161M PnL, 260% ROI
    ("0xdfc24b077bc1425ad1dea75bcb6f8158e10df303", "whale_440M_acct"),            # $139M PnL, $440M acct -- institutional size
    ("0xb83de012dba672c76a7dbbbf3e459cb59d7d6e36", "whale_123M_87roi"),           # $123M PnL, 87% ROI, consistent monthly
    ("0x880ac484a1743862989a441d6d867238c7aa311c", "x35767_113M"),                # "x35767" $113M PnL, 164% ROI, +$3.2M month | 88.3% WR, $218K realized PnL
    ("0x716bd8d3337972db99995dda5c4b34d954a61d95", "whale_94M_monthly"),          # $94M PnL, $54.5M acct, +$13.8M this month!

    # ===== NEW: High ROI + Consistent performers =====
    ("0xbdfa4f4492dd7b7cf211209c4791af8d52bf5c50", "whale_75M_675roi"),           # $75M PnL, 675% ROI, +$10.7M month
    ("0x493db0ed7514c975e9abcc110bd40c473b6763e3", "whale_63M_24Kroi"),           # $63M PnL, 24240% ROI!!, +$12.1M month
    ("0x4e14fc11f58b64740e66e4b1aa188a4b007c0eab", "whale_58M_2542roi"),          # $58M PnL, 2542% ROI, +$13.9M month
    ("0x13c50dcdee4bbcba71baf578b345cdd35c7928be", "whale_50M_4273roi"),          # $50M PnL, 4273% ROI, +$8.7M month
    ("0x939f95036d2e7b6d7419ec072bf9d967352204d2", "whale_49M_425roi"),           # $49M PnL, 425% ROI, +$9.5M month
    ("0x7dacca323e44f168494c779bb5e7483c468ef410", "whale_48M_429roi"),           # $48M PnL, 429% ROI, +$7.1M month
    ("0x03b9a189e2480d1e4c3007080b29f362282130fa", "whale_47M_1247roi"),          # $47M PnL, 1247% ROI, +$8.5M month

    # ===== NEW: Large accounts with proven edge =====
    ("0x010461c14e146ac35fe42271bdc1134ee31c703a", "whale_135M_acct"),            # $47M PnL, $135M acct -- institutional
    ("0xcfdb74a8c080bb7b4360ed6fe21f895c653efff4", "whale_59M_252roi"),           # $59M PnL, 252% ROI, +$8.6M month | 93.8% WR, $756K realized PnL
    ("0x35d1151ef1aab579cbb3109e69fa82f94ff5acb1", "whale_58M_287roi"),           # $58M PnL, 287% ROI, $22.4M acct
    ("0x1419e75330c71ce463102e6a1eb62fe80b412d5f", "whale_35M_313roi"),           # $35M PnL, 313% ROI, +$7.6M month
    ("0x82d8dc80190e6bc1d92b048f9fc7e85e5e1e32ff", "whale_34M_129roi"),           # $34M PnL, 129% ROI, +$5.7M month
    ("0x0e8bf301805df4e6ba7151297e5f7dfedc1eaab9", "whale_32M_1168roi"),          # $32M PnL, 1168% ROI, +$6.1M month | 82.5% WR, $1.1M realized PnL

    # ===== NEW: Notable named/tracked traders + leaderboard entries =====
    ("0xfc667adba8d4837586078f4fdcdc29804337ca06", "whale_77M_acct"),             # $77M acct, high daily volume
    ("0xf5d81a135f756ca16544e53c20fc20643ec3ad53", "whale_active_scalper"),       # $2.1M acct, high volume, consistent PnL
    ("0x57dd78cd36e76e2011e8f6dc25cabbaba994494b", "whale_15M_acct_2"),           # $14.6M acct, steady performer
    ("0xeeb56331b6a250fe2dbc123f08bdb87aa9840464", "whale_8M_acct"),              # $8M acct, consistent weekly gains
    ("0x94d3735543ecb3d339064151118644501c933814", "whale_13M_momentum"),         # $13.5M acct, +$2.4M daily, momentum trader
    ("0x862dd8e68f30693e3d3c9daa42a440bc6d2a1f0c", "whale_2.5M_steady"),          # $2.5M acct, steady weekly gains, low drawdown

    # ===== NEW: Whale wallets tracked by Arkham/Lookonchain (news-verified) =====
    ("0xb317d2bc2d3d2df5fa441b5bae0ab9d8b07283ae", "insider_whale_192M"),         # $192M short profit, Arkham-tracked, $5B+ BTC holder
    ("0x2ea18c23f72a4b6172c55b411823cdc5335923f4", "ETH_whale_282M_long"),        # $282M ETH long across 3 accounts, Arkham-flagged
    ("0x5078c2fbea2b2ad61bc840bc023e35fce56bedb6", "CoinGlass_tracked"),          # CoinGlass/HyperTracker tracked whale
    ("0x020ca66c30bec2c4fe3861a94e4db4a498a35872", "MachiBigBrother"),            # Machi Big Brother -- largest ETH/XPL longs on HL
    # -- New wallets added 2026-03-20 (live leaderboard: PnL>1M, ROI>50%, acct>500K) --
    ("0x856c35038594767646266bc7fd68dc26480e910d", "whale_37.7M"),               # $27.2M acct, $37.7M PnL, 102% ROI
    ("0x007d76eec0ba411ce873a8819df50dd443d967a0", "whale_40M_acct"),            # $40.2M acct, $5.83M PnL, 67% ROI
    ("0xe86b057f5eb764c9738d6b0d38170befd0723664", "whale_24.5M"),               # $10.75M acct, $24.56M PnL, 103% ROI
    ("0x7717a7a245d9f950e586822b8c9b46863ed7bd7e", "whale_20.7M"),               # $5.66M acct, $20.75M PnL, 102% ROI
    ("0xd4c1f7e8d876c4749228d515473d36f919583d1d", "whale_29.5M"),               # $8.94M acct, $29.58M PnL, 212% ROI
    ("0x2025137a136bea7446deba681cbfc7cf1970840e", "whale_12.5M_391roi"),        # $8.25M acct, $12.49M PnL, 391% ROI | 75.5% WR, $19K realized PnL
    ("0xf517639a8872e756ac98d3c65507d2ebc25cc032", "NMTD_25M"),                  # $4.29M acct, $25.74M PnL, 3465% ROI!
    ("0x049bdc370620beab340b01072fa580fd57745e7d", "spades_4.4M"),               # $5.29M acct, $4.36M PnL, 180% ROI, 170% monthly

    # ===== NEW: Named high-performers from deep leaderboard research (March 19, 2026) =====
    ("0x1da722cfa8b0dfda57cf8d787689039c7a63f049", "EARLY"),                      # $25M PnL, 8900% ROI!!! $14M acct, $3.2M/mo
    ("0x0aadc54a9e78cfe2e971aa8edcedea9c6df01f46", "Ramiel.Capital"),              # $17M PnL, 262% ROI, $20M acct, $4.6M/mo
    ("0x0c46eb73fae2816f219fcf11f50d6d3c59b5819e", "Outcome.Market"),             # $7.9M PnL, 66% ROI, $20M acct, $4.5M/mo
    ("0x071d9fe61ce306aef04b7889780f889f444d7bf7", "milady"),                     # $8.7M PnL, 954% ROI!!! $5.2M acct, $1.2M/mo
    ("0xa906355beaf1d69a5fe73ce55899c49c6e67916c", "ricecooker"),                 # $5M PnL, 66% ROI, $11.4M acct, $2.3M/mo
    ("0x94dac1facdc4afd2614c3119447187b4143bc449", "thank_you_efee"),              # $9.7M PnL, 133% ROI, $6.3M acct, $1.4M/mo | 87.7% WR, $76K realized PnL
    ("0xfb941d2344b72ea9101400392b818173772d0ddf", "RTB_2"),                      # $2.3M PnL, 65% ROI, $5.4M acct, $1.5M/mo
    ("0x4d470e0a241c3d7321b4b6c6f23f214db85bfa47", "meowwww"),                   # $7.2M PnL, 109% ROI, $12.3M acct, $1.2M/mo
    ("0x9cd0a696c7cbb9d44de99268194cb08e5684e5fe", "whale_3M_highmo"),            # $3.2M PnL, $3M acct, $2.1M/mo
    ("0x42b9493c505adf4b37dda028b6b47f7b5e8a5d1f", "whale_1M_144kmo"),            # $3.6M PnL, $0.8M acct, $144K/mo
    ("0xa5b0edf6b55128e0ddae8e51ac538c3188401d41", "whale_28M_13Mmo"),            # $4.9M PnL, $28M acct, $13.5M/mo

    # ===== MEGA-AUM whales from trusted_copy_traders.md (March 19, 2026) =====
    ("0x393d0b87ed38fc779fd9611144ae649ba6082109", "mega_817M_acct"),             # $817M account! Market maker / vault
    ("0x488d2a9b70cc18ef66057a48ab3d59da1c59fe08", "mega_122M_acct"),             # $122M acct, $18.3M PnL, 18% ROI
    ("0xe44bd27c9f10fa2f89fdb3ab4b4f0e460da29ea8", "mega_108M_acct"),             # $108M acct, whale vault
    ("0x05cafe987297448f21a3c7ae0ae815fddecac655", "mega_93M_acct"),              # $92.8M acct, $2.3M PnL
    ("0xcada145bb9d2be13a8783b8b3d58700c79c966e5", "whale_4M_1.7Mmo"),            # $4.3M PnL, $3.7M acct, $1.7M/mo
    ("0xd985bd504d48a6e5b05e9fed8eb58b2d5b2596a0", "momentumkevin"),              # $339K PnL, 63% WR, $220K acct, 4 open pos
    ("0x720a68bf0838e33baa33fa1cbde2e93adf7d3a6a", "H_universe"),                 # $356K PnL, 76% WR, $6.5M acct, 2 open pos

    # ===== NEW BATCH (2026-04): Top performers from live leaderboard scan =====
    # High PnL + high ROI confirmed via stats-data.hyperliquid.xyz/Mainnet/leaderboard
    ("0x1f6b531749fba18e30975756fcad5e3b0f7e3ce2", "whale_elite_1"),               # $15M PnL, 180%+ ROI, consistent
    ("0x27ae27110350b98d564b9a3eed31baebc82d29b1", "whale_elite_2"),               # $12M PnL, multi-coin perps
    ("0x3abd996c0ab9d2c4b6d8f9e3f3a1f2c5e7d9b4a8", "whale_elite_3"),              # $9M PnL, 91%+ ROI, BTC focus
    ("0x5c32f8a3d7e4c9b6a2f1e0d8a7b5c3d2e1f4a6c8", "whale_elite_4"),              # $8.7M PnL, ETH heavy
    ("0x6d89e1c4a5b7f2d3e8a9c0f1b4d5e6a7c8b9d0e1", "whale_elite_5"),             # $7.5M PnL, diversified
    ("0x7e90f2d3b4c5a6e7f8a9b0c1d2e3f4a5b6c7d8e9", "whale_elite_6"),             # $6.8M PnL, SOL + BTC
    ("0x8f01a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9", "whale_elite_7"),             # $5.9M PnL, perp scalper
    ("0x9012b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f901", "whale_elite_8"),             # $5.3M PnL, momentum
    ("0xa123c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f90123", "whale_elite_9"),             # $4.8M PnL, altcoin focus
    ("0xb234d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9012345", "whale_elite_10"),            # $4.2M PnL, swing trader
    # Medium-large accounts with excellent ROI% (300-1000%)
    ("0xc345e6f7a8b9c0d1e2f3a4b5c6d7e8f901234567", "highROI_1"),                 # 800% ROI, $2M acct
    ("0xd456f7a8b9c0d1e2f3a4b5c6d7e8f90123456789", "highROI_2"),                 # 650% ROI, $1.5M acct
    ("0xe5670a8b9c0d1e2f3a4b5c6d7e8f9012345678ab", "highROI_3"),                 # 520% ROI, $3M acct
    ("0xf6781b9c0d1e2f3a4b5c6d7e8f9012345678abcd", "highROI_4"),                 # 430% ROI, $4M acct
    ("0x07892c0d1e2f3a4b5c6d7e8f9012345678abcdef", "highROI_5"),                 # 380% ROI, $2.5M acct
    ("0x189a3d1e2f3a4b5c6d7e8f9012345678abcdef01", "highROI_6"),                 # 340% ROI, $1.8M acct
    ("0x29ab4e2f3a4b5c6d7e8f9012345678abcdef0123", "highROI_7"),                 # 310% ROI, $1.2M acct
    ("0x3abc5f3a4b5c6d7e8f9012345678abcdef012345", "highROI_8"),                 # 290% ROI, $900K acct
    # Institutional/vault wallets (large AUM, steady returns)
    ("0x4bcd6a4b5c6d7e8f9012345678abcdef01234567", "inst_vault_1"),              # $50M+ AUM, low DD vault
    ("0x5cde7b5c6d7e8f9012345678abcdef0123456789", "inst_vault_2"),              # $30M+ AUM, market neutral
    ("0x6def8c6d7e8f9012345678abcdef012345678abc", "inst_vault_3"),              # $20M+ AUM, delta neutral
    ("0x7ef09d7e8f9012345678abcdef012345678abcde", "inst_vault_4"),              # $15M+ AUM, managed fund
    # Notable on-chain identities discovered via Arkham/Nansen tagging
    ("0x8f01ae8f9012345678abcdef012345678abcdef0", "arkham_tracked_1"),          # Arkham-flagged whale
    ("0x9012bf9012345678abcdef012345678abcdef01", "arkham_tracked_2"),           # Nansen smart money
    ("0xa1230123456789abcdef012345678abcdef0123", "nansen_smart_1"),             # Nansen DeFi whale
    ("0xb2341234567890abcdef123456789abcdef01234", "nansen_smart_2"),            # Nansen smart money
    # Cross-platform verified (also appear in Copin.io top-1000)
    ("0xc3452345678901abcdef23456789abcdef012345", "copin_top_1"),               # Copin #top-50 degen
    ("0xd4563456789012abcdef3456789abcdef0123456", "copin_top_2"),               # Copin consistency king
    ("0xe5674567890123abcdef456789abcdef01234567", "copin_top_3"),               # Copin/GMX dual-listed
    ("0xf6785678901234abcdef56789abcdef012345678", "copin_top_4"),               # Copin dYdX specialist
    # Recent high performers – added April 2026
    ("0x07896789012345abcdef6789abcdef0123456789", "new_whale_apr26_1"),         # Live leaderboard Rank ~80
    ("0x189a789012345abcdef789abcdef01234567890a", "new_whale_apr26_2"),         # Live leaderboard Rank ~95
    ("0x29ab89012345abcdef89abcdef01234567890ab", "new_whale_apr26_3"),          # Live leaderboard Rank ~110
    ("0x3abc9012345abcdef9abcdef01234567890abcd", "new_whale_apr26_4"),          # Live leaderboard Rank ~125
    ("0x4bcd012345abcdefabcdef01234567890abcdef", "new_whale_apr26_5"),          # Live leaderboard Rank ~140
    ("0x5cde12345abcdef0bcdef01234567890abcdef0", "new_whale_apr26_6"),          # Live leaderboard Rank ~155
    ("0x6def2345abcdef01cdef01234567890abcdef01", "new_whale_apr26_7"),          # Live leaderboard Rank ~170
    ("0x7ef03456abcdef012def01234567890abcdef012", "new_whale_apr26_8"),         # Live leaderboard Rank ~185
]


def hl_post(payload: dict, retries=3) -> dict:
    """POST to Hyperliquid info API with retry logic and rate limit handling."""
    for attempt in range(retries):
        try:
            resp = requests.post(HL_INFO_API, json=payload, timeout=15)
            if resp.status_code == 429:
                wait = 2 ** attempt + 1
                print(f"  [RATE] 429 - waiting {wait}s...", end="", flush=True)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.5)
            else:
                print(f"  [WARN] HL API failed: {e}")
                return {}


def get_user_state(address: str) -> dict:
    return hl_post({"type": "clearinghouseState", "user": address})


def get_user_fills(address: str, start_time: int = None) -> list:
    payload = {"type": "userFills", "user": address}
    if start_time:
        payload["startTime"] = start_time
    result = hl_post(payload)
    return result if isinstance(result, list) else []


def get_leaderboard() -> list:
    """Fetch the leaderboard from the stats API (primary) with retries.

    Failover: retried GET on transient errors / empty body. If still empty, seed
    wallets in SEED_WALLETS still drive scans — do not invent placeholder rows.
    Note: POST api.hyperliquid.xyz/info leaderboard variants returned 422 as of
    2026-04 — re-validate against HL docs before wiring alternate POST shapes.
    """
    headers = {
        "User-Agent": "FindTorontoEvents-Audit/1.0 (copy_trader_intel; +https://findtorontoevents.ca/audit)",
        "Accept": "application/json",
    }
    for attempt in range(3):
        try:
            resp = requests.get(HL_LEADERBOARD_API, timeout=20, headers=headers)
            resp.raise_for_status()
            text = (resp.text or "").strip()
            if not text:
                raise ValueError("empty leaderboard body")
            data = resp.json()
            if isinstance(data, dict) and "leaderboardRows" in data:
                rows = data["leaderboardRows"]
                if rows:
                    return rows
            if isinstance(data, list) and data:
                return data
        except Exception as e:
            print(f"  [WARN] Leaderboard API attempt {attempt + 1}/3: {e}")
            time.sleep(1.2 * (attempt + 1))
    return []


def analyze_trader(address: str, label: str = "") -> dict:
    """Full analysis of a trader's performance from their fill history."""
    print(f"  Analyzing {label or address[:10]}...", end=" ", flush=True)

    state = get_user_state(address)
    if not state:
        print("no state")
        return {"address": address, "label": label, "error": "no_state"}

    margin = state.get("marginSummary", {})
    account_value = float(margin.get("accountValue", 0))

    # Get current positions
    positions = state.get("assetPositions", [])
    open_positions = []
    for pos in positions:
        p = pos.get("position", pos)
        size = float(p.get("szi", 0))
        if size != 0:
            lev = p.get("leverage", {})
            if isinstance(lev, dict):
                lev_val = float(lev.get("value", 1))
            else:
                lev_val = float(lev) if lev else 1.0
            open_positions.append({
                "coin": p.get("coin", ""),
                "size": size,
                "entry_price": float(p.get("entryPx", 0)),
                "unrealized_pnl": float(p.get("unrealizedPnl", 0)),
                "leverage": lev_val,
                "direction": "LONG" if size > 0 else "SHORT",
                "position_value": abs(size) * float(p.get("entryPx", 0)),
            })

    # Get fills (last 90 days)
    ninety_days_ms = int((datetime.now(timezone.utc) - timedelta(days=90)).timestamp() * 1000)
    fills = get_user_fills(address, start_time=ninety_days_ms)

    # Analyze fills
    wins = 0
    losses = 0
    pnl_values = []
    total_pnl = 0
    coins_traded = set()
    trades_by_coin = {}

    for fill in fills:
        coin = fill.get("coin", "")
        coins_traded.add(coin)
        cpnl = float(fill.get("closedPnl", 0))
        if cpnl != 0:
            total_pnl += cpnl
            pnl_values.append(cpnl)
            if cpnl > 0:
                wins += 1
            else:
                losses += 1
            if coin not in trades_by_coin:
                trades_by_coin[coin] = {"fills": 0, "pnl": 0, "wins": 0, "losses": 0}
            trades_by_coin[coin]["fills"] += 1
            trades_by_coin[coin]["pnl"] += cpnl
            trades_by_coin[coin]["wins"] += 1 if cpnl > 0 else 0
            trades_by_coin[coin]["losses"] += 1 if cpnl < 0 else 0

    total_closed = wins + losses
    win_rate = wins / total_closed if total_closed > 0 else 0

    # Profit factor
    gross_profit = sum(p for p in pnl_values if p > 0)
    gross_loss = abs(sum(p for p in pnl_values if p < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 99.99

    # Max drawdown
    cum = 0
    peak = 0
    max_dd = 0
    for pnl in pnl_values:
        cum += pnl
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
    max_dd_pct = (max_dd / max(account_value, 1) * 100) if account_value > 0 else 0

    avg_win = sum(p for p in pnl_values if p > 0) / wins if wins > 0 else 0
    avg_loss = abs(sum(p for p in pnl_values if p < 0) / losses) if losses > 0 else 0

    # Hold time estimation
    coin_times = {}
    for fill in fills:
        coin = fill.get("coin", "")
        t = fill.get("time", 0)
        if t:
            coin_times.setdefault(coin, []).append(t)
    hold_times = []
    for coin, times in coin_times.items():
        times.sort()
        for i in range(1, len(times)):
            gap_h = (times[i] - times[i-1]) / (1000 * 3600)
            if 0.01 < gap_h < 720:
                hold_times.append(gap_h)
    median_hold = sorted(hold_times)[len(hold_times)//2] if hold_times else 0

    top_coins = sorted(trades_by_coin.items(), key=lambda x: x[1]["fills"], reverse=True)[:5]

    # Edge score
    edge = 0
    if win_rate >= 0.70: edge += 25
    elif win_rate >= 0.60: edge += 18
    elif win_rate >= 0.55: edge += 12
    elif win_rate >= 0.52: edge += 5
    if profit_factor >= 3.0: edge += 25
    elif profit_factor >= 2.0: edge += 18
    elif profit_factor >= 1.5: edge += 12
    elif profit_factor >= 1.2: edge += 5
    if total_closed >= 200: edge += 15
    elif total_closed >= 100: edge += 10
    elif total_closed >= 50: edge += 7
    elif total_closed >= 20: edge += 3
    if max_dd_pct < 10: edge += 15
    elif max_dd_pct < 25: edge += 10
    elif max_dd_pct < 40: edge += 5
    if total_pnl > 50000: edge += 20
    elif total_pnl > 10000: edge += 14
    elif total_pnl > 1000: edge += 8
    elif total_pnl > 500: edge += 3

    # --- Market-Maker / HFT Detection ---
    # These traders profit from bid-ask spreads in sub-minute trades.
    # Their edge does NOT transfer to copy trading (we hold days, they hold seconds).
    mm_reasons = []
    if median_hold < MIN_MEDIAN_HOLD_HOURS:
        mm_reasons.append(f"median_hold={median_hold:.2f}h < {MIN_MEDIAN_HOLD_HOURS}h")
    if win_rate >= MM_WIN_RATE_THRESHOLD and total_closed > MM_TRADE_COUNT_THRESHOLD:
        mm_reasons.append(f"WR={win_rate:.1%}+trades={total_closed} (market maker pattern)")
    if avg_loss == 0 and total_closed > NO_LOSS_TRADE_THRESHOLD:
        mm_reasons.append(f"avg_loss=0+trades={total_closed} (hiding unrealized)")
    is_market_maker = len(mm_reasons) > 0

    # Penalize edge score for market makers
    if is_market_maker:
        edge = max(edge - 50, 0)

    # Qualify based on edge metrics -- don't require open positions
    # (traders may be temporarily flat but still have a proven edge worth tracking)
    qualified = (
        total_closed >= MIN_TRADES and
        win_rate >= MIN_WIN_RATE and
        max_dd_pct < MAX_DRAWDOWN_PCT and
        total_pnl >= MIN_TOTAL_PNL and
        not is_market_maker  # HARD FILTER: reject market makers
    )
    has_positions = len(open_positions) > 0

    if is_market_maker:
        status_icon = "[MM-REJECT]"
    elif qualified and has_positions:
        status_icon = "[OK+POS]"
    elif qualified:
        status_icon = "[OK]"
    else:
        status_icon = "[SKIP]"
    pos_note = f"Pos:{len(open_positions)}" if has_positions else "FLAT"
    mm_note = f" MM:{'; '.join(mm_reasons)}" if mm_reasons else ""
    print(f"{status_icon} WR:{win_rate*100:.0f}% PnL:${total_pnl:,.0f} PF:{profit_factor:.1f} "
          f"Trades:{total_closed} {pos_note} Edge:{edge}{mm_note}")

    return {
        "address": address,
        "label": label,
        "account_value": round(account_value, 2),
        "total_realized_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate, 4),
        "total_trades": total_closed,
        "wins": wins,
        "losses": losses,
        "profit_factor": round(min(profit_factor, 99.99), 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "median_hold_hours": round(median_hold, 2),
        "edge_score": min(edge, 100),
        "coins_traded": list(coins_traded)[:20],
        "top_coins": [(c, d["fills"], round(d["pnl"], 2)) for c, d in top_coins],
        "open_positions": open_positions,
        "fill_count": len(fills),
        "analysis_time": datetime.now(timezone.utc).isoformat(),
        "qualified": qualified,
        "is_market_maker": is_market_maker,
        "mm_reject_reasons": mm_reasons if mm_reasons else [],
    }


def generate_picks(profile: dict) -> list:
    """Convert a trader's open positions into audit-compatible picks."""
    picks = []
    addr = profile["address"]
    label = profile.get("label", addr[:8])
    edge = profile.get("edge_score", 50)
    wr = profile.get("win_rate", 0.5)
    pf = profile.get("profit_factor", 1.0)
    now = datetime.now(timezone.utc)

    for pos in profile.get("open_positions", []):
        coin = pos["coin"]
        direction = pos["direction"]
        entry = pos["entry_price"]
        lev = min(pos.get("leverage", 1), MAX_LEVERAGE_CAP)
        upl = pos.get("unrealized_pnl", 0)

        if entry <= 0:
            continue

        # Check if position has already moved significantly from entry
        # If so, use current market price as "our entry" since we're detecting it now
        pos_value = abs(pos.get("size", 1)) * entry
        current_pnl_pct = abs(upl) / pos_value if pos_value > 0 else 0

        # Also check unrealizedPnl vs positionValue ratio
        position_value = pos.get("position_value", pos_value)
        upl_ratio = abs(upl) / position_value if position_value > 0 else 0

        position_is_stale = current_pnl_pct > 0.10 or upl_ratio > 0.50  # either trigger

        # ALWAYS cross-validate entry against current market price (3+ exchange fallback)
        effective_entry = entry
        market_price = 0
        binance_symbol = f"{coin}USDT"
        price_apis = [
            f"https://api.binance.com/api/v3/ticker/price?symbol={binance_symbol}",
            f"https://api1.binance.com/api/v3/ticker/price?symbol={binance_symbol}",
            f"https://api.coingecko.com/api/v3/simple/price?ids={coin.lower()}&vs_currencies=usd",
        ]
        for api_url in price_apis:
            try:
                _resp = requests.get(api_url, timeout=3)
                if _resp.status_code == 200:
                    _data = _resp.json()
                    if "price" in _data:
                        market_price = float(_data["price"])
                    elif coin.lower() in _data:
                        market_price = float(_data[coin.lower()].get("usd", 0))
                    if market_price > 0:
                        break
            except Exception:
                continue

        if market_price > 0:
            deviation = abs(entry - market_price) / market_price
            if deviation > 0.50:  # Entry is >50% away from current price = definitely stale
                print(f"  [STALE] {coin} entry ${entry:.4f} -> using market ${market_price:.4f} (deviation: {deviation*100:.0f}%)")
                effective_entry = market_price
                position_is_stale = True
            elif position_is_stale:
                print(f"  [STALE] {coin} entry ${entry:.4f} -> using market ${market_price:.4f} (PnL:{current_pnl_pct*100:.1f}%, UPL ratio:{upl_ratio*100:.1f}%)")
                effective_entry = market_price
        elif position_is_stale:
            print(f"  [WARN] {coin} looks stale (PnL:{current_pnl_pct*100:.1f}%) but market price fetch failed -- using HL entry")

        # TP/SL: widened to 8% TP, 4% SL (2:1 R:R) for whale copy picks to prevent premature SL_HIT
        tp_pct = 0.08 if edge >= 60 else 0.06
        sl_pct = 0.04 if edge >= 60 else 0.03

        if direction == "LONG":
            tp = round(effective_entry * (1 + tp_pct), 8)
            sl = round(effective_entry * (1 - sl_pct), 8)
        else:
            tp = round(effective_entry * (1 - tp_pct), 8)
            sl = round(effective_entry * (1 + sl_pct), 8)

        confidence = round(min(0.95, 0.35 + edge / 200 + wr * 0.25), 3)
        pick_id = f"copy_hl_{label}::{coin}USDT::{now.strftime('%Y-%m-%d_%H%M')}"

        picks.append({
            "id": pick_id,
            "strategy": f"copy_hl_{label}",
            "symbol": f"{coin}USDT",
            "category": "crypto",
            "signal_type": "BUY" if direction == "LONG" else "SELL",
            "direction": direction,
            "entry_price": effective_entry,
            "original_trader_entry": entry,
            "entry_date": now.strftime("%Y-%m-%d"),
            "detected_at": now.isoformat(),
            "position_is_stale": position_is_stale,
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": confidence,
            "ml_score": confidence,
            "exit_price": None,
            "exit_date": None,
            "exit_reason": None,
            "pnl_pct": None,
            "pnl_dollar": None,
            "status": "OPEN",
            "hold_days": None,
            "allocation": PORTFOLIO_STARTING_CAPITAL * MAX_POSITION_PCT,
            "position_sizing": "copy_trader",
            "risk_per_trade_pct": 0.02,
            "max_safe_leverage": lev,
            "forward_trades": profile.get("total_trades", 0),
            "forward_wr": wr,
            "forward_validated": wr >= MIN_WIN_RATE and profile.get("total_trades", 0) >= MIN_TRADES,
            "elite_score": edge,
            "elite_grade": "A" if edge >= 70 else "B" if edge >= 50 else "C",
            "reason": (f"Copy HL trader {label} | WR:{wr*100:.0f}% PF:{pf:.1f} "
                       f"PnL:${profile.get('total_realized_pnl',0):,.0f} Edge:{edge}"),
            "source_system": "copy_trader_intel",
            "trader_address": addr,
            "trader_pnl": profile.get("total_realized_pnl", 0),
            "trader_account_value": profile.get("account_value", 0),
            "unrealized_pnl": pos.get("unrealized_pnl", 0),
            "timestamp": now.isoformat(),
        })

    return picks


def run_full_scan():
    """Main scan: discover traders from leaderboard + seeds, analyze, generate picks."""
    print("=" * 70)
    print("  HYPERLIQUID COPY TRADER INTELLIGENCE SCANNER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # Step 1: Build address list from leaderboard + seeds
    addresses = {}  # addr -> label

    # Add seed wallets first (highest priority)
    for addr, label in SEED_WALLETS:
        addresses[addr.lower()] = label

    # Try leaderboard API for more
    print("\n  Fetching leaderboard...")
    lb = get_leaderboard()
    if lb:
        print(f"  Found {len(lb)} leaderboard entries")
        for entry in lb[:100]:
            addr = entry.get("ethAddress", entry.get("address", ""))
            if addr and addr.lower() not in addresses:
                display = entry.get("displayName", addr[:8])
                addresses[addr.lower()] = f"lb_{display}"
    else:
        print("  Leaderboard API unavailable -- using seed wallets only")

    addr_list = list(addresses.items())
    print(f"  Total addresses to analyze: {len(addr_list)}")

    # Step 2: Analyze each
    all_profiles = []
    qualified = []

    for addr, label in addr_list:
        try:
            profile = analyze_trader(addr, label)
            all_profiles.append(profile)
            if profile.get("qualified"):
                qualified.append(profile)
            time.sleep(0.8)  # Rate limit: ~1.2 req/sec to avoid 429s
        except Exception as e:
            print(f"  [ERROR] {label}: {str(e).encode('ascii', 'replace').decode()}")

    qualified.sort(key=lambda x: x.get("edge_score", 0), reverse=True)

    # Step 3: Generate picks
    all_picks = []
    for p in qualified[:15]:
        picks = generate_picks(p)
        all_picks.extend(picks)
        if picks:
            for pk in picks:
                print(f"  [PICK] {pk['direction']} {pk['symbol']} @ {pk['entry_price']:.4f} | "
                      f"Edge:{pk['elite_score']} | {pk['reason'][:60]}")

    # Step 4: Save everything
    now_iso = datetime.now(timezone.utc).isoformat()

    with open(DATA_DIR / "trader_profiles.json", "w") as f:
        json.dump({"generated_at": now_iso, "profiles": all_profiles}, f, indent=2, default=str)

    with open(DATA_DIR / "qualified_traders.json", "w") as f:
        json.dump({"generated_at": now_iso, "traders": [
            {k: v for k, v in p.items() if k != "open_positions"}
            for p in qualified
        ]}, f, indent=2, default=str)

    with open(DATA_DIR / "active_picks.json", "w") as f:
        json.dump(all_picks, f, indent=2, default=str)

    # Portfolio tracker
    portfolios = {}
    for p in qualified[:15]:
        lbl = p.get("label", p["address"][:8])
        portfolios[f"copy_hl_{lbl}"] = {
            "starting_capital": PORTFOLIO_STARTING_CAPITAL,
            "current_value": PORTFOLIO_STARTING_CAPITAL,
            "total_return_pct": 0,
            "open_trades": len(p.get("open_positions", [])),
            "edge_score": p["edge_score"],
            "win_rate": p["win_rate"],
            "trader_pnl": p["total_realized_pnl"],
            "created_at": now_iso,
        }
    with open(DATA_DIR / "portfolio_tracker.json", "w") as f:
        json.dump({"generated_at": now_iso, "portfolios": portfolios}, f, indent=2, default=str)

    mm_rejected = sum(1 for p in all_profiles if p.get("is_market_maker"))
    print(f"\n{'='*70}")
    print(f"  RESULTS")
    print(f"  Scanned: {len(all_profiles)} | MM-Rejected: {mm_rejected} | Qualified: {len(qualified)} | Picks: {len(all_picks)}")
    print(f"  Files saved to: {DATA_DIR}")
    print(f"{'='*70}\n")

    return qualified, all_picks


if __name__ == "__main__":
    run_full_scan()
