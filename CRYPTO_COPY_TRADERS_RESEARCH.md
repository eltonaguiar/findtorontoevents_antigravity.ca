# Crypto Copy Traders Research — Top Performers & Data Extraction Guide

**Last Updated:** 2025-07-11  
**Status:** Verified — scraping/API access confirmed before data collection  
**Purpose:** Identify the world's best verifiable copy traders, document how to scrape their strategies, and reverse-engineer trading styles

---

## Executive Summary

| Platform | Public Data | Method | Quality |
|---|---|---|---|
| **OKX** | ✅ Fully public, NO auth | REST API (JSON) | ⭐⭐⭐⭐⭐ Best |
| **Bitget** | ✅ HTML scraping works | Web scraping | ⭐⭐⭐⭐ Great |
| **Hyperliquid** | ✅ Blockchain-transparent | REST API (POST) | ⭐⭐⭐⭐ Great |
| **Copin.io** | ✅ Multi-protocol aggregator | Web/API | ⭐⭐⭐ Good aggregator |
| **Bybit** | ✅ Public (CDN-protected) | REST API (beehive) | ⭐⭐⭐ Good |
| **Binance** | ❌ Blocked | JS-rendered, no public API found | ⭐ Poor |

**Bottom line:** OKX gives everything — full trade history with timestamps, entry/exit prices, leverage — all via unauthenticated REST API. Use OKX as the primary data source. Bitget HTML scraping works cleanly as secondary source. Hyperliquid has a fully open blockchain-based API.

---

## Part 1: OKX Copy Trading (Primary Data Source)

### Confirmed Working API Endpoints (No Auth Required)

#### 1. Get Trader Leaderboard
```
GET https://www.okx.com/api/v5/copytrading/public-lead-traders
```

**Response Fields:**
| Field | Description |
|---|---|
| `uniqueCode` | Unique trader identifier (needed for other endpoints) |
| `nickName` | Display name |
| `pnl` | 90-day absolute PnL in USDT |
| `pnlRatio` | 90-day PnL ratio (e.g., `2.1574` = +215.74%) |
| `winRatio` | Win rate (e.g., `0.542` = 54.2%) |
| `aum` | Total AUM in USDT managed |
| `copyTraderNum` | Current number of copiers |
| `accCopyTraderNum` | Maximum allowed copiers |
| `leadDays` | Days active as lead trader |
| `traderInsts[]` | List of instruments traded |
| `pnlRatios[]` | Array of 20 weekly PnL snapshots (equity curve) |

#### 2. Get Trader's Current Open Positions
```
GET https://www.okx.com/api/v5/copytrading/public-current-subpositions?uniqueCode={CODE}
```

**Response Fields:**
| Field | Description |
|---|---|
| `instId` | Instrument (e.g., `BTC-USDT-SWAP`) |
| `posSide` | `long` or `short` |
| `lever` | Leverage used |
| `mgnMode` | `cross` or `isolated` margin |
| `openAvgPx` | Average entry price |
| `openTime` | Entry timestamp (epoch ms) |
| `upl` | Unrealized PnL current |
| `uplRatio` | Unrealized PnL ratio |

#### 3. Get Trader's Historical Trades ⭐ (Most Valuable for Strategy Analysis)
```
GET https://www.okx.com/api/v5/copytrading/public-subpositions-history?uniqueCode={CODE}&limit=100
```

**Response Fields:**
| Field | Description |
|---|---|
| `instId` | Instrument traded |
| `posSide` | `long` or `short` |
| `lever` | Leverage used |
| `mgnMode` | Margin mode |
| `openAvgPx` | Entry price |
| `closeAvgPx` | Exit price |
| `openTime` | Entry timestamp in epoch ms |
| `closeTime` | Exit timestamp in epoch ms |
| `pnl` | Realized PnL in USDT |
| `pnlRatio` | Return on position |
| `subPos` | Sub-position size |
| `subPosId` | Unique trade ID |

### How to Calculate Hold Time
```python
hold_hours = (int(closeTime) - int(openTime)) / 3_600_000
```

