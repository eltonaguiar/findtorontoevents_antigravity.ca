/**
 * FPSV4 Zombies — Zombie AI, spawning, hit detection, object pooling
 */
var FPSV4 = window.FPSV4 || {};

FPSV4.Zombies = (function () {
  'use strict';

  var MAX_ALIVE = 24;
  var SPAWN_EDGE_OFFSET = 2;
  var ATTACK_RANGE = 1.8;
  var ATTACK_COOLDOWN = 1.2;
  var DEATH_LINGER = 3; // seconds before corpse fades
  var GROAN_INTERVAL_MIN = 4;
  var GROAN_INTERVAL_MAX = 12;

  // Zombie pool
  var pool = [];
  var activeZombies = [];
  var scene = null;

  // ─── Zombie Mesh Builder ───
  function createZombieMesh() {
    var group = new THREE.Group();

    // Body — greenish decayed
    var bodyGeo = new THREE.BoxGeometry(0.55, 0.95, 0.35);
    var bodyMat = new THREE.MeshStandardMaterial({ color: 0x3a5a3a, roughness: 0.8 });
    var body = new THREE.Mesh(bodyGeo, bodyMat);
    body.position.y = 1.15;
    body.castShadow = true;
    body.name = 'body';
    group.add(body);

    // Head — pale
    var headGeo = new THREE.SphereGeometry(0.18, 8, 8);
    var headMat = new THREE.MeshStandardMaterial({ color: 0x8a9a7a, roughness: 0.6 });
    var head = new THREE.Mesh(headGeo, headMat);
    head.position.y = 1.82;
    head.castShadow = true;
    head.name = 'head';
    group.add(head);

    // Glowing eyes
    var eyeGeo = new THREE.SphereGeometry(0.035, 4, 4);
    var eyeMat = new THREE.MeshBasicMaterial({ color: 0x44ff44 });
    var leftEye = new THREE.Mesh(eyeGeo, eyeMat);
    leftEye.position.set(-0.06, 1.84, 0.14);
    group.add(leftEye);
    var rightEye = new THREE.Mesh(eyeGeo, eyeMat);
    rightEye.position.set(0.06, 1.84, 0.14);
    group.add(rightEye);

    // Arms — reaching forward
    var armGeo = new THREE.BoxGeometry(0.1, 0.55, 0.1);
    var armMat = new THREE.MeshStandardMaterial({ color: 0x3a5a3a, roughness: 0.7 });
    var leftArm = new THREE.Mesh(armGeo, armMat);
    leftArm.position.set(-0.38, 1.1, 0.15);
    leftArm.rotation.x = -0.5;
    leftArm.castShadow = true;
    group.add(leftArm);
    var rightArm = new THREE.Mesh(armGeo, armMat);
    rightArm.position.set(0.38, 1.1, 0.15);
    rightArm.rotation.x = -0.5;
    rightArm.castShadow = true;
    group.add(rightArm);

    // Legs
    var legGeo = new THREE.BoxGeometry(0.14, 0.65, 0.14);
    var legMat = new THREE.MeshStandardMaterial({ color: 0x2a3a2a, roughness: 0.8 });
    var leftLeg = new THREE.Mesh(legGeo, legMat);
    leftLeg.position.set(-0.14, 0.33, 0);
    leftLeg.castShadow = true;
    group.add(leftLeg);
    var rightLeg = new THREE.Mesh(legGeo, legMat);
    rightLeg.position.set(0.14, 0.33, 0);
    rightLeg.castShadow = true;
    group.add(rightLeg);

    group.visible = false;
    return group;
  }

  // ─── Init ───
  function init() {
    scene = FPSV4.Engine.getScene();

    // Pre-create zombie pool
    for (var i = 0; i < MAX_ALIVE; i++) {
      var mesh = createZombieMesh();
      scene.add(mesh);
      pool.push({
        mesh: mesh,
        active: false,
        health: 0,
        maxHealth: 0,
        speed: 0,
        damage: 0,
        pos: new THREE.Vector3(),
        attackTimer: 0,
        groanTimer: Math.random() * GROAN_INTERVAL_MAX,
        deathTimer: 0,
        dying: false,
        // Shamble animation
        shambleTimer: Math.random() * Math.PI * 2,
        shambleSpeed: 2 + Math.random()
      });
    }

    console.log('[FPSV4 Zombies] Pool created:', MAX_ALIVE);
  }

  // ─── Spawn a Zombie ───
  function spawn(health, speed, damage) {
    // Find inactive slot
    var zombie = null;
    for (var i = 0; i < pool.length; i++) {
      if (!pool[i].active) {
        zombie = pool[i];
        break;
      }
    }
    if (!zombie) return null; // Pool exhausted

    var arenaSize = FPSV4.Engine.getArenaSize();
    var half = arenaSize / 2 - SPAWN_EDGE_OFFSET;

    // Spawn at random edge
    var side = Math.floor(Math.random() * 4);
    var x, z;
    switch (side) {
      case 0: x = -half; z = (Math.random() - 0.5) * arenaSize * 0.8; break;
      case 1: x = half; z = (Math.random() - 0.5) * arenaSize * 0.8; break;
      case 2: z = -half; x = (Math.random() - 0.5) * arenaSize * 0.8; break;
      default: z = half; x = (Math.random() - 0.5) * arenaSize * 0.8; break;
    }

    zombie.active = true;
    zombie.health = health;
    zombie.maxHealth = health;
    zombie.speed = speed;
    zombie.damage = damage;
    zombie.pos.set(x, 0, z);
    zombie.attackTimer = 0;
    zombie.dying = false;
    zombie.deathTimer = 0;
    zombie.shambleTimer = Math.random() * Math.PI * 2;

    zombie.mesh.visible = true;
    zombie.mesh.position.copy(zombie.pos);
    zombie.mesh.rotation.set(0, 0, 0);
    zombie.mesh.scale.set(1, 1, 1);

    // Reset materials to normal opacity
    zombie.mesh.traverse(function (child) {
      if (child.isMesh && child.material) {
        child.material.transparent = false;
        child.material.opacity = 1;
      }
    });

    activeZombies.push(zombie);
    return zombie;
  }

  // ─── Update All Zombies ───
  function update(dt) {
    var player = FPSV4.Engine.getPlayer();
    var playerPos = player.pos;

    for (var i = activeZombies.length - 1; i >= 0; i--) {
      var z = activeZombies[i];

      if (z.dying) {
        // Death animation
        z.deathTimer += dt;
        // Fall over
        var fallProgress = Math.min(z.deathTimer / 0.5, 1);
        z.mesh.rotation.x = fallProgress * (Math.PI / 2);
        z.mesh.position.y = z.pos.y - fallProgress * 0.8;

        // Fade out
        if (z.deathTimer > DEATH_LINGER - 1) {
          var fade = 1 - (z.deathTimer - (DEATH_LINGER - 1));
          z.mesh.traverse(function (child) {
            if (child.isMesh && child.material) {
              child.material.transparent = true;
              child.material.opacity = Math.max(0, fade);
            }
          });
        }

        if (z.deathTimer >= DEATH_LINGER) {
          // Return to pool
          z.active = false;
          z.mesh.visible = false;
          activeZombies.splice(i, 1);
        }
        continue;
      }

      if (!player.alive) continue;

      // Move toward player
      var dx = playerPos.x - z.pos.x;
      var dz = playerPos.z - z.pos.z;
      var dist = Math.sqrt(dx * dx + dz * dz);

      if (dist > 0.1) {
        var nx = dx / dist;
        var nz = dz / dist;

        // Simple separation from other zombies
        for (var j = 0; j < activeZombies.length; j++) {
          if (i === j || activeZombies[j].dying) continue;
          var oz = activeZombies[j];
          var sepX = z.pos.x - oz.pos.x;
          var sepZ = z.pos.z - oz.pos.z;
          var sepDist = Math.sqrt(sepX * sepX + sepZ * sepZ);
          if (sepDist < 0.8 && sepDist > 0.01) {
            nx += (sepX / sepDist) * 0.3;
            nz += (sepZ / sepDist) * 0.3;
          }
        }

        // Normalize movement
        var mLen = Math.sqrt(nx * nx + nz * nz);
        if (mLen > 0) {
          nx /= mLen;
          nz /= mLen;
        }

        var moveSpeed = z.speed * dt;
        z.pos.x += nx * moveSpeed;
        z.pos.z += nz * moveSpeed;

        // Clamp to arena
        var half = FPSV4.Engine.getArenaSize() / 2 - 0.5;
        z.pos.x = Math.max(-half, Math.min(half, z.pos.x));
        z.pos.z = Math.max(-half, Math.min(half, z.pos.z));

        // Face player
        z.mesh.rotation.y = Math.atan2(dx, dz);
      }

      // Shamble animation (sinusoidal wobble)
      z.shambleTimer += dt * z.shambleSpeed;
      var wobble = Math.sin(z.shambleTimer) * 0.06;
      z.mesh.position.set(z.pos.x, z.pos.y + Math.abs(wobble) * 0.1, z.pos.z);
      z.mesh.rotation.z = wobble;

      // Leg animation approximation
      var children = z.mesh.children;
      for (var c = 0; c < children.length; c++) {
        if (children[c].position.y < 0.5 && children[c].position.x !== 0) {
          // Legs: alternate forward/back
          var legDir = children[c].position.x > 0 ? 1 : -1;
          children[c].rotation.x = Math.sin(z.shambleTimer) * 0.3 * legDir;
        }
      }

      // Attack
      if (dist < ATTACK_RANGE) {
        z.attackTimer += dt;
        if (z.attackTimer >= ATTACK_COOLDOWN) {
          z.attackTimer = 0;
          FPSV4.Engine.damagePlayer(z.damage);
          FPSV4.Audio.playZombieAttack();
        }
      } else {
        z.attackTimer = Math.max(0, z.attackTimer - dt * 0.5);
      }

      // Groan sounds
      z.groanTimer -= dt;
      if (z.groanTimer <= 0) {
        z.groanTimer = GROAN_INTERVAL_MIN + Math.random() * (GROAN_INTERVAL_MAX - GROAN_INTERVAL_MIN);
        if (dist < 30) {
          FPSV4.Audio.playZombieGroan();
        }
      }
    }
  }

  // ─── Hit Detection (called by weapons) ───
  function checkHit(raycaster, damage, headshotMult) {
    var result = { hit: false, killed: false, headshot: false, zombie: null };

    var closestDist = Infinity;
    var closestZombie = null;
    var closestHeadshot = false;

    for (var i = 0; i < activeZombies.length; i++) {
      var z = activeZombies[i];
      if (z.dying) continue;

      // Raycast against zombie mesh children
      var intersects = raycaster.intersectObject(z.mesh, true);
      if (intersects.length > 0 && intersects[0].distance < closestDist) {
        closestDist = intersects[0].distance;
        closestZombie = z;
        // Check if headshot (hit the head mesh)
        closestHeadshot = intersects[0].object.name === 'head';
      }
    }

    if (closestZombie) {
      var finalDamage = damage;
      if (closestHeadshot) finalDamage *= headshotMult;

      closestZombie.health -= finalDamage;
      result.hit = true;
      result.headshot = closestHeadshot;
      result.zombie = closestZombie;

      // Show damage number
      if (FPSV4.UI) {
        FPSV4.UI.showDamageNumber(closestZombie.mesh.position, finalDamage, closestHeadshot);
      }

      if (closestZombie.health <= 0) {
        killZombie(closestZombie);
        result.killed = true;
      }
    }

    return result;
  }

  // ─── Kill Zombie ───
  function killZombie(z) {
    z.dying = true;
    z.deathTimer = 0;
    FPSV4.Audio.playZombieDeath();

    if (FPSV4.GameMode) {
      FPSV4.GameMode.onZombieKilled();
    }
  }

  // ─── Clear All ───
  function clearAll() {
    for (var i = 0; i < pool.length; i++) {
      pool[i].active = false;
      pool[i].dying = false;
      pool[i].mesh.visible = false;
    }
    activeZombies = [];
  }

  // ─── Getters ───
  function getActiveCount() {
    var count = 0;
    for (var i = 0; i < activeZombies.length; i++) {
      if (!activeZombies[i].dying) count++;
    }
    return count;
  }

  function getTotalActive() {
    return activeZombies.length;
  }

  return {
    init: init,
    spawn: spawn,
    update: update,
    checkHit: checkHit,
    clearAll: clearAll,
    getActiveCount: getActiveCount,
    getTotalActive: getTotalActive,
    _getActiveList: function () { return activeZombies; }
  };
})();
