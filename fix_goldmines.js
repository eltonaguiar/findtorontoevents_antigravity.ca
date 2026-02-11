const fs = require('fs');

const filePath = 'e:/findtorontoevents_antigravity.ca/index.html';
let content = fs.readFileSync(filePath, 'utf8');

// Find the goldmines section and replace it
const oldSection = `    + '<div class="os-category-panel" data-catpanel="goldmines">'
    // ── Cursor group ──
    + '<div style="padding:2px 12px;font-size:11px;color:#00d4ff;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;">\\u{1F916} Cursor</div>'
    + '<a href="/goldmine_cursor/" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#f59e0b;"></span><span class="os-sub-text">GOLDMINE_CURSOR Dashboard</span><span class="os-sub-arrow">\\u203A</span></a>'
    + '<a href="/goldmine_cursor/#proof" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#22c55e;"></span><span class="os-sub-text">Track Record (Proof)</span><span class="os-sub-arrow">\\u203A</span></a>'
    + '<a href="/goldmine_cursor/#scorecard" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#a855f7;"></span><span class="os-sub-text">Weekly Scorecard</span><span class="os-sub-arrow">\\u203A</span></a>'
    + '<a href="/goldmine_cursor/#mission" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#ef4444;"></span><span class="os-sub-text">Mission Control</span><span class="os-sub-arrow">\\u203A</span></a>'
    + '<div style="height:1px;background:rgba(255,255,255,0.06);margin:8px 0 4px;"></div>'
    // ── Windsurf group ──
    + '<div style="padding:2px 12px;font-size:11px;color:#f59e0b;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;">\\u{1F3C4} Windsurf</div>'
    + '<a href="/investments/goldmines/windsurf/" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#f59e0b;"></span><span class="os-sub-text">GOLDMINE_WS Dashboard</span><span class="os-sub-arrow">\\u203A</span></a>'
    + '<a href="/investments/goldmines/windsurf/#tab-leaderboard" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#22c55e;"></span><span class="os-sub-text">System Leaderboard</span><span class="os-sub-arrow">\\u203A</span></a>'
    + '<a href="/investments/goldmines/windsurf/#tab-proof" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#a855f7;"></span><span class="os-sub-text">Proof Log</span><span class="os-sub-arrow">\\u203A</span></a>'
    + '<a href="/investments/goldmines/windsurf/#tab-health" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#06b6d4;"></span><span class="os-sub-text">System Health</span><span class="os-sub-arrow">\\u203A</span></a>'
    + '<div style="height:1px;background:rgba(255,255,255,0.06);margin:8px 0 4px;"></div>'
    // ── Claude group ──
    + '<div style="padding:2px 12px;font-size:11px;color:#6366f1;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;">\\u{1F916} Claude</div>'
    + '<a href="/live-monitor/goldmine-dashboard.html" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#6366f1;"></span><span class="os-sub-text">Goldmine Checker</span><span class="os-sub-arrow">\\u203A</span></a>'
    + '<a href="/live-monitor/goldmine-alerts.html" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#f43f5e;"></span><span class="os-sub-text">Health Alerts</span><span class="os-sub-arrow">\\u203A</span></a>'
    + '</div>'`;

const newSection = `    + '<div class="os-category-panel" data-catpanel="goldmines">'
    // ── Antigravity group ──
    + '<div style="padding:2px 12px;font-size:11px;color:#22c55e;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;">\\u{1F680} Antigravity</div>'
    + '<a href="/investments/goldmines/antigravity/" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#22c55e;"></span><span class="os-sub-text">Antigravity Goldmine</span><span class="os-sub-arrow">\\u203A</span></a>'
    + '<div style="height:1px;background:rgba(255,255,255,0.06);margin:8px 0 4px;"></div>'
    // ── Cursor group ──
    + '<div style="padding:2px 12px;font-size:11px;color:#00d4ff;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;">\\u{1F916} Cursor</div>'
    + '<a href="/goldmine_cursor/" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#f59e0b;"></span><span class="os-sub-text">Cursor Goldmine</span><span class="os-sub-arrow">\\u203A</span></a>'
    + '<div style="height:1px;background:rgba(255,255,255,0.06);margin:8px 0 4px;"></div>'
    // ── Windsurf group ──
    + '<div style="padding:2px 12px;font-size:11px;color:#f59e0b;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;">\\u{1F3C4} Windsurf</div>'
    + '<a href="/investments/goldmines/windsurf/" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#f59e0b;"></span><span class="os-sub-text">Windsurf Goldmine</span><span class="os-sub-arrow">\\u203A</span></a>'
    + '<div style="height:1px;background:rgba(255,255,255,0.06);margin:8px 0 4px;"></div>'
    // ── Claude group ──
    + '<div style="padding:2px 12px;font-size:11px;color:#6366f1;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;">\\u{1F916} Claude</div>'
    + '<a href="/live-monitor/goldmine-dashboard.html" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#6366f1;"></span><span class="os-sub-text">Claude Goldmine</span><span class="os-sub-arrow">\\u203A</span></a>'
    + '</div>'`;

content = content.replace(oldSection, newSection);

fs.writeFileSync(filePath, content, 'utf8');
console.log('✅ Successfully updated goldmines section!');
