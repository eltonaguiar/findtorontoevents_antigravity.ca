/**
 * FPSV4 GameMode — Wave system, points, game state machine, persistence
 */
var FPSV4 = window.FPSV4 || {};

FPSV4.GameMode = (function () {
  'use strict';

  // ─── Game States ───
  var STATE = {
    MENU: 'menu',
    COUNTDOWN: 'countdown',
    PLAYING: 'playing',
    INTERMISSION: 'intermission',
    GAMEOVER: 'gameover'
  };

  // ─── State ───
  var state = STATE.MENU;
  var round = 1;
  var points = 500; // Start with 500 pts
  var totalPointsEarned = 0;
  var kills = 0;
  var headshots = 0;
  var zombiesKilledThisRound = 0;
  var zombiesToSpawnThisRound = 0;
  var zombiesSpawned = 0;
  var spawnTimer = 0;
  var intermissionTimer = 0;
  var countdownTimer = 0;
  var gameTime = 0;

  var INTERMISSION_DURATION = 12;
  var COUNTDOWN_DURATION = 3;

  // Persistent stats
  var STORAGE_KEY = 'fpsv4_stats';
  var persistent = {
    bestRound: 0,
    totalKills: 0,
    totalGames: 0,
    totalHeadshots: 0
  };

  // ─── Zombie Count Formula ───
  function zombiesForRound(r) {
    // Starts manageable, escalates
    return Math.floor(0.08 * r * r + 0.2 * r + 6);
    // R1: 6, R5: 9, R10: 16, R15: 25, R20: 38, R30: 78
  }

  // ─── Zombie Stats Per Round ───
  function zombieHealth(r) {
    if (r <= 9) return 100 + r * 50;
    return (100 + r * 50) * (1 + (r - 9) * 0.08);
  }

  function zombieSpeed(r) {
    // Base 2.5, caps at 5.5
    return Math.min(5.5, 2.5 + r * 0.12);
  }

  function zombieDamage(r) {
    // Base 25, increases by 3 per round
    return Math.min(80, 25 + r * 3);
  }

  function spawnInterval(r) {
    // Faster spawns at higher rounds
    return Math.max(0.4, 2.0 - r * 0.1);
  }

  // ─── Load / Save Persistent Stats ───
  function loadStats() {
    try {
      var data = localStorage.getItem(STORAGE_KEY);
      if (data) {
        var parsed = JSON.parse(data);
        persistent.bestRound = parsed.bestRound || 0;
        persistent.totalKills = parsed.totalKills || 0;
        persistent.totalGames = parsed.totalGames || 0;
        persistent.totalHeadshots = parsed.totalHeadshots || 0;
      }
    } catch (e) { /* ignore */ }
  }

  function saveStats() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(persistent));
    } catch (e) { /* ignore */ }
  }

  // ─── Start Game ───
  function startGame() {
    loadStats();
    round = 1;
    points = 500;
    totalPointsEarned = 0;
    kills = 0;
    headshots = 0;
    gameTime = 0;

    // Reset systems
    FPSV4.Engine.resetPlayer();
    FPSV4.Weapons.resetWeapons();
    FPSV4.Zombies.clearAll();

    // Show HUD, hide menus
    document.getElementById('hud').style.display = 'block';
    document.getElementById('fp-weapon').style.display = 'block';
    document.getElementById('main-menu').classList.add('hidden');
    document.getElementById('game-over').classList.remove('active');
    document.getElementById('pause-menu').classList.remove('active');

    // Lock pointer
    FPSV4.Engine.lockPointer();

    // Audio init
    FPSV4.Audio.init();

    // Start engine game loop
    FPSV4.Engine.start(gameUpdate);

    // Begin countdown to first round
    startCountdown();

    console.log('[FPSV4 GameMode] Game started');
  }

  // ─── Countdown ───
  function startCountdown() {
    state = STATE.COUNTDOWN;
    countdownTimer = COUNTDOWN_DURATION;
    var cdEl = document.getElementById('countdown');
    if (cdEl) cdEl.style.display = 'block';
  }

  function updateCountdown(dt) {
    countdownTimer -= dt;
    var cdEl = document.getElementById('countdown');
    if (cdEl) {
      var num = Math.ceil(countdownTimer);
      cdEl.textContent = num > 0 ? num : 'GO!';
    }
    if (countdownTimer <= -0.5) {
      var cdEl2 = document.getElementById('countdown');
      if (cdEl2) cdEl2.style.display = 'none';
      startRound();
    }
  }

  // ─── Start Round ───
  function startRound() {
    state = STATE.PLAYING;
    zombiesKilledThisRound = 0;
    zombiesToSpawnThisRound = zombiesForRound(round);
    zombiesSpawned = 0;
    spawnTimer = 0;

    FPSV4.Audio.playRoundStart();
    if (FPSV4.UI) FPSV4.UI.showRoundBanner(round);

    console.log('[FPSV4] Round', round, '- Zombies:', zombiesToSpawnThisRound);
  }

  // ─── Game Update (called by engine every frame) ───
  function gameUpdate(dt) {
    if (state === STATE.COUNTDOWN) {
      updateCountdown(dt);
      FPSV4.Weapons.update(dt);
      if (FPSV4.UI) FPSV4.UI.update();
      return;
    }

    if (state === STATE.PLAYING) {
      gameTime += dt;

      // Spawn zombies
      if (zombiesSpawned < zombiesToSpawnThisRound) {
        spawnTimer += dt;
        var interval = spawnInterval(round);
        while (spawnTimer >= interval && zombiesSpawned < zombiesToSpawnThisRound) {
          // Only spawn if below max alive
          if (FPSV4.Zombies.getActiveCount() < 24) {
            FPSV4.Zombies.spawn(
              zombieHealth(round),
              zombieSpeed(round) + (Math.random() - 0.5) * 0.5,
              zombieDamage(round)
            );
            zombiesSpawned++;
          }
          spawnTimer -= interval;
        }
      }

      // Check round complete
      if (zombiesSpawned >= zombiesToSpawnThisRound && FPSV4.Zombies.getActiveCount() === 0) {
        endRound();
      }

      // Update systems
      FPSV4.Zombies.update(dt);
      FPSV4.Weapons.update(dt);
      if (FPSV4.UI) FPSV4.UI.update();
      return;
    }

    if (state === STATE.INTERMISSION) {
      intermissionTimer -= dt;

      // Update HUD with intermission timer
      if (FPSV4.UI) FPSV4.UI.update();

      // Allow weapon switching and reloading during intermission
      FPSV4.Weapons.update(dt);

      if (intermissionTimer <= 0) {
        round++;
        startCountdown();
      }
      return;
    }

    if (state === STATE.GAMEOVER) {
      // Just keep rendering, zombies can still animate
      FPSV4.Zombies.update(dt);
      return;
    }
  }

  // ─── End Round ───
  function endRound() {
    state = STATE.INTERMISSION;
    intermissionTimer = INTERMISSION_DURATION;

    FPSV4.Audio.playRoundEnd();

    console.log('[FPSV4] Round', round, 'complete!');
  }

  // ─── Points ───
  function addPoints(pts, isHeadshot) {
    points += pts;
    totalPointsEarned += pts;
    if (FPSV4.UI) FPSV4.UI.showPointsPopup(pts, isHeadshot);
  }

  function spendPoints(cost) {
    if (points >= cost) {
      points -= cost;
      return true;
    }
    return false;
  }

  // ─── Kill Tracking ───
  function addKill(isHeadshot) {
    kills++;
    if (isHeadshot) headshots++;
    if (FPSV4.UI) FPSV4.UI.addKillFeed(isHeadshot);
  }

  function onZombieKilled() {
    zombiesKilledThisRound++;
  }

  // ─── Player Death ───
  function onPlayerDeath() {
    state = STATE.GAMEOVER;

    // Update persistent stats
    persistent.totalKills += kills;
    persistent.totalHeadshots += headshots;
    persistent.totalGames++;
    if (round > persistent.bestRound) persistent.bestRound = round;
    saveStats();

    // Show game over screen
    setTimeout(function () {
      if (FPSV4.UI) FPSV4.UI.showGameOver(round, kills, headshots, totalPointsEarned);
    }, 1500);

    // Release pointer
    if (document.exitPointerLock) document.exitPointerLock();

    console.log('[FPSV4] Game Over at round', round);
  }

  // ─── Pause ───
  function togglePause() {
    if (state === STATE.GAMEOVER || state === STATE.MENU) return;
    var pauseEl = document.getElementById('pause-menu');
    if (pauseEl.classList.contains('active')) {
      resumeGame();
    } else {
      pauseEl.classList.add('active');
      if (document.exitPointerLock) document.exitPointerLock();
    }
  }

  function resumeGame() {
    var pauseEl = document.getElementById('pause-menu');
    pauseEl.classList.remove('active');
    FPSV4.Engine.lockPointer();
  }

  // ─── Restart ───
  function restart() {
    FPSV4.Zombies.clearAll();
    document.getElementById('pause-menu').classList.remove('active');
    document.getElementById('game-over').classList.remove('active');
    startGame();
  }

  // ─── Back to Menu ───
  function toMenu() {
    FPSV4.Zombies.clearAll();
    document.getElementById('game-over').classList.remove('active');
    document.getElementById('hud').style.display = 'none';
    document.getElementById('fp-weapon').style.display = 'none';
    document.getElementById('main-menu').classList.remove('hidden');
    state = STATE.MENU;
    if (FPSV4.UI) FPSV4.UI.updateMenuStats();
    if (document.exitPointerLock) document.exitPointerLock();
  }

  // ─── Init ───
  function initModule() {
    loadStats();

    // Play button
    var btnPlay = document.getElementById('btn-play');
    if (btnPlay) {
      btnPlay.addEventListener('click', function () {
        startGame();
      });
    }
  }

  return {
    init: initModule,
    startGame: startGame,
    resume: resumeGame,
    restart: restart,
    toMenu: toMenu,
    togglePause: togglePause,
    addPoints: addPoints,
    spendPoints: spendPoints,
    addKill: addKill,
    onZombieKilled: onZombieKilled,
    onPlayerDeath: onPlayerDeath,
    getState: function () { return state; },
    getRound: function () { return round; },
    getPoints: function () { return points; },
    getKills: function () { return kills; },
    getHeadshots: function () { return headshots; },
    getGameTime: function () { return gameTime; },
    getIntermissionTimer: function () { return intermissionTimer; },
    getPersistent: function () { return persistent; },
    getZombiesRemaining: function () { return zombiesToSpawnThisRound - zombiesSpawned + FPSV4.Zombies.getActiveCount(); },
    STATES: STATE
  };
})();