### Python Scraper Template
```python
import requests

BASE = "https://www.okx.com/api/v5/copytrading"

def get_top_traders():
    r = requests.get(f"{BASE}/public-lead-traders")
    return r.json()["data"]

def get_trade_history(unique_code, limit=100):
    url = f"{BASE}/public-subpositions-history"
    params = {"uniqueCode": unique_code, "limit": limit}
    r = requests.get(url, params=params)
    trades = r.json()["data"]
    for t in trades:
        t["hold_hours"] = (int(t["closeTime"]) - int(t["openTime"])) / 3_600_000
    return trades

def get_open_positions(unique_code):
    url = f"{BASE}/public-current-subpositions"
    r = requests.get(url, params={"uniqueCode": unique_code})
    return r.json()["data"]

# Example: Analyze CrowleyZhou
trades = get_trade_history("99FB5ECCC0C27A8A", limit=100)
avg_hold = sum(t["hold_hours"] for t in trades) / len(trades)
win_rate = sum(1 for t in trades if float(t["pnl"]) > 0) / len(trades)
avg_leverage = sum(float(t["lever"]) for t in trades) / len(trades)
print(f"Avg hold: {avg_hold:.1f}h | Win rate: {win_rate:.0%} | Avg leverage: {avg_leverage:.1f}x")
```

---

## Part 2: Top OKX Traders — Verified Data

All traders below have `uniqueCode` confirmed — can be queried directly via API.

| # | Trader | uniqueCode | 90D PnL % | 90D PnL $ | Copiers | Max Copiers | AUM | Days Active | Win Rate |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Expert-Ethash-Camel** | `1173EC858F15E04F` | **+1,053.34%** | $150,500 | 301 | 301 MAX | $164K | 821 | — |
| 2 | **nightraid-** | `849CAD818B573125` | +255.31% | $131,758 | 372 | 600 | $164K | 405 | — |
| 3 | **Fair-Hash-Maverick** | `0C053614746975C0` | +238.32% | $249,761 | 300 | 300 MAX | $77K | 404 | — |
| 4 | **CrowleyZhou** | `99FB5ECCC0C27A8A` | +215.74% | $389,045 | 580 | 600 | $439K | 147 | — |
| 5 | **FJ Investment** | `AD2B6E949E5E91EC` | +125.68% | $211,900 | 86 | 310 | $520K | 724 | 54.22% |
| 6 | **Trader KS** | `D442CF34E4AEEAF1` | +99.93% | $205,774 | 78 | 300 | $52K | 504 | 61.9% |

**Key Observations:**
- `Expert-Ethash-Camel` → +1,053% in 90 days — extraordinary outlier, fully maxed copiers (301/301), 821 days of consistent performance
- `CrowleyZhou` → Best AUM ($439K) + highest copiers below max (580/600), newer trader at 147 days
- `FJ Investment` → 724-day veteran with $520K AUM — most institutional-grade profile
- `Trader KS` → Highest win rate (61.9%) among the named traders

### CrowleyZhou Live Trade Sample (API-verified)
```
Instrument:  ICP-USDT-SWAP
Direction:   Long
Leverage:    10x (cross margin)
Entry:       $2.588
Exit:        $2.668
Hold Time:   ~106 hours (~4.4 days)
PnL:         +$2,061 (+49.77% on position)
```
→ **Style:** Medium-term swing trader, cross margin, leveraged longs on altcoins

---

## Part 3: Top Bitget Traders — Verified Data

Scraping method: **HTML scraping** — `https://www.bitget.com/copy-trading/futures` renders full stats.

Individual profiles at: `https://www.bitget.com/copy-trading/trader/{PROFILE_ID}/futures`

