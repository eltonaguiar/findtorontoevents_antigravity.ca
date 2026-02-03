/**
 * UPDATE #73: Recommendations Engine
 * Generate personalized movie recommendations
 */

interface Movie {
    id: number;
    title: string;
    genre?: string;
    release_year?: number;
    rating?: number;
    [key: string]: any;
}

interface UserPreferences {
    favoriteGenres: string[];
    watchedMovies: number[];
    ratedMovies: Map<number, number>;
    queuedMovies: number[];
}

export class RecommendationsEngine {
    /**
     * Get personalized recommendations based on user preferences
     */
    getRecommendations(
        allMovies: Movie[],
        userPreferences: UserPreferences,
        limit: number = 10
    ): Movie[] {
        const scores = new Map<number, number>();

        allMovies.forEach(movie => {
            // Skip already watched movies
            if (userPreferences.watchedMovies.includes(movie.id)) {
                return;
            }

            let score = 0;

            // Genre matching (highest weight)
            if (movie.genre) {
                const movieGenres = movie.genre.split(',').map(g => g.trim());
                const genreMatches = movieGenres.filter(g =>
                    userPreferences.favoriteGenres.includes(g)
                ).length;
                score += genreMatches * 10;
            }

            // Rating boost
            if (movie.rating) {
                score += movie.rating * 2;
            }

            // Recency boost (newer movies get slight preference)
            if (movie.release_year) {
                const yearScore = Math.max(0, (movie.release_year - 2000) / 10);
                score += yearScore;
            }

            // Similar to highly rated movies
            const similarityScore = this.calculateSimilarityScore(
                movie,
                allMovies,
                userPreferences.ratedMovies
            );
            score += similarityScore * 5;

            scores.set(movie.id, score);
        });

        // Sort by score and return top N
        return allMovies
            .filter(m => scores.has(m.id))
            .sort((a, b) => (scores.get(b.id) || 0) - (scores.get(a.id) || 0))
            .slice(0, limit);
    }

    /**
     * Get similar movies based on a specific movie
     */
    getSimilarMovies(
        targetMovie: Movie,
        allMovies: Movie[],
        limit: number = 5
    ): Movie[] {
        const scores = new Map<number, number>();

        allMovies.forEach(movie => {
            if (movie.id === targetMovie.id) return;

            let score = 0;

            // Genre similarity
            if (targetMovie.genre && movie.genre) {
                const targetGenres = targetMovie.genre.split(',').map(g => g.trim());
                const movieGenres = movie.genre.split(',').map(g => g.trim());
                const commonGenres = targetGenres.filter(g => movieGenres.includes(g));
                score += commonGenres.length * 10;
            }

            // Year proximity
            if (targetMovie.release_year && movie.release_year) {
                const yearDiff = Math.abs(targetMovie.release_year - movie.release_year);
                score += Math.max(0, 10 - yearDiff);
            }

            // Rating similarity
            if (targetMovie.rating && movie.rating) {
                const ratingDiff = Math.abs(targetMovie.rating - movie.rating);
                score += Math.max(0, 5 - ratingDiff);
            }

            scores.set(movie.id, score);
        });

        return allMovies
            .filter(m => scores.has(m.id))
            .sort((a, b) => (scores.get(b.id) || 0) - (scores.get(a.id) || 0))
            .slice(0, limit);
    }

    /**
     * Get trending recommendations
     */
    getTrendingRecommendations(
        allMovies: Movie[],
        limit: number = 10
    ): Movie[] {
        return allMovies
            .filter(m => m.rating && m.rating >= 7)
            .sort((a, b) => {
                // Combine rating and recency
                const scoreA = (a.rating || 0) + (a.release_year || 0) / 1000;
                const scoreB = (b.rating || 0) + (b.release_year || 0) / 1000;
                return scoreB - scoreA;
            })
            .slice(0, limit);
    }

    private calculateSimilarityScore(
        movie: Movie,
        allMovies: Movie[],
        ratedMovies: Map<number, number>
    ): number {
        let totalSimilarity = 0;
        let count = 0;

        ratedMovies.forEach((rating, movieId) => {
            if (rating >= 4) { // Only consider highly rated movies
                const ratedMovie = allMovies.find(m => m.id === movieId);
                if (ratedMovie && ratedMovie.genre && movie.genre) {
                    const ratedGenres = ratedMovie.genre.split(',').map(g => g.trim());
                    const movieGenres = movie.genre.split(',').map(g => g.trim());
                    const commonGenres = ratedGenres.filter(g => movieGenres.includes(g));

                    if (commonGenres.length > 0) {
                        totalSimilarity += commonGenres.length;
                        count++;
                    }
                }
            }
        });

        return count > 0 ? totalSimilarity / count : 0;
    }
}

export const recommendationsEngine = new RecommendationsEngine();

/**
 * React hook for recommendations
 */
import { useState, useEffect } from 'react';

export function useRecommendations(
    allMovies: Movie[],
    userPreferences: UserPreferences
) {
    const [recommendations, setRecommendations] = useState<Movie[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setLoading(true);

        // Simulate async processing
        setTimeout(() => {
            const recs = recommendationsEngine.getRecommendations(
                allMovies,
                userPreferences,
                10
            );
            setRecommendations(recs);
            setLoading(false);
        }, 500);
    }, [allMovies, userPreferences]);

    return { recommendations, loading };
}
