"""UEPS dashboard section renderer (Phases 10-11).

Opt-in sidecar (per CLAUDE.md Wire-Up Rule). Wiring plan: a future PR will
add `{include}` directive in audit_dashboard/template.html (deferred until
Copilot's BLOCKED_SYMBOLS purge merges to avoid conflict).

Renders a self-contained HTML block for the "US Equity Picks" section of the
audit dashboard, given a list of pick dicts produced by
`alpha_engine.value_screener.ValueScreener.screen_universe` and
`alpha_engine.swing_screener.SwingScreener.screen_universe`.

Spec source: `updates/long_term_value_project_2026-04-27/PROJECT.md` Phase 10/11
+ the ten card elements enumerated in the prompt brief which mirrors
SYNTHESIS § 5 ("Dashboard surface — locked"). When SYNTHESIS.md is committed
this docstring should be re-pointed at it.

Hard contract:
    * Pure stdlib. No jinja2, no flask. f-strings + html.escape are sufficient.
    * Every user-controlled string MUST be escaped with html.escape before it
      lands in HTML or HTML attributes.
    * Every aggregate stat (WR, PF, MDD, ...) MUST display its sample size n
      next to it. Renderer logs a warning AND inserts "(n=?)" placeholder if
      the caller forgets.
    * Tier badges follow PROJECT.md decision #4 / SYNTHESIS § 7 thresholds:
        Tier 1: WR >= 55%  AND PF >= 2.0 AND MDD <= 10% AND n >= 100
        Tier 2: WR >= 50%  AND PF >= 1.5 AND MDD <= 20% AND n >= 100
        Pre-tier ("Building (n=N/100)"): n < 100
    * LTCG warning: surfaces when 330 <= days_held <= 365 (US 1-year LTCG
      threshold).
"""
from __future__ import annotations

import html
import logging
from typing import Any, Iterable, Mapping

logger = logging.getLogger(__name__)


# Tier thresholds (locked per PROJECT.md decision #4 / SYNTHESIS section 7)

TIER1_WR = 0.55
TIER1_PF = 2.0
TIER1_MDD = 0.10
TIER2_WR = 0.50
TIER2_PF = 1.5
TIER2_MDD = 0.20
N_FLOOR = 100  # n>=100 to leave "Building (n=N/100)" pre-tier state

# LTCG bands (US tax)

LTCG_DAYS = 365
LTCG_WARN_BAND_DAYS = 35   # warn when within 35 days of LTCG threshold
LTCG_HARD_FLOOR_DAYS = LTCG_DAYS - LTCG_WARN_BAND_DAYS  # 330

# Fundamental colour thresholds (green/yellow/red)
# Inline rules - keep the dashboard self-explanatory. Each entry is the
# (green_floor, red_floor, higher_is_better) tuple. A None floor means "skip".
FUND_THRESHOLDS: dict[str, tuple[float | None, float | None, bool]] = {
    "pe":                    (15.0, 30.0, False),  # lower P/E is better
    "pb":                    (1.5,  3.5,  False),  # lower P/B is better
    "ev_ebitda":             (8.0,  16.0, False),
    "roic":                  (0.15, 0.05, True),   # >=15% green, <=5% red
    "roe":                   (0.15, 0.05, True),
    "fcf_yield":             (0.06, 0.02, True),
    "debt_to_equity":        (0.5,  1.5,  False),
    "interest_coverage":     (5.0,  2.0,  True),
    "piotroski_f":           (7.0,  4.0,  True),   # >=7 strong, <=4 weak
    "magic_formula_rank":    (50.0, 200.0, False),  # rank 1 = best
    "acquirers_multiple":    (8.0,  16.0, False),
    "altman_z_double_prime": (2.6,  1.1,  True),   # >=2.6 safe, <=1.1 distress
    "beneish_m":             (-2.22, -1.78, False),  # < -2.22 clean
}

FUND_LABEL: dict[str, str] = {
    "pe": "P/E",
    "pb": "P/B",
    "ev_ebitda": "EV/EBITDA",
    "roic": "ROIC",
    "roe": "ROE",
    "fcf_yield": "FCF Yield",
    "debt_to_equity": "D/E",
    "interest_coverage": "Int. Cov.",
    "piotroski_f": "F-Score",
    "magic_formula_rank": "Magic Formula Rank",
    "acquirers_multiple": "Acquirer's Mult.",
    "altman_z_double_prime": "Altman Z''",
    "beneish_m": "Beneish M",
}

