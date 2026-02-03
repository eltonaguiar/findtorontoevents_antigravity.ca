/**
 * UPDATE #48: Favorites/Watchlist Hook
 * Manage user's favorite movies
 */

import { useState, useEffect, useCallback } from 'react';

interface Movie {
    id: number;
    title: string;
    type?: string;
    release_year?: number;
}

const FAVORITES_KEY = 'movieshows_favorites';

export function useFavorites() {
    const [favorites, setFavorites] = useState<Movie[]>([]);

    // Load from localStorage
    useEffect(() => {
        const stored = localStorage.getItem(FAVORITES_KEY);
        if (stored) {
            try {
                setFavorites(JSON.parse(stored));
            } catch (error) {
                console.error('Failed to parse favorites:', error);
            }
        }
    }, []);

    // Save to localStorage
    useEffect(() => {
        localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
    }, [favorites]);

    const addFavorite = useCallback((movie: Movie) => {
        setFavorites(prev => {
            if (prev.some(m => m.id === movie.id)) {
                return prev; // Already in favorites
            }
            return [...prev, movie];
        });
    }, []);

    const removeFavorite = useCallback((movieId: number) => {
        setFavorites(prev => prev.filter(m => m.id !== movieId));
    }, []);

    const toggleFavorite = useCallback((movie: Movie) => {
        setFavorites(prev => {
            const exists = prev.some(m => m.id === movie.id);
            if (exists) {
                return prev.filter(m => m.id !== movie.id);
            } else {
                return [...prev, movie];
            }
        });
    }, []);

    const isFavorite = useCallback((movieId: number) => {
        return favorites.some(m => m.id === movieId);
    }, [favorites]);

    const clearFavorites = useCallback(() => {
        if (confirm('Clear all favorites?')) {
            setFavorites([]);
        }
    }, []);

    return {
        favorites,
        addFavorite,
        removeFavorite,
        toggleFavorite,
        isFavorite,
        clearFavorites,
        count: favorites.length
    };
}
