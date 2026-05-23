from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "updates" / "index.html"
t = p.read_text(encoding="utf-8")
marker = '  <div class="container" id="updatesContainer">\n'
needle = "2026-04-07-audit-score-improvement-review.html"
if needle in t:
    print("already present")
    raise SystemExit(0)
idx = t.find(marker)
if idx == -1:
    raise SystemExit("marker missing")
inner = '''    <!-- Update: April 7, 2026 - Audit score improvement plan review -->
    <div class="update-entry" style="--dot-color: #38bdf8;" data-tags="audit,scoring,hedge-fund,asset-class,crypto,forex,equity" data-category="trading" data-types="improvement,milestone">
      <div class="update-date">Apr 7, 2026 &mdash; <strong style="color:#38bdf8;">Audit /audit score plan</strong> review + Redis bus feedback</div>
      <div class="update-badges">
        <span class="badge badge-fix" style="background:#450a0a;border-color:#ef4444;color:#fecaca;">NOT FINANCIAL ADVICE</span>
        <span class="badge badge-improvement">Cross-asset</span>
        <span class="badge badge-milestone">Fleet: audit_picks_score_improvement_review</span>
      </div>
      <p style="color:#e0e0e0;font-size:0.92em;line-height:1.65">Cursor plan for <strong>audit picks edge analysis</strong> (snapshot <code>dashboard_data.json</code>, active-book analyzer, merged report) is <strong>endorsed</strong>. Full feedback: asymmetric quality by asset class &mdash; crypto <code>smart_score</code> carries IC, <code>elite</code> flat; equity scores rank but the traded pool bleeds; forex weak headline discrimination. Hedge-fund consistency needs <strong>truth-layer P0s</strong> plus <strong>gates/allowlists</strong>, not only reweighting.</p>
      <p style="color:#94a3b8;font-size:0.88em;margin-top:10px"><a href="/updates/2026-04-07-audit-score-improvement-review.html" style="color:#38bdf8">Read summary</a> &middot; <a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/docs/AUDIT_SCORE_IMPROVEMENT_PLAN_REVIEW_2026-04-07.md" target="_blank" rel="noopener" style="color:#38bdf8">Full review (GitHub)</a> &middot; Redis topic <code>audit_picks_score_improvement_review</code></p>
    </div>

'''
t2 = t[: idx + len(marker)] + inner + t[idx + len(marker) :]
tmp = p.with_suffix(".html.fixtmp")
tmp.write_text(t2, encoding="utf-8")
tmp.replace(p)
print("inserted")
