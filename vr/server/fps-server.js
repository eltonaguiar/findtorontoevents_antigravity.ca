/**
 * FPS Arena Multiplayer Server
 * Real-time game server for FPS Arena multiplayer matches
 * Uses Socket.io for player synchronization, hit detection, and match management
 * 
 * @module fps-server
 * @version 1.0.0
 */

const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');

// ─── CONSTANTS ───────────────────────────────────────────────────────────────
const MAX_PLAYERS_PER_ROOM = 12;
const MATCH_DURATION = 300; // 5 minutes
const RESPAWN_TIME = 3; // seconds
const TICK_RATE = 20; // state broadcasts per second
const ARENA_SIZE = 80;
const MAX_HEALTH = 100;
const MAX_ARMOR = 100;

const RANKS = [
  { name: 'Recruit',        xp: 0 },
  { name: 'Private',        xp: 100 },
  { name: 'Corporal',       xp: 300 },
  { name: 'Sergeant',       xp: 600 },
  { name: 'Staff Sergeant', xp: 1000 },
  { name: 'Lieutenant',     xp: 1500 },
  { name: 'Captain',        xp: 2200 },
  { name: 'Major',          xp: 3000 },
  { name: 'Colonel',        xp: 4000 },
  { name: 'General',        xp: 5500 },
  { name: 'Commander',      xp: 7500 },
  { name: 'Legend',          xp: 10000 }
];

// Anti-cheat constants
const MAX_SPEED_THRESHOLD = 20; // units per second
const MAX_SHOTS_PER_SECOND = 15;
const POSITION_HISTORY_SIZE = 10;
const SPAWN_PROTECTION_TIME = 3; // seconds

function getRank(xp) {
  let rank = RANKS[0];
  for (let i = RANKS.length - 1; i >= 0; i--) {
    if (xp >= RANKS[i].xp) { rank = RANKS[i]; break; }
  }
  return rank;
}

// Weapon definitions (server-side authoritative damage)
const WEAPONS = {
  pistol:  { damage: 22, range: 40, headshotMult: 2.5 },
  shotgun: { damage: 85, range: 15, headshotMult: 1.5 },
  smg:     { damage: 18, range: 25, headshotMult: 2.0 },
  assault: { damage: 28, range: 50, headshotMult: 2.5 },
  sniper:  { damage: 110, range: 100, headshotMult: 3.0 },
  rocket:  { damage: 150, range: 60, headshotMult: 1.0, splash: 5, splashDamage: 80 }
};

class FPSGameServer {
  constructor(options = {}) {
    this.port = options.port || process.env.FPS_PORT || 3003;
    this.corsOrigin = options.corsOrigin || process.env.CORS_ORIGIN || '*';

    this.app = express();
    this.server = http.createServer(this.app);
    this.io = new Server(this.server, {
      cors: {
        origin: this.corsOrigin,
        methods: ['GET', 'POST']
      },
      transports: ['websocket', 'polling'],
      pingTimeout: 60000,
      pingInterval: 25000
    });

    // Active game rooms: roomId -> Room object
    this.rooms = new Map();
    // Player -> room mapping: socketId -> { roomId, playerId }
    this.playerSockets = new Map();
    // Tick intervals per room
    this.roomTicks = new Map();
  }

  // ─── Room Object Constructor ─────────────────────────────────────────────
  createRoom(roomId, hostId, hostName, options = {}) {
    return {
      id: roomId,
      hostId: hostId,
      name: options.name || `${hostName}'s Arena`,
      mode: options.mode || 'ffa', // ffa = free-for-all, team = team deathmatch
      maxPlayers: Math.min(options.maxPlayers || 8, MAX_PLAYERS_PER_ROOM),
      botCount: options.botCount !== undefined ? options.botCount : 4,
      difficulty: options.difficulty || 'normal',
      matchDuration: options.matchDuration || MATCH_DURATION,
      // State
      state: 'lobby', // lobby, playing, ended
      matchTime: options.matchDuration || MATCH_DURATION,
      createdAt: Date.now(),
      startedAt: null,
      // Players: playerId -> PlayerState
      players: new Map(),
      // Kill feed entries
      killFeed: [],
      // Bot players (simplified AI state tracked server-side)
      bots: []
    };
  }

  // ─── Player State Constructor ────────────────────────────────────────────
  createPlayerState(playerId, socketId, name, userId, totalXP) {
    return {
      id: playerId,
      socketId: socketId,
      name: name,
      fcUserId: userId, // FavCreators user ID
      totalXP: totalXP || 0,
      rank: getRank(totalXP || 0).name,
      isBot: false,
      // Match stats
      kills: 0,
      deaths: 0,
      assists: 0,
      streak: 0,
      bestStreak: 0,
      xpEarned: 0,
      headshots: 0,
      damageDealt: 0,
      // In-game state
      health: MAX_HEALTH,
      armor: 50,
      alive: true,
      respawnTimer: 0,
      weapon: 'assault',
      spawnProtection: SPAWN_PROTECTION_TIME,
      // Position / rotation
      position: { x: 0, y: 1.7, z: 0 },
      rotation: { x: 0, y: 0 },
      // Timestamps
      lastUpdate: Date.now(),
      lastShot: 0,
      joinedAt: Date.now(),
      // Anti-cheat
      positionHistory: [],
      shotTimestamps: [],
      violations: 0,
      // Match history for this session
      lastDamagedBy: null
    };
  }

