/**
 * UPDATE #15: useQueue Hook
 * React hook for queue state management
 */

import { useState, useEffect, useCallback } from 'react';

interface Movie {
    id: number;
    title: string;
    [key: string]: any;
}

interface UseQueueResult {
    queue: Movie[];
    addToQueue: (movie: Movie) => void;
    removeFromQueue: (movieId: number) => void;
    reorderQueue: (fromIndex: number, toIndex: number) => void;
    clearQueue: () => void;
    isInQueue: (movieId: number) => boolean;
    syncToServer: () => Promise<void>;
}

const QUEUE_STORAGE_KEY = 'movieshows_queue';

export function useQueue(userId?: number): UseQueueResult {
    const [queue, setQueue] = useState<Movie[]>([]);

    // Load queue from localStorage on mount
    useEffect(() => {
        const stored = localStorage.getItem(QUEUE_STORAGE_KEY);
        if (stored) {
            try {
                setQueue(JSON.parse(stored));
            } catch (error) {
                console.error('Failed to parse queue from localStorage:', error);
            }
        }
    }, []);

    // Save queue to localStorage whenever it changes
    useEffect(() => {
        localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(queue));
    }, [queue]);

    const addToQueue = useCallback((movie: Movie) => {
        setQueue(prev => {
            if (prev.some(m => m.id === movie.id)) {
                return prev; // Already in queue
            }
            return [...prev, movie];
        });
    }, []);

    const removeFromQueue = useCallback((movieId: number) => {
        setQueue(prev => prev.filter(m => m.id !== movieId));
    }, []);

    const reorderQueue = useCallback((fromIndex: number, toIndex: number) => {
        setQueue(prev => {
            const newQueue = [...prev];
            const [removed] = newQueue.splice(fromIndex, 1);
            newQueue.splice(toIndex, 0, removed);
            return newQueue;
        });
    }, []);

    const clearQueue = useCallback(() => {
        if (confirm('Are you sure you want to clear your entire queue?')) {
            setQueue([]);
        }
    }, []);

    const isInQueue = useCallback((movieId: number) => {
        return queue.some(m => m.id === movieId);
    }, [queue]);

    const syncToServer = useCallback(async () => {
        if (!userId) {
            console.log('No user ID, skipping server sync');
            return;
        }

        try {
            const response = await fetch('/MOVIESHOWS/api/queue.php', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: 'sync',
                    queue: queue.map((movie, index) => ({
                        movie_id: movie.id,
                        position: index
                    }))
                })
            });

            if (!response.ok) {
                throw new Error('Failed to sync queue');
            }

            console.log('Queue synced to server');
        } catch (error) {
            console.error('Queue sync failed:', error);
            throw error;
        }
    }, [userId, queue]);

    return {
        queue,
        addToQueue,
        removeFromQueue,
        reorderQueue,
        clearQueue,
        isInQueue,
        syncToServer
    };
}
