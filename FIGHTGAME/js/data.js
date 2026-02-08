/* ============================================================
   SHADOW ARENA — Game Data & Configuration
   Copyright-safe original fighting game
   ============================================================ */

// === GAME CONFIGURATION ===
var CONFIG = {
    CANVAS_WIDTH: 1280,
    CANVAS_HEIGHT: 720,
    GROUND_Y: 620,
    STAGE_LEFT: 60,
    STAGE_RIGHT: 1220,
    GRAVITY: 2200,
    MAX_FALL_SPEED: 1200,
    ROUND_TIME: 99,
    ROUNDS_TO_WIN: 2,
    COMBO_WINDOW: 600,        // ms to chain next hit
    HITSTOP_DURATION: 80,     // ms of freeze on hit
    SCREEN_SHAKE_DECAY: 0.9,
    BLOCK_DAMAGE_MULT: 0.15,
    SPECIAL_METER_MAX: 100,
    METER_GAIN_DEAL: 8,
    METER_GAIN_TAKE: 12,
    DASH_SPEED: 600,
    DASH_DURATION: 180,
    WALK_SPEED: 280,
    JUMP_FORCE: -750,
    DOUBLE_JUMP_FORCE: -650,
    CROUCH_HEIGHT_MULT: 0.6,
    KNOCKBACK_LIGHT: 200,
    KNOCKBACK_HEAVY: 400,
    KNOCKBACK_SPECIAL: 500,
    LAUNCH_FORCE: -500,
    AI_REACTION_FRAMES: { easy: 30, medium: 18, hard: 8, insane: 3 },
    FPS: 60
};

