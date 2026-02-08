/* ============================================================
   SHADOW ARENA — Game Engine
   Fighter class, Rendering, Physics, AI, Game Loop
   ============================================================ */

// === INPUT MANAGER ===
function InputManager() {
    this.keys = {};
    this.prevKeys = {};
    this.gamepads = [];
    this.prevGamepadButtons = {};
    var self = this;

    document.addEventListener('keydown', function(e) {
        self.keys[e.code] = true;
        if (['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Space','Numpad1','Numpad2','Numpad3','Numpad4','Numpad5','Numpad6','Numpad0'].indexOf(e.code) !== -1) {
            e.preventDefault();
        }
    });
    document.addEventListener('keyup', function(e) {
        self.keys[e.code] = false;
    });

    window.addEventListener('gamepadconnected', function(e) {
        console.log('Gamepad connected: ' + e.gamepad.id);
    });
    window.addEventListener('gamepaddisconnected', function(e) {
        console.log('Gamepad disconnected: ' + e.gamepad.id);
    });
}

InputManager.prototype.update = function() {
    // Poll gamepads (must happen at start of frame so button states are current)
    var rawPads = navigator.getGamepads ? navigator.getGamepads() : [];
    this.gamepads = [];
    for (var i = 0; i < rawPads.length; i++) {
        if (rawPads[i]) this.gamepads.push(rawPads[i]);
    }
};

// Called at END of frame — snapshots current state into prev for next frame's just-pressed detection.
// If prev is updated at the start of the frame (before input is read), async keydown events
// that fired between frames cause keys and prevKeys to be identical, breaking isKeyJustPressed.
InputManager.prototype.postUpdate = function() {
    var k;
    for (k in this.keys) {
        this.prevKeys[k] = this.keys[k];
    }
    for (var g = 0; g < this.gamepads.length; g++) {
        if (!this.prevGamepadButtons[g]) this.prevGamepadButtons[g] = {};
        var pad = this.gamepads[g];
        if (pad) {
            for (var b = 0; b < pad.buttons.length; b++) {
                this.prevGamepadButtons[g][b] = pad.buttons[b].pressed;
            }
        }
    }
};

InputManager.prototype.isKeyDown = function(code) {
    return !!this.keys[code];
};

InputManager.prototype.isKeyJustPressed = function(code) {
    return !!this.keys[code] && !this.prevKeys[code];
};

InputManager.prototype.getGamepad = function(index) {
    return this.gamepads[index] || null;
};

InputManager.prototype.isGamepadButtonDown = function(padIndex, btnIndex) {
    var pad = this.gamepads[padIndex];
    if (!pad || !pad.buttons[btnIndex]) return false;
    return pad.buttons[btnIndex].pressed;
};

InputManager.prototype.isGamepadButtonJustPressed = function(padIndex, btnIndex) {
    var pad = this.gamepads[padIndex];
    if (!pad || !pad.buttons[btnIndex]) return false;
    var prev = this.prevGamepadButtons[padIndex] && this.prevGamepadButtons[padIndex][btnIndex];
    return pad.buttons[btnIndex].pressed && !prev;
};

InputManager.prototype.getGamepadAxis = function(padIndex, axisIndex) {
    var pad = this.gamepads[padIndex];
    if (!pad || pad.axes[axisIndex] === undefined) return 0;
    var val = pad.axes[axisIndex];
    return Math.abs(val) < GAMEPAD_MAP.STICK_DEADZONE ? 0 : val;
};

InputManager.prototype.getPlayerInput = function(playerIndex, keyMap, gamepadIndex) {
    var input = {
        left: false, right: false, up: false, down: false,
        lightAttack: false, heavyAttack: false, special: false,
        grab: false, block: false, dash: false, taunt: false,
        // Just-pressed versions
        lightAttackPressed: false, heavyAttackPressed: false, specialPressed: false,
        grabPressed: false, dashPressed: false
    };

    // Keyboard
    input.left = this.isKeyDown(keyMap.left);
    input.right = this.isKeyDown(keyMap.right);
    input.up = this.isKeyDown(keyMap.up);
    input.down = this.isKeyDown(keyMap.down);
    input.lightAttack = this.isKeyDown(keyMap.lightAttack);
    input.heavyAttack = this.isKeyDown(keyMap.heavyAttack);
    input.special = this.isKeyDown(keyMap.special);
    input.grab = this.isKeyDown(keyMap.grab);
    input.block = this.isKeyDown(keyMap.block);
    input.dash = this.isKeyDown(keyMap.dash);
    input.taunt = this.isKeyDown(keyMap.taunt);

    input.lightAttackPressed = this.isKeyJustPressed(keyMap.lightAttack);
    input.heavyAttackPressed = this.isKeyJustPressed(keyMap.heavyAttack);
    input.specialPressed = this.isKeyJustPressed(keyMap.special);
    input.grabPressed = this.isKeyJustPressed(keyMap.grab);
    input.dashPressed = this.isKeyJustPressed(keyMap.dash);

    // Gamepad overlay
    if (gamepadIndex !== undefined && gamepadIndex !== null) {
        var gp = this.getGamepad(gamepadIndex);
        if (gp) {
            var ax = this.getGamepadAxis(gamepadIndex, GAMEPAD_MAP.MOVE_X);
            var ay = this.getGamepadAxis(gamepadIndex, GAMEPAD_MAP.MOVE_Y);
            if (ax < -0.3) input.left = true;
            if (ax > 0.3) input.right = true;
            if (ay < -0.3) input.up = true;
            if (ay > 0.3) input.down = true;
            // D-pad
            if (this.isGamepadButtonDown(gamepadIndex, GAMEPAD_MAP.DPAD_LEFT)) input.left = true;
            if (this.isGamepadButtonDown(gamepadIndex, GAMEPAD_MAP.DPAD_RIGHT)) input.right = true;
            if (this.isGamepadButtonDown(gamepadIndex, GAMEPAD_MAP.DPAD_UP)) input.up = true;
            if (this.isGamepadButtonDown(gamepadIndex, GAMEPAD_MAP.DPAD_DOWN)) input.down = true;
            // Buttons
            if (this.isGamepadButtonDown(gamepadIndex, GAMEPAD_MAP.LIGHT_ATTACK)) input.lightAttack = true;
            if (this.isGamepadButtonDown(gamepadIndex, GAMEPAD_MAP.HEAVY_ATTACK)) input.heavyAttack = true;
            if (this.isGamepadButtonDown(gamepadIndex, GAMEPAD_MAP.SPECIAL)) input.special = true;
            if (this.isGamepadButtonDown(gamepadIndex, GAMEPAD_MAP.GRAB)) input.grab = true;
            if (this.isGamepadButtonDown(gamepadIndex, GAMEPAD_MAP.BLOCK)) input.block = true;
            if (this.isGamepadButtonDown(gamepadIndex, GAMEPAD_MAP.DASH)) input.dash = true;
            // Just-pressed
            if (this.isGamepadButtonJustPressed(gamepadIndex, GAMEPAD_MAP.LIGHT_ATTACK)) input.lightAttackPressed = true;
            if (this.isGamepadButtonJustPressed(gamepadIndex, GAMEPAD_MAP.HEAVY_ATTACK)) input.heavyAttackPressed = true;
            if (this.isGamepadButtonJustPressed(gamepadIndex, GAMEPAD_MAP.SPECIAL)) input.specialPressed = true;
            if (this.isGamepadButtonJustPressed(gamepadIndex, GAMEPAD_MAP.GRAB)) input.grabPressed = true;
            if (this.isGamepadButtonJustPressed(gamepadIndex, GAMEPAD_MAP.DASH)) input.dashPressed = true;
        }
    }

    return input;
};

// === PARTICLE SYSTEM ===
function ParticleSystem() {
    this.particles = [];
}

ParticleSystem.prototype.emit = function(x, y, count, options) {
    var opts = options || {};
    for (var i = 0; i < count; i++) {
        this.particles.push({
            x: x + randomRange(-5, 5),
            y: y + randomRange(-5, 5),
            vx: randomRange(opts.minVX || -150, opts.maxVX || 150),
            vy: randomRange(opts.minVY || -250, opts.maxVY || -50),
            life: randomRange(opts.minLife || 0.3, opts.maxLife || 0.8),
            maxLife: 0,
            size: randomRange(opts.minSize || 2, opts.maxSize || 6),
            color: opts.color || '#ffaa00',
            gravity: opts.gravity !== undefined ? opts.gravity : 400,
            shrink: opts.shrink !== undefined ? opts.shrink : true
        });
        this.particles[this.particles.length - 1].maxLife = this.particles[this.particles.length - 1].life;
    }
};

ParticleSystem.prototype.update = function(dt) {
    for (var i = this.particles.length - 1; i >= 0; i--) {
        var p = this.particles[i];
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.vy += p.gravity * dt;
        p.life -= dt;
        if (p.life <= 0) {
            this.particles.splice(i, 1);
        }
    }
};

ParticleSystem.prototype.render = function(ctx) {
    for (var i = 0; i < this.particles.length; i++) {
        var p = this.particles[i];
        var alpha = clamp(p.life / p.maxLife, 0, 1);
        var size = p.shrink ? p.size * alpha : p.size;
        ctx.globalAlpha = alpha;
        ctx.fillStyle = p.color;
        ctx.fillRect(p.x - size / 2, p.y - size / 2, size, size);
    }
    ctx.globalAlpha = 1;
};

ParticleSystem.prototype.clear = function() {
    this.particles = [];
};

// === FIGHTER CLASS ===
function Fighter(x, y, facingRight, charIndex, weaponIndex, isPlayer) {
    this.x = x;
    this.y = y;
    this.facingRight = facingRight;
    this.charIndex = charIndex;
    this.weaponIndex = weaponIndex;
    this.character = CHARACTERS[charIndex];
    this.weapon = WEAPONS[weaponIndex];
    this.isPlayer = isPlayer;

    this.health = 100;
    this.maxHealth = 100;
    this.specialMeter = 0;
    this.velX = 0;
    this.velY = 0;
    this.grounded = true;
    this.canDoubleJump = this.character.hasDoubleJump;
    this.usedDoubleJump = false;

    this.state = 'idle';
    this.stateTime = 0;
    this.stateFrame = 0;
    this.attackPhase = 'none';
    this.attackTimer = 0;
    this.attackDuration = 0;
    this.attackHitActive = false;
    this.attackHasHit = false;
    this.currentAttackType = null;

    this.isBlocking = false;
    this.blockStun = 0;
    this.hitStun = 0;
    this.knockbackX = 0;
    this.knockbackY = 0;

    this.comboCount = 0;
    this.comboTimer = 0;
    this.comboDamage = 0;

    this.isDashing = false;
    this.dashTimer = 0;
    this.dashDir = 0;

    this.poisonTimer = 0;
    this.poisonDPS = 0;
    this.freezeTimer = 0;
    this.isTaunting = false;
    this.tauntTimer = 0;
    this.isKO = false;
    this.winPose = false;

    this.animTime = Math.random() * 10;
    this.hurtFlash = 0;

    var _RENDER_SCALE = 1.35;
    this.width = (this.character.body.shoulderW + 10) * _RENDER_SCALE;
    this.height = (this.character.body.headR * 2 + this.character.body.torsoH + this.character.body.legLen + 10) * _RENDER_SCALE;

    this.rageActive = false;
}

