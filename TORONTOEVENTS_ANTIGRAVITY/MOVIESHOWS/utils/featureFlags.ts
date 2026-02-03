/**
 * UPDATE #88: Feature Flags System
 * Control feature rollout
 */

interface FeatureFlag {
    key: string;
    enabled: boolean;
    description?: string;
    rolloutPercentage?: number; // 0-100
    enabledForUsers?: string[];
    disabledForUsers?: string[];
}

class FeatureFlagManager {
    private flags: Map<string, FeatureFlag> = new Map();

    /**
     * Register a feature flag
     */
    register(flag: FeatureFlag): void {
        this.flags.set(flag.key, flag);
    }

    /**
     * Check if feature is enabled for user
     */
    isEnabled(key: string, userId?: string): boolean {
        const flag = this.flags.get(key);
        if (!flag) {
            return false; // Default to disabled if flag doesn't exist
        }

        // Check if explicitly disabled for user
        if (userId && flag.disabledForUsers?.includes(userId)) {
            return false;
        }

        // Check if explicitly enabled for user
        if (userId && flag.enabledForUsers?.includes(userId)) {
            return true;
        }

        // Check rollout percentage
        if (flag.rolloutPercentage !== undefined && userId) {
            const hash = this.hashString(userId);
            const userPercentage = (hash % 100);
            if (userPercentage >= flag.rolloutPercentage) {
                return false;
            }
        }

        return flag.enabled;
    }

    /**
     * Enable feature
     */
    enable(key: string): void {
        const flag = this.flags.get(key);
        if (flag) {
            flag.enabled = true;
        }
    }

    /**
     * Disable feature
     */
    disable(key: string): void {
        const flag = this.flags.get(key);
        if (flag) {
            flag.enabled = false;
        }
    }

    /**
     * Set rollout percentage
     */
    setRollout(key: string, percentage: number): void {
        const flag = this.flags.get(key);
        if (flag) {
            flag.rolloutPercentage = Math.max(0, Math.min(100, percentage));
        }
    }

    /**
     * Get all flags
     */
    getAllFlags(): FeatureFlag[] {
        return Array.from(this.flags.values());
    }

    /**
     * Get flag details
     */
    getFlag(key: string): FeatureFlag | undefined {
        return this.flags.get(key);
    }

    private hashString(str: string): number {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return Math.abs(hash);
    }
}

export const featureFlags = new FeatureFlagManager();

// Register default flags
featureFlags.register({
    key: 'new_ui',
    enabled: false,
    description: 'New UI redesign',
    rolloutPercentage: 10
});

featureFlags.register({
    key: 'advanced_search',
    enabled: true,
    description: 'Advanced search features'
});

featureFlags.register({
    key: 'social_features',
    enabled: true,
    description: 'Social sharing and comments'
});

featureFlags.register({
    key: 'recommendations',
    enabled: true,
    description: 'Personalized recommendations'
});

featureFlags.register({
    key: 'beta_features',
    enabled: false,
    description: 'Beta features for testing',
    rolloutPercentage: 5
});

/**
 * React hook for feature flags
 */
import { useState, useEffect } from 'react';

export function useFeatureFlag(key: string, userId?: string): boolean {
    const [isEnabled, setIsEnabled] = useState(false);

    useEffect(() => {
        setIsEnabled(featureFlags.isEnabled(key, userId));
    }, [key, userId]);

    return isEnabled;
}

/**
 * Component wrapper for feature flags
 */
import React from 'react';

interface FeatureGateProps {
    flag: string;
    userId?: string;
    children: React.ReactNode;
    fallback?: React.ReactNode;
}

export function FeatureGate({ flag, userId, children, fallback = null }: FeatureGateProps) {
    const isEnabled = useFeatureFlag(flag, userId);
    return <>{ isEnabled? children: fallback } </>;
}