// === CHARACTERS ===
var CHARACTERS = [
    {
        id: 'kai',
        name: 'Kai',
        title: 'Shadow Striker',
        description: 'A swift warrior who strikes from the shadows with lethal precision.',
        lore: 'Trained in the ancient art of shadow combat, Kai vanished from his dojo and now fights to reclaim his honor.',
        stats: { speed: 8, power: 6, defense: 5, range: 6, special: 7 },
        colors: {
            skin: '#c8956c',
            hair: '#1a1a2e',
            primary: '#2d1b69',
            secondary: '#1a1a2e',
            accent: '#8e44ad',
            eye: '#e74c3c',
            glow: '#9b59b6'
        },
        body: { headR: 15, torsoW: 28, torsoH: 30, armW: 9, armLen: 26, legW: 10, legLen: 28, shoulderW: 32 },
        walkSpeed: 1.0,
        jumpForce: 1.0,
        weight: 1.0,
        specialName: 'Shadow Dash',
        specialDesc: 'Teleports behind the opponent and delivers a devastating strike.',
        specialDamage: 22,
        specialStartup: 8,
        specialRecovery: 20,
        hasDoubleJump: true,
        uniqueFeature: 'scarf'
    },
    {
        id: 'rook',
        name: 'Rook',
        title: 'Iron Titan',
        description: 'An unstoppable armored juggernaut built for raw power.',
        lore: 'A former blacksmith who forged his own unbreakable armor, Rook fights to protect the weak.',
        stats: { speed: 3, power: 10, defense: 9, range: 5, special: 6 },
        colors: {
            skin: '#a0785a',
            hair: '#4a3728',
            primary: '#5d6d7e',
            secondary: '#2c3e50',
            accent: '#f39c12',
            eye: '#f1c40f',
            glow: '#e67e22'
        },
        body: { headR: 16, torsoW: 38, torsoH: 34, armW: 13, armLen: 24, legW: 14, legLen: 26, shoulderW: 42 },
        walkSpeed: 0.65,
        jumpForce: 0.8,
        weight: 1.4,
        specialName: 'Titan Smash',
        specialDesc: 'Leaps into the air and crashes down with earth-shattering force.',
        specialDamage: 30,
        specialStartup: 16,
        specialRecovery: 28,
        hasDoubleJump: false,
        uniqueFeature: 'armor'
    },
    {
        id: 'zara',
        name: 'Zara',
        title: 'Storm Dancer',
        description: 'A lightning-fast acrobat who overwhelms foes with blinding speed.',
        lore: 'Born during a thunderstorm, Zara channels the fury of the skies through her devastating kicks.',
        stats: { speed: 10, power: 4, defense: 4, range: 5, special: 8 },
        colors: {
            skin: '#8d5524',
            hair: '#e8e8e8',
            primary: '#1abc9c',
            secondary: '#16a085',
            accent: '#00ffcc',
            eye: '#00ffcc',
            glow: '#1abc9c'
        },
        body: { headR: 13, torsoW: 24, torsoH: 28, armW: 8, armLen: 24, legW: 9, legLen: 30, shoulderW: 28 },
        walkSpeed: 1.35,
        jumpForce: 1.15,
        weight: 0.75,
        specialName: 'Lightning Barrage',
        specialDesc: 'Unleashes a rapid flurry of electrified strikes.',
        specialDamage: 18,
        specialStartup: 4,
        specialRecovery: 14,
        hasDoubleJump: true,
        uniqueFeature: 'lightning'
    },
    {
        id: 'vex',
        name: 'Vex',
        title: 'Venom Fang',
        description: 'A cunning assassin whose toxic attacks drain the life from opponents.',
        lore: 'An exile from a forbidden alchemist order, Vex weaponized ancient poisons into a deadly fighting style.',
        stats: { speed: 7, power: 5, defense: 4, range: 8, special: 9 },
        colors: {
            skin: '#b8b8b8',
            hair: '#2ecc71',
            primary: '#27ae60',
            secondary: '#1a5032',
            accent: '#00ff88',
            eye: '#00ff44',
            glow: '#2ecc71'
        },
        body: { headR: 14, torsoW: 26, torsoH: 30, armW: 9, armLen: 27, legW: 9, legLen: 28, shoulderW: 30 },
        walkSpeed: 1.1,
        jumpForce: 1.0,
        weight: 0.9,
        specialName: 'Toxic Cloud',
        specialDesc: 'Releases a poisonous mist that damages over time.',
        specialDamage: 15,
        specialStartup: 10,
        specialRecovery: 16,
        hasDoubleJump: false,
        uniqueFeature: 'poison',
        poisonDPS: 3,
        poisonDuration: 3000
    },
    {
        id: 'freya',
        name: 'Freya',
        title: 'Frost Sentinel',
        description: 'A disciplined guardian who freezes opponents with icy precision.',
        lore: 'Keeper of the Frozen Gate, Freya trained for decades in subzero caves to master ice combat.',
        stats: { speed: 5, power: 7, defense: 8, range: 7, special: 7 },
        colors: {
            skin: '#f0d9c0',
            hair: '#aed6f1',
            primary: '#2980b9',
            secondary: '#1a5276',
            accent: '#85c1e9',
            eye: '#3498db',
            glow: '#5dade2'
        },
        body: { headR: 14, torsoW: 26, torsoH: 30, armW: 9, armLen: 26, legW: 10, legLen: 28, shoulderW: 30 },
        walkSpeed: 0.85,
        jumpForce: 0.95,
        weight: 1.0,
        specialName: 'Glacial Spike',
        specialDesc: 'Summons a massive ice spike from the ground.',
        specialDamage: 24,
        specialStartup: 12,
        specialRecovery: 22,
        hasDoubleJump: false,
        uniqueFeature: 'ice',
        freezeDuration: 800
    },
    {
        id: 'drake',
        name: 'Drake',
        title: 'Inferno',
        description: 'A berserker fueled by fire who grows stronger the more damage he takes.',
        lore: 'Cursed by a fire spirit, Drake must fight to keep the flames within from consuming him.',
        stats: { speed: 7, power: 8, defense: 3, range: 6, special: 8 },
        colors: {
            skin: '#d4a574',
            hair: '#e74c3c',
            primary: '#c0392b',
            secondary: '#7b241c',
            accent: '#ff6600',
            eye: '#ff4400',
            glow: '#e74c3c'
        },
        body: { headR: 15, torsoW: 30, torsoH: 32, armW: 11, armLen: 26, legW: 11, legLen: 28, shoulderW: 34 },
        walkSpeed: 1.1,
        jumpForce: 1.0,
        weight: 1.1,
        specialName: 'Inferno Rush',
        specialDesc: 'Engulfs himself in flame and charges forward.',
        specialDamage: 26,
        specialStartup: 6,
        specialRecovery: 18,
        hasDoubleJump: false,
        uniqueFeature: 'fire',
        rageMode: true,
        rageDamageBonus: 0.3
    }
];

