/**
 * UPDATE #98: Video Player Component
 * Advanced video player with controls
 */

import React, { useState, useRef, useEffect } from 'react';

interface VideoPlayerProps {
    src: string;
    poster?: string;
    autoplay?: boolean;
    onEnded?: () => void;
    onTimeUpdate?: (currentTime: number) => void;
}

export function VideoPlayer({
    src,
    poster,
    autoplay = false,
    onEnded,
    onTimeUpdate
}: VideoPlayerProps) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [volume, setVolume] = useState(1);
    const [isMuted, setIsMuted] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [showControls, setShowControls] = useState(true);
    const controlsTimeout = useRef<NodeJS.Timeout>();

    useEffect(() => {
        const video = videoRef.current;
        if (!video) return;

        const handleTimeUpdate = () => {
            setCurrentTime(video.currentTime);
            onTimeUpdate?.(video.currentTime);
        };

        const handleLoadedMetadata = () => {
            setDuration(video.duration);
        };

        const handleEnded = () => {
            setIsPlaying(false);
            onEnded?.();
        };

        video.addEventListener('timeupdate', handleTimeUpdate);
        video.addEventListener('loadedmetadata', handleLoadedMetadata);
        video.addEventListener('ended', handleEnded);

        return () => {
            video.removeEventListener('timeupdate', handleTimeUpdate);
            video.removeEventListener('loadedmetadata', handleLoadedMetadata);
            video.removeEventListener('ended', handleEnded);
        };
    }, [onEnded, onTimeUpdate]);

    const togglePlay = () => {
        const video = videoRef.current;
        if (!video) return;

        if (isPlaying) {
            video.pause();
        } else {
            video.play();
        }
        setIsPlaying(!isPlaying);
    };

    const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
        const video = videoRef.current;
        if (!video) return;

        const time = parseFloat(e.target.value);
        video.currentTime = time;
        setCurrentTime(time);
    };

    const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const video = videoRef.current;
        if (!video) return;

        const vol = parseFloat(e.target.value);
        video.volume = vol;
        setVolume(vol);
        setIsMuted(vol === 0);
    };

    const toggleMute = () => {
        const video = videoRef.current;
        if (!video) return;

        video.muted = !isMuted;
        setIsMuted(!isMuted);
    };

    const toggleFullscreen = () => {
        const container = videoRef.current?.parentElement;
        if (!container) return;

        if (!isFullscreen) {
            container.requestFullscreen?.();
        } else {
            document.exitFullscreen?.();
        }
        setIsFullscreen(!isFullscreen);
    };

    const formatTime = (seconds: number): string => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const handleMouseMove = () => {
        setShowControls(true);

        if (controlsTimeout.current) {
            clearTimeout(controlsTimeout.current);
        }

        controlsTimeout.current = setTimeout(() => {
            if (isPlaying) {
                setShowControls(false);
            }
        }, 3000);
    };

    return (
        <div className="video-player" onMouseMove={handleMouseMove}>
            <video
                ref={videoRef}
                src={src}
                poster={poster}
                autoPlay={autoplay}
                onClick={togglePlay}
            />

            <div className={`video-controls ${showControls ? 'visible' : ''}`}>
                <div className="progress-bar">
                    <input
                        type="range"
                        min="0"
                        max={duration}
                        value={currentTime}
                        onChange={handleSeek}
                        className="seek-bar"
                    />
                </div>

                <div className="controls-bottom">
                    <button onClick={togglePlay} className="control-btn">
                        {isPlaying ? '⏸' : '▶'}
                    </button>

                    <div className="time-display">
                        {formatTime(currentTime)} / {formatTime(duration)}
                    </div>

                    <div className="volume-control">
                        <button onClick={toggleMute} className="control-btn">
                            {isMuted ? '🔇' : '🔊'}
                        </button>
                        <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.1"
                            value={isMuted ? 0 : volume}
                            onChange={handleVolumeChange}
                            className="volume-bar"
                        />
                    </div>

                    <button onClick={toggleFullscreen} className="control-btn">
                        {isFullscreen ? '⛶' : '⛶'}
                    </button>
                </div>
            </div>
        </div>
    );
}

const styles = `
.video-player {
  position: relative;
  width: 100%;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.video-player video {
  width: 100%;
  display: block;
  cursor: pointer;
}

.video-controls {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 100%);
  padding: 1rem;
  opacity: 0;
  transition: opacity 0.3s;
}

.video-controls.visible {
  opacity: 1;
}

.progress-bar {
  margin-bottom: 0.75rem;
}

.seek-bar {
  width: 100%;
  height: 4px;
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 2px;
  outline: none;
  cursor: pointer;
}

.seek-bar::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 12px;
  height: 12px;
  background: #667eea;
  border-radius: 50%;
  cursor: pointer;
}

.controls-bottom {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.control-btn {
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.25rem;
  transition: transform 0.2s;
}

.control-btn:hover {
  transform: scale(1.1);
}

.time-display {
  font-size: 0.9rem;
  color: white;
}

.volume-control {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: auto;
}

.volume-bar {
  width: 80px;
  height: 4px;
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 2px;
  outline: none;
  cursor: pointer;
}

.volume-bar::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 10px;
  height: 10px;
  background: white;
  border-radius: 50%;
  cursor: pointer;
}
`;
