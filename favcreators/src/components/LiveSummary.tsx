import type { LiveCreator } from '../types';
import './LiveSummary.css';
import React, { useState } from 'react';

interface RecentlyOnlineCreator {
    creator_id: string;
    creator_name: string;
    platform: string;
    username: string;
    last_seen_online: string;
    is_live: boolean;
}

interface LiveSummaryProps {
    liveCreators: LiveCreator[];
    recentlyOnline?: RecentlyOnlineCreator[];
    onToggle: () => void;
    isCollapsed?: boolean;
    isChecking?: boolean;
    checkProgress?: { current: number; total: number; currentCreator: string } | null;
    selectedPlatform?: string;
    onPlatformChange?: (platform: string) => void;
    lastUpdated?: number; // Timestamp of last live status update
    onRefresh?: () => void; // Callback to manually refresh live status
    isRefreshing?: boolean; // Whether a manual refresh is in progress
    onManageLiveChecks?: () => void; // Open the manage live checks modal
    liveCheckCreatorCount?: number; // Number of creators being checked
    totalCreatorCount?: number; // Total number of creators
}

function getPlatformIcon(platform: string): string {
    const icons: Record<string, string> = {
        tiktok: '📱',
        twitch: '🎮',
        kick: '⚡',
        youtube: '▶️',
        instagram: '📷'
    };
    return icons[platform.toLowerCase()] || '🌐';
}

function getPlatformColor(platform: string): string {
    const colors: Record<string, string> = {
        tiktok: '#ff0050',
        twitch: '#9146ff',
        kick: '#53fc18',
        youtube: '#ff0000',
        instagram: '#e4405f'
    };
    return colors[platform.toLowerCase()] || '#6366f1';
}

function formatTimeAgo(timestamp?: number): string {
    if (!timestamp) return '';

    const now = Date.now();
    const diff = now - (timestamp * 1000);
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
}

// Group live creators by creator ID, combining platforms
interface GroupedLiveCreator {
    creator: LiveCreator['creator'];
    platforms: {
        platform: string;
        accountUrl: string;
        status: 'live' | 'story';
        startedAt?: number;
        storyCount?: number;
        postedAt?: number;
    }[];
    latestStartedAt?: number;
}

function groupLiveCreators(liveCreators: LiveCreator[]): GroupedLiveCreator[] {
    const grouped = new Map<string, GroupedLiveCreator>();

    liveCreators.forEach(lc => {
        const existing = grouped.get(lc.creator.id);
        if (existing) {
            // Add this platform to existing creator
            existing.platforms.push({
                platform: lc.platform,
                accountUrl: lc.accountUrl,
                status: lc.status,
                startedAt: lc.startedAt,
                storyCount: lc.storyCount,
                postedAt: lc.postedAt
            });
            // Update latest started time
            if (lc.startedAt && (!existing.latestStartedAt || lc.startedAt > existing.latestStartedAt)) {
                existing.latestStartedAt = lc.startedAt;
            }
        } else {
            // Create new grouped entry
            grouped.set(lc.creator.id, {
                creator: lc.creator,
                platforms: [{
                    platform: lc.platform,
                    accountUrl: lc.accountUrl,
                    status: lc.status,
                    startedAt: lc.startedAt,
                    storyCount: lc.storyCount,
                    postedAt: lc.postedAt
                }],
                latestStartedAt: lc.startedAt
            });
        }
    });

    // Convert map to array and sort by latest activity
    return Array.from(grouped.values()).sort((a, b) =>
        (b.latestStartedAt || 0) - (a.latestStartedAt || 0)
    );
}

