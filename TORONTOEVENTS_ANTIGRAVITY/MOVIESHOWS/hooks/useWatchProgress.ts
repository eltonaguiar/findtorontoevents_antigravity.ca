/**
 * UPDATE #74: Watch Progress Tracker
 * Track viewing progress for movies/shows
 */

import { useState, useEffect, useCallback } from 'react';

interface WatchProgress {
    movieId: number;
    progress: number; // 0-100
    currentTime: number; // in seconds
    duration: number; // in seconds
    lastWatched: string;
    completed: boolean;
}

const STORAGE_KEY = 'movieshows_watch_progress';

export function useWatchProgress() {
    const [progressMap, setProgressMap] = useState<Map<number, WatchProgress>>(new Map());

    // Load from localStorage
    useEffect(() => {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
            try {
                const data = JSON.parse(stored);
                setProgressMap(new Map(Object.entries(data).map(([k, v]) => [parseInt(k), v as WatchProgress])));
            } catch (error) {
                console.error('Failed to parse watch progress:', error);
            }
        }
    }, []);

    // Save to localStorage
    useEffect(() => {
        const data = Object.fromEntries(progressMap);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    }, [progressMap]);

    const updateProgress = useCallback((
        movieId: number,
        currentTime: number,
        duration: number
    ) => {
        const progress = Math.min(100, (currentTime / duration) * 100);
        const completed = progress >= 95; // Consider 95%+ as completed

        setProgressMap(prev => new Map(prev).set(movieId, {
            movieId,
            progress,
            currentTime,
            duration,
            lastWatched: new Date().toISOString(),
            completed
        }));
    }, []);

    const getProgress = useCallback((movieId: number): WatchProgress | null => {
        return progressMap.get(movieId) || null;
    }, [progressMap]);

    const clearProgress = useCallback((movieId: number) => {
        setProgressMap(prev => {
            const newMap = new Map(prev);
            newMap.delete(movieId);
            return newMap;
        });
    }, []);

    const getContinueWatching = useCallback((): WatchProgress[] => {
        return Array.from(progressMap.values())
            .filter(p => !p.completed && p.progress > 5)
            .sort((a, b) => new Date(b.lastWatched).getTime() - new Date(a.lastWatched).getTime())
            .slice(0, 10);
    }, [progressMap]);

    return {
        updateProgress,
        getProgress,
        clearProgress,
        getContinueWatching,
        allProgress: Array.from(progressMap.values())
    };
}

/**
 * Progress Bar Component
 */
import React from 'react';

interface ProgressBarProps {
    progress: number;
    showPercentage?: boolean;
}

export function ProgressBar({ progress, showPercentage = false }: ProgressBarProps) {
    return (
        <div className= "progress-bar-container" >
        <div className="progress-bar" >
            <div 
          className="progress-fill"
    style = {{ width: `${progress}%` }
}
        />
    </div>
{
    showPercentage && (
        <span className="progress-text" > { Math.round(progress) } % </span>
      )
}
</div>
  );
}

const styles = `
.progress-bar-container {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.85rem;
  opacity: 0.7;
  min-width: 40px;
}
`;
