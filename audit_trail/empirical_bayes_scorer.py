"""
Empirical Bayes win-probability from closed trades (Beta–Binomial shrinkage).

Aligned with Downloads/empirical_bayes_scorer.py — hierarchical shrinkage and Wilson bands.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


def _pnl_win(t: dict) -> bool | None:
    pnl = t.get("pnl_pct")
    if pnl is not None:
        try:
            return float(pnl) > 0
        except (TypeError, ValueError):
            pass
    w = t.get("won")
    if isinstance(w, bool):
        return w
    if w is not None:
        return str(w).lower() in ("1", "true", "yes", "win")
    return None


def _strategy_name(t: dict) -> str:
    """Match dashboard `strategy` and forward-test `algorithm` fields."""
    s = t.get("strategy")
    if s is not None and str(s).strip():
        return str(s).strip()
    a = t.get("algorithm")
    if a is not None and str(a).strip():
        return str(a).strip()
    return "unknown"


def _calc_wr(trades: list[dict]) -> float:
    if not trades:
        return 0.44
    wins = 0
    n = 0
    for t in trades:
        ww = _pnl_win(t)
        if ww is None:
            continue
        n += 1
        if ww:
            wins += 1
    return wins / n if n > 0 else 0.44


def _mean_pnl(trades: list[dict]) -> float | None:
    values: list[float] = []
    for t in trades:
        pnl = t.get("pnl_pct")
        if pnl is None:
            pnl = t.get("pnl")
        if pnl is None:
            continue
        try:
            values.append(float(pnl))
        except (TypeError, ValueError):
            continue
    if not values:
        return None
    return sum(values) / len(values)


class EmpiricalBayesScorer:
    PRIOR_STRENGTH = 20.0
    NET_LOSER_SCORE_CAP = 59.9

    def __init__(self, closed_trades: list[dict]):
        self.trades = [t for t in closed_trades if isinstance(t, dict)]
        self.global_wr = _calc_wr(self.trades)

        self._by_strategy: dict[str, list[dict]] = defaultdict(list)
        self._by_strat_sym: dict[str, list[dict]] = defaultdict(list)
        self._by_strat_sym_dir: dict[str, list[dict]] = defaultdict(list)
        self._by_strat_dir: dict[str, list[dict]] = defaultdict(list)
        self._by_asset_dir: dict[str, list[dict]] = defaultdict(list)

        for t in self.trades:
            strat = _strategy_name(t)
            sym = str(t.get("symbol") or "unknown").upper()
            direction = str(t.get("direction") or "LONG").upper()
            asset = str(t.get("asset_class") or "CRYPTO").upper()

            self._by_strategy[strat].append(t)
            self._by_strat_sym["%s|%s" % (strat, sym)].append(t)
            self._by_strat_sym_dir["%s|%s|%s" % (strat, sym, direction)].append(t)
            self._by_strat_dir["%s|%s" % (strat, direction)].append(t)
            self._by_asset_dir["%s|%s" % (asset, direction)].append(t)

    def _shrink(self, observed_wr: float, n: int, prior_wr: float) -> float:
        ps = self.PRIOR_STRENGTH
        return (n * observed_wr + ps * prior_wr) / (n + ps) if (n + ps) > 0 else prior_wr

    def win_prob(
        self,
        symbol: str,
        strategy: str,
        direction: str = "LONG",
        asset_class: str = "CRYPTO",
    ) -> dict[str, Any]:
        sym = str(symbol or "").upper()
        strat = str(strategy or "")
        direction = str(direction or "LONG").upper()
        asset_class = str(asset_class or "CRYPTO").upper()

        key_ssd = "%s|%s|%s" % (strat, sym, direction)
        ssd_trades = self._by_strat_sym_dir.get(key_ssd, [])
        n_ssd = len(ssd_trades)
        ssd_wr = _calc_wr(ssd_trades) if n_ssd > 0 else None

        key_ss = "%s|%s" % (strat, sym)
        ss_trades = self._by_strat_sym.get(key_ss, [])
        n_ss = len(ss_trades)
        ss_wr = _calc_wr(ss_trades) if n_ss > 0 else None

        key_sd = "%s|%s" % (strat, direction)
        sd_trades = self._by_strat_dir.get(key_sd, [])
        n_sd = len(sd_trades)
        sd_wr = _calc_wr(sd_trades) if n_sd > 0 else None

        strat_trades = self._by_strategy.get(strat, [])
        n_strat = len(strat_trades)
        strat_wr = _calc_wr(strat_trades) if n_strat > 0 else None

        key_ad = "%s|%s" % (asset_class, direction)
        ad_trades = self._by_asset_dir.get(key_ad, [])
        n_ad = len(ad_trades)
        ad_wr = _calc_wr(ad_trades) if n_ad > 0 else None

        if n_ssd >= 5 and ssd_wr is not None:
            prior_ss = ss_wr if ss_wr is not None else (strat_wr if strat_wr is not None else self.global_wr)
            prob_ssd = self._shrink(ssd_wr, n_ssd, prior_ss)
            prob_ss = (
                self._shrink(ss_wr, n_ss, strat_wr if strat_wr is not None else self.global_wr)
                if ss_wr is not None and n_ss > 0
                else None
            )
            prob_strat = (
                self._shrink(strat_wr, n_strat, self.global_wr)
                if strat_wr is not None and n_strat > 0
                else self.global_wr
            )
            final = 0.5 * prob_ssd + 0.3 * (prob_ss or prob_strat) + 0.2 * prob_strat
            n_used = n_ssd
            tier = "SYMBOL_STRATEGY_DIRECTION"
        elif n_ss >= 5 and ss_wr is not None:
            prob_ss = self._shrink(ss_wr, n_ss, strat_wr if strat_wr is not None else self.global_wr)
            prob_strat = (
                self._shrink(strat_wr, n_strat, self.global_wr)
                if strat_wr is not None and n_strat > 0
                else self.global_wr
            )
            final = 0.5 * prob_ss + 0.3 * prob_strat + 0.2 * self.global_wr
            n_used = n_ss
            tier = "SYMBOL_STRATEGY"
        elif n_sd >= 5 and sd_wr is not None:
            prob_sd = self._shrink(sd_wr, n_sd, strat_wr if strat_wr is not None else self.global_wr)
            prob_strat = (
                self._shrink(strat_wr, n_strat, self.global_wr)
                if strat_wr is not None and n_strat > 0
                else self.global_wr
            )
            final = 0.5 * prob_sd + 0.3 * prob_strat + 0.2 * self.global_wr
            n_used = n_sd
            tier = "STRATEGY_DIRECTION"
        elif n_strat >= 5 and strat_wr is not None:
            final = self._shrink(strat_wr, n_strat, self.global_wr)
            n_used = n_strat
            tier = "STRATEGY"
        elif n_ad >= 5 and ad_wr is not None:
            final = self._shrink(ad_wr, n_ad, self.global_wr)
            n_used = n_ad
            tier = "ASSET_DIRECTION"
        else:
            final = self.global_wr
            n_used = max(n_ssd, n_ss, n_sd, n_strat, n_ad, 0)
            tier = "GLOBAL_PRIOR"

        if n_used > 0:
            z = 1.96
            denom = 1 + z**2 / n_used
            center = (final + z**2 / (2 * n_used)) / denom
            spread = z * math.sqrt((final * (1 - final) + z**2 / (4 * n_used)) / n_used) / denom
            ci_low = max(0.0, center - spread)
            ci_high = min(1.0, center + spread)
        else:
            ci_low = max(0.0, final - 0.15)
            ci_high = min(1.0, final + 0.15)

        return {
            "win_prob": round(final, 4),
            "n_trades": n_used,
            "tier": tier,
            "ci_95_low": round(ci_low, 4),
            "ci_95_high": round(ci_high, 4),
            "confidence_band": round(ci_high - ci_low, 4),
            "shrinkage_applied": n_used < 20,
            "global_prior": round(self.global_wr, 4),
        }

    def score_pick(self, pick: dict[str, Any]) -> dict[str, Any]:
        result = self.win_prob(
            symbol=str(pick.get("symbol") or ""),
            strategy=str(pick.get("strategy") or pick.get("algorithm") or ""),
            direction=str(pick.get("direction") or "LONG"),
            asset_class=str(pick.get("asset_class") or "CRYPTO"),
        )

        original_score = float(pick.get("score") or 50.0)
        baseline = self.global_wr if self.global_wr > 0 else 0.44
        enhanced_score = min(100.0, original_score * (result["win_prob"] / baseline))

        strat = str(pick.get("strategy") or pick.get("algorithm") or "")
        strat_trades = self._by_strategy.get(strat, [])
        mean_pnl = _mean_pnl(strat_trades)
        is_net_loser = mean_pnl is not None and mean_pnl < 0 and len(strat_trades) >= 10
        if is_net_loser:
            enhanced_score = min(enhanced_score, self.NET_LOSER_SCORE_CAP)

        enriched = dict(pick)
        enriched["eb_win_prob"] = result["win_prob"]
        enriched["eb_tier"] = result["tier"]
        enriched["eb_n_trades"] = result["n_trades"]
        enriched["eb_ci_band"] = result["confidence_band"]
        enriched["eb_shrunk"] = result["shrinkage_applied"]
        enriched["eb_mean_pnl"] = round(mean_pnl, 4) if mean_pnl is not None else None
        enriched["eb_net_loser_cap_applied"] = is_net_loser
        enriched["enhanced_score"] = round(enhanced_score, 1)
        enriched["eb_kill_flag"] = result["win_prob"] < 0.35 and result["n_trades"] >= 10
        return enriched