  // ─── Bot State Constructor ───────────────────────────────────────────────
  createBotState(index) {
    const BOT_NAMES = [
      'ShadowStrike', 'NightHawk', 'IronWolf', 'PhantomAce',
      'RapidFire', 'FrostBite', 'BlazeRunner', 'StormBringer',
      'SilentScope', 'ThunderBolt', 'ViperKing', 'DarkReaper'
    ];
    const spawn = this.getRandomSpawn();
    return {
      id: `bot_${index}_${Date.now()}`,
      name: BOT_NAMES[index % BOT_NAMES.length],
      isBot: true,
      kills: 0,
      deaths: 0,
      streak: 0,
      bestStreak: 0,
      xpEarned: 0,
      health: MAX_HEALTH,
      armor: 50,
      alive: true,
      respawnTimer: 0,
      weapon: ['assault', 'smg', 'shotgun', 'sniper'][Math.floor(Math.random() * 4)],
      position: { x: spawn.x, y: 0, z: spawn.z },
      rotation: { x: 0, y: Math.random() * Math.PI * 2 },
      totalXP: Math.floor(Math.random() * 5000),
      rank: getRank(Math.floor(Math.random() * 5000)).name,
      // AI state
      moveDir: { x: Math.random() - 0.5, z: Math.random() - 0.5 },
      changeDirTimer: 2 + Math.random() * 3,
      fireTimer: 0,
      targetId: null
    };
  }

  getRandomSpawn() {
    const half = ARENA_SIZE / 2 - 5;
    return {
      x: (Math.random() - 0.5) * 2 * half,
      z: (Math.random() - 0.5) * 2 * half
    };
  }

  // ─── INIT ──────────────────────────────────────────────────────────────────
  async init() {
    this.setupMiddleware();
    this.setupRoutes();
    this.setupSocketHandlers();
    console.log('FPS Arena Server initialized');
  }

  setupMiddleware() {
    this.app.use(cors());
    this.app.use(express.json());
  }

