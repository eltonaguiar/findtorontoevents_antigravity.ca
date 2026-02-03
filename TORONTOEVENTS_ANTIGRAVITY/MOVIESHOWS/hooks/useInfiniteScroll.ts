/**
 * UPDATE #49: Infinite Scroll Hook
 * Load more content as user scrolls
 */

import { useState, useEffect, useCallback, useRef } from 'react';

interface InfiniteScrollOptions {
    threshold?: number;
    rootMargin?: string;
}

export function useInfiniteScroll(
    callback: () => void | Promise<void>,
    hasMore: boolean,
    options: InfiniteScrollOptions = {}
) {
    const { threshold = 0.5, rootMargin = '100px' } = options;
    const [isLoading, setIsLoading] = useState(false);
    const observerRef = useRef<IntersectionObserver | null>(null);
    const loadMoreRef = useRef<HTMLDivElement | null>(null);

    const handleObserver = useCallback(
        async (entries: IntersectionObserverEntry[]) => {
            const target = entries[0];
            if (target.isIntersecting && hasMore && !isLoading) {
                setIsLoading(true);
                try {
                    await callback();
                } finally {
                    setIsLoading(false);
                }
            }
        },
        [callback, hasMore, isLoading]
    );

    useEffect(() => {
        const element = loadMoreRef.current;
        if (!element) return;

        observerRef.current = new IntersectionObserver(handleObserver, {
            threshold,
            rootMargin
        });

        observerRef.current.observe(element);

        return () => {
            if (observerRef.current) {
                observerRef.current.disconnect();
            }
        };
    }, [handleObserver, threshold, rootMargin]);

    return { loadMoreRef, isLoading };
}

/**
 * Example usage:
 * 
 * const [movies, setMovies] = useState([]);
 * const [page, setPage] = useState(1);
 * const [hasMore, setHasMore] = useState(true);
 * 
 * const loadMore = async () => {
 *   const newMovies = await fetchMovies(page);
 *   setMovies(prev => [...prev, ...newMovies]);
 *   setPage(prev => prev + 1);
 *   setHasMore(newMovies.length > 0);
 * };
 * 
 * const { loadMoreRef, isLoading } = useInfiniteScroll(loadMore, hasMore);
 * 
 * return (
 *   <>
 *     {movies.map(movie => <MovieCard key={movie.id} {...movie} />)}
 *     <div ref={loadMoreRef}>{isLoading && 'Loading...'}</div>
 *   </>
 * );
 */
