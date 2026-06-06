"""
Trading Blueprint Generator — Crypto Focus
Generates a comprehensive analysis page for AI/human review of our trading systems.
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict
from pathlib import Path

EST = timezone(timedelta(hours=-5))
NOW = datetime.now(EST)

def load_payload():
    p = Path(__file__).resolve().parent.parent / "audit_trail" / "data" / "dashboard_payload.json"
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def load_template_descriptions():
    """Extract system descriptions from template.html sysDescriptions object."""
    t = Path(__file__).resolve().parent / "template.html"
    if not t.exists():
        return {}
    text = t.read_text(encoding="utf-8", errors="replace")
    # Find sysDescriptions block
    start = text.find("const sysDescriptions = {")
    if start < 0:
        start = text.find("sysDescriptions = {")
    if start < 0:
        return {}
    brace = text.index("{", start)
    depth = 0
    end = brace
    for i in range(brace, min(brace + 20000, len(text))):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    block = text[brace:end]
    # Parse line by line: 'key': 'value...',
    descs = {}
    import re
    for line in block.split("\n"):
        line = line.strip()
        if not line or line.startswith("//") or line in ("{", "}"):
            continue
        # Match 'key': 'value', (value may contain apostrophes)
        m = re.match(r"'([^']+)'\s*:\s*'(.+)',?\s*$", line)
        if m:
            key = m.group(1)
            val = m.group(2)
            # Strip trailing quote and comma
            if val.endswith("',"):
                val = val[:-2]
            elif val.endswith("'"):
                val = val[:-1]
            descs[key] = val
    return descs


def load_forex_futures_picks():
    """Load forex/futures picks from main active_picks.json (filter by category)."""
    p = Path(__file__).resolve().parent.parent / "alpha_engine" / "data" / "active_picks.json"
    if not p.exists():
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            all_picks = json.load(f)
        return [pk for pk in all_picks if pk.get("category") in ("forex", "futures")]
    except Exception:
        return []


def generate_blueprint():
    D = load_payload()
    descs = load_template_descriptions()

    gen_at = D.get("generated_at", "")
    systems = D.get("systems", [])
    active_picks = D.get("picks", {}).get("active", [])
    closed_picks = D.get("picks", {}).get("closed", [])
    bvf = D.get("backtest_vs_forward", [])
    leaderboard = D.get("leaderboard", [])
    perf_by_ac = D.get("performance", {}).get("by_asset_class", {})

    # ── Filter to CRYPTO only ──
    crypto_systems = [s for s in systems if "CRYPTO" in (s.get("asset_classes") or [])]
    crypto_active = [p for p in active_picks if (p.get("asset_class", "") or "").upper() == "CRYPTO"]
    crypto_closed = [p for p in closed_picks if (p.get("asset_class", "") or "").upper() == "CRYPTO"]
    crypto_perf = perf_by_ac.get("CRYPTO", {})

    # ── Load forex/futures picks from active_picks.json ──
    ff_picks = load_forex_futures_picks()
    forex_picks = [p for p in ff_picks if p.get("category") == "forex"]
    futures_picks = [p for p in ff_picks if p.get("category") == "futures"]

    # ── System-level analysis ──
    sys_with_data = [s for s in crypto_systems if (s.get("closed_picks", 0) or 0) > 0 or (s.get("active_picks", 0) or 0) > 0]
    sys_with_data.sort(key=lambda s: s.get("total_pnl_pct") or 0, reverse=True)

    # ── Strategy-level from active picks ──
    strat_data = defaultdict(lambda: {
        "active": 0, "symbols": set(), "directions": Counter(),
        "systems": set(), "fwd_wr": [], "fwd_pf": [], "fwd_trades": [],
        "bt_wr": [], "bt_pf": [], "confidence": [], "rr": [],
        "health": Counter(), "pnl": [], "picks": []
    })
    for p in crypto_active:
        strat = p.get("strategy") or "unknown"
        sd = strat_data[strat]
        sd["active"] += 1
        sd["symbols"].add(p.get("symbol", ""))
        sd["directions"][p.get("direction", "?")] += 1
        sd["systems"].add(p.get("source_system", ""))
        if p.get("strat_fwd_wr") is not None:
            sd["fwd_wr"].append(p["strat_fwd_wr"])
        if p.get("strat_fwd_pf") is not None:
            sd["fwd_pf"].append(p["strat_fwd_pf"])
        if p.get("strat_fwd_trades") is not None:
            sd["fwd_trades"].append(p["strat_fwd_trades"])
        if p.get("bt_win_rate") is not None:
            sd["bt_wr"].append(p["bt_win_rate"])
        if p.get("bt_profit_factor") is not None:
            sd["bt_pf"].append(p["bt_profit_factor"])
        if p.get("confidence") is not None:
            sd["confidence"].append(float(p["confidence"]))
        if p.get("rr_ratio") is not None:
            sd["rr"].append(float(p["rr_ratio"]))
        sd["health"][p.get("strat_health", "unknown")] += 1
        sd["pnl"].append(float(p.get("pnl_pct", 0) or 0))
        sd["picks"].append(p)

    # ── Picks per day (last 7 days) ──
    day_counts = Counter()
    day_picks = defaultdict(list)
    for p in crypto_active:
        ts = p.get("timestamp", "")
        if ts:
            day = ts[:10]
            day_counts[day] += 1
            day_picks[day].append(p)
    last_7 = sorted(day_counts.keys(), reverse=True)[:7]

    # ── Top score picks simulation ──
    # Compute a composite score for each pick
    def pick_score(p):
        """Enhanced scoring with regime, volume, ADX, and direction weighting.
        The original score is kept as a base, then adjusted by market regime,
        signal volume, ADX strength, and direction bias (long vs short)."""
        # Base components (same as original)
        conf = float(p.get("confidence", 0) or 0)
        rr = float(p.get("rr_ratio", 0) or 0)
        fwd_wr = float(p.get("strat_fwd_wr", 0) or 0) / 100
        fwd_pf = float(p.get("strat_fwd_pf", 0) or 0)
        fwd_trades = int(p.get("strat_fwd_trades", 0) or 0)
        agreement = int(p.get("agreement_count", 0) or 0)
        # Health penalty (unchanged)
        health = p.get("strat_health", "")
        health_mult = 1.0 if health == "healthy" else 0.7 if health == "degrading" else 0.5

        # Base composite score
        base_score = (
            0.25 * conf +
            0.20 * min(rr / 5, 1.0) +
            0.25 * fwd_wr +
            0.15 * min(fwd_pf / 3, 1.0) +
            0.10 * min(fwd_trades / 50, 1.0) +
            0.05 * min(agreement / 3, 1.0)
        )

        # --- Regime adjustment ---
        # Simple regime proxy: BTC 24h change (positive = bullish, negative = bearish)
        btc_change = float(p.get("btc_24h_change", 0) or 0)
        direction = str(p.get("direction", "LONG")).upper()
        if btc_change < 0:  # bearish regime
            regime_mult = 1.2 if direction == "SHORT" else 0.8
        elif btc_change > 0:  # bullish regime
            regime_mult = 1.2 if direction == "LONG" else 0.8
        else:  # neutral / unknown
            regime_mult = 1.0

        # --- Volume weighting ---
        # Prefer high‑volume picks (≥ $50M 24h volume gets a boost)
        vol = float(p.get("volume_24h", 0) or 0)
        if vol >= 50_000_000:
            vol_mult = 1.2
        elif vol >= 10_000_000:
            vol_mult = 1.0
        else:
            vol_mult = 0.8

        # --- ADX strength weighting ---
        adx = float(p.get("adx", 0) or 0)
        adx_mult = 1.0 if adx >= 15 else 0.8

        # Combine all multipliers
        final_score = base_score * health_mult * regime_mult * vol_mult * adx_mult
        return round(final_score, 4)

    scored_picks = [(pick_score(p), p) for p in crypto_active]
    scored_picks.sort(key=lambda x: x[0], reverse=True)

    # Simulate: top 10 and top 20 picks
    def simulate_portfolio(picks, label):
        if not picks:
            return {"label": label, "count": 0}
        pnls = [float(p.get("pnl_pct", 0) or 0) for p in picks]
        wins = sum(1 for x in pnls if x > 0)
        losses = sum(1 for x in pnls if x < 0)
        flat = len(pnls) - wins - losses
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0
        total_pnl = sum(pnls)
        gross_w = sum(x for x in pnls if x > 0)
        gross_l = abs(sum(x for x in pnls if x < 0))
        pf = gross_w / gross_l if gross_l > 0 else (99 if gross_w > 0 else 0)
        wr = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
        symbols = set(p.get("symbol", "") for p in picks)
        dirs = Counter(p.get("direction", "") for p in picks)
        # Hold time analysis
        ages = [float(p.get("age_hours", 0) or 0) for p in picks]
        avg_hold = sum(ages) / len(ages) if ages else 0
        max_hold = max(ages) if ages else 0
        min_hold = min(ages) if ages else 0
        # Max drawdown simulation (worst individual pick)
        max_dd = min(pnls) if pnls else 0
        # Compute overlap with other portfolios
        pick_ids = set(p.get("symbol", "") + p.get("direction", "") for p in picks)
        return {
            "label": label, "count": len(picks),
            "wins": wins, "losses": losses, "flat": flat,
            "wr": round(wr, 1), "avg_pnl": round(avg_pnl, 2),
            "total_pnl": round(total_pnl, 2), "pf": round(pf, 2),
            "symbols": len(symbols), "directions": dict(dirs),
            "avg_hold_h": round(avg_hold, 1), "max_hold_h": round(max_hold, 1),
            "min_hold_h": round(min_hold, 1), "max_dd": round(max_dd, 2),
            "pick_ids": pick_ids, "picks": picks
        }

    top10_sim = simulate_portfolio([p for _, p in scored_picks[:10]], "Top 10 Score")
    top20_sim = simulate_portfolio([p for _, p in scored_picks[:20]], "Top 20 Score")
    # Also try: only picks with fwd_wr >= 55 AND fwd_trades >= 10
    vetted = [p for s, p in scored_picks if
              float(p.get("strat_fwd_wr", 0) or 0) >= 55 and
              int(p.get("strat_fwd_trades", 0) or 0) >= 10]
    vetted_sim = simulate_portfolio(vetted[:20], "Top 20 Vetted (FWD WR≥55%, Trades≥10)")
    # High agreement only
    agree3 = [p for s, p in scored_picks if int(p.get("agreement_count", 0) or 0) >= 3]
    agree_sim = simulate_portfolio(agree3[:20], "Top 20 High Agreement (≥3 systems)")

    # ── Mercury AI recommended scoring formula ──
    def mercury_score(p):
        fwd_wr = float(p.get("strat_fwd_wr", 0) or 0) / 100
        fwd_pf = float(p.get("strat_fwd_pf", 0) or 0)
        conf = float(p.get("confidence", 0) or 0)
        agreement = int(p.get("agreement_count", 0) or 0)
        trust = p.get("trust_tier", "SANDBOX")
        trust_score = {"PROVEN": 1.0, "SANDBOX": 0.5, "PROBATION": 0.2, "DEMOTED": 0.3}.get(trust, 0.5)
        return round(0.30 * fwd_wr + 0.25 * min(fwd_pf / 3, 1.0) + 0.20 * conf + 0.15 * min(agreement / 3, 1.0) + 0.10 * trust_score, 4)

    mercury_scored = [(mercury_score(p), p) for p in crypto_active]
    mercury_scored.sort(key=lambda x: x[0], reverse=True)
    mercury_top20_sim = simulate_portfolio([p for _, p in mercury_scored[:20]], "Mercury Top 20 (FWD-weighted)")

    # Mercury strict filter: FWD trades ≥ 30, FWD WR ≥ 55%, FWD PF ≥ 1.2, decay ≤ -10%
    mercury_strict = [p for s, p in mercury_scored if
                      int(p.get("strat_fwd_trades", 0) or 0) >= 30 and
                      float(p.get("strat_fwd_wr", 0) or 0) >= 55 and
                      float(p.get("strat_fwd_pf", 0) or 0) >= 1.2]
    mercury_strict_sim = simulate_portfolio(mercury_strict[:20], "Mercury Strict (FWD≥30t, WR≥55%, PF≥1.2)")

    # ── Grok normalized scoring formula ──
    def grok_score(p):
        fwd_wr = float(p.get("strat_fwd_wr", 0) or 0) / 100
        fwd_pf = float(p.get("strat_fwd_pf", 0) or 0)
        conf = float(p.get("confidence", 0) or 0)
        agreement = int(p.get("agreement_count", 0) or 0)
        fwd_trades = int(p.get("strat_fwd_trades", 0) or 0)
        trust = p.get("trust_tier", "SANDBOX")
        trust_w = {"PROVEN": 1.0, "SANDBOX": 0.5, "PROBATION": 0.2, "DEMOTED": 0.3}.get(trust, 0.5)
        # Hard gate: zero score for unproven strategies
        decay = float(p.get("strat_bt_wr", 0) or 0) - float(p.get("strat_fwd_wr", 0) or 0)
        if fwd_trades < 30 or fwd_wr < 0.55 or fwd_pf < 1.2 or decay > 15:
            return 0.0
        # Normalized scoring (55% on proven forward metrics)
        norm_wr = min(1.0, (fwd_wr - 0.45) / 0.55)
        norm_pf = min(1.0, (fwd_pf - 1.0) / 2.0)
        max_agree = max(int(pp.get("agreement_count", 0) or 0) for pp in crypto_active) if crypto_active else 1
        return round(0.30 * norm_wr + 0.25 * norm_pf + 0.20 * conf + 0.15 * (agreement / max(max_agree, 1)) + 0.10 * trust_w, 4)

    grok_scored = [(grok_score(p), p) for p in crypto_active]
    grok_scored = [(s, p) for s, p in grok_scored if s > 0]
    grok_scored.sort(key=lambda x: x[0], reverse=True)
    grok_top20_sim = simulate_portfolio([p for _, p in grok_scored[:20]], "Grok Top 20 (Hard-gated + Normalized)")

    # ── Portfolio overlap analysis ──
    all_sims = [top10_sim, top20_sim, vetted_sim, agree_sim, mercury_top20_sim, mercury_strict_sim, grok_top20_sim]
    for i, s1 in enumerate(all_sims):
        if not s1.get("pick_ids"):
            continue
        overlaps = []
        for j, s2 in enumerate(all_sims):
            if i == j or not s2.get("pick_ids"):
                continue
            common = s1["pick_ids"] & s2["pick_ids"]
            if common:
                overlaps.append(f'{s2["label"]}: {len(common)} shared')
        s1["overlap"] = "; ".join(overlaps) if overlaps else "None"

    # ── Backtest vs Forward comparison ──
    crypto_bvf = [b for b in bvf if any(
        s.get("name") == b.get("system") and "CRYPTO" in (s.get("asset_classes") or [])
        for s in systems
    )]
    # Also include all if we can't filter (many are crypto)
    if len(crypto_bvf) < 10:
        crypto_bvf = bvf  # most are crypto anyway

    # ── Leaderboard (top strategies) ──
    crypto_lb = [l for l in leaderboard if l.get("fwd_trades", 0) and l.get("fwd_trades", 0) >= 3]
    crypto_lb.sort(key=lambda x: x.get("fwd_total_pnl", 0), reverse=True)

    # ── Build HTML ──
    html = build_html(
        gen_at=gen_at,
        crypto_perf=crypto_perf,
        sys_with_data=sys_with_data,
        descs=descs,
        strat_data=strat_data,
        last_7=last_7,
        day_counts=day_counts,
        day_picks=day_picks,
        scored_picks=scored_picks,
        top10_sim=top10_sim,
        top20_sim=top20_sim,
        vetted_sim=vetted_sim,
        agree_sim=agree_sim,
        mercury_top20_sim=mercury_top20_sim,
        mercury_strict_sim=mercury_strict_sim,
        grok_top20_sim=grok_top20_sim,
        crypto_bvf=crypto_bvf,
        crypto_lb=crypto_lb,
        crypto_active=crypto_active,
        crypto_systems=crypto_systems,
        forex_picks=forex_picks,
        futures_picks=futures_picks,
    )

    out = Path(__file__).resolve().parent / "trading_blueprint.html"
    out.write_text(html, encoding="utf-8")
    print(f"Trading Blueprint generated: {out} ({len(html):,} bytes)")
    return str(out)


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _pnl_color(v):
    v = float(v or 0)
    return "#22c55e" if v > 0 else "#ef4444" if v < 0 else "#888"


def _fmt_pct(v):
    v = float(v or 0)
    return f'{"+" if v >= 0 else ""}{v:.2f}%'


def build_html(*, gen_at, crypto_perf, sys_with_data, descs, strat_data,
               last_7, day_counts, day_picks, scored_picks,
               top10_sim, top20_sim, vetted_sim, agree_sim,
               mercury_top20_sim, mercury_strict_sim, grok_top20_sim,
               crypto_bvf, crypto_lb, crypto_active, crypto_systems,
               forex_picks=None, futures_picks=None):

    now_str = NOW.strftime("%Y-%m-%d %H:%M EST")

    # ── Section 1: Executive Summary ──
    cp = crypto_perf
    exec_summary = f"""
    <div class="section">
      <h2>1. Executive Summary — Crypto Portfolio</h2>
      <p class="dim">Generated {now_str} from {len(crypto_systems)} crypto systems producing {len(crypto_active):,} active picks.</p>
      <div class="card-grid">
        <div class="card"><div class="card-label">Active Picks</div><div class="card-val">{cp.get('active',0):,}</div></div>
        <div class="card"><div class="card-label">Closed Picks</div><div class="card-val">{cp.get('closed',0):,}</div></div>
        <div class="card"><div class="card-label">Win Rate</div><div class="card-val" style="color:{_pnl_color(cp.get('win_rate',0)-50)}">{cp.get('win_rate',0):.1f}%</div></div>
        <div class="card"><div class="card-label">Total PnL (Realized)</div><div class="card-val" style="color:{_pnl_color(cp.get('pnl',0))}">{_fmt_pct(cp.get('pnl',0))}</div></div>
        <div class="card"><div class="card-label">Profit Factor</div><div class="card-val" style="color:{_pnl_color(cp.get('profit_factor',0)-1)}">{cp.get('profit_factor',0):.2f}</div></div>
        <div class="card"><div class="card-label">Expectancy / Trade</div><div class="card-val" style="color:{_pnl_color(cp.get('expectancy',0))}">{_fmt_pct(cp.get('expectancy',0))}</div></div>
        <div class="card"><div class="card-label">Avg Win</div><div class="card-val" style="color:#22c55e">+{cp.get('avg_win',0):.2f}%</div></div>
        <div class="card"><div class="card-label">Avg Loss</div><div class="card-val" style="color:#ef4444">-{cp.get('avg_loss',0):.2f}%</div></div>
      </div>
      <div class="verdict-box bad">
        <b>Honest Assessment:</b> The overall crypto portfolio is <b>unprofitable</b> with a {cp.get('win_rate',0):.1f}% win rate and {cp.get('profit_factor',0):.2f} profit factor.
        Expectancy is {_fmt_pct(cp.get('expectancy',0))} per trade — meaning every trade loses on average.
        The system generates too many low-quality signals from unproven strategies. However, a subset of proven strategies shows strong positive results (see Section 4).
        <br><br><b>Key Problem:</b> Avg loss ({cp.get('avg_loss',0):.2f}%) exceeds avg win ({cp.get('avg_win',0):.2f}%), AND win rate is below 50%.
        A profitable system needs EITHER a high WR with reasonable R:R, OR a low WR with high R:R. We have neither in aggregate.
      </div>
    </div>"""

    # ── Section 2: System-by-System Breakdown ──
    sys_rows = ""
    for s in sys_with_data:
        name = s.get("name", "")
        desc = descs.get(name, descs.get(name.lower(), "No description available"))
        wr = s.get("win_rate", 0) or 0
        closed = s.get("closed_picks", 0) or 0
        active = s.get("active_picks", 0) or 0
        wins = s.get("wins", 0) or 0
        losses = s.get("losses", 0) or 0
        pnl = s.get("total_pnl_pct", 0) or 0
        pf = s.get("profit_factor") or 0
        exp = s.get("expectancy", 0) or 0
        avg_w = s.get("avg_win", 0) or 0
        avg_l = s.get("avg_loss", 0) or 0
        mdd = s.get("max_drawdown", 0) or 0
        unrealized = s.get("unrealized_pnl_pct", 0) or 0

        grade = "A" if wr >= 55 and pf >= 1.5 and closed >= 20 else \
                "B" if wr >= 50 and pf >= 1.0 and closed >= 10 else \
                "C" if wr >= 45 or pf >= 0.8 else \
                "D" if closed >= 5 else "F"
        grade_color = {"A": "#22c55e", "B": "#86efac", "C": "#f59e0b", "D": "#ef4444", "F": "#888"}[grade]

        sys_rows += f"""<tr>
          <td><b>{_esc(name.replace('_',' '))}</b><br><span class="dim" style="font-size:11px">{_esc(desc[:120])}</span></td>
          <td style="text-align:center;color:{grade_color};font-weight:700;font-size:18px">{grade}</td>
          <td class="num">{active}</td>
          <td class="num">{closed}</td>
          <td class="num">{wins}</td><td class="num">{losses}</td>
          <td class="num" style="color:{_pnl_color(wr-50)}">{wr:.1f}%</td>
          <td class="num" style="color:{_pnl_color(pnl)}">{_fmt_pct(pnl)}</td>
          <td class="num" style="color:{_pnl_color((pf or 0)-1)}">{pf:.2f}</td>
          <td class="num" style="color:{_pnl_color(exp)}">{_fmt_pct(exp)}</td>
          <td class="num">+{avg_w:.1f}%</td>
          <td class="num">-{avg_l:.1f}%</td>
        </tr>"""

    systems_section = f"""
    <div class="section">
      <h2>2. System-by-System Breakdown ({len(sys_with_data)} crypto systems with data)</h2>
      <p class="dim">Grade: A = proven profitable (WR≥55, PF≥1.5, 20+ trades), B = positive edge, C = marginal, D = insufficient data, F = unprofitable</p>
      <div class="table-wrap">
      <table><thead><tr>
        <th style="min-width:200px">System</th><th>Grade</th><th>Active</th><th>Closed</th><th>W</th><th>L</th>
        <th>WR</th><th>Total PnL</th><th>PF</th><th>Expect.</th><th>Avg W</th><th>Avg L</th>
      </tr></thead><tbody>{sys_rows}</tbody></table>
      </div>
    </div>"""

    # ── Section 3: Strategy Detail (top 30 by active picks) ──
    top_strats = sorted(strat_data.items(), key=lambda x: x[1]["active"], reverse=True)[:30]
    strat_rows = ""
    for strat_name, sd in top_strats:
        fwd_wr = sum(sd["fwd_wr"]) / len(sd["fwd_wr"]) if sd["fwd_wr"] else 0
        fwd_pf = sum(sd["fwd_pf"]) / len(sd["fwd_pf"]) if sd["fwd_pf"] else 0
        fwd_trades = max(sd["fwd_trades"]) if sd["fwd_trades"] else 0
        bt_wr = sum(sd["bt_wr"]) / len(sd["bt_wr"]) if sd["bt_wr"] else None
        avg_conf = sum(sd["confidence"]) / len(sd["confidence"]) if sd["confidence"] else 0
        avg_rr = sum(sd["rr"]) / len(sd["rr"]) if sd["rr"] else 0
        avg_pnl = sum(sd["pnl"]) / len(sd["pnl"]) if sd["pnl"] else 0
        dirs = ", ".join(f"{d}:{c}" for d, c in sd["directions"].most_common())
        health_str = ", ".join(f"{h}:{c}" for h, c in sd["health"].most_common())
        syms_list = sorted(sd["symbols"])[:8]
        syms_str = ", ".join(s.replace("USDT", "") for s in syms_list)
        if len(sd["symbols"]) > 8:
            syms_str += f" +{len(sd['symbols'])-8} more"

        bt_str = f"{bt_wr:.1f}%" if bt_wr is not None else "n/a"

        strat_rows += f"""<tr>
          <td><b>{_esc(strat_name[:40])}</b></td>
          <td class="num">{sd['active']}</td>
          <td class="num">{dirs}</td>
          <td class="num" style="font-size:11px">{_esc(syms_str)}</td>
          <td class="num">{bt_str}</td>
          <td class="num" style="color:{_pnl_color(fwd_wr-50)}">{fwd_wr:.1f}%</td>
          <td class="num">{fwd_trades}</td>
          <td class="num" style="color:{_pnl_color(fwd_pf-1)}">{fwd_pf:.2f}</td>
          <td class="num">{avg_conf:.2f}</td>
          <td class="num">{avg_rr:.1f}</td>
          <td class="num" style="color:{_pnl_color(avg_pnl)}">{_fmt_pct(avg_pnl)}</td>
          <td class="num">{health_str}</td>
        </tr>"""

    strat_section = f"""
    <div class="section">
      <h2>3. Strategy Breakdown — Top 30 by Active Picks</h2>
      <p class="dim">Each strategy may run across multiple systems. Forward WR/PF/Trades reflect live forward-testing performance. BT = backtest.</p>
      <div class="table-wrap">
      <table><thead><tr>
        <th>Strategy</th><th>Active</th><th>Directions</th><th>Symbols</th>
        <th>BT WR</th><th>FWD WR</th><th>FWD Trades</th><th>FWD PF</th>
        <th>Conf</th><th>R:R</th><th>Avg PnL</th><th>Health</th>
      </tr></thead><tbody>{strat_rows}</tbody></table>
      </div>
    </div>"""

    # ── Section 3b: Strategy Logic Reference ──
    STRATEGY_LOGIC = {
        "ema_stack": "EMA Stack (9/21/50/200). Entry: all 4 EMAs aligned (9>21>50>200 for LONG). Timeframe: 4H. Exit: fastest EMA crosses below next.",
        "macd_crossover": "MACD(12,26,9) signal line crossover. Entry: MACD crosses above signal (LONG) or below (SHORT). Timeframe: 1H-4H. Exit: reverse crossover or TP/SL.",
        "stochrsi_macd_combo": "StochRSI(14) + MACD confluence. Entry: both indicators agree on direction (StochRSI oversold + MACD bullish = LONG). Timeframe: 4H.",
        "bollinger_squeeze": "Bollinger Band(20,2) squeeze breakout. Entry: bandwidth contracts to <4%, then price breaks upper/lower band with volume confirmation. Timeframe: 4H.",
        "enhanced_ml_A_xgboost": "XGBoost gradient-boosted tree. Features: 100+ technical indicators (RSI, MACD, BB, OBV, ATR, etc.). Trained on 6mo rolling window. Output: probability of +3% move within 48h.",
        "M_claw_fear_deep": "KIMI Fear-based contrarian. Entry: Fear & Greed Index ≤15 ('Extreme Fear') + RSI(14)<25 + volume spike >2x avg. Targets capitulation bottoms.",
        "M_claw_fear_contrarian": "KIMI Fear contrarian. Entry: F&G ≤25 + negative funding rate + price below 200 EMA. Less extreme than deep fear variant.",
        "M_fear_buy_relaxed": "Relaxed fear buy. Entry: F&G ≤35 (moderate fear) + any bullish momentum signal. Wider net than deep/contrarian variants.",
        "crypto_vwap_deviation_reversion": "VWAP Deviation Mean Reversion. Entry: price deviates >2 std from VWAP, bet on reversion. PROVEN: +332% total PnL. Timeframe: 1H.",
        "drawdown_recovery_rsi_eth": "RSI Recovery on ETH. Entry: RSI(14)<30 after >15% drawdown from local high. ETH-specific. PROVEN: 72.7% WR, +291%. Timeframe: 4H.",
        "multi_period_rsi_confluence_eth": "Multi-period RSI Confluence on ETH. Entry: RSI oversold on 3+ timeframes simultaneously (1H+4H+1D). PROVEN: 64.3% WR, +200%.",
        "multi_period_rsi_confluence_xrp": "Multi-period RSI Confluence on XRP. Same logic as ETH variant. PROVEN: 83.3% WR, +157%. Timeframe: 1H+4H+1D.",
        "hurst_regime_adaptive": "Hurst Exponent regime detection. Entry: H>0.5 = trending (trade breakouts), H<0.5 = mean-reverting (trade pullbacks). Adapts strategy to market regime.",
        "Mercury2 Fast": "Mercury2 XGBoost with fast exits (tighter TP/SL). Same ML model, shorter hold period. WARNING: has shown broken entry prices on probation.",
        "connors_rsi2": "Connors RSI(2) mean reversion. Entry: RSI(2)<5 (extreme oversold) for LONG. PROVEN: 75.7% WR on SPY (p=6e-6, Sharpe 4.84). Crypto variant: 62.5% WR on BTC.",
        "vix_spike_reversal": "VIX Spike Reversal. Entry: VIX>30 + Crypto F&G<25 = buy panic. PROVEN: 72% WR (p=0.022, Sharpe 6.20). 10yr backtest with 25 trades.",
        "funding_rate_carry": "Funding Rate Carry. Market-neutral: long spot + short perps when funding>0.05%. Captures funding payments. Documented 19-115% annual.",
        "fear_greed_extreme_dca": "Extreme Fear DCA. Buy when F&G≤10, DCA over multiple days. Nasdaq backtest: 14.6% annual return.",
        "vwap_rsi_institutional": "VWAP + Triple RSI Institutional Confluence. Entry: price returns to VWAP + RSI(14)<40 oversold + RSI(21)>50 + RSI(50)>55 (trend intact) + volume spike. Category: intraday mean reversion. Expected WR 65-72%.",
        "liquidation_cascade_contrarian": "Liquidation Cascade Contrarian. Entry: large wick >3x ATR (cascade) + volume spike >3x avg + >50% wick recovery. Catches post-liquidation bounces. Category: structural. Expected WR 58-65%, R:R 1:2+.",
        "regime_sentinel_composite": "Regime Sentinel Composite. Meta-strategy: classifies market into ACCUMULATION/MARKUP/DISTRIBUTION/MARKDOWN via SMA50/200 + RSI + F&G + momentum + volume. Direct signals only at extremes (F&G<15 BUY, F&G>85 SELL). Used as filter for all other strategies.",
        "rsi_pairs_arbitrage": "RSI-Weighted Pairs Arbitrage. Entry: Z-score of BTC/ETH spread < -2.0 + RSI of underperformer < 35. Market-neutral stat-arb on correlated pairs. Expected WR 70-78%, PF 2.0-2.5.",
    }

    # Build strategy logic reference from both the dict and strat_data
    logic_rows = ""
    covered = set()
    for strat_name, sd in sorted(strat_data.items(), key=lambda x: x[1]["active"], reverse=True)[:50]:
        logic = STRATEGY_LOGIC.get(strat_name, "")
        if not logic:
            # Try partial match
            for k, v in STRATEGY_LOGIC.items():
                if k.lower() in strat_name.lower() or strat_name.lower() in k.lower():
                    logic = v
                    break
        if not logic and strat_name.startswith("Revival_Mutated_"):
            parent = strat_name.replace("Revival_Mutated_", "")
            logic = f"Auto-mutated variant of '{parent}'. Parameters adjusted ±10-30% from parent strategy. Enters as SANDBOX tier (0.25x trust). Parent logic unknown — see parent strategy for rules."
        if not logic and "genome" in strat_name.lower() or "gp_" in strat_name.lower():
            logic = "Genetically-programmed expression tree. Buy/sell formulas evolved via GP from RSI/MACD/EMA/Volume/ATR primitives. Specific formula varies per generation."
        if not logic:
            logic = "<i>No documented entry/exit rules. Strategy logic needs documentation.</i>"
        fwd_wr = sum(sd["fwd_wr"]) / len(sd["fwd_wr"]) if sd["fwd_wr"] else 0
        fwd_t = max(sd["fwd_trades"]) if sd["fwd_trades"] else 0
        logic_rows += f'<tr><td><b>{_esc(strat_name[:45])}</b></td><td class="num">{sd["active"]}</td><td class="num" style="color:{_pnl_color(fwd_wr-50)}">{fwd_wr:.0f}%/{fwd_t}t</td><td style="font-size:12px">{logic}</td></tr>'

    strat_logic_section = f"""
    <div class="section">
      <h2>3b. Strategy Logic Reference — What Each Strategy Actually Does</h2>
      <p class="dim">For an external reviewer to evaluate signal quality, they need to know the actual entry/exit rules, not just names. Strategies marked with "No documented rules" are a transparency gap.</p>
      <div class="table-wrap">
      <table><thead><tr><th style="min-width:180px">Strategy</th><th>Active</th><th>FWD WR/Trades</th><th>Entry/Exit Logic & Parameters</th></tr></thead>
      <tbody>{logic_rows}</tbody></table>
      </div>
      <div class="verdict-box neutral">
        <b>Transparency gap:</b> Many strategies lack documented entry/exit rules. This makes external review impossible for those strategies.
        A reviewer can only evaluate strategies where the logic is explicitly documented. Undocumented strategies should be treated as untestable black boxes.
      </div>
    </div>"""

    # ── Section 4: Backtest vs Forward-Test Comparison ──
    bvf_sorted = sorted(crypto_bvf, key=lambda x: abs(x.get("decay") or 0), reverse=True)
    bvf_rows = ""
    for b in bvf_sorted[:40]:
        decay = b.get("decay", 0) or 0
        bt_wr = b.get("bt_wr", 0) or 0
        fwd_wr = b.get("fwd_wr", 0) or 0
        bt_t = b.get("bt_trades", 0) or 0
        fwd_t = b.get("fwd_trades", 0) or 0
        decay_color = "#22c55e" if decay < 0 else "#ef4444" if decay > 10 else "#f59e0b"
        bvf_rows += f"""<tr>
          <td>{_esc(b.get('strategy','')[:40])}</td>
          <td class="dim">{_esc(b.get('system','')[:20])}</td>
          <td class="num">{bt_wr:.1f}%</td><td class="num">{bt_t}</td>
          <td class="num" style="color:{_pnl_color(fwd_wr-50)}">{fwd_wr:.1f}%</td><td class="num">{fwd_t}</td>
          <td class="num" style="color:{decay_color}">{decay:+.1f}%</td>
        </tr>"""

    bvf_section = f"""
    <div class="section">
      <h2>4. Backtest vs Forward-Test Performance</h2>
      <p class="dim">Decay = BT WR − FWD WR. Positive decay means strategy performs <b>worse</b> live than in backtest (overfitting). Negative means it improved.</p>
      <div class="verdict-box neutral">
        <b>What to look for:</b> Strategies with low decay AND sufficient forward trades (≥10) are the most trustworthy.
        High decay (>15%) suggests curve-fitting. Negative decay with few trades may be luck.
      </div>
      <div class="table-wrap">
      <table><thead><tr>
        <th>Strategy</th><th>System</th>
        <th>BT WR</th><th>BT Trades</th><th>FWD WR</th><th>FWD Trades</th><th>Decay</th>
      </tr></thead><tbody>{bvf_rows}</tbody></table>
      </div>
    </div>"""

    # ── Section 5: Daily Pick Volume (last 7 days) ──
    day_rows = ""
    for day in last_7:
        cnt = day_counts[day]
        picks_for_day = day_picks[day]
        # Top 5 symbols
        sym_counts = Counter(p.get("symbol", "") for p in picks_for_day)
        top_syms = ", ".join(f"{s.replace('USDT','')}({c})" for s, c in sym_counts.most_common(5))
        dir_counts = Counter(p.get("direction", "") for p in picks_for_day)
        dir_str = ", ".join(f"{d}:{c}" for d, c in dir_counts.most_common())
        sys_counts = Counter(p.get("source_system", "") for p in picks_for_day)
        top_sys = ", ".join(f"{s}({c})" for s, c in sys_counts.most_common(3))
        day_rows += f"""<tr>
          <td>{day}</td><td class="num">{cnt}</td>
          <td class="dim">{dir_str}</td>
          <td style="font-size:11px">{_esc(top_syms)}</td>
          <td style="font-size:11px">{_esc(top_sys)}</td>
        </tr>"""

    daily_section = f"""
    <div class="section">
      <h2>5. Daily Pick Volume — Last 7 Days</h2>
      <p class="dim">How many crypto signals are being generated each day? Is the system too aggressive or too conservative?</p>
      <table><thead><tr>
        <th>Date</th><th>Picks</th><th>Directions</th><th>Top Symbols</th><th>Top Systems</th>
      </tr></thead><tbody>{day_rows}</tbody></table>
      <div class="verdict-box neutral">
        <b>Volume Analysis:</b> The system generates {sum(day_counts[d] for d in last_7):,} crypto picks over 7 days
        (avg {sum(day_counts[d] for d in last_7)//max(len(last_7),1)}/day).
        {"This is extremely high — most picks are noise. A narrower filter would improve signal quality." if sum(day_counts[d] for d in last_7) > 500 else "Volume is manageable but may miss opportunities if too conservative."}
      </div>
    </div>"""

    # ── Section 6: Top Score Picks & Simulated Portfolios ──
    def sim_table(sim):
        if not sim.get("count"):
            return "<p class='dim'>No picks matched criteria.</p>"
        picks = sim.get("picks", [])
        pick_rows = ""
        for p in picks[:20]:
            sym = p.get("symbol", "")
            d = p.get("direction", "")
            entry = p.get("entry_price", 0)
            tp = p.get("take_profit", 0)
            sl = p.get("stop_loss", 0)
            pnl = float(p.get("pnl_pct", 0) or 0)
            conf = float(p.get("confidence", 0) or 0)
            rr = float(p.get("rr_ratio", 0) or 0)
            fwr = float(p.get("strat_fwd_wr", 0) or 0)
            strat = p.get("strategy", "")[:25]
            sys_name = p.get("source_system", "")[:20]
            agree = int(p.get("agreement_count", 0) or 0)
            age_h = float(p.get("age_hours", 0) or 0)
            pick_rows += f"""<tr>
              <td>{_esc(sym.replace('USDT',''))}</td>
              <td style="color:{'#22c55e' if d=='LONG' else '#ef4444'}">{d}</td>
              <td class="num">{entry}</td><td class="num">{tp}</td><td class="num">{sl}</td>
              <td class="num" style="color:{_pnl_color(pnl)}">{_fmt_pct(pnl)}</td>
              <td class="num">{age_h:.0f}h</td>
              <td class="num">{conf:.2f}</td><td class="num">{rr:.1f}</td>
              <td class="num" style="color:{_pnl_color(fwr-50)}">{fwr:.0f}%</td>
              <td class="num">{agree}</td>
              <td class="dim" style="font-size:11px">{_esc(strat)}</td>
              <td class="dim" style="font-size:11px">{_esc(sys_name)}</td>
            </tr>"""
        overlap_html = f'<span style="color:var(--yellow)">Overlap: {sim.get("overlap","n/a")}</span>' if sim.get("overlap") else ''
        return f"""
        <div class="sim-summary">
          <span><b>{sim['count']}</b> picks</span>
          <span>WR: <b style="color:{_pnl_color(sim['wr']-50)}">{sim['wr']}%</b></span>
          <span>Total PnL: <b style="color:{_pnl_color(sim['total_pnl'])}">{_fmt_pct(sim['total_pnl'])}</b> (unrealized)</span>
          <span>PF: <b style="color:{_pnl_color(sim['pf']-1)}">{sim['pf']}</b></span>
          <span>Avg PnL: <b style="color:{_pnl_color(sim['avg_pnl'])}">{_fmt_pct(sim['avg_pnl'])}</b></span>
          <span>Worst pick: <b style="color:var(--red)">{_fmt_pct(sim.get('max_dd',0))}</b></span>
          <span>{sim['symbols']} symbols</span>
          <span>{sim.get('directions','')}</span>
          <span>Hold: avg {sim.get('avg_hold_h',0):.0f}h, max {sim.get('max_hold_h',0):.0f}h</span>
          {overlap_html}
        </div>
        <table><thead><tr>
          <th>Symbol</th><th>Dir</th><th>Entry</th><th>TP</th><th>SL</th><th>PnL (unreal.)</th>
          <th>Age(h)</th><th>Conf</th><th>R:R</th><th>FWD WR</th><th>Agree</th><th>Strategy</th><th>System</th>
        </tr></thead><tbody>{pick_rows}</tbody></table>"""

    sim_section = f"""
    <div class="section">
      <h2>6. Optimal Pick Selection — Simulated Results</h2>
      <p class="dim">If we only traded the top-scoring picks, what would performance look like? All PnL values are <b>unrealized</b> (positions still open).</p>

      <h3>Scoring Formula</h3>
      <div class="code-block">
score = (0.25 × confidence + 0.20 × min(R:R/5, 1) + 0.25 × fwd_wr + 0.15 × min(fwd_pf/3, 1) + 0.10 × min(fwd_trades/50, 1) + 0.05 × min(agreement/3, 1)) × health_multiplier

health_multiplier: healthy=1.0, degrading=0.7, other=0.5
      </div>

      <h3>A) Top 10 by Score</h3>
      {sim_table(top10_sim)}

      <h3>B) Top 20 by Score</h3>
      {sim_table(top20_sim)}

      <h3>C) Top 20 Vetted Only (Forward WR ≥ 55%, Forward Trades ≥ 10)</h3>
      {sim_table(vetted_sim)}

      <h3>D) Top 20 High Agreement (≥3 systems agree)</h3>
      {sim_table(agree_sim)}

      <h3>E) Mercury AI Recommended Scoring (FWD-weighted)</h3>
      <div class="code-block">
