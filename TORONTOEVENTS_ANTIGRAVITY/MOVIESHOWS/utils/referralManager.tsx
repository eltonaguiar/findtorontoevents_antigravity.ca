/**
 * UPDATE #107: Referral System
 * User referral and rewards program
 */

interface Referral {
    id: string;
    referrerId: number;
    referredUserId?: number;
    referralCode: string;
    status: 'pending' | 'completed' | 'rewarded';
    createdAt: string;
    completedAt?: string;
    reward?: number;
}

interface ReferralReward {
    type: 'credit' | 'discount' | 'free_month';
    value: number;
    description: string;
}

class ReferralManager {
    private referrals: Map<string, Referral> = new Map();
    private userCodes: Map<number, string> = new Map();

    /**
     * Generate referral code for user
     */
    generateReferralCode(userId: number): string {
        // Check if user already has a code
        const existingCode = this.userCodes.get(userId);
        if (existingCode) return existingCode;

        // Generate new code
        const code = `REF${userId}${Math.random().toString(36).substr(2, 6).toUpperCase()}`;
        this.userCodes.set(userId, code);

        return code;
    }

    /**
     * Get user's referral code
     */
    getUserReferralCode(userId: number): string {
        return this.userCodes.get(userId) || this.generateReferralCode(userId);
    }

    /**
     * Create referral
     */
    createReferral(referrerId: number, referralCode: string): Referral {
        const referral: Referral = {
            id: `ref_${Date.now()}`,
            referrerId,
            referralCode,
            status: 'pending',
            createdAt: new Date().toISOString()
        };

        this.referrals.set(referral.id, referral);
        return referral;
    }

    /**
     * Complete referral (when referred user subscribes)
     */
    completeReferral(referralId: string, referredUserId: number): ReferralReward {
        const referral = this.referrals.get(referralId);
        if (!referral) throw new Error('Referral not found');

        referral.status = 'completed';
        referral.referredUserId = referredUserId;
        referral.completedAt = new Date().toISOString();

        // Calculate reward
        const reward: ReferralReward = {
            type: 'credit',
            value: 10, // $10 credit
            description: '$10 credit for successful referral'
        };

        referral.reward = reward.value;
        referral.status = 'rewarded';

        return reward;
    }

    /**
     * Get user's referrals
     */
    getUserReferrals(userId: number): Referral[] {
        return Array.from(this.referrals.values())
            .filter(ref => ref.referrerId === userId);
    }

    /**
     * Get referral stats
     */
    getReferralStats(userId: number): {
        totalReferrals: number;
        completedReferrals: number;
        pendingReferrals: number;
        totalRewards: number;
    } {
        const userReferrals = this.getUserReferrals(userId);

        return {
            totalReferrals: userReferrals.length,
            completedReferrals: userReferrals.filter(r => r.status === 'completed' || r.status === 'rewarded').length,
            pendingReferrals: userReferrals.filter(r => r.status === 'pending').length,
            totalRewards: userReferrals.reduce((sum, r) => sum + (r.reward || 0), 0)
        };
    }

    /**
     * Validate referral code
     */
    validateReferralCode(code: string): boolean {
        return Array.from(this.userCodes.values()).includes(code);
    }

    /**
     * Get referrer ID from code
     */
    getReferrerIdFromCode(code: string): number | null {
        for (const [userId, userCode] of this.userCodes.entries()) {
            if (userCode === code) {
                return userId;
            }
        }
        return null;
    }
}

export const referralManager = new ReferralManager();

/**
 * Referral dashboard component
 */
import React from 'react';

interface ReferralDashboardProps {
    userId: number;
}