| # | Name | Handle | 30D ROI | 30D Profit | Max DD | Win Rate | Copiers | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | WIN-2026 | @BGUSER-X15KWVSN | **+19,396%** | $38,784 | 70.6% | 89.5% | 354/500 | ETHUSDT, BTCUSDT |
| 2 | DeepSeek-V4 | @BGUSER-YLCSRYTY | +12,017% | $41,585 | 83.4% | 100% | 437/1000 | ETHUSDT only |
| 3 | 来者发财 | @BGUSER-57E4J14D | +12,731% | $25,529 | 93.2% | 92.9% | 214/600 | ETHUSDT only |
| 4 | ICHIZENCapital | @ICHIZENCapital | +4,302% | $14,928 | **21.6%** | 34.6% | 0/600 | Low DD standout ⭐ |
| 5 | **hale** | @hale | +61.04% | $160,605 | **15.5%** | 57.1% | 750/750 MAX | Multi-coin, 1605 days ⭐ |
| 6 | **Bg-ATM** | @BGUSER-D3ZSGEF5 | +57.48% | $117,938 | **14.7%** | 90.3% | 450/500 | BTCUSDT only, 86 days ⭐ |
| 7 | Rich💰💰 | @BGUSER-9G3FB5CG | +64.69% | $115,939 | 36.9% | 100% | 373/500 | BTCUSDT, ETHUSD |
| 8 | 發哥 | @BGUSER-437X4N8S | +58.8% | $116,166 | 40.4% | 92.1% | 174/500 | ETHUSDT, BTCUSDT |
| 9 | 小小的躺赢 | @btctangying | +3.1% | $74,407 | **9.6%** | 100% | 13/500 | BTCUSDT, lowest DD |
| 10 | woshiguaizi | @woshiguaizi | +0.47% | $6,927 | 11.7% | 84.6% | 297/500 | $102K copier PnL |

**Bitget Profile IDs (for direct page scraping):**
- hale: `b1b5467f8bb73f53ac97`
- Bg-ATM: `b0bd4a7e86bb3956a49c`

**Key Observations:**
- Top 3 ROI traders (WIN-2026, DeepSeek-V4, 来者发财) have extremely high drawdowns (70-93%) — these are **high-risk exploders**, not sustainable
- **Stars with quality risk/reward:**
  - `hale` — 1605 days, maxed 750 copiers, 15.5% DD, 57% win rate → gold standard long-term performer
  - `Bg-ATM` — Only 86 days but 90.3% win rate and just 14.7% DD → exceptional risk-adjusted returns
  - `ICHIZENCapital` — 21.6% DD on +4,302% ROI → best risk/return profile on leaderboard
  - `小小的躺赢` — 9.6% DD (lowest), 100% win rate, BTCUSDT only → ultra-conservative scalper

---

## Part 4: Hyperliquid Leaderboard

Hyperliquid is a fully on-chain perpetuals DEX. All data is publicly verifiable on-chain.

**Leaderboard URL:** `https://app.hyperliquid.xyz/leaderboard`  
*(Note: Frontend is JS-rendered — use the API below for programmatic access)*

### Hyperliquid API (Public, No Auth)
```
POST https://api.hyperliquid.xyz/info
Content-Type: application/json

{"type": "leaderboard"}
```

### Top Traders from Hyperliquid Leaderboard (30D, verified live)

Note: Only accounts with ≥$100K balance AND ≥$10M trading volume are shown.

| Rank | Address | Account Value | 30D PnL | 30D ROI |
|---|---|---|---|---|
| 1 | 0x393d...2109 | $849,857,363 | **+$206,396,118** | +30.59% |
| 2 | 0x488d...fe08 | $124,545,456 | +$31,490,490 | +33.84% |
| 3 | 0xe44b...9ea8 | $111,459,704 | +$28,423,898 | +34.23% |
| 4 | 0x05ca...c655 | $96,567,116 | +$25,100,551 | +35.12% |

**Data available per Hyperliquid address (via API):**
- Full trade history (entry/exit/leverage/instrument)
- Open/closed positions
- Portfolio equity curve
- Vault participation

**Note:** Hyperliquid traders are anonymous addresses. Cross-reference with Copin.io or Nansen to identify known traders by wallet.

---

## Part 5: Copin.io — Multi-Protocol Aggregator

Copin.io aggregates data across **14+ perpetual DEX and CEX protocols:**

