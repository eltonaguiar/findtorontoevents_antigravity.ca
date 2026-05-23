import asyncio
import json
import logging
import os
import sys
from typing import Dict, List, Tuple, Optional, Any

try:
    import pymysql
    _HAS_PYMYSQL = True
except Exception:
    pymysql = None  # type: ignore
    _HAS_PYMYSQL = False

from alpha_engine.betway_scraper import BetwayScraper
from alpha_engine.proline_scraper import ProlineScraper
from alpha_engine.sports_prediction_market_sync import fetch_polymarket_sports_signals
from alpha_engine.sports_situational_edge import SituationalEdgeEngine

try:
    from alpha_engine.polymarket_signals import get_true_probability
except ImportError:
    def get_true_probability(event_name: str) -> float:
        return 0.55

logger = logging.getLogger(__name__)

DB_DEFAULTS = {
    "host": os.environ.get("SPORTS_DB_HOST", "mysql.50webs.com"),
    "user": os.environ.get("SPORTS_DB_USER", "ejaguiar1_sportsbet"),
    "password": os.environ.get("SPORTS_DB_PASSWORD", "eltonsportsbets"),
    "database": os.environ.get("SPORTS_DB_NAME", "ejaguiar1_sportsbet"),
    "port": int(os.environ.get("SPORTS_DB_PORT", "3306")),
}


