/**
 * Loads audit_dashboard/data/audit_surface_truth.json and renders money-ready bridge panel.
 * Used on /audit/, ai-tournament, ai_leaderboard (Goal #1 trust hierarchy).
 */
(function () {
  const MOUNT_ID = 'audit-surface-truth-mount';

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function tier2Badge(pass) {
    return pass
      ? '<span style="color:#22c55e;font-weight:700">Tier-2 ✓</span>'
      : '<span style="color:#ef4444;font-weight:700">NOT money-ready</span>';
  }

  window.renderAuditSurfaceTruth = function (el, data) {
    if (!el || !data) return;
    const rows = (data.by_asset_class || [])
      .map(function (c) {
        return (
          '<tr><td>' +
          esc(c.asset_class) +
          '</td><td class="num">' +
          esc(c.n_resolved) +
          '</td><td class="num">' +
          esc(c.wr_pct) +
          '%</td><td class="num">' +
          esc(c.pf) +
          '</td><td>' +
          tier2Badge(c.tier2_pass) +
          '</td><td style="font-size:11px;color:#94a3b8">' +
          esc(c.bridge_action) +
          '</td></tr>'
        );
      })
      .join('');
    const t = data.tournament || {};
    const lb = data.ai_leaderboard || {};
    el.innerHTML =
      '<div style="padding:14px 16px;background:linear-gradient(135deg,rgba(239,68,68,0.12),rgba(15,23,42,0.9));border:2px solid rgba(239,68,68,0.45);border-radius:10px;margin:12px 0;font-size:12px;line-height:1.55">' +
      '<div style="font-weight:800;font-size:14px;color:#fecaca;margin-bottom:8px">🎯 Money-ready bridge — policy-clean truth (mutual-fund bar: n≥100, WR≥50%, PF≥1.5)</div>' +
      '<p style="color:#e2e8f0;margin:0 0 10px">' +
      esc(data.headline) +
      '</p>' +
      '<p style="color:#fca5a5;margin:0 0 10px"><strong>Tournament:</strong> ' +
      esc(t.banner || '') +
      ' <strong>Leaderboard:</strong> ' +
      esc(lb.banner || '') +
      '</p>' +
      '<table style="width:100%;border-collapse:collapse;font-size:11px;margin-top:8px">' +
      '<thead><tr style="color:#94a3b8"><th>Class</th><th class="num">n</th><th class="num">WR%</th><th class="num">PF</th><th>Status</th><th>Bridge</th></tr></thead><tbody>' +
      rows +
      '</tbody></table>' +
      '<p style="margin:10px 0 0;font-size:10px;color:#64748b">Source: <code>audit_surface_truth.json</code> · generated ' +
      esc((data.generated_at || '').slice(0, 19)) +
      'Z · Trust: ' +
      esc((data.trust_hierarchy || [])[0] || '') +
      '</p></div>';
  };

  window.loadAuditSurfaceTruth = function (mountId) {
    const el = document.getElementById(mountId || MOUNT_ID);
    if (!el) return;
    fetch('./data/audit_surface_truth.json?' + Date.now())
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        window.__AUDIT_SURFACE_TRUTH__ = d;
        window.renderAuditSurfaceTruth(el, d);
      })
      .catch(function () {
        el.innerHTML =
          '<div style="padding:10px;color:#fbbf24;font-size:12px">⚠ Could not load audit_surface_truth.json — run <code>python3 tools/build_audit_surface_truth.py</code> in CI.</div>';
      });
  };

  document.addEventListener('DOMContentLoaded', function () {
    if (document.getElementById(MOUNT_ID)) {
      window.loadAuditSurfaceTruth(MOUNT_ID);
    }
  });
})();