| Protocol | Type |
|---|---|
| Hyperliquid | DEX |
| GMX (Arbitrum/Avalanche) | DEX |
| Kwenta (Optimism) | DEX |
| dYdX | DEX |
| gTrade (Gains Network) | DEX |
| ApeX Protocol | DEX |
| AVANTIS (Base) | DEX |
| Bitget | CEX |
| OKX | CEX |
| Bybit | CEX |
| BingX | CEX |
| Gate.io | CEX |

**Explorer URL:** `https://app.copin.io/explorer?protocol=HYPERLIQUID&sort=pnl&order=desc`

The Copin.io dataset covers **2M+ trader profiles** and **billions of positions**  
Use it to find the same trader across multiple platforms (cross-platform performance validation).

---

## Part 6: Trading Style Reverse Engineering Guide

### What You Can Extract from the OKX API

From `public-subpositions-history`, you can reverse-engineer:

| Pattern | How to Calculate | Significance |
|---|---|---|
| **Hold Time** | `(closeTime - openTime) / 3,600,000` | Scalper vs swing vs position trader |
| **Leverage Preference** | Average `lever` across all trades | Risk appetite |
| **Directional Bias** | % of trades with `posSide == "long"` vs `"short"` | Bull/bear bias |
| **Instrument Focus** | Most frequent `instId` values | Asset specialization |
| **Trade Frequency** | Trades per day over active period | Trading style |
| **Risk Management** | Max single trade loss / average win | Position sizing discipline |
| **Session Timing** | Hour distribution of `openTime` (UTC) | Trading session (Asia/EU/US) |
| **Margin Style** | `mgnMode` distribution | Cross vs isolated (risk management approach) |
| **Bet Sizing** | `subPos` values relative to account | Position sizing consistency |

### Trader Archetypes (Identifiable from Data)

| Archetype | Hold Time | Leverage | Win Rate | DD Profile |
|---|---|---|---|---|
| **Scalper** | < 2 hours | 10-50x | >70% | High |
| **Day Trader** | 2–24 hours | 5-20x | 55-70% | Medium |
| **Swing Trader** | 1–7 days | 2-10x | 50-60% | Low-Medium |
| **Position Trader** | > 7 days | 1-5x | 45-55% | Low |
| **High-Risk Exploiter** | Any | 20-100x | Any | Very High |

### Entry Criteria Signals (What to Look For)

Since the API gives entry prices but not the reason for entry, you can:

1. **Cross-reference entry price with chart** — Did they enter at a key S/R level? After a breakout?
2. **Look at leverage consistency** — A trader always using 10x is systematic; varying leverage suggests discretionary
3. **Instrument concentration** — Single-coin traders => deep knowledge / edge in that market
4. **Long bias vs short bias** — Long-biased in alt rallies suggests trend-following
5. **Entry timing** — Use UTC hour of `openTime` to identify preferred market session

---

## Part 7: High-Priority Targets for Deep Analysis

### Tier 1 — Best Risk-Adjusted Performers (Verified)

1. **Expert-Ethash-Camel (OKX)** — `uniqueCode: 1173EC858F15E04F`
   - +1,053% in 90 days, 821 days on platform, maxed out copiers
   - Use the API to get 100+ trades and calculate average hold time, leverage, instruments

2. **hale (Bitget)** — `@hale`, profile `b1b5467f8bb73f53ac97`
   - 1605 days active, 750/750 MAX copiers (most followed on Bitget), 15.5% DD
   - HTML scrape their profile for full statistics

3. **Bg-ATM (Bitget)** — `@BGUSER-D3ZSGEF5`, profile `b0bd4a7e86bb3956a49c`
   - 86 days old but 90.3% win rate, 14.7% DD — remarkable new entrant
   - BTCUSDT only → very focused specialist

### Tier 2 — Interesting Edge Cases

4. **小小的躺赢 (Bitget)** — `@btctangying`
   - Only 9.6% DD with 100% win rate, BTCUSDT only
   - Likely a scalper or ultra-tight risk management

