"""
KIMI_FEB172026 - Live Monitor Dashboard
Real-time web dashboard showing system status, performance, and active signals
Auto-refreshes every 30 seconds
"""

import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

try:
    from fastapi import FastAPI, WebSocket
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# HTML Template for the dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KIMI_FEB172026 - Live Monitor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0f;
            color: #fff;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 20px;
            border-bottom: 2px solid #00ff88;
        }
        .header h1 {
            font-size: 1.8rem;
            background: linear-gradient(90deg, #00ff88, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header p { color: #888; margin-top: 5px; }
        .status-bar {
            display: flex;
            gap: 20px;
            padding: 15px 20px;
            background: #12121a;
            border-bottom: 1px solid #2a2a3a;
        }
        .status-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        .status-online { background: #00ff88; }
        .status-warning { background: #ffd700; }
        .status-offline { background: #ff4757; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: #12121a;
            border: 1px solid #2a2a3a;
            border-radius: 12px;
            padding: 20px;
        }
        .card h3 {
            color: #888;
            font-size: 0.9rem;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .metric {
            font-size: 2rem;
            font-weight: bold;
        }
        .metric.positive { color: #00ff88; }
        .metric.negative { color: #ff4757; }
        .metric.neutral { color: #00d4ff; }
        .change {
            font-size: 0.85rem;
            color: #888;
            margin-top: 5px;
        }
        .signals-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }
        .signals-table th {
            text-align: left;
            padding: 12px;
            color: #888;
            border-bottom: 1px solid #2a2a3a;
            font-weight: 600;
        }
        .signals-table td {
            padding: 12px;
            border-bottom: 1px solid #2a2a3a;
        }
        .signals-table tr:hover {
            background: #1a1a25;
        }
        .badge {
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .badge-long { background: rgba(0,255,136,0.2); color: #00ff88; }
        .badge-short { background: rgba(255,71,87,0.2); color: #ff4757; }
        .badge-high { background: rgba(0,212,255,0.2); color: #00d4ff; }
        .progress-bar {
            width: 100px;
            height: 6px;
            background: #2a2a3a;
            border-radius: 3px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            border-radius: 3px;
            transition: width 0.3s;
        }
        .last-updated {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.85rem;
        }
        .alert {
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .alert-success { background: rgba(0,255,136,0.1); border: 1px solid #00ff88; }
        .alert-warning { background: rgba(255,215,0,0.1); border: 1px solid #ffd700; }
        .alert-error { background: rgba(255,71,87,0.1); border: 1px solid #ff4757; }
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
            .status-bar { flex-wrap: wrap; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ KIMI_FEB172026 Live Monitor</h1>
        <p>Autonomous Trading System - Real-time Performance Dashboard</p>
    </div>
    
    <div class="status-bar">
        <div class="status-item">
            <div class="status-dot" id="systemStatusDot"></div>
            <span id="systemStatus">Connecting...</span>
        </div>
        <div class="status-item">
            <span>📊 Scans: <strong id="scanCount">0</strong></span>
        </div>
        <div class="status-item">
            <span>🎯 Positions: <strong id="positionCount">0</strong></span>
        </div>
        <div class="status-item">
            <span>⏱️ Last Update: <strong id="lastUpdate">-</strong></span>
        </div>
    </div>
    
    <div class="container">
        <div id="alerts"></div>
        
        <div class="grid">
            <div class="card">
                <h3>Win Rate (7d)</h3>
                <div class="metric neutral" id="winRate">--</div>
                <div class="change" id="winRateChange">Target: 65%</div>
            </div>
            <div class="card">
                <h3>Total P&L (7d)</h3>
                <div class="metric neutral" id="totalPnl">--</div>
                <div class="change" id="totalPnlChange">vs last week</div>
            </div>
            <div class="card">
                <h3>Sharpe Ratio</h3>
                <div class="metric neutral" id="sharpe">--</div>
                <div class="change">Risk-adjusted return</div>
            </div>
            <div class="card">
                <h3>Active Signals</h3>
                <div class="metric neutral" id="activeSignals">--</div>
                <div class="change">High confidence (65%+)</div>
            </div>
        </div>
        
        <div class="card">
            <h3>🎯 Latest Signals</h3>
            <table class="signals-table">
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Symbol</th>
                        <th>Algorithm</th>
                        <th>Direction</th>
                        <th>Confidence</th>
                        <th>Entry</th>
                        <th>TP / SL</th>
                        <th>Win Prob</th>
                    </tr>
                </thead>
                <tbody id="signalsBody">
                    <tr><td colspan="8" style="text-align:center;color:#666;">Loading...</td></tr>
                </tbody>
            </table>
        </div>
        
        <div class="last-updated">
            Auto-refreshes every 30 seconds • Dashboard v1.0
        </div>
    </div>
    
    <script>
        let ws;
        
        function connect() {
            ws = new WebSocket('ws://localhost:8000/ws');
            
            ws.onopen = () => {
                console.log('Connected to KIMI monitor');
                updateSystemStatus('online');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onclose = () => {
                console.log('Disconnected, retrying...');
                updateSystemStatus('offline');
                setTimeout(connect, 3000);
            };
            
            ws.onerror = (err) => {
                console.error('WebSocket error:', err);
                updateSystemStatus('warning');
            };
        }
        
        function updateSystemStatus(status) {
            const dot = document.getElementById('systemStatusDot');
            const text = document.getElementById('systemStatus');
            
            dot.className = 'status-dot status-' + status;
            text.textContent = status === 'online' ? 'Live' : 
                              status === 'warning' ? 'Reconnecting...' : 'Offline';
        }
        
        function updateDashboard(data) {
            // Update metrics
            if (data.metrics) {
                const m = data.metrics;
                updateMetric('winRate', (m.win_rate * 100).toFixed(1) + '%', m.win_rate >= 0.65 ? 'positive' : 'neutral');
                updateMetric('totalPnl', (m.total_pnl_pct >= 0 ? '+' : '') + m.total_pnl_pct.toFixed(2) + '%', 
                           m.total_pnl_pct >= 0 ? 'positive' : 'negative');
                updateMetric('sharpe', m.sharpe_ratio.toFixed(2), 
                           m.sharpe_ratio >= 1.5 ? 'positive' : m.sharpe_ratio >= 1.0 ? 'neutral' : 'negative');
            }
            
            // Update status bar
            if (data.status) {
                document.getElementById('scanCount').textContent = data.status.scan_count || 0;
                document.getElementById('positionCount').textContent = data.status.open_positions || 0;
                document.getElementById('lastUpdate').textContent = 
                    data.status.last_scan ? new Date(data.status.last_scan).toLocaleTimeString() : '-';
            }
            
            // Update signals table
            if (data.signals) {
                updateSignalsTable(data.signals);
                document.getElementById('activeSignals').textContent = data.signals.length;
                document.getElementById('activeSignals').className = 
                    'metric ' + (data.signals.length > 0 ? 'positive' : 'neutral');
            }
            
            // Update alerts
            if (data.validation && data.validation.recommendations) {
                updateAlerts(data.validation.recommendations);
            }
        }
        
        function updateMetric(id, value, className) {
            const el = document.getElementById(id);
            el.textContent = value;
            el.className = 'metric ' + className;
        }
        
        function updateSignalsTable(signals) {
            const tbody = document.getElementById('signalsBody');
            
            if (signals.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#666;">No active signals</td></tr>';
                return;
            }
            
            tbody.innerHTML = signals.slice(0, 10).map(s => `
                <tr>
                    <td>${new Date(s.timestamp).toLocaleTimeString()}</td>
                    <td><strong>${s.symbol}</strong></td>
                    <td>${s.algorithm}</td>
                    <td><span class="badge badge-${s.direction.toLowerCase()}">${s.direction}</span></td>
                    <td>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width:${s.confidence*100}%;background:${getColor(s.confidence)}"></div>
                        </div>
                        ${(s.confidence*100).toFixed(0)}%
                    </td>
                    <td>$${s.entry.toLocaleString()}</td>
                    <td>$${s.take_profit.toLocaleString()} / $${s.stop_loss.toLocaleString()}</td>
                    <td><span class="badge badge-high">${(s.win_probability*100).toFixed(0)}%</span></td>
                </tr>
            `).join('');
        }
        
        function updateAlerts(recommendations) {
            const alertsDiv = document.getElementById('alerts');
            
            if (recommendations.length === 0) {
                alertsDiv.innerHTML = '<div class="alert alert-success">✓ System operating within normal parameters</div>';
                return;
            }
            
            const critical = recommendations.filter(r => r.priority === 'HIGH');
            const warnings = recommendations.filter(r => r.priority === 'MEDIUM');
            
            let html = '';
            if (critical.length > 0) {
                html += `<div class="alert alert-error">⚠️ ${critical[0].message}</div>`;
            } else if (warnings.length > 0) {
                html += `<div class="alert alert-warning">⚡ ${warnings[0].message}</div>`;
            }
            
            alertsDiv.innerHTML = html;
        }
        
        function getColor(value) {
            if (value >= 0.8) return '#00ff88';
            if (value >= 0.65) return '#00d4ff';
            return '#ffd700';
        }
        
        // Fallback polling if WebSocket not available
        async function pollData() {
            try {
                const response = await fetch('/api/dashboard-data');
                const data = await response.json();
                updateDashboard(data);
                updateSystemStatus('online');
            } catch (err) {
                console.error('Poll error:', err);
                updateSystemStatus('offline');
            }
        }
        
        // Try WebSocket first, fall back to polling
        if (typeof WebSocket !== 'undefined') {
            connect();
        } else {
            pollData();
            setInterval(pollData, 30000);
        }
    </script>
</body>
</html>
"""

def create_app():
    """Create FastAPI application for monitoring"""
    if not FASTAPI_AVAILABLE:
        print("FastAPI not installed. Run: pip install fastapi uvicorn")
        return None
    
    app = FastAPI(title="KIMI Monitor", version="1.0.0")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    data_dir = Path(__file__).parent / "data"
    
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return DASHBOARD_HTML
    
    @app.get("/api/dashboard-data")
    async def get_dashboard_data():
        """Get all dashboard data"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "status": {},
            "metrics": {},
            "signals": [],
            "validation": {}
        }
        
        # Load system status
        status_path = data_dir / "system_status.json"
        if status_path.exists():
            with open(status_path, 'r') as f:
                data["status"] = json.load(f)
        
        # Load performance
        perf_path = data_dir / "performance_history.json"
        if perf_path.exists():
            with open(perf_path, 'r') as f:
                history = json.load(f)
                if history:
                    data["metrics"] = history[-1]
        
        # Load recent signals
        signals_path = data_dir / "latest_signals.json"
        if signals_path.exists():
            with open(signals_path, 'r') as f:
                signals_data = json.load(f)
                data["signals"] = signals_data.get("signals", [])[:10]
        
        # Load validation
        validation_path = data_dir / "validation_history.json"
        if validation_path.exists():
            with open(validation_path, 'r') as f:
                validations = json.load(f)
                if validations:
                    data["validation"] = validations[-1]
        
        return data
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket for real-time updates"""
        await websocket.accept()
        
        try:
            while True:
                # Send dashboard data
                data = await get_dashboard_data()
                await websocket.send_json(data)
                
                # Wait 5 seconds before next update
                await asyncio.sleep(5)
                
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            await websocket.close()
    
    @app.get("/api/health")
    async def health_check():
        """Health check endpoint"""
        status_path = data_dir / "system_status.json"
        
        if not status_path.exists():
            return {"status": "unknown"}
        
        with open(status_path, 'r') as f:
            status = json.load(f)
        
        # Check if scan is recent (within 10 minutes)
        last_scan = status.get("last_scan")
        if last_scan:
            last_time = datetime.fromisoformat(last_scan)
            minutes_ago = (datetime.now() - last_time).total_seconds() / 60
            
            if minutes_ago > 10:
                return {"status": "stalled", "minutes_since_scan": minutes_ago}
        
        return {"status": "healthy", "data": status}
    
    return app


if __name__ == "__main__":
    if not FASTAPI_AVAILABLE:
        print("Please install FastAPI: pip install fastapi uvicorn")
        sys.exit(1)
    
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
