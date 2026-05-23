"""Shin (1993) devig vs proportional inverse-normalize backtest harness.

Validates the new `sports_value_devig_shin()` PHP function on PR #401
(live-monitor/api/sports_value_analyze_lib.php) by re-implementing the
algorithm in Python and comparing it head-to-head against the proportional
inverse-normalize method on real Pinnacle quotes from the production DB.

Methodology
-----------
1. Parse a mysqldump (INSERT INTO lm_sports_odds rows) -- stdlib regex only.
2. Group h2h moneyline rows by (event_id, market='h2h'); keep buckets where
   Pinnacle ('pinnacle' / 'pinnacle_eu') quoted BOTH home and away.
3. For each bucket compute:
     - shin_p[home, away]   via bisection on z in [0, 0.5]
     - prop_p[home, away]   via inverse normalization
   Record the favorite-side delta (Shin - Proportional, in pp). Shin is
   expected to pull the favorite slightly UP and the dog slightly DOWN
   because vig is theorized to be carried mostly by the dog side.
4. Cross-reference settled rows in `lm_sports_bets` (status in won/lost).
   For each settled bet whose (event_id, pick) maps to a Pinnacle bucket,
   score the implied probability under each method against the realized
   outcome (1=won, 0=lost) using Brier score: mean((p - y)**2). Lower is
   better-calibrated.
5. Honest sample-size caveat: with the 2026-04-25 snapshot we expect ~41
   settled bets total, of which only the Pinnacle-quoted subset counts.

Run:  python tools/backtest_shin_devig.py
Output: stdout summary + reports/SHIN_DEVIG_BACKTEST_2026_04_26.md
Read-only on the SQL dump. No network calls. Stdlib only.
"""

from __future__ import annotations

import math
import os
import re
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

SQL_DUMP = r"C:\Users\zerou\Downloads\ejaguiar1_sportsbet.sql"
REPORT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "reports",
    "SHIN_DEVIG_BACKTEST_2026_04_26.md",
)

PINNACLE_KEYS = {"pinnacle", "pinnacle_eu"}


# ---------- Shin devig (port of sports_value_devig_shin in PHP) ----------

def shin_devig(prices: List[float]) -> Optional[List[float]]:
    n = len(prices)
    if n < 2:
        return None
    pi: List[float] = []
    sum_pi = 0.0
    for p in prices:
        if p < 1.01:
            return None
        inv = 1.0 / p
        pi.append(inv)
        sum_pi += inv
    if sum_pi <= 1.0 + 1e-9:
        return [v / sum_pi for v in pi] if sum_pi > 0 else [0.0] * n

    def shin_sum(z: float) -> float:
        denom = 2.0 * (1.0 - z)
        if denom <= 1e-9:
            return float("inf")
        s = 0.0
        for inv in pi:
            term = inv * inv / sum_pi
            s += (math.sqrt(z * z + 4.0 * (1.0 - z) * term) - z) / denom
        return s

    lo, hi = 0.0, 0.5
    f_lo = shin_sum(lo) - 1.0
    f_hi = shin_sum(hi) - 1.0
    if f_lo * f_hi > 0:
        return [v / sum_pi for v in pi]
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        f_mid = shin_sum(mid) - 1.0
        if f_mid > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-10:
            break
    z = 0.5 * (lo + hi)
    denom = 2.0 * (1.0 - z)
    if denom <= 1e-9:
        return [v / sum_pi for v in pi]
    out = []
    for inv in pi:
        term = inv * inv / sum_pi
        out.append((math.sqrt(z * z + 4.0 * (1.0 - z) * term) - z) / denom)
    return out


def proportional_devig(prices: List[float]) -> Optional[List[float]]:
    inv = [1.0 / p for p in prices if p >= 1.01]
    if len(inv) != len(prices):
        return None
    s = sum(inv)
    if s <= 1e-9:
        return None
    return [v / s for v in inv]


# ---------- SQL dump parser ----------

# Crude but adequate: split on '),(' between the outer parens of each INSERT.
ODDS_INSERT_RE = re.compile(
    r"INSERT INTO `lm_sports_odds`[^V]*VALUES\s*(.*?);\s*\n", re.DOTALL
)
BETS_INSERT_RE = re.compile(
    r"INSERT INTO `lm_sports_bets`[^V]*VALUES\s*(.*?);\s*\n", re.DOTALL
)
# Split a values blob like (a,b,...),(c,d,...),... into rows.
ROW_SPLIT_RE = re.compile(r"\),\(")