mercury_score = 0.30 × fwd_wr + 0.25 × min(fwd_pf/3, 1) + 0.20 × confidence + 0.15 × min(agreement/3, 1) + 0.10 × trust_tier_score

trust_tier_score: PROVEN=1.0, SANDBOX=0.5, DEMOTED=0.3, PROBATION=0.2
Key change: FWD WR weight increased from 0.25→0.30, R:R removed, trust tier added
      </div>
      {sim_table(mercury_top20_sim)}

      <h3>F) Mercury Strict Filter (FWD Trades≥30, WR≥55%, PF≥1.2)</h3>
      <p class="dim">Only strategies with substantial forward validation and proven profitability. This is the most conservative filter.</p>
      {sim_table(mercury_strict_sim)}

      <h3>G) Grok Hard-Gated + Normalized Scoring</h3>
      <div class="code-block">
HARD GATE (score=0 if ANY fail): fwd_trades &lt; 30, fwd_wr &lt; 55%, fwd_pf &lt; 1.2, decay &gt; 15%

normalized_wr = min(1.0, (fwd_wr - 0.45) / 0.55)
normalized_pf = min(1.0, (fwd_pf - 1.0) / 2.0)
score = 0.30 × norm_wr + 0.25 × norm_pf + 0.20 × confidence + 0.15 × (agreement/max) + 0.10 × trust

