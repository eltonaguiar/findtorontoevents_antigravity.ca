/**
 * UPDATE #101: Subscription Management System
 * Handle user subscriptions and tiers
 */

type SubscriptionTier = 'free' | 'basic' | 'premium' | 'enterprise';

interface SubscriptionPlan {
    id: string;
    tier: SubscriptionTier;
    name: string;
    price: number;
    interval: 'month' | 'year';
    features: string[];
    limits: {
        maxWatchlists?: number;
        maxPlaylists?: number;
        offlineDownloads?: boolean;
        adFree?: boolean;
        hdStreaming?: boolean;
        ultraHdStreaming?: boolean;
        simultaneousStreams?: number;
    };
}

interface UserSubscription {
    userId: number;
    planId: string;
    tier: SubscriptionTier;
    status: 'active' | 'canceled' | 'expired' | 'trial';
    startDate: string;
    endDate?: string;
    autoRenew: boolean;
    paymentMethod?: string;
}

const subscriptionPlans: SubscriptionPlan[] = [
    {
        id: 'free',
        tier: 'free',
        name: 'Free',
        price: 0,
        interval: 'month',
        features: [
            'Browse movies and TV shows',
            'Watch trailers',
            'Basic recommendations',
            'Limited watchlist'
        ],
        limits: {
            maxWatchlists: 1,
            maxPlaylists: 3,
            offlineDownloads: false,
            adFree: false,
            hdStreaming: false,
            ultraHdStreaming: false,
            simultaneousStreams: 1
        }
    },
    {
        id: 'basic',
        tier: 'basic',
        name: 'Basic',
        price: 9.99,
        interval: 'month',
        features: [
            'Everything in Free',
            'Ad-free experience',
            'HD streaming',
            'Unlimited watchlists',
            'Download for offline viewing'
        ],
        limits: {
            offlineDownloads: true,
            adFree: true,
            hdStreaming: true,
            ultraHdStreaming: false,
            simultaneousStreams: 2
        }
    },
    {
        id: 'premium',
        tier: 'premium',
        name: 'Premium',
        price: 14.99,
        interval: 'month',
        features: [
            'Everything in Basic',
            'Ultra HD (4K) streaming',
            'Advanced recommendations',
            'Priority support',
            'Early access to new features'
        ],
        limits: {
            offlineDownloads: true,
            adFree: true,
            hdStreaming: true,
            ultraHdStreaming: true,
            simultaneousStreams: 4
        }
    },
    {
        id: 'enterprise',
        tier: 'enterprise',
        name: 'Enterprise',
        price: 49.99,
        interval: 'month',
        features: [
            'Everything in Premium',
            'Team management',
            'Custom branding',
            'API access',
            'Dedicated support',
            'Analytics dashboard'
        ],
        limits: {
            offlineDownloads: true,
            adFree: true,
            hdStreaming: true,
            ultraHdStreaming: true,
            simultaneousStreams: 10
        }
    }
];

class SubscriptionManager {
    /**
     * Get all available plans
     */
    getPlans(): SubscriptionPlan[] {
        return subscriptionPlans;
    }

    /**
     * Get plan by ID
     */
    getPlan(planId: string): SubscriptionPlan | undefined {
        return subscriptionPlans.find(plan => plan.id === planId);
    }

    /**
     * Check if user has access to feature
     */
    hasFeature(subscription: UserSubscription, feature: keyof SubscriptionPlan['limits']): boolean {
        const plan = this.getPlan(subscription.planId);
        if (!plan) return false;

        return plan.limits[feature] === true;
    }

    /**
     * Get feature limit
     */
    getLimit(subscription: UserSubscription, limit: keyof SubscriptionPlan['limits']): any {
        const plan = this.getPlan(subscription.planId);
        if (!plan) return 0;

        return plan.limits[limit];
    }

    /**
     * Check if subscription is active
     */
    isActive(subscription: UserSubscription): boolean {
        if (subscription.status !== 'active' && subscription.status !== 'trial') {
            return false;
        }

        if (subscription.endDate) {
            return new Date(subscription.endDate) > new Date();
        }

        return true;
    }

    /**
     * Calculate days remaining
     */
    getDaysRemaining(subscription: UserSubscription): number {
        if (!subscription.endDate) return Infinity;

        const now = new Date();
        const end = new Date(subscription.endDate);
        const diff = end.getTime() - now.getTime();

        return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
    }

    /**
     * Upgrade subscription
     */
    async upgrade(userId: number, newPlanId: string): Promise<UserSubscription> {
        // In production, this would call payment API
        console.log(`Upgrading user ${userId} to plan ${newPlanId}`);

        const plan = this.getPlan(newPlanId);
        if (!plan) throw new Error('Invalid plan');

        return {
            userId,
            planId: newPlanId,
            tier: plan.tier,
            status: 'active',
            startDate: new Date().toISOString(),
            autoRenew: true
        };
    }

    /**
     * Cancel subscription
     */
    async cancel(userId: number): Promise<void> {
        // In production, this would call payment API
        console.log(`Canceling subscription for user ${userId}`);
    }
}

export const subscriptionManager = new SubscriptionManager();

/**
 * React hook for subscription
 */
import { useState, useEffect } from 'react';

export function useSubscription(userId: number) {
    const [subscription, setSubscription] = useState<UserSubscription | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Fetch user subscription
        // This would call an API in production
        setLoading(false);
    }, [userId]);

    const upgrade = async (planId: string) => {
        const newSub = await subscriptionManager.upgrade(userId, planId);
        setSubscription(newSub);
    };

    const cancel = async () => {
        await subscriptionManager.cancel(userId);
        if (subscription) {
            setSubscription({ ...subscription, status: 'canceled' });
        }
    };

    return {
        subscription,
        loading,
        upgrade,
        cancel,
        hasFeature: (feature: keyof SubscriptionPlan['limits']) =>
            subscription ? subscriptionManager.hasFeature(subscription, feature) : false,
        getLimit: (limit: keyof SubscriptionPlan['limits']) =>
            subscription ? subscriptionManager.getLimit(subscription, limit) : 0
    };
}
