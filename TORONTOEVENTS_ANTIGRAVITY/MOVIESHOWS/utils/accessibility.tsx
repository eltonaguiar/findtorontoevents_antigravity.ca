/**
 * UPDATE #89: Accessibility Improvements
 * WCAG 2.1 AA compliance utilities
 */

/**
 * Skip to main content link
 */
import React from 'react';

export function SkipToMain() {
    return (
        <a href="#main-content" className="skip-to-main">
            Skip to main content
        </a>
    );
}

/**
 * Screen reader only text
 */
export function ScreenReaderOnly({ children }: { children: React.ReactNode }) {
    return <span className="sr-only">{children}</span>;
}

/**
 * Focus trap for modals
 */
export function useFocusTrap(ref: React.RefObject<HTMLElement>) {
    React.useEffect(() => {
        if (!ref.current) return;

        const element = ref.current;
        const focusableElements = element.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );

        const firstElement = focusableElements[0] as HTMLElement;
        const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

        const handleTab = (e: KeyboardEvent) => {
            if (e.key !== 'Tab') return;

            if (e.shiftKey) {
                if (document.activeElement === firstElement) {
                    lastElement?.focus();
                    e.preventDefault();
                }
            } else {
                if (document.activeElement === lastElement) {
                    firstElement?.focus();
                    e.preventDefault();
                }
            }
        };

        element.addEventListener('keydown', handleTab);
        firstElement?.focus();

        return () => {
            element.removeEventListener('keydown', handleTab);
        };
    }, [ref]);
}

/**
 * Announce to screen readers
 */
export function announce(message: string, priority: 'polite' | 'assertive' = 'polite'): void {
    const announcer = document.getElementById('aria-live-announcer');
    if (announcer) {
        announcer.setAttribute('aria-live', priority);
        announcer.textContent = message;

        // Clear after announcement
        setTimeout(() => {
            announcer.textContent = '';
        }, 1000);
    }
}

/**
 * Live region component
 */
export function LiveRegion() {
    return (
        <div
            id="aria-live-announcer"
            className="sr-only"
            aria-live="polite"
            aria-atomic="true"
        />
    );
}

/**
 * Keyboard navigation hook
 */
export function useKeyboardNav(
    items: any[],
    onSelect: (index: number) => void
) {
    const [focusedIndex, setFocusedIndex] = React.useState(0);

    const handleKeyDown = React.useCallback((e: React.KeyboardEvent) => {
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                setFocusedIndex(prev => Math.min(prev + 1, items.length - 1));
                break;
            case 'ArrowUp':
                e.preventDefault();
                setFocusedIndex(prev => Math.max(prev - 1, 0));
                break;
            case 'Enter':
            case ' ':
                e.preventDefault();
                onSelect(focusedIndex);
                break;
            case 'Home':
                e.preventDefault();
                setFocusedIndex(0);
                break;
            case 'End':
                e.preventDefault();
                setFocusedIndex(items.length - 1);
                break;
        }
    }, [focusedIndex, items.length, onSelect]);

    return { focusedIndex, handleKeyDown };
}

/**
 * Color contrast checker
 */
export function checkContrast(foreground: string, background: string): {
    ratio: number;
    passesAA: boolean;
    passesAAA: boolean;
} {
    const fgLuminance = getLuminance(foreground);
    const bgLuminance = getLuminance(background);

    const ratio = (Math.max(fgLuminance, bgLuminance) + 0.05) /
        (Math.min(fgLuminance, bgLuminance) + 0.05);

    return {
        ratio,
        passesAA: ratio >= 4.5,
        passesAAA: ratio >= 7
    };
}

function getLuminance(color: string): number {
    // Simplified luminance calculation
    const rgb = hexToRgb(color);
    if (!rgb) return 0;

    const [r, g, b] = [rgb.r, rgb.g, rgb.b].map(val => {
        val = val / 255;
        return val <= 0.03928 ? val / 12.92 : Math.pow((val + 0.055) / 1.055, 2.4);
    });

    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}

const styles = `
.skip-to-main {
  position: absolute;
  left: -9999px;
  z-index: 999;
  padding: 1rem;
  background: #667eea;
  color: white;
  text-decoration: none;
  font-weight: 600;
}

.skip-to-main:focus {
  left: 50%;
  transform: translateX(-50%);
  top: 1rem;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
`;
