"""One canonical view of the resolved closed book (``resolved_closed_picks_net``).

Why this exists (external review v2/v3, action A2; `docs/AUDIT_SURFACE_REVIEW_2026-11-19.md`):

    /audit reported ETF at n=52, WR 1.9%, PF 0.02 while audit3 reported n=584,
    WR 43.1%, PF 0.98 for the same class on the same day. EQUITY differed 3x on
    n and 14pp on WR; COMMODITY had opposite signs. Both pages were arithmetically
    correct on their own inputs and neither denominator was published, so there was
    no way to tell which number described the book.

The fix is not a better metric, it is a declared one. This module publishes the
resolved closed book once, with:

  * the validity rules supplied by the caller (the dashboard passes its own
    ``_is_valid_resolved_pick``, so there is still exactly ONE copy of those rules),
  * every excluded row attributed to a reason instead of vanishing,
  * mirror duplicates removed under the same key the dashboard uses,
  * realised cost applied per class to give ``pnl_net_pct`` alongside gross,
  * a sha256 over the canonical rows, so any surface quoting a number can be
    checked against the rows it came from.

Consumers:
  * ``audit_trail/dashboard_generator.py`` writes the sidecar and embeds the
    summary block in the payload as ``resolved_closed_picks_net``.
  * ``alpha_engine/audit3_tribunal.py`` scores the canonical rows when the sidecar
    is reachable and otherwise falls back to the export slice, stamping which
    denominator it used (``mode``) rather than implying they are the same.

Stdlib only: this runs in CI on runners with no third-party packages.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable

SCHEMA = "audit.canonical.v1"

from alpha_engine.symbol_identity import pick_id_join_key  # noqa: E402
ROWS_FILENAME = "resolved_closed_picks_net.json"

#: Realised round-trip cost per class, in basis points, taken from the dashboard's
#: own ``slippage_validation.asset_class_stats`` (2026-11-19 payload) rather than a
#: new cost model. audit3 carries the same numbers as its flat fallbacks; when a
#: per-strategy measured cost is known callers should pass ``cost_bps`` explicitly.
CLASS_COST_BPS: dict[str, float] = {
    "CRYPTO": 9.97,
    "EQUITY": 5.0,
    "ETF": 5.0,
    "FOREX": 2.0,
    "BOND": 5.0,
    "FUTURES": 15.0,
    "COMMODITY": 15.0,
    "MUTUAL_FUND": 8.0,
}
DEFAULT_COST_BPS: float = 10.0

#: |pnl| at or below this is flat, not a win or a loss (matches the dashboard).
FLAT_EPSILON_PCT: float = 0.01

# ── Provenance triple (A1) ────────────────────────────────────────────────────
# Every published number must be able to name the three choices that produced it.
# These are DECLARATIONS of what the code already does, not new behaviour — the
# point is that a reader (or a tile on /audit) can state them without guessing.
POPULATION = "resolved_closed_picks_net"
COST_MODEL = "measured_class_slippage_bps"

#: Win is defined on GROSS pnl, not net: `won = pnl_gross_pct > FLAT_EPSILON_PCT`.
#: That is deliberate (it matches the dashboard) but it is a trap worth naming —
#: a pick can be a "win" and still lose money after cost. The net figure is
#: published alongside as `pnl_net_pct`, never folded into `won`.
WIN_DEFINITION = "gross_pnl_pct > flat_epsilon_pct"


def provenance() -> dict[str, Any]:
    """The (population, cost_model, win_definition) triple, with its parameters.

    A number without this is not wrong, it is unattributable — which is how
    /audit and /audit3 disagreed by 3x on the same class while both being
    arithmetically correct.
    """
    return {
        "population": POPULATION,
        "cost_model": COST_MODEL,
        "win_definition": WIN_DEFINITION,
        "flat_epsilon_pct": FLAT_EPSILON_PCT,
        "default_cost_bps": DEFAULT_COST_BPS,
        "schema": SCHEMA,
    }

_NON_PERFORMANCE_EXITS = {
    "",
    "UNKNOWN",
    "MANUAL",
    "CANCELLED",
    "CANCELED",
    "INVALID_ENTRY",
    "NO_FILL",
    "NOT_FILLED",
}

#: Statuses that mean "not a resolved outcome". OPEN/PENDING are unresolved by
#: definition; CANCELLED/CANCELED/INVALID never produced a realised fill.
_NON_PERFORMANCE_STATUSES = ("OPEN", "PENDING", "CANCELLED", "CANCELED", "INVALID")

#: Statuses only written after a position resolved — used to accept a row whose
#: exit_reason is absent, since the status itself is evidence of closure.
_TERMINAL_STATUSES = frozenset({"WON", "LOST", "EXPIRED", "CLOSED"})

#: Exit reasons that carry no information rather than a negative statement —
#: judged by closure evidence (close marker or terminal status), not denied.
_NO_EXIT_INFO = ("", "UNKNOWN")


def is_performance_scored_row(row: dict) -> bool:
    """Single definition of 'this closed row counts toward performance'.

    Both the canonical view and the audit3 tribunal MUST call this, so the two
    can never drift apart again. They did: the tribunal used a 3-value status
    deny-list and never read ``exit_reason``, while this view also dropped on
    exit reason — a measured ~4.9k-row disagreement (4,868 null exits, 100
    ``STALE*``) that was dormant only while the sidecar happened to be present
    and the tribunal ran in ``mode: canonical``.

    Encodes the CANONICAL semantics — status deny-list AND exit-reason
    exclusion — because this view is the stricter, already-published definition.

    Scope is deliberately narrow: identity, numeric pnl, status and exit reason.
    Row-content integrity checks (corrupt prices, blocked symbols, placeholder
    exits) belong to the caller's ``validity`` predicate, which keeps exactly
    one copy of those rules.
    """
    if not isinstance(row, dict):
        return False
    if row.get("paper_trade") or row.get("expired_no_pnl") or row.get("_auto_expired"):
        return False
    if _f(row.get("pnl_pct")) is None:
        return False
    exit_reason = str(row.get("exit_reason", "") or "").upper().strip()
    # "" and UNKNOWN are ABSENT INFORMATION, not a stated non-performance exit:
    # they are judged by the closure-evidence clause below. Every other denied
    # reason is an affirmative statement that the row is not a realised
    # outcome, and is a hard deny.
    if exit_reason not in _NO_EXIT_INFO and exit_reason in _NON_PERFORMANCE_EXITS:
        return False
    if exit_reason.startswith("STALE"):
        return False
    if exit_reason.startswith("RESOLVE_FAILED"):
        return False
    status = str(row.get("status", "") or "").upper().strip()
    if status in _NON_PERFORMANCE_STATUSES:
        return False
    # With no exit reason, the row must still be demonstrably closed: a close
    # marker, or a terminal status that can only be written after resolution.
    # Otherwise a numeric pnl with no exit information is a snapshot, not an
    # outcome — and counting it is how a "closed" book silently gains rows
    # that never closed.
    if exit_reason in _NO_EXIT_INFO:
        close_markers = (
            row.get("closed_at")
            or row.get("exit_timestamp")
            or row.get("exit_time_est")
            or row.get("exit_date")
        )
        if not close_markers and status not in _TERMINAL_STATUSES:
            return False
    return True


def cost_bps(asset_class: str | None, override: float | None = None) -> float:
    """Round-trip cost in bps for a class (explicit override wins)."""
    if isinstance(override, (int, float)):
        return float(override)
    return CLASS_COST_BPS.get(str(asset_class or "").upper(), DEFAULT_COST_BPS)


def _f(value: Any) -> float | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def dedupe_key(pick: dict) -> tuple:
    """Mirror-duplicate key — the same one the dashboard headline uses.

    Systems mirror the same trade into several feeds; counting each copy inflates
    win rate and PnL. Rows that collide on (symbol, direction, entry, pnl) are one
    economic trade.
    """
    return (
        str(pick.get("symbol", "")).upper(),
        str(pick.get("direction", "") or pick.get("signal_type", "")).upper()[:1],
        round(_f(pick.get("entry_price")) or 0.0, 6),
        round(_f(pick.get("pnl_pct")) or 0.0, 4),
    )


def default_exclusion_reason(pick: Any) -> str | None:
    """Cheap, self-contained reason classifier for rows the caller's predicate drops.

    The *decision* to keep a row belongs to the caller's ``validity`` predicate;
    this only names the cause so the published view can attribute the exclusion.
    It is deliberately coarser than the predicate: a row rejected for corrupt
    prices is reported as ``invalid_row`` rather than pretending to a precision
    this function does not have.
    """
    if not isinstance(pick, dict):
        return "not_a_record"
    # One decision, one place: the predicate below is the same function the
    # audit3 tribunal calls, so an exclusion reason can never describe a
    # different rule than the one that kept or dropped the row.
    if is_performance_scored_row(pick):
        return None
    if pick.get("paper_trade"):
        return "paper_trade"
    if pick.get("expired_no_pnl") or pick.get("_auto_expired"):
        return "auto_expired"
    if _f(pick.get("pnl_pct")) is None:
        return "no_numeric_pnl"
    exit_reason = str(pick.get("exit_reason", "") or "").upper().strip()
    if exit_reason in _NON_PERFORMANCE_EXITS or exit_reason.startswith("STALE"):
        return "non_performance_exit"
    if exit_reason.startswith("RESOLVE_FAILED"):
        return "resolver_breakeven_fallback"
    return "not_resolved"
    # None means "nothing visibly wrong with this row" — the caller's predicate may
    # still have rejected it for a reason this coarse classifier does not model
    # (corrupt prices, micro-hold, blocked symbol), and build_view attributes those
    # to "invalid_row" so they are never lost.
    return None


def canonical_row(pick: dict, *, strategy_cost_bps: dict | None = None) -> dict | None:
    """Project one resolved pick onto the canonical row shape."""
    gross = _f(pick.get("pnl_pct"))
    if gross is None:
        return None
    asset_class = str(pick.get("asset_class") or "").upper() or None
    strategy = str(pick.get("strategy") or pick.get("source_system") or "")
    override = (strategy_cost_bps or {}).get(f"{strategy.lower()}|{asset_class}")
    if override is None:
        override = (strategy_cost_bps or {}).get(strategy.lower())
    cost = cost_bps(asset_class, override)
    net = gross - cost / 100.0
    return {
        # Identity fields are kept deliberately: downstream loaders (audit3) dedupe
        # on `id` when present and otherwise on (symbol, direction, entry, pnl).
        # Dropping entry_price here collapsed 24 distinct trades out of 3,500 in an
        # end-to-end check, which is exactly the kind of silent denominator drift
        # this module exists to remove.
        "id": pick.get("id"),
        # Cross-system join key: the DB writes ids as v1::<writer>::<id> while this
        # view keeps the bare id, so an unnormalised join silently matches nothing
        # (2026-11-19: 0 of 230 MeanReversionBB rows joined). Consumers joining to
        # at_pick_outcomes.pick_id must key on this field.
        "join_key": pick_id_join_key(pick.get("id")),
        "entry_price": _f(pick.get("entry_price")),
        "symbol": str(pick.get("symbol") or ""),
        "asset_class": asset_class,
        "direction": str(pick.get("direction") or pick.get("signal_type") or "").upper(),
        "strategy": strategy,
        "source_system": str(pick.get("source_system") or ""),
        "closed_at": str(
            pick.get("closed_at") or pick.get("exit_timestamp")
            or pick.get("timestamp") or ""
        ),
        "exit_reason": str(pick.get("exit_reason") or ""),
        "pnl_gross_pct": round(gross, 6),
        "pnl_net_pct": round(net, 6),
        "cost_bps": round(cost, 4),
        "won": gross > FLAT_EPSILON_PCT,
        "lost": gross < -FLAT_EPSILON_PCT,
        # Kept so audit3's loader can consume the sidecar without a second adapter.
        "pnl_pct": round(gross, 6),
        "status": "WON" if gross > FLAT_EPSILON_PCT else ("LOST" if gross < -FLAT_EPSILON_PCT else "FLAT"),
    }


def build_view(
    picks: Iterable[dict],
    *,
    generated_at: str,
    validity: Callable[[dict], bool] | None = None,
    source: str | None = None,
    strategy_cost_bps: dict | None = None,
) -> dict[str, Any]:
    """Build the canonical view: kept rows + attributed exclusions + class rollup."""
    drops: Counter[str] = Counter()
    rows: list[dict] = []
    seen: set[tuple] = set()
    n_input = 0
    for pick in picks or []:
        n_input += 1
        if validity is not None and not validity(pick):
            drops[default_exclusion_reason(pick) or "invalid_row"] += 1
            continue
        key = dedupe_key(pick)
        if key in seen:
            drops["mirror_duplicate"] += 1
            continue
        seen.add(key)
        row = canonical_row(pick, strategy_cost_bps=strategy_cost_bps)
        if row is None:
            drops["no_numeric_pnl"] += 1
            continue
        rows.append(row)

    rows.sort(key=lambda r: r.get("closed_at") or "")
    blobs = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema": SCHEMA,
        "generated_at": generated_at,
        "source": source,
        # A1: the triple travels with the payload, so every tile derived from it
        # can name its population, cost model, and win definition.
        "provenance": provenance(),
        "counts": {
            "input_rows": n_input,
            "kept_rows": len(rows),
            "excluded_rows": n_input - len(rows),
            "excluded_by_reason": dict(sorted(drops.items())),
        },
        "classes": class_rollup(rows),
        "cost_model": {
            "kind": "measured_class_slippage_bps",
            "class_cost_bps": dict(sorted(CLASS_COST_BPS.items())),
            "default_cost_bps": DEFAULT_COST_BPS,
        },
        "rows_sha256": hashlib.sha256(blobs).hexdigest(),
        "rows_file": ROWS_FILENAME,
        "rows": rows,
    }


def class_rollup(rows: list[dict]) -> dict[str, dict]:
    """Per-class n / win rate / profit factor / mean gross and net, from the rows."""
    acc: dict[str, dict] = {}
    for r in rows:
        cls = r.get("asset_class") or "UNKNOWN"
        a = acc.setdefault(cls, {
            "n": 0, "wins": 0, "losses": 0, "flat": 0,
            "gross_sum": 0.0, "net_sum": 0.0,
            "gross_win_sum": 0.0, "gross_loss_sum": 0.0,
            "cost_bps_sum": 0.0,
        })
        a["n"] += 1
        a["gross_sum"] += r["pnl_gross_pct"]
        a["net_sum"] += r["pnl_net_pct"]
        a["cost_bps_sum"] += r["cost_bps"]
        if r["won"]:
            a["wins"] += 1
            a["gross_win_sum"] += r["pnl_gross_pct"]
        elif r["lost"]:
            a["losses"] += 1
            a["gross_loss_sum"] += r["pnl_gross_pct"]
        else:
            a["flat"] += 1

    out: dict[str, dict] = {}
    for cls, a in sorted(acc.items()):
        decided = a["wins"] + a["losses"]
        gross_pf = (a["gross_win_sum"] / abs(a["gross_loss_sum"])
                    if a["gross_loss_sum"] else None)
        out[cls] = {
            "n": a["n"],
            "wins": a["wins"],
            "losses": a["losses"],
            "flat": a["flat"],
            "win_rate_pct": round(100.0 * a["wins"] / decided, 2) if decided else None,
            "profit_factor": round(gross_pf, 4) if gross_pf is not None else None,
            "mean_gross_pct": round(a["gross_sum"] / a["n"], 4),
            "mean_net_pct": round(a["net_sum"] / a["n"], 4),
            "mean_cost_bps": round(a["cost_bps_sum"] / a["n"], 3),
        }
    return out


def coverage_statement(view: dict, summary: dict | None = None) -> str:
    """One sentence naming the denominator, for a page header."""
    counts = (view or {}).get("counts") or {}
    kept = int(counts.get("kept_rows") or 0)
    total = int(counts.get("input_rows") or 0)
    reasons = counts.get("excluded_by_reason") or {}
    summary = summary if isinstance(summary, dict) else {}

    def _s(key: str) -> int | None:
        v = summary.get(key)
        return int(v) if isinstance(v, (int, float)) else None

    book = _s("total_closed_picks") or total
    parts = "".join(
        f", {k.replace('_', ' ')} {v:,}" for k, v in reasons.items() if k != "mirror_duplicate"
    )
    dupes = int(reasons.get("mirror_duplicate") or 0)
    txt = (f"The canonical resolved book is {kept:,} rows"
           f" (from {book:,} closed records{parts}"
           + (f", mirror duplicates {dupes:,}" if dupes else "")
           + ").")
    if kept and book and book >= kept:
        txt += f" That is {100.0 * kept / book:.1f}% of the closed record set."
    txt += (" Every surface quoting a per-class number must say whether it used this view.")
    return txt


def write_view(path: str | Path, view: dict) -> Path:
    """Write the sidecar (rows included). Idempotent; returns the path written."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(view, fh, separators=(",", ":"))
        fh.write("\n")
    return out


def payload_block(view: dict) -> dict:
    """Everything except the rows — this is what goes inside dashboard_data.json."""
    block = {k: v for k, v in (view or {}).items() if k != "rows"}
    block["rows_count"] = len((view or {}).get("rows") or [])
    block["rows_embedded"] = False
    return block


def load_sidecar(payload_path: str | Path, block: dict | None = None
                 ) -> dict | None:
    """Load and verify the sidecar named by the payload block, or None.

    Returns None (never raises) when the sidecar is absent, unparseable, or its
    hash disagrees with the payload — a mismatched view must not be silently
    mixed with rows it does not describe.
    """
    base = Path(payload_path).resolve().parent
    block = block if isinstance(block, dict) else {}
    name = block.get("rows_file") or ROWS_FILENAME
    candidate = base / str(name)
    if not candidate.exists():
        return None
    try:
        with open(candidate, encoding="utf-8") as fh:
            view = json.load(fh)
    except Exception:
        return None
    if not isinstance(view, dict) or view.get("schema") != SCHEMA:
        return None
    expected = block.get("rows_sha256")
    if expected and view.get("rows_sha256") and expected != view.get("rows_sha256"):
        return None
    return view
