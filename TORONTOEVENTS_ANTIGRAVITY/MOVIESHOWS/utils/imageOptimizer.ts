/**
 * UPDATE #64: Image Optimization Utility
 * Optimize and cache images
 */

interface ImageOptimizationOptions {
    quality?: number;
    maxWidth?: number;
    maxHeight?: number;
    format?: 'webp' | 'jpeg' | 'png';
}

class ImageOptimizer {
    private cache = new Map<string, string>();

    async optimizeImage(
        imageUrl: string,
        options: ImageOptimizationOptions = {}
    ): Promise<string> {
        const cacheKey = `${imageUrl}_${JSON.stringify(options)}`;

        // Check cache first
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey)!;
        }

        try {
            // For external images, we can use a CDN service
            // For now, return original URL with query params for CDN optimization
            const url = new URL(imageUrl);

            if (options.maxWidth) {
                url.searchParams.set('w', options.maxWidth.toString());
            }
            if (options.maxHeight) {
                url.searchParams.set('h', options.maxHeight.toString());
            }
            if (options.quality) {
                url.searchParams.set('q', options.quality.toString());
            }
            if (options.format) {
                url.searchParams.set('fm', options.format);
            }

            const optimizedUrl = url.toString();
            this.cache.set(cacheKey, optimizedUrl);
            return optimizedUrl;
        } catch (error) {
            console.error('Image optimization failed:', error);
            return imageUrl;
        }
    }

    async preloadImage(url: string): Promise<void> {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => resolve();
            img.onerror = reject;
            img.src = url;
        });
    }

    async preloadImages(urls: string[]): Promise<void> {
        await Promise.all(urls.map(url => this.preloadImage(url)));
    }

    clearCache() {
        this.cache.clear();
    }

    getCacheSize(): number {
        return this.cache.size;
    }
}

export const imageOptimizer = new ImageOptimizer();

/**
 * Generate responsive image srcset
 */
export function generateSrcSet(baseUrl: string, sizes: number[]): string {
    return sizes
        .map(size => `${baseUrl}?w=${size} ${size}w`)
        .join(', ');
}

/**
 * Get optimal image size based on viewport
 */
export function getOptimalImageSize(): number {
    const width = window.innerWidth;

    if (width < 640) return 640;
    if (width < 768) return 768;
    if (width < 1024) return 1024;
    if (width < 1280) return 1280;
    return 1920;
}
