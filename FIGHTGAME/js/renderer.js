/* ============================================================
   SHADOW ARENA — Premium Character Renderer v2
   Cel-shaded fighting game art with bold outlines, gradient
   shading, detailed anatomy, expressive faces, and VFX.
   All positions computed from character body data.
   ============================================================ */
(function() {
'use strict';

// ─── CONSTANTS ──────────────────────────────────────────────
var OL = 2.0;          // outline width
var OC = '#0a0a12';    // outline colour (near-black blue)
var SCALE = 1.35;      // visual scale — must match engine _RENDER_SCALE

// ─── COLOUR UTILITIES ───────────────────────────────────────
function darker(hex, amt) {
    var r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
    r = Math.max(0, r - amt); g = Math.max(0, g - amt); b = Math.max(0, b - amt);
    return '#' + ((1<<24)+(r<<16)+(g<<8)+b).toString(16).slice(1);
}
function lighter(hex, amt) {
    var r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
    r = Math.min(255, r + amt); g = Math.min(255, g + amt); b = Math.min(255, b + amt);
    return '#' + ((1<<24)+(r<<16)+(g<<8)+b).toString(16).slice(1);
}
function rgba(hex, a) {
    var r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
}
// Seeded-ish per-frame consistent random for VFX
var _seed = 42;
function sfx_rand() { _seed = (_seed * 16807 + 0) % 2147483647; return (_seed & 0x7fffffff) / 2147483647; }
function sfx_range(mn, mx) { return mn + sfx_rand() * (mx - mn); }

// ─── CORE DRAWING PRIMITIVES (outlined + gradient-shaded) ───

// Outlined ellipse with gradient shading
function oEllipse(ctx, cx, cy, rx, ry, fill, shadow) {
    ctx.fillStyle = OC;
    ctx.beginPath(); ctx.ellipse(cx, cy, rx + OL, ry + OL, 0, 0, Math.PI * 2); ctx.fill();
    if (shadow) { ctx.fillStyle = shadow; ctx.beginPath(); ctx.ellipse(cx + 1, cy + 1, rx, ry, 0, 0, Math.PI * 2); ctx.fill(); }
    ctx.fillStyle = fill;
    ctx.beginPath(); ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2); ctx.fill();
}

// Outlined path
function oPath(ctx, buildPath, fill, shadow) {
    ctx.save(); ctx.lineWidth = OL * 2; ctx.strokeStyle = OC; ctx.lineJoin = 'round';
    buildPath(ctx); ctx.stroke(); ctx.restore();
    if (shadow) { ctx.save(); ctx.translate(1.2, 1.2); ctx.fillStyle = shadow; buildPath(ctx); ctx.fill(); ctx.restore(); }
    ctx.fillStyle = fill; buildPath(ctx); ctx.fill();
}

// Outlined rounded rect
function oRect(ctx, x, y, w, h, r, fill, shadow) {
    oPath(ctx, function(c) {
        c.beginPath(); c.moveTo(x + r, y); c.lineTo(x + w - r, y);
        c.quadraticCurveTo(x + w, y, x + w, y + r); c.lineTo(x + w, y + h - r);
        c.quadraticCurveTo(x + w, y + h, x + w - r, y + h); c.lineTo(x + r, y + h);
        c.quadraticCurveTo(x, y + h, x, y + h - r); c.lineTo(x, y + r);
        c.quadraticCurveTo(x, y, x + r, y); c.closePath();
    }, fill, shadow);
}

// Gradient-shaded limb with outline + optional cloth/glove
function drawShadedLimb(ctx, x, y, angle, length, thickness, baseColor, options) {
    var opt = options || {};
    var clothColor = opt.cloth;
    var gloveColor = opt.glove;
    var isArm = opt.isArm;
    var bulge = opt.bulge || 1.12;

    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(degToRad(angle));

    var hw = thickness * 0.5;
    var bw = hw * bulge;
    var tw = hw * 0.88;

    var buildLimb = function(c) {
        c.beginPath(); c.moveTo(-hw, 0);
        c.quadraticCurveTo(-bw, length * 0.35, -tw, length);
        c.lineTo(tw, length);
        c.quadraticCurveTo(bw, length * 0.35, hw, 0);
        c.closePath();
    };

    // Outline
    ctx.lineWidth = OL * 2; ctx.strokeStyle = OC; ctx.lineJoin = 'round';
    buildLimb(ctx); ctx.stroke();

    // Gradient fill
    var base = clothColor || baseColor;
    var grad = ctx.createLinearGradient(-bw, 0, bw, 0);
    grad.addColorStop(0, darker(base, 35));
    grad.addColorStop(0.35, base);
    grad.addColorStop(0.65, lighter(base, 18));
    grad.addColorStop(1, darker(base, 25));
    ctx.fillStyle = grad; buildLimb(ctx); ctx.fill();

    // Cloth/skin transition
    if (clothColor && (opt.splitAt !== undefined)) {
        var splitY = length * opt.splitAt;
        ctx.fillStyle = baseColor;
        ctx.beginPath();
        ctx.moveTo(-tw - 1, splitY); ctx.quadraticCurveTo(-tw * 0.8, length * 0.75, -tw, length);
        ctx.lineTo(tw, length); ctx.quadraticCurveTo(tw * 0.8, length * 0.75, tw + 1, splitY);
        ctx.closePath(); ctx.fill();
    }

    // Highlight
    ctx.globalAlpha = 0.15; ctx.fillStyle = '#fff';
    ctx.beginPath(); ctx.ellipse(hw * 0.3, length * 0.3, hw * 0.22, length * 0.28, 0, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 1;

    // Joint
    oEllipse(ctx, 0, 0, hw * 0.5, hw * 0.5, clothColor || baseColor, darker(clothColor || baseColor, 30));

    // Fist / hand
    if (isArm) {
        var fc = gloveColor || baseColor;
        oEllipse(ctx, 0, length, hw * 0.52, hw * 0.42, fc, darker(fc, 30));
        if (gloveColor) {
            ctx.strokeStyle = darker(gloveColor, 40); ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(-hw * 0.3, length - 1.5); ctx.lineTo(hw * 0.3, length - 1.5); ctx.stroke();
        }
    }

    ctx.restore();
}

// Shaded V-taper torso with outline
function drawShadedTorso(ctx, ox, oy, sw, ww, h, topColor, bottomColor, opts) {
    var o = opts || {};
    var nw = o.neckW || sw * 0.3;
    var buildTorso = function(c) {
        c.beginPath(); c.moveTo(ox - nw, oy);
        c.lineTo(ox - sw, oy + h * 0.08);
        c.quadraticCurveTo(ox - sw * 1.03, oy + h * 0.4, ox - ww, oy + h);
        c.lineTo(ox + ww, oy + h);
        c.quadraticCurveTo(ox + sw * 1.03, oy + h * 0.4, ox + sw, oy + h * 0.08);
        c.lineTo(ox + nw, oy); c.closePath();
    };
    // Outline
    ctx.lineWidth = OL * 2; ctx.strokeStyle = OC; ctx.lineJoin = 'round';
    buildTorso(ctx); ctx.stroke();
    // Gradient
    var grad = ctx.createLinearGradient(ox - sw, oy, ox + sw, oy);
    grad.addColorStop(0, darker(topColor, 28)); grad.addColorStop(0.3, topColor);
    grad.addColorStop(0.55, lighter(topColor, 14)); grad.addColorStop(0.8, topColor);
    grad.addColorStop(1, darker(topColor, 22));
    ctx.fillStyle = grad; buildTorso(ctx); ctx.fill();
    // Bottom blend
    if (bottomColor && bottomColor !== topColor) {
        ctx.save(); buildTorso(ctx); ctx.clip();
        var vg = ctx.createLinearGradient(ox, oy + h * 0.55, ox, oy + h);
        vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, bottomColor);
        ctx.fillStyle = vg; ctx.fillRect(ox - sw - 4, oy, sw * 2 + 8, h); ctx.restore();
    }
    // Specular
    ctx.globalAlpha = 0.1; ctx.fillStyle = '#fff';
    ctx.beginPath(); ctx.ellipse(ox + sw * 0.15, oy + h * 0.25, sw * 0.18, h * 0.16, 0.2, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 1;
}

// Head with outline & cheek highlight
function drawShadedHead(ctx, cx, cy, r, skinColor) {
    oEllipse(ctx, cx, cy, r * 0.93, r * 1.02, skinColor, darker(skinColor, 24));
    ctx.globalAlpha = 0.09; ctx.fillStyle = '#fff';
    ctx.beginPath(); ctx.ellipse(cx + r * 0.2, cy - r * 0.12, r * 0.32, r * 0.22, 0, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 1;
}

// Expressive eyes — shift with state
function drawExpressiveEyes(ctx, cx, cy, r, eyeColor, state) {
    var ex = cx + r * 0.28, ey = cy - r * 0.08;
    var ew = r * 0.3, eh;
    var angry = state === 'attacking' || state === 'special' || state === 'taunt';
    var hurt = state === 'hit' || state === 'ko';
    eh = state === 'ko' ? ew * 0.15 : (hurt ? ew * 0.45 : ew * 0.72);

    // Socket shadow
    ctx.fillStyle = 'rgba(0,0,0,0.07)';
    ctx.beginPath(); ctx.ellipse(ex, ey, ew + 1.5, eh + 1.5, 0, 0, Math.PI * 2); ctx.fill();
    // Sclera
    ctx.fillStyle = hurt ? '#e8d8d8' : '#f8f8ff';
    ctx.beginPath(); ctx.ellipse(ex, ey, ew, eh, 0, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = OC; ctx.lineWidth = 0.8; ctx.stroke();

    if (state !== 'ko') {
        // Iris
        ctx.fillStyle = eyeColor;
        ctx.beginPath(); ctx.ellipse(ex + 0.5, ey + (hurt ? 0.5 : 0), ew * 0.55, eh * 0.62, 0, 0, Math.PI * 2); ctx.fill();
        // Pupil
        ctx.fillStyle = '#000';
        ctx.beginPath(); ctx.arc(ex + 0.7, ey + (hurt ? 0.5 : 0), ew * 0.22, 0, Math.PI * 2); ctx.fill();
        // Highlight
        ctx.fillStyle = '#fff';
        ctx.beginPath(); ctx.arc(ex + ew * 0.3, ey - eh * 0.3, ew * 0.15, 0, Math.PI * 2); ctx.fill();
    } else {
        ctx.strokeStyle = eyeColor; ctx.lineWidth = 1.3;
        ctx.beginPath(); ctx.moveTo(ex - 2, ey - 1.5); ctx.lineTo(ex + 2, ey + 1.5); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(ex + 2, ey - 1.5); ctx.lineTo(ex - 2, ey + 1.5); ctx.stroke();
    }

    // Brow
    ctx.strokeStyle = OC; ctx.lineWidth = 2; ctx.lineCap = 'round';
    ctx.beginPath();
    if (angry) { ctx.moveTo(ex - ew - 1.5, ey - eh - 0.5); ctx.quadraticCurveTo(ex, ey - eh - 4, ex + ew + 2.5, ey - eh + 1.5); }
    else if (hurt) { ctx.moveTo(ex - ew - 0.5, ey - eh - 2.5); ctx.quadraticCurveTo(ex, ey - eh + 1, ex + ew + 1.5, ey - eh - 1.5); }
    else { ctx.moveTo(ex - ew - 0.5, ey - eh - 2.5); ctx.quadraticCurveTo(ex, ey - eh - 3.5, ex + ew + 1.5, ey - eh - 2); }
    ctx.stroke(); ctx.lineCap = 'butt';
}

// Mouth for expressions
function drawExpressiveMouth(ctx, cx, cy, r, state) {
    var mx = cx + r * 0.18, my = cy + r * 0.42;
    if (state === 'ko') {
        oEllipse(ctx, mx, my, 3.5, 3, '#2a0505', '#1a0000');
        ctx.fillStyle = '#ddd'; ctx.fillRect(mx - 2.5, my - 2.5, 5, 1.2);
    } else if (state === 'hit') {
        oEllipse(ctx, mx, my + 1, 3, 2.5, '#2a0505', '#1a0000');
        ctx.fillStyle = '#ddd'; ctx.fillRect(mx - 2, my - 0.8, 4, 1);
    } else if (state === 'attacking' || state === 'special') {
        oEllipse(ctx, mx, my + 1, 4.5, 3.5, '#2a0505', '#1a0000');
        ctx.fillStyle = '#ddd'; ctx.fillRect(mx - 3.5, my - 2, 7, 1.3);
        ctx.fillRect(mx - 3, my + 2.5, 6, 1);
    } else if (state === 'taunt') {
        ctx.strokeStyle = OC; ctx.lineWidth = 1.6;
        ctx.beginPath(); ctx.moveTo(mx - 3.5, my); ctx.quadraticCurveTo(mx, my + 2.5, mx + 4.5, my - 0.8); ctx.stroke();
        ctx.fillStyle = '#eee'; ctx.beginPath(); ctx.moveTo(mx - 0.5, my); ctx.quadraticCurveTo(mx + 1, my + 1.2, mx + 2.5, my); ctx.closePath(); ctx.fill();
    } else if (state === 'block') {
        ctx.fillStyle = '#eee'; ctx.fillRect(mx - 3, my - 0.8, 6, 2.5);
        ctx.strokeStyle = OC; ctx.lineWidth = 1; ctx.strokeRect(mx - 3, my - 0.8, 6, 2.5);
        ctx.strokeStyle = '#ccc'; ctx.lineWidth = 0.4;
        for (var ti = 0; ti < 4; ti++) { ctx.beginPath(); ctx.moveTo(mx - 2 + ti * 1.3, my - 0.8); ctx.lineTo(mx - 2 + ti * 1.3, my + 1.7); ctx.stroke(); }
    } else {
        ctx.strokeStyle = OC; ctx.lineWidth = 1.6;
        ctx.beginPath(); ctx.moveTo(mx - 3, my); ctx.quadraticCurveTo(mx, my + 0.4, mx + 3, my - 0.2); ctx.stroke();
    }
}

// Boot
function drawBoot(ctx, x, y, w, h, color) {
    oRect(ctx, x - w * 0.55, y - h * 0.3, w * 1.15, h, 2.5, color, darker(color, 28));
    ctx.fillStyle = darker(color, 45); ctx.fillRect(x - w * 0.55, y + h * 0.5, w * 1.15, 2.5);
}

// Complete leg: thigh + shin + boot
function drawFullLeg(ctx, x, y, angle, len, thick, pantsColor, bootColor, bootH, opts) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(degToRad(angle));
    var o = opts || {};
    drawShadedLimb(ctx, 0, 0, 0, len * 0.52, thick, pantsColor, { bulge: 1.18 });
    drawShadedLimb(ctx, 0, len * 0.48, 0, len * 0.52, thick * 0.88, pantsColor, { bulge: 1.04 });
    if (o.kneePad) oEllipse(ctx, 0, len * 0.48, thick * 0.38, thick * 0.32, o.kneePad, darker(o.kneePad, 28));
    drawBoot(ctx, 0, len, thick * 0.88, bootH || 8, bootColor);
    ctx.restore();
}


// ─── ENERGY / VFX HELPERS ───────────────────────────────────
function drawGlow(ctx, x, y, r, color, intensity) {
    ctx.save(); ctx.globalAlpha = intensity;
    var g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, rgba(color, 0.5)); g.addColorStop(0.5, rgba(color, 0.12)); g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2);
    ctx.restore();
}

function drawFlameShape(ctx, fx, fy, sz, c1, c2) {
    ctx.fillStyle = sfx_rand() > 0.5 ? c1 : c2;
    ctx.beginPath(); ctx.moveTo(fx, fy);
    ctx.quadraticCurveTo(fx - sz * 0.6, fy - sz * 0.8, fx, fy - sz * 1.6);
    ctx.quadraticCurveTo(fx + sz * 0.6, fy - sz * 0.8, fx, fy);
    ctx.fill();
}

// ─── POSITION HELPER ────────────────────────────────────────
// Returns key Y coordinates derived from the character body data
function bodyPos(body, bY) {
    var legLen = body.legLen;
    var torsoH = body.torsoH;
    var headR = body.headR;
    var sw = (body.shoulderW || body.torsoW + 4) * 0.5;
    return {
        legY: -(legLen + 4),                              // hip
        tY: -(legLen + torsoH) + bY,                      // torso top
        tH: torsoH,                                       // torso height
        hY: -(legLen + torsoH + headR) + bY * 0.5,        // head centre
        hR: headR,                                        // head radius
        sw: sw,                                            // half-shoulder width
        ww: sw * 0.7,                                      // waist half-width
        legLen: legLen,
        armLen: body.armLen,
        armW: body.armW,
        legW: body.legW
    };
}


// ═══════════════════════════════════════════════════════════
//   PER-CHARACTER RENDERING
// ═══════════════════════════════════════════════════════════

// ── KAI — Shadow Striker (Ninja) ────────────────────────────
function drawKai(ctx, f, P) {
    var c = f.character.colors, b = f.character.body, t = f.animTime, bY = P.bodyOffsetY;
    var p = bodyPos(b, bY);

    // Back leg
    drawFullLeg(ctx, -8, p.legY, P.leftLegAngle, p.legLen, p.legW, c.secondary, '#111', 9);
    // Back arm
    drawShadedLimb(ctx, -p.sw, p.tY + 4, P.leftArmAngle, p.armLen, p.armW, c.skin, { isArm: true, cloth: c.primary, splitAt: 0.45 });

    // Torso — ninja gi with X-strap
    drawShadedTorso(ctx, 0, p.tY, p.sw, p.ww, p.tH, c.primary, darker(c.primary, 12));
    ctx.strokeStyle = c.accent; ctx.lineWidth = 2.2;
    ctx.beginPath(); ctx.moveTo(-p.sw + 4, p.tY + 5); ctx.lineTo(p.sw - 4, p.tY + p.tH - 5); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(p.sw - 4, p.tY + 5); ctx.lineTo(-p.sw + 4, p.tY + p.tH - 5); ctx.stroke();
    // Belt
    oRect(ctx, -p.sw, p.tY + p.tH - 5, p.sw * 2, 5, 2, '#1a0d3d', '#0d0620');
    ctx.fillStyle = '#ffd700'; ctx.fillRect(-3, p.tY + p.tH - 4, 6, 3);

    // Front leg
    drawFullLeg(ctx, 8, p.legY, P.rightLegAngle, p.legLen, p.legW, c.secondary, '#111', 9);
    // Front arm
    drawShadedLimb(ctx, p.sw, p.tY + 4, P.rightArmAngle, p.armLen, p.armW, c.skin, { isArm: true, cloth: c.primary, splitAt: 0.45 });

    // Head
    drawShadedHead(ctx, 0, p.hY, p.hR, c.skin);
    // Ninja mask
    oPath(ctx, function(ct) {
        ct.beginPath(); ct.moveTo(-p.hR, p.hY + 1);
        ct.quadraticCurveTo(-p.hR - 1, p.hY + p.hR * 0.8, -p.hR * 0.5, p.hY + p.hR);
        ct.lineTo(p.hR * 0.6, p.hY + p.hR);
        ct.quadraticCurveTo(p.hR + 1, p.hY + p.hR * 0.8, p.hR, p.hY + 1);
        ct.closePath();
    }, c.secondary, darker(c.secondary, 18));
    // Hair — slicked back + ponytail
    oPath(ctx, function(ct) { ct.beginPath(); ct.ellipse(0, p.hY - 3, p.hR + 1, p.hR * 0.65, 0, Math.PI * 0.85, Math.PI * 2.15); ct.closePath(); }, c.hair, darker(c.hair, 14));
    ctx.strokeStyle = c.hair; ctx.lineWidth = 4.5; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(-p.hR * 0.6, p.hY);
    for (var pi = 1; pi <= 5; pi++) ctx.lineTo(-p.hR * 0.6 - pi * 6, p.hY + Math.sin(t * 3.5 + pi * 0.7) * 4.5 + pi * 2.8);
    ctx.stroke();
    ctx.strokeStyle = darker(c.hair, 18); ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(-p.hR * 0.6, p.hY);
    for (var pj = 1; pj <= 5; pj++) ctx.lineTo(-p.hR * 0.6 - pj * 6, p.hY + Math.sin(t * 3.5 + pj * 0.7) * 4.5 + pj * 2.8);
    ctx.stroke(); ctx.lineCap = 'butt';

    // Eye above mask — intense red glow
    ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.ellipse(p.hR * 0.32, p.hY - 1.5, 4, 2.5, 0, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = OC; ctx.lineWidth = 0.8; ctx.stroke();
    ctx.fillStyle = c.eye; ctx.beginPath(); ctx.ellipse(p.hR * 0.38, p.hY - 1.5, 2.5, 2, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#000'; ctx.beginPath(); ctx.arc(p.hR * 0.42, p.hY - 1.5, 1, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(p.hR * 0.5, p.hY - 2.3, 0.7, 0, Math.PI * 2); ctx.fill();
    // Eye glow
    ctx.shadowColor = c.eye; ctx.shadowBlur = 6;
    ctx.fillStyle = rgba(c.eye, 0.3); ctx.beginPath(); ctx.ellipse(p.hR * 0.35, p.hY - 1.5, 5, 3, 0, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0;
    // Brow
    ctx.strokeStyle = c.skin; ctx.lineWidth = 2.2;
    ctx.beginPath(); ctx.moveTo(0, p.hY - 4); ctx.quadraticCurveTo(p.hR * 0.35, p.hY - 7, p.hR * 0.75, p.hY - 5); ctx.stroke();

    // Flowing scarf — multilayer
    var scarfColors = [c.accent, lighter(c.accent, 18), darker(c.accent, 12)];
    for (var sl = 0; sl < 3; sl++) {
        ctx.strokeStyle = scarfColors[sl]; ctx.lineWidth = 5 - sl * 1.3; ctx.lineCap = 'round';
        ctx.beginPath(); ctx.moveTo(-4, p.hY + 6);
        for (var si = 1; si <= 6; si++) ctx.lineTo(-4 - si * 6 + sl * 1.5, p.hY + 6 + Math.sin(t * 4 + si * 0.7 + sl * 0.3) * 6 + si * 3.5);
        ctx.stroke();
    }
    ctx.lineCap = 'butt';

    // Shadow wisps at feet
    if (f.state === 'idle' || f.state === 'walk') {
        ctx.globalAlpha = 0.18; _seed = Math.floor(t * 3);
        for (var sw = 0; sw < 3; sw++) { ctx.fillStyle = c.glow; ctx.beginPath(); ctx.ellipse(sfx_range(-14, 14), sfx_range(-4, 3), sfx_range(3, 9), 2, 0, 0, Math.PI * 2); ctx.fill(); }
        ctx.globalAlpha = 1;
    }
}

// ── ROOK — Iron Titan (Heavy Knight) ────────────────────────
function drawRook(ctx, f, P) {
    var c = f.character.colors, b = f.character.body, t = f.animTime, bY = P.bodyOffsetY;
    var p = bodyPos(b, bY);

    // Cape behind everything
    oPath(ctx, function(ct) {
        ct.beginPath(); ct.moveTo(-p.sw - 2, p.tY + 6);
        ct.quadraticCurveTo(-p.sw - 5 + Math.sin(t * 1.8) * 3, p.tY + p.tH + 8, -p.sw + 4 + Math.sin(t * 2) * 4, -3 + bY);
        ct.lineTo(p.sw - 4 + Math.sin(t * 2 + 1) * 4, -3 + bY);
        ct.quadraticCurveTo(p.sw + 5 + Math.sin(t * 1.8 + 1) * 3, p.tY + p.tH + 8, p.sw + 2, p.tY + 6);
        ct.closePath();
    }, '#5a1515', '#3a0a0a');

    // Back leg (armoured)
    drawFullLeg(ctx, -10, p.legY, P.leftLegAngle, p.legLen, p.legW, c.secondary, '#2a2a2a', 12, { kneePad: c.primary });
    // Back arm (gauntlet)
    drawShadedLimb(ctx, -p.sw - 3, p.tY + 6, P.leftArmAngle, p.armLen, p.armW, c.skin, { isArm: true, cloth: c.primary, glove: '#3a3a4a', splitAt: 0.3 });

    // Torso — heavy plate
    drawShadedTorso(ctx, 0, p.tY, p.sw, p.ww, p.tH, c.primary, c.secondary, { neckW: p.sw * 0.38 });
    // Plate lines
    ctx.strokeStyle = rgba(c.accent, 0.55); ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, p.tY + 5); ctx.lineTo(0, p.tY + p.tH - 7); ctx.stroke();
    for (var al = 0; al < 3; al++) { ctx.beginPath(); ctx.moveTo(-p.sw + 3, p.tY + 10 + al * (p.tH / 4)); ctx.lineTo(p.sw - 3, p.tY + 10 + al * (p.tH / 4)); ctx.stroke(); }
    // Central emblem
    ctx.fillStyle = c.accent;
    ctx.beginPath(); ctx.moveTo(0, p.tY + 12); ctx.lineTo(-4.5, p.tY + 17); ctx.lineTo(0, p.tY + 22); ctx.lineTo(4.5, p.tY + 17); ctx.closePath(); ctx.fill();
    // Belt
    oRect(ctx, -p.sw - 1, p.tY + p.tH - 6, (p.sw + 1) * 2, 6, 2, '#3a2815', '#2a1a0a');
    ctx.fillStyle = c.accent; ctx.fillRect(-4, p.tY + p.tH - 5, 8, 4);

    // Shoulder pauldrons
    for (var sd = -1; sd <= 1; sd += 2) {
        var sx = sd * (p.sw + 5);
        oEllipse(ctx, sx, p.tY + 5, p.armW, p.armW * 0.78, c.primary, darker(c.primary, 28));
        ctx.strokeStyle = c.accent; ctx.lineWidth = 0.8;
        ctx.beginPath(); ctx.ellipse(sx, p.tY + 5, p.armW * 0.75, p.armW * 0.6, 0, 0, Math.PI * 2); ctx.stroke();
        oPath(ctx, function(ct) { ct.beginPath(); ct.moveTo(sx, p.tY - 3); ct.lineTo(sx - 2.5, p.tY + 3); ct.lineTo(sx + 2.5, p.tY + 3); ct.closePath(); }, c.accent, darker(c.accent, 18));
    }

    // Front leg
    drawFullLeg(ctx, 10, p.legY, P.rightLegAngle, p.legLen, p.legW, c.secondary, '#2a2a2a', 12, { kneePad: c.primary });
    // Front arm
    drawShadedLimb(ctx, p.sw + 3, p.tY + 6, P.rightArmAngle, p.armLen, p.armW, c.skin, { isArm: true, cloth: c.primary, glove: '#3a3a4a', splitAt: 0.3 });

    // Head — helmet with T-visor
    oEllipse(ctx, 0, p.hY, p.hR + 2, p.hR + 2, c.primary, darker(c.primary, 24));
    // Crest
    oPath(ctx, function(ct) { ct.beginPath(); ct.moveTo(-2.5, p.hY - p.hR - 14); ct.lineTo(-3, p.hY - p.hR + 1); ct.lineTo(3, p.hY - p.hR + 1); ct.lineTo(2.5, p.hY - p.hR - 14); ct.closePath(); }, '#4a4a5a', '#333340');
    // T-Visor
    ctx.fillStyle = c.eye; ctx.shadowColor = c.eye; ctx.shadowBlur = 8;
    ctx.fillRect(-p.hR * 0.7, p.hY - 3, p.hR * 1.4, 3);
    ctx.fillRect(-2, p.hY - 3, 4, p.hR * 0.55);
    ctx.shadowBlur = 0;
    ctx.strokeStyle = darker(c.primary, 35); ctx.lineWidth = 0.8;
    ctx.strokeRect(-p.hR * 0.7, p.hY - 3, p.hR * 1.4, 3);
}

// ── ZARA — Storm Dancer (Acrobat) ───────────────────────────
function drawZara(ctx, f, P) {
    var c = f.character.colors, b = f.character.body, t = f.animTime, bY = P.bodyOffsetY;
    var p = bodyPos(b, bY);

    // Back leg
    drawFullLeg(ctx, -7, p.legY, P.leftLegAngle, p.legLen, p.legW, c.secondary, '#148a6a', 8);
    // Back arm + wraps
    drawShadedLimb(ctx, -p.sw, p.tY + 4, P.leftArmAngle, p.armLen, p.armW, c.skin, { isArm: true });
    ctx.save(); ctx.translate(-p.sw, p.tY + 4); ctx.rotate(degToRad(P.leftArmAngle));
    ctx.strokeStyle = '#f0f0f0'; ctx.lineWidth = 1.8;
    for (var w = 0; w < 5; w++) { ctx.beginPath(); ctx.moveTo(-4, p.armLen * 0.55 + w * 2.5); ctx.lineTo(4, p.armLen * 0.56 + w * 2.5); ctx.stroke(); }
    ctx.restore();

    // Torso — crop top
    drawShadedTorso(ctx, 0, p.tY, p.sw, p.ww, p.tH, c.primary, c.secondary, { neckW: p.sw * 0.28 });
    ctx.strokeStyle = lighter(c.primary, 28); ctx.lineWidth = 1.3;
    ctx.beginPath(); ctx.moveTo(-p.sw * 0.6, p.tY + 2); ctx.lineTo(0, p.tY + p.tH * 0.4); ctx.lineTo(p.sw * 0.6, p.tY + 2); ctx.stroke();
    // Exposed midriff
    oRect(ctx, -p.ww, p.tY + p.tH - p.tH * 0.3, p.ww * 2, p.tH * 0.3, 2, c.skin, darker(c.skin, 18));
    ctx.fillStyle = darker(c.skin, 22); ctx.beginPath(); ctx.arc(0, p.tY + p.tH - p.tH * 0.12, 1.2, 0, Math.PI * 2); ctx.fill();
    // Shorts band
    oRect(ctx, -p.sw, p.tY + p.tH - 2, p.sw * 2, 3.5, 2, c.accent, darker(c.accent, 18));

    // Front leg
    drawFullLeg(ctx, 7, p.legY, P.rightLegAngle, p.legLen, p.legW, c.secondary, '#148a6a', 8);
    // Front arm + wraps
    drawShadedLimb(ctx, p.sw, p.tY + 4, P.rightArmAngle, p.armLen, p.armW, c.skin, { isArm: true });
    ctx.save(); ctx.translate(p.sw, p.tY + 4); ctx.rotate(degToRad(P.rightArmAngle));
    ctx.strokeStyle = '#f0f0f0'; ctx.lineWidth = 1.8;
    for (var w2 = 0; w2 < 5; w2++) { ctx.beginPath(); ctx.moveTo(-4, p.armLen * 0.55 + w2 * 2.5); ctx.lineTo(4, p.armLen * 0.56 + w2 * 2.5); ctx.stroke(); }
    ctx.restore();

    // Head
    drawShadedHead(ctx, 0, p.hY, p.hR, c.skin);
    // Flowing white hair
    oPath(ctx, function(ct) { ct.beginPath(); ct.ellipse(0, p.hY - 3, p.hR + 3, p.hR * 0.8, 0, Math.PI * 0.82, Math.PI * 2.18); ct.closePath(); }, c.hair, '#ccc');
    for (var hs = 0; hs < 5; hs++) {
        ctx.strokeStyle = hs % 2 === 0 ? c.hair : '#d0d0d0'; ctx.lineWidth = 3 - hs * 0.3; ctx.lineCap = 'round';
        ctx.beginPath(); ctx.moveTo(-p.hR * 0.5 - hs * 2, p.hY + hs * 2.5);
        ctx.quadraticCurveTo(-p.hR - hs * 4 + Math.sin(t * 3 + hs) * 5, p.hY + hs * 4, -p.hR - hs * 5 + Math.sin(t * 3 + hs) * 8, p.hY + 4 + hs * 5);
        ctx.stroke();
    }
    ctx.lineCap = 'butt';
    // Face
    drawExpressiveEyes(ctx, 0, p.hY, p.hR, c.eye, f.state);
    drawExpressiveMouth(ctx, 0, p.hY, p.hR, f.state);

    // Lightning VFX
    ctx.strokeStyle = c.accent; ctx.lineWidth = 1.6;
    ctx.shadowColor = c.accent; ctx.shadowBlur = 5;
    ctx.globalAlpha = 0.45 + Math.sin(t * 14) * 0.25;
    _seed = Math.floor(t * 6);
    for (var li = 0; li < 4; li++) {
        var lx = sfx_range(-p.sw - 4, p.sw + 4), ly = p.tY + sfx_range(0, p.tH + 16);
        ctx.beginPath(); ctx.moveTo(lx, ly);
        ctx.lineTo(lx + sfx_range(-10, 10), ly + sfx_range(-10, 10));
        ctx.lineTo(lx + sfx_range(-14, 14), ly + sfx_range(-14, 14));
        ctx.stroke();
    }
    ctx.shadowBlur = 0; ctx.globalAlpha = 1;
}

// ── VEX — Venom Fang (Hooded Assassin) ──────────────────────
function drawVex(ctx, f, P) {
    var c = f.character.colors, b = f.character.body, t = f.animTime, bY = P.bodyOffsetY;
    var p = bodyPos(b, bY);

    // Back leg
    drawFullLeg(ctx, -7, p.legY, P.leftLegAngle, p.legLen, p.legW, '#162a1a', '#0a1a0e', 9);
    // Back arm — bare with vein glows
    drawShadedLimb(ctx, -p.sw, p.tY + 5, P.leftArmAngle, p.armLen, p.armW, c.skin, { isArm: true });
    ctx.save(); ctx.translate(-p.sw, p.tY + 5); ctx.rotate(degToRad(P.leftArmAngle));
    ctx.strokeStyle = c.accent; ctx.lineWidth = 1.1; ctx.shadowColor = c.accent; ctx.shadowBlur = 4;
    ctx.globalAlpha = 0.45 + Math.sin(t * 3) * 0.25;
    ctx.beginPath(); ctx.moveTo(-2, 3); ctx.quadraticCurveTo(-3.5, p.armLen * 0.5, 0, p.armLen * 0.85); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(1.5, 4); ctx.quadraticCurveTo(3, p.armLen * 0.55, 0.5, p.armLen * 0.9); ctx.stroke();
    ctx.shadowBlur = 0; ctx.globalAlpha = 1; ctx.restore();

    // Torso — hooded cloak
    drawShadedTorso(ctx, 0, p.tY, p.sw, p.ww, p.tH, c.primary, '#0d2614', { neckW: p.sw * 0.3 });
    ctx.strokeStyle = darker(c.primary, 18); ctx.lineWidth = 0.8;
    ctx.beginPath(); ctx.moveTo(-p.sw * 0.7, p.tY + 5); ctx.quadraticCurveTo(0, p.tY + 8, p.sw * 0.7, p.tY + 5); ctx.stroke();
    // Clasp
    ctx.fillStyle = '#888'; ctx.beginPath(); ctx.arc(0, p.tY + 5, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = c.accent; ctx.beginPath(); ctx.arc(0, p.tY + 5, 2.2, 0, Math.PI * 2); ctx.fill();
    // Poison vial belt
    oRect(ctx, -p.sw, p.tY + p.tH - 5, p.sw * 2, 5, 2, '#1a3020', '#0d2010');
    for (var vi = 0; vi < 4; vi++) { oRect(ctx, -p.sw * 0.6 + vi * (p.sw * 0.35), p.tY + p.tH - 9, 3.5, 6, 1, c.accent, darker(c.accent, 28)); ctx.fillStyle = '#1a3020'; ctx.fillRect(-p.sw * 0.6 + vi * (p.sw * 0.35), p.tY + p.tH - 9, 3.5, 1.5); }

    // Front leg
    drawFullLeg(ctx, 7, p.legY, P.rightLegAngle, p.legLen, p.legW, '#162a1a', '#0a1a0e', 9);
    // Front arm
    drawShadedLimb(ctx, p.sw, p.tY + 5, P.rightArmAngle, p.armLen, p.armW, c.skin, { isArm: true });
    ctx.save(); ctx.translate(p.sw, p.tY + 5); ctx.rotate(degToRad(P.rightArmAngle));
    ctx.strokeStyle = c.accent; ctx.lineWidth = 1.1; ctx.shadowColor = c.accent; ctx.shadowBlur = 4;
    ctx.globalAlpha = 0.45 + Math.sin(t * 3 + 1) * 0.25;
    ctx.beginPath(); ctx.moveTo(0, 4); ctx.quadraticCurveTo(-2.5, p.armLen * 0.5, 1, p.armLen * 0.88); ctx.stroke();
    ctx.shadowBlur = 0; ctx.globalAlpha = 1; ctx.restore();

    // Head
    drawShadedHead(ctx, 0, p.hY, p.hR, c.skin);
    // Hood
    oPath(ctx, function(ct) {
        ct.beginPath(); ct.moveTo(-p.hR - 3, p.hY + 4);
        ct.quadraticCurveTo(-p.hR - 5, p.hY - p.hR * 0.8, -p.hR * 0.35, p.hY - p.hR - 5);
        ct.quadraticCurveTo(p.hR * 0.2, p.hY - p.hR - 7, p.hR * 0.7, p.hY - p.hR - 3);
        ct.quadraticCurveTo(p.hR + 2, p.hY - p.hR * 0.6, p.hR, p.hY + 4);
        ct.quadraticCurveTo(0, p.hY + 2, -p.hR - 3, p.hY + 4);
        ct.closePath();
    }, c.primary, darker(c.primary, 18));
    // Hood shadow
    ctx.fillStyle = 'rgba(0,0,0,0.3)'; ctx.beginPath(); ctx.ellipse(0, p.hY, p.hR * 0.8, p.hR * 0.4, 0, 0, Math.PI); ctx.fill();
    // Glowing eyes from shadow
    ctx.shadowColor = c.eye; ctx.shadowBlur = 10;
    ctx.fillStyle = c.eye;
    ctx.beginPath(); ctx.ellipse(p.hR * 0.32, p.hY - 2, 3, 1.8, 0.1, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(-p.hR * 0.28, p.hY - 2, 2.5, 1.5, -0.1, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(p.hR * 0.4, p.hY - 2.8, 0.9, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0;

    // Poison mist at feet
    ctx.globalAlpha = 0.13; _seed = Math.floor(t * 2.5);
    for (var pm = 0; pm < 5; pm++) { ctx.fillStyle = c.accent; ctx.beginPath(); ctx.ellipse(sfx_range(-22, 22), sfx_range(-5, 3), sfx_range(5, 12), sfx_range(2.5, 5), 0, 0, Math.PI * 2); ctx.fill(); }
    ctx.globalAlpha = 1;
}

// ── FREYA — Frost Sentinel (Ice Warrior) ────────────────────
function drawFreya(ctx, f, P) {
    var c = f.character.colors, b = f.character.body, t = f.animTime, bY = P.bodyOffsetY;
    var p = bodyPos(b, bY);

    // Armoured skirt behind legs
    oPath(ctx, function(ct) {
        ct.beginPath(); ct.moveTo(-p.sw - 2, p.tY + p.tH - 2);
        ct.quadraticCurveTo(-p.sw - 5 + Math.sin(t * 2) * 3, p.tY + p.tH + 8, -p.sw + 2 + Math.sin(t * 2.5) * 3, -3 + bY);
        ct.lineTo(p.sw - 2 + Math.sin(t * 2.5 + 1) * 3, -3 + bY);
        ct.quadraticCurveTo(p.sw + 5 + Math.sin(t * 2 + 1) * 3, p.tY + p.tH + 8, p.sw + 2, p.tY + p.tH - 2);
        ct.closePath();
    }, c.secondary, darker(c.secondary, 18));
    ctx.strokeStyle = rgba(c.accent, 0.3); ctx.lineWidth = 0.6;
    for (var sf = -2; sf <= 2; sf++) { ctx.beginPath(); ctx.moveTo(sf * 6, p.tY + p.tH); ctx.lineTo(sf * 7, -4 + bY); ctx.stroke(); }

    // Back leg
    drawFullLeg(ctx, -7, p.legY, P.leftLegAngle, p.legLen, p.legW, c.secondary, '#1a4a6a', 8);
    // Back arm
    drawShadedLimb(ctx, -p.sw, p.tY + 5, P.leftArmAngle, p.armLen, p.armW, c.skin, { isArm: true, cloth: c.primary, splitAt: 0.45 });

    // Torso — armoured bodice
    drawShadedTorso(ctx, 0, p.tY, p.sw, p.ww, p.tH, c.primary, c.secondary, { neckW: p.sw * 0.25 });
    ctx.strokeStyle = lighter(c.accent, 18); ctx.lineWidth = 1.3;
    ctx.beginPath(); ctx.moveTo(-p.sw * 0.65, p.tY + 4); ctx.quadraticCurveTo(0, p.tY + p.tH * 0.5, p.sw * 0.65, p.tY + 4); ctx.stroke();
    // Centre gem
    ctx.fillStyle = '#a8d8ff'; ctx.shadowColor = '#85c1e9'; ctx.shadowBlur = 7;
    ctx.beginPath(); ctx.moveTo(0, p.tY + 8); ctx.lineTo(-4.5, p.tY + 13); ctx.lineTo(0, p.tY + 18); ctx.lineTo(4.5, p.tY + 13); ctx.closePath(); ctx.fill();
    ctx.shadowBlur = 0;
    // Belt
    oRect(ctx, -p.sw, p.tY + p.tH - 4, p.sw * 2, 4, 2, '#1a4a6a', '#0d3050');
    ctx.fillStyle = '#a8d8ff'; ctx.fillRect(-2.5, p.tY + p.tH - 3, 5, 2.5);

    // Front leg
    drawFullLeg(ctx, 7, p.legY, P.rightLegAngle, p.legLen, p.legW, c.secondary, '#1a4a6a', 8);
    // Front arm
    drawShadedLimb(ctx, p.sw, p.tY + 5, P.rightArmAngle, p.armLen, p.armW, c.skin, { isArm: true, cloth: c.primary, splitAt: 0.45 });

    // Head
    drawShadedHead(ctx, 0, p.hY, p.hR, c.skin);
    // Long blue hair
    oPath(ctx, function(ct) { ct.beginPath(); ct.ellipse(-1, p.hY - 3, p.hR + 3, p.hR * 0.8, 0, Math.PI * 0.82, Math.PI * 2.18); ct.closePath(); }, c.hair, darker(c.hair, 14));
    oPath(ctx, function(ct) {
        ct.beginPath(); ct.moveTo(-p.hR, p.hY + 1);
        ct.quadraticCurveTo(-p.hR - 3 + Math.sin(t * 2) * 2.5, p.hY + p.hR * 1.5, -p.hR + 2 + Math.sin(t * 2.5) * 3, p.hY + p.hR * 2.5);
        ct.lineTo(-p.hR * 0.3 + Math.sin(t * 2.5) * 2, p.hY + p.hR * 2.5);
        ct.quadraticCurveTo(-p.hR * 0.5, p.hY + p.hR, -p.hR * 0.6, p.hY + 1);
        ct.closePath();
    }, c.hair, darker(c.hair, 10));
    // Ice crown/tiara
    for (var cr = -2; cr <= 2; cr++) {
        var crH = cr === 0 ? 11 : (Math.abs(cr) === 1 ? 7 : 5);
        oPath(ctx, function(ct) { ct.beginPath(); ct.moveTo(cr * 5 - 2, p.hY - p.hR - 1); ct.lineTo(cr * 5, p.hY - p.hR - 1 - crH); ct.lineTo(cr * 5 + 2, p.hY - p.hR - 1); ct.closePath(); }, '#b8e6ff', '#8ac8e8');
    }
    drawGlow(ctx, 0, p.hY - p.hR - 6, 12, '#85c1e9', 0.22);
    // Face
    drawExpressiveEyes(ctx, 0, p.hY, p.hR, c.eye, f.state);
    drawExpressiveMouth(ctx, 0, p.hY, p.hR, f.state);

    // Frost particles
    ctx.globalAlpha = 0.35; _seed = Math.floor(t * 4);
    for (var fp = 0; fp < 5; fp++) {
        ctx.fillStyle = '#b8e6ff';
        var fx = sfx_range(-p.sw - 6, p.sw + 6), fy = p.tY + sfx_range(-8, p.tH + 12);
        ctx.beginPath(); ctx.moveTo(fx, fy - 3.5); ctx.lineTo(fx + 2.5, fy); ctx.lineTo(fx, fy + 3.5); ctx.lineTo(fx - 2.5, fy); ctx.closePath(); ctx.fill();
    }
    ctx.globalAlpha = 1;
}

// ── DRAKE — Inferno (Berserker) ─────────────────────────────
function drawDrake(ctx, f, P) {
    var c = f.character.colors, b = f.character.body, t = f.animTime, bY = P.bodyOffsetY;
    var p = bodyPos(b, bY);
    var rage = f.rageActive;

    // Fire ground glow when raging
    if (rage) drawGlow(ctx, 0, -4, 40, c.accent, 0.32 + Math.sin(t * 8) * 0.08);

    // Back leg
    drawFullLeg(ctx, -9, p.legY, P.leftLegAngle, p.legLen, p.legW, '#3d1a0a', '#1a0a04', 10);
    // Back arm — bare muscular
    drawShadedLimb(ctx, -p.sw, p.tY + 5, P.leftArmAngle, p.armLen, p.armW, c.skin, { isArm: true, bulge: 1.22 });
    // Flame tattoo on arm
    ctx.save(); ctx.translate(-p.sw, p.tY + 5); ctx.rotate(degToRad(P.leftArmAngle));
    ctx.strokeStyle = c.accent; ctx.lineWidth = 1.3; ctx.shadowColor = c.accent; ctx.shadowBlur = rage ? 5 : 2;
    ctx.globalAlpha = 0.45 + (rage ? 0.35 : 0);
    ctx.beginPath(); ctx.moveTo(-1.5, 4); ctx.quadraticCurveTo(-4, p.armLen * 0.45, -0.5, p.armLen * 0.75); ctx.quadraticCurveTo(2.5, p.armLen * 0.52, 3, p.armLen * 0.3); ctx.stroke();
    ctx.shadowBlur = 0; ctx.globalAlpha = 1; ctx.restore();

    // Torso — SHIRTLESS, muscular
    drawShadedTorso(ctx, 0, p.tY, p.sw, p.ww, p.tH, c.skin, darker(c.skin, 12), { neckW: p.sw * 0.36 });
    // Muscle definition
    ctx.strokeStyle = 'rgba(0,0,0,0.12)'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.arc(-p.sw * 0.35, p.tY + p.tH * 0.38, p.sw * 0.38, 0.3, Math.PI - 0.3); ctx.stroke();
    ctx.beginPath(); ctx.arc(p.sw * 0.35, p.tY + p.tH * 0.38, p.sw * 0.38, 0.3, Math.PI - 0.3); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, p.tY + p.tH * 0.28); ctx.lineTo(0, p.tY + p.tH - 3); ctx.stroke();
    for (var ab = 0; ab < 3; ab++) { ctx.beginPath(); ctx.moveTo(-p.ww * 0.5, p.tY + p.tH * 0.55 + ab * (p.tH * 0.13)); ctx.quadraticCurveTo(0, p.tY + p.tH * 0.53 + ab * (p.tH * 0.13), p.ww * 0.5, p.tY + p.tH * 0.55 + ab * (p.tH * 0.13)); ctx.stroke(); }
    // Flame tattoos on torso
    ctx.strokeStyle = c.accent; ctx.lineWidth = 1.5; ctx.shadowColor = c.accent; ctx.shadowBlur = rage ? 7 : 2;
    ctx.globalAlpha = 0.38 + (rage ? 0.35 : 0);
    ctx.beginPath(); ctx.moveTo(-p.sw * 0.9, p.tY + p.tH); ctx.quadraticCurveTo(-p.sw, p.tY + p.tH * 0.6, -p.sw * 0.65, p.tY + p.tH * 0.35); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(p.sw * 0.9, p.tY + p.tH); ctx.quadraticCurveTo(p.sw, p.tY + p.tH * 0.6, p.sw * 0.65, p.tY + p.tH * 0.35); ctx.stroke();
    // Chest scar
    ctx.strokeStyle = 'rgba(180,80,60,0.35)'; ctx.lineWidth = 1.3;
    ctx.beginPath(); ctx.moveTo(-p.sw * 0.4, p.tY + p.tH * 0.4); ctx.lineTo(p.sw * 0.2, p.tY + p.tH * 0.55); ctx.stroke();
    ctx.shadowBlur = 0; ctx.globalAlpha = 1;
    // Torn cloth waistband
    oRect(ctx, -p.sw, p.tY + p.tH - 4, p.sw * 2, 4, 2, '#3d1a0a', '#2a0d04');
    ctx.fillStyle = '#4a1a0a';
    for (var tc = 0; tc < 3; tc++) {
        var tx = -p.sw * 0.6 + tc * p.sw * 0.55;
        ctx.beginPath(); ctx.moveTo(tx, p.tY + p.tH); ctx.lineTo(tx - 1.5, p.tY + p.tH + 6 + Math.sin(t * 3 + tc) * 1.5);
        ctx.lineTo(tx + 3.5, p.tY + p.tH + 4.5 + Math.sin(t * 3 + tc + 1) * 1.5); ctx.lineTo(tx + 2, p.tY + p.tH); ctx.fill();
    }

    // Front leg
    drawFullLeg(ctx, 9, p.legY, P.rightLegAngle, p.legLen, p.legW, '#3d1a0a', '#1a0a04', 10);
    // Front arm
    drawShadedLimb(ctx, p.sw, p.tY + 5, P.rightArmAngle, p.armLen, p.armW, c.skin, { isArm: true, bulge: 1.22 });
    ctx.save(); ctx.translate(p.sw, p.tY + 5); ctx.rotate(degToRad(P.rightArmAngle));
    ctx.strokeStyle = c.accent; ctx.lineWidth = 1.3; ctx.shadowColor = c.accent; ctx.shadowBlur = rage ? 5 : 2;
    ctx.globalAlpha = 0.45 + (rage ? 0.35 : 0);
    ctx.beginPath(); ctx.moveTo(0.5, 3); ctx.quadraticCurveTo(4, p.armLen * 0.45, 0.5, p.armLen * 0.8); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-1.5, 5); ctx.quadraticCurveTo(-4, p.armLen * 0.5, -0.5, p.armLen * 0.85); ctx.stroke();
    ctx.shadowBlur = 0; ctx.globalAlpha = 1; ctx.restore();

    // Head
    drawShadedHead(ctx, 0, p.hY, p.hR, c.skin);
    // Wild spiky hair
    oPath(ctx, function(ct) { ct.beginPath(); ct.ellipse(0, p.hY - 4, p.hR + 3, p.hR * 0.78, 0, Math.PI * 0.75, Math.PI * 2.25); ct.closePath(); }, c.hair, darker(c.hair, 12));
    var spikes = [[-0.7, 14], [-0.35, 18], [0, 16], [0.3, 20], [0.6, 14], [0.85, 12]];
    for (var sp = 0; sp < spikes.length; sp++) {
        var sa = spikes[sp][0], sLen = spikes[sp][1];
        var sInR = p.hR + 2;
        oPath(ctx, function(ct) {
            ct.beginPath();
            ct.moveTo(Math.cos(sa - 1.55) * sInR, p.hY - 4 + Math.sin(sa - 1.55) * (sInR * 0.78));
            ct.lineTo(Math.cos(sa - 1.5) * (sInR + sLen) + Math.sin(t * 4 + sp) * 1.5, p.hY - 4 + Math.sin(sa - 1.5) * ((sInR + sLen) * 0.5));
            ct.lineTo(Math.cos(sa - 1.45) * sInR, p.hY - 4 + Math.sin(sa - 1.45) * (sInR * 0.78));
            ct.closePath();
        }, sp % 2 === 0 ? c.hair : '#ff4422', darker(c.hair, 8));
    }
    // Glowing tips when raging
    if (rage) {
        for (var ht = 0; ht < spikes.length; ht++) {
            var ha = spikes[ht][0], hLen = spikes[ht][1];
            var htx = Math.cos(ha - 1.5) * (p.hR + 2 + hLen) + Math.sin(t * 4 + ht) * 1.5;
            var hty = p.hY - 4 + Math.sin(ha - 1.5) * ((p.hR + 2 + hLen) * 0.5);
            drawGlow(ctx, htx, hty, 5, c.accent, 0.35);
        }
    }
    // Face — fierce
    drawExpressiveEyes(ctx, 0, p.hY, p.hR, c.eye, f.state);
    // Permanent snarl
    var mx = p.hR * 0.18 + 2, my = p.hY + p.hR * 0.42;
    oEllipse(ctx, mx, my, 4.5, 2.8, '#2a0505', '#1a0000');
    ctx.fillStyle = '#ddd'; ctx.fillRect(mx - 3.5, my - 1.3, 7, 1.3); ctx.fillRect(mx - 3, my + 1, 6, 1);

    // Fire particles
    var fCount = rage ? 10 : 3;
    ctx.globalAlpha = rage ? 0.6 : 0.25;
    _seed = Math.floor(t * 8);
    for (var fi = 0; fi < fCount; fi++) drawFlameShape(ctx, sfx_range(-22, 22), p.tY + p.tH - sfx_range(0, 45), sfx_range(2.5, rage ? 8 : 5), c.accent, '#ff2200');
    ctx.globalAlpha = 1;
}


// ═══════════════════════════════════════════════════════════
//   DISPATCH & OVERRIDE
// ═══════════════════════════════════════════════════════════

var DRAW_MAP = {
    'kai': drawKai, 'rook': drawRook, 'zara': drawZara,
    'vex': drawVex, 'freya': drawFreya, 'drake': drawDrake
};

Fighter.prototype.render = function(ctx) {
    var c = this.character;
    var dir = this.facingRight ? 1 : -1;
    var pose = this._getPose();

    ctx.save();
    ctx.translate(this.x, this.y);
    ctx.scale(dir * SCALE, SCALE);

    // Hit flash
    if (this.hurtFlash > 0 && Math.floor(this.hurtFlash * 30) % 2 === 0) ctx.globalAlpha = 0.5;
    // Freeze tint
    if (this.freezeTimer > 0) ctx.globalAlpha = 0.65;

    // Ground shadow (oval, soft)
    ctx.fillStyle = 'rgba(0,0,0,0.38)';
    ctx.beginPath(); ctx.ellipse(0, 0, 22, 5, 0, 0, Math.PI * 2); ctx.fill();

    // Character body
    var fn = DRAW_MAP[c.id];
    if (fn) fn(ctx, this, pose);

    // Weapon
    var sw = (c.body.shoulderW || c.body.torsoW + 4) * 0.5;
    var armLen = c.body.armLen;
    var shoulderY = -(c.body.legLen + c.body.torsoH) + pose.bodyOffsetY + 4;
    var hx = sw + Math.sin(degToRad(pose.rightArmAngle)) * armLen;
    var hy = shoulderY + Math.cos(degToRad(pose.rightArmAngle)) * armLen * 0.3;
    this._drawWeapon(ctx, hx, hy, pose.weaponAngle);

    // Block shield (energy arc)
    if (this.isBlocking) {
        ctx.strokeStyle = 'rgba(100,200,255,0.7)'; ctx.lineWidth = 3;
        ctx.shadowColor = 'rgba(100,200,255,0.5)'; ctx.shadowBlur = 14;
        ctx.beginPath(); ctx.arc(12, -(c.body.legLen + c.body.torsoH * 0.5), 38, -Math.PI * 0.65, Math.PI * 0.65); ctx.stroke();
        ctx.strokeStyle = 'rgba(180,230,255,0.3)'; ctx.lineWidth = 7;
        ctx.beginPath(); ctx.arc(12, -(c.body.legLen + c.body.torsoH * 0.5), 34, -Math.PI * 0.55, Math.PI * 0.55); ctx.stroke();
        ctx.shadowBlur = 0;
    }

    // Freeze crystals
    if (this.freezeTimer > 0) {
        ctx.fillStyle = 'rgba(180,220,255,0.45)';
        _seed = 999;
        for (var ic = 0; ic < 6; ic++) {
            var ix = sfx_range(-22, 22), iy = sfx_range(-(c.body.legLen + c.body.torsoH + c.body.headR * 2), -8);
            ctx.beginPath(); ctx.moveTo(ix, iy - 5); ctx.lineTo(ix + 3.5, iy); ctx.lineTo(ix, iy + 5); ctx.lineTo(ix - 3.5, iy); ctx.closePath(); ctx.fill();
        }
    }

    ctx.restore();

    // Poison overlay (outside main transform)
    if (this.poisonTimer > 0) {
        ctx.save(); ctx.globalAlpha = 0.18; ctx.fillStyle = '#00ff66';
        ctx.beginPath(); ctx.arc(this.x, this.y - this.height * 0.5, 32 + Math.sin(this.animTime * 5) * 4, 0, Math.PI * 2); ctx.fill();
        ctx.restore();
    }

    // Combo counter (premium)
    if (this.comboCount > 1) {
        ctx.save();
        ctx.textAlign = 'center';
        var cScale = 1 + Math.sin(this.comboTimer / 100) * 0.08;
        ctx.translate(this.x, this.y - this.height - 18);
        ctx.scale(cScale, cScale);
        ctx.shadowColor = '#ff8800'; ctx.shadowBlur = 10;
        ctx.font = 'bold 28px "Orbitron", sans-serif';
        ctx.fillStyle = '#ffd700'; ctx.fillText(this.comboCount + ' HIT', 0, 0);
        ctx.shadowBlur = 0;
        ctx.font = 'bold 15px "Rajdhani", sans-serif';
        ctx.fillStyle = '#ffaa00'; ctx.fillText('COMBO!', 0, 16);
        ctx.restore();
    }
};

})();