  // ─── REST API ROUTES ───────────────────────────────────────────────────────
  setupRoutes() {
    // Health check
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'ok',
        service: 'fps-server',
        timestamp: new Date().toISOString(),
        activeRooms: this.rooms.size,
        activePlayers: this.playerSockets.size
      });
    });

    // List rooms
    this.app.get('/api/fps/rooms', (req, res) => {
      const roomList = [];
      for (const [id, room] of this.rooms) {
        const humanPlayers = Array.from(room.players.values()).filter(p => !p.isBot).length;
        roomList.push({
          id: room.id,
          name: room.name,
          mode: room.mode,
          state: room.state,
          players: humanPlayers,
          maxPlayers: room.maxPlayers,
          botCount: room.bots.length,
          difficulty: room.difficulty,
          hostId: room.hostId,
          matchTime: room.state === 'playing' ? Math.ceil(room.matchTime) : room.matchDuration,
          createdAt: room.createdAt
        });
      }
      res.json({ success: true, rooms: roomList });
    });

    // Get room details
    this.app.get('/api/fps/rooms/:roomId', (req, res) => {
      const room = this.rooms.get(req.params.roomId);
      if (!room) return res.status(404).json({ success: false, error: 'Room not found' });

      const players = [];
      for (const [id, p] of room.players) {
        players.push({
          id: p.id, name: p.name, rank: p.rank, isBot: p.isBot,
          kills: p.kills, deaths: p.deaths, alive: p.alive
        });
      }
      room.bots.forEach(b => {
        players.push({
          id: b.id, name: b.name, rank: b.rank, isBot: true,
          kills: b.kills, deaths: b.deaths, alive: b.alive
        });
      });

      res.json({
        success: true,
        room: {
          id: room.id, name: room.name, mode: room.mode, state: room.state,
          matchTime: Math.ceil(room.matchTime), players, killFeed: room.killFeed.slice(-10)
        }
      });
    });

    // Global leaderboard (across all active rooms)
    this.app.get('/api/fps/leaderboard', (req, res) => {
      const allPlayers = [];
      for (const [, room] of this.rooms) {
        for (const [, p] of room.players) {
          if (!p.isBot) {
            allPlayers.push({
              name: p.name, rank: p.rank, totalXP: p.totalXP,
              kills: p.kills, deaths: p.deaths,
              assists: p.assists || 0, headshots: p.headshots || 0,
              damageDealt: p.damageDealt || 0,
              kd: p.deaths > 0 ? (p.kills / p.deaths).toFixed(2) : p.kills.toString(),
              roomName: room.name
            });
          }
        }
      }
      allPlayers.sort((a, b) => b.kills - a.kills);
      res.json({ success: true, leaderboard: allPlayers.slice(0, 50) });
    });

    // Server stats endpoint
    this.app.get('/api/fps/stats', (req, res) => {
      let totalPlayers = 0;
      let totalBots = 0;
      let activeMatches = 0;

      for (const [, room] of this.rooms) {
        const humanCount = Array.from(room.players.values()).filter(p => !p.isBot).length;
        totalPlayers += humanCount;
        totalBots += room.bots.length;
        if (room.state === 'playing') activeMatches++;
      }

      res.json({
        success: true,
        stats: {
          totalRooms: this.rooms.size,
          activeMatches,
          totalPlayers,
          totalBots,
          uptime: process.uptime(),
          memory: process.memoryUsage().heapUsed
        }
      });
    });

    // Map info endpoint
    this.app.get('/api/fps/maps', (req, res) => {
      res.json({
        success: true,
        maps: [
          {
            id: 'arena_default',
            name: 'Neon Arena',
            description: 'The classic 80x80 arena with multiple levels, cover points, and hazard zones',
            size: ARENA_SIZE,
            maxPlayers: MAX_PLAYERS_PER_ROOM,
            features: ['cover_objects', 'elevated_platforms', 'hazard_zones', 'weapon_pickups']
          }
        ]
      });
    });
  }

  // ─── SOCKET HANDLERS ───────────────────────────────────────────────────────
  setupSocketHandlers() {
    this.io.on('connection', (socket) => {
      console.log(`[FPS] Player connected: ${socket.id}`);

      socket.emit('connected', {
        type: 'connected',
        clientId: socket.id,
        timestamp: Date.now()
      });

      // ── Create Room ────────────────────────────────────────────────────
      socket.on('create_room', (data) => {
        try {
          const { userId, userName, totalXP, options } = data;
          if (!userId || !userName) {
            return socket.emit('error', { code: 'INVALID', message: 'Missing userId or userName' });
          }

          const roomId = `fps_${uuidv4().substring(0, 8)}`;
          const room = this.createRoom(roomId, socket.id, userName, options || {});

          // Create player state
          const playerId = `p_${socket.id}`;
          const spawn = this.getRandomSpawn();
          const player = this.createPlayerState(playerId, socket.id, userName, userId, totalXP);
          player.position = { x: spawn.x, y: 1.7, z: spawn.z };

          room.players.set(playerId, player);
          this.rooms.set(roomId, room);
          this.playerSockets.set(socket.id, { roomId, playerId });

          socket.join(roomId);

          // Spawn bots
          for (let i = 0; i < room.botCount; i++) {
            room.bots.push(this.createBotState(i));
          }

          socket.emit('room_created', {
            type: 'room_created',
            roomId: room.id,
            room: this.serializeRoom(room),
            playerId: playerId,
            spawnPosition: player.position
          });

          console.log(`[FPS] Room created: ${roomId} by ${userName}`);
        } catch (err) {
          console.error('[FPS] Error creating room:', err);
          socket.emit('error', { code: 'CREATE_FAILED', message: 'Failed to create room' });
        }
      });

      // ── Join Room ──────────────────────────────────────────────────────
      socket.on('join_room', (data) => {
        try {
          const { roomId, userId, userName, totalXP } = data;
          const room = this.rooms.get(roomId);
          if (!room) return socket.emit('error', { code: 'NOT_FOUND', message: 'Room not found' });

          const humanCount = Array.from(room.players.values()).filter(p => !p.isBot).length;
          if (humanCount >= room.maxPlayers) {
            return socket.emit('error', { code: 'ROOM_FULL', message: 'Room is full' });
          }

          const playerId = `p_${socket.id}`;
          const spawn = this.getRandomSpawn();
          const player = this.createPlayerState(playerId, socket.id, userName, userId, totalXP);
          player.position = { x: spawn.x, y: 1.7, z: spawn.z };

          room.players.set(playerId, player);
          this.playerSockets.set(socket.id, { roomId, playerId });

          socket.join(roomId);

          // Notify the joiner
          socket.emit('room_joined', {
            type: 'room_joined',
            roomId: room.id,
            room: this.serializeRoom(room),
            playerId: playerId,
            spawnPosition: player.position
          });

          // Notify others in the room
          socket.to(roomId).emit('player_joined', {
            type: 'player_joined',
            player: this.serializePlayer(player)
          });

          console.log(`[FPS] ${userName} joined room ${roomId}`);
        } catch (err) {
          console.error('[FPS] Error joining room:', err);
          socket.emit('error', { code: 'JOIN_FAILED', message: 'Failed to join room' });
        }
      });

      // ── Quick Match (auto-join or create) ──────────────────────────────
      socket.on('quick_match', (data) => {
        try {
          const { userId, userName, totalXP } = data;
          if (!userId || !userName) {
            return socket.emit('error', { code: 'INVALID', message: 'Missing userId or userName' });
          }

          // Find a room in lobby or playing state with space
          let bestRoom = null;
          for (const [, room] of this.rooms) {
            if (room.state === 'ended') continue;
            const humanCount = Array.from(room.players.values()).filter(p => !p.isBot).length;
            if (humanCount < room.maxPlayers) {
              bestRoom = room;
              break;
            }
          }

          if (bestRoom) {
            // Join existing room
            const playerId = `p_${socket.id}`;
            const spawn = this.getRandomSpawn();
            const player = this.createPlayerState(playerId, socket.id, userName, userId, totalXP);
            player.position = { x: spawn.x, y: 1.7, z: spawn.z };

            bestRoom.players.set(playerId, player);
            this.playerSockets.set(socket.id, { roomId: bestRoom.id, playerId });
            socket.join(bestRoom.id);

            socket.emit('room_joined', {
              type: 'room_joined',
              roomId: bestRoom.id,
              room: this.serializeRoom(bestRoom),
              playerId,
              spawnPosition: player.position
            });

            socket.to(bestRoom.id).emit('player_joined', {
              type: 'player_joined',
              player: this.serializePlayer(player)
            });

            // Auto-start if the room is in lobby and has 2+ human players
            const humanCount = Array.from(bestRoom.players.values()).filter(p => !p.isBot).length;
            if (bestRoom.state === 'lobby' && humanCount >= 2) {
              this.startMatch(bestRoom);
            }

            console.log(`[FPS] ${userName} quick-matched into ${bestRoom.id}`);
          } else {
            // Create a new room
            const roomId = `fps_${uuidv4().substring(0, 8)}`;
            const room = this.createRoom(roomId, socket.id, userName, { botCount: 4 });

            const playerId = `p_${socket.id}`;
            const spawn = this.getRandomSpawn();
            const player = this.createPlayerState(playerId, socket.id, userName, userId, totalXP);
            player.position = { x: spawn.x, y: 1.7, z: spawn.z };

            room.players.set(playerId, player);
            this.rooms.set(roomId, room);
            this.playerSockets.set(socket.id, { roomId, playerId });
            socket.join(roomId);

            for (let i = 0; i < room.botCount; i++) {
              room.bots.push(this.createBotState(i));
            }

            socket.emit('room_created', {
              type: 'room_created',
              roomId: room.id,
              room: this.serializeRoom(room),
              playerId,
              spawnPosition: player.position
            });

            console.log(`[FPS] ${userName} created room via quick match: ${roomId}`);
          }
        } catch (err) {
          console.error('[FPS] Quick match error:', err);
          socket.emit('error', { code: 'QUICKMATCH_FAILED', message: 'Quick match failed' });
        }
      });

      // ── Start Match ────────────────────────────────────────────────────
      socket.on('start_match', () => {
        const info = this.playerSockets.get(socket.id);
        if (!info) return;
        const room = this.rooms.get(info.roomId);
        if (!room) return;
        if (room.hostId !== socket.id) {
          return socket.emit('error', { code: 'NOT_HOST', message: 'Only the host can start the match' });
        }
        if (room.state !== 'lobby') return;
        this.startMatch(room);
      });

      // ── Player State Update (position, rotation, weapon) ───────────────
      socket.on('player_update', (data) => {
        const info = this.playerSockets.get(socket.id);
        if (!info) return;
        const room = this.rooms.get(info.roomId);
        if (!room || room.state !== 'playing') return;
        const player = room.players.get(info.playerId);
        if (!player || !player.alive) return;

        const now = Date.now();
        const half = ARENA_SIZE / 2;

        if (data.position) {
          const newX = Math.max(-half, Math.min(half, data.position.x || 0));
          const newY = Math.max(0, Math.min(20, data.position.y || 1.7));
          const newZ = Math.max(-half, Math.min(half, data.position.z || 0));

          // Anti-cheat: Speed validation
          const dt = (now - player.lastUpdate) / 1000;
          if (dt > 0.01) {
            const dx = newX - player.position.x;
            const dz = newZ - player.position.z;
            const speed = Math.sqrt(dx * dx + dz * dz) / dt;
            if (speed > MAX_SPEED_THRESHOLD) {
              player.violations++;
              if (player.violations > 20) {
                console.warn(`[FPS-AC] ${player.name} speed violation: ${speed.toFixed(1)}u/s`);
              }
              // Silently reject extreme teleports but allow small ones
              if (speed > MAX_SPEED_THRESHOLD * 3) return;
            }
          }

          player.position.x = newX;
          player.position.y = newY;
          player.position.z = newZ;

          // Track position history
          player.positionHistory.push({ x: newX, z: newZ, t: now });
          if (player.positionHistory.length > POSITION_HISTORY_SIZE) {
            player.positionHistory.shift();
          }
        }
        if (data.rotation) {
          player.rotation.x = data.rotation.x || 0;
          player.rotation.y = data.rotation.y || 0;
        }
        if (data.weapon && WEAPONS[data.weapon]) {
          player.weapon = data.weapon;
        }
        player.lastUpdate = now;
      });

      // ── Shoot Event (server-authoritative hit detection) ───────────────
      socket.on('shoot', (data) => {
        const info = this.playerSockets.get(socket.id);
        if (!info) return;
        const room = this.rooms.get(info.roomId);
        if (!room || room.state !== 'playing') return;
        const shooter = room.players.get(info.playerId);
        if (!shooter || !shooter.alive) return;

        const weaponDef = WEAPONS[shooter.weapon];
        if (!weaponDef) return;

        // Anti-cheat: Rate limit shooting
        const now = Date.now();
        if (now - shooter.lastShot < 50) return;

        // Anti-cheat: Track shot frequency
        shooter.shotTimestamps.push(now);
        // Keep only last second of shots
        shooter.shotTimestamps = shooter.shotTimestamps.filter(t => now - t < 1000);
        if (shooter.shotTimestamps.length > MAX_SHOTS_PER_SECOND) {
          shooter.violations++;
          console.warn(`[FPS-AC] ${shooter.name} exceeded shot rate: ${shooter.shotTimestamps.length}/s (violations: ${shooter.violations})`);
          if (shooter.violations > 10) {
            socket.emit('error', { code: 'KICKED', message: 'Kicked for suspicious activity' });
            this.handlePlayerLeave(socket);
            return;
          }
          return; // Silently drop the shot
        }

        shooter.lastShot = now;

        // data.targetId = who they claim to have hit
        // data.headshot = boolean
        // data.hitPosition = {x,y,z} where they clicked
        if (!data.targetId) return;

        // Find target (human or bot)
        let target = room.players.get(data.targetId);
        let isTargetBot = false;
        if (!target) {
          target = room.bots.find(b => b.id === data.targetId);
          isTargetBot = true;
        }
        if (!target || !target.alive) return;

        // Validate distance
        const dx = shooter.position.x - target.position.x;
        const dz = shooter.position.z - target.position.z;
        const dist = Math.sqrt(dx * dx + dz * dz);

        // Allow some tolerance on range (client may have slightly different positions)
        if (dist > weaponDef.range * 1.2) return;

        // Calculate damage with distance falloff
        let damage = weaponDef.damage;
        if (data.headshot) damage *= weaponDef.headshotMult;
        const falloff = 1 - Math.max(0, (dist - weaponDef.range * 0.5) / (weaponDef.range * 0.5)) * 0.5;
        damage = Math.round(damage * falloff);

        // Apply damage
        this.applyDamage(room, shooter, target, damage, isTargetBot, data.headshot);

        // Notify the shooter of confirmed hit
        socket.emit('hit_confirmed', {
          targetId: target.id,
          damage: damage,
          headshot: !!data.headshot,
          targetHealth: target.health,
          killed: target.health <= 0
        });
      });

      // ── Rocket Explosion (area damage) ─────────────────────────────────
      socket.on('rocket_explode', (data) => {
        const info = this.playerSockets.get(socket.id);
        if (!info) return;
        const room = this.rooms.get(info.roomId);
        if (!room || room.state !== 'playing') return;
        const shooter = room.players.get(info.playerId);
        if (!shooter) return;

        if (!data.position) return;
        const pos = data.position;
        const splashRadius = 5;
        const splashDamage = 80;

        // Check all players and bots
        const allTargets = [
          ...Array.from(room.players.values()),
          ...room.bots
        ];

        allTargets.forEach(target => {
          if (!target.alive || target.id === shooter.id) return; // don't splash self (for simplicity)
          const dx2 = pos.x - target.position.x;
          const dz2 = pos.z - target.position.z;
          const d = Math.sqrt(dx2 * dx2 + dz2 * dz2);
          if (d < splashRadius) {
            const dmg = Math.round(splashDamage * (1 - d / splashRadius));
            const isBot = target.isBot === true || !!room.bots.find(b => b.id === target.id);
            this.applyDamage(room, shooter, target, dmg, isBot, false);
          }
        });
      });

      // ── Chat Message in Game ───────────────────────────────────────────
      socket.on('game_chat', (data) => {
        const info = this.playerSockets.get(socket.id);
        if (!info) return;
        const room = this.rooms.get(info.roomId);
        if (!room) return;
        const player = room.players.get(info.playerId);
        if (!player) return;

        const msg = (data.message || '').trim().substring(0, 200);
        if (!msg) return;

        this.io.to(info.roomId).emit('game_chat', {
          playerId: player.id,
          playerName: player.name,
          message: msg,
          timestamp: Date.now()
        });
      });

      // ── Leave Room ─────────────────────────────────────────────────────
      socket.on('leave_room', () => {
        this.handlePlayerLeave(socket);
      });

      // ── Disconnect ─────────────────────────────────────────────────────
      socket.on('disconnect', (reason) => {
        console.log(`[FPS] Player disconnected: ${socket.id}, reason: ${reason}`);
        this.handlePlayerLeave(socket);
      });
    });
  }

  // ─── DAMAGE APPLICATION ──────────────────────────────────────────────────
  applyDamage(room, shooter, target, damage, isTargetBot, headshot) {
    // Check spawn protection
    if (!isTargetBot && target.spawnProtection > 0) return;

    // Armor absorbs 60%
    if (target.armor > 0) {
      const armorDmg = Math.min(target.armor, damage * 0.6);
      target.armor = Math.max(0, target.armor - armorDmg);
      damage = Math.round(damage - armorDmg);
    }
    target.health = Math.max(0, target.health - damage);

    // Track damage dealt and assist credits
    if (!shooter.isBot) shooter.damageDealt += damage;
    if (headshot && !shooter.isBot) shooter.headshots++;

    // Track last damaged by for assist credit
    if (!isTargetBot && target.lastDamagedBy !== shooter.id) {
      // If someone else damaged them before, they get an assist
      if (target.lastDamagedBy) {
        const assister = room.players.get(target.lastDamagedBy);
        if (assister && assister.id !== shooter.id) {
          assister.assists++;
          assister.xpEarned += 10;
        }
      }
      target.lastDamagedBy = shooter.id;
    }

    if (target.health <= 0) {
      this.handleKill(room, shooter, target, isTargetBot, headshot);
    }

    // Broadcast damage to room
    this.io.to(room.id).emit('player_damaged', {
      targetId: target.id,
      health: target.health,
      armor: target.armor,
      attackerId: shooter.id,
      damage: damage,
      headshot: !!headshot
    });
  }

  // ─── KILL HANDLING ─────────────────────────────────────────────────────────
  handleKill(room, killer, victim, isVictimBot, headshot) {
    victim.alive = false;
    victim.deaths++;
    victim.streak = 0;

    killer.kills++;
    killer.streak++;
    if (killer.streak > killer.bestStreak) killer.bestStreak = killer.streak;

    // XP gain
    let xpGain = 25;
    if (headshot) xpGain += 10;
    if (killer.streak >= 3) xpGain += 10;
    if (killer.streak >= 5) xpGain += 20;
    if (!isVictimBot) xpGain *= 2; // Double XP for PvP kills
    killer.xpEarned += xpGain;

    // Kill feed entry
    const feedEntry = {
      killerId: killer.id,
      killerName: killer.name,
      victimId: victim.id,
      victimName: victim.name,
      weapon: killer.weapon,
      headshot: !!headshot,
      pvp: !victim.isBot && !killer.isBot,
      timestamp: Date.now()
    };
    room.killFeed.push(feedEntry);
    if (room.killFeed.length > 50) room.killFeed.shift();

    // Broadcast kill
    this.io.to(room.id).emit('player_killed', {
      ...feedEntry,
      killerStreak: killer.streak,
      xpGain: xpGain
    });

    // Schedule respawn
    const respawnDelay = RESPAWN_TIME * 1000;
    setTimeout(() => {
      if (!this.rooms.has(room.id)) return;
      if (room.state !== 'playing') return;
      const spawn = this.getRandomSpawn();
      victim.position = { x: spawn.x, y: isVictimBot ? 0 : 1.7, z: spawn.z };
      victim.health = MAX_HEALTH;
      victim.armor = 50;
      victim.alive = true;
      victim.lastDamagedBy = null;
      if (!isVictimBot) victim.spawnProtection = SPAWN_PROTECTION_TIME;

      this.io.to(room.id).emit('player_respawned', {
        playerId: victim.id,
        position: victim.position,
        health: victim.health,
        armor: victim.armor,
        spawnProtection: SPAWN_PROTECTION_TIME
      });
    }, respawnDelay);
  }

  // ─── MATCH MANAGEMENT ──────────────────────────────────────────────────────
  startMatch(room) {
    room.state = 'playing';
    room.startedAt = Date.now();
    room.matchTime = room.matchDuration;

    // Reset all player stats
    for (const [, p] of room.players) {
      p.kills = 0; p.deaths = 0; p.streak = 0; p.bestStreak = 0; p.xpEarned = 0;
      p.health = MAX_HEALTH; p.armor = 50; p.alive = true;
      const spawn = this.getRandomSpawn();
      p.position = { x: spawn.x, y: 1.7, z: spawn.z };
    }
    room.bots.forEach(b => {
      b.kills = 0; b.deaths = 0; b.streak = 0; b.bestStreak = 0;
      b.health = MAX_HEALTH; b.armor = 50; b.alive = true;
      const spawn = this.getRandomSpawn();
      b.position = { x: spawn.x, y: 0, z: spawn.z };
    });

    room.killFeed = [];

    this.io.to(room.id).emit('match_started', {
      matchDuration: room.matchDuration,
      players: this.serializeAllPlayers(room),
      timestamp: Date.now()
    });

    // Start game tick
    this.startRoomTick(room);

    console.log(`[FPS] Match started in room ${room.id}`);
  }

  startRoomTick(room) {
    // Stop existing tick
    if (this.roomTicks.has(room.id)) {
      clearInterval(this.roomTicks.get(room.id));
    }

    const interval = 1000 / TICK_RATE;
    let lastTime = Date.now();

    const tick = () => {
      if (!this.rooms.has(room.id) || room.state !== 'playing') {
        clearInterval(this.roomTicks.get(room.id));
        this.roomTicks.delete(room.id);
        return;
      }

      const now = Date.now();
      const dt = (now - lastTime) / 1000;
      lastTime = now;

      // Update match timer
      room.matchTime -= dt;
      if (room.matchTime <= 0) {
        this.endMatch(room);
        return;
      }

      // Update spawn protection timers
      for (const [, p] of room.players) {
        if (p.spawnProtection > 0) p.spawnProtection -= dt;
      }

      // Update bots (simplified server-side AI)
      this.updateBots(room, dt);

      // Broadcast game state to all players
      this.broadcastState(room);
    };

    const intervalId = setInterval(tick, interval);
    this.roomTicks.set(room.id, intervalId);
  }

  updateBots(room, dt) {
    const humanPlayers = Array.from(room.players.values()).filter(p => p.alive);

    room.bots.forEach(bot => {
      if (!bot.alive) return;

      // Simple AI: move around and shoot at nearest player
      bot.changeDirTimer -= dt;
      if (bot.changeDirTimer <= 0) {
        bot.changeDirTimer = 1.5 + Math.random() * 3;
        // Pick direction toward a player or random
        if (humanPlayers.length > 0 && Math.random() < 0.6) {
          const target = humanPlayers[Math.floor(Math.random() * humanPlayers.length)];
          const dx = target.position.x - bot.position.x;
          const dz = target.position.z - bot.position.z;
          const len = Math.sqrt(dx * dx + dz * dz) || 1;
          bot.moveDir = { x: dx / len, z: dz / len };
          bot.targetId = target.id;
        } else {
          bot.moveDir = { x: Math.random() - 0.5, z: Math.random() - 0.5 };
          bot.targetId = null;
        }
      }

      // Move
      const speed = 4 * dt;
      bot.position.x += bot.moveDir.x * speed;
      bot.position.z += bot.moveDir.z * speed;

      // Clamp to arena
      const half = ARENA_SIZE / 2 - 1;
      bot.position.x = Math.max(-half, Math.min(half, bot.position.x));
      bot.position.z = Math.max(-half, Math.min(half, bot.position.z));

      // Face movement direction
      bot.rotation.y = Math.atan2(bot.moveDir.x, bot.moveDir.z);

      // Fire at players
      bot.fireTimer -= dt;
      if (bot.fireTimer <= 0 && humanPlayers.length > 0) {
        bot.fireTimer = 0.8 + Math.random() * 1.5;

        // Find nearest visible player
        let nearest = null;
        let nearestDist = Infinity;
        humanPlayers.forEach(p => {
          const dx2 = p.position.x - bot.position.x;
          const dz2 = p.position.z - bot.position.z;
          const d = Math.sqrt(dx2 * dx2 + dz2 * dz2);
          if (d < nearestDist && d < 35) {
            nearestDist = d;
            nearest = p;
          }
        });

        if (nearest) {
          // Accuracy based on difficulty
          const accMap = { easy: 0.15, normal: 0.30, hard: 0.50, insane: 0.70 };
          const accuracy = accMap[room.difficulty] || 0.3;
          if (Math.random() < accuracy) {
            const dmg = 8 + Math.floor(Math.random() * 12);
            this.applyDamage(room, bot, nearest, dmg, false, false);
          }
        }
      }
    });
  }

  broadcastState(room) {
    // Collect all player states for broadcast
    const players = [];
    for (const [, p] of room.players) {
      players.push({
        id: p.id, name: p.name, rank: p.rank, isBot: false,
        position: p.position, rotation: p.rotation,
        health: p.health, armor: p.armor, alive: p.alive,
        weapon: p.weapon, kills: p.kills, deaths: p.deaths, streak: p.streak
      });
    }
    room.bots.forEach(b => {
      players.push({
        id: b.id, name: b.name, rank: b.rank, isBot: true,
        position: b.position, rotation: b.rotation,
        health: b.health, armor: b.armor, alive: b.alive,
        weapon: b.weapon, kills: b.kills, deaths: b.deaths, streak: b.streak
      });
    });

    this.io.to(room.id).emit('game_state', {
      matchTime: Math.ceil(room.matchTime),
      players: players,
      timestamp: Date.now()
    });
  }

  endMatch(room) {
    room.state = 'ended';

    // Stop tick
    if (this.roomTicks.has(room.id)) {
      clearInterval(this.roomTicks.get(room.id));
      this.roomTicks.delete(room.id);
    }

    // Compile final scoreboard with detailed stats
    const scoreboard = [];
    for (const [, p] of room.players) {
      scoreboard.push({
        id: p.id, name: p.name, rank: p.rank, isBot: false,
        kills: p.kills, deaths: p.deaths, assists: p.assists || 0,
        headshots: p.headshots || 0, damageDealt: p.damageDealt || 0,
        bestStreak: p.bestStreak, xpEarned: p.xpEarned,
        kd: p.deaths > 0 ? (p.kills / p.deaths).toFixed(2) : p.kills.toString(),
        score: p.kills * 100 + (p.assists || 0) * 25 + (p.headshots || 0) * 50 + p.xpEarned
      });
    }
    room.bots.forEach(b => {
      scoreboard.push({
        id: b.id, name: b.name, rank: b.rank, isBot: true,
        kills: b.kills, deaths: b.deaths, assists: 0,
        headshots: 0, damageDealt: 0,
        bestStreak: b.bestStreak, xpEarned: b.xpEarned || 0,
        kd: b.deaths > 0 ? (b.kills / b.deaths).toFixed(2) : b.kills.toString(),
        score: b.kills * 100
      });
    });
    scoreboard.sort((a, b) => b.score - a.score);

    this.io.to(room.id).emit('match_ended', {
      scoreboard: scoreboard,
      killFeed: room.killFeed.slice(-20),
      matchDuration: room.matchDuration,
      timestamp: Date.now()
    });

    console.log(`[FPS] Match ended in room ${room.id}`);

    // Clean up room after 30 seconds
    setTimeout(() => {
      if (this.rooms.has(room.id) && room.state === 'ended') {
        // Remove remaining players
        for (const [, p] of room.players) {
          const s = this.io.sockets.sockets.get(p.socketId);
          if (s) {
            s.leave(room.id);
            this.playerSockets.delete(p.socketId);
          }
        }
        this.rooms.delete(room.id);
        console.log(`[FPS] Room cleaned up: ${room.id}`);
      }
    }, 30000);
  }

  // ─── PLAYER LEAVE ─────────────────────────────────────────────────────────
  handlePlayerLeave(socket) {
    const info = this.playerSockets.get(socket.id);
    if (!info) return;

    const room = this.rooms.get(info.roomId);
    if (!room) {
      this.playerSockets.delete(socket.id);
      return;
    }

    const player = room.players.get(info.playerId);

    // Remove player from room
    room.players.delete(info.playerId);
    this.playerSockets.delete(socket.id);
    socket.leave(info.roomId);

    // Notify others
    this.io.to(info.roomId).emit('player_left', {
      playerId: info.playerId,
      playerName: player ? player.name : 'Unknown',
      timestamp: Date.now()
    });

    console.log(`[FPS] Player left room ${info.roomId}: ${player ? player.name : 'unknown'}`);

    // If room is empty (no human players), clean it up
    const humanCount = Array.from(room.players.values()).filter(p => !p.isBot).length;
    if (humanCount === 0) {
      if (this.roomTicks.has(room.id)) {
        clearInterval(this.roomTicks.get(room.id));
        this.roomTicks.delete(room.id);
      }
      this.rooms.delete(room.id);
      console.log(`[FPS] Room removed (empty): ${room.id}`);
    } else if (room.hostId === socket.id) {
      // Transfer host to next player
      const nextPlayer = Array.from(room.players.values()).find(p => !p.isBot);
      if (nextPlayer) {
        room.hostId = nextPlayer.socketId;
        this.io.to(info.roomId).emit('host_changed', {
          newHostId: nextPlayer.id,
          newHostName: nextPlayer.name
        });
      }
    }
  }

  // ─── SERIALIZERS ──────────────────────────────────────────────────────────
  serializeRoom(room) {
    return {
      id: room.id,
      name: room.name,
      mode: room.mode,
      state: room.state,
      maxPlayers: room.maxPlayers,
      matchDuration: room.matchDuration,
      difficulty: room.difficulty,
      botCount: room.bots.length,
      hostId: room.hostId,
      players: this.serializeAllPlayers(room)
    };
  }

  serializeAllPlayers(room) {
    const result = [];
    for (const [, p] of room.players) {
      result.push(this.serializePlayer(p));
    }
    room.bots.forEach(b => {
      result.push({
        id: b.id, name: b.name, rank: b.rank, isBot: true,
        kills: b.kills, deaths: b.deaths, health: b.health, armor: b.armor,
        alive: b.alive, position: b.position, rotation: b.rotation, weapon: b.weapon
      });
    });
    return result;
  }

  serializePlayer(p) {
    return {
      id: p.id, name: p.name, rank: p.rank, isBot: p.isBot || false,
      fcUserId: p.fcUserId,
      kills: p.kills, deaths: p.deaths, health: p.health, armor: p.armor,
      alive: p.alive, position: p.position, rotation: p.rotation, weapon: p.weapon,
      totalXP: p.totalXP
    };
  }

  // ─── SERVER LIFECYCLE ─────────────────────────────────────────────────────
  async start() {
    await this.init();
    this.server.listen(this.port, () => {
      console.log(`FPS Arena Server running on port ${this.port}`);
      console.log(`WebSocket endpoint: ws://localhost:${this.port}`);
      console.log(`REST API: http://localhost:${this.port}/api/fps`);
    });
  }

  async stop() {
    // Stop all room ticks
    for (const [roomId, intervalId] of this.roomTicks) {
      clearInterval(intervalId);
    }
    this.roomTicks.clear();

    return new Promise((resolve) => {
      this.io.close(() => { console.log('FPS Socket.io closed'); });
      this.server.close(() => {
        console.log('FPS HTTP server closed');
        resolve();
      });
    });
  }
}

// Start if run directly
if (require.main === module) {
  const server = new FPSGameServer({
    port: process.env.FPS_PORT || 3003,
    corsOrigin: process.env.CORS_ORIGIN || '*'
  });

  server.start().catch(err => {
    console.error('Failed to start FPS server:', err);
    process.exit(1);
  });

  process.on('SIGTERM', async () => {
    console.log('SIGTERM received, shutting down FPS server');
    await server.stop();
    process.exit(0);
  });
  process.on('SIGINT', async () => {
    console.log('SIGINT received, shutting down FPS server');
    await server.stop();
    process.exit(0);
  });
}

module.exports = FPSGameServer;
