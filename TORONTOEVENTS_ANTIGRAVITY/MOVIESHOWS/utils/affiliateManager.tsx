/**
 * UPDATE #108: Affiliate Program
 * Affiliate marketing and commission tracking
 */

interface Affiliate {
    id: string;
    userId: number;
    status: 'pending' | 'active' | 'suspended';
    commissionRate: number; // percentage
    totalEarnings: number;
    pendingEarnings: number;
    paidEarnings: number;
    createdAt: string;
    approvedAt?: string;
}

interface AffiliateClick {
    id: string;
    affiliateId: string;
    clickedAt: string;
    ipAddress?: string;
    userAgent?: string;
    converted: boolean;
}

interface AffiliateCommission {
    id: string;
    affiliateId: string;
    amount: number;
    subscriptionId: string;
    status: 'pending' | 'approved' | 'paid';
    createdAt: string;
    paidAt?: string;
}

class AffiliateManager {
    private affiliates: Map<string, Affiliate> = new Map();
    private clicks: AffiliateClick[] = [];
    private commissions: AffiliateCommission[] = [];

    /**
     * Apply to become an affiliate
     */
    async applyForAffiliate(userId: number): Promise<Affiliate> {
        const affiliate: Affiliate = {
            id: `aff_${Date.now()}`,
            userId,
            status: 'pending',
            commissionRate: 20, // 20% commission
            totalEarnings: 0,
            pendingEarnings: 0,
            paidEarnings: 0,
            createdAt: new Date().toISOString()
        };

        this.affiliates.set(affiliate.id, affiliate);
        return affiliate;
    }

    /**
     * Approve affiliate
     */
    approveAffiliate(affiliateId: string): void {
        const affiliate = this.affiliates.get(affiliateId);
        if (affiliate) {
            affiliate.status = 'active';
            affiliate.approvedAt = new Date().toISOString();
        }
    }

    /**
     * Track affiliate click
     */
    trackClick(affiliateId: string, ipAddress?: string, userAgent?: string): AffiliateClick {
        const click: AffiliateClick = {
            id: `click_${Date.now()}`,
            affiliateId,
            clickedAt: new Date().toISOString(),
            ipAddress,
            userAgent,
            converted: false
        };

        this.clicks.push(click);
        return click;
    }

    /**
     * Track conversion and create commission
     */
    trackConversion(
        affiliateId: string,
        subscriptionId: string,
        amount: number
    ): AffiliateCommission {
        const affiliate = this.affiliates.get(affiliateId);
        if (!affiliate || affiliate.status !== 'active') {
            throw new Error('Invalid or inactive affiliate');
        }

        const commissionAmount = amount * (affiliate.commissionRate / 100);

        const commission: AffiliateCommission = {
            id: `comm_${Date.now()}`,
            affiliateId,
            amount: commissionAmount,
            subscriptionId,
            status: 'pending',
            createdAt: new Date().toISOString()
        };

        this.commissions.push(commission);

        // Update affiliate earnings
        affiliate.totalEarnings += commissionAmount;
        affiliate.pendingEarnings += commissionAmount;

        return commission;
    }

    /**
     * Approve commission
     */
    approveCommission(commissionId: string): void {
        const commission = this.commissions.find(c => c.id === commissionId);
        if (commission) {
            commission.status = 'approved';
        }
    }

    /**
     * Pay commission
     */
    payCommission(commissionId: string): void {
        const commission = this.commissions.find(c => c.id === commissionId);
        if (!commission) return;

        const affiliate = this.affiliates.get(commission.affiliateId);
        if (!affiliate) return;

        commission.status = 'paid';
        commission.paidAt = new Date().toISOString();

        affiliate.pendingEarnings -= commission.amount;
        affiliate.paidEarnings += commission.amount;
    }

    /**
     * Get affiliate stats
     */
    getAffiliateStats(affiliateId: string): {
        totalClicks: number;
        conversions: number;
        conversionRate: number;
        totalEarnings: number;
        pendingEarnings: number;
        paidEarnings: number;
    } {
        const affiliate = this.affiliates.get(affiliateId);
        if (!affiliate) {
            return {
                totalClicks: 0,
                conversions: 0,
                conversionRate: 0,
                totalEarnings: 0,
                pendingEarnings: 0,
                paidEarnings: 0
            };
        }

        const affiliateClicks = this.clicks.filter(c => c.affiliateId === affiliateId);
        const conversions = affiliateClicks.filter(c => c.converted).length;

        return {
            totalClicks: affiliateClicks.length,
            conversions,
            conversionRate: affiliateClicks.length > 0 ? (conversions / affiliateClicks.length) * 100 : 0,
            totalEarnings: affiliate.totalEarnings,
            pendingEarnings: affiliate.pendingEarnings,
            paidEarnings: affiliate.paidEarnings
        };
    }