Fighter.prototype.reset = function(x, y, facingRight) {
    this.x = x;
    this.y = y;
    this.facingRight = facingRight;
    this.health = 100;
    this.specialMeter = 0;
    this.velX = 0;
    this.velY = 0;
    this.grounded = true;
    this.usedDoubleJump = false;
    this.state = 'idle';
    this.stateTime = 0;
    this.attackPhase = 'none';
    this.attackHitActive = false;
    this.attackHasHit = false;
    this.currentAttackType = null;
    this.isBlocking = false;
    this.blockStun = 0;
    this.hitStun = 0;
    this.knockbackX = 0;
    this.knockbackY = 0;
    this.comboCount = 0;
    this.comboTimer = 0;
    this.comboDamage = 0;
    this.isDashing = false;
    this.dashTimer = 0;
    this.poisonTimer = 0;
    this.freezeTimer = 0;
    this.isTaunting = false;
    this.isKO = false;
    this.winPose = false;
    this.hurtFlash = 0;
    this.rageActive = false;
};

Fighter.prototype.getHitbox = function() {
    var w = this.width;
    var h = this.height;
    if (this.state === 'crouch') h *= CONFIG.CROUCH_HEIGHT_MULT;
    return {
        x: this.x - w / 2,
        y: this.y - h,
        w: w,
        h: h
    };
};

Fighter.prototype.getAttackBox = function() {
    if (!this.attackHitActive || this.attackHasHit) return null;
    var range = 0;
    var type = this.currentAttackType;
    if (type === 'light') range = this.weapon.lightRange;
    else if (type === 'heavy') range = this.weapon.heavyRange;
    else if (type === 'special') range = 90;
    else if (type === 'grab') range = 50;
    var dir = this.facingRight ? 1 : -1;
    var w = range;
    var h = 40;
    var ox = dir > 0 ? this.width / 2 : -this.width / 2 - w;
    var oy = -this.height * 0.5;
    if (this.state === 'crouch') oy = -this.height * 0.3;
    return {
        x: this.x + ox,
        y: this.y + oy,
        w: w,
        h: h
    };
};

Fighter.prototype.startAttack = function(type) {
    if (this.hitStun > 0 || this.blockStun > 0 || this.isKO || this.freezeTimer > 0) return;
    if (this.state === 'attacking' || this.state === 'special') return;

    this.currentAttackType = type;
    this.attackHasHit = false;
    this.attackHitActive = false;

    var startup, active, recovery;
    if (type === 'light') {
        startup = this.weapon.lightStartup;
        active = 4;
        recovery = this.weapon.lightRecovery;
        this.state = 'attacking';
    } else if (type === 'heavy') {
        startup = this.weapon.heavyStartup;
        active = 6;
        recovery = this.weapon.heavyRecovery;
        this.state = 'attacking';
    } else if (type === 'special') {
        if (this.specialMeter < 50) return;
        this.specialMeter -= 50;
        startup = this.character.specialStartup;
        active = 8;
        recovery = this.character.specialRecovery;
        this.state = 'special';
    } else if (type === 'grab') {
        startup = 4;
        active = 4;
        recovery = 20;
        this.state = 'attacking';
    }

    this.attackPhase = 'startup';
    this.attackTimer = 0;
    this.attackDuration = (startup + active + recovery) / CONFIG.FPS;
    this._attackStartup = startup / CONFIG.FPS;
    this._attackActive = active / CONFIG.FPS;
    this._attackRecovery = recovery / CONFIG.FPS;
    this.stateTime = 0;

    // Attack whoosh SFX
    if (window.GameAudio) {
        if (type === 'light') GameAudio.sfx.lightAttack();
        else if (type === 'heavy') GameAudio.sfx.heavyAttack();
        else if (type === 'special') GameAudio.sfx.specialAttack();
    }
};

Fighter.prototype.takeDamage = function(amount, knockbackX, knockbackY, attacker) {
    if (this.isKO) return;

    var blocked = this.isBlocking;
    var actualDamage = blocked ? amount * CONFIG.BLOCK_DAMAGE_MULT : amount;

    // Drake rage mode bonus
    if (attacker && attacker.rageActive) {
        actualDamage *= (1 + attacker.character.rageDamageBonus);
    }

    this.health -= actualDamage;
    if (this.health < 0) this.health = 0;

    if (blocked) {
        this.blockStun = 0.2;
        this.knockbackX = knockbackX * 0.3;
        if (window.GameAudio) GameAudio.sfx.block();
    } else {
        this.hitStun = 0.3;
        this.knockbackX = knockbackX;
        this.knockbackY = knockbackY;
        this.velY = knockbackY;
        // CRITICAL: mark as airborne so gravity applies during launch
        if (knockbackY < 0) {
            this.grounded = false;
        }
        this.state = 'hit';
        this.stateTime = 0;
        this.attackPhase = 'none';
        this.attackHitActive = false;
        this.hurtFlash = 0.15;
    }

    // Special meter gain
    var prevMeter = this.specialMeter;
    this.specialMeter = Math.min(CONFIG.SPECIAL_METER_MAX, this.specialMeter + CONFIG.METER_GAIN_TAKE);
    if (attacker) {
        var aPrev = attacker.specialMeter;
        attacker.specialMeter = Math.min(CONFIG.SPECIAL_METER_MAX, attacker.specialMeter + CONFIG.METER_GAIN_DEAL);
        if (aPrev < 50 && attacker.specialMeter >= 50 && window.GameAudio) GameAudio.sfx.meterFull();
    }
    if (prevMeter < 50 && this.specialMeter >= 50 && window.GameAudio) GameAudio.sfx.meterFull();

    // Drake rage check
    if (this.character.rageMode && this.health < 30) {
        this.rageActive = true;
    }

    if (this.health <= 0) {
        this.isKO = true;
        this.state = 'ko';
        this.stateTime = 0;
        this.velY = -300;
        this.grounded = false;
    }
};

Fighter.prototype.applyPoison = function(dps, duration) {
    this.poisonDPS = dps;
    this.poisonTimer = duration / 1000;
};

Fighter.prototype.applyFreeze = function(duration) {
    this.freezeTimer = duration / 1000;
};

Fighter.prototype.update = function(dt, input) {
    this.animTime += dt;
    this.stateTime += dt;

    // Timers
    if (this.hurtFlash > 0) this.hurtFlash -= dt;
    if (this.comboTimer > 0) {
        this.comboTimer -= dt * 1000;
        if (this.comboTimer <= 0) {
            this.comboCount = 0;
            this.comboDamage = 0;
        }
    }

    // Poison DOT
    if (this.poisonTimer > 0) {
        this.poisonTimer -= dt;
        this.health -= this.poisonDPS * dt;
        if (this.health <= 0) {
            this.health = 0;
            this.isKO = true;
            this.state = 'ko';
            this.stateTime = 0;
        }
    }

    // Freeze
    if (this.freezeTimer > 0) {
        this.freezeTimer -= dt;
        return;
    }

    if (this.isKO) {
        this.velY += CONFIG.GRAVITY * dt;
        this.y += this.velY * dt;
        this._applyBounds();
        if (this.y >= CONFIG.GROUND_Y) {
            this.y = CONFIG.GROUND_Y;
            this.velY = 0;
            this.grounded = true;
        }
        return;
    }

    if (this.winPose) return;

    // Hitstun / blockstun
    if (this.hitStun > 0) {
        this.hitStun -= dt;
        this.x += this.knockbackX * dt;
        this.knockbackX *= 0.9;
    }
    if (this.blockStun > 0) {
        this.blockStun -= dt;
        this.x += this.knockbackX * dt;
        this.knockbackX *= 0.9;
    }

    // Dash
    if (this.isDashing) {
        this.dashTimer -= dt;
        this.x += this.dashDir * CONFIG.DASH_SPEED * dt;
        if (this.dashTimer <= 0) {
            this.isDashing = false;
        }
        this._applyBounds();
        return;
    }

    // Attack state machine
    if (this.state === 'attacking' || this.state === 'special') {
        this.attackTimer += dt;
        if (this.attackTimer < this._attackStartup) {
            this.attackPhase = 'startup';
            this.attackHitActive = false;
        } else if (this.attackTimer < this._attackStartup + this._attackActive) {
            this.attackPhase = 'active';
            this.attackHitActive = true;
        } else if (this.attackTimer < this.attackDuration) {
            this.attackPhase = 'recovery';
            this.attackHitActive = false;
        } else {
            this.state = 'idle';
            this.attackPhase = 'none';
            this.attackHitActive = false;
            this.currentAttackType = null;
        }
        // Can still fall during air attacks
        if (!this.grounded) {
            this.velY += CONFIG.GRAVITY * dt;
            if (this.velY > CONFIG.MAX_FALL_SPEED) this.velY = CONFIG.MAX_FALL_SPEED;
            this.y += this.velY * dt;
            if (this.y >= CONFIG.GROUND_Y) {
                this.y = CONFIG.GROUND_Y;
                this.velY = 0;
                this.grounded = true;
                this.usedDoubleJump = false;
            }
        }
        this._applyBounds();
        return;
    }

    // Taunt
    if (this.isTaunting) {
        this.tauntTimer -= dt;
        if (this.tauntTimer <= 0) {
            this.isTaunting = false;
            this.state = 'idle';
            this.specialMeter = Math.min(CONFIG.SPECIAL_METER_MAX, this.specialMeter + 15);
        }
        return;
    }

    if (!input) { this._applyPhysics(dt); return; }

    // Blocking
    var holdingBack = (this.facingRight && input.left) || (!this.facingRight && input.right);
    this.isBlocking = holdingBack && input.block && this.grounded && this.hitStun <= 0;

    if (this.isBlocking) {
        this.state = 'block';
        this._applyPhysics(dt);
        return;
    }

    // Handle input actions (only if not stunned)
    if (this.hitStun <= 0 && this.blockStun <= 0) {
        // Dash
        if (input.dashPressed && this.grounded) {
            this.isDashing = true;
            this.dashTimer = CONFIG.DASH_DURATION / 1000;
            this.dashDir = this.facingRight ? 1 : -1;
            if (input.left) this.dashDir = -1;
            if (input.right) this.dashDir = 1;
            if (window.GameAudio) GameAudio.sfx.dash();
            return;
        }

        // Attacks
        if (input.specialPressed) {
            this.startAttack('special');
            if (this.state === 'special') return;
        }
        if (input.heavyAttackPressed) {
            this.startAttack('heavy');
            if (this.state === 'attacking') return;
        }
        if (input.lightAttackPressed) {
            this.startAttack('light');
            if (this.state === 'attacking') return;
        }
        if (input.grabPressed) {
            this.startAttack('grab');
            if (this.state === 'attacking') return;
        }

        // Taunt
        if (input.taunt && this.grounded && this.state === 'idle') {
            this.isTaunting = true;
            this.tauntTimer = 1.5;
            this.state = 'taunt';
            return;
        }

        // Movement
        var moveSpeed = CONFIG.WALK_SPEED * this.character.walkSpeed;
        if (input.left) {
            this.velX = -moveSpeed;
            this.state = this.grounded ? 'walk' : this.state;
        } else if (input.right) {
            this.velX = moveSpeed;
            this.state = this.grounded ? 'walk' : this.state;
        } else {
            this.velX = 0;
            if (this.grounded && this.state === 'walk') this.state = 'idle';
        }

        // Crouch
        if (input.down && this.grounded) {
            this.state = 'crouch';
            this.velX = 0;
        } else if (this.state === 'crouch' && !input.down) {
            this.state = 'idle';
        }

        // Jump
        if (input.up && this.grounded && this.state !== 'crouch') {
            this.velY = CONFIG.JUMP_FORCE * this.character.jumpForce;
            this.grounded = false;
            this.state = 'jump';
            this.usedDoubleJump = false;
            if (window.GameAudio) GameAudio.sfx.jump();
        } else if (input.up && !this.grounded && this.canDoubleJump && !this.usedDoubleJump) {
            this.velY = CONFIG.DOUBLE_JUMP_FORCE * this.character.jumpForce;
            this.usedDoubleJump = true;
            if (window.GameAudio) GameAudio.sfx.jump();
        }

        if (!this.grounded) this.state = 'jump';
        if (this.grounded && this.velX === 0 && this.state !== 'crouch') this.state = 'idle';
    }

    this._applyPhysics(dt);
};