55% weight on proven forward metrics. Zero tolerance for unvalidated strategies.
      </div>
      {sim_table(grok_top20_sim)}

      <h3>Important Caveats</h3>
      <div class="verdict-box bad">
        <b>All PnL values above are UNREALIZED</b> — these positions are still open and can reverse at any time.
        An unrealized total PnL is NOT a valid measure of strategy quality. These snapshots change every few minutes.
        <br><br><b>Portfolio overlap:</b> The four portfolios above are NOT independent — they share many of the same picks
        (same high-scoring picks appear in multiple selection methods). Do not treat them as independent validation.
        <br><br><b>No benchmark:</b> Without comparing to a simple BTC buy-and-hold or a 60/40 crypto index over the same period,
        it is impossible to know if these picks add alpha or are just riding market beta.
      </div>

      <h3>Scoring Formula Limitations</h3>
      <div class="verdict-box neutral">
        <b>Reviewers should note:</b>
        <br>• <b>Confidence is uncalibrated</b> — a 0.8 confidence score does NOT mean 80%% probability of profit. Each system generates its own scale.
        <br>• <b>Agreement caps at 3</b> — the formula uses min(agreement/3, 1), so 3-system and 23-system agreement score identically. This may underweight strong consensus.
        <br>• <b>Forward WR dominates</b> at 25%% weight, but most strategies have 0 forward trades, making this component 0 for the majority of picks.
        <br>• <b>No historical backtest of the formula itself</b> — we have not validated whether this scoring formula would have selected winners in the past.
      </div>

      <div class="verdict-box neutral">
        <b>Recommendation for reviewers:</b> Compare portfolios A-D. Which filtering criteria produces the best risk-adjusted returns?
        If vetted picks (C) outperform raw score (A), the system should raise minimum forward-trade thresholds.
        If agreement picks (D) outperform, cross-system consensus is more valuable than individual strategy metrics.
      </div>
    </div>"""

    # ── Section 7: Leaderboard (top strategies by forward PnL) ──
    lb_rows = ""
    for l in crypto_lb[:30]:
        fwd_pnl = l.get("fwd_total_pnl", 0) or 0
        fwd_wr = l.get("fwd_wr", 0) or 0
        fwd_t = l.get("fwd_trades", 0) or 0
        bt_wr = l.get("bt_wr", 0) or 0
        bt_pf = l.get("bt_pf", 0) or 0
        bt_t = l.get("bt_trades", 0) or 0
        decay = (bt_wr or 0) - (fwd_wr or 0)
        sys_list = ", ".join((l.get("systems") or [])[:3])
        lb_rows += f"""<tr>
          <td><b>{_esc(l.get('strategy','')[:35])}</b></td>
          <td class="dim" style="font-size:11px">{_esc(sys_list)}</td>
          <td class="num">{bt_wr:.1f}%</td><td class="num">{bt_t}</td><td class="num">{bt_pf:.2f}</td>
          <td class="num" style="color:{_pnl_color(fwd_wr-50)}">{fwd_wr:.1f}%</td>
          <td class="num">{fwd_t}</td>
          <td class="num" style="color:{_pnl_color(fwd_pnl)}">{_fmt_pct(fwd_pnl)}</td>
          <td class="num" style="color:{'#22c55e' if abs(decay)<10 else '#ef4444'}">{decay:+.1f}%</td>
        </tr>"""

    lb_section = f"""
    <div class="section">
      <h2>7. Strategy Leaderboard — Top 30 by Forward PnL</h2>
      <p class="dim">Strategies ranked by actual forward-testing profit. Only strategies with ≥3 forward trades shown.</p>
      <div class="table-wrap">
      <table><thead><tr>
        <th>Strategy</th><th>Systems</th>
        <th>BT WR</th><th>BT Trades</th><th>BT PF</th>
        <th>FWD WR</th><th>FWD Trades</th><th>FWD PnL</th><th>Decay</th>
      </tr></thead><tbody>{lb_rows}</tbody></table>
      </div>
    </div>"""

    # ── Section 8: Questions for Reviewers ──
    review_section = """
    <div class="section">
      <h2>8. Questions for AI / Human Reviewers</h2>
      <div class="review-questions">
        <div class="q">
          <h4>Q1: Signal Volume</h4>
          <p>We generate 100-1000+ crypto signals per day across 75 systems. Is this creating too much noise?
          Should we enforce a hard cap (e.g., max 20 picks/day) based on score ranking?</p>
        </div>
        <div class="q">
          <h4>Q2: Entry Quality</h4>
          <p>Our avg loss (-19.88%) exceeds avg win (+17.78%). Should we tighten stop-losses, widen take-profits,
          or implement trailing stops to improve the win/loss ratio?</p>
        </div>
        <div class="q">
          <h4>Q3: Strategy Pruning</h4>
          <p>Many strategies have &lt;5 forward trades. Should we require a minimum forward trade count (e.g., 20)
          before allowing a strategy to generate live signals?</p>
        </div>
        <div class="q">
          <h4>Q4: Backtest Decay</h4>
          <p>Several strategies show 30-50% decay from backtest to forward test. At what decay threshold
          should we auto-demote or disable a strategy?</p>
        </div>
        <div class="q">
          <h4>Q5: Optimal Filtering</h4>
          <p>Based on the simulated portfolios in Section 6, which selection criteria (score, vetted, agreement)
          produces the best risk-adjusted outcome? What filter thresholds would you recommend?</p>
        </div>
        <div class="q">
          <h4>Q6: Position Sizing</h4>
          <p>Currently all picks are equal-weighted. Should we size positions based on confidence score, R:R ratio,
          system trust tier, or forward validation strength?</p>
        </div>
        <div class="q">
          <h4>Q7: What's Actually Working?</h4>
          <p>Looking at the leaderboard (Section 7) and system grades (Section 2), which 3-5 strategies or systems
          show genuine edge that we should double down on?</p>
        </div>
      </div>
    </div>"""

    # ── Section 9: Mercury AI Recommendations ──
    mercury_section = """
    <div class="section">
      <h2>9. Mercury AI Recommendations (External Review)</h2>
      <p class="dim">These recommendations were provided by an external AI reviewer (Mercury) after analyzing the full blueprint. They represent actionable improvements prioritized by impact.</p>

      <h3>Top 5 Strategies to Scale</h3>
      <table><thead><tr><th>#</th><th>Strategy</th><th>Why Scale</th><th>Action</th></tr></thead><tbody>
        <tr><td>1</td><td><b>crypto_rsi_whaleconfirmed_v1</b></td><td>FWD WR 67%, PF 2.1+ — combines RSI with on-chain whale confirmation</td><td>Increase position size, add to PROVEN tier</td></tr>
        <tr><td>2</td><td><b>funding_momentum</b></td><td>Exploits funding rate trends — unique edge not in standard TA</td><td>Extend to more perpetual pairs</td></tr>
        <tr><td>3</td><td><b>crypto_keltner_compression_expansion</b></td><td>Volatility squeeze breakout — well-understood mechanics</td><td>Add multi-timeframe confirmation</td></tr>
        <tr><td>4</td><td><b>crypto_vwap_deviation_reversion_vol</b></td><td>Mean reversion to VWAP with volume filter — institutional flow signal</td><td>Tighten entry window, reduce max hold time</td></tr>
        <tr><td>5</td><td><b>crypto_kalman_trend_residual_reversion</b></td><td>Kalman filter trend + residual reversion — adaptive to regime changes</td><td>Validate with walk-forward optimization</td></tr>
      </tbody></table>

      <h3>Recommended Filtering Thresholds</h3>
      <div class="verdict-box neutral">
        <b>Minimum requirements before a strategy generates live signals:</b>
        <br>• ≥30 forward trades (current: many strategies have &lt;5)
        <br>• FWD WR ≥ 55% (current: no minimum enforced)
        <br>• FWD PF ≥ 1.2 (current: no minimum enforced)
        <br>• BT→FWD Decay ≤ 10% (current: some strategies show 30-50% decay)
        <br><br><b>Impact:</b> This would dramatically reduce signal noise by disabling unproven strategies while preserving strategies with genuine edge.
      </div>

      <h3>Position Sizing Recommendations</h3>
      <table><thead><tr><th>Tier</th><th>Allocation</th><th>Criteria</th></tr></thead><tbody>
        <tr><td><b>Core</b> (60%)</td><td>3-5% per pick</td><td>PROVEN systems, FWD WR≥60%, PF≥1.5, ≥50 trades</td></tr>
        <tr><td><b>Satellite</b> (30%)</td><td>1-2% per pick</td><td>SANDBOX with FWD WR≥55%, PF≥1.2, ≥30 trades</td></tr>
        <tr><td><b>Experimental</b> (10%)</td><td>0.5% per pick</td><td>New strategies, genetic mutations, &lt;30 trades</td></tr>
      </tbody></table>

      <h3>Scoring Formula Restructure</h3>
      <div class="code-block">
