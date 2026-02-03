/**
 * UPDATE #25: Watch History Tracker
 * Track and display watched movies
 */

import { useState, useEffect, useCallback } from 'react';

interface WatchHistoryItem {
    movieId: number;
    title: string;
    watchedAt: Date;
    watchCount: number;
}

const HISTORY_STORAGE_KEY = 'movieshows_watch_history';
const MAX_HISTORY_ITEMS = 100;

export function useWatchHistory() {
    const [history, setHistory] = useState<WatchHistoryItem[]>([]);

    // Load from localStorage
    useEffect(() => {
        const stored = localStorage.getItem(HISTORY_STORAGE_KEY);
        if (stored) {
            try {
                const parsed = JSON.parse(stored);
                setHistory(parsed.map((item: any) => ({
                    ...item,
                    watchedAt: new Date(item.watchedAt)
                })));
            } catch (error) {
                console.error('Failed to parse watch history:', error);
            }
        }
    }, []);

    // Save to localStorage
    useEffect(() => {
        localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
    }, [history]);

    const addToHistory = useCallback((movieId: number, title: string) => {
        setHistory(prev => {
            const existing = prev.find(item => item.movieId === movieId);

            if (existing) {
                // Update existing entry
                return prev.map(item =>
                    item.movieId === movieId
                        ? { ...item, watchedAt: new Date(), watchCount: item.watchCount + 1 }
                        : item
                ).sort((a, b) => b.watchedAt.getTime() - a.watchedAt.getTime());
            } else {
                // Add new entry
                const newHistory = [
                    { movieId, title, watchedAt: new Date(), watchCount: 1 },
                    ...prev
                ];

                // Keep only last MAX_HISTORY_ITEMS
                return newHistory.slice(0, MAX_HISTORY_ITEMS);
            }
        });
    }, []);

    const clearHistory = useCallback(() => {
        if (confirm('Clear all watch history?')) {
            setHistory([]);
        }
    }, []);

    const removeFromHistory = useCallback((movieId: number) => {
        setHistory(prev => prev.filter(item => item.movieId !== movieId));
    }, []);

    const hasWatched = useCallback((movieId: number) => {
        return history.some(item => item.movieId === movieId);
    }, [history]);

    return {
        history,
        addToHistory,
        clearHistory,
        removeFromHistory,
        hasWatched
    };
}
