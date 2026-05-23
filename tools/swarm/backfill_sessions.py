"""Backfill 2026-05-11 + 2026-05-12 paper-trade sessions into swarm_picks.json.

Sources of truth (committed to main):
- TV_SWARM_SESSION_2026-05-11_2330EST.MD (round 1 — 22 picks)
- TV_PICKS_WHY_2026-05-11_2229EST.MD (round 1 — per-trade justifications)
- TV_SWARM_SESSION_2026-05-12_1553EST.MD (round 2 — 16 picks)

Round 1 universe was voted by 10 named personas (MOMENTUM_TECH, MACRO_BEAR,
MEAN_REVERSION, FUND_VALUE, NEWS_FLOW, ONCHAIN_QUANT, VOL_TRADER, BREAKOUT,
PAIRS_CORR, SEASONAL) all backed by underlying_model="claude-opus-4-7" (this
session's main model).

Round 2 + V4 value picks used a smaller refresh swarm + dedicated value
screener — each represented as a single composite vote here since per-persona
breakdown wasn't preserved in the .MD.

Run: `python tools/swarm/backfill_sessions.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.swarm.swarm_pick_schema import (
    atomic_write_store, derive_consensus_tier, load_store, new_pick_id,
)

STORE_PATH = REPO_ROOT / "audit_dashboard" / "data" / "swarm_picks.json"

OPUS_47 = "claude-opus-4-7"

PERSONA_ROLES = {
    "MOMENTUM_TECH": "trend-following",
    "MACRO_BEAR": "macro-skeptic",
    "MEAN_REVERSION": "contrarian",
    "FUND_VALUE": "value-investor",
    "NEWS_FLOW": "catalyst-driven",
    "ONCHAIN_QUANT": "on-chain-analyst",
    "VOL_TRADER": "implied-vol",
    "BREAKOUT": "purist-breakout",
    "PAIRS_CORR": "relative-value",
    "SEASONAL": "calendar-flow",
}


def make_vote(persona: str, vote: str, conf: int, tf: str, just: str,
              underlying_model: str = OPUS_47) -> dict:
    return {
        "name": persona,
        "role": PERSONA_ROLES.get(persona, "generalist"),
        "underlying_model": underlying_model,
        "vote": vote,
        "confidence_0_100": conf,
        "timeframe": tf,
        "justification_summary": just,
    }


def make_pick(*, pick_id: str | None = None, created_at: str, session_id: str,
              account: str, symbol: str, direction: str, entry: float, tp: float,
              sl: float, qty: float, qty_unit: str, timeframe: str, asset_class: str,
              votes: list[dict], btc_regime: str = "RANGE", vol_regime: str = "MID") -> dict:
    agreed = sum(1 for v in votes if v["vote"] == direction)
    voted = sum(1 for v in votes if v["vote"] != "SKIP")
    score = agreed / voted if voted else 0.0
    return {
        "pick_id": pick_id or new_pick_id(),
        "created_at": created_at,
        "session_id": session_id,
        "account": account,
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "tp": tp,
        "sl": sl,
        "qty": qty,
        "qty_unit": qty_unit,
        "timeframe": timeframe,
        "asset_class": asset_class,
        "consensus_tier": derive_consensus_tier(score, voted),
        "models_consulted": votes,
        "models_agreed": agreed,
        "models_voted": voted,
        "consensus_score": round(score, 4),
        "regime_at_entry": {
            "btc_regime": btc_regime,
            "vol_regime": vol_regime,
            "source": "TV_SWARM_SESSION_*.MD (manual snapshot)",
        },
        "outcome": None,
        "pattern_tags": [],
    }


def round1_picks() -> list[dict]:
    """Round 1 — 2026-05-11 session.

    Three accounts: zerounderscore (4), Leap Crypto (3), theswarm (15).
    Plus V4 was SKIPPED (recorded separately in skipped_candidates list).

    Vote breakdown reconstructed from the 10-persona aggregation table in
    TV_SWARM_SESSION_2026-05-11_2330EST.MD section "Swarm Consensus Analysis".
    """
    s_zero = "tv_session_2026-05-11_2230est_zerounderscore"
    s_leap = "tv_session_2026-05-11_2230est_leap"
    s_swarm = "tv_session_2026-05-11_2230est_theswarm"

    # zerounderscore — single-strategy curator-style picks (not full 10-persona vote)
    zero_picks = [
        make_pick(created_at="2026-05-11T22:00:00-05:00", session_id=s_zero,
                  account="zerounderscore", symbol="BINANCE:ONDOUSDT",
                  direction="LONG", entry=0.4357, tp=0.4693, sl=0.4171,
                  qty=8000, qty_unit="asset_units", timeframe="4H",
                  asset_class="CRYPTO",
                  votes=[make_vote("trio_bot", "LONG", 78, "4H",
                                   "Sweet-spot conf 0.78, RWA rotation, trio_bot elite=100")]),
        make_pick(created_at="2026-05-11T22:01:00-05:00", session_id=s_zero,
                  account="zerounderscore", symbol="BINANCE:APTUSDT",
                  direction="LONG", entry=1.112, tp=1.199, sl=1.066,
                  qty=3300, qty_unit="asset_units", timeframe="4H",
                  asset_class="CRYPTO",
                  votes=[make_vote("ml_strategy_reviver", "LONG", 75, "1D",
                                   "APT basing in 1.05-1.15 range, declining sell volume")]),
        make_pick(created_at="2026-05-11T22:02:00-05:00", session_id=s_zero,
                  account="zerounderscore", symbol="BINANCE:ARBUSDT",
                  direction="LONG", entry=0.1394, tp=0.1502, sl=0.1335,
                  qty=26000, qty_unit="asset_units", timeframe="1D",
                  asset_class="CRYPTO",
                  votes=[make_vote("ml_strategy_reviver", "LONG", 75, "1D",
                                   "L2 rotation, near absolute lows, best R:R 2.50")]),
        make_pick(created_at="2026-05-11T22:03:00-05:00", session_id=s_zero,
                  account="zerounderscore", symbol="BINANCE:ADAUSDT",
                  direction="SHORT", entry=0.2785, tp=0.2560, sl=0.2894,
                  qty=13000, qty_unit="asset_units", timeframe="1D",
                  asset_class="CRYPTO",
                  votes=[make_vote("ml_strategy_reviver_inverse", "SHORT", 75, "1D",
                                   "Inverse signal of losing LONG, balances LONG-heavy book")]),
    ]

    # Leap Crypto — swarm-vetted slate (per TV_PICKS_WHY .MD)
    leap_picks = [
        make_pick(created_at="2026-05-11T22:30:00-05:00", session_id=s_leap,
                  account="The Leap Crypto", symbol="COINBASE:BTCUSDC.P",
                  direction="SHORT", entry=81189.8, tp=76800.0, sl=83900.0,
                  qty=0.05, qty_unit="asset_units", timeframe="1D",
                  asset_class="CRYPTO", btc_regime="TOPPING",
                  votes=[
                      make_vote("LEAP_SWARM_AGG", "SHORT", 70, "1D",
                                "BTC failed at 84k twice, distribution at range high, LONG-bias in topping = 25% WR per memory"),
                  ]),
        make_pick(created_at="2026-05-11T22:32:00-05:00", session_id=s_leap,
                  account="The Leap Crypto", symbol="COINBASE:ETHUSDC.P",
                  direction="SHORT", entry=2313.25, tp=2092.0, sl=2428.0,
                  qty=1.3, qty_unit="asset_units", timeframe="1D",
                  asset_class="CRYPTO", btc_regime="TOPPING",
                  votes=[
                      make_vote("LEAP_SWARM_AGG", "SHORT", 60, "1D",
                                "ETH/BTC ratio bleeding, correlated confirm to BTC short"),
                  ]),
        make_pick(created_at="2026-05-11T22:34:00-05:00", session_id=s_leap,
                  account="The Leap Crypto", symbol="COINBASE:DOGEUSDC.P",
                  direction="LONG", entry=0.11069, tp=0.12056, sl=0.10453,
                  qty=18000, qty_unit="asset_units", timeframe="1D",
                  asset_class="CRYPTO", btc_regime="TOPPING",
                  votes=[
                      make_vote("LEAP_SWARM_AGG", "LONG", 55, "1D",
                                "Alt-beta diversifier vs 2 BTC/ETH shorts, retail risk-on bounce candidate"),
                  ]),
    ]

    # theswarm round-1 — 15 picks from 10-persona swarm. Reconstruct per-persona votes
    # from TV_SWARM_SESSION_2026-05-11_2330EST.MD §"Swarm Consensus Analysis".
    swarm_picks = [
        # LINK 5/5 LONG — unanimous tier (anchor)
        make_pick(created_at="2026-05-11T23:18:00-05:00", session_id=s_swarm,
                  account="theswarm", symbol="BINANCE:LINKUSDT",
                  direction="LONG", entry=10.52, tp=11.56, sl=9.98,
                  qty=475, qty_unit="asset_units", timeframe="4H",
                  asset_class="CRYPTO",
                  votes=[
                      make_vote("MOMENTUM_TECH", "LONG", 78, "4H", "Breaking 200d EMA on rising vol"),
                      make_vote("MACRO_BEAR", "LONG", 55, "1D", "Even bears agree base intact"),
                      make_vote("MEAN_REVERSION", "LONG", 70, "4H", "Bounce off lower BB on 4H"),
                      make_vote("FUND_VALUE", "LONG", 65, "1D", "Oracle TVL recovering"),
                      make_vote("ONCHAIN_QUANT", "LONG", 72, "4H", "Stake-flow positive, smart-money tag"),
                  ]),
        # DOGE 4/4 SHORT - strong
        make_pick(created_at="2026-05-11T23:20:00-05:00", session_id=s_swarm,
                  account="theswarm", symbol="BINANCE:DOGEUSDT",
                  direction="SHORT", entry=0.11041, tp=0.10157, sl=0.11593,
                  qty=27000, qty_unit="asset_units", timeframe="1D",
                  asset_class="CRYPTO",
                  votes=[
                      make_vote("MOMENTUM_TECH", "SHORT", 65, "4H", "Lower-highs intact"),
                      make_vote("FUND_VALUE", "SHORT", 60, "1D", "No fundamentals to support"),
                      make_vote("VOL_TRADER", "SHORT", 58, "1D", "IV expensive vs realized"),
                      make_vote("BREAKOUT", "SHORT", 62, "4H", "Failed lower-low retest"),
                  ]),
        # ADA 4/5 SHORT - strong
        make_pick(created_at="2026-05-11T23:22:00-05:00", session_id=s_swarm,
                  account="theswarm", symbol="BINANCE:ADAUSDT",
                  direction="SHORT", entry=0.2782, tp=0.2560, sl=0.2921,
                  qty=11000, qty_unit="asset_units", timeframe="1D",
                  asset_class="CRYPTO",
                  votes=[
                      make_vote("MOMENTUM_TECH", "SHORT", 60, "1D", "Persistent downtrend"),
                      make_vote("MACRO_BEAR", "SHORT", 65, "1D", "Risk-off proxy"),
                      make_vote("ONCHAIN_QUANT", "SHORT", 55, "1D", "Net outflow week"),
                      make_vote("FUND_VALUE", "LONG", 50, "1M", "Oversold, dividend-like staking"),
                      make_vote("SEASONAL", "SHORT", 50, "1W", "May weakness"),
                  ]),
        # ETH 4L/4S tied = control
        make_pick(created_at="2026-05-11T23:24:00-05:00", session_id=s_swarm,
                  account="theswarm", symbol="BINANCE:ETHUSDT",
                  direction="LONG", entry=2313.60, tp=2451.0, sl=2244.0,
                  qty=0.86, qty_unit="asset_units", timeframe="1D",
                  asset_class="CRYPTO",
                  votes=[
                      make_vote("FUND_VALUE", "LONG", 65, "1M", "EIP-1559 burn + staking yield"),
                      make_vote("ONCHAIN_QUANT", "LONG", 68, "4H", "6yr low exchange supply"),
                      make_vote("MEAN_REVERSION", "LONG", 60, "1D", "Overshoot to downside"),
                      make_vote("NEWS_FLOW", "LONG", 60, "1W", "SEC softening, ETF optionality"),
                      make_vote("MOMENTUM_TECH", "SHORT", 55, "4H", "Below key MAs"),
                      make_vote("MACRO_BEAR", "SHORT", 60, "1D", "Higher beta to BTC"),
                      make_vote("VOL_TRADER", "SHORT", 70, "1D", "IV rich vs RV"),
                      make_vote("SEASONAL", "SHORT", 65, "1M", "May avg -3.4% historically"),
                  ]),
        # BTC 2L/3S control (placed LONG control-test)
        make_pick(created_at="2026-05-11T23:26:00-05:00", session_id=s_swarm,
                  account="theswarm", symbol="BINANCE:BTCUSDT",
                  direction="LONG", entry=80880.70, tp=84000.0, sl=78500.0,
                  qty=0.015, qty_unit="asset_units", timeframe="1D",
                  asset_class="CRYPTO", btc_regime="TOPPING",
                  votes=[
                      make_vote("ONCHAIN_QUANT", "LONG", 72, "4H", "Exchange supply multi-year low"),
                      make_vote("NEWS_FLOW", "LONG", 55, "1W", "SEC softening tailwind"),
                      make_vote("MOMENTUM_TECH", "SHORT", 60, "4H", "Triple rejection at 84k"),
                      make_vote("VOL_TRADER", "SHORT", 65, "1D", "IV rich post-100k pin"),
                      make_vote("SEASONAL", "SHORT", 65, "1M", "Post-halving Y1 May drawdown pattern"),
                  ]),
        # BNB single LONG
        make_pick(created_at="2026-05-11T23:28:00-05:00", session_id=s_swarm,
                  account="theswarm", symbol="BINANCE:BNBUSDT",
                  direction="LONG", entry=662.46, tp=695.60, sl=642.60,
                  qty=1.5, qty_unit="asset_units", timeframe="1D",
                  asset_class="CRYPTO",
                  votes=[
                      make_vote("FUND_VALUE", "LONG", 50, "1M", "Quarterly burn = de facto buyback"),
                  ]),
        # TLT 6/7 LONG unanimous
        make_pick(created_at="2026-05-11T23:30:00-05:00", session_id=s_swarm,
                  account="theswarm", symbol="NASDAQ:TLT",
                  direction="LONG", entry=85.40, tp=90.69, sl=82.99,
                  qty=58, qty_unit="asset_units", timeframe="1M",
                  asset_class="ETF",
                  votes=[
                      make_vote("MACRO_BEAR", "LONG", 74, "3M", "ISM<50 precedes Fed pivot"),
                      make_vote("FUND_VALUE", "LONG", 55, "1M", "Long-duration yield + carry"),
                      make_vote("ONCHAIN_QUANT", "LONG", 50, "1D", "Stablecoin mcap expansion"),
                      make_vote("VOL_TRADER", "LONG", 62, "1W", "MOVE elevated, IV>RV"),
                      make_vote("SEASONAL", "LONG", 72, "1M", "Bonds bid May-Jun rotation"),
                      make_vote("MEAN_REVERSION", "LONG", 60, "1D", "Oversold yield-spike candidate"),
                      make_vote("NEWS_FLOW", "SHORT", 55, "1D", "Hawkish hold + debt-ceiling supply"),
                  ]),
        # GLD 6/8 LONG unanimous
        make_pick(created_at="2026-05-11T23:32:00-05:00", session_id=s_swarm,
                  account="theswarm", symbol="AMEX:GLD",
                  direction="LONG", entry=433.50, tp=460.80, sl=421.60,
                  qty=12, qty_unit="asset_units", timeframe="1M",
                  asset_class="ETF",
                  votes=[
                      make_vote("MOMENTUM_TECH", "LONG", 74, "1W", "Multi-month uptrend intact"),
                      make_vote("MACRO_BEAR", "LONG", 78, "3M", "Stagflation = gold's best regime"),
                      make_vote("NEWS_FLOW", "LONG", 80, "1W", "Debt-ceiling + Mideast tension"),
                      make_vote("BREAKOUT", "LONG", 70, "1W", "Pressing ATHs, clean breakout"),
                      make_vote("PAIRS_CORR", "LONG", 68, "1M", "Gold/silver ratio wide, strong leg"),
                      make_vote("SEASONAL", "LONG", 86, "1M", "May-Aug strongest seasonal"),
                      make_vote("MEAN_REVERSION", "SHORT", 70, "1D", "RSI hot, upper BB tag"),
                      make_vote("VOL_TRADER", "SHORT", 76, "1D", "GVZ elevated, IV>>RV"),
                  ]),
        # USO single LONG control
        make_pick(created_at="2026-05-11T23:34:00-05:00", session_id=s_swarm,
                  account="theswarm", symbol="AMEX:USO",
                  direction="LONG", entry=138.50, tp=144.50, sl=136.20,
                  qty=7, qty_unit="asset_units", timeframe="1W",
                  asset_class="ETF",
                  votes=[
                      make_vote("NEWS_FLOW", "LONG", 50, "1D", "Mideast tension floor, China stimulus"),
                  ]),
        # NVDA 5/6 SHORT strong
        make_pick(created_at="2026-05-11T23:36:00-05:00", session_id=s_swarm,
                  account="theswarm", symbol="NASDAQ:NVDA",
                  direction="SHORT", entry=219.50, tp=201.90, sl=228.20,
                  qty=18, qty_unit="asset_units", timeframe="1W",
                  asset_class="EQUITY",
                  votes=[
                      make_vote("MOMENTUM_TECH", "LONG", 78, "1D", "Bull flag near ATH"),
                      make_vote("MACRO_BEAR", "SHORT", 72, "1M", "Cap-ex cycle peaking"),
                      make_vote("MEAN_REVERSION", "SHORT", 60, "1H", "Parabolic z-score elevated"),
                      make_vote("NEWS_FLOW", "SHORT", 70, "1W", "AI capex cooling"),
                      make_vote("VOL_TRADER", "SHORT", 80, "1D", "IV rich, dealer long gamma"),
                      make_vote("BREAKOUT", "SHORT", 60, "4H", "Broke down from prior range"),
                  ]),
        # TSLA 5/6 SHORT strong
        make_pick(created_at="2026-05-11T23:38:00-05:00", session_id=s_swarm,
                  account="theswarm", symbol="NASDAQ:TSLA",
                  direction="SHORT", entry=445.50, tp=409.50, sl=462.90,
                  qty=9, qty_unit="asset_units", timeframe="1W",
                  asset_class="EQUITY",
                  votes=[
                      make_vote("MOMENTUM_TECH", "SHORT", 65, "4H", "Failed breakout, 50DMA rolling"),
                      make_vote("MACRO_BEAR", "SHORT", 75, "1M", "Consumer credit + auto cycle"),
                      make_vote("FUND_VALUE", "SHORT", 55, "1M", "60x multiple unjustified"),
                      make_vote("MEAN_REVERSION", "LONG", 60, "4H", "Hammered into support"),
                      make_vote("VOL_TRADER", "SHORT", 75, "1D", "IV always rich, dealer pin"),
                      make_vote("SEASONAL", "SHORT", 58, "1M", "Auto Q2-Q3 weak"),
                  ]),
        # AMZN 3/3 LONG moderate
        make_pick(created_at="2026-05-11T23:40:00-05:00", session_id=s_swarm,
                  account="theswarm", symbol="NASDAQ:AMZN",
                  direction="LONG", entry=268.50, tp=285.10, sl=260.90,
                  qty=11, qty_unit="asset_units", timeframe="1M",
                  asset_class="EQUITY",
                  votes=[
                      make_vote("MOMENTUM_TECH", "LONG", 62, "1D", "Trending above rising MAs"),
                      make_vote("FUND_VALUE", "LONG", 50, "1M", "AWS margin expansion, SoP undervalued"),
                      make_vote("VOL_TRADER", "LONG", 68, "1W", "Post-ER vol crush done"),
                  ]),
        # USDJPY single LONG (carry)
        make_pick(created_at="2026-05-11T23:42:00-05:00", session_id=s_swarm,
                  account="theswarm", symbol="FX:USDJPY",
                  direction="LONG", entry=157.60, tp=158.60, sl=156.93,
                  qty=10000, qty_unit="asset_units", timeframe="1D",
                  asset_class="FOREX",
                  votes=[
                      make_vote("FOREX_RESEARCH_SWARM", "LONG", 70, "1D",
                                "2y rate diff +4.8%, EMA20 hold, swap +8 pips/night"),
                  ]),
        # MCL micro crude single LONG
        make_pick(created_at="2026-05-11T23:44:00-05:00", session_id=s_swarm,
                  account="theswarm", symbol="NYMEX:MCL1!",
                  direction="LONG", entry=99.02, tp=101.84, sl=96.89,
                  qty=1, qty_unit="contracts", timeframe="1W",
                  asset_class="FUTURES",
                  votes=[
                      make_vote("FUTURES_RESEARCH_SWARM", "LONG", 55, "1W",
                                "Micro WTI, Mideast tension floor, China stimulus marginal bid"),
                  ]),
    ]
    return zero_picks + leap_picks + swarm_picks


def round2_picks() -> list[dict]:
    """Round 2 — 2026-05-12 session: theswarm refresh (10) + V4 value (6)."""
    s_refresh = "tv_session_2026-05-12_1553est_theswarm_refresh"
    s_v4 = "tv_session_2026-05-12_1553est_v4_value"

    refresh = [
        make_pick(created_at="2026-05-12T15:30:00-05:00", session_id=s_refresh,
                  account="theswarm", symbol="BINANCE:DOTUSDT",
                  direction="SHORT", entry=1.337, tp=1.230, sl=1.404,
                  qty=1500, qty_unit="asset_units", timeframe="4H",
                  asset_class="CRYPTO",
                  votes=[
                      make_vote("MACRO_BEAR", "SHORT", 65, "1D", "Lagging L1, no narrative"),
                      make_vote("MOMENTUM_TECH", "SHORT", 60, "4H", "Lower-highs on 1D"),
                      make_vote("FUND_VALUE", "SHORT", 50, "1M", "Weak tokenomics vs peers"),
                  ]),
        make_pick(created_at="2026-05-12T15:32:00-05:00", session_id=s_refresh,
                  account="theswarm", symbol="BINANCE:INJUSDT",
                  direction="LONG", entry=4.724, tp=5.102, sl=4.535,
                  qty=530, qty_unit="asset_units", timeframe="4H",
                  asset_class="CRYPTO",
                  votes=[
                      make_vote("MOMENTUM_TECH", "LONG", 68, "4H", "Cleanest uptrend in alt L1s"),
                      make_vote("VOL_TRADER", "LONG", 60, "1W", "Vol regime favorable"),
                      make_vote("NEWS_FLOW", "LONG", 60, "1W", "RWA narrative live"),
                  ]),
        make_pick(created_at="2026-05-12T15:34:00-05:00", session_id=s_refresh,
                  account="theswarm", symbol="BINANCE:TIAUSDT",
                  direction="SHORT", entry=0.4587, tp=0.4130, sl=0.4820,
                  qty=3300, qty_unit="asset_units", timeframe="1D",
                  asset_class="CRYPTO",
                  votes=[
                      make_vote("MACRO_BEAR", "SHORT", 58, "1D", "Unlock overhang"),
                      make_vote("MOMENTUM_TECH", "SHORT", 55, "1D", "Faded from $4.40, modular-DA cooling"),
                  ]),
        make_pick(created_at="2026-05-12T15:36:00-05:00", session_id=s_refresh,
                  account="theswarm", symbol="BINANCE:POLUSDT",
                  direction="SHORT", entry=0.0987, tp=0.0888, sl=0.1036,
                  qty=15000, qty_unit="asset_units", timeframe="1D",
                  asset_class="CRYPTO",
                  votes=[
                      make_vote("MOMENTUM_TECH", "SHORT", 55, "1D", "POL rebrand didn't stick"),
                      make_vote("ONCHAIN_QUANT", "SHORT", 50, "1D", "Ghost-WR history, structural fade"),
                  ]),
        make_pick(created_at="2026-05-12T15:38:00-05:00", session_id=s_refresh,
                  account="theswarm", symbol="BINANCE:RUNEUSDT",
                  direction="LONG", entry=0.588, tp=0.634, sl=0.558,
                  qty=2500, qty_unit="asset_units", timeframe="4H",
                  asset_class="CRYPTO",
                  votes=[
                      make_vote("MOMENTUM_TECH", "LONG", 55, "4H", "Thorchain volume recovery"),
                  ]),
        make_pick(created_at="2026-05-12T15:40:00-05:00", session_id=s_refresh,
                  account="theswarm", symbol="NASDAQ:CRWD",
                  direction="LONG", entry=546.50, tp=601.00, sl=519.00,
                  qty=4, qty_unit="asset_units", timeframe="1W",
                  asset_class="EQUITY",
                  votes=[
                      make_vote("MOMENTUM_TECH", "LONG", 70, "1W", "Cyber tailwind post-breach cycle"),
                      make_vote("NEWS_FLOW", "LONG", 65, "1W", "ER beat momentum"),
                  ]),
        make_pick(created_at="2026-05-12T15:42:00-05:00", session_id=s_refresh,
                  account="theswarm", symbol="NYSE:BAC",
                  direction="LONG", entry=50.85, tp=55.88, sl=48.26,
                  qty=30, qty_unit="asset_units", timeframe="1W",
                  asset_class="EQUITY",
                  votes=[
                      make_vote("FUND_VALUE", "LONG", 70, "1M", "Value bank, P/B reasonable"),
                      make_vote("MACRO_BEAR", "LONG", 55, "1M", "Steepening curve helps NIM"),
                  ]),
        make_pick(created_at="2026-05-12T15:44:00-05:00", session_id=s_refresh,
                  account="theswarm", symbol="NASDAQ:PLTR",
                  direction="SHORT", entry=136.10, tp=122.40, sl=142.80,
                  qty=11, qty_unit="asset_units", timeframe="1D",
                  asset_class="EQUITY",
                  votes=[
                      make_vote("MACRO_BEAR", "SHORT", 65, "1D", "Parabolic, retail-driven"),
                      make_vote("MEAN_REVERSION", "SHORT", 60, "1D", "Gov-AI hype priced in"),
                  ]),
        make_pick(created_at="2026-05-12T15:46:00-05:00", session_id=s_refresh,
                  account="theswarm", symbol="FX:AUDJPY",
                  direction="LONG", entry=114.117, tp=115.83, sl=112.97,
                  qty=10000, qty_unit="asset_units", timeframe="1D",
                  asset_class="FOREX",
                  votes=[
                      make_vote("FOREX_RESEARCH_SWARM", "LONG", 70, "1D",
                                "RBA hawkish, BoJ glacial, cleanest carry pair"),
                  ]),
        make_pick(created_at="2026-05-12T15:48:00-05:00", session_id=s_refresh,
                  account="theswarm", symbol="FX:USDCAD",
                  direction="LONG", entry=1.37000, tp=1.3905, sl=1.3604,
                  qty=5000, qty_unit="asset_units", timeframe="1D",
                  asset_class="FOREX",
                  votes=[
                      make_vote("MACRO_BEAR", "LONG", 55, "1D", "CAD soft on oil + BoC dovish"),
                  ]),
        make_pick(created_at="2026-05-12T15:50:00-05:00", session_id=s_refresh,
                  account="theswarm", symbol="CME_MINI:MES1!",
                  direction="SHORT", entry=7419.75, tp=7271.0, sl=7494.0,
                  qty=1, qty_unit="contracts", timeframe="4H",
                  asset_class="FUTURES",
                  votes=[
                      make_vote("MACRO_BEAR", "SHORT", 60, "4H", "VIX 16 cheap insurance, ISM<50 overlay"),
                  ]),
    ]

    # V4 value-stock picks — single dedicated value-screener swarm
    def v4_vote(ticker_thesis: str, conf: int) -> list[dict]:
        return [make_vote("V4_VALUE_SCREENER_SWARM", "LONG", conf, "6M", ticker_thesis,
                          underlying_model=OPUS_47)]

    v4 = [
        make_pick(created_at="2026-05-12T15:52:00-05:00", session_id=s_v4,
                  account="HIGHFWWRABV55_SCOREABOVE50_V4", symbol="NYSE:F",
                  direction="LONG", entry=12.05, tp=13.85, sl=11.10,
                  qty=10, qty_unit="asset_units", timeframe="3M",
                  asset_class="EQUITY",
                  votes=v4_vote("Ford P/E 9.94, 4.87% div, Q1 EPS +260% beat, EY 10%", 70)),
        make_pick(created_at="2026-05-12T15:54:00-05:00", session_id=s_v4,
                  account="HIGHFWWRABV55_SCOREABOVE50_V4", symbol="NYSE:VZ",
                  direction="LONG", entry=48.20, tp=54.50, sl=44.80,
                  qty=2, qty_unit="asset_units", timeframe="6M",
                  asset_class="EQUITY",
                  votes=v4_vote("Verizon P/E 9.84, 6.15% div, $19B FCF, 0.45 beta defensive", 75)),
        make_pick(created_at="2026-05-12T15:56:00-05:00", session_id=s_v4,
                  account="HIGHFWWRABV55_SCOREABOVE50_V4", symbol="NYSE:PFE",
                  direction="LONG", entry=25.80, tp=29.50, sl=23.80,
                  qty=5, qty_unit="asset_units", timeframe="6M",
                  asset_class="EQUITY",
                  votes=v4_vote("Pfizer 6.7% div, Q1 beat, oncology pipeline (Seagen)", 65)),
        make_pick(created_at="2026-05-12T15:58:00-05:00", session_id=s_v4,
                  account="HIGHFWWRABV55_SCOREABOVE50_V4", symbol="NYSE:USB",
                  direction="LONG", entry=55.60, tp=63.00, sl=51.20,
                  qty=2, qty_unit="asset_units", timeframe="6M",
                  asset_class="EQUITY",
                  votes=v4_vote("US Bancorp P/E 11.64, P/B 1.31, 3.71% div, Q1 beat", 65)),
        make_pick(created_at="2026-05-12T16:00:00-05:00", session_id=s_v4,
                  account="HIGHFWWRABV55_SCOREABOVE50_V4", symbol="NYSE:UNM",
                  direction="LONG", entry=79.50, tp=91.00, sl=74.00,
                  qty=1, qty_unit="asset_units", timeframe="6M",
                  asset_class="EQUITY",
                  votes=v4_vote("Unum P/E 9.77, P/B 1.18, record Q1 EPS, counter-cyclical", 70)),
        make_pick(created_at="2026-05-12T16:02:00-05:00", session_id=s_v4,
                  account="HIGHFWWRABV55_SCOREABOVE50_V4", symbol="NYSE:KMI",
                  direction="LONG", entry=32.30, tp=36.50, sl=29.90,
                  qty=4, qty_unit="asset_units", timeframe="6M",
                  asset_class="EQUITY",
                  votes=v4_vote("Kinder Morgan 3.7% div, $1.65B FCF, LNG export tailwind", 60)),
    ]
    return refresh + v4


def main() -> None:
    existing = load_store(STORE_PATH)
    if existing:
        print(f"swarm_picks.json already has {len(existing)} picks — refusing to overwrite. "
              f"Delete file first if backfill should re-run.")
        return
    all_picks = round1_picks() + round2_picks()
    atomic_write_store(STORE_PATH, all_picks)
    print(f"Backfilled {len(all_picks)} picks to {STORE_PATH}")


if __name__ == "__main__":
    main()
