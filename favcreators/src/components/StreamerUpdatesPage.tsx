import React, { useState, useEffect, useCallback } from 'react';
import { resolveAuthBase } from '../utils/auth';

// Smart Thumbnail component with multiple fallback attempts
interface SmartThumbnailProps {
    src: string;
    alt: string;
    contentUrl: string;
    platform: string;
    style?: React.CSSProperties;
}

const SmartThumbnail: React.FC<SmartThumbnailProps> = ({ src, alt, contentUrl, platform, style }) => {
    const [currentSrc, setCurrentSrc] = useState(src);
    const [attemptIndex, setAttemptIndex] = useState(0);
    const [hasError, setHasError] = useState(false);

    // Generate fallback URLs based on platform and content URL
    const getFallbackUrls = useCallback(() => {
        const fallbacks: string[] = [];

        // YouTube fallbacks
        if (platform === 'youtube' || contentUrl.includes('youtube.com') || contentUrl.includes('youtu.be')) {
            // Extract video ID
            let videoId: string | null = null;
            const patterns = [
                /youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})/,
                /youtu\.be\/([a-zA-Z0-9_-]{11})/,
                /youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})/,
                /youtube\.com\/embed\/([a-zA-Z0-9_-]{11})/
            ];
            for (const pattern of patterns) {
                const match = contentUrl.match(pattern);
                if (match) {
                    videoId = match[1];
                    break;
                }
            }

            if (videoId) {
                fallbacks.push(
                    `https://i.ytimg.com/vi/${videoId}/maxresdefault.jpg`,
                    `https://i.ytimg.com/vi/${videoId}/sddefault.jpg`,
                    `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`,
                    `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg`,
                    `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`,
                    `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`,
                    `https://i3.ytimg.com/vi/${videoId}/hqdefault.jpg`
                );
            }
        }

        // Add original src if not already in list
        if (src && !fallbacks.includes(src)) {
            fallbacks.unshift(src);
        }

        return fallbacks;
    }, [src, contentUrl, platform]);

    const fallbackUrls = getFallbackUrls();

    const handleError = () => {
        const nextIndex = attemptIndex + 1;
        if (nextIndex < fallbackUrls.length) {
            setAttemptIndex(nextIndex);
            setCurrentSrc(fallbackUrls[nextIndex]);
        } else {
            setHasError(true);
        }
    };

    // Platform-specific placeholder styles
    const platformColors: Record<string, string> = {
        youtube: '#FF0000',
        tiktok: '#000000',
        twitter: '#1DA1F2',
        instagram: '#E4405F',
        news: '#4A4A4A'
    };

    const platformIcons: Record<string, string> = {
        youtube: '📺',
        tiktok: '🎵',
        twitter: '🐦',
        instagram: '📷',
        news: '📰'
    };

    if (hasError || !currentSrc) {
        // Render placeholder
        return (
            <div style={{
                ...style,
                backgroundColor: platformColors[platform] || '#6B7280',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontSize: '48px'
            }}>
                {platformIcons[platform] || '📄'}
            </div>
        );
    }

    return (
        <img
            src={currentSrc}
            alt={alt}
            style={style}
            onError={handleError}
            loading="lazy"
        />
    );
};

interface Creator {
    id: number;
    name: string;
    avatarUrl: string;
    followerCount: number;
    contentCount: number;
}

interface ContentItem {
    id: number;
    creator: {
        id: number;
        name: string;
        avatarUrl: string;
    };
    platform: 'youtube' | 'tiktok' | 'twitter' | 'instagram' | 'news';
    contentType: 'video' | 'short' | 'reel' | 'story' | 'tweet' | 'post' | 'article';
    title: string;
    description: string;
    thumbnailUrl: string;
    contentUrl: string;
    publishedAt: number;
    metadata?: any;
}