CURRENT:  0.25×conf + 0.20×R:R + 0.25×fwd_wr + 0.15×fwd_pf + 0.10×trades + 0.05×agreement
PROPOSED: 0.30×fwd_wr + 0.25×fwd_pf + 0.20×conf + 0.15×agreement + 0.10×trust_tier

Key changes:
  - FWD WR increased 0.25→0.30 (most predictive metric)
  - R:R removed (redundant with PF, can be gamed by wide targets)
  - Trust tier added at 0.10 (rewards battle-tested systems)
  - Agreement increased 0.05→0.15 (cross-system consensus is strong signal)
      </div>

      <h3>Priority Action Items</h3>
      <div class="verdict-box neutral">
        <b>Immediate (this week):</b>
        <br>1. Implement hard gates in scanner: zero score if fwd_trades&lt;30, fwd_wr&lt;55%, fwd_pf&lt;1.2, decay&gt;15%
        <br>2. Cap daily signals at 20 via top-score selection (cuts ~90% noise)
        <br>3. Implement kill criteria for grade-F systems (see Section 0)
        <br>4. Add trailing stop at 70% R:R target — tighten SL to min(ATR×0.5×R:R, entry×0.005)
        <br><br><b>Short-term (2 weeks):</b>
        <br>5. Switch to Grok normalized scoring (compare Portfolio G vs E vs A-D)
        <br>6. Implement tiered position sizing: position_size = min(0.05, (score×R:R) / sum_scores)
        <br>7. Add BTC buy-and-hold benchmark comparison to all portfolio sims
        <br>8. Adjust all PnL metrics -0.40% round-trip to account for exchange fees
        <br><br><b>Medium-term (1 month):</b>
        <br>9. Walk-forward optimization for top 5 strategies
        <br>10. Add realized PnL tracking (currently all PnL is unrealized)
        <br>11. Build correlation check: prune_correlated_picks to avoid concentrated bets
        <br>12. Build a proper backtest of the scoring formula itself on historical picks
      </div>

      <h3>Confirmed Red Flags (3/3 AI Reviewers Agree)</h3>
      <div class="verdict-box bad">
        <br>• <b>~86%% of active picks come from Grade F systems</b> (Codex finding) — the system is feeding mostly unvalidated noise into portfolios.
        <br>• <b>Over-reliance on unvetted ML/genetic systems</b> — high decay rates indicate overfitting. Most should be killed or sandboxed.
        <br>• <b>Missing fees in PnL calculation</b> — all metrics should subtract -0.40%% round-trip (0.10%% taker × 2 sides + ~0.05%% slippage × 2).
        <br>• <b>No correlation checks</b> — multiple picks on the same asset/direction from different systems create concentrated risk.
        <br>• <b>Duplicate stacking</b> — multiple systems bet same symbol+direction, treated as independent alpha when it's concentrated risk.
        <br>• <b>Revival_Mutated_* strategies</b> should be blocked from live capital entirely (paper-only until validated).
        <br>• <b>Confidence is double-counted</b> with FWD WR (they correlate, weighting both inflates scores).
        <br>• <b>Data integrity</b>: closed ≠ wins + losses in some systems — phantom/unresolved trades exist.
        <br><br><b>Projected impact of implementing filters + scoring: +15-25%% expectancy boost within 30 days.</b>
      </div>

      <h3>Codex (GPT-5.3) Additional Recommendations</h3>
      <div class="verdict-box neutral">
        <b>2-Stage Scoring (replaces single formula):</b>
        <br><b>Stage 1 — Hard Pass/Fail Gate:</b>
        <br>• fwd_trades ≥ 50 (strictest threshold across all reviewers)
        <br>• fwd_pf_net ≥ 1.15 (after fees)
        <br>• net expectancy > 0
        <br>• health = healthy
        <br>• NOT Revival_Mutated_*
        <br>• Grade A/B only (C on strict probation)
        <br><br><b>Stage 2 — Rank by uncertainty-adjusted net expectancy</b> (not raw WR):
        <br>• Use expectancy = (WR × avg_win) − ((1−WR) × avg_loss) − round_trip_cost
        <br>• Penalize low sample size with uncertainty factor: expectancy × (1 − 1/sqrt(trades))
        <br>• One position per symbol+direction (no duplicate stacking)
        <br><br><b>Best portfolio method:</b> D (High Agreement) + deduplication + vetting gate
        <br><b>Kill criteria:</b> Probation at rolling-20 PF &lt; 0.9; Kill at rolling-50 PF &lt; 0.95 or decay &gt; 15pp
      </div>
    </div>"""

    # ── Section 0: Glossary + Architecture ──
    # Count grade F systems
    grade_f = sum(1 for s in sys_with_data if (s.get("closed_picks", 0) or 0) < 5 and (s.get("win_rate", 0) or 0) < 45)
    total_sys = len(sys_with_data)

    # Compute average hold time from active picks
    avg_age = sum(float(p.get("age_hours", 0) or 0) for p in crypto_active) / max(len(crypto_active), 1)

    glossary_section = f"""
    <div class="section">
      <h2>0. Glossary, Architecture & Assumptions</h2>

      <h3>Key Terms</h3>
      <table><thead><tr><th>Term</th><th>Definition</th></tr></thead><tbody>
        <tr><td><b>WR</b> (Win Rate)</td><td>% of closed trades that were profitable (hit TP or closed in profit)</td></tr>
        <tr><td><b>PF</b> (Profit Factor)</td><td>Gross wins / Gross losses. PF &gt; 1.0 = profitable. PF &gt; 1.5 = strong edge.</td></tr>
        <tr><td><b>R:R</b> (Risk:Reward)</td><td>Distance to take-profit / distance to stop-loss. R:R of 2.0 means TP is 2x further than SL.</td></tr>
        <tr><td><b>Expectancy</b></td><td>(WR × Avg Win) − ((1−WR) × Avg Loss). Expected PnL per trade. Must be positive for profitability.</td></tr>
        <tr><td><b>Confidence</b></td><td>Strategy-specific score 0.0−1.0 generated by each system based on its internal signal strength assessment. NOT calibrated (0.8 confidence ≠ 80% probability).</td></tr>
        <tr><td><b>BT</b> (Backtest)</td><td>Performance on historical data. Subject to look-ahead bias, curve-fitting, and survivorship bias.</td></tr>
        <tr><td><b>FWD</b> (Forward Test)</td><td>Performance on live market data after the strategy was deployed. The gold standard for validation.</td></tr>
        <tr><td><b>Decay</b></td><td>BT WR − FWD WR. Positive = strategy performs worse live (likely overfitted). Negative = improved or BT data missing.</td></tr>
        <tr><td><b>Health</b></td><td>Strategy status: <b>healthy</b> = performing within expected parameters. <b>degrading</b> = recent drawdown or declining WR. <b>watch</b> = under observation. <b>None</b> = status not yet classified.</td></tr>
        <tr><td><b>Agreement</b></td><td>Number of independent system groups flagging the same symbol+direction. Higher = more consensus. Capped at system group level (deduplicated).</td></tr>
        <tr><td><b>Trust Tier</b></td><td>PROVEN (1.0x weight) → SANDBOX (0.25x, default for new systems) → PROBATION (0.10−0.15x) → DEMOTED (0.25x, asset-specific failures)</td></tr>
      </tbody></table>

      <h3>System Architecture</h3>
      <div class="code-block">
