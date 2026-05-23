"""
elimination_engine.py — KIMI Rise of the Claw v11.0
Tournament Elimination & Challenger Injection Engine

Rules (tightened post-audit — Feb 20 2026):
- Score < 40 (Danger Zone) for 3+ consecutive days → PROBATION
- Score < 30 during probation for 2+ days → ELIMINATED
- Min 20 closed picks before eligible for elimination
- Eliminated algorithms replaced by challenger pool
- Promotions: Challenger→Premier (≥55 for 5 days), Premier→Champions (≥75 for 3 days)
- Demotions: Champions→Premier (<55 for 3 days), Premier→Challenger (<40 for 3 days)
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
ELIMINATION_STATE_PATH = DATA_DIR / "elimination_state.json"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ELIMINATION_RULES = {
    "danger_zone_threshold": 40,    # Score below this = danger zone (was 25, tightened post-audit)
    "probation_threshold": 30,      # Score below this during probation = eliminated (was 20)
    "danger_zone_days": 3,          # Days in danger zone before probation (was 7)
    "probation_days": 2,            # Days in probation before elimination (was 3)
    # Raised from 5 to 20: need sufficient sample for statistical significance. Fixed 2026-03-13
    "min_picks_for_elimination": 20, # Min closed picks before eligible
    "promotion_challenger_score": 55,  # Score to move Challenger → Premier
    "promotion_challenger_days": 5,
    "promotion_premier_score": 75,  # Score to move Premier → Champions
    "promotion_premier_days": 3,
    "demotion_champions_score": 55,
    "demotion_champions_days": 3,
    "demotion_premier_score": 40,
    "demotion_premier_days": 3,
}

# ---------------------------------------------------------------------------
# Permanently Banned Strategies — F-grade (0-25% WR in forward testing)
# These skip the gradual danger-zone→probation→elimination pipeline entirely.
# Signals from these strategies are never generated.
# Added 2026-03-16 based on 15-trade forward-test results.
# ---------------------------------------------------------------------------
PERMANENTLY_BANNED_STRATEGIES = {
    "meme-scanner-live",              # 0.0% WR (2/15 trades won=0)
    "supertrend-crypto",              # 0.0% WR (1/15 trades won=0)
    "btc-dominance-reversal-scout",   # 16.7% WR (6/15 trades, 1 win)
    "stocktwits-bull-scout",          # 22.2% WR (9/15 trades, 2 wins)
}

# ---------------------------------------------------------------------------
# Forced Probation Strategies — D-grade (25-40% WR in forward testing)
# These are placed directly into probation status on engine init,
# bypassing the normal danger-zone countdown. One more bad streak = eliminated.
# Added 2026-03-16 based on 15-trade forward-test results.
# ---------------------------------------------------------------------------
FORCE_PROBATION_STRATEGIES = {
    "williams-r-scout",               # 33.3% WR (9/15 trades, 3 wins)
    "stoch-rsi-crypto",               # 37.5% WR (8/15 trades, 3 wins)
}

# ---------------------------------------------------------------------------
# 20 Challenger Reserve Algorithms
# ---------------------------------------------------------------------------

CHALLENGER_POOL = [
    {
        "id": "ichimoku-cloud-scout",
        "name": "Ichimoku Cloud Breakout",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "IchimokuCloud",
        "symbols": ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "META", "GOOGL", "BTC-USD", "ETH-USD", "SOL-USD"],
        "description": "Price breaking above Ichimoku cloud with senkou span confirmation",
    },
    {
        "id": "elder-ray-scout",
        "name": "Elder Ray Bull Power",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "ElderRay",
        "symbols": ["SPY", "QQQ", "AAPL", "MSFT", "AMD", "NVDA", "AMZN", "META"],
        "description": "Elder Ray Bull Power crosses above zero with EMA uptrend",
    },
    {
        "id": "pivot-point-scout",
        "name": "Classic Pivot Point Breakout",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "PivotPoint",
        "symbols": ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META"],
        "description": "Price breaks above R1 or R2 pivot with volume confirmation",
    },
    {
        "id": "wyckoff-accumulation-scout",
        "name": "Wyckoff Accumulation Spring",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "WyckoffAccumulation",
        "symbols": ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMD", "META", "GOOGL", "JPM", "XOM", "COIN", "MSTR"],
        "description": "Wyckoff spring + upthrust pattern detection (institutional accumulation)",
    },
    {
        "id": "open-drive-scout",
        "name": "Opening Range Breakout",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "OpeningRangeBreakout",
        "symbols": ["SPY", "QQQ", "AAPL", "TSLA", "NVDA", "AMD", "COIN", "MSTR", "PLTR", "GME"],
        "description": "Opening range breakout after first 30-min candle with volume",
    },
    {
        "id": "smart-money-div-scout",
        "name": "Smart Money Structure Break",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "SmartMoneyStructure",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "BNB-USD", "LINK-USD", "INJ-USD", "TIA-USD", "SUI20947-USD"],
        "description": "ICT structure break of swing high + order block mitigation",
    },
    {
        "id": "vwap-bands-scout",
        "name": "VWAP Statistical Deviation",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "VWAPBands",
        "symbols": ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "META", "BTC-USD", "ETH-USD"],
        "description": "Price at VWAP -2\u03c3 band with RSI oversold confirmation",
    },
    {
        "id": "dark-pool-scout",
        "name": "Dark Pool Block Trade Proxy",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "DarkPoolProxy",
        "symbols": ["AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA", "JPM", "BAC", "XOM", "SPY", "QQQ"],
        "description": "Large block trade proxy via intraday volume anomaly at stable price",
    },
    {
        "id": "chande-momentum-scout",
        "name": "Chande Momentum Oscillator",
        "category": "crypto",
        "tier": "SCOUT",
        "strategy": "ChandeMomentum",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "DOGE-USD", "LINK-USD", "ADA-USD"],
        "description": "CMO crosses above -50 from oversold territory",
    },
    {
        "id": "renko-breakout-scout",
        "name": "Renko Brick Breakout",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "RenkoBreakout",
        "symbols": ["SPY", "QQQ", "AAPL", "NVDA", "MSFT", "TSLA", "BTC-USD", "ETH-USD"],
        "description": "3 consecutive bullish Renko bricks + price above 20-brick MA",
    },
    {
        "id": "time-of-day-scout",
        "name": "Intraday Time-of-Day Momentum",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "TimeOfDayMomentum",
        "symbols": ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA"],
        "description": "10:30-11:00 and 14:30-15:00 statistical momentum windows",
    },
    {
        "id": "power-of-3-scout",
        "name": "ICT Power of 3 Pattern",
        "category": "crypto",
        "tier": "TIER_1",
        "strategy": "PowerOf3",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "AVAX-USD", "LINK-USD", "INJ-USD"],
        "description": "ICT accumulate-manipulate-distribute pattern (Asian session sweep)",
    },
    {
        "id": "spread-momentum-scout",
        "name": "Credit Spread Momentum",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "CreditSpreadMomentum",
        "symbols": ["SPY", "QQQ", "IWM", "HYG", "TLT", "LQD", "AAPL", "MSFT"],
        "description": "HYG/LQD spread tightening = risk-on \u2192 buy equities",
    },
    {
        "id": "implied-vol-skew-scout",
        "name": "IV Rank + Skew Signal",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "ImpliedVolSkew",
        "symbols": ["SPY", "QQQ", "AAPL", "NVDA", "TSLA", "META", "COIN", "MSTR"],
        "description": "IV rank < 20 + positive call skew = low risk entry",
    },
    {
        "id": "market-profile-scout",
        "name": "Market Profile POC Breakout",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "MarketProfile",
        "symbols": ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA"],
        "description": "Price breaks above value area high (VAH) of previous session",
    },
    {
        "id": "trin-reversal-scout",
        "name": "TRIN Arms Index Extreme",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "TRINReversal",
        "symbols": ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "META"],
        "description": "TRIN > 2.0 (extreme selling) = mean-reversion bounce signal",
    },
    {
        "id": "dmi-scout",
        "name": "Directional Movement Index",
        "category": "crypto",
        "tier": "SCOUT",
        "strategy": "DMIScout",
        "symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "BNB-USD", "LINK-USD"],
        "description": "DI+ crosses DI- with ADX > 20 confirming new trend",
    },
    {
        "id": "price-channel-scout",
        "name": "20-Day Price Channel Breakout",
        "category": "penny",
        "tier": "SCOUT",
        "strategy": "PriceChannel",
        "symbols": ["GME", "AMC", "PLTR", "SOFI", "HOOD", "MARA", "RIOT", "BBAI", "RIVN", "LCID"],
        "description": "Donchian 20-day high breakout + volume 2x average",
    },
    {
        "id": "kagi-reversal-scout",
        "name": "Kagi Line Reversal",
        "category": "stock",
        "tier": "SCOUT",
        "strategy": "KagiReversal",
        "symbols": ["SPY", "QQQ", "AAPL", "NVDA", "TSLA", "BTC-USD", "ETH-USD"],
        "description": "Kagi line flip from yin to yang with above-average volume",
    },
    {
        "id": "volatility-skew-scout",
        "name": "Options Volatility Skew",
        "category": "stock",
        "tier": "TIER_1",
        "strategy": "VolatilitySkew",
        "symbols": ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "META", "TSLA", "COIN"],
        "description": "Call skew > put skew (more call buying) = institutional bullish bias",
    },
]


# ---------------------------------------------------------------------------
# Elimination Engine
# ---------------------------------------------------------------------------

class EliminationEngine:
    """
    Manages algorithm lifecycle: danger zone → probation → elimination → replacement.
    Also handles promotions/demotions between leagues.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DATA_DIR
        self.state = self._load_state()
        self._apply_hard_bans()
        self._apply_forced_probation()

    def _load_state(self) -> dict:
        """Load persistent elimination state."""
        if ELIMINATION_STATE_PATH.exists():
            try:
                with open(ELIMINATION_STATE_PATH) as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "algo_history": {},   # algo_id → {danger_zone_days, probation_days, status}
            "eliminated": [],      # list of eliminated algo IDs
            "promoted": [],
            "demoted": [],
            "challengers_injected": [],
            "last_updated": None,
        }

    def _save_state(self):
        """Persist state to disk."""
        self.state["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(ELIMINATION_STATE_PATH, "w") as f:
            json.dump(self.state, f, indent=2)

    def _apply_hard_bans(self):
        """
        Mark all PERMANENTLY_BANNED_STRATEGIES as eliminated immediately.
        Called on init — these never go through the gradual pipeline.
        """
        already_eliminated = {
            e["algo_id"] if isinstance(e, dict) else e
            for e in self.state.get("eliminated", [])
        }
        changed = False
        for algo_id in PERMANENTLY_BANNED_STRATEGIES:
            # Ensure algo_history entry exists and is marked eliminated
            if algo_id not in self.state["algo_history"]:
                self.state["algo_history"][algo_id] = {
                    "danger_zone_days": 0,
                    "probation_days": 0,
                    "status": "eliminated",
                    "current_score": 0,
                    "current_league": "Banned",
                }
                changed = True
            else:
                if self.state["algo_history"][algo_id].get("status") != "eliminated":
                    self.state["algo_history"][algo_id]["status"] = "eliminated"
                    changed = True

            if algo_id not in already_eliminated:
                self.state["eliminated"].append({
                    "algo_id": algo_id,
                    "eliminated_at": datetime.now(timezone.utc).isoformat(),
                    "final_score": 0,
                    "closed_picks": 0,
                    "reason": "F-grade forward-test ban (0-25% WR)",
                })
                changed = True
                logger.info(f"HARD BAN: {algo_id} (permanently banned — F-grade WR)")

        if changed:
            self._save_state()

    def _apply_forced_probation(self):
        """
        Place all FORCE_PROBATION_STRATEGIES into probation status immediately.
        They skip the danger-zone countdown but can still recover if scores improve.
        """
        changed = False
        for algo_id in FORCE_PROBATION_STRATEGIES:
            if algo_id not in self.state["algo_history"]:
                self.state["algo_history"][algo_id] = {
                    "danger_zone_days": ELIMINATION_RULES["danger_zone_days"],
                    "probation_days": 0,
                    "status": "probation",
                    "current_score": 0,
                    "current_league": "Danger Zone",
                }
                changed = True
                logger.info(f"FORCED PROBATION: {algo_id} (D-grade WR 25-40%%)")
            else:
                hist = self.state["algo_history"][algo_id]
                # Only force probation if not already eliminated
                if hist.get("status") not in ("eliminated", "probation"):
                    hist["status"] = "probation"
                    hist["danger_zone_days"] = ELIMINATION_RULES["danger_zone_days"]
                    changed = True
                    logger.info(f"FORCED PROBATION: {algo_id} (D-grade WR 25-40%%)")

        if changed:
            self._save_state()

    def is_banned(self, algo_id: str) -> bool:
        """
        Check if an algorithm is permanently banned or eliminated.
        Used by live_scanner to skip signal generation entirely.
        """
        if algo_id in PERMANENTLY_BANNED_STRATEGIES:
            return True
        hist = self.state.get("algo_history", {}).get(algo_id)
        if hist and hist.get("status") == "eliminated":
            return True
        return False

    def check_eliminations(self, tournament: dict) -> list[str]:
        """
        Evaluate each algorithm's tournament score for elimination eligibility.
        Returns list of algo IDs to eliminate.
        """
        rankings = tournament.get("rankings", [])
        to_eliminate = []

        for algo in rankings:
            algo_id = algo.get("id", "")
            score = algo.get("score", 46.0)
            closed_picks = algo.get("closedPicks", 0)
            league = algo.get("league", "Challenger League")

            # Initialize history if needed
            if algo_id not in self.state["algo_history"]:
                self.state["algo_history"][algo_id] = {
                    "danger_zone_days": 0,
                    "probation_days": 0,
                    "status": "active",
                    "current_score": score,
                    "current_league": league,
                }

            hist = self.state["algo_history"][algo_id]

            # Skip already eliminated
            if hist["status"] == "eliminated":
                continue

            # Update score history
            hist["current_score"] = score
            hist["current_league"] = league

            # Not enough picks yet — skip elimination check
            if closed_picks < ELIMINATION_RULES["min_picks_for_elimination"]:
                hist["danger_zone_days"] = 0
                hist["probation_days"] = 0
                continue

            # Danger zone tracking
            if score < ELIMINATION_RULES["danger_zone_threshold"]:
                hist["danger_zone_days"] += 1
            else:
                hist["danger_zone_days"] = 0
                hist["probation_days"] = 0
                hist["status"] = "active"

            # Probation trigger
            if hist["danger_zone_days"] >= ELIMINATION_RULES["danger_zone_days"]:
                hist["status"] = "probation"

            # Probation tracking
            if hist["status"] == "probation":
                if score < ELIMINATION_RULES["probation_threshold"]:
                    hist["probation_days"] += 1
                else:
                    # Recovering in probation — back to active
                    hist["status"] = "active"
                    hist["probation_days"] = 0
                    hist["danger_zone_days"] = 0

            # Elimination trigger
            if (hist["status"] == "probation"
                    and hist["probation_days"] >= ELIMINATION_RULES["probation_days"]):
                hist["status"] = "eliminated"
                to_eliminate.append(algo_id)
                self.state["eliminated"].append({
                    "algo_id": algo_id,
                    "eliminated_at": datetime.now(timezone.utc).isoformat(),
                    "final_score": score,
                    "closed_picks": closed_picks,
                    "reason": f"Score {score:.1f} in danger zone for {hist['danger_zone_days']}d",
                })
                logger.info(f"ELIMINATED: {algo_id} (score={score:.1f}, days={hist['danger_zone_days']}")

        self._save_state()
        return to_eliminate

    def inject_challengers(self, eliminated_ids: list[str]) -> list[dict]:
        """
        Select replacement algorithms from CHALLENGER_POOL.
        Returns list of new algo defs to inject into ALGO_DEFS.
        """
        already_injected = {c["algo_id"] for c in self.state.get("challengers_injected", [])}
        available = [c for c in CHALLENGER_POOL if c["id"] not in already_injected]

        challengers = []
        for algo_id in eliminated_ids:
            if not available:
                logger.warning("Challenger pool exhausted!")
                break
            challenger = available.pop(0)
            challengers.append(challenger)
            self.state["challengers_injected"].append({
                "algo_id": challenger["id"],
                "replaced": algo_id,
                "injected_at": datetime.now(timezone.utc).isoformat(),
            })
            logger.info(f"INJECTED: {challenger['id']} replacing {algo_id}")

        self._save_state()
        return challengers

    def check_promotions_demotions(self, tournament: dict) -> dict:
        """
        Check and log league promotions/demotions.
        Returns {"promoted": [...], "demoted": [...]}
        """
        rankings = tournament.get("rankings", [])
        promoted = []
        demoted = []

        for algo in rankings:
            algo_id = algo.get("id", "")
            score = algo.get("score", 46.0)
            league = algo.get("league", "Challenger League")

            if algo_id not in self.state["algo_history"]:
                continue
            hist = self.state["algo_history"][algo_id]
            prev_league = hist.get("current_league", league)

            # Promotion checks
            if league == "Challenger League" and score >= ELIMINATION_RULES["promotion_challenger_score"]:
                hist.setdefault("promo_days", 0)
                hist["promo_days"] += 1
                if hist["promo_days"] >= ELIMINATION_RULES["promotion_challenger_days"]:
                    promoted.append({"algo_id": algo_id, "from": "Challenger League", "to": "Premier League"})
                    hist["promo_days"] = 0
            elif league == "Premier League" and score >= ELIMINATION_RULES["promotion_premier_score"]:
                hist.setdefault("promo_days", 0)
                hist["promo_days"] += 1
                if hist["promo_days"] >= ELIMINATION_RULES["promotion_premier_days"]:
                    promoted.append({"algo_id": algo_id, "from": "Premier League", "to": "Champions League"})
                    hist["promo_days"] = 0
            else:
                hist["promo_days"] = 0

            # Demotion checks
            if league == "Champions League" and score < ELIMINATION_RULES["demotion_champions_score"]:
                hist.setdefault("demo_days", 0)
                hist["demo_days"] += 1
                if hist["demo_days"] >= ELIMINATION_RULES["demotion_champions_days"]:
                    demoted.append({"algo_id": algo_id, "from": "Champions League", "to": "Premier League"})
                    hist["demo_days"] = 0
            elif league == "Premier League" and score < ELIMINATION_RULES["demotion_premier_score"]:
                hist.setdefault("demo_days", 0)
                hist["demo_days"] += 1
                if hist["demo_days"] >= ELIMINATION_RULES["demotion_premier_days"]:
                    demoted.append({"algo_id": algo_id, "from": "Premier League", "to": "Challenger League"})
                    hist["demo_days"] = 0
            else:
                hist["demo_days"] = 0

        self._save_state()
        return {"promoted": promoted, "demoted": demoted}

    def log_event(self, event_type: str, algo_id: str, reason: str):
        """Append elimination/promotion event to audit_log.json."""
        audit_path = self.data_dir / "audit_log.json"
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,  # ELIMINATION | PROMOTION | DEMOTION | CHALLENGER_INJECT
            "algorithm": algo_id,
            "signal": event_type,
            "reason": reason,
            "symbol": "SYSTEM",
            "price": None,
        }
        try:
            if audit_path.exists():
                with open(audit_path) as f:
                    log = json.load(f)
            else:
                log = []
            log.append(entry)
            with open(audit_path, "w") as f:
                json.dump(log, f, indent=2)
        except Exception as e:
            logger.warning(f"log_event failed: {e}")

    def get_state(self) -> dict:
        """Return current elimination state for all_data injection."""
        return {
            "eliminated": [e["algo_id"] for e in self.state.get("eliminated", [])],
            "permanently_banned": list(PERMANENTLY_BANNED_STRATEGIES),
            "on_probation": [
                algo_id for algo_id, hist in self.state.get("algo_history", {}).items()
                if hist.get("status") == "probation"
            ],
            "challengers": [c["algo_id"] for c in self.state.get("challengers_injected", [])],
            "last_updated": self.state.get("last_updated"),
        }

    def get_status_report(self) -> str:
        """Human-readable status report."""
        hist = self.state.get("algo_history", {})
        eliminated = [a for a, h in hist.items() if h.get("status") == "eliminated"]
        probation = [a for a, h in hist.items() if h.get("status") == "probation"]
        active = [a for a, h in hist.items() if h.get("status") == "active"]
        banned = list(PERMANENTLY_BANNED_STRATEGIES)

        elim_str = ", ".join(eliminated) if eliminated else "none"
        prob_str = ", ".join(probation) if probation else "none"
        banned_str = ", ".join(banned) if banned else "none"
        ci_key = "challengers_injected"

        lines = [
            "=== Elimination Engine Status ===",
            f"Active: {len(active)} algorithms",
            f"Permanently Banned (F-grade): {len(banned)} ({banned_str})",
            f"On Probation: {len(probation)} ({prob_str})",
            f"Eliminated: {len(eliminated)} ({elim_str})",
            f"Challengers Injected: {len(self.state.get(ci_key, []))}",
        ]
        return chr(10).join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("EliminationEngine — testing with current tournament data...")
    engine = EliminationEngine()

    # Load tournament
    t_path = DATA_DIR / "tournament.json"
    if t_path.exists():
        with open(t_path) as f:
            tournament = json.load(f)
        eliminated = engine.check_eliminations(tournament)
        promo_demo = engine.check_promotions_demotions(tournament)
        print(engine.get_status_report())
        print(f"Would eliminate: {eliminated}")
        print(f"Promotions: {promo_demo['promoted']}")
        print(f"Demotions: {promo_demo['demoted']}")
    else:
        print("No tournament.json found")
    print("Done.")