def _split_row(row: str) -> List[str]:
    # row has fields separated by commas; strings are single-quoted with
    # backslash-escape. Walk char by char.
    out: List[str] = []
    buf: List[str] = []
    in_str = False
    esc = False
    for ch in row:
        if esc:
            buf.append(ch)
            esc = False
            continue
        if ch == "\\":
            buf.append(ch)
            esc = True
            continue
        if ch == "'":
            in_str = not in_str
            buf.append(ch)
            continue
        if ch == "," and not in_str:
            out.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    out.append("".join(buf))
    return out


def _unq(s: str) -> str:
    s = s.strip()
    if s.startswith("'") and s.endswith("'"):
        s = s[1:-1]
    return s.replace("\\'", "'").replace("\\\\", "\\")


def parse_odds(text: str):
    """Yield odds rows as dicts."""
    for m in ODDS_INSERT_RE.finditer(text):
        blob = m.group(1).strip()
        if blob.startswith("("):
            blob = blob[1:]
        if blob.endswith(")"):
            blob = blob[:-1]
        # Rows are separated by "),\n(" — normalize newlines first.
        blob = blob.replace("\n", "")
        for row in ROW_SPLIT_RE.split(blob):
            fields = _split_row(row)
            if len(fields) < 13:
                continue
            try:
                yield {
                    "event_id": _unq(fields[2]),
                    "sport": _unq(fields[1]),
                    "home_team": _unq(fields[3]),
                    "away_team": _unq(fields[4]),
                    "bookmaker_key": _unq(fields[7]).lower(),
                    "market": _unq(fields[8]),
                    "outcome_name": _unq(fields[9]),
                    "outcome_price": float(fields[10]),
                }
            except (ValueError, IndexError):
                continue


def parse_bets(text: str):
    for m in BETS_INSERT_RE.finditer(text):
        blob = m.group(1).strip()
        if blob.startswith("("):
            blob = blob[1:]
        if blob.endswith(")"):
            blob = blob[:-1]
        blob = blob.replace("\n", "")
        for row in ROW_SPLIT_RE.split(blob):
            fields = _split_row(row)
            if len(fields) < 30:
                continue
            try:
                yield {
                    "event_id": _unq(fields[1]),
                    "pick": _unq(fields[9]),
                    "market": _unq(fields[8]),
                    "odds": float(fields[13]),
                    "status": _unq(fields[26]),
                    "result": _unq(fields[27]),
                }
            except (ValueError, IndexError):
                continue


# ---------- Backtest ----------

