/**
 * UPDATE #81: Admin Dashboard Component
 * Manage content and users
 */

import React, { useState } from 'react';

interface DashboardStats {
    totalMovies: number;
    totalUsers: number;
    totalComments: number;
    totalViews: number;
    newUsersToday: number;
    viewsToday: number;
}

interface AdminDashboardProps {
    stats: DashboardStats;
    onRefresh?: () => void;
}

export function AdminDashboard({ stats, onRefresh }: AdminDashboardProps) {
    const [activeTab, setActiveTab] = useState<'overview' | 'content' | 'users' | 'analytics'>('overview');

    return (
        <div className="admin-dashboard">
            <div className="dashboard-header">
                <h1>Admin Dashboard</h1>
                <button onClick={onRefresh} className="refresh-btn">🔄 Refresh</button>
            </div>

            <div className="dashboard-tabs">
                <button
                    onClick={() => setActiveTab('overview')}
                    className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
                >
                    Overview
                </button>
                <button
                    onClick={() => setActiveTab('content')}
                    className={`tab ${activeTab === 'content' ? 'active' : ''}`}
                >
                    Content
                </button>
                <button
                    onClick={() => setActiveTab('users')}
                    className={`tab ${activeTab === 'users' ? 'active' : ''}`}
                >
                    Users
                </button>
                <button
                    onClick={() => setActiveTab('analytics')}
                    className={`tab ${activeTab === 'analytics' ? 'active' : ''}`}
                >
                    Analytics
                </button>
            </div>

            {activeTab === 'overview' && (
                <div className="dashboard-stats">
                    <div className="stat-card">
                        <div className="stat-icon">🎬</div>
                        <div className="stat-content">
                            <div className="stat-value">{stats.totalMovies.toLocaleString()}</div>
                            <div className="stat-label">Total Movies</div>
                        </div>
                    </div>

                    <div className="stat-card">
                        <div className="stat-icon">👥</div>
                        <div className="stat-content">
                            <div className="stat-value">{stats.totalUsers.toLocaleString()}</div>
                            <div className="stat-label">Total Users</div>
                            <div className="stat-change">+{stats.newUsersToday} today</div>
                        </div>
                    </div>

                    <div className="stat-card">
                        <div className="stat-icon">💬</div>
                        <div className="stat-content">
                            <div className="stat-value">{stats.totalComments.toLocaleString()}</div>
                            <div className="stat-label">Comments</div>
                        </div>
                    </div>

                    <div className="stat-card">
                        <div className="stat-icon">👁️</div>
                        <div className="stat-content">
                            <div className="stat-value">{stats.totalViews.toLocaleString()}</div>
                            <div className="stat-label">Total Views</div>
                            <div className="stat-change">+{stats.viewsToday} today</div>
                        </div>
                    </div>
                </div>
            )}

            {activeTab === 'content' && (
                <div className="dashboard-content">
                    <h2>Content Management</h2>
                    <p>Manage movies, trailers, and metadata</p>
                </div>
            )}

            {activeTab === 'users' && (
                <div className="dashboard-content">
                    <h2>User Management</h2>
                    <p>Manage users, permissions, and moderation</p>
                </div>
            )}

            {activeTab === 'analytics' && (
                <div className="dashboard-content">
                    <h2>Analytics</h2>
                    <p>Detailed analytics and insights</p>
                </div>
            )}
        </div>
    );
}

const styles = `
.admin-dashboard {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.dashboard-header h1 {
  margin: 0;
  font-size: 2rem;
}

.refresh-btn {
  padding: 0.75rem 1.5rem;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-btn:hover {
  background: rgba(255, 255, 255, 0.15);
}

.dashboard-tabs {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  border-bottom: 2px solid rgba(255, 255, 255, 0.1);
}

.tab {
  padding: 1rem 2rem;
  background: none;
  border: none;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border-bottom: 3px solid transparent;
  margin-bottom: -2px;
}

.tab:hover {
  background: rgba(255, 255, 255, 0.05);
}

.tab.active {
  border-bottom-color: #667eea;
}

.dashboard-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.stat-card {
  display: flex;
  gap: 1.5rem;
  padding: 2rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  transition: all 0.2s;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
}

.stat-icon {
  font-size: 3rem;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 2.5rem;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-label {
  margin-top: 0.5rem;
  opacity: 0.7;
  font-size: 0.9rem;
}

.stat-change {
  margin-top: 0.25rem;
  color: #4ade80;
  font-size: 0.85rem;
}

.dashboard-content {
  padding: 2rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
}

.dashboard-content h2 {
  margin: 0 0 1rem;
}
`;
