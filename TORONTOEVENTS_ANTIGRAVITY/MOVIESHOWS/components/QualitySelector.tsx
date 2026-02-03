/**
 * UPDATE #99: Quality Selector
 * Video quality selection component
 */

import React, { useState } from 'react';

type VideoQuality = '4k' | '1080p' | '720p' | '480p' | '360p' | 'auto';

interface QualityOption {
    quality: VideoQuality;
    label: string;
    bitrate?: number;
    resolution?: string;
}

const qualityOptions: QualityOption[] = [
    { quality: 'auto', label: 'Auto', resolution: 'Adaptive' },
    { quality: '4k', label: '4K', bitrate: 20000, resolution: '3840x2160' },
    { quality: '1080p', label: 'Full HD', bitrate: 8000, resolution: '1920x1080' },
    { quality: '720p', label: 'HD', bitrate: 5000, resolution: '1280x720' },
    { quality: '480p', label: 'SD', bitrate: 2500, resolution: '854x480' },
    { quality: '360p', label: 'Low', bitrate: 1000, resolution: '640x360' }
];

interface QualitySelectorProps {
    currentQuality: VideoQuality;
    onQualityChange: (quality: VideoQuality) => void;
    availableQualities?: VideoQuality[];
}

export function QualitySelector({
    currentQuality,
    onQualityChange,
    availableQualities = ['auto', '1080p', '720p', '480p', '360p']
}: QualitySelectorProps) {
    const [isOpen, setIsOpen] = useState(false);

    const filteredOptions = qualityOptions.filter(option =>
        availableQualities.includes(option.quality)
    );

    const currentOption = qualityOptions.find(opt => opt.quality === currentQuality);

    return (
        <div className="quality-selector">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="quality-button"
            >
                ⚙️ {currentOption?.label}
            </button>

            {isOpen && (
                <div className="quality-menu">
                    <div className="quality-header">
                        <span>Quality</span>
                        <button onClick={() => setIsOpen(false)} className="close-btn">×</button>
                    </div>

                    <div className="quality-options">
                        {filteredOptions.map(option => (
                            <button
                                key={option.quality}
                                onClick={() => {
                                    onQualityChange(option.quality);
                                    setIsOpen(false);
                                }}
                                className={`quality-option ${currentQuality === option.quality ? 'active' : ''}`}
                            >
                                <div className="option-label">{option.label}</div>
                                {option.resolution && (
                                    <div className="option-resolution">{option.resolution}</div>
                                )}
                                {currentQuality === option.quality && (
                                    <span className="check-mark">✓</span>
                                )}
                            </button>
                        ))}
                    </div>

                    <div className="quality-info">
                        <p>Higher quality requires more bandwidth</p>
                    </div>
                </div>
            )}
        </div>
    );
}

/**
 * Adaptive quality manager
 */
class AdaptiveQualityManager {
    private currentQuality: VideoQuality = 'auto';
    private bandwidth: number = 0;

    /**
     * Measure network bandwidth
     */
    async measureBandwidth(): Promise<number> {
        const startTime = Date.now();
        const testUrl = 'https://via.placeholder.com/1000x1000.jpg';

        try {
            const response = await fetch(testUrl);
            const blob = await response.blob();
            const endTime = Date.now();

            const duration = (endTime - startTime) / 1000; // seconds
            const sizeInBits = blob.size * 8;
            this.bandwidth = sizeInBits / duration; // bits per second

            return this.bandwidth;
        } catch (error) {
            console.error('Bandwidth measurement failed:', error);
            return 0;
        }
    }

    /**
     * Get recommended quality based on bandwidth
     */
    getRecommendedQuality(): VideoQuality {
        const mbps = this.bandwidth / 1000000;

        if (mbps >= 25) return '4k';
        if (mbps >= 8) return '1080p';
        if (mbps >= 5) return '720p';
        if (mbps >= 2.5) return '480p';
        return '360p';
    }

    /**
     * Auto-adjust quality
     */
    async autoAdjustQuality(): Promise<VideoQuality> {
        await this.measureBandwidth();
        return this.getRecommendedQuality();
    }
}

export const adaptiveQualityManager = new AdaptiveQualityManager();

const styles = `
.quality-selector {
  position: relative;
}

.quality-button {
  padding: 0.5rem 1rem;
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
}

.quality-button:hover {
  background: rgba(0, 0, 0, 0.8);
}

.quality-menu {
  position: absolute;
  bottom: 100%;
  right: 0;
  margin-bottom: 0.5rem;
  min-width: 250px;
  background: rgba(20, 20, 20, 0.98);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  overflow: hidden;
  backdrop-filter: blur(10px);
}

.quality-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
}

.quality-options {
  max-height: 300px;
  overflow-y: auto;
}

.quality-option {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: none;
  border: none;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  color: white;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
}

.quality-option:hover {
  background: rgba(255, 255, 255, 0.1);
}

.quality-option.active {
  background: rgba(102, 126, 234, 0.2);
}

.option-label {
  font-weight: 500;
}

.option-resolution {
  font-size: 0.85rem;
  opacity: 0.6;
}

.check-mark {
  color: #667eea;
  font-weight: 700;
}

.quality-info {
  padding: 0.75rem 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 0.85rem;
  opacity: 0.6;
}

.quality-info p {
  margin: 0;
}
`;
