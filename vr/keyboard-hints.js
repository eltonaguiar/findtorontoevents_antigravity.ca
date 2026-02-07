/**
 * VR Zone — Keyboard Hints Overlay (QW-009)
 *
 * Shared module providing a consistent keyboard shortcut overlay across all VR zones.
 * Each zone registers its shortcuts; pressing ? or F1 toggles the help panel.
 *
 * Usage from any zone:
 *   VRKeyboardHints.register([
 *     { key: 'R', desc: 'Refresh data' },
 *     { key: 'ArrowKeys', desc: 'Paginate' },
 *   ]);
 */
(function () {
  'use strict';

  var COMMON_SHORTCUTS = [
    { key: 'WASD',    desc: 'Move around' },
    { key: 'Mouse',   desc: 'Look around' },
    { key: 'M / Tab', desc: 'Toggle menu' },
    { key: 'Esc',     desc: 'Close overlay' },
    { key: 'H',       desc: 'Back to Hub' },
    { key: '?',       desc: 'Show this help' }
  ];

  var zoneShortcuts = [];
  var panelVisible = false;
  var panelEl = null;
  var hintBarEl = null;

  function createHintBar() {
    if (document.getElementById('vr-hint-bar')) return;
    hintBarEl = document.createElement('div');
    hintBarEl.id = 'vr-hint-bar';
    hintBarEl.setAttribute('role', 'status');
    hintBarEl.setAttribute('aria-label', 'Keyboard shortcuts hint');

    var style = document.createElement('style');
    style.textContent =
      '#vr-hint-bar{position:fixed;bottom:0;left:0;right:0;z-index:9998;' +
      'background:linear-gradient(to top,rgba(0,0,0,0.7),transparent);' +
      'padding:8px 16px 10px;text-align:center;pointer-events:none;' +
      'font-family:Inter,system-ui,sans-serif;font-size:12px;color:#64748b;' +
      'transition:opacity 0.3s;opacity:0.8}' +
      '#vr-hint-bar .hint-key{background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);' +
      'padding:1px 6px;border-radius:4px;font-family:monospace;color:#94a3b8;margin:0 2px;font-size:11px}' +
      '#vr-hint-bar .hint-sep{margin:0 8px;color:#334155}' +
      '#vr-kb-overlay{position:fixed;inset:0;z-index:10002;background:rgba(8,10,20,0.92);' +
      'display:none;align-items:center;justify-content:center;padding:2rem;' +
      'font-family:Inter,system-ui,sans-serif}' +
      '#vr-kb-overlay.open{display:flex}' +
      '#vr-kb-card{max-width:680px;width:min(92vw,680px);background:rgba(10,18,32,0.97);' +
      'border:1px solid rgba(0,212,255,0.3);border-radius:18px;padding:24px;' +
      'box-shadow:0 20px 60px rgba(0,0,0,0.5);animation:kbFadeIn .25s ease}' +
      '@keyframes kbFadeIn{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:none}}' +
      '#vr-kb-card h2{margin:0 0 16px;font-size:1.6rem;color:#7dd3fc}' +
      '.kb-columns{display:grid;grid-template-columns:1fr 1fr;gap:20px}' +
      '.kb-section h3{margin:0 0 8px;font-size:0.85rem;text-transform:uppercase;' +
      'letter-spacing:1px;color:#475569}' +
      '.kb-row{display:flex;align-items:center;gap:8px;padding:4px 0;color:#cbd5e1;font-size:13px}' +
      '.kb-key{background:rgba(15,23,42,0.8);border:1px solid rgba(148,163,184,0.4);' +
      'border-radius:6px;padding:2px 8px;font-family:monospace;color:#e2e8f0;font-size:12px;' +
      'min-width:36px;text-align:center}' +
      '.kb-close{position:absolute;top:16px;right:20px;background:none;border:none;' +
      'color:#64748b;font-size:22px;cursor:pointer;padding:4px 8px}' +
      '.kb-close:hover{color:#ef4444}' +
      '@media(max-width:600px){.kb-columns{grid-template-columns:1fr}}';
    document.head.appendChild(style);
    document.body.appendChild(hintBarEl);
    updateHintBar();
  }

  function updateHintBar() {
    if (!hintBarEl) return;
    var items = zoneShortcuts.slice(0, 4);
    var html = items.map(function (s) {
      return '<span class="hint-key">' + s.key + '</span> ' + s.desc;
    }).join('<span class="hint-sep">|</span>');
    if (html) html += '<span class="hint-sep">|</span>';
    html += '<span class="hint-key">?</span> All shortcuts';
    hintBarEl.innerHTML = html;
  }

  function createOverlay() {
    if (document.getElementById('vr-kb-overlay')) return;
    panelEl = document.createElement('div');
    panelEl.id = 'vr-kb-overlay';
    panelEl.setAttribute('role', 'dialog');
    panelEl.setAttribute('aria-label', 'Keyboard shortcuts');
    document.body.appendChild(panelEl);
    rebuildOverlay();
  }

  function rebuildOverlay() {
    if (!panelEl) return;
    var zoneRows = zoneShortcuts.map(function (s) {
      return '<div class="kb-row"><span class="kb-key">' + s.key + '</span>' + s.desc + '</div>';
    }).join('');
    var commonRows = COMMON_SHORTCUTS.map(function (s) {
      return '<div class="kb-row"><span class="kb-key">' + s.key + '</span>' + s.desc + '</div>';
    }).join('');
    panelEl.innerHTML =
      '<div id="vr-kb-card" style="position:relative">' +
        '<button class="kb-close" onclick="VRKeyboardHints.hide()" aria-label="Close">&times;</button>' +
        '<h2>Keyboard Shortcuts</h2>' +
        '<div class="kb-columns">' +
          '<div class="kb-section"><h3>This Zone</h3>' + (zoneRows || '<div class="kb-row" style="color:#475569">No zone shortcuts</div>') + '</div>' +
          '<div class="kb-section"><h3>Global</h3>' + commonRows + '</div>' +
        '</div>' +
      '</div>';
  }

  function toggle() { panelVisible = !panelVisible; if (panelEl) panelEl.classList.toggle('open', panelVisible); }
  function show() { panelVisible = true; if (panelEl) panelEl.classList.add('open'); }
  function hide() { panelVisible = false; if (panelEl) panelEl.classList.remove('open'); }

  function isInputFocused() {
    var tag = (document.activeElement || {}).tagName;
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === '?' || (e.key === '/' && !e.ctrlKey && !e.metaKey && !isInputFocused())) {
      e.preventDefault();
      toggle();
      return;
    }
    if (e.key === 'F1') { e.preventDefault(); toggle(); return; }
    if (e.key === 'Escape' && panelVisible) { hide(); return; }
    if ((e.key === 'h' || e.key === 'H') && !isInputFocused() && !e.ctrlKey && !e.metaKey) {
      var menu = document.getElementById('vr-nav-menu-2d');
      if (menu && menu.classList.contains('active')) return;
      if (panelVisible) return;
      var path = window.location.pathname;
      if (path === '/vr/' || path === '/vr/index.html') return;
      window.location.href = '/vr/';
    }
  });

  window.VRKeyboardHints = {
    register: function (shortcuts) {
      zoneShortcuts = shortcuts || [];
      updateHintBar();
      rebuildOverlay();
    },
    show: show,
    hide: hide,
    toggle: toggle
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { createHintBar(); createOverlay(); });
  } else {
    createHintBar();
    createOverlay();
  }
})();