Fighter.prototype._applyPhysics = function(dt) {
    // Gravity
    if (!this.grounded) {
        this.velY += CONFIG.GRAVITY * dt;
        if (this.velY > CONFIG.MAX_FALL_SPEED) this.velY = CONFIG.MAX_FALL_SPEED;
    }

    this.x += this.velX * dt;
    this.y += this.velY * dt;

    // Ground collision
    var wasAirborne = !this.grounded;
    if (this.y >= CONFIG.GROUND_Y) {
        this.y = CONFIG.GROUND_Y;
        this.velY = 0;
        this.grounded = true;
        this.usedDoubleJump = false;
        if (this.state === 'jump' || this.state === 'hit') {
            this.state = 'idle';
        }
        if (wasAirborne && window.GameAudio) GameAudio.sfx.land();
    }

    this._applyBounds();
};

Fighter.prototype._applyBounds = function() {
    if (this.x < CONFIG.STAGE_LEFT + this.width / 2) {
        this.x = CONFIG.STAGE_LEFT + this.width / 2;
    }
    if (this.x > CONFIG.STAGE_RIGHT - this.width / 2) {
        this.x = CONFIG.STAGE_RIGHT - this.width / 2;
    }
    // Prevent flying off the top of the screen
    var minY = -50; // small buffer above visible canvas
    if (this.y < minY) {
        this.y = minY;
        if (this.velY < 0) this.velY = 0; // stop upward velocity
    }
};

