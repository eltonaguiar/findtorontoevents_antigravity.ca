/**
 * UPDATE #105: Premium Features System
 * Unlock premium features for subscribers
 */

interface PremiumFeature {
    id: string;
    name: string;
    description: string;
    requiredTier: 'basic' | 'premium' | 'enterprise';
    icon?: string;
}

const premiumFeatures: PremiumFeature[] = [
    {
        id: 'offline_downloads',
        name: 'Offline Downloads',
        description: 'Download content to watch offline',
        requiredTier: 'basic',
        icon: '📥'
    },
    {
        id: 'ad_free',
        name: 'Ad-Free Experience',
        description: 'Enjoy content without interruptions',
        requiredTier: 'basic',
        icon: '🚫'
    },
    {
        id: 'hd_streaming',
        name: 'HD Streaming',
        description: 'Watch in high definition',
        requiredTier: 'basic',
        icon: '📺'
    },
    {
        id: 'uhd_streaming',
        name: '4K Ultra HD',
        description: 'Experience cinema-quality streaming',
        requiredTier: 'premium',
        icon: '🎬'
    },
    {
        id: 'advanced_recommendations',
        name: 'Advanced AI Recommendations',
        description: 'Personalized content suggestions',
        requiredTier: 'premium',
        icon: '🤖'
    },
    {
        id: 'early_access',
        name: 'Early Access',
        description: 'Get new features before everyone else',
        requiredTier: 'premium',
        icon: '⚡'
    },
    {
        id: 'api_access',
        name: 'API Access',
        description: 'Integrate with your own applications',
        requiredTier: 'enterprise',
        icon: '🔌'
    },
    {
        id: 'custom_branding',
        name: 'Custom Branding',
        description: 'White-label the platform',
        requiredTier: 'enterprise',
        icon: '🎨'
    },
    {
        id: 'team_management',
        name: 'Team Management',
        description: 'Manage multiple users and permissions',
        requiredTier: 'enterprise',
        icon: '👥'
    }
];

class PremiumFeaturesManager {
    /**
     * Check if user has access to feature
     */
    hasAccess(userTier: string, featureId: string): boolean {
        const feature = premiumFeatures.find(f => f.id === featureId);
        if (!feature) return false;

        const tierOrder = ['free', 'basic', 'premium', 'enterprise'];
        const userTierIndex = tierOrder.indexOf(userTier);
        const requiredTierIndex = tierOrder.indexOf(feature.requiredTier);

        return userTierIndex >= requiredTierIndex;
    }

    /**
     * Get all features for tier
     */
    getFeaturesForTier(tier: string): PremiumFeature[] {
        const tierOrder = ['free', 'basic', 'premium', 'enterprise'];
        const tierIndex = tierOrder.indexOf(tier);

        return premiumFeatures.filter(feature => {
            const featureTierIndex = tierOrder.indexOf(feature.requiredTier);
            return featureTierIndex <= tierIndex;
        });
    }

    /**
     * Get feature by ID
     */
    getFeature(featureId: string): PremiumFeature | undefined {
        return premiumFeatures.find(f => f.id === featureId);
    }

    /**
     * Get all features
     */
    getAllFeatures(): PremiumFeature[] {
        return premiumFeatures;
    }
}

export const premiumFeaturesManager = new PremiumFeaturesManager();

/**
 * Premium feature gate component
 */
import React from 'react';

interface PremiumGateProps {
    featureId: string;
    userTier: string;
    children: React.ReactNode;
    fallback?: React.ReactNode;
    onUpgrade?: () => void;
}