75 CRYPTO SYSTEMS generate signals every 15-30 min via GitHub Actions
  │
  ├── PROVEN: battleground, alpha_engine (forward-validated, full trust)
  ├── GENETIC: genome_gp, DARWIN variants (GP expression trees evolving buy/sell formulas)
  │     └── Function set: RSI, MACD, EMA, Volume, ATR, Bollinger — standard TA indicators
  │     └── Fitness: Sharpe ratio on 6-month rolling window, penalized by trade count
  │     └── Population: 500 individuals, 100 generations, tournament selection
  ├── ML: mercury2 (XGBoost), ml_bg_system_a-f (various ML ensembles), crypto_ml_edge
  ├── REVIVAL: Auto-mutates dormant strategies when stale &gt;2 days (parameter ±10-30%)
  │     └── ⚠ Known risk: creates untested variants. Safeguard: enters as SANDBOX tier (0.25x weight)
  ├── KIMI: 81-algorithm scanner (fear/greed, order book, funding rate, whale detection)
  └── AGGREGATORS: super_signals, aggregated_picks (consensus from multiple systems)
  │
  ▼
SCORING ENGINE: ranks each pick 0-100 based on weighted formula
  │
  ▼
AUDIT DASHBOARD: tracks all picks, monitors TP/SL resolution, computes performance
      </div>

      <h3>Fee & Execution Assumptions</h3>
      <table><thead><tr><th>Parameter</th><th>Value</th><th>Notes</th></tr></thead><tbody>
        <tr><td>Exchange fees</td><td>0.10% taker per side</td><td>Binance standard. Round-trip cost = 0.20%</td></tr>
        <tr><td>Slippage</td><td>~0.05% estimated</td><td>For liquid pairs (BTC, ETH). Small-cap may be higher.</td></tr>
        <tr><td>Funding rate</td><td>Not included</td><td>Perpetual swap funding can be +/- 0.01-0.10% per 8h. Material for holds &gt;24h.</td></tr>
        <tr><td>PnL calculation</td><td>Entry vs TP/SL hit</td><td>Does NOT include fees. Actual returns ~0.20-0.40% worse than shown per trade.</td></tr>
        <tr><td>Price source</td><td>Binance spot API</td><td>Live prices fetched on page load. During outages, falls back to CoinGecko.</td></tr>
        <tr><td>Avg hold time</td><td>{avg_age:.0f}h ({avg_age/24:.1f} days)</td><td>Computed from current active picks. Historical may differ.</td></tr>
      </tbody></table>

      <h3>System Lifecycle</h3>
      <table><thead><tr><th>Stage</th><th>Criteria</th><th>Trust Weight</th></tr></thead><tbody>
        <tr><td>New / SANDBOX</td><td>Default for all new systems. &lt;50 closed trades.</td><td>0.25x</td></tr>
        <tr><td>Under Review</td><td>10-50 closed trades. Performance monitored.</td><td>0.25x</td></tr>
        <tr><td>PROVEN</td><td>50+ closed trades, WR ≥ 50%, PF ≥ 1.0, documented forward results.</td><td>0.8−1.0x</td></tr>
        <tr><td>PROBATION</td><td>Documented poor performance: broken risk mgmt, consistently losing, or system errors.</td><td>0.10−0.15x</td></tr>
        <tr><td>DEMOTED</td><td>Strategy works on some assets but fails on others (asset-specific demotion).</td><td>0.25x</td></tr>
        <tr><td>Killed</td><td>Auto-kill when criteria met (see below). {grade_f} of {total_sys} systems are grade F.</td><td>0x (disabled)</td></tr>
      </tbody></table>

      <h3>Kill Criteria (Mercury AI Recommended)</h3>
      <div class="verdict-box bad">
        <b>A system/strategy should be automatically KILLED (disabled) when ANY of these are met:</b>
        <br>• <b>FWD WR &lt; 40%</b> after ≥30 closed trades — consistently below random chance
        <br>• <b>FWD PF &lt; 0.8</b> after ≥30 closed trades — losing more than winning
        <br>• <b>BT→FWD Decay &gt; 25%</b> — strategy is severely overfitted to historical data
        <br>• <b>Max Drawdown &gt; 30%</b> on $100 position sizing — unacceptable risk
        <br>• <b>No trades generated</b> in 14+ days — dormant/broken system
        <br>• <b>3 consecutive losing months</b> — persistent underperformance
        <br><br>⚠️ <b>Current status:</b> Kill mechanism is NOT yet implemented. {grade_f}/{total_sys} grade-F systems remain active, generating noise and diluting signal quality.
      </div>
    </div>"""

    # ── Section 10: Forex & Futures Picks ──
    forex_picks = forex_picks or []
    futures_picks = futures_picks or []
    all_ff = forex_picks + futures_picks

    ff_pick_rows = ""
    for p in all_ff:
        sym = p.get("symbol", "")
        cat = p.get("category", "")
        cat_badge = f'<span style="background:{"#06b6d4" if cat == "forex" else "#f59e0b"};color:#000;padding:1px 6px;border-radius:4px;font-size:10px;font-weight:700">{cat.upper()}</span>'
        sig = p.get("signal_type", p.get("direction", ""))
        entry = p.get("entry_price", 0)
        tp = p.get("take_profit", 0)
        sl = p.get("stop_loss", 0)
        conf = float(p.get("confidence", 0) or 0)
        rr = float(p.get("risk_reward", p.get("rr_ratio", 0)) or 0)
        pnl = float(p.get("unrealized_pnl_pct", p.get("pnl_pct", 0)) or 0)
        strat = p.get("strategy", "")[:30]
        reason = _esc(str(p.get("reason", ""))[:80])
        hold = int(p.get("hold_days", 0) or 0)
        sig_color = "#22c55e" if sig in ("BUY", "LONG") else "#ef4444"
        ff_pick_rows += f"""<tr>
          <td>{_esc(sym)}</td>
          <td>{cat_badge}</td>
          <td style="color:{sig_color};font-weight:700">{sig}</td>
          <td class="num">{entry}</td><td class="num">{tp}</td><td class="num">{sl}</td>
          <td class="num">{conf:.2f}</td><td class="num">{rr:.1f}</td>
          <td class="num" style="color:{_pnl_color(pnl)}">{_fmt_pct(pnl)}</td>
          <td class="num">{hold}d</td>
          <td class="dim" style="font-size:11px">{_esc(strat)}</td>
          <td class="dim" style="font-size:11px">{reason}</td>
        </tr>"""

    # Strategy breakdown for forex/futures
    ff_strat_counts = Counter(p.get("strategy", "") for p in all_ff)
    ff_sym_counts = Counter(p.get("symbol", "") for p in all_ff)
    ff_dir_counts = Counter(p.get("signal_type", p.get("direction", "")) for p in all_ff)

    ff_summary_cards = f"""
      <div class="card-grid">
        <div class="card"><div class="card-label">Forex Picks</div><div class="card-val" style="color:var(--cyan)">{len(forex_picks)}</div></div>
        <div class="card"><div class="card-label">Futures Picks</div><div class="card-val" style="color:var(--yellow)">{len(futures_picks)}</div></div>
        <div class="card"><div class="card-label">Total Active</div><div class="card-val">{len(all_ff)}</div></div>
        <div class="card"><div class="card-label">Unique Symbols</div><div class="card-val">{len(ff_sym_counts)}</div></div>
        <div class="card"><div class="card-label">Strategies</div><div class="card-val">{len(ff_strat_counts)}</div></div>
        <div class="card"><div class="card-label">BUY Signals</div><div class="card-val" style="color:var(--green)">{ff_dir_counts.get("BUY", 0) + ff_dir_counts.get("LONG", 0)}</div></div>
        <div class="card"><div class="card-label">SELL Signals</div><div class="card-val" style="color:var(--red)">{ff_dir_counts.get("SELL", 0) + ff_dir_counts.get("SHORT", 0)}</div></div>
      </div>"""

    # Market hours note
    ff_market_note = """
      <div class="verdict-box neutral">
        <b>Market Hours:</b>
        <br>Forex: 24/5 — Sunday 5 PM ET to Friday 5 PM ET (continuous)
        <br>Futures (ES, NQ): Sunday 6 PM ET to Friday 5 PM ET (with daily halt 5-6 PM ET)
        <br><br><b>Key Strategies:</b>
        <br>Connors RSI-2 on ES=F/NQ=F: Extends our most proven strategy (75.7% WR on SPY, p=6e-6) to futures. ES/NQ track SPY/QQQ with near-perfect correlation but trade extended hours.
        <br>Turn-of-Month on ES=F/NQ=F: Lakonishok &amp; Smidt (1988) TOM effect applies equally to index futures.
        <br>Forex: 7 strategies including carry trade, mean reversion, JPY risk-off, DXY correlation, BB squeeze, session momentum, and DXY RSI fade.
      </div>"""

    forex_futures_section = f"""
    <div class="section">
      <h2>10. Forex &amp; Futures — Active Picks</h2>
      <p class="dim">Non-crypto picks from forex (7 strategies) and index futures (Connors RSI-2, TOM). These extend proven equity strategies to 24/5 markets.</p>
      {ff_summary_cards}
      {ff_market_note}
      <h3>Active Picks ({len(all_ff)} total)</h3>
      <div class="table-wrap">
      <table><thead><tr>
        <th>Symbol</th><th>Class</th><th>Signal</th><th>Entry</th><th>TP</th><th>SL</th>
        <th>Conf</th><th>R:R</th><th>PnL</th><th>Hold</th><th>Strategy</th><th>Reason</th>
      </tr></thead><tbody>{ff_pick_rows if ff_pick_rows else '<tr><td colspan="12" class="dim" style="text-align:center">No active forex/futures picks at this time.</td></tr>'}</tbody></table>
      </div>
    </div>"""

    # ── Assemble full page ──
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Crypto Trading Blueprint — System Analysis for Review</title>
<style>
  :root {{ --bg: #0a0a12; --card: #12122a; --border: #1e1e3a; --text: #e0e0f0; --dim: #8888aa; --green: #22c55e; --red: #ef4444; --yellow: #f59e0b; --cyan: #06b6d4; --purple: #a78bfa; }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:var(--bg); color:var(--text); font-family:'Inter','Segoe UI',system-ui,sans-serif; font-size:14px; line-height:1.6; padding:20px; max-width:1400px; margin:0 auto; }}
  h1 {{ font-size:28px; margin-bottom:8px; background:linear-gradient(135deg, var(--cyan), var(--purple)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
  h2 {{ font-size:20px; color:var(--cyan); margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid var(--border); }}
  h3 {{ font-size:16px; color:var(--purple); margin:16px 0 8px; }}
  h4 {{ font-size:14px; color:var(--yellow); margin-bottom:4px; }}
  .dim {{ color:var(--dim); font-size:12px; }}
  .section {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:20px 24px; margin-bottom:20px; }}
  .card-grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(150px,1fr)); gap:10px; margin:12px 0; }}
  .card {{ background:var(--bg); border:1px solid var(--border); border-radius:8px; padding:10px 14px; text-align:center; }}
  .card-label {{ font-size:11px; color:var(--dim); text-transform:uppercase; letter-spacing:0.5px; }}
  .card-val {{ font-size:20px; font-weight:700; margin-top:4px; }}
  .table-wrap {{ overflow-x:auto; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; margin:8px 0; }}
  th {{ background:#0f1628; color:var(--dim); font-size:11px; text-transform:uppercase; letter-spacing:0.3px; padding:8px 6px; text-align:left; border-bottom:1px solid var(--border); white-space:nowrap; }}
  td {{ padding:6px; border-bottom:1px solid #1a1a30; }}
  .num {{ text-align:right; font-family:'Consolas','Fira Code',monospace; }}
  tr:hover {{ background:rgba(255,255,255,0.03); }}
  .verdict-box {{ padding:14px 18px; border-radius:8px; margin:12px 0; font-size:13px; line-height:1.6; }}
  .verdict-box.bad {{ background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); }}
  .verdict-box.good {{ background:rgba(34,197,94,0.08); border:1px solid rgba(34,197,94,0.3); }}
  .verdict-box.neutral {{ background:rgba(167,139,250,0.08); border:1px solid rgba(167,139,250,0.3); }}
  .sim-summary {{ display:flex; flex-wrap:wrap; gap:16px; padding:10px 14px; background:var(--bg); border-radius:8px; margin:8px 0; font-size:13px; }}
  .code-block {{ background:#0a0a16; border:1px solid var(--border); border-radius:6px; padding:12px 16px; font-family:'Consolas','Fira Code',monospace; font-size:12px; white-space:pre-wrap; margin:8px 0; color:var(--cyan); }}
  .review-questions {{ display:grid; gap:12px; }}
  .q {{ background:var(--bg); border:1px solid var(--border); border-radius:8px; padding:12px 16px; }}
  .q p {{ color:var(--dim); font-size:13px; margin-top:4px; }}
  .header-meta {{ color:var(--dim); font-size:12px; margin-bottom:20px; }}
  .toc {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:16px 24px; margin-bottom:20px; }}
  .toc a {{ color:var(--cyan); text-decoration:none; }}
  .toc a:hover {{ text-decoration:underline; }}
  .toc ol {{ padding-left:20px; }}
  .toc li {{ margin:4px 0; }}
  @media(max-width:768px) {{ body {{ padding:10px; }} .card-grid {{ grid-template-columns:repeat(2,1fr); }} }}
</style>
</head>
<body>
<h1>Crypto Trading Blueprint</h1>
<div class="header-meta">
  <p>Comprehensive analysis of our algorithmic crypto trading systems for external review.</p>
  <p>Generated: {now_str} | Data snapshot: {gen_at[:19] if gen_at else 'unknown'} UTC | {len(crypto_systems)} systems | {len(crypto_active):,} active crypto picks</p>
  <p><b>Purpose:</b> Provide enough context for another AI or human trader to evaluate our system, identify weaknesses, and suggest improvements.</p>
</div>

<div class="toc">
  <b>Table of Contents</b>
  <ol>
    <li><a href="#s0">Glossary & Architecture</a> — Key terms, system design, fee assumptions, lifecycle rules</li>
    <li><a href="#s1">Executive Summary</a> — Overall crypto performance (honest assessment)</li>
    <li><a href="#s2">System Breakdown</a> — Per-system stats, grades, descriptions</li>
    <li><a href="#s3">Strategy Detail</a> — Top 30 strategies with BT/FWD metrics</li>
    <li><a href="#s3b">Strategy Logic Reference</a> — What each strategy actually does (entry/exit rules)</li>
    <li><a href="#s4">Backtest vs Forward</a> — Decay analysis (overfitting detection)</li>
    <li><a href="#s5">Daily Volume</a> — Signal generation rate, last 7 days</li>
    <li><a href="#s6">Optimal Picks Simulation</a> — What if we only traded top-scored picks?</li>
    <li><a href="#s7">Strategy Leaderboard</a> — Top 30 by forward PnL</li>
    <li><a href="#s8">Questions for Reviewers</a> — Specific feedback requested</li>
    <li><a href="#s9">Mercury AI Recommendations</a> — External review action items</li>
    <li><a href="#s10">Forex &amp; Futures</a> — Active forex/futures picks with market hours and strategy details</li>
  </ol>
</div>

<div id="s0">{glossary_section}</div>
<div id="s1">{exec_summary}</div>
<div id="s2">{systems_section}</div>
<div id="s3">{strat_section}</div>
<div id="s3b">{strat_logic_section}</div>
<div id="s4">{bvf_section}</div>
<div id="s5">{daily_section}</div>
<div id="s6">{sim_section}</div>
<div id="s7">{lb_section}</div>
<div id="s8">{review_section}</div>
<div id="s9">{mercury_section}</div>
<div id="s10">{forex_futures_section}</div>

<div class="section" style="text-align:center; padding:30px;">
  <p class="dim">Trading Blueprint v2.0 — Auto-generated from live audit data</p>
  <p class="dim">Data freshness: updates every 15 minutes via GitHub Actions</p>
  <p class="dim">Source: <a href="https://findtorontoevents.ca/audit/" style="color:var(--cyan)">Audit Dashboard</a></p>
</div>
</body>
</html>"""

    return html


if __name__ == "__main__":
    generate_blueprint()