def main() -> int:
    if not os.path.exists(SQL_DUMP):
        print(f"SQL dump not found: {SQL_DUMP}", file=sys.stderr)
        return 1
    with open(SQL_DUMP, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()

    # event_id -> {bookmaker_key -> {outcome_name -> price}}; track home/away.
    buckets: Dict[str, Dict] = defaultdict(
        lambda: {"home": None, "away": None, "books": defaultdict(dict)}
    )
    odds_count = 0
    for r in parse_odds(text):
        if r["market"] != "h2h":
            continue
        odds_count += 1
        b = buckets[r["event_id"]]
        b["home"] = r["home_team"]
        b["away"] = r["away_team"]
        b["books"][r["bookmaker_key"]][r["outcome_name"]] = r["outcome_price"]

    pin_buckets: Dict[str, Tuple[float, float, str, str]] = {}
    for eid, b in buckets.items():
        for bk, outs in b["books"].items():
            if bk not in PINNACLE_KEYS:
                continue
            home_px = outs.get(b["home"])
            away_px = outs.get(b["away"])
            if home_px and away_px and home_px >= 1.01 and away_px >= 1.01:
                pin_buckets[eid] = (home_px, away_px, b["home"], b["away"])
                break

    fav_deltas: List[float] = []
    for eid, (hp, ap, _h, _a) in pin_buckets.items():
        shin = shin_devig([hp, ap])
        prop = proportional_devig([hp, ap])
        if not shin or not prop:
            continue
        # Favorite = lower price = higher implied probability.
        fav_idx = 0 if hp < ap else 1
        fav_deltas.append((shin[fav_idx] - prop[fav_idx]) * 100.0)

    # Settled bets cross-ref.
    bets = list(parse_bets(text))
    settled = [b for b in bets if b["status"] in ("won", "lost") and b["market"] == "h2h"]
    shin_brier_terms: List[float] = []
    prop_brier_terms: List[float] = []
    matched = 0
    for bet in settled:
        eid = bet["event_id"]
        if eid not in pin_buckets:
            continue
        hp, ap, home, away = pin_buckets[eid]
        if bet["pick"] == home:
            idx = 0
        elif bet["pick"] == away:
            idx = 1
        else:
            continue
        shin = shin_devig([hp, ap])
        prop = proportional_devig([hp, ap])
        if not shin or not prop:
            continue
        y = 1.0 if bet["status"] == "won" else 0.0
        shin_brier_terms.append((shin[idx] - y) ** 2)
        prop_brier_terms.append((prop[idx] - y) ** 2)
        matched += 1

    n_pin = len(pin_buckets)
    n_settled = len(settled)
    mean_fav_delta = sum(fav_deltas) / len(fav_deltas) if fav_deltas else 0.0
    shin_brier = sum(shin_brier_terms) / len(shin_brier_terms) if shin_brier_terms else float("nan")
    prop_brier = sum(prop_brier_terms) / len(prop_brier_terms) if prop_brier_terms else float("nan")

    inconclusive = matched < 20

    lines = [
        f"odds rows parsed:         {odds_count}",
        f"h2h buckets total:        {len(buckets)}",
        f"Pinnacle h2h buckets:     {n_pin}",
        f"settled h2h bets:         {n_settled}",
        f"settled & Pinnacle-anchored: {matched}",
        f"mean Shin-Prop favorite delta (pp): {mean_fav_delta:+.4f}",
        f"Shin Brier:               {shin_brier:.6f}",
        f"Proportional Brier:       {prop_brier:.6f}",
    ]
    if not math.isnan(shin_brier) and not math.isnan(prop_brier):
        diff = prop_brier - shin_brier  # >0 means Shin better
        lines.append(f"Brier diff (Prop - Shin): {diff:+.6f}  ({'Shin better' if diff > 0 else 'Prop better'})")
    print("\n".join(lines))
    if inconclusive:
        print("\nNOTE: matched < 20 settled+anchored buckets -- result is INCONCLUSIVE.")

    # Write report
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    md = []
    md.append("# Shin Devig Backtest -- 2026-04-26")
    md.append("")
    md.append("Validation of `sports_value_devig_shin()` introduced in PR #401")
    md.append("(`live-monitor/api/sports_value_analyze_lib.php`). Compares Shin (1993)")
    md.append("bisection devig against the prior proportional inverse-normalize on a")
    md.append("snapshot of the production DB (`ejaguiar1_sportsbet.sql`).")
    md.append("")
    md.append("## Methodology")
    md.append("")
    md.append("- Re-implemented the PHP `sports_value_devig_shin()` in Python (stdlib).")
    md.append("- Parsed `lm_sports_odds` h2h rows; kept buckets with both Pinnacle home")
    md.append("  and away prices.")
    md.append("- For each bucket: Shin fair probs vs proportional fair probs.")
    md.append("- Cross-referenced settled `lm_sports_bets` (won/lost) and computed Brier")
    md.append("  score per method against realized win.")
    md.append("")
    md.append("## Results")
    md.append("")
    md.append("```")
    md.extend(lines)
    md.append("```")
    md.append("")
    if inconclusive:
        md.append("## Verdict")
        md.append("")
        md.append("**INCONCLUSIVE.** Pinnacle-anchored settled bets in the snapshot are")
        md.append("below the 20-sample threshold for a meaningful Brier comparison.")
        md.append("Will rerun once `lm_sports_odds_history` populates from the new")
        md.append("`*/5 * * * *` Pinnacle scraper cron and additional bets settle.")
        md.append("")
        md.append("The favorite-side mean delta is still informative as a structural")
        md.append("check: Shin is expected to push the favorite slightly higher than")
        md.append("proportional (positive pp) when both books are vigged.")
    else:
        md.append("## Verdict")
        md.append("")
        if not math.isnan(shin_brier) and not math.isnan(prop_brier):
            if prop_brier > shin_brier:
                md.append(f"Shin shows a lower Brier score by {prop_brier - shin_brier:.6f}")
                md.append("(better calibration). Sample is modest; treat as directional.")
            else:
                md.append(f"Shin Brier is higher by {shin_brier - prop_brier:.6f}.")
                md.append("Recommend further review before relying on Shin in production.")
    md.append("")
    md.append("## Reproduce")
    md.append("")
    md.append("```")
    md.append("python tools/backtest_shin_devig.py")
    md.append("```")
    md.append("")
    md.append("Source: `tools/backtest_shin_devig.py`. Read-only on the SQL dump.")
    md.append("Stdlib Python only; no network calls.")

    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    print(f"\nReport written: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