const StreamerUpdatesPage: React.FC = () => {
    const [contentItems, setContentItems] = useState<ContentItem[]>([]);
    const [filteredItems, setFilteredItems] = useState<ContentItem[]>([]);
    const [platformFilter, setPlatformFilter] = useState<string[]>(['all']);
    const [creatorFilter, setCreatorFilter] = useState<number | null>(null);
    const [availableCreators, setAvailableCreators] = useState<Creator[]>([]);
    const [contentTypeFilter] = useState<string[]>(['all']); // Reserved for future use
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [userId, setUserId] = useState<number>(0);

    // Platform icons
    const platformIcons: Record<string, string> = {
        youtube: '📺',
        tiktok: '🎵',
        twitter: '🐦',
        instagram: '📷',
        news: '📰'
    };

    // Fetch user ID from session (or URL param for testing)
    useEffect(() => {
        const fetchUserId = async () => {
            // Check for URL parameter override (for testing)
            const urlParams = new URLSearchParams(window.location.search);
            const urlUserId = urlParams.get('user_id');
            if (urlUserId && !isNaN(parseInt(urlUserId))) {
                console.log('[StreamerUpdates] Using URL param user_id:', urlUserId);
                setUserId(parseInt(urlUserId));
                return;
            }

            // Check hash params (for React Router hash mode)
            const hashParams = new URLSearchParams(window.location.hash.split('?')[1] || '');
            const hashUserId = hashParams.get('user_id');
            if (hashUserId && !isNaN(parseInt(hashUserId))) {
                console.log('[StreamerUpdates] Using hash param user_id:', hashUserId);
                setUserId(parseInt(hashUserId));
                return;
            }

            try {
                const authBase = await resolveAuthBase();
                const response = await fetch(`${authBase}/get_me.php`, {
                    credentials: 'include'
                });

                if (response.ok) {
                    const data = await response.json();
                    console.log('[StreamerUpdates] get_me.php returned:', data);
                    // get_me.php returns {user: {id: ..., ...}, debug_log_enabled: ...}
                    const userId = data.user?.id || data.id || 0;
                    console.log('[StreamerUpdates] Detected user_id:', userId);
                    setUserId(userId);
                } else {
                    setUserId(0); // Guest mode
                }
            } catch (err) {
                console.error('Failed to fetch user ID:', err);
                setUserId(0);
            }
        };

        fetchUserId();
    }, []);

    // Fetch available creators
    useEffect(() => {
        const fetchCreators = async () => {
            if (userId === null) return;

            try {
                const authBase = await resolveAuthBase();
                const url = `${authBase}/creator_news_creators.php?user_id=${userId}`;
                console.log('[StreamerUpdates] Fetching creators from:', url);

                const response = await fetch(url);
                if (response.ok) {
                    const data = await response.json();
                    console.log('[StreamerUpdates] Creators API response:', data);
                    console.log('[StreamerUpdates] Setting availableCreators to:', data.creators);
                    setAvailableCreators(data.creators || []);
                } else {
                    console.error('[StreamerUpdates] Failed to fetch creators, status:', response.status);
                }
            } catch (err) {
                console.error('Failed to fetch creators:', err);
            }
        };

        fetchCreators();
    }, [userId]);

    // Fetch content feed
    const fetchContentFeed = useCallback(async () => {
        if (userId === null) return;

        setIsLoading(true);
        setError(null);

        try {
            const authBase = await resolveAuthBase();
            const creatorParam = creatorFilter ? `&creator_id=${creatorFilter}` : '';
            const url = `${authBase}/creator_news_api.php?user_id=${userId}&limit=50${creatorParam}`;

            console.log('[StreamerUpdates] Fetching content:', { userId, creatorFilter, url });

            const response = await fetch(url, {
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.error) {
                setError(data.error);
                setContentItems([]);
            } else {
                console.log('[StreamerUpdates] Received items:', data.items?.length || 0);
                setContentItems(data.items || []);
            }
        } catch (err) {
            console.error('Failed to fetch content feed:', err);
            setError(err instanceof Error ? err.message : 'Failed to load content');
            setContentItems([]);
        } finally {
            setIsLoading(false);
        }
    }, [userId, creatorFilter]);

    // Initial load and re-fetch when filters change
    useEffect(() => {
        if (userId !== null) {
            fetchContentFeed();
        }
    }, [userId, creatorFilter, fetchContentFeed]);

    // Apply filters
    useEffect(() => {
        let filtered = [...contentItems];

        // Platform filter
        if (!platformFilter.includes('all')) {
            filtered = filtered.filter(item => platformFilter.includes(item.platform));
        }

        // Content type filter
        if (!contentTypeFilter.includes('all')) {
            filtered = filtered.filter(item => contentTypeFilter.includes(item.contentType));
        }

        setFilteredItems(filtered);
    }, [contentItems, platformFilter, contentTypeFilter]);

    // Toggle platform filter
    const togglePlatformFilter = (platform: string) => {
        if (platform === 'all') {
            setPlatformFilter(['all']);
        } else {
            const newFilters = platformFilter.includes('all')
                ? [platform]
                : platformFilter.includes(platform)
                    ? platformFilter.filter(p => p !== platform)
                    : [...platformFilter, platform];

            setPlatformFilter(newFilters.length === 0 ? ['all'] : newFilters);
        }
    };

    // Format timestamp
    const formatTimestamp = (timestamp: number): string => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);

        if (diffHours < 1) return 'Just now';
        if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

        return date.toLocaleDateString();
    };

    return (
        <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h1 style={{ margin: 0 }}>Streamer Updates</h1>
                <button
                    onClick={fetchContentFeed}
                    disabled={isLoading}
                    style={{
                        padding: '10px 20px',
                        backgroundColor: 'var(--primary, #007bff)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '5px',
                        cursor: isLoading ? 'not-allowed' : 'pointer',
                        opacity: isLoading ? 0.6 : 1
                    }}
                >
                    {isLoading ? 'Refreshing...' : '🔄 Refresh'}
                </button>
            </div>

            {/* Filters */}
            <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: 'var(--bg-secondary, #f8f9fa)', borderRadius: '8px' }}>
                <div style={{ marginBottom: '10px' }}>
                    <strong>Creator:</strong>
                    <select
                        value={creatorFilter || ''}
                        onChange={(e) => setCreatorFilter(e.target.value ? parseInt(e.target.value) : null)}
                        style={{
                            marginLeft: '10px',
                            padding: '5px 10px',
                            borderRadius: '5px',
                            border: '1px solid var(--border, #ddd)'
                        }}
                    >
                        <option value="">All Creators</option>
                        {availableCreators.map(creator => (
                            <option key={creator.id} value={creator.id}>
                                {creator.name} ({creator.contentCount} items)
                            </option>
                        ))}
                    </select>
                </div>
                <div style={{ marginBottom: '10px' }}>
                    <strong>Platforms:</strong>
                    {['all', 'youtube', 'tiktok', 'twitter', 'instagram', 'news'].map(platform => (
                        <button
                            key={platform}
                            onClick={() => togglePlatformFilter(platform)}
                            style={{
                                margin: '0 5px',
                                padding: '5px 15px',
                                backgroundColor: platformFilter.includes(platform) ? 'var(--primary, #007bff)' : 'var(--bg, white)',
                                color: platformFilter.includes(platform) ? 'white' : 'var(--text, black)',
                                border: '1px solid var(--border, #ddd)',
                                borderRadius: '20px',
                                cursor: 'pointer'
                            }}
                        >
                            {platform === 'all' ? 'All' : `${platformIcons[platform]} ${platform.charAt(0).toUpperCase() + platform.slice(1)}`}
                        </button>
                    ))}
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <div style={{ padding: '15px', backgroundColor: '#f8d7da', color: '#721c24', borderRadius: '5px', marginBottom: '20px' }}>
                    <strong>Error:</strong> {error}
                </div>
            )}

            {/* Loading State */}
            {isLoading && (
                <div style={{ textAlign: 'center', padding: '40px' }}>
                    <div style={{ fontSize: '48px' }}>⏳</div>
                    <p>Loading content...</p>
                </div>
            )}

            {/* Empty State */}
            {!isLoading && filteredItems.length === 0 && !error && (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted, #666)' }}>
                    <div style={{ fontSize: '48px', marginBottom: '10px' }}>📭</div>
                    <p>No content found. Follow some creators to see their latest updates!</p>
                </div>
            )}

            {/* Content Feed */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
                {filteredItems.map(item => (
                    <div
                        key={item.id}
                        style={{
                            border: '1px solid var(--border, #ddd)',
                            borderRadius: '8px',
                            overflow: 'hidden',
                            backgroundColor: 'var(--bg, white)',
                            transition: 'transform 0.2s, box-shadow 0.2s',
                            cursor: 'pointer'
                        }}
                        onClick={() => window.open(item.contentUrl, '_blank')}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.transform = 'translateY(-4px)';
                            e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.transform = 'translateY(0)';
                            e.currentTarget.style.boxShadow = 'none';
                        }}
                    >
                        {/* Thumbnail with smart fallbacks */}
                        <SmartThumbnail
                            src={item.thumbnailUrl}
                            alt={item.title}
                            contentUrl={item.contentUrl}
                            platform={item.platform}
                            style={{ width: '100%', height: '180px', objectFit: 'cover' }}
                        />

                        {/* Content */}
                        <div style={{ padding: '15px' }}>
                            {/* Creator Header - Prominent */}
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                marginBottom: '12px',
                                padding: '8px',
                                backgroundColor: 'rgba(0,0,0,0.05)',
                                borderRadius: '4px'
                            }}>
                                {item.creator.avatarUrl && (
                                    <img
                                        src={item.creator.avatarUrl}
                                        alt={item.creator.name}
                                        style={{
                                            width: '32px',
                                            height: '32px',
                                            borderRadius: '50%',
                                            marginRight: '10px',
                                            objectFit: 'cover'
                                        }}
                                    />
                                )}
                                <div>
                                    <div style={{ fontWeight: 'bold', fontSize: '14px', color: 'var(--text, black)' }}>
                                        {item.creator.name}
                                    </div>
                                    <div style={{ fontSize: '11px', color: 'var(--text-muted, #666)' }}>
                                        {platformIcons[item.platform]} {item.platform.toUpperCase()}
                                    </div>
                                </div>
                            </div>

                            {/* Title */}
                            <h3 style={{
                                margin: '0 0 10px 0',
                                fontSize: '16px',
                                lineHeight: '1.4',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                display: '-webkit-box',
                                WebkitLineClamp: 2,
                                WebkitBoxOrient: 'vertical'
                            }}>
                                {item.title || 'Untitled'}
                            </h3>

                            {/* Description */}
                            {item.description && (
                                <p style={{
                                    margin: '0 0 10px 0',
                                    fontSize: '14px',
                                    color: 'var(--text-muted, #666)',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    display: '-webkit-box',
                                    WebkitLineClamp: 2,
                                    WebkitBoxOrient: 'vertical'
                                }}>
                                    {item.description}
                                </p>
                            )}

                            {/* Timestamp */}
                            <div style={{ fontSize: '12px', color: 'var(--text-muted, #999)' }}>
                                {formatTimestamp(item.publishedAt)}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default StreamerUpdatesPage;
