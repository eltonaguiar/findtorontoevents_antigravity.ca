#!/usr/bin/env python3
"""
tennis_elo_engine.py — Surface-specific ELO ratings from JeffSackmann/tennis_atp.

Open-source data sources (replaces ~$50K/year sports analytics stack):
  - github.com/JeffSackmann/tennis_atp (MIT): every ATP match since 1968,
    rankings, results, stats — replaces paid data subscriptions ($500/mo).
  - github.com/JeffSackmann/tennis_slam_pointbypoint: point-by-point Grand
    Slam data — referenced for future in-match Bayesian model extension.
  - github.com/jgollub1/tennis_elo: ELO + serve/return stats → win probability
    methodology (inspiration for the surface-specific ELO + serve-dominance
    computation implemented here).

Outputs live-monitor/data/tennis_elo_ratings.json consumed by the PHP
tennis ELO overlay (live-monitor/api/tennis_elo_lib.php) which annotates
ATP/WTA picks in sports_picks.php analogously to the NHL goalie overlay.

Usage:
  python3 live-monitor/tennis_elo_engine.py
  python3 live-monitor/tennis_elo_engine.py --years 6 --out /custom/path.json
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import math
import os
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

GITHUB_RAW = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master"
REQUEST_TIMEOUT = 30

# ELO parameters inspired by jgollub1/tennis_elo
ELO_INIT = 1500.0
ELO_K_SLAM = 40.0      # Grand Slams weighted higher
ELO_K_MASTERS = 36.0   # Masters 1000
ELO_K_500 = 32.0       # ATP 500 / ATP Finals
ELO_K_DEFAULT = 24.0   # ATP 250 / Challenger

SURFACE_MAP = {
    "hard": "hard",
    "clay": "clay",
    "grass": "grass",
    "carpet": "hard",
    "indoor hard": "hard",
    "acrylic": "hard",
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(ROOT, "live-monitor", "data", "tennis_elo_ratings.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _k_factor(tourney_level: str) -> float:
    lvl = (tourney_level or "A").strip().upper()
    if lvl == "G":
        return ELO_K_SLAM
    if lvl == "M":
        return ELO_K_MASTERS
    if lvl in ("A", "F"):
        return ELO_K_500
    return ELO_K_DEFAULT


def _elo_expected(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def _surface_norm(raw: str) -> str:
    return SURFACE_MAP.get((raw or "").lower().strip(), "hard")


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _fetch_csv(year: int) -> Optional[List[Dict[str, str]]]:
    url = f"{GITHUB_RAW}/atp_matches_{year}.csv"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "TennisEloEngine/1.0 (findtorontoevents.ca)"}
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(raw))
        rows = list(reader)
        LOG.info("Fetched %d matches for %d", len(rows), year)
        return rows
    except Exception as exc:
        LOG.warning("Could not fetch atp_matches_%d.csv: %s", year, exc)
        return None


# ---------------------------------------------------------------------------
# ELO state per player
# ---------------------------------------------------------------------------

class PlayerState:
    """Mutable ELO + rolling serve stats for one player."""

    SURFACES = ("hard", "clay", "grass")
    EMA_ALPHA = 0.08  # slow EMA to smooth noise over career

    def __init__(self) -> None:
        self.elo: float = ELO_INIT
        self.elo_surface: Dict[str, float] = {s: ELO_INIT for s in self.SURFACES}
        self.matches: int = 0
        # Serve stats (exponential moving averages, seeded to tour averages)
        self.serve_in_pct: float = 61.0        # 1st serve in %
        self.first_won_pct: float = 73.0       # pts won on 1st serve %
        self.second_won_pct: float = 53.0      # pts won on 2nd serve %

    def apply_elo_delta(self, surface: str, overall_delta: float, surface_delta: float) -> None:
        self.elo += overall_delta
        old = self.elo_surface.get(surface, ELO_INIT)
        self.elo_surface[surface] = old + surface_delta
        self.matches += 1

    def update_serve_stats(self, row: Dict[str, str], prefix: str) -> None:
        """prefix is 'w_' for winner or 'l_' for loser."""
        svpt = _safe_float(row.get(f"{prefix}svpt"))
        if svpt <= 0:
            return
        fst_in = _safe_float(row.get(f"{prefix}1stIn"))
        fst_won = _safe_float(row.get(f"{prefix}1stWon"))
        snd_won = _safe_float(row.get(f"{prefix}2ndWon"))

        serve_in = 100.0 * fst_in / svpt if svpt > 0 else None
        f_won = 100.0 * fst_won / fst_in if fst_in > 0 else None
        snd_pts = svpt - fst_in
        s_won = 100.0 * snd_won / snd_pts if snd_pts > 1 else None

        a = self.EMA_ALPHA
        if serve_in is not None and 20 < serve_in < 90:
            self.serve_in_pct = (1 - a) * self.serve_in_pct + a * serve_in
        if f_won is not None and 40 < f_won < 95:
            self.first_won_pct = (1 - a) * self.first_won_pct + a * f_won
        if s_won is not None and 25 < s_won < 90:
            self.second_won_pct = (1 - a) * self.second_won_pct + a * s_won

    @property
    def serve_dominance(self) -> float:
        """Composite serve quality score (higher = bigger server advantage).
        Inspired by jgollub1/tennis_elo serve-dominance ratio."""
        # Weighted mix of 1st and 2nd serve effectiveness
        # A player wins ~(serve_in * 1st_won + (1-serve_in) * 2nd_won) of service points
        s = self.serve_in_pct / 100.0
        return s * self.first_won_pct + (1 - s) * self.second_won_pct


# ---------------------------------------------------------------------------
# ELO computation
# ---------------------------------------------------------------------------

def compute_elo(rows: List[Dict[str, str]]) -> Dict[str, PlayerState]:
    players: Dict[str, PlayerState] = defaultdict(PlayerState)

    for row in rows:
        winner = (row.get("winner_name") or "").strip()
        loser = (row.get("loser_name") or "").strip()
        if not winner or not loser:
            continue

        surface = _surface_norm(row.get("surface", ""))
        k = _k_factor(row.get("tourney_level", "A"))

        ws = players[winner]
        ls = players[loser]

        # --- Overall ELO ---
        exp_w = _elo_expected(ws.elo, ls.elo)
        w_delta_overall = k * (1.0 - exp_w)
        l_delta_overall = k * (0.0 - (1.0 - exp_w))

        # --- Surface ELO ---
        w_surf = ws.elo_surface.get(surface, ELO_INIT)
        l_surf = ls.elo_surface.get(surface, ELO_INIT)
        exp_ws = _elo_expected(w_surf, l_surf)
        w_delta_surf = k * (1.0 - exp_ws)
        l_delta_surf = k * (0.0 - (1.0 - exp_ws))

        ws.apply_elo_delta(surface, w_delta_overall, w_delta_surf)
        ls.apply_elo_delta(surface, l_delta_overall, l_delta_surf)

        # --- Serve stats ---
        ws.update_serve_stats(row, "w_")
        ls.update_serve_stats(row, "l_")

    return dict(players)


def win_probability(rating_a: float, rating_b: float) -> float:
    """ELO win probability for player A vs player B."""
    return _elo_expected(rating_a, rating_b)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def build_output(players: Dict[str, PlayerState], total_matches: int) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    player_data: Dict[str, Any] = {}
    for name, state in sorted(players.items(), key=lambda kv: -kv[1].elo):
        if state.matches < 5:
            continue
        player_data[name] = {
            "elo": round(state.elo, 1),
            "elo_hard": round(state.elo_surface.get("hard", ELO_INIT), 1),
            "elo_clay": round(state.elo_surface.get("clay", ELO_INIT), 1),
            "elo_grass": round(state.elo_surface.get("grass", ELO_INIT), 1),
            "serve_in_pct": round(state.serve_in_pct, 1),
            "first_won_pct": round(state.first_won_pct, 1),
            "second_won_pct": round(state.second_won_pct, 1),
            "serve_dominance": round(state.serve_dominance, 1),
            "matches": state.matches,
        }
    return {
        "ok": True,
        "generated_at": now,
        "source": "tennis_elo_engine",
        "attribution": (
            "Data: JeffSackmann/tennis_atp (MIT license) — "
            "replaces paid ATP data feeds. "
            "ELO methodology inspired by jgollub1/tennis_elo."
        ),
        "total_matches_processed": total_matches,
        "player_count": len(player_data),
        "players": player_data,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Tennis ELO engine — JeffSackmann/tennis_atp")
    ap.add_argument(
        "--years", type=int, default=6,
        help="Number of recent years to fetch (default: 6)"
    )
    ap.add_argument("--out", default=DEFAULT_OUT, help="Output JSON path")
    args = ap.parse_args()

    current_year = datetime.now(timezone.utc).year
    years = list(range(current_year - args.years + 1, current_year + 1))
    LOG.info("Fetching ATP match data for years: %s", years)

    all_rows: List[Dict[str, str]] = []
    for year in years:
        rows = _fetch_csv(year)
        if rows:
            all_rows.extend(rows)

    if not all_rows:
        LOG.error("No match data loaded — check network access to raw.githubusercontent.com")
        print(json.dumps({"ok": False, "error": "no match data loaded"}))
        sys.exit(1)

    # Sort chronologically by tourney_date (YYYYMMDD integer string)
    all_rows.sort(key=lambda r: _safe_int(r.get("tourney_date", "0")))
    LOG.info("Processing %d total matches across %d years...", len(all_rows), len(years))

    players = compute_elo(all_rows)
    LOG.info("ELO computed for %d players", len(players))

    output = build_output(players, len(all_rows))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2)
    LOG.info("Wrote %d players → %s", output["player_count"], args.out)
    print(json.dumps({
        "ok": True,
        "player_count": output["player_count"],
        "matches_processed": len(all_rows),
    }))


if __name__ == "__main__":
    main()