// === FIGHTER RENDERING ===
Fighter.prototype.render = function(ctx) {
    var c = this.character;
    var b = c.body;
    var dir = this.facingRight ? 1 : -1;
    var pose = this._getPose();

    ctx.save();
    ctx.translate(this.x, this.y);
    ctx.scale(dir, 1);

    // Flash on hit
    if (this.hurtFlash > 0 && Math.floor(this.hurtFlash * 30) % 2 === 0) {
        ctx.globalAlpha = 0.6;
    }

    // Freeze tint
    if (this.freezeTimer > 0) {
        ctx.globalAlpha = 0.7;
    }

    // Shadow
    ctx.fillStyle = 'rgba(0,0,0,0.3)';
    ctx.beginPath();
    ctx.ellipse(0, 0, b.shoulderW * 0.6, 6, 0, 0, Math.PI * 2);
    ctx.fill();

    // --- Legs ---
    this._drawLimb(ctx, 0 - 8, -b.legLen - 4, pose.leftLegAngle, b.legW, b.legLen, c.colors.secondary);
    this._drawLimb(ctx, 0 + 8, -b.legLen - 4, pose.rightLegAngle, b.legW, b.legLen, c.colors.secondary);

    // Feet
    ctx.fillStyle = c.colors.secondary;
    var lfx = 0 - 8 + Math.sin(degToRad(pose.leftLegAngle)) * b.legLen;
    var lfy = -4 + Math.cos(degToRad(pose.leftLegAngle)) * b.legLen * 0.15;
    ctx.fillRect(lfx - 6, lfy - 2, 12, 5);
    var rfx = 0 + 8 + Math.sin(degToRad(pose.rightLegAngle)) * b.legLen;
    var rfy = -4 + Math.cos(degToRad(pose.rightLegAngle)) * b.legLen * 0.15;
    ctx.fillRect(rfx - 6, rfy - 2, 12, 5);

    // --- Torso ---
    var torsoY = -b.legLen - b.torsoH + pose.bodyOffsetY;
    ctx.fillStyle = c.colors.primary;
    this._roundRect(ctx, -b.torsoW / 2, torsoY, b.torsoW, b.torsoH, 4);

    // Belt/accent line
    ctx.fillStyle = c.colors.accent;
    ctx.fillRect(-b.torsoW / 2 + 2, torsoY + b.torsoH - 6, b.torsoW - 4, 4);

    // --- Arms ---
    var shoulderY = torsoY + 4;
    // Back arm
    this._drawLimb(ctx, -b.shoulderW / 2, shoulderY, pose.leftArmAngle, b.armW, b.armLen, c.colors.skin);
    // Front arm + weapon
    this._drawLimb(ctx, b.shoulderW / 2, shoulderY, pose.rightArmAngle, b.armW, b.armLen, c.colors.skin);

    // Weapon in front hand
    var handX = b.shoulderW / 2 + Math.sin(degToRad(pose.rightArmAngle)) * b.armLen;
    var handY = shoulderY + Math.cos(degToRad(pose.rightArmAngle)) * b.armLen * 0.3;
    this._drawWeapon(ctx, handX, handY, pose.weaponAngle);

    // --- Head ---
    var headY = torsoY - b.headR + pose.bodyOffsetY * 0.5;
    ctx.fillStyle = c.colors.skin;
    ctx.beginPath();
    ctx.arc(0, headY, b.headR, 0, Math.PI * 2);
    ctx.fill();

    // Hair
    ctx.fillStyle = c.colors.hair;
    ctx.beginPath();
    ctx.arc(0, headY - 2, b.headR + 1, Math.PI, Math.PI * 2);
    ctx.fill();

    // Eyes
    ctx.fillStyle = c.colors.eye;
    ctx.beginPath();
    ctx.arc(4, headY - 1, 2.5, 0, Math.PI * 2);
    ctx.fill();

    // Unique features
    this._drawUniqueFeature(ctx, headY, torsoY, pose);

    // Rage aura for Drake
    if (this.rageActive) {
        ctx.strokeStyle = c.colors.glow;
        ctx.lineWidth = 2;
        ctx.globalAlpha = 0.4 + Math.sin(this.animTime * 8) * 0.2;
        ctx.beginPath();
        ctx.arc(0, torsoY + b.torsoH / 2, b.shoulderW + 10 + Math.sin(this.animTime * 6) * 5, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 1;
    }

    // Blocking shield effect
    if (this.isBlocking) {
        ctx.strokeStyle = 'rgba(100,200,255,0.6)';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(10, torsoY + b.torsoH / 2, 35, -Math.PI * 0.6, Math.PI * 0.6);
        ctx.stroke();
    }

    ctx.restore();

    // Poison effect
    if (this.poisonTimer > 0) {
        ctx.fillStyle = 'rgba(0,255,100,0.3)';
        ctx.beginPath();
        ctx.arc(this.x, this.y - this.height / 2, 30 + Math.sin(this.animTime * 5) * 5, 0, Math.PI * 2);
        ctx.fill();
    }

    // Combo counter
    if (this.comboCount > 1) {
        ctx.save();
        ctx.font = 'bold 24px "Rajdhani", sans-serif';
        ctx.fillStyle = '#ffcc00';
        ctx.textAlign = 'center';
        ctx.fillText(this.comboCount + ' HIT COMBO!', this.x, this.y - this.height - 20);
        ctx.restore();
    }
};

Fighter.prototype._getPose = function() {
    var t = this.animTime;
    var st = this.stateTime;
    var pose = {
        bodyOffsetY: 0,
        leftArmAngle: -15,
        rightArmAngle: 15,
        leftLegAngle: -5,
        rightLegAngle: 5,
        weaponAngle: 20
    };

    switch (this.state) {
        case 'idle':
            pose.bodyOffsetY = Math.sin(t * 3) * 2;
            pose.leftArmAngle = -15 + Math.sin(t * 2) * 5;
            pose.rightArmAngle = 15 + Math.sin(t * 2 + 1) * 5;
            pose.leftLegAngle = -5 + Math.sin(t * 3) * 2;
            pose.rightLegAngle = 5 + Math.sin(t * 3 + Math.PI) * 2;
            pose.weaponAngle = 20 + Math.sin(t * 2) * 5;
            break;

        case 'walk':
            pose.bodyOffsetY = Math.abs(Math.sin(t * 8)) * 3;
            pose.leftArmAngle = Math.sin(t * 8) * 25;
            pose.rightArmAngle = -Math.sin(t * 8) * 25;
            pose.leftLegAngle = -Math.sin(t * 8) * 20;
            pose.rightLegAngle = Math.sin(t * 8) * 20;
            pose.weaponAngle = 15 + Math.sin(t * 8) * 10;
            break;

        case 'jump':
            pose.bodyOffsetY = -5;
            pose.leftArmAngle = -40;
            pose.rightArmAngle = 40;
            pose.leftLegAngle = this.velY < 0 ? -15 : 10;
            pose.rightLegAngle = this.velY < 0 ? 15 : -10;
            pose.weaponAngle = 45;
            break;

        case 'crouch':
            pose.bodyOffsetY = 15;
            pose.leftArmAngle = -30;
            pose.rightArmAngle = 10;
            pose.leftLegAngle = -30;
            pose.rightLegAngle = 30;
            pose.weaponAngle = 0;
            break;

        case 'attacking':
            var progress = this.attackTimer / this.attackDuration;
            if (this.currentAttackType === 'light') {
                if (progress < 0.3) {
                    pose.rightArmAngle = lerp(15, -60, progress / 0.3);
                    pose.weaponAngle = lerp(20, -90, progress / 0.3);
                } else if (progress < 0.5) {
                    pose.rightArmAngle = lerp(-60, 70, (progress - 0.3) / 0.2);
                    pose.weaponAngle = lerp(-90, 90, (progress - 0.3) / 0.2);
                } else {
                    pose.rightArmAngle = lerp(70, 15, (progress - 0.5) / 0.5);
                    pose.weaponAngle = lerp(90, 20, (progress - 0.5) / 0.5);
                }
            } else if (this.currentAttackType === 'heavy') {
                if (progress < 0.4) {
                    pose.rightArmAngle = lerp(15, -90, progress / 0.4);
                    pose.weaponAngle = lerp(20, -120, progress / 0.4);
                    pose.bodyOffsetY = lerp(0, -5, progress / 0.4);
                } else if (progress < 0.55) {
                    pose.rightArmAngle = lerp(-90, 80, (progress - 0.4) / 0.15);
                    pose.weaponAngle = lerp(-120, 100, (progress - 0.4) / 0.15);
                    pose.bodyOffsetY = lerp(-5, 3, (progress - 0.4) / 0.15);
                } else {
                    pose.rightArmAngle = lerp(80, 15, (progress - 0.55) / 0.45);
                    pose.weaponAngle = lerp(100, 20, (progress - 0.55) / 0.45);
                }
            } else if (this.currentAttackType === 'grab') {
                pose.leftArmAngle = lerp(-15, 50, Math.min(progress * 3, 1));
                pose.rightArmAngle = lerp(15, 50, Math.min(progress * 3, 1));
            }
            break;

        case 'special':
            var sp = this.attackTimer / this.attackDuration;
            pose.rightArmAngle = lerp(15, 80, Math.min(sp * 2, 1));
            pose.leftArmAngle = lerp(-15, -80, Math.min(sp * 2, 1));
            pose.weaponAngle = lerp(20, 180, Math.min(sp * 2, 1));
            pose.bodyOffsetY = Math.sin(sp * Math.PI * 4) * 5;
            break;

        case 'hit':
            pose.bodyOffsetY = 5;
            pose.leftArmAngle = -40;
            pose.rightArmAngle = -20;
            pose.leftLegAngle = 10;
            pose.rightLegAngle = -10;
            pose.weaponAngle = -30;
            break;

        case 'block':
            pose.leftArmAngle = 50;
            pose.rightArmAngle = -10;
            pose.weaponAngle = -80;
            pose.bodyOffsetY = 2;
            break;

        case 'ko':
            var koP = Math.min(st / 0.5, 1);
            pose.bodyOffsetY = lerp(0, 40, koP);
            pose.leftArmAngle = lerp(-15, -60, koP);
            pose.rightArmAngle = lerp(15, 70, koP);
            pose.leftLegAngle = lerp(-5, 20, koP);
            pose.rightLegAngle = lerp(5, 30, koP);
            break;

        case 'taunt':
            pose.leftArmAngle = -60 + Math.sin(t * 10) * 15;
            pose.rightArmAngle = 60 + Math.sin(t * 10) * 15;
            pose.bodyOffsetY = Math.sin(t * 6) * 3;
            pose.weaponAngle = 90;
            break;
    }

    return pose;
};

Fighter.prototype._drawLimb = function(ctx, x, y, angle, width, length, color) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(degToRad(angle));
    ctx.fillStyle = color;
    ctx.fillRect(-width / 2, 0, width, length);
    // Joint circle
    ctx.beginPath();
    ctx.arc(0, 0, width / 2 + 1, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
};

Fighter.prototype._drawWeapon = function(ctx, hx, hy, angle) {
    var w = this.weapon;
    ctx.save();
    ctx.translate(hx, hy);
    ctx.rotate(degToRad(angle));

    ctx.strokeStyle = w.color;
    ctx.lineWidth = w.width;
    ctx.lineCap = 'round';

    switch (w.drawType) {
        case 'blade':
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(w.length, 0);
            ctx.stroke();
            // Blade edge glow
            ctx.strokeStyle = w.glowColor;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(5, -w.width / 2);
            ctx.lineTo(w.length, 0);
            ctx.stroke();
            // Guard
            ctx.fillStyle = '#8b7355';
            ctx.fillRect(-3, -6, 6, 12);
            break;

        case 'hammer':
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(w.length - 15, 0);
            ctx.stroke();
            // Hammer head
            ctx.fillStyle = '#5d6d7e';
            ctx.fillRect(w.length - 18, -12, 18, 24);
            ctx.fillStyle = w.glowColor;
            ctx.fillRect(w.length - 16, -10, 2, 20);
            break;

        case 'daggers':
            ctx.beginPath();
            ctx.moveTo(0, -4);
            ctx.lineTo(w.length, -4);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(0, 4);
            ctx.lineTo(w.length, 4);
            ctx.stroke();
            break;

        case 'chain':
            for (var i = 0; i < w.length; i += 8) {
                ctx.fillStyle = (i / 8) % 2 === 0 ? w.color : w.glowColor;
                ctx.fillRect(i, -2 + Math.sin(i * 0.3 + this.animTime * 8) * 3, 6, 4);
            }
            // Chain end weight
            ctx.fillStyle = '#5d6d7e';
            ctx.beginPath();
            ctx.arc(w.length, Math.sin(this.animTime * 8) * 4, 6, 0, Math.PI * 2);
            ctx.fill();
            break;

        case 'axe':
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(w.length - 12, 0);
            ctx.stroke();
            // Axe head
            ctx.fillStyle = '#78909c';
            ctx.beginPath();
            ctx.moveTo(w.length - 12, -14);
            ctx.lineTo(w.length, 0);
            ctx.lineTo(w.length - 12, 14);
            ctx.closePath();
            ctx.fill();
            break;

        case 'staff':
            ctx.lineWidth = w.width;
            ctx.beginPath();
            ctx.moveTo(-10, 0);
            ctx.lineTo(w.length, 0);
            ctx.stroke();
            // End caps
            ctx.fillStyle = w.glowColor;
            ctx.beginPath();
            ctx.arc(w.length, 0, 4, 0, Math.PI * 2);
            ctx.fill();
            ctx.beginPath();
            ctx.arc(-10, 0, 4, 0, Math.PI * 2);
            ctx.fill();
            break;
    }

    // Attack flash
    if (this.attackHitActive) {
        ctx.globalAlpha = 0.4;
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = w.width + 4;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(w.length, 0);
        ctx.stroke();
        ctx.globalAlpha = 1;
    }

    ctx.restore();
};

Fighter.prototype._drawUniqueFeature = function(ctx, headY, torsoY, pose) {
    var c = this.character;

    switch (c.uniqueFeature) {
        case 'scarf':
            // Flowing scarf
            ctx.strokeStyle = c.colors.accent;
            ctx.lineWidth = 4;
            ctx.beginPath();
            ctx.moveTo(-5, headY + 5);
            for (var i = 1; i <= 5; i++) {
                ctx.lineTo(-5 - i * 8, headY + 5 + Math.sin(this.animTime * 4 + i) * 6 + i * 3);
            }
            ctx.stroke();
            break;

        case 'armor':
            // Shoulder pads
            ctx.fillStyle = c.colors.accent;
            ctx.fillRect(-c.body.shoulderW / 2 - 4, torsoY + 1, 10, 8);
            ctx.fillRect(c.body.shoulderW / 2 - 6, torsoY + 1, 10, 8);
            // Helmet visor
            ctx.fillStyle = c.colors.accent;
            ctx.fillRect(2, headY - 4, 10, 4);
            break;

        case 'lightning':
            // Lightning crackles
            if (this.state === 'special' || Math.random() < 0.03) {
                ctx.strokeStyle = c.colors.accent;
                ctx.lineWidth = 1.5;
                ctx.globalAlpha = 0.8;
                var lx = randomRange(-20, 20);
                var ly = randomRange(torsoY - 10, torsoY + c.body.torsoH);
                ctx.beginPath();
                ctx.moveTo(lx, ly);
                ctx.lineTo(lx + randomRange(-15, 15), ly + randomRange(-15, 15));
                ctx.lineTo(lx + randomRange(-15, 15), ly + randomRange(-15, 15));
                ctx.stroke();
                ctx.globalAlpha = 1;
            }
            break;

        case 'poison':
            // Dripping effect
            ctx.fillStyle = c.colors.accent;
            ctx.globalAlpha = 0.5;
            for (var p = 0; p < 3; p++) {
                var px = randomRange(-10, 10);
                var py = torsoY + c.body.torsoH + Math.sin(this.animTime * 2 + p) * 10;
                ctx.beginPath();
                ctx.arc(px, py, 2, 0, Math.PI * 2);
                ctx.fill();
            }
            ctx.globalAlpha = 1;
            break;

        case 'ice':
            // Ice crystals around hands during special
            if (this.state === 'special') {
                ctx.fillStyle = 'rgba(133,193,233,0.6)';
                for (var ic = 0; ic < 4; ic++) {
                    var ix = randomRange(-30, 30);
                    var iy = torsoY + randomRange(-10, c.body.torsoH);
                    ctx.beginPath();
                    ctx.moveTo(ix, iy - 5);
                    ctx.lineTo(ix + 3, iy);
                    ctx.lineTo(ix, iy + 5);
                    ctx.lineTo(ix - 3, iy);
                    ctx.closePath();
                    ctx.fill();
                }
            }
            break;

        case 'fire':
            // Fire aura
            var fireAlpha = this.rageActive ? 0.6 : 0.2;
            ctx.globalAlpha = fireAlpha;
            for (var fi = 0; fi < (this.rageActive ? 6 : 2); fi++) {
                var fx = randomRange(-15, 15);
                var fy = torsoY + c.body.torsoH - randomRange(0, 30);
                var fsize = randomRange(3, 8);
                ctx.fillStyle = Math.random() > 0.5 ? c.colors.accent : c.colors.glow;
                ctx.beginPath();
                ctx.arc(fx, fy, fsize, 0, Math.PI * 2);
                ctx.fill();
            }
            ctx.globalAlpha = 1;
            break;
    }
};

Fighter.prototype._roundRect = function(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
    ctx.fill();
};


// === AI OPPONENT ===
function AIController(difficulty) {
    this.difficulty = DIFFICULTY[difficulty] || DIFFICULTY.medium;
    this.reactionTimer = 0;
    this.decisionTimer = 0;
    this.currentDecision = 'idle';
    this.adaptMemory = [];
    this.patternCounts = {};
}

AIController.prototype.getInput = function(fighter, opponent, dt) {
    var input = {
        left: false, right: false, up: false, down: false,
        lightAttack: false, heavyAttack: false, special: false,
        grab: false, block: false, dash: false, taunt: false,
        lightAttackPressed: false, heavyAttackPressed: false, specialPressed: false,
        grabPressed: false, dashPressed: false
    };

    this.reactionTimer += dt;
    this.decisionTimer += dt;

    var reactionTime = this.difficulty.reactionFrames / CONFIG.FPS;
    if (this.decisionTimer < reactionTime) return input;
    this.decisionTimer = 0;

    var dist = Math.abs(fighter.x - opponent.x);
    var isClose = dist < 80;
    var isMid = dist < 200;
    var isFar = dist >= 200;
    var opponentAttacking = opponent.state === 'attacking' || opponent.state === 'special';
    var healthAdvantage = fighter.health - opponent.health;
    var hasSpecial = fighter.specialMeter >= 50;

    // Track opponent patterns for adaptation
    if (this.difficulty.adaptRate > 0) {
        var oppAction = opponent.state + '_' + opponent.currentAttackType;
        this.patternCounts[oppAction] = (this.patternCounts[oppAction] || 0) + 1;
    }

    // Decision making
    var rand = Math.random();

    // Block incoming attacks
    if (opponentAttacking && rand < this.difficulty.blockChance) {
        input.block = true;
        input.left = fighter.facingRight;
        input.right = !fighter.facingRight;
        return input;
    }

    // Close range decisions
    if (isClose) {
        if (rand < this.difficulty.aggressiveness) {
            // Attack
            var attackRand = Math.random();
            if (hasSpecial && attackRand < 0.2) {
                input.specialPressed = true;
                input.special = true;
            } else if (attackRand < 0.5 && rand < this.difficulty.comboChance) {
                input.heavyAttackPressed = true;
                input.heavyAttack = true;
            } else if (attackRand < 0.8) {
                input.lightAttackPressed = true;
                input.lightAttack = true;
            } else {
                input.grabPressed = true;
                input.grab = true;
            }
        } else {
            // Defensive - dash away or block
            if (Math.random() < 0.4) {
                input.dashPressed = true;
                input.dash = true;
                input.left = fighter.facingRight;
                input.right = !fighter.facingRight;
            } else {
                input.block = true;
                input.left = fighter.facingRight;
                input.right = !fighter.facingRight;
            }
        }
    }
    // Mid range
    else if (isMid) {
        if (rand < this.difficulty.aggressiveness * 0.8) {
            // Advance and attack
            input.right = opponent.x > fighter.x;
            input.left = opponent.x < fighter.x;
            if (dist < 120 && Math.random() < 0.4) {
                input.lightAttackPressed = true;
                input.lightAttack = true;
            }
        } else {
            // Use ranged special or approach carefully
            if (hasSpecial && Math.random() < 0.3) {
                input.specialPressed = true;
                input.special = true;
            } else {
                input.right = opponent.x > fighter.x;
                input.left = opponent.x < fighter.x;
            }
        }
    }
    // Far range
    else {
        // Approach
        input.right = opponent.x > fighter.x;
        input.left = opponent.x < fighter.x;
        // Sometimes dash in
        if (Math.random() < 0.2) {
            input.dashPressed = true;
            input.dash = true;
        }
        // Anti-air if opponent is jumping
        if (!opponent.grounded && Math.random() < this.difficulty.comboChance) {
            input.heavyAttackPressed = true;
            input.heavyAttack = true;
        }
    }

    // Jump occasionally
    if (Math.random() < 0.05) {
        input.up = true;
    }

    // Crouch to dodge occasionally
    if (opponentAttacking && Math.random() < 0.15) {
        input.down = true;
    }

    // Low health aggression boost (comeback mechanic)
    if (fighter.health < 25 && hasSpecial && Math.random() < 0.4) {
        input.specialPressed = true;
        input.special = true;
    }

    return input;
};


// === STAGE RENDERER ===
function renderStage(ctx, stage, time) {
    var s = STAGES[stage] || STAGES[0];
    var cw = CONFIG.CANVAS_WIDTH, ch = CONFIG.CANVAS_HEIGHT, gy = CONFIG.GROUND_Y;
    var sl = CONFIG.STAGE_LEFT, sr = CONFIG.STAGE_RIGHT;

    // Sky gradient (richer with 3 stops)
    var grad = ctx.createLinearGradient(0, 0, 0, ch);
    grad.addColorStop(0, s.skyColors[0]);
    grad.addColorStop(0.6, s.skyColors[1]);
    grad.addColorStop(1, s.groundColor);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, cw, ch);

    // Ambient particles (slow-drifting motes)
    ctx.globalAlpha = 0.15;
    for (var mp = 0; mp < 20; mp++) {
        var mx = ((time * 12 + mp * 67) % cw);
        var my = ((mp * 37 + Math.sin(time * 0.5 + mp) * 60) % (gy - 40)) + 30;
        ctx.fillStyle = s.accentColor;
        ctx.beginPath();
        ctx.arc(mx, my, 1.5 + Math.sin(time + mp) * 0.5, 0, Math.PI * 2);
        ctx.fill();
    }
    ctx.globalAlpha = 1;

    // Stage features
    switch (s.features) {
        case 'lanterns':
            for (var i = 0; i < 6; i++) {
                var lx = 100 + i * 210;
                // String
                ctx.strokeStyle = '#3a1a0a'; ctx.lineWidth = 1;
                ctx.beginPath(); ctx.moveTo(lx, 0); ctx.lineTo(lx, 75 + Math.sin(time * 1.5 + i) * 4); ctx.stroke();
                // Glow halo
                var gRad = ctx.createRadialGradient(lx, 90, 0, lx, 90, 45);
                gRad.addColorStop(0, 'rgba(255,120,40,0.18)');
                gRad.addColorStop(1, 'rgba(255,120,40,0)');
                ctx.fillStyle = gRad; ctx.fillRect(lx - 45, 45, 90, 90);
                // Lantern body
                ctx.fillStyle = '#6a1a0a';
                ctx.beginPath(); ctx.moveTo(lx - 10, 78 + Math.sin(time * 1.5 + i) * 4);
                ctx.quadraticCurveTo(lx - 14, 92, lx - 10, 106);
                ctx.lineTo(lx + 10, 106); ctx.quadraticCurveTo(lx + 14, 92, lx + 10, 78 + Math.sin(time * 1.5 + i) * 4);
                ctx.closePath(); ctx.fill();
                // Inner glow
                ctx.fillStyle = 'rgba(255,180,80,' + (0.5 + Math.sin(time * 4 + i * 1.3) * 0.2) + ')';
                ctx.beginPath(); ctx.ellipse(lx, 92, 7, 10, 0, 0, Math.PI * 2); ctx.fill();
            }
            break;

        case 'crowd':
            // Crowd rows (parallax-ish depth)
            for (var row = 0; row < 3; row++) {
                var rowY = 55 + row * 28;
                var crowdCount = 35 + row * 5;
                for (var ci = 0; ci < crowdCount; ci++) {
                    var ccx = (ci * 34 + row * 12) % (cw + 20) - 10;
                    var ccy = rowY + Math.sin(time * (2.5 + row * 0.3) + ci * 0.4) * (2 + row);
                    var hue = (ci * 37 + row * 120) % 360;
                    var lum = 20 + row * 5;
                    ctx.fillStyle = 'hsl(' + hue + ',25%,' + lum + '%)';
                    ctx.beginPath(); ctx.arc(ccx, ccy, 7 - row, 0, Math.PI * 2); ctx.fill();
                    ctx.fillRect(ccx - 4 + row, ccy + 6 - row, 8 - row * 2, 12 - row * 2);
                }
            }
            break;

        case 'cityscape':
            // Far buildings (silhouettes)
            ctx.fillStyle = '#0d0d1a';
            for (var fb = 0; fb < 20; fb++) {
                var fbx = fb * 72 - 20;
                var fbh = 60 + ((fb * 53 + 17) % 160);
                ctx.fillRect(fbx, gy - fbh - 220, 60, fbh);
            }
            // Near buildings
            for (var bi = 0; bi < 15; bi++) {
                var bx = bi * 95 - 15;
                var bh = 100 + ((bi * 47 + 31) % 200);
                var buildY = gy - bh - 170;
                ctx.fillStyle = '#1a1a2e';
                ctx.fillRect(bx, buildY, 80, bh);
                // Window grid (deterministic)
                for (var wy = 0; wy < bh - 10; wy += 18) {
                    for (var wx = 8; wx < 72; wx += 16) {
                        var winOn = ((bi * 7 + wy * 3 + wx * 11 + Math.floor(time * 0.1)) % 5) < 2;
                        if (winOn) {
                            ctx.fillStyle = 'rgba(255,200,60,' + (0.25 + ((bi + wy + wx) % 3) * 0.15) + ')';
                            ctx.fillRect(bx + wx, buildY + wy + 4, 7, 9);
                        }
                    }
                }
            }
            // Neon signs with pulsing glow
            ctx.shadowColor = s.accentColor; ctx.shadowBlur = 15;
            ctx.fillStyle = s.accentColor;
            ctx.globalAlpha = 0.4 + Math.sin(time * 3.5) * 0.2;
            ctx.fillRect(180, gy - 360, 85, 14);
            ctx.globalAlpha = 0.35 + Math.sin(time * 4.2 + 1) * 0.2;
            ctx.fillRect(680, gy - 290, 65, 12);
            ctx.globalAlpha = 0.3 + Math.sin(time * 2.8 + 2) * 0.15;
            ctx.fillRect(1020, gy - 320, 70, 13);
            ctx.shadowBlur = 0; ctx.globalAlpha = 1;
            break;

        case 'torches':
            // Pillars with detail
            for (var pd = 0; pd < 2; pd++) {
                var px = pd === 0 ? 25 : cw - 55;
                // Pillar gradient
                var pGrad = ctx.createLinearGradient(px, gy - 320, px + 30, gy);
                pGrad.addColorStop(0, '#5a4530'); pGrad.addColorStop(0.5, '#4a3520'); pGrad.addColorStop(1, '#3a2510');
                ctx.fillStyle = pGrad;
                ctx.fillRect(px, gy - 320, 30, 320);
                // Carvings
                ctx.strokeStyle = 'rgba(255,200,100,0.1)'; ctx.lineWidth = 1;
                for (var cv = 0; cv < 6; cv++) { ctx.beginPath(); ctx.moveTo(px + 5, gy - 280 + cv * 45); ctx.lineTo(px + 25, gy - 280 + cv * 45); ctx.stroke(); }
                // Capital
                ctx.fillStyle = '#5a4530';
                ctx.fillRect(px - 5, gy - 325, 40, 12);
            }
            // Torches with fire
            for (var ti = 0; ti < 4; ti++) {
                var tx = 90 + ti * 340;
                ctx.fillStyle = '#5d4037'; ctx.fillRect(tx - 3, gy - 200, 6, 200);
                // Torch bracket
                ctx.fillStyle = '#6d5040'; ctx.fillRect(tx - 8, gy - 205, 16, 8);
                // Fire layers
                for (var fl = 0; fl < 4; fl++) {
                    var fAlpha = (0.5 - fl * 0.1) + Math.sin(time * (8 + fl * 2) + ti * 2) * 0.15;
                    var fR = (14 - fl * 3) + Math.sin(time * (6 + fl) + ti) * 3;
                    var fColors = ['rgba(255,80,20,' + fAlpha + ')', 'rgba(255,150,30,' + fAlpha + ')', 'rgba(255,220,80,' + fAlpha + ')', 'rgba(255,255,200,' + fAlpha + ')'];
                    ctx.fillStyle = fColors[fl];
                    ctx.beginPath(); ctx.ellipse(tx, gy - 212 - fl * 4, fR, fR * 1.4, 0, 0, Math.PI * 2); ctx.fill();
                }
            }
            break;
    }

    // Ground with gradient
    var gGrad = ctx.createLinearGradient(0, gy, 0, ch);
    gGrad.addColorStop(0, s.groundColor);
    gGrad.addColorStop(1, '#000');
    ctx.fillStyle = gGrad;
    ctx.fillRect(0, gy, cw, ch - gy);

    // Ground line (accent glow)
    ctx.strokeStyle = s.accentColor;
    ctx.lineWidth = 2;
    ctx.shadowColor = s.accentColor;
    ctx.shadowBlur = 8;
    ctx.globalAlpha = 0.55;
    ctx.beginPath(); ctx.moveTo(sl, gy); ctx.lineTo(sr, gy); ctx.stroke();
    ctx.shadowBlur = 0;
    ctx.globalAlpha = 1;

    // Stage walls with vignette gradient
    var wGrad1 = ctx.createLinearGradient(0, 0, sl + 20, 0);
    wGrad1.addColorStop(0, s.wallColor); wGrad1.addColorStop(0.7, s.wallColor); wGrad1.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = wGrad1;
    ctx.fillRect(0, 0, sl + 20, ch);
    var wGrad2 = ctx.createLinearGradient(sr - 20, 0, cw, 0);
    wGrad2.addColorStop(0, 'rgba(0,0,0,0)'); wGrad2.addColorStop(0.3, s.wallColor); wGrad2.addColorStop(1, s.wallColor);
    ctx.fillStyle = wGrad2;
    ctx.fillRect(sr - 20, 0, cw - sr + 20, ch);

    // Top vignette
    var topV = ctx.createLinearGradient(0, 0, 0, 60);
    topV.addColorStop(0, 'rgba(0,0,0,0.35)'); topV.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = topV;
    ctx.fillRect(0, 0, cw, 60);
}

