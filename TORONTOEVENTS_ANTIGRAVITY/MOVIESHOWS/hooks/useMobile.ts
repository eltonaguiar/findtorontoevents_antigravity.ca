/**
 * UPDATE #38: Mobile Responsiveness Hook
 * Detect mobile devices and provide touch utilities
 */

import { useState, useEffect } from 'react';

interface MobileDetection {
    isMobile: boolean;
    isTablet: boolean;
    isDesktop: boolean;
    isTouchDevice: boolean;
    screenWidth: number;
    screenHeight: number;
}

export function useMobileDetection(): MobileDetection {
    const [detection, setDetection] = useState<MobileDetection>({
        isMobile: false,
        isTablet: false,
        isDesktop: true,
        isTouchDevice: false,
        screenWidth: typeof window !== 'undefined' ? window.innerWidth : 1920,
        screenHeight: typeof window !== 'undefined' ? window.innerHeight : 1080
    });

    useEffect(() => {
        const checkDevice = () => {
            const width = window.innerWidth;
            const height = window.innerHeight;
            const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

            setDetection({
                isMobile: width < 768,
                isTablet: width >= 768 && width < 1024,
                isDesktop: width >= 1024,
                isTouchDevice,
                screenWidth: width,
                screenHeight: height
            });
        };

        checkDevice();
        window.addEventListener('resize', checkDevice);
        window.addEventListener('orientationchange', checkDevice);

        return () => {
            window.removeEventListener('resize', checkDevice);
            window.removeEventListener('orientationchange', checkDevice);
        };
    }, []);

    return detection;
}

/**
 * UPDATE #38: Touch Gesture Hook
 * Handle swipe gestures for mobile
 */

interface SwipeHandlers {
    onSwipeLeft?: () => void;
    onSwipeRight?: () => void;
    onSwipeUp?: () => void;
    onSwipeDown?: () => void;
}

export function useSwipeGesture(handlers: SwipeHandlers, threshold: number = 50) {
    useEffect(() => {
        let touchStartX = 0;
        let touchStartY = 0;
        let touchEndX = 0;
        let touchEndY = 0;

        const handleTouchStart = (e: TouchEvent) => {
            touchStartX = e.changedTouches[0].screenX;
            touchStartY = e.changedTouches[0].screenY;
        };

        const handleTouchEnd = (e: TouchEvent) => {
            touchEndX = e.changedTouches[0].screenX;
            touchEndY = e.changedTouches[0].screenY;
            handleSwipe();
        };

        const handleSwipe = () => {
            const deltaX = touchEndX - touchStartX;
            const deltaY = touchEndY - touchStartY;

            if (Math.abs(deltaX) > Math.abs(deltaY)) {
                // Horizontal swipe
                if (Math.abs(deltaX) > threshold) {
                    if (deltaX > 0) {
                        handlers.onSwipeRight?.();
                    } else {
                        handlers.onSwipeLeft?.();
                    }
                }
            } else {
                // Vertical swipe
                if (Math.abs(deltaY) > threshold) {
                    if (deltaY > 0) {
                        handlers.onSwipeDown?.();
                    } else {
                        handlers.onSwipeUp?.();
                    }
                }
            }
        };

        document.addEventListener('touchstart', handleTouchStart);
        document.addEventListener('touchend', handleTouchEnd);

        return () => {
            document.removeEventListener('touchstart', handleTouchStart);
            document.removeEventListener('touchend', handleTouchEnd);
        };
    }, [handlers, threshold]);
}
