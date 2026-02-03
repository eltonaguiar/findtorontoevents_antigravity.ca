/**
 * UPDATE #83: Analytics Dashboard
 * Detailed analytics and insights
 */

import React from 'react';

interface AnalyticsData {
    pageViews: { date: string; count: number }[];
    topMovies: { id: number; title: string; views: number }[];
    userGrowth: { date: string; count: number }[];
    deviceBreakdown: { device: string; percentage: number }[];
    topGenres: { genre: string; views: number }[];
}

interface AnalyticsDashboardProps {
    data: AnalyticsData;
    dateRange?: string;
}

export function AnalyticsDashboard({ data, dateRange = 'Last 30 days' }: AnalyticsDashboardProps) {
    const totalViews = data.pageViews.reduce((sum, item) => sum + item.count, 0);
    const avgViewsPerDay = Math.round(totalViews / data.pageViews.length);

    return (
        <div className="analytics-dashboard">
            <div className="analytics-header">
                <h2>Analytics Dashboard</h2>
                <span className="date-range">{dateRange}</span>
            </div>

            <div className="analytics-summary">
                <div className="summary-card">
                    <div className="summary-value">{totalViews.toLocaleString()}</div>
                    <div className="summary-label">Total Views</div>
                </div>
                <div className="summary-card">
                    <div className="summary-value">{avgViewsPerDay.toLocaleString()}</div>
                    <div className="summary-label">Avg Views/Day</div>
                </div>
                <div className="summary-card">
                    <div className="summary-value">{data.topMovies.length}</div>
                    <div className="summary-label">Trending Movies</div>
                </div>
            </div>

            <div className="analytics-grid">
                <div className="analytics-section">
                    <h3>Top Movies</h3>
                    <div className="top-list">
                        {data.topMovies.slice(0, 5).map((movie, index) => (
                            <div key={movie.id} className="top-item">
                                <span className="rank">#{index + 1}</span>
                                <span className="title">{movie.title}</span>
                                <span className="views">{movie.views.toLocaleString()} views</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="analytics-section">
                    <h3>Device Breakdown</h3>
                    <div className="device-chart">
                        {data.deviceBreakdown.map(device => (
                            <div key={device.device} className="device-item">
                                <div className="device-label">
                                    <span>{device.device}</span>
                                    <span>{device.percentage}%</span>
                                </div>
                                <div className="device-bar">
                                    <div
                                        className="device-fill"
                                        style={{ width: `${device.percentage}%` }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="analytics-section">
                    <h3>Top Genres</h3>
                    <div className="genre-list">
                        {data.topGenres.map(genre => (
                            <div key={genre.genre} className="genre-item">
                                <span className="genre-name">{genre.genre}</span>
                                <span className="genre-views">{genre.views.toLocaleString()}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="analytics-section full-width">
                    <h3>Page Views Trend</h3>
                    <div className="trend-chart">
                        {data.pageViews.map((item, index) => {
                            const maxViews = Math.max(...data.pageViews.map(v => v.count));
                            const height = (item.count / maxViews) * 100;

                            return (
                                <div key={index} className="trend-bar-wrapper">
                                    <div
                                        className="trend-bar"
                                        style={{ height: `${height}%` }}
                                        title={`${item.date}: ${item.count} views`}
                                    />
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}

const styles = `
.analytics-dashboard {
  padding: 2rem;
}

.analytics-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.analytics-header h2 {
  margin: 0;
}

.date-range {
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  font-size: 0.9rem;
}

.analytics-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.summary-card {
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  text-align: center;
}

.summary-value {
  font-size: 2.5rem;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.summary-label {
  margin-top: 0.5rem;
  opacity: 0.7;
}

.analytics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}

.analytics-section {
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
}

.analytics-section.full-width {
  grid-column: 1 / -1;
}

.analytics-section h3 {
  margin: 0 0 1.5rem;
  font-size: 1.2rem;
}

.top-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.top-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
}

.rank {
  font-weight: 700;
  color: #667eea;
  min-width: 30px;
}

.title {
  flex: 1;
}

.views {
  opacity: 0.7;
  font-size: 0.9rem;
}

.device-chart {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.device-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.device-label {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
}

.device-bar {
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.device-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s;
}

.genre-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.genre-item {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
}

.genre-name {
  font-weight: 500;
}

.genre-views {
  opacity: 0.7;
}

.trend-chart {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 200px;
  padding: 1rem 0;
}

.trend-bar-wrapper {
  flex: 1;
  height: 100%;
  display: flex;
  align-items: flex-end;
}

.trend-bar {
  width: 100%;
  background: linear-gradient(to top, #667eea 0%, #764ba2 100%);
  border-radius: 4px 4px 0 0;
  transition: all 0.3s;
  cursor: pointer;
}

.trend-bar:hover {
  opacity: 0.8;
}

@media (max-width: 768px) {
  .analytics-grid {
    grid-template-columns: 1fr;
  }
}
`;