# Order in which to render the fundamentals card.
FUND_ORDER: tuple[str, ...] = (
    "pe",
    "pb",
    "ev_ebitda",
    "roic",
    "roe",
    "fcf_yield",
    "debt_to_equity",
    "interest_coverage",
    "piotroski_f",
    "magic_formula_rank",
    "acquirers_multiple",
    "altman_z_double_prime",
    "beneish_m",
)


# Helpers


def _esc(value: Any) -> str:
    """HTML-escape any value (with None -> empty string)."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _esc_attr(value: Any) -> str:
    """Same as _esc but always quoted for attribute context."""
    return _esc(value)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _pct_str(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.{digits}f}%"


def _num_str(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def _classify_fundamental(key: str, value: float | None) -> str:
    """Return 'green' | 'yellow' | 'red' | 'unknown' for a fundamental key."""
    if value is None:
        return "unknown"
    rule = FUND_THRESHOLDS.get(key)
    if rule is None:
        return "unknown"
    green_floor, red_floor, higher_is_better = rule
    if green_floor is None or red_floor is None:
        return "unknown"
    if higher_is_better:
        if value >= green_floor:
            return "green"
        if value <= red_floor:
            return "red"
        return "yellow"
    # lower-is-better
    if value <= green_floor:
        return "green"
    if value >= red_floor:
        return "red"
    return "yellow"


# Tiny inline markdown renderer (no external deps)


def render_markdown_inline(text: str) -> str:
    """Render a tiny markdown subset to HTML. Safe-by-default: input is
    fully escaped first, then we *re-introduce* the supported tags by
    pattern-replacement on the escaped text. This means a user typing
    ``<script>`` in their thesis cannot smuggle a tag, because the brackets
    are already escaped to ``&lt;script&gt;`` before any markdown processing
    runs.

    Supported tokens (intentionally minimal):
        **bold**       -> <strong>bold</strong>
        *italic*       -> <em>italic</em>
        _italic_       -> <em>italic</em>
        `code`         -> <code>code</code>
        - list item    -> rendered as a <ul><li>
        * list item    -> rendered as a <ul><li>

    Newlines are preserved as <br> outside list contexts.
    """
    if text is None:
        return ""
    # First escape EVERYTHING. We do all subsequent regex on escaped text.
    escaped = html.escape(text, quote=True)

    # List handling - extremely small. We split on lines, gather adjacent
    # "- " or "* " items into a single <ul>.
    lines = escaped.split("\n")
    out: list[str] = []
    in_list = False
    for line in lines:
        stripped = line.lstrip()
        is_li = stripped.startswith("- ") or stripped.startswith("* ")
        if is_li:
            if not in_list:
                out.append("<ul class=\"ueps-md-list\">")
                in_list = True
            out.append(f"<li>{stripped[2:]}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(line)
    if in_list:
        out.append("</ul>")
    body = "\n".join(out)

    # Inline tokens. Order matters: do `code` first so its contents aren't
    # mis-parsed as italic.
    body = _replace_balanced(body, "`", "<code>", "</code>")
    body = _replace_balanced(body, "**", "<strong>", "</strong>")
    body = _replace_balanced(body, "_", "<em>", "</em>")
    body = _replace_balanced(body, "*", "<em>", "</em>")

    # Newlines (outside list lines, which already produced <li>) -> <br>.
    body = body.replace("\n", "<br>\n")
    return body


def _replace_balanced(
    text: str, marker: str, open_tag: str, close_tag: str
) -> str:
    """Replace pairs of ``marker`` with open/close tags. Unmatched markers
    are left intact. Pure string scan, no regex.
    """
    out: list[str] = []
    i = 0
    open_state = False
    n = len(text)
    m = len(marker)
    while i < n:
        if text[i : i + m] == marker:
            # peek for a closing marker later in the string
            if not open_state:
                # check that there's a matching close later, else leave
                rest = text.find(marker, i + m)
                if rest == -1:
                    out.append(text[i])
                    i += 1
                    continue
                out.append(open_tag)
                open_state = True
            else:
                out.append(close_tag)
                open_state = False
            i += m
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


# Tier badge


def classify_tier(
    wr: float | None,
    pf: float | None,
    mdd: float | None,
    n: int | None,
) -> str:
    """Return the tier label for a strategy track record.

    Returns one of: "Tier 1", "Tier 2", "Pre-tier", "Building (n=N/100)".
    """
    n_int = _safe_int(n)
    if n_int is None or n_int < N_FLOOR:
        if n_int is None:
            return "Building (n=?/100)"
        return f"Building (n={n_int}/100)"
    wr_f = _safe_float(wr) or 0.0
    pf_f = _safe_float(pf) or 0.0
    mdd_f = _safe_float(mdd)
    # MDD given as a positive fraction 0..1 (e.g. 0.08 = 8%).
    mdd_v = mdd_f if mdd_f is not None else 1.0
    if wr_f >= TIER1_WR and pf_f >= TIER1_PF and mdd_v <= TIER1_MDD:
        return "Tier 1"
    if wr_f >= TIER2_WR and pf_f >= TIER2_PF and mdd_v <= TIER2_MDD:
        return "Tier 2"
    return "Pre-tier"


def _badge_class(tier: str) -> str:
    if tier == "Tier 1":
        return "ueps-tier-badge tier1"
    if tier == "Tier 2":
        return "ueps-tier-badge tier2"
    if tier.startswith("Building"):
        return "ueps-tier-badge building"
    return "ueps-tier-badge pretier"


# Aggregate-stats validator


def render_aggregate_stat_block(
    aggregate_stats: Mapping[str, Any] | None,
    *,
    context: str = "",
) -> str:
    """Render a strategy-aggregate stats line (WR/PF/MDD/Sharpe with n=).

    Per CLAUDE.md MAJOR GOAL #1 + SYNTHESIS section 7, every aggregate stat MUST
    display ``n=value`` next to it. If `aggregate_stats` is missing the
    ``n`` key, this function logs a warning and inserts ``(n=?)``.
    """
    if aggregate_stats is None:
        return ""
    n_raw = aggregate_stats.get("n")
    n_int = _safe_int(n_raw)
    if n_int is None:
        logger.warning(
            "UEPS aggregate stats missing n= sample size%s; "
            "rendering '(n=?)' placeholder. Stats: %s",
            f" ({context})" if context else "",
            dict(aggregate_stats),
        )
        n_label = "n=?"
    else:
        n_label = f"n={n_int}"

    strategy = _esc(aggregate_stats.get("strategy", ""))
    wr = _safe_float(aggregate_stats.get("wr"))
    pf = _safe_float(aggregate_stats.get("pf"))
    mdd = _safe_float(aggregate_stats.get("mdd"))
    sharpe = _safe_float(aggregate_stats.get("sharpe"))

    tier = classify_tier(wr, pf, mdd, n_int)
    badge_class = _badge_class(tier)

    parts: list[str] = []
    parts.append(
        f'<div class="ueps-agg-stats" data-strategy="{_esc_attr(strategy)}">'
    )
    if strategy:
        parts.append(f'<span class="ueps-strategy-name">{strategy}</span>')
    parts.append(f'<span class="{badge_class}">{_esc(tier)}</span>')
    if wr is not None:
        parts.append(
            f'<span class="ueps-stat">WR {_pct_str(wr)} <em>({n_label})</em></span>'
        )
    if pf is not None:
        parts.append(
            f'<span class="ueps-stat">PF {_num_str(pf, 2)} <em>({n_label})</em></span>'
        )
    if mdd is not None:
        parts.append(
            f'<span class="ueps-stat">MDD {_pct_str(mdd)} <em>({n_label})</em></span>'
        )
    if sharpe is not None:
        parts.append(
            f'<span class="ueps-stat">Sharpe {_num_str(sharpe, 2)} <em>({n_label})</em></span>'
        )
    if (
        wr is None and pf is None and mdd is None and sharpe is None
        and not strategy
    ):
        # Caller passed something but it had no useful fields. Still surface
        # the n= for traceability.
        parts.append(f'<span class="ueps-stat"><em>({n_label})</em></span>')
    parts.append("</div>")
    return "".join(parts)


# Per-card sub-renderers


def _render_header(pick: Mapping[str, Any]) -> str:
    symbol = _esc(pick.get("symbol", ""))
    asset_class = _esc(pick.get("asset_class", "EQUITY"))
    pick_type = _esc(pick.get("pick_type", ""))
    horizon = _esc(pick.get("holding_horizon", ""))
    days_held = _safe_int(pick.get("days_held"))
    days_held_label = (
        f"day {days_held}" if days_held is not None else "day 0"
    )
    return (
        '<div class="ueps-card-header">'
        f'<span class="ueps-ticker">{symbol}</span>'
        f'<span class="ueps-asset-class">{asset_class}</span>'
        f'<span class="ueps-pick-type">{pick_type}</span>'
        f'<span class="ueps-horizon">{horizon}</span>'
        f'<span class="ueps-days-held">{_esc(days_held_label)}</span>'
        "</div>"
    )


def _render_thesis_block(pick: Mapping[str, Any]) -> str:
    thesis = pick.get("thesis", "") or ""
    if not thesis:
        return ""
    rendered = render_markdown_inline(thesis)
    return (
        '<div class="ueps-thesis-block">'
        '<h4 class="ueps-section-title">Thesis</h4>'
        f'<div class="ueps-thesis-body">{rendered}</div>'
        "</div>"
    )


def _render_fundamental_snapshot(pick: Mapping[str, Any]) -> str:
    snap = pick.get("fundamental_snapshot") or {}
    if not isinstance(snap, Mapping) or not snap:
        return ""
    rows: list[str] = []
    for key in FUND_ORDER:
        if key not in snap:
            continue
        value = _safe_float(snap.get(key))
        cls = _classify_fundamental(key, value)
        label = _esc(FUND_LABEL.get(key, key))
        # Values: percent for some keys, raw for the rest.
        if key in {"roic", "roe", "fcf_yield"}:
            display = _pct_str(value, 1)
        elif key == "piotroski_f":
            iv = _safe_int(value)
            display = f"{iv}/9" if iv is not None else "n/a"
        elif key == "magic_formula_rank":
            iv = _safe_int(value)
            display = f"#{iv}" if iv is not None else "n/a"
        elif key == "beneish_m":
            display = _num_str(value, 2)
        else:
            display = _num_str(value, 2)
        green_floor, red_floor, higher = (
            FUND_THRESHOLDS.get(key) or (None, None, True)
        )
        rows.append(
            f'<div class="ueps-fund-row {cls}" '
            f'data-key="{_esc_attr(key)}" '
            f'data-green-floor="{_esc_attr(green_floor)}" '
            f'data-red-floor="{_esc_attr(red_floor)}" '
            f'data-higher-is-better="{str(higher).lower()}">'
            f'<span class="ueps-fund-label">{label}</span>'
            f'<span class="ueps-fund-value">{_esc(display)}</span>'
            "</div>"
        )
    if not rows:
        return ""
    return (
        '<div class="ueps-fundamentals">'
        '<h4 class="ueps-section-title">Fundamental Snapshot</h4>'
        '<div class="ueps-fund-grid">' + "".join(rows) + "</div>"
        "</div>"
    )


def _render_earnings_history(pick: Mapping[str, Any]) -> str:
    history = pick.get("earnings_history") or []
    if not isinstance(history, list) or not history:
        return ""
    rows: list[str] = []
    # Last 8 quarters (oldest first or newest first - we just show as supplied,
    # truncated to 8 entries from the end so most-recent always wins).
    history_view = list(history)[-8:]
    for row in history_view:
        if not isinstance(row, Mapping):
            continue
        date_str = _esc(row.get("date", ""))
        actual = _safe_float(row.get("eps_actual"))
        estimate = _safe_float(row.get("eps_estimate"))
        surprise = _safe_float(row.get("surprise_pct"))
        cls = ""
        if surprise is not None:
            if surprise > 0:
                cls = "beat"
            elif surprise < 0:
                cls = "miss"
        if surprise is None:
            surprise_disp = "n/a"
        else:
            surprise_disp = f"{surprise:+.2f}%"
        rows.append(
            f'<tr class="{cls}">'
            f'<td>{date_str}</td>'
            f'<td>{_esc(_num_str(actual, 2))}</td>'
            f'<td>{_esc(_num_str(estimate, 2))}</td>'
            f'<td>{_esc(surprise_disp)}</td>'
            "</tr>"
        )
    if not rows:
        return ""
    return (
        '<div class="ueps-earnings-history">'
        '<h4 class="ueps-section-title">Earnings History</h4>'
        '<table class="ueps-earnings-table">'
        '<thead><tr><th>Quarter</th><th>EPS Actual</th><th>EPS Est.</th><th>Surprise</th></tr></thead>'
        '<tbody>' + "".join(rows) + '</tbody>'
        "</table></div>"
    )


def _render_next_earnings_and_tax(pick: Mapping[str, Any]) -> str:
    next_date = pick.get("next_earnings_date")
    days_held = _safe_int(pick.get("days_held"))
    parts: list[str] = []

    if next_date:
        parts.append(
            '<div class="ueps-next-earnings" '
            f'data-next-earnings-date="{_esc_attr(next_date)}">'
            '<h4 class="ueps-section-title">Next Earnings</h4>'
            f'<span class="ueps-next-date">{_esc(next_date)}</span>'
            '<span class="ueps-countdown" data-countdown-target="'
            f'{_esc_attr(next_date)}">computing...</span>'
            "</div>"
        )

    # LTCG tax warning: surface from 330-365+ days held.
    if days_held is not None and days_held >= LTCG_HARD_FLOOR_DAYS:
        days_to_ltcg = max(0, LTCG_DAYS - days_held)
        if days_held >= LTCG_DAYS:
            msg = (
                f"LTCG threshold reached (held {days_held}d). "
                "Selling now qualifies for long-term capital gains rates."
            )
            sev = "ok"
        else:
            msg = (
                f"LTCG warning: {days_to_ltcg} day(s) until 1-year LTCG "
                "(US tax). Holding past 365 days may save material tax. "
                f"Currently held {days_held} day(s)."
            )
            sev = "warn"
        parts.append(
            f'<div class="ueps-tax-banner ueps-tax-{sev}">'
            f'<strong>LTCG:</strong> {_esc(msg)}'
            "</div>"
        )
    return "".join(parts)


def _render_dividend_record(pick: Mapping[str, Any]) -> str:
    rec = pick.get("dividend_record") or {}
    if not isinstance(rec, Mapping) or not rec:
        return ""
    annual_yield = _safe_float(rec.get("annual_yield"))
    payout = _safe_float(rec.get("payout_ratio"))
    growth_yrs = _safe_int(rec.get("consecutive_growth_years"))
    next_ex = rec.get("next_ex_div_date")
    history = rec.get("history_5y") or []

    rows: list[str] = ['<div class="ueps-dividend">']
    rows.append('<h4 class="ueps-section-title">Dividend Record</h4>')
    rows.append('<div class="ueps-div-grid">')
    if annual_yield is not None:
        rows.append(
            f'<div class="ueps-div-cell"><span>Yield</span>'
            f'<strong>{_pct_str(annual_yield, 2)}</strong></div>'
        )
    if payout is not None:
        rows.append(
            f'<div class="ueps-div-cell"><span>Payout</span>'
            f'<strong>{_pct_str(payout, 1)}</strong></div>'
        )
    if growth_yrs is not None:
        rows.append(
            f'<div class="ueps-div-cell"><span>Cons. Growth</span>'
            f'<strong>{growth_yrs}y</strong></div>'
        )
    if next_ex:
        rows.append(
            f'<div class="ueps-div-cell"><span>Next Ex-Div</span>'
            f'<strong>{_esc(next_ex)}</strong></div>'
        )
    rows.append("</div>")

    # Inline 5y dividend sparkline (SVG)
    if isinstance(history, list) and len(history) > 0:
        amounts: list[float] = []
        for ev in history:
            if isinstance(ev, Mapping):
                a = _safe_float(ev.get("amount"))
                if a is not None:
                    amounts.append(a)
        if amounts:
            rows.append(_render_dividend_sparkline(amounts))
    rows.append("</div>")
    return "".join(rows)


def _render_dividend_sparkline(amounts: list[float]) -> str:
    """Render an inline SVG sparkline for the 5y dividend history."""
    if not amounts:
        return ""
    width = 160
    height = 32
    n = len(amounts)
    if n == 1:
        # Single-bar fallback so we still emit a valid SVG.
        return (
            f'<svg class="ueps-div-sparkline" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" '
            'role="img" aria-label="Dividend history sparkline">'
            f'<rect x="0" y="0" width="{width}" height="{height}" '
            'fill="rgba(96,165,250,0.15)" />'
            f'<line x1="0" y1="{height // 2}" x2="{width}" '
            f'y2="{height // 2}" stroke="#60a5fa" stroke-width="2" />'
            "</svg>"
        )
    lo = min(amounts)
    hi = max(amounts)
    span = (hi - lo) or 1.0
    pts: list[str] = []
    for i, v in enumerate(amounts):
        x = (i / (n - 1)) * width
        y = height - ((v - lo) / span) * height
        pts.append(f"{x:.2f},{y:.2f}")
    polyline = " ".join(pts)
    return (
        f'<svg class="ueps-div-sparkline" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" '
        'role="img" aria-label="Dividend history sparkline">'
        '<polyline fill="none" stroke="#60a5fa" stroke-width="2" '
        f'points="{polyline}" />'
        "</svg>"
    )


def _render_technical_state(pick: Mapping[str, Any]) -> str:
    extra = pick.get("extra") or {}
    tech = extra.get("technical_state") if isinstance(extra, Mapping) else None
    if not isinstance(tech, Mapping):
        # Placeholder values per spec - show "n/a" but render the row so the
        # layout is stable across picks.
        tech = {}
    px = _safe_float(tech.get("price")) or _safe_float(pick.get("entry_price"))
    ema50 = _safe_float(tech.get("ema_50"))
    rsi = _safe_float(tech.get("rsi"))
    support = _safe_float(tech.get("support"))
    resistance = _safe_float(tech.get("resistance"))
    px_vs_ema = (
        f"{(px / ema50 - 1) * 100:+.1f}% vs 50-EMA"
        if px is not None and ema50 not in (None, 0)
        else "n/a"
    )
    return (
        '<div class="ueps-technical">'
        '<h4 class="ueps-section-title">Technical State</h4>'
        '<div class="ueps-tech-grid">'
        f'<div><span>Px vs 50-EMA</span><strong>{_esc(px_vs_ema)}</strong></div>'
        f'<div><span>RSI</span><strong>{_esc(_num_str(rsi, 1))}</strong></div>'
        f'<div><span>Support</span><strong>{_esc(_num_str(support, 2))}</strong></div>'
        f'<div><span>Resistance</span><strong>{_esc(_num_str(resistance, 2))}</strong></div>'
        "</div></div>"
    )


def _render_thesis_break_status(pick: Mapping[str, Any]) -> str:
    if pick.get("pick_type") != "long_term_value":
        return ""
    rules = pick.get("thesis_break_rules") or []
    extra = pick.get("extra")
    current = extra.get("current_metrics") if isinstance(extra, Mapping) else None
    if not isinstance(rules, list) or not rules:
        return ""
    rows: list[str] = []
    op_map = {
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "==": lambda a, b: a == b,
    }
    for rule in rules:
        if not isinstance(rule, Mapping):
            continue
        metric = rule.get("metric", "")
        op = rule.get("op", "")
        threshold = _safe_float(rule.get("threshold"))
        cur_val = None
        if isinstance(current, Mapping):
            cur_val = _safe_float(current.get(metric))
        # PASS = thesis NOT broken; FAIL = thesis-break rule HAS triggered.
        triggered = False
        if cur_val is not None and threshold is not None and op in op_map:
            triggered = op_map[op](cur_val, threshold)
        state = "FAIL" if triggered else "PASS"
        cls = "fail" if triggered else "pass"
        cur_label = _num_str(cur_val, 4) if cur_val is not None else "-"
        rows.append(
            f'<tr class="{cls}">'
            f'<td>{_esc(metric)}</td>'
            f'<td>{_esc(op)} {_esc(_num_str(threshold, 4))}</td>'
            f'<td>{_esc(cur_label)}</td>'
            f'<td><span class="ueps-rule-state {cls}">{state}</span></td>'
            "</tr>"
        )
    if not rows:
        return ""
    return (
        '<div class="ueps-thesis-break">'
        '<h4 class="ueps-section-title">Thesis-Break Status</h4>'
        '<table class="ueps-thesis-table">'
        '<thead><tr><th>Metric</th><th>Rule</th><th>Current</th><th>State</th></tr></thead>'
        '<tbody>' + "".join(rows) + "</tbody>"
        "</table></div>"
    )


def _render_iv_progress(pick: Mapping[str, Any]) -> str:
    if pick.get("pick_type") != "long_term_value":
        return ""
    entry = _safe_float(pick.get("entry_price"))
    current = _safe_float(pick.get("current_price"))
    iv = _safe_float(pick.get("intrinsic_value"))
    if entry is None or iv is None or iv <= entry:
        return ""
    if current is None:
        current = entry
    span = iv - entry
    progress = (current - entry) / span
    progress = max(0.0, min(1.0, progress))
    pct = progress * 100
    return (
        '<div class="ueps-iv-progress">'
        '<h4 class="ueps-section-title">Intrinsic-Value Progress</h4>'
        '<div class="ueps-iv-bar">'
        f'<div class="ueps-iv-fill" style="width:{pct:.1f}%"></div>'
        "</div>"
        '<div class="ueps-iv-labels">'
        f'<span>Entry: {_esc(_num_str(entry, 2))}</span>'
        f'<span>Current: {_esc(_num_str(current, 2))}</span>'
        f'<span>IV Target: {_esc(_num_str(iv, 2))}</span>'
        "</div></div>"
    )


def _render_position_breadcrumb(pick: Mapping[str, Any]) -> str:
    extra = pick.get("extra") or {}
    target = (
        _safe_float(extra.get("target_position_pct"))
        if isinstance(extra, Mapping) else None
    )
    current = (
        _safe_float(extra.get("current_position_pct"))
        if isinstance(extra, Mapping) else None
    )
    target_label = _pct_str(target, 2) if target is not None else "n/a"
    current_label = _pct_str(current, 2) if current is not None else "0.00%"
    return (
        '<div class="ueps-position">'
        '<span class="ueps-position-label">Position:</span> '
        f'<span class="ueps-position-current">{_esc(current_label)}</span>'
        ' / '
        f'<span class="ueps-position-target">target {_esc(target_label)}</span>'
        "</div>"
    )


def _render_swing_targets(pick: Mapping[str, Any]) -> str:
    if pick.get("pick_type") != "swing":
        return ""
    entry = _safe_float(pick.get("entry_price"))
    tp = _safe_float(pick.get("take_profit"))
    sl = _safe_float(pick.get("stop_loss"))
    if entry is None or tp is None or sl is None:
        return ""
    if entry == sl:
        rr_label = "n/a"
    else:
        rr = abs(tp - entry) / abs(entry - sl)
        rr_label = f"{rr:.2f}:1"
    return (
        '<div class="ueps-swing-targets">'
        '<h4 class="ueps-section-title">Swing Targets</h4>'
        f'<div><span>Entry</span><strong>{_esc(_num_str(entry, 2))}</strong></div>'
        f'<div><span>TP</span><strong>{_esc(_num_str(tp, 2))}</strong></div>'
        f'<div><span>SL</span><strong>{_esc(_num_str(sl, 2))}</strong></div>'
        f'<div><span>R:R</span><strong>{_esc(rr_label)}</strong></div>'
        "</div>"
    )


# Top-level pick card


def render_pick_card(
    pick: Mapping[str, Any],
    aggregate_stats: Mapping[str, Any] | None = None,
) -> str:
    """Render a single pick as a card. The 10 elements per SYNTHESIS section 5
    are emitted unconditionally - sections that lack data render an empty
    string rather than malformed HTML, so the layout is stable.
    """
    if pick is None:
        return ""

    symbol = _esc(pick.get("symbol", ""))
    pick_type = _esc(pick.get("pick_type", ""))

    sections: list[str] = []
    sections.append(_render_header(pick))
    sections.append(_render_thesis_block(pick))
    sections.append(_render_fundamental_snapshot(pick))
    sections.append(_render_earnings_history(pick))
    sections.append(_render_next_earnings_and_tax(pick))
    sections.append(_render_dividend_record(pick))
    sections.append(_render_technical_state(pick))
    sections.append(_render_thesis_break_status(pick))
    sections.append(_render_iv_progress(pick))
    sections.append(_render_swing_targets(pick))
    if aggregate_stats is not None:
        sections.append(
            render_aggregate_stat_block(
                aggregate_stats,
                context=f"{symbol or 'pick'} aggregate",
            )
        )
    sections.append(_render_position_breadcrumb(pick))

    return (
        f'<article class="ueps-pick-card" '
        f'data-symbol="{_esc_attr(symbol)}" '
        f'data-pick-type="{_esc_attr(pick_type)}">'
        + "".join(sections)
        + "</article>"
    )


# Empty-state placeholder


def render_empty_state(tab_label: str) -> str:
    return (
        '<div class="ueps-empty-state">'
        f'<p>Building track record for <strong>{_esc(tab_label)}</strong>. '
        "No picks emitted yet - the screener has not yet produced "
        "n&ge;100 closed trades.</p>"
        "<p>This tab will populate once the weekly/daily screener "
        "writes its first batch of picks. See "
        "<code>updates/long_term_value_project_2026-04-27/PROJECT.md</code>"
        " for status.</p>"
        "</div>"
    )


# Main: full UEPS section renderer


def render_ueps_section(
    picks: Iterable[Mapping[str, Any]] | None = None,
    aggregate_stats_by_strategy: Mapping[str, Mapping[str, Any]] | None = None,
) -> str:
    """Render the entire ``US Equity Picks`` section as an HTML fragment.

    Args:
        picks: list of pick dicts produced by ValueScreener / SwingScreener,
            optionally augmented with ``status`` (ACTIVE vs CLOSED),
            ``days_held``, and ``current_price``.
        aggregate_stats_by_strategy: optional map {strategy: {wr, pf, mdd,
            sharpe, n}} that the renderer surfaces per-pick when the pick's
            ``strategy`` field matches a key.
    """
    picks_list: list[Mapping[str, Any]] = list(picks or [])
    agg_map = aggregate_stats_by_strategy or {}

    # Bucket picks by tab
    long_term: list[Mapping[str, Any]] = []
    swing: list[Mapping[str, Any]] = []
    closed: list[Mapping[str, Any]] = []
    for p in picks_list:
        if not isinstance(p, Mapping):
            continue
        status = str(p.get("status", "ACTIVE")).upper()
        if status == "CLOSED":
            closed.append(p)
            continue
        pt = p.get("pick_type")
        if pt == "long_term_value":
            long_term.append(p)
        elif pt == "swing":
            swing.append(p)
        else:
            # Unknown pick types we keep visible under the closed tab so they
            # don't silently disappear; helps debug data drift.
            closed.append(p)

    def _render_pick_list(
        items: list[Mapping[str, Any]], tab_label: str
    ) -> str:
        if not items:
            return render_empty_state(tab_label)
        cards = []
        for p in items:
            strategy = p.get("strategy", "")
            agg = agg_map.get(strategy) if strategy else None
            cards.append(render_pick_card(p, aggregate_stats=agg))
        return "<div class=\"ueps-pick-grid\">" + "".join(cards) + "</div>"

    inner = (
        '<div class="ueps-section" id="ueps-section" '
        'data-rendered-by="audit_dashboard.ueps_section_renderer">'
        '<h2 class="ueps-section-heading">US Equity Picks</h2>'
        '<div class="ueps-tab-bar" role="tablist">'
        '<button class="ueps-tab active" data-tab="long-term" '
        'role="tab" aria-selected="true">Long-Term Value Holds</button>'
        '<button class="ueps-tab" data-tab="swing" role="tab" '
        'aria-selected="false">Swing Plays</button>'
        '<button class="ueps-tab" data-tab="closed" role="tab" '
        'aria-selected="false">Closed Holds</button>'
        "</div>"
        '<div class="ueps-tab-panel active" data-panel="long-term">'
        f"{_render_pick_list(long_term, 'Long-Term Value Holds')}"
        "</div>"
        '<div class="ueps-tab-panel" data-panel="swing" hidden>'
        f"{_render_pick_list(swing, 'Swing Plays')}"
        "</div>"
        '<div class="ueps-tab-panel" data-panel="closed" hidden>'
        f"{_render_pick_list(closed, 'Closed Holds')}"
        "</div>"
        "</div>"
    )
    return inner


__all__ = [
    "TIER1_WR",
    "TIER1_PF",
    "TIER1_MDD",
    "TIER2_WR",
    "TIER2_PF",
    "TIER2_MDD",
    "N_FLOOR",
    "LTCG_DAYS",
    "LTCG_HARD_FLOOR_DAYS",
    "FUND_THRESHOLDS",
    "FUND_LABEL",
    "FUND_ORDER",
    "classify_tier",
    "render_aggregate_stat_block",
    "render_markdown_inline",
    "render_pick_card",
    "render_empty_state",
    "render_ueps_section",
]
