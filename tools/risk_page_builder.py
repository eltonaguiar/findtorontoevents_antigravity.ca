#!/usr/bin/env python3
"""Build reports/risk_metrics_live.json and audit_dashboard/risk_management.html.

Applies the risk methodologies the repo already contains but never surfaces:
tail risk (VaR/CVaR), risk-adjusted return (Sharpe/Sortino/PSR), drawdown
(max DD / Calmar / Ulcer), position sizing (fractional Kelly, risk parity),
Monte-Carlo risk of ruin, and concentration (HHI).

Rules this file follows, deliberately:
  * Every metric carries its n and the window it was measured on.
  * A metric whose sample is inadequate renders INSUFFICIENT, not a number.
  * Fund history shorter than 300 months is flagged: it excludes 2008, so its
    "always positive over 5y" numbers are survivorship, not probability.
  * The ledger headline is labelled INCOMPLETE when censored_pct > 20%.

Usage:
    python3 tools/risk_page_builder.py --payload /tmp/dd_live.json
    python3 tools/risk_page_builder.py --payload https://findtorontoevents.ca/audit/data/dashboard_data.json
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (compatible; risk-page-builder/1.0)"}
MIN_FUND_MONTHS = 300  # < 25y excludes 2008 -> survivorship regime
MIN_LEDGER_N = 200
CENSORED_LIMIT = 20.0


# ------------------------------------------------------------------ helpers
def load(src: str) -> dict:
    if src.startswith(("http://", "https://")):
        req = urllib.request.Request(src, headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    return json.loads(Path(src).read_text(encoding="utf-8"))


def monthly_history(symbol: str, rng: str = "max") -> list[tuple[str, float]]:
    """[(YYYY-MM, close)] oldest first."""
    u = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.parse.quote(symbol)}?range={rng}&interval=1mo"
    )
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read().decode())
    res = (j.get("chart") or {}).get("result") or []
    if not res:
        return []
    r0 = res[0]
    ts = r0.get("timestamp") or []
    q = ((r0.get("indicators") or {}).get("quote") or [{}])[0]
    closes = q.get("close") or []
    out = []
    for i, t in enumerate(ts):
        if i < len(closes) and closes[i] is not None:
            out.append((datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m"), closes[i]))
    return out


def pf(xs: list[float]) -> float | None:
    g = sum(x for x in xs if x > 0)
    l = -sum(x for x in xs if x < 0)
    return (g / l) if l else None


def cvar(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    k = max(1, int(len(s) * (1 - q)))
    return statistics.mean(s[:k])


def sortino(xs: list[float], target: float = 0.0) -> float | None:
    if not xs:
        return None
    dn = [min(0.0, x - target) for x in xs]
    dd = math.sqrt(sum(v * v for v in dn) / len(dn))
    return ((statistics.mean(xs) - target) / dd) if dd else None


def equity_path(returns: list[float]) -> tuple[float, float]:
    """Compound per-period % returns into an equity path.

    Returns (terminal_pct_change, max_drawdown_pct). Compounding is the only
    correct construction here: summing monthly percentages produced impossible
    values (QQQ "-140% drawdown") because percentages do not add across periods.
    """
    eq = peak = 1.0
    mdd = 0.0
    for x in returns:
        eq *= 1 + x / 100.0
        peak = max(peak, eq)
        if peak > 0:
            mdd = min(mdd, eq / peak - 1)
    return (eq - 1) * 100.0, max(mdd * 100.0, -100.0)


def ulcer_index(returns: list[float]) -> float:
    eq = peak = 0.0
    acc = []
    for x in returns:
        eq += x
        peak = max(peak, eq)
        acc.append((eq - peak) ** 2)
    return math.sqrt(sum(acc) / len(acc)) if acc else 0.0


def kelly(win_rate: float, avg_win: float, avg_loss: float) -> float | None:
    """Full Kelly fraction for a binary bet. Negative => do not bet."""
    if avg_loss == 0 or avg_win == 0:
        return None
    b = abs(avg_win / avg_loss)  # payoff ratio
    p = win_rate
    return (p * b - (1 - p)) / b


def risk_of_ruin(win_rate: float, avg_win: float, avg_loss: float,
                 n: int = 200, paths: int = 2000, ruin_at: float = 0.5) -> float:
    ruined = 0
    for _ in range(paths):
        eq = 1.0
        for _ in range(n):
            eq *= 1 + (avg_win if random.random() < win_rate else avg_loss) / 100.0
            if eq <= ruin_at:
                ruined += 1
                break
    return 100.0 * ruined / paths


def base_rates(closes: list[float], months: int) -> dict | None:
    out = []
    for i in range(len(closes) - months):
        a, b = closes[i], closes[i + months]
        if a:
            out.append((b / a - 1) * 100)
    if not out:
        return None
    return {
        "n_windows": len(out),
        "pct_positive": round(100 * sum(1 for x in out if x > 0) / len(out), 1),
        "median_pct": round(statistics.median(out), 2),
        "worst_pct": round(min(out), 2),
        "best_pct": round(max(out), 2),
    }


# ------------------------------------------------------------------ compute
def ledger_block(d: dict) -> dict:
    picks = d.get("picks") or {}
    closed = [r for r in (picks.get("recent_closed") or [])
              if isinstance(r.get("pnl_pct"), (int, float))]
    closed.sort(key=lambda r: str(r.get("closed_at") or ""))
    ret = [float(r["pnl_pct"]) for r in closed]
    raw = picks.get("active_raw") or []
    censored = 100.0 * sum(1 for r in raw if r.get("current_price") in (None, "")) / max(1, len(raw))
    wins = [x for x in ret if x > 0]
    losses = [x for x in ret if x < 0]
    wr = len(wins) / len(ret) if ret else 0.0
    avg_w = statistics.mean(wins) if wins else 0.0
    avg_l = statistics.mean(losses) if losses else 0.0
    mean = statistics.mean(ret) if ret else 0.0
    sd = statistics.pstdev(ret) if len(ret) > 1 else 0.0
    k = kelly(wr, avg_w, avg_l)
    em = Counter(str(r.get("system") or r.get("strategy")) for r in closed)
    hhi = sum((c / len(closed)) ** 2 for c in Counter(r.get("asset_class") for r in closed).values()) if closed else None
    return {
        "n": len(ret),
        "n_sufficient": len(ret) >= MIN_LEDGER_N,
        "win_rate_pct": round(wr * 100, 2),
        "profit_factor": round(pf(ret), 3) if pf(ret) else None,
        "mean_pct_per_trade": round(mean, 3),
        "median_pct_per_trade": round(statistics.median(ret), 3) if ret else None,
        "stdev_pct": round(sd, 3),
        "mean_over_sd": round(mean / sd, 3) if sd else None,
        "note_mean_over_sd": "not annualised; per-trade ratio only",
        "sortino_per_trade": round(sortino(ret), 3) if sortino(ret) is not None else None,
        "cvar_95_pct": round(cvar(ret, 0.95), 2),
        "cvar_99_pct": round(cvar(ret, 0.99), 2),
        "skew": round(sum(((x - mean) / sd) ** 3 for x in ret) / len(ret), 3) if sd else None,
        "max_drawdown_pct_compounded": round(equity_path(ret)[1], 1),
        "compounded_terminal_pct": round(equity_path(ret)[0], 2),
        "ulcer_index": round(ulcer_index(ret), 2),
        "kelly_fraction": round(k, 4) if k is not None else None,
        "kelly_action": "DO NOT BET (negative edge)" if (k is not None and k <= 0) else "size at 1/4 Kelly cap",
        "avg_win_pct": round(avg_w, 3),
        "avg_loss_pct": round(avg_l, 3),
        "payoff_ratio": round(abs(avg_w / avg_l), 3) if avg_l else None,
        "mc_risk_of_ruin_pct_200_trades": round(risk_of_ruin(wr, avg_w, avg_l), 1),
        "concentration_hhi_class": round(hhi, 3) if hhi is not None else None,
        "top_emitters": em.most_common(3),
        "top_emitter_share_pct": round(100 * em.most_common(1)[0][1] / len(closed), 1) if em and closed else None,
        "censored_pct": round(censored, 1),
        "headline_status": "INCOMPLETE" if censored > CENSORED_LIMIT else "OK",
        "caveats": [
            "includes rows the validator flags as FABRICATED_FLAT: exit_price is not the close on its own exit date",
            "censored_pct is the share of open positions with no market price",
            "max drawdown is compounded; at a negative mean the path tends to -100% by construction",
        ],
    }


def fund_block(symbols: list[tuple[str, str]]) -> tuple[dict, dict | None]:
    funds = {}
    for sym, label in symbols:
        try:
            hist = monthly_history(sym)
            if not hist:
                funds[sym] = {"label": label, "error": "no history"}
                continue
            closes = [c for _, c in hist]
            months = len(closes)
            mret = [(closes[i + 1] / closes[i] - 1) * 100 for i in range(months - 1)]
            cagr = ((closes[-1] / closes[0]) ** (12 / months) - 1) * 100
            sd_m = statistics.pstdev(mret) if len(mret) > 1 else 0.0
            funds[sym] = {
                "label": label,
                "first_obs": hist[0][0],
                "last_obs": hist[-1][0],
                "months": months,
                "cagr_pct": round(cagr, 2),
                "ann_vol_pct": round(sd_m * math.sqrt(12), 2),
                "sharpe": round((statistics.mean(mret) * 12) / (sd_m * math.sqrt(12)), 2) if sd_m else None,
                "sortino_annual": round(sortino(mret) * math.sqrt(12), 2) if sortino(mret) is not None else None,
                "max_dd_pct": round(equity_path(mret)[1], 1),
                "cvar_95_monthly_pct": round(cvar(mret, 0.95), 2),
                "price_only_series": True,
                "price_only_note": (
                    "Yahoo monthly closes exclude distributions: bond funds pay most of their "
                    "return as income, so AGG-type CAGR and hit rates are understated; equity "
                    "CAGR is understated by roughly the dividend yield (~1.3-2%/yr)"
                ),
                "survivorship_warning": months < MIN_FUND_MONTHS,
                "survivorship_note": (
                    f"only {months} months of history: excludes 2008 and other pre-inception drawdowns, "
                    "so long-horizon 'always positive' figures are regime-specific"
                ) if months < MIN_FUND_MONTHS else "",
                "win_12m": base_rates(closes, 12),
                "win_60m": base_rates(closes, 60),
                "win_120m": base_rates(closes, 120),
            }
        except Exception as e:  # noqa: BLE001
            funds[sym] = {"label": label, "error": f"{type(e).__name__}: {e}"}

    fee = None
    spy = funds.get("SPY") or {}
    if spy.get("cagr_pct") is not None:
        g = spy["cagr_pct"] / 100
        n = 20
        cheap = (1 + g - 0.0003) ** n
        dear = (1 + g - 0.0060) ** n
        fee = {
            "base": "SPY measured CAGR",
            "base_cagr_pct": spy["cagr_pct"],
            "horizon_years": n,
            "growth_0.03pct_fee": round(cheap, 3),
            "growth_0.60pct_fee": round(dear, 3),
            "terminal_value_lost_pct": round(100 * (1 - dear / cheap), 2),
            "note": "same portfolio, same return, different fee: the only certain number in the table",
        }
    return funds, fee


# --------------------------------------------------------------------- page
CSS = """
:root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--fg:#e6edf3;--dim:#8b949e;
--red:#f85149;--amb:#d29922;--grn:#3fb950;--blu:#58a6ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;padding:28px}
h1{font-size:20px;margin:0 0 4px}h2{font-size:15px;margin:28px 0 8px;color:var(--blu);
border-bottom:1px solid var(--line);padding-bottom:6px}
.sub{color:var(--dim);font-size:12px;margin-bottom:18px}
table{border-collapse:collapse;width:100%;margin:8px 0 4px;font-size:13px}
th,td{text-align:left;padding:5px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--dim);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.04em}
.badge{display:inline-block;padding:1px 7px;border-radius:10px;font-size:11px;font-weight:700}
.bad{background:rgba(248,81,73,.15);color:var(--red);border:1px solid var(--red)}
.warn{background:rgba(210,153,34,.15);color:var(--amb);border:1px solid var(--amb)}
.good{background:rgba(63,185,80,.15);color:var(--grn);border:1px solid var(--grn)}
.na{color:var(--dim);font-style:italic}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin:10px 0}
.note{color:var(--dim);font-size:12px;margin:4px 0 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.kpi .k{color:var(--dim);font-size:11px;text-transform:uppercase}
.kpi .v{font-size:19px;font-weight:700;margin-top:2px}
code{background:#21262d;padding:1px 5px;border-radius:4px;font-size:12px}
"""


def fnum(v, suffix="", digits=2, dash="—"):
    if v is None:
        return f'<span class="na">{dash}</span>'
    if isinstance(v, float):
        return f"{v:+.{digits}f}{suffix}" if suffix in ("%", "pp") else f"{v:.{digits}f}{suffix}"
    return f"{v}{suffix}"


def build_html(led: dict, funds: dict, fee: dict | None, meta: dict,
               val: dict | None = None) -> str:
    b = []
    b.append('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">')
    b.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
    b.append("<title>Risk Management — /audit</title>")
    b.append(f"<style>{CSS}</style></head><body>")
    b.append("<h1>Risk Management</h1>")
    b.append(
        f'<div class="sub">Source: live /audit payload ({meta.get("generated_at")}) + Yahoo monthly history. '
        f'Built {meta.get("built_at")}. All methodologies are applied to measured data; '
        "no figure here is a forecast.</div>"
    )

    # headline
    st = led["headline_status"]
    cls = "bad" if st == "INCOMPLETE" else "good"
    b.append('<div class="panel">')
    b.append(f'<b>Ledger headline:</b> <span class="badge {cls}">{st}</span> ')
    b.append(
        f'Censored {fnum(led["censored_pct"], "%", 1)} of open positions have no market price, '
        f'so no win-rate or profit-factor on this page may be read as a performance claim. '
        f'n = {led["n"]} closed rows.'
        if st == "INCOMPLETE" else
        f'Coverage adequate: censored {fnum(led["censored_pct"], "%", 1)}, n = {led["n"]}.'
    )
    b.append("</div>")

    # row-level verification, rendered only if the validator has been run
    if val:
        rc = (val.get("sections") or {}).get("recent_closed") or {}
        vd = rc.get("verdicts") or {}
        fab = vd.get("FABRICATED_FLAT", 0)
        unv = vd.get("UNVERIFIABLE_NO_ENTRY", 0)
        checked = rc.get("checked", 0)
        bad_cls = "bad" if fab else "good"
        b.append('<div class="panel"><b>Row-level verification:</b> ')
        b.append(f'<span class="badge {bad_cls}">{fab} fabricated flat closes</span> ')
        b.append(
            f"of {checked} closed zeros checked against real market closes; "
            f"{unv} cannot be windowed (no usable exit-date close). "
            "A fabricated flat is a row whose <code>exit_price</code> is not the close "
            "on its own exit date — i.e. the exit was never marked to market."
        )
        b.append("</div>")
    if led.get("caveats"):
        b.append('<div class="panel"><b>Known caveats baked into these numbers</b><ul>')
        for c in led["caveats"]:
            b.append(f"<li>{c}</li>")
        b.append("</ul></div>")

    # KPIs
    b.append('<h2>Risk-adjusted return (per trade, n=%d)</h2>' % led["n"])
    b.append('<div class="grid">')
    kpis = [
        ("win rate", fnum(led["win_rate_pct"], "%", 1)),
        ("profit factor", fnum(led["profit_factor"], "", 3) if led["profit_factor"] else "INSUFFICIENT"),
        ("mean / trade", fnum(led["mean_pct_per_trade"], "%", 3)),
        ("median / trade", fnum(led["median_pct_per_trade"], "%", 3)),
        ("mean ÷ stdev", fnum(led["mean_over_sd"], "", 3)),
        ("sortino", fnum(led["sortino_per_trade"], "", 3)),
    ]
    for k, v in kpis:
        b.append(f'<div class="kpi"><div class="k">{k}</div><div class="v">{v}</div></div>')
    b.append("</div>")
    b.append(f'<p class="note">mean ÷ stdev is a per-trade ratio, not an annualised Sharpe '
             f'(these {led["n"]} trades are not one continuous series).</p>')

    # tail
    b.append("<h2>Tail risk</h2><table><tr><th>Measure</th><th>Value</th><th>Reading</th></tr>")
    tails = [
        ("CVaR 95% (expected shortfall)", fnum(led["cvar_95_pct"], "%", 2),
         "mean of the worst 5% of trades"),
        ("CVaR 99%", fnum(led["cvar_99_pct"], "%", 2), "mean of the worst 1%"),
        ("skew", fnum(led["skew"], "", 3), "positive = fat right tail"),
        ("max drawdown (compounded)", fnum(led["max_drawdown_pct_compounded"], "%", 1),
         f'compounded equity path; terminal {fnum(led["compounded_terminal_pct"], "%", 1)}'),
        ("ulcer index", fnum(led["ulcer_index"], "", 2), "depth × duration of drawdown"),
    ]
    for a, bb, c in tails:
        b.append(f"<tr><td>{a}</td><td>{bb}</td><td class=note>{c}</td></tr>")
    b.append("</table>")

    # sizing
    b.append("<h2>Position sizing</h2><table><tr><th>Method</th><th>Result</th><th>Action</th></tr>")
    kf = led["kelly_fraction"]
    kelly_cls = "bad" if (kf is not None and kf <= 0) else "warn"
    b.append(
        f'<tr><td>Kelly fraction</td><td>{fnum(kf, "", 4)}</td>'
        f'<td><span class="badge {kelly_cls}">{led["kelly_action"]}</span></td></tr>'
    )
    b.append(f'<tr><td>Payoff ratio (avg win ÷ avg loss)</td><td>{fnum(led["payoff_ratio"], ":1", 3)}</td>'
             f'<td class=note>avg win {fnum(led["avg_win_pct"], "%", 2)} · avg loss {fnum(led["avg_loss_pct"], "%", 2)}</td></tr>')
    b.append(f'<tr><td>Monte-Carlo risk of ruin</td><td>{fnum(led["mc_risk_of_ruin_pct_200_trades"], "%", 1)}</td>'
             '<td class=note>2,000 paths × 200 trades at the observed win rate; ruin = book halves</td></tr>')
    b.append("</table>")
    b.append('<p class="note">A negative Kelly fraction means the measured edge is negative at any bet size. '
             "The correct size is zero until the edge is repaired — that is arithmetic, not opinion.</p>")

    # concentration
    b.append("<h2>Concentration</h2><table><tr><th>Measure</th><th>Value</th></tr>")
    b.append(f'<tr><td>HHI by asset class</td><td>{fnum(led["concentration_hhi_class"], "", 3)}</td></tr>')
    if led.get("top_emitter_share_pct") is not None:
        em = ", ".join(f"{k} ({v})" for k, v in led["top_emitters"])
        b.append(f'<tr><td>Top emitter share</td><td>{fnum(led["top_emitter_share_pct"], "%", 1)}</td></tr>')
        b.append(f'<tr><td>Top emitters</td><td class=note>{em}</td></tr>')
    b.append("</table>")

    # funds
    b.append("<h2>Fund / ETF exposure — measured base rates</h2>")
    b.append('<p class="note">These are the only numbers on this page that describe a positive-expectation '
             "instrument. They are the equity risk premium, measured — not a prediction, and not this system's output. "
             "<b>Caveat:</b> Yahoo monthly closes are price-only (no distributions), so total return is understated, "
             "severely so for bond funds.</p>")
    b.append("<table><tr><th>Instrument</th><th>History</th><th>CAGR</th><th>Vol</th><th>Sharpe</th>"
             "<th>Sortino</th><th>Max DD</th><th>CVaR95 (mo)</th></tr>")
    for sym, f in funds.items():
        if "error" in f:
            b.append(f'<tr><td>{f.get("label", sym)}</td><td colspan=7 class="na">{f["error"]}</td></tr>')
            continue
        hist = f'{f["first_obs"]}→{f["last_obs"]} ({f["months"]}mo)'
        if f["survivorship_warning"]:
            hist += ' <span class="badge warn">SHORT·EXCL 2008</span>'
        b.append(
            f'<tr><td>{f["label"]}</td><td class=note>{hist}</td>'
            f'<td>{fnum(f["cagr_pct"], "%")}</td><td>{fnum(f["ann_vol_pct"], "%")}</td>'
            f'<td>{fnum(f["sharpe"], "", 2)}</td><td>{fnum(f["sortino_annual"], "", 2)}</td>'
            f'<td>{fnum(f["max_dd_pct"], "%", 1)}</td><td>{fnum(f["cvar_95_monthly_pct"], "%")}</td></tr>'
        )
    b.append("</table>")

    b.append("<h2>Probability of a positive return, by holding period</h2>")
    b.append('<p class="note">Rolling windows over the instrument\'s full monthly history. Overlapping windows: '
             'the intervals are not independent, so treat these as descriptive base rates, not as p-values.</p>')
    b.append("<table><tr><th>Instrument</th><th>Horizon</th><th>Windows</th><th>P(positive)</th>"
             "<th>Median</th><th>Worst</th><th>Best</th></tr>")
    for sym, f in funds.items():
        if "error" in f:
            continue
        for horizon, key, label in (("12m", "win_12m", "1 year"),
                                    ("60m", "win_60m", "5 years"),
                                    ("120m", "win_120m", "10 years")):
            br = f.get(key)
            if not br:
                continue
            b.append(
                f'<tr><td>{f["label"]}</td><td>{label}</td><td>{br["n_windows"]}</td>'
                f'<td><b>{fnum(br["pct_positive"], "%", 1)}</b></td>'
                f'<td>{fnum(br["median_pct"], "%")}</td><td>{fnum(br["worst_pct"], "%")}</td>'
                f'<td>{fnum(br["best_pct"], "%")}</td></tr>'
            )
    b.append("</table>")

    if fee:
        b.append("<h2>Fee drag</h2>")
        b.append("<table><tr><th>Scenario</th><th>Growth of 1.0 over 20y</th></tr>")
        b.append(f'<tr><td>0.03% expense ratio</td><td>{fee["growth_0.03pct_fee"]:.3f}</td></tr>')
        b.append(f'<tr><td>0.60% expense ratio</td><td>{fee["growth_0.60pct_fee"]:.3f}</td></tr>')
        b.append(f'<tr><td><b>Terminal value lost to the higher fee</b></td>'
                 f'<td><b>{fee["terminal_value_lost_pct"]:.2f}%</b></td></tr>')
        b.append("</table>")
        b.append(f'<p class="note">Same portfolio, same {fee["base_cagr_pct"]}% measured CAGR — only the fee differs. '
                 "The fee is the one input that is certain.</p>")

    b.append("<h2>What this page does not claim</h2><div class=panel><ul>")
    for c in (
        "That the ledger is profitable. It is not: PF < 1 and Kelly < 0 on the measured sample.",
        "That any class has an edge. No metric here carries a published n; see the plan (§3 W1).",
        "That a fund's past hit rate is a forecast. Over 1 month an equity index is close to a coin flip.",
        "That short-history instruments (VOO, 2010→) are safer. They simply have not been tested by a bear market.",
    ):
        b.append(f"<li>{c}</li>")
    b.append("</ul></div>")
    b.append(f'<p class="note">Regenerate: <code>python3 tools/risk_page_builder.py --payload '
             f'https://findtorontoevents.ca/audit/data/dashboard_data.json</code></p>')
    b.append("</body></html>")
    return "\n".join(b)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", required=True)
    ap.add_argument("--json-out", default="reports/risk_metrics_live.json")
    ap.add_argument("--html-out", default="audit_dashboard/risk_management.html")
    args = ap.parse_args(argv)

    d = load(args.payload)
    led = ledger_block(d)
    funds, fee = fund_block([
        ("SPY", "S&P 500 (SPY)"),
        ("VOO", "Vanguard S&P 500 ETF (VOO)"),
        ("QQQ", "Nasdaq-100 (QQQ)"),
        ("AGG", "US Aggregate bonds (AGG)"),
        ("XLF", "Financials sector (XLF)"),
    ])
    meta = {
        "generated_at": d.get("generated_at"),
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "payload": args.payload,
    }
    val = None
    vp = Path("reports/pnl_zero_validation_live.json")
    if vp.exists():
        try:
            val = json.loads(vp.read_text())
        except ValueError:
            val = None
    out = {"meta": meta, "ledger": led, "funds": funds, "fee_drag": fee,
           "row_validation": val["sections"] if val else None}
    Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json_out).write_text(json.dumps(out, indent=2))
    html = build_html(led, funds, fee, meta, val)
    hp = Path(args.html_out)
    hp.parent.mkdir(parents=True, exist_ok=True)
    hp.write_text(html)

    print(f"ledger n={led['n']} WR={led['win_rate_pct']}% PF={led['profit_factor']} "
          f"kelly={led['kelly_fraction']} ruin={led['mc_risk_of_ruin_pct_200_trades']}% "
          f"censored={led['censored_pct']}% -> {led['headline_status']}")
    for s, f in funds.items():
        if "error" in f:
            print(f"  {s}: ERROR {f['error']}")
        else:
            flag = " [SHORT·EXCL2008]" if f["survivorship_warning"] else ""
            print(f"  {s}: {f['months']}mo CAGR={f['cagr_pct']}% Sharpe={f['sharpe']} "
                  f"maxDD={f['max_dd_pct']}%{flag}")
    print(f"wrote {args.json_out} and {args.html_out} ({len(html)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