// Multi-platform badge component
function MultiPlatformBadge({ platforms }: { platforms: GroupedLiveCreator['platforms'] }) {
    const livePlatforms = platforms.filter(p => p.status === 'live');

    if (livePlatforms.length === 0) {
        // Show story badge
        const story = platforms.find(p => p.status === 'story');
        if (story) {
            return (
                <div className="platform-badge" style={{ backgroundColor: getPlatformColor(story.platform) }}>
                    {getPlatformIcon(story.platform)} STORY
                </div>
            );
        }
        return null;
    }

    if (livePlatforms.length === 1) {
        // Single platform - show simple badge
        const p = livePlatforms[0];
        return (
            <div className="platform-badge" style={{ backgroundColor: getPlatformColor(p.platform) }}>
                {getPlatformIcon(p.platform)} {p.platform.toUpperCase()}
            </div>
        );
    }

    // Multiple platforms - show combined badge
    return (
        <div className="multi-platform-badge">
            {livePlatforms.map((p, idx) => (
                <span key={p.platform}>
                    <span
                        className="platform-indicator"
                        style={{
                            backgroundColor: getPlatformColor(p.platform),
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontSize: '10px',
                            fontWeight: 'bold'
                        }}
                    >
                        {getPlatformIcon(p.platform)} {p.platform.toUpperCase()}
                    </span>
                    {idx < livePlatforms.length - 1 && <span className="platform-separator"> & </span>}
                </span>
            ))}
        </div>
    );
}

const PLATFORM_OPTIONS = [
    { value: 'all', label: 'All Platforms' },
    { value: 'tiktok', label: '📱 TikTok' },
    { value: 'twitch', label: '🎮 Twitch' },
    { value: 'kick', label: '⚡ Kick' },
    { value: 'youtube', label: '▶️ YouTube' },
    { value: 'instagram', label: '📷 Instagram' }
];

// Recently Online Section Component with expand/collapse
function RecentlyOnlineSection({ recentlyOnline }: { recentlyOnline: RecentlyOnlineCreator[] }) {
    const [isExpanded, setIsExpanded] = useState(false);
    
    if (recentlyOnline.length === 0) return null;
    
    const displayCount = isExpanded ? recentlyOnline.length : 10;
    const displayList = recentlyOnline.slice(0, displayCount);
    const liveCount = recentlyOnline.filter(c => c.is_live).length;
    const offlineCount = recentlyOnline.length - liveCount;
    
    return (
        <div className="live-section" style={{ marginTop: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <h3 className="section-title" style={{ margin: 0 }}>⏰ Recently Active</h3>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {liveCount > 0 && <span style={{ color: '#22c55e' }}>{liveCount} live</span>}
                    {liveCount > 0 && offlineCount > 0 && ' · '}
                    {offlineCount > 0 && <span>{offlineCount} offline</span>}
                </span>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '0 0 12px' }}>
                Sorted by most recently online (last 24 hours)
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {displayList.map((creator, idx) => {
                    const platformUrl = creator.platform === 'kick'
                        ? `https://kick.com/${creator.username}`
                        : creator.platform === 'twitch'
                            ? `https://twitch.tv/${creator.username}`
                            : creator.platform === 'youtube'
                                ? `https://youtube.com/@${creator.username}`
                                : `https://tiktok.com/@${creator.username}`;
                    
                    // Parse last_seen_online date
                    const lastSeen = new Date(creator.last_seen_online);
                    const now = new Date();
                    const diffMs = now.getTime() - lastSeen.getTime();
                    const diffMins = Math.floor(diffMs / 60000);
                    const diffHours = Math.floor(diffMins / 60);
                    let timeAgo = '';
                    if (diffHours > 0) {
                        timeAgo = `${diffHours}h ago`;
                    } else if (diffMins > 0) {
                        timeAgo = `${diffMins}m ago`;
                    } else {
                        timeAgo = 'Just now';
                    }

                    return (
                        <a
                            key={`${creator.creator_id}-${creator.platform}-${idx}`}
                            href={platformUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                padding: '8px 12px',
                                backgroundColor: creator.is_live ? 'rgba(34,197,94,0.1)' : 'rgba(255,255,255,0.03)',
                                border: `1px solid ${creator.is_live ? 'rgba(34,197,94,0.3)' : 'rgba(255,255,255,0.08)'}`,
                                borderRadius: '8px',
                                textDecoration: 'none',
                                color: 'inherit',
                                transition: 'all 0.2s ease',
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.backgroundColor = creator.is_live ? 'rgba(34,197,94,0.2)' : 'rgba(255,255,255,0.08)';
                                e.currentTarget.style.borderColor = creator.is_live ? 'rgba(34,197,94,0.5)' : 'rgba(255,255,255,0.15)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.backgroundColor = creator.is_live ? 'rgba(34,197,94,0.1)' : 'rgba(255,255,255,0.03)';
                                e.currentTarget.style.borderColor = creator.is_live ? 'rgba(34,197,94,0.3)' : 'rgba(255,255,255,0.08)';
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                {creator.is_live && (
                                    <span style={{
                                        width: '8px',
                                        height: '8px',
                                        backgroundColor: '#22c55e',
                                        borderRadius: '50%',
                                        animation: 'pulse 2s infinite',
                                    }} />
                                )}
                                <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>
                                    {creator.creator_name}
                                </span>
                                <span
                                    style={{
                                        padding: '2px 6px',
                                        backgroundColor: `${getPlatformColor(creator.platform)}25`,
                                        color: getPlatformColor(creator.platform),
                                        borderRadius: '4px',
                                        fontSize: '0.7rem',
                                        fontWeight: 600,
                                        textTransform: 'uppercase',
                                    }}
                                >
                                    {getPlatformIcon(creator.platform)} {creator.platform}
                                </span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                {creator.is_live ? (
                                    <span style={{ 
                                        fontSize: '0.75rem', 
                                        fontWeight: 600, 
                                        color: '#22c55e',
                                        padding: '2px 8px',
                                        backgroundColor: 'rgba(34,197,94,0.15)',
                                        borderRadius: '4px',
                                    }}>
                                        LIVE NOW
                                    </span>
                                ) : (
                                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                        {timeAgo}
                                    </span>
                                )}
                            </div>
                        </a>
                    );
                })}
            </div>
            {recentlyOnline.length > 10 && (
                <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    style={{
                        width: '100%',
                        marginTop: '12px',
                        padding: '10px',
                        backgroundColor: 'rgba(255,255,255,0.05)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '8px',
                        color: 'var(--text-color)',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                        fontWeight: 500,
                        transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)';
                    }}
                >
                    {isExpanded 
                        ? `Show Less ▲` 
                        : `Show All ${recentlyOnline.length} Creators ▼`}
                </button>
            )}
        </div>
    );
}