// === WEAPONS ===
var WEAPONS = [
    {
        id: 'katana',
        name: 'Katana',
        description: 'A balanced blade with excellent speed and reach.',
        stats: { speed: 7, damage: 7, range: 7 },
        lightDamage: 8,
        heavyDamage: 16,
        lightStartup: 4,
        heavyStartup: 10,
        lightRecovery: 8,
        heavyRecovery: 16,
        lightRange: 70,
        heavyRange: 85,
        color: '#c0c0c0',
        glowColor: '#e8e8e8',
        drawType: 'blade',
        length: 50,
        width: 4
    },
    {
        id: 'warhammer',
        name: 'War Hammer',
        description: 'Devastatingly powerful but slow to swing.',
        stats: { speed: 3, damage: 10, range: 6 },
        lightDamage: 12,
        heavyDamage: 25,
        lightStartup: 8,
        heavyStartup: 18,
        lightRecovery: 14,
        heavyRecovery: 24,
        lightRange: 60,
        heavyRange: 75,
        color: '#8b7355',
        glowColor: '#d4a574',
        drawType: 'hammer',
        length: 55,
        width: 8
    },
    {
        id: 'daggers',
        name: 'Dual Daggers',
        description: 'Blazing fast with rapid combos but short reach.',
        stats: { speed: 10, damage: 4, range: 3 },
        lightDamage: 5,
        heavyDamage: 10,
        lightStartup: 2,
        heavyStartup: 6,
        lightRecovery: 5,
        heavyRecovery: 10,
        lightRange: 45,
        heavyRange: 55,
        color: '#a0a0a0',
        glowColor: '#d0d0d0',
        drawType: 'daggers',
        length: 25,
        width: 3
    },
    {
        id: 'chainwhip',
        name: 'Chain Whip',
        description: 'Outstanding range to control space from a distance.',
        stats: { speed: 5, damage: 6, range: 10 },
        lightDamage: 7,
        heavyDamage: 14,
        lightStartup: 6,
        heavyStartup: 12,
        lightRecovery: 10,
        heavyRecovery: 18,
        lightRange: 100,
        heavyRange: 130,
        color: '#8a8a8a',
        glowColor: '#b0b0b0',
        drawType: 'chain',
        length: 70,
        width: 3
    },
    {
        id: 'battleaxe',
        name: 'Battle Axe',
        description: 'Heavy cleaving power with good range.',
        stats: { speed: 4, damage: 9, range: 7 },
        lightDamage: 10,
        heavyDamage: 22,
        lightStartup: 7,
        heavyStartup: 14,
        lightRecovery: 12,
        heavyRecovery: 20,
        lightRange: 75,
        heavyRange: 90,
        color: '#6d4c41',
        glowColor: '#a1887f',
        drawType: 'axe',
        length: 55,
        width: 6
    },
    {
        id: 'staff',
        name: 'Bo Staff',
        description: 'Versatile weapon with excellent reach and control.',
        stats: { speed: 6, damage: 5, range: 9 },
        lightDamage: 6,
        heavyDamage: 13,
        lightStartup: 5,
        heavyStartup: 10,
        lightRecovery: 8,
        heavyRecovery: 14,
        lightRange: 90,
        heavyRange: 110,
        color: '#8d6e63',
        glowColor: '#bcaaa4',
        drawType: 'staff',
        length: 65,
        width: 5
    }
];

// === RANKS ===
var RANKS = [
    { name: 'Novice',       minXP: 0,     icon: '🥉', color: '#cd7f32', tier: 1 },
    { name: 'Fighter',      minXP: 500,   icon: '🥈', color: '#c0c0c0', tier: 2 },
    { name: 'Warrior',      minXP: 1500,  icon: '🥇', color: '#ffd700', tier: 3 },
    { name: 'Champion',     minXP: 3500,  icon: '💎', color: '#00bcd4', tier: 4 },
    { name: 'Master',       minXP: 7000,  icon: '🔷', color: '#2196f3', tier: 5 },
    { name: 'Grandmaster',  minXP: 12000, icon: '❤️‍🔥', color: '#e91e63', tier: 6 },
    { name: 'Legend',        minXP: 20000, icon: '👑', color: '#ff9800', tier: 7 },
    { name: 'Immortal',     minXP: 35000, icon: '⚡', color: '#9c27b0', tier: 8 }
];

// === STAGES ===
var STAGES = [
    {
        id: 'dojo',
        name: 'Shadow Dojo',
        groundColor: '#3e2723',
        wallColor: '#1a1a1a',
        skyColors: ['#0d0d0d', '#1a1a2e'],
        accentColor: '#4a0e0e',
        particles: 'dust',
        features: 'lanterns'
    },
    {
        id: 'arena',
        name: 'Grand Arena',
        groundColor: '#37474f',
        wallColor: '#263238',
        skyColors: ['#1a237e', '#0d47a1'],
        accentColor: '#ffd600',
        particles: 'sparks',
        features: 'crowd'
    },
    {
        id: 'rooftop',
        name: 'Neon Rooftop',
        groundColor: '#212121',
        wallColor: '#1b1b2f',
        skyColors: ['#0f0c29', '#302b63'],
        accentColor: '#ff0066',
        particles: 'rain',
        features: 'cityscape'
    },
    {
        id: 'temple',
        name: 'Ancient Temple',
        groundColor: '#33291a',
        wallColor: '#1a1200',
        skyColors: ['#1a0a00', '#2d1600'],
        accentColor: '#ff6f00',
        particles: 'embers',
        features: 'torches'
    }
];

