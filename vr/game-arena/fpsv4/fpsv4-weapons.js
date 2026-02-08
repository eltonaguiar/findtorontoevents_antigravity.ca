/**
 * FPSV4 Weapons — Weapon definitions, firing, reload, ADS, FP rendering
 */
var FPSV4 = window.FPSV4 || {};

FPSV4.Weapons = (function () {
  'use strict';

  // ─── Weapon Definitions ───
  var WEAPONS = [
    { id: 'm1911',   name: 'M1911',          type: 'Pistol',          key: '1', damage: 30,  fireRate: 3.5, clipSize: 8,  reserve: 32,  range: 35,  accuracy: 82, recoil: 10, auto: false, spread: 0.02, headshotMult: 2.0, color: '#94a3b8' },
    { id: 'shotgun',  name: 'SPAS-12',       type: 'Shotgun',         key: '2', damage: 90,  fireRate: 1.1, clipSize: 8,  reserve: 32,  range: 12,  accuracy: 55, recoil: 40, auto: false, spread: 0.09, headshotMult: 1.5, color: '#f97316' },
    { id: 'smg',      name: 'MP5',           type: 'SMG',             key: '3', damage: 20,  fireRate: 11,  clipSize: 30, reserve: 150, range: 22,  accuracy: 68, recoil: 14, auto: true,  spread: 0.04, headshotMult: 1.8, color: '#3b82f6' },
    { id: 'assault',  name: 'M4 Carbine',    type: 'Assault Rifle',   key: '4', damage: 32,  fireRate: 8,   clipSize: 30, reserve: 150, range: 45,  accuracy: 76, recoil: 16, auto: true,  spread: 0.028, headshotMult: 2.0, color: '#22c55e' },
    { id: 'sniper',   name: 'AWP',           type: 'Sniper Rifle',    key: '5', damage: 120, fireRate: 0.7, clipSize: 5,  reserve: 25,  range: 90,  accuracy: 95, recoil: 50, auto: false, spread: 0.006, headshotMult: 3.0, color: '#a855f7' },
    { id: 'rocket',   name: 'RPG-7',         type: 'Rocket Launcher', key: '6', damage: 160, fireRate: 0.5, clipSize: 1,  reserve: 8,   range: 50,  accuracy: 50, recoil: 55, auto: false, spread: 0.04, headshotMult: 1.0, color: '#ef4444' }
  ];

  var KNIFE = { id: 'knife', name: 'Combat Knife', damage: 130, range: 2.0, cooldown: 0.6 };

  // ─── State ───
  var currentWeapon = 0; // index into WEAPONS
  var ammoClip = [];
  var ammoReserve = [];
  var reloading = false;
  var reloadTimer = 0;
  var fireTimer = 0;
  var knifeCooldown = 0;
  var ads = false;
  var adsLerp = 0;
  var spreadAccum = 0;
  var footstepTimer = 0;

  // FP Weapon renderer
  var fpCtx = null;
  var fpCanvas = null;

  // ─── Init ───
  function init() {
    fpCanvas = document.getElementById('fp-weapon-canvas');
    if (fpCanvas) fpCtx = fpCanvas.getContext('2d');

    // Initialize ammo for starting weapon (M1911)
    resetWeapons();
  }

  function resetWeapons() {
    ammoClip = [];
    ammoReserve = [];
    for (var i = 0; i < WEAPONS.length; i++) {
      ammoClip[i] = 0;
      ammoReserve[i] = 0;
    }
    // Starting weapon: M1911
    currentWeapon = 0;
    ammoClip[0] = WEAPONS[0].clipSize;
    ammoReserve[0] = WEAPONS[0].reserve;
    reloading = false;
    reloadTimer = 0;
    fireTimer = 0;
    ads = false;
    adsLerp = 0;
    spreadAccum = 0;
  }

  function giveWeapon(index) {
    if (index < 0 || index >= WEAPONS.length) return;
    ammoClip[index] = WEAPONS[index].clipSize;
    ammoReserve[index] = WEAPONS[index].reserve;
  }

  function giveAmmo(index) {
    if (index < 0 || index >= WEAPONS.length) return;
    ammoReserve[index] = WEAPONS[index].reserve;
  }

  function giveAllAmmo() {
    for (var i = 0; i < WEAPONS.length; i++) {
      if (ammoClip[i] > 0 || ammoReserve[i] > 0) {
        ammoReserve[i] = WEAPONS[i].reserve;
      }
    }
  }

  // ─── Update (called every frame) ───
  function update(dt) {
    var engine = FPSV4.Engine;
    var player = engine.getPlayer();
    var keys = engine.getKeys();

    if (!player.alive) return;

    // Fire timer countdown
    if (fireTimer > 0) fireTimer -= dt;
    if (knifeCooldown > 0) knifeCooldown -= dt;

    // Reload timer
    if (reloading) {
      reloadTimer -= dt;
      if (reloadTimer <= 0) {
        finishReload();
      }
    }

    // Spread recovery
    spreadAccum *= Math.max(0, 1 - dt * 4);

    // ADS
    var wantAds = engine.isMouseRightDown() && !reloading && !player.sprinting;
    ads = wantAds;
    var adsTarget = ads ? 1 : 0;
    adsLerp += (adsTarget - adsLerp) * Math.min(1, dt * 12);

    // Weapon switching (number keys)
    if (!reloading) {
      for (var w = 0; w < WEAPONS.length; w++) {
        if (keys['Digit' + (w + 1)] && (ammoClip[w] > 0 || ammoReserve[w] > 0)) {
          if (currentWeapon !== w) {
            currentWeapon = w;
            ads = false;
            adsLerp = 0;
            spreadAccum = 0;
          }
        }
      }
    }

    // Reload (R key)
    if (keys['KeyR'] && !reloading) {
      startReload();
    }

    // Fire (left mouse)
    var wep = WEAPONS[currentWeapon];
    if (engine.isMouseDown() && fireTimer <= 0 && !reloading && !player.sprinting) {
      if (ammoClip[currentWeapon] > 0) {
        fire();
      } else if (ammoReserve[currentWeapon] > 0) {
        startReload();
      }
      // Semi-auto: require re-click
      if (!wep.auto) {
        // Will prevent continuous fire until mouse released and pressed again
        fireTimer = 1 / wep.fireRate;
      }
    }

    // Knife (V key)
    if (keys['KeyV'] && knifeCooldown <= 0) {
      knifeAttack();
    }

    // Footsteps
    var moving = keys['KeyW'] || keys['KeyS'] || keys['KeyA'] || keys['KeyD'];
    if (moving && player.onGround) {
      var stepInterval = player.sprinting ? 0.3 : 0.45;
      footstepTimer += dt;
      if (footstepTimer >= stepInterval) {
        footstepTimer = 0;
        FPSV4.Audio.playFootstep(player.sprinting);
      }
    } else {
      footstepTimer = 0;
    }

    // Render first-person weapon
    renderFPWeapon(dt);
  }

  // ─── Fire ───
  function fire() {
    var wep = WEAPONS[currentWeapon];
    ammoClip[currentWeapon]--;
    fireTimer = 1 / wep.fireRate;

    // Audio
    FPSV4.Audio.playGunshot(wep.id);

    // Recoil
    var player = FPSV4.Engine.getPlayer();
    player.viewPunchX = -wep.recoil * 0.002 * (0.8 + Math.random() * 0.4);
    player.viewPunchY = (Math.random() - 0.5) * wep.recoil * 0.001;

    // Spread
    spreadAccum = Math.min(spreadAccum + wep.spread * 0.5, wep.spread * 3);
    var totalSpread = wep.spread + spreadAccum;
    if (ads) totalSpread *= 0.4;

    // Muzzle flash
    var flashEl = document.getElementById('muzzle-flash-overlay');
    if (flashEl) {
      flashEl.classList.add('active');
      setTimeout(function () { flashEl.classList.remove('active'); }, 40);
    }

    // FP weapon kick animation
    var fpEl = document.getElementById('fp-weapon');
    if (fpEl) {
      fpEl.classList.remove('firing');
      void fpEl.offsetWidth; // Reflow
      fpEl.classList.add('firing');
    }

    // Raycast against zombies
    var camera = FPSV4.Engine.getCamera();
    var dir = new THREE.Vector3(0, 0, -1);
    dir.applyQuaternion(camera.quaternion);
    // Apply spread
    dir.x += (Math.random() - 0.5) * totalSpread;
    dir.y += (Math.random() - 0.5) * totalSpread;
    dir.normalize();

    var raycaster = new THREE.Raycaster(camera.position.clone(), dir, 0, wep.range);

    // Check hits against zombies
    if (FPSV4.Zombies) {
      var hitResult = FPSV4.Zombies.checkHit(raycaster, wep.damage, wep.headshotMult);
      if (hitResult.hit) {
        // Hitmarker
        var hmEl = document.getElementById('hitmarker');
        if (hmEl) {
          hmEl.classList.add('show');
          setTimeout(function () { hmEl.classList.remove('show'); }, 100);
        }
        if (hitResult.headshot) {
          FPSV4.Audio.playHeadshot();
        } else {
          FPSV4.Audio.playHit();
        }
        if (hitResult.killed) {
          FPSV4.Audio.playKill();
          var pts = hitResult.headshot ? 150 : 100;
          if (FPSV4.GameMode) FPSV4.GameMode.addPoints(pts, hitResult.headshot);
          if (FPSV4.GameMode) FPSV4.GameMode.addKill(hitResult.headshot);
        } else {
          // Hit but not killed: 10 pts
          if (FPSV4.GameMode) FPSV4.GameMode.addPoints(10, false);
        }
      }
    }
  }

  // ─── Knife Attack ───
  function knifeAttack() {
    knifeCooldown = KNIFE.cooldown;
    FPSV4.Audio.playKnifeSwing();

    var camera = FPSV4.Engine.getCamera();
    var dir = new THREE.Vector3(0, 0, -1);
    dir.applyQuaternion(camera.quaternion);
    var raycaster = new THREE.Raycaster(camera.position.clone(), dir, 0, KNIFE.range);

    if (FPSV4.Zombies) {
      var hitResult = FPSV4.Zombies.checkHit(raycaster, KNIFE.damage, 1.5);
      if (hitResult.hit) {
        FPSV4.Audio.playHit();
        if (hitResult.killed) {
          FPSV4.Audio.playKill();
          if (FPSV4.GameMode) FPSV4.GameMode.addPoints(50, false);
          if (FPSV4.GameMode) FPSV4.GameMode.addKill(hitResult.headshot);
        }
      }
    }
  }

  // ─── Reload ───
  function startReload() {
    var wep = WEAPONS[currentWeapon];
    if (ammoClip[currentWeapon] >= wep.clipSize) return;
    if (ammoReserve[currentWeapon] <= 0) return;
    if (reloading) return;

    reloading = true;
    reloadTimer = 1.5; // 1.5s reload time
    ads = false;
    FPSV4.Audio.playReload();

    var fpEl = document.getElementById('fp-weapon');
    if (fpEl) {
      fpEl.classList.remove('reloading');
      void fpEl.offsetWidth;
      fpEl.classList.add('reloading');
    }
  }

  function finishReload() {
    var wep = WEAPONS[currentWeapon];
    var needed = wep.clipSize - ammoClip[currentWeapon];
    var available = Math.min(needed, ammoReserve[currentWeapon]);
    ammoClip[currentWeapon] += available;
    ammoReserve[currentWeapon] -= available;
    reloading = false;
    reloadTimer = 0;
  }

  // ─── First-Person Weapon Renderer (Canvas 2D) ───
  function renderFPWeapon(dt) {
    if (!fpCtx) return;
    var ctx = fpCtx;
    var w = fpCanvas.width;
    var h = fpCanvas.height;
    ctx.clearRect(0, 0, w, h);

    var wep = WEAPONS[currentWeapon];
    var player = FPSV4.Engine.getPlayer();

    // Weapon bob from movement
    var bobX = Math.sin(player.headBobTimer * 0.7) * 3;
    var bobY = Math.abs(Math.cos(player.headBobTimer * 0.7)) * 4;

    // ADS offset (move weapon to center)
    var adsOffsetX = adsLerp * -60;
    var adsOffsetY = adsLerp * 30;

    ctx.save();
    ctx.translate(w / 2 + 80 + bobX + adsOffsetX, h - 20 + bobY + adsOffsetY);

    // Draw weapon based on type
    var baseColor = wep.color;

    if (wep.id === 'm1911') {
      // Pistol shape
      ctx.fillStyle = '#444';
      ctx.fillRect(-15, -60, 30, 45); // Body
      ctx.fillStyle = '#333';
      ctx.fillRect(-8, -95, 16, 40); // Barrel
      ctx.fillStyle = '#555';
      ctx.fillRect(-12, -15, 24, 35); // Grip
      ctx.fillStyle = '#222';
      ctx.fillRect(-5, -12, 10, 28); // Grip texture
      // Trigger guard
      ctx.strokeStyle = '#444';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(0, -18, 10, 0, Math.PI);
      ctx.stroke();
    } else if (wep.id === 'shotgun') {
      ctx.fillStyle = '#5a3a1a';
      ctx.fillRect(-18, -50, 36, 35); // Body
      ctx.fillStyle = '#444';
      ctx.fillRect(-10, -110, 20, 65); // Barrel
      ctx.fillRect(-8, -115, 16, 8); // Front sight
      ctx.fillStyle = '#6b4a2a';
      ctx.fillRect(-14, -15, 28, 40); // Stock
      ctx.fillStyle = '#333';
      ctx.fillRect(-6, -50, 12, 10); // Pump
    } else if (wep.id === 'smg') {
      ctx.fillStyle = '#444';
      ctx.fillRect(-14, -55, 28, 40); // Body
      ctx.fillStyle = '#333';
      ctx.fillRect(-7, -100, 14, 50); // Barrel
      ctx.fillStyle = '#555';
      ctx.fillRect(-10, -15, 20, 30); // Grip
      ctx.fillStyle = '#3b82f6';
      ctx.fillRect(-16, -45, 3, 20); // Magazine
    } else if (wep.id === 'assault') {
      ctx.fillStyle = '#4a4a4a';
      ctx.fillRect(-16, -55, 32, 38); // Body
      ctx.fillStyle = '#383838';
      ctx.fillRect(-8, -110, 16, 60); // Barrel
      ctx.fillStyle = '#555';
      ctx.fillRect(-12, -15, 24, 35); // Stock
      ctx.fillStyle = '#22c55e';
      ctx.fillRect(-18, -50, 4, 25); // Magazine
      // Rail
      ctx.fillStyle = '#333';
      ctx.fillRect(-10, -58, 20, 3);
    } else if (wep.id === 'sniper') {
      ctx.fillStyle = '#2d3748';
      ctx.fillRect(-14, -55, 28, 35); // Body
      ctx.fillStyle = '#222';
      ctx.fillRect(-6, -130, 12, 80); // Long barrel
      ctx.fillStyle = '#555';
      ctx.fillRect(-12, -15, 24, 40); // Stock
      // Scope
      ctx.fillStyle = '#a855f7';
      ctx.fillRect(-10, -65, 20, 8);
      ctx.beginPath();
      ctx.arc(0, -61, 6, 0, Math.PI * 2);
      ctx.fillStyle = '#333';
      ctx.fill();
    } else if (wep.id === 'rocket') {
      ctx.fillStyle = '#5a5a5a';
      ctx.fillRect(-20, -50, 40, 30); // Tube
      ctx.fillStyle = '#444';
      ctx.beginPath();
      ctx.arc(0, -55, 18, Math.PI, 0);
      ctx.fill();
      ctx.fillStyle = '#666';
      ctx.fillRect(-14, -15, 28, 30); // Grip
      ctx.fillStyle = '#ef4444';
      ctx.fillRect(-12, -80, 24, 30); // Warhead tip
    }

    ctx.restore();
  }

  // ─── Public API ───
  return {
    init: init,
    update: update,
    resetWeapons: resetWeapons,
    giveWeapon: giveWeapon,
    giveAmmo: giveAmmo,
    giveAllAmmo: giveAllAmmo,
    isADS: function () { return ads; },
    getADSLerp: function () { return adsLerp; },
    isReloading: function () { return reloading; },
    getCurrentWeapon: function () { return WEAPONS[currentWeapon]; },
    getCurrentWeaponIndex: function () { return currentWeapon; },
    getClip: function () { return ammoClip[currentWeapon]; },
    getReserve: function () { return ammoReserve[currentWeapon]; },
    getWeapons: function () { return WEAPONS; },
    getSpreadAccum: function () { return spreadAccum; }
  };
})();
