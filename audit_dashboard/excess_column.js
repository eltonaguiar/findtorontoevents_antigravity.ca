// ============================================================
// EXCESS COLUMN — per-pick performance vs the class benchmark
// Loaded by index.html & template.html via <script src="excess_column.js">
//
// WHY THIS IS A SEPARATE FILE: the audit workflow regenerates index.html from
// template.html on every run, so logic added to the generated page is lost.
// This file is not touched by the generator.
//
// METHOD — mirrors tools/pick_excess.py exactly:
//   bench return = last close on/before the entry day  ->  last close on/before the exit day
//   excess       = pick pnl% - bench return%            (percentage points)
//   benchmark    = EQUITY/ETF -> SPY, CRYPTO -> BTC-USD
//
// A SUB-DAY WINDOW IS NOT SCORED HERE. When entry and exit fall on the same
// trading day there is no daily benchmark window. The dashboard ships no
// intraday series, so the cell renders "—" with the reason rather than a
// fabricated 0. tools/pick_excess.py scores those from 60-minute bars; the
// dashboard intentionally does not, to keep the sidecar ~25KB instead of ~500KB.
// ============================================================
(function (global) {
  'use strict';

  var DEFAULT_BENCH = { EQUITY: 'SPY', ETF: 'SPY', CRYPTO: 'BTC-USD' };
  var SIDECAR = 'data/benchmark_prices.json';
  var state = {
    series: null, benchmarks: DEFAULT_BENCH, loaded: false, error: '', generated: null
  };

  function parseTs(s) {
    if (!s) return null;
    var d = new Date(String(s).trim().replace(' ', 'T'));
    return isNaN(d.getTime()) ? null : d;
  }

  function dayKey(d) {
    // UTC day, matching the Python tool, which normalises timestamps to UTC.
    var y = d.getUTCFullYear(), m = d.getUTCMonth() + 1, day = d.getUTCDate();
    return y + '-' + (m < 10 ? '0' + m : m) + '-' + (day < 10 ? '0' + day : day);
  }

  function closeOnOrBefore(sym, day) {
    var s = state.series && state.series[sym];
    if (!s || !s.dates || !s.dates.length) return null;
    var lo = 0, hi = s.dates.length - 1, best = -1;
    while (lo <= hi) {
      var mid = (lo + hi) >> 1;
      if (s.dates[mid] <= day) { best = mid; lo = mid + 1; } else { hi = mid - 1; }
    }
    if (best < 0) return null;
    return { day: s.dates[best], close: s.closes[best] };
  }

  /**
   * @param {Object} p     a pick from D.picks.recent_closed
   * @param {number} [pickPct] the PnL% already displayed for this row (getPnl(p))
   * @returns {{ok:boolean, reason?:string, sym?:string, excess_pp?:number, ...}}
   */
  function compute(p, pickPct) {
    if (!p || typeof p !== 'object') return { ok: false, reason: 'no pick' };
    if (!state.loaded) return { ok: false, reason: 'benchmark series not loaded' };

    var cls = String(p.asset_class || '').toUpperCase();
    var sym = state.benchmarks[cls];
    if (!sym) return { ok: false, reason: 'no benchmark for class ' + (cls || '?') };

    var t0 = parseTs(p.timestamp || p.entry_time);
    var t1 = parseTs(p.closed_at || p.resolved_at);
    if (!t0 || !t1) return { ok: false, reason: 'missing entry/exit timestamp', sym: sym };

    var pct = (typeof pickPct === 'number' && isFinite(pickPct)) ? pickPct : parseFloat(p.pnl_pct);
    if (!isFinite(pct)) return { ok: false, reason: 'no pick PnL', sym: sym };

    var a = closeOnOrBefore(sym, dayKey(t0));
    var b = closeOnOrBefore(sym, dayKey(t1));
    if (!a || !b) return { ok: false, reason: 'no ' + sym + ' bar in range', sym: sym };

    if (a.day >= b.day) {
      return {
        ok: false, sym: sym, entry_day: a.day, exit_day: b.day,
        reason: 'sub-day window (entry and exit on the same trading day)'
      };
    }

    var benchPct = (b.close / a.close - 1) * 100;
    return {
      ok: true, sym: sym, pick_pct: pct, bench_pct: benchPct,
      excess_pp: pct - benchPct, entry_day: a.day, exit_day: b.day,
      bench_entry_close: a.close, bench_exit_close: b.close
    };
  }

  function fmt(x) { return (x >= 0 ? '+' : '') + x.toFixed(2); }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function cellHtml(p, pickPct) {
    var r = compute(p, pickPct);
    if (!r.ok) {
      var tip = 'Excess vs benchmark not available: ' + r.reason +
                (r.sym ? '\nBenchmark: ' + r.sym : '') +
                '\nNot scored rather than shown as 0 — a zero would be a fabricated number.';
      return '<td class="r" style="color:var(--text-dim);cursor:help" title="' + esc(tip) + '">&mdash;</td>';
    }
    var color = r.excess_pp > 0 ? '#22c55e' : r.excess_pp < 0 ? '#ef4444' : 'var(--text-dim)';
    var tip = 'Excess vs ' + r.sym + ': pick ' + fmt(r.pick_pct) + '% minus benchmark ' +
              fmt(r.bench_pct) + '% = ' + fmt(r.excess_pp) + 'pp' +
              '\nWindow: ' + r.entry_day + ' -> ' + r.exit_day +
              '\nPositive = the pick beat simply holding ' + r.sym + ' over the same window.' +
              '\nBenchmark closes: ' + r.bench_entry_close + ' -> ' + r.bench_exit_close;
    return '<td class="r" style="font-weight:700;color:' + color + ';cursor:help" title="' + esc(tip) + '">' +
           fmt(r.excess_pp) + 'pp</td>';
  }

  function sortVal(p) {
    var r = compute(p);
    return r.ok ? r.excess_pp : -1e9;
  }

  function _setSeries(payload) {
    if (!payload || !payload.series) return false;
    state.series = payload.series;
    if (payload.benchmarks) state.benchmarks = payload.benchmarks;
    state.generated = payload.generated_utc || null;
    state.loaded = true;
    state.error = '';
    return true;
  }

  function load(cb) {
    if (typeof fetch !== 'function') { state.error = 'fetch unavailable'; return; }
    fetch(SIDECAR + '?t=' + Date.now(), { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (j) { if (_setSeries(j) && typeof cb === 'function') cb(); })
      .catch(function (e) { state.error = String((e && e.message) || e); });
  }

  global.PickExcess = {
    load: load, compute: compute, cellHtml: cellHtml, sortVal: sortVal,
    state: state, _setSeries: _setSeries, BENCHMARKS: DEFAULT_BENCH, SIDECAR: SIDECAR
  };

  if (typeof window !== 'undefined' && typeof document !== 'undefined') {
    // The drill-down modal opens on click, well after this resolves. Until it
    // does, rows render "—" rather than blocking the table.
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () { load(); });
    } else {
      load();
    }
  }
})(typeof window !== 'undefined' ? window : globalThis);
