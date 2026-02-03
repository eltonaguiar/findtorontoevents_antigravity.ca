/**
 * UPDATE #104: Revenue Analytics Dashboard
 * Track revenue and business metrics
 */

import React from 'react';

interface RevenueMetrics {
    totalRevenue: number;
    monthlyRevenue: number;
    yearlyRevenue: number;
    averageRevenuePerUser: number;
    churnRate: number;
    lifetimeValue: number;
    subscriptionsByTier: Record<string, number>;
    revenueByTier: Record<string, number>;
    growthRate: number;
}

interface RevenueAnalyticsDashboardProps {
    metrics: RevenueMetrics;
    dateRange?: string;
}

export function RevenueAnalyticsDashboard({
    metrics,
    dateRange = 'Last 30 days'
}: RevenueAnalyticsDashboardProps) {
    return (
        <div className="revenue-dashboard">
            <div className="dashboard-header">
                <h2>Revenue Analytics</h2>
                <span className="date-range">{dateRange}</span>
            </div>

            <div className="metrics-grid">
                <div className="metric-card highlight">
                    <div className="metric-icon">💰</div>
                    <div className="metric-content">
                        <div className="metric-value">${metrics.totalRevenue.toLocaleString()}</div>
                        <div className="metric-label">Total Revenue</div>
                        <div className="metric-change positive">
                            +{metrics.growthRate}% vs last period
                        </div>
                    </div>
                </div>

                <div className="metric-card">
                    <div className="metric-icon">📊</div>
                    <div className="metric-content">
                        <div className="metric-value">${metrics.monthlyRevenue.toLocaleString()}</div>
                        <div className="metric-label">Monthly Recurring Revenue</div>
                    </div>
                </div>

                <div className="metric-card">
                    <div className="metric-icon">👤</div>
                    <div className="metric-content">
                        <div className="metric-value">${metrics.averageRevenuePerUser.toFixed(2)}</div>
                        <div className="metric-label">ARPU</div>
                    </div>
                </div>

                <div className="metric-card">
                    <div className="metric-icon">💎</div>
                    <div className="metric-content">
                        <div className="metric-value">${metrics.lifetimeValue.toFixed(2)}</div>
                        <div className="metric-label">Customer LTV</div>
                    </div>
                </div>

                <div className="metric-card">
                    <div className="metric-icon">📉</div>
                    <div className="metric-content">
                        <div className="metric-value">{metrics.churnRate.toFixed(1)}%</div>
                        <div className="metric-label">Churn Rate</div>
                        <div className={`metric-change ${metrics.churnRate < 5 ? 'positive' : 'negative'}`}>
                            {metrics.churnRate < 5 ? 'Healthy' : 'Needs attention'}
                        </div>
                    </div>
                </div>

                <div className="metric-card">
                    <div className="metric-icon">📅</div>
                    <div className="metric-content">
                        <div className="metric-value">${metrics.yearlyRevenue.toLocaleString()}</div>
                        <div className="metric-label">Annual Revenue</div>
                    </div>
                </div>
            </div>

            <div className="charts-section">
                <div className="chart-card">
                    <h3>Revenue by Tier</h3>
                    <div className="tier-breakdown">
                        {Object.entries(metrics.revenueByTier).map(([tier, revenue]) => (
                            <div key={tier} className="tier-item">
                                <div className="tier-label">
                                    <span className="tier-name">{tier}</span>
                                    <span className="tier-revenue">${revenue.toLocaleString()}</span>
                                </div>
                                <div className="tier-bar">
                                    <div
                                        className="tier-fill"
                                        style={{
                                            width: `${(revenue / metrics.totalRevenue) * 100}%`
                                        }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="chart-card">
                    <h3>Subscriptions by Tier</h3>
                    <div className="subscription-breakdown">
                        {Object.entries(metrics.subscriptionsByTier).map(([tier, count]) => (
                            <div key={tier} className="subscription-item">
                                <span className="sub-tier">{tier}</span>
                                <span className="sub-count">{count.toLocaleString()}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

const styles = `
.revenue-dashboard {
  padding: 2rem;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.dashboard-header h2 {
  margin: 0;
  font-size: 2rem;
}

.date-range {
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  font-size: 0.9rem;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.metric-card {
  display: flex;
  gap: 1.5rem;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.2s;
}

.metric-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
}

.metric-card.highlight {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
  border-color: #667eea;
}

.metric-icon {
  font-size: 2.5rem;
}

.metric-content {
  flex: 1;
}

.metric-value {
  font-size: 2rem;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.metric-label {
  margin-top: 0.5rem;
  opacity: 0.7;
  font-size: 0.9rem;
}

.metric-change {
  margin-top: 0.25rem;
  font-size: 0.85rem;
  font-weight: 600;
}

.metric-change.positive {
  color: #4ade80;
}

.metric-change.negative {
  color: #f87171;
}

.charts-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 2rem;
}

.chart-card {
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
}

.chart-card h3 {
  margin: 0 0 1.5rem;
  font-size: 1.25rem;
}

.tier-breakdown {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.tier-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.tier-label {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
}

.tier-name {
  font-weight: 600;
  text-transform: capitalize;
}

.tier-revenue {
  color: #4ade80;
  font-weight: 700;
}

.tier-bar {
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.tier-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s;
}

.subscription-breakdown {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.subscription-item {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
}

.sub-tier {
  font-weight: 500;
  text-transform: capitalize;
}

.sub-count {
  font-weight: 700;
  color: #667eea;
}

@media (max-width: 768px) {
  .charts-section {
    grid-template-columns: 1fr;
  }
}
`;