// === HUD RENDERER ===
function renderHUD(ctx, fighter1, fighter2, timer, round, p1Wins, p2Wins) {
    var hudY = 16;
    var barWidth = 420;
    var barHeight = 26;
    var meterHeight = 7;
    var cw = CONFIG.CANVAS_WIDTH;
    var halfW = cw / 2;

    // ── Health bar helper ──
    function drawHealthBar(x, y, w, h, pct, glowColor, flipDir) {
        // Background
        ctx.fillStyle = '#0a0a0f';
        ctx.fillRect(x - 3, y - 3, w + 6, h + 6);
        // Inner dark
        ctx.fillStyle = '#1a1a22';
        ctx.fillRect(x, y, w, h);
        // Health gradient
        var fillW = pct * w;
        if (fillW > 0) {
            var barColor1 = pct > 0.5 ? '#22dd66' : pct > 0.25 ? '#ddaa22' : '#dd3333';
            var barColor2 = pct > 0.5 ? '#11aa44' : pct > 0.25 ? '#aa7711' : '#aa1111';
            var grad = ctx.createLinearGradient(x, y, x, y + h);
            grad.addColorStop(0, barColor1);
            grad.addColorStop(0.5, barColor2);
            grad.addColorStop(1, barColor1);
            ctx.fillStyle = grad;
            if (flipDir) {
                ctx.fillRect(x + w - fillW, y, fillW, h);
            } else {
                ctx.fillRect(x, y, fillW, h);
            }
            // Highlight streak at top
            ctx.globalAlpha = 0.25;
            ctx.fillStyle = '#fff';
            if (flipDir) {
                ctx.fillRect(x + w - fillW, y + 1, fillW, 3);
            } else {
                ctx.fillRect(x, y + 1, fillW, 3);
            }
            ctx.globalAlpha = 1;
            // Glow on edge when low
            if (pct < 0.25) {
                ctx.shadowColor = '#ff2222';
                ctx.shadowBlur = 12;
                ctx.fillStyle = 'rgba(255,30,30,0.15)';
                ctx.fillRect(x, y, w, h);
                ctx.shadowBlur = 0;
            }
        }
        // Border (bevelled)
        ctx.strokeStyle = '#555';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(x - 1, y - 1, w + 2, h + 2);
        ctx.strokeStyle = '#222';
        ctx.lineWidth = 1;
        ctx.strokeRect(x - 2.5, y - 2.5, w + 5, h + 5);
    }

    // ── Special meter helper ──
    function drawMeter(x, y, w, h, pct, glow, flipDir) {
        ctx.fillStyle = '#08080f';
        ctx.fillRect(x - 1, y - 1, w + 2, h + 2);
        ctx.fillStyle = '#111';
        ctx.fillRect(x, y, w, h);
        var mW = pct * w;
        if (mW > 0) {
            var ready = pct >= 0.5;
            var mGrad = ctx.createLinearGradient(x, y, x, y + h);
            mGrad.addColorStop(0, ready ? glow : '#444');
            mGrad.addColorStop(1, ready ? glow : '#333');
            ctx.fillStyle = mGrad;
            if (flipDir) ctx.fillRect(x + w - mW, y, mW, h);
            else ctx.fillRect(x, y, mW, h);
            if (ready) {
                ctx.shadowColor = glow;
                ctx.shadowBlur = 6;
                ctx.fillStyle = 'rgba(255,255,255,0.1)';
                ctx.fillRect(x, y, w, h);
                ctx.shadowBlur = 0;
            }
        }
    }

    // ── Bars ──
    var p1BarX = 55;
    var p2BarX = cw - 55 - barWidth;
    var p1Pct = fighter1.health / fighter1.maxHealth;
    var p2Pct = fighter2.health / fighter2.maxHealth;
    drawHealthBar(p1BarX, hudY, barWidth, barHeight, p1Pct, fighter1.character.colors.glow, false);
    drawHealthBar(p2BarX, hudY, barWidth, barHeight, p2Pct, fighter2.character.colors.glow, true);

    // ── Meters ──
    var meterY = hudY + barHeight + 5;
    drawMeter(p1BarX, meterY, barWidth, meterHeight, fighter1.specialMeter / CONFIG.SPECIAL_METER_MAX, fighter1.character.colors.glow, false);
    drawMeter(p2BarX, meterY, barWidth, meterHeight, fighter2.specialMeter / CONFIG.SPECIAL_METER_MAX, fighter2.character.colors.glow, true);

    // ── Names ──
    ctx.font = 'bold 17px "Orbitron", "Rajdhani", sans-serif';
    ctx.textAlign = 'left';
    ctx.fillStyle = '#fff';
    ctx.shadowColor = 'rgba(0,0,0,0.6)';
    ctx.shadowBlur = 4;
    ctx.fillText(fighter1.character.name.toUpperCase(), p1BarX, meterY + meterHeight + 18);
    ctx.textAlign = 'right';
    ctx.fillText(fighter2.character.name.toUpperCase(), p2BarX + barWidth, meterY + meterHeight + 18);
    ctx.shadowBlur = 0;

    // ── Timer ──
    ctx.textAlign = 'center';
    // Timer panel background
    ctx.fillStyle = 'rgba(10,10,18,0.85)';
    ctx.beginPath();
    ctx.moveTo(halfW - 42, hudY - 6);
    ctx.lineTo(halfW + 42, hudY - 6);
    ctx.lineTo(halfW + 36, hudY + 50);
    ctx.lineTo(halfW - 36, hudY + 50);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = '#444';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    // Timer text
    ctx.font = 'bold 44px "Orbitron", "Rajdhani", sans-serif';
    var timeVal = Math.ceil(timer);
    ctx.fillStyle = timer <= 10 ? '#ff3333' : '#f0f0f0';
    if (timer <= 10) { ctx.shadowColor = '#ff0000'; ctx.shadowBlur = 12; }
    ctx.fillText(timeVal.toString(), halfW, hudY + 40);
    ctx.shadowBlur = 0;

    // Round text
    ctx.font = '12px "Orbitron", "Rajdhani", sans-serif';
    ctx.fillStyle = '#888';
    ctx.fillText('ROUND ' + round, halfW, hudY + 55);

    // ── Win dots ──
    for (var i = 0; i < CONFIG.ROUNDS_TO_WIN; i++) {
        // P1
        ctx.fillStyle = i < p1Wins ? '#ffd700' : '#2a2a2a';
        ctx.beginPath(); ctx.arc(halfW - 28 - i * 16, hudY + 67, 5, 0, Math.PI * 2); ctx.fill();
        if (i < p1Wins) { ctx.strokeStyle = '#ffaa00'; ctx.lineWidth = 1; ctx.stroke(); }
        // P2
        ctx.fillStyle = i < p2Wins ? '#ffd700' : '#2a2a2a';
        ctx.beginPath(); ctx.arc(halfW + 28 + i * 16, hudY + 67, 5, 0, Math.PI * 2); ctx.fill();
        if (i < p2Wins) { ctx.strokeStyle = '#ffaa00'; ctx.lineWidth = 1; ctx.stroke(); }
    }
}


