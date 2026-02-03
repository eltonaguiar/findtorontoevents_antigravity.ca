/**
 * UPDATE #114: CDN Integration
 * Content Delivery Network optimization
 */

interface CDNConfig {
    provider: 'cloudflare' | 'cloudfront' | 'fastly';
    baseUrl: string;
    regions: string[];
    cacheRules: CacheRule[];
}

interface CacheRule {
    pattern: string;
    ttl: number;
    edgeCacheTtl?: number;
    bypassCache?: boolean;
}

class CDNManager {
    private config: CDNConfig;

    constructor(config: CDNConfig) {
        this.config = config;
    }

    /**
     * Get CDN URL for asset
     */
    getCDNUrl(path: string): string {
        // Remove leading slash
        const cleanPath = path.startsWith('/') ? path.slice(1) : path;
        return `${this.config.baseUrl}/${cleanPath}`;
    }

    /**
     * Get optimized image URL
     */
    getImageUrl(
        path: string,
        options: {
            width?: number;
            height?: number;
            quality?: number;
            format?: 'webp' | 'avif' | 'jpg' | 'png';
        } = {}
    ): string {
        const params = new URLSearchParams();

        if (options.width) params.append('w', options.width.toString());
        if (options.height) params.append('h', options.height.toString());
        if (options.quality) params.append('q', options.quality.toString());
        if (options.format) params.append('f', options.format);

        const baseUrl = this.getCDNUrl(path);
        return params.toString() ? `${baseUrl}?${params.toString()}` : baseUrl;
    }

    /**
     * Purge cache for path
     */
    async purgeCache(paths: string[]): Promise<void> {
        console.log(`Purging CDN cache for ${paths.length} paths`);

        // In production, call CDN API
        // Example for Cloudflare:
        // await fetch('https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache', {
        //   method: 'POST',
        //   headers: { 'Authorization': `Bearer ${apiKey}` },
        //   body: JSON.stringify({ files: paths })
        // });
    }

    /**
     * Prefetch assets
     */
    prefetchAssets(urls: string[]): void {
        urls.forEach(url => {
            const link = document.createElement('link');
            link.rel = 'prefetch';
            link.href = this.getCDNUrl(url);
            document.head.appendChild(link);
        });
    }

    /**
     * Preload critical assets
     */
    preloadAssets(urls: string[]): void {
        urls.forEach(url => {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.href = this.getCDNUrl(url);
            link.as = this.getAssetType(url);
            document.head.appendChild(link);
        });
    }

    /**
     * Get asset type for preload
     */
    private getAssetType(url: string): string {
        if (url.match(/\.(jpg|jpeg|png|gif|webp|avif)$/i)) return 'image';
        if (url.match(/\.(woff|woff2|ttf|otf)$/i)) return 'font';
        if (url.match(/\.(css)$/i)) return 'style';
        if (url.match(/\.(js)$/i)) return 'script';
        if (url.match(/\.(mp4|webm)$/i)) return 'video';
        return 'fetch';
    }

    /**
     * Get cache rule for path
     */
    getCacheRule(path: string): CacheRule | undefined {
        return this.config.cacheRules.find(rule => {
            const regex = new RegExp(rule.pattern);
            return regex.test(path);
        });
    }
}

// Default CDN configuration
export const cdnManager = new CDNManager({
    provider: 'cloudflare',
    baseUrl: 'https://cdn.movieshows.com',
    regions: ['us-east', 'us-west', 'eu-west', 'ap-southeast'],
    cacheRules: [
        {
            pattern: '\\.(jpg|jpeg|png|gif|webp|avif)$',
            ttl: 31536000, // 1 year
            edgeCacheTtl: 86400 // 1 day
        },
        {
            pattern: '\\.(css|js)$',
            ttl: 604800, // 1 week
            edgeCacheTtl: 3600 // 1 hour
        },
        {
            pattern: '\\.(woff|woff2|ttf|otf)$',
            ttl: 31536000, // 1 year
            edgeCacheTtl: 86400 // 1 day
        },
        {
            pattern: '/api/',
            ttl: 0,
            bypassCache: true
        }
    ]
});

/**
 * React hook for CDN images
 */
import React from 'react';

interface CDNImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
    src: string;
    width?: number;
    height?: number;
    quality?: number;
    format?: 'webp' | 'avif' | 'jpg' | 'png';
}

export function CDNImage({
    src,
    width,
    height,
    quality = 85,
    format = 'webp',
    alt,
    ...props
}: CDNImageProps) {
    const cdnUrl = cdnManager.getImageUrl(src, { width, height, quality, format });

    return (
        <img
            src={cdnUrl}
            alt={alt}
            loading="lazy"
            decoding="async"
            {...props}
        />
    );
}

/**
 * Responsive image component
 */
export function ResponsiveImage({
    src,
    alt,
    sizes = '100vw',
    ...props
}: CDNImageProps & { sizes?: string }) {
    const widths = [320, 640, 768, 1024, 1280, 1536];

    const srcSet = widths
        .map(w => `${cdnManager.getImageUrl(src, { width: w, format: 'webp' })} ${w}w`)
        .join(', ');

    return (
        <img
            src={cdnManager.getImageUrl(src, { width: 1024, format: 'webp' })}
            srcSet={srcSet}
            sizes={sizes}
            alt={alt}
            loading="lazy"
            decoding="async"
            {...props}
        />
    );
}
