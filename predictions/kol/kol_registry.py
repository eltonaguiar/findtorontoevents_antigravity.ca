"""
Unified KOL (Key Opinion Leader) Registry
==========================================
Central registry for all tracked analysts across crypto, equity, forex,
and macro asset classes. Replaces hardcoded lists in twitter_scraper.py
and analyst_scraper.py.

Usage:
    from predictions.kol.kol_registry import (
        get_active_kols,
        get_kols_by_platform,
        get_kol_handles_for_twitter,
        get_analysts_dict,
    )
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Category labels (human-readable)
# ---------------------------------------------------------------------------

CATEGORY_LABELS = {
    "on_chain": "On-Chain",
    "macro": "Macro",
    "ta_daily": "TA Daily",
    "narrative": "Narrative",
    "meme": "Meme",
    "quant": "Quant",
    "equity": "Equity",
    "forex": "Forex",
}

# ---------------------------------------------------------------------------
# Trust tiers (ascending confidence)
# ---------------------------------------------------------------------------

TRUST_TIERS = ["UNRANKED", "WATCH", "MIXED", "PROVEN", "ELITE"]

# ---------------------------------------------------------------------------
# Helper to build a KOL entry with sensible defaults
# ---------------------------------------------------------------------------

def _kol(
    handle: str,
    display_name: str,
    category: str,
    *,
    asset_classes: list[str] | None = None,
    platforms: list[str] | None = None,
    specialty_symbols: list[str] | None = None,
    youtube_channel_id: str | None = None,
    telegram_channel: str | None = None,
    substack_url: str | None = None,
    rss_url: str | None = None,
    tradingview_handle: str | None = None,
    trust_tier: str = "UNRANKED",
    initial_weight: float = 1.0,
    active: bool = True,
) -> dict:
    return {
        "handle": handle,
        "display_name": display_name,
        "category": category,
        "asset_classes": asset_classes or ["crypto"],
        "platforms": platforms or ["twitter"],
        "specialty_symbols": specialty_symbols or [],
        "youtube_channel_id": youtube_channel_id,
        "telegram_channel": telegram_channel,
        "substack_url": substack_url,
        "rss_url": rss_url,
        "tradingview_handle": tradingview_handle,
        "trust_tier": trust_tier,
        "initial_weight": initial_weight,
        "active": active,
    }


# ===================================================================
#  KOL REGISTRY
# ===================================================================

KOL_REGISTRY: list[dict] = [

    # ---------------------------------------------------------------
    #  ON-CHAIN  (Tier A - existing, trust_tier="WATCH")
    # ---------------------------------------------------------------
    _kol(
        "woonomic", "Willy Woo", "on_chain",
        platforms=["twitter", "substack"],
        substack_url="https://willywoo.substack.com",
        trust_tier="WATCH",
    ),
    _kol(
        "ki_young_ju", "Ki Young Ju", "on_chain",
        trust_tier="WATCH",
    ),
    _kol(
        "WClementeIII", "Will Clemente", "on_chain",
        trust_tier="WATCH",
    ),
    _kol(
        "100trillionUSD", "Plan B", "on_chain",
        trust_tier="WATCH",
    ),
    _kol(
        "intocryptoverse", "Benjamin Cowen", "on_chain",
        platforms=["youtube", "twitter"],
        tradingview_handle="intocryptoverse",
        youtube_channel_id="UCRvqjQPSeaWn-uEx-w0XOIg",
        trust_tier="WATCH",
    ),
    _kol(
        "DylanLeClair_", "Dylan LeClair", "on_chain",
        trust_tier="WATCH",
    ),

    # ---------------------------------------------------------------
    #  MACRO  (Tier A - existing, trust_tier="WATCH")
    # ---------------------------------------------------------------
    _kol(
        "RaoulGMI", "Raoul Pal", "macro",
        trust_tier="WATCH",
    ),
    _kol(
        "CryptoHayes", "Arthur Hayes", "macro",
        platforms=["twitter", "substack"],
        substack_url="https://cryptohayes.substack.com",
        trust_tier="WATCH",
    ),
    _kol(
        "krugermacro", "Alex Kruger", "macro",
        trust_tier="WATCH",
    ),

    # ---------------------------------------------------------------
    #  TA DAILY  (Tier A - existing, trust_tier="WATCH")
    # ---------------------------------------------------------------
    _kol(
        "CryptoMichNL", "Michael van de Poppe", "ta_daily",
        tradingview_handle="CryptoMichNL",
        trust_tier="WATCH",
    ),
    _kol(
        "CryptoDonAlt", "DonAlt", "ta_daily",
        tradingview_handle="CryptoDonAlt",
        trust_tier="WATCH",
    ),
    _kol(
        "CredibleCrypto", "Credible Crypto", "ta_daily",
        tradingview_handle="CredibleCrypto",
        trust_tier="WATCH",
    ),
    _kol(
        "davthewave", "Dave the Wave", "ta_daily",
        tradingview_handle="davthewave",
        trust_tier="WATCH",
    ),
    _kol(
        "HsakaTrades", "Hsaka", "ta_daily",
        trust_tier="WATCH",
    ),
    _kol(
        "Pentosh1", "Pentoshi", "ta_daily",
        trust_tier="WATCH",
    ),
    _kol(
        "Josh_Rager", "Josh Rager", "ta_daily",
        trust_tier="WATCH",
    ),
    _kol(
        "scottmelker", "Scott Melker", "ta_daily",
        tradingview_handle="scottmelker",
        trust_tier="WATCH",
    ),

    # ---------------------------------------------------------------
    #  NARRATIVE  (Tier A - existing, trust_tier="WATCH")
    # ---------------------------------------------------------------
    _kol(
        "milesdeutscher", "Miles Deutscher", "narrative",
        trust_tier="WATCH",
    ),
    _kol(
        "coinbureau", "Coin Bureau", "narrative",
        platforms=["youtube"],
        youtube_channel_id="UCqK_GSMbpiV8spgD3ZGloSw",
        trust_tier="WATCH",
    ),
    _kol(
        "TheCryptoLark", "Lark Davis", "narrative",
        platforms=["youtube"],
        youtube_channel_id="UCl2oCaw8hdR_kbqyqd2klIA",
        trust_tier="WATCH",
    ),

    # ---------------------------------------------------------------
    #  NARRATIVE  (Tier B - new, trust_tier="UNRANKED")
    # ---------------------------------------------------------------
    _kol(
        "AltcoinDailyio", "Altcoin Daily", "narrative",
        platforms=["youtube"],
        youtube_channel_id="UCbLhGKVY-bJPcawebgtNfbw",
    ),
    _kol(
        "EllioTrades", "EllioTrades", "narrative",
        platforms=["twitter", "youtube"],
    ),
    _kol(
        "cryptomanran", "Ran Neuner", "narrative",
        platforms=["twitter", "youtube"],
    ),

    # ---------------------------------------------------------------
    #  TA DAILY  (Tier B - new, trust_tier="UNRANKED")
    # ---------------------------------------------------------------
    _kol(
        "CryptoBanter", "Crypto Banter", "ta_daily",
        platforms=["youtube"],
        youtube_channel_id="UCN9Nj4tjXbVTLYWN0EKly_Q",
    ),
    _kol(
        "ColdBloodShill", "Cold Blood Shill", "ta_daily",
    ),
    _kol(
        "blaboratory", "SmartContracter", "ta_daily",
    ),
    _kol(
        "trader1sz", "Trader1SZ", "ta_daily",
    ),
    _kol(
        "CryptoKaleo", "Kaleo", "ta_daily",
    ),
    _kol(
        "ZssBecker", "Zss Becker", "ta_daily",
    ),
    _kol(
        "CryptoCred", "CryptoCred", "ta_daily",
    ),
    _kol(
        "tabortrader", "TabTrader", "ta_daily",
    ),

    # ---------------------------------------------------------------
    #  MACRO  (Tier B - new, trust_tier="UNRANKED")
    # ---------------------------------------------------------------
    _kol(
        "MacroScope17", "MacroScope", "macro",
    ),

    # ---------------------------------------------------------------
    #  MEME  (Tier B - new, trust_tier="UNRANKED")
    # ---------------------------------------------------------------
    _kol(
        "inversebrah", "inversebrah", "meme",
    ),
    _kol(
        "DegenSpartan", "Degen Spartan", "meme",
    ),

    # ---------------------------------------------------------------
    #  QUANT  (Tier B - new, trust_tier="UNRANKED")
    # ---------------------------------------------------------------
    _kol(
        "GCRClassic", "GCR", "quant",
    ),
    _kol(
        "looloukl", "LouKerner", "quant",
    ),

    # ---------------------------------------------------------------
    #  ON-CHAIN  (Tier B - new, trust_tier="UNRANKED")
    # ---------------------------------------------------------------
    _kol(
        "glaboratory", "glassnode", "on_chain",
        platforms=["twitter", "substack"],
    ),
    _kol(
        "naborrator", "Nansen", "on_chain",
    ),
    _kol(
        "santaborerger", "Santiment", "on_chain",
    ),
    _kol(
        "whale_alert", "Whale Alert", "on_chain",
    ),
    _kol(
        "APompliano", "Anthony Pompliano", "macro",
        platforms=["twitter", "youtube"],
    ),
    _kol(
        "CryptoCapo_", "Capo of Crypto", "ta_daily",
    ),

    # ---------------------------------------------------------------
    #  EQUITY / ETF  (trust_tier="UNRANKED")
    # ---------------------------------------------------------------
    _kol(
        "WarrenBuffett", "Warren Buffett", "equity",
        asset_classes=["equity", "etf"],
        specialty_symbols=["BRK.B"],
    ),
    _kol(
        "jimcramer", "Jim Cramer", "equity",
        asset_classes=["equity", "etf"],
        specialty_symbols=["SPY", "QQQ", "AAPL", "NVDA"],
    ),
    _kol(
        "unusual_whales", "Unusual Whales", "equity",
        asset_classes=["equity", "etf"],
        specialty_symbols=["SPY", "QQQ"],
    ),
    _kol(
        "chaaborsi", "Chamath", "equity",
        asset_classes=["equity", "etf"],
        specialty_symbols=["SPY", "SOFI"],
    ),
    _kol(
        "elerianm", "Mohamed El-Erian", "macro",
        asset_classes=["macro", "equity"],
    ),
    _kol(
        "LizAnnSonders", "Liz Ann Sonders", "equity",
        asset_classes=["equity", "etf"],
    ),

    # ---------------------------------------------------------------
    #  FOREX / FUTURES  (trust_tier="UNRANKED")
    # ---------------------------------------------------------------
    _kol(
        "ForexLive", "ForexLive", "forex",
        asset_classes=["forex", "futures"],
    ),
    _kol(
        "FXstreetNews", "FXstreet", "forex",
        asset_classes=["forex"],
    ),
    _kol(
        "JoelKruger", "Joel Kruger", "forex",
        asset_classes=["forex"],
        specialty_symbols=["EURUSD", "GBPUSD"],
    ),
]


# ===================================================================
#  LOOKUP HELPERS
# ===================================================================

def get_active_kols() -> list[dict]:
    """Return all active KOLs."""
    return [k for k in KOL_REGISTRY if k["active"]]


def get_kols_by_platform(platform: str) -> list[dict]:
    """Return active KOLs present on the given platform."""
    return [
        k for k in KOL_REGISTRY
        if k["active"] and platform in k["platforms"]
    ]


def get_kols_by_category(category: str) -> list[dict]:
    """Return active KOLs in the given category."""
    return [
        k for k in KOL_REGISTRY
        if k["active"] and k["category"] == category
    ]


def get_kols_by_asset_class(asset_class: str) -> list[dict]:
    """Return active KOLs covering the given asset class."""
    return [
        k for k in KOL_REGISTRY
        if k["active"] and asset_class in k["asset_classes"]
    ]


def get_kol_by_handle(handle: str) -> dict | None:
    """Return a KOL by handle, or None."""
    for k in KOL_REGISTRY:
        if k["handle"] == handle:
            return k
    return None


def get_kol_handles_for_twitter() -> list[str]:
    """Return list of Twitter handles for backward compat with twitter_scraper.py."""
    return [
        k["handle"] for k in KOL_REGISTRY
        if k["active"] and "twitter" in k["platforms"]
    ]


def get_analysts_dict() -> dict:
    """Return dict keyed by handle matching the old analyst_scraper.py ANALYSTS format.

    Each value has: display_name, category, platform (first platform),
    tradingview_handle, specialty (derived from category label).
    """
    result = {}
    for k in KOL_REGISTRY:
        if not k["active"]:
            continue
        result[k["handle"]] = {
            "display_name": k["display_name"],
            "category": k["category"],
            "platform": k["platforms"][0] if k["platforms"] else "twitter",
            "tradingview_handle": k["tradingview_handle"],
            "specialty": CATEGORY_LABELS.get(k["category"], k["category"]),
        }
    return result


# ===================================================================
#  MODULE SELF-TEST
# ===================================================================

if __name__ == "__main__":
    active = get_active_kols()
    print(f"Total KOLs: {len(KOL_REGISTRY)}")
    print(f"Active KOLs: {len(active)}")
    print()

    # Counts by category
    for cat, label in CATEGORY_LABELS.items():
        count = len(get_kols_by_category(cat))
        if count:
            print(f"  {label:12s}: {count}")

    # Counts by platform
    print()
    for plat in ["twitter", "youtube", "substack", "telegram"]:
        count = len(get_kols_by_platform(plat))
        if count:
            print(f"  {plat:12s}: {count}")

    # Backward compat check
    print(f"\nTwitter handles: {len(get_kol_handles_for_twitter())}")
    print(f"Analysts dict entries: {len(get_analysts_dict())}")
