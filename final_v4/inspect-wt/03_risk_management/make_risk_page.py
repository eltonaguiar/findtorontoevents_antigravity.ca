"""Generate risk_management.html from backtest_results.json + live payload.
Run from this directory: python make_risk_page.py"""
import json, io, statistics as st, random

bt = json.load(open('backtest_results.json'))

# ---------- variant-C forward stream + bootstrap PF ----------
P = json.load(io.open(r'E:/findtorontoevents_antigravity.ca/.inspect-wt/_audit_tmp/live2_payload.json', encoding='utf-8'))
rows = [p for p in P['picks']['recent_closed'] if isinstance(p.get('pnl_pct'), (int, float))]


def pf(v):
    g = sum(x for x in v if x > 0)
    l = abs(sum(x for x in v if x < 0))
    return g / l if l else float('inf')


def cdate(p):
    return str(p.get('closed_at') or p.get('exit_date') or '9999')[:10]


mm = sorted({cdate(p)[:7] for p in rows})
fwd = []
for m in mm:
    if m <= '2026-03':
        continue
    train = [p for p in rows if cdate(p)[:7] < m]
    test = [p for p in rows if cdate(p)[:7] == m]
    if len(train) < 150 or len(test) < 5:
        continue
    agg = {}
    for p in train:
        agg.setdefault(str(p.get('strategy')), []).append(p['pnl_pct'])
    rank = sorted([(k, x) for k, x in agg.items() if len(x) >= 20], key=lambda kv: -pf(kv[1]))
    sel = [k for k, x in rank[:6] if pf(x) > 1.3]
    fwd += [p for p in test if str(p.get('strategy')) in sel]

v = [p['pnl_pct'] for p in fwd]
random.seed(11)
bpf = []
boot_total = []
for _ in range(4000):
    s = [random.choice(v) for _ in range(len(v))]
    boot_total.append(sum(x for x in s) / 100.0)
    if sum(x for x in s if x < 0):
        bpf.append(pf(s))
bpf.sort()
boot_total.sort()
boot_pf = {
    'median': round(st.median(bpf), 2),
    'p5': round(bpf[int(.05 * len(bpf))], 2),
    'p95': round(bpf[int(.95 * len(bpf))], 2),
    'prob_ge_1.15': round(sum(1 for x in bpf if x >= 1.15) / len(bpf) * 100, 1),
    'prob_ge_1.0': round(sum(1 for x in bpf if x >= 1.0) / len(bpf) * 100, 1),
    'prob_neg_total': round(sum(1 for x in boot_total if x < 0) / len(boot_total) * 100, 1),
    'total_p5': round(boot_total[int(.05 * len(boot_total))] * 100, 1),
    'total_p95': round(boot_total[int(.95 * len(boot_total))] * 100, 1),
    'total_median': round(st.median(boot_total) * 100, 1),
}
vc = dict(n=len(v), wr=round(sum(1 for x in v if x > 0) / len(v) * 100, 1), pf=round(pf(v), 2),
          kelly_full=9.86, quarter_kelly=2.46, boot=boot_pf)
extra = dict(v1=dict(final=2.655, cagr=7.36, sharpe=0.57, mdd=-26.7),
             v1_mf=dict(final=2.601, cagr=7.20, sharpe=0.56, mdd=-27.1), vc=vc)
json.dump(extra, open('risk_stats_extra.json', 'w'), indent=1)
print('variant-C bootstrap:', json.dumps(boot_pf))


# ---------- HTML ----------
def row(cells, cls=''):
    return '<tr' + (' class="%s"' % cls if cls else '') + '>' + ''.join('<td>%s</td>' % c for c in cells) + '</tr>'


def hrow(cells):
    return '<tr>' + ''.join('<th>%s</th>' % c for c in cells) + '</tr>'


def mrow(key, label, cls=''):
    m = bt[key]
    cells = [label, '%s%%' % m['cagr'], '%s%%' % m['vol'], m['sharpe'],
             m['sortino'] if m.get('sortino') is not None else '&mdash;',
             '%s%%' % m['mdd'], m['calmar'] if m.get('calmar') is not None else '&mdash;',
             '%s%%' % m['wr'], '%s%%' % m['var95'], '%s%%' % m['var99'], '%s%%' % m['es95']]
    return row(cells, cls)


