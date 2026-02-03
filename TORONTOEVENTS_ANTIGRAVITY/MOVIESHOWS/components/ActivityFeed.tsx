/**
 * UPDATE #76: Activity Feed
 * Show user activity and social interactions
 */

import React from 'react';

type ActivityType =
    | 'watched'
    | 'rated'
    | 'commented'
    | 'added_to_queue'
    | 'created_playlist'
    | 'followed'
    | 'liked';

interface Activity {
    id: string;
    userId: number;
    username: string;
    avatar?: string;
    type: ActivityType;
    movieId?: number;
    movieTitle?: string;
    rating?: number;
    comment?: string;
    playlistName?: string;
    targetUsername?: string;
    timestamp: string;
}

interface ActivityFeedProps {
    activities: Activity[];
    onLoadMore?: () => void;
    hasMore?: boolean;
}

export function ActivityFeed({ activities, onLoadMore, hasMore = false }: ActivityFeedProps) {
    const getActivityIcon = (type: ActivityType): string => {
        const icons = {
            watched: '👁️',
            rated: '⭐',
            commented: '💬',
            added_to_queue: '➕',
            created_playlist: '📋',
            followed: '👥',
            liked: '❤️'
        };
        return icons[type];
    };

    const getActivityText = (activity: Activity): string => {
        switch (activity.type) {
            case 'watched':
                return `watched ${activity.movieTitle}`;
            case 'rated':
                return `rated ${activity.movieTitle} ${activity.rating}/5`;
            case 'commented':
                return `commented on ${activity.movieTitle}`;
            case 'added_to_queue':
                return `added ${activity.movieTitle} to queue`;
            case 'created_playlist':
                return `created playlist "${activity.playlistName}"`;
            case 'followed':
                return `followed ${activity.targetUsername}`;
            case 'liked':
                return `liked ${activity.movieTitle}`;
            default:
                return 'performed an action';
        }
    };

    const formatTimeAgo = (timestamp: string): string => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    };

    return (
        <div className="activity-feed">
            <h3>Recent Activity</h3>

            <div className="activity-list">
                {activities.map(activity => (
                    <div key={activity.id} className="activity-item">
                        <div className="activity-avatar">
                            {activity.avatar ? (
                                <img src={activity.avatar} alt={activity.username} />
                            ) : (
                                <div className="avatar-placeholder">
                                    {activity.username.charAt(0).toUpperCase()}
                                </div>
                            )}
                        </div>

                        <div className="activity-content">
                            <div className="activity-text">
                                <span className="activity-icon">{getActivityIcon(activity.type)}</span>
                                <span className="activity-username">{activity.username}</span>
                                <span className="activity-action">{getActivityText(activity)}</span>
                            </div>

                            {activity.comment && (
                                <p className="activity-comment">"{activity.comment}"</p>
                            )}

                            <span className="activity-time">{formatTimeAgo(activity.timestamp)}</span>
                        </div>
                    </div>
                ))}
            </div>

            {hasMore && (
                <button onClick={onLoadMore} className="load-more-btn">
                    Load More
                </button>
            )}
        </div>
    );
}

const styles = `
.activity-feed {
  padding: 2rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
}

.activity-feed h3 {
  margin: 0 0 1.5rem;
  font-size: 1.5rem;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.activity-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  transition: all 0.2s;
}

.activity-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.activity-avatar img,
.activity-avatar .avatar-placeholder {
  width: 40px;
  height: 40px;
  border-radius: 50%;
}

.avatar-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-weight: 700;
  font-size: 1.2rem;
}

.activity-content {
  flex: 1;
}

.activity-text {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.activity-icon {
  font-size: 1.2rem;
}

.activity-username {
  font-weight: 600;
  color: #667eea;
}

.activity-action {
  opacity: 0.9;
}

.activity-comment {
  margin: 0.5rem 0;
  padding: 0.75rem;
  background: rgba(0, 0, 0, 0.2);
  border-left: 3px solid #667eea;
  border-radius: 4px;
  font-style: italic;
  opacity: 0.8;
}

.activity-time {
  font-size: 0.85rem;
  opacity: 0.6;
}

.load-more-btn {
  width: 100%;
  padding: 1rem;
  margin-top: 1.5rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.load-more-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}
`;
