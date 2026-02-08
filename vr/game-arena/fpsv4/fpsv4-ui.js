/**
 * FPSV4 UI — HUD updates, menus, floating numbers, kill feed, minimap
 */
var FPSV4 = window.FPSV4 || {};

FPSV4.UI = (function () {
  'use strict';

  // Cached DOM elements
  var els = {};

  function cacheElements() {
    els.hudRound = document.getElementById('hud-round');
    els.hudPoints = document.getElementById('hud-points');
    els.hudKills = document.getElementById('hud-kills');
    els.hudHeadshots = document.getElementById('hud-headshots');
    els.hudHealth = document.getElementById('hud-health');
    els.healthBar = document.getElementById('health-bar');
    els.hudClip = document.getElementById('hud-clip');
    els.hudReserve = document.getElementById('hud-reserve');
    els.hudWepName = document.getElementById('hud-wep-name');
    els.hudWepType = document.getElementById('hud-wep-type');
    els.killFeed = document.getElementById('kill-feed');
    els.damageOverlay = document.getElementById('damage-overlay');
    els.lowHealthOverlay = document.getElementById('low-health-overlay');
    els.roundBanner = document.getElementById('round-banner');
    els.minimapCanvas = document.getElementById('minimap-canvas');
  }

  function init() {
    cacheElements();
    FPSV4.Engine.init();
    FPSV4.Weapons.init();
    FPSV4.Zombies.init();
    FPSV4.GameMode.init();

    console.log('[FPSV4 UI] Initialized');
  }

  // ─── HUD Update (called every frame) ───
  function update() {
    var gm = FPSV4.GameMode;
    var wep = FPSV4.Weapons;
    var player = FPSV4.Engine.getPlayer();

    // Round & Points
    if (els.hudRound) els.hudRound.textContent = gm.getRound();
    if (els.hudPoints) els.hudPoints.textContent = gm.getPoints();

    // Kills
    if (els.hudKills) els.hudKills.textContent = gm.getKills();
    if (els.hudHeadshots) els.hudHeadshots.textContent = gm.getHeadshots();

    // Health
    var hp = player.health;
    if (els.hudHealth) {
      els.hudHealth.textContent = Math.ceil(hp);
      els.hudHealth.style.color = hp > 60 ? '#22c55e' : hp > 30 ? '#f59e0b' : '#ef4444';
    }
    if (els.healthBar) {
      els.healthBar.style.width = hp + '%';
      els.healthBar.style.background = hp > 60 ? '#22c55e' : hp > 30 ? '#f59e0b' : '#ef4444';
    }

    // Low health overlay
    if (els.lowHealthOverlay) {
      if (hp <= 30 && hp > 0) {
        els.lowHealthOverlay.classList.add('active');
        els.lowHealthOverlay.style.opacity = '1';
      } else {
        els.lowHealthOverlay.classList.remove('active');
        els.lowHealthOverlay.style.opacity = '0';
      }
    }

    // Ammo
    if (els.hudClip) els.hudClip.textContent = wep.getClip();
    if (els.hudReserve) els.hudReserve.textContent = wep.getReserve();

    // Weapon info
    var currentWep = wep.getCurrentWeapon();
    if (els.hudWepName) els.hudWepName.textContent = currentWep.name;
    if (els.hudWepType) {
      var typeText = currentWep.type;
      if (wep.isReloading()) typeText = 'Reloading...';
      else if (wep.isADS()) typeText += ' [ADS]';
      els.hudWepType.textContent = typeText;
    }

    // Crosshair spread
    var spread = wep.getSpreadAccum();
    var crosshairLines = document.querySelectorAll('.ch-line');
    var spreadPx = 6 + spread * 300;
    for (var i = 0; i < crosshairLines.length; i++) {
      var line = crosshairLines[i];
      if (line.classList.contains('top')) line.style.top = (-spreadPx - 6) + 'px';
      else if (line.classList.contains('bottom')) line.style.bottom = (-spreadPx - 6) + 'px';
      else if (line.classList.contains('left')) line.style.left = (-spreadPx - 6) + 'px';
      else if (line.classList.contains('right')) line.style.right = (-spreadPx - 6) + 'px';
    }

    // Update minimap
    renderMinimap();
  }

  // ─── Minimap ───
  function renderMinimap() {
    if (!els.minimapCanvas) return;
    var ctx = els.minimapCanvas.getContext('2d');
    if (!ctx) return;

    var w = els.minimapCanvas.width;
    var h = els.minimapCanvas.height;
    var arenaSize = FPSV4.Engine.getArenaSize();
    var scale = w / arenaSize;

    ctx.clearRect(0, 0, w, h);

    // Background
    ctx.fillStyle = 'rgba(10,10,20,0.8)';
    ctx.beginPath();
    ctx.arc(w / 2, h / 2, w / 2, 0, Math.PI * 2);
    ctx.fill();

    // Arena border
    ctx.strokeStyle = 'rgba(255,255,255,0.1)';
    ctx.lineWidth = 1;
    ctx.strokeRect(2, 2, w - 4, h - 4);

    // Player dot
    var player = FPSV4.Engine.getPlayer();
    var px = (player.pos.x + arenaSize / 2) * scale;
    var pz = (player.pos.z + arenaSize / 2) * scale;
    ctx.fillStyle = '#22c55e';
    ctx.beginPath();
    ctx.arc(px, pz, 3, 0, Math.PI * 2);
    ctx.fill();

    // Player direction
    var dirX = Math.sin(player.yaw);
    var dirZ = Math.cos(player.yaw);
    ctx.strokeStyle = '#22c55e';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(px, pz);
    ctx.lineTo(px + dirX * 8, pz + dirZ * 8);
    ctx.stroke();

    // Zombie dots (red)
    ctx.fillStyle = '#ef4444';
    // Access zombie positions via the module (we need to get active zombies somehow)
    // For now, we'll iterate the pool checking active state
    var zombieCount = FPSV4.Zombies.getActiveCount();
    if (zombieCount > 0 && FPSV4.Zombies._getActiveList) {
      var zombies = FPSV4.Zombies._getActiveList();
      for (var i = 0; i < zombies.length; i++) {
        if (zombies[i].dying) continue;
        var zx = (zombies[i].pos.x + arenaSize / 2) * scale;
        var zz = (zombies[i].pos.z + arenaSize / 2) * scale;
        ctx.beginPath();
        ctx.arc(zx, zz, 2, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  // ─── Floating Damage Numbers ───
  function showDamageNumber(worldPos, damage, isHeadshot) {
    var camera = FPSV4.Engine.getCamera();

    // Project 3D to 2D
    var pos3 = worldPos.clone();
    pos3.y += 2.2;
    pos3.project(camera);

    if (pos3.z > 1) return; // Behind camera

    var x = (pos3.x * 0.5 + 0.5) * window.innerWidth;
    var y = (-pos3.y * 0.5 + 0.5) * window.innerHeight;

    var el = document.createElement('div');
    el.className = 'dmg-number ' + (isHeadshot ? 'headshot' : 'normal');
    el.textContent = Math.round(damage);
    el.style.left = x + 'px';
    el.style.top = y + 'px';
    document.body.appendChild(el);

    setTimeout(function () { el.remove(); }, 800);
  }

  // ─── Points Popup ───
  function showPointsPopup(pts, isHeadshot) {
    var el = document.createElement('div');
    el.className = 'pts-popup';
    el.textContent = '+' + pts + (isHeadshot ? ' HEADSHOT' : '');
    el.style.left = (window.innerWidth / 2 + 80) + 'px';
    el.style.top = (window.innerHeight / 2 - 30) + 'px';
    document.body.appendChild(el);

    setTimeout(function () { el.remove(); }, 1200);
  }

  // ─── Kill Feed ───
  function addKillFeed(isHeadshot) {
    if (!els.killFeed) return;

    var entry = document.createElement('div');
    entry.className = 'kill-entry';
    entry.innerHTML = '<span style="color:#22c55e">You</span> ' +
      (isHeadshot ? '<span style="color:#fbbf24">\u2620 headshot</span>' : 'killed') +
      ' <span style="color:#ef4444">Zombie</span>';

    els.killFeed.insertBefore(entry, els.killFeed.firstChild);

    // Limit feed size
    while (els.killFeed.children.length > 5) {
      els.killFeed.removeChild(els.killFeed.lastChild);
    }

    // Auto-remove after 4s
    setTimeout(function () {
      if (entry.parentNode) entry.remove();
    }, 4000);
  }

  // ─── Damage Overlay ───
  function showDamageOverlay() {
    if (!els.damageOverlay) return;
    els.damageOverlay.classList.add('hit');
    setTimeout(function () {
      els.damageOverlay.classList.remove('hit');
    }, 150);
  }

  // ─── Round Banner ───
  function showRoundBanner(round) {
    if (!els.roundBanner) return;
    var title = els.roundBanner.querySelector('.rb-title');
    var sub = els.roundBanner.querySelector('.rb-sub');
    if (title) title.textContent = 'ROUND ' + round;
    if (sub) sub.textContent = FPSV4.GameMode.getZombiesRemaining() + ' zombies incoming';

    els.roundBanner.classList.remove('active');
    void els.roundBanner.offsetWidth;
    els.roundBanner.classList.add('active');

    setTimeout(function () {
      els.roundBanner.classList.remove('active');
    }, 3000);
  }

  // ─── Game Over Screen ───
  function showGameOver(round, kills, headshots, points) {
    var goEl = document.getElementById('game-over');
    if (!goEl) return;

    document.getElementById('go-round').textContent = round;
    document.getElementById('go-kills').textContent = kills;
    document.getElementById('go-headshots').textContent = headshots;
    document.getElementById('go-points').textContent = points;
    document.getElementById('go-subtitle').textContent = 'Survived until Round ' + round;

    var bestEl = document.getElementById('go-best');
    var persistent = FPSV4.GameMode.getPersistent();
    if (round >= persistent.bestRound) {
      bestEl.textContent = 'NEW PERSONAL BEST!';
      bestEl.style.color = '#fbbf24';
    } else {
      bestEl.textContent = 'Best: Round ' + persistent.bestRound;
      bestEl.style.color = '#a855f7';
    }

    goEl.classList.add('active');
  }

  // ─── Menu Stats ───
  function updateMenuStats() {
    var persistent = FPSV4.GameMode.getPersistent();
    var bestRoundEl = document.getElementById('menu-best-round');
    var totalKillsEl = document.getElementById('menu-total-kills');
    var gamesEl = document.getElementById('menu-games');
    if (bestRoundEl) bestRoundEl.textContent = persistent.bestRound;
    if (totalKillsEl) totalKillsEl.textContent = persistent.totalKills;
    if (gamesEl) gamesEl.textContent = persistent.totalGames;
  }

  // ─── Settings ───
  function showSettings() {
    // For now, just toggle pause
    FPSV4.GameMode.togglePause();
  }

  // ─── Init on DOM ready ───
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    // Small delay to ensure all modules are loaded
    setTimeout(init, 50);
  }

  return {
    init: init,
    update: update,
    showDamageNumber: showDamageNumber,
    showPointsPopup: showPointsPopup,
    addKillFeed: addKillFeed,
    showDamageOverlay: showDamageOverlay,
    showRoundBanner: showRoundBanner,
    showGameOver: showGameOver,
    updateMenuStats: updateMenuStats,
    showSettings: showSettings
  };
})();