// === GAME ENGINE ===
function GameEngine(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.input = new InputManager();
    this.particles = new ParticleSystem();

    this.fighter1 = null;
    this.fighter2 = null;
    this.ai = null;
    this.gameMode = 'vs_ai';  // vs_ai, vs_local, vs_online
    this.difficulty = 'medium';

    this.gameState = 'idle';  // idle, countdown, fighting, round_end, match_end
    this.roundTimer = CONFIG.ROUND_TIME;
    this.currentRound = 1;
    this.p1Wins = 0;
    this.p2Wins = 0;
    this.countdownTimer = 0;
    this.countdownText = '';
    this.roundEndTimer = 0;
    this.stageIndex = 0;

    this.hitstopTimer = 0;
    this.screenShakeX = 0;
    this.screenShakeY = 0;
    this.impactFlash = 0;
    this.koSlowTimer = 0;

    this.gameTime = 0;
    this.lastTime = 0;
    this.running = false;

    this.matchStats = {
        p1Damage: 0,
        p2Damage: 0,
        p1Combos: 0,
        p2Combos: 0,
        p1MaxCombo: 0,
        p2MaxCombo: 0,
        perfectRounds: 0,
        startTime: 0
    };

    this.p1GamepadIndex = null;
    this.p2GamepadIndex = null;

    this.onMatchEnd = null;  // Callback
    this.onRoundEnd = null;
}