export function ReferralDashboard({ userId }: ReferralDashboardProps) {
    const referralCode = referralManager.getUserReferralCode(userId);
    const stats = referralManager.getReferralStats(userId);
    const referrals = referralManager.getUserReferrals(userId);

    const copyToClipboard = () => {
        navigator.clipboard.writeText(referralCode);
        alert('Referral code copied!');
    };

    const shareUrl = `https://movieshows.com/signup?ref=${referralCode}`;

    return (
        <div className="referral-dashboard">
            <div className="referral-header">
                <h2>Refer Friends & Earn Rewards</h2>
                <p>Give $10, Get $10 when your friends subscribe</p>
            </div>

            <div className="referral-code-section">
                <div className="code-display">
                    <span className="code-label">Your Referral Code</span>
                    <div className="code-value">{referralCode}</div>
                </div>
                <button onClick={copyToClipboard} className="copy-button">
                    📋 Copy Code
                </button>
            </div>

            <div className="share-section">
                <h3>Share Your Link</h3>
                <div className="share-url">
                    <input type="text" value={shareUrl} readOnly />
                    <button onClick={() => navigator.clipboard.writeText(shareUrl)}>
                        Copy Link
                    </button>
                </div>
            </div>

            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-value">{stats.totalReferrals}</div>
                    <div className="stat-label">Total Referrals</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{stats.completedReferrals}</div>
                    <div className="stat-label">Completed</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{stats.pendingReferrals}</div>
                    <div className="stat-label">Pending</div>
                </div>
                <div className="stat-card highlight">
                    <div className="stat-value">${stats.totalRewards}</div>
                    <div className="stat-label">Total Earned</div>
                </div>
            </div>

            <div className="referrals-list">
                <h3>Your Referrals</h3>
                {referrals.length === 0 ? (
                    <p className="empty-state">No referrals yet. Start sharing your code!</p>
                ) : (
                    <div className="referrals-table">
                        {referrals.map(referral => (
                            <div key={referral.id} className="referral-row">
                                <div className="referral-info">
                                    <span className="referral-date">
                                        {new Date(referral.createdAt).toLocaleDateString()}
                                    </span>
                                    <span className={`referral-status status-${referral.status}`}>
                                        {referral.status}
                                    </span>
                                </div>
                                {referral.reward && (
                                    <div className="referral-reward">+${referral.reward}</div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

const styles = `
.referral-dashboard {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}

.referral-header {
  text-align: center;
  margin-bottom: 3rem;
}

.referral-header h2 {
  margin: 0 0 0.5rem;
  font-size: 2rem;
}

.referral-header p {
  margin: 0;
  font-size: 1.1rem;
  opacity: 0.8;
}

.referral-code-section {
  display: flex;
  gap: 1rem;
  align-items: center;
  padding: 2rem;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border: 2px solid rgba(102, 126, 234, 0.3);
  border-radius: 12px;
  margin-bottom: 2rem;
}

.code-display {
  flex: 1;
}

.code-label {
  display: block;
  font-size: 0.9rem;
  opacity: 0.7;
  margin-bottom: 0.5rem;
}

.code-value {
  font-size: 2rem;
  font-weight: 700;
  font-family: monospace;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.copy-button {
  padding: 1rem 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.copy-button:hover {
  transform: scale(1.05);
}

.share-section {
  margin-bottom: 2rem;
}

.share-section h3 {
  margin: 0 0 1rem;
}

.share-url {
  display: flex;
  gap: 0.5rem;
}

.share-url input {
  flex: 1;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
}

.share-url button {
  padding: 0.75rem 1.5rem;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: white;
  cursor: pointer;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  text-align: center;
}

.stat-card.highlight {
  background: linear-gradient(135deg, rgba(74, 222, 128, 0.1) 0%, rgba(34, 197, 94, 0.1) 100%);
  border: 1px solid rgba(74, 222, 128, 0.3);
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: #667eea;
}

.stat-card.highlight .stat-value {
  color: #4ade80;
}

.stat-label {
  margin-top: 0.5rem;
  opacity: 0.7;
  font-size: 0.9rem;
}

.referrals-list h3 {
  margin: 0 0 1rem;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  opacity: 0.6;
}

.referrals-table {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.referral-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.referral-info {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.referral-date {
  opacity: 0.7;
  font-size: 0.9rem;
}

.referral-status {
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: capitalize;
}

.status-pending {
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
}

.status-completed,
.status-rewarded {
  background: rgba(74, 222, 128, 0.2);
  color: #4ade80;
}

.referral-reward {
  font-weight: 700;
  color: #4ade80;
  font-size: 1.1rem;
}
`;
