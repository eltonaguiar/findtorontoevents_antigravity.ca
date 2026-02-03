/**
 * UPDATE #39: Performance Monitoring
 * Track Web Vitals and performance metrics
 */

interface PerformanceMetrics {
    lcp?: number; // Largest Contentful Paint
    fid?: number; // First Input Delay
    cls?: number; // Cumulative Layout Shift
    fcp?: number; // First Contentful Paint
    ttfb?: number; // Time to First Byte
}

export class PerformanceMonitor {
    private metrics: PerformanceMetrics = {};

    constructor() {
        this.initializeMonitoring();
    }

    private initializeMonitoring() {
        // Monitor LCP
        if ('PerformanceObserver' in window) {
            try {
                const lcpObserver = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    const lastEntry = entries[entries.length - 1] as any;
                    this.metrics.lcp = lastEntry.renderTime || lastEntry.loadTime;
                    this.reportMetric('LCP', this.metrics.lcp);
                });
                lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
            } catch (e) {
                console.warn('LCP monitoring not supported');
            }

            // Monitor FID
            try {
                const fidObserver = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    entries.forEach((entry: any) => {
                        this.metrics.fid = entry.processingStart - entry.startTime;
                        this.reportMetric('FID', this.metrics.fid);
                    });
                });
                fidObserver.observe({ entryTypes: ['first-input'] });
            } catch (e) {
                console.warn('FID monitoring not supported');
            }

            // Monitor CLS
            try {
                let clsValue = 0;
                const clsObserver = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    entries.forEach((entry: any) => {
                        if (!entry.hadRecentInput) {
                            clsValue += entry.value;
                            this.metrics.cls = clsValue;
                            this.reportMetric('CLS', this.metrics.cls);
                        }
                    });
                });
                clsObserver.observe({ entryTypes: ['layout-shift'] });
            } catch (e) {
                console.warn('CLS monitoring not supported');
            }
        }

        // Monitor page load metrics
        window.addEventListener('load', () => {
            setTimeout(() => {
                const perfData = performance.getEntriesByType('navigation')[0] as any;
                if (perfData) {
                    this.metrics.fcp = perfData.responseStart - perfData.fetchStart;
                    this.metrics.ttfb = perfData.responseStart - perfData.requestStart;

                    this.reportMetric('FCP', this.metrics.fcp);
                    this.reportMetric('TTFB', this.metrics.ttfb);
                }
            }, 0);
        });
    }

    private reportMetric(name: string, value: number) {
        console.log(`[Performance] ${name}: ${value.toFixed(2)}ms`);

        // Send to analytics if available
        if (typeof window !== 'undefined' && (window as any).gtag) {
            (window as any).gtag('event', 'web_vitals', {
                event_category: 'Web Vitals',
                event_label: name,
                value: Math.round(value),
                non_interaction: true
            });
        }
    }

    getMetrics(): PerformanceMetrics {
        return { ...this.metrics };
    }
}

// Initialize global performance monitor
export const performanceMonitor = new PerformanceMonitor();
