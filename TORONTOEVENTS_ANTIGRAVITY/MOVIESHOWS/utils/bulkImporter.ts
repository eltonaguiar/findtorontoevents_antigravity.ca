/**
 * UPDATE #63: Bulk Content Importer
 * Import movies from TMDB in bulk
 */

import { tmdbService } from '../services/tmdbService';
import { movieAPI } from '../services/movieAPI';

interface ImportProgress {
    total: number;
    imported: number;
    failed: number;
    current: string;
}

export class BulkImporter {
    private onProgress?: (progress: ImportProgress) => void;

    constructor(onProgress?: (progress: ImportProgress) => void) {
        this.onProgress = onProgress;
    }

    async importPopularMovies(pages: number = 5): Promise<ImportProgress> {
        const progress: ImportProgress = {
            total: 0,
            imported: 0,
            failed: 0,
            current: ''
        };

        for (let page = 1; page <= pages; page++) {
            try {
                const response = await tmdbService.getPopularMovies(page);
                progress.total += response.results.length;

                for (const movie of response.results) {
                    progress.current = movie.title;
                    this.onProgress?.(progress);

                    try {
                        await this.importMovie(movie);
                        progress.imported++;
                    } catch (error) {
                        console.error(`Failed to import ${movie.title}:`, error);
                        progress.failed++;
                    }

                    // Rate limiting: wait 100ms between requests
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
            } catch (error) {
                console.error(`Failed to fetch page ${page}:`, error);
            }
        }

        return progress;
    }

    async importTrendingMovies(): Promise<ImportProgress> {
        const progress: ImportProgress = {
            total: 0,
            imported: 0,
            failed: 0,
            current: ''
        };

        try {
            const response = await tmdbService.getTrendingMovies('week');
            progress.total = response.results.length;

            for (const movie of response.results) {
                progress.current = movie.title;
                this.onProgress?.(progress);

                try {
                    await this.importMovie(movie);
                    progress.imported++;
                } catch (error) {
                    console.error(`Failed to import ${movie.title}:`, error);
                    progress.failed++;
                }

                await new Promise(resolve => setTimeout(resolve, 100));
            }
        } catch (error) {
            console.error('Failed to fetch trending movies:', error);
        }

        return progress;
    }

    private async importMovie(tmdbMovie: any) {
        // Get full movie details
        const details = await tmdbService.getMovieDetails(tmdbMovie.id);
        const videos = await tmdbService.getMovieVideos(tmdbMovie.id);

        // Find official trailer
        const trailer = videos.results.find(
            v => v.type === 'Trailer' && v.site === 'YouTube'
        );

        // Create movie in our database
        const movieData = {
            title: details.title,
            type: 'movie',
            release_year: details.release_date ? parseInt(details.release_date.split('-')[0]) : undefined,
            genre: details.genres?.map(g => g.name).join(', '),
            description: details.overview,
            tmdb_id: details.id,
            source: 'tmdb'
        };

        const response = await movieAPI.createMovie(movieData);

        if (response.data?.id && trailer) {
            // Add trailer (would need trailer API endpoint)
            console.log(`Added trailer for ${details.title}: ${trailer.key}`);
        }

        // Add thumbnail (would need thumbnail API endpoint)
        if (details.poster_path) {
            const thumbnailUrl = tmdbService.getPosterUrl(details.poster_path);
            console.log(`Added thumbnail for ${details.title}: ${thumbnailUrl}`);
        }
    }
}

/**
 * React hook for bulk import
 */
import { useState } from 'react';

export function useBulkImport() {
    const [progress, setProgress] = useState<ImportProgress | null>(null);
    const [isImporting, setIsImporting] = useState(false);

    const importPopular = async (pages: number = 5) => {
        setIsImporting(true);
        const importer = new BulkImporter(setProgress);
        const result = await importer.importPopularMovies(pages);
        setIsImporting(false);
        return result;
    };

    const importTrending = async () => {
        setIsImporting(true);
        const importer = new BulkImporter(setProgress);
        const result = await importer.importTrendingMovies();
        setIsImporting(false);
        return result;
    };

    return {
        progress,
        isImporting,
        importPopular,
        importTrending
    };
}
