// ============================================================
// FORWARD CLOCK PANEL — how close each pre-registered strategy is to a verdict
// Loaded by index.html & template.html via <script src="forward_clock.js">
//
// WHY THIS IS A SEPARATE FILE: the audit workflow regenerates index.html from
// template.html on every run, so anything added to the generated page is lost.
//
// WHAT IT IS NOT: this panel declares nothing. It reads data/forward_clock.json,
// which tools/build_forward_clock.py produces by calling the SAME decide() and
// interim_verdict() the CLI uses. A panel with its own verdict logic would drift
// from `forward_tracker.py status`, and the dashboard is what people look at.
//
// A 0% BAR IS NOT A BAD SCORE. It means no pick has closed since registration —
// the pre-registration guard excludes everything older. The panel says that in
// words rather than drawing an empty bar and letting the reader assume failure.
// ============================================================
(function (global) {
  'use strict';

  var SRC = 'data/forward_clock.json';
  var HOST_ID = 'forward-clock-body';

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function num(x, d) {
    return (x == null || !isFinite(x)) ? '—' : x.toFixed(d == null ? 2 : d);
  }

  function verdictColor(v) {
    if (v === 'PROMOTE') return '#22c55e';
    if (v === 'KILL' || v === 'BROKEN') return '#ef4444';
    if (v === 'HOLD-LONGER') return '#eab308';
    return '#94a3b8';
  }

  function bar(r) {
    if (!r.target_windows) return '<span style="color:#64748b">no fixed sample registered</span>';
    var pct = r.pct_of_target == null ? 0 : Math.max(0, Math.min(100, r.pct_of_target));
    var tip = r.windows + ' of ' + r.target_windows + ' independent windows';
    return '<div title="' + esc(tip) + '" style="background:#1e293b;border-radius:4px;height:9px;width:110px;display:inline-block;vertical-align:middle">' +
           '<div style="background:#38bdf8;height:9px;border-radius:4px;width:' + pct + '%"></div></div>' +
           ' <span style="font-variant-numeric:tabular-nums">' + r.windows + '/' + r.target_windows +
           ' (' + num(pct, 1) + '%)</span>';
  }

  function interimCell(r) {
    if (!r.has_measurement_design) {
      return '<td style="color:#64748b" title="This strategy uses the PF/calendar rules only; no window-based sequential test was pre-registered.">—</td>';
    }
    if (r.next_look == null && r.look == null) {
      return '<td style="color:#64748b">looks complete</td>';
    }
    var nxt = (r.next_look == null) ? 'final look reached' : ('next: n=' + r.next_look);
    var z = (r.z == null) ? '—' : (r.z === 'Infinity' ? '∞' : num(r.z));
    var tip = 'Endpoint: ' + (r.endpoint || '?') +
              '\nObserved z vs the boundary at the last scheduled look: ' + (r.boundary == null ? '—' : num(r.boundary)) +
              '\nBoundaries: ' + ((r.all_boundaries || []).map(function (x) { return num(x); }).join(' / ') || '—') +
              '\nThe boundary tightens as windows accumulate; an early PROMOTE therefore needs a much larger z.';
    return '<td style="cursor:help" title="' + esc(tip) + '">' + esc(nxt) +
           '<br><span style="color:#64748b;font-size:11px">z ' + esc(z) + ' vs bar ' +
           (r.boundary == null ? '—' : num(r.boundary)) + '</span></td>';
  }

  function priorCell(r) {
    if (r.prior_excess_pp == null) return '<td style="color:#64748b">—</td>';
    return '<td style="cursor:help" title="' + esc(r.prior_status || 'in-sample prior') + '">' +
           '<span style="color:#eab308">' + (r.prior_excess_pp >= 0 ? '+' : '') + num(r.prior_excess_pp) + 'pp</span>' +
           '<br><span style="color:#64748b;font-size:11px">in-sample prior</span></td>';
  }

  function render(data) {
    var rows = data.strategies || [];
    var started = rows.filter(function (r) { return r.started; })
                      .map(function (r) { return r.started; }).sort()[0] || '—';
    var head = '<div style="margin-bottom:8px">' +
      '<strong style="color:#e2e8f0">Forward-test clock</strong> ' +
      '<span style="color:#64748b;font-size:12px">— pre-registered rules, measured progress. ' +
      'Started ' + esc(started) + ' · ' + data.ledger_rows + ' closed trade(s) admitted · ' +
      'costs ' + (data.cost_model && data.cost_model.fee_bps_per_side != null ? data.cost_model.fee_bps_per_side + ' bps/side' : 'not set') +
      '</span></div>';

    if (!rows.length) {
      return head + '<div style="color:#64748b">No strategies registered.</div>';
    }

    var html = head;
    if (!data.ledger_rows) {
      html += '<div style="margin:8px 0;padding:8px 10px;border-left:3px solid #38bdf8;background:#0b1220;color:#cbd5e1;font-size:12px">' +
        'Nothing has been admitted yet. That is the pre-registration guard working, not a failure: ' +
        'picks that closed before a strategy was registered are excluded by construction, because ' +
        'scoring them would turn the forward test back into the retrospective read it exists to escape.' +
        '</div>';
    }

    html += '<table style="width:100%;border-collapse:collapse;font-size:12px">' +
      '<tr style="color:#94a3b8;text-align:left">' +
      '<th style="padding:4px 6px">Strategy</th><th>Class</th><th>Clock</th>' +
      '<th>Windows → sample</th><th>Next look</th><th>Prior (in-sample)</th>' +
      '<th>Verdict</th><th>Note</th></tr>';

    rows.forEach(function (r) {
      html += '<tr style="border-top:1px solid #1e293b">' +
        '<td style="padding:4px 6px;color:#e2e8f0;font-weight:600">' + esc(r.strategy) + '</td>' +
        '<td>' + esc(r.class || '—') + '</td>' +
        '<td style="color:#94a3b8">' + (r.days_elapsed == null ? '—' : r.days_elapsed + 'd') +
          (r.mean_hold_days ? '<br><span style="font-size:11px;color:#64748b">hold ' + num(r.mean_hold_days, 0) + 'd</span>' : '') + '</td>' +
        '<td>' + bar(r) + '</td>' +
        interimCell(r) +
        priorCell(r) +
        '<td style="color:' + verdictColor(r.verdict) + ';font-weight:700">' + esc(r.verdict) + '</td>' +
        '<td style="color:#64748b">' + esc(r.note || '') + '</td>' +
        '</tr>';
    });
    html += '</table>';
    html += '<div style="margin-top:8px;color:#64748b;font-size:11px">' + esc(data.note || '') +
            ' Generated ' + esc(data.generated_utc || '?') + '.</div>';
    return html;
  }

  function mount() {
    var host = global.document && global.document.getElementById(HOST_ID);
    if (!host) return;
    if (typeof fetch !== 'function') { host.textContent = 'Fetch unavailable.'; return; }
    fetch(SRC + '?t=' + Date.now(), { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (j) { host.innerHTML = render(j); })
      .catch(function (e) {
        host.innerHTML = '<span style="color:#ef4444">Forward clock unavailable: ' + esc(e.message) +
          '. Not shown rather than shown empty — an empty clock would read as "0 progress".</span>';
      });
  }

  global.ForwardClock = { mount: mount, render: render, SRC: SRC };

  if (typeof global.document !== 'undefined') {
    if (global.document.readyState === 'loading') {
      global.document.addEventListener('DOMContentLoaded', mount);
    } else {
      mount();
    }
  }
})(typeof window !== 'undefined' ? window : globalThis);