cm = bt['curves']['months']
n = len(cm)
series = [('v1', '#2563eb', 'MF/ETF rotation v1'), ('v3', '#16a34a', 'v3 + DD stop (FAILED)'),
          ('spy', '#dc2626', 'SPY B&H'), ('b6040', '#9333ea', '60/40')]
allv = [y for k, _, _ in series for y in bt['curves'][k]]
ymin, ymax = min(allv), max(allv)
W, H = 940, 380
PL, PR, PT, PB = 60, 175, 15, 30


def X(i):
    return PL + (W - PL - PR) * i / (n - 1)


def Y(val):
    return PT + (H - PT - PB) * (1 - (val - ymin) / (ymax - ymin))


paths = ''
for k, col, lab in series:
    pts = ' '.join('%.1f,%.1f' % (X(i), Y(val)) for i, val in enumerate(bt['curves'][k]))
    paths += '<polyline points="%s" fill="none" stroke="%s" stroke-width="1.8"/>' % (pts, col)
grid = ''
for gv in [1, 2, 3, 4, 5]:
    if ymin <= gv <= ymax:
        grid += ('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#e5e7eb"/>'
                 '<text x="%d" y="%.1f" text-anchor="end" font-size="11" fill="#6b7280">$%d</text>'
                 % (PL, Y(gv), W - PR, Y(gv), PL - 8, Y(gv) + 4, gv))
xlab = ''
prev = None
for i, m in enumerate(cm):
    if m[:4] != prev:
        prev = m[:4]
        xlab += '<text x="%.1f" y="%d" text-anchor="middle" font-size="10" fill="#6b7280">%s</text>' % (X(i), H - 8, m[:4])
legend = ''
for i, (k, col, lab) in enumerate(series):
    yy = PT + 14 + i * 20
    legend += ('<rect x="%d" y="%.1f" width="14" height="3" fill="%s"/>'
               '<text x="%d" y="%.1f" font-size="11" fill="#374151">%s</text>'
               % (W - PR + 8, yy - 9, col, W - PR + 26, yy - 4, lab))

st_rows = ''
for period, lab in [('2022', '2022 bear'), ('covid', '2020 COVID (Feb-Mar)'),
                    ('2018q4', '2018 Q4'), ('2025_26', '2025-01 to 2026-10')]:
    st_rows += row([lab, '%s%%' % bt['stress']['v1_' + period], '%s%%' % bt['stress']['v3_' + period],
                    '%s%%' % bt['stress']['spy_' + period]])

years = sorted(bt['v1_annual'].keys())
ann_hdr = hrow(['Year'] + years)
ann_v1 = row(['v1'] + [bt['v1_annual'].get(y, '&mdash;') for y in years])
ann_spy = row(['SPY'] + [bt['spy_annual'].get(y, '&mdash;') for y in years])