5. **ICHIZENCapital (Bitget)** — `@ICHIZENCapital`
   - +4,302% ROI with only 21.6% DD — extremely high return with controlled downside

### Tier 3 — High-Risk High-Return (For Research Only)

6. **WIN-2026 (Bitget)** — `@BGUSER-X15KWVSN`
   - +19,396% 30D ROI — but 70.6% max drawdown, not sustainable
   - Worth studying the entry mechanics but dangerous to copy

---

## Part 8: Data Collection Workflow

### Step 1: Collect OKX Traders
```python
import requests, json, time

def harvest_okx_traders():
    traders = requests.get(
        "https://www.okx.com/api/v5/copytrading/public-lead-traders"
    ).json()["data"]
    
    results = []
    for trader in traders:
        code = trader["uniqueCode"]
        time.sleep(0.5)  # Be polite
        history = requests.get(
            f"https://www.okx.com/api/v5/copytrading/public-subpositions-history",
            params={"uniqueCode": code, "limit": 100}
        ).json().get("data", [])
        
        if history:
            hold_times = [
                (int(t["closeTime"]) - int(t["openTime"])) / 3_600_000 
                for t in history
            ]
            levers = [float(t["lever"]) for t in history]
            pnls = [float(t["pnl"]) for t in history]
            instruments = [t["instId"] for t in history]
            
            trader["avg_hold_hours"] = sum(hold_times) / len(hold_times)
            trader["avg_leverage"] = sum(levers) / len(levers)
            trader["win_rate_calc"] = sum(1 for p in pnls if p > 0) / len(pnls)
            trader["top_instrument"] = max(set(instruments), key=instruments.count)
            trader["total_pnl_usd"] = sum(pnls)
        
        results.append(trader)
    
    with open("okx_traders_full.json", "w") as f:
        json.dump(results, f, indent=2)
    
    return results
```

### Step 2: Scrape Bitget Leaderboard
```python
import requests
from bs4 import BeautifulSoup

def scrape_bitget_leaderboard():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    url = "https://www.bitget.com/copy-trading/futures"
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    # Parse trader cards from rendered HTML
    # All stats (ROI, profit, DD, win rate, copiers) are in the HTML
    return soup

def get_bitget_trader_profile(profile_id):
    url = f"https://www.bitget.com/copy-trading/trader/{profile_id}/futures"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    r = requests.get(url, headers=headers)
    return BeautifulSoup(r.text, "html.parser")
```

### Step 3: Hyperliquid API
```python
def get_hyperliquid_leaderboard(window="day"):
    # window options: "day", "week", "month", "allTime"
    r = requests.post(
        "https://api.hyperliquid.xyz/info",
        json={"type": "leaderboard"},
        headers={"Content-Type": "application/json"}
    )
    return r.json()

def get_hyperliquid_trader_fills(address):
    r = requests.post(
        "https://api.hyperliquid.xyz/info",
        json={"type": "userFills", "user": address},
        headers={"Content-Type": "application/json"}
    )
    return r.json()
```

---

## Part 9: Recommended Analysis Pipeline

```
1. Pull OKX leaderboard → filter by 90D PnL ratio > 50% AND leadDays > 90
2. For each trader: pull last 100 trades → calculate avg hold, leverage, bias
3. Run same filter on Bitget HTML scrape → filter by DD < 25% AND 30D ROI > 30%
4. Cross-reference top traders on Copin.io (same address, different platforms)
5. For any trader with consistent edge: pull 6 months of trades, tag by:
   - Instrument category (BTC, ETH, alts, narrative tokens)
   - Market condition (trending vs ranging)
   - Entry at support/resistance vs breakout
6. Build signal profile: 
   - Direction bias score
   - Avg hold time
   - Preferred leverage range
   - Preferred market session
   - Best performing instruments
7. Output: Per-trader "trade fingerprint" for copy-trade filtering
```

---

## Appendix: Quick Reference Links

