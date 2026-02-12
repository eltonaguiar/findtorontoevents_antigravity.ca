# gnn_regime.py - Graph Neural Network for regime detection
# Requirements: pip install torch torch-geometric yfinance pandas numpy mysql-connector-python

import os
import torch
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
from torch_geometric.data import Data
import yfinance as yf
import pandas as pd
import numpy as np
import mysql.connector

# DB config
DB_HOST = os.getenv('DB_HOST', 'mysql.50webs.com')
DB_USER = os.getenv('DB_USER', 'ejaguiar1_stocks')
DB_PASS = os.getenv('DB_PASS', 'stocks')
DB_NAME = os.getenv('DB_NAME', 'ejaguiar1_stocks')

class RegimeGNN(torch.nn.Module):
    def __init__(self, num_features, hidden_channels):
        super().__init__()
        self.conv1 = GCNConv(num_features, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, 3)  # 3 regimes

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = self.conv2(x, edge_index)
        return F.log_softmax(x, dim=1)

def fetch_market_graph():
    # Nodes: assets, edges: correlations
    tickers = ['SPY', 'QQQ', 'IWM', '^VIX', 'GLD', 'TLT', 'USO']
    data = yf.download(tickers, period='1y')['Adj Close']
    returns = data.pct_change().dropna()
    
    corr = returns.corr().values
    edge_index = []
    for i in range(len(tickers)):
        for j in range(i+1, len(tickers)):
            if abs(corr[i,j]) > 0.5:
                edge_index.append([i,j])
                edge_index.append([j,i])
    
    edge_index = torch.tensor(edge_index).t()
    features = torch.tensor(returns[-1].values.reshape(-1,1), dtype=torch.float)  # Last returns as features
    
    return Data(x=features, edge_index=edge_index)

def train_gnn():
    data = fetch_market_graph()
    model = RegimeGNN(num_features=1, hidden_channels=16)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    # Dummy training (use real labels in prod)
    model.train()
    for epoch in range(200):
        out = model(data.x, data.edge_index)
        loss = F.nll_loss(out, torch.randint(0,3,(data.num_nodes,)))  # Random labels for demo
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    
    torch.save(model.state_dict(), 'models/gnn_regime.pth')
    return model

def predict_regime():
    model = RegimeGNN(1,16)
    model.load_state_dict(torch.load('models/gnn_regime.pth'))
    data = fetch_market_graph()
    model.eval()
    out = model(data.x, data.edge_index)
    regimes = out.argmax(dim=1).numpy()
    return regimes[0]  # SPY regime

if __name__ == '__main__':
    train_gnn()
    regime = predict_regime()
    print(f"Detected regime: {regime}")