GameEngine.prototype.setupMatch = function(p1Char, p1Weapon, p2Char, p2Weapon, mode, difficulty, stage) {
    this.fighter1 = new Fighter(300, CONFIG.GROUND_Y, true, p1Char, p1Weapon, true);
    this.fighter2 = new Fighter(CONFIG.CANVAS_WIDTH - 300, CONFIG.GROUND_Y, false, p2Char, p2Weapon, mode !== 'vs_ai');

    this.gameMode = mode || 'vs_ai';
    this.difficulty = difficulty || 'medium';
    this.ai = this.gameMode === 'vs_ai' ? new AIController(this.difficulty) : null;
    this.stageIndex = stage || 0;

    this.currentRound = 1;
    this.p1Wins = 0;
    this.p2Wins = 0;

    this.matchStats = {
        p1Damage: 0, p2Damage: 0,
        p1Combos: 0, p2Combos: 0,
        p1MaxCombo: 0, p2MaxCombo: 0,
        perfectRounds: 0, startTime: Date.now()
    };

    this.startRound();
};

GameEngine.prototype.startRound = function() {
    this.fighter1.reset(300, CONFIG.GROUND_Y, true);
    this.fighter2.reset(CONFIG.CANVAS_WIDTH - 300, CONFIG.GROUND_Y, false);
    this.particles.clear();
    this.roundTimer = CONFIG.ROUND_TIME;
    this.gameState = 'countdown';
    this.countdownTimer = 3;
    this.countdownText = '3';
    this.hitstopTimer = 0;
    this.screenShakeX = 0;
    this.screenShakeY = 0;
    this.impactFlash = 0;
    this.koSlowTimer = 0;
};

