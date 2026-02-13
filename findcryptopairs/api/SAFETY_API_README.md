# On-Chain Safety & Rug-Pull Detection API

A comprehensive PHP-based system for analyzing Ethereum, BSC, and Polygon tokens for safety risks and potential rug-pull indicators.

## Features

- **Contract Safety Analysis** - Checks verification, mint functions, blacklist, ownership
- **Liquidity Analysis** - Verifies locked liquidity, LP token status, adequate liquidity
- **Holder Distribution** - Analyzes whale concentration and distribution risks
- **Honeypot Detection** - Identifies tokens that cannot be sold
- **Tax Detection** - Finds hidden buy/sell taxes

## Risk Scoring System

| Score | Level | Color | Recommendation |
|-------|-------|-------|----------------|
| 80-100 | Low | 🟢 Green | Safe to trade |
| 60-79 | Medium | 🟡 Yellow | Exercise caution |
| 40-59 | High | 🟠 Orange | High risk of issues |
| 0-39 | Critical | 🔴 Red | Likely scam/rug |

### Score Breakdown

- **Contract Safety (40 points)**
  - Contract verified: +10 pts
  - No mint / ownership renounced: +10 pts
  - No blacklist: +10 pts
  - Source code available: +10 pts

- **Liquidity Safety (30 points)**
  - Liquidity locked >6 months: +15 pts
  - LP tokens burned: +10 pts
  - Adequate liquidity ($50k+): +5 pts

- **Holder Distribution (20 points)**
  - Top 10 < 30%: +10 pts
  - Top 5 < 20%: +5 pts
  - No single holder > 10%: +5 pts

- **Transaction Safety (10 points)**
  - Can sell (not honeypot): +5 pts
  - No hidden taxes > 5%: +5 pts

## API Endpoints

### 1. Full Analysis
```
GET safety_onchain.php?action=analyze&address=0x...&chain=ethereum
```

**Parameters:**
- `address` (required): Token contract address
- `chain` (optional): Chain name (ethereum, bsc, polygon, arbitrum, base). Default: ethereum
- `nocache` (optional): Set to 1 to bypass cache

**Response:**
```json
{
  "ok": true,
  "contract_address": "0x...",
  "chain": "ethereum",
  "token_name": "PEPE",
  "token_symbol": "PEPE",
  "safety_score": 75,
  "risk_level": "medium",
  "risk_color": "yellow",
  "checks": {
    "contract_verified": true,
    "mint_renounced": true,
    "no_blacklist": true,
    "source_available": true,
    "liquidity_locked": false,
    "lp_burned": true,
    "adequate_liquidity": true,
    "top10_concentration_ok": true,
    "can_sell": true,
    "taxes_ok": true
  },
  "red_flags": ["Liquidity not locked"],
  "warnings": [],
  "holder_stats": {
    "total_holders": 15000,
    "top_holder_percent": 5.2,
    "top5_percent": 18.5,
    "top10_percent": 28.3,
    "distribution_risk": "low"
  },
  "liquidity_info": {
    "has_liquidity": true,
    "liquidity_amount_usd": 2500000,
    "liquidity_locked": false,
    "lp_tokens_burned": true,
    "dex": "uniswap"
  },
  "tax_info": {
    "is_honeypot": false,
    "sell_enabled": true,
    "buy_tax": 0,
    "sell_tax": 0,
    "slippage_warning": false
  },
  "recommendation": "Trade with caution - liquidity not locked",
  "score_breakdown": {
    "contract": 40,
    "liquidity": 15,
    "holders": 20,
    "transaction": 10
  },
  "explorer_url": "https://etherscan.io/address/0x...",
  "timestamp": 1707772800
}
```

### 2. Quick Score
```
GET safety_onchain.php?action=quick&address=0x...&chain=ethereum
```

**Response:**
```json
{
  "ok": true,
  "contract_address": "0x...",
  "chain": "ethereum",
  "safety_score": 75,
  "risk_level": "medium",
  "is_honeypot": false,
  "has_mint": false,
  "can_blacklist": false,
  "contract_verified": true,
  "timestamp": 1707772800
}
```

### 3. Batch Analysis
```
GET safety_onchain.php?action=batch&addresses=0x...,0x...,0x...&chain=ethereum
```

**Response:**
```json
{
  "ok": true,
  "chain": "ethereum",
  "analyzed": 3,
  "errors": 0,
  "results": [
    {
      "address": "0x...",
      "name": "Token1",
      "symbol": "TK1",
      "score": 85,
      "risk_level": "low",
      "risk_color": "green",
      "is_honeypot": false
    }
  ],
  "timestamp": 1707772800
}
```

### 4. Holder Distribution
```
GET safety_onchain.php?action=holders&address=0x...&chain=ethereum
```