export function PremiumGate({
    featureId,
    userTier,
    children,
    fallback,
    onUpgrade
}: PremiumGateProps) {
    const hasAccess = premiumFeaturesManager.hasAccess(userTier, featureId);
    const feature = premiumFeaturesManager.getFeature(featureId);

    if (hasAccess) {
        return <>{children}</>;
    }

    if (fallback) {
        return <>{fallback}</>;
    }

    return (
        <div className="premium-gate">
            <div className="premium-gate-icon">{feature?.icon || '🔒'}</div>
            <h3>{feature?.name}</h3>
            <p>{feature?.description}</p>
            <p className="required-tier">
                Requires: <strong>{feature?.requiredTier}</strong> plan
            </p>
            {onUpgrade && (
                <button onClick={onUpgrade} className="upgrade-button">
                    Upgrade Now
                </button>
            )}
        </div>
    );
}

/**
 * Premium features showcase
 */
interface PremiumShowcaseProps {
    currentTier: string;
    onUpgrade: () => void;
}

export function PremiumShowcase({ currentTier, onUpgrade }: PremiumShowcaseProps) {
    const availableFeatures = premiumFeaturesManager.getFeaturesForTier(currentTier);
    const lockedFeatures = premiumFeatures.filter(
        f => !availableFeatures.includes(f)
    );

    return (
        <div className="premium-showcase">
            <div className="showcase-section">
                <h2>Your Features</h2>
                <div className="features-grid">
                    {availableFeatures.map(feature => (
                        <div key={feature.id} className="feature-card available">
                            <div className="feature-icon">{feature.icon}</div>
                            <h3>{feature.name}</h3>
                            <p>{feature.description}</p>
                            <span className="feature-badge">✓ Available</span>
                        </div>
                    ))}
                </div>
            </div>

            {lockedFeatures.length > 0 && (
                <div className="showcase-section">
                    <h2>Unlock More Features</h2>
                    <div className="features-grid">
                        {lockedFeatures.map(feature => (
                            <div key={feature.id} className="feature-card locked">
                                <div className="feature-icon">{feature.icon}</div>
                                <h3>{feature.name}</h3>
                                <p>{feature.description}</p>
                                <span className="feature-badge locked">
                                    🔒 {feature.requiredTier}
                                </span>
                            </div>
                        ))}
                    </div>
                    <button onClick={onUpgrade} className="upgrade-cta">
                        Upgrade to Unlock All Features
                    </button>
                </div>
            )}
        </div>
    );
}

const styles = `
.premium-gate {
  padding: 3rem;
  text-align: center;
  background: rgba(0, 0, 0, 0.3);
  border: 2px dashed rgba(255, 255, 255, 0.2);
  border-radius: 12px;
}

.premium-gate-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.premium-gate h3 {
  margin: 0 0 0.5rem;
  font-size: 1.5rem;
}

.premium-gate p {
  margin: 0 0 1rem;
  opacity: 0.8;
}

.required-tier {
  font-size: 0.9rem;
}

.required-tier strong {
  color: #667eea;
  text-transform: capitalize;
}

.upgrade-button {
  margin-top: 1.5rem;
  padding: 1rem 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.upgrade-button:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.premium-showcase {
  padding: 2rem;
}

.showcase-section {
  margin-bottom: 3rem;
}

.showcase-section h2 {
  margin: 0 0 2rem;
  font-size: 2rem;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.feature-card {
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  border: 2px solid rgba(255, 255, 255, 0.1);
  transition: all 0.2s;
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
}

.feature-card.available {
  border-color: rgba(74, 222, 128, 0.3);
}

.feature-card.locked {
  opacity: 0.6;
}

.feature-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.feature-card h3 {
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
}

.feature-card p {
  margin: 0 0 1rem;
  opacity: 0.8;
  font-size: 0.9rem;
}

.feature-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 600;
}

.feature-badge:not(.locked) {
  background: rgba(74, 222, 128, 0.2);
  color: #4ade80;
}

.feature-badge.locked {
  background: rgba(255, 255, 255, 0.1);
  text-transform: capitalize;
}

.upgrade-cta {
  width: 100%;
  max-width: 400px;
  padding: 1.25rem 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 700;
  font-size: 1.1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.upgrade-cta:hover {
  transform: scale(1.02);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
}
`;
