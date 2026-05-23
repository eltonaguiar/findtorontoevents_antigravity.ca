#!/usr/bin/env python3
"""
COPY TRADER LIVE INTELLIGENCE GATHERER
Queries OKX, Hyperliquid, and Binance for real-time trader positions.
Generates consensus report: copy_trader_intel/data/live_intelligence_report.json
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import ssl
from datetime import datetime, timezone
from collections import defaultdict

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')
    sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', closefd=False, errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

TIMEOUT = 12
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
}

def api_get(url, label=""):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            print(f"  [OK] {label or url}")
            return data
    except urllib.error.HTTPError as e:
        print(f"  [HTTP {e.code}] {label or url}: {e.reason}")
        return None
    except Exception as e:
        print(f"  [ERR] {label or url}: {type(e).__name__}: {e}")
        return None

def api_post(url, body, label=""):
    try:
        payload = json.dumps(body).encode()
        req = urllib.request.Request(url, data=payload, headers=HEADERS, method="POST")
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            print(f"  [OK] {label or url}")
            return data
    except urllib.error.HTTPError as e:
        print(f"  [HTTP {e.code}] {label or url}: {e.reason}")
        return None
    except Exception as e:
        print(f"  [ERR] {label or url}: {type(e).__name__}: {e}")
        return None


# ============================================================
# 1. OKX COPY TRADING - SEED TRADERS (verified codes)
# ============================================================
OKX_SEED_TRADERS = [
    {"uniqueCode": "1173EC858F15E04F", "nickName": "Expert-Ethash-Camel", "note": "+1071% ROI"},
    {"uniqueCode": "849CAD818B573125", "nickName": "nightraid-", "note": "+281% ROI"},
    {"uniqueCode": "0C053614746975C0", "nickName": "Fair-Hash-Maverick", "note": "+238% ROI, 82.9% WR"},
    {"uniqueCode": "99FB5ECCC0C27A8A", "nickName": "CrowleyZhou", "note": "$479K AUM, 600 copiers"},
    {"uniqueCode": "AD2B6E949E5E91EC", "nickName": "FJ Investment", "note": "+125% 90d"},
    {"uniqueCode": "D442CF34E4AEEAF1", "nickName": "Trader KS", "note": "+103% ROI"},
    {"uniqueCode": "8DADD51A63B6D30F", "nickName": "DL-Trading", "note": "+104% ROI, 72.7% WR"},
    {"uniqueCode": "823664FB73B79E41", "nickName": "Junglelaw", "note": "$5.37M AUM, stability king"},
    {"uniqueCode": "097F20F08F8BEB70", "nickName": "pikawenjiatouzi", "note": "+55% ROI"},
    {"uniqueCode": "609DDBB0C0532E3D", "nickName": "old leeks", "note": "+54% ROI, veteran"},
]

OKX_MIRRORS = ["https://www.okx.com", "https://aws.okx.com", "https://okx.com"]

def fetch_okx_traders():
    print("\n=== OKX COPY TRADING (10 seed traders) ===")
    traders = []
    positions_all = []

    for t in OKX_SEED_TRADERS:
        code = t["uniqueCode"]
        nick = t["nickName"]
        traders.append({"source": "OKX", "uniqueCode": code, "nickname": nick, "note": t.get("note", "")})

        got = False
        for mirror in OKX_MIRRORS:
            url = f"{mirror}/api/v5/copytrading/public-current-subpositions?instType=SWAP&uniqueCode={code}&limit=20"
            pdata = api_get(url, f"OKX {nick} ({mirror.split('//')[1].split('.')[0]})")
            if pdata and pdata.get("code") == "0":
                for p in (pdata.get("data") or []):
                    positions_all.append({
                        "source": "OKX",
                        "trader": nick,
                        "traderCode": code,
                        "symbol": p.get("instId", ""),
                        "direction": "LONG" if p.get("posSide") == "long" else "SHORT",
                        "size": p.get("subPosQty", "0"),
                        "avgPrice": p.get("avgPx", "0"),
                        "markPrice": p.get("markPx", "0"),
                        "pnl": p.get("pnl", "0"),
                        "leverage": p.get("lever", "1"),
                        "openTime": p.get("openTime", ""),
                    })
                got = True
                break
            time.sleep(0.3)

        if not got:
            print(f"    (no data for {nick})")
        time.sleep(0.5)

    print(f"  Total: {len(traders)} traders, {len(positions_all)} open positions")
    return traders, positions_all


# ============================================================
# 2. HYPERLIQUID - TOP WHALES (verified addresses from scraper)
# ============================================================
HL_WHALES = [
    ("0x0ddf9bae2af4b874b96d287a5ad42eb47138a902", "PensionFund_24M"),
    ("0x162cc7c861ebd0c06b3d72319201150482518185", "ABC_41M"),
    ("0x87f9cd15f5050a9283b8896300f7c8cf69ece2cf", "whale_52M"),
    ("0xecb63caa47c7c4e77f60f1ce858cf28dc2b82b00", "whale_201M"),
    ("0x023a3d058020fb76cca98f01b3c48c8938a22355", "Auros_66M"),
    ("0x7fdafde5cfb5465924316eced2d3715494c517d1", "BobbyBigSize_161M"),
    ("0xdfc24b077bc1425ad1dea75bcb6f8158e10df303", "whale_440M_acct"),
    ("0x880ac484a1743862989a441d6d867238c7aa311c", "x35767_113M"),
    ("0xbdfa4f4492dd7b7cf211209c4791af8d52bf5c50", "whale_75M_675roi"),
    ("0x493db0ed7514c975e9abcc110bd40c473b6763e3", "whale_63M_24Kroi"),
    ("0xb317d2bc2d3d2df5fa441b5bae0ab9d8b07283ae", "insider_whale_192M"),
    ("0x2ea18c23f72a4b6172c55b411823cdc5335923f4", "ETH_whale_282M_long"),
    ("0x020ca66c30bec2c4fe3861a94e4db4a498a35872", "MachiBigBrother"),
    ("0x8db0787b609e54cbfddf2b89b34b8c7fcc95f05c", "JamesWynn"),
    ("0x3bcae23e8c380dab4732e9a159c0456f12d866f3", "whale_2370roi"),
]

def fetch_hyperliquid():
    print("\n=== HYPERLIQUID WHALES (15 addresses) ===")
    positions = []

    for addr, name in HL_WHALES:
        body = {"type": "clearinghouseState", "user": addr}
        data = api_post("https://api.hyperliquid.xyz/info", body, f"HL {name}")
        if data and isinstance(data, dict):
            asset_positions = data.get("assetPositions", [])
            margin_summary = data.get("marginSummary", {})
            account_value = margin_summary.get("accountValue", "0")

            pos_count = 0
            for ap in asset_positions:
                pos = ap.get("position", {})
                coin = pos.get("coin", "")
                szi = float(pos.get("szi", "0"))
                if szi == 0:
                    continue
                entry_px = pos.get("entryPx", "0")
                unrealized_pnl = pos.get("unrealizedPnl", "0")
                leverage_val = pos.get("leverage", {})
                lev = leverage_val.get("value", "1") if isinstance(leverage_val, dict) else str(leverage_val)
                position_value = pos.get("positionValue", "0")

                positions.append({
                    "source": "Hyperliquid",
                    "trader": name,
                    "traderAddress": addr,
                    "symbol": f"{coin}-USDT" if not coin.endswith("USDT") else coin,
                    "direction": "LONG" if szi > 0 else "SHORT",
                    "size": str(abs(szi)),
                    "sizeNotional": str(position_value),
                    "entryPrice": entry_px,
                    "unrealizedPnl": str(unrealized_pnl),
                    "leverage": str(lev),
                    "accountValue": str(account_value),
                })
                pos_count += 1
            if pos_count > 0:
                try:
                    av = float(account_value)
                    print(f"    {name}: {pos_count} positions, acct=${av:,.0f}")
                except (ValueError, TypeError):
                    print(f"    {name}: {pos_count} positions")
        time.sleep(0.3)

    # HL meta for funding/OI
    meta_data = api_post("https://api.hyperliquid.xyz/info", {"type": "metaAndAssetCtxs"}, "HL meta+OI")
    hl_oi = {}
    if meta_data and isinstance(meta_data, list) and len(meta_data) >= 2:
        universe = meta_data[0].get("universe", [])
        ctxs = meta_data[1] if len(meta_data) > 1 else []
        for i, u in enumerate(universe):
            if i < len(ctxs):
                coin = u.get("name", "")
                hl_oi[coin] = {
                    "openInterest": ctxs[i].get("openInterest", "0"),
                    "funding": ctxs[i].get("funding", "0"),
                    "markPrice": ctxs[i].get("markPx", "0"),
                }

    print(f"  Total: {len(positions)} Hyperliquid whale positions")
    return positions, hl_oi


# ============================================================
# 3. BINANCE L/S RATIOS (3+ mirror failover per project rules)
# ============================================================
def fetch_binance_ls_ratios():
    print("\n=== BINANCE LONG/SHORT RATIOS ===")
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
               "BNBUSDT", "AVAXUSDT", "LINKUSDT", "ADAUSDT", "SUIUSDT"]
    ratios = {}
    mirrors = ["https://fapi.binance.com", "https://fapi1.binance.com",
               "https://fapi2.binance.com", "https://fapi3.binance.com"]

    for sym in symbols:
        got = False
        for mirror in mirrors:
            url = f"{mirror}/futures/data/globalLongShortAccountRatio?symbol={sym}&period=4h&limit=1"
            data = api_get(url, f"Binance L/S {sym}")
            if data and isinstance(data, list) and len(data) > 0:
                e = data[0]
                ratios[sym] = {
                    "source": "Binance",
                    "longShortRatio": e.get("longShortRatio", "0"),
                    "longAccount": e.get("longAccount", "0"),
                    "shortAccount": e.get("shortAccount", "0"),
                    "timestamp": e.get("timestamp", 0),
                }
                got = True
                break
            time.sleep(0.15)
        if not got:
            # Bybit fallback
            burl = f"https://api.bybit.com/v5/market/account-ratio?category=linear&symbol={sym}&period=4h&limit=1"
            bdata = api_get(burl, f"Bybit L/S fallback {sym}")
            if bdata and bdata.get("retCode") == 0 and bdata.get("result", {}).get("list"):
                e = bdata["result"]["list"][0]
                buy = float(e.get("buyRatio", "0.5"))
                sell = max(float(e.get("sellRatio", "0.5")), 0.001)
                ratios[sym] = {
                    "source": "Bybit", "longShortRatio": f"{buy/sell:.4f}",
                    "longAccount": e.get("buyRatio", "0"), "shortAccount": e.get("sellRatio", "0"),
                }
                got = True
        if not got:
            ratios[sym] = {"source": "unavailable", "longShortRatio": "N/A"}
        time.sleep(0.15)

    ok = sum(1 for v in ratios.values() if v["source"] != "unavailable")
    print(f"  Got {ok}/{len(symbols)} symbols")
    return ratios


def fetch_binance_top_trader_ls():
    print("\n=== BINANCE TOP TRADER POSITION RATIOS ===")
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
    ratios = {}
    mirrors = ["https://fapi.binance.com", "https://fapi1.binance.com",
               "https://fapi2.binance.com", "https://fapi3.binance.com"]
    for sym in symbols:
        for mirror in mirrors:
            url = f"{mirror}/futures/data/topLongShortPositionRatio?symbol={sym}&period=4h&limit=1"
            data = api_get(url, f"TopTrader L/S {sym}")
            if data and isinstance(data, list) and len(data) > 0:
                e = data[0]
                ratios[sym] = {
                    "longShortRatio": e.get("longShortRatio", "0"),
                    "longAccount": e.get("longAccount", "0"),
                    "shortAccount": e.get("shortAccount", "0"),
                }
                break
            time.sleep(0.15)
        time.sleep(0.15)
    print(f"  Got {len(ratios)}/{len(symbols)} symbols")
    return ratios


# ============================================================
# 4. CONSENSUS BUILDER
# ============================================================
def normalize_symbol(sym):
    s = sym.upper().replace("-SWAP", "").replace("_UMCBL", "").replace("_DMCBL", "")
    s = s.replace("-", "").replace("_", "").replace("/", "")
    if s.endswith("PERP"):
        s = s[:-4] + "USDT"
    if not s.endswith("USDT") and not s.endswith("USD"):
        s = s + "USDT"
    return s


def build_consensus(okx_positions, hl_positions, ls_ratios, top_trader_ls, hl_oi):
    print("\n=== BUILDING CONSENSUS ===")
    symbol_votes = defaultdict(lambda: {"LONG": [], "SHORT": [], "sources": set()})

    for p in okx_positions + hl_positions:
        raw_sym = p.get("symbol", "")
        if not raw_sym:
            continue
        sym = normalize_symbol(raw_sym)
        direction = p.get("direction", "LONG")
        symbol_votes[sym][direction].append({
            "trader": p.get("trader", "unknown"),
            "source": p.get("source", "unknown"),
            "size": p.get("size", "0"),
            "sizeNotional": p.get("sizeNotional", ""),
            "pnl": p.get("pnl", p.get("unrealizedPnl", "0")),
            "leverage": p.get("leverage", "1"),
            "entryPrice": p.get("avgPrice", p.get("entryPrice", "")),
        })
        symbol_votes[sym]["sources"].add(p.get("source", ""))

    consensus_picks = []
    for sym, votes in sorted(symbol_votes.items(), key=lambda x: len(x[1]["LONG"])+len(x[1]["SHORT"]), reverse=True):
        lc = len(votes["LONG"])
        sc = len(votes["SHORT"])
        total = lc + sc
        if total == 0:
            continue
        sources = list(votes["sources"])
        dom = "LONG" if lc >= sc else "SHORT"
        agree = max(lc, sc) / total * 100

        ls = ls_ratios.get(sym, {})
        lsr = ls.get("longShortRatio", "N/A")
        crowd = "NEUTRAL"
        divergence = False
        if lsr not in ("N/A", "0"):
            try:
                r = float(lsr)
                crowd = "CROWD_LONG" if r > 1.2 else ("CROWD_SHORT" if r < 0.8 else "NEUTRAL")
                if dom == "SHORT" and crowd == "CROWD_LONG":
                    divergence = True
                elif dom == "LONG" and crowd == "CROWD_SHORT":
                    divergence = True
            except ValueError:
                pass

        ttls = top_trader_ls.get(sym, {})
        top_bias = "N/A"
        if ttls:
            try:
                ttr = float(ttls.get("longShortRatio", "1"))
                top_bias = "TOP_LONG" if ttr > 1.1 else ("TOP_SHORT" if ttr < 0.9 else "TOP_NEUTRAL")
            except ValueError:
                pass

        coin = sym.replace("USDT", "").replace("USD", "")
        hli = hl_oi.get(coin, {})

        total_notional = 0
        for dl in [votes["LONG"], votes["SHORT"]]:
            for d in dl:
                try:
                    total_notional += float(d.get("sizeNotional", "0") or "0")
                except (ValueError, TypeError):
                    pass

        consensus_picks.append({
            "symbol": sym, "dominantDirection": dom,
            "longTraders": lc, "shortTraders": sc, "totalTraders": total,
            "agreementPct": round(agree, 1), "totalNotionalUSD": round(total_notional, 2),
            "sources": sources, "multiSourceAgreement": len(sources) > 1,
            "crowdBias": crowd, "binanceLSRatio": lsr, "topTraderBias": top_bias,
            "smartMoneyCrowdDivergence": divergence,
            "hyperliquidFunding": hli.get("funding", "N/A"),
            "hyperliquidOI": hli.get("openInterest", "N/A"),
            "longDetails": votes["LONG"], "shortDetails": votes["SHORT"],
        })

    consensus_picks.sort(key=lambda x: (
        -int(x["multiSourceAgreement"]), -int(x["smartMoneyCrowdDivergence"]),
        -x["totalTraders"], -x["totalNotionalUSD"],
    ))
    return consensus_picks, [p for p in consensus_picks if p["smartMoneyCrowdDivergence"]]


def main():
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"COPY TRADER INTELLIGENCE - {ts}")
    print("=" * 70)

    okx_traders, okx_pos = fetch_okx_traders()
    hl_pos, hl_oi = fetch_hyperliquid()
    ls_ratios = fetch_binance_ls_ratios()
    top_ls = fetch_binance_top_trader_ls()

    consensus, divergences = build_consensus(okx_pos, hl_pos, ls_ratios, top_ls, hl_oi)

    all_pos = okx_pos + hl_pos
    total_traders = len(set(p.get("trader", "") for p in all_pos))

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat() + "Z",
        "summary": {
            "totalTradersScanned": total_traders,
            "totalOpenPositions": len(all_pos),
            "uniqueSymbols": len(consensus),
            "multiSourceConsensus": sum(1 for p in consensus if p["multiSourceAgreement"]),
            "divergenceSignals": len(divergences),
            "dataSources": {
                "OKX": {"traders": len(okx_traders), "positions": len(okx_pos)},
                "Hyperliquid": {"whales": len(HL_WHALES), "positions": len(hl_pos)},
                "BinanceLSRatios": ls_ratios,
                "BinanceTopTraderLS": top_ls,
            },
        },
        "consensusPicks": consensus[:40],
        "divergenceAlerts": divergences,
        "topConvictionPicks": [p for p in consensus if p["totalTraders"] >= 2][:10],
        "rawPositions": {"OKX": okx_pos, "Hyperliquid": hl_pos},
        "traderProfiles": {"OKX": okx_traders},
    }

    print("\n" + "=" * 70)
    print("CONSENSUS REPORT SUMMARY")
    print("=" * 70)
    print(f"Traders scanned: {total_traders}")
    print(f"Open positions:  {len(all_pos)}")
    print(f"Unique symbols:  {len(consensus)}")
    print(f"Multi-source:    {report['summary']['multiSourceConsensus']}")
    print(f"Divergences:     {len(divergences)}")

    if consensus:
        print(f"\nTOP CONSENSUS PICKS:")
        for i, p in enumerate(consensus[:20], 1):
            d = " ** DIVERGENCE **" if p["smartMoneyCrowdDivergence"] else ""
            m = " [MULTI-SRC]" if p["multiSourceAgreement"] else ""
            n = f" ${p['totalNotionalUSD']:,.0f}" if p['totalNotionalUSD'] > 0 else ""
            print(f"  {i:2}. {p['symbol']:14s} {p['dominantDirection']:5s} "
                  f"({p['longTraders']}L/{p['shortTraders']}S) "
                  f"agree={p['agreementPct']:.0f}% "
                  f"crowd={p['crowdBias']:12s} topTr={p['topTraderBias']:11s} "
                  f"src={','.join(p['sources'])}{n}{m}{d}")

    if divergences:
        print(f"\n{'!'*50}")
        print("DIVERGENCE ALERTS (Smart Money vs Crowd):")
        for dv in divergences:
            print(f"  ! {dv['symbol']}: SmartMoney={dv['dominantDirection']}, "
                  f"Crowd={dv['crowdBias']}, L/S={dv['binanceLSRatio']}")

    print(f"\nBINANCE L/S RATIOS (4h):")
    for sym, ls in ls_ratios.items():
        r = ls.get("longShortRatio", "N/A")
        lp = ls.get("longAccount", "?")
        sp = ls.get("shortAccount", "?")
        ttr = top_ls.get(sym, {}).get("longShortRatio", "N/A")
        print(f"  {sym:14s}: crowd={r:>7s} (L={lp} S={sp})  topTrader={ttr:>7s}  [{ls.get('source','?')}]")

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "live_intelligence_report.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str, ensure_ascii=False)
    print(f"\nReport saved: {out_path}")
    return report

if __name__ == "__main__":
    main()
