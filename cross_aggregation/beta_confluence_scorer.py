"""
Beta Confluence Scorer — experimental multi-factor scoring (2026-03-16)
Scores every pick on 5 pillars (0-100 total) alongside the production score.
"""
import os
import json
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

_MARKET_CONTEXT_CACHE = {"data": None, "ts": 0}
_CACHE_TTL = 300


class BetaConfluenceScorer:
    WEIGHTS = {"technical": 25, "onchain": 20, "sentiment": 15, "risk_reward": 20, "structure": 20}

    def score_pick(self, pick: Dict[str, Any], market_context: Dict[str, Any],
                   system_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        breakdown = {
            "technical": self._score_technical(pick, market_context),
            "onchain": self._score_onchain(pick, market_context),
            "sentiment": self._score_sentiment(pick, market_context),
            "risk_reward": self._score_risk_reward(pick),
            "structure": self._score_structure(pick, market_context, system_data),
        }
        for key in breakdown:
            breakdown[key] = round(min(breakdown[key], self.WEIGHTS[key]), 1)
        total = round(sum(breakdown.values()), 1)
        return {"total": total, "breakdown": breakdown, "qualified": total >= 70}

    def _score_technical(self, pick: Dict, ctx: Dict) -> float:
        score = 0.0
        conf = pick.get("confidence", 0.5)
        direction = pick.get("direction", "LONG")
        is_long = direction in ("LONG", "BUY")

        rsi = pick.get("rsi_at_entry") or pick.get("confidence_breakdown", {}).get("rsi")
        if rsi is not None:
            if is_long and rsi < 40: score += 5
            elif is_long and rsi < 50: score += 3
            elif not is_long and rsi > 60: score += 5
            elif not is_long and rsi > 50: score += 3

        vol_ratio = pick.get("volume_ratio", 1.0)
        if vol_ratio >= 2.0: score += 5
        elif vol_ratio >= 1.5: score += 3
        elif vol_ratio >= 1.0: score += 1

        score += min(5, conf * 7)

        agree = pick.get("agreement_count_raw", 1)
        if agree >= 3: score += 5
        elif agree >= 2: score += 3

        try:
            from signal_aggregator.confidence_calculator import BayesianConfidenceCalculator
            calc = BayesianConfidenceCalculator()
            bayes_conf = calc.calculate_signal_confidence({"wins": 0, "losses": 0}, [conf])
            score += min(5, min(1.0, bayes_conf) * 5)
        except Exception:
            score += min(5, conf * 5)

        return score

    def _score_onchain(self, pick: Dict, ctx: Dict) -> float:
        score = 0.0
        direction = pick.get("direction", "LONG")
        is_long = direction in ("LONG", "BUY")
        fg = ctx.get("fear_greed_index", 50)

        # Fear & Greed (0-6, was 0-7)
        if is_long:
            if fg <= 25: score += 6
            elif fg <= 40: score += 4
            else: score += 2
        else:
            if fg >= 75: score += 6
            elif fg >= 60: score += 4
            else: score += 2

        # Exchange flows (0-5, was 0-7)
        flows = ctx.get("exchange_flows_net", 0)
        if is_long and flows < -500: score += 5
        elif is_long and flows < 0: score += 3
        elif not is_long and flows > 500: score += 5
        elif not is_long and flows > 0: score += 3
        else: score += 2

        # MVRV (0-4, was 0-6)
        mvrv = ctx.get("mvrv_zscore", 0)
        if is_long and mvrv < -0.5: score += 4
        elif is_long and mvrv < 0: score += 2
        elif not is_long and mvrv > 2: score += 4
        else: score += 2

        # Order book depth (0-5)
        ob_data = ctx.get("order_book_depth", {})
        symbol = pick.get("symbol", "")
        ob = ob_data.get(symbol, {})
        if ob:
            imb = ob.get("imbalance", 0)
            if is_long and imb > 0.3: score += 5
            elif is_long and imb > 0.1: score += 3
            elif not is_long and imb < -0.3: score += 5
            elif not is_long and imb < -0.1: score += 3
            else: score += 1
        else:
            score += 2

        return score

    def _score_sentiment(self, pick: Dict, ctx: Dict) -> float:
        score = 0.0
        direction = pick.get("direction", "LONG")
        is_long = direction in ("LONG", "BUY")
        fg = ctx.get("fear_greed_index", 50)

        if is_long and fg <= 30: score += 8
        elif is_long and fg <= 45: score += 5
        elif not is_long and fg >= 70: score += 8
        elif not is_long and fg >= 55: score += 5
        else: score += 2

        galaxy = ctx.get("lunarcrush_galaxy_score")
        if galaxy is not None:
            if is_long and galaxy >= 70: score += 7
            elif is_long and galaxy >= 50: score += 4
            elif not is_long and galaxy <= 30: score += 7
            elif not is_long and galaxy <= 50: score += 4
            else: score += 2
        else:
            if (is_long and fg <= 35) or (not is_long and fg >= 65): score += 5
            else: score += 2

        return score

    def _score_risk_reward(self, pick: Dict) -> float:
        score = 0.0
        entry = pick.get("entry") or pick.get("entry_price", 0)
        tp = pick.get("tp") or pick.get("take_profit", 0)
        sl = pick.get("sl") or pick.get("stop_loss", 0)

        if not entry or not tp or not sl:
            return 10.0

        direction = pick.get("direction", "LONG")
        is_long = direction in ("LONG", "BUY")

        if is_long:
            reward = tp - entry
            risk = entry - sl
        else:
            reward = entry - tp
            risk = sl - entry

        rr = reward / risk if risk > 0 else 0

        if rr >= 3: score += 8
        elif rr >= 2: score += 5
        elif rr >= 1.5: score += 3

        if is_long:
            total_dist = tp - sl
            remaining = tp - entry
        else:
            total_dist = sl - tp
            remaining = entry - tp

        room_pct = remaining / total_dist if total_dist > 0 else 0
        if room_pct >= 0.7: score += 6
        elif room_pct >= 0.5: score += 4
        elif room_pct >= 0.3: score += 2

        atr_val = pick.get("atr_at_entry", 0)
        if atr_val > 0:
            sl_distance = abs(entry - sl)
            atr_ratio = sl_distance / atr_val
            if atr_ratio >= 1.5: score += 6
            elif atr_ratio >= 1.0: score += 4
            elif atr_ratio >= 0.5: score += 2
        else:
            score += 3

        return score

    def _score_structure(self, pick: Dict, ctx: Dict, system_data: Optional[Dict] = None) -> float:
        score = 0.0
        direction = pick.get("direction", "LONG")
        is_long = direction in ("LONG", "BUY")
        strategy = pick.get("strategy", "")

        regime = ctx.get("regime", "UNKNOWN")
        is_momentum = any(k in strategy for k in ["momentum", "breakout", "trend", "ema", "hoffman"])
        is_mean_rev = any(k in strategy for k in ["reversion", "zscore", "pairs", "bounce", "engulfing"])

        if regime == "TRENDING" and is_momentum: score += 8
        elif regime == "RANGING" and is_mean_rev: score += 8
        elif regime in ("TRENDING", "RANGING"): score += 4
        else: score += 2

        btc_pct = ctx.get("btc_24h_pct", 0)
        symbol = pick.get("symbol", "")
        is_crypto = any(c in symbol.upper() for c in ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "DOT", "AVAX", "LINK"])

        if is_crypto:
            if is_long and btc_pct > 2: score += 6
            elif is_long and btc_pct > 0: score += 4
            elif not is_long and btc_pct < -2: score += 6
            elif not is_long and btc_pct < 0: score += 4
            else: score += 1
        else:
            score += 3

        vol_regime = ctx.get("volatility_regime", "NORMAL")
        if vol_regime == "LOW": score += 3
        elif vol_regime == "NORMAL": score += 4
        elif vol_regime == "HIGH": score += 2

        # Funding rate penalty for crypto (0 to -3 pts)
        if is_crypto:
            funding = ctx.get("btc_funding_rate", 0)
            if is_long and funding > 0.001:  # >0.1% = overleveraged longs
                score -= 3
            elif is_long and funding > 0.0005:  # >0.05%
                score -= 1
            elif not is_long and funding < -0.001:  # overleveraged shorts
                score -= 3
            elif not is_long and funding < -0.0005:
                score -= 1

        if system_data:
            trust_tiers = pick.get("system_trust_tiers", {})
            proven_count = sum(1 for t in trust_tiers.values() if isinstance(t, dict) and t.get("tier") == "PROVEN")
            if proven_count >= 2: score += 2
            elif proven_count >= 1: score += 1

        return score

    @staticmethod
    def build_market_context() -> Dict[str, Any]:
        global _MARKET_CONTEXT_CACHE
        if _MARKET_CONTEXT_CACHE["data"] and (time.time() - _MARKET_CONTEXT_CACHE["ts"]) < _CACHE_TTL:
            return _MARKET_CONTEXT_CACHE["data"]

        ctx = {
            "fear_greed_index": 50, "btc_24h_pct": 0.0, "volatility_regime": "NORMAL",
            "regime": "UNKNOWN", "exchange_flows_net": 0, "mvrv_zscore": 0,
            "lunarcrush_galaxy_score": None, "order_book_depth": {},
            "btc_funding_rate": 0,
        }

        import requests

        import time as _time
        for _att in range(3):
            try:
                r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
                if r.status_code == 200:
                    ctx["fear_greed_index"] = int(r.json()["data"][0]["value"])
                    break
            except Exception as e:
                if _att == 2:
                    logger.warning(f"F&G API failed after 3 attempts: {e}")
                else:
                    _time.sleep(2 * (_att + 1))

        for _att in range(3):
            try:
                r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                                 params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"}, timeout=5)
                if r.status_code == 200:
                    ctx["btc_24h_pct"] = r.json().get("bitcoin", {}).get("usd_24h_change", 0.0)
                    break
            except Exception as e:
                if _att == 2:
                    logger.warning(f"CoinGecko API failed after 3 attempts: {e}")
                else:
                    _time.sleep(2 * (_att + 1))

        btc_abs = abs(ctx["btc_24h_pct"])
        if btc_abs < 1: ctx["volatility_regime"] = "LOW"
        elif btc_abs < 3: ctx["volatility_regime"] = "NORMAL"
        elif btc_abs < 7: ctx["volatility_regime"] = "HIGH"
        else: ctx["volatility_regime"] = "EXTREME"

        fg = ctx["fear_greed_index"]
        btc = ctx["btc_24h_pct"]
        if btc > 1 and fg > 45: ctx["regime"] = "TRENDING"
        elif abs(btc) < 1.5 and 35 < fg < 65: ctx["regime"] = "RANGING"
        elif btc_abs > 5: ctx["regime"] = "VOLATILE"

        lc_key = os.environ.get("LUNARCRUSH_API")
        if lc_key:
            for _att in range(3):
                try:
                    r = requests.get("https://lunarcrush.com/api4/public/coins/btc/v1",
                                     headers={"Authorization": f"Bearer {lc_key}"}, timeout=5)
                    if r.status_code == 200:
                        ctx["lunarcrush_galaxy_score"] = r.json().get("data", {}).get("galaxy_score")
                        break
                except Exception as e:
                    if _att == 2:
                        logger.warning(f"LunarCrush API failed after 3 attempts: {e}")
                    else:
                        _time.sleep(2 * (_att + 1))

        try:
            from cross_aggregation.order_book_depth import get_bulk_imbalance
            ob_data = get_bulk_imbalance(["BTC-USD", "ETH-USD", "SOL-USD"])
            ctx["order_book_depth"] = ob_data
        except Exception as e:
            logger.warning(f"Order book depth failed: {e}")

        # BTC funding rate with failover (Binance fapi mirrors + Bybit)
        try:
            from alpha_engine import api_failover as _api_failover
        except ImportError:
            try:
                import api_failover as _api_failover
            except ImportError:
                _api_failover = None
        if _api_failover is not None:
            try:
                fr = _api_failover.fetch_funding_rate("BTCUSDT")
                if fr:
                    ctx["btc_funding_rate"] = fr["rate"]
            except Exception as e:
                logger.warning(f"Funding rate fetch failed: {e}")

        _MARKET_CONTEXT_CACHE["data"] = ctx
        _MARKET_CONTEXT_CACHE["ts"] = time.time()
        return ctx
