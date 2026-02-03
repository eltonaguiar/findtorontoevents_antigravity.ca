/**
 * UPDATE #61: TMDB API Integration
 * Fetch movie data from The Movie Database
 */

const TMDB_API_KEY = 'YOUR_API_KEY'; // User should add their key
const TMDB_BASE_URL = 'https://api.themoviedb.org/3';
const TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p';

interface TMDBMovie {
    id: number;
    title: string;
    overview: string;
    release_date: string;
    poster_path: string;
    backdrop_path: string;
    vote_average: number;
    genre_ids: number[];
}

class TMDBService {
    private apiKey: string;

    constructor(apiKey: string = TMDB_API_KEY) {
        this.apiKey = apiKey;
    }

    private async request<T>(endpoint: string, params: Record<string, string> = {}): Promise<T> {
        const url = new URL(`${TMDB_BASE_URL}${endpoint}`);
        url.searchParams.set('api_key', this.apiKey);

        Object.entries(params).forEach(([key, value]) => {
            url.searchParams.set(key, value);
        });

        const response = await fetch(url.toString());
        if (!response.ok) {
            throw new Error(`TMDB API error: ${response.statusText}`);
        }

        return response.json();
    }

    async searchMovies(query: string, page: number = 1) {
        return this.request<{ results: TMDBMovie[]; total_pages: number }>(
            '/search/movie',
            { query, page: page.toString() }
        );
    }

    async getPopularMovies(page: number = 1) {
        return this.request<{ results: TMDBMovie[]; total_pages: number }>(
            '/movie/popular',
            { page: page.toString() }
        );
    }

    async getTrendingMovies(timeWindow: 'day' | 'week' = 'week') {
        return this.request<{ results: TMDBMovie[] }>(
            `/trending/movie/${timeWindow}`
        );
    }

    async getMovieDetails(movieId: number) {
        return this.request<TMDBMovie & { genres: Array<{ id: number; name: string }> }>(
            `/movie/${movieId}`
        );
    }

    async getMovieVideos(movieId: number) {
        return this.request<{ results: Array<{ key: string; type: string; site: string }> }>(
            `/movie/${movieId}/videos`
        );
    }

    getImageUrl(path: string, size: 'w500' | 'w780' | 'original' = 'w500') {
        return `${TMDB_IMAGE_BASE}/${size}${path}`;
    }

    getPosterUrl(path: string) {
        return this.getImageUrl(path, 'w500');
    }

    getBackdropUrl(path: string) {
        return this.getImageUrl(path, 'w780');
    }
}

export const tmdbService = new TMDBService();

/**
 * React hook for TMDB
 */
import { useState, useCallback } from 'react';

export function useTMDB() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const execute = useCallback(async <T,>(
        apiCall: () => Promise<T>
    ): Promise<T | null> => {
        setLoading(true);
        setError(null);

        try {
            const result = await apiCall();
            setLoading(false);
            return result;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'TMDB API error');
            setLoading(false);
            return null;
        }
    }, []);

    return { execute, loading, error };
}