export default function LiveSummary({
    liveCreators,
    recentlyOnline = [],
    onToggle,
    isCollapsed = false,
    isChecking = false,
    checkProgress,
    selectedPlatform = 'all',
    onPlatformChange,
    lastUpdated,
    onRefresh,
    isRefreshing = false,
    onManageLiveChecks,
    liveCheckCreatorCount,
    totalCreatorCount,
}: LiveSummaryProps) {
    
    // Track page load time
    const [pageLoadTime] = React.useState<number>(Date.now());
    const groupedCreators = groupLiveCreators(liveCreators);

    // Filter creators by selected platform
    const filteredCreators = selectedPlatform === 'all'
        ? groupedCreators
        : groupedCreators.filter(gc => gc.platforms.some(p => p.platform.toLowerCase() === selectedPlatform.toLowerCase()));

    // Separate into live streams and stories for display sections
    const liveStreams = filteredCreators.filter(gc => gc.platforms.some(p => p.status === 'live'));
    const stories = filteredCreators.filter(gc => gc.platforms.every(p => p.status === 'story'));

    const progressPercent = checkProgress && checkProgress.total > 0
        ? Math.round((checkProgress.current / checkProgress.total) * 100)
        : 0;

    // Determine refresh status message
    const getRefreshStatusMessage = () => {
        if (isChecking || isRefreshing) {
            return { text: 'Checking live status...', icon: '⏳', type: 'checking' };
        }
        if (lastUpdated) {
            const timeAgo = formatTimeAgo(Math.floor(lastUpdated / 1000));
            return { text: `Updated ${timeAgo}`, icon: '✓', type: 'updated' };
        }
        return { text: 'Auto-updates every 3 minutes', icon: 'ℹ️', type: 'info' };
    };

    const refreshStatus = getRefreshStatusMessage();

    return (
        <div className="live-summary">
            {/* Link to Creator Content (FROM creators) */}
            <a
                href="/fc/creator_updates/"
                style={{
                    display: 'block',
                    padding: '12px 16px',
                    marginBottom: '8px',
                    backgroundColor: 'rgba(139, 92, 246, 0.15)',
                    border: '1px solid rgba(139, 92, 246, 0.3)',
                    borderRadius: '8px',
                    color: '#c4b5fd',
                    textDecoration: 'none',
                    fontSize: '0.9rem',
                    fontWeight: 500,
                    transition: 'all 0.2s ease',
                    textAlign: 'center'
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'rgba(139, 92, 246, 0.25)';
                    e.currentTarget.style.borderColor = 'rgba(139, 92, 246, 0.5)';
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'rgba(139, 92, 246, 0.15)';
                    e.currentTarget.style.borderColor = 'rgba(139, 92, 246, 0.3)';
                }}
            >
                🎬 View Latest Creator Content
            </a>

            {/* Link to Streamer Updates (ABOUT creators) */}
            <a
                href="#/updates"
                style={{
                    display: 'block',
                    padding: '12px 16px',
                    marginBottom: '12px',
                    backgroundColor: 'rgba(99, 102, 241, 0.15)',
                    border: '1px solid rgba(99, 102, 241, 0.3)',
                    borderRadius: '8px',
                    color: '#a5b4fc',
                    textDecoration: 'none',
                    fontSize: '0.9rem',
                    fontWeight: 500,
                    transition: 'all 0.2s ease',
                    textAlign: 'center'
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'rgba(99, 102, 241, 0.25)';
                    e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.5)';
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'rgba(99, 102, 241, 0.15)';
                    e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.3)';
                }}
            >
                📰 View Creator News & Community Updates
            </a>

            <div className="live-summary-header" onClick={onToggle}>
                <div className="live-summary-title">
                    <span className="live-pulse">🔴</span>
                    <h2>Creators Live Now</h2>
                    {filteredCreators.length > 0 && (
                        <span className="live-count">{filteredCreators.length}</span>
                    )}
                </div>
                <div className="live-summary-controls">
                    {/* Refresh Button */}
                    {onRefresh && (
                        <button 
                            className={`refresh-button ${isChecking || isRefreshing ? 'refreshing' : ''}`}
                            onClick={(e) => {
                                e.stopPropagation();
                                onRefresh();
                            }}
                            disabled={isChecking || isRefreshing}
                            title="Refresh live status"
                            aria-label="Refresh live status"
                        >
                            <span className="refresh-icon">🔄</span>
                        </button>
                    )}
                    <button className="collapse-toggle" aria-label={isCollapsed ? "Expand" : "Collapse"}>
                        {isCollapsed ? '▼' : '▲'}
                    </button>
                </div>
            </div>

            {/* Refresh Status Bar - Always visible */}
            <div className={`refresh-status-bar ${refreshStatus.type}`}>
                <span className="refresh-status-icon">{refreshStatus.icon}</span>
                <span className="refresh-status-text">{refreshStatus.text}</span>
                {(isChecking || isRefreshing) && checkProgress && (
                    <span className="refresh-status-progress">
                        ({checkProgress.current}/{checkProgress.total})
                    </span>
                )}
            </div>

            {!isCollapsed && (
                <div className="live-summary-content">
                    {/* Platform Filter + Manage Live Checks */}
                    <div className="platform-filter" style={{
                        marginBottom: '16px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        flexWrap: 'wrap'
                    }}>
                        <label htmlFor="platform-filter" style={{
                            fontSize: '0.9rem',
                            color: 'var(--text-muted)',
                            fontWeight: 500
                        }}>
                            Filter by platform:
                        </label>
                        <select
                            id="platform-filter"
                            value={selectedPlatform}
                            onChange={(e) => onPlatformChange?.(e.target.value)}
                            style={{
                                padding: '8px 12px',
                                borderRadius: '8px',
                                border: '1px solid rgba(255,255,255,0.2)',
                                backgroundColor: 'rgba(0,0,0,0.3)',
                                color: 'white',
                                fontSize: '0.9rem',
                                cursor: 'pointer',
                                minWidth: '150px'
                            }}
                        >
                            {PLATFORM_OPTIONS.map(opt => (
                                <option key={opt.value} value={opt.value}>
                                    {opt.label}
                                </option>
                            ))}
                        </select>
                        {isChecking && (
                            <span style={{
                                fontSize: '0.8rem',
                                color: 'var(--accent)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px'
                            }}>
                                <span className="checking-spinner-small">⏳</span>
                                Checking...
                            </span>
                        )}
                        {onManageLiveChecks && (
                            <button
                                onClick={onManageLiveChecks}
                                style={{
                                    marginLeft: 'auto',
                                    padding: '6px 14px',
                                    background: 'rgba(99, 102, 241, 0.15)',
                                    border: '1px solid rgba(99, 102, 241, 0.35)',
                                    borderRadius: '8px',
                                    color: '#a5b4fc',
                                    cursor: 'pointer',
                                    fontSize: '0.8rem',
                                    fontWeight: 500,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    transition: 'all 0.2s ease',
                                    whiteSpace: 'nowrap',
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.background = 'rgba(99, 102, 241, 0.25)';
                                    e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.5)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.background = 'rgba(99, 102, 241, 0.15)';
                                    e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.35)';
                                }}
                                title="Choose which creators to check for live status"
                            >
                                <span>⚙️</span>
                                Manage
                                {liveCheckCreatorCount !== undefined && totalCreatorCount !== undefined && (
                                    <span style={{
                                        padding: '1px 6px',
                                        background: 'rgba(99, 102, 241, 0.3)',
                                        borderRadius: '4px',
                                        fontSize: '0.75rem',
                                    }}>
                                        {liveCheckCreatorCount}/{totalCreatorCount}
                                    </span>
                                )}
                            </button>
                        )}
                    </div>

                    {/* Progress bar during checking - always show when isChecking is true */}
                    {/* Timestamps display */}
                    <div className="timestamps" style={{
                        marginBottom: '12px',
                        padding: '8px 12px',
                        backgroundColor: 'rgba(0,0,0,0.15)',
                        borderRadius: '6px',
                        fontSize: '0.75rem',
                        color: 'var(--text-muted)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        flexWrap: 'wrap',
                        gap: '8px'
                    }}>
                        <span>
                            📅 Page loaded: {new Date(pageLoadTime).toLocaleString()}
                        </span>
                        {lastUpdated && (
                            <span>
                                🔄 Last updated: {new Date(lastUpdated).toLocaleString()}
                                {' '}
                                ({formatTimeAgo(Math.floor(lastUpdated / 1000))})
                            </span>
                        )}
                    </div>

                    {isChecking && (
                        <div className="checking-progress-container" style={{
                            marginBottom: '20px',
                            padding: '16px',
                            backgroundColor: 'rgba(0,0,0,0.2)',
                            borderRadius: '8px',
                            border: '1px solid rgba(255,255,255,0.05)'
                        }}>
                            <p className="checking-text" style={{ margin: '0 0 12px 0' }}>
                                <span className="checking-spinner">⏳</span>
                                Checking for live creators...
                            </p>
                            {checkProgress && (
                                <div className="checking-progress" style={{ width: '100%', maxWidth: '400px' }}>
                                    <div style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        marginBottom: '6px',
                                        fontSize: '0.85rem',
                                        color: 'var(--text-muted)'
                                    }}>
                                        <span>Checking: {checkProgress.currentCreator}</span>
                                        <span>{checkProgress.current} / {checkProgress.total} ({progressPercent}%)</span>
                                    </div>
                                    <div style={{
                                        width: '100%',
                                        height: '6px',
                                        backgroundColor: 'rgba(255,255,255,0.1)',
                                        borderRadius: '3px',
                                        overflow: 'hidden'
                                    }}>
                                        <div style={{
                                            width: `${progressPercent}%`,
                                            height: '100%',
                                            backgroundColor: 'var(--accent)',
                                            transition: 'width 0.3s ease',
                                            borderRadius: '3px'
                                        }} />
                                    </div>
                                </div>
                            )}
                            <p className="checking-subtext" style={{
                                margin: '12px 0 0 0',
                                fontSize: '0.8rem',
                                color: 'var(--text-muted)',
                                fontStyle: 'italic'
                            }}>This may take awhile depending on how many creators you follow. Check back soon!</p>
                        </div>
                    )}

                    {filteredCreators.length === 0 && !isChecking ? (
                        <div className="no-live-message">
                            <p>No creators live right now. Check back soon!</p>
                            <p className="no-live-subtext">
                                Live status updates automatically every 3 minutes.
                                Click the refresh button to check now.
                            </p>
                        </div>
                    ) : (
                        <>
                            {liveStreams.length > 0 && (
                                <div className="live-section">
                                    <h3 className="section-title">🔴 Live Streams</h3>
                                    <div className="live-grid">
                                        {liveStreams.map((gc) => (
                                            <div
                                                key={gc.creator.id}
                                                className="live-card"
                                            >
                                                <div className="live-card-header">
                                                    <img
                                                        src={gc.creator.avatarUrl || `https://ui-avatars.com/api/?name=${encodeURIComponent(gc.creator.name)}&background=random`}
                                                        alt={gc.creator.name}
                                                        className="live-avatar"
                                                    />
                                                    <div className="live-info">
                                                        <div className="creator-name">{gc.creator.name}</div>
                                                        <MultiPlatformBadge platforms={gc.platforms.filter(p => p.status === 'live')} />
                                                    </div>
                                                </div>
                                                {gc.latestStartedAt && (
                                                    <div className="live-time">Started {formatTimeAgo(gc.latestStartedAt)}</div>
                                                )}
                                                {/* Platform links */}
                                                <div className="platform-links">
                                                    {gc.platforms
                                                        .filter(p => p.status === 'live')
                                                        .map(p => (
                                                            <a
                                                                key={p.platform}
                                                                href={p.accountUrl}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="platform-link"
                                                                style={{
                                                                    backgroundColor: `${getPlatformColor(p.platform)}30`,
                                                                    color: getPlatformColor(p.platform)
                                                                }}
                                                            >
                                                                {getPlatformIcon(p.platform)} Watch on {p.platform}
                                                            </a>
                                                        ))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {stories.length > 0 && (
                                <div className="live-section">
                                    <h3 className="section-title">📱 Recent Stories</h3>
                                    <div className="live-grid">
                                        {stories.map((gc) => {
                                            const story = gc.platforms.find(p => p.status === 'story');
                                            return (
                                                <a
                                                    key={gc.creator.id}
                                                    href={story?.accountUrl || '#'}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="live-card story-card"
                                                >
                                                    <div className="live-card-header">
                                                        <img
                                                            src={gc.creator.avatarUrl || `https://ui-avatars.com/api/?name=${encodeURIComponent(gc.creator.name)}&background=random`}
                                                            alt={gc.creator.name}
                                                            className="live-avatar"
                                                        />
                                                        <div className="live-info">
                                                            <div className="creator-name">{gc.creator.name}</div>
                                                            <MultiPlatformBadge platforms={gc.platforms} />
                                                        </div>
                                                    </div>
                                                    <div className="story-info">
                                                        {story?.storyCount && <span>{story.storyCount} video{story.storyCount > 1 ? 's' : ''}</span>}
                                                        {story?.postedAt && <span>Posted {formatTimeAgo(story.postedAt)}</span>}
                                                    </div>
                                                </a>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </>
                    )}

                    {/* Recently Online Section - Always visible below live/stories or no-live message */}
                    <RecentlyOnlineSection recentlyOnline={recentlyOnline} />
                </div>
            )}
        </div>
    );
}
