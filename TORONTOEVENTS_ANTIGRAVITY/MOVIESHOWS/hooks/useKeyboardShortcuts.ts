/**
 * UPDATE #24: Keyboard Shortcuts Hook
 * Add keyboard navigation support
 */

import { useEffect, useCallback } from 'react';

interface KeyboardShortcuts {
    [key: string]: () => void;
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcuts, enabled: boolean = true) {
    const handleKeyPress = useCallback((event: KeyboardEvent) => {
        if (!enabled) return;

        // Don't trigger if user is typing in an input
        if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
            return;
        }

        const key = event.key.toLowerCase();
        const handler = shortcuts[key];

        if (handler) {
            event.preventDefault();
            handler();
        }
    }, [shortcuts, enabled]);

    useEffect(() => {
        window.addEventListener('keydown', handleKeyPress);
        return () => window.removeEventListener('keydown', handleKeyPress);
    }, [handleKeyPress]);
}

// Common shortcuts helper
export const commonShortcuts = {
    search: '/',
    escape: 'escape',
    enter: 'enter',
    arrowUp: 'arrowup',
    arrowDown: 'arrowdown',
    arrowLeft: 'arrowleft',
    arrowRight: 'arrowright',
    space: ' ',
};

/**
 * Example usage:
 * 
 * useKeyboardShortcuts({
 *   '/': () => focusSearch(),
 *   'escape': () => closeModal(),
 *   'arrowup': () => scrollUp(),
 *   'arrowdown': () => scrollDown(),
 * });
 */
