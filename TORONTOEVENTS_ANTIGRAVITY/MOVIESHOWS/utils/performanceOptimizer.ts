/**
 * UPDATE #93: Performance Optimizer
 * Advanced performance utilities
 */

class PerformanceOptimizer {
    /**
     * Lazy load images with Intersection Observer
     */
    lazyLoadImages(selector: string = 'img[data-src]'): void {
        if (!('IntersectionObserver' in window)) {
            // Fallback for older browsers
            this.loadAllImages(selector);
            return;
        }

        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target as HTMLImageElement;
                    const src = img.getAttribute('data-src');

                    if (src) {
                        img.src = src;
                        img.removeAttribute('data-src');
                        observer.unobserve(img);
                    }
                }
            });
        });

        document.querySelectorAll(selector).forEach(img => {
            imageObserver.observe(img);
        });
    }

    /**
     * Preload critical resources
     */
    preloadResources(resources: { href: string; as: string; type?: string }[]): void {
        resources.forEach(resource => {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.href = resource.href;
            link.as = resource.as;
            if (resource.type) {
                link.type = resource.type;
            }
            document.head.appendChild(link);
        });
    }

    /**
     * Prefetch next page resources
     */
    prefetchPage(url: string): void {
        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = url;
        document.head.appendChild(link);
    }

    /**
     * Debounce function
     */
    debounce<T extends (...args: any[]) => any>(
        func: T,
        wait: number
    ): (...args: Parameters<T>) => void {
        let timeout: NodeJS.Timeout;

        return function executedFunction(...args: Parameters<T>) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };

            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Throttle function
     */
    throttle<T extends (...args: any[]) => any>(
        func: T,
        limit: number
    ): (...args: Parameters<T>) => void {
        let inThrottle: boolean;

        return function executedFunction(...args: Parameters<T>) {
            if (!inThrottle) {
                func(...args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * Request idle callback wrapper
     */
    runWhenIdle(callback: () => void, timeout: number = 2000): void {
        if ('requestIdleCallback' in window) {
            requestIdleCallback(callback, { timeout });
        } else {
            setTimeout(callback, 1);
        }
    }

    /**
     * Measure performance
     */
    measure(name: string, startMark: string, endMark: string): number {
        if (!('performance' in window)) return 0;

        try {
            performance.measure(name, startMark, endMark);
            const measure = performance.getEntriesByName(name)[0];
            return measure.duration;
        } catch (error) {
            console.warn('Performance measurement failed:', error);
            return 0;
        }
    }

    /**
     * Get Web Vitals
     */
    async getWebVitals(): Promise<{
        FCP?: number;
        LCP?: number;
        FID?: number;
        CLS?: number;
        TTFB?: number;
    }> {
        const vitals: any = {};

        if (!('performance' in window)) return vitals;

        // TTFB (Time to First Byte)
        const navigationTiming = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
        if (navigationTiming) {
            vitals.TTFB = navigationTiming.responseStart - navigationTiming.requestStart;
        }

        // FCP (First Contentful Paint)
        const paintEntries = performance.getEntriesByType('paint');
        const fcpEntry = paintEntries.find(entry => entry.name === 'first-contentful-paint');
        if (fcpEntry) {
            vitals.FCP = fcpEntry.startTime;
        }

        return vitals;
    }

    /**
     * Optimize bundle size
     */
    async loadChunk(chunkName: string): Promise<any> {
        try {
            const module = await import(/* webpackChunkName: "[request]" */ `@/chunks/${chunkName}`);
            return module.default;
        } catch (error) {
            console.error(`Failed to load chunk: ${chunkName}`, error);
            throw error;
        }
    }

    private loadAllImages(selector: string): void {
        document.querySelectorAll(selector).forEach(img => {
            const src = img.getAttribute('data-src');
            if (src) {
                (img as HTMLImageElement).src = src;
                img.removeAttribute('data-src');
            }
        });
    }
}

export const performanceOptimizer = new PerformanceOptimizer();

/**
 * React hook for performance monitoring
 */
import { useEffect, useState } from 'react';

export function usePerformanceMetrics() {
    const [metrics, setMetrics] = useState<any>({});

    useEffect(() => {
        performanceOptimizer.getWebVitals().then(vitals => {
            setMetrics(vitals);
        });
    }, []);

    return metrics;
}
