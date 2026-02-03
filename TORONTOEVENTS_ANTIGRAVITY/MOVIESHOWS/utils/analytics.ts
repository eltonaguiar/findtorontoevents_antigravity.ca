/**
 * UPDATE #50: Analytics Integration
 * Track user interactions and page views
 */

interface AnalyticsEvent {
    category: string;
    action: string;
    label?: string;
    value?: number;
}

class Analytics {
    private isInitialized = false;

    initialize(trackingId: string) {
        if (this.isInitialized) return;

        // Google Analytics 4
        const script = document.createElement('script');
        script.async = true;
        script.src = `https://www.googletagmanager.com/gtag/js?id=${trackingId}`;
        document.head.appendChild(script);

        (window as any).dataLayer = (window as any).dataLayer || [];
        function gtag(...args: any[]) {
            (window as any).dataLayer.push(args);
        }
        (window as any).gtag = gtag;

        gtag('js', new Date());
        gtag('config', trackingId);

        this.isInitialized = true;
    }

    pageView(path: string, title?: string) {
        if (typeof (window as any).gtag === 'function') {
            (window as any).gtag('event', 'page_view', {
                page_path: path,
                page_title: title
            });
        }
    }

    event({ category, action, label, value }: AnalyticsEvent) {
        if (typeof (window as any).gtag === 'function') {
            (window as any).gtag('event', action, {
                event_category: category,
                event_label: label,
                value: value
            });
        }
    }

    // Convenience methods
    trackMovieView(movieId: number, title: string) {
        this.event({
            category: 'Movie',
            action: 'view',
            label: title,
            value: movieId
        });
    }

    trackTrailerPlay(movieId: number, title: string) {
        this.event({
            category: 'Trailer',
            action: 'play',
            label: title,
            value: movieId
        });
    }

    trackSearch(query: string) {
        this.event({
            category: 'Search',
            action: 'query',
            label: query
        });
    }

    trackQueueAdd(movieId: number, title: string) {
        this.event({
            category: 'Queue',
            action: 'add',
            label: title,
            value: movieId
        });
    }

    trackShare(platform: string, movieId: number) {
        this.event({
            category: 'Share',
            action: platform,
            value: movieId
        });
    }

    trackRating(movieId: number, rating: number) {
        this.event({
            category: 'Rating',
            action: 'submit',
            value: rating
        });
    }
}

export const analytics = new Analytics();

// React hook for analytics
import { useEffect } from 'react';

export function useAnalytics(trackingId?: string) {
    useEffect(() => {
        if (trackingId) {
            analytics.initialize(trackingId);
        }
    }, [trackingId]);

    return analytics;
}

/**
 * Example usage:
 * 
 * // In App.tsx
 * useAnalytics('G-XXXXXXXXXX');
 * 
 * // Track events
 * analytics.trackMovieView(123, 'Dune: Part Two');
 * analytics.trackSearch('action movies');
 * analytics.trackQueueAdd(456, 'Inception');
 */