// === DIFFICULTY PRESETS ===
var DIFFICULTY = {
    easy:   { name: 'Rookie',    reactionFrames: 30, blockChance: 0.15, comboChance: 0.1,  aggressiveness: 0.3, adaptRate: 0,    xpMult: 1.0, color: '#4caf50' },
    medium: { name: 'Warrior',   reactionFrames: 18, blockChance: 0.4,  comboChance: 0.35, aggressiveness: 0.5, adaptRate: 0.1,  xpMult: 1.5, color: '#ff9800' },
    hard:   { name: 'Champion',  reactionFrames: 8,  blockChance: 0.65, comboChance: 0.6,  aggressiveness: 0.65,adaptRate: 0.25, xpMult: 2.5, color: '#f44336' },
    insane: { name: 'Legendary', reactionFrames: 3,  blockChance: 0.85, comboChance: 0.8,  aggressiveness: 0.8, adaptRate: 0.5,  xpMult: 4.0, color: '#9c27b0' }
};

// === GAMEPAD MAPPING (Xbox Layout / Standard) ===
var GAMEPAD_MAP = {
    // Buttons
    LIGHT_ATTACK: 0,    // A
    HEAVY_ATTACK: 1,    // B
    SPECIAL: 2,         // X
    GRAB: 3,            // Y
    BLOCK: 4,           // LB
    DASH: 5,            // RB
    TAUNT: 6,           // LT (as button)
    SUPER: 7,           // RT (as button)
    BACK: 8,            // Back/Select
    START: 9,           // Start
    // Axes
    MOVE_X: 0,          // Left stick X
    MOVE_Y: 1,          // Left stick Y
    // D-pad (buttons 12-15)
    DPAD_UP: 12,
    DPAD_DOWN: 13,
    DPAD_LEFT: 14,
    DPAD_RIGHT: 15,
    // Deadzone
    STICK_DEADZONE: 0.25
};

// === KEYBOARD MAPPINGS ===
var KEYBOARD_P1 = {
    left: 'KeyA',
    right: 'KeyD',
    up: 'KeyW',
    down: 'KeyS',
    lightAttack: 'KeyJ',
    heavyAttack: 'KeyK',
    special: 'KeyL',
    grab: 'KeyU',
    block: 'KeyI',
    dash: 'KeyO',
    taunt: 'KeyH'
};

var KEYBOARD_P2 = {
    left: 'ArrowLeft',
    right: 'ArrowRight',
    up: 'ArrowUp',
    down: 'ArrowDown',
    lightAttack: 'Numpad1',
    heavyAttack: 'Numpad2',
    special: 'Numpad3',
    grab: 'Numpad5',
    block: 'Numpad4',
    dash: 'Numpad6',
    taunt: 'Numpad0'
};

// === XP FORMULA ===
function calculateXP(won, difficulty, healthRemaining, combosLanded, perfectRound, timeBonus) {
    var base = won ? 100 : 25;
    var diffMult = DIFFICULTY[difficulty] ? DIFFICULTY[difficulty].xpMult : 1;
    var healthBonus = won ? Math.floor(healthRemaining * 2) : 0;
    var comboBonus = combosLanded * 10;
    var perfect = perfectRound ? 50 : 0;
    var time = timeBonus > 0 ? Math.floor(timeBonus) : 0;
    return Math.floor((base + healthBonus + comboBonus + perfect + time) * diffMult);
}

// === RANK LOOKUP ===
function getRank(xp) {
    var rank = RANKS[0];
    for (var i = RANKS.length - 1; i >= 0; i--) {
        if (xp >= RANKS[i].minXP) {
            rank = RANKS[i];
            break;
        }
    }
    var nextRank = null;
    for (var j = 0; j < RANKS.length; j++) {
        if (RANKS[j].minXP > xp) {
            nextRank = RANKS[j];
            break;
        }
    }
    return { current: rank, next: nextRank, xp: xp };
}

// === UTILITY FUNCTIONS ===
function lerp(a, b, t) {
    return a + (b - a) * t;
}

function clamp(val, min, max) {
    return Math.max(min, Math.min(max, val));
}

function randomRange(min, max) {
    return Math.random() * (max - min) + min;
}

function easeOutQuad(t) {
    return t * (2 - t);
}

function easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

function degToRad(deg) {
    return deg * Math.PI / 180;
}