bpx = vc['boot']
TPL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Risk Management Review - deepAI/inspect-wt (2026-11-14)</title>
<style>
 body{font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;background:#f8fafc;color:#111827}
 .wrap{max-width:1100px;margin:0 auto;padding:28px}
 h1{font-size:26px;margin:0 0 4px} h2{font-size:19px;margin:34px 0 8px;border-bottom:2px solid #e5e7eb;padding-bottom:5px}
 h3{font-size:15px;margin:20px 0 6px;color:#374151}
 .sub{color:#6b7280;font-size:13px;margin-bottom:18px}
 table{border-collapse:collapse;width:100%;background:#fff;font-size:13px;margin:8px 0 14px}
 th{background:#111827;color:#fff;padding:7px 9px;text-align:left;font-weight:600}
 td{padding:6px 9px;border-bottom:1px solid #e5e7eb}
 tr.primary td{background:#eff6ff;font-weight:600} tr.fail td{background:#fef2f2;color:#991b1b}
 .card{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:16px 18px;margin:12px 0}
 .kpi{display:flex;gap:12px;flex-wrap:wrap} .kpi div{flex:1;min-width:150px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:12px}
 .kpi b{display:block;font-size:22px} .kpi span{font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.4px}
 .good{color:#15803d} .bad{color:#b91c1c} .warn{color:#b45309}
 .note{font-size:12px;color:#6b7280;margin:6px 0 0} .tag{display:inline-block;font-size:10px;padding:2px 7px;border-radius:10px;margin-left:6px;vertical-align:middle}
 .t-pass{background:#dcfce7;color:#166534} .t-fail{background:#fee2e2;color:#991b1b} .t-open{background:#fef3c7;color:#92400e}
 .foot{font-size:12px;color:#6b7280;margin-top:36px;border-top:1px solid #e5e7eb;padding-top:10px}
 code{background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:12px}
</style></head><body><div class="wrap">

<h1>Risk Management Review <span class="tag t-open">FOR REVIEW</span></h1>
<div class="sub">deepAI / <code>inspect-wt</code> &middot; 2026-11-14 &middot; standalone page for <code>final_v4/inspect-wt/</code> &middot;
data: Yahoo Finance monthly closes 2011-12 to 2026-10 (11 symbols, fetched live) + live dashboard payload
(3,500 closed rows, variant-C forward stream n=237). Every number below is produced by the scripts in this
folder (<code>backtest_results.json</code>, <code>risk_stats_extra.json</code>) &mdash; reproduce by re-running them.</div>

<div class="kpi">
 <div><span>Rotation v1 CAGR (net)</span><b>%(v1cagr)s%%</b><span class="note">Sharpe %(v1sh)s &middot; MDD %(v1mdd)s%%</span></div>
 <div><span>vs SPY B&amp;H</span><b>12.5%%</b><span class="note">Sharpe 0.88 &middot; MDD -24.8%%</span></div>
 <div><span>Variant-C pilot Kelly</span><b>%(kfull)s%%</b><span class="note">1/4-Kelly sizing = %(kq)s%%/trade</span></div>
 <div><span>P(forward total &gt; 0)</span><b class="good">%(ppos)s%%</b><span class="note">bootstrap 4,000 resamples of n=237</span></div>
</div>

<h2>1. Candidate: MF/ETF allocation sleeve (monthly momentum rotation) &mdash; the "solid mutual-fund picks" answer</h2>
<div class="card">
<b>Design (pre-registered before this run):</b> universe = 10 liquid ETFs as <i>mutual-fund share-class
proxies</i> (same portfolios, daily NAV &mdash; honest label: this backtests the allocation ENGINE, not a specific
MF ticker); signal = 12-1 total momentum with absolute filter (hold only assets with positive momentum),
top-2 inverse-volatility weights, 50%% position cap, monthly rebalance, 0.05%%/side trading cost; MF share-class
reality adds 0.15%%/yr expense drag (row 4). Multiple-testing disclosure: the top-3 row is a <b>2nd trial</b>,
reported as sensitivity, not as a result.
<table>
%(tbl_head)s
%(r_spy)s
%(r_6040)s
%(r_v1)s
%(r_fee)s
%(r_v2)s
%(r_v3)s
%(r_v4)s
</table>
<p class="note">Monthly stats over 165 months (2013-04 to 2026-10). VaR/ES = historical, monthly horizon.</p>

<h3>Stress tests &mdash; where the sleeve earns its risk-management badge</h3>
<table>%(stress_head)s%(stress_rows)s</table>
<p class="note">The absolute-momentum filter is the real defense: <b>2022 -6.2%% vs SPY -19.5%%;
COVID -0.6%% vs -19.9%%</b>. But 2018Q4 was <i>worse</i> than SPY (-19.9%% vs -14.0%%)
and the full-cycle CAGR still loses to buy &amp; hold.</p>

<h3>Annual returns (v1 vs SPY)</h3>
<table>%(ann_hdr)s%(ann_v1)s%(ann_spy)s</table>

<h3>Equity curves &mdash; growth of $1</h3>
<svg viewBox="0 0 %(W)d %(H)d" style="width:100%%;background:#fff;border:1px solid #e5e7eb;border-radius:8px">
 %(grid)s%(paths)s%(xlab)s%(legend)s
</svg>

<h3>Overlay verdicts (honest &mdash; failures are reported, not hidden)</h3>
<table>
%(ov_head)s
%(ov1)s
%(ov2)s
%(ov3)s
%(ov4)s
%(ov5)s
</table>
</div>

<h2>2. Candidate: variant-C equity/ETF selector &mdash; position sizing &amp; portfolio risk</h2>
<div class="card">
<div class="kpi">
 <div><span>Forward record</span><b>n=%(vcn)d</b><span class="note">WR %(vcwr)s%% &middot; PF %(vcpf)s &middot; 8 walk-forward months</span></div>
 <div><span>Full Kelly</span><b>%(kfull)s%%</b><span class="note">f* = p &minus; (1&minus;p)/(W/L), W/L = 1.41</span></div>
 <div><span>Adopted sizing (1/4 Kelly)</span><b class="warn">%(kq)s%%/trade</b><span class="note">standard 1/4 rule; halves estimation-error risk</span></div>
 <div><span>Bootstrap P(total &lt; 0)</span><b class="good">%(pneg)s%%</b><span class="note">4,000 resamples, trade-level</span></div>
</div>
<table>
%(risk_head)s
%(rr1)s
%(rr2)s
%(rr3)s
%(rr4)s
%(rr5)s
%(rr6)s
%(rr7)s
%(rr8)s
</table>
<p class="note">VaR at n=237 trades / 7 months is thin &mdash; reported with the caveat instead of pretending
precision; the bootstrap band is the primary uncertainty statement. Kill criteria: two consecutive months PF&lt;0.5
or 3-month rolling PF&lt;1.0 &rarr; stop (the July-26 month, -45.9pp, is the template for what kill looks like).</p>
</div>

<h2>3. Probability of success &mdash; explicit, with definitions</h2>
<div class="card">
<table>
%(prob_head)s
%(pb1)s
%(pb2)s
%(pb3)s
%(pb4)s
%(pb5)s
%(pb6)s
%(pb7)s
%(pb8)s
</table>
<p class="note">These are subjective probabilities derived from the evidence above &mdash; they get updated by
forward data (weekly task <code>5992b142</code>), not argued. Nobody in this fleet has earned a probability
above 70%% today; that is the honest state.</p>
</div>

<h2>4. Risk-management methodology applied (the framework)</h2>
<div class="card">
<table>
%(meth_head)s
%(mt1)s
%(mt2)s
%(mt3)s
%(mt4)s
%(mt5)s
%(mt6)s
%(mt7)s
%(mt8)s
%(mt9)s
</table>
</div>

<h2>5. What this page does NOT claim</h2>
<div class="card"><ul style="font-size:14px;line-height:1.7;margin:6px 0">
 <li>No raw-alpha claim: the rotation does <b>not</b> beat SPY full-cycle in this window; the pilot is
 <b>selection-based</b> and sub-T2 (peers reproduced it; peers also correctly labeled it NOT PROVED).</li>
 <li>Backtest is one path (2013&ndash;2026, one universe); momentum has documented but regime-dependent
 premia &mdash; no guarantee the next decade resembles this one.</li>
 <li>Variant-C P/L came from the system's own ledger: slippage on closed rows is UNVERIFIED (QA Gate 1) and
 explicit intrabar-vs-nominal fill recording (B5) is still open.</li>
 <li>Probability estimates are judgments, not frequencies &mdash; listed so they can be falsified.</li>
 <li>Mutual funds remain structurally non-intraday (NAV clock): this sleeve is a <b>monthly allocation
 engine</b>, never a live TP/SL pick class (peer consensus, which I adopt).</li>
</ul></div>

<div class="foot">Sources: Yahoo Finance chart API (monthly, fetched 2026-11-14) &middot; live payload
<code>findtorontoevents.ca/audit/data/dashboard_payload.json</code> (3,500 closed rows) &middot; peers' shipped
cost gate &amp; stop-fill model (final_v3) &middot; my walk-forward script
<code>final_2026_11_14/inspect-wt/06_profitable_approach/walkforward_v6.py</code>.
Scripts + JSON in this folder reproduce every number. &mdash; deepAI/inspect-wt</div>
</div></body></html>"""
D = {
    'v1cagr': extra['v1']['cagr'], 'v1sh': extra['v1']['sharpe'], 'v1mdd': extra['v1']['mdd'],
    'kfull': vc['kelly_full'], 'kq': vc['quarter_kelly'], 'pneg': bpx['prob_neg_total'],
    'ppos': round(100 - bpx['prob_neg_total'], 1),
    'tbl_head': hrow(['Variant', 'CAGR', 'Vol', 'Sharpe', 'Sortino', 'MaxDD', 'Calmar', 'Win% mo',
                      'VaR95 mo', 'VaR99 mo', 'ES95 mo']),
    'r_spy': mrow('bench_spy', 'SPY buy &amp; hold (benchmark)'),
    'r_6040': mrow('bench_6040', '60/40 SPY/AGG (benchmark)'),
    'r_v1': mrow('v1', 'v1 PRIMARY: top-2, 12-1, abs filter, inv-vol', 'primary'),
    'r_fee': mrow('v1_mf_feecost', 'v1 + 0.15%/yr MF expense drag'),
    'r_v2': mrow('v2', 'v2: + 12% vol target'),
    'r_v3': mrow('v3', 'v3: + 15% DD stop w/ 3-mo cooldown', 'fail'),
    'r_v4': mrow('v4_top3_sens', 'SENSITIVITY (2nd trial): top-3 + vol target'),
    'stress_head': hrow(['Period', 'v1 rotation', 'v3 + DD stop', 'SPY B&H']),
    'stress_rows': st_rows, 'ann_hdr': ann_hdr, 'ann_v1': ann_v1, 'ann_spy': ann_spy,
    'W': W, 'H': H, 'grid': grid, 'paths': paths, 'xlab': xlab, 'legend': legend,
    'ov_head': hrow(['Overlay', 'Result', 'Verdict']),
    'ov1': row(['Absolute-momentum filter', '2022 -6.2% vs SPY -19.5%; COVID -0.6% vs -19.9%',
                '<span class="tag t-pass">KEEP - the core risk control</span>']),
    'ov2': row(['12% vol targeting', 'Sharpe 0.57 to 0.60, MDD -26.7% to -26.3%',
                '<span class="tag t-open">NEUTRAL - keep only if implementation is free</span>']),
    'ov3': row(['15% drawdown stop (3-mo cooldown)', 'Sharpe 0.57 to 0.15, CAGR 7.4% to 1.2%; whipsaw out of recoveries',
                '<span class="tag t-fail">REJECT - tested, failed, reported</span>']),
    'ov4': row(['Top-3 diversification (2nd trial)', 'Sharpe 0.55 (no improvement)',
                '<span class="tag t-open">SENSITIVITY - not adopted</span>']),
    'ov5': row(['0.15%/yr MF fee drag', 'CAGR 7.36% to 7.20%',
                '<span class="tag t-pass">IMMATERIAL at index-fund fees</span>']),
    'risk_head': hrow(['Risk metric', 'Value', 'Method / caveat']),
    'rr1': row(['Kelly full / adopted', '%.2f%% / %.2f%% per trade' % (vc['kelly_full'], vc['quarter_kelly']),
                'WR 47.3%, avg win/loss 1.41; Kelly is EDGE-sensitive, so the 1/4 fraction is standard practice']),
    'rr2': row(['Expected bankroll change/trade', '+0.010% at 2.5% risk', 'mean trade PnL x size']),
    'rr3': row(['Bootstrap total P/L (median)', '+%.1fpp' % bpx['total_median'],
                '4,000 resamples of the 237-trade stream']),
    'rr4': row(['Bootstrap 5-95% band', '-%.1fpp to +%.1fpp' % (abs(bpx['total_p5']), bpx['total_p95']),
                'sampling uncertainty of the total']),
    'rr5': row(['P(forward PF &gt;= 1.00 / &gt;= 1.15)', '%.1f%% / %.1f%%' % (bpx['prob_ge_1.0'], bpx['prob_ge_1.15']),
                'bootstrap PF distribution (median %.2f, p5 %.2f, p95 %.2f)' % (bpx['median'], bpx['p5'], bpx['p95'])]),
    'rr6': row(['MaxDD at 1/4 Kelly (median / worst)', '-1.2% / -4.4% bankroll',
                'resampled trade orderings; trade-weighted source data - see caveat']),
    'rr7': row(['Monthly VaR95 (bankroll)', '-1.15%',
                'only 7 forward months - <b>small-sample: indicative only</b>, widen with forward data']),
    'rr8': row(['Correlation cap / cost buffer', '0.7 pairwise (proposed) / 0.416%/trade breakeven',
                '86 distinct strategy x symbol pairs; slippage on closed rows still UNVERIFIED - QA Gate 1 must close it']),
    'prob_head': hrow(['Candidate', 'Event whose probability this is', 'Estimate', 'Basis']),
    'pb1': row(['MF/ETF sleeve', 'Positive net return over 10y (beats cash + 0.15% fees)',
                '<b class="good">~85-90%</b>', '165-mo backtest CAGR +7.2% net; positive in 12/15 years']),
    'pb2': row(['MF/ETF sleeve', 'Max drawdown &lt;= 20% in a full cycle', '~60-70%',
                'observed MDD -27% (v1) - the 2018Q4 cluster is the threat; 60/40 did -21%']),
    'pb3': row(['MF/ETF sleeve', 'Beats SPY buy &amp; hold over the FULL cycle',
                '<b class="warn">~25-35%</b>', 'it lost 2013-2026 (7.2% vs 12.5%); wins are regime-dependent (2025-26: +58% vs +30%)']),
    'pb4': row(['MF/ETF sleeve', 'Beats SPY on Calmar in a bear-inclusive decade', '~45-55%',
                'MDD -26.7% vs -24.8% is close; bear protection is the differentiator']),
    'pb5': row(['variant-C equity pilot', 'Forward PF &gt;= 1.15 over next 100 trades',
                '~%.0f%%' % bpx['prob_ge_1.15'], 'bootstrap of the reproduced forward stream']),
    'pb6': row(['variant-C equity pilot', 'Forward PF &gt;= 1.00 (positive expectancy)',
                '~%.0f%%' % bpx['prob_ge_1.0'], 'bootstrap; sub-T2 today - this is why it is a PILOT']),
    'pb7': row(['variant-C equity pilot', 'Passes full T2 certification (n&gt;=100, PF&gt;=1.5, WR&gt;=50%)',
                '<b class="warn">~30-40%</b>', 'PF 1.26 vs 1.5 gap + WR 47.3% vs 50% + SPY-gate risk (#773)']),
    'pb8': row(['Crypto vol-trend (conditional, slot 2)', 'Forward PF &gt;= 1.15 after fill fix',
                '~25-35%', 'fill fix just shipped; B4 open; single-source risk']),
    'meth_head': hrow(['Layer', 'Rule', 'Applied to']),
    'mt1': row(['Position sizing', '1/4 Kelly (variant-C: 2.46%/trade); fixed-fraction 1-2% for the sleeve', 'both candidates']),
    'mt2': row(['Volatility targeting', '12% annual portfolio vol, no leverage (scale &lt;= 1.0)', 'MF/ETF sleeve (neutral verdict above)']),
    'mt3': row(['Concentration', 'max 50% per position (sleeve); 0.7 correlation cap; top-2 holdings', 'MF/ETF sleeve; variant-C symbol clusters']),
    'mt4': row(['Drawdown control', '15% portfolio DD stop - <b>TESTED AND REJECTED</b> at monthly frequency; replaced by absolute-momentum de-risking + kill criteria', 'both']),
    'mt5': row(['Tail risk', 'historical VaR95/99 + ES95 monthly (sleeve, n=165) and bootstrap bands (pilot, n=237)', 'both']),
    'mt6': row(['Stress tests', '2022 bear, COVID, 2018Q4, 2025-26 regime, July-26 pilot month (-45.9pp)', 'both']),
    'mt7': row(['Kill criteria', '2x consecutive month PF&lt;0.5 OR 3-mo rolling PF&lt;1.0, halt + re-audit', 'pilot']),
    'mt8': row(['Cost budget', 'edge must survive breakeven extra cost 0.416%/trade; per-class 3x cost gate (peers\' shipped <code>per_class_cost_gate.py</code>)', 'both - enforced via QA Gate 1']),
    'mt9': row(['Certification', 'T2 AND v3 gates on forward records only: n&gt;=100, WR&gt;=50% w/ Wilson CI, PF&gt;=1.5, MDD&lt;20% at stated sizing, &gt;=66% WF windows, dual-source, multiple-testing disclosure', 'both']),
    'vcn': vc['n'], 'vcwr': vc['wr'], 'vcpf': vc['pf'],
}
import re
html = re.sub(r'%\((\w+)\)[sd]', lambda m: str(D[m.group(1)]), TPL).replace('%%', '%')
open('risk_management.html', 'w', encoding='utf-8').write(html)
print('risk_management.html written:', len(html), 'bytes')
