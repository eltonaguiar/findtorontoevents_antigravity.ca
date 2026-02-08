/**
 * FPSV4 Engine — Core renderer, camera, movement, physics, map
 */
var FPSV4 = window.FPSV4 || {};

FPSV4.Engine = (function () {
  'use strict';

  // ─── Constants ───
  var ARENA_SIZE = 50;
  var WALL_HEIGHT = 5;
  var PLAYER_HEIGHT = 1.7;
  var PLAYER_SPEED = 6;
  var SPRINT_MULT = 1.6;
  var CROUCH_SPEED = 3;
  var GRAVITY = -22;
  var JUMP_SPEED = 9;
  var MOUSE_SENS = 0.002;
  var PLAYER_RADIUS = 0.4;

  // ─── Three.js objects ───
  var scene, camera, renderer, clock;
  var canvas;

  // ─── Player state ───
  var player = {
    pos: new THREE.Vector3(0, PLAYER_HEIGHT, 0),
    vel: new THREE.Vector3(),
    pitch: 0,
    yaw: 0,
    onGround: true,
    sprinting: false,
    crouching: false,
    crouchLerp: 0,
    headBobTimer: 0,
    headBobAmount: 0,
    health: 100,
    maxHealth: 100,
    alive: true,
    // Screen effects
    screenShake: 0,
    viewPunchX: 0,
    viewPunchY: 0
  };

  // ─── Input ───
  var keys = {};
  var mouseDown = false;
  var mouseRightDown = false;

  // ─── Arena collision objects ───
  var arenaObjects = []; // Array of { min: Vector3, max: Vector3 } AABBs

  // ─── FPS tracking ───
  var frameCount = 0;
  var lastFpsTime = 0;
  var currentFps = 60;

  // ─── Game loop callback ───
  var updateCallback = null;
  var loopRunning = false;

  // ─── Init ───
  function init() {
    canvas = document.getElementById('game-canvas');

    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x050508);
    scene.fog = new THREE.FogExp2(0x050508, 0.018);

    // Camera
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 200);
    camera.position.copy(player.pos);

    // Renderer
    renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, powerPreference: 'high-performance' });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.9;

    // Clock
    clock = new THREE.Clock();

    // Lighting
    setupLighting();

    // Build the arena
    buildArena();

    // Input
    setupInput();

    // Resize
    window.addEventListener('resize', function () {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });

    console.log('[FPSV4 Engine] Initialized');
  }

  // ─── Lighting ───
  function setupLighting() {
    // Dim ambient — eerie underground feel
    var hemiLight = new THREE.HemisphereLight(0x1a1a3e, 0x0a0a1a, 0.3);
    scene.add(hemiLight);

    // Directional moonlight (very dim)
    var dirLight = new THREE.DirectionalLight(0x4466aa, 0.15);
    dirLight.position.set(10, 20, 5);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 60;
    dirLight.shadow.camera.left = -30;
    dirLight.shadow.camera.right = 30;
    dirLight.shadow.camera.top = 30;
    dirLight.shadow.camera.bottom = -30;
    scene.add(dirLight);

    // Emergency red lights scattered around
    var redPositions = [
      [-15, 4, -15], [15, 4, -15], [-15, 4, 15], [15, 4, 15],
      [0, 4, 0]
    ];
    redPositions.forEach(function (p) {
      var light = new THREE.PointLight(0xcc2222, 0.4, 18);
      light.position.set(p[0], p[1], p[2]);
      scene.add(light);
    });

    // Flickering fluorescent (simulated with a brighter point light)
    var fluorescent = new THREE.PointLight(0xddeeff, 0.6, 25);
    fluorescent.position.set(0, 4.5, 0);
    fluorescent.castShadow = true;
    scene.add(fluorescent);

    // Store for flickering effect
    FPSV4._fluorescent = fluorescent;
  }

  // ─── Arena Builder ───
  function buildArena() {
    var halfSize = ARENA_SIZE / 2;

    // Floor
    var floorGeo = new THREE.PlaneGeometry(ARENA_SIZE, ARENA_SIZE);
    var floorMat = new THREE.MeshStandardMaterial({ color: 0x1a1a1a, roughness: 0.95, metalness: 0.05 });
    var floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    // Grid on floor
    var grid = new THREE.GridHelper(ARENA_SIZE, 50, 0x222222, 0x181818);
    grid.position.y = 0.01;
    scene.add(grid);

    // Walls
    var wallMat = new THREE.MeshStandardMaterial({ color: 0x252530, roughness: 0.8, metalness: 0.2 });
    var wallDefs = [
      { pos: [0, WALL_HEIGHT / 2, -halfSize], size: [ARENA_SIZE, WALL_HEIGHT, 0.5] },
      { pos: [0, WALL_HEIGHT / 2, halfSize], size: [ARENA_SIZE, WALL_HEIGHT, 0.5] },
      { pos: [-halfSize, WALL_HEIGHT / 2, 0], size: [0.5, WALL_HEIGHT, ARENA_SIZE] },
      { pos: [halfSize, WALL_HEIGHT / 2, 0], size: [0.5, WALL_HEIGHT, ARENA_SIZE] }
    ];

    wallDefs.forEach(function (w) {
      var geo = new THREE.BoxGeometry(w.size[0], w.size[1], w.size[2]);
      var mesh = new THREE.Mesh(geo, wallMat);
      mesh.position.set(w.pos[0], w.pos[1], w.pos[2]);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      scene.add(mesh);
      // AABB collision
      arenaObjects.push({
        min: new THREE.Vector3(w.pos[0] - w.size[0] / 2, 0, w.pos[2] - w.size[2] / 2),
        max: new THREE.Vector3(w.pos[0] + w.size[0] / 2, w.size[1], w.pos[2] + w.size[2] / 2)
      });
    });

    // Interior structures — cover and obstacles
    var structures = [
      // Central pillar
      { pos: [0, 1.5, 0], size: [3, 3, 3], color: 0x2a2a3a },
      // Corner bunkers
      { pos: [-16, 1.5, -16], size: [5, 3, 5], color: 0x302020 },
      { pos: [16, 1.5, -16], size: [5, 3, 5], color: 0x203020 },
      { pos: [-16, 1.5, 16], size: [5, 3, 5], color: 0x202030 },
      { pos: [16, 1.5, 16], size: [5, 3, 5], color: 0x302030 },
      // Cover walls
      { pos: [-8, 1.5, 0], size: [0.5, 3, 6], color: 0x333345 },
      { pos: [8, 1.5, 0], size: [0.5, 3, 6], color: 0x333345 },
      { pos: [0, 1.5, -8], size: [6, 3, 0.5], color: 0x333345 },
      { pos: [0, 1.5, 8], size: [6, 3, 0.5], color: 0x333345 },
      // Crates
      { pos: [-12, 0.6, -6], size: [1.2, 1.2, 1.2], color: 0x4a3a2a },
      { pos: [12, 0.6, 6], size: [1.2, 1.2, 1.2], color: 0x4a3a2a },
      { pos: [6, 0.6, -12], size: [1.2, 1.2, 1.2], color: 0x4a3a2a },
      { pos: [-6, 0.6, 12], size: [1.2, 1.2, 1.2], color: 0x4a3a2a },
      // Low walls for crouch cover
      { pos: [-5, 0.5, -14], size: [4, 1, 0.4], color: 0x3a3a4a },
      { pos: [5, 0.5, 14], size: [4, 1, 0.4], color: 0x3a3a4a },
      // Shipping containers
      { pos: [-20, 1.5, -5], size: [3, 3, 6], color: 0x6b2a2a },
      { pos: [20, 1.5, 5], size: [3, 3, 6], color: 0x2a2a6b }
    ];

    var structMat;
    structures.forEach(function (s) {
      var geo = new THREE.BoxGeometry(s.size[0], s.size[1], s.size[2]);
      structMat = new THREE.MeshStandardMaterial({ color: s.color, roughness: 0.85, metalness: 0.15 });
      var mesh = new THREE.Mesh(geo, structMat);
      mesh.position.set(s.pos[0], s.pos[1], s.pos[2]);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      scene.add(mesh);
      // AABB
      arenaObjects.push({
        min: new THREE.Vector3(s.pos[0] - s.size[0] / 2, 0, s.pos[2] - s.size[2] / 2),
        max: new THREE.Vector3(s.pos[0] + s.size[0] / 2, s.size[1], s.pos[2] + s.size[2] / 2)
      });
    });

    // Neon strips on bunkers
    var neonColors = [0xef4444, 0x3b82f6, 0xa855f7, 0x22c55e];
    structures.slice(1, 5).forEach(function (s, i) {
      var nGeo = new THREE.BoxGeometry(s.size[0] + 0.2, 0.08, s.size[2] + 0.2);
      var nMat = new THREE.MeshBasicMaterial({ color: neonColors[i] });
      var nMesh = new THREE.Mesh(nGeo, nMat);
      nMesh.position.set(s.pos[0], s.pos[1] + s.size[1] / 2 + 0.04, s.pos[2]);
      scene.add(nMesh);
    });

    // Skybox (dark enclosure)
    var skyMat = new THREE.MeshBasicMaterial({ color: 0x020205, side: THREE.BackSide });
    var sky = new THREE.Mesh(new THREE.BoxGeometry(160, 40, 160), skyMat);
    sky.position.y = 15;
    scene.add(sky);

    // Dust particles
    var dustGeo = new THREE.BufferGeometry();
    var dustPos = [];
    for (var i = 0; i < 400; i++) {
      dustPos.push(
        (Math.random() - 0.5) * ARENA_SIZE,
        Math.random() * WALL_HEIGHT,
        (Math.random() - 0.5) * ARENA_SIZE
      );
    }
    dustGeo.setAttribute('position', new THREE.Float32BufferAttribute(dustPos, 3));
    var dustMat = new THREE.PointsMaterial({ color: 0x666666, size: 0.04, transparent: true, opacity: 0.25 });
    scene.add(new THREE.Points(dustGeo, dustMat));
  }

  // ─── Input Setup ───
  function setupInput() {
    document.addEventListener('keydown', function (e) {
      keys[e.code] = true;
      // Jump
      if (e.code === 'Space' && player.onGround && player.alive) {
        player.vel.y = JUMP_SPEED;
        player.onGround = false;
      }
      // Escape for pause
      if (e.code === 'Escape' && FPSV4.GameMode) {
        FPSV4.GameMode.togglePause();
      }
    });

    document.addEventListener('keyup', function (e) {
      keys[e.code] = false;
    });

    // Mouse move
    document.addEventListener('mousemove', function (e) {
      if (document.pointerLockElement !== canvas) return;
      if (!player.alive) return;

      var sens = MOUSE_SENS;
      // ADS reduces sensitivity
      if (FPSV4.Weapons && FPSV4.Weapons.isADS()) sens *= 0.5;

      player.yaw -= e.movementX * sens;
      player.pitch -= e.movementY * sens;
      player.pitch = Math.max(-Math.PI / 2 + 0.01, Math.min(Math.PI / 2 - 0.01, player.pitch));
    });

    // Mouse buttons
    canvas.addEventListener('mousedown', function (e) {
      if (e.button === 0) mouseDown = true;
      if (e.button === 2) mouseRightDown = true;
    });
    canvas.addEventListener('mouseup', function (e) {
      if (e.button === 0) mouseDown = false;
      if (e.button === 2) mouseRightDown = false;
    });

    // Pointer lock on click
    canvas.addEventListener('click', function () {
      if (!document.pointerLockElement) {
        canvas.requestPointerLock();
      }
      // Init audio on first click
      if (FPSV4.Audio) FPSV4.Audio.init();
    });

    // Prevent right-click menu
    canvas.addEventListener('contextmenu', function (e) { e.preventDefault(); });
  }

  // ─── Collision Detection ───
  function checkCollision(pos, radius) {
    for (var i = 0; i < arenaObjects.length; i++) {
      var box = arenaObjects[i];
      var closestX = Math.max(box.min.x, Math.min(pos.x, box.max.x));
      var closestZ = Math.max(box.min.z, Math.min(pos.z, box.max.z));
      var dx = pos.x - closestX;
      var dz = pos.z - closestZ;
      if (dx * dx + dz * dz < radius * radius) {
        return { hit: true, box: box, closestX: closestX, closestZ: closestZ };
      }
    }
    return { hit: false };
  }

  // ─── Movement Update ───
  function updateMovement(dt) {
    if (!player.alive) return;

    player.sprinting = keys['ShiftLeft'] || keys['ShiftRight'];
    player.crouching = keys['ControlLeft'] || keys['ControlRight'];
    if (player.sprinting) player.crouching = false;

    // Crouch lerp
    var targetCrouch = player.crouching ? 1 : 0;
    player.crouchLerp += (targetCrouch - player.crouchLerp) * Math.min(1, dt * 10);

    // Movement direction
    var moveX = 0, moveZ = 0;
    if (keys['KeyW']) moveZ -= 1;
    if (keys['KeyS']) moveZ += 1;
    if (keys['KeyA']) moveX -= 1;
    if (keys['KeyD']) moveX += 1;

    var moving = moveX !== 0 || moveZ !== 0;

    if (moving) {
      // Normalize
      var len = Math.sqrt(moveX * moveX + moveZ * moveZ);
      moveX /= len;
      moveZ /= len;

      // Speed
      var speed = player.crouching ? CROUCH_SPEED : (player.sprinting ? PLAYER_SPEED * SPRINT_MULT : PLAYER_SPEED);

      // Apply yaw rotation
      var sinY = Math.sin(player.yaw);
      var cosY = Math.cos(player.yaw);
      var worldX = moveX * cosY + moveZ * sinY;
      var worldZ = -moveX * sinY + moveZ * cosY;

      player.vel.x = worldX * speed;
      player.vel.z = worldZ * speed;
    } else {
      player.vel.x *= 0.85;
      player.vel.z *= 0.85;
    }

    // Gravity
    if (!player.onGround) {
      player.vel.y += GRAVITY * dt;
    }

    // Try move X
    var newX = player.pos.x + player.vel.x * dt;
    var testPos = { x: newX, z: player.pos.z };
    if (!checkCollision(testPos, PLAYER_RADIUS).hit) {
      player.pos.x = newX;
    } else {
      player.vel.x = 0;
    }

    // Try move Z
    var newZ = player.pos.z + player.vel.z * dt;
    testPos = { x: player.pos.x, z: newZ };
    if (!checkCollision(testPos, PLAYER_RADIUS).hit) {
      player.pos.z = newZ;
    } else {
      player.vel.z = 0;
    }

    // Move Y
    player.pos.y += player.vel.y * dt;

    // Ground check
    var eyeHeight = PLAYER_HEIGHT - player.crouchLerp * 0.6;
    if (player.pos.y <= eyeHeight) {
      player.pos.y = eyeHeight;
      player.vel.y = 0;
      player.onGround = true;
    }

    // Arena bounds clamping
    var half = ARENA_SIZE / 2 - 1;
    player.pos.x = Math.max(-half, Math.min(half, player.pos.x));
    player.pos.z = Math.max(-half, Math.min(half, player.pos.z));

    // Head bob
    if (moving && player.onGround) {
      var bobSpeed = player.sprinting ? 12 : 7;
      player.headBobTimer += dt * bobSpeed;
      player.headBobAmount = Math.sin(player.headBobTimer) * (player.sprinting ? 0.06 : 0.03);
    } else {
      player.headBobAmount *= 0.9;
    }

    // Screen shake decay
    player.screenShake *= Math.max(0, 1 - dt * 8);
    player.viewPunchX *= Math.max(0, 1 - dt * 6);
    player.viewPunchY *= Math.max(0, 1 - dt * 6);

    // Update camera
    camera.position.set(
      player.pos.x + (Math.random() - 0.5) * player.screenShake,
      player.pos.y + player.headBobAmount + (Math.random() - 0.5) * player.screenShake,
      player.pos.z + (Math.random() - 0.5) * player.screenShake
    );
    camera.rotation.set(player.pitch + player.viewPunchX, player.yaw + player.viewPunchY, 0, 'YXZ');
  }

  // ─── Fluorescent flicker ───
  var flickerTimer = 0;
  function updateFlicker(dt) {
    flickerTimer += dt;
    if (FPSV4._fluorescent) {
      // Subtle random flicker
      var flicker = 0.5 + Math.sin(flickerTimer * 30) * 0.05 + Math.random() * 0.1;
      FPSV4._fluorescent.intensity = flicker;
    }
  }

  // ─── Game Loop ───
  function gameLoop() {
    requestAnimationFrame(gameLoop);

    var dt = clock.getDelta();
    dt = Math.min(dt, 0.05); // Cap delta to prevent physics explosions

    // FPS counter
    frameCount++;
    var now = performance.now();
    if (now - lastFpsTime >= 1000) {
      currentFps = frameCount;
      frameCount = 0;
      lastFpsTime = now;
      var fpsEl = document.getElementById('fps-value');
      if (fpsEl) {
        fpsEl.textContent = currentFps;
        fpsEl.style.color = currentFps >= 55 ? '#22c55e' : currentFps >= 30 ? '#f59e0b' : '#ef4444';
      }
    }

    // Update movement
    updateMovement(dt);

    // Flicker
    updateFlicker(dt);

    // External update (weapons, zombies, game mode)
    if (updateCallback) updateCallback(dt);

    // Render
    renderer.render(scene, camera);
  }

  // ─── Raycasting Utility ───
  var raycaster = new THREE.Raycaster();

  function raycastFromCamera(maxDist) {
    var dir = new THREE.Vector3(0, 0, -1);
    dir.applyQuaternion(camera.quaternion);
    raycaster.set(camera.position, dir);
    raycaster.far = maxDist || 100;
    return raycaster;
  }

  // ─── Player Damage ───
  function damagePlayer(amount) {
    if (!player.alive) return;
    player.health -= amount;
    player.screenShake = 0.15;
    if (player.health <= 0) {
      player.health = 0;
      player.alive = false;
      if (FPSV4.GameMode) FPSV4.GameMode.onPlayerDeath();
    }
    if (FPSV4.UI) FPSV4.UI.showDamageOverlay();
    if (FPSV4.Audio) FPSV4.Audio.playDamage();
  }

  function healPlayer(amount) {
    player.health = Math.min(player.maxHealth, player.health + amount);
  }

  // ─── Reset Player ───
  function resetPlayer() {
    player.pos.set(0, PLAYER_HEIGHT, 0);
    player.vel.set(0, 0, 0);
    player.pitch = 0;
    player.yaw = 0;
    player.health = 100;
    player.maxHealth = 100;
    player.alive = true;
    player.onGround = true;
    player.screenShake = 0;
    player.viewPunchX = 0;
    player.viewPunchY = 0;
  }

  // ─── Start ───
  function start(onUpdate) {
    updateCallback = onUpdate;
    if (!loopRunning) {
      loopRunning = true;
      gameLoop();
      console.log('[FPSV4 Engine] Game loop started');
    }
  }

  // ─── Public API ───
  return {
    init: init,
    start: start,
    getScene: function () { return scene; },
    getCamera: function () { return camera; },
    getPlayer: function () { return player; },
    getKeys: function () { return keys; },
    isMouseDown: function () { return mouseDown; },
    isMouseRightDown: function () { return mouseRightDown; },
    getCanvas: function () { return canvas; },
    getArenaSize: function () { return ARENA_SIZE; },
    getArenaObjects: function () { return arenaObjects; },
    raycastFromCamera: raycastFromCamera,
    damagePlayer: damagePlayer,
    healPlayer: healPlayer,
    resetPlayer: resetPlayer,
    lockPointer: function () { if (canvas) canvas.requestPointerLock(); }
  };
})();