class SportsEdgeFinder:
    """
    Cross-references traditional sportsbooks (Betway, Proline+) against prediction
    markets (Polymarket) and situational models to find +EV bets and arbitrage.
    """
    def __init__(self):
        self.betway = BetwayScraper()
        self.proline = ProlineScraper()
        self.situational = SituationalEdgeEngine()
        self._pm_signals: List[Dict[str, Any]] = []

    def american_to_implied(self, odds: int) -> float:
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)

    def decimal_to_implied(self, decimal: float) -> float:
        return 1.0 / decimal

    def calculate_ev(self, true_prob: float, offered_odds_decimal: float) -> float:
        """Decimal-odds EV: (p * (d-1)) - (1-p)"""
        return (true_prob * (offered_odds_decimal - 1.0)) - (1.0 - true_prob)

    def _db_conn(self) -> Optional[Any]:
        if not _HAS_PYMYSQL:
            return None
        try:
            return pymysql.connect(
                host=DB_DEFAULTS["host"],
                user=DB_DEFAULTS["user"],
                password=DB_DEFAULTS["password"],
                database=DB_DEFAULTS["database"],
                port=DB_DEFAULTS["port"],
                connect_timeout=10,
                read_timeout=15,
                cursorclass=pymysql.cursors.DictCursor,
            )
        except Exception as e:
            logger.error(f"DB connect failed: {e}")
            return None

    def _fetch_odds_from_db(self, sport_like: str = "basketball_nba", hours: int = 48) -> List[Dict[str, Any]]:
        conn = self._db_conn()
        if not conn:
            return []
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT sport, event_id, home_team, away_team, commence_time, "
                    "bookmaker, bookmaker_key, market, outcome_name, outcome_price "
                    "FROM lm_sports_odds "
                    "WHERE sport LIKE %s AND commence_time >= NOW() "
                    "AND commence_time <= DATE_ADD(NOW(), INTERVAL %s HOUR) "
                    "AND outcome_price > 1.01 AND outcome_price < 80.0 "
                    "ORDER BY event_id, market, outcome_name, outcome_price DESC",
                    (f"%{sport_like}%", hours),
                )
                return list(cur.fetchall())
        finally:
            conn.close()

    def _load_pm_signals(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        if self._pm_signals and not force_refresh:
            return self._pm_signals
        self._pm_signals = fetch_polymarket_sports_signals(limit=500)
        return self._pm_signals

    def _match_pm_prob(self, home_team: str, away_team: str) -> Optional[float]:
        """Fuzzy-match a PM signal to the game and return the confidence (probability)."""
        signals = self._load_pm_signals()
        home_norm = home_team.lower().strip()
        away_norm = away_team.lower().strip()
        best: Optional[Dict[str, Any]] = None
        best_score = -1.0
        for s in signals:
            q = (s.get("question") or "").lower()
            et = (s.get("event_title") or "").lower()
            score = 0.0
            if home_norm in q or home_norm in et:
                score += 1.0
            if away_norm in q or away_norm in et:
                score += 1.0
            if score < 1.0:
                continue
            # Tie-break by volume
            score += (s.get("volume_usd", 0) or 0) / 1_000_000.0
            if score > best_score:
                best_score = score
                best = s
        if best:
            return float(best.get("confidence", 0))
        return None

    def scan_for_edges(self, sport: str = "basketball_nba", min_ev: float = 0.03) -> List[Dict[str, Any]]:
        """
        Synchronously scan DB odds + PM signals + situational model for +EV edges.
        Returns list of edge dicts.
        """
        logger.info(f"Scanning {sport} for +EV edges (min_ev={min_ev})...")
        edges: List[Dict[str, Any]] = []

        rows = self._fetch_odds_from_db(sport, hours=48)
        if not rows:
            logger.warning("No odds rows from DB; edges empty.")
            return edges

        # Group by event+market+outcome, keep best price per book
        buckets: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for r in rows:
            bk = f"{r['event_id']}\x1f{r['market']}"
            ok = r["outcome_name"]
            buckets.setdefault(bk, {}).setdefault(ok, []).append(r)

        for bk, outcomes in buckets.items():
            eid, market = bk.split("\x1f", 1)
            if len(outcomes) < 2:
                continue
            # Get teams from first row
            first_row = next(iter(outcomes.values()))[0]
            home_team = first_row["home_team"]
            away_team = first_row["away_team"]
            commence_time = first_row["commence_time"]

            # Try to get true probability from PM
            pm_prob = self._match_pm_prob(home_team, away_team)

            # 2026-04-27 (sports-C3): pre-compute Jensen-normalized devig
            # ACROSS all outcomes of this event before per-outcome iteration.
            # The previous implementation took mean(1/price) per outcome
            # *without* normalizing — that returns the bookmaker's vig-loaded
            # implied probability, so EV trends to -vig and "+EV" picks were
            # dispersion noise. Mirror sports_value_truep_consensus_jensen()
            # in live-monitor/api/sports_value_analyze_lib.php.
            # See docs/CODE_REVIEW_2026_04_27.md (sports-C3).
            _oc_invs: Dict[str, float] = {}
            for _ok, _quotes in outcomes.items():
                if not _quotes:
                    continue
                _ok_invs = [1.0 / float(q["outcome_price"]) for q in _quotes]
                if _ok_invs:
                    _oc_invs[_ok] = sum(_ok_invs) / len(_ok_invs)
            _devig_sum = sum(_oc_invs.values())

            # 2026-04-27 (sports-C2): situational adjustments are gated behind
            # SPORTS_SITUATIONAL_ADJUSTMENT=1. With default kwargs (no rest
            # days, no b2b flags, no weather), every adjust_*_prob returns 0,
            # so the +6.5% NBA-rest / +3% NFL-key edges advertised in PR #400
            # were always inert. Disabled until upstream feeds are wired.
            _situational_enabled = (
                os.environ.get("SPORTS_SITUATIONAL_ADJUSTMENT") == "1"
            )

            for ok, quotes in outcomes.items():
                if not quotes:
                    continue
                best = max(quotes, key=lambda x: float(x["outcome_price"]))
                price = float(best["outcome_price"])
                bk_key = best["bookmaker_key"]

                # Determine base true probability
                if pm_prob is not None:
                    # If this outcome is the away team, flip probability
                    true_prob = pm_prob if ok.lower() == home_team.lower() else (1.0 - pm_prob)
                elif _devig_sum > 0 and ok in _oc_invs:
                    # Jensen-normalized devig across all outcomes (sports-C3).
                    true_prob = _oc_invs[ok] / _devig_sum
                else:
                    true_prob = 0.5

                # Situational adjustment (sport-specific) — gated, sports-C2
                if _situational_enabled:
                    if "basketball" in sport:
                        adj = self.situational.adjust_nba_prob(true_prob)
                        true_prob = adj["adjusted_prob"]
                    elif "icehockey" in sport:
                        adj = self.situational.adjust_nhl_prob(true_prob)
                        true_prob = adj["adjusted_prob"]
                    elif "baseball" in sport:
                        adj = self.situational.adjust_mlb_prob(true_prob)
                        true_prob = adj["adjusted_prob"]
                    elif "americanfootball" in sport:
                        adj = self.situational.adjust_nfl_prob(true_prob)
                        true_prob = adj["adjusted_prob"]

                ev = self.calculate_ev(true_prob, price)
                if ev > min_ev:
                    edges.append({
                        "type": "+EV",
                        "sportsbook": best["bookmaker"],
                        "sportsbook_key": bk_key,
                        "event": f"{away_team} @ {home_team}",
                        "event_id": eid,
                        "market": market,
                        "outcome": ok,
                        "offered_odds_decimal": round(price, 3),
                        "implied_prob": round(self.decimal_to_implied(price), 4),
                        "true_probability": round(true_prob, 4),
                        "expected_value": round(ev * 100, 2),
                        "action": "Place Bet",
                        "commence_time": str(commence_time),
                        "pm_matched": pm_prob is not None,
                    })

        edges.sort(key=lambda x: x["expected_value"], reverse=True)
        logger.info(f"Found {len(edges)} +EV edges for {sport}")
        return edges


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    finder = SportsEdgeFinder()
    # Example: scan NBA
    edges = finder.scan_for_edges("basketball_nba", min_ev=0.03)
    print(json.dumps(edges, indent=2))
