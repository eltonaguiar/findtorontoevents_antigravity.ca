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
    // Copy current keys to prev for just-pressed detection
    var k;
    for (k in this.keys) {
        this.prevKeys[k] = this.keys[k];
    }
    // Poll gamepads
    var rawPads = navigator.getGamepads ? navigator.getGamepads() : [];
    this.gamepads = [];
    for (var i = 0; i < rawPads.length; i++) {
        if (rawPads[i]) this.gamepads.push(rawPads[i]);
    }
    // Store prev button states
    for (var g = 0; g < this.gamepads.length; g++) {
        var padId = g;
        if (!this.prevGamepadButtons[padId]) this.prevGamepadButtons[padId] = {};
        var pad = this.gamepads[g];
        for (var b = 0; b < pad.buttons.length; b++) {
            this.prevGamepadButtons[padId][b] = pad.buttons[b].pressed;
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

    this.width = this.character.body.shoulderW + 10;
    this.height = this.character.body.headR * 2 + this.character.body.torsoH + this.character.body.legLen + 10;

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
    } else {
        this.hitStun = 0.3;
        this.knockbackX = knockbackX;
        this.knockbackY = knockbackY;
        this.velY = knockbackY;
        this.state = 'hit';
        this.stateTime = 0;
        this.attackPhase = 'none';
        this.attackHitActive = false;
        this.hurtFlash = 0.15;
    }

    // Special meter gain
    this.specialMeter = Math.min(CONFIG.SPECIAL_METER_MAX, this.specialMeter + CONFIG.METER_GAIN_TAKE);
    if (attacker) {
        attacker.specialMeter = Math.min(CONFIG.SPECIAL_METER_MAX, attacker.specialMeter + CONFIG.METER_GAIN_DEAL);
    }

    // Drake rage check
    if (this.character.rageMode && this.health < 30) {
        this.rageActive = true;
    }

    if (this.health <= 0) {
        this.isKO = true;
        this.state = 'ko';
        this.stateTime = 0;
        this.velY = -300;
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
        } else if (input.up && !this.grounded && this.canDoubleJump && !this.usedDoubleJump) {
            this.velY = CONFIG.DOUBLE_JUMP_FORCE * this.character.jumpForce;
            this.usedDoubleJump = true;
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
    if (this.y >= CONFIG.GROUND_Y) {
        this.y = CONFIG.GROUND_Y;
        this.velY = 0;
        this.grounded = true;
        this.usedDoubleJump = false;
        if (this.state === 'jump' || this.state === 'hit') {
            this.state = 'idle';
        }
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

    // Sky gradient
    var grad = ctx.createLinearGradient(0, 0, 0, CONFIG.CANVAS_HEIGHT);
    grad.addColorStop(0, s.skyColors[0]);
    grad.addColorStop(1, s.skyColors[1]);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, CONFIG.CANVAS_WIDTH, CONFIG.CANVAS_HEIGHT);

    // Stage features
    switch (s.features) {
        case 'lanterns':
            for (var i = 0; i < 5; i++) {
                var lx = 150 + i * 250;
                ctx.fillStyle = 'rgba(255,100,30,0.15)';
                ctx.beginPath();
                ctx.arc(lx, 100, 20 + Math.sin(time * 2 + i) * 3, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = '#4a0e0e';
                ctx.fillRect(lx - 8, 85, 16, 25);
            }
            break;

        case 'crowd':
            for (var ci = 0; ci < 40; ci++) {
                var cx = 30 + ci * 32;
                var cy = 80 + Math.sin(time * 3 + ci * 0.5) * 3;
                ctx.fillStyle = 'hsl(' + (ci * 37 % 360) + ',30%,25%)';
                ctx.beginPath();
                ctx.arc(cx, cy, 8, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillRect(cx - 5, cy + 8, 10, 15);
            }
            break;

        case 'cityscape':
            ctx.fillStyle = '#1a1a2e';
            for (var bi = 0; bi < 15; bi++) {
                var bx = bi * 95;
                var bh = 100 + (bi * 47 % 200);
                ctx.fillRect(bx, CONFIG.GROUND_Y - bh - 200, 80, bh);
                // Windows
                ctx.fillStyle = Math.random() > 0.7 ? '#ffcc00' : '#1a1a2e';
                for (var wy = 0; wy < bh - 10; wy += 20) {
                    for (var wx = 10; wx < 70; wx += 20) {
                        if (Math.random() > 0.5) {
                            ctx.fillStyle = 'rgba(255,200,50,' + (0.3 + Math.random() * 0.4) + ')';
                            ctx.fillRect(bx + wx, CONFIG.GROUND_Y - bh - 200 + wy + 5, 8, 10);
                        }
                    }
                }
                ctx.fillStyle = '#1a1a2e';
            }
            // Neon signs
            ctx.fillStyle = s.accentColor;
            ctx.globalAlpha = 0.3 + Math.sin(time * 4) * 0.2;
            ctx.fillRect(200, CONFIG.GROUND_Y - 350, 80, 15);
            ctx.fillRect(700, CONFIG.GROUND_Y - 280, 60, 12);
            ctx.globalAlpha = 1;
            break;

        case 'torches':
            for (var ti = 0; ti < 4; ti++) {
                var tx = 100 + ti * 350;
                // Torch pole
                ctx.fillStyle = '#5d4037';
                ctx.fillRect(tx - 3, CONFIG.GROUND_Y - 200, 6, 200);
                // Flame
                ctx.fillStyle = 'rgba(255,150,30,' + (0.6 + Math.sin(time * 8 + ti * 2) * 0.3) + ')';
                ctx.beginPath();
                ctx.arc(tx, CONFIG.GROUND_Y - 210, 12 + Math.sin(time * 6 + ti) * 4, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = 'rgba(255,220,100,' + (0.4 + Math.sin(time * 10 + ti * 3) * 0.2) + ')';
                ctx.beginPath();
                ctx.arc(tx, CONFIG.GROUND_Y - 215, 6 + Math.sin(time * 12 + ti) * 2, 0, Math.PI * 2);
                ctx.fill();
            }
            // Ancient pillars
            ctx.fillStyle = '#4a3520';
            ctx.fillRect(30, CONFIG.GROUND_Y - 300, 30, 300);
            ctx.fillRect(CONFIG.CANVAS_WIDTH - 60, CONFIG.GROUND_Y - 300, 30, 300);
            break;
    }

    // Ground
    ctx.fillStyle = s.groundColor;
    ctx.fillRect(0, CONFIG.GROUND_Y, CONFIG.CANVAS_WIDTH, CONFIG.CANVAS_HEIGHT - CONFIG.GROUND_Y);

    // Ground line
    ctx.strokeStyle = s.accentColor;
    ctx.lineWidth = 2;
    ctx.globalAlpha = 0.5;
    ctx.beginPath();
    ctx.moveTo(CONFIG.STAGE_LEFT, CONFIG.GROUND_Y);
    ctx.lineTo(CONFIG.STAGE_RIGHT, CONFIG.GROUND_Y);
    ctx.stroke();
    ctx.globalAlpha = 1;

    // Stage walls
    ctx.fillStyle = s.wallColor;
    ctx.fillRect(0, 0, CONFIG.STAGE_LEFT, CONFIG.CANVAS_HEIGHT);
    ctx.fillRect(CONFIG.STAGE_RIGHT, 0, CONFIG.CANVAS_WIDTH - CONFIG.STAGE_RIGHT, CONFIG.CANVAS_HEIGHT);
}

// === HUD RENDERER ===
function renderHUD(ctx, fighter1, fighter2, timer, round, p1Wins, p2Wins) {
    var hudY = 20;
    var barWidth = 400;
    var barHeight = 28;
    var meterHeight = 8;

    // P1 Health bar (left, fills right-to-left)
    var p1BarX = 60;
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(p1BarX - 2, hudY - 2, barWidth + 4, barHeight + 4);
    ctx.fillStyle = '#333';
    ctx.fillRect(p1BarX, hudY, barWidth, barHeight);
    var p1Width = (fighter1.health / fighter1.maxHealth) * barWidth;
    var p1Color = fighter1.health > 50 ? '#2ecc71' : fighter1.health > 25 ? '#f39c12' : '#e74c3c';
    ctx.fillStyle = p1Color;
    ctx.fillRect(p1BarX, hudY, p1Width, barHeight);

    // P2 Health bar (right, fills left-to-right)
    var p2BarX = CONFIG.CANVAS_WIDTH - 60 - barWidth;
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(p2BarX - 2, hudY - 2, barWidth + 4, barHeight + 4);
    ctx.fillStyle = '#333';
    ctx.fillRect(p2BarX, hudY, barWidth, barHeight);
    var p2Width = (fighter2.health / fighter2.maxHealth) * barWidth;
    var p2Color = fighter2.health > 50 ? '#2ecc71' : fighter2.health > 25 ? '#f39c12' : '#e74c3c';
    ctx.fillStyle = p2Color;
    ctx.fillRect(p2BarX + barWidth - p2Width, hudY, p2Width, barHeight);

    // Special meters
    var meterY = hudY + barHeight + 6;

    // P1 meter
    ctx.fillStyle = '#111';
    ctx.fillRect(p1BarX, meterY, barWidth, meterHeight);
    var p1Meter = (fighter1.specialMeter / CONFIG.SPECIAL_METER_MAX) * barWidth;
    ctx.fillStyle = fighter1.specialMeter >= 50 ? fighter1.character.colors.glow : '#555';
    ctx.fillRect(p1BarX, meterY, p1Meter, meterHeight);

    // P2 meter
    ctx.fillStyle = '#111';
    ctx.fillRect(p2BarX, meterY, barWidth, meterHeight);
    var p2Meter = (fighter2.specialMeter / CONFIG.SPECIAL_METER_MAX) * barWidth;
    ctx.fillStyle = fighter2.specialMeter >= 50 ? fighter2.character.colors.glow : '#555';
    ctx.fillRect(p2BarX + barWidth - p2Meter, meterY, p2Meter, meterHeight);

    // Names
    ctx.font = 'bold 16px "Rajdhani", sans-serif';
    ctx.fillStyle = '#fff';
    ctx.textAlign = 'left';
    ctx.fillText(fighter1.character.name.toUpperCase(), p1BarX, hudY + barHeight + meterHeight + 22);
    ctx.textAlign = 'right';
    ctx.fillText(fighter2.character.name.toUpperCase(), p2BarX + barWidth, hudY + barHeight + meterHeight + 22);

    // Timer
    ctx.textAlign = 'center';
    ctx.font = 'bold 42px "Rajdhani", sans-serif';
    ctx.fillStyle = timer <= 10 ? '#e74c3c' : '#ffffff';
    ctx.fillText(Math.ceil(timer).toString(), CONFIG.CANVAS_WIDTH / 2, hudY + 36);

    // Round indicator
    ctx.font = '14px "Rajdhani", sans-serif';
    ctx.fillStyle = '#aaa';
    ctx.fillText('ROUND ' + round, CONFIG.CANVAS_WIDTH / 2, hudY + 54);

    // Win dots
    for (var i = 0; i < CONFIG.ROUNDS_TO_WIN; i++) {
        ctx.fillStyle = i < p1Wins ? '#ffd700' : '#333';
        ctx.beginPath();
        ctx.arc(CONFIG.CANVAS_WIDTH / 2 - 30 - i * 18, hudY + 68, 5, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = i < p2Wins ? '#ffd700' : '#333';
        ctx.beginPath();
        ctx.arc(CONFIG.CANVAS_WIDTH / 2 + 30 + i * 18, hudY + 68, 5, 0, Math.PI * 2);
        ctx.fill();
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

    // Hitstop
    if (this.hitstopTimer > 0) {
        this.hitstopTimer -= dt;
        return;
    }

    // Screen shake decay
    this.screenShakeX *= CONFIG.SCREEN_SHAKE_DECAY;
    this.screenShakeY *= CONFIG.SCREEN_SHAKE_DECAY;

    this.particles.update(dt);

    switch (this.gameState) {
        case 'countdown':
            this.countdownTimer -= dt;
            if (this.countdownTimer > 2) this.countdownText = '3';
            else if (this.countdownTimer > 1) this.countdownText = '2';
            else if (this.countdownTimer > 0) this.countdownText = '1';
            else {
                this.countdownText = 'FIGHT!';
                if (this.countdownTimer < -0.5) {
                    this.gameState = 'fighting';
                }
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

        // Effects
        this.hitstopTimer = CONFIG.HITSTOP_DURATION / 1000;
        this.screenShakeX = randomRange(-8, 8) * (type === 'heavy' || type === 'special' ? 2 : 1);
        this.screenShakeY = randomRange(-5, 5) * (type === 'heavy' || type === 'special' ? 2 : 1);

        // Hit particles
        var hitX = (attacker.x + defender.x) / 2;
        var hitY = defender.y - defender.height / 2;
        this.particles.emit(hitX, hitY, type === 'heavy' ? 15 : 8, {
            color: attacker.character.colors.glow,
            minVX: -200, maxVX: 200,
            minVY: -300, maxVY: -50,
            minSize: 2, maxSize: type === 'heavy' ? 8 : 5,
            minLife: 0.2, maxLife: 0.5
        });

        // White flash particles
        this.particles.emit(hitX, hitY, 4, {
            color: '#ffffff',
            minVX: -100, maxVX: 100,
            minVY: -150, maxVY: -50,
            minSize: 3, maxSize: 6,
            minLife: 0.1, maxLife: 0.2
        });
    }
};

GameEngine.prototype._endRound = function() {
    this.gameState = 'round_end';
    this.roundEndTimer = 2.5;

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

    // Countdown overlay
    if (this.gameState === 'countdown') {
        ctx.fillStyle = 'rgba(0,0,0,0.4)';
        ctx.fillRect(0, 0, w, h);
        ctx.textAlign = 'center';
        ctx.font = 'bold 96px "Rajdhani", sans-serif';
        ctx.fillStyle = this.countdownText === 'FIGHT!' ? '#ff4444' : '#ffffff';
        ctx.shadowColor = this.countdownText === 'FIGHT!' ? '#ff0000' : '#000';
        ctx.shadowBlur = 20;
        ctx.fillText(this.countdownText, w / 2, h / 2 + 30);
        ctx.shadowBlur = 0;
    }

    // Round end overlay
    if (this.gameState === 'round_end') {
        ctx.fillStyle = 'rgba(0,0,0,0.5)';
        ctx.fillRect(0, 0, w, h);
        ctx.textAlign = 'center';
        ctx.font = 'bold 56px "Rajdhani", sans-serif';
        ctx.fillStyle = '#ffd700';
        ctx.shadowColor = '#ff8800';
        ctx.shadowBlur = 15;
        var winnerName = this.fighter2.isKO ? this.fighter1.character.name : this.fighter2.character.name;
        ctx.fillText(winnerName.toUpperCase() + ' WINS!', w / 2, h / 2 + 15);
        ctx.shadowBlur = 0;
    }

    // Match end overlay
    if (this.gameState === 'match_end') {
        ctx.fillStyle = 'rgba(0,0,0,0.7)';
        ctx.fillRect(0, 0, w, h);
        ctx.textAlign = 'center';

        var matchWinner = this.p1Wins >= CONFIG.ROUNDS_TO_WIN ? this.fighter1 : this.fighter2;
        var playerNum = this.p1Wins >= CONFIG.ROUNDS_TO_WIN ? 1 : 2;

        ctx.font = 'bold 36px "Rajdhani", sans-serif';
        ctx.fillStyle = '#aaa';
        ctx.fillText('MATCH OVER', w / 2, h / 2 - 80);

        ctx.font = 'bold 64px "Rajdhani", sans-serif';
        ctx.fillStyle = '#ffd700';
        ctx.shadowColor = '#ff8800';
        ctx.shadowBlur = 20;
        ctx.fillText(matchWinner.character.name.toUpperCase() + ' WINS!', w / 2, h / 2 - 20);
        ctx.shadowBlur = 0;

        ctx.font = '24px "Rajdhani", sans-serif';
        ctx.fillStyle = '#ccc';
        ctx.fillText(this.p1Wins + ' - ' + this.p2Wins, w / 2, h / 2 + 20);

        ctx.font = '20px "Rajdhani", sans-serif';
        ctx.fillStyle = '#888';
        ctx.fillText('Press ENTER or START to continue', w / 2, h / 2 + 60);
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

    ctx.restore();
};