| Resource | URL |
|---|---|
| OKX Copy Trading Leaderboard | https://www.okx.com/copy-trading |
| OKX Public API (lead traders) | https://www.okx.com/api/v5/copytrading/public-lead-traders |
| Bitget Copy Trading Leaderboard | https://www.bitget.com/copy-trading/futures |
| Hyperliquid Leaderboard | https://app.hyperliquid.xyz/leaderboard |
| Hyperliquid API | https://api.hyperliquid.xyz/info |
| Copin.io Explorer | https://app.copin.io/explorer |
| Copin.io Docs | https://docs.copin.io |

---

*Original research conducted by analyzing live data from OKX API (unauthenticated), Bitget web scraping, and Hyperliquid leaderboard. All trader metrics reflect data at time of research. Past performance does not guarantee future results.*

---

## Part 10: Social & Analytics Platform Reverse-Engineering (Added 2026-03-19)

### Source Assessment Matrix

| Platform | Public Data | Method | Cost | Viability |
|---|---|---|---|---|
| **Whale Alert** | Full transfers >$100K | REST API (free tier) | Free (10 req/min) | BEST |
| **Etherscan** | All ETH txns + token transfers | REST API (free tier) | Free (5 req/sec) | BEST |
| **Arkham Intelligence** | Labeled entities, portfolios | REST API (free tier) | Free (10 req/min) | BEST |
| **Twitter/X** | Tweets (trade calls) | API v2 ($100/mo) or twscrape | $0-$100/mo | Medium |
| **TradingView** | Ideas (JS-rendered) | Playwright scraping | Free but slow | Medium |
| **CryptoQuant** | On-chain metrics | REST API | $39/mo for Pro | Medium |
| **Glassnode** | Entity metrics | REST API | $39-$799/mo | Low (expensive) |
| **Nansen** | Smart money labels | No public API | Enterprise only | Skip |
| **3Commas** | Bot marketplace | Auth-only API | No public stats | Skip |
| **Zignaly** | Profit sharing pools | No API | Platform shrinking | Skip |
| **Shrimpy** | N/A | Shut down | N/A | Dead |

### TOP 3 Implemented: Whale Alert + Etherscan + Arkham

See standalone scanner files:
- `alpha_engine/whale_alert_scanner.py`
- `alpha_engine/etherscan_whale_tracker.py`
- `alpha_engine/arkham_smart_money.py`

---

## Part 11: Whale Alert API — Large Transfer Tracking

**Free tier:** 10 requests/min, no credit card required. Get API key at https://whale-alert.io/

**What it gives you:** Real-time alerts for crypto transfers >$100K between wallets, exchanges, and unknown addresses. The key signal: large transfers FROM exchanges (withdrawals = accumulation) and TO exchanges (deposits = likely selling).

### Whale Alert API Endpoints

```
GET https://api.whale-alert.io/v1/transactions
  ?api_key={KEY}
  &min_value=500000          # Minimum USD value
  &start={unix_timestamp}    # Start time (max 1h ago on free tier)
  &cursor={cursor}           # Pagination

GET https://api.whale-alert.io/v1/status
  ?api_key={KEY}             # Check API status + remaining quota
```

**Response fields:**
| Field | Description |
|---|---|
| `blockchain` | bitcoin, ethereum, tron, etc. |
| `symbol` | BTC, ETH, USDT, etc. |
| `id` | Unique transaction hash |
| `transaction_type` | `transfer`, `mint`, `burn` |
| `from.owner` | Source entity name (e.g., "binance", "unknown") |
| `from.owner_type` | `exchange`, `unknown` |
| `to.owner` | Destination entity name |
| `to.owner_type` | `exchange`, `unknown` |
| `amount` | Amount of tokens transferred |
| `amount_usd` | USD value at time of transfer |
| `timestamp` | Unix timestamp |

### Signal Derivation Logic

| Pattern | Signal | Rationale |
|---|---|---|
| Exchange -> Unknown (large BTC/ETH) | **Bullish** | Whale withdrawing to cold storage = accumulation |
| Unknown -> Exchange (large BTC/ETH) | **Bearish** | Whale depositing to sell |
| Exchange -> Exchange (stablecoins) | **Neutral/Watch** | Rebalancing between venues |
| Mint (USDT/USDC) | **Bullish** | New stablecoins = fresh buying power |
| Burn (USDT/USDC) | **Bearish** | Stablecoins redeemed = capital leaving crypto |
| Unknown -> Unknown (very large) | **Watch** | OTC deal or internal transfer |

