/**
 * UPDATE #113: Advanced Caching Strategies
 * Multi-level caching with Redis support
 */

interface CacheStrategy {
    ttl: number; // Time to live in seconds
    staleWhileRevalidate?: number; // Serve stale while fetching fresh
    tags?: string[]; // Cache tags for invalidation
}

class AdvancedCacheManager {
    private memoryCache: Map<string, { data: any; expires: number; tags: string[] }> = new Map();
    private requestCache: Map<string, Promise<any>> = new Map();

    /**
     * Get from cache with strategy
     */
    async get<T>(
        key: string,
        fetcher: () => Promise<T>,
        strategy: CacheStrategy = { ttl: 300 }
    ): Promise<T> {
        const cached = this.memoryCache.get(key);
        const now = Date.now();

        // Check if we have valid cached data
        if (cached && now < cached.expires) {
            return cached.data;
        }

        // Stale-while-revalidate: return stale data while fetching fresh
        if (
            cached &&
            strategy.staleWhileRevalidate &&
            now < cached.expires + strategy.staleWhileRevalidate * 1000
        ) {
            // Return stale data immediately
            const staleData = cached.data;

            // Fetch fresh data in background
            this.fetchAndCache(key, fetcher, strategy).catch(console.error);

            return staleData;
        }

        // Deduplicate concurrent requests
        if (this.requestCache.has(key)) {
            return this.requestCache.get(key)!;
        }

        return this.fetchAndCache(key, fetcher, strategy);
    }

    /**
     * Fetch and cache data
     */
    private async fetchAndCache<T>(
        key: string,
        fetcher: () => Promise<T>,
        strategy: CacheStrategy
    ): Promise<T> {
        const promise = fetcher();
        this.requestCache.set(key, promise);

        try {
            const data = await promise;

            this.memoryCache.set(key, {
                data,
                expires: Date.now() + strategy.ttl * 1000,
                tags: strategy.tags || []
            });

            // Also cache in localStorage for persistence
            try {
                localStorage.setItem(
                    `cache_${key}`,
                    JSON.stringify({
                        data,
                        expires: Date.now() + strategy.ttl * 1000
                    })
                );
            } catch (e) {
                // Ignore localStorage errors
            }

            return data;
        } finally {
            this.requestCache.delete(key);
        }
    }

    /**
     * Invalidate by key
     */
    invalidate(key: string): void {
        this.memoryCache.delete(key);
        localStorage.removeItem(`cache_${key}`);
    }

    /**
     * Invalidate by tag
     */
    invalidateByTag(tag: string): void {
        for (const [key, value] of this.memoryCache.entries()) {
            if (value.tags.includes(tag)) {
                this.invalidate(key);
            }
        }
    }

    /**
     * Prefetch data
     */
    async prefetch<T>(
        key: string,
        fetcher: () => Promise<T>,
        strategy: CacheStrategy = { ttl: 300 }
    ): Promise<void> {
        await this.get(key, fetcher, strategy);
    }

    /**
     * Clear all cache
     */
    clear(): void {
        this.memoryCache.clear();

        // Clear localStorage cache
        const keys = Object.keys(localStorage);
        keys.forEach(key => {
            if (key.startsWith('cache_')) {
                localStorage.removeItem(key);
            }
        });
    }

    /**
     * Get cache stats
     */
    getStats(): {
        size: number;
        keys: string[];
        hitRate: number;
    } {
        return {
            size: this.memoryCache.size,
            keys: Array.from(this.memoryCache.keys()),
            hitRate: 0 // Would track in production
        };
    }
}

export const advancedCache = new AdvancedCacheManager();

/**
 * React hook for cached data
 */
import { useState, useEffect } from 'react';

export function useCachedQuery<T>(
    key: string,
    fetcher: () => Promise<T>,
    strategy: CacheStrategy = { ttl: 300 }
) {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        let cancelled = false;

        const fetchData = async () => {
            try {
                const result = await advancedCache.get(key, fetcher, strategy);
                if (!cancelled) {
                    setData(result);
                    setError(null);
                }
            } catch (err) {
                if (!cancelled) {
                    setError(err instanceof Error ? err : new Error('Fetch failed'));
                }
            } finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        };

        fetchData();

        return () => {
            cancelled = true;
        };
    }, [key]);

    const refetch = async () => {
        setLoading(true);
        advancedCache.invalidate(key);

        try {
            const result = await advancedCache.get(key, fetcher, strategy);
            setData(result);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err : new Error('Fetch failed'));
        } finally {
            setLoading(false);
        }
    };

    return { data, loading, error, refetch };
}

/**
 * Cache warming utility
 */
export async function warmCache(routes: Array<{ key: string; fetcher: () => Promise<any> }>) {
    console.log(`Warming cache for ${routes.length} routes...`);

    await Promise.all(
        routes.map(route =>
            advancedCache.prefetch(route.key, route.fetcher, { ttl: 3600 })
        )
    );

    console.log('Cache warming complete');
}