**Response:**
```json
{
  "ok": true,
  "contract_address": "0x...",
  "holder_stats": {
    "total_holders": 15000,
    "top_holder_percent": 5.2,
    "top5_percent": 18.5,
    "top10_percent": 28.3,
    "distribution_risk": "low"
  },
  "risk_assessment": {
    "risk_score": 85,
    "risk_level": "low",
    "concerns": []
  }
}
```

### 5. Honeypot Check
```
GET safety_onchain.php?action=honeypot&address=0x...&chain=ethereum
```

**Response:**
```json
{
  "ok": true,
  "contract_address": "0x...",
  "honeypot_check": {
    "is_honeypot": false,
    "sell_enabled": true,
    "buy_tax": 0,
    "sell_tax": 0
  },
  "is_safe": true,
  "warning": "",
  "timestamp": 1707772800
}
```

### 6. Health Check
```
GET safety_onchain.php?action=health
```

**Response:**
```json
{
  "ok": true,
  "service": "onchain_safety",
  "status": "operational",
  "apis": {
    "etherscan": {"status": "operational"},
    "tokensniffer": {"status": "operational"}
  },
  "timestamp": 1707772800
}
```

## Setup

### 1. Configuration
Copy `.env.example` to `.env` and add your API keys:
```bash
cp .env.example .env
```

Edit `.env` and add:
```
ETHERSCAN_API_KEY=your_key_here
TOKENSNIFFER_API_KEY=your_key_here
```

### 2. Get Free API Keys

**Etherscan:**
- Visit: https://etherscan.io/apis
- Sign up for free API key
- Rate limit: 5 calls/second

**TokenSniffer:**
- Visit: https://tokensniffer.com/api
- Free tier available
- Optional but recommended for honeypot detection

### 3. Cache Directory
Ensure the cache directory is writable:
```bash
mkdir -p cache/safety
chmod 755 cache/safety
```

## Supported Chains

| Chain | Parameter | Support |
|-------|-----------|---------|
| Ethereum | `ethereum` | ✅ Full |
| BSC | `bsc` | ✅ Full |
| Polygon | `polygon` | ✅ Full |
| Arbitrum | `arbitrum` | ✅ Full |
| Base | `base` | ✅ Full |

## Red Flags Detected

The API identifies these critical issues:

- ❌ **Honeypot** - Cannot sell tokens
- ❌ **Unverified Contract** - Source code not published
- ❌ **Mint Function** - Can create unlimited tokens
- ❌ **Blacklist** - Can block addresses from trading
- ❌ **Unlocked Liquidity** - Dev can remove liquidity
- ❌ **High Taxes** - >5% buy/sell tax
- ❌ **Whale Concentration** - Single holder >10%

## Caching

Results are cached for improved performance:
- Full analysis: 1 hour
- Quick score: 30 minutes
- Honeypot check: 30 minutes

Use `?nocache=1` to bypass cache.

## Error Handling

All errors return a consistent format:
```json
{
  "ok": false,
  "error": "Description of what went wrong"
}
```

Common errors:
- Invalid address format
- API rate limits exceeded
- Contract not found
- API keys invalid/missing

## Security Notes

⚠️ **Disclaimer:** This tool provides analysis based on available on-chain data and third-party APIs. It cannot guarantee a token is safe. Always:

1. Do your own research (DYOR)
2. Only invest what you can afford to lose
3. Check multiple sources before investing
4. Be aware that contracts can be upgraded (proxies)
5. New exploits may not be detected immediately

## PHP Requirements

- PHP 5.2+ (compatible with legacy systems)
- cURL or allow_url_fopen enabled
- JSON extension
- Write permissions for cache directory

## Files

- `safety_onchain.php` - Main API endpoint
- `safety_etherscan.php` - Etherscan API wrapper
- `safety_tokensniffer.php` - TokenSniffer API wrapper
- `.env.example` - Configuration template
- `cache/safety/` - Cache directory (created automatically)

## Example Usage

### JavaScript/Fetch
```javascript
async function checkToken(address) {
  const response = await fetch(
    `safety_onchain.php?action=analyze&address=${address}&chain=ethereum`
  );
  const data = await response.json();
  
  if (data.ok) {
    console.log(`Score: ${data.safety_score}/100`);
    console.log(`Risk: ${data.risk_level}`);
    console.log(`Recommendation: ${data.recommendation}`);
  }
}
```

### PHP
```php
require_once 'safety_onchain.php';

$result = analyzeToken('0x...', 'ethereum');
echo "Safety Score: " . $result['safety_score'] . "/100\n";
echo "Risk Level: " . $result['risk_level'] . "\n";
```

### cURL
```bash
curl "https://yoursite.com/findcryptopairs/api/safety_onchain.php?action=analyze&address=0x...&chain=ethereum"
```

## License

This tool is for educational and research purposes. Use at your own risk.