---

## Part 12: Etherscan Whale Wallet Tracker — ETH Ecosystem

**Free tier:** 5 calls/sec, 100K calls/day. Get API key at https://etherscan.io/apis

**Strategy:** Track known whale/fund wallets. When they accumulate a token, that is a leading indicator. Key labeled addresses come from Arkham, Etherscan labels, or community-maintained lists.

### Etherscan API Endpoints Used

```
# Get ETH balance for an address
GET https://api.etherscan.io/api?module=account&action=balance&address={ADDR}&tag=latest&apikey={KEY}

# Get ERC-20 token transfers for a wallet (last 100)
GET https://api.etherscan.io/api?module=account&action=tokentx&address={ADDR}&startblock=0&endblock=99999999&sort=desc&page=1&offset=100&apikey={KEY}

# Get normal ETH transactions
GET https://api.etherscan.io/api?module=account&action=txlist&address={ADDR}&startblock=0&endblock=99999999&sort=desc&page=1&offset=50&apikey={KEY}
```

### Known Whale/Fund Addresses (Public Labels)

| Entity | Address | Type |
|---|---|---|
| Justin Sun | `0x176F3DAb24a159341c0509bB36B833E7fdd0a132` | Individual whale |
| Vitalik Buterin | `0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045` | Ethereum founder |
| Wintermute | `0x0000006daea1723962647b7e189d311d757Fb793` | Market maker |
| Jump Trading | `0x9507c04B10486547584C37bCBd931B2a4FeE9A41` | Market maker |
| Paradigm | `0xcDbE43Ab7eFB23D9A3f4fB76b474E7e1E19ee00C` | VC fund |
| Binance Hot | `0x28C6c06298d514Db089934071355E5743bf21d60` | Exchange hot wallet |
| Coinbase Hot | `0x71660c4005BA85c37ccec55d0C4493E66Fe775d3` | Exchange hot wallet |

---

## Part 13: Arkham Intelligence — Labeled Smart Money Tracking

**Free tier:** 10 req/min, basic entity data, transfer alerts. Sign up at https://platform.arkhamintelligence.com/

**What makes Arkham special:** They label 300K+ addresses with real entity names (funds, protocols, individuals). You can search "what is Paradigm buying" and get actual answers.

### Arkham API Endpoints

```
# Search for an entity
GET https://api.arkhamintelligence.com/intelligence/entity/search?query=paradigm
  Headers: API-Key: {KEY}

# Get entity portfolio
GET https://api.arkhamintelligence.com/intelligence/address/{ADDRESS}/portfolio
  Headers: API-Key: {KEY}

# Get transfers for an entity
GET https://api.arkhamintelligence.com/intelligence/transfers?address={ADDRESS}&limit=50
  Headers: API-Key: {KEY}

# Get token page (aggregated holder data)
GET https://api.arkhamintelligence.com/intelligence/token/{CONTRACT_ADDRESS}
  Headers: API-Key: {KEY}
```

### Smart Money Entities to Track
- paradigm, a16z, jump-trading, wintermute, galaxy-digital
- pantera-capital, dragonfly-capital, polychain-capital, multicoin-capital

---

## Part 14: Twitter/X Crypto Trader Tracking (Supplementary)

**Access methods (ranked by reliability):**

1. **twscrape** (Python library, free): Requires burner Twitter accounts for authentication, but scrapes without official API. Install: `pip install twscrape`. Works as of early 2025 but X actively fights it.

2. **Twitter API v2 Basic ($100/month):** 10K tweet reads/month. Endpoint: `GET https://api.twitter.com/2/tweets/search/recent?query=...`. Useful queries:
   - `"$BTC long" OR "$BTC short" OR "entry:" (has:media OR has:links)` — trade calls
   - `from:CryptoCred OR from:HsakaTrades OR from:EmperorBTC` — specific traders

