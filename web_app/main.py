"""
================================================================================
CRYPTOALPHA PRO - Web Application
================================================================================
FastAPI-based web interface for the EXTREME signal system.

Run: uvicorn web_app.main:app --host 0.0.0.0 --port 8000
================================================================================
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn


# Data Models
class PortfolioMetrics(BaseModel):
    timestamp: str
    initial_capital: float
    current_capital: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    total_return_pct: float
    open_positions: int
    closed_trades: int
    win_rate: float


class TradeResponse(BaseModel):
    trade_id: str
    asset: str
    entry_time: str
    entry_price: float
    exit_time: Optional[str]
    exit_price: Optional[float]
    exit_reason: Optional[str]
    realized_pnl_pct: float
    realized_pnl_usd: float
    status: str


# Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


manager = ConnectionManager()


# Background Task
async def price_monitor_task():
    while True:
        try:
            report_files = sorted(Path('.').glob('war_room_v2_report_*.json'))
            if report_files:
                with open(report_files[-1]) as f:
                    data = json.load(f)
                
                await manager.broadcast({
                    'type': 'portfolio_update',
                    'data': data.get('metrics', {}),
                    'timestamp': datetime.now().isoformat()
                })
            
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Monitor error: {e}")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(price_monitor_task())
    yield


app = FastAPI(
    title="CryptoAlpha Pro API",
    description="EXTREME Signal System",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/")
async def root():
    return {"message": "CryptoAlpha Pro API", "docs": "/docs", "dashboard": "/dashboard"}


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    html_content = open(Path(__file__).parent / 'static' / 'dashboard.html').read() if (Path(__file__).parent / 'static' / 'dashboard.html').exists() else generate_dashboard_html()
    return HTMLResponse(content=html_content)


def generate_dashboard_html():
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CryptoAlpha Pro - Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Inter', sans-serif; background: #0f172a; color: #f8fafc; }
        .metric-card { background: #1e293b; border: 1px solid #334155; border-radius: 0.75rem; padding: 1rem; }
        .pulse-dot { animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    </style>
</head>
<body class="min-h-screen">
    <header class="bg-slate-900 border-b border-slate-800 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 py-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-red-600 flex items-center justify-center font-bold text-white">α</div>
                    <div>
                        <h1 class="font-bold text-xl">CryptoAlpha Pro</h1>
                        <p class="text-xs text-slate-400">EXTREME Signal System</p>
                    </div>
                </div>
                <div class="flex items-center gap-4">
                    <div class="flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-sm">
                        <span class="w-2 h-2 rounded-full bg-green-500 pulse-dot"></span>
                        Live
                    </div>
                </div>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-6">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div class="metric-card">
                <div class="text-sm text-slate-500 mb-1">Total P&L</div>
                <div id="total-pnl" class="text-2xl font-bold text-slate-400">--</div>
            </div>
            <div class="metric-card">
                <div class="text-sm text-slate-500 mb-1">Realized P&L</div>
                <div id="realized-pnl" class="text-2xl font-bold text-slate-400">--</div>
            </div>
            <div class="metric-card">
                <div class="text-sm text-slate-500 mb-1">Win Rate</div>
                <div id="win-rate" class="text-2xl font-bold text-slate-400">--</div>
            </div>
            <div class="metric-card">
                <div class="text-sm text-slate-500 mb-1">Open Positions</div>
                <div id="open-positions" class="text-2xl font-bold text-slate-400">--</div>
            </div>
        </div>
        
        <div id="trade-history" class="bg-slate-900 rounded-xl border border-slate-800 p-4">
            <h3 class="font-semibold mb-4">Trade History</h3>
            <div class="text-center text-slate-500 py-8">Loading...</div>
        </div>
    </main>

    <script>
        const ws = new WebSocket(`ws://${window.location.host}/ws`);
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'portfolio_update') {
                updateDashboard(data.data);
            }
        };
        
        async function loadData() {
            try {
                const response = await fetch('/api/portfolio');
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                console.error('Error:', error);
            }
        }
        
        function updateDashboard(data) {
            document.getElementById('total-pnl').textContent = formatCurrency(data.total_pnl);
            document.getElementById('total-pnl').className = `text-2xl font-bold ${data.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`;
            document.getElementById('realized-pnl').textContent = formatCurrency(data.realized_pnl);
            document.getElementById('win-rate').textContent = data.win_rate.toFixed(1) + '%';
            document.getElementById('open-positions').textContent = data.open_positions;
        }
        
        function formatCurrency(value) {
            if (value === undefined) return '--';
            const sign = value >= 0 ? '+' : '';
            return `${sign}$${value.toFixed(2)}`;
        }
        
        loadData();
        setInterval(loadData, 10000);
    </script>
</body>
</html>'''


@app.get("/api/portfolio", response_model=PortfolioMetrics)
async def get_portfolio():
    report_files = sorted(Path('.').glob('war_room_v2_report_*.json'))
    
    if not report_files:
        return PortfolioMetrics(
            timestamp=datetime.now().isoformat(),
            initial_capital=10000.0,
            current_capital=10000.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            total_pnl=0.0,
            total_return_pct=0.0,
            open_positions=0,
            closed_trades=0,
            win_rate=0.0
        )
    
    with open(report_files[-1]) as f:
        data = json.load(f)
    
    metrics = data.get('metrics', {})
    
    return PortfolioMetrics(
        timestamp=data.get('timestamp', datetime.now().isoformat()),
        initial_capital=metrics.get('initial_capital', 10000.0),
        current_capital=metrics.get('current_capital', 10000.0),
        realized_pnl=metrics.get('realized_pnl', 0.0),
        unrealized_pnl=metrics.get('unrealized_pnl', 0.0),
        total_pnl=metrics.get('total_pnl', 0.0),
        total_return_pct=metrics.get('total_return_pct', 0.0),
        open_positions=metrics.get('open_positions', 0),
        closed_trades=metrics.get('closed_trades', 0),
        win_rate=metrics.get('win_rate', 0.0)
    )


@app.get("/api/trades", response_model=List[TradeResponse])
async def get_trades():
    report_files = sorted(Path('.').glob('war_room_v2_report_*.json'))
    
    if not report_files:
        return []
    
    with open(report_files[-1]) as f:
        data = json.load(f)
    
    trades = []
    
    for trade_data in data.get('open_trades', []):
        trades.append(TradeResponse(
            trade_id=trade_data.get('trade_id', ''),
            asset=trade_data.get('asset', ''),
            entry_time=trade_data.get('entry_time', ''),
            entry_price=trade_data.get('entry_price', 0),
            exit_time=None,
            exit_price=None,
            exit_reason=None,
            realized_pnl_pct=0.0,
            realized_pnl_usd=0.0,
            status='OPEN'
        ))
    
    for trade_data in data.get('closed_trades', []):
        trades.append(TradeResponse(
            trade_id=trade_data.get('trade_id', ''),
            asset=trade_data.get('asset', ''),
            entry_time=trade_data.get('entry_time', ''),
            entry_price=trade_data.get('entry_price', 0),
            exit_time=trade_data.get('exit_time'),
            exit_price=trade_data.get('exit_price'),
            exit_reason=trade_data.get('exit_reason'),
            realized_pnl_pct=trade_data.get('realized_pnl_pct', 0) * 100,
            realized_pnl_usd=trade_data.get('realized_pnl_usd', 0),
            status='CLOSED'
        ))
    
    return trades


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat(), "version": "2.0.0"}


if __name__ == "__main__":
    uvicorn.run("web_app.main:app", host="0.0.0.0", port=8000, reload=True)