    /**
     * Get affiliate commissions
     */
    getAffiliateCommissions(affiliateId: string): AffiliateCommission[] {
        return this.commissions.filter(c => c.affiliateId === affiliateId);
    }
}

export const affiliateManager = new AffiliateManager();

/**
 * Affiliate dashboard component
 */
import React from 'react';

interface AffiliateDashboardProps {
    affiliateId: string;
}

export function AffiliateDashboard({ affiliateId }: AffiliateDashboardProps) {
    const stats = affiliateManager.getAffiliateStats(affiliateId);
    const commissions = affiliateManager.getAffiliateCommissions(affiliateId);

    const affiliateLink = `https://movieshows.com/signup?aff=${affiliateId}`;

    return (
        <div className="affiliate-dashboard">
            <div className="dashboard-header">
                <h2>Affiliate Dashboard</h2>
                <p>Earn 20% commission on every sale</p>
            </div>

            <div className="affiliate-link-section">
                <h3>Your Affiliate Link</h3>
                <div className="link-display">
                    <input type="text" value={affiliateLink} readOnly />
                    <button onClick={() => navigator.clipboard.writeText(affiliateLink)}>
                        Copy Link
                    </button>
                </div>
            </div>

            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-icon">👆</div>
                    <div className="stat-content">
                        <div className="stat-value">{stats.totalClicks}</div>
                        <div className="stat-label">Total Clicks</div>
                    </div>
                </div>

                <div className="stat-card">
                    <div className="stat-icon">✅</div>
                    <div className="stat-content">
                        <div className="stat-value">{stats.conversions}</div>
                        <div className="stat-label">Conversions</div>
                    </div>
                </div>

                <div className="stat-card">
                    <div className="stat-icon">📊</div>
                    <div className="stat-content">
                        <div className="stat-value">{stats.conversionRate.toFixed(1)}%</div>
                        <div className="stat-label">Conversion Rate</div>
                    </div>
                </div>

                <div className="stat-card highlight">
                    <div className="stat-icon">💰</div>
                    <div className="stat-content">
                        <div className="stat-value">${stats.totalEarnings.toFixed(2)}</div>
                        <div className="stat-label">Total Earnings</div>
                    </div>
                </div>

                <div className="stat-card">
                    <div className="stat-icon">⏳</div>
                    <div className="stat-content">
                        <div className="stat-value">${stats.pendingEarnings.toFixed(2)}</div>
                        <div className="stat-label">Pending</div>
                    </div>
                </div>

                <div className="stat-card">
                    <div className="stat-icon">✓</div>
                    <div className="stat-content">
                        <div className="stat-value">${stats.paidEarnings.toFixed(2)}</div>
                        <div className="stat-label">Paid Out</div>
                    </div>
                </div>
            </div>

            <div className="commissions-section">
                <h3>Recent Commissions</h3>
                {commissions.length === 0 ? (
                    <p className="empty-state">No commissions yet. Start promoting!</p>
                ) : (
                    <div className="commissions-table">
                        {commissions.slice(0, 10).map(commission => (
                            <div key={commission.id} className="commission-row">
                                <div className="commission-info">
                                    <span className="commission-date">
                                        {new Date(commission.createdAt).toLocaleDateString()}
                                    </span>
                                    <span className={`commission-status status-${commission.status}`}>
                                        {commission.status}
                                    </span>
                                </div>
                                <div className="commission-amount">
                                    ${commission.amount.toFixed(2)}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

const styles = `
.affiliate-dashboard {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;
}

.dashboard-header {
  text-align: center;
  margin-bottom: 3rem;
}

.dashboard-header h2 {
  margin: 0 0 0.5rem;
  font-size: 2rem;
}

.dashboard-header p {
  margin: 0;
  font-size: 1.1rem;
  opacity: 0.8;
}

.affiliate-link-section {
  margin-bottom: 2rem;
}

.affiliate-link-section h3 {
  margin: 0 0 1rem;
}

.link-display {
  display: flex;
  gap: 0.5rem;
}

.link-display input {
  flex: 1;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  font-family: monospace;
}

.link-display button {
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.link-display button:hover {
  transform: scale(1.05);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  display: flex;
  gap: 1rem;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.stat-card.highlight {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border-color: #667eea;
}

.stat-icon {
  font-size: 2rem;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: #667eea;
}

.stat-label {
  margin-top: 0.25rem;
  opacity: 0.7;
  font-size: 0.9rem;
}

.commissions-section h3 {
  margin: 0 0 1rem;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  opacity: 0.6;
}

.commissions-table {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.commission-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.commission-info {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.commission-date {
  opacity: 0.7;
  font-size: 0.9rem;
}

.commission-status {
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

.status-approved {
  background: rgba(74, 222, 128, 0.2);
  color: #4ade80;
}

.status-paid {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.commission-amount {
  font-weight: 700;
  color: #4ade80;
  font-size: 1.1rem;
}
`;