3. **Social aggregators (free, indirect):**
   - **LunarCrush** (already integrated): Galaxy Score, social volume, influencer tracking
   - **Santiment** free tier: Social volume metrics, trending words

**Known high-signal Twitter accounts (community consensus):**
- @CryptoCred — Technical analysis educator, verifiable calls
- @HsakaTrades — SFP/structure trader (basis for our swing_failure_pattern strategy)
- @EmperorBTC — Education + calls
- @inversebrah — Contrarian sentiment indicator
- @GCRClassic — Macro + alt rotation calls
- @Pentosh1 — HTF structure (basis for our pentoshi_htf_structure strategy)

**Trade call regex pattern:**
```
TRADE_CALL_REGEX = r'\$?(BTC|ETH|SOL|[A-Z]{3,5})\s*(long|short|buy|sell)\s*(?:@|entry:?\s*)\$?([\d,.]+)'
```

---

## Part 15: TradingView Idea Scraping (Supplementary)

**No public API.** Requires browser automation (Playwright/Selenium).

**Undocumented widget endpoint (limited but works):**
```
GET https://www.tradingview.com/ideas-widget/?locale=en&sort=recent&stream=BTCUSD
```
Returns HTML fragments with idea titles, authors, timestamps, and direction (long/short badges). Parseable with BeautifulSoup but rate-limited.

**Verdict:** Too slow and fragile for production. Copy-trader APIs (OKX, Bitget) give exact trade data instead of subjective "ideas."

---

## Part 16: CryptoQuant / Glassnode (Supplementary)

**CryptoQuant Quicktake feed** (public, scrapeable):
```
GET https://cryptoquant.com/quicktake
```
Contains analyst posts about whale movements, exchange flows, miner behavior.

**Glassnode free tier** (very limited):
```
GET https://api.glassnode.com/v1/metrics/market/price_usd_close?a=BTC&i=24h&api_key={KEY}
```

**Better free alternatives already in the codebase:**
- `blockchain.info/charts/` — hash rate, difficulty, TX volume (used by `onchain_strategies.py`)
- `api.alternative.me/fng/` — Fear & Greed index (used by `onchain_strategies.py`)
- Binance public API — funding rates, open interest

These are already integrated into the Alpha Engine. Paid CryptoQuant/Glassnode tiers add entity-level tracking that Etherscan + Arkham cover for free.

---

## Appendix: Updated Quick Reference Links

| Resource | URL | Cost |
|---|---|---|
| OKX Copy Trading API | https://www.okx.com/api/v5/copytrading/public-lead-traders | Free |
| Bitget Copy Trading | https://www.bitget.com/copy-trading/futures | Free (scrape) |
| Hyperliquid API | https://api.hyperliquid.xyz/info | Free |
| Copin.io Explorer | https://app.copin.io/explorer | Free |
| Whale Alert API | https://whale-alert.io/ | Free (10 req/min) |
| Etherscan API | https://etherscan.io/apis | Free (5 req/sec) |
| Arkham Intelligence | https://platform.arkhamintelligence.com/ | Free tier |
| Arkham API Docs | https://docs.arkhamintelligence.com/ | Free tier |
| Twitter API v2 | https://developer.twitter.com/en/docs | $100/mo (Basic) |
| twscrape (Python) | https://github.com/vladkens/twscrape | Free (fragile) |
| TradingView Ideas | https://www.tradingview.com/ideas/ | Free (JS scraping) |
| CryptoQuant | https://cryptoquant.com/ | $39/mo Pro |
| Glassnode | https://glassnode.com/ | $39-$799/mo |
| LunarCrush (existing) | https://lunarcrush.com/ | Free tier |

---

*Updated 2026-03-19 with social/analytics platform research. Top 3 actionable sources: Whale Alert (free API, real-time whale transfers), Etherscan (free API, ETH whale wallet tracking), Arkham Intelligence (free tier, labeled smart money). Past performance does not guarantee future results.*