GameEngine.prototype.start = function() {
    if (this.running) return;
    this.running = true;
    this.lastTime = performance.now();
    var self = this;
    function loop(timestamp) {
        if (!self.running) return;
        var dt = (timestamp - self.lastTime) / 1000;
        if (dt > 0.05) dt = 0.05;  // Cap delta time
        self.lastTime = timestamp;
        self.gameTime += dt;
        self.update(dt);
        self.input.postUpdate(); // snapshot keys/buttons for next frame's just-pressed detection
        self.render();
        requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
};

GameEngine.prototype.stop = function() {
    this.running = false;
};

GameEngine.prototype.update = function(dt) {
    this.input.update();

    // Paused state — skip all game logic
    if (this.gameState === 'paused') {
        return;
    }

    // Impact flash decay
    if (this.impactFlash > 0) this.impactFlash -= dt;

    // KO slow-motion: reduce effective dt during ko slo-mo
    if (this.koSlowTimer > 0) {
        this.koSlowTimer -= dt;
        dt *= 0.25; // quarter speed
    }

    // Hitstop
    if (this.hitstopTimer > 0) {
        this.hitstopTimer -= dt;
        this.particles.update(dt); // still update particles during hitstop for visual polish
        return;
    }

    // Screen shake decay
    this.screenShakeX *= CONFIG.SCREEN_SHAKE_DECAY;
    this.screenShakeY *= CONFIG.SCREEN_SHAKE_DECAY;

    this.particles.update(dt);

    switch (this.gameState) {
        case 'countdown':
            var prevText = this.countdownText;
            this.countdownTimer -= dt;
            if (this.countdownTimer > 2) this.countdownText = '3';
            else if (this.countdownTimer > 1) this.countdownText = '2';
            else if (this.countdownTimer > 0) this.countdownText = '1';
            else {
                this.countdownText = 'FIGHT!';
                if (this.countdownTimer < -0.5) {
                    this.gameState = 'fighting';
                    if (window.GameAudio) GameAudio.startMusic('fight');
                }
            }
            // Play countdown beep on text change
            if (window.GameAudio && this.countdownText !== prevText) {
                if (this.countdownText === 'FIGHT!') GameAudio.sfx.roundStart();
                else GameAudio.sfx.countdown(parseInt(this.countdownText));
            }
            break;

        case 'fighting':
            // Timer
            this.roundTimer -= dt;
            if (this.roundTimer <= 0) {
                this.roundTimer = 0;
                this._endRound();
                break;
            }

            // Player 1 input
            var p1Input = this.input.getPlayerInput(0, KEYBOARD_P1, this.p1GamepadIndex);
            this.fighter1.update(dt, p1Input);

            // Player 2 / AI input
            var p2Input;
            if (this.gameMode === 'vs_ai') {
                p2Input = this.ai.getInput(this.fighter2, this.fighter1, dt);
            } else {
                p2Input = this.input.getPlayerInput(1, KEYBOARD_P2, this.p2GamepadIndex);
            }
            this.fighter2.update(dt, p2Input);

            // Auto face opponent
            if (this.fighter1.state !== 'attacking' && this.fighter1.state !== 'special') {
                this.fighter1.facingRight = this.fighter2.x > this.fighter1.x;
            }
            if (this.fighter2.state !== 'attacking' && this.fighter2.state !== 'special') {
                this.fighter2.facingRight = this.fighter1.x > this.fighter2.x;
            }

            // Push apart if overlapping
            this._pushFightersApart();

            // Collision detection
            this._checkAttackCollisions(this.fighter1, this.fighter2);
            this._checkAttackCollisions(this.fighter2, this.fighter1);

            // Check KO
            if (this.fighter1.isKO || this.fighter2.isKO) {
                this._endRound();
            }
            break;

        case 'round_end':
            this.roundEndTimer -= dt;
            this.fighter1.update(dt, null);
            this.fighter2.update(dt, null);
            if (this.roundEndTimer <= 0) {
                // Check match end
                if (this.p1Wins >= CONFIG.ROUNDS_TO_WIN || this.p2Wins >= CONFIG.ROUNDS_TO_WIN) {
                    this.gameState = 'match_end';
                    if (window.GameAudio) {
                        GameAudio.stopMusic();
                        GameAudio.sfx.matchEnd();
                    }
                    if (this.onMatchEnd) {
                        var winner = this.p1Wins >= CONFIG.ROUNDS_TO_WIN ? 1 : 2;
                        this.onMatchEnd(winner, this.matchStats);
                    }
                } else {
                    this.currentRound++;
                    this.startRound();
                }
            }
            break;

        case 'match_end':
            this.fighter1.update(dt, null);
            this.fighter2.update(dt, null);
            break;
    }
};

GameEngine.prototype._pushFightersApart = function() {
    var f1 = this.fighter1;
    var f2 = this.fighter2;
    var minDist = (f1.width + f2.width) / 2;
    var dist = Math.abs(f1.x - f2.x);
    if (dist < minDist) {
        var overlap = (minDist - dist) / 2;
        if (f1.x < f2.x) {
            f1.x -= overlap;
            f2.x += overlap;
        } else {
            f1.x += overlap;
            f2.x -= overlap;
        }
    }
};

GameEngine.prototype._checkAttackCollisions = function(attacker, defender) {
    var atkBox = attacker.getAttackBox();
    if (!atkBox) return;

    var defBox = defender.getHitbox();

    // AABB collision
    if (atkBox.x < defBox.x + defBox.w &&
        atkBox.x + atkBox.w > defBox.x &&
        atkBox.y < defBox.y + defBox.h &&
        atkBox.y + atkBox.h > defBox.y) {

        attacker.attackHasHit = true;
        var damage = 0;
        var kbX = 0;
        var kbY = 0;
        var type = attacker.currentAttackType;

        if (type === 'light') {
            damage = attacker.weapon.lightDamage;
            kbX = CONFIG.KNOCKBACK_LIGHT * (attacker.facingRight ? 1 : -1);
        } else if (type === 'heavy') {
            damage = attacker.weapon.heavyDamage;
            kbX = CONFIG.KNOCKBACK_HEAVY * (attacker.facingRight ? 1 : -1);
            kbY = CONFIG.LAUNCH_FORCE * 0.3;
        } else if (type === 'special') {
            damage = attacker.character.specialDamage;
            kbX = CONFIG.KNOCKBACK_SPECIAL * (attacker.facingRight ? 1 : -1);
            kbY = CONFIG.LAUNCH_FORCE * 0.5;

            // Apply character-specific effects
            if (attacker.character.uniqueFeature === 'poison') {
                defender.applyPoison(attacker.character.poisonDPS, attacker.character.poisonDuration);
            }
            if (attacker.character.uniqueFeature === 'ice') {
                defender.applyFreeze(attacker.character.freezeDuration);
            }
        } else if (type === 'grab') {
            damage = 12;
            kbX = CONFIG.KNOCKBACK_HEAVY * 1.2 * (attacker.facingRight ? 1 : -1);
            kbY = CONFIG.LAUNCH_FORCE;
        }

        // Combo scaling
        attacker.comboCount++;
        attacker.comboTimer = CONFIG.COMBO_WINDOW;
        var comboScale = Math.max(0.3, 1 - (attacker.comboCount - 1) * 0.1);
        damage *= comboScale;
        attacker.comboDamage += damage;

        // Track stats
        if (attacker === this.fighter1) {
            this.matchStats.p1Damage += damage;
            this.matchStats.p1Combos++;
            if (attacker.comboCount > this.matchStats.p1MaxCombo) this.matchStats.p1MaxCombo = attacker.comboCount;
        } else {
            this.matchStats.p2Damage += damage;
            this.matchStats.p2Combos++;
            if (attacker.comboCount > this.matchStats.p2MaxCombo) this.matchStats.p2MaxCombo = attacker.comboCount;
        }

        defender.takeDamage(damage, kbX, kbY, attacker);

        // Hit SFX
        if (window.GameAudio) {
            if (type === 'special') GameAudio.sfx.specialHit();
            else if (type === 'heavy') GameAudio.sfx.heavyHit();
            else if (type === 'grab') GameAudio.sfx.grabHit();
            else GameAudio.sfx.lightHit();
            // KO boom
            if (defender.health <= 0) {
                setTimeout(function() { GameAudio.sfx.ko(); }, 100);
            }
        }

        // Effects — premium impact
        var isHeavyHit = type === 'heavy' || type === 'special';
        var isCritCombo = attacker.comboCount >= 5;
        this.hitstopTimer = (isHeavyHit ? CONFIG.HITSTOP_DURATION * 1.8 : CONFIG.HITSTOP_DURATION) / 1000;
        var shakeMult = isHeavyHit ? 2.5 : (isCritCombo ? 1.8 : 1);
        this.screenShakeX = randomRange(-8, 8) * shakeMult;
        this.screenShakeY = randomRange(-5, 5) * shakeMult;
        // Impact flash (white overlay duration in seconds)
        this.impactFlash = isHeavyHit ? 0.08 : 0.04;
        // KO slow-motion
        if (defender.health <= 0) { this.koSlowTimer = 0.6; }

        // Hit particles — more on heavy
        var hitX = (attacker.x + defender.x) / 2;
        var hitY = defender.y - defender.height / 2;
        var pCount = isHeavyHit ? 22 : 10;
        this.particles.emit(hitX, hitY, pCount, {
            color: attacker.character.colors.glow,
            minVX: -250, maxVX: 250,
            minVY: -350, maxVY: -50,
            minSize: 2, maxSize: isHeavyHit ? 10 : 5,
            minLife: 0.2, maxLife: isHeavyHit ? 0.7 : 0.45
        });

        // White flash burst
        this.particles.emit(hitX, hitY, isHeavyHit ? 8 : 4, {
            color: '#ffffff',
            minVX: -120, maxVX: 120,
            minVY: -180, maxVY: -40,
            minSize: 3, maxSize: 8,
            minLife: 0.08, maxLife: 0.2
        });

        // Spark ring on heavy
        if (isHeavyHit) {
            this.particles.emit(hitX, hitY, 12, {
                color: '#ffdd44',
                minVX: -300, maxVX: 300,
                minVY: -300, maxVY: 300,
                minSize: 1, maxSize: 3,
                minLife: 0.15, maxLife: 0.35
            });
        }
    }
};

GameEngine.prototype._endRound = function() {
    this.gameState = 'round_end';
    this.roundEndTimer = 2.5;
    if (window.GameAudio) GameAudio.sfx.roundEnd();

    var winner;
    if (this.fighter1.isKO) {
        this.p2Wins++;
        winner = 2;
        this.fighter2.winPose = true;
    } else if (this.fighter2.isKO) {
        this.p1Wins++;
        winner = 1;
        this.fighter1.winPose = true;
        if (this.fighter1.health >= 100) this.matchStats.perfectRounds++;
    } else {
        // Time out - whoever has more health wins
        if (this.fighter1.health >= this.fighter2.health) {
            this.p1Wins++;
            winner = 1;
            this.fighter1.winPose = true;
        } else {
            this.p2Wins++;
            winner = 2;
            this.fighter2.winPose = true;
        }
    }

    if (this.onRoundEnd) {
        this.onRoundEnd(winner, this.currentRound);
    }
};

GameEngine.prototype.render = function() {
    var ctx = this.ctx;
    var w = this.canvas.width;
    var h = this.canvas.height;

    ctx.save();

    // Screen shake
    if (Math.abs(this.screenShakeX) > 0.5 || Math.abs(this.screenShakeY) > 0.5) {
        ctx.translate(this.screenShakeX, this.screenShakeY);
    }

    // Draw stage
    renderStage(ctx, this.stageIndex, this.gameTime);

    // Draw fighters
    if (this.fighter1) this.fighter1.render(ctx);
    if (this.fighter2) this.fighter2.render(ctx);

    // Particles
    this.particles.render(ctx);

    // HUD
    if (this.fighter1 && this.fighter2) {
        renderHUD(ctx, this.fighter1, this.fighter2, this.roundTimer, this.currentRound, this.p1Wins, this.p2Wins);
    }

    // Countdown overlay (dramatic)
    if (this.gameState === 'countdown') {
        ctx.fillStyle = 'rgba(0,0,0,0.45)';
        ctx.fillRect(0, 0, w, h);
        ctx.textAlign = 'center';
        var isFight = this.countdownText === 'FIGHT!';
        ctx.font = 'bold ' + (isFight ? '110' : '100') + 'px "Orbitron", "Rajdhani", sans-serif';
        ctx.fillStyle = isFight ? '#ff3333' : '#f0f0f0';
        ctx.shadowColor = isFight ? '#ff0000' : '#4488ff';
        ctx.shadowBlur = isFight ? 35 : 20;
        ctx.fillText(this.countdownText, w / 2, h / 2 + 35);
        // Double-shadow for depth
        ctx.shadowColor = isFight ? '#880000' : '#002244';
        ctx.shadowBlur = 60;
        ctx.fillText(this.countdownText, w / 2, h / 2 + 35);
        ctx.shadowBlur = 0;
        // Accent line
        ctx.strokeStyle = isFight ? '#ff4444' : '#ffffff';
        ctx.lineWidth = 2;
        ctx.globalAlpha = 0.5;
        ctx.beginPath(); ctx.moveTo(w * 0.3, h / 2 + 55); ctx.lineTo(w * 0.7, h / 2 + 55); ctx.stroke();
        ctx.globalAlpha = 1;
    }

    // Round end overlay (dramatic)
    if (this.gameState === 'round_end') {
        ctx.fillStyle = 'rgba(0,0,0,0.55)';
        ctx.fillRect(0, 0, w, h);
        ctx.textAlign = 'center';
        var winnerName = this.fighter2.isKO ? this.fighter1.character.name : this.fighter2.character.name;
        var winnerGlow = this.fighter2.isKO ? this.fighter1.character.colors.glow : this.fighter2.character.colors.glow;
        // Winner name
        ctx.font = 'bold 62px "Orbitron", "Rajdhani", sans-serif';
        ctx.fillStyle = '#ffd700';
        ctx.shadowColor = winnerGlow;
        ctx.shadowBlur = 25;
        ctx.fillText(winnerName.toUpperCase(), w / 2, h / 2);
        ctx.shadowBlur = 0;
        // "WINS" subtitle
        ctx.font = 'bold 28px "Rajdhani", sans-serif';
        ctx.fillStyle = '#ddd';
        ctx.fillText('WINS THE ROUND', w / 2, h / 2 + 35);
    }

    // Match end overlay (premium results screen)
    if (this.gameState === 'match_end') {
        ctx.fillStyle = 'rgba(0,0,0,0.75)';
        ctx.fillRect(0, 0, w, h);
        ctx.textAlign = 'center';

        var matchWinner = this.p1Wins >= CONFIG.ROUNDS_TO_WIN ? this.fighter1 : this.fighter2;

        // Decorative line
        ctx.strokeStyle = '#ffd700';
        ctx.lineWidth = 1.5;
        ctx.globalAlpha = 0.4;
        ctx.beginPath(); ctx.moveTo(w * 0.25, h / 2 - 95); ctx.lineTo(w * 0.75, h / 2 - 95); ctx.stroke();
        ctx.globalAlpha = 1;

        ctx.font = 'bold 30px "Orbitron", "Rajdhani", sans-serif';
        ctx.fillStyle = '#999';
        ctx.fillText('MATCH OVER', w / 2, h / 2 - 75);

        ctx.font = 'bold 68px "Orbitron", "Rajdhani", sans-serif';
        ctx.fillStyle = '#ffd700';
        ctx.shadowColor = matchWinner.character.colors.glow;
        ctx.shadowBlur = 30;
        ctx.fillText(matchWinner.character.name.toUpperCase(), w / 2, h / 2 - 10);
        ctx.shadowBlur = 0;

        ctx.font = 'bold 26px "Rajdhani", sans-serif';
        ctx.fillStyle = '#eee';
        ctx.fillText('WINS!', w / 2, h / 2 + 22);

        ctx.font = '22px "Rajdhani", sans-serif';
        ctx.fillStyle = '#aaa';
        ctx.fillText(this.p1Wins + ' \u2014 ' + this.p2Wins, w / 2, h / 2 + 50);

        // Decorative line
        ctx.strokeStyle = '#ffd700';
        ctx.lineWidth = 1.5;
        ctx.globalAlpha = 0.4;
        ctx.beginPath(); ctx.moveTo(w * 0.25, h / 2 + 65); ctx.lineTo(w * 0.75, h / 2 + 65); ctx.stroke();
        ctx.globalAlpha = 1;

        ctx.font = '18px "Rajdhani", sans-serif';
        ctx.fillStyle = '#666';
        ctx.fillText('Press ENTER or START to continue', w / 2, h / 2 + 85);
    }

    // Paused overlay
    if (this.gameState === 'paused') {
        ctx.fillStyle = 'rgba(0,0,0,0.5)';
        ctx.fillRect(0, 0, w, h);
        ctx.textAlign = 'center';
        ctx.font = 'bold 48px "Orbitron", "Rajdhani", sans-serif';
        ctx.fillStyle = '#ffd700';
        ctx.shadowColor = '#ff8800';
        ctx.shadowBlur = 15;
        ctx.fillText('PAUSED', w / 2, h / 2 - 10);
        ctx.shadowBlur = 0;
        ctx.font = '18px "Rajdhani", sans-serif';
        ctx.fillStyle = '#aaa';
        ctx.fillText('Press F1 or close the controls panel to resume', w / 2, h / 2 + 30);
    }

    // Impact flash overlay (white flash on heavy hit)
    if (this.impactFlash > 0) {
        ctx.fillStyle = 'rgba(255,255,255,' + Math.min(this.impactFlash * 8, 0.45) + ')';
        ctx.fillRect(0, 0, w, h);
    }

    ctx.restore();
};
