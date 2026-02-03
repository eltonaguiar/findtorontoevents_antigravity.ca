/**
 * UPDATE #53: API Service Layer
 * Centralized API calls with error handling
 */

const API_BASE = '/MOVIESHOWS/api';

interface Movie {
    id: number;
    title: string;
    type?: string;
    release_year?: number;
    genre?: string;
    description?: string;
    tmdb_id?: number;
    imdb_id?: string;
    source?: string;
}

interface ApiResponse<T> {
    data?: T;
    error?: string;
    status: number;
}

class MovieAPI {
    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<ApiResponse<T>> {
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });

            const data = await response.json();

            if (!response.ok) {
                return {
                    error: data.error || 'Request failed',
                    status: response.status
                };
            }

            return {
                data,
                status: response.status
            };
        } catch (error) {
            return {
                error: error instanceof Error ? error.message : 'Network error',
                status: 0
            };
        }
    }

    async getMovies(params?: {
        limit?: number;
        offset?: number;
        type?: string;
        genre?: string;
        year?: number;
    }): Promise<ApiResponse<{ movies: Movie[]; count: number }>> {
        const queryParams = new URLSearchParams();
        if (params?.limit) queryParams.set('limit', params.limit.toString());
        if (params?.offset) queryParams.set('offset', params.offset.toString());
        if (params?.type) queryParams.set('type', params.type);
        if (params?.genre) queryParams.set('genre', params.genre);
        if (params?.year) queryParams.set('year', params.year.toString());

        const query = queryParams.toString();
        return this.request(`/movies.php${query ? `?${query}` : ''}`);
    }

    async getMovie(id: number): Promise<ApiResponse<Movie>> {
        return this.request(`/movies.php?id=${id}`);
    }

    async createMovie(movie: Partial<Movie>): Promise<ApiResponse<{ id: number; message: string }>> {
        return this.request('/movies.php', {
            method: 'POST',
            body: JSON.stringify(movie)
        });
    }

    async updateMovie(id: number, movie: Partial<Movie>): Promise<ApiResponse<{ message: string }>> {
        return this.request(`/movies.php?id=${id}`, {
            method: 'PUT',
            body: JSON.stringify(movie)
        });
    }

    async deleteMovie(id: number): Promise<ApiResponse<{ message: string }>> {
        return this.request(`/movies.php?id=${id}`, {
            method: 'DELETE'
        });
    }

    async searchMovies(query: string): Promise<ApiResponse<{ movies: Movie[]; count: number }>> {
        return this.request(`/movies.php?search=${encodeURIComponent(query)}`);
    }
}

export const movieAPI = new MovieAPI();

/**
 * React hook for API calls
 */
import { useState, useCallback } from 'react';

export function useMovieAPI() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const execute = useCallback(async <T,>(
        apiCall: () => Promise<ApiResponse<T>>
    ): Promise<T | null> => {
        setLoading(true);
        setError(null);

        const response = await apiCall();

        setLoading(false);

        if (response.error) {
            setError(response.error);
            return null;
        }

        return response.data || null;
    }, []);

    return { execute, loading, error };
}
