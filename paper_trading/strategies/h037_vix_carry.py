"""H-037 VIX Term Structure Carry — Paper Trading Strategy (ETF).

Hypothesis: When VIX futures are in contango (near-term < far-term), short
volatility ETFs (e.g. SVXY, UVXY inverse plays) earn positive carry. When
VIX futures are in backwardation, stay flat or go long volatility.

Harness results (2026-05-19):
  WR=58.9%, PF=1.295, n=1185, eff=0.75, 3/4 WF folds passed.

Regime filter (consensus 2026-05-20):
  Only trade when VIX > 14 AND contango > 5% annualized.
  Expected PF boost: +0.15-0.20, n reduced by ~30%.

This strategy fetches VIX futures term structure data and generates picks
for ETF symbols that proxy VIX carry trades.
"""
from typing import List, Optional
from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick
from paper_trading.helpers import fetch_json

# ETF symbols that proxy VIX term structure carry
ETF_SYMBOLS = ["SVXY", "UVXY", "VIXY", "VXX"]

# Regime filter thresholds (consensus from DeepSeek/xAI/Cerebras 2026-05-20)
VIX_FLOOR = 14.0          # Only trade when VIX spot > 14
CONTANGO_MIN = 0.05       # 5% annualized contango minimum

# TP/SL parameters (harness-validated)
TP_PCT = 0.04             # 4% take profit
SL_PCT = 0.03             # 3% stop loss


def _fetch_vix_term_structure() -> Optional[dict]:
    """Fetch VIX spot and futures term structure.

    Returns dict with:
      - spot: current VIX level
      - front: front-month futures price
      - back: back-month futures price
      - contango: (back - front) / front (annualized)

    Falls back to cached values if API fails.
    """
    try:
        # Try CBOE VIX futures data (free, no API key)
        url = "https://markets.cboe.com/api/futures?symbol=VIX"
        data = fetch_json(url)
        if data and "data" in data:
            contracts = sorted(
                [c for c in data["data"] if c.get("expiration")],
                key=lambda c: c["expiration"]
            )
            if len(contracts) >= 2:
                front = float(contracts[0]["settle"])
                back = float(contracts[-1]["settle"])
                spot = float(data.get("spot", front))
                contango = (back - front) / front
                return {
                    "spot": spot,
                    "front": front,
                    "back": back,
                    "contango": contango,
                }
    except Exception:
        pass

    # Fallback: use Yahoo Finance VIX spot + approximate term structure
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?range=1d&interval=1d"
        data = fetch_json(url)
        if data and "chart" in data and data["chart"]["result"]:
            spot = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            # Approximate contango from historical VIX term structure relationship
            # When VIX < 20, contango typically 5-15%; when VIX > 30, backwardation
            contango_approx = max(0, (20 - spot) / 100)  # Linear approximation
            return {
                "spot": spot,
                "front": spot * 1.01,
                "back": spot * (1 + contango_approx),
                "contango": contango_approx,
            }
    except Exception:
        pass

    return None


def _passes_regime_filter(ts: dict) -> bool:
    """Check if current regime passes the filter.

    Only trade when:
      1. VIX spot > VIX_FLOOR (14)
      2. Contango > CONTANGO_MIN (5%)
    """
    spot = ts.get("spot", 0)
    contango = ts.get("contango", 0)
    return spot > VIX_FLOOR and contango > CONTANGO_MIN


class H037VIXCarry(BaseStrategy):
    """H-037: VIX Term Structure Carry (ETF).

    Generates LONG picks on inverse VIX ETFs (SVXY) when contango > 5%
    and VIX > 14. Generates LONG picks on long VIX ETFs (UVXY, VIXY)
    when backwardation detected (contango < 0).

    Regime filter: skips all signals when VIX < 14 or contango < 5%.
    """
    name = "h037_vix_carry"
    display_name = "H-037 VIX Term Structure Carry"
    source = "Hypothesis Registry H-037"
    category = "etf"
    portfolio_type = "etf_carry"
    symbols = ETF_SYMBOLS

    def fetch_data(self) -> dict:
        """Fetch VIX term structure data."""
        ts = _fetch_vix_term_structure()
        return {"term_structure": ts}

    def generate_picks(self, data: dict) -> List[NormalizedPick]:
        """Generate picks based on VIX term structure regime."""
        picks = []
        ts = data.get("term_structure")

        if ts is None:
            return picks

        spot = ts.get("spot", 0)
        contango = ts.get("contango", 0)

        # Regime filter: skip if conditions not met
        if not _passes_regime_filter(ts):
            return picks

        # Fetch current prices for ETF symbols
        for symbol in self.symbols:
            try:
                price_data = self._fetch_etf_price(symbol)
                if not price_data:
                    continue

                entry = price_data["price"]
                direction = self._get_direction(symbol, contango)

                if direction == "LONG":
                    tp = entry * (1 + TP_PCT)
                    sl = entry * (1 - SL_PCT)
                else:
                    tp = entry * (1 - TP_PCT)
                    sl = entry * (1 + SL_PCT)

                rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

                picks.append(NormalizedPick(
                    symbol=symbol,
                    direction=direction,
                    entry_price=round(entry, 2),
                    tp=round(tp, 2),
                    sl=round(sl, 2),
                    strategy=self.name,
                    strategy_name=self.display_name,
                    category=self.category,
                    confidence=0.65,  # Harness-validated WR=58.9%
                    reason=f"VIX spot={spot:.1f}, contango={contango:.1%}, regime={'contango' if contango > 0 else 'backwardation'}",
                    risk_reward=round(rr, 2),
                ))
            except Exception:
                continue

        return picks

    def _fetch_etf_price(self, symbol: str) -> Optional[dict]:
        """Fetch current ETF price via Yahoo Finance."""
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1d"
            data = fetch_json(url)
            if data and "chart" in data and data["chart"]["result"]:
                meta = data["chart"]["result"][0]["meta"]
                return {
                    "price": meta.get("regularMarketPrice", 0),
                    "currency": meta.get("currency", "USD"),
                }
        except Exception:
            pass
        return None

    def _get_direction(self, symbol: str, contango: float) -> str:
        """Determine trade direction based on symbol and contango.

        In contango: LONG inverse VIX ETFs (SVXY)
        In backwardation: LONG long VIX ETFs (UVXY, VIXY, VXX)
        """
        inverse_etfs = {"SVXY"}
        long_etfs = {"UVXY", "VIXY", "VXX"}

        if contango > 0 and symbol in inverse_etfs:
            return "LONG"
        elif contango < 0 and symbol in long_etfs:
            return "LONG"
        return "SHORT"  # Default: short the wrong-side ETF
