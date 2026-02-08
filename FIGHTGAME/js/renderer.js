/* ============================================================
   SHADOW ARENA — Enhanced Character Renderer
   Detailed per-character art: unique builds, outfits, faces, hair
   ============================================================ */

// Override the basic Fighter.render with the enhanced version
(function() {

// ── Shared drawing helpers ──────────────────────────────────
function curve(ctx, pts) {
    // Draw a closed bezier shape from an array of [x,y] points
    if (pts.length < 3) return;
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (var i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.closePath();
}

function ellipse(ctx, cx, cy, rx, ry) {
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
}

function roundRect(ctx, x, y, w, h, r) {
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
}

function drawMuscleArm(ctx, x, y, angle, length, thickness, skinColor, clothColor, hasGlove) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(degToRad(angle));
    // Upper arm (skin or cloth)
    var grad = ctx.createLinearGradient(0, 0, 0, length);
    grad.addColorStop(0, clothColor || skinColor);
    grad.addColorStop(0.4, clothColor || skinColor);
    grad.addColorStop(0.45, skinColor);
    grad.addColorStop(1, skinColor);
    ctx.fillStyle = clothColor ? grad : skinColor;
    // Curved arm shape
    ctx.beginPath();
    ctx.moveTo(-thickness * 0.5, 0);
    ctx.quadraticCurveTo(-thickness * 0.65, length * 0.4, -thickness * 0.4, length);
    ctx.lineTo(thickness * 0.4, length);
    ctx.quadraticCurveTo(thickness * 0.65, length * 0.4, thickness * 0.5, 0);
    ctx.closePath();
    ctx.fill();
    // Joint
    ctx.fillStyle = skinColor;
    ctx.beginPath();
    ctx.arc(0, 0, thickness * 0.45, 0, Math.PI * 2);
    ctx.fill();
    // Fist
    if (hasGlove) {
        ctx.fillStyle = clothColor || '#333';
        roundRect(ctx, -thickness * 0.45, length - 2, thickness * 0.9, thickness * 0.7, 3);
        ctx.fill();
    } else {
        ctx.fillStyle = skinColor;
        ctx.beginPath();
        ctx.arc(0, length, thickness * 0.35, 0, Math.PI * 2);
        ctx.fill();
    }
    ctx.restore();
}

function drawLeg(ctx, x, y, angle, length, thickness, pantsColor, shoeColor, bootHeight) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(degToRad(angle));
    // Pants/leg
    ctx.fillStyle = pantsColor;
    ctx.beginPath();
    ctx.moveTo(-thickness * 0.55, 0);
    ctx.quadraticCurveTo(-thickness * 0.7, length * 0.3, -thickness * 0.45, length);
    ctx.lineTo(thickness * 0.45, length);
    ctx.quadraticCurveTo(thickness * 0.7, length * 0.3, thickness * 0.55, 0);
    ctx.closePath();
    ctx.fill();
    // Knee line
    ctx.strokeStyle = 'rgba(0,0,0,0.15)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(-thickness * 0.3, length * 0.45);
    ctx.quadraticCurveTo(0, length * 0.42, thickness * 0.3, length * 0.45);
    ctx.stroke();
    // Boot/shoe
    var bh = bootHeight || 8;
    ctx.fillStyle = shoeColor || '#222';
    roundRect(ctx, -thickness * 0.5, length - bh + 2, thickness, bh + 2, 3);
    ctx.fill();
    // Joint
    ctx.fillStyle = pantsColor;
    ctx.beginPath();
    ctx.arc(0, 0, thickness * 0.4, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
}

function drawTorso(ctx, x, y, w, h, topColor, bottomColor, neckW) {
    // Heroic torso: wider shoulders tapering to waist
    var sw = w * 0.55;  // shoulder half-width
    var ww = w * 0.38;  // waist half-width
    var nw = neckW || w * 0.18;
    ctx.beginPath();
    ctx.moveTo(x - nw, y);                     // neck left
    ctx.lineTo(x - sw, y + h * 0.12);          // left shoulder
    ctx.quadraticCurveTo(x - sw - 2, y + h * 0.4, x - ww, y + h);  // left side
    ctx.lineTo(x + ww, y + h);                 // bottom
    ctx.quadraticCurveTo(x + sw + 2, y + h * 0.4, x + sw, y + h * 0.12);  // right side
    ctx.lineTo(x + nw, y);                     // neck right
    ctx.closePath();
    if (bottomColor) {
        var grad = ctx.createLinearGradient(x, y, x, y + h);
        grad.addColorStop(0, topColor);
        grad.addColorStop(1, bottomColor);
        ctx.fillStyle = grad;
    } else {
        ctx.fillStyle = topColor;
    }
    ctx.fill();
}

function drawHead(ctx, x, y, radius, skinColor) {
    // Slightly taller head shape (oval)
    ctx.fillStyle = skinColor;
    ctx.beginPath();
    ctx.ellipse(x, y, radius * 0.9, radius, 0, 0, Math.PI * 2);
    ctx.fill();
}

function drawEyes(ctx, x, y, radius, eyeColor, state, facingDir) {
    var ex = x + radius * 0.25;
    var ey = y - radius * 0.1;
    var ew = 3.5;
    var eh = state === 'hit' ? 1 : (state === 'ko' ? 0.5 : 2.5);
    // Eye whites
    ctx.fillStyle = '#fff';
    ctx.beginPath();
    ctx.ellipse(ex, ey, ew, eh, 0, 0, Math.PI * 2);
    ctx.fill();
    // Iris
    ctx.fillStyle = eyeColor;
    ctx.beginPath();
    ctx.ellipse(ex + 0.5, ey, ew * 0.6, eh * 0.7, 0, 0, Math.PI * 2);
    ctx.fill();
    // Pupil
    ctx.fillStyle = '#000';
    ctx.beginPath();
    ctx.arc(ex + 0.8, ey, 1, 0, Math.PI * 2);
    ctx.fill();
    // Brow
    ctx.strokeStyle = 'rgba(0,0,0,0.5)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    var browLift = state === 'hit' ? 1 : (state === 'attacking' || state === 'special' ? -2 : 0);
    ctx.moveTo(ex - ew - 1, ey - eh - 2 + browLift);
    ctx.quadraticCurveTo(ex, ey - eh - 4 + browLift, ex + ew + 2, ey - eh - 1 + browLift);
    ctx.stroke();
}

function drawMouth(ctx, x, y, radius, state) {
    var mx = x + radius * 0.15;
    var my = y + radius * 0.45;
    ctx.strokeStyle = 'rgba(0,0,0,0.5)';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    if (state === 'hit' || state === 'ko') {
        // Open mouth - pain
        ctx.ellipse(mx, my, 3, 2.5, 0, 0, Math.PI * 2);
        ctx.fillStyle = '#400';
        ctx.fill();
    } else if (state === 'attacking' || state === 'special') {
        // Battle cry
        ctx.ellipse(mx, my + 1, 3.5, 3, 0, 0, Math.PI * 2);
        ctx.fillStyle = '#300';
        ctx.fill();
    } else if (state === 'taunt') {
        // Smirk
        ctx.moveTo(mx - 3, my);
        ctx.quadraticCurveTo(mx, my + 3, mx + 4, my - 1);
        ctx.stroke();
    } else {
        // Neutral/determined
        ctx.moveTo(mx - 3, my);
        ctx.lineTo(mx + 3, my);
        ctx.stroke();
    }
}


// ── Per-Character Renderers ─────────────────────────────────

// KAI — Shadow Striker (Ninja)
function drawKai(ctx, f, pose) {
    var c = f.character.colors;
    var t = f.animTime;
    var bY = pose.bodyOffsetY;
    var torsoY = -68 + bY;
    var torsoH = 34;

    // Back leg
    drawLeg(ctx, -7, -30 + bY, pose.leftLegAngle, 30, 11, c.secondary, '#1a1a1a', 10);
    // Back arm
    drawMuscleArm(ctx, -16, torsoY + 5, pose.leftArmAngle, 27, 9, c.skin, c.primary, false);

    // Torso — tight ninja outfit
    drawTorso(ctx, 0, torsoY, 36, torsoH, c.primary, '#1a0d3d', 7);
    // Chest wrap / cross strap
    ctx.strokeStyle = c.accent;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(-12, torsoY + 6);
    ctx.lineTo(10, torsoY + torsoH - 4);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(12, torsoY + 6);
    ctx.lineTo(-10, torsoY + torsoH - 4);
    ctx.stroke();
    // Belt
    ctx.fillStyle = c.accent;
    ctx.fillRect(-14, torsoY + torsoH - 5, 28, 5);
    // Belt buckle
    ctx.fillStyle = '#ffd700';
    ctx.fillRect(-3, torsoY + torsoH - 4, 6, 3);

    // Front leg
    drawLeg(ctx, 7, -30 + bY, pose.rightLegAngle, 30, 11, c.secondary, '#1a1a1a', 10);
    // Front arm
    drawMuscleArm(ctx, 16, torsoY + 5, pose.rightArmAngle, 27, 9, c.skin, c.primary, false);

    // Head
    var headY = torsoY - 14;
    drawHead(ctx, 0, headY, 14, c.skin);
    // Ninja mask (covers lower face)
    ctx.fillStyle = c.secondary;
    ctx.beginPath();
    ctx.moveTo(-12, headY);
    ctx.quadraticCurveTo(-13, headY + 10, -6, headY + 14);
    ctx.lineTo(8, headY + 14);
    ctx.quadraticCurveTo(13, headY + 10, 12, headY);
    ctx.closePath();
    ctx.fill();
    // Hair — tied back
    ctx.fillStyle = c.hair;
    ctx.beginPath();
    ctx.ellipse(0, headY - 5, 13, 8, 0, Math.PI, Math.PI * 2);
    ctx.fill();
    // Hair tail
    ctx.strokeStyle = c.hair;
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(-8, headY - 2);
    for (var hi = 1; hi <= 4; hi++) {
        ctx.lineTo(-8 - hi * 6, headY - 2 + Math.sin(t * 3 + hi) * 4 + hi * 2);
    }
    ctx.stroke();
    // Eyes (intense, visible above mask)
    ctx.fillStyle = '#fff';
    ctx.beginPath(); ctx.ellipse(4, headY - 2, 4, 2.5, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = c.eye;
    ctx.beginPath(); ctx.ellipse(4.5, headY - 2, 2.5, 2, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#000';
    ctx.beginPath(); ctx.arc(5, headY - 2, 1, 0, Math.PI * 2); ctx.fill();
    // Angry brow
    ctx.strokeStyle = c.skin;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, headY - 5);
    ctx.lineTo(9, headY - 6);
    ctx.stroke();

    // Flowing scarf
    ctx.strokeStyle = c.accent;
    ctx.lineWidth = 5;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(-4, headY + 5);
    for (var si = 1; si <= 6; si++) {
        ctx.lineTo(-4 - si * 8, headY + 5 + Math.sin(t * 4 + si * 0.8) * 6 + si * 4);
    }
    ctx.stroke();
    ctx.lineWidth = 3;
    ctx.strokeStyle = '#6c3483';
    ctx.beginPath();
    ctx.moveTo(-4, headY + 5);
    for (var sj = 1; sj <= 6; sj++) {
        ctx.lineTo(-4 - sj * 8, headY + 5 + Math.sin(t * 4 + sj * 0.8) * 6 + sj * 4);
    }
    ctx.stroke();
}

// ROOK — Iron Titan (Heavy Knight)
function drawRook(ctx, f, pose) {
    var c = f.character.colors;
    var t = f.animTime;
    var bY = pose.bodyOffsetY;
    var torsoY = -76 + bY;
    var torsoH = 40;

    // Back leg (armored)
    drawLeg(ctx, -9, -32 + bY, pose.leftLegAngle, 32, 15, c.secondary, '#3d3d3d', 14);
    // Leg armor plate
    ctx.save();
    ctx.translate(-9, -32 + bY);
    ctx.rotate(degToRad(pose.leftLegAngle));
    ctx.fillStyle = c.primary;
    roundRect(ctx, -6, 4, 12, 14, 2);
    ctx.fill();
    ctx.restore();

    // Back arm (armored)
    drawMuscleArm(ctx, -21, torsoY + 7, pose.leftArmAngle, 26, 14, c.skin, c.primary, true);

    // Torso — heavy plate armor
    drawTorso(ctx, 0, torsoY, 48, torsoH, c.primary, c.secondary, 9);
    // Chest plate detail
    ctx.strokeStyle = c.accent;
    ctx.lineWidth = 1.5;
    // Center line
    ctx.beginPath();
    ctx.moveTo(0, torsoY + 4);
    ctx.lineTo(0, torsoY + torsoH - 6);
    ctx.stroke();
    // Horizontal plates
    for (var pl = 0; pl < 3; pl++) {
        var py = torsoY + 10 + pl * 9;
        ctx.beginPath();
        ctx.moveTo(-16, py);
        ctx.lineTo(16, py);
        ctx.stroke();
    }
    // Belt
    ctx.fillStyle = '#4a3520';
    ctx.fillRect(-18, torsoY + torsoH - 6, 36, 6);
    ctx.fillStyle = c.accent;
    ctx.fillRect(-4, torsoY + torsoH - 5, 8, 4);

    // Shoulder pauldrons
    ctx.fillStyle = c.primary;
    // Left pauldron
    ctx.beginPath();
    ctx.ellipse(-22, torsoY + 6, 10, 8, -0.2, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = c.accent;
    ctx.lineWidth = 1;
    ctx.stroke();
    // Right pauldron
    ctx.beginPath();
    ctx.ellipse(22, torsoY + 6, 10, 8, 0.2, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Front leg (armored)
    drawLeg(ctx, 9, -32 + bY, pose.rightLegAngle, 32, 15, c.secondary, '#3d3d3d', 14);
    ctx.save();
    ctx.translate(9, -32 + bY);
    ctx.rotate(degToRad(pose.rightLegAngle));
    ctx.fillStyle = c.primary;
    roundRect(ctx, -6, 4, 12, 14, 2);
    ctx.fill();
    ctx.restore();

    // Front arm
    drawMuscleArm(ctx, 21, torsoY + 7, pose.rightArmAngle, 26, 14, c.skin, c.primary, true);

    // Head — helmet
    var headY = torsoY - 14;
    ctx.fillStyle = c.primary;
    ctx.beginPath();
    ctx.ellipse(0, headY, 16, 15, 0, 0, Math.PI * 2);
    ctx.fill();
    // Helmet ridge
    ctx.fillStyle = '#4a4a5a';
    ctx.beginPath();
    ctx.moveTo(0, headY - 16);
    ctx.lineTo(-3, headY - 6);
    ctx.lineTo(3, headY - 6);
    ctx.closePath();
    ctx.fill();
    ctx.fillRect(-2, headY - 16, 4, 16);
    // T-visor
    ctx.fillStyle = c.eye;
    ctx.fillRect(-10, headY - 3, 20, 3);
    ctx.fillRect(-2, headY - 3, 4, 8);
    // Visor glow
    ctx.shadowColor = c.eye;
    ctx.shadowBlur = 6;
    ctx.fillRect(-10, headY - 3, 20, 3);
    ctx.shadowBlur = 0;

    // Cape
    ctx.fillStyle = 'rgba(80,20,20,0.6)';
    ctx.beginPath();
    ctx.moveTo(-18, torsoY + 4);
    ctx.quadraticCurveTo(-22, torsoY + torsoH, -16 + Math.sin(t * 2) * 4, torsoY + torsoH + 20);
    ctx.lineTo(16 + Math.sin(t * 2 + 1) * 4, torsoY + torsoH + 20);
    ctx.quadraticCurveTo(22, torsoY + torsoH, 18, torsoY + 4);
    ctx.closePath();
    ctx.fill();
}

// ZARA — Storm Dancer (Acrobat)
function drawZara(ctx, f, pose) {
    var c = f.character.colors;
    var t = f.animTime;
    var bY = pose.bodyOffsetY;
    var torsoY = -66 + bY;
    var torsoH = 30;

    // Back leg (athletic)
    drawLeg(ctx, -6, -28 + bY, pose.leftLegAngle, 30, 10, c.secondary, '#1a8a6a', 8);
    // Back arm (wrapped forearms)
    drawMuscleArm(ctx, -14, torsoY + 5, pose.leftArmAngle, 25, 8, c.skin, null, false);
    // Forearm wrap
    ctx.save();
    ctx.translate(-14, torsoY + 5);
    ctx.rotate(degToRad(pose.leftArmAngle));
    ctx.strokeStyle = '#eee';
    ctx.lineWidth = 1.5;
    for (var wi = 0; wi < 4; wi++) {
        ctx.beginPath();
        ctx.moveTo(-4, 14 + wi * 3);
        ctx.lineTo(4, 15 + wi * 3);
        ctx.stroke();
    }
    ctx.restore();

    // Torso — athletic top
    drawTorso(ctx, 0, torsoY, 30, torsoH, c.primary, c.secondary, 6);
    // Sports top detail — V-neckline
    ctx.strokeStyle = c.accent;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(-8, torsoY + 2);
    ctx.lineTo(0, torsoY + 10);
    ctx.lineTo(8, torsoY + 2);
    ctx.stroke();
    // Midriff (exposed)
    ctx.fillStyle = c.skin;
    ctx.fillRect(-10, torsoY + torsoH - 8, 20, 8);
    // Shorts waistband
    ctx.fillStyle = c.accent;
    ctx.fillRect(-12, torsoY + torsoH - 2, 24, 3);

    // Front leg
    drawLeg(ctx, 6, -28 + bY, pose.rightLegAngle, 30, 10, c.secondary, '#1a8a6a', 8);
    // Front arm
    drawMuscleArm(ctx, 14, torsoY + 5, pose.rightArmAngle, 25, 8, c.skin, null, false);
    ctx.save();
    ctx.translate(14, torsoY + 5);
    ctx.rotate(degToRad(pose.rightArmAngle));
    ctx.strokeStyle = '#eee';
    ctx.lineWidth = 1.5;
    for (var wj = 0; wj < 4; wj++) {
        ctx.beginPath();
        ctx.moveTo(-4, 14 + wj * 3);
        ctx.lineTo(4, 15 + wj * 3);
        ctx.stroke();
    }
    ctx.restore();

    // Head
    var headY = torsoY - 12;
    drawHead(ctx, 0, headY, 13, c.skin);
    // Flowing white hair
    ctx.fillStyle = c.hair;
    ctx.beginPath();
    ctx.ellipse(0, headY - 4, 14, 10, 0, Math.PI * 0.9, Math.PI * 2.1);
    ctx.fill();
    // Hair strands flowing back
    ctx.strokeStyle = c.hair;
    ctx.lineWidth = 3;
    for (var hs = 0; hs < 5; hs++) {
        ctx.beginPath();
        ctx.moveTo(-6 - hs * 2, headY - 2 + hs * 3);
        ctx.quadraticCurveTo(
            -14 - hs * 4 + Math.sin(t * 3 + hs) * 5,
            headY + hs * 4,
            -16 - hs * 5 + Math.sin(t * 3 + hs) * 8,
            headY + 4 + hs * 5
        );
        ctx.stroke();
    }
    // Face
    drawEyes(ctx, 0, headY, 13, c.eye, f.state, 1);
    drawMouth(ctx, 0, headY, 13, f.state);

    // Lightning crackle around fists
    ctx.strokeStyle = c.accent;
    ctx.lineWidth = 1.5;
    ctx.globalAlpha = 0.6 + Math.sin(t * 12) * 0.3;
    for (var li = 0; li < 3; li++) {
        var lx = 14 + Math.sin(degToRad(pose.rightArmAngle)) * 25 + randomRange(-8, 8);
        var ly = torsoY + 5 + 25 * 0.3 + randomRange(-8, 8);
        ctx.beginPath();
        ctx.moveTo(lx, ly);
        ctx.lineTo(lx + randomRange(-10, 10), ly + randomRange(-10, 10));
        ctx.lineTo(lx + randomRange(-10, 10), ly + randomRange(-10, 10));
        ctx.stroke();
    }
    ctx.globalAlpha = 1;
}

// VEX — Venom Fang (Assassin)
function drawVex(ctx, f, pose) {
    var c = f.character.colors;
    var t = f.animTime;
    var bY = pose.bodyOffsetY;
    var torsoY = -68 + bY;
    var torsoH = 32;

    // Back leg
    drawLeg(ctx, -7, -30 + bY, pose.leftLegAngle, 30, 10, '#1a3020', '#0d1a10', 10);
    // Back arm — exposed with vein marks
    drawMuscleArm(ctx, -15, torsoY + 5, pose.leftArmAngle, 27, 9, c.skin, null, false);
    // Vein lines on back arm
    ctx.save();
    ctx.translate(-15, torsoY + 5);
    ctx.rotate(degToRad(pose.leftArmAngle));
    ctx.strokeStyle = c.accent;
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.5 + Math.sin(t * 3) * 0.2;
    ctx.beginPath();
    ctx.moveTo(0, 4); ctx.quadraticCurveTo(-3, 12, 0, 20);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(2, 6); ctx.quadraticCurveTo(4, 14, 1, 22);
    ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.restore();

    // Torso — dark cloak
    drawTorso(ctx, 0, torsoY, 34, torsoH, c.primary, '#0d2614', 7);
    // Cloak clasp
    ctx.fillStyle = '#888';
    ctx.beginPath();
    ctx.arc(0, torsoY + 5, 4, 0, Math.PI * 2);
    ctx.fill();
    // Poison vial belt
    ctx.fillStyle = '#1a3020';
    ctx.fillRect(-14, torsoY + torsoH - 5, 28, 5);
    for (var vi = 0; vi < 3; vi++) {
        ctx.fillStyle = c.accent;
        ctx.globalAlpha = 0.6;
        roundRect(ctx, -8 + vi * 6, torsoY + torsoH - 8, 4, 6, 1);
        ctx.fill();
    }
    ctx.globalAlpha = 1;

    // Front leg
    drawLeg(ctx, 7, -30 + bY, pose.rightLegAngle, 30, 10, '#1a3020', '#0d1a10', 10);
    // Front arm with vein marks
    drawMuscleArm(ctx, 15, torsoY + 5, pose.rightArmAngle, 27, 9, c.skin, null, false);
    ctx.save();
    ctx.translate(15, torsoY + 5);
    ctx.rotate(degToRad(pose.rightArmAngle));
    ctx.strokeStyle = c.accent;
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.5 + Math.sin(t * 3 + 1) * 0.2;
    ctx.beginPath();
    ctx.moveTo(-1, 4); ctx.quadraticCurveTo(-3, 14, 1, 22);
    ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.restore();

    // Head
    var headY = torsoY - 12;
    drawHead(ctx, 0, headY, 14, c.skin);

    // Hood
    ctx.fillStyle = c.primary;
    ctx.beginPath();
    ctx.moveTo(-16, headY + 4);
    ctx.quadraticCurveTo(-18, headY - 10, -4, headY - 18);
    ctx.quadraticCurveTo(2, headY - 20, 8, headY - 16);
    ctx.quadraticCurveTo(14, headY - 8, 12, headY + 4);
    ctx.quadraticCurveTo(0, headY + 2, -16, headY + 4);
    ctx.closePath();
    ctx.fill();
    // Hood shadow on face
    ctx.fillStyle = 'rgba(0,0,0,0.3)';
    ctx.beginPath();
    ctx.ellipse(0, headY - 2, 11, 6, 0, 0, Math.PI);
    ctx.fill();

    // Glowing green eyes (sinister)
    ctx.shadowColor = c.eye;
    ctx.shadowBlur = 8;
    ctx.fillStyle = c.eye;
    ctx.beginPath(); ctx.ellipse(4, headY - 2, 3, 1.8, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(-4, headY - 2, 2.5, 1.5, 0, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0;

    // Poison drip from hands
    ctx.fillStyle = c.accent;
    ctx.globalAlpha = 0.4;
    for (var pd = 0; pd < 3; pd++) {
        var dx = 15 + Math.sin(degToRad(pose.rightArmAngle)) * 27;
        var dy = torsoY + 5 + 27 * 0.3;
        ctx.beginPath();
        ctx.arc(dx + randomRange(-3, 3), dy + randomRange(0, 10), randomRange(1, 3), 0, Math.PI * 2);
        ctx.fill();
    }
    ctx.globalAlpha = 1;
}

// FREYA — Frost Sentinel (Ice Warrior)
function drawFreya(ctx, f, pose) {
    var c = f.character.colors;
    var t = f.animTime;
    var bY = pose.bodyOffsetY;
    var torsoY = -70 + bY;
    var torsoH = 34;

    // Armored skirt (behind legs)
    ctx.fillStyle = c.secondary;
    ctx.beginPath();
    ctx.moveTo(-18, torsoY + torsoH - 2);
    ctx.quadraticCurveTo(-20 + Math.sin(t * 2) * 2, -20 + bY, -14 + Math.sin(t * 2.5) * 3, -8 + bY);
    ctx.lineTo(14 + Math.sin(t * 2.5 + 1) * 3, -8 + bY);
    ctx.quadraticCurveTo(20 + Math.sin(t * 2 + 1) * 2, -20 + bY, 18, torsoY + torsoH - 2);
    ctx.closePath();
    ctx.fill();
    // Skirt detail lines
    ctx.strokeStyle = c.accent;
    ctx.lineWidth = 0.8;
    ctx.globalAlpha = 0.4;
    for (var sk = -2; sk <= 2; sk++) {
        ctx.beginPath();
        ctx.moveTo(sk * 6, torsoY + torsoH);
        ctx.lineTo(sk * 7, -10 + bY);
        ctx.stroke();
    }
    ctx.globalAlpha = 1;

    // Back leg (under skirt)
    drawLeg(ctx, -7, -28 + bY, pose.leftLegAngle, 28, 10, c.secondary, '#1a4a6a', 10);
    // Back arm
    drawMuscleArm(ctx, -15, torsoY + 5, pose.leftArmAngle, 26, 9, c.skin, c.primary, false);

    // Torso — armored bodice
    drawTorso(ctx, 0, torsoY, 34, torsoH, c.primary, c.secondary, 6);
    // Armor chest plate
    ctx.strokeStyle = c.accent;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(-10, torsoY + 6);
    ctx.quadraticCurveTo(0, torsoY + 14, 10, torsoY + 6);
    ctx.stroke();
    // Center gem
    ctx.fillStyle = '#85c1e9';
    ctx.shadowColor = '#85c1e9';
    ctx.shadowBlur = 6;
    ctx.beginPath();
    ctx.moveTo(0, torsoY + 8);
    ctx.lineTo(-4, torsoY + 12);
    ctx.lineTo(0, torsoY + 16);
    ctx.lineTo(4, torsoY + 12);
    ctx.closePath();
    ctx.fill();
    ctx.shadowBlur = 0;
    // Belt
    ctx.fillStyle = '#1a4a6a';
    ctx.fillRect(-14, torsoY + torsoH - 4, 28, 4);

    // Front leg
    drawLeg(ctx, 7, -28 + bY, pose.rightLegAngle, 28, 10, c.secondary, '#1a4a6a', 10);
    // Front arm
    drawMuscleArm(ctx, 15, torsoY + 5, pose.rightArmAngle, 26, 9, c.skin, c.primary, false);

    // Head
    var headY = torsoY - 13;
    drawHead(ctx, 0, headY, 13, c.skin);
    // Long flowing blue hair
    ctx.fillStyle = c.hair;
    ctx.beginPath();
    ctx.ellipse(0, headY - 3, 15, 10, 0, Math.PI * 0.85, Math.PI * 2.15);
    ctx.fill();
    // Hair flowing down
    ctx.fillStyle = c.hair;
    ctx.beginPath();
    ctx.moveTo(-12, headY);
    ctx.quadraticCurveTo(-14 + Math.sin(t * 2) * 3, headY + 20, -10 + Math.sin(t * 2.5) * 4, headY + 35);
    ctx.lineTo(-6 + Math.sin(t * 2.5 + 0.5) * 3, headY + 35);
    ctx.quadraticCurveTo(-8, headY + 15, -8, headY);
    ctx.closePath();
    ctx.fill();
    // Ice crown / tiara
    ctx.fillStyle = '#b8e6ff';
    ctx.shadowColor = '#85c1e9';
    ctx.shadowBlur = 4;
    for (var cr = -2; cr <= 2; cr++) {
        var crH = cr === 0 ? 10 : (Math.abs(cr) === 1 ? 7 : 5);
        ctx.beginPath();
        ctx.moveTo(cr * 5 - 2, headY - 12);
        ctx.lineTo(cr * 5, headY - 12 - crH);
        ctx.lineTo(cr * 5 + 2, headY - 12);
        ctx.closePath();
        ctx.fill();
    }
    ctx.shadowBlur = 0;

    // Face
    drawEyes(ctx, 0, headY, 13, c.eye, f.state, 1);
    drawMouth(ctx, 0, headY, 13, f.state);

    // Frost particles
    ctx.fillStyle = '#b8e6ff';
    ctx.globalAlpha = 0.3;
    for (var fp = 0; fp < 4; fp++) {
        var fx = randomRange(-25, 25);
        var fy = torsoY + randomRange(-5, torsoH + 10);
        ctx.beginPath();
        ctx.moveTo(fx, fy - 3);
        ctx.lineTo(fx + 2, fy);
        ctx.lineTo(fx, fy + 3);
        ctx.lineTo(fx - 2, fy);
        ctx.closePath();
        ctx.fill();
    }
    ctx.globalAlpha = 1;
}

// DRAKE — Inferno (Berserker)
function drawDrake(ctx, f, pose) {
    var c = f.character.colors;
    var t = f.animTime;
    var bY = pose.bodyOffsetY;
    var torsoY = -72 + bY;
    var torsoH = 36;

    // Back leg (tattered pants)
    drawLeg(ctx, -8, -30 + bY, pose.leftLegAngle, 30, 12, '#3d1a0a', '#2a1a0a', 10);
    // Back arm (bare, muscular)
    drawMuscleArm(ctx, -17, torsoY + 5, pose.leftArmAngle, 27, 12, c.skin, null, false);
    // Flame tattoo on back arm
    ctx.save();
    ctx.translate(-17, torsoY + 5);
    ctx.rotate(degToRad(pose.leftArmAngle));
    ctx.strokeStyle = c.accent;
    ctx.lineWidth = 1.2;
    ctx.globalAlpha = 0.6 + (f.rageActive ? 0.3 : 0);
    ctx.beginPath();
    ctx.moveTo(-2, 5);
    ctx.quadraticCurveTo(-4, 10, -1, 16);
    ctx.quadraticCurveTo(2, 12, 3, 8);
    ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.restore();

    // Torso — SHIRTLESS muscular
    // Skin torso
    drawTorso(ctx, 0, torsoY, 40, torsoH, c.skin, '#b8885a', 8);
    // Muscle definition
    ctx.strokeStyle = 'rgba(0,0,0,0.12)';
    ctx.lineWidth = 1;
    // Pecs
    ctx.beginPath();
    ctx.arc(-7, torsoY + 12, 8, 0.3, Math.PI - 0.3);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(7, torsoY + 12, 8, 0.3, Math.PI - 0.3);
    ctx.stroke();
    // Abs
    for (var ab = 0; ab < 3; ab++) {
        ctx.beginPath();
        ctx.moveTo(-5, torsoY + 20 + ab * 5);
        ctx.lineTo(5, torsoY + 20 + ab * 5);
        ctx.stroke();
    }
    ctx.beginPath();
    ctx.moveTo(0, torsoY + 18);
    ctx.lineTo(0, torsoY + torsoH - 2);
    ctx.stroke();
    // Flame tattoos on torso
    ctx.strokeStyle = c.accent;
    ctx.lineWidth = 1.5;
    ctx.globalAlpha = 0.4 + (f.rageActive ? 0.4 : 0);
    ctx.beginPath();
    ctx.moveTo(-14, torsoY + torsoH);
    ctx.quadraticCurveTo(-16, torsoY + 20, -10, torsoY + 10);
    ctx.quadraticCurveTo(-8, torsoY + 18, -12, torsoY + torsoH);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(14, torsoY + torsoH);
    ctx.quadraticCurveTo(16, torsoY + 20, 10, torsoY + 10);
    ctx.stroke();
    ctx.globalAlpha = 1;
    // Belt / waistband
    ctx.fillStyle = '#3d1a0a';
    ctx.fillRect(-16, torsoY + torsoH - 4, 32, 5);
    // Torn cloth hanging
    ctx.fillStyle = '#4a1a0a';
    ctx.beginPath();
    ctx.moveTo(-10, torsoY + torsoH);
    ctx.lineTo(-12, torsoY + torsoH + 8);
    ctx.lineTo(-6, torsoY + torsoH + 6);
    ctx.lineTo(-8, torsoY + torsoH);
    ctx.fill();

    // Front leg
    drawLeg(ctx, 8, -30 + bY, pose.rightLegAngle, 30, 12, '#3d1a0a', '#2a1a0a', 10);
    // Front arm (bare, muscular, with tattoo)
    drawMuscleArm(ctx, 17, torsoY + 5, pose.rightArmAngle, 27, 12, c.skin, null, false);
    ctx.save();
    ctx.translate(17, torsoY + 5);
    ctx.rotate(degToRad(pose.rightArmAngle));
    ctx.strokeStyle = c.accent;
    ctx.lineWidth = 1.2;
    ctx.globalAlpha = 0.6 + (f.rageActive ? 0.3 : 0);
    ctx.beginPath();
    ctx.moveTo(1, 4); ctx.quadraticCurveTo(4, 10, 1, 18);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(-2, 6); ctx.quadraticCurveTo(-5, 12, -2, 20);
    ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.restore();

    // Head
    var headY = torsoY - 14;
    drawHead(ctx, 0, headY, 15, c.skin);
    // Wild spiky red hair
    ctx.fillStyle = c.hair;
    // Base hair
    ctx.beginPath();
    ctx.ellipse(0, headY - 5, 16, 10, 0, Math.PI * 0.8, Math.PI * 2.2);
    ctx.fill();
    // Spikes
    var spikeAngles = [-0.6, -0.3, 0, 0.25, 0.5, 0.8];
    for (var sp = 0; sp < spikeAngles.length; sp++) {
        var sa = spikeAngles[sp];
        var sLen = 12 + (sp % 2) * 6;
        ctx.fillStyle = sp % 2 === 0 ? c.hair : '#ff4422';
        ctx.beginPath();
        ctx.moveTo(Math.cos(sa - 1.5) * 14, headY - 6 + Math.sin(sa - 1.5) * 10);
        ctx.lineTo(Math.cos(sa - 1.5) * (14 + sLen) + Math.sin(t * 4 + sp) * 2,
                   headY - 6 + Math.sin(sa - 1.5) * (10 + sLen));
        ctx.lineTo(Math.cos(sa - 1.3) * 14, headY - 6 + Math.sin(sa - 1.3) * 10);
        ctx.closePath();
        ctx.fill();
    }

    // Face — fierce
    drawEyes(ctx, 0, headY, 15, c.eye, f.state, 1);
    // Gritted teeth
    var mx = 15 * 0.15 + 2;
    var my = headY + 15 * 0.45;
    ctx.fillStyle = '#300';
    ctx.beginPath();
    ctx.ellipse(mx, my, 4, 2.5, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#ddd';
    ctx.fillRect(mx - 3.5, my - 1, 7, 1);

    // Fire aura (enhanced during rage)
    var fireCount = f.rageActive ? 10 : 3;
    var fireAlpha = f.rageActive ? 0.7 : 0.25;
    ctx.globalAlpha = fireAlpha;
    for (var fi = 0; fi < fireCount; fi++) {
        var ffx = randomRange(-20, 20);
        var ffy = torsoY + torsoH - randomRange(0, 40);
        var fsize = randomRange(3, f.rageActive ? 10 : 6);
        ctx.fillStyle = Math.random() > 0.5 ? c.accent : '#ff2200';
        ctx.beginPath();
        ctx.moveTo(ffx, ffy);
        ctx.quadraticCurveTo(ffx - fsize * 0.5, ffy - fsize, ffx, ffy - fsize * 1.5);
        ctx.quadraticCurveTo(ffx + fsize * 0.5, ffy - fsize, ffx, ffy);
        ctx.fill();
    }
    ctx.globalAlpha = 1;
}


// ── Character dispatch table ────────────────────────────────
var CHARACTER_DRAW = {
    'kai': drawKai,
    'rook': drawRook,
    'zara': drawZara,
    'vex': drawVex,
    'freya': drawFreya,
    'drake': drawDrake
};


// ── Replace Fighter.prototype.render ────────────────────────
Fighter.prototype.render = function(ctx) {
    var c = this.character;
    var dir = this.facingRight ? 1 : -1;
    var pose = this._getPose();

    ctx.save();
    ctx.translate(this.x, this.y);
    ctx.scale(dir, 1);

    // Hit flash
    if (this.hurtFlash > 0 && Math.floor(this.hurtFlash * 30) % 2 === 0) {
        ctx.globalAlpha = 0.6;
    }
    // Freeze tint
    if (this.freezeTimer > 0) {
        ctx.globalAlpha = 0.7;
        // Ice overlay color
        ctx.fillStyle = 'rgba(130,200,255,0.15)';
        ctx.fillRect(-30, -this.height, 60, this.height);
    }

    // Ground shadow
    ctx.fillStyle = 'rgba(0,0,0,0.35)';
    ctx.beginPath();
    ctx.ellipse(0, 0, 22, 5, 0, 0, Math.PI * 2);
    ctx.fill();

    // Draw character body
    var drawFn = CHARACTER_DRAW[c.id];
    if (drawFn) {
        drawFn(ctx, this, pose);
    }

    // Draw weapon (in front hand)
    var armLen = c.body.armLen;
    var shoulderX = c.body.shoulderW ? c.body.shoulderW / 2 : 15;
    var shoulderY = -68 + pose.bodyOffsetY + 5;
    var handX = shoulderX + Math.sin(degToRad(pose.rightArmAngle)) * armLen;
    var handY = shoulderY + Math.cos(degToRad(pose.rightArmAngle)) * armLen * 0.3;
    this._drawWeapon(ctx, handX, handY, pose.weaponAngle);

    // Blocking shield
    if (this.isBlocking) {
        ctx.strokeStyle = 'rgba(100,200,255,0.6)';
        ctx.lineWidth = 3;
        ctx.shadowColor = 'rgba(100,200,255,0.4)';
        ctx.shadowBlur = 10;
        ctx.beginPath();
        ctx.arc(12, -40, 38, -Math.PI * 0.7, Math.PI * 0.7);
        ctx.stroke();
        ctx.shadowBlur = 0;
    }

    // Rage aura (Drake)
    if (this.rageActive) {
        ctx.strokeStyle = c.colors.glow;
        ctx.lineWidth = 2;
        ctx.globalAlpha = 0.4 + Math.sin(this.animTime * 8) * 0.2;
        ctx.beginPath();
        ctx.arc(0, -40, 35 + Math.sin(this.animTime * 6) * 5, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 1;
    }

    ctx.restore();

    // Poison overlay
    if (this.poisonTimer > 0) {
        ctx.fillStyle = 'rgba(0,255,100,0.2)';
        ctx.beginPath();
        ctx.arc(this.x, this.y - this.height / 2, 30 + Math.sin(this.animTime * 5) * 5, 0, Math.PI * 2);
        ctx.fill();
    }

    // Combo counter
    if (this.comboCount > 1) {
        ctx.save();
        ctx.font = 'bold 26px "Orbitron", "Rajdhani", sans-serif';
        ctx.textAlign = 'center';
        ctx.fillStyle = '#ffd700';
        ctx.shadowColor = '#ff8800';
        ctx.shadowBlur = 8;
        ctx.fillText(this.comboCount + ' HIT', this.x, this.y - this.height - 28);
        ctx.font = 'bold 16px "Rajdhani", sans-serif';
        ctx.fillStyle = '#ffaa00';
        ctx.fillText('COMBO!', this.x, this.y - this.height - 10);
        ctx.shadowBlur = 0;
        ctx.restore();
    }
};

})